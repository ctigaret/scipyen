# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
import sys, os # noqa
import pathlib, urllib # noqa
import typing, warnings # noqa
import subprocess, traceback, json # noqa
import shutil
import platform


def get_my_desktop_session():
    env = dict(
        (k, v)
        for k, v in os.environ.items()
        if any(s in k.lower() for s in ("desktop", "session", "xdg"))
    )
    if len(env) == 0:
        return

    xdg_session_desktop = env.get("XDG_SESSION_DESKTOP", "")
    return xdg_session_desktop

def get_desktop(what: str = "desktop"):
    r"""Somewhat redundant to get_wm()"""
    if sys.platform.startswith("linux"):
        if what == "wm":
            return os.environ.get("WINDOWMANAGER", None)

        elif what == "session":
            return os.environ.get("XDG_SESSION_TYPE", None)

        else:
            return os.environ.get(
                "XDG_CURRENT_DESKTOP", os.environ.get("XDG_SESSION_DESKTOP", None)
            )

    else:
        return sys.platform

def get_wm():
    r"""Retrieves the name of the window manager, on Linux platforms.
    On any other platforms returns None.
    Somewhat redundant to get_desktop()
    """
    # NOTE: 2023-01-07 16:08:36
    # From
    # https://stackoverflow.com/questions/3333243/how-can-i-check-with-python-which-window-manager-is-running
    if not sys.platform.startswith("linux"):
        return

    wmctrl = shutil.which("wmctrl")

    if len(wmctrl):
        wmctrl = os.path.basename(wmctrl)

        out = subprocess.run(
            [wmctrl, "-m"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if len(out.stdout) == 0:
            print(out.stderr)
            return

        wmname = [s for s in out.stdout.split("\n") if s.startswith("Name: ")]

        if len(wmname):
            return wmname[0].strip("Name: ")

    else:
        inxi = shutil.which("inxi")
        if len(inxi):
            inxi = os.path.basename(inxi)
            out = subprocess.run(
                [inxi, "-Sxx", "-y", "1", "--indents", "0"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if len(out.stdout) == 0:
                print(out.stderr)
                return

            inxiout = dict(
                filter(
                    lambda x: len(x) == 2,
                    (tuple(s.split(": ")) for s in out.stdout.split("\n")),
                )
            )

            if len(inxiout) == 0:
                return

            # desktop = inxiout.get("Desktop", None)
            # tk = inxiout.get("tk", None)
            wm = inxiout.get("wm", None)

            return wm

def is_x11() -> bool:
    return get_desktop("session").lower() == "x11"

def is_kde_x11() -> bool:
    if platform.system() != "Linux":
        return False

    return get_desktop("session").lower() == "x11" and get_desktop() == "KDE"

def is_gnome_x11() -> bool:
    if platform.system() != "Linux":
        return False

    return get_desktop("session").lower() == "x11" and get_desktop() == "GNOME"


def is_kde_wayland() -> bool:
    if platform.system() != "Linux":
        return False

    return get_desktop("session").lower() == "wayland" and get_desktop() == "KDE"

def is_gnome_wayland() -> bool:
    if platform.system() != "Linux":
        return False

    return get_desktop("session").lower() == "wayland" and get_desktop() == "GNOME"

def is_wayland() -> bool:
    return get_desktop("session").lower() == "wayland"

def is_kde() -> bool:
    if platform.system() != "Linux":
        return False

    return (
        get_desktop("session").lower() in ("x11", "wayland") and get_desktop() == "KDE"
    )

def is_gnome() -> bool:
    if platform.system() != "Linux":
        return False

    return (
        get_desktop("session").lower() in ("x11", "wayland") and get_desktop() == "GNOME"
    )
