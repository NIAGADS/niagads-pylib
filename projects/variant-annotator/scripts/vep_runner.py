"""VEP (Variant Effect Predictor) command runner for variant annotation."""

import os
import sys

from niagads.settings.core import CustomSettings
from niagads.subprocess_manager.runner import CommandRunner
from niagads.subprocess_manager.types import Command


class Settings(CustomSettings):
    """VEP runner configuration from environment variables."""

    HOST_VEP_CACHE_DIR: str  # cache dir on host
    PROJECT_DIR: str  # parent directory for niagads-pylib project


def main():
    """Main entry point for VEP runner."""
    try:
        settings = Settings()
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    bin_dir = os.path.join(
        settings.PROJECT_DIR, "niagads-pylib/projects/variant-annotator/bin"
    )

    commands = {
        "initialize": Command(
            name="initialize",
            command=[os.path.join(bin_dir, "fetch_vep_plugin_cache.sh")],
            help="Install VEP plugin dependencies",
        ),
        "run": Command(
            name="run",
            command=[os.path.join(bin_dir, "vep.sh")],
            shell=True,
            help="Run vep, using docker compose and GenomicsDB wrapper script.\n"
            "Expects two command args: \n"
            "`--file`: full path to the input file\n"
            "`--is-sv`: [0|1] indicating whether annotating SVs; defaults to 0\n"
            "Script saves outputs to `vep_output` directory that it will create in --file's parent (basedir).\n"
            "NOTE: for this two work, the data directory must have permisisons 777 (i.e., chmod -R a+rwx dir/)",
        ),
    }

    runner = CommandRunner(
        description="VEP variant annotation command wrapper",
        commands=commands,
    )

    print(runner.run())


if __name__ == "__main__":
    sys.exit(main())
