"""Model downloader for Rocky.Ai.

Downloads GGUF models directly from HuggingFace.
No Ollama, no middleman — just direct HTTP downloads with resume support.
"""

import json
from pathlib import Path
from typing import Optional, Generator
from dataclasses import dataclass
import httpx
from rocky.utils.logging import get_logger

logger = get_logger(__name__)

# HuggingFace base URL for model files
HF_BASE_URL = "https://huggingface.co"


@dataclass
class ModelInfo:
    """Information about a downloadable model."""
    name: str
    repo_id: str
    filename: str
    size_bytes: int
    description: str
    quantization: str
    parameters: str  # e.g., "4B", "8B"
    purpose: str  # "text", "vision"


@dataclass
class DownloadProgress:
    """Progress update during download."""
    downloaded: int
    total: int
    speed_bps: float  # bytes per second
    status: str  # "downloading", "verifying", "complete", "error"
    error: Optional[str] = None

    @property
    def percent(self) -> float:
        if self.total <= 0:
            return 0.0
        return (self.downloaded / self.total) * 100


# Full model registry — 20 models from 400MB to 36GB, curated for Rocky.Ai
MODEL_REGISTRY: dict[str, ModelInfo] = {
    # ═══ Tier 1: Ultra-light (2-4GB RAM) ═══
    "qwen2.5-0.5b-q4": ModelInfo(
        name="Qwen2.5-0.5B Tiny",
        repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        filename="qwen2.5-0.5b-instruct-q4_k_m.gguf",
        size_bytes=400_000_000,
        description="Minimum viable — fast on any hardware",
        quantization="Q4_K_M",
        parameters="0.5B",
        purpose="text",
    ),
    "qwen2.5-0.5b": ModelInfo(
        name="Qwen2.5-0.5B",
        repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        filename="qwen2.5-0.5b-instruct-q8_0.gguf",
        size_bytes=530_000_000,
        description="Ultra-light, best quality at 0.5B",
        quantization="Q8_0",
        parameters="0.5B",
        purpose="text",
    ),
    # ═══ Tier 2: Light (4-8GB RAM) ═══
    "qwen2.5-1.5b-q4": ModelInfo(
        name="Qwen2.5-1.5B Fast",
        repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        filename="qwen2.5-1.5b-instruct-q4_k_m.gguf",
        size_bytes=1_000_000_000,
        description="Good balance for 4-6GB systems",
        quantization="Q4_K_M",
        parameters="1.5B",
        purpose="text",
    ),
    "qwen2.5-1.5b": ModelInfo(
        name="Qwen2.5-1.5B",
        repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        filename="qwen2.5-1.5b-instruct-q8_0.gguf",
        size_bytes=1_600_000_000,
        description="Sweet spot for 8GB no-GPU",
        quantization="Q8_0",
        parameters="1.5B",
        purpose="text",
    ),
    # ═══ Tier 3: Medium (8-12GB RAM) ═══
    "qwen2.5-3b-q4": ModelInfo(
        name="Qwen2.5-3B Fast",
        repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
        filename="qwen2.5-3b-instruct-q4_k_m.gguf",
        size_bytes=1_800_000_000,
        description="Strong general model, compressed for speed",
        quantization="Q4_K_M",
        parameters="3B",
        purpose="text",
    ),
    "qwen2.5-3b": ModelInfo(
        name="Qwen2.5-3B",
        repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
        filename="qwen2.5-3b-instruct-q5_k_m.gguf",
        size_bytes=2_360_000_000,
        description="Default for 8GB GPU systems — great balance",
        quantization="Q5_K_M",
        parameters="3B",
        purpose="text",
    ),
    # ═══ Tier 4: High (12-16GB RAM) ═══
    "qwen2.5-7b-q2": ModelInfo(
        name="Qwen2.5-7B Compact",
        repo_id="Qwen/Qwen2.5-7B-Instruct-GGUF",
        filename="qwen2.5-7b-instruct-q2_k.gguf",
        size_bytes=2_800_000_000,
        description="7B intelligence in a compact package",
        quantization="Q2_K",
        parameters="7B",
        purpose="text",
    ),
    "qwen2.5-7b": ModelInfo(
        name="Qwen2.5-7B",
        repo_id="Qwen/Qwen2.5-7B-Instruct-GGUF",
        filename="qwen2.5-7b-instruct-q3_k_m.gguf",
        size_bytes=3_800_000_000,
        description="High quality general assistant",
        quantization="Q3_K_M",
        parameters="7B",
        purpose="text",
    ),
    "qwen2.5-coder-7b": ModelInfo(
        name="Qwen2.5-Coder-7B",
        repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        size_bytes=4_200_000_000,
        description="Coding specialist — best for developers",
        quantization="Q4_K_M",
        parameters="7B",
        purpose="text",
    ),
    "qwen2.5-coder-7b-q8": ModelInfo(
        name="Qwen2.5-Coder-7B HQ",
        repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        filename="qwen2.5-coder-7b-instruct-q8_0.gguf",
        size_bytes=7_700_000_000,
        description="Max coding quality at 7B",
        quantization="Q8_0",
        parameters="7B",
        purpose="text",
    ),
    # ═══ Tier 5: Pro (24-32GB RAM, GPU) ═══
    "qwen2.5-14b-q3": ModelInfo(
        name="Qwen2.5-14B",
        repo_id="bartowski/Qwen2.5-14B-Instruct-GGUF",
        filename="Qwen2.5-14B-Instruct-Q3_K_M.gguf",
        size_bytes=6_700_000_000,
        description="14B general — major quality jump over 7B",
        quantization="Q3_K_M",
        parameters="14B",
        purpose="text",
    ),
    "qwen2.5-14b": ModelInfo(
        name="Qwen2.5-14B HQ",
        repo_id="bartowski/Qwen2.5-14B-Instruct-GGUF",
        filename="Qwen2.5-14B-Instruct-Q5_K_M.gguf",
        size_bytes=10_500_000_000,
        description="14B high quality — near-frontier intelligence",
        quantization="Q5_K_M",
        parameters="14B",
        purpose="text",
    ),
    "qwen2.5-coder-14b": ModelInfo(
        name="Qwen2.5-Coder-14B",
        repo_id="Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        filename="qwen2.5-coder-14b-instruct-q4_k_m.gguf",
        size_bytes=8_700_000_000,
        description="14B coding specialist — serious dev work",
        quantization="Q4_K_M",
        parameters="14B",
        purpose="text",
    ),
    "qwen2.5-coder-14b-q8": ModelInfo(
        name="Qwen2.5-Coder-14B HQ",
        repo_id="Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        filename="qwen2.5-coder-14b-instruct-q8_0.gguf",
        size_bytes=15_700_000_000,
        description="14B coding max quality",
        quantization="Q8_0",
        parameters="14B",
        purpose="text",
    ),
    # ═══ Tier 6: Enterprise (48-64GB RAM, GPU) ═══
    "qwen2.5-32b": ModelInfo(
        name="Qwen2.5-32B",
        repo_id="Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
        filename="qwen2.5-coder-32b-instruct-q4_k_m.gguf",
        size_bytes=19_000_000_000,
        description="32B coder — enterprise-grade intelligence",
        quantization="Q4_K_M",
        parameters="32B",
        purpose="text",
    ),
    "qwen2.5-32b-q8": ModelInfo(
        name="Qwen2.5-32B HQ",
        repo_id="Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
        filename="qwen2.5-coder-32b-instruct-q8_0.gguf",
        size_bytes=34_000_000_000,
        description="32B max quality — needs 48GB+ RAM",
        quantization="Q8_0",
        parameters="32B",
        purpose="text",
    ),
    # ═══ Tier 7: Workstation (64-100GB RAM, GPU) ═══
    "qwen2.5-72b-q2": ModelInfo(
        name="Qwen2.5-72B Compact",
        repo_id="bartowski/Qwen2.5-72B-Instruct-GGUF",
        filename="Qwen2.5-72B-Instruct-Q2_K.gguf",
        size_bytes=18_000_000_000,
        description="72B intelligence, heavily compressed — 64GB RAM",
        quantization="Q2_K",
        parameters="72B",
        purpose="text",
    ),
    "qwen2.5-72b-q3": ModelInfo(
        name="Qwen2.5-72B",
        repo_id="bartowski/Qwen2.5-72B-Instruct-GGUF",
        filename="Qwen2.5-72B-Instruct-Q3_K_M.gguf",
        size_bytes=27_000_000_000,
        description="72B high quality — frontier-class local AI",
        quantization="Q3_K_M",
        parameters="72B",
        purpose="text",
    ),
    "qwen2.5-72b": ModelInfo(
        name="Qwen2.5-72B HQ",
        repo_id="bartowski/Qwen2.5-72B-Instruct-GGUF",
        filename="Qwen2.5-72B-Instruct-Q4_K_M.gguf",
        size_bytes=36_000_000_000,
        description="72B max quality — best local model possible, 100GB RAM",
        quantization="Q4_K_M",
        parameters="72B",
        purpose="text",
    ),
}


class ModelDownloader:
    """Downloads and manages GGUF model files."""

    def __init__(self, models_dir: Optional[Path] = None):
        if models_dir is None:
            models_dir = Path.home() / ".rocky" / "models"
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.models_dir / "manifest.json"
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        """Load the local model manifest."""
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"models": {}}

    def _save_manifest(self):
        """Save the model manifest."""
        with open(self._manifest_path, "w") as f:
            json.dump(self._manifest, f, indent=2)

    def get_model_path(self, model_key: str) -> Optional[Path]:
        """Get the local path for a model if it exists."""
        info = self._manifest.get("models", {}).get(model_key)
        if info:
            path = Path(info["path"])
            if path.exists():
                return path
        return None

    def is_model_available(self, model_key: str) -> bool:
        """Check if a model is downloaded and ready."""
        return self.get_model_path(model_key) is not None

    def list_available_models(self) -> list[dict]:
        """List all models in the registry with their download status."""
        models = []
        for key, info in MODEL_REGISTRY.items():
            models.append({
                "key": key,
                "name": info.name,
                "description": info.description,
                "size_bytes": info.size_bytes,
                "parameters": info.parameters,
                "quantization": info.quantization,
                "purpose": info.purpose,
                "downloaded": self.is_model_available(key),
            })
        return models

    def list_downloaded_models(self) -> list[dict]:
        """List locally downloaded models."""
        downloaded = []
        for key, info in self._manifest.get("models", {}).items():
            path = Path(info["path"])
            if path.exists():
                downloaded.append({
                    "key": key,
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "name": info.get("name", key),
                })
        return downloaded

    def download_model(
        self,
        model_key: str,
        force: bool = False,
    ) -> Generator[DownloadProgress, None, None]:
        """Download a model from HuggingFace.

        Yields DownloadProgress updates.
        Supports resumable downloads.
        """
        # Look up model info
        model_info = MODEL_REGISTRY.get(model_key)
        if not model_info:
            yield DownloadProgress(
                downloaded=0, total=0, speed_bps=0,
                status="error",
                error=f"Unknown model: {model_key}. Available: {list(MODEL_REGISTRY.keys())}",
            )
            return

        # Check if already downloaded
        if not force and self.is_model_available(model_key):
            existing = self.get_model_path(model_key)
            yield DownloadProgress(
                downloaded=existing.stat().st_size,
                total=existing.stat().st_size,
                speed_bps=0,
                status="complete",
            )
            return

        # Build download URL
        url = f"{HF_BASE_URL}/{model_info.repo_id}/resolve/main/{model_info.filename}"
        dest_path = self.models_dir / model_info.filename
        temp_path = dest_path.with_suffix(".downloading")

        logger.info(f"Downloading {model_info.name} from {url}")

        # Check for partial download (resume support)
        downloaded_size = 0
        if temp_path.exists():
            downloaded_size = temp_path.stat().st_size

        try:
            headers = {}
            if downloaded_size > 0:
                headers["Range"] = f"bytes={downloaded_size}-"
                logger.info(f"Resuming download from {downloaded_size} bytes")

            import time
            start_time = time.time()
            last_update_time = start_time

            with httpx.stream(
                "GET",
                url,
                headers=headers,
                follow_redirects=True,
                timeout=httpx.Timeout(30.0, read=300.0),
            ) as response:
                if response.status_code == 416:
                    # Range not satisfiable — file already complete
                    if temp_path.exists():
                        temp_path.rename(dest_path)
                        self._register_model(model_key, model_info, dest_path)
                        yield DownloadProgress(
                            downloaded=dest_path.stat().st_size,
                            total=dest_path.stat().st_size,
                            speed_bps=0,
                            status="complete",
                        )
                        return

                response.raise_for_status()

                # Get total size
                content_length = int(response.headers.get("content-length", 0))
                if response.status_code == 206:
                    # Partial content — total is downloaded + remaining
                    total_size = downloaded_size + content_length
                else:
                    total_size = content_length
                    downloaded_size = 0  # Not resuming, start fresh
                    if temp_path.exists():
                        temp_path.unlink()

                mode = "ab" if downloaded_size > 0 else "wb"
                with open(temp_path, mode) as f:
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):  # 1MB chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        now = time.time()
                        elapsed = now - start_time
                        speed = downloaded_size / elapsed if elapsed > 0 else 0

                        # Yield progress every 500ms
                        if now - last_update_time >= 0.5:
                            last_update_time = now
                            yield DownloadProgress(
                                downloaded=downloaded_size,
                                total=total_size,
                                speed_bps=speed,
                                status="downloading",
                            )

            # Move to final location
            temp_path.rename(dest_path)

            # Register in manifest
            self._register_model(model_key, model_info, dest_path)

            yield DownloadProgress(
                downloaded=downloaded_size,
                total=downloaded_size,
                speed_bps=0,
                status="complete",
            )

        except Exception as e:
            logger.error(f"Download failed: {e}")
            yield DownloadProgress(
                downloaded=downloaded_size,
                total=model_info.size_bytes,
                speed_bps=0,
                status="error",
                error=str(e),
            )

    def _register_model(self, model_key: str, model_info: ModelInfo, path: Path):
        """Register a downloaded model in the manifest."""
        self._manifest["models"][model_key] = {
            "name": model_info.name,
            "path": str(path),
            "repo_id": model_info.repo_id,
            "filename": model_info.filename,
            "quantization": model_info.quantization,
            "parameters": model_info.parameters,
            "purpose": model_info.purpose,
        }
        self._save_manifest()

    def delete_model(self, model_key: str) -> bool:
        """Delete a downloaded model."""
        path = self.get_model_path(model_key)
        if path and path.exists():
            path.unlink()
            self._manifest.get("models", {}).pop(model_key, None)
            self._save_manifest()
            logger.info(f"Deleted model: {model_key}")
            return True
        return False

    def get_recommended_model(self) -> str:
        """Get the best model for this machine's hardware.

        Detects RAM, GPU, and CPU to pick the optimal model.
        Uses ~60% of available RAM as budget for model size.
        """
        from rocky.utils.platform import get_memory_gb, has_gpu, get_cpu_count

        ram_gb = get_memory_gb()
        gpu = has_gpu()
        cpus = get_cpu_count()

        if gpu:
            # GPU systems — push for maximum quality
            if ram_gb >= 100:
                return "qwen2.5-72b"          # 36GB Q4_K_M
            elif ram_gb >= 80:
                return "qwen2.5-72b-q3"       # 27GB Q3_K_M
            elif ram_gb >= 64:
                return "qwen2.5-72b-q2"       # 18GB Q2_K
            elif ram_gb >= 48:
                return "qwen2.5-32b"          # 19GB Q4_K_M
            elif ram_gb >= 32:
                return "qwen2.5-coder-14b"    # 8.7GB Q4_K_M
            elif ram_gb >= 24:
                return "qwen2.5-14b-q3"       # 6.7GB Q3_K_M
            elif ram_gb >= 16:
                return "qwen2.5-coder-7b"     # 4.2GB Q4_K_M
            elif ram_gb >= 12:
                return "qwen2.5-7b"           # 3.5GB Q3_K_M
            elif ram_gb >= 8:
                return "qwen2.5-3b"           # 2.2GB Q5_K_M
            else:
                return "qwen2.5-1.5b-q4"      # 1GB

        else:
            # CPU only — speed matters, use smaller models
            if ram_gb >= 64 and cpus >= 16:
                return "qwen2.5-14b-q3"       # 6.7GB, big CPU box
            elif ram_gb >= 32 and cpus >= 8:
                return "qwen2.5-coder-7b"     # 4.2GB
            elif ram_gb >= 16 and cpus >= 8:
                return "qwen2.5-3b-q4"        # 1.8GB
            elif ram_gb >= 8:
                return "qwen2.5-1.5b"         # 1.6GB
            elif ram_gb >= 4:
                return "qwen2.5-0.5b"         # 530MB
            else:
                return "qwen2.5-0.5b-q4"      # 400MB

    def get_system_profile(self) -> dict:
        """Get a summary of system hardware for display."""
        from rocky.utils.platform import get_memory_gb, has_gpu, get_cpu_count

        ram = get_memory_gb()
        gpu = has_gpu()
        cpus = get_cpu_count()
        rec = self.get_recommended_model()
        model = MODEL_REGISTRY.get(rec)

        return {
            "ram_gb": round(ram),
            "gpu": gpu,
            "cpu_cores": cpus,
            "recommended_model": rec,
            "model_name": model.name if model else rec,
            "model_size": format_size(model.size_bytes) if model else "?",
        }


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
