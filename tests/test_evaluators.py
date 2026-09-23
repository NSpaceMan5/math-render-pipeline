import numpy as np

from mrp.evaluators import registry
from mrp.evaluators.polar_loom import polar_loom


def test_registry_lists_polar_loom():
    assert "polar_loom" in registry.available()


def test_output_shape_and_dtype():
    arr = polar_loom(64, 48, rings=8)
    assert arr.shape == (48, 64, 3) and arr.dtype == np.uint8


def test_deterministic_bit_identical():
    a = polar_loom(96, 72, rings=10, twist=2.5)
    b = polar_loom(96, 72, rings=10, twist=2.5)
    assert np.array_equal(a, b)


def test_params_change_output():
    a = polar_loom(64, 64, rings=8, twist=1.0)
    b = polar_loom(64, 64, rings=8, twist=4.0)
    assert not np.array_equal(a, b)


def test_not_blank():
    assert polar_loom(128, 128, rings=16).std() > 5.0
