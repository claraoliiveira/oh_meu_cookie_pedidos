from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CheckoutForm, PickupSlotForm
from .models import Customer, Order, OrderItem, PickupSlot, Product


def _catalog_context(form=None):
    slots = list(
        PickupSlot.objects.filter(
            active=True,
            pickup_date__gte=timezone.localdate(),
        ).order_by("pickup_date", "period")
    )
    dates = []
    slots_by_date = {}
    for slot in slots:
        key = slot.pickup_date.isoformat()
        if key not in slots_by_date:
            dates.append({"value": key, "label": slot.pickup_date.strftime("%d/%m/%Y")})
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


@transaction.atomic
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
    return redirect("pedido_sucesso", token=order.public_token)


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
        {"order": order, "whatsapp_url": whatsapp_url},
    )


@login_required
def gestao_inicio(request):
    return redirect("gestao_pedidos")


@login_required
def gestao_pedidos(request):
    if request.method == "POST":
        order = get_object_or_404(Order, pk=request.POST.get("order_id"))
        status = request.POST.get("status")
        if status not in Order.Status.values:
            messages.error(request, "Status inválido.")
        else:
            order.status = status
            order.payment_confirmed = request.POST.get("payment_confirmed") == "on"
            order.save(update_fields=["status", "payment_confirmed", "updated_at"])
            messages.success(request, f"Pedido #{order.pk} atualizado.")
        return redirect("gestao_pedidos")

    query = request.GET.get("q", "").strip()
    orders = Order.objects.select_related("customer", "pickup_slot").prefetch_related("items__product")
    if query:
        filters = Q(customer__name__icontains=query) | Q(customer__phone__icontains=query)
        if query.isdigit():
            filters |= Q(pk=int(query))
        orders = orders.filter(filters)
    return render(
        request,
        "gestao/pedidos.html",
        {
            "orders": orders[:150],
            "statuses": Order.Status.choices,
            "query": query,
        },
    )


@login_required
def gestao_agenda(request):
    form = PickupSlotForm(request.POST or None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "remove":
            slot = get_object_or_404(PickupSlot, pk=request.POST.get("slot_id"))
            slot.active = False
            slot.save(update_fields=["active"])
            messages.success(request, "Opção removida do formulário de pedidos.")
            return redirect("gestao_agenda")
        if action == "add" and form.is_valid():
            form.save()
            messages.success(request, "Nova opção de retirada liberada.")
            return redirect("gestao_agenda")

    slots = PickupSlot.objects.filter(
        active=True,
        pickup_date__gte=timezone.localdate(),
    ).order_by("pickup_date", "period")
    return render(
        request,
        "gestao/agenda.html",
        {"form": form, "slots": slots},
    )
