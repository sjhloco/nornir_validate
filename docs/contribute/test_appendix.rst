Unittest Appendix
=================

There are 5 sets of unit tests grouped under their own class to allow for running for individual os_type feature or all os_type and features. *test_validations.py* uses the index files to dynamically build the tests to simplify things so that the test files do NOT need updating when new sub-features are added.

**test_command_templating:** Renders *"subfeature_index.yml"* with *"xx_desired_state.j2"* and compares result against the file *"xx_commands.yml"*

.. code-block:: bash

    pytest 'tests/test_validations.py::TestCommands::test_command_templating[<os_type>_<feature>]' -vv
    pytest 'tests/test_validations.py::TestCommands' -vv

**test_create_validation:** Formats *"xx_cmd_output.json"* with *"xx_actual_state.generate_val_file"* and compares result against the file *"xx_validate.yml"*

.. code-block:: bash

    pytest 'tests/test_validations.py::TestValFile::test_create_validation_file[<os_type>_<feature>]' -vv
    pytest 'tests/test_validations.py::TestValFile' -vv

**test_desired_state_templating:** Renders *"xx_validate.yml"* with *"xx_desired_state.j2"* and compares result against the file *"xx_desired_state.yml"*

.. code-block:: bash

    pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[<os_type>_<feature>]' -vv
    pytest 'tests/test_validations.py::TestDesiredState' -vv

**test_actual_state_formatting:** Formats *"xx_cmd_output.json"* with *"xx_actual_state.format_actual_state"* and compares result against the file *"xx_actual_state.yml"*

.. code-block:: bash

    pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[<os_type>_<feature>]' -vv
    pytest 'tests/test_validations.py::TestActualState' -vv

**test_report_passes:** Validates a compliance report comparing the files *"xx_desired_state.yml"* and *"xx_actual_state.yml"* passes

.. code-block:: bash

    pytest 'tests/test_validations.py::TestComplianceReport::test_report_passes[<os_type>_<feature>]' -vv
    pytest 'tests/test_validations.py::TestComplianceReport' -vv

**test_all:** Run all validations, so all classes.

.. code-block:: bash

    pytest tests/test_validations.py -vv
