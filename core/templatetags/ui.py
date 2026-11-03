from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def icon(name, size=20, cls=''):
    """Icono SVG del sprite (core/partials/icons.html)."""
    return format_html(
        '<svg class="icon {}" width="{}" height="{}" aria-hidden="true" focusable="false">'
        '<use href="#i-{}"></use></svg>', cls, size, size, name,
    )


@register.filter
def filesize(n):
    n = n or 0
    if n < 1024:
        return f'{n} B'
    if n < 1024 * 1024:
        return f'{n / 1024:.0f} KB'
    return f'{n / 1024 / 1024:.1f} MB'


@register.filter
def info_archivo(f):
    """«MP4 · 2,0 MB» para mostrar un archivo subido sin su ruta interna."""
    import os
    ext = os.path.splitext(getattr(f, 'name', '') or '')[1].lstrip('.').upper() or 'Archivo'
    try:
        return f"{ext} · {filesize(f.size).replace('.', ',')}"
    except (OSError, ValueError):
        return f'{ext} · no encontrado'
