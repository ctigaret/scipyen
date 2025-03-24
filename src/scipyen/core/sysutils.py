# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""System and platform utilities
"""
import os, sys, subprocess, shutil, platform, pathlib
from shutil import which
# from core.desktoputils import (get_wm, get_desktop, get_dbus_service_names, 
#                                is_kde_x11, is_kde_wayland, is_kde)

# from qtpy.QtCore import (Signal, Slot, Property,)

def adapt_ui_path(module_path, uifile):
    return os.path.join(module_path, uifile)
