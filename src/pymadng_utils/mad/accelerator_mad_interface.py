"""MAD-NG interfaces with a small, composable class hierarchy.

The module defines:
- ``AcceleratorMadInterface``: Base class providing core MAD-NG operations like sequence loading, beam setup, variable management, marker installation, and TWISS execution.


Backward-compatible aliases are kept for existing imports.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np
from pymadng import MAD

from pymadng_utils.config import SHUSHING_SCRIPT
from pymadng_utils.physics import dp2pt, pt2dp

if TYPE_CHECKING:
    import pandas as pd

    from pymadng_utils.accelerators.base import Accelerator

logger = logging.getLogger(__name__)

class MultipoleInfo(NamedTuple):
    dk_table: str  # MAD-NG table storing perturbations: "dknl" or "dksl"
    base_table: str  # MAD-NG table storing base strengths: "knl" or "ksl"
    index: int  # 1-based Lua index into the table
    dk_suffix: str  # knob name suffix used in MAD variables (e.g. "dk1l", "dk1sl")
    is_delta: (
        bool  # True when attr is already a delta (e.g. dk1l), False for absolute (k1)
    )


# Maximum multipole order supported (k0 through k{MAX_MULTIPOLE-1}).
# This also sets the size of the dknl/dksl deferred tables allocated in MAD-NG.
MAX_MULTIPOLE = 3


def _build_multipole_attrs(max_order: int) -> dict[str, MultipoleInfo]:
    """Generate multipole metadata from MAX_MULTIPOLE.

    Normal components use dknl/knl, skew use dksl/ksl.
    """
    attrs: dict[str, MultipoleInfo] = {}
    for n in range(max_order):
        idx = n + 1  # MAD-NG tables are 1-based
        for dk_table, base_table, abs_attr, delta_attr in [
            ("dknl", "knl", f"k{n}", f"dk{n}l"),
            ("dksl", "ksl", f"k{n}s", f"dk{n}sl"),
        ]:
            info_abs = MultipoleInfo(
                dk_table, base_table, idx, delta_attr, is_delta=False
            )
            info_delta = MultipoleInfo(
                dk_table, base_table, idx, delta_attr, is_delta=True
            )
            attrs[abs_attr] = info_abs
            attrs[delta_attr] = info_delta
    return attrs


MULTIPOLE_ATTRS = _build_multipole_attrs(MAX_MULTIPOLE)
MISALIGN_ATTRS = frozenset({"dx", "dy"})

MAGNET_STRENGTH_SUFFIXES = (
    {f".{attr}" for attr in MULTIPOLE_ATTRS}
    | {f".{attr}" for attr in MISALIGN_ATTRS}
    | {".kick"}
)

_PERTURBATION_BASE_SPECS: dict[str, dict[str, Any]] = {
    "d": {"kind": ("sbend", "rbend"), "attr": "k0"},
    "q": {"kind": ("quadrupole",), "attr": "k1"},
    "s": {"kind": ("sextupole",), "attr": "k2"},
}


class AcceleratorMadInterface:
    """
    Base class for MAD-NG interfaces providing core functionality.

    This class provides essential MAD-NG operations without automatic
    initialization, allowing subclasses to customise setup as needed.
    """

    def __init__(self, accelerator: Accelerator, **mad_kwargs):
        """
        Initialise base MAD interface.

        Args:
            accelerator: Accelerator configuration object
            **mad_kwargs: Keyword arguments passed to pymadng.MAD()
        """
        self.accelerator = accelerator
        self.mad = MAD(**mad_kwargs)
        logger.debug("Initialised MAD core interface")
        self.py_name = self.mad.py_name
        self.mad.send(SHUSHING_SCRIPT.read_text())
        self.mad.send("__observed_flag__ = MAD.element.flags.observed")
        self.mad.send("MADX.option.rbarc = false")

        # Load the default sequence and set up the beam immediately, as these are common to all workflows.
        self.setup_sequence()
        self.beta: float = self.mad.loaded_sequence.beam.beta

    def __repr__(self) -> str:
        """Return a concise developer-facing interface representation."""
        return (
            f"{type(self).__name__}("
            f"seq_name={self.accelerator.seq_name!r}, "
            f"py_name={self.py_name!r})"
        )

    def __str__(self) -> str:
        """Return a concise human-readable interface summary."""
        return f"{type(self).__name__}({self.accelerator.seq_name})"

    def dp2pt(self, dp: float) -> float:
        """Convert relative momentum deviation ``dp/p`` to MAD-NG ``pt`` using the loaded beam."""
        return dp2pt(dp, self.beta)

    def pt2dp(self, pt: float) -> float:
        """Convert MAD-NG ``pt`` to relative momentum deviation ``dp/p`` using the loaded beam."""
        return pt2dp(pt, self.beta)

    def load_sequence(self) -> None:
        """
        Load a sequence file into MAD-NG from the accelerator configuration.
        """
        logger.debug(f"Loading sequence from {self.accelerator.sequence_file}")
        file_path = Path(self.accelerator.sequence_file).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Sequence file not found: {file_path}")
        self.mad.send("shush()")

        logger.debug("Caching MAD translation for faster subsequent loads")
        mad_cache_path = file_path.with_suffix(".mad")
        self.mad.send(f'MADX:load("{file_path}", "{mad_cache_path}", {{rbarc=false}})')

        if self.mad.MADX[self.accelerator.seq_name] == 0:
            raise ValueError(
                f"Sequence '{self.accelerator.seq_name}' not found in MAD file '{self.accelerator.sequence_file}'"
            )
        self.mad.send(f"loaded_sequence = MADX.{self.accelerator.seq_name}")
        self.mad["SEQ_NAME"] = self.accelerator.seq_name
        self.mad.send("unshush()")

    def setup_beam(self) -> None:
        """
        Set up beam parameters in MAD-NG based on the accelerator configuration.
        """
        self.mad.send(
            f'loaded_sequence.beam = beam {{ particle = "{self.accelerator.particle}", energy={self.accelerator.energy:.15e} }}',
        )
        logger.debug(
            f"Setting beam: particle={self.accelerator.particle}, energy={self.accelerator.energy:.15e} GeV"
        )

    def setup_sequence(self) -> None:
        """
        Load the sequence and set up the beam in MAD-NG.

        This method combines sequence loading and beam setup for convenience.
        """
        self.load_sequence()
        self.setup_beam()

    def unobserve_all_elements(self) -> None:
        """Unobserve all elements in the loaded sequence."""
        self.mad.send("loaded_sequence:deselect(__observed_flag__)")

    def observe(self, pattern: str | None = None, unobserve_first: bool = True) -> None:
        """
        Configure element observation for tracking.

        Args:
            pattern: Pattern to match elements for observation (default: None, which uses the accelerator's BPM pattern)
            unobserve_first: Whether to unobserve all elements before observing the new pattern (default: True)
        """
        if pattern is None:
            pattern = self.accelerator.bpm_pattern
        logger.debug(f"Setting observation pattern: {pattern}")
        if unobserve_first:
            self.unobserve_all_elements()
        self.mad.send(
            f"loaded_sequence:select(__observed_flag__, {{pattern='{pattern}'}})"
        )

    def observe_element(self, element_name: str, unobserve_first: bool = False) -> None:
        """Observe a single element matched by its exact name.

        Unlike :meth:`observe`, which treats its argument as a Lua pattern, this
        anchors (``^``...``$``) and escapes the name so it matches only that
        element. Observing a bare name such as ``BPH.13008`` would otherwise be an
        unanchored Lua pattern in which ``.`` is a wildcard, so it also selects any
        neighbour whose name contains it as a substring (e.g. the centre-reference
        marker ``OMC_MARKER_BPH.13008``), corrupting the observed-BPM count.
        """
        logger.debug(f"Observing exact element: {element_name}")
        if unobserve_first:
            self.unobserve_all_elements()
        # Escape Lua pattern magic characters and anchor both ends, all in Lua so
        # the exact name (not a pattern) drives the selection.
        self.mad.send(
            f"""
local _exact = '{element_name}'
local _pattern = '^' .. _exact:gsub('[%(%)%.%%%+%-%*%?%[%]%^%$]', '%%%1') .. '$'
loaded_sequence:select(__observed_flag__, {{pattern=_pattern}})
"""
        )

    def unobserve(self, pattern: str | None = None) -> None:
        """
        Remove observation for elements matching a pattern.

        Args:
            pattern: Pattern to match elements for unobserving, (default: None, which uses the accelerator's BPM pattern)
        """
        if pattern is None:
            pattern = self.accelerator.bpm_pattern
        logger.debug(f"Unobserving elements matching pattern: {pattern}")
        self.mad.send(
            f"loaded_sequence:deselect(__observed_flag__, {{pattern='{pattern}'}})"
        )

    def unobserve_elements(self, elements: list[str]) -> None:
        """
        Remove specific elements from observation.

        Args:
            elements: List of element names to unobserve
        """
        for elm in elements:
            self.unobserve(elm)

    def observe_elements(
        self, element_names: list[str], unobserve_first: bool = True
    ) -> None:
        if unobserve_first:
            self.unobserve_all_elements()
        for pattern in element_names:
            self.observe_element(pattern, unobserve_first=False)

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

    def make_element_thin(
        self,
        element_name: str,
        marker_name: str | None = None,
        observe_after: bool = True,
    ) -> str:
        """
        Make an element thin by replacing it with a zero-length copy of itself.

        The replacement inherits from the original element (preserving its kind
        and attributes) but with ``l = 0`` and ``at`` pinned to the original
        element's centre position, so the optics at the thin element match those
        at the centre of the thick original.

        Thinning is only permitted when the element does not bend or focus the
        beam, i.e. ``k0``, ``k1`` and ``k2`` are all zero (or nil). Collapsing a
        focusing/bending element to zero length would silently drop its effect on
        the optics, so that case is rejected.

        Args:
            element_name: Name of the element to replace
            marker_name: Name of the new marker
            observe_after: Whether to observe the new marker after replacement

        Returns:
            str: The name of the marker that replaces the original element.
        """
        if marker_name is None:
            marker_name = element_name

        self.mad.send(f"""
correct_elm = MADX['{element_name}']
{self.py_name}:send(correct_elm)
{self.py_name}:send({{correct_elm.k0 or 0, correct_elm.k1 or 0, correct_elm.k2 or 0}}, true)
        """)
        elm = self.mad.recv("correct_elm")
        k0, k1, k2 = self.mad.recv()
        if elm == 0:
            raise ValueError(f"Could not find element: {element_name}")
        nonzero = {
            name: value
            for name, value in (("k0", k0), ("k1", k1), ("k2", k2))
            if abs(float(value)) > 0
        }
        if nonzero:
            raise ValueError(
                f"Refusing to thin '{element_name}': it has non-zero {nonzero}; "
                "collapsing a bending/focusing element to zero length would change the optics."
            )
        self.mad.send(f"""
local new_elm = correct_elm '{marker_name}' {{ l = 0, at = loaded_sequence:upos(correct_elm) }}
local replaced = loaded_sequence:replace({{new_elm}}, '{element_name}')
MADX['{marker_name}'] = new_elm ! Replace in the madx environment for later reference
{self.py_name}:send(replaced and #replaced or 0)
correct_elm = nil
        """)
        if (n_replaced := self.mad.recv()) != 1:
            raise ValueError(
                f"Element replacement failed, replaced {n_replaced} elements instead of 1"
            )
        if observe_after:
            self.observe_element(marker_name)
        return marker_name

    def insert_acd_markers(self, element_name: str | None = None) -> tuple[str, str]:
        """Insert thin monitor endpoints immediately before and after the AC-dipole element.

        Args:
            element_name: Optional explicit element name. Defaults to the
                accelerator's AC-dipole marker element.

        Returns:
            Tuple of ``(before_marker_name, after_marker_name)``. The historical
            names are kept, but the installed elements are monitors so MAD-NG
            monitor callbacks include them in tracking output.
        """
        element_name = self.accelerator.ac_dipole_name

        before_marker = self.accelerator.acd_marker_name("before")
        after_marker = self.accelerator.acd_marker_name("after")

        self.mad.send(f"""
{self.py_name}:send(loaded_sequence['{element_name}'] ~= 0, true)
        """)
        if not bool(self.mad.recv()):
            raise ValueError(f"Could not find element: {element_name}")

        self.mad.send(f"""
local seq_elm = loaded_sequence['{element_name}']
{self.py_name}:send(loaded_sequence:upos(seq_elm), true)
{self.py_name}:send({{seq_elm.refpos or (loaded_sequence.refer or "centre"), seq_elm.l}}, true)
        """)
        element_pos = self.mad.recv()
        element_refpos, element_length = self.mad.recv()
        logger.debug(
            f"ACD element '{element_name}' position: {element_pos}, refpos: {element_refpos}, length: {element_length}"
        )
        if element_refpos != "centre":
            raise ValueError(
                "ACD marker insertion currently only supports centre reference"
            )
        if element_length > 0:
            self.mad.send(f"""
-- Replace the thick ACD element with a thin copy so the before/after markers
-- are not inside a thick body and can be used as valid range endpoints.
-- loaded_sequence:replace recomputes surrounding drifts automatically.
local seq_elm = loaded_sequence['{element_name}']
local replaced = loaded_sequence:replace({{seq_elm {{ l = 0, at = {self.py_name}:recv() }}}}, '{element_name}')
{self.py_name}:send(replaced and #replaced or 0)
            """).send(element_pos)
            if (n_replaced := self.mad.recv()) != 1:
                raise ValueError(
                    f"Element replacement failed during ACD marker insertion, replaced {n_replaced} elements instead of 1"
                )

        start_pos = element_pos - 1e-10
        end_pos = element_pos + 1e-10

        self.mad.send(f"""
local monitor in MAD.element
loaded_sequence:install{{
    monitor "{before_marker}" {{ at = {start_pos:.15e} }},
    monitor "{after_marker}" {{ at = {end_pos:.15e} }},
}}
MADX['{before_marker}'] = loaded_sequence['{before_marker}']
MADX['{after_marker}'] = loaded_sequence['{after_marker}']
{self.py_name}:send({{MADX['{before_marker}'] ~= 0, MADX['{after_marker}'] ~= 0}}, true)
correct_elm = nil
        """)
        before_exists, after_exists = self.mad.recv()
        if not bool(before_exists) or not bool(after_exists):
            raise ValueError(f"ACD marker insertion failed for element {element_name}")

        return before_marker, after_marker

    def run_twiss(self, **twiss_kwargs) -> pd.DataFrame:
        """
        Run TWISS calculation and return results. If 'observe' is not specified,
        it defaults to 1 (observing observed elements every turn).

        Args:
            **twiss_kwargs: Additional arguments for twiss calculation. The
                convenience keyword ``pt`` runs the closed-orbit search at the
                given longitudinal momentum by passing it as the sixth initial
                phase-space coordinate (``X0 = {x, px, y, py, t, pt}``) rather
                than converting to ``deltap``. This is numerically identical to
                ``deltap = pt2dp(pt)`` (closed orbit and dispersion agree to
                round-off) but keeps the caller in native ``pt`` space and drops
                the ``pt -> dp/p`` round-trip. It cannot be combined with an
                explicit ``X0`` or ``deltap``.

        Returns:
            TFS DataFrame with twiss results
        """
        logger.debug("Running twiss calculation")
        if "pt" in twiss_kwargs:
            pt = twiss_kwargs.pop("pt")
            if "X0" in twiss_kwargs or "deltap" in twiss_kwargs:
                raise ValueError(
                    "run_twiss: 'pt' cannot be combined with 'X0' or 'deltap'"
                )
            twiss_kwargs["X0"] = [0.0, 0.0, 0.0, 0.0, 0.0, float(pt)]
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
        df.headers["particle"] = self.accelerator.particle
        df.headers["energy"] = self.accelerator.energy
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

    # --- multipole perturbation table helpers ---

    def _ensure_deferred_dk_table(self, element_name: str, dk_table: str) -> None:
        """Initialise the dknl/dksl table as deferred without resetting values."""
        zeros_or_old = ",\n".join(
            [f"old[{i}] or 0.0" for i in range(1, MAX_MULTIPOLE + 1)]
        )
        self.mad.send(f"""
if not MAD.typeid.is_deferred(loaded_sequence['{element_name}'].{dk_table}) then
    local old = loaded_sequence['{element_name}'].{dk_table} or {{}}
    loaded_sequence['{element_name}'].{dk_table} = MAD.typeid.deferred {{\n{zeros_or_old}}}
end
        """)

    def _set_dk_component(
        self, element_name: str, info: MultipoleInfo, delta: float
    ) -> None:
        """Write a delta strength into the correct dknl/dksl slot."""
        self._ensure_deferred_dk_table(element_name, info.dk_table)
        self.mad.send(f"""
loaded_sequence['{element_name}'].{info.dk_table}[{info.index}] = {self.py_name}:recv()
        """)
        self.mad.send(delta)

    # --- misalignment helpers (separate from multipole logic) ---

    def _set_misalignment(self, element_name: str, attr: str, value: float) -> None:
        """Set a misalignment value, preserving other misalignment attributes already set."""
        # The plain `if not mad[...]` truthiness test is unreliable here because pymadng
        # returns a MadRef object even for an unset table, which is always truthy.
        self.mad.send(
            f"{self.py_name}:send(loaded_sequence['{element_name}'].misalign, true)"
        )
        misalign_dict = self.mad.recv()
        if not isinstance(misalign_dict, dict) or len(misalign_dict) == 0:
            self.mad[f"loaded_sequence['{element_name}'].misalign"] = []
        self.mad[f"loaded_sequence['{element_name}'].misalign.{attr}"] = value

    def _get_misalignment(self, element_name: str, attr: str) -> float:
        """Get a misalignment value, returning 0.0 if not set."""
        self.mad.send(
            f"{self.py_name}:send(loaded_sequence['{element_name}'].misalign, true)"
        )
        misalign_dict = self.mad.recv()
        if not isinstance(misalign_dict, dict) or len(misalign_dict) == 0:
            return 0.0
        return float(misalign_dict.get(attr, 0.0))

    # --- generic element strength get/set ---

    def _get_effective_element_strength(self, element_name: str, attr: str) -> float:
        """Return the effective element strength, including any dknl/dksl perturbations."""
        if attr in MISALIGN_ATTRS:
            return self._get_misalignment(element_name, attr)

        info = MULTIPOLE_ATTRS.get(attr)
        if info is None:
            return self.mad[f"loaded_sequence['{element_name}'].{attr}"]

        # If the dk table hasn't been initialised yet, return the base attribute directly.
        if len(getattr(self.mad.loaded_sequence[element_name], info.dk_table)) == 0:
            return self.mad[f"loaded_sequence['{element_name}'].{attr}"]

        if info.is_delta:
            return float(
                self.mad[
                    f"loaded_sequence['{element_name}'].{info.dk_table}[{info.index}]"
                ]
            )

        # Absolute attrs: the perturbation is stored in the *integrated* dknl/dksl
        # table, so its per-metre contribution to the gradient is dknl[i]/l. The
        # effective per-metre strength is therefore base + dknl[i]/l. (A dknl[i]=X
        # is equivalent to changing the per-metre strength by X/l -- verified by
        # tune equivalence.) Thin elements (l==0) have no per-metre form, so fall
        # back to the raw sum.
        length = self.mad[f"loaded_sequence['{element_name}'].l"]
        denom = float(length) if length not in (None, 0) else 1.0
        self.mad.send(f"""
local {info.dk_table}, {attr} in loaded_sequence['{element_name}']
{self.py_name}:send({attr} + {info.dk_table}[{info.index}]/{denom!r})
        """)
        return self.mad.recv()

    def _get_base_element_strength(self, element_name: str, attr: str) -> float:
        """Return the element strength ignoring any dknl/dksl perturbation."""
        if self.mad[f"loaded_sequence['{element_name}'].{attr}"] is not None:
            return float(self.mad[f"loaded_sequence['{element_name}'].{attr}"])
        info = MULTIPOLE_ATTRS[attr]
        return float(
            self.mad[
                f"loaded_sequence['{element_name}'].{info.base_table}[{info.index}]"
            ]
        )

    def _set_effective_element_strength(
        self, element_name: str, attr: str, target: float
    ) -> None:
        """Set an element strength, routing multipole updates through dknl/dksl."""
        info = MULTIPOLE_ATTRS.get(attr)
        if info is None:
            self.mad[f"loaded_sequence['{element_name}'].{attr}"] = target
            return

        if info.is_delta:
            # Delta attrs (dk1l, ...) are already the integrated dknl value.
            delta = float(target)
        else:
            # Absolute attrs: target is a per-metre strength. The perturbation is
            # stored integrated in dknl/dksl, so the delta to write is the per-metre
            # change times the element length. (Inverse of the /l applied when
            # reading; thin elements l==0 fall back to the raw per-metre delta.)
            base = float(self.mad[f"loaded_sequence['{element_name}'].{attr}"])
            length = self.mad[f"loaded_sequence['{element_name}'].l"]
            delta_per_metre = float(target) - base
            delta = (
                delta_per_metre * float(length)
                if length not in (None, 0)
                else delta_per_metre
            )
        self._set_dk_component(element_name, info, delta)

    # --- public magnet-strength API ---

    def set_magnet_strengths(self, strengths: dict[str, float]) -> None:
        """Set magnet strengths, routing multipole updates through dknl/dksl.

        Names must end with one of :data:`_MAGNET_STRENGTH_SUFFIXES`. Multipole
        knobs (absolute ``.k0``/``.k1``... or integrated-delta ``.dk0l``/``.dk1l``...)
        are folded into the deferred ``dknl``/``dksl`` tables so they actually move
        the closed orbit / TWISS; misalignments (``.dx``/``.dy``) go through the
        element ``misalign`` table; anything else is set as a direct field.
        """
        logger.debug(f"Setting {len(strengths)} magnet strengths")
        direct_variables: dict[str, float] = {}

        for name, strength in strengths.items():
            if not any(name.endswith(suffix) for suffix in MAGNET_STRENGTH_SUFFIXES):
                raise ValueError(
                    f"Magnet name '{name}' must end with one of {MAGNET_STRENGTH_SUFFIXES}"
                )
            magnet_name, attr = name.rsplit(".", 1)
            if attr in MISALIGN_ATTRS:
                self._set_misalignment(magnet_name, attr, strength)
            elif attr in MULTIPOLE_ATTRS:
                self._set_effective_element_strength(magnet_name, attr, strength)
            else:
                direct_variables[f"loaded_sequence['{magnet_name}'].{attr}"] = strength

        if direct_variables:
            self.set_variables(**direct_variables)

    def get_magnet_strengths(self, names: list[str]) -> dict[str, float]:
        """Get effective magnet strengths, including any dknl/dksl perturbations."""
        return {
            name: self._get_effective_element_strength(*name.rsplit(".", 1))
            for name in names
        }

    def get_base_magnet_strengths(self, names: list[str]) -> dict[str, float]:
        """Get underlying magnet strengths without any dknl/dksl perturbation."""
        return {
            name: self._get_base_element_strength(*name.rsplit(".", 1))
            for name in names
        }

    def _resolve_relative_error(
        self,
        family_config: dict[str, Any],
        element_name: str,
        rel_error: float | None,
    ) -> float | None:
        """Resolve the relative error for one element from global or family settings."""
        if rel_error is not None:
            return rel_error

        relative_error_table = family_config.get("relative_error_table")
        if isinstance(relative_error_table, dict):
            for prefix, rel_value in relative_error_table.items():
                if element_name.startswith(str(prefix)):
                    return float(rel_value)

        default_rel_std = family_config.get("default_rel_std")
        if default_rel_std is not None:
            return float(default_rel_std)
        if relative_error_table is not None:
            return None
        raise ValueError(
            f"Relative error not specified for family with kind {family_config['kind']}"
        )

    def apply_magnet_perturbations(
        self,
        rel_error: float | None = 1e-4,
        seed: int = 42,
        magnet_type: str | list[str] = "all",
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Apply accelerator-specific perturbations to the loaded sequence."""
        if magnet_type == "all":
            requested = ["d", "q", "s"]
        else:
            requested = magnet_type if isinstance(magnet_type, list) else list(magnet_type)
        if not requested:
            return {}, {}

        family_overrides = self.accelerator.get_perturbation_families()
        family_configs = [
            _PERTURBATION_BASE_SPECS[family] | family_overrides[family]
            for family in ("d", "q", "s")
            if family in requested and family in family_overrides
        ]
        if not family_configs:
            return {}, {}

        rng = np.random.default_rng(seed)
        magnet_strengths: dict[str, float] = {}
        true_strengths: dict[str, float] = {}

        for elm in self.mad.loaded_sequence:
            for family_config in family_configs:
                if elm.kind not in family_config["kind"]:
                    continue
                pattern = family_config.get("pattern")
                if pattern and not re.match(str(pattern), str(elm.name)):
                    continue

                element_rel_error = self._resolve_relative_error(
                    family_config=family_config,
                    element_name=str(elm.name),
                    rel_error=rel_error,
                )
                if element_rel_error is None:
                    continue

                attr = str(family_config["attr"])
                strength_before = float(elm[attr])
                delta = float(rng.normal(0, abs(strength_before * element_rel_error)))
                strength_after = strength_before + delta

                info = MULTIPOLE_ATTRS.get(attr)
                if info is not None:
                    self._set_effective_element_strength(
                        str(elm.name), attr, strength_after
                    )
                    # ``_set_effective_element_strength`` writes the *integrated*
                    # perturbation (delta * length) into dknl, and the ``dk*l`` knob
                    # name is itself integrated, so record the integrated value. This
                    # keeps the returned dict consistent with what
                    # ``get_magnet_strengths`` reads back for the same knob (which
                    # returns dknl[i] directly).
                    length = float(elm.l)
                    magnet_strengths[f"{elm.name}.{info.dk_suffix}"] = delta * length
                else:
                    elm[attr] = strength_after
                    magnet_strengths[f"{elm.name}.{attr}"] = strength_after
                true_strengths[str(elm.name)] = strength_after
                break

        return magnet_strengths, true_strengths

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

    def check_madng_succeded(self, fail_message: str) -> None:
        """Check if the last MAD-NG command succeeded, raise error if not."""
        result = self.mad.send(f"{self.py_name}:send('success')").recv()
        if result != "success":
            raise RuntimeError(f"{fail_message}: {result}")

    def close(self) -> None:
        """Close the MAD-NG interface."""
        if self.mad is not None:
            logger.debug("Closing MAD interface")
            self.mad.close()

    def _info_required(self) -> int:
        # If the logging level is info, we want info = 2, if it's debug, we want info = 5 at least
        if logger.isEnabledFor(logging.DEBUG):
            return 7
        if logger.isEnabledFor(logging.INFO):
            return 2
        return 0

    def match_tunes(
        self,
        target_qx: float,
        target_qy: float,
        qx_knob: str | None = None,
        qy_knob: str | None = None,
        deltap: float = 0.0,
    ) -> dict[str, float]:
        """Match tunes using tune variables provided by the accelerator.

        Args:
            target_qx: Target horizontal tune (fractional or full)
            target_qy: Target vertical tune (fractional or full)
            qx_knob: MAD variable name for horizontal tune knob (optional if accelerator provides get_tune_variables)
            qy_knob: MAD variable name for vertical tune knob (optional if accelerator provides get_tune_variables)
            deltap: Relative momentum deviation for tune matching (default: 0.0)
        """
        if qx_knob is None or qy_knob is None:
            qx_knob, qy_knob = self.accelerator.tune_variables

        # Check if we have been given the total tunes rather than the fractional
        qx_int, qy_int = self.accelerator.tune_integers
        if target_qx >= 1:
            qx_int = 0
        if target_qy >= 1:
            qy_int = 0

        self.mad["result"] = self.mad.match(
            command=rf"\ -> twiss{{sequence=loaded_sequence, deltap={deltap:.16e}}}",
            variables=[
                {"var": f"'MADX.{qx_knob}'", "name": f"'{qx_knob}'"},
                {"var": f"'MADX.{qy_knob}'", "name": f"'{qy_knob}'"},
            ],
            equalities=[
                {"expr": f"\\t -> t.q1-({qx_int}+{target_qx})", "name": "'q1'"},
                {"expr": f"\\t -> t.q2-({qy_int}+{target_qy})", "name": "'q2'"},
            ],
            objective={"fmin": 1e-8},
            info=self._info_required(),
        )
        return {
            qx_knob: self.mad[f"MADX['{qx_knob}']"],
            qy_knob: self.mad[f"MADX['{qy_knob}']"],
        }

    def _check_mad_response(self, expected: str, error_msg: str) -> None:
        """Check that the response from MAD-NG matches the expected value."""
        try:
            if (result := self.mad.recv()) != expected:
                raise RuntimeError(f"Unexpected response from MAD-NG: {result}. {error_msg}")
        except Exception as exc:
            raise RuntimeError(error_msg) from exc

    def perform_orbit_correction(
        self,
        machine_deltap: float,
        target_qx: float,
        target_qy: float,
        corrector_file: Path | None,
        twiss_name: str = "zero_twiss",
    ) -> dict[str, float]:
        """Perform orbit correction followed by off-momentum tune rematching."""
        qx_knob, qy_knob = self.accelerator.tune_variables
        qx_int, qy_int = self.accelerator.tune_integers
        self.mad["machine_deltap"] = machine_deltap
        self.mad["correct_file"] = str(corrector_file.absolute()) if corrector_file else None

        self.mad.send(rf"""
local correct, option in MAD

io.write("*** orbit correction using off momentum twiss\n")
local tws_offmom = twiss {{ sequence=loaded_sequence, deltap=machine_deltap }}

local fmt = option.numfmt ; option.numfmt = "% -.16e"
local tbl = correct {{ sequence=loaded_sequence, model=tws_offmom, target={twiss_name}, method="svd", info=1, plane="x" }}
if correct_file then
    tbl:write(correct_file)
end
option.numfmt = fmt

io.write("*** rematching tunes for off-momentum twiss\n")
match {{
  command := twiss {{sequence=loaded_sequence, observe=0, deltap=machine_deltap}},
  variables = {{ rtol=1e-4,
    {{ var = 'MADX.{qx_knob}', name='{qx_knob}' }},
    {{ var = 'MADX.{qy_knob}', name='{qy_knob}' }},
  }},
  equalities = {{ tol = 1e-6,
    {{ expr = \t -> t.q1-{qx_int + target_qx:.16e}, name='q1' }},
    {{ expr = \t -> t.q2-{qy_int + target_qy:.16e}, name='q2' }},
  }},
  objective = {{fmin = 1e-8}},
  info={self._info_required()}
}}

{self.py_name}:send("Complete")
        """)
        self._check_mad_response(
            "Complete", "Error during MAD-NG orbit correction and tune matching"
        )
        return {
            qx_knob: self.mad[f"MADX['{qx_knob}']"],
            qy_knob: self.mad[f"MADX['{qy_knob}']"],
        }

    def install_ac_dipole(
        self,
        nat_tunes: tuple[float, float],
        drv_tunes: tuple[float, float],
        deltap: float = 0.0,
    ) -> None:
        """
        Install AC dipole kickers at the location given by the accelerator's AC dipole marker, with specified natural and driven tunes.

        The AC dipole consists of horizontal and vertical kicker elements that
        drive the beam at specified tunes. The beta functions at the marker
        location are automatically retrieved from the twiss table.

        Args:
            marker_name: Name of marker where AC dipole will be installed
            nat_tunes: Natural tunes (qx, qy)
            drv_tunes: Driven tunes (qx_drv, qy_drv)
            deltap: Relative momentum deviation for the marker beta functions.
            offset: Offset from marker location (default: 0.0)
        """
        install_point = self.accelerator.ac_dipole_name
        logger.debug(
            f"Installing AC dipole at {install_point} with natural tunes {nat_tunes} "
            f"and driven tunes {drv_tunes}"
        )

        # Get beta functions at AC marker location
        self.mad.send(f"""
acd_location = loaded_sequence:upos("{install_point}")
{self.py_name}:send(acd_location, true)
""")
        acd_location = self.mad.recv()
        if acd_location is None:
            raise ValueError(
                f"Could not find position for AC dipole installation point: {install_point}"
            )

        # Install AC kickers
        self.mad.send(f"""
local marker in MAD.element
-- Make the ACD thin with a marker just to get the beta functions at the correct location
loaded_sequence:replace({{marker '__custom_marker__' {{at = acd_location}}}}, "{install_point}")
""")

        self.mad.send(f"""
local hackicker, vackicker in MAD.element

! Do a twiss and replace the ac_bet values for the kickers
local tws = twiss{{sequence=loaded_sequence, deltap={deltap:.16e}}}
local betx = tws['__custom_marker__'].beta11
local bety = tws['__custom_marker__'].beta22
loaded_sequence:install{{
    hackicker "hackicker" {{
        at = acd_location,
        nat_q = {nat_tunes[0]:.15e},
        drv_q = {drv_tunes[0]:.15e},
        ac_bet = betx,
    }},
    vackicker "vackicker" {{
        at = acd_location,
        nat_q = {nat_tunes[1]:.15e},
        drv_q = {drv_tunes[1]:.15e},
        ac_bet = bety,
    }}
}}
loaded_sequence:remove('__custom_marker__') -- Clean up the temporary marker
        """)

        logger.debug(f"AC dipole installed: at {install_point}, {acd_location:.6f} m")

    def __enter__(self) -> AcceleratorMadInterface:
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and close MAD interface."""
        self.close()

class AcceleratorErrorsMadInterface(AcceleratorMadInterface):
    """MAD interface variant that applies accelerator-specific startup errors."""

    def __init__(self, accelerator: Accelerator, **mad_kwargs):
        super().__init__(accelerator=accelerator, **mad_kwargs)
        self.accelerator.apply_accelerator_specific_errors(self)
