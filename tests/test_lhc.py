from __future__ import annotations

from typing import TYPE_CHECKING

from pymadng_utils.accelerators import LHC

if TYPE_CHECKING:
    from pathlib import Path


def test_lhc_marker_name_uses_ac_dipole_marker(seq_b1: Path) -> None:
    accel = LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0)

    assert accel.acd_marker_name("before") == "MKQA.6L4.B1_before"
    assert accel.acd_marker_name("after") == "MKQA.6L4.B1_after"


def test_lhc_repr_and_str_use_default_accelerator_behaviour(seq_b1: Path) -> None:
    accel = LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0)

    assert repr(accel) == (
        "LHC("
        "beam=1, "
        "tune_knobs_suffix='_op', "
        f"sequence_file={seq_b1!r}, "
        "kinetic_energy=6800.0, "
        "particle='proton', "
        "energy=6800.93827208816, "
        "beta=0.9999999904832221, "
        "bpm_pattern='^BPM.*$'"
        ")"
    )
    assert str(accel) == (
        f"LHC(seq_name=lhcb1, particle=proton, kinetic_energy=6800 GeV, "
        f"sequence_file={seq_b1})"
    )
