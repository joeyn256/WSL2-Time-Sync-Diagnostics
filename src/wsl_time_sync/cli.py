from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyze import analyze_probe, load_json
from .compare import compare_paths
from .diagnose import collect_diagnosis
from .probe import run_probe
from .python_check import check_python
from .utils import write_json


def _emit(payload: dict, output: str | None) -> None:
    if output:
        write_json(output, payload)
        print(output)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wsl-time-sync",
        description="Read-only WSL2 timing diagnostics and offline analysis.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    diagnose = sub.add_parser("diagnose", help="Capture read-only environment metadata.")
    diagnose.add_argument("--output")

    probe = sub.add_parser("probe", help="Run a bounded guest-side timing probe.")
    probe.add_argument("--duration", type=float, default=30.0)
    probe.add_argument("--cadence", type=float, default=1.0)
    probe.add_argument("--output")

    analyze = sub.add_parser("analyze", help="Analyze a previously captured probe.")
    analyze.add_argument("input")
    analyze.add_argument("--output")

    compare = sub.add_parser("compare", help="Compare two analysis reports descriptively.")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.add_argument("--output")

    pycheck = sub.add_parser(
        "python-check",
        help="Report Python metadata and optionally check installed distributions.",
    )
    pycheck.add_argument("--requirements")
    pycheck.add_argument("--output")

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "diagnose":
        _emit(collect_diagnosis(), args.output)
        return 0

    if args.command == "probe":
        _emit(run_probe(args.duration, args.cadence), args.output)
        return 0

    if args.command == "analyze":
        _emit(analyze_probe(load_json(args.input)), args.output)
        return 0

    if args.command == "compare":
        _emit(compare_paths(args.left, args.right), args.output)
        return 0

    if args.command == "python-check":
        _emit(check_python(args.requirements), args.output)
        return 0

    return 2
