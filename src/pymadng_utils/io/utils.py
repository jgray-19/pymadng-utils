"""
Utilities for reading and saving knob data.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_knobs(file_path: str | Path) -> dict[str, float]:
    """
    Read knob strengths from a tab-delimited file.

    Args:
        file_path: File where each line is "knob_name\tstrength"; lines without exactly two
            tab-separated fields are skipped.

    Returns:
        A dictionary mapping knob names to their float strengths.
    """
    path = Path(file_path)
    logger.info(f"Reading knobs from {path}")
    strengths: dict[str, float] = {}
    with path.open("r") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != 2:
                continue
            knob, val = parts
            strengths[knob] = float(val)
    logger.debug(f"Read {len(strengths)} knobs from {path}")
    return strengths


def save_knobs(knobs: dict[str, float], filepath: Path) -> None:
    """
    Write knob strengths to a tab-separated file, one "knob_name\tstrength" line per knob.

    Args:
        knobs: Dictionary of knob names and values
        filepath: Path of the file to write
    """
    logger.info(f"Saving {len(knobs)} knobs to {filepath}")
    with filepath.open("w") as f:
        for key, val in knobs.items():
            f.write(f"{key}\t{val: .15e}\n")
