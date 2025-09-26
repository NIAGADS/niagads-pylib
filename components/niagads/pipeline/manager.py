import asyncio
from enum import auto
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from niagads.common.core import ComponentBaseMixin
from niagads.enums.common import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.pipeline.config import PipelineConfig, StageConfig, TaskConfig
from niagads.pipeline.plugins.registry import PluginRegistry
from niagads.utils.dict import deep_merge
from pydantic import BaseModel


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


class StageTaskSelector(BaseModel):
    stage: str
    task: Optional[str] = None

    @classmethod
    def from_str(cls, value: str):
        """
        Convert a string like 'stage' or 'stage.task' to a StageTaskSelector instance.
        """
        if "." in value:
            stage, task = value.split(".", 1)
            return cls(stage=stage, task=task)
        return cls(stage=value)

    @classmethod
    def from_any(cls, value: Any):
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls.from_str(value)
        if isinstance(value, dict):
            return cls(**value)
        raise ValueError(f"Cannot convert {value!r} to StageTaskSelector")

    @classmethod
    def normalize_list(
        cls, items: Optional[List[Any]]
    ) -> Optional[List["StageTaskSelector"]]:
        """
        Normalize a list of stage/task selectors to StageTaskSelector objects.

        This method ensures that all elements in the list are converted to StageTaskSelector,
        regardless of whether they are provided as strings ("stage" or "stage.task"), dicts,
        or already as StageTaskSelector instances. This allows the pipeline to accept flexible
        input formats from CLI, config, or code, and always work with a uniform type internally.

        Example usage:
            selectors = ["stage1", {"stage": "stage2", "task": "taskA"}, StageTaskSelector(stage="stage3")]
            normalized = StageTaskSelector.normalize_list(selectors)
            # normalized is now a list of StageTaskSelector objects

        Args:
            items (Optional[List[Any]]): List of selectors as strings, dicts, or StageTaskSelector.
        Returns:
            Optional[List[StageTaskSelector]]: List of normalized StageTaskSelector objects, or None if input is None.
        """
        if items is None:
            return None
        return [cls.from_any(i) for i in items]


class PipelineManager(ComponentBaseMixin):
    """
    Pipeline executor with:
        - Stage barrier semantics (stages run in order, next waits for previous)
        - Async parallel stage execution (max_concurrency controls concurrency)
        - Task retries and per-task timeouts
        - CLI overrides for params, resume_from, only/skip filters, plan-only output
        - Dry-run by default; --commit enables writes
    """

    def __init__(self, config_file: str, debug: bool = False, verbose: bool = False):
        """
        Initialize the PipelineManager with a pipeline configuration file.

        Args:
            config_path (str): Path to the pipeline configuration JSON file.
        """
        super().__init__(debug=debug, verbose=verbose)

        with open(config_file, "r") as f:
            config = json.load(f)
        self.__config = PipelineConfig(**config)

        # Filters and plan
        self.__only: Optional[List[StageTaskSelector]] = None
        self.__skip: Optional[List[StageTaskSelector]] = []
        self.__resume_point: Optional[StageTaskSelector] = None
        self.__checkpoint: Optional[Dict[str, Any]] = None

    # ---- planning & filtering ----
    def _plan(self) -> List[Tuple[StageConfig, List[TaskConfig]]]:
        """
        Compute the execution plan (stages and tasks) based on filters and resume_point.
        """
        plan = []
        resume = StageTaskSelector.from_any(self.__resume_point)
        resuming = resume is not None
        found_resume_stage = not resuming
        found_resume_task = not resuming

        for stage in self.__config.stages:
            if stage.skip or stage.deprecated:
                continue

            # If resuming, skip stages before the resume stage
            if resuming and not found_resume_stage:
                if stage.name == resume.stage:
                    found_resume_stage = True
                else:
                    continue

            stage_tasks = []
            for task in stage.tasks:
                if task.skip or task.deprecated:
                    continue

                # If resuming at a specific task, skip tasks before the resume task in the resume stage
                if resuming and stage.name == resume.stage and resume.task:
                    if not found_resume_task:
                        if task.name == resume.task:
                            found_resume_task = True
                        else:
                            continue

                # Apply 'only' and 'skip' filters
                if self.__only and not (
                    self._match_stage_task(self.__only, stage.name, task.name)
                    or self._match_stage_task(self.__only, stage.name, None)
                ):
                    continue
                if self.__skip and (
                    self._match_stage_task(self.__skip, stage.name, None)
                    or self._match_stage_task(self.__skip, stage.name, task.name)
                ):
                    continue

                stage_tasks.append(task)

            if stage_tasks:
                plan.append((stage, stage_tasks))

            # If resuming at a stage (not a task), after the first matching stage, treat as normal
            if resuming and found_resume_stage and not resume.task:
                found_resume_stage = True  # remains True for all subsequent stages

        return plan

    def _match_stage_task(self, filters, stage_name, task_name=None):
        if not filters:
            return False
        for f in filters:
            if f.stage == stage_name:
                if f.task is None or f.task == task_name:
                    return True
        return False

    def _has_resume_point(self):
        resume = StageTaskSelector.from_any(self.__resume_point)
        return bool(resume)

    def print_plan(self):
        """
        Print a human-readable plan of the pipeline stages and tasks to be executed.
        """
        plan = self._plan()
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
    ) -> bool:
        plugin_cls = PluginRegistry.get(task.plugin)
        params = self.interpolate_params(
            deep_merge(self.__config.params, task.params), scope=pipeline_scope
        )
        if self.__checkpoint:
            params["resume_from"] = self.__checkpoint
        plugin = plugin_cls(name=task.name, params=params)
        return await self._plugin_one_run(plugin, mode, task)

    async def _plugin_one_run(self, plugin, mode, task):
        attempt = 0
        last_exc = None
        while attempt <= task.retries:
            try:
                if task.timeout_seconds:
                    await asyncio.wait_for(
                        plugin.run(runtime_params=None, mode=mode),
                        timeout=task.timeout_seconds,
                    )
                else:
                    await plugin.run(runtime_params=None, mode=mode)
                return ProcessStatus.SUCCESS
            except Exception as e:
                last_exc = e
                attempt += 1
                if attempt > task.retries:
                    return ProcessStatus.FAIL
                await asyncio.sleep(min(2 * attempt, 10))
        if last_exc:
            raise last_exc
        return ProcessStatus.FAIL

    async def _run_shell_task(self, task: TaskConfig) -> ProcessStatus:
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
            return ProcessStatus.SUCCESS if proc.returncode == 0 else ProcessStatus.FAIL
        except Exception:
            return ProcessStatus.FAIL

    async def _run_file_task(self, task: TaskConfig) -> ProcessStatus:
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
            return (
                ProcessStatus.SUCCESS
                if os.path.exists(task.path)
                else ProcessStatus.FAIL
            )
        return ProcessStatus.SUCCESS

    async def _run_validation_task(self, task: TaskConfig) -> ProcessStatus:
        """
        Run a validation task (custom validator).

        Args:
            task (TaskConfig): The task configuration.

        Returns:
            bool: True if the validation succeeds, False otherwise.
        """
        # Placeholder for custom validators (e.g., import and run a callable by dotted path)
        return ProcessStatus.SUCCESS

    async def _run_notify_task(self, task: TaskConfig) -> ProcessStatus:
        """
        Run a notification task (e.g., Slack/email/webhook).

        Args:
            task (TaskConfig): The task configuration.

        Returns:
            bool: True if the notification succeeds, False otherwise.
        """
        # Placeholder for Slack/email/webhook; callers can implement an adapter.
        # We do NOT do DB work here per earlier constraints.
        return ProcessStatus.SUCCESS

    # ---- stage execution ----
    async def _run_stage(
        self,
        stage: StageConfig,
        tasks: List[TaskConfig],
        mode: ETLMode,
        pipeline_scope: Dict[str, Any],
    ) -> bool:
        """
        Execute all tasks in a stage, either in parallel (async) or sequentially.

        Args:
            stage (StageConfig): The stage configuration.
            tasks (List[TaskConfig]): List of tasks to execute in the stage.
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).
            pipeline_scope (Dict[str, Any]): Pipeline-wide parameters for interpolation.

        Returns:
            bool: True if all tasks succeed, False if any task fails.
        """
        if stage.parallel_mode == "async":
            sem = asyncio.Semaphore(stage.max_concurrency or len(tasks))

            task_coroutines = [
                self._run_stage_task(stage, t, mode, pipeline_scope, sem) for t in tasks
            ]
            results = await asyncio.gather(*task_coroutines, return_exceptions=True)

            # Fail-fast barrier: any failure aborts pipeline
            for r in results:
                if r is not True:
                    return ProcessStatus.FAIL
            return ProcessStatus.SUCCESS

    async def _run_stage_task(self, stage, task, mode, pipeline_scope, sem):
        async with sem:
            if task.type == "plugin":
                return await self._run_plugin_task(
                    stage,
                    task,
                    mode,
                    pipeline_scope,
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

    # ---- public API ----
    async def run(
        self,
        *,
        mode: ETLMode = ETLMode.DRY_RUN,
        parameter_overrides: Optional[
            Dict[str, Any]
        ] = None,  # pipeline param overrides
    ) -> bool:
        """
        Execute the pipeline.

        Args:
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).
            parameter_overrides (Optional[Dict[str, Any]]): Pipeline parameter overrides.

        Returns:
            bool: True if the pipeline completes successfully, False otherwise.
        """
        # apply overrides to pipeline params
        if parameter_overrides:
            self.__config = PipelineConfig(
                **{
                    **self.__config.dict(),
                    "params": deep_merge(self.__config.params, parameter_overrides),
                }
            )

        plan = self._plan()
        scope = self.__config.params.copy()
        for stage, tasks in plan:
            status = await self._run_stage(
                stage=stage,
                tasks=tasks,
                mode=mode,
                pipeline_scope=scope,
            )
            return status
        return ProcessStatus.SUCCESS

    # ---- filter properties ----
    @property
    def only(self) -> Optional[List[StageTaskSelector]]:
        return self.__only

    @only.setter
    def only(self, value: Optional[List[Any]]):
        if value is not None and self.__skip:
            raise ValueError(
                "Cannot set both 'only' and 'skip' filters; they are mutually exclusive."
            )
        self.__only = StageTaskSelector.normalize_list(value)

    @property
    def skip(self) -> Optional[List[StageTaskSelector]]:
        return self.__skip

    @skip.setter
    def skip(self, value: Optional[List[Any]]):
        if value is not None and self.__only:
            raise ValueError(
                "Cannot set both 'only' and 'skip' filters; they are mutually exclusive."
            )
        self.__skip = StageTaskSelector.normalize_list(value)

    @property
    def resume_point(self) -> Optional[StageTaskSelector]:
        return self.__resume_point

    @resume_point.setter
    def resume_point(self, value: Optional[Any]):
        selector = StageTaskSelector.from_any(value)
        if selector is not None:
            # Validate immediately: must not be skipped or deprecated
            for stage in self.__config.stages:
                if stage.name == selector.stage:
                    if stage.skip or stage.deprecated:
                        msg = f"Cannot resume at skipped or deprecated stage: {selector.stage}"
                        self.logger.error(msg)
                        raise ValueError(msg)
                    if selector.task:
                        found = False
                        for task in stage.tasks:
                            if task.name == selector.task:
                                found = True
                                if task.skip or task.deprecated:
                                    msg = f"Cannot resume at skipped or deprecated task: {selector.stage}.{selector.task}"
                                    self.logger.error(msg)
                                    raise ValueError(msg)
                        if not found:
                            msg = f"Task not found for resume_point: {selector.stage}.{selector.task}"
                            self.logger.error(msg)
                            raise ValueError(msg)
                    break
            else:
                msg = f"Stage not found for resume_point: {selector.stage}"
                self.logger.error(msg)
                raise ValueError(msg)
        self.__resume_point = selector

    @property
    def checkpoint(self) -> Optional[Dict[str, Any]]:
        return self.__checkpoint

    @checkpoint.setter
    def checkpoint(self, value: Optional[Dict[str, Any]]):
        self.__checkpoint = value

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
