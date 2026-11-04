# 0004 — Keep UE transmit power fixed in the PoC; decide on power control before the pilot

Status: proposed (to discuss with the supervisor; final decision due before the pilot)
Touches: sim, rf, analysis, H2

## Context
The proposal lists three physical-layer (L1) features: airtime, transmit power and SNR. Stage 3
(`docs/poc-plan.md`) asks which of these Simu5G exposes as time series. Checked in the Simu5G v1.6.0
source in the container (`$SIMU5G_ROOT/src`, 2026-11-03 and 2026-11-04):
- `LtePhyBase` reads `ueTxPower` (default 26 dBm) once at initialisation, and `LtePhyUe` copies it into
  `txPower_`. The UE's transmit power is therefore constant for the whole run.
- Transmit power is an input to SINR. `LteRealisticChannelModel::getSINR`, which the NR channel models
  inherit, computes per resource block: received power = TX power + antenna gains − cable loss − path
  loss + fading, and SINR = received power − (thermal noise + noise figure + interference).
- A search of `src/` found no signal or NED statistic for transmit power, so nothing records it.
- We found no uplink power control for our UE: no open-loop path-loss compensation, no scaling with the
  number of allocated resource blocks, and no closed-loop power commands from the gNB. Real LTE/NR UEs
  do all three (3GPP TS 38.213 §7.1 for NR PUSCH; section number from memory, check before citing).
- Not audited: the D2D and background-traffic modules handle power separately. Neither applies to the
  vehicle UE in `C2Simu5G`.

The other two L1 features are recorded (`sim/omnetpp/omnetpp.ini`, `[Config Simu5G]`): SINR and CQI
in both directions, and resource blocks served per TTI at the gNB as the airtime proxy. HARQ
transmission attempts are recorded as well.

**Fixed power distorts uplink SINR, not just the missing power series.** A real UE lowers its power when
path loss is low and raises it when path loss is high, which partly holds uplink SINR steady. Here every
channel change lands directly on SINR. Stage-3 runs (one per stack, 2026-11-03; UE static at 50 m) show
`rcvdSinrUl` up to 56.1 dB, which looks unrealistically high; fixed full power is a likely contributor,
not an established cause.

## Decision
For the PoC stages, transmit power stays a fixed per-run configuration value, not a measured feature.
- The configured `ueTxPower` / `eNodeBTxPower` are written to the run's manifest (stage 4), so every run
  records the value it used.
- The PoC's simulated L1 features are SINR/CQI and resource-block utilisation (airtime). No TX-power
  time series is extracted.
- Simulated uplink SINR is treated as produced under fixed power, not as an estimate of what a real UE
  under power control would see.
- This is provisional. Whether to add uplink power control is decided with the supervisor before the
  pilot, because pilot and campaign data would otherwise need rerunning. The wider question of where a
  simulated L1 fingerprint comes from is tracked in `docs/poc-plan.md` (Open items).
- If power control is not added, the thesis states this as a testbed limitation: transmit-power
  behaviour during link loss is not modelled, and H2's fusion result covers L1 = {SNR, airtime} only.
- The cabled RF measurement (weeks 10–11, `rf/README.md`) records received power. Without power control
  it cannot validate a simulated TX-power response, and comparing uplink SNR with it needs care for the
  reason above.

## Alternatives considered
- **Implement open-loop uplink power control now** (subclass the NR UE PHY; P = min(Pmax, P0 + α·PL +
  10·log10(M_RB))). Moderate C++ work, and a self-written model that needs its own validation; closed-loop
  control adds gNB-side logic on top. The power series itself would be a function of path loss and RB
  allocation, so it may add little as a separate feature. It would, however, also change uplink SINR,
  making that series more realistic. This is the main candidate if the decision is reopened, and it can
  be added later as a PHY subclass without changing the rest of the ladder (not yet prototyped).
- **Energy proxy** (served RBs × fixed power): honest, but it is a rescaling of the airtime feature and
  adds nothing for H2. It does not address the uplink SINR distortion.
- **Use a different radio simulator with power control**: rejected for now. Simu5G is fixed by the
  proposal and stages 1–3 are built on it.

## Consequences
- We give up any fingerprint signal carried by how a real UE's transmit power reacts to link loss
  (e.g. ramping on retries or reconnection). The direction of any bias in the simulated L1 gain for H2 is
  unknown, because uplink SINR is distorted as well.
- If the decision stands, the proposal's feature list changes. The thesis method chapter must say so and
  point here.
- Any simulated uplink SINR results depend on this choice; pilot or campaign data collected before the
  decision may have to be rerun.
- How we would notice this was wrong: the supervisor considers TX power central to the research
  question, or the RF lab capture shows received-power variation around a disruption that simulated SINR
  and airtime do not reflect. Either case reopens the first alternative, recorded as a new ADR that
  supersedes this one.
- Unverified: whether a newer Simu5G release adds uplink power control. Check the release notes before
  revisiting.
