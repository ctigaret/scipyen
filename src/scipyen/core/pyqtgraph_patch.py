# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
import os
__has_PySide6__=False
if os.environ["QT_API"] == "pyside6":
    import PySide6
    from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
    from PySide6.QtCore import Signal, Slot
    from PySide6.QtUiTools import loadUiType as __loadUiType__
    import qtpy
    qtpy.API = os.environ["QT_API"]
    os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"
    os.environ["FORCE_QT_API"] = "1"
    __has_PySide6__=True
elif os.environ["QT_API"] == "pyqt6":
    import qtpy
    qtpy.API = os.environ["QT_API"]
    os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"
    os.environ["FORCE_QT_API"] = "1"
    from qtpy import QtCore, QtGui, QtWidgets, QtSvg
    from qtpy.QtCore import Signal, Slot
    from qtpy.uic import loadUiType as __loadUiType__
else:
    import qtpy
    qtpy.API = os.environ["QT_API"]
    from qtpy import QtCore, QtGui, QtWidgets, QtSvg
    from qtpy.QtCore import Signal, Slot
    from qtpy.uic import loadUiType as __loadUiType__

import pyqtgraph

pyqtgraph.setConfigOptions(background="w", foreground="k", editorCommand="kate")
from core import pyqtgraph_symbols # to register custom symbols



