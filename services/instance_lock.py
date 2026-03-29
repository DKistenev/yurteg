"""Single-instance lock — prevents running two copies of the app."""

from __future__ import annotations

import atexit
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_LOCK_PATH = Path.home() / ".yurteg" / "app.lock"
_lock_fd: int | None = None


def acquire_instance_lock() -> None:
    """Acquire exclusive file lock or exit with user-friendly message.

    Must be called before ui.run(). On failure, prints message to stderr
    and calls sys.exit(1).
    """
    global _lock_fd
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        fd = os.open(str(_LOCK_PATH), os.O_CREAT | os.O_RDWR)
    except OSError as e:
        logger.error("Не удалось создать lock-файл: %s", e)
        sys.exit(1)

    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError):
        os.close(fd)
        print("ЮрТэг уже запущен.", file=sys.stderr)
        logger.warning("Попытка повторного запуска заблокирована (lock busy)")
        sys.exit(1)

    # Write PID for debugging
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())

    _lock_fd = fd
    atexit.register(_release_lock)
    logger.info("Instance lock acquired (PID %d)", os.getpid())


def _release_lock() -> None:
    """Release file lock on normal exit."""
    global _lock_fd
    if _lock_fd is not None:
        try:
            os.close(_lock_fd)
        except OSError:
            pass
        _lock_fd = None
        logger.debug("Instance lock released")
