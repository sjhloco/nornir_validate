from typing import Any, Dict
from napalm.base import validate
from napalm.base.exceptions import ValidationException
import json
import os
import re
from datetime import datetime

# ----------------------------------------------------------------------------
# FIX: napalm_validate doesn't recognize ~/ for home drive
# ----------------------------------------------------------------------------
def fix_home_path(input_path: str) -> str:
    """
    It takes a string as input, and if the string starts with `~/`, it replaces the `~` with the user's
    home directory

    :param input_path: The path to the input file
    :type input_path: str
    :return: The input path with the home directory expanded.
    """
    if re.match("^~/", input_path):
        return os.path.expanduser(input_path)
    else:
        return input_path


# -------------------------------------------------------------------------------------------
# REPORT_FILE: If a hostname and directory are passed in as function arguments saves report to file
# --------------------------------------------------------------------------------------------
def save_report_to_file(
    hostname: str, directory: str, report: Dict[str, Any], complies: bool, skipped: bool
) -> str:
    """
    If the report file already exists, it will update the 'skipped' and 'complies' keys with the report
    outcome. If the report file does not exist, it will create a new report file and add the 'skipped'
    and 'complies' keys with the report outcome

    :param hostname: The hostname of the device you're running the validation against
    :type hostname: str
    :param directory: The directory where the report will be saved
    :type directory: str
    :param report: The report dictionary that is returned by napalm_validate
    :type report: Dict[str, Any]
    :param complies: True if the device complies with the validation rules, False otherwise
    :type complies: bool
    :param skipped: A list of skipped tests
    :type skipped: bool
    :return: The report can be viewed using:
    cat /home/vagrant/napalm_validate_reports/nxos1_compliance_report_20200708-1456.json | python -m
    json.tool
    """

    filename = os.path.join(
        fix_home_path(directory),
        hostname
        + "_compliance_report_"
        + datetime.now().strftime("%Y%m%d-%H%M")
        + ".json",
    )
    # If report file already exists conditionally updates 'skipped' and 'complies' with report outcome
    if os.path.exists(filename):
        with open(filename, "r") as file_content:
            existing_report = json.load(file_content)
        if list(report.values())[0].get("skipped"):
            existing_report["skipped"].extend(skipped)
        elif len(skipped) == 0:
            existing_report["skipped"] = skipped
        # Only adds if is no already failing compliance
        if existing_report.get("complies") == True:
            existing_report["complies"] = complies
    # If creating a new report file adds 'complies' and 'skipped' with report outcome
    else:
        existing_report = {}
        existing_report["complies"] = complies
        if len(skipped) == 0:
            existing_report["skipped"] = skipped

    # Writes to file the full napalm_validate result (including an existing report)
    existing_report.update(report)
    with open(filename, "w") as file_content:
        json.dump(existing_report, file_content)
    # return f" The report can be viewed using:  \n \33[3m\033[1;37m\33[30m  cat {filename} | python -m json.tool \033[0;0m"
    return f" The report can be viewed using:  \ncat {filename} | python -m json.tool"


# ----------------------------------------------------------------------------------------------------------
# VALIDATE: Uses naplam_validate on custom data fed in (still supports '_mode: strict') to validate and create reports
# ----------------------------------------------------------------------------------------------------------
def generate_validate_report(
    d_state: Dict[str, Dict], a_state: Dict[str, Dict], hostname: str, directory: str
) -> Dict[str, Any]:
    """
    The function takes the desired and actual state dictionaries, hostname and directory as arguments.
    It then runs the compare method from the napalm-validate library on each feature in the desired
    state dictionary. If the compare method can't be run on a feature, it adds a skipped key to the
    feature dictionary. The function then checks if the report complies and if any features were
    skipped. If the report complies, it returns a dictionary with the result, report and report_text. If
    the report doesn't comply or features were skipped, it returns a dictionary with the report and
    report_text

    :param d_state: Desired state dictionary
    :type d_state: Dict[str, Dict]
    :param a_state: Actual state of the device
    :type a_state: Dict[str, Dict]
    :param hostname: The hostname of the device being validated
    :type hostname: str
    :param directory: Directory where the report will be saved
    :type directory: str
    :return: a dictionary with the following keys:
    """

    report: Dict[str, Any] = {}
    for feature, sub_feat in d_state.items():
        for each_sub_feat in sub_feat:
            try:
                name = f"{feature}.{each_sub_feat}"
                # napalm_validate compare method produces report based on desired and actual state
                d_state_sub_feat = d_state[feature][each_sub_feat]
                a_state_sub_feat = a_state[feature][each_sub_feat]
                if isinstance(d_state_sub_feat, dict):
                    report[name] = validate.compare(d_state_sub_feat, a_state_sub_feat)
                else:
                    report[name] = validate.compare(
                        {each_sub_feat: d_state_sub_feat},
                        {each_sub_feat: a_state_sub_feat},
                    )
            # If validation couldn't be run on a command adds skipped key to the cmd dictionary
            except NotImplementedError:
                report[feature] = {"skipped": True, "reason": "NotImplemented"}

    # RESULT: Results of compliance report (complies = validation result, skipped (list of skipped cmds) = validation didn't run)
    complies = all([each_cmpl.get("complies", True) for each_cmpl in report.values()])
    skipped = [feat for feat, output in report.items() if output.get("skipped", False)]

    # REPORT_FILE: Save report to file, if not add complies and skipped dictionary to report
    if hostname != None and directory != None:
        report_text = save_report_to_file(
            hostname, directory, report, complies, skipped
        )
    else:
        # Empty value if report_file not created
        report_text = ""
    # These must be added after the report
    report["complies"] = complies
    if len(skipped) != 0:
        report["skipped"] = skipped
    # RETURN_RESULT: If compliance fails set state failed (used by Nornir). report dict is used in validation builder
    if complies == True:
        return dict(
            failed=False,
            result="\u2705 Validation report complies, desired_state and actual_state match.",
            report=report,
            report_text=report_text,
        )
    if complies == False or skipped == True:
        return dict(failed=True, result=report, report=report, report_text=report_text)
