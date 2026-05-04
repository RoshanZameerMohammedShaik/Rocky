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

Rocky ships with 10 models and auto-selects the best one for your hardware at install time.

| Tier | Model | Size | RAM | Best For |
|------|-------|------|-----|----------|
| 1 | Qwen2.5-0.5B Q4/Q8 | 400-530 MB | 2-4 GB | Ultra-light, any hardware |
| 2 | Qwen2.5-1.5B Q4/Q8 | 1.0-1.6 GB | 4-8 GB | Light, good for CPU-only |
| 3 | Qwen2.5-3B Q4/Q5 | 1.8-2.2 GB | 8-12 GB | Default for GPU systems |
| 4 | Qwen2.5-7B Q2/Q3 | 2.8-3.5 GB | 12-16 GB | High quality |
| 5 | Qwen2.5-Coder-7B Q4/Q8 | 4.2-7.7 GB | 16 GB+ | Premium, coding specialist |

Switch models with `/models` inside Rocky. Re-detect hardware with `python -m rocky.setup_model`.

## License

MIT
