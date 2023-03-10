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


def _format_asa_sts(input_data: list) -> list:
    """
    > If the encapsulation is not empty, then create a dictionary with the ASA peer and session status
    standardised like IOS session_status  based receive/transmit packets. Append it to the output list

    :param input_data: list
    :type input_data: list
    :return: A list of dictionaries.
    """
    output = []
    for each_peer in input_data:
        if len(each_peer["encapsulation"]) != 0:
            tmp_dict = {"peer": each_peer["connection"]}
            if (
                each_peer["total_bytes_received"] == "0"
                and each_peer["total_bytes_transmitted"] == "0"
            ):
                tmp_dict["session_status"] = "DOWN-NoRX/TX"
            elif each_peer["total_bytes_received"] == "0":
                tmp_dict["session_status"] = "DOWN-NoRX"
            elif each_peer["total_bytes_transmitted"] == "0":
                tmp_dict["session_status"] = "DOWN-NoTX"
            else:
                tmp_dict["session_status"] = "UP-ACTIVE"
            output.append(tmp_dict)
    return output


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
    # STS_PEER: {peer_ip: UP-ACTIVE, peer_ip: UP-ACTIVE}}
    # ----------------------------------------------------------------------------
    if sub_feature == "sts_peer":
        if bool(re.search("asa", os_type)):
            output = _format_asa_sts(output)
        for each_vpn in output:
            tmp_dict[each_vpn["peer"]] = each_vpn["session_status"]

    # ----------------------------------------------------------------------------
    # AC_CLIENT: {user: tunnel_group: x, group_policy:y }}
    # ----------------------------------------------------------------------------
    elif sub_feature == "ac_client":
        for each_vpn in output:
            user = each_vpn["username"]
            tmp_dict[user]["group_policy"] = _make_int(each_vpn["group_policy"])
            tmp_dict[user]["tunnel_group"] = _make_int(each_vpn["tunnel_group"])

    # ----------------------------------------------------------------------------
    # VPN_COUNT: {sts: x, ac:y }}
    # ----------------------------------------------------------------------------
    elif sub_feature == "vpn_count":
        for each_line in output:
            if isinstance(each_line, str):
                tmp_dict["sts"] = _make_int(each_line.split()[-1])
            else:
                for each_vpn, active_sess in zip(
                    each_line["vpn_session_name"], each_line["vpn_session_active"]
                ):
                    if each_vpn == "AnyConnect Client":
                        tmp_dict["ac"] = _make_int(active_sess)

    return dict(tmp_dict)
