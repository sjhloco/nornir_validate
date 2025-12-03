from typing import NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    conn_line: int
    conn_pos: int


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "asa" in os_type:
        return OsKeys(0, -1)
    elif "panos" in os_type:
        return OsKeys(1, -2)
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


def format_conn_count(key: OsKeys, output: list[str]) -> str | int:
    """Format FW conns into the data structure.

    Args:
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure OR raw data structure
    Returns:
        str:  {conn_count: xx}
    """
    return _make_int(output[key.conn_line].split()[key.conn_pos])


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,  # noqa: ARG001
    os_type: str,
    sub_feature: str,
    output: list[str | dict[str, str]],
) -> int | str:
    """Engine to run all the actual state and validation file sub-feature formatting.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[dict[str, Any]]): The structured (dict from NTC-tmpl) or unstructured str/int from raw) command output from the device
    Returns:
        dict[str, Any]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### FW_CONN_COUNT: {conn_count: xx}
    if sub_feature == "conn_count":
        return format_conn_count(key, raw_output)

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
