"""Task plan tool for Rocky.Ai.

Allows Rocky to create and track a checklist for multi-step work.
Session-scoped — plan resets when session ends.
"""

from dataclasses import dataclass
from rocky.tools.base import Tool, ToolResult, ToolParameter


@dataclass
class PlanTask:
    subject: str
    status: str = "pending"  # pending, in_progress, done


class TaskPlanTool(Tool):
    """Create, update, and list task plans for multi-step work."""

    def __init__(self):
        super().__init__(
            name="task_plan",
            description="Create/update/list a task checklist for tracking multi-step work",
            parameters=[
                ToolParameter(
                    name="action", type="string",
                    description="Action: 'create', 'update', or 'list'",
                    required=True),
                ToolParameter(
                    name="subject", type="string",
                    description="Task subject/title",
                    required=False, default=""),
                ToolParameter(
                    name="status", type="string",
                    description="New status: 'pending', 'in_progress', 'done'",
                    required=False, default="pending"),
            ]
        )
        self._tasks: list[PlanTask] = []

    def execute(self, action: str, subject: str = "", status: str = "pending") -> ToolResult:
        if action == "create":
            return self._create(subject)
        elif action == "update":
            return self._update(subject, status)
        elif action == "list":
            return self._list()
        else:
            return ToolResult.fail(f"Unknown action: {action}. Use 'create', 'update', or 'list'.")

    def _create(self, subject: str) -> ToolResult:
        if not subject:
            return ToolResult.fail("Subject required for create action.")
        self._tasks.append(PlanTask(subject=subject))
        return ToolResult.ok(f"Added task: {subject}", data={"total": len(self._tasks)})

    def _update(self, subject: str, status: str) -> ToolResult:
        for task in self._tasks:
            if task.subject == subject:
                task.status = status
                return ToolResult.ok(f"Updated '{subject}' → {status}")
        return ToolResult.fail(f"Task not found: {subject}")

    def _list(self) -> ToolResult:
        if not self._tasks:
            return ToolResult.ok("No tasks in plan.", data={"tasks": []})

        icons = {"done": "✔", "in_progress": "⠧", "pending": "◦"}
        lines = []
        for task in self._tasks:
            icon = icons.get(task.status, "◦")
            lines.append(f"  {icon}  {task.subject}")

        output = "\n".join(lines)
        return ToolResult.ok(output, data={"tasks": [
            {"subject": t.subject, "status": t.status} for t in self._tasks
        ]})
