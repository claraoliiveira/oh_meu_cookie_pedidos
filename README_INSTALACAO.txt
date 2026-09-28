OH! MEU COOKIE — INTEGRAÇÃO INFINITEPAY
========================================

Este pacote foi preparado para ser colocado DENTRO da pasta do seu projeto Django,
no mesmo nível do arquivo manage.py.

Fluxo:
pedido salvo -> botão/URL de pagamento -> página externa da InfinitePay ->
Pix/cartão -> retorno para o site -> confirmação do pagamento.

InfiniteTag configurada:
clara-oliveira-cqv

IMPORTANTE:
No plano gratuito do PythonAnywhere, api.checkout.infinitepay.io precisa estar
liberado na allowlist para o Django conseguir criar/verificar links.

COMO INSTALAR
-------------

1) Descompacte este ZIP dentro da pasta onde está o seu manage.py.

Exemplo:
C:\Users\Clara\Oh_Meu_Cookie_Django_MVP\oh_meu_cookie_django\

Depois de copiar, você deve ter:
manage.py
config\
negocio\
pagamentos\
instalar_infinitepay.py

2) Com o ambiente virtual ativado, execute:

python instalar_infinitepay.py

3) Instale/garanta a dependência requests:

pip install requests

4) Crie a tabela da integração:

python manage.py migrate

5) Confira:

python manage.py check

6) Reinicie o site no PythonAnywhere.

URL para iniciar o pagamento de um pedido:
------------------------------------------------
/pagamento/infinitepay/<ID_DO_PEDIDO>/

Exemplo para pedido 15:
/pagamento/infinitepay/15/

Você pode usar em um template existente:

<a href="{% url 'pagamentos:iniciar' pedido.id %}">
    Pagar com InfinitePay
</a>

A integração procura por negocio.Pedido automaticamente.

Campos de total reconhecidos automaticamente:
- valor_total
- total
- total_price
- valor
- amount

Campos de cliente reconhecidos automaticamente:
- nome / nome_cliente / customer_name
- email / email_cliente
- telefone / telefone_cliente / phone

Campos que podem ser atualizados no pedido após confirmação:
- pago (booleano)
- payment_status / status_pagamento
- status (somente se o campo aceitar o valor "Pago")

Mesmo que o modelo Pedido não possua esses campos, a confirmação permanece registrada
em PagamentoInfinitePay.

Se o seu valor total estiver em outro campo, acrescente no settings.py:
INFINITEPAY_TOTAL_FIELD = "nome_do_seu_campo"

Configuração adicionada automaticamente:
INFINITEPAY_HANDLE = "clara-oliveira-cqv"
INFINITEPAY_ORDER_MODEL = "negocio.Pedido"

ENDPOINTS
---------
Criar checkout:
POST https://api.checkout.infinitepay.io/links

Verificar pagamento:
POST https://api.checkout.infinitepay.io/payment_check

Webhook do seu site:
https://SEU-DOMINIO/pagamento/infinitepay/webhook/

Retorno:
https://SEU-DOMINIO/pagamento/infinitepay/retorno/

SEGURANÇA
---------
O webhook:
- exige POST JSON;
- verifica se o pedido existe;
- compara o valor recebido com o valor esperado do pedido;
- registra transaction_nsu, invoice_slug e receipt_url;
- não recebe nem armazena dados de cartão.

OBSERVAÇÃO SOBRE ESTOQUE
------------------------
Este módulo NÃO dá baixa diretamente no estoque porque cada projeto pode ter regras
diferentes para produção/estoque. Ele marca o pagamento e registra os dados.
Se o seu modelo Pedido já usa o campo "pago", a alteração é automática.

