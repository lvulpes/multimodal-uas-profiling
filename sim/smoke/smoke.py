"""Stage-1 smoke test: heartbeat received, arm, takeoff. Exits non-zero on failure.

python sim/smoke/smoke.py --profile px4_pymavlink
"""

from __future__ import annotations

import logging
import sys

from sitl import Session, TestFailure, connect_and_fly, run_test

log = logging.getLogger("smoke")


def body(s: Session) -> None:
    connect_and_fly(s)
    r = s.cfg["rtt"]
    rtts = s.gcs.measure_rtt(r["samples"], r["interval_s"], r["timeout_s"])
    got = sorted(x for x in rtts if x is not None)
    lost = len(rtts) - len(got)
    stats = {"n": len(rtts), "lost": lost}
    if got:
        stats.update(
            min=round(got[0], 3),
            p50=round(got[len(got) // 2], 3),
            p95=round(got[min(len(got) - 1, int(len(got) * 0.95))], 3),
            max=round(got[-1], 3),
        )
    s.summary["checks"]["rtt_ms"] = stats
    log.info("TIMESYNC RTT over %s: %s", s.link, stats)
    if lost > r["max_lost_fraction"] * len(rtts):
        raise TestFailure(f"{lost}/{len(rtts)} TIMESYNC requests unanswered")


if __name__ == "__main__":
    sys.exit(run_test("smoke", body))
