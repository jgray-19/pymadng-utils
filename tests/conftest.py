"""
Common pytest fixtures for MAD interface tests.

This module contains shared fixtures used across MAD interface test modules.
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pymadng_utils.mad.core_mad_interface import CoreMadInterface

if TYPE_CHECKING:
    from collections.abc import Generator

# Configure logging for tests
logging.getLogger("xdeps").setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Path to the example corrector file used by several tests."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def seq_b1(data_dir: Path) -> Path:
    """Path to the example sequence file for beam 1 used by several tests."""
    return data_dir / "sequences" / "lhcb1.seq"

@pytest.fixture(scope="session")
def acc_models_path(data_dir: Path) -> Path:
    """Path to the example accelerator models directory used by several tests."""
    return data_dir / "acc-models-lhc"

@pytest.fixture(scope="function")
def interface() -> Generator[CoreMadInterface, None, None]:
    """Create a fresh CoreMadInterface for each test."""
    iface = CoreMadInterface()
    yield iface
    with contextlib.suppress(Exception):
        del iface


@pytest.fixture(scope="function")
def loaded_interface(interface: CoreMadInterface, seq_b1: Path) -> CoreMadInterface:
    """Fixture that returns an interface with the example sequence loaded."""
    interface.load_sequence(seq_b1, "lhcb1")
    return interface


@pytest.fixture(scope="function")
def loaded_interface_with_beam(loaded_interface: CoreMadInterface) -> CoreMadInterface:
    """Fixture that returns an interface with the example sequence loaded and beam set up."""
    loaded_interface.setup_beam(particle="proton", beam_energy=6800.0)
    return loaded_interface
