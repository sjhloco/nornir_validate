from typing import Dict, List
import re


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
        cdp_local = "local_interface"
        cdp_nbr = "neighbor"
        cdp_remote = "neighbor_interface"
    elif bool(re.search("nxos", os_type)):
        cdp_local = "local_interface"
        cdp_nbr = "neighbor"
        cdp_remote = "neighbor_interface"
    elif bool(re.search("asa", os_type)):
        pass
    elif bool(re.search("wlc", os_type)):
        cdp_local = "local_port"
        cdp_nbr = "destination_host"
        cdp_remote = "remote_port"

    # ----------------------------------------------------------------------------
    # CDP/LLDP: {intf: {neighbor: neighbor_interface}}
    # ----------------------------------------------------------------------------
    if sub_feature == "cdp" or sub_feature == "lldp":
        for each_nbr in output:
            tmp_dict[each_nbr[cdp_local]] = {each_nbr[cdp_nbr]: each_nbr[cdp_remote]}

    return dict(tmp_dict)
