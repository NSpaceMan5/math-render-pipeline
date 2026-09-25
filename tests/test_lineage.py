"""Tests for the OpenLineage emitter.

We do not run a real Marquez here. The emitter is designed to be a no-op
when OPENLINEAGE_URL is unset, and to log-and-continue when it is set
but the server is unreachable.
"""
from unittest.mock import MagicMock, patch

import pytest

from mrp.lineage import LineageEmitter
from mrp.lineage import emitter as emitter_mod


def test_disabled_when_url_unset(monkeypatch):
    monkeypatch.delenv("OPENLINEAGE_URL", raising=False)
    e = LineageEmitter(url=None)
    assert e.enabled is False
    e.emit_render_start("polar_loom", "abc", "run-1")
    e.emit_render_complete("polar_loom", "abc", "rid", "file:///x", "run-1")
    e.emit_render_fail("polar_loom", "abc", "run-1")
    e.emit_consumer_event("rid", "render.events")


def test_enabled_when_url_set(monkeypatch):
    pytest.importorskip("openlineage.client")
    with patch.object(emitter_mod, "OpenLineageClient") as MockClient:
        MockClient.return_value = MagicMock()
        e = LineageEmitter(url="http://localhost:5000")
        assert e.enabled is True
        e.emit_render_start("polar_loom", "abc", "run-1")
        assert MockClient.return_value.emit.call_count == 1


def test_emit_swallows_errors(monkeypatch):
    pytest.importorskip("openlineage.client")
    with patch.object(emitter_mod, "OpenLineageClient") as MockClient:
        client = MagicMock()
        client.emit.side_effect = RuntimeError("boom")
        MockClient.return_value = client
        e = LineageEmitter(url="http://localhost:5000")
        # should not raise
        e.emit_render_start("polar_loom", "abc", "run-1")


def test_singleton(monkeypatch):
    monkeypatch.delenv("OPENLINEAGE_URL", raising=False)
    emitter_mod.reset_emitter()
    e1 = emitter_mod.get_emitter()
    e2 = emitter_mod.get_emitter()
    assert e1 is e2
    emitter_mod.reset_emitter()
    e3 = emitter_mod.get_emitter()
    assert e3 is not e1
