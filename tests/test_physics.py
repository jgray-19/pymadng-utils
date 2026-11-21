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


@pytest.mark.parametrize("beta0", [1.0, 0.99999999, 0.52, 0.34])
@pytest.mark.parametrize("dp", [1e-2, 1e-3, 1e-4, 1e-5, -1e-4])
def test_dp_pt_round_trip_is_machine_precision(beta0: float, dp: float) -> None:
    """dp -> pt -> dp must round-trip to ~machine precision.

    The conversions are written in cancellation-free form; the naive
    ``sqrt(1 + small) - const`` form loses ~3 significant digits for small ``dp``
    (relative round-trip error up to ~1e-12, worse at low beta), which this test
    guards against. A tolerance of 1e-14 is comfortably met by the fixed form
    but fails the naive one.
    """
    assert pt2dp(dp2pt(dp, beta0), beta0) == pytest.approx(dp, rel=1e-14, abs=1e-18)


def test_dp2pt_matches_high_precision_reference() -> None:
    """dp2pt agrees with a 50-digit Decimal evaluation to machine precision."""
    from decimal import Decimal, getcontext

    getcontext().prec = 50
    beta0 = 0.52
    dp = 1e-4
    inv_beta0 = Decimal(1) / Decimal(str(beta0))
    exact = float(
        ((Decimal(1) + Decimal(str(dp))) ** 2 + (inv_beta0**2 - 1)).sqrt() - inv_beta0
    )
    assert dp2pt(dp, beta0) == pytest.approx(exact, rel=1e-15, abs=1e-18)
