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


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,  # noqa: ARG001
    os_type: str,  # noqa: ARG001
    sub_feature: str,
    output: list[str],
) -> int | str:
    """Takes cmd output and just returns the numerical value.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[str]): The structured (dict from NTC template) or unstructured (str/int from raw) command output from the device
    Returns:
        int | str: {mab_count: xx}
    """
    ### MAB_COUNT: {mab_count: xx}
    if sub_feature == "mab_count" or sub_feature == "dot1x_count":
        return _make_int(output[0].split()[-1])

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
