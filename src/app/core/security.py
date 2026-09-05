"""Hashing de contraseñas con la biblioteca estándar.

Usamos ``hashlib.scrypt`` en lugar de passlib/bcrypt para no añadir
dependencias: el proyecto solo suma ``itsdangerous`` (que exige
``SessionMiddleware``) al instalar la autenticación.

Formato almacenado: ``scrypt$N$r$p$<sal-b64>$<derivada-b64>``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_PREFIX = "scrypt"
_N = 2**14
_R = 8
_P = 1
_DKLEN = 32
_SALT_BYTES = 16


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=_DKLEN
    )


def hash_password(password: str) -> str:
    """Devuelve la representación almacenable de ``password``."""
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = _derive(password, salt, _N, _R, _P)
    return "$".join([_PREFIX, str(_N), str(_R), str(_P), _b64(salt), _b64(derived)])


def verify_password(password: str, encoded: str | None) -> bool:
    """Comprueba ``password`` contra un valor generado por ``hash_password``.

    Devuelve ``False`` ante cualquier valor mal formado en lugar de lanzar:
    un registro corrupto en la base de datos no debe tumbar el login, solo
    denegar el acceso.
    """
    if not password or not encoded:
        return False
    parts = encoded.split("$")
    if len(parts) != 6 or parts[0] != _PREFIX:
        return False
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = base64.b64decode(parts[4])
        expected = base64.b64decode(parts[5])
    except (ValueError, TypeError):
        return False
    try:
        derived = _derive(password, salt, n, r, p)
    except ValueError:
        return False
    return hmac.compare_digest(derived, expected)


def constant_time_equals(a: str, b: str) -> bool:
    """Comparación de cadenas resistente a temporización."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def fingerprint(value: str) -> str:
    """Huella corta y estable de un secreto, apta para guardar en la sesión.

    Se guarda en la cookie para que, si la clave de administración cambia en
    el entorno, las sesiones de administrador abiertas dejen de validar.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
