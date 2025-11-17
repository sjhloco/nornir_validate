import re
from collections import Counter, defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    neighbor_id: str
    bgp_nhbr: str
    bgp_nhbr_as: str
    bgp_pfxrcd: str


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "ios" in os_type:
        return OsKeys(
            "neighbor_id", "bgp_neighbor", "neighbor_as", "state_or_prefixes_received"
        )
    elif "nxos" in os_type:  # noqa: SIM114
        return OsKeys("neighbor_id", "bgp_neigh", "neigh_as", "state_pfxrcd")
    elif "asa" in os_type:
        return OsKeys("neighbor_id", "bgp_neigh", "neigh_as", "state_pfxrcd")
    elif "panos" in os_type:
        return OsKeys("", "bgp_neighbor", "neighbor_as", "accepted_pfx")
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


def format_eigrp_nhbr(val_file: bool, output: list[dict[str, Any]]) -> dict[str, Any]:
    """Format EIGRP neighbor output into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {intf: {asn: x, nbr: {nbr_ip: up}}, val_file is {intf: {asn: x, nbr: nbr_ip}}
    """
    result: dict[str, dict[str, str | int | dict[str, str]]] = defaultdict(dict)
    for each_nbr in output:
        intf = each_nbr["interface"]
        state = "down" if len(each_nbr["uptime"]) == 0 else "up"
        if result.get(intf) is None:
            result[intf]["asn"] = _make_int(each_nbr["as"])
        # val_file
        if val_file:
            result[intf]["nbr"] = each_nbr["ip_address"]
        # actual state
        elif not val_file:
            result[intf]["nbr"] = {each_nbr["ip_address"]: state}
    return dict(result)


def format_ospf_nhbr(
    val_file: bool, os_type: str, key: OsKeys, output: list[dict[str, Any]]
) -> dict[str, Any]:
    """Format OSPF interface and neighbor outputs into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {intf: {pid, x, area: x, nbr: {nbr_ip: FULL}}, val file is {intf: {pid, x, area: x, nbr: [nbr_ip, nbr_ip]}}
    """
    result: dict[str, Any] = defaultdict(dict)

    # Helper functions used only by this function
    def _remove_char(input_data: str, char: str) -> str:
        """If specified character the input data, return the input data split on the specified character, otherwise return the input data."""
        if char in input_data:
            return input_data.split(char)[0]
        else:
            return input_data

    def _ospf_nhbr(
        neighbor_id: str,
        output: list[dict[str, Any]],
        tmp_dict_nbr: defaultdict[str, Any],
    ) -> dict[str, list[str] | dict[str, str | int | dict[str, str]]]:
        """Returns formatted OSPF neighbors combined and grouped by interface."""
        for each_intf in output:
            # Data from "show ip int br" is saved in result
            if each_intf.get("process") is not None:
                pid = _make_int(each_intf["process"])
                result[each_intf["interface"]]["pid"] = pid
                result[each_intf["interface"]]["area"] = _make_int(each_intf["area"])
                # If is actual state adds empty dict
                if tmp_dict_nbr.default_factory is dict:
                    result[each_intf["interface"]]["nbr"] = {}
            # Data from "show ip ospf neigh" is saved in tmp_dict_nbr (list is val_file, dict actual_state)
            elif tmp_dict_nbr.default_factory is list:
                tmp_dict_nbr[each_intf["interface"]].extend([each_intf[neighbor_id]])
            elif tmp_dict_nbr.default_factory is dict:
                state = _remove_char(each_intf["state"], "/")
                tmp_dict_nbr[each_intf["interface"]][each_intf[neighbor_id]] = state
        return dict(tmp_dict_nbr)

    # INTF: Add OSPF intf and process/area to results and neigbors per interface to dict_nbr
    if val_file:
        dict_nbr = _ospf_nhbr(key.neighbor_id, output, defaultdict(list))
    elif not val_file:
        dict_nbr = _ospf_nhbr(key.neighbor_id, output, defaultdict(dict))
    # NBR: Add neighbors based on matching interfaces in results and dict_nbr
    for intf in result.keys():  # noqa: SIM118
        for intf1, nbr in dict_nbr.items():
            # ASA has to be treated differently as interfaces are logical names
            if bool(re.search("asa", os_type)):
                if intf == intf1:
                    result[intf]["nbr"] = nbr
            else:
                # Splits intf short and long names to then be able to interface number ([1:]) and short name is in long name ([0])
                spl_intf = re.split(r"(\D+)", intf.lower())[1:]
                spl_intf1 = re.split(r"(\D+)", intf1.lower())[1:]
                if spl_intf[1:] == spl_intf1[1:] and spl_intf[0] in spl_intf1[0]:
                    result[intf]["nbr"] = nbr
    return dict(result)


def format_ospf_lsdb(output: list[str]) -> dict[str | int, Any]:
    """Format OSPF LSDB count output into the data structure.

    Args:
        output (list[dict[str, str]]): The command output from the device in raw data structure
    Returns:
        ict[str | int, Any]: {process: total_lsa: x}
    """
    result: dict[str | int, dict[str, str | int]] = {}
    for idx, each_item in enumerate(output):
        if "Process ID" in each_item:
            proc = _make_int(each_item.split("s ID")[1].replace(")", "").split()[0])
            result[proc] = {"total_lsa": _make_int(output[idx + 1].split()[1])}
    return result


def format_bgp(
    os_type: str, key: OsKeys, output: list[dict[str, Any]]
) -> dict[str, Any]:
    """Format BGP peers into the data structure.

    Args:
        os_type (str): The different Nornir platforms which are OS type of the device
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {peer: {asn:x, rcv_pfx:x}}
    """
    result: dict[str, Any] = defaultdict(dict)

    # Helper functions used only by this function
    def _remove_dup_peers(
        output: list[dict[str, Any]], bgp_nhbr: str
    ) -> list[dict[str, str]]:
        """Removes duplicate peers from the IPv4 address family as likely to be the underlay peers."""
        neigh_counts = Counter(item[bgp_nhbr] for item in output)
        cln_output = [
            item
            for item in output
            if not (
                neigh_counts[item[bgp_nhbr]] > 1
                and item["address_family"] == "IPv4 Unicast"
            )
        ]
        return cln_output

    if not bool(re.search("asa", os_type)):
        cln_output = _remove_dup_peers(output, key.bgp_nhbr)
    else:
        cln_output = output
    for each_peer in cln_output:
        result[each_peer[key.bgp_nhbr]]["asn"] = _make_int(each_peer[key.bgp_nhbr_as])
        result[each_peer[key.bgp_nhbr]]["rcv_pfx"] = _make_int(
            each_peer[key.bgp_pfxrcd]
        )
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
        dict[str | int, Any]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### EIGRP_INTF_NBR: {intf: {asn: x, nbr: {nbr_ip: up}}
    if sub_feature == "eigrp_intf_nbr":
        return format_eigrp_nhbr(val_file, ntc_output)

    ### OSPF_INTF_NBR: {intf: {pid, x, area: x, nbr: {nbr_ip: FULL}}
    elif sub_feature == "ospf_intf_nbr":
        return format_ospf_nhbr(val_file, os_type, key, ntc_output)

    ### OSPF_LSDB_COUNT: {process: total_lsa: x}
    elif sub_feature == "ospf_lsdb_count":
        return format_ospf_lsdb(raw_output)

    ### BGP_PEER: {peer: {asn:x, rcv_pfx:x}}
    elif sub_feature == "bgp_peer":
        return format_bgp(os_type, key, ntc_output)

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
