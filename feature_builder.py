import os
import yaml
import json
import shutil
import argparse
import importlib
from rich.theme import Theme
from rich.console import Console
from typing import Any, Dict, List
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader, StrictUndefined


# ----------------------------------------------------------------------------
# Flags to define what is run, all take 2 arguments
# ----------------------------------------------------------------------------
def _create_parser() -> Dict[str, Any]:
    """
    This function creates a parser object, adds arguments to it, and returns the arguments as a
    dictionary
    :return: The vars() function returns the __dict__ attribute of the object.
    """
    parser = argparse.ArgumentParser()
    # parser.add_argument(
    #     "-di",
    #     "--discovery",
    #     action="store_true",
    #     help="Runs the desired_state command on a device printing raw output",
    # )
    parser.add_argument(
        "-cf",
        "--create_feature",
        nargs=2,
        help="Creates the feature and feature test directories",
    )
    parser.add_argument(
        "-as",
        "--create_actual_state",
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
# Create the Feature and feature test directories
# ----------------------------------------------------------------------------
def create_feature_dir(rc: "Rich", os_type: str, feature: str) -> None:
    """
    > Create new feature and feature test folders (copies those from skeleton_new_feature so
    includes all files)

    The function takes in three arguments:

    - `rc`: This is the `Rich` object that we imported from the `rich` library. It's used to print out
    the output in a nice format.
    - `os_type`: This is the operating system type that we want to create the feature for.
    - `feature`: This is the name of the feature that we want to create

    :param rc: This is the Rich object that is passed to the function. It is used to print to the
    console
    :type rc: "Rich"
    :param os_type: The operating system type (e.g. "linux", "windows")
    :type os_type: str
    :param feature: The name of the feature you want to create
    :type feature: str
    """
    # Create new feature and feature test folders (copies those from skeleton_new_feature so includes all files)
    feat_dir = os.path.join(os.getcwd(), "skeleton_new_feature", "newfeature")
    feat_test_dir = os.path.join(os.getcwd(), "skeleton_new_feature", "newfeature_test")
    for src, dst in [(feat_dir, TMPL_PATH), (feat_test_dir, TEST_PATH)]:
        if not os.path.exists(TMPL_PATH):
            shutil.copytree(src, dst, ignore=None, dirs_exist_ok=False)
    # Rename the files within the feature directory
    old_names = ["newfeature_desired_state.j2", "newfeature_actual_state.py"]
    new_names = [f"{feature}_desired_state.j2", f"{feature}_actual_state.py"]
    for old_name, new_name in zip(old_names, new_names):
        os.rename(os.path.join(TMPL_PATH, old_name), os.path.join(TMPL_PATH, new_name))
    # Rename the files within the feature test directory
    old_names = [
        f"ostype_newfeature_validate.yml",
        f"ostype_newfeature_cmd_output.json",
    ]
    new_names = [
        f"{os_type}_{feature}_validate.yml",
        f"{os_type}_{feature}_cmd_output.json",
    ]
    for old_name, new_name in zip(old_names, new_names):
        os.rename(os.path.join(TEST_PATH, old_name), os.path.join(TEST_PATH, new_name))

    rc.print(f"✅ Created directories '{TMPL_PATH}' and '{TEST_PATH}'")


# ----------------------------------------------------------------------------
# Generates the data structured command output
# ----------------------------------------------------------------------------
def generate_cmd_data(rc: "Rich", os_type: str, feature: str) -> None:
    pass


# ----------------------------------------------------------------------------
# Create the desired state yaml test file
# ----------------------------------------------------------------------------
def create_desired_state(rc: "Rich", os_type: str, feature: str) -> None:
    """
    It takes the data from the `validate.yml` file, renders the template, and saves the result to a file

    :param rc: This is the Rich object that we created earlier
    :type rc: "Rich"
    :param os_type: The operating system type
    :type os_type: str
    :param feature: The name of the feature to create the desired state for
    :type feature: str
    """
    # Loads data from YAML file
    val_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_validate.yml")
    with open(val_file) as input_data:
        val_data = yaml.load(input_data, Loader=yaml.FullLoader)
    # Loads the and render the template
    env = Environment(
        loader=FileSystemLoader(TMPL_PATH),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template(f"{feature}_desired_state.j2")
    sub_feat = val_data["all"][feature]
    ds = tmpl.render(os_type=os_type, feature=feature, sub_features=sub_feat)
    # Save to file
    ds_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_desired_state.yml")
    with open(ds_file, "w") as f:
        f.write(ds.lstrip().rstrip()[2:])

    rc.print(f"✅ Created the file '{ds_file}'")


# ----------------------------------------------------------------------------
# Create the desired state yaml test file
# ----------------------------------------------------------------------------
def create_actual_state(rc: "Rich", os_type: str, feature: str) -> None:
    """
    > It takes the command output file and converts it to the actual state file

    :param rc: This is the Rich class object that we created earlier
    :type rc: "Rich"
    :param os_type: The OS type (e.g. linux, windows, aix)
    :type os_type: str
    :param feature: The name of the feature you want to create the actual state for
    :type feature: str
    """
    # import the feature formatting module
    feat_mod = f"feature_templates.{feature}.{feature}_actual_state"
    globals()[f"{feature}"] = importlib.import_module(feat_mod)
    # Load the cmd output file
    cmd_output_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_cmd_output.json")
    with open(cmd_output_file) as input_data:
        cmd_output = json.load(input_data)
    # Generate the actual state
    actual_state = defaultdict(dict)
    for sub_feature, output in cmd_output[feature].items():
        tmp_dict = defaultdict(dict)
        result = eval(feature).format_output(os_type, sub_feature, output, tmp_dict)
        actual_state[feature][sub_feature] = result
    # Convert to yaml and save to file
    as_file = os.path.join(TEST_PATH, f"{os_type}_{feature}_actual_state.yml")
    with open(as_file, "w") as yaml_file:
        yaml.dump(dict(actual_state), yaml_file, sort_keys=False)

    rc.print(f"✅ Created the file '{as_file}'")


# ----------------------------------------------------------------------------
# Runs the script
# ----------------------------------------------------------------------------
def main():
    global TEST_PATH, TMPL_PATH
    my_theme = {"repr.ipv4": "none", "repr.number": "none", "repr.call": "none"}
    rc = Console(theme=Theme(my_theme))

    args = _create_parser()
    os_type = [x for x in args.values() if x != None][0][0]
    feature = [x for x in args.values() if x != None][0][1]
    TEST_PATH = os.path.join(os.getcwd(), "tests", "os_test_files", os_type, feature)
    TMPL_PATH = os.path.join(os.getcwd(), "feature_templates", feature)

    if args["create_feature"] != None:
        create_feature_dir(rc, os_type, feature)
    elif args["discovery"] == None:
        generate_cmd_data(rc, os_type, feature)
    elif args["create_desired_state"] == None:
        create_desired_state(rc, os_type, feature)
    elif args["create_actual_state"] == None:
        create_actual_state(rc, os_type, feature)
    else:
        raise Exception(
            "At least one of the arguments '-cf', '-as' or '-ds' is required"
        )


if __name__ == "__main__":
    main()


### !! Run using python feature_builder.py -flag <os_type> <feature>
