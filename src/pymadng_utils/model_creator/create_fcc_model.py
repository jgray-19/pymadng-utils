"""Prepare the FCC-ee LCC MAD-X lattice for LOCO studies."""

from __future__ import annotations

import logging
import re
from pathlib import Path

LOGGER = logging.getLogger(__name__)

# ``hcor_qd0ar.0: kicker, hkick = -0.0, vkick = 0.0, lrad = 0.0, at=2.4;``
_CORRECTOR = re.compile(
    r"^(?P<name>(?P<plane>[hv])cor_[\w.]+):(?P<head>\s*kicker\b.*?)\b(?P=plane)kick\s*=\s*[-+0-9.eE]+(?P<tail>.*)$"
)
_BPM_MARKER = re.compile(r"^(?P<name>bpm_[\w.]+):\s*marker\b")
_SEXTUPOLE = re.compile(r"^(?P<head>\w[\w.]*:\s*sextupole\b[^;]*?),\s*at=")
_SEQUENCE_START = re.compile(r"^\w+\s*:\s*sequence\b", re.IGNORECASE)

#: Variable that drives the kick of corrector ``name``.
def kick_variable(name: str) -> str:
    return f"k_{name}"


def bpms_to_monitors(madx_text: str) -> str:
    """Declare the ``bpm_*`` markers as ``monitor`` (what the MAD-NG fitter expects of a BPM)."""
    return "\n".join(_BPM_MARKER.sub(r"\g<name>: monitor", line) for line in madx_text.splitlines()) + "\n"


def slice_sextupoles(madx_text: str, nslice: int = 3) -> str:
    """Give every sextupole ``nslice`` MAD-NG slices (a single slice is too coarse for the FCC-ee sextupoles)."""
    return "\n".join(_SEXTUPOLE.sub(rf"\g<head>, nslice={nslice}, at=", line) for line in madx_text.splitlines()) + "\n"


def defer_correctors(madx_text: str) -> tuple[str, dict[str, str]]:
    """Rewrite every ``hcor_*`` / ``vcor_*`` kicker so its kick is a MAD-X variable.

    Returns the new text and ``{corrector name: variable}``. The variables are
    declared (at zero) just before the sequence statement; no other line is touched.
    """
    lines = madx_text.splitlines()
    variables: dict[str, str] = {}
    for i, line in enumerate(lines):
        match = _CORRECTOR.match(line)
        if match is None:
            continue
        name, plane = match["name"], match["plane"]
        variable = kick_variable(name)
        variables[name] = variable
        lines[i] = f"{name}:{match['head']}{plane}kick := {variable}{match['tail']}"
    if not variables:
        raise ValueError("No hcor_/vcor_ kickers found in the MAD-X text")
    start = next((i for i, line in enumerate(lines) if _SEQUENCE_START.match(line)), None)
    if start is None:
        raise ValueError("No sequence statement found in the MAD-X text")
    declarations = [f"{variable} = 0.0;" for variable in variables.values()]
    return "\n".join([*lines[:start], *declarations, *lines[start:]]) + "\n", variables


def create_fcc_model(lattice_dir: Path | str, output_file: Path | str, *, madx_name: str = "fccee_z.madx") -> dict[str, str]:
    """Write ``output_file``: ``lattice_dir/madx_name`` with deferred corrector kicks, monitor BPMs and 3-slice sextupoles.

    Returns ``{corrector name: kick variable}``.
    """
    source = Path(lattice_dir) / madx_name
    text, variables = defer_correctors(slice_sextupoles(bpms_to_monitors(source.read_text())))
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(text)
    LOGGER.info("Wrote %s with %d deferred correctors", output_file, len(variables))
    return variables
