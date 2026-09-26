"""Keep one pipeline run at a time, and turn DuckDB lock errors into plain messages.

DuckDB allows a single writing process per database file. Two runs at once
(for example the dashboard button and a terminal run) would otherwise fail
halfway with a low-level "Could not set lock" IO error.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb


class WarehouseBusyError(RuntimeError):
    """Another process is using the warehouse; retrying later will work."""


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # exists but owned by someone else
        return True
    return True


@contextmanager
def pipeline_lock(warehouse_path: Path) -> Iterator[None]:
    """Exclusive lock file next to the warehouse, holding the owner's PID.
    A lock left behind by a crashed run (dead PID) is cleared automatically."""
    lock = Path(warehouse_path).with_suffix(".pipeline.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                owner = int(lock.read_text().strip() or 0)
            except (OSError, ValueError):
                owner = 0
            if owner and _pid_alive(owner):
                raise WarehouseBusyError(
                    f"A pipeline run is already in progress (process {owner}). "
                    "Wait for it to finish, then try again.") from None
            lock.unlink(missing_ok=True)  # stale lock from a crashed run
    else:
        raise WarehouseBusyError("Could not acquire the pipeline lock; try again in a moment.")
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def friendly_lock_error(exc: Exception) -> Exception:
    """Map DuckDB's file-lock IOException to WarehouseBusyError; leave others alone."""
    if isinstance(exc, duckdb.ConnectionException) and "different configuration" in str(exc):
        # Same process: e.g. the dashboard's first-run build is writing while
        # another page load tries to read. Short-lived, so callers retry.
        return WarehouseBusyError("The warehouse is being built or updated by this app right now.")
    if isinstance(exc, duckdb.IOException) and "lock" in str(exc).lower():
        holder = str(exc).split("(PID", 1)[-1].split(")", 1)[0].strip() if "(PID" in str(exc) else "unknown"
        return WarehouseBusyError(
            f"The warehouse file is in use by another program (process {holder}). This usually means a "
            "pipeline run is still going, or another dashboard or terminal has it open. Wait for the run "
            f"to finish, or stop that program (for example `kill {holder}` on Mac/Linux), then try again.")
    return exc
