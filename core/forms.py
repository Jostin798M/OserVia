from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.core.validators import RegexValidator
from django.utils import timezone

from . import validadores as v
from .models import (AvisoVuelo, Beneficio, Cita, CitaConsular, Comprobante, ContenidoSitio, CorreoConsulado,
                     Cotizacion, DocumentoRequerido, DocumentoViaje, Expediente, Oferta, Perfil,
                     PreguntaFrecuente, Promocion, Publicacion, Servicio, SolicitudViaje, VueloContratado)
from .permisos import es_admin

User = get_user_model()

validar_telefono = RegexValidator(r'^\+?[0-9 ()-]{7,20}$', 'Ingresa un teléfono válido (solo números, puede iniciar con +).')
validar_documento = RegexValidator(r'^[A-Za-z0-9-]{5,20}$', 'Ingresa un número de cédula o pasaporte válido.')

SI_NO = [(True, 'Sí'), (False, 'No')]


def _bool(valor):
    return valor in (True, 'True', 'true', '1', 1)


def fecha(attrs=None):
    return forms.DateInput(attrs={'type': 'date', **(attrs or {})}, format='%Y-%m-%d')


def fecha_hora():
    return forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')


def hora():
    return forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')


def personal_activo():
    return (User.objects.filter(is_active=True, perfil__rol__in=['asesor', 'admin'])
            .select_related('perfil').order_by('first_name', 'email'))


class AsesorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, u):
        return f'{u.get_full_name() or u.email} · {u.perfil.get_rol_display()}'


class UsuarioChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, u):
        return f'{u.get_full_name() or "(sin nombre)"} · {u.email}'


class EstiloMixin:
    """Clase CSS de los controles y marca de campos con error."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, (forms.RadioSelect, forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                continue
            base = 'select' if isinstance(w, forms.Select) else 'input'
            w.attrs['class'] = f"{base} {w.attrs.get('class', '')}".strip()

    def full_clean(self):
        # Se marca después de validar: así los formularios que ajustan sus opciones
        # en __init__ no se validan antes de tiempo.
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs['aria-invalid'] = 'true'


# ==================================================================== Autenticación (RS-01)

class LoginForm(EstiloMixin, forms.Form):
    email = forms.EmailField(label='Correo electrónico', widget=forms.EmailInput(
        attrs={'autocomplete': 'email', 'placeholder': 'tu@correo.com', 'autofocus': True}))
    password = forms.CharField(label='Contraseña', strip=False, widget=forms.PasswordInput(
        attrs={'autocomplete': 'current-password', 'placeholder': '••••••••'}))
    recordar = forms.BooleanField(label='Mantener la sesión iniciada', required=False, initial=True)

    MENSAJE_ERROR = 'El correo o la contraseña no son correctos, o la cuenta está deshabilitada.'

    def __init__(self, request=None, *args, **kwargs):
        self.request, self.user = request, None
        super().__init__(*args, **kwargs)

    def clean(self):
        from . import seguridad
        data = super().clean()
        email, password = data.get('email'), data.get('password')
        if email and password:
            if seguridad.esta_bloqueado(self.request, email):
                raise forms.ValidationError('Demasiados intentos fallidos. Espera 15 minutos antes de volver a intentarlo.')
            user = authenticate(self.request, email=email, password=password)
            if user is None:
                seguridad.registrar_fallo(self.request, email)
                raise forms.ValidationError(self.MENSAJE_ERROR)
            seguridad.limpiar(self.request, email)
            self.user = user
        return data


class RegistroForm(EstiloMixin, forms.Form):
    """RS-01.1 y RS-01.5: desde el registro público solo se crean cuentas de usuario."""
    first_name = forms.CharField(label='Nombres', max_length=150,
                                 widget=forms.TextInput(attrs={'autocomplete': 'given-name', 'placeholder': 'María José'}))
    last_name = forms.CharField(label='Apellidos', max_length=150,
                                widget=forms.TextInput(attrs={'autocomplete': 'family-name', 'placeholder': 'Pérez Vera'}))
    email = forms.EmailField(label='Correo electrónico',
                             widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'tu@correo.com'}))
    telefono = forms.CharField(label='Teléfono', max_length=20, validators=[validar_telefono],
                               widget=forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel', 'placeholder': '+593 99 123 4567'}))
    password1 = forms.CharField(label='Contraseña', strip=False, help_text='Mínimo 8 caracteres, no solo números.',
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    password2 = forms.CharField(label='Confirmar contraseña', strip=False,
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    acepto = forms.BooleanField(label='Acepto los Términos y condiciones y la Política de privacidad',
                                error_messages={'required': 'Debes aceptar los Términos y condiciones y la Política de privacidad.'})

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        elif p1:
            temp = User(username=data.get('email', ''), email=data.get('email', ''),
                        first_name=data.get('first_name', ''), last_name=data.get('last_name', ''))
            try:
                password_validation.validate_password(p1, temp)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return data

    def save(self, rol=Perfil.Rol.USUARIO):
        d = self.cleaned_data
        user = User.objects.create_user(username=d['email'], email=d['email'], password=d['password1'],
                                        first_name=d['first_name'].strip(), last_name=d['last_name'].strip(),
                                        is_staff=rol != Perfil.Rol.USUARIO)
        Perfil.objects.create(usuario=user, telefono=d['telefono'], rol=rol,
                              terminos_aceptados_en=timezone.now() if d.get('acepto') else None)
        return user


class CrearPersonalForm(RegistroForm):
    """RS-01.5: el administrador crea cuentas de asesor (o de otro administrador)."""
    rol = forms.ChoiceField(label='Rol', choices=[('asesor', 'Asesor'), ('admin', 'Administrador')], initial='asesor')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['acepto']  # la cuenta la crea el administrador

    def save(self):
        return super().save(rol=self.cleaned_data['rol'])


class RecuperarForm(EstiloMixin, PasswordResetForm):
    """RS-01.4."""
    def get_users(self, email):
        return (u for u in User.objects.filter(email__iexact=email, is_active=True) if u.has_usable_password())


class NuevaPasswordForm(EstiloMixin, SetPasswordForm):
    pass


class PerfilForm(EstiloMixin, forms.Form):
    first_name = forms.CharField(label='Nombres', max_length=150)
    last_name = forms.CharField(label='Apellidos', max_length=150)
    email = forms.EmailField(label='Correo electrónico', help_text='Es el correo con el que inicias sesión.')
    telefono = forms.CharField(label='Teléfono', max_length=20, required=False, validators=[validar_telefono],
                               widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': '+593 99 123 4567'}))
    cedula = forms.CharField(label='Cédula / pasaporte', max_length=20, required=False, validators=[validar_documento],
                             help_text='Se completará automáticamente en tus solicitudes.')

    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.perfil, _ = Perfil.objects.get_or_create(usuario=user)
        kwargs.setdefault('initial', {'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email,
                                      'telefono': self.perfil.telefono, 'cedula': self.perfil.cedula})
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        otros = User.objects.exclude(pk=self.user.pk)
        if otros.filter(email__iexact=email).exists() or otros.filter(username__iexact=email).exists():
            raise forms.ValidationError('Ya existe otra cuenta con este correo.')
        return email

    def save(self):
        d, u = self.cleaned_data, self.user
        u.username = d['email']
        u.first_name, u.last_name, u.email = d['first_name'].strip(), d['last_name'].strip(), d['email']
        u.save()
        self.perfil.telefono, self.perfil.cedula = d['telefono'], d['cedula']
        self.perfil.save()
        return u


class CambiarPasswordForm(EstiloMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Contraseña actual'
        self.fields['old_password'].widget.attrs.pop('autofocus', None)
        self.fields['new_password1'].label = 'Nueva contraseña'
        self.fields['new_password1'].help_text = 'Mínimo 8 caracteres, no solo números ni muy común.'
        self.fields['new_password2'].label = 'Confirmar nueva contraseña'
        self.fields['new_password2'].help_text = 'Escríbela de nuevo para confirmar.'


# ==================================================================== Público

class ConsultaForm(EstiloMixin, forms.Form):
    """RS-04.5: nombre, motivo y teléfono, todos obligatorios."""
    nombre = forms.CharField(label='Nombre completo', max_length=150,
                             error_messages={'required': 'Ingresa tu nombre completo.'},
                             widget=forms.TextInput(attrs={'autocomplete': 'name', 'placeholder': 'Tu nombre y apellido'}))
    telefono = forms.CharField(label='Teléfono', max_length=20, validators=[validar_telefono],
                               error_messages={'required': 'Ingresa un teléfono de contacto.'},
                               widget=forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel', 'placeholder': '+593 99 123 4567'}))
    motivo = forms.CharField(label='Motivo de consulta', max_length=1000,
                             error_messages={'required': 'Cuéntanos el motivo de tu consulta.'},
                             widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ej.: quiero información sobre la visa Schengen'}))
    sitio_web = forms.CharField(required=False, widget=forms.HiddenInput)  # trampa para bots

    def clean_sitio_web(self):
        if self.cleaned_data.get('sitio_web'):
            raise forms.ValidationError('Solicitud no válida.')
        return ''


class BuscarVuelosForm(EstiloMixin, forms.Form):
    """RS-05.7: filtros combinables."""
    destino = forms.CharField(label='Destino', required=False,
                              widget=forms.TextInput(attrs={'placeholder': '¿A dónde quieres ir?'}))
    fecha = forms.DateField(label='Fecha de salida', required=False, widget=fecha())
    precio_max = forms.DecimalField(label='Precio máx. por persona (USD)', required=False, min_value=0,
                                    widget=forms.NumberInput(attrs={'placeholder': 'Ej.: 900', 'step': '1'}))
    duracion_max = forms.DecimalField(label='Duración máx. del vuelo (h)', required=False, min_value=0,
                                      widget=forms.NumberInput(attrs={'placeholder': 'Ej.: 12', 'step': '0.5'}))


# ==================================================================== Cotizaciones (RS-05)

class SolicitudViajeForm(EstiloMixin, forms.ModelForm):
    seguro = forms.TypedChoiceField(label='¿Deseas incluir un seguro de viaje?', choices=SI_NO, coerce=_bool,
                                    widget=forms.RadioSelect,
                                    error_messages={'required': 'Indica si deseas incluir un seguro de viaje.'})

    class Meta:
        model = SolicitudViaje
        fields = ['tipo', 'trayecto', 'origen', 'destino', 'fecha_salida', 'fecha_regreso', 'pasajeros', 'clase',
                  'seguro', 'nombre', 'cedula', 'email', 'telefono', 'comentarios']
        widgets = {
            'tipo': forms.RadioSelect, 'trayecto': forms.RadioSelect,
            'origen': forms.TextInput(attrs={'placeholder': 'Ciudad o aeropuerto', 'list': 'ciudades', 'autocomplete': 'off'}),
            'destino': forms.TextInput(attrs={'placeholder': 'Ciudad, país o paquete', 'list': 'ciudades', 'autocomplete': 'off'}),
            'fecha_salida': fecha(), 'fecha_regreso': fecha({'data-min-from': 'id_fecha_salida'}),
            'pasajeros': forms.NumberInput(attrs={'min': 1, 'max': 20, 'inputmode': 'numeric'}),
            'cedula': forms.TextInput(attrs={'placeholder': '0912345678'}),
            'telefono': forms.TextInput(attrs={'type': 'tel', 'placeholder': '+593 99 123 4567'}),
            'comentarios': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Horarios preferidos, equipaje, presupuesto…'}),
        }
        labels = {'fecha_salida': 'Salida', 'fecha_regreso': 'Regreso', 'clase': 'Clase de cabina',
                  'destino': 'Destino o paquete'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoy = timezone.localdate().isoformat()
        self.fields['fecha_salida'].widget.attrs['min'] = hoy
        self.fields['fecha_regreso'].widget.attrs['min'] = hoy
        self.fields['trayecto'].choices = SolicitudViaje.Trayecto.choices
        self.fields['trayecto'].required = False
        self.fields['clase'].choices = [('', 'Sin preferencia')] + list(SolicitudViaje.Clase.choices)
        self.fields['clase'].required = False
        self.fields['cedula'].validators.append(validar_documento)
        self.fields['telefono'].validators.append(validar_telefono)

    def clean_fecha_salida(self):
        f = self.cleaned_data['fecha_salida']
        if f < timezone.localdate():
            raise forms.ValidationError('La fecha de salida no puede estar en el pasado.')
        return f

    def clean(self):
        d = super().clean()
        tipo, salida, regreso = d.get('tipo'), d.get('fecha_salida'), d.get('fecha_regreso')
        if tipo == SolicitudViaje.Tipo.VUELO:
            if not d.get('origen'):
                self.add_error('origen', 'Indica la ciudad de origen.')
            if not d.get('trayecto'):
                self.add_error('trayecto', 'Indica si el viaje es solo de ida o de ida y vuelta.')
            elif d['trayecto'] == SolicitudViaje.Trayecto.IDA:
                d['fecha_regreso'] = regreso = None
            elif not regreso:
                self.add_error('fecha_regreso', 'Para un viaje de ida y vuelta indica la fecha de regreso.')
        elif tipo == SolicitudViaje.Tipo.PAQUETE:
            d['trayecto'], d['clase'] = '', ''
            if not regreso:
                self.add_error('fecha_regreso', 'Indica la fecha prevista de regreso del paquete.')
        if salida and regreso and regreso < salida:
            self.add_error('fecha_regreso', 'El regreso debe ser posterior a la salida.')
        if d.get('origen') and d.get('destino') and d['origen'].strip().lower() == d['destino'].strip().lower():
            self.add_error('destino', 'El destino debe ser distinto del origen.')
        return d


class AceptarCotizacionForm(forms.Form):
    """RS-05.3: si la cotización no incluye seguro, se pregunta si desea contratarlo."""
    contratar_seguro = forms.TypedChoiceField(label='Esta cotización no incluye seguro de viaje. ¿Deseas contratarlo?',
                                              choices=SI_NO, coerce=_bool, widget=forms.RadioSelect,
                                              error_messages={'required': 'Indica si deseas contratar el seguro de viaje.'})

    def __init__(self, cotizacion, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if cotizacion.incluye_seguro:
            del self.fields['contratar_seguro']


class CotizacionForm(EstiloMixin, forms.ModelForm):
    """RS-05.5."""
    incluye_seguro = forms.TypedChoiceField(label='¿Incluye seguro de viaje?', choices=SI_NO, coerce=_bool,
                                            widget=forms.RadioSelect)

    class Meta:
        model = Cotizacion
        fields = ['servicios_incluidos', 'precio_total', 'vigencia', 'incluye_seguro', 'condiciones']
        widgets = {'servicios_incluidos': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Vuelo GYE–MAD ida y vuelta\nEquipaje de 23 kg'}),
                   'condiciones': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Forma de pago, penalidades, reserva…'}),
                   'vigencia': fecha(), 'precio_total': forms.NumberInput(attrs={'step': '0.01', 'min': 0})}

    def clean_vigencia(self):
        f = self.cleaned_data['vigencia']
        if f < timezone.localdate():
            raise forms.ValidationError('La vigencia no puede ser una fecha pasada.')
        return f


class AsignarForm(EstiloMixin, forms.Form):
    asesor = AsesorChoiceField(label='Asesor responsable', queryset=User.objects.none(), empty_label='Selecciona un asesor')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asesor'].queryset = personal_activo()


# ==================================================================== Expedientes (RS-06, RS-08)

class ExpedienteForm(EstiloMixin, forms.ModelForm):
    usuario = UsuarioChoiceField(label='Cuenta del usuario', queryset=User.objects.none(),
                                 empty_label='Selecciona la cuenta del usuario')
    asesor = AsesorChoiceField(label='Asesor responsable', queryset=User.objects.none(), required=False,
                               empty_label='Sin asignar')

    class Meta:
        model = Expediente
        fields = ['usuario', 'tipo', 'asesor', 'nombre', 'documento_identidad', 'telefono', 'email', 'precio_total',
                  'pais', 'tipo_visa', 'pasaporte',
                  'paquete_nombre', 'destino', 'fecha_salida', 'fecha_regreso', 'servicios_incluidos', 'itinerario']
        widgets = {
            'tipo': forms.RadioSelect,
            'pais': forms.TextInput(attrs={'list': 'paises', 'placeholder': 'Ej.: España (Schengen)'}),
            'tipo_visa': forms.TextInput(attrs={'list': 'tipos-visa', 'placeholder': 'Ej.: Turismo'}),
            'fecha_salida': fecha(), 'fecha_regreso': fecha(),
            'servicios_incluidos': forms.Textarea(attrs={'rows': 3}), 'itinerario': forms.Textarea(attrs={'rows': 5}),
            'precio_total': forms.NumberInput(attrs={'step': '0.01', 'min': 0}),
            'telefono': forms.TextInput(attrs={'type': 'tel'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario'].queryset = (User.objects.filter(is_active=True, perfil__rol='usuario')
                                           .order_by('first_name', 'email'))
        self.fields['asesor'].queryset = personal_activo()
        if user and not es_admin(user):
            del self.fields['asesor']  # el asesor que lo crea queda como responsable
        if self.instance.pk:
            for campo in ('usuario', 'tipo', 'asesor'):
                self.fields.pop(campo, None)

    def clean(self):
        d = super().clean()
        tipo = d.get('tipo') or self.instance.tipo
        if tipo == Expediente.Tipo.VISA:
            for campo in ('pais', 'tipo_visa'):
                if not d.get(campo):
                    self.add_error(campo, 'Obligatorio para una asesoría de visa.')
        if tipo == Expediente.Tipo.PAQUETE:
            for campo in ('paquete_nombre', 'destino', 'fecha_salida', 'fecha_regreso'):
                if not d.get(campo):
                    self.add_error(campo, 'Obligatorio para un paquete turístico.')
        if d.get('fecha_salida') and d.get('fecha_regreso') and d['fecha_regreso'] < d['fecha_salida']:
            self.add_error('fecha_regreso', 'El regreso debe ser posterior a la salida.')
        return d


class EtapaForm(EstiloMixin, forms.Form):
    """RS-06.2, RS-06.3."""
    etapa = forms.ChoiceField(label='Etapa', choices=Expediente.Etapa.choices)
    fecha_presentacion = forms.DateField(label='Fecha en que se presentó al consulado', required=False, widget=fecha())

    def __init__(self, expediente, *args, **kwargs):
        self.expediente = expediente
        kwargs.setdefault('initial', {'etapa': expediente.etapa, 'fecha_presentacion': expediente.fecha_presentacion})
        super().__init__(*args, **kwargs)

    def clean(self):
        d = super().clean()
        etapa = d.get('etapa')
        if etapa in (Expediente.Etapa.PREPARACION, Expediente.Etapa.PRESENTADO) and not self.expediente.documentacion_completa:
            raise forms.ValidationError('Documentación incompleta: no se puede avanzar a «Preparación para la cita '
                                        'consular» hasta que todos los documentos solicitados estén aceptados.')
        if etapa == Expediente.Etapa.PRESENTADO and not d.get('fecha_presentacion'):
            self.add_error('fecha_presentacion', 'Indica la fecha en que el usuario se presentó al consulado.')
        if d.get('fecha_presentacion') and d['fecha_presentacion'] > timezone.localdate():
            self.add_error('fecha_presentacion', 'La fecha no puede ser futura.')
        return d


class ResultadoForm(EstiloMixin, forms.ModelForm):
    """RS-08.4."""
    class Meta:
        model = Expediente
        fields = ['resultado', 'resultado_fecha', 'resultado_detalle']
        widgets = {'resultado_fecha': fecha(), 'resultado_detalle': forms.Textarea(attrs={'rows': 2})}

    def clean(self):
        d = super().clean()
        if d.get('resultado') and d['resultado'] != Expediente.Resultado.NO_REGISTRADO and not d.get('resultado_fecha'):
            self.add_error('resultado_fecha', 'Indica la fecha en que se recibió el resultado.')
        return d


class SeguimientoForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Expediente
        fields = ['estado', 'precio_total', 'comentario_usuario', 'notas_internas']
        widgets = {'comentario_usuario': forms.Textarea(attrs={'rows': 3}), 'notas_internas': forms.Textarea(attrs={'rows': 2}),
                   'precio_total': forms.NumberInput(attrs={'step': '0.01', 'min': 0})}


class DocumentoRequeridoForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = DocumentoRequerido
        fields = ['nombre', 'indicaciones']
        widgets = {'nombre': forms.TextInput(attrs={'placeholder': 'Ej.: Pasaporte vigente', 'list': 'docs-sugeridos'}),
                   'indicaciones': forms.TextInput(attrs={'placeholder': 'Ej.: escaneado a color, todas las hojas'})}


class RevisionForm(EstiloMixin, forms.Form):
    """RS-07.3."""
    ACCIONES = [('revision', 'Marcar en revisión'), ('aceptado', 'Aceptar documento'), ('correccion', 'Pedir corrección')]
    accion_doc = forms.ChoiceField(label='Resultado', choices=ACCIONES)
    comentario = forms.CharField(label='Qué debe corregirse', required=False,
                                 widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Obligatorio si pides corrección'}))

    def __init__(self, documento, *args, **kwargs):
        self.documento = documento
        super().__init__(*args, **kwargs)

    def clean(self):
        d = super().clean()
        accion, estado = d.get('accion_doc'), self.documento.estado
        if accion == 'revision' and estado != 'recibido':
            raise forms.ValidationError('Solo un documento recibido puede pasar a revisión.')
        if accion in ('aceptado', 'correccion') and estado not in ('recibido', 'revision'):
            raise forms.ValidationError('Solo se pueden revisar documentos recibidos o en revisión.')
        if accion == 'correccion' and not d.get('comentario', '').strip():
            self.add_error('comentario', 'Explica qué debe corregirse.')
        return d


class SubirDocumentoForm(forms.Form):
    """RS-07.2 / RS-07.4: PDF o PNG de hasta 10 MB."""
    documento = forms.ModelChoiceField(label='Documento solicitado', queryset=DocumentoRequerido.objects.none(),
                                       empty_label='Selecciona el documento')
    archivo = v.ArchivoField(label='Archivo', extensiones=v.DOCUMENTOS_USUARIO, max_mb=10)

    def __init__(self, expediente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['documento'].queryset = expediente.documentos.filter(estado__in=['pendiente', 'correccion'])
        self.fields['documento'].widget.attrs['class'] = 'select'


class CitaConsularForm(EstiloMixin, forms.ModelForm):
    confirmacion = v.ArchivoField(label='Confirmación de la cita', required=False)

    class Meta:
        model = CitaConsular
        fields = ['consulado', 'direccion', 'fecha', 'hora', 'confirmacion']
        widgets = {'fecha': fecha(), 'hora': hora()}


class CorreoConsuladoForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = CorreoConsulado
        fields = ['destinatario', 'asunto', 'fecha_envio', 'proxima_revision', 'respuesta']
        widgets = {'fecha_envio': fecha(), 'proxima_revision': fecha(), 'respuesta': forms.Textarea(attrs={'rows': 2})}


class VueloContratadoForm(EstiloMixin, forms.ModelForm):
    boleto = v.ArchivoField(label='Boleto emitido', required=False)

    class Meta:
        model = VueloContratado
        fields = ['aerolinea', 'numero_vuelo', 'origen', 'destino', 'salida', 'llegada', 'boleto']
        widgets = {'salida': fecha_hora(), 'llegada': fecha_hora()}

    def clean(self):
        d = super().clean()
        if d.get('salida') and d.get('llegada') and d['llegada'] <= d['salida']:
            self.add_error('llegada', 'La llegada debe ser posterior a la salida.')
        return d


class DocumentoViajeForm(EstiloMixin, forms.ModelForm):
    archivo = v.ArchivoField(label='Archivo')

    class Meta:
        model = DocumentoViaje
        fields = ['titulo', 'archivo']
        widgets = {'titulo': forms.TextInput(attrs={'placeholder': 'Ej.: Voucher del hotel'})}


class AvisoVueloForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = AvisoVuelo
        fields = ['tipo', 'aerolinea', 'numero_vuelo', 'fecha_vuelo', 'cambio_informado', 'nueva_fecha_hora', 'fecha_aviso']
        widgets = {'fecha_vuelo': fecha(), 'fecha_aviso': fecha(), 'nueva_fecha_hora': fecha_hora(),
                   'cambio_informado': forms.Textarea(attrs={'rows': 2})}

    def clean(self):
        d = super().clean()
        if d.get('tipo') == AvisoVuelo.Tipo.REPROGRAMACION and not d.get('nueva_fecha_hora'):
            self.add_error('nueva_fecha_hora', 'Indica la nueva fecha y hora del vuelo reprogramado.')
        return d


# ==================================================================== Pagos (RS-10)

class ComprobanteForm(EstiloMixin, forms.ModelForm):
    """RS-10.2."""
    expediente = forms.ModelChoiceField(label='Servicio', queryset=Expediente.objects.none(), empty_label='Selecciona el servicio')
    archivo = v.ArchivoField(label='Comprobante (imagen o PDF)', extensiones=v.COMPROBANTES)

    class Meta:
        model = Comprobante
        fields = ['expediente', 'monto', 'fecha_pago', 'numero', 'medio', 'archivo']
        widgets = {'fecha_pago': fecha(), 'monto': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'})}

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expediente'].queryset = Expediente.objects.filter(usuario=user).exclude(estado='cancelado')
        self.fields['expediente'].label_from_instance = lambda e: f'{e.codigo} · {e.titulo}'
        self.fields['fecha_pago'].widget.attrs['max'] = timezone.localdate().isoformat()
        self.fields['medio'].choices = [('', 'Selecciona el medio de pago')] + list(Comprobante.Medio.choices)

    def clean_fecha_pago(self):
        f = self.cleaned_data['fecha_pago']
        if f > timezone.localdate():
            raise forms.ValidationError('La fecha del pago no puede ser futura.')
        return f

    def clean(self):
        d = super().clean()
        exp, numero = d.get('expediente'), (d.get('numero') or '').strip()
        if exp and numero and exp.comprobantes.filter(numero__iexact=numero).exclude(estado='rechazado').exists():
            self.add_error('numero', 'Este comprobante ya fue enviado para este servicio.')
        return d

    def validate_unique(self):
        pass  # la unicidad se valida arriba con un mensaje claro


class RechazoComprobanteForm(EstiloMixin, forms.Form):
    motivo = forms.CharField(label='Motivo del rechazo', widget=forms.Textarea(attrs={'rows': 2}),
                             error_messages={'required': 'Explica el motivo del rechazo.'})


# ==================================================================== Citas (RS-09)

class CitaForm(EstiloMixin, forms.ModelForm):
    usuario = UsuarioChoiceField(label='Usuario', queryset=User.objects.none(), empty_label='Selecciona el usuario')
    asesor = AsesorChoiceField(label='Asesor que atenderá', queryset=User.objects.none(), empty_label='Selecciona')

    class Meta:
        model = Cita
        fields = ['usuario', 'asesor', 'motivo', 'modalidad', 'fecha', 'hora', 'enlace', 'direccion', 'estado']
        widgets = {'fecha': fecha(), 'hora': hora(), 'modalidad': forms.RadioSelect,
                   'enlace': forms.URLInput(attrs={'placeholder': 'https://meet.google.com/…'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario'].queryset = User.objects.filter(is_active=True, perfil__rol='usuario').order_by('first_name')
        self.fields['asesor'].queryset = personal_activo()
        if not self.instance.pk:
            del self.fields['estado']
        self.fields['fecha'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean(self):
        d = super().clean()
        if d.get('modalidad') == Cita.Modalidad.VIRTUAL:
            if not d.get('enlace'):
                self.add_error('enlace', 'Para una cita virtual indica el enlace de la reunión.')
            d['direccion'] = ''
        elif d.get('modalidad') == Cita.Modalidad.PRESENCIAL:
            if not d.get('direccion'):
                self.add_error('direccion', 'Para una cita presencial indica la dirección.')
            d['enlace'] = ''  # RS-09.1: no se otorga enlace en modalidad presencial
        if d.get('fecha') and d['fecha'] < timezone.localdate() and 'fecha' in self.changed_data:
            self.add_error('fecha', 'La fecha no puede estar en el pasado.')
        return d


# ==================================================================== Contenido (RS-03.1)

def _textarea(rows=3):
    return forms.Textarea(attrs={'rows': rows})


class OfertaForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Oferta
        fields = ['tipo', 'titulo', 'descripcion', 'origen', 'destino', 'fecha_salida', 'fecha_regreso',
                  'duracion_horas', 'duracion_dias', 'precio_persona', 'servicios_incluidos', 'condiciones',
                  'incluye_seguro', 'promocion', 'publicado', 'orden']
        widgets = {'tipo': forms.RadioSelect, 'fecha_salida': fecha(), 'fecha_regreso': fecha(),
                   'descripcion': _textarea(), 'servicios_incluidos': _textarea(4), 'condiciones': _textarea()}

    def clean(self):
        d = super().clean()
        if d.get('tipo') == Oferta.Tipo.VUELO:
            if not d.get('origen'):
                self.add_error('origen', 'Obligatorio para una oferta de vuelo.')
            if d.get('duracion_horas') is None:
                self.add_error('duracion_horas', 'Obligatorio para una oferta de vuelo.')
        if d.get('tipo') == Oferta.Tipo.PAQUETE and not d.get('duracion_dias'):
            self.add_error('duracion_dias', 'Obligatorio para un paquete turístico.')
        if d.get('fecha_salida') and d.get('fecha_regreso') and d['fecha_regreso'] < d['fecha_salida']:
            self.add_error('fecha_regreso', 'El regreso debe ser posterior a la salida.')
        return d


class PromocionForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Promocion
        fields = ['titulo', 'descripcion', 'condiciones', 'fecha_inicio', 'fecha_fin', 'publicado', 'orden']
        widgets = {'fecha_inicio': fecha(), 'fecha_fin': fecha(), 'descripcion': _textarea(), 'condiciones': _textarea()}

    def clean(self):
        d = super().clean()
        if d.get('fecha_inicio') and d.get('fecha_fin') and d['fecha_fin'] < d['fecha_inicio']:
            self.add_error('fecha_fin', 'La fecha de finalización debe ser posterior a la de inicio.')
        return d


class ServicioForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['titulo', 'descripcion', 'icono', 'publicado', 'orden']
        widgets = {'descripcion': _textarea()}


class BeneficioForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Beneficio
        fields = ['titulo', 'descripcion', 'icono', 'publicado', 'orden']
        widgets = {'descripcion': _textarea()}


class PreguntaForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = PreguntaFrecuente
        fields = ['pregunta', 'respuesta', 'palabras_clave', 'publicado', 'orden']
        widgets = {'respuesta': _textarea(4)}


class PublicacionForm(EstiloMixin, forms.ModelForm):
    imagen = v.ArchivoField(label='Imagen', extensiones=v.IMAGENES, max_mb=5, required=False)
    video = v.ArchivoField(label='Video', extensiones=v.VIDEOS, max_mb=80, required=False)

    class Meta:
        model = Publicacion
        fields = ['titulo', 'texto', 'imagen', 'video', 'enlace', 'fecha', 'publicado', 'orden']
        widgets = {'texto': _textarea(), 'fecha': fecha()}

    def clean(self):
        d = super().clean()
        if not (d.get('imagen') or d.get('video')):
            raise forms.ValidationError('Adjunta una imagen o un video.')
        return d


class SitioForm(EstiloMixin, forms.ModelForm):
    video_tutorial = v.ArchivoField(label='Video tutorial', extensiones=v.VIDEOS, max_mb=80, required=False)

    class Meta:
        model = ContenidoSitio
        exclude = ['actualizado']
        widgets = {'descripcion': _textarea(), 'historia': _textarea(5), 'mision': _textarea(), 'vision': _textarea()}
