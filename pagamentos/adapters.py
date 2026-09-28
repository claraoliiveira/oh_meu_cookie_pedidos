from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

TOTAL_CANDIDATES = ("valor_total", "total", "total_price", "valor", "amount")
NAME_CANDIDATES = ("nome", "nome_cliente", "customer_name", "cliente_nome")
EMAIL_CANDIDATES = ("email", "email_cliente", "customer_email")
PHONE_CANDIDATES = ("telefone", "telefone_cliente", "phone", "whatsapp")

def get_order_model():
    label = getattr(settings, "INFINITEPAY_ORDER_MODEL", "negocio.Pedido")
    try:
        app_label, model_name = label.split(".", 1)
        return apps.get_model(app_label, model_name)
    except Exception as exc:
        raise ImproperlyConfigured(
            f'Não foi possível carregar INFINITEPAY_ORDER_MODEL="{label}".'
        ) from exc

def get_order(pk):
    model = get_order_model()
    return model.objects.get(pk=pk)

def _read(obj, candidates, default=None):
    for name in candidates:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value not in (None, ""):
                return value
    return default

def get_total_decimal(order):
    forced = getattr(settings, "INFINITEPAY_TOTAL_FIELD", "")
    candidates = (forced,) + TOTAL_CANDIDATES if forced else TOTAL_CANDIDATES
    value = _read(order, candidates)
    if value is None:
        raise ValueError(
            "Não encontrei o valor total do pedido. "
            "Defina INFINITEPAY_TOTAL_FIELD no settings.py."
        )
    try:
        total = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Valor total inválido no pedido: {value!r}") from exc
    if total <= 0:
        raise ValueError("O valor total do pedido deve ser maior que zero.")
    return total

def get_total_cents(order):
    return int(get_total_decimal(order) * 100)

def get_customer(order):
    customer = {}
    name = _read(order, NAME_CANDIDATES)
    email = _read(order, EMAIL_CANDIDATES)
    phone = _read(order, PHONE_CANDIDATES)

    if name:
        customer["name"] = str(name).strip()
    if email:
        customer["email"] = str(email).strip()
    if phone:
        digits = "".join(ch for ch in str(phone) if ch.isdigit())
        if digits:
            if not digits.startswith("55"):
                digits = "55" + digits
            customer["phone_number"] = "+" + digits
    return customer

def build_items(order):
    # Integração universal: envia o pedido inteiro como um único item.
    # Assim funciona mesmo que o projeto use estruturas diferentes para itens.
    return [{
        "quantity": 1,
        "price": get_total_cents(order),
        "description": f"Oh! Meu Cookie - Pedido #{order.pk}",
    }]

def mark_order_paid(order):
    """
    Atualiza campos comuns, sem exigir mudanças no modelo existente.
    O registro PagamentoInfinitePay continua sendo a fonte da confirmação
    mesmo quando nenhum desses campos existir no Pedido.
    """
    changed = []

    if hasattr(order, "pago"):
        try:
            setattr(order, "pago", True)
            changed.append("pago")
        except Exception:
            pass

    for field_name in ("status_pagamento", "payment_status"):
        if hasattr(order, field_name):
            try:
                setattr(order, field_name, "Pago")
                changed.append(field_name)
            except Exception:
                pass

    # Só tenta status se "Pago" for opção válida ou campo livre.
    try:
        field = order._meta.get_field("status")
        choices = dict(field.flatchoices or [])
        if choices:
            valid_values = {str(k) for k in choices.keys()}
            paid_value = next(
                (k for k, v in choices.items() if str(v).strip().lower() == "pago"),
                None
            )
            if paid_value is not None:
                setattr(order, "status", paid_value)
                changed.append("status")
        else:
            setattr(order, "status", "Pago")
            changed.append("status")
    except Exception:
        pass

    if changed:
        order.save(update_fields=list(dict.fromkeys(changed)))
