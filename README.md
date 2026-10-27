# Link-loss response as a UAS fingerprint

MSc thesis. Can a UAS be identified by fusing physical-layer and network-layer behaviour during a
command-and-control link disruption? Hypotheses H1–H4 are in [`CLAUDE.md`](CLAUDE.md) and
[`docs/proposal.pdf`](docs/proposal.pdf).

## Layout

```
.
├── CLAUDE.md                 project memory for Claude Code (research context + working rules)
├── compose.yaml              claude (dev sandbox) + campaign (headless batch runs)
├── docker/                   Dockerfile (multi-stage), egress firewall, entrypoint, requirements
├── .claude/
│   ├── settings.json         permissions + RF-transmit guard hook
│   ├── hooks/block-tx.sh
│   └── skills/               run-experiment, add-profile, feature-extraction,
│                             omnet-inet-dev, rf-measurement, write-adr
├── docs/
│   ├── proposal.pdf
│   ├── architecture.md       data flow + open questions for the simulation POC
│   └── decisions/            ADRs
├── experiments/
│   ├── design.yaml           THE factor grid (pilot / main / extra)
│   ├── disruptions.yaml      link-loss, congestion, weak-radio definitions
│   └── backgrounds.yaml      radio background-load levels
├── profiles/                 one YAML per UAS profile (GS stack + flight stack + failsafe config)
├── sim/
│   ├── omnetpp/              INET + Simu5G project (NED, ini, C++ modules)
│   ├── gazebo/               worlds, models
│   ├── flight/               flight-software SITL (pinned submodules, params)
│   ├── gs/                   ground-station software configs
│   ├── bridge/               coupling + trace export
│   └── scripts/              build / run helpers
├── rf/                       ECH measurement: capture, sync, analysis (cabled + attenuated, receive-only)
├── src/linkloss/             python package: design, segments, orchestration, features, models
├── tests/
├── data/                     git-ignored: raw/ (append-only), interim/, processed/
└── thesis/                   report source (author's text)
```

## Quick start (Fedora host, Docker)

```bash
git init                      # BEFORE the first compose run, so .git/hooks is not created as root
cp .env.example .env          # optional: git identity, API key, extra firewall domains
make image                    # first build compiles OMNeT++/INET/Simu5G: slow, then cached
make claude                   # starts Claude Code in the sandbox; log in on first run
make shell                    # Drop into container directly to run commands
```

- `make claude-auto` starts Claude with permission prompts off. The container is the guardrail
  (non-root, egress allowlist, `.git/hooks` read-only), but `/workspace` is writable: commit often.
- Claude commits inside the container; **you push from the host.** No SSH keys or git credentials
  are mounted into the sandbox.
- `:z` on the bind mounts is for SELinux; drop it on hosts without SELinux.
- To reach another host from the sandbox: `EXTRA_ALLOWED_DOMAINS="host.example" ` in `.env`, then restart.

## Status
Scaffold only. The simulation POC (OMNeT++ ↔ flight/GS coupling) is the next step; see
[`docs/architecture.md`](docs/architecture.md).
