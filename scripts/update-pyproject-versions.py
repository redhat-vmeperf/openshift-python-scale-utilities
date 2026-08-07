# scripts/update-pyproject-versions.py
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
UV_LOCK = REPO_ROOT / "uv.lock"

VERSIONED_DEP_RE = re.compile(r'"([a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?)\s*[>~]=\s*(\d+(?:\.\d+)*)"')
BARE_DEP_RE = re.compile(r'"([a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?)"')


def read_lock_versions():
    with open(UV_LOCK, "rb") as f:  # noqa: FCN001
        lock = tomllib.load(f)  # noqa: FCN001
    return {pkg["name"]: pkg["version"] for pkg in lock.get("package", [])}


def trim_version(*, resolved, depth):
    parts = resolved.split(".")
    return ".".join(parts[:depth])


def make_versioned_replacer(lock_versions):
    def replace(match):
        pkg_display = match.group(index=1)
        old_ver = match.group(index=2)
        depth = len(old_ver.split("."))
        resolved = lock_versions.get(pkg_display.lower())
        if resolved is None:
            return match.group(index=0)
        new_ver = trim_version(resolved=resolved, depth=depth)
        return f'"{pkg_display}~={new_ver}"'

    return replace


def add_bare_versions(*, text, lock_versions):
    in_deps = False

    def replace_bare(match):
        if not in_deps:
            return match.group(index=0)
        pkg_display = match.group(index=1)
        resolved = lock_versions.get(pkg_display.lower())
        if resolved is None:
            return match.group(index=0)
        depth = min(len(resolved.split(".")), 3)
        new_ver = trim_version(resolved=resolved, depth=depth)
        return f'"{pkg_display}~={new_ver}"'

    lines = text.splitlines(keepends=True)
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("dependencies") or stripped.startswith("dev"):
            in_deps = True
        elif stripped.startswith("[") and not stripped.startswith("[["):
            if "dependencies" not in stripped.lower():
                in_deps = False

        if in_deps:
            line = BARE_DEP_RE.sub(repl=replace_bare, string=line)
        result.append(line)
    return "".join(result)


def process_pyproject():
    text = PYPROJECT.read_text()
    lock_versions = read_lock_versions()

    text = VERSIONED_DEP_RE.sub(repl=make_versioned_replacer(lock_versions), string=text)
    text = add_bare_versions(text=text, lock_versions=lock_versions)

    PYPROJECT.write_text(text)  # noqa: FCN001


if __name__ == "__main__":
    process_pyproject()
    print("Updated pyproject.toml specifiers from uv.lock")
