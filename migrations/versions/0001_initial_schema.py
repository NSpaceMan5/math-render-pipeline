"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-25

Idempotent: uses CREATE TABLE / CREATE INDEX IF NOT EXISTS so it can be
applied on top of a database that was created by the pre-Alembic code
path (raw SQL in src/mrp/metadata.py). This is the standard pattern for
adopting Alembic on a live project.
"""
from alembic import op


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def upgrade() -> None:
    if _is_sqlite():
        op.execute("""
            CREATE TABLE IF NOT EXISTS render_events (
                render_id     TEXT PRIMARY KEY,
                formula_id    TEXT NOT NULL,
                formula_hash  TEXT NOT NULL,
                params_json   TEXT NOT NULL,
                width         INTEGER NOT NULL,
                height        INTEGER NOT NULL,
                runtime_ms    INTEGER NOT NULL,
                checksum      TEXT NOT NULL,
                storage_uri   TEXT NOT NULL,
                preview_uri   TEXT NOT NULL,
                bytes_full    INTEGER NOT NULL,
                bytes_preview INTEGER NOT NULL,
                ingest_source TEXT NOT NULL DEFAULT 'batch',
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
    else:
        op.execute("""
            CREATE TABLE IF NOT EXISTS render_events (
                render_id     TEXT PRIMARY KEY,
                formula_id    TEXT NOT NULL,
                formula_hash  TEXT NOT NULL,
                params_json   JSONB NOT NULL,
                width         INT NOT NULL,
                height        INT NOT NULL,
                runtime_ms    INT NOT NULL,
                checksum      TEXT NOT NULL,
                storage_uri   TEXT NOT NULL,
                preview_uri   TEXT NOT NULL,
                bytes_full    BIGINT NOT NULL,
                bytes_preview BIGINT NOT NULL,
                ingest_source TEXT NOT NULL DEFAULT 'batch',
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_render_events_formula "
        "ON render_events(formula_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_render_events_created "
        "ON render_events(created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_render_events_hash "
        "ON render_events(formula_hash)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_render_events_hash")
    op.execute("DROP INDEX IF EXISTS ix_render_events_created")
    op.execute("DROP INDEX IF EXISTS ix_render_events_formula")
    op.execute("DROP TABLE IF EXISTS render_events")
