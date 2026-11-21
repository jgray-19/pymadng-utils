"""Accelerator descriptors used by MAD-facing helpers."""

from pymadng_utils.accelerators.base import Accelerator
from pymadng_utils.accelerators.fcc import FCC
from pymadng_utils.accelerators.lhc import LHC
from pymadng_utils.accelerators.psb import PSB, PSB_FLAT_BOTTOM_GEV
from pymadng_utils.physics import PROTON_MASS_GEV

__all__ = [
    "FCC",
    "LHC",
    "PROTON_MASS_GEV",
    "PSB",
    "PSB_FLAT_BOTTOM_GEV",
    "Accelerator",
]
