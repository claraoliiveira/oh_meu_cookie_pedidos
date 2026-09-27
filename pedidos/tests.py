import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Customer, Order, OrderItem, PickupSlot, Product
from .pickup_schedule import HOME_ADDRESS, SCHOOL


def next_weekday(weekday):
    today = timezone.localdate()
    return today + timedelta(days=(weekday - today.weekday()) % 7)


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

    @override_settings(INFINITEPAY_HANDLE="clara-oliveira-cqv", PUBLIC_BASE_URL="https://loja.test")
    @patch("pedidos.payments.requests.post")
    def test_order_redirects_to_secure_infinitepay_checkout(self, mocked_post):
        gateway_response = Mock()
        gateway_response.raise_for_status.return_value = None
        gateway_response.json.return_value = {
            "url": "https://checkout.infinitepay.com.br/clara-oliveira-cqv?lenc=teste"
        }
        mocked_post.return_value = gateway_response

        response = self.client.post(
            reverse("finalizar_pedido"),
            {
                "name": "Clara",
                "phone": "(33) 99999-0000",
                "pickup_date": self.slot.pickup_date.isoformat(),
                "pickup_slot": self.slot.pk,
                "payment_method": Order.PaymentMethod.PIX,
                "items_json": json.dumps([{"product_id": self.product.pk, "quantity": 2}]),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://checkout.infinitepay.com.br/"))
        sent_payload = mocked_post.call_args.kwargs["json"]
        self.assertEqual(sent_payload["handle"], "clara-oliveira-cqv")
        self.assertEqual(sent_payload["items"][0]["price"], 750)
        self.assertEqual(sent_payload["items"][0]["quantity"], 2)
        self.assertEqual(sent_payload["webhook_url"], "https://loja.test/pagamentos/infinitepay/webhook/")

    @override_settings(INFINITEPAY_HANDLE="clara-oliveira-cqv")
    @patch("pedidos.payments.requests.post")
    def test_payment_return_confirms_order_using_server_check(self, mocked_post):
        order_response = self.client.post(
            reverse("finalizar_pedido"),
            {
                "name": "Clara",
                "phone": "33999990000",
                "pickup_date": self.slot.pickup_date.isoformat(),
                "pickup_slot": self.slot.pk,
                "payment_method": Order.PaymentMethod.CARD,
                "items_json": json.dumps([{"product_id": self.product.pk, "quantity": 2}]),
            },
        )
        order = Order.objects.get()

        payment_check_response = Mock()
        payment_check_response.raise_for_status.return_value = None
        payment_check_response.json.return_value = {
            "success": True,
            "paid": True,
            "amount": 1500,
            "paid_amount": 1500,
            "installments": 1,
            "capture_method": "pix",
        }
        mocked_post.return_value = payment_check_response

        response = self.client.get(
            reverse("pagamento_retorno", args=[order.public_token]),
            {
                "order_nsu": str(order.public_token),
                "transaction_nsu": "transacao-123",
                "slug": "cobranca-123",
            },
        )

        self.assertEqual(order_response.status_code, 302)
        self.assertRedirects(response, reverse("pedido_sucesso", args=[order.public_token]))
        order.refresh_from_db()
        self.assertTrue(order.payment_confirmed)
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.payment_method, Order.PaymentMethod.PIX)
        self.assertEqual(order.payment_transaction_nsu, "transacao-123")
        self.assertIsNotNone(order.paid_at)

    def test_webhook_rejects_invalid_order_identifier(self):
        response = self.client.post(
            reverse("infinitepay_webhook"),
            data=json.dumps(
                {
                    "order_nsu": "nao-e-uuid",
                    "transaction_nsu": "transacao",
                    "invoice_slug": "slug",
                    "amount": 1500,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])


class ManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("clara", password="senha-segura-123")

    def test_orders_page_requires_login(self):
        response = self.client.get(reverse("gestao_pedidos"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_unpaid_order_cannot_be_manually_confirmed(self):
        self.client.force_login(self.user)
        product = Product.objects.create(name="Cookie", price=Decimal("3.00"))
        slot = PickupSlot.objects.create(
            pickup_date=timezone.localdate() + timedelta(days=2),
            period="12:10 até 12:30",
            location=SCHOOL,
        )
        customer = Customer.objects.create(name="Cliente", phone="33999999999")
        order = Order.objects.create(
            customer=customer,
            pickup_slot=slot,
            payment_method=Order.PaymentMethod.PIX,
            total=Decimal("3.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            unit_price=product.price,
        )

        response = self.client.post(
            reverse("gestao_pedidos"),
            {"order_id": order.pk, "status": Order.Status.CONFIRMED},
            follow=True,
        )
        order.refresh_from_db()

        self.assertEqual(order.status, Order.Status.NEW)
        self.assertContains(response, "Aguarde a confirmação automática do pagamento")

    def test_manager_can_add_monday_with_automatic_slots(self):
        self.client.force_login(self.user)
        pickup_date = next_weekday(0)
        response = self.client.post(
            reverse("gestao_agenda"),
            {
                "action": "add",
                "pickup_date": pickup_date.isoformat(),
            },
        )
        self.assertRedirects(response, reverse("gestao_agenda"))
        slots = PickupSlot.objects.filter(pickup_date=pickup_date, active=True)
        self.assertEqual(slots.count(), 3)
        self.assertTrue(slots.filter(period="12:10 até 12:30", location=SCHOOL).exists())
        self.assertTrue(slots.filter(period="17:00 até 19:00", location=HOME_ADDRESS).exists())

    def test_wednesday_has_four_automatic_slots(self):
        self.client.force_login(self.user)
        pickup_date = next_weekday(2)
        response = self.client.post(
            reverse("gestao_agenda"),
            {"action": "add", "pickup_date": pickup_date.isoformat()},
        )
        self.assertRedirects(response, reverse("gestao_agenda"))
        slots = PickupSlot.objects.filter(pickup_date=pickup_date, active=True)
        self.assertEqual(slots.count(), 4)
        self.assertTrue(slots.filter(period="19:00 até 20:00", location=HOME_ADDRESS).exists())
        self.assertTrue(slots.filter(location__icontains="WhatsApp").exists())
        catalog = self.client.get(reverse("catalogo"))
        self.assertContains(catalog, f"Quarta-feira — {pickup_date:%d/%m/%Y}")
        self.assertContains(catalog, "19:00 até 20:00")

    def test_friday_has_three_automatic_slots(self):
        self.client.force_login(self.user)
        pickup_date = next_weekday(4)
        response = self.client.post(
            reverse("gestao_agenda"),
            {"action": "add", "pickup_date": pickup_date.isoformat()},
        )
        self.assertRedirects(response, reverse("gestao_agenda"))
        self.assertEqual(
            PickupSlot.objects.filter(pickup_date=pickup_date, active=True).count(),
            3,
        )

    def test_other_weekdays_are_rejected(self):
        self.client.force_login(self.user)
        pickup_date = next_weekday(1)
        response = self.client.post(
            reverse("gestao_agenda"),
            {"action": "add", "pickup_date": pickup_date.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Escolha uma data que caia em uma segunda-feira, quarta-feira ou sexta-feira.",
        )
        self.assertFalse(PickupSlot.objects.filter(pickup_date=pickup_date).exists())

    def test_removing_date_hides_all_its_slots(self):
        self.client.force_login(self.user)
        pickup_date = next_weekday(0)
        self.client.post(
            reverse("gestao_agenda"),
            {"action": "add", "pickup_date": pickup_date.isoformat()},
        )
        response = self.client.post(
            reverse("gestao_agenda"),
            {"action": "remove_date", "pickup_date": pickup_date.isoformat()},
        )
        self.assertRedirects(response, reverse("gestao_agenda"))
        self.assertFalse(PickupSlot.objects.filter(pickup_date=pickup_date, active=True).exists())
