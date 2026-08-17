"""
Configuration constants for the knob optimisation pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path

# =============================================================================
# OPTIMISATION SETTINGS
# =============================================================================

logger = logging.getLogger(__name__)

# =============================================================================
# FILE PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).absolute().parent
logger.info(f"Current project root: {PROJECT_ROOT}")

SHUSHING_SCRIPT = PROJECT_ROOT / "mad_scripts" / "shush_mad_output.mad"
