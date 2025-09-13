import ast
import importlib
import json
import logging
import os
import re
from collections import defaultdict
from glob import glob
from typing import Any, Callable, Optional, Union

import ipdb
import yaml
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.inventory import Host
from nornir.core.task import Result, Task
from nornir_jinja2.plugins.tasks import template_file
from nornir_netmiko.tasks import netmiko_send_command
from nornir_rich.functions import print_result
from nornir_utils.plugins.tasks.files import write_file

from compliance_report import generate_validate_report


# ----------------------------------------------------------------------------
# IMPORT: Import all the actual_state modules required based on validation input data
# ----------------------------------------------------------------------------
def import_actual_state_modules(
    input_data: Union[str, dict[str, Any], set[str]],
) -> None:
    """Imports the actual_state.py modules for all the features used in the validation input file.

    Args:
        input_data (str): File path to the validation input file or the validation input data itself
        directory (str): The path to the data directory where the input file might be located
    """
    # Load the validation input file (dont need to serialize yaml as just searching it)
    if isinstance(input_data, str) and ".yml" in input_data:
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
#  OS_TYPE: Gets os_type from host_var OS types (platform) and then removes duplicates and None
# ----------------------------------------------------------------------------
def merge_os_types(host: Host) -> list[str]:
    """For a Nornir host object gathers the connection handlers name for the different connection plugins.

    Args:
        host (Host): Nornir inventory host object, holds the hosts attributes

    Returns:
        list[str]: List of the connection handlers for the different connection plugins
    """
    tmp_os_type: list[Union[str, None]] = []
    tmp_os_type.append(host.platform)
    tmp_os_type.append(host.get_connection_parameters("scrapli").platform)
    tmp_os_type.append(host.get_connection_parameters("netmiko").platform)
    tmp_os_type.append(host.get_connection_parameters("napalm").platform)
    set_os_type = set(tmp_os_type)
    os_type = [x for x in set_os_type if x is not None]
    os_type.sort()
    return os_type


# ----------------------------------------------------------------------------
# CRUNCH: Combines features, sub-features and template_path into a structured dictionary
# ----------------------------------------------------------------------------
def return_feature_desired_data(validations: dict[str, Any]) -> dict[str, Any]:
    """Reformats validation structure adding sub_features key and name of the jinja template.

    Args:
        validations (dict[str, Any]): The user defined validations that were gathered from the input file

    Returns:
        dict[str, Any]: Dictionary of all the data required for the desired state to be rendered
    """
    feat_desired_data: dict[str, dict[str, Any]] = defaultdict(dict)
    for feature, sub_feature in validations.items():
        feat_desired_data[feature]["file"] = f"{feature}_desired_state.j2"
        if isinstance(sub_feature, list):
            feat_desired_data[feature]["sub_features"] = sub_feature
        else:
            feat_desired_data[feature]["sub_features"] = {}
            feat_desired_data[feature]["sub_features"].update(sub_feature)
    return feat_desired_data


# ----------------------------------------------------------------------------
#  CRUNCH: Converts the yaml formatted string into a dictionary
# ----------------------------------------------------------------------------
def return_yaml_desired_state(str_desired_state: str) -> dict[str, Any]:
    """Takes a string of YAML and returns a dictionary of the desired state.

    Args:
        str_desired_state (str): String representation of the desired state (including cmds)

    Returns:
        dict[str, Any]: A dictionary of the desired state in the format {feat: {subfeat: {cmds: expected_result}
    """
    # Conditional fix as yaml.Loader causes error for the pattern ">dd"
    if re.search(r" >\d+\n", str_desired_state):
        x = yaml.load(str_desired_state.replace(">", "->"), Loader=yaml.Loader)
        desired_state = ast.literal_eval(str(x[0]).replace("->", ">"))
    else:
        desired_state = yaml.load(str_desired_state, Loader=yaml.Loader)[0]
    return dict(desired_state)


# ----------------------------------------------------------------------------
#  CLEAN: Removes any features, sub-features or commands with a value of None
# ----------------------------------------------------------------------------
def strip_empty_feat(desired_state: dict[str, Any]) -> dict[str, Any]:
    """Removes any features, sub-features or commands with a value of None from desired state to safeguard against errors.

    Args:
        desired_state (dict[str, Any]): Desired state in format

    Returns:
        dict[str, Any]: Final desired state
    """
    # Remove any features that dont hold any sub features (not a dictionary)
    desired_state = {k: v for k, v in desired_state.items() if isinstance(v, dict)}
    # Remove any sub-features that dont hold any commands (not a dictionary)
    tmp_ds = {}
    for feat, sub_feat in desired_state.items():
        tmp_ds[feat] = {k: v for k, v in sub_feat.items() if isinstance(v, dict)}
    # Delete any commands that have a desired state of None
    clean_desired_state: dict[str, dict[str, Any]] = defaultdict(dict)
    for feat, sub_feat in tmp_ds.items():
        for sub_feat_name, cmds in sub_feat.items():
            tmp_cmd = {}
            for each_cmd, cmd_ds in cmds.items():
                if cmd_ds is not None and cmd_ds != "None":
                    tmp_cmd[each_cmd] = cmd_ds
            if len(tmp_cmd) != 0:
                clean_desired_state[feat][sub_feat_name] = tmp_cmd
    return dict(clean_desired_state)


# ----------------------------------------------------------------------------
#  REMOVE: Removes commands from the desired state sub-features
# ----------------------------------------------------------------------------
def remove_cmds_desired_state(desired_state: dict[str, Any]) -> dict[str, Any]:
    """Strips the commands out of the desired state dictionaries (no longer needed as gathered actual state).

    Args:
        desired_state (dict[str, Any]): Desired state in format ({feat: {subfeat: {cmd: expected_result})

    Returns:
        dict[str, Any]: Final desired state in the format {feat: {subfeat: expected_result}}
    """
    clean_desired_state: dict[str, dict[str, Any]] = defaultdict(dict)
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
#  VAL_DM: Creates validation data model for all feature/sub-feature validations
# ----------------------------------------------------------------------------
def create_val_dm() -> dict[str, dict[str, list[str]]]:
    """Creates validation data model from all_subfeat_index file.

    Returns:
        dict[str, Any]: Validation DM with any example data (dicts) such as route table VRF names removed
    """
    all_index_file = os.path.join(
        "example_validations", "subfeature_index_files", "all_subfeat_index.yml"
    )
    validations: dict[str, dict[str, list[str]]]
    with open(all_index_file) as tmp_data:
        validations = yaml.load(tmp_data, Loader=yaml.FullLoader)
        for feat in validations["all"]:
            for idx, sub_feat in enumerate(validations["all"][feat]):
                if isinstance(sub_feat, dict):
                    validations["all"][feat][idx] = list(sub_feat.keys())[0]
    return validations


# ----------------------------------------------------------------------------
#  CLEAN: Cleans up non structured text data when auto generating validation files
# ----------------------------------------------------------------------------
def cleanup_output(cmd: str, tmp_cmd_output: Any) -> Any:  # noqa: ANN401
    """Removes errors that occur from empty features, mainly unstructured data (non-ntc templates).

    Args:
        cmd (str): Command that was run to get tmp_cmd_output
        tmp_cmd_output (list[dict[str, Any]]): Command output, had to use type Any due to try/except

    Returns:
        list[dict[str, Any]]: The original or sanitized command output (typing Any for same reason)
    """
    # Converts NXOS "| json" cmds from string to JSON
    if "| json" in cmd:
        tmp_cmd_output = [json.loads(tmp_cmd_output)]
    # Required for non-formatted data (no NTC template)
    if isinstance(tmp_cmd_output, str):
        tmp_cmd_output = (
            tmp_cmd_output.lstrip().rstrip().replace("^\n", "").splitlines()
        )
        # Catches empty tables as wont be parsed (such as WLC show int grp sum)
        if "---------" in str(tmp_cmd_output):
            tmp_cmd_output = []
        # Catches functions not supported (text output error in from cli)
        elif len(tmp_cmd_output) == 1:
            try:
                int(tmp_cmd_output[0])
            except Exception as e:
                # If matched strips these text statements out
                if (
                    tmp_cmd_output[0] == "Number of lines which match regexp = 0"
                    or "Number of lines which match regexp" not in tmp_cmd_output[0]
                ):
                    tmp_cmd_output = []
    return tmp_cmd_output


# ----------------------------------------------------------------------------
# 1. DESIRED_STATE: Create a host_var of desired state by running (per-os-type) task_template
# ----------------------------------------------------------------------------
def task_desired_state(
    task: Task,
    validations: dict[str, Any],
    task_template: Callable[[Task, str, str, dict[str, Any]], str],
) -> Optional[Result]:
    """Uses nornir-template (task_template method) to produce host_var of combined desired states (exits if nothing to be validated).

    Args:
        task (Task): The nornir tasks that implements (runs) this the nornir-jinja template plugin
        validations (dict[str, Any]): The validations to be run (user input validation data)
        task_template (Callable[[Task, str, str, dict[str, Any]], str]): Nornir-jinja plugin task to render the validations

    Returns:
        Optional[Result]: If no validation returns Nornir result stating so (if validations desired_sate added as hosts_vars to task host
    """
    desired_state: dict[str, Any] = {}
    # 1a. TMPL: Create the desired_state for each feature to be validated (double logic to stop error if top level dict not exist)
    if (
        validations.get("hosts") is not None
        and validations["hosts"].get(str(task.host)) is not None
    ):
        task.run(
            task=task_template,
            tmpl_path="feature_templates/",
            validations=validations["hosts"][str(task.host)],
            desired_state=desired_state,
        )
    if (
        validations.get("groups") is not None
        and validations["groups"].get(str(task.host.groups[0])) is not None
    ):
        task.run(
            task=task_template,
            tmpl_path="feature_templates/",
            validations=validations["groups"][str(task.host.groups[0])],
            desired_state=desired_state,
        )
    if validations.get("all") is not None:
        task.run(
            task=task_template,
            tmpl_path="feature_templates/",
            validations=validations["all"],
            desired_state=desired_state,
        )
    # 1b. VAR: Create host_var of combined desired states or exits if nothing to be validated

    if len(desired_state) == 0:
        result_text = "\u26a0\ufe0f  No validations were performed as no desired_state was generated, check input file and template"
        return Result(host=task.host, failed=True, result=result_text)
    else:
        task.host["desired_state"] = strip_empty_feat(desired_state)
        return None  #! hopefully shouldnt break anything, needed to fix linting


# ----------------------------------------------------------------------------
# 2. TEMPLATE: Called by task_desired_state to create the desired state (using jinja)
# ----------------------------------------------------------------------------
def task_template(
    task: Task,
    tmpl_path: str,
    validations: dict[str, Any],
    desired_state: dict[str, Any],
) -> dict[str, Any]:
    """Nornir-jinja task to render the validations into the desired states (also includes cmds to get the actual-state).

    Args:
        task (Task): The nornir tasks that implements (runs) this the nornir-jinja template plugin
        tmpl_path (str): Path to the feature templates
        validations (dict[str, Any]): The validations to be run (user input validation data)
        desired_state (dict[str, Any]): The final desired state in format ({feat: {subfeat: {cmd: expected_result})

    Returns:
        list[str]: _description_

    # :param task: The task object that is passed to the plugin
    # :type task: Task
    """
    # 2a. CRUNCH: Formulate data to be used in templates to create desired state
    os_type = merge_os_types(task.host)
    feat_desired_data = return_feature_desired_data(validations)
    # 2b. TMPL: Create the desired state (includes cmds to get actual state) from the jinja2 template
    for feature, values in feat_desired_data.items():
        str_desired_state: str = task.run(
            task=template_file,
            template=values["file"],
            path=os.path.join(tmpl_path, feature),
            os_type=os_type,
            feature=feature,
            sub_features=values["sub_features"],
        ).result
        # 2c. SERIALISE: Uses YAML to convert the string result into a dictionary ({feat: {subfeat: {cmd: expected_result})
        desired_state.update(return_yaml_desired_state(str_desired_state))

    return desired_state


# ----------------------------------------------------------------------------
# 3. ACTUAL_STATE: Formats cmd outputs to create the actual state
# ----------------------------------------------------------------------------
def actual_state_engine(
    val_file: bool, os_type: list[str], feat_actual_data: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """From the cmd output creates the actual state of features and sub-features with the output of the sub-features formatted.

    Args:
        val_file (bool): True if generate validation file called this function
        os_type (list[str]): Connection handler (plugin) used to format cmd data into actual state structure (same format as desired state)
        feat_actual_data (dict[str, dict[str, Any]]): The structured or non-structured data (cmd output) got from devices

    Returns:
        dict[str, dict[str, Any]]: Actual state formatted as ({feat: {subfeat: actual_result})
    """
    actual_state: dict[str, dict[str, Any]] = defaultdict(dict)
    for feature, sub_feat_dict in feat_actual_data.items():
        for sub_feature, output in sub_feat_dict.items():
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
# 4. ENGINE: Formats gathered output as actual state and runs compliance report - Only one that prints (logging debug)
# ----------------------------------------------------------------------------
def validate(
    task: Task, input_data: dict[str, Any], save_report: Union[str | None] = None
) -> Result:
    """The main engine that runs file formatting, nornir tasks and compliance report.

    Args:
        task (Task): The nornir tasks that implements (runs) this the nornir tasks
        input_data (str): The User defined input data from input file
        save_report (Union[str | None]): To optionally save compliance reports to the directory specified in this variable

    Returns:
        Result: The final result of nornir_validate (all tasks), a special Nornir Result object passed back to the main() method to be printed
    """
    # 4a, Import the actual state modules and load the input file of validations
    import_actual_state_modules(input_data)
    # 4b. TMPL: Creates desired states using the jinja template by calling task_desired_state (1) which in term calls task_template (2)
    task.run(
        task=task_desired_state,
        validations=input_data,
        task_template=task_template,
        severity_level=logging.DEBUG,
    )
    # 4c. CMD: Using commands crunched from the desired output gathers per-feature/sub-feature actual config of the device
    feat_actual_data: dict[str, dict[str, Any]] = defaultdict(dict)
    for feature, sub_feature in task.host["desired_state"].items():
        for sub_feat_name, sub_feat_cmds in sub_feature.items():
            cmd_output = []
            for cmd in sub_feat_cmds.keys():  # noqa: SIM118
                tmp_cmd_output = task.run(
                    task=netmiko_send_command,
                    command_string=cmd,
                    use_textfsm=True,
                    severity_level=logging.DEBUG,
                ).result
                # Converts NXOS "| json" cmds from string to JSON
                if "json" in cmd:
                    tmp_cmd_output = [json.loads(tmp_cmd_output)]
                # Required for non-structured data(no NTC template)
                elif isinstance(tmp_cmd_output, str):
                    tmp_cmd_output = tmp_cmd_output.lstrip().rstrip().splitlines()
                cmd_output.extend(tmp_cmd_output)
            feat_actual_data[feature][sub_feat_name] = cmd_output

    # 4d. ACTUAL: Formats the returned data into dict of cmds {cmd: {seq: key:val}} same as desired_state
    os_type = merge_os_types(task.host)
    actual_state = actual_state_engine(False, os_type, feat_actual_data)
    # 4e. VAL: Uses Napalm_validate validate method to generate a compliance report
    desired_state = remove_cmds_desired_state(task.host["desired_state"])
    comp_result = generate_validate_report(
        desired_state, actual_state, str(task.host), save_report
    )
    # 4f. RSLT: Nornir returns compliance result or if fails the compliance report
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
def val_file_builder(
    task: Task, input_data: Union[dict[str, Any], str] = "", directory: str = ""
) -> Result:
    """Generates a validation file based on what features are enabled on a device (gathered from actual state).

    Args:
        task (Task): The Nornir task that executes host actions and stores the results
        input_data (Union[dict[str, Any], str]): Validations or if an empty string if dynamically creating a validation file
        directory (str): Working directory where the file will be saved

    Returns:
        Result: The nornir result from the execution of the task, so list of enabled and not enabled features as well as val file name
    """
    # 5a. Use input input validation DM or if empty create one of all the possible validations
    validations = create_val_dm() if len(input_data) == 0 else input_data
    import_actual_state_modules(validations)
    # 5b. TMPL: Creates desired states using the jinja template by calling task_desired_state (1) which in term calls task)template (2)
    task.run(
        task=task_desired_state,
        validations=validations,
        task_template=task_template,
        severity_level=logging.DEBUG,
    )
    # 5c. CMD: Using commands crunched from the desired output gathers pre-feature/sub-feature actual config of the device
    feat_actual_data: dict[str, dict[str, Any]] = defaultdict(dict)
    used_subfeat, not_used_subfeat = ([] for i in range(2))
    for feature, sub_feature in task.host["desired_state"].items():
        for sub_feat_name, sub_feat_cmds in sub_feature.items():
            cmd_output = []
            for cmd in sub_feat_cmds.keys():  # noqa: SIM118
                try:
                    tmp_cmd_output = task.run(
                        task=netmiko_send_command,
                        command_string=cmd,
                        use_textfsm=True,
                        severity_level=logging.DEBUG,
                    ).result
                except NornirSubTaskError:
                    tmp_cmd_output = []
                # Cleans up non-formatted data (no NTC template)
                tmp_cmd_output = cleanup_output(cmd, tmp_cmd_output)
                cmd_output.extend(tmp_cmd_output)
            if len(tmp_cmd_output) != 0:
                feat_actual_data[feature][sub_feat_name] = cmd_output
                used_subfeat.append(sub_feat_name)
            else:
                not_used_subfeat.append(sub_feat_name)

    #  5d. FORMAT: Format the returned data into dict of cmds {cmd: {seq: key:val}} and save to file
    os_type = merge_os_types(task.host)
    actual_state = actual_state_engine(True, os_type, feat_actual_data)
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
