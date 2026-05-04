"""Network utilities for Rocky.Ai."""

import socket
from typing import Optional
import httpx


def is_online(timeout: float = 2.0) -> bool:
    """Check if internet connection is available."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        pass

    # Fallback: try to reach a reliable host
    try:
        with httpx.Client(timeout=timeout) as client:
            client.head("https://www.google.com")
        return True
    except Exception:
        return False


def get_local_ip() -> Optional[str]:
    """Get local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None
