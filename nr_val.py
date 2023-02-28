from typing import Any, Dict, List
import logging
import argparse
import yaml
from collections import defaultdict
import os
import json
import re
import ast
from glob import glob
import importlib

from nornir import InitNornir
from nornir.core.task import Task, Result
from nornir_jinja2.plugins.tasks import template_file
from nornir_utils.plugins.tasks.data import load_yaml
from nornir_netmiko.tasks import netmiko_send_command
from nornir_rich.functions import print_result

from compliance_report import generate_validate_report

# ----------------------------------------------------------------------------
# Manually defined variables and user input
# ----------------------------------------------------------------------------
# Name of the input variable file (needs its full path)
INPUT_DATA = "input_data.yml"
# Enter a directory location to save compliance report to file
REPORT_DIRECTORY = None
# REPORT_DIRECTORY = "/Users/user1/Documents/Coding/Nornir/code/nornir_validate"
# REPORT_DIRECTORY = "C:\\scripts\\nornir_checks\\nornir_validate\\reports"


# ----------------------------------------------------------------------------
# Gather input Arguments
# ----------------------------------------------------------------------------
def _create_parser() -> Dict[str, Any]:
    """
    Creates a parser object, adds arguments to the parser object, and returns the arguments as a dictionary

    :return: A dictionary of the command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--directory",
        default=REPORT_DIRECTORY,
        help="Directory where to save the compliance report",
    )
    parser.add_argument(
        "-f",
        "--filename",
        default=INPUT_DATA,
        help="Name (with full path) of the input Yaml file of validation variables",
    )
    return vars(parser.parse_args())


# ----------------------------------------------------------------------------
# IMPORT: Import all the actual_state modules required based on validation input data
# ----------------------------------------------------------------------------
def import_actual_state_modules(input_data: str) -> None:
    """
    It imports the actual_state.py modules for all the features used in the validation input file

    :param input_data: The path to the validation input file or the validation input file itself
    :type input_data: str
    """
    # Load the validation input file (dont need to serialise yaml as just searching it)
    if ".yml" in input_data:
        with open(input_data) as f:
            validations = f.read()
    else:
        validations = str(input_data)

    # Gather the path of the actual_state.py modules for all validation features used
    actual_state_modules = {}
    all_features = glob("feature_templates/*/*.py")
    if len(all_features) != 0:
        for each_feature in all_features:
            if each_feature.split(os.sep)[1] in validations:
                each_module = ".".join(each_feature.split(os.sep)).replace(".py", "")
                actual_state_modules[each_feature.split(os.sep)[1]] = each_module
    # Import the actual_state.py modules with an alias of the feature name
    for name, each_module in actual_state_modules.items():
        globals()[f"{name}"] = importlib.import_module(each_module)


# ----------------------------------------------------------------------------
# LOAD: Loads input (validation) data file
# ----------------------------------------------------------------------------
def task_load_input_data(task: Task, input_data: str) -> Dict[str, Any]:
    """
    It loads the input data for the task

    :param task: The task object that is passed to the task function
    :type task: Task
    :param input_data: The path to the input data file
    :type input_data: str
    :return: A dictionary of validations.
    """
    if ".yml" in input_data:
        validations = task.run(
            task=load_yaml, file=input_data, severity_level=logging.DEBUG
        ).result
    else:
        validations = input_data
    return validations


# ----------------------------------------------------------------------------
# CRUNCH: Combines features, sub-features and feature_path into a structured dictionary
# ----------------------------------------------------------------------------
def return_feature_desired_data(validations: str) -> Dict[str, Any]:
    """
    > This function takes a dictionary of validations and returns a dictionary of desired state data

    :param validations: This is the dictionary that contains the validations that you want to run
    :type validations: str
    :return: A dictionary with the feature name as the key and a dictionary as the value.
    """
    feat_desired_data = defaultdict(dict)
    for feature, sub_feature in validations.items():
        feat_desired_data[feature]["file"] = f"{feature}_desired_state.j2"
        feat_desired_data[feature]["sub_features"] = {}
        feat_desired_data[feature]["sub_features"].update(sub_feature)
    return feat_desired_data


# ----------------------------------------------------------------------------
#  CRUNCH: Convert Jinja string into yaml and list of dicts [cmd: {seq: ket:val}] into a dict of cmds {cmd: {seq: key:val}}
# ----------------------------------------------------------------------------
def return_yaml_desired_state(str_desired_state: str) -> Dict[str, Dict]:
    """
    > The function takes a string of YAML and returns a dictionary of the desired state

    :param str_desired_state: The string representation of the desired state
    :type str_desired_state: str
    :return: A dictionary of the desired state
    """
    # Conditional fix as yaml.Loader causes error for ">dd" as swaps a digit for a space
    if re.search(r":\ >\d+", str_desired_state):
        x = yaml.load(str_desired_state.replace(">", "->"), Loader=yaml.Loader)
        desired_state = ast.literal_eval(str(x[0]).replace("->", ">"))
    else:
        desired_state = yaml.load(str_desired_state, Loader=yaml.Loader)[0]
    return desired_state


# ----------------------------------------------------------------------------
#  STRIP: Removes any features, sub-features or commands with a value of None from desired state to safeguard against errors
# ----------------------------------------------------------------------------
def strip_empty_feat(desired_state: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    > Remove any features that dont hold any sub features (not a dictionary) and remove any sub-features
    that dont hold any commands (not a dictionary) and delete any commands that a have a desired state
    of None

    :param desired_state: This is the desired state of the device. It's a dictionary that contains the
    feature, sub-feature, and command
    :type desired_state: Dict[str, Dict]
    :return: A dictionary of dictionaries.
    """
    # Remove any features that dont hold any sub features (not a dictionary)
    desired_state = {k: v for k, v in desired_state.items() if isinstance(v, dict)}
    # Remove any sub-features that dont hold any commands (not a dictionary)
    tmp_ds = {}
    for feat, sub_feat in desired_state.items():
        tmp_ds[feat] = {k: v for k, v in sub_feat.items() if isinstance(v, dict)}
    # Delete any commands that a have a desired state of None
    clean_desired_state = defaultdict(dict)
    for feat, sub_feat in tmp_ds.items():
        for sub_feat_name, cmds in sub_feat.items():
            tmp_cmd = {}
            for each_cmd, cmd_ds in cmds.items():
                if cmd_ds != None and cmd_ds != "None":
                    tmp_cmd[each_cmd] = cmd_ds
            if len(tmp_cmd) != 0:
                clean_desired_state[feat][sub_feat_name] = tmp_cmd

    return dict(clean_desired_state)


# ----------------------------------------------------------------------------
#  REMOVE: Removes commands from the desired state sub-features
# ----------------------------------------------------------------------------
def remove_cmds_desired_state(desired_state: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    > It takes a dictionary of dictionaries and returns a dictionary of dictionaries
    with all sub_feature commands removed

    :param desired_state: The desired state of the device
    :type desired_state: Dict[str, Dict]
    :return: A dictionary of dictionaries.
    """
    clean_desired_state = defaultdict(dict)
    for feature, sub_feature in desired_state.items():
        for sub_feat_name, sub_feat_cmds in sub_feature.items():
            clean_desired_state[feature][sub_feat_name] = {}
            for cmd_ds in sub_feat_cmds.values():
                if cmd_ds == "SUB_FEATURE_COMBINED_CMD":
                    pass
                elif isinstance(cmd_ds, dict):
                    clean_desired_state[feature][sub_feat_name].update(cmd_ds)
                else:
                    clean_desired_state[feature][sub_feat_name] = cmd_ds
    return dict(clean_desired_state)


# ----------------------------------------------------------------------------
#  OS_TYPE: Gets os_type from host_var OS types (platform) and then removes duplicates and None
# ----------------------------------------------------------------------------
def merge_os_types(host: "Host") -> List:
    """
    > This function takes a nornir host object and returns a list of the OS types for that host

    :param host: "Host" = The host object that is being processed
    :type host: "Host"
    :return: A list of the OS types for the host.
    """
    tmp_os_type: List = []
    tmp_os_type.append(host.platform)
    tmp_os_type.append(host.get_connection_parameters("scrapli").platform)
    tmp_os_type.append(host.get_connection_parameters("netmiko").platform)
    tmp_os_type.append(host.get_connection_parameters("napalm").platform)
    set_os_type = set(tmp_os_type)
    os_type = list(set_os_type)
    os_type.remove(None)
    os_type.sort()
    return os_type


# ----------------------------------------------------------------------------
# 1. DESIRED_STATE: Create a host_var of desired state by running (per-os-type) task_template
# ----------------------------------------------------------------------------
def task_desired_state(
    task: Task, validations: Dict[str, Any], task_template: str
) -> None:
    """
    > The function takes the task, validations and task_template as arguments and returns a host_var of
    combined desired states or exits if nothing to be validated

    :param task: The task object
    :type task: Task
    :param validations: This is the dictionary of validations that we created in the previous step
    :type validations: Dict[str, Any]
    :param task_template: This is the name of the template file that will be used to generate the
    desired_state
    :type task_template: str
    :return: A dictionary of the desired state for the host
    """
    desired_state: Dict[str, Any] = {}
    # 1a. TMPL: Create the desired_state for each feature to be validated (double 'if' to stop error if top level dict not exist)
    if validations.get("hosts") != None:
        if validations["hosts"].get(str(task.host)) != None:
            task.run(
                task=task_template,
                tmpl_path="feature_templates/",
                validations=validations["hosts"][str(task.host)],
                desired_state=desired_state,
            )
    if validations.get("groups") != None:
        if validations["groups"].get(str(task.host.groups[0])) != None:
            task.run(
                task=task_template,
                tmpl_path="feature_templates/",
                validations=validations["groups"][str(task.host.groups[0])],
                desired_state=desired_state,
            )
    if validations.get("all") != None:
        task.run(
            task=task_template,
            tmpl_path="feature_templates/",
            validations=validations["all"],
            desired_state=desired_state,
        )

    # 1b. VAR: Create host_var of combined desired states or exits if nothing to be validated
    if len(desired_state) == 0:
        result_text = "\u26A0\uFE0F  No validations were performed as no desired_state was generated, check input file and template"
        return Result(host=task.host, failed=True, result=result_text)
    else:
        task.host["desired_state"] = strip_empty_feat(desired_state)


# ----------------------------------------------------------------------------
# 2. TEMPLATE: Nornir template task called by task_desired_state to create desired state YML from template and serializes it
# ----------------------------------------------------------------------------
def task_template(
    task: Task, tmpl_path: str, validations: str, desired_state: Dict[str, Any]
) -> str:
    """
    > The function takes a task, a template path, a list of validations and a dictionary of desired
    state. Uses nornir-jinja to create a dictionary of desired state from the jinja2 templates

    :param task: The task object that is passed to the plugin
    :type task: Task
    :param tmpl_path: The path to the templates
    :type tmpl_path: str
    :param validations: A string of the validations to be run
    :type validations: str
    :param desired_state: This is the dictionary that will be used to compare the current state of the
    device with the desired state
    :type desired_state: Dict[str, Any]
    """
    # 2a. CRUNCH: Formulate data to be used in templates to create desired state
    os_type = merge_os_types(task.host)
    feat_desired_data = return_feature_desired_data(validations)

    # 2b. TMPL: Create the desired state from the jinja2 template
    for feature, values in feat_desired_data.items():
        str_desired_state = task.run(
            task=template_file,
            template=values["file"],
            path=os.path.join(tmpl_path, feature),
            os_type=os_type,
            feature=feature,
            sub_features=values["sub_features"],
        ).result
        # 2c. SERIALISE: Convert Jinja string into yaml and list of dicts [cmd: {seq: ket:val}] into a dict of cmds {cmd: {seq: key:val}}
        desired_state.update(return_yaml_desired_state(str_desired_state))


# ----------------------------------------------------------------------------
# 3. ACTUAL_STATE: Creates actual state by formatting cmd outputs
# ----------------------------------------------------------------------------
def actual_state_engine(
    os_type: List, feat_actual_data: Dict[str, List]
) -> Dict[str, Dict]:
    """
    It takes a list of OS types and a dictionary of features and sub-features and formatting the cmd output
    to return actual state as a dictionary of features and sub-features with the output of the sub-features formatted

    :param os_type: List
    :type os_type: List
    :param feat_actual_data: This is the output of the actual_state_engine function
    :type feat_actual_data: Dict[str, List]
    :return: A dictionary of dictionaries.
    """
    actual_state: Dict[str, Any] = defaultdict(dict)

    for feature, sub_feat_dict in feat_actual_data.items():
        for sub_feature, output in sub_feat_dict.items():
            tmp_dict = defaultdict(dict)
            # EMPTY: If output is empty just adds an empty dictionary
            if output == None or len(output) == 0:
                result = tmp_dict
            else:
                result = eval(feature).format_output(
                    str(os_type), sub_feature, output, tmp_dict
                )
            actual_state[feature][sub_feature] = result
    return dict(actual_state)


# ----------------------------------------------------------------------------
# 4. ENGINE: Formats gathered output as actual state and runs compliance report - Only one that prints (logging debug)
# ----------------------------------------------------------------------------
def task_engine(
    task: Task, input_data: str = INPUT_DATA, directory: str = REPORT_DIRECTORY
) -> str:
    """
    Engine that runs all nornir and non-nornir (formatting) tasks

    :param task: The task object that is passed to the task engine
    :type task: Task
    :param input_data: The input data file that contains the desired state of the device
    :type input_data: str
    :param directory: The directory where the compliance report will be saved
    :type directory: str
    :return: The result of the task_engine function is a Result object.
    """
    # 4a, Import the actual state modulues
    import_actual_state_modules(input_data)
    # 4b. Load the input file of validations
    validations = task_load_input_data(task, input_data)

    # 4c. TMPL: Creates desired states using the jinja template by calling task_desired_state (1) which in term calls task)template (2)
    task.run(
        task=task_desired_state,
        validations=validations,
        task_template=task_template,
        severity_level=logging.DEBUG,
    )

    # 4d. CMD: Using commands crunched from the desired output gathers pre-feature/sub-feature actual config of the device
    feat_actual_data = defaultdict(dict)
    for feature, sub_feature in task.host["desired_state"].items():
        for sub_feat_name, sub_feat_cmds in sub_feature.items():
            cmd_output = []
            for cmd in sub_feat_cmds.keys():
                tmp_cmd_output = task.run(
                    task=netmiko_send_command,
                    command_string=cmd,
                    use_textfsm=True,
                    severity_level=logging.DEBUG,
                ).result
                # Converts NXOS "| json" cmds from string to JSON
                if "json" in cmd:
                    tmp_cmd_output = [json.loads(tmp_cmd_output)]
                # Required for non-formatted data (no NTC template)
                elif isinstance(tmp_cmd_output, str):
                    tmp_cmd_output = tmp_cmd_output.lstrip().rstrip().splitlines()
                cmd_output.extend(tmp_cmd_output)
            feat_actual_data[feature][sub_feat_name] = cmd_output

    # 4e. ACTUAL: Formats the returned data into dict of cmds {cmd: {seq: key:val}} same as desired_state
    os_type = merge_os_types(task.host)
    actual_state = actual_state_engine(os_type, feat_actual_data)

    # 4f. VAL: Uses Napalm_validate validate method to generate a compliance report
    desired_state = remove_cmds_desired_state(task.host["desired_state"])

    comp_result = generate_validate_report(
        desired_state, actual_state, str(task.host), directory
    )
    # 4g. RSLT: Nornir returns compliance result or if fails the compliance report
    return Result(
        host=task.host,
        failed=comp_result["failed"],
        result=comp_result["result"],
        report=comp_result["report"],
        report_text=comp_result["report_text"],
    )


# ----------------------------------------------------------------------------
# MAIN: Runs the script
# ----------------------------------------------------------------------------
def main():
    args = _create_parser()
    nr = InitNornir(config_file="config.yml")
    result = nr.run(
        task=task_engine, input_data=args["filename"], directory=args["directory"]
    )
    print_result(result, vars=["result", "report_text"])


if __name__ == "__main__":
    main()
