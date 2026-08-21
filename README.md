# lunar-cli

> [!NOTE]
> This repository is a custom fork of [caelestia-dots/cli](https://github.com/caelestia-dots/cli). It serves as the main command-line control and background automation engine for [lunar-shell](https://github.com/Nuwantha005/lunar-shell) and [lunar-lock](https://github.com/Nuwantha005/lunar-lock).

---

## Reasoning for Forking & Modifications

The original `caelestia-cli` was modified to create `lunar-cli` to handle expanded inter-application communication, dynamic color synchronization, and headless rendering:
- **Hot-Swappable Theme Recoloring**: Extended the scheme generation pipeline to instantly recolor applications on scheme changes without needing process restarts.
- **Headless Lock Preview Pipeline**: Implemented a standalone preview generator using `labwc` and `ffmpeg` to pre-render screenshot previews for lock screen themes and video backgrounds.
- **Enhanced Lock IPC**: Expanded `caelestia lock` subcommands to support dynamic lock screen backends (`caelestia`, `qylock`, `custom-qylock`, `hyprlock`), preview rendering, and emergency unlocking.

---

## Features

- **Dynamic Hot-Swappable Recoloring**: Colors update instantly across Kitty terminals, Qt/KDE applications, Firefox (via Pywalfox), and `lunar-shell` components.
  - *Note: GTK applications (such as Thunar) require closing all active instances to apply new colors due to GTK design limitations.*
- **Headless Preview Pipeline**: Subcommands (`caelestia lock --generate-previews` and `caelestia lock --render-preview`) generate accurate lock screen visual previews in a headless environment.
- **Smart Cache Management**: Preview cache directory (`~/.cache/caelestia/previews/`) with SHA-256 mtime hashing to auto-invalidate stale thumbnails when theme assets or wallpapers change.

---

## Technical Details

### Hot-Swappable Recoloring Architecture

`lunar-cli` uses target-specific mechanisms to push color changes live:
- **Qt / KDE Applications**: Generates color definitions (`caelestia.colors` / `caelestia.qss`) and broadcasts the DBus signal `org.kde.KGlobalSettings.notifyChange`, prompting applications like Dolphin to reload colors immediately.
- **Kitty Terminals**: Targets active Kitty Unix sockets (`kitten @ --to=unix:<socket> set-colors ...`) using `~/.local/state/caelestia/kitty-colors.conf`, eliminating terminal flashing and avoiding filesystem watching overhead.
- **Firefox Browser**: Maps Material You palette tokens into `~/.cache/wal/colors.json` and triggers `pywalfox update` via the Pywalfox native messaging bridge.

### Headless Preview Pipeline Mechanics

Location: `lunar-cli/src/caelestia/utils/preview.py`

When generating previews (`capture_with_labwc`):
1. **Compositor Execution**: Spawns `labwc` in a headless environment (`WLR_BACKENDS=headless WLR_HEADLESS_OUTPUTS=1`) configured to a standard resolution (e.g. 1920x1080 via `wlr-randr`).
2. **Settling Delays**: Enforces visual settling delays (1.8s for `hyprlock`, 2.5s for `custom-qylock`) to allow QML animations and shaders to settle.
3. **Screenshot Capture**: Executes `grim` within the headless session to capture the exact rendered state.
4. **Video Frame Extraction**: For video backgrounds (`.mp4`, `.webm`, `.mkv`), `ffmpeg` extracts the frame at timestamp `00:00:01` prior to compositor rendering.

---

## Installation & Setup

> [!WARNING]
> Installation currently requires manual configuration and technical knowledge, as file paths are hardcoded across `lunar-shell`, `lunar-cli`, and `lunar-lock`. A unified installation script is planned as a future target.

---

## Known Issues & Limitations

- **Headless Previews**: Generated previews for native Qylock `.gif` thumbnails rely on original low-resolution GIF assets provided by upstream creators. Future work includes piping live frames directly from the headless compositor to provide high-resolution previews for vanilla Qylock themes.

---

## Gallery

<!-- Add screenshots and videos here -->
