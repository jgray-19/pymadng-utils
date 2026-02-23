"""MAD-NG utility functions for LHC model creation and tune matching."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pymadng_utils.mad import LhcModelCreatorMadInterface
from pymadng_utils.madx.tfs_utils import convert_multiple_tfs_files

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger(__name__)

def update_model_with_madng(
    beam: int,
    model_dir: Path,
    *,
    tunes: list[float] = [0.28, 0.31],
    drv_tunes: list[float] | None = None,
    matching_knob: str = "_op",
) -> None:
    """
    Update LHC model using MAD-NG with tune matching and twiss computation.

    This is the main workflow function that:
    1. Initializes the MAD-NG model
    2. Matches tunes to target values
    3. Computes and exports twiss tables (elements, natural, AC dipole)
    4. Converts TFS files to MAD-X format

    Parameters
    ----------
    beam : int
        Beam number (1 or 2).
    model_dir : Path
        Model directory containing saved sequences and for output files.
    tunes : list[float], optional
        Natural fractional tunes [Q1, Q2]. Defaults to [0.28, 0.31].
    drv_tunes : list[float], optional
        Driven fractional tunes [Q1, Q2]. Defaults to [0.0, 0.0].
    matching_knob : str, optional
        Suffix for the tune matching knobs. Default is "_op".
    """
    LOGGER.info(f"\n{'=' * 60}")
    LOGGER.info(f"Updating model for beam {beam} with MAD-NG")
    LOGGER.info(f"Natural tunes: {tunes}, Driven tunes: {drv_tunes}")
    LOGGER.info(f"{'=' * 60}\n")

    mad_interface = LhcModelCreatorMadInterface(
        model_dir=model_dir,
        beam=beam,
        tunes=tunes,
        drv_tunes=drv_tunes,
        tune_knobs_suffix=matching_knob,
    )
    try:
        mad_interface.compute_and_export_twiss_tables()
    finally:
        mad_interface.close()

    # Convert TFS files to MAD-X format
    tfs_files = [
        model_dir / "twiss_ac.dat",
        model_dir / "twiss_elements.dat",
        model_dir / "twiss.dat",
    ]
    convert_multiple_tfs_files(tfs_files)

    LOGGER.info(f"\nModel update complete for beam {beam}\n")
