"""Property-based tests (Hypothesis) for all three formulas."""
import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from mrp.evaluators.harmonic_grid import harmonic_grid
from mrp.evaluators.moire_grid import moire_grid
from mrp.evaluators.polar_loom import polar_loom


def _shape_ok(arr, w, h):
    return arr.shape == (h, w, 3) and arr.dtype == np.uint8


@settings(max_examples=25, deadline=None)
@given(
    w=st.integers(min_value=32, max_value=96),
    h=st.integers(min_value=32, max_value=96),
    rings=st.integers(min_value=1, max_value=32),
    twist=st.floats(min_value=0.0, max_value=6.0),
    decay=st.floats(min_value=0.1, max_value=4.0),
    fold=st.floats(min_value=0.5, max_value=2.0),
)
def test_polar_loom_shape_and_determinism(w, h, rings, twist, decay, fold):
    a = polar_loom(w, h, rings=rings, twist=twist, decay=decay, fold=fold)
    b = polar_loom(w, h, rings=rings, twist=twist, decay=decay, fold=fold)
    assert _shape_ok(a, w, h)
    assert np.array_equal(a, b)


@settings(max_examples=25, deadline=None)
@given(
    w=st.integers(min_value=32, max_value=96),
    h=st.integers(min_value=32, max_value=96),
    nx=st.integers(min_value=1, max_value=20),
    ny=st.integers(min_value=1, max_value=20),
    phase=st.floats(min_value=-3.14, max_value=3.14),
    skew=st.floats(min_value=-1.5, max_value=1.5),
    mix=st.floats(min_value=0.0, max_value=1.0),
)
def test_harmonic_grid_shape_and_determinism(w, h, nx, ny, phase, skew, mix):
    a = harmonic_grid(w, h, nx=nx, ny=ny, phase=phase, skew=skew, mix=mix)
    b = harmonic_grid(w, h, nx=nx, ny=ny, phase=phase, skew=skew, mix=mix)
    assert _shape_ok(a, w, h)
    assert np.array_equal(a, b)


@settings(max_examples=25, deadline=None)
@given(
    w=st.integers(min_value=32, max_value=96),
    h=st.integers(min_value=32, max_value=96),
    f1=st.floats(min_value=4.0, max_value=40.0),
    f2=st.floats(min_value=4.0, max_value=40.0),
    angle=st.floats(min_value=-0.5, max_value=0.5),
    mix=st.floats(min_value=0.0, max_value=1.0),
    sharpen=st.floats(min_value=0.1, max_value=4.0),
)
def test_moire_grid_shape_and_determinism(w, h, f1, f2, angle, mix, sharpen):
    a = moire_grid(w, h, f1=f1, f2=f2, angle=angle, mix=mix, sharpen=sharpen)
    b = moire_grid(w, h, f1=f1, f2=f2, angle=angle, mix=mix, sharpen=sharpen)
    assert _shape_ok(a, w, h)
    assert np.array_equal(a, b)


@settings(max_examples=15, deadline=None)
@given(
    w=st.integers(min_value=48, max_value=96),
    h=st.integers(min_value=48, max_value=96),
)
def test_outputs_non_degenerate(w, h):
    for fn, kw in [
        (polar_loom,    {"rings": 8}),
        (harmonic_grid, {"nx": 4, "ny": 3}),
        (moire_grid,    {"f1": 10.0, "f2": 10.4}),
    ]:
        arr = fn(w, h, **kw)
        # Non-degenerate: cukup assert dynamic range cukup lebar
        # dan distribusi tidak konstan. Formula boleh tidak menyentuh 0/255.
        assert int(arr.max()) - int(arr.min()) > 20
        assert arr.std() > 1.0
