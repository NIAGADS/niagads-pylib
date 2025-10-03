# TODO: review error handling; make sure errors are propogated and then caught
# and logged in a try block

import asyncio
import json
import traceback
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from niagads.common.core import ComponentBaseMixin
from niagads.enums.common import ProcessStatus
from niagads.etl.config import ETLMode
from niagads.etl.pipeline.config import (
    ParallelMode,
    PipelineConfig,
    PipelineSettings,
    StageConfig,
    TaskConfig,
    TaskType,
)
from niagads.etl.pipeline.filters import PipelineFilters
from niagads.etl.pipeline.selectors import StageTaskSelector
from niagads.etl.utils import (
    register_plugin_directory,
    interpolate_params,
    register_plugins,
)
from niagads.utils.dict import deep_merge


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
        self.__filters = PipelineFilters()

        register_plugins(
            project=PipelineSettings.from_env().PROJECT,
            packages=PipelineSettings.from_env().PLUGIN_PACKAGES,
        )

    # ---- planning & filtering ----
    def _plan(self) -> List[Tuple[StageConfig, List[TaskConfig]]]:
        plan = []
        self.__filters.validate(self.__config.stages)
        resume = self.__filters.resume_point
        resuming = resume is not None
        found_resume_stage = not resuming
        found_resume_task = not resuming

        for stage in self.__config.stages:
            if stage.skip or stage.deprecated:
                continue
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
                if self.__filters.only and not (
                    StageTaskSelector.match_stage_task(
                        self.__filters.only, stage.name, task.name
                    )
                    or StageTaskSelector.match_stage_task(
                        self.__filters.only, stage.name, None
                    )
                ):
                    continue
                if self.__filters.skip and (
                    StageTaskSelector.match_stage_task(
                        self.__filters.skip, stage.name, None
                    )
                    or StageTaskSelector.match_stage_task(
                        self.__filters.skip, stage.name, task.name
                    )
                ):
                    continue
                stage_tasks.append(task)
            if stage_tasks:
                plan.append((stage, stage_tasks))
            if resuming and found_resume_stage and not resume.task:
                found_resume_stage = True
        return plan

    def print_plan(self, log: bool = False):
        """
        Print or log a human-readable plan of the pipeline stages and tasks to be executed.

        Args:
            log (bool): If True, log the plan using the logger. If False, print to stdout.

        Returns:
            None
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
        task: TaskConfig,
        mode: ETLMode,
        pipeline_scope: Dict[str, Any],
    ) -> ProcessStatus:
        from niagads.etl.plugins.registry import PluginRegistry

        plugin_cls = PluginRegistry.get(task.plugin)
        params = interpolate_params(
            deep_merge(self.__config.params, task.params), scope=pipeline_scope
        )
        if self.__checkpoint:
            params["resume_from"] = self.__checkpoint
        plugin = plugin_cls(name=task.name, params=params)
        await plugin.run(runtime_params=None, mode=mode)
        return ProcessStatus.SUCCESS

    async def _run_shell_task(self, task: TaskConfig) -> ProcessStatus:
        """
        Run a shell command as a pipeline task.
        """
        if not task.command:
            raise ValueError(f"Shell task '{task.name}' missing 'command'")
        proc = await asyncio.create_subprocess_shell(
            task.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return ProcessStatus.SUCCESS
        else:
            raise RuntimeError(
                f"Shell task '{task.name}' failed with return code {proc.returncode}\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
            )

    async def _run_file_task(self, task: TaskConfig) -> ProcessStatus:
        """
        Run a file operation task (e.g., check existence, copy, move).
        # Example "exists" action:
        if task.action == "exists":
            if os.path.exists(task.path):
                return ProcessStatus.SUCCESS
            else:
                raise FileNotFoundError(
                    f"File task '{task.name}' path does not exist: {task.path}"
                )
        Args:
            task (TaskConfig): The task configuration.

        Returns:
            bool: True if the file operation succeeds, False otherwise.
        """
        # Placeholder: implement file copy/move/validate actions as you need.
        # Non-DB side effects only — consistent with earlier constraints.
        if not task.path:
            raise ValueError(f"File task '{task.name}' missing 'path'")
        raise NotImplementedError("File Tasks not yet implemented.")

    async def _run_validation_task(self, task: TaskConfig) -> ProcessStatus:
        """
        Run a validation task (custom validator).
        """
        # Placeholder for custom validators (e.g., import and run a callable by dotted path)
        raise NotImplementedError("Validation Tasks not yet implemented.")

    async def _run_notify_task(self, task: TaskConfig) -> ProcessStatus:
        """
        Run a notification task (e.g., Slack/email/webhook).

        Args:
            task (TaskConfig): The task configuration.

        Returns:
            bool: True if the notification succeeds, False otherwise.
        """
        # Placeholder for Slack/email/webhook; callers can implement an adapter.
        raise NotImplementedError("Notification Tasks not yet implemented")

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
        # Only check status, error handling/logging is centralized in _run_stage_task
        if any(r is not ProcessStatus.SUCCESS for r in results):
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

            # Only check status, error handling/logging is centralized in _run_stage_task
            if any(r is not ProcessStatus.SUCCESS for r in results):
                return ProcessStatus.FAIL
            return ProcessStatus.SUCCESS

    async def _run_stage_sequential(
        self,
        stage: StageConfig,
        tasks: List[TaskConfig],
        mode: ETLMode,
        pipeline_scope: Dict[str, Any],
    ) -> ProcessStatus:
        for t in tasks:
            result = await self._run_stage_task(stage, t, mode, pipeline_scope)

            # Only check status, error handling/logging is centralized in _run_stage_task
            if result is not ProcessStatus.SUCCESS:
                return ProcessStatus.FAIL
        return ProcessStatus.SUCCESS

    async def _run_stage_task(
        self,
        stage: StageConfig,
        task: TaskConfig,
        mode: ETLMode,
        pipeline_scope: Dict[str, Any],
    ) -> ProcessStatus:
        self.logger.info(f"[Task] {task.name} started (type={task.type})")
        try:
            match task.type:
                case TaskType.PLUGIN:
                    result = await self._run_plugin_task(task, mode, pipeline_scope)
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
    ) -> ProcessStatus:
        """
        Execute the pipeline.

        Args:
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).
            parameter_overrides (Optional[Dict[str, Any]]): Pipeline parameter overrides.

        Returns:
            ProcessStatus: SUCCESS if the pipeline completes successfully, FAIL otherwise.
        """
        # apply overrides to pipeline params
        if parameter_overrides:
            self.params = deep_merge(self.params, parameter_overrides)

        plan = self._plan()
        self._log_pipeline_start(mode)

        all_success = True
        for stage, tasks in plan:
            self.logger.info(
                f"[Stage] {stage.name} started. Tasks: {[t.name for t in tasks]}"
            )
            status = await self._run_stage(
                stage=stage,
                tasks=tasks,
                mode=mode,
                pipeline_scope=self.params,
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

    def _log_pipeline_start(self, mode: ETLMode):
        self.logger.info(f"Pipeline started. Mode: {mode.name}")
        if self.__filters.only:
            self.logger.info(
                f"Filter: only = {[str(sel) for sel in self.__filters.only]}"
            )
        if self.__filters.skip:
            self.logger.info(
                f"Filter: skip = {[str(sel) for sel in self.__filters.skip]}"
            )
        if self.__filters.resume_point:
            self.logger.info(f"Resuming from: {self.__filters.resume_point}")

        if self._verbose:
            self.print_plan(log=True)

    # ---- filter properties ----
    @property
    def only(self):
        return self.__filters.only

    @only.setter
    def only(self, value):
        self.__filters.only = value

    @property
    def skip(self):
        return self.__filters.skip

    @skip.setter
    def skip(self, value):
        self.__filters.skip = value

    @property
    def resume_point(self):
        return self.__filters.resume_point

    @resume_point.setter
    def resume_point(self, value):
        self.__filters.resume_point = value

    @property
    def checkpoint(self) -> Optional[Dict[str, Any]]:
        return self.__checkpoint

    @checkpoint.setter
    def checkpoint(self, value: Optional[Dict[str, Any]]):
        self.__checkpoint = value

    # ---- pipeline params property ----
    @property
    def params(self):
        return self.__config.params

    @params.setter
    def params(self, value):
        self.__config.params = value
