from typing import Dict, List
import ipaddress
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


def _get_pfxlen(network: str, mask: str) -> str:
    ip_mask = network + "/" + mask
    ip_pfxlen = ipaddress.IPv4Interface(ip_mask).with_prefixlen
    return ip_pfxlen


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


# Fixes issues due to shit NXOS JSON making dict rather than list if only item. Feed in cmd specific TABLE_xx and ROW_xx keywords
def shit_nxos(main_dict, parent_dict, child_dict):
    # breakpoint()
    if isinstance(main_dict[parent_dict][child_dict], dict):
        main_dict[parent_dict][child_dict] = [main_dict[parent_dict][child_dict]]


# CISCO_CDP_LLDP: To format Cisco CDP or LLDP neighbor output
def cisco_cdp_lldp_nhbr(tmp_dict: Dict[str, List], output: List) -> None:
    for each_nbr in output:
        tmp_dict[each_nbr["local_interface"]] = {
            each_nbr["neighbor"]: each_nbr["neighbor_interface"]
        }


# CISCO_INTF_STUS: To format Cisco show interface status output
def cisco_intf_stus(tmp_dict: Dict[str, List], output: List) -> None:
    for each_intf in output:
        tmp_dict[each_intf["port"]]["duplex"] = each_intf["duplex"]
        tmp_dict[each_intf["port"]]["speed"] = _make_int(each_intf["speed"])
        tmp_dict[each_intf["port"]]["status"] = each_intf["status"]
        tmp_dict[each_intf["port"]]["vlan"] = _make_int(each_intf["vlan"])


# CISCO_INTF_SWPRT: To format Cisco show interface switchport output
def cisco_intf_swprt(tmp_dict: Dict[str, List], output: List) -> None:
    for each_intf in output:
        mode = each_intf["mode"].replace("static ", "")
        tmp_dict[each_intf["interface"]]["mode"] = mode
        if each_intf["mode"] == "static access" or each_intf["mode"] == "access":
            tmp_dict[each_intf["interface"]]["vlan"] = _make_int(
                each_intf["access_vlan"]
            )
        elif each_intf["mode"] == "trunk":
            tmp_dict[each_intf["interface"]]["vlan"] = each_intf["trunking_vlans"]
        else:
            tmp_dict[each_intf["interface"]]["vlan"] = None


# CISCO_VL_BRF: To format Cisco show vlan brief output
def cisco_vl_brf(tmp_dict: Dict[str, List], output: List) -> None:
    for each_vl in output:
        vl_id = _make_int(each_vl["vlan_id"])
        tmp_dict[vl_id]["name"] = each_vl["name"]
        tmp_dict[vl_id]["intf"] = each_vl["interfaces"]
    for each_vl in [1, 1002, 1003, 1004, 1005]:
        if tmp_dict.get(each_vl) != None:
            del tmp_dict[each_vl]


# CISCO_PO: To format Cisco show etherchannel/port-channel summary (not NXOS)
def cisco_po(tmp_dict: Dict[str, List], output: List) -> None:
    for each_po in output:
        tmp_dict[each_po["po_name"]]["status"] = each_po["po_status"]
        if each_po["protocol"] == "-":
            each_po["protocol"] = "NONE"
        tmp_dict[each_po["po_name"]]["protocol"] = each_po["protocol"]
        po_mbrs = {}
        for mbr_intf, mbr_status in zip(
            each_po["interfaces"], each_po["interfaces_status"]
        ):
            # For routers as use bndl rather than P
            if mbr_status == "bndl":
                mbr_status = "P"
            # Creates dict of members to add to as value in the PO dictionary
            po_mbrs[mbr_intf] = {"mbr_status": mbr_status}
        tmp_dict[each_po["po_name"]]["members"] = po_mbrs


# CISCO_OSPF_INTF_BR: To format Cisco show ip ospf interface brief/show ospf interface brief (not NXOS)
def cisco_ospf_intf_br(tmp_dict: Dict[str, List], output: List) -> None:
    for each_intf in output:
        tmp_dict[each_intf["interface"]]["area"] = _make_int(each_intf["area"])
        tmp_dict[each_intf["interface"]]["state"] = each_intf["state"]
        tmp_dict[each_intf["interface"]]["cost"] = _make_int(each_intf["cost"])
        tmp_dict[each_intf["interface"]]["nbr_count"] = each_intf["neighbors_fc"]


# CISCO_OSPF_NBR: To format Cisco show ip ospf neighbor/show ospf neighbor (not NXOS)
def cisco_ospf_nbr(tmp_dict: Dict[str, List], output: List) -> None:
    for each_nhbr in output:
        tmp_dict[each_nhbr["neighbor_id"]] = {
            "state": _remove_char(each_nhbr["state"], "/ ")
        }


# ----------------------------------------------------------------------------
# IOS/IOS-XE desired state formatting
# ----------------------------------------------------------------------------
def ios_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:

    # ----------------------------------------------------------------------------
    # SWI_RTR: Switch and router commands
    # ----------------------------------------------------------------------------
    # IMAGE: show version - {image: code_number}
    if "show version" in cmd:
        if len(output[0]["version"]) == 0:
            tmp_dict["image"] = output[0]["running_image"]
        else:
            tmp_dict["image"] = output[0]["version"]
    # MGMT ACL: show ip access-lists <name> - [{acl_name: {name: seq_num: {protocol: ip/tcp/udp, src: src_ip, dst: dst_ip, dst_port: port}]
    if "show ip access-lists" in cmd:
        acl = _acl_format(output)
        tmp_dict1 = defaultdict(dict)
        for each_ace in acl:
            # Creates dict for each ACE entry
            if each_ace.get("line_num") != None:
                tmp_dict1[each_ace["line_num"]]["action"] = each_ace["action"]
                tmp_dict1[each_ace["line_num"]]["protocol"] = each_ace["protocol"]
                tmp_dict1[each_ace["line_num"]]["src"] = _acl_scr_dst(each_ace, "src")
                tmp_dict1[each_ace["line_num"]]["dst"] = _acl_scr_dst(each_ace, "dst")
                if each_ace.get("dst_port") != None:
                    tmp_dict1[each_ace["line_num"]]["dst_port"] = each_ace["dst_port"]
                elif each_ace.get("icmp_type") != None:
                    tmp_dict1[each_ace["line_num"]]["icmp_type"] = each_ace["icmp_type"]
                tmp_dict[each_ace["acl_name"]] = dict(tmp_dict1)
    # PO: show etherchannel summary - {po_name: {protocol: type, status: code, members: {intf_name: {mbr_status: code}}}}
    elif "show etherchannel summary" in cmd:
        cisco_po(tmp_dict, output)
    # INTF_L3: show ip interface brief -  {intf: {ip:x, status: x}}
    elif "show ip interface brief" in cmd:
        for each_intf in output:
            tmp_dict[each_intf["intf"]]["ip"] = each_intf["ipaddr"]
            tmp_dict[each_intf["intf"]]["status"] = each_intf["status"]
    # CDP/LLDP: show cdp/lldp neighbors - {intf: {neighbor: neighbor_interface}}
    elif "show cdp neighbors" in cmd or "show lldp neighbors" in cmd:
        cisco_cdp_lldp_nhbr(tmp_dict, output)
    # HSRP: show standby brief - {group: {state:x, priority: x}}
    elif "show standby brief" in cmd:
        for each_nbr in output:
            grp = _make_int(each_nbr["group"])
            tmp_dict[grp]["state"] = each_nbr["state"]
            tmp_dict[grp]["priority"] = _make_int(each_nbr["priority"])

    # ----------------------------------------------------------------------------
    # SWI: Switch-only commands
    # ----------------------------------------------------------------------------
    # SWI_STACK: show switch - {sw_num: {priority: x, role: x, state: x}}
    elif "show switch" in cmd:
        if len(output) >= 6:
            for each_swi in output[5:]:
                if len(each_swi) != 0:
                    tmp_swi = each_swi.split()
                    swi = _make_int(tmp_swi[0].replace("*", ""))

                    tmp_dict[swi]["role"] = tmp_swi[1]
                    tmp_dict[swi]["priority"] = _make_int(tmp_swi[3])
                    tmp_dict[swi]["state"] = tmp_swi[5]
    # VSS_HA: show  redundancy state | in state - {my_state: ACTIVE, peer_state: STANDBY HOT}
    elif "show  redundancy state | in state" in cmd:
        for each_swi in output:
            if len(each_swi) != 0:
                tmp_swi = each_swi.split()
                tmp_dict[tmp_swi[0] + "_" + tmp_swi[1]] = each_swi.split("-")[
                    1
                ].rstrip()
    # INTF_L2: show interfaces status - {intf: {duplex: x, speed: x, status: x, vlan:x }}
    elif "show interfaces status" in cmd:
        cisco_intf_stus(tmp_dict, output)
    # SWITCHPORT: show interfaces switchport - {intf: {mode: access or trunk, vlan: x or [x,y]}}
    elif "show interfaces switchport" in cmd:
        cisco_intf_swprt(tmp_dict, output)
    # VLAN: show vlan brief - {vlan: {name: x, intf:[x,y]}}
    elif "show vlan brief" in cmd:
        cisco_vl_brf(tmp_dict, output)
    # STP_VL: show spanning-tree - {vlan: intf:[x,y]}
    elif "show spanning-tree" in cmd:
        tmp_dict = defaultdict(list)
        for each_intf in output:
            if each_intf["status"] == "FWD":
                tmp_dict[_make_int(each_intf["vlan_id"])].append(each_intf["interface"])
    # ALL_MAC: show mac address-table count | in Dynamic - {total_mac: x}
    elif "show mac address-table | count dynamic|DYNAMIC" in cmd:
        tmp_dict["total_mac"] = _make_int(output[0].split()[-1])
    # VLAN_MAC: show mac address-table vlan x | count dynamic|DYNAMIC - {vlxxx_mac: x}
    elif "show mac address-table vlan" in cmd:
        vl = cmd.split()[4] + "_total_mac"
        tmp_dict[vl] = _make_int(output[0].split()[-1])
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
    # NUM_ROUTES: show ip route  summary | in Total - {vrf_subnets: x}
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
        cisco_ospf_intf_br(tmp_dict, output)
    # OSPF_NBR: show ip ospf neighbor - {nbr_ip: {state: x}}
    elif "show ip ospf neighbor" in cmd:
        cisco_ospf_nbr(tmp_dict, output)
    # OSPF_LSDB: show ip ospf database database-summary | in Total - {process: total_lsa:, process: total_lsa:}
    elif "show ip ospf database database-summary | in Total" in cmd:
        if len(output) != 0:
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


# ----------------------------------------------------------------------------
# NXOS desired state formatting
# ----------------------------------------------------------------------------
def nxos_format(
    cmd: str, output: List, tmp_dict: Dict[str, None], actual_state: Dict[str, None]
) -> Dict[str, Dict]:

    # IMAGE: {image: code_number}
    if "show version" in cmd:
        tmp_dict["image"] = output[0]["os"]
    # MGMT ACL: [{acl_name: {name: seq_num: {protocol: ip/tcp/udp, src: src_ip, dst: dst_ip, dst_port: port}]
    elif "show access-lists" in cmd:
        acl = _acl_format(output)
        tmp_dict1 = defaultdict(dict)
        for each_ace in acl:
            # Creates dict for each ACE entry
            if each_ace.get("action") != "remark":
                tmp_dict1[each_ace["sn"]]["action"] = each_ace["action"]
                tmp_dict1[each_ace["sn"]]["protocol"] = each_ace["protocol"]
                tmp_dict1[each_ace["sn"]]["src"] = each_ace["source"]
                tmp_dict1[each_ace["sn"]]["dst"] = each_ace["destination"]
                if each_ace["protocol"] == "icmp" and each_ace.get("modifier") != None:
                    tmp_dict1[each_ace["sn"]]["icmp_type"] = each_ace["modifier"]
                elif each_ace.get("modifier") != None:
                    tmp_dict1[each_ace["sn"]]["dst_port"] = each_ace["modifier"]
                tmp_dict[each_ace["name"]] = dict(tmp_dict1)
    # PO: {po_name: {protocol: type, status: code, members: {intf_name: {mbr_status: code}}}}
    elif "show port-channel summary" in cmd:
        for each_po in output:
            tmp_dict[each_po["bundle_iface"]]["status"] = (
                each_po["bundle_status"].replace("(", "").replace(")", "")
            )
            tmp_dict[each_po["bundle_iface"]]["protocol"] = each_po["bundle_proto"]
            po_mbrs = {}
            for mbr_intf, mbr_status in zip(
                each_po["phys_iface"], each_po["phys_iface_status"]
            ):
                # Creates dict of members to add to as value in the PO dictionary
                po_mbrs[mbr_intf] = {
                    "mbr_status": mbr_status.replace("(", "").replace(")", "")
                }
            tmp_dict[each_po["bundle_iface"]]["members"] = po_mbrs
    # L3_INTF: {intf: {ip:x, status: x}}
    elif "show ip interface brief vrf all | json" in cmd:
        shit_nxos(output, "TABLE_intf", "ROW_intf")
        for intf in output["TABLE_intf"]["ROW_intf"]:
            tmp_dict[intf["intf-name"]]["status"] = intf["link-state"]
            intf.setdefault("prefix", None)
            tmp_dict[intf["intf-name"]]["prefix"] = intf["prefix"]
    # CDP/LLDP: {intf: {neighbor: neighbor_interface}}
    elif "show cdp neighbors" in cmd or "show lldp neighbors" in cmd:
        cisco_cdp_lldp_nhbr(tmp_dict, output)
    # HSRP: {intf: {state:x, priority: x}}
    elif "show hsrp brief | json" in cmd:
        shit_nxos(output, "TABLE_grp_detail", "ROW_grp_detail")
        for each_hsrp in output["TABLE_grp_detail"]["ROW_grp_detail"]:
            tmp_dict[each_hsrp["sh_if_index"]]["state"] = each_hsrp["sh_group_state"]
            tmp_dict[each_hsrp["sh_if_index"]]["priority"] = _make_int(
                each_hsrp["sh_prio"]
            )
    # MODULE: {module_num: {model:x, status: x}}
    elif "show module" in cmd:
        for each_mod in output:
            tmp_dict[_make_int(each_mod["module"])]["model"] = each_mod["model"]
            tmp_dict[_make_int(each_mod["module"])]["status"] = each_mod["status"]
    # VPC: {role: x, peer-status: peer-ok, keepalive-status: peer-alive, vlan-consistency: consistent, peer-consistency: SUCCESS, type2-consistency: SUCCESS,
    #       peer-link-port-state": 1, peer-link-vlans": x,y,z, PoX: {vpc-id: x, port-state: 1, consistency-status: SUCCESS, vlans: x,y,z}
    elif "show vpc | json" in cmd:
        tmp_dict["role"] = output["vpc-role"]
        tmp_dict["peer-status"] = output["vpc-peer-status"]
        tmp_dict["keepalive-status"] = output["vpc-peer-keepalive-status"]
        tmp_dict["vlan-consistency"] = output["vpc-per-vlan-peer-consistency"]
        tmp_dict["peer-consistency"] = output["vpc-peer-consistency-status"]
        tmp_dict["type2-consistency"] = output["vpc-type-2-consistency-status"]
        peer_link = output["TABLE_peerlink"]["ROW_peerlink"]
        tmp_dict["peer-link-port-state"] = _make_int(peer_link["peer-link-port-state"])
        tmp_dict["peer-link_vlans"] = peer_link["peer-up-vlan-bitset"]
        # TABLE_vpc is only present if are vPCs configured
        if output.get("TABLE_vpc") != None:
            shit_nxos(output, "TABLE_vpc", "ROW_vpc")
            for vpc in output["TABLE_vpc"]["ROW_vpc"]:
                tmp_dict[vpc["vpc-ifindex"]]["vpc_id"] = _make_int(vpc["vpc-id"])
                tmp_dict[vpc["vpc-ifindex"]]["port_status"] = _make_int(
                    vpc["vpc-port-state"]
                )
                tmp_dict[vpc["vpc-ifindex"]]["consistency_status"] = vpc[
                    "vpc-consistency-status"
                ]
                tmp_dict[vpc["vpc-ifindex"]]["vlans"] = vpc["up-vlan-bitset"]

    # INTF: {intf: {duplex: x, speed: x, status: x, vlan:x }}
    elif "show interface status" in cmd:
        cisco_intf_stus(tmp_dict, output)
    # SWITCHPORT: {intf: {mode: access or trunk, vlan: x or [x,y]}}
    elif "show interface switchport" in cmd:
        cisco_intf_swprt(tmp_dict, output)
    # VLAN: {vlan: {name: x, intf:[x,y]}}
    elif "show vlan brief" in cmd:
        cisco_vl_brf(tmp_dict, output)
    # ALL_MAC: {total_mac: x}
    elif "show mac address-table count dynamic | in Total" in cmd:
        tmp_dict["total_mac"] = _make_int(output[0].split()[-1])
    # VLAN_MAC: {vlxxx_total_mac: x}
    elif "show mac address-table count dynamic vlan " in cmd:
        vl = cmd.split()[-4] + "_total_mac"
        tmp_dict[vl] = _make_int(output[0].split()[-1])
    # VRF: {vrf: [intfx, intfy]}
    elif "show vrf interface" in cmd:
        for each_vrf in output:
            if tmp_dict.get(each_vrf["name"]) == None:
                tmp_dict[each_vrf["name"]] = [each_vrf["interface"]]
            else:
                tmp_dict[each_vrf["name"]].append(each_vrf["interface"])
    # NUM_ROUTES: {global_subnets: x, vrfX_subnets: x}
    elif re.match(r"show ip route .* summary \| in Total", cmd):
        if len(output) != 0:
            if cmd.split()[4] == "|":
                vrf = "global_subnets"
            else:
                vrf = cmd.split()[4] + "_subnets"
            tmp_dict[vrf] = _make_int(output[0].split()[2])
    # ROUTES: {vrf: {route/prefix: {type: x, nexthop: next-hop}, route/prefix: {type: x, nexthop: [next-hop, next-hop]}}}
    elif re.match("show ip route vrf all", cmd):
        for each_rte in output:
            # Creates varaibles used to create data model
            vrf = each_rte["vrf"]
            rte = each_rte["network"] + "/" + each_rte["mask"]
            if each_rte["network"] == each_rte["nexthop_ip"]:
                nh = each_rte["nexthop_if"]
            else:
                nh = each_rte["nexthop_ip"]
            # If VRF doenst exist add VRF and route
            if tmp_dict.get(vrf) == None:
                tmp_dict[vrf] = {rte: {"nexthop": nh}}
            # If route doesnt exist add it, if already exists add additonal non-duplicate next-hops
            else:
                if tmp_dict[vrf].get(rte) == None:
                    tmp_dict[vrf].update({rte: {"nexthop": nh}})
                elif not isinstance(tmp_dict[vrf][rte]["nexthop"], list):
                    if tmp_dict[vrf][rte]["nexthop"] != nh:
                        tmp_dict[vrf][rte]["nexthop"] = [tmp_dict[vrf][rte]["nexthop"]]
                        tmp_dict[vrf][rte]["nexthop"].append(nh)
                else:
                    tmp_dict[vrf][rte]["nexthop"].append(nh)
            # Add route type, joins route type if is a routing protocol
            if len(each_rte["type"]) == 0:
                tmp_dict[vrf][rte]["type"] = each_rte["protocol"]
            else:
                tmp_dict[vrf][rte]["type"] = (
                    each_rte["protocol"] + " " + each_rte["type"]
                )

    # OSPF_INTF: {intf: {vrf: v, area: w, cost: x, state: y, nbr_count: z}}
    elif "show ip ospf interface brief vrf all | json" in cmd:
        shit_nxos(output, "TABLE_ctx", "ROW_ctx")
        for each_proc in output["TABLE_ctx"]["ROW_ctx"]:
            shit_nxos(each_proc, "TABLE_intf", "ROW_intf")
            # Loops through interfaces in OSPF process and creates temp dict of each interface in format {intf_name: {attribute: value}}
            for each_intf in each_proc["TABLE_intf"]["ROW_intf"]:
                tmp_dict[each_intf["ifname"]]["vrf"] = each_proc["cname"]
                tmp_dict[each_intf["ifname"]]["area"] = each_intf["area"]
                tmp_dict[each_intf["ifname"]]["cost"] = each_intf["cost"]
                tmp_dict[each_intf["ifname"]]["status"] = each_intf["admin_status"]
                tmp_dict[each_intf["ifname"]]["nbr_count"] = each_intf["nbr_total"]
    # OSPF_NBR: {nbr_ip: {state: x}}
    elif "show ip ospf neighbor vrf all" in cmd:
        for each_nhbr in output:
            tmp_dict[each_nhbr["neighbor_ipaddr"]] = {
                "state": _remove_char(each_nhbr["state"], "/ ")
            }
    # OSPF_LSDB:{process: total_lsa:, process: total_lsa:}
    elif "show ip ospf database database-summary vrf all | in Total|VRF" in cmd:
        if len(output) != 0:
            for idx, each_line in enumerate(output):
                if len(each_line.split()) > 2:
                    proc = each_line.split()[-3]
                    if tmp_dict.get(each_line.split()[-3]) == None:
                        tmp_dict[proc] = _make_int(output[idx + 1].split()[-1])
                    else:
                        tmp_dict[proc] = tmp_dict[proc] + _make_int(
                            output[idx + 1].split()[-1]
                        )
    # BGP_PEER: {peer: {asn:x, rcv_pfx:x}}
    elif "show bgp all summary | json" in cmd:
        shit_nxos(output, "TABLE_vrf", "ROW_vrf")
        for each_vrf in output["TABLE_vrf"]["ROW_vrf"]:
            shit_nxos(each_vrf, "TABLE_af", "ROW_af")
            for each_af in each_vrf["TABLE_af"]["ROW_af"]:
                shit_nxos(each_af, "TABLE_saf", "ROW_saf")
                for each_saf in each_af["TABLE_saf"]["ROW_saf"]:
                    if each_saf.get("TABLE_neighbor") != None:
                        shit_nxos(each_saf, "TABLE_neighbor", "ROW_neighbor")
                        for each_nbr in each_saf["TABLE_neighbor"]["ROW_neighbor"]:
                            tmp_dict[each_nbr["neighborid"]]["asn"] = _make_int(
                                each_nbr["neighboras"]
                            )
                            tmp_dict[each_nbr["neighborid"]]["rcv_pfx"] = _make_int(
                                each_nbr["prefixreceived"]
                            )
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

    # IMAGE: {image: code_number}
    if "show version" in cmd:
        tmp_dict["image"] = output[0]["version"]
    # MGMT ACL: [{ssh_or_http: {seq_num: {src: src_ip, intf: interface}]
    elif "show run ssh" in cmd or "show run http" in cmd:
        tmp_dict1 = defaultdict(dict)
        seq = 10
        for each_ace in output:
            try:
                ip_mask = each_ace.split()[1] + "/" + each_ace.split()[2]
                ip_pfxlen = ipaddress.IPv4Interface(ip_mask).with_prefixlen
                if ip_pfxlen == "0.0.0.0/0":
                    tmp_dict1[str(seq)]["src"] = "any"
                else:
                    tmp_dict1[str(seq)]["src"] = ip_pfxlen
                tmp_dict1[str(seq)]["intf"] = each_ace.split()[3]
                seq = seq + 10
            except:
                pass
        if len(tmp_dict1) != 0:
            tmp_dict[cmd.split()[-1].upper()] = dict(tmp_dict1)
    # HA: {local_state: Primary - Active, peer_state: Secondary - Standby Ready}
    elif "show failover" in cmd:
        tmp_dict["local_state"] = output[0]["service_state"][0]
        tmp_dict["peer_state"] = output[0]["service_state_mate"][0]
    # PO: {po_name: {protocol: type, status: code, members: {intf_name: {mbr_status: code}}}}
    elif "show port-channel summary" in cmd:
        cisco_po(tmp_dict, output)
    # INTF: {intf: {ip: x, name: xx, status, duplex: x, speed: x, status: x, vlan:x }}
    elif "show interface" in cmd:
        for each_intf in output:
            tmp_dict[each_intf["interface"]]["ip"] = each_intf["ip_address"]
            tmp_dict[each_intf["interface"]]["name"] = each_intf["interface_zone"]
            tmp_dict[each_intf["interface"]]["status"] = each_intf["link_status"]
            tmp_dict[each_intf["interface"]]["duplex"] = each_intf["duplex"]
            tmp_dict[each_intf["interface"]]["speed"] = _make_int(each_intf["speed"])
            tmp_dict[each_intf["interface"]]["vlan"] = _make_int(each_intf["vlan"])
    # NUM_CONN: {total_conn: x}
    elif "show conn count" in cmd:
        tmp_dict["total_conn"] = _make_int(output[0].split()[0])
    # NUM_ROUTES: {global_subnets: x}
    elif "show  route summary | in Total" in cmd:
        tmp_dict["global_subnets"] = _make_int(output[0].split()[2])
    # ROUTES: {route/prefix: {type: x, nexthop: next-hop}, route/prefix: {type: x, nexthop: [next-hop, next-hop]}}
    elif "show route" in cmd:
        for each_rte in output:
            # Creates varaibles used to create data model
            rte = _get_pfxlen(each_rte["network"], each_rte["mask"])
            if len(each_rte["nexthopip"]) != 0:
                nh = each_rte["nexthopip"]
            else:
                nh = each_rte["nexthopif"]
            # If route doesnt exist add it, if already exists add additonal non-duplicate next-hops
            if tmp_dict.get(rte) == None:
                tmp_dict[rte]["nexthop"] = nh
            elif not isinstance(tmp_dict[rte]["nexthop"], list):
                if tmp_dict[rte]["nexthop"] != nh:
                    tmp_dict[rte]["nexthop"] = [tmp_dict[rte]["nexthop"]]
                    tmp_dict[rte]["nexthop"].append(nh)
            else:
                tmp_dict[rte]["nexthop"].append(nh)
            # Add route type, joins route type if is a routing protocol
            if len(each_rte["type"]) == 0:
                tmp_dict[rte]["type"] = each_rte["protocol"]
            else:
                tmp_dict[rte]["type"] = each_rte["protocol"] + " " + each_rte["type"]
    # BGP_PEER: {peer: {asn:x, rcv_pfx:x}}
    elif "show bgp summary" in cmd:
        for each_peer in output:
            tmp_dict[each_peer["bgp_neigh"]]["asn"] = _make_int(each_peer["neigh_as"])
            tmp_dict[each_peer["bgp_neigh"]]["rcv_pfx"] = _make_int(
                each_peer["state_pfxrcd"]
            )
    # OSPF_INTF: {intf: {area: x, cost: y, state: z, nbr_count: z}}
    elif "show ospf interface brief" in cmd:
        cisco_ospf_intf_br(tmp_dict, output)
    # OSPF_NBR: {nbr_ip: {state: x}}
    elif "show ospf neighbor" in cmd:
        cisco_ospf_nbr(tmp_dict, output)
    # OSPF_LSDB: {process: total_lsa:, process: total_lsa:}
    elif "show ospf database database-summary | in Process|Total" in cmd:
        if len(output) != 0:
            for idx, each_line in enumerate(output):
                if re.search("^Process", each_line):
                    proc = _make_int(each_line.split()[1])
                    if tmp_dict.get(each_line.split()[1]) == None:
                        tmp_dict[proc] = _make_int(output[idx + 1].split()[1])
                    else:
                        tmp_dict[proc] = tmp_dict[proc] + _make_int(
                            output[idx + 1].split()[1]
                        )
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

    # IMAGE: {image: code_number}
    if "show sysinfo" in cmd:
        tmp_dict["image"] = output[0]["product_version"]
    # HA: {local_state: ACTIVE, peer_state: STANDBY HOT}
    elif "show redundancy summary" in cmd:
        tmp_dict["local_state"] = output[0]["local_state"]
        tmp_dict["peer_state"] = output[0]["peer_state"]
    # L3_INTF: {intf_name: {ip:x, port: x, vlan: }}
    elif "show interface summary" in cmd:
        for each_intf in output:
            tmp_dict[each_intf["name"]]["ip"] = each_intf["ip_addr"]
            tmp_dict[each_intf["name"]]["port"] = each_intf["port"]
            tmp_dict[each_intf["name"]]["vlan"] = _make_int(each_intf["vlan"])
    # INTF: {intf: {duplex: x, speed: x, status: x }}
    elif "show port summary" in cmd:
        for each_intf in output:
            port = _make_int(each_intf["port"])
            tmp_dict[port]["status"] = each_intf["link_status"]
            try:
                tmp_dict[port]["speed"] = each_intf["physical_status"].split()[0]
                tmp_dict[port]["duplex"] = each_intf["physical_status"].split()[1]
            except:
                tmp_dict[port]["speed"] = each_intf["physical_status"]
                tmp_dict[port]["duplex"] = each_intf["physical_status"]
    # CDP: {intf: {neighbor: neighbor_interface}}
    elif "show cdp neighbors detail" in cmd:
        for each_nbr in output:
            tmp_dict[each_nbr["local_port"]] = {
                each_nbr["destination_host"]: each_nbr["remote_port"]
            }
    # WLAN: {wlan: {profile: x, intf: x, ssid: x, status: Enabled}}
    elif "show wlan summary" in cmd:
        for each_wlan in output:
            wlan = _make_int(each_wlan["wlanid"])
            tmp_dict[wlan]["profile"] = each_wlan["profile"]
            tmp_dict[wlan]["intf"] = each_wlan["interface"]
            tmp_dict[wlan]["ssid"] = each_wlan["ssid"]
            tmp_dict[wlan]["status"] = each_wlan["status"]

    # AP_IMAGE: {ap: {primary_image: x, primary_image: x}}
    elif "show ap image all" in cmd:
        for each_ap in output:
            tmp_dict[each_ap["ap_name"]]["primary_image"] = each_ap["primary_image"]
            tmp_dict[each_ap["ap_name"]]["backup_image"] = each_ap["backup_image"]
    # AP_SUMMARY: {ap: {primary_image: x, primary_image: x}}
    elif "show ap summary" in cmd:
        for each_ap in output:
            tmp_dict[each_ap["ap_name"]]["ap_model"] = each_ap["ap_model"]
            tmp_dict[each_ap["ap_name"]]["ip"] = each_ap["ip"]
            tmp_dict[each_ap["ap_name"]]["clients"] = each_ap["clients"]

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
    # INTF_GRP: {grp_name: {ap_groups: x, interfaces: y, wlans: z}}
    elif "show interface group summary" in cmd:
        for each_grp in output:
            grp_name = each_grp["interface_group_name"]
            tmp_dict[grp_name]["ap_groups"] = _make_int(each_grp["total_ap_groups"])
            tmp_dict[grp_name]["interfaces"] = _make_int(each_grp["total_interfaces"])
            tmp_dict[grp_name]["ap_wlans"] = _make_int(each_grp["total_wlans"])
    # FLEX_GTP: {grp_name: ap_count}
    elif "show flexconnect group summary" in cmd:
        for each_grp in output:
            tmp_dict[each_grp["flexconnect_group_name"]] = _make_int(
                each_grp["ap_count"]
            )

    actual_state[cmd] = dict(tmp_dict)
    return actual_state
