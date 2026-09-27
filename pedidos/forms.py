import json

from django import forms
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import Order, PickupSlot


class CheckoutForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=120)
    phone = forms.CharField(label="Telefone / WhatsApp", max_length=30)
    pickup_date = forms.CharField(widget=forms.HiddenInput)
    pickup_slot = forms.ModelChoiceField(
        label="Horário e local",
        queryset=PickupSlot.objects.none(),
        empty_label="Escolha primeiro a data",
    )
    payment_method = forms.ChoiceField(
        label="Forma de pagamento",
        choices=(("", "Selecione"), *Order.PaymentMethod.choices),
    )
    notes = forms.CharField(
        label="Observações",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ex.: separar em duas embalagens"}),
    )
    items_json = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pickup_slot"].queryset = PickupSlot.objects.filter(
            active=True,
            pickup_date__gte=timezone.localdate(),
        )

    def clean_phone(self):
        phone = "".join(character for character in self.cleaned_data["phone"] if character.isdigit())
        if len(phone) < 10:
            raise forms.ValidationError("Informe um WhatsApp com DDD.")
        return phone

    def clean_items_json(self):
        try:
            items = json.loads(self.cleaned_data["items_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            raise forms.ValidationError("Não foi possível ler os itens do pedido.")

        cleaned = []
        for item in items if isinstance(items, list) else []:
            try:
                product_id = int(item["product_id"])
                quantity = int(item["quantity"])
            except (KeyError, TypeError, ValueError):
                continue
            if quantity > 0:
                cleaned.append({"product_id": product_id, "quantity": min(quantity, 100)})
        if not cleaned:
            raise forms.ValidationError("Escolha pelo menos um cookie.")
        return cleaned

    def clean(self):
        cleaned = super().clean()
        selected_date = parse_date(cleaned.get("pickup_date", ""))
        slot = cleaned.get("pickup_slot")
        if slot and selected_date != slot.pickup_date:
            self.add_error("pickup_slot", "Esse horário não pertence à data escolhida.")
        if slot and not slot.is_available:
            self.add_error("pickup_slot", "Essa opção de retirada não está mais disponível.")
        return cleaned


class PickupSlotForm(forms.ModelForm):
    class Meta:
        model = PickupSlot
        fields = ["pickup_date", "period", "location"]
        widgets = {
            "pickup_date": forms.DateInput(attrs={"type": "date"}),
            "period": forms.TextInput(attrs={"placeholder": "Ex.: 14h às 18h"}),
            "location": forms.TextInput(attrs={"placeholder": "Ex.: Rua..., nº..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pickup_date"].widget.attrs["min"] = timezone.localdate().isoformat()

    def clean_pickup_date(self):
        pickup_date = self.cleaned_data["pickup_date"]
        if pickup_date < timezone.localdate():
            raise forms.ValidationError("A data não pode estar no passado.")
        return pickup_date
