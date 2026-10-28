"""Stage-1 link-loss test: fly, cut the C2 link (both directions), check the failsafe fires.

Pass = the vehicle enters the profile's failsafe.expected_mode within failsafe.timeout_s +
failsafe_margin_s after the cut, as seen on the passive monitor link. The cut-to-mode delay is
recorded in summary.json (relevant to H4; a single run, not a measurement campaign).

    python sim/smoke/failsafe.py --profile ardupilot_pymavlink
"""

from __future__ import annotations

import logging
import sys
import time

from sitl import Session, TestFailure, connect_and_fly, mode_of, run_test

log = logging.getLogger("failsafe")


def body(s: Session) -> None:
    connect_and_fly(s)
    fs = s.profile["failsafe"]
    expected = fs["expected_mode"]
    s.gcs.wait_for_quietly(lambda: False, s.cfg["hover_s"])  # hover, keep GCS state fresh
    mode_before = mode_of(s.gcs.state.heartbeat)
    if mode_before == expected:
        raise TestFailure(f"already in {expected} before the cut")
    if not s.monitor.mode_changes:
        raise TestFailure("monitor link saw no vehicle heartbeat; cannot observe the failsafe")

    t_cut = time.time()
    s.relay.cut.set()
    log.info("C2 link cut (mode %s)", mode_before)
    window = fs["timeout_s"] + s.cfg["failsafe_margin_s"]
    deadline = time.monotonic() + window
    fired = None
    while fired is None and time.monotonic() < deadline:
        time.sleep(0.2)
        fired = next(
            ((t, m) for t, m in s.monitor.mode_changes if t >= t_cut and m == expected), None
        )
    s.summary["checks"]["cut"] = {
        "t_cut": t_cut,
        "mode_before": mode_before,
        "modes_after_cut": [
            (round(t - t_cut, 2), m) for t, m in s.monitor.mode_changes if t >= t_cut
        ],
    }
    if fired is None:
        raise TestFailure(f"no {expected} within {window:.0f} s of the cut")
    delay = fired[0] - t_cut
    s.summary["checks"]["failsafe"] = {"mode": expected, "delay_s": round(delay, 2)}
    log.info("failsafe fired: %s after %.1f s", expected, delay)
    stats = s.relay.stats
    if stats.up_drop == 0 or stats.down_drop == 0:
        raise TestFailure(f"cut did not drop traffic in both directions: {stats}")


if __name__ == "__main__":
    sys.exit(run_test("failsafe", body))
