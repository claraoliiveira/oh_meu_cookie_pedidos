import json
import uuid
from django.db import transaction
from django.http import JsonResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .adapters import get_order, get_total_cents, mark_order_paid
from .models import PagamentoInfinitePay
from .services import create_checkout, check_payment, InfinitePayError

def _absolute(request, name):
    return request.build_absolute_uri(reverse(name))

def _order_or_404(pk):
    try:
        return get_order(pk)
    except Exception as exc:
        raise Http404("Pedido não encontrado.") from exc

def iniciar_pagamento(request, pedido_id):
    order = _order_or_404(pedido_id)
    expected = get_total_cents(order)

    pagamento = PagamentoInfinitePay.objects.filter(
        pedido_id=order.pk,
        status__in=["criado", "aguardando"],
    ).order_by("-criado_em").first()

    if pagamento is None:
        pagamento = PagamentoInfinitePay.objects.create(
            pedido_id=order.pk,
            order_nsu=f"OMC-{order.pk}-{uuid.uuid4().hex[:12]}",
            valor_esperado_centavos=expected,
            status="criado",
        )
    else:
        pagamento.valor_esperado_centavos = expected
        pagamento.save(update_fields=["valor_esperado_centavos", "atualizado_em"])

    if pagamento.checkout_url:
        return redirect(pagamento.checkout_url)

    try:
        checkout_url, _ = create_checkout(
            order=order,
            order_nsu=pagamento.order_nsu,
            redirect_url=_absolute(request, "pagamentos:retorno"),
            webhook_url=_absolute(request, "pagamentos:webhook"),
        )
    except InfinitePayError as exc:
        pagamento.status = "erro"
        pagamento.ultimo_erro = str(exc)
        pagamento.save(update_fields=["status", "ultimo_erro", "atualizado_em"])
        return render(request, "pagamentos/erro.html", {
            "pedido": order,
            "erro": str(exc),
        }, status=502)

    pagamento.checkout_url = checkout_url
    pagamento.status = "aguardando"
    pagamento.ultimo_erro = ""
    pagamento.save(update_fields=["checkout_url", "status", "ultimo_erro", "atualizado_em"])
    return redirect(checkout_url)

def retorno(request):
    order_nsu = request.GET.get("order_nsu", "").strip()
    transaction_nsu = request.GET.get("transaction_nsu", "").strip()
    slug = request.GET.get("slug", "").strip()
    receipt_url = request.GET.get("receipt_url", "").strip()
    capture_method = request.GET.get("capture_method", "").strip()

    if not order_nsu:
        return render(request, "pagamentos/aguardando.html", {
            "mensagem": "Recebemos seu retorno. Estamos aguardando a confirmação do pagamento."
        })

    pagamento = PagamentoInfinitePay.objects.filter(order_nsu=order_nsu).first()
    if not pagamento:
        return render(request, "pagamentos/erro.html", {
            "erro": "Não encontramos o pagamento correspondente a este pedido."
        }, status=404)

    pagamento.payload_retorno = dict(request.GET.items())
    if transaction_nsu:
        pagamento.transaction_nsu = transaction_nsu
    if slug:
        pagamento.invoice_slug = slug
    if receipt_url:
        pagamento.receipt_url = receipt_url
    if capture_method:
        pagamento.capture_method = capture_method
    pagamento.save()

    # Webhook pode já ter confirmado antes do cliente voltar.
    if pagamento.status == "pago":
        return render(request, "pagamentos/sucesso.html", {"pagamento": pagamento})

    if not (transaction_nsu and slug):
        return render(request, "pagamentos/aguardando.html", {
            "pagamento": pagamento,
            "mensagem": "O pagamento ainda está sendo confirmado."
        })

    try:
        data = check_payment(
            order_nsu=order_nsu,
            transaction_nsu=transaction_nsu,
            slug=slug,
        )
    except InfinitePayError:
        # Não mostra erro definitivo para o comprador; webhook ainda pode chegar.
        return render(request, "pagamentos/aguardando.html", {
            "pagamento": pagamento,
            "mensagem": "Pagamento recebido. A confirmação automática ainda está sendo processada."
        })

    paid = bool(data.get("success")) and bool(data.get("paid"))
    amount = int(data.get("amount") or 0)

    if paid and amount == pagamento.valor_esperado_centavos:
        with transaction.atomic():
            pagamento.status = "pago"
            pagamento.paid_amount_centavos = int(data.get("paid_amount") or amount)
            pagamento.installments = data.get("installments")
            pagamento.capture_method = data.get("capture_method") or pagamento.capture_method
            pagamento.pago_em = timezone.now()
            pagamento.ultimo_erro = ""
            pagamento.save()

            try:
                order = get_order(pagamento.pedido_id)
                mark_order_paid(order)
            except Exception:
                pass

        return render(request, "pagamentos/sucesso.html", {"pagamento": pagamento})

    if paid and amount != pagamento.valor_esperado_centavos:
        pagamento.ultimo_erro = (
            f"Valor divergente. Esperado={pagamento.valor_esperado_centavos}; recebido={amount}"
        )
        pagamento.save(update_fields=["ultimo_erro", "atualizado_em"])

    return render(request, "pagamentos/aguardando.html", {
        "pagamento": pagamento,
        "mensagem": "Ainda não recebemos a confirmação final do pagamento."
    })

@csrf_exempt
@require_POST
def webhook(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"success": False, "message": "JSON inválido"}, status=400)

    order_nsu = str(payload.get("order_nsu") or "").strip()
    if not order_nsu:
        return JsonResponse({"success": False, "message": "order_nsu ausente"}, status=400)

    pagamento = PagamentoInfinitePay.objects.filter(order_nsu=order_nsu).first()
    if not pagamento:
        return JsonResponse({"success": False, "message": "Pedido não encontrado"}, status=400)

    try:
        amount = int(payload.get("amount"))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "message": "Valor inválido"}, status=400)

    if amount != pagamento.valor_esperado_centavos:
        pagamento.payload_webhook = payload
        pagamento.ultimo_erro = (
            f"Webhook com valor divergente. Esperado={pagamento.valor_esperado_centavos}; "
            f"recebido={amount}"
        )
        pagamento.save(update_fields=["payload_webhook", "ultimo_erro", "atualizado_em"])
        return JsonResponse({"success": False, "message": "Valor divergente"}, status=400)

    with transaction.atomic():
        pagamento.payload_webhook = payload
        pagamento.transaction_nsu = str(payload.get("transaction_nsu") or "")
        pagamento.invoice_slug = str(payload.get("invoice_slug") or "")
        pagamento.receipt_url = str(payload.get("receipt_url") or "")
        pagamento.capture_method = str(payload.get("capture_method") or "")
        pagamento.installments = payload.get("installments")
        pagamento.paid_amount_centavos = int(payload.get("paid_amount") or amount)
        pagamento.status = "pago"
        pagamento.pago_em = pagamento.pago_em or timezone.now()
        pagamento.ultimo_erro = ""
        pagamento.save()

        try:
            order = get_order(pagamento.pedido_id)
            mark_order_paid(order)
        except Exception:
            pass

    return JsonResponse({"success": True, "message": None})
