"""
These unittests test the different os_type command validations using desired_actual_cmd.py
which holds the desired_state, cmd_output and actual_state which have per-os_type child dictionaires
"""

import pytest
import os
import yaml
import json
from glob import glob

from nornir import InitNornir
from nornir.core.task import Result
from nornir.core.filter import F

from nr_val import merge_os_types
from nr_val import task_template
from nr_val import task_desired_state
from nr_val import actual_state_engine
from nr_val import import_actual_state_modules
from nr_val import remove_cmds_desired_state
from compliance_report import generate_validate_report


# ----------------------------------------------------------------------------
# Directory that holds inventory files and load ACL dict (show, delete, wcard, mask, prefix)
# ----------------------------------------------------------------------------
TEST_INVENTORY = os.path.join(os.path.dirname(__file__), "test_inventory")
# WHERE TEST FILES ARE
OS_TEST_FILES = os.path.join(os.path.dirname(__file__), "os_test_files")
# ACTUAL VALIDATE TEMPLATES
TEMPLATE_DIR = os.path.join(os.getcwd(), "templates/")


# ----------------------------------------------------------------------------
# TESTED_DATA: Functions used to get all the feature file names used by the tests
# ----------------------------------------------------------------------------
def form_file_names(dvc_os, feature):
    """Returns all file names and variables needed for assertions"""
    input_data = {}
    try:
        input_data["os_type"] = dvc_os.name.split("_")[1]
    except:
        input_data["os_type"] = dvc_os.name
    os_feat_name = os.path.join(feature.path, f"{dvc_os.name}_{feature.name}")
    input_data["val_file"] = f"{os_feat_name}_validate.yml"
    input_data["ds_file"] = f"{os_feat_name}_desired_state.yml"
    input_data["as_file"] = f"{os_feat_name}_actual_state.yml"
    input_data["cmd_file"] = f"{os_feat_name}_cmd_output.json"
    input_data["vendor_os"] = dvc_os.name.upper()
    input_data["feature"] = feature.name.upper()
    return input_data


def get_test_file_info(return_os_feature_name):
    """Dynamically gets and returns all feature unit-tests and subsequent file names (form_file_names)"""
    all_features = {}
    for each_os in os.scandir(OS_TEST_FILES):
        if each_os.is_dir():
            for each_feature in os.scandir(each_os.path):
                if each_feature.is_dir():
                    name = f"{each_os.name}_{each_feature.name}"
                    all_features[name] = form_file_names(each_os, each_feature)
    return all_features


def get_os_feat_name():
    """Dynamically gets and returns a list of all os_feature name used by loop_os_feature_names"""
    all_os_feat_names = []
    for each_os in os.scandir(OS_TEST_FILES):
        if each_os.is_dir():
            for each_feature in os.scandir(each_os.path):
                if each_feature.is_dir():
                    name = f"{each_os.name}_{each_feature.name}"
                    all_os_feat_names.append(name)
    return all_os_feat_names


def loop_os_feature_names():
    """Loops through all_os_feature_names returning each one which is eventually called desired or actual state test method"""
    all_os_feat_names = get_os_feat_name()
    return (each_os_feat_name for each_os_feat_name in all_os_feat_names)


# ----------------------------------------------------------------------------
# FIXTURES: Initialises Nornir, loads inventory and gest all input data (features and files)
# ----------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def load_inv():
    """Loads nornir inventory used for unittest desired_state template building (is a host_var)"""
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


@pytest.fixture(scope="function", params=loop_os_feature_names())
def return_os_feature_name(request):
    """Returns the looped os_feature_name to be used by the desired or actual state test method"""
    return request.param


@pytest.fixture(scope="class")
def import_modules():
    """Import actual state modules for any feature that has a validation file"""
    all_features = []
    validation_files = glob("tests/os_test_files/*/*/*.yml")
    for each_val_file in validation_files:
        all_features.append(each_val_file.split("/")[3])
    import_actual_state_modules(set(all_features))


# ----------------------------------------------------------------------------
# SHARED_FUNCTIONS: Functions used by both the desired and actual state classes
# ----------------------------------------------------------------------------
def load_yaml_file(input_yml_file):
    """Return the YAML file structured data"""
    with open(input_yml_file) as input_data:
        output_yml_data = yaml.load(input_data, Loader=yaml.FullLoader)
    return output_yml_data


def load_json_file(input_json_file):
    """Return the JSON file structured data"""
    with open(input_json_file) as input_data:
        output_json_data = json.load(input_data)
    return output_json_data


def have_same_keys(feature, state, expected_state, true_state):
    """Test that the keys for the expected desired/actual state and true desired/actual are the same"""
    exp_ds = set(expected_state.keys())
    tru_ds = set(true_state.keys())
    diff = exp_ds.symmetric_difference(tru_ds)
    err_msg = f"❌ {state}: {feature['vendor_os']} {feature['feature']} missing features or sub-features (diffs): {', '.join(diff)}"
    assert not diff, err_msg


def sub_feature_test(feature, state, expected_state, true_state):
    """Test each sub feature expected desired/actual/report state and true desired/actual/report are the same"""
    for sub_feat in expected_state.keys():
        err_msg = f"❌ {state}: {feature['vendor_os']} {feature['feature']} {sub_feat.upper()} is incorrect"
        try:
            del true_state[sub_feat]["complies"]
            del expected_state[sub_feat]["complies"]
        except:
            pass
        assert true_state[sub_feat] == expected_state[sub_feat], err_msg


# ----------------------------------------------------------------------------
# 1. DESIRED_STATE: Tests the templated input_vars (desired_state) are formatted correctly
# ----------------------------------------------------------------------------
class TestDesiredState:

    # ----------------------------------------------------------------------------
    # PRE_TASKS: Methods to get all the elements required to test desired state
    # ----------------------------------------------------------------------------
    def task_get_desired_state(self, task, validations):
        """Return the actual desired state structured data by rendering the template with nornir and assigning as a host_var"""
        task.run(
            task=task_desired_state,
            validations=validations,
            task_template=task_template,
        )

        return Result(host=task.host, result=task.host["desired_state"])

    # ----------------------------------------------------------------------------
    # ASSERT: Calls other class methods and then runs the assertion
    # ----------------------------------------------------------------------------
    def test_desired_state_templating(self, return_os_feature_name):
        """Uses other methods to load all the files and then per-feature desired state assertion"""
        all_features = get_test_file_info(return_os_feature_name)
        feature = all_features[return_os_feature_name]

        validate_file = feature["val_file"]
        desired_state_file = feature["ds_file"]
        os_type = feature["os_type"]

        # Load all the files needed for the validation
        validations = load_yaml_file(validate_file)
        expected_ds = load_yaml_file(desired_state_file)

        # Filter inventory on OS type amd then get true desired state
        task_nr = nr.filter(F(has_parent_group=os_type))
        output = task_nr.run(task=self.task_get_desired_state, validations=validations)
        true_ds = output[f"{os_type}_host"][0].result

        # Make sure keys are the same and then run unittest of each sub-feature within the feature
        have_same_keys(feature, "Desired State", expected_ds, true_ds)
        f_name = feature["feature"].lower()
        sub_feature_test(feature, "Desired State", expected_ds[f_name], true_ds[f_name])


# ----------------------------------------------------------------------------
# 2. ACTUAL_STATE: Per-os_type testing that actual state is formatting commands properly
# ----------------------------------------------------------------------------
@pytest.mark.usefixtures("import_modules")
class TestActualState:
    def test_actual_state_formatting(self, return_os_feature_name):
        """Uses other methods to load all the files and then run per-feature actual state assertion"""
        all_features = get_test_file_info(return_os_feature_name)
        feature = all_features[return_os_feature_name]

        cmd_output = feature["cmd_file"]
        actual_state_file = feature["as_file"]
        os_type = feature["os_type"]

        # Load all the files needed for the validation
        expected_as = load_yaml_file(actual_state_file)
        cmd_output = load_json_file(cmd_output)

        # Merge all OS types and then get the true actual state
        os_type = merge_os_types(nr.inventory.hosts[f"{os_type}_host"])
        true_as = actual_state_engine(os_type, cmd_output)

        # Make sure keys are the same and then run unittest of each sub-feature within the feature
        have_same_keys(feature, "Actual State", expected_as, true_as)
        f_name = feature["feature"].lower()
        have_same_keys(feature, "Actual State", expected_as[f_name], true_as[f_name])
        sub_feature_test(feature, "Actual State", expected_as[f_name], true_as[f_name])


# ----------------------------------------------------------------------------
# 3. REPORT: Tests that  teh compliance report passes
# ----------------------------------------------------------------------------
class TestComplianceReport:
    def test_report_passes(self, return_os_feature_name):
        all_features = get_test_file_info(return_os_feature_name)
        feature = all_features[return_os_feature_name]
        desired_state_file = feature["ds_file"]
        actual_state_file = feature["as_file"]

        # Load all the files needed for the validation
        tmp_desired_state = load_yaml_file(desired_state_file)
        desired_state = remove_cmds_desired_state(tmp_desired_state)
        actual_state = load_yaml_file(actual_state_file)

        # Create the expected passing compliance report and actual compliance report
        sub_feat = {}
        for each_sub_feat in actual_state[feature["feature"].lower()]:
            sub_feat[each_sub_feat] = {"complies": True, "nested": True}
        expected_report = {
            "failed": False,
            "result": "✅ Validation report complies, desired_state and actual_state match.",
            "report": {
                feature["feature"].lower(): {
                    "complies": True,
                    "present": sub_feat,
                    "missing": [],
                    "extra": [],
                },
                "complies": True,
                "skipped": [],
            },
            "report_text": "",
        }
        true_report = generate_validate_report(desired_state, actual_state, "hst", None)

        # If does not comply run assert on each sub-feature within the report
        err_msg = f"❌ Compliance Report: {feature['vendor_os']} {feature['feature']} desired and actual state do not match"
        if true_report.get("failed", True) == False:
            assert true_report == expected_report, err_msg
        else:
            ex_report = expected_report["report"]
            tr_report = true_report["report"]
            have_same_keys(
                feature, "Compliance Report", ex_report["report"], tr_report["report"]
            )
            f_name = feature["feature"].lower()
            ex_report_feat = expected_report["report"][f_name]["present"]
            tr_report_feat = true_report["report"][f_name]["present"]
            have_same_keys(feature, "Compliance Report", ex_report_feat, tr_report_feat)
            sub_feature_test(
                feature, "Compliance Report", ex_report_feat, tr_report_feat
            )
