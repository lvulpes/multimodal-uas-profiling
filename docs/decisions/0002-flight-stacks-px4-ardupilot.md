# 0002 — PoC flight stacks: PX4 v1.17.0 and ArduCopter 4.7.2 SITL, built in the image

Status: proposed
Touches: sim, infra, H4

## Context
The PoC (docs/poc-plan.md) needs two different autopilot stacks behind the same ground station
(pymavlink) so that stage 5 can compare profiles. Their link-loss behaviour must be configurable
through native parameters (H4). The sandbox has no sudo and blocks apt, so the stacks must be built
in the Docker image, and builds must be reproducible from a pinned source.

## Decision
- **PX4 v1.17.0** (commit d6f12ad1c4f7, latest non-prerelease on 2026-10-27; v1.18 was at rc1), SITL with
  Gazebo Harmonic (gz sim 8.15.0) headless, airframe `gz_x500`.
- **ArduCopter 4.7.2** (tag `Copter-4.7.2`, commit fb773567896f, latest Copter tag on 2026-10-27), SITL with
  its built-in physics (`--model quad`), no Gazebo.
- **pymavlink 2.4.50** as the GCS for both (pinned in `docker/requirements.txt`).
- Built in the `flight` stage of `docker/Dockerfile` (`PX4_REF`, `ARDUPILOT_REF`). Dependencies are
  copied from the upstream setup scripts at those tags, headless subset (the scripts themselves need
  sudo, and ArduPilot's refuses to run as root). Clone, build and clean-up happen in one layer per stack;
  `.git` and object files are removed, and the exact commits including submodules are kept in
  `/opt/{px4,ardupilot}/SOURCE_COMMITS.txt`.
- Native link-loss parameters, read from the pinned sources (PX4 `parameters.json` of the build;
  `ArduCopter/Parameters.cpp`), are set per profile in `profiles/*.yaml`:

  | | PX4 v1.17.0 | ArduCopter 4.7.2 |
  |---|---|---|
  | enable/action | `NAV_DLL_ACT` (default 0 = disabled; 2 = Return) | `FS_GCS_ENABLE` (default 0; 1 = RTL) |
  | timeout | `COM_DL_LOSS_T` (default 10 s) | `FS_GCS_TIMEOUT` (default 5 s, range 2–120) |
  | extra delay | `COM_FAIL_ACT_T` (default 5 s hold before the action) | none found |
  | GCS identity | any GCS heartbeat | `MAV_GCS_SYSID` (renamed from `SYSID_MYGCS` in 4.7), default 255 |

## Alternatives considered
- Two PX4 or two ArduPilot configurations only: less stack diversity for the first profile comparison.
- ArduPilot under Gazebo (ardupilot_gazebo plugin): another build and plugin to pin; its built-in physics
  is enough for failsafe behaviour in stage 1 (see docs/architecture.md, question 7). Revisit if physics
  fidelity matters for the response window.
- Git submodules under `sim/flight/` (earlier plan): pulls multi-GB trees into the workspace; the image
  already pins the source, and the first full-history build filled the host disk.
- Latest PX4 prerelease (v1.18.0-rc1): not a release.

## Consequences
- Both failsafes are **disabled by default**; a profile that forgets `failsafe.native` shows no
  link-loss response at all. The stage-1 GCS sets and reads back these params before flight.
- Equal `timeout_s` does not mean equal reaction time: in stage 1, PX4 (5 s + 5 s `COM_FAIL_ACT_T`) entered
  RTL 12.2 s after the cut and ArduCopter (5 s) 4.3 s after it (one run each, heartbeat at 1 Hz). H4
  equalisation must cover `COM_FAIL_ACT_T`, not only the timeout. The ~1 s beyond 10 s on PX4 is not
  explained yet.
- `make`/`waf` cannot be re-run inside the image (no `.git`, root-owned); changing stack code means a
  rebuild. Bumping a pin means rebuilding and re-checking the parameter names above.
- Simulated physics differs between the stacks (Gazebo vs built-in). This is part of the profile, not a
  controlled variable; note it when interpreting stage-5 differences.
