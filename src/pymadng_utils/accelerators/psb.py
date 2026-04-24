"""PSB-specific accelerator implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymadng_utils.accelerators.base import (
    Accelerator,
)

if TYPE_CHECKING:
    from pathlib import Path


PSB_FLAT_BOTTOM_MOMENTUM_GEV = 0.160


class PSB(Accelerator):
    """Proton Synchrotron Booster accelerator configuration."""

    BPM_PATTERN_TEMPLATE = "^BR{ring}%.BPM"

    def __init__(
        self,
        ring: int,
        sequence_file: Path | str,
        pc: float = PSB_FLAT_BOTTOM_MOMENTUM_GEV,
        bpm_pattern: str | None = None,
        particle: str = "proton",
    ) -> None:
        if ring not in (1, 2, 3, 4):
            raise ValueError(f"PSB ring must be 1, 2, 3, or 4, got {ring}")

        self.ring = ring
        super().__init__(
            sequence_file=sequence_file,
            pc=pc,
            bpm_pattern=bpm_pattern or self.BPM_PATTERN_TEMPLATE.format(ring=ring),
            particle=particle,
        )

    @property
    def seq_name(self) -> str:
        """Return the sequence name for the selected PSB ring."""
        return f"psb{self.ring}"

    @property
    def ac_dipole_location(self) -> tuple[str, float]:
        """PSB does not use the LHC AC-dipole exciter model."""
        raise NotImplementedError("PSB does not define an AC-dipole exciter marker")

    def get_exciter_bpm(self) -> tuple[str, str]:
        """Return the two BPMs adjacent to the PSB exciter."""
        return f"BR{self.ring}.BPM3L3", f"BR{self.ring}.BPM4L3"

    @property
    def tune_variables(self) -> tuple[str, str]:
        """Return PSB tune variable names."""
        return "kBRQF", "kBRQD"

    @property
    def tune_integers(self) -> tuple[int, int]:
        """Return PSB integer tunes."""
        return 4, 4

    @staticmethod
    def infer_monitor_plane(bpm_name: str) -> str:
        """Infer measurement plane from PSB monitor names."""
        name = bpm_name.upper()
        if any(token in name for token in (".BPM", ".BWS", ".BPP", ".BPT")):
            return "HV"
        raise ValueError(
            f"Unsupported PSB monitor name for plane inference: {bpm_name}"
        )
