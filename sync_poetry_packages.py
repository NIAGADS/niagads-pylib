#!/usr/bin/env python3
"""Update Poetry packages from Polylith brick mappings in a TOML file."""

import argparse
import json
import re
import tomllib
from pathlib import Path, PurePosixPath


class PoetryPackageSync:
    """Keep Poetry package declarations aligned with Polylith bricks."""

    def run(self, path: Path) -> None:
        """Replace the package list using the file's current brick mappings.

        Args:
            path (Path): TOML file to update in place.
        """
        text = path.read_text(encoding="utf-8")
        document = tomllib.loads(text)
        bricks = document["tool"]["polylith"]["bricks"]
        entries = []

        for source, target in bricks.items():
            source_path = PurePosixPath(source)
            target_path = PurePosixPath(target)
            if source_path.parts[-len(target_path.parts) :] != target_path.parts:
                raise ValueError(f"Brick source {source!r} does not end in {target!r}")

            parent = str(source_path.parents[len(target_path.parts) - 1])
            entries.append(
                f"    {{ include = {json.dumps(target)}, "
                f"from = {json.dumps(parent)} }},\n"
            )

        packages = "packages = [\n" + "".join(entries) + "]\n"
        headers = list(re.finditer(r"(?m)^\[([^\]\n]+)\][ \t]*(?:#[^\n]*)?$", text))
        for index, header in enumerate(headers):
            if header.group(1) != "tool.poetry":
                continue
            start = header.end()
            end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
            section = text[start:end]
            assignment = re.search(r"(?m)^[ \t]*packages[ \t]*=", section)
            if assignment is None:
                section = "\n" + packages + section
            else:
                value_start = assignment.start()
                value_end = value_start
                for line in section[value_start:].splitlines(keepends=True):
                    value_end += len(line)
                    try:
                        tomllib.loads(section[value_start:value_end])
                    except tomllib.TOMLDecodeError:
                        continue
                    break
                section = section[:value_start] + packages + section[value_end:]
            text = text[:start] + section + text[end:]
            break
        else:
            text = text.rstrip() + "\n\n[tool.poetry]\n" + packages

        tomllib.loads(text)
        path.write_text(text, encoding="utf-8")


def main() -> None:
    """Parse the target file and synchronize its Poetry package list."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toml", type=Path, help="TOML file to update in place")
    args = parser.parse_args()
    PoetryPackageSync().run(args.toml)


if __name__ == "__main__":
    main()
