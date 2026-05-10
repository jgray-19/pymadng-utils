from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from omc3.model.constants import JOB_MODEL_MADX_NOMINAL

from pymadng_utils.madx.make_sequence import (
    _detect_accelerator_from_model_dir,
    _detect_lhc_beam_from_model_dir,
    _detect_psb_ring_from_model_dir,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write_nominal_job(model_dir: Path, text: str) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / JOB_MODEL_MADX_NOMINAL).write_text(text)


def test_detect_accelerator_requires_explicit_use_statement(tmp_path: Path) -> None:
    model_dir = tmp_path / "lhc_model_b1"
    _write_nominal_job(
        model_dir,
        "! LHC year 2025\ncall, file='acc-models-lhc/lhc.seq';\n",
    )

    with pytest.raises(ValueError, match="explicit `use, sequence="):
        _detect_accelerator_from_model_dir(model_dir)


def test_detect_lhc_beam_no_longer_guesses_from_directory_name(
    tmp_path: Path,
) -> None:
    model_dir = tmp_path / "model_b2"
    _write_nominal_job(
        model_dir,
        "! LHC year 2025\ncall, file='acc-models-lhc/lhc.seq';\n"
        "use, sequence=lhcb1;\nuse, sequence=lhcb2;\n",
    )

    with pytest.raises(ValueError, match="Expected exactly one explicit `use, sequence=lhcb1;` or `use, sequence=lhcb2;` statement"):
        _detect_lhc_beam_from_model_dir(model_dir)


def test_detect_psb_ring_no_longer_guesses_from_directory_name(
    tmp_path: Path,
) -> None:
    model_dir = tmp_path / "psb3_model"
    _write_nominal_job(
        model_dir,
        "call, file='psb.seq';\nuse, sequence=psb1;\nuse, sequence=psb3;\nENDMATCH;\n",
    )

    with pytest.raises(ValueError, match="Expected exactly one explicit `use, sequence=psbN;` statement"):
        _detect_psb_ring_from_model_dir(model_dir)
