"""Validación de archivos subidos: extensión, tamaño y contenido real (firma)."""
import os

from django import forms

MB = 1024 * 1024

FIRMAS = {
    '.pdf': [b'%PDF'],
    '.png': [b'\x89PNG\r\n\x1a\n'],
    '.jpg': [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
    '.mp4': [],   # contenedor ISO: se valida por 'ftyp' en el byte 4
    '.webm': [b'\x1a\x45\xdf\xa3'],
}

DOCUMENTOS_USUARIO = ('.pdf', '.png')                 # RS-07.2
COMPROBANTES = ('.pdf', '.png', '.jpg', '.jpeg')      # RS-10.2 (imagen o PDF)
ARCHIVOS_AGENCIA = ('.pdf', '.png', '.jpg', '.jpeg')
IMAGENES = ('.png', '.jpg', '.jpeg')
VIDEOS = ('.mp4', '.webm')


def _nombres(exts):
    return ', '.join(e.lstrip('.').upper() for e in exts if e != '.jpeg')


def validar_archivo(f, extensiones, max_mb=10):
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in extensiones:
        raise forms.ValidationError(f'«{f.name}» no es un formato permitido. Usa {_nombres(extensiones)}.')
    if f.size > max_mb * MB:
        raise forms.ValidationError(f'«{f.name}» pesa {f.size / MB:.1f} MB; el máximo es {max_mb} MB.')
    inicio = f.read(16)
    f.seek(0)
    if ext == '.mp4':
        valido = inicio[4:8] == b'ftyp'
    else:
        valido = any(inicio.startswith(s) for s in FIRMAS[ext])
    if not valido:
        raise forms.ValidationError(f'«{f.name}» está dañado o su contenido no corresponde a un archivo {ext.lstrip(".").upper()}.')
    return f


class ArchivoInput(forms.ClearableFileInput):
    """Muestra el archivo actual sin desbordar el formulario."""
    template_name = 'core/widgets/archivo.html'


class ArchivoField(forms.FileField):
    def __init__(self, *args, extensiones=ARCHIVOS_AGENCIA, max_mb=10, **kwargs):
        self.extensiones, self.max_mb = extensiones, max_mb
        kwargs.setdefault('widget', ArchivoInput(attrs={'accept': ','.join(extensiones)}))
        kwargs.setdefault('help_text', f'{_nombres(extensiones)} · máximo {max_mb} MB.')
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        f = super().clean(data, initial)
        if f and hasattr(f, 'size') and f is not initial:
            validar_archivo(f, self.extensiones, self.max_mb)
        return f
