# Architecture

```
  ┌──────────────┐        C2 traffic (e.g. MAVLink)         ┌───────────────┐
  │ GS software  │◄────────────────────────────────────────►│ Flight SW     │
  │  (profile)   │  real packets via emulation interface    │ (SITL, prof.) │
  └──────┬───────┘                                          └───────┬───────┘
         │                                                          │ sensors/actuators
  ┌──────▼───────────────────────────────┐                  ┌───────▼───────┐
  │ OMNeT++ / INET  (real-time/emulation)│                  │    Gazebo     │
  │  + Simu5G radio (SNR, TX power, ...) │                  │   (physics)   │
  └──────┬───────────────────────────────┘                  └───────────────┘
         │ pcap (L2/L3) + PHY vectors + disruption/failsafe events
         ▼
  data/raw/<run_id>/ ──► features per segment ──► models (H1–H4)
                              ▲
        rf/ (cabled SDR, validation only) ──┘ compared on airtime / TX power / SNR
```

Run structure: `steady → disruption → response → recovery`. Factors: profile × disruption ×
radio_background × seed (`experiments/design.yaml`).

## Open questions for the simulation POC
These are my reasoning from the proposal, not verified facts.

1. **Real-time coupling.** The real GS and flight software run on wall-clock time, so OMNeT++ must run
   under a real-time scheduler with an external/emulation interface. Consequences: every run lasts
   its real duration (campaign time ≈ runs × run length; e.g. 282 runs × 6 min ≈ 28 h sequential),
   parallel runs need isolated network namespaces, and scheduler lag must be monitored because it
   distorts inter-arrival features. Creating TAP interfaces may need capabilities the sandbox user
   does not have (see `compose.yaml` TODO).
2. **Where the L1 metrics come from.** Check that Simu5G exposes SNR, transmit power and something
   that maps to "airtime" (e.g. resource-block utilisation) per node, at usable time resolution.
3. **Segment definition.** Does `response` start when the disruption starts or when it ends? This
   fixes the H1 window and what "steady window of the same length" means.
4. **H4 / failsafe equalisation.** Which native parameters set the link-loss timeout and action in each
   chosen stack, and can they be made equal without changing other behaviour?
5. **One timebase.** Use wall-clock as the common timebase for Gazebo, OMNeT++, flight/GS logs, pcap and
   (later) the I/Q capture; define the marker used to align the SDR recording.
6. **Reproducibility claim.** Real-time coupling is not bit-exact, so seeds control the OMNeT++ RNG
   streams and disruption timing only; claim statistical reproducibility.
7. **Is Gazebo needed per run?** Flight-failsafe behaviour needs vehicle state, but a headless or
   simplified physics setup may be enough and would cut resource use.
8. **Factorisation.** The proposal gives totals (216/48/18) but not the factor levels; see the
   assumption stated in `experiments/design.yaml`.
