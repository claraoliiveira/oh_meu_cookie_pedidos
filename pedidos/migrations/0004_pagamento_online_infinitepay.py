from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pedidos", "0003_padronizar_agenda"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("PIX", "Pix online"),
                    ("CARTAO", "Cartão de crédito online"),
                ],
                max_length=10,
                verbose_name="forma de pagamento",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="checkout_url",
            field=models.URLField(blank=True, verbose_name="link do checkout"),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_capture_method",
            field=models.CharField(
                blank=True,
                max_length=30,
                verbose_name="meio confirmado pela InfinitePay",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_installments",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name="parcelas",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_slug",
            field=models.CharField(
                blank=True,
                max_length=120,
                verbose_name="código da cobrança",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_transaction_nsu",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=120,
                verbose_name="identificador da transação",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="paid_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="pago em",
            ),
        ),
    ]
