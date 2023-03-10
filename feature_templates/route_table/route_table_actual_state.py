from typing import Dict, List
import re
import ipaddress


# ----------------------------------------------------------------------------
# Mini-functions used by the main function
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


def _get_pfxlen(network: str, mask: str) -> str:
    """
    > This function takes a network and a mask and returns the network with the prefix length

    :param network: The network address of the subnet
    :type network: str
    :param mask: The subnet mask of the network
    :type mask: str
    :return: the prefix length of the network.
    """
    ip_mask = network + "/" + mask
    ip_pfxlen = ipaddress.IPv4Interface(ip_mask).with_prefixlen
    return ip_pfxlen


# ----------------------------------------------------------------------------
# Engine that runs the actual state sub-feature formatting for all os types
# ----------------------------------------------------------------------------
def format_actual_state(
    os_type: str, sub_feature: str, output: List, tmp_dict: Dict[str, None]
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

    ### KEY: Set the dictionary keys to use on a per-OS basis
    if bool(re.search("ios", os_type)):
        route_count = 2
        route_nhip = "nexthop_ip"
        route_nhif = "nexthop_if"
    elif bool(re.search("nxos", os_type)):
        route_count = -1
        route_nhip = "nexthop_ip"
        route_nhif = "nexthop_if"
    elif bool(re.search("asa", os_type)):
        route_count = 2
        route_nhip = "nexthopip"
        route_nhif = "nexthopif"
    elif bool(re.search("wlc", os_type)):
        pass

    # ----------------------------------------------------------------------------
    # VRF: {vrf: [intfx, intfy]}}
    # ----------------------------------------------------------------------------
    if sub_feature == "vrf":
        for each_vrf in output:
            if tmp_dict.get(each_vrf["name"]) == None:
                try:
                    tmp_dict[each_vrf["name"]]["intf"] = each_vrf["interfaces"]
                except:
                    tmp_dict[each_vrf["name"]]["intf"] = [each_vrf["interface"]]
            else:
                tmp_dict[each_vrf["name"]]["intf"].append(each_vrf["interface"])

    # ----------------------------------------------------------------------------
    # RTE_COUNT: {global_subnets: x, xx_subnets: x})
    # ----------------------------------------------------------------------------
    if sub_feature == "route_count":
        for idx, each_item in enumerate(output):
            if "IP" in each_item:
                tmp = each_item.replace("maximum-paths is", "name is default")
                vrf = tmp.split()[5].replace('"', "").replace("default", "global")
                tmp_dict[vrf] = _make_int(output[idx + 1].split()[route_count])

    # ----------------------------------------------------------------------------
    # ROUTE: {vrf: {route/prefix: type: x, nh: y}})
    # ----------------------------------------------------------------------------
    elif sub_feature == "route":
        for each_rte in output:
            # Creates variables used to create data model
            vrf = each_rte.get("vrf", "global").replace("default", "global")
            if len(vrf) == 0:
                vrf = "global"
            rte = _get_pfxlen(each_rte["network"], each_rte["mask"])
            regex = r"^L$|^local$|^C$|^direct$"
            if re.search(regex, each_rte["protocol"]) or each_rte[route_nhip] == "":
                nh = each_rte[route_nhif]
            else:
                nh = each_rte[route_nhip]
            if len(each_rte["type"]) == 0:
                rte_type = each_rte["protocol"]
            else:
                rte_type = f"{each_rte['protocol']} {each_rte['type']}"
            # If VRF doesn't exist add VRF and route
            if tmp_dict.get(vrf) == None:
                tmp_dict[vrf] = {rte: {"nh": nh, "rtype": rte_type}}
            # If route doesn't exist add it, if already exists add additional non-duplicate next-hops
            else:
                if tmp_dict[vrf].get(rte) == None:
                    tmp_dict[vrf].update({rte: {"nh": nh, "rtype": rte_type}})
                elif not isinstance(tmp_dict[vrf][rte]["nh"], list):
                    if tmp_dict[vrf][rte]["nh"] != nh:
                        tmp_dict[vrf][rte]["nh"] = [tmp_dict[vrf][rte]["nh"]]
                        tmp_dict[vrf][rte]["nh"].append(nh)
                else:
                    tmp_dict[vrf][rte]["nh"].append(nh)

    return dict(tmp_dict)
