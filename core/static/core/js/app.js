(function () {
  'use strict';

  var root = document.documentElement;
  var media = window.matchMedia('(prefers-color-scheme: dark)');

  /* ------------------------------------------------------------ Tema */
  function temaActual() {
    var t = root.getAttribute('data-theme');
    if (t === 'light' || t === 'dark') return t;
    return media.matches ? 'dark' : 'light';
  }
  function syncMeta() {
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', temaActual() === 'dark' ? '#0a111e' : '#f4f6fb');
    document.querySelectorAll('[data-theme-toggle]').forEach(function (b) {
      var dark = temaActual() === 'dark';
      b.setAttribute('aria-label', dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
      b.setAttribute('title', dark ? 'Modo claro' : 'Modo oscuro');
    });
  }
  var movimientoReducido = window.matchMedia('(prefers-reduced-motion: reduce)');
  function aplicarTema(siguiente) {
    // Si coincide con el sistema, se vuelve a modo automático.
    var sistema = media.matches ? 'dark' : 'light';
    if (siguiente === sistema) {
      root.removeAttribute('data-theme');
      try { localStorage.removeItem('theme'); } catch (err) {}
    } else {
      root.setAttribute('data-theme', siguiente);
      try { localStorage.setItem('theme', siguiente); } catch (err) {}
    }
    syncMeta();
  }
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-theme-toggle]');
    if (!btn) return;
    var siguiente = temaActual() === 'dark' ? 'light' : 'dark';
    if (movimientoReducido.matches) { aplicarTema(siguiente); return; }
    if (document.startViewTransition) {
      /* El tema nuevo se revela en círculo desde el botón. */
      var r = btn.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      root.style.setProperty('--tema-x', x + 'px');
      root.style.setProperty('--tema-y', y + 'px');
      root.style.setProperty('--tema-r', Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)) + 'px');
      root.classList.add('tema-anim');
      var fin = function () { root.classList.remove('tema-anim'); };
      document.startViewTransition(function () { aplicarTema(siguiente); }).finished.then(fin, fin);
    } else {
      root.classList.add('tema-suave');
      aplicarTema(siguiente);
      setTimeout(function () { root.classList.remove('tema-suave'); }, 500);
    }
  });
  if (media.addEventListener) media.addEventListener('change', syncMeta);
  syncMeta();

  /* ------------------------------------------------------------ Movimiento reducido
     Las animaciones SVG (SMIL) no obedecen al CSS: se detienen aquí dejando
     el avión quieto sobre la ruta. */
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('svg.auth-art, svg.hero-art').forEach(function (svg) {
      if (svg.pauseAnimations) { svg.setCurrentTime(6.5); svg.pauseAnimations(); }
    });
  }

  /* ------------------------------------------------------------ Toasts */
  function cerrarToast(t) {
    if (!t || t.classList.contains('is-leaving')) return;
    t.classList.add('is-leaving');
    setTimeout(function () { t.remove(); }, 260);
  }
  document.querySelectorAll('.toast').forEach(function (t, i) {
    var btn = t.querySelector('button');
    if (btn) btn.addEventListener('click', function () { cerrarToast(t); });
    setTimeout(function () { cerrarToast(t); }, 6000 + i * 800);
  });

  /* ------------------------------------------------------------ Mostrar contraseña */
  document.querySelectorAll('[data-reveal]').forEach(function (btn) {
    var input = document.getElementById(btn.getAttribute('data-reveal'));
    if (!input) return;
    btn.addEventListener('click', function () {
      var visible = input.type === 'text';
      input.type = visible ? 'password' : 'text';
      btn.setAttribute('aria-pressed', String(!visible));
      btn.setAttribute('aria-label', visible ? 'Mostrar contraseña' : 'Ocultar contraseña');
      btn.querySelector('.i-eye').style.display = visible ? '' : 'none';
      btn.querySelector('.i-eye-off').style.display = visible ? 'none' : '';
    });
  });

  /* ------------------------------------------------------------ Evitar doble envío */
  document.querySelectorAll('form[data-submit-once]').forEach(function (form) {
    form.addEventListener('submit', function () {
      var btn = form.querySelector('[type="submit"]');
      if (!btn) return;
      setTimeout(function () {
        btn.disabled = true;
        var label = btn.querySelector('[data-label]');
        if (label && btn.dataset.loading) label.textContent = btn.dataset.loading;
      }, 0);
    });
  });

  /* ------------------------------------------------------------ Stepper numérico */
  document.querySelectorAll('[data-stepper]').forEach(function (wrap) {
    var input = wrap.querySelector('input');
    var menos = wrap.querySelector('[data-step="-1"]');
    var mas = wrap.querySelector('[data-step="1"]');
    var min = parseInt(input.min || '1', 10), max = parseInt(input.max || '99', 10);
    function sync() {
      var v = parseInt(input.value || min, 10);
      menos.disabled = v <= min;
      mas.disabled = v >= max;
    }
    wrap.addEventListener('click', function (e) {
      var b = e.target.closest('[data-step]');
      if (!b) return;
      var v = parseInt(input.value || min, 10) + parseInt(b.dataset.step, 10);
      input.value = Math.min(max, Math.max(min, v));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      sync();
    });
    input.addEventListener('input', sync);
    sync();
  });

  /* ------------------------------------------------------------ Intercambiar origen/destino */
  document.querySelectorAll('[data-swap]').forEach(function (btn) {
    var ids = btn.getAttribute('data-swap').split(',');
    btn.addEventListener('click', function () {
      var a = document.getElementById(ids[0]), b = document.getElementById(ids[1]);
      var tmp = a.value; a.value = b.value; b.value = tmp;
      btn.classList.toggle('spin');
    });
  });

  /* ------------------------------------------------------------ Mostrar/ocultar según radios
     data-show-when="tipo=vuelo"  ·  varias alternativas con "|" (basta que se cumpla una) */
  function valorRadio(nombre) {
    var sel = document.querySelector('input[name="' + nombre + '"]:checked');
    return sel ? sel.value : null;
  }
  document.querySelectorAll('[data-solo-tipo]').forEach(function (campo) {
    var caja = campo.closest('.field');
    if (caja) caja.setAttribute('data-show-when', 'tipo=' + campo.dataset.soloTipo);
  });
  var sincronizar = [], radiosVigilados = {};
  document.querySelectorAll('[data-show-when]').forEach(function (el) {
    var conds = el.getAttribute('data-show-when').split('|').map(function (c) { return c.split('='); });
    function sync() {
      el.hidden = !conds.some(function (c) { return valorRadio(c[0]) === c[1]; });
    }
    conds.forEach(function (c) { radiosVigilados[c[0]] = true; });
    sincronizar.push(sync);
    sync();
  });
  Object.keys(radiosVigilados).forEach(function (nombre) {
    document.querySelectorAll('input[name="' + nombre + '"]').forEach(function (r) {
      r.addEventListener('change', function () {
        animarCambio(r.form || document.body, function () { sincronizar.forEach(function (s) { s(); }); });
      });
    });
  });
  document.querySelectorAll('[data-show-when-select]').forEach(function (el) {
    var c = el.getAttribute('data-show-when-select').split('=');
    var sel = document.getElementById(c[0]);
    if (!sel) return;
    function sync() { el.hidden = sel.value !== c[1]; }
    sel.addEventListener('change', sync);
    sync();
  });

  /* ------------------------------------------------------------ Menú del sitio público (móvil) */
  document.querySelectorAll('[data-menu]').forEach(function (btn) {
    var menu = document.getElementById(btn.getAttribute('aria-controls'));
    btn.addEventListener('click', function () {
      var abierto = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', String(!abierto));
      btn.setAttribute('aria-label', abierto ? 'Abrir menú' : 'Cerrar menú');
      menu.hidden = abierto;
    });
  });

  /* ------------------------------------------------------------ Total estimado de una oferta */
  document.querySelectorAll('[data-estimador]').forEach(function (box) {
    var precio = parseFloat(box.dataset.precio);
    var input = box.dataset.pasajerosId ? document.getElementById(box.dataset.pasajerosId) : box.querySelector('input[name="pasajeros"]');
    var salida = box.querySelector('[data-total]');
    if (!input || !salida || isNaN(precio)) return;
    var fmt = new Intl.NumberFormat('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    function sync() {
      var n = Math.min(20, Math.max(1, parseInt(input.value || '1', 10) || 1));
      salida.textContent = '$' + fmt.format(precio * n);
    }
    input.addEventListener('input', sync);
    input.addEventListener('change', sync);
    sync();
  });

  /* ------------------------------------------------------------ Pagar lo restante */
  var restantesData = document.getElementById('restantes-data');
  var btnRestante = document.querySelector('[data-pagar-restante]');
  if (restantesData && btnRestante) {
    var restantes = JSON.parse(restantesData.textContent);
    var selServicio = document.getElementById('id_expediente');
    var monto = document.getElementById('id_monto');
    var fmtR = new Intl.NumberFormat('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    function syncRestante() {
      var r = restantes[selServicio.value];
      btnRestante.disabled = !r;
      if (r) monto.max = r; else monto.removeAttribute('max');
    }
    btnRestante.addEventListener('click', function () {
      var r = restantes[selServicio.value];
      if (r) { monto.value = r; monto.dispatchEvent(new Event('input', { bubbles: true })); monto.focus(); }
    });
    selServicio.addEventListener('change', syncRestante);
    syncRestante();
  }

  /* ------------------------------------------------------------ Carrusel */
  document.querySelectorAll('[data-carrusel]').forEach(function (c) {
    var pista = c.querySelector('[data-carrusel-pista]');
    var prev = c.querySelector('[data-carrusel-prev]'), next = c.querySelector('[data-carrusel-next]');
    function paso() { return pista.firstElementChild ? pista.firstElementChild.getBoundingClientRect().width + 20 : pista.clientWidth; }
    function sync() {
      prev.disabled = pista.scrollLeft < 5;
      next.disabled = pista.scrollLeft + pista.clientWidth >= pista.scrollWidth - 5;
    }
    prev.addEventListener('click', function () { pista.scrollBy({ left: -paso() }); });
    next.addEventListener('click', function () { pista.scrollBy({ left: paso() }); });
    pista.addEventListener('scroll', sync, { passive: true });
    window.addEventListener('resize', sync);
    sync();
  });

  /* ------------------------------------------------------------ Barra lateral del panel (móvil) */
  var sidebar = document.getElementById('sidebar');
  if (sidebar) {
    var abrirSb = document.querySelector('[data-sidebar-open]');
    var fondo = document.querySelector('.sidebar-backdrop');
    function sb(mostrar) {
      sidebar.classList.toggle('is-open', mostrar);
      fondo.hidden = !mostrar;
      if (abrirSb) abrirSb.setAttribute('aria-expanded', String(mostrar));
      document.body.style.overflow = mostrar ? 'hidden' : '';
    }
    if (abrirSb) abrirSb.addEventListener('click', function () { sb(true); });
    document.querySelectorAll('[data-sidebar-close]').forEach(function (el) { el.addEventListener('click', function () { sb(false); }); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && sidebar.classList.contains('is-open')) sb(false); });
  }

  /* ------------------------------------------------------------ Video tutorial (RS-04.3) */
  var tutorial = document.querySelector('[data-tutorial]');
  if (tutorial) {
    var video = tutorial.querySelector('video');
    /* Hay un video por tema; al cambiar de tema con el video abierto se conserva el punto de reproducción. */
    var videoSegunTema = function () {
      var url = temaActual() === 'dark' && video.dataset.videoOscuro ? video.dataset.videoOscuro : video.dataset.videoClaro;
      if (!url || video.getAttribute('src') === url) return;
      var enCurso = video.currentTime && video.duration ? { t: video.currentTime / video.duration, pausado: video.paused } : null;
      video.setAttribute('src', url);
      if (!enCurso) return;
      video.load();
      video.addEventListener('loadedmetadata', function () {
        video.currentTime = enCurso.t * video.duration;
        if (!enCurso.pausado) video.play().catch(function () {});
      }, { once: true });
    };
    new MutationObserver(function () { if (tutorial.open) videoSegunTema(); }).observe(root, { attributes: true, attributeFilter: ['data-theme'] });
    document.querySelectorAll('[data-tutorial-open]').forEach(function (b) {
      b.addEventListener('click', function () { videoSegunTema(); tutorial.showModal(); video.play().catch(function () {}); });
    });
    function cerrarTutorial() { video.pause(); if (tutorial.open) tutorial.close(); }
    tutorial.querySelector('[data-tutorial-close]').addEventListener('click', cerrarTutorial);
    tutorial.addEventListener('close', function () { video.pause(); });
    tutorial.addEventListener('click', function (e) { if (e.target === tutorial) cerrarTutorial(); });
  }

  /* ------------------------------------------------------------ Asistente virtual (RS-04.1) */
  var chat = document.querySelector('[data-chat]');
  if (chat) {
    var abrir = document.querySelector('[data-chat-open]');
    var log = chat.querySelector('[data-chat-log]');
    var formChat = chat.querySelector('[data-chat-form]');
    var entrada = formChat.querySelector('input');
    function toggleChat(mostrar) {
      chat.hidden = !mostrar;
      abrir.setAttribute('aria-expanded', String(mostrar));
      if (mostrar) entrada.focus();
    }
    function agregar(texto, clase, enlace, enlaceTexto) {
      var div = document.createElement('div');
      div.className = 'msg ' + clase;
      div.textContent = texto;
      if (enlace) {
        var a = document.createElement('a');
        a.href = enlace;
        a.textContent = (enlaceTexto || 'Abrir') + ' →';
        if (/^https?:/.test(enlace)) { a.target = '_blank'; a.rel = 'noopener'; }
        div.appendChild(document.createElement('br'));
        div.appendChild(a);
      }
      log.appendChild(div);
      log.scrollTop = log.scrollHeight;
    }
    function preguntar(q) {
      q = q.trim();
      if (!q) return;
      agregar(q, 'msg--user');
      fetch(chat.dataset.url + '?q=' + encodeURIComponent(q), { headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (d) { agregar(d.respuesta, 'msg--bot', d.enlace, d.enlace_texto); })
        .catch(function () { agregar('No pude responder en este momento. Inténtalo de nuevo.', 'msg--bot'); });
    }
    abrir.addEventListener('click', function () { toggleChat(chat.hidden); });
    chat.querySelector('[data-chat-close]').addEventListener('click', function () { toggleChat(false); abrir.focus(); });
    formChat.addEventListener('submit', function (e) { e.preventDefault(); preguntar(entrada.value); entrada.value = ''; });
    chat.querySelectorAll('[data-chat-q]').forEach(function (b) {
      b.addEventListener('click', function () { preguntar(b.getAttribute('data-chat-q')); });
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !chat.hidden) toggleChat(false); });
  }

  /* ------------------------------------------------------------ Expediente nuevo: datos de la cuenta (RS-08.2) */
  var usuariosData = document.getElementById('usuarios-data');
  var selUsuario = document.getElementById('id_usuario');
  if (usuariosData && selUsuario) {
    var datos = JSON.parse(usuariosData.textContent);
    var mapa = { nombre: 'id_nombre', email: 'id_email', telefono: 'id_telefono', documento: 'id_documento_identidad' };
    selUsuario.addEventListener('change', function () {
      var d = datos[selUsuario.value];
      if (!d) return;
      Object.keys(mapa).forEach(function (k) {
        var campo = document.getElementById(mapa[k]);
        if (campo && !campo.value && d[k]) campo.value = d[k];
      });
    });
  }

  /* ------------------------------------------------------------ Fecha de regreso >= salida */
  document.querySelectorAll('[data-min-from]').forEach(function (el) {
    var src = document.getElementById(el.getAttribute('data-min-from'));
    if (!src) return;
    function sync() {
      if (src.value) {
        el.min = src.value;
        if (el.value && el.value < src.value) el.value = '';
        el.dispatchEvent(new Event('refrescar'));
      }
    }
    src.addEventListener('change', sync);
    sync();
  });

  /* Avisa antes de enviar si el archivo supera el máximo permitido. */
  document.querySelectorAll('input[type=file][data-max-bytes]').forEach(function (campo) {
    campo.addEventListener('change', function () {
      var maximo = Number(campo.dataset.maxBytes);
      var excede = Array.prototype.some.call(campo.files, function (f) { return f.size > maximo; });
      var aviso = campo.closest('.field') && campo.closest('.field').querySelector('.error--archivo');
      if (aviso) aviso.remove();
      if (excede) {
        campo.value = '';
        campo.dispatchEvent(new Event('archivo-limpio'));
        var msg = el('p', 'error error--archivo', 'El archivo pesa más de ' + Math.round(maximo / 1048576) + ' MB. Elige uno más liviano.');
        msg.setAttribute('role', 'alert');
        (campo.closest('.field') || campo.parentNode).appendChild(msg);
      }
    });
  });

  /* Cotización: en un hospedaje las fechas y personas se nombran distinto. */
  var etiquetas = document.querySelectorAll('[data-etiqueta-hospedaje]');
  if (etiquetas.length) {
    var actualizarEtiquetas = function () {
      var marcado = document.querySelector('input[name=tipo]:checked');
      etiquetas.forEach(function (el) {
        var hospedaje = (marcado ? marcado.value : el.dataset.tipoFijo) === 'hospedaje';
        var etiqueta = el.querySelector('.label'), texto = etiqueta.firstChild;
        if (!el.dataset.etiquetaOriginal) el.dataset.etiquetaOriginal = texto.nodeValue;
        var nuevo = hospedaje ? el.dataset.etiquetaHospedaje + ' ' : el.dataset.etiquetaOriginal;
        if (texto.nodeValue === nuevo) return;
        texto.nodeValue = nuevo;
        if (!movimientoReducido.matches && etiqueta.animate) etiqueta.animate([{ opacity: 0, transform: 'translateY(4px)' }, { opacity: 1, transform: 'none' }], { duration: 260, easing: 'ease-out' });
      });
    };
    document.querySelectorAll('input[name=tipo]').forEach(function (r) { r.addEventListener('change', actualizarEtiquetas); });
    actualizarEtiquetas();
  }

  /* Autocompletado de lugares (combobox accesible) y origen según la ubicación.
     Las coordenadas se usan solo aquí, en el navegador: no se envían al servidor. */
  function sinTildes(t) { return (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim(); }
  function leerSesion(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
  function guardarSesion(k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} }
  function distanciaKm(aLat, aLon, bLat, bLon) {
    var r = Math.PI / 180, dLat = (bLat - aLat) * r, dLon = (bLon - aLon) * r;
    var x = Math.pow(Math.sin(dLat / 2), 2) + Math.cos(aLat * r) * Math.cos(bLat * r) * Math.pow(Math.sin(dLon / 2), 2);
    return 12742 * Math.asin(Math.sqrt(x));
  }
  function icono(nombre) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'icon'); svg.setAttribute('width', '18'); svg.setAttribute('height', '18'); svg.setAttribute('aria-hidden', 'true');
    var use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', '#i-' + nombre); svg.appendChild(use);
    return svg;
  }

  document.querySelectorAll('input[data-lugares]').forEach(function (campo, indice) {
    var fuente = document.getElementById(campo.dataset.lugares);
    if (!fuente) return;
    var lugares = JSON.parse(fuente.textContent);
    var filtra = campo.dataset.ubicacion === '1';  // en los buscadores; en formularios solo se ofrece la opción
    var conUbicacion = !!campo.dataset.ubicacion && 'geolocation' in navigator;
    var lista = document.createElement('ul');
    lista.className = 'lugares'; lista.id = 'lugares-lista-' + indice; lista.hidden = true;
    lista.setAttribute('role', 'listbox'); lista.setAttribute('aria-label', 'Lugares sugeridos');
    campo.parentNode.style.position = 'relative';
    campo.parentNode.appendChild(lista);
    campo.setAttribute('role', 'combobox'); campo.setAttribute('aria-autocomplete', 'list');
    campo.setAttribute('aria-expanded', 'false'); campo.setAttribute('aria-controls', lista.id);
    var aviso = document.createElement('p');
    aviso.className = 'hint'; aviso.hidden = true; aviso.setAttribute('role', 'status');
    campo.parentNode.parentNode.appendChild(aviso);
    var opciones = [], activa = -1;

    function avisar(texto) { aviso.textContent = texto; aviso.hidden = !texto; }
    function cerrar() {
      lista.hidden = true; activa = -1;
      campo.setAttribute('aria-expanded', 'false'); campo.removeAttribute('aria-activedescendant');
    }
    function buscar(texto) {
      var q = sinTildes(texto);
      if (!q) return lugares.filter(function (l) { return l.ofertas > 0; }).concat(lugares.filter(function (l) { return !l.ofertas; })).slice(0, 6);
      var inicio = [], resto = [];
      lugares.forEach(function (l) {
        var nombre = sinTildes(l.valor);
        if (nombre.indexOf(q) === 0) inicio.push(l);
        else if (nombre.indexOf(q) > -1 || (' ' + sinTildes(l.detalle)).indexOf(' ' + q) > -1) resto.push(l);
      });
      return inicio.concat(resto).slice(0, 8);
    }
    function agregar(texto, detalle, nombreIcono, alElegir, clase) {
      var li = document.createElement('li');
      li.className = 'lugar' + (clase ? ' ' + clase : ''); li.id = lista.id + '-' + opciones.length;
      li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false');
      var ic = document.createElement('span'); ic.className = 'lugar-icono'; ic.appendChild(icono(nombreIcono));
      var tx = document.createElement('span'); tx.className = 'lugar-texto';
      var no = document.createElement('span'); no.className = 'lugar-nombre'; no.textContent = texto;
      tx.appendChild(no);
      if (detalle) { var de = document.createElement('span'); de.className = 'lugar-detalle'; de.textContent = detalle; tx.appendChild(de); }
      li.appendChild(ic); li.appendChild(tx);
      li.addEventListener('mousedown', function (e) { e.preventDefault(); alElegir(); });
      lista.appendChild(li); opciones.push({ el: li, elegir: alElegir });
    }
    function detalleDe(l) {
      var partes = [];
      if (l.detalle) partes.push(l.detalle);
      if (l.ofertas) partes.push(l.ofertas + (l.ofertas === 1 ? ' oferta' : ' ofertas'));
      return partes.join(' · ');
    }
    function mostrar() {
      lista.textContent = ''; opciones = []; activa = -1;
      campo.removeAttribute('aria-activedescendant');
      if (conUbicacion && !campo.value.trim()) {
        agregar('Usar mi ubicación', 'Buscar la ciudad más cercana', 'pin', function () { cerrar(); ubicar(false); }, 'lugar--ubicacion');
      }
      buscar(campo.value).forEach(function (l) {
        agregar(l.valor, detalleDe(l), 'pin', function () { campo.value = l.valor; avisar(''); cerrar(); });
      });
      if (!opciones.length) {
        var vacio = document.createElement('li');
        vacio.className = 'lugares-vacio'; vacio.textContent = 'Sin sugerencias. Puedes buscar con lo que escribiste.';
        lista.appendChild(vacio);
      }
      lista.hidden = false; campo.setAttribute('aria-expanded', 'true');
    }
    function resaltar(i) {
      if (activa > -1) opciones[activa].el.setAttribute('aria-selected', 'false');
      activa = i;
      opciones[i].el.setAttribute('aria-selected', 'true');
      opciones[i].el.scrollIntoView({ block: 'nearest' });
      campo.setAttribute('aria-activedescendant', opciones[i].el.id);
    }
    /* Automático: rellena y filtra solo si hay vuelos desde esa ciudad, para no dejar la página vacía. */
    function ubicar(automatico) {
      if (!automatico) avisar('Buscando tu ubicación…');
      navigator.geolocation.getCurrentPosition(function (pos) {
        var cerca = null, menor = 600;
        lugares.forEach(function (l) {
          if (l.lat === undefined) return;
          var km = distanciaKm(pos.coords.latitude, pos.coords.longitude, l.lat, l.lon);
          if (km < menor) { menor = km; cerca = l; }
        });
        if (!cerca) { avisar(automatico ? '' : 'No encontramos una ciudad cercana. Escribe tu origen.'); return; }
        if (campo.value.trim()) { avisar(''); return; }
        campo.value = cerca.valor;
        if (!filtra) {
          avisar('Usamos tu ubicación. Puedes cambiar el origen.');
        } else if (cerca.ofertas && automatico) {
          guardarSesion('origen-detectado', '1');
          campo.form.submit();
        } else {
          avisar(cerca.ofertas ? 'Usamos tu ubicación. Puedes cambiar el origen.' : 'Usamos tu ubicación. Por ahora no hay vuelos publicados desde esta ciudad.');
        }
      }, function () {
        avisar(automatico ? '' : 'No pudimos obtener tu ubicación. Escribe tu origen.');
      }, { timeout: 8000, maximumAge: 3600000 });
    }

    campo.addEventListener('focus', mostrar);
    campo.addEventListener('input', function () { avisar(''); mostrar(); });
    campo.addEventListener('blur', cerrar);
    campo.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !lista.hidden) { e.preventDefault(); cerrar(); return; }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (lista.hidden) mostrar();
        if (!opciones.length) return;
        var paso = e.key === 'ArrowDown' ? 1 : -1;
        resaltar(activa < 0 ? (paso > 0 ? 0 : opciones.length - 1) : (activa + paso + opciones.length) % opciones.length);
      } else if (e.key === 'Enter' && activa > -1) {
        e.preventDefault(); opciones[activa].elegir();
      }
    });

    if (conUbicacion && filtra) {
      if (leerSesion('origen-detectado') === '1' && campo.value) {
        avisar('Usamos tu ubicación. Puedes cambiar el origen.');
        guardarSesion('origen-detectado', '');
      }
      /* Se intenta una sola vez por sesión, y nunca si el cliente ya está filtrando. */
      if (!location.search && !campo.value && leerSesion('origen-consultado') !== '1') {
        guardarSesion('origen-consultado', '1');
        ubicar(true);
      }
    }
  });

  /* ------------------------------------------------------------ Selector propio de fecha y hora
     Sustituye los controles nativos. El campo original sigue enviando el mismo formato ISO. */
  var MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  var DIAS = [['L', 'lunes'], ['M', 'martes'], ['X', 'miércoles'], ['J', 'jueves'], ['V', 'viernes'], ['S', 'sábado'], ['D', 'domingo']];
  function dos(n) { return (n < 10 ? '0' : '') + n; }
  function aIso(d) { return d.getFullYear() + '-' + dos(d.getMonth() + 1) + '-' + dos(d.getDate()); }
  function deIso(t) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(t || '');
    return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
  }
  function deHora(t) {
    var m = /(?:^|T)(\d{2}):(\d{2})/.exec(t || '');
    return m ? { h: +m[1], m: +m[2] } : null;
  }
  function el(etiqueta, clase, texto) {
    var n = document.createElement(etiqueta);
    if (clase) n.className = clase;
    if (texto !== undefined) n.textContent = texto;
    if (etiqueta === 'button') n.type = 'button';
    return n;
  }
  var selectorAbierto = null;

  function mejorarCampo(input, indice) {
    var tipo = input.type, conFecha = tipo !== 'time', conHora = tipo !== 'date';
    var valorInicial = input.value;
    input.type = 'hidden';
    input.value = valorInicial;
    var boton = el('button', 'input dp-campo');
    boton.id = (input.id || 'selector-' + indice) + '-selector';
    boton.setAttribute('aria-haspopup', 'dialog');
    boton.setAttribute('aria-expanded', 'false');
    ['aria-invalid', 'aria-describedby'].forEach(function (a) {
      if (input.hasAttribute(a)) boton.setAttribute(a, input.getAttribute(a));
    });
    boton.disabled = input.disabled;
    var texto = el('span', 'dp-valor');
    boton.appendChild(texto);
    boton.appendChild(icono(conFecha ? 'calendar' : 'clock'));
    input.parentNode.insertBefore(boton, input.nextSibling);
    var etiqueta = input.id && document.querySelector('label[for="' + input.id + '"]');
    if (etiqueta) etiqueta.htmlFor = boton.id;
    else boton.setAttribute('aria-label', input.getAttribute('aria-label') || 'Elegir fecha');

    function pintar() {
      var f = deIso(input.value), h = deHora(input.value);
      var partes = [];
      if (conFecha && f) partes.push(f.getDate() + ' ' + MESES[f.getMonth()].slice(0, 3) + ' ' + f.getFullYear());
      if (conHora && h) partes.push(dos(h.h) + ':' + dos(h.m));
      var hay = partes.length > 0;
      texto.textContent = hay ? partes.join(', ') : (conFecha ? (conHora ? 'Elige fecha y hora' : 'Elige una fecha') : 'Elige la hora');
      boton.classList.toggle('dp-campo--vacio', !hay);
    }
    input.addEventListener('refrescar', pintar);
    input.addEventListener('change', pintar);
    pintar();

    boton.addEventListener('click', function () {
      if (selectorAbierto && selectorAbierto.boton === boton) { selectorAbierto.cerrar(true); return; }
      if (selectorAbierto) selectorAbierto.cerrar(false);
      abrir();
    });

    function abrir() {
      var hoy = new Date(); hoy.setHours(0, 0, 0, 0);
      var min = deIso(input.getAttribute('min')), max = deIso(input.getAttribute('max'));
      var elegida = deIso(input.value), hora = deHora(input.value);
      var base = elegida || (min && min > hoy ? min : hoy);
      var estado = { anio: base.getFullYear(), mes: base.getMonth(), foco: new Date(base), vista: 'dias' };
      var hoja = window.matchMedia('(max-width: 639px)').matches;
      var pop = el('div', 'dp' + (hoja ? ' dp--hoja' : ''));
      pop.setAttribute('role', 'dialog');
      pop.setAttribute('aria-label', conFecha ? 'Elegir fecha' : 'Elegir hora');
      var fondo = hoja ? el('div', 'dp-fondo') : null;
      if (fondo) document.body.appendChild(fondo);
      document.body.appendChild(pop);
      var contenido = el('div', 'dp-contenido');
      pop.appendChild(contenido);

      function fuera(d) { return (min && d < min) || (max && d > max); }
      function guardar() {
        var v = '';
        if (conFecha && elegida) v = aIso(elegida);
        if (conHora && (!conFecha || elegida)) {
          var h = hora || { h: 9, m: 0 };
          v = conFecha ? v + 'T' + dos(h.h) + ':' + dos(h.m) : dos(h.h) + ':' + dos(h.m);
        }
        input.value = v;
        pintar();
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
      function enfocarDia() {
        var b = contenido.querySelector('[data-dia="' + aIso(estado.foco) + '"]');
        if (b) b.focus();
      }
      function pintarDias() {
        var caja = el('div', 'dp-calendario');
        var cab = el('div', 'dp-cabecera');
        var previo = el('button', 'dp-nav'); previo.setAttribute('aria-label', 'Mes anterior'); previo.appendChild(icono('arrow-left'));
        var titulo = el('button', 'dp-titulo', MESES[estado.mes] + ' ' + estado.anio);
        titulo.setAttribute('aria-label', 'Elegir mes y año: ' + titulo.textContent);
        var sigue = el('button', 'dp-nav'); sigue.setAttribute('aria-label', 'Mes siguiente'); sigue.appendChild(icono('arrow-right'));
        previo.disabled = !!min && new Date(estado.anio, estado.mes, 1) <= min;
        sigue.disabled = !!max && new Date(estado.anio, estado.mes + 1, 0) >= max;
        function moverMes(p) {
          var d = new Date(estado.anio, estado.mes + p, 1);
          estado.anio = d.getFullYear(); estado.mes = d.getMonth(); estado.foco = d;
          estado.direccion = p;
          pintarTodo();
          (p < 0 ? contenido.querySelector('.dp-nav') : contenido.querySelectorAll('.dp-nav')[1]).focus();
        }
        previo.addEventListener('click', function () { moverMes(-1); });
        sigue.addEventListener('click', function () { moverMes(1); });
        titulo.addEventListener('click', function () { estado.vista = 'meses'; pintarTodo(); contenido.querySelector('.dp-titulo').focus(); });
        cab.appendChild(previo); cab.appendChild(titulo); cab.appendChild(sigue);
        caja.appendChild(cab);
        var rejilla = el('div', 'dp-rejilla');
        if (estado.direccion) rejilla.classList.add(estado.direccion > 0 ? 'dp-de-derecha' : 'dp-de-izquierda');
        estado.direccion = 0;
        rejilla.setAttribute('role', 'grid');
        DIAS.forEach(function (d) {
          var c = el('span', 'dp-dia-nombre', d[0]); c.setAttribute('title', d[1]); c.setAttribute('aria-hidden', 'true');
          rejilla.appendChild(c);
        });
        var primero = new Date(estado.anio, estado.mes, 1);
        for (var v = (primero.getDay() + 6) % 7; v > 0; v--) rejilla.appendChild(el('span'));
        var total = new Date(estado.anio, estado.mes + 1, 0).getDate();
        var enMes = estado.foco.getFullYear() === estado.anio && estado.foco.getMonth() === estado.mes;
        if (!enMes) estado.foco = primero;
        for (var n = 1; n <= total; n++) (function (dia) {
          var f = new Date(estado.anio, estado.mes, dia), iso = aIso(f);
          var b = el('button', 'dp-dia', String(dia));
          b.dataset.dia = iso;
          b.setAttribute('aria-label', dia + ' de ' + MESES[estado.mes] + ' de ' + estado.anio);
          b.tabIndex = aIso(estado.foco) === iso ? 0 : -1;
          if (iso === aIso(hoy)) { b.classList.add('dp-dia--hoy'); b.setAttribute('aria-current', 'date'); }
          if (elegida && iso === aIso(elegida)) { b.classList.add('dp-dia--elegido'); b.setAttribute('aria-pressed', 'true'); }
          if (fuera(f)) { b.setAttribute('aria-disabled', 'true'); b.classList.add('dp-dia--no'); }
          b.addEventListener('click', function () {
            if (fuera(f)) return;
            elegida = f; estado.foco = f;
            if (conHora) { pintarTodo(); enfocarDia(); return; }
            guardar(); cerrar(true);
          });
          rejilla.appendChild(b);
        })(n);
        rejilla.addEventListener('keydown', function (e) {
          var d = new Date(estado.foco), mov = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key];
          if (mov) d.setDate(d.getDate() + mov);
          else if (e.key === 'Home') d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
          else if (e.key === 'End') d.setDate(d.getDate() + (6 - ((d.getDay() + 6) % 7)));
          else if (e.key === 'PageUp') d.setMonth(d.getMonth() - 1);
          else if (e.key === 'PageDown') d.setMonth(d.getMonth() + 1);
          else return;
          e.preventDefault();
          estado.foco = d; estado.anio = d.getFullYear(); estado.mes = d.getMonth();
          pintarTodo(); enfocarDia();
        });
        caja.appendChild(rejilla);
        return caja;
      }
      function pintarMeses() {
        var caja = el('div', 'dp-calendario');
        var cab = el('div', 'dp-cabecera');
        var previo = el('button', 'dp-nav'); previo.setAttribute('aria-label', 'Año anterior'); previo.appendChild(icono('arrow-left'));
        var titulo = el('button', 'dp-titulo', String(estado.anio));
        titulo.setAttribute('aria-label', 'Volver a los días');
        var sigue = el('button', 'dp-nav'); sigue.setAttribute('aria-label', 'Año siguiente'); sigue.appendChild(icono('arrow-right'));
        previo.disabled = !!min && estado.anio <= min.getFullYear();
        sigue.disabled = !!max && estado.anio >= max.getFullYear();
        previo.addEventListener('click', function () { estado.anio--; pintarTodo(); contenido.querySelector('.dp-nav').focus(); });
        sigue.addEventListener('click', function () { estado.anio++; pintarTodo(); contenido.querySelectorAll('.dp-nav')[1].focus(); });
        titulo.addEventListener('click', function () { estado.vista = 'dias'; pintarTodo(); contenido.querySelector('.dp-titulo').focus(); });
        cab.appendChild(previo); cab.appendChild(titulo); cab.appendChild(sigue);
        caja.appendChild(cab);
        var meses = el('div', 'dp-meses');
        MESES.forEach(function (nombre, i) {
          var b = el('button', 'dp-mes', nombre.slice(0, 3));
          b.setAttribute('aria-label', nombre + ' de ' + estado.anio);
          if (i === estado.mes) b.classList.add('dp-mes--actual');
          b.disabled = (!!min && new Date(estado.anio, i + 1, 0) < min) || (!!max && new Date(estado.anio, i, 1) > max);
          b.addEventListener('click', function () {
            estado.mes = i; estado.foco = new Date(estado.anio, i, 1); estado.vista = 'dias';
            pintarTodo(); enfocarDia();
          });
          meses.appendChild(b);
        });
        caja.appendChild(meses);
        return caja;
      }
      function columna(nombre, valores, actual, alElegir) {
        var col = el('div', 'dp-columna');
        col.setAttribute('role', 'listbox'); col.setAttribute('aria-label', nombre);
        valores.forEach(function (v) {
          var b = el('button', 'dp-hora', dos(v));
          b.setAttribute('role', 'option');
          b.setAttribute('aria-selected', String(v === actual));
          b.setAttribute('aria-label', dos(v) + ' ' + nombre);
          b.addEventListener('click', function () { alElegir(v); });
          col.appendChild(b);
        });
        return col;
      }
      function pintarHora() {
        var paso = Math.max(1, Math.round((+input.getAttribute('step') || 300) / 60));
        var minutos = [];
        for (var m = 0; m < 60; m += paso) minutos.push(m);
        var actual = hora || null;
        if (actual && minutos.indexOf(actual.m) < 0) { minutos.push(actual.m); minutos.sort(function (a, b) { return a - b; }); }
        var horas = [];
        for (var h = 0; h < 24; h++) horas.push(h);
        var caja = el('div', 'dp-tiempo');
        var cols = el('div', 'dp-columnas');
        function cambiar(campo, v) {
          hora = hora || { h: 9, m: 0 };
          hora[campo] = v;
          pintarTodo();
          var marcada = contenido.querySelector('.dp-columna:' + (campo === 'h' ? 'first-child' : 'last-child') + ' [aria-selected="true"]');
          if (marcada) marcada.focus();
        }
        cols.appendChild(columna('horas', horas, actual ? actual.h : -1, function (v) { cambiar('h', v); }));
        cols.appendChild(el('span', 'dp-dos-puntos', ':'));
        cols.appendChild(columna('minutos', minutos, actual ? actual.m : -1, function (v) { cambiar('m', v); }));
        caja.appendChild(cols);
        return caja;
      }
      function pintarTodo() {
        var desplazamientos = [].map.call(contenido.querySelectorAll('.dp-columna'), function (c) { return c.scrollTop; });
        contenido.textContent = '';
        var cuerpo = el('div', 'dp-cuerpo');
        if (conFecha) cuerpo.appendChild(estado.vista === 'dias' ? pintarDias() : pintarMeses());
        if (conHora) cuerpo.appendChild(pintarHora());
        contenido.appendChild(cuerpo);
        var pie = el('div', 'dp-pie');
        var borrar = el('button', 'dp-accion', 'Borrar');
        borrar.addEventListener('click', function () { elegida = null; hora = null; guardar(); cerrar(true); });
        pie.appendChild(borrar);
        if (conFecha) {
          var botonHoy = el('button', 'dp-accion', 'Hoy');
          botonHoy.disabled = fuera(hoy);
          botonHoy.addEventListener('click', function () {
            elegida = new Date(hoy); estado.anio = hoy.getFullYear(); estado.mes = hoy.getMonth(); estado.foco = new Date(hoy); estado.vista = 'dias';
            if (conHora) { pintarTodo(); enfocarDia(); return; }
            guardar(); cerrar(true);
          });
          pie.appendChild(botonHoy);
        }
        if (conHora) {
          var listo = el('button', 'dp-accion dp-accion--principal', 'Listo');
          listo.disabled = conFecha && !elegida;
          listo.addEventListener('click', function () { guardar(); cerrar(true); });
          pie.appendChild(listo);
        }
        contenido.appendChild(pie);
        [].forEach.call(contenido.querySelectorAll('.dp-columna'), function (c, i) {
          if (desplazamientos.length) { c.scrollTop = desplazamientos[i]; return; }
          var marcada = c.querySelector('[aria-selected="true"]');
          c.scrollTop = marcada ? marcada.offsetTop - c.clientHeight / 2 + marcada.offsetHeight / 2 : (i === 0 ? 9 * 40 : 0);
        });
        colocar();
      }
      function colocar() {
        if (hoja) return;
        var r = boton.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
        var abajo = r.bottom + h + 14 <= innerHeight || r.top - h - 14 < 0;
        pop.style.top = (abajo ? r.bottom + 6 : r.top - h - 6) + 'px';
        pop.style.left = Math.max(8, Math.min(r.left, innerWidth - w - 8)) + 'px';
        pop.style.transformOrigin = abajo ? 'top left' : 'bottom left';
      }
      function alPulsarFuera(e) {
        if (!pop.contains(e.target) && !boton.contains(e.target)) cerrar(false);
      }
      function alTeclear(e) {
        if (e.key === 'Escape') { e.preventDefault(); cerrar(true); }
      }
      function alSalirFoco(e) {
        if (e.relatedTarget && !pop.contains(e.relatedTarget) && e.relatedTarget !== boton) cerrar(false);
      }
      function cerrar(devolverFoco) {
        if (selectorAbierto !== control) return;
        selectorAbierto = null;
        document.removeEventListener('mousedown', alPulsarFuera);
        document.removeEventListener('keydown', alTeclear);
        window.removeEventListener('scroll', colocar, true);
        window.removeEventListener('resize', colocar);
        boton.setAttribute('aria-expanded', 'false');
        pop.classList.add('dp--saliendo');
        if (fondo) fondo.classList.add('dp-fondo--saliendo');
        var quitar = function () { pop.remove(); if (fondo) fondo.remove(); };
        if (movimientoReducido.matches) quitar(); else setTimeout(quitar, 160);
        if (devolverFoco) boton.focus();
      }
      var control = { boton: boton, cerrar: cerrar };
      selectorAbierto = control;
      boton.setAttribute('aria-expanded', 'true');
      pintarTodo();
      if (fondo) fondo.addEventListener('click', function () { cerrar(true); });
      document.addEventListener('mousedown', alPulsarFuera);
      document.addEventListener('keydown', alTeclear);
      pop.addEventListener('focusout', alSalirFoco);
      window.addEventListener('scroll', colocar, true);
      window.addEventListener('resize', colocar);
      if (conFecha) enfocarDia();
      else (contenido.querySelector('[aria-selected="true"]') || contenido.querySelector('.dp-hora')).focus({ preventScroll: true });
    }
  }
  document.querySelectorAll('input[type="date"], input[type="time"], input[type="datetime-local"]').forEach(mejorarCampo);

  /* ------------------------------------------------------------ Animaciones */
  if (!movimientoReducido.matches) {
    /* Aparición escalonada al entrar en pantalla. */
    if ('IntersectionObserver' in window) {
      var aparecer = '.offer, .feature, .promo, .benefit, .post, .faq-item, .req, .stat, .kpi, .tutorial-card, .public .card, .section-head';
      var observador = new IntersectionObserver(function (entradas) {
        entradas.forEach(function (e) {
          if (!e.isIntersecting) return;
          observador.unobserve(e.target);
          e.target.classList.add('visto');
        });
      }, { threshold: 0.06, rootMargin: '0px 0px -4% 0px' });
      [].slice.call(document.querySelectorAll(aparecer), 0, 120).forEach(function (n) {
        if (n.closest('.fade-up, .aparece') || n.querySelector('.input:focus')) return;
        var hermanos = n.parentNode ? [].indexOf.call(n.parentNode.children, n) : 0;
        n.style.setProperty('--retardo', Math.min(hermanos, 5) * 70 + 'ms');
        n.classList.add('aparece');
        var limpiar = function (e) {
          if (e.target !== n || e.propertyName !== 'opacity') return;
          n.classList.remove('aparece', 'visto');
          n.style.removeProperty('--retardo');
          n.removeEventListener('transitionend', limpiar);
        };
        n.addEventListener('transitionend', limpiar);
        observador.observe(n);
      });
    }
    /* Las cifras del resumen cuentan hasta su valor. */
    document.querySelectorAll('.stat-value, .kpi strong').forEach(function (n) {
      var txt = n.textContent.trim();
      if (!/^\d{1,5}$/.test(txt) || txt === '0') return;
      var fin = +txt, inicio = null;
      n.textContent = '0';
      function paso(t) {
        if (inicio === null) inicio = t;
        var p = Math.min((t - inicio) / 800, 1);
        n.textContent = String(Math.round(fin * (1 - Math.pow(1 - p, 3))));
        if (p < 1) requestAnimationFrame(paso); else n.textContent = txt;
      }
      requestAnimationFrame(paso);
    });
    /* El total estimado destaca cuando cambia. */
    if ('MutationObserver' in window) {
      document.querySelectorAll('[data-total]').forEach(function (n) {
        new MutationObserver(function () {
          n.classList.remove('pulso');
          void n.offsetWidth;
          n.classList.add('pulso');
        }).observe(n, { childList: true, characterData: true, subtree: true });
      });
    }
  }

  /* ------------------------------------------------------------ Cambios de formulario animados
     Los campos que siguen visibles se deslizan a su nuevo lugar, los nuevos aparecen y los que salen se desvanecen. */
  function animarCambio(raiz, cambio) {
    if (movimientoReducido.matches || !raiz.animate) { cambio(); return; }
    var sel = '[data-show-when], .field, .route-swap, .form-section-title, .form-actions';
    var items = [].filter.call(raiz.querySelectorAll(sel), function (n) { return !n.parentElement.closest(sel); });
    var antes = items.map(function (n) { var r = n.getBoundingClientRect(); return { r: r, v: n.getClientRects().length > 0 }; });
    var caja = raiz.closest('.card') || raiz.querySelector('.card') || raiz, alto = caja.offsetHeight;
    var curva = 'cubic-bezier(.2, .7, .2, 1)';
    items.forEach(function (n, i) { if (antes[i].v && !n.dataset.x) antes[i].copia = n; });
    cambio();
    items.forEach(function (n, i) {
      var a = antes[i], ahora = n.getClientRects().length > 0;
      if (a.v && ahora) {
        var r = n.getBoundingClientRect(), dx = a.r.left - r.left, dy = a.r.top - r.top;
        if (Math.abs(dx) > 1 || Math.abs(dy) > 1) n.animate([{ transform: 'translate(' + dx + 'px,' + dy + 'px)' }, { transform: 'none' }], { duration: 340, easing: curva });
      } else if (!a.v && ahora) {
        n.animate([{ opacity: 0, transform: 'translateY(10px) scale(.98)' }, { opacity: 1, transform: 'none' }], { duration: 320, delay: 70, easing: curva, fill: 'backwards' });
      } else if (a.v && !ahora) {
        var fantasma = n.cloneNode(true);
        fantasma.hidden = false;
        fantasma.removeAttribute('id');
        fantasma.setAttribute('aria-hidden', 'true');
        fantasma.querySelectorAll('[id],[name]').forEach(function (c) { c.removeAttribute('id'); c.removeAttribute('name'); });
        fantasma.style.cssText = 'position:fixed;margin:0;pointer-events:none;z-index:6;left:' + a.r.left + 'px;top:' + a.r.top + 'px;width:' + a.r.width + 'px;height:' + a.r.height + 'px';
        document.body.appendChild(fantasma);
        fantasma.animate([{ opacity: 1 }, { opacity: 0, transform: 'scale(.97)' }], { duration: 170, easing: 'ease-in' }).onfinish = function () { fantasma.remove(); };
      }
    });
    var nuevoAlto = caja.offsetHeight;
    if (nuevoAlto !== alto) caja.animate([{ height: alto + 'px' }, { height: nuevoAlto + 'px' }], { duration: 340, easing: curva });
  }

  /* Indicador que se desliza entre las opciones de un control segmentado. */
  document.querySelectorAll('.segmented').forEach(function (grupo) {
    var indicador = el('span', 'seg-indicador');
    indicador.setAttribute('aria-hidden', 'true');
    grupo.classList.add('con-indicador');
    grupo.insertBefore(indicador, grupo.firstChild);
    function mover() {
      var marcado = grupo.querySelector('input:checked');
      indicador.hidden = !marcado;
      if (!marcado) return;
      var l = marcado.closest('label');
      indicador.style.width = l.offsetWidth + 'px';
      indicador.style.height = l.offsetHeight + 'px';
      indicador.style.transform = 'translate(' + l.offsetLeft + 'px,' + l.offsetTop + 'px)';
    }
    grupo.addEventListener('change', mover);
    window.addEventListener('resize', mover);
    mover();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(mover);
    requestAnimationFrame(function () { requestAnimationFrame(function () { grupo.classList.add('seg-listo'); }); });
  });

  /* El icono del encabezado de la cotización acompaña al servicio elegido. */
  var iconoHero = document.querySelector('[data-cotizar] .hero-icon use') || (document.querySelector('.segmented input[name="tipo"]') && document.querySelector('.hero-icon use'));
  if (iconoHero) {
    var ICONOS_TIPO = { vuelo: 'takeoff', paquete: 'suitcase', hospedaje: 'bed' };
    var cambiarIcono = function (animar) {
      var m = document.querySelector('input[name="tipo"]:checked');
      if (!m || !ICONOS_TIPO[m.value]) return;
      iconoHero.setAttribute('href', '#i-' + ICONOS_TIPO[m.value]);
      if (animar && !movimientoReducido.matches) iconoHero.closest('.hero-icon').animate([{ transform: 'scale(.7) rotate(-14deg)', opacity: .3 }, { transform: 'none', opacity: 1 }], { duration: 380, easing: 'cubic-bezier(.2, 1.4, .4, 1)' });
    };
    document.querySelectorAll('input[name="tipo"]').forEach(function (r) { r.addEventListener('change', function () { cambiarIcono(true); }); });
    cambiarIcono(false);
  }

  /* ------------------------------------------------------------ Lista desplegable propia */
  function mejorarSelect(select, indice) {
    if (select.multiple || select.dataset.mejorado) return;
    select.dataset.mejorado = '1';
    [].forEach.call(select.options, function (o) {
      if (o.value === '' && /select an option|^-+$/i.test(o.text.trim())) o.text = 'Selecciona una opción';
    });
    select.removeAttribute('required');
    select.classList.add('sl-nativo');
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');
    var boton = el('button', 'select sl-campo');
    boton.id = (select.id || 'lista-' + indice) + '-lista';
    boton.setAttribute('aria-haspopup', 'listbox');
    boton.setAttribute('aria-expanded', 'false');
    ['aria-invalid', 'aria-describedby'].forEach(function (a) { if (select.hasAttribute(a)) boton.setAttribute(a, select.getAttribute(a)); });
    boton.disabled = select.disabled;
    var texto = el('span', 'dp-valor');
    boton.appendChild(texto);
    select.parentNode.insertBefore(boton, select.nextSibling);
    var etiqueta = select.id && document.querySelector('label[for="' + select.id + '"]');
    if (etiqueta) etiqueta.htmlFor = boton.id;
    else boton.setAttribute('aria-label', select.getAttribute('aria-label') || select.name);
    function pintar() {
      var o = select.options[select.selectedIndex];
      texto.textContent = o ? o.text : '';
      boton.classList.toggle('dp-campo--vacio', !o || o.value === '');
    }
    select.addEventListener('change', pintar);
    pintar();
    var abierto = null;
    function cerrar(foco) {
      if (!abierto) return;
      var a = abierto; abierto = null;
      if (selectorAbierto === a.control) selectorAbierto = null;
      document.removeEventListener('mousedown', a.fuera);
      window.removeEventListener('scroll', a.colocar, true);
      window.removeEventListener('resize', a.colocar);
      boton.setAttribute('aria-expanded', 'false');
      a.pop.classList.add('dp--saliendo');
      if (a.fondo) a.fondo.classList.add('dp-fondo--saliendo');
      var quitar = function () { a.pop.remove(); if (a.fondo) a.fondo.remove(); };
      if (movimientoReducido.matches) quitar(); else setTimeout(quitar, 160);
      if (foco) boton.focus();
    }
    function abrir() {
      if (selectorAbierto) selectorAbierto.cerrar(false);
      var hoja = window.matchMedia('(max-width: 639px)').matches;
      var pop = el('div', 'dp sl' + (hoja ? ' dp--hoja' : ''));
      var fondo = hoja ? el('div', 'dp-fondo') : null;
      if (fondo) { document.body.appendChild(fondo); fondo.addEventListener('click', function () { cerrar(true); }); }
      var buscador = null;
      if (select.options.length > 8) {
        buscador = el('input', 'input sl-buscar');
        buscador.type = 'search'; buscador.placeholder = 'Buscar…'; buscador.autocomplete = 'off';
        buscador.setAttribute('aria-label', 'Buscar en la lista');
        pop.appendChild(buscador);
      }
      var lista = el('ul', 'sl-lista');
      lista.setAttribute('role', 'listbox');
      lista.tabIndex = -1;
      pop.appendChild(lista);
      document.body.appendChild(pop);
      var visibles = [], activo = -1;
      function resaltar(i, centrar) {
        if (activo > -1 && visibles[activo]) visibles[activo].classList.remove('sl-activa');
        activo = i;
        if (visibles[i]) {
          visibles[i].classList.add('sl-activa');
          lista.setAttribute('aria-activedescendant', visibles[i].id);
          if (buscador) buscador.setAttribute('aria-activedescendant', visibles[i].id);
          var top = visibles[i].offsetTop, h = visibles[i].offsetHeight;
          if (centrar) lista.scrollTop = top - lista.clientHeight / 2 + h / 2;
          else if (top < lista.scrollTop) lista.scrollTop = top;
          else if (top + h > lista.scrollTop + lista.clientHeight) lista.scrollTop = top + h - lista.clientHeight;
        }
      }
      function elegir(o) {
        select.value = o.value;
        pintar();
        cerrar(true);
        select.dispatchEvent(new Event('change', { bubbles: true }));
      }
      function pintarLista(filtro) {
        lista.textContent = ''; visibles = []; activo = -1;
        var q = sinTildes(filtro || '');
        [].forEach.call(select.options, function (o, i) {
          if (o.disabled || (q && sinTildes(o.text).indexOf(q) < 0)) return;
          var li = el('li', 'sl-opcion', o.text);
          li.id = boton.id + '-op-' + i;
          li.setAttribute('role', 'option');
          li.setAttribute('aria-selected', String(i === select.selectedIndex));
          if (o.value === '') li.classList.add('sl-opcion--vacia');
          if (i === select.selectedIndex) li.appendChild(icono('check'));
          li.addEventListener('mousedown', function (e) { e.preventDefault(); });
          li.addEventListener('click', function () { elegir(o); });
          lista.appendChild(li);
          visibles.push(li);
        });
        if (!visibles.length) lista.appendChild(el('li', 'lugares-vacio', 'Sin resultados.'));
      }
      function colocar() {
        if (hoja) return;
        var r = boton.getBoundingClientRect();
        pop.style.width = Math.max(r.width, 220) + 'px';
        var h = pop.offsetHeight, abajo = r.bottom + h + 14 <= innerHeight || r.top - h - 14 < 0;
        pop.style.top = (abajo ? r.bottom + 6 : r.top - h - 6) + 'px';
        pop.style.left = Math.max(8, Math.min(r.left, innerWidth - pop.offsetWidth - 8)) + 'px';
        pop.style.transformOrigin = abajo ? 'top' : 'bottom';
      }
      function tecla(e) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault();
          if (visibles.length) resaltar(activo < 0 ? 0 : (activo + (e.key === 'ArrowDown' ? 1 : -1) + visibles.length) % visibles.length);
        } else if (e.key === 'Home' && !buscador) { e.preventDefault(); resaltar(0); }
        else if (e.key === 'End' && !buscador) { e.preventDefault(); resaltar(visibles.length - 1); }
        else if (e.key === 'Enter' || (e.key === ' ' && !buscador)) {
          e.preventDefault();
          if (visibles[activo]) visibles[activo].click();
        } else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cerrar(true); }
        else if (e.key === 'Tab') { cerrar(false); }
        else if (!buscador && e.key.length === 1) {
          var q = sinTildes(e.key);
          for (var i = 0; i < visibles.length; i++) {
            if (sinTildes(visibles[(activo + 1 + i) % visibles.length].textContent).indexOf(q) === 0) { resaltar((activo + 1 + i) % visibles.length); break; }
          }
        }
      }
      var fuera = function (e) { if (!pop.contains(e.target) && !boton.contains(e.target)) cerrar(false); };
      abierto = { pop: pop, fondo: fondo, fuera: fuera, colocar: colocar };
      abierto.control = { boton: boton, cerrar: cerrar };
      selectorAbierto = abierto.control;
      pintarLista('');
      boton.setAttribute('aria-expanded', 'true');
      colocar();
      var inicial = visibles.findIndex(function (v) { return v.getAttribute('aria-selected') === 'true'; });
      resaltar(inicial < 0 ? 0 : inicial, true);
      pop.addEventListener('keydown', tecla);
      if (buscador) {
        buscador.addEventListener('input', function () { pintarLista(buscador.value); if (visibles.length) resaltar(0); colocar(); });
        buscador.focus();
      } else lista.focus();
      document.addEventListener('mousedown', fuera);
      window.addEventListener('scroll', colocar, true);
      window.addEventListener('resize', colocar);
    }
    boton.addEventListener('click', function () { if (abierto) cerrar(true); else abrir(); });
    boton.addEventListener('keydown', function (e) {
      if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && !abierto) { e.preventDefault(); abrir(); }
    });
  }
  document.querySelectorAll('select').forEach(mejorarSelect);

  /* ------------------------------------------------------------ Campo de archivo propio */
  document.querySelectorAll('input[type="file"]').forEach(function (campo) {
    campo.removeAttribute('required');
    var zona = el('label', 'archivo-zona');
    var ic = el('span', 'archivo-icono'); ic.appendChild(icono('upload'));
    var tx = el('span', 'archivo-texto');
    var nombre = el('span', 'archivo-nombre'), ayuda = el('span', 'archivo-ayuda', 'o arrástralo aquí');
    tx.appendChild(nombre); tx.appendChild(ayuda);
    var quitar = el('button', 'archivo-quitar');
    quitar.setAttribute('aria-label', 'Quitar archivo'); quitar.hidden = true; quitar.appendChild(icono('x', 16));
    campo.parentNode.insertBefore(zona, campo);
    zona.appendChild(campo); zona.appendChild(ic); zona.appendChild(tx); zona.appendChild(quitar);
    campo.classList.add('archivo-nativo');
    function pintar() {
      var f = campo.files && campo.files[0];
      zona.classList.toggle('archivo-zona--lleno', !!f);
      nombre.textContent = f ? f.name : (campo.closest('.file-field') && campo.closest('.file-field').querySelector('.file-current') ? 'Elegir otro archivo' : 'Elegir archivo');
      ayuda.textContent = f ? (f.size < 1048576 ? Math.max(1, Math.round(f.size / 1024)) + ' KB' : (f.size / 1048576).toFixed(1).replace('.', ',') + ' MB') : 'o arrástralo aquí';
      quitar.hidden = !f;
      ic.textContent = ''; ic.appendChild(icono(f ? 'check' : 'upload'));
    }
    quitar.addEventListener('click', function (e) { e.preventDefault(); campo.value = ''; campo.dispatchEvent(new Event('change', { bubbles: true })); });
    campo.addEventListener('change', pintar);
    campo.addEventListener('archivo-limpio', pintar);
    ['dragenter', 'dragover'].forEach(function (t) { zona.addEventListener(t, function (e) { e.preventDefault(); zona.classList.add('archivo-zona--sobre'); }); });
    ['dragleave', 'drop'].forEach(function (t) { zona.addEventListener(t, function (e) { e.preventDefault(); zona.classList.remove('archivo-zona--sobre'); }); });
    zona.addEventListener('drop', function (e) {
      if (!e.dataTransfer.files.length) return;
      campo.files = e.dataTransfer.files;
      campo.dispatchEvent(new Event('change', { bubbles: true }));
    });
    pintar();
  });

  /* ------------------------------------------------------------ Confirmación propia */
  var dialogoConfirmar = null;
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form.dataset || !form.dataset.confirmar) return;
    if (form.dataset.confirmado === '1') { form.dataset.confirmado = ''; return; }
    e.preventDefault();
    e.stopImmediatePropagation();
    var enviador = e.submitter;
    if (!window.HTMLDialogElement) { if (window.confirm(form.dataset.confirmar)) { form.dataset.confirmado = '1'; form.requestSubmit(enviador); } return; }
    if (!dialogoConfirmar) {
      dialogoConfirmar = el('dialog', 'modal confirmar');
      dialogoConfirmar.setAttribute('aria-labelledby', 'confirmar-texto');
      var p = el('p', 'confirmar-texto'); p.id = 'confirmar-texto';
      var acciones = el('div', 'confirmar-acciones');
      var no = el('button', 'btn', 'Cancelar'), si = el('button', 'btn btn-peligro', 'Confirmar');
      acciones.appendChild(no); acciones.appendChild(si);
      dialogoConfirmar.appendChild(p); dialogoConfirmar.appendChild(acciones);
      no.addEventListener('click', function () { dialogoConfirmar.close(); });
      dialogoConfirmar.addEventListener('click', function (ev) { if (ev.target === dialogoConfirmar) dialogoConfirmar.close(); });
      document.body.appendChild(dialogoConfirmar);
    }
    dialogoConfirmar.querySelector('.confirmar-texto').textContent = form.dataset.confirmar;
    dialogoConfirmar.querySelector('.btn-peligro').onclick = function () {
      dialogoConfirmar.close();
      form.dataset.confirmado = '1';
      if (enviador) form.requestSubmit(enviador); else form.requestSubmit();
    };
    dialogoConfirmar.showModal();
    dialogoConfirmar.querySelector('.btn').focus();
  }, true);

  /* ------------------------------------------------------------ Reproductor de video propio */
  function tiempo(s) {
    if (!isFinite(s) || s < 0) s = 0;
    var m = Math.floor(s / 60), h = Math.floor(m / 60), seg = Math.floor(s % 60);
    return h ? h + ':' + dos(m % 60) + ':' + dos(seg) : m + ':' + dos(seg);
  }
  document.querySelectorAll('video').forEach(function (video) {
    video.removeAttribute('controls');
    var caja = el('div', 'vp vp--detenido');
    caja.tabIndex = 0;
    caja.setAttribute('role', 'group');
    caja.setAttribute('aria-label', 'Reproductor de video');
    video.parentNode.insertBefore(caja, video);
    caja.appendChild(video);
    var grande = el('button', 'vp-grande'); grande.setAttribute('aria-label', 'Reproducir video');
    grande.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4.5v15l12-7.5z" fill="currentColor"/></svg>';
    var carga = el('span', 'vp-carga'); carga.setAttribute('aria-hidden', 'true');
    var barra = el('div', 'vp-barra');
    var linea = document.createElement('input');
    linea.type = 'range'; linea.className = 'vp-rango vp-linea'; linea.min = 0; linea.max = 1000; linea.value = 0; linea.step = 1;
    linea.setAttribute('aria-label', 'Posición del video');
    var play = el('button', 'vp-btn');
    var tiempoTx = el('span', 'vp-tiempo', '0:00 / 0:00');
    var separador = el('span', 'vp-espacio');
    var sonido = el('button', 'vp-btn');
    var volumen = document.createElement('input');
    volumen.type = 'range'; volumen.className = 'vp-rango vp-volumen'; volumen.min = 0; volumen.max = 1; volumen.step = .05; volumen.value = 1;
    volumen.setAttribute('aria-label', 'Volumen');
    var velocidad = el('button', 'vp-btn vp-velocidad', '1x'); velocidad.setAttribute('aria-label', 'Velocidad de reproducción: 1x');
    var pantalla = el('button', 'vp-btn'); pantalla.setAttribute('aria-label', 'Pantalla completa');
    var fila = el('div', 'vp-fila');
    [play, tiempoTx, separador, sonido, volumen, velocidad, pantalla].forEach(function (n) { fila.appendChild(n); });
    barra.appendChild(linea); barra.appendChild(fila);
    caja.appendChild(grande); caja.appendChild(carga); caja.appendChild(barra);
    function dibujar(boton, svg, etiqueta) {
      boton.innerHTML = '<svg class="icon" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">' + svg + '</svg>';
      boton.setAttribute('aria-label', etiqueta);
    }
    var I_PLAY = '<path d="M7 4.5v15l12-7.5z" fill="currentColor" stroke="none"/>';
    var I_PAUSA = '<path d="M7 4h3.5v16H7zM13.5 4H17v16h-3.5z" fill="currentColor" stroke="none"/>';
    var I_ALTO = '<path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" fill="currentColor" stroke="none"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>';
    var I_MUDO = '<path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" fill="currentColor" stroke="none"/><path d="m16 9.5 5 5M21 9.5l-5 5"/>';
    var I_AMPLIAR = '<path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>';
    var I_REDUCIR = '<path d="M9 4v5H4M20 9h-5V4M15 20v-5h5M4 15h5v5"/>';
    function pintarRango(r) { r.style.setProperty('--p', ((r.value - r.min) / (r.max - r.min)) * 100 + '%'); }
    function pintarPlay() {
      var parado = video.paused || video.ended;
      dibujar(play, parado ? I_PLAY : I_PAUSA, parado ? 'Reproducir' : 'Pausar');
      caja.classList.toggle('vp--detenido', parado);
    }
    function pintarSonido() {
      var mudo = video.muted || video.volume === 0;
      dibujar(sonido, mudo ? I_MUDO : I_ALTO, mudo ? 'Activar sonido' : 'Silenciar');
      volumen.value = mudo ? 0 : video.volume;
      pintarRango(volumen);
    }
    function pintarTiempo() {
      var d = video.duration || 0;
      tiempoTx.textContent = tiempo(video.currentTime) + ' / ' + tiempo(d);
      if (!linea.dataset.moviendo) { linea.value = d ? (video.currentTime / d) * 1000 : 0; pintarRango(linea); }
      if (video.buffered.length && d) linea.style.setProperty('--b', (video.buffered.end(video.buffered.length - 1) / d) * 100 + '%');
      linea.setAttribute('aria-valuetext', tiempo(video.currentTime) + ' de ' + tiempo(d));
    }
    function alternar() { if (video.paused || video.ended) video.play().catch(function () {}); else video.pause(); }
    var temporizador;
    function mostrarControles() {
      caja.classList.remove('vp--oculto');
      clearTimeout(temporizador);
      temporizador = setTimeout(function () { if (!video.paused && !caja.matches(':focus-within:has(.vp-rango:active)')) caja.classList.add('vp--oculto'); }, 2600);
    }
    [grande, play].forEach(function (b) { b.addEventListener('click', function (e) { e.stopPropagation(); alternar(); }); });
    video.addEventListener('click', alternar);
    video.addEventListener('dblclick', function () { pantalla.click(); });
    video.addEventListener('play', pintarPlay);
    video.addEventListener('pause', function () { pintarPlay(); caja.classList.remove('vp--oculto'); });
    video.addEventListener('ended', pintarPlay);
    video.addEventListener('timeupdate', pintarTiempo);
    video.addEventListener('progress', pintarTiempo);
    video.addEventListener('loadedmetadata', pintarTiempo);
    video.addEventListener('durationchange', pintarTiempo);
    video.addEventListener('volumechange', pintarSonido);
    video.addEventListener('waiting', function () { caja.classList.add('vp--cargando'); });
    ['playing', 'canplay', 'pause'].forEach(function (t) { video.addEventListener(t, function () { caja.classList.remove('vp--cargando'); }); });
    video.addEventListener('error', function () {
      caja.classList.add('vp--error');
      if (!caja.querySelector('.vp-mensaje')) caja.appendChild(el('p', 'vp-mensaje', 'No se pudo cargar el video. Inténtalo de nuevo más tarde.'));
    });
    linea.addEventListener('input', function () {
      linea.dataset.moviendo = '1';
      pintarRango(linea);
      if (video.duration) video.currentTime = (linea.value / 1000) * video.duration;
      tiempoTx.textContent = tiempo(video.currentTime) + ' / ' + tiempo(video.duration);
    });
    linea.addEventListener('change', function () { delete linea.dataset.moviendo; });
    sonido.addEventListener('click', function () { video.muted = !video.muted; if (!video.muted && video.volume === 0) video.volume = 1; });
    volumen.addEventListener('input', function () { video.volume = +volumen.value; video.muted = +volumen.value === 0; pintarRango(volumen); });
    var VELOCIDADES = [1, 1.25, 1.5, 2, .75];
    velocidad.addEventListener('click', function () {
      var v = VELOCIDADES[(VELOCIDADES.indexOf(video.playbackRate) + 1) % VELOCIDADES.length];
      video.playbackRate = v;
      var t = String(v).replace('.', ',') + 'x';
      velocidad.textContent = t;
      velocidad.setAttribute('aria-label', 'Velocidad de reproducción: ' + t);
    });
    pantalla.addEventListener('click', function () {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (caja.requestFullscreen) caja.requestFullscreen().catch(function () {});
      else if (video.webkitEnterFullscreen) video.webkitEnterFullscreen();
    });
    document.addEventListener('fullscreenchange', function () {
      var activa = document.fullscreenElement === caja;
      caja.classList.toggle('vp--completa', activa);
      dibujar(pantalla, activa ? I_REDUCIR : I_AMPLIAR, activa ? 'Salir de pantalla completa' : 'Pantalla completa');
    });
    caja.addEventListener('mousemove', mostrarControles);
    caja.addEventListener('touchstart', mostrarControles, { passive: true });
    caja.addEventListener('focusin', mostrarControles);
    caja.addEventListener('mouseleave', function () { if (!video.paused) caja.classList.add('vp--oculto'); });
    video.addEventListener('play', mostrarControles);
    caja.addEventListener('keydown', function (e) {
      if (e.target.tagName === 'INPUT' && (e.key.indexOf('Arrow') === 0)) return;
      if (e.target.tagName === 'BUTTON' && (e.key === ' ' || e.key === 'Enter')) return;
      if (e.key === ' ' || e.key === 'k') { e.preventDefault(); alternar(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); video.currentTime = Math.min(video.currentTime + 5, video.duration || 0); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); video.currentTime = Math.max(video.currentTime - 5, 0); }
      else if (e.key === 'm') sonido.click();
      else if (e.key === 'f') pantalla.click();
      else return;
      mostrarControles();
    });
    dibujar(pantalla, I_AMPLIAR, 'Pantalla completa');
    pintarPlay(); pintarSonido(); pintarTiempo(); pintarRango(linea);
  });

  /* ------------------------------------------------------------ Inicio de sesión: solo el logo cargando */
  var cargaLogo = document.querySelector('[data-carga-logo]');
  var formEntrar = document.querySelector('form[data-inicio-sesion]');
  if (cargaLogo && formEntrar) {
    formEntrar.addEventListener('submit', function (e) {
      var correo = formEntrar.querySelector('input[name="email"]'), clave = formEntrar.querySelector('input[name="password"]');
      if (e.defaultPrevented || !correo || !clave || !correo.value.trim() || !clave.value) return;
      cargaLogo.hidden = false;
      if (movimientoReducido.matches) return;
      e.preventDefault();  // un instante para que la carga se vea; luego se envía con normalidad
      setTimeout(function () { HTMLFormElement.prototype.submit.call(formEntrar); }, 550);
    });
  }

  /* ------------------------------------------------------------ Pantallas de carga con la estructura de cada página
     Aparecen solo si la página siguiente tarda; reutilizan las rejillas reales, así que son adaptables. */
  var esqueletos = (function () {
    function l(ancho, alto, clase) {
      return '<span class="sk' + (clase ? ' ' + clase : '') + '" style="width:' + (ancho || '100%') + ';height:' + (alto || '14px') + '"></span>';
    }
    function repetir(n, f) { var t = ''; for (var i = 0; i < n; i++) t += f(i); return t; }
    function tarjeta(c) { return '<div class="card"><div class="card-body sk-pila">' + c + '</div></div>'; }
    function encabezado(angosto) {
      return '<section class="hero hero--compact"><div class="container' + (angosto ? ' container--narrow' : '') + '"><div class="hero-row">' +
        '<span class="sk sk--claro hero-icon"></span><div class="sk-pila" style="flex:1;min-width:0">' + l('min(320px,70%)', '30px', 'sk--claro') + l('min(460px,90%)', '14px', 'sk--claro') + '</div></div></div></section>';
    }
    function campo() { return '<div class="field sk-pila sk-pila--corta">' + l('38%', '12px') + l('100%', '48px', 'sk--campo') + '</div>'; }
    function buscador(columnas, filas) {
      var f = (filas || []).map(function (g) { return '<div class="grid grid-' + g + '" style="margin-bottom:16px">' + repetir(g, campo) + '</div>'; }).join('');
      return '<div class="card card-elevated"><div class="card-body">' + f + '<div class="grid grid-' + columnas + '">' + repetir(columnas, campo) + '</div><div class="sk-fin">' + l('150px', '44px', 'sk--boton') + '</div></div></div>';
    }
    function oferta() {
      return '<article class="offer"><div class="offer-top sk-oferta-top"><span class="sk sk--claro" style="display:block;width:40px;height:40px;border-radius:12px"></span><div class="sk-pila" style="margin-top:12px">' + l('70%', '18px', 'sk--claro') + l('55%', '12px', 'sk--claro') + '</div></div>' +
        '<div class="offer-body"><div class="sk-pila">' + l('75%', '12px') + l('50%', '12px') + '</div><div class="offer-foot"><div class="sk-pila sk-pila--corta" style="width:40%">' + l('60%', '10px') + l('100%', '26px') + '</div>' + l('104px', '36px', 'sk--boton') + '</div></div></article>';
    }
    function ofertas(n) { return '<div class="cards-grid">' + repetir(n, oferta) + '</div>'; }
    function promo() { return '<article class="promo sk-pila">' + l('92px', '22px', 'sk--boton') + l('80%', '20px') + l('100%', '12px') + l('65%', '12px') + l('85%', '12px') + l('130px', '36px', 'sk--boton') + '</article>'; }
    function caracteristica() { return '<article class="feature sk-pila">' + l('46px', '46px', 'sk--icono') + l('60%', '18px') + l('100%', '12px') + l('80%', '12px') + '</article>'; }
    function fila() {
      return '<div class="req sk-fila"><span class="sk sk--icono" style="width:44px;height:44px;flex-shrink:0"></span><span class="sk-pila" style="flex:1;min-width:0">' + l('min(280px,80%)', '15px') + l('min(380px,95%)', '11px') + '</span>' + l('78px', '24px', 'sk--boton sk-oculto-movil') + '</div>';
    }
    function filas(n) { return '<div class="sk-pila sk-pila--filas">' + repetir(n, fila) + '</div>'; }
    function cabeceraSeccion() { return '<div class="section-head"><div class="sk-pila sk-pila--corta" style="flex:1">' + l('min(260px,70%)', '24px') + l('min(340px,90%)', '12px') + '</div></div>'; }
    function parrafo(n) { return repetir(n, function (i) { return l(i === n - 1 ? '60%' : '100%', '13px'); }); }
    function datos(n) { return '<div class="grid grid-3">' + repetir(n, function () { return '<div class="sk-pila sk-pila--corta">' + l('50%', '11px') + l('80%', '15px') + '</div>'; }) + '</div>'; }
    function chips(n) { return '<div class="sk-chips">' + repetir(n, function () { return l('84px', '34px', 'sk--boton'); }) + '</div>'; }
    function contenedor(c, angosto) { return '<div class="container' + (angosto ? ' container--narrow' : '') + ' lift">' + c + '</div>'; }
    function detalle(aside) {
      return encabezado() + contenedor('<div class="detail-grid"><div class="stack">' + tarjeta(l('45%', '20px') + parrafo(3) + datos(3)) + tarjeta(l('35%', '20px') + filas(3)) + '</div><aside class="stack">' + aside + '</aside></div>');
    }
    function formulario(grupos) {
      var c = '';
      for (var i = 0; i < grupos; i++) c += '<div class="sk-pila" style="margin-bottom:24px">' + l('180px', '18px') + '<div class="grid grid-2">' + repetir(4, campo) + '</div></div>';
      return encabezado(true) + contenedor('<div class="card card-elevated"><div class="card-body">' + c + '<div class="sk-fin">' + l('170px', '48px', 'sk--boton') + '</div></div></div>', true);
    }
    function listado(nChips, nFilas) { return encabezado() + contenedor(tarjeta(chips(nChips) + l('100%', '48px', 'sk--campo')) + '<div class="section">' + filas(nFilas) + '</div>'); }
    var T = {
      inicio: function () {
        return '<section class="hero hero--home"><div class="container sk-pila" style="gap:16px">' + l('190px', '13px', 'sk--claro') + l('min(620px,92%)', '50px', 'sk--claro') + l('min(460px,75%)', '50px', 'sk--claro') + l('min(560px,95%)', '15px', 'sk--claro') +
          '<div class="sk-chips" style="margin-top:12px">' + repetir(3, function () { return l('150px', '52px', 'sk--claro sk--boton'); }) + '</div></div></section>' +
          contenedor('<div class="cards-grid">' + repetir(3, caracteristica) + '</div><section class="section">' + cabeceraSeccion() + ofertas(3) + '</section>');
      },
      vuelos: function () { return encabezado() + contenedor(buscador(3, [2]) + '<section class="section">' + ofertas(6) + '</section>'); },
      paquetes: function () { return encabezado() + contenedor(buscador(4) + '<section class="section">' + ofertas(3) + '</section>'); },
      hospedaje: function () { return encabezado() + contenedor(buscador(3) + '<section class="section">' + ofertas(3) + '</section>'); },
      oferta: function () { return detalle(tarjeta(l('55%', '11px') + l('70%', '38px') + campo() + l('100%', '56px', 'sk--campo') + l('100%', '52px', 'sk--boton') + parrafo(3))); },
      promociones: function () { return encabezado() + contenedor('<div class="cards-grid">' + repetir(3, promo) + '</div>'); },
      promocion: function () { return encabezado() + contenedor('<div class="stack">' + tarjeta(parrafo(2) + datos(2)) + tarjeta(l('30%', '20px') + parrafo(2)) + '<section>' + cabeceraSeccion() + ofertas(3) + '</section></div>'); },
      visas: function () { return encabezado() + contenedor('<div class="cards-grid">' + repetir(3, caracteristica) + '</div><section class="section split"><div class="stack">' + tarjeta(l('55%', '20px') + parrafo(4)) + '</div><div>' + tarjeta(l('45%', '20px') + campo() + campo() + l('100%', '48px', 'sk--boton')) + '</div></section>'); },
      nosotros: function () { return encabezado() + contenedor('<div class="stack">' + tarjeta(l('30%', '22px') + parrafo(5)) + '<div class="grid grid-2">' + repetir(2, function () { return tarjeta(l('40%', '20px') + parrafo(3)); }) + '</div></div>'); },
      contacto: function () { return encabezado() + contenedor('<div class="split"><div>' + tarjeta(l('50%', '20px') + campo() + campo() + campo() + l('100%', '48px', 'sk--boton')) + '</div><div class="stack">' + tarjeta(l('40%', '20px') + parrafo(4)) + '</div></div>'); },
      preguntas: function () { return encabezado() + contenedor('<div class="faq">' + repetir(7, function () { return '<div class="faq-item" style="padding:16px">' + l('min(520px,85%)', '15px') + '</div>'; }) + '</div>', true); },
      legal: function () { return encabezado(true) + contenedor(tarjeta(repetir(4, function () { return l('45%', '20px') + parrafo(4); })), true); },
      cuenta: function () { return encabezado() + contenedor('<div class="stats">' + repetir(3, function () { return '<div class="stat sk-pila sk-pila--corta">' + l('50%', '28px') + l('85%', '11px') + '</div>'; }) + '</div><section class="section">' + cabeceraSeccion() + filas(3) + '</section><section class="section">' + cabeceraSeccion() + filas(2) + '</section>'); },
      filasCuenta: function () { return encabezado() + contenedor(filas(5)); },
      citas: function () { return encabezado() + contenedor('<div class="grid grid-2">' + repetir(4, function () { return tarjeta('<div style="display:flex;gap:14px"><span class="sk sk--icono" style="width:52px;height:56px;flex-shrink:0"></span><div class="sk-pila" style="flex:1">' + l('70%', '15px') + l('90%', '11px') + l('50%', '11px') + '</div></div>'); }) + '</div>'); },
      pagos: function () { return encabezado() + contenedor('<div class="detail-grid"><div class="stack">' + repetir(2, function () { return tarjeta(l('45%', '20px') + '<div class="money">' + repetir(3, function () { return '<div class="sk-pila sk-pila--corta">' + l('70%', '11px') + l('90%', '22px') + '</div>'; }) + '</div>' + filas(1)); }) + '</div><aside class="stack">' + tarjeta(l('55%', '20px') + campo() + campo() + campo() + l('100%', '64px', 'sk--campo') + l('100%', '48px', 'sk--boton')) + '</aside></div>'); },
      detalleCuenta: function () { return detalle(tarjeta(l('50%', '20px') + parrafo(3) + l('100%', '44px', 'sk--boton'))); },
      formulario2: function () { return formulario(2); },
      formulario1: function () { return formulario(1); },
      panel: function () {
        return encabezado() + contenedor('<div class="kpis">' + repetir(6, function () { return '<div class="kpi sk-pila">' + l('36px', '36px', 'sk--icono') + l('40%', '26px') + l('85%', '11px') + '</div>'; }) + '</div><div class="detail-grid section"><div class="stack">' + repetir(2, function () { return tarjeta(l('45%', '18px') + filas(2)); }) + '</div><aside class="stack">' + repetir(2, function () { return tarjeta(l('55%', '18px') + parrafo(3)); }) + '</aside></div>');
      },
      listaPanel: function () { return listado(4, 6); },
      listaSimple: function () { return listado(2, 7); },
      detallePanel: function () { return encabezado() + contenedor('<div class="sk-chips" style="margin-bottom:16px">' + repetir(5, function () { return l('96px', '34px', 'sk--boton'); }) + '</div><div class="detail-grid"><div class="stack">' + tarjeta(l('40%', '20px') + datos(6)) + tarjeta(l('35%', '20px') + filas(3)) + '</div><aside class="stack">' + tarjeta(l('55%', '18px') + campo() + l('100%', '44px', 'sk--boton')) + tarjeta(l('45%', '18px') + '<div class="money">' + repetir(3, function () { return l('100%', '64px', 'sk--campo'); }) + '</div>') + '</aside></div>'); },
      agenda: function () { return encabezado() + contenedor(tarjeta('<div class="sk-chips">' + repetir(3, function () { return l('170px', '40px', 'sk--campo'); }) + '</div>') + '<div class="section">' + filas(5) + '</div>'); },
      contenidoPanel: function () { return encabezado() + contenedor('<div class="cards-grid">' + repetir(6, caracteristica) + '</div>'); },
      entrar: function () {
        return '<div class="auth"><aside class="auth-aside"><div class="sk-pila" style="position:relative;margin:auto 0;max-width:380px;width:100%">' + l('60%', '34px', 'sk--claro') + l('90%', '14px', 'sk--claro') + l('75%', '14px', 'sk--claro') + '</div></aside>' +
          '<div class="auth-main"><div class="auth-card sk-pila" style="width:100%">' + l('55%', '30px') + l('75%', '13px') + campo() + campo() + l('100%', '52px', 'sk--boton') + l('60%', '13px') + '</div></div></div>';
      }
    };
    var RUTAS = [
      [/^\/$/, 'inicio'], [/^\/vuelos\/$/, 'vuelos'], [/^\/paquetes\/$/, 'paquetes'], [/^\/hospedaje\/$/, 'hospedaje'],
      [/^\/ofertas\/[^/]+\/$/, 'oferta'], [/^\/promociones\/$/, 'promociones'], [/^\/promociones\/\d+\/$/, 'promocion'],
      [/^\/visas\/$/, 'visas'], [/^\/nosotros\/$/, 'nosotros'], [/^\/contacto\/$/, 'contacto'], [/^\/preguntas-frecuentes\/$/, 'preguntas'],
      [/^\/(privacidad|terminos)\/$/, 'legal'], [/^\/(entrar|registro|recuperar)(\/.*)?$/, 'entrar'],
      [/^\/mi-cuenta\/$/, 'cuenta'], [/^\/mi-cuenta\/cotizar\/$/, 'formulario2'], [/^\/mi-cuenta\/perfil\/$/, 'formulario1'],
      [/^\/mi-cuenta\/(solicitudes|expedientes)\/$/, 'filasCuenta'], [/^\/mi-cuenta\/(solicitudes|expedientes)\/\d+\/$/, 'detalleCuenta'],
      [/^\/mi-cuenta\/citas\/$/, 'citas'], [/^\/mi-cuenta\/pagos\/$/, 'pagos'],
      [/^\/panel\/$/, 'panel'], [/^\/panel\/agenda\/$/, 'agenda'], [/^\/panel\/contenido\/$/, 'contenidoPanel'],
      [/^\/panel\/(expedientes\/nuevo|expedientes\/\d+\/editar|citas\/(nueva|\d+)|contenido\/agencia|contenido\/[^/]+\/(nuevo|\d+)|perfil)\/?$/, 'formulario1'],
      [/^\/panel\/(solicitudes|expedientes|clientes)\/\d+\/$/, 'detallePanel'],
      [/^\/panel\/(consultas|solicitudes|expedientes|documentos|pagos)\/$/, 'listaPanel'],
      [/^\/panel\/(clientes|personal|contenido\/[^/]+)\/$/, 'listaSimple']
    ];
    return {
      para: function (ruta) {
        for (var i = 0; i < RUTAS.length; i++) if (RUTAS[i][0].test(ruta)) return T[RUTAS[i][1]]();
        return null;
      },
      tipo: function (ruta) {
        for (var i = 0; i < RUTAS.length; i++) if (RUTAS[i][0].test(ruta)) return RUTAS[i][1];
        return null;
      }
    };
  })();

  var temporizadorCarga = null, restaurarCarga = null;
  function quitarEsqueleto() {
    clearTimeout(temporizadorCarga); clearTimeout(restaurarCarga);
    document.body.classList.remove('esq-activo');
    document.querySelectorAll('.esqueleto').forEach(function (n) { n.remove(); });
    var m = document.querySelector('main#contenido');
    if (m) m.removeAttribute('aria-busy');
    if (cargaLogo) cargaLogo.hidden = true;
  }
  function mostrarEsqueleto(ruta) {
    var html = esqueletos.para(ruta);
    if (!html) return;
    clearTimeout(temporizadorCarga);
    temporizadorCarga = setTimeout(function () {
      if (selectorAbierto) selectorAbierto.cerrar(false);
      var caja = el('div', 'esqueleto');
      caja.setAttribute('aria-hidden', 'true');
      caja.innerHTML = html;
      caja.dataset.tipo = esqueletos.tipo(ruta);
      var principal = document.querySelector('main#contenido');
      /* Las páginas de acceso y las que no comparten estructura ocupan toda la pantalla. */
      var completa = !principal || caja.dataset.tipo === 'entrar';
      if (completa) { caja.classList.add('esqueleto--completo'); document.body.appendChild(caja); }
      else { principal.setAttribute('aria-busy', 'true'); principal.appendChild(caja); document.body.classList.add('esq-activo'); }
      window.scrollTo(0, 0);
    }, 140);
    /* Si la navegación se cancela o falla, se devuelve la página actual. */
    restaurarCarga = setTimeout(quitarEsqueleto, 20000);
  }
  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a || (a.target && a.target !== '_self') || a.hasAttribute('download')) return;
    var url;
    try { url = new URL(a.href, location.href); } catch (err) { return; }
    if (url.origin !== location.origin) return;
    if (url.pathname === location.pathname && url.search === location.search) return;
    mostrarEsqueleto(url.pathname);
  });
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (e.defaultPrevented || !f || (f.method || 'get').toLowerCase() !== 'get') return;
    var url = new URL(f.action || location.href, location.href);
    if (url.origin === location.origin) mostrarEsqueleto(url.pathname);
  });
  /* Al volver con el botón Atrás, la página se restaura sin la carga. */
  window.addEventListener('pageshow', function (e) { if (e.persisted) quitarEsqueleto(); });
})();
