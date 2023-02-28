# Adding a new Feature for Validation

The *feature_builder.py* script assists with the creation of new features for validation as well as relevant test files also required. 

Every feature has a folder within *feature_templates* that holds a jinja2 template file (`<feature>_desired_state.j2`) for creating the desired state (from the input validation data) and a python module (`<feature>_actual_state.py`) used for creating the actual state from the command output. Features can contain one or more sub-features that are validated, the logic for all of these sub-features for all os types are within these files.

```bash
├── feature_templates
│   ├── intf_bonded
│   │   ├── intf_bonded_actual_state.py
│   │   └── intf_bonded_desired_state.j2
│   ├── neighbor
│   │   ├── neighbor_actual_state.py
│   │   └── neighbor_desired_state.j2
```

Every feature must also have a per os_type test folder (within *tests/os_test_files*) that contains 4 files to test the actual state and desired state creation. All test files are needed and must pass unit testing for a new feature to be added.


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

### 1. Create the feature and feature test directories

Use the following command to create the folder directories as well as all the needed files except for the test *_desired_state.yml* and *_actual_state.yml* files (as these will be created by subsequent runs of the script). If you are just adding another OS to an existing feature it will obviously on created the test directories and files for that os_type of te feature. All the files created have the skelton structure already set as well as the formatting for comments that should be followed.

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

This the output that teh actul state will be gleaned from. Each sub-feature will have a seperate command, this could be a dictionary of a few commands with each under a sub-feature name dictionary. If the command has an NTC template the command output will be a list of dictioanries, if it is jsut screen scrapped output it will be a list with each element being a line of the output.

{
    "new_feature": {
        "sub_feature1": [
            {
                cmd output
            }
        ]
    }
}

The script can be used to generate the json output for a single command from a live device or a copy of the devices output from file.

```none
python feature_builder.py -di <netmiko_ostype> <command> <ip address or filename>
```


### 3. Create the validated state test *(os_type_feature_name_validate.yml)*

From the command output you can now desfine the valdaitions that are wanted to prove this sub-feature is compliant. For things such as interfaces that you would exploctly to always be in a certain state is no need to include that actual status in the validation, it will be explict.

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

The desired state contains the commands to be run by each subfeature and the validation for each information got from the rendered file. To keep it DRY the different os type commands are set as conditional variables so that the rest of the template can be where ever possible the same for all os type. It is preferable to use macros whereever possible for repeatable code.

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

Any desired state values that are lists of objects (can also be strict) require an extra key called *list*, this is not needed in actual state).

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

Once the template has been built the `-ds` flag can be used to test it by trying to render the desired state test file *(ostype_feature_desired_state.j2)*) using the template and the validate test file. Once it has been created also run the desired state unit testing for this one feature.

```
python feature_builder.py -ds <os_type> <feature> 
pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[ostype_newfeature]' -vv
```

### 5. Create the actual state module *(feature_actual_state.py)* and actual state test file *(ostype_feature_actual_state.py)*

The actual state contains the python logic to fomrulate the returned device data into a data structure format that matches that of the desired state. To keep it DRY for different os types commands conditional variables are set for dictioanry keys as these can vary between the different os type structred data returned by NTC templates. It is preferable to use functions whereever possible for repeatable code. All dictionary values that are numeric should be made an integerer (if not validations wont be 100% accurate.)

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

Once the template has been built the `-as` flag can be used to test it by trying to create the actual state test file *(ostype_feature_actual_state.j2)*) by feeding the test command output through the actual state module.  Once it has been created also run the actual state unit testing for this one feature.

```
python feature_builder.py -as <os_type> <feature> 
pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[ostype_newfeature]' -vv
```

### ^. Run compliance report test 

pytest 'tests/test_validations.py::TestComplianceReport::test_report_passes[ostype_newfeature]' -vv

### 6. Run all unit tests and add to documentation

Run the unit tests for all validations desired and actual state.

```
pytest tests/test_validations.py -vv
```

If all tests pass add the inforation reagrds to the feature to the *current validations* table of the README and add an example of the new validation to the *full_example_input_data.yml* file.


!!! Wherever possible best to use dict rather than a list of dicts as get better output on what when wrong. Fore example:

with bas ASN

  route_protocol:
    eigrp_nbr:
      - ip: 10.10.10.2
        intf: Gi3
        asn: 1
      - ip: 10.230.205.27
        intf: Vl10
        asn: 54

E             Full diff:
E               {
E             +  'diff': {'complies': False,
E             +           'extra': [{'asn': 545,
E             +                      'intf': 'Vl10',
E             +                      'ip': '10.230.205.27',
E             +                      'state': 'up'}],
E             +           'missing': [{'asn': 54,
E             +                        'intf': 'Vl10',
E             +                        'ip': '10.230.205.27',
E             +                        'state': 'up'}],
E             +           'present': [{'asn': 1,
E             +                        'intf': 'Gi3',
E             +                        'ip': '10.10.10.2',
E             +                        'state': 'up'}]},
E                'nested': True,
E               }

  route_protocol:
    eigrp_nbr:
      10.10.10.2:
        intf: Gi3
        asn: 1
      10.230.205.27:
        intf: Vl10
        asn: 54

E             +  'diff': {'complies': False,
E             +           'extra': [],
E             +           'missing': [],
E             +           'present': {'10.10.10.2': {'complies': True,
E             +                                      'nested': True},
E             +                       '10.230.205.27': {'complies': False,
E             +                                         'diff': {'complies': False,
E             +                                                  'extra': [],
E             +                                                  'missing': [],
E             +                                                  'present': {'asn': {'actual_value': 545,
E             +                                                                      'complies': False,
E             +                                                                      'expected_value': 55,
E             +                                                                      'nested': False},
E             +                                                              'intf': {'complies': True,
E             +                                                                       'nested': False},
E             +                                                              'state': {'complies': True,
E             +                                                                        'nested': False}}},
E             +                                         'nested': True}}},
E                'nested': True,
E               }



!!!! If want to use multiple commands to form a su-feature then all but one of the commands can have a dict value of any string rather than a dict ofm validatiosn and will be removed when commands are removed, see ospf for example

{% elif sub_feat == 'ospf_intf_nbr' %}
    ospf_intf_nbr:
      {{ ospf_intf_cmd }}: 
        SUB_FEATURE_COMBINED_CMD
      {{ ospf_nbr_cmd }}: 










- **input data (variables)**: Yaml file (default is *input_data.yml*) that holds the *host*, *group* and *all* data that describe the desired state of the network
- **desired_state template:** Jinja template (*desired_state.j2*) that is rendered with the input data to create the desired state
- **actual_state python logic:** Python method (*actual_state.py*) that creates a data structure from the command outputs to be used as a comparison against the desired state




## Desired State

The input file (***input_data.yml***) is rendered by a jinja template (***desired_state.j2***) to produce a YAML formatted list of dictionaries with the key being the command and the value the desired output. The top level Jinja condition is for the ***os_type*** got from nornir *platform* (*ios* and *iosxe* are the same) with ***feature*** matching the feature name within the input file to make the rendering conditional. Optionally, ***strict*** mode can be used to ensure of an exact match, no more, no less.

```jinja
{% if 'ios' in os_type |string %}
{% if feature == 'image' %}
- show version:
    image: {{ input_vars }}
{% elif feature == 'port_channel' %}
- show etherchannel summary:
{% for each_po_name, each_po_info in input_vars.items() %}
    {{ each_po_name }}:
      status: U
      protocol: {{ each_po_info.protocol }}
      members:
        _mode: strict
{% for each_member in each_po_info.members %}
        {{ each_member }}:
          mbr_status: P
{% endfor %}{% endfor %}
{% elif feature == 'ospf_nbr' %}
- show ip ospf neighbor:
    _mode: strict
{% for each_nbr in input_vars.nbrs %}
    {{ each_nbr }}:
      state: FULL
{% endfor %}
{% endif %}{% endif %}
```

Below is an example of the YAML output after rendering the template with the example input data.

```yaml
- show version: 
    image: 16.6.2
- show etherchannel summary:
    Po2:
      status: U
      protocol: LACP
      members:
        _mode: strict
        Gi0/15:
          mbr_status: P
        Gi0/16:
          mbr_status: P
- show ip ospf neighbor:
    _mode: strict
    192.168.255.1:
      state: FULL
    2.2.2.2:
      state: FULL
```

The resulting python object is generated by serialising the YAML output and is stored as a host_var (nornir *data* dictionary) called *desired_state*.

```python
{
    "show version": {"image": "16.6.2"},
    "show etherchannel summary": {
        "Po2": {
            "status": "U",
            "protocol": "LACP",
            "members": {
                "_mode": "strict",
                "Gi0/15": {"mbr_status": "P"},
                "Gi0/16": {"mbr_status": "P"},
            },
        }
    },
    "show ip ospf neighbor": {
        "192.168.255.1": {"state": "FULL"},
        "2.2.2.2": {"state": "FULL"},
        "_mode": "strict",
    },
}
```

## Actual State

Netmiko gathers command outputs creating TextFSM formatted data-models (using *[ntc-templates](https://github.com/networktocode/ntc-templates/tree/master/ntc_templates/templates)*) that are fed into ***actual_state.py*** and matched on *os_type* specific methods and commands to create a nested dictionary that matches the structure of the *desired_state*.

```python
def ios_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:
    if "show version" in cmd:
        tmp_dict["image"] = output[0]["version"]
    elif "show etherchannel summary" in cmd:
        for each_po in output:
            tmp_dict[each_po["po_name"]]["status"] = each_po["po_status"]
            if each_po["protocol"] == "-":
                each_po["protocol"] = "NONE"
            tmp_dict[each_po["po_name"]]["protocol"] = each_po["protocol"]
            po_mbrs = {}
            for mbr_intf, mbr_status in zip(
                each_po["interfaces"], each_po["interfaces_status"]
            ):
                po_mbrs[mbr_intf] = {"mbr_status": mbr_status}
            tmp_dict[each_po["po_name"]]["members"] = po_mbrs
    elif "show ip ospf neighbor" in cmd:
        for each_nhbr in output:
            tmp_dict[each_nhbr["neighbor_id"]] = {
                "state": remove_char(each_nhbr["state"], "/")
            }
    actual_state[cmd] = dict(tmp_dict)
    return actual_state
```

The resulting *actual_state* is the same as the *desired_state* except for the absence of *'_mode': 'strict'*.

```python
{
    "show version": {"image": "16.6.2"},
    "show etherchannel summary": {
        "Po2": {
            "status": "U",
            "protocol": "LACP",
            "members": {
                "Gi0/15": {"mbr_status": "P"},
                "Gi0/16": {"mbr_status": "P"},
            },
        }
    },
    "show ip ospf neighbor": {
        "192.168.255.1": {"state": "FULL"},
        "2.2.2.2": {"state": "FULL"},
    },
}
```

For each command the formatting will be different as the captured data is different, however the principle is same in terms of the structure.