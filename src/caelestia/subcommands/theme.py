import json
from argparse import Namespace

from caelestia.utils.theme_engine import (
    get_current_theme_state,
    list_themes,
    set_random_theme_wallpaper,
    set_theme,
    set_theme_pfp,
    set_theme_wallpaper,
)


class Command:
    args: Namespace

    def __init__(self, args: Namespace) -> None:
        self.args = args

    def run(self) -> None:
        subcommand = getattr(self.args, "theme_command", None)

        if subcommand == "set":
            set_theme(self.args.name)
        elif subcommand == "get":
            state = get_current_theme_state()
            if self.args.json:
                print(json.dumps(state, indent=2))
            else:
                print(state.get("name", "No active theme"))
        elif subcommand == "list":
            themes = list_themes()
            if self.args.json:
                print(json.dumps(themes, indent=2))
            else:
                current = get_current_theme_state().get("name", "")
                for t in themes:
                    active = " *" if t["name"] == current else ""
                    print(f"- {t['name']}{active}")
        elif subcommand == "wallpaper":
            wp_sub = getattr(self.args, "wp_command", None)
            if wp_sub == "set":
                set_theme_wallpaper(self.args.path)
            elif wp_sub == "random":
                set_random_theme_wallpaper()
        elif subcommand == "pfp":
            pfp_sub = getattr(self.args, "pfp_command", None)
            if pfp_sub == "set":
                set_theme_pfp(self.args.path)
