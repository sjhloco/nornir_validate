from typing import Dict, List
from collections import defaultdict
import ipaddress
import re


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
def _set_keys(os_type: List) -> Dict[str, Dict]:
    """
    Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures

    :param os_type: This is a list of strings that are the OS types of the devices in the inventory
    :type os_type: List
    """
    global image_version, mgmt_acl_name, mgmt_acl_seq
    if bool(re.search("ios", os_type)):
        image_version = "version"
        mgmt_acl_name = "acl_name"
        mgmt_acl_seq = "line_num"
    elif bool(re.search("nxos", os_type)):
        image_version = "os"
        mgmt_acl_name = "name"
        mgmt_acl_seq = "sn"
    elif bool(re.search("asa", os_type)):
        image_version = "version"
        mgmt_acl_name = "name"
        mgmt_acl_seq = "sn"
    elif bool(re.search("wlc", os_type)):
        image_version = "product_version"


# ----------------------------------------------------------------------------
# DEF: Mini-functions used by the main function
# ----------------------------------------------------------------------------
def _make_int(input_data: str) -> int:
    """
    It takes a string and returns an integer if it can, otherwise it returns the original string

    :param input_data: The data to be converted to an integer
    :type input_data: str
    :return: the input_data as an integer.
    """
    try:
        return int(input_data)
    except:
        return input_data


def _acl_format_into_dict(input_acl: List, name: str) -> List:
    """
    > This function takes a list of ACEs, removes all the empty dictionaries from ACL list
    and returns a dictionary of ACLs.

    :param input_acl: This is the list of ACEs that you want to format into a dict
    :type input_acl: List
    :param name: The name of the ACL
    :type name: str
    :return: A dict of ACLs with the name of the ACL as the key and a list of ACEs as the value.
    """
    acl = {}
    acl_names = set(item[name] for item in input_acl)

    for each_acl_name in acl_names:
        tmp_acl_list = []
        for each_ace in input_acl:
            if each_ace.get("line_num", "dummy") == "":
                pass
            else:
                tmp_ace_dict = {}
                for ace_key, ace_val in each_ace.items():
                    # Add none blank ACE entires to dict of ACEs
                    if len(ace_val) != 0:
                        tmp_ace_dict[ace_key] = ace_val
                # Add dict of all none blank ACE entires to list of ACLs
                if each_acl_name == each_ace[name]:
                    tmp_acl_list.append(tmp_ace_dict)
            # Add all ACLs to Dict of ACL names
            acl[each_acl_name] = tmp_acl_list
    return acl


def _acl_remove_remark(input_acl: List) -> Dict[str, Dict]:
    """
    > Removes remark and reorders the seq number as NXOS gives remarks a sequence number (IOS doesnt)

    :param input_acl: This is the ACL that you want to remove the remark from
    :type input_acl: List
    :return: A dictionary of dictionaries.
    """
    for name, ace in input_acl.items():
        while "remark" in str(ace):
            ace_count = len(ace)
            for idx, each_ace in enumerate(ace):
                if each_ace["action"] == "remark":
                    for x in reversed(range(idx + 1, ace_count)):
                        ace[x]["sn"] = ace[x - 1]["sn"]
                    del ace[idx]
                    break
    return input_acl


def _acl_scr_dst(each_ace: Dict[str, str], src_dst: str) -> str:
    """
    > It takes a dictionary of ACEs and a string of either "src" or "dst" and returns the source or
    destination address of the ACE converted into address/prefix

    :param each_ace: This is the dictionary that contains the ACE information
    :type each_ace: Dict[str, str]
    :param src_dst: This is the source or destination of the ACL
    :type src_dst: str
    :return: the source or destination address of the ACL.
    """
    if each_ace.get(src_dst + "_network") != None:
        addr = each_ace[src_dst + "_network"] + "/" + each_ace[src_dst + "_wildcard"]
        return ipaddress.IPv4Interface(addr).with_prefixlen
    elif each_ace.get(src_dst + "_host") != None:
        return ipaddress.IPv4Interface(each_ace[src_dst + "_host"]).with_prefixlen
    else:
        return each_ace[src_dst + "_any"]


def _acl_asa_format(input_acl: List, name: str) -> Dict[str, Dict]:
    """
    > This function takes a list of ASA SSH and HTTP access and returns a list of dictionaries with the name,
    sequence number, action, and source for each ACE (same format as ACLs)

    :param input_acl: This is the list of ACL lines that you want to convert
    :type input_acl: List
    :param name: The name of the ACL
    :type name: str
    :return: A list of dictionaries.
    """
    asa_list = []
    seq = 10
    for each_ace in input_acl:
        if re.match(f"^{name} [0-9]", each_ace):
            asa_dict = dict(name=name)
            asa_dict["sn"] = str(seq)
            asa_dict["action"] = "permit"
            ip_mask = each_ace.split()[1] + "/" + each_ace.split()[2]
            ip_pfxlen = ipaddress.IPv4Interface(ip_mask).with_prefixlen
            if ip_pfxlen == "0.0.0.0/0":
                asa_dict["source"] = f"{each_ace.split()[3]} - any"
            else:
                asa_dict["source"] = f"{each_ace.split()[3]} - {ip_pfxlen}"
            asa_list.append(asa_dict)
            seq = seq + 10
    return asa_list


# ----------------------------------------------------------------------------
# VALIDATION: Engine to create the validation file sub-feature validations (for all os-types)
# ----------------------------------------------------------------------------
def generate_val_file(
    os_type: List, sub_feature: str, output: List, tmp_dict: Dict[str, None]
) -> Dict[str, Dict]:
    """
    > The function takes the command output and formats it into a dictionary that can be used
    in the validation file to validate features

    :param os_type: List
    :type os_type: List
    :param sub_feature: This is the sub-feature that you want to validate
    :type sub_feature: str
    :param output: the output of the command
    :type output: List
    :param tmp_dict: This is the dictionary that will be returned by the function
    :type tmp_dict: Dict[str, None]
    :return: A dictionary with the following keys:
        - image
        - mgmt_acl
        - module
    """
    _set_keys(os_type)
    ### IMAGE: {image: code_number}
    if sub_feature == "image":
        tmp_dict = output[0][image_version]

    ### MGMT_ACL: {acl_name: ace: [{permit: ip/pfx}, {deny: ip/pfx}]}
    elif "mgmt_acl" in sub_feature:
        # tmp_dict = []
        if bool(re.search("asa", os_type)):
            asa_output = _acl_asa_format(output, "ssh")
            asa_output.extend(_acl_asa_format(output, "http"))
            output = asa_output
        acl = _acl_format_into_dict(output, mgmt_acl_name)
        acl = _acl_remove_remark(acl)

        for name, ace in acl.items():
            tmp_ace = []
            for each_ace in ace:
                try:
                    tmp_ace.append({each_ace["action"]: each_ace["source"]})
                except:
                    tmp_ace.append({each_ace["action"]: _acl_scr_dst(each_ace, "src")})
            tmp_dict[name] = {"ace": tmp_ace}
            tmp_dict = dict(tmp_dict)

    ### MODULE: {module_num: {model: xxx}}
    elif sub_feature == "module":
        for each_mod in output:
            mod = _make_int(each_mod["module"])
            tmp_dict[mod]["model"] = each_mod["model"]
            status = each_mod.get("status", "x").lower()
            if "active" in status or "standby" in status:
                tmp_dict[mod]["status"] = each_mod["status"].lower()

        tmp_dict = dict(tmp_dict)

    return tmp_dict


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine that runs the actual state sub-feature formatting for all os types
# ----------------------------------------------------------------------------
def format_actual_state(
    os_type: List, sub_feature: str, output: List, tmp_dict: Dict[str, None]
) -> Dict[str, Dict]:
    """
    > The function takes the command output and formats it into a dictionary that can be used
    to compare against the desired state

    :param os_type: str = The OS type of the device
    :type os_type: str
    :param sub_feature: This is the sub-feature of the feature you're working on. For example, if you're
    working on the "image" feature, the sub-feature would be "version"
    :type sub_feature: str
    :param output: The output from the device
    :type output: List
    :param tmp_dict: This is the dictionary that will be returned by the function
    :type tmp_dict: Dict[str, None]
    :return: A dictionary of dictionaries.
    """

    _set_keys(os_type)
    ### IMAGE: {image: code_number}
    if sub_feature == "image":
        tmp_dict = output[0][image_version]

    ### MGMT_ACL: {acl_name: seq_num: {protocol: ip/tcp/udp, src: src_ip (or as intf - src_ip), dst: dst_ip, dst_port: port}}
    elif sub_feature == "mgmt_acl":
        if bool(re.search("asa", os_type)):
            asa_output = _acl_asa_format(output, "ssh")
            asa_output.extend(_acl_asa_format(output, "http"))
            output = asa_output
        acl = _acl_format_into_dict(output, mgmt_acl_name)
        acl = _acl_remove_remark(acl)
        for name, ace in acl.items():
            tmp_dict[name] = defaultdict(dict)
        for name, ace in acl.items():
            for each_ace in ace:
                seq = _make_int(each_ace[mgmt_acl_seq])
                tmp_dict[name][seq]["action"] = each_ace["action"]
                tmp_dict[name][seq]["protocol"] = "ip"
                tmp_dict[name][seq]["dst"] = "any"
                try:
                    tmp_dict[name][seq]["src"] = each_ace["source"]
                except:
                    tmp_dict[name][seq]["src"] = _acl_scr_dst(each_ace, "src")
            tmp_dict[name] = dict(tmp_dict[name])
        tmp_dict = dict(tmp_dict)

    ### MODULE: {module_num: {model: xxx, status, ok}}
    elif sub_feature == "module":
        for each_mod in output:
            mod = _make_int(each_mod["module"])
            tmp_dict[mod]["model"] = each_mod["model"]
            if len(each_mod["status"]) == 0:
                tmp_dict[mod]["status"] = "ok"
            else:
                tmp_dict[mod]["status"] = each_mod["status"].lower()
        tmp_dict = dict(tmp_dict)

    return tmp_dict
