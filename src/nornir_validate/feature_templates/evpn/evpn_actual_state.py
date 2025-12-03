from collections import defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    nve_vni_bd_vrf: str


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "ios" in os_type:
        return OsKeys("vrf")
    elif "nxos" in os_type:
        return OsKeys("bd_vrf")
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


def format_nve_vni(
    val_file: bool, key: OsKeys, output: list[dict[str, str]]
) -> dict[str | int, Any]:
    """Format NVE VNI into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str | int, Any]: {l3vni: {bdi_vrf: z, state: Up}}, val file doesn't include state
    """
    result: dict[str | int, dict[str, str | int]] = defaultdict(dict)
    for each_vni in output:
        vni = _make_int(each_vni["vni"])
        if "L2" in each_vni["mode"]:
            result[vni]["bd_vrf"] = _make_int(each_vni["bd"])
        else:
            result[vni]["bd_vrf"] = _make_int(each_vni[key.nve_vni_bd_vrf])
        # If creating actual state
        if not val_file:
            result[vni]["state"] = each_vni["state"]
    return dict(result)


def format_nve_peer(
    val_file: bool, output: list[dict[str, str]]
) -> dict[str, str] | list[str]:
    """Format NVE VNI into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str, str] | list[str]: {peer1_ip: state: Up}, val file is just list a [peer_ip, peer_ip]
    """
    result = {}
    val_file_list: list[str] = []
    for each_peer in output:
        result[each_peer["peer"]] = each_peer["state"].capitalize()
        if each_peer["peer"] not in str(val_file_list):
            val_file_list.append(each_peer["peer"])
    # List of peers if is a validation file
    if val_file:
        return val_file_list
    else:
        return result


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,  # noqa: ARG001
    os_type: str,
    sub_feature: str,
    output: list[str | dict[str, str]],
) -> dict[Any, Any] | list[str]:
    """Engine to run all the actual state and validation file sub-feature formatting.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[str | dict[str, str]]): The structured (dict from NTC template) or unstructured (str/int from raw) command output from the device
    Returns:
        dict[Any, Any] | list[str]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### NVE_VNI: {l3vni: {bdi_vrf: z, state: Up}}, val file doesn't include state
    if sub_feature == "nve_vni":
        return format_nve_vni(val_file, key, ntc_output)
    ### NVE_PEER: {peer1_ip: state: Up}, val file is just list a [peer_ip, peer_ip]
    elif sub_feature == "nve_peer":
        return format_nve_peer(val_file, ntc_output)
    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
