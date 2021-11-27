# Nornir Validate

Uses Nornir to gather (*netmiko*) and format device output before feeding this into *napalm-validate* in the form of *actual_state* and *desired_state* to produce a *compliance report*. The idea behind this is to run pre and post checks on any devices within the network based and an input file of your desired network state.

As the name suggests I have not reinvented the wheel here, I have just extended *napalm_validate* to validate on commands rather than getters to allow for the flexibility of being able to validate on any command output. This is done by importing the *napalm_validate compare* method and feeding the desire_sate and actual_state manually. To understand what I am waffling about in this README you need to understand the following terms:

- **desired_state:** The state you expect the device to be in. For example you could expect that the device has certain BGP peers or all ports in all port-channels are up
- **actual_state:** This is the live state of the device gathered from connecting to and running commands on that device

## Installation and Prerequisites

Clone the repository and create a virtual environment

git clone https://github.com/sjhloco/nornir_validate.git
python -m venv ~/venv/nr_val
source ~/venv/nr_val/bin/activate

Install the packages

pip install -r firewall_policy_report/requirements.txt

Before being able to generate a compliance report the following three elements are needed:

- **input variables**: A yaml file (default *input_data.yml*) that holds the host and group variables that describe the desired state of that device. used by the desired state template to build the desired state of the device
- **desired_state template:** A jinja template (default *desired_state.j2*) that is rendered using the input variables to create the desired state of the device
- **actual_state python logic:** A python method (*actual_state.py*) that creates a data structure from the device command output that can be used as a comparison against the actual state

All of these will require building to fit the needs of your environment, these are explained in more detail in the later sections

## Run

*nornir_validate* can be run independently as a standalone script or imported into an existing script and use that scripts Nornir inventory.

### Standalone

Running *nornir_validate* independently will cause it to create its own Nornir inventory looking in the *nornir_validate* root directory for *config.yml* and the *inventory* directory for *hosts.yml*, *groups.yml* and *defaults.yml*)

By default it uses an input variable file called *input_data.yml* located in the the *nornir_template* directory and does not save the compliance report to file. Either of these can be changed in the variable section at the start of *nornir_template.py* or overridden by using flags ar runtime.

```python
input_file = "input_data.yml"
report_directory = None
```

| flag           | Description |
| -------------- | ----------- |
| -i or --filename | Overrides the value set in the *input_file* variable |
| -d or --directory | Overrides the value set in *directory* variable |

Specifying anything but *None* as the *report_directory* will cause the report to be saved in that location, the naming format will be *hostname_compliance_report_YYYY-MM-DD.json*

```python
python nornir_validate.py
```

### Imported

Rather than creating a new Nornir inventory nornir_inventory can be imported into an existing Nornir script to make use of an already existing Nornir inventory.

```python
from nornir_template import actual_state_engine

nr = InitNornir(config_file="config.yml")
result = nr.run(task=validate_task)
print_result(result)
```

If you wanted to changed the input file or directory either of these can be used as an function argument.

```python
result = nr.run(task=validate_task, input_file='/Users/user1/input_vars.yml', directory='/Users/user1/')
```








If the overall compliance report passes (all command validations comply) a message is returned to Nornir (optionally save to file). If it does not comply or a validation was skipped (due to napalm_validate implementation error) the report is returned to Nornir as well as marking the Nornir task as failed.




If the *directory* argument is passed in at nornir_validate runtime the report will also be saved to file as *'directory/hostname_compliance_report.json'*. The default action is to not save the report to file.



Any compliance failures are printed to screen, can also optionally save the full compliance report to file.












The input variable file is made up of three optional dictionaries. For any conflicting variables *groups* takes precedence over *all* and *hosts* over *groups*.

- **hosts:** Dictionary of host names each holding dictionaries of host-specific variables for the different features being validated
- **groups:** Dictionary of group names each holding dictionaries of group-specific variables for the different features being validated
- **all**: Dictionaries of variables for the different features being validated that are the same across all hosts

The host or group name must be an exact match of the host or group name within the nornir inventory. This below input file example will check the OSPF neighbors on *all* devices, the two ACLs on all devices in the *ios* group and the port-channel state and port member ship on the host *HME-SWI-VSS01*.

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

### Desired state

A YAML formatted data structure built from a template (with *nornir-template*) using data from the input variable file. The output us is not saved to file but still needs loading to serialise YAML and the output converted from a list of dicts *[cmd: {seq: ket:val}]* into a dictionary of cmds *{cmd: {seq: key:val}}*.

The formatting is the same as used with napalm_validate with lists of commands, so for example to check OSPF and port-channels from the above example the jinja template would be as follows. *feature* matches the name of the features within the input file. *strict* mode means that it has to be an exact match, no more or no less. This can be omitted if that is not a requirement.

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

Below is an example of what the YAML output after rendering the template with the example input variables. Note, the remarks are not checked as are not part of the command out from the device.

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

The resulting python object generated from serialising the YAML output is saved as the host_var *desired_state*.

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

### Actual state

The actual_state is the devices command output converted into a data structure that matches that of the desired state. Due to complexity in creating the data structure python logic rather than jinja templating is used to accomplish this. To allow for ease of expansion *actual_state.py* is split into three sections.

- ***Mini-functions:*** Functions used by any other functions for repeatable tasks to keep it DRY
- ***actual_state_engine:*** The engine that will run the specific actual state formatting function dependant on the devices OS
- ***os_type_formatting:*** Per-OS function to create the actual state file for all the commands for that specific device OS type

The *validate_task* function (in *nornir_validate.py*) passes the command output into *actual_state.py* as a dictionary with the *command* as the key and the *command output* as the value. The *actual_state_engine* function loops through the dictionary and passes both the key and value into the OS specific *os_type_formatting* function based on the OS type got from the Nornir *platform* host_var. The *command* (key) is matched upon and formatting applied on the *command output* (value) to create a structured nested dictionary (dictionary of dictionaries) that matches the desired state.

For example, the python logic to format the OSPF and port-channel:

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

will create the *actual_state* of:

```python
{'show etherchannel summary': {'Po3': {'members': {'Gi0/15': {'mbr_status': 'D'},
                                                   'Gi0/16': {'mbr_status': 'D'}},
                                       'protocol': 'LACP',
                                       'status': 'SD'}},
 'show ip ospf neighbor': {'192.168.255.1': {'state': 'FULL'},
                           '2.2.2.2': {'state': 'FULL'}}}
```

For each command the formatting will be different as the captured data is different, however the principle will be the same. The command (*cmd*) and result (*tmp_dict*) are added to the *actual_state* dictionary and returned to the engine.



Validation builder is other folder etc, etc

1. Add to github private, finish README and understand how works (test with importing)
2. Add unit tests
3. run black on it to get formatting correct
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