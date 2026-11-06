"""Panel del personal: administrador y asesores (reemplaza al /admin/ de Django)."""
import re
from datetime import date, timedelta
from itertools import chain

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import servicios
from .forms import (AsignarForm, AvisoVueloForm, BeneficioForm, CitaConsularForm, CitaForm, CorreoConsuladoForm,
                    CotizacionForm, CrearPersonalForm, DocumentoRequeridoForm, DocumentoViajeForm, EtapaForm,
                    ExpedienteForm, OfertaForm, PreguntaForm, PromocionForm, PublicacionForm,
                    RechazoComprobanteForm, ResultadoForm, RevisionForm, SeguimientoForm, ServicioForm, SitioForm,
                    VueloContratadoForm)
from .models import (ArchivoDocumento, AvisoVuelo, Beneficio, Cita, CitaConsular, Comprobante, Consulta,
                     ContenidoSitio, CorreoConsulado, DocumentoRequerido, DocumentoViaje, Expediente, Oferta,
                     Perfil, PreguntaFrecuente, Promocion, Publicacion, Servicio, SolicitudViaje, VueloContratado)
from .permisos import admin_required, es_admin, filtrar_asignados, personal_required, puede_ver_expediente

User = get_user_model()


def _volver(request, defecto):
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        return redirect(destino)
    return redirect(defecto)


def _paginar(request, items, n=20):
    return Paginator(items, n).get_page(request.GET.get('p'))


# ==================================================================== Resumen

@personal_required
def panel_inicio(request):
    u, hoy = request.user, timezone.localdate()
    exps = filtrar_asignados(Expediente.objects.all(), u)
    docs = DocumentoRequerido.objects.filter(expediente__in=exps, expediente__estado='en_curso')
    comprobantes = Comprobante.objects.filter(expediente__in=exps, estado='pendiente').select_related('expediente')
    consultas = Consulta.objects.filter(estado='nueva') if es_admin(u) else Consulta.objects.filter(asesor=u, estado='asignada')
    solicitudes = filtrar_asignados(SolicitudViaje.objects.filter(estado__in=['recibida', 'en_atencion']), u)
    citas = Cita.objects.filter(fecha=hoy).exclude(estado='cancelada').select_related('usuario', 'asesor')
    if not es_admin(u):
        citas = citas.filter(asesor=u)
    correos = CorreoConsulado.objects.filter(expediente__in=exps, proxima_revision__lte=hoy, respuesta='').select_related('expediente')
    return render(request, 'core/panel/inicio.html', {
        'stats': {
            'consultas': consultas.count(), 'solicitudes': solicitudes.count(),
            'expedientes': exps.filter(estado='en_curso').count(),
            'por_revisar': docs.filter(estado__in=['recibido', 'revision']).count(),
            'pendientes_usuario': docs.filter(estado__in=['pendiente', 'correccion']).count(),
            'comprobantes': comprobantes.count(),
            'sin_asignar': (SolicitudViaje.objects.filter(asesor__isnull=True).exclude(estado='cancelada').count()
                            + Expediente.objects.filter(asesor__isnull=True, estado='en_curso').count()) if es_admin(u) else None,
        },
        'citas': citas, 'correos': correos[:5],
        'docs_revisar': docs.filter(estado__in=['recibido', 'revision']).select_related('expediente')[:6],
        'comprobantes': comprobantes[:5],
    })


# ==================================================================== Consultas (RS-04.6)

@personal_required
def panel_consultas(request):
    u = request.user
    if request.method == 'POST':
        c = get_object_or_404(filtrar_asignados(Consulta.objects.all(), u), pk=request.POST.get('consulta'))
        if request.POST.get('accion') == 'asignar' and es_admin(u):
            form = AsignarForm(request.POST)
            if form.is_valid():
                servicios.asignar(c, form.cleaned_data['asesor'], u)
                messages.success(request, f'{c.codigo} asignada a {form.cleaned_data["asesor"].get_full_name()}.')
        elif request.POST.get('accion') == 'atendida':
            c.estado = Consulta.Estado.ATENDIDA
            c.save(update_fields=['estado'])
            messages.success(request, f'{c.codigo} marcada como atendida.')
        return _volver(request, 'panel_consultas')
    estado = request.GET.get('estado', 'abiertas')
    qs = filtrar_asignados(Consulta.objects.select_related('asesor', 'asignado_por'), u)
    if estado == 'abiertas':
        qs = qs.exclude(estado='atendida')
    elif estado in Consulta.Estado.values:
        qs = qs.filter(estado=estado)
    return render(request, 'core/panel/consultas.html', {'pagina': _paginar(request, qs), 'estado': estado,
                                                         'asignar_form': AsignarForm()})


# ==================================================================== Solicitudes de cotización (RS-05)

def _buscar(qs, q, campos, prefijo):
    if not q:
        return qs
    filtro = Q()
    for c in campos:
        filtro |= Q(**{f'{c}__icontains': q})
    m = re.fullmatch(rf'(?:{prefijo}-?)?0*(\d+)', q.strip(), re.I)
    if m:
        filtro |= Q(pk=int(m.group(1)))
    return qs.filter(filtro)


@personal_required
def panel_solicitudes(request):
    u = request.user
    estado, q = request.GET.get('estado', 'abiertas'), request.GET.get('q', '').strip()
    qs = filtrar_asignados(SolicitudViaje.objects.select_related('usuario', 'asesor'), u)
    qs = _buscar(qs, q, ['origen', 'destino', 'nombre', 'cedula', 'email', 'oferta_codigo'], 'COT')
    if estado == 'abiertas':
        qs = qs.filter(estado__in=['recibida', 'en_atencion', 'cotizada'])
    elif estado == 'sin_asignar':
        qs = qs.filter(asesor__isnull=True).exclude(estado='cancelada')
    elif estado in SolicitudViaje.Estado.values:
        qs = qs.filter(estado=estado)
    return render(request, 'core/panel/solicitudes.html', {'pagina': _paginar(request, qs), 'estado': estado, 'q': q,
                                                           'estados': SolicitudViaje.Estado.choices})


@personal_required
def panel_solicitud(request, pk):
    u = request.user
    s = get_object_or_404(filtrar_asignados(SolicitudViaje.objects.select_related('usuario', 'asesor', 'asignado_por'), u), pk=pk)
    cot_form, asignar_form = CotizacionForm(), AsignarForm(initial={'asesor': s.asesor_id})
    accion = request.POST.get('accion') if request.method == 'POST' else None
    if accion == 'asignar' and es_admin(u):
        asignar_form = AsignarForm(request.POST)
        if asignar_form.is_valid():
            servicios.asignar(s, asignar_form.cleaned_data['asesor'], u)
            messages.success(request, 'Asesor asignado.')
            return redirect(s.get_panel_url())
    elif accion == 'cotizacion':
        if not (es_admin(u) or s.asesor_id == u.id):
            raise Http404
        cot_form = CotizacionForm(request.POST)
        if cot_form.is_valid():
            c = cot_form.save(commit=False)
            c.solicitud, c.creado_por = s, u
            c.save()
            s.actualizar_estado()
            messages.success(request, f'Cotización {c.codigo} registrada como «Pendiente de respuesta». El usuario ya puede verla.')
            return redirect(s.get_panel_url())
    elif accion == 'cancelar':
        s.estado = SolicitudViaje.Estado.CANCELADA
        s.save(update_fields=['estado', 'actualizado'])
        messages.success(request, 'Solicitud cancelada.')
        return redirect(s.get_panel_url())
    return render(request, 'core/panel/solicitud.html', {
        's': s, 'cot_form': cot_form, 'asignar_form': asignar_form,
        'cotizaciones': s.cotizaciones.select_related('creado_por'),
        'asignaciones': s.asignaciones.select_related('asesor', 'asignado_por'),
        'expedientes': s.expedientes.all(),
    })


# ==================================================================== Expedientes (RS-06, RS-07, RS-08)

@personal_required
def panel_expedientes(request):
    u = request.user
    tipo, estado, q = request.GET.get('tipo', 'todos'), request.GET.get('estado', 'en_curso'), request.GET.get('q', '').strip()
    qs = filtrar_asignados(Expediente.objects.select_related('usuario', 'asesor').prefetch_related('documentos', 'vuelos'), u)
    qs = _buscar(qs, q, ['nombre', 'documento_identidad', 'pasaporte', 'pais', 'destino', 'paquete_nombre', 'usuario__email'], 'EXP')
    if tipo in Expediente.Tipo.values:
        qs = qs.filter(tipo=tipo)
    if estado in Expediente.Estado.values:
        qs = qs.filter(estado=estado)
    elif estado == 'sin_asignar':
        qs = qs.filter(asesor__isnull=True)
    return render(request, 'core/panel/expedientes.html', {'pagina': _paginar(request, qs), 'tipo': tipo,
                                                           'estado': estado, 'q': q})


@personal_required
def panel_expediente_nuevo(request):
    """RS-06.1 / RS-08.2: los datos de la cuenta se proponen para revisarlos y completarlos."""
    u = request.user
    inicial = {'tipo': request.GET.get('tipo', 'visa')}
    solicitud = None
    if request.GET.get('solicitud'):
        solicitud = get_object_or_404(filtrar_asignados(SolicitudViaje.objects.all(), u), pk=request.GET['solicitud'])
        inicial.update({'usuario': solicitud.usuario_id, 'tipo': solicitud.tipo, 'nombre': solicitud.nombre,
                        'telefono': solicitud.telefono, 'documento_identidad': solicitud.cedula, 'email': solicitud.email,
                        'destino': solicitud.destino, 'fecha_salida': solicitud.fecha_salida,
                        'fecha_regreso': solicitud.fecha_regreso, 'asesor': solicitud.asesor_id,
                        'paquete_nombre': solicitud.oferta_nombre if solicitud.tipo in ('paquete', 'hospedaje') else ''})
        aceptada = solicitud.cotizaciones.filter(estado='aceptada').first()
        if aceptada:
            inicial.update({'precio_total': aceptada.precio_total, 'servicios_incluidos': aceptada.servicios_incluidos})
    elif request.GET.get('usuario'):
        cliente = get_object_or_404(User.objects.select_related('perfil'), pk=request.GET['usuario'], perfil__rol='usuario')
        inicial.update({'usuario': cliente.pk, 'nombre': cliente.get_full_name(), 'email': cliente.email,
                        'telefono': cliente.perfil.telefono, 'documento_identidad': cliente.perfil.cedula})
    form = ExpedienteForm(request.POST or None, initial=inicial, user=u)
    if request.method == 'POST' and form.is_valid():
        exp = form.save(commit=False)
        exp.creado_por = u
        if request.POST.get('solicitud'):
            exp.solicitud = filtrar_asignados(SolicitudViaje.objects.all(), u).filter(pk=request.POST['solicitud']).first()
        asesor = form.cleaned_data.get('asesor') if es_admin(u) else u
        exp.asesor = None
        exp.save()
        if asesor:
            servicios.asignar(exp, asesor, u)
        messages.success(request, f'Expediente {exp.codigo} creado.')
        return redirect(exp.get_panel_url())
    return render(request, 'core/panel/expediente_form.html', {'form': form, 'solicitud': solicitud,
                                                               'usuarios_json': _usuarios_json()})


def _usuarios_json():
    """Datos de cada cuenta para completar el formulario al elegirla (RS-08.2)."""
    return {str(x.pk): {'nombre': x.get_full_name(), 'email': x.email, 'telefono': x.perfil.telefono,
                        'documento': x.perfil.cedula}
            for x in User.objects.filter(is_active=True, perfil__rol='usuario').select_related('perfil')}


def _expediente_visible(request, pk):
    exp = get_object_or_404(Expediente.objects.select_related('usuario', 'asesor', 'asignado_por', 'solicitud'), pk=pk)
    if not puede_ver_expediente(request.user, exp) or exp.usuario_id == request.user.id:
        raise Http404  # RS-02.2
    return exp


@personal_required
def panel_expediente_editar(request, pk):
    exp = _expediente_visible(request, pk)
    form = ExpedienteForm(request.POST or None, instance=exp, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Datos del expediente actualizados.')
        return redirect(exp.get_panel_url())
    return render(request, 'core/panel/expediente_form.html', {'form': form, 'e': exp})


ACCIONES_EXPEDIENTE = {
    # accion: (Form, mensaje)
    'cita_consular': (CitaConsularForm, 'Cita consular registrada. El usuario ya puede verla.'),
    'correo': (CorreoConsuladoForm, 'Correo al consulado registrado.'),
    'vuelo': (VueloContratadoForm, 'Datos del vuelo registrados.'),
    'doc_viaje': (DocumentoViajeForm, 'Documento de viaje agregado.'),
    'aviso': (AvisoVueloForm, 'Aviso registrado. Ya aparece en la cuenta del usuario.'),
    'doc_nuevo': (DocumentoRequeridoForm, 'Documento solicitado. Queda «Pendiente de entrega».'),
}

ELIMINABLES = {'vuelo': VueloContratado, 'doc_viaje': DocumentoViaje, 'cita_consular': CitaConsular,
               'correo': CorreoConsulado, 'aviso': AvisoVuelo}


@personal_required
def panel_expediente(request, pk):
    u = request.user
    exp = _expediente_visible(request, pk)
    accion = request.POST.get('accion') if request.method == 'POST' else None
    forms = {k: F() for k, (F, _) in ACCIONES_EXPEDIENTE.items()}
    etapa_form = EtapaForm(exp) if exp.es_visa else None
    resultado_form = ResultadoForm(instance=exp) if exp.es_visa else None
    seguimiento_form = SeguimientoForm(instance=exp)
    asignar_form = AsignarForm(initial={'asesor': exp.asesor_id})
    revision_forms, rechazo_forms = {}, {}
    abrir = None  # sección a mostrar abierta si hubo errores

    if accion in ACCIONES_EXPEDIENTE:
        F, mensaje = ACCIONES_EXPEDIENTE[accion]
        form = F(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.expediente = exp
            for campo in ('registrado_por', 'subido_por', 'creado_por'):
                if hasattr(obj, campo):
                    setattr(obj, campo, u)
            obj.save()
            servicios.tocar(exp.pk)
            messages.success(request, mensaje)
            return redirect(exp.get_panel_url() + f'#{accion}')
        forms[accion], abrir = form, accion
        messages.error(request, 'Revisa los campos marcados.')
    elif accion == 'eliminar' and request.POST.get('tipo') in ELIMINABLES:
        get_object_or_404(ELIMINABLES[request.POST['tipo']], pk=request.POST.get('id'), expediente=exp).delete()
        messages.success(request, 'Registro eliminado.')
        return redirect(exp.get_panel_url())
    elif accion == 'doc_eliminar':
        d = get_object_or_404(DocumentoRequerido, pk=request.POST.get('id'), expediente=exp)
        if d.archivos.exists():
            messages.error(request, 'No se puede quitar un documento que ya tiene archivos entregados.')
        else:
            d.delete()
            messages.success(request, 'Documento quitado de la lista.')
        return redirect(exp.get_panel_url() + '#documentos')
    elif accion == 'revisar':
        d = get_object_or_404(DocumentoRequerido, pk=request.POST.get('id'), expediente=exp)
        form = RevisionForm(d, request.POST)
        if form.is_valid():
            servicios.revisar_documento(d, form.cleaned_data['accion_doc'], form.cleaned_data['comentario'], u)
            messages.success(request, f'«{d.nombre}»: {d.get_estado_display()}.')
            return redirect(exp.get_panel_url() + '#documentos')
        revision_forms[d.pk] = form
        messages.error(request, 'No se guardó la revisión: ' + ' '.join(sum(form.errors.values(), [])))
    elif accion == 'etapa' and exp.es_visa:
        etapa_form = EtapaForm(exp, request.POST)
        if etapa_form.is_valid():
            if servicios.cambiar_etapa(exp, etapa_form.cleaned_data['etapa'], u, etapa_form.cleaned_data['fecha_presentacion']):
                messages.success(request, f'Etapa actualizada a «{exp.get_etapa_display()}». Quedó en el historial.')
            return redirect(exp.get_panel_url())
        abrir = 'etapa'
    elif accion == 'resultado' and exp.es_visa:
        resultado_form = ResultadoForm(request.POST, instance=exp)
        if resultado_form.is_valid():
            resultado_form.save()
            messages.success(request, 'Resultado consular registrado.')
            return redirect(exp.get_panel_url())
        abrir = 'resultado'
    elif accion == 'seguimiento':
        seguimiento_form = SeguimientoForm(request.POST, instance=exp)
        if seguimiento_form.is_valid():
            seguimiento_form.save()
            messages.success(request, 'Cambios guardados.')
            return redirect(exp.get_panel_url())
        abrir = 'seguimiento'
    elif accion == 'asignar' and es_admin(u):
        asignar_form = AsignarForm(request.POST)
        if asignar_form.is_valid():
            servicios.asignar(exp, asignar_form.cleaned_data['asesor'], u)
            messages.success(request, 'Asesor responsable actualizado.')
            return redirect(exp.get_panel_url())
    elif accion in ('confirmar', 'rechazar'):
        c = get_object_or_404(Comprobante, pk=request.POST.get('id'), expediente=exp)
        if accion == 'confirmar':
            ok = servicios.confirmar_comprobante(c.pk, u)
            if ok == 'excede':
                messages.error(request, f'No se confirmó: el monto (${c.monto:,.2f}) supera el saldo pendiente '
                                        f'(${exp.saldo:,.2f}). Rechaza el comprobante indicando el motivo.')
            elif ok:
                messages.success(request, 'Pago confirmado y registrado como abono.')
            else:
                messages.error(request, 'Este comprobante ya había sido revisado.')
            return redirect(exp.get_panel_url() + '#pagos')
        form = RechazoComprobanteForm(request.POST)
        if form.is_valid():
            servicios.rechazar_comprobante(c.pk, form.cleaned_data['motivo'], u)
            messages.success(request, 'Comprobante rechazado. El usuario verá el motivo.')
            return redirect(exp.get_panel_url() + '#pagos')
        rechazo_forms[c.pk] = form
        abrir = 'pagos'

    documentos = list(exp.documentos.prefetch_related(
        Prefetch('archivos', queryset=ArchivoDocumento.objects.order_by('-subido')), 'revisiones__revisor'))
    for d in documentos:
        d.form = revision_forms.get(d.pk) or RevisionForm(d)
    comprobantes = list(exp.comprobantes.select_related('revisado_por'))
    for c in comprobantes:
        c.form = rechazo_forms.get(c.pk) or RechazoComprobanteForm()
    return render(request, 'core/panel/expediente.html', {
        'e': exp, 'forms': forms, 'etapa_form': etapa_form, 'resultado_form': resultado_form,
        'seguimiento_form': seguimiento_form, 'asignar_form': asignar_form, 'abrir': abrir,
        'documentos': documentos, 'comprobantes': comprobantes,
        'cambios': exp.cambios_etapa.select_related('usuario'),
        'asignaciones': exp.asignaciones.select_related('asesor', 'asignado_por'),
        'citas_consulares': exp.citas_consulares.all(), 'correos': exp.correos.all(), 'vuelos': exp.vuelos.all(),
        'documentos_viaje': exp.documentos_viaje.all(), 'avisos': exp.avisos.all(), 'abonos': exp.abonos.all(),
        'citas': exp.citas.select_related('asesor'),
    })


@personal_required
def panel_documentos(request):
    """RS-07.5: documentos pendientes de entrega o con corrección requerida."""
    u = request.user
    vista = request.GET.get('vista', 'usuario')
    estados = ['pendiente', 'correccion'] if vista == 'usuario' else ['recibido', 'revision']
    exps = filtrar_asignados(Expediente.objects.filter(estado='en_curso'), u)
    docs = (DocumentoRequerido.objects.filter(expediente__in=exps, estado__in=estados)
            .select_related('expediente__usuario').prefetch_related('revisiones').order_by('expediente_id', 'pk'))
    return render(request, 'core/panel/documentos.html', {'pagina': _paginar(request, docs, 30), 'vista': vista})


# ==================================================================== Pagos (RS-10)

@personal_required
def panel_pagos(request):
    u = request.user
    estado = request.GET.get('estado', 'pendiente')
    exps = filtrar_asignados(Expediente.objects.all(), u)
    qs = Comprobante.objects.filter(expediente__in=exps).select_related('expediente__usuario', 'revisado_por')
    if estado in Comprobante.Estado.values:
        qs = qs.filter(estado=estado)
    saldos = [e for e in exps.filter(precio_total__isnull=False, estado='en_curso').prefetch_related('abonos')]
    return render(request, 'core/panel/pagos.html', {'pagina': _paginar(request, qs), 'estado': estado,
                                                     'saldos': saldos, 'rechazo_form': RechazoComprobanteForm()})


# ==================================================================== Agenda (RS-09)

@personal_required
def panel_agenda(request):
    """RS-09.3: citas que atenderá en la fecha seleccionada."""
    u = request.user
    try:
        dia = date.fromisoformat(request.GET.get('fecha', ''))
    except ValueError:
        dia = timezone.localdate()
    citas = Cita.objects.filter(fecha=dia).select_related('usuario', 'asesor', 'expediente').order_by('hora')
    asesor_id = request.GET.get('asesor', '')
    if not es_admin(u):
        citas = citas.filter(asesor=u)
    elif asesor_id:
        citas = citas.filter(asesor_id=asesor_id)
    from .forms import personal_activo
    return render(request, 'core/panel/agenda.html', {
        'dia': dia, 'citas': citas, 'anterior': dia - timedelta(days=1), 'siguiente': dia + timedelta(days=1),
        'hoy': timezone.localdate(), 'asesores': personal_activo() if es_admin(u) else None, 'asesor_id': asesor_id,
    })


@personal_required
def panel_cita(request, pk=None):
    """RS-09.1: programar (o reprogramar) una cita."""
    u = request.user
    cita = None
    if pk:
        cita = get_object_or_404(Cita, pk=pk)
        if not es_admin(u) and cita.asesor_id != u.id:
            raise Http404
    inicial = {'asesor': u.pk, 'usuario': request.GET.get('usuario'), 'direccion': ContenidoSitio.actual().direccion}
    form = CitaForm(request.POST or None, instance=cita, initial=inicial)
    if request.method == 'POST' and form.is_valid():
        c = form.save(commit=False)
        if cita is None:
            c.creado_por = u
            if request.GET.get('expediente'):
                c.expediente = Expediente.objects.filter(pk=request.GET['expediente'], usuario=c.usuario).first()
        elif {'fecha', 'hora'} & set(form.changed_data) and c.estado == Cita.Estado.PROGRAMADA:
            c.estado = Cita.Estado.REPROGRAMADA
        c.save()
        messages.success(request, 'Cita guardada. Ya aparece en «Mis citas» del usuario.')
        return redirect(f"{reverse('panel_agenda')}?fecha={c.fecha.isoformat()}")
    return render(request, 'core/panel/cita_form.html', {'form': form, 'cita': cita})


# ==================================================================== Cuentas (RS-01.5)

@admin_required
def panel_clientes(request):
    q = request.GET.get('q', '').strip()
    qs = (User.objects.filter(perfil__rol='usuario').select_related('perfil')
          .annotate(n_exp=Count('expedientes', distinct=True), n_sol=Count('solicitudes_viaje', distinct=True))
          .order_by('-date_joined'))
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
                       | Q(perfil__cedula__icontains=q) | Q(perfil__telefono__icontains=q))
    return render(request, 'core/panel/clientes.html', {'pagina': _paginar(request, qs), 'q': q})


@admin_required
def panel_cliente(request, pk):
    cliente = get_object_or_404(User.objects.select_related('perfil'), pk=pk, perfil__rol='usuario')
    items = sorted(chain(cliente.solicitudes_viaje.all(), cliente.expedientes.all()), key=lambda s: s.creado, reverse=True)
    return render(request, 'core/panel/cliente.html', {'cliente': cliente, 'items': items,
                                                       'citas': cliente.citas.select_related('asesor')})


@admin_required
def panel_personal(request):
    form = CrearPersonalForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        nuevo = form.save()
        messages.success(request, f'Cuenta de {nuevo.perfil.get_rol_display().lower()} creada para {nuevo.email}.')
        return redirect('panel_personal')
    personal = list(User.objects.filter(perfil__rol__in=['asesor', 'admin']).select_related('perfil')
                    .order_by('perfil__rol', 'first_name'))
    for p in personal:
        p.n_exp = Expediente.objects.filter(asesor=p, estado='en_curso').count()
    return render(request, 'core/panel/personal.html', {'form': form, 'personal': personal})


@admin_required
@require_POST
def panel_cuenta_estado(request, pk):
    """Habilitar o deshabilitar una cuenta de usuario o asesor (se conservan sus registros)."""
    cuenta = get_object_or_404(User, pk=pk)
    if cuenta == request.user:
        messages.error(request, 'No puedes deshabilitar tu propia cuenta.')
    else:
        cuenta.is_active = not cuenta.is_active
        cuenta.save(update_fields=['is_active'])
        messages.success(request, f'Cuenta de {cuenta.email} {"habilitada" if cuenta.is_active else "deshabilitada"}.')
    return _volver(request, 'panel_inicio')


# ==================================================================== Contenido público (RS-03.1)

CONTENIDO = {
    'ofertas': (Oferta, OfertaForm, 'Ofertas de vuelos, paquetes y hospedaje', 'Oferta'),
    'promociones': (Promocion, PromocionForm, 'Promociones', 'Promoción'),
    'servicios': (Servicio, ServicioForm, 'Servicios', 'Servicio'),
    'beneficios': (Beneficio, BeneficioForm, '¿Por qué viajar con nosotros?', 'Beneficio'),
    'preguntas': (PreguntaFrecuente, PreguntaForm, 'Preguntas frecuentes', 'Pregunta'),
    'publicaciones': (Publicacion, PublicacionForm, 'Publicaciones de redes', 'Publicación'),
}


@admin_required
def panel_contenido(request):
    secciones = [{'clave': k, 'titulo': t, 'total': M.objects.count(), 'publicados': M.objects.filter(publicado=True).count()}
                 for k, (M, F, t, _) in CONTENIDO.items()]
    return render(request, 'core/panel/contenido.html', {'secciones': secciones, 'sitio_obj': ContenidoSitio.actual()})


@admin_required
def panel_contenido_lista(request, seccion):
    if seccion not in CONTENIDO:
        raise Http404
    M, F, titulo, singular = CONTENIDO[seccion]
    if request.method == 'POST':
        obj = get_object_or_404(M, pk=request.POST.get('id'))
        if request.POST.get('accion') == 'publicar':
            obj.publicado = not obj.publicado
            obj.save(update_fields=['publicado', 'actualizado'])
            messages.success(request, f'«{obj}» {"publicado" if obj.publicado else "retirado de la vista pública"}.')
        elif request.POST.get('accion') == 'eliminar':
            obj.delete()
            messages.success(request, 'Elemento eliminado.')
        return redirect('panel_contenido_lista', seccion=seccion)
    return render(request, 'core/panel/contenido_lista.html', {'items': M.objects.all(), 'seccion': seccion,
                                                               'titulo': titulo, 'singular': singular})


@admin_required
def panel_contenido_form(request, seccion, pk=None):
    if seccion not in CONTENIDO:
        raise Http404
    M, F, titulo, singular = CONTENIDO[seccion]
    obj = get_object_or_404(M, pk=pk) if pk else None
    form = F(request.POST or None, request.FILES or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{singular} guardado/a.')
        return redirect('panel_contenido_lista', seccion=seccion)
    return render(request, 'core/panel/contenido_form.html', {'form': form, 'obj': obj, 'seccion': seccion,
                                                              'titulo': titulo, 'singular': singular})


@admin_required
def panel_sitio(request):
    sitio = ContenidoSitio.actual()
    form = SitioForm(request.POST or None, request.FILES or None, instance=sitio)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Información de la agencia actualizada.')
        return redirect('panel_contenido')
    return render(request, 'core/panel/contenido_form.html', {'form': form, 'obj': sitio, 'seccion': 'sitio',
                                                              'titulo': 'Información de la agencia', 'singular': 'Información'})
