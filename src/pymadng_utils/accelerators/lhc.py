"""LHC-specific accelerator implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from pymadng_utils.accelerators.base import Accelerator

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


class LHC(Accelerator):
    """Large Hadron Collider accelerator configuration.

    Holds the beam number, sequence direction, BPM pattern, operational tune knobs
    (``dqx_b<beam><suffix>``) and the integer tunes (62, 60).
    """

    BPM_PATTERN = "^BPM.*$"
    QUAD_ERROR_TABLE: ClassVar[dict[str, float]] = {
        "MQ.": 18e-4,
        "MQM": 12e-4,
        "MQY": 8e-4,
        "MQX": 10e-4,
        "MQW": 15e-4,
    }

    def __init__(
        self,
        beam: int,
        sequence_file: Path | str,
        kinetic_energy: float = 6800.0,
        bpm_pattern: str = BPM_PATTERN,
        particle: str = "proton",
        tune_knobs_suffix: str = "_op",
        seq_dir: int | None = None,
        **kwargs,
    ):
        """Initialise LHC accelerator for a specific beam.

        Args:
            beam: Beam number (1 or 2)
            sequence_file: Path to sequence file
            kinetic_energy: Particle kinetic energy in GeV (default 6800 GeV for LHC)
            bpm_pattern: Pattern for selecting BPMs
            particle: Type of particle (default "proton")
            tune_knobs_suffix: Suffix of the MAD-X tune knobs ``dqx_b<beam>`` / ``dqy_b<beam>``
            seq_dir: MAD-NG sequence direction. Required for beam 2: -1 for the MAD-X beam-2
                sequence (listed in beam-1 order), 1 for the beam-4 tracking sequence (also
                named ``lhcb2``). Defaults to 1 for beam 1.
        Raises:
            ValueError: If an invalid beam number is provided
        """
        if beam not in (1, 2):
            raise ValueError(f"LHC beam must be 1 or 2, got {beam}")
        self.beam = beam
        self.tune_knobs_suffix = tune_knobs_suffix
        if seq_dir is None:
            if beam == 2:
                raise ValueError(
                    "LHC beam 2 needs seq_dir: -1 (MAD-X beam 2) or 1 (beam-4 tracking)"
                )
            seq_dir = 1
        self.seq_dir = seq_dir
        super().__init__(
            sequence_file=sequence_file,
            kinetic_energy=kinetic_energy,
            bpm_pattern=bpm_pattern,
            particle=particle,
            **kwargs,
        )

    @property
    def seq_name(self) -> str:
        """Return the sequence name for this LHC beam."""
        return f"lhcb{self.beam}"

    @property
    def tune_variables(self) -> tuple[str, str]:
        """Return LHC operational tune knob names."""
        return (
            f"dqx_b{self.beam}{self.tune_knobs_suffix}",
            f"dqy_b{self.beam}{self.tune_knobs_suffix}",
        )

    @property
    def tune_integers(self) -> tuple[int, int]:
        """Return LHC integer tunes."""
        return 62, 60

    @property
    def ac_dipole_name(self) -> str:
        """Return the LHC AC-dipole element name."""
        return f"MKQA.6L4.B{self.beam}"

    def get_perturbation_families(self) -> dict[str, dict[str, float | str | dict]]:
        """Return perturbation-family metadata for LHC magnets."""
        return {
            "d": {
                "default_rel_std": 1e-4,
                "pattern": r"^MB",
            },
            "q": {
                "relative_error_table": self.QUAD_ERROR_TABLE,
                "pattern": r"^MQ",
            },
            "s": {
                "default_rel_std": 1e-4,
                "pattern": r"^MS",
            },
        }
