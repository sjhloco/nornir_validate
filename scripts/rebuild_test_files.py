import os
from importlib.resources import files
from pathlib import Path

from feature_builder import (
    create_commands,
    create_desired_state,
    create_val_file,
    format_actual_state,
)

# Get project root (reliable regardless of where script is run)
project_root = Path(__file__).parent.parent
OS_TEST_FILES = os.path.join(project_root, "tests", "os_test_files")

for os_type in os.scandir(OS_TEST_FILES):
    if os_type.is_dir():
        for feature in os.scandir(os_type.path):
            if feature.is_dir():
                test_path = feature.path
                tmpl_path = files("nornir_validate").joinpath(
                    "feature_templates", feature.name
                )
                # Convert to Path as importlib.resources.files().joinpath() returns a Traversable
                tmpl_path = Path(str(tmpl_path))
                create_commands(os_type.name, feature.name, test_path, tmpl_path)
                create_val_file(os_type.name, feature.name, test_path)
                format_actual_state(os_type.name, feature.name, test_path)
                create_desired_state(os_type.name, feature.name, test_path, tmpl_path)
