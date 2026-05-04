# Rocky.Ai V2 — Tool System Overhaul Design Spec

**Date:** 2026-05-04
**Author:** Roshan + Claude
**Status:** Approved
**Approach:** Layered Enhancement (evolve each component independently)

---

## 1. Overview

Rebuild Rocky's tool calling architecture modeled after Claude Code's agent system, adapted for local compute. This transforms Rocky from a single-tool-call assistant into a fully agentic AI that can plan, execute multi-step tasks, learn user preferences, and be steered mid-task.

### Goals
- Agentic reasoning loop (multi-step tool chaining)
- Comprehensive system prompt that eliminates hallucinated tool names
- Dynamic environment context awareness (auto-refreshing)
- User persona system that learns across sessions
- Granular permission system with inline prompts
- Mid-task instruction injection (/btw)
- Rich formatted output with streaming markdown
- Polished minimalistic animations throughout

### Not in Scope
- MCP servers (Amazon-specific)
- PyPI publishing
- Multi-model family support (Llama, Mistral, etc.)
- Sub-agents / parallel workers
- Jupyter notebook editing
- Scheduling / cron

---

## 2. Agentic Loop

**File:** `rocky/agent.py` (refactor `process_message()`)

### Current Behavior
```
User message → LLM → 1 tool call → 1 followup → done
```

### New Behavior
```
User message → LLM → tool call(s) → feed results back → LLM decides:
                                                          ├─ call more tools → loop
                                                          └─ text response → done
```

### Termination Strategy

The loop exits via smart detection, not arbitrary caps:

| Condition | Action |
|-----------|--------|
| Model produces text with no tool calls | Normal exit — done |
| Same tool + same args called 3 times | Loop detected → stop, warn user |
| 5 consecutive tool failures | Error chain → pause, explain to user |
| 100 iterations reached | Catastrophic safety ceiling → stop |
| Ctrl+C received | Clean abort with progress summary |
| User types /btw | Inject instruction, continue loop |

### On Forced Stop

Rocky outputs a progress summary:
```
  ⚠  Stopped after {N} steps.
     Completed: {list of what was done}
     In progress: {current task, may be partial}
     Remaining: {what was likely planned}

     Say "continue" to resume.
```

"continue" works because full conversation history persists in memory. Rocky picks up where it left off.

### Pseudocode

```python
def process_message(self, user_input: str) -> Generator[str, None, None]:
    self.memory.add_user_message(user_input)

    iteration = 0
    max_iterations = 100
    recent_calls = []
    consecutive_errors = 0

    while iteration < max_iterations:
        iteration += 1

        # Check Ctrl+C stop flag
        if self.runner.stop_event.is_set():
            yield self._progress_summary()
            break

        # Check /btw queue
        while not self.runner.btw_queue.empty():
            btw_msg = self.runner.btw_queue.get()
            self.memory.add_user_message(f"[Mid-task instruction]: {btw_msg}")
            # Show acknowledgment with spinner
            yield "\n  ⠧  Noted — adjusting...\n"

        # Get LLM response
        messages = self.memory.get_messages()
        response_text, tool_calls = yield from self._stream_response(messages)

        # No tool calls → model is done
        if not tool_calls:
            self.memory.add_assistant_message(response_text)
            break

        # Loop detection
        for tc in tool_calls:
            call_sig = f"{tc.name}:{sorted(tc.arguments.items())}"
            recent_calls.append(call_sig)
            if recent_calls.count(call_sig) >= 3:
                yield "\n  ⚠  Loop detected — stopping.\n"
                yield self._progress_summary()
                return

        # Execute tools
        for tc in tool_calls:
            result = self._execute_tool_with_permissions(tc.name, tc.arguments)
            self._show_tool_result(tc.name, tc.arguments, result)
            self.memory.add_tool_result(tc.name, result.output or result.error or "")

            if not result.success:
                consecutive_errors += 1
            else:
                consecutive_errors = 0

            if consecutive_errors >= 5:
                yield "\n  ⚠  Multiple failures — pausing.\n"
                yield self._progress_summary()
                return

        self.memory.add_assistant_message(response_text, tool_calls=[...])

    if iteration >= max_iterations:
        yield "\n  ⚠  Reached maximum steps.\n"
        yield self._progress_summary()
```

---

## 3. Dynamic Context System

**File:** `rocky/context.py` (NEW)

Auto-refreshing environment awareness. Rocky always knows where it is.

### SessionContext Data

```python
@dataclass
class SessionContext:
    working_dir: str              # /home/user/myproject
    is_git_repo: bool
    git_branch: str               # "main"
    git_status_summary: str       # "3 modified, 1 untracked"
    git_recent_commits: list[str] # last 5 one-line commits
    os_name: str                  # "Linux" / "macOS" / "Windows"
    shell: str                    # "/bin/zsh"
    python_version: str           # "3.12.3"
    ram_gb: int                   # 16
    has_gpu: bool
    gpu_name: str                 # "NVIDIA RTX 4090" or "Apple M2"
    internet_available: bool
    current_model: str            # "qwen2.5-3b"
    user_persona_summary: str     # from persona system
```

### Auto-Refresh Triggers

| Trigger | What refreshes |
|---------|---------------|
| Session start | Everything |
| After `run_command` with cd | working_dir, git state |
| After git tool calls | git state only |
| After file writes | git status only |
| Every 20 tool calls | Lightweight git status |
| `/refresh` | NOT context — this is for memory (see Section 4) |

### Injection into System Prompt

Appended as a dynamic block:
```
## Current Environment
- Working directory: /home/user/myproject
- Git: main branch, 3 modified files, 1 untracked
- Recent commits: feat: add auth, fix: login bug, ...
- System: Linux, zsh, Python 3.12, 16GB RAM, NVIDIA RTX 4090
- Model: qwen2.5-3b (2.2GB, Q5_K_M)
- Internet: available
```

---

## 4. User Persona System

**File:** `rocky/persona.py` (NEW)
**Storage:** `~/.rocky/persona/`

Rocky learns who it's talking to — not by asking, but by observing.

### Storage Files

```
~/.rocky/persona/
├── persona.yaml     # Traits, preferences, personality
├── memory.yaml      # Project decisions, corrections, facts
└── vault.enc        # Encrypted sensitive data (optional)
```

### persona.yaml Structure

```yaml
traits:
  experience_level: senior
  primary_language: python
  tone_preference: concise
  detail_level: low
  coding_style:
    type_hints: true
    docstrings: minimal
    naming: snake_case

preferences:
  framework: flask
  test_style: pytest
  editor: vscode
  git_style: conventional_commits

personality:
  patience: high
  exploration: likes_options
  humor: occasional
```

### memory.yaml Structure

```yaml
project_decisions:
  - "Auth module uses JWT, lives in src/auth/"
  - "Database is PostgreSQL, not SQLite"

learned_facts:
  - "User's project deadline is June 15"

corrections:
  - "Don't suggest print() for debugging — user prefers logging"
  - "Don't restructure files without asking"
```

### Learning Modes

**Passive (every conversation, no cost):**
Rule-based heuristics after each exchange:
- User says "just do it" / "skip the explanation" → `detail_level: low`
- User writes Python with type hints → `type_hints: true`
- User corrects Rocky → stored as correction
- Directory has `.vscode/` → `editor: vscode`
- Git log uses conventional commits → `git_style: conventional_commits`

**Active (on `/refresh` or session close):**
LLM analyzes recent conversation turns, extracts deeper persona signals — tone shifts, preference patterns, project decisions that heuristics miss.

### /refresh Command

`/refresh` = memory checkpoint. Saves conversation learnings + persona updates.

```
  /refresh

  ✔  Memory checkpoint saved
     ◦  Persona: updated tone preference (concise, direct)
     ◦  Project: noted Flask API with JWT auth
     ◦  Context: 3 new files tracked
```

Rocky also auto-saves at natural breakpoints (end of multi-step task, before session close).

Periodic tip shown once per session:
```
  Tip: Use /refresh to save what I've learned from our conversation.
```

### Sensitive Data Handling

Regex patterns detect:
- Email addresses, phone numbers, SSNs
- API keys, AWS credentials, passwords
- Credit card numbers, private keys

When detected:
```
  ⚠  I noticed what looks like an API key in our conversation.

     ▶ Save encrypted (AES-256, local only)
       Skip — don't remember this
```

Arrow-key selection (blue ▶), not letter input.

If user saves:
- Encrypted with Fernet (AES-128-CBC via `cryptography` library)
- Key derived from machine-local secret (`~/.rocky/persona/.key`)
- Stored in `~/.rocky/persona/vault.enc`
- Decrypted into memory at session start only

**NEVER stored, even encrypted:**
- Religious views, political opinions, sexual orientation
- Health/medical information, financial details
- Anything the user says "forget this"

### Persona in System Prompt

Compressed 3-5 line summary:
```
## About This User
Senior Python developer. Prefers concise responses with code,
minimal explanation. Uses type hints, pytest, Flask. Conventional
commits. Has corrected me about: don't use print() for debugging,
don't restructure files without asking.
```

---

## 5. Permission System

**Files:** `rocky/ui/permissions.py` (rewrite), `rocky/tools/base.py` (enhance)

### Tool Permission Tiers

```python
PERMISSION_TIERS = {
    # Tier 0: Always allowed — pure reads, no side effects
    "read_file": 0,
    "list_directory": 0,
    "search_files": 0,
    "glob_files": 0,
    "summarize_file": 0,
    "git_status": 0,
    "git_log": 0,
    "git_diff": 0,
    "web_search": 0,
    "web_fetch": 0,
    "search_knowledge": 0,
    "task_plan": 0,

    # Tier 1: Prompt — writes and mutations
    "write_file": 1,
    "edit_file": 1,
    "index_files": 1,
    "git_commit": 1,
    "run_command": 1,

    # Tier 2: Always prompt — media/external
    "describe_image": 2,
    "transcribe_audio": 2,
    "process_video": 2,
}
```

Tier 0 never prompts. Tier 1+ prompts until trusted.

### Inline Prompt (during tool execution)

```
  ⚙  run_command: npm install express

     ▶ Allow-Once
       Deny
       Trust 'run_command'
       Trust-All ⚠

```

Arrow-key selection with blue ▶. Single-letter fast path also works: A, D, T, X.

- **Allow-Once (A)** — Run this time, ask again next time
- **Deny (D)** — Don't run. Rocky adapts.
- **Trust (T)** — Trust this tool for the session. Won't ask again for this tool.
- **Trust-All (X)** — Trust everything. Shows caution first:

```
  ⚠  This allows Rocky to run ALL tools including shell commands
     without asking. Are you sure?

     ▶ Yes
       No
```

### Always Blocked (regardless of trust)

```python
ALWAYS_BLOCKED = [
    r"rm\s+(-rf?|--recursive)\s+[/~]",
    r"mkfs\.",
    r"dd\s+if=.*of=/dev",
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;:",
    r"chmod\s+-R\s+777\s+/",
]
```

```
  ✘  Blocked: Recursive deletion of root directory
     This command is blocked for safety regardless of trust level.
```

### Slash Commands

```
/tools                    Show current permission state for all tools
/tools trust <tool>       Trust a specific tool for the session
/tools trust-all          Trust all tools (with caution warning)
/tools deny <tool>        Block a specific tool for the session
/tools reset              Reset all permissions to defaults
```

### Session-Only

ALL permissions reset when the session ends. Every new session starts fresh with default tiers. Zero carry-over. This is intentional safety.

---

## 6. System Prompt

**File:** `rocky/llm/prompts.py` (complete rewrite, ~300-400 lines)

### Structure

```
Block 1: Identity & Boundaries        (~50 lines)
Block 2: Tool Catalog & Rules         (~150 lines)
Block 3: Agentic Behavior Rules       (~80 lines)
Block 4: Environment Context           (~15 lines, dynamic)
Block 5: User Persona                  (~5 lines, dynamic)
```

### Block 1: Identity & Boundaries

```
You are Rocky.Ai, a local AI assistant running entirely on the user's machine.
You are private, offline-capable, and designed for engineers and professionals.

## Core Principles
- You are helpful, direct, and professional
- You respect user privacy — everything stays local
- You never send data anywhere without explicit user consent
- You prefer action over explanation unless asked to explain

## Topics You Do Not Engage With
You are designed for professional and technical use. You do NOT discuss:
- Religion or religious beliefs
- Politics, political parties, elections, or political figures
- Sexual content or relationships
- Violence, weapons, or harmful activities
- Hate speech, discrimination, or stereotypes
- Illegal activities or how to circumvent laws
- Medical diagnoses or legal advice

If asked, respond:
"I'm designed for technical and professional tasks. I can't help with that topic,
but I'm happy to help with coding, engineering, research, or other professional work."

## Response Style
- Be direct and concise — lead with the answer, not the reasoning
- Use markdown for formatting, fenced code blocks with language tags
- Don't over-explain obvious things
- Match the user's energy — if they're brief, be brief
- Never use emojis unless the user does first

## Response Formatting
Format responses for maximum readability:
- Code → fenced blocks with language tag (```python, ```bash, etc.)
- Comparisons → tables (| Column | Column |)
- Steps/procedures → numbered lists (1. 2. 3.)
- Options/features → bullet lists (- item)
- Key terms → bold (**term**)
- File paths, commands, variables → inline code (`path`)
- Warnings → bold prefix (**Note:** or **Warning:**)
- Long explanations → headers (## Section) to break them up
- Never dump raw unformatted text
- Keep tables under 5 columns
- Code blocks must always have a language tag
- Match format complexity to answer complexity
```

### Block 2: Tool Catalog & Rules

```
## Available Tools

You have access to EXACTLY these tools. You may ONLY call tools from this list.
If no tool fits, respond with text. NEVER invent tool names.

### File Operations
| Tool | Purpose | When to Use |
|------|---------|-------------|
| read_file | Read file contents | Read/show/open a file; understand code before editing |
| write_file | Create or overwrite file | Create new file; save generated code |
| edit_file | Find-and-replace in file | Change/fix/update existing code |
| list_directory | List directory contents | Explore project structure |
| search_files | Regex search in files | Find where something is defined |
| glob_files | Find files by pattern | Find files by name (e.g., **/*.py) |
| summarize_file | Structural file overview | Understand large file without reading all of it |

### Shell
| run_command | Execute shell command | Install packages, run tests, builds |

### Web
| web_search | Search the internet | Need current info or can't answer locally |
| web_fetch | Fetch a webpage | Need docs from a specific URL |

### Git
| git_status | Show repo status | Before committing; check changes |
| git_diff | Show file changes | See what changed |
| git_log | Show commit history | Understand project history |
| git_commit | Create a commit | ONLY when user explicitly asks |

### Knowledge
| index_files | Index files for search | Build knowledge base from files |
| search_knowledge | Search indexed content | Query previously indexed content |

### Media
| describe_image | Analyze an image | User asks about an image |
| transcribe_audio | Transcribe audio | User asks to transcribe audio |
| process_video | Process video | User asks to analyze video |

### Task Tracking
| task_plan | Track multi-step work | Create/update progress checklist |

## Tool Rules

1. NEVER invent a tool name. No tool exists beyond this list.
   If you need missing functionality, say so in text or use run_command.

2. ALWAYS read_file before edit_file. Never edit what you haven't read.

3. Prefer dedicated tools over run_command:
   - Read a file → read_file, not cat
   - Find files → glob_files or list_directory, not find
   - Search code → search_files, not grep
   - run_command for: installs, tests, builds, servers, and
     commands with no dedicated tool equivalent.

4. "Write code" or "show me code" WITHOUT a file path →
   respond with markdown code block. Do NOT call write_file.

5. Questions → answer directly. Don't call tools unless you
   genuinely need information you don't have.

6. git_commit requires explicit user instruction. Never auto-commit.

7. For large files, use summarize_file first to understand structure,
   then read_file with specific line ranges for details.
```

### Block 3: Agentic Behavior Rules

```
## Multi-Step Reasoning

You can chain multiple tool calls to accomplish complex tasks.
After each result, decide: call another tool, or respond.

### Approach for multi-step tasks:
1. Understand the full goal, not just the first step
2. Plan your approach before starting
3. Use task_plan to create a checklist for complex work
4. Execute tools one at a time, each result informs the next
5. When done, summarize concisely

### Example: "Fix the bug in auth.py"
1. read_file auth.py → understand the code
2. Identify the bug
3. edit_file auth.py → apply fix
4. read_file auth.py → verify edit
5. run_command "pytest tests/test_auth.py" → verify fix
6. Respond: "Fixed the null check on line 42. Tests pass."

### When to STOP:
- You have enough information to answer
- The task is complete and verified
- You hit an unresolvable error — explain it
- You're repeating a tool call with same arguments (you're stuck)

### When NOT to chain:
- Simple questions — just answer
- "Show me code" — write markdown
- Opinion questions — just respond

### Mid-Task Instructions
User may inject instructions via /btw while you work.
These appear as: [Mid-task instruction]: <message>
Adjust your approach accordingly without restarting.

### Error Handling
- Tool fails → read error, try different approach
- 3 consecutive failures → stop, explain to user
- Never retry exact same failing call
```

### Blocks 4 & 5: Dynamic Templates

```
## Current Environment
- Working directory: {working_dir}
- Git: {branch}, {status_summary}
- Recent commits: {commits}
- System: {os}, {shell}, Python {python_version}, {ram}GB RAM{gpu_info}
- Model: {current_model}
- Internet: {online_status}

## About This User
{persona_summary}
```

---

## 7. /btw Mid-Loop Injection

**Files:** `rocky/agent_runner.py` (NEW), `rocky/cli.py` (enhance)

### Architecture

```
┌─ Main Thread (CLI input) ────────────────────────┐
│  Listens for user input while agent works:        │
│    /btw <msg> → push to thread-safe queue         │
│    Ctrl+C     → set stop event                    │
│    other      → "Rocky is working. Use /btw or    │
│                  Ctrl+C"                           │
└──────────┬────────────────────────────────────────┘
           │ Queue + Event
           ▼
┌─ Worker Thread (Agent loop) ─────────────────────┐
│  Each iteration:                                  │
│    1. Check stop event → break with summary       │
│    2. Check /btw queue → inject into memory       │
│    3. Call LLM                                    │
│    4. Execute tool(s)                             │
│    5. Show result                                 │
│    6. Loop                                        │
└───────────────────────────────────────────────────┘
```

### User Experience

Rocky is working:
```
  ✔  Created app.py
  ✔  Created routes/auth.py
  ⠧  Writing routes/users.py
```

User types:
```
  /btw add input validation to all routes
```

Rocky:
```
  ⠧  Noted — adjusting...
  ✔  Created routes/users.py (with input validation)
  ⠧  Writing routes/products.py
```

### AgentRunner Implementation

```python
import threading
from queue import Queue

class AgentRunner:
    def __init__(self):
        self.btw_queue = Queue()
        self.stop_event = threading.Event()
        self.is_working = False

    def inject_btw(self, message: str):
        self.btw_queue.put(message)

    def request_stop(self):
        self.stop_event.set()

    def run(self, agent, user_input):
        self.is_working = True
        self.stop_event.clear()
        # Run agent loop in worker thread
        thread = threading.Thread(
            target=self._worker, args=(agent, user_input)
        )
        thread.start()
        return thread

    def _worker(self, agent, user_input):
        try:
            for chunk in agent.process_message(user_input):
                # Output to console (thread-safe via Rich)
                pass
        finally:
            self.is_working = False
```

---

## 8. Ctrl+C Behavior

**File:** `rocky/cli.py`

### Two States

**Ctrl+C while Rocky is working:**
- Sets `agent_runner.stop_event`
- Agent loop breaks after current tool completes
- Progress summary shown
- User can "continue" to resume

**Ctrl+C while Rocky is idle:**

Arrow-key menu:
```
  Are you sure you want to quit?

    ▶ Yes
      No
      Refresh and quit
```

- Blue ▶ selector, arrow keys to navigate, Enter to confirm
- Default: Yes
- **Yes** — quit immediately, no save
- **No** — cancel, back to terminal
- **Refresh and quit** — run /refresh (memory + persona checkpoint), then quit

---

## 9. New & Enhanced Tools

### Enhanced Existing Tools

**edit_file — add replace_all:**
```python
ToolParameter(
    name="replace_all",
    type="boolean",
    description="Replace all occurrences (default: false)",
    required=False,
    default=False
)
```

**search_files — enhanced grep:**
```python
# New parameters:
context_lines: int   # lines before/after each match
output_mode: str     # "content", "files", "count"
file_type: str       # filter by extension
```

**run_command — background execution:**
```python
run_in_background: bool  # default False
```
Returns job ID immediately. `/jobs` shows status. Rocky continues working.

**list_directory — controlled depth:**
```python
max_depth: int  # default 1
```

### New Tools

**glob_files** (`rocky/tools/files.py`):
```python
GlobFilesTool:
    name: "glob_files"
    description: "Find files matching a glob pattern"
    params: pattern (str), path (str, default ".")
    returns: sorted list of matching paths
```

**summarize_file** (`rocky/tools/files.py`):
```python
SummarizeFileTool:
    name: "summarize_file"
    description: "Structural summary (classes, functions, imports)"
    params: path (str)
    returns: file overview without full content
```
Example output:
```
auth.py (245 lines)
  Imports: flask, jwt, datetime, functools
  Classes:
    - AuthManager (lines 15-180): login(), logout(), refresh_token()
    - TokenStore (lines 182-230): get(), set(), delete()
  Functions:
    - require_auth (line 8): decorator
    - hash_password (line 232): utility
```

**task_plan** (`rocky/tools/task_plan.py`):
```python
TaskPlanTool:
    name: "task_plan"
    description: "Create/update/list task checklist"
    params: action (str), subject (str), status (str)
```
Visual output:
```
  ✔  Create project structure
  ✔  Write app.py
  ⠧  Write routes/auth.py
  ◦  Write routes/users.py
  ◦  Write tests
```

---

## 10. UI & Animations

### Icon Set (fixed-width, Rich Text with width=2)

| Icon | State | Color |
|------|-------|-------|
| ✔ | Completed/success | Green |
| ✘ | Failed/blocked | Red |
| ⚠ | Warning/caution | Yellow |
| ⠧ | In progress | Animated braille spinner |
| ◦ | Pending | Small hollow circle, red |

All icons padded to 2-character width for perfect alignment.

### Streaming Markdown

**File:** `rocky/ui/stream.py` (NEW)

Uses Rich `Live` + `Markdown` for progressive rendering:
```python
from rich.live import Live
from rich.markdown import Markdown

full_response = ""
with Live(Markdown(""), console=self.console, refresh_per_second=10) as live:
    for chunk in agent.process_message(user_input):
        full_response += chunk
        live.update(Markdown(full_response))
```

Tables, code blocks, lists render progressively as tokens stream in. Always formatted, never raw.

### Download Progress Bar

Thin line style with animated shimmer:
```
  ⠧  Downloading Qwen2.5-7B...  ━━━━━━━━━━━━━━━━━━━━╌╌╌·····╌╌╌  48%  1.1/2.2 GB
```

- Filled: `━━━` in cyan/aqua
- Unfilled: animated shimmer (bright spot travels right along dim track)
- Uses Rich Progress + Live for shimmer animation

### Arrow-Key Menu

**File:** `rocky/ui/menu.py` (NEW)

Reusable component for all selection prompts:
- Blue ▶ selector on left
- Bold text on selected option
- Arrow keys to navigate, Enter to confirm
- Used for: quit confirmation, permission prompts, sensitive data prompt

```
    ▶ Yes
      No
      Refresh and quit
```

---

## 11. Slash Commands (Final)

### New Commands
```
/btw <msg>               Mid-loop instruction injection
/refresh                  Memory + persona checkpoint
/tools                    Show permission state
/tools trust <tool>       Trust tool for session
/tools trust-all          Trust all (with caution)
/tools deny <tool>        Block tool for session
/tools reset              Reset permissions
/jobs                     Background command status
```

### Modified Commands
```
/model [name]             Show current / list all / switch model (replaces /model + /models)
```

### Removed Commands
```
/models                   Merged into /model
/exit                     Use /quit or Ctrl+C
/trust                    Use /tools trust-all
```

### Unchanged Commands
```
/help    /quit    /clear    /save [name]    /load <name>    /sessions    /version
```

Note: `/help` output must be updated to show all new commands.

---

## 12. File Map

### Modified Files
| File | Change |
|------|--------|
| `rocky/llm/prompts.py` | Complete rewrite (26 → 300-400 lines) |
| `rocky/agent.py` | Refactor into agentic loop |
| `rocky/tools/base.py` | Permission tiers |
| `rocky/tools/files.py` | replace_all, glob_files, summarize_file |
| `rocky/tools/shell.py` | run_in_background + job tracking |
| `rocky/tools/__init__.py` | Register new tools |
| `rocky/ui/permissions.py` | Arrow-key + A/D/T/X system |
| `rocky/ui/animations.py` | Updated icons (spinner, ◦, fixed alignment) |
| `rocky/ui/input.py` | /btw passthrough during agent loop |
| `rocky/ui/markdown.py` | Enhanced Rich Markdown rendering |
| `rocky/cli.py` | New commands, threading, Ctrl+C states |
| `rocky/config.py` | Persona config, permission defaults |
| `rocky/session/memory.py` | Mid-task instruction support |
| `rocky/utils/validators.py` | Sensitive data regex patterns |

### New Files
| File | Purpose |
|------|---------|
| `rocky/agent_runner.py` | Threading wrapper (input + agent threads) |
| `rocky/context.py` | Auto-refreshing environment context |
| `rocky/persona.py` | User persona + memory + encrypted vault |
| `rocky/tools/task_plan.py` | Session task tracking tool |
| `rocky/ui/menu.py` | Reusable arrow-key selector (blue ▶) |
| `rocky/ui/stream.py` | Rich Live markdown streaming |

### New Data Files (auto-created at runtime)
| Path | Purpose |
|------|---------|
| `~/.rocky/persona/persona.yaml` | User traits, preferences |
| `~/.rocky/persona/memory.yaml` | Project decisions, corrections |
| `~/.rocky/persona/vault.enc` | Encrypted sensitive data |
| `~/.rocky/persona/.key` | Machine-local encryption key |

---

## 13. Data Flow Summary

```
User types message
    │
    ▼
CLI (main thread)
    │── Pass to AgentRunner
    │── Listen for /btw or Ctrl+C
    │
    ▼
AgentRunner (worker thread)
    │
    ▼
Agent.process_message()
    │
    ├─→ Build system prompt:
    │     prompts.py (static 300-400 lines)
    │     + context.py (auto-refreshed env)
    │     + persona.py (user summary)
    │
    ├─→ Send to LLM engine
    │     │
    │     ▼
    │   LlamaCppEngine.chat()
    │     │── Stream tokens via Rich Live Markdown
    │     │── Parse tool calls from <tool_call> tags
    │     │
    │     ▼
    │   Tool calls found?
    │     ├─ No → display response, exit loop
    │     └─ Yes ─→ For each tool:
    │                 │── Check permission tier
    │                 │── Tier 0: run silently
    │                 │── Tier 1+: prompt (A/D/T/X) or trusted
    │                 │── Execute tool
    │                 │── Show result (spinner → ✔/✘)
    │                 │── Feed result back to memory
    │                 └── Loop back to LLM
    │
    ├─→ Check /btw queue each iteration
    ├─→ Check stop event each iteration
    ├─→ Loop detection (same call 3x)
    ├─→ Error chain detection (5 failures)
    │
    ▼
Loop exits → auto-refresh context → passive persona update
```
