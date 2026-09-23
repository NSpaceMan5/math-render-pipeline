from __future__ import annotations

from pathlib import Path

from .config import settings


def _s3_client():
    import boto3
    from botocore.client import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )


def put(render_id: str, full: bytes, preview: bytes) -> tuple[str, str]:
    if not settings.use_s3:
        root = Path(settings.artifact_root) / render_id
        root.mkdir(parents=True, exist_ok=True)
        f = root / "full.png"
        f.write_bytes(full)
        p = root / "preview.png"
        p.write_bytes(preview)
        return f"file://{f.resolve()}", f"file://{p.resolve()}"

    c = _s3_client()
    fkey = f"renders/{render_id}/full.png"
    pkey = f"renders/{render_id}/preview.png"
    c.put_object(Bucket=settings.s3_bucket, Key=fkey, Body=full, ContentType="image/png")
    c.put_object(Bucket=settings.s3_bucket, Key=pkey, Body=preview, ContentType="image/png")
    return f"s3://{settings.s3_bucket}/{fkey}", f"s3://{settings.s3_bucket}/{pkey}"
