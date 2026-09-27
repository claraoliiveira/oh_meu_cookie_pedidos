# Oh! Meu Cookie — Pedidos

Versão enxuta do site feita em Python e Django para receber pedidos de cookies.

## O que esta versão tem

- formulário público inspirado no site do Google Apps Script;
- nome e WhatsApp do cliente;
- quantidade de cada sabor e total atualizado na tela;
- datas, horários e locais de retirada configuráveis;
- pagamento por Pix ou cartão;
- observações do pedido;
- confirmação pelo WhatsApp;
- área protegida apenas para **Pedidos** e **Datas de retirada**.

Esta versão **não possui** estoque de produtos, insumos, receitas, produção, contas a receber ou financeiro. A quantidade do cardápio não é limitada por estoque.

## Instalação no Windows

Abra o PowerShell dentro desta pasta (a mesma que contém `manage.py`) e execute:

```powershell
py -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
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
```

Use o WhatsApp apenas com números, incluindo `55` e o DDD.

## Atualizar com Git no computador

Se este projeto estiver em um repositório próprio:

```powershell
git add .
git commit -m "Cria versão somente para pedidos"
git push
```

Recomenda-se publicar esta pasta em um repositório separado da versão completa, pois os modelos e o banco de dados são diferentes.

## Publicar ou atualizar no PythonAnywhere

No console Bash do PythonAnywhere:

```bash
cd ~/oh_meu_cookie_pedidos
git pull
source venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Na aba **Web**, configure:

- **Source code:** `/home/SEU_USUARIO/oh_meu_cookie_pedidos`
- **Working directory:** `/home/SEU_USUARIO/oh_meu_cookie_pedidos`
- **Virtualenv:** `/home/SEU_USUARIO/oh_meu_cookie_pedidos/venv`

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
source venv/bin/activate
python manage.py criar_gestor clara
```

## Como liberar pedidos

1. Entre em `/entrar/`.
2. Abra **Datas de retirada**.
3. Cadastre a data, o horário e o local.
4. A opção aparecerá imediatamente na página pública.

Se nenhuma data estiver ativa, o botão de finalizar permanece bloqueado. Isso evita receber pedidos em dias que você não pode atender.

## Banco de dados

O projeto usa SQLite (`db.sqlite3`). O banco é criado pelo `migrate` e não acompanha o ZIP. Faça backup do arquivo `db.sqlite3` no servidor antes de alterações importantes.
