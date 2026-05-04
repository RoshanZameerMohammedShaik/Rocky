"""Tests for user persona system."""
import tempfile
from pathlib import Path
from rocky.persona import PersonaManager


class TestPersonaManager:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.manager = PersonaManager(storage_path=self.tmpdir)

    def test_initial_state_empty(self):
        assert self.manager.traits.experience_level == "unknown"
        assert len(self.manager.memory.corrections) == 0

    def test_update_trait(self):
        self.manager.update_trait("experience_level", "senior")
        assert self.manager.traits.experience_level == "senior"

    def test_add_correction(self):
        self.manager.add_correction("Don't use print for debugging")
        assert "Don't use print for debugging" in self.manager.memory.corrections

    def test_add_project_decision(self):
        self.manager.add_decision("Using Flask for the API")
        assert "Using Flask for the API" in self.manager.memory.project_decisions

    def test_save_and_load(self):
        self.manager.update_trait("primary_language", "python")
        self.manager.add_correction("No print debugging")
        self.manager.save()

        # Load fresh
        manager2 = PersonaManager(storage_path=self.tmpdir)
        manager2.load()
        assert manager2.traits.primary_language == "python"
        assert "No print debugging" in manager2.memory.corrections

    def test_render_summary(self):
        self.manager.update_trait("experience_level", "senior")
        self.manager.update_trait("primary_language", "python")
        self.manager.update_trait("tone_preference", "concise")
        summary = self.manager.render_summary()
        assert "senior" in summary.lower() or "Senior" in summary

    def test_passive_learn_concise(self):
        # Simulates user saying "just do it"
        self.manager.passive_learn_from_message("just do it, skip the explanation")
        assert self.manager.traits.detail_level == "low"

    def test_passive_learn_type_hints(self):
        code = "def foo(x: int) -> str:\n    return str(x)"
        self.manager.passive_learn_from_message(code)
        assert self.manager.traits.coding_style.get("type_hints") is True
