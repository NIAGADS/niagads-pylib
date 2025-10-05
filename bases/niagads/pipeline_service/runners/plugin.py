import asyncio
import sys
from typing import Union, get_args, get_origin

from niagads.arg_parser.core import (
    case_insensitive_enum_type,
    comma_separated_list,
    json_type,
)
from niagads.enums.common import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.config import ETLMode
from niagads.etl.pipeline.config import PipelineSettings
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.utils import register_plugins
from pydantic import BaseModel


class PluginArgDef(BaseModel):
    arg_name: str
    arg_type: type
    default: any
    help: str
    required: bool


class PluginRunner:
    """
    Encapsulates logic for running a single ETL plugin from the command line.
    Dynamically adds plugin params to the argument parser.
    """

    def __init__(self, plugin_name, parser, mode):
        try:
            register_plugins(
                project=PipelineSettings.from_env().PROJECT,
                packages=PipelineSettings.from_env().PLUGIN_PACKAGES,
            )
            self._plugin_cls = PluginRegistry.get(plugin_name)
        except KeyError:
            print(
                f"Error: Plugin '{plugin_name}' not found in registry.\n"
                f"Available plugins:\n {'\n'.join(PluginRegistry.list_plugins())}"
            )
            sys.exit(1)
        try:
            self._param_fields = self._plugin_cls.parameter_model().model_fields
        except Exception as e:
            print(f"Error accessing parameter model for plugin '{plugin_name}': {e}")
            sys.exit(1)
        self._mode = mode
        self._params = {}
        self._parser = parser  # store parser for usage printing
        self._register_plugin_args()

    def print_plugin_help(self):
        print(f"\nPLUGIN: '{self._plugin_cls.__name__}'")
        print(f"\nDESCRIPTION:\n {self._plugin_cls.description}\n")
        self._parser.print_help()

    @staticmethod
    def _resolve_arg_type(arg_type):
        """
        Resolves the concrete type and required status for an argument type.

        Handles typing.Optional and Union types, returning the base type and
        whether the argument is required (True if not Optional, False otherwise).
        """

        origin = get_origin(arg_type)
        required = True
        resolved_type = arg_type
        if origin is Union:
            args = get_args(arg_type)
            if type(None) in args:
                required = False
            # Remove NoneType from Union (i.e., Optional)
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                resolved_type = non_none_args[0]
            else:
                resolved_type = str  # fallback
        return resolved_type, required

    def _add_plugin_arg(self, arg: PluginArgDef):
        """
        Adds an argument to the parser using a PluginArgInfo object.

        Args:
            arg_info: PluginArgInfo instance containing argument details.
        """
        # Use description to select custom types for
        # parameters that expect to do conversions from strings
        if "comma-separated" in arg.help.lower():
            self._parser.add_argument(
                arg.arg_name,
                type=comma_separated_list,
                default=arg.default,
                required=arg.required,
                help=arg.help,
            )
        elif "json" in arg.help.lower():
            self._parser.add_argument(
                arg.arg_name,
                type=json_type,
                default=arg.default,
                required=arg.required,
                help=arg.help,
            )
        elif issubclass(arg.arg_type, CaseInsensitiveEnum):
            self._parser.add_argument(
                arg.arg_name,
                type=case_insensitive_enum_type(arg.arg_type),
                default=arg.default,
                required=arg.required,
                help=arg.help,
            )
        elif arg.arg_type is bool:
            if arg.default is True:
                self._parser.add_argument(
                    arg.arg_name, action="store_false", help=arg.help
                )
            else:
                self._parser.add_argument(
                    arg.arg_name, action="store_true", help=arg.help
                )
        else:
            self._parser.add_argument(
                arg.arg_name,
                type=arg.arg_type,
                default=arg.default,
                required=arg.required,
                help=arg.help,
            )

    def _register_plugin_args(self):
        for field_name, field in self._param_fields.items():
            arg_type, required = self._resolve_arg_type(field.annotation)
            arg_info = PluginArgDef(
                arg_name=f"--{field_name.replace('_', '-')}",
                arg_type=arg_type,
                default=field.default,
                help=str(getattr(field, "description", "")),
                required=required,
            )
            self._add_plugin_arg(arg_info)

    def _set_runtime_parameters(self):
        """
        Parses command-line arguments and sets plugin runtime parameters.

        Iterates over all parameter fields, extracting their values from the parsed
        arguments and storing them in the internal params dictionary for plugin execution.
        """
        args = self._parser.parse_args()
        for field_name in self._param_fields:
            value = getattr(args, field_name, None)
            if value is not None:
                self._params[field_name] = value

    async def run(self):
        self._set_runtime_parameters()
        try:
            plugin: AbstractBasePlugin = self._plugin_cls(params=self._params)
        except Exception as e:
            print(f"Error instantiating plugin '{self._plugin_cls.__name__}': {e}")
            sys.exit(1)
        try:
            status = await plugin.run(mode=self._mode)
        except Exception as e:
            print(f"Error running plugin '{self._plugin_cls.__name__}': {e}")
            sys.exit(1)
        if status == ProcessStatus.SUCCESS:
            print(f"Plugin '{self._plugin_cls.__name__}' completed successfully.")
        else:
            print(f"Plugin '{self._plugin_cls.__name__}' failed.")
            sys.exit(1)


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
        # parser.print_help()
        runner.print_plugin_help()
        sys.exit(0)

    await runner.run()


def run_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
