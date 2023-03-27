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
    if bool(re.search("ios", os_type)):
        pass
    elif bool(re.search("nxos", os_type)):
        pass
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


def _format_ap(output: List, tmp_dict: Dict[str, None]) -> None:
    """Format APs and return data structure in tmp_dict"""
    for each_ap in output:
        a = each_ap["ap_name"]
        tmp_dict[each_ap["ap_name"]]["model"] = each_ap["ap_model"]
        tmp_dict[each_ap["ap_name"]]["ip"] = each_ap["ip"]
        tmp_dict[each_ap["ap_name"]]["client_count"] = _make_int(each_ap["clients"])


def _format_client_count(output: List, tmp_dict: Dict[str, None]) -> None:
    """Format client count and return data structure in tmp_dict"""
    if len(output) != 0:
        tmp_output = []
        for each_line in output:
            if "Number of Cl" in each_line or "Invalid WLAN ID 999" in each_line:
                tmp_output.append(each_line)
    if len(tmp_output) != 0:
        for idx, each_line in enumerate(tmp_output):
            if "Invalid WLAN ID 999" in each_line:
                name = f"wl{each_line.split()[4].replace('999', '')}_count"
                tmp_dict[name] = _make_int(tmp_output[idx + 1].split()[-1])
                tmp_output[idx + 1] = ""
            elif "Number of Cl" in each_line:
                tmp_dict["total_count"] = _make_int(each_line.split()[-1])


def _format_flexconnect(output: List, tmp_dict: Dict[str, None]) -> None:
    """Format flexconnect groups and return data structure in tmp_dict"""
    for each_grp in output:
        name = each_grp["flexconnect_group_name"]
        tmp_dict[name]["ap_count"] = _make_int(each_grp["ap_count"])


def _format_intf_grp(output: List, tmp_dict: Dict[str, None]) -> None:
    """Format interface groups and return data structure in tmp_dict"""
    for each_grp in output:
        name = each_grp["interface_group_name"]
        tmp_dict[name]["ap_grp_count"] = _make_int(each_grp["total_ap_groups"])
        tmp_dict[name]["intf_count"] = _make_int(each_grp["total_interfaces"])
        tmp_dict[name]["wlan_count"] = _make_int(each_grp["total_wlans"])


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

    ### WLAN: {wlan_id: {intf: x, ssid: xy}}}
    if sub_feature == "wlan":
        for each_wlan in output:
            wlanid = _make_int(each_wlan["wlanid"])
            tmp_dict[wlanid]["interface"] = each_wlan["interface"]
            tmp_dict[wlanid]["ssid"] = each_wlan["ssid"]

    ### AP: {ap_name: {model: x, ip: x, clients: x}}}
    elif sub_feature == "ap":
        _format_ap(output, tmp_dict)

    ### CLIENT_COUNT: {total_count: x, wlxx_count: x}
    elif sub_feature == "client_count":
        _format_client_count(output, tmp_dict)

    ### FLEXCONN: {grp_name: {ap_count: x}}}
    elif sub_feature == "flexconnect":
        _format_flexconnect(output, tmp_dict)

    ### INTF_GRP: {grp_name: {ap_count: x, intf_count: x, wlan_count: x}}}
    elif sub_feature == "intf_grp":
        _format_intf_grp(output, tmp_dict)

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

    ### WLAN: {wlan_id: {intf: x, ssid: xy, status: Enabled}}}
    if sub_feature == "wlan":
        for each_wlan in output:
            wlanid = _make_int(each_wlan["wlanid"])
            tmp_dict[wlanid]["intf"] = each_wlan["interface"]
            tmp_dict[wlanid]["ssid"] = each_wlan["ssid"]
            tmp_dict[wlanid]["status"] = "Enabled"

    ### AP: {ap_name: {model: x, ip: x, clients: x}}}
    elif sub_feature == "ap":
        _format_ap(output, tmp_dict)

    ### CLIENT_COUNT: {total_count: x, wlxx_count: x}
    elif sub_feature == "client_count":
        _format_client_count(output, tmp_dict)

    ### FLEXCONN: {grp_name: {ap_count: x}}}
    elif sub_feature == "flexconnect":
        _format_flexconnect(output, tmp_dict)

    ### INTF_GRP: {grp_name: {ap_count: x, intf_count: x, wlan_count: x}}}
    elif sub_feature == "intf_grp":
        _format_intf_grp(output, tmp_dict)

    return dict(tmp_dict)
