# Nornir Validate - v1

Uses Nornir (with ***nornir-netmiko***) to gather and format device output before feeding this into ***napalm-validate*** in the form of ***actual_state*** and ***desired_state*** to produce a ***compliance report***. The idea behind this project is to run pre and post checks on network devices based on an input file of the desired *device_state*.

As the name suggests I have not reinvented the wheel here, I just extended [*napalm_validate*](https://github.com/napalm-automation/napalm/blob/develop/napalm/base/validate.py) (importing the *napalm_validate compare* method) to validate on commands rather than getters to allow for the flexibility of validating any command output.

## Current Validations

| Feature | Sub-feature | Description | Validation | Strict | IOS/IOS-XE | NXOS | ASA | WLC | Palo
| ------- | ---------------------- | ------ | ---------- | ---- | --- | --- | ----
| system | image | software version number | ❌ | ✅ | ✅ | ✅ | ✅  | ❌
| system | mgmt_acl | Management ACLs (SSH/SNMP/HTTP) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| system | module | Module model and status (explicit) | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| redundancy | ha_state | Local and peer state | ❌ | ✅ | ❌ | ✅ | ✅ | ❌
| redundancy | sw_stack | Switch stack state (explicit), priority and role | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| neighbor | cdp | Neighbor device and port | ❌ | ✅ | ✅ | ❌ | ✅ | ❌
| neighbor | lldp | Neighbor device and port | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| intf_bonded | port-channel | Po strict membership & status (explicit) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| intf_bonded | vpc | VPC status (explicit), port membership and VLANs | ❌ | ❌ | ✅ | ❌ | ❌ | ❌
| interface | intf | Port speed, duplex, type and status (explicit) | ❌ | ✅ | ✅ | ✅ | ✅ | ❌
| interface | layer2 | Switchport mode and vlans | ❌ | ✅ | ✅ | ✅ | ✅ | ❌
| interface | ip_brief | Interface IP and status (explicit) | ❌ | ✅ | ✅ | ✅ | ✅ | ❌
| layer2 | vlan | Exact interfaces in VLANs | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| layer2 | stp_vlan | Spanning-tree interfaces state (explicit FWD) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌
| layer2 | mac_table | Total and per-VLAN MAC count | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| fhr | hsrp | HSRP interface, priority and state | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| route_table | vrf | VRF strict interface membership | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| route_table | route_count | total subnets in global or per-VRF | ❌ | ✅ | ✅ | ✅ | ❌ | ❌
| route_table | route | Per-VRF route type and strict next-hops | ✅ | ✅ | ✅ | ✅ | ❌ | ❌




| ospf | OSPF Interface (interfaces, area, cost) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| ospf | OSPF neighbors (neighbor, state) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| opsf | OSPF database (Total LSAs) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| eigrp | EIGRP Interface | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| eigrp | EIGRP neighbors | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| bgp | BGP peers (peer, asn, rcv_pfx) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌


| evpn | NVE VNI (L3VNI, VRF, BDI, state) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| evpn | NVE peer (L3VNI, peer, state) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| evpn | EVPN type2 MAC/IP table | ✅ | ✅ | ✅ | ❌ | ❌ | ❌              <<<<< think can have cmd output on ios-xe, must check
| vpn | VPN count of s-t-s, and ac | ❌ | ✅ | ❌ | ✅ | ❌ | ❌            <<<< need to add count of vpns up on ios-xe >>>>
| vpn | site-to-site tunnels (peer, interface, state) | ✅ | ✅ | ❌ | ✅
| vpn | AnyConnect tunnels (user and group) | ❌ | ❌ | ❌ | ✅ | ❌ | ❌
| sessions | MAB & DOT1X Auth Sessions (count) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| sessions | number of fw connectiosn | ❌ | ❌ | ❌ | ✅ | ❌ | ❌
| sessions | number wifi clients | ❌ | ❌ | ❌ | ❌ | ✅ | ❌

| wifi | WLANs (associated intf and SSID) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | APs (image, model, ip and clients) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | Interface groups (Interfaces and wlans) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | flexconnect groups (group and ap count) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌

- Integers (count): Any output that is a numerical value (like route table summary, MAC count, BGP received prefixes, etc) can use an exact value (must be an integer), less than a value ("<15"), more than a value (">15"), between a range ("10<->20") or tolerance percentage either side of a value ("10%15")
- Strict mode: Can be used to ensure of an exact match, no more, no less (for dictionaries or lists)
- Explicit states: This means that the state isnt manually entered in the vlaidate file rather that it is automatically  explixlty expected to be in a good state.
- Management ACL: Validation of the allowed management addresses for SSH and HTTP on ASA (including in source interface) or an extended ACL (IP and any port) on other platforms (assumes seq is 10, 20, etc)
- Module assumes it a status of 'ok', however unliek eoxplxit states thise can be overiden by defining a status (such as active or standby for nxos sup)
- Routing table: Uses a string for a single next-hop or a list if there are multiple next-hops




- BGP peers: If peers have same the IP uses those from the upper address family (for example with MPLS VPN will ignore IPv4 and only use VPNv4 peer)


<!-- | Validation | Strict | IOS/IOS-XE | NXOS | ASA | WLC | Palo
| ---------- | ------ | ---------- | ---- | --- | --- | ----------
| Image | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| Management ACL (SSH/SNMP/HTTP) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
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
| MAC address table (count) | ✅|  ✅  | ❌ | ❌ | ❌ | ❌
| MAB & DOT1X Auth Sessions (count) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| VRF (member interfaces) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| Route summary (total subnets) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| Routing table (route and strict next-hops) | ❌ |  ✅  | ❌ | ❌ | ❌ | ❌
| OSPF Interface (interfaces, area, cost) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| OSPF neighbors (neighbor, state) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| OSPF database (Total LSAs) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| EIGRP Interface | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| EIGRP neighbors | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| BGP peers (peer, asn, rcv_pfx) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| NVE VNI (L3VNI, VRF, BDI, state) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| NVE peer (L3VNI, peer, state) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌
| VPN (peer, interface, state) | ✅ |  ✅  | ❌ | ❌ | ❌ | ❌ -->


## Installation and Prerequisites

Clone the repository, create a virtual environment and install the required python packages

```bash
git clone https://github.com/sjhloco/nornir_validate.git
python -m venv ~/venv/nr_val
source ~/venv/nr_val/bin/activate
cd nornir_validate/
pip install -r requirements.txt
```

## Running nornir_validate

To generate a meaningful compliance report the following elements are needed:

- **input data (variables)**: Yaml file (default is *input_data.yml*) that holds the *host*, *group* and *all* data that describe the desired state of the network
- **desired_state template:** Jinja template (*desired_state.j2*) that is rendered with the input data to create the desired state
- **actual_state python logic:** Python method (*actual_state.py*) that creates a data structure from the command outputs to be used as a comparison against the desired state

*nornir_validate* can be run independently as a standalone script or imported to use a scripts existing nornir inventory.

### Standalone

When run as standalone *nornir_validate* creates its own nornir inventory (*config.yml*) looking in the *inventory* directory for *hosts.yml*, *groups.yml* and *defaults.yml*.

By default input data is gathered from *input_data.yml* and the compliance report not saved to file. Either of these can be changed in the variables section at the start of *nr_val.py* or overridden using runtime flags.

```python
input_data = "input_data.yml"
report_directory = None
```

| flag           | Description |
| -------------- | ----------- |
| `-f` or `--filename` | Override value set in *input_data* variable to manually define input data file |
| `-d` or `--directory` | Override value set in *directory* variable to save compliance reports to file |

Specifying anything other than *None* for the *report_directory* enables saving the compliance report in the format *hostname_compliance_report_YYYYMMDD-HHMM.json*

```python
python nr_val.py
```

If the validation fails a full compliance report will be printed to screen and the nornir task marked as failed.

<img src=https://user-images.githubusercontent.com/33333983/143948220-65f6745c-a67b-46ca-8791-39131f82ca32.gif  width="750" height="500">

### Imported

The ***validate_task*** function can be imported directly into a script to make use of an existing nornir inventory. When calling the imported function it is mandatory to specify the *input_data*, the *directory* is optional and only needed if you want to save the report to file.

```python
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_validate.nr_val import validate_task

nr = InitNornir(config_file="config.yml")
result = nr.run(task=validate_task, input_data="my_input_data.yml", directory='/Users/user1/reports')
print_result(result)
```

Rather than using a file the *input_data* can be a nested dictionary formatted in the same manner using *hosts*, *groups* and *all*.

```python
my_input_data = {"groups": {"ios": {"acl": [{"name": "TEST_SSH_ACCESS",
                                             "ace": [{"remark": "MGMT Access - VLAN10"},
                                                     {"permit": "10.17.10.0/24"}]}]}}}
result = nr.run(task=validate_task, input_data="my_input_data")
```

## Input Data

The input data structured around three dictionaries made up of features and the their desired state

- **hosts:** Dictionary of host names each holding dictionaries of host-specific features being validated
- **groups:** Dictionary of group names each holding dictionaries of group-specific features being validated
- **all**: Dictionaries of variables for the different features being validated across all hosts

The host or group name must be an exact match of the host or group name within the nornir inventory. If there is a confliction between the features, *groups* take precedence over *all* and *hosts* over *groups*.

The result of the below example will check the port-channel state and port membership of *all* devices, the image version for the *iosxe* group and the OSPF neighbors on host *HME-RTR01*.

```yaml
hosts:
  HME-RTR01:
    ospf_nbr:
      nbrs: [192.168.1.5, 2.2.2.2]
groups:
  iosxe:
    image: 16.6.2
all:
  port_channel:
    Po2:
      protocol: LACP
      members: [Gi0/15, Gi0/16]
```

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

## Compliance Report

The *desired_state* and *actual_state* are fed into ***compliance_report.py*** and iterated through ***napalm_validate*** (***validate.compare*** method) to produces a per-command compliance report. The commands are grouped into an overall compliance report with the reports compliance status set to *false* if any of the individual commands failed compliance.

In this example compliance report the image and port-channel passed but the report failed due to a missing OSPF neighbor (*1.1.1.1*).

```python
{ 'complies': False,
  'show etherchannel summary': { 'complies': True,
                                 'extra': [],
                                 'missing': [],
                                 'present': { 'Po1': { 'complies': True,
                                                       'nested': True}}},
  'show ip ospf neighbor': { 'complies': False,
                             'extra': [],
                             'missing': ['1.1.1.1'],
                             'present': { '10.90.10.2': { 'complies': True,
                                                          'nested': True}}},
  'show version': { 'complies': True,
                    'extra': [],
                    'missing': [],
                    'present': {'image': {'complies': True, 'nested': False}}},
  'skipped': []}
  ```

## TBC in the Future

Am still trialing this out, is a lot of work still to be done on adding differing platform commands and putting it through its paces in a real world environment. Like many of my other projects what seems like a great idea in my head could turn out in reality to not be much use in the real world. Only time will tell..........

I plan to do the following over the coming months:

- Finish adding each feature from the current validations table, already have majority of the information for them
- Redo unit tests fro the script as it has been changed a fair bit (also now more modular)
- Create new examples using rich for print result
- Rewrite readme and add new example video
- Add Palo commands, will be interfaces and routing rather than security policy based
- Add some Cisco SD-WAN comands to check tunnel status
- Possibly add support for genie, not sure where to put the toggle of whether to use netmiko or genie for a command - may not bother
- Package it up, use poetry and add unit testing

I may look into replacing or extending napalm-validate as would be good to add support for:

- Make it web-based
- Convert JSON report to HTML page something in the vain of the [Robot framework](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)

To allow me to fudge it to be able to import it as a module (due to inheritance) I added the following to *nr_val.py* that I need to remember to remove when it gets packaged up and check the validation_builder (as effects inheritance), don't forget.....

```python
sys.path.insert(0, "nornir_validate")

def return_template_path() -> str:
    if "validation_builder" in os.getcwd():
        tmpl_path = os.path.join(os.path.dirname(os.getcwd()), "feature_templates/")
    elif "nornir_validate" in os.getcwd():
        tmpl_path = "feature_templates/"
    else:
        tmpl_path = "nornir_validate/feature_templates/"
    return tmpl_path
```


## Adding a new Feature for Validation

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
        _mode: strict
        intf:
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

