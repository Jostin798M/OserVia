"""Almacén de archivos en Supabase Storage (bucket privado) usando su API REST."""
import json
import mimetypes
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

TIEMPO_ESPERA = 30
VIGENCIA_ENLACE = 300  # segundos


@deconstructible
class AlmacenSupabase(Storage):
    def __init__(self, url=None, clave=None, bucket=None):
        self.base = f'{(url or settings.SUPABASE_URL).rstrip("/")}/storage/v1'
        self.clave = clave or settings.SUPABASE_SERVICE_KEY
        self.bucket = bucket or settings.SUPABASE_BUCKET

    def _ruta(self, nombre):
        return quote(f'{self.bucket}/{nombre}')

    def _pedir(self, metodo, ruta, datos=None, cabeceras=None):
        peticion = Request(f'{self.base}{ruta}', data=datos, method=metodo, headers={
            'Authorization': f'Bearer {self.clave}', **(cabeceras or {})})
        try:
            with urlopen(peticion, timeout=TIEMPO_ESPERA) as r:
                return r.read()
        except HTTPError as e:
            if e.code in (400, 404):
                raise FileNotFoundError(ruta) from e
            raise OSError(f'Supabase Storage respondió {e.code}') from e
        except URLError as e:
            raise OSError('No se pudo conectar con Supabase Storage') from e

    def _save(self, name, content):
        name = name.replace('\\', '/')
        content.seek(0)
        tipo = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        self._pedir('POST', f'/object/{self._ruta(name)}', content.read(), {'Content-Type': tipo})
        return name

    def _open(self, name, mode='rb'):
        return ContentFile(self._pedir('GET', f'/object/{self._ruta(name)}'), name=name)

    def _info(self, name):
        return json.loads(self._pedir('GET', f'/object/info/{self._ruta(name)}'))

    def exists(self, name):
        try:
            self._info(name)
            return True
        except FileNotFoundError:
            return False

    def size(self, name):
        return self._info(name)['size']

    def delete(self, name):
        try:
            self._pedir('DELETE', f'/object/{self._ruta(name)}')
        except FileNotFoundError:
            pass

    def enlace_firmado(self, name, descarga=None, segundos=VIGENCIA_ENLACE):
        cuerpo = json.dumps({'expiresIn': segundos}).encode()
        r = json.loads(self._pedir('POST', f'/object/sign/{self._ruta(name)}', cuerpo,
                                   {'Content-Type': 'application/json'}))
        enlace = f'{self.base}{r["signedURL"]}'
        return f'{enlace}&download={quote(descarga)}' if descarga else enlace

    def url(self, name):
        return self.enlace_firmado(name)
