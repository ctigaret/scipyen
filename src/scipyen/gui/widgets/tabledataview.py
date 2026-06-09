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

class TableDataView(QtWidgets.QTableView):
    r"""Custom table view, with placeholder text
    """
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

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


