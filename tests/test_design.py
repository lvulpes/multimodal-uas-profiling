from pathlib import Path

from linkloss.design import load_runs

DESIGN = Path(__file__).resolve().parents[1] / "experiments" / "design.yaml"


def test_main_phase_has_216_runs():  # total stated in the proposal
    assert len(load_runs(DESIGN, "main")) == 216


def test_pilot_phase_has_48_runs():  # total stated in the proposal
    assert len(load_runs(DESIGN, "pilot")) == 48


def test_run_ids_unique_and_pilot_seeds_disjoint_from_main():
    runs = load_runs(DESIGN)
    assert len({r.run_id for r in runs}) == len(runs)
    main = {r.seed for r in runs if r.phase == "main"}
    pilot = {r.seed for r in runs if r.phase == "pilot"}
    assert not main & pilot
