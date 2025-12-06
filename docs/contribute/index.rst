Contribute
==========

*Pull Requests* are welcomed for new validations as the worth of this tool is dependent on its validations. As part of the Github workflow the following actions (checks) are performed on submitted PRs:

- Formatting and linting: ``ruff format --check .`` and ``ruff check .``
- Typing: ``mypy .``
- Unit testing: ``pytest -v``

Feature Layout
--------------

Each **feature** (`feature_templates <https://github.com/sjhloco/nornir-validate/tree/main/src/nornir_validate/feature_templates>`_) consists of one or more **sub-features** with the directory structured as follows:

.. code-block:: bash

    feature_templates/
    ├── intf_bonded/
    │   ├── intf_bonded_desired_state.j2     # Generates the desired state data model including the commands for validation and auto-generating validation file
    │   └── intf_bonded_actual_state.py      # Formats the command output into the actual state data model (also used to generate validation files)

A list of all features/sub-features are stored as `index_files <https://github.com/sjhloco/nornir-validate/tree/main/src/nornir_validate/index_files>`_ and used for auto-generation of validation files and unit testing.

OS-Specific Testing Layout
--------------------------

Each platform (``os_type``) must have a corresponding unit test directory (`tests/os_test_files/ <https://github.com/sjhloco/nornir-validate/tree/main/tests/os_test_files>`_), the directory structure is as follows:

.. code-block:: bash

    tests/os_test_files/
    ├── cisco_asa/
    │   ├── intf_bonded/
    │   │   ├── cisco_asa_intf_bonded_validate.yml        # Validation criteria, what is being validated
    │   │   ├── cisco_asa_intf_bonded_desired_state.yml   # Desired state generated from xx_validate.yml
    │   │   ├── cisco_asa_intf_bonded_commands.yml        # Commands used by index to auto-generate validation file
    │   │   ├── cisco_asa_intf_bonded_cmd_output.json     # CLI output from xx_commands.yml
    │   │   ├── cisco_asa_intf_bonded_actual_state.yml    # Actual state generated from xx_cmd_output.json

Creating a Validation
---------------------

To be able to develop a new validation you need to answer these questions:

- Is it a *new feature*, *new sub-feature* or a *new os_type of an existing* `sub-feature <https://nornir-validate.readthedocs.io/en/latest/validations.html>`_?
- What are the names of the *os_type*, *feature* and *sub-feature*?
- What commands need to be run to gather the validation data (will become the *actual state*)?
- How will the data model be structured to define what is to be validated (the *desired state*)?

The following steps take you through the different tasks that are required, the **feature_builder.py** script will assist with the majority of these.

* :doc:`Formatting, linting, testing, documentation and PR <fmt_lint_test_doc_pr>` - The boring stuff required to submit a PR
* :doc:`Feature structure <structure>` - Create the feature directory structure and index of sub-features
* :doc:`New OS for existing sub-feature <newos_exist_subfeat>` - Steps to add a new OS type to an existing sub-feature
* :doc:`New feature/sub-feature <new_sudfeature>` - Steps to create a new feature and/or sub-feature
* :doc:`Unittest appendix <test_appendix>` - More details on unit testing

.. toctree::
    :hidden:
    :maxdepth: 1
    
    fmt_lint_test_doc_pr
    structure
    newos_exist_subfeat
    new_sudfeature
    test_appendix
