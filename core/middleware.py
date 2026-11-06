from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.views.defaults import page_not_found

from .models import Perfil


class Pagina404Middleware:
    """Con DEBUG activo Django muestra su 404 técnica; esto la reemplaza por la página 404 de OserVia
    para que se vea igual en desarrollo y en producción (en producción Django ya usa 404.html)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG and response.status_code == 404 and not request.path.startswith(settings.STATIC_URL):
            return page_not_found(request, None)
        return response


class CambioClaveMiddleware:
    """Quien debe cambiar su contraseña no puede usar el sistema hasta hacerlo."""
    LIBRES = ('/salir/', '/static/', '/privacidad/', '/terminos/', '/publico/', '/asistente/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        destino = reverse('cambiar_clave')
        if (request.user.is_authenticated and request.path != destino and not request.path.startswith(self.LIBRES)):
            perfil = Perfil.objects.filter(usuario=request.user, debe_cambiar_clave=True).only('pk').first()
            if perfil:
                return redirect(destino)
        return self.get_response(request)
