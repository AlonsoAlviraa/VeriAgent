"""A/B tighten-only consult: 50 Grok vs 50 Gemini on math_error invoices.

Neither lane may SIGN a math_error invoice. Missing GEMINI_API_KEY → no-op GAP.
Never prints secret values.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def run_ab(
    *,
    per_lane: int = 50,
    manifest: Path | None = None,
    load_env: bool = True,
    lanes: tuple[str, ...] = ("gemini", "grok"),
) -> dict:
    if load_env:
        _load_dotenv()
    os.environ.setdefault("VERIAGENT_AUTO_INIT_DB", "1")
    os.environ.setdefault("VERIFLEET_QUEUE_DISPATCH", "0")
    prev_skip = os.environ.get("VERIFLEET_SKIP_LLM")
    os.environ.pop("VERIFLEET_SKIP_LLM", None)

    gemini = _present("GEMINI_API_KEY") or _present("GOOGLE_API_KEY")
    grok = _present("XAI_API_KEY")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "per_lane": per_lane,
        "gemini_key": "present" if gemini else "missing",
        "xai_key": "present" if grok else "missing",
        "noop": False,
        "gap": None,
        "lanes": {},
        "loosened": [],
        "ok": True,
    }
    def _restore_skip() -> None:
        if prev_skip is not None:
            os.environ["VERIFLEET_SKIP_LLM"] = prev_skip
        else:
            os.environ.pop("VERIFLEET_SKIP_LLM", None)

    if not gemini:
        report["noop"] = True
        report["gap"] = "GEMINI_API_KEY missing; A/B harness no-op. skip-llm soaks remain the gate."
        report["ok"] = True
        _restore_skip()
        return report

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from ai_agents.adk import consult as adk_consult
    from ai_agents.adk.runtime import run_fleet
    from core_engine.db.database import Base
    import core_engine.db.models  # noqa: F401
    import core_engine.db.fleet_models  # noqa: F401
    import core_engine.control_plane.models  # noqa: F401
    import core_engine.auth.models  # noqa: F401

    man_path = manifest or (ROOT / "demo" / "corpus" / "v1" / "manifest.json")
    if not man_path.exists():
        report["noop"] = True
        report["gap"] = "corpus manifest missing; generate corpus first"
        _restore_skip()
        return report
    items = json.loads(man_path.read_text(encoding="utf-8"))["items"]
    math_items = [i for i in items if i["class"] == "math_error"][:per_lane]
    if len(math_items) < per_lane:
        report["gap"] = f"only {len(math_items)} math_error invoices available (wanted {per_lane})"

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    def _timed_consult(name: str, payload: dict) -> dict:
        from ai_agents.adk import armor

        redacted, _hits = armor.redact_pii(armor.flatten_payload(payload))
        pool = ThreadPoolExecutor(max_workers=1)
        try:
            fut = pool.submit(
                original,
                redacted_invoice=redacted,
                memory={},
                auditor_draft="ESCALATED: Base+Tax mismatch",
                provider=name,
            )
            return fut.result(timeout=20)
        except FuturesTimeout:
            return {"invoked": False, "recommendation": None, "reason": "timeout", "runner": "none"}
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    original = adk_consult.consult

    def _lane(name: str) -> dict:
        signed = 0
        invoked = 0
        errors = 0
        miss = 0
        attempted = 0
        would_sign = 0
        decisions: dict[str, int] = {}
        recos: dict[str, int] = {}
        gap = None
        for item in math_items:
            payload = json.loads(Path(item["json"]).read_text(encoding="utf-8"))
            payload["number"] = f"{name[:1].upper()}{payload['number']}"
            attempted += 1
            try:
                os.environ.pop("VERIFLEET_SKIP_LLM", None)
                advice = _timed_consult(name, payload)
            except Exception as exc:
                errors += 1
                miss += 1
                if miss >= 3:
                    gap = "lane aborted after 3 consecutive consult failures"
                    break
                continue
            reco = advice.get("recommendation") or "none"
            recos[reco] = recos.get(reco, 0) + 1
            if advice.get("invoked"):
                invoked += 1
                miss = 0
            else:
                miss += 1
            if reco == "SIGN":
                would_sign += 1
            os.environ["VERIFLEET_SKIP_LLM"] = "1"
            result = run_fleet(
                db=db,
                tenant_id=f"ab-{name}",
                roles=["issuer"],
                user_id="ab",
                invoice=payload,
            )
            decisions[result.decision] = decisions.get(result.decision, 0) + 1
            if result.signed or result.decision == "SIGNED":
                signed += 1
                report["loosened"].append(
                    {
                        "lane": name,
                        "id": item["id"],
                        "decision": result.decision,
                        "signed": result.signed,
                        "recommendation": reco,
                    }
                )
            if miss >= 3 and invoked == 0:
                gap = "lane aborted: consult not invoked (rate-limit or provider error)"
                break
        return {
            "count": attempted,
            "wanted": len(math_items),
            "invoked": invoked,
            "signed": signed,
            "would_sign": would_sign,
            "errors": errors,
            "decisions": decisions,
            "recommendations": recos,
            "gap": gap,
        }

    try:
        if "gemini" in lanes:
            report["lanes"]["gemini"] = _lane("gemini")
        if "grok" in lanes:
            if grok:
                report["lanes"]["grok"] = _lane("grok")
            else:
                report["lanes"]["grok"] = {"gap": "XAI_API_KEY missing"}
    finally:
        db.close()
        engine.dispose()
        _restore_skip()

    report["ok"] = not report["loosened"]
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--per-lane", type=int, default=50)
    p.add_argument("--manifest", type=Path, default=None)
    p.add_argument("--out", type=Path, default=ROOT / "runs" / "consult-ab.json")
    p.add_argument("--lanes", default="gemini,grok", help="Comma-separated: gemini,grok")
    args = p.parse_args()
    report = run_ab(
        per_lane=args.per_lane,
        manifest=args.manifest,
        lanes=tuple(x.strip() for x in args.lanes.split(",") if x.strip()),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"ab_ok={report['ok']} noop={report['noop']} "
        f"gemini={report['gemini_key']} xai={report['xai_key']} "
        f"loosened={len(report['loosened'])} wrote {args.out}"
    )
    if report.get("gap"):
        print(f"GAP: {report['gap']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
