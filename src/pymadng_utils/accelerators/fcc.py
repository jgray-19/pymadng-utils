"""FCC-ee accelerator implementation (LCC lattice, single ring)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymadng_utils.accelerators.base import Accelerator
from pymadng_utils.physics import particle_mass

if TYPE_CHECKING:
    from pathlib import Path

#: Total beam energy per FCC-ee mode, GeV.
FCC_ENERGY_GEV = {"z": 45.6, "w": 80.0, "h": 120.0, "t": 182.5}
#: Integer tunes of the LCC_107 Z lattice (166.16, 162.20).
FCC_Z_TUNE_INTEGERS = (166, 162)


class FCC(Accelerator):
    """FCC-ee (LCC optics) accelerator configuration.

    The LCC lattices are a single ring (``fccee_p_ring``) with lower-case element
    names: BPMs ``bpm_<quad>``, quadrupoles ``q*``, and paired correctors
    ``hcor_<quad>`` / ``vcor_<quad>`` (MAD-X ``kicker`` with ``hkick`` / ``vkick``).
    MAD-NG upper-cases element names when loading the madx, so the Lua patterns here
    are upper case (MAD-X variables stay lower case).
    """

    SEQUENCE_NAME = "fccee_p_ring"
    BPM_PATTERN = "^BPM_.*$"
    CORRECTOR_PATTERN = "^[HV]COR_"
    #: Relative k1 calibration error used for the FCC-ee LOCO studies.
    QUAD_REL_STD = 0.5e-2
    #: The LCC madx is written for MAD-X's default rbarc=true (rbend l is the chord).
    RBARC = True
    #: Ignore the beam charge like MAD-X does (otherwise an electron flips every magnet strength).
    NOCHARGE = True

    def __init__(
        self,
        sequence_file: Path | str,
        kinetic_energy: float | None = None,
        bpm_pattern: str = BPM_PATTERN,
        particle: str = "electron",
        mode: str = "z",
        **kwargs,
    ):
        """Initialise the FCC-ee accelerator.

        Args:
            sequence_file: Path to the MAD-X sequence file (e.g. ``fccee_z.madx``)
            kinetic_energy: Particle kinetic energy in GeV (default: the mode's beam energy
                minus the particle mass)
            bpm_pattern: Pattern for selecting BPMs
            particle: Type of particle (default "electron"; MAD-NG runs with ``nocharge`` as the madx ignores the charge)
            mode: FCC-ee running mode, one of ``z``, ``w``, ``h``, ``t``

        Raises:
            ValueError: If an unknown mode is given
        """
        mode = mode.lower()
        if mode not in FCC_ENERGY_GEV:
            raise ValueError(f"FCC mode must be one of {sorted(FCC_ENERGY_GEV)}, got {mode!r}")
        self.mode = mode
        super().__init__(
            sequence_file=sequence_file,
            kinetic_energy=(
                FCC_ENERGY_GEV[mode] - particle_mass(particle) if kinetic_energy is None else kinetic_energy
            ),
            bpm_pattern=bpm_pattern,
            particle=particle,
            **kwargs,
        )

    @property
    def seq_name(self) -> str:
        """Return the sequence name of the FCC-ee ring."""
        return self.SEQUENCE_NAME

    @property
    def tune_variables(self) -> tuple[str, str]:
        """The LCC lattice files define no tune knobs."""
        raise NotImplementedError("The FCC-ee LCC lattice has no tune knobs")

    @property
    def tune_integers(self) -> tuple[int, int]:
        """Return the integer tunes (Z lattice)."""
        if self.mode != "z":
            raise NotImplementedError(f"Integer tunes are only known for the Z lattice, not {self.mode!r}")
        return FCC_Z_TUNE_INTEGERS

    @property
    def ac_dipole_name(self) -> str:
        """FCC-ee has no AC dipole."""
        raise NotImplementedError("FCC-ee has no AC-dipole exciter")

    def get_perturbation_families(self) -> dict[str, dict[str, float | str | dict]]:
        """Return perturbation-family metadata for FCC-ee magnets."""
        return {
            "q": {
                "default_rel_std": self.QUAD_REL_STD,
                "pattern": r"(?i)^q",
            },
        }
