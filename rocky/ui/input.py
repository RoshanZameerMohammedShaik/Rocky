"""Input handling for Rocky.Ai."""

import re
import readline
from typing import Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from rocky.config import get_config

# Filter terminal escape sequences (focus events, etc)
_ESCAPE_FILTER = re.compile(r'\x1b\[[OI]|\x1b\[\d+[A-Z]')

# Custom style for prompt
PROMPT_STYLE = Style.from_dict({
    "prompt": "bold cyan",
    "input": "",
})


class InputHandler:
    """Handles user input with history and completion."""

    def __init__(self):
        config = get_config()
        history_file = config.paths.base / "history"

        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            style=PROMPT_STYLE,
            enable_history_search=True,
        )

    def get_input(self, prompt: str = "You: ") -> Optional[str]:
        """Get user input with history support."""
        try:
            text = self.session.prompt(prompt)
            if text:
                text = _ESCAPE_FILTER.sub('', text)
            return text
        except EOFError:
            return None
        except KeyboardInterrupt:
            return None

    def get_multiline_input(self, prompt: str = "You: ") -> Optional[str]:
        """Get multiline input (end with empty line)."""
        lines = []
        try:
            first_line = self.session.prompt(prompt)
            if first_line is None:
                return None
            lines.append(first_line)

            while True:
                line = self.session.prompt("... ")
                if line == "":
                    break
                lines.append(line)

            return "\n".join(lines)
        except (EOFError, KeyboardInterrupt):
            return None


def setup_readline_history():
    """Setup readline history for basic input() calls."""
    config = get_config()
    history_file = config.paths.base / "history_readline"

    try:
        readline.read_history_file(str(history_file))
    except FileNotFoundError:
        pass

    readline.set_history_length(1000)

    import atexit
    atexit.register(readline.write_history_file, str(history_file))


# Global input handler
_input_handler: Optional[InputHandler] = None


def get_input_handler() -> InputHandler:
    """Get or create global input handler."""
    global _input_handler
    if _input_handler is None:
        _input_handler = InputHandler()
    return _input_handler
