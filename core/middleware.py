from django.conf import settings
from django.views.defaults import page_not_found


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
