# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
import typing, pathlib, functools, os, itertools, sys, traceback
from functools import singledispatch, singledispatchmethod
from urllib.parse import urlparse, urlsplit
from collections import namedtuple, deque
from dataclasses import MISSING
from enum import Enum, IntEnum

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg)
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__  = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    # QtType = typing.TypeVar("QtType", bound = "Shiboken.Object")
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
    QKeyboardModifiers = QtCore.Qt.KeyboardModifiers
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
    from qtpy import sip
    ____has_sip____ = True
    # QtType = typing.TypeVar("QtType", bound = "sip.wrappertype")
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    QKeyboardModifiers = QtCore.Qt.KeyboardModifier

__has_qtdbus__ = False
try:
    from qtpy import QtDBus

    __has_qtdbus__ = True
except:
    pass

from traitlets.utils.bunch import Bunch

from core import desktoputils as dutils
from core import qtutils

from core.prog import (safewrapper, print_styled)
from gui import guiutils
from iolib import pictio
# from iolib.navigation import navigator

class DynamicMenuButton(QtWidgets.QPushButton):
    def __init__(self, icon:typing.Optional[QtGui.QIcon]=None, text:typing.Optional[str],
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(icon=icon, text=text, parent=parent)
        
    def setMenu(self, menu:QtWidgets.QMenu):
        super().setMenu(None)
        
    def showMenu(self, func:typing.Callable):
        func()
        
class DynamicToolButton(QtWidgets.QToolButton):
    def __init__(self, icon:typing.Optional[QtGui.QIcon]=None, text:typing.Optional[str],
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(icon=icon, text=text, parent=parent)
        
    def setMenu(self, menu:QtWidgets.QMenu):
        super().setMenu(None)
        
    def showMenu(self, func:typing.Callable):
        func()
        
        
