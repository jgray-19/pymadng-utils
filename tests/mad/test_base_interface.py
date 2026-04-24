"""
Tests for AcceleratorMadInterface.

This module contains pytest tests for the AcceleratorMadInterface class.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad import AcDipoleMadInterface
from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface
from tests.mad.helpers import (
    check_beam_setup,
    check_element_observations,
    check_interface_basic_init,
    check_sequence_loaded,
    cleanup_interface,
    get_marker_and_element_positions,
)

if TYPE_CHECKING:
    from pathlib import Path


class MissingSequenceLHC(LHC):
    @property
    def seq_name(self) -> str:
        return "does_not_exist"


@pytest.fixture(scope="function")
def loaded_ac_interface_with_beam(seq_b1: Path):
    """Fixture that returns an AC-capable interface with sequence loaded and beam set up."""
    interface = AcDipoleMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, pc=6800.0)
    )
    yield interface
    interface.close()


def test_init(seq_b1: Path) -> None:
    """Test initialization of AcceleratorMadInterface."""
    interface = AcceleratorMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, pc=6800.0)
    )
    check_interface_basic_init(interface, "py")
    interface.mad.send("a = 2")
    assert interface.mad.a == 2
    cleanup_interface(interface)


def test_load_sequence(interface: AcceleratorMadInterface) -> None:
    """Test loading a sequence file during initialisation."""
    check_sequence_loaded(interface, "lhcb1")
    assert (
        interface.mad.loaded_sequence is not None and interface.mad.loaded_sequence != 0
    )
    assert interface.mad.MADX.lhcb1 is not None and interface.mad.MADX.lhcb1 != 0


def test_load_sequence_unknown_sequence_raises(seq_b1: Path) -> None:
    """Loading a valid file with a missing sequence name should fail clearly."""
    with pytest.raises(
        ValueError,
        match=r"Sequence 'does_not_exist' not found in MAD file",
    ):
        AcceleratorMadInterface(
            accelerator=MissingSequenceLHC(beam=1, sequence_file=seq_b1, pc=6800.0)
        )


def test_load_sequence_bad_file_raises(tmp_path: Path) -> None:
    """Loading an invalid sequence file should fail through the missing-sequence check."""
    bad_sequence = tmp_path / "bad.seq"
    bad_sequence.write_text("this is not a MAD-X sequence\n")

    with pytest.raises(
        ValueError,
        match=r"Sequence 'lhcb1' not found in MAD file",
    ):
        AcceleratorMadInterface(
            accelerator=LHC(beam=1, sequence_file=bad_sequence, pc=6800.0)
        )


def test_setup_beam(loaded_interface: AcceleratorMadInterface) -> None:
    """Test beam parameters from the accelerator descriptor are applied."""
    check_beam_setup(loaded_interface, particle="proton", pc=6800.0)


@pytest.mark.parametrize(
    "pattern",
    ["MB.A33R2.B1", "BPM"],
    ids=["SingleElement", "BPMElements"],
)
def test_observe_elements(
    loaded_interface: AcceleratorMadInterface,
    pattern: str,
) -> None:
    """Test configuring element observation."""
    loaded_interface.observe(pattern)
    check_element_observations(loaded_interface, f"elm.name:match('{pattern}')")
    loaded_interface.unobserve_elements([pattern])


def test_cycle_sequence(loaded_interface: AcceleratorMadInterface) -> None:
    """Test cycling sequence to a marker."""
    loaded_interface.mad.send("""py:send(loaded_sequence:raw_get("__cycle"))""")
    assert loaded_interface.mad.recv() is None

    loaded_interface.cycle_sequence("IP5")
    loaded_interface.mad.send("""py:send(loaded_sequence:raw_get("__cycle"))""")
    cycle_marker = loaded_interface.mad.recv()
    assert cycle_marker == "IP5"

    loaded_interface.cycle_sequence()
    loaded_interface.mad.send("""py:send(loaded_sequence:raw_get("__cycle"))""")
    cycle_marker = loaded_interface.mad.recv()
    assert cycle_marker is None


def test_cycle_sequence_invalid_marker_raises(
    loaded_interface: AcceleratorMadInterface,
) -> None:
    """Cycling to a missing marker should raise the wrapped runtime error."""
    with pytest.raises(
        RuntimeError, match="Cycle failed - check MAD output for details"
    ):
        loaded_interface.cycle_sequence("NOT_A_MARKER")


@pytest.mark.parametrize(
    "element, marker_name, offset, expected_marker_name, index_check, pos_check",
    [
        (
            "S.DS.L1.B1",
            None,
            None,
            "S.DS.L1.B1_marker",
            lambda m, e: m + 1 == e,
            lambda m, e: m == e - 1e-10,
        ),
        (
            "S.DS.L1.B1",
            "MyMarker",
            5e-6,
            "MyMarker",
            lambda m, e: m - 1 == e,
            lambda m, e: m == e + 5e-6,
        ),
    ],
    ids=["default_marker", "custom_marker"],
)
def test_install_marker(
    loaded_interface: AcceleratorMadInterface,
    element,
    marker_name,
    offset,
    expected_marker_name,
    index_check,
    pos_check,
) -> None:
    """Test installing a marker element."""
    interface = loaded_interface
    if marker_name and offset is not None:
        ret_name = interface.install_marker(
            element, marker_name=marker_name, offset=offset
        )
    else:
        ret_name = interface.install_marker(element)
    marker_position, marker_index, elem_position, elem_index = (
        get_marker_and_element_positions(interface, expected_marker_name, element)
    )
    assert index_check(marker_index, elem_index)
    assert pos_check(marker_position, elem_position)
    assert ret_name == expected_marker_name


def test_install_marker_missing_element_raises(
    loaded_interface: AcceleratorMadInterface,
) -> None:
    """Installing a marker near a missing element should raise a clear error."""
    with pytest.raises(
        ValueError,
        match=r"Element 'NOT_AN_ELEMENT' not found in loaded sequence",
    ):
        loaded_interface.install_marker("NOT_AN_ELEMENT")


def test_replace_with_marker_missing_element_raises(
    loaded_interface: AcceleratorMadInterface,
) -> None:
    """Replacing a missing element should raise a clear error."""
    with pytest.raises(ValueError, match=r"Could not find element: NOT_AN_ELEMENT"):
        loaded_interface.replace_with_marker("NOT_AN_ELEMENT")


def test_getset_variables(interface: AcceleratorMadInterface) -> None:
    """Test setting MAD variables."""
    interface.set_variables(**{"KQTL_1L1_B1": 1.2, "KQTL_1L2_B1": 2.3})
    assert interface.mad.KQTL_1L1_B1 == 1.2
    assert interface.mad.KQTL_1L2_B1 == 2.3

    v1, v2 = interface.get_variables("KQTL_1L1_B1", "KQTL_1L2_B1")
    assert v1 == 1.2
    assert v2 == 2.3


def test_set_madx_variables(interface: AcceleratorMadInterface) -> None:
    """Test setting MAD-X variables."""
    interface.set_madx_variables(**{"kqtl_1l1_b1": 1.5, "KQTL_1L2_B1": 2.5})
    assert interface.mad.MADX.KQTL_1L1_B1 == 1.5
    assert interface.mad.MADX.kqtl_1l2_b1 == 2.5

def test_twiss(loaded_interface_with_beam: AcceleratorMadInterface):
    """Test twiss function."""
    interface = loaded_interface_with_beam
    twiss_df = interface.run_twiss()

    # Assert the columns we expect are present
    expected_columns = [
        "s",
        "beta11",
        "beta22",
        "alfa11",
        "alfa22",
        "mu1",
        "mu2",
        "dx",
        "dy",
    ]
    for col in expected_columns:
        assert col in twiss_df.columns, (
            f"Expected column {col} not found in twiss output"
        )
    assert "name" not in twiss_df.columns, "Column 'name' should be the index"
    assert twiss_df.index.name == "name", (
        f"Expected index name to be 'name', got {twiss_df.index.name}"
    )

    # There should only be one entry, since by default observe = 1 and nothing has been set to be observed
    assert len(twiss_df) == 1, f"Expected 1 twiss entry, got {len(twiss_df)}"
    # Check the marker is named $end
    assert twiss_df.index[0] == "$end", (
        f"Expected marker name '$end', got {twiss_df.index[0]}"
    )

    # Check the tunes
    assert abs(twiss_df.headers["q1"] - 62.28) < 3e-7, f"Unexpected Qx: {twiss_df.q1}"
    assert abs(twiss_df.headers["q2"] - 60.31) < 3e-7, f"Unexpected Qy: {twiss_df.q2}"

    # Now set observe to 0
    twiss_df = interface.run_twiss(observe=0)
    # There should be loads of entries now, including drifts
    assert len(twiss_df) > 1000, f"Expected >1000 twiss entries, got {len(twiss_df)}"
    assert "drift__3" in twiss_df.index, (
        "Expected to find drift elements in twiss output"
    )
    assert "MB.A33R2.B1" in twiss_df.index, (
        "Expected to find magnet elements in twiss output"
    )
    assert abs(twiss_df.headers["q1"] - 62.28) < 3e-7, f"Unexpected Qx: {twiss_df.headers['q1']}"
    assert abs(twiss_df.headers["q2"] - 60.31) < 3e-7, f"Unexpected Qy: {twiss_df.headers['q2']}"

    # Now observe BPMs
    interface.observe("BPM")
    twiss_df = interface.run_twiss()
    # There should only be BPMs observed
    assert len(twiss_df) == 563, f"Expected 563 twiss entries, got {len(twiss_df)}"
    assert all(twiss_df.index.str.match(r"^BPM.*")), (
        "Expected only BPM elements in twiss output"
    )
    assert abs(twiss_df.headers["q1"] - 62.28) < 3e-7, f"Unexpected Qx: {twiss_df.headers['q1']}"
    assert abs(twiss_df.headers["q2"] - 60.31) < 3e-7, f"Unexpected Qy: {twiss_df.headers['q2']}"
    interface.unobserve_elements(["BPM"])

def test_install_ac_dipole_and_twiss(loaded_ac_interface_with_beam) -> None:
    """Test AC dipole installation and verify that tunes change to driven values."""
    interface = loaded_ac_interface_with_beam

    # Run initial twiss to get natural tunes
    tws = interface.run_twiss(observe=0)
    nat_qx = tws.headers["q1"] % 1
    nat_qy = tws.headers["q2"] % 1

    # Define AC dipole parameters
    nat_tunes = (nat_qx, nat_qy)
    drv_tunes = (0.27, 0.322)

    # Install AC dipole
    interface.install_ac_dipole(
        nat_tunes=nat_tunes, drv_tunes=drv_tunes
    )

    # Run twiss after AC dipole installation
    tws_ac = interface.run_twiss(observe=0)
    drv_qx = tws_ac.headers["q1"] % 1
    drv_qy = tws_ac.headers["q2"] % 1

    # Verify that tunes have changed to driven values
    tolerance = 1e-4
    assert np.isclose(drv_qx, drv_tunes[0], atol=tolerance), (
        f"Q1 not driven correctly: expected {drv_tunes[0]:.6f}, got {drv_qx:.6f}"
    )
    assert np.isclose(drv_qy, drv_tunes[1], atol=tolerance), (
        f"Q2 not driven correctly: expected {drv_tunes[1]:.6f}, got {drv_qy:.6f}"
    )
