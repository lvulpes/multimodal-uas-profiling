# 0003 — Couple GCS and flight software to OMNeT++ through a UDP socket bridge

Status: proposed (implemented for plain INET in stage 2, 2026-10-28)
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

## Implementation notes (stage 2)
- `sim/bridge/UdpSocketBridge` (INET app, shared library built by `make sim-build`) owns one real UDP
  socket registered with `inet::RealTimeScheduler`; network `sim/omnetpp/C2Inet.ned` is GCS host –
  router – UAV host over Ethernet (1 ms, 100 Mbps per link, set in `omnetpp.ini`). Real-side ports come
  from the harness on the command line (`sim/smoke/omnet.py`), not from the ini.
- **Scheduler lag** = wall clock since the scheduler's base time minus simulation time, recorded at every
  bridge event and every 100 ms. First runs (one per stack): p50 0.09–0.13 ms, p99 0.35–0.37 ms, max
  1.3–2.1 ms. One negative sample per run is a shutdown artifact: SIGINT interrupts the scheduler's
  `select()` and INET then runs the next event early. Single runs on one machine; not a characterisation.
- **RTT** is measured at application level with MAVLink TIMESYNC (GCS request, autopilot reply), so it
  includes the autopilot's handling time. Medians (one run each): PX4 0.66 ms direct / 5.1 ms through
  OMNeT++; ArduPilot 5.2 ms direct / 6.8 ms through OMNeT++. The simulated path adds 4 ms (2 × 2.0 ms
  one-way transit); ArduPilot's ~5 ms reply latency overlaps with it instead of adding to it. Network
  RTT should therefore be read from the bridge's `transitDelay`, not from TIMESYNC alone; the
  difference between stacks in reply latency is itself stack behaviour (possibly relevant to H1/H2).
- The pcap recorder needs `**.fcsMode = "computed"` and `**.crcMode = "computed"`.
