from django.contrib import admin

from .models import Customer, Order, OrderItem, PickupSlot, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "active", "featured", "sort_order")
    list_editable = ("price", "active", "featured", "sort_order")
    search_fields = ("name",)


@admin.register(PickupSlot)
class PickupSlotAdmin(admin.ModelAdmin):
    list_display = ("pickup_date", "period", "location", "active")
    list_filter = ("active", "pickup_date")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "pickup_slot", "status", "payment_method", "payment_confirmed", "total")
    list_filter = ("status", "payment_method", "payment_confirmed")
    search_fields = ("customer__name", "customer__phone")
    inlines = [OrderItemInline]


admin.site.register(Customer)
