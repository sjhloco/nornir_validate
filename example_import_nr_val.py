import argparse
import os

import yaml
from nornir import InitNornir

# from nornir_inspect import nornir_inspect
from nr_val import print_build_result, print_val_result, val_file_builder, validate

nr = InitNornir(config_file="config.yml")

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--validation", action="store_true")
parser.add_argument("-g", "--gen_val_file", action="store_true")
parser.add_argument("data_file", nargs="?", default="input_data.yml", help="Input file")
args = parser.parse_args()


# ----------------------------------------------------------------------------
# LOAD: Load files used by the script
# ----------------------------------------------------------------------------
with open(args.data_file) as tmp_data:
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


# ----------------------------------------------------------------------------
# Validation: Examples of doing validation with the differing options
# ----------------------------------------------------------------------------
if args.validation:
    ### RUN: To run with either of the inputs
    result = nr.run(task=validate, input_data=input_data)

    ### Report: Need to add a save_report arg, either "" for local dir (may have to use os.getcwd()) or an actual directory path (~/Documents/Coding/Nornir/code/new_nr_val/folder1)
    # result = nr.run(task=validate, input_data=input_data, save_report="")

    ### PRINT: Uses my custom nornir.rich print
    print_val_result(result)


# ----------------------------------------------------------------------------
# Generate Validation file: Examples of creating validation files with the differing options
# ----------------------------------------------------------------------------
elif args.gen_val_file:
    ### Without an input index file
    if args.data_file == "input_data.yml":
        result = nr.run(task=val_file_builder)
    ### With input index file, save report in current location
    else:
        result = nr.run(task=val_file_builder, input_data=input_data)

    ### With input index file and directory to save in
    # result = nr.run(
    #     task=val_file_builder,
    #     input_data=input_data,
    #     directory="/Users/mucholoco/Documents/Coding/Nornir/code/new_nr_val/folder1",
    # )

    ### PRINT: Normal print
    # print_build_result(result, nr)
    # Print errors in val file build (output of failed netmiko commands)
    print_val_result(result)
