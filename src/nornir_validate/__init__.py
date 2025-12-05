from importlib.metadata import PackageNotFoundError, version

from nornir_validate.core import (
    print_build_result,
    print_val_result,
    val_file_builder,
    validate,
)

try:
    __version__ = version("nornir_validate")
except PackageNotFoundError:
    # Package isn't installed yet (dev mode)
    __version__ = "0.0.0"

__all__ = ["validate", "print_val_result", "print_val_result", "print_build_result"]
