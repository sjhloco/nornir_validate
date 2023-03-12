from typing import Dict, List
from collections import defaultdict
import re
from copy import copy


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
def _set_keys(os_type: List) -> Dict[str, Dict]:
    """
    Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures

    :param os_type: This is a list of strings that are the OS types of the devices in the inventory
    :type os_type: List
    """
    global ospf_nbr_ip, ospf_nbr_fam, bgp_addr_fam
    if bool(re.search("ios", os_type)):
        ospf_nbr_ip = "address"
        bgp_addr_fam = "addr_family"
    elif bool(re.search("nxos", os_type)):
        ospf_nbr_ip = "neighbor_ipaddr"
        bgp_addr_fam = "address_family"
    elif bool(re.search("asa", os_type)):
        ospf_nbr_ip = "address"
    elif bool(re.search("wlc", os_type)):
        pass


# ----------------------------------------------------------------------------
# DEF: Mini-functions used by the main function
# ----------------------------------------------------------------------------
def _make_int(input_data: str) -> int:
    """
    It takes a string and returns an integer if it can, otherwise it returns the original string

    :param input_data: The data to be converted to an integer
    :type input_data: str
    :return: the input_data as an integer.
    """
    try:
        return int(input_data)
    except:
        return input_data


def _remove_char(input_data: str, char: str) -> str:
    """
    "If the specified character is in the input data, return the input data split on the specified
    character, otherwise return the input data."

    :param input_data: The string to be modified
    :type input_data: str
    :param char: The character to remove
    :type char: str
    :return: The input_data is being split at the specified character and the first part of the split is
    being returned.
    """
    if char in input_data:
        return input_data.split(char)[0]
    else:
        return input_data


def _remove_dup_peers(input_data: List, bgp_addr_fam: str) -> List:
    """
    If duplicate peers remove the IPv4 address family as likely to be the underlay
    The function returns a list of dictionaries

    :param input_data: This is the list of dictionaries that we want to remove duplicates from
    :type input_data: List
    :param bgp_addr_fam: The address family to use for the BGP session
    :type bgp_addr_fam: str
    :return: A list of dictionaries
    """
    output = copy(input_data)
    for idx, each_peer in enumerate(input_data):
        for idx1, each_peer1 in enumerate(input_data):
            if each_peer["bgp_neigh"] == each_peer1["bgp_neigh"]:
                if each_peer[bgp_addr_fam] != each_peer1[bgp_addr_fam]:
                    if each_peer[bgp_addr_fam] == "IPv4 Unicast":
                        del output[idx]
                    elif each_peer[bgp_addr_fam] == "IPv4 Unicast":
                        del output[idx1]
    return output


def _format_ospf_lsdb(output: List, tmp_dict: Dict[str, None]) -> None:
    """Format OSPF LSDB and return data structure in tmp_dict"""
    for idx, each_item in enumerate(output):
        if "Process ID" in each_item:
            proc = _make_int(each_item.split("s ID")[1].replace(")", "").split()[0])
            lsdb_count = _make_int(output[idx + 1].split()[1])
            if lsdb_count != 0:
                tmp_dict[proc]["total_lsa"] = lsdb_count


def _format_bgp(os_type: List, output: List, tmp_dict: Dict[str, None]) -> None:
    """Format BGP peers and return data structure in tmp_dict"""
    if bool(re.search("asa", os_type)) == False:
        output = _remove_dup_peers(output, bgp_addr_fam)
    for each_peer in output:
        tmp_dict[each_peer["bgp_neigh"]]["asn"] = _make_int(each_peer["neigh_as"])
        tmp_dict[each_peer["bgp_neigh"]]["rcv_pfx"] = _make_int(
            each_peer["state_pfxrcd"]
        )


# ----------------------------------------------------------------------------
# VALIDATION: Engine to create the validation file sub-feature validations (for all os-types)
# ----------------------------------------------------------------------------
def generate_val_file(
    os_type: List, sub_feature: str, output: List, tmp_dict: Dict[str, None]
) -> Dict[str, Dict]:
    """
    > The function takes the command output and formats it into a dictionary that can be used
    in the validation file to validate features

    :param os_type: List
    :type os_type: List
    :param sub_feature: This is the sub-feature that you want to validate
    :type sub_feature: str
    :param output: the output of the command
    :type output: List
    :param tmp_dict: This is the dictionary that will be returned by the function
    :type tmp_dict: Dict[str, None]
    :return: A dictionary with the following keys:
        - image
        - mgmt_acl
        - module
    """
    _set_keys(os_type)

    ### EIGRP_INTF_NBR: {intf: {asn: x, nbr: [nbr_ip, nbr_ip]}}
    if sub_feature == "eigrp_intf_nbr":
        for each_nbr in output:
            intf = each_nbr["interface"]
            tmp_dict[intf]["asn"] = _make_int(each_nbr["as"])
            tmp_dict[intf]["nbr"] = each_nbr["address"]

    ### OSPF_INTF_NBR: {intf: {pid, x, area: x, nbr: [nbr_ip, nbr_ip]}}
    elif sub_feature == "ospf_intf_nbr":
        # Combine all interfaces into a dict
        dict_nbr = defaultdict(list)
        for each_intf in output:
            if each_intf.get("process") != None:
                pid = _make_int(each_intf["process"])
                tmp_dict[each_intf["interface"]]["pid"] = pid
                tmp_dict[each_intf["interface"]]["area"] = _make_int(each_intf["area"])
            else:
                dict_nbr[each_intf["interface"]].extend([each_intf[ospf_nbr_ip]])
        # Match neighbors to interfaces adding neighbors as a list to interfaces
        for intf in tmp_dict.keys():
            for intf1, nbr in dict_nbr.items():
                # ASA has to be treated differently as interfaces are logical names
                if bool(re.search("asa", os_type)):
                    if intf == intf1:
                        tmp_dict[intf]["nbr"] = nbr
                else:
                    spl_intf = re.split(r"(\D+)", intf.lower())[1:]
                    spl_intf1 = re.split(r"(\D+)", intf1.lower())[1:]
                    # If the interface number ([1:]) matches and the short name is in long name ([0])
                    if spl_intf[1:] == spl_intf1[1:] and spl_intf[0] in spl_intf1[0]:
                        tmp_dict[intf]["nbr"] = nbr

    ### OSPF_LSDB_COUNT: {process: total_lsa: x}
    elif sub_feature == "ospf_lsdb_count":
        _format_ospf_lsdb(output, tmp_dict)

    ### BGP_PEER: {peer: {asn:x, rcv_pfx:x}}
    if sub_feature == "bgp_peer":
        _format_bgp(os_type, output, tmp_dict)

    return dict(tmp_dict)


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine that runs the actual state sub-feature formatting for all os types
# ----------------------------------------------------------------------------
def format_actual_state(
    os_type: List, sub_feature: str, output: List, tmp_dict: Dict[str, None]
) -> Dict[str, Dict]:
    """
    > The function takes the command output and formats it into a dictionary that can be used
    to compare against the desired state

    :param os_type: str = The OS type of the device
    :type os_type: str
    :param sub_feature: This is the sub-feature of the feature you're working on. For example, if you're
    working on the "image" feature, the sub-feature would be "version"
    :type sub_feature: str
    :param output: The output from the device
    :type output: List
    :param tmp_dict: This is the dictionary that will be returned by the function
    :type tmp_dict: Dict[str, None]
    :return: A dictionary of dictionaries.
    """
    _set_keys(os_type)

    ### EIGRP_INTF_NBR: {intf: {asn: x, nbr: {nbr_ip: up}}
    if sub_feature == "eigrp_intf_nbr":
        for each_nbr in output:
            intf = each_nbr["interface"]
            if len(each_nbr["uptime"]) == 0:
                state = "down"
            else:
                state = "up"
            if tmp_dict.get(intf) == None:
                tmp_dict[intf]["asn"] = _make_int(each_nbr["as"])
                tmp_dict[intf]["nbr"] = {each_nbr["address"]: state}
            else:
                tmp_dict[intf]["nbr"][each_nbr["address"]] = state

    ### OSPF_INTF_NBR: {intf: {pid, x, area: x, nbr: {nbr_ip: FULL}}
    elif sub_feature == "ospf_intf_nbr":
        # Combine all interfaces into a dict
        dict_nbr = defaultdict(dict)
        for each_intf in output:
            if each_intf.get("process") != None:
                pid = _make_int(each_intf["process"])
                tmp_dict[each_intf["interface"]]["pid"] = pid
                tmp_dict[each_intf["interface"]]["area"] = _make_int(each_intf["area"])
                tmp_dict[each_intf["interface"]]["nbr"] = {}
            else:
                state = _remove_char(each_intf["state"], "/")
                dict_nbr[each_intf["interface"]][each_intf[ospf_nbr_ip]] = state
        # Match neighbors to interfaces adding neighbors as a list to interfaces
        for intf in tmp_dict.keys():
            for intf1, nbr in dict_nbr.items():
                # ASA has to be treated differently as interfaces are logical names
                if bool(re.search("asa", os_type)):
                    if intf == intf1:
                        tmp_dict[intf]["nbr"].update(nbr)
                else:
                    spl_intf = re.split(r"(\D+)", intf.lower())[1:]
                    spl_intf1 = re.split(r"(\D+)", intf1.lower())[1:]
                    # If the interface number ([1:]) matches and the short name is in long name ([0])
                    if spl_intf[1:] == spl_intf1[1:] and spl_intf[0] in spl_intf1[0]:
                        tmp_dict[intf]["nbr"].update(nbr)

    ### OSPF_LSDB_COUNT: {process: total_lsa: x}
    elif sub_feature == "ospf_lsdb_count":
        _format_ospf_lsdb(output, tmp_dict)

    ### BGP_PEER: {peer: {asn:x, rcv_pfx:x}}
    if sub_feature == "bgp_peer":
        _format_bgp(os_type, output, tmp_dict)

    return dict(tmp_dict)
