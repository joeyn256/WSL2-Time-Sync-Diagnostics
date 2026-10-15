from importlib.metadata import PackageNotFoundError, version as _distribution_version

try:
    __version__ = _distribution_version("wsl2-time-sync-diagnostics")
except PackageNotFoundError:
    # Source-tree fallback for tooling that imports before installation.
    __version__ = "0+unknown"
