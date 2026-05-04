"""Conversation memory for Rocky.Ai."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from rocky.llm.engine import ChatMessage


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)


class ConversationMemory:
    """Manages conversation history."""

    def __init__(self, max_turns: int = 50):
        self.turns: list[ConversationTurn] = []
        self.max_turns = max_turns
        self.system_prompt: Optional[str] = None

    def set_system_prompt(self, prompt: str):
        """Set the system prompt."""
        self.system_prompt = prompt

    def add_user_message(self, content: str):
        """Add a user message."""
        self.turns.append(ConversationTurn(role="user", content=content))
        self._trim_if_needed()

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[list[dict]] = None,
        tool_results: Optional[list[dict]] = None
    ):
        """Add an assistant message."""
        self.turns.append(ConversationTurn(
            role="assistant",
            content=content,
            tool_calls=tool_calls or [],
            tool_results=tool_results or []
        ))
        self._trim_if_needed()

    def add_tool_result(self, tool_name: str, result: str):
        """Add a tool result to the last assistant turn."""
        if self.turns and self.turns[-1].role == "assistant":
            self.turns[-1].tool_results.append({
                "tool": tool_name,
                "result": result
            })

    def add_mid_task_instruction(self, instruction: str):
        """Add a /btw mid-task instruction from the user."""
        self.turns.append(ConversationTurn(
            role="user",
            content=f"[Mid-task instruction]: {instruction}"
        ))
        self._trim_if_needed()

    def get_messages(self) -> list[ChatMessage]:
        """Get messages in format for LLM."""
        messages = []

        if self.system_prompt:
            messages.append(ChatMessage(role="system", content=self.system_prompt))

        for turn in self.turns:
            content = turn.content

            # Include tool results in assistant messages
            if turn.tool_results:
                for tr in turn.tool_results:
                    content += f"\n\n[Tool: {tr['tool']}]\n{tr['result']}"

            messages.append(ChatMessage(role=turn.role, content=content))

        return messages

    def get_last_n_turns(self, n: int) -> list[ConversationTurn]:
        """Get the last n turns."""
        return self.turns[-n:]

    def clear(self):
        """Clear conversation history."""
        self.turns.clear()

    def _trim_if_needed(self):
        """Trim old turns if exceeding max."""
        if len(self.turns) > self.max_turns:
            excess = len(self.turns) - self.max_turns
            self.turns = self.turns[excess:]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "system_prompt": self.system_prompt,
            "turns": [
                {
                    "role": t.role,
                    "content": t.content,
                    "timestamp": t.timestamp.isoformat(),
                    "tool_calls": t.tool_calls,
                    "tool_results": t.tool_results,
                }
                for t in self.turns
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMemory":
        """Create from dictionary."""
        memory = cls()
        memory.system_prompt = data.get("system_prompt")

        for turn_data in data.get("turns", []):
            turn = ConversationTurn(
                role=turn_data["role"],
                content=turn_data["content"],
                timestamp=datetime.fromisoformat(turn_data.get("timestamp", datetime.now().isoformat())),
                tool_calls=turn_data.get("tool_calls", []),
                tool_results=turn_data.get("tool_results", []),
            )
            memory.turns.append(turn)

        return memory
