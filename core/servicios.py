"""Reglas de negocio (se usan desde las vistas y desde las pruebas)."""
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (Abono, ArchivoDocumento, Asignacion, CambioEtapa, Comprobante, Consulta, DocumentoRequerido,
                     Expediente, RevisionDocumento, SolicitudViaje)


def asignar(obj, asesor, por):
    """RS-02.4 / RS-04.6: asigna o cambia el asesor y guarda quién y cuándo."""
    obj.asesor, obj.asignado_por, obj.asignado_en = asesor, por, timezone.now()
    campos = ['asesor', 'asignado_por', 'asignado_en']
    if isinstance(obj, Consulta) and obj.estado == Consulta.Estado.NUEVA:
        obj.estado = Consulta.Estado.ASIGNADA
        campos.append('estado')
    if isinstance(obj, SolicitudViaje) and obj.estado == SolicitudViaje.Estado.RECIBIDA:
        obj.estado = SolicitudViaje.Estado.EN_ATENCION
        campos.append('estado')
    obj.save(update_fields=campos)
    clave = {Consulta: 'consulta', SolicitudViaje: 'solicitud', Expediente: 'expediente'}[type(obj)]
    Asignacion.objects.create(**{clave: obj}, asesor=asesor, asignado_por=por)


def cambiar_etapa(exp, nueva, usuario, fecha_presentacion=None):
    """RS-06.2 / RS-06.6: guarda el historial automáticamente."""
    anterior = exp.etapa
    exp.etapa = nueva
    if nueva == Expediente.Etapa.PRESENTADO:
        exp.fecha_presentacion = fecha_presentacion
    exp.save()
    if anterior != nueva:
        CambioEtapa.objects.create(expediente=exp, anterior=anterior, nueva=nueva, usuario=usuario)
    return anterior != nueva


def subir_documento(documento, archivo, usuario):
    """RS-07.2 / RS-07.4: el archivo queda Recibido; los anteriores se conservan."""
    if not documento.puede_subir:
        raise ValueError('Este documento no admite archivos en su estado actual.')
    ArchivoDocumento.objects.create(documento=documento, archivo=archivo, nombre_original=archivo.name[:255],
                                    tamano=archivo.size, subido_por=usuario)
    documento.estado = DocumentoRequerido.Estado.RECIBIDO
    documento.save(update_fields=['estado', 'actualizado'])
    tocar(documento.expediente_id)


def tocar(expediente_id):
    """Actualiza la «última actualización» (RS-08.1) sin reescribir otros campos con datos viejos."""
    Expediente.objects.filter(pk=expediente_id).update(actualizado=timezone.now())


def revisar_documento(documento, accion, comentario, revisor):
    """RS-07.3: guarda el resultado, el revisor y la fecha y hora."""
    documento.estado = accion
    documento.save(update_fields=['estado', 'actualizado'])
    RevisionDocumento.objects.create(documento=documento, estado=accion, comentario=comentario.strip(), revisor=revisor)
    tocar(documento.expediente_id)


def confirmar_comprobante(comprobante_id, revisor):
    """RS-10.3 / RNF-07: un comprobante genera como máximo un abono, aunque se confirme dos veces a la vez."""
    try:
        with transaction.atomic():
            c = Comprobante.objects.select_for_update().get(pk=comprobante_id)
            if c.estado != Comprobante.Estado.PENDIENTE:
                return False
            c.estado, c.revisado_por, c.revisado_en = Comprobante.Estado.CONFIRMADO, revisor, timezone.now()
            c.save(update_fields=['estado', 'revisado_por', 'revisado_en'])
            Abono.objects.create(comprobante=c, expediente=c.expediente, monto=c.monto, fecha=c.fecha_pago,
                                 registrado_por=revisor)
            return True
    except IntegrityError:
        return False  # otra confirmación simultánea ya creó el abono


def rechazar_comprobante(comprobante_id, motivo, revisor):
    with transaction.atomic():
        c = Comprobante.objects.select_for_update().get(pk=comprobante_id)
        if c.estado != Comprobante.Estado.PENDIENTE:
            return False
        c.estado, c.motivo_rechazo = Comprobante.Estado.RECHAZADO, motivo.strip()
        c.revisado_por, c.revisado_en = revisor, timezone.now()
        c.save(update_fields=['estado', 'motivo_rechazo', 'revisado_por', 'revisado_en'])
        return True
