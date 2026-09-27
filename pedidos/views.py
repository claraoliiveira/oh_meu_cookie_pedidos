import json
import logging
import uuid
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import CheckoutForm, PickupDateForm
from .models import Customer, Order, OrderItem, PickupSlot, Product
from .payments import PaymentGatewayError, create_checkout, verify_payment
from .pickup_schedule import PICKUP_SCHEDULES, pickup_date_label, pickup_options_for


logger = logging.getLogger(__name__)


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

    try:
        return redirect(create_checkout(order, request))
    except PaymentGatewayError as exc:
        messages.error(request, str(exc))
        return redirect("pedido_sucesso", token=order.public_token)


@require_POST
def iniciar_pagamento(request, token):
    order = get_object_or_404(
        Order.objects.select_related("customer").prefetch_related("items__product"),
        public_token=token,
    )
    if order.payment_confirmed:
        messages.success(request, "Este pedido já está pago.")
        return redirect("pedido_sucesso", token=order.public_token)
    try:
        checkout_url = order.checkout_url or create_checkout(order, request)
        return redirect(checkout_url)
    except PaymentGatewayError as exc:
        messages.error(request, str(exc))
        return redirect("pedido_sucesso", token=order.public_token)


def pagamento_retorno(request, token):
    order = get_object_or_404(Order, public_token=token)
    order_nsu = request.GET.get("order_nsu", "")
    transaction_nsu = request.GET.get("transaction_nsu", "")
    slug = request.GET.get("slug", "")

    if order_nsu and order_nsu != str(order.public_token):
        messages.error(request, "O retorno do pagamento não pertence a este pedido.")
        return redirect("pedido_sucesso", token=order.public_token)

    try:
        verify_payment(order, transaction_nsu, slug)
        messages.success(request, "Pagamento aprovado! Seu pedido foi confirmado.")
    except PaymentGatewayError as exc:
        messages.error(request, str(exc))
    return redirect("pedido_sucesso", token=order.public_token)


@csrf_exempt
@require_POST
def infinitepay_webhook(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse(
            {"success": False, "message": "JSON inválido"},
            status=400,
        )

    if not isinstance(payload, dict):
        return JsonResponse(
            {"success": False, "message": "Conteúdo inválido"},
            status=400,
        )

    order_nsu = str(payload.get("order_nsu", ""))
    transaction_nsu = str(payload.get("transaction_nsu", ""))
    slug = str(payload.get("invoice_slug", ""))
    try:
        public_token = uuid.UUID(order_nsu)
    except (ValueError, AttributeError):
        public_token = None
    order = Order.objects.filter(public_token=public_token).first() if public_token else None
    if not order:
        return JsonResponse(
            {"success": False, "message": "Pedido não encontrado"},
            status=400,
        )

    try:
        informed_amount = int(payload.get("amount"))
    except (TypeError, ValueError):
        informed_amount = -1
    expected_amount = int(order.total * 100)
    if informed_amount != expected_amount:
        logger.warning("Webhook com valor divergente para o pedido %s", order.pk)
        return JsonResponse(
            {"success": False, "message": "Valor divergente"},
            status=400,
        )

    try:
        verify_payment(order, transaction_nsu, slug)
    except PaymentGatewayError as exc:
        logger.warning("Pagamento do pedido %s não confirmado: %s", order.pk, exc)
        return JsonResponse({"success": False, "message": str(exc)}, status=400)

    return JsonResponse({"success": True, "message": None})


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
        elif (
            not order.payment_confirmed
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
                "Aguarde a confirmação automática do pagamento antes de avançar o pedido.",
            )
        else:
            order.status = status
            order.save(update_fields=["status", "updated_at"])
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
