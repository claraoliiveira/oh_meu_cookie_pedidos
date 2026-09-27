from django.urls import path

from . import views


urlpatterns = [
    path("", views.catalogo, name="catalogo"),
    path("pedido/finalizar/", views.finalizar_pedido, name="finalizar_pedido"),
    path("pedido/<uuid:token>/sucesso/", views.pedido_sucesso, name="pedido_sucesso"),
    path("pedido/<uuid:token>/pagar/", views.iniciar_pagamento, name="iniciar_pagamento"),
    path(
        "pedido/<uuid:token>/pagamento/retorno/",
        views.pagamento_retorno,
        name="pagamento_retorno",
    ),
    path(
        "pagamentos/infinitepay/webhook/",
        views.infinitepay_webhook,
        name="infinitepay_webhook",
    ),
    path("gestao/", views.gestao_inicio, name="gestao_inicio"),
    path("gestao/pedidos/", views.gestao_pedidos, name="gestao_pedidos"),
    path("gestao/agenda/", views.gestao_agenda, name="gestao_agenda"),
]
