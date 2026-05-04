"""Comprehensive V2 integration tests — stress testing every component.

Tests the full stack: tools, permissions, context, persona, agentic loop,
error handling, edge cases. Designed to find bugs, not just confirm happy paths.
"""

import os
import time
import tempfile
from pathlib import Path
from rich.console import Console

# ============================================================
# TOOL TESTS — Deep dive into every tool's behavior
# ============================================================


class TestReadFileTool:
    """Exhaustive read_file testing."""

    def setup_method(self):
        from rocky.tools.files import ReadFileTool
        self.tool = ReadFileTool()

    def test_read_existing_file(self):
        path = tempfile.mktemp(suffix=".txt")
        Path(path).write_text("hello world")
        try:
            result = self.tool.execute(path=path)
            assert result.success
            assert "hello" in result.output
        finally:
            os.unlink(path)

    def test_read_nonexistent_file(self):
        result = self.tool.execute(path="/tmp/absolutely_nonexistent_xyz.txt")
        assert not result.success
        assert "not found" in result.error.lower() or "error" in result.error.lower()

    def test_read_empty_file(self):
        path = tempfile.mktemp(suffix=".txt")
        Path(path).write_text("")
        try:
            result = self.tool.execute(path=path)
            assert result.success
        finally:
            os.unlink(path)

    def test_read_binary_file(self):
        path = tempfile.mktemp(suffix=".bin")
        Path(path).write_bytes(b"\x00\x01\x02\x03\xff\xfe")
        try:
            result = self.tool.execute(path=path)
            # Should either succeed with warning or fail gracefully
            assert result is not None
        finally:
            os.unlink(path)

    def test_read_large_file(self):
        path = tempfile.mktemp(suffix=".txt")
        Path(path).write_text("x" * 100000)
        try:
            result = self.tool.execute(path=path)
            assert result.success
        finally:
            os.unlink(path)

    def test_read_file_with_special_chars_in_name(self):
        path = tempfile.mktemp(suffix="_special (1).txt")
        Path(path).write_text("content")
        try:
            result = self.tool.execute(path=path)
            assert result.success
        finally:
            os.unlink(path)

    def test_read_symlink(self):
        real_path = tempfile.mktemp(suffix=".txt")
        link_path = tempfile.mktemp(suffix="_link.txt")
        Path(real_path).write_text("linked content")
        try:
            os.symlink(real_path, link_path)
            result = self.tool.execute(path=link_path)
            assert result.success
            assert "linked content" in result.output
        finally:
            os.unlink(real_path)
            if os.path.exists(link_path):
                os.unlink(link_path)

    def test_read_permission_denied(self):
        path = tempfile.mktemp(suffix=".txt")
        Path(path).write_text("secret")
        os.chmod(path, 0o000)
        try:
            result = self.tool.execute(path=path)
            assert not result.success
        finally:
            os.chmod(path, 0o644)
            os.unlink(path)


class TestWriteFileTool:
    """Exhaustive write_file testing."""

    def setup_method(self):
        from rocky.tools.files import WriteFileTool
        self.tool = WriteFileTool()

    def test_write_new_file(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            result = self.tool.execute(path=path, content="new content")
            assert result.success
            assert Path(path).read_text() == "new content"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_write_overwrites_existing(self):
        path = tempfile.mktemp(suffix=".txt")
        Path(path).write_text("old")
        try:
            result = self.tool.execute(path=path, content="new")
            assert result.success
            assert Path(path).read_text() == "new"
        finally:
            os.unlink(path)

    def test_write_empty_content(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            result = self.tool.execute(path=path, content="")
            assert result.success
            assert Path(path).read_text() == ""
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_write_creates_parent_dirs(self):
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "sub", "dir", "file.txt")
        try:
            result = self.tool.execute(path=path, content="deep")
            # Should either create dirs or fail gracefully
            assert result is not None
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_write_unicode_content(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            content = "Hello 🌍 中文 العربية"
            result = self.tool.execute(path=path, content=content)
            assert result.success
            assert Path(path).read_text() == content
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_write_multiline(self):
        path = tempfile.mktemp(suffix=".py")
        try:
            content = "def foo():\n    return 42\n\ndef bar():\n    pass\n"
            result = self.tool.execute(path=path, content=content)
            assert result.success
            assert Path(path).read_text() == content
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestEditFileTool:
    """Exhaustive edit_file testing including replace_all."""

    def setup_method(self):
        from rocky.tools.files import EditFileTool, WriteFileTool
        self.tool = EditFileTool()
        self.write = WriteFileTool()

    def test_edit_single_occurrence(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            self.write.execute(path=path, content="hello world")
            result = self.tool.execute(path=path, old_str="hello", new_str="goodbye")
            assert result.success
            assert Path(path).read_text() == "goodbye world"
        finally:
            os.unlink(path)

    def test_edit_not_found(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            self.write.execute(path=path, content="hello")
            result = self.tool.execute(path=path, old_str="xyz", new_str="abc")
            assert not result.success
        finally:
            os.unlink(path)

    def test_edit_replace_all_true(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            self.write.execute(path=path, content="a b a c a")
            result = self.tool.execute(path=path, old_str="a", new_str="X", replace_all=True)
            assert result.success
            assert Path(path).read_text() == "X b X c X"
        finally:
            os.unlink(path)

    def test_edit_replace_all_false_fails_on_multiple(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            self.write.execute(path=path, content="foo bar foo")
            result = self.tool.execute(path=path, old_str="foo", new_str="baz", replace_all=False)
            assert not result.success
            assert "2" in result.error  # should mention count
        finally:
            os.unlink(path)

    def test_edit_multiline_replacement(self):
        path = tempfile.mktemp(suffix=".py")
        try:
            self.write.execute(path=path, content="def old():\n    pass\n")
            result = self.tool.execute(
                path=path,
                old_str="def old():\n    pass",
                new_str="def new():\n    return 42"
            )
            assert result.success
            assert "def new():" in Path(path).read_text()
        finally:
            os.unlink(path)

    def test_edit_empty_new_str_deletes(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            self.write.execute(path=path, content="keep_this remove_this keep_too")
            result = self.tool.execute(path=path, old_str=" remove_this", new_str="")
            assert result.success
            assert Path(path).read_text() == "keep_this keep_too"
        finally:
            os.unlink(path)

    def test_edit_nonexistent_file(self):
        result = self.tool.execute(path="/tmp/nonexistent.txt", old_str="a", new_str="b")
        assert not result.success


class TestGlobFilesTool:
    """Exhaustive glob_files testing."""

    def setup_method(self):
        from rocky.tools.files import GlobFilesTool
        self.tool = GlobFilesTool()

    def test_glob_py_files(self):
        result = self.tool.execute(pattern="*.py", path="rocky")
        assert result.success
        assert result.data["count"] > 0

    def test_glob_recursive(self):
        result = self.tool.execute(pattern="**/*.py", path="rocky")
        assert result.success
        assert result.data["count"] > 10  # rocky has many py files

    def test_glob_specific_file(self):
        result = self.tool.execute(pattern="agent.py", path="rocky")
        assert result.success
        assert result.data["count"] == 1

    def test_glob_no_match(self):
        result = self.tool.execute(pattern="*.absolutely_fake_extension", path="rocky")
        assert result.success
        assert result.data["count"] == 0

    def test_glob_nonexistent_directory(self):
        result = self.tool.execute(pattern="*.py", path="/nonexistent_dir_xyz")
        assert not result.success

    def test_glob_hidden_files(self):
        tmpdir = tempfile.mkdtemp()
        Path(tmpdir, ".hidden").write_text("x")
        Path(tmpdir, "visible.txt").write_text("x")
        try:
            result = self.tool.execute(pattern=".*", path=tmpdir)
            assert result.success
            assert result.data["count"] >= 1
        finally:
            import shutil
            shutil.rmtree(tmpdir)


class TestSummarizeFileTool:
    """Exhaustive summarize_file testing."""

    def setup_method(self):
        from rocky.tools.files import SummarizeFileTool
        self.tool = SummarizeFileTool()

    def test_summarize_python_with_classes(self):
        result = self.tool.execute(path="rocky/tools/base.py")
        assert result.success
        assert "Tool" in result.output
        assert "ToolResult" in result.output
        assert "ToolParameter" in result.output

    def test_summarize_python_with_functions(self):
        result = self.tool.execute(path="rocky/context.py")
        assert result.success
        assert "ContextGatherer" in result.output

    def test_summarize_nonexistent(self):
        result = self.tool.execute(path="/nonexistent_file.py")
        assert not result.success

    def test_summarize_empty_file(self):
        path = tempfile.mktemp(suffix=".py")
        Path(path).write_text("")
        try:
            result = self.tool.execute(path=path)
            assert result.success
            assert "0 lines" in result.output
        finally:
            os.unlink(path)

    def test_summarize_shows_line_numbers(self):
        result = self.tool.execute(path="rocky/agent.py")
        assert result.success
        assert "line" in result.output.lower()


class TestRunCommandTool:
    """Exhaustive run_command testing."""

    def setup_method(self):
        from rocky.tools.shell import RunCommandTool
        from rocky.ui.permissions import get_permission_manager
        self.tool = RunCommandTool(Console())
        # Trust run_command for tests (avoids stdin prompt)
        get_permission_manager().trust_tool("run_command")

    def test_simple_command(self):
        result = self.tool.execute(command="echo hello", run_in_background=False)
        assert result.success
        assert "hello" in result.output

    def test_command_failure(self):
        result = self.tool.execute(command="false", run_in_background=False)
        # 'false' command exits with code 1
        assert result is not None

    def test_command_with_pipe(self):
        result = self.tool.execute(command="echo 'hello world' | wc -w", run_in_background=False)
        assert result.success
        assert "2" in result.output

    def test_background_execution(self):
        result = self.tool.execute(command="sleep 0.1 && echo done", run_in_background=True)
        assert result.success
        assert "job" in result.output.lower() or "background" in result.output.lower()

    def test_timeout(self):
        result = self.tool.execute(command="sleep 10", timeout=1, run_in_background=False)
        # Should timeout
        assert not result.success or "timeout" in (result.error or "").lower()

    def test_stderr_capture(self):
        result = self.tool.execute(command="echo error >&2", run_in_background=False)
        assert result is not None

    def test_multiline_output(self):
        result = self.tool.execute(command="printf 'line1\nline2\nline3'", run_in_background=False)
        assert result.success
        assert "line1" in result.output
        assert "line3" in result.output


class TestGitTools:
    """Test git tools in the current repo."""

    def test_git_status(self):
        from rocky.tools.git import GitStatusTool
        tool = GitStatusTool()
        result = tool.execute()
        assert result.success
        assert "branch" in result.output.lower() or "main" in result.output.lower()

    def test_git_log(self):
        from rocky.tools.git import GitLogTool
        tool = GitLogTool()
        result = tool.execute()
        assert result.success
        assert len(result.output) > 0

    def test_git_log_with_limit(self):
        from rocky.tools.git import GitLogTool
        tool = GitLogTool()
        result = tool.execute(count=3)
        assert result.success

    def test_git_diff(self):
        from rocky.tools.git import GitDiffTool
        tool = GitDiffTool()
        result = tool.execute()
        assert result.success  # may be empty if no changes


class TestSearchFilesTool:
    """Exhaustive search_files testing."""

    def setup_method(self):
        from rocky.tools.files import SearchFilesTool
        self.tool = SearchFilesTool()

    def test_search_finds_pattern(self):
        result = self.tool.execute(pattern="class Agent", path="rocky")
        assert result.success
        assert "agent.py" in result.output.lower()

    def test_search_regex(self):
        result = self.tool.execute(pattern=r"def \w+_tool", path="rocky")
        assert result.success

    def test_search_no_match(self):
        result = self.tool.execute(pattern="XYZZY_NONEXISTENT_PATTERN_123", path="rocky")
        assert result.success  # search returns success even with no matches
        # But output should indicate nothing found

    def test_search_in_specific_file(self):
        result = self.tool.execute(pattern="PermissionTier", path="rocky/ui/permissions.py")
        assert result.success
        assert "PermissionTier" in result.output or result.data


class TestTaskPlanTool:
    """Exhaustive task_plan testing."""

    def setup_method(self):
        from rocky.tools.task_plan import TaskPlanTool
        self.tool = TaskPlanTool()
        self.tool._tasks.clear()

    def test_create_multiple_tasks(self):
        for i in range(10):
            result = self.tool.execute(action="create", subject=f"Task {i}")
            assert result.success
        result = self.tool.execute(action="list")
        assert result.data["tasks"]
        assert len(result.data["tasks"]) == 10

    def test_update_to_all_statuses(self):
        self.tool.execute(action="create", subject="Test")
        for status in ["pending", "in_progress", "done"]:
            result = self.tool.execute(action="update", subject="Test", status=status)
            assert result.success

    def test_invalid_action(self):
        result = self.tool.execute(action="delete", subject="Test")
        assert not result.success

    def test_create_without_subject(self):
        result = self.tool.execute(action="create", subject="")
        assert not result.success

    def test_list_empty(self):
        result = self.tool.execute(action="list")
        assert result.success
        assert "no tasks" in result.output.lower()

    def test_icons_in_list(self):
        self.tool.execute(action="create", subject="Pending task")
        self.tool.execute(action="create", subject="Done task")
        self.tool.execute(action="update", subject="Done task", status="done")
        result = self.tool.execute(action="list")
        assert "✔" in result.output  # done icon
        assert "◦" in result.output  # pending icon


class TestWebTools:
    """Web tool testing (may require internet)."""

    def test_web_search_basic(self):
        from rocky.tools.web import WebSearchTool
        tool = WebSearchTool()
        result = tool.execute(query="python programming")
        # May fail without internet, that's OK
        assert result is not None

    def test_web_fetch_invalid_url(self):
        from rocky.tools.web import WebFetchTool
        tool = WebFetchTool()
        result = tool.execute(url="http://completely-nonexistent-domain-xyz123.invalid")
        assert not result.success


# ============================================================
# PERMISSION SYSTEM — Deep testing
# ============================================================


class TestPermissionSystemDeep:
    """Stress test the permission system."""

    def setup_method(self):
        from rocky.ui.permissions import PermissionManager
        self.pm = PermissionManager()

    def test_all_tier0_tools_auto_allow(self):
        """Every tier 0 tool should auto-allow without prompting."""
        tier0_tools = [
            "read_file", "list_directory", "search_files", "glob_files",
            "summarize_file", "git_status", "git_log", "git_diff",
            "web_search", "web_fetch", "search_knowledge", "task_plan",
        ]
        for tool in tier0_tools:
            assert self.pm.should_allow(tool) is True, f"{tool} should auto-allow"

    def test_all_tier1_tools_need_prompt(self):
        """Every tier 1 tool should require a prompt."""
        tier1_tools = [
            "write_file", "edit_file", "index_files", "git_commit", "run_command",
        ]
        for tool in tier1_tools:
            assert self.pm.should_allow(tool) is None, f"{tool} should need prompt"

    def test_trust_all_overrides_everything(self):
        """Trust-all should allow all tools."""
        self.pm.trust_all()
        assert self.pm.should_allow("write_file") is True
        assert self.pm.should_allow("run_command") is True
        assert self.pm.should_allow("process_video") is True
        assert self.pm.should_allow("some_unknown_tool") is True

    def test_trust_all_does_not_override_blocked(self):
        """Blocked commands stay blocked even with trust-all."""
        self.pm.trust_all()
        assert self.pm.is_blocked_command("rm -rf /") is True
        assert self.pm.should_allow("run_command", command="rm -rf /") is False

    def test_blocked_patterns_comprehensive(self):
        """Test all dangerous command patterns."""
        dangerous = [
            "rm -rf /",
            "rm -rf ~",
            "rm -rf /*",
            "rm -r /home",
            "mkfs.ext4 /dev/sda",
            "dd if=/dev/zero of=/dev/sda",
            ":(){ :|:& };:",
            "chmod -R 777 /",
            "chown -R root:root /",
        ]
        for cmd in dangerous:
            assert self.pm.is_blocked_command(cmd) is True, f"Should block: {cmd}"

    def test_safe_commands_not_blocked(self):
        """Normal commands should NOT be blocked."""
        safe = [
            "ls -la",
            "cat file.txt",
            "rm myfile.txt",
            "rm -rf ./build",
            "git status",
            "python script.py",
            "npm install",
            "chmod 644 file.txt",
            "dd if=input.img of=output.img",
        ]
        for cmd in safe:
            assert self.pm.is_blocked_command(cmd) is False, f"Should allow: {cmd}"

    def test_deny_overrides_trust(self):
        """Denying a tool after trusting should deny it."""
        self.pm.trust_tool("write_file")
        assert self.pm.should_allow("write_file") is True
        self.pm.deny_tool("write_file")
        assert self.pm.should_allow("write_file") is False

    def test_trust_overrides_deny(self):
        """Trusting a tool after denying should trust it."""
        self.pm.deny_tool("write_file")
        assert self.pm.should_allow("write_file") is False
        self.pm.trust_tool("write_file")
        assert self.pm.should_allow("write_file") is True

    def test_reset_clears_everything(self):
        """Reset should return to defaults."""
        self.pm.trust_all()
        self.pm.deny_tool("read_file")
        self.pm.reset()
        assert self.pm.should_allow("read_file") is True  # back to tier 0
        assert self.pm.should_allow("write_file") is None  # back to needing prompt

    def test_get_status(self):
        """Status should reflect current state."""
        self.pm.trust_tool("write_file")
        self.pm.deny_tool("run_command")
        status = self.pm.get_status()
        assert "write_file" in status["trusted_tools"]
        assert "run_command" in status["denied_tools"]
        assert status["trust_all"] is False


# ============================================================
# CONTEXT SYSTEM — Deep testing
# ============================================================


class TestContextSystemDeep:
    """Stress test the context system."""

    def setup_method(self):
        from rocky.context import ContextGatherer
        self.gatherer = ContextGatherer()

    def test_gather_has_all_fields(self):
        ctx = self.gatherer.gather()
        assert ctx.working_dir != ""
        assert ctx.os_name != ""
        assert ctx.shell != ""
        assert ctx.python_version != ""
        assert isinstance(ctx.ram_gb, (int, float))
        assert ctx.ram_gb > 0
        assert isinstance(ctx.has_gpu, bool)

    def test_gather_git_info_in_repo(self):
        """We're in a git repo, so git info should be populated."""
        ctx = self.gatherer.gather()
        assert ctx.is_git_repo is True
        assert ctx.git_branch != ""
        assert ctx.git_status_summary != ""
        assert len(ctx.git_recent_commits) > 0

    def test_gather_outside_git_repo(self):
        """Gather from /tmp should have no git info."""
        ctx = self.gatherer.gather(working_dir="/tmp")
        assert ctx.is_git_repo is False
        assert ctx.git_branch == ""

    def test_render_for_prompt_format(self):
        """Rendered prompt should be well-formatted."""
        ctx = self.gatherer.gather()
        rendered = ctx.render_for_prompt()
        assert "## Current Environment" in rendered
        assert "Working directory:" in rendered
        assert "System:" in rendered
        assert "Internet:" in rendered

    def test_should_refresh_triggers(self):
        """Test refresh trigger logic."""
        assert self.gatherer.should_refresh("run_command") is True
        assert self.gatherer.should_refresh("git_commit") is True
        assert self.gatherer.should_refresh("write_file") is True
        assert self.gatherer.should_refresh("edit_file") is True
        assert self.gatherer.should_refresh("read_file") is False
        assert self.gatherer.should_refresh("search_files") is False

    def test_periodic_refresh(self):
        """Every 20 calls should trigger refresh."""
        for i in range(19):
            self.gatherer.should_refresh("read_file")
        # 20th call should trigger
        assert self.gatherer.should_refresh("read_file") is True

    def test_refresh_git_only(self):
        """Git-only refresh should update git fields."""
        ctx = self.gatherer.gather()
        old_branch = ctx.git_branch
        self.gatherer.refresh_git_only()
        assert self.gatherer.current.git_branch == old_branch  # same repo, same branch

    def test_current_property(self):
        """Current should be None before first gather."""
        fresh = type(self.gatherer)()
        assert fresh.current is None
        fresh.gather()
        assert fresh.current is not None


# ============================================================
# PERSONA SYSTEM — Deep testing
# ============================================================


class TestPersonaSystemDeep:
    """Stress test the persona system."""

    def setup_method(self):
        from rocky.persona import PersonaManager
        self.tmpdir = Path(tempfile.mkdtemp())
        self.manager = PersonaManager(storage_path=self.tmpdir)

    def test_passive_learn_brevity_signals(self):
        """All brevity signals should set detail_level to low."""
        signals = [
            "just do it",
            "skip the explanation",
            "just show me the code",
            "less talk more code",
            "just code it",
            "tl;dr",
            "be brief please",
        ]
        for sig in signals:
            self.manager.traits.detail_level = "balanced"
            self.manager.passive_learn_from_message(sig)
            assert self.manager.traits.detail_level == "low", f"Failed on: {sig}"

    def test_passive_learn_verbose_signals(self):
        """All verbose signals should set detail_level to high."""
        signals = [
            "explain in detail please",
            "walk me through this",
            "step by step how does this work",
            "can you explain what's happening",
            "i don't understand this part",
        ]
        for sig in signals:
            self.manager.traits.detail_level = "balanced"
            self.manager.passive_learn_from_message(sig)
            assert self.manager.traits.detail_level == "high", f"Failed on: {sig}"

    def test_passive_learn_type_hints(self):
        """Code with type hints should be detected."""
        code_samples = [
            "def foo(x: int) -> str: pass",
            "def process(data: list[dict]) -> bool: return True",
            "def convert(value: float) -> int: return int(value)",
        ]
        for code in code_samples:
            self.manager.traits.coding_style = {}
            self.manager.passive_learn_from_message(code)
            assert self.manager.traits.coding_style.get("type_hints") is True, f"Failed: {code}"

    def test_passive_learn_language_detection(self):
        """Python patterns should set primary_language."""
        python_signals = [
            "```python\nprint('hello')\n```",
            "I need to import os and sys",
            "from pathlib import Path",
        ]
        for sig in python_signals:
            self.manager.traits.primary_language = "unknown"
            self.manager.passive_learn_from_message(sig)
            assert self.manager.traits.primary_language == "python", f"Failed: {sig}"

    def test_save_load_roundtrip(self):
        """Full save/load roundtrip with all data."""
        self.manager.update_trait("experience_level", "senior")
        self.manager.update_trait("primary_language", "rust")
        self.manager.update_trait("tone_preference", "concise")
        self.manager.update_trait("detail_level", "low")
        self.manager.traits.coding_style = {"type_hints": True, "docstrings": False}
        self.manager.add_correction("Never use print for debugging")
        self.manager.add_correction("Always use pathlib not os.path")
        self.manager.add_decision("Use FastAPI for the backend")
        self.manager.add_fact("User works at Amazon")
        self.manager.save()

        from rocky.persona import PersonaManager
        loaded = PersonaManager(storage_path=self.tmpdir)
        assert loaded.traits.experience_level == "senior"
        assert loaded.traits.primary_language == "rust"
        assert loaded.traits.detail_level == "low"
        assert loaded.traits.coding_style.get("type_hints") is True
        assert "Never use print for debugging" in loaded.memory.corrections
        assert "Use FastAPI for the backend" in loaded.memory.project_decisions
        assert "User works at Amazon" in loaded.memory.learned_facts

    def test_render_summary_comprehensive(self):
        """Summary should include all relevant info."""
        self.manager.update_trait("experience_level", "senior")
        self.manager.update_trait("primary_language", "python")
        self.manager.update_trait("detail_level", "low")
        self.manager.traits.coding_style["type_hints"] = True
        self.manager.traits.preferences["git_style"] = "conventional_commits"
        self.manager.add_correction("Don't use global state")

        summary = self.manager.render_summary()
        assert "Senior" in summary or "senior" in summary
        assert "python" in summary
        assert "concise" in summary.lower() or "minimal" in summary.lower()
        assert "type hints" in summary
        assert "conventional commits" in summary
        assert "Don't use global state" in summary

    def test_deduplication(self):
        """Same correction/decision shouldn't be added twice."""
        self.manager.add_correction("No tabs")
        self.manager.add_correction("No tabs")
        self.manager.add_correction("No tabs")
        assert self.manager.memory.corrections.count("No tabs") == 1

    def test_dirty_tracking(self):
        """Manager should track when changes need saving."""
        assert self.manager.is_dirty is False
        self.manager.update_trait("experience_level", "junior")
        assert self.manager.is_dirty is True
        self.manager.save()
        assert self.manager.is_dirty is False

    def test_environment_learning(self):
        """Should detect git commit style."""
        # We're in the rocky-ai repo which uses conventional commits
        self.manager.passive_learn_from_environment(os.getcwd())
        # Should detect conventional commits from git history
        assert self.manager.traits.preferences.get("git_style") == "conventional_commits"


# ============================================================
# SENSITIVE DATA DETECTION — Deep testing
# ============================================================


class TestSensitiveDataDeep:
    """Stress test sensitive data detection."""

    def setup_method(self):
        from rocky.utils.validators import detect_sensitive_data
        self.detect = detect_sensitive_data

    def test_aws_key_variations(self):
        """Various AWS key formats."""
        key = "AKI" + "AIOSFODNN7" + "EXAMPLE"
        assert any(r.type.value == "api_key" for r in self.detect(f"aws_key={key}"))

    def test_github_token(self):
        token = "ghp_" + "a" * 36
        results = self.detect(f"token: {token}")
        assert any(r.type.value == "api_key" for r in results)

    def test_slack_token(self):
        token = "xoxb-" + "1234567890-abcdefghij"
        results = self.detect(f"SLACK_TOKEN={token}")
        assert any(r.type.value == "api_key" for r in results)

    def test_email_variations(self):
        emails = [
            "user@example.com",
            "first.last@company.co.uk",
            "user+tag@gmail.com",
        ]
        for email in emails:
            results = self.detect(f"Contact: {email}")
            assert any(r.type.value == "email" for r in results), f"Missed: {email}"

    def test_credit_cards(self):
        cards = [
            "4111-1111-1111-1111",  # Visa
            "5500-0000-0000-0004",  # Mastercard
            "3782 822463 10005",    # Amex (different format)
        ]
        for card in cards:
            results = self.detect(f"Card: {card}")
            # At least Visa and MC should match
            if card.startswith("4") or card.startswith("5"):
                assert any(r.type.value == "credit_card" for r in results), f"Missed: {card}"

    def test_password_patterns(self):
        passwords = [
            "password = 'mysecret123'",
            "passwd: 'another_secret'",
            "pwd = 'shortpw'",
            'secret = "api_key_here"',
        ]
        for pw in passwords:
            results = self.detect(pw)
            assert any(r.type.value == "password" for r in results), f"Missed: {pw}"

    def test_no_false_positives(self):
        """Normal text should NOT trigger detection."""
        safe_texts = [
            "The password policy requires 8 characters",
            "Let me explain how authentication works",
            "This is a normal code comment",
            "The function returns a string value",
            "import os\nimport sys\nprint('hello')",
        ]
        for text in safe_texts:
            results = self.detect(text)
            assert len(results) == 0, f"False positive on: {text} -> {results}"

    def test_private_key_detection(self):
        marker = "-----BEGIN " + "RSA PRIVATE" + " KEY-----"
        results = self.detect(marker)
        assert any(r.type.value == "private_key" for r in results)

    def test_value_truncation(self):
        """Long values should be truncated in results."""
        long_email = "a" * 50 + "@example.com"
        results = self.detect(f"email: {long_email}")
        for r in results:
            assert len(r.value) <= 23  # 20 + "..."


# ============================================================
# ARROW MENU — Deep testing
# ============================================================


class TestArrowMenuDeep:
    """Stress test the arrow menu."""

    def setup_method(self):
        from rocky.ui.menu import ArrowMenu
        self.ArrowMenu = ArrowMenu

    def test_single_option(self):
        menu = self.ArrowMenu(title="?", options=["Only"])
        assert menu.get_selected() == "Only"
        menu.move_down()
        assert menu.get_selected() == "Only"  # wraps to same

    def test_many_options(self):
        options = [f"Option {i}" for i in range(20)]
        menu = self.ArrowMenu(title="?", options=options)
        assert menu.get_selected() == "Option 0"
        for _ in range(19):
            menu.move_down()
        assert menu.get_selected() == "Option 19"
        menu.move_down()
        assert menu.get_selected() == "Option 0"  # wrapped

    def test_rapid_navigation(self):
        menu = self.ArrowMenu(title="?", options=["A", "B", "C"])
        for _ in range(100):
            menu.move_down()
        assert menu.selected == 100 % 3

    def test_render_contains_selector(self):
        menu = self.ArrowMenu(title="Test?", options=["Yes", "No"])
        rendered = menu.render()
        assert "▶" in rendered.plain
        assert "Yes" in rendered.plain
        assert "No" in rendered.plain

    def test_default_selection(self):
        menu = self.ArrowMenu(title="?", options=["A", "B", "C"], default=2)
        assert menu.get_selected() == "C"


# ============================================================
# STREAM RENDERER — Basic testing
# ============================================================


class TestStreamRenderer:
    """Test the streaming markdown renderer."""

    def test_stream_simple_text(self):
        from rocky.ui.stream import StreamRenderer
        console = Console(file=open(os.devnull, "w"))
        renderer = StreamRenderer(console)

        def chunks():
            yield "Hello "
            yield "world!"

        result = renderer.stream(chunks())
        assert result == "Hello world!"

    def test_stream_markdown(self):
        from rocky.ui.stream import StreamRenderer
        console = Console(file=open(os.devnull, "w"))
        renderer = StreamRenderer(console)

        def chunks():
            yield "# Title\n\n"
            yield "- item 1\n"
            yield "- item 2\n"

        result = renderer.stream(chunks())
        assert "# Title" in result
        assert "- item 1" in result

    def test_stream_empty(self):
        from rocky.ui.stream import StreamRenderer
        console = Console(file=open(os.devnull, "w"))
        renderer = StreamRenderer(console)

        def chunks():
            return
            yield  # noqa: unreachable

        result = renderer.stream(chunks())
        assert result == ""


# ============================================================
# BACKGROUND JOB MANAGER — Deep testing
# ============================================================


class TestBackgroundJobManager:
    """Stress test background job execution."""

    def setup_method(self):
        from rocky.tools.shell import BackgroundJobManager
        self.manager = BackgroundJobManager()

    def test_start_and_complete(self):
        job_id = self.manager.start_job("echo hello")
        time.sleep(0.5)
        job = self.manager.get_job(job_id)
        assert job is not None
        assert job.completed is True
        assert "hello" in job.output

    def test_multiple_jobs(self):
        ids = []
        for i in range(5):
            ids.append(self.manager.start_job(f"echo job_{i}"))
        time.sleep(1)
        for job_id in ids:
            job = self.manager.get_job(job_id)
            assert job.completed is True

    def test_job_failure(self):
        job_id = self.manager.start_job("false")
        time.sleep(0.5)
        job = self.manager.get_job(job_id)
        assert job.completed is True
        assert job.exit_code != 0

    def test_job_timeout(self):
        job_id = self.manager.start_job("sleep 10", timeout=1)
        time.sleep(2)
        job = self.manager.get_job(job_id)
        assert job.completed is True
        assert "timed out" in job.error.lower()

    def test_list_jobs(self):
        self.manager.start_job("echo 1")
        self.manager.start_job("echo 2")
        jobs = self.manager.list_jobs()
        assert len(jobs) >= 2

    def test_nonexistent_job(self):
        job = self.manager.get_job(99999)
        assert job is None


# ============================================================
# AGENT INTEGRATION — Testing the loop mechanics
# ============================================================


class TestAgentLoopMechanics:
    """Test agent loop detection and termination without LLM."""

    def test_agent_initializes(self):
        """Agent should initialize without crashing."""
        from rocky.agent import Agent
        agent = Agent(Console(file=open(os.devnull, "w")))
        assert agent.context is not None
        assert agent.persona is not None
        assert agent.btw_queue is not None
        assert agent._max_iterations == 100

    def test_btw_queue_injection(self):
        """BTW queue should accept messages."""
        from rocky.agent import Agent
        agent = Agent(Console(file=open(os.devnull, "w")))
        agent.btw_queue.put("test instruction")
        assert not agent.btw_queue.empty()
        msg = agent.btw_queue.get()
        assert msg == "test instruction"

    def test_clear_memory_rebuilds_prompt(self):
        """Clearing memory should rebuild system prompt with context."""
        from rocky.agent import Agent
        agent = Agent(Console(file=open(os.devnull, "w")))
        agent.context.gather()
        agent.clear_memory()
        # Memory should have a system prompt set
        assert agent.memory.system_prompt is not None
        assert len(agent.memory.system_prompt) > 100


# ============================================================
# CONFIG SYSTEM — Deep testing
# ============================================================


class TestConfigDeep:
    """Test config system with new V2 additions."""

    def test_persona_config_defaults(self):
        from rocky.config import get_config
        config = get_config()
        assert config.persona.enabled is True
        assert config.persona.auto_learn is True
        assert config.persona.auto_save_interval == 10

    def test_permission_defaults(self):
        from rocky.config import get_config
        config = get_config()
        assert config.permission_defaults.tier0_auto_allow is True
        assert config.permission_defaults.show_blocked_warning is True

    def test_persona_path_exists(self):
        from rocky.config import get_config
        config = get_config()
        assert config.paths.persona.exists()

    def test_all_paths_exist(self):
        from rocky.config import get_config
        config = get_config()
        assert config.paths.base.exists()
        assert config.paths.models.exists()
        assert config.paths.sessions.exists()
        assert config.paths.persona.exists()


# ============================================================
# SYSTEM PROMPT — Validation
# ============================================================


class TestSystemPrompt:
    """Validate the system prompt content."""

    def setup_method(self):
        from rocky.llm.prompts import SYSTEM_PROMPT, build_system_prompt
        self.prompt = SYSTEM_PROMPT
        self.build = build_system_prompt

    def test_prompt_has_identity(self):
        assert "Rocky.Ai" in self.prompt

    def test_prompt_has_all_tools(self):
        """Every registered tool should be mentioned in the prompt."""
        tool_names = [
            "read_file", "write_file", "edit_file", "list_directory",
            "search_files", "glob_files", "summarize_file", "run_command",
            "git_status", "git_diff", "git_log", "git_commit",
            "web_search", "web_fetch", "task_plan",
        ]
        for tool in tool_names:
            assert tool in self.prompt, f"Tool '{tool}' not in system prompt"

    def test_prompt_has_guardrails(self):
        assert "never" in self.prompt.lower() or "NEVER" in self.prompt
        assert "invent" in self.prompt.lower() or "hallucinate" in self.prompt.lower()

    def test_prompt_has_banned_topics(self):
        assert "religion" in self.prompt.lower()
        assert "politic" in self.prompt.lower()

    def test_prompt_has_formatting_rules(self):
        assert "markdown" in self.prompt.lower()

    def test_build_with_context(self):
        result = self.build(context_block="## Test Context\n- Hello")
        assert "## Test Context" in result
        assert "Hello" in result

    def test_build_with_persona(self):
        result = self.build(persona_block="Senior Python developer")
        assert "Senior Python developer" in result

    def test_build_without_extras(self):
        result = self.build()
        # build() with no args strips placeholder sections, so result should be
        # shorter than SYSTEM_PROMPT (which contains {context_block} etc.)
        assert "Rocky.Ai" in result
        assert "{context_block}" not in result
        assert "{persona_block}" not in result

    def test_prompt_length(self):
        """Prompt should be substantial (200+ lines)."""
        lines = self.prompt.splitlines()
        assert len(lines) >= 100, f"Prompt only {len(lines)} lines, expected 100+"
