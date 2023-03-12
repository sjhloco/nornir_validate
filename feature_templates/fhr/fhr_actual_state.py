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
    global hsrp_intf, hsrp_prio, hsrp_state
    if bool(re.search("ios", os_type)):
        hsrp_intf = "iface"
        hsrp_prio = "priority"
        hsrp_state = "state"
    elif bool(re.search("nxos", os_type)):
        hsrp_intf = "sh_if_index"
        hsrp_prio = "sh_prio"
        hsrp_state = "sh_group_state"
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


def _format_hsrp(os_type: List, output: List, tmp_dict: Dict[str, None]) -> None:
    """Format HSRP and return data structure in tmp_dict"""
    if bool(re.search("nxos", os_type)):
        output = _fix_nxos(output[0], "TABLE_grp_detail", "ROW_grp_detail")
    for each_nbr in output:
        tmp_dict[each_nbr[hsrp_intf]]["priority"] = _make_int(each_nbr[hsrp_prio])
        tmp_dict[each_nbr[hsrp_intf]]["state"] = each_nbr[hsrp_state]


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

    ### HSRP: {intf: {priority: x, state: y}}
    if sub_feature == "hsrp":
        _format_hsrp(os_type, output, tmp_dict)

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

    ### HSRP: {intf: {priority: x, state: y})
    if sub_feature == "hsrp":
        _format_hsrp(os_type, output, tmp_dict)

    return dict(tmp_dict)
