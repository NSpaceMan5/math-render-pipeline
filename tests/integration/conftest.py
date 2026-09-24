"""Fixtures for integration tests.

These tests require Docker (Colima, Docker Desktop, or a remote daemon).
In CI they run in a dedicated job. Locally they skip gracefully when
Docker is unavailable.
"""
from __future__ import annotations

import pytest


def _docker_available() -> bool:
    try:
        import docker
        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def postgres_container():
    if not _docker_available():
        pytest.skip("Docker daemon unavailable - skipping integration tests")
    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError:
        from testcontainers.postgres import PostgresContainer
    with PostgresContainer("postgres:16") as pg:
        yield pg


@pytest.fixture(scope="session")
def redpanda_container():
    if not _docker_available():
        pytest.skip("Docker daemon unavailable - skipping integration tests")
    try:
        from testcontainers.community.kafka import RedpandaContainer
    except ImportError:
        from testcontainers.kafka import RedpandaContainer
    with RedpandaContainer() as rp:
        yield rp


@pytest.fixture
def postgres_dsn(postgres_container):
    """Return a plain postgresql:// URL that psycopg accepts."""
    if hasattr(postgres_container, "get_connection_url"):
        url = postgres_container.get_connection_url()
        # testcontainers may return a SQLAlchemy URL with a driver suffix
        for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://"):
            if url.startswith(prefix):
                url = url.replace(prefix, "postgresql://", 1)
                break
        return url

    # Fallback for older testcontainers versions
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    c = getattr(postgres_container, "container", postgres_container)
    user = getattr(c, "username", "postgres")
    pw   = getattr(c, "password", "postgres")
    db   = getattr(c, "dbname", "postgres")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"
