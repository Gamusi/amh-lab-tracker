"""Launcher package for AMH Lab Tracker."""
from .make_desktop_shortcut import make_desktop_shortcut
from .install_autostart_windows import install_autostart_windows
from .install_autostart_linux import install_autostart_linux

__all__ = [
    "make_desktop_shortcut",
    "install_autostart_windows",
    "install_autostart_linux"
]
