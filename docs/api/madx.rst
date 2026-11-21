MAD-X Utilities
===============

``pymadng_utils.madx`` groups the helpers that interact with MAD-X directly or post-process MAD-NG outputs into MAD-X-style TFS files.

The main entry point in this package area is ``make_madx_sequence()``, which exports a saved sequence from an OMC3 model directory. The function is intentionally strict:

* it expects ``job.create_model_nominal.madx`` to exist
* it requires explicit sequence selection statements in that job file
* it raises on unsupported or ambiguous layouts instead of silently guessing

That behaviour is deliberate and matches the committed test fixtures and supported workflows in this repository.

Package exports
---------------

.. automodule:: pymadng_utils.madx
   :members:
   :undoc-members:
   :show-inheritance:

Sequence export
---------------

.. automodule:: pymadng_utils.madx.make_sequence
   :members:
   :undoc-members:
   :show-inheritance:

TFS conversion
--------------

.. automodule:: pymadng_utils.madx.tfs_utils
   :members:
   :undoc-members:
   :show-inheritance:
