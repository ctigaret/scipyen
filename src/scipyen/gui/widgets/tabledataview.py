# -*- coding: utf-8 -*-
# $Id: tabledataview.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# NOTE: 2026-02-02 08:32:09
# DO NOT REMOVE
# used in tableeditorwidget.TableEditorWidget and tableeditor.TableEditor

#### BEGIN core python modules
from __future__ import print_function

import os, inspect, warnings, traceback, datetime, typing, sys
from functools import (singledispatch, singledispatchmethod)

#### END core python modules

#### BEGIN 3rd party modules
import pandas as pd

r"""Custom table view, with placeholder text
"""

import quantities as pq
#import xarray as xa
import numpy as np
import neo
from core.vigra_patches import vigra
# import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
# __has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    # import PySide6
    # from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    # from qtpy import sip
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    # __has_sip__ = True

class TableDataView(QtWidgets.QTableView):
    r"""Custom table view, with placeholder text

For code painting the NW corner label see
// Source - https://stackoverflow.com/a/24163288
// Posted by aknuds1, modified by community. See post 'Timeline' for change history
// Retrieved 2026-06-12, License - CC BY-SA 3.0

"""
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None, **kwargs):
        super().__init__(parent)

        self._decimals_ = kwargs.pop("decimals", None)

        if not isinstance(self._decimals_, int) or self._decimals_ < 0:
            self._decimals_ = None

#     def openPersistentEditor(self, index):
#         model = self.model()
#         if model is None or model.rowCount() == 0 or model.columnCount() == 0:
#             return
#
#         col = index.column()
#
#         if hasattr(model, "_modelDataColumnHeaders_"):
#             colHeader = model._modelDataColumnHeaders_[col]
#             if colHeader.lower() == "edit":

    def setCornerLabel(self, text:str = ""):
        btn = self.findChild(QtWidgets.QAbstractButton)
        btn.setText(text)
        btn.setToolTip('Toggle selecting all table cells')
        btn.installEventFilter(self)

        opt = QtWidgets.QStyleOptionHeader()
        opt.text = btn.text()
        s = QtCore.QSize(btn.style().sizeFromContents(
            QtWidgets.QStyle.CT_HeaderSection, opt, QtCore.QSize(), btn)#.
            # expandedTo(QtWidgets.QApplication.globalStrut())
            )

        if s.isValid():
            self.verticalHeader().setMinimumWidth(s.width())

    def paintEvent(self, event):
        r"""Paints a placeholder text when there is no data"""
        super().paintEvent(event)
        if self.model() is not None and self.model().rowCount() > 0:
            return

        painter = QtGui.QPainter(self.viewport())
        painter.save()
        col = self.palette().placeholderText().color()
        painter.setPen(col)
        fm = self.fontMetrics()
        elided_text = fm.elidedText(
            "No data", QtCore.Qt.ElideRight, self.viewport().width()
        )
        painter.drawText(self.viewport().rect(), QtCore.Qt.AlignCenter, elided_text)
        painter.restore()

    def eventFilter(self, obj, event):
        if event.type() != QtCore.QEvent.Paint or not isinstance(
                obj, QtWidgets.QAbstractButton):
            return False

        # Paint table corner button (i.e. label for row index)
        # by hand (borrowed from QTableCornerButton)
        opt = QtWidgets.QStyleOptionHeader()
        opt.initFrom(obj)
        styleState = QtWidgets.QStyle.State_None

        if obj.isEnabled():
            styleState |= QtWidgets.QStyle.State_Enabled

        if obj.isActiveWindow():
            styleState |= QtWidgets.QStyle.State_Active

        if obj.isDown():
            styleState |= QtWidgets.QStyle.State_Sunken

        opt.state = styleState
        opt.rect = obj.rect()

        # This line is the only difference to QTableCornerButton
        opt.text = obj.text()
        opt.position = QtWidgets.QStyleOptionHeader.OnlyOneSection
        painter = QtWidgets.QStylePainter(obj)
        painter.drawControl(QtWidgets.QStyle.CE_Header, opt)

        return True

    @Slot(QtWidgets.QWidget, QtCore.QModelIndex)
    def _slot_editDataExternally(self, sender, index): # TODO 2026-06-07 11:08:52 finalize me
        # NOTE: 2026-06-07 11:56:17
        # external editor NEEDS a separate QMainWindow!
        if isinstance(sender, QtWidgets.QPushButton):
            model = self._currentModelIndex_.model()
            role = ObjectDataRole if self._useObjectDataRole_ else QtCore.Qt.EditRole

            data = self._currentModelIndex_.data(role)

            editor = ExternalEditorDelegate(data)
            editor.decimals = self._decimals_

            editor.show()

    @property
    def decimals(self) -> int | None:
        return self._decimals_

    @decimals.setter
    def decimals(self, val: int | None = None):
        needsDataChanged = self._decimals_ != val

        if isinstance(val, int) and val >= 0:
            self._decimals_ = val
        else:
            self._decimals_ = None

        if needsDataChanged:
            self.reset()
            # self.model().beginResetModel()
            # self.model().endResetModel()
