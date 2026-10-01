"""URLs de ficheros estáticos con huella de contenido.

``/static/css/tailwind.css`` no cambiaba de URL entre versiones, y el
navegador seguía usando la copia en caché después de un despliegue: el
2026-10-01 el calendario de fechas se pintaba sin estilos porque la hoja en
caché era anterior a sus clases. Con ``?v=<hash>`` la URL cambia cuando cambia
el contenido, y solo entonces.
"""

from __future__ import annotations

import hashlib
from functools import cache
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@cache
def static_url(path: str) -> str:
    """``static_url("css/tailwind.css")`` → ``/static/css/tailwind.css?v=<hash>``.

    La caché es por proceso: los estáticos van dentro de la imagen y no cambian
    mientras el servidor corre.
    """
    digest = hashlib.sha256((STATIC_DIR / path).read_bytes()).hexdigest()[:10]
    return f"/static/{path}?v={digest}"
