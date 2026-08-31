"""Operator CLI — same run_fleet path as /fleet. Never prints secrets."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _short_hash(value: str | None) -> str:
    if not value:
        return "—"
    if len(value) <= 16:
        return value
    return f"{value[:8]}…{value[-8:]}"


def format_ingest_line(decision: str | None, invoice_hash: str | None) -> str:
    return f"{decision or '—'}  {_short_hash(invoice_hash)}"


def _stamp_number(invoice: dict) -> dict:
    out = dict(invoice)
    base = str(out.get("number") or "001")
    out["number"] = f"{base}-{int(time.time() * 1000) % 1_000_000:06d}"
    return out


def ingest_path(
    path: Path,
    *,
    db,
    tenant_id: str = "default",
    roles: Sequence[str] = ("issuer",),
    user_id: str = "cli",
):
    """Call the same runtime.run_fleet ingest as POST /api/v1/fleet/ingest."""
    from ai_agents.adk.runtime import run_fleet

    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(str(path))

    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON fixture must be an object")
        invoice = payload.get("invoice") if isinstance(payload.get("invoice"), dict) else payload
        return run_fleet(
            db=db,
            tenant_id=tenant_id,
            roles=list(roles),
            user_id=user_id,
            invoice=_stamp_number(dict(invoice)),
        )

    if suffix == ".pdf":
        upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_id = f"cli-{uuid.uuid4().hex[:12]}"
        dest = upload_dir / f"{file_id}.pdf"
        shutil.copyfile(path, dest)
        try:
            return run_fleet(
                db=db,
                tenant_id=tenant_id,
                roles=list(roles),
                user_id=user_id,
                file_id=file_id,
            )
        finally:
            dest.unlink(missing_ok=True)

    raise ValueError("ingest accepts a .json fixture or a .pdf")


def _open_db():
    os.environ.setdefault("DATABASE_URL", "sqlite:///verifleet.db")
    os.environ.setdefault("VERIAGENT_AUTO_INIT_DB", "1")
    from core_engine.db.database import SessionLocal, init_db

    init_db()
    return SessionLocal()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m verifleet",
        description="VeriFleet operator CLI. Same local ingest as /fleet. Does not print API keys.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    ingest_p = sub.add_parser("ingest", help="Ingest a JSON fixture or PDF through run_fleet")
    ingest_p.add_argument("path", help="Path to factura.pdf or a JSON fixture")
    ingest_p.add_argument("--tenant", default="default")
    ingest_p.add_argument("--role", default="issuer")
    args = parser.parse_args(argv)

    if args.cmd != "ingest":
        parser.error("unknown command")

    db = _open_db()
    try:
        result = ingest_path(
            Path(args.path),
            db=db,
            tenant_id=args.tenant,
            roles=[args.role],
        )
    except FileNotFoundError as exc:
        print(f"not found: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    finally:
        db.close()

    print(format_ingest_line(result.decision, result.invoice_hash))
    return 0 if result.decision else 1


if __name__ == "__main__":
    raise SystemExit(main())
