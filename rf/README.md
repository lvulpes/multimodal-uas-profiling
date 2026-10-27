# RF validation (ECH lab, weeks 10–11)

Validates the simulated radio response: UAS radio → **cable + attenuator** → SDR (receive-only),
recording I/Q samples and received power while the C2 link is disrupted, time-synchronised with the
network capture. See `.claude/skills/rf-measurement/SKILL.md` for the rules.

```
capture/   SDR recording scripts (receive-only), SigMF metadata
sync/      timebase alignment between I/Q and network capture (marker-based offset/drift)
analysis/  compare measured vs simulated airtime / TX power / SNR per segment
```

## Safety checklist (fill in before the session; the author confirms with ECH)
- [ ] Conducted connection only, no antenna on the path
- [ ] Attenuator value: ___ dB; max UAS TX power: ___ dBm; cable loss: ___ dB
- [ ] Power at SDR input = TX − attenuation − cable loss = ___ dBm, below SDR safe input level (___ dBm)
- [ ] SDR configured receive-only
- [ ] Lab rules / approvals at ECH confirmed by: ___
