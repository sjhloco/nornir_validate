from typing import Dict, List
from collections import defaultdict
import re

# ----------------------------------------------------------------------------
# Mini-functions used by the main function
# ----------------------------------------------------------------------------
def _make_int(input_data: str) -> int:
    """
    It takes a string and returns an integer if it can, otherwise it returns the original string

    :param input_data: The data to be converted to an integer
    :type input_data: str
    :return: the input_data as an integer.
    """
    try:
        return int(input_data)
    except:
        return input_data


# ----------------------------------------------------------------------------
# Engine that runs the actual state sub-feature formatting for all os types
# ----------------------------------------------------------------------------
def format_output(
    os_type: str, sub_feature: str, output: List, tmp_dict: Dict[str, None]
) -> Dict[str, Dict]:
    """
    > The function takes the command output and formats it into a dictionary that can be used
    to compare against the desired state

    :param os_type: str = The OS type of the device
    :type os_type: str
    :param sub_feature: This is the sub-feature of the feature you're working on. For example, if you're
    working on the "image" feature, the sub-feature would be "version"
    :type sub_feature: str
    :param output: The output from the device
    :type output: List
    :param tmp_dict: This is the dictionary that will be returned by the function
    :type tmp_dict: Dict[str, None]
    :return: A dictionary of dictionaries.
    """

    ### KEY: Set the dictionary keys to use on a per-OS basis
    if bool(re.search("ios", os_type)):
        new_subfeat1 = "xxx"
        new_subfeat2 = "xxx"
    elif bool(re.search("nxos", os_type)):
        new_subfeat1 = "yyy"
        new_subfeat2 = "yyy"
    elif bool(re.search("asa", os_type)):
        new_subfeat1 = "zzz"
        new_subfeat2 = "zzz"
    elif bool(re.search("wlc", os_type)):
        new_subfeat1 = "xxx"
        new_subfeat2 = "xxx"
    # ----------------------------------------------------------------------------
    # SUB_FEATURE1_NAME: {key_name: x}
    # ----------------------------------------------------------------------------
    if sub_feature == "new_subfeat1":
        tmp_dict["key_name"] = output[0][new_subfeat1]

    # ----------------------------------------------------------------------------
    # SUB_FEATURE2_NAME: {xxx: {y: y, z: xxx}}
    # ----------------------------------------------------------------------------
    elif sub_feature == "new_subfeat2":
        for each_item in output:
            tmp_dict[each_item]["y"] = each_x["y"]
            tmp_dict[each_item]["z"] = each_x[new_subfeat2]

    return dict(tmp_dict)
