# COCOAID Phase 11.3.22 Fast Setup Hotfix

## Problem fixed

Repeated setup runs were using `pip install --upgrade` for pip, setuptools, wheel, lxml, and the complete requirements file. Even when packages were already installed, the `--upgrade` flag caused pip to query PyPI for newer package metadata. On slow or blocked connections this produced repeated 15-second `ReadTimeoutError` retries for each package and could delay startup by several minutes.

## Installer changes

- Added `scripts/check_requirements_local.py`, which evaluates the installed environment from local package metadata only and never accesses the network.
- `setup.bat` now checks all project requirements locally before any package installation.
- If every required package/version is already satisfied, setup prints that dependencies are ready and skips PyPI completely.
- Removed unconditional network upgrades of pip, setuptools, wheel, lxml, and all requirements.
- lxml is installed from a binary wheel only when its required range is not already satisfied.
- Fallback dependency installation no longer uses `--upgrade`, so already-satisfied packages are left untouched.
- Network fallback is limited to one retry with an 8-second timeout.
- pip is repaired, if necessary, with Python's bundled `ensurepip` before dependency checks; this step is offline.
- `pip check` still validates the activated COCOAID environment after the local/online dependency step.

## Verification

- Fast-setup focused tests: 12 passed.
- Full unit suite: 331 passed.
- Integration suite: 54 passed.
- Mathematical suite: 9 passed.
- Total automated tests: 394 passed.
- Installation verification passed.
- Phase 3, 4, 5, 6, 6.2, 7, 8, 8.1, 9, 10, and 11 verification passed.
- Existing interface remains `phase11-agritech-interface-1.3.22` because this is an installer-only hotfix; website assets and behavior are unchanged.

## Expected repeated-setup behavior

On a machine where the existing COCOAID virtual environment already satisfies `requirements.txt`, setup should display:

`All required Python packages are already installed and compatible.`

followed by:

`Skipping PyPI access and dependency installation.`

No PyPI retry loop should occur in that case.
