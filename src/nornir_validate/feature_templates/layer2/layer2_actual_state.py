from collections import defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    mac_table_match: str
    mac_table_element: int
    mac_table_idx: int


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "ios" in os_type:
        return OsKeys("Vlan", -1, 1)
    elif "nxos" in os_type:
        return OsKeys("enet", 0, 1)
    # Fallback if nothing matched
    msg = f"Error, '_set_keys' has no match for OS type: '{os_type}'"
    raise NotImplementedError(msg)


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
    raw_output = [str(o) for o in output if isinstance(o, (str, int))]
    ntc_output = [o for o in output if isinstance(o, dict)]
    if len(raw_output) != 0 and output != raw_output:
        pass  # Pass instead of RAISE as it changes all int into str (makes MYPY checks easier)
    elif len(ntc_output) != 0 and output != ntc_output:
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


def format_vlan(output: list[dict[str, Any]]) -> dict[str | int, Any]:
    """Format vlan output into the data structure.

    Args:
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str | int, Any]: {vlan: {name: x, intf:[x,y]}}
    """
    result: dict[str | int, dict[str, dict[str, list[str]]]] = defaultdict(dict)
    for each_vl in output:
        vl_id = _make_int(each_vl["vlan_id"])
        result[vl_id]["name"] = each_vl["vlan_name"]
        result[vl_id]["intf"] = each_vl["interfaces"]
    for each_item in [1002, 1003, 1004, 1005]:
        if result.get(each_item) is not None:
            del result[each_item]
    return dict(result)


def format_stp(val_file: bool, output: list[dict[str, Any]]) -> dict[str | int, Any]:
    """Format STP into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str | int, Any]: {vlan: {intfx: FWD, intfy: FWD}}, if val_file is {vlan: {'intf': [intfx, intfy]}}
    """
    result: dict[str | int, dict[str, Any]] = defaultdict(dict)
    for each_vl in output:
        # If creating actual state
        if not val_file:
            result[_make_int(each_vl["vlan_id"])][each_vl["interface"]] = each_vl[
                "status"
            ]
        # If creating validation file
        elif val_file:
            if result.get(_make_int(each_vl["vlan_id"])) is None:
                result[_make_int(each_vl["vlan_id"])]["intf"] = [each_vl["interface"]]
            elif isinstance(result[_make_int(each_vl["vlan_id"])]["intf"], list):
                result[_make_int(each_vl["vlan_id"])]["intf"].append(
                    each_vl["interface"]
                )
    return dict(result)


def format_mac_table(key: OsKeys, output: list[str]) -> dict[str, str | int]:
    """Format MAC table count into the data structure.

    Args:
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[str]): The command output from the device raw data structure
    Results:
        dict[str, str | int]: {total_mac_count: x, vlx_mac_count: x}
    """
    result = {}
    # Total MAC count is always first element in list
    try:
        result["total_mac_count"] = _make_int(output[0].split()[-1])
    except Exception as e:
        result["total_mac_count"] = 0
    # Per-VLAN MAC count are in 2 consecutive cmds, first VL to match on and second the count
    for idx, each_item in enumerate(output):
        each_item = str(each_item)
        if key.mac_table_match in each_item:
            name = f"vl{each_item.split()[key.mac_table_element].replace(':', '')}_mac_count"
            result[name] = _make_int(output[idx + key.mac_table_idx].split()[-1])
            output[idx] = ""
            output[idx + 1] = ""
    return dict(result)


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,
    os_type: str,
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
        dict[Any, Any]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### VLAN: {vlan: {name: x, intf:[x,y]}}
    if sub_feature == "vlan":
        return format_vlan(ntc_output)

    ### STP: {vlan: {intfx: FWD, intfy: FWD}}, if val_file is {vlan: {'intf': [intfx, intfy]}}
    elif sub_feature == "stp_vlan":
        return format_stp(val_file, ntc_output)

    ### MAC TABLE COUNT: {total_mac_count: x, vlx_mac_count: x}
    elif sub_feature == "mac_table":
        return format_mac_table(key, raw_output)

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
