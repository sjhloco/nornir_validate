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
    global mac_table_match, mac_table_match1, mac_table_element
    if bool(re.search("ios", os_type)):
        mac_table_match = "Vlan"
        mac_table_match1 = "Vlan"
        mac_table_element = -1
    elif bool(re.search("nxos", os_type)):
        mac_table_match = "static"
        mac_table_match1 = "Vlan"
        mac_table_element = 1
    elif bool(re.search("asa", os_type)):
        pass
    elif bool(re.search("wlc", os_type)):
        pass


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


def _format_vlan(output: List, tmp_dict: Dict[str, None]) -> None:
    """Format vlan and return data structure in tmp_dict"""
    for each_vl in output:
        vl_id = _make_int(each_vl["vlan_id"])
        tmp_dict[vl_id]["name"] = each_vl["name"]
        tmp_dict[vl_id]["intf"] = each_vl["interfaces"]
    for each_vl in [1002, 1003, 1004, 1005]:
        if tmp_dict.get(each_vl) != None:
            del tmp_dict[each_vl]


def _format_mac_table(output: List, tmp_dict: Dict[str, None]) -> None:
    """Format vlan and return data structure in tmp_dict"""
    for idx, each_item in enumerate(output):
        if mac_table_match in each_item:
            name = (
                f"vl{each_item.split()[mac_table_element].replace(':', '')}_mac_count"
            )
            tmp_dict[name] = _make_int(output[idx + 1].split()[-1])
            output[idx] = ""
            output[idx + 1] = ""
        elif "error" in each_item.lower() or "^" in each_item:
            output[idx] = ""
    # Only lines left will be count of total MACs
    for each_item in output:
        if len(each_item) != 0:
            tmp_dict["total_mac_count"] = _make_int(each_item.split()[-1])


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

    ### VLAN: {vlan: {name: x, intf:[x,y]}}
    if sub_feature == "vlan":
        _format_vlan(output, tmp_dict)

    ### STP: {vlan: intf:[x,y]}
    elif sub_feature == "stp_vlan":
        for each_vl in output:
            if tmp_dict.get(_make_int(each_vl["vlan_id"])) == None:
                tmp_dict[_make_int(each_vl["vlan_id"])]["intf"] = [each_vl["interface"]]
            else:
                tmp_dict[_make_int(each_vl["vlan_id"])]["intf"].append(
                    each_vl["interface"]
                )

    ### MAC TABLE COUNT: {total_mac_count: x, vlx_mac_count: x}
    elif sub_feature == "mac_table":
        _format_mac_table(output, tmp_dict)

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

    ### VLAN: {vlan: {name: x, intf:[x,y]}}
    if sub_feature == "vlan":
        _format_vlan(output, tmp_dict)

    ### STP: {cmd: {vlan: {intfx: FWD, intfy: FWD}}}
    elif sub_feature == "stp_vlan":
        for each_vl in output:
            tmp_dict[_make_int(each_vl["vlan_id"])][each_vl["interface"]] = each_vl[
                "status"
            ]

    ### MAC TABLE COUNT: {total_mac_count: x, vlx_mac_count: x}
    elif sub_feature == "mac_table":
        _format_mac_table(output, tmp_dict)

    return dict(tmp_dict)
