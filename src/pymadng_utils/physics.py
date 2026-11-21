"""Beam-physics helpers matching MAD-NG conventions. Using pretty much identical code to MAD-NG"""

from __future__ import annotations

import math

PHOTON_MASS_GEV = 0.0
ELECTRON_MASS_GEV = 0.00051099895000
PROTON_MASS_GEV = 0.93827208816
NEUTRON_MASS_GEV = 0.93956542052
MUON_MASS_GEV = 0.1056583755
DEUTERON_MASS_GEV = 1.87561294257

PARTICLE_MASSES_GEV = {
    "photon": PHOTON_MASS_GEV,
    "electron": ELECTRON_MASS_GEV,
    "positron": ELECTRON_MASS_GEV,
    "proton": PROTON_MASS_GEV,
    "antiproton": PROTON_MASS_GEV,
    "neutron": NEUTRON_MASS_GEV,
    "antineutron": NEUTRON_MASS_GEV,
    "ion": NEUTRON_MASS_GEV,
    "muon": MUON_MASS_GEV,
    "antimuon": MUON_MASS_GEV,
    "negmuon": MUON_MASS_GEV,
    "posmuon": MUON_MASS_GEV,
    "deuteron": DEUTERON_MASS_GEV,
    "antideuteron": DEUTERON_MASS_GEV,
}


def particle_mass(particle: str) -> float:
    """Return the MAD-NG particle mass in GeV."""
    try:
        return PARTICLE_MASSES_GEV[str(particle).strip().lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported particle: {particle}") from exc


def beta_from_energy(energy: float, particle: str = "proton") -> float:
    """Compute relativistic beta from total energy [GeV] and particle name."""
    mass = particle_mass(particle)
    if mass == 0.0:
        return 1.0
    energy = float(energy)
    if energy <= mass:
        raise ValueError(f"Total energy {energy} GeV must be greater than mass {mass} GeV")
    mass_over_energy = mass / energy
    return math.sqrt((1.0 - mass_over_energy) * (1.0 + mass_over_energy))


def dp2pt(dp: float, beta0: float = 1.0) -> float:
    """Convert relative momentum deviation ``dp/p`` to MAD-NG ``pt``.

    Uses the cancellation-free identity ``sqrt(a) - b = (a - b^2)/(sqrt(a) + b)``
    to avoid catastrophic cancellation: the naive ``sqrt((1+dp)^2 + 1/beta0^2 -
    1) - 1/beta0`` subtracts two ~1 quantities to yield a ~dp result, losing
    ~3 significant digits for small ``dp`` (relative error up to ~1e-12). The
    rewritten numerator ``2*dp + dp^2`` carries no cancellation, giving
    machine-precision accuracy.
    """
    dp = float(dp)
    if dp == 0.0:
        return 0.0
    inv_beta0 = 1.0 / float(beta0)
    radicand = (1.0 + dp) ** 2 + (inv_beta0**2 - 1.0)
    return (2.0 * dp + dp * dp) / (math.sqrt(radicand) + inv_beta0)


def pt2dp(pt: float, beta0: float = 1.0) -> float:
    """Convert MAD-NG ``pt`` to relative momentum deviation ``dp/p``.

    Uses the cancellation-free identity ``sqrt(a) - 1 = (a - 1)/(sqrt(a) + 1)``:
    the naive ``sqrt(1 + 2*pt/beta0 + pt^2) - 1`` loses ~3 significant digits for
    small ``pt`` (it is ``sqrt(1 + small) - 1``), whereas the rewritten
    numerator ``2*pt/beta0 + pt^2`` has no cancellation and stays accurate to
    machine precision.
    """
    pt = float(pt)
    if pt == 0.0:
        return 0.0
    inv_beta0 = 1.0 / float(beta0)
    radicand = 1.0 + 2.0 * pt * inv_beta0 + pt**2
    return (2.0 * pt * inv_beta0 + pt * pt) / (math.sqrt(radicand) + 1.0)
