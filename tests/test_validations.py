"""
These unittests test the different os_type command validations using the files from within the os_type test folder
desired_state.j2 is used for generating the desired_state and commands to be run
actual_state.py is used for formatting the actual_state and the validation file
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
TEMPLATE_DIR = os.path.join(os.getcwd(), "feature_templates/")


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
    input_data["cmd_output_file"] = f"{os_feat_name}_cmd_output.json"
    input_data["cmd_file"] = f"{os_feat_name}_commands.yml"
    input_data["val_file"] = f"{os_feat_name}_validate.yml"
    input_data["ds_file"] = f"{os_feat_name}_desired_state.yml"
    input_data["as_file"] = f"{os_feat_name}_actual_state.yml"
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


def have_same_keys(feature, check_type, expected_state, true_state):
    """Test that the keys for the expected desired/actual state and true desired/actual are the same"""
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
    err_msg = f"❌ {check_type}: {feature['vendor_os']} {feature['feature']} {text_msg} (diffs): {', '.join(str_diff)}"
    assert not diff, err_msg


def sub_feature_test(feature, state, expected_state, true_state):
    """Test each sub feature expected desired/actual/report state and true desired/actual/report are the same"""
    for sub_feat in expected_state.keys():
        err_msg = f"❌ {state}: {feature['vendor_os']} {feature['feature']} is incorrect"
        try:
            del true_state[sub_feat]["complies"]
            del expected_state[sub_feat]["complies"]
        except:
            pass
        assert true_state[sub_feat] == expected_state[sub_feat], err_msg


def task_get_desired_state(task, validations):
    """Return the actual desired state structured data by rendering the template with nornir and assigning as a host_var"""
    task.run(
        task=task_desired_state,
        validations=validations,
        task_template=task_template,
    )

    return Result(host=task.host, result=task.host["desired_state"])


# ----------------------------------------------------------------------------
# 1. COMMANDS: Renders "subfeature_index.yml" with "desired_state.j2" and compares result against the file "commands.yml"
# ----------------------------------------------------------------------------
class TestCommands:
    def test_command_templating(self, return_os_feature_name):
        """Uses other methods to load all the files, then does a per-subfeat command assertion"""
        all_features = get_test_file_info(return_os_feature_name)
        feature = all_features[return_os_feature_name]
        cmd_file = feature["cmd_file"]
        os_type = feature["os_type"]
        vendor_os = feature["vendor_os"].lower()
        index_file = os.path.join(OS_TEST_FILES, vendor_os, "subfeature_index.yml")

        # Load all the files needed for the validation
        expected_cmd = load_yaml_file(cmd_file)
        # index_file = os.path.join(os.path.split(TEST_PATH)[0], "subfeature_index.yml")
        sub_features = load_yaml_file(index_file)["all"][feature["feature"].lower()]
        validations = {"all": {feature["feature"].lower(): sub_features}}

        # Runs the templating to create the actual result
        task_nr = nr.filter(F(has_parent_group=os_type))
        output = task_nr.run(task=task_get_desired_state, validations=validations)
        true_cmd = output[f"{os_type}_host"][0].result

        # Assertion checks that keys are the same for feature and sub-feature before testing each sub-feature
        have_same_keys(feature, "Commands", expected_cmd, true_cmd)
        f_name = feature["feature"].lower()
        have_same_keys(feature, "Commands", expected_cmd[f_name], true_cmd[f_name])
        sub_feature_test(feature, "Commands", expected_cmd[f_name], true_cmd[f_name])


# ----------------------------------------------------------------------------
# 2. VAL_FILE: Formats "cmd_output.json" with "actual_state.create_validation" and compares result against the file "validate.yml"
# ----------------------------------------------------------------------------
@pytest.mark.usefixtures("import_modules")
class TestValFile:
    def test_create_validation_file(self, return_os_feature_name):
        """Uses other methods to load all the files and then run per-feature validation file assertion"""
        all_features = get_test_file_info(return_os_feature_name)
        feature = all_features[return_os_feature_name]
        cmd_output = feature["cmd_output_file"]
        validate_file = feature["val_file"]
        os_type = feature["os_type"]

        # Load all the files needed for the validation
        expect_val = load_yaml_file(validate_file)["all"]
        cmd_output = load_json_file(cmd_output)

        # Merge all OS types and then get the actual result
        os_type = merge_os_types(nr.inventory.hosts[f"{os_type}_host"])
        true_val = actual_state_engine("generate_val_file", os_type, cmd_output)

        # Assertion checks that keys are the same for feature and sub-feature before testing each sub-feature
        have_same_keys(feature, "Create Val File", expect_val, true_val)
        f_name = feature["feature"].lower()
        have_same_keys(feature, "Create Val File", expect_val[f_name], true_val[f_name])
        sub_feature_test(
            feature, "Create Val File", expect_val[f_name], true_val[f_name]
        )


# ----------------------------------------------------------------------------
# 3. DESIRED_STATE: Renders "validate.yml" with "desired_state.j2" and compares result against the file "desired_state.yml"
# ----------------------------------------------------------------------------
class TestDesiredState:
    # USES val file, desired state and compares against the result of desired_state_templating
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

        # Filter inventory on OS type runs the templating to create the actual result
        task_nr = nr.filter(F(has_parent_group=os_type))
        output = task_nr.run(task=task_get_desired_state, validations=validations)
        true_ds = output[f"{os_type}_host"][0].result

        # Assertion checks that keys are the same for feature and sub-feature before testing each sub-feature
        have_same_keys(feature, "Desired State", expected_ds, true_ds)
        f_name = feature["feature"].lower()
        have_same_keys(feature, "Desired State", expected_ds[f_name], true_ds[f_name])
        sub_feature_test(feature, "Desired State", expected_ds[f_name], true_ds[f_name])


# ----------------------------------------------------------------------------
# 4. ACTUAL_STATE: Formats "cmd_output.json" with "actual_state.format_actual_state" and compares result against the file "actual_state.yml"
# ----------------------------------------------------------------------------
@pytest.mark.usefixtures("import_modules")
class TestActualState:
    def test_actual_state_formatting(self, return_os_feature_name):
        """Uses other methods to load all the files and then run per-feature actual state assertion"""
        all_features = get_test_file_info(return_os_feature_name)
        feature = all_features[return_os_feature_name]
        cmd_output = feature["cmd_output_file"]
        actual_state_file = feature["as_file"]
        os_type = feature["os_type"]

        # Load all the files needed for the validation
        expected_as = load_yaml_file(actual_state_file)
        cmd_output = load_json_file(cmd_output)

        # Merge all OS types and then get the true actual state
        os_type = merge_os_types(nr.inventory.hosts[f"{os_type}_host"])
        true_as = actual_state_engine("format_actual_state", os_type, cmd_output)

        # Assertion checks that keys are the same for feature and sub-feature before testing each sub-feature
        have_same_keys(feature, "Actual State", expected_as, true_as)
        f_name = feature["feature"].lower()
        have_same_keys(feature, "Actual State", expected_as[f_name], true_as[f_name])
        sub_feature_test(feature, "Actual State", expected_as[f_name], true_as[f_name])


# ----------------------------------------------------------------------------
# 5. REPORT: Vlidates a compliance report comparing the files "desired_state.yml" and "actual_state.yml" passes
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

        # Create the expected passing compliance report
        all_sub_feat = []
        sub_feat = {"complies": True}
        for each_sub_feat in actual_state[feature["feature"].lower()]:
            base_dict = {"complies": True, "missing": [], "extra": []}
            name = f"{feature['feature'].lower()}.{each_sub_feat}"
            all_sub_feat.append(name)
            tmp_sub_feat = actual_state[feature["feature"].lower()][each_sub_feat]
            if isinstance(tmp_sub_feat, dict):
                present = {}
                for k, v in tmp_sub_feat.items():
                    if isinstance(v, dict) or isinstance(v, list):
                        present[k] = {"complies": True, "nested": True}
                    else:
                        present[k] = {"complies": True, "nested": False}
            elif isinstance(tmp_sub_feat, list):
                present = tmp_sub_feat.copy()
            else:
                present = {each_sub_feat: {"complies": True, "nested": False}}
            base_dict.update({"present": present})
            sub_feat[name] = base_dict
        expected_report = {
            "failed": False,
            "report": sub_feat,
            "result": "✅ Validation report complies, desired_state and actual_state match.",
            "report_text": "",
        }

        # Create the actual compliance report
        true_report = generate_validate_report(desired_state, actual_state, "hst", None)
        ex_report = expected_report["report"]
        tr_report = true_report["report"]

        # Validate all the features are there (keys)
        have_same_keys(feature, "Compliance Report", ex_report, tr_report)
        for sub_feat in all_sub_feat:
            feature["feature"] = sub_feat.upper()
            # Validate all the sub-features are there (keys)
            have_same_keys(feature, "subfeat", ex_report[sub_feat], tr_report[sub_feat])
            # Validate all the sub-features keys (validated objects) are there
            ex_report_val = ex_report[sub_feat]["present"]
            tr_report_val = tr_report[sub_feat]["present"]
            if isinstance(ex_report_val, dict):
                have_same_keys(feature, "val-keys", ex_report_val, tr_report_val)
            # Validate all the sub-features match
            err_msg = f"❌ Compliance Report: {feature['vendor_os']} {feature['feature']} desired and actual state do not match"
            assert ex_report_val == tr_report_val, err_msg
