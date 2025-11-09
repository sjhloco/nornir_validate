import re
from collections import defaultdict
from typing import Any


# ----------------------------------------------------------------------------
# DEF: Mini-functions used by the main function
# ----------------------------------------------------------------------------
def _make_int(input_data: str) -> int | str:
    """Takes a string and returns an integer if it can, otherwise it returns the original string.

    Args:
        input_data (str): The data to be converted to an integer
    Returns:
        int | str: The input_data as a integer if possible, if not as the original string
    """
    try:
        return int(input_data)
    except ValueError:
        return input_data


def format_sts_peer(
    val_file: bool,
    os_type: str,
    output: list[dict[str, Any]],
) -> dict[str, str] | list[str]:
    """Format STS peers into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str, str] | list[str]: {peer_ip: IP, peer_ip: UP-ACTIVE}}, val file is just list a [peer_ip, peer_ip]
    """
    result = {}
    # For ASA need to standardise the session status based on receive/transmit packets
    if re.search("asa", os_type):
        sts_output = []
        for each_peer in output:
            if (
                len(each_peer["udp_src_port"]) != 0
                and len(each_peer["udp_dst_port"]) != 0
            ):
                tmp_dict = {
                    "peer": each_peer["connection"],
                    "session_status": "UP-ACTIVE",
                }
                if (
                    each_peer["total_bytes_received"] == "0"
                    and each_peer["total_bytes_transmitted"] == "0"
                ):
                    tmp_dict["session_status"] = "DOWN-NoRX/TX"
                elif each_peer["total_bytes_received"] == "0":
                    tmp_dict["session_status"] = "DOWN-NoRX"
                elif each_peer["total_bytes_transmitted"] == "0":
                    tmp_dict["session_status"] = "DOWN-NoTX"
                sts_output.append(tmp_dict)
    # All other OS types change output name so can all use same loop
    else:
        sts_output = output
    val_file_list = []
    for each_vpn in sts_output:
        result[each_vpn["peer"]] = each_vpn["session_status"]
        val_file_list.append(each_vpn["peer"])
    # List of peers if is a validation file
    if val_file:
        return val_file_list
    else:
        return result


def format_ac_user(output: list[dict[str, Any]]) -> dict[str, Any]:
    """Format AnyConnect Users into the data structure.

    Args:
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {user: tunnel_group: x, group_policy:y }}
    """
    result: dict[str, dict[str, str]] = defaultdict(dict)
    for each_vpn in output:
        user = each_vpn["username"]
        result[user]["group_policy"] = each_vpn["group_policy"]
        result[user]["tunnel_group"] = each_vpn["tunnel_group"]
    return dict(result)


def format_vpn_count(
    output: list[str | dict[str, Any]],
) -> dict[str, str | int]:
    """Format VPN count for AC and StS into the data structure.

    Args:
        output (list[str | dict[str, Any]]): The command output from the device, 2 commands so includes raw str and ntc dict
    Returns:
        dict[str, str | int]: {sts: x, ac:y }}
    """
    result = {}
    for each_line in output:
        if isinstance(each_line, str):
            if "Number of lines which match regexp" in each_line:
                result["sts"] = _make_int(each_line.split()[-1])
        else:
            for each_vpn, active_sess in zip(
                each_line["vpn_session_name"],
                each_line["vpn_session_active"],
                strict=False,
            ):
                if each_vpn == "AnyConnect Client":
                    result["ac"] = _make_int(active_sess)
    return result


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool, os_type: str, sub_feature: str, output: list[dict[str, Any]]
) -> dict[str, Any] | list[str]:
    """Engine to run all the actual state and validation file sub-feature formatting.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[dict[str, Any]]): The structured (dict from NTC template) or unstructured (str/int from raw) command output from the device
    Returns:
        dict[str, Any] | list[str]: Returns formatted command output based on sub_feature and val_file arguments.
    """
    ### STS_PEER: {peer_ip: IP, peer_ip: UP-ACTIVE}} (val file is just list a [peer_ip, peer_ip]).
    if sub_feature == "sts_peer":
        return format_sts_peer(val_file, os_type, output)

    ### AC_USER: {user: tunnel_group: x, group_policy:y }}
    elif sub_feature == "ac_user":
        return format_ac_user(output)

    ### VPN_COUNT: {sts: x, ac:y }}
    elif sub_feature == "vpn_count":
        # Reforming output so it has the right typing
        mixed_output: list[str | dict[str, Any]] = [
            o for o in output if isinstance(o, (str, dict))
        ]
        return format_vpn_count(mixed_output)

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
