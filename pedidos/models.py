import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Product(models.Model):
    name = models.CharField("produto", max_length=150)
    description = models.TextField("descrição", blank=True)
    price = models.DecimalField(
        "preço",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    active = models.BooleanField("disponível no cardápio", default=True)
    featured = models.BooleanField("destaque", default=False)
    sort_order = models.PositiveSmallIntegerField("ordem", default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "produto"
        verbose_name_plural = "produtos"

    def __str__(self):
        return self.name


class PickupSlot(models.Model):
    pickup_date = models.DateField("data", db_index=True)
    period = models.CharField("horário", max_length=100)
    location = models.CharField("local", max_length=180)
    active = models.BooleanField("disponível", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pickup_date", "period", "location"]
        constraints = [
            models.UniqueConstraint(
                fields=["pickup_date", "period", "location"],
                name="unique_pickup_slot",
            )
        ]
        verbose_name = "opção de retirada"
        verbose_name_plural = "opções de retirada"

    @property
    def is_available(self):
        return self.active and self.pickup_date >= timezone.localdate()

    def __str__(self):
        return f"{self.pickup_date:%d/%m/%Y} — {self.period} · {self.location}"


class Customer(models.Model):
    name = models.CharField("nome", max_length=120)
    phone = models.CharField("WhatsApp", max_length=30, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return f"{self.name} — {self.phone}"


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "NOVO", "Novo"
        CONFIRMED = "CONFIRMADO", "Confirmado"
        PREPARING = "EM_PREPARO", "Em preparo"
        READY = "PRONTO", "Pronto para retirada"
        COMPLETED = "CONCLUIDO", "Concluído"
        CANCELLED = "CANCELADO", "Cancelado"

    class PaymentMethod(models.TextChoices):
        PIX = "PIX", "Pix"
        CARD = "CARTAO", "Cartão"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="cliente",
    )
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    pickup_slot = models.ForeignKey(
        PickupSlot,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="retirada",
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    payment_method = models.CharField(
        "forma de pagamento",
        max_length=10,
        choices=PaymentMethod.choices,
    )
    payment_confirmed = models.BooleanField("pagamento confirmado", default=False)
    notes = models.TextField("observações", blank=True)
    total = models.DecimalField("total", max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"

    def recalculate_total(self, save=True):
        self.total = sum((item.subtotal for item in self.items.all()), Decimal("0"))
        if save:
            self.save(update_fields=["total", "updated_at"])
        return self.total

    def __str__(self):
        return f"Pedido #{self.pk} — {self.customer.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="pedido",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="produto",
    )
    quantity = models.PositiveIntegerField("quantidade", validators=[MinValueValidator(1)])
    unit_price = models.DecimalField("valor unitário", max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
