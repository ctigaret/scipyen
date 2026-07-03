# -*- coding: utf-8 -*-
# $Id: drawerwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath # noqa
import numbers
import numpy as np
import quantities as pq
import pandas as pd
import neo
from tribool import Tribool

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
__has_qtdbus__ = False

if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip # noqa
    from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

try:
    from qtpy import QtDBus # noqa
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

from core.prog import scipywarn # noqa
from core import scipyendataclasses as sdc
from core import scipyen_quantities as scq
from gui import guiutils
from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]


class DrawerWidget(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)


    def _configureUI_(self):
        self._toggleButton_ = QtWidgets.QToolButton(self)
        self._toggleButton_.setIcon(guiutils.getIcon("application-menu"))
        self._toggleButton_.setCheckable(True)
        self._toggleButton_.setAutoRaise(True)
        self._toggleButton_.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)

        # self._sizeAnimation_ =
        self._animationGroup_ = QtCore.QParallelAnimationGroup()
