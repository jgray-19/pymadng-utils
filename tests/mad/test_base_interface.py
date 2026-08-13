"""
Tests for AcceleratorMadInterface.

This module contains pytest tests for the AcceleratorMadInterface class.
"""

from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path

import numpy as np
import pytest

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface
from pymadng_utils.physics import beta_from_energy
from pymadng_utils.physics import dp2pt as physics_dp2pt
from tests.mad.helpers import (
    check_beam_setup,
    check_element_observations,
    check_interface_basic_init,
    check_sequence_loaded,
    cleanup_interface,
    get_marker_and_element_positions,
)


class MissingSequenceLHC(LHC):
    @property
    def seq_name(self) -> str:
        return "does_not_exist"


@pytest.fixture(scope="function")
def loaded_ac_interface_with_beam(seq_b1: Path):
    """Fixture that returns an AC-capable interface with sequence loaded and beam set up."""
    interface = AcceleratorMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0)
    )
    yield interface
    interface.close()


def test_init(seq_b1: Path) -> None:
    """Test initialization of AcceleratorMadInterface."""
    interface = AcceleratorMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0)
    )
    check_interface_basic_init(interface, "py")
    interface.mad.send("a = 2")
    assert interface.mad.a == 2
    cleanup_interface(interface)


def test_repr_and_str_are_concise(interface: AcceleratorMadInterface) -> None:
    assert repr(interface) == "AcceleratorMadInterface(seq_name='lhcb1', py_name='py')"
    assert str(interface) == "AcceleratorMadInterface(lhcb1)"


def test_load_sequence(interface: AcceleratorMadInterface) -> None:
    """Test loading a sequence file during initialisation."""
    check_sequence_loaded(interface, "lhcb1")
    assert (
        interface.mad.loaded_sequence is not None and interface.mad.loaded_sequence != 0
    )
    assert interface.mad.MADX.lhcb1 is not None and interface.mad.MADX.lhcb1 != 0


def test_load_sequence_unknown_sequence_raises(seq_b1: Path) -> None:
    """Loading a valid file with a missing sequence name should fail clearly."""
    with pytest.raises(
        ValueError,
        match=r"Sequence 'does_not_exist' not found in MAD file",
    ):
        AcceleratorMadInterface(
            accelerator=MissingSequenceLHC(
                beam=1, sequence_file=seq_b1, kinetic_energy=6800.0
            )
        )


def test_load_sequence_bad_file_raises(tmp_path: Path) -> None:
    """Loading an invalid sequence file should fail through the missing-sequence check."""
    bad_sequence = tmp_path / "bad.seq"
    bad_sequence.write_text("this is not a MAD-X sequence\n")

    with pytest.raises(
        ValueError,
        match=r"Sequence 'lhcb1' not found in MAD file",
    ):
        AcceleratorMadInterface(
            accelerator=LHC(beam=1, sequence_file=bad_sequence, kinetic_energy=6800.0)
        )


def test_setup_beam(loaded_interface: AcceleratorMadInterface) -> None:
    """Test beam parameters from the accelerator descriptor are applied."""
    check_beam_setup(loaded_interface, particle="proton", kinetic_energy=6800.0)


def test_beta_matches_python_and_mad_ng_calculations(
    loaded_interface: AcceleratorMadInterface,
) -> None:
    """The accelerator beta and MAD-NG beam beta should agree."""
    accelerator = loaded_interface.accelerator
    expected_beta = beta_from_energy(accelerator.energy, accelerator.particle)
    mad_ng_beta = loaded_interface.mad.loaded_sequence.beam.beta

    assert accelerator.beta == pytest.approx(expected_beta)
    assert loaded_interface.beta == pytest.approx(mad_ng_beta)
    assert loaded_interface.beta == pytest.approx(accelerator.beta)


def test_interface_and_accelerator_use_matching_beta_for_dp_pt(
    loaded_interface: AcceleratorMadInterface,
) -> None:
    """Both conversion paths should use equivalent beta values."""
    dp = 0.015

    assert loaded_interface.dp2pt(dp) == pytest.approx(
        loaded_interface.accelerator.dp2pt(dp)
    )
    assert loaded_interface.pt2dp(loaded_interface.dp2pt(dp)) == pytest.approx(dp)


# Full-mantissa values: no short decimal literal reproduces these bit-for-bit,
# so any conversion input that gets formatted into the MAD chunk (rather than
# sent down the pipe as a double) comes back changed.
AWKWARD_DELTAPS = [1.0 / 3.0e3, 0.1234567890123456789e-2, math.pi * 1e-4]
AWKWARD_DELTAPS_LABELS = ["1/3000", "long_decimal", "pi/10000"]


@pytest.mark.parametrize("dp", AWKWARD_DELTAPS, ids=AWKWARD_DELTAPS_LABELS)
def test_interface_dp_pt_conversions_use_mad_ng_gphys(
    loaded_interface: AcceleratorMadInterface, dp: float
) -> None:
    """The interface converts through ``MAD.gphys`` on the sequence beam.

    This must be MAD-NG's own conversion, not the Python one: only then does a
    converted ``deltap`` seed exactly what ``twiss{deltap=...}`` seeds itself.
    The two implementations agree to ~1e-13, so the assertion is bit-exact
    against gphys and merely close against the Python version.

    The inputs deliberately have full mantissas, which also makes this fail if
    the value is interpolated into the MAD chunk as a formatted literal instead
    of being sent as a double.
    """
    interface = loaded_interface

    interface.mad.send(
        "py:send(MAD.gphys.dp2pt(py:recv(), loaded_sequence.beam.beta))"
    ).send(dp)
    expected = interface.mad.recv()

    assert interface.dp2pt(dp) == expected
    # ... and it is genuinely not the Python implementation.
    python_value = physics_dp2pt(dp, interface.beta)
    assert interface.dp2pt(dp) != python_value
    assert interface.dp2pt(dp) == pytest.approx(python_value, rel=1e-12)


@pytest.mark.parametrize("dp", AWKWARD_DELTAPS, ids=AWKWARD_DELTAPS_LABELS)
def test_dp_pt_conversion_inputs_cross_the_pipe_bit_exactly(
    loaded_interface: AcceleratorMadInterface, dp: float
) -> None:
    """The conversion input reaches MAD-NG as an exact double, not a rounded literal.

    Recovers the input from the conversion output: ``pt2dp`` is the analytic
    inverse of ``dp2pt``, so the recovered value can only land within
    ~1e-13 of the original if the original arrived intact. A ``%.10e``-style
    interpolation into the MAD chunk truncates ~6 digits and is caught here,
    while the earlier bit-exact comparisons cannot see it for round inputs.
    """
    interface = loaded_interface

    recovered = interface.pt2dp(interface.dp2pt(dp))

    assert recovered == pytest.approx(dp, rel=1e-12), (
        f"input mangled in transport: {recovered!r} from {dp!r}"
    )


@pytest.mark.parametrize(
    "pattern",
    ["MB.A33R2.B1", "BPM"],
    ids=["SingleElement", "BPMElements"],
)
def test_observe_elements(
    loaded_interface: AcceleratorMadInterface,
    pattern: str,
) -> None:
    """Test configuring element observation."""
    loaded_interface.observe(pattern)
    check_element_observations(loaded_interface, f"elm.name:match('{pattern}')")
    loaded_interface.unobserve_elements([pattern])


def test_cycle_sequence(loaded_interface: AcceleratorMadInterface) -> None:
    """Test cycling sequence to a marker."""
    loaded_interface.mad.send("""py:send(loaded_sequence:raw_get("__cycle"))""")
    assert loaded_interface.mad.recv() is None

    loaded_interface.cycle_sequence("IP5")
    loaded_interface.mad.send("""py:send(loaded_sequence:raw_get("__cycle"))""")
    cycle_marker = loaded_interface.mad.recv()
    assert cycle_marker == "IP5"

    loaded_interface.cycle_sequence()
    loaded_interface.mad.send("""py:send(loaded_sequence:raw_get("__cycle"))""")
    cycle_marker = loaded_interface.mad.recv()
    assert cycle_marker is None


def test_cycle_sequence_invalid_marker_raises(
    loaded_interface: AcceleratorMadInterface,
) -> None:
    """Cycling to a missing marker should raise the wrapped runtime error."""
    with pytest.raises(
        RuntimeError, match="Cycle failed - check MAD output for details"
    ):
        loaded_interface.cycle_sequence("NOT_A_MARKER")


@pytest.mark.parametrize(
    "element_name, marker_name, expected_marker_name",
    [
        (
            "S.DS.L1.B1",
            None,
            "S.DS.L1.B1",
        ),
        (
            "S.DS.L1.B1",
            "MyMarker",
            "MyMarker",
        ),
    ],
    ids=["same_name", "custom_name"],
)
def test_make_element_thin(
    loaded_interface: AcceleratorMadInterface,
    element_name,
    marker_name,
    expected_marker_name,
) -> None:
    """Test that make_element_thin replaces an element in-place, preserving kind and position."""
    interface = loaded_interface

    interface.mad.send(f"py:send(MADX['{element_name}'].kind)")
    kind_before = interface.mad.recv()

    (
        marker_position_before,
        marker_index_before,
        elem_position_before,
        elem_index_before,
    ) = get_marker_and_element_positions(interface, expected_marker_name, element_name)
    ret_name = interface.make_element_thin(element_name, marker_name)
    marker_position_after, marker_index_after, elem_position_after, elem_index_after = (
        get_marker_and_element_positions(interface, expected_marker_name, element_name)
    )

    if element_name != expected_marker_name:
        assert marker_position_before is None
        assert marker_index_before is None
        assert elem_position_after is None
        assert elem_index_after is None
    else:
        assert marker_position_before == elem_position_before
        assert marker_index_before == elem_index_before

    assert marker_index_after == elem_index_before
    assert marker_position_after == elem_position_before
    assert ret_name == expected_marker_name

    interface.mad.send(f"py:send(MADX['{expected_marker_name}'].kind)")
    kind_after = interface.mad.recv()
    assert kind_after == kind_before

    interface.mad.send(f"py:send(loaded_sequence['{expected_marker_name}'].l)")
    assert interface.mad.recv() == 0


def test_make_element_thin_missing_element_raises(
    loaded_interface: AcceleratorMadInterface,
) -> None:
    """Making a missing element thin should raise a clear error."""
    with pytest.raises(ValueError, match=r"Could not find element: NOT_AN_ELEMENT"):
        loaded_interface.make_element_thin("NOT_AN_ELEMENT")


def test_insert_acd_markers(
    loaded_interface: AcceleratorMadInterface,
) -> None:
    """Insert before/after markers around the accelerator AC-dipole element."""
    interface = loaded_interface
    element_name = interface.accelerator.ac_dipole_name
    before_name = interface.accelerator.acd_marker_name("before")
    after_name = interface.accelerator.acd_marker_name("after")

    (
        before_position_before,
        before_index_before,
        element_position_before,
        element_index_before,
    ) = get_marker_and_element_positions(interface, before_name, element_name)
    after_position_before, after_index_before, _, _ = get_marker_and_element_positions(
        interface, after_name, element_name
    )

    ret_before, ret_after = interface.insert_acd_markers()

    (
        before_position_after,
        before_index_after,
        element_position_after,
        element_index_after,
    ) = get_marker_and_element_positions(interface, before_name, element_name)
    after_position_after, after_index_after, _, _ = get_marker_and_element_positions(
        interface, after_name, element_name
    )

    assert before_position_before is None
    assert before_index_before is None
    assert after_position_before is None
    assert after_index_before is None
    assert ret_before == before_name
    assert ret_after == after_name
    assert before_index_after is not None
    assert element_index_after is not None
    assert after_index_after is not None
    assert before_position_after < after_position_after
    assert element_position_after == element_position_before
    assert (
        len({int(before_index_after), int(element_index_after), int(after_index_after)})
        == 3
    )


def test_getset_variables(interface: AcceleratorMadInterface) -> None:
    """Test setting MAD variables."""
    interface.set_variables(KQTL_1L1_B1=1.2, KQTL_1L2_B1=2.3)
    assert interface.mad.KQTL_1L1_B1 == 1.2
    assert interface.mad.KQTL_1L2_B1 == 2.3

    v1, v2 = interface.get_variables("KQTL_1L1_B1", "KQTL_1L2_B1")
    assert v1 == 1.2
    assert v2 == 2.3


def test_set_madx_variables(interface: AcceleratorMadInterface) -> None:
    """Test setting MAD-X variables."""
    interface.set_madx_variables(kqtl_1l1_b1=1.5, KQTL_1L2_B1=2.5)
    assert interface.mad.MADX.KQTL_1L1_B1 == 1.5
    assert interface.mad.MADX.kqtl_1l2_b1 == 2.5

def test_twiss(loaded_interface_with_beam: AcceleratorMadInterface):
    """Test twiss function."""
    interface = loaded_interface_with_beam
    twiss_df = interface.run_twiss()

    # Assert the columns we expect are present
    expected_columns = [
        "s",
        "beta11",
        "beta22",
        "alfa11",
        "alfa22",
        "mu1",
        "mu2",
        "dx",
        "dy",
    ]
    for col in expected_columns:
        assert col in twiss_df.columns, (
            f"Expected column {col} not found in twiss output"
        )
    assert "name" not in twiss_df.columns, "Column 'name' should be the index"
    assert twiss_df.index.name == "name", (
        f"Expected index name to be 'name', got {twiss_df.index.name}"
    )

    # There should only be one entry, since by default observe = 1 and nothing has been set to be observed
    assert len(twiss_df) == 1, f"Expected 1 twiss entry, got {len(twiss_df)}"
    # Check the marker is named $end
    assert twiss_df.index[0] == "$end", (
        f"Expected marker name '$end', got {twiss_df.index[0]}"
    )

    # Check the tunes
    assert abs(twiss_df.headers["q1"] - 62.28) < 3e-7, f"Unexpected Qx: {twiss_df.q1}"
    assert abs(twiss_df.headers["q2"] - 60.31) < 3e-7, f"Unexpected Qy: {twiss_df.q2}"

    # Now set observe to 0
    twiss_df = interface.run_twiss(observe=0)
    # There should be loads of entries now, including drifts
    assert len(twiss_df) > 1000, f"Expected >1000 twiss entries, got {len(twiss_df)}"
    assert "drift__3" in twiss_df.index, (
        "Expected to find drift elements in twiss output"
    )
    assert "MB.A33R2.B1" in twiss_df.index, (
        "Expected to find magnet elements in twiss output"
    )
    assert abs(twiss_df.headers["q1"] - 62.28) < 3e-7, f"Unexpected Qx: {twiss_df.headers['q1']}"
    assert abs(twiss_df.headers["q2"] - 60.31) < 3e-7, f"Unexpected Qy: {twiss_df.headers['q2']}"

    # Now observe BPMs
    interface.observe("BPM")
    twiss_df = interface.run_twiss()
    # There should only be BPMs observed
    assert len(twiss_df) == 563, f"Expected 563 twiss entries, got {len(twiss_df)}"
    assert all(twiss_df.index.str.match(r"^BPM.*")), (
        "Expected only BPM elements in twiss output"
    )
    assert abs(twiss_df.headers["q1"] - 62.28) < 3e-7, f"Unexpected Qx: {twiss_df.headers['q1']}"
    assert abs(twiss_df.headers["q2"] - 60.31) < 3e-7, f"Unexpected Qy: {twiss_df.headers['q2']}"
    interface.unobserve_elements(["BPM"])

def test_twiss_pt_kwarg_is_exact_x0_injection(
    loaded_interface_with_beam: AcceleratorMadInterface,
) -> None:
    """run_twiss(pt=X) is bit-identical to run_twiss(X0=[0,0,0,0,0,X]).

    The ``pt`` keyword is defined as exactly that ``X0`` injection, so this is
    the contract it must satisfy to the bit.
    """
    interface = loaded_interface_with_beam
    interface.observe("BPM")

    pt = 1e-3
    tws_pt = interface.run_twiss(pt=pt)
    tws_x0 = interface.run_twiss(X0=[0.0, 0.0, 0.0, 0.0, 0.0, pt])

    for col in ("x", "px", "y", "py", "dx", "dpx", "dy", "dpy"):
        if col not in tws_pt.columns:
            continue
        np.testing.assert_array_equal(
            tws_pt[col].to_numpy(),
            tws_x0[col].to_numpy(),
            err_msg=f"pt vs explicit X0 differ in {col}",
        )
    interface.unobserve_elements(["BPM"])


@pytest.mark.parametrize("deltap", [1e-3, -1e-3, 1e-4, 1.0 / 3.0e3])
def test_twiss_pt_and_deltap_are_the_same_code_path(
    loaded_interface_with_beam: AcceleratorMadInterface, deltap: float
) -> None:
    """``deltap=dp`` and ``pt=dp2pt(dp)`` agree to the last bit, as does MAD-NG.

    Both keywords are normalised to the same ``X0`` pt injection, with ``deltap``
    converted by ``MAD.gphys.dp2pt`` on the sequence's beam and moved over the
    pipe as a double, so all three routes -- our ``deltap``, our ``pt``, and
    MAD-NG's own ``twiss{deltap=...}`` -- must be bit-identical.

    The assertion is deliberately bit-for-bit. The previous tolerances (atol
    1e-9 on x, 1e-7 on dx) were loose enough to hide a real ~1e-9 orbit /
    ~1e-8 dispersion discrepancy: the test converted with ``pt2dp`` and
    compared against MAD-NG's ``dp2pt``, and those two are not mutual inverses
    to the bit (~1e-13 relative on the seed, amplified by the closed-orbit
    search over the ring). Converting once, in one direction, removes it.
    """
    interface = loaded_interface_with_beam
    interface.observe("BPM")

    pt = interface.dp2pt(deltap)
    tws_deltap = interface.run_twiss(deltap=deltap)
    tws_pt = interface.run_twiss(pt=pt)

    # MAD-NG's native deltap handling, with no interference from run_twiss
    # beyond matching its method=6 default (xsuite-equivalent integrator).
    interface.mad["tws_native", "flw_native"] = interface.mad.twiss(
        sequence="loaded_sequence", deltap=deltap, observe=1, method=6
    )
    tws_native = interface.mad.tws_native.to_df().set_index("name")

    assert list(tws_pt.columns) == list(tws_deltap.columns)
    for other, label in ((tws_pt, "pt"), (tws_native, "native deltap")):
        for col in tws_deltap.columns:
            if tws_deltap[col].dtype.kind != "f":
                continue
            np.testing.assert_array_equal(
                tws_deltap[col].to_numpy(),
                other[col].to_numpy(),
                err_msg=f"deltap vs {label} differ in column {col}",
            )
    for header in ("q1", "q2", "dq1", "dq2"):
        if header in tws_deltap.headers:
            assert tws_deltap.headers[header] == tws_pt.headers[header], header

    # The seeded pt is exactly what MAD-NG propagated. That the offset genuinely
    # takes effect on the optics is pinned quantitatively by
    # test_twiss_deltap_moves_the_orbit_by_the_predicted_amount below.
    np.testing.assert_array_equal(tws_deltap["pt"].to_numpy(), pt)
    interface.unobserve_elements(["BPM"])


@pytest.mark.parametrize(
    "kinetic_energy, expected_beta",
    [(6800.0, 0.9999999904832221), (0.160, 0.5197529494)],
    ids=["flat_top", "low_beta0"],
)
def test_twiss_deltap_moves_the_orbit_by_the_predicted_amount(
    seq_b1: Path, kinetic_energy: float, expected_beta: float
) -> None:
    """A ``deltap`` must move the closed orbit by ``dx * dp2pt(deltap)``, and the
    residual must fall off as the offset squared.

    This is the guard against ``deltap`` silently not taking effect. Asserting
    only that the orbit is "not zero" would pass for any wrong-but-nonzero
    seed, so instead the orbit response is checked against MAD-NG dispersion in
    three independent ways:

    1. the least-squares scale of the orbit shift onto ``dx`` equals the seeded
       ``pt`` to <5e-4, so the magnitude is right, not merely nonzero;
    2. that scale error, and the residual around the linear prediction, halve
       when the offset halves -- the signature of a genuine second-order
       remainder. A seed that is dropped, doubled, or beta-scaled wrongly
       cannot reproduce this convergence;
    3. at ``beta0 ~ 0.52`` the prediction built from raw ``deltap`` instead of
       ``pt`` is off by ~93%, so the conversion direction is pinned too.

    Note MAD-NG's ``dx`` is d(x)/d(pt), not d(x)/d(dp/p) -- which is precisely
    why (3) discriminates and why the flat-top case cannot.
    """
    interface = AcceleratorMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, kinetic_energy=kinetic_energy)
    )
    try:
        assert interface.beta == pytest.approx(expected_beta, abs=1e-9)
        interface.observe("BPM")

        tws0 = interface.run_twiss()
        x0 = tws0["x"].to_numpy()
        dx0 = tws0["dx"].to_numpy()
        assert np.abs(dx0).max() > 1.0, "no dispersion to predict against"

        scale_errors = {}
        residuals = {}
        for deltap in (1e-4, 5e-5):
            pt = interface.dp2pt(deltap)
            shift = interface.run_twiss(deltap=deltap)["x"].to_numpy() - x0
            assert np.abs(shift).max() > 0.0, "deltap had no effect on the orbit"

            # (1) magnitude: best-fit scale of the response onto the dispersion.
            best_fit = float(dx0 @ shift / (dx0 @ dx0))
            assert best_fit == pytest.approx(pt, rel=5e-4), (
                f"orbit responds as pt={best_fit:.6e}, seeded pt={pt:.6e}"
            )
            scale_errors[deltap] = abs(best_fit / pt - 1.0)

            residual = np.abs(shift - dx0 * pt).max() / np.abs(shift).max()
            assert residual < 2e-2
            residuals[deltap] = residual

            # (3) the same prediction built from raw deltap is badly wrong once
            # beta0 departs from 1, which pins the conversion direction.
            if interface.beta < 0.9:
                raw = np.abs(shift - dx0 * deltap).max() / np.abs(shift).max()
                assert raw > 20 * residual, (
                    f"deltap and pt predictions are not distinguishable: "
                    f"{raw:.3e} vs {residual:.3e}"
                )

        # (2) second-order convergence: halving the offset halves both errors.
        assert residuals[5e-5] / residuals[1e-4] == pytest.approx(0.5, rel=0.05)
        assert scale_errors[5e-5] / scale_errors[1e-4] == pytest.approx(0.5, rel=0.05)
    finally:
        interface.close()


def test_twiss_deltap_is_converted_to_pt_not_used_raw(seq_b1: Path) -> None:
    """``deltap`` is seeded as ``dp2pt(deltap)``, not as a raw ``pt``.

    Deliberately runs the LHC sequence at a 160 MeV kinetic energy, where
    ``beta0 ~ 0.52`` and so ``pt`` and ``dp/p`` differ by ~48%. The normalised
    strengths in the sequence do not depend on the beam energy, so the optics
    are unchanged and only the conversion is under test. At the real 6.8 TeV
    energy ``beta0 = 1 - 1e-8``, the two are indistinguishable in the optics,
    which is exactly why the tests above cannot pin the conversion down: a
    dropped, inverted, or wrong-beta conversion is only visible at low beta.
    """
    interface = AcceleratorMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, kinetic_energy=0.160)
    )
    try:
        assert interface.beta == pytest.approx(0.5197, abs=1e-3)

        deltap = 1e-3
        expected_pt = interface.dp2pt(deltap)
        # pt ~ beta0 * dp/p at leading order, i.e. clearly distinct from deltap.
        assert expected_pt == pytest.approx(deltap * interface.beta, rel=1e-3)

        tws = interface.run_twiss(deltap=deltap)
        np.testing.assert_array_equal(tws["pt"].to_numpy(), expected_pt)

        # Seeding the raw deltap as pt would be a genuinely different machine
        # state, not a round-off away.
        tws_raw = interface.run_twiss(pt=deltap)
        orbit_shift = np.abs(tws["x"].to_numpy() - tws_raw["x"].to_numpy()).max()
        assert orbit_shift > 1e-5, orbit_shift

        # deltap and its exact pt equivalent remain the same code path.
        tws_pt = interface.run_twiss(pt=expected_pt)
        np.testing.assert_array_equal(tws_pt["x"].to_numpy(), tws["x"].to_numpy())
    finally:
        interface.close()


def test_twiss_deltap_zero_is_the_on_momentum_machine(
    loaded_interface_with_beam: AcceleratorMadInterface,
) -> None:
    """``deltap=0`` must reproduce the on-momentum table exactly.

    Guards the zero branch of the conversion: ``gphys.dp2pt`` short-circuits at
    zero, so a seeded ``X0`` of all zeros has to be indistinguishable from
    passing no offset at all.
    """
    interface = loaded_interface_with_beam
    interface.observe("BPM")

    tws0 = interface.run_twiss()
    tws_zero = interface.run_twiss(deltap=0.0)

    assert interface.dp2pt(0.0) == 0.0
    for col in tws0.columns:
        if tws0[col].dtype.kind != "f":
            continue
        np.testing.assert_array_equal(
            tws_zero[col].to_numpy(),
            tws0[col].to_numpy(),
            err_msg=f"deltap=0 differs from on-momentum in column {col}",
        )
    interface.unobserve_elements(["BPM"])


def test_twiss_pt_kwarg_conflicts_raise(
    loaded_interface_with_beam: AcceleratorMadInterface,
) -> None:
    """pt cannot be combined with an explicit X0 or deltap."""
    interface = loaded_interface_with_beam
    with pytest.raises(ValueError, match="'pt' cannot be combined"):
        interface.run_twiss(pt=1e-3, deltap=0.0)
    with pytest.raises(ValueError, match="'pt' cannot be combined"):
        interface.run_twiss(pt=1e-3, X0=[0.0, 0.0, 0.0, 0.0, 0.0, 1e-3])


def test_install_ac_dipole_and_twiss(loaded_ac_interface_with_beam) -> None:
    """Test AC dipole installation and verify that tunes change to driven values."""
    interface = loaded_ac_interface_with_beam

    # Run initial twiss to get natural tunes
    tws = interface.run_twiss(observe=0)
    nat_qx = tws.headers["q1"] % 1
    nat_qy = tws.headers["q2"] % 1

    # Define AC dipole parameters
    nat_tunes = (nat_qx, nat_qy)
    drv_tunes = (0.27, 0.322)

    # Install AC dipole
    interface.install_ac_dipole(
        nat_tunes=nat_tunes, drv_tunes=drv_tunes
    )

    # Run twiss after AC dipole installation
    tws_ac = interface.run_twiss(observe=0)
    drv_qx = tws_ac.headers["q1"] % 1
    drv_qy = tws_ac.headers["q2"] % 1

    # Verify that tunes have changed to driven values
    tolerance = 1e-3
    assert np.isclose(drv_qx, drv_tunes[0], atol=tolerance), (
        f"Q1 not driven correctly: expected {drv_tunes[0]:.6f}, got {drv_qx:.6f}"
    )
    assert np.isclose(drv_qy, drv_tunes[1], atol=tolerance), (
        f"Q2 not driven correctly: expected {drv_tunes[1]:.6f}, got {drv_qy:.6f}"
    )


def _run_match_tunes_capture_output(seq_b1, log_level: int) -> int:
    """Run match_tunes at the given log level and return MAD stdout length."""
    ami_logger = logging.getLogger("pymadng_utils.mad.accelerator_mad_interface")
    ami_logger.setLevel(log_level)
    with tempfile.NamedTemporaryFile(mode="r", suffix=".txt", delete=False) as f:
        tmp_path = f.name
    iface = AcceleratorMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0),
        stdout=tmp_path,
    )
    try:
        iface.match_tunes(target_qx=0.28, target_qy=0.31)
    finally:
        iface.close()
    print(log_level, Path(tmp_path).read_text())
    return len(Path(tmp_path).read_text())


def test_match_tunes_verbosity_scales_with_log_level(seq_b1) -> None:
    """More verbose logging levels produce more MAD-NG output during match_tunes."""
    ami_logger = logging.getLogger("pymadng_utils.mad.accelerator_mad_interface")
    original_level = ami_logger.level
    try:
        n_warning = _run_match_tunes_capture_output(seq_b1, logging.WARNING)
        n_info = _run_match_tunes_capture_output(seq_b1, logging.INFO)
        n_debug = _run_match_tunes_capture_output(seq_b1, logging.DEBUG)
    finally:
        ami_logger.setLevel(original_level)

    assert n_debug > n_info > n_warning
