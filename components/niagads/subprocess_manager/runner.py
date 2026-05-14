import argparse
from niagads.arg_parser.core import json_type
from niagads.common.core import ComponentBaseMixin
from niagads.subprocess_manager.types import Command


class CommandRunner(ComponentBaseMixin):
    def __init__(
        self,
        description: str,
        commands: dict[str, Command] = None,
        debug: bool = False,
        verbose: bool = False,
        initialize_logger: bool = True,
    ):
        super().__init__(debug, verbose, initialize_logger)
        self._description = description
        self._commands = commands or {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def execute(
        self,
        name: str,
        command_args: dict,
        dry_run: bool = False,
    ) -> int:
        try:
            cmd = self._commands[name]
        except KeyError:
            raise ValueError(f"Unknown mode: {name}")

        return cmd.run(command_args, dry_run=dry_run)

    @property
    def choices(self) -> list[str]:
        return sorted(self._commands.keys())

    def run(self):
        parser = argparse.ArgumentParser(description=self._description)

        parser.add_argument(
            "--list",
            action="store_true",
            help="print help for each command",
        )

        parser.add_argument(
            "--mode",
            choices=self.choices,
        )

        parser.add_argument("--dry-run", action="store_true")

        parser.add_argument(
            "--cmd-args",
            type=json_type,
            help="dictionary of additional args to be passed on to the command",
        )

        args = parser.parse_args()

        if args.list:
            for cmd in self._commands.keys():
                print(f"\n----- mode: {cmd} -----\n{self._commands[cmd].help}")
            return 0

        if not args.mode:
            parser.error("--mode is required when not using --list")

        return self.execute(args.mode, args.cmd_args, dry_run=args.dry_run)
