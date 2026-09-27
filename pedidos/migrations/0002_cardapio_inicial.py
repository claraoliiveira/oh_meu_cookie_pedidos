from decimal import Decimal

from django.db import migrations


def criar_cardapio(apps, schema_editor):
    Product = apps.get_model("pedidos", "Product")
    products = [
        ("Tradicional", "Massa amanteigada com gotas de chocolate.", "3.00", True),
        ("Red Velvet", "Cookie macio de red velvet, delicado e irresistível.", "3.50", False),
        ("Chocolate com Chocolate Branco", "Chocolate intenso com pedaços de chocolate branco.", "3.50", False),
        ("Oreo", "Cookie artesanal com pedacinhos de Oreo.", "3.50", False),
        ("Nutella", "Cookie generoso com recheio cremoso de Nutella.", "9.00", True),
    ]
    for order, (name, description, price, featured) in enumerate(products, start=1):
        Product.objects.update_or_create(
            name=name,
            defaults={
                "description": description,
                "price": Decimal(price),
                "active": True,
                "featured": featured,
                "sort_order": order,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("pedidos", "0001_initial")]
    operations = [migrations.RunPython(criar_cardapio, migrations.RunPython.noop)]
