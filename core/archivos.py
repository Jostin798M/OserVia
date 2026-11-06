"""Entrega de archivos con soporte de rangos (permite adelantar y retroceder videos)."""
import mimetypes
import os
import re

from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect

RANGO = re.compile(r'bytes=(\d*)-(\d*)$')


def servir(request, fieldfile, nombre=None, descargar=False):
    if not fieldfile:
        raise Http404
    # Almacén remoto: la vista ya verificó el permiso; se entrega con un enlace firmado de corta duración.
    # El almacén atiende directamente los rangos de video y evita el límite de respuesta de Vercel.
    if hasattr(fieldfile.storage, 'enlace_firmado'):
        try:
            enlace = fieldfile.storage.enlace_firmado(fieldfile.name, descarga=nombre if descargar else None)
        except OSError:
            raise Http404
        r = HttpResponseRedirect(enlace)
        r['Cache-Control'] = 'private, no-store'
        r['Referrer-Policy'] = 'no-referrer'
        return r
    try:
        ruta = fieldfile.path
        total = os.path.getsize(ruta)
    except (FileNotFoundError, ValueError, NotImplementedError):
        raise Http404
    tipo = mimetypes.guess_type(nombre or ruta)[0] or 'application/octet-stream'
    m = RANGO.match(request.headers.get('Range', '').strip())
    if m and (m.group(1) or m.group(2)):
        inicio, fin = m.group(1), m.group(2)
        if inicio:
            inicio, fin = int(inicio), min(int(fin) if fin else total - 1, total - 1)
        else:
            inicio, fin = max(total - int(fin), 0), total - 1
        if inicio > fin or inicio >= total:
            r = HttpResponse(status=416)
            r['Content-Range'] = f'bytes */{total}'
            return r
        with open(ruta, 'rb') as fh:
            fh.seek(inicio)
            datos = fh.read(fin - inicio + 1)
        r = HttpResponse(datos, status=206, content_type=tipo)
        r['Content-Range'] = f'bytes {inicio}-{fin}/{total}'
        r['Accept-Ranges'] = 'bytes'
        r['Content-Length'] = str(len(datos))
        return r
    r = FileResponse(open(ruta, 'rb'), content_type=tipo, as_attachment=descargar,
                     filename=nombre or os.path.basename(ruta))
    r['Accept-Ranges'] = 'bytes'
    r['X-Content-Type-Options'] = 'nosniff'
    return r
