from typing import Any

from pydantic import BaseModel, Field


class RenderSpec(BaseModel):
    formula_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    samples: int = Field(default=1, ge=1)


class RenderResult(BaseModel):
    render_id: str
    formula_id: str
    formula_hash: str
    params_json: dict[str, Any]
    width: int
    height: int
    runtime_ms: int
    checksum: str
    storage_uri: str
    preview_uri: str
    bytes_full: int
    bytes_preview: int
