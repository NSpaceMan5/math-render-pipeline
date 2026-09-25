"""OpenLineage integration.

Emits run events (START / COMPLETE / FAIL) for the render job and the
consumer job. No-op unless OPENLINEAGE_URL is set, so CI and local dev
do not require a running Marquez.
"""
from .emitter import (
    LineageEmitter,
    get_emitter,
    reset_emitter,
)

__all__ = ["LineageEmitter", "get_emitter", "reset_emitter"]
