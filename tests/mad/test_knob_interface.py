"""
Tests for KnobMadInterface.

This module contains pytest tests for the KnobMadInterface class.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad.knob_mad_interface import KnobMadInterface

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="function")
def knob_interface_with_beam(seq_b1: Path):
    """Fixture that returns a KnobMadInterface with sequence loaded and beam set up."""
    interface = KnobMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0)
    )
    yield interface
    # Suppress only expected cleanup-related errors to avoid hiding real bugs.
    with contextlib.suppress(AttributeError, RuntimeError):
        interface.close()


def test_observe_bpms(knob_interface_with_beam: KnobMadInterface) -> None:
    """Test observing BPMs and bad BPMs."""
    # Test observe_bpms with just pattern
    knob_interface_with_beam.observe_bpms("BPM")
    knob_interface_with_beam.mad.send("""
local count = 0
for _, elm in loaded_sequence:iter() do
    if elm:is_observed() then
        count = count + 1
    end
end
py:send(count)
""")
    bpm_count = knob_interface_with_beam.mad.recv()
    assert bpm_count > 0, "No BPMs were observed"

    # Test observe_bpms with bad BPMs
    knob_interface_with_beam.unobserve_elements(["BPM"])
    knob_interface_with_beam.observe_bpms("BPM", bad_bpms=["BPM.1L1.B1"])
    # Should still have observed BPMs (minus the bad ones if they existed)
    knob_interface_with_beam.mad.send("""
local count = 0
for _, elm in loaded_sequence:iter() do
    if elm:is_observed() and elm.name ~= "BPM.1L1.B1" then
        count = count + 1
    end
end
py:send(count)
""")
    bpm_count_with_filter = knob_interface_with_beam.mad.recv()
    assert bpm_count_with_filter > 0, "No BPMs were observed after filtering"


def test_apply_corrector_strengths_updates_kickers(
    knob_interface_with_beam: KnobMadInterface,
) -> None:
    """Applying corrector strengths should update real sequence kicker fields."""
    correctors = pd.DataFrame(
        [
            {"ename": "MCBYH.B5L2.B1", "hkick": 1.25e-6},
            {"ename": "MCBYV.5L2.B1", "vkick": -2.5e-6},
            {"ename": "MKI.D5L2.B1", "hkick": 3.5e-6, "vkick": -4.5e-6},
        ]
    )

    knob_interface_with_beam.apply_corrector_strengths(correctors)

    assert knob_interface_with_beam.mad.loaded_sequence[
        "MCBYH.B5L2.B1"
    ].kick == pytest.approx(1.25e-6)
    assert knob_interface_with_beam.mad.loaded_sequence[
        "MCBYV.5L2.B1"
    ].kick == pytest.approx(-2.5e-6)
    assert knob_interface_with_beam.mad.loaded_sequence[
        "MKI.D5L2.B1"
    ].hkick == pytest.approx(3.5e-6)
    assert knob_interface_with_beam.mad.loaded_sequence[
        "MKI.D5L2.B1"
    ].vkick == pytest.approx(-4.5e-6)


def test_apply_corrector_strengths_ignores_missing_elements(
    knob_interface_with_beam: KnobMadInterface,
) -> None:
    """Missing corrector names should be ignored without disturbing valid rows."""
    correctors = pd.DataFrame(
        [
            {"ename": "DOES.NOT.EXIST", "hkick": 9.9e-6},
            {"ename": "MCBYH.B5L2.B1", "hkick": 7.5e-7},
        ]
    )

    knob_interface_with_beam.apply_corrector_strengths(correctors)

    assert knob_interface_with_beam.mad.loaded_sequence[
        "MCBYH.B5L2.B1"
    ].kick == pytest.approx(7.5e-7)


def test_set_corrector_strengths_from_knob_file(
    knob_interface_with_beam: KnobMadInterface, tmp_path: Path
) -> None:
    """A non-TFS knob file should fall back to read_knobs and set MADX values."""
    knob_file = tmp_path / "corrector_knobs.txt"
    knob_file.write_text("dqx_b1_op\t1.250000e-03\ndqy_b1_op\t-2.500000e-03\n")

    knob_interface_with_beam.set_corrector_strengths(knob_file)

    assert knob_interface_with_beam.mad.MADX.dqx_b1_op == pytest.approx(1.25e-3)
    assert knob_interface_with_beam.mad.MADX.dqy_b1_op == pytest.approx(-2.5e-3)


def test_set_corrector_strengths_missing_file_is_noop(
    knob_interface_with_beam: KnobMadInterface, tmp_path: Path
) -> None:
    """A missing corrector-strength file should leave existing values unchanged."""
    before_qx = knob_interface_with_beam.mad.MADX.dqx_b1_op
    before_qy = knob_interface_with_beam.mad.MADX.dqy_b1_op

    knob_interface_with_beam.set_corrector_strengths(
        tmp_path / "missing_correctors.tfs"
    )

    assert knob_interface_with_beam.mad.MADX.dqx_b1_op == before_qx
    assert knob_interface_with_beam.mad.MADX.dqy_b1_op == before_qy


def test_set_knobs_reads_knob_file(
    knob_interface_with_beam: KnobMadInterface, tmp_path: Path
) -> None:
    """Knob files should be read and applied in the MADX environment."""
    knob_file = tmp_path / "tune_knobs.txt"
    knob_file.write_text("dqx_b1_op\t4.000000e-04\ndqy_b1_op\t-6.000000e-04\n")

    knob_interface_with_beam.set_knobs(knob_file)

    assert knob_interface_with_beam.mad.MADX.dqx_b1_op == pytest.approx(4.0e-4)
    assert knob_interface_with_beam.mad.MADX.dqy_b1_op == pytest.approx(-6.0e-4)
