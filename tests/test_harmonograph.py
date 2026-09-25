import numpy as np

from mrp.evaluators.harmonograph import harmonograph


def test_shape_and_dtype():
    arr = harmonograph(64, 48, n_samples=10_000, t_max=10.0)
    assert arr.shape == (48, 64, 3) and arr.dtype == np.uint8


def test_deterministic():
    a = harmonograph(96, 72, n_samples=20_000, t_max=20.0)
    b = harmonograph(96, 72, n_samples=20_000, t_max=20.0)
    assert np.array_equal(a, b)


def test_params_change_output():
    a = harmonograph(64, 64, n_samples=10_000, f1=2.01, f2=3.00)
    b = harmonograph(64, 64, n_samples=10_000, f1=2.50, f2=3.00)
    assert not np.array_equal(a, b)


def test_not_blank():
    arr = harmonograph(128, 128, n_samples=50_000, t_max=40.0)
    assert int(arr.max()) - int(arr.min()) > 20
    assert arr.std() > 1.0
