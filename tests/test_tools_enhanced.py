"""Tests for enhanced file tools."""
import os
import tempfile
from rocky.tools.files import EditFileTool, GlobFilesTool, SummarizeFileTool, WriteFileTool


class TestEditFileReplaceAll:
    def test_replace_all_multiple_occurrences(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            WriteFileTool().execute(path=path, content="foo bar foo baz foo")
            tool = EditFileTool()
            result = tool.execute(path=path, old_str="foo", new_str="qux", replace_all=True)
            assert result.success

            from rocky.tools.files import ReadFileTool
            content = ReadFileTool().execute(path=path).output
            assert content == "qux bar qux baz qux"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_replace_all_false_fails_on_multiple(self):
        path = tempfile.mktemp(suffix=".txt")
        try:
            WriteFileTool().execute(path=path, content="foo bar foo")
            tool = EditFileTool()
            result = tool.execute(path=path, old_str="foo", new_str="qux", replace_all=False)
            assert not result.success
            assert "found 2 times" in result.error.lower()
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestGlobFiles:
    def test_glob_finds_python_files(self):
        tool = GlobFilesTool()
        result = tool.execute(pattern="*.py", path="rocky")
        assert result.success
        assert result.data["count"] > 0

    def test_glob_recursive(self):
        tool = GlobFilesTool()
        result = tool.execute(pattern="**/*.py", path="rocky")
        assert result.success
        assert result.data["count"] > 5

    def test_glob_no_matches(self):
        tool = GlobFilesTool()
        result = tool.execute(pattern="*.xyz_nonexistent", path="rocky")
        assert result.success
        assert result.data["count"] == 0


class TestSummarizeFile:
    def test_summarize_python_file(self):
        tool = SummarizeFileTool()
        result = tool.execute(path="rocky/tools/base.py")
        assert result.success
        assert "Tool" in result.output
        assert "ToolRegistry" in result.output

    def test_summarize_nonexistent(self):
        tool = SummarizeFileTool()
        result = tool.execute(path="/nonexistent.py")
        assert not result.success
