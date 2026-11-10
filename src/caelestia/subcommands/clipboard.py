import subprocess
from argparse import Namespace
from pathlib import Path

LUNAR_SHELL_PATH = Path.home() / "work-linux/projects/arch/shell/lunar-shell"


class Command:
    args: Namespace

    def __init__(self, args: Namespace) -> None:
        self.args = args

    def run(self) -> None:
        if self.args.delete:
            subprocess.run(["qs", "-p", str(LUNAR_SHELL_PATH), "ipc", "call", "clipboard", "clear"])
        else:
            subprocess.run(["qs", "-p", str(LUNAR_SHELL_PATH), "ipc", "call", "clipboard", "toggle"])
