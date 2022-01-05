from typing import Dict, List
import ipaddress
from collections import defaultdict
import re

# ----------------------------------------------------------------------------
# Engine to run different formatters
# ----------------------------------------------------------------------------
def format_actual_state(
    os_type: str,
    cmd: str,
    output: List,
    tmp_dict: Dict[str, None],
    actual_state: Dict[str, None],
) -> Dict[str, Dict]:
    if bool(re.search("ios", str(os_type))):
        iosxe_format(cmd, output, tmp_dict, actual_state)
    elif bool(re.search("nxos", str(os_type))):
        nxos_format(cmd, output, tmp_dict, actual_state)
    elif bool(re.search("asa", str(os_type))):
        asa_format(cmd, output, tmp_dict, actual_state)
    return actual_state


# ----------------------------------------------------------------------------
# Mini-functions used by all OS types to keep DRY
# ----------------------------------------------------------------------------
# ACL_FORMAT: Removes all the empty dictionaries from ACL list of dicts
def acl_format(input_acl: List) -> List:
    acl: List = []
    for each_acl in input_acl:
        tmp_acl = {}
        for ace_key, ace_val in each_acl.items():
            if len(ace_val) != 0:
                tmp_acl[ace_key] = ace_val
        acl.append(tmp_acl)
    return acl


# ACL_ADDR: Converts addressing into address/prefix
def acl_scr_dst(each_ace: Dict[str, str], src_dst: str) -> str:
    if each_ace.get(src_dst + "_network") != None:
        addr = each_ace[src_dst + "_network"] + "/" + each_ace[src_dst + "_wildcard"]
        return ipaddress.IPv4Interface(addr).with_prefixlen
    elif each_ace.get(src_dst + "_host") != None:
        return ipaddress.IPv4Interface(each_ace[src_dst + "_host"]).with_prefixlen
    else:
        return each_ace[src_dst + "_any"]


# REMOVE: Removes the specified character and anything after it
def remove_char(input_data: str, char: str) -> str:
    if char in input_data:
        return input_data.split(char)[0]
    else:
        return input_data


# ----------------------------------------------------------------------------
# IOS/IOS-XE desired state formatting
# ----------------------------------------------------------------------------
def iosxe_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:
    # MGMT_ACL: Creates ACL dicts in the format [{acl_name: {seq_num: {protocol: ip/tcp/udp, src: src_ip, dst: dst_ip, dst_port: port}]
    if "show ip access-lists" in cmd:
        acl = acl_format(output)
        tmp_dict1 = defaultdict(dict)
        for each_ace in acl:
            # Creates dict for each ACE entry
            if each_ace.get("line_num") != None:
                tmp_dict1[each_ace["line_num"]]["action"] = each_ace["action"]
                tmp_dict1[each_ace["line_num"]]["protocol"] = each_ace["protocol"]
                tmp_dict1[each_ace["line_num"]]["src"] = acl_scr_dst(each_ace, "src")
                tmp_dict1[each_ace["line_num"]]["dst"] = acl_scr_dst(each_ace, "dst")
                if each_ace.get("dst_port") != None:
                    tmp_dict1[each_ace["line_num"]]["dst_port"] = each_ace["dst_port"]
                elif each_ace.get("icmp_type") != None:
                    tmp_dict1[each_ace["line_num"]]["icmp_type"] = each_ace["icmp_type"]
                tmp_dict[each_ace["acl_name"]] = dict(tmp_dict1)

    # OSPF: Creates OSPF dicts in the format {ospf_nbr_rid: {state: nbr_state}}
    elif "show ip ospf neighbor" in cmd:
        for each_nhbr in output:
            tmp_dict[each_nhbr["neighbor_id"]] = {
                "state": remove_char(each_nhbr["state"], "/")
            }
    # PO: Creates port-channel dicts in the format {po_name: {protocol: type, status: code, members: {intf_name: {mbr_status: code}}}}
    elif "show etherchannel summary" in cmd:
        for each_po in output:
            tmp_dict[each_po["po_name"]]["status"] = each_po["po_status"]
            tmp_dict[each_po["po_name"]]["protocol"] = each_po["protocol"]
            po_mbrs = {}
            for mbr_intf, mbr_status in zip(
                each_po["interfaces"], each_po["interfaces_status"]
            ):
                # Creates dict of members to add to as value in the PO dictionary
                po_mbrs[mbr_intf] = {"mbr_status": mbr_status}
            tmp_dict[each_po["po_name"]]["members"] = po_mbrs

    actual_state[cmd] = dict(tmp_dict)
    return actual_state


# ----------------------------------------------------------------------------
# NXOS desired state formatting
# ----------------------------------------------------------------------------
def nxos_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:
    # MGMT_ACL: Creates ACL dicts in the format [{acl_name: {seq_num: {protocol: ip/tcp/udp, src: src_ip, dst: dst_ip, dst_port: port}]
    if "show access-lists" in cmd:
        acl = acl_format(output)
        tmp_dict1 = defaultdict(dict)
        for each_ace in acl:
            # Creates dict for each ACE entry
            if each_ace.get("action") != "remark":
                tmp_dict1[each_ace["sn"]]["action"] = each_ace["action"]
                tmp_dict1[each_ace["sn"]]["protocol"] = each_ace["protocol"]
                tmp_dict1[each_ace["sn"]]["src"] = each_ace["source"]
                tmp_dict1[each_ace["sn"]]["dst"] = each_ace["destination"]
                if each_ace["protocol"] == "icmp" and each_ace.get("modifier") != None:
                    tmp_dict1[each_ace["sn"]]["icmp_type"] = each_ace["modifier"]
                elif each_ace.get("modifier") != None:
                    tmp_dict1[each_ace["sn"]]["dst_port"] = each_ace["modifier"]
                tmp_dict[each_ace["name"]] = dict(tmp_dict1)
    actual_state[cmd] = dict(tmp_dict)
    return actual_state


# ----------------------------------------------------------------------------
# ASA desired state formatting
# ----------------------------------------------------------------------------
def asa_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:
    # MGMT_ACL: Creates SSH and HTTP dicts in the format [{ssh_or_http: {seq_num: {src: src_ip, intf: interface}]
    if "show run ssh" in cmd or "show run http" in cmd:
        tmp_dict1 = defaultdict(dict)
        seq = 10
        for each_ace in output.splitlines():
            try:
                ip_mask = each_ace.split()[1] + "/" + each_ace.split()[2]
                ip_pfxlen = ipaddress.IPv4Interface(ip_mask).with_prefixlen
                if ip_pfxlen == "0.0.0.0/0":
                    tmp_dict1[str(seq)]["src"] = "any"
                else:
                    tmp_dict1[str(seq)]["src"] = ip_pfxlen
                tmp_dict1[str(seq)]["intf"] = each_ace.split()[3]
                seq = seq + 10
            except:
                pass
        if len(tmp_dict1) != 0:
            tmp_dict[cmd.split()[-1].upper()] = dict(tmp_dict1)

    actual_state[cmd] = dict(tmp_dict)
    return actual_state
