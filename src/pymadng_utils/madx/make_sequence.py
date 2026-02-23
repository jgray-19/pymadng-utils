from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from cpymad.madx import Madx

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

LOGGER = logging.getLogger(__name__)

MADX_FILENAME = "job.create_model_nominal.madx"

def make_madx_sequence(
    model_dir: Path,
    sequence_madx_name: str,
    sequence_save_path: Path,
    madx_filename: str | None = None,
    customisation_command: Callable[[str], str] | None = None, # Optional function that takes a string and returns a modified string
) -> Path:
    """
    Generate and save the MAD-X sequence file from an OMC3-generated model and MAD-X job file.

    Args:
        model_dir: Directory containing the OMC3-generated model and MAD-X job file.
        sequence_save_path: Path where the generated sequence file should be saved.
        madx_filename: Optional name of the MAD-X job file. If None, uses default 'madx_job.madx'.
        customisation_command: Optional function that takes a string and returns a modified string.
            If provided, this function will be applied to each line of the MAD-X job file before sending it to MAD-X.
            This allows for dynamic modifications of the MAD-X commands based on the model or other parameters.

    Returns:
        Path to the generated MAD-X sequence file.

    Raises:
        FileNotFoundError: If the MAD-X job file is not found in the model directory.
    """

    filename = madx_filename or MADX_FILENAME
    madx_file = model_dir / filename

    if not madx_file.exists():
        raise FileNotFoundError(f"MAD-X file not found: {madx_file}")

    with madx_file.open("r") as f:
        lines = f.readlines()


    with Madx(stdout=False) as madx:
        madx.chdir(str(model_dir))

        for line in lines:
            # Apply customisation command if provided
            if customisation_command:
                line = customisation_command(line)

            # Check if twiss[_a-z]*\.dat is in the line, then we stop processing and save the sequence
            if re.search(r"twiss[_a-z]*\.dat", line):
                # Stop processing and save the sequence
                save_cmd = f"""
set, format="-16.16e";
save, sequence={sequence_madx_name}, file="{sequence_save_path.absolute()}", noexpr=false;
                """
                madx.input(save_cmd)
                break

            madx.send(line)
    LOGGER.info(f"Saved MAD-X sequence to {sequence_save_path}")
    return sequence_save_path
