"""
harmonograph — original formulation.

A harmonograph is a mechanical device: two pendulums swing a pen in a
damped Lissajous pattern. This module reproduces that trace numerically:

    x(t) = sin(f1·t + p1)·exp(-d1·t) + sin(f2·t + p2)·exp(-d2·t)
    y(t) = sin(f3·t + p3)·exp(-d3·t) + sin(f4·t + p4)·exp(-d4·t)

We sample t on a fixed grid, bin the (x, y) trace into a 2D histogram,
then map density to RGB. Deterministic given (n_samples, t_max) and the
parameter dict.

This is a different family from the other three:
    polar_loom     — polar harmonics with radial shear
    harmonic_grid  — Cartesian orthogonal harmonics
    moire_grid     — interference of two rotated lattices
    harmonograph   — damped Lissajous trace density
"""
from __future__ import annotations

import numpy as np

_EPS = 1e-12


def harmonograph(
    width: int,
    height: int,
    n_samples: int = 200_000,
    t_max: float = 80.0,
    f1: float = 2.01, f2: float = 3.00,
    f3: float = 2.99, f4: float = 3.00,
    d1: float = 0.020, d2: float = 0.030,
    d3: float = 0.025, d4: float = 0.020,
    p1: float = 0.0, p2: float = 0.5,
    p3: float = 1.0, p4: float = 1.5,
    gamma: float = 0.70,
    r_gain: float = 0.35,
    g_gain: float = 0.85,
    b_gain: float = 1.00,
) -> np.ndarray:
    """
    Render the harmonograph trace.

    Parameters
    ----------
    n_samples, t_max : trace resolution and duration
    f1..f4, d1..d4, p1..p4 : pendulum frequencies, dampings, phases
    gamma : density compression exponent (lower = brighter tails)
    r_gain, g_gain, b_gain : per-channel density multipliers
    """
    t = np.linspace(0.0, t_max, n_samples, dtype=np.float64)

    x = (np.sin(f1 * t + p1) * np.exp(-d1 * t)
         + np.sin(f2 * t + p2) * np.exp(-d2 * t))
    y = (np.sin(f3 * t + p3) * np.exp(-d3 * t)
         + np.sin(f4 * t + p4) * np.exp(-d4 * t))

    # normalize each axis to [-1, 1]
    x = x / (np.max(np.abs(x)) + _EPS)
    y = y / (np.max(np.abs(y)) + _EPS)

    # 2D histogram, fixed bins = output resolution
    hist, _, _ = np.histogram2d(
        y, x,
        bins=(height, width),
        range=[[-1.0, 1.0], [-1.0, 1.0]],
    )

    # gamma compression and normalization
    hist = np.power(hist, gamma)
    peak = float(hist.max())
    if peak < _EPS:
        hist = np.zeros_like(hist)
    else:
        hist = hist / peak

    R = hist * r_gain
    G = hist * g_gain
    B = hist * b_gain
    rgb = np.stack([R, G, B], axis=-1)
    return (np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)


DEFAULTS = {
    "n_samples": 200_000,
    "t_max": 80.0,
    "f1": 2.01, "f2": 3.00, "f3": 2.99, "f4": 3.00,
    "d1": 0.020, "d2": 0.030, "d3": 0.025, "d4": 0.020,
    "p1": 0.0, "p2": 0.5, "p3": 1.0, "p4": 1.5,
    "gamma": 0.70, "r_gain": 0.35, "g_gain": 0.85, "b_gain": 1.00,
}
