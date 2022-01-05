# Validation Builder

*validation_builder.py* is designed to help with the building of new validations, so the creation of the *desired_state* templates and *actual_state* python logic. Within the *validation_builder* directory there are five files that will be used to create the new validations:

- **input_data.yml:** Dictionaries of the features to be validated stored under *all*, *groups* and *hosts* dictionaries
- **desired_state.j2:** Template of per-feature Jinja logic used to render the input data to create the desired state
- **desired_state.yml:** The desired state which is the result of the rendered template
- **actual_state.py:** Python file of the per-command python logic used to create the actual state from the command output
- **actual_state.json:** The actual state which is the result of the actual state python logic

*desired_state.yml* and *actual_state.json* are static files of what you are trying to achieve by either rendering the template or formatting the command output returned by a device. *input_data.yml* and *desired_state.j2* will hold the code you are trying to create that will eventually be used to dynamically create the first two files.

Even if a file is empty or not used all of these files must be present or the script will not run. The file location and file names can be changed in the variables at the start of the script.

```python
input_file = "input_data.yml"                   # Name of the input data file
desired_state = "desired_state.yml"             # Name of the static desired_state file
desired_state_tmpl = "desired_state.j2"         # Name of the desired_state template
actual_state = "actual_state.json"              # Name of the static actual_state file
actual_state_tmpl = "actual_state.py"           # Name of actual_state python logic file
from actual_state import format_actual_state    # Must also import the python logic file
```

Differing runtime flags are used to assist with the different stages of the validation file build process. If no flag is specified the compliance report is created based on the *input_data.yml* and *desired_state.j2*, so is the equivalent of running *nornir_validate*.

| flag           | Description |
| -------------- | ----------- |
| `-ds` or `--desired_state` | Renders the contents of the *desired_state.j2* template and prints the YAML formatted output
| `-rds` or `--report_desired_state` | Builds and prints a compliance report using the dynamically created *desired_state* and static *actual_state.json* file
| `-di` or `--discovery` | Runs the *desired_state* commands on a device printing the TextFSM data-modeled output
| `-as` or `--actual_state` | Runs the *desired_state* commands printing the JSON formatted *actual_state*
| `-ras` or `--report_actual_state` |  Builds and prints a compliance report using the dynamically created *actual_state* and static *desired_state.yml* file
| None | Builds and prints a compliance report using dynamically created *desired_state* and *actual_state*

The following steps walk you through the process of creating a new validation using the validate builder. At a bare minimum to be able to run the script a feature dictionary is required in the input_data and a conditional match of that same feature in the jinja template (see step1.)

## 1. Create desired_state template

Define the Jinja2 template (*desired_state.j2*) which is used to create the *desired_state*. This is a YAML formatted per-device_type list of nested dictionaries with the command being the key and the value the expected feature state.

```jinja
{% if 'ios' in os_type |string %}
{% if feature == 'ospf' %}
- show ip ospf neighbor:
    _mode: strict
{% for each_nbr in input_vars.nbrs %}
    {{ each_nbr }}:
      state: FULL
{% endfor %}
{% endif %}
{% endif %}
```

The template is rendered using the input data (*input_data.yml*) with the os_type (*ios*) feature (*ospf*) used for conditionally matching in the template.

```yaml
all:
  ospf:
    nbrs: [192.168.255.1]
```

`-ds` or `--desired_state` prints the output of the rendered template in YAML and JSON format. The JSON formatted output is what will be used by the compliance report, so this is what you are aiming for in terms of how the *actual_state* is structured (formatted command output).

```python
python val_builder.py -ds
**** Validation Builder - Desired State ****************************************
desired_state_task**************************************************************
* HME-SWI-VSS01 ** changed : False *********************************************
vvvv desired_state_task ** changed : False vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv INFO
---- template in YAML ** changed : False --------------------------------------- INFO
- show ip ospf neighbor:
    _mode: strict
    192.168.255.1:
      state: FULL

---- template in JSON ** changed : False --------------------------------------- INFO
{ 'result': { 'show ip ospf neighbor': { '192.168.255.1': {'state': 'FULL'},
                                         '_mode': 'strict'}}}
^^^^ END desired_state_task ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

## 2. Test dynamic desired_state against static actual_state

Run a compliance report using the dynamic *desired_state* (from step1) and a static *actual_state* (*actual_state.json*) file to prove that the jinja templating and format of the actual_state is correct. Although the JSON formatting of the actual_state in step1 is correct, for this to be used in Python (the static *actual_state.json* file) you must swap out all `'` for `"` and remove the ***result*** and ***_mode*** (if used) dictionaries.

```python
{ "show ip ospf neighbor": { "192.168.255.1": {"state": "FULL"}}}
```

`--rds` or `--report_desired_state` builds and prints the compliance report with the *desire_state* dynamically created (rendering *desired_state.j2*) and the *actual_state* got from a static file (loads *actual_state.json*).

```python
python val_builder.py -rds
**** Validation Builder - Compliance Report using dynamic desired_state and static actual_state
report_desired_state_task*******************************************************
* HME-SWI-VSS01 ** changed : False *********************************************
vvvv report_desired_state_task ** changed : False vvvvvvvvvvvvvvvvvvvvvvvvvvvvvv INFO
{ 'show ip ospf neighbor': { 'complies': True,
                             'extra': [],
                             'missing': [],
                             'present': { '192.168.255.1': { 'complies': True,
                                                             'nested': True}}}}
^^^^ END report_desired_state_task ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

## 3. Discover TextFSM formatted command output

The discovery stage will gather the TextFSM formatted command output from the device. The *desired_state.yml* defines a list of dictionaries with the key being the command to be run (used to gather output) and the value the desired state. At this stage of the process it is just an empty dictionary as it is only being used to define the commands that will be run on a device.

```yaml
- show ip ospf neighbor: {}
```

`-di` or `--discovery` return the command output formatted into a TextFSM data model. TextFSM uses *ntc-templates* so the command must already have been defined by [NTC](https://github.com/networktocode/ntc-templates/tree/master/ntc_templates/templates) and be an exact match of the full command (no abbreviations like *show ip int brief*).

```python
python val_builder.py -di
**** Validation Builder - Discovery ********************************************
discovery_task******************************************************************
* HME-SWI-VSS01 ** changed : False *********************************************
vvvv discovery_task ** changed : False vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv INFO
{ 'show ip ospf neighbor': [ { 'address': '192.168.255.1',
                               'dead_time': '00:00:35',
                               'interface': 'Vlan98',
                               'neighbor_id': '192.168.255.1',
                               'priority': '1',
                               'state': 'FULL/BDR'}]}
^^^^ END discovery_task ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

## 4. Create actual state

Based on the discovery output build the python logic to perform the data model formatting of the *actual_state* so that it matches the JSON formatted output from step2 (minus top-level *result* dictionary and nested *_mode* dictionary). This is defined in the *actual_state.py* on a *per-os_type* basis as each os-type has a separate function.

By using a breakpoint (*ipdb.set_trace()*) after the command you can look through the TextFSM data model to workout the python logic for your *actual_state* data model. The [nornir docs](https://nornir.readthedocs.io/en/latest/howto/ipdb_how_to_use_it_with_nornir.html) have a good tutorial on using the [iPython pdb debugger](https://github.com/gotcha/ipdb).

```python
if "show ip ospf neighbor" in cmd:
    # ipdb.set_trace()
    for each_nhbr in output:
        tmp_dict[each_nhbr['neighbor_id']] = {'state': remove_char(each_nhbr['state'], '/')}
```

`-as` or `--actual_state` runs the commands from the *desired_state.yml* and passes the returned output (TextFSM data-model) through *actual_state.py* printing the resulting *actual_state* to screen.

```python
python val_builder.py -as
**** Validation Builder - Actual State *****************************************
actual_state_task***************************************************************
* HME-SWI-VSS01 ** changed : False *********************************************
vvvv actual_state_task ** changed : False vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv INFO
{'show ip ospf neighbor': {'192.168.255.1': {'state': 'FULL'}}}
^^^^ END actual_state_task ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

## 5. Test dynamic actual_state against static desired_state

Run a compliance report using the dynamic *actual_state* (from step4) and a static *desired_state* (*desired_state.yml*) file to prove that the jinja templating and format of the actual_state is correct. This test can come in handy when troubleshooting or changing an existing *desired_state*. As you have already proved the dynamic desired state in step2 for new validations you can skip this test and just run the full report (step6) instead.

```yaml
- show ip ospf neighbor:
    _mode: strict
    192.168.255.1:
      state: FULL
```

`--ads` or `--report_actual_state` builds and prints a compliance report with the *actual_state* dynamically created (from python logic in *actual_state.py*) and the *desired_state* got from a static file (loads *desired_state.yml*).

```python
python val_builder.py -ras
**** Validation Builder - Compliance Report using dynamic actual_state and static desired_state
report_actual_state_task********************************************************
* HME-SWI-VSS01 ** changed : False *********************************************
vvvv report_actual_state_task ** changed : False vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv INFO
{ 'show ip ospf neighbor': { 'complies': True,
                             'extra': [],
                             'missing': [],
                             'present': { '192.168.255.1': { 'complies': True,
                                                             'nested': True}}}}
^^^^ END report_actual_state_task ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

## 6. Create Compliance report with dynamic desired_state and actual_state

Once happy with the new validations run the script with no flags (the equivalent of using *nr_val.py*) to dynamically create files for both the *desired_state* and *actual_state*.

```python
python val_builder.py
**** Validation Builder - Compliance Report ************************************
report_task*********************************************************************
* HME-SWI-VSS01 ** changed : False *********************************************
vvvv report_task ** changed : False vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv INFO
{ 'complies': True,
  'show ip ospf neighbor': { 'complies': True,
                             'extra': [],
                             'missing': [],
                             'present': { '192.168.255.1': { 'complies': True,
                                                             'nested': True}}},
  'skipped': []}
^^^^ END report_task ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

The new lines of code in the jinja template and python file can now be moved into the relevant files within the nornir_validate *templates* directory to be used for future validations.

## 7. Add to unittests

***test_validations.py*** tests that the desired state templating and actual state command formatting is correct. Once the validations are completed update the relevant dictionaries within ***desired_actual_cmd.py*** with the outputs got from val_builder to add these commands to unittesting. This file contains the following 3 dictionaries with each having a further child dictionary for the different os_types.

- **input_data_validations:** The per-os_type input variables that the desired and actual state will be created from
- **desired_state:** Should match the templated result of the rendered jinja template
- **cmd_output:** The raw textFSM formatted device command output (used to create the actual_state)
- **actual_state:** Should match the formatted result of the actual_state python logic
- **input_data_validations:** The per-os_type input variables that the desired and actual state will be created from

Test methods have been built for WLC and Checkpoints but are hashed out as there are no actual tests for these device types at the moment.

#### a. Update input data

Add the input data used in val_builder to relevant groups os_type dictionary within the *input_data_validations.yml*.

#### b. TestDesiredState

Add JSON formatted output (not YAML) from the ***desired_state*** (`-ds`) to the relevant os_type dictionary in *desired_state*. Make sure to remove parent the *results* dictionary (leave *_mode* in) and replace all instances of *'* for *"* (if using black it will automatically do this for you).

You can run all desired_state unittests or run any of the individual os_type desired_state unittests.

```python
pytest tests/test_validations.py::TestDesiredState -vv
pytest tests/test_validations.py::TestDesiredState::test_ios_desired_state_templating -vv
pytest tests/test_validations.py::TestDesiredState::test_nxos_desired_state_templating -vv
pytest tests/test_validations.py::TestDesiredState::test_asa_desired_state_templating -vv
```

#### c. TestActualState

Add the output from the output of ***discovery*** (`-di`) to the relevant os_type dictionary in *cmd_output* and ***actual_state*** (`-as`) to the relevant os_type dictionary in *actual_state* (replace *'* for *"* or let black do it) automatically.

You can run all actual_state unittests or run any of the individual os_type actual_state unittests.

```python
pytest tests/test_validations.py::TestActualState -vv
pytest tests/test_validations.py::TestActualState::test_ios_actual_state_formatting -vv
pytest tests/test_validations.py::TestActualState::test_nxos_actual_state_formatting -vv
pytest tests/test_validations.py::TestActualState::test_asa_actual_state_formatting -vv
```

The unittests can be run for both desired and actual state by omitting the method name.

```python
pytest tests/test_validations.py -vv
```