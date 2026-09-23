from collections.abc import Callable
from typing import Any

import numpy as np

from .harmonic_grid import DEFAULTS as _HG_DEFAULTS
from .harmonic_grid import harmonic_grid
from .polar_loom import DEFAULTS as _PL_DEFAULTS
from .polar_loom import polar_loom

Evaluator = Callable[..., np.ndarray]

_REGISTRY: dict[str, tuple[Evaluator, dict[str, Any]]] = {
    "polar_loom": (polar_loom, _PL_DEFAULTS),
    "harmonic_grid": (harmonic_grid, _HG_DEFAULTS),
}


def get(name: str) -> Evaluator:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown formula: {name}. Available: {list(_REGISTRY)}")
    return _REGISTRY[name][0]


def defaults(name: str) -> dict[str, Any]:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown formula: {name}")
    return dict(_REGISTRY[name][1])


def available() -> list[str]:
    return sorted(_REGISTRY)
