from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from pymadng_utils.mad import AcDipoleMadInterface

# Model data columns and headers
MODEL_STRENGTHS = [
    "k1l",
    "k2l",
    "k3l",
    "k4l",
    "k5l",
    "k1sl",
    "k2sl",
    "k3sl",
    "k4sl",
    "k5sl",
]

MODEL_HEADER = [
    "name",
    "type",
    "title",
    "origin",
    "date",
    "time",
    "refcol",
    "direction",
    "observe",
    "energy",
    "deltap",
    "length",
    "alfap",
    "q1",
    "q2",
    "q3",
    "dq1",
    "dq2",
    "dq3",
]

MODEL_COLUMNS = [
    "name",
    "kind",
    "s",
    "betx",
    "alfx",
    "bety",
    "alfy",
    "mu1",
    "mu2",
    "x",
    "px",
    "y",
    "py",
    "dx",
    "dpx",
    "dy",
    "dpy",
    "r11",
    "r12",
    "r21",
    "r22",
]


LOGGER = logging.getLogger(__name__)


class ModelCreatorMadInterface(AcDipoleMadInterface):
    """MAD-NG interface specialised for model creation workflows."""

    TUNE_MATCH_TOLERANCE = 1e-6

    def __init__(
        self,
        model_dir: Path,
        madx_file_path: Path,
        seq_name: str,
        energy: float,
        tunes: list[float],
        tune_knobs: dict[str, str],
        **mad_kwargs,
    ):
        super().__init__(**mad_kwargs)
        self.model_dir = model_dir
        self.madx_file = madx_file_path
        self.seq_name = seq_name
        self.energy = energy  # GeV
        self.tunes = tunes
        self.tune_knobs = tune_knobs

        if not self.madx_file.exists():
            raise FileNotFoundError(
                f"Saved sequence file not found in {self.madx_file}. Run make_madx_sequence first."
            )
        self.load_sequence(self.madx_file, self.seq_name)
        self.setup_beam(self.energy)

        LOGGER.info(f"Initialized MAD-NG model for sequence {self.seq_name}")
        self.match_model_tunes()


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
            qx_knob=self.tune_knobs["q1"],
            qy_knob=self.tune_knobs["q2"],
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

    def compute_and_export_twiss_tables(
        self,
    ) -> None:
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
        self.mad.send(MODEL_HEADER).send(MODEL_COLUMNS).send(MODEL_STRENGTHS)

        self.add_strength_columns("twiss_elements")

        self.observe_elements("BPM")
        self.mad.send(
            "twiss_data = twiss {sequence=loaded_sequence, coupling=true, observe=1}"
        )

        self.add_strength_columns("twiss_data")

        self.mad.send(f"""
twiss_elements:write("{self.model_dir / "twiss_elements.dat"}", cols, hnams)
twiss_data:write("{self.model_dir / "twiss.dat"}", cols, hnams)
{self.py_name}:send("export_complete")
""")

        result = self.mad.receive()
        if result != "export_complete":
            raise RuntimeError(f"Failed to export twiss tables: {result}")

        LOGGER.info(f"Successfully exported twiss tables to {self.model_dir}")

    def close(self) -> None:
        """Close the MAD-NG interface."""
        if self.mad is not None:
            self.mad.close()


class LhcModelCreatorMadInterface(ModelCreatorMadInterface):
    """MAD-NG interface specialised for model creation workflows."""

    TUNE_MATCH_TOLERANCE = 1e-6
    AC_MARKER_PATTERN = "MKQA.6L4.B{beam}"
    AC_MARKER_OFFSET = 1.583 / 2

    def __init__(
        self,
        model_dir: Path,
        madx_file_path: Path | None = None,
        energy: float = 6800,
        tunes: list[float] = [0.28, 0.31],
        drv_tunes: list[float] | None = None,
        tune_knobs_suffix: str = "_op",
        beam: int = 1,
        **mad_kwargs,
    ):
        if madx_file_path is None:
            madx_file_path = model_dir / f"lhcb{beam}_saved.seq"
        super().__init__(
            model_dir=model_dir,
            madx_file_path=madx_file_path,
            seq_name=f"lhcb{beam}",
            energy=energy,
            tunes=tunes,
            tune_knobs={
                "q1": f"dqx_b{beam}{tune_knobs_suffix}",
                "q2": f"dqy_b{beam}{tune_knobs_suffix}",
            },
            **mad_kwargs,
        )
        self.beam = beam
        self.drv_tunes = drv_tunes

    def compute_and_export_twiss_tables(
        self,
    ) -> None:
        """Compute twiss tables including AC dipole for LHC."""
        super().compute_and_export_twiss_tables()

        ac_marker = self.AC_MARKER_PATTERN.format(beam=self.beam)
        if self.drv_tunes is not None:
            self.install_ac_dipole(
                marker_name=ac_marker,
                nat_tunes=(self.tunes[0], self.tunes[1]),
                drv_tunes=(self.drv_tunes[0], self.drv_tunes[1]),
                offset=self.AC_MARKER_OFFSET,
            )
        self.mad.send(
            "twiss_ac = twiss {sequence=loaded_sequence, coupling=true, observe=1}"
        )
        self.add_strength_columns("twiss_ac")

        # Write AC dipole twiss table to file
        self.mad.send(f"""
twiss_ac:write("{self.model_dir / "twiss_ac.dat"}", cols, hnams)
{self.py_name}:send("export_complete")
""")

        result = self.mad.receive()
        if result != "export_complete":
            raise RuntimeError(f"Failed to export AC dipole twiss table: {result}")

        LOGGER.info(
            f"Successfully exported AC dipole twiss table to {self.model_dir / 'twiss_ac.dat'}"
        )
