import argparse
import asyncio
from typing import Dict

from pipeline_manager import PipelineManager
from plugin_registry import PluginRegistry


def parse_overrides(items: list[str] | None) -> Dict[str, str]:
    """
    Parse KEY=VALUE pairs from CLI into dict.
    """
    out: Dict[str, str] = {}
    if not items:
        return out
    for it in items:
        if "=" not in it:
            raise ValueError(f"Invalid override '{it}', expected KEY=VALUE")
        k, v = it.split("=", 1)
        out[k] = v
    return out


def parse_resume_param(s: str | None):
    """
    Parse resume parameter: "line=12345" or "id=ABC".
    """
    if not s:
        return None
    if "=" not in s:
        raise ValueError("--resume-param must be 'line=N' or 'id=VALUE'")
    k, v = s.split("=", 1)
    if k == "line":
        return {"line": int(v)}
    if k == "id":
        return {"id": v}
    raise ValueError("--resume-param must be 'line=N' or 'id=VALUE'")


def main():
    p = argparse.ArgumentParser(description="ETL Pipeline Manager (dry-run by default)")
    p.add_argument("config", help="Path to pipeline config JSON")
    p.add_argument(
        "--commit",
        action="store_true",
        help="Actually commit changes (default: dry-run)",
    )
    p.add_argument(
        "--only",
        nargs="*",
        help="Run only specified Stage or Stage.Task (space-separated)",
    )
    p.add_argument(
        "--skip", nargs="*", help="Skip specified Stage or Stage.Task (space-separated)"
    )
    p.add_argument(
        "--resume-step",
        type=str,
        help="Resume from Stage or Stage.Task (does NOT imply --only)",
    )
    p.add_argument(
        "--resume-param", type=str, help="Resume parameter: 'line=N' or 'id=VALUE'"
    )
    p.add_argument("--log-file", type=str, help="Override plugin log_file for this run")
    p.add_argument(
        "--param",
        dest="overrides",
        nargs="*",
        help="Pipeline param overrides: KEY=VALUE",
    )
    p.add_argument(
        "--plan-only", action="store_true", help="Print plan and exit (no execution)"
    )
    # Registry introspection
    p.add_argument(
        "--list-plugins", action="store_true", help="List registered plugins and exit"
    )
    p.add_argument(
        "--describe-plugin",
        type=str,
        help="Print parameter schema/metadata for a plugin and exit",
    )

    args = p.parse_args()

    if args.list_plugins:
        for name in PluginRegistry.list_plugins():
            print(name)
        return

    if args.describe_plugin:
        meta = PluginRegistry.describe(args.describe_plugin)
        import json

        print(json.dumps(meta, indent=2))
        return

    overrides = parse_overrides(args.overrides)
    resume_param = parse_resume_param(args.resume_param)

    mgr = PipelineManager(args.config)
    ok = asyncio.run(
        mgr.run(
            commit=args.commit,
            only=args.only,
            skip=args.skip,
            resume_step=args.resume_step,
            resume_param=resume_param,
            log_file_override=args.log_file,
            overrides=overrides,
            print_only=args.plan_only,
        )
    )
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
