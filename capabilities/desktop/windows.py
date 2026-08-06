import os
import subprocess
from pathlib import Path


class WindowsExplorerLauncher:
    def __init__(self, executable: Path | None = None) -> None:
        candidate = executable or Path(
            os.environ.get("SYSTEMROOT", r"C:\Windows"),
            "explorer.exe",
        )
        try:
            resolved_executable = candidate.resolve(strict=True)
        except OSError as error:
            raise ValueError("Windows Explorer executable must exist") from error
        if not resolved_executable.is_file():
            raise ValueError("Windows Explorer executable must be a file")
        self._executable = resolved_executable

    def open(self, path: Path) -> None:
        subprocess.Popen(
            [str(self._executable), str(path)],
            shell=False,
            close_fds=True,
        )
