from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from core import panel_views as p
from core import public_views as pub
from core import views as v
from core.forms import NuevaPasswordForm, RecuperarForm

# El /admin/ de Django no se usa: la gestión se hace desde /panel/.

urlpatterns = [
    # ---------------------------------------------------------- Sitio público (sin iniciar sesión)
    path('', pub.inicio, name='inicio'),
    path('vuelos/', pub.vuelos, name='vuelos'),
    path('paquetes/', pub.paquetes, name='paquetes'),
    path('promociones/', pub.promociones, name='promociones'),
    path('ofertas/<str:codigo>/', pub.oferta, name='oferta'),
    path('visas/', pub.visas, name='visas'),
    path('nosotros/', pub.nosotros, name='nosotros'),
    path('contacto/', pub.contacto, name='contacto'),
    path('preguntas-frecuentes/', pub.preguntas, name='preguntas'),
    path('privacidad/', pub.privacidad, name='privacidad'),
    path('terminos/', pub.terminos, name='terminos'),
    path('asistente/', pub.asistente, name='asistente'),
    path('publico/<str:tipo>/<int:pk>/', pub.archivo_publico, name='archivo_publico'),

    # ---------------------------------------------------------- Cuentas
    path('entrar/', v.login_view, name='login'),
    path('registro/', v.registro_view, name='registro'),
    path('salir/', v.logout_view, name='logout'),
    path('recuperar/', auth_views.PasswordResetView.as_view(
        form_class=RecuperarForm, template_name='core/recuperar/form.html',
        email_template_name='core/recuperar/email.txt', subject_template_name='core/recuperar/asunto.txt',
        success_url=reverse_lazy('recuperar_enviado')), name='recuperar'),
    path('recuperar/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='core/recuperar/enviado.html'), name='recuperar_enviado'),
    path('recuperar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        form_class=NuevaPasswordForm, template_name='core/recuperar/nueva.html',
        success_url=reverse_lazy('recuperar_listo')), name='recuperar_confirmar'),
    path('recuperar/listo/', auth_views.PasswordResetCompleteView.as_view(
        template_name='core/recuperar/listo.html'), name='recuperar_listo'),

    # ---------------------------------------------------------- Cuenta del usuario
    path('mi-cuenta/', v.dashboard_view, name='dashboard'),
    path('mi-cuenta/perfil/', v.perfil_view, name='perfil'),
    path('mi-cuenta/cotizar/', v.cotizar_view, name='cotizar'),
    path('mi-cuenta/solicitudes/', v.mis_solicitudes_view, name='mis_solicitudes'),
    path('mi-cuenta/solicitudes/<int:pk>/', v.solicitud_view, name='solicitud'),
    path('mi-cuenta/expedientes/', v.expedientes_view, name='expedientes'),
    path('mi-cuenta/expedientes/<int:pk>/', v.expediente_view, name='expediente'),
    path('mi-cuenta/citas/', v.citas_view, name='citas'),
    path('mi-cuenta/pagos/', v.pagos_view, name='pagos'),
    path('archivos/<str:tipo>/<int:pk>/', v.archivo_view, name='archivo'),

    # ---------------------------------------------------------- Panel del personal
    path('panel/', p.panel_inicio, name='panel_inicio'),
    path('panel/consultas/', p.panel_consultas, name='panel_consultas'),
    path('panel/solicitudes/', p.panel_solicitudes, name='panel_solicitudes'),
    path('panel/solicitudes/<int:pk>/', p.panel_solicitud, name='panel_solicitud'),
    path('panel/expedientes/', p.panel_expedientes, name='panel_expedientes'),
    path('panel/expedientes/nuevo/', p.panel_expediente_nuevo, name='panel_expediente_nuevo'),
    path('panel/expedientes/<int:pk>/', p.panel_expediente, name='panel_expediente'),
    path('panel/expedientes/<int:pk>/editar/', p.panel_expediente_editar, name='panel_expediente_editar'),
    path('panel/documentos/', p.panel_documentos, name='panel_documentos'),
    path('panel/pagos/', p.panel_pagos, name='panel_pagos'),
    path('panel/agenda/', p.panel_agenda, name='panel_agenda'),
    path('panel/citas/nueva/', p.panel_cita, name='panel_cita_nueva'),
    path('panel/citas/<int:pk>/', p.panel_cita, name='panel_cita'),
    path('panel/clientes/', p.panel_clientes, name='panel_clientes'),
    path('panel/clientes/<int:pk>/', p.panel_cliente, name='panel_cliente'),
    path('panel/personal/', p.panel_personal, name='panel_personal'),
    path('panel/cuentas/<int:pk>/estado/', p.panel_cuenta_estado, name='panel_cuenta_estado'),
    path('panel/contenido/', p.panel_contenido, name='panel_contenido'),
    path('panel/contenido/agencia/', p.panel_sitio, name='panel_sitio'),
    path('panel/contenido/<str:seccion>/', p.panel_contenido_lista, name='panel_contenido_lista'),
    path('panel/contenido/<str:seccion>/nuevo/', p.panel_contenido_form, name='panel_contenido_nuevo'),
    path('panel/contenido/<str:seccion>/<int:pk>/', p.panel_contenido_form, name='panel_contenido_editar'),
]

