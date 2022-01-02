from typing import Any, Dict, List
import argparse
import os
import logging
import sys
import yaml
import inspect
from collections import defaultdict
import ipdb

from nornir import InitNornir
from nornir.core.task import Task, Result
from nornir_utils.plugins.tasks.data import load_yaml, load_json, echo_data
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_title, print_result
from nornir_jinja2.plugins.tasks import template_file

# Programmatically update syspath so imports work when script run from diff locations
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from nr_val import input_task
from nr_val import merge_os_types
from compliance_report import report
from actual_state import format_actual_state

# ----------------------------------------------------------------------------
# Manually defined variables
# ----------------------------------------------------------------------------
input_data = "input_data.yml"  # Name of the input variable file
desired_state = "desired_state.yml"  # Name of the static desired_state file
desired_state_tmpl = "desired_state.j2"  # Name of the desired_state template
actual_state = "actual_state.json"  # Name of the static actual_state file
actual_state_tmpl = "actual_state.py"  # Name of actual_state python logic file

# ----------------------------------------------------------------------------
# Flags to define what is run, none take any values
# ----------------------------------------------------------------------------
def _create_parser() -> Dict[str, Any]:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-di",
        "--discovery",
        action="store_true",
        help="Runs the desired_state command on a device printing raw output",
    )
    parser.add_argument(
        "-as",
        "--actual_state",
        action="store_true",
        help="Runs the desired_state commands creating the actual state",
    )
    parser.add_argument(
        "-ds",
        "--desired_state",
        action="store_true",
        help="Renders the contents of desired_state.j2",
    )
    parser.add_argument(
        "-rds",
        "--report_desired_state",
        action="store_true",
        help="Builds compliance report using using static actual_state.json file and dynamically created desired_state",
    )
    parser.add_argument(
        "-ras",
        "--report_actual_state",
        action="store_true",
        help="Builds compliance report using using static desired_state.yml file and dynamically created actual_state",
    )
    return vars(parser.parse_args())


# ----------------------------------------------------------------------------
# 1. Validates existence of test files
# ----------------------------------------------------------------------------
##### !!!! Still to do !!!!!!
def _check_feature_exist(input_data, desired_state_tmpl):
    with open(input_data, "r") as file_:
        input_data = yaml.load(file_, Loader=yaml.SafeLoader)
    with open(desired_state_tmpl) as file_:
        desired_state_tmpl = file_.read()

    # Go through and get contents of all, host and groups
    # Check if dict name is in the template, if not fail
    # ipdb.set_trace()


def _file_validation(
    input_data: str,
    desired_state: str,
    desired_state_tmpl: str,
    actual_state: str,
) -> Dict[str, Any]:
    errors = []

    for each_file in [
        input_data,
        desired_state,
        desired_state_tmpl,
        actual_state,
        actual_state_tmpl,
    ]:
        if os.path.exists(each_file) == False:
            errors.append(each_file)
    if len(errors) != 0:
        print(
            "❌ FileError: The following files are missing, all are required (even if empty) to run the Validation Builder."
        )
        for each_err in errors:
            print(f"    -{each_err}")
        sys.exit(1)

    elif len(errors) == 0:
        _check_feature_exist(input_data, desired_state_tmpl)
        return dict(
            input_data=input_data,
            desired_state=desired_state,
            desired_state_tmpl=desired_state_tmpl,
            actual_state=actual_state,
            actual_state_tmpl=actual_state_tmpl,
        )


# ----------------------------------------------------------------------------
# 2. Class of all validation builder methods
# ----------------------------------------------------------------------------
class ValidationBuilder:
    def __init__(self, args: Dict[str, bool], files: Dict[str, Any]) -> None:
        self.discovery = args["discovery"]
        self.desired_state = args["desired_state"]
        self.actual_state = args["actual_state"]
        self.report_desired_state = args["report_desired_state"]
        self.report_actual_state = args["report_actual_state"]
        self.input_data = files["input_data"]
        self.desired_state_file = files["desired_state"]
        self.desired_state_tmpl = files["desired_state_tmpl"]
        self.actual_state_file = files["actual_state"]
        self.report_task_desired_state = {}

    # ----------------------------------------------------------------------------
    # 2a. ENGINE: Runs tasks dependant on flags specified at runtime
    # ----------------------------------------------------------------------------
    def engine(self) -> Result:
        nr = InitNornir(
            inventory={
                "plugin": "SimpleInventory",
                "options": {
                    "host_file": os.path.join(parentdir, "inventory/hosts.yml"),
                    "group_file": os.path.join(parentdir, "inventory/groups.yml"),
                    "defaults_file": os.path.join(parentdir, "inventory/defaults.yml"),
                },
            }
        )

        if self.discovery == True:
            print_title("Validation Builder - Discovery")
            return nr.run(task=self.discovery_task)
        elif self.actual_state == True:
            print_title("Validation Builder - Actual State")
            return nr.run(task=self.actual_state_task)
        elif self.desired_state == True:
            print_title("Validation Builder - Desired State")
            return nr.run(task=self.desired_state_task)
        elif self.report_desired_state == True:
            print_title(
                "Validation Builder - Compliance Report using dynamic desired_state and static actual_state"
            )
            return nr.run(task=self.report_desired_state_task)
        elif self.report_actual_state == True:
            print_title(
                "Validation Builder - Compliance Report using dynamic actual_state and static desired_state"
            )
            return nr.run(task=self.report_actual_state_task)
        else:
            print_title("Validation Builder - Compliance Report")
            return nr.run(task=self.report_task)

    # ----------------------------------------------------------------------------
    # 2b. TEMPLATE: Renders the template and prints result to screen (used by desired_state_task)
    # ----------------------------------------------------------------------------
    def template_task(
        self, task: Task, tmpl_path: str, input_vars: str, desired_state: Dict[str, Any]
    ) -> None:
        # Required so doesn't print if running full report
        if self.desired_state == True:
            sev_level = logging.INFO
        else:
            sev_level = logging.DEBUG
        # YAML has to be printed for each task to keep proper formatting
        os_type = merge_os_types(task.host)

        for val_feature, feature_vars in input_vars.items():
            tmp_desired_state = task.run(
                name="template in YAML",
                task=template_file,
                path="",
                template=desired_state_tmpl,
                os_type=os_type,
                feature=val_feature,
                input_vars=feature_vars,
                severity_level=sev_level,
            ).result

            # Converts jinja string into yaml and list of dicts [cmd: {seq: ket:val}] into a dict of cmds {cmd: {seq: key:val}}
            for each_list in yaml.load(tmp_desired_state, Loader=yaml.SafeLoader):
                desired_state.update(each_list)

    # ----------------------------------------------------------------------------
    # 2c. ACTUAL_STATE: Creates actual state by formatting cmd outputs
    # ----------------------------------------------------------------------------
    def actual_state_engine(
        self, os_type: List, cmd_output: Dict[str, List]
    ) -> Dict[str, Dict]:
        actual_state: Dict[str, Any] = {}

        # Loops through getting command and output from the command
        for cmd, output in cmd_output.items():
            tmp_dict = defaultdict(dict)
            if output == None:
                actual_state[cmd] = tmp_dict
            else:
                format_actual_state(os_type, cmd, output, tmp_dict, actual_state)
        return actual_state

    # ----------------------------------------------------------------------------
    # 2d. DISCOVERY - Runs the desired_state commands on a device and prints the textFSM raw output
    # ----------------------------------------------------------------------------
    def discovery_task(self, task: Task) -> Result:
        result: Dict[str, Any] = {}
        # If it is the full report uses dynamic uses cmds from dynamic (desired_state_tmpl) rather than static desired_state
        if len(self.report_task_desired_state) != 0:
            all_cmds = self.report_task_desired_state
        # If not full report load input_vars and store them in a dict {cmd: {desired_state}, cmd: {desired_state}}
        if len(self.report_task_desired_state) == 0:
            list_of_cmds = task.run(
                task=load_yaml,
                file=self.desired_state_file,
                severity_level=logging.DEBUG,
            ).result
            all_cmds = {k: v for element in list_of_cmds for k, v in element.items()}
        # Get output of each command
        for each_cmd in all_cmds:
            result[each_cmd] = task.run(
                task=netmiko_send_command,
                command_string=each_cmd,
                use_textfsm=True,
                severity_level=logging.DEBUG,
            ).result
        return Result(host=task.host, result=result)

    # ----------------------------------------------------------------------------
    # 2e. ACTUAL - Runs the desired_state commands creating the formated actual_state and printing to screen
    # ----------------------------------------------------------------------------
    def actual_state_task(self, task: Task) -> Result:
        cmd_output = task.run(
            task=self.discovery_task, severity_level=logging.DEBUG
        ).result
        os_type = merge_os_types(task.host)
        actual_state = self.actual_state_engine(os_type, cmd_output)
        return Result(host=task.host, result=actual_state)

    # ----------------------------------------------------------------------------
    # 2f. DESIRED - Renders the contents of desired_state.j2 and prints to screen
    # ----------------------------------------------------------------------------
    def desired_state_task(self, task: Task) -> Result:
        task.run(
            task=input_task,
            input_data=self.input_data,
            template_task=self.template_task,
            severity_level=logging.DEBUG,
        )
        # JSON can be printed for all tasks (commands) in one go as keeps proper formatting
        task.run(
            name="template in JSON",
            task=echo_data,
            result=task.host["desired_state"],
            severity_level=logging.INFO,
        )

    # ----------------------------------------------------------------------------
    # 2g. REPORT_DESIRED: Report from dynamically built desired_state and static actual_state
    # ----------------------------------------------------------------------------
    def report_desired_state_task(self, task: Task) -> Result:
        # Dynamically get the desired state
        task.run(
            task=input_task,
            input_data=self.input_data,
            template_task=self.template_task,
            severity_level=logging.DEBUG,
        )
        # Static file of actual state
        actual_state = task.run(
            task=load_json, file=self.actual_state_file, severity_level=logging.DEBUG
        ).result
        # Generate report
        comp_result = report(
            task.host["desired_state"], actual_state, str(task.host), None
        )
        return Result(
            host=task.host, failed=comp_result["failed"], result=comp_result["report"]
        )

    # ----------------------------------------------------------------------------
    # 2h. REPORT_ACTUAL: Report from dynamically built actual_state and static desired_state
    # ----------------------------------------------------------------------------
    def report_actual_state_task(self, task: Task) -> Result:
        # Dynamically get the actual state
        actual_state = task.run(
            task=self.actual_state_task, severity_level=logging.DEBUG
        ).result
        # Static file of desired state
        tmp_desired_state = task.run(
            task=load_yaml, file=self.desired_state_file, severity_level=logging.DEBUG
        ).result
        desired_state = {}
        for each_list in tmp_desired_state:
            desired_state.update(each_list)
        # Generate report
        comp_result = report(desired_state, actual_state, str(task.host), None)
        return Result(
            host=task.host, failed=comp_result["failed"], result=comp_result["report"]
        )

    # ----------------------------------------------------------------------------
    # 2i. REPORT - Builds compliance report
    # ----------------------------------------------------------------------------
    def report_task(self, task: Task) -> Result:
        task.run(
            task=input_task,
            input_data=self.input_data,
            template_task=self.template_task,
            severity_level=logging.DEBUG,
        )
        self.report_task_desired_state = task.host["desired_state"]
        actual_state = task.run(
            task=self.actual_state_task, severity_level=logging.DEBUG
        ).result
        comp_result = report(
            task.host["desired_state"], actual_state, str(task.host), None
        )
        return Result(
            host=task.host, failed=comp_result["failed"], result=comp_result["report"]
        )


# ----------------------------------------------------------------------------
# Runs the script
# ----------------------------------------------------------------------------
def main():
    args = _create_parser()
    files = _file_validation(
        input_data, desired_state, desired_state_tmpl, actual_state
    )
    val_build = ValidationBuilder(args, files)
    result = val_build.engine()
    print_result(result)


if __name__ == "__main__":
    main()
