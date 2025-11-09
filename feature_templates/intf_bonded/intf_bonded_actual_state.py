import re
from collections import defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    po_name: str
    po_status: str
    po_protocol: str
    po_intf: str


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "ios" in os_type or "nxos" in os_type or "asa" in os_type:
        return OsKeys(
            "bundle_name", "bundle_status", "bundle_protocol", "member_interface"
        )
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


def _format_status(status: str) -> str:
    """Takes the status and for NXOS removes additional letters and brackets and returns a string.

    Args:
        status (str): The status of the port-channel or PO member interface
    Returns:
        str: Returns cleaned up status without any additional letters and brackets
    """
    if re.match(f".*U", status):
        status = "U"
    return status.replace("(", "").replace(")", "")


def format_po(
    val_file: bool, key: OsKeys, output: list[dict[str, Any]]
) -> dict[str, Any]:
    """Format port-channel into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {po_name: {protocol: type, status: code, members: {intf_name: {mbr_status: code}}}}, val_file is {po_name: {protocol: type, members: [intf_x, intf_y]}}
    """
    result: dict[str, dict[str, str | dict[str, dict[str, str]]]] = defaultdict(dict)
    for each_po in output:
        if each_po[key.po_protocol] == "-":
            each_po[key.po_protocol] = "NONE"
        result[each_po[key.po_name]]["protocol"] = each_po[key.po_protocol].upper()
        # Val_file doesn't get status of PO or its member ports (is just a list of them)
        if val_file:
            result[each_po[key.po_name]]["members"] = each_po[key.po_intf]
        # The actual_state gets the PO status as well as member port status
        if not val_file:
            result[each_po[key.po_name]]["status"] = _format_status(
                each_po[key.po_status]
            )
            po_mbrs = {}
            for mbr_intf, mbr_status in zip(
                each_po[key.po_intf], each_po[f"{key.po_intf}_status"], strict=False
            ):
                # For routers as use bndl rather than P
                if mbr_status == "bndl":
                    mbr_status = "P"
                # Creates dict of members to add to as value in the PO dictionary
                po_mbrs[mbr_intf] = {"mbr_status": _format_status(mbr_status)}
            result[each_po[key.po_name]]["members"] = po_mbrs
    return dict(result)


def format_vpc_peer(val_file: bool, output: list[dict[str, Any]]) -> dict[str, Any]:
    """Format vpc_peer link info into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {role: x, 'peerlink_vlans': [x,y], 'peerlink_port_state': x, 'peer_status': x, 'keepalive_status': x, 'vlan_consistency': x, 'peer_consistency': x, 'type2_consistency': x},
        val_file is just {role: x, 'peerlink_vlans': [x,y]}
    """
    result: dict[str, str | int | list[str | int] | dict[str, str]] = defaultdict(dict)
    # Common for both actual_state and val_file
    result["role"] = output[0]["vpc-role"]
    peer_link = output[0]["TABLE_peerlink"]["ROW_peerlink"]
    trunk_vl = peer_link["peer-up-vlan-bitset"]
    result["peerlink_vlans"] = [_make_int(vl) for vl in trunk_vl.split(",")]
    # If creating actual state also needs state (is implicit in val file)
    if not val_file:
        result["peerlink_port_state"] = _make_int(peer_link["peer-link-port-state"])
        result["peer_status"] = output[0]["vpc-peer-status"]
        result["keepalive_status"] = output[0]["vpc-peer-keepalive-status"]
        result["vlan_consistency"] = output[0]["vpc-per-vlan-peer-consistency"]
        result["peer_consistency"] = output[0]["vpc-peer-consistency-status"]
        result["type2_consistency"] = output[0]["vpc-type-2-consistency-status"]
    return dict(result)


def format_vpcs(val_file: bool, output: list[dict[str, str]]) -> dict[str | int, Any]:
    """Format vpcs into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str | int, Any]: {vpc_xx: {'po': x, 'vlans': [x,y], 'port_state': x, 'consistency_status': x}, val_file {vpc_xx: {'po': x, 'vlans': [x,y]}
    """
    result: dict[str | int, dict[str, str | int | list[str | int]]] = defaultdict(dict)
    all_vpcs = _fix_nxos(output[0], "TABLE_vpc", "ROW_vpc")
    for vpc in all_vpcs:
        vpc_id = _make_int(vpc["vpc-id"])
        result[vpc_id]["po"] = vpc["vpc-ifindex"]
        trunk_vl = vpc["up-vlan-bitset"]
        result[vpc_id]["vlans"] = [_make_int(vl) for vl in trunk_vl.split(",")]
        # If creating actual state also needs state (is implicit in val file)
        if not val_file:
            result[vpc_id]["port_state"] = _make_int(vpc["vpc-port-state"])
            result[vpc_id]["consistency_status"] = vpc["vpc-consistency-status"]
    return dict(result)


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,
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
    aw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### PORT_CHANNEL: {po_name: {protocol: type, status: code, members: {intf_name: {mbr_status: code}}}}
    if sub_feature == "port_channel":
        return format_po(val_file, key, ntc_output)

    ### VPC: see below
    elif sub_feature == "vpc":
        # {role: x, 'peerlink_vlans': [x,y], 'peerlink_port_state': x, 'peer_status': x,'keepalive_status': x, 'vlan_consistency': x, 'peer_consistency': x, 'type2_consistency': x}, val_file is just {role: x, 'peerlink_vlans': [x,y]}
        vpc_result = format_vpc_peer(val_file, ntc_output)
        # TABLE_vpc is only present if are vPCs configured
        if ntc_output[0].get("TABLE_vpc") is not None:
            # {vpc_xx: {'po': x, 'vlans': [x,y], 'port_state': x, 'consistency_status': x}, val_file {vpc_xx: {'po': x, 'vlans': [x,y]}
            all_vpcs: dict[Any, Any] = format_vpcs(val_file, ntc_output)
            vpc_result["vpcs"] = all_vpcs
        return vpc_result

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
