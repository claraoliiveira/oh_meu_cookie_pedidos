from django.contrib import admin
from .models import PagamentoInfinitePay

@admin.register(PagamentoInfinitePay)
class PagamentoInfinitePayAdmin(admin.ModelAdmin):
    list_display = (
        "pedido_id", "order_nsu", "status", "capture_method",
        "paid_amount_centavos", "criado_em", "pago_em",
    )
    list_filter = ("status", "capture_method", "criado_em")
    search_fields = ("order_nsu", "transaction_nsu", "invoice_slug", "pedido_id")
    readonly_fields = (
        "order_nsu", "checkout_url", "transaction_nsu", "invoice_slug",
        "receipt_url", "payload_retorno", "payload_webhook",
        "criado_em", "atualizado_em", "pago_em",
    )
