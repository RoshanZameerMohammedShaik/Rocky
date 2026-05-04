"""Configuration management for Rocky.Ai."""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import platform


@dataclass
class ModelConfig:
    """Model configuration."""
    default: str = "qwen2.5-3b"  # Model key from registry
    context_length: int = 8192
    temperature: float = 0.7
    max_tokens: int = 4096
    gpu_layers: int = -1  # -1 = auto (all layers on GPU)


@dataclass
class PermissionsConfig:
    auto_trust: bool = False


@dataclass
class UIConfig:
    theme: str = "dark"
    show_thinking: bool = True


@dataclass
class OfflineConfig:
    prefer_offline: bool = True


@dataclass
class PathsConfig:
    base: Path = field(default_factory=lambda: Path.home() / ".rocky")
    models: Path = field(default_factory=lambda: Path.home() / ".rocky" / "models")
    sessions: Path = field(default_factory=lambda: Path.home() / ".rocky" / "sessions")
    knowledge: Path = field(default_factory=lambda: Path.home() / ".rocky" / "knowledge")
    logs: Path = field(default_factory=lambda: Path.home() / ".rocky" / "logs")


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    permissions: PermissionsConfig = field(default_factory=PermissionsConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    offline: OfflineConfig = field(default_factory=OfflineConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load config from file or create default."""
        if config_path is None:
            config_path = Path.home() / ".rocky" / "config.yaml"

        config = cls()

        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}

            if "model" in data:
                model_data = data["model"]
                config.model = ModelConfig(
                    default=model_data.get("default", config.model.default),
                    context_length=model_data.get("context_length", config.model.context_length),
                    temperature=model_data.get("temperature", config.model.temperature),
                    max_tokens=model_data.get("max_tokens", config.model.max_tokens),
                    gpu_layers=model_data.get("gpu_layers", config.model.gpu_layers),
                )
            if "permissions" in data:
                config.permissions = PermissionsConfig(**data["permissions"])
            if "ui" in data:
                config.ui = UIConfig(**data["ui"])
            if "offline" in data:
                config.offline = OfflineConfig(**data["offline"])

        # Ensure directories exist
        for path_field in [config.paths.base, config.paths.models,
                           config.paths.sessions, config.paths.knowledge,
                           config.paths.logs]:
            path_field.mkdir(parents=True, exist_ok=True)

        return config

    def save(self, config_path: Optional[Path] = None):
        """Save config to file."""
        if config_path is None:
            config_path = Path.home() / ".rocky" / "config.yaml"

        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "model": {
                "default": self.model.default,
                "context_length": self.model.context_length,
                "temperature": self.model.temperature,
                "max_tokens": self.model.max_tokens,
                "gpu_layers": self.model.gpu_layers,
            },
            "permissions": {"auto_trust": self.permissions.auto_trust},
            "ui": {
                "theme": self.ui.theme,
                "show_thinking": self.ui.show_thinking,
            },
            "offline": {"prefer_offline": self.offline.prefer_offline},
        }

        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)


def get_platform() -> str:
    """Get current platform: 'macos', 'windows', or 'linux'."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    return "linux"


def get_shell() -> str:
    """Get appropriate shell for current platform."""
    if get_platform() == "windows":
        return "powershell"
    return os.environ.get("SHELL", "/bin/bash")


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config
