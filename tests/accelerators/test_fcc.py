"""FCC accelerator descriptor (no MAD-NG)."""

import pytest

from pymadng_utils.accelerators import FCC


def test_fcc_z_defaults(tmp_path):
    acc = FCC(sequence_file=tmp_path / "fccee_z.madx")
    assert acc.seq_name == "fccee_p_ring"
    assert acc.mode == "z"
    assert acc.particle == "electron"
    assert acc.NOCHARGE and acc.RBARC
    assert acc.energy == pytest.approx(45.6, rel=1e-6)
    assert acc.tune_integers == (166, 162)
    assert acc.bpm_pattern == "^BPM_.*$"


def test_fcc_rejects_unknown_mode(tmp_path):
    with pytest.raises(ValueError):
        FCC(sequence_file=tmp_path / "x.madx", mode="q")


def test_fcc_has_no_tune_knobs_or_ac_dipole(tmp_path):
    acc = FCC(sequence_file=tmp_path / "x.madx")
    with pytest.raises(NotImplementedError):
        acc.tune_variables
    with pytest.raises(NotImplementedError):
        acc.ac_dipole_name
