import subprocess
from argparse import Namespace
from pathlib import Path
from typing import List

from caelestia.utils.io import log, warn
from caelestia.utils.theme_engine import get_current_theme_state, save_theme_state
from caelestia.subcommands.shell import _qs_config_args

VALID_BACKENDS = ["caelestia", "qylock", "hyprlock"]

def get_qylock_themes() -> List[str]:
    # Possible paths to qylock themes
    possible_paths = [
        Path.home() / "work-linux/projects/arch/shell/lunar-lock/themes",
        Path.home() / "work-linux/projects/arch/shell/lunar-shell/lock-themes",
        Path.home() / ".config/quickshell/caelestia/lock-themes",
        Path.home() / ".config/caelestia/lock-themes",
    ]
    for p in possible_paths:
        if p.exists() and p.is_dir():
            themes = [
                d.name for d in sorted(p.iterdir())
                if d.is_dir() and not d.name.startswith(".")
            ]
            if themes:
                return themes
    return []


class Command:
    args: Namespace

    def __init__(self, args: Namespace) -> None:
        self.args = args

    def run(self) -> None:
        if getattr(self.args, "list_backends", False):
            state = get_current_theme_state()
            curr = state.get("lockBackend", "caelestia")
            for b in VALID_BACKENDS:
                active = " *" if b == curr else ""
                print(f"- {b}{active}")
            return

        if getattr(self.args, "list_themes", False):
            state = get_current_theme_state()
            curr = state.get("qylockTheme", "")
            themes = get_qylock_themes()
            for t in themes:
                active = " *" if t == curr else ""
                print(f"- {t}{active}")
            return

        state = get_current_theme_state()
        state_changed = False

        if backend := getattr(self.args, "backend", None) or getattr(self.args, "set_backend", None):
            if backend not in VALID_BACKENDS:
                warn(f"Invalid backend '{backend}'. Valid backends: {', '.join(VALID_BACKENDS)}")
                return
            state["lockBackend"] = backend
            state_changed = True

        if theme := getattr(self.args, "theme", None) or getattr(self.args, "set_theme", None):
            available_themes = get_qylock_themes()
            if available_themes and theme not in available_themes:
                warn(f"Unknown qylock theme '{theme}'. Use --list-themes to see available themes.")
            state["qylockTheme"] = theme
            state_changed = True

        if state_changed:
            save_theme_state(state)

        # If --set-backend or --set-theme was used without requesting lock, don't lock
        if getattr(self.args, "set_backend", None) or getattr(self.args, "set_theme", None):
            if not getattr(self.args, "lock_now", False) and not getattr(self.args, "backend", None) and not getattr(self.args, "theme", None):
                backend_str = state.get("lockBackend", "caelestia")
                theme_str = state.get("qylockTheme", "none")
                log(f"Lock configuration updated: backend={backend_str}, qylockTheme={theme_str}")
                return

        # Perform lock action
        current_backend = state.get("lockBackend", "caelestia")
        if current_backend == "hyprlock":
            try:
                subprocess.Popen(["hyprlock"])
            except Exception as e:
                warn(f"Failed to execute hyprlock: {e}")
        else:
            # Use the same qs config path resolution as `caelestia shell`
            # so that qs finds the correct lunar-shell or caelestia config
            try:
                subprocess.run([*_qs_config_args(), "ipc", "call", "lock", "lock"], check=False)
            except Exception as e:
                warn(f"Failed to trigger shell lock IPC: {e}")
