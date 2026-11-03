"""Portal del usuario (cliente) y autenticación."""
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import servicios
from .archivos import servir
from .forms import (AceptarCotizacionForm, CambiarPasswordForm, ComprobanteForm, LoginForm, PerfilForm, RegistroForm,
                    SolicitudViajeForm, SubirDocumentoForm)
from .models import (ArchivoDocumento, AvisoVuelo, Cita, CitaConsular, Comprobante, Cotizacion, DocumentoViaje,
                     Expediente, Oferta, Perfil, SolicitudViaje, VueloContratado)
from .permisos import es_personal, puede_ver_expediente


def _perfil(user):
    perfil, _ = Perfil.objects.get_or_create(usuario=user)
    return perfil


def _inicio_de(user):
    return 'panel_inicio' if es_personal(user) else 'dashboard'


# ==================================================================== Autenticación (RS-01)

def login_view(request):
    if request.user.is_authenticated:
        return redirect(_inicio_de(request.user))
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.user)
        if not form.cleaned_data.get('recordar'):
            request.session.set_expiry(0)
        destino = request.POST.get('next') or request.GET.get('next')
        valido = destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure())
        if es_personal(form.user):  # administrador y asesores van a su panel
            return redirect(destino if valido and destino.startswith('/panel/') else 'panel_inicio')
        if valido and not destino.startswith('/panel/'):
            return redirect(destino)
        return redirect('dashboard')
    return render(request, 'core/login.html', {'form': form, 'next': request.GET.get('next', '')})


def registro_view(request):
    if request.user.is_authenticated:
        return redirect(_inicio_de(request.user))
    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='core.backends.EmailBackend')
        messages.success(request, f'¡Cuenta creada! Bienvenido/a, {user.first_name}.')  # RS-01.1
        return redirect('dashboard')
    return render(request, 'core/registro.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)  # RS-01.3
    messages.info(request, 'Cerraste sesión correctamente.')
    return redirect('login')


@login_required
def perfil_view(request):
    user = request.user
    accion = request.POST.get('accion') if request.method == 'POST' else None
    datos_form = PerfilForm(user, request.POST if accion == 'datos' else None)
    pass_form = CambiarPasswordForm(user, request.POST if accion == 'password' else None)
    if accion == 'datos' and datos_form.is_valid():
        datos_form.save()
        messages.success(request, 'Tus datos se actualizaron correctamente.')
        return redirect('perfil')
    if accion == 'password' and pass_form.is_valid():
        pass_form.save()
        update_session_auth_hash(request, pass_form.user)
        messages.success(request, 'Tu contraseña se cambió correctamente.')
        return redirect('perfil')
    plantilla = 'core/panel/perfil.html' if es_personal(user) else 'core/perfil.html'
    return render(request, plantilla, {'datos_form': datos_form, 'pass_form': pass_form, 'accion': accion,
                                       'stats': {'viajes': user.solicitudes_viaje.count(),
                                                 'expedientes': user.expedientes.count()}})


# ==================================================================== Inicio del usuario

@login_required
def dashboard_view(request):
    if es_personal(request.user):
        return redirect('panel_inicio')
    u = request.user
    hoy = timezone.localdate()
    expedientes = list(Expediente.objects.filter(usuario=u).prefetch_related('documentos', 'abonos', 'vuelos'))
    saldo = sum((e.saldo for e in expedientes if e.saldo and e.saldo > 0), Decimal('0'))
    docs = sum(1 for e in expedientes if e.estado == 'en_curso' for d in e.documentos.all() if d.puede_subir)
    cotizaciones = (Cotizacion.objects.filter(solicitud__usuario=u, estado='pendiente', vigencia__gte=hoy)
                    .select_related('solicitud'))
    return render(request, 'core/dashboard.html', {
        'expedientes': [e for e in expedientes if e.estado == 'en_curso'][:4],
        'cotizaciones': cotizaciones,
        'citas': Cita.objects.filter(usuario=u, fecha__gte=hoy).exclude(estado='cancelada').select_related('asesor')[:3],
        'avisos': AvisoVuelo.objects.filter(expediente__usuario=u, fecha_aviso__gte=hoy - timedelta(days=30)),
        'stats': {'expedientes': sum(1 for e in expedientes if e.estado == 'en_curso'), 'docs': docs,
                  'cotizaciones': cotizaciones.count(), 'saldo': saldo},
    })


# ==================================================================== Cotizaciones (RS-05)

@login_required
def cotizar_view(request):
    user = request.user
    oferta = None
    codigo = request.GET.get('oferta') or request.POST.get('oferta')
    if codigo:
        oferta = Oferta.objects.filter(codigo=codigo, publicado=True).select_related('promocion').first()
    if request.method == 'POST':
        form = SolicitudViajeForm(request.POST)
        if form.is_valid():
            s = form.save(commit=False)
            s.usuario = user
            if oferta:  # RS-05.4
                s.oferta, s.oferta_codigo, s.oferta_nombre = oferta, oferta.codigo, oferta.titulo
                promo = oferta.promocion_vigente
                s.promocion_nombre = promo.titulo if promo else ''
            s.save()
            perfil = _perfil(user)
            perfil.cedula = perfil.cedula or s.cedula
            perfil.telefono = perfil.telefono or s.telefono
            perfil.save()
            messages.success(request, f'Recibimos tu solicitud {s.codigo}. Un asesor preparará tu cotización.')
            return redirect(s)
        messages.error(request, 'Falta información: revisa los campos marcados.')
    else:
        perfil = _perfil(user)
        inicial = {'nombre': user.get_full_name(), 'email': user.email, 'cedula': perfil.cedula,
                   'telefono': perfil.telefono, 'tipo': request.GET.get('tipo', 'vuelo'), 'trayecto': 'ida_vuelta'}
        if oferta:
            inicial.update({'tipo': oferta.tipo, 'origen': oferta.origen,
                            'destino': oferta.destino if oferta.tipo == 'vuelo' else f'{oferta.titulo} ({oferta.destino})',
                            'fecha_salida': oferta.fecha_salida, 'fecha_regreso': oferta.fecha_regreso,
                            'trayecto': 'ida_vuelta' if oferta.fecha_regreso else 'ida'})
            try:
                inicial['pasajeros'] = min(max(int(request.GET.get('pasajeros', 1)), 1), 20)
            except ValueError:
                pass
        form = SolicitudViajeForm(initial=inicial)
    return render(request, 'core/cotizar.html', {'form': form, 'oferta': oferta})


@login_required
def mis_solicitudes_view(request):
    estado = request.GET.get('estado', 'todas')
    qs = list(SolicitudViaje.objects.filter(usuario=request.user).prefetch_related('cotizaciones'))
    if estado == 'curso':
        qs = [s for s in qs if s.en_curso]
    elif estado == 'finalizadas':
        qs = [s for s in qs if not s.en_curso]
    return render(request, 'core/mis_solicitudes.html', {'items': qs, 'estado': estado})


@login_required
def solicitud_view(request, pk):
    s = get_object_or_404(SolicitudViaje, pk=pk, usuario=request.user)  # RS-02.3
    forms_aceptar = {}
    if request.method == 'POST':
        c = get_object_or_404(Cotizacion, pk=request.POST.get('cotizacion'), solicitud=s)
        accion = request.POST.get('accion')
        if c.estado != Cotizacion.Estado.PENDIENTE:
            messages.error(request, 'Esta cotización ya fue respondida.')
        elif c.vencida:
            messages.error(request, 'Esta cotización ya venció. Solicita a tu asesor una nueva propuesta.')
        elif accion == 'rechazar':
            c.estado, c.respondida_en = Cotizacion.Estado.RECHAZADA, timezone.now()
            c.save(update_fields=['estado', 'respondida_en'])
            s.actualizar_estado()
            messages.info(request, f'Rechazaste la cotización {c.codigo}.')
            return redirect(s)
        elif accion == 'aceptar':
            form = AceptarCotizacionForm(c, request.POST)
            if form.is_valid():
                c.estado, c.respondida_en = Cotizacion.Estado.ACEPTADA, timezone.now()
                c.contratar_seguro = True if c.incluye_seguro else form.cleaned_data['contratar_seguro']
                c.save(update_fields=['estado', 'respondida_en', 'contratar_seguro'])
                s.actualizar_estado()
                messages.success(request, f'¡Aceptaste la cotización {c.codigo}! Tu asesor se pondrá en contacto para continuar.')
                return redirect(s)
            forms_aceptar[c.pk] = form
    cotizaciones = list(s.cotizaciones.all())
    for c in cotizaciones:
        c.form_aceptar = forms_aceptar.get(c.pk) or AceptarCotizacionForm(c)
    return render(request, 'core/solicitud.html', {'s': s, 'cotizaciones': cotizaciones})


# ==================================================================== Expedientes (RS-06, RS-07, RS-08)

@login_required
def expedientes_view(request):
    qs = Expediente.objects.filter(usuario=request.user).prefetch_related('documentos', 'abonos', 'vuelos')
    return render(request, 'core/expedientes.html', {'items': qs})


@login_required
def expediente_view(request, pk):
    exp = get_object_or_404(Expediente.objects.select_related('asesor'), pk=pk, usuario=request.user)
    form = SubirDocumentoForm(exp)
    if request.method == 'POST':
        form = SubirDocumentoForm(exp, request.POST, request.FILES)
        if exp.estado != Expediente.Estado.EN_CURSO:
            messages.error(request, 'Este expediente ya no admite documentos.')
        elif form.is_valid():
            doc = form.cleaned_data['documento']
            servicios.subir_documento(doc, form.cleaned_data['archivo'], request.user)
            messages.success(request, f'Recibimos «{doc.nombre}». Tu asesor lo revisará.')
            return redirect(exp)
        else:
            messages.error(request, 'No se guardó el archivo. Revisa el mensaje junto al formulario.')
    documentos = exp.documentos.prefetch_related(
        Prefetch('archivos', queryset=ArchivoDocumento.objects.order_by('-subido')), 'revisiones')
    return render(request, 'core/expediente.html', {
        'e': exp, 'form': form, 'documentos': documentos,
        'cita_consular': exp.citas_consulares.first(), 'vuelos': exp.vuelos.all(),
        'documentos_viaje': exp.documentos_viaje.all(), 'avisos': exp.avisos.all(),
        'abonos': exp.abonos.all(), 'comprobantes': exp.comprobantes.all(),
    })


# ==================================================================== Citas (RS-09.2)

@login_required
def citas_view(request):
    hoy = timezone.localdate()
    citas = Cita.objects.filter(usuario=request.user).select_related('asesor')
    return render(request, 'core/citas.html', {
        'proximas': citas.filter(fecha__gte=hoy).exclude(estado='cancelada'),
        'pasadas': (citas.filter(fecha__lt=hoy) | citas.filter(estado='cancelada')).order_by('-fecha', '-hora'),
    })


# ==================================================================== Pagos (RS-10)

@login_required
def pagos_view(request):
    user = request.user
    form = ComprobanteForm(user, request.POST or None, request.FILES or None,
                           initial={'expediente': request.GET.get('servicio')})
    if request.method == 'POST':
        if form.is_valid():
            c = form.save(commit=False)
            c.enviado_por, c.nombre_original = user, form.cleaned_data['archivo'].name[:255]
            c.save()
            messages.success(request, 'Recibimos tu comprobante. Quedó «Pendiente de revisión» hasta que la agencia lo confirme.')
            return redirect('pagos')
        messages.error(request, 'No se guardó el comprobante. Revisa los campos marcados.')
    expedientes = Expediente.objects.filter(usuario=user).prefetch_related('abonos', 'comprobantes')
    return render(request, 'core/pagos.html', {'form': form, 'expedientes': expedientes})


# ==================================================================== Archivos privados (RNF-06)

ARCHIVOS = {
    'documento': (ArchivoDocumento, 'archivo', lambda o: o.documento.expediente),
    'boleto': (VueloContratado, 'boleto', lambda o: o.expediente),
    'viaje': (DocumentoViaje, 'archivo', lambda o: o.expediente),
    'cita': (CitaConsular, 'confirmacion', lambda o: o.expediente),
    'comprobante': (Comprobante, 'archivo', lambda o: o.expediente),
}


@login_required
def archivo_view(request, tipo, pk):
    if tipo not in ARCHIVOS:
        raise Http404
    Modelo, campo, expediente_de = ARCHIVOS[tipo]
    obj = get_object_or_404(Modelo, pk=pk)
    if not puede_ver_expediente(request.user, expediente_de(obj)):
        raise Http404
    f = getattr(obj, campo)
    nombre = getattr(obj, 'nombre_original', None) or f.name.rsplit('/', 1)[-1]
    return servir(request, f, nombre=nombre, descargar=request.GET.get('descargar') == '1')
