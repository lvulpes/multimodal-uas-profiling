# Simulation PoC plan

Goal: get the whole simulation environment running early, as a demo, so debugging does not eat project
time later. Nothing here has to be final; the real profile set (6 combinations of autopilot stack,
ground-station software and payload) is not defined yet.

## Decisions so far
- Profiles for the PoC: `px4_pymavlink` (PX4 SITL + Gazebo, headless) and `ardupilot_pymavlink`
  (ArduPilot SITL). Ground station = a pymavlink script for both.
- Network coupling ("socket bridge"): the container's seccomp profile blocks `unshare`, so there are no
  network namespaces or TAP devices. GS and flight software talk over loopback UDP with per-run port
  numbers; a small OMNeT++ module bridges those sockets into the simulated network (INET/Simu5G) under the
  real-time scheduler. The pcap is recorded on the simulator side.
  - Trade-off: L2/L3 headers in the capture come from the simulator, not the real kernel stack;
    application-level behaviour (MAVLink timing, retries, heartbeats, failsafe reactions) stays real.
    Check with the supervisor that this is acceptable for the network features.
  - Upgrade path if it is not: a custom seccomp profile allowing namespaces + the capabilities TAP needs.
- Building flight stacks happens in the Docker image (`flight` stage), because the sandbox has no sudo and
  its firewall blocks apt. Loop: Claude edits `docker/Dockerfile` → author runs `make image` on the host →
  Claude tests in the container.

## Stages (each adds one module; do not start the next until the previous passes)

| # | Adds | Passes when |
|---|------|-------------|
| 1 | PX4 (+ headless Gazebo) and ArduPilot SITL, each driven by a pymavlink GCS; no OMNeT++ | Heartbeats received, arm, takeoff work for both stacks. A separate test cuts the C2 link and the stack's failsafe fires. |
| 2 | Plain INET between GS and flight software via the socket bridge | The same traffic passes through OMNeT++. RTT measured; real-time scheduler lag logged. |
| 3 | Simu5G (UE ↔ gNB ↔ core) replaces the INET link | Same traffic passes. SNR, TX power and an airtime-like quantity recorded as time series; note which signals Simu5G does not expose. |
| 4 | Disruption injection + segment timestamps | One run writes `data/raw/<run_id>/` (manifest, pcap, phy, events); four segments populated; failsafe event visible. |
| 5 | Second profile compared | Crude features from `steady` vs `response` windows differ between the two profiles (first hint for H1). |

## Open items
- What the 6 profile combinations are (autopilot × GS × payload). Update `experiments/design.yaml` when known.
- Whether the `response` segment starts at disruption onset or at its end (decide by stage 4).
- pymavlink is a stand-in GS; real GS software may behave differently and matter for the fingerprint.
- Failsafe parameter names per stack (needed for H4 equalisation) must be looked up in the stacks' docs for
  the pinned versions, not assumed.
