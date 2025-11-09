from collections import defaultdict
from typing import Any


# ----------------------------------------------------------------------------
# OUTPUT: Creates str or ntc output dictionaries based on device command output
# ----------------------------------------------------------------------------
def _format_output(
    os_type: str, sub_feature: str, output: list[str | dict[str, str]]
) -> tuple[list[str], list[dict[str, str]]]:
    """Screen scraping return different data structures, they need defining to make function typing easier.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[str | dict[str, str]]): The structured (dict from NTC template) or unstructured (str from raw) command output from the device
    Raises:
        ValueError: Errors if the new output variable doesn't match the input as not meant to be changing it, just defining it for MYPY
    Returns:
        tuple[list[str], list[dict[str, str]]]: Returns either RAW list[str] or NTC list[dict], the other non-matched one will be empty
    """
    raw_output = [o for o in output if isinstance(o, str)]
    ntc_output = [o for o in output if isinstance(o, dict)]
    if (
        len(raw_output) != 0
        and output != raw_output
        or len(ntc_output) != 0
        and output != ntc_output
    ):
        msg = f"{os_type} {sub_feature} _format_output is malformed"
        raise ValueError(msg)
    return raw_output, ntc_output


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


def format_wlan(val_file: bool, output: list[dict[str, str]]) -> dict[str | int, Any]:
    """Format WLANs into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str | int, Any]: {wlan_id: {intf: x, ssid: xy, status: Enabled}}, if val_file is {wlan_id: {interface: x, ssid: xy}}
    """
    result: dict[str | int, dict[str, str]] = defaultdict(dict)
    for each_wlan in output:
        wlanid = _make_int(each_wlan["wlanid"])
        result[wlanid]["ssid"] = each_wlan["ssid"]
        # If creating actual state (replace(none) needed as long names merge next column (PIMIPv6))
        if not val_file:
            result[wlanid]["intf"] = each_wlan["interface"].replace("none", "").rstrip()
            result[wlanid]["status"] = "Enabled"
        # If creating validation file
        elif val_file:
            result[wlanid]["interface"] = (
                each_wlan["interface"].replace("none", "").rstrip()
            )
    return dict(result)


def format_ap(output: list[dict[str, str]]) -> dict[str, Any]:
    """Format APs into the data structure.

    Args:
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {ap_name: {model: x, ip: x, clients: x}}}
    """
    result: dict[str, dict[str, str | int]] = defaultdict(dict)
    for each_ap in output:
        result[each_ap["ap_name"]]["model"] = each_ap["ap_model"]
        result[each_ap["ap_name"]]["ip"] = each_ap["ip_address"]
        result[each_ap["ap_name"]]["client_count"] = _make_int(each_ap["clients"])
    return dict(result)


def format_client_count(output: list[str]) -> dict[str, str | int]:
    """Format client count into the data structure.

    Args:
        output (list[str]): The command output from the device in raw data structure
    Returns:
        dict[str, str | int]: {total_count: x, wlxx_count: x}
    """
    result = {}
    tmp_output = []
    # Gathers AP count from raw screen scrapped output
    for each_line in output:
        if "Number of Cl" in each_line or "Invalid WLAN ID 999" in each_line:
            tmp_output.append(each_line)
    # Formats client count from the slimmed down data
    if len(tmp_output) != 0:
        for idx, each_line in enumerate(tmp_output):
            if "Invalid WLAN ID 999" in each_line:
                name = f"wl{each_line.split()[4].replace('999', '')}_count"
                result[name] = _make_int(tmp_output[idx + 1].split()[-1])
                tmp_output[idx + 1] = ""
            elif "Number of Cl" in each_line:
                result["total_count"] = _make_int(each_line.split()[-1])
    return result


def format_flexconnect(output: list[dict[str, str]]) -> dict[str, Any]:
    """Format flexconnect groups into the data structure.

    Args:
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {grp_name: {ap_count: x}}}
    """
    result: dict[str, dict[str, str | int]] = defaultdict(dict)
    for each_grp in output:
        name = each_grp["flexconnect_group_name"]
        result[name]["ap_count"] = _make_int(each_grp["ap_count"])
    return dict(result)


def format_intf_grp(output: list[dict[str, str]]) -> dict[str, Any]:
    """Format interface groups into the data structure.

    Args:
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {ap_count: x, intf_count: x, wlan_count: x}}}
    """
    result: dict[str, dict[str, str | int]] = defaultdict(dict)
    for each_grp in output:
        name = each_grp["interface_group_name"]
        result[name]["ap_grp_count"] = _make_int(each_grp["total_ap_groups"])
        result[name]["intf_count"] = _make_int(each_grp["total_interfaces"])
        result[name]["wlan_count"] = _make_int(each_grp["total_wlans"])
    return dict(result)


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,
    os_type: str,  # noqa: ARG001
    sub_feature: str,
    output: list[str | dict[str, str]],
) -> dict[Any, Any]:
    """Engine to run all the actual state and validation file sub-feature formatting.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[str | dict[str, str]]): The structured (dict from NTC template) or unstructured (str/int from raw) command output from the device
    Returns:
        dict[str, Any]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)
    ### WLAN: {wlan_id: {intf: x, ssid: xy, status: Enabled}}}, if val_file is {wlan_id: {interface: x, ssid: xy}}
    if sub_feature == "wlan":
        return format_wlan(val_file, ntc_output)

    ### AP: {ap_name: {model: x, ip: x, clients: x}}}
    elif sub_feature == "ap":
        return format_ap(ntc_output)

    ### CLIENT_COUNT: {total_count: x, wlxx_count: x}
    elif sub_feature == "client_count":
        return format_client_count(raw_output)

    ### FLEXCONN: {grp_name: {ap_count: x}}}
    elif sub_feature == "flexconnect":
        return format_flexconnect(ntc_output)

    ### INTF_GRP: {grp_name: {ap_count: x, intf_count: x, wlan_count: x}}}
    elif sub_feature == "intf_grp":
        return format_intf_grp(ntc_output)

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
