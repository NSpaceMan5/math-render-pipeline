import numpy as np
from mrp.evaluators.harmonic_grid import harmonic_grid

def test_shape_and_dtype():
    arr = harmonic_grid(64, 48, nx=4, ny=3)
    assert arr.shape == (48, 64, 3) and arr.dtype == np.uint8

def test_deterministic():
    a = harmonic_grid(96, 72, nx=5, ny=4, phase=0.3)
    b = harmonic_grid(96, 72, nx=5, ny=4, phase=0.3)
    assert np.array_equal(a, b)

def test_params_change_output():
    a = harmonic_grid(64, 64, nx=4, ny=4)
    b = harmonic_grid(64, 64, nx=12, ny=4)
    assert not np.array_equal(a, b)

def test_not_blank():
    assert harmonic_grid(128, 128, nx=6, ny=5).std() > 5.0
