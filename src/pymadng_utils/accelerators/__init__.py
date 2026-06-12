"""Accelerator descriptors used by MAD-facing helpers."""

from pymadng_utils.accelerators.base import Accelerator
from pymadng_utils.physics import PROTON_MASS_GEV
from pymadng_utils.accelerators.lhc import LHC
from pymadng_utils.accelerators.psb import (
    PSB,
    PSB_FLAT_BOTTOM_GEV,
)

__all__ = [
    "PROTON_MASS_GEV",
    "Accelerator",
    "LHC",
    "PSB",
    "PSB_FLAT_BOTTOM_MOMENTUM_GEV",
]
