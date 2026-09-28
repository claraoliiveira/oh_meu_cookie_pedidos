from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .forms import CheckoutForm, PickupDateForm
from .models import Customer, Order, OrderItem, PickupSlot, Product
from .pickup_schedule import PICKUP_SCHEDULES, pickup_date_label, pickup_options_for


def _catalog_context(form=None):
    slots = [
        slot
        for slot in
        PickupSlot.objects.filter(
            active=True,
            pickup_date__gte=timezone.localdate(),
        ).order_by("pickup_date", "period")
        if slot.pickup_date.weekday() in PICKUP_SCHEDULES
    ]
    dates = []
    slots_by_date = {}
    for slot in slots:
        key = slot.pickup_date.isoformat()
        if key not in slots_by_date:
            dates.append({"value": key, "label": pickup_date_label(slot.pickup_date)})
            slots_by_date[key] = []
        slots_by_date[key].append(
            {
                "id": slot.pk,
                "label": f"{slot.period} — {slot.location}",
            }
        )
    return {
        "products": Product.objects.filter(active=True),
        "form": form or CheckoutForm(),
        "available_dates": dates,
        "slots_by_date": slots_by_date,
    }


def catalogo(request):
    return render(request, "loja/pedidos.html", _catalog_context())


def finalizar_pedido(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Envie o formulário do pedido.")

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        return render(request, "loja/pedidos.html", _catalog_context(form), status=400)

    data = form.cleaned_data
    requested_items = data["items_json"]
    products = {
        product.pk: product
        for product in Product.objects.filter(
            pk__in=[item["product_id"] for item in requested_items],
            active=True,
        )
    }
    if len(products) != len({item["product_id"] for item in requested_items}):
        form.add_error("items_json", "Um produto escolhido não está mais no cardápio.")
        return render(request, "loja/pedidos.html", _catalog_context(form), status=400)

    with transaction.atomic():
        customer, _ = Customer.objects.get_or_create(
            phone=data["phone"],
            defaults={"name": data["name"]},
        )
        if customer.name != data["name"]:
            customer.name = data["name"]
            customer.save(update_fields=["name"])

        order = Order.objects.create(
            customer=customer,
            pickup_slot=data["pickup_slot"],
            payment_method=data["payment_method"],
            notes=data["notes"],
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=products[item["product_id"]],
                    quantity=item["quantity"],
                    unit_price=products[item["product_id"]].price,
                )
                for item in requested_items
            ]
        )
        order.recalculate_total()

    return redirect("pagamento_direto", token=order.public_token)


def _public_url(request, route_name, *args):
    path = reverse(route_name, args=args)
    if settings.PUBLIC_BASE_URL:
        return f"{settings.PUBLIC_BASE_URL}{path}"
    return request.build_absolute_uri(path)


def pagamento_direto(request, token):
    order = get_object_or_404(
        Order.objects.select_related("customer", "pickup_slot").prefetch_related(
            "items__product"
        ),
        public_token=token,
    )
    if order.payment_confirmed:
        return redirect("pedido_sucesso", token=order.public_token)

    phone = "".join(character for character in order.customer.phone if character.isdigit())
    if not phone.startswith("55"):
        phone = f"55{phone}"

    checkout_payload = {
        "handle": settings.INFINITEPAY_HANDLE,
        "redirect_url": _public_url(request, "pedido_sucesso", order.public_token),
        "order_nsu": str(order.public_token),
        "customer": {
            "name": order.customer.name,
            "phone_number": f"+{phone}",
        },
        "items": [
            {
                "quantity": item.quantity,
                "price": int(item.unit_price * 100),
                "description": item.product.name,
            }
            for item in order.items.all()
        ],
    }
    return render(
        request,
        "loja/pagamento.html",
        {
            "order": order,
            "checkout_payload": checkout_payload,
            "checkout_api_url": f"{settings.INFINITEPAY_API_BASE}/links",
        },
    )


@require_POST
def iniciar_pagamento(request, token):
    order = get_object_or_404(Order, public_token=token)
    if order.payment_confirmed:
        messages.success(request, "Este pedido já está pago.")
        return redirect("pedido_sucesso", token=order.public_token)
    return redirect("pagamento_direto", token=order.public_token)


def pedido_sucesso(request, token):
    order = get_object_or_404(
        Order.objects.select_related("customer", "pickup_slot").prefetch_related("items__product"),
        public_token=token,
    )
    lines = [f"Olá! Fiz o pedido #{order.pk} pelo site:"]
    lines.extend(
        f"• {item.quantity}x {item.product.name} — R$ {item.subtotal:.2f}"
        for item in order.items.all()
    )
    lines.extend(
        [
            f"Total: R$ {order.total:.2f}",
            f"Retirada: {order.pickup_slot}",
            f"Pagamento: {order.get_payment_method_display()}",
        ]
    )
    if order.notes:
        lines.append(f"Observações: {order.notes}")
    whatsapp_url = f"https://wa.me/{settings.COOKIE_WHATSAPP_NUMBER}?text={quote(chr(10).join(lines))}"
    return render(
        request,
        "loja/sucesso.html",
        {
            "order": order,
            "whatsapp_url": whatsapp_url,
            "returned_from_payment": bool(
                request.GET.get("transaction_nsu")
                or request.GET.get("capture_method")
                or request.GET.get("slug")
            ),
        },
    )


@login_required
def gestao_inicio(request):
    return redirect("gestao_pedidos")


def _management_whatsapp_url(order):
    phone = "".join(character for character in order.customer.phone if character.isdigit())
    if not phone.startswith("55"):
        phone = f"55{phone}"
    message = "\n".join(
        [
            f"Olá, {order.customer.name}! Aqui é da Oh! Meu Cookie 🍪",
            f"Estou entrando em contato sobre o pedido #{order.pk}.",
            f"Retirada: {order.pickup_slot}",
            f"Total: R$ {order.total:.2f}",
        ]
    )
    return f"https://wa.me/{phone}?text={quote(message)}"


@login_required
def gestao_pedidos(request):
    if request.method == "POST":
        order = get_object_or_404(Order, pk=request.POST.get("order_id"))
        action = request.POST.get("action", "legacy_update")

        if action == "confirm_payment":
            if request.POST.get("payment_checked") != "yes":
                messages.error(
                    request,
                    "Marque que conferiu o recebimento no app InfinitePay.",
                )
            elif order.status in {Order.Status.CANCELLED, Order.Status.COMPLETED}:
                messages.error(request, "Este pedido não pode mais ter o pagamento alterado.")
            else:
                order.payment_confirmed = True
                order.paid_at = order.paid_at or timezone.now()
                if order.status == Order.Status.NEW:
                    order.status = Order.Status.CONFIRMED
                order.save(
                    update_fields=["status", "payment_confirmed", "paid_at", "updated_at"]
                )
                messages.success(request, f"Pagamento do pedido #{order.pk} confirmado.")
        elif action == "advance":
            next_status = {
                Order.Status.CONFIRMED: Order.Status.PREPARING,
                Order.Status.PREPARING: Order.Status.READY,
                Order.Status.READY: Order.Status.COMPLETED,
            }.get(order.status)
            if not order.payment_confirmed:
                messages.error(
                    request,
                    "Confira e confirme o pagamento antes de avançar o pedido.",
                )
            elif next_status is None:
                messages.error(request, "Este pedido não possui uma próxima etapa.")
            else:
                order.status = next_status
                order.save(update_fields=["status", "updated_at"])
                messages.success(
                    request,
                    f"Pedido #{order.pk}: {order.get_status_display()}.",
                )
        elif action == "cancel":
            if order.status == Order.Status.COMPLETED:
                messages.error(request, "Um pedido já retirado não pode ser cancelado.")
            else:
                order.status = Order.Status.CANCELLED
                order.save(update_fields=["status", "updated_at"])
                messages.success(request, f"Pedido #{order.pk} cancelado.")
        else:
            # Mantém compatibilidade com a versão anterior e com formulários já abertos.
            status = request.POST.get("status")
            payment_confirmed = request.POST.get("payment_confirmed") == "on"
            if status not in Order.Status.values:
                messages.error(request, "Status inválido.")
            elif (
                not payment_confirmed
                and status
                in {
                    Order.Status.CONFIRMED,
                    Order.Status.PREPARING,
                    Order.Status.READY,
                    Order.Status.COMPLETED,
                }
            ):
                messages.error(
                    request,
                    "Confira o recebimento no app InfinitePay e marque o pagamento como confirmado.",
                )
            else:
                order.payment_confirmed = payment_confirmed
                order.paid_at = (order.paid_at or timezone.now()) if payment_confirmed else None
                order.status = (
                    Order.Status.CONFIRMED
                    if payment_confirmed and status == Order.Status.NEW
                    else status
                )
                order.save(
                    update_fields=[
                        "status",
                        "payment_confirmed",
                        "paid_at",
                        "updated_at",
                    ]
                )
                messages.success(request, f"Pedido #{order.pk} atualizado.")
        return redirect("gestao_pedidos")

    today = timezone.localdate()
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    payment_filter = request.GET.get("payment", "").strip()
    pickup_date_value = request.GET.get("pickup_date", "").strip()
    pickup_date_filter = parse_date(pickup_date_value) if pickup_date_value else None

    if status_filter not in Order.Status.values:
        status_filter = ""
    if payment_filter not in {"pending", "paid"}:
        payment_filter = ""

    all_orders = Order.objects.all()
    summary = all_orders.aggregate(
        new=Count("pk", filter=Q(status=Order.Status.NEW)),
        payment_pending=Count(
            "pk",
            filter=Q(payment_confirmed=False)
            & ~Q(status__in=[Order.Status.CANCELLED, Order.Status.COMPLETED]),
        ),
        preparing=Count("pk", filter=Q(status=Order.Status.PREPARING)),
        ready=Count("pk", filter=Q(status=Order.Status.READY)),
        today=Count(
            "pk",
            filter=Q(pickup_slot__pickup_date=today)
            & ~Q(status=Order.Status.CANCELLED),
        ),
    )

    orders = Order.objects.select_related("customer", "pickup_slot").prefetch_related(
        "items__product"
    )
    if query:
        filters = Q(customer__name__icontains=query) | Q(customer__phone__icontains=query)
        if query.isdigit():
            filters |= Q(pk=int(query))
        orders = orders.filter(filters)
    if status_filter:
        orders = orders.filter(status=status_filter)
    if payment_filter:
        orders = orders.filter(payment_confirmed=payment_filter == "paid")
    if pickup_date_filter:
        orders = orders.filter(pickup_slot__pickup_date=pickup_date_filter)

    priority = {
        Order.Status.NEW: 0,
        Order.Status.CONFIRMED: 1,
        Order.Status.PREPARING: 2,
        Order.Status.READY: 3,
        Order.Status.COMPLETED: 4,
        Order.Status.CANCELLED: 5,
    }
    order_list = list(orders.order_by("-created_at")[:150])
    order_list.sort(
        key=lambda order: (
            order.pickup_slot.pickup_date < today,
            order.pickup_slot.pickup_date if order.pickup_slot.pickup_date >= today else today,
            priority.get(order.status, 9),
            order.pickup_slot.period,
        )
    )

    grouped_orders = []
    groups_by_date = {}
    for order in order_list:
        order.management_whatsapp_url = _management_whatsapp_url(order)
        order.pickup_is_today = order.pickup_slot.pickup_date == today
        order.pickup_is_overdue = (
            order.pickup_slot.pickup_date < today
            and order.status not in {Order.Status.COMPLETED, Order.Status.CANCELLED}
        )
        pickup_date = order.pickup_slot.pickup_date
        if pickup_date not in groups_by_date:
            group = {
                "date": pickup_date,
                "label": pickup_date_label(pickup_date),
                "is_today": pickup_date == today,
                "is_past": pickup_date < today,
                "orders": [],
            }
            groups_by_date[pickup_date] = group
            grouped_orders.append(group)
        groups_by_date[pickup_date]["orders"].append(order)

    return render(
        request,
        "gestao/pedidos.html",
        {
            "order_groups": grouped_orders,
            "statuses": Order.Status.choices,
            "query": query,
            "status_filter": status_filter,
            "payment_filter": payment_filter,
            "pickup_date_filter": pickup_date_value if pickup_date_filter else "",
            "has_filters": bool(
                query or status_filter or payment_filter or pickup_date_filter
            ),
            "summary": summary,
            "today": today,
        },
    )


@login_required
def gestao_agenda(request):
    form = PickupDateForm(request.POST or None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "remove_date":
            pickup_date = parse_date(request.POST.get("pickup_date", ""))
            if pickup_date:
                PickupSlot.objects.filter(pickup_date=pickup_date).update(active=False)
                messages.success(request, "Data removida do formulário de pedidos.")
            return redirect("gestao_agenda")
        if action == "add" and form.is_valid():
            pickup_date = form.cleaned_data["pickup_date"]
            PickupSlot.objects.filter(pickup_date=pickup_date).update(active=False)
            for period, location in pickup_options_for(pickup_date):
                PickupSlot.objects.update_or_create(
                    pickup_date=pickup_date,
                    period=period,
                    location=location,
                    defaults={"active": True},
                )
            messages.success(
                request,
                f"{pickup_date_label(pickup_date)} liberada com todos os horários.",
            )
            return redirect("gestao_agenda")

    slots = PickupSlot.objects.filter(
        active=True,
        pickup_date__gte=timezone.localdate(),
    ).order_by("pickup_date", "period")
    return render(
        request,
        "gestao/agenda.html",
        {
            "form": form,
            "slots": slots,
            "date_count": len({slot.pickup_date for slot in slots}),
        },
    )
