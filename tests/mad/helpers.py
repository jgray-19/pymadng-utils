"""
Common helper functions for MAD interface tests.

This module contains utility functions used across MAD interface test modules.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface


def _recv_n(mad: Any, n: int) -> list[Any]:
    """Helper to receive n messages from a MAD instance."""
    results = []
    for _ in range(n):
        results.append(mad.recv())
    return results


def check_interface_basic_init(interface: Any, py_name: str = "py") -> None:
    """Check basic interface initialization properties."""
    assert interface.py_name == py_name
    assert hasattr(interface, "mad")


def cleanup_interface(interface: Any) -> None:
    """Clean up interface instance."""
    with contextlib.suppress(Exception):
        del interface


def check_sequence_loaded(
    interface: AcceleratorMadInterface, seq_name: str = "lhcb1"
) -> None:
    """Check that sequence is loaded correctly."""
    assert seq_name == interface.mad.SEQ_NAME
    assert interface.mad.loaded_sequence is not None


def check_beam_setup(
    interface: AcceleratorMadInterface,
    particle: str = "proton",
    kinetic_energy: float | None = None,
    charge: int = 1,
    spin: float = 0.5,
) -> None:
    """Check beam setup properties."""
    assert particle == interface.mad.loaded_sequence.beam.particle
    if kinetic_energy is not None:
        print(
            f"Checking beam energy: expected kinetic={kinetic_energy} GeV, "
            f"got total={interface.mad.loaded_sequence.beam.energy} GeV, "
            f"mass={interface.mad.loaded_sequence.beam.mass} GeV"
            f"resulting kinetic={interface.mad.loaded_sequence.beam.energy - interface.mad.loaded_sequence.beam.mass} GeV"
        )
        assert np.isclose(
            kinetic_energy,
            interface.mad.loaded_sequence.beam.energy
            - interface.mad.loaded_sequence.beam.mass,
            rtol=1e-10,
        )
    assert charge == interface.mad.loaded_sequence.beam.charge
    assert spin == interface.mad.loaded_sequence.beam.spin


def check_element_observations(
    interface: AcceleratorMadInterface,
    condition: str,
) -> None:
    """Helper to check element observations in MAD."""
    interface.mad.send(f"""
for _, elm in loaded_sequence:iter() do
    if {condition} then
        assert(
            elm:is_observed(),
            "Found expected observation missing for element " .. elm.name
        )
    else
        assert(
            not elm:is_observed(),
            "Found unexpected observation for element " .. elm.name
        )
    end
end
py:send("PASS")""")
    assert interface.mad.recv() == "PASS"


def get_marker_and_element_positions(
    interface: AcceleratorMadInterface, marker_name: str, element_name: str
) -> tuple[int | float, int, int | float, int]:
    """Helper to get positions and indices of marker and element."""
    interface.mad.send(f"""
py:send(loaded_sequence:upos("{marker_name}"))
py:send(loaded_sequence:index_of("{marker_name}"))
py:send(loaded_sequence:upos("{element_name}"))
py:send(loaded_sequence:index_of("{element_name}"))
""")
    return _recv_n(interface.mad, 4)
