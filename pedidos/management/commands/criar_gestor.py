from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Cria ou atualiza um usuário da área de pedidos."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        username = options["username"].strip()
        if not username:
            raise CommandError("Informe um nome de usuário.")
        password = getpass("Digite a nova senha: ")
        confirmation = getpass("Repita a nova senha: ")
        if password != confirmation:
            raise CommandError("As senhas não são iguais.")
        if len(password) < 8:
            raise CommandError("Use uma senha com pelo menos 8 caracteres.")
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_active = True
        user.set_password(password)
        user.save()
        action = "criado" if created else "atualizado"
        self.stdout.write(self.style.SUCCESS(f"Usuário {username} {action} com sucesso."))
