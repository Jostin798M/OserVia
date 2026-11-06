"""Limitador sencillo de intentos de inicio de sesión (fuerza bruta)."""
import hashlib

from django.conf import settings
from django.core.cache import cache

MAX_INTENTOS = 5          # por combinación IP + correo
MAX_INTENTOS_IP = 20      # por IP, sin importar el correo
BLOQUEO_SEGUNDOS = 15 * 60


def _ip(request):
    if not request:
        return ''
    # Detrás del proxy de Vercel, REMOTE_ADDR no es el visitante; Vercel fija X-Forwarded-For y no admite suplantarlo.
    if settings.EN_VERCEL:
        return request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _claves(request, email):
    ip = _ip(request)
    email = (email or '').strip().lower()
    combo = hashlib.sha256(f'{ip}|{email}'.encode()).hexdigest()
    return f'login-fallos:{combo}', f'login-fallos-ip:{ip}'


def esta_bloqueado(request, email):
    k_combo, k_ip = _claves(request, email)
    return (cache.get(k_combo, 0) >= MAX_INTENTOS) or (cache.get(k_ip, 0) >= MAX_INTENTOS_IP)


def registrar_fallo(request, email):
    for k in _claves(request, email):
        cache.add(k, 0, BLOQUEO_SEGUNDOS)
        try:
            cache.incr(k)
        except ValueError:
            cache.set(k, 1, BLOQUEO_SEGUNDOS)


def limpiar(request, email):
    cache.delete(_claves(request, email)[0])
