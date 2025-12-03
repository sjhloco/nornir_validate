import ipaddress
import re
from collections import defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    count_match: str
    count_iter: int
    route_mask: str
    route_nhip: str
    route_nhif: str
    route_type: str


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "ios" in os_type:
        return OsKeys("IP", 2, "prefix_length", "nexthop_ip", "nexthop_if", "protocol")
    elif "nxos" in os_type:
        return OsKeys("IP", -1, "prefix_length", "nexthop_ip", "nexthop_if", "protocol")
    elif "asa" in os_type:
        return OsKeys("IP", 2, "netmask", "nexthopip", "nexthopif", "protocol")
    elif "panos" in os_type:
        return OsKeys("IPv6", 3, "prefix_length", "nexthop_ip", "nexthop_if", "flags")
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


def format_vrf(output: list[dict[str, Any]]) -> dict[str | int, Any]:
    """Format VRF output into the data structure.

    Args:
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {vrf: [intfx, intfy]}
    """
    result: dict[str | int, list[str]] = {}
    for each_vrf in output:
        vrf_name = _make_int(each_vrf["name"])
        if result.get(vrf_name) is None:
            try:
                result[vrf_name] = each_vrf["interfaces"]
            except KeyError:
                result[vrf_name] = [each_vrf["interface"]]
        else:
            result[vrf_name].append(each_vrf["interface"])
    return dict(result)


def format_rte_count(key: OsKeys, os_type: str, output: list[str]) -> dict[str, Any]:
    """Format route count output into the data structure.

    Args:
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        os_type (str): The different Nornir platforms which are OS type of the device
        output (list[dict[str, str]]): The command output from the device in raw data structure
    Returns:
        dict[str, Any]: {global_subnets: x, xx_subnets: x}
    """
    result: dict[str, int | str] = {}
    for idx, each_item in enumerate(output):
        if key.count_match in each_item:
            # Needed for Panos as no VRFs
            if bool(re.search("panos", os_type)):
                vrf = "global"
            else:
                tmp = each_item.replace("maximum-paths is", "name is default")
                vrf = tmp.split()[5].replace('"', "").replace("default", "global")
            result[vrf] = _make_int(output[idx + 1].split()[key.count_iter])
    return dict(result)


def format_route(key: OsKeys, output: list[dict[str, Any]]) -> dict[str, Any]:
    """Format table output into a structured route dictionary.

    Args:
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, Any]]): The command output from the device in ntc data structure

    Returns:
        dict[str, Any]: {vrf: {route/prefix: type: x, nh: y}})
    """
    result: dict[str, dict[str, dict[str, str | list[str]]]] = defaultdict(dict)

    # Helper functions used only by this function
    def _get_pfxlen(network: str, mask: str) -> str:
        """Takes a network and a mask and returns the network/prefix length."""
        ip_mask = network + "/" + mask
        ip_pfxlen = ipaddress.IPv4Interface(ip_mask).with_prefixlen
        return ip_pfxlen

    def _select_next_hop(each_rte: dict[str, str]) -> str:
        """Determine next-hop IP or interface."""
        proto_regex = re.compile(r"^L$|^local$|^C$|^direct$|A C")
        if proto_regex.search(each_rte[key.route_type]) or not each_rte[key.route_nhip]:
            return each_rte[key.route_nhif]
        return each_rte[key.route_nhip]

    def _format_route_type(each_rte: dict[str, str]) -> str:
        """Format route type string."""
        return (
            each_rte[key.route_type].replace("A ", "").replace("A?", "")
            if not each_rte.get("type", "")
            else f"{each_rte[key.route_type]} {each_rte['type']}"
        )

    for each_rte in output:
        if not isinstance(each_rte, dict):
            continue
        # VRF Handling
        vrf = each_rte.get("vrf", "global").replace("default", "global") or "global"
        # Route + Next-Hop
        rte = _get_pfxlen(each_rte["network"], each_rte[key.route_mask])
        nh = _select_next_hop(each_rte)
        rte_type = _format_route_type(each_rte)

        # Insert the above into result
        vrf_routes = result.setdefault(vrf, {})
        if rte not in vrf_routes:
            # First time seeing this route
            vrf_routes[rte] = {"nh": nh, "rtype": rte_type}
        else:
            existing_nh = vrf_routes[rte]["nh"]
            if isinstance(existing_nh, list):
                existing_nh.append(nh)
            elif existing_nh != nh:
                vrf_routes[rte]["nh"] = [existing_nh, nh]

    return dict(result)


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,  # noqa: ARG001
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
        dict[str, Any]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### VRF: {vrf: [intfx, intfy]}
    if sub_feature == "vrf":
        return format_vrf(ntc_output)

    ### RTE_COUNT: {global_subnets: x, xx_subnets: x}
    elif sub_feature == "route_count":
        return format_rte_count(key, os_type, raw_output)

    ### ROUTE: {vrf: {route/prefix: type: x, nh: y}})
    elif sub_feature == "route":
        return format_route(key, ntc_output)

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
