# Rocky.Ai

A fully local, open-source agentic AI CLI tool that runs entirely on your machine — no cloud, no API keys, no external AI apps.

## What Makes Rocky Different

- **Truly self-contained** — No Ollama, no LM Studio, no background services. Rocky embeds its own AI engine.
- **Single install** — `pip install rocky-ai` and you're done. Model downloads on first run.
- **Private by default** — Everything runs locally. Your data never leaves your machine.
- **Agentic** — Rocky can read/write files, run commands, search the web, and work with git.

## Features

- Local LLM (Qwen2.5) — embedded via llama-cpp-python, no separate app
- File operations with glob patterns
- Shell command execution with permissions
- Web search (offline-first, online when needed)
- Audio transcription (Whisper, optional)
- Knowledge base (semantic search)
- Beautiful terminal UI
- GPU acceleration (CUDA, Metal, Vulkan — auto-detected)

## Requirements

- Python 3.10+
- 8GB RAM minimum (4GB usable with 1.7B model)
- ~6GB disk space (app + model)
- macOS, Windows, or Linux

## Installation

```bash
pip install rocky-ai
```

For CUDA GPU acceleration on Windows/Linux:
```bash
CMAKE_ARGS="-DGGML_CUDA=on" pip install rocky-ai
```

## Usage

```bash
Rocky
```

On first run, Rocky downloads its AI model (~3GB). After that, it works fully offline.

## Models

Rocky ships with 19 models across 7 tiers and auto-selects the best one at install time.

| Tier | Model | Size | RAM |
|------|-------|------|-----|
| 1 Ultra-Light | Qwen2.5-0.5B | 400-530 MB | 2-4 GB |
| 2 Light | Qwen2.5-1.5B | 1.0-1.6 GB | 4-8 GB |
| 3 Medium | Qwen2.5-3B | 1.8-2.2 GB | 8-12 GB |
| 4 High | Qwen2.5-7B / Coder-7B | 2.8-7.7 GB | 12-16 GB |
| 5 Pro | Qwen2.5-14B / Coder-14B | 6.2-14.6 GB | 24-32 GB |
| 6 Enterprise | Qwen2.5-Coder-32B | 17.7-31.7 GB | 48-64 GB |
| 7 Workstation | Qwen2.5-72B | 16.8-33.5 GB | 64-100 GB |

Switch models with `/models` inside Rocky. Re-detect hardware with `python -m rocky.setup_model`.

## License

MIT
