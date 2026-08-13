"""Sweep invoice fixtures through run_fleet (SQLite, VERIFLEET_SKIP_LLM=1)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "sqlite:///verifleet_fixture_sweep.db")
os.environ["VERIAGENT_AUTO_INIT_DB"] = "1"
os.environ["VERIFLEET_SKIP_LLM"] = "1"
os.environ.setdefault("VERIFLEET_QUEUE_DISPATCH", "0")
os.environ.pop("PUBSUB_TOPIC", None)
os.environ.pop("VERIFLEET_PUBSUB_PUSH", None)

SEARCH_DIRS = (
    ROOT / "demo" / "fixtures",
    ROOT / "frontend" / "public" / "demo-fixtures",
    ROOT / "uploads",
)
INVOICE_SUFFIXES = {".json", ".pdf"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def discover() -> list[Path]:
    found: list[Path] = []
    for folder in SEARCH_DIRS:
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in INVOICE_SUFFIXES:
                found.append(path)
    return found


def expected_for(path: Path) -> dict:
    name = path.name.lower()
    if "injection" in name:
        return {
            "decision": "BLOCKED",
            "signed": False,
            "reason_contains": ["armor", "injection", "blocked"],
            "tenant_id": "default",
        }
    if "math" in name:
        return {
            "decision": "ESCALATED",
            "signed": False,
            "reason_contains": ["base+tax"],
            "tenant_id": "default",
        }
    if "hospitality" in name:
        return {
            "decision": "ESCALATED",
            "signed": False,
            "reason_contains": ["hospitality"],
            "tenant_id": "enterprise-demo",
        }
    if "valid" in name:
        return {
            "decision": "SIGNED",
            "signed": True,
            "reason_contains": ["auditor pass", "core_engine signed"],
            "tenant_id": "default",
        }
    return {
        "decision": None,
        "signed": None,
        "reason_contains": [],
        "tenant_id": "default",
    }


def reason_matches(reason: str, needles: list[str]) -> bool:
    blob = (reason or "").lower()
    return any(n.lower() in blob for n in needles) if needles else True


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run() -> int:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from ai_agents.adk.runtime import run_fleet
    from core_engine.db.database import Base
    import core_engine.db.models  # noqa: F401
    import core_engine.db.fleet_models  # noqa: F401
    import core_engine.control_plane.models  # noqa: F401
    import core_engine.auth.models  # noqa: F401

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = ROOT / "runs" / f"{stamp}-fixture-fleet"
    out_dir.mkdir(parents=True, exist_ok=True)

    upload_dir = out_dir / "uploads"
    upload_dir.mkdir()
    os.environ["UPLOAD_DIR"] = str(upload_dir)

    db_path = out_dir / "fleet.sqlite"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    fixtures = discover()
    rows: list[dict] = []
    failures = 0

    try:
        for idx, path in enumerate(fixtures):
            rel = path.relative_to(ROOT).as_posix()
            exp = expected_for(path)
            digest = _sha256(path)
            rec: dict = {
                "path": rel,
                "abs_path": str(path),
                "suffix": path.suffix.lower(),
                "bytes": path.stat().st_size,
                "sha256": digest,
                "expected_decision": exp["decision"],
                "expected_signed": exp["signed"],
                "tenant_id": exp["tenant_id"],
                "roles": ["issuer"],
                "ok": False,
            }
            try:
                kwargs: dict = {
                    "db": db,
                    "tenant_id": exp["tenant_id"],
                    "roles": ["issuer"],
                    "user_id": "fixture-sweep",
                }
                if path.suffix.lower() == ".json":
                    payload = load_json(path)
                    original_number = payload.get("number")
                    # Keep series/number unique on the shared SQLite hash chain.
                    payload["number"] = f"{original_number}-{idx:02d}"
                    rec["fixture_number"] = original_number
                    rec["run_number"] = payload["number"]
                    rec["input"] = "invoice=json"
                    result = run_fleet(invoice=payload, **kwargs)
                else:
                    fid = f"fix-{idx:02d}-{path.stem}"
                    dest = upload_dir / f"{fid}{path.suffix.lower()}"
                    shutil.copy2(path, dest)
                    rec["file_id"] = fid
                    rec["upload_copy"] = dest.as_posix()
                    rec["input"] = "file_id=pdf"
                    result = run_fleet(file_id=fid, **kwargs)

                rec.update(
                    {
                        "run_id": result.run_id,
                        "status": result.status,
                        "decision": result.decision,
                        "signed": result.signed,
                        "reason": result.reason,
                        "invoice_id": result.invoice_id,
                        "invoice_hash": result.invoice_hash,
                        "armor_allowed": (result.armor or {}).get("allowed"),
                        "armor_reasons": (result.armor or {}).get("reasons"),
                        "memory_hits": result.memory_hits,
                        "adk_consult": (result.adk or {}).get("consult"),
                        "denied_tools": result.denied_tools,
                        "event_agents": [e.get("agent") for e in (result.events or [])],
                        "span_names": [s.get("name") for s in (result.spans or [])],
                    }
                )
                decision_ok = result.decision == exp["decision"]
                signed_ok = result.signed is exp["signed"]
                reason_ok = reason_matches(result.reason, exp["reason_contains"])
                rec["ok"] = bool(decision_ok and signed_ok and reason_ok)
                rec["gate"] = {
                    "decision_ok": decision_ok,
                    "signed_ok": signed_ok,
                    "reason_ok": reason_ok,
                }
                if not rec["ok"]:
                    failures += 1
            except Exception as exc:
                failures += 1
                rec["error"] = f"{type(exc).__name__}: {exc}"
                rec["traceback"] = traceback.format_exc()
            rows.append(rec)
    finally:
        db.close()
        engine.dispose()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_url": f"sqlite:///{db_path.as_posix()}",
        "verifleet_skip_llm": os.environ.get("VERIFLEET_SKIP_LLM"),
        "fixture_count": len(fixtures),
        "pass_count": sum(1 for r in rows if r.get("ok")),
        "fail_count": failures,
        "search_dirs": [p.relative_to(ROOT).as_posix() for p in SEARCH_DIRS],
        "rows": rows,
    }
    (out_dir / "state.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (out_dir / "report.md").write_text(render_md(report), encoding="utf-8")
    latest = ROOT / "runs" / "fixture-fleet-latest.md"
    latest.write_text(render_md(report), encoding="utf-8")
    print(render_md(report))
    print(f"\nWrote {out_dir / 'report.md'}")
    return 0 if failures == 0 else 1


def render_md(report: dict) -> str:
    lines = [
        "# VeriFleet fixture evidence",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Database: `{report['database_url']}`",
        f"- `VERIFLEET_SKIP_LLM`: `{report['verifleet_skip_llm']}`",
        f"- Fixtures found: **{report['fixture_count']}**",
        f"- Pass: **{report['pass_count']}**  Fail: **{report['fail_count']}**",
        "",
        "Search dirs: " + ", ".join(f"`{d}`" for d in report["search_dirs"]),
        "",
        "| Path | Input | Tenant | Decision | Signed | Expected | OK | Reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report["rows"]:
        err = r.get("error")
        decision = r.get("decision") or ("ERROR" if err else "")
        signed = r.get("signed")
        expected = f"{r.get('expected_decision')}/signed={r.get('expected_signed')}"
        reason = (r.get("reason") or err or "").replace("|", "\\|")
        ok = "PASS" if r.get("ok") else "FAIL"
        lines.append(
            f"| `{r['path']}` | `{r.get('input', '')}` | `{r.get('tenant_id')}` | "
            f"**{decision}** | {signed} | {expected} | **{ok}** | {reason} |"
        )
    lines.extend(["", "## Per-path detail", ""])
    for r in report["rows"]:
        lines.append(f"### `{r['path']}`")
        lines.append("")
        lines.append(f"- SHA-256: `{r['sha256']}` ({r['bytes']} bytes)")
        lines.append(f"- Input mode: `{r.get('input')}`")
        if r.get("fixture_number") is not None:
            lines.append(f"- Fixture number `{r['fixture_number']}` → run number `{r.get('run_number')}`")
        if r.get("file_id"):
            lines.append(f"- `file_id`: `{r['file_id']}`")
        lines.append(f"- Tenant `{r['tenant_id']}`, roles `{r.get('roles')}`")
        if r.get("error"):
            lines.append(f"- **Exception:** `{r['error']}`")
            lines.append("```")
            lines.append((r.get("traceback") or "").rstrip())
            lines.append("```")
        else:
            lines.append(f"- `run_id`: `{r.get('run_id')}`")
            lines.append(f"- status `{r.get('status')}` decision **{r.get('decision')}** signed `{r.get('signed')}`")
            lines.append(f"- reason: {r.get('reason')}")
            lines.append(f"- invoice_id `{r.get('invoice_id')}` hash `{r.get('invoice_hash')}`")
            lines.append(f"- armor.allowed `{r.get('armor_allowed')}` reasons `{r.get('armor_reasons')}`")
            lines.append(f"- memory_hits `{r.get('memory_hits')}`")
            lines.append(f"- adk.consult `{r.get('adk_consult')}`")
            lines.append(f"- events: {r.get('event_agents')}")
            lines.append(f"- spans: {r.get('span_names')}")
            lines.append(f"- gate: `{r.get('gate')}`")
        lines.append("")
    lines.extend(
        [
            "## Gate policy",
            "",
            "- `valid_invoice.*` → **SIGNED** (issuer, tenant `default`)",
            "- `math_error.json` → **ESCALATED** (`Base+Tax != Total`)",
            "- `injection.json` → **BLOCKED** (Model Armor)",
            "- `hospitality.json` → **ESCALATED** (Memory Bank `deny_categories=hospitality` on `enterprise-demo`)",
            "- `uploads/` is scanned; empty dir is recorded as zero fixtures",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(run())
