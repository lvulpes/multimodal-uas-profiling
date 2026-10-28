# Human notes

These are notes about the project after discussions and execution by Claude code. There's no value for an AI agent in these notes as everything included here is based on the outputs of said AI agent.

## PoC ladder setup

We're setting up a 4 rung ladder to reach a proof of concept (poc).
The PoC ladder is in docs/poc-plan.md, in the "Stages" table; stage 1 is the first row. The decisions behind it are in docs/decisions/0002-… and 0003-…, and the open architecture questions are in docs/architecture.md.

## Running test stages

Running a whole stage
``` terminal
make shell        # on the host: opens a shell in the sandbox
make stage1       # inside: both smoke tests, then both link-cut tests
```
Running only parts of a stage
``` terminal
make smoke                                   # heartbeat/arm/takeoff, both stacks
make failsafe                                # link-cut tests, both stacks
make failsafe STAGE1_PROFILES=px4_pymavlink  # one stack only
python sim/smoke/failsafe.py --profile ardupilot_pymavlink   # one test directly
```

Each test prints PASS or FAIL and exits non-zero on failure, so make stage1 stops at the first one that fails. Each run gets its own folder, data/smoke/<test>-<profile>-<UTC time>/, containing:
- summary.json: result, confirmed failsafe parameters, takeoff altitude, cut-to-RTL delay, packets forwarded and dropped by the relay
- test.log: what the ground station saw, including the vehicle's status messages
- sitl.log: the flight stack's own output, the first place to look if a stack fails to start

