"""MAD-NG interfaces with a small, composable class hierarchy.

The module defines:
- ``CoreMadInterface``: minimal operational API used across projects.
- ``AcDipoleMadInterface``: optional extension that adds AC dipole installation.

Backward-compatible aliases are kept for existing imports.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pymadng import MAD

from pymadng_utils.config import SHUSHING_SCRIPT

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class CoreMadInterface:
    """
    Base class for MAD-NG interfaces providing core functionality.

    This class provides essential MAD-NG operations without automatic
    initialization, allowing subclasses to customise setup as needed.
    """

    def __init__(self, **mad_kwargs):
        """
        Initialise base MAD interface.

        Args:
            **mad_kwargs: Keyword arguments passed to pymadng.MAD()
        """
        self.mad = MAD(**mad_kwargs)
        logger.debug("Initialised MAD core interface")
        self.py_name = self.mad.py_name
        self.mad.send(SHUSHING_SCRIPT.read_text())

    def load_sequence(self, sequence_file: str | Path, seq_name: str) -> None:
        """
        Load a sequence file into MAD-NG.

        Args:
            sequence_file: Path to sequence file
            seq_name: Name of the sequence to load
        """
        logger.debug(f"Loading sequence from {sequence_file}")
        file_path = Path(sequence_file).resolve()
        self.mad.send("shush()")

        logger.debug("Caching MAD translation for faster subsequent loads")
        mad_cache_path = file_path.with_suffix(".mad")
        self.mad.send(f'MADX:load("{file_path}", "{mad_cache_path}")')

        if self.mad.MADX[seq_name] == 0:
            raise ValueError(
                f"Sequence '{seq_name}' not found in MAD file '{sequence_file}'"
            )
        self.mad.send(f"loaded_sequence = MADX.{seq_name}")
        self.mad["SEQ_NAME"] = seq_name
        self.mad.send("unshush()")

    def setup_beam(self, beam_energy: float, particle: str = "proton") -> None:
        """
        Set up beam parameters.

        Args:
            beam_energy: Beam energy in GeV
            particle: Particle type (default: proton)
        """
        logger.debug(
            f"Setting beam: particle={particle}, energy={beam_energy:.15e} GeV"
        )
        self.mad.send(
            f'loaded_sequence.beam = beam {{ particle = "{particle}", energy = {beam_energy:.15e} }}'
        )

    def observe_elements(self, pattern: str = "BPM") -> None:
        """
        Configure element observation for tracking.

        Args:
            pattern: Pattern to match elements for observation
        """
        logger.debug(f"Setting observation pattern: {pattern}")
        self.mad.send(f"""
local observed in MAD.element.flags
loaded_sequence:deselect(observed)
loaded_sequence:select(observed, {{pattern="{pattern}"}})
""")

    def unobserve_elements(self, elements: list[str]) -> None:
        """
        Remove specific elements from observation.

        Args:
            elements: List of element names to unobserve
        """
        logger.debug(f"Unobserving elements: {', '.join(elements)}")
        self.mad.send(
            "local observed in MAD.element.flags\n"
            + "\n".join(
                f'loaded_sequence:deselect(observed, {{pattern="{elem}"}})'
                for elem in elements
            )
        )

    def cycle_sequence(self, marker_name: str | None = None) -> None:
        """
        Cycle sequence to start from a specific marker.

        Args:
            marker_name: Name of marker to cycle to
        """
        logger.debug(f"Cycling sequence to start from {marker_name}")
        success_script = f"\n{self.py_name}:send(true)\n"
        if marker_name is None:
            self.mad.send("loaded_sequence:cycle()" + success_script)
        else:
            self.mad.send(f"loaded_sequence:cycle('{marker_name}')" + success_script)
        try:
            assert self.mad.recv(), (
                "Sequence cycling failed, you may have left something in the pipe."
            )
        except RuntimeError as e:
            logger.error(f"Error during sequence cycling: {e}")
            raise RuntimeError("Cycle failed - check MAD output for details") from e

    def replace_with_marker(
        self, element_name: str, marker_name: str | None = None
    ) -> str:
        """
        Replace an element with a marker.

        Args:
            element_name: Name of the element to replace
            marker_name: Name of the new marker

        Returns:
            str: The name of the marker that replaces the original element.
        """
        if marker_name is None:
            marker_name = element_name

        self.mad.send(f"""
correct_elm = MADX['{element_name}']
{self.py_name}:send(correct_elm)
{self.py_name}:send({{correct_elm.refpos or (loaded_sequence.refer or "centre"), correct_elm.l}}, true)
        """)
        elm = self.mad.recv("correct_elm")
        details = self.mad.recv()
        if elm == 0:
            raise ValueError(f"Could not find element: {element_name}")
        if details[0] != "centre" and details[1] > 0:
            raise ValueError(
                "Replacing markers currently not supported with non-centre reference or non-zero length"
            )
        self.mad.send(f"""
local new_elm = MAD.element.marker '{marker_name}' {{ at=correct_elm.at, from=correct_elm.from }}
local replaced = loaded_sequence:replace({{new_elm}}, '{element_name}')
MADX['{element_name}'] = new_elm ! Replace in the madx environment for later reference
{self.py_name}:send(replaced and #replaced or 0)
correct_elm = nil
        """)
        if (n_replaced := self.mad.recv()) != 1:
            raise ValueError(
                f"Element replacement failed, replaced {n_replaced} elements instead of 1"
            )

        return marker_name

    def install_marker(
        self, element_name: str, marker_name: str | None = None, offset: float = -1e-10
    ) -> str:
        """
        Install a marker element near an existing element.

        Args:
            element_name: Name of reference element
            marker_name: Name for new marker (auto-generated if None)
            offset: Offset from reference element

        Returns:
            Name of the installed marker
        """
        if marker_name is None:
            marker_name = f"{element_name}_marker"

        elm_idx = self.mad.send(
            f"{self.py_name}:send(loaded_sequence:index_of('{element_name}'))"
        ).recv()
        if elm_idx is None:
            raise ValueError(f"Element '{element_name}' not found in loaded sequence")
        if elm_idx <= 2:
            # First index is always $start marker, second is first real element
            offset = 1e-10  # Can't go before the first element -> MAD-NG bug

        quoted_marker = self.mad.quote_strings(marker_name)
        logger.debug(f"Installing marker {marker_name} at {element_name}")

        self.mad.send(f"""
loaded_sequence:install{{
MAD.element.marker {quoted_marker} {{ at={offset}, from="{element_name}" }}
}}
""")
        return marker_name

    def run_twiss(self, **twiss_kwargs) -> pd.DataFrame:
        """
        Run TWISS calculation and return results. If 'observe' is not specified,
        it defaults to 1 (observing observed elements every turn).

        Args:
            **twiss_kwargs: Additional arguments for twiss calculation

        Returns:
            TFS DataFrame with twiss results
        """
        logger.debug("Running twiss calculation")
        if "observe" not in twiss_kwargs:
            twiss_kwargs["observe"] = 1  # Default to no observation if not set

        try:
            self.mad["tws", "flw"] = self.mad.twiss(
                sequence="loaded_sequence", **twiss_kwargs
            )
        except ValueError as e:
            logger.error(f"Error during twiss calculation: {e}")
            raise RuntimeError("Twiss failed - check MAD output for details") from e

        df = self.mad.tws.to_df()
        if "name" in df.columns:
            df.set_index("name", inplace=True)
        return df

    def set_variables(self, **kwargs) -> None:
        """
        Set multiple MAD variables.

        Args:
            **kwargs: Variable names and their values
        """
        self.mad.send_vars(**kwargs)

    def set_madx_variables(self, **kwargs) -> None:
        """
        Set multiple MADX variables.

        Args:
            **kwargs: Variable names and their values
        """
        kwargs = {f"MADX['{key}']": value for key, value in kwargs.items()}
        self.set_variables(**kwargs)

    def get_variables(self, *names: str) -> tuple[float, ...]:
        """
        Get MAD variable values.

        Args:
            names: Variable names

        Returns:
            Variable values
        """
        return self.mad.recv_vars(*names, shallow_copy=True)

    def close(self) -> None:
        """Close the MAD-NG interface."""
        if self.mad is not None:
            logger.debug("Closing MAD interface")
            self.mad.close()


class AcDipoleMadInterface(CoreMadInterface):
    """Optional extension of ``CoreMadInterface`` with AC dipole installation."""

    def install_ac_dipole(
        self,
        marker_name: str,
        nat_tunes: tuple[float, float],
        drv_tunes: tuple[float, float],
        offset: float = 0.0,
    ) -> None:
        """
        Install AC dipole kickers at a specified marker location.

        The AC dipole consists of horizontal and vertical kicker elements that
        drive the beam at specified tunes. The beta functions at the marker
        location are automatically retrieved from the twiss table.

        Args:
            marker_name: Name of marker where AC dipole will be installed
            nat_tunes: Natural tunes (qx, qy)
            drv_tunes: Driven tunes (qx_drv, qy_drv)
            offset: Offset from marker location (default: 0.0)
        """
        logger.debug(
            f"Installing AC dipole at {marker_name} with natural tunes {nat_tunes} "
            f"and driven tunes {drv_tunes}"
        )

        # Get beta functions at AC marker location
        self.mad.send(f"""
local tws = twiss{{sequence=loaded_sequence}}
local betx = tws['{marker_name}'].beta11
local bety = tws['{marker_name}'].beta22
{self.py_name}:send({{betx, bety}}, true)
""")
        betx, bety = self.mad.recv()

        if betx is None or bety is None:
            raise ValueError(
                f"Could not retrieve beta functions at marker '{marker_name}'"
            )

        # Install AC kickers
        self.mad.send(f"""
local hackicker, vackicker in MAD.element
loaded_sequence:install{{
    hackicker "hackicker" {{
        at = {offset},
        from = "{marker_name}",
        nat_q = {nat_tunes[0]:.15e},
        drv_q = {drv_tunes[0]:.15e},
        ac_bet = {betx:.15e},
    }},
    vackicker "vackicker" {{
        at = {offset},
        from = "{marker_name}",
        nat_q = {nat_tunes[1]:.15e},
        drv_q = {drv_tunes[1]:.15e},
        ac_bet = {bety:.15e},
    }}
}}
""")

        logger.debug(
            f"AC dipole installed: betx={betx:.6f}, bety={bety:.6f} at {marker_name}"
        )
