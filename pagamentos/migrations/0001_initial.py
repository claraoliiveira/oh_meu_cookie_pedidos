from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PagamentoInfinitePay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pedido_id", models.PositiveBigIntegerField(db_index=True)),
                ("order_nsu", models.CharField(db_index=True, max_length=100, unique=True)),
                ("valor_esperado_centavos", models.PositiveBigIntegerField(default=0)),
                ("status", models.CharField(choices=[("criado","Criado"),("aguardando","Aguardando pagamento"),("pago","Pago"),("erro","Erro")], default="criado", max_length=20)),
                ("checkout_url", models.URLField(blank=True, max_length=1000)),
                ("transaction_nsu", models.CharField(blank=True, db_index=True, max_length=200)),
                ("invoice_slug", models.CharField(blank=True, max_length=200)),
                ("receipt_url", models.URLField(blank=True, max_length=1000)),
                ("capture_method", models.CharField(blank=True, max_length=50)),
                ("installments", models.PositiveIntegerField(blank=True, null=True)),
                ("paid_amount_centavos", models.PositiveBigIntegerField(blank=True, null=True)),
                ("ultimo_erro", models.TextField(blank=True)),
                ("payload_retorno", models.JSONField(blank=True, default=dict)),
                ("payload_webhook", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("pago_em", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Pagamento InfinitePay",
                "verbose_name_plural": "Pagamentos InfinitePay",
                "ordering": ["-criado_em"],
            },
        ),
    ]
