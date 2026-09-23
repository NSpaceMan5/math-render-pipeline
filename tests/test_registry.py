from mrp.evaluators import registry


def test_two_formulas_registered():
    assert set(registry.available()) >= {"polar_loom", "harmonic_grid", "moire_grid"}


def test_defaults_present():
    for name in registry.available():
        d = registry.defaults(name)
        assert isinstance(d, dict) and len(d) > 0


def test_unknown_formula_raises():
    import pytest

    with pytest.raises(KeyError):
        registry.get("does_not_exist")
