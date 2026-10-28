"""Stage-2 harness: run the OMNeT++ socket bridge (sim/bridge, sim/omnetpp), summarise results.

The flight stack sends to the vehicle-side bridge port; the GCS-side bridge sends to the GCS port.
Results: c2.sca / c2.vec / c2.pcap in <log_dir>/omnetpp/.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from sitl import REPO, TestFailure

log = logging.getLogger("omnet")


def launch(
    cfg: dict[str, Any], log_dir: Path, vehicle_port: int, gcs_port: int
) -> subprocess.Popen:
    opp = cfg["omnetpp"]
    inet = Path(os.environ["INET_ROOT"]) / "src"
    result_dir = log_dir / "omnetpp"
    result_dir.mkdir()
    ini = REPO / opp["ini"]
    cmd = [
        "opp_run",
        "-u",
        "Cmdenv",
        "-c",
        opp["config"],
        "-n",
        f"{inet}:{REPO / opp['ned_path']}",
        "-l",
        str(inet / "INET"),
        "-l",
        str(REPO / opp["bridge_lib"]),
        f"--result-dir={result_dir}",
        f"--*.gcs.app[0].realPeerPort={gcs_port}",
        f"--*.uav.app[0].realBindPort={vehicle_port}",
        str(ini),
    ]
    log.info("launch omnetpp: %s", " ".join(cmd))
    out = (log_dir / "omnetpp.log").open("w")
    proc = subprocess.Popen(
        cmd,
        cwd=ini.parent,
        stdin=subprocess.DEVNULL,
        stdout=out,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    deadline = time.monotonic() + opp["ready_timeout_s"]
    while not _udp_port_bound(vehicle_port):
        if proc.poll() is not None:
            raise TestFailure(f"omnetpp exited with {proc.returncode} (see omnetpp.log)")
        if time.monotonic() > deadline:
            raise TestFailure(f"omnetpp did not bind UDP {vehicle_port} (see omnetpp.log)")
        time.sleep(0.2)
    log.info("omnetpp bridge ready on UDP %d", vehicle_port)
    return proc


def _udp_port_bound(port: int) -> bool:
    suffix = f":{port:04X}"
    with open("/proc/net/udp") as f:
        next(f)
        return any(line.split()[1].endswith(suffix) for line in f)


def stop(proc: subprocess.Popen, timeout_s: float) -> None:
    """SIGINT lets Cmdenv call finish(), which writes the scalars."""
    for sig in (signal.SIGINT, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout_s)
            return
        except subprocess.TimeoutExpired:
            log.warning("omnetpp did not stop on %s", sig.name)


def summarise(log_dir: Path) -> dict[str, Any]:
    result_dir = log_dir / "omnetpp"
    scalars = _read_scalars(result_dir / "c2.sca")
    vectors = _read_vectors(result_dir / "c2.vec")
    summary: dict[str, Any] = {"bridges": {}}
    for side in ("gcs", "uav"):
        module = f"C2Inet.{side}.app[0]"
        summary["bridges"][side] = {
            "from_real": int(scalars.get((module, "numFromReal"), 0)),
            "to_real": int(scalars.get((module, "numToReal"), 0)),
            "dropped": int(scalars.get((module, "numDropped"), 0)),
            "transit_ms": _stats_ms(vectors.get((module, "transitDelay:vector"), [])),
        }
    lag = [v for (_, name), vals in vectors.items() if name == "schedulerLag:vector" for v in vals]
    summary["scheduler_lag_ms"] = _stats_ms(lag)
    summary["scheduler_lag_ms"]["negative"] = sum(v < 0 for v in lag)
    return summary


def check(summary: dict[str, Any]) -> None:
    """Stage-2 pass criteria on the simulator side: traffic in both directions, lag recorded."""
    for side, b in summary["bridges"].items():
        if b["from_real"] == 0 or b["to_real"] == 0:
            raise TestFailure(f"no traffic through the {side} bridge in both directions: {b}")
    if summary["scheduler_lag_ms"]["n"] == 0:
        raise TestFailure("no scheduler lag samples recorded")


def _read_scalars(path: Path) -> dict[tuple[str, str], float]:
    out = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] == "scalar":
            out[(parts[1], parts[2])] = float(parts[3])
    return out


def _read_vectors(path: Path) -> dict[tuple[str, str], list[float]]:
    """Text .vec: `vector <id> <module> <name> ETV` declarations, `<id> <ev> <t> <v>` data."""
    names: dict[str, tuple[str, str]] = {}
    out: dict[tuple[str, str], list[float]] = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "vector":
            names[parts[1]] = (parts[2], parts[3])
        elif len(parts) == 4 and parts[0] in names:
            out.setdefault(names[parts[0]], []).append(float(parts[3]))
    return out


def _stats_ms(values_s: list[float]) -> dict[str, Any]:
    if not values_s:
        return {"n": 0}
    v = sorted(x * 1e3 for x in values_s)
    return {
        "n": len(v),
        "p50": round(v[len(v) // 2], 3),
        "p99": round(v[min(len(v) - 1, int(len(v) * 0.99))], 3),
        "max": round(v[-1], 3),
    }
