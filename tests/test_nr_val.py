"""These unittests test the operation of nornir_validate (nr_val.py), they do not methods related to validations.

Use test_validations.py to test the different os_type command validations (desired_state, cmd_output, actual_state)
"""

import os

import pytest
from nornir import InitNornir

from nr_val import (
    merge_feat_subfeat,
    merge_os_types,
    remove_cmds_desired_state,
    return_feature_desired_data,
    return_yaml_desired_state,
    strip_empty_feat,
)

# ----------------------------------------------------------------------------
# Directory that holds inventory files
# ----------------------------------------------------------------------------
test_inventory = os.path.join(os.path.dirname(__file__), "test_inventory")


# ----------------------------------------------------------------------------
# Tests all the methods within nr_val.py
# ----------------------------------------------------------------------------


# MERGE_FEAT: Tests merging
def test_merge_feat_subfeat() -> None:
    err_msg = "❌ return_merge_feat_subfeat: Function testing failed"
    desired_output = {
        "feat1": {"sub_feat1": {"key1": 1, "key2": 2}, "sub_feat3": {"key1": 1}}
    }
    tmp_data = {
        "feat1": {"sub_feat1": {"key3": 3}, "sub_feat2": {"key1": 1}},
        "feat2": {"sub_feat1": {"key1": 1}},
    }
    merge_feat_subfeat(desired_output, tmp_data)
    actual_output = {
        "feat1": {
            "sub_feat1": {"key1": 1, "key2": 2, "key3": 3},
            "sub_feat3": {"key1": 1},
            "sub_feat2": {"key1": 1},
        },
        "feat2": {"sub_feat1": {"key1": 1}},
    }
    assert actual_output == desired_output, err_msg


# MERGE_OS_TYPE: Tests merging of nornir platforms (device types)
def test_merge_os_types() -> None:
    err_msg = "❌ merge_os_types: Function testing failed"
    nr = InitNornir(
        inventory={
            "plugin": "SimpleInventory",
            "options": {
                "host_file": os.path.join(test_inventory, "hosts.yml"),
                "group_file": os.path.join(test_inventory, "groups.yml"),
            },
        },
        logging={"enabled": False},
    )

    desired_output = ["cisco_ios", "cisco_iosxe", "ios"]
    actual_output = merge_os_types(nr.inventory.hosts["TEST_HOST"])
    assert actual_output == desired_output, err_msg


# DESIRED_STATE_DATA: Tests creating data structure for desired state templating (combines features, sub-features and feature_path)
def test_return_feature_desired_data() -> None:
    err_msg = "❌ return_feature_desired_data: Function testing failed"
    desired_output = return_feature_desired_data({"system": {"image": "15.2(7)E2"}})
    actual_output = {
        "system": {
            "file": "system_desired_state.j2",
            "sub_features": {"image": "15.2(7)E2"},
        }
    }
    assert actual_output == desired_output, err_msg


# DESIRED_STATE_YAML: Tests serializing string returned by Jinja into YAML
def test_return_yaml_desired_state() -> None:
    err_msg = "❌ return_yaml_desired_state: Function testing failed"
    input_data = "\n- neighbor:\n    cdp:\n      show cdp neighbors:\n        Gig 0/8:\n          HME-AIR-WLC01: Gig 0/0/1\n        Gig 0/11:\n          HME-2802-AP01: Gig 0\n"
    desired_output = return_yaml_desired_state(input_data)
    actual_output = {
        "neighbor": {
            "cdp": {
                "show cdp neighbors": {
                    "Gig 0/8": {"HME-AIR-WLC01": "Gig 0/0/1"},
                    "Gig 0/11": {"HME-2802-AP01": "Gig 0"},
                }
            }
        }
    }
    assert actual_output == desired_output, err_msg


# CLEAN_DESIRED_STATE: Tests removing any empty (None) features, sub-features or commands
def test_strip_empty_feat() -> None:
    err_msg = "❌ strip_empty_feat: Function testing failed"
    input_data = {
        "system": {"image": {"show version": "15.2(7)E2"}},
        "neighbor": {},
        "interface": {"intf": {}},
        "layer2": {"vlan": {"show vlan brief": None}},
    }
    desired_output = strip_empty_feat(input_data)
    actual_output = {"system": {"image": {"show version": "15.2(7)E2"}}}
    assert actual_output == desired_output, err_msg


# CLEAN_CMD_DESIRED_STATE: Tests removing commands from the desired state sub-features
def test_remove_cmds_desired_state() -> None:
    err_msg = "❌ remove_cmds_desired_state: Function testing failed"
    input_data = {
        "intf": {
            "ip_brief": {
                "show ip interface brief": {
                    "Loopback1": {"ip": "10.10.255.1", "status": "up"}
                }
            }
        },
        "route_protocol": {
            "ospf_intf_nbr": {
                "show ip ospf interface brief": "SUB_FEATURE_COMBINED_CMD",
                "show ip ospf neighbor": {
                    "Gi0/3": {
                        "pid": 3,
                        "area": 1,
                        "nbr": {"_mode": "strict", "192.168.230.2": "FULL"},
                    }
                },
            },
        },
    }
    desired_output = remove_cmds_desired_state(input_data)
    actual_output = {
        "intf": {"ip_brief": {"Loopback1": {"ip": "10.10.255.1", "status": "up"}}},
        "route_protocol": {
            "ospf_intf_nbr": {
                "Gi0/3": {
                    "pid": 3,
                    "area": 1,
                    "nbr": {"_mode": "strict", "192.168.230.2": "FULL"},
                }
            }
        },
    }
    assert actual_output == desired_output, err_msg
