from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import pytest

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad.model_creator_mad_interface import ModelCreatorMadInterface

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def model_file(seq_b1: Path, tmp_path: Path) -> Path:
    """Provide a writable saved-sequence file for model-creator tests."""
    target = tmp_path / "lhcb1_saved.seq"
    target.write_text(seq_b1.read_text())
    return target


@pytest.fixture
def model_interface(model_file: Path, tmp_path: Path):
    """Create a real model-creator interface using the test sequence."""
    accel = LHC(beam=1, kinetic_energy=6800.0, sequence_file=model_file)
    interface = ModelCreatorMadInterface(
        model_dir=tmp_path,
        accelerator=accel,
        tunes=[0.28, 0.31],
    )
    yield interface
    with contextlib.suppress(Exception):
        interface.close()


def test_model_creator_init_requires_existing_sequence(tmp_path: Path) -> None:
    """The interface should fail fast when the saved sequence file is missing."""
    missing_file = tmp_path / "missing.seq"


    with pytest.raises(FileNotFoundError, match="Sequence file not found"):
        ModelCreatorMadInterface(
            model_dir=tmp_path,
            accelerator=LHC(beam=1, kinetic_energy=6800.0, sequence_file=missing_file),
            tunes=[0.28, 0.31],
        )


def test_model_creator_init_loads_sequence_and_beam(
    model_interface: ModelCreatorMadInterface, model_file: Path, tmp_path: Path
) -> None:
    """Initialization should load the sequence, set the beam, and keep config values."""
    assert model_interface.model_dir == tmp_path
    assert model_interface.accelerator.sequence_file == model_file
    assert model_interface.accelerator.kinetic_energy == 6800.0
    assert model_interface.tunes == [0.28, 0.31]
    assert model_interface.accelerator.tune_variables == ("dqx_b1_op", "dqy_b1_op")
    assert model_interface.mad.SEQ_NAME == "lhcb1"
    assert model_interface.mad.loaded_sequence is not None
    assert model_interface.mad.loaded_sequence.beam.particle == "proton"
    assert model_interface.mad.loaded_sequence.beam.energy == pytest.approx(6800.0 + 0.9382720813)


def test_model_creator_repr_and_str_use_default_interface_behaviour(
    model_interface: ModelCreatorMadInterface,
) -> None:
    assert (
        repr(model_interface)
        == "ModelCreatorMadInterface(seq_name='lhcb1', py_name='py')"
    )
    assert str(model_interface) == "ModelCreatorMadInterface(lhcb1)"


def test_get_current_tunes_reads_real_twiss(
    model_interface: ModelCreatorMadInterface,
) -> None:
    """The tune reader should return the actual natural tunes from MAD."""
    q1, q2 = model_interface.get_current_tunes()

    assert isinstance(q1, float)
    assert isinstance(q2, float)
    assert abs(q1 % 1 - 0.28) < 1e-6
    assert abs(q2 % 1 - 0.31) < 1e-6


def test_compute_and_export_twiss_tables_writes_outputs(
    model_interface: ModelCreatorMadInterface, tmp_path: Path
) -> None:
    """The real export path should write both natural twiss tables."""
    model_interface.compute_and_export_twiss_tables()

    twiss_file = tmp_path / "twiss.dat"
    elements_file = tmp_path / "twiss_elements.dat"
    assert twiss_file.exists()
    assert elements_file.exists()
    assert twiss_file.stat().st_size > 0
    assert elements_file.stat().st_size > 0
