import subprocess


def notify(*args: str, urgency: str = "low") -> str:
    cmd = ["notify-send", "-a", "caelestia-cli", "-u", urgency, *args]
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ""


def close_notification(id: str) -> None:
    subprocess.run(
        [
            "gdbus",
            "call",
            "--session",
            "--dest=org.freedesktop.Notifications",
            "--object-path=/org/freedesktop/Notifications",
            "--method=org.freedesktop.Notifications.CloseNotification",
            id,
        ],
        stdout=subprocess.DEVNULL,
    )
