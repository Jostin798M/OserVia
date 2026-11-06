# OserVia

**Sistema de atención y seguimiento para OSERTRAVEL EC**, agencia de viajes y asesoría de visas de Guayaquil.

Proyecto de Ingeniería de Software I (ESPOL · FIEC · 2026 2S) del equipo **DeepMinders — Team 3**.

OserVia reúne en una aplicación web lo que la agencia hoy lleva en carpetas físicas, correo y herramientas
separadas: la oferta pública, las cotizaciones, los expedientes de cada servicio, los documentos, las citas y los
pagos. El detalle de los requerimientos y su estado está en [`REQUERIMIENTOS.md`](REQUERIMIENTOS.md).

## Qué incluye

- **Sitio público** (sin iniciar sesión): ofertas de vuelos y de hospedaje con buscador, paquetes, promociones, asesoría de
  visas, Nosotros, preguntas frecuentes, formulario de consulta, asistente virtual, botón de WhatsApp y video
  tutorial.
- **Mi cuenta** (clientes): cotizaciones que se aceptan o rechazan, expedientes con etapa y documentos, entrega
  de archivos, citas, pagos y saldos.
- **Panel** (administrador y asesores): consultas, cotizaciones, expedientes, revisión de documentos, agenda,
  confirmación de pagos, usuarios, personal y contenido público. Cada asesor ve solo lo que tiene asignado.
- Modo claro y oscuro, diseño adaptable a celular y un solo inicio de sesión para todos los roles.

## Requisitos

- Python 3.12 o superior
- Git

## Instalación

```bash
git clone <url-del-repositorio> oservia
cd oservia

python -m venv .venv
source .venv/bin/activate          # En Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py cargar_demo       # contenido, cuentas y casos de demostración
python manage.py runserver
```

Abre http://127.0.0.1:8000/

## Cuentas de demostración

`cargar_demo` crea estas cuentas **solo para pruebas locales**:

| Rol | Correo | Contraseña |
|---|---|---|
| Cliente con casos de ejemplo | `josmocobos@espol.edu.ec` | `test123` |
| Administrador | `josmocobos@admin.com` | `admin123` |
| Asesora | `asesor@admin.com` | `asesor123` |
| Asesor | `asesor2@admin.com` | `asesor123` |

Todas entran por **/entrar/**: los clientes llegan a «Mi cuenta» y el personal al panel.
Para volver a empezar: `python manage.py cargar_demo --reiniciar`.

## Pruebas

```bash
python manage.py test core
```

Cada prueba indica en su nombre el requerimiento que verifica (por ejemplo `test_rs_07_2_formatos_y_tamano`).

## Estructura

```
OserVia/                 Configuración de Django (settings, urls)
core/
  models.py              Modelo de datos
  forms.py               Formularios y validaciones
  servicios.py           Reglas de negocio (asignaciones, etapas, revisión, pagos)
  permisos.py            Roles y control de acceso
  public_views.py        Sitio público
  views.py               Cuenta del cliente e inicio de sesión
  panel_views.py         Panel del personal
  templates/             Plantillas HTML
  static/core/           CSS, JavaScript e imágenes (logos)
  management/commands/   Comando cargar_demo
  demo/                  Video tutorial incluido en la demostración
  tests.py               Pruebas de aceptación por requerimiento
REQUERIMIENTOS.md        Requerimientos del sistema y su estado
```

## Publicación (Vercel y Supabase)

Vercel está conectado a este repositorio: cada commit en `main` publica el sitio. Supabase aloja la base de
datos y los archivos, y las variables necesarias están en `.env.example`.

- **Límite de subida:** Vercel acepta hasta 4,5 MB por petición, así que los formularios permiten hasta 4 MB.
- **Migraciones:** se ejecutan desde tu equipo con `DATABASE_URL` en el puerto 5432 de Supabase. Vercel no las aplica.
- **Tablas nuevas:** activa RLS en cada tabla nueva de `public` para que no quede expuesta por la API de Supabase.
- **Correo:** sin `EMAIL_HOST`, los correos de recuperación de contraseña no se envían.

## Publicar en otro servidor

La configuración de producción se activa con variables de entorno:

```bash
export DJANGO_PRODUCCION=1
export DJANGO_SECRET_KEY='<una-clave-larga-y-aleatoria>'
export DJANGO_ALLOWED_HOSTS='tudominio.com'
```

Con `DJANGO_PRODUCCION=1` se exige HTTPS (redirección, cookies seguras y HSTS). Además:

- No ejecutes `cargar_demo` en producción y crea un administrador con `python manage.py createsuperuser`.
- Configura un servidor de correo (SMTP) para que lleguen los enlaces de recuperación de contraseña.
- Usa una base de datos como PostgreSQL y un almacenamiento persistente para `media/`.
- Revisa con la agencia y un profesional legal la Política de privacidad y los Términos y condiciones, que
  están marcados como borrador.

## Equipo

- Anthony Walter Paredes Vega
- Kristhel Sharareh Carrión Maldonado
- Jostin Emilio Mora Cobos
- Xavier Andrés Murillo Panchana

Docente: Ph. D. Mónica Katiuska Villavicencio Cabezas.
