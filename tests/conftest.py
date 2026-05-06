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

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface

if TYPE_CHECKING:
    from collections.abc import Generator

# Configure logging for tests
logging.getLogger("xdeps").setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Path to the example test data."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def seq_b1(data_dir: Path) -> Path:
    """Path to the example sequence file for beam 1 used by several tests."""
    return data_dir / "sequences" / "lhcb1.seq"


@pytest.fixture(scope="session")
def lhc_b1(seq_b1: Path) -> LHC:
    """Reusable LHC accelerator descriptor for beam 1 tests."""
    return LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0)


@pytest.fixture(scope="session")
def acc_models_path(data_dir: Path) -> Path:
    """Path to the example accelerator models directory used by several tests."""
    return data_dir / "acc-models-lhc"


@pytest.fixture(scope="function")
def interface(lhc_b1: LHC) -> Generator[AcceleratorMadInterface, None, None]:
    """Create a fresh AcceleratorMadInterface for each test."""
    iface = AcceleratorMadInterface(accelerator=lhc_b1)
    yield iface
    with contextlib.suppress(Exception):
        iface.close()


@pytest.fixture(scope="function")
def loaded_interface(interface: AcceleratorMadInterface) -> AcceleratorMadInterface:
    """Return an interface with the example sequence already loaded."""
    return interface


@pytest.fixture(scope="function")
def loaded_interface_with_beam(
    loaded_interface: AcceleratorMadInterface,
) -> AcceleratorMadInterface:
    """Return an interface with the example sequence loaded and beam set up."""
    return loaded_interface
