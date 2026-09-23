"""
harmonic_grid — original Cartesian harmonic formulation (this repo).
"""

from __future__ import annotations

import math

import numpy as np


def harmonic_grid(
    width: int,
    height: int,
    nx: int = 6,
    ny: int = 4,
    phase: float = 0.0,
    skew: float = 0.0,
    mix: float = 0.5,
) -> np.ndarray:
    u = np.linspace(-1.0, 1.0, width, dtype=np.float64)
    v = np.linspace(-1.0, 1.0, height, dtype=np.float64)
    U, V = np.meshgrid(u, v, indexing="xy")
    if skew != 0.0:
        c, s = math.cos(skew), math.sin(skew)
        Us, Vs = U * c - V * s, U * s + V * c
    else:
        Us, Vs = U, V
    axis_a = np.sin(nx * np.pi * Us + phase)
    axis_b = np.cos(ny * np.pi * Vs + phase)
    diag = np.sin(nx * np.pi * Us + ny * np.pi * Vs)
    R = 0.5 + 0.5 * ((1.0 - mix) * axis_a + mix * diag)
    G = 0.5 + 0.5 * axis_b
    B = 0.5 + 0.5 * ((1.0 - mix) * (axis_a * axis_b) + mix * diag)
    rgb = np.stack([R, G, B], axis=-1)
    return (np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)


DEFAULTS = dict(nx=6, ny=4, phase=0.0, skew=0.0, mix=0.5)
