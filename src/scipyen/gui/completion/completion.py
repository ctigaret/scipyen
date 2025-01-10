# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: Python version: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-FileCopyrightText: Original KDE C++ KCompletion Framework authors https://invent.kde.org/frameworks/kcompletion
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing
from qtpy import QtCore, QtGui, QtWidgets, QtSvg, QtNetwork, sip
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class _CompletionBase_(QtCore.QObject):
    def __init__:pass
