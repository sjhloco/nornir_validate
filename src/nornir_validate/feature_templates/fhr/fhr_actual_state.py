import re
from collections import defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    hsrp_intf: str
    hsrp_prio: str
    hsrp_state: str


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: A NamedTuple with the keys for interface, priority, and state
    """
    if "ios" in os_type:
        return OsKeys("interface", "priority", "state")
    elif "nxos" in os_type:
        return OsKeys("sh_if_index", "sh_prio", "sh_group_state")
    elif bool(re.search("asa", os_type)):  # noqa: SIM114
        pass
    elif bool(re.search("wlc", os_type)):
        pass
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


def _fix_nxos(
    main_dict: dict[str, Any], parent_name: str, child_name: str
) -> list[dict[str, Any]]:
    """NXOS JSON makes dict rather than list if only 1 item in output. If the child_dict is a dict this methods convert it to a list.

    Args:
        main_dict (dict[str, Any]): The dictionary of the command output
        parent_name (str): The parent dictionary key name (e.g. TABLE_xx)
        child_name (str): The key of the dictionary that you want to fix, for example ROW_xx
    Returns:
        A list of dictionaries
    """
    child_dict_value: list[dict[str, Any]] | dict[str, Any] = main_dict[parent_name][
        child_name
    ]
    if isinstance(child_dict_value, dict):
        child_dict_value = [child_dict_value]
    return child_dict_value


def format_hsrp(
    key: OsKeys, output: list[dict[str, Any]]
) -> dict[str, dict[str, str | int]]:
    """Format HSRP output into the data structure.

    Args:
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str, dict[str, str | int]]: {intf: {priority: x, state: y}
    """
    result: dict[str, dict[str, str | int]] = defaultdict(dict)
    for each_nbr in output:
        result[each_nbr[key.hsrp_intf]]["priority"] = _make_int(each_nbr[key.hsrp_prio])
        result[each_nbr[key.hsrp_intf]]["state"] = each_nbr[key.hsrp_state]
    return dict(result)


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,  # noqa: ARG001
    os_type: str,
    sub_feature: str,
    output: list[str | dict[str, str]],
) -> dict[str, dict[str, str | int]]:
    """Engine to run all the actual state and validation file sub-feature formatting.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[str | dict[str, str]]): The structured (dict from NTC template) or unstructured (str/int from raw) command output from the device
    Returns:
        dict[str, dict[str, str | int]]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### HSRP: {intf: {priority: x, state: y})
    if sub_feature == "hsrp":  # noqa: SIM102
        if bool(re.search("nxos", os_type)):
            ntc_output = _fix_nxos(ntc_output[0], "TABLE_grp_detail", "ROW_grp_detail")
        return format_hsrp(key, ntc_output)

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
