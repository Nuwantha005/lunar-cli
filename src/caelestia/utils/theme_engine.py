import json
import os
import random
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from caelestia.utils.io import log
from caelestia.utils.paths import c_state_dir, pictures_dir
from caelestia.utils.wallpaper import set_wallpaper

THEMES_DIR = pictures_dir / "themes"
THEME_STATE_FILE = c_state_dir / "theme.json"
PFP_STATE_FILE = c_state_dir / "pfp.jpg"


def get_themes_dir() -> Path:
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    return THEMES_DIR


def get_current_theme_state() -> Dict[str, Any]:
    if not THEME_STATE_FILE.exists():
        return {}
    try:
        with open(THEME_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error reading theme state: {e}")
        return {}


def save_theme_state(data: Dict[str, Any]) -> None:
    c_state_dir.mkdir(parents=True, exist_ok=True)
    with open(THEME_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_themes() -> List[Dict[str, Any]]:
    themes_dir = get_themes_dir()
    themes: List[Dict[str, Any]] = []

    if not themes_dir.exists():
        return themes

    for entry in sorted(themes_dir.iterdir()):
        if entry.is_dir():
            theme_json = entry / "theme.json"
            theme_info = {
                "name": entry.name,
                "path": str(entry),
                "wallpaper": None,
                "pfp": None,
                "schemeMode": "dark",
                "schemeVariant": "tonalspot",
            }
            if theme_json.exists():
                try:
                    with open(theme_json, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        theme_info.update(meta)
                except Exception:
                    pass

            # Resolve active wallpaper preview for this theme
            wallpapers_dir = entry / "wallpapers"
            if not wallpapers_dir.exists():
                wallpapers_dir = entry / "wallpaper"  # backwards compatibility

            selected_wall = theme_info.get("selectedWallpaper")
            if selected_wall and (entry / selected_wall).exists():
                theme_info["wallpaper"] = str(entry / selected_wall)
            elif selected_wall:
                # Try stem fallback (e.g. .jpg vs .png mismatch)
                target_path = entry / selected_wall
                if target_path.parent.exists():
                    matched = next(
                        (p for p in target_path.parent.iterdir()
                         if p.stem == target_path.stem and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]),
                        None
                    )
                    if matched:
                        theme_info["wallpaper"] = str(matched)

            if not theme_info.get("wallpaper") and wallpapers_dir.exists():
                walls = sorted([
                    p for p in wallpapers_dir.iterdir()
                    if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
                ])
                if walls:
                    theme_info["wallpaper"] = str(walls[0])

            # Resolve active lock wallpaper preview for this theme
            selected_lock_wall = theme_info.get("selectedLockWallpaper")
            if selected_lock_wall and (entry / selected_lock_wall).exists():
                theme_info["lockWallpaper"] = str(entry / selected_lock_wall)
            else:
                theme_info["lockWallpaper"] = theme_info.get("wallpaper")

            # Resolve pfp preview for this theme
            pfp_dir = entry / "pfp"
            selected_pfp = theme_info.get("selectedPfp")
            if selected_pfp and (entry / selected_pfp).exists():
                theme_info["pfp"] = str(entry / selected_pfp)
            elif selected_pfp:
                target_path = entry / selected_pfp
                if target_path.parent.exists():
                    matched = next(
                        (p for p in target_path.parent.iterdir()
                         if p.stem == target_path.stem and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]),
                        None
                    )
                    if matched:
                        theme_info["pfp"] = str(matched)

            if not theme_info.get("pfp") and pfp_dir.exists():
                pfps = sorted([
                    p for p in pfp_dir.iterdir()
                    if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
                ])
                if pfps:
                    theme_info["pfp"] = str(pfps[0])

            themes.append(theme_info)

    return themes


def get_theme_info(name: str) -> Optional[Dict[str, Any]]:
    for t in list_themes():
        if t["name"].lower() == name.lower():
            return t
    return None


def set_theme(name: str) -> bool:
    info = get_theme_info(name)
    if not info:
        log(f"Theme '{name}' not found in {THEMES_DIR}")
        return False

    theme_dir = Path(info["path"])
    wallpaper_path = info.get("wallpaper")
    lock_wallpaper_path = info.get("lockWallpaper") or wallpaper_path
    pfp_path = info.get("pfp")

    # 1. Save theme.json state FIRST so set_wallpaper() reads the updated schemeMode & schemeVariant
    state = {
        "name": info["name"],
        "path": str(theme_dir),
        "scheme": info.get("scheme", "dynamic"),
        "schemeFlavour": info.get("schemeFlavour", "default"),
        "schemeMode": info.get("schemeMode", "dark"),
        "schemeVariant": info.get("schemeVariant", "tonalspot"),
        "selectedWallpaper": os.path.relpath(wallpaper_path, theme_dir) if wallpaper_path else None,
        "selectedLockWallpaper": os.path.relpath(lock_wallpaper_path, theme_dir) if lock_wallpaper_path else None,
        "selectedPfp": os.path.relpath(pfp_path, theme_dir) if pfp_path else None,
        "lockBackend": info.get("lockBackend", "caelestia"),
        "qylockTheme": info.get("qylockTheme", None),
    }
    save_theme_state(state)

    # Write lock override bg
    if lock_wallpaper_path and os.path.exists(lock_wallpaper_path):
        from caelestia.utils.paths import lock_override_bg_path
        lock_override_bg_path.parent.mkdir(parents=True, exist_ok=True)
        lock_override_bg_path.write_text(str(lock_wallpaper_path))

    # Update scheme.json immediately so colour pipeline works
    try:
        from caelestia.utils.scheme import get_scheme
        scheme = get_scheme()
        changed = False
        target_scheme = info.get("scheme", "dynamic")
        if scheme.name != target_scheme:
            scheme.name = target_scheme
            changed = True
        target_flavour = info.get("schemeFlavour", "default")
        if scheme.flavour != target_flavour:
            scheme.flavour = target_flavour
            changed = True
        # Note: schemeMode and schemeVariant are applied by set_wallpaper automatically
    except Exception as e:
        log(f"Failed to update scheme: {e}")

    # 2. Resolve & set wallpaper (triggers colour pipeline with updated theme state)
    if wallpaper_path and os.path.exists(wallpaper_path):
        set_wallpaper(Path(wallpaper_path))

    # 3. Resolve & set profile picture (pfp)
    if pfp_path and os.path.exists(pfp_path):
        set_theme_pfp(pfp_path)

    log(f"Switched theme to '{info['name']}'")
    return True


def set_theme_wallpaper(wallpaper_path: str) -> bool:
    wp = Path(wallpaper_path).resolve()
    if not wp.exists():
        log(f"Wallpaper path '{wallpaper_path}' does not exist.")
        return False

    # Apply wallpaper
    set_wallpaper(wp)

    # Update current theme state if wallpaper is inside active theme dir
    state = get_current_theme_state()
    if state.get("path"):
        theme_dir = Path(state["path"])
        try:
            rel = wp.relative_to(theme_dir)
            state["selectedWallpaper"] = str(rel)
            save_theme_state(state)

            # Persist back to theme.json in theme folder as well
            theme_meta_path = theme_dir / "theme.json"
            meta = {}
            if theme_meta_path.exists():
                try:
                    with open(theme_meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass
            meta["selectedWallpaper"] = str(rel)
            with open(theme_meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except ValueError:
            pass  # Wallpaper is outside active theme dir

    return True


def set_theme_lock_wallpaper(wallpaper_path: str) -> bool:
    wp = Path(wallpaper_path).resolve()
    if not wp.exists():
        log(f"Lock wallpaper path '{wallpaper_path}' does not exist.")
        return False

    from caelestia.utils.paths import lock_override_bg_path
    lock_override_bg_path.parent.mkdir(parents=True, exist_ok=True)
    lock_override_bg_path.write_text(str(wp))

    state = get_current_theme_state()
    if state.get("path"):
        theme_dir = Path(state["path"])
        try:
            rel = wp.relative_to(theme_dir)
            state["selectedLockWallpaper"] = str(rel)
            save_theme_state(state)

            theme_meta_path = theme_dir / "theme.json"
            meta = {}
            if theme_meta_path.exists():
                try:
                    with open(theme_meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass
            meta["selectedLockWallpaper"] = str(rel)
            with open(theme_meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except ValueError:
            pass

    log(f"Set lock wallpaper to '{wp}'")
    return True


def set_theme_pfp(pfp_path: str) -> bool:
    pfp = Path(pfp_path).resolve()
    if not pfp.exists():
        log(f"PFP path '{pfp_path}' does not exist.")
        return False

    # Symlink to state pfp.jpg
    if PFP_STATE_FILE.is_symlink() or PFP_STATE_FILE.exists():
        PFP_STATE_FILE.unlink(missing_ok=True)
    
    try:
        PFP_STATE_FILE.symlink_to(pfp)
    except Exception:
        shutil.copy(pfp, PFP_STATE_FILE)

    # Symlink to ~/.face
    face_file = Path.home() / ".face"
    if face_file.is_symlink() or face_file.exists():
        face_file.unlink(missing_ok=True)
    try:
        face_file.symlink_to(pfp)
    except Exception:
        shutil.copy(pfp, face_file)

    state = get_current_theme_state()
    if state.get("path"):
        theme_dir = Path(state["path"])
        try:
            rel = pfp.relative_to(theme_dir)
            state["selectedPfp"] = str(rel)
            save_theme_state(state)

            theme_meta_path = theme_dir / "theme.json"
            meta = {}
            if theme_meta_path.exists():
                try:
                    with open(theme_meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass
            meta["selectedPfp"] = str(rel)
            with open(theme_meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except ValueError:
            pass

    return True


def set_random_theme_wallpaper() -> bool:
    state = get_current_theme_state()
    if not state.get("path"):
        return False
    
    theme_dir = Path(state["path"])
    wallpapers_dir = theme_dir / "wallpapers"
    if not wallpapers_dir.exists():
        wallpapers_dir = theme_dir / "wallpaper"

    if not wallpapers_dir.exists():
        return False

    walls = [
        p for p in wallpapers_dir.iterdir()
        if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
    ]
    if not walls:
        return False

    chosen = random.choice(walls)
    return set_theme_wallpaper(str(chosen))
