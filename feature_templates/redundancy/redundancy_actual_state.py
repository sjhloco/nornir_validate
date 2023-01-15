from typing import Dict, List
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
def format_output(
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
    # HA_STATE: {local_state: x, peer_state: x}
    # ----------------------------------------------------------------------------
    if sub_feature == "ha_state":
        if bool(re.search("asa", os_type)):
            tmp_dict["local_state"] = output[0][ha_state_local][0]
            tmp_dict["peer_state"] = output[0][ha_state_peer][0]
        else:
            tmp_dict["local_state"] = output[0][ha_state_local]
            tmp_dict["peer_state"] = output[0][ha_state_peer]

    # ----------------------------------------------------------------------------
    # SWI_STACK: show switch - {sw_num: {priority: x, role: x, state: x}}
    # ----------------------------------------------------------------------------
    elif sub_feature == "switch_stack":
        for each_swi in output:
            swi = _make_int(each_swi["switch"])
            tmp_dict[swi]["role"] = each_swi["role"]
            tmp_dict[swi]["priority"] = _make_int(each_swi["priority"])
            tmp_dict[swi]["role"] = each_swi["role"]
            tmp_dict[swi]["state"] = each_swi["state"]

    return dict(tmp_dict)
