from mrp.models import RenderSpec
from mrp.renderer import render
from mrp.streaming import event_from_result
from mrp.streaming.schemas import TOPIC, RenderEvent


def test_topic_name():
    assert TOPIC == "render.events"


def test_event_from_result_roundtrip():
    spec = RenderSpec(formula_id="polar_loom", width=48, height=48, params={"rings": 6})
    r, _, _ = render(spec)
    r.storage_uri = "file:///x.png"
    r.preview_uri = "file:///x_preview.png"
    ev = event_from_result(r)
    d = ev.model_dump()
    assert d["render_id"] == r.render_id
    assert d["formula_id"] == "polar_loom"
    assert d["ingest_source"] == "stream"
    assert len(d["event_id"]) == 32
    ev2 = RenderEvent(**d)
    assert ev2.render_id == ev.render_id
