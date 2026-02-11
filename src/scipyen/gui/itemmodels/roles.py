# -*- coding: utf-8 -*-
# $Id: roles.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import os, sys, traceback, types, typing

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

StandaloneEditorWidgetRole = QtCore.Qt.UserRole + 2
ObjectDataAccessRole = QtCore.Qt.UserRole + 20
ObjectDataAccessTypeRole = QtCore.Qt.UserRole + 30
ObjectTypeRole = QtCore.Qt.UserRole + 40
ObjectDataRole = QtCore.Qt.UserRole + 50
ObjectKeyRole = QtCore.Qt.UserRole + 60
ObjectKeyTypeRole = QtCore.Qt.UserRole + 70
DataChoicesRole = QtCore.Qt.UserRole + 80


__all__ = ("StandaloneEditorWidgetRole",
           "ObjectTypeRole", "ObjectDataRole",
           "ObjectKeyRole", "ObjectKeyTypeRole",
           "ObjectDataAccessRole", "ObjectDataAccessTypeRole",
           "DataChoicesRole")


