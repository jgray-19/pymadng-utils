"""
Tests for CoreMadInterface.

This module contains pytest tests for the CoreMadInterface class.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import numpy as np
import pytest
from pymadng_utils.mad import AcDipoleMadInterface
from pymadng_utils.mad.core_mad_interface import CoreMadInterface

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


@pytest.fixture(scope="function")
def loaded_ac_interface_with_beam(seq_b1: Path):
    """Fixture that returns an AC-capable interface with sequence loaded and beam set up."""
    interface = AcDipoleMadInterface()
    interface.load_sequence(seq_b1, "lhcb1")
    interface.setup_beam(particle="proton", beam_energy=6800.0)
    yield interface
    # Suppress only expected cleanup-related errors to avoid hiding real bugs.
    with contextlib.suppress(AttributeError, RuntimeError):
        interface.close()


@pytest.mark.parametrize(
    "py_name, expected_py_name, var_name, var_value",
    [
        (None, "py", "a", 2),
        ("test_py", "test_py", "b", 3),
    ],
    ids=["default_py_name", "custom_py_name"],
)
def test_init(py_name, expected_py_name, var_name, var_value) -> None:
    """Test initialization of CoreMadInterface."""
    interface = CoreMadInterface() if py_name is None else CoreMadInterface(py_name=py_name)
    check_interface_basic_init(interface, expected_py_name)
    interface.mad.send(f"{var_name} = {var_value}")
    assert getattr(interface.mad, var_name) == var_value
    cleanup_interface(interface)


def test_load_sequence(interface: CoreMadInterface, seq_b1: Path) -> None:
    """Test loading a sequence file."""
    # this test explicitly checks load_sequence behaviour
    interface.load_sequence(seq_b1, "lhcb1")
    check_sequence_loaded(interface, "lhcb1")
    assert (
        interface.mad.loaded_sequence is not None and interface.mad.loaded_sequence != 0
    )
    assert interface.mad.MADX.lhcb1 is not None and interface.mad.MADX.lhcb1 != 0


@pytest.mark.parametrize("energy", [6500.0, 7000.0])
def test_setup_beam(loaded_interface: CoreMadInterface, energy) -> None:
    """Test setting up beam parameters."""
    interface = loaded_interface
    interface.setup_beam(particle="proton", beam_energy=energy)
    check_beam_setup(interface, particle="proton", energy=energy)


@pytest.mark.parametrize(
    "pattern",
    ["MB.A33R2.B1", "BPM"],
    ids=["SingleElement", "BPMElements"],
)
def test_observe_elements(
    loaded_interface: CoreMadInterface,
    pattern: str,
) -> None:
    """Test configuring element observation."""
    loaded_interface.observe_elements(pattern)
    check_element_observations(loaded_interface, f"elm.name:match('{pattern}')")
    loaded_interface.unobserve_elements([pattern])


def test_cycle_sequence(loaded_interface: CoreMadInterface) -> None:
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
    loaded_interface: CoreMadInterface,
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


def test_getset_variables(interface: CoreMadInterface) -> None:
    """Test setting MAD variables."""
    interface.set_variables(**{"KQTL_1L1_B1": 1.2, "KQTL_1L2_B1": 2.3})
    assert interface.mad.KQTL_1L1_B1 == 1.2
    assert interface.mad.KQTL_1L2_B1 == 2.3

    v1, v2 = interface.get_variables("KQTL_1L1_B1", "KQTL_1L2_B1")
    assert v1 == 1.2
    assert v2 == 2.3


def test_set_madx_variables(interface: CoreMadInterface) -> None:
    """Test setting MAD-X variables."""
    interface.set_madx_variables(**{"kqtl_1l1_b1": 1.5, "KQTL_1L2_B1": 2.5})
    assert interface.mad.MADX.KQTL_1L1_B1 == 1.5
    assert interface.mad.MADX.kqtl_1l2_b1 == 2.5

def test_twiss(loaded_interface_with_beam: CoreMadInterface):
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
    interface.observe_elements("BPM")
    twiss_df = interface.run_twiss()
    # There should only be BPMs observed
    assert len(twiss_df) == 563, f"Expected 563 twiss entries, got {len(twiss_df)}"
    assert all(twiss_df.index.str.match(r"^BPM.*")), (
        "Expected only BPM elements in twiss output"
    )
    assert abs(twiss_df.headers["q1"] - 62.28) < 3e-7, f"Unexpected Qx: {twiss_df.headers['q1']}"
    assert abs(twiss_df.headers["q2"] - 60.31) < 3e-7, f"Unexpected Qy: {twiss_df.headers['q2']}"
    interface.unobserve_elements(["BPM"])


@pytest.mark.parametrize(
    "target_qx,target_qy,qx_knob,qy_knob",
    [
        (0.2801, 0.3101, None, None),
        (0.29, 0.32, "dqx_b1", "dqy_b1"),
        (0.27, 0.30, None, None),
    ],
)
def test_match_tunes(
    loaded_interface_with_beam: CoreMadInterface,
    target_qx: float,
    target_qy: float,
    qx_knob: str,
    qy_knob: str,
):
    """Test matching tunes."""
    interface = loaded_interface_with_beam
    default_qx = qx_knob or "dqx_b1_op"
    default_qy = qy_knob or "dqy_b1_op"
    knobs = {
        default_qx: interface.mad.MADX[default_qx],
        default_qy: interface.mad.MADX[default_qy],
    }
    print("Initial knobs:", knobs)

    kwargs = {}
    if qx_knob:
        kwargs["qx_knob"] = qx_knob
    if qy_knob:
        kwargs["qy_knob"] = qy_knob

    new_knobs = interface.match_tunes(
        target_qx=target_qx, target_qy=target_qy, **kwargs
    )

    twiss_df = interface.run_twiss()
    assert abs((twiss_df.headers["q1"] % 1) - target_qx) < 1e-5, (
        f"Qx not matched: {twiss_df.headers['q1'] % 1} != {target_qx}"
    )
    assert abs((twiss_df.headers["q2"] % 1) - target_qy) < 1e-5, (
        f"Qy not matched: {twiss_df.headers['q2'] % 1} != {target_qy}"
    )

    # Check that knobs have been changed
    for knob, old_value in knobs.items():
        new_value = interface.mad.MADX[knob]
        assert new_value != old_value, f"Knob {knob} value did not change"
        assert new_value == new_knobs[knob], (
            f"Returned knob value for {knob} does not match MAD value"
        )



def test_install_ac_dipole_and_twiss(loaded_ac_interface_with_beam) -> None:
    """Test AC dipole installation and verify that tunes change to driven values."""
    interface = loaded_ac_interface_with_beam

    # Run initial twiss to get natural tunes
    tws = interface.run_twiss(observe=0)
    nat_qx = tws.headers["q1"] % 1
    nat_qy = tws.headers["q2"] % 1

    # Define AC dipole parameters
    ac_marker = "MKQA.6L4.B1"
    nat_tunes = (nat_qx, nat_qy)
    drv_tunes = (0.27, 0.322)
    # Use small positive offset to avoid overlapping with marker element
    ac_offset = 1.583 / 2  # Standard AC dipole offset

    # Install AC dipole
    interface.install_ac_dipole(
        marker_name=ac_marker, nat_tunes=nat_tunes, drv_tunes=drv_tunes, offset=ac_offset
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
