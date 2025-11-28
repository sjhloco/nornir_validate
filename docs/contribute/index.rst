Contribute
==========

*Pull Requests* are welcomed for new validations, the worth of this tool is dependent on its validations. As part of the Github workflow the following actions (checks) are performed on submitted PRs:

- Formatting and linting: ``ruff format`` and ``ruff check``
- Typing: ``mypy .``
- Regenerate all test files: ``python re_build_test_files.py``
- Unit testing: ``pytest -vv``

Feature Layout
--------------

Each **feature** (`feature_templates <https://github.com/sjhloco/nornir_validate/tree/main/feature_templates>`_) consists of one or more **sub-features** with the directory structured as follows:

.. code-block:: bash

    feature_templates/
    ├── intf_bonded/
    │   ├── intf_bonded_desired_state.j2     # Generates the desired state data model including the commands for validation and auto-generating validation file
    │   └── intf_bonded_actual_state.py      # Formats the command output into the actual state data model (also used to generate validation files)

OS-Specific Testing Layout
--------------------------

Each platform (``os_type``) must have a corresponding unit test directory (`tests/os_test_files/ <https://github.com/sjhloco/nornir_validate/tree/main/tests/os_test_files>`_) and *sub-feature index*, the directory structure is as follows:

.. code-block:: bash

    tests/os_test_files/
    ├── cisco_asa/
    │   ├── intf_bonded/
    │   │   ├── cisco_asa_intf_bonded_validate.yml        # Validation criteria, what is being validated
    │   │   ├── cisco_asa_intf_bonded_desired_state.yml   # Desired state generated from xx_validate.yml
    │   │   ├── cisco_asa_intf_bonded_commands.yml        # Commands used by index to auto-generate validation file
    │   │   ├── cisco_asa_intf_bonded_cmd_output.json     # CLI output from xx_commands.yml
    │   │   ├── cisco_asa_intf_bonded_actual_state.yml    # Actual state generated from xx_cmd_output.json
    │   └── subfeature_index.yml                          # Index of sub-feature validations for this os_type
 

Creating a Validation
---------------------

To be able to develop a new validation you need to answer these questions:

- Is it a *new feature*, *new sub-feature* or a *new os_type of an existing* `sub-feature <http://127.0.0.1:5500/_build/html/validations.html>`_?
- What are the names of the *os_type*, *feature* and *sub-feature*?
- What commands need to be run to gather the validation data (will become the *actual state*)?
- How will the data model be structured to define what is to be validated (the *desired state*)?

The following steps take you through the different tasks that are required, the **feature_builder.py** script will assist with the majority of these.

* :doc:`Feature structure <structure>` - Create the feature directory structure and index of sub-features
* :doc:`New OS for existing sub-feature <newos_exist_subfeat>` - Steps to add a new OS type to an existing sub-feature
* :doc:`New feature/sub-feature <new_sudfeature>` - Steps to create a new feature and/or sub-feature
* :doc:`Formatting, linting, testing and documentation <test_lint_doc>` - The boring stuff required to submit a PR
* :doc:`Unittest appendix <test_appendix>` - More details on unit testing

.. toctree::
    :hidden:
    :maxdepth: 1
    
    structure
    newos_exist_subfeat
    new_sudfeature
    test_lint_doc
    test_appendix