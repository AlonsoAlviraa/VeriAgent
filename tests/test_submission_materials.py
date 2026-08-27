"""Judge-facing English package: read the real files, drive /health twice."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_submission_materials_contain_required_phrases():
    contest = _read("CONTEST.md")
    readme = _read("README.md")
    script = _read("demo", "script.md")
    voice = _read("demo", "voiceover.md")
    blog = _read("demo", "blog.md")
    social = _read("demo", "social.md")
    judge = _read("demo", "judge.md")
    devpost = _read("demo", "devpost.md")

    assert "Fortified Enterprise Fleet" in contest
    assert "gemini-3.5-flash" in contest
    assert "google-adk" in contest
    assert "InMemoryRunner" in contest
    assert "pre-existing" in contest.lower()
    assert "cryptographic kernel" in contest.lower()

    assert "DATABASE_URL=sqlite:///verifleet.db" in readme or "sqlite:///verifleet.db" in readme
    assert "set DATABASE_URL" in readme or "DATABASE_URL" in readme

    assert "≤ 4 minutes" in script or "≤ 4:00" in script
    assert "≤ 4:00" in voice or "≤ 4 minutes" in voice
    assert "InMemoryRunner" in voice

    assert "created for the purposes of entering this hackathon" in blog
    assert "#AllThingsAgenticHackathon" in social
    assert "Fortified Enterprise Fleet" in devpost
    assert "gemini-3.5-flash" in devpost
    assert "sqlite:///verifleet.db" in judge

    bundle = "\n".join([contest, readme, script, voice, blog, social, judge, devpost])
    assert not re.search(
        r"https://[a-z0-9-]+\.[a-z0-9-]+\.run\.app",
        bundle,
        re.I,
    ), "do not invent a live Cloud Run URL in judge-facing docs"


def test_deploy_script_sets_sql_and_push_subscription():
    script = _read("infra", "deploy.sh")
    assert "DATABASE_URL=" in script
    assert "VERIFLEET_PUBSUB_PUSH=1" in script
    assert "/api/v1/fleet/pubsub/push" in script
    assert "invoice-received-push" in script
    assert "VERIFLEET_SKIP_LLM=1" in script
    assert "GEMINI_API_KEY=" not in script
    assert "XAI_API_KEY=" not in script
    assert "infra/cloudbuild.yaml" in script
    assert "--file Dockerfile.backend" not in script
    build = _read("infra", "cloudbuild.yaml")
    assert "Dockerfile.backend" in build


def test_health_stage_one_strings_twice():
    from core_engine.main import app

    client = TestClient(app)
    for _ in range(2):
        res = client.get("/health")
        assert res.status_code == 200
        blob = json.dumps(res.json())
        assert "gemini-3.5-flash" in blob
        assert "google-adk" in blob
        assert "InMemoryRunner" in blob


def test_compliance_http_lists_fleet_track_items():
    from core_engine.main import app

    client = TestClient(app)
    res = client.get(
        "/api/v1/fleet/compliance",
        headers={"X-Tenant-Id": "enterprise-demo", "X-Roles": "issuer"},
    )
    assert res.status_code == 200
    body = res.json()
    ids = {item["id"] for item in body["items"]}
    for needed in (
        "registry",
        "runtime",
        "memory",
        "identity",
        "gateway",
        "armor",
        "runner",
    ):
        assert needed in ids
