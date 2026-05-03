from __future__ import print_function

import os
# import warnings
import types
import traceback
# import itertools
import inspect
import dataclasses
import numbers
import pathlib
import datetime
import fractions
import decimal
import pkgutil
import typing
# -*- coding: utf-8 -*-
# $Id: historytreeview.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import enum
import pickle
from functools import (singledispatch, singledispatchmethod)
from collections import deque
from dataclasses import MISSING
import math
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

# from core.workspacefunctions import (validate_varname, user_workspace)
from core import prog

# from gui.delegates import PythonItemDelegate
from gui.workspacegui import WorkspaceGuiMixin
from gui.itemmodels.roles import * #noqa
from gui.itemmodels.historymodel import HistoryModel

class HistoryTreeView(QtWidgets.QTreeView, WorkspaceGuiMixin): # TODO 2026-05-03 23:27:07 finalize me
    sig_itemDoubleClicked = Signal(QtGui.QStandardItem, name="sig_itemDoubleClicked")

    def __init__(self: typing.Self, *args, **kwargs):
        parent = kwargs.pop("parent", None)
        super().__init__(parent=parent)

        self.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.setExpandsOnDoubleClick(True)

        self._dragStartPosition_: typing.Optional[QtCore.QPoint] = None

        shell = self._scipyenWindow_.shell

        super().setModel(HistoryModel(shell))

    def setModel(self: typing.Self, model: QtCore.QAbstractItemModel):
        # disallow changing the model
        pass

    def clear(self: typing.Self):
        pass
        #self.model().clear()

    def mousePressEvent(self: typing.Self, evt: QtGui.QMouseEvent):
        if evt.button() == QtCore.Qt.LeftButton:
            self._dragStartPosition_ = evt.pos()

        super().mousePressEvent(evt)
        evt.setAccepted(True)

    def mouseDoubleClickEvent(self: typing.Self, evt: QtGui.QMouseEvent):
        pos = evt.position().toPoint()
        index = self.indexAt(pos)
        item = self.model().itemFromIndex(index)
        if item.column() == 0:
            self.sig_itemDoubleClicked.emit(item)
        super().mouseDoubleClickEvent(evt)
        evt.setAccepted(True)

    # def paintEvent(self, event):
    #     super().paintEvent(event)
    #     if self.model()._modelData_ is None:
    #         painter = QtGui.QPainter(self.viewport())
    #         painter.save()
    #         col = self.palette().placeholderText().color()
    #         painter.setPen(col)
    #         fm = self.fontMetrics()
    #         elided_text = fm.elidedText(
    #             "No data", QtCore.Qt.ElideRight, self.viewport().width()
    #         )
    #         painter.drawText(self.viewport().rect(), QtCore.Qt.AlignCenter, elided_text)
    #         painter.restore()

