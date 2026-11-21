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
        path: Path to the file where each line is "knob_name\tstrength".

    Returns:
        A dictionary mapping knob names to their true float strengths.
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
    Save matched tunes to file.

    Args:
        matched_tunes: Dictionary of tune knobs and values
        filepath: Path to save file
    """
    logger.info(f"Saving {len(knobs)} knobs to {filepath}")
    with filepath.open("w") as f:
        for key, val in knobs.items():
            f.write(f"{key}\t{val: .15e}\n")