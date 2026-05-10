from __future__ import annotations

from pathlib import Path

import pytest

from pymadng_utils.accelerators import PROTON_MASS_GEV, PSB, PSB_FLAT_BOTTOM_GEV


def test_psb_infers_ring_and_defaults(seq_psb3: Path) -> None:
    """PSB should infer the ring from the saved sequence name and expose defaults."""
    accel = PSB(sequence_file=seq_psb3)

    assert accel.ring == 3
    assert accel.seq_name == "psb3"
    assert accel.bpm_pattern == "^BR3%.BPM.*3$"
    assert accel.tune_variables == ("kBRQF", "kBRQD")
    assert accel.tune_integers == (4, 4)
    assert accel.ac_dipole_location == ("BR3.DES3L1", 0.565 / 2)
    assert accel.get_exciter_bpm() == ("BR3.BPM3L3", "BR3.BPM4L3")
    assert accel.kinetic_energy == pytest.approx(PSB_FLAT_BOTTOM_GEV)
    assert accel.energy == pytest.approx(PSB_FLAT_BOTTOM_GEV + PROTON_MASS_GEV)


def test_psb_requires_inferable_or_explicit_ring(tmp_path: Path) -> None:
    """PSB should fail fast when the ring cannot be inferred from the filename."""
    sequence_file = tmp_path / "booster_saved.seq"
    sequence_file.write_text("")

    with pytest.raises(ValueError, match="Could not infer PSB ring number"):
        PSB(sequence_file=sequence_file)


def test_psb_infer_monitor_plane() -> None:
    """Known PSB monitor families should map to the shared horizontal/vertical plane."""
    assert PSB.infer_monitor_plane("BR3.BPM3L3") == "HV"
    assert PSB.infer_monitor_plane("BR3.BWS.2L1.H_ROT") == "HV"

    with pytest.raises(ValueError, match="Unsupported PSB monitor name"):
        PSB.infer_monitor_plane("BR3.UNKNOWN")
