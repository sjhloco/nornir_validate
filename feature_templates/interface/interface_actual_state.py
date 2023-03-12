from typing import Dict, List
from collections import defaultdict
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
    global intf_name, intf_type, intf_status, ip_name, ip_ip, ip_status
    if bool(re.search("ios", os_type)):
        intf_name = "port"
        intf_type = "vlan"
        intf_status = "status"
        ip_name = "intf"
        ip_ip = "ipaddr"
        ip_status = "status"
    elif bool(re.search("nxos", os_type)):
        intf_name = "port"
        intf_type = "vlan"
        intf_status = "status"
        ip_name = "intf-name"
        ip_ip = "prefix"
        ip_status = "link-state"
    elif bool(re.search("asa", os_type)):
        intf_name = "interface"
        intf_type = "interface_zone"
        intf_status = "link_status"
        ip_name = "intf"
        ip_ip = "ipaddr"
        ip_status = "status"
    elif bool(re.search("wlc", os_type)):
        intf_name = "port"
        intf_type = "stp_status"
        intf_status = "link_status"
        ip_name = "name"
        ip_ip = "ip_addr"
        ip_status = "status"


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


def _fix_nxos(main_dict: Dict[str, Dict], parent_dict: str, child_dict: str) -> List:
    """
    Fixes issues due to NXOS JSON making dict rather than list if only 1 item.
    If the child_dict is a dictionary, convert it to a list. Feed in cmd specific TABLE_xx and ROW_xx keywords

    :param main_dict: The dictionary that contains the parent dictionary
    :param parent_dict: The parent dictionary key
    :param child_dict: The key of the dictionary that you want to fix
    :return: A list of dictionaries
    """
    if isinstance(main_dict[parent_dict][child_dict], dict):
        main_dict[parent_dict][child_dict] = [main_dict[parent_dict][child_dict]]
    return main_dict[parent_dict][child_dict]


def _make_none(input_dict: Dict[str, str], dict_key: str) -> str:
    """
    If the value of the key in the dictionary is empty, then set the value to None

    :param input_dict: the dictionary that contains the key-value pair
    :param dict_key: The key in the dictionary that you want to check
    :return: A dictionary with the value that is not empty
    """
    tmp_value = input_dict.get(dict_key)
    if len(tmp_value) == 0:
        tmp_value = None
    return tmp_value


def _wlc_duplex_speed(intf: Dict[str, str]) -> None:
    """
    It takes the physical status of the interface and splits it into two variables, duplex and speed

    :param intf: The interface name
    """
    try:
        intf["duplex"] = _make_int(intf["physical_status"].split()[1])
        intf["speed"] = intf["physical_status"].split()[0]
    except:
        intf["duplex"] = intf["physical_status"]
        intf["speed"] = intf["physical_status"]


def _format_switchport(output: List, tmp_dict: Dict[str, None]) -> None:
    """Format switchport and return data structure in tmp_dict"""
    for each_intf in output:
        mode = each_intf["mode"].replace("static ", "").split()[0]
        tmp_dict[each_intf["interface"]]["mode"] = mode
        if each_intf["mode"] == "static access" or each_intf["mode"] == "access":
            tmp_dict[each_intf["interface"]]["vlan"] = _make_int(
                each_intf["access_vlan"]
            )
        elif bool(re.search("trunk", each_intf["mode"])):
            trunk_vl = each_intf["trunking_vlans"]
            try:
                trunk_vl = [_make_int(vl) for vl in trunk_vl.split(",")]
            except:
                trunk_vl = [_make_int(vl) for vl in trunk_vl[0].split(",")]
            tmp_dict[each_intf["interface"]]["vlan"] = trunk_vl
        else:
            tmp_dict[each_intf["interface"]]["vlan"] = None


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

    ### INTF: {intf: {duplex: x, speed: x, type:x}}
    if sub_feature == "intf":
        for each_intf in output:
            intf = _make_int(each_intf[intf_name])
            if bool(re.search("wlc", os_type)):
                _wlc_duplex_speed(each_intf)
            if len(each_intf["duplex"]) != 0:
                tmp_dict[intf]["duplex"] = each_intf["duplex"]
            if len(each_intf["speed"]) != 0:
                tmp_dict[intf]["speed"] = _make_int(each_intf["speed"])
            if isinstance(_make_int(each_intf.get(intf_type)), int):
                tmp_dict[intf]["type"] = "access"
            elif len(each_intf[intf_type]) != 0:
                tmp_dict[intf]["type"] = _make_none(each_intf, intf_type)

    ### SWITCHPORT: {intf: {mode: access or trunk, vlan: x or [x,y]}}
    elif sub_feature == "switchport":
        _format_switchport(output, tmp_dict)

    ### IP_BRIEF: {intf: {ip:x, status: x}}}
    elif sub_feature == "ip_brief":
        if bool(re.search("nxos", os_type)):
            output = _fix_nxos(output[0], "TABLE_intf", "ROW_intf")
        for each_intf in output:
            tmp_dict[each_intf[ip_name]] = each_intf.get(
                ip_ip, each_intf.get("unnum-intf")
            )

    return dict(tmp_dict)


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

    ### INTF: {intf: {duplex: x, speed: x, type:x, connected }}
    if sub_feature == "intf":
        for each_intf in output:
            intf = _make_int(each_intf[intf_name])
            if bool(re.search("wlc", os_type)):
                _wlc_duplex_speed(each_intf)
            tmp_dict[intf]["duplex"] = _make_none(each_intf, "duplex")
            tmp_dict[intf]["speed"] = _make_int(_make_none(each_intf, "speed"))
            if isinstance(_make_int(each_intf.get(intf_type)), int):
                tmp_dict[intf]["type"] = "access"
            else:
                tmp_dict[intf]["type"] = _make_none(each_intf, intf_type)
            tmp_dict[intf]["status"] = (
                each_intf[intf_status].lower().replace("up", "connected")
            )

    ### SWITCHPORT: {intf: {mode: access or trunk, vlan: x or [x,y]}}
    elif sub_feature == "switchport":
        _format_switchport(output, tmp_dict)

    ### IP_BRIEF: {intf: {ip:x, status: x}}}
    elif sub_feature == "ip_brief":
        if bool(re.search("nxos", os_type)):
            output = _fix_nxos(output[0], "TABLE_intf", "ROW_intf")
        for each_intf in output:
            tmp_dict[each_intf[ip_name]]["ip"] = each_intf.get(
                ip_ip, each_intf.get("unnum-intf")
            )
            tmp_dict[each_intf[ip_name]]["status"] = each_intf.get(ip_status, "up")

    return dict(tmp_dict)
