"""Tests for dynamic context system."""
from rocky.context import SessionContext, ContextGatherer


class TestContextGatherer:
    def test_gather_returns_context(self):
        gatherer = ContextGatherer()
        ctx = gatherer.gather()
        assert isinstance(ctx, SessionContext)
        assert ctx.working_dir != ""
        assert ctx.os_name in ("Linux", "Darwin", "Windows")

    def test_working_dir_is_cwd(self):
        import os
        gatherer = ContextGatherer()
        ctx = gatherer.gather()
        assert ctx.working_dir == os.getcwd()

    def test_render_for_prompt(self):
        gatherer = ContextGatherer()
        ctx = gatherer.gather()
        rendered = ctx.render_for_prompt()
        assert "Working directory:" in rendered
        assert "System:" in rendered

    def test_refresh_updates_context(self):
        gatherer = ContextGatherer()
        ctx1 = gatherer.gather()
        ctx2 = gatherer.gather()
        assert ctx1.working_dir == ctx2.working_dir
