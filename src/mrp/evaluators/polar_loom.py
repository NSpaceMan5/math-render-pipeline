"""
polar_loom — original mathematical image formulation (this repo).
"""
from __future__ import annotations
import numpy as np

_EPS = 1e-12

def _normalize(a: np.ndarray) -> np.ndarray:
    lo, hi = float(a.min()), float(a.max())
    if hi - lo < _EPS:
        return np.zeros_like(a)
    return (a - lo) / (hi - lo)

def polar_loom(
    width: int,
    height: int,
    rings: int = 28,
    twist: float = 2.7,
    decay: float = 2.1,
    fold: float = 1.15,
    phi_r: float = 0.13,
    phi_g: float = 0.21,
    phi_b: float = 0.37,
    kappa_g: float = 0.50,
    kappa_b: float = 0.35,
) -> np.ndarray:
    u = np.linspace(-1.0, 1.0, width, dtype=np.float64)
    v = np.linspace(-1.0, 1.0, height, dtype=np.float64)
    U, V = np.meshgrid(u, v, indexing="xy")

    R = np.sqrt(U * U + V * V) + _EPS
    Theta = np.arctan2(V, U)
    env = np.exp(-decay * R)
    phase = twist * R * np.pi

    ch_r = np.zeros_like(R)
    ch_g = np.zeros_like(R)
    ch_b = np.zeros_like(R)

    for k in range(1, rings + 1):
        fk = float(k)
        wgt = env / (fk ** fold)
        ch_r += np.sin(fk * Theta + phase + phi_r * fk) * wgt
        ch_g += (np.cos((fk + 0.5) * Theta - phase + phi_g * fk)
                 * np.cos(kappa_g * R * np.pi * fk) * wgt)
        ch_b += (np.sin(fk * 0.75 * Theta + 1.3 * phase + phi_b * fk)
                 * np.sin(kappa_b * R * np.pi * fk) * wgt)

    rgb = np.stack([_normalize(ch_r), _normalize(ch_g), _normalize(ch_b)], axis=-1)
    return (rgb * 255.0).astype(np.uint8)

DEFAULTS = dict(rings=28, twist=2.7, decay=2.1, fold=1.15)
