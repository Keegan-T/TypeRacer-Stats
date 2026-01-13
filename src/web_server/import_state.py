import time
from typing import Optional


class ImportState:
    """Tracks the current import state for the web server."""

    _current_user: Optional[str] = None
    _universe: str = "play"
    _start_time: Optional[float] = None

    @classmethod
    def start_import(cls, username: str, universe: str = "play"):
        """Mark a user as being imported."""
        cls._current_user = username
        cls._universe = universe
        cls._start_time = time.time()

    @classmethod
    def finish_import(cls):
        """Clear the import state."""
        cls._current_user = None
        cls._universe = "play"
        cls._start_time = None

    @classmethod
    def is_importing(cls) -> bool:
        """Check if an import is currently in progress."""
        return cls._current_user is not None

    @classmethod
    def get_current_import(cls) -> Optional[dict]:
        """Get information about the current import."""
        if not cls.is_importing():
            return None

        return {
            "username": cls._current_user,
            "universe": cls._universe,
            "start_time": cls._start_time,
            "elapsed": time.time() - cls._start_time if cls._start_time else 0,
        }
