import asyncio
from enum import auto
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from niagads.enums.core import CaseInsensitiveEnum
from niagads.pipeline.config import PipelineConfig, StageConfig, TaskConfig
from niagads.pipeline.plugins.registry import PluginRegistry
from niagads.utils.dict import deep_merge


class ETLMode(CaseInsensitiveEnum):
    """
    ETL execution mode:
    - COMMIT: Perform ETL and commit all changes to the database.
    - NON_COMMIT: Perform ETL but roll back all changes at the end (no commit).
    - DRY_RUN: Simulate ETL, do not write or commit any changes to the database.
    """

    COMMIT = auto()
    NON_COMMIT = auto()
    DRY_RUN = auto()


class PipelineManager:
    """
    Pipeline executor with:
        - Stage barrier semantics (stages run in order, next waits for previous)
        - Async parallel stage execution (max_concurrency controls concurrency)
        - Task retries and per-task timeouts
        - CLI overrides for params, resume_from, only/skip filters, plan-only output
        - Dry-run by default; --commit enables writes
    """

    def __init__(self, config_path: str):
        """
        Initialize the PipelineManager with a pipeline configuration file.

        Args:
            config_path (str): Path to the pipeline configuration JSON file.
        """
        with open(config_path, "r") as f:
            cfg = json.load(f)
        self.__config = PipelineConfig(**cfg)

    # ---- planning & filtering ----
    def _select_stages_tasks(
        self,
        only: Optional[List[str]] = None,
        skip: Optional[List[str]] = None,
        resume_step: Optional[str] = None,
    ) -> List[Tuple[StageConfig, List[TaskConfig]]]:
        """
        Filter and select stages and tasks to execute based on filters.

        Args:
            only (Optional[List[str]]): List of "Stage.Task" or "Stage" to include.
            skip (Optional[List[str]]): List of "Stage.Task" or "Stage" to exclude.
            resume_step (Optional[str]): "Stage" or "Stage.Task" to start from (earlier ones skipped).

        Returns:
            List[Tuple[StageConfig, List[TaskConfig]]]: List of (stage, tasks) tuples to execute.
        """

        # normalize filters to sets of tuples (stage, task|None)
        def normalize(items: Optional[List[str]]) -> set[Tuple[str, Optional[str]]]:
            s: set[Tuple[str, Optional[str]]] = set()
            if not items:
                return s
            for it in items:
                parts = it.split(".", 1)
                if len(parts) == 1:
                    s.add((parts[0], None))
                else:
                    s.add((parts[0], parts[1]))
            return s

        only_set = normalize(only)
        skip_set = normalize(skip)

        # figure resume cutoff
        resume_stage = None
        resume_task = None
        if resume_step:
            p = resume_step.split(".", 1)
            resume_stage = p[0]
            resume_task = p[1] if len(p) > 1 else None

        plan: List[Tuple[StageConfig, List[TaskConfig]]] = []
        for stage in self.__config.stages:
            if stage.skip or stage.deprecated:
                continue

            # skip until resume stage
            if resume_stage:
                if stage.name != resume_stage:
                    continue

            # pick tasks
            stage_tasks: List[TaskConfig] = []
            for task in stage.tasks:
                if task.skip or task.deprecated:
                    continue

                # apply only filter
                if only_set:
                    if (stage.name, None) not in only_set and (
                        stage.name,
                        task.name,
                    ) not in only_set:
                        continue
                # apply skip filter
                if (stage.name, None) in skip_set or (
                    stage.name,
                    task.name,
                ) in skip_set:
                    continue

                # if resuming from a specific task, skip earlier tasks in this stage
                if (
                    resume_stage == stage.name
                    and resume_task
                    and task.name != resume_task
                ):
                    # skip until we hit the named task
                    # once we add the named task below -> clear resume_stage/task to include rest of this stage
                    pass
                stage_tasks.append(task)
                if (
                    resume_stage == stage.name
                    and resume_task
                    and task.name == resume_task
                ):
                    # include this task and from now on process rest normally:
                    resume_stage = None
                    resume_task = None

            if stage_tasks:
                plan.append((stage, stage_tasks))
            # if resuming at a stage (no task), after first match, clear the flag:
            if resume_stage == stage.name and resume_task is None:
                resume_stage = None

        return plan

    def print_plan(self, only=None, skip=None, resume_step=None):
        """
        Print a human-readable plan of the pipeline stages and tasks to be executed.

        Args:
            only (Optional[List[str]]): List of "Stage.Task" or "Stage" to include.
            skip (Optional[List[str]]): List of "Stage.Task" or "Stage" to exclude.
            resume_step (Optional[str]): "Stage" or "Stage.Task" to start from.

        Returns:
            str: The formatted plan as a string.
        """
        plan = self._select_stages_tasks(only=only, skip=skip, resume_step=resume_step)
        out = []
        for stage, tasks in plan:
            out.append(
                f"[Stage] {stage.name}  mode={stage.parallel_mode}  max={stage.max_concurrency or '-'}"
            )
            for t in tasks:
                out.append(
                    f"  - {t.name}  type={t.type}  plugin={t.plugin or '-'}  timeout={t.timeout_seconds or '-'}  retries={t.retries}"
                )
        return "\n".join(out)

    # ---- task executors ----
    async def _run_plugin_task(
        self,
        stage: StageConfig,
        task: TaskConfig,
        mode: ETLMode,
        pipeline_scope: Dict[str, Any],
        resume_param: Optional[Dict[str, Any]],
        log_file_override: Optional[str],
    ) -> bool:
        """
        Run a plugin task with retries and timeout, applying parameter interpolation and overrides.

        Args:
            stage (StageConfig): The stage configuration.
            task (TaskConfig): The task configuration.
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).
            pipeline_scope (Dict[str, Any]): Pipeline-wide parameters for interpolation.
            resume_param (Optional[Dict[str, Any]]): Resume information for plugins.
            log_file_override (Optional[str]): Override for log file path.

        Returns:
            bool: True if the task succeeds, False otherwise.
        """
        plugin_cls = PluginRegistry.get(task.plugin)
        # scoped params: pipeline.params -> task.params -> CLI resume/log overrides
        params = self.interpolate_params(
            deep_merge(self.__config.params, task.params), scope=pipeline_scope
        )

        if log_file_override:
            params["log_file"] = log_file_override
        if resume_param:
            params["resume_from"] = resume_param

        # validate via plugin's parameter_model inside BasePlugin.__init__
        plugin = plugin_cls(name=task.name, params=params)

        async def _one_run() -> bool:
            # Pass ETLMode to plugin.run
            return await plugin.run(runtime_params=None, mode=mode)

        attempt = 0
        last_exc = None
        while attempt <= task.retries:
            try:
                if task.timeout_seconds:
                    return await asyncio.wait_for(
                        _one_run(), timeout=task.timeout_seconds
                    )
                else:
                    return await _one_run()
            except Exception as e:
                last_exc = e
                attempt += 1
                if attempt > task.retries:
                    # BasePlugin already logs exceptions; nothing more to add here.
                    return False
                await asyncio.sleep(min(2 * attempt, 10))  # simple backoff
        # should not get here
        if last_exc:
            raise last_exc
        return False

    async def _run_shell_task(self, task: TaskConfig) -> bool:
        """
        Run a shell command as a pipeline task.

        Args:
            task (TaskConfig): The task configuration.

        Returns:
            bool: True if the shell command succeeds, False otherwise.
        """
        if not task.command:
            raise ValueError(f"Shell task '{task.name}' missing 'command'")
        try:
            proc = await asyncio.create_subprocess_shell(
                task.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False

    async def _run_file_task(self, task: TaskConfig) -> bool:
        """
        Run a file operation task (e.g., check existence, copy, move).

        Args:
            task (TaskConfig): The task configuration.

        Returns:
            bool: True if the file operation succeeds, False otherwise.
        """
        # Placeholder: implement file copy/move/validate actions as you need.
        # Non-DB side effects only — consistent with earlier constraints.
        if not task.path:
            raise ValueError(f"File task '{task.name}' missing 'path'")
        # Example "exists" action:
        if task.action == "exists":
            return os.path.exists(task.path)
        return True

    async def _run_validation_task(self, task: TaskConfig) -> bool:
        """
        Run a validation task (custom validator).

        Args:
            task (TaskConfig): The task configuration.

        Returns:
            bool: True if the validation succeeds, False otherwise.
        """
        # Placeholder for custom validators (e.g., import and run a callable by dotted path)
        return True

    async def _run_notify_task(self, task: TaskConfig) -> bool:
        """
        Run a notification task (e.g., Slack/email/webhook).

        Args:
            task (TaskConfig): The task configuration.

        Returns:
            bool: True if the notification succeeds, False otherwise.
        """
        # Placeholder for Slack/email/webhook; callers can implement an adapter.
        # We do NOT do DB work here per earlier constraints.
        return True

    # ---- stage execution ----
    async def _run_stage(
        self,
        stage: StageConfig,
        tasks: List[TaskConfig],
        mode: ETLMode,
        pipeline_scope: Dict[str, Any],
        resume_param: Optional[Dict[str, Any]],
        log_file_override: Optional[str],
    ) -> bool:
        """
        Execute all tasks in a stage, either in parallel (async) or sequentially.

        Args:
            stage (StageConfig): The stage configuration.
            tasks (List[TaskConfig]): List of tasks to execute in the stage.
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).
            pipeline_scope (Dict[str, Any]): Pipeline-wide parameters for interpolation.
            resume_param (Optional[Dict[str, Any]]): Resume information for plugins.
            log_file_override (Optional[str]): Override for log file path.

        Returns:
            bool: True if all tasks succeed, False if any task fails.
        """
        if stage.parallel_mode == "async":
            sem = asyncio.Semaphore(stage.max_concurrency or len(tasks))

            async def run_task(task: TaskConfig):
                async with sem:
                    if task.type == "plugin":
                        return await self._run_plugin_task(
                            stage,
                            task,
                            mode,
                            pipeline_scope,
                            resume_param,
                            log_file_override,
                        )
                    if task.type == "shell":
                        return await self._run_shell_task(task)
                    if task.type == "file":
                        return await self._run_file_task(task)
                    if task.type == "validation":
                        return await self._run_validation_task(task)
                    if task.type == "notify":
                        return await self._run_notify_task(task)
                    return False

            coros = [run_task(t) for t in tasks]
            results = await asyncio.gather(*coros, return_exceptions=True)
            # Fail-fast barrier: any failure aborts pipeline
            for r in results:
                if r is not True:
                    return False
            return True

        # sequential
        for t in tasks:
            ok = False
            if t.type == "plugin":
                ok = await self._run_plugin_task(
                    stage, t, mode, pipeline_scope, resume_param, log_file_override
                )
            elif t.type == "shell":
                ok = await self._run_shell_task(t)
            elif t.type == "file":
                ok = await self._run_file_task(t)
            elif t.type == "validation":
                ok = await self._run_validation_task(t)
            elif t.type == "notify":
                ok = await self._run_notify_task(t)

            if not ok:
                return False
        return True

    # ---- public API ----
    async def run(
        self,
        *,
        mode: ETLMode = ETLMode.DRY_RUN,
        only: Optional[List[str]] = None,
        skip: Optional[List[str]] = None,
        resume_step: Optional[str] = None,
        resume_param: Optional[Dict[str, Any]] = None,  # {"line":N} or {"id":"X"}
        log_file_override: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,  # pipeline param overrides
        print_only: bool = False,
    ) -> bool:
        """
        Execute the pipeline.

        Args:
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).
            only (Optional[List[str]]): List of "Stage.Task" or "Stage" to include.
            skip (Optional[List[str]]): List of "Stage.Task" or "Stage" to exclude.
            resume_step (Optional[str]): "Stage" or "Stage.Task" to start from.
            resume_param (Optional[Dict[str, Any]]): Resume information for plugins.
            log_file_override (Optional[str]): Override for log file path.
            overrides (Optional[Dict[str, Any]]): Pipeline parameter overrides.
            print_only (bool): If True, print the plan and return without executing.

        Returns:
            bool: True if the pipeline completes successfully, False otherwise.
        """
        # apply overrides to pipeline params
        if overrides:
            self.__config = PipelineConfig(
                **{
                    **self.__config.dict(),
                    "params": deep_merge(self.__config.params, overrides),
                }
            )

        plan = self._select_stages_tasks(only=only, skip=skip, resume_step=resume_step)
        if print_only:
            print(self.print_plan(only=only, skip=skip, resume_step=resume_step))
            return True

        scope = self.__config.params.copy()
        for stage, tasks in plan:
            ok = await self._run_stage(
                stage=stage,
                tasks=tasks,
                mode=mode,
                pipeline_scope=scope,
                resume_param=resume_param,
                log_file_override=log_file_override,
            )
            if not ok:
                return False
        return True

    # ---- utils ----
    @staticmethod
    def interpolate_params(
        params: Dict[str, Any], scope: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Replace ${key} with scope[key] in string values in the params dict.

        Args:
            params (Dict[str, Any]): Dictionary of parameters to interpolate.
            scope (Dict[str, Any]): Dictionary providing values for interpolation.

        Returns:
            Dict[str, Any]: Interpolated parameters dictionary.
        """

        def repl(val: Any) -> Any:
            if isinstance(val, str):
                for m in re.finditer(r"\$\{([^}]+)\}", val):
                    key = m.group(1)
                    if key in scope:
                        val = val.replace(m.group(0), str(scope[key]))
            elif isinstance(val, dict):
                return {k: repl(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [repl(x) for x in val]
            return val

        return {k: repl(v) for k, v in params.items()}
