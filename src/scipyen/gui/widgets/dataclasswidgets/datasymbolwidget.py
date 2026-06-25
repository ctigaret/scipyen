# -*- coding: utf-8 -*-
# $Id: datasymbolwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


import sys, os, typing, types, warnings, math, cmath # noqa
import numbers # noqa
import numpy as np # noqa
import quantities as pq # noqa
import neo
from tribool import Tribool # noqa

import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
__has_qtdbus__ = False

if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6 # noqa
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip# noqa
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

try:
    from qtpy import QtDBus# noqa
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

from core import datatypes # noqa
# from core import strutils
from core.prog import scipywarn # noqa
from gui import (guiutils, interact) # noqa
from gui.workspacegui import WorkspaceGuiMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_DataSymbolWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "datasymbolwidget.ui")
    )

class DataSymbolWidget(Ui_DataSymbolWidget, QWidget):
    r"""Common small widget showing the symbol binding of an objet when needed.
Use as part of more complex widgets in Scipyen.
"""
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None):
        QWidget.__init__(self, parent=parent)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

    def setValue(self, val:str):
        if not isinstance(val, str):
            val = ""

        self.objectSymbolLabel.setText(val)

    def clear(self):
        self.objectSymbolLabel.setText("")


