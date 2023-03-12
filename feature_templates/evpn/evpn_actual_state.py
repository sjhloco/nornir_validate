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
    global nve_vni_bd_vrf, nve_vni_bd_vrf
    if bool(re.search("ios", os_type)):
        nve_vni_bd_vrf = "vrf"
    elif bool(re.search("nxos", os_type)):
        nve_vni_bd_vrf = "bd_vrf"
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

    ### NVE_VNI: {l3vni: {bdi_vrf: z}}
    if sub_feature == "nve_vni":
        for each_vni in output:
            vni = _make_int(each_vni["vni"])
            if "L2" in each_vni["mode"]:
                tmp_dict[vni]["bd_vrf"] = _make_int(each_vni["bd"])
            else:
                tmp_dict[vni]["bd_vrf"] = _make_int(each_vni[nve_vni_bd_vrf])
        tmp_dict = dict(tmp_dict)

    ### NVE_PEER: [peer1_ip, peer1_ip]
    elif sub_feature == "nve_peer":
        tmp_dict = []
        for each_peer in output:
            if each_peer["peer"] not in str(tmp_dict):
                tmp_dict.append(each_peer["peer"])
        # tmp_set = set(tmp_dict)
        # tmp_dict = list(tmp_set)

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

    ### NVE_VNI: {l3vni: {bdi_vrf: z, state: Up}}
    if sub_feature == "nve_vni":
        for each_vni in output:
            vni = _make_int(each_vni["vni"])
            if "L2" in each_vni["mode"]:
                tmp_dict[vni]["bd_vrf"] = _make_int(each_vni["bd"])
            else:
                tmp_dict[vni]["bd_vrf"] = _make_int(each_vni[nve_vni_bd_vrf])
            tmp_dict[vni]["state"] = each_vni["state"]

    ### NVE_PEER: {peer1_ip: state: Up, peer1_ip: state: Up}
    elif sub_feature == "nve_peer":
        for each_peer in output:
            tmp_dict[each_peer["peer"]] = each_peer["state"].capitalize()

    return dict(tmp_dict)
