from typing import Dict, List
from collections import defaultdict
import re


# ----------------------------------------------------------------------------
# Mini-functions used by the main function
# ----------------------------------------------------------------------------
# INTEGER: Changes string to integer
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
        pass
    elif bool(re.search("nxos", os_type)):
        pass
    elif bool(re.search("asa", os_type)):
        pass
    elif bool(re.search("wlc", os_type)):
        pass

    # ----------------------------------------------------------------------------
    # WLAN: {wlan_id: {intf: x, ssid: xy, status: Enabled}}}
    # ----------------------------------------------------------------------------
    if sub_feature == "wlan":
        for each_wlan in output:
            wlanid = _make_int(each_wlan["wlanid"])
            tmp_dict[wlanid]["intf"] = each_wlan["interface"]
            tmp_dict[wlanid]["ssid"] = each_wlan["ssid"]
            tmp_dict[wlanid]["status"] = "Enabled"

    # ----------------------------------------------------------------------------
    # AP: {ap_name: {model: x, ip: x, clients: x}}}
    # ----------------------------------------------------------------------------
    elif sub_feature == "ap":
        for each_ap in output:
            a = each_ap["ap_name"]
            tmp_dict[each_ap["ap_name"]]["model"] = each_ap["ap_model"]
            tmp_dict[each_ap["ap_name"]]["ip"] = each_ap["ip"]
            tmp_dict[each_ap["ap_name"]]["client_count"] = _make_int(each_ap["clients"])

    # ----------------------------------------------------------------------------
    # CLIENT_COUNT: {total_count: x, wlxx_count: x}
    # ----------------------------------------------------------------------------
    elif sub_feature == "client_count":
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

    # ----------------------------------------------------------------------------
    # FLEXCONN: {grp_name: {ap_count: x}}}
    # ----------------------------------------------------------------------------
    elif sub_feature == "flexconnect":
        for each_grp in output:
            name = each_grp["flexconnect_group_name"]
            tmp_dict[name]["ap_count"] = _make_int(each_grp["ap_count"])

    # ----------------------------------------------------------------------------
    # INTF_GRP: {grp_name: {ap_count: x, intf_count: x, wlan_count: x}}}
    # ----------------------------------------------------------------------------
    elif sub_feature == "intf_grp":
        for each_grp in output:
            name = each_grp["interface_group_name"]
            tmp_dict[name]["ap_grp_count"] = _make_int(each_grp["total_ap_groups"])
            tmp_dict[name]["intf_count"] = _make_int(each_grp["total_interfaces"])
            tmp_dict[name]["wlan_count"] = _make_int(each_grp["total_wlans"])

    return dict(tmp_dict)
