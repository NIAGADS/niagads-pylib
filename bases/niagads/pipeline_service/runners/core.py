import json

from niagads.arg_parser.core import (
    case_insensitive_enum_type,
    comma_separated_list,
    json_type,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.pipeline.manager import PipelineManager, ETLMode
from niagads.enums.common import ProcessStatus


class PipelineRunner:
    """
    Encapsulates the ETL Pipeline Manager runner logic for script execution.
    """

    def __init__(self, args):
        self.__args = args

    async def run(self):
        """
        Execute the pipeline runner with parsed arguments (async).

        Returns:
            None
        """
        args = self.__args

        if args.list_plugins:
            for name in PluginRegistry.list_plugins():
                print(name)
            return

        if args.describe_plugin:
            meta = PluginRegistry.describe(args.describe_plugin)
            print(json.dumps(meta, indent=2))
            return

        # resume_checkpoint = self.parse_resume_param(args.resume_param)
        manager = PipelineManager(args.config)

        # Set filters from CLI args
        if args.only:
            manager.only = args.only
        if args.skip:
            manager.skip = args.skip
        if args.resume_at:
            manager.resume_point = args.resume_at
        if args.resume_checkpoint:
            manager.checkpoint = args.resume_checkpoint

        if args.plan_only:
            manager.print_plan()
            return

        status = await manager.run(
            mode=args.mode,
            parameter_overrides=args.parameter_overrides,
        )

        if status != ProcessStatus.SUCCESS:
            raise SystemExit(1)


async def main():
    """
    Entry point for running the PipelineRunner as a script.

    Returns:
        None
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="ETL Pipeline Manager (dry-run by default)"
    )
    parser.add_argument("config", help="Path to pipeline config JSON")
    parser.add_argument(
        "--mode",
        type=case_insensitive_enum_type(ETLMode),
        default=ETLMode.DRY_RUN,
        help="ETL execution mode: COMMIT (commit changes), NON_COMMIT (rollback at end), DRY_RUN (simulate only)",
    )
    parser.add_argument(
        "--only",
        type=comma_separated_list,
        help="Run only specified Stage or Stage.Task (comma-separated)",
    )
    parser.add_argument(
        "--skip",
        type=comma_separated_list,
        help="Skip specified Stage or Stage.Task (comma-separated)",
    )
    parser.add_argument(
        "--resume-at",
        type=str,
        help="Resume from Stage or Stage.Task (does NOT imply --only)",
    )
    parser.add_argument(
        "--resume-checkpoint",
        type=str,
        help="Resume checkpoint for the resume-at task: 'line=N' or 'id=VALUE'",
    )
    parser.add_argument("--log-file", type=str, help="pipeline log file name")
    parser.add_argument(
        "--param",
        dest="parameter_overrides",
        type=json_type,
        help="Pipeline param overrides as JSON string",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="print plan and exit (no execution)",
    )
    parser.add_argument(
        "--list-plugins",
        action="store_true",
        help="List registered plugins and exit",
    )
    parser.add_argument(
        "--describe-plugin",
        type=str,
        help="Print parameter schema/metadata for a plugin and exit",
    )

    args = parser.parse_args()
    runner = PipelineRunner(args)

    await runner.run()


def run_main():
    """wrapper necessary so that the main coroutine gets correctly awaited"""
    import asyncio

    asyncio.run(main())


if __name__ == "__main__":
    run_main()
