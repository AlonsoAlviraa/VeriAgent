"""Run demo/fixtures/live PDFs through run_fleet with Grok consult.

Loads .env without printing values. Unsets VERIFLEET_SKIP_LLM and Gemini
keys so consult() takes the xai_direct path. Writes runs/grok-live-fleet-latest.md.
"""

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

LIVE_DIR = ROOT / "demo" / "fixtures" / "live"


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _present(name: str) -> bool:
    return bool(os.getenv(name))


def _force_grok_path() -> None:
    """Unset skip flag and Gemini keys after dotenv/xai_direct setdefault."""
    os.environ.pop("VERIFLEET_SKIP_LLM", None)
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)


def run() -> int:
    _load_dotenv()
    os.environ.setdefault("VERIAGENT_AUTO_INIT_DB", "1")
    os.environ.setdefault("VERIFLEET_QUEUE_DISPATCH", "0")
    os.environ.pop("PUBSUB_TOPIC", None)
    os.environ.pop("VERIFLEET_PUBSUB_PUSH", None)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from ai_agents.adk.consult import skip_reason
    from ai_agents.adk.runtime import run_fleet
    from ai_agents.xai_direct import DEFAULT_MODEL
    from core_engine.db.database import Base
    import core_engine.db.models  # noqa: F401
    import core_engine.db.fleet_models  # noqa: F401
    import core_engine.control_plane.models  # noqa: F401
    import core_engine.auth.models  # noqa: F401

    # xai_direct._load_dotenv uses setdefault — pop Gemini *after* that import.
    _force_grok_path()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = ROOT / "runs" / f"{stamp}-grok-live-fleet"
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

    pdfs = sorted(p for p in LIVE_DIR.glob("*.pdf") if p.is_file())
    rows: list[dict] = []
    try:
        for idx, path in enumerate(pdfs):
            rel = path.relative_to(ROOT).as_posix()
            rec: dict = {
                "path": rel,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "tenant_id": "default",
                "roles": ["issuer"],
            }
            fid = f"live-{idx:02d}-{path.stem}"
            dest = upload_dir / f"{fid}.pdf"
            shutil.copy2(path, dest)
            rec["file_id"] = fid
            try:
                result = run_fleet(
                    db=db,
                    tenant_id="default",
                    roles=["issuer"],
                    user_id="grok-live",
                    file_id=fid,
                )
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
                        "memory_hits": result.memory_hits,
                        "adk_consult": (result.adk or {}).get("consult"),
                        "event_agents": [e.get("agent") for e in (result.events or [])],
                        "span_names": [s.get("name") for s in (result.spans or [])],
                    }
                )
            except Exception as exc:
                rec["error"] = f"{type(exc).__name__}: {exc}"
                rec["traceback"] = traceback.format_exc()
            rows.append(rec)
    finally:
        db.close()
        engine.dispose()

    consults = [r.get("adk_consult") or {} for r in rows]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_url": f"sqlite:///{db_path.as_posix()}",
        "verifleet_skip_llm": os.environ.get("VERIFLEET_SKIP_LLM"),
        "skip_reason": skip_reason(),
        "xai_model": DEFAULT_MODEL,
        "credentials": {
            "XAI_API_KEY": "present" if _present("XAI_API_KEY") else "missing",
            "GEMINI_API_KEY": "present" if _present("GEMINI_API_KEY") else "missing",
            "GOOGLE_API_KEY": "present" if _present("GOOGLE_API_KEY") else "missing",
            "GOOGLE_CLOUD_PROJECT": "present" if _present("GOOGLE_CLOUD_PROJECT") else "missing",
        },
        "pdf_count": len(pdfs),
        "grok_invoked": sum(1 for c in consults if c.get("invoked") and c.get("runner") == "xai_direct"),
        "rows": rows,
    }
    (out_dir / "state.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md = render_md(report)
    (out_dir / "report.md").write_text(md, encoding="utf-8")
    latest = ROOT / "runs" / "grok-live-fleet-latest.md"
    latest.write_text(md, encoding="utf-8")
    print(md)
    print(f"\nWrote {latest}")
    return 0 if report["grok_invoked"] == len(pdfs) and pdfs else 1


def render_md(report: dict) -> str:
    lines = [
        "# VeriFleet Grok live evidence",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Database: `{report['database_url']}`",
        f"- `VERIFLEET_SKIP_LLM`: `{report['verifleet_skip_llm']}` (unset → Grok path)",
        f"- `skip_reason()`: `{report['skip_reason']}`",
        f"- xAI model: `{report['xai_model']}`",
        f"- Credential presence (no values): `{report['credentials']}`",
        f"- Live PDFs: **{report['pdf_count']}**",
        f"- Grok consult invoked (`runner=xai_direct`): **{report['grok_invoked']}**",
        "",
        "Sources: `demo/fixtures/live/SOURCES.md` (public invoice2data VAT fixtures).",
        "Gemini keys were unset for this run so consult uses `ai_agents/xai_direct.py`.",
        "",
        "| Path | Decision | Signed | Consult invoked | Model | Runner | Recommendation | Reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report["rows"]:
        err = r.get("error")
        c = r.get("adk_consult") or {}
        decision = r.get("decision") or ("ERROR" if err else "")
        reason = (r.get("reason") or err or "").replace("|", "\\|")
        lines.append(
            f"| `{r['path']}` | **{decision}** | {r.get('signed')} | "
            f"{c.get('invoked')} | `{c.get('model', '')}` | `{c.get('runner', '')}` | "
            f"{c.get('recommendation')} | {reason} |"
        )
    lines.extend(["", "## Per-path detail", ""])
    for r in report["rows"]:
        lines.append(f"### `{r['path']}`")
        lines.append("")
        lines.append(f"- SHA-256: `{r['sha256']}` ({r['bytes']} bytes)")
        lines.append(f"- `file_id`: `{r.get('file_id')}`")
        lines.append(f"- Tenant `{r['tenant_id']}`, roles `{r.get('roles')}`")
        if r.get("error"):
            lines.append(f"- **Exception:** `{r['error']}`")
            lines.append("```")
            lines.append((r.get("traceback") or "").rstrip())
            lines.append("```")
        else:
            c = r.get("adk_consult") or {}
            text = (c.get("text") or "").replace("\n", " ").strip()
            lines.append(f"- `run_id`: `{r.get('run_id')}`")
            lines.append(f"- status `{r.get('status')}` decision **{r.get('decision')}** signed `{r.get('signed')}`")
            lines.append(f"- reason: {r.get('reason')}")
            lines.append(f"- invoice_id `{r.get('invoice_id')}` hash `{r.get('invoice_hash')}`")
            lines.append(f"- armor.allowed `{r.get('armor_allowed')}`")
            lines.append(f"- adk.consult.invoked `{c.get('invoked')}` model `{c.get('model')}` runner `{c.get('runner')}` framework `{c.get('framework')}`")
            lines.append(f"- adk.consult.recommendation `{c.get('recommendation')}` reason `{c.get('reason')}`")
            lines.append(f"- adk.consult.text: {text[:400]}")
            lines.append(f"- events: {r.get('event_agents')}")
            lines.append(f"- spans: {r.get('span_names')}")
        lines.append("")
    lines.extend(
        [
            "## Notes",
            "",
            "- Public PDFs are not VeriFactu JSON; auditor typically ESCALATEs on missing structured fields.",
            "- Consult still runs after the auditor and may tighten SIGN only; it cannot loosen gates.",
            "- No secret values from `.env` are written here.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(run())
