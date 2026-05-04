"""Post-install model setup for Rocky.Ai.

Run after pip install to detect hardware and download the best model.
Usage: python -m rocky.setup_model
"""

import sys
from rocky.llm.downloader import ModelDownloader, MODEL_REGISTRY, format_size


def main():
    """Detect system hardware and download the optimal model."""
    from rocky.utils.platform import get_memory_gb, has_gpu, get_cpu_count

    ram = get_memory_gb()
    gpu = has_gpu()
    cpus = get_cpu_count()

    print()
    print("  \033[1mRocky.Ai — System Detection\033[0m")
    print()
    print(f"  RAM:  {ram:.0f} GB")
    print(f"  CPU:  {cpus} cores")
    print(f"  GPU:  {'Yes' if gpu else 'No'}")
    print()

    dl = ModelDownloader()
    recommended = dl.get_recommended_model()
    model_info = MODEL_REGISTRY[recommended]

    print(f"  Best model for your system: \033[1;36m{model_info.name}\033[0m")
    print(f"  Size: {format_size(model_info.size_bytes)}")
    print(f"  Quantization: {model_info.quantization}")
    print(f"  {model_info.description}")
    print()

    if dl.is_model_available(recommended):
        print("  \033[32m\u2714 Model already downloaded\033[0m")
        return 0

    print(f"  Downloading {model_info.name}...")
    print()

    for progress in dl.download_model(recommended):
        if progress.status == "downloading":
            pct = progress.percent
            bar_len = 40
            filled = int(bar_len * pct / 100)
            bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
            speed_mb = progress.speed_bps / (1024 * 1024)
            sys.stdout.write(
                f"\r  [{bar}] {pct:.0f}%  "
                f"{format_size(progress.downloaded)} / "
                f"{format_size(progress.total)}  "
                f"({speed_mb:.1f} MB/s)"
            )
            sys.stdout.flush()
        elif progress.status == "error":
            print(f"\n\n  \033[31m\u2718 Download failed: {progress.error}\033[0m")
            return 1
        elif progress.status == "complete":
            print(f"\n\n  \033[32m\u2714 Downloaded {model_info.name}\033[0m")
            break

    print()
    print("  Ready! Type \033[1mRocky\033[0m to start.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
