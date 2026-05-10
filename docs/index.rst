pymadng-utils documentation
===========================

``pymadng-utils`` provides utility code around MAD-NG, MAD-X, and model-generation workflows. It is designed for accelerator workflows that need a small Python layer over saved sequences, OMC3 model directories, and exported TWISS data.

The package is split into a few focused areas:

* ``pymadng_utils.accelerators`` for machine descriptors that define sequence names, beam settings, tune knobs, and optional perturbation/error metadata.
* ``pymadng_utils.mad`` for reusable MAD-NG interface classes.
* ``pymadng_utils.madx`` for MAD-X sequence export and TFS conversion helpers.
* ``pymadng_utils.io`` for lightweight knob file I/O.
* ``pymadng_utils.model_creator`` for OMC3 model creation workflows.

The supported code paths covered by the repository today are:

* LHC model creation and saved-sequence workflows
* PSB model creation, including explicit driven AC-dipole configurations
* SPS support in the sequence-export helper layer

Start with the usage guide if you want the workflow-level picture. Use the API reference when you already know which module you need.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   usage
   api/index
