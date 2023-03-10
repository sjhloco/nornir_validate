from typing import Dict, List
from collections import defaultdict
import re


# ----------------------------------------------------------------------------
# Mini-functions used by the main function
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
# Engine that runs the actual state sub-feature formatting for all os types
# ----------------------------------------------------------------------------
def format_actual_state(
    os_type: str, sub_feature: str, output: List, tmp_dict: Dict[str, None]
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

    ### KEY: Set the dictionary keys to use on a per-OS basis
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
    # VLAN: {vlan: {name: x, intf:[x,y]}}
    # ----------------------------------------------------------------------------
    if sub_feature == "vlan":
        for each_vl in output:
            vl_id = _make_int(each_vl["vlan_id"])
            tmp_dict[vl_id]["name"] = each_vl["name"]
            tmp_dict[vl_id]["intf"] = each_vl["interfaces"]
        for each_vl in [1002, 1003, 1004, 1005]:
            if tmp_dict.get(each_vl) != None:
                del tmp_dict[each_vl]

    # ----------------------------------------------------------------------------
    # STP: {vlan: intf:[x,y]}
    # ----------------------------------------------------------------------------
    elif sub_feature == "stp_vlan":
        for each_vl in output:
            tmp_dict[_make_int(each_vl["vlan_id"])][each_vl["interface"]] = each_vl[
                "status"
            ]

    # ----------------------------------------------------------------------------
    # MAC TABLE COUNT: {total_mac_count: x, vlx_mac_count: x}
    # ----------------------------------------------------------------------------
    elif sub_feature == "mac_table":
        for idx, each_item in enumerate(output):
            if mac_table_match in each_item:
                name = f"vl{each_item.split()[mac_table_element].replace(':', '')}_mac_count"
                tmp_dict[name] = _make_int(output[idx + 1].split()[-1])
                output[idx] = ""
                output[idx + 1] = ""
            elif "error" in each_item.lower() or "^" in each_item:
                output[idx] = ""
        # Only lines left will be count of total MACs
        for each_item in output:
            if len(each_item) != 0:
                tmp_dict["total_mac_count"] = _make_int(each_item.split()[-1])

    return dict(tmp_dict)
