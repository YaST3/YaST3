
import platform

cached: dict[str, str] | None = None

def read_os_release() -> dict[str, str]:
    """Read freedesktop os-release and return key-value pairs."""
    global cached
    if cached is not None:
        return cached

    try:
        os_release_info = platform.freedesktop_os_release()
    except Exception:
        os_release_info = {}

    cached = os_release_info
    return os_release_info
