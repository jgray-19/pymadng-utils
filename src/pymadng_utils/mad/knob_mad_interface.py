"""MAD-NG interface with knob and corrector management functionality."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pymadng_utils.io.utils import read_knobs

from .accelerator_mad_interface import AcceleratorMadInterface

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pandas as pd

logger = logging.getLogger(__name__)

def resolve_knobs(knobs: Mapping[str, float] | str | Path) -> dict[str, float]:
    """Knob name/value pairs, whether given directly or as a file to read.

    Callers that already hold the knobs in memory pass the mapping and no file
    is ever written; callers holding a user-authored ``name<TAB>value`` file
    pass the path and it is read here, in exactly one place.
    """
    if isinstance(knobs, str | Path):
        return dict(read_knobs(Path(knobs)))
    return dict(knobs)


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

    def set_corrector_strengths(
        self, corrector_knobs: Mapping[str, float] | str | Path
    ) -> None:
        """Apply corrector settings, given as knobs or as a corrector table file.

        A mapping is a set of MAD-X knob variables and is sent as such. A path is
        read first: a TFS *corrector table* (``ename``/``kind``/``hkick``...) is
        applied element by element, anything else is parsed as a knobs file.
        The two are different data shapes, not two spellings of one, so the
        format is decided by reading -- never by catching a failure to apply.
        """
        if isinstance(corrector_knobs, str | Path):
            path = Path(corrector_knobs)
            if not path.exists():
                logger.warning(f"Corrector strengths file not found: {path}")
                return
            corrector_table = self._read_corrector_table(path)
            if corrector_table is not None:
                self._apply_changed_correctors(corrector_table, source=str(path))
                self.mad.send(f"{self.py_name}:send(true)")
                assert self.mad.recv(), "Failed to set corrector strengths"
                return

        knobs = resolve_knobs(corrector_knobs)
        for name, val in knobs.items():
            self.mad.send(f"MADX['{name}'] = {val}")
        logger.info(f"Set {len(knobs)} corrector knobs")

        self.mad.send(f"{self.py_name}:send(true)")
        assert self.mad.recv(), "Failed to set corrector strengths"

    @staticmethod
    def _read_corrector_table(path: Path) -> pd.DataFrame | None:
        """The TFS corrector table at *path*, or ``None`` if it is not one."""
        import tfs

        try:
            table = tfs.read(path)
        except (tfs.TfsFormatError, UnboundLocalError, ValueError) as error:
            logger.debug(
                f"{path} is not a TFS corrector table ({error}); reading as knobs"
            )
            return None
        required = {"ename", "kind", "hkick", "hkick_old", "vkick", "vkick_old"}
        missing = required.difference(table.columns)
        if missing:
            raise ValueError(
                f"{path} is a TFS table but is missing the corrector columns: "
                + ", ".join(sorted(missing))
            )
        return table

    def _apply_changed_correctors(
        self, corrector_table: pd.DataFrame, *, source: str
    ) -> None:
        non_monitors = corrector_table[corrector_table["kind"] != "monitor"]
        changed = (non_monitors["hkick"] != non_monitors["hkick_old"]) | (
            non_monitors["vkick"] != non_monitors["vkick_old"]
        )
        logger.info(
            f"Applying {changed.sum()} non-zero corrector strengths from {source}"
        )
        self.apply_corrector_strengths(non_monitors[changed])

    def set_knobs(self, tune_knobs: Mapping[str, float] | str | Path) -> None:
        """Set predefined knobs, given directly or as a knobs file."""
        knobs = resolve_knobs(tune_knobs)
        # Get existing knob names in MAD
        prev = self.mad.recv_vars(*[f"MADX['{name}']" for name in knobs])

        for name, val in knobs.items():
            self.mad.send(f"MADX['{name}'] = {val}")

        self.mad.send(f"{self.py_name}:send(true)")
        assert self.mad.recv(), "Failed to set knobs"

        logger.debug(f"Previous knob values: {prev}")
        logger.debug(f"Set {len(knobs)} knobs")
