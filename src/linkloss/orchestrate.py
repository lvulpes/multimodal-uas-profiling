"""Run orchestration (stub). Real implementation arrives with the simulation POC.

Planned responsibilities: build the per-run environment from the profile/disruption/background YAML,
start Gazebo + flight SW + GS + OMNeT++, apply the disruption schedule, write data/raw/<run_id>/
(manifest.json, net.pcap, phy.parquet, events.jsonl), and mark runs INVALID on failed validation.
"""

from __future__ import annotations

import argparse
import sys

from linkloss.design import load_runs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").add_argument("phase", nargs="?")
    sub.add_parser("run").add_argument("run_id")
    sub.add_parser("run-phase").add_argument("phase")
    args = parser.parse_args()

    if args.cmd == "list":
        for r in load_runs(phase=args.phase):
            print(r.run_id)
        return 0

    print(f"TODO(POC): orchestration for '{args.cmd}' is not implemented yet.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
