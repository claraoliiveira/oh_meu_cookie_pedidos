from django.db import migrations
from django.utils import timezone


SCHOOL = "E.E. Madre Serafina de Jesus"
HOME_ADDRESS = "Rua Dr. Carlos Prates, 1332 - Centro"
SCHEDULES = {
    0: (
        ("12:10 até 12:30", SCHOOL),
        ("14:10 até 14:40", SCHOOL),
        ("17:00 até 19:00", HOME_ADDRESS),
    ),
    2: (
        ("12:10 até 12:30", SCHOOL),
        ("13:20 até 14:10", SCHOOL),
        ("15:00 até 17:30", f"{SCHOOL} (marcar o horário exato pelo WhatsApp)"),
        ("19:00 até 20:00", HOME_ADDRESS),
    ),
    4: (
        ("12:10 até 12:30", SCHOOL),
        ("14:10 até 14:40", SCHOOL),
        ("17:00 até 19:00", HOME_ADDRESS),
    ),
}


def standardize_future_slots(apps, schema_editor):
    PickupSlot = apps.get_model("pedidos", "PickupSlot")
    dates = list(
        PickupSlot.objects.filter(
            active=True,
            pickup_date__gte=timezone.localdate(),
        )
        .values_list("pickup_date", flat=True)
        .distinct()
    )
    for pickup_date in dates:
        PickupSlot.objects.filter(pickup_date=pickup_date).update(active=False)
        for period, location in SCHEDULES.get(pickup_date.weekday(), ()):
            PickupSlot.objects.update_or_create(
                pickup_date=pickup_date,
                period=period,
                location=location,
                defaults={"active": True},
            )


class Migration(migrations.Migration):
    dependencies = [("pedidos", "0002_cardapio_inicial")]
    operations = [migrations.RunPython(standardize_future_slots, migrations.RunPython.noop)]
