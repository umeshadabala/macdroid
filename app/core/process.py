"""
Process management utility for PhoneConnect.
Handles launching, monitoring, and cleanly terminating child processes (ADB, scrcpy, helpers).
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from typing import Callable, List, Optional

from app.core.logger import get_logger

log = get_logger("process")


class ManagedProcess:
    """Represents a supervised child process."""

    def __init__(
        self,
        name: str,
        command: List[str],
        env: Optional[dict] = None,
        on_exit: Optional[Callable[[int], None]] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.name = name
        self.command = command
        self.env = env
        self.on_exit = on_exit
        self.on_output = on_output
        self.process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._is_terminating = False

    def start(self) -> bool:
        """Start the child process."""
        try:
            log.info("Starting managed process [%s]: %s", self.name, " ".join(self.command))
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=self.env or os.environ.copy(),
            )

            if self.on_output and self.process.stdout:
                self._reader_thread = threading.Thread(
                    target=self._read_output,
                    name=f"Reader-{self.name}",
                    daemon=True,
                )
                self._reader_thread.start()

            # Watcher thread to notify on exit
            threading.Thread(
                target=self._wait_exit,
                name=f"Watcher-{self.name}",
                daemon=True,
            ).start()

            return True
        except Exception as e:
            log.error("Failed to start managed process [%s]: %s", self.name, e)
            return False

    def _read_output(self) -> None:
        if not self.process or not self.process.stdout:
            return
        try:
            for line in iter(self.process.stdout.readline, ""):
                cleaned = line.rstrip()
                if cleaned:
                    if self.on_output:
                        self.on_output(cleaned)
                    log.debug("[%s] %s", self.name, cleaned)
        except Exception as e:
            if not self._is_terminating:
                log.debug("[%s] Stream reader ended: %s", self.name, e)

    def _wait_exit(self) -> None:
        if not self.process:
            return
        code = self.process.wait()
        log.info("Managed process [%s] exited with code %d", self.name, code)
        if self.on_exit and not self._is_terminating:
            self.on_exit(code)

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def terminate(self, timeout: float = 2.0) -> None:
        """Gracefully terminate the process, escalating to kill if necessary."""
        if not self.process or self.process.poll() is not None:
            return

        self._is_terminating = True
        log.info("Terminating process [%s] (pid=%d)...", self.name, self.process.pid)
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                log.warning("Process [%s] did not terminate in time. Killing...", self.name)
                self.process.kill()
                self.process.wait(timeout=1.0)
        except Exception as e:
            log.error("Error terminating process [%s]: %s", self.name, e)


class ProcessManager:
    """Registry and lifecycle manager for all child processes in the application."""

    def __init__(self) -> None:
        self._processes: List[ManagedProcess] = []
        self._lock = threading.Lock()

    def launch(
        self,
        name: str,
        command: List[str],
        env: Optional[dict] = None,
        on_exit: Optional[Callable[[int], None]] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> ManagedProcess:
        """Create, track, and start a managed process."""
        proc = ManagedProcess(name, command, env=env, on_exit=on_exit, on_output=on_output)
        with self._lock:
            self._processes.append(proc)
        proc.start()
        return proc

    def stop_all(self) -> None:
        """Terminate all tracked child processes."""
        with self._lock:
            running = [p for p in self._processes if p.is_running()]
            for p in running:
                p.terminate()
            self._processes.clear()


process_manager = ProcessManager()
