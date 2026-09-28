from django.db import models

class PagamentoInfinitePay(models.Model):
    STATUS_CHOICES = [
        ("criado", "Criado"),
        ("aguardando", "Aguardando pagamento"),
        ("pago", "Pago"),
        ("erro", "Erro"),
    ]

    pedido_id = models.PositiveBigIntegerField(db_index=True)
    order_nsu = models.CharField(max_length=100, unique=True, db_index=True)
    valor_esperado_centavos = models.PositiveBigIntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="criado")
    checkout_url = models.URLField(max_length=1000, blank=True)
    transaction_nsu = models.CharField(max_length=200, blank=True, db_index=True)
    invoice_slug = models.CharField(max_length=200, blank=True)
    receipt_url = models.URLField(max_length=1000, blank=True)
    capture_method = models.CharField(max_length=50, blank=True)
    installments = models.PositiveIntegerField(null=True, blank=True)
    paid_amount_centavos = models.PositiveBigIntegerField(null=True, blank=True)

    ultimo_erro = models.TextField(blank=True)
    payload_retorno = models.JSONField(default=dict, blank=True)
    payload_webhook = models.JSONField(default=dict, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    pago_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Pagamento InfinitePay"
        verbose_name_plural = "Pagamentos InfinitePay"

    def __str__(self):
        return f"Pedido {self.pedido_id} - {self.get_status_display()}"
