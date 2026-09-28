from django.urls import path
from . import views

app_name = "pagamentos"

urlpatterns = [
    path("infinitepay/<int:pedido_id>/", views.iniciar_pagamento, name="iniciar"),
    path("infinitepay/retorno/", views.retorno, name="retorno"),
    path("infinitepay/webhook/", views.webhook, name="webhook"),
]
