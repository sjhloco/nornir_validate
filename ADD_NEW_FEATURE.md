# Adding a new Feature for Validation

Every feature has a directory in *feature_templates* that holds a jinja2 template file (`<feature>_desired_state.j2`) for creating the desired state (from the input validation data) and a python module (`<feature>_actual_state.py`) used for creating the actual state (from the command output). Features contain one or more sub-feature (what is to be validated) with the logic for all os types being in the one file.

```bash
├── feature_templates
│   ├── intf_bonded
│   │   ├── intf_bonded_actual_state.py
│   │   └── intf_bonded_desired_state.j2
│   ├── neighbor
│   │   ├── neighbor_actual_state.py
│   │   └── neighbor_desired_state.j2
```

Every feature must have a per-os_type test folder (*tests/os_test_files*) that contains 4 files used to test the actual and desired state creation. All test files are needed and must pass unit testing for a new feature to be added.

```bash
├── tests
│   ├── os_test_files
│   │   ├── cisco_asa
│   │   │   ├── intf_bonded
│   │   │   │   ├── cisco_asa_intf_bonded_actual_state.yml
│   │   │   │   ├── cisco_asa_intf_bonded_cmd_output.json
│   │   │   │   ├── cisco_asa_intf_bonded_desired_state.yml
│   │   │   │   └── cisco_asa_intf_bonded_validate.yml
│   │   │   ├── redundancy
│   │   │   │   ├── cisco_asa_redundancy_actual_state.yml
│   │   │   │   ├── cisco_asa_redundancy_cmd_output.json
│   │   │   │   ├── cisco_asa_redundancy_desired_state.yml
│   │   │   │   └── cisco_asa_redundancy_validate.yml
│   │   ├── cisco_ios
│   │   │   ├── intf_bonded
│   │   │   │   ├── cisco_ios_intf_bonded_actual_state.yml
│   │   │   │   ├── cisco_ios_intf_bonded_cmd_output.json
│   │   │   │   ├── cisco_ios_intf_bonded_desired_state.yml
│   │   │   │   └── cisco_ios_intf_bonded_validate.yml
```

The *feature_builder.py* script assists with the creation of new features for validation as well as all the relevant test files required.

| Flag and Argument | Description |
| ----------------- | ----------- |
| `-cf <os_type>_<feature_name>` | Creates the feature and test feature file structure (folders and files) |
| `-di <netmiko_ostype> <command> <ip address or filename>` | Generates the *cmd_output* data structure (prints to screen)
| `-ds <os_type> <feature>` | Generates the *desired_state* data structure (saved to *<os_type>_<feature>_desired_state.yml*)  
| `-as <os_type> <feature>` | Generates the *actual_state* data structure (saved to *<os_type>_<feature>_actual_state.yml*)

### 1. Create the feature and feature test directories

Create all the directories files needed for a feature and its unit tests except for the *_desired_state.yml* and *_actual_state.yml* as these will be created by subsequent runs of the *feature_builder.py*. All the files created have the skelton structure (from *skeleton_new_feature*) already set as well as the formatting for comments. If you are just adding another OS to an existing feature it only creates the test directories and files for that os_type of the feature as everything else will already exist.

```none
python feature_builder.py -cf <os_type> <feature_name>
```

This will create the following:

```bash
├── feature_templates
│   ├── feature_name
│   │   ├── featurename_actual_state.py
│   │   └── featurename_desired_state.j2
├── tests
│   ├── os_test_files
│   │   ├── os_type
│   │   │   ├── intf_bonded
│   │   │   │   ├── ostype_featurename_cmd_output.json
│   │   │   │   └── ostype_featurename_validate.yml
```

### 2. Edit the JSON formatted command output test file *(os_type_feature_name_cmd_output.json)*

This the device output that the actual state will be gleaned from. Each sub-feature will have the either 1 command or a dictionary of a few commands needed to validate that sub-feature. If the command has an *[ntc-templates](https://github.com/networktocode/ntc-templates/tree/master/ntc_templates/templates)* the command output will be a list of dictionaries, if it is just screen scrapped output it will be a list with each element being a line of the output.

{
    "new_feature": {
        "sub_feature1": [
            {
                cmd output
            }
        ]
    }
}

*feature_builder.py* can be used to generate the json output for a single command from a live device or from a file containing the devices output.

```none
python feature_builder.py -di <netmiko_ostype> <command> <ip address or filename>
```

### 3. Create the sub-feature validations *(os_type_feature_name_validate.yml)*

From the command output define the validations that are wanted to prove that this sub-feature is compliant. For things that should always be explicitly in a certain state (such as interfaces UP) is no need to include that actual status in the validation, it will be explicitly defined in the jinja template.

```yaml
all:
  new_feature:
    new_subfeat1: 
      a: b
    new_subfeat2:
      - c: d
        x: y
      - e: f
        a: z
```

### 4. Create the desired state template *(feature_desired_state.j2)* and desired state test file *(ostype_feature_desired_state.j2)*

The desired state contains the validations got from the validation file (step3) and the commands that will be run to gather that actual state for that (the command outputs from step2). To keep it DRY the different *os_type* commands are set as conditional variables so that the rest of the template can be (wherever possible) the same for all os_types. For repeatable elements it is preferable to use macros to eliminate duplication.

```jinja
{% if 'ios' in os_type |string %}
{% set new_subfeat1_cmd = "show x" %}
{% elif 'nxos' in os_type |string %}
{% set new_subfeat1_cmd = "show y" %}
{% endif %}

- {{ feature }}:
{% for sub_feat, input_vars in sub_features.items() %}
{% if sub_feat == 'new_subfeat1' %}
    new_subfeat1:
      {{ new_subfeat1_cmd }}: 
{% for each_item in input_vars %}
        {{ each_item.x }}:
          y: {{ each_item.y }}
          status: Up
{% endfor %}
{% endif %}{% endfor %}
```

Any desired state values that are lists of objects (can also be strict) require an extra key called *list* (this is not needed in actual state).

```yaml
route_table:
  vrf:
    show vrf:
      BLU:
        intf:
          _mode: strict
          list:
          - Lo12
          - Vl5
```

Once the template has been built render it using the validation test file (step3) to create the desired_state test file *(ostype_feature_desired_state.j2)*). Once it has been created can now run the desired state unit testing for this one feature.

```none
python feature_builder.py -ds <os_type> <feature> 
pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[ostype_newfeature]' -vv
```

### 5. Create the actual state module *(feature_actual_state.py)* and actual state test file *(ostype_feature_actual_state.py)*

The actual state contains the python logic to formulate the returned device data into a data structure format that matches that of the desired state. It is preferable to use functions wherever possible for repeatable code. All dictionary values that are numeric should be made an integer, if not validations wont be 100% accurate.

```python
def format_output(os_type: str, sub_feature: str, output: List, tmp_dict: Dict[str, None]) -> Dict[str, Dict]:

    if bool(re.search("ios", os_type)):
        new_subfeat1 = "x"
    elif bool(re.search("nxos", os_type)):
        new_subfeat1 = "y"

    if sub_feature == "new_subfeat1":
        for each_item in output:
            tmp_dict[each_item]["y"] = each_item[new_subfeat1]
            tmp_dict[each_item]["z"] = _make_int(each_item[new_subfeat2])

    return dict(tmp_dict)
```

Once the actual_state methods have been built create the actual_state test file *(ostype_feature_actual_state.j2)*) by feeding the test command output through the actual state module. Once it has been created can now run the actual state unit testing for this one feature.

```
python feature_builder.py -as <os_type> <feature> 
pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[ostype_newfeature]' -vv
```

### 6. Run compliance report unit test

This will test that the actual_state and desired_state are correct by creating a compliance report based on the actual and desired state files created in hte previous steps.

pytest 'tests/test_validations.py::TestComplianceReport::test_report_passes[ostype_newfeature]' -vv

### 7. Run all unit tests and add to documentation

Finally run unit tests for validations of all features desired state, actual state and compliance report.

```
pytest tests/test_validations.py -vv
```

### 8. Documentation

The following needs updating for any new validations:

- README: Update the *current validations* table
- Example_validations: Add a simple example of the validation data to *all_validations.yml* as well as any os_type validation file that feature can be used by

### Extra information

Wherever possible best to use dictionary rather than a list of dictionaries as get better output on what when wrong. A list is just looking for an exact amtch of the list, whereas a dictionary will tell you the differences for each individual dictionary key:value pair. 

In order to use multiple commands to form a sub-feature as the validations are meant to be under the command one of the commands has the validations and all the others have *SUB_FEATURE_COMBINED_CMD* which is matched and removed when the commands are removed so as not to affect desired state formatting. *route_protocol.ospf_intf_nbr* shows an example of this as it combines the OPSF neighbor and interface command outputs for validation.

```jinja
{% elif sub_feat == 'ospf_intf_nbr' %}
    ospf_intf_nbr:
      {{ ospf_intf_cmd }}: 
        SUB_FEATURE_COMBINED_CMD
      {{ ospf_nbr_cmd }}: 
{% for each_intf, intf_info in input_vars.items() %}
        {{ each_intf }}:
          pid: {{ intf_info.pid }}
          area: {{ intf_info.area }}
{% if intf_info.nbr is defined %}
          {{ def_nbr(intf_info, "FULL") }}
{% else %}
          nbr: {}
{% endif %}
{% endfor %}
```
