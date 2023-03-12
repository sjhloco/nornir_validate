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
! python feature_builder.py -cf <os_type>_<feature>                                     Creates the feature and test feature directory structure (folders and files)
! python new_val_builder.py -cmd <os_type> <feature>                                    Generates the commands used to generates a validation file (saved to <os_type>_<feature>_cmds.yml)
! python feature_builder.py -di <netmiko_ostype> <command> <ip address or filename>     Generates the cmd_output data structure (prints to screen)
! python new_val_builder.py -val <os_type> <feature>                                    Generates the validate file (saved to <os_type>_<feature>_desired_state.yml)
! python new_val_builder.py -ds <os_type> <feature>                                     Creates the desired_state data structure (saved to <os_type>_<feature>_desired_state.yml) 
! python new_val_builder.py -as <os_type> <feature>                                     Creates the actual_state data structure (saved to <os_type>_<feature>_actual_state.yml)
"""

USERNAME = "test_user"
PASSWORD = "L00K_pa$$w0rd_github!"


# ----------------------------------------------------------------------------
# ARG: Flags to define what is run, all take 2 arguments except -di that takes 3
# ----------------------------------------------------------------------------
def _create_parser() -> Dict[str, Any]:
    """
    This function creates a parser object, adds arguments to it, and returns the arguments as a
    dictionary
    :return: The vars() function returns the __dict__ attribute of the object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-cf",
        "--create_feature",
        nargs=2,
        help="Creates the feature and feature test directories",
    )
    parser.add_argument(
        "-cmd",
        "--create_commands",
        nargs=2,
        help="Renders that sub-feature index creating a file of commands to gather the output on which the validation file is created",
    )
    parser.add_argument(
        "-di",
        "--discovery",
        nargs=3,
        help="Generates the data-modeled command output from a device or a static file",
    )
    parser.add_argument(
        "-val",
        "--create_val_file",
        nargs=2,
        help="Generates the validation file from cmd_output and the actual_state.generate_val_file method",
    )
    parser.add_argument(
        "-as",
        "--format_actual_state",
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
# TMPL: Render and format jinja template (cmds or desired state)
# ----------------------------------------------------------------------------
def _render_tmpl(
    os_type: str, feature: str, input_data: Dict[str, Any], TMPL_PATH: str
) -> Dict[str, Any]:
    """
    > This function takes in the OS type, feature, input data, and template path and returns a
    dictionary of the rendered template

    :param os_type: str, feature: str, input_data: Dict[str, Any], TMPL_PATH: str
    :type os_type: str
    :param feature: The feature name
    :type feature: str
    :param input_data: This is the data that is passed in from the main function
    :type input_data: Dict[str, Any]
    :param TMPL_PATH: The path to the templates
    :type TMPL_PATH: str
    :return: A list of dictionaries.
    """
    # Loads the and renders the template
    env = Environment(
        loader=FileSystemLoader(TMPL_PATH),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template(f"{feature}_desired_state.j2")
    sub_feat = input_data["all"][feature]
    output = tmpl.render(os_type=os_type, feature=feature, sub_features=sub_feat)

    # Convert Jinja string into yaml and list of dicts
    if re.search(r":\ >\d+", output):
        x = yaml.load(output.replace(">", "->"), Loader=yaml.Loader)
        return ast.literal_eval(str(x[0]).replace("->", ">"))
    else:
        return yaml.load(output, Loader=yaml.Loader)[0]


# ----------------------------------------------------------------------------
# PY_FORMAT: Format command output (validation file or actual state)
# ----------------------------------------------------------------------------
def _format_cmd_output(
    os_type: str, feature: str, method: str, cmd_output: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Imports the feature formatting module, then calls the relevant method on the module to format the output.

    :param os_type: str, feature: str, method: str, cmd_output: Dict[str, Any]
    :type os_type: str
    :param feature: The feature you want to validate
    :type feature: str
    :param method: This is the method that will be called from the feature module
    :type method: str
    :param cmd_output: This is the output of the command that was run
    :type cmd_output: Dict[str, Any]
    :return: The formatted data is being returned.
    """
    # import the feature formatting module
    feat_mod = f"feature_templates.{feature}.{feature}_actual_state"
    globals()[f"{feature}"] = importlib.import_module(feat_mod)
    # Generate the validation file or actual state
    formatted_data = defaultdict(dict)
    for sub_feature, output in cmd_output[feature].items():
        tmp_dict = defaultdict(dict)
        result = getattr(eval(feature), method)(
            str(os_type), sub_feature, output, tmp_dict
        )
        formatted_data[feature][sub_feature] = result
    return formatted_data


# ----------------------------------------------------------------------------
# FEAT_DIR: Create the Feature and feature test directories
# ----------------------------------------------------------------------------
def create_feature_dir(
    os_type: str, feature: str, TEST_PATH: str, TMPL_PATH: str
) -> None:
    """
    > Create new feature and feature test folders (copies those from skeleton_new_feature so
    includes all files)

    :param os_type: The operating system type (e.g. "linux", "windows")
    :type os_type: str
    :param feature: The name of the feature you want to create
    :type feature: str
    :param TEST_PATH: The path to the test directory
    :type TEST_PATH: str
    :param TMPL_PATH: The path to the templates folder
    :type TMPL_PATH: str
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
        os.path.join(TEST_PATH, f"ostype_newfeature_cmd_output.json"),
    ]
    new_names = [
        os.path.join(TMPL_PATH, f"{feature}_desired_state.j2"),
        os.path.join(TMPL_PATH, f"{feature}_actual_state.py"),
        os.path.join(TEST_PATH, f"{os_type}_{feature}_cmd_output.json"),
    ]
    for old_name, new_name in zip(old_names, new_names):
        if os.path.exists(old_name):
            os.rename(old_name, new_name)

    # Add subfeature_index if it doesnt already exist
    index_file = os.path.join(os.path.split(TEST_PATH)[0], "subfeature_index.yml")
    if not os.path.exists(index_file):
        shutil.copy(
            os.path.join(os.getcwd(), "skeleton_new_feature", "subfeature_index.yml"),
            os.path.split(TEST_PATH)[0],
        )

    if len(dir_created) != 0:
        result = "'\n '".join(dir_created)
        rc.print(f"✅ Created directories: \n '{result}'")


# ----------------------------------------------------------------------------
# COMMANDS: Generates a dictionary of commands for validation (used to create validation files)
# ----------------------------------------------------------------------------
def create_commands(os_type: str, feature: str, TEST_PATH: str, TMPL_PATH: str) -> None:
    """
    > This function takes the OS type, feature, and the path to the template file, and creates a YAML
    file with the commands to be executed

    :param os_type: str
    :type os_type: str
    :param feature: The name of the feature you want to create commands for
    :type feature: str
    :param TEST_PATH: The path to the test directory
    :type TEST_PATH: str
    :param TMPL_PATH: The path to the templates folder
    :type TMPL_PATH: str
    """
    # Loads data from YAML file
    index_file = os.path.join(os.path.split(TEST_PATH)[0], "subfeature_index.yml")
    with open(index_file) as input_data:
        index_data = yaml.load(input_data, Loader=yaml.FullLoader)
    # Render and format the data
    commmands = _render_tmpl(os_type, feature, index_data, TMPL_PATH)
    # Save to yaml file
    cmds_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_commands.yml")
    with open(cmds_file, "w") as yaml_file:
        yaml.dump(commmands, yaml_file, sort_keys=False)
    rc.print(f"✅ Created the file '{ cmds_file}'")


# ----------------------------------------------------------------------------
# CMD_OUTPUT: Generates the data structured command output
# ----------------------------------------------------------------------------
def generate_cmd_data(os_type: str, command: str, host_or_file: str) -> None:
    """
    > This function takes in a Rich Console object, an OS type, a command, and a host or file name. It
    then checks if the host is a valid IP address or if the file exists. If it's a valid IP address, it
    will run the command against the device and parse the output into a data structure. If it's a valid
    file, it will parse the file into a data structure. It then prints the data structure using the Rich
    Console object

    :param os_type: The OS type of the device you're running the command against
    :type os_type: str
    :param command: The command to run on the device or file
    :type command: str
    :param host_or_file: The IP address of the device or the path to the file containing the command
    output
    :type host_or_file: str
    """
    # Make sure IP is valid address or the file of cmd output exists
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
        rc.print(json.dumps(struc_data.splitlines()))
    else:
        rc.print(json.dumps(struc_data))


# ----------------------------------------------------------------------------
# VAL_FILE: Generate the validate yaml test file
# ----------------------------------------------------------------------------
def create_val_file(os_type: str, feature: str, TEST_PATH: str) -> None:
    """
    > It takes the output of the `cmd_output` function and passes it through the `_format_cmd_output`
    function to generate the validation file

    :param os_type: The operating system type, e.g. 'linux' or 'windows'
    :type os_type: str
    :param feature: The feature to generate the validation file for
    :type feature: str
    :param TEST_PATH: The path to the test directory
    :type TEST_PATH: str
    """
    # Load the cmd output file
    cmd_output_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_cmd_output.json")
    with open(cmd_output_file) as input_data:
        cmd_output = json.load(input_data)
    # Generate the validation file by passing through python formatting
    val_data = _format_cmd_output(os_type, feature, "generate_val_file", cmd_output)
    # Save to yaml
    val_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_validate.yml")
    with open(val_file, "w") as yaml_file:
        yaml.dump(dict(all=dict(val_data)), yaml_file, sort_keys=False)
    rc.print(f"✅ Created the file '{val_file}'")


# ----------------------------------------------------------------------------
# DESIRED_STATE: Create the desired state yaml test file
# ----------------------------------------------------------------------------
def create_desired_state(
    os_type: str, feature: str, TEST_PATH: str, TMPL_PATH: str
) -> None:
    """
    It takes the data from the `validate.yml` file, renders the template, and saves the result to a file

    :param os_type: The operating system type
    :type os_type: str
    :param feature: The name of the feature to create the desired state for
    :type feature: str
    :param TEST_PATH: The path to the test directory
    :type TEST_PATH: str
    :param TMPL_PATH: The path to the templates folder
    :type TMPL_PATH: str
    """
    # Loads data from YAML file
    val_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_validate.yml")
    with open(val_file) as input_data:
        val_data = yaml.load(input_data, Loader=yaml.FullLoader)
    # Render and format the data
    desired_state = _render_tmpl(os_type, feature, val_data, TMPL_PATH)
    # Save to yaml file
    ds_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_desired_state.yml")
    with open(ds_file, "w") as yaml_file:
        yaml.dump(desired_state, yaml_file, sort_keys=False)
    rc.print(f"✅ Created the file '{ds_file}'")


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Create the ACTUAL state yaml test file
# ----------------------------------------------------------------------------
def format_actual_state(os_type: str, feature: str, TEST_PATH: str) -> None:
    """
    > It takes the command output file and converts it to the actual state file

    :param os_type: The OS type (e.g. linux, windows, aix)
    :type os_type: str
    :param feature: The name of the feature you want to create the actual state for
    :type feature: str
    :param TEST_PATH: The path to the test directory
    :type TEST_PATH: str
    """
    # Load the cmd output file
    cmd_output_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_cmd_output.json")
    with open(cmd_output_file) as input_data:
        cmd_output = json.load(input_data)
    # Generate the validation file by passing through python formatting
    actual_state = _format_cmd_output(
        os_type, feature, "format_actual_state", cmd_output
    )
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
    global rc
    my_theme = {"repr.ipv4": "none", "repr.number": "none", "repr.call": "none"}
    rc = Console(theme=Theme(my_theme))

    args = _create_parser()
    os_type = [x for x in args.values() if x != None][0][0]
    feature = [x for x in args.values() if x != None][0][1]

    TEST_PATH = os.path.join(os.getcwd(), "tests", "os_test_files", os_type, feature)
    TMPL_PATH = os.path.join(os.getcwd(), "feature_templates", feature)
    # Dependant on the flag run the relevant function
    if args["create_feature"] != None:
        create_feature_dir(os_type, feature, TEST_PATH, TMPL_PATH)
    elif args["create_commands"] != None:
        create_commands(os_type, feature, TEST_PATH, TMPL_PATH)
    elif args["discovery"] != None:
        host_or_file = args["discovery"][2]
        generate_cmd_data(os_type, feature, host_or_file)
    elif args["create_val_file"] != None:
        create_val_file(os_type, feature, TEST_PATH)
    elif args["create_desired_state"] != None:
        create_desired_state(os_type, feature, TEST_PATH, TMPL_PATH)
    elif args["format_actual_state"] != None:
        format_actual_state(os_type, feature, TEST_PATH)
    else:
        raise Exception(
            "At least one of the arguments '-cf', '-as' or '-ds' is required"
        )


if __name__ == "__main__":
    main()
