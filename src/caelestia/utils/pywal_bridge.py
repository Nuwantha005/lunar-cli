import json
import subprocess
from pathlib import Path
from typing import Dict

from caelestia.utils.paths import cache_dir, wallpaper_path_path

PYWAL_COLORS_FILE = cache_dir / "wal/colors.json"


def m3_to_pywal_colors(colours: Dict[str, str]) -> Dict:
    wallpaper_path = ""
    if wallpaper_path_path.exists():
        try:
            wallpaper_path = wallpaper_path_path.read_text().strip()
        except Exception:
            pass

    bg = colours.get("surface", colours.get("background", "000000"))
    fg = colours.get("onSurface", colours.get("onBackground", "ffffff"))
    cursor = colours.get("primary", colours.get("secondary", fg))

    colors_dict = {}
    for i in range(16):
        key = f"term{i}"
        val = colours.get(key, "000000")
        colors_dict[f"color{i}"] = f"#{val}" if not val.startswith("#") else val

    return {
        "wallpaper": wallpaper_path,
        "alpha": "100",
        "special": {
            "background": f"#{bg}" if not bg.startswith("#") else bg,
            "foreground": f"#{fg}" if not fg.startswith("#") else fg,
            "cursor": f"#{cursor}" if not cursor.startswith("#") else cursor,
        },
        "colors": colors_dict,
    }


def funnel_to_pywalfox(colours: Dict[str, str]) -> None:
    try:
        data = m3_to_pywal_colors(colours)
        PYWAL_COLORS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PYWAL_COLORS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        subprocess.run(
            ["pywalfox", "update"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass
