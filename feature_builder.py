import os
import re
import ast
import yaml
import json
import shutil
import argparse
import importlib
from getpass import getpass
from typing import Any, Dict, List
from collections import defaultdict
from ipaddress import ip_address

from rich.theme import Theme
from rich.console import Console
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from netmiko import ConnectHandler
from ntc_templates.parse import parse_output

# ----------------------------------------------------------------------------
# Variables and information about running the script
# ----------------------------------------------------------------------------
""" Can be running using any for the following flags:
! python feature_builder.py -cf <os_type>_<feature_name>                                  Generate the feature and test feature file structure
! python feature_builder.py -di <netmiko_ostype> <command> <ip address or filename>       Generate the data structured cmd_output
! python new_val_builder.py -ds <os_type> <feature>                                       Generate the desired state (saved to <os_type>_<feature>_desired_state.yml)  
! python new_val_builder.py -as <os_type> <feature>                                       Generate the desired state (saved to <os_type>_<feature>_actual_state.yml) 
"""

# USERNAME = "test_user"
# PASSWORD = "L00K_pa$$w0rd_github!"

# ----------------------------------------------------------------------------
# Flags to define what is run, all take 2 arguments except -di that takes 3
# ----------------------------------------------------------------------------
def _create_parser() -> Dict[str, Any]:
    """
    This function creates a parser object, adds arguments to it, and returns the arguments as a
    dictionary
    :return: The vars() function returns the __dict__ attribute of the object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-di",
        "--discovery",
        nargs=3,
        help="Generates the data-modeled cmd output from a device or a static file",
    )
    parser.add_argument(
        "-cf",
        "--create_feature",
        nargs=2,
        help="Creates the feature and feature test directories",
    )
    parser.add_argument(
        "-as",
        "--create_actual_state",
        nargs=2,
        help="Feeds the cmd output through actual state formatting to create the actual state test file",
    )
    parser.add_argument(
        "-ds",
        "--create_desired_state",
        nargs=2,
        help="Renders that validation input against the desired_state template to create the desired state test file",
    )

    return vars(parser.parse_args())


# ----------------------------------------------------------------------------
# Create the Feature and feature test directories
# ----------------------------------------------------------------------------
def create_feature_dir(rc: "Rich", os_type: str, feature: str) -> None:
    """
    > Create new feature and feature test folders (copies those from skeleton_new_feature so
    includes all files)

    The function takes in three arguments:

    - `rc`: This is the `Rich` object that we imported from the `rich` library. It's used to print out
    the output in a nice format.
    - `os_type`: This is the operating system type that we want to create the feature for.
    - `feature`: This is the name of the feature that we want to create

    :param rc: This is the Rich object that is passed to the function. It is used to print to the
    console
    :type rc: "Rich"
    :param os_type: The operating system type (e.g. "linux", "windows")
    :type os_type: str
    :param feature: The name of the feature you want to create
    :type feature: str
    """
    # Create new feature and feature test folders (copies those from skeleton_new_feature so includes all files)
    dir_created = []
    feat_dir = os.path.join(os.getcwd(), "skeleton_new_feature", "newfeature")
    feat_test_dir = os.path.join(os.getcwd(), "skeleton_new_feature", "newfeature_test")
    for src, dst in [(feat_dir, TMPL_PATH), (feat_test_dir, TEST_PATH)]:
        if not os.path.exists(dst):
            shutil.copytree(src, dst, ignore=None, dirs_exist_ok=False)
            dir_created.append(dst)
    # Rename the files within the feature and feature test directories
    old_names = [
        os.path.join(TMPL_PATH, "newfeature_desired_state.j2"),
        os.path.join(TMPL_PATH, "newfeature_actual_state.py"),
        os.path.join(TEST_PATH, f"ostype_newfeature_validate.yml"),
        os.path.join(TEST_PATH, f"ostype_newfeature_cmd_output.json"),
    ]
    new_names = [
        os.path.join(TMPL_PATH, f"{feature}_desired_state.j2"),
        os.path.join(TMPL_PATH, f"{feature}_actual_state.py"),
        os.path.join(TEST_PATH, f"{os_type}_{feature}_validate.yml"),
        os.path.join(TEST_PATH, f"{os_type}_{feature}_cmd_output.json"),
    ]
    for old_name, new_name in zip(old_names, new_names):
        if os.path.exists(old_name):
            os.rename(old_name, new_name)

    if len(dir_created) != 0:
        result = "' and '".join(dir_created)
        rc.print(f"✅ Created directories '{result}'")


# ----------------------------------------------------------------------------
# Generates the data structured command output
# ----------------------------------------------------------------------------
def generate_cmd_data(
    rc: "Rich", os_type: str, command: str, host_or_file: str
) -> None:
    """
    > This function takes in a Rich Console object, an OS type, a command, and a host or file name. It
    then checks if the host is a valid IP address or if the file exists. If it's a valid IP address, it
    will run the command against the device and parse the output into a data structure. If it's a valid
    file, it will parse the file into a data structure. It then prints the data structure using the Rich
    Console object

    :param rc: Rich is a library that allows you to print in color and format text
    :type rc: "Rich"
    :param os_type: The OS type of the device you're running the command against
    :type os_type: str
    :param command: The command to run on the device or file
    :type command: str
    :param host_or_file: The IP address of the device or the path to the file containing the command
    output
    :type host_or_file: str
    """

    valid_ip, valid_file = (False for i in range(2))
    try:
        ip_address(host_or_file)
        valid_ip = True
    except:
        try:
            with open(host_or_file, encoding="utf-8") as f:
                cmd_output = f.read()
                valid_file = True
        except:
            rc.print("❌ The IP is invalid or the file does not exist")

    # Run against a device, get command output and parse into a data structure
    if valid_ip == True:
        if "USERNAME" not in globals():
            user = input("Username: ")
        else:
            user = USERNAME
        if "PASSWORD" not in globals():
            pword = getpass("Password: ")
        else:
            pword = PASSWORD
        creds = dict(
            device_type=os_type, host=host_or_file, username=user, password=pword
        )
        with ConnectHandler(**creds) as net_connect:
            struc_data = net_connect.send_command(command, use_textfsm=True)
    # Parse the loaded command output into a data structure
    elif valid_file == True:
        struc_data = parse_output(os_type, command, cmd_output)

    # Print using JSON dump to change all ' for ""
    if isinstance(struc_data, str):
        rc.print(struc_data.splitlines())
    else:
        rc.print(json.dumps(struc_data))


# ----------------------------------------------------------------------------
# Create the desired state yaml test file
# ----------------------------------------------------------------------------
def create_desired_state(rc: "Rich", os_type: str, feature: str) -> None:
    """
    It takes the data from the `validate.yml` file, renders the template, and saves the result to a file

    :param rc: This is the Rich object that we created earlier
    :type rc: "Rich"
    :param os_type: The operating system type
    :type os_type: str
    :param feature: The name of the feature to create the desired state for
    :type feature: str
    """
    # Loads data from YAML file
    val_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_validate.yml")
    with open(val_file) as input_data:
        val_data = yaml.load(input_data, Loader=yaml.FullLoader)
    # Loads the and render the template
    env = Environment(
        loader=FileSystemLoader(TMPL_PATH),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template(f"{feature}_desired_state.j2")
    sub_feat = val_data["all"][feature]
    ds = tmpl.render(os_type=os_type, feature=feature, sub_features=sub_feat)

    # Convert Jinja string into yaml and list of dicts
    if re.search(r":\ >\d+", ds):
        x = yaml.load(ds.replace(">", "->"), Loader=yaml.Loader)
        desired_state = ast.literal_eval(str(x[0]).replace("->", ">"))
    else:
        desired_state = yaml.load(ds, Loader=yaml.Loader)[0]

    # Save to yaml file
    ds_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_desired_state.yml")
    # with open(ds_file, "w") as f:
    #     yaml.dump(yaml.load(ds, Loader=yaml.Loader)[0], f, sort_keys=False)
    with open(ds_file, "w") as yaml_file:
        yaml.dump(desired_state, yaml_file, sort_keys=False)
    rc.print(f"✅ Created the file '{ds_file}'")


# ----------------------------------------------------------------------------
# Create the desired state yaml test file
# ----------------------------------------------------------------------------
def create_actual_state(rc: "Rich", os_type: str, feature: str) -> None:
    """
    > It takes the command output file and converts it to the actual state file

    :param rc: This is the Rich class object that we created earlier
    :type rc: "Rich"
    :param os_type: The OS type (e.g. linux, windows, aix)
    :type os_type: str
    :param feature: The name of the feature you want to create the actual state for
    :type feature: str
    """
    # import the feature formatting module
    feat_mod = f"feature_templates.{feature}.{feature}_actual_state"
    globals()[f"{feature}"] = importlib.import_module(feat_mod)
    # Load the cmd output file
    cmd_output_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_cmd_output.json")
    with open(cmd_output_file) as input_data:
        cmd_output = json.load(input_data)
    # Generate the actual state
    actual_state = defaultdict(dict)
    for sub_feature, output in cmd_output[feature].items():
        tmp_dict = defaultdict(dict)
        result = eval(feature).format_output(os_type, sub_feature, output, tmp_dict)
        actual_state[feature][sub_feature] = result

    # Save to yaml
    as_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_actual_state.yml")
    with open(as_file, "w") as yaml_file:
        yaml.dump(dict(actual_state), yaml_file, sort_keys=False)
    rc.print(f"✅ Created the file '{as_file}'")


# ----------------------------------------------------------------------------
# Runs the script
# ----------------------------------------------------------------------------
def main():
    """
    The engine that runs the different functions based on arguments passed at runtime
    """
    global TEST_PATH, TMPL_PATH
    my_theme = {"repr.ipv4": "none", "repr.number": "none", "repr.call": "none"}
    rc = Console(theme=Theme(my_theme))

    args = _create_parser()
    os_type = [x for x in args.values() if x != None][0][0]
    feature = [x for x in args.values() if x != None][0][1]
    TEST_PATH = os.path.join(os.getcwd(), "tests", "os_test_files", os_type, feature)
    TMPL_PATH = os.path.join(os.getcwd(), "feature_templates", feature)

    # Dependant on the flag run the relevant function
    if args["create_feature"] != None:
        create_feature_dir(rc, os_type, feature)
    elif args["discovery"] != None:
        host_or_file = args["discovery"][2]
        generate_cmd_data(rc, os_type, feature, host_or_file)
    elif args["create_desired_state"] != None:
        create_desired_state(rc, os_type, feature)
    elif args["create_actual_state"] != None:
        create_actual_state(rc, os_type, feature)
    else:
        raise Exception(
            "At least one of the arguments '-cf', '-as' or '-ds' is required"
        )


if __name__ == "__main__":
    main()
