"""Modelo de datos de OserVia.

Los identificadores RU/RS/RNF corresponden al documento de requerimientos
(OserVia_Requerimientos_Overleaf.pdf).
"""
import os
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse
from django.utils import timezone

USER = settings.AUTH_USER_MODEL


def ruta_privada(instance, filename):
    """Archivos de clientes: nunca se publican por URL directa (RNF-06)."""
    ext = os.path.splitext(filename)[1].lower()
    return f'privado/{instance._meta.model_name}/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}'


def ruta_publica(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'publico/{instance._meta.model_name}/{uuid.uuid4().hex}{ext}'


ICONOS = [
    ('passport', 'Pasaporte'), ('plane', 'Avión'), ('takeoff', 'Despegue'), ('suitcase', 'Maleta'),
    ('shield', 'Escudo'), ('globe', 'Mundo'), ('headset', 'Atención'), ('star', 'Estrella'),
    ('users', 'Personas'), ('calendar', 'Calendario'), ('clock', 'Reloj'), ('check-circle', 'Verificado'),
]


# ==================================================================== Cuentas

class Perfil(models.Model):
    class Rol(models.TextChoices):
        USUARIO = 'usuario', 'Usuario'
        ASESOR = 'asesor', 'Asesor'
        ADMIN = 'admin', 'Administrador'

    usuario = models.OneToOneField(USER, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField('rol', max_length=10, choices=Rol.choices, default=Rol.USUARIO)
    cedula = models.CharField('cédula / pasaporte', max_length=20, blank=True)
    telefono = models.CharField('teléfono', max_length=20, blank=True)
    terminos_aceptados_en = models.DateTimeField('aceptó términos y privacidad el', null=True, blank=True)

    class Meta:
        verbose_name = 'perfil'
        verbose_name_plural = 'perfiles'

    def __str__(self):
        return f'{self.usuario} ({self.get_rol_display()})'


def nombre_de(user):
    if not user:
        return '—'
    return user.get_full_name() or user.email


# ==================================================================== Contenido público (RS-03, RS-04)

class ContenidoSitio(models.Model):
    """Información institucional y de contacto editable por el administrador (RU-03)."""
    nombre = models.CharField('nombre comercial', max_length=80, default='OSERTRAVEL EC')
    eslogan = models.CharField('eslogan', max_length=160, default='Asesoría de viajes y visas desde Guayaquil')
    descripcion = models.TextField('descripción corta', default=(
        'Asesoría de visas, boletería aérea, paquetes turísticos y seguros de viaje, con acompañamiento '
        'personalizado para quienes viajan o tramitan su visa por primera vez.'))
    historia = models.TextField('historia', blank=True)
    mision = models.TextField('misión', blank=True)
    vision = models.TextField('visión', blank=True)
    direccion = models.CharField('dirección', max_length=200, default='Calles Tungurahua y Hurtado, referencia 1000A')
    ciudad = models.CharField('ciudad', max_length=80, default='Centro de Guayaquil, Ecuador')
    mapa_url = models.URLField('enlace al mapa', blank=True)
    telefono = models.CharField('teléfono', max_length=30, default='+593 99 026 2569')
    whatsapp = models.CharField('WhatsApp (solo dígitos con código de país)', max_length=20, default='593990262569')
    email = models.EmailField('correo de atención', default='infoclientes@osertravelec.com')
    horario = models.CharField('horario de atención', max_length=120, default='Lunes a viernes, 09:00 – 18:00')
    instagram = models.URLField('Instagram', blank=True)
    facebook = models.URLField('Facebook', blank=True)
    video_tutorial = models.FileField('video tutorial (MP4/WebM)', upload_to=ruta_publica, blank=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'información de la agencia'
        verbose_name_plural = 'información de la agencia'

    def __str__(self):
        return self.nombre

    @classmethod
    def actual(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def whatsapp_url(self):
        return f'https://wa.me/{self.whatsapp}' if self.whatsapp else ''


class Publicable(models.Model):
    publicado = models.BooleanField('publicado', default=True,
                                    help_text='Desmarca para retirarlo de la vista pública.')
    orden = models.PositiveSmallIntegerField('orden', default=0)
    actualizado = models.DateTimeField('actualizado', auto_now=True)

    class Meta:
        abstract = True
        ordering = ['orden', 'pk']


class Servicio(Publicable):
    titulo = models.CharField('título', max_length=100)
    descripcion = models.TextField('descripción')
    icono = models.CharField('icono', max_length=20, choices=ICONOS, default='globe')

    class Meta(Publicable.Meta):
        verbose_name = 'servicio'
        verbose_name_plural = 'servicios'

    def __str__(self):
        return self.titulo


class Beneficio(Publicable):
    """Sección «¿Por qué viajar con nosotros?» (RS-03.4)."""
    titulo = models.CharField('título', max_length=100)
    descripcion = models.TextField('descripción')
    icono = models.CharField('icono', max_length=20, choices=ICONOS, default='star')

    class Meta(Publicable.Meta):
        verbose_name = 'beneficio'
        verbose_name_plural = 'beneficios'

    def __str__(self):
        return self.titulo


class PreguntaFrecuente(Publicable):
    pregunta = models.CharField('pregunta', max_length=200)
    respuesta = models.TextField('respuesta')
    palabras_clave = models.CharField('palabras clave para el asistente', max_length=200, blank=True,
                                      help_text='Separadas por comas. Ayudan al asistente virtual a encontrar esta respuesta.')

    class Meta(Publicable.Meta):
        verbose_name = 'pregunta frecuente'
        verbose_name_plural = 'preguntas frecuentes'

    def __str__(self):
        return self.pregunta


class Promocion(Publicable):
    titulo = models.CharField('título', max_length=120)
    descripcion = models.TextField('descripción')
    condiciones = models.TextField('condiciones', blank=True)
    fecha_inicio = models.DateField('se puede solicitar desde')
    fecha_fin = models.DateField('se puede solicitar hasta')

    class Meta(Publicable.Meta):
        verbose_name = 'promoción'
        verbose_name_plural = 'promociones'
        ordering = ['fecha_fin']

    def __str__(self):
        return self.titulo

    @property
    def vigente(self):
        hoy = timezone.localdate()
        return self.fecha_inicio <= hoy <= self.fecha_fin


class Oferta(Publicable):
    """Oferta de vuelo o paquete turístico publicada por la agencia (RS-03.1, RS-05.7)."""
    class Tipo(models.TextChoices):
        VUELO = 'vuelo', 'Vuelo'
        PAQUETE = 'paquete', 'Paquete turístico'

    tipo = models.CharField('tipo', max_length=10, choices=Tipo.choices)
    codigo = models.CharField('código', max_length=12, unique=True, editable=False, blank=True)
    titulo = models.CharField('nombre de la oferta', max_length=120)
    descripcion = models.TextField('descripción')
    origen = models.CharField('origen', max_length=100, blank=True)
    destino = models.CharField('destino', max_length=100)
    fecha_salida = models.DateField('fecha de salida')
    fecha_regreso = models.DateField('fecha de regreso', null=True, blank=True)
    duracion_horas = models.DecimalField('duración del vuelo (horas)', max_digits=4, decimal_places=1,
                                         null=True, blank=True)
    duracion_dias = models.PositiveSmallIntegerField('duración (días)', null=True, blank=True)
    precio_persona = models.DecimalField('precio por persona (USD)', max_digits=9, decimal_places=2,
                                         validators=[MinValueValidator(Decimal('0'))])
    servicios_incluidos = models.TextField('servicios incluidos', help_text='Uno por línea.')
    condiciones = models.TextField('condiciones')
    incluye_seguro = models.BooleanField('incluye seguro de viaje', default=False)
    promocion = models.ForeignKey(Promocion, verbose_name='promoción', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='ofertas')

    class Meta(Publicable.Meta):
        verbose_name = 'oferta'
        verbose_name_plural = 'ofertas'
        ordering = ['fecha_salida']

    def __str__(self):
        return f'{self.codigo} · {self.titulo}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            prefijo = 'VUE' if self.tipo == self.Tipo.VUELO else 'PAQ'
            self.codigo = f'{prefijo}-{self.pk:04d}'
            super().save(update_fields=['codigo'])

    def get_absolute_url(self):
        return reverse('oferta', args=[self.codigo])

    @property
    def lista_servicios(self):
        return [s.strip(' -•') for s in self.servicios_incluidos.splitlines() if s.strip()]

    @property
    def promocion_vigente(self):
        return self.promocion if self.promocion and self.promocion.publicado and self.promocion.vigente else None


class Publicacion(Publicable):
    """Publicaciones de redes sociales mostradas en la página principal (RS-04.2)."""
    titulo = models.CharField('título', max_length=120)
    texto = models.TextField('texto', blank=True)
    imagen = models.FileField('imagen (JPG/PNG)', upload_to=ruta_publica, blank=True)
    video = models.FileField('video (MP4/WebM)', upload_to=ruta_publica, blank=True)
    enlace = models.URLField('enlace a la publicación original', blank=True)
    fecha = models.DateField('fecha', default=timezone.localdate)

    class Meta(Publicable.Meta):
        verbose_name = 'publicación'
        verbose_name_plural = 'publicaciones'
        ordering = ['-fecha']

    def __str__(self):
        return self.titulo


# ==================================================================== Asignaciones (RS-02.4)

class AsignableMixin(models.Model):
    asesor = models.ForeignKey(USER, verbose_name='asesor responsable', on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='+')
    asignado_por = models.ForeignKey(USER, verbose_name='asignado por', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    asignado_en = models.DateTimeField('asignado el', null=True, blank=True)

    class Meta:
        abstract = True


class Asignacion(models.Model):
    """Historial de asignaciones: quién asignó a quién y cuándo."""
    consulta = models.ForeignKey('Consulta', on_delete=models.CASCADE, null=True, blank=True, related_name='asignaciones')
    solicitud = models.ForeignKey('SolicitudViaje', on_delete=models.CASCADE, null=True, blank=True, related_name='asignaciones')
    expediente = models.ForeignKey('Expediente', on_delete=models.CASCADE, null=True, blank=True, related_name='asignaciones')
    asesor = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    asignado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']


# ==================================================================== Consultas (RS-04.5, RS-04.6)

class Consulta(AsignableMixin):
    class Estado(models.TextChoices):
        NUEVA = 'nueva', 'Nueva'
        ASIGNADA = 'asignada', 'Asignada'
        ATENDIDA = 'atendida', 'Atendida'

    nombre = models.CharField('nombre completo', max_length=150)
    telefono = models.CharField('teléfono', max_length=20)
    motivo = models.TextField('motivo de consulta')
    estado = models.CharField('estado', max_length=10, choices=Estado.choices, default=Estado.NUEVA)
    creado = models.DateTimeField('recibida', auto_now_add=True)

    class Meta:
        ordering = ['-creado']
        verbose_name = 'consulta'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    @property
    def codigo(self):
        return f'CON-{self.pk:05d}'


# ==================================================================== Cotizaciones (RS-05)

class SolicitudViaje(AsignableMixin):
    class Tipo(models.TextChoices):
        VUELO = 'vuelo', 'Vuelo'
        PAQUETE = 'paquete', 'Paquete turístico'

    class Trayecto(models.TextChoices):
        IDA = 'ida', 'Solo ida'
        IDA_VUELTA = 'ida_vuelta', 'Ida y vuelta'

    class Clase(models.TextChoices):
        ECONOMICA = 'economica', 'Económica'
        PREMIUM = 'premium', 'Premium economy'
        EJECUTIVA = 'ejecutiva', 'Ejecutiva'

    class Estado(models.TextChoices):
        RECIBIDA = 'recibida', 'Recibida'
        EN_ATENCION = 'en_atencion', 'En atención'
        COTIZADA = 'cotizada', 'Cotización enviada'
        ACEPTADA = 'aceptada', 'Cotización aceptada'
        NO_ACEPTADA = 'no_aceptada', 'Cotización rechazada'
        CANCELADA = 'cancelada', 'Cancelada'

    usuario = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='solicitudes_viaje')
    tipo = models.CharField('tipo de servicio', max_length=10, choices=Tipo.choices, default=Tipo.VUELO)
    trayecto = models.CharField('tipo de viaje', max_length=12, choices=Trayecto.choices, blank=True)
    origen = models.CharField('origen', max_length=120, blank=True)
    destino = models.CharField('destino / paquete', max_length=120)
    fecha_salida = models.DateField('fecha de salida')
    fecha_regreso = models.DateField('fecha de regreso', null=True, blank=True)
    pasajeros = models.PositiveSmallIntegerField('pasajeros', default=1,
                                                 validators=[MinValueValidator(1), MaxValueValidator(20)])
    clase = models.CharField('clase', max_length=10, choices=Clase.choices, blank=True)
    seguro = models.BooleanField('desea incluir seguro de viaje', default=False)
    oferta = models.ForeignKey(Oferta, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes')
    oferta_codigo = models.CharField('código de la oferta', max_length=12, blank=True)
    oferta_nombre = models.CharField('oferta', max_length=120, blank=True)
    promocion_nombre = models.CharField('promoción', max_length=120, blank=True)
    nombre = models.CharField('nombre completo', max_length=150)
    cedula = models.CharField('cédula de identidad', max_length=20)
    email = models.EmailField('correo electrónico')
    telefono = models.CharField('teléfono', max_length=20)
    comentarios = models.TextField('comentarios', blank=True)
    estado = models.CharField('estado', max_length=12, choices=Estado.choices, default=Estado.RECIBIDA)
    creado = models.DateTimeField('creado', auto_now_add=True)
    actualizado = models.DateTimeField('actualizado', auto_now=True)

    kind = 'viaje'

    class Meta:
        ordering = ['-creado']
        verbose_name = 'solicitud de cotización'
        verbose_name_plural = 'solicitudes de cotización'

    def __str__(self):
        return f'{self.codigo} · {self.titulo}'

    @property
    def codigo(self):
        return f'COT-{self.pk:05d}'

    @property
    def titulo(self):
        return f'{self.origen} → {self.destino}' if self.origen else self.destino

    @property
    def subtitulo(self):
        p = 'pasajero' if self.pasajeros == 1 else 'pasajeros'
        extra = f' · {self.get_trayecto_display()}' if self.trayecto else ''
        return f'{self.get_tipo_display()}{extra} · {self.pasajeros} {p}'

    @property
    def oferta_texto(self):
        return f'{self.oferta_nombre} ({self.oferta_codigo})' if self.oferta_codigo else 'Sin oferta seleccionada'

    @property
    def tono(self):
        return {'recibida': 'info', 'en_atencion': 'warn', 'cotizada': 'warn', 'aceptada': 'success',
                'no_aceptada': 'danger', 'cancelada': 'neutral'}.get(self.estado, 'neutral')

    @property
    def en_curso(self):
        return self.estado in ('recibida', 'en_atencion', 'cotizada')

    def get_absolute_url(self):
        return reverse('solicitud', args=[self.pk])

    def get_panel_url(self):
        return reverse('panel_solicitud', args=[self.pk])

    def actualizar_estado(self):
        """Recalcula el estado a partir de sus cotizaciones."""
        if self.estado == self.Estado.CANCELADA:
            return
        estados = set(self.cotizaciones.values_list('estado', flat=True))
        if 'aceptada' in estados:
            nuevo = self.Estado.ACEPTADA
        elif 'pendiente' in estados:
            nuevo = self.Estado.COTIZADA
        elif estados == {'rechazada'}:
            nuevo = self.Estado.NO_ACEPTADA
        else:
            nuevo = self.Estado.EN_ATENCION if self.asesor_id else self.Estado.RECIBIDA
        if nuevo != self.estado:
            self.estado = nuevo
            self.save(update_fields=['estado', 'actualizado'])


class Cotizacion(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de respuesta'
        ACEPTADA = 'aceptada', 'Aceptada'
        RECHAZADA = 'rechazada', 'Rechazada'

    solicitud = models.ForeignKey(SolicitudViaje, on_delete=models.CASCADE, related_name='cotizaciones')
    servicios_incluidos = models.TextField('servicios incluidos', help_text='Uno por línea.')
    precio_total = models.DecimalField('precio total (USD)', max_digits=10, decimal_places=2,
                                       validators=[MinValueValidator(Decimal('0'))])
    vigencia = models.DateField('oferta válida hasta')
    condiciones = models.TextField('condiciones de contratación')
    incluye_seguro = models.BooleanField('incluye seguro de viaje', default=False)
    estado = models.CharField('estado', max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    contratar_seguro = models.BooleanField('desea contratar seguro', null=True, blank=True)
    respondida_en = models.DateTimeField('respondida el', null=True, blank=True)
    creado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado']
        verbose_name = 'cotización'
        verbose_name_plural = 'cotizaciones'

    def __str__(self):
        return self.codigo

    @property
    def codigo(self):
        return f'PRO-{self.pk:05d}'

    @property
    def lista_servicios(self):
        return [s.strip(' -•') for s in self.servicios_incluidos.splitlines() if s.strip()]

    @property
    def vencida(self):
        return self.estado == self.Estado.PENDIENTE and self.vigencia < timezone.localdate()

    @property
    def tono(self):
        return {'pendiente': 'warn', 'aceptada': 'success', 'rechazada': 'danger'}[self.estado]


# ==================================================================== Expedientes (RS-06, RS-08)

class Expediente(AsignableMixin):
    class Tipo(models.TextChoices):
        VISA = 'visa', 'Asesoría de visa'
        VUELO = 'vuelo', 'Boletería (vuelo)'
        PAQUETE = 'paquete', 'Paquete turístico'

    class Estado(models.TextChoices):
        EN_CURSO = 'en_curso', 'En curso'
        FINALIZADO = 'finalizado', 'Finalizado'
        CANCELADO = 'cancelado', 'Cancelado'

    class Etapa(models.TextChoices):
        RECOLECCION = 'recoleccion', 'Recolección de documentos'
        REVISION = 'revision', 'Revisión de documentos'
        PREPARACION = 'preparacion', 'Preparación para la cita consular'
        PRESENTADO = 'presentado', 'Usuario presentado al consulado'

    class Resultado(models.TextChoices):
        NO_REGISTRADO = 'no_registrado', 'Resultado no registrado'
        APROBADA = 'aprobada', 'Visa aprobada'
        NEGADA = 'negada', 'Visa negada'
        OTRO = 'otro', 'Otro resultado'

    usuario = models.ForeignKey(USER, verbose_name='usuario', on_delete=models.CASCADE, related_name='expedientes')
    tipo = models.CharField('tipo de servicio', max_length=10, choices=Tipo.choices)
    estado = models.CharField('estado del servicio', max_length=12, choices=Estado.choices, default=Estado.EN_CURSO)
    solicitud = models.ForeignKey(SolicitudViaje, verbose_name='solicitud de origen', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='expedientes')
    nombre = models.CharField('nombre completo', max_length=150)
    telefono = models.CharField('teléfono', max_length=20)
    documento_identidad = models.CharField('documento de identidad', max_length=20)
    email = models.EmailField('correo electrónico', blank=True)
    precio_total = models.DecimalField('precio total del servicio (USD)', max_digits=10, decimal_places=2,
                                       null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    comentario_usuario = models.TextField('comentarios para el usuario', blank=True)
    notas_internas = models.TextField('notas internas', blank=True, help_text='Solo visibles para el personal.')
    # Visa
    pais = models.CharField('país de destino', max_length=60, blank=True)
    tipo_visa = models.CharField('tipo de visa', max_length=60, blank=True)
    pasaporte = models.CharField('número de pasaporte', max_length=20, blank=True)
    etapa = models.CharField('etapa', max_length=12, choices=Etapa.choices, blank=True)
    fecha_presentacion = models.DateField('fecha de presentación al consulado', null=True, blank=True)
    resultado = models.CharField('resultado consular', max_length=14, choices=Resultado.choices,
                                 default=Resultado.NO_REGISTRADO)
    resultado_detalle = models.TextField('detalle del resultado', blank=True)
    resultado_fecha = models.DateField('fecha en que se recibió el resultado', null=True, blank=True)
    # Paquete
    paquete_nombre = models.CharField('paquete contratado', max_length=120, blank=True)
    destino = models.CharField('destino', max_length=120, blank=True)
    fecha_salida = models.DateField('fecha de salida', null=True, blank=True)
    fecha_regreso = models.DateField('fecha de regreso', null=True, blank=True)
    servicios_incluidos = models.TextField('servicios incluidos', blank=True, help_text='Uno por línea.')
    itinerario = models.TextField('itinerario', blank=True)

    creado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    creado = models.DateTimeField('creado', auto_now_add=True)
    actualizado = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        ordering = ['-creado']
        verbose_name = 'expediente'

    def __str__(self):
        return f'{self.codigo} · {self.titulo}'

    def save(self, *args, **kwargs):
        if self.tipo == self.Tipo.VISA and not self.etapa:
            self.etapa = self.Etapa.RECOLECCION  # RS-06.2
        super().save(*args, **kwargs)

    @property
    def codigo(self):
        return f'EXP-{self.pk:05d}'

    @property
    def titulo(self):
        if self.tipo == self.Tipo.VISA:
            return f'Visa {self.tipo_visa.lower()} · {self.pais}'.strip(' ·')
        if self.tipo == self.Tipo.PAQUETE:
            return self.paquete_nombre or self.destino or 'Paquete turístico'
        v = self.vuelos.first()
        return f'{v.origen} → {v.destino}' if v else 'Boletería aérea'

    @property
    def es_visa(self):
        return self.tipo == self.Tipo.VISA

    @property
    def tono(self):
        return {'en_curso': 'info', 'finalizado': 'success', 'cancelado': 'neutral'}[self.estado]

    def etapas_progreso(self):
        claves = [c for c, _ in self.Etapa.choices]
        actual = claves.index(self.etapa) if self.etapa in claves else 0
        return [{'label': label, 'estado': 'done' if i < actual or (i == actual == len(claves) - 1)
                 else 'current' if i == actual else 'todo'}
                for i, (_, label) in enumerate(self.Etapa.choices)]

    @property
    def lista_servicios(self):
        return [s.strip(' -•') for s in self.servicios_incluidos.splitlines() if s.strip()]

    # ---- Documentación (RS-06.3)
    @property
    def documentacion_completa(self):
        docs = list(self.documentos.all())
        return bool(docs) and all(d.estado == DocumentoRequerido.Estado.ACEPTADO for d in docs)

    @property
    def documentos_pendientes(self):
        return [d for d in self.documentos.all() if d.estado != DocumentoRequerido.Estado.ACEPTADO]

    # ---- Pagos (RS-10.4)
    @property
    def total_abonado(self):
        return self.abonos.aggregate(t=Sum('monto'))['t'] or Decimal('0')

    @property
    def saldo(self):
        if self.precio_total is None:
            return None
        return self.precio_total - self.total_abonado

    @property
    def en_revision(self):
        return self.comprobantes.filter(estado='pendiente').aggregate(t=Sum('monto'))['t'] or Decimal('0')

    @property
    def por_pagar(self):
        """Lo que aún se puede enviar: saldo menos comprobantes que esperan revisión."""
        if self.precio_total is None:
            return None
        return max(self.saldo - self.en_revision, Decimal('0'))

    def get_absolute_url(self):
        return reverse('expediente', args=[self.pk])

    def get_panel_url(self):
        return reverse('panel_expediente', args=[self.pk])


class CambioEtapa(models.Model):
    """Historial de cambios de etapa de una asesoría de visa (RS-06.6)."""
    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='cambios_etapa')
    anterior = models.CharField(max_length=12, choices=Expediente.Etapa.choices, blank=True)
    nueva = models.CharField(max_length=12, choices=Expediente.Etapa.choices)
    usuario = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']


class CitaConsular(models.Model):
    """Cita de visa ya confirmada por la entidad consular (RS-08.3)."""
    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='citas_consulares')
    consulado = models.CharField('consulado o centro de atención', max_length=150)
    direccion = models.CharField('dirección', max_length=200)
    fecha = models.DateField('fecha')
    hora = models.TimeField('hora')
    confirmacion = models.FileField('confirmación de la cita (PDF/PNG/JPG)', upload_to=ruta_privada, blank=True)
    registrado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-hora']


class CorreoConsulado(models.Model):
    """Bitácora de correos enviados al consulado (RS-06.7)."""
    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='correos')
    destinatario = models.EmailField('destinatario')
    asunto = models.CharField('asunto', max_length=200)
    fecha_envio = models.DateField('fecha de envío')
    respuesta = models.TextField('respuesta registrada', blank=True)
    proxima_revision = models.DateField('próxima revisión del buzón', null=True, blank=True)
    registrado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_envio', '-pk']


class VueloContratado(models.Model):
    """Datos del vuelo emitido (RS-06.4)."""
    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='vuelos')
    aerolinea = models.CharField('aerolínea', max_length=80)
    numero_vuelo = models.CharField('número de vuelo', max_length=12)
    origen = models.CharField('origen', max_length=100)
    destino = models.CharField('destino', max_length=100)
    salida = models.DateTimeField('salida')
    llegada = models.DateTimeField('llegada')
    boleto = models.FileField('boleto emitido (PDF/PNG/JPG)', upload_to=ruta_privada, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['salida']


class AvisoVuelo(models.Model):
    """Cancelaciones o cambios informados por la aerolínea (RS-06.8)."""
    class Tipo(models.TextChoices):
        CANCELACION = 'cancelacion', 'Cancelación'
        CAMBIO = 'cambio', 'Cambio de horario'
        REPROGRAMACION = 'reprogramacion', 'Vuelo reprogramado'

    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='avisos')
    aerolinea = models.CharField('aerolínea', max_length=80)
    numero_vuelo = models.CharField('número de vuelo', max_length=12)
    fecha_vuelo = models.DateField('fecha del vuelo')
    tipo = models.CharField('tipo de aviso', max_length=15, choices=Tipo.choices)
    cambio_informado = models.TextField('cambio informado')
    fecha_aviso = models.DateField('fecha del aviso', default=timezone.localdate)
    nueva_fecha_hora = models.DateTimeField('nueva fecha y hora', null=True, blank=True)
    registrado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')

    class Meta:
        ordering = ['-fecha_aviso', '-pk']


class DocumentoViaje(models.Model):
    """Documentos del viaje que la agencia entrega al usuario (RS-06.5)."""
    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='documentos_viaje')
    titulo = models.CharField('título', max_length=120)
    archivo = models.FileField('archivo (PDF/PNG/JPG)', upload_to=ruta_privada)
    subido_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    subido = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['subido']


# ==================================================================== Documentos solicitados (RS-07)

class DocumentoRequerido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de entrega'
        RECIBIDO = 'recibido', 'Recibido'
        REVISION = 'revision', 'En revisión'
        CORRECCION = 'correccion', 'Corrección requerida'
        ACEPTADO = 'aceptado', 'Aceptado por la agencia'

    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='documentos')
    nombre = models.CharField('documento solicitado', max_length=120)
    indicaciones = models.CharField('indicaciones', max_length=250, blank=True)
    estado = models.CharField('estado', max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return self.nombre

    @property
    def tono(self):
        return {'pendiente': 'neutral', 'recibido': 'info', 'revision': 'warn',
                'correccion': 'danger', 'aceptado': 'success'}[self.estado]

    @property
    def puede_subir(self):
        return self.estado in (self.Estado.PENDIENTE, self.Estado.CORRECCION)

    @property
    def ultima_correccion(self):
        if self.estado != self.Estado.CORRECCION:
            return None
        return self.revisiones.filter(estado=self.Estado.CORRECCION).first()


class ArchivoDocumento(models.Model):
    documento = models.ForeignKey(DocumentoRequerido, on_delete=models.CASCADE, related_name='archivos')
    archivo = models.FileField(upload_to=ruta_privada)
    nombre_original = models.CharField(max_length=255)
    tamano = models.PositiveIntegerField(default=0)
    subido_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    subido = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-subido', '-pk']

    @property
    def extension(self):
        return os.path.splitext(self.nombre_original)[1].lstrip('.').upper()


class RevisionDocumento(models.Model):
    """Cada cambio de estado hecho por el asesor queda registrado (RS-07.3, RS-07.4)."""
    documento = models.ForeignKey(DocumentoRequerido, on_delete=models.CASCADE, related_name='revisiones')
    estado = models.CharField(max_length=12, choices=DocumentoRequerido.Estado.choices)
    comentario = models.TextField(blank=True)
    revisor = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']


# ==================================================================== Citas con la agencia (RS-09)

class Cita(models.Model):
    class Modalidad(models.TextChoices):
        VIRTUAL = 'virtual', 'Virtual'
        PRESENCIAL = 'presencial', 'Presencial'

    class Estado(models.TextChoices):
        PROGRAMADA = 'programada', 'Programada'
        REPROGRAMADA = 'reprogramada', 'Reprogramada'
        CANCELADA = 'cancelada', 'Cancelada'

    usuario = models.ForeignKey(USER, verbose_name='usuario', on_delete=models.CASCADE, related_name='citas')
    asesor = models.ForeignKey(USER, verbose_name='asesor que atenderá', on_delete=models.SET_NULL,
                               null=True, related_name='citas_atendidas')
    expediente = models.ForeignKey(Expediente, verbose_name='expediente relacionado', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='citas')
    motivo = models.CharField('motivo', max_length=200)
    modalidad = models.CharField('modalidad', max_length=10, choices=Modalidad.choices)
    fecha = models.DateField('fecha')
    hora = models.TimeField('hora')
    enlace = models.URLField('enlace de la reunión', blank=True)
    direccion = models.CharField('dirección', max_length=200, blank=True)
    estado = models.CharField('estado', max_length=12, choices=Estado.choices, default=Estado.PROGRAMADA)
    creado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'hora']

    @property
    def tono(self):
        return {'programada': 'info', 'reprogramada': 'warn', 'cancelada': 'neutral'}[self.estado]


# ==================================================================== Pagos (RS-10, RNF-07)

class Comprobante(models.Model):
    class Medio(models.TextChoices):
        TRANSFERENCIA = 'transferencia', 'Transferencia bancaria'
        DEPOSITO = 'deposito', 'Depósito bancario'

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de revisión'
        CONFIRMADO = 'confirmado', 'Confirmado'
        RECHAZADO = 'rechazado', 'Rechazado'

    expediente = models.ForeignKey(Expediente, verbose_name='servicio', on_delete=models.CASCADE, related_name='comprobantes')
    enviado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    archivo = models.FileField(upload_to=ruta_privada)
    nombre_original = models.CharField(max_length=255)
    monto = models.DecimalField('monto pagado (USD)', max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(Decimal('0.01'))])
    fecha_pago = models.DateField('fecha del pago')
    numero = models.CharField('número de comprobante', max_length=40)
    medio = models.CharField('medio de pago', max_length=14, choices=Medio.choices)
    estado = models.CharField('estado', max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    motivo_rechazo = models.TextField('motivo del rechazo', blank=True)
    revisado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    revisado_en = models.DateTimeField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado']
        constraints = [
            # Un mismo comprobante no puede estar dos veces en revisión o confirmado.
            models.UniqueConstraint(fields=['expediente', 'numero'], condition=~Q(estado='rechazado'),
                                    name='comprobante_unico_activo'),
        ]

    @property
    def tono(self):
        return {'pendiente': 'warn', 'confirmado': 'success', 'rechazado': 'danger'}[self.estado]


class Abono(models.Model):
    """Abono confirmado. OneToOne con el comprobante: nunca dos abonos por comprobante (RNF-07)."""
    comprobante = models.OneToOneField(Comprobante, on_delete=models.PROTECT, related_name='abono')
    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='abonos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    registrado_por = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, related_name='+')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'pk']


# Requisitos orientativos para la página pública de visas.
REQUISITOS_VISA = {
    'Estados Unidos': ['Pasaporte vigente (mínimo 6 meses)', 'Formulario DS-160 completado', 'Foto 5x5 cm fondo blanco',
                       'Comprobante de pago de la tasa consular', 'Respaldos económicos y laborales'],
    'España (Schengen)': ['Pasaporte vigente con 2 hojas libres', 'Formulario de solicitud Schengen',
                          'Seguro de viaje (cobertura mínima 30.000 EUR)', 'Reserva de vuelo y alojamiento',
                          'Estados de cuenta de los últimos 3 meses'],
    'Canadá': ['Pasaporte vigente', 'Formularios de solicitud de visa de visitante', 'Fotografía digital reciente',
               'Prueba de solvencia económica', 'Carta de trabajo o matrícula de estudios'],
    'Reino Unido': ['Pasaporte vigente', 'Solicitud en línea', 'Estados de cuenta de los últimos 6 meses',
                    'Itinerario de viaje', 'Carta de empleo'],
}
