"""MAD-NG interface with knob and corrector management functionality."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pymadng_utils.io.utils import read_knobs

from .accelerator_mad_interface import AcceleratorMadInterface

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class KnobMadInterface(AcceleratorMadInterface):
    """Base class for accelerator-specific MAD-NG interfaces with common setup methods."""

    def apply_corrector_strengths(self, corrector_table: pd.DataFrame) -> None:
        """Apply corrector strengths from a table to MAD sequence."""
        logger.debug(f"Applying corrector strengths to {len(corrector_table)} elements")

        mappings = {
            "hkicker": [("kick", "hkick")],
            "vkicker": [("kick", "vkick")],
            "tkicker": [("hkick", "hkick"), ("vkick", "vkick")],
        }

        for _, row in corrector_table.iterrows():
            ename = row["ename"]
            try:
                element = self.mad.loaded_sequence[ename]
                kind = element.kind
            except KeyError:
                logger.warning(f"Element {ename} not found in loaded sequence")
                continue

            if kind in mappings:
                for attr, col in mappings[kind]:
                    if col in row.index:
                        self.mad.send(
                            f"loaded_sequence['{ename}'].{attr} = {self.py_name}:recv()"
                        )
                        self.mad.send(row[col])
                    else:
                        logger.warning(
                            f"Column '{col}' not found in corrector table for element {ename}"
                        )
            else:
                logger.warning(f"Element {ename} has unknown kind '{kind}'")

    def observe_bpms(
        self,
        bpm_pattern: str,
        bad_bpms: list[str] | None = None,
        unobserve_first: bool = True,
    ) -> None:
        """Set up the MAD-NG session to observe BPMs."""
        self.observe(bpm_pattern, unobserve_first)
        logger.debug(f"Set up observation for BPMs matching pattern: {bpm_pattern}")
        if bad_bpms:
            self.unobserve_elements(bad_bpms)
            logger.debug(f"Set up observation for bad BPMs: {bad_bpms}")

    def set_corrector_strengths(self, corrector_strengths: str | Path) -> None:
        """Load corrector strengths from file and apply them to the sequence."""
        import tfs

        path = Path(corrector_strengths)
        if not path.exists():
            logger.warning(f"Corrector strengths file not found: {path}")
            return
        try:
            corrector_table = tfs.read(path)

            # Filter out monitor elements from the corrector table
            non_monitors = corrector_table["kind"] != "monitor"
            corrector_table: tfs.TfsDataFrame = corrector_table[non_monitors]  # type: ignore[assignment, not-subscriptable]

            # Log how many non-zero correctors are being applied
            changed = (corrector_table["hkick"] != corrector_table["hkick_old"]) | (
                corrector_table["vkick"] != corrector_table["vkick_old"]
            )
            logger.info(
                f"Applying {changed.sum()} non-zero corrector strengths from {path}"  # type: ignore[unresolved-attribute]
            )

            # Apply corrector strengths for non-zero correctors only
            self.apply_corrector_strengths(corrector_table[changed])  # type: ignore[invalid-argument-type]
        except (tfs.TfsFormatError, UnboundLocalError) as e:
            logger.warning(
                f"Error reading or applying corrector strengths: {e}, assuming knobs"
            )
            knobs = read_knobs(path)
            for name, val in knobs.items():
                self.mad.send(f"MADX['{name}'] = {val}")

            logger.info(f"Set {len(knobs)} corrector knobs from {path}")

        self.mad.send(f"{self.py_name}:send(true)")
        assert self.mad.recv(), "Failed to set corrector strengths"

    def set_knobs(self, knobs_file: str | Path) -> None:
        """Load and set predefined knobs from file."""
        path = Path(knobs_file)
        knobs = read_knobs(path)
        # Get existing knob names in MAD
        prev = self.mad.recv_vars(*[f"MADX['{name}']" for name in knobs])

        for name, val in knobs.items():
            self.mad.send(f"MADX['{name}'] = {val}")

        self.mad.send(f"{self.py_name}:send(true)")
        assert self.mad.recv(), "Failed to set knobs"

        logger.debug(f"Previous knob values: {prev}")
        logger.debug(f"Set knobs from {path}: {len(knobs)}")
