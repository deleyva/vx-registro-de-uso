from __future__ import annotations

from cuid2 import Cuid

_generator = Cuid(length=24)


def create_id() -> str:
    """Generate a Prisma-compatible cuid (24 chars)."""
    return _generator.generate()
