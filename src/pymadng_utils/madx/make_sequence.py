"""MAD-X utility functions for model sequence creation."""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from cpymad.madx import Madx
from omc3.model.accelerators.lhc import Lhc
from omc3.model.accelerators.sps import Sps
from omc3.model.constants import JOB_MODEL_MADX_NOMINAL
from omc3.model.model_creators.manager import CreatorType, get_model_creator_class

from pymadng_utils.madx.constants import (
    _DEFINE_NOMINAL_BEAMS_RE,
    _LHC_USE_SEQUENCE_RE,
    _LHC_YEAR_RE,
    _POST_OPTICS_INSERT_MARKERS,
    _PSB_MATCH_END_RE,
    _PSB_USE_SEQUENCE_RE,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from omc3.model.model_creators.abstract_model_creator import ModelCreator

LOGGER = logging.getLogger(__name__)


def _read_nominal_job_text(model_dir: Path) -> str:
    """Return the nominal OMC3 MAD-X job file contents."""
    job_file = model_dir / JOB_MODEL_MADX_NOMINAL
    if not job_file.exists():
        raise FileNotFoundError(
            f"Expected nominal MAD-X job file not found: {job_file}"
        )
    return job_file.read_text(errors="ignore")


def _adapt_script_to_beam4(base_script: str, beam: int, energy: float) -> str:
    """Adapt creator base script for beam4 tracking (beam 2 only)."""
    if beam != 2:
        raise ValueError("beam4 script adaptation is only valid for beam 2.")

    script = base_script.replace("lhc.seq", "lhcb4.seq")
    beam4_cmd = f"beam, sequence=LHCB2, particle=proton, energy={energy}, bv=1;"

    if not _DEFINE_NOMINAL_BEAMS_RE.search(script):
        raise ValueError("Could not find define_nominal_beams call to adapt for beam4.")

    return _DEFINE_NOMINAL_BEAMS_RE.sub(beam4_cmd, script, count=1)


def _detect_accelerator_from_model_dir(model_dir: Path) -> str:
    """Infer accelerator family from the nominal MAD-X job file."""
    job_text = _read_nominal_job_text(model_dir)
    if _LHC_USE_SEQUENCE_RE.search(job_text):
        return "lhc"
    if re.search(r"use\s*,\s*sequence\s*=\s*sps\b", job_text, re.IGNORECASE):
        return "sps"
    if _PSB_USE_SEQUENCE_RE.search(job_text):
        return "psb"

    raise ValueError(
        f"Could not infer accelerator type from model directory: {model_dir}. "
        "Expected the nominal MAD-X job file to contain an explicit "
        "`use, sequence=...;` statement for LHC, SPS, or PSB."
    )


def _detect_lhc_beam_from_model_dir(model_dir: Path) -> int:
    """Infer LHC beam number from the nominal MAD-X job file."""
    text = _read_nominal_job_text(model_dir)
    use_matches = {int(match.group(1)) for match in _LHC_USE_SEQUENCE_RE.finditer(text)}
    if len(use_matches) == 1:
        beam = use_matches.pop()
        LOGGER.info(
            "Inferred LHC beam %d from use statement in MAD-X nominal job file.",
            beam,
        )
        return beam

    raise ValueError(
        f"Could not infer LHC beam from model directory: {model_dir}. "
        "Expected exactly one explicit `use, sequence=lhcb1;` or "
        "`use, sequence=lhcb2;` statement in the nominal MAD-X job file."
    )


def _detect_lhc_year_from_model_dir(model_dir: Path) -> str:
    """Infer LHC optics year from the nominal omc3 MAD-X header."""
    match = _LHC_YEAR_RE.search(_read_nominal_job_text(model_dir))
    if match is not None:
        return match.group("year")

    raise ValueError(
        f"Could not infer LHC year from model directory: {model_dir}. "
        "Expected the omc3 nominal header comment '! LHC year ...'."
    )


def _detect_psb_ring_from_model_dir(model_dir: Path) -> int:
    """Infer PSB ring number from the nominal MAD-X job file."""
    text = _read_nominal_job_text(model_dir)
    use_matches = {int(match.group(1)) for match in _PSB_USE_SEQUENCE_RE.finditer(text)}
    if len(use_matches) == 1:
        return use_matches.pop()

    raise ValueError(
        f"Could not infer PSB ring from model directory: {model_dir}. "
        "Expected exactly one explicit `use, sequence=psbN;` statement in the "
        "nominal MAD-X job file."
    )


def _extract_psb_script(job_text: str) -> str:
    """Return the portion of the PSB job file up to and including tune matching."""
    match = _PSB_MATCH_END_RE.search(job_text)
    if match is None:
        raise ValueError("Could not find `ENDMATCH;` in PSB nominal MAD-X job file.")
    return job_text[: match.end()] + "\n"


def _psb_ac_maps_to_markers(seq_path: Path) -> None:
    """Remove PSB AC-map content from the saved sequence.

    The nominal MAD-X job installs thin ``hacmap``/``vacmap`` matrix elements
    for AC-dipole excitation. These are converted to markers in the final sequence,
    since the AC-dipole is installed differently in MAD-NG.
    """
    seq_text = seq_path.read_text()

    for coeff_pat, elm in [
        (r"(?im)^\s*hacmap21\s*=\s*[^;]+;\s*$", "hacmap"),
        (r"(?im)^\s*vacmap43\s*=\s*[^;]+;\s*$", "vacmap"),
    ]:
        # Coefficient assignment, matrix definition, and any placement.
        seq_text = re.sub(coeff_pat, "", seq_text)
        seq_text = re.sub(
            rf"(?im)^\s*{elm}\s*:\s*matrix\s*,\s*l:?=\s*[^;]+;\s*$",
            f"{elm}: marker;",
            seq_text,
        )

    seq_path.write_text(seq_text)


def _inject_post_optics_calls(madx_script: str, madx_files: Sequence[str]) -> str:
    """Insert additional MAD-X files after the optics modifiers section."""
    if not madx_files:
        return madx_script

    extra_calls = "\n! ----- Additional post-optics modifiers -----\n" + "".join(
        f"call, file = '{madx_file}';\n" for madx_file in madx_files
    )

    for marker in _POST_OPTICS_INSERT_MARKERS:
        marker_index = madx_script.find(marker)
        if marker_index != -1:
            return madx_script[:marker_index] + extra_calls + madx_script[marker_index:]

    return madx_script + extra_calls


def _make_psb_sequence(
    model_dir: Path,
    *,
    seq_outdir: Path,
) -> tuple[Path, int]:
    """Generate a matched PSB sequence from an existing nominal MAD-X job file."""
    ring = _detect_psb_ring_from_model_dir(model_dir)
    job_text = _read_nominal_job_text(model_dir)
    # The script takes everything up to the end of the match block.
    madx_script = _extract_psb_script(job_text)
    save_script = (
        "set, format='-16.16e';\n"
        f"save, sequence=psb{ring}, file='saved_madx.seq', noexpr=false;\n"
    )

    with Madx(stdout=False) as madx:
        madx.chdir(str(model_dir))
        madx.input(madx_script)
        madx.chdir(str(seq_outdir))
        madx.input(save_script)

    saved_seq = seq_outdir / "saved_madx.seq"
    if not saved_seq.exists():
        raise FileNotFoundError(
            f"Expected saved sequence file not produced by MAD-X: {saved_seq}"
        )

    seq_path = seq_outdir / f"psb{ring}_saved.seq"
    if saved_seq.resolve() != seq_path.resolve():
        shutil.copy2(saved_seq, seq_path)
        saved_seq.unlink(missing_ok=True)

    _psb_ac_maps_to_markers(seq_path)
    return seq_path, ring


def _load_nominal_creator_from_model_dir(
    model_dir: Path,
) -> tuple[ModelCreator, str, int | None]:
    """Load OMC3 nominal creator from an existing LHC or SPS model directory."""
    accelerator = _detect_accelerator_from_model_dir(model_dir)
    if accelerator == "lhc":
        beam = _detect_lhc_beam_from_model_dir(model_dir)
        year = _detect_lhc_year_from_model_dir(model_dir)
        accel = Lhc(model_dir=model_dir, beam=beam, year=year)
    else:
        beam = None
        accel = Sps(model_dir=model_dir)

    creator_class = get_model_creator_class(accel, CreatorType.NOMINAL)  # ty:ignore[invalid-argument-type]
    creator = creator_class(accel)
    # creator.prepare_run()
    return creator, accelerator, beam


def make_madx_sequence(
    model_dir: Path | str,
    *,
    seq_outdir: Path | None = None,
    beam4: bool = False,
    post_optics_madx_files: Sequence[Path | str] | None = None,
) -> Path:
    """Generate and save a matched MAD-X sequence file from a model folder.

    - Supports LHC, SPS, and PSB model directories
    - Uses the existing PSB nominal job file and stops after tune matching
    - Optionally injects post-optics modifiers for creator-backed accelerators
    - Saves the resulting sequence to ``seq_outdir`` or the model directory
    """

    model_dir = Path(model_dir)
    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    accelerator = _detect_accelerator_from_model_dir(model_dir)
    outdir = Path(seq_outdir) if seq_outdir is not None else model_dir
    outdir.mkdir(parents=True, exist_ok=True)

    if accelerator == "psb":
        if beam4:
            raise ValueError("beam4 sequence adaptation is not supported for PSB.")
        if post_optics_madx_files:
            raise ValueError(
                "Additional post-optics MAD-X files are not supported for PSB sequence export."
            )

        seq_path, ring = _make_psb_sequence(model_dir, seq_outdir=outdir)
        LOGGER.info(
            "Saved MAD-X sequence for accelerator PSB ring %d to %s", ring, seq_path
        )
        return seq_path

    creator, accelerator, beam = _load_nominal_creator_from_model_dir(model_dir)

    madx_script = creator.get_base_madx_script()
    if beam4:
        if accelerator != "lhc" or beam != 2:
            raise ValueError(
                "beam4 sequence adaptation is only supported for LHC beam 2."
            )
        creator_energy = creator.accel.energy
        if creator_energy is None:
            raise ValueError(
                "Could not determine beam energy from model creator accelerator."
            )

        madx_script = _adapt_script_to_beam4(madx_script, beam, float(creator_energy))

    if post_optics_madx_files:
        madx_script = _inject_post_optics_calls(
            madx_script,
            [
                f"{creator.resolve_path_for_madx(Path(madx_file).resolve())}"
                for madx_file in post_optics_madx_files
            ],
        )

    with Madx(stdout=False) as madx:
        madx.chdir(str(model_dir))
        madx.input(madx_script)

        # Always move to outdir, in case you don't have write permissions in the original model_dir
        madx.chdir(str(outdir))
        madx.input(creator.get_save_sequence_script())

    saved_seq = outdir / creator.save_sequence_filename
    if not saved_seq.exists():
        raise FileNotFoundError(
            f"Expected saved sequence file not produced by creator: {saved_seq}"
        )

    desired_seq_name = f"{creator.sequence_name.lower()}_saved.seq"
    seq_path = outdir / desired_seq_name

    if saved_seq.resolve() != seq_path.resolve():
        shutil.copy2(saved_seq, seq_path)
        saved_seq.unlink(missing_ok=True)

    LOGGER.info(
        "Saved MAD-X sequence for accelerator %s%s to %s",
        accelerator.upper(),
        f" beam {beam}" if accelerator == "lhc" else "",
        seq_path,
    )
    return seq_path
