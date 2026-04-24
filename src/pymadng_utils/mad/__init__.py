"""MAD-NG interface utilities."""

from .accelerator_mad_interface import (
    AcceleratorErrorsMadInterface,
    AcceleratorMadInterface,
)
from .knob_mad_interface import KnobMadInterface

__all__ = [
    "AcceleratorMadInterface",
    "AcceleratorErrorsMadInterface",
    "KnobMadInterface",
    "ModelCreatorMadInterface",
]


def __getattr__(name: str):
    if name == "ModelCreatorMadInterface":
        from .model_creator_mad_interface import ModelCreatorMadInterface

        return ModelCreatorMadInterface
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
