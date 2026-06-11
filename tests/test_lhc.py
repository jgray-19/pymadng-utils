from __future__ import annotations

from pathlib import Path

from pymadng_utils.accelerators import LHC


def test_lhc_marker_name_uses_ac_dipole_marker(seq_b1: Path) -> None:
    accel = LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0)

    assert accel.acd_marker_name("before") == "MKQA.6L4.B1_before"
    assert accel.acd_marker_name("after") == "MKQA.6L4.B1_after"
