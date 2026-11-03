"""Carga contenido y casos de demostración.

    python manage.py cargar_demo             # solo si la base está vacía
    python manage.py cargar_demo --reiniciar # borra los datos de negocio y los vuelve a crear

Los precios y casos son ficticios; el contenido se edita desde Panel → Contenido.
"""
import zlib
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core import servicios
from core.models import (Abono, AvisoVuelo, Beneficio, Cita, CitaConsular, Comprobante, Consulta, ContenidoSitio,
                         CorreoConsulado, Cotizacion, DocumentoRequerido, DocumentoViaje, Expediente, Oferta, Perfil,
                         PreguntaFrecuente, Promocion, Publicacion, Servicio, SolicitudViaje, VueloContratado)

User = get_user_model()


def pdf(texto):
    """Genera un PDF mínimo válido con una línea de texto."""
    contenido = f'BT /F1 18 Tf 72 720 Td ({texto}) Tj ET'.encode('latin-1', 'replace')
    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
        b'<< /Length %d >>\nstream\n' % len(contenido) + contenido + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    salida, offsets = b'%PDF-1.4\n', []
    for i, o in enumerate(objetos, 1):
        offsets.append(len(salida))
        salida += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    xref = len(salida)
    salida += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objetos) + 1)
    salida += b''.join(b'%010d 00000 n \n' % off for off in offsets)
    salida += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objetos) + 1, xref)
    return salida


def png(ancho=4, alto=4, color=(26, 79, 156)):
    import struct

    def bloque(tipo, datos):
        return struct.pack('>I', len(datos)) + tipo + datos + struct.pack('>I', zlib.crc32(tipo + datos) & 0xffffffff)
    filas = b''.join(b'\x00' + bytes(color) * ancho for _ in range(alto))
    return (b'\x89PNG\r\n\x1a\n' + bloque(b'IHDR', struct.pack('>IIBBBBB', ancho, alto, 8, 2, 0, 0, 0))
            + bloque(b'IDAT', zlib.compress(filas)) + bloque(b'IEND', b''))


DEMO = Path(__file__).resolve().parents[2] / 'demo'


def demo(nombre, texto):
    """PDF de demostración con diseño (core/demo); si falta, uno mínimo."""
    ruta = DEMO / nombre
    return ruta.read_bytes() if ruta.exists() else pdf(texto)


class Command(BaseCommand):
    help = 'Carga datos de demostración de OserVia.'

    def add_arguments(self, parser):
        parser.add_argument('--reiniciar', action='store_true', help='Borra los datos de negocio antes de cargar.')

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts['reiniciar']:
            for M in (Abono, Comprobante, Cita, Consulta, Expediente, SolicitudViaje, Oferta, Promocion, Servicio,
                      Beneficio, PreguntaFrecuente, Publicacion):
                M.objects.all().delete()
        elif Oferta.objects.exists():
            self.stdout.write('Ya hay datos. Usa --reiniciar para volver a cargarlos.')
            return

        hoy = timezone.localdate()
        self.cuentas()
        self.contenido(hoy)
        self.casos(hoy)
        self.stdout.write(self.style.SUCCESS('Datos de demostración cargados.'))

    # ------------------------------------------------------------------ Cuentas
    def cuenta(self, email, password, nombre, apellido, rol, telefono='', cedula=''):
        u = User.objects.filter(email__iexact=email).first() or User(username=email, email=email)
        if not u.pk or not u.has_usable_password():
            u.set_password(password)
        u.username, u.first_name, u.last_name = email, nombre, apellido
        u.is_staff, u.is_active = rol != 'usuario', True
        u.save()
        p, _ = Perfil.objects.get_or_create(usuario=u)
        p.rol, p.telefono, p.cedula = rol, telefono or p.telefono, cedula or p.cedula
        p.save()
        return u

    def cuentas(self):
        self.admin = self.cuenta('josmocobos@admin.com', 'admin123', 'Administrador', '', 'admin', '+593 99 026 2569')
        self.asesora = self.cuenta('asesor@admin.com', 'asesor123', 'Carla', 'Vélez', 'asesor', '+593 98 765 4321')
        self.asesor2 = self.cuenta('asesor2@admin.com', 'asesor123', 'Diego', 'Ramírez', 'asesor', '+593 98 111 2233')
        self.cliente = self.cuenta('josmocobos@espol.edu.ec', 'test123', 'Jostin', 'Mora', 'usuario',
                                   '+593 99 123 4567', '0912345678')
        for usuario, nombre, apellido in [('krcarrio', 'Kristhel Sharareh', 'Carrión Maldonado'),
                                          ('xamurill', 'Xavier Andrés', 'Murillo Panchana'),
                                          ('anthpare', 'Anthony Walter', 'Paredes Vega')]:
            self.cuenta(f'{usuario}@espol.edu.ec', 'test123', nombre, apellido, 'usuario')
            self.cuenta(f'{usuario}@admin.com', 'admin123', nombre, apellido, 'admin')
        # Cuentas existentes sin perfil quedan como usuarios.
        for u in User.objects.filter(perfil__isnull=True):
            Perfil.objects.create(usuario=u, rol='admin' if u.is_superuser else 'usuario')

    # ------------------------------------------------------------------ Contenido público
    def contenido(self, hoy):
        sitio = ContenidoSitio.actual()
        sitio.historia = (
            'OSERTRAVEL EC nació en Guayaquil en octubre de 2024 como un emprendimiento de asesoría de viajes y visas, '
            'y el 24 de febrero de 2025 abrió su oficina en el centro de la ciudad. Su fundadora, Mónica Tomalá, '
            'suma diez años de experiencia acompañando a viajeros, especialmente a quienes realizan su primer viaje '
            'o su primer trámite de visa.')
        sitio.mision = ('Acompañar a cada viajero con orientación clara y cercana, desde la cotización de su viaje o '
                        'la preparación de su visa hasta el día de su partida.')
        sitio.vision = ('Ser la agencia de referencia en Guayaquil para quienes viajan por primera vez, reconocida por '
                        'su transparencia y su seguimiento personalizado.')
        sitio.save()
        # Video tutorial incluido en el repositorio (RS-04.3)
        video = Path(__file__).resolve().parents[2] / 'demo' / 'tutorial.mp4'
        if video.exists() and not sitio.video_tutorial:
            sitio.video_tutorial.save('tutorial.mp4', ContentFile(video.read_bytes()), save=True)

        for i, (t, d, ic) in enumerate([
            ('Asesoría de visas', 'Schengen, Estados Unidos, Canadá, Reino Unido y más. Revisión de documentos, '
             'preparación de la cita y entrevista simulada.', 'passport'),
            ('Boletería aérea', 'Cotizamos, reservamos y emitimos tu boleto, y te ayudamos con el check-in previo al viaje.', 'plane'),
            ('Paquetes turísticos', 'Vuelo, hotel, traslados y actividades en un solo plan, con acompañamiento hasta tu regreso.', 'suitcase'),
            ('Seguros de viaje', 'Coberturas médicas y de asistencia según el destino y los requisitos consulares.', 'shield'),
        ]):
            Servicio.objects.create(titulo=t, descripcion=d, icono=ic, orden=i)

        for i, (t, d, ic) in enumerate([
            ('Experiencia', 'Diez años acompañando trámites de visa y viajes.', 'star'),
            ('Primera vez sin miedo', 'Orientación paso a paso para viajeros primerizos.', 'users'),
            ('Seguimiento en línea', 'Consulta el estado de tu trámite, tus documentos y tus pagos desde tu cuenta.', 'check-circle'),
            ('Entrevista gratuita', 'La primera entrevista informativa de visas no tiene costo.', 'headset'),
        ]):
            Beneficio.objects.create(titulo=t, descripcion=d, icono=ic, orden=i)

        for i, (p, r, k) in enumerate([
            ('¿La asesoría garantiza que me aprueben la visa?',
             'No. La agencia te acompaña en la preparación, pero la decisión corresponde únicamente al consulado.',
             'garantiza, aprueban, aprobación, negada'),
            ('¿La primera entrevista tiene costo?',
             'No. La primera entrevista informativa de visas es gratuita y dura unos 30 minutos.',
             'entrevista, gratis, gratuita, costo, primera'),
            ('¿Cómo envío mis documentos?',
             'Desde tu cuenta, en el expediente que te abre tu asesor: eliges el documento solicitado y adjuntas un PDF o PNG de hasta 10 MB.',
             'documentos, enviar, subir, archivo, pdf'),
            ('¿Qué formas de pago aceptan?',
             'Transferencia o depósito bancario. Envía la foto o el PDF del comprobante desde «Pagos» en tu cuenta; el abono se descuenta cuando la agencia lo confirma.',
             'pago, pagos, pagar, transferencia, depósito, abono'),
            ('¿Puedo pagar en abonos?',
             'Depende del servicio. En asesorías Schengen se suele pedir un 50 % inicial; en paquetes con suficiente anticipación puede haber abonos mensuales. Tu cotización indica las condiciones.',
             'abonos, cuotas, plazos, financiamiento'),
            ('¿Cuánto tiempo toma el trámite de visa?',
             'Depende del país y de la disponibilidad de citas del consulado. Tu asesor te indicará los tiempos estimados en la entrevista.',
             'tiempo, demora, tarda, cuánto, días'),
        ]):
            PreguntaFrecuente.objects.create(pregunta=p, respuesta=r, palabras_clave=k, orden=i)

        self.promo = Promocion.objects.create(
            titulo='Panamá en temporada baja', descripcion='Paquetes a Panamá con precio especial por persona.',
            condiciones='Válido para salidas hasta marzo. Sujeto a disponibilidad al momento de reservar.',
            fecha_inicio=hoy - timedelta(days=5), fecha_fin=hoy + timedelta(days=40))
        Promocion.objects.create(
            titulo='Asesoría Schengen: segundo intento', descripcion='Descuento en honorarios para un segundo intento de visa Schengen.',
            condiciones='Aplica a clientes de la agencia con solicitud anterior. Sujeto a evaluación.',
            fecha_inicio=hoy - timedelta(days=30), fecha_fin=hoy + timedelta(days=60))

        incluye_vuelo = 'Vuelo de ida y vuelta\nEquipaje de mano de 10 kg\nEquipaje facturado de 23 kg\nAsistencia para el check-in'
        cond_vuelo = 'Precio por persona en clase económica. Tarifa sujeta a disponibilidad al momento de emitir. Cambios con penalidad.'
        self.vuelos = {}
        for codigo, (o, d, dias, h, precio, promo) in {
            'mad': ('Guayaquil (GYE)', 'Madrid (MAD)', 45, '11.5', '980', None),
            'mia': ('Guayaquil (GYE)', 'Miami (MIA)', 20, '3.5', '420', None),
            'pty': ('Quito (UIO)', 'Ciudad de Panamá (PTY)', 30, '2', '310', self.promo),
            'jfk': ('Guayaquil (GYE)', 'Nueva York (JFK)', 60, '6', '560', None),
            'yyz': ('Guayaquil (GYE)', 'Toronto (YYZ)', 75, '9', '890', None),
            'bog': ('Guayaquil (GYE)', 'Bogotá (BOG)', 25, '1.5', '260', None),
        }.items():
            self.vuelos[codigo] = Oferta.objects.create(
                tipo='vuelo', titulo=f'{d.split(" (")[0]} desde {o.split(" (")[0]}',
                descripcion=f'Vuelo de {o} a {d} con aerolínea regular.', origen=o, destino=d,
                fecha_salida=hoy + timedelta(days=dias), fecha_regreso=hoy + timedelta(days=dias + 14),
                duracion_horas=Decimal(h), precio_persona=Decimal(precio), servicios_incluidos=incluye_vuelo,
                condiciones=cond_vuelo, promocion=promo)

        self.paquetes = {}
        for codigo, (titulo, destino, dias, salida, precio, promo, seguro) in {
            'ciudad': ('Panamá Ciudad', 'Ciudad de Panamá, Panamá', 4, 35, '650', self.promo, True),
            'playa': ('Panamá Playa', 'Playa Blanca, Panamá', 5, 50, '780', self.promo, True),
            'combo': ('Panamá y Colombia', 'Panamá y Cartagena, Colombia', 8, 70, '1450', None, False),
        }.items():
            self.paquetes[codigo] = Oferta.objects.create(
                tipo='paquete', titulo=titulo, descripcion=f'Paquete de {dias} días a {destino} con vuelo, hotel y traslados.',
                destino=destino, fecha_salida=hoy + timedelta(days=salida),
                fecha_regreso=hoy + timedelta(days=salida + dias - 1), duracion_dias=dias, precio_persona=Decimal(precio),
                servicios_incluidos='Vuelo ida y vuelta\nHotel con desayuno\nTraslados aeropuerto–hotel–aeropuerto\nCity tour'
                                    + ('\nSeguro de viaje' if seguro else ''),
                condiciones='Precio por persona en habitación doble. Reserva con abono; saldo antes de la emisión.',
                incluye_seguro=seguro, promocion=promo)

        Publicacion.objects.create(titulo='¡Nueva oficina en el centro de Guayaquil!', texto='Te esperamos en Tungurahua y Hurtado.',
                                   imagen=ContentFile(png(8, 6, (26, 79, 156)), name='oficina.png'))
        Publicacion.objects.create(titulo='Viajeros felices en Panamá', texto='Gracias por confiar en nosotros.',
                                   imagen=ContentFile(png(8, 6, (18, 128, 74)), name='panama.png'))

    # ------------------------------------------------------------------ Casos de ejemplo
    def casos(self, hoy):
        c, a, adm = self.cliente, self.asesora, self.admin
        base = {'nombre': 'Jostin Mora', 'cedula': '0912345678', 'email': c.email, 'telefono': '+593 99 123 4567'}

        # Consultas públicas
        Consulta.objects.create(nombre='María Pérez', telefono='+593 98 222 3344', motivo='Quiero información sobre la visa de turismo a Estados Unidos.')
        q = Consulta.objects.create(nombre='Luis Andrade', telefono='0997776655', motivo='¿Tienen paquetes a Cancún para diciembre?')
        servicios.asignar(q, a, adm)

        # 1) Cotización de vuelo desde una oferta, con propuesta pendiente de respuesta.
        o = self.vuelos['mad']
        s1 = SolicitudViaje.objects.create(usuario=c, tipo='vuelo', trayecto='ida_vuelta', origen=o.origen, destino=o.destino,
                                           fecha_salida=o.fecha_salida, fecha_regreso=o.fecha_regreso, pasajeros=2,
                                           clase='economica', seguro=True, oferta=o, oferta_codigo=o.codigo,
                                           oferta_nombre=o.titulo, **base)
        servicios.asignar(s1, a, adm)
        Cotizacion.objects.create(solicitud=s1, servicios_incluidos='Vuelo GYE–MAD ida y vuelta para 2 pasajeros\nEquipaje facturado de 23 kg\nSeguro de viaje Schengen',
                                  precio_total=Decimal('2140.00'), vigencia=hoy + timedelta(days=7), incluye_seguro=True,
                                  condiciones='Reserva con el 30 %. Emisión al completar el pago. Cambios con penalidad de la aerolínea.',
                                  creado_por=a)
        s1.actualizar_estado()

        # 2) Solicitud sin oferta, recién recibida.
        SolicitudViaje.objects.create(usuario=c, tipo='vuelo', trayecto='ida', origen='Guayaquil (GYE)', destino='Lima (LIM)',
                                      fecha_salida=hoy + timedelta(days=28), pasajeros=1, seguro=False, **base)

        # 3) Paquete aceptado -> expediente con pagos.
        p = self.paquetes['ciudad']
        s3 = SolicitudViaje.objects.create(usuario=c, tipo='paquete', destino=f'{p.titulo} ({p.destino})', fecha_salida=p.fecha_salida,
                                           fecha_regreso=p.fecha_regreso, pasajeros=2, seguro=True, oferta=p,
                                           oferta_codigo=p.codigo, oferta_nombre=p.titulo, promocion_nombre=self.promo.titulo, **base)
        servicios.asignar(s3, a, adm)
        cot = Cotizacion.objects.create(solicitud=s3, servicios_incluidos=p.servicios_incluidos, precio_total=Decimal('1300.00'),
                                        vigencia=hoy + timedelta(days=5), incluye_seguro=True, condiciones=p.condiciones, creado_por=a,
                                        estado='aceptada', contratar_seguro=True, respondida_en=timezone.now() - timedelta(days=2))
        s3.actualizar_estado()
        e_paq = Expediente.objects.create(usuario=c, tipo='paquete', solicitud=s3, nombre='Jostin Mora', telefono=base['telefono'],
                                          documento_identidad=base['cedula'], email=c.email, precio_total=cot.precio_total,
                                          paquete_nombre=p.titulo, destino=p.destino, fecha_salida=p.fecha_salida,
                                          fecha_regreso=p.fecha_regreso, servicios_incluidos=p.servicios_incluidos,
                                          itinerario='Día 1: llegada y traslado al hotel.\nDía 2: city tour y Canal de Panamá.\n'
                                                     'Día 3: Casco Antiguo y tiempo libre.\nDía 4: traslado al aeropuerto y regreso.',
                                          comentario_usuario='Tu reserva está confirmada. El saldo debe completarse antes de la emisión de los boletos.',
                                          creado_por=a)
        servicios.asignar(e_paq, a, adm)
        DocumentoViaje.objects.create(expediente=e_paq, titulo='Voucher del hotel', subido_por=a,
                                      archivo=ContentFile(demo('voucher.pdf', 'Voucher de hotel - Panama Ciudad'), name='voucher.pdf'))
        c1 = Comprobante.objects.create(expediente=e_paq, enviado_por=c, monto=Decimal('650.00'), fecha_pago=hoy - timedelta(days=2),
                                        numero='TRX-889201', medio='transferencia', nombre_original='transferencia.pdf',
                                        archivo=ContentFile(demo('comprobante.pdf', 'Comprobante TRX-889201'), name='transferencia.pdf'))
        servicios.confirmar_comprobante(c1.pk, a)
        Comprobante.objects.create(expediente=e_paq, enviado_por=c, monto=Decimal('300.00'), fecha_pago=hoy, numero='DEP-55102',
                                   medio='deposito', nombre_original='deposito.png', archivo=ContentFile(png(), name='deposito.png'))

        # 4) Asesoría de visa Schengen en revisión de documentos.
        e_visa = Expediente.objects.create(usuario=c, tipo='visa', nombre='Jostin Mora', telefono=base['telefono'],
                                           documento_identidad=base['cedula'], email=c.email, pais='España (Schengen)',
                                           tipo_visa='Turismo', pasaporte='A1234567', precio_total=Decimal('450.00'),
                                           comentario_usuario='Revisa la corrección pedida en tus estados de cuenta.',
                                           creado_por=a)
        servicios.asignar(e_visa, a, adm)
        servicios.cambiar_etapa(e_visa, 'revision', a)
        docs = {n: DocumentoRequerido.objects.create(expediente=e_visa, nombre=n, indicaciones=i, creado_por=a) for n, i in [
            ('Pasaporte vigente', 'Escaneado a color, todas las hojas con sellos.'),
            ('Estados de cuenta (últimos 3 meses)', 'Con sello del banco.'),
            ('Seguro de viaje Schengen', 'Cobertura mínima de 30.000 EUR.'),
            ('Reserva de vuelo', ''),
        ]}
        for nombre, flujo in [('Pasaporte vigente', ['aceptado']), ('Estados de cuenta (últimos 3 meses)', ['correccion']),
                              ('Reserva de vuelo', [])]:
            d = docs[nombre]
            servicios.subir_documento(d, ContentFile(demo('documento.pdf', nombre), name=f'{nombre[:20]}.pdf'), c)
            for paso in flujo:
                servicios.revisar_documento(d, paso, 'Falta el sello del banco en el mes de agosto.' if paso == 'correccion' else '', a)
        CorreoConsulado.objects.create(expediente=e_visa, destinatario='consulado@ejemplo.com', asunto='Consulta de disponibilidad de citas',
                                       fecha_envio=hoy - timedelta(days=3), proxima_revision=hoy, registrado_por=a)
        c2 = Comprobante.objects.create(expediente=e_visa, enviado_por=c, monto=Decimal('225.00'), fecha_pago=hoy - timedelta(days=10),
                                        numero='TRX-771020', medio='transferencia', nombre_original='abono-visa.pdf',
                                        archivo=ContentFile(demo('comprobante.pdf', 'Comprobante TRX-771020'), name='abono-visa.pdf'))
        servicios.confirmar_comprobante(c2.pk, a)

        # 5) Boletería con vuelo emitido y aviso de la aerolínea.
        e_vuelo = Expediente.objects.create(usuario=c, tipo='vuelo', nombre='Jostin Mora', telefono=base['telefono'],
                                            documento_identidad=base['cedula'], email=c.email, precio_total=Decimal('420.00'), creado_por=a)
        servicios.asignar(e_vuelo, self.asesor2, adm)
        tz = timezone.get_current_timezone()
        salida = datetime.combine(hoy + timedelta(days=20), time(8, 15), tzinfo=tz)
        VueloContratado.objects.create(expediente=e_vuelo, aerolinea='Avianca', numero_vuelo='AV 8371', origen='Guayaquil (GYE)',
                                       destino='Miami (MIA)', salida=salida, llegada=salida + timedelta(hours=3, minutes=40),
                                       boleto=ContentFile(demo('boleto.pdf', 'Boleto electronico AV 8371'), name='boleto.pdf'))
        AvisoVuelo.objects.create(expediente=e_vuelo, aerolinea='Avianca', numero_vuelo='AV 8371', fecha_vuelo=salida.date(),
                                  tipo='reprogramacion', cambio_informado='La aerolínea adelantó la salida por ajuste de itinerario.',
                                  nueva_fecha_hora=salida - timedelta(hours=1, minutes=30), registrado_por=self.asesor2)
        c3 = Comprobante.objects.create(expediente=e_vuelo, enviado_por=c, monto=Decimal('420.00'), fecha_pago=hoy - timedelta(days=6),
                                        numero='DEP-33019', medio='deposito', nombre_original='deposito.pdf',
                                        archivo=ContentFile(demo('comprobante.pdf', 'Deposito DEP-33019'), name='deposito.pdf'))
        servicios.confirmar_comprobante(c3.pk, self.asesor2)

        # Citas con la agencia
        Cita.objects.create(usuario=c, asesor=a, creado_por=a, expediente=e_visa, motivo='Preparación de entrevista consular',
                            modalidad='virtual', fecha=hoy + timedelta(days=1), hora=time(10, 0), enlace='https://meet.google.com/abc-defg-hij')
        Cita.objects.create(usuario=c, asesor=a, creado_por=a, expediente=e_paq, motivo='Entrega de documentos de viaje y charla de orientación',
                            modalidad='presencial', fecha=hoy + timedelta(days=5), hora=time(15, 30),
                            direccion='Calles Tungurahua y Hurtado, referencia 1000A, centro de Guayaquil')
        Cita.objects.create(usuario=c, asesor=a, creado_por=a, motivo='Revisión de requisitos de visa', modalidad='presencial',
                            fecha=hoy, hora=time(16, 0), direccion='Calles Tungurahua y Hurtado, referencia 1000A, centro de Guayaquil')
