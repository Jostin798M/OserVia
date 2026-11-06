"""Cierra todas las sesiones y, si se pide, obliga a cada cuenta a crear una contraseña nueva."""
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Perfil


class Command(BaseCommand):
    help = 'Cierra todas las sesiones activas.'

    def add_arguments(self, parser):
        parser.add_argument('--exigir-cambio', action='store_true',
                            help='Pide una contraseña nueva a todas las cuentas al volver a entrar.')

    @transaction.atomic
    def handle(self, *args, **opts):
        sesiones, _ = Session.objects.all().delete()
        self.stdout.write(f'Sesiones cerradas: {sesiones}')
        if opts['exigir_cambio']:
            self.stdout.write(f'Cuentas que deben cambiar la contraseña: {Perfil.objects.update(debe_cambiar_clave=True)}')
