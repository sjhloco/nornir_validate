"""Use if want to feed in static command output (say on train and eve not working !!!!!
Command output is put in the file xxx_actual_cmd_output.py in the format (2nd cmd is text, no ntc-template for it):

cmd_output = {
    "show sysinfo": [
        {
            "bootloader_version": "8.3.15.177",
        .....
        },
    "show client summary": "\n"
    "Number of Clients................................ 4\n"
    "\n"
    ...
    }

When run prints all the actual state dicts to screen

> python static_cmd_output.py
{'show ap image all': {'DC1-AP-0101': {'backup_image': '8.10.130.0',
                                       'primary_image': '8.10.171.0'},
...
}
"""

from typing import Any, Dict, List
from collections import defaultdict
from actual_state import format_actual_state
import nxos_actual_cmd_output
import wlc_actual_cmd_output
import asa_actual_cmd_output
from pprint import pprint


def actual_state_engine(os_type: List, cmd_output: Dict[str, List]) -> Dict[str, Dict]:
    actual_state: Dict[str, Any] = {}

    # Loops through getting command and output from the command
    for cmd, output in cmd_output.items():
        tmp_dict = defaultdict(dict)
        if output == None:
            actual_state[cmd] = tmp_dict
        elif len(output) == 0:
            actual_state[cmd] = tmp_dict
        else:
            format_actual_state(os_type, cmd, output, tmp_dict, actual_state)

    return actual_state


# cmd_output = nxos_actual_cmd_output.cmd_output
# cmd_output = wlc_actual_cmd_output.cmd_output
cmd_output = asa_actual_cmd_output.cmd_output

# If wanted to run against commands in here rather than a file
# cmd_output = {
#     "show version": [
#         {
#             "boot_image": "bootflash:///nxos.9.3.5.bin",
#             "hostname": "DC2-N9K-LEF01",
#             "last_reboot_reason": "Reset Requested by CLI command " "reload",
#             "os": "9.3(5)",
#             "platform": "C93180YC",
#             "serial": "FDO24080HZU",
#             "uptime": "759 day(s), 4 hour(s), 22 minute(s), 13 " "second(s)",
#         }
#     ]
# }

# a = actual_state_engine(["nxos"], cmd_output)
# a = actual_state_engine(["wlc"], cmd_output)
a = actual_state_engine(["asa"], cmd_output)
pprint(a)
