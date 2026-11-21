# pymadng-utils

[![codecov](https://codecov.io/gh/jgray-19/pymadng-utils/graph/badge.svg?token=L1EV8MDM6M)](https://codecov.io/gh/jgray-19/pymadng-utils)
[![Coverage](https://github.com/jgray-19/pymadng-utils/actions/workflows/coverage.yml/badge.svg)](https://github.com/jgray-19/pymadng-utils/actions/workflows/coverage.yml)

> **Alpha (0.0.1).** The API may change without notice.

`pymadng-utils` is a small Python library for accelerator-model workflows that cross the MAD-X/MAD-NG boundary. It provides:

- LHC, PSB and FCC-ee machine descriptors;
- a managed MAD-NG session that loads a saved MAD-X sequence and configures its beam;
- observation, TWISS, tune matching, AC-dipole, AC-kicker, orbit-correction, magnet-strength, and perturbation helpers;
- conversion of MAD-NG TFS tables to MAD-X/OMC3 naming conventions;
- export of reusable sequences from existing OMC3 model directories; and
- end-to-end LHC and PSB model-creation workflows and FCC-ee lattice preparation.

The package is workflow infrastructure, not a replacement for MAD-NG, MAD-X, or OMC3. Most operations require a working accelerator software environment and real sequence/model files.

## Installation

Python 3.11 or newer is required.

Install the core package:

```bash
python -m pip install .
```

Install an editable checkout with the dependencies used by model creation and tests:

```bash
python -m pip install -e '.[test]'
```

The extras are:

| Extra | Adds | Intended use |
|---|---|---|
| `model` | `cpymad`, `omc3` | sequence export and model creation |
| `test` | `pytest`, `pytest-cov`, `cpymad`, `omc3` | repository test suite |
| `dev` | `pre-commit`, `ruff` | linting and pre-commit hooks |
| `docs` | Sphinx and the Furo theme | local documentation build |

MAD-NG itself must be usable by `pymadng`; `cpymad` additionally needs a working MAD-X installation. OMC3 model creation may also require access to CERN accelerator-model repositories, depending on its `fetch` configuration.

## Quick start: load a sequence and run TWISS

An accelerator descriptor holds the machine-specific contract: sequence name, particle and kinetic energy, BPM selection pattern, tune knobs, integer tunes, and AC-dipole element name. Constructing `AcceleratorMadInterface` immediately starts MAD-NG, loads the sequence, and attaches the beam.

```python
from pathlib import Path

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad import AcceleratorMadInterface

accelerator = LHC(
    beam=1,
    sequence_file=Path("lhcb1_saved.seq"),
    kinetic_energy=6800.0,  # GeV; this is kinetic, not total energy
)

with AcceleratorMadInterface(accelerator) as interface:
    interface.observe()  # uses the LHC BPM pattern
    twiss = interface.run_twiss(coupling=True)
    print(twiss.headers["q1"], twiss.headers["q2"])
```

`run_twiss()` returns the `pymadng` table converted to a DataFrame, indexed by element name when the result contains a `name` column. Its headers are augmented with `particle` and total `energy` in GeV.

Use the interface as a context manager, or call `close()` explicitly. The MAD-X sequence is translated on every load; `load_sequence(cache_translation=True)` writes a sibling `.mad` cache, which makes that directory writable-required and is unsafe for parallel loaders of the same sequence.

### Off-momentum coordinates

MAD-NG uses `pt`, while many accelerator workflows use relative momentum deviation `dp/p`. The descriptor and interface both expose beam-aware conversions:

```python
with AcceleratorMadInterface(accelerator) as interface:
    pt = interface.dp2pt(1e-3)
    twiss = interface.run_twiss(pt=pt, coupling=True)
```

The convenience `pt=` argument is mutually exclusive with explicit `X0=` and `deltap=` arguments. A `deltap=` argument (without an explicit `X0=`) is normalised through the same path: it is converted to `pt` and seeded as the sixth `X0` coordinate, so `run_twiss(deltap=dp)`, `run_twiss(pt=interface.dp2pt(dp))`, and MAD-NG's own `twiss{deltap=dp}` are all bit-identical.

`interface.dp2pt`/`interface.pt2dp` run `MAD.gphys.dp2pt`/`pt2dp` inside MAD-NG on the loaded sequence's `beam.beta`, with the value sent and received over the pipe as a double, so nothing is lost to string formatting or to a second implementation of the same formula. Note these are not mutual inverses to the last bit (~1e-13 relative), and the closed-orbit search amplifies that to ~1e-9 on the orbit over a full ring, so convert once and stay in one coordinate rather than round-tripping. Standalone conversion functions are available from `pymadng_utils.physics` when the reference `beta` is already known and no MAD-NG session is at hand.

## What else is here

The [usage guide](https://github.com/jgray-19/pymadng-utils/blob/main/docs/usage.rst) documents the rest in full: the LHC and PSB
descriptors, the four MAD-NG interface classes and their operations, saved-sequence
export from an OMC3 model directory (LHC, PSB, SPS), model-table regeneration, the
packaged end-to-end LHC creator, and the TFS/knob conversion helpers. The
[API reference](https://github.com/jgray-19/pymadng-utils/blob/main/docs/api/index.rst) documents each object from its docstrings.

## Development

Install the git hooks once with `pre-commit install` (ruff, whitespace checks, and a commit-message check).

Run the test suite:

```bash
pytest
```

Some tests start MAD-NG or MAD-X and use committed accelerator fixtures; they are integration tests, not pure unit tests.

Build the Sphinx documentation:

```bash
python -m pip install -e '.[docs]'
make -C docs html
```

The generated site starts at `docs/_build/html/index.html`.

## Repository layout

```text
src/pymadng_utils/
├── accelerators/   LHC/PSB/FCC-ee descriptors
├── io/             knob-file I/O
├── mad/            MAD-NG session interfaces
├── mad_scripts/    packaged MAD-NG scripts (output suppression, tune matching)
├── madx/           sequence export and TFS conversion
├── model_creator/  higher-level model workflows
└── physics.py      particle masses and dp/p ↔ pt conversion
```

The project is distributed under the terms in [`LICENSE`](https://github.com/jgray-19/pymadng-utils/blob/main/LICENSE).
