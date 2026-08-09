from __future__ import annotations

import argparse
import importlib.metadata as metadata
from pathlib import Path
from typing import Iterable

from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.requirements import Requirement


def _iter_requirement_lines(path: Path) -> Iterable[str]:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        if line:
            yield line


def _installed_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _requirement_satisfied(requirement: Requirement) -> tuple[bool, str]:
    environment = default_environment()
    if requirement.marker and not requirement.marker.evaluate(environment):
        return True, f"SKIP {requirement} (marker does not apply)"

    installed = _installed_version(requirement.name)
    if installed is None:
        return False, f"MISSING {requirement.name} ({requirement.specifier or 'any version'})"
    if requirement.specifier and not requirement.specifier.contains(installed, prereleases=True):
        return False, f"MISMATCH {requirement.name}: installed {installed}, requires {requirement.specifier}"

    # Verify dependencies requested by top-level extras such as uvicorn[standard].
    # pip check handles ordinary transitive dependencies; this catches optional
    # extra dependencies that would otherwise be invisible to a top-level check.
    if requirement.extras:
        try:
            dist_metadata = metadata.metadata(requirement.name)
        except metadata.PackageNotFoundError:
            return False, f"MISSING {requirement.name}"
        for extra in requirement.extras:
            extra_env = dict(environment)
            extra_env["extra"] = extra
            for requires_dist in dist_metadata.get_all("Requires-Dist") or []:
                child = Requirement(requires_dist)
                if child.marker and not child.marker.evaluate(extra_env):
                    continue
                child_version = _installed_version(child.name)
                if child_version is None:
                    return False, f"MISSING {child.name} required by {requirement.name}[{extra}]"
                if child.specifier and not child.specifier.contains(child_version, prereleases=True):
                    return False, (
                        f"MISMATCH {child.name}: installed {child_version}, "
                        f"requires {child.specifier} for {requirement.name}[{extra}]"
                    )

    return True, f"OK {requirement.name} {installed}"


def check(requirements: Iterable[Requirement]) -> tuple[bool, list[str]]:
    messages: list[str] = []
    all_ok = True
    for requirement in requirements:
        ok, message = _requirement_satisfied(requirement)
        messages.append(message)
        all_ok = all_ok and ok
    return all_ok, messages


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check COCOAID Python requirements using installed package metadata only; never accesses the network."
    )
    parser.add_argument("--file", default="requirements.txt", help="requirements file to check")
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        help="check one requirement string instead of, or in addition to, the requirements file",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    requirements: list[Requirement] = []
    if args.require:
        requirements.extend(Requirement(item) for item in args.require)
    else:
        path = Path(args.file)
        if not path.is_file():
            if not args.quiet:
                print(f"Requirements file not found: {path}")
            return 2
        requirements.extend(Requirement(line) for line in _iter_requirement_lines(path))

    ok, messages = check(requirements)
    if not args.quiet:
        for message in messages:
            print(message)
        print("LOCAL REQUIREMENTS CHECK PASSED" if ok else "LOCAL REQUIREMENTS CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
