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

    bg_hex = f"#{bg}" if not bg.startswith("#") else bg
    fg_hex = f"#{fg}" if not fg.startswith("#") else fg
    cursor_hex = f"#{cursor}" if not cursor.startswith("#") else cursor

    colors_dict = {
        "color0": bg_hex,
        "color1": f"#{colours.get('term1', 'ff0000')}".replace("##", "#"),
        "color2": f"#{colours.get('term2', '00ff00')}".replace("##", "#"),
        "color3": f"#{colours.get('term3', 'ffff00')}".replace("##", "#"),
        "color4": f"#{colours.get('term4', '0000ff')}".replace("##", "#"),
        "color5": f"#{colours.get('term5', 'ff00ff')}".replace("##", "#"),
        "color6": f"#{colours.get('term6', '00ffff')}".replace("##", "#"),
        "color7": fg_hex,
        "color8": f"#{colours.get('term0', '343434')}".replace("##", "#"),
        "color9": f"#{colours.get('term9', 'ff5555')}".replace("##", "#"),
        "color10": f"#{colours.get('term10', '55ff55')}".replace("##", "#"),
        "color11": f"#{colours.get('term11', 'ffff55')}".replace("##", "#"),
        "color12": f"#{colours.get('term12', '5555ff')}".replace("##", "#"),
        "color13": f"#{colours.get('term13', 'ff55ff')}".replace("##", "#"),
        "color14": f"#{colours.get('term14', '55ffff')}".replace("##", "#"),
        "color15": fg_hex,
    }

    return {
        "wallpaper": wallpaper_path,
        "alpha": "100",
        "special": {
            "background": bg_hex,
            "foreground": fg_hex,
            "cursor": cursor_hex,
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
