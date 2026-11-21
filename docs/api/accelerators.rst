Accelerators
============

``pymadng_utils.accelerators`` contains the machine descriptors consumed by the MAD-facing interfaces.

Overview
--------

* ``Accelerator`` defines the minimum contract needed by MAD helpers: sequence file, sequence name, beam parameters, BPM pattern, and tune metadata.
* ``LHC`` and ``PSB`` provide concrete machine descriptors used by the current tests and model-creation workflows.
* Accelerators can optionally expose perturbation-family metadata and startup-error hooks for interfaces that support those workflows.

Package exports
---------------

``Accelerator``, ``LHC``, and ``PSB`` are re-exported here from the submodules below,
which hold their canonical documentation.

.. automodule:: pymadng_utils.accelerators
   :no-index:

Base descriptor
---------------

.. automodule:: pymadng_utils.accelerators.base
   :members:
   :undoc-members:
   :show-inheritance:

LHC descriptor
--------------

.. automodule:: pymadng_utils.accelerators.lhc
   :members:
   :undoc-members:
   :show-inheritance:

PSB descriptor
--------------

.. automodule:: pymadng_utils.accelerators.psb
   :members:
   :undoc-members:
   :show-inheritance:
