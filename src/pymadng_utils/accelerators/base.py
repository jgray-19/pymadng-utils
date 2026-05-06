"""Minimal accelerator definitions for MAD-facing helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

PROTON_MASS_GEV = 0.9382720813
ELECTRON_MASS_GEV = 0.0005109989461


PARTICLE_MASSES_GEV = {
    "proton": PROTON_MASS_GEV,
    "electron": ELECTRON_MASS_GEV,
    "positron": ELECTRON_MASS_GEV,
}



class Accelerator(ABC):
    """Small accelerator descriptor modelled on ``aba_optimiser``.

    The repository only needs the machine-specific fields that the MAD-NG ACD
    driver consumes directly: sequence path, MAD sequence name, beam energy and
    BPM pattern.
    """

    def __init__(
        self,
        sequence_file: Path | str,
        kinetic_energy: float,
        bpm_pattern: str = "BPM",
        particle: str = "proton",
    ) -> None:
        self.sequence_file = Path(sequence_file)
        self.kinetic_energy = float(kinetic_energy)
        try:
            self.energy = self.kinetic_energy + PARTICLE_MASSES_GEV[particle]
        except KeyError:
            raise ValueError(f"Unsupported particle: {particle}")
        self.bpm_pattern = str(bpm_pattern)
        self.particle = str(particle)

    @property
    @abstractmethod
    def seq_name(self) -> str:
        """Return the sequence name for this accelerator.

        Returns:
            Sequence name to use in MAD
        """
        pass

    @property
    @abstractmethod
    def ac_dipole_location(self) -> tuple[str, float]:
        """Return the AC-dipole exciter marker and the offset from the marker for installation."""
        pass

    @property
    @abstractmethod
    def get_exciter_bpm(self) -> tuple[str, str]:
        """Return the two BPM names adjacent to the exciter."""
        pass

    def apply_accelerator_specific_errors(self, mad_iface: Any) -> None:
        """Apply machine-specific startup errors to a loaded MAD sequence."""
        del mad_iface

    def get_perturbation_families(self) -> dict[str, dict[str, str | float | dict]]:
        """Return per-family perturbation metadata keyed by family code d/q/s."""
        return {}
