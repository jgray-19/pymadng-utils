pymadng-utils documentation
===========================

``pymadng-utils`` provides utility code around MAD-NG, MAD-X, and model-generation workflows. The package is split into a few focused areas:

* ``pymadng_utils.accelerators`` for machine descriptors that define sequence names, beam settings, tune knobs, and optional perturbation/error metadata.
* ``pymadng_utils.mad`` for reusable MAD-NG interface classes.
* ``pymadng_utils.madx`` for MAD-X sequence export and TFS conversion helpers.
* ``pymadng_utils.io`` for lightweight knob file I/O.
* ``pymadng_utils.model_creator`` for OMC3 model creation workflows.

The API reference below is generated from the codebase and intended to document both the reusable interfaces and the higher-level workflow entry points.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   api/index
