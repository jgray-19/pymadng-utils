"""Minimal accelerator definitions for MAD-facing helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any  # noqa: F401 — used in __init__ signature

from pymadng_utils.physics import beta_from_energy, dp2pt, particle_mass, pt2dp


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
        **kwargs: Any,
    ) -> None:
        assert not kwargs, f"Unexpected keyword arguments: {list(kwargs)}"
        super().__init__()
        self.sequence_file = Path(sequence_file)
        self.kinetic_energy = float(kinetic_energy)
        self.particle = str(particle)
        self.energy = self.kinetic_energy + particle_mass(self.particle)
        self.beta = beta_from_energy(self.energy, self.particle)
        self.bpm_pattern = str(bpm_pattern)

    def __repr__(self) -> str:
        """Return a developer-facing representation of public accelerator state."""
        fields = ", ".join(
            f"{name}={value!r}"
            for name, value in vars(self).items()
            if not name.startswith("_")
        )
        return f"{type(self).__name__}({fields})"

    def __str__(self) -> str:
        """Return a concise human-readable accelerator summary."""
        return (
            f"{type(self).__name__}(seq_name={self.seq_name}, "
            f"particle={self.particle}, "
            f"kinetic_energy={self.kinetic_energy:g} GeV, "
            f"sequence_file={self.sequence_file})"
        )

    def dp2pt(self, dp: float) -> float:
        """Convert relative momentum deviation ``dp/p`` to MAD-NG ``pt``."""
        return dp2pt(dp, self.beta)

    def pt2dp(self, pt: float) -> float:
        """Convert MAD-NG ``pt`` to relative momentum deviation ``dp/p``."""
        return pt2dp(pt, self.beta)

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
    def ac_dipole_name(self) -> str:
        """Return the AC-dipole exciter marker and the offset from the marker for installation."""
        pass

    def acd_marker_name(self, side: str) -> str:
        """Return a stable row name for the AC-dipole marker state."""
        if side not in {"before", "after"}:
            raise ValueError(f"side must be 'before' or 'after', got {side!r}")
        marker_name = self.ac_dipole_name
        return f"{marker_name}_{side}"

    def kicker_marker_name(self, kicker_name: str) -> str:
        """Return the measured initial-condition marker name for kicker tracking."""
        return kicker_name

    def kicker_cycle_marker_name(self, kicker_name: str) -> str:
        """Return the unobserved centre marker used to cycle kicker-mode tracking."""
        return f"{kicker_name}_centre"

    # @property
    # @abstractmethod
    # def get_exciter_bpm(self) -> tuple[str, str]:
    #     """Return the two BPM names adjacent to the exciter."""
    #     pass

    def apply_accelerator_specific_errors(self, mad_iface: Any) -> None:
        """Apply machine-specific startup errors to a loaded MAD sequence."""
        del mad_iface

    def get_perturbation_families(self) -> dict[str, dict[str, str | float | dict]]:
        """Return per-family perturbation metadata keyed by family code d/q/s."""
        return {}

    @property
    @abstractmethod
    def tune_variables(self) -> tuple[str, str]:
        """Return PSB tune variable names."""
        pass

    @property
    @abstractmethod
    def tune_integers(self) -> tuple[int, int]:
        """Return PSB integer tunes."""
        pass
