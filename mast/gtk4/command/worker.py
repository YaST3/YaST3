"""Worker object that executes a command in a background thread."""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable

from mast.core.i18n import _


class CommandWorker(threading.Thread):
    """Run a command in a worker thread and stream output."""

    def __init__(
        self,
        command: list[str],
        on_output: Callable[[str], None],
        on_finished: Callable[[int, str, str], None],
    ):
        super().__init__(daemon=True)
        self.command = command
        self.on_output = on_output
        self.on_finished = on_finished

    def run(self) -> None:
        self.on_output("$ " + " ".join(self.command))

        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            self.on_finished(-1, str(e), "")
            return

        lines: list[str] = []
        if process.stdout is not None:
            for raw_line in process.stdout:
                line = raw_line.rstrip()
                if line:
                    lines.append(line)
                    self.on_output(line)

        return_code = process.wait()
        stdout = "\n".join(lines).strip() if lines else ""
        if return_code == 0:
            self.on_finished(return_code, "", stdout)
            return

        error = "\n".join(lines[-20:]).strip() or _("Unknown error")
        self.on_finished(return_code, error, stdout)
