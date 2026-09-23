"""
moire_grid — original formulation.

Two sinusoidal grids with nearly-identical spatial frequency, one rotated
by a small angle, interfere to produce low-frequency moiré fringes. The
result is a beat pattern whose scale is set by the difference between the
two frequencies and the rotation angle, not by the grid pitch itself.

This is a different mathematical family from the other two formulas:
    polar_loom     — polar harmonics with radial shear
    harmonic_grid  — Cartesian orthogonal harmonics
    moire_grid     — interference / beat between two rotated lattices
"""
from __future__ import annotations

import math

import numpy as np

_EPS = 1e-12


def moire_grid(
    width: int,
    height: int,
    f1: float = 22.0,
    f2: float = 22.6,
    angle: float = 0.06,
    mix: float = 0.5,
    sharpen: float = 1.4,
) -> np.ndarray:
    """
    Parameters
    ----------
    f1, f2   : spatial frequencies of the two grids (cycles per unit)
    angle    : rotation of the second grid (radians); small values give
               wide moiré fringes
    mix      : blend between grid-1 only (0) and grid-2 only (1)
    sharpen  : tanh gain applied to the interference field; higher =
               crisper fringes, lower = softer
    """
    u = np.linspace(-1.0, 1.0, width, dtype=np.float64)
    v = np.linspace(-1.0, 1.0, height, dtype=np.float64)
    U, V = np.meshgrid(u, v, indexing="xy")

    # Grid 1: axis-aligned checkerboard in cosine form
    g1 = np.cos(f1 * np.pi * U) + np.cos(f1 * np.pi * V)

    # Grid 2: rotated by `angle`
    c, s = math.cos(angle), math.sin(angle)
    Ur = U * c - V * s
    Vr = U * s + V * c
    g2 = np.cos(f2 * np.pi * Ur) + np.cos(f2 * np.pi * Vr)

    # Interference / beat field
    field = (1.0 - mix) * g1 + mix * g2

    # Channel mapping: R = beat, G = grid1 envelope, B = grid2 envelope
    R = 0.5 + 0.5 * np.tanh(sharpen * field * 0.5)
    G = 0.5 + 0.5 * np.tanh(sharpen * g1    * 0.5)
    B = 0.5 + 0.5 * np.tanh(sharpen * g2    * 0.5)

    rgb = np.stack([R, G, B], axis=-1)
    return (np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)


DEFAULTS = {"f1": 22.0, "f2": 22.6, "angle": 0.06, "mix": 0.5, "sharpen": 1.4}
