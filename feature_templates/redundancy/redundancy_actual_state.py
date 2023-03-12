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
    global ha_state_local, ha_state_peer
    if bool(re.search("ios", os_type)):
        ha_state_local = "active_software_state"
        ha_state_peer = "standby_software_state"
    elif bool(re.search("nxos", os_type)):
        pass
    elif bool(re.search("asa", os_type)):
        ha_state_local = "service_state"
        ha_state_peer = "service_state_mate"
    elif bool(re.search("wlc", os_type)):
        ha_state_local = "local_state"
        ha_state_peer = "peer_state"


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


def _format_ha_state(os_type: List, output: List, tmp_dict: Dict[str, None]) -> None:
    """Format HA state and return data structure in tmp_dict"""
    if bool(re.search("asa", os_type)):
        tmp_dict["local"] = output[0][ha_state_local][0]
        tmp_dict["peer"] = output[0][ha_state_peer][0]
    else:
        tmp_dict["local"] = output[0][ha_state_local]
        tmp_dict["peer"] = output[0][ha_state_peer]


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

    ### HA_STATE: {local_state: x, peer_state: x}
    if sub_feature == "ha_state":
        _format_ha_state(os_type, output, tmp_dict)

    ### SWI_STACK: show switch - {switchx: {priority: x, role: x, state: x}}
    elif sub_feature == "sw_stack":
        for each_swi in output:
            swi = f"switch{_make_int(each_swi['switch'])}"
            tmp_dict[swi]["role"] = each_swi["role"]
            tmp_dict[swi]["priority"] = _make_int(each_swi["priority"])
            tmp_dict[swi]["role"] = each_swi["role"]

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

    ### HA_STATE: {local_state: x, peer_state: x}
    if sub_feature == "ha_state":
        _format_ha_state(os_type, output, tmp_dict)

    ### SWI_STACK: show switch - {switchx: {priority: x, role: x, state: x}}
    elif sub_feature == "sw_stack":
        for each_swi in output:
            swi = f"switch{_make_int(each_swi['switch'])}"
            tmp_dict[swi]["role"] = each_swi["role"]
            tmp_dict[swi]["priority"] = _make_int(each_swi["priority"])
            tmp_dict[swi]["role"] = each_swi["role"]
            tmp_dict[swi]["state"] = each_swi["state"]

    return dict(tmp_dict)
