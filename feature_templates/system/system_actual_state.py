import ipaddress
import re
import trace
from collections import defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    image_version: str
    mgmt_acl_name: str
    mgmt_acl_seq: str
    sla_grp: str
    sla_dst: str
    sla_rtt: str
    sla_state: str


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "ios" in os_type:
        return OsKeys(
            "version", "acl_name", "line_num", "interface", "name", "rtt", "status"
        )
    elif "nxos" in os_type:
        return OsKeys("os", "name", "sn", "", "", "", "")
    elif "asa" in os_type:
        return OsKeys("version", "name", "sn", "", "", "", "")
    elif "wlc" in os_type:
        return OsKeys("product_version", "", "", "", "", "", "")
    elif "panos" in os_type:
        return OsKeys(
            "os", "", "", "grp_name", "destination", "rtt_avg", "success_rate"
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


def _acl_format_into_dict(
    output: list[dict[str, str]], name: str
) -> dict[str, list[dict[str, str]]]:
    """From a list of ACEs, removes the empty dicts and creates a dict of ACLs.

    Args:
        output (list[dict[str, str]]): List of ACE entries
        name (str): Name used in data structure as ACL name for this type of OS
    Returns:
        dict[str, list[dict[str, str]]]: A dict of ACLs with the name of the ACL as the key and a list of ACEs as the value
    """
    acl = {}
    acl_names = set(item[name] for item in output)
    for each_acl_name in acl_names:
        tmp_acl_list = []
        for each_ace in output:
            if each_ace.get("line_num", "dummy") == "":
                pass
            else:
                tmp_ace_dict = {}
                for ace_key, ace_val in each_ace.items():
                    # Add none blank ACE entries to dict of ACEs
                    if len(ace_val) != 0:
                        tmp_ace_dict[ace_key] = ace_val
                # Add dict of all none blank ACE entries to list of ACLs
                if each_acl_name == each_ace[name]:
                    tmp_acl_list.append(tmp_ace_dict)
            # Add all ACLs to dict of ACL names
            acl[each_acl_name] = tmp_acl_list
    return acl


def _acl_remove_remark(
    acl: dict[str, list[dict[str, str]]],
) -> dict[str, list[dict[str, str]]]:
    """Removes remark and reorders the seq number as NXOS gives remarks a sequence number (IOS doesnt).

    Args:
        acl (list[dict[str, str]]): Dictionary if ACLs
    Returns:
        dict[str, list[dict[str, str]]]: Same ACL dict but with remarks removed
    """
    for ace in acl.values():
        while "remark" in str(ace):
            ace_count = len(ace)
            for idx, each_ace in enumerate(ace):
                if each_ace["action"] == "remark":
                    for x in reversed(range(idx + 1, ace_count)):
                        ace[x]["sn"] = ace[x - 1]["sn"]
                    del ace[idx]
                    break
    return acl


def _acl_scr_dst(each_ace: dict[str, str], src_dst: str) -> str:
    """Converts the source or destination address of the ACE converted into address/prefix (IOS).

    Args:
        each_ace (dict[str, str]): Single ACL ACE
        src_dst (str): Either is the source (src) or (destination (dst) address
    Returns:
        str: Returns either the host or network address with prefix rather than subnet mask (or "any" as catchall)
    """
    if each_ace.get(src_dst + "_network") is not None:
        addr = each_ace[src_dst + "_network"] + "/" + each_ace[src_dst + "_wildcard"]
        return ipaddress.IPv4Interface(addr).with_prefixlen
    elif each_ace.get(src_dst + "_host") is not None:
        return ipaddress.IPv4Interface(each_ace[src_dst + "_host"]).with_prefixlen
    else:
        return each_ace[src_dst + "_any"]


def _acl_asa_format(output: list[str], name: str) -> list[dict[str, str]]:
    """Formats ASA SSH and HTTP ACLs into same data structure as normal switch ACLs.

    Args:
        output (list[str]): The command output from the device (raw)
        name (str): Name of access-list being standardised, ssh or http
    Returns:
        list[dict[str, str]]: List of dictionaries with the name, sequence number, action, and source for each ACE (same format as ACLs)
    """
    asa_acl_list = []
    seq = 10
    for each_ace in output:
        if re.match(f"^{name} [0-9]", each_ace):
            asa_dict = dict(name=name)
            asa_dict["sn"] = str(seq)
            asa_dict["action"] = "permit"
            ip_mask = each_ace.split()[1] + "/" + each_ace.split()[2]
            ip_pfxlen = ipaddress.IPv4Interface(ip_mask).with_prefixlen
            if ip_pfxlen == "0.0.0.0/0":
                asa_dict["source"] = f"{each_ace.split()[3]} - any"
            else:
                asa_dict["source"] = f"{each_ace.split()[3]} - {ip_pfxlen}"
            asa_acl_list.append(asa_dict)
            seq = seq + 10
    return asa_acl_list


def _acl_val_file(ace: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Creates a list of ace statements from an ACL for the validation file.

    Args:
        ace (list[dict[str, str]]): List of all ACEs for a ACL
    Returns:
        dict[str, list[dict[str, str]]]: Cleaned up ACL ACEs in format [{action: address/pfx}]
    """
    val_aces = []
    for each_ace in ace:
        try:
            val_aces.append({each_ace["action"]: each_ace["source"]})
        # For IOS as needs to convert subnet mask so in the format address/prefix
        except KeyError as e:
            val_aces.append({each_ace["action"]: _acl_scr_dst(each_ace, "src")})
    return dict(ace=val_aces)


def _acl_actual_state(
    ace: list[dict[str, str]], mgmt_acl_seq: str
) -> dict[int | str, dict[str, str]]:
    """Creates a dict of ace statements from an ACL for the actual state grouped by seq (key).

    Args:
        ace (list[dict[str, str]]): List of all ACEs for a ACL
        mgmt_acl_seq (str): os-specific name used to call the ACL
    Returns:
        dict[int | str, dict[str, str]]: Cleaned up ACL ACEs grouped by seq {seq: {'action': x, 'protocol': y, 'dst': 'any', 'src': address/pfx}}
    """
    ac_aces: defaultdict[int | str, dict[str, str]] = defaultdict(dict)
    for each_ace in ace:
        seq = _make_int(each_ace[mgmt_acl_seq])
        ac_aces[seq]["action"] = each_ace["action"]
        ac_aces[seq]["protocol"] = "ip"
        ac_aces[seq]["dst"] = "any"
        try:
            ac_aces[seq]["src"] = each_ace["source"]
        # For IOS as needs to convert subnet mask so in the format address/prefix
        except KeyError as e:
            ac_aces[seq]["src"] = _acl_scr_dst(each_ace, "src")
    return dict(ac_aces)


def _norm_ios_trk_grp(
    key: OsKeys, output: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Split tracker-group objects probes (trackers) into separate dictionaries.

    Args:
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure OR raw data structure
    Returns:
        list[dict[str, str]]: List of endpoint trackers grouped by tracker group
    """
    norm_output = []
    for probe in output:
        if probe.get(key.sla_grp) is None:
            # Split each probe element into lists
            rtts = probe[key.sla_rtt].split(", ")
            trackers = probe["trackers"].split(", ")
            tmp_status = probe["status"].split("(")[1].replace(")", "")
            statuses = (
                tmp_status.split(" OR ")
                if " OR " in tmp_status
                else tmp_status.split(" AND ")
            )
            # Loop through all elements simultaneously
            for rtt, status, tracker in zip(rtts, statuses, trackers, strict=False):
                norm_output.append(
                    {
                        key.sla_grp: probe[key.sla_dst],
                        key.sla_dst: tracker,
                        key.sla_rtt: rtt,
                        key.sla_state: status,
                    }
                )
        else:
            norm_output.append(probe)
    return norm_output


def _palo_sla_state(state: str) -> str:
    """Convert Palo Alto SLA success rate state to Up/Down.

    Args:
        state (str): The SLA state from Palo Alto based on probe success rate
    Returns:
        str: Palo SLA state of "Up" or "Down"
    """
    tmp_state = state.split("/")[0] if len(state.split("/")) > 1 else None
    if state.split("/")[0] == tmp_state:
        return "Up"
    else:
        return "Down"


def format_image(key: OsKeys, output: list[dict[str, str]]) -> str:
    """Format image into the data structure.

    Args:
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure OR raw data structure
    Returns:
        str:  {image: code_number}
    """
    return output[0][key.image_version]


def format_acl(
    val_file: bool, key: OsKeys, output: list[dict[str, str]]
) -> dict[str, dict[str, list[dict[str, str]]] | dict[int | str, dict[str, str]]]:
    """Format management ACL into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device
    Returns:
        dict[str, dict[str, list[dict[str, str]]] | dict[int | str, dict[str, str]]]: {seq: {'action': x, 'protocol': y, 'dst': 'any', 'src': address/pfx}},
        val_file is [{action: address/pfx}]
    """
    result: dict[
        str,
        dict[str, list[dict[str, str]]] | dict[int | str, dict[str, str]],
    ] = {}
    # Cleanup up data structure
    acl = _acl_format_into_dict(output, key.mgmt_acl_name)
    acl = _acl_remove_remark(acl)
    # Separate functions to create val file actual state
    for name, ace in acl.items():
        # If creating validation file
        if val_file:
            result[name] = _acl_val_file(ace)
        #  If creating the actual state
        elif not val_file:
            result[name] = _acl_actual_state(ace, key.mgmt_acl_seq)
    return result


def format_module(val_file: bool, output: list[dict[str, str]]) -> dict[str | int, Any]:
    """Format module into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        output (list[dict[str, str]]): The command output from the device in ntc data structure
    Returns:
        dict[str | int, Any]:  {module_num: {model: xxx, status, ok}}, val_file is {module_num: {model: xxx}}
    """
    result: dict[int | str, dict[str, str]] = defaultdict(dict)
    for each_mod in output:
        mod = _make_int(each_mod["module"])
        result[mod]["model"] = each_mod["model"]
        # If creating validation file
        if val_file:
            status = each_mod.get("status", "x").lower()
            if "active" in status or "standby" in status:
                result[mod]["status"] = each_mod["status"].lower()
        #  If creating the actual state
        elif not val_file:
            if len(each_mod["status"]) == 0:
                result[mod]["status"] = "ok"
            else:
                result[mod]["status"] = each_mod["status"].lower()
    return dict(result)


def format_sla(
    val_file: bool, os_type: str, key: OsKeys, output: list[dict[str, str]]
) -> dict[str, Any]:
    """Format SLA monitoring into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure OR raw data structure
    Returns:
        dict[str, Any]:  {cmd: {grp_name: {dst: {rtt: x, State: Up}}}}, val_file is {cmd: {grp_name: {dst: {rtt: x}}}}
    """
    result: dict[str, dict[str, dict[str, str | int]]] = defaultdict(dict)
    # Normalise IOS tracker group
    if "ios" in os_type:
        output = _norm_ios_trk_grp(key, output)
    # Run function on all SLAs
    for probe in output:
        try:
            # Round up/down floats as needs to be integer to all for =>, =<, etc
            rtt_num = float(probe[key.sla_rtt])
            result[probe[key.sla_grp]][probe[key.sla_dst]] = {"rtt": round(rtt_num)}
        except (ValueError, TypeError):
            result[probe[key.sla_grp]][probe[key.sla_dst]] = {
                "rtt": _make_int(probe[key.sla_rtt])
            }
        # Add state if it is the actual state
        if not val_file:
            if "panos" in os_type:
                result[probe[key.sla_grp]][probe[key.sla_dst]]["state"] = (
                    _palo_sla_state(probe[key.sla_state])
                )
            else:
                result[probe[key.sla_grp]][probe[key.sla_dst]]["state"] = probe[
                    key.sla_state
                ].capitalize()
    return dict(result)


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,
    os_type: str,
    sub_feature: str,
    output: list[str | dict[str, str]],
) -> str | dict[Any, Any]:
    """Engine to run all the actual state and validation file sub-feature formatting.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[str | dict[str, str]]): The structured (dict from NTC template) or unstructured (str/int from raw) command output from the device
    Returns:
        str | dict[Any, Any]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### IMAGE: {image: code_number}
    if sub_feature == "image":
        return format_image(key, ntc_output)

    ### MGMT_ACL: {acl_name: seq_num: {protocol: ip/tcp/udp, src: src_ip (or as intf - src_ip), dst: dst_ip, dst_port: port}}
    elif sub_feature == "mgmt_acl":
        if bool(re.search("asa", os_type)):
            ntc_output = _acl_asa_format(raw_output, "ssh")
            ntc_output.extend(_acl_asa_format(raw_output, "http"))
        return format_acl(val_file, key, ntc_output)

    ### MODULE: {module_num: {model: xxx, status, ok}}
    elif sub_feature == "module":
        return format_module(val_file, ntc_output)

    ### SLA: {cmd: {grp_name: {dst: {rtt: x, State: Up}}}}
    if sub_feature == "sla":
        return format_sla(val_file, os_type, key, ntc_output)

    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
