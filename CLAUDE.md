# CLAUDE.md — Link-loss response as a UAS fingerprint

MSc thesis project (Martin Elfvelin), spring 2027, 20 weeks at 50%. Proposal: `docs/proposal.pdf`.
You are working in a sandbox container; the workspace is `/workspace`.

## Research question
To what extent can a UAS be identified by fusing physical-layer (L1) and network-layer (L2/L3)
behavioural responses during a C2 link disruption?

| ID | Hypothesis |
|----|------------|
| H1 | Identification from the window after a link loss beats a steady-flight window of the same length |
| H2 | The gain from fusing RF + network features is largest in the response window |
| H3 | The link-loss response is distinguishable from the response to benign congestion and weak radio |
| H4 | The fingerprint survives when failsafe timeouts are set equal across profiles |

Every analysis, plot and table should be traceable to one of H1–H4. If it is not, say so.

## Architecture (simulation testbed) — see `docs/architecture.md`
- **Gazebo** — physics / vehicle dynamics
- **Flight software** (SITL, e.g. PX4 or ArduPilot — not yet chosen) — onboard behaviour, failsafe logic
- **Ground-station software** (not yet chosen) — GCS side of the C2 link
- **OMNeT++ / INET** — network simulation carrying the C2 traffic between GS and vehicle
- **Simu5G** — radio environment (L1/L2 behaviour, background load)
- **Bridge** (`sim/bridge/`) — couples the real software stacks to OMNeT++ and exports synchronised traces

A *profile* = one combination of GS stack + flight stack + configuration (`profiles/*.yaml`).
Factors per run: `profile`, `disruption`, `radio_background`, `seed`. The proposal totals 216 main runs
(+48 pilot, +18 extra); the grid lives in `experiments/design.yaml` and **only there**.

Each run has four segments: `steady` → `disruption` → `response` → `recovery`.
Boundaries are defined once in `src/linkloss/segments.py`; all feature code goes through it.

Features — network (L2/L3): traffic burstiness, inter-arrival time, retransmission cadence.
Physical (L1): airtime, transmit power, SNR.

## RF measurement (weeks 10–11, lab at ECH) — see `rf/README.md`
Validation of the simulated radio response only. **Cabled connection with attenuator, never radiating.**
SDR records I/Q + received power, time-synchronised with the network capture. Never write code that
transmits over the air, and never remove the attenuator from a procedure or checklist.

## Working rules
1. **Reproducibility.** A run is determined by (profile, disruption, radio_background, seed) + git commit
   + image digest. Write `manifest.json` per run with all of these. The coupled real-time stacks are not
   bit-exact; claim statistical reproducibility only, and say so where relevant.
2. **No raw data in git.** `data/` is git-ignored and `data/raw/` is append-only: never edit or overwrite
   a finished run; rerun under a new attempt suffix.
3. **Configs over code.** Profiles, disruptions and backgrounds are YAML (`profiles/`, `experiments/`).
   No hard-coded constants in sim or analysis code.
4. **Avoid label leakage.** Features must not encode the profile trivially (ports, IPs, MAVLink system
   IDs, run order, seed-correlated timestamps). Cross-validate grouped by seed/run, never by random row.
5. **H4 matters.** Failsafe timeouts are a first-class parameter of each profile so they can be equalised.
6. **Pilot seeds are disjoint from main seeds**; pilot-tuned choices must not be evaluated on pilot data.
7. Check what exists before writing: read `docs/decisions/` and `docs/architecture.md`.
8. Non-obvious design choices → short ADR in `docs/decisions/NNNN-title.md` (skill: `write-adr`).
9. Say when something is unverified (versions, API behaviour, assumptions about a stack). Check docs or
   run it instead of guessing silently.
10. Small, reviewable commits with prefixes: `sim:`, `analysis:`, `rf:`, `infra:`, `docs:`, `thesis:`.
    Do not push; the author pushes from the host.
11. Python ≥3.10 with type hints, `ruff` + `pytest`. OMNeT++ C++ follows INET style, built with `opp_makemake`.

## Commands (inside the container)
`make sim-build` · `make sim-run RUN=<run_id>` · `make pilot` · `make campaign` · `make analyze` ·
`make test` · `make lint`. Some are stubs until the simulation POC exists; if a target is missing or a
stub, implement it in the `Makefile` / `sim/scripts/` rather than working around it.

## Skills (`.claude/skills/`)
`run-experiment`, `add-profile`, `feature-extraction`, `omnet-inet-dev`, `rf-measurement`, `write-adr`.

## Sandbox
You run in Docker with an egress allowlist (Anthropic, GitHub, npm, PyPI). You cannot start other
containers or use `sudo`. If a task needs a host or service that is not reachable, say so and ask —
do not try to route around the firewall.

## Writing
`thesis/` is the author's text. Draft or edit it only when asked, and keep claims tied to evidence and H1–H4.
