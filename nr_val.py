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
from nornir_utils.plugins.tasks.files import write_file
from nornir_netmiko.tasks import netmiko_send_command
from nornir_rich.functions import print_result

from compliance_report import generate_validate_report

# ----------------------------------------------------------------------------
# Manually defined variables and user input
# ----------------------------------------------------------------------------
# Default directory location to look for validation files and save compliance report and/or generated validation files
# DATA_DIRECTORY = os.getcwd()
DATA_DIRECTORY = (
    "/Users/mucholoco/Documents/Coding/Nornir/code/nornir_validate/hme_val_files"
)
# Device error messages used by validation generator to stop failures if a feature is not supported
ERR_MSG = [
    "is not enabled",
    "ERROR:",
    "INFO:",
    "No sessions to display.",
    "Incorrect usage",
]


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
        "-g",
        "--generate_val_file",
        action="store_true",
        help="Generate the validation file from device output",
    )
    parser.add_argument(
        "-s",
        "--save_to_file",
        action="store_true",
        help="Save the compliance report to file in the specified directory",
    )
    parser.add_argument(
        "-d",
        "--directory",
        default=DATA_DIRECTORY,
        help="Directory to look for validation files and/or to save the compliance reports",
    )
    args = parser.parse_known_args()
    return args


# ----------------------------------------------------------------------------
# INPUT_DATA: Checking data directory/input data file exists and the formatting/merging of multiple files
# ----------------------------------------------------------------------------
def check_file_exist(input_file: str, directory: str) -> str:
    """
    > If the input file doesn't exist in the current directory, check if it exists in the default data
    directory. If it doesn't exist in either location returned error message is not None

    :param input_file: The file you want to check if it exists
    :type input_file: str
    :param directory: The directory where the data files are stored
    :type directory: str
    :return: The input file if it exists, or the input file in the data directory if it exists, or an
    error message if it doesn't exist.
    """
    if os.path.isfile(input_file) == True:
        return input_file
    elif os.path.isfile(input_file) == False:
        err_msg = f"❌ The input file doesn't exist:\n - {input_file}"
        data_input_file = os.path.join(directory, input_file)
        if data_input_file != input_file:
            if os.path.isfile(os.path.join(directory, data_input_file)) == True:
                return data_input_file
            else:
                err_msg = f"❌ The input file doesn't exist:\n - {input_file}\n - {data_input_file}"
    if err_msg != None:
        print(err_msg)
        exit()


def merge_feat_subfeat(input_file: Dict[str, Any], tmp_file: Dict[str, Any]) -> None:
    """
    Merge the feature and subfeature dictionaries into one dictionary

    :param input_file: A dictionary containing the following keys:
    :type input_file: Dict[str, Any]
    :param tmp_file: The temporary file that contains the features and subfeatures
    :type tmp_file: Dict[str, Any]
    """
    for feat in tmp_file.keys():
        # FEAT: If feature doesn't exist add it
        if input_file.get(feat) == None:
            input_file[feat] = tmp_file[feat]
        elif input_file.get(feat):
            for subfeat in tmp_file[feat].keys():
                # SUBFEAT: If feature exist but sub feature not add the subfeat
                if input_file[feat].get(subfeat) == None:
                    input_file[feat][subfeat] = tmp_file[feat][subfeat]
                # MERGE: If feature and sub feature exist but not same merge them
                elif input_file[feat].get(subfeat):
                    if input_file[feat][subfeat] == tmp_file[feat][subfeat]:
                        pass
                    else:
                        input_file[feat][subfeat].update(tmp_file[feat][subfeat])


def merge_val_input_files(directory: str) -> Dict[str, Any]:
    """
    It takes all the .yml files in the data directory and merges the all, groups and hosts
    dictionaries into the one file of all validations

    :return: None
    """
    input_file = dict(all={}, groups={}, hosts={})
    all_files = glob(f"{directory}/*.yml")
    if len(all_files) == 0:
        print(f"❌ There are no .yml validation files in {directory}")
        exit()
    for each_file in all_files:
        with open(each_file) as input_data:
            input_data = yaml.load(input_data, Loader=yaml.FullLoader)
            if input_data.get("all"):
                merge_feat_subfeat(input_file["all"], input_data["all"])
            if input_data.get("hosts") != None:
                for grp in input_data["hosts"].keys():
                    if input_file["hosts"].get(grp) == None:
                        input_file["hosts"][grp] = input_data["hosts"][grp]
                    else:
                        merge_feat_subfeat(
                            input_file["hosts"][grp], input_data["hosts"][grp]
                        )
            if input_data.get("groups") != None:
                for grp in input_data["groups"].keys():
                    if input_file["groups"].get(grp) == None:
                        input_file["groups"][grp] = input_data["groups"][grp]
                    else:
                        merge_feat_subfeat(
                            input_file["groups"][grp], input_data["groups"][grp]
                        )
    if (
        len(input_file["all"]) == 0
        and len(input_file["groups"]) == 0
        and len(input_file["hosts"]) == 0
    ):
        print(
            f"❌ None of the validation files in {directory} have all, groups or hosts dictionaries"
        )
        exit()
    else:
        return input_file


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
def return_feature_desired_data(validations: Dict[str, Any]) -> Dict[str, Any]:
    """
    > This function takes a dictionary of validations and returns a dictionary of desired state data

    :param validations: This is the dictionary that contains the validations that you want to run
    :type validations: str
    :return: A dictionary with the feature name as the key and a dictionary as the value.
    """
    feat_desired_data = defaultdict(dict)
    for feature, sub_feature in validations.items():
        feat_desired_data[feature]["file"] = f"{feature}_desired_state.j2"
        if isinstance(sub_feature, list):
            feat_desired_data[feature]["sub_features"] = sub_feature
        else:
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
    if re.search(r" >\d+\n", str_desired_state):
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
    return desired_state


# ----------------------------------------------------------------------------
# 3. ACTUAL_STATE: Creates actual state by formatting cmd outputs
# ----------------------------------------------------------------------------
def actual_state_engine(
    method: str, os_type: List, feat_actual_data: Dict[str, List]
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
                result = getattr(eval(feature), method)(
                    str(os_type), sub_feature, output, tmp_dict
                )
            actual_state[feature][sub_feature] = result
    return dict(actual_state)


# ----------------------------------------------------------------------------
# 4. ENGINE: Formats gathered output as actual state and runs compliance report - Only one that prints (logging debug)
# ----------------------------------------------------------------------------
def task_engine(task: Task, input_data: str, directory: str = None) -> Result:
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
    # 4a, Import the actual state modules and load the input file of validations
    import_actual_state_modules(input_data)
    validations = task_load_input_data(task, input_data)
    # 4b. TMPL: Creates desired states using the jinja template by calling task_desired_state (1) which in term calls task)template (2)
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
    actual_state = actual_state_engine("format_actual_state", os_type, feat_actual_data)

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
# 5. VAL_FILE_BUILDER: Builds validation files based on the actual state
# ----------------------------------------------------------------------------
def val_file_builder(task: Task, input_data: str, directory: str) -> Result:
    """
    It takes indexes of features and based on creates the commands to use to gather the actual state
    of the device from which it then generates the validation file

    :param task: The task object that is passed to the function
    :type task: Task
    :param input_data: This is the input file of vals or the empty string if you want to create a val
    file of all vals
    :type input_data: str
    :return: The result of the task is a Result object.
    """
    # 5a. Load the input file of vals or create val file of all vals, then import the actual state modules
    if len(input_data) == 0:
        all_index_file = os.path.join(
            "example_validations", "subfeature_index_files", "all_subfeat_index.yml"
        )
        with open(all_index_file) as tmp_data:
            validations = yaml.load(tmp_data, Loader=yaml.FullLoader)
            for feat in validations["all"]:
                for idx, sub_feat in enumerate(validations["all"][feat]):
                    if isinstance(sub_feat, dict):
                        validations["all"][feat][idx] = list(sub_feat.keys())[0]
    else:
        validations = task_load_input_data(task, input_data)

    import_actual_state_modules(validations)

    # 5b. TMPL: Creates desired states using the jinja template by calling task_desired_state (1) which in term calls task)template (2)
    task.run(
        task=task_desired_state,
        validations=validations,
        task_template=task_template,
        severity_level=logging.DEBUG,
    )

    # 5c. CMD: Using commands crunched from the desired output gathers pre-feature/sub-feature actual config of the device
    feat_actual_data = defaultdict(dict)
    used_subfeat, not_used_subfeat = ([] for i in range(2))
    for feature, sub_feature in task.host["desired_state"].items():
        for sub_feat_name, sub_feat_cmds in sub_feature.items():
            cmd_output = []
            for cmd in sub_feat_cmds.keys():
                try:
                    tmp_cmd_output = task.run(
                        task=netmiko_send_command,
                        command_string=cmd,
                        use_textfsm=True,
                        severity_level=logging.DEBUG,
                    ).result
                except:
                    tmp_cmd_output = []
                # Catches empty tables as wont be parsed (such as WLC show int grp sum)
                if isinstance(tmp_cmd_output, str) and len(tmp_cmd_output) != 0:
                    if "---------" in tmp_cmd_output.splitlines()[-1]:
                        tmp_cmd_output = []
                # Catches command output errors likely due to trying a command on an os_type that deosnt support that feature
                for err in ERR_MSG:
                    if err in str(tmp_cmd_output):
                        tmp_cmd_output = []
                # Converts NXOS "| json" cmds from string to JSON
                if "json" in cmd:
                    tmp_cmd_output = [json.loads(tmp_cmd_output)]
                # Required for non-formatted data (no NTC template)
                elif isinstance(tmp_cmd_output, str):
                    tmp_cmd_output = tmp_cmd_output.lstrip().rstrip().splitlines()
                cmd_output.extend(tmp_cmd_output)
            if len(tmp_cmd_output) != 0:
                feat_actual_data[feature][sub_feat_name] = cmd_output
                used_subfeat.append(sub_feat_name)
            else:
                not_used_subfeat.append(sub_feat_name)

    #  5d. FORMAT: Format the returned data into dict of cmds {cmd: {seq: key:val}} and save to file
    os_type = merge_os_types(task.host)
    actual_state = actual_state_engine("generate_val_file", os_type, feat_actual_data)
    val_file = os.path.join(directory, f"{str(task.host)}_vals.yml")
    task.run(
        task=write_file,
        filename=val_file,
        content=yaml.dump({"hosts": {str(task.host): actual_state}}, sort_keys=False),
    )
    info = f"✅ Created the validation file '{val_file}'"

    return Result(
        host=task.host,
        result="",
        used_subfeat=used_subfeat,
        not_used_subfeat=not_used_subfeat,
        file_info=info,
    )


# ----------------------------------------------------------------------------
# MAIN: Runs the script
# ----------------------------------------------------------------------------
def main():
    args, input_file = _create_parser()
    args = vars(args)
    nr = InitNornir(config_file="config.yml")
    #  Failfast if input file (full path, DATA_DIRECTORY or specified dir) or DATA_DIRECTORY dont exist
    if os.path.exists(args["directory"]) == False:
        print(f"❌ The directory doesn't exist:\n - {args['directory']}")
    elif len(input_file) >= 1:
        input_file = check_file_exist(input_file[0], args["directory"])
    elif len(input_file) == 0 and args["generate_val_file"] == False:
        input_file = merge_val_input_files(args["directory"])

    # CREATE_VAL_FILE: Runs the validation file generator (method 5)
    if args["generate_val_file"] == True:
        result = nr.run(
            task=val_file_builder,
            input_data=input_file,
            directory=args["directory"],
        )
        # TSHOOT: Unhash to see output of failed netmiko commands
        # print_result(result)
        # RESULT: Print details of which sub-features have/haven't had validations created
        for each_host in nr.inventory.hosts.keys():
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

    # RUN_VALIDATION: Runs the validation creating compliance report (method 4)
    else:
        if args["save_to_file"] == True:
            result = nr.run(
                task=task_engine, input_data=input_file, directory=args["directory"]
            )
        else:
            result = nr.run(task=task_engine, input_data=input_file)
        print_result(result, vars=["result", "report_text"])


if __name__ == "__main__":
    main()
