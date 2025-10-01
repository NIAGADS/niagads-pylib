# TODO: review error handling; make sure errors are propogated and then caught
# and logged in a try block

import asyncio
import json
import os
import re
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from enum import auto
from typing import Any, Dict, List, Optional, Tuple

from niagads.common.core import ComponentBaseMixin
from niagads.enums.common import ProcessStatus
from niagads.enums.core import CaseInsensitiveEnum
from niagads.pipeline.config import (
    ParallelMode,
    PipelineConfig,
    StageConfig,
    TaskConfig,
    TaskType,
)
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

    @staticmethod
    def match_stage_task(filters, stage_name, task_name=None):
        if not filters:
            return False
        for f in filters:
            if f.stage == stage_name:
                if f.task is None or f.task == task_name:
                    return True
        return False


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
                    StageTaskSelector.match_stage_task(
                        self.__only, stage.name, task.name
                    )
                    or StageTaskSelector.match_stage_task(self.__only, stage.name, None)
                ):
                    continue
                if self.__skip and (
                    StageTaskSelector.match_stage_task(self.__skip, stage.name, None)
                    or StageTaskSelector.match_stage_task(
                        self.__skip, stage.name, task.name
                    )
                ):
                    continue

                stage_tasks.append(task)

            if stage_tasks:
                plan.append((stage, stage_tasks))

            # If resuming at a stage (not a task), after the first matching stage, treat as normal
            if resuming and found_resume_stage and not resume.task:
                found_resume_stage = True  # remains True for all subsequent stages

        return plan

    def _has_resume_point(self):
        resume = StageTaskSelector.from_any(self.__resume_point)
        return bool(resume)

    def print_plan(self, log: bool = False):
        """
        Print or log a human-readable plan of the pipeline stages and tasks to be executed.
        """
        plan = self._plan()
        lines = ["Pipeline Plan:"]
        for stage, tasks in plan:
            lines.append(
                f"[Stage] {stage.name}  mode={stage.parallel_mode}  max={stage.max_concurrency or '-'}"
            )
            for t in tasks:
                lines.append(
                    f"    - {t.name:<12} type={t.type:<10} plugin={t.plugin or '-':<16} timeout={str(t.timeout_seconds) if getattr(t, 'timeout_seconds', None) else '-':<6} retries={getattr(t, 'retries', '-') if hasattr(t, 'retries') else '-'}"
                )
        output = "\n" + "\n".join(lines)
        if log:
            self.logger.info(output)
        else:
            print(output)

    # ---- task executors ----
    async def _run_plugin_task(
        self,
        stage: StageConfig,
        task: TaskConfig,
        mode: ETLMode,
        pipeline_scope: Dict[str, Any],
    ) -> ProcessStatus:
        plugin_cls = PluginRegistry.get(task.plugin)
        params = self.interpolate_params(
            deep_merge(self.__config.params, task.params), scope=pipeline_scope
        )
        if self.__checkpoint:
            params["resume_from"] = self.__checkpoint
        plugin = plugin_cls(name=task.name, params=params)
        try:
            await plugin.run(runtime_params=None, mode=mode)
            return ProcessStatus.SUCCESS
        except Exception:
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
    ) -> ProcessStatus:
        """
        Execute all tasks in a stage, either in parallel (async/thread/process) or sequentially.

        Args:
            stage (StageConfig): The stage configuration.
            tasks (List[TaskConfig]): List of tasks to execute in the stage.
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).
            pipeline_scope (Dict[str, Any]): Pipeline-wide parameters for interpolation.

        Returns:
            bool: True if all tasks succeed, False if any task fails.
        """
        match stage.parallel_mode:
            case ParallelMode.NONE:
                return await self._run_stage_sequential(
                    stage, tasks, mode, pipeline_scope
                )
            case ParallelMode.THREAD:
                return await self._run_stage_parallel_thread(
                    stage, tasks, mode, pipeline_scope
                )
            case ParallelMode.PROCESS:
                return await self._run_stage_parallel_process(
                    stage, tasks, mode, pipeline_scope
                )
            case _:
                raise ValueError(
                    f"Unknown parallel mode: {stage.parallel_mode!r} for stage '{stage.name}'"
                )

    async def _run_stage_parallel_thread(
        self, stage, tasks, mode, pipeline_scope
    ) -> ProcessStatus:
        results = await asyncio.gather(
            *(self._run_stage_task(stage, t, mode, pipeline_scope) for t in tasks),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception) or r is not ProcessStatus.SUCCESS:
                self.logger.error(f"Stage task failed or raised exception: {r}")
                return ProcessStatus.FAIL
        return ProcessStatus.SUCCESS

    # FIXME: potentially being handled incorrectly; something to do w/pickling
    async def _run_stage_parallel_process(
        self,
        stage: StageConfig,
        tasks: list[TaskConfig],
        mode: ETLMode,
        pipeline_scope: dict,
    ) -> ProcessStatus:

        max_workers = stage.max_concurrency or len(tasks)
        loop = asyncio.get_running_loop()

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                loop.run_in_executor(
                    executor,
                    lambda t=t: asyncio.run(
                        self._run_stage_task(stage, t, mode, pipeline_scope)
                    ),
                    t,
                )
                for t in tasks
            ]
            results = await asyncio.gather(*futures, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception) or r is not ProcessStatus.SUCCESS:
                    self.logger.error(f"Stage task failed or raised exception: {r}")
                    return ProcessStatus.FAIL
            return ProcessStatus.SUCCESS

    async def _run_stage_sequential(
        self, stage, tasks, mode, pipeline_scope
    ) -> ProcessStatus:
        for t in tasks:
            result = await self._run_stage_task(stage, t, mode, pipeline_scope)
            if result is not ProcessStatus.SUCCESS:
                return ProcessStatus.FAIL
        return ProcessStatus.SUCCESS

    async def _run_stage_task(self, stage, task, mode, pipeline_scope) -> ProcessStatus:
        self.logger.info(f"[Task] {task.name} started (type={task.type})")
        try:
            match task.type:
                case TaskType.PLUGIN:
                    result = await self._run_plugin_task(
                        stage, task, mode, pipeline_scope
                    )
                case TaskType.SHELL:
                    result = await self._run_shell_task(task)
                case TaskType.FILE:
                    result = await self._run_file_task(task)
                case TaskType.VALIDATION:
                    result = await self._run_validation_task(task)
                case TaskType.NOTIFY:
                    result = await self._run_notify_task(task)
                case _:
                    raise ValueError(
                        f"Unknown task type: {task.type!r} in stage '{stage.name}' task '{task.name}'"
                    )
        except Exception as e:
            self.logger.error(
                f"[Task] {task.name} raised exception: {e}\n{traceback.format_exc()}"
            )
            return ProcessStatus.FAIL
        if result is not ProcessStatus.SUCCESS:
            self.logger.error(f"[Task] {task.name} failed: {result}")
        else:
            self.logger.info(f"[Task] {task.name} completed successfully.")
        return result

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

        self.logger.info(f"Pipeline started. Mode: {mode.name}")
        if self.only:
            self.logger.info(f"Filter: only = {[str(sel) for sel in self.only]}")
        if self.skip:
            self.logger.info(f"Filter: skip = {[str(sel) for sel in self.skip]}")
        if self.resume_point:
            self.logger.info(f"Resuming from: {self.resume_point}")
        self.print_plan()

        all_success = True
        for stage, tasks in plan:
            self.logger.info(
                f"[Stage] {stage.name} started. Tasks: {[t.name for t in tasks]}"
            )
            status = await self._run_stage(
                stage=stage,
                tasks=tasks,
                mode=mode,
                pipeline_scope=scope,
            )
            if status is not ProcessStatus.SUCCESS:
                self.logger.error(f"[Stage] {stage.name} failed.")
                all_success = False
                break
            self.logger.info(f"[Stage] {stage.name} completed successfully.")

        if all_success:
            self.logger.info("Pipeline completed successfully.")
            return ProcessStatus.SUCCESS
        else:
            self.logger.error("Pipeline failed.")
            return ProcessStatus.FAIL

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

    # FIXME: look into string.Template
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
                    else:
                        raise KeyError(
                            f"Parameter interpolation failed: missing key '{key}' in scope."
                        )
            elif isinstance(val, dict):
                return {k: repl(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [repl(x) for x in val]
            return val

        return {k: repl(v) for k, v in params.items()}
