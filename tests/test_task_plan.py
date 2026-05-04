"""Tests for task plan tool."""
from rocky.tools.task_plan import TaskPlanTool


class TestTaskPlan:
    def setup_method(self):
        self.tool = TaskPlanTool()
        self.tool._tasks.clear()

    def test_create_task(self):
        result = self.tool.execute(action="create", subject="Write app.py")
        assert result.success
        assert "Write app.py" in result.output

    def test_list_tasks(self):
        self.tool.execute(action="create", subject="Task 1")
        self.tool.execute(action="create", subject="Task 2")
        result = self.tool.execute(action="list")
        assert result.success
        assert "Task 1" in result.output
        assert "Task 2" in result.output

    def test_update_task_status(self):
        self.tool.execute(action="create", subject="Task 1")
        result = self.tool.execute(action="update", subject="Task 1", status="done")
        assert result.success

    def test_update_nonexistent_task(self):
        result = self.tool.execute(action="update", subject="Nonexistent", status="done")
        assert not result.success
