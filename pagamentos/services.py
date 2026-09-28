from urllib.parse import urljoin
import requests
from django.conf import settings
from .adapters import build_items, get_customer

class InfinitePayError(Exception):
    pass

def api_base():
    return getattr(settings, "INFINITEPAY_API_BASE", "https://api.checkout.infinitepay.io").rstrip("/")

def handle():
    value = getattr(settings, "INFINITEPAY_HANDLE", "").strip()
    if not value:
        raise InfinitePayError("INFINITEPAY_HANDLE não foi configurado.")
    return value.lstrip("$")

def create_checkout(*, order, order_nsu, redirect_url, webhook_url, timeout=15):
    payload = {
        "handle": handle(),
        "redirect_url": redirect_url,
        "webhook_url": webhook_url,
        "order_nsu": str(order_nsu),
        "items": build_items(order),
    }
    customer = get_customer(order)
    if customer:
        payload["customer"] = customer

    try:
        response = requests.post(
            f"{api_base()}/links",
            json=payload,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
    except requests.RequestException as exc:
        raise InfinitePayError(
            "Não foi possível conectar à InfinitePay. "
            "No PythonAnywhere gratuito, confirme se api.checkout.infinitepay.io "
            "já foi liberado na allowlist."
        ) from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not response.ok:
        detail = data if data else response.text[:500]
        raise InfinitePayError(f"InfinitePay retornou HTTP {response.status_code}: {detail}")

    url = data.get("url")
    if not url:
        raise InfinitePayError("A InfinitePay respondeu sem a URL do checkout.")
    return url, data

def check_payment(*, order_nsu, transaction_nsu, slug, timeout=15):
    payload = {
        "handle": handle(),
        "order_nsu": str(order_nsu),
        "transaction_nsu": str(transaction_nsu),
        "slug": str(slug),
    }

    try:
        response = requests.post(
            f"{api_base()}/payment_check",
            json=payload,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
    except requests.RequestException as exc:
        raise InfinitePayError("Não foi possível consultar o pagamento na InfinitePay.") from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not response.ok:
        detail = data if data else response.text[:500]
        raise InfinitePayError(f"Falha na verificação: HTTP {response.status_code}: {detail}")
    return data
