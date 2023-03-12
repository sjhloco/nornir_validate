# Nornir Validate

Uses Nornir (with ***nornir-netmiko***) to gather and format device output before feeding this into ***napalm-validate*** in the form of the ***actual_state*** and ***desired_state*** to produce a ***compliance report***. As the name suggests I have not reinvented the wheel here, I just extended [*napalm_validate*](https://github.com/napalm-automation/napalm/blob/develop/napalm/base/validate.py) to validate on commands rather than getters to allow for the flexibility of validating any command output. The idea behind this project is to to validate network state based on input files of desired device states.

In short the script works in the following manner:

- **Input file:** The *desired state* is defined in YAML format and fed into the script at runtime
- **Desired state:** The *desired state* is rendered by Jinja adding the commands required for validation and saved as a *Nornir host_var*
- **Actual state:** *Netmiko* runs the commands against the devices parsing the outputs through *ntc-templates* before creating an *actual state* in the same format as the desired state
- **Compliance report:** The *desired state* and *actual state* are fed into *napalm_validate* compared creating a *compliance report* of the differences

## Current Validations

Validations are split up into *features* which each contain the *sub-features* that can be validated.

| Feature | Sub-feature | Description | Strict | IOS/ IOS-XE | NXOS | ASA | WLC | Palo |
| ------- | ----------- | ----------- | ------ | ----------- | ---- | --- | --- | ---- |
| system | image | Software version | ❌ | ✅ | ✅ | ✅ | ✅  | ❌
| system | mgmt_acl | Management ACLs | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| system | module | Model & status (implicit) | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| redundancy | ha_state | Local & peer state | ❌ | ✅ | ❌ | ✅ | ✅ | ❌
| redundancy | sw_stack | Switch, role, priority & state (implicit) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| neighbor | cdp | Neighbor name & port | ❌ | ✅ | ✅ | ❌ | ✅ | ❌
| neighbor | lldp | Neighbor name & port | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| intf_bonded | port-channel | Interface members (strict) & status (implicit) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| intf_bonded | vpc | VPC status (implicit), port-channels and VLANs (strict) | ✅ | ❌ | ✅ | ❌ | ❌ | ❌
| interface | intf | Port speed, duplex, type & status (implicit) | ❌ | ✅ | ✅ | ✅ | ✅ | ❌
| interface | switchport | Switchport mode & VLANs | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| interface | ip_brief | IP address & status (implicit) | ❌ | ✅ | ✅ | ✅ | ✅ | ❌
| layer2 | vlan | VLAN interfaces | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| layer2 | stp_vlan | Per-VLAN interfaces STP state (implicit FWD) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| layer2 | mac_table | Total & per-VLAN MAC count | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| fhr | hsrp | Interface, priority & state | ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| route_table | vrf | VRF interfaces | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| route_table | route_count | Per-VRF RT subnet count | ❌ | ✅ | ✅ | ✅ | ❌ | ❌
| route_table | route | Per-VRF route type and next-hops | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| route_protocol | eigrp_intf_nbr | Interfaces, neighbors of & state (implicit) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌
| route_protocol | ospf_intf_nbr | Interfaces, neighbors of & state (implicit) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| route_protocol | ospf_lsdb_count | Total LSAs per-OSPF process | ❌ | ✅ | ✅ | ✅ | ❌ | ❌
| route_protocol | bgp_peer | BGP peer, ASN and rcv_pfx | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
| fw | conn_count | Total conns | ❌ | ❌ | ❌ | ✅ | ❌ | ❌
| auth_session | mab_count| Total MAB Sessions | ❌ | ✅ | ❌ | ❌ | ❌ | ❌
| auth_session | dot1x_count| Total DOT1x Sessions | ❌ | ✅ | ❌ | ❌ | ❌ | ❌
| evpn | nve_vni | NVE L3VNI/ VRF or L2VNI/ BDI & state (implicit) |  ❌ | ✅ | ✅ | ❌ | ❌ | ❌
| evpn | nve_peer | NVE peers & state (implicit) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
| vpn | sts_peer | VPN peers & state (implicit) | ✅ | ✅ | ❌ | ✅ | ❌ | ❌
| vpn | ac_user | AnyConnect users, group-policy & tunnel-group | ❌ | ❌ | ❌ | ✅ | ❌ | ❌
| vpn | vpn_count | Total StS VPNs and/or AnyConnect users | ❌ | ✅ | ❌ | ✅ | ❌ | ❌
| wifi | wlan | WLAN ID, SSID, interface & status (implicit) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | ap | APs, model, IP & client count on each | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | client_count | Total clients per-WLAN | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | flexconnect | AP count per-flexconn groups | ❌ | ❌ | ❌ | ❌ | ✅ | ❌
| wifi | intf_grp | Interfaces, WLANs & APs per-group | ❌ | ❌ | ❌ | ❌ | ✅ | ❌

- **Integers (count):** Any output that is a numerical value (route table summary, MAC count, BGP prefixes, etc) can use an exact value (must be an integer), less than a value (*<15*), more than a value (*>15*), between a range (*10<->20*) or a tolerance percentage either side of a value (*10%15*)
- **Strict:** Strict validations (dict or list) must be of an exact match, no more, no less (like exact BGP peers)
- **implicit state:** Is expecting a certain state (like interfaces Up) rather than being manually defined in the validation file
- **Management ACL:** Allowed addresses for SSH and HTTP on ASA or an extended ACL on other platforms (assumes seq is 10, 20, etc)
- **Module:** Assumes an implicit status of *ok*, this can be overridden such as for *active* or *standby* on a nxos sup
- **Interface:* The speed and duplex don't need to be defined if a port doesn't have these properties (like a sub-interface)
- **Route table:** Next-hop can be a single address, strict list of multiple next-hops or the interface name for directly connected interfaces
- **OSPF:** A dictionary of interfaces with an optional strict list of neigbors (address not RID) off each interface (expected to be FULL, doesn't care about DR, BDR)
- **BGP:** For duplicate peers across different address-families the IPv4 address family entry is ignored and the other overlay address family validated (EVPN, MPLS VPN, etc)

## Installation and Prerequisites

Clone the repository, create a virtual environment and install the required python packages

```bash
git clone https://github.com/sjhloco/nornir_validate.git
python -m venv ~/venv/nr_val
source ~/venv/nr_val/bin/activate
cd nornir_validate/
pip install -r requirements.txt
```

Still waiting on the following NTC-template PRs to be approved before the following validations will work properly, will update *requirements.txt* once they have been merged.

- IOS: vpn.sts_peer - [#1308](https://github.com/networktocode/ntc-templates/pull/1308) to fix *show crpto detail* by adding support for IKEv2 parameters 
- IOS: show nve vni and nve peers - [#1304](https://github.com/networktocode/ntc-templates/pull/1304) to add *show nve vni* & *nve peers*
- NXOS: evpn.nve_vni & evpn.nve_peer - [#1303](https://github.com/networktocode/ntc-templates/pull/1303) to add *show nve vni* & *nve peers*
- NXOS: route_protocol.bgp_peer - [#1310](https://github.com/networktocode/ntc-templates/pull/1310) to fix *show ip bgp all summary vrf all* to show all address families

## Input Data

A compliance report is generated based on a YAML formatted file (default *input_data.yml*) describing the desired state of the network. The input data is structured around three dictionaries which can each hold all or a sub-section of features.

- **hosts:** Dictionary of host names each holding dictionaries of host-specific features being validated
- **groups:** Dictionary of group names each holding dictionaries of group-specific features being validated
- **all**: Dictionaries of variables for the different features being validated across all hosts

The host or group name must be an exact match of the host or group name within the nornir inventory. If there is a confliction between the features, *groups* take precedence over *all* and *hosts* over *groups*.

The result of the below example will check the port-channel state and port membership of *all* devices, the image version for devices in the *iosxe* group and the OSPF interfaces and neighbors on host *HME-RTR01*.

```yaml
all:
  intf_bonded:
    port_channel:
      Po2:
        protocol: LACP
        members: [Gi0/15, Gi0/16]
groups:
  iosxe:
    system:
      image: 16.6.2
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
```

Examples of validation the formatting for all of the features can be found in the *example_validations* directory.

## Compliance Report

The *desired_state* (from input file) and *actual_state* (from device) are iterated through ***napalm_validate*** to produces a per-feature compliance report. The features are grouped into an overall compliance report with the reports compliance status set to *false* if any of the individual features (and therefore sub-features) failed compliance.

In this example compliance report the image and port-channel passed but the report failed due to BGP peer 10.10.100.100 not being defined (is strict, no more or no less peers).

<img width="1552" alt="Screenshot 2023-02-28 at 22 03 40" src="https://user-images.githubusercontent.com/33333983/221991852-ed706526-51c0-4ae0-b286-a8441600b654.png">

## Running nornir_validate

*nr_val* can be run as a standalone script or imported into another project.

### Standalone

When run as standalone *nr_val* creates its own nornir inventory looking in the *inventory* directory for *hosts.yml*, *groups.yml* and *defaults.yml*.

By default the input data is gathered from *input_data.yml* and the compliance report not saved to file. Either of these can be changed in the variables section at the start of *nr_val.py* or overridden using runtime flags. Specifying anything other than *None* for the *report_directory* enables saving the compliance report with a name in the format of *hostname_compliance_report_YYYYMMDD-HHMM.json*

```python
INPUT_DATA = "input_data.yml"
REPORT_DIRECTORY = None
```

| Flag           | Description |
| -------------- | ----------- |
| `-f` or `--filename` | Override value set in *INPUT_DATA* variable to manually define the input data file |
| `-d` or `--directory` | Override value set in *REPORT_DIRECTORY* variable to save compliance reports to file |

```python
python nr_val.py -f my_validations.yml
```

If the validation fails a full compliance report will be printed to screen and the nornir task marked as failed.

![run_example_config](https://user-images.githubusercontent.com/33333983/222000867-84f2042f-902a-4697-9ec3-16425a667867.gif)

### Imported

The *nr_val* ***task_engine*** function can be imported directly into a script to make use of an existing nornir inventory and/or dynamically create the input data. When calling the imported function it is mandatory to specify the *input_data*, the *directory* is optional and only required if you want to save the report to file.

```python
from nornir import InitNornir
from nr_val import task_engine
from nornir_rich.functions import print_result

nr = InitNornir(config_file="config.yml")
result = nr.run(task=task_engine, input_data="input_data.yml")
print_result(result, vars=["result", "report_text"])
```

Rather than using a file the *input_data* can be a dictionary formatted in the same manner using *hosts*, *groups* and *all*.

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

- Add an input_data builder with the idea being that it is run against a device to automatically create the desired state validation file based off the current actual state.
- Package it up using poetry and add all relevant testing
- Move the documentation into [readthedocs](https://docs.readthedocs.io/en/stable/tutorial/#)

Add some new validations:

- Palo firewalls: Interfaces and routing rather than security policy based (*show high-availability all, show interface hardware, show interface logical, etc*)
- Cisco SD-WAN: Tunnel status (*show sdwan bfd summary, show sdwan control connections, show omp peers, show sdwan controller local properties*). Probably going to also need to create NTC templates

I may also look into replacing or extending napalm-validate as would be good to add support for:

- A web-based GUI
- Convert JSON report to HTML page something in the vain of the [Robot framework](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
