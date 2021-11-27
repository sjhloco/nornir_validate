from typing import Any, Dict, List
from napalm.base import validate
from napalm.base.exceptions import ValidationException
import json
import os
import re
import datetime
import ipdb

# FIX: napalm_validate doesn't recognize ~/ for home drive, also used in report method
def fix_home_path(input_path: str) -> str:
    if re.match('^~/', input_path):
        return os.path.expanduser(input_path)
    else:
        return input_path

# VALIDATE: Uses naplam_validate on custom data fed into it (still supports '_mode: strict') to validate and create reports
def compliance_report(desired_state: Dict[str, Dict], actual_state: Dict[str, Dict], hostname: str, directory: str):
    report: Dict[str, Any] = {}
    for cmd, desired_results in desired_state.items():
        # Safe guard in case any empty desired_results, stops script failing
        if desired_results == None:
            pass
        else:
            # napalm_validate compare method produces report based on desired and actual state
            try:
                report[cmd] = validate.compare(desired_results, actual_state[cmd])
            # If validation couldn't be run on a command adds skipped key to the cmd dictionary
            except NotImplementedError:
                report[cmd] = {"skipped": True, "reason": "NotImplemented"}
    # RESULT: Results of compliance report (complies = validation result, skipped = validation didn't run)
    complies = all([each_cmpl.get("complies", True) for each_cmpl in report.values()])
    skipped = [cmd for cmd, output in report.items() if output.get("skipped", False)]
    report_text = ''        # Empty value if report_file not created

    # REPORT_FILE: If a hostname and directory are passed in as function arguments saves report to file
    if hostname != None and directory != None:
        filename = os.path.join(fix_home_path(directory),  hostname + '_compliance_report_' + str(datetime.date.today()) + '.json')
        # If report file already exists conditionally updates 'skipped' and 'complies' with report outcome
        if os.path.exists(filename):
            with open(filename, 'r') as file_content:
                existing_report = json.load(file_content)
            if list(report.values())[0].get('skipped'):
                existing_report['skipped'].extend(skipped)
            if existing_report.get('complies'):         # No need to add if already failing compliance
                existing_report['complies'] = complies
        # If creating a new report file adds 'complies' and 'skipped' with report outcome
        else:
            existing_report = {}
            existing_report['complies'] = complies
            existing_report['skipped'] = skipped
        # Writes to file the full napalm_validate result (including an existing report)
        existing_report.update(report)
        with open(filename, 'w') as file_content:
            json.dump(existing_report, file_content)
        report_text = " The report can be viewed using:  "\
                     f"\n \33[3m\033[1;37m\33[30m  cat {filename} | python -m json.tool \033[0;0m"

    # RETURN_RESULT: Returns the report if compliance failed and sets the state to failed (used by Nornir)
    # Also create report dict as that is used in validation builder
    if complies == True:
        return dict(failed=False, result=u"\u2705 Validation report complies, desired_state and actual_state match." + report_text, report=report)
    if complies == False or skipped == True:
        return dict(failed=True, result=report, report=report)
