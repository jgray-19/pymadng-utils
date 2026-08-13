"""
Tests for the shush()/unshush() MAD-NG output muting helpers.

The helpers (loaded from ``shush_mad_output.mad`` during interface init) redirect
the MAD-NG process stdout/stderr to ``/dev/null`` at the file-descriptor level and
restore them again. These tests drive real MAD-NG snippets and inspect the
captured process output, since fd-level muting cannot be observed any other way.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface

BEFORE = "SHUSH_VISIBLE_BEFORE"
MUTED = "SHUSH_MUTED_LINE"
AFTER = "SHUSH_VISIBLE_AFTER"


def _capture_mad_output(
    seq_b1: Path, drive: Callable[[AcceleratorMadInterface], None]
) -> str:
    """Run *drive* against an interface whose MAD process stdout goes to a file.

    Returns the full captured MAD-NG output text after the interface is closed.
    """
    with tempfile.NamedTemporaryFile(mode="r", suffix=".txt", delete=False) as handle:
        log_path = handle.name
    iface = AcceleratorMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0),
        stdout=log_path,
    )
    try:
        drive(iface)
    finally:
        iface.close()
    return Path(log_path).read_text()


def test_shush_mutes_then_restores_fd_output(seq_b1: Path) -> None:
    """Output between shush()/unshush() is dropped; output either side survives."""

    def drive(iface: AcceleratorMadInterface) -> None:
        iface.mad.send(f'io.write("{BEFORE}\\n")')
        iface.mad.send("shush()")
        iface.mad.send(f'io.write("{MUTED}\\n")')
        iface.mad.send("unshush()")
        iface.mad.send(f'io.write("{AFTER}\\n")')

    out = _capture_mad_output(seq_b1, drive)
    assert BEFORE in out
    assert MUTED not in out  # muted at the fd level -> went to /dev/null
    assert AFTER in out  # fd restored after unshush()


def test_shush_and_unshush_are_idempotent(seq_b1: Path) -> None:
    """Double shush()/unshush() is harmless and restore still works.

    A single on/off muting state means a stray extra call in either direction is
    a no-op, so a missed unshush() cannot leave output stuck at /dev/null.
    """

    def drive(iface: AcceleratorMadInterface) -> None:
        iface.mad.send("shush()")
        iface.mad.send("shush()")  # already muted -> no-op
        iface.mad.send(f'io.write("{MUTED}\\n")')
        iface.mad.send("unshush()")
        iface.mad.send("unshush()")  # not muted -> no-op
        iface.mad.send(f'io.write("{AFTER}\\n")')

    out = _capture_mad_output(seq_b1, drive)
    assert MUTED not in out
    assert AFTER in out


def test_unshush_without_shush_is_noop(seq_b1: Path) -> None:
    """Calling unshush() when never muted leaves output flowing normally."""

    def drive(iface: AcceleratorMadInterface) -> None:
        iface.mad.send("unshush()")  # never shushed
        iface.mad.send(f'io.write("{AFTER}\\n")')

    assert AFTER in _capture_mad_output(seq_b1, drive)


def test_data_pipe_survives_shush(seq_b1: Path) -> None:
    """The pymadng data channel keeps working while output is muted."""
    iface = AcceleratorMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0)
    )
    try:
        iface.mad.send("shush()")
        iface.mad.send(f"{iface.py_name}:send(1 + 2)")
        assert iface.mad.recv() == 3
        iface.mad.send("unshush()")
        iface.mad.send(f"{iface.py_name}:send(4 + 5)")
        assert iface.mad.recv() == 9
    finally:
        iface.close()
