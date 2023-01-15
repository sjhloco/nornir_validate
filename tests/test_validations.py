"""
These unittests test the different os_type command validations using desired_actual_cmd.py
which holds the desired_state, cmd_output and actual_state which have per-os_type child dictionaires
"""

import pytest
import os
import yaml
from glob import glob
import json

from nornir import InitNornir
from nornir.core.task import Result
from nornir.core.filter import F

from .ORIG_before_feature_rework import desired_actual_cmd
from nr_val import merge_os_types
from nr_val import task_template
from nr_val import task_desired_state
from nr_val import actual_state_engine

from nr_val import import_actual_state_modules

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
        expected_desired_state = load_yaml_file(desired_state_file)

        # Filter inventory on OS type amd then get true desired state
        task_nr = nr.filter(F(has_parent_group=os_type))
        output = task_nr.run(task=self.task_get_desired_state, validations=validations)

        # breakpoint()
        true_desired_state = output[f"{os_type}_host"][0].result

        err_msg = f"❌ Desired State: {feature['vendor_os']} {feature['feature']} templating is incorrect"
        assert true_desired_state == expected_desired_state, err_msg


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
        expected_actual_state = load_yaml_file(actual_state_file)
        cmd_output = load_json_file(cmd_output)

        # Merge all OS types and then get the true actual state
        os_type = merge_os_types(nr.inventory.hosts[f"{os_type}_host"])
        true_actual_state = actual_state_engine(os_type, cmd_output)

        err_msg = f"❌ Actual State: {feature['vendor_os']} {feature['feature']} formatting is incorrect"
        assert true_actual_state == expected_actual_state, err_msg
