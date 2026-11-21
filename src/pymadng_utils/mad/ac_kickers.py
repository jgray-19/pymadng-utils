"""Thin flattop AC kickers: install them at the AC-dipole element and drive their knobs.

Each plane has two fixed-phase kickers, ``a`` (lag 0, sin) and ``b`` (lag 1/4, cos), so the
kick ``0.3 / pc (a sin(phi) + b cos(phi))`` with ``phi = 2 pi turn freq`` is linear in the volts
``a`` and ``b``. ``turn`` is the MAD-NG turn counter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymadng import MAD

#: ``(name, plane, lag in turns)`` per kicker; plane 0 = horizontal, 1 = vertical.
KICKER_SPECS = (
    ("hackicker_a", 0, 0.0),
    ("hackicker_b", 0, 0.25),
    ("vackicker_a", 1, 0.0),
    ("vackicker_b", 1, 0.25),
)
#: Kicker element names in ``KICKER_SPECS`` order.
AC_KICKERS = tuple(name for name, _, _ in KICKER_SPECS)


def _for_each_kicker(mad: MAD, body: str) -> None:
    """Run ``body`` in Lua for each kicker, with ``i`` (1-based index) and ``e`` (element) set."""
    names = ", ".join(f"'{name}'" for name in AC_KICKERS)
    mad.send(f"""
for i, name in ipairs {{{names}}} do
    local e = loaded_sequence[name]
    {body}
end
""")


def install_ac_kickers(
    mad: MAD,
    acd_name: str,
    kicks: tuple[float, float, float, float],
    freqs: tuple[float, float],
) -> None:
    """Install the kickers at the position of the thin element ``acd_name``, which is kept.

    ``kicks`` = (a_x, b_x, a_y, b_y) are the initial volts; ``freqs`` = (h, v) drive tunes.
    """
    elements = ",\n".join(
        f"    {'hackicker' if plane == 0 else 'vackicker'} '{name}' "
        f"{{at=at, volt=kicks[{i}], freq=freqs[{plane + 1}], lag={lag!r}, ramp=ramp}}"
        for i, (name, plane, lag) in enumerate(KICKER_SPECS, start=1)
    )
    mad.send(f"""
local hackicker, vackicker in MAD.element
local kicks, freqs = {mad.py_name}:recv(), {mad.py_name}:recv()
local acd = loaded_sequence['{acd_name}']
assert(acd and acd.l == 0, "AC kickers need a thin AC-dipole element")
local at = loaded_sequence:spos(loaded_sequence:index_of(acd))
local ramp = {{0, 0, 1e12, 1e12}}
loaded_sequence:install{{
{elements}
}}
{mad.py_name}:send(true)
""")
    mad.send([float(v) for v in kicks])
    mad.send([float(v) for v in freqs])
    if not mad.recv():
        raise RuntimeError("Failed to install AC kickers")


def set_ac_kicker_freqs(mad: MAD, freqs: tuple[float, float]) -> None:
    """Set every kicker's ``freq`` to its plane's drive tune ``freqs`` = (h, v)."""
    values = ", ".join(repr(float(freqs[plane])) for _, plane, _ in KICKER_SPECS)
    _for_each_kicker(mad, f"e.freq = ({{{values}}})[i]")


def bind_ac_kicker_volts(mad: MAD, variables: tuple[str, str, str, str]) -> None:
    """Make each kicker's ``volt`` follow ``loaded_sequence[variable]`` (deferred)."""
    names = ", ".join(f"'{v}'" for v in variables)
    _for_each_kicker(mad, f"local var = ({{{names}}})[i]; e.volt = \\-> loaded_sequence[var]")


def shift_ac_kicker_phase(mad: MAD, turn_offset: int) -> None:
    """Make MAD turn ``t`` act as turn ``t + turn_offset``: ``lag = lag0 + turn_offset freq``."""
    lags = ", ".join(repr(lag) for _, _, lag in KICKER_SPECS)
    _for_each_kicker(
        mad, f"local lag = ({{{lags}}})[i]; e.lag = \\s -> lag + {int(turn_offset)} * s.freq"
    )
