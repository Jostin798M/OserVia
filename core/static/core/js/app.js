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
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-theme-toggle]');
    if (!btn) return;
    var siguiente = temaActual() === 'dark' ? 'light' : 'dark';
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
  document.querySelectorAll('[data-show-when]').forEach(function (el) {
    var conds = el.getAttribute('data-show-when').split('|').map(function (c) { return c.split('='); });
    function sync() {
      el.hidden = !conds.some(function (c) { return valorRadio(c[0]) === c[1]; });
    }
    conds.forEach(function (c) {
      document.querySelectorAll('input[name="' + c[0] + '"]').forEach(function (r) { r.addEventListener('change', sync); });
    });
    sync();
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
    document.querySelectorAll('[data-tutorial-open]').forEach(function (b) {
      b.addEventListener('click', function () { tutorial.showModal(); video.play().catch(function () {}); });
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
      }
    }
    src.addEventListener('change', sync);
    sync();
  });
})();
