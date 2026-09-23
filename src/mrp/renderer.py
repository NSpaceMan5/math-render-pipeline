from __future__ import annotations
import hashlib, io, json, time, uuid
from PIL import Image
from .evaluators.registry import get
from .models import RenderSpec, RenderResult

_PREVIEW_MAX = 512

def _hash_spec(spec: RenderSpec) -> str:
    payload = json.dumps(
        {"formula": spec.formula_id, "params": spec.params,
         "w": spec.width, "h": spec.height, "s": spec.samples},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()

def render(spec: RenderSpec) -> tuple[RenderResult, bytes, bytes]:
    t0 = time.perf_counter()
    arr = get(spec.formula_id)(spec.width, spec.height, **spec.params)
    runtime_ms = int((time.perf_counter() - t0) * 1000)

    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True, compress_level=6)
    full_bytes = buf.getvalue()

    prev = img.copy()
    prev.thumbnail((_PREVIEW_MAX, _PREVIEW_MAX))
    pbuf = io.BytesIO()
    prev.save(pbuf, format="PNG", optimize=True, compress_level=9)
    preview_bytes = pbuf.getvalue()

    checksum = hashlib.sha256(full_bytes).hexdigest()
    fhash = _hash_spec(spec)
    render_id = f"{fhash[:16]}-{uuid.uuid4().hex[:8]}"

    result = RenderResult(
        render_id=render_id, formula_id=spec.formula_id,
        formula_hash=fhash, params_json=spec.params,
        width=spec.width, height=spec.height, runtime_ms=runtime_ms,
        checksum=checksum, storage_uri="", preview_uri="",
        bytes_full=len(full_bytes), bytes_preview=len(preview_bytes),
    )
    return result, full_bytes, preview_bytes
