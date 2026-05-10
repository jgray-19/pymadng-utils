Usage Guide
===========

``pymadng-utils`` is intentionally small. Most real workflows fall into one of two categories:

- load an existing saved sequence into MAD-NG and manipulate it from Python
- start from an OMC3 model directory and turn it into saved sequences plus MAD-NG-exported TWISS files

Supported workflows
-------------------

The current repository actively covers:

- LHC model creation and MAD-NG reload workflows
- PSB model creation, including explicit driven AC-dipole configurations
- SPS sequence export support through the MAD-X helper layer

The code is deliberately stricter than earlier versions. In particular, sequence export expects a real nominal OMC3 model directory and fails fast when the job file does not unambiguously describe the accelerator and sequence.

MAD-NG session workflow
-----------------------

The base runtime workflow is:

1. instantiate an accelerator descriptor
2. create an ``AcceleratorMadInterface`` or one of its specialisations
3. load or initialise the sequence
4. run observations, TWISS, matching, perturbations, or knob application

Example:

.. code-block:: python

   from pathlib import Path

   from pymadng_utils.accelerators import LHC
   from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface

   accelerator = LHC(
       sequence_file=Path("lhcb1_saved.seq"),
       beam=1,
       kinetic_energy=6800.0,
   )

   with AcceleratorMadInterface(accelerator=accelerator) as interface:
       interface.observe("IP.")
       twiss = interface.run_twiss(coupling=True)
       print(twiss.q1, twiss.q2)

Model-directory workflow
------------------------

For model creation or post-processing, the package layers MAD-X and MAD-NG work:

1. create a nominal model directory with OMC3
2. export a saved MAD-X sequence using ``make_madx_sequence()``
3. re-open that sequence in MAD-NG with the machine descriptor
4. export ``twiss.dat``, ``twiss_ac.dat``, and ``twiss_elements.dat``

Example:

.. code-block:: python

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

Saved sequence expectations
---------------------------

``make_madx_sequence()`` expects an OMC3-created model directory with ``job.create_model_nominal.madx`` present.

For the supported workflows:

- LHC beam inference comes from an explicit ``use, sequence=lhcb1;`` or ``use, sequence=lhcb2;`` statement
- PSB ring inference comes from an explicit ``use, sequence=psbN;`` statement
- unsupported or ambiguous layouts raise an error instead of falling back to directory-name guesses

This is intentional: the helper is meant to be predictable for committed test fixtures and real model directories, not permissive for ad hoc layouts.
