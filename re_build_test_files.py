import os

from feature_builder import (
    create_commands,
    create_desired_state,
    create_val_file,
    format_actual_state,
)

OS_TEST_FILES = os.path.join(os.path.dirname(__file__), "tests", "os_test_files")

for os_type in os.scandir(OS_TEST_FILES):
    if os_type.is_dir():
        for feature in os.scandir(os_type.path):
            if feature.is_dir():
                test_path = feature.path
                tmpl_path = os.path.join(os.getcwd(), "feature_templates", feature.name)
                create_commands(os_type.name, feature.name, test_path, tmpl_path)
                create_val_file(os_type.name, feature.name, test_path)
                format_actual_state(os_type.name, feature.name, test_path)
                create_desired_state(os_type.name, feature.name, test_path, tmpl_path)
