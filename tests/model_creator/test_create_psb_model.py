from __future__ import annotations

import contextlib
from pathlib import Path

import pytest
import tfs
from omc3.model_creator import create_instance_and_model

from pymadng_utils.accelerators import PSB
from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface
from pymadng_utils.madx.make_sequence import make_madx_sequence
from pymadng_utils.model_creator.madng_utils import update_model_with_madng

PSB_NAT_TUNES = (0.17, 0.225)
PSB_DRV_TUNES = (0.162, 0.232)


def _create_psb_nominal_model(
    output_dir: Path,
    acc_models_dir: Path,
    *,
    drv_tunes: tuple[float, float] | None = None,
) -> None:
    kwargs = {
        "outputdir": output_dir,
        "accel": "psbooster",
        "type": "nominal",
        "nat_tunes": list(PSB_NAT_TUNES),
        "dpp": 0.0,
        "fetch": "path",
        "path": acc_models_dir,
        "scenario": "lhc_indiv",
        "year": "2026",
        "cycle_point": "1_flat_bottom",
        "str_file": "psb_fb_lhcindiv.str",
        "ring": 3,
        "list_choices": False,
        "show_help": False,
        "logfile": None,
    }
    if drv_tunes is not None:
        kwargs["drv_tunes"] = list(drv_tunes)
        kwargs["driven_excitation"] = "acd"

    create_instance_and_model(
        **kwargs,
    )


@pytest.fixture(scope="module")
def psb_model_dir(
    tmp_path_factory: pytest.TempPathFactory, acc_models_psb_path: Path
) -> Path:
    """Create a full PSB model from the committed minimal PSB acc-models snapshot."""
    model_dir = tmp_path_factory.mktemp("psb_model") / "ring3_model"
    _create_psb_nominal_model(model_dir, acc_models_psb_path)

    sequence_file = make_madx_sequence(model_dir)
    update_model_with_madng(
        accelerator=PSB(sequence_file=sequence_file, ring=3),
        model_dir=model_dir,
        tunes=list(PSB_NAT_TUNES),
        drv_tunes=None,
    )
    return model_dir


@pytest.fixture(scope="module")
def psb_model_dir_with_acd(
    tmp_path_factory: pytest.TempPathFactory, acc_models_psb_path: Path
) -> Path:
    """Create a PSB model with explicit driven tunes and ACD excitation."""
    model_dir = tmp_path_factory.mktemp("psb_model_acd") / "ring3_model"
    _create_psb_nominal_model(
        model_dir,
        acc_models_psb_path,
        drv_tunes=PSB_DRV_TUNES,
    )

    sequence_file = make_madx_sequence(model_dir)
    update_model_with_madng(
        accelerator=PSB(sequence_file=sequence_file, ring=3),
        model_dir=model_dir,
        tunes=list(PSB_NAT_TUNES),
        drv_tunes=list(PSB_DRV_TUNES),
    )
    return model_dir


def test_create_psb_model_via_omc3_api(psb_model_dir: Path) -> None:
    """PSB model creation should work without shelling out to the omc3 CLI."""
    expected_files = [
        "job.create_model_nominal.madx",
        "psb3_saved.seq",
        "twiss.dat",
        "twiss_ac.dat",
        "twiss_elements.dat",
    ]
    for file_name in expected_files:
        assert (psb_model_dir / file_name).exists(), f"Missing {file_name}"

    sequence_text = (psb_model_dir / "psb3_saved.seq").read_text()
    # If there is no ACD excitation, we should not have any ACD markers in the sequence
    assert "hacmap: hackicker" not in sequence_text
    assert "vacmap: vackicker" not in sequence_text
    assert "matrix" not in sequence_text

    twiss = tfs.read(psb_model_dir / "twiss.dat", index="NAME")
    twiss_ac = tfs.read(psb_model_dir / "twiss_ac.dat", index="NAME")
    twiss_elements = tfs.read(psb_model_dir / "twiss_elements.dat", index="NAME")

    assert twiss.headers["NAME"] == "PSB3"
    assert abs(twiss.headers["Q1"] % 1 - PSB_NAT_TUNES[0]) < 1e-6
    assert abs(twiss.headers["Q2"] % 1 - PSB_NAT_TUNES[1]) < 1e-6
    assert abs(twiss_ac.headers["Q1"] % 1 - PSB_NAT_TUNES[0]) < 1e-6
    assert abs(twiss_ac.headers["Q2"] % 1 - PSB_NAT_TUNES[1]) < 1e-6
    assert "BR3.BPM3L3" in twiss.index
    assert "HACMAP" not in twiss_elements.index
    assert "VACMAP" not in twiss_elements.index


def test_create_psb_model_with_explicit_acd(
    psb_model_dir_with_acd: Path,
) -> None:
    """Explicit driven tunes plus ACD excitation should produce a driven PSB model."""
    accelerator = PSB(sequence_file=psb_model_dir_with_acd / "psb3_saved.seq", ring=3)
    install_marker, install_offset = accelerator.ac_dipole_location

    twiss = tfs.read(psb_model_dir_with_acd / "twiss.dat", index="NAME")
    twiss_ac = tfs.read(psb_model_dir_with_acd / "twiss_ac.dat", index="NAME")
    twiss_elements = tfs.read(
        psb_model_dir_with_acd / "twiss_elements.dat", index="NAME"
    )

    assert abs(twiss.headers["Q1"] % 1 - PSB_NAT_TUNES[0]) < 1e-6
    assert abs(twiss.headers["Q2"] % 1 - PSB_NAT_TUNES[1]) < 1e-6
    assert abs(twiss_ac.headers["Q1"] % 1 - PSB_DRV_TUNES[0]) < 1e-6
    assert abs(twiss_ac.headers["Q2"] % 1 - PSB_DRV_TUNES[1]) < 1e-6
    assert install_marker in twiss_elements.index
    assert install_offset == 0.565 / 2
    assert abs(twiss_elements.loc["HACMAP", "S"] - twiss_elements.loc["VACMAP", "S"]) < 1e-9
    assert abs(twiss_elements.loc["HACMAP", "S"] - twiss_elements.loc[install_marker, "S"]) < 1e-9

    # Check that we have rewritten the madx sequence with MAD-NG compatible ACDs and tunes
    sequence_text = (psb_model_dir_with_acd / "psb3_saved.seq").read_text()
    assert f"nat_q:={4 + PSB_NAT_TUNES[0]:.16e}" in sequence_text
    assert f"nat_q:={4 + PSB_NAT_TUNES[1]:.16e}" in sequence_text
    assert f"drv_q:={4 + PSB_DRV_TUNES[0]:.16e}" in sequence_text
    assert f"drv_q:={4 + PSB_DRV_TUNES[1]:.16e}" in sequence_text


def test_psb_saved_sequence_loads_in_madng(psb_model_dir: Path) -> None:
    """The generated PSB saved sequence should support a real MAD-NG twiss run."""
    interface = AcceleratorMadInterface(
        accelerator=PSB(sequence_file=psb_model_dir / "psb3_saved.seq", ring=3)
    )
    try:
        interface.observe()
        twiss = interface.run_twiss(coupling=True)
    finally:
        with contextlib.suppress(Exception):
            interface.close()

    assert abs(twiss.q1 % 1 - PSB_NAT_TUNES[0]) < 1e-6
    assert abs(twiss.q2 % 1 - PSB_NAT_TUNES[1]) < 1e-6
    assert "BR3.BPM3L3" in twiss.index
    assert "BR3.BPM4L3" in twiss.index
