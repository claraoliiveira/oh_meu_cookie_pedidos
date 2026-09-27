# Oh! Meu Cookie — Pedidos

Versão enxuta do site feita em Python e Django para receber pedidos de cookies.

## O que esta versão tem

- formulário público inspirado no site do Google Apps Script;
- nome e WhatsApp do cliente;
- quantidade de cada sabor e total atualizado na tela;
- datas de retirada liberadas pela gestão, com horários e locais automáticos;
- pagamento online por Pix ou cartão de crédito com Checkout Integrado InfinitePay;
- confirmação automática do pagamento por consulta segura e webhook;
- observações do pedido;
- confirmação pelo WhatsApp;
- área protegida apenas para **Pedidos** e **Datas de retirada**.

Esta versão **não possui** estoque de produtos, insumos, receitas, produção, contas a receber ou financeiro. A quantidade do cardápio não é limitada por estoque.

## Horários automáticos de retirada

Ao liberar uma data, o sistema identifica o dia da semana e cria as opções abaixo:

### Segunda-feira

- 12:10 até 12:30 — E.E. Madre Serafina de Jesus
- 14:10 até 14:40 — E.E. Madre Serafina de Jesus
- 17:00 até 19:00 — Rua Dr. Carlos Prates, 1332 - Centro

### Quarta-feira

- 12:10 até 12:30 — E.E. Madre Serafina de Jesus
- 13:20 até 14:10 — E.E. Madre Serafina de Jesus
- 15:00 até 17:30 — E.E. Madre Serafina de Jesus (marcar o horário exato pelo WhatsApp)
- 19:00 até 20:00 — Rua Dr. Carlos Prates, 1332 - Centro

### Sexta-feira

- 12:10 até 12:30 — E.E. Madre Serafina de Jesus
- 14:10 até 14:40 — E.E. Madre Serafina de Jesus
- 17:00 até 19:00 — Rua Dr. Carlos Prates, 1332 - Centro

Datas de terça, quinta, sábado ou domingo são recusadas pelo formulário.

## Instalação no Windows

Abra o PowerShell dentro desta pasta (a mesma que contém `manage.py`) e execute:

```cmd
py -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py criar_gestor clara
python manage.py runserver
```

O comando `criar_gestor` pedirá a senha sem mostrar os caracteres. Depois acesse:

- Loja: http://127.0.0.1:8000/
- Login: http://127.0.0.1:8000/entrar/

Os cinco sabores do site de referência são criados automaticamente pelo comando `migrate`.

## Antes de publicar

Edite o arquivo `.env`:

```env
DJANGO_SECRET_KEY=coloque-uma-chave-longa-e-secreta
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=seuusuario.pythonanywhere.com
COOKIE_WHATSAPP_NUMBER=5533991254014
INFINITEPAY_HANDLE=clara-oliveira-cqv
PUBLIC_BASE_URL=https://ohmeucookiee.pythonanywhere.com
INFINITEPAY_TIMEOUT=10
```

Use o WhatsApp apenas com números, incluindo `55` e o DDD.

## Ativar o pagamento online na InfinitePay

Antes de testar no site:

1. Abra o App InfinitePay.
2. Entre em **Vendas → Checkout → Configurações**.
3. Toque em **Habilitar Checkout Integrado**.
4. Em **Meios de pagamentos**, deixe **Pix** e **Cartão de crédito** ativos.
5. Escolha se as taxas do cartão serão assumidas pela loja ou repassadas ao cliente.

A InfiniteTag configurada neste projeto é `clara-oliveira-cqv`, sem o símbolo `$`.

O site não recebe nem armazena números de cartão. O cliente paga na página segura da
InfinitePay. Depois, o servidor consulta a InfinitePay e só confirma o pedido quando o
status, o identificador do pedido e o valor total forem validados.

## Atualizar com Git no computador

Se este projeto estiver em um repositório próprio:

```cmd
git add .
git commit -m "Adiciona pagamento online com InfinitePay"
git push
```

Recomenda-se publicar esta pasta em um repositório separado da versão completa, pois os modelos e o banco de dados são diferentes.

## Publicar ou atualizar no PythonAnywhere

No console Bash do PythonAnywhere:

```bash
cd ~/oh_meu_cookie_pedidos
source ~/.virtualenvs/ohmeucookie/bin/activate
git pull origin main
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Confirme também que o `.env` do PythonAnywhere contém:

```env
INFINITEPAY_HANDLE=clara-oliveira-cqv
PUBLIC_BASE_URL=https://ohmeucookiee.pythonanywhere.com
INFINITEPAY_TIMEOUT=10
```

Se sua conta do PythonAnywhere for gratuita, teste a conexão externa no console Bash:

```bash
python -c "import requests; r=requests.get('https://api.checkout.infinitepay.io', timeout=10); print(r.status_code)"
```

Um `404` ou `405` significa que o servidor alcançou o domínio. Se aparecer bloqueio do
proxy/allowlist, solicite ao PythonAnywhere a liberação de `api.checkout.infinitepay.io`
usando a documentação oficial do Checkout Integrado, ou use um plano pago, que não possui
essa restrição de acesso externo.

Depois de clicar em **Reload**, faça um pedido barato de teste. Não considere apenas a tela
de retorno: confirme no painel da InfinitePay que a cobrança foi recebida e confira se o
pedido aparece na gestão com **Confirmado automaticamente**.

Na aba **Web**, configure:

- **Source code:** `/home/SEU_USUARIO/oh_meu_cookie_pedidos`
- **Working directory:** `/home/SEU_USUARIO/oh_meu_cookie_pedidos`
- **Virtualenv:** `/home/SEU_USUARIO/.virtualenvs/ohmeucookie`

No arquivo WSGI do PythonAnywhere, deixe:

```python
import os
import sys

project_home = "/home/SEU_USUARIO/oh_meu_cookie_pedidos"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Depois, na aba **Web**, confira o mapeamento de arquivos estáticos:

- URL: `/static/`
- Directory: `/home/SEU_USUARIO/oh_meu_cookie_pedidos/staticfiles`

Clique em **Reload**.

Na primeira publicação, crie o login:

```bash
cd ~/oh_meu_cookie_pedidos
source ~/.virtualenvs/ohmeucookie/bin/activate
python manage.py criar_gestor clara
```

## Como liberar pedidos

1. Entre em `/entrar/`.
2. Abra **Datas de retirada**.
3. Escolha uma segunda, quarta ou sexta-feira.
4. O sistema libera automaticamente todos os horários e locais daquele dia.
5. As opções aparecem imediatamente na página pública.

Se nenhuma data estiver ativa, o botão de finalizar permanece bloqueado. Isso evita receber pedidos em dias que você não pode atender.

## Banco de dados

O projeto usa SQLite (`db.sqlite3`). O banco é criado pelo `migrate` e não acompanha o ZIP. Faça backup do arquivo `db.sqlite3` no servidor antes de alterações importantes.
