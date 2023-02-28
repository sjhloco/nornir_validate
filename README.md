# Nornir Validate

Uses Nornir (with ***nornir-netmiko***) to gather and format device output before feeding this into ***napalm-validate*** in the form of ***actual_state*** and ***desired_state*** to produce a ***compliance report***. The idea behind this project is to run pre and post checks on network devices based on an input file of the desired *device_state*.

As the name suggests I have not reinvented the wheel here, I just extended [*napalm_validate*](https://github.com/napalm-automation/napalm/blob/develop/napalm/base/validate.py) (importing the *napalm_validate compare* method) to validate on commands rather than getters to allow for the flexibility of validating any command output.

In short the script works in the following manner:

1. The *desired state* is defined in YAML format and fed into the script at run time
2. This is rendered by Jinja to add the commands needed to validate it and then saved as a *Nornir host_var*
3. *Netmiko* runs commands are run against the devices parsing the outputs through *ntc-templates* before creating an *actual state* that matches the formatting of the desired state
4. The Desired and actual state red into and compared by *napalm_validate* to create a *compliance report* of the differences

## Current Validations

Validations are split up into *features* that each contain the *sub-features* that can be validated.

| Feature | Sub-feature | Description | Validation | Strict | IOS/IOS-XE | NXOS | ASA | WLC | Palo
| ------- | ----------- | ----------- | ---------- | ------ | ---------- | ---- | --- | --- | ---
| system | image | Software version number | ❌ | ✅ | ✅ | ✅ | ✅  | ❌
| system | mgmt_acl | Management ACLs (SSH/SNMP/HTTP) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| system | module | Module model and status (explicit) | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| redundancy | ha_state | Local and peer state | ❌ | ✅ | ❌ | ✅ | ✅ | ❌
| redundancy | sw_stack | Switch stack state (explicit), priority and role | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| neighbor | cdp | CDP neighbor device and port | ❌ | ✅ | ✅ | ❌ | ✅ | ❌
| neighbor | lldp | LLDP neighbor device and port | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| intf_bonded | port-channel | Port-channel strict membership & status (explicit) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| intf_bonded | vpc | VPC status (explicit), port membership and VLANs | ❌ | ❌ | ✅ | ❌ | ❌ | ❌
| interface | intf | Switches port speed, duplex, type and status (explicit) | ❌ | ✅ | ✅ | ✅ | ✅ | ❌
| interface | layer2 | Switchport mode and vlans | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| interface | ip_brief | Interface IP and status (explicit) | ❌ | ✅ | ✅ | ✅ | ✅ | ❌
| layer2 | vlan | Exact interfaces in VLANs | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| layer2 | stp_vlan | Spanning-tree interfaces state (explicit FWD) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| layer2 | mac_table | Total and per-VLAN dynamic MAC count | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| fhr | hsrp | HSRP interface, priority and state | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| route_table | vrf | VRF strict interface membership | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| route_table | route_count | total subnets in global or per-VRF | ❌ | ✅ | ✅ | ✅ | ❌ | ❌
| route_table | route | Per-VRF route type and strict next-hops | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| route_protocol | eigrp_intf_nbr: | Interfaces and list (strict) of neighbors and state (explicit) off them | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| route_protocol | ospf_intf_nbr | Interfaces and list (strict) of neighbors (address not rid) and state (explicit) off them | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| route_protocol | ospf_lsdb_count | Total LSAs per-ospf process | ❌ | ✅ | ✅ | ✅ | ❌ | ❌
| route_protocol | bgp_peer | BGP peer, asn and rcv_pfx or state | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| fw | conn_count | Total number of connections | ❌ | ❌ | ❌ | ✅ | ❌ | ❌
| auth_session | mab_count| Total number of MAB Sessions | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| auth_session | dot1x_count| Total number of DOT1X Sessions | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| evpn | nve_vni | NVE L3VNI and VRF or L2VNI and BDI, and state (explicit) |  ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| evpn | nve_peer | NVE peers and state (explicit) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| vpn | sts_peer | List of site-to-site VPN peers and state (explicit) | ✅ | ✅ | ❌ | ✅ | ❌ | ❌
| vpn | ac_client | AnyConnect users with group-policy and tunnel-group | ❌ | ❌ | ❌ | ✅ | ❌ | ❌
| vpn | vpn_count | Total VPN count for site-to-site peers and AnyConnect users | ❌ | ✅ | ❌ | ✅ | ❌ | ❌
| wifi | wlan | WLAN ID, SSID, associated intf and status (explicit) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | ap | List of APs, model, IP and the number of clients on each | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | client_count | Total and per-wlan number of wifi clients | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | flexconnect | List of flexconnect groups and ap count for each | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | intf_grp | Number of interfaces, WLANs and APs per interface group | ❌ | ❌ | ❌ | ❌ | ✅ | ❌

- Integers (count): Any output that is a numerical value (like route table summary, MAC count, BGP received prefixes, etc) can use an exact value (must be an integer), less than a value (*"<15"*), more than a value (*">15"*), between a range (*"10<->20"*) or a tolerance percentage either side of a value (*"10%15"*)
- Strict mode: Any strict validations (dictionaries or lists) must be of an exact match, no more, no less (like exact BGP peers)
- Explicit states: The state is not manually entered in the validate file, rather that is automatically explictly expected to be in a certain state (like interfaces Up)
- Management ACL: Allowed addresses for SSH and HTTP on ASA (includes source zone) or an extended ACL (IP and any port) on other platforms (assumes seq is 10, 20, etc)
- Module: Although it assumes it a status of *ok*, unlike other explicit states this can be overridden (such as active or standby for nxos sup)
- Interface: The speed and duplex dont need to be defiend if a port doesnt have them, such asa  virtual port
- Routing table: Use a string for a single next-hop or a list if there are multiple next-hops. Directly connected interfaces use the interface as the next-hop
- EIGRP and OSPF: A dictionary of interfaces with an optional strict list of neigbors (address not RID) off each interface. OSPF neighbors are expected to be FULL, doesn't care about DR, BDR, etc
- BGP peers: If there are duplicate peers the IPv4 address family entry will be ignored and the other overlay address family will be validated (like with EVPN or MPLS VPN)

## Installation and Prerequisites

Clone the repository, create a virtual environment and install the required python packages

```bash
git clone https://github.com/sjhloco/nornir_validate.git
python -m venv ~/venv/nr_val
source ~/venv/nr_val/bin/activate
cd nornir_validate/
pip install -r requirements.txt
```

## Input Data

To generate a meaningful compliance report a YAML formatted input file is needed (default is *input_data.yml*) that holds all the data that describes the desired state of the network. The input data is structured around three dictionaries which can hold a sub-section or all of the features and sub-features.

- **hosts:** Dictionary of host names each holding dictionaries of host-specific features being validated
- **groups:** Dictionary of group names each holding dictionaries of group-specific features being validated
- **all**: Dictionaries of variables for the different features being validated across all hosts

The host or group name must be an exact match of the host or group name within the nornir inventory. If there is a confliction between the features, *groups* take precedence over *all* and *hosts* over *groups*.

The result of the below example will check the port-channel state and port membership of *all* devices, the image version for the *iosxe* group and the OSPF interfaces and neighbors on host *HME-RTR01*.

```yaml
hosts:
  HME-RTR01:
    route_protocol:
      ospf_intf_nbr:
        Gi1/1:
          pid: 1
          area: 0
        Vl120:
          pid: 1
          area: 0
          nbr: [192.168.10.2, 192.168.10.3]
groups:
  iosxe:
    system:
      image: 16.6.2
all:
  intf_bonded:
    port_channel:
      Po2:
        protocol: LACP
        members: [Gi0/15, Gi0/16]
```

The *example_validations* directory has examples of the formatting for all of the possible validations.

## Compliance Report

The *desired_state* (got from input file) and *actual_state* (got from devices) are fed into ***compliance_report.py*** and iterated through ***napalm_validate*** (***validate.compare*** method) to produces a per-feature compliance report. The features are grouped into an overall compliance report with the reports compliance status set to *false* if any of the individual features (and therefore sub-features) failed compliance.

In this example compliance report the image and port-channel passed but the report failed due to BGP peer 10.10.254.3 not being defined (as is strict, no more, no less).

!!!!!! amy use image instead (saved to desktop)

```python
                complies = False
intf_bonded.port_channel = {'complies': True, 'present': {'Po1': {'complies': True, 'nested': True}}, 'missing': [], 'extra': []}
 route_protocol.bgp_peer = {
                               'complies': False,
                               'present': {
                                   '10.10.254.2': {'complies': True, 'nested': True},
                                   '10.10.254.10': {'complies': True, 'nested': True}
                               },
                               'missing': [],
                               'extra': ['10.10.254.3']
                           }
            system.image = {'complies': True, 'present': {'image': {'complies': True, 'nested': False}}, 'missing': [], 'extra': []}
```

## Running nornir_validate

*nornir_validate* can be run independently as a standalone script or imported into another project and use that scripts existing nornir inventory.

### Standalone

When run as standalone *nornir_validate* creates its own nornir inventory (*config.yml*) looking in the *inventory* directory for *hosts.yml*, *groups.yml* and *defaults.yml*.

By default input data is gathered from *input_data.yml* and the compliance report not saved to file. Either of these can be changed in the variables section at the start of *nr_val.py* or overridden using runtime flags. Specifying anything other than *None* for the *report_directory* enables saving the compliance report in the format *hostname_compliance_report_YYYYMMDD-HHMM.json*

```python
INPUT_DATA = "input_data.yml"
REPORT_DIRECTORY = None
```

| flag           | Description |
| -------------- | ----------- |
| `-f` or `--filename` | Override value set in *input_data* variable to manually define input data file |
| `-d` or `--directory` | Override value set in *directory* variable to save compliance reports to file |

```python
python nr_val.py
```

If the validation fails a full compliance report will be printed to screen and the nornir task marked as failed.

<img src=https://user-images.githubusercontent.com/33333983/143948220-65f6745c-a67b-46ca-8791-39131f82ca32.gif  width="750" height="500">

### Imported

The nr_val ***task_engine*** function can be imported directly into a script to make use of an existing nornir inventory and/or dynamically created input data. When calling the imported function it is mandatory to specify the *input_data*, the *directory* is optional and only needed if you want to save the report to file.

```python
from nornir import InitNornir
from nr_val import task_engine
from nornir_rich.functions import print_result

nr = InitNornir(config_file="config.yml")
result = nr.run(task=task_engine, input_data="input_data.yml")
print_result(result, vars=["result", "report_text"])
```

Rather than using a file the *input_data* can be a nested dictionary formatted in the same manner using *hosts*, *groups* and *all*.

```python
my_input_data = {"groups": {"ios": {"acl": [{"name": "TEST_SSH_ACCESS",
                                             "ace": [{"remark": "MGMT Access - VLAN10"},
                                                     {"permit": "10.17.10.0/24"}]}]}}}
my_input_data = {"groups": {"ios": {"intf_bonded": {"port_channel": {"Po1": {"protocol": "LACP", 
                                                                     "members": ["Gi0/2", "Gi0/3"]}}}}}}
result = nr.run(task=task_engine, input_data=my_input_data)
```

## TBC in the Future

This project is still a work in progress, am planning on doing the following over the coming months:

- Redo unit tests *test_nr_val.py* as the recent remodelling will have broken a lot of them
- Tidy up *ADD_NEW_FEATURE.md* which documents the process for anyone wishing to add new validations
- Add to nr_val an input_data builder with the idea being that to run it against a device and create the desired state validation file from a devices current actual state.
- Package it up using poetry and add all relevant testing
- Move the documentation into [readthedocs](https://docs.readthedocs.io/en/stable/tutorial/#)

Add some new validations for:

- Palo firewalls: Interfaces and routing rather than security policy based (*show high-availability all, show interface hardware, show interface logical, etc*)
- Cisco SD-WAN (will probably also need NTC templates): Tunnel status (*show sdwan bfd summary, show sdwan control connections, show omp peers, show sdwan controller local properties*)

I may also look into replacing or extending napalm-validate as would be good to add support for:

- Make it web-based
- Convert JSON report to HTML page something in the vain of the [Robot framework](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
