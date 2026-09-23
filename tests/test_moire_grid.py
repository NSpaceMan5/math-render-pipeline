import numpy as np

from mrp.evaluators.moire_grid import moire_grid


def test_shape_and_dtype():
    arr = moire_grid(64, 48, f1=10, f2=10.5)
    assert arr.shape == (48, 64, 3) and arr.dtype == np.uint8


def test_deterministic():
    a = moire_grid(96, 72, f1=12, f2=12.4, angle=0.05)
    b = moire_grid(96, 72, f1=12, f2=12.4, angle=0.05)
    assert np.array_equal(a, b)


def test_params_change_output():
    a = moire_grid(64, 64, f1=10, f2=10.2, angle=0.02)
    b = moire_grid(64, 64, f1=10, f2=14.0, angle=0.40)
    assert not np.array_equal(a, b)


def test_not_blank():
    assert moire_grid(128, 128, f1=14, f2=14.6).std() > 5.0
