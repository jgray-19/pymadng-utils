"""
Tests for KnobMadInterface.

This module contains pytest tests for the KnobMadInterface class.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import pytest

from pymadng_utils.mad.knob_mad_interface import KnobMadInterface

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="function")
def knob_interface_with_beam(seq_b1: Path):
    """Fixture that returns a KnobMadInterface with sequence loaded and beam set up."""
    interface = KnobMadInterface()
    interface.load_sequence(seq_b1, "lhcb1")
    interface.setup_beam(particle="proton", beam_energy=6800.0)
    yield interface
    # Suppress only expected cleanup-related errors to avoid hiding real bugs.
    with contextlib.suppress(AttributeError, RuntimeError):
        interface.close()


def test_set_magnet_strength(knob_interface_with_beam: KnobMadInterface) -> None:
    """Test setting magnet strengths."""
    magnet_strengths = {
        "MB.A8R2.B1.k0": 3.566169870533780e-04,
        "MB.B8R2.B1.k0": 3.566320017035819e-04,
        "MQ.11R2.B1.k1": -8.555311397913858e-03,
        "MS.11R2.B1.k2": -1.366585087094679e-01,
    }
    strengths_before = {}
    for mag_name, new_strength in magnet_strengths.items():
        mag_base, strength_num = mag_name.rsplit(".", 1)
        strengths_before[mag_base] = knob_interface_with_beam.mad[
            f"MADX['{mag_base}'].{strength_num}"
        ]

    knob_interface_with_beam.set_magnet_strengths(magnet_strengths)
    for mag_name, new_strength in magnet_strengths.items():
        mag_base, strength_num = mag_name.rsplit(".", 1)
        updated_strength = knob_interface_with_beam.mad[f"MADX['{mag_base}'].{strength_num}"]

        assert updated_strength != strengths_before[mag_base], (
            f"Magnet {mag_name} strength did not change from previous value."
        )
        assert updated_strength == new_strength, (
            f"Magnet {mag_name} strength not updated correctly: "
            f"{updated_strength} != {new_strength}"
        )


def test_set_magnet_strengths_error(knob_interface_with_beam: KnobMadInterface) -> None:
    """Test setting magnet strengths with incorrect naming raises error."""
    with pytest.raises(ValueError):
        knob_interface_with_beam.set_magnet_strengths(
            {
                "MOB.A8R2.B1.k4": 3.566169870533780e-04,  # Invalid magnet type
            }
        )

    magnet_strengths_invalid_suffix = {
        "MB.A8R2.B1.k": 3.566169870533780e-04,  # Invalid suffix
    }
    with pytest.raises(ValueError):
        knob_interface_with_beam.set_magnet_strengths(magnet_strengths_invalid_suffix)

    with pytest.raises(ValueError):
        knob_interface_with_beam.set_magnet_strengths(
            {
                "MB.A8R2.B1_k0": 3.566169870533780e-04,  # Invalid format
            }
        )


def test_observe_bpms(knob_interface_with_beam: KnobMadInterface) -> None:
    """Test observing BPMs and bad BPMs."""
    # Reset observations first
    knob_interface_with_beam.observe_elements("NONE")

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
    knob_interface_with_beam.observe_elements("NONE")
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
