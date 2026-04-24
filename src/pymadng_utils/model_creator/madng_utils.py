"""MAD-NG utility functions for LHC model creation and tune matching."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pymadng_utils.mad.model_creator_mad_interface import ModelCreatorMadInterface
from pymadng_utils.madx.tfs_utils import convert_multiple_tfs_files

if TYPE_CHECKING:
    from pathlib import Path

    from pymadng_utils.accelerators import Accelerator

LOGGER = logging.getLogger(__name__)


def update_model_with_madng(
    accelerator: Accelerator,
    model_dir: Path,
    tunes: list[float] = [0.28, 0.31],
    *,
    drv_tunes: list[float] | None = None,
    convert_to_madx: bool = True,
) -> None:
    """
    Update model using MAD-NG with tune matching and twiss computation.

    This is the main workflow function that:
    1. Initializes the MAD-NG model
    2. Matches tunes to target values
    3. Computes and exports twiss tables (elements, natural, AC dipole)
    4. Converts TFS files to MAD-X format

    Args:
        accelerator: Accelerator configuration object
        model_dir: Directory where model files are located and will be updated
        tunes: Target fractional tunes [Q1, Q2] to match in the model
        drv_tunes: Optional target driven tunes [Q1, Q2] for tracking mode
        convert_to_madx: Whether to convert TFS files to MAD-X format after export
    """
    LOGGER.info(f"\n{'=' * 60}")
    LOGGER.info(f"Updating model for {accelerator.seq_name} with MAD-NG")
    LOGGER.info(f"Natural tunes: {tunes}, Driven tunes: {drv_tunes}")
    LOGGER.info(f"{'=' * 60}\n")

    with ModelCreatorMadInterface(
        accelerator=accelerator,
        model_dir=model_dir,
        tunes=tunes,
        drv_tunes=drv_tunes,
    ) as mad_interface:
        mad_interface.compute_and_export_twiss_tables()

    if convert_to_madx:
        LOGGER.info("Converting TFS files to MAD-X format...")
        # Convert TFS files to MAD-X format
        tfs_files = [
            model_dir / "twiss_ac.dat",
            model_dir / "twiss_elements.dat",
            model_dir / "twiss.dat",
        ]
        convert_multiple_tfs_files(tfs_files)

    LOGGER.info(f"\nModel update complete for {accelerator.seq_name}\n")
