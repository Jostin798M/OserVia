# OserVia — Requerimientos del sistema

**Sistema de atención y seguimiento para OSERTRAVEL EC**

Documento único que reúne la información de los documentos del proyecto:

| Documento original | Qué aportaba | Dónde está aquí |
|---|---|---|
| `Especificacion_Proyecto_OSERTRAVEL_EC.pdf` | Cliente, contexto, alcance, módulos, reglas del negocio y criterios de aceptación | Secciones 1 a 5 y 9 |
| `OserVia_Requerimientos_Overleaf.pdf` | Requerimientos funcionales y no funcionales (versión final) | Secciones 6 a 8 |
| `Nivel.docx` | Borrador anterior de los mismos requerimientos | Sección 10 (diferencias) |
| `01bMidtermProjectSpec1.2_es.pdf` | Consigna y rúbrica del proyecto de medio término | Sección 11 |
| `830-1998.pdf` (IEEE 830-1998) y `29148-2018` (ISO/IEC/IEEE 29148:2018) | Normas de referencia para escribir requerimientos | Sección 12 |

Las columnas **Estado** y **Dónde** indican cómo lo cumple la aplicación web actual (actualizado el
3 de noviembre de 2026). Cada requerimiento verificable tiene una prueba automática en `core/tests.py`
cuyo nombre incluye su identificador (por ejemplo `test_rs_07_2_formatos_y_tamano`).

---

## 1. Identificación del proyecto

| Dato | Valor |
|---|---|
| Institución | ESPOL — Facultad de Ingeniería en Electricidad y Computación |
| Asignatura | Ingeniería de Software I — período 2026 2S |
| Docente | Ph. D. Mónica Katiuska Villavicencio Cabezas |
| Equipo | DeepMinders — Team 3 (T3) |
| Cliente | OSERTRAVEL EC (persona natural), Guayaquil |
| Sponsor y representante | Mónica Elizabeth Tomalá Tomalá, propietaria |
| Contacto de trabajo | infoclientes@osertravelec.com · +593 99 026 2569 |
| Oficina | Calles Tungurahua y Hurtado, referencia 1000A, centro de Guayaquil |

| Integrante | Responsabilidad en la especificación |
|---|---|
| Anthony Walter Paredes Vega | Contacto con la Sponsor, levantamiento de información y coordinación de la validación |
| Kristhel Sharareh Carrión Maldonado | Caracterización del cliente, procesos actuales y resumen ejecutivo |
| Jostin Emilio Mora Cobos | Alcance, módulos, componentes Web y Mobile App y modelo de características |
| Xavier Andrés Murillo Panchana | Objetivos, stakeholders, reglas y criterios de aceptación |

> Los datos de identidad personales de la Sponsor (cédula y correo personal) que constaban en la
> especificación original no se copian aquí.

## 2. Contexto y problema

OSERTRAVEL EC inició su actividad en octubre de 2024 y abrió su oficina el 24 de febrero de 2025. Se
dedica a la asesoría de visas (sobre todo Schengen y Estados Unidos; también Canadá, Reino Unido,
Tailandia y trámites del consulado español), a la boletería aérea, a los paquetes turísticos (por ejemplo
Panamá Ciudad, Panamá Playa, Panamá y Colombia) y a los seguros de viaje. Atiende sobre todo a personas
que viajan o tramitan su visa por primera vez. La Sponsor estima unas 10 consultas diarias de visas,
más de 20 de viajes y de 30 a 50 clientes al mes en temporada baja.

**Problema.** El seguimiento depende de carpetas físicas, de la revisión manual del correo, de Google
Calendar para la agenda y de Contífico para pagos. Para conocer el estado de un trámite hay que
reconstruirlo revisando varias fuentes; una respuesta consular puede pasar inadvertida y las consultas
repetitivas consumen el tiempo de la asesora.

**Solución.** Un expediente único por servicio, con responsable, estado, documentos, citas, pagos e
historial, consultable por el personal y por el viajero desde su cuenta, más un sitio público con la
oferta de la agencia y un formulario de consulta.

## 3. Alcance y límites

**Incluye:** presentación de servicios y promociones, recepción de consultas y cotizaciones, registro de
servicios contratados (expedientes), entrega y revisión de documentos, seguimiento de asesorías de visa,
citas y control de pagos.

**No incluye:**
- Obtener citas consulares, enviar formularios a plataformas gubernamentales ni decidir sobre visas.
- Conectarse con aerolíneas o mayoristas, ni comprar o emitir boletos o pólizas (se registran en el expediente).
- Leer el correo automáticamente ni sincronizar con Contífico, Google Calendar o WhatsApp.
- Cobro en línea con tarjeta (ampliación condicionada a presupuesto y proveedor).
- Comisiones por referidos (marcado como *Won't* en la primera versión).

El sistema mantiene por separado el estado de atención, el de los documentos y el de los pagos, y
distingue la etapa de la asesoría del resultado consular.

## 4. Personas que usarán el sistema

| Rol | Qué hace | En OserVia |
|---|---|---|
| Administrador | Administra cuentas, contenido público y asignación de casos | Panel completo, incluido «Usuarios», «Personal» y «Contenido público» |
| Asesor | Atiende las solicitudes y expedientes que tiene asignados | Panel limitado a sus casos |
| Usuario | Consulta la oferta, solicita atención y sigue sus servicios | Sitio público y «Mi cuenta» |

## 5. Módulos propuestos

| Módulo | Descripción | En OserVia |
|---|---|---|
| M01 Información de servicios y promociones | Publicación administrable de servicios, ofertas y preguntas frecuentes | Sitio público + Panel → Contenido |
| M02 Consultas y cotizaciones | Solicitudes con su oferta de origen, cotizaciones y respuesta del pasajero | Cotizaciones (cliente y panel) |
| M03 Expedientes, documentos y bitácora | Expediente por servicio, estados de documentos, correos al consulado | Expedientes y Documentos |
| M04 Agenda, citas y actividades | Citas virtuales o presenciales y agenda del asesor | Mis citas y Panel → Agenda |
| M05 Honorarios, abonos y comisiones | Precio, comprobantes, abonos y saldo | Pagos (cliente y panel) |
| M06 Usuarios, permisos y reportes | Roles, cuentas e historial de cambios | Panel → Usuarios / Personal, resumen |

---

## 6. Requerimientos funcionales

Prioridad MoSCoW: **Must** (indispensable), **Should** (importante), **Could** (complementario),
**Won't** (fuera de la primera versión). Estado: **Cumple** · **Condicionado** (cumple, pero depende de algo externo) ·
**Fuera de alcance**.

### 6.1 Cuentas de acceso

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-01 | Must | El usuario puede crear una cuenta e iniciar sesión para consultar sus servicios contratados. | Cumple | `/registro/`, `/entrar/` |
| RS-01.1 | Must | Crear cuenta con nombre completo, correo, teléfono y contraseña, todos obligatorios. Si falta un dato o el correo ya existe, indica el problema y no crea la cuenta; si se completa, muestra una confirmación. | Cumple | `/registro/` |
| RS-01.2 | Must | Usuario, asesor y administrador inician sesión con correo y contraseña. Si los datos son correctos y la cuenta está habilitada, ingresa; si no, se impide el acceso con un mensaje. | Cumple | `/entrar/` (un solo acceso para todos los roles) |
| RS-01.3 | Must | Cerrar sesión; después hay que volver a iniciarla para ver información privada. | Cumple | Botón «Salir» |
| RS-01.4 | Should | Solicitar cambio de contraseña con un enlace enviado al correo, de un solo uso. | Condicionado | `/recuperar/`. En desarrollo el correo se muestra en la terminal; en producción requiere configurar un servidor de correo (SMTP). |
| RS-01.5 | Must | El administrador crea cuentas de asesor y habilita o deshabilita cuentas; una cuenta deshabilitada no inicia sesión pero conserva sus registros. «Crear cuenta» solo crea usuarios. | Cumple | Panel → Personal / Usuarios |

### 6.2 Permisos y asignaciones

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-02 | Must | El administrador consulta todos los expedientes, el asesor los asignados y el usuario solo los propios. | Cumple | Panel y «Mi cuenta» |
| RS-02.1 | Must | El administrador consulta los expedientes de todos los usuarios. | Cumple | Panel → Expedientes |
| RS-02.2 | Must | El asesor consulta y actualiza solo los expedientes asignados; no puede ver ni modificar los demás. | Cumple | Cualquier otro devuelve 404 |
| RS-02.3 | Must | El usuario consulta solo sus propias solicitudes, cotizaciones, expedientes, documentos, citas y pagos. | Cumple | «Mi cuenta» |
| RS-02.4 | Must | El administrador asigna o cambia el asesor de una solicitud o expediente; se guarda quién lo hizo y cuándo. | Cumple | Panel → detalle → «Asesor responsable» + historial |

### 6.3 Información de la agencia

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-03 | Must | El usuario conoce los servicios e información de la agencia y el administrador la mantiene actualizada. | Cumple | Sitio público + Panel → Contenido |
| RS-03.1 | Must | El administrador crea, edita, publica y retira servicios, promociones, ofertas de vuelos, paquetes y preguntas frecuentes. | Cumple | Panel → Contenido público |
| RS-03.2 | Must | Sin iniciar sesión se consultan servicios, promociones, ofertas y preguntas frecuentes. Cada oferta muestra descripción, precio, condiciones y servicios incluidos; las promociones muestran fecha de inicio y fin. | Cumple | `/`, `/vuelos/`, `/paquetes/`, `/promociones/`, `/ofertas/<código>/` |
| RS-03.3 | Should | Sección «Nosotros» con historia, misión, visión y ubicación, sin iniciar sesión. | Cumple | `/nosotros/` (misión y visión son borradores a validar con la Sponsor) |
| RS-03.4 | Could | Sección «¿Por qué viajar con nosotros?» con beneficios (título y descripción). | Cumple | Página principal |
| RS-03.5 | Should | Al final de las páginas públicas: dirección, teléfono, correo y horarios, y enlaces a Inicio, Vuelos, Paquetes turísticos, Nosotros y Contacto. | Cumple | Pie de página público (el horario es un dato a confirmar) |

### 6.4 Ayuda y contacto

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-04 | Must | El usuario obtiene orientación y solicita información a la agencia. | Cumple | Contacto, asistente, WhatsApp |
| RS-04.1 | Could | Asistente virtual sin iniciar sesión sobre servicios, cotizaciones y horarios; si no sabe, lo indica y ofrece el WhatsApp. | Cumple | Botón flotante de chat |
| RS-04.2 | Could | Publicaciones seleccionadas de redes sociales en la página principal; se pueden ver y reproducir videos sin iniciar sesión. | Cumple | «En nuestras redes» (se cargan desde Panel → Contenido) |
| RS-04.3 | Could | Video sobre cómo consultar servicios, cotizar y contactar; se puede reproducir, pausar, adelantar, retroceder, ajustar volumen y cerrar. | Cumple | «Cómo usar OserVia» en la página principal |
| RS-04.4 | Should | Botón de WhatsApp en las páginas públicas, con el número oficial. | Cumple | Botón flotante verde |
| RS-04.5 | Must | Formulario público con nombre, motivo y teléfono (obligatorios); guarda fecha y hora y confirma, o explica el error. | Cumple | Página principal y `/contacto/` |
| RS-04.6 | Must | El administrador ve las solicitudes de información y las asigna; el asesor ve las suyas, con nombre, teléfono, motivo y fecha y hora. | Cumple | Panel → Consultas |

### 6.5 Cotizaciones de viajes

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-05 | Must | El usuario solicita cotizaciones de vuelos o paquetes y el asesor registra la propuesta y la respuesta. | Cumple | Cotizaciones |
| RS-05.1 | Must | Vuelos: origen, destino, salida, pasajeros e ida o ida y vuelta (con regreso). Paquetes: paquete o destino, fechas y pasajeros. En ambos: nombre, correo, cédula y teléfono. Indica el campo faltante, confirma al guardar, exige sesión y relaciona la solicitud con la cuenta. | Cumple | `/mi-cuenta/cotizar/` |
| RS-05.2 | Must | Pregunta si desea incluir seguro de viaje y guarda la respuesta. | Cumple | Formulario de cotización |
| RS-05.3 | Must | Al aceptar una cotización muestra si incluye seguro; si no, pregunta si desea contratarlo y guarda la respuesta. | Cumple | Detalle de la solicitud |
| RS-05.4 | Must | Al solicitar desde una oferta guarda su nombre, código y promoción; sin oferta indica «Sin oferta seleccionada». | Cumple | Botón «Solicitar cotización» de cada oferta |
| RS-05.5 | Must | El asesor registra la cotización: servicios incluidos, precio total, vigencia y condiciones; el usuario la ve en su cuenta. | Cumple | Panel → Cotizaciones → detalle |
| RS-05.6 | Must | Cada cotización nueva queda «Pendiente de respuesta»; el usuario la acepta o rechaza; se guarda fecha y hora y el asesor la consulta. | Cumple | Detalle de la solicitud (cliente y panel) |
| RS-05.7 | Must | Buscar ofertas de vuelos sin sesión por destino, fecha de salida, precio máximo por persona y duración máxima; todos los filtros se combinan; si no hay resultados lo indica. | Cumple | `/vuelos/` |
| RS-05.8 | Must | Consultar y buscar ofertas de hospedaje sin sesión por destino, fecha de entrada y precio máximo por persona, y solicitarlas con el mismo flujo de cotización y expediente que vuelos y paquetes. | Cumple | Sitio público → Hospedaje; solicitud del cliente. |
| RS-05.9 | Must | Buscar paquetes turísticos sin sesión por destino, fecha de salida, precio máximo por persona y duración máxima, con filtros combinables. | Cumple | Sitio público → Paquetes. |
| RS-05.10 | Should | Filtrar vuelos por origen, con la ciudad más cercana sugerida por la ubicación si el usuario da permiso, y autocompletar lugares en vuelos, paquetes y hospedaje. | Cumple | Buscadores del sitio público. |

### 6.6 Seguimiento de servicios

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-06 | Must | El asesor registra los servicios contratados y consulta su información y documentos. | Cumple | Panel → Expedientes |
| RS-06.1 | Must | Expediente por servicio relacionado con la cuenta: nombre, teléfono, documento, tipo de servicio, asesor y código único; en visas, país y tipo de visa. | Cumple | Panel → Expedientes → Nuevo (código `EXP-00000`) |
| RS-06.2 | Must | Etapas de visa: Recolección de documentos, Revisión de documentos, Preparación para la cita consular y Usuario presentado al consulado (pide la fecha). Inicia en Recolección. | Cumple | Detalle del expediente → Etapa |
| RS-06.3 | Must | Muestra «Documentación completa» o «incompleta» con los pendientes, y no permite avanzar a Preparación mientras esté incompleta. | Cumple | Expediente (cliente y panel) |
| RS-06.4 | Must | Vuelo: aerolínea, número, origen, destino, fechas y horas, y boleto; el usuario lo consulta y descarga. | Cumple | Expediente de boletería |
| RS-06.5 | Must | Paquete: nombre, destino, fechas, servicios, itinerario y documentos del viaje; el usuario los consulta y descarga. | Cumple | Expediente de paquete |
| RS-06.6 | Must | Cada cambio de etapa guarda la anterior, la nueva, el asesor y la fecha y hora en «Historial de cambios». | Cumple | Expediente → Historial de cambios |
| RS-06.7 | Must | Registrar correos enviados al consulado: expediente, destinatario, asunto y fecha de envío. | Cumple | Expediente → Correos al consulado (además: respuesta y próxima revisión) |
| RS-06.8 | Could | Registrar cancelaciones y cambios de horario de la aerolínea y mostrarlos al usuario; si se reprograma, la nueva fecha y hora. | Cumple | Avisos en «Mi cuenta» y en el expediente |

### 6.7 Documentos

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-07 | Must | El usuario entrega documentos, consulta su revisión y envía correcciones. | Cumple | Expediente → Documentos |
| RS-07.1 | Must | El asesor registra los documentos que debe entregar el usuario; quedan «Pendiente de entrega». | Cumple | Panel → expediente → «Solicitar un documento» |
| RS-07.2 | Must | El usuario elige el documento y adjunta un PDF o PNG de hasta 10 MB; queda «Recibido» o se explica el problema. | Cumple | Se valida extensión, tamaño y contenido real del archivo |
| RS-07.3 | Must | El asesor marca «En revisión» y luego «Corrección requerida» (con explicación obligatoria) o «Aceptado»; se guarda asesor, fecha y hora. | Cumple | Panel → expediente → revisión |
| RS-07.4 | Must | Ante «Corrección requerida» el usuario envía otro archivo; queda «Recibido» y se conservan los anteriores y los comentarios. | Cumple | Historial de archivos y revisiones |
| RS-07.5 | Must | El asesor consulta los documentos pendientes o con corrección de sus expedientes, con usuario, código, documento y explicación. | Cumple | Panel → Documentos |

### 6.8 Trámites de visa

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-08 | Must | El usuario consulta la etapa, los pendientes, la cita consular y el resultado registrado. | Cumple | Expediente de visa |
| RS-08.1 | Must | Para cada trámite: etapa, última actualización, documentación completa o incompleta, pendientes y comentarios al usuario. | Cumple | Expediente de visa |
| RS-08.2 | Must | El asesor registra nombre, pasaporte, correo, teléfono, país y tipo de visa; los datos ya guardados en la cuenta se proponen para revisarlos. | Cumple | Nuevo expediente (se completan al elegir la cuenta) |
| RS-08.3 | Must | Cita consular confirmada: consulado, dirección, fecha, hora y confirmación adjunta; el usuario la consulta y descarga. | Cumple | Expediente → Cita consular |
| RS-08.4 | Must | Resultado consular con fecha; mientras no exista muestra «Resultado no registrado». | Cumple | Separado de la etapa de la asesoría |

### 6.9 Citas con la agencia

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-09 | Must | El asesor programa citas y el usuario las consulta en «Mis citas». | Cumple | Panel → Agenda / «Mis citas» |
| RS-09.1 | Must | Motivo, modalidad, fecha, hora y asesor; virtual pide enlace, presencial pide dirección y no tiene enlace. | Cumple | Panel → Agenda → Nueva cita (también reprogramar) |
| RS-09.2 | Must | «Mis citas» muestra motivo, asesor, modalidad, fecha y hora; enlace o dirección; si no hay, lo indica. | Cumple | `/mi-cuenta/citas/` |
| RS-09.3 | Must | El asesor consulta las citas de una fecha con usuario, motivo, modalidad, hora y enlace o dirección; si no hay, lo indica. | Cumple | Panel → Agenda |

### 6.10 Pagos y saldos

| ID | Prioridad | Requerimiento | Estado | Dónde |
|---|---|---|---|---|
| RU-10 | Must | El asesor registra valores y pagos; el usuario consulta lo pagado y el total. | Cumple | Pagos |
| RS-10.1 | Must | Precio total del servicio en el expediente, base del saldo. | Cumple | Expediente → Seguimiento |
| RS-10.2 | Must | El usuario elige un servicio y envía imagen o PDF del comprobante con monto, fecha, número y medio (transferencia o depósito); queda «Pendiente de revisión». | Cumple | `/mi-cuenta/pagos/` |
| RS-10.3 | Must | El asesor confirma (se registra el abono) o rechaza con motivo visible al usuario; un comprobante no genera más de un abono. | Cumple | Expediente → Pagos |
| RS-10.4 | Must | Saldo = precio total − abonos confirmados (los pendientes o rechazados no se descuentan); lo ven usuario, asesor y administrador. | Cumple | Pagos (cliente y panel) |

### 6.11 Comisiones por referidos

| ID | Prioridad | Requerimiento | Estado |
|---|---|---|---|
| RU-11 | Won't | Registrar quién recomendó a un usuario y calcular su comisión. | Fuera de alcance. No forma parte de la primera versión, como define el documento |

## 7. Requerimientos no funcionales

| ID | Clasificación (Sommerville) | Requerimiento | Criterio de validación | Estado |
|---|---|---|---|---|
| RNF-01 | Producto: usabilidad | Adaptarse a computadora y celular sin elementos superpuestos ni cortados y sin desplazamiento lateral. | Consultar servicios, cotizar, enviar documentos y consultar pagos en computadora y celular; registrar tamaños y navegadores. | Cumple. Verificado en 1366, 1024 y 390 px (Chromium), modo claro y oscuro |
| RNF-02 | Producto: usabilidad | 4 de 5 personas nuevas envían una cotización y consultan un saldo sin ayuda, en máximo 5 minutos cada actividad. | Prueba con cinco participantes con cuentas preparadas. | Condicionado. Debe realizarla el equipo con usuarios reales |
| RNF-03 | Producto: eficiencia | Con 5 personas simultáneas, servicios, expedientes y saldos responden en ≤ 3 s en al menos 9 de cada 10 consultas. | 10 consultas de cada tipo con 5 usuarios simultáneos. | Cumple. 30/30 consultas por debajo de 0,2 s en el equipo de desarrollo |
| RNF-04 | Producto: seguridad | La aplicación publicada usa HTTPS. | Páginas, formularios y archivos por HTTPS sin advertencias. | Condicionado. Configurado (`DJANGO_PRODUCCION=1`); requiere un servidor con certificado |
| RNF-05 | Producto: seguridad | Contraseñas guardadas de forma protegida. | Revisar cómo se guarda la contraseña de una cuenta de prueba. | Cumple. PBKDF2-SHA256 |
| RNF-06 | Producto: seguridad | Impedir ver o modificar expedientes, documentos y pagos sin autorización, aun cambiando la URL o usando el enlace de un archivo. | Intentarlo como otro usuario, como asesor no asignado y sin sesión. | Cumple. Los archivos se sirven solo tras verificar permisos |
| RNF-07 | Producto: fiabilidad | Un solo abono por comprobante aunque se confirme varias veces o a la vez. | Confirmar varias veces y dos veces simultáneamente. | Cumple. Probado con dos confirmaciones simultáneas |

**Medidas de seguridad adicionales implementadas:** bloqueo de 15 minutos tras 5 intentos fallidos de
inicio de sesión; la sesión del personal expira a las 2 horas; el `/admin/` de Django está desactivado;
los archivos subidos se validan por su contenido real.

## 8. Reglas del negocio

1. La primera entrevista informativa de visas es gratuita y dura unos 30 minutos.
2. La asesoría no garantiza la visa: el expediente distingue la prestación de la agencia de la resolución consular.
3. El contrato registra las condiciones explicadas; el sistema conserva su referencia, sin sustituir la firma.
4. Los honorarios de asesoría de visas no se reembolsan por una decisión desfavorable; para un segundo intento Schengen puede ofrecerse un descuento.
5. En visas del espacio europeo se pide un abono inicial del 50 % y el segundo abono suele llegar en 12 a 15 días; no se aplica a otros servicios.
6. En asesoría estadounidense hay un único pago de honorarios; la tasa consular se paga aparte.
7. En paquetes puede haber reserva y abonos mensuales si hay anticipación (por ejemplo seis meses); para el mes siguiente se paga completo. La agencia no da crédito.
8. Las condiciones y diferencias de precio por medio de pago constan en la cotización.
9. La comisión por referido se genera al terminar el servicio del pasajero referido, una sola vez (fuera de la primera versión).

## 9. Criterios de aceptación

| Código | Resultado observable | Objetivo | Estado |
|---|---|---|---|
| CA-01 | Publicar un servicio y una promoción, enviar una consulta desde ella y conservar la referencia de origen. | OE-1 | Cumple |
| CA-02 | Abrir un expediente y consultar responsable, estado, documentos y próxima acción sin acudir a una carpeta física. | OE-2 | Cumple |
| CA-03 | Registrar una gestión por correo, la revisión del buzón y una respuesta, y mostrar la actividad posterior. | OE-2 | Cumple |
| CA-04 | Solicitar, confirmar y reprogramar una cita sin confundir la solicitud con una fecha confirmada. | OE-3 | Cumple. Las citas se programan y reprograman desde el panel; las solicitudes llegan por Consultas |
| CA-05 | Registrar dos abonos y comprobar el saldo; un comprobante no revisado queda pendiente. | OE-4 | Cumple |
| CA-06 | Desde la Web y la aplicación móvil consultar el estado de un trámite y entregar un documento, sin ver expedientes ajenos. | OE-5 | Condicionado. Cumplido en la web (adaptada a celular); no existe una aplicación móvil nativa |
| CA-07 | Completar un recorrido de atención con revisión de la Sponsor. | OE-6 | Condicionado. Pendiente de la revisión con la Sponsor |
| CA-08 | Finalizar un servicio con referidor y calcular la comisión sin duplicarla. | OE-4 | Fuera de alcance. Comisiones fuera de la primera versión (RU-11) |
| CA-09 | Recibir un documento, revisarlo, observarlo con motivo y que la corrección quede recibida hasta una nueva revisión, con historial. | OE-2 | Cumple |

## 10. Diferencias entre el borrador (`Nivel.docx`) y la versión final

La versión final (Overleaf) es la que se implementó. Diferencias relevantes del borrador:

| ID | Borrador | Versión final (implementada) |
|---|---|---|
| RS-01.1 | Agregaba «si no cumple las reglas de registro» | Igual en la práctica: la aplicación valida contraseña y teléfono |
| RS-05.1 | No decía que exige sesión ni que se relaciona con la cuenta | Exige sesión y vincula la solicitud a la cuenta |
| RS-05.3 | Pregunta de seguro «al solicitar contratar» | Pregunta de seguro «al aceptar una cotización» |
| RS-05.6 | El asesor registraba si el usuario aceptó o rechazó | El usuario acepta o rechaza desde su cuenta |
| RS-07.2 | «Desde la Web y la aplicación móvil», formatos sin especificar | Desde la aplicación web, PDF o PNG de hasta 10 MB |

## 11. Consigna del proyecto de medio término

Entregable principal: el documento de especificación de requerimientos en PDF, elaborado por hasta 4
estudiantes y con la conformidad del cliente. Debe incluir:

- Integrantes en la primera página, tabla de contenido, índice de tablas e índice de figuras.
- Requerimientos no funcionales clasificados según Sommerville y con criterios de validación.
- Enlace a un repositorio público con evidencias del levantamiento y el prototipo.
- Acta de conformidad firmada por el cliente como apéndice.
- Capturas del prototipo y su flujo de ventanas como apéndice.
- Secciones «Contribuciones individuales» y «Declaración de autoría».
- Plantilla LaTeX de ETS con el logo de ESPOL. Cada estudiante envía su coevaluación.

| Rúbrica | Puntos |
|---|---|
| Especificación y organización de requerimientos funcionales | 40 |
| Especificación y categorización de no funcionales (con criterio de validación) | 20 |
| Elaboración del prototipo | 15 |
| Evidencias de técnicas de levantamiento y metodologías | 5 |
| Estructura del documento | 5 |
| Contenido de otras secciones | 15 |
| **Extra:** trabajo en LaTeX e inglés | +3 |
| **Penalidades:** sin carta de aceptación del cliente −100 · entregables incompletos hasta −50 · cada error ortográfico −2 (máx. −20) · sin coevaluación −50 individual | |

Retrasos: hasta 1 h −10 %, de 1 a 12 h −20 %, de 12 a 48 h −30 %, más de 48 h −100 %.

## 12. Normas de referencia

- **IEEE Std 830-1998** — *Recommended Practice for Software Requirements Specifications*. Describe el
  contenido de una buena especificación y sus cualidades: correcta, no ambigua, completa, consistente,
  priorizada, verificable, modificable y trazable.
- **ISO/IEC/IEEE 29148:2018** — *Systems and software engineering — Life cycle processes — Requirements
  engineering*. Reemplaza a IEEE 830 y define los procesos de ingeniería de requerimientos, las
  características de cada requerimiento (necesario, singular, factible, verificable…) y los documentos
  de requerimientos de stakeholders, del sistema y del software.

Ambas son documentos con derechos de autor; aquí solo se citan. Otras referencias de la consigna:
Robertson y Robertson, Pressman y Maxim, Sommerville, Cohn, SWEBOK, Leffingwell, Wiegers y Beatty,
MockupScreens, guías de ETS y la plantilla Volere.
