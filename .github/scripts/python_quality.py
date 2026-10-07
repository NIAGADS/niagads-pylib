"""Validate tracked Python sources and report or apply workspace formatting."""

import argparse
import os
import subprocess
import sys
import tokenize
from pathlib import Path


def main() -> int:
    """Run syntax checks, advisory import checks, and formatting in that order."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    files = sorted(
        path
        for path in subprocess.check_output(["git", "ls-files", "-z"])
        .decode()
        .split("\0")
        if path.endswith(".py")
    )
    log = []

    def record(message: str) -> None:
        print(message, flush=True)
        log.append(message)

    def run(command: list[str]) -> int:
        result = subprocess.run(command, capture_output=True, text=True)
        record(result.stdout + result.stderr)
        return result.returncode

    try:
        record(f"Syntax validation: {len(files)} tracked Python files.")
        invalid = False
        for name in files:
            try:
                with tokenize.open(name) as source:
                    compile(source.read(), name, "exec")
            except SyntaxError as error:
                invalid = True
                record(f"ERROR {name}:{error.lineno}:{error.offset}: {error.msg}")
                if error.text:
                    record(error.text.rstrip())
            except (OSError, UnicodeError) as error:
                invalid = True
                record(f"ERROR {name}: {error}")
        record("Unused imports (warnings only; no fixes):")
        warning_status = 0
        if files:
            warning_status = run(
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "--isolated",
                    "--select",
                    "F401",
                    "--no-fix",
                    "--",
                    *files,
                ]
            )
        if invalid or warning_status not in (0, 1):
            record("FAILED: validation errors; formatting was not applied.")
            return 1
        record("Syntax validation passed.")
        targets = [
            name
            for name in files
            if not name.startswith("development/")
            and "/alembic/versions/" not in f"/{name}"
        ]
        record(
            f"Formatting {'check' if args.check else 'apply'}: {len(targets)} files."
        )
        status = 0
        if targets:
            isort = [
                sys.executable,
                "-m",
                "isort",
                "--settings-path",
                "pyproject.toml",
                "--filter-files",
            ]
            black = [sys.executable, "-m", "black", "--config", "pyproject.toml"]
            if args.check:
                isort += ["--check-only", "--diff"]
                black += ["--check", "--diff"]
            status |= run([*isort, "--", *targets])
            if not status or args.check:
                status |= run([*black, "--", *targets])
        record(
            "FAILED: formatting errors or changes required."
            if status
            else "PASSED: unused imports are advisory only."
        )
        return int(bool(status))
    except (OSError, subprocess.SubprocessError) as error:
        record(f"FAILED: {error}")
        return 1
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text("\n".join(log) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
