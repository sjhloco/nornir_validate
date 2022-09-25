# Nornir Validate

Uses Nornir (with ***nornir-netmiko***) to gather and format device output before feeding this into ***napalm-validate*** in the form of ***actual_state*** and ***desired_state*** to produce a ***compliance report***. The idea behind this is for running pre and post checks on network devices based and an input file of the desired *device_state*.

As the name suggests I have not reinvented the wheel here, I have just extended *napalm_validate* to validate on commands rather than getters to allow for the flexibility of validating any command output. This is done by importing the *napalm_validate compare* method and feeding in to it the *desire_state* and *actual_state* manually. To get what I am waffling on about you need to understand the following terms:

- **desired_state:** The state you expect the device to be in. For example, you could expect that the device has certain OSPF neighbors, specific CDP neighbors or that all ports in a port-channel are up
- **actual_state:** This is real-time state of the device gathered by connecting to it and scraping the output of show commands

## Current Validations

This documents what validations are available for the different device types.

| Validation | Strict | IOS/IOS-XE | NXOS | ASA | WLC | Checkpoint
| ---------- | ------ | ---------- | ---- | --- | --- | ----------
| Image | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| Management ACL (SSH/SNMP/HTTP)* | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| Port-channel (membership & status) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| Interface brief (IP and status) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| CDP neighbors | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| LLDP neighbors | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| HSRP (priority and state) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| Switch stack (state and priority) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| VSS HA state | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| Interface status (speed, duplex, status) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| Switchport (mode and vlan) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| VLANs (member interfaces) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| Spanning-Tree (FWD vlan interfaces) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| VRF (member interfaces) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| Route summary (total subnets) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| Route (route and next-hop) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| VRF Route summary (total subnets) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| VRF Route (route and next-hop) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| OSPF Interface (interfaces, area, cost) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| OSPF neighbors (neighbor, state) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| OSPF database (Total LSAs) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| EIGRP Interface | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| EIGRP neighbors | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| BGP peers (peer, asn, rcv_pfx) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| NVE VNI (L3VNI, VRF, BDI, state) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| NVE peer (L3VNI, peer, state) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| VPN (peer, interface, state) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌

*Management ACL is a very basic extended ACL (does not work with standard) validation looking at the source IP and action (non-ASA) or interface (ASs). On ASAs it is the allowed list for SSH and HTTP whilst on all other platforms is the ACL governing SSH and SNMP access.

## Installation and Prerequisites

Clone the repository, create a virtual environment and install the required python packages

```bash
git clone https://github.com/sjhloco/nornir_validate.git
python -m venv ~/venv/nr_val
source ~/venv/nr_val/bin/activate
cd nornir_validate/
pip install -r requirements.txt
```

I have had to use the develop branch of *nornir-netmiko* as it doesn't yet support *netmiko 4.0.0* which I needed as it has a fix for this [ntc-templates parsing in netmiko](https://github.com/ktbyers/netmiko/pull/2274) bug.

### Caveats

If you using the IOS command *show_interfaces_status* and an interface in a port-channel is *suspended* the script will fail as it is missing from the NTC template (*cisco_ios_show_interfaces_status*) as per this closed [bug](https://github.com/networktocode/ntc-templates/issues/1021). I haven't got round to doing a PR yet so as a workaround you can edit the *~/venv/nr_val/lib/python3.9/site-packages/ntc_templates/templates/cisco_ios_show_interfaces_status.textfsm* file (replace your virtual env at start) and add *suspended* to the end of this *Value STATUS* line.

```python
Value STATUS (err-disabled|disabled|connected|notconnect|inactive|up|down|monitoring)
```

Due to the way that the *napalm_validate* matching works if can miss some things if there are common values. For example with the number of routes if the desired number is 5 and the actual number is 15 this will pass as it looks if 5 is in 15 rather than an exact match. Not sure if this is by design, at end of the day I am using it for a more expanded purpose so need to look how it performs normally before seeing if I can fix it.

## Running nornir_validate

Before being able to generate a meaningful compliance report you will need to edit the following elements, they are explained in more detail in the later sections.

- **input data (variables)**: A yaml file (default *input_data.yml*) that holds the *host*, *group* and *all* (all devices) variables that describe the desired)state of the network
- **desired_state template:** A jinja template (*desired_state.j2*) that is rendered with the input variables to create the desired state
- **actual_state python logic:** A python method (in *actual_state.py*) that creates a data structure from the command outputs to be used as a comparison against the desired state

***nornir_validate*** can be run independently as a standalone script or imported into a script to use that scripts existing nornir inventory.

### Standalone

When run as standalone *nornir_validate* creates its own nornir inventory using the *config.yml* configuration file and looks in the *inventory* directory for the *hosts.yml*, *groups.yml* and *defaults.yml* files.

By default input data is gathered from *input_data.yml* and the compliance report is not saved to file. Either of these can be changed in the variables section at the start of *nornir_template.py* or overridden using flags at runtime.

```python
input_data = "input_data.yml"
report_directory = None
```

| flag           | Description |
| -------------- | ----------- |
| `-f` or `--filename` | Overrides the value set in the *input_data* variable to manually define input data file |
| `-d` or `--directory` | Overrides the value set in *directory* variable to save compliance reports to file |

Specifying anything other than *None* for the *report_directory* enables saving the compliance report, the naming format is *hostname_compliance_report_YYYYMMDD-HH:MM.json*

```python
python nr_val.py
```

If the validation fails a full compliance report will be printed to screen and the nornir task marked as failed.

<img src=https://user-images.githubusercontent.com/33333983/143948220-65f6745c-a67b-46ca-8791-39131f82ca32.gif  width="750" height="500">

### Imported

Rather than using the inventory in *nornir_validate* the ***validate_task*** function can be imported into a script to make use of an already existing nornir inventory.

```python
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_validate.nr_val import validate_task

nr = InitNornir(config_file="config.yml")
result = nr.run(task=validate_task, input_data="my_input_data.yml")
print_result(result)
```

Rather than using a file the *input_data* can be a nested dictionary formatted in the same manner (*hosts*, *groups*, *all* dictionaries).

```python
my_input_data = {"groups": {"ios": {"acl": [{"name": "TEST_SSH_ACCESS",
                                             "ace": [{"remark": "MGMT Access - VLAN10"},
                                                     {"permit": "10.17.10.0/24"}]}]}}}
result = nr.run(task=validate_task, input_data="my_input_data")
```

When calling the imported function it is mandatory to specify the *input_data*, the *directory* is still optional as is only needed if you want to save the report to file.

```python
result = nr.run(task=validate_task, input_data="my_input_data.yml", directory='/Users/user1/reports')
```

## Input Data

The input data (variable) file holds the *host_vars* and *group_vars* which are made up of dictionaries of features and their values. It is structured around these three optional dictionaries, it must have one of them:

- **hosts:** Dictionary of host names each holding dictionaries of host-specific variables for the different features being validated
- **groups:** Dictionary of group names each holding dictionaries of group-specific variables for the different features being validated
- **all**: Dictionaries of variables for the different features being validated across all hosts

The host or group name must be an exact match of the host or group name within the nornir inventory. If there are any conflictions between the variables, *groups* take precedence over *all* and *hosts* over *groups*.

The result of the below example will check the OSPF neighbors on *all* devices, ACLs on all hosts in the *ios* group and the port-channel state and port membership on host *HME-SWI-VSS01*.

```yaml
hosts:
  HME-SWI-VSS01:
    port_channel:
      Po2:
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

## Desired State

The input file (***input_data.yml***) is rendered by a jinja template (***desired_state.j2***) to produce a YAML formatted list of dictionaries with the key being the command and the value the desired output. The top level Jinja condition is for the os_type (got from nornir *platform*), each os_type has templating for the features tested.

***feature*** matches the name of the features within the input file to make the rendering conditional. ***strict*** mode means that it has to be an exact match, no more, no less. This can be omitted if that is not a requirement.

```jinja
{% if 'ios' in os_type |string %}
{% if feature == 'ospf' %}
- show ip ospf neighbor:
    _mode: strict
{% for each_nbr in input_vars.nbrs %}
    {{ each_nbr }}:
      state: FULL
{% endfor %}

{% elif feature == 'port_channel' %}
- show etherchannel summary:
{% for each_po_name, each_po_info in input_vars.items() %}
    {{ each_po_name }}:
      status: U
      protocol: {{ each_po_info.mode }}
      members:
        _mode: strict
{% for each_member in each_po_info.members %}
        {{ each_member }}:
          mbr_status: P
{% endfor %}{% endfor %}

{% endif %}
{% endif %}
```

Below is an example of the YAML output after rendering the template with the example input data.

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

The resulting python object is generated by serialising the YAML output and is stored as a host_var (nornir *data* dictionary) called *desired_state* for that host. This is the same structure that the *actual_state* will be in.

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

## Actual State

Netmiko is used to gather the command outputs and create TextFSM formatted data-models using *[ntc-templates](https://github.com/networktocode/ntc-templates/tree/master/ntc_templates/templates)*. This is fed into ***actual_state.py*** where a dictionary of the *command* (key) and *command output* (value) are passed through an *os_type* (based on nornir *platform*) specific method to create a nested dictionary that matches the structure of the *desired_state*.

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

The resulting *actual_state* is the same as the *desired_state* except for the absence of the *'_mode': 'strict'* dictionary.

```python
{'show etherchannel summary': {'Po3': {'members': {'Gi0/15': {'mbr_status': 'D'},
                                                   'Gi0/16': {'mbr_status': 'D'}},
                                       'protocol': 'LACP',
                                       'status': 'SD'}},
 'show ip ospf neighbor': {'192.168.255.1': {'state': 'FULL'},
                           '2.2.2.2': {'state': 'FULL'}}}
```

For each command the formatting will be different as the captured data is different, however the principle is same in terms of the structure.

## Compliance Report

The *desired_state* and *actual_state* are fed into ***compliance_report.py*** which iterates through them feeding the command outputs into ***napalm_validate*** (its ***validate.compare*** method) which produces a per-command compliance report (complies *true* of *false*). All the commands are grouped into an overall compliance report with the reports compliance status set to *false* if any of the individual commands fail compliance.

This example shows a failed compliance report where the ACLs passed but OSPF failed due to a missing OSPF neighbor (*2.2.2.2*).

```python
{ 'complies': False,
  'show ip access-lists TEST_SSH_ACCESS': { 'complies': True,
                                            'present': { 'TEST_SSH_ACCESS': { 'complies': True,
                                                                              'nested': True}},
                                            'missing': [],
                                            'extra': []},
  'show ip ospf neighbor': { 'complies': False,
                             'extra': [],
                             'missing': ['2.2.2.2'],
                             'present': { '192.168.255.1': { 'complies': True,
                                                             'nested': True}}},
  'skipped': []}
  ```

## Validation Builder

 The *validation_builder* directory has a script with different runtime flags to assist with the building of new validations, have a look at the README in this directory for full details on how to use this.

## Future

This the first build of this project to get the structure of the base components correct. There is still a lot of work to be done on adding more commands to validate and putting it through its paces in a real world environment. Like many of my other projects what seems like a great idea in my head could turn out in reality to not be much use in the real world. Only time will tell..........

I plan to do the following over the coming months:

- Test out a lot of the IOS validations in a proper real-world environment (very basic lab test done so far)
- Look into napalm_validate see if the looseness of the regex search misses matches there, if so try and fix and raise a PR
- Add NXOS commands to cover the majority of IOS/IOS-XE commands and other NXOS only cmds. Not sure if will use TextFSM or native NXOS JSON cmds, where possible use common python functions (actual state) or jinja macros (desired state)to keep it DRY.
- Add ASA commands, will be interfaces, routing and VPN
- Add WLC commands, will be interfaces and APs
- Add Checkpoint commands, will be interfaces and routing
- Add support for genie, not sure where you put the toggle of whether to use netmiko pr genie for a command
- Look into if it is possible to convert JSON report to HTML page something in the vain of the [Robot framework](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
- Maybe look at what is involved to add it as a nornir plugin
- Package it up, need to make it easy to extend (abstraction of actual_state.py and desired_state.j2) so will not be as much need to make changes to the base code

To allow me to fudge it to be able to import it as a module (due to inheritance) I added the following to *nr_val.py* that I need to remember to remove when it gets packaged up and check validation_builder (as effects inheritance), don't forget.....

```python
import os
import sys
sys.path.insert(0, "nornir_validate")

    if "nornir_validate" in os.getcwd():
        tmpl_path = "templates/"
    else:
       tmpl_path =  "nornir_validate/templates/"
```
