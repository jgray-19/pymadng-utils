pymadng-utils
==============

``pymadng-utils`` connects saved MAD-X sequences, MAD-NG sessions, and OMC3 model directories. It supplies LHC and PSB machine descriptors, reusable MAD-NG operations, sequence export, TFS conversion, and model-table generation.

The :doc:`usage` page explains the supported workflows and their file contracts. The :doc:`api/index` pages document the Python objects directly from their source docstrings.

Scope
-----

* Runtime MAD-NG descriptors and interfaces: LHC and PSB.
* OMC3 model-directory sequence export: LHC, PSB, and SPS.
* Packaged end-to-end model creation: LHC.

Python 3.11 or newer is required. Model creation and sequence export require the optional ``model`` dependencies and working MAD-X/OMC3 installations.

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   usage
   api/index
