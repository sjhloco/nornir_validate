import os

import yaml
from nornir import InitNornir
from nornir_inspect import nornir_inspect
from nornir_rich.functions import print_result

from nr_val import val_file_builder, validate

nr = InitNornir(config_file="config.yml")

# ----------------------------------------------------------------------------
# Validation: An example using an input from a variable or loaded from a file
# ----------------------------------------------------------------------------
# my_input_data = {
#     "groups": {
#         "ios": {
#             "intf_bonded": {
#                 "port_channel": {
#                     "Po1": {"protocol": "LACP", "members": ["Gi0/2", "Gi0/3"]}
#                 }
#             },
#         }
#     }
# }
with open("input_data.yml") as tmp_data:
    input_data = yaml.load(tmp_data, Loader=yaml.Loader)

### RUN: To run with either of the inputs
# result = nr.run(task=validate, input_data=input_data)

### Report: Need to add a save_report arg, either "" for local dir (may have to use os.getcwd()) or an actual directory path (~/Documents/Coding/Nornir/code/new_nr_val/folder1)
# result = nr.run(task=validate, input_data=input_data, save_report="")

### PRINT: Not sure if will change options
# print_result(result, vars=["result", "report_text"])
# Incase I want to print differently
# for each_host in nr.inventory.hosts.keys():  # noqa: SIM118
#     print_result(
#         result[each_host][0],
#         vars=[
#             "host",
#             "result",
#             "report_text",
#         ],
#     )


# ========================= Generate validate file ========================================
with open("ios_subfeat_index.yml") as tmp_data:
    input_data = yaml.load(tmp_data, Loader=yaml.Loader)

### With input index file
# result = nr.run(task=val_file_builder, input_data=input_data)

### With input index file and directory to save in
# result = nr.run(
#     task=val_file_builder,
#     input_data=input_data,
#     directory="/Users/mucholoco/Documents/Coding/Nornir/code/new_nr_val/folder1",
# )

### Without an input index file
result = nr.run(task=val_file_builder)

# result = nr.run(
#     task=val_file_builder, input_data=input_data, directory=""
# )  # save report in current location

# result = nr.run(task=val_file_builder, input_data="", directory="")

# breakpoint()
# nornir_inspect(result)


### PRINT:
# print_result(result)  #! Unhash to see output of failed netmiko commands

for each_host in nr.inventory.hosts.keys():  # noqa: SIM118
    print_result(
        result[each_host][0],
        vars=[
            "host",
            "result",
            "used_subfeat",
            "not_used_subfeat",
            "file_info",
        ],
    )
