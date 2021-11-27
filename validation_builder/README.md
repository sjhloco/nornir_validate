# Validation Builder

*validation_builder.py* is designed to help with the building of new validations, so the creation of *desired_state* templates and *actual_state* python logic. The *validation_builder* directory holds all of the files needed to create new validations to run this script.

- **desired_state.yml:** The result of what the rendered template will be
- **actual_state.json:** The result of what the actual state will after being run through the actual state python logic.
- **input_data.yml:** Input variables under *all*, *groups* and *hosts* dictionaries
- **desired_state.j2:** Template of per-feature Jinja logic used to render the input variables to create the desired state

*desired_state.yml* and *actual_state.json* are static files of what you are trying to achieve by either rendering the template or formatting the output returned by a devices. *input_data.yml* and *desired_state.j2* are the files you are trying to create that will eventually be used to dynamically create the first two files.

Even if a file is empty and not used or empty, all these files must be present or the script will not run. The file location and file names can be changed in the variables at the start of the script:

```python
test_directory = "validation_builder"           # Directory location where all tests files are stored
input_file = "input_data.yml"                   # Name of the input variable file
desired_state = "desired_state.yml"             # Name of the static desired_state file
desired_state_tmpl = "desired_state.j2"         # Name of the desired_state template
actual_state = "actual_state.json"              # Name of the static actual_state file
```

The script can be run with any of these flags to assist with the different stages of building the validation files. If no flag is specified it runs as normal creating the compliance report based on the *input_data.yml* and *desired_state.j2*.

| flag           | Description |
| -------------- | ----------- |
| -ds or --desired_state | Renders the contents of desired_state.j2 template and prints the YAML formatted output to screen
| -di or --discovery | Run the desired_state commands on a device printing the raw textFSM output to screen
| -as or --actual_state | Runs the desired_state commands creating and printing the JSON formatted actual_state to screen
| --rds or --report_desired_state | Builds compliance report using using static actual_state.json file and dynamically created desired_state
| --ras or --report_actual_state | Builds compliance report using using static desired_state.yml file and dynamically created actual_state
| no flag | Builds the compliance report using dynamically created desired_state and dynamically gathered formatted actual_state

The following steps walk through creating a new validation using the validate builder.

### 1. Create the desired state template

The first step is to define the Jinja2 template (*desired_state.j2*) which is used to create the *desired_state*. This is a YAML formatted list of nested dictionaries with the command being the key.

```jinja
{% if feature == 'ospf' %}
- show ip ospf neighbor:
    _mode: strict
{% for each_nbr in input_vars.nbrs %}
    {{ each_nbr }}:
      state: FULL
{% endfor %}
{% endif %}
```

The template is rendered using the input variables (*input_data.yml*) with the feature (*ospf* in this case) used for conditionally matching in the template.

```yaml
all:
  ospf:
    nbrs: [192.168.255.1]
```

`-ds` or `--desired_state` shows the output of the rendered template in YAML and JSON format. The JSON formatted output is what will be used for validation, so this is what you are aiming in terms of how the *actual_state* looks (the formatted device output)

```python
python validation_builder.py -ds
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

### 2. Discover textFSM formatted command output

The discovery stage will gather the command output from the device and format it in to data structure. Within *desired_state.yml* define a dictionary of commands of which to gather the output, the command is the key and the value can be an empty dictionary as at this stage it is just being used to run the command.

```yaml
- show ip ospf neighbor: {}
```

`-di` or `--discovery` return the command formatted into a data structure by textFSM. It uses *ntc-templates* so the command must already have been defined by NTC and be an exact match (no abbreviated commands)

```python
python validation_builder.py -di
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

### 3. Create actual state

Based on the discovery output build the formatting for the actual state in *actual_state.py* on a *os_type* basis. The idea is that the result of this formatting should match the JSON formatted output from step1 (minus top-level dict of *result* and *_mode*).

```python
if "show ip ospf neighbor" in cmd:
    for each_nhbr in output:
        tmp_dict[each_nhbr['neighbor_id']] = {'state': remove_char(each_nhbr['state'], '/')}
```

`-as` or `--actual_state` runs the commands from *desired_state.yml* and passes the returned output (textFSM data structure) through *actual_state.py* printing the resulting *actual_state* to screen.

```python
python validation_builder.py -as
**** Validation Builder - Actual State *****************************************
actual_state_task***************************************************************
* HME-SWI-VSS01 ** changed : False *********************************************
vvvv actual_state_task ** changed : False vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv INFO
{'show ip ospf neighbor': {'192.168.255.1': {'state': 'FULL'}}}
^^^^ END actual_state_task ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

## Using static files to create compliance report

A compliance report can be generated using either a static *actual_state* (JSON in *actual_state.json*) file and dynamic *desired_state* (from step1) or a static *desired_state* (YAML in *desired_state.yml*) and dynamic *actual_state* (from step3). This is a good way to test out the either of the dynamic states created in these steps.

Note: Although the JSON formatting in step1 is correct, for this to be used in Python (like when create static *actual_state.json* file) you must swap all `'` for `"`.

`--rds` or `--report_desired_state` builds and prints a compliance report with the *desire_state* dynamically created (rendering *desired_state.j2*) and the *actual_state* from a static file (loads *actual_state.json*).

```python
(mgmt_acl_update1) macoloco:validate$python validation_builder.py -rds
**** Validation Builder - Compliance Report dynamic desired_state and static actual_state
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

`--ads` or `--report_actual_state` builds and prints a compliance report with the *actual_state* dynamically created (from python logic in *actual_state.py*) and the *desired_state* from a static file (loads *desired_state.yml*).

```python
(mgmt_acl_update1) macoloco:validate$python validation_builder.py -ras
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
