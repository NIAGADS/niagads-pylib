from typing import Optional
from niagads.utils.string import is_bool
from pydantic import BaseModel

from niagads.utils.sys import execute_cmd


class Command(BaseModel):
    name: str
    command: list[str]
    shell: Optional[bool] = False
    required_args: Optional[list[str]] = None
    help: Optional[str]

    def _build_args_list(self, runtime_args: dict):
        args_list = []
        for key, value in runtime_args.items():
            args_list.append(f"--{key}")
            if not is_bool(value, int_as_bool=False):
                args_list.append(str(value))
        return args_list

    def _parse_runtime_args(self, runtime_args: dict) -> list[str]:
        if self.required_args is not None:
            missing = set(self.required_args) - set(runtime_args.keys())
            if missing:
                raise ValueError(f"Command '{self.name}' requires arguments: {missing}")
        return self._build_args_list(runtime_args)

    def build(self, runtime_args: dict) -> list[str]:
        return self.command + self._parse_runtime_args(runtime_args)

    def run(self, args: dict, dry_run: bool = False) -> int:
        cmd = self.build(args)
        return execute_cmd(cmd, shell=self.shell, print_cmd_only=dry_run, verbose=True)


class DockerCommand(Command):
    use_compose: bool = True

    def build(self, runtime_args: dict):
        docker_args: dict = runtime_args.pop("docker", {})
        cli_args_list = self._build_args_list(runtime_args)

        pre_run_keys = ["-f, --file, --env-file"]
        docker_pre = {k: v for k, v in docker_args.items() if k in pre_run_keys}
        docker_post = {k: v for k, v in docker_args.items() if k not in pre_run_keys}

        if self.use_compose:
            cmd = ["docker", "compose"]
            cmd += self._build_args_list(docker_pre)
            cmd += ["run", "--rm"]
            cmd += self._build_args_list(docker_post)
            cmd += self.command
            cmd += cli_args_list
            return cmd
        else:
            raise NotImplementedError("raw docker (non-compose) not yet implemented")
