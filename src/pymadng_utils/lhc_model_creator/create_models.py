#!/usr/bin/env python3
"""
Script to create LHC model directories for beam 1 and beam 2 at 18cm optics using omc3.

This script orchestrates the complete model creation workflow:
1. Creates nominal model using omc3
2. Generates MAD-X sequences
3. Updates model with MAD-NG (tune matching, twiss computation)
4. Exports TFS files in MAD-X format
"""
from __future__ import annotations

import logging
import pathlib

from omc3.model_creator import create_instance_and_model

from .madng_utils import update_model_with_madng
from .make_sequence import make_lhc_sequence

LOGGER = logging.getLogger(__name__)

def create_lhc_model(
    beam: int,
    output_dir: pathlib.Path,
    year: str,
    *,
    fetch: str = "afs",
    path: str | None = None,
    nat_tunes: list[float] = [0.28, 0.31],
    drv_tunes: list[float] = [0.27, 0.322],
    energy: float = 6800.0,
    modifiers: str | list[str] | None = None,
) -> None:
    """
    Create a complete LHC model for the specified beam.

    This function performs the full workflow:
    1. Creates model instance using omc3
    2. Generates MAD-X sequence files (including beam4 for tracking if beam=2)
    3. Updates model with MAD-NG (tune matching and twiss computation)

    Parameters
    ----------
    beam : int
        Beam number (1 or 2).
    output_dir : pathlib.Path
        Directory where model files will be created.
    year : str
        LHC year/era.
    nat_tunes : list[float], optional
        Natural fractional tunes [Q1, Q2]. Defaults to config values.
    drv_tunes : list[float], optional
        Driven fractional tunes [Q1, Q2]. Defaults to config values.
    energy : float, optional
        Beam energy in GeV. Defaults to config value.
    modifier : str, optional
        Optics modifier file name. Defaults to config value.

    Raises
    ------
    ValueError
        If beam is not 1 or 2.
    """
    if beam not in (1, 2):
        raise ValueError(f"Beam must be 1 or 2, got {beam}")

    if fetch != "afs" and path is None:
        raise ValueError("Custom path must be provided if fetch method is not 'afs'")

    if isinstance(modifiers, str):
        modifiers = [modifiers]

    LOGGER.info(f"\n{'=' * 70}")
    LOGGER.info(f"Creating LHC Model for Beam {beam}")
    LOGGER.info(f"{'=' * 70}")
    LOGGER.info(f"Output directory: {output_dir}")
    LOGGER.info(f"Natural tunes: {nat_tunes}")
    LOGGER.info(f"Driven tunes: {drv_tunes}")
    LOGGER.info(f"Energy: {energy} GeV")
    LOGGER.info(f"Year: {year}")
    LOGGER.info(f"Modifiers: {modifiers}")
    LOGGER.info(f"{'=' * 70}\n")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Create base model with omc3
    LOGGER.info("Step 1: Creating base model with omc3...")
    create_drv_tunes = [0.0, 0.0] if drv_tunes is None else drv_tunes
    LOGGER.debug("Model fetch path: %s", path)
    create_instance_and_model(
        accel="lhc",
        fetch=fetch,
        path=path,
        type="nominal",
        beam=beam,
        year=year,
        driven_excitation="acd",
        energy=energy,
        nat_tunes=nat_tunes,
        drv_tunes=create_drv_tunes,
        modifiers=modifiers,
        outputdir=output_dir,
    )
    LOGGER.info("✓ Base model created\n")

    # Step 2: Generate MAD-X sequences
    LOGGER.info("Step 2: Generating MAD-X sequences...")
    make_lhc_sequence(beam, output_dir, energy, beam4=(beam == 2))
    LOGGER.info("✓ MAD-X sequences generated\n")

    # Step 3: Update with MAD-NG
    LOGGER.info("Step 3: Updating model with MAD-NG...")
    update_model_with_madng(
        beam,
        output_dir,
        tunes=nat_tunes,
        drv_tunes=drv_tunes,
    )
    LOGGER.info("✓ Model update complete\n")

    LOGGER.info(f"{'=' * 70}")
    LOGGER.info(f"Model for beam {beam} created successfully!")
    LOGGER.info(f"Location: {output_dir}")
    LOGGER.info(f"{'=' * 70}\n")


def main() -> None:
    """Main entry point for creating LHC models."""
    # Determine output directory relative to this script
    data_dir = pathlib.Path(__file__).parent.parent / "data"

    # Model naming convention: model_b{beam}__t{q1}_{q2}_{optics}
    nat_tunes = [0.28, 0.31]
    optics_label = "18cm"

    print("\n" + "=" * 70)
    print("LHC Model Creation Script")
    print("=" * 70 + "\n")

    # Create Beam 1 model
    model_dir_b1 = data_dir / f"model_b1__t{nat_tunes[0]}_{nat_tunes[1]}_{optics_label}"
    create_lhc_model(beam=1, output_dir=model_dir_b1, year="2025")

    # Create Beam 2 model
    model_dir_b2 = data_dir / f"model_b2__t{nat_tunes[0]}_{nat_tunes[1]}_{optics_label}"
    create_lhc_model(beam=2, output_dir=model_dir_b2, year="2025")
    print("\n" + "=" * 70)
    print("All models created successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
