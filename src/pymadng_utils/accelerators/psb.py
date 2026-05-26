"""PSB-specific accelerator implementation."""

from __future__ import annotations

import re
from pathlib import Path

from pymadng_utils.accelerators.base import (
    Accelerator,
)

PSB_FLAT_BOTTOM_GEV = 0.160


def _infer_psb_ring_number(sequence_path: Path) -> int:
    match = re.search(r"psb(\d+)", sequence_path.name, re.IGNORECASE)
    if match is not None:
        return int(match.group(1))
    raise ValueError(
        f"Could not infer PSB ring number from sequence file name: {sequence_path.name}"
    )


class PSB(Accelerator):
    """Proton Synchrotron Booster accelerator configuration."""

    BPM_PATTERN_TEMPLATE = "^BR{ring}%.BPM.*{ring}$"
    SEXTUPOLE_PATTERN = r"^BR%d+%.XNO.*"

    def __init__(
        self,
        sequence_file: Path | str,
        ring: int | None = None,
        kinetic_energy: float = PSB_FLAT_BOTTOM_GEV,
        bpm_pattern: str | None = None,
        particle: str = "proton",
        **kwargs,
    ) -> None:
        if ring is None:
            ring = _infer_psb_ring_number(Path(sequence_file))
        if ring not in (1, 2, 3, 4):
            raise ValueError(f"PSB ring must be 1, 2, 3, or 4, got {ring}")

        self.ring = ring
        super().__init__(
            sequence_file=sequence_file,
            kinetic_energy=kinetic_energy,
            bpm_pattern=bpm_pattern or self.BPM_PATTERN_TEMPLATE.format(ring=ring),
            particle=particle,
            **kwargs,
        )

    @property
    def seq_name(self) -> str:
        """Return the sequence name for the selected PSB ring."""
        return f"psb{self.ring}"

    @property
    def ac_dipole_location(self) -> tuple[str, float]:
        """Return the PSB AC-dipole installation marker and offset."""
        return (f"BR{self.ring}.DES3L1", 0.565 / 2)

    # def get_exciter_bpm(self) -> tuple[str, str]:
    #     """Return the two BPMs adjacent to the PSB exciter."""
    #     return f"BR{self.ring}.BPM3L3", f"BR{self.ring}.BPM4L3"

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
