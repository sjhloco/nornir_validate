from typing import Dict, List

from collections import defaultdict
import re
import json
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
        "show ip ospf database database-summary vrf all | in Total|VRF",
        "show conn count",
        "show  route summary | in Total",
        "show ospf database database-summary | in Process|Total",
    ]
    non_ntc_tmpl_regex_cmds = r"(show ip route .* summary \| in Total)|(show ip  route.*)|(show mac address-table .*)|(show client .*)"
    if isinstance(output, str):
        if cmd in non_ntc_tmpl_cmds:
            output = output.lstrip().rstrip().splitlines()
        elif re.match(non_ntc_tmpl_regex_cmds, cmd):
            output = output.lstrip().rstrip().splitlines()
        # Converts NXOS "| json" cmds from string to JSON
        elif "json" in cmd:
            output = json.loads(output)
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
    elif bool(re.search("wlc", str(os_type))):
        wlc_format(cmd, output, tmp_dict, actual_state)
    return actual_state


# ----------------------------------------------------------------------------
# Mini-functions used by all OS types to keep DRY
# ----------------------------------------------------------------------------









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


    # AUTH_MAB: show authentication sessions | count mab - {auth_mab: x}
    elif "show authentication sessions | count mab" in cmd:
        tmp_dict["auth_mab"] = _make_int(output[0].split()[-1])
    # AUTH_DOT1X: show authentication sessions | count dot1x - {auth_dot1x: x}
    elif "show authentication sessions | count dot1x" in cmd:
        tmp_dict["auth_dot1x"] = _make_int(output[0].split()[-1])






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


# ----------------------------------------------------------------------------
# NXOS desired state formatting
# ----------------------------------------------------------------------------
def nxos_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:

   

   



    # NVE_INTF: {vni: {vl_vrf: vlan_or_vrf, state: UP}}
    elif "show nve vni | json" in cmd:
        shit_nxos(output, "TABLE_nve_vni", "ROW_nve_vni")
        for each_vni in output["TABLE_nve_vni"]["ROW_nve_vni"]:
            vni = _make_int(each_vni["vni"])
            tmp_dict[vni]["vl_vrf"] = each_vni["type"].split("[")[-1].replace("]", "")
            tmp_dict[vni]["state"] = each_vni["vni-state"]
    # NVE_PEERS: {peer_ip: Up}
    elif "show nve peers | json" in cmd:
        shit_nxos(output, "TABLE_nve_peers", "ROW_nve_peers")
        for each_peer in output["TABLE_nve_peers"]["ROW_nve_peers"]:
            tmp_dict[each_peer["peer-ip"]] = each_peer["peer-state"]
    # EVPN_MAC_IP: {host-ip: {mac: x, type: y, next-hop: z}}
    elif "show l2route mac-ip all | json" in cmd:
        shit_nxos(output, "TABLE_l2route_mac_ip", "ROW_l2route_mac_ip")
        for each_obj in output["TABLE_l2route_mac_ip"]["ROW_l2route_mac_ip"]:
            tmp_dict[each_obj["host-ip"]]["mac"] = each_obj["mac-addr"]
            tmp_dict[each_obj["host-ip"]]["type"] = each_obj["prod-type"]
            tmp_dict[each_obj["host-ip"]]["next-hop"] = each_obj["next-hop1"].split()[0]

    actual_state[cmd] = dict(tmp_dict)
    return actual_state


# ----------------------------------------------------------------------------
# ASA desired state formatting
# ----------------------------------------------------------------------------
def asa_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:

  
    # NUM_CONN: {total_conn: x}
    elif "show conn count" in cmd:
        tmp_dict["total_conn"] = _make_int(output[0].split()[0])
    # NUM_ROUTES: {global_subnets: x}

 
 
    # STS_VPN: show crypto session brief - {vpn_peer: {bytes_tx: x, bytes_rx: x}}
    elif "show vpn-sessiondb detail l2l" in cmd:
        for each_vpn in output:
            if len(each_vpn["encapsulation"]) == 0:
                peer = each_vpn["connection"]
                tmp_dict[peer]["bytes_rx"] = _make_int(each_vpn["total_bytes_received"])
                tmp_dict[peer]["bytes_tx"] = _make_int(
                    each_vpn["total_bytes_transmitted"]
                )
    # AC_VPN: show crypto session brief - {user: {group_policy: x, tunnel_group: x, bytes_tx: x, bytes_rx: x}}
    elif "show vpn-session anyconnect" in cmd:
        for each_vpn in output:
            user = each_vpn["username"]
            tmp_dict[user]["group_policy"] = _make_int(each_vpn["group_policy"])
            tmp_dict[user]["tunnel_group"] = _make_int(each_vpn["tunnel_group"])
            tmp_dict[user]["bytes_rx"] = _make_int(each_vpn["bytes_rx"])
            tmp_dict[user]["bytes_tx"] = _make_int(each_vpn["bytes_tx"])
    # NUM_VPN: {ac: xx, sts: xx}
    elif "show vpn-session" in cmd:
        for each_vpn, active_sess in zip(
            output[0]["vpn_session_name"], output[0]["vpn_session_active"]
        ):
            if each_vpn == "Site-to-Site VPN":
                tmp_dict["sts"] = _make_int(active_sess)
            if each_vpn == "AnyConnect Client":
                tmp_dict["ac"] = _make_int(active_sess)

    actual_state[cmd] = dict(tmp_dict)
    return actual_state


# ----------------------------------------------------------------------------
# WLC desired state formatting
# ----------------------------------------------------------------------------
def wlc_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:






    # NUM_CLIENTS: {total: x, wlan: x}
    elif "show client" in cmd:
        if len(output) != 0:
            if cmd.split()[2] == "summary":
                wlan = "total"
            elif cmd.split()[2] == "wlan":
                wlan = "wlan_" + cmd.split()[3]
            for each_line in output:
                if "Number of Clients" in each_line:
                    tmp_dict[wlan] = _make_int(each_line.split()[-1])
        else:
            tmp_dict["total"]


    actual_state[cmd] = dict(tmp_dict)
    return actual_state
