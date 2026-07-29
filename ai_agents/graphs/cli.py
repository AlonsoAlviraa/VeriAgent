"""
[AGENT-016 / Sprint 1-V2] ProductGraph CLI.

Uso:
    python -m ai_agents.graphs.cli run --goal "..." --prompt "..."
    python -m ai_agents.graphs.cli stream --goal "..." --prompt "..."
    python -m ai_agents.graphs.cli list
    python -m ai_agents.graphs.cli show --thread-id <id>
"""

from __future__ import annotations

import argparse
import json
import sys

from ai_agents.graphs.product_graph import DEFAULT_MAX_ITERATIONS
from ai_agents.graphs.runtime import (
    list_runs,
    load_run_state,
    new_thread_id,
    run_persistent,
    run_streaming,
)


def _cmd_run(args: argparse.Namespace) -> int:
    tid = args.thread_id or new_thread_id()
    print(f"[ProductGraph] Iniciando run {tid} ...", file=sys.stderr)
    result = run_persistent(
        goal=args.goal,
        mega_prompt=args.prompt,
        thread_id=tid,
        max_iterations=args.max_iter,
        save_artifacts=not args.no_artifacts,
    )
    meta = result.get("_meta", {})
    if args.json:
        out = {k: v for k, v in result.items() if k != "messages"}
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    else:
        print(result.get("final_report") or "[ProductGraph] Sin reporte (¿API keys configuradas?).")
    if meta.get("artifacts_dir"):
        print(f"\n[artifacts] {meta['artifacts_dir']}", file=sys.stderr)
    return 0


def _cmd_stream(args: argparse.Namespace) -> int:
    print(f"[ProductGraph] Streaming run ...", file=sys.stderr)
    for ev in run_streaming(
        goal=args.goal,
        mega_prompt=args.prompt,
        max_iterations=args.max_iter,
    ):
        snap = ev.state_snapshot
        print(
            f"[{ev.timestamp}] {ev.node}: status={snap.get('status')} "
            f"iter={snap.get('iteration')} score={snap.get('quality_score')}",
            file=sys.stderr,
        )
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    runs = list_runs()
    if not runs:
        print("(sin runs persistidas)")
        return 0
    if args.json:
        print(json.dumps(runs, ensure_ascii=False, indent=2))
    else:
        print(f"{'thread_id':<28} {'status':<10} {'score':<8} {'iter':<5} goal")
        for r in runs:
            print(
                f"{r['thread_id']:<28} {r['status']:<10} "
                f"{r['quality_score']:<8.2f} {r['iteration']:<5} {r['goal'][:40]}"
            )
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    state = load_run_state(args.thread_id)
    if state is None:
        print(f"Run no encontrada: {args.thread_id}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2, default=str))
    else:
        print(state.get("final_report") or state.get("report", "(sin reporte)"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="product-graph",
        description="ProductGraph CLI — grafo autónomo de generación de specs de producto.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Ejecuta el grafo y persiste artifacts.")
    p_run.add_argument("--goal", required=True, help="Objetivo de producto.")
    p_run.add_argument("--prompt", default="Investiga tendencias y oportunidades.", help="Mega-prompt de research.")
    p_run.add_argument("--thread-id", help="ID de run (default: autogenerado).")
    p_run.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITERATIONS)
    p_run.add_argument("--no-artifacts", action="store_true", help="No guardar artifacts a disco.")
    p_run.add_argument("--json", action="store_true", help="Output JSON del estado.")
    p_run.set_defaults(func=_cmd_run)

    p_stream = sub.add_parser("stream", help="Ejecuta emitiendo eventos por nodo.")
    p_stream.add_argument("--goal", required=True)
    p_stream.add_argument("--prompt", default="Investiga tendencias y oportunidades.")
    p_stream.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITERATIONS)
    p_stream.set_defaults(func=_cmd_stream)

    p_list = sub.add_parser("list", help="Lista runs persistidas.")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cmd_list)

    p_show = sub.add_parser("show", help="Muestra el reporte de una run.")
    p_show.add_argument("--thread-id", required=True)
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=_cmd_show)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
