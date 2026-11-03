"""Sitio público: se consulta sin iniciar sesión (RS-03, RS-04, RS-05.7)."""
import re
import unicodedata

from django.contrib import messages
from django.db import DatabaseError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .archivos import servir
from .forms import BuscarVuelosForm, ConsultaForm
from .models import (REQUISITOS_VISA, Beneficio, Consulta, ContenidoSitio, Oferta, PreguntaFrecuente, Promocion,
                     Publicacion, Servicio)


def ofertas_publicas(tipo=None):
    qs = Oferta.objects.filter(publicado=True, fecha_salida__gte=timezone.localdate()).select_related('promocion')
    return qs.filter(tipo=tipo) if tipo else qs


def promociones_vigentes():
    hoy = timezone.localdate()
    return Promocion.objects.filter(publicado=True, fecha_inicio__lte=hoy, fecha_fin__gte=hoy)


def _procesar_consulta(request):
    """RS-04.5: guarda la consulta con fecha y hora o explica el problema."""
    form = ConsultaForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            try:
                c = Consulta.objects.create(nombre=form.cleaned_data['nombre'].strip(),
                                            telefono=form.cleaned_data['telefono'].strip(),
                                            motivo=form.cleaned_data['motivo'].strip())
            except DatabaseError:
                messages.error(request, 'No pudimos guardar tu consulta. Por favor, inténtalo de nuevo en unos minutos.')
            else:
                messages.success(request, f'¡Gracias, {c.nombre.split()[0]}! Recibimos tu consulta ({c.codigo}) el '
                                          f'{timezone.localtime(c.creado):%d/%m/%Y a las %H:%M}. Te contactaremos pronto.')
                return None, True
        else:
            messages.error(request, 'Revisa los datos del formulario de consulta.')
    return form, False


def inicio(request):
    form, enviada = _procesar_consulta(request)
    if enviada:
        return redirect(reverse('inicio') + '#consulta')
    return render(request, 'core/public/inicio.html', {
        'form': form,
        'servicios': Servicio.objects.filter(publicado=True),
        'beneficios': Beneficio.objects.filter(publicado=True),
        'promociones': promociones_vigentes()[:3],
        'vuelos': ofertas_publicas('vuelo')[:3],
        'paquetes': ofertas_publicas('paquete')[:3],
        'publicaciones': Publicacion.objects.filter(publicado=True)[:6],
        'preguntas': PreguntaFrecuente.objects.filter(publicado=True)[:4],
    })


def vuelos(request):
    """RS-05.7: todas las condiciones elegidas deben cumplirse."""
    form = BuscarVuelosForm(request.GET or None)
    qs = ofertas_publicas('vuelo')
    filtrando = False
    if form.is_valid():
        d = form.cleaned_data
        if d['destino']:
            qs = qs.filter(destino__icontains=d['destino'].strip())
        if d['fecha']:
            qs = qs.filter(fecha_salida=d['fecha'])
        if d['precio_max'] is not None:
            qs = qs.filter(precio_persona__lte=d['precio_max'])
        if d['duracion_max'] is not None:
            qs = qs.filter(duracion_horas__lte=d['duracion_max'])
        filtrando = any(v not in (None, '') for v in d.values())
    return render(request, 'core/public/vuelos.html', {'form': form, 'ofertas': qs, 'filtrando': filtrando})


def paquetes(request):
    return render(request, 'core/public/paquetes.html', {'ofertas': ofertas_publicas('paquete')})


def promociones(request):
    return render(request, 'core/public/promociones.html', {'promociones': promociones_vigentes().prefetch_related('ofertas')})


def oferta(request, codigo):
    o = get_object_or_404(Oferta.objects.select_related('promocion'), codigo=codigo, publicado=True)
    return render(request, 'core/public/oferta.html', {'o': o})


def visas(request):
    return render(request, 'core/public/visas.html', {'requisitos': REQUISITOS_VISA,
                                                      'servicio': Servicio.objects.filter(publicado=True, icono='passport').first()})


def nosotros(request):
    return render(request, 'core/public/nosotros.html', {'beneficios': Beneficio.objects.filter(publicado=True)})


def contacto(request):
    form, enviada = _procesar_consulta(request)
    if enviada:
        return redirect('contacto')
    return render(request, 'core/public/contacto.html', {'form': form})


def privacidad(request):
    return render(request, 'core/public/privacidad.html')


def terminos(request):
    return render(request, 'core/public/terminos.html')


def preguntas(request):
    return render(request, 'core/public/preguntas.html', {'preguntas': PreguntaFrecuente.objects.filter(publicado=True)})


# ---------------------------------------------------------------- Asistente virtual (RS-04.1)

def _normalizar(texto):
    texto = unicodedata.normalize('NFD', texto.lower())
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return set(re.findall(r'[a-z0-9]{3,}', texto))


VACIAS = {'que', 'como', 'cual', 'cuales', 'para', 'por', 'los', 'las', 'del', 'una', 'uno', 'con', 'mas', 'hay',
          'puedo', 'quiero', 'tienen', 'tiene', 'son', 'esta', 'este', 'ustedes', 'sus', 'mis', 'necesito', 'saber'}


@require_GET
def asistente(request):
    pregunta = request.GET.get('q', '')[:300]
    palabras = _normalizar(pregunta) - VACIAS
    sitio = ContenidoSitio.actual()
    if not palabras:
        return JsonResponse({'respuesta': 'Escribe tu pregunta, por ejemplo: «¿Cómo solicito una cotización?».',
                             'encontrada': True})

    # Intenciones básicas exigidas: servicios, cotizaciones y horarios.
    if palabras & {'horario', 'horarios', 'atienden', 'abren', 'hora', 'horas', 'abierto'}:
        return JsonResponse({'respuesta': f'Nuestro horario de atención es: {sitio.horario}. '
                                          f'Estamos en {sitio.direccion}, {sitio.ciudad}.', 'encontrada': True})
    if palabras & {'cotizar', 'cotizacion', 'cotizaciones', 'presupuesto', 'precio', 'precios', 'costo', 'cuesta'}:
        return JsonResponse({'respuesta': 'Para solicitar una cotización: elige una oferta en «Vuelos» o «Paquetes» y '
                                          'pulsa «Solicitar cotización», o usa «Cotizar viaje» en tu cuenta. Necesitas '
                                          'iniciar sesión (crear una cuenta es gratis). Un asesor te enviará la propuesta '
                                          'y podrás aceptarla o rechazarla desde tu cuenta.',
                             'enlace': reverse('cotizar'), 'enlace_texto': 'Solicitar cotización', 'encontrada': True})
    if palabras & {'servicio', 'servicios', 'ofrecen', 'hacen'}:
        lista = ', '.join(s.titulo for s in Servicio.objects.filter(publicado=True)) or 'asesoría de visas, vuelos y paquetes turísticos'
        return JsonResponse({'respuesta': f'Ofrecemos: {lista}.', 'enlace': reverse('inicio') + '#servicios',
                             'enlace_texto': 'Ver servicios', 'encontrada': True})

    mejor, puntaje = None, 0
    for p in PreguntaFrecuente.objects.filter(publicado=True):
        claves = _normalizar(f'{p.pregunta} {p.palabras_clave}') - VACIAS
        coincidencias = len(palabras & claves)
        if coincidencias > puntaje:
            mejor, puntaje = p, coincidencias
    if mejor:
        return JsonResponse({'respuesta': mejor.respuesta, 'pregunta': mejor.pregunta, 'encontrada': True})

    return JsonResponse({
        'respuesta': 'No tengo una respuesta para eso. Escríbenos por WhatsApp y un asesor te ayudará.',
        'enlace': sitio.whatsapp_url, 'enlace_texto': 'Abrir WhatsApp', 'encontrada': False,
    })


# ---------------------------------------------------------------- Archivos públicos

def archivo_publico(request, tipo, pk):
    if tipo == 'tutorial':
        sitio = ContenidoSitio.actual()
        f = sitio.video_tutorial
    else:
        pub = get_object_or_404(Publicacion, pk=pk, publicado=True)
        f = {'imagen': pub.imagen, 'video': pub.video}.get(tipo)
    return servir(request, f)
