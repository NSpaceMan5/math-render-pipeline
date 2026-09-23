from mrp.models import RenderSpec
from mrp.renderer import render


def test_render_hash_stable():
    spec = RenderSpec(
        formula_id="polar_loom", width=64, height=64, params={"rings": 8, "twist": 2.0}
    )
    r1, b1, p1 = render(spec)
    r2, b2, p2 = render(spec)
    assert r1.formula_hash == r2.formula_hash
    assert b1 == b2 and p1 == p2


def test_checksum_sha256_hex():
    r, _, _ = render(RenderSpec(formula_id="polar_loom", width=48, height=48, params={"rings": 6}))
    assert len(r.checksum) == 64
    assert all(c in "0123456789abcdef" for c in r.checksum)


def test_preview_smaller():
    r, full, prev = render(
        RenderSpec(formula_id="polar_loom", width=1024, height=768, params={"rings": 12})
    )
    assert len(prev) < len(full) and r.bytes_preview < r.bytes_full
