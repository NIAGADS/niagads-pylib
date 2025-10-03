import asyncio
import sys

from niagads.arg_parser.core import (
    json_type,
    case_insensitive_enum_type,
    comma_separated_list,
)
from niagads.enums.core import CaseInsensitiveEnum
from niagads.pipeline.plugins.registry import PluginRegistry
from niagads.pipeline.plugins.base import AbstractBasePlugin, BasePluginParams
from niagads.pipeline.manager import ETLMode
from niagads.enums.common import ProcessStatus

# TODO - register plugin before getting; see pipeline manager


class PluginRunner:
    """
    Encapsulates logic for running a single ETL plugin from the command line.
    Dynamically adds plugin params to the argument parser.
    """

    def __init__(self, plugin_name, parser, mode):
        self.__plugin_cls = self._validate_plugin(plugin_name)
        self.__param_fields = self.__plugin_cls.parameter_model().model_fields
        self.__mode = mode
        self.__params = {}
        self.__register_plugin_args(parser)

    def print_usage(self):
        print(f"\nPLUGIN: '{self.__plugin_cls.__name__}'")
        print(f"\nDESCRIPTION:\n {self.__plugin_cls.description}\n")
        print(f"\nUSAGE:\n")
        for field_name, field in self.__param_fields.items():
            arg_name = (f"--{field_name.replace('_', '-')}",)
            arg_type = field.annotation
            desc = str(getattr(field, "description", ""))
            default = field.default
            print(f"  {arg_name} ({arg_type.__name__})  Default: {default}  {desc}")
        sys.exit(0)

    def _validate_plugin(self, plugin_name):
        plugin_cls = PluginRegistry.get(plugin_name)
        if not plugin_cls:
            print(f"Plugin '{plugin_name}' not found.")
            raise SystemExit(1)
        return plugin_cls

    @staticmethod
    def add_plugin_arg(parser, arg_name, arg_type, default, desc):
        desc_lower = desc.lower() if desc else ""
        # Use description to select custom types for
        # parameters that expect to do conversions from strings
        if "comma-separated" in desc_lower:
            parser.add_argument(
                arg_name,
                type=comma_separated_list,
                default=default,
                required=False,
                help=desc,
            )
        elif "json" in desc_lower:
            parser.add_argument(
                arg_name,
                type=json_type,
                default=default,
                required=False,
                help=desc,
            )
        elif issubclass(arg_type, CaseInsensitiveEnum):
            parser.add_argument(
                arg_name,
                type=case_insensitive_enum_type(arg_type),
                default=default,
                required=False,
                help=desc,
            )
        elif arg_type is bool:
            if default is True:
                parser.add_argument(arg_name, action="store_false", help=desc)
            else:
                parser.add_argument(arg_name, action="store_true", help=desc)
        else:
            parser.add_argument(
                arg_name,
                type=arg_type,
                default=default,
                required=False,
                help=desc,
            )

    def __register_plugin_args(self, parser):
        for field_name, field in self.__param_fields.items():
            arg_name = f"--{field_name.replace('_', '-')}"
            arg_type = field.annotation
            default = field.default
            desc = str(getattr(field, "description", ""))
            self.add_plugin_arg(parser, arg_name, arg_type, default, desc)

    def resolve_params(self, args):
        for field_name in self.__param_fields:
            value = getattr(args, field_name, None)
            if value is not None:
                self.__params[field_name] = value

    async def run(self):
        plugin: AbstractBasePlugin = self.__plugin_cls(params=self.__params)
        status = await plugin.run(mode=self.__mode)
        if status == ProcessStatus.SUCCESS:
            print(f"Plugin '{self.__plugin_cls.__name__}' completed successfully.")
        else:
            print(f"Plugin '{self.__plugin_cls.__name__}' failed.")
            raise SystemExit(1)


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run a single ETL plugin standalone",
        add_help=False,
        allow_abbrev=False,
    )
    parser.add_argument("--plugin", type=str, help="Plugin name to run")
    parser.add_argument(
        "--help", action="store_true", help="Show help message and exit"
    )
    parser.add_argument(
        "--mode",
        type=case_insensitive_enum_type(ETLMode),
        default=ETLMode.DRY_RUN,
        help="ETL execution mode: COMMIT (commit changes), NON_COMMIT (rollback at end), DRY_RUN (simulate only). Default: %(default)s",
    )

    # Parse known args to get plugin name and help
    known_args, remaining = parser.parse_known_args()
    if known_args.help and not known_args.plugin:
        parser.print_help()
        sys.exit(0)

    # Instantiate runner and dynamically add plugin params
    runner = PluginRunner(known_args.plugin, parser, known_args.mode)
    if known_args.help:  # print plugin help
        parser.print_help()
        runner.print_usage()

    # Parse all args (now with plugin params)
    args = parser.parse_args()
    runner.resolve_params(args)
    await runner.run()


def run_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
