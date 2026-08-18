from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pymadng_utils.accelerators import (
    PROTON_MASS_GEV,
    PSB,
    PSB_FLAT_BOTTOM_GEV,
    Accelerator,
)
from pymadng_utils.physics import beta_from_energy

if TYPE_CHECKING:
    from pathlib import Path


class DummyAccelerator(Accelerator):
    @property
    def seq_name(self) -> str:
        return "dummy"

    @property
    def ac_dipole_name(self) -> str:
        return "dummy.acd"

    @property
    def tune_variables(self) -> tuple[str, str]:
        return "qx", "qy"

    @property
    def tune_integers(self) -> tuple[int, int]:
        return 1, 2


def test_psb_infers_ring_and_defaults(seq_psb3: Path) -> None:
    """PSB should infer the ring from the saved sequence name and expose defaults."""
    accel = PSB(sequence_file=seq_psb3)

    assert accel.ring == 3
    assert accel.seq_name == "psb3"
    assert accel.bpm_pattern == "^BR3%.BPM.*3$"
    assert accel.tune_variables == ("kBRQF", "kBRQD")
    assert accel.tune_integers == (4, 4)
    assert accel.ac_dipole_name == "HACMAP"
    # assert accel.get_exciter_bpm() == ("BR3.BPM3L3", "BR3.BPM4L3")
    assert accel.kinetic_energy == pytest.approx(PSB_FLAT_BOTTOM_GEV)
    assert accel.energy == pytest.approx(PSB_FLAT_BOTTOM_GEV + PROTON_MASS_GEV)
    assert accel.beta == pytest.approx(beta_from_energy(accel.energy, "proton"))


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


def test_accelerator_repr_and_str_default_behaviour(tmp_path: Path) -> None:
    sequence_file = tmp_path / "dummy.seq"
    accel = DummyAccelerator(
        sequence_file=sequence_file,
        kinetic_energy=1.25,
        bpm_pattern="^BPM",
    )

    assert repr(accel) == (
        "DummyAccelerator("
        f"sequence_file={sequence_file!r}, "
        "kinetic_energy=1.25, "
        "particle='proton', "
        "energy=2.1882720881599997, "
        "beta=0.903412239922737, "
        "bpm_pattern='^BPM'"
        ")"
    )
    assert str(accel) == (
        f"DummyAccelerator(seq_name=dummy, particle=proton, "
        f"kinetic_energy=1.25 GeV, sequence_file={sequence_file})"
    )


def test_accelerator_uses_beta_for_dp_pt_conversions(tmp_path: Path) -> None:
    accel = DummyAccelerator(sequence_file=tmp_path / "dummy.seq", kinetic_energy=1.25)
    dp = 0.015

    assert accel.pt2dp(accel.dp2pt(dp)) == pytest.approx(dp)
