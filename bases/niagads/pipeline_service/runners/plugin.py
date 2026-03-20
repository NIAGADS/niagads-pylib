import asyncio
import os
import sys
from typing import Any, Optional, Union, get_args, get_origin

from niagads.arg_parser.core import (
    case_insensitive_enum_type,
    comma_separated_list,
    json_type,
)
from niagads.common.core import ComponentBaseMixin
from niagads.common.types import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.etl.pipeline.config import PipelineSettings
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.utils import register_plugins
from pydantic import BaseModel, ValidationError

# FIXME: plugin usage not indicating required arguments.  May have something do with default=None
# may need to leave off default altogether when generating arguments if they are required
# to get usage to print correctly

os.environ["PYDANTIC_ERRORS_OMIT_URL"] = "1"


class PluginArgDef(BaseModel):
    arg_name: str
    arg_type: Any
    default: Any
    help: str
    required: Optional[bool]


class PluginRunner(ComponentBaseMixin):
    """
    Encapsulates logic for running a single ETL plugin from the command line.
    Dynamically adds plugin params to the argument parser.
    """

    def __init__(
        self,
        plugin_name,
        argument_parser,
        list_only: bool = False,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        try:
            register_plugins(
                project=PipelineSettings.from_env().PROJECT,
                packages=PipelineSettings.from_env().PLUGIN_PACKAGES,
            )
            if list_only:
                available_plugins = "\n".join(PluginRegistry.list_plugins())
                print(f"Available plugins:\n{available_plugins}")
                sys.exit(0)

            self._plugin_cls = PluginRegistry.get(plugin_name)
        except ValidationError as err:
            if self._debug:
                self.logger.exception("ValidationError loading plugins")
            else:
                self.logger.error(f"ValidationError loading plugins: {err}")
        except KeyError:
            available_plugins = "\n".join(PluginRegistry.list_plugins())
            msg = (
                f"Plugin '{plugin_name}' not found in registry.\n"
                f"Available plugins:\n{available_plugins}"
            )
            self.logger.error(msg)
        try:
            self.__plugin_metadata = PluginRegistry.get_metadata(plugin_name)
            self._param_fields = self.__plugin_metadata.parameter_model.model_fields
        except Exception as e:
            msg = f"Error accessing parameter model for plugin '{plugin_name}'"
            if self._debug:
                self.logger.exception(msg)
            else:
                self.logger.error(f"{msg}: {e}")

        self._params = {}
        self._argument_parser = argument_parser  # store parser for usage printing
        self._register_plugin_args()

    def print_plugin_help(self):
        print(f"\nPLUGIN: '{self._plugin_cls.__name__}'")
        print(f"\nDESCRIPTION:\n {self.__plugin_metadata.description}\n")
        self._argument_parser.print_help()

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
            self._argument_parser.add_argument(
                arg.arg_name,
                type=comma_separated_list,
                default=arg.default,
                required=arg.required,
                help=arg.help,
            )
        elif "json" in arg.help.lower():
            self._argument_parser.add_argument(
                arg.arg_name,
                type=json_type,
                default=arg.default,
                required=arg.required,
                help=arg.help,
            )
        elif issubclass(arg.arg_type, CaseInsensitiveEnum):
            self._argument_parser.add_argument(
                arg.arg_name,
                type=case_insensitive_enum_type(arg.arg_type),
                default=arg.default,
                required=arg.required,
                help=arg.help,
            )
        elif arg.arg_type is bool:
            if arg.default is True:
                self._argument_parser.add_argument(
                    arg.arg_name, action="store_false", help=arg.help
                )
            else:
                self._argument_parser.add_argument(
                    arg.arg_name, action="store_true", help=arg.help
                )
        else:
            self._argument_parser.add_argument(
                arg.arg_name,
                type=arg.arg_type,
                default=arg.default,
                required=arg.required,
                help=arg.help,
            )

    def _register_plugin_args(self):
        for field_name, field in self._param_fields.items():
            if field.exclude:  # i.e. bypass parent class parameters
                continue  # skip field

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
        args = self._argument_parser.parse_args()
        for field_name in self._param_fields:
            value = getattr(args, field_name, None)
            if value is not None:
                self._params[field_name] = value

    async def run(self):
        self._set_runtime_parameters()
        try:
            plugin: AbstractBasePlugin = self._plugin_cls(
                params=self._params, debug=self._debug, verbose=self._verbose
            )
        except Exception as e:
            msg = f"Error instantiating plugin '{self._plugin_cls.__name__}'"
            if self._debug:
                self.logger.exception(msg)
            else:
                self.logger.error(f"{msg}: {e}")
        try:
            status = await plugin.run()
        except Exception as e:
            msg = f"Error running plugin '{self._plugin_cls.__name__}'"
            if self._debug:
                self.logger.exception(msg)
            else:
                self.logger.error(f"{msg}: {e}")
        if status == ProcessStatus.SUCCESS:
            self.logger.info(
                f"Plugin '{self._plugin_cls.__name__}' completed successfully."
            )
        else:
            msg = f"Plugin '{self._plugin_cls.__name__}' failed."
            if self._debug:
                self.logger.exception(msg)
            else:
                self.logger.error(f"{msg}: {e}")


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run a single ETL plugin standalone",
        add_help=False,
        allow_abbrev=False,
    )
    parser.add_argument("--plugin", type=str, help="Plugin name to run")
    parser.add_argument("--list", action="store_true", help="List registered plugins")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")
    parser.add_argument(
        "--help", action="store_true", help="Show help message and exit"
    )

    # Parse known args to get plugin name and help
    known_args, remaining = parser.parse_known_args()
    if known_args.help and not known_args.plugin:
        parser.print_help()
        sys.exit(0)

    # Instantiate runner and dynamically add plugin params
    runner = PluginRunner(
        known_args.plugin,
        parser,
        known_args.list,
        debug=known_args.debug,
        verbose=known_args.verbose,
    )
    if known_args.help:  # print plugin help
        # parser.print_help()
        runner.print_plugin_help()
        sys.exit(0)

    await runner.run()


def run_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
