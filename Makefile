SHELL := /bin/bash
export HOST_UID := $(shell id -u)
export HOST_GID := $(shell id -g)

RUN   ?=
PHASE ?= main

.DEFAULT_GOAL := help
.PHONY: help image claude claude-auto shell sim-build sim-run pilot campaign analyze test lint

help: ## Show targets
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

# ---------------------------------------------------------------- host side (outside the container)
image: ## [host] Build the sandbox image
	docker compose build claude

claude: ## [host] Claude Code in the sandbox (normal permission prompts)
	docker compose run --rm claude claude

claude-auto: ## [host] Claude Code, permission prompts OFF (sandbox + firewall are the guardrail)
	docker compose run --rm claude claude --dangerously-skip-permissions

shell: ## [host] Plain shell in the sandbox
	docker compose run --rm claude bash

# ---------------------------------------------------------------- container side
sim-build: ## Build the OMNeT++ project in sim/omnetpp
	sim/scripts/build_omnetpp.sh

sim-run: ## Run one experiment: make sim-run RUN=<run_id>
	@test -n "$(RUN)" || { echo "usage: make sim-run RUN=<run_id>"; exit 2; }
	python -m linkloss.orchestrate run $(RUN)

pilot: ## Run every pilot-phase run
	python -m linkloss.orchestrate run-phase pilot

campaign: ## Run a phase: make campaign PHASE=main
	python -m linkloss.orchestrate run-phase $(PHASE)

analyze: ## Features + models (stub until the POC produces data)
	@echo "TODO(analysis): not implemented yet"; exit 1

test: ## pytest
	pytest

lint: ## ruff
	ruff check src tests
