"""Pruebas de aceptación: cada prueba indica el requerimiento (RS/RNF) que verifica."""
import shutil
import tempfile
import threading
from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core import servicios
from core.management.commands.cargar_demo import pdf, png
from core.models import (Abono, Asignacion, CambioEtapa, Cita, Comprobante, Consulta, Cotizacion, DocumentoRequerido,
                         Expediente, Oferta, Perfil, Promocion, SolicitudViaje, VueloContratado)

MEDIA = tempfile.mkdtemp()
HOY = timezone.localdate


def crear(email, rol='usuario', password='ClaveSegura123', **kw):
    u = User.objects.create_user(email, email, password, is_staff=rol != 'usuario', **kw)
    Perfil.objects.create(usuario=u, rol=rol, telefono='0991234567', cedula='0912345678')
    return u


def archivo_pdf(nombre='doc.pdf'):
    return SimpleUploadedFile(nombre, pdf('prueba'), content_type='application/pdf')


@override_settings(MEDIA_ROOT=MEDIA)
class Base(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.admin = crear('admin@t.com', 'admin', first_name='Ana')
        self.asesor = crear('asesor@t.com', 'asesor', first_name='Carla')
        self.asesor2 = crear('asesor2@t.com', 'asesor', first_name='Diego')
        self.user = crear('user@t.com', first_name='Jostin', last_name='Mora')
        self.otro = crear('otro@t.com')

    def expediente(self, tipo='visa', asesor=None, usuario=None, **kw):
        datos = {'pais': 'España (Schengen)', 'tipo_visa': 'Turismo'} if tipo == 'visa' else {}
        datos.update(kw)
        e = Expediente.objects.create(usuario=usuario or self.user, tipo=tipo, nombre='Jostin Mora', telefono='099',
                                      documento_identidad='0912345678', creado_por=self.admin, **datos)
        if asesor:
            servicios.asignar(e, asesor, self.admin)
        return e

    def como(self, user):
        self.client.force_login(user)
        return self.client


# ==================================================================== RS-01 Cuentas

class CuentasTest(Base):
    def test_rs_01_1_registro_con_confirmacion_y_validaciones(self):
        r = self.client.post(reverse('registro'), {'first_name': 'Luis', 'last_name': 'Paz', 'email': 'luis@t.com',
                                                   'telefono': '0991112222', 'password1': 'ViajeroFeliz2026',
                                                   'password2': 'ViajeroFeliz2026', 'acepto': 'on'}, follow=True)
        self.assertContains(r, 'Cuenta creada')
        self.assertEqual(User.objects.get(email='luis@t.com').perfil.rol, 'usuario')
        self.assertIsNotNone(User.objects.get(email='luis@t.com').perfil.terminos_aceptados_en)
        self.client.logout()
        r = self.client.post(reverse('registro'), {'first_name': 'X', 'last_name': 'Y', 'email': 'LUIS@t.com',
                                                   'telefono': '', 'password1': 'a', 'password2': 'a'})
        self.assertIn('email', r.context['form'].errors)
        self.assertIn('telefono', r.context['form'].errors)

    def test_registro_exige_aceptar_terminos(self):
        r = self.client.post(reverse('registro'), {'first_name': 'A', 'last_name': 'B', 'email': 'sin@t.com', 'telefono': '0990000000',
                                                   'password1': 'ViajeroFeliz2026', 'password2': 'ViajeroFeliz2026'})
        self.assertIn('acepto', r.context['form'].errors)
        self.assertFalse(User.objects.filter(email='sin@t.com').exists())
        for url in ['privacidad', 'terminos']:
            self.assertEqual(self.client.get(reverse(url)).status_code, 200)
        self.assertContains(self.client.get(reverse('login')), reverse('privacidad'))

    def test_rs_01_2_login_por_correo_y_cuenta_deshabilitada(self):
        r = self.client.post(reverse('login'), {'email': 'USER@t.com', 'password': 'ClaveSegura123'})
        self.assertRedirects(r, reverse('dashboard'))
        self.client.logout()
        self.user.is_active = False
        self.user.save()
        r = self.client.post(reverse('login'), {'email': 'user@t.com', 'password': 'ClaveSegura123'})
        self.assertContains(r, 'deshabilitada')

    def test_rs_01_2_personal_entra_al_panel(self):
        r = self.client.post(reverse('login'), {'email': 'asesor@t.com', 'password': 'ClaveSegura123'})
        self.assertRedirects(r, reverse('panel_inicio'))

    def test_rs_01_3_cerrar_sesion(self):
        self.como(self.user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)

    def test_rs_01_4_recuperar_contrasena_un_solo_uso(self):
        self.client.post(reverse('recuperar'), {'email': 'user@t.com'})
        self.assertEqual(len(mail.outbox), 1)
        enlace = [l for l in mail.outbox[0].body.splitlines() if '/recuperar/' in l][0].split('testserver')[1]
        r = self.client.get(enlace, follow=True)
        self.assertTrue(r.context['validlink'])
        r = self.client.post(r.redirect_chain[-1][0], {'new_password1': 'NuevaClave2026x', 'new_password2': 'NuevaClave2026x'})
        self.assertRedirects(r, reverse('recuperar_listo'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaClave2026x'))
        self.assertFalse(self.client.get(enlace, follow=True).context['validlink'])

    def test_rs_01_5_admin_crea_asesor_y_deshabilita_cuentas(self):
        self.como(self.admin)
        self.client.post(reverse('panel_personal'), {'first_name': 'Nuevo', 'last_name': 'Asesor', 'email': 'n@t.com',
                                                     'telefono': '0990000000', 'rol': 'asesor',
                                                     'password1': 'ClaveAsesor2026', 'password2': 'ClaveAsesor2026'})
        self.assertEqual(User.objects.get(email='n@t.com').perfil.rol, 'asesor')
        self.client.post(reverse('panel_cuenta_estado', args=[self.asesor.pk]))
        self.asesor.refresh_from_db()
        self.assertFalse(self.asesor.is_active)
        # Un asesor no puede crear cuentas.
        self.como(self.asesor2)
        self.assertEqual(self.client.get(reverse('panel_personal')).status_code, 404)

    def test_rs_01_5_registro_publico_no_crea_personal(self):
        self.client.post(reverse('registro'), {'first_name': 'A', 'last_name': 'B', 'email': 'x@t.com', 'telefono': '0990000000',
                                               'password1': 'ViajeroFeliz2026', 'password2': 'ViajeroFeliz2026', 'rol': 'admin', 'acepto': 'on'})
        self.assertEqual(User.objects.get(email='x@t.com').perfil.rol, 'usuario')

    def test_rnf_05_contrasena_cifrada(self):
        self.assertTrue(self.user.password.startswith('pbkdf2_sha256$'))
        self.assertNotIn('ClaveSegura123', self.user.password)

    def test_bloqueo_tras_5_intentos(self):
        for _ in range(5):
            self.client.post(reverse('login'), {'email': 'admin@t.com', 'password': 'mala'})
        r = self.client.post(reverse('login'), {'email': 'admin@t.com', 'password': 'ClaveSegura123'})
        self.assertContains(r, 'Demasiados intentos')

    def test_un_solo_acceso_y_salida_al_login(self):
        self.assertEqual(self.client.get('/panel/entrar/').status_code, 404)
        r = self.client.get(reverse('panel_expedientes'))
        self.assertRedirects(r, reverse('login') + '?next=/panel/expedientes/')
        r = self.client.post(reverse('login') + '?next=/panel/expedientes/', {'email': 'asesor@t.com', 'password': 'ClaveSegura123'})
        self.assertRedirects(r, '/panel/expedientes/')
        r = self.client.post(reverse('logout'))
        self.assertRedirects(r, reverse('login'))

    def test_admin_django_desactivado(self):
        self.assertEqual(self.client.get('/admin/').status_code, 404)


# ==================================================================== RS-02 Acceso y asignación

class AccesoTest(Base):
    def test_rs_02_2_asesor_solo_ve_lo_asignado(self):
        mio, ajeno = self.expediente(asesor=self.asesor), self.expediente(asesor=self.asesor2)
        self.como(self.asesor)
        self.assertEqual(self.client.get(mio.get_panel_url()).status_code, 200)
        self.assertEqual(self.client.get(ajeno.get_panel_url()).status_code, 404)
        self.assertEqual(self.client.post(ajeno.get_panel_url(), {'accion': 'seguimiento', 'estado': 'cancelado'}).status_code, 404)
        r = self.client.get(reverse('panel_expedientes') + '?estado=todos')
        self.assertContains(r, mio.codigo)
        self.assertNotContains(r, ajeno.codigo)

    def test_rs_02_1_admin_ve_todo(self):
        e = self.expediente(asesor=self.asesor2)
        self.como(self.admin)
        self.assertEqual(self.client.get(e.get_panel_url()).status_code, 200)

    def test_rs_02_3_y_rnf_06_usuario_solo_lo_suyo(self):
        e = self.expediente(asesor=self.asesor)
        d = DocumentoRequerido.objects.create(expediente=e, nombre='Pasaporte')
        servicios.subir_documento(d, archivo_pdf(), self.user)
        url_archivo = reverse('archivo', args=['documento', d.archivos.first().pk])
        self.como(self.otro)
        self.assertEqual(self.client.get(e.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(url_archivo).status_code, 404)
        self.assertEqual(self.client.get(reverse('panel_inicio')).status_code, 404)
        self.como(self.asesor2)
        self.assertEqual(self.client.get(url_archivo).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url_archivo).status_code, 302)
        self.como(self.user)
        self.assertEqual(self.client.get(url_archivo).status_code, 200)

    def test_rs_02_4_asignacion_guarda_quien_y_cuando(self):
        e = self.expediente()
        self.como(self.admin)
        self.client.post(e.get_panel_url(), {'accion': 'asignar', 'asesor': self.asesor.pk})
        e.refresh_from_db()
        self.assertEqual((e.asesor, e.asignado_por), (self.asesor, self.admin))
        self.assertIsNotNone(e.asignado_en)
        self.assertEqual(Asignacion.objects.filter(expediente=e).count(), 1)
        # Un asesor no puede reasignar.
        self.como(self.asesor)
        self.client.post(e.get_panel_url(), {'accion': 'asignar', 'asesor': self.asesor2.pk})
        e.refresh_from_db()
        self.assertEqual(e.asesor, self.asesor)


# ==================================================================== RS-03 / RS-04 Sitio público

class PublicoTest(Base):
    def setUp(self):
        super().setUp()
        self.promo = Promocion.objects.create(titulo='Promo X', descripcion='d', fecha_inicio=HOY() - timedelta(days=1),
                                              fecha_fin=HOY() + timedelta(days=9))
        self.mad = Oferta.objects.create(tipo='vuelo', titulo='Madrid', descripcion='d', origen='GYE', destino='Madrid',
                                         fecha_salida=HOY() + timedelta(days=30), duracion_horas=Decimal('11.5'),
                                         precio_persona=Decimal('980'), servicios_incluidos='Vuelo', condiciones='c',
                                         promocion=self.promo)
        self.mia = Oferta.objects.create(tipo='vuelo', titulo='Miami', descripcion='d', origen='GYE', destino='Miami',
                                         fecha_salida=HOY() + timedelta(days=20), duracion_horas=Decimal('3.5'),
                                         precio_persona=Decimal('420'), servicios_incluidos='Vuelo', condiciones='c')

    def test_rs_03_1_admin_publica_y_retira(self):
        self.como(self.admin)
        r = self.client.post(reverse('panel_contenido_nuevo', args=['preguntas']),
                             {'pregunta': '¿Hacen check-in?', 'respuesta': 'Sí', 'publicado': 'on', 'orden': 0})
        self.assertRedirects(r, reverse('panel_contenido_lista', args=['preguntas']))
        self.client.logout()
        self.assertContains(self.client.get(reverse('preguntas')), '¿Hacen check-in?')
        self.como(self.admin)
        self.client.post(reverse('panel_contenido_lista', args=['ofertas']), {'accion': 'publicar', 'id': self.mia.pk})
        self.client.logout()
        self.assertEqual(self.client.get(self.mia.get_absolute_url()).status_code, 404)

    def test_rs_03_2_ofertas_y_promociones_sin_sesion(self):
        r = self.client.get(self.mad.get_absolute_url())
        for texto in ['980', 'Vuelo', 'Promo X', 'Solicitar esta oferta', 'Total estimado']:
            self.assertContains(r, texto)
        r = self.client.get(reverse('promociones'))
        self.assertContains(r, self.promo.fecha_fin.strftime('%Y'))

    def test_rs_03_3_y_03_5_nosotros_y_pie_de_pagina(self):
        r = self.client.get(reverse('nosotros'))
        self.assertEqual(r.status_code, 200)
        for texto in ['Tungurahua', '+593 99 026 2569', 'infoclientes@osertravelec.com', 'Lunes a viernes',
                      reverse('vuelos'), reverse('paquetes'), reverse('nosotros'), reverse('contacto')]:
            self.assertContains(r, texto)

    def test_rs_04_4_boton_whatsapp(self):
        self.assertContains(self.client.get(reverse('vuelos')), 'https://wa.me/593990262569')

    def test_rs_04_1_asistente(self):
        self.assertIn('Lunes a viernes', self.client.get(reverse('asistente'), {'q': '¿cuál es el horario?'}).json()['respuesta'])
        self.assertIn('cotización', self.client.get(reverse('asistente'), {'q': 'cómo cotizar un viaje'}).json()['respuesta'])
        r = self.client.get(reverse('asistente'), {'q': 'xyzzy plutonio'}).json()
        self.assertFalse(r['encontrada'])
        self.assertIn('wa.me', r['enlace'])

    def test_rs_04_5_consulta_publica(self):
        r = self.client.post(reverse('inicio'), {'nombre': 'María', 'telefono': '0991234567', 'motivo': 'Visa'}, follow=True)
        self.assertContains(r, 'Recibimos tu consulta')
        c = Consulta.objects.get()
        self.assertIsNotNone(c.creado)
        r = self.client.post(reverse('contacto'), {'nombre': '', 'telefono': '0991234567', 'motivo': 'x'})
        self.assertContains(r, 'Ingresa tu nombre completo')

    def test_rs_04_6_asignar_consultas(self):
        c = Consulta.objects.create(nombre='M', telefono='099', motivo='x')
        self.como(self.admin)
        self.client.post(reverse('panel_consultas'), {'consulta': c.pk, 'accion': 'asignar', 'asesor': self.asesor.pk})
        c.refresh_from_db()
        self.assertEqual((c.asesor, c.estado), (self.asesor, 'asignada'))
        self.como(self.asesor)
        self.assertContains(self.client.get(reverse('panel_consultas')), 'M')
        self.como(self.asesor2)
        self.assertNotContains(self.client.get(reverse('panel_consultas')), c.codigo)

    def test_rs_05_7_buscar_vuelos_con_todos_los_filtros(self):
        url = reverse('vuelos')
        r = self.client.get(url, {'destino': 'mad', 'precio_max': 1000, 'duracion_max': 12})
        self.assertEqual(list(r.context['ofertas']), [self.mad])
        r = self.client.get(url, {'destino': 'mad', 'precio_max': 500})
        self.assertContains(r, 'No encontramos vuelos')
        r = self.client.get(url, {'fecha': self.mia.fecha_salida.isoformat()})
        self.assertEqual(list(r.context['ofertas']), [self.mia])


# ==================================================================== RS-05 Cotizaciones

class CotizacionesTest(Base):
    def datos(self, **kw):
        d = {'tipo': 'vuelo', 'trayecto': 'ida_vuelta', 'origen': 'GYE', 'destino': 'Madrid',
             'fecha_salida': (HOY() + timedelta(days=10)).isoformat(), 'fecha_regreso': (HOY() + timedelta(days=20)).isoformat(),
             'pasajeros': 2, 'seguro': 'True', 'nombre': 'Jostin', 'cedula': '0912345678', 'email': 'user@t.com', 'telefono': '0991234567'}
        d.update(kw)
        return d

    def test_rs_05_1_requiere_sesion(self):
        self.assertEqual(self.client.get(reverse('cotizar')).status_code, 302)

    def test_rs_05_1_ida_y_vuelta_exige_regreso(self):
        self.como(self.user)
        r = self.client.post(reverse('cotizar'), self.datos(fecha_regreso=''))
        self.assertIn('fecha_regreso', r.context['form'].errors)
        r = self.client.post(reverse('cotizar'), self.datos(trayecto='ida', fecha_regreso=''))
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse('cotizar'), self.datos(trayecto=''))
        self.assertIn('trayecto', r.context['form'].errors)

    def test_rs_05_1_paquete_con_fechas_previstas(self):
        self.como(self.user)
        r = self.client.post(reverse('cotizar'), self.datos(tipo='paquete', origen='', trayecto='', destino='Panamá'))
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse('cotizar'), self.datos(tipo='paquete', origen='', fecha_regreso=''))
        self.assertIn('fecha_regreso', r.context['form'].errors)

    def test_rs_05_2_seguro_obligatorio_y_guardado(self):
        self.como(self.user)
        r = self.client.post(reverse('cotizar'), self.datos(seguro=''))
        self.assertIn('seguro', r.context['form'].errors)
        self.client.post(reverse('cotizar'), self.datos(seguro='False'))
        self.assertFalse(SolicitudViaje.objects.get().seguro)

    def test_rs_05_4_referencia_de_oferta(self):
        promo = Promocion.objects.create(titulo='Promo', descripcion='d', fecha_inicio=HOY(), fecha_fin=HOY() + timedelta(days=5))
        o = Oferta.objects.create(tipo='vuelo', titulo='Madrid', descripcion='d', origen='GYE', destino='Madrid',
                                  fecha_salida=HOY() + timedelta(days=30), duracion_horas=10, precio_persona=900,
                                  servicios_incluidos='x', condiciones='c', promocion=promo)
        self.como(self.user)
        self.client.post(reverse('cotizar') + f'?oferta={o.codigo}', self.datos())
        self.client.post(reverse('cotizar'), self.datos())
        con, sin = SolicitudViaje.objects.order_by('pk')
        self.assertEqual((con.oferta_codigo, con.oferta_nombre, con.promocion_nombre), (o.codigo, 'Madrid', 'Promo'))
        self.assertEqual(sin.oferta_texto, 'Sin oferta seleccionada')

    def test_rs_05_5_y_05_6_cotizacion_aceptada_con_seguro(self):
        s = SolicitudViaje.objects.create(usuario=self.user, tipo='vuelo', trayecto='ida', origen='GYE', destino='MAD',
                                          fecha_salida=HOY() + timedelta(days=9), nombre='J', cedula='0912345678',
                                          email='u@t.com', telefono='099')
        servicios.asignar(s, self.asesor, self.admin)
        self.como(self.asesor2)
        self.assertEqual(self.client.get(s.get_panel_url()).status_code, 404)
        self.como(self.asesor)
        self.client.post(s.get_panel_url(), {'accion': 'cotizacion', 'servicios_incluidos': 'Vuelo', 'precio_total': '900',
                                             'vigencia': (HOY() + timedelta(days=3)).isoformat(), 'incluye_seguro': 'False',
                                             'condiciones': 'Ninguna'})
        c = Cotizacion.objects.get()
        self.assertEqual(c.estado, 'pendiente')
        self.como(self.user)
        r = self.client.post(s.get_absolute_url(), {'cotizacion': c.pk, 'accion': 'aceptar'})
        self.assertContains(r, 'Indica si deseas contratar el seguro')  # RS-05.3
        self.client.post(s.get_absolute_url(), {'cotizacion': c.pk, 'accion': 'aceptar', 'contratar_seguro': 'True'})
        c.refresh_from_db()
        s.refresh_from_db()
        self.assertEqual((c.estado, c.contratar_seguro, s.estado), ('aceptada', True, 'aceptada'))
        self.assertIsNotNone(c.respondida_en)
        self.como(self.asesor)
        self.assertContains(self.client.get(s.get_panel_url()), 'Aceptada')

    def test_rs_05_6_rechazar_y_no_responder_vencidas(self):
        s = SolicitudViaje.objects.create(usuario=self.user, destino='X', fecha_salida=HOY(), nombre='J', cedula='0912345678',
                                          email='u@t.com', telefono='099')
        c = Cotizacion.objects.create(solicitud=s, servicios_incluidos='x', precio_total=1, vigencia=HOY(), condiciones='c')
        v = Cotizacion.objects.create(solicitud=s, servicios_incluidos='x', precio_total=1, vigencia=HOY() - timedelta(days=1), condiciones='c')
        self.como(self.user)
        self.client.post(s.get_absolute_url(), {'cotizacion': c.pk, 'accion': 'rechazar'})
        self.client.post(s.get_absolute_url(), {'cotizacion': v.pk, 'accion': 'rechazar'})
        c.refresh_from_db()
        v.refresh_from_db()
        self.assertEqual((c.estado, v.estado), ('rechazada', 'pendiente'))


# ==================================================================== RS-06 / RS-07 / RS-08 Expedientes

class ExpedientesTest(Base):
    def test_rs_06_1_crear_expediente_con_codigo_y_etapa_inicial(self):
        self.como(self.asesor)
        r = self.client.post(reverse('panel_expediente_nuevo'), {
            'usuario': self.user.pk, 'tipo': 'visa', 'nombre': 'Jostin Mora', 'documento_identidad': '0912345678',
            'telefono': '099', 'pais': 'Canadá', 'tipo_visa': 'Turismo', 'pasaporte': 'A1'})
        e = Expediente.objects.get()
        self.assertRedirects(r, e.get_panel_url())
        self.assertEqual((e.codigo, e.etapa, e.asesor), (f'EXP-{e.pk:05d}', 'recoleccion', self.asesor))
        r = self.client.post(reverse('panel_expediente_nuevo'), {'usuario': self.user.pk, 'tipo': 'visa', 'nombre': 'J',
                                                                 'documento_identidad': '1', 'telefono': '1'})
        self.assertIn('pais', r.context['form'].errors)

    def test_rs_06_3_no_avanza_con_documentacion_incompleta_y_rs_06_6_historial(self):
        e = self.expediente(asesor=self.asesor)
        d = DocumentoRequerido.objects.create(expediente=e, nombre='Pasaporte')
        self.como(self.asesor)
        r = self.client.post(e.get_panel_url(), {'accion': 'etapa', 'etapa': 'preparacion'})
        self.assertContains(r, 'Documentación incompleta')
        self.client.post(e.get_panel_url(), {'accion': 'etapa', 'etapa': 'revision'})
        servicios.subir_documento(d, archivo_pdf(), self.user)
        servicios.revisar_documento(d, 'aceptado', '', self.asesor)
        self.client.post(e.get_panel_url(), {'accion': 'etapa', 'etapa': 'preparacion'})
        r = self.client.post(e.get_panel_url(), {'accion': 'etapa', 'etapa': 'presentado'})
        self.assertContains(r, 'Indica la fecha')
        self.client.post(e.get_panel_url(), {'accion': 'etapa', 'etapa': 'presentado', 'fecha_presentacion': HOY().isoformat()})
        e.refresh_from_db()
        self.assertEqual((e.etapa, e.fecha_presentacion), ('presentado', HOY()))
        cambios = list(CambioEtapa.objects.filter(expediente=e).order_by('pk').values_list('anterior', 'nueva', 'usuario'))
        self.assertEqual(cambios, [('recoleccion', 'revision', self.asesor.pk), ('revision', 'preparacion', self.asesor.pk),
                                   ('preparacion', 'presentado', self.asesor.pk)])

    def test_rs_06_4_vuelo_y_boleto_descargable(self):
        e = self.expediente('vuelo', asesor=self.asesor)
        self.como(self.asesor)
        self.client.post(e.get_panel_url(), {'accion': 'vuelo', 'aerolinea': 'Avianca', 'numero_vuelo': 'AV1', 'origen': 'GYE',
                                             'destino': 'MIA', 'salida': '2030-01-01T08:00', 'llegada': '2030-01-01T12:00',
                                             'boleto': archivo_pdf('boleto.pdf')})
        v = VueloContratado.objects.get()
        self.como(self.user)
        self.assertContains(self.client.get(e.get_absolute_url()), 'AV1')
        self.assertEqual(self.client.get(reverse('archivo', args=['boleto', v.pk])).status_code, 200)

    def test_rs_06_7_correo_consulado_y_rs_08_3_cita_consular(self):
        e = self.expediente(asesor=self.asesor)
        self.como(self.asesor)
        self.client.post(e.get_panel_url(), {'accion': 'correo', 'destinatario': 'c@ejemplo.com', 'asunto': 'Citas',
                                             'fecha_envio': HOY().isoformat()})
        self.client.post(e.get_panel_url(), {'accion': 'cita_consular', 'consulado': 'Consulado X', 'direccion': 'Av. 1',
                                             'fecha': '2030-02-01', 'hora': '09:30', 'confirmacion': archivo_pdf('conf.pdf')})
        self.assertEqual(e.correos.count(), 1)
        self.como(self.user)
        r = self.client.get(e.get_absolute_url())
        self.assertContains(r, 'Consulado X')
        self.assertContains(r, 'Descargar confirmación')

    def test_rs_08_4_resultado_separado_de_la_etapa(self):
        e = self.expediente(asesor=self.asesor)
        self.como(self.user)
        self.assertContains(self.client.get(e.get_absolute_url()), 'Resultado no registrado')
        self.como(self.asesor)
        self.client.post(e.get_panel_url(), {'accion': 'resultado', 'resultado': 'aprobada', 'resultado_fecha': HOY().isoformat()})
        e.refresh_from_db()
        self.assertEqual((e.resultado, e.etapa), ('aprobada', 'recoleccion'))

    def test_rs_07_2_formatos_y_tamano(self):
        e = self.expediente(asesor=self.asesor)
        d = DocumentoRequerido.objects.create(expediente=e, nombre='Pasaporte')
        self.como(self.user)
        for nombre, contenido in [('foto.jpg', b'\xff\xd8\xff' + b'0' * 10), ('falso.pdf', b'MZ no soy pdf'),
                                  ('grande.pdf', b'%PDF' + b'0' * (10 * 1024 * 1024 + 1))]:
            r = self.client.post(e.get_absolute_url(), {'documento': d.pk, 'archivo': SimpleUploadedFile(nombre, contenido)})
            self.assertTrue(r.context['form'].errors, nombre)
        self.client.post(e.get_absolute_url(), {'documento': d.pk, 'archivo': SimpleUploadedFile('p.png', png())})
        d.refresh_from_db()
        self.assertEqual(d.estado, 'recibido')

    def test_rs_07_3_y_07_4_correccion_con_historial(self):
        e = self.expediente(asesor=self.asesor)
        d = DocumentoRequerido.objects.create(expediente=e, nombre='Estados de cuenta')
        servicios.subir_documento(d, archivo_pdf('v1.pdf'), self.user)
        self.como(self.asesor)
        r = self.client.post(e.get_panel_url(), {'accion': 'revisar', 'id': d.pk, 'accion_doc': 'correccion', 'comentario': ''})
        self.assertContains(r, 'Explica qué debe corregirse')
        self.client.post(e.get_panel_url(), {'accion': 'revisar', 'id': d.pk, 'accion_doc': 'correccion', 'comentario': 'Falta sello'})
        d.refresh_from_db()
        self.assertEqual(d.estado, 'correccion')
        self.assertEqual(d.revisiones.first().revisor, self.asesor)
        self.como(self.user)
        self.assertContains(self.client.get(e.get_absolute_url()), 'Falta sello')
        self.client.post(e.get_absolute_url(), {'documento': d.pk, 'archivo': archivo_pdf('v2.pdf')})
        d.refresh_from_db()
        self.assertEqual((d.estado, d.archivos.count(), d.revisiones.count()), ('recibido', 2, 1))

    def test_rs_07_5_documentos_pendientes_del_asesor(self):
        e = self.expediente(asesor=self.asesor)
        DocumentoRequerido.objects.create(expediente=e, nombre='Foto carnet')
        DocumentoRequerido.objects.create(expediente=self.expediente(asesor=self.asesor2), nombre='Doc ajeno')
        self.como(self.asesor)
        r = self.client.get(reverse('panel_documentos'))
        self.assertContains(r, 'Foto carnet')
        self.assertNotContains(r, 'Doc ajeno')

    def test_rs_08_1_usuario_ve_documentacion_incompleta(self):
        e = self.expediente(asesor=self.asesor)
        DocumentoRequerido.objects.create(expediente=e, nombre='Pasaporte')
        self.como(self.user)
        r = self.client.get(e.get_absolute_url())
        self.assertContains(r, 'Documentación incompleta')
        self.assertContains(r, 'Pendiente de entrega')


# ==================================================================== RS-09 Citas

class CitasTest(Base):
    def test_rs_09_1_modalidad_y_rs_09_2_mis_citas(self):
        self.como(self.asesor)
        base = {'usuario': self.user.pk, 'asesor': self.asesor.pk, 'motivo': 'Entrevista',
                'fecha': (HOY() + timedelta(days=2)).isoformat(), 'hora': '10:00'}
        r = self.client.post(reverse('panel_cita_nueva'), {**base, 'modalidad': 'virtual'})
        self.assertIn('enlace', r.context['form'].errors)
        self.client.post(reverse('panel_cita_nueva'), {**base, 'modalidad': 'virtual', 'enlace': 'https://meet.example.com/x'})
        self.client.post(reverse('panel_cita_nueva'), {**base, 'modalidad': 'presencial', 'direccion': 'Oficina',
                                                       'enlace': 'https://no-debe-guardarse.com'})
        presencial = Cita.objects.get(modalidad='presencial')
        self.assertEqual(presencial.enlace, '')
        self.como(self.user)
        r = self.client.get(reverse('citas'))
        self.assertContains(r, 'https://meet.example.com/x')
        self.assertContains(r, 'Oficina')
        self.como(self.otro)
        self.assertContains(self.client.get(reverse('citas')), 'No tienes citas registradas')

    def test_rs_09_3_agenda_por_fecha_del_asesor(self):
        Cita.objects.create(usuario=self.user, asesor=self.asesor, motivo='Mía', modalidad='presencial', fecha=HOY(),
                            hora=time(9), direccion='x')
        Cita.objects.create(usuario=self.user, asesor=self.asesor2, motivo='De otro', modalidad='presencial', fecha=HOY(),
                            hora=time(9), direccion='x')
        self.como(self.asesor)
        r = self.client.get(reverse('panel_agenda'))
        self.assertContains(r, 'Mía')
        self.assertNotContains(r, 'De otro')
        r = self.client.get(reverse('panel_agenda') + f'?fecha={(HOY() + timedelta(days=1)).isoformat()}')
        self.assertContains(r, 'No hay citas para esta fecha')


# ==================================================================== RS-10 Pagos

class PagosTest(Base):
    def setUp(self):
        super().setUp()
        self.e = self.expediente('paquete', asesor=self.asesor, paquete_nombre='P', destino='D', fecha_salida=HOY(),
                                 fecha_regreso=HOY(), precio_total=Decimal('1000'))

    def enviar(self, monto='400'):
        return self.client.post(reverse('pagos'), {'expediente': self.e.pk, 'monto': monto, 'fecha_pago': HOY().isoformat(),
                                                   'medio': 'transferencia', 'archivo': archivo_pdf('c.pdf')})

    def test_rs_10_2_a_10_4_flujo_de_pago(self):
        self.como(self.user)
        self.enviar()
        c = Comprobante.objects.get()
        self.assertEqual(c.estado, 'pendiente')
        self.assertEqual(self.e.saldo, Decimal('1000'))  # pendiente no se descuenta
        self.assertRegex(c.numero, r'^CP-\d{8}-[0-9A-F]{6}$')  # lo asigna el sistema
        self.como(self.asesor)
        self.client.post(self.e.get_panel_url(), {'accion': 'confirmar', 'id': c.pk})
        self.assertEqual(self.e.saldo, Decimal('600'))
        self.como(self.user)
        self.enviar('100')
        c2 = Comprobante.objects.exclude(pk=c.pk).get()
        self.como(self.asesor)
        r = self.client.post(self.e.get_panel_url(), {'accion': 'rechazar', 'id': c2.pk, 'motivo': ''})
        self.assertContains(r, 'Explica el motivo')
        self.client.post(self.e.get_panel_url(), {'accion': 'rechazar', 'id': c2.pk, 'motivo': 'Ilegible'})
        self.assertEqual(self.e.saldo, Decimal('600'))
        self.como(self.user)
        r = self.client.get(reverse('pagos'))
        self.assertContains(r, 'Ilegible')
        self.assertContains(r, '600')

    def test_rnf_07_confirmar_dos_veces_un_solo_abono(self):
        c = Comprobante.objects.create(expediente=self.e, monto=300, fecha_pago=HOY(), numero='X', medio='deposito',
                                       archivo=ContentFile(pdf('x'), name='x.pdf'))
        self.assertTrue(servicios.confirmar_comprobante(c.pk, self.asesor))
        self.assertFalse(servicios.confirmar_comprobante(c.pk, self.asesor))
        self.assertEqual(Abono.objects.count(), 1)
        self.assertEqual(self.e.saldo, Decimal('700'))


@override_settings(MEDIA_ROOT=MEDIA)
class ConcurrenciaTest(TransactionTestCase):
    """RNF-07: dos confirmaciones simultáneas generan un solo abono."""

    def test_confirmaciones_simultaneas(self):
        u = crear('c@t.com')
        e = Expediente.objects.create(usuario=u, tipo='vuelo', nombre='x', telefono='1', documento_identidad='1',
                                      precio_total=500)
        c = Comprobante.objects.create(expediente=e, monto=200, fecha_pago=HOY(), numero='Z', medio='deposito',
                                       archivo=ContentFile(pdf('z'), name='z.pdf'))
        resultados, barrera = [], threading.Barrier(2)

        def confirmar():
            from django.db import connection
            barrera.wait()
            try:
                resultados.append(servicios.confirmar_comprobante(c.pk, u))
            except Exception as exc:  # sqlite puede rechazar la escritura simultánea: eso tampoco duplica
                resultados.append(type(exc).__name__)
            finally:
                connection.close()

        hilos = [threading.Thread(target=confirmar) for _ in range(2)]
        [h.start() for h in hilos]
        [h.join() for h in hilos]
        self.assertEqual(Abono.objects.filter(comprobante=c).count(), 1)
        self.assertEqual(Expediente.objects.get(pk=e.pk).saldo, Decimal('300'))


class DespliegueTest(TestCase):
    """Entrega de archivos desde Supabase Storage y límite de subida de Vercel."""

    def almacen(self):
        from core.almacen import AlmacenSupabase
        return AlmacenSupabase(url='https://x.supabase.co', clave='k', bucket='b')

    def test_enlace_firmado_incluye_nombre_de_descarga(self):
        from unittest import mock
        respuesta = mock.MagicMock()
        respuesta.__enter__.return_value.read.return_value = b'{"signedURL": "/object/sign/b/a%20b.pdf?token=t"}'
        with mock.patch('core.almacen.urlopen', return_value=respuesta) as abrir:
            enlace = self.almacen().enlace_firmado('a b.pdf', descarga='Mi boleto.pdf')
        peticion = abrir.call_args.args[0]
        self.assertEqual(peticion.full_url, 'https://x.supabase.co/storage/v1/object/sign/b/a%20b.pdf')
        self.assertEqual(enlace, 'https://x.supabase.co/storage/v1/object/sign/b/a%20b.pdf?token=t&download=Mi%20boleto.pdf')

    def test_servir_redirige_al_enlace_firmado(self):
        from unittest import mock
        from django.test import RequestFactory
        from core.archivos import servir
        f = mock.MagicMock(name='f')
        f.name = 'privado/a.pdf'
        f.storage.enlace_firmado.return_value = 'https://x.supabase.co/firmado'
        r = servir(RequestFactory().get('/'), f, nombre='a.pdf')
        self.assertEqual((r.status_code, r['Location']), (302, 'https://x.supabase.co/firmado'))
        self.assertIn('no-store', r['Cache-Control'])

    def test_limite_de_subida_reduce_el_maximo(self):
        from core.validadores import ArchivoField
        with self.settings(LIMITE_SUBIDA_MB=4):
            campo = ArchivoField(max_mb=10)
        self.assertEqual(campo.max_mb, 4)
        self.assertIn('4 MB', campo.help_text)
