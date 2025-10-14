"""Can be running using any for the following flags.

python feature_builder.py -cf <os_type> <feature.subfeature>                          Creates the feature and test feature directory structure (folders and files)
python feature_builder.py -cmd <os_type> <feature>                                    Generates the commands used to generates a validation file (saved to <os_type>_<feature>_cmds.yml)
python feature_builder.py -di <netmiko_ostype> <feature.subfeature> <ip or filename>  Generates the cmd_output data structure (prints to screen)
python feature_builder.py -vf <os_type> <feature>                                     Generates the validate file (saved to <os_type>_<feature>_desired_state.yml)
python feature_builder.py -ds <os_type> <feature>                                     Creates the desired_state data structure (saved to <os_type>_<feature>_desired_state.yml)
python feature_builder.py -as <os_type> <feature>                                     Creates the actual_state data structure (saved to <os_type>_<feature>_actual_state.yml)
"""

import argparse
import ast
import importlib
import json
import os
import re
import shutil
from collections import defaultdict
from getpass import getpass
from ipaddress import ip_address
from typing import Any, Union

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from netmiko import ConnectHandler
from ntc_templates.parse import ParsingException, parse_output
from rich.console import Console
from rich.theme import Theme
from ruamel.yaml import YAML

# ----------------------------------------------------------------------------
# Rich console used to print by
# ----------------------------------------------------------------------------
my_theme = {"repr.ipv4": "none", "repr.number": "none", "repr.call": "none"}
rc = Console(theme=Theme(my_theme))


# ----------------------------------------------------------------------------
# ARG: Flags to define what is run, all take 2 arguments except -di that takes 3
# ----------------------------------------------------------------------------
def _create_parser() -> dict[str, Union[None, list[str]]]:
    """Takes input arguments to use as flags to run the relevant functions as well as os_type and feature_name.

    Returns:
        dict[str, Union[None, list[str]]]: All args have dict value of None except for used arg that has a list [os_type, feature_name]
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
        "-vf",
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
    os_type: str,
    feature: str,
    input_data: dict[str, dict[str, list[str]]],
    tmpl_path: str,
) -> Any:  # noqa: ANN401
    """Renders Jinja template for commands and desired state.

    Args:
        os_type (str): The network operating system type (based off netmiko platform)
        feature (str): The name of the feature new feature that is to be created
        input_data (dict[str, dict[str, list[str]]]): Contains sub-features that are to be rendered
        tmpl_path (str): The path to the templates folder, includes feature name
    Returns:
        Any: The rendered template as a nested dictionary (mypy only sees as Any) of {feature: {sub_feature: {key: value}}}
    """
    # Loads the and renders the template
    env = Environment(
        loader=FileSystemLoader(tmpl_path),
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
    os_type: str, feature: str, val_file: bool, cmd_output: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Imports the feature module (actual_state.py) calling the relevant method to format the output.

    Args:
        os_type (str): The network operating system type (based off netmiko platform)
        feature (str): The name of the new feature that is to be created
        val_file (bool): True if for generating a validation file, False for actual state
        cmd_output (dict[str, dict[str, Any]]): The data structured command output (x_cmd_output.json)

    Returns:
        dict[str, dict[str, Any]]: Actual state or validation file (same as actual state but without state info (i.e. interface status))
    """
    # import the feature formatting module
    feat_mod = f"feature_templates.{feature}.{feature}_actual_state"
    globals()[f"{feature}"] = importlib.import_module(feat_mod)
    # Generate the validation file or actual state
    actual_state: dict[str, dict[str, Any]] = defaultdict(dict)
    for sub_feature, output in cmd_output[feature].items():
        # EMPTY: If output is empty just adds an empty dictionary
        if output is None or len(output) == 0:
            result = {}
        else:
            # Gets per-sub-feature actual state structured data from imported feature_templates (python imports)
            result = eval(feature).format_actual_state(
                val_file, str(os_type), sub_feature, output
            )
            actual_state[feature][sub_feature] = result
    return dict(actual_state)


# ----------------------------------------------------------------------------
# FEAT_DIR: Create the Feature and feature test directories
# ----------------------------------------------------------------------------
def create_feature_dir(
    feature: str,
    subfeat: Union[str | None],
    test_path: str,
    tmpl_path: str,
) -> None:
    """Create new feature and feature test folders (copies those from skeleton_new_feature so includes all files).

    Args:
        feature (str): The name of the feature new feature that is to be created
        subfeat (str): The name of the new sub-feature that is to be created
        test_path (str): The path to the test directory, includes os_type and feature name
        tmpl_path (str): The path to the templates folder, includes feature name
    """
    # Needed as pyaml doesn't indent lists correctly (purely cosmetic)
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)  # control indentation depth

    # Create new feature and feature test folders (copies those from skeleton_new_feature so includes all files)
    dir_created = []
    feat_dir = os.path.join(os.getcwd(), "skeleton_new_feature", "newfeature")
    feat_test_dir = os.path.join(os.getcwd(), "skeleton_new_feature", "newfeature_test")
    for src, dst in [(feat_dir, tmpl_path), (feat_test_dir, test_path)]:
        if not os.path.exists(dst):
            shutil.copytree(src, dst, ignore=None, dirs_exist_ok=False)
            dir_created.append(dst)

    # Rename the files within the feature and feature test directories
    old_names = [
        os.path.join(tmpl_path, "newfeature_desired_state.j2"),
        os.path.join(tmpl_path, "newfeature_actual_state.py"),
    ]
    new_names = [
        os.path.join(tmpl_path, f"{feature}_desired_state.j2"),
        os.path.join(tmpl_path, f"{feature}_actual_state.py"),
    ]
    for old_name, new_name in zip(old_names, new_names):
        if os.path.exists(old_name):
            os.rename(old_name, new_name)

    # Add subfeature_index if it doesn't already exist
    index_file = os.path.join(os.path.split(test_path)[0], "subfeature_index.yml")
    try:
        with open(index_file) as input_data:
            index_data = yaml.load(input_data)
            prt_msg = f"✅ Updated the file '{index_file}'"
    except FileNotFoundError:
        index_data = {"all": {}}
        prt_msg = f"✅ Created the file '{index_file}'"
    # Add sub feature to index file
    if index_data["all"].get(feature) is None:
        index_data["all"][feature] = [subfeat]
    elif "subfeat" not in str(index_data["all"][feature]):
        index_data["all"][feature].append(subfeat)
    with open(index_file, "w", encoding="utf-8") as f:
        yaml.dump(index_data, f)

    # Print result of what was done
    if len(dir_created) != 0:
        result = "'\n '".join(dir_created)
        rc.print(f"✅ Created directories: \n '{result}'")
        rc.print(prt_msg)


# ----------------------------------------------------------------------------
# COMMANDS: Generates a dictionary of commands for validation (used to create validation files)
# ----------------------------------------------------------------------------
def create_commands(os_type: str, feature: str, test_path: str, tmpl_path: str) -> None:
    """Using the Jinja template conditionally (OS and feature) creates a YAML file containing the commands to be executed.

    Args:
        os_type (str): The network operating system type (based off netmiko platform)
        feature (str): The name of the new feature that is to be created
        test_path (str): The path to the test directory, includes os_type and feature name
        tmpl_path (str): The path to the templates folder, includes feature name
    """
    # Loads data from YAML file
    index_file = os.path.join(os.path.split(test_path)[0], "subfeature_index.yml")
    with open(index_file) as input_data:
        index_data = yaml.load(input_data, Loader=yaml.FullLoader)
    # Render and format the data
    commmands = _render_tmpl(os_type, feature, index_data, tmpl_path)
    # Save to yaml file
    cmds_file = os.path.join(test_path, f"{os_type}_{feature}_commands.yml")
    with open(cmds_file, "w") as yaml_file:
        yaml.dump(commmands, yaml_file, sort_keys=False)
    rc.print(f"✅ Created the file '{cmds_file}'")


# ----------------------------------------------------------------------------
# CMD_OUTPUT: Generates the data structured command output
# ----------------------------------------------------------------------------
def generate_cmd_data(
    os_type: str,
    feature: str,
    subfeat: Union[str, None],
    test_path: str,
    host_or_file: str,
) -> None:
    """Parses into data structure by running cmd against device (if valid IP) using file of raw output (non-parsed).

    Args:
        os_type (str): The network operating system type (netmiko platform)
        feature (str): The name of the new feature that is to be created
        subfeat (str): The name of the new sub-feature that is to be created
        test_path (str): The path to the test directory, includes os_type and feature name
        host_or_file (str): The IP address of the device or the path to the file containing the command output
    """
    # Load file data to be used by the function (JSON file may not exist)
    cmds_file = os.path.join(test_path, f"{os_type}_{feature}_commands.yml")
    with open(cmds_file) as yaml_file:
        cmd_data = yaml.safe_load(yaml_file)
    command = next(iter(cmd_data[feature][subfeat]), None)
    cmd_output_file = os.path.join(test_path, f"{os_type}_{feature}_cmd_output.json")
    try:
        with open(cmd_output_file, encoding="utf-8") as f:
            cmd_output_data = json.load(f)
            prt_msg = f"✅ Updated the file '{cmd_output_file}'"
    except FileNotFoundError:
        cmd_output_data = {feature: {}}
        prt_msg = f"✅ Created the file '{cmd_output_file}'"

    # Make sure IP is valid address or the file of cmd output exists
    try:
        ip_address(host_or_file)
        valid_ip, valid_file = True, False
    except ValueError:
        try:
            with open(host_or_file, encoding="utf-8") as f:
                cmd_output = f.read()
                valid_ip, valid_file = False, True
        except FileNotFoundError:
            valid_ip, valid_file = False, False
            rc.print("❌ The IP is invalid or the file does not exist")

    # DEVICE: Run against a device, get command output and parse into a data structure
    if valid_ip:
        user = os.environ.get("DVC_USER") or input("Username: ")
        pword = os.environ.get("DVC_PWORD") or getpass("Password: ")
        creds = dict(
            device_type=os_type, host=host_or_file, username=user, password=pword
        )
        with ConnectHandler(**creds) as net_connect:
            struc_data = net_connect.send_command(command, use_textfsm=True)
    # FILE: Parse the loaded command output into a data structure (if no ntc-template return list of strings)
    elif valid_file:
        try:
            struc_data = parse_output(os_type, command, cmd_output)
        except ParsingException:
            struc_data = cmd_output.splitlines()
    # JSON: Writes the data to json file
    cmd_output_data[feature][subfeat] = struc_data
    with open(cmd_output_file, "w", encoding="utf-8") as f:
        json.dump(cmd_output_data, f, indent=4)
    rc.print(prt_msg)


# ----------------------------------------------------------------------------
# VAL_FILE: Generate the validate yaml test file
# ----------------------------------------------------------------------------
def create_val_file(os_type: str, feature: str, test_path: str) -> None:
    """Takes the command output file and processes it to create the validation file.

    Args:
        os_type (str): The network operating system type (based off netmiko platform)
        feature (str): The name of the new feature to create actual state for
        test_path (str): The path to the test directory, includes os_type and feature name
    """
    # Load the cmd output file
    cmd_output_file = os.path.join(test_path, f"{os_type}_{feature}_cmd_output.json")
    with open(cmd_output_file) as input_data:
        cmd_output = json.load(input_data)
    # Generate the validation file by passing through python formatting
    val_data = _format_cmd_output(os_type, feature, True, cmd_output)
    # Save to yaml
    val_file = os.path.join(test_path, f"{os_type}_{feature}_validate.yml")
    with open(val_file, "w") as yaml_file:
        yaml.dump(dict(all=dict(val_data)), yaml_file, sort_keys=False)
    rc.print(f"✅ Created the file '{val_file}'")


# ----------------------------------------------------------------------------
# DESIRED_STATE: Create the desired state yaml test file
# ----------------------------------------------------------------------------
def create_desired_state(
    os_type: str, feature: str, test_path: str, tmpl_path: str
) -> None:
    """Renders the template using the data from validate.yml saving the result to file.

    Args:
        os_type (str): The network operating system type (based off netmiko platform)
        feature (str): The name of the new feature to create the desired state for
        test_path (str): The path to the test directory, includes os_type and feature name
        tmpl_path (str): The path to the templates folder, includes feature name
    """
    # Loads data from YAML file
    val_file = os.path.join(test_path, f"{os_type}_{feature}_validate.yml")
    with open(val_file) as input_data:
        val_data = yaml.load(input_data, Loader=yaml.FullLoader)
    # Render and format the data
    desired_state = _render_tmpl(os_type, feature, val_data, tmpl_path)
    # Save to yaml file
    ds_file = os.path.join(test_path, f"{os_type}_{feature}_desired_state.yml")
    with open(ds_file, "w") as yaml_file:
        yaml.dump(desired_state, yaml_file, sort_keys=False)
    rc.print(f"✅ Created the file '{ds_file}'")


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Create the ACTUAL state yaml test file
# ----------------------------------------------------------------------------
def format_actual_state(os_type: str, feature: str, test_path: str) -> None:
    """Takes the command output file and processes it to create actual state file.

    Args:
        os_type (str): The network operating system type (based off netmiko platform)
        feature (str): The name of the new feature to create actual state for
        test_path (str): The path to the test directory, includes os_type and feature name
    """
    # Load the cmd output file
    cmd_output_file = os.path.join(test_path, f"{os_type}_{feature}_cmd_output.json")
    with open(cmd_output_file) as input_data:
        cmd_output = json.load(input_data)
    # Generate the validation file by passing through python formatting
    actual_state = _format_cmd_output(os_type, feature, False, cmd_output)
    # Save to yaml
    as_file = os.path.join(test_path, f"{os_type}_{feature}_actual_state.yml")
    with open(as_file, "w") as yaml_file:
        yaml.dump(dict(actual_state), yaml_file, sort_keys=False)
    rc.print(f"✅ Created the file '{as_file}'")


# ----------------------------------------------------------------------------
# Runs the script
# ----------------------------------------------------------------------------
def main() -> None:
    """The engine that runs the different functions based on arguments passed at runtime."""
    my_theme = {"repr.ipv4": "none", "repr.number": "none", "repr.call": "none"}
    args = _create_parser()
    os_type = [x for x in args.values() if x is not None][0][0]
    feat_subfeat = [x for x in args.values() if x is not None][0][1]
    feature = feat_subfeat.split(".")[0]
    subfeat = feat_subfeat.split(".")[1] if len(feat_subfeat.split(".")) > 1 else None
    test_path = os.path.join(os.getcwd(), "tests", "os_test_files", os_type, feature)
    tmpl_path = os.path.join(os.getcwd(), "feature_templates", feature)

    # Dependant on the flag run the relevant function
    if args["create_feature"] is not None:
        create_feature_dir(feature, subfeat, test_path, tmpl_path)
    elif args["create_commands"] is not None:
        create_commands(os_type, feature, test_path, tmpl_path)
    elif args["discovery"] is not None:
        host_or_file = args["discovery"][2]
        generate_cmd_data(os_type, feature, subfeat, test_path, host_or_file)
    elif args["create_val_file"] is not None:
        create_val_file(os_type, feature, test_path)
    elif args["format_actual_state"] is not None:
        format_actual_state(os_type, feature, test_path)
    elif args["create_desired_state"] is not None:
        create_desired_state(os_type, feature, test_path, tmpl_path)
    else:
        msg = "At least one of the arguments '-cf', '-as' or '-ds' is required"
        raise Exception(msg)


if __name__ == "__main__":
    main()
