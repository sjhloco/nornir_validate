"""These unittests test the different os_type command validations.

Uses the files from within the os_type test folder.
Desired_state.j2 is used for generating the desired_state and commands to be run.
actual_state.py is used for formatting the actual_state and the validation file.
"""

import json
import os
from collections.abc import Generator
from glob import glob
from os import DirEntry
from pprint import pprint
from typing import Any

import ipdb
import pytest
import yaml
from nornir import InitNornir
from nornir.core.filter import F
from nornir.core.task import Result, Task

from compliance_report import generate_validate_report
from nr_val import (
    actual_state_engine,
    import_actual_state_modules,
    merge_os_types,
    remove_cmds_desired_state,
    task_desired_state,
    task_template,
)

# ----------------------------------------------------------------------------
# Directory that holds inventory files and load ACL dict (show, delete, wcard, mask, prefix)
# ----------------------------------------------------------------------------
TEST_INVENTORY = os.path.join(os.path.dirname(__file__), "test_inventory")
# WHERE TEST FILES ARE
OS_TEST_FILES = os.path.join(os.path.dirname(__file__), "os_test_files")
# ACTUAL VALIDATE TEMPLATES
TEMPLATE_DIR = os.path.join(os.getcwd(), "feature_templates/")
nr: Any = (
    None  # To fix MyPY as nr defined in fixture load_inv (session) which MyPY wont see
)


# ----------------------------------------------------------------------------
# TESTED_DATA: Functions used to get all the feature file names used by the tests
# ----------------------------------------------------------------------------
def form_file_names(dvc_os: DirEntry[Any], feature: DirEntry[Any]) -> dict[str, Any]:
    """Returns all file names and variables needed for assertions.

    Args:
        dvc_os (os.DirEntry): OS type
        feature (os.DirEntry): Name of feature

    Returns:
        dict[str, Any]: All the details needed to do validation for a feature (cmd_file, val_file, feature, vendor_os, etc)
    """
    input_data = {}
    try:
        input_data["os_type"] = dvc_os.name.split("_")[1]
    except:
        #! Waiting to find what hits this
        print("!!!FIX EXCEPT IF THIS IS EVET HIT")
        breakpoint()
        input_data["os_type"] = dvc_os.name
    os_feat_name = os.path.join(feature.path, f"{dvc_os.name}_{feature.name}")
    input_data["cmd_output_file"] = f"{os_feat_name}_cmd_output.json"
    input_data["cmd_file"] = f"{os_feat_name}_commands.yml"
    input_data["val_file"] = f"{os_feat_name}_validate.yml"
    input_data["ds_file"] = f"{os_feat_name}_desired_state.yml"
    input_data["as_file"] = f"{os_feat_name}_actual_state.yml"
    input_data["vendor_os"] = dvc_os.name.upper()
    input_data["feat_name"] = feature.name.upper()
    return input_data


def get_test_file_info() -> dict[str, Any]:
    """Dynamically gets all feature unit-tests and subsequent file names (form_file_names).

    Returns:
        dict[str, dict[str, Any]]: File names and variables needed for all os features
    """
    all_features = {}
    for each_os in os.scandir(OS_TEST_FILES):
        if each_os.is_dir():
            for each_feature in os.scandir(each_os.path):
                if each_feature.is_dir():
                    name = f"{each_os.name}_{each_feature.name}"
                    all_features[name] = form_file_names(each_os, each_feature)
    return all_features


def get_os_feat_name() -> list[str]:
    """Dynamically gets and returns a list of all os_feature name used by loop_os_feature_names.

    Returns:
        list[str]: List of all os_feature name
    """
    all_os_feat_names = []
    for each_os in os.scandir(OS_TEST_FILES):
        if each_os.is_dir():
            for each_feature in os.scandir(each_os.path):
                if each_feature.is_dir():
                    name = f"{each_os.name}_{each_feature.name}"
                    all_os_feat_names.append(name)
    return all_os_feat_names


def loop_os_feature_names() -> Generator[str, None, None]:
    """Loops through all_os_feature_names returning each one which is eventually called desired or actual state test method."""
    all_os_feat_names = get_os_feat_name()
    return (each_os_feat_name for each_os_feat_name in all_os_feat_names)


# ----------------------------------------------------------------------------
# FIXTURES: Initialises Nornir, loads inventory and gets all input data (features and files)
# ----------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def load_inv() -> None:
    """Loads nornir inventory used for unittest (is a host_var)."""
    global nr
    nr = InitNornir(
        inventory={
            "plugin": "SimpleInventory",
            "options": {
                "host_file": os.path.join(TEST_INVENTORY, "hosts_validations.yml"),
                "group_file": os.path.join(TEST_INVENTORY, "groups.yml"),
            },
        },
        logging={"enabled": False},
    )


@pytest.fixture(scope="function", params=loop_os_feature_names())  # noqa: PT003
def return_os_feature_name(request: pytest.FixtureRequest) -> Any:  # noqa: ANN401
    """Returns the looped os_feature_name to be used by the desired or actual state test method."""
    return str(request.param)


@pytest.fixture(scope="class")
def import_modules() -> None:
    """Import actual state modules for any feature that has a validation file."""
    all_features = []
    validation_files = glob("tests/os_test_files/*/*/*.yml")
    for each_val_file in validation_files:
        all_features.append(each_val_file.split("/")[3])
    import_actual_state_modules(set(all_features))


# ----------------------------------------------------------------------------
# SHARED_FUNCTIONS: Functions used by both the desired and actual state classes
# ----------------------------------------------------------------------------
def load_yaml_file(input_yml_file: str) -> dict[str, Any]:
    """Return the YAML file structured data.

    Args:
        input_yml_file (str): Full path to file to be opened

    Returns:
        dict[str, object]: Contents of the loaded file as a dictionary
    """
    with open(input_yml_file) as input_data:
        output_yml_data: dict[str, Any] = yaml.load(input_data, Loader=yaml.FullLoader)
    return output_yml_data


def load_json_file(input_json_file: str) -> dict[str, Any]:
    """Return the JSON file structured data.

    Args:
        input_json_file (str): Full path to file to be opened

    Returns:
        dict[str, dict[str, Any]]: Contents of the loaded file as a dictionary
    """
    with open(input_json_file) as input_data:
        output_json_data: dict[str, Any] = json.load(input_data)
    return output_json_data


def have_same_keys(
    feature: dict[str, Any],
    check_type: str,
    expected_state: dict[str, Any],
    true_state: dict[str, Any],
) -> None:
    """Test that the keys for the expected desired/actual state and true desired/actual are the same.

    Args:
        feature (dict[str, Any]): File names and feature info
        check_type (str): Which test (method) is calling this function
        expected_state (dict[str, Any]): The expected result of desired state dict from the test
        true_state (dict[str, Any]): The actual result of desired state dict from the test
    """
    exp_ds = set(expected_state.keys())
    tru_ds = set(true_state.keys())
    diff = exp_ds.symmetric_difference(tru_ds)
    if check_type == "val-keys":
        text_msg = "missing sub-feature validated objects/keys"
        check_type = "Compliance Report"
    elif check_type == "subfeat":
        text_msg = "missing sub-features"
        check_type = "Compliance Report"
    else:
        text_msg = "missing features"
    str_diff = []
    for x in diff:
        str_diff.append(str(x))
    err_msg = f"❌ {check_type}: {feature['vendor_os']} {feature['feat_name']} {text_msg} (diffs): {', '.join(str_diff)}"
    assert not diff, err_msg


def sub_feature_test(
    feature: dict[str, Any],
    check_type: str,
    expected_state: dict[str, Any],
    true_state: dict[str, Any],
) -> None:
    """Test each sub-feature expected desired/actual/report state and true desired/actual/report are the same.

    Args:
        feature (dict[str, Any]): File names and feature info
        check_type (str): Which test (method) is calling this function
        expected_state (dict[str, Any]): The expected result of desired state dict from the test
        true_state (dict[str, Any]): The actual result of desired state dict from the test
    """
    for sub_feat in expected_state.keys():  # noqa: SIM118
        err_msg = f"❌ {check_type}: {feature['vendor_os']} {feature['feat_name']} is incorrect"
        try:
            del true_state[sub_feat]["complies"]
            del expected_state[sub_feat]["complies"]
        except Exception:
            pass
        assert true_state[sub_feat] == expected_state[sub_feat], err_msg


def task_get_desired_state(task: Task, validations: dict[str, Any]) -> Result:
    """Return the actual by rendering the template with nornir and assigning as a host_var.

    Args:
        task (Task): The nornir tasks that implements (runs) this the nornir-jinja template plugin
        validations (dict[str, Any]): The validations to be run (user input validation data)

    Returns:
        Result: Nornir result with host and desired state structured data
    """
    task.run(
        task=task_desired_state,
        validations=validations,
        task_template=task_template,
    )
    return Result(host=task.host, result=task.host["desired_state"])


# ----------------------------------------------------------------------------
# 1. COMMANDS: Asserts commands created properly on a per-subfeat basis
# ----------------------------------------------------------------------------
class TestCommands:
    def test_command_templating(self, return_os_feature_name: str) -> None:
        """Renders "subfeature_index.yml" with "desired_state.j2" and compares result against the file "commands.yml".

        Args:
            return_os_feature_name (str): OS followed by feature name
        """
        all_features = get_test_file_info()
        feature = all_features[return_os_feature_name]
        cmd_file = feature["cmd_file"]
        os_type = feature["os_type"]
        vendor_os = feature["vendor_os"].lower()
        index_file = os.path.join(OS_TEST_FILES, vendor_os, "subfeature_index.yml")

        # Load all the files needed for the validation
        expected_cmd = load_yaml_file(cmd_file)
        sub_features = load_yaml_file(index_file)["all"][feature["feat_name"].lower()]
        validations = {"all": {feature["feat_name"].lower(): sub_features}}

        # Runs the templating to create the actual result
        task_nr = nr.filter(F(has_parent_group=os_type))
        output = task_nr.run(task=task_get_desired_state, validations=validations)
        true_cmd = output[f"{os_type}_host"][0].result

        # Assertion checks that keys are the same for feature and sub-feature before testing each sub-feature
        have_same_keys(feature, "Commands", expected_cmd, true_cmd)
        f_name = feature["feat_name"].lower()
        have_same_keys(feature, "Commands", expected_cmd[f_name], true_cmd[f_name])
        sub_feature_test(feature, "Commands", expected_cmd[f_name], true_cmd[f_name])


# ----------------------------------------------------------------------------
# 2. VAL_FILE: Asserts the validation file is created properly (is auto generated from actual state
# ----------------------------------------------------------------------------
@pytest.mark.usefixtures("import_modules")
class TestValFile:
    def test_create_validation_file(self, return_os_feature_name: str) -> None:
        """Formats "cmd_output.json" with "actual_state.create_validation" and compares result against the file "validate.yml".

        Args:
            return_os_feature_name (str): OS followed by feature name
        """
        all_features = get_test_file_info()
        feature = all_features[return_os_feature_name]
        cmd_output = feature["cmd_output_file"]
        validate_file = feature["val_file"]
        os_type = feature["os_type"]

        # Load all the files needed for the validation
        expect_val = load_yaml_file(validate_file)["all"]
        cmd_output = load_json_file(cmd_output)

        # Merge all OS types and then get the actual result
        os_type = merge_os_types(nr.inventory.hosts[f"{os_type}_host"])
        true_val = actual_state_engine(True, os_type, cmd_output)

        # Assertion checks that keys are the same for feature and sub-feature before testing each sub-feature
        have_same_keys(feature, "Create Val File", expect_val, true_val)
        f_name = feature["feat_name"].lower()
        have_same_keys(feature, "Create Val File", expect_val[f_name], true_val[f_name])
        sub_feature_test(
            feature, "Create Val File", expect_val[f_name], true_val[f_name]
        )


# ----------------------------------------------------------------------------
# 3. DESIRED_STATE: Asserts desired state created properly on a per-subfeat basis
# ----------------------------------------------------------------------------
class TestDesiredState:
    # USES val file, desired state and compares against the result of desired_state_templating
    def test_desired_state_templating(self, return_os_feature_name: str) -> None:
        """Renders "validate.yml" with "desired_state.j2" and compares result against the file "desired_state.yml".

        Args:
            return_os_feature_name (str): OS followed by feature name
        """
        all_features = get_test_file_info()
        feature = all_features[return_os_feature_name]
        validate_file = feature["val_file"]
        desired_state_file = feature["ds_file"]
        os_type = feature["os_type"]

        # Load all the files needed for the validation
        validations = load_yaml_file(validate_file)
        expected_ds = load_yaml_file(desired_state_file)

        # Filter inventory on OS type runs the templating to create the actual result
        task_nr = nr.filter(F(has_parent_group=os_type))
        output = task_nr.run(task=task_get_desired_state, validations=validations)
        true_ds = output[f"{os_type}_host"][0].result

        # Assertion checks that keys are the same for feature and sub-feature before testing each sub-feature
        have_same_keys(feature, "Desired State", expected_ds, true_ds)
        f_name = feature["feat_name"].lower()
        have_same_keys(feature, "Desired State", expected_ds[f_name], true_ds[f_name])
        sub_feature_test(feature, "Desired State", expected_ds[f_name], true_ds[f_name])


# ----------------------------------------------------------------------------
# 4. ACTUAL_STATE: Asserts desired state created properly on a per-subfeat basis
# ----------------------------------------------------------------------------
@pytest.mark.usefixtures("import_modules")
class TestActualState:
    def test_actual_state_formatting(self, return_os_feature_name: str) -> None:
        """Formats "cmd_output.json" with "actual_state.format_actual_state" and compares result against the file "actual_state.yml".

        Args:
            return_os_feature_name (str): OS followed by feature name
        """
        all_features = get_test_file_info()
        feature = all_features[return_os_feature_name]
        cmd_output = feature["cmd_output_file"]
        actual_state_file = feature["as_file"]
        os_type = feature["os_type"]

        # Load all the files needed for the validation
        expected_as = load_yaml_file(actual_state_file)
        cmd_output = load_json_file(cmd_output)

        # Merge all OS types and then get the true actual state
        os_type = merge_os_types(nr.inventory.hosts[f"{os_type}_host"])
        true_as = actual_state_engine(False, os_type, cmd_output)

        # Assertion checks that keys are the same for feature and sub-feature before testing each sub-feature
        have_same_keys(feature, "Actual State", expected_as, true_as)
        f_name = feature["feat_name"].lower()
        have_same_keys(feature, "Actual State", expected_as[f_name], true_as[f_name])
        sub_feature_test(feature, "Actual State", expected_as[f_name], true_as[f_name])


# ----------------------------------------------------------------------------
# 5. REPORT: Asserts compliance report output
# ----------------------------------------------------------------------------
class TestComplianceReport:
    def _create_ex_report(
        self, feature: dict[str, Any], state: dict[str, Any]
    ) -> dict[str, Any]:
        """Helper to create the expected passing compliance report from actual state or desired state."""
        self.all_sub_feat = []
        sub_feat: dict[str, Any] = {"complies": True}
        for each_sub_feat in state[feature["feat_name"].lower()]:
            base_dict = {"complies": True, "missing": [], "extra": []}
            name = f"{feature['feat_name'].lower()}.{each_sub_feat}"
            self.all_sub_feat.append(name)
            tmp_sub_feat = state[feature["feat_name"].lower()][each_sub_feat]
            if isinstance(tmp_sub_feat, dict):
                present = {}
                for k, v in tmp_sub_feat.items():
                    if isinstance(v, (dict, list)):
                        present[k] = {"complies": True, "nested": True}
                    else:
                        present[k] = {"complies": True, "nested": False}
            elif isinstance(tmp_sub_feat, list):
                present = {
                    item: {"complies": True, "nested": False} for item in tmp_sub_feat
                }
            else:
                present = {each_sub_feat: {"complies": True, "nested": False}}
            base_dict.update({"present": present})
            sub_feat[name] = base_dict
        return {
            "failed": False,
            "report": sub_feat,
            "result": "✅ Validation report complies, desired_state and actual_state match.",
            "report_text": "",
        }

    def test_report_passes(self, return_os_feature_name: str) -> None:
        """Validates a compliance report by comparing the files "desired_state.yml" and "actual_state.yml"."""
        all_features = get_test_file_info()
        feature = all_features[return_os_feature_name]
        desired_state_file = feature["ds_file"]
        actual_state_file = feature["as_file"]

        # Load all the files needed for the validation
        tmp_desired_state = load_yaml_file(desired_state_file)
        desired_state = remove_cmds_desired_state(tmp_desired_state)
        actual_state = load_yaml_file(actual_state_file)

        # Create the actual compliance report
        true_report = generate_validate_report(desired_state, actual_state, "hst", None)
        # Create dummy val reports to compare against, normally from actual state
        if "interface" in return_os_feature_name:
            # Interface has to use desired state as actual state has disabled interfaces
            expected_report = self._create_ex_report(feature, desired_state)
        else:
            expected_report = self._create_ex_report(feature, actual_state)
        ex_report = expected_report["report"]
        tr_report = true_report["report"]

        # Validate all the features are there (keys)
        have_same_keys(feature, "Compliance Report", ex_report, tr_report)
        for each_sub_feat in self.all_sub_feat:
            feature["feat_name"] = each_sub_feat.upper()
            # Validate all the sub-features are there (keys)
            have_same_keys(
                feature, "subfeat", ex_report[each_sub_feat], tr_report[each_sub_feat]
            )
            # Validate all the sub-features keys (validated objects) are there
            ex_report_val = ex_report[each_sub_feat]["present"]
            tr_report_val = tr_report[each_sub_feat]["present"]
            if isinstance(ex_report_val, dict):
                have_same_keys(feature, "val-keys", ex_report_val, tr_report_val)
            # Validate all the sub-features match
            err_msg = f"❌ Compliance Report: {feature['vendor_os']} {feature['feat_name']} desired and actual state do not match"
            assert ex_report_val == tr_report_val, err_msg
