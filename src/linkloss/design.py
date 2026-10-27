"""Expand experiments/design.yaml into the list of runs.

The factor grid lives only in the YAML; everything else asks this module for runs.
"""

from __future__ import annotations

import argparse
import itertools
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_DESIGN = Path("experiments/design.yaml")


@dataclass(frozen=True)
class Run:
    phase: str
    profile: str
    disruption: str
    radio_background: str
    seed: int

    @property
    def run_id(self) -> str:
        return (
            f"{self.phase}__{self.profile}__{self.disruption}__{self.radio_background}__s{self.seed}"
        )


def _seeds(spec) -> list[int]:
    if isinstance(spec, dict):
        return [int(spec["base"]) + i for i in range(int(spec["count"]))]
    return [int(s) for s in spec]


def load_runs(path: Path | str = DEFAULT_DESIGN, phase: str | None = None) -> list[Run]:
    cfg = yaml.safe_load(Path(path).read_text())
    runs: list[Run] = []
    for name, phase_cfg in cfg["phases"].items():
        if phase is not None and name != phase:
            continue
        factors = (phase_cfg or {}).get("factors")
        if not factors:
            continue
        for profile, disruption, background, seed in itertools.product(
            factors["profile"],
            factors["disruption"],
            factors["radio_background"],
            _seeds(factors["seed"]),
        ):
            runs.append(Run(name, profile, disruption, background, seed))
    ids = [r.run_id for r in runs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate run IDs in design")
    return runs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", default=str(DEFAULT_DESIGN))
    parser.add_argument("--phase", default=None)
    parser.add_argument("--list", action="store_true", help="print run IDs instead of the count")
    args = parser.parse_args()
    runs = load_runs(args.design, args.phase)
    if args.list:
        for r in runs:
            print(r.run_id)
    else:
        print(len(runs))


if __name__ == "__main__":
    main()
