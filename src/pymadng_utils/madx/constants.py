# LHC Specific regex patterns for beam and year inference
import re

_DEFINE_NOMINAL_BEAMS_RE = re.compile(
    r"exec,\s*define_nominal_beams\([^;]*\)\s*;", re.IGNORECASE
)
_LHC_USE_SEQUENCE_RE = re.compile(r"use\s*,\s*sequence\s*=\s*lhcb([12])", re.IGNORECASE)
_LHC_SEQUENCE_TOKEN_RE = re.compile(r"\blhcb([12])\b", re.IGNORECASE)
_LHC_YEAR_RE = re.compile(
    r"^\s*!\s*LHC year\s+(?P<year>\S+)\s*$", re.IGNORECASE | re.MULTILINE
)

_POST_OPTICS_INSERT_MARKERS = (
    "\n! ----- Remove IR symmetry definitions -----\n",
    "\n! ----- Finalize Sequence -----\n",
)

# PSB Specific regex patterns for ring inference
_PSB_USE_SEQUENCE_RE = re.compile(r"use\s*,\s*sequence\s*=\s*psb([1-4])", re.IGNORECASE)
_PSB_SEQUENCE_TOKEN_RE = re.compile(r"\bpsb([1-4])\b", re.IGNORECASE)
_PSB_MATCH_END_RE = re.compile(r"^\s*ENDMATCH\s*;\s*$", re.IGNORECASE | re.MULTILINE)
