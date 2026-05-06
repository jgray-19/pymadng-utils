from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import tfs

from pymadng_utils.model_creator.constants import (
    MADNG_MODEL_COLUMNS,
    MADX_MODEL_COLUMNS,
    MODEL_HEADER,
    MODEL_STRENGTHS,
)

from .accelerator_mad_interface import AcceleratorMadInterface

if TYPE_CHECKING:
    from pathlib import Path

    from pymadng_utils.accelerators.base import Accelerator

LOGGER = logging.getLogger(__name__)


class ModelCreatorMadInterface(AcceleratorMadInterface):
    """MAD-NG interface specialised for model creation workflows."""

    TUNE_MATCH_TOLERANCE = 1e-6

    def __init__(
        self,
        accelerator: Accelerator,
        model_dir: Path,
        tunes: list[float] | None = None,
        drv_tunes: list[float] | None = None,
        **mad_kwargs,
    ):
        super().__init__(accelerator=accelerator, **mad_kwargs)
        self.model_dir = model_dir
        if tunes is None:
            # Just in case the twiss is madng based, it will be lowercase, not capitalised
            twiss = tfs.read(model_dir / "twiss.dat")
            headers = {key.lower(): value for key, value in twiss.headers.items()}
            tunes = [headers["q1"]%1, headers["q2"]%1]

        self.tunes = tunes
        self.setup_sequence()

        LOGGER.info(
            f"Initialized MAD-NG model for sequence {self.accelerator.seq_name}"
        )
        self.match_model_tunes()
        self.drv_tunes = drv_tunes

    def match_model_tunes(self) -> None:
        """Match model tunes using standard tune knobs for the current beam."""
        q1, q2 = self.get_current_tunes("Initial")

        if (
            abs(self.tunes[0] - (q1 % 1)) < self.TUNE_MATCH_TOLERANCE
            and abs(self.tunes[1] - (q2 % 1)) < self.TUNE_MATCH_TOLERANCE
        ):
            LOGGER.info("Tunes already matched within tolerance, skipping matching.")
            return

        self.match_tunes(
            target_qx=self.tunes[0],
            target_qy=self.tunes[1],
        )
        self.get_current_tunes("Final")

    def add_strength_columns(self, table_name: str) -> None:
        """Add multipole strength columns to a MAD-NG table."""
        self.mad.send(f"""
strength_cols = {self.py_name}:recv()
MAD.gphys.melmcol({table_name}, strength_cols)
""").send(MODEL_STRENGTHS)

    def get_current_tunes(self, label: str = "") -> tuple[float, float]:
        """Retrieve current tunes from the loaded sequence."""
        self.mad.send(f"""
local tbl = twiss {{sequence=loaded_sequence}};
{self.py_name}:send({{tbl.q1, tbl.q2}}, true)
""")
        q1, q2 = self.mad.recv()

        if not isinstance(q1, float) or not isinstance(q2, float):
            raise TypeError(f"Expected float tunes, got {type(q1)} and {type(q2)}")

        log_msg = f"{label} tunes" if label else "Tunes"
        LOGGER.info(f"{log_msg}: Q1={q1:.6f}, Q2={q2:.6f}")
        return q1, q2

    def compute_and_export_twiss_tables(self, export_madx_names = True) -> None:
        """Compute twiss tables and export model files."""
        self.mad.send("""
hnams = py:recv()
cols = py:recv()
str_cols = py:recv()

cols = MAD.utility.tblcat(cols, str_cols)
twiss_elements = twiss { sequence=loaded_sequence, coupling=true }
twiss_elements:select(nil, \\ -> true)
twiss_elements:deselect{pattern="drift"}
""")
        model_columns = MADX_MODEL_COLUMNS if export_madx_names else MADNG_MODEL_COLUMNS
        self.mad.send(MODEL_HEADER).send(model_columns).send(MODEL_STRENGTHS)

        self.add_strength_columns("twiss_elements")

        self.observe()
        self.mad.send(
            "twiss_data = twiss {sequence=loaded_sequence, coupling=true, observe=1}"
        )

        self.add_strength_columns("twiss_data")

        self.mad.send(f"""
twiss_elements:write("{self.model_dir / "twiss_elements.dat"}", cols, hnams)
twiss_data:write("{self.model_dir / "twiss.dat"}", cols, hnams)
""")
        self.check_madng_succeded("Failed to export twiss tables")

        if self.drv_tunes is not None:
            self.install_ac_dipole(
                nat_tunes=(self.tunes[0], self.tunes[1]),
                drv_tunes=(self.drv_tunes[0], self.drv_tunes[1]),
            )
        self.mad.send(
            "twiss_ac = twiss {sequence=loaded_sequence, coupling=true, observe=1}"
        )
        self.add_strength_columns("twiss_ac")

        # Write AC dipole twiss table to file
        self.mad.send(f"""
twiss_ac:write("{self.model_dir / "twiss_ac.dat"}", cols, hnams)
""")
        self.check_madng_succeded("Failed to export AC dipole twiss table")
        LOGGER.info(
            f"Successfully exported AC dipole twiss table to {self.model_dir / 'twiss_ac.dat'}"
        )

    def __enter__(self) -> ModelCreatorMadInterface:
        """Enter the MAD-NG context manager."""
        return self

    def close(self) -> None:
        """Close the MAD-NG interface."""
        if self.mad is not None:
            self.mad.close()
