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
from typing import TYPE_CHECKING

from omc3.model_creator import create_instance_and_model

from pymadng_utils.accelerators import LHC, PSB, PSB_FLAT_BOTTOM_GEV
from pymadng_utils.madx.make_sequence import make_madx_sequence
from pymadng_utils.model_creator.madng_utils import update_model_with_madng
from pymadng_utils.physics import PROTON_MASS_GEV

if TYPE_CHECKING:
    import pathlib

LOGGER = logging.getLogger(__name__)


def create_lhc_model(
    beam: int,
    output_dir: pathlib.Path,
    year: str,
    *,
    fetch: str = "afs",
    path: str | None = None,
    nat_tunes: tuple[float, float] = (0.28, 0.31),
    drv_tunes: tuple[float, float] | None = (0.27, 0.322),
    energy: float = 6800.0,
    modifiers: str | list[str] | None = None,
) -> None:
    """
    Create a complete LHC model for the specified beam.

    This function performs the full workflow:

    1. Creates model instance using omc3
    2. Exports the MAD-X sequence ``lhcb<beam>_saved.seq`` (for beam 2 this is the forward
       beam-4 tracking sequence, so ``seq_dir=1`` is used for the MAD-NG ``LHC`` descriptor)
    3. Updates model with MAD-NG (tune matching and twiss computation)

    Args:
        beam: Beam number (1 or 2).
        output_dir: Directory where model files will be created.
        year: LHC optics year.
        fetch: omc3 ``fetch`` method; ``path`` is required unless it is ``"afs"``.
        path: omc3 accelerator-model path for non-AFS fetch methods.
        nat_tunes: Natural fractional tunes [Q1, Q2].
        drv_tunes: Driven fractional tunes [Q1, Q2]; ``None`` skips the AC dipole.
        energy: Total beam energy in GeV (omc3 and MAD-X ``beam, energy=`` convention); the
            MAD-NG ``LHC`` descriptor gets ``energy - PROTON_MASS_GEV`` as kinetic energy.
        modifiers: omc3 optics modifier files.

    Raises:
        ValueError: If beam is not 1 or 2.
    """
    if beam not in (1, 2):
        raise ValueError(f"Beam must be 1 or 2, got {beam}")

    if fetch != "afs" and path is None:
        raise ValueError("Custom path must be provided if fetch method is not 'afs'")

    if isinstance(modifiers, str):
        modifiers = [modifiers]

    accelerator = LHC(
        beam=beam,
        sequence_file=output_dir / f"lhcb{beam}_saved.seq",
        kinetic_energy=energy - PROTON_MASS_GEV,
        seq_dir=1,  # beam 2 is exported as the forward beam-4 sequence (see make_madx_sequence)
    )

    LOGGER.info(f"\n{'=' * 70}")
    LOGGER.info(f"Creating LHC Model for Beam {beam}")
    LOGGER.info(f"{'=' * 70}")
    LOGGER.info(f"Output directory: {output_dir}")
    LOGGER.info(f"Natural tunes: {nat_tunes}")
    LOGGER.info(f"Driven tunes: {drv_tunes}")
    LOGGER.info(f"Total energy: {energy} GeV")
    LOGGER.info(f"Year: {year}")
    LOGGER.info(f"Modifiers: {modifiers}")
    LOGGER.info(f"{'=' * 70}\n")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Create base model with omc3
    LOGGER.info("Step 1: Creating base model with omc3...")
    create_drv_tunes = (0.0, 0.0) if drv_tunes is None else drv_tunes
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
        nat_tunes=list(nat_tunes),
        drv_tunes=list(create_drv_tunes),
        modifiers=modifiers,
        outputdir=output_dir,
    )
    LOGGER.info("✓ Base model created\n")

    # Step 2: Generate MAD-X sequences
    LOGGER.info("Step 2: Generating MAD-X sequences...")
    make_madx_sequence(output_dir, beam4=(beam == 2))
    LOGGER.info("✓ MAD-X sequences generated\n")

    # Step 3: Update with MAD-NG
    LOGGER.info("Step 3: Updating model with MAD-NG...")
    update_model_with_madng(accelerator, output_dir, tunes=nat_tunes, drv_tunes=drv_tunes)
    LOGGER.info("✓ Model update complete\n")

    LOGGER.info(f"{'=' * 70}")
    LOGGER.info(f"Model for beam {beam} created successfully!")
    LOGGER.info(f"Location: {output_dir}")
    LOGGER.info(f"{'=' * 70}\n")


def create_psb_model(
    ring: int,
    output_dir: pathlib.Path,
    year: str,
    *,
    fetch: str = "afs",
    path: str | None = None,
    nat_tunes: tuple[float, float] = (0.17, 0.225),
    drv_tunes: tuple[float, float] | None = None,
    kinetic_energy: float = PSB_FLAT_BOTTOM_GEV,
    dpp: float = 0.0,
    cycle_point: str = "1_flat_bottom",
    str_file: str = "psb_fb_lhcindiv.str",
    scenario: str = "lhc_indiv",
    update_with_madng: bool = True,
) -> None:
    """
    Create a complete PSB model for the specified ring.

    This function performs the full workflow:

    1. Creates model instance using omc3
    2. Generates MAD-X sequence files
    3. Updates model with MAD-NG (tune matching and twiss computation)

    ``update_with_madng=False`` stops after step 2, leaving the plain omc3
    model in place. PSB callers that seed the MAD-NG update with extra magnet
    strengths, or that need it re-run with ``convert_to_madx=False`` for
    in-process tracking, run their own MAD-NG step against this base model
    instead of the one this function would otherwise run -- so this flag lets
    them skip the redundant first pass rather than computing (and discarding)
    a Twiss twice.

    Args:
        ring: PSB ring number (1, 2, 3, or 4).
        output_dir: Directory where model files will be created.
        year: Scenario year/era.
        fetch: omc3 ``fetch`` method; ``path`` is required unless it is ``"afs"``.
        path: omc3 accelerator-model path for non-AFS fetch methods.
        nat_tunes: Natural fractional tunes [Q1, Q2].
        drv_tunes: Driven fractional tunes [Q1, Q2]. ``None`` skips the AC dipole excitation.
        kinetic_energy: Kinetic energy in GeV.
        dpp: Relative momentum deviation the model is built/twissed at.
        cycle_point: PSB cycle point.
        str_file: Strength file name.
        scenario: omc3 scenario name.
        update_with_madng: Run the MAD-NG update (step 3); see above.

    Raises:
        ValueError: If ring is not 1, 2, 3, or 4.
    """
    if ring not in (1, 2, 3, 4):
        raise ValueError(f"Ring must be 1, 2, 3, or 4, got {ring}")

    if fetch != "afs" and path is None:
        raise ValueError("Custom path must be provided if fetch method is not 'afs'")

    accelerator = PSB(
        ring=ring,
        sequence_file=output_dir / f"psb{ring}_saved.seq",
        kinetic_energy=kinetic_energy,
    )

    LOGGER.info(f"\n{'=' * 70}")
    LOGGER.info(f"Creating PSB Model for Ring {ring}")
    LOGGER.info(f"{'=' * 70}")
    LOGGER.info(f"Output directory: {output_dir}")
    LOGGER.info(f"Natural tunes: {nat_tunes}")
    LOGGER.info(f"Driven tunes: {drv_tunes}")
    LOGGER.info(f"Kinetic energy: {kinetic_energy} GeV")
    LOGGER.info(f"Year: {year}")
    LOGGER.info(f"{'=' * 70}\n")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Create base model with omc3
    LOGGER.info("Step 1: Creating base model with omc3...")
    LOGGER.debug("Model fetch path: %s", path)
    model_kwargs = {
        "outputdir": output_dir,
        "accel": "psbooster",
        "type": "nominal",
        "nat_tunes": list(nat_tunes),
        "dpp": dpp,
        "fetch": fetch,
        "path": path,
        "scenario": scenario,
        "year": year,
        "cycle_point": cycle_point,
        "str_file": str_file,
        "ring": ring,
        "list_choices": False,
        "show_help": False,
    }
    if drv_tunes is not None:
        model_kwargs["drv_tunes"] = list(drv_tunes)
        model_kwargs["driven_excitation"] = "acd"
    create_instance_and_model(**model_kwargs)
    LOGGER.info("✓ Base model created\n")

    # Step 2: Generate MAD-X sequence
    LOGGER.info("Step 2: Generating MAD-X sequence...")
    make_madx_sequence(output_dir)
    LOGGER.info("✓ MAD-X sequence generated\n")

    if not update_with_madng:
        LOGGER.info("Skipping step 3 (update_with_madng=False)\n")
        return

    # Step 3: Update with MAD-NG
    LOGGER.info("Step 3: Updating model with MAD-NG...")
    update_model_with_madng(
        accelerator, output_dir, tunes=nat_tunes, drv_tunes=drv_tunes, deltap=dpp
    )
    LOGGER.info("✓ Model update complete\n")

    LOGGER.info(f"{'=' * 70}")
    LOGGER.info(f"Model for ring {ring} created successfully!")
    LOGGER.info(f"Location: {output_dir}")
    LOGGER.info(f"{'=' * 70}\n")
