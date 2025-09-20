import argparse
import os

import yaml
from nornir import InitNornir

# from nornir_inspect import nornir_inspect
from nornir_rich.functions import print_result

from nr_val import val_file_builder, validate

# from nornir_utils.plugins.functions import print_title, print_result

nr = InitNornir(config_file="config.yml")


parser = argparse.ArgumentParser()
parser.add_argument("-v", "--validation", action="store_true")
parser.add_argument("-g", "--gen_val_file", action="store_true")
args = parser.parse_args()


# ----------------------------------------------------------------------------
# LOAD: Load files used by the script
# ----------------------------------------------------------------------------
## VAL_FILE: Validation file
# data_file = "input_data.yml"
# data_file = "FG-WLC-AIR01_vals.yml"
# data_file = "ET-WLC-AIR01_vals.yml"
# data_file = "AZ1-ASA-VPN01_vals.yml"
data_file = "DC3-FPR-OOB01_vals.yml"
with open(data_file) as tmp_data:
    input_data = yaml.load(tmp_data, Loader=yaml.Loader)

## VAL_DATA: Raw validation data
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

## IDX: Index file which is used to generate validation files
# idx_file = "wlc_subfeat_index.yml"
idx_file = "asa_subfeat_index.yml"
with open(idx_file) as tmp_data:
    input_idx = yaml.load(tmp_data, Loader=yaml.Loader)


# ----------------------------------------------------------------------------
# Validation: Examples of doing validation with the differing options
# ----------------------------------------------------------------------------
if args.validation:
    ### RUN: To run with either of the inputs
    result = nr.run(task=validate, input_data=input_data)

    ### Report: Need to add a save_report arg, either "" for local dir (may have to use os.getcwd()) or an actual directory path (~/Documents/Coding/Nornir/code/new_nr_val/folder1)
    # result = nr.run(task=validate, input_data=input_data, save_report="")

    ### MY nornir_rich print
    # print_result(result, vars=["result", "report_text"])

    ### ORIG nornir_rich print, dont use as doesnt delete empty results when run with prt flag
    print_result(result, vars=["result"], line_breaks=True)
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


# ----------------------------------------------------------------------------
# Generate Validation file: Examples of creating validation files with the differing options
# ----------------------------------------------------------------------------
elif args.gen_val_file:
    ### With input index file, save report in current location
    result = nr.run(task=val_file_builder, input_data=input_idx)

    ### Without an input index file
    # result = nr.run(task=val_file_builder)

    ### With input index file and directory to save in
    # result = nr.run(
    #     task=val_file_builder,
    #     input_data=input_idx,
    #     directory="/Users/mucholoco/Documents/Coding/Nornir/code/new_nr_val/folder1",
    # )

    ## PRINT: Normal print
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

    ## PRINT: Error
    # print_result(result)  #! Unhash to see output of failed netmiko commands
