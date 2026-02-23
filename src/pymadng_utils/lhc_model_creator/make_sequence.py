"""MAD-X utility functions for LHC model creation."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pymadng_utils.madx import make_madx_sequence

if TYPE_CHECKING:
    import pathlib

LOGGER = logging.getLogger(__name__)

def make_lhc_sequence(
    beam: int,
    model_dir: pathlib.Path,
    energy: float,
    *,
    seq_outdir: pathlib.Path | None = None,
    beam4: bool = False,
    madx_filename: str | None = None,
) -> pathlib.Path:
    """
    Generate and save the MAD-X sequence file for the specified beam.

    This function reads the MAD-X job file, processes it line by line,
    and saves the sequence. For beam 4 mode (tracking), it adjusts beam
    settings and uses the lhcb4.seq file instead of lhc.seq.

    Parameters
    ----------
    beam : int
        Beam number (1 or 2).
    model_dir : pathlib.Path
        Directory containing the model files.
    seq_outdir : pathlib.Path, optional
        Output directory for the generated sequence file. If None,
        saves in model_dir.
    beam4 : bool, optional
        If True, configure for beam 4 tracking mode (only valid for beam 2).
        Default is False.
    madx_filename : str, optional
        Name of the MAD-X job file. If None, uses default from config.

    Raises
    ------
    AssertionError
        If beam4 is True but beam is not 2.
    FileNotFoundError
        If the MAD-X job file doesn't exist.
    """
    if beam4 and beam != 2:
        raise ValueError("Beam 4 sequence can only be generated for beam 2")

    if beam4:
        LOGGER.info(f"Generating beam4 sequence for tracking (beam {beam})")

    if beam4:
        def customisation_command(line: str) -> str:
            # Handle beam4 specific modifications
            if "define_nominal_beams" in line:
                # Override with beam4 settings
                return (
                    f"beam, sequence=LHCB2, particle=proton, "
                    f"energy={energy}, bv=1;"
                )

            if "acc-models-lhc/lhc.seq" in line:
                # Use beam4 sequence file instead
                return line.replace("acc-models-lhc/lhc.seq", "acc-models-lhc/lhcb4.seq")

            return line
    else:
        customisation_command = None

    seq_path = seq_outdir / f"lhcb{beam}_saved.seq" if seq_outdir else model_dir / f"lhcb{beam}_saved.seq"
    return make_madx_sequence(
        model_dir=model_dir,
        sequence_madx_name=f"lhcb{beam}_saved.seq",
        sequence_save_path=seq_path,
        madx_filename=madx_filename,
        customisation_command=customisation_command,
    )
