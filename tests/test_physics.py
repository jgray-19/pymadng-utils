from __future__ import annotations

import math

import pytest

from pymadng_utils.physics import (
    PROTON_MASS_GEV,
    beta_from_energy,
    dp2pt,
    particle_mass,
    pt2dp,
)


def test_beta_from_energy_uses_relativistic_mass_ratio() -> None:
    energy = 2.0 * PROTON_MASS_GEV

    assert beta_from_energy(energy, "proton") == pytest.approx(math.sqrt(3.0) / 2.0)


def test_beta_from_energy_accepts_particle_aliases() -> None:
    energy = 2.0 * particle_mass("electron")

    assert beta_from_energy(energy, "positron") == pytest.approx(math.sqrt(3.0) / 2.0)


def test_beta_from_energy_is_one_for_massless_particles() -> None:
    assert beta_from_energy(0.0, "photon") == 1.0


def test_beta_from_energy_requires_total_energy_above_mass() -> None:
    with pytest.raises(ValueError, match="must be greater than mass"):
        beta_from_energy(PROTON_MASS_GEV, "proton")


def test_dp_pt_conversions_round_trip_with_beta() -> None:
    beta = beta_from_energy(2.0 * PROTON_MASS_GEV, "proton")
    dp = 0.0123

    assert pt2dp(dp2pt(dp, beta), beta) == pytest.approx(dp)
