# Adding a new Feature for Validation

 Features contain one or more sub-feature which define what is to be validated. Each feature has a directory in *feature_templates* that holds a jinja2 template and python module with each having two purposes.

- ***<feature>_desired_state.j2:*** Generates the commands used for validation file creation and renders the validation file to create the desired state
- ***<feature>_actual_state.py:*** Using devices command output creates the validation file and actual state

```bash
├── feature_templates
│   ├── intf_bonded
│   │   ├── intf_bonded_actual_state.py
│   │   └── intf_bonded_desired_state.j2
│   ├── neighbor
│   │   ├── neighbor_actual_state.py
│   │   └── neighbor_desired_state.j2
```

Each os_type has a *subfeature_index* file and per-feature test folder (*tests/os_test_files*) of files used to the test validation file, actual state and desired state. All test files are needed and must pass unit testing for a new feature to be added.

```bash
├── tests
│   ├── os_test_files
│   │   ├── cisco_asa
│   │   │   ├── intf_bonded
│   │   │   │   ├── cisco_asa_intf_bonded_actual_state.yml
│   │   │   │   ├── cisco_asa_intf_bonded_cmd_output.json
│   │   │   │   ├── cisco_asa_intf_bonded_commands.yml
│   │   │   │   ├── cisco_asa_intf_bonded_desired_state.yml
│   │   │   │   └── cisco_asa_intf_bonded_validate.yml
│   │   │   ├── redundancy
│   │   │   │   ├── cisco_asa_redundancy_actual_state.yml
│   │   │   │   ├── cisco_asa_redundancy_cmd_output.json
│   │   │   │   ├── cisco_asa_redundancy_command.yml
│   │   │   │   ├── cisco_asa_redundancy_desired_state.yml
│   │   │   │   └── cisco_asa_redundancy_validate.yml
│   │   │   ├── subfeature_index.yml
│   │   ├── cisco_ios
│   │   │   ├── intf_bonded
│   │   │   │   ├── cisco_ios_intf_bonded_actual_state.yml
│   │   │   │   ├── cisco_ios_intf_bonded_cmd_output.json
│   │   │   │   ├── cisco_ios_intf_bonded_commands.yml
│   │   │   │   ├── cisco_ios_intf_bonded_desired_state.yml
│   │   │   │   └── cisco_ios_intf_bonded_validate.yml
│   │   │   ├── subfeature_index.yml
```

The *feature_builder.py* script assists with the creation of new features for validation as well as all the relevant test files required.

| Flag and Argument | Description |
| ----------------- | ----------- |
| `-cf <os_type>_<feature>` | Creates the feature and test feature file structure (folders and files) |
| `-cmd <os_type> <feature>` | Generates the commands used to create a validation file (saved to *<os_type>_<feature>_cmds.yml*)
| `-di <netmiko_ostype> <command> <ip address or filename>` | Generates the *cmd_output* data structure (prints to screen)
| `-val <os_type> <feature>` | Generates the validate file (saved to *<os_type>_<feature>_desired_state.yml*)
| `-ds <os_type> <feature>` | Generates the *desired_state* data structure (saved to *<os_type>_<feature>_desired_state.yml*)  
| `-as <os_type> <feature>` | Generates the *actual_state* data structure (saved to *<os_type>_<feature>_actual_state.yml*)

Before you start building a new feature or sub-feature you need decide what you want to validate and what commands will be needed to be able to perform that validation.

### 1. Create the feature and feature test directories

Create the directories and base files files needed to build a new feature and its unit tests (from *skeleton_new_feature* with a pre-defined structure and formatting), all other files are created by subsequent runs of the *feature_builder.py* script. If you are just adding another OS to an existing feature it only creates the test directories and files for that os_type of the feature as everything else will already exist.

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
│   │   │   │   └── ostype_featurename_cmd_output.json
│   │   │   ├── subfeature_index.yml
```

### 2. Define the feature and/or sub-features *(subfeature_index.yml)* and commands to validate it *(subfeature_commands.yml)*

Each os_type test folder has 1 file indexing all features and sub features in the format *{feature: [sub-feat, sub-feat, etc]}*. The majority for the time the-sub feature will be a string, however on occasions for more complex validations that require multiple commands (VRF route-tables, ACLs, etc) this will be a dictionary of lists.

```yaml
all:
  system:
    - image
    - mgmt_acl: ["TEST_SSH_ACCESS", "TEST_SSH_ACCESS1"]
    - module
```

It is from this index file that the commands *subfeature_commands.yml* file is created (rendered from *feature_desired_state.j2*) which is will be later used to generate the validation file. The resulting formatting in the that you want to achieve after rendering is as follows:

```yaml
image:
  show version: VALIDATE
mgmt_acl:
  show ip access-lists TEST_SSH_ACCESS: VALIDATE
  show ip access-lists TEST_SNMP_ACCESS: VALIDATE
module:
  show module: VALIDATE
```

To keep the template file DRY the different *os_type* commands are set as conditional variables so that the rest of the template can be (wherever possible) the same for all os_types. The logic is *match on a sub-feature, define the command to run*.

```jinja
{# ####### CMD: Set command variables on a per-os_type basis ####### #}
{% if 'ios' in os_type |string %}
{% set new_subfeat1_cmd = "show x" %}
{% elif 'nxos' in os_type |string %}
{% endif %}

{# ##### VAL_CMDS: Build a dictionary of commands used for creating the validation file ##### #}
{% if sub_features.__class__.__name__ == 'list' %}
- {{ feature }}:
{% for sub_feat in sub_features %}
{% if sub_feat == 'new_subfeat1' and image_cmd is defined %}
    new_subfeat1: 
      {{ new_subfeat1_cmd }}: VALIDATE
{# ##### End statements: for sub_feature and sub_feature conditional  ##### #}
{% endif %}{% endfor %}
```

Render the template and unit tes the created *subfeature_commands.yml* file.

```none
python feature_builder.py -cmd <os_type> <feature> 
pytest 'tests/test_validations.py::TestCommands::test_command_templating[<os_type>_<feature>]' -vv
```

### 3. Edit the JSON formatted command output test file *(os_type_feature_name_cmd_output.json)*

This file holds the device output of the commands from step2 (grouped under sub-features) that the validation file and actual state will be gleaned from. If the command has an *[ntc-templates](https://github.com/networktocode/ntc-templates/tree/master/ntc_templates/templates)* the  output will be a list of dictionaries, if it is just screen scrapped output it will be a list with each element being a line of the output.

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

### 4. Edit *actual_state.generate_val_file* to generate the sub-feature validation file *(os_type_feature_name_validate.yml)*

The validations are what is fed into nornir_validate at run time to prove that this sub-feature is compliant. This is the file will that will be rendered by jinja to create the actual desired state. For things that should always be implicitly in a certain state (such as interfaces UP) is no need to include that actual status in the validation, it will be explicitly defined in the jinja template. The formatting that you want to achiev is as follows.

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

Python logic rather than jinja formulates is used to create this data structure. It is preferable to use functions wherever possible for repeatable code. All dictionary values that are numeric should be made an integer, if not validations wont be 100% accurate. In a similar manner to templates to keep the code DRY *os_type* dictionary keys are used as unfortunately different NTC templates have different key names.

```python
# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
def _set_keys(os_type: List) -> Dict[str, Dict]:
    global image_version, mgmt_acl_name, mgmt_acl_seq
    if bool(re.search("ios", os_type)):
        image_version = "version"
        mgmt_acl_name = "acl_name"
        mgmt_acl_seq = "line_num"
    elif bool(re.search("nxos", os_type)):
        image_version = "os"
        mgmt_acl_name = "name"
        mgmt_acl_seq = "sn"

# ----------------------------------------------------------------------------
# VALIDATION: Engine to create the validation file sub-feature validations (for all os-types)
# ----------------------------------------------------------------------------
def generate_val_file(
    os_type: List, sub_feature: str, output: List, tmp_dict: Dict[str, None]
) -> Dict[str, Dict]:
    _set_keys(os_type)
    ### SUB_FEATURE1_NAME: {key_name: x}
    if sub_feature == "new_subfeat1":
        tmp_dict["key_name"] = output[0][new_subfeat1]
    ### SUB_FEATURE2_NAME: {xxx: {y: y, z: xxx}}
    elif sub_feature == "new_subfeat2":
        for each_item in output:
            tmp_dict[each_item]["y"] = each_item["y"]
            tmp_dict[each_item]["z"] = each_item[new_subfeat2]
    return tmp_dict
```

Run *feature_builder.py* to create the validation file whihc can then be unit tested.

```none
python feature_builder.py -val <os_type> <feature> 
pytest 'tests/test_validations.py::TestValFile::test_create_validation_file[<os_type>_<feature>]' -vv
```

### 5. Create the desired state template *(feature_desired_state.j2)* and desired state test file *(ostype_feature_desired_state.j2)*

The desired state contains the validations got from the validation file (step4) and the commands (step2) that will be run to gather that actual state for that (the command outputs from step2). The same *os_type* commands and structure from step2 are used, only now the data from the validation file is added under each sub-feature and command.  For repeatable elements it is preferable to use macros to eliminate duplication.

```jinja
{# ##### DESIRED_STATE: Build desired state of the feature and each sub-feature ##### #}
{% else %}
- {{ feature }}:
{% for sub_feat, input_vars in sub_features.items() %}
{% for sub_feat, input_vars in sub_features.items() %}
{# ### SUB_FEATURE1_NAME: {cmd: {version: xx}} ### #}
{% if sub_feat == 'new_subfeat1' %}
    new_subfeat1: 
      {{ new_subfeat1_cmd }}: 
        {{ input_vars }}
{# ### SUB_FEATURE2_NAME: {cmd: {xxx: {y: y, z: xxx}}} ### #}
{% elif sub_feat == 'new_subfeat2' %}
    new_subfeat2:
      {{ new_subfeat2_cmd }}: 
{% for each_item in input_vars %}
        {{ each_item.xxx }}:
          y: {{ each_item.y }}
          z: {{ z | default('ok') }}
{% endfor %}
{# ##### End statements: for sub_feature and sub_feature conditional  ##### #}
{% endif %}{% endfor %}
{% endif %}
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

Once the template has been built render it using the validation file (step4) to create the desired_state test file *(ostype_feature_desired_state.j2)*). Once it has been created can now run the desired state unit testing for this one feature.

```none
python feature_builder.py -ds <os_type> <feature> 
pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[ostype_newfeature]' -vv
```

### 6. Create the actual state module *(feature_actual_state.py)* and actual state test file *(ostype_feature_actual_state.py)*

The actual state contains the python logic to formulate the returned device data into a data structure format that matches that of the desired state (just doesnt have the commands or strict dict). Depending on how similar the val_file and desired state are, it could be exactly the same as that definedin genrate_val_file. One main difference will  e implicit staes (like interface stae), this wouldnt be in the val_file  (as is implict it should be up) but will be in the actual state. It is preferable to use functions wherever possible for repeatable code. All dictionary values that are numeric should be made an integer, if not validations wont be 100% accurate.

```python
# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine that runs the actual state sub-feature formatting for all os types
# ----------------------------------------------------------------------------
def format_actual_state(
    os_type: List, sub_feature: str, output: List, tmp_dict: Dict[str, None]
) -> Dict[str, Dict]:
    _set_keys(os_type)
    ### SUB_FEATURE1_NAME: {key_name: x}
    if sub_feature == "image":
        tmp_dict["key_name"] = output[0][new_subfeat1]
    ### SUB_FEATURE2_NAME: {xxx: {y: y, z: xxx, status: ok}}
    elif sub_feature == "new_subfeat2":
        for each_item in output:
            tmp_dict[each_item]["y"] = each_item["y"]
            tmp_dict[each_item]["z"] = each_item[new_subfeat2]
            tmp_dict[each_item]["status"] = each_item["x"]
            
    return dict(tmp_dict)
```

Once the actual_state methods have been built create the actual_state test file *(ostype_feature_actual_state.j2)*) by feeding the test command output through the actual state module. Once it has been created can now run the actual state unit testing for this one feature.

```none
python feature_builder.py -as <os_type> <feature> 
pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[ostype_newfeature]' -vv
```

### 7. Run compliance report unit test

This will test that the actual_state and desired_state are correct by creating a compliance report based on the actual and desired state files created in hte previous steps.

```none
pytest 'tests/test_validations.py::TestComplianceReport::test_report_passes[ostype_newfeature]' -vv
```

### Unit testing

There are 5 sets of unit tests grouped under there own class to allow for running for individual os_type feature or all os_type and features

***test_command_templating:*** Renders *"subfeature_index.yml"* with *"x_desired_state.j2"* and compares result against the file *"x_commands.yml"*

```none
pytest 'tests/test_validations.py::TestCommands::test_command_templating[<os_type>_<feature>]' -vv
pytest 'tests/test_validations.py::TestCommands` -vv
```

***test_create_validation:*** Formats *"cmd_output.json"* with *"actual_state.generate_val_file"* and compares result against the file *"validate.yml"*

```none
pytest 'tests/test_validations.py::TestValFile::test_create_validation_file[<os_type>_<feature>]' -vv
pytest 'tests/test_validations.py::TestValFile' -vv
```

***test_desired_state_templating:*** Renders *"validate.yml"* with *"desired_state.j2"* and compares result against the file *"desired_state.yml"*

```none
pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[<os_type>_<feature>]' -vv
pytest 'tests/test_validations.py::TestDesiredState' -vv
```

***test_actual_state_formatting:*** Formats *"cmd_output.json"* with *"actual_state.format_actual_state"* and compares result against the file *"actual_state.yml"*

```none
pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[<os_type>_<feature>]' -vv
pytest 'tests/test_validations.py::TestActualState' -vv
```

***test_report_passes:*** Validates a compliance report comparing the files "desired_state.yml" and "actual_state.yml" passes

```none
pytest 'tests/test_validations.py::TestComplianceReport::test_report_passe[<os_type>_<feature>]' -vv
pytest 'tests/test_validations.py::TestComplianceReport' -vv
```

Finally can run all validations, so all classes.

```none
pytest tests/test_validations.py -vv
```

### Documentation

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
