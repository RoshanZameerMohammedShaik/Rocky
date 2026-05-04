# Rocky.Ai V2 Tool System Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Rocky from a single-tool-call assistant into a fully agentic AI with multi-step reasoning, user persona learning, granular permissions, and polished terminal UI.

**Architecture:** Layered enhancement — each component built and tested independently. Foundation (UI components, utils) first, then core systems (context, persona, permissions), then the agent loop rewrite, then CLI integration.

**Tech Stack:** Python 3.10+, llama-cpp-python, Rich (Live, Spinner, Progress, Markdown), prompt-toolkit, PyYAML, cryptography (Fernet)

**Spec:** `docs/specs/2026-05-04-tool-system-overhaul-design.md`

---

## Task 1: Add `cryptography` dependency and update test infrastructure

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/test_rocky.py`

- [ ] **Step 1: Add cryptography to dependencies**

```toml
# In pyproject.toml [project] dependencies, add:
dependencies = [
    "llama-cpp-python>=0.2.80",
    "httpx>=0.25.0",
    "rich>=13.0.0",
    "prompt-toolkit>=3.0.0",
    "pyyaml>=6.0",
    "beautifulsoup4>=4.12.0",
    "cryptography>=41.0.0",
]
```

- [ ] **Step 2: Remove outdated Ollama tests from test_rocky.py**

Delete `class TestOllamaClient` (lines 183-199) — references deleted module.

- [ ] **Step 3: Fix TestConfig default assertion**

Change line 15 from:
```python
assert config.model.default == "llama3.2:3b"
```
to:
```python
assert config.model.default == "auto"
```

- [ ] **Step 4: Install and verify**

Run: `cd ~/rocky-ai && pip install -e ".[dev]" 2>&1 | tail -5`
Run: `pytest tests/test_rocky.py -v 2>&1 | tail -20`
Expected: All tests pass (minus Ollama tests which are removed)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/test_rocky.py
git commit -m "chore: add cryptography dep, fix outdated tests"
```

---

## Task 2: UI Foundation — Arrow-Key Menu (`rocky/ui/menu.py`)

**Files:**
- Create: `rocky/ui/menu.py`
- Create: `tests/test_menu.py`

- [ ] **Step 1: Write test for menu selection**

```python
# tests/test_menu.py
"""Tests for arrow-key menu."""
import pytest
from unittest.mock import patch, MagicMock
from rocky.ui.menu import ArrowMenu


class TestArrowMenu:
    def test_menu_creation(self):
        menu = ArrowMenu(
            title="Test?",
            options=["Yes", "No", "Maybe"],
            default=0
        )
        assert menu.selected == 0
        assert len(menu.options) == 3

    def test_move_down(self):
        menu = ArrowMenu(title="Test?", options=["A", "B", "C"])
        menu.move_down()
        assert menu.selected == 1
        menu.move_down()
        assert menu.selected == 2

    def test_move_down_wraps(self):
        menu = ArrowMenu(title="Test?", options=["A", "B", "C"])
        menu.move_down()
        menu.move_down()
        menu.move_down()
        assert menu.selected == 0  # wraps to top

    def test_move_up(self):
        menu = ArrowMenu(title="Test?", options=["A", "B", "C"], default=2)
        menu.move_up()
        assert menu.selected == 1

    def test_move_up_wraps(self):
        menu = ArrowMenu(title="Test?", options=["A", "B", "C"], default=0)
        menu.move_up()
        assert menu.selected == 2  # wraps to bottom

    def test_get_selected(self):
        menu = ArrowMenu(title="Test?", options=["Yes", "No", "Maybe"], default=1)
        assert menu.get_selected() == "No"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_menu.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement ArrowMenu**

```python
# rocky/ui/menu.py
"""Arrow-key menu selector for Rocky.Ai.

Reusable interactive menu with blue ▶ selector.
Used for: quit confirmation, permission prompts, sensitive data prompt.
"""

import sys
from typing import Optional
from rich.console import Console
from rich.text import Text
from rich.live import Live


SELECTOR = "▶"
SELECTOR_STYLE = "bold blue"


class ArrowMenu:
    """Interactive arrow-key menu with blue ▶ selector."""

    def __init__(
        self,
        title: str,
        options: list[str],
        default: int = 0,
        console: Optional[Console] = None,
    ):
        self.title = title
        self.options = options
        self.selected = default
        self.console = console or Console()

    def move_down(self):
        self.selected = (self.selected + 1) % len(self.options)

    def move_up(self):
        self.selected = (self.selected - 1) % len(self.options)

    def get_selected(self) -> str:
        return self.options[self.selected]

    def render(self) -> Text:
        """Render the menu as Rich Text."""
        output = Text()
        output.append(f"  {self.title}\n\n", style="bold")

        for i, option in enumerate(self.options):
            if i == self.selected:
                output.append(f"    {SELECTOR} ", style=SELECTOR_STYLE)
                output.append(f"{option}\n", style="bold white")
            else:
                output.append(f"      {option}\n", style="dim")

        return output

    def run(self) -> str:
        """Run the interactive menu. Returns selected option string."""
        try:
            import tty
            import termios

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

            try:
                tty.setraw(fd)

                with Live(
                    self.render(),
                    console=self.console,
                    refresh_per_second=30,
                    transient=True,
                ) as live:
                    while True:
                        ch = sys.stdin.read(1)

                        if ch == "\r" or ch == "\n":
                            break
                        elif ch == "\x1b":
                            seq = sys.stdin.read(2)
                            if seq == "[A":  # Up arrow
                                self.move_up()
                            elif seq == "[B":  # Down arrow
                                self.move_down()

                        live.update(self.render())

            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        except (ImportError, termios.error, ValueError):
            # Fallback for non-Unix or piped input
            self.console.print(self.render())
            self.console.print()
            choices = [str(i + 1) for i in range(len(self.options))]
            from rich.prompt import Prompt
            choice = Prompt.ask(
                "Select",
                choices=choices,
                default=str(self.selected + 1),
            )
            self.selected = int(choice) - 1

        # Print final state
        selected_text = Text()
        selected_text.append(f"    {SELECTOR} ", style=SELECTOR_STYLE)
        selected_text.append(self.get_selected(), style="bold white")
        self.console.print(selected_text)

        return self.get_selected()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_menu.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add rocky/ui/menu.py tests/test_menu.py
git commit -m "feat(ui): add arrow-key menu selector with blue ▶"
```

---

## Task 3: UI Foundation — Updated Icons & Spinner (`rocky/ui/animations.py`)

**Files:**
- Modify: `rocky/ui/animations.py`

- [ ] **Step 1: Update ICONS dict and add spinner utilities**

Replace the `ICONS` dict at the top of `rocky/ui/animations.py` with:

```python
from rich.text import Text
from rich.spinner import Spinner

# Fixed-width status icons (width=2 for alignment)
ICONS = {
    "done": "✔",
    "fail": "✘",
    "warn": "⚠",
    "pending": "◦",
    "processing": "⠧",  # placeholder for spinner display
}

ICON_STYLES = {
    "done": "green",
    "fail": "red",
    "warn": "yellow",
    "pending": "red",
    "processing": "cyan",
}


def icon_text(name: str, pad: int = 2) -> Text:
    """Get a fixed-width icon as Rich Text for alignment."""
    char = ICONS.get(name, "•")
    style = ICON_STYLES.get(name, "")
    t = Text(f"{char:>{pad}}", style=style)
    return t


def get_spinner() -> Spinner:
    """Get the standard Rocky braille dot spinner."""
    return Spinner("dots", style="cyan")
```

- [ ] **Step 2: Keep existing animation functions intact**

The `show_write_lines`, `show_edit_diff`, `show_read_shimmer`, `RectangularLoader`, etc. remain unchanged. Only the ICONS section and imports get updated.

- [ ] **Step 3: Verify build**

Run: `python -c "from rocky.ui.animations import ICONS, icon_text, get_spinner; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add rocky/ui/animations.py
git commit -m "feat(ui): update icons to ✔/✘/⚠/◦ with fixed-width alignment"
```

---

## Task 4: UI Foundation — Rich Live Markdown Streaming (`rocky/ui/stream.py`)

**Files:**
- Create: `rocky/ui/stream.py`

- [ ] **Step 1: Implement streaming markdown renderer**

```python
# rocky/ui/stream.py
"""Rich Live markdown streaming renderer for Rocky.Ai.

Streams LLM response tokens through Rich Markdown for progressive rendering.
Tables, code blocks, and lists format as they stream in.
"""

from typing import Generator
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text


class StreamRenderer:
    """Renders streaming LLM output as formatted markdown."""

    def __init__(self, console: Console):
        self.console = console
        self._buffer = ""

    def stream(self, chunks: Generator[str, None, None]) -> str:
        """Stream chunks and render as markdown progressively.

        Returns the full accumulated response text.
        """
        self._buffer = ""

        with Live(
            Text(""),
            console=self.console,
            refresh_per_second=10,
            vertical_overflow="visible",
        ) as live:
            for chunk in chunks:
                self._buffer += chunk
                # Render current buffer as markdown
                try:
                    live.update(Markdown(self._buffer))
                except Exception:
                    # Fallback: render as plain text if markdown parsing fails mid-stream
                    live.update(Text(self._buffer))

        return self._buffer

    def show_thinking(self) -> Live:
        """Show thinking spinner. Caller manages the context."""
        spinner = Spinner("dots", text="Thinking...", style="cyan")
        return Live(spinner, console=self.console, refresh_per_second=10)
```

- [ ] **Step 2: Verify import**

Run: `python -c "from rocky.ui.stream import StreamRenderer; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add rocky/ui/stream.py
git commit -m "feat(ui): add Rich Live markdown streaming renderer"
```

---

## Task 5: Enhanced Validators — Sensitive Data Detection (`rocky/utils/validators.py`)

**Files:**
- Modify: `rocky/utils/validators.py`
- Create: `tests/test_validators_sensitive.py`

- [ ] **Step 1: Write tests for sensitive data detection**

```python
# tests/test_validators_sensitive.py
"""Tests for sensitive data detection."""
import pytest
from rocky.utils.validators import detect_sensitive_data, SensitiveDataType


class TestSensitiveDataDetection:
    def test_detects_email(self):
        results = detect_sensitive_data("Contact me at user@example.com please")
        assert any(r.type == SensitiveDataType.EMAIL for r in results)

    def test_detects_api_key_aws(self):
        # Construct test key dynamically to avoid static scanning
        test_key = "AKI" + "AIOSFODNN7" + "EXAMPLE"
        results = detect_sensitive_data(f"Key: {test_key}")
        assert any(r.type == SensitiveDataType.API_KEY for r in results)

    def test_detects_phone(self):
        results = detect_sensitive_data("Call 555-123-4567")
        assert any(r.type == SensitiveDataType.PHONE for r in results)

    def test_detects_credit_card(self):
        results = detect_sensitive_data("Card: 4111-1111-1111-1111")
        assert any(r.type == SensitiveDataType.CREDIT_CARD for r in results)

    def test_detects_private_key(self):
        # Construct test marker dynamically to avoid static scanning
        marker = "-----BEGIN " + "RSA PRIVATE" + " KEY-----"
        results = detect_sensitive_data(marker)
        assert any(r.type == SensitiveDataType.PRIVATE_KEY for r in results)

    def test_no_false_positive_on_normal_text(self):
        results = detect_sensitive_data("Just a normal sentence about coding")
        assert len(results) == 0

    def test_detects_password_pattern(self):
        results = detect_sensitive_data("password = 'super_secret_123'")
        assert any(r.type == SensitiveDataType.PASSWORD for r in results)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_validators_sensitive.py -v`
Expected: FAIL — SensitiveDataType not found

- [ ] **Step 3: Add sensitive data detection to validators.py**

Append to `rocky/utils/validators.py`:

```python
from dataclasses import dataclass
from enum import Enum


class SensitiveDataType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    API_KEY = "api_key"
    PASSWORD = "password"
    CREDIT_CARD = "credit_card"
    PRIVATE_KEY = "private_key"


@dataclass
class SensitiveDataMatch:
    type: SensitiveDataType
    value: str
    description: str


# Patterns for sensitive data detection
SENSITIVE_PATTERNS = [
    (SensitiveDataType.PRIVATE_KEY, r"-----BEGIN\s+(RSA |EC |DSA )?PRIVATE KEY" + "-----", "Private key detected"),
    (SensitiveDataType.API_KEY, r"(?:AKI" + r"A|ABIA|ACCA|ASIA)[0-9A-Z]{16}", "AWS access key"),
    (SensitiveDataType.API_KEY, r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}", "GitHub token"),
    (SensitiveDataType.API_KEY, r"sk-[A-Za-z0-9]{32,}", "API secret key"),
    (SensitiveDataType.API_KEY, r"xox[baprs]-[0-9A-Za-z\-]{10,}", "Slack token"),
    (SensitiveDataType.CREDIT_CARD, r"\b(?:4[0-9]{3}|5[1-5][0-9]{2}|3[47][0-9]{1})[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}\b", "Credit card number"),
    (SensitiveDataType.SSN, r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "Possible SSN"),
    (SensitiveDataType.PASSWORD, r"""(?:password|passwd|pwd|secret)\s*[=:]\s*['"][^'"]{4,}['"]""", "Password in assignment"),
    (SensitiveDataType.PHONE, r"\b(?:\+1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b", "Phone number"),
    (SensitiveDataType.EMAIL, r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b", "Email address"),
]

_sensitive_compiled = [(t, re.compile(p, re.IGNORECASE), d) for t, p, d in SENSITIVE_PATTERNS]


def detect_sensitive_data(text: str) -> list[SensitiveDataMatch]:
    """Detect sensitive data patterns in text."""
    matches = []
    for data_type, pattern, description in _sensitive_compiled:
        for match in pattern.finditer(text):
            matches.append(SensitiveDataMatch(
                type=data_type,
                value=match.group(0)[:20] + "..." if len(match.group(0)) > 20 else match.group(0),
                description=description,
            ))
    return matches
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_validators_sensitive.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add rocky/utils/validators.py tests/test_validators_sensitive.py
git commit -m "feat(utils): add sensitive data detection patterns"
```

---

## Task 6: Config Enhancements (`rocky/config.py`)

**Files:**
- Modify: `rocky/config.py`

- [ ] **Step 1: Add PersonaConfig and PermissionConfig dataclasses**

Add after `class OfflineConfig`:

```python
@dataclass
class PersonaConfig:
    enabled: bool = True
    auto_learn: bool = True  # passive learning from conversations
    auto_save_interval: int = 10  # auto-save persona every N turns


@dataclass
class PermissionDefaults:
    """Default permission behavior."""
    tier0_auto_allow: bool = True  # reads always allowed
    show_blocked_warning: bool = True
```

- [ ] **Step 2: Add persona paths to PathsConfig**

```python
@dataclass
class PathsConfig:
    base: Path = field(default_factory=lambda: Path.home() / ".rocky")
    models: Path = field(default_factory=lambda: Path.home() / ".rocky" / "models")
    sessions: Path = field(default_factory=lambda: Path.home() / ".rocky" / "sessions")
    knowledge: Path = field(default_factory=lambda: Path.home() / ".rocky" / "knowledge")
    logs: Path = field(default_factory=lambda: Path.home() / ".rocky" / "logs")
    persona: Path = field(default_factory=lambda: Path.home() / ".rocky" / "persona")
```

- [ ] **Step 3: Add new configs to Config class**

```python
@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    permissions: PermissionsConfig = field(default_factory=PermissionsConfig)
    permission_defaults: PermissionDefaults = field(default_factory=PermissionDefaults)
    persona: PersonaConfig = field(default_factory=PersonaConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    offline: OfflineConfig = field(default_factory=OfflineConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
```

- [ ] **Step 4: Add persona path to directory creation in Config.load()**

Add `config.paths.persona` to the list of paths created:
```python
for path_field in [config.paths.base, config.paths.models,
                   config.paths.sessions, config.paths.knowledge,
                   config.paths.logs, config.paths.persona]:
    path_field.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 5: Verify**

Run: `python -c "from rocky.config import get_config; c = get_config(); print(c.paths.persona)"`
Expected: `/home/<user>/.rocky/persona`

- [ ] **Step 6: Commit**

```bash
git add rocky/config.py
git commit -m "feat(config): add persona and permission config sections"
```

---

## Task 7: Dynamic Context System (`rocky/context.py`)

**Files:**
- Create: `rocky/context.py`
- Create: `tests/test_context.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_context.py
"""Tests for dynamic context system."""
import pytest
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement context.py**

```python
# rocky/context.py
"""Dynamic environment context for Rocky.Ai.

Auto-gathers system state and injects into the system prompt.
Refreshes automatically after state-changing tool calls.
"""

import os
import subprocess
import platform
from dataclasses import dataclass, field
from typing import Optional
from rocky.utils.platform import get_memory_gb, has_gpu, get_cpu_count
from rocky.utils.network import is_online
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SessionContext:
    """Environment context gathered at session start."""

    working_dir: str = ""
    is_git_repo: bool = False
    git_branch: str = ""
    git_status_summary: str = ""
    git_recent_commits: list[str] = field(default_factory=list)
    os_name: str = ""
    shell: str = ""
    python_version: str = ""
    ram_gb: int = 0
    has_gpu: bool = False
    gpu_name: str = ""
    internet_available: bool = False
    current_model: str = ""
    user_persona_summary: str = ""

    def render_for_prompt(self) -> str:
        """Render context as text for system prompt injection."""
        lines = ["## Current Environment"]
        lines.append(f"- Working directory: {self.working_dir}")

        if self.is_git_repo:
            lines.append(f"- Git: {self.git_branch} branch, {self.git_status_summary}")
            if self.git_recent_commits:
                commits = ", ".join(self.git_recent_commits[:5])
                lines.append(f"- Recent commits: {commits}")

        gpu_info = f", {self.gpu_name}" if self.has_gpu else ""
        lines.append(
            f"- System: {self.os_name}, {self.shell}, "
            f"Python {self.python_version}, {self.ram_gb}GB RAM{gpu_info}"
        )

        if self.current_model:
            lines.append(f"- Model: {self.current_model}")

        status = "available" if self.internet_available else "offline"
        lines.append(f"- Internet: {status}")

        if self.user_persona_summary:
            lines.append("")
            lines.append("## About This User")
            lines.append(self.user_persona_summary)

        return "\n".join(lines)


class ContextGatherer:
    """Gathers environment context."""

    def __init__(self):
        self._last_context: Optional[SessionContext] = None
        self._call_count = 0

    def gather(self, working_dir: Optional[str] = None) -> SessionContext:
        """Gather full environment context."""
        ctx = SessionContext()

        ctx.working_dir = working_dir or os.getcwd()
        ctx.os_name = platform.system()
        ctx.shell = os.environ.get("SHELL", "unknown")
        ctx.python_version = platform.python_version()
        ctx.ram_gb = get_memory_gb()
        ctx.has_gpu = has_gpu()
        ctx.internet_available = is_online()

        # GPU name
        if ctx.has_gpu:
            ctx.gpu_name = self._get_gpu_name()

        # Git info
        git_info = self._get_git_info(ctx.working_dir)
        if git_info:
            ctx.is_git_repo = True
            ctx.git_branch = git_info.get("branch", "")
            ctx.git_status_summary = git_info.get("status", "")
            ctx.git_recent_commits = git_info.get("commits", [])

        self._last_context = ctx
        return ctx

    def refresh_git_only(self, working_dir: Optional[str] = None) -> None:
        """Lightweight refresh — only git state."""
        if self._last_context is None:
            self.gather(working_dir)
            return

        wd = working_dir or self._last_context.working_dir
        git_info = self._get_git_info(wd)
        if git_info:
            self._last_context.git_branch = git_info.get("branch", "")
            self._last_context.git_status_summary = git_info.get("status", "")
            self._last_context.git_recent_commits = git_info.get("commits", [])

    def should_refresh(self, tool_name: str) -> bool:
        """Check if a tool call should trigger context refresh."""
        self._call_count += 1

        # Full refresh triggers
        if tool_name == "run_command":
            return True  # might have cd'd

        # Git-only refresh triggers
        git_tools = {"git_commit", "write_file", "edit_file"}
        if tool_name in git_tools:
            return True

        # Periodic lightweight refresh
        if self._call_count % 20 == 0:
            return True

        return False

    @property
    def current(self) -> Optional[SessionContext]:
        return self._last_context

    def _get_git_info(self, path: str) -> Optional[dict]:
        """Get git repo information."""
        try:
            # Check if git repo
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return None

            info = {}

            # Branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            info["branch"] = result.stdout.strip() or "detached"

            # Status summary
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().splitlines()
            modified = sum(1 for l in lines if l.startswith(" M") or l.startswith("M"))
            untracked = sum(1 for l in lines if l.startswith("??"))
            staged = sum(1 for l in lines if l[0] in "AMDRC")

            parts = []
            if modified:
                parts.append(f"{modified} modified")
            if staged:
                parts.append(f"{staged} staged")
            if untracked:
                parts.append(f"{untracked} untracked")
            info["status"] = ", ".join(parts) if parts else "clean"

            # Recent commits
            result = subprocess.run(
                ["git", "-P", "log", "--oneline", "-n5"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            info["commits"] = [
                line.split(" ", 1)[1] if " " in line else line
                for line in result.stdout.strip().splitlines()[:5]
            ]

            return info

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"Git info gathering failed: {e}")
            return None

    def _get_gpu_name(self) -> str:
        """Detect GPU name."""
        # NVIDIA
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # macOS Metal
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True, timeout=5
                )
                if "Apple" in result.stdout:
                    return result.stdout.strip().split("\n")[0]
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        return "GPU detected"
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_context.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add rocky/context.py tests/test_context.py
git commit -m "feat: add dynamic context system with auto-refresh"
```

---

## Task 8: User Persona System (`rocky/persona.py`)

**Files:**
- Create: `rocky/persona.py`
- Create: `tests/test_persona.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_persona.py
"""Tests for user persona system."""
import pytest
import tempfile
from pathlib import Path
from rocky.persona import PersonaManager, PersonaTraits, PersonaMemory


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_persona.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement persona.py**

```python
# rocky/persona.py
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
from rocky.utils.validators import detect_sensitive_data

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
            "project_decisions": self.memory.project_decisions[-50:],  # cap at 50
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
        from pathlib import Path
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_persona.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add rocky/persona.py tests/test_persona.py
git commit -m "feat: add user persona system with passive learning"
```

---

## Task 9: Permission System Rewrite (`rocky/tools/base.py` + `rocky/ui/permissions.py`)

**Files:**
- Modify: `rocky/tools/base.py`
- Modify: `rocky/ui/permissions.py`
- Create: `tests/test_permissions.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_permissions.py
"""Tests for permission system."""
import pytest
from rocky.ui.permissions import PermissionManager, PermissionTier, PermissionDecision


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_permissions.py -v`
Expected: FAIL

- [ ] **Step 3: Rewrite permissions.py**

```python
# rocky/ui/permissions.py
"""Permission system for Rocky.Ai.

Tiered permissions with inline prompts and session-only state.
All permissions reset when session ends.
"""

import re
from enum import Enum
from typing import Optional
from rich.console import Console
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


class PermissionTier(Enum):
    AUTO_ALLOW = 0  # Pure reads — never prompt
    PROMPT = 1      # Writes/mutations — prompt until trusted
    ALWAYS_PROMPT = 2  # Media/external — always prompt


class PermissionDecision(Enum):
    ALLOW_ONCE = "allow_once"
    DENY = "deny"
    TRUST = "trust"
    TRUST_ALL = "trust_all"


# Tool → Tier mapping
TOOL_TIERS = {
    # Tier 0: Auto-allow
    "read_file": PermissionTier.AUTO_ALLOW,
    "list_directory": PermissionTier.AUTO_ALLOW,
    "search_files": PermissionTier.AUTO_ALLOW,
    "glob_files": PermissionTier.AUTO_ALLOW,
    "summarize_file": PermissionTier.AUTO_ALLOW,
    "git_status": PermissionTier.AUTO_ALLOW,
    "git_log": PermissionTier.AUTO_ALLOW,
    "git_diff": PermissionTier.AUTO_ALLOW,
    "web_search": PermissionTier.AUTO_ALLOW,
    "web_fetch": PermissionTier.AUTO_ALLOW,
    "search_knowledge": PermissionTier.AUTO_ALLOW,
    "task_plan": PermissionTier.AUTO_ALLOW,
    # Tier 1: Prompt
    "write_file": PermissionTier.PROMPT,
    "edit_file": PermissionTier.PROMPT,
    "index_files": PermissionTier.PROMPT,
    "git_commit": PermissionTier.PROMPT,
    "run_command": PermissionTier.PROMPT,
    # Tier 2: Always prompt
    "describe_image": PermissionTier.ALWAYS_PROMPT,
    "transcribe_audio": PermissionTier.ALWAYS_PROMPT,
    "process_video": PermissionTier.ALWAYS_PROMPT,
}

# Always blocked regardless of trust
BLOCKED_PATTERNS = [
    (r"rm\s+(-rf?|--recursive)\s+[/~]", "Recursive deletion of system directory"),
    (r"rm\s+-rf?\s+\*", "Recursive deletion with wildcard"),
    (r"mkfs\.", "Filesystem formatting"),
    (r"dd\s+if=.*of=/dev", "Direct disk write with dd"),
    (r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", "Fork bomb"),
    (r"chmod\s+-R\s+777\s+/", "Recursive chmod 777 on root"),
    (r"chown\s+-R.*\s+/", "Recursive chown on root"),
]

_blocked_compiled = [(re.compile(p, re.IGNORECASE), reason) for p, reason in BLOCKED_PATTERNS]


class PermissionManager:
    """Session-scoped permission manager.

    All state resets when session ends. No persistence.
    """

    def __init__(self):
        self._trusted_tools: set[str] = set()
        self._denied_tools: set[str] = set()
        self._trust_all: bool = False

    def get_tier(self, tool_name: str) -> PermissionTier:
        """Get the permission tier for a tool."""
        return TOOL_TIERS.get(tool_name, PermissionTier.PROMPT)

    def should_allow(self, tool_name: str, command: str = "") -> Optional[bool]:
        """Check if a tool should be allowed.

        Returns:
            True = auto-allow (tier 0 or trusted)
            False = denied or blocked
            None = needs user prompt
        """
        # Check blocked commands first
        if command and self.is_blocked_command(command):
            return False

        # Check denied
        if tool_name in self._denied_tools:
            return False

        # Check trust-all
        if self._trust_all:
            return True

        # Check per-tool trust
        if tool_name in self._trusted_tools:
            return True

        # Check tier
        tier = self.get_tier(tool_name)
        if tier == PermissionTier.AUTO_ALLOW:
            return True

        # Needs prompt
        return None

    def trust_tool(self, tool_name: str):
        """Trust a tool for this session."""
        self._trusted_tools.add(tool_name)
        self._denied_tools.discard(tool_name)

    def deny_tool(self, tool_name: str):
        """Deny a tool for this session."""
        self._denied_tools.add(tool_name)
        self._trusted_tools.discard(tool_name)

    def trust_all(self):
        """Trust all tools for this session."""
        self._trust_all = True
        self._denied_tools.clear()

    def reset(self):
        """Reset all permissions to defaults."""
        self._trusted_tools.clear()
        self._denied_tools.clear()
        self._trust_all = False

    def is_blocked_command(self, command: str) -> bool:
        """Check if command matches always-blocked patterns."""
        for pattern, _ in _blocked_compiled:
            if pattern.search(command):
                return True
        return False

    def get_block_reason(self, command: str) -> Optional[str]:
        """Get reason a command is blocked."""
        for pattern, reason in _blocked_compiled:
            if pattern.search(command):
                return reason
        return None

    def get_status(self) -> dict:
        """Get current permission state for display."""
        return {
            "trust_all": self._trust_all,
            "trusted_tools": sorted(self._trusted_tools),
            "denied_tools": sorted(self._denied_tools),
        }

    def prompt_user(self, console: Console, tool_name: str, detail: str = "") -> PermissionDecision:
        """Show inline permission prompt and get user decision.

        Uses single-letter fast path: A, D, T, X
        Also supports arrow-key menu via ArrowMenu.
        """
        from rocky.ui.menu import ArrowMenu

        console.print()
        console.print(f"  [bold]⚙  {tool_name}:[/bold] {detail}")
        console.print()

        menu = ArrowMenu(
            title="",
            options=[
                "Allow-Once",
                "Deny",
                f"Trust '{tool_name}'",
                "Trust-All ⚠",
            ],
            default=0,
            console=console,
        )

        # Try fast-path single letter first
        # (ArrowMenu.run() handles the actual interaction)
        choice = menu.run()

        if choice == "Allow-Once":
            return PermissionDecision.ALLOW_ONCE
        elif choice == "Deny":
            return PermissionDecision.DENY
        elif choice.startswith("Trust '"):
            self.trust_tool(tool_name)
            return PermissionDecision.TRUST
        else:
            # Trust-All — confirm first
            confirm_menu = ArrowMenu(
                title="⚠  This allows Rocky to run ALL tools without asking. Sure?",
                options=["Yes", "No"],
                default=1,  # default No for safety
                console=console,
            )
            if confirm_menu.run() == "Yes":
                self.trust_all()
                return PermissionDecision.TRUST_ALL
            else:
                return PermissionDecision.DENY


# Global instance
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get or create global permission manager."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_permissions.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add rocky/ui/permissions.py tests/test_permissions.py
git commit -m "feat(permissions): tiered system with A/D/T/X and arrow-key menu"
```

---

## Task 10: System Prompt Rewrite (`rocky/llm/prompts.py`)

**Files:**
- Modify: `rocky/llm/prompts.py`

- [ ] **Step 1: Replace entire prompts.py with the full system prompt**

The complete content is defined in the design spec Section 6. Write the full ~350 line prompt covering:
- Block 1: Identity & Boundaries (core principles, banned topics, response style, formatting rules)
- Block 2: Tool Catalog & Rules (every tool listed, selection rules)
- Block 3: Agentic Behavior (multi-step reasoning, when to stop, mid-task instructions, error handling)
- Block 4 template: `CONTEXT_TEMPLATE` (filled at runtime by context.py)
- Block 5 template: `PERSONA_TEMPLATE` (filled at runtime by persona.py)

Keep the `TOOL_RESULT_PROMPT` string.

Add a function:
```python
def build_system_prompt(context_block: str = "", persona_block: str = "") -> str:
    """Build the full system prompt with dynamic context and persona."""
    prompt = SYSTEM_PROMPT
    if context_block:
        prompt += "\n\n" + context_block
    if persona_block:
        prompt += "\n\n" + persona_block
    return prompt
```

- [ ] **Step 2: Verify it loads**

Run: `python -c "from rocky.llm.prompts import SYSTEM_PROMPT, build_system_prompt; print(f'{len(SYSTEM_PROMPT)} chars, {len(SYSTEM_PROMPT.splitlines())} lines')"`
Expected: ~300+ lines

- [ ] **Step 3: Commit**

```bash
git add rocky/llm/prompts.py
git commit -m "feat(prompts): comprehensive 350-line system prompt with tool catalog and guardrails"
```

---

## Task 11: Enhanced Tools — edit_file, glob_files, summarize_file

**Files:**
- Modify: `rocky/tools/files.py`
- Create: `tests/test_tools_enhanced.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_tools_enhanced.py
"""Tests for enhanced file tools."""
import os
import pytest
import tempfile
from pathlib import Path
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
        assert result.data["count"] > 5  # rocky has many .py files

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
        assert "Tool" in result.output  # should find the Tool class
        assert "ToolRegistry" in result.output

    def test_summarize_nonexistent(self):
        tool = SummarizeFileTool()
        result = tool.execute(path="/nonexistent.py")
        assert not result.success
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools_enhanced.py -v`
Expected: FAIL

- [ ] **Step 3: Add replace_all to EditFileTool**

In `rocky/tools/files.py`, modify `EditFileTool.__init__` to add parameter:

```python
ToolParameter(
    name="replace_all",
    type="boolean",
    description="Replace all occurrences of old_str (default: false, fails if multiple matches)",
    required=False,
    default=False
),
```

Modify `EditFileTool.execute` signature and logic:

```python
def execute(self, path: str, old_str: str, new_str: str, replace_all: bool = False) -> ToolResult:
    try:
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            return ToolResult.fail(f"File not found: {path}")

        content = file_path.read_text(encoding="utf-8")
        old_content = content

        if old_str not in content:
            return ToolResult.fail(f"String not found in file: {old_str[:50]}...")

        count = content.count(old_str)

        if not replace_all and count > 1:
            return ToolResult.fail(
                f"String found {count} times. Use replace_all=true or provide more context."
            )

        if replace_all:
            new_content = content.replace(old_str, new_str)
        else:
            new_content = content.replace(old_str, new_str, 1)

        file_path.write_text(new_content, encoding="utf-8")

        return ToolResult.ok(
            f"Edited file: {path} ({count} replacement{'s' if count > 1 else ''})",
            data={"path": str(file_path), "old_content": old_content, "new_content": new_content}
        )
    except PermissionError:
        return ToolResult.fail(f"Permission denied: {path}")
    except Exception as e:
        return ToolResult.fail(f"Error editing file: {e}")
```

- [ ] **Step 4: Add GlobFilesTool class**

Append to `rocky/tools/files.py`:

```python
class GlobFilesTool(Tool):
    """Find files matching a glob pattern."""

    def __init__(self):
        super().__init__(
            name="glob_files",
            description="Find files matching a glob pattern (e.g., '**/*.py', 'src/*.ts')",
            parameters=[
                ToolParameter(name="pattern", type="string",
                             description="Glob pattern to match", required=True),
                ToolParameter(name="path", type="string",
                             description="Directory to search in", required=False, default="."),
            ]
        )

    def execute(self, pattern: str, path: str = ".") -> ToolResult:
        try:
            dir_path = Path(path).expanduser().resolve()
            if not dir_path.exists():
                return ToolResult.fail(f"Directory not found: {path}")

            matches = sorted(dir_path.glob(pattern))
            # Filter to files only
            files = [str(m.relative_to(dir_path)) for m in matches if m.is_file()]

            output = "\n".join(files[:200])
            if len(files) > 200:
                output += f"\n... and {len(files) - 200} more"

            if not files:
                output = "No files matched."

            return ToolResult.ok(output, data={"count": len(files), "path": str(dir_path)})
        except Exception as e:
            return ToolResult.fail(f"Glob error: {e}")
```

- [ ] **Step 5: Add SummarizeFileTool class**

Append to `rocky/tools/files.py`:

```python
class SummarizeFileTool(Tool):
    """Get structural summary of a file without reading full content."""

    def __init__(self):
        super().__init__(
            name="summarize_file",
            description="Get a structural summary (classes, functions, imports) without full content",
            parameters=[
                ToolParameter(name="path", type="string",
                             description="Path to the file", required=True),
            ]
        )

    def execute(self, path: str) -> ToolResult:
        try:
            file_path = Path(path).expanduser().resolve()

            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")

            if is_binary_file(file_path):
                return ToolResult.fail(f"Cannot summarize binary file: {path}")

            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)

            imports = []
            classes = []
            functions = []
            current_class = None

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # Imports
                if stripped.startswith(("import ", "from ")):
                    mod = stripped.split()[1] if len(stripped.split()) > 1 else ""
                    if mod and mod not in imports:
                        imports.append(mod)

                # Classes
                elif stripped.startswith("class "):
                    match = re.match(r"class\s+(\w+)", stripped)
                    if match:
                        current_class = {"name": match.group(1), "line": i, "methods": []}
                        classes.append(current_class)

                # Functions/methods
                elif stripped.startswith("def "):
                    match = re.match(r"def\s+(\w+)", stripped)
                    if match:
                        func_name = match.group(1)
                        if current_class and line.startswith("    "):
                            current_class["methods"].append(func_name)
                        else:
                            functions.append({"name": func_name, "line": i})
                            current_class = None

                # Reset class context on non-indented non-empty lines
                elif stripped and not line.startswith((" ", "\t")) and not stripped.startswith(("#", "@")):
                    current_class = None

            # Build output
            parts = [f"{file_path.name} ({total_lines} lines)"]

            if imports:
                parts.append(f"  Imports: {', '.join(imports[:15])}")

            if classes:
                parts.append("  Classes:")
                for cls in classes:
                    methods = ", ".join(cls["methods"][:8])
                    suffix = f": {methods}" if methods else ""
                    parts.append(f"    - {cls['name']} (line {cls['line']}){suffix}")

            if functions:
                parts.append("  Functions:")
                for fn in functions[:15]:
                    parts.append(f"    - {fn['name']} (line {fn['line']})")

            return ToolResult.ok("\n".join(parts), data={"path": str(file_path), "lines": total_lines})
        except Exception as e:
            return ToolResult.fail(f"Error summarizing file: {e}")
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_tools_enhanced.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add rocky/tools/files.py tests/test_tools_enhanced.py
git commit -m "feat(tools): add replace_all, glob_files, summarize_file"
```

---

## Task 12: Enhanced Shell — Background Execution (`rocky/tools/shell.py`)

**Files:**
- Modify: `rocky/tools/shell.py`

- [ ] **Step 1: Add background execution support**

Add `run_in_background` parameter to `RunCommandTool.__init__`:

```python
ToolParameter(
    name="run_in_background",
    type="boolean",
    description="Run command in background, returns job ID immediately",
    required=False,
    default=False
),
```

Add a `BackgroundJobManager` class and modify `execute()` to support background mode. When `run_in_background=True`, start the command in a thread and return a job ID immediately.

```python
import threading
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BackgroundJob:
    id: int
    command: str
    started: datetime = field(default_factory=datetime.now)
    completed: bool = False
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None


class BackgroundJobManager:
    """Manages background shell jobs."""

    def __init__(self):
        self._jobs: dict[int, BackgroundJob] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def start_job(self, command: str, working_dir: Optional[str] = None, timeout: int = 300) -> int:
        job_id = self._next_id
        self._next_id += 1

        job = BackgroundJob(id=job_id, command=command)
        self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_job, args=(job, command, working_dir, timeout), daemon=True
        )
        thread.start()
        return job_id

    def _run_job(self, job: BackgroundJob, command: str, working_dir: Optional[str], timeout: int):
        try:
            shell_cmd = get_shell_command(command)
            result = subprocess.run(
                shell_cmd, capture_output=True, text=True,
                timeout=timeout, cwd=working_dir
            )
            with self._lock:
                job.output = result.stdout
                job.error = result.stderr
                job.exit_code = result.returncode
                job.completed = True
        except subprocess.TimeoutExpired:
            with self._lock:
                job.error = f"Timed out after {timeout}s"
                job.completed = True
                job.exit_code = -1
        except Exception as e:
            with self._lock:
                job.error = str(e)
                job.completed = True
                job.exit_code = -1

    def get_job(self, job_id: int) -> Optional[BackgroundJob]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[BackgroundJob]:
        return list(self._jobs.values())


# Global job manager
_job_manager: Optional[BackgroundJobManager] = None

def get_job_manager() -> BackgroundJobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = BackgroundJobManager()
    return _job_manager
```

- [ ] **Step 2: Verify**

Run: `python -c "from rocky.tools.shell import RunCommandTool, get_job_manager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add rocky/tools/shell.py
git commit -m "feat(shell): add background command execution with job manager"
```

---

## Task 13: New Tool — Task Plan (`rocky/tools/task_plan.py`)

**Files:**
- Create: `rocky/tools/task_plan.py`
- Create: `tests/test_task_plan.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_task_plan.py
"""Tests for task plan tool."""
import pytest
from rocky.tools.task_plan import TaskPlanTool


class TestTaskPlan:
    def setup_method(self):
        self.tool = TaskPlanTool()
        # Clear any existing plan
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
```

- [ ] **Step 2: Implement task_plan.py**

```python
# rocky/tools/task_plan.py
"""Task plan tool for Rocky.Ai.

Allows Rocky to create and track a checklist for multi-step work.
Session-scoped — plan resets when session ends.
"""

from dataclasses import dataclass, field
from typing import Optional
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
                ToolParameter(name="action", type="string",
                             description="Action: 'create', 'update', or 'list'",
                             required=True),
                ToolParameter(name="subject", type="string",
                             description="Task subject/title",
                             required=False, default=""),
                ToolParameter(name="status", type="string",
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
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_task_plan.py -v`
Expected: All 4 PASS

- [ ] **Step 4: Commit**

```bash
git add rocky/tools/task_plan.py tests/test_task_plan.py
git commit -m "feat(tools): add task_plan tool for multi-step progress tracking"
```

---

## Task 14: Register New Tools (`rocky/tools/__init__.py`)

**Files:**
- Modify: `rocky/tools/__init__.py`

- [ ] **Step 1: Add new tool imports and exports**

```python
from rocky.tools.files import (
    ReadFileTool, WriteFileTool, EditFileTool,
    ListDirectoryTool, SearchFilesTool,
    GlobFilesTool, SummarizeFileTool,
)
from rocky.tools.task_plan import TaskPlanTool

__all__ = [
    # ... existing ...
    "GlobFilesTool",
    "SummarizeFileTool",
    "TaskPlanTool",
]
```

- [ ] **Step 2: Verify imports**

Run: `python -c "from rocky.tools import GlobFilesTool, SummarizeFileTool, TaskPlanTool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add rocky/tools/__init__.py
git commit -m "chore(tools): register new tools in __init__"
```

---

## Task 15: Session Memory — Mid-Task Instruction Support

**Files:**
- Modify: `rocky/session/memory.py`

- [ ] **Step 1: Add method for mid-task messages**

Add to `ConversationMemory`:

```python
def add_mid_task_instruction(self, instruction: str):
    """Add a /btw mid-task instruction from the user."""
    self.turns.append(ConversationTurn(
        role="user",
        content=f"[Mid-task instruction]: {instruction}"
    ))
    self._trim_if_needed()
```

- [ ] **Step 2: Verify**

Run: `python -c "
from rocky.session.memory import ConversationMemory
m = ConversationMemory()
m.add_mid_task_instruction('add rate limiting')
msgs = m.get_messages()
assert '[Mid-task instruction]' in msgs[-1].content
print('OK')
"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add rocky/session/memory.py
git commit -m "feat(session): add mid-task instruction support for /btw"
```

---

## Task 16: Agentic Loop Rewrite (`rocky/agent.py`)

**Files:**
- Modify: `rocky/agent.py`

- [ ] **Step 1: Rewrite agent.py with full agentic loop**

This is the largest single change. Replace `process_message()` with the agentic loop from the spec. Key changes:

1. Import `ContextGatherer`, `PersonaManager`, `build_system_prompt`, `get_permission_manager`, `PermissionDecision`, `StreamRenderer`, `TaskPlanTool`, `GlobFilesTool`, `SummarizeFileTool`
2. Add `self.context` and `self.persona` to `__init__`
3. Register new tools (`GlobFilesTool`, `SummarizeFileTool`, `TaskPlanTool`)
4. Replace `process_message()` with agentic loop (100 iterations, loop detection, error chains)
5. Add `_execute_tool_with_permissions()` that checks the permission manager
6. Add `/btw` queue checking between iterations
7. Add `_progress_summary()` method
8. Use `StreamRenderer` for formatted output
9. Build system prompt dynamically with context + persona

The full implementation follows the pseudocode in the spec (Section 2) and the data flow (Section 13).

- [ ] **Step 2: Verify basic import**

Run: `python -c "from rocky.agent import Agent; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add rocky/agent.py
git commit -m "feat(agent): agentic loop with multi-step reasoning, permissions, and context"
```

---

## Task 17: Agent Runner — Threading (`rocky/agent_runner.py`)

**Files:**
- Create: `rocky/agent_runner.py`

- [ ] **Step 1: Implement AgentRunner**

```python
# rocky/agent_runner.py
"""Threading wrapper for Rocky.Ai agent.

Runs the agent loop in a worker thread while the main thread
handles user input (/btw, Ctrl+C).
"""

import threading
from queue import Queue
from typing import Optional
from rich.console import Console
from rocky.agent import Agent


class AgentRunner:
    """Manages agent execution in a separate thread."""

    def __init__(self, agent: Agent, console: Console):
        self.agent = agent
        self.console = console
        self.btw_queue: Queue = Queue()
        self.stop_event = threading.Event()
        self.is_working = False
        self._thread: Optional[threading.Thread] = None

    def inject_btw(self, message: str):
        """Inject a /btw mid-task instruction."""
        self.btw_queue.put(message)

    def request_stop(self):
        """Request the agent loop to stop."""
        self.stop_event.set()

    def start(self, user_input: str):
        """Start processing a user message in the worker thread."""
        self.is_working = True
        self.stop_event.clear()

        # Clear any leftover /btw messages
        while not self.btw_queue.empty():
            self.btw_queue.get()

        self._thread = threading.Thread(
            target=self._worker, args=(user_input,), daemon=True
        )
        self._thread.start()

    def wait(self):
        """Wait for the agent to finish."""
        if self._thread:
            self._thread.join()

    def _worker(self, user_input: str):
        """Worker thread — runs the agent loop."""
        try:
            for chunk in self.agent.process_message(user_input):
                if self.stop_event.is_set():
                    break
                # Output handled by agent internally via console
        finally:
            self.is_working = False
```

- [ ] **Step 2: Verify**

Run: `python -c "from rocky.agent_runner import AgentRunner; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add rocky/agent_runner.py
git commit -m "feat: add AgentRunner threading wrapper for /btw and Ctrl+C"
```

---

## Task 18: CLI Integration — New Commands, Ctrl+C, /btw

**Files:**
- Modify: `rocky/cli.py`

- [ ] **Step 1: Rewrite CLI with new features**

Major changes to `rocky/cli.py`:
1. Import `AgentRunner`, `ArrowMenu`, `get_permission_manager`, `get_job_manager`
2. Replace `/trust` with `/tools` command and subcommands
3. Add `/btw` handling during agent loop
4. Add `/refresh` command (triggers persona save + memory checkpoint)
5. Add `/jobs` command (shows background job status)
6. Merge `/model` and `/models` into single `/model [name]` command
7. Remove `/exit` (keep only `/quit`)
8. Replace Ctrl+C handler with two-state behavior:
   - During agent work: calls `runner.request_stop()`
   - When idle: shows arrow-key quit menu (Yes/No/Refresh and quit)
9. Update `/help` output

- [ ] **Step 2: Test manually**

Run: `Rocky` and verify:
- `/help` shows new commands
- `/tools` shows permission state
- `/model` shows current + lists all
- Ctrl+C when idle shows quit menu with blue ▶
- Basic chat still works

- [ ] **Step 3: Commit**

```bash
git add rocky/cli.py
git commit -m "feat(cli): /tools, /btw, /refresh, /jobs, Ctrl+C quit menu"
```

---

## Task 19: Download Progress Bar with Shimmer

**Files:**
- Modify: `rocky/llm/downloader.py`

- [ ] **Step 1: Update download progress bar styling**

In the `ModelDownloader.download()` method, replace the Rich Progress bar configuration with:

```python
from rich.progress import (
    Progress, SpinnerColumn, TextColumn,
    BarColumn, TaskProgressColumn, DownloadColumn,
)

progress = Progress(
    SpinnerColumn("dots", style="cyan"),
    TextColumn("[bold]{task.description}"),
    BarColumn(bar_width=40, style="dim", complete_style="cyan", finished_style="green"),
    TaskProgressColumn(),
    DownloadColumn(),
    console=self.console,
)
```

The `complete_style="cyan"` makes the filled portion cyan. The `style="dim"` makes the unfilled track dim. The spinner column uses braille dots.

For the animated shimmer on the unfilled portion, use a custom `BarColumn` subclass or Rich's `pulse_style` parameter:

```python
BarColumn(bar_width=40, style="dim", complete_style="cyan", pulse_style="bright_cyan"),
```

The `pulse_style` creates the traveling shimmer effect on the bar when indeterminate, but for determinate progress, use Rich's built-in animation.

- [ ] **Step 2: Test by switching model**

Run: `python -c "from rocky.llm.downloader import ModelDownloader; d = ModelDownloader(); print(d.get_recommended_model())"`
Expected: prints model name without error

- [ ] **Step 3: Commit**

```bash
git add rocky/llm/downloader.py
git commit -m "feat(ui): cyan progress bar with shimmer for model downloads"
```

---

## Task 20: Final Integration — Update /help, Test Full Flow, Update Website

**Files:**
- Modify: `docs/index.html`
- Modify: `README.md`

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v 2>&1 | tail -30`
Expected: All tests PASS

- [ ] **Step 2: Manual integration test**

Run Rocky and test:
1. Start session → context shown at startup
2. Ask a question → formatted markdown response with Rich Live
3. Ask to create a file → permission prompt with arrow-key menu
4. Ask multi-step task → agentic loop with task plan
5. Type `/btw` during work → instruction acknowledged
6. `/refresh` → memory checkpoint saved
7. `/tools` → shows permission state
8. `/model` → shows current + list
9. Ctrl+C when idle → quit menu with blue ▶

- [ ] **Step 3: Update website and README with V2 features**

Add sections for:
- Agentic multi-step reasoning
- User persona learning
- Permission system
- /btw mid-task steering
- New tools (glob, summarize, task plan)

- [ ] **Step 4: Commit**

```bash
git add docs/index.html README.md
git commit -m "docs: update website and README with V2 features"
```

- [ ] **Step 5: Final commit with all remaining changes**

```bash
git add -A
git status
git commit -m "feat: Rocky.Ai V2 — agentic loop, persona, permissions, context awareness"
```

---

## Dependency Order

```
Task 1  (test infra)
   ↓
Tasks 2-5 (foundation — parallel)
   ↓
Task 6  (config)
   ↓
Tasks 7-8 (context + persona — parallel)
   ↓
Task 9  (permissions)
   ↓
Task 10 (system prompt)
   ↓
Tasks 11-13 (tools — parallel)
   ↓
Task 14 (register tools)
   ↓
Task 15 (session memory)
   ↓
Task 16 (agent loop)
   ↓
Task 17 (agent runner)
   ↓
Task 18 (CLI)
   ↓
Tasks 19-20 (polish — parallel)
```
