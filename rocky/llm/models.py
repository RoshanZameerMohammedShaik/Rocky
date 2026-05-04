"""Model management for Rocky.Ai.

Manages model downloading, loading, and switching.
Uses llama-cpp-python engine with HuggingFace model downloads.
No Ollama dependency.
"""

from typing import Optional
from rich.console import Console
from rocky.llm.engine import LlamaCppEngine
from rocky.llm.downloader import ModelDownloader, MODEL_REGISTRY, format_size
from rocky.config import get_config
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


class ModelManager:
    """Manages model lifecycle: download, load, switch, unload."""

    def __init__(self, engine: LlamaCppEngine, console: Optional[Console] = None):
        self.engine = engine
        self.console = console or Console()
        self.config = get_config()
        self.downloader = ModelDownloader()
        self._current_model_key: Optional[str] = None

    def get_text_model_key(self) -> str:
        """Get the configured text model key."""
        configured = self.config.model.default
        if configured and configured in MODEL_REGISTRY:
            return configured
        return self.downloader.get_recommended_model()

    def get_text_model(self) -> str:
        """Get the current text model name (for display)."""
        if self._current_model_key:
            info = MODEL_REGISTRY.get(self._current_model_key)
            if info:
                return f"{info.name} ({info.quantization})"
        return "No model loaded"

    def ensure_model(self, model_type: str = "text") -> bool:
        """Ensure a model is downloaded and loaded.

        Downloads if not present, then loads into the engine.
        """
        if model_type == "text":
            model_key = self.get_text_model_key()
        else:
            logger.warning(f"Unknown model type: {model_type}")
            return False

        # Check if already loaded
        if self.engine.is_loaded() and self._current_model_key == model_key:
            return True

        # Download if needed
        if not self.downloader.is_model_available(model_key):
            if not self._download_model(model_key):
                return False

        # Load the model
        return self._load_model(model_key)

    def _download_model(self, model_key: str) -> bool:
        """Download a model with progress display."""
        model_info = MODEL_REGISTRY.get(model_key)
        if not model_info:
            self.console.print(f"[red]Unknown model: {model_key}[/red]")
            return False

        self.console.print(
            f"[yellow]Downloading {model_info.name} "
            f"({format_size(model_info.size_bytes)})...[/yellow]"
        )
        self.console.print(f"[dim]{model_info.description}[/dim]")

        from rocky.ui.progress import SimpleProgress

        with SimpleProgress(
            self.console,
            f"Downloading {model_info.name}",
            total=100,
        ) as progress:
            for update in self.downloader.download_model(model_key):
                if update.status == "error":
                    self.console.print(f"\n[red]Download failed: {update.error}[/red]")
                    return False

                if update.status == "downloading":
                    progress.update(
                        completed=update.percent,
                        description=(
                            f"Downloading {model_info.name} "
                            f"({format_size(int(update.downloaded))} / "
                            f"{format_size(int(update.total))})"
                        ),
                    )

                if update.status == "complete":
                    progress.update(completed=100)

        self.console.print(f"[green]Downloaded {model_info.name}[/green]")
        return True

    def _load_model(self, model_key: str) -> bool:
        """Load a model into the engine."""
        model_path = self.downloader.get_model_path(model_key)
        if not model_path:
            self.console.print(f"[red]Model not found: {model_key}[/red]")
            return False

        model_info = MODEL_REGISTRY.get(model_key)
        model_name = model_info.name if model_info else model_key

        self.console.print(f"[dim]Loading {model_name}...[/dim]")

        # Determine GPU layers
        n_gpu_layers = -1  # Use all available GPU layers by default

        success = self.engine.load_model(
            model_path=str(model_path),
            n_ctx=self.config.model.context_length,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )

        if success:
            self._current_model_key = model_key
            self.console.print(f"[green]Loaded {model_name}[/green]")
        else:
            self.console.print(f"[red]Failed to load {model_name}[/red]")

        return success

    def list_models(self) -> list[dict]:
        """List all available and downloaded models."""
        return self.downloader.list_available_models()

    def switch_model(self, model_key: str) -> bool:
        """Switch to a different model."""
        if model_key not in MODEL_REGISTRY:
            self.console.print(f"[red]Unknown model: {model_key}[/red]")
            self.console.print(
                f"[dim]Available: {', '.join(MODEL_REGISTRY.keys())}[/dim]"
            )
            return False

        self.engine.unload()
        self._current_model_key = None
        return self.ensure_model("text")
