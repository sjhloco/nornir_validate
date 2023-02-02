# These dictionaries are used by test_validations.py to test templated desired_state and formatted actual_state

# --------------------------------------------------------------------------------------
# DESIRED: The desired state after it has been templated and assigned as a host_var
# --------------------------------------------------------------------------------------
desired_state = {
    ## --------------------------------------------------------------------------------------
    ## IOS/IOS-XE: Desired State for IOS/IOS-XE os-type
    ## --------------------------------------------------------------------------------------
    "ios": {
        "show version": {"image": "16.6.2"},
        "show ip access-lists TEST_SSH_ACCESS": {
            "TEST_SSH_ACCESS": {
                "_mode": "strict",
                "10": {
                    "action": "permit",
                    "protocol": "ip",
                    "src": "10.17.10.0/24",
                    "dst": "any",
                },
                "20": {
                    "action": "permit",
                    "protocol": "ip",
                    "src": "10.10.10.10/32",
                    "dst": "any",
                },
                "30": {"action": "deny", "protocol": "ip", "src": "any", "dst": "any"},
            }
        },
        "show etherchannel summary": {
            "Po3": {
                "status": "U",
                "protocol": "LACP",
                "members": {
                    "_mode": "strict",
                    "Gi0/15": {"mbr_status": "P"},
                    "Gi0/16": {"mbr_status": "P"},
                },
            }
        },
        "show ip interface brief": {
            "GigabitEthernet1": {"ip": "10.10.20.102", "status": "up"},
            "GigabitEthernet2": {"ip": "10.20.20.102", "status": "up"},
            "GigabitEthernet3": {"ip": "10.30.20.102", "status": "up"},
        },
        "show cdp neighbors": {
            "Gi0/1": {"Switch01": "Gi0/3"},
            "Gi0/2": {"Switch02": "Gi0/3"},
        },
        "show lldp neighbors": {"Gi2": {"Router01": "Gi0/1"}},
        "show standby brief": {0: {"priority": 50, "state": "Active"}},
        "show switch": {
            1: {"priority": 15, "role": "Active", "state": "Ready"},
            2: {"priority": 14, "role": "Standby", "state": "Ready"},
            "_mode": "strict",
        },
        "show  redundancy state | in state": {
            "my_state": "ACTIVE",
            "peer_state": "STANDBY " "HOT",
        },
        "show interfaces status": {
            "Gi0/0": {
                "duplex": "a-full",
                "speed": "auto",
                "status": "connected",
                "vlan": "routed",
            },
            "Gi0/1": {
                "duplex": "a-full",
                "speed": "auto",
                "status": "suspended",
                "vlan": 20,
            },
            "Gi0/2": {
                "duplex": "a-full",
                "speed": "auto",
                "status": "connected",
                "vlan": "trunk",
            },
            "Po3": {
                "duplex": "auto",
                "speed": "auto",
                "status": "notconnect",
                "vlan": 20,
            },
        },
        "show interfaces switchport": {
            "Gi0/1": {"mode": "access", "vlan": 10},
            "Gi0/3": {"mode": "trunk", "vlan": "10,20,30"},
        },
        "show vlan brief": {
            10: {
                "intf": {"_mode": "strict", "list": ["Gi0/1", "Gi0/2"]},
                "name": "vl10",
            },
            20: {"intf": {"_mode": "strict", "list": ["Lo3"]}, "name": "vl2"},
        },
        "show spanning-tree": {
            10: {"list": ["Gi0/1", "Gi0/2"]},
            20: {"list": ["Gi0/3"]},
        },
        "show mac address-table | count dynamic|DYNAMIC": {"total_mac": 1100},
        "show mac address-table vlan 52 | count dynamic|DYNAMIC": {"52_total_mac": 21},
        "show authentication sessions | count mab": {"auth_mab": 21},
        "show authentication sessions | count dot1x": {"auth_dot1x": 22},
        "show vrf": {
            "AMB": {"_mode": "strict", "list": ["Gi0/1", "Gi0/2"]},
            "BLU": {"_mode": "strict", "list": ["Lo2"]},
            "GRY": {"_mode": "strict", "list": ["Vl20"]},
        },
        "show ip route  summary | in Total": {"global_subnets": 20},
        "show ip route vrf BLU summary | in Total": {"BLU_subnets": 113},
        "show ip  route": {
            "0.0.0.0/0": "10.30.20.1",
            "1.1.1.1/32": "Loopback1",
            "10.30.20.0/24": "GigabitEthernet1",
            "10.30.20.102/32": "GigabitEthernet1",
            "192.168.25.42/32": {"list": ["192.168.14.10", "192.168.14.2"]},
            "21.1.1.1/32": "10.10.10.2",
        },
        "show ip  route vrf BLU": {"0.0.0.0/0": "10.30.20.1"},
        "show ip ospf interface brief": {
            "Gi3": {"area": 0, "cost": 1, "state": "P2P"},
            "_mode": "strict",
        },
        "show ip ospf neighbor": {
            "192.168.255.1": {"state": "FULL"},
            "2.2.2.2": {"state": "FULL"},
            "_mode": "strict",
        },
        "show ip ospf database database-summary | in Total": {"total_lsa": 8},
        "show ip eigrp interfaces": {
            "intf": {"_mode": "strict", "list": ["Gi3", "Lo1"]}
        },
        "show ip eigrp neighbors": {
            "nbrs": {"_mode": "strict", "list": ["10.10.10.2", "2.2.2.2"]}
        },
        "show bgp all summary": {
            "10.10.10.2": {"asn": 888, "rcv_pfx": 2},
            "10.10.20.2": {"asn": 889, "rcv_pfx": 3},
            "_mode": "strict",
        },
        "show nve vni": {
            10301: {"bdi": 301, "state": "Up", "vrf": "BLU"},
            10302: {"bdi": 302, "state": "Up", "vrf": "GRN"},
            "_mode": "strict",
        },
        "show nve peers": {
            10301: {"peer": "192.168.10.10", "state": "UP"},
            10302: {"peer": "192.168.10.10", "state": "UP"},
            "_mode": "strict",
        },
        "show crypto session brief": {
            "21.16.9.23": {"intf": "Tu10", "status": "UA"},
            "_mode": "strict",
        },
    },
    ## --------------------------------------------------------------------------------------
    ## NXOS: Desired State for NXOS os-type
    ## --------------------------------------------------------------------------------------
    "nxos": {
        "show access-lists TEST_SSH_ACCESS": {
            "TEST_SSH_ACCESS": {
                "20": {
                    "action": "permit",
                    "dst": "any",
                    "protocol": "ip",
                    "src": "10.17.10.0/24",
                },
                "40": {
                    "action": "permit",
                    "dst": "any",
                    "protocol": "ip",
                    "src": "10.10.10.10/32",
                },
                "50": {"action": "deny", "dst": "any", "protocol": "ip", "src": "any"},
                "_mode": "strict",
            }
        },
    },
    ## --------------------------------------------------------------------------------------
    ## ASA: Desired State for ASA os-type
    ## --------------------------------------------------------------------------------------
    "asa": {
        "show run http": {
            "HTTP": {
                "10": {"intf": "mgmt", "src": "10.17.10.0/24"},
                "20": {"intf": "mgmt", "src": "10.10.10.10/32"},
                "30": {"intf": "mgmt", "src": "any"},
                "_mode": "strict",
            }
        },
        "show run ssh": {
            "SSH": {
                "10": {"intf": "mgmt", "src": "10.17.10.0/24"},
                "20": {"intf": "mgmt", "src": "10.10.10.10/32"},
                "30": {"intf": "mgmt", "src": "any"},
                "_mode": "strict",
            }
        },
    },
    "ckp": {},
    "wlc": {},
}

# --------------------------------------------------------------------------------------
# CMD: The command output (textFSM formatted) that is used to format the actual_state
# --------------------------------------------------------------------------------------
cmd_output = {
    ## --------------------------------------------------------------------------------------
    ## IOS/IOS-XE: Command output for IOS/IOS-XE os-type
    ## --------------------------------------------------------------------------------------
    "ios": {
        "show authentication sessions | count mab": "Number of lines which match regexp = 13",
        "show authentication sessions | count dot1x": "Number of lines which match regexp = 21",
  
                "show nve vni": "Interface  VNI        Multicast-group VNI state  Mode  BD    cfg vrf",
                "nve1       10301   N/A             Up         L3CP  301  CLI BLU",
                "nve1       10302   N/A             Up         L3CP  302  CLI GRN",
                "show nve peers": "Interface  VNI      Type Peer-IP          RMAC/Num_RTs   eVNI     state flags UP time",
                "nve1       10301 L3CP 192.168.1.2   2466.8cd1.5555 10301   UP   A/M 2d10h",
                "nve1       10302 L3CP 192.168.1.2   2466.8cd1.5555 10302   UP   A/M 2d10h",
                "show crypto session brief": "Status: A- Active, U - Up, D - Down, I - Idle, S - Standby, N - Negotiating",
                "        K - No IKE",
                "ivrf = (none)",
                "Peer            I/F          Username        Group/Phase1_id          Uptime   Status",
                "21.16.9.23  Tu11                         10.211.20.2             10:55:31 UA",  

    ## --------------------------------------------------------------------------------------
    ## NXOS: Command output for NXOS os-type
    ## --------------------------------------------------------------------------------------
    "nxos": {
        "show access-lists TEST_SSH_ACCESS": [
            {
                "action": "remark",
                "destination": "VLAN10",
                "modifier": "",
                "name": "TEST_SSH_ACCESS",
                "port": "",
                "protocol": "Access",
                "range": "",
                "sn": "10",
                "source": "-",
            },
            {
                "action": "permit",
                "destination": "any",
                "modifier": "",
                "name": "TEST_SSH_ACCESS",
                "port": "",
                "protocol": "ip",
                "range": "",
                "sn": "20",
                "source": "10.17.10.0/24",
            },
            {
                "action": "remark",
                "destination": "Access",
                "modifier": "",
                "name": "TEST_SSH_ACCESS",
                "port": "",
                "protocol": "MGMT",
                "range": "",
                "sn": "30",
                "source": "Citrix",
            },
            {
                "action": "permit",
                "destination": "any",
                "modifier": "",
                "name": "TEST_SSH_ACCESS",
                "port": "",
                "protocol": "ip",
                "range": "",
                "sn": "40",
                "source": "10.10.10.10/32",
            },
            {
                "action": "deny",
                "destination": "any",
                "modifier": "",
                "name": "TEST_SSH_ACCESS",
                "port": "",
                "protocol": "ip",
                "range": "",
                "sn": "50",
                "source": "any",
            },
        ]
    },
    ### ASA: Command output for IOS/IOS-XE os-type ###
    "asa": {
        "show run http": "http server enable\n"
        "http 0.0.0.0 0.0.0.0 mgmt\n"
        "http 10.17.10.0 255.255.255.0 mgmt\n"
        "http 10.10.10.10 255.255.255.255 mgmt",
        "show run ssh": "ssh stricthostkeycheck\n"
        "ssh 10.17.10.0 255.255.255.0 mgmt\n"
        "ssh 10.10.10.10 255.255.255.255 mgmt\n"
        "ssh 0.0.0.0 0.0.0.0 mgmt\n"
        "ssh timeout 30\n"
        "ssh version 2\n"
        "ssh key-exchange group dh-group1-sha1",
    },
    "ckp": {},
    "wlc": {},
}

# --------------------------------------------------------------------------------------
# ACTUAL: The actual state after it has been formatted by actual_state.py
# --------------------------------------------------------------------------------------
actual_state = {
    ## --------------------------------------------------------------------------------------
    ## IOS/IOS-XE: Actual State for IOS/IOS-XE os-type
    ## --------------------------------------------------------------------------------------
    "ios": {
        "show version": {"image": "15.2(7)E2"},
        "show ip access-lists TEST_SSH_ACCESS": {
            "TEST_SSH_ACCESS": {
                "10": {
                    "action": "permit",
                    "dst": "any",
                    "protocol": "ip",
                    "src": "10.17.10.0/24",
                },
                "20": {
                    "action": "permit",
                    "dst": "any",
                    "protocol": "ip",
                    "src": "10.10.10.10/32",
                },
                "30": {"action": "deny", "dst": "any", "protocol": "ip", "src": "any"},
            }
        },
        "show etherchannel summary": {
            "Po3": {
                "members": {
                    "Gi0/15": {"mbr_status": "D"},
                    "Gi0/16": {"mbr_status": "D"},
                },
                "protocol": "LACP",
                "status": "SD",
            }
        },
        "show ip interface brief": {
            "GigabitEthernet0/0": {"ip": "10.30.20.101", "status": "up"},
            "GigabitEthernet0/1": {"ip": "unassigned", "status": "up"},
        },
        "show cdp neighbors": {"Gig 0/3": {"Switch": "0/3"}},
        "show lldp neighbors": {"Gi3": {"Router": "Gi0/3"}},
        "show standby brief": {0: {"priority": 50, "state": "Active"}},
        "show switch": {
            1: {"priority": 15, "role": "Active", "state": "Ready"},
            2: {"priority": 14, "role": "Standby", "state": "Ready"},
            3: {"priority": 13, "role": "Member", "state": "Ready"},
        },
        "show  redundancy state | in state": {
            "my_state": "ACTIVE",
            "peer_state": "STANDBY HOT",
        },
        "show interfaces status": {
            "Gi0/0": {
                "duplex": "a-full",
                "speed": "auto",
                "status": "connected",
                "vlan": "routed",
            },
            "Gi0/1": {
                "duplex": "a-full",
                "speed": "auto",
                "status": "suspended",
                "vlan": 20,
            },
            "Gi0/2": {
                "duplex": "a-full",
                "speed": "auto",
                "status": "connected",
                "vlan": "trunk",
            },
        },
        "show interfaces switchport": {
            "Gi0/1": {"mode": "down (suspended member " "of bundle Po3)", "vlan": None},
            "Gi0/3": {"mode": "trunk", "vlan": ["10,20"]},
            "Po3": {"mode": "down", "vlan": None},
        },
        "show vlan brief": {
            10: {"intf": [], "name": "test"},
            20: {"intf": ["Gi0/1"], "name": "test20"},
        },
        "show spanning-tree": {10: ["Gi0/3"], 20: ["Gi0/3"]},
        "show mac address-table | count dynamic|DYNAMIC": {"total_mac": 1103},
        "show mac address-table vlan 852 | count dynamic|DYNAMIC": {"852_total_mac": 6},
        "show authentication sessions | count mab": {"auth_mab": 13},
        "show authentication sessions | count dot1x": {"auth_dot1x": 21},
        "show vrf": {"BLU": ["Lo50"]},
        "show ip route  summary | in Total": {"global_subnets": 20},
        "show ip route vrf BLU summary | in Total": {"BLU_subnets": 113},
        "show ip  route": {
            "0.0.0.0/0": "10.30.20.1",
            "1.1.1.1/32": "Loopback1",
            "10.10.10.0/24": "GigabitEthernet3",
            "10.10.10.1/32": "GigabitEthernet3",
            "10.30.20.0/24": "GigabitEthernet1",
            "10.30.20.102/32": "GigabitEthernet1",
            "2.2.2.2/32": "10.10.10.2",
            "21.1.1.1/32": "10.10.10.2",
            "23.1.1.1/32": "10.10.10.2",
            "4.4.4.4/32": "10.10.10.2",
            "5.5.5.5/32": "10.10.10.2",
            "6.6.6.6/32": "10.10.10.2",
            "192.168.14.4/30": "192.168.14.2",
            "192.168.25.41/32": "Loopback1",
            "192.168.25.42/32": ["192.168.14.2", "192.168.14.10"],
            "192.168.25.43/32/32": "192.168.14.2",
            "192.168.25.45": "Loopback2",
            "192.168.25.47": "Loopback3",
        },
        "show ip  route vrf BLU": {
            "50.1.1.1/32": "Loopback50",
            "10.12.1.0/27": ["192.168.12.1", "192.168.12.5"],
            "10.12.242.64/28": ["192.168.12.1", "192.168.12.5"],
            "172.16.10.0/24": "10.80.10.2",
            "172.16.20.0/24": "10.80.10.2",
        },
        "show ip ospf interface brief": {
            "Gi3": {"area": 0, "cost": 1, "state": "P2P"},
            "Lo7": {"area": 0, "cost": 1, "state": "LOOP"},
            "Lo8": {"area": 2, "cost": 1, "state": "LOOP"},
        },
        "show ip ospf neighbor": {
            "192.168.255.1": {"state": "FULL"},
            "2.2.2.2": {"state": "FULL"},
        },
        "show ip ospf database database-summary | in Total": {"total_lsa": 11},
        "show ip eigrp interfaces": {"intf": ["Gi3", "Lo20"]},
        "show ip eigrp neighbors": {"nbrs": ["10.10.10.2"]},
        "show bgp all summary": {"10.10.10.2": {"asn": 888, "rcv_pfx": 1}},
        "show nve vni": {
            10301: {"bdi": 301, "vrf": "BLU", "state": "Up"},
            10302: {"bdi": 302, "vrf": "GRN", "state": "Up"},
        },
        "show nve peers": {
            10301: {"peer": "192.168.1.2", "state": "UP"},
            10302: {"peer": "192.168.1.2", "state": "UP"},
        },
        "show crypto session brief": {"21.16.9.23": {"intf": "Tu11", "status": "UA"}},
    },
    ## --------------------------------------------------------------------------------------
    ## NXOS: Actual State for NXOS os-type
    ## --------------------------------------------------------------------------------------
    "nxos": {
        "show access-lists TEST_SSH_ACCESS": {
            "TEST_SSH_ACCESS": {
                "20": {
                    "action": "permit",
                    "dst": "any",
                    "protocol": "ip",
                    "src": "10.17.10.0/24",
                },
                "40": {
                    "action": "permit",
                    "dst": "any",
                    "protocol": "ip",
                    "src": "10.10.10.10/32",
                },
                "50": {"action": "deny", "dst": "any", "protocol": "ip", "src": "any"},
            }
        }
    },
    ## --------------------------------------------------------------------------------------
    ## ASA: Actual State for ASA os-type
    ## --------------------------------------------------------------------------------------
    "asa": {
        "show run http": {
            "HTTP": {
                "10": {"intf": "mgmt", "src": "any"},
                "20": {"intf": "mgmt", "src": "10.17.10.0/24"},
                "30": {"intf": "mgmt", "src": "10.10.10.10/32"},
            }
        },
        "show run ssh": {
            "SSH": {
                "10": {"intf": "mgmt", "src": "10.17.10.0/24"},
                "20": {"intf": "mgmt", "src": "10.10.10.10/32"},
                "30": {"intf": "mgmt", "src": "any"},
            }
        },
    },
    "ckp": {},
    "wlc": {},
}
