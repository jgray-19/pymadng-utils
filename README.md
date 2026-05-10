# pymadng-utils

[![codecov](https://codecov.io/gh/jgray-19/pymadng-utils/graph/badge.svg?token=L1EV8MDM6M)](https://codecov.io/gh/jgray-19/pymadng-utils)

`pymadng-utils` provides thin, workflow-oriented helpers around MAD-NG, MAD-X, and OMC3 model creation. The package is aimed at two concrete use cases:

- loading saved sequences into MAD-NG and running optics-style operations programmatically
- creating or post-processing accelerator model directories into saved sequences plus TWISS outputs

The supported accelerator paths in the current codebase are:

- `LHC`
- `PSB`
- `SPS` for MAD-X sequence export helpers only

## Package layout

- `src/pymadng_utils/accelerators`: machine descriptors used by the interfaces
- `src/pymadng_utils/mad`: MAD-NG interface classes
- `src/pymadng_utils/madx`: MAD-X sequence export and TFS conversion helpers
- `src/pymadng_utils/model_creator`: higher-level model creation workflows
- `src/pymadng_utils/io`: knob-file helpers
- `tests`: end-to-end and unit coverage

## Installation

For development:

```bash
pip install -e .[test]
```

If you want to build the Sphinx docs locally:

```bash
pip install -e .[test]
pip install sphinx sphinx-rtd-theme
```

The package expects the underlying accelerator toolchain to be available in the environment you run it in, notably `pymadng`, `cpymad`, `tfs`, and `omc3` for the model-creation workflows.

## Main concepts

### Accelerators

Machine-specific details live in accelerator descriptors such as `LHC` and `PSB`. They provide:

- the saved sequence filename and MAD sequence name
- beam or ring metadata
- tune knob names and integer tunes
- BPM patterns and monitor-plane helpers
- optional AC-dipole installation metadata

### MAD-NG interfaces

The `pymadng_utils.mad` package contains the runtime interfaces:

- `AcceleratorMadInterface` for loading a sequence, setting up the beam, observing elements, running TWISS, changing variables, and applying perturbations
- `AcceleratorErrorsMadInterface` for workflows that want accelerator-specific startup errors applied automatically
- `KnobMadInterface` for knob and corrector-file handling
- `ModelCreatorMadInterface` for model-export workflows

### MAD-X sequence export

`pymadng_utils.madx.make_sequence.make_madx_sequence()` converts an OMC3-created model directory into a saved MAD-X sequence that can be loaded again in MAD-NG.

The function now expects a real nominal OMC3 model directory containing `job.create_model_nominal.madx`. It intentionally fails fast for layouts it cannot identify unambiguously.

### Model creation workflow

The higher-level workflow is:

1. create a nominal model directory with OMC3
2. export a saved MAD-X sequence from that model directory
3. reopen the saved sequence in MAD-NG
4. match or verify tunes
5. export `twiss.dat`, `twiss_ac.dat`, and `twiss_elements.dat`

For PSB, the workflow also supports driven models with explicit `drv_tunes` plus `driven_excitation="acd"`.

## Minimal examples

### Load a saved sequence in MAD-NG

```python
from pathlib import Path

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface

sequence = Path("lhcb1_saved.seq")
accelerator = LHC(sequence_file=sequence, beam=1, kinetic_energy=6800.0)

with AcceleratorMadInterface(accelerator=accelerator) as interface:
    interface.observe("IP.")
    twiss = interface.run_twiss(coupling=True)
    print(twiss.q1, twiss.q2)
```

### Update an existing model directory with MAD-NG

```python
from pathlib import Path

from pymadng_utils.accelerators import PSB
from pymadng_utils.madx.make_sequence import make_madx_sequence
from pymadng_utils.model_creator.madng_utils import update_model_with_madng

model_dir = Path("path/to/psb_model")
sequence_file = make_madx_sequence(model_dir)

update_model_with_madng(
    accelerator=PSB(sequence_file=sequence_file, ring=3),
    model_dir=model_dir,
    tunes=[0.17, 0.225],
    drv_tunes=[0.162, 0.232],
)
```

## Documentation

The Sphinx docs live in `docs/`.

Build them locally with:

```bash
make -C docs html
```

The entry point is `docs/index.rst`, and the API reference is generated from the package modules.
