New OS for existing sub-feature
===============================

This is the simplest form of collaboration as the majority of the structure is already in place. As long as the structured data of the command output follows the same pattern as other OS types for that sub-feature then it is just a simple case of adding the new os_type command (*xx_desired_state.j2*) and dictionary keys (*xx_actual_state.py*). If the structured data is different you will also need to update the actual state formatting function to handle these differences.

The below steps run through an example to add **paloalto_panos** support to the existing sub-feature **route_table.route_count**. The test directory has already been created and index updated as per :doc:`feature structure <structure>` (``python feature_builder.py -cf paloalto_panos route_table.route_count``)

1. Validation commands (-cmd)
-----------------------------

As this is an existing sub-feature the data structure of what you are validating is already defined, all you need to do is add the validation command to the os_type conditional statements at the top of the desired_state jinja template (*route_table_desired_state.j2*).

.. code-block:: jinja

    {% elif 'panos' in os_type |string %}
    {% set route_count_cmd = "show routing resource" %}

Use ``-cmd`` (*--create_commands*) to create (render) the **xx_commands.yml** file and then unit test it. 

.. code-block:: bash

    python feature_builder.py -cmd <os_type> <feature>
    pytest 'tests/test_validations.py::TestCommands::test_command_templating[<ostype>_<feature>]' -vv

    ❯ python feature_builder.py -cmd paloalto_panos route_table
    ❯ pytest 'tests/test_validations.py::TestCommands::test_command_templating[paloalto_panos_route_table]' -vv

2. Command Output (-di) 
-----------------------

The command output can be a parsed `ntc-template <https://github.com/networktocode/ntc-templates/tree/master/ntc_templates/templates>`_ data model (lists of dictionaries) or the screen scraped raw output (lists of strings). Use ``-di`` (*--discovery*) to create the **xx_cmd_output.json** file from a live device (prompted for username/password or env var *DVC_USER/DVC_PWORD*) or a local file of the raw output. 

.. code-block:: bash

    python feature_builder.py -di <netmiko_ostype> <feature.subfeature> <ip address or filename>

    ❯ python feature_builder.py -di paloalto_panos route_table.route_count route_count_output.raw

.. note::

    If there are multiple commands used for a sub-feature ``-di`` will only create the structured data for the first command, the others will have to be added to the list manually.


3. Actual State (-as) and Validation file (-vf)
-----------------------------------------------

The actual state and validation file use the same Python function (*format_xx*) as most of the time they are identical. The exception to this is for things that should always be implicitly in a certain state, such as interfaces being *up*. These are conditionally omitted from the validation file as they are explicitly defined in the desired state jinja template.

Add the conditional *os_type* key names under *_set_keys*, in this example the *route_table.route* sub-feature is not used so the last 4 elements are left blank.

.. code-block:: python

    class OsKeys(NamedTuple):
        count_match: str
        count_iter: int
        route_mask: str
        route_nhip: str
        route_nhif: str
        route_type: str

    def _set_keys(os_type: str) -> OsKeys:
        if "ios" in os_type:
            return OsKeys("IP", 2, "prefix_length", "nexthop_ip", "nexthop_if", "protocol")
        .......
        elif "panos" in os_type:
            return OsKeys("IPv6", 3, "", "", "", "")

Dependent on the structure of the returned device data you may need to edit the *format_xx* method, in this case it was needed due to a different way of handling VRFs.

.. code-block:: python

    def format_rte_count(key: OsKeys, os_type: str, output: list[str]) -> dict[str, Any]:
        result: dict[str, int | str] = {}
        for idx, each_item in enumerate(output):
            if key.count_match in each_item:
                # Needed for Panos as no VRFs
                if bool(re.search("panos", os_type)):
                    vrf = "global"
                else:
                    tmp = each_item.replace("maximum-paths is", "name is default")
                    vrf = tmp.split()[5].replace('"', "").replace("default", "global")
                result[vrf] = _make_int(output[idx + 1].split()[key.count_iter])
        return dict(result)

Use ``-as`` (*--format_actual_state*) to create the **xx_actual_state.yml** test file, ``-vf`` (*--create_val_file*) to create the **xx_validate.yml** file and unit test them both.

.. code-block:: bash

    python feature_builder.py -as <os_type> <feature> 
    pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[ostype_newfeature]' -vv
    python feature_builder.py -vf <os_type> <feature> 
    pytest 'tests/test_validations.py::TestValFile::test_create_validation_file[ostype_newfeature]' -vv

    ❯ python feature_builder.py -as paloalto_panos route_table
    ❯ pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[paloalto_panos_route_table]' -vv
    ❯ python feature_builder.py -vf paloalto_panos route_table
    ❯ pytest 'tests/test_validations.py::TestValFile::test_create_validation_file[paloalto_panos_route_table]' -vv

.. note::

    If editing the actual state be aware that it has the potential to break the the actual_state for other OSs, this is tested as part of final unit tests before submitting the PR

4. Desired State (-ds) 
----------------------

The validation file defines what *"correct"* looks like for each sub-feature, how the sub-feature is judged to be compliant. Therefore, it is this file that is used to create (render) the desired state. Use ``-ds`` (*--create_desired_state*) to render the data from the validation file (*xx_validate.yml*) to create the **xx_desired_state.j2** file and then unit test it.

.. code-block:: bash

    python feature_builder.py -ds <os_type> <feature> 
    pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[ostype_newfeature]' -vv

    ❯ python feature_builder.py -ds paloalto_panos route_table
    ❯ pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[paloalto_panos_route_table]' -vv

5. Compliance Report 
--------------------

The final thing to do is test that the *"desired_state.yml"* and *"actual_state.yml"* files match by unit testing the compliance report. 

.. code-block:: bash

    pytest 'tests/test_validations.py::TestComplianceReport::test_report_passes[ostype_newfeature]' -vv

    ❯ pytest 'tests/test_validations.py::TestComplianceReport::test_report_passes[paloalto_panos_route_table]' -vv
