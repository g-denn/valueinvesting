from __future__ import annotations

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_idea_radar.db"

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine


client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    db = Path("test_idea_radar.db")
    if db.exists():
        db.unlink()


def test_ingest_paste_and_feed_and_search():
    payload = {
        "source_name": "manual",
        "title": "Acme Corp",
        "text": """
Long thesis on ACME with strong cash generation.
- Margin expansion from mix shift
- Insider ownership aligns incentives
Primary catalyst is a new product cycle.
Main risk is execution on distribution.
Valuation at 8x EV/EBIT seems discounted.
""",
    }

    res = client.post("/documents/paste", json=payload)
    assert res.status_code == 200
    doc = res.json()
    assert doc["status"] == "INDEXED"
    assert doc["quality_score"] > 0

    feed = client.get("/feed")
    assert feed.status_code == 200
    assert len(feed.json()) >= 1

    search = client.get("/search", params={"q": "ACME"})
    assert search.status_code == 200
    assert len(search.json()["documents"]) >= 1


def test_get_idea_and_tag_and_digest():
    res = client.post(
        "/documents/paste",
        json={
            "source_name": "manual",
            "title": "Beta Inc",
            "text": "Long BETA because free cash flow yield is mispriced. Catalyst: buyback acceleration. Risk: cyclical demand.",
        },
    )
    assert res.status_code == 200

    idea = client.get("/ideas/1")
    assert idea.status_code == 200
    assert idea.json()["one_line_thesis"]

    tag = client.post("/ideas/1/tags", json={"tag": "gold", "note": "high signal"})
    assert tag.status_code == 200
    assert tag.json()["status"] == "ok"

    digest = client.get("/digests/weekly/latest")
    assert digest.status_code == 200
    assert "top_documents" in digest.json()
