"""Utilities for working with accelerator descriptors, MAD-NG, MAD-X, and model workflows."""

from importlib.metadata import version

from pymadng_utils.accelerators import FCC, LHC, PSB
from pymadng_utils.mad import (
    AcceleratorErrorsMadInterface,
    AcceleratorMadInterface,
    KnobMadInterface,
)

__version__ = version("pymadng-utils")

__all__ = [
    "FCC",
    "LHC",
    "PSB",
    "AcceleratorErrorsMadInterface",
    "AcceleratorMadInterface",
    "KnobMadInterface",
    "__version__",
]
