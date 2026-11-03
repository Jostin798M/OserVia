"""Roles y reglas de acceso (RS-02, RNF-06)."""
from functools import wraps

from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache


def rol(user):
    if not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return 'admin'
    perfil = getattr(user, 'perfil', None)
    return perfil.rol if perfil else 'usuario'


def es_admin(user):
    return rol(user) == 'admin'


def es_asesor(user):
    return rol(user) == 'asesor'


def es_personal(user):
    return rol(user) in ('admin', 'asesor')


def filtrar_asignados(qs, user):
    """Administrador: todo. Asesor: solo lo asignado (RS-02.1, RS-02.2)."""
    if es_admin(user):
        return qs
    return qs.filter(asesor=user)


def puede_ver_expediente(user, exp):
    if es_admin(user):
        return True
    if es_asesor(user):
        return exp.asesor_id == user.id
    return exp.usuario_id == user.id  # RS-02.3


def personal_required(view):
    """Sin sesión -> acceso del panel. Con sesión que no es de personal -> 404."""
    @wraps(view)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if not es_personal(request.user):
            raise Http404
        return view(request, *args, **kwargs)
    return never_cache(envoltura)


def admin_required(view):
    @wraps(view)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if not es_admin(request.user):
            raise Http404
        return view(request, *args, **kwargs)
    return never_cache(envoltura)
