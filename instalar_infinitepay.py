from pathlib import Path
import re

BASE = Path(__file__).resolve().parent

def localizar_settings():
    candidatos = list(BASE.glob("*/settings.py"))
    candidatos = [p for p in candidatos if p.parent.name not in {"pagamentos", "venv", ".venv"}]
    if (BASE / "config" / "settings.py").exists():
        return BASE / "config" / "settings.py"
    if len(candidatos) == 1:
        return candidatos[0]
    raise SystemExit("Não consegui localizar settings.py automaticamente.")

def localizar_urls(settings_path):
    candidato = settings_path.parent / "urls.py"
    if candidato.exists():
        return candidato
    if (BASE / "config" / "urls.py").exists():
        return BASE / "config" / "urls.py"
    raise SystemExit("Não consegui localizar urls.py automaticamente.")

def patch_settings(path):
    txt = path.read_text(encoding="utf-8")
    original = txt

    if '"pagamentos"' not in txt and "'pagamentos'" not in txt:
        m = re.search(r"INSTALLED_APPS\s*=\s*\[", txt)
        if not m:
            raise SystemExit("INSTALLED_APPS não encontrado em settings.py.")
        pos = m.end()
        txt = txt[:pos] + '\n    "pagamentos",' + txt[pos:]

    bloco = (
        "\n\n# ============================================================\n"
        "# OH! MEU COOKIE - INFINITEPAY\n"
        "# ============================================================\n"
        'INFINITEPAY_HANDLE = "clara-oliveira-cqv"\n'
        'INFINITEPAY_ORDER_MODEL = "negocio.Pedido"\n'
        'INFINITEPAY_API_BASE = "https://api.checkout.infinitepay.io"\n'
    )

    if "INFINITEPAY_HANDLE" not in txt:
        txt += bloco

    if txt != original:
        backup = path.with_suffix(".py.bak_infinitepay")
        backup.write_text(original, encoding="utf-8")
        path.write_text(txt, encoding="utf-8")
        print(f"[OK] settings.py atualizado. Backup: {backup.name}")
    else:
        print("[OK] settings.py já estava configurado.")

def patch_urls(path):
    txt = path.read_text(encoding="utf-8")
    original = txt

    m = re.search(r"from\s+django\.urls\s+import\s+([^\n]+)", txt)
    if m:
        itens = [x.strip() for x in m.group(1).split(",")]
        if "include" not in itens:
            itens.append("include")
            novo = "from django.urls import " + ", ".join(itens)
            txt = txt[:m.start()] + novo + txt[m.end():]
    else:
        txt = "from django.urls import include\n" + txt

    if 'include("pagamentos.urls")' not in txt and "include('pagamentos.urls')" not in txt:
        m = re.search(r"urlpatterns\s*=\s*\[", txt)
        if not m:
            raise SystemExit("urlpatterns não encontrado em urls.py.")
        pos = m.end()
        txt = txt[:pos] + '\n    path("pagamento/", include("pagamentos.urls")),' + txt[pos:]

    if txt != original:
        backup = path.with_suffix(".py.bak_infinitepay")
        backup.write_text(original, encoding="utf-8")
        path.write_text(txt, encoding="utf-8")
        print(f"[OK] urls.py atualizado. Backup: {backup.name}")
    else:
        print("[OK] urls.py já estava configurado.")

def main():
    settings_path = localizar_settings()
    urls_path = localizar_urls(settings_path)
    print(f"Projeto detectado: {settings_path.parent.name}")
    patch_settings(settings_path)
    patch_urls(urls_path)
    print("")
    print("Integração instalada.")
    print("Agora execute:")
    print("  pip install requests")
    print("  python manage.py migrate")
    print("  python manage.py check")

if __name__ == "__main__":
    main()
