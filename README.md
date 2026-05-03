# Rocky.AI

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

| Model | Size | RAM Needed | Best For |
|-------|------|-----------|----------|
| Qwen2.5-0.5B | ~530MB | 4GB+ | Low-RAM systems |
| Qwen2.5-3B (default) | ~2.2GB | 8GB+ | Best balance of speed and quality |
| Qwen2.5-7B | ~3.5GB | 12GB+ | Maximum quality |

Switch models with `/models` and `/model` commands inside Rocky.

## License

MIT
