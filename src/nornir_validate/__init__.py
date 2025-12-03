from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nornir_validate")
except PackageNotFoundError:
    # Package isn't installed yet (dev mode)
    __version__ = "0.0.0"
