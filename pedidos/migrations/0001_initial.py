import uuid
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="nome")),
                ("phone", models.CharField(max_length=30, unique=True, verbose_name="WhatsApp")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "cliente", "verbose_name_plural": "clientes", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="PickupSlot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pickup_date", models.DateField(db_index=True, verbose_name="data")),
                ("period", models.CharField(max_length=100, verbose_name="horário")),
                ("location", models.CharField(max_length=180, verbose_name="local")),
                ("active", models.BooleanField(default=True, verbose_name="disponível")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "opção de retirada", "verbose_name_plural": "opções de retirada", "ordering": ["pickup_date", "period", "location"]},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="produto")),
                ("description", models.TextField(blank=True, verbose_name="descrição")),
                ("price", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))], verbose_name="preço")),
                ("active", models.BooleanField(default=True, verbose_name="disponível no cardápio")),
                ("featured", models.BooleanField(default=False, verbose_name="destaque")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="ordem")),
            ],
            options={"verbose_name": "produto", "verbose_name_plural": "produtos", "ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("status", models.CharField(choices=[("NOVO", "Novo"), ("CONFIRMADO", "Confirmado"), ("EM_PREPARO", "Em preparo"), ("PRONTO", "Pronto para retirada"), ("CONCLUIDO", "Concluído"), ("CANCELADO", "Cancelado")], db_index=True, default="NOVO", max_length=20, verbose_name="status")),
                ("payment_method", models.CharField(choices=[("PIX", "Pix"), ("CARTAO", "Cartão")], max_length=10, verbose_name="forma de pagamento")),
                ("payment_confirmed", models.BooleanField(default=False, verbose_name="pagamento confirmado")),
                ("notes", models.TextField(blank=True, verbose_name="observações")),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="total")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="pedidos.customer", verbose_name="cliente")),
                ("pickup_slot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="pedidos.pickupslot", verbose_name="retirada")),
            ],
            options={"verbose_name": "pedido", "verbose_name_plural": "pedidos", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name="quantidade")),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="valor unitário")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="pedidos.order", verbose_name="pedido")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="pedidos.product", verbose_name="produto")),
            ],
        ),
        migrations.AddConstraint(
            model_name="pickupslot",
            constraint=models.UniqueConstraint(fields=("pickup_date", "period", "location"), name="unique_pickup_slot"),
        ),
    ]
