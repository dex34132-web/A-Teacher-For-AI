"""Orchestrator — routes requests to tools and manages execution."""
from __future__ import annotations
import concurrent.futures
from core.routing.v26.tools.base import BackgroundTask, PipelineResult, ToolRegistry, ToolResult

class Orchestrator:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._background_tasks: list[BackgroundTask] = []

    def dispatch(self, command: str, **params) -> ToolResult:
        return self._registry.execute(command, **params)

    def pipeline(self, steps: list[tuple[str, dict]]) -> PipelineResult:
        results = []
        context = {}
        for step_name, step_params in steps:
            merged = {**step_params, **context}
            result = self._registry.execute(step_name, **merged)
            results.append((step_name, result))
            if not result.success:
                break
            context.update(result.data)
        return PipelineResult(steps=results, success=all(r.success for _, r in results))

    def parallel(self, calls: list[tuple[str, dict]]) -> PipelineResult:
        results = []
        with concurrent.futures.ThreadPoolExecutor() as pool:
            futures = {}
            for name, params in calls:
                future = pool.submit(self._registry.execute, name, **params)
                futures[future] = name
            for future in concurrent.futures.as_completed(futures):
                results.append((futures[future], future.result()))
        return PipelineResult(steps=results, success=all(r.success for _, r in results))

    def remember_with_learning(self, content: str, outcome: str = "NEUTRAL",
                                project: str = "", session: str = "", **kwargs) -> PipelineResult:
        steps = [
            ("lerev_remember", {"content": content, "outcome": outcome, "project": project, "session": session, **kwargs}),
            ("lerev_conflict", {"content": content, "project": project}),
            ("lerev_deduplicate", {"content": content, "project": project}),
        ]
        return self.pipeline(steps)

    def trigger_background(self, task_type: str, **params) -> None:
        self._background_tasks.append(BackgroundTask(task_type=task_type, params=params))

    def process_background(self) -> list[ToolResult]:
        results = []
        while self._background_tasks:
            task = self._background_tasks.pop(0)
            result = self._registry.execute(task.task_type, **task.params)
            results.append(result)
        return results
