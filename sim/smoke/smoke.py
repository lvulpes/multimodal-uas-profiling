"""Stage-1 smoke test: heartbeat received, arm, takeoff. Exits non-zero on failure.

python sim/smoke/smoke.py --profile px4_pymavlink
"""

from __future__ import annotations

import sys

from sitl import Session, connect_and_fly, run_test


def body(s: Session) -> None:
    connect_and_fly(s)


if __name__ == "__main__":
    sys.exit(run_test("smoke", body))
