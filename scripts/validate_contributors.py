
import os
import re
import subprocess
import sys
from pathlib import PurePosixPath


USERNAME_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$"
)


def fail(message):
    print(f"::error::{message}")
    sys.exit(1)


def git(*args):
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True
    )
    return result.stdout


def parse_front_matter(content):
    lines = content.splitlines()

    if not lines or lines[0].strip() != "---":
        fail("Profile must start with YAML front matter.")

    try:
        end = lines.index("---", 1)
    except ValueError:
        fail("Missing closing YAML front matter delimiter.")

    fields = {}

    for line in lines[1:end]:
        if ":" not in line:
            fail(f"Invalid front matter line: {line}")

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip('"').strip("'")

        if key in fields:
            fail(f"Duplicate field: {key}")

        fields[key] = value

    return fields


def main():
    base = os.environ.get("BASE_REF")
    head = os.environ.get("HEAD_REF")

    if not base or not head:
        fail("Missing BASE_REF or HEAD_REF.")

    changed = git(
        "diff",
        "--name-status",
        f"{base}...{head}"
    ).splitlines()

    profiles = []
    invalid = []

    for entry in changed:
        parts = entry.split("\t")
        status = parts[0]
        path = parts[-1]

        if status.startswith("R"):
            invalid.append(path)
            continue

        if (
            status in ("A", "M")
            and path.startswith("contributors/")
            and path.endswith(".md")
        ):
            profiles.append(path)
        else:
            invalid.append(path)

    if invalid:
        fail(
            "Only contributor Markdown profiles may be changed. "
            "Invalid files: " + ", ".join(invalid)
        )

    if len(profiles) != 1:
        fail(
            f"Expected exactly one contributor profile, "
            f"found {len(profiles)}."
        )

    path = profiles[0]

    if len(PurePosixPath(path).parts) != 2:
        fail("Profiles must be directly inside contributors/.")

    username = PurePosixPath(path).stem

    if not USERNAME_RE.fullmatch(username):
        fail("Invalid GitHub username in filename.")

    content = git("show", f"{head}:{path}")

    fields = parse_front_matter(content)

    if not fields.get("name"):
        fail("Missing name field.")

    if not fields.get("github"):
        fail("Missing github field.")

    if fields["github"].casefold() != username.casefold():
        fail("GitHub username must match the filename.")

    if "## About me" not in content:
        fail("Missing About me section.")

    about = content.split("## About me", 1)[1].strip()

    if len(about) < 20:
        fail("Your introduction must contain at least 20 characters.")

    print(f"Successfully validated contributor: {username}")


if __name__ == "__main__":
    main()
