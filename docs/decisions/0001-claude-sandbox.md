# 0001 — Claude Code runs in a Docker sandbox with an egress allowlist

Status: proposed
Touches: infra

## Context
Claude writes most of the code and runs builds, simulations and scripts. It needs a writable workspace and
network access to the Anthropic API, GitHub and package registries, but should not be able to reach
arbitrary hosts, touch host credentials, or alter anything that runs on the host.

## Decision
- One image (multi-stage): the simulation toolchain is inside the same container as Claude, so it can
  build and run sims itself. A separate `campaign` service reuses the `sim` stage for headless batch runs
  without Claude or API access.
- Non-root user matching the host UID/GID. The container starts as root only to install an iptables/ipset
  egress allowlist, then drops privileges with `gosu`; `no-new-privileges` is set; `sudo` is not installed.
- Workspace bind-mounted; `.git/hooks` mounted read-only (hooks execute on the host at commit time).
  No SSH keys or git credentials are mounted: Claude commits, the author pushes from the host.
- Claude's login and history live in a named volume, not in the repo.
- `.claude/settings.json` adds permission rules (deny `git push`, `sudo`, reading `.env`, editing
  `data/raw`) and an RF-transmit tripwire hook. `make claude-auto` skips permission prompts; the container is
  then the main guardrail.

## Alternatives considered
- Dev container integrated with an IDE: not needed (neovim on the host).
- Docker-in-Docker / giving Claude the Docker socket: rejected; equals root on the host.
- Separate sim container driven by Claude: needs the socket or an RPC layer; added complexity for no gain.

## Consequences
Residual risks: data can still leave via DNS to the configured resolver or via allowed hosts (GitHub, PyPI,
npm); the workspace and `data/` are writable, so commit often and keep raw data append-only by habit;
resolved IPs are fixed at start (restart if the API becomes unreachable). Real-time network emulation may
need extra capabilities (see `docs/architecture.md`, question 1); decide the narrowest set when it
becomes concrete. Revisit if any of this blocks the simulation POC.
