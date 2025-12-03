import re
from collections import defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    ha_state_local: str
    ha_state_peer: str


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "ios" in os_type:
        return OsKeys("active_software_state", "standby_software_state")
    elif "asa" in os_type:
        return OsKeys("service_state", "service_state_mate")
    elif "wlc" in os_type:
        return OsKeys("local_state", "peer_state")
    elif "panos" in os_type:
        return OsKeys("state", "")
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


def format_ha_state(
    key: OsKeys, os_type: str, output: list[dict[str, Any]]
) -> dict[str, str]:
    """Format HA state into the data structure.

    Args:
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        os_type (str): The different Nornir platforms which are OS type of the device
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str, str]: {local_state: x, peer_state: x}
    """
    result = {}
    if bool(re.search("asa", os_type)):
        result["local"] = output[0][key.ha_state_local][0]
        result["peer"] = output[0][key.ha_state_peer][0]
    elif bool(re.search("panos", os_type)):
        state = output[0][key.ha_state_local].split("-")[0]
        result["local"] = state
        result["peer"] = "standby" if state == "active" else "active"
    else:
        result["local"] = output[0][key.ha_state_local]
        result["peer"] = output[0][key.ha_state_peer]
    return dict(result)


def format_sw_stack(val_file: bool, output: list[dict[str, Any]]) -> dict[str, Any]:
    """Format switch stack into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {switchx: {priority: x, role: x, state: x}}, val)file doesn't have 'state: x'
    """
    result: dict[str, dict[str, str | int]] = defaultdict(dict)
    for each_swi in output:
        swi = f"switch{_make_int(each_swi['switch'])}"
        result[swi]["role"] = each_swi["role"]
        result[swi]["priority"] = _make_int(each_swi["priority"])
        result[swi]["role"] = each_swi["role"]
        # If creating actual state also needs state (is implicit in val file)
        if not val_file:
            result[swi]["state"] = each_swi["state"]
    return dict(result)


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,  # noqa: ARG001
    os_type: str,
    sub_feature: str,
    output: list[str | dict[str, str]],
) -> dict[str, Any]:
    """Engine to run all the actual state and validation file sub-feature formatting.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[str | dict[str, str]]): The structured (dict from NTC template) or unstructured (str/int from raw) command output from the device
    Returns:
        dict[str, Any]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### HA_STATE: {local_state: x, peer_state: x}
    if sub_feature == "ha_state":
        return format_ha_state(key, os_type, ntc_output)
    ### SWI_STACK: show switch - {switchx: {priority: x, role: x, state: x}}, val_file doesn't have 'state: x'.
    elif sub_feature == "sw_stack":
        return format_sw_stack(val_file, ntc_output)
    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
