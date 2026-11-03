from .models import ContenidoSitio
from .permisos import es_admin, es_asesor, es_personal


def _pendientes(user):
    """Contadores del menú lateral del panel."""
    from .models import Comprobante, Consulta, DocumentoRequerido, Expediente, SolicitudViaje
    from .permisos import filtrar_asignados
    exps = filtrar_asignados(Expediente.objects.filter(estado='en_curso'), user)
    consultas = Consulta.objects.filter(estado='nueva') if es_admin(user) else Consulta.objects.filter(asesor=user, estado='asignada')
    return {
        'consultas': consultas.count(),
        'solicitudes': filtrar_asignados(SolicitudViaje.objects.filter(estado__in=['recibida', 'en_atencion']), user).count(),
        'documentos': DocumentoRequerido.objects.filter(expediente__in=exps, estado__in=['recibido', 'revision']).count(),
        'pagos': Comprobante.objects.filter(expediente__in=filtrar_asignados(Expediente.objects.all(), user),
                                            estado='pendiente').count(),
    }


def sitio(request):
    """Datos de la agencia y rol del usuario, disponibles en todas las plantillas."""
    u = request.user
    contexto = {
        'sitio': ContenidoSitio.actual(),
        'es_admin': es_admin(u),
        'es_asesor': es_asesor(u),
        'es_personal': es_personal(u),
    }
    if contexto['es_personal'] and request.path.startswith('/panel/'):
        contexto['pendientes'] = _pendientes(u)
    return contexto
