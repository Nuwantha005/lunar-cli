import os
import json
import hashlib
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone

PREVIEW_CACHE_DIR = Path(
    os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
) / "caelestia" / "previews"

# Settle delays for headless labwc rendering (in seconds)
# You can adjust these delays if a backend needs more/less time to load visuals before screenshotting
HYPRLOCK_SETTLE_DELAY = 1.8
CUSTOM_QYLOCK_SETTLE_DELAY = 2.5


def preview_cache_key(*components: str) -> str:
    """SHA-256 hash of concatenated key components."""
    return hashlib.sha256(":".join(components).encode()).hexdigest()


def get_file_identity(path: Path) -> str:
    """Return 'path:mtime_ns' for cache key input."""
    resolved = path.resolve()
    if not resolved.exists():
        return str(resolved)
    return f"{resolved}:{resolved.stat().st_mtime_ns}"


def is_cache_valid(cache_path: Path) -> bool:
    """Check if a cached preview file exists and is non-empty."""
    return cache_path.exists() and cache_path.stat().st_size > 0


# --- Manifest Storage ---

def load_manifest(backend: str) -> dict:
    manifest_path = PREVIEW_CACHE_DIR / backend / "manifest.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text())
        except Exception:
            pass
    return {"version": 1, "entries": {}}


def save_manifest(backend: str, manifest: dict) -> None:
    manifest_path = PREVIEW_CACHE_DIR / backend / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))


def add_manifest_entry(backend: str, key: str, metadata: dict, filename: str) -> None:
    manifest = load_manifest(backend)
    manifest["entries"][key] = {
        **metadata,
        "file": filename,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_manifest(backend, manifest)


# --- Labwc Headless Infrastructure ---

def capture_with_labwc(
    exec_cmd: str,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
    settle_delay: float = 2.0,
) -> bool:
    """
    Launches headless Labwc compositor, sets resolution via wlr-randr,
    runs target command, captures with grim, and cleans up.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    runner_script = (
        f"wlr-randr --output HEADLESS-1 --custom-mode {width}x{height}\n"
        f"{exec_cmd} &\n"
        f"APP_PID=$!\n"
        f"sleep {settle_delay}\n"
        f"grim '{output_path}'\n"
        f"kill $APP_PID 2>/dev/null\n"
        f"killall -TERM labwc 2>/dev/null\n"
    )

    env = {**os.environ, "WLR_BACKENDS": "headless", "WLR_HEADLESS_OUTPUTS": "1"}
    env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)

    try:
        subprocess.run(
            ["labwc", "-s", f"bash -c \"{runner_script}\""],
            env=env,
            capture_output=True,
            timeout=settle_delay + 12,
        )
        return is_cache_valid(output_path)
    except Exception as e:
        print(f"Warning: Labwc capture failed for {output_path.name}: {e}")
        return False


# --- Hyprlock Capture ---

def capture_hyprlock(wallpaper: Path, pfp: Path, config_path: Path, output: Path) -> bool:
    """Capture hyprlock preview via headless Labwc."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(f"$LOCK_BG = {wallpaper}\n")
        f.write(f"$LOCK_PFP = {pfp}\n\n")
        if config_path.exists():
            f.write(f"source = {config_path}\n\n")
        f.write("general {\n    no_fade_in = true\n    grace = 0\n    disable_loading_bar = true\n}\n")
        hyprlock_conf = f.name

    try:
        return capture_with_labwc(
            exec_cmd=f"hyprlock -c '{hyprlock_conf}'",
            output_path=output,
            settle_delay=HYPRLOCK_SETTLE_DELAY,
        )
    finally:
        try:
            os.unlink(hyprlock_conf)
        except OSError:
            pass


def hyprlock_cache_path(wallpaper: Path, pfp: Path, config_id: str) -> Path:
    key = preview_cache_key(get_file_identity(wallpaper), get_file_identity(pfp), config_id)
    return PREVIEW_CACHE_DIR / "hyprlock" / f"{key}.png"


# --- Custom Qylock Capture ---

def capture_custom_qylock(theme_name: str, wallpaper: Path, output: Path) -> bool:
    """Capture Qylock theme with custom wallpaper via headless Labwc."""
    lock_dir = Path.home() / "work-linux/projects/arch/shell/lunar-lock"
    lock_bin = lock_dir / "quickshell-lockscreen/lock.sh"

    if not lock_bin.exists():
        lock_bin = Path.home() / ".config/qylock/lock.sh"

    exec_cmd = (
        f"export QS_THEME='{theme_name}'; "
        f"export QYLOCK_THEME='{theme_name}'; "
        f"export QYLOCK_OVERRIDE_BG='{wallpaper}'; "
        f"bash '{lock_bin}' '{theme_name}'"
    )

    return capture_with_labwc(
        exec_cmd=exec_cmd,
        output_path=output,
        settle_delay=CUSTOM_QYLOCK_SETTLE_DELAY,
    )


def custom_qylock_cache_path(wallpaper: Path, theme_name: str) -> Path:
    key = preview_cache_key(get_file_identity(wallpaper), theme_name)
    return PREVIEW_CACHE_DIR / "custom-qylock" / f"{key}.png"
