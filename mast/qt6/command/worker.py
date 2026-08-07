"""Worker object that executes a command in a background thread."""

from __future__ import annotations

import subprocess

from PySide6.QtCore import QObject, Signal

from mast.core.i18n import _


class CommandWorker(QObject):
    """Run a command in a worker thread and stream output."""

    output = Signal(str)
    finished = Signal(int, str, str)

    def __init__(self, command: list[str]):
        super().__init__()
        self.command = command

    def run(self) -> None:
        self.output.emit("$ " + " ".join(self.command))

        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            self.finished.emit(-1, str(e), "")
            return

        lines: list[str] = []
        if process.stdout is not None:
            for raw_line in process.stdout:
                line = raw_line.rstrip()
                if line:
                    lines.append(line)
                    self.output.emit(line)

        return_code = process.wait()
        stdout = "\n".join(lines).strip() if lines else ""
        if return_code == 0:
            self.finished.emit(return_code, "", stdout)
            return

        error = "\n".join(lines[-20:]).strip() or _("Unknown error")
        self.finished.emit(return_code, error, stdout)
