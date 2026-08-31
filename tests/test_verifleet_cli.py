"""CLI ingest uses the same run_fleet path as /fleet."""

from __future__ import annotations

from pathlib import Path

from verifleet.cli import format_ingest_line, ingest_path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "frontend" / "public" / "demo-fixtures" / "valid_invoice.json"


def test_cli_ingest_valid_invoice_json(db_session, monkeypatch, capsys):
    monkeypatch.setenv("GOOGLE_API_KEY", "sk-secret-should-never-print")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret-should-never-print")

    result = ingest_path(FIXTURE, db=db_session, tenant_id="default", roles=["issuer"])
    assert result.decision == "SIGNED"
    assert result.invoice_hash
    assert len(result.invoice_hash) > 16

    line = format_ingest_line(result.decision, result.invoice_hash)
    print(line)
    captured = capsys.readouterr()
    out = captured.out

    assert "SIGNED" in line
    assert result.invoice_hash[:8] in line
    assert result.invoice_hash[-8:] in line
    assert "…" in line
    assert result.invoice_hash not in line
    assert "sk-secret-should-never-print" not in out
    assert "gemini-secret-should-never-print" not in out
    assert "GOOGLE_API_KEY" not in out
    assert "GEMINI_API_KEY" not in out
