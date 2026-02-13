# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r""" Editing dataclasses fields - options to explore:
1) use a Tree widget DONE: see DataTreeViewer, DataTreeView, DataTreeModel

2) QDataWidgetMapper
• would require a custom item model based on the dataclass field and field types
(CAUTION with descriptor types, here)
• for specific python data types would also need custom widgets (see above)
"""
import sys, os, typing
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


from core.prog import safewrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

import math, datetime
import numpy as np
import quantities as pq
from core import scipyen_quantities as scq
from core import strutils
from core import datatypes as dt
import pandas as pd

# from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget
# from gui.textviewer import TextViewer


class DataClassWidget(QtWidgets.QWidget):
    # TODO: 2024-12-11 09:46:03 work in progress
    def __init__(self, dataparent=None):
        super().__init__(parent=parent)
