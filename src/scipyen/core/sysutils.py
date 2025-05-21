# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""System and platform utilities
"""
import os, sys, subprocess, shutil, platform, pathlib, typing
from shutil import which
from core.prog import print_styled
# from core.desktoputils import (get_wm, get_desktop, get_dbus_service_names, 
#                                is_kde_x11, is_kde_wayland, is_kde)

# from qtpy.QtCore import (Signal, Slot, Property,)

def adapt_ui_path(module_path, uifile):
    return os.path.join(module_path, uifile)

def getUnbuiltVersion(path:pathlib.Path):
    proc = subprocess.run([sys.executable, "-m", "setuptools_scm"], capture_output=True, cwd=path.as_posix())
    if proc.returncode == 0:
        return proc.stdout.decode().replace("\n", "")

def checkGitRepo(path:pathlib.Path, label:str = "Scipyen") -> bool:
    gitTest = subprocess.run(["git", "-C", path.as_posix(), "status", "--short", "--branch"], capture_output=True)

    if gitTest.returncode == 0:
        result = gitTest.stdout.decode().split("\n")
        brComp = result[0]
        head, branches = brComp.split("## ")
        local, remote = branches.split("...")
        local = print_styled(local, color="green")
        remote = print_styled(remote, color="red")
        msg = f"{print_styled('WARNING:', color='yellow')} Running {local} branch of the local {label} git repository in {print_styled(path.as_posix(), color='blue')}, with status:"
        result[0] = "## "+local+"..."+remote
        if len(result) > 1:
            for k in range(1,len(result)):
                s = result[k]
                head = print_styled(s[:2], color="red")
                fileName = s[2:]
                result[k] = head+fileName

        result.insert(0, msg)
        print("\n".join(result))
        return True
    
    return False
    
