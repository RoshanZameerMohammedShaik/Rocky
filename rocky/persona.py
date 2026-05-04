"""User persona system for Rocky.Ai.

Learns user preferences, personality, and project context across sessions.
Stores locally in ~/.rocky/persona/. Never transmits data.
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from rocky.config import get_config
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PersonaTraits:
    """Observable user traits."""
    experience_level: str = "unknown"
    primary_language: str = "unknown"
    tone_preference: str = "balanced"
    detail_level: str = "balanced"
    coding_style: dict = field(default_factory=dict)
    preferences: dict = field(default_factory=dict)
    personality: dict = field(default_factory=dict)


@dataclass
class PersonaMemory:
    """Learned facts and corrections."""
    project_decisions: list[str] = field(default_factory=list)
    learned_facts: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)


class PersonaManager:
    """Manages user persona learning and persistence."""

    def __init__(self, storage_path: Optional[Path] = None):
        config = get_config()
        self.storage_path = storage_path or config.paths.persona
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.traits = PersonaTraits()
        self.memory = PersonaMemory()
        self._dirty = False
        self.load()

    def load(self):
        """Load persona from disk."""
        persona_file = self.storage_path / "persona.yaml"
        memory_file = self.storage_path / "memory.yaml"

        if persona_file.exists():
            try:
                data = yaml.safe_load(persona_file.read_text()) or {}
                traits = data.get("traits", {})
                self.traits = PersonaTraits(
                    experience_level=traits.get("experience_level", "unknown"),
                    primary_language=traits.get("primary_language", "unknown"),
                    tone_preference=traits.get("tone_preference", "balanced"),
                    detail_level=traits.get("detail_level", "balanced"),
                    coding_style=traits.get("coding_style", {}),
                    preferences=traits.get("preferences", {}),
                    personality=traits.get("personality", {}),
                )
            except Exception as e:
                logger.warning(f"Failed to load persona: {e}")

        if memory_file.exists():
            try:
                data = yaml.safe_load(memory_file.read_text()) or {}
                self.memory = PersonaMemory(
                    project_decisions=data.get("project_decisions", []),
                    learned_facts=data.get("learned_facts", []),
                    corrections=data.get("corrections", []),
                )
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}")

    def save(self):
        """Save persona and memory to disk."""
        persona_file = self.storage_path / "persona.yaml"
        memory_file = self.storage_path / "memory.yaml"

        persona_data = {
            "traits": {
                "experience_level": self.traits.experience_level,
                "primary_language": self.traits.primary_language,
                "tone_preference": self.traits.tone_preference,
                "detail_level": self.traits.detail_level,
                "coding_style": self.traits.coding_style,
                "preferences": self.traits.preferences,
                "personality": self.traits.personality,
            }
        }

        memory_data = {
            "project_decisions": self.memory.project_decisions[-50:],
            "learned_facts": self.memory.learned_facts[-50:],
            "corrections": self.memory.corrections[-30:],
        }

        persona_file.write_text(yaml.dump(persona_data, default_flow_style=False))
        memory_file.write_text(yaml.dump(memory_data, default_flow_style=False))
        self._dirty = False

    def update_trait(self, key: str, value):
        """Update a persona trait."""
        if hasattr(self.traits, key):
            setattr(self.traits, key, value)
            self._dirty = True

    def add_correction(self, correction: str):
        """Add a user correction."""
        if correction not in self.memory.corrections:
            self.memory.corrections.append(correction)
            self._dirty = True

    def add_decision(self, decision: str):
        """Add a project decision."""
        if decision not in self.memory.project_decisions:
            self.memory.project_decisions.append(decision)
            self._dirty = True

    def add_fact(self, fact: str):
        """Add a learned fact."""
        if fact not in self.memory.learned_facts:
            self.memory.learned_facts.append(fact)
            self._dirty = True

    def passive_learn_from_message(self, message: str):
        """Extract persona signals from a user message (rule-based heuristics)."""
        msg_lower = message.lower()

        # Detail level
        brevity_signals = ["just do it", "skip the explanation", "just show me",
                           "less talk", "just code", "tl;dr", "be brief"]
        if any(s in msg_lower for s in brevity_signals):
            self.traits.detail_level = "low"
            self._dirty = True

        verbose_signals = ["explain in detail", "walk me through", "step by step",
                           "can you explain", "i don't understand"]
        if any(s in msg_lower for s in verbose_signals):
            self.traits.detail_level = "high"
            self._dirty = True

        # Type hints detection
        if re.search(r"def\s+\w+\(.*:\s*\w+.*\)\s*->", message):
            self.traits.coding_style["type_hints"] = True
            self._dirty = True

        # Language detection
        if re.search(r"```python|\.py\b|import\s+\w+|from\s+\w+\s+import", message):
            if self.traits.primary_language == "unknown":
                self.traits.primary_language = "python"
                self._dirty = True

    def passive_learn_from_environment(self, working_dir: str):
        """Learn from project environment."""
        wd = Path(working_dir)

        # Editor detection
        if (wd / ".vscode").exists():
            self.traits.preferences["editor"] = "vscode"
        elif (wd / ".idea").exists():
            self.traits.preferences["editor"] = "jetbrains"

        # Git commit style
        try:
            import subprocess
            result = subprocess.run(
                ["git", "-P", "log", "--oneline", "-n10"],
                cwd=working_dir, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                commits = result.stdout.strip().splitlines()
                conventional = sum(
                    1 for c in commits
                    if re.match(r"[a-f0-9]+\s+(feat|fix|docs|style|refactor|perf|test|chore)", c)
                )
                if conventional >= 5:
                    self.traits.preferences["git_style"] = "conventional_commits"
        except Exception:
            pass

    def render_summary(self) -> str:
        """Render a concise persona summary for the system prompt."""
        parts = []

        if self.traits.experience_level != "unknown":
            parts.append(f"{self.traits.experience_level.capitalize()} developer")

        if self.traits.primary_language != "unknown":
            parts.append(f"works in {self.traits.primary_language}")

        if self.traits.tone_preference != "balanced":
            parts.append(f"prefers {self.traits.tone_preference} responses")

        if self.traits.detail_level == "low":
            parts.append("wants concise answers with code, minimal explanation")
        elif self.traits.detail_level == "high":
            parts.append("appreciates detailed explanations")

        style_parts = []
        if self.traits.coding_style.get("type_hints"):
            style_parts.append("type hints")
        if self.traits.preferences.get("test_style"):
            style_parts.append(self.traits.preferences["test_style"])
        if self.traits.preferences.get("git_style"):
            style_parts.append("conventional commits")
        if style_parts:
            parts.append(f"uses {', '.join(style_parts)}")

        summary = ". ".join(parts) + "." if parts else ""

        if self.memory.corrections:
            recent = self.memory.corrections[-3:]
            summary += "\nCorrections: " + "; ".join(recent)

        return summary

    @property
    def is_dirty(self) -> bool:
        return self._dirty
