"""Fixtures for integration tests.

These tests require Docker (Colima, Docker Desktop, or a remote daemon).
In CI we run them in a dedicated job. Locally they skip gracefully when
Docker is unavailable.

Note: the `integration` marker is applied per-test-file via
`pytestmark = pytest.mark.integration` at module level. Putting it here
in conftest would have no effect — conftest has no test items.
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
    from testcontainers.postgres import PostgresContainer
    with PostgresContainer("postgres:16") as pg:
        yield pg


@pytest.fixture(scope="session")
def redpanda_container():
    if not _docker_available():
        pytest.skip("Docker daemon unavailable - skipping integration tests")
    from testcontainers.kafka import RedpandaContainer
    with RedpandaContainer() as rp:
        yield rp


@pytest.fixture
def postgres_dsn(postgres_container):
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.container.username
    pw   = postgres_container.container.password
    db   = postgres_container.container.dbname
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"
