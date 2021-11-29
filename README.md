# Nornir Validate

Uses Nornir (with ***nornir-netmiko***) to gather and format device output before feeding this into ***napalm-validate*** in the form of ***actual_state*** and ***desired_state*** to produce a ***compliance report***. The idea behind this is for running pre and post checks on network devices based and an input file of the desired device state.

As the name suggests I have not reinvented the wheel here, I have just extended *napalm_validate* to validate on commands rather than getters to allow me the flexibility to validate any command output. This is done by importing the *napalm_validate compare* method and feeding in the *desire_state* and *actual_state* manually. To understand what I am waffling on about in this README you need to understand the following terms:

- **desired_state:** The state you expect the device to be in. For example, you could expect that the device has certain OSPF neighbors, specific CDP neighbors or that all ports in a port-channel are up
- **actual_state:** This is real-time state of the device gathered by connecting to it and scraping the output of show commands

## Installation and Prerequisites

Clone the repository, create a virtual environment and install the required python packages

```bash
git clone https://github.com/sjhloco/nornir_validate.git
python -m venv ~/venv/nr_val
source ~/venv/nr_val/bin/activate
cd nornir_validate/
pip install -r requirements.txt
```

### Caveats

There a couple of bugs in current releases of nornir and netmiko that effect how this script runs, below describes the workarounds for these.

**netmiko**\
If using python3.9 the script will fail with this error as described in [bug](https://github.com/ktbyers/netmiko/pull/2274)\
`IsADirectoryError: [Errno 21] Is a directory: '/Users/user1/venv/nr_val/lib/python3.9/site-packages/ntc_templates/templates'`

The current Netmiko version (3.4) doesn't yet have the fix so replace *utilities.py* from your local netmiko directory with *bug_fixes/utilities.py* that has the bug fix applied. In the commands swap out */Users/user1/venv/nr_val* with your own virtual environment.

```bash
mv /Users/user1/venv/nr_val/lib/python3.9/site-packages/netmiko/utilities.py /Users/user1/venv/nr_val/lib/python3.9/site-packages/netmiko/utilities.py_ORIG
cp bug_fixes/utilities.py /Users/user1/venv/nr_val/lib/python3.9/site-packages/netmiko/utilities.py
```

**nornir_utils**\
This [bug](xxx) is purely cosmetic so doesn't effect the functionality, is upto you if you want to apply or not.

```bash
mv /Users/user1/venv/nr_val/lib/python3.9/site-packages/nornir_utils/plugins/functions/print_result.py /Users/user1/venv/nr_val/lib/python3.9/site-packages/nornir_utils/plugins/functions/print_result.py_ORIG
cp bug_fixes/print_result.py /Users/user1/venv/nr_val/lib/python3.9/site-packages/nornir_utils/plugins/functions/print_result.py
```

## Running nornir-validate

Before being able to generate a meaningful compliance report you will need to edit the following elements, they are explained in more detail in the later sections.

- **input variables**: A yaml file (default *input_data.yml*) that holds the host and group variables that describe the desired state of the network
- **desired_state template:** A jinja template (default *desired_state.j2*) that is rendered using the input variables to create the desired state
- **actual_state python logic:** A python method (in *actual_state.py*) that creates a data structure from command outputs to be used as a comparison against the desired state

***nornir_validate*** can be run independently as a standalone script or imported into a script to use that scripts existing Nornir inventory.

### Standalone

When run as standalone *nornir_validate* creates its own Nornir inventory using the *config.yml* configuration file and the *hosts.yml*, *groups.yml* and *defaults.yml* files located in the *inventory* directory.

By default it uses an input variable file called  *input_data.yml* and the compliance report is not saved to file. Either of these can be changed in the variables section at the start of *nornir_template.py* or overridden using flags at runtime.

```python
input_file = "input_data.yml"
report_directory = None
```

| flag           | Description |
| -------------- | ----------- |
| `-f` or `--filename` | Overrides the value set in the *input_file* variable |
| `-d` or `--directory` | Overrides the value set in *directory* variable |

Specifying anything other than *None* for the *report_directory* will cause the compliance report to be saved in that location, the naming format is *hostname_compliance_report_YYYY-MM-DD.json*

```python
python nr_val.py
```

If the overall compliance report passes (all command validations comply) a message is returned to Nornir (can optionally save to file). If it does not comply or a validation was skipped (due to napalm_validate implementation error) the report is returned to Nornir as well as marking the Nornir task as failed.

<img src=https://user-images.githubusercontent.com/33333983/143948220-65f6745c-a67b-46ca-8791-39131f82ca32.gif  width="750" height="500">

### Imported

Rather than using the inventory in *nornir_validate* the ***validate_task*** function can be imported into a script to make use of an already existing nornir inventory. It is mandatory to specify the *input_file* argument, *directory* is only needed if you want to save the report to file.

```python
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_validate.nr_val import validate_task

nr = InitNornir(config_file="config.yml")
result = nr.run(task=validate_task, input_file="my_input_data.yml")
print_result(result)
```

## Input Variables

The input variable file holds the host_vars and group_vars that are rendered by the desired state template tp produce the desired state. It is made up of three optional dictionaries:

- **hosts:** Dictionary of host names each holding dictionaries of host-specific variables for the different features being validated
- **groups:** Dictionary of group names each holding dictionaries of group-specific variables for the different features being validated
- **all**: Dictionaries of variables for the different features being validated that are the same across all hosts

If there are any conflictions between the variables, *groups* take precedence over *all* and *hosts* over *groups*.

The host or group name must be an exact match of the host or group name within the nornir inventory. THe result of the below example will check the OSPF neighbors on *all* devices, ACLs on all hosts in the *ios* group and the port-channel state and port membership on host *HME-SWI-VSS01*.

```yaml
hosts:
  HME-SWI-VSS01:
    po:
      - name: Po2
        mode: LACP
        members: [Gi0/15, Gi0/16]
groups:
  ios:
    acl:
      - name: TEST_SSH_ACCESS
        ace:
          - { remark: MGMT Access - VLAN10 }
          - { permit: 10.17.10.0/24 }
          - { remark: Citrix Access }
          - { permit: 10.10.10.10/32 }
          - { deny: any }
      - name: TEST_SNMP_ACCESS
        ace:
          - { deny: 10.10.20.11 }
          - { permit: any }
all:
  ospf:
    nbrs: [192.168.255.1, 2.2.2.2]
```

## Desired state

The input variable file is rendered by a jinja template to produce a YAML formatted list if dictionaries with the key being the command and the value the desired output. *feature* matches the name of the features within the input file to make the rendering conditional. *strict* mode means that it has to be an exact match, no more or no less. This can be omitted if that is not a requirement.

```jinja
{% if feature == 'ospf' %}
- show ip ospf neighbor:
    _mode: strict
{% for each_nbr in input_vars.nbrs %}
    {{ each_nbr }}:
      state: FULL
{% endfor %}

{% elif feature == 'po' %}
- show etherchannel summary:
{% for each_po in input_vars %}
    {{ each_po.name }}:
      status: U
      protocol: {{ each_po.mode }}
      members:
{% for each_memeber in each_po.members %}
        _mode: strict
        {{ each_memeber }}:
          mbr_status: P
{% endfor %}{% endfor %}
{% endif %}
```

Below is an example of the YAML output after rendering the template with the example input variables.

```yaml
- show etherchannel summary:
    Po2:
      status: U
      protocol: LACP
      members:
        _mode: strict
        Gi0/15:
          mbr_status: P
        _mode: strict
        Gi0/16:
          mbr_status: P
- show ip ospf neighbor:
    _mode: strict
    192.168.255.1:
      state: FULL
    2.2.2.2:
      state: FULL
```

The resulting python object is generated from serialising the YAML output and is stored as host_var *desired_state* to be later compared against the actual state in the compliance report.

```python
{'show etherchannel summary': {'Po2': {'members': {'Gi0/15': {'mbr_status': 'P'},
                                                   'Gi0/16': {'mbr_status': 'P'},
                                                   '_mode': 'strict'},
                                       'status': 'U',
                                       'protocol': 'LACP'}},
 'show ip ospf neighbor': {'192.168.255.1': {'state': 'FULL'},
                           '2.2.2.2': {'state': 'FULL'},
                           '_mode': 'strict'}}
```

## Actual state

Netmiko is used to gather the command outputs and create a NTC textFSM formatted data model from them which are then passed into *actual_state.py* to convert them into a data structure that matches that of the desired state. Due to complexity in creating the data structure python logic rather than jinja templating is used to accomplish this.

Based on the *os_type* of the device (nornir *platform*) a dictionary of the *command* (key) and *command output* (value) are passed through an os_type specific method to a structured nested dictionary (dictionary of dictionaries) that matches the formatting of the desired state.

For example, the python logic to format the OSPF and port-channel looks like this.

```python
    if "show ip ospf neighbor" in cmd:
        for each_nhbr in output:
            tmp_dict[each_nhbr['neighbor_id']] = {'state': remove_char(each_nhbr['state'], '/')}
    elif "show etherchannel summary" in cmd:
        for each_po in output:
            tmp_dict[each_po['po_name']]['status'] = each_po['po_status']
            tmp_dict[each_po['po_name']]['protocol'] = each_po['protocol']
            po_mbrs = {}
            for mbr_intf, mbr_status in zip(each_po['interfaces'], each_po['interfaces_status']):
                po_mbrs[mbr_intf] = {'mbr_status': mbr_status}
            tmp_dict[each_po['po_name']]['members'] = po_mbrs
```

This will create an *actual_state* of:

```python
{'show etherchannel summary': {'Po3': {'members': {'Gi0/15': {'mbr_status': 'D'},
                                                   'Gi0/16': {'mbr_status': 'D'}},
                                       'protocol': 'LACP',
                                       'status': 'SD'}},
 'show ip ospf neighbor': {'192.168.255.1': {'state': 'FULL'},
                           '2.2.2.2': {'state': 'FULL'}}}
```

For each command the formatting will be different as the captured data is different, however the principle is same in terms of the structure. The command (*cmd*) and result (*tmp_dict*) are added to the *actual_state* dictionary and returned to be used along with the desired_state in the compliance_report.

## Validation builder

At the moment there are only example desired_state templates and actual_state python logic for IOS commands *show ip access-lists*, *show ip ospf neighbor* and *show etherchannel summary*. The *validation_builder* directory has a script to assist with building new validations, there is a README in this directory which give more details on running this.

1. run black on it to get formatting correct
2. proof read everything and code
3. enter PR for napalm
4. Publish on github



DONE THIS, BUT MAY mean issues with update_acl script
!!!! How to split desired and actual state in to device type specific and move cmds out of actual state !!!!
Move actual_state_engine to nornir_validate
move actual_state.py to templates, include OS-type when it is called, dont need to call different file per OS type, all in same file

5. Add to update_acl script and test (import it ratehr than runnign it if possible)
6. Change update ACL script to use netmiko
7. Run black on it.
8. Test it out at work
9.  Update Orion and write unit tests
10. run black on Orion
11. submit to Nornir


To run as import had to add followijng

need info about tiemp and need to make proper program later


import os
import sys
sys.path.insert(0, "nornir_validate")
from templates.actual_state import format_actual_state
from compliance_report import compliance_report


tmpl_path = os.path.join(os.getcwd(), "nornir_validate/templates/")
