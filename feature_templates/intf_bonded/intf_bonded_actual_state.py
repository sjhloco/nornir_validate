from typing import Dict, List
import re
from collections import defaultdict

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


def _fix_nxos(main_dict: Dict[str, Dict], parent_dict: str, child_dict: str) -> List:
    """
    Fixes issues due to NXOS JSON making dict rather than list if only 1 item. If the child_dict is a dictionary,
    convert it to a list. Feed in cmd specific TABLE_xx and ROW_xx keywords

    :param main_dict: The dictionary that contains the parent dictionary
    :param parent_dict: The parent dictionary key
    :param child_dict: The key of the dictionary that you want to fix

    """
    if isinstance(main_dict[parent_dict][child_dict], dict):
        main_dict[parent_dict][child_dict] = [main_dict[parent_dict][child_dict]]
    return main_dict[parent_dict][child_dict]


def _format_status(status: str) -> str:
    """
    It takes the status and for nxos removes additional letters and brackets and returns a string

    :param status: The status of the student
    :type status: str
    :return: A list of tuples.
    """
    if re.match(f".*U", status):
        status = "U"
    return status.replace("(", "").replace(")", "")


# ----------------------------------------------------------------------------
# Engine that runs the actual state sub-feature formatting for all os types
# ----------------------------------------------------------------------------
def format_output(
    os_type: str, sub_feature: str, output: List, tmp_dict: Dict[str, None]
) -> Dict[str, Dict]:
    """
    > The function takes the command output and formats it into a dictionary that can be used
    to compare against the desired state

    :param os_type: The OS type of the device
    :type os_type: str
    :param sub_feature: This is the sub-feature of the feature you're working with. For example, if
    you're working with the feature "port_channel", the sub-feature would be "port_channel"
    :type sub_feature: str
    :param output: List of lists of the output from the show command
    :type output: List
    :param tmp_dict: This is the dictionary that will be returned
    :type tmp_dict: Dict[str, None]
    :return: A dictionary of dictionaries.
    """

    ### KEY: Set the dictionary keys to use on a per-OS basis
    if bool(re.search("ios", os_type)) or bool(re.search("asa", os_type)):
        po_name = "po_name"
        po_status = "po_status"
        po_protocol = "protocol"
        po_intf = "interfaces"
    elif bool(re.search("nxos", os_type)):
        po_name = "bundle_iface"
        po_status = "bundle_status"
        po_protocol = "bundle_proto"
        po_intf = "phys_iface"

    # ----------------------------------------------------------------------------
    # PORT_CHANNEL: {po_name: {protocol: type, status: code, members: {intf_name: {mbr_status: code}}}}
    # ----------------------------------------------------------------------------
    if sub_feature == "port_channel":
        for each_po in output:
            tmp_dict[each_po[po_name]]["status"] = _format_status(each_po[po_status])
            if each_po[po_protocol] == "-":
                each_po[po_protocol] = "NONE"
            tmp_dict[each_po[po_name]]["protocol"] = each_po[po_protocol].upper()
            po_mbrs = {}
            for mbr_intf, mbr_status in zip(
                each_po[po_intf], each_po[f"{po_intf}_status"]
            ):
                # For routers as use bndl rather than P
                if mbr_status == "bndl":
                    mbr_status = "P"
                # Creates dict of members to add to as value in the PO dictionary
                po_mbrs[mbr_intf] = {"mbr_status": _format_status(mbr_status)}
            tmp_dict[each_po[po_name]]["members"] = po_mbrs

    # ----------------------------------------------------------------------------
    # VPC: {role: x, peer-status: peer-ok, keepalive-status: peer-alive, vlan-consistency: consistent, peer-consistency: SUCCESS, type2-consistency: SUCCESS,
    #       peer-link-port-state": 1, peer-link-vlans": x,y,z, PoX: {vpc-id: x, port-state: 1, consistency-status: SUCCESS, vlans: x,y,z}
    # ----------------------------------------------------------------------------
    elif sub_feature == "vpc":
        tmp_dict["role"] = output["vpc-role"]
        tmp_dict["peer_status"] = output["vpc-peer-status"]
        tmp_dict["keepalive_status"] = output["vpc-peer-keepalive-status"]
        tmp_dict["vlan_consistency"] = output["vpc-per-vlan-peer-consistency"]
        tmp_dict["peer_consistency"] = output["vpc-peer-consistency-status"]
        tmp_dict["type2_consistency"] = output["vpc-type-2-consistency-status"]
        _fix_nxos(output, "TABLE_peerlink", "ROW_peerlink")
        peer_link = output["TABLE_peerlink"]["ROW_peerlink"]
        tmp_dict["peerlink_port_state"] = _make_int(
            peer_link[0]["peer-link-port-state"]
        )
        tmp_dict["peerlink_vlans"] = _make_int(peer_link[0]["peer-up-vlan-bitset"])
        # TABLE_vpc is only present if are vPCs configured
        if output.get("TABLE_vpc") != None:
            output = _fix_nxos(output, "TABLE_vpc", "ROW_vpc")
            tmp_vpc = defaultdict(dict)
            for vpc in output:
                vpc_id = _make_int(vpc["vpc-id"])
                tmp_vpc[vpc_id]["po"] = vpc["vpc-ifindex"]
                tmp_vpc[vpc_id]["port_state"] = _make_int(vpc["vpc-port-state"])
                tmp_vpc[vpc_id]["consistency_status"] = vpc["vpc-consistency-status"]
                tmp_vpc[vpc_id]["vlans"] = _make_int(vpc["up-vlan-bitset"])
            tmp_dict["vpcs"] = dict(tmp_vpc)

    return dict(tmp_dict)
