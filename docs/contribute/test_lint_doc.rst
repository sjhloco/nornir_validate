Testing, linting and documentation
==================================

Before submitting a PR the following tasks need to be completed. 

- Ruf, MyPy and unit tests MUST all pass
- Documentation MUST be updated
- New validations ADDED to the examples

Unittest
--------

Before doing the unit testing re-run the test file builds (*ds, as, vf*), unless a breaking change has been made to a sub-feature you shouldn't really be seeing any changes to these existing files.

.. code-block:: bash

    python scripts/rebuild_test_files.py

Run unit tests for nr_val and all its features/sub-features.

.. code-block:: bash

    pytest -v

Linting, formatting and typing
------------------------------

The project uses `Ruff <https://ruff.rs/>`_ for linting and formatting and `MyPy <https://mypy-lang.org>`_ for static type checking.

- The Ruff Linter is an extremely fast Python linter designed as a drop-in replacement for *Flake8, isort, pydocstyle, pyupgrade, autoflake*, and more.
- The Ruff Formatter is a code formatter for Python that focuses on speed and correctness, similar to *black* but with a different design philosophy.

.. code-block:: bash

    ruff format --check .
    ruff check .
    mypy .

Documentation
-------------

Make the following changes to the RTD documentation:

- Update the **current validations** table (link to `validations.rst <https://github.com/sjhloco/nornir-validate/blob/main/docs/validations.rst>`_)
- If you feel the validation is requires more details (unusual to need it) also add an entry in the **Validation-specific details** section

Examples
--------

New feature/sub-features need adding to the `example_validation_files <https://github.com/sjhloco/nornir-validate/tree/main/example_validation_files>`_. Add the sub-feature validation example (can get from test files) to the os_specific *xx_validations.yml* file, if it is a new sub-feature it will also need adding to *all_validations.yml*
