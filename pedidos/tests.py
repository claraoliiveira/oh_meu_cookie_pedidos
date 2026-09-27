import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Order, PickupSlot, Product


class PublicOrderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(name="Teste", price=Decimal("7.50"), active=True)
        cls.slot = PickupSlot.objects.create(
            pickup_date=timezone.localdate() + timedelta(days=2),
            period="14h às 18h",
            location="Balcão da loja",
        )

    def test_catalog_loads_without_stock_fields(self):
        response = self.client.get(reverse("catalogo"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teste")
        self.assertNotContains(response, "disponível(is)")
        self.assertNotIn("available_quantity", [field.name for field in Product._meta.fields])

    def test_valid_order_is_saved(self):
        response = self.client.post(
            reverse("finalizar_pedido"),
            {
                "name": "Clara",
                "phone": "(33) 99999-0000",
                "pickup_date": self.slot.pickup_date.isoformat(),
                "pickup_slot": self.slot.pk,
                "payment_method": Order.PaymentMethod.PIX,
                "notes": "Caprichar na embalagem",
                "items_json": json.dumps([{"product_id": self.product.pk, "quantity": 2}]),
            },
        )
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.total, Decimal("15.00"))
        self.assertEqual(order.items.get().quantity, 2)

    def test_inactive_slot_is_rejected(self):
        self.slot.active = False
        self.slot.save(update_fields=["active"])
        response = self.client.post(
            reverse("finalizar_pedido"),
            {
                "name": "Clara",
                "phone": "33999990000",
                "pickup_date": self.slot.pickup_date.isoformat(),
                "pickup_slot": self.slot.pk,
                "payment_method": Order.PaymentMethod.CARD,
                "items_json": json.dumps([{"product_id": self.product.pk, "quantity": 1}]),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)


class ManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("clara", password="senha-segura-123")

    def test_orders_page_requires_login(self):
        response = self.client.get(reverse("gestao_pedidos"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_manager_can_add_pickup_slot(self):
        self.client.force_login(self.user)
        pickup_date = timezone.localdate() + timedelta(days=3)
        response = self.client.post(
            reverse("gestao_agenda"),
            {
                "action": "add",
                "pickup_date": pickup_date.isoformat(),
                "period": "9h às 12h",
                "location": "Loja",
            },
        )
        self.assertRedirects(response, reverse("gestao_agenda"))
        self.assertTrue(PickupSlot.objects.filter(pickup_date=pickup_date).exists())
