import logging
from decimal import Decimal
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import Order


logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    """Erro seguro e apresentável da comunicação com a InfinitePay."""


def _money_to_cents(value):
    return int((Decimal(value) * 100).quantize(Decimal("1")))


def _public_url(request, route_name, *args):
    path = reverse(route_name, args=args)
    base_url = settings.PUBLIC_BASE_URL
    if base_url:
        return f"{base_url}{path}"
    return request.build_absolute_uri(path)


def _post_json(path, payload):
    try:
        response = requests.post(
            f"{settings.INFINITEPAY_API_BASE}{path}",
            json=payload,
            timeout=settings.INFINITEPAY_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.exception("Falha na comunicação com a InfinitePay")
        raise PaymentGatewayError(
            "Não foi possível acessar o pagamento agora. Tente novamente em instantes."
        ) from exc

    if not isinstance(data, dict):
        raise PaymentGatewayError("A InfinitePay enviou uma resposta inválida.")
    return data


def _checkout_url_is_safe(url):
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and (hostname == "checkout.infinitepay.com.br" or hostname.endswith(".infinitepay.com.br"))
    )


def create_checkout(order, request):
    if not settings.INFINITEPAY_HANDLE:
        raise PaymentGatewayError("O pagamento online ainda não foi configurado pela loja.")
    if order.payment_confirmed:
        raise PaymentGatewayError("Este pedido já está pago.")

    phone = "".join(character for character in order.customer.phone if character.isdigit())
    if not phone.startswith("55"):
        phone = f"55{phone}"

    payload = {
        "handle": settings.INFINITEPAY_HANDLE,
        "redirect_url": _public_url(request, "pagamento_retorno", order.public_token),
        "webhook_url": _public_url(request, "infinitepay_webhook"),
        "order_nsu": str(order.public_token),
        "customer": {
            "name": order.customer.name,
            "phone_number": f"+{phone}",
        },
        "items": [
            {
                "quantity": item.quantity,
                "price": _money_to_cents(item.unit_price),
                "description": item.product.name,
            }
            for item in order.items.select_related("product")
        ],
    }
    data = _post_json("/links", payload)
    checkout_url = data.get("url", "")
    if not _checkout_url_is_safe(checkout_url):
        raise PaymentGatewayError("A InfinitePay não devolveu um link de pagamento válido.")

    order.checkout_url = checkout_url
    order.save(update_fields=["checkout_url", "updated_at"])
    return checkout_url


def verify_payment(order, transaction_nsu, slug):
    if not settings.INFINITEPAY_HANDLE:
        raise PaymentGatewayError("A integração da InfinitePay não está configurada.")
    if not transaction_nsu or not slug:
        raise PaymentGatewayError("Faltam dados para confirmar o pagamento.")

    if order.payment_confirmed:
        if order.payment_transaction_nsu and order.payment_transaction_nsu != transaction_nsu:
            raise PaymentGatewayError("O pedido já possui outra transação confirmada.")
        return order

    data = _post_json(
        "/payment_check",
        {
            "handle": settings.INFINITEPAY_HANDLE,
            "order_nsu": str(order.public_token),
            "transaction_nsu": transaction_nsu,
            "slug": slug,
        },
    )

    if data.get("success") is not True or data.get("paid") is not True:
        raise PaymentGatewayError("O pagamento ainda não foi aprovado pela InfinitePay.")

    try:
        confirmed_amount = int(data.get("amount"))
    except (TypeError, ValueError) as exc:
        raise PaymentGatewayError("A InfinitePay não confirmou o valor do pedido.") from exc
    if confirmed_amount != _money_to_cents(order.total):
        logger.error("Valor divergente no pedido %s", order.pk)
        raise PaymentGatewayError("O valor confirmado é diferente do total do pedido.")

    capture_method = data.get("capture_method", "")
    if capture_method not in {"pix", "credit_card"}:
        raise PaymentGatewayError("A forma de pagamento confirmada é inválida.")

    try:
        installments = int(data.get("installments") or 1)
    except (TypeError, ValueError):
        installments = 1

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.payment_confirmed:
            if (
                locked_order.payment_transaction_nsu
                and locked_order.payment_transaction_nsu != transaction_nsu
            ):
                raise PaymentGatewayError("O pedido já possui outra transação confirmada.")
            return locked_order

        locked_order.payment_confirmed = True
        locked_order.payment_transaction_nsu = transaction_nsu
        locked_order.payment_slug = slug
        locked_order.payment_capture_method = capture_method
        locked_order.payment_installments = max(1, installments)
        locked_order.paid_at = timezone.now()
        locked_order.payment_method = (
            Order.PaymentMethod.PIX
            if capture_method == "pix"
            else Order.PaymentMethod.CARD
        )
        if locked_order.status == Order.Status.NEW:
            locked_order.status = Order.Status.CONFIRMED
        locked_order.save(
            update_fields=[
                "payment_confirmed",
                "payment_transaction_nsu",
                "payment_slug",
                "payment_capture_method",
                "payment_installments",
                "paid_at",
                "payment_method",
                "status",
                "updated_at",
            ]
        )
    return locked_order
