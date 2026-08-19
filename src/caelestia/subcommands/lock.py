import os
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import List

from caelestia.utils.io import log, warn
from caelestia.utils.paths import c_state_dir
from caelestia.utils.theme_engine import get_current_theme_state, save_theme_state, set_theme_hyprlock_config
from caelestia.subcommands.shell import _qs_config_args

VALID_BACKENDS = ["caelestia", "qylock", "custom-qylock", "hyprlock"]


def get_qylock_themes() -> List[str]:
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


def get_hyprlock_configs() -> List[str]:
    state = get_current_theme_state()
    if not state.get("path"):
        return []
    theme_dir = Path(state["path"])
    hypr_dir = theme_dir / "hyprlock"
    if hypr_dir.exists() and hypr_dir.is_dir():
        return sorted([
            p.name for p in hypr_dir.iterdir()
            if p.is_file() and p.name.endswith(".conf")
        ])
    return []


class Command:
    args: Namespace

    def __init__(self, args: Namespace) -> None:
        self.args = args

    def run(self) -> None:
        if getattr(self.args, "render_preview", False):
            self._render_single_preview()
            return

        if getattr(self.args, "generate_previews", False):
            backend = getattr(self.args, "preview_backend", None)
            if not backend:
                self._generate_hyprlock_previews()
                self._generate_custom_qylock_previews()
            elif backend == "hyprlock":
                self._generate_hyprlock_previews()
            elif backend == "custom-qylock":
                self._generate_custom_qylock_previews()
            return

        if getattr(self.args, "picker", False):
            try:
                subprocess.run([*_qs_config_args(), "ipc", "call", "lock", "openPicker"], check=False)
                log("Opened instant lock screen picker")
            except Exception as e:
                warn(f"Failed to open lock screen picker: {e}")
            return

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

        if getattr(self.args, "list_hyprlock_configs", False):
            state = get_current_theme_state()
            curr = state.get("hyprlockConfig", "")
            configs = get_hyprlock_configs()
            for c in configs:
                active = " *" if c == curr else ""
                print(f"- {c}{active}")
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

        if hypr_cfg := getattr(self.args, "hyprlock_config", None) or getattr(self.args, "set_hyprlock_config", None):
            set_theme_hyprlock_config(hypr_cfg)
            state = get_current_theme_state()

        if state_changed:
            save_theme_state(state)

        if lock_wp := getattr(self.args, "set_lock_wallpaper", None):
            from caelestia.utils.theme_engine import set_theme_lock_wallpaper
            set_theme_lock_wallpaper(lock_wp)
            if not getattr(self.args, "lock_now", False) and not getattr(self.args, "backend", None) and not getattr(self.args, "theme", None) and not getattr(self.args, "hyprlock_config", None):
                return

        # If --set-* flags were used without requesting lock, don't lock
        if getattr(self.args, "set_backend", None) or getattr(self.args, "set_theme", None) or getattr(self.args, "set_hyprlock_config", None):
            if not getattr(self.args, "lock_now", False) and not getattr(self.args, "backend", None) and not getattr(self.args, "theme", None) and not getattr(self.args, "hyprlock_config", None):
                backend_str = state.get("lockBackend", "caelestia")
                theme_str = state.get("qylockTheme", "none")
                hypr_str = state.get("hyprlockConfig", "none")
                log(f"Lock configuration updated: backend={backend_str}, qylockTheme={theme_str}, hyprlockConfig={hypr_str}")
                return

        # Perform lock action
        current_backend = state.get("lockBackend", "caelestia")
        if current_backend == "hyprlock":
            self.launch_hyprlock(state)
        else:
            try:
                subprocess.run([*_qs_config_args(), "ipc", "call", "lock", "lock"], check=False)
            except Exception as e:
                warn(f"Failed to trigger shell lock IPC: {e}")

    def launch_hyprlock(self, state: dict) -> None:
        theme_dir = Path(state.get("path", ""))
        hypr_dir = theme_dir / "hyprlock"
        hypr_cfg_name = state.get("hyprlockConfig") or "lock_screen1.conf"
        target_conf = hypr_dir / hypr_cfg_name

        if not target_conf.exists() and hypr_dir.exists():
            confs = [p for p in hypr_dir.iterdir() if p.name.endswith(".conf")]
            if confs:
                target_conf = confs[0]

        # Resolve lock wallpaper
        lock_bg = ""
        override_file = c_state_dir / "lock_override_bg"
        if override_file.exists():
            lock_bg = override_file.read_text().strip()
        if not lock_bg or not Path(lock_bg).exists():
            sel_wall = state.get("selectedLockWallpaper") or state.get("selectedWallpaper")
            if sel_wall and (theme_dir / sel_wall).exists():
                lock_bg = str(theme_dir / sel_wall)
        if not lock_bg or not Path(lock_bg).exists():
            from caelestia.utils.paths import wallpaper_path_path
            if wallpaper_path_path.exists():
                lock_bg = wallpaper_path_path.read_text().strip()

        # Resolve pfp
        lock_pfp = ""
        pfp_file = c_state_dir / "pfp.jpg"
        if pfp_file.exists():
            lock_pfp = str(pfp_file.resolve())
        else:
            face_file = Path.home() / ".face"
            if face_file.exists():
                lock_pfp = str(face_file.resolve())

        user_name = os.environ.get("USER", "user")

        if target_conf.exists():
            # Generate runtime hyprlock launcher config
            runtime_conf = c_state_dir / "hyprlock.conf"
            content = [
                "# Auto-generated by Caelestia",
                f'$LOCK_BG = {lock_bg}',
                f'$LOCK_PFP = {lock_pfp}',
                "",
                f'source = {target_conf}',
                ""
            ]
            c_state_dir.mkdir(parents=True, exist_ok=True)
            runtime_conf.write_text("\n".join(content))

            try:
                subprocess.Popen(["hyprlock", "-c", str(runtime_conf)])
                log(f"Launched hyprlock with theme config: {target_conf.name}")
            except Exception as e:
                warn(f"Failed to execute hyprlock: {e}")
        else:
            try:
                subprocess.Popen(["hyprlock"])
            except Exception as e:
                warn(f"Failed to execute hyprlock: {e}")

    def _get_wallpaper_list(self) -> List[Path]:
        state = get_current_theme_state()
        walls: List[Path] = []
        if theme_path := state.get("path"):
            walls_dir = Path(theme_path) / "wallpapers"
            if walls_dir.exists() and walls_dir.is_dir():
                walls.extend([p for p in sorted(walls_dir.rglob("*")) if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm"]])
        if not walls:
            def_dir = Path.home() / ".local/share/caelestia/wallpapers"
            if def_dir.exists():
                walls.extend([p for p in sorted(def_dir.rglob("*")) if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm"]])
        return walls or [Path.home() / ".local/state/caelestia/wallpaper/current"]

    def _get_pfp_list(self) -> List[Path]:
        state = get_current_theme_state()
        pfps: List[Path] = []
        if theme_path := state.get("path"):
            pfp_dir = Path(theme_path) / "pfp"
            if pfp_dir.exists() and pfp_dir.is_dir():
                pfps.extend([p for p in sorted(pfp_dir.glob("*")) if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]])
        if not pfps:
            face = Path.home() / ".face"
            if face.exists():
                pfps.append(face)
        return pfps or [c_state_dir / "pfp.jpg"]

    def _render_single_preview(self) -> None:
        from caelestia.utils.preview import capture_hyprlock, capture_custom_qylock, add_manifest_entry, preview_cache_key, get_file_identity
        backend = getattr(self.args, "preview_backend", None)
        out_path = getattr(self.args, "preview_output", None)
        if not backend or not out_path:
            warn("Both --preview-backend and --preview-output are required for --render-preview")
            return

        output = Path(out_path)
        wall = Path(getattr(self.args, "preview_wallpaper", "") or "")

        if backend == "hyprlock":
            configs = get_hyprlock_configs()
            if not configs:
                warn("No hyprlock configs available for current theme")
                return
            pfp = Path(getattr(self.args, "preview_pfp", "") or "")
            state = get_current_theme_state()
            theme_dir = Path(state.get("path", ""))
            cfg_path = theme_dir / "hyprlock" / configs[0]
            if capture_hyprlock(wall, pfp, cfg_path, output):
                key = preview_cache_key(get_file_identity(wall), get_file_identity(pfp), configs[0])
                add_manifest_entry("hyprlock", key, {
                    "wallpaper": str(wall),
                    "pfp": str(pfp),
                    "config": configs[0],
                }, output.name)
                log(f"Rendered hyprlock preview: {output.name}")
            else:
                warn(f"Failed to render hyprlock preview: {output.name}")
        elif backend == "custom-qylock":
            theme = getattr(self.args, "preview_theme", "") or "nier-automata"
            if capture_custom_qylock(theme, wall, output):
                key = preview_cache_key(get_file_identity(wall), theme)
                add_manifest_entry("custom-qylock", key, {
                    "wallpaper": str(wall),
                    "theme": theme,
                }, output.name)
                log(f"Rendered custom-qylock preview: {output.name}")
            else:
                warn(f"Failed to render custom-qylock preview: {output.name}")

    def _generate_hyprlock_previews(self) -> None:
        from caelestia.utils.preview import (
            capture_hyprlock, hyprlock_cache_path, is_cache_valid,
            preview_cache_key, get_file_identity, add_manifest_entry
        )
        configs = get_hyprlock_configs()
        if not configs:
            warn("No hyprlock configs available for current theme. Skipping hyprlock preview generation.")
            return

        wallpapers = self._get_wallpaper_list()
        pfps = self._get_pfp_list()
        state = get_current_theme_state()
        theme_dir = Path(state.get("path", ""))

        total = len(wallpapers) * len(pfps) * len(configs)
        log(f"Generating hyprlock previews ({total} combinations)...")
        generated, skipped = 0, 0

        for wall in wallpapers:
            for pfp in pfps:
                for cfg in configs:
                    cache_path = hyprlock_cache_path(wall, pfp, cfg)
                    key = preview_cache_key(get_file_identity(wall), get_file_identity(pfp), cfg)
                    if is_cache_valid(cache_path):
                        skipped += 1
                        continue
                    log(f"Generating hyprlock preview: {wall.name} x {pfp.name} x {cfg}")
                    cfg_path = theme_dir / "hyprlock" / cfg
                    if capture_hyprlock(wall, pfp, cfg_path, cache_path):
                        add_manifest_entry("hyprlock", key, {
                            "wallpaper": str(wall),
                            "pfp": str(pfp),
                            "config": cfg,
                        }, cache_path.name)
                        generated += 1
                    else:
                        warn(f"Failed hyprlock capture for {wall.name}")

        log(f":: Hyprlock previews: {generated} generated, {skipped} cached ({total} total)")

    def _generate_custom_qylock_previews(self) -> None:
        from caelestia.utils.preview import (
            capture_custom_qylock, custom_qylock_cache_path, is_cache_valid,
            preview_cache_key, get_file_identity, add_manifest_entry
        )
        wallpapers = self._get_wallpaper_list()
        themes = get_qylock_themes()

        total = len(wallpapers) * len(themes)
        log(f"Generating custom qylock previews ({total} combinations)...")
        generated, skipped = 0, 0

        for wall in wallpapers:
            for theme in themes:
                cache_path = custom_qylock_cache_path(wall, theme)
                key = preview_cache_key(get_file_identity(wall), theme)
                if is_cache_valid(cache_path):
                    skipped += 1
                    continue
                log(f"Generating custom qylock preview: {wall.name} x {theme}")
                if capture_custom_qylock(theme, wall, cache_path):
                    add_manifest_entry("custom-qylock", key, {
                        "wallpaper": str(wall),
                        "theme": theme,
                    }, cache_path.name)
                    generated += 1
                else:
                    warn(f"Failed custom qylock capture for {wall.name} x {theme}")

        log(f":: Custom Qylock previews: {generated} generated, {skipped} cached ({total} total)")
