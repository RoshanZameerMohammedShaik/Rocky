"""Tests for permission system."""
from rocky.ui.permissions import PermissionManager, PermissionTier


class TestPermissionTiers:
    def test_read_tools_are_tier_0(self):
        pm = PermissionManager()
        assert pm.get_tier("read_file") == PermissionTier.AUTO_ALLOW
        assert pm.get_tier("list_directory") == PermissionTier.AUTO_ALLOW
        assert pm.get_tier("search_files") == PermissionTier.AUTO_ALLOW
        assert pm.get_tier("git_status") == PermissionTier.AUTO_ALLOW

    def test_write_tools_are_tier_1(self):
        pm = PermissionManager()
        assert pm.get_tier("write_file") == PermissionTier.PROMPT
        assert pm.get_tier("edit_file") == PermissionTier.PROMPT
        assert pm.get_tier("run_command") == PermissionTier.PROMPT

    def test_unknown_tool_defaults_to_prompt(self):
        pm = PermissionManager()
        assert pm.get_tier("unknown_tool") == PermissionTier.PROMPT


class TestPermissionState:
    def test_tier_0_auto_allows(self):
        pm = PermissionManager()
        assert pm.should_allow("read_file") is True

    def test_tier_1_requires_decision(self):
        pm = PermissionManager()
        assert pm.should_allow("write_file") is None  # needs prompt

    def test_trust_tool(self):
        pm = PermissionManager()
        pm.trust_tool("write_file")
        assert pm.should_allow("write_file") is True

    def test_deny_tool(self):
        pm = PermissionManager()
        pm.deny_tool("run_command")
        assert pm.should_allow("run_command") is False

    def test_trust_all(self):
        pm = PermissionManager()
        pm.trust_all()
        assert pm.should_allow("write_file") is True
        assert pm.should_allow("run_command") is True

    def test_reset(self):
        pm = PermissionManager()
        pm.trust_all()
        pm.reset()
        assert pm.should_allow("write_file") is None  # back to prompt

    def test_blocked_commands_always_blocked(self):
        pm = PermissionManager()
        pm.trust_all()
        assert pm.is_blocked_command("rm -rf /") is True
        assert pm.is_blocked_command("ls -la") is False
