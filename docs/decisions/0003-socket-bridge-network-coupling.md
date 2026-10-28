# 0003 — Couple GCS and flight software to OMNeT++ through a UDP socket bridge

Status: proposed (not implemented; stage 2 of docs/poc-plan.md)
Touches: sim, H1, H2, H3

## Context
The C2 traffic between the real GCS and flight software must pass through the simulated network
(INET, later Simu5G) so that disruptions and radio conditions act on it. The usual way is an emulation
interface (TAP device or raw sockets inside a network namespace per run). In this sandbox that is not
available, verified on 2026-10-28 inside the container:
- `unshare -n true` and `unshare -rn true` fail with "Operation not permitted";
- `/dev/net/tun` does not exist; effective capabilities are empty; a seccomp filter is active.

## Decision
GCS and flight software talk plain UDP over loopback, with per-run port numbers. A small OMNeT++ module
(the "socket bridge", `sim/bridge/`) owns those sockets, injects each datagram into the simulated network
as an application payload, and delivers it at the far end back to the real socket. OMNeT++ runs under the
real-time scheduler. The pcap is recorded on the simulator side.

Stage 1 already uses the same shape with an in-process Python UDP relay standing in for the network
(`sim/smoke/sitl.py`, `UdpRelay`); the bridge replaces that relay.

## Alternatives considered
- **TAP/namespace emulation** (INET `ExtInterface`-style): real kernel L2/L3 path, but needs the
  capabilities above. Upgrade path: a custom seccomp profile allowing namespaces + `/dev/net/tun` + the
  narrowest capability set (`NET_ADMIN`), set in `compose.yaml` for the sim/campaign service only.
- **Shaping the loopback with tc/netem**: needs `NET_ADMIN` too, and gives no Simu5G radio layer.
- **Relay in Python only**: no simulated network, so no L1 metrics; fine for stage 1, not for H2.

## Consequences
- **Trade-off:** L2/L3 headers in the capture are produced by the simulator (INET/Simu5G), not by the real
  kernel stack. Application-level behaviour stays real: MAVLink timing, retries, heartbeat cadence and
  failsafe reactions come from the actual GCS and flight software. Network features (burstiness,
  inter-arrival time, retransmission cadence) are measured on simulator-side packets; anything that
  depends on real kernel/socket behaviour (kernel buffering, real IP/UDP header fields) is lost.
  **To check with the supervisor** before stage 4 that this is acceptable for the network features.
- Real-time scheduler lag adds to inter-arrival times; it must be logged per run (stage 2 criterion).
- Per-run ports must be configurable on both stacks. Stage 1 found PX4's GCS link sends to a fixed
  remote port 14550 (`px4-rc.mavlink`, no `-o`), independent of the instance number. Parallel PX4 runs
  therefore need an override of that startup line or one run at a time. Unverified for ArduPilot beyond
  `--serialN udpclient:<ip>:<port>`, which worked in stage 1.
- Gazebo's gz-transport uses multicast discovery, which the sandbox firewall drops; `GZ_IP=127.0.0.1`
  is required (verified in stage 1) and `GZ_PARTITION` per run keeps parallel worlds apart.
- Label leakage (CLAUDE.md rule 4): per-run port numbers must not correlate with the profile in features.
