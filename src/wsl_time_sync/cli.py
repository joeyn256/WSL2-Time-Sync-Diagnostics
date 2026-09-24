from __future__ import annotations

import argparse
import json

from .analyze import analyze_probe, load_json
from .compare import compare_paths
from .diagnose import collect_diagnosis
from .probe import run_probe
from .python_check import check_python
from .settle import run_settle_check
from .utils import write_json


def _emit(payload: dict, output: str | None) -> None:
    if output:
        write_json(output, payload)
        print(output)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wsl-time-sync",
        description="Read-only WSL2 timing diagnostics and offline analysis.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    diagnose = sub.add_parser("diagnose", help="Capture read-only environment and adjtimex metadata.")
    diagnose.add_argument("--output")
    probe = sub.add_parser("probe", help="Run a bounded RAW-bracketed guest-side timing probe.")
    probe.add_argument("--duration", type=float, default=30.0)
    probe.add_argument("--cadence", type=float, default=1.0)
    probe.add_argument("--output")
    analyze = sub.add_parser("analyze", help="Analyze a v1 or v2 probe using fixed windows.")
    analyze.add_argument("input")
    analyze.add_argument("--window", type=float, default=10.0, help="Fixed-window seconds (default: 10).")
    analyze.add_argument("--rate-band-ppm", type=float, default=100.0, help="Example symmetric rate band (default: 100 ppm).")
    analyze.add_argument("--event-threshold-ns", type=int, default=500_000_000, help="Example realtime-minus-RAW change band (default: 500000000 ns).")
    analyze.add_argument("--output")
    compare = sub.add_parser("compare", help="Compare analysis reports after checking method context.")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.add_argument("--output")
    settle = sub.add_parser("settle-check", help="Observe a finite example kernel-state policy; never certify readiness.")
    settle.add_argument("--duration", type=float, default=30.0)
    settle.add_argument("--cadence", type=float, default=1.0)
    settle.add_argument("--expected-tick", type=int, default=10000)
    settle.add_argument("--max-abs-freq-ppm", type=float, default=100.0)
    settle.add_argument("--required-consecutive", type=int, default=3)
    settle.add_argument("--output")
    pycheck = sub.add_parser("python-check", help="Report Python metadata and optionally check installed distributions.")
    pycheck.add_argument("--requirements")
    pycheck.add_argument("--output")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "diagnose":
            payload = collect_diagnosis()
        elif args.command == "probe":
            payload = run_probe(args.duration, args.cadence)
        elif args.command == "analyze":
            payload = analyze_probe(load_json(args.input), window_s=args.window,
                                    rate_band_ppm=args.rate_band_ppm,
                                    event_threshold_ns=args.event_threshold_ns)
        elif args.command == "compare":
            payload = compare_paths(args.left, args.right)
        elif args.command == "settle-check":
            payload = run_settle_check(args.duration, args.cadence, expected_tick=args.expected_tick,
                                       max_abs_freq_ppm=args.max_abs_freq_ppm,
                                       required_consecutive=args.required_consecutive)
        else:
            payload = check_python(args.requirements)
        _emit(payload, args.output)
    except OverflowError:
        parser.error("numeric input is outside the supported finite range")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0
