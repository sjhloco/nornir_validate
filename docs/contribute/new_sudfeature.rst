New feature/sub-feature
=======================

The method for creating a new feature and sub-feature or just a new sub-feature within an existing feature is very much the same, you need to define what you are validating (*validation file*) and format the returned command output into the correct structure (*actual state*). The easiest way to do this is to work backwards by first deciding how the *actual state* looks (based on *command outputs*) before creating the validation file of what is to be validated (used to create the *desired state*). 

The below steps run through an example to add a new **cisco_viptela omp_peer** sub-feature within a new **sdwan** feature. The feature directory, base feature state files and test directory have already been created and sub-feature index updated as per :doc:`feature structure <structure>` (``uv run scripts/feature_builder.py -cf cisco_viptela sdwan.omp_peer``).

1. Commands (-cmd)
------------------

The feature specific **xx_desired_state.j2** file holds the commands that will gather the validation data for each sub-feature, the logic being *"match on a sub-feature, define the command to run"*. Add a dictionary entry for the new sub-feature (**<sub-feature>_cmd: <command>**) as well as the conditional statement logic for the sub-feature.

.. code-block:: jinja

    {# ####### CMD: Set command variables on a per-os_type basis ####### #}
    {% if 'ios' in os_type |string %}
    {% elif 'nxos' in os_type |string %}
    {% elif 'asa' in os_type |string %}
    {% elif 'wlc' in os_type |string %}
    {% elif 'panos' in os_type |string %}
    {% elif 'viptela' in os_type |string %}
    {% set omp_peer_cmd = "show omp peers" %}
    {% endif %}

    {# ### OMP_PEER: {cmd: {peer: {site_id:x, routes_received:x, routes_installed:x:, routes_sent:x, state:up}} ### #}
    {% if sub_feat == 'omp_peer' and omp_peer_cmd is defined %}
        omp_peer:
        {{ omp_peer_cmd }}:
    {% if generate_val_file %}
            VALIDATE
    {% endif %}

The formatting I am looking to achieve for this example is:

.. code-block:: yaml

    sdwan:
      omp_peer:
        show omp peers: VALIDATE

Use ``-cmd`` (*--create_commands*) to create the **xx_commands.yml** file and then unit test it. 

.. code-block:: bash

    uv run scripts/feature_builder.py -cmd <os_type> <feature>
    uv run pytest 'tests/test_validations.py::TestCommands::test_command_templating[<ostype>_<feature>]' -vv

    ❯ uv run scripts/feature_builder.py -cmd  cisco_viptela sdwan
    ❯ uv run pytest 'tests/test_validations.py::TestCommands::test_command_templating[cisco_viptela_sdwan]' -vv

2. Command Output (-di) 
-----------------------

The command output can be a parsed `ntc-template <https://github.com/networktocode/ntc-templates/tree/master/ntc_templates/templates>`_ data model (lists of dictionaries) or the screen scraped raw output (lists of strings). Use ``-di`` (*--discovery*) to create the **xx_cmd_output.json** file from a live device (prompted for username/password or env var *DVC_USER/DVC_PWORD*) or a local file of the raw output. 

.. code-block:: bash

    uv run scripts/feature_builder.py -di <netmiko_ostype> <feature.subfeature> <ip address or filename>

    ❯ uv run scripts/feature_builder.py -di cisco_viptela sdwan.omp_peer show_omp_peers.raw

.. note::

    If there are multiple commands used for a sub-feature ``-di`` will only create the structured data for the first command, the others will have to be added to the list manually.

3. Actual State (-as) and Validation file (-vf)
-----------------------------------------------

**xx_actual_state.py** is the python logic used to formulate the returned device data (command output) into a data structure format that will eventually match that of the desired state (just doesn't have the commands or *strict* key). The actual state and validation file generation use the same Python function (*format_xx*) as most of the time they are identical.

Although the formatting of this file is going to be different for each sub-feature, there are some common rules that should be observed to keep the code as uniform as possible.

- Each sub-feature must have its own function for doing the formatting
- Each sub-feature function must cover all OS types, this is accomplished with the **_set_keys** function that abstracts dictionary key names per os_type
- Any common functions (used by multiple functions) should start with *_*
- The **format_actual_state** function only calls the sub-feature functions, do not put any sub-feature formatting or logic in it
- **format_actual_state** must always use **_format_output** to differentiate between *raw_output* and *ntc_output*

Following on with the same **cisco_viptela sdwan.omp_peer** example, I want to create the following data structure for the actual state (grouped by OMP peer): 

.. code-block:: yaml

    192.168.11.1:
      site_id: 65154
      routes_received: 183
      routes_installed: 0
      routes_sent: 723
      state: up

Conditional per os_type key names are defined under the **OsKeys** class and **_set_keys** function, these normalize differences between the key names in different vendor outputs.

.. code-block:: python

    class OsKeys(NamedTuple):
        omp_peer: str

    def _set_keys(os_type: str) -> OsKeys:
        if "viptela" in os_type:
            return OsKeys("peer")
        # Fallback if nothing matched
        msg = f"Error, '_set_keys' has no match for OS type: '{os_type}'"
        raise NotImplementedError(msg)

The **format_actual_state** function is the engine that instantiates the keys and calls the sub-feature functions. Add a conditional entry for the new sub-feature that calls its formatting function, the function name must start with *format_* and the comment be the expected resulting data model.

.. code-block:: python

    def format_actual_state(val_file: bool, os_type: str, sub_feature: str, output: list[Union[str, dict[str, str]]]) -> dict[str, Any]:
        key = _set_keys(os_type)
        raw_output, ntc_output = _format_output(os_type, sub_feature, output)

        ### OMP_PEER: {peer: {site_id:x, routes_received:x, routes_installed:x:, routes_sent:x, state:x}}
        if sub_feature == "omp_peer":
            return format_omp(val_file, key, ntc_output)
        ### CatchAll
        else:
            msg = f"Unsupported sub_feature: {sub_feature}"
            raise ValueError(msg)


.. note::

    You may need to pass the *val_file* and/or *os_type* variables into the sub-feature function if the validation file or os_type output needs to be handled differently for the validation file or for a particular os_type.

Create the sub-feature function that will generate the actual state and validation file. Normally these are identical, however for elements that should always be implicitly in a certain state (such as omp state up) you will need to conditionally omit them from the validation file as they will be explicitly defined in the jinja template.

.. code-block:: python

    def format_omp(val_file: bool, key: OsKeys, output: list[dict[str, str]]) -> dict[str, Any]:
        """Format OMP peer into the data structure.
    
        Args:
            val_file (bool): Used to identify if creating validation file as sometimes need implicit values
            key (OsKeys): Keys for the specific OS type to retrieve the output data
            output (list[dict[str, str]]): The command output from the device in ntc data structure OR raw data structure
        Returns:
            dict[str, dict[str, str | int]]: {peer: {site_id:x, routes_received:x, routes_installed:x:, routes_sent:x, state:x}} val file has no {state: x}
        """
        result: dict[str, dict[str, str | int]] = defaultdict(dict)
        for entry in output:
            peer = entry[key.omp_peer]
            result[peer]["site_id"] = _make_int(entry["site_id"])
            result[peer]["routes_received"] = _make_int(entry["routes_received"])
            result[peer]["routes_installed"] = _make_int(entry["routes_installed"])
            result[peer]["routes_sent"] = _make_int(entry["routes_sent"])
            # If is actual_state adds peer state
            if not val_file:
                result[peer]["state"] = entry["state"]
        return dict(result)

.. note::

    All dictionary values that are numeric should be made an integer (use the **_make_int** function), if not validations wont be 100% accurate.

Use ``-as`` (*--format_actual_state*) to create the **xx_actual_state.yml** test file, ``-vf`` (*--create_val_file**) to create the **xx_validate.yml** file and unit test them.

.. code-block:: bash

    uv run scripts/feature_builder.py -as <os_type> <feature> 
    uv run pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[ostype_newfeature]' -vv
    uv run scripts/feature_builder.py -vf <os_type> <feature> 
    uv run pytest 'tests/test_validations.py::TestValFile::test_create_validation_file[ostype_newfeature]' -vv

    ❯ uv run scripts/feature_builder.py -as cisco_viptela sdwan
    ❯ uv run pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[cisco_viptela_sdwan]' -vv
    ❯ uv run scripts/feature_builder.py -vf cisco_viptela sdwan
    ❯ uv run pytest 'tests/test_validations.py::TestValFile::test_create_validation_file[cisco_viptela_sdwan]' -vv

4. Desired state
----------------

The validation file defines what *"correct"* looks like for each sub-feature, how the sub-feature is judged to be compliant. Therefore, it is this file that is used to create (render) the desired state. The desired state is a combination of the sub-feature commands (what is run to gather the actual state) and the validation file (what you want to validate) with any explicit states added. The formatting I am looking to achieve is below, **_mode: strict** has been added as it must be these exact OMP peers.

.. code-block:: yaml

    sdwan:
      omp_peer:
        show omp peers:
        _mode: strict
        192.168.11.1:
          site_id: 65154    
          routes_received: 183
          routes_installed: 0
          routes_sent: 723
          state: up

The configuration follows on from what added under step 1, under a *{% elif desired_state %}* statement you want to render the data from the validation file and add any explicit states (*state: up*).

.. code-block:: jinja

    {# ### OMP_PEER: {cmd: {peer: {site_id:x, routes_received:x, routes_installed:x:, routes_sent:x, state:up}}} ### #}
    {% elif sub_feat == 'omp_peer' and omp_peer_cmd is defined %}
        omp_peer:
          {{ omp_peer_cmd }}:
    {% if generate_val_file %}
            VALIDATE
    {% elif desired_state %}
            _mode: strict
    {% for each_peer, peer_info in input_vars.items() %}
            {{ each_peer }}:
              site_id: {{ peer_info.site_id }}
              routes_received: {{ peer_info.routes_received }}
              routes_installed: {{ peer_info.routes_installed }}
              routes_sent: {{ peer_info.routes_sent }}
              state: up
    {% endfor %}{% endif %}

.. note::

    For repeatable elements it is preferable to use macros to eliminate duplication.

Use ``-ds`` (*--create_desired_state*) to render the data from the validation file (*xx_validate.yml*) to create the **xx_desired_state.j2** test file and then unit test it.

.. code-block:: bash

    uv run scripts/feature_builder.py -ds <os_type> <feature> 
    uv run pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[ostype_newfeature]' -vv

    ❯ uv run scripts/feature_builder.py -ds cisco_viptela sdwan
    ❯ uv run pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[cisco_viptela_sdwan]' -vv

5. Compliance Report 
--------------------

The final thing to do is test that the *"desired_state.yml"* and *"actual_state.yml"* files match by unit testing the compliance report.

.. code-block:: bash

    uv run pytest 'tests/test_validations.py::TestComplianceReport::test_report_passes[ostype_newfeature]' -vv

    ❯ uv run pytest 'tests/test_validations.py::TestComplianceReport::test_report_passes[cisco_viptela_sdwan]' -vv
