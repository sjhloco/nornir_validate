from typing import Dict, List
import ipaddress
from collections import defaultdict
import re
import ipdb

# ----------------------------------------------------------------------------
# Engine to run different formatters
# ----------------------------------------------------------------------------
def format_actual_state(
    os_type: str,
    cmd: str,
    output: List,
    tmp_dict: Dict[str, None],
    actual_state: Dict[str, None],
) -> Dict[str, Dict]:

    # NO_NTC: Catch all if no NTC template. Either return dummy to not error or converts string to a list
    non_ntc_tmpl_cmds = [
        "show bgp all summary",
        "show run ssh",
        "show run http",
        "show ip ospf database database-summary | in Total",
        "show ip eigrp interfaces",
        "show switch",
        "show  redundancy state | in state",
        "show nve vni",
        "show nve peers",
        "show crypto session brief",
        "show authentication sessions | count mab",
        "show authentication sessions | count dot1x",
    ]
    non_ntc_tmpl_regex_cmds = r"(show ip route .* summary \| in Total)|(show ip  route.*)|(show mac address-table .*)"
    if isinstance(output, str):
        if cmd in non_ntc_tmpl_cmds:
            output = output.lstrip().rstrip().splitlines()
        elif re.match(non_ntc_tmpl_regex_cmds, cmd):
            output = output.lstrip().rstrip().splitlines()
        # All other cmd outputs that are string are ignored to stop errors
        else:
            actual_state[cmd] = defaultdict(dict)
            return actual_state

    if bool(re.search("ios", str(os_type))):
        ios_format(cmd, output, tmp_dict, actual_state)
    elif bool(re.search("nxos", str(os_type))):
        nxos_format(cmd, output, tmp_dict, actual_state)
    elif bool(re.search("asa", str(os_type))):
        asa_format(cmd, output, tmp_dict, actual_state)
    return actual_state


# ----------------------------------------------------------------------------
# Mini-functions used by all OS types to keep DRY
# ----------------------------------------------------------------------------
# ACL_FORMAT: Removes all the empty dictionaries from ACL list of dicts
def _acl_format(input_acl: List) -> List:
    acl: List = []
    for each_acl in input_acl:
        tmp_acl = {}
        for ace_key, ace_val in each_acl.items():
            if len(ace_val) != 0:
                tmp_acl[ace_key] = ace_val
        acl.append(tmp_acl)
    return acl


# ACL_ADDR: Converts addressing into address/prefix
def _acl_scr_dst(each_ace: Dict[str, str], src_dst: str) -> str:
    if each_ace.get(src_dst + "_network") != None:
        addr = each_ace[src_dst + "_network"] + "/" + each_ace[src_dst + "_wildcard"]
        return ipaddress.IPv4Interface(addr).with_prefixlen
    elif each_ace.get(src_dst + "_host") != None:
        return ipaddress.IPv4Interface(each_ace[src_dst + "_host"]).with_prefixlen
    else:
        return each_ace[src_dst + "_any"]


# REMOVE: Removes the specified character and anything after it
def _remove_char(input_data: str, char: str) -> str:
    if char in input_data:
        return input_data.split(char)[0]
    else:
        return input_data


# HOST_RTE: Add /32 to any host routes
def _host_route(input_data: str) -> str:
    if "/" not in input_data:
        return input_data + "/32"
    else:
        return input_data


# EDIT_RTE: Used by "_add_prefix" to edit route by adding the prefix
def _edit_rte(output: List, rte_idx: int, pfx: int) -> None:
    rte = output[rte_idx].split()
    if len(rte) == 6 or len(rte) == 7 or len(rte) == 2:
        rte[1] = rte[1] + "/" + pfx
    elif len(rte) == 3 or len(rte) == 8:
        rte[2] = rte[2] + "/" + pfx
    output[rte_idx] = " ".join(rte)


# ADD_PFX: Adds prefix to subnetted routes in routing table as these show prefix on another line
def _add_prefix(output: List) -> List:
    for idx, each_rte in enumerate(output):
        if "is subnetted" in each_rte:
            # Gets the prefix and the number of routes that need it adding
            pfx = each_rte.split()[0].split("/")[1]
            num_rtes = int(each_rte.split()[-2])
            skipped = 0
            # Uses range to call the list index nof route and add prefix to it
            for x in range(1, num_rtes + 1):
                # Bypass any lines with next-hop on new line (counts number of skipped)
                if output[idx + x].split()[0][0] == "[":
                    skipped = skipped + 1
                else:
                    _edit_rte(output, idx + x, pfx)
            # If was any skipped lines, has to run again to account for skipped indexes
            if skipped != 0:
                _edit_rte(output, idx + x, pfx)
    return output


# INTEGER: Changes string to integer
def _make_int(input_data: str) -> int:
    try:
        return int(input_data)
    except:
        return input_data


# ----------------------------------------------------------------------------
# IOS/IOS-XE desired state formatting
# ----------------------------------------------------------------------------
def ios_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:

    # ----------------------------------------------------------------------------
    # SWI_RTR: Switch and router commands
    # ----------------------------------------------------------------------------


    # ----------------------------------------------------------------------------
    # SWI: Switch-only commands
    # ----------------------------------------------------------------------------

    # AUTH_MAB: show authentication sessions | count mab - {auth_mab: x}
    elif "show authentication sessions | count mab" in cmd:
        tmp_dict["auth_mab"] = _make_int(output[0].split()[-1])
    # AUTH_DOT1X: show authentication sessions | count dot1x - {auth_dot1x: x}
    elif "show authentication sessions | count dot1x" in cmd:
        tmp_dict["auth_dot1x"] = _make_int(output[0].split()[-1])

    # ----------------------------------------------------------------------------
    # RTR: Router-only commands
    # ----------------------------------------------------------------------------
    # VRF: show vrf - {vrf: [intfx, intfy]}
    elif "show vrf" in cmd:
        for each_vrf in output:
            tmp_dict[each_vrf["name"]] = each_vrf["interfaces"]
    # NUM_ROUTES: show ip route  summary | in Total - {total_subnets: x}
    elif re.match(r"show ip route .* summary \| in Total", cmd):
        if len(output) != 0:
            if cmd.split()[4] == "|":
                vrf = "global_subnets"
            else:
                vrf = cmd.split()[4] + "_subnets"
            tmp_dict[vrf] = _make_int(output[0].split()[2])
    # ROUTES: show ip  route - {route/prefix: next-hop, route/prefix: [next-hop, next-hop]}
    elif re.match("show ip  route.*", cmd):
        tmp_nh = []
        # Function to add prefix to subnetted routes
        output = _add_prefix(output)
        # Format the route table output
        for each_rte in reversed(output):
            tmp_rte = each_rte.split()
            # Removes extra route type OSPF (E2, IA) or EIGRP (EX) add to make len of lines same
            if len(tmp_rte) == 8:
                del tmp_rte[1]
            if len(tmp_rte) == 0 or tmp_rte[0] == "Routing":
                pass
            # Catches multiple next-hops or next-hop on new line adds a list which is then used if it is "via"
            elif tmp_rte[0][0] == "[":
                tmp_nh.append(tmp_rte[2].replace(",", ""))
            # Routes and next-hops on same line
            elif "via" in each_rte:
                if len(tmp_nh) == 0:
                    tmp_dict[tmp_rte[1]] = tmp_rte[4].replace(",", "")
                else:
                    tmp_nh.append(tmp_rte[4].replace(",", ""))
                    tmp_dict[tmp_rte[1]] = tmp_nh
                    tmp_nh = []
            # Routes on own line with next hops on separate line (NH caught with "[")
            elif len(tmp_rte) == 2 or len(tmp_rte) == 3:
                # In case only 1 next-hop make it a string
                if len(tmp_nh) == 1:
                    tmp_nh = tmp_nh[0]
                tmp_dict[tmp_rte[1]] = tmp_nh
                tmp_nh = []
            elif "directly" in each_rte:
                tmp_dict[tmp_rte[1]] = tmp_rte[5]

    # OSPF_INTF: show ip ospf interface brief - {intf: {area: x, cost: y, state: z}}
    elif "show ip ospf interface brief" in cmd:
        for each_intf in output:
            tmp_dict[each_intf["interface"]]["area"] = _make_int(each_intf["area"])
            tmp_dict[each_intf["interface"]]["state"] = each_intf["state"]
            tmp_dict[each_intf["interface"]]["cost"] = _make_int(each_intf["cost"])
    # OSPF_NBR: show ip ospf neighbor - {nbr_ip: {state: x}}
    elif "show ip ospf neighbor" in cmd:
        for each_nhbr in output:
            tmp_dict[each_nhbr["neighbor_id"]] = {
                "state": _remove_char(each_nhbr["state"], "/")
            }
    # OSPF_LSDB: show ip ospf database database-summary | in Total - {total_lsa: x }
    elif "show ip ospf database database-summary | in Total" in cmd:
        if len(output) != None:
            tmp_dict["total_lsa"] = _make_int(output[0].split()[1])
    # EIGRP_INTF: show ip eigrp interfaces - {intf: [x, y]}
    elif "show ip eigrp interfaces" in cmd:
        tmp_dict = defaultdict(list)
        if len(output) >= 4:
            for each_nbr in output[3:]:
                tmp_dict["intf"].append(each_nbr.split()[0])
    # EIGRP_NBR: show ip eigrp neighbors - {nbrs: [x, y]}
    elif "show ip eigrp neighbors" in cmd:
        tmp_dict = defaultdict(list)
        for each_nbr in output:
            if len(each_nbr) != 0:
                tmp_dict["nbrs"].append(each_nbr["address"])
    # BGP_PEER: show bgp all summary - {peer: {asn:x, rcv_pfx:x}}
    elif "show bgp all summary" in cmd:
        for each_line in output:
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", each_line):
                bgp_peer = each_line.split()
                tmp_dict[bgp_peer[0]]["asn"] = _make_int(bgp_peer[2])
                tmp_dict[bgp_peer[0]]["rcv_pfx"] = _make_int(bgp_peer[-1])
    # NVE_INTF: show nve vni - {l3vni: {bdi: x, vrf: z, state: UP}}
    elif "show nve vni" in cmd:
        for each_vni in output[1:]:
            if len(each_vni) != 0:
                tmp_vni = each_vni.split()
                tmp_dict[_make_int(tmp_vni[1])]["bdi"] = _make_int(tmp_vni[5])
                tmp_dict[_make_int(tmp_vni[1])]["vrf"] = tmp_vni[7]
                tmp_dict[_make_int(tmp_vni[1])]["state"] = tmp_vni[3]
    # NVE_PEERS: show nve peers - {ls_vni: {peer: ip, state: Up}}
    elif "show nve peers" in cmd:
        for each_vni in output[1:]:
            if len(each_vni) != 0:
                tmp_vni = each_vni.split()
                tmp_dict[_make_int(tmp_vni[1])]["peer"] = tmp_vni[3]
                tmp_dict[_make_int(tmp_vni[1])]["state"] = tmp_vni[6]
    # VPN: show crypto session brief - {vpn_peer: {intf: x, status: UA}}
    elif "show crypto session brief" in cmd:
        for each_vpn in output[4:]:
            if len(each_vpn) != 0:
                tmp_vpn = each_vpn.split()
                tmp_dict[tmp_vpn[0]]["intf"] = tmp_vpn[1]
                tmp_dict[tmp_vpn[0]]["status"] = tmp_vpn[-1]

    actual_state[cmd] = dict(tmp_dict)
    return actual_state




    actual_state[cmd] = dict(tmp_dict)
    return actual_state
