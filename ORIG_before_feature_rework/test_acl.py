# a = {
#     "TEST_SSH_ACCESS": {
#         "10": {"action": "remark", "protocol": "Access", "src": "-", "dst": "any"},
#         "20": {
#             "action": "permit",
#             "protocol": "ip",
#             "src": "10.17.10.0/24",
#             "dst": "any",
#         },
#         "30": {"action": "remark", "protocol": "MGMT", "src": "Citrix", "dst": "any"},
#         "40": {
#             "action": "permit",
#             "protocol": "ip",
#             "src": "10.10.10.10/32",
#             "dst": "any",
#         },
#         "50": {"action": "deny", "protocol": "ip", "src": "any", "dst": "any"},
#     }
# }

acl = [
    {
        "action": "remark",
        "name": "TEST_SSH_ACCESS",
        "sn": "10",
        "source": "!!10_REMARK!!",
    },
    {
        "action": "permit",
        "name": "TEST_SSH_ACCESS",
        "sn": "20",
        "source": "!!20!!",
    },
    {
        "action": "remark",
        "name": "TEST_SSH_ACCESS",
        "sn": "30",
        "source": "!!30_REMARK!!",
    },
    {
        "action": "permit",
        "name": "TEST_SSH_ACCESS",
        "sn": "40",
        "source": "!!40!!",
    },
    {
        "action": "deny",
        "name": "TEST_SSH_ACCESS",
        "sn": "50",
        "source": "!!50!!",
    },
    {
        "action": "remark",
        "name": "TEST_SSH_ACCESS1",
        "sn": "10",
        "source": "!!10_REMARK!!",
    },
    {
        "action": "permit",
        "name": "TEST_SSH_ACCESS1",
        "sn": "20",
        "source": "!!20!!",
    },
    {
        "action": "remark",
        "name": "TEST_SSH_ACCESS1",
        "sn": "30",
        "source": "!!30_REMARK!!",
    },
    {
        "action": "permit",
        "name": "TEST_SSH_ACCESS1",
        "sn": "40",
        "source": "!!40!!",
    },
    {
        "action": "deny",
        "name": "TEST_SSH_ACCESS1",
        "sn": "50",
        "source": "!!50!!",
    },
]

from collections import defaultdict
from pprint import pprint

# List of ACL names
acl_names = set(item["name"] for item in acl)
# Dict of each ACL
acl_dict = {}
for each_acl_name in acl_names:
    tmp_acl = []
    for each_acl in acl:
        if each_acl_name == each_acl["name"]:
            tmp_acl.append(each_acl)
    acl_dict[each_acl_name] = tmp_acl


tmp_dict = defaultdict(dict)
for name, ace in acl_dict.items():
    while "remark" in str(ace):
        ace_count = len(ace)
        for idx, each_ace in enumerate(ace):
            if each_ace["action"] == "remark":
                for x in reversed(range(idx + 1, ace_count)):
                    ace[x]["sn"] = ace[x - 1]["sn"]
                del ace[idx]
                break
pprint(acl_dict)
# "remark" in str(acl_dict)

# for i in generator:
#     print(i)
# tmp_dict = defaultdict(dict)


# # First need to group into seperate acls
# for each_acl in acl:

#     tmp_dict[each_ace[mgmt_acl_name]] =

# for each_acl in acl:
#     ace_count = len(seq_ace)


# for name, seq_ace in a.items():
#     ace_count = len(seq_ace)
#     for idx, (seq, ace) in enumerate(seq_ace.items()):

#         if ace["action"] != "remark":
#             tmp_dict[name][seq] = ace
#         elif ace["action"] == "remark":
#             for x in range(idx + 1, ace_count):
#                 tmp_dict[name][ace["sn"]] = a[name]
#             breakpoint()
