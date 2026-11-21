"""Package paths."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).absolute().parent

SHUSHING_SCRIPT = PACKAGE_DIR / "mad_scripts" / "shush_mad_output.mad"
MATCH_TUNES_SCRIPT = PACKAGE_DIR / "mad_scripts" / "match_tunes.mad"
