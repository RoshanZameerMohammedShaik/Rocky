"""LLM inference engine for Rocky.AI using llama-cpp-python.

Runs models directly in-process — no Ollama, no external apps, no UI.
Just pure local inference via llama.cpp bindings.
"""

import json
import re
from typing import Generator, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChatMessage:
    """A chat message."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    images: Optional[list[str]] = None
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolCall:
    """A tool call parsed from model output."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    """Response from chat completion."""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    done: bool = False
    model: str = ""
    tokens_generated: int = 0
    tokens_per_second: float = 0.0


class LlamaCppEngine:
    """Inference engine using llama-cpp-python.

    Loads GGUF models directly in-process. No external service required.
    Supports CPU, CUDA, Metal, and Vulkan acceleration automatically.
    """

    def __init__(self):
        self._model = None
        self._model_path: Optional[str] = None
        self._chat_format: Optional[str] = None

    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self._model is not None

    def load_model(
        self,
        model_path: str,
        n_ctx: int = 8192,
        n_gpu_layers: int = -1,
        n_threads: Optional[int] = None,
        chat_format: Optional[str] = None,
        verbose: bool = False,
    ) -> bool:
        """Load a GGUF model file.

        Args:
            model_path: Path to the .gguf file
            n_ctx: Context window size
            n_gpu_layers: GPU layers (-1 = all, 0 = CPU only)
            n_threads: CPU threads (None = auto-detect)
            chat_format: Chat template format (None = auto-detect from model)
            verbose: Show llama.cpp debug output
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            logger.error("llama-cpp-python not installed. Run: pip install llama-cpp-python")
            return False

        # Unload existing model if any
        self.unload()

        if not Path(model_path).exists():
            logger.error(f"Model file not found: {model_path}")
            return False

        try:
            logger.info(f"Loading model: {model_path}")

            kwargs = {
                "model_path": model_path,
                "n_ctx": n_ctx,
                "n_gpu_layers": n_gpu_layers,
                "verbose": verbose,
            }

            if n_threads is not None:
                kwargs["n_threads"] = n_threads

            if chat_format:
                kwargs["chat_format"] = chat_format

            self._model = Llama(**kwargs)
            self._model_path = model_path
            self._chat_format = chat_format

            logger.info(f"Model loaded successfully: {Path(model_path).name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self._model = None
            return False

    def unload(self):
        """Unload the current model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._model_path = None
            logger.info("Model unloaded")

    def chat(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        top_p: float = 0.8,
        top_k: int = 20,
        max_tokens: int = 4096,
        stream: bool = True,
    ) -> Generator[ChatResponse, None, None]:
        """Run chat completion.

        Args:
            messages: Conversation history
            tools: Tool schemas for function calling
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
        """
        if not self._model:
            yield ChatResponse(
                content="Error: No model loaded.",
                done=True
            )
            return

        # Convert messages to llama-cpp format
        api_messages = self._format_messages(messages, tools)

        try:
            if stream:
                yield from self._stream_chat(api_messages, temperature, top_p, top_k, max_tokens, tools)
            else:
                yield from self._batch_chat(api_messages, temperature, top_p, top_k, max_tokens, tools)
        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield ChatResponse(content=f"Error: {e}", done=True)

    def _format_messages(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict]] = None,
    ) -> list[dict]:
        """Convert ChatMessages to the format llama-cpp-python expects."""
        api_messages = []

        for msg in messages:
            api_msg = {"role": msg.role, "content": msg.content or ""}

            if msg.tool_calls:
                api_msg["tool_calls"] = msg.tool_calls

            if msg.tool_call_id:
                api_msg["tool_call_id"] = msg.tool_call_id

            api_messages.append(api_msg)

        return api_messages

    def _stream_chat(
        self,
        messages: list[dict],
        temperature: float,
        top_p: float,
        top_k: int,
        max_tokens: int,
        tools: Optional[list[dict]] = None,
    ) -> Generator[ChatResponse, None, None]:
        """Stream chat completion tokens."""
        full_content = ""

        kwargs = {
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = self._format_tools(tools)
            kwargs["tool_choice"] = "auto"

        try:
            response_stream = self._model.create_chat_completion(**kwargs)

            for chunk in response_stream:
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                finish_reason = chunk.get("choices", [{}])[0].get("finish_reason")

                if content:
                    full_content += content
                    yield ChatResponse(content=content, done=False)

                if finish_reason:
                    # Parse tool calls from the accumulated response
                    tool_calls = self._parse_tool_calls(full_content)

                    yield ChatResponse(
                        content="" if tool_calls else "",
                        tool_calls=tool_calls,
                        done=True,
                        model=Path(self._model_path).name if self._model_path else "",
                    )
                    return

            # If stream ended without finish_reason
            tool_calls = self._parse_tool_calls(full_content)
            yield ChatResponse(
                content="",
                tool_calls=tool_calls,
                done=True,
                model=Path(self._model_path).name if self._model_path else "",
            )

        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            # Fall back to non-streaming
            yield from self._batch_chat(messages, temperature, top_p, top_k, max_tokens, tools)

    def _batch_chat(
        self,
        messages: list[dict],
        temperature: float,
        top_p: float,
        top_k: int,
        max_tokens: int,
        tools: Optional[list[dict]] = None,
    ) -> Generator[ChatResponse, None, None]:
        """Non-streaming chat completion."""
        kwargs = {
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_tokens": max_tokens,
            "stream": False,
        }

        if tools:
            kwargs["tools"] = self._format_tools(tools)
            kwargs["tool_choice"] = "auto"

        response = self._model.create_chat_completion(**kwargs)

        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        # Check for native tool_calls in response
        native_tool_calls = message.get("tool_calls", [])
        tool_calls = []

        if native_tool_calls:
            for i, tc in enumerate(native_tool_calls):
                func = tc.get("function", {})
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                tool_calls.append(ToolCall(
                    id=tc.get("id", f"call_{i}"),
                    name=func.get("name", ""),
                    arguments=args,
                ))
        else:
            # Parse tool calls from text response
            tool_calls = self._parse_tool_calls(content)

        usage = response.get("usage", {})

        yield ChatResponse(
            content=content,
            tool_calls=tool_calls,
            done=True,
            model=Path(self._model_path).name if self._model_path else "",
            tokens_generated=usage.get("completion_tokens", 0),
        )

    def _format_tools(self, tools: list[dict]) -> list[dict]:
        """Format tool schemas for llama-cpp-python's tool calling."""
        formatted = []
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    }),
                },
            })
        return formatted

    @staticmethod
    def _fix_json(text: str) -> str:
        """Fix common JSON issues from model output.

        Models sometimes double the outer braces: {{"name":...}}
        instead of {"name":...}. Strip matched extra outer braces.
        """
        fixed = text.strip()
        # If it starts with {{ and ends with }}, strip one layer
        if (
            fixed.startswith('{{')
            and fixed.endswith('}}')
            and not fixed.startswith('{{{')
        ):
            fixed = fixed[1:-1]
        return fixed

    def _parse_tool_calls(self, text: str) -> list[ToolCall]:
        """Parse tool calls from model text output.

        Supports multiple formats:
        1. <tool_call>{"name": "...", "arguments": {...}}</tool_call>
        2. ```json {"tool": "...", "arguments": {...}} ```
        3. Inline {"tool": "...", "arguments": {...}}

        Handles malformed JSON (doubled braces, etc).
        """
        tool_calls = []
        call_id = 0

        # Pattern 1: <tool_call> tags (greedy to capture nested braces)
        qwen_pattern = r'<tool_call>\s*([\s\S]*?)\s*</tool_call>'
        for match in re.finditer(qwen_pattern, text):
            raw = self._fix_json(match.group(1).strip())
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Try to extract JSON object from the raw text
                obj_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if obj_match:
                    try:
                        data = json.loads(obj_match.group(0))
                    except json.JSONDecodeError:
                        continue
                else:
                    continue

            name = data.get("name", "")
            args = data.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if name:
                tool_calls.append(ToolCall(
                    id=f"call_{call_id}",
                    name=name,
                    arguments=args,
                ))
                call_id += 1

        if tool_calls:
            return tool_calls

        # Pattern 2: JSON code blocks
        json_block_pattern = r'```json\s*\n?\s*(\{[^`]+\})\s*\n?```'
        for match in re.finditer(json_block_pattern, text, re.DOTALL):
            raw = self._fix_json(match.group(1))
            try:
                data = json.loads(raw)
                name = (
                    data.get("tool")
                    or data.get("name")
                    or data.get("function", "")
                )
                args = data.get(
                    "arguments",
                    data.get("params", data.get("parameters", {})),
                )
                if isinstance(args, str):
                    args = json.loads(args)
                if name:
                    tool_calls.append(ToolCall(
                        id=f"call_{call_id}",
                        name=name,
                        arguments=args,
                    ))
                    call_id += 1
            except json.JSONDecodeError:
                continue

        if tool_calls:
            return tool_calls

        # Pattern 3: Inline JSON with tool or name key
        inline_pattern = r'(\{["\s]*(?:tool|name)["\s]*:[\s\S]*?\})\s*\}'
        for match in re.finditer(inline_pattern, text):
            raw = self._fix_json(match.group(0))
            try:
                data = json.loads(raw)
                name = data.get("tool") or data.get("name", "")
                args = data.get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                if name:
                    tool_calls.append(ToolCall(
                        id=f"call_{call_id}",
                        name=name,
                        arguments=args,
                    ))
                    call_id += 1
            except json.JSONDecodeError:
                continue

        return tool_calls

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = True,
    ) -> Generator[str, None, None]:
        """Simple text generation (non-chat)."""
        if not self._model:
            yield "Error: No model loaded."
            return

        try:
            if stream:
                response = self._model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                )
                for chunk in response:
                    text = chunk.get("choices", [{}])[0].get("text", "")
                    if text:
                        yield text
            else:
                response = self._model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                yield response.get("choices", [{}])[0].get("text", "")

        except Exception as e:
            logger.error(f"Generate error: {e}")
            yield f"Error: {e}"

    def get_model_info(self) -> dict:
        """Get information about the currently loaded model."""
        if not self._model:
            return {"loaded": False}

        return {
            "loaded": True,
            "path": self._model_path,
            "name": Path(self._model_path).stem if self._model_path else "unknown",
            "n_ctx": self._model.n_ctx() if hasattr(self._model, 'n_ctx') else 0,
            "chat_format": self._chat_format,
        }
