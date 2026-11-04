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
- The drone in the radio simulation must move with the flown drone: a UE that stays put makes no sense for
  the real simulation (stage 5).
  - Position source: PX4 runs with Gazebo and ArduPilot SITL runs without it, so the feed probably has to
    come from the vehicle's MAVLink position rather than from Gazebo. Unverified: whether the harness's
    5 Hz position rate is enough for the radio model.
  - Unverified: Simu5G's channel model is meant for ground-level UEs (1.5 m default, urban macrocell), so a
    UE that moves correctly does not guarantee realistic radio behaviour at altitude. Check in stage 5; it
    may be a reason to prefer another channel model or simulator.
  - The position feed runs through the real-time bridge, so the radio's view lags the flight slightly.
    Log the lag and keep it small, as for scheduler lag.
- Test design, from a supervisor/examiner's document (not in the repo; the grid is `experiments/design.yaml`):
  > Main design: 6 × 4 × 3 × 3 = 216 runs.
  > Pilot: 4 profiles × 4 disruption levels × clean background × 3 seeds = 48 runs.
  > Matched-timeout arm: 18 extra runs (6 profiles × 3 seeds, long disruption), with failsafe timeouts and
  > actions set equal across profiles.
  > Disruption lengths: chosen to bracket the failsafe timeouts of the stacks in use. Take the values from
  > the firmware documentation.
  > Profiles: each stack keeps its default link-loss behaviour in the main design, so differences come from
  > the software, not from hand-set values.
- Seed sets the flight: "Seed - different routes and start times - 3" (author, 2026-11-04). Routes and
  start times live in YAML (`experiments/`), and the smoke harness, which only hovers today, must fly them.
  - The same seed must give the same route and start time for every profile; otherwise route is confounded
    with profile.
  - Pilot routes must differ from main routes. Disjoint seed numbers alone do not guarantee that.

## Stages (each adds one module; do not start the next until the previous passes)

| # | Adds | Passes when |
|---|------|-------------|
| 1 | PX4 (+ headless Gazebo) and ArduPilot SITL, each driven by a pymavlink GCS; no OMNeT++ | Heartbeats received, arm, takeoff work for both stacks. A separate test cuts the C2 link and the stack's failsafe fires. |
| 2 | Plain INET between GS and flight software via the socket bridge | The same traffic passes through OMNeT++. RTT measured; real-time scheduler lag logged. |
| 3 | Simu5G (UE ↔ gNB ↔ core) replaces the INET link | Same traffic passes. SNR, TX power and an airtime-like quantity recorded as time series; note which signals Simu5G does not expose. |
| 4 | Disruption injection + segment timestamps | One run writes `data/raw/<run_id>/` (manifest, pcap, phy, events); four segments populated; failsafe event visible. |
| 5 | Vehicle flies a seed-defined route and its position drives the Simu5G UE during the run (one position source for both stacks, see below) | The UE's position follows the flown path; path loss and SINR change with distance; position-update lag logged. |
| 6 | Second profile compared, with the stage-5 coupling in place | Crude features from `steady` vs `response` windows differ between the two profiles (first hint for H1). |

## Open items
- What the 6 profile combinations are (autopilot × GS × payload), and which 4 go in the pilot. Not defined yet;
  `experiments/design.yaml` uses placeholders. The disruption lengths depend on this.
- Whether the `response` segment starts at disruption onset or at its end (decide by stage 4).
- Main-design failsafe settings: the failsafe is enabled in every profile (author, 2026-11-04), because both
  stacks disable it by default (ADR 0002). Still open: the action, and whether timing stays at stack
  defaults. The PoC profiles currently set a 5 s timeout and Return.
- **To discuss with the supervisor (H3): is there a comparison without link loss?** The backgrounds are clean,
  congested and weak (author, 2026-11-04), and all 4 disruption levels read as link loss, so every run contains
  a link loss. Congestion and weak radio are then conditions during it, with no onset to respond to.
- Matched-timeout arm: its background and seeds are not stated. Assumed clean background and main seeds.
- "Start time" of a seed: working assumption is take-off time (author's guess, unconfirmed).
- **To discuss with the supervisor: which radio is the UAS meant to use?** The proposal says "a UAS radio" for
  the lab test and names radio hardware as a source of the fingerprint, but never says the C2 link is
  cellular; choosing Simu5G implies that it is. If the lab radio is not cellular, Simu5G models the wrong
  radio and the lab test cannot validate it. This decides the radio simulator choice (ADR 0004).
- pymavlink is a stand-in GS; real GS software may behave differently and matter for the fingerprint.
- Failsafe parameter names per stack (needed for H4 equalisation) must be looked up in the stacks' docs for
  the pinned versions, not assumed.
- **To discuss with the supervisor (H2): where would a simulated L1 fingerprint come from?** All profiles
  share the same simulated radio, and until stage 5 the UE is static (`StationaryMobility`, 1.5 m high), so
  different failsafe manoeuvres look the same to the radio. In the
  stage-3 runs (one per stack, 2026-11-03) both stacks had identical SINR limits: `rcvdSinrDl` 65.746 dB,
  `rcvdSinrUl` 46.748–56.124 dB. Seeds were not varied, so this is only an indication. If L1 differences
  can only come from traffic patterns, which L2/L3 already sees, the fusion gain could be close to zero
  because of how the testbed is built. Related: transmit power, ADR 0004. Proposed changes, not yet in
  the stage table:
  - Stage 4: realise `link_loss` at the radio level rather than dropping packets at the bridge, so L1 sees
    the disruption. How Simu5G handles a lost radio link is unverified.
  - Stage 6: add a criterion that at least one L1 feature differs between profiles beyond what traffic
    explains.

# Claude session

claude --resume f854c713-22fe-43c6-931d-53b745e8fe01
