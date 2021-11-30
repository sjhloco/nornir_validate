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

If the validation check fails the full compliance report will be printed to screen and the task marked as failed in Nornir.

<img src=https://user-images.githubusercontent.com/33333983/143948220-65f6745c-a67b-46ca-8791-39131f82ca32.gif  width="750" height="500">

### Imported

Rather than using the inventory in *nornir_validate* the ***validate_task*** function can be imported into a script to make use of an already existing nornir inventory.

```python
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_validate.nr_val import validate_task

nr = InitNornir(config_file="config.yml")
result = nr.run(task=validate_task, input_file="my_input_data.yml")
print_result(result)
```

As arguments within this function it is mandatory to specify the *input_file*, the *directory* is optional as only needed if you want to save the report to file.

```python
result = nr.run(task=validate_task, input_file="my_input_data.yml", directory='/Users/user1/reports')
```

## Input Variables

The input variable file holds the *host_vars* and *group_vars* which are made up of dictionaries of features and their values. It is made up of three optional dictionaries:

- **hosts:** Dictionary of host names each holding dictionaries of host-specific variables for the different features being validated
- **groups:** Dictionary of group names each holding dictionaries of group-specific variables for the different features being validated
- **all**: Dictionaries of variables for the different features being validated across all hosts

The host or group name must be an exact match of the host or group name within the nornir inventory. If there are any conflictions between the variables, *groups* take precedence over *all* and *hosts* over *groups*.

THe result of the below example will check the OSPF neighbors on *all* devices, ACLs on all hosts in the *ios* group and the port-channel state and membership on host *HME-SWI-VSS01*.

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

The input variable file (***input_data.yml***) is rendered by a jinja template (***desired_state.j2***) to produce a YAML formatted list of dictionaries with the key being the command and the value the desired output. ***feature*** matches the name of the features within the input file to make the rendering conditional.\
*strict* mode means that it has to be an exact match, no more, no less, this can be omitted if that is not a requirement.

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

The resulting python object is generated by serialising the YAML output and is stored as a host_var (data dictionary) called *desired_state* for that host.

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

Netmiko is used to gather the command outputs and create TextFSM formatted data-models using *ntc-templates*. This is fed into ***actual_state.py*** where a dictionary of the *command* (key) and *command output* (value) are passed through an *os_type* (based on nornir *platform*) specific method to create a nested dictionary (dictionary of dictionaries) which matches the structure of the desired state.

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

For each command the formatting will be different as the captured data is different, however the principle is same in terms of the structure.

## Compliance report

The desired_state and actual_state are fed into ***compliance_report.py*** which iterates through them feeding the command outputs into ***napalm_validate*** (its *validate.compare* method) which produces a per_command compliance report (complies true of false). All the commands are then grouped into an overall complaince report and the reports compliance status decided based on the individual commands compliance.

This example shows a failed compliance report where the ACLs passed but OSPF failed due to a missing OSPF neighbor (2.2.2.2.)

```json
{ 'complies': False,
  'show ip access-lists TEST_SNMP_ACCESS': { 'complies': True,
                                             'extra': [],
                                             'missing': [],
                                             'present': { '10': { 'complies': True,
                                                                  'nested': True},
                                                          '20': { 'complies': True,
                                                                  'nested': True}}},
  'show ip access-lists TEST_SSH_ACCESS': { 'complies': True,
                                            'extra': [],
                                            'missing': [],
                                            'present': { '10': { 'complies': True,
                                                                 'nested': True},
                                                         '20': { 'complies': True,
                                                                 'nested': True},
                                                         '30': { 'complies': True,
                                                                 'nested': True}}},
  'show ip ospf neighbor': { 'complies': False,
                             'extra': [],
                             'missing': ['2.2.2.2'],
                             'present': { '192.168.255.1': { 'complies': True,
                                                             'nested': True}}},
  'skipped': []}
  ```

## Validation builder

At the moment there are only example desired_state templates and actual_state python logic for IOS commands *show ip access-lists*, *show ip ospf neighbor* and *show etherchannel summary*. The *validation_builder* directory has a script to assist with building new validations, there is a README in this directory which give more details on running this.

## Future



This the first build of this to get the structure correct, is still a lot of work to be done on adding more commands to validate and put it through its passes a real world environment. If could still could like many of my other projects, what seems a great idea at the time in reality turns out to be not much use in the real world.

If it turns out to be of any use I plan to do the following over the coming months:

- Add Lots more commands to the actual_state.py and desired_state.j2. Have already setup unit-testing for the project so shouldnt be too bad to keep track of these.
- Once happy with the amount of base commands add a layer of abstraction for actual_state.py and desired_state.j2 so these can be fed in when it is imported into another script
- Package it up as hopefully with the abstraction of actual_state.py, desired_state.j2 and input variables should be no need to make changes to the main code. Never done so needs a bot of research as seems more involved with adding unit tests and format checking as part of it.
- Drink a few beers
- Maybe look at how to add as a nornir pluggin

To allow me to fudge it to be able to import it as a module (due to inheritance) I added the following which have got to remember to remove when it gets packaged up:


```python
import os
import sys
sys.path.insert(0, "nornir_validate")

    if "nornir_validate" in os.getcwd():
        tmpl_path = "templates/"
    else:
       tmpl_path =  "nornir_validate/templates/"
```
