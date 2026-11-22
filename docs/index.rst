pymadng-utils
==============

``pymadng-utils`` connects saved MAD-X sequences, MAD-NG sessions, and OMC3 model directories. It supplies LHC, PSB and FCC-ee machine descriptors, reusable MAD-NG operations, sequence export, TFS conversion, and model-table generation.

The :doc:`usage` page explains the supported workflows and their file contracts. The :doc:`api/index` pages document the Python objects directly from their source docstrings.

Scope
-----

* Runtime MAD-NG descriptors and interfaces: LHC, PSB and FCC-ee.
* OMC3 model-directory sequence export: LHC and PSB.
* Packaged end-to-end model creation: LHC (``create_lhc_model``), PSB (``create_psb_model``) and FCC-ee lattice preparation (``create_fcc_model``).

Python 3.11 or newer is required. Model creation and sequence export (``pymadng_utils.madx.make_sequence`` and ``pymadng_utils.model_creator.create_models``) require the optional ``model`` dependencies and working MAD-X/OMC3 installations; everything else needs only the core install.

The package is alpha (0.0.2): the API may change without notice.

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   usage
   api/index
