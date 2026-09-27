# -*- coding: utf-8 -*-
# $Id: dataexchangewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


import sys, os, typing, types, warnings, math, cmath # noqa
import numbers # noqa
# import dataclasses
import numpy as np # noqa
import quantities as pq # noqa
# import neo
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
except: # noqa
    __has_qtdbus__ = False

from core import datatypes # noqa
from core.prog import scipywarn # noqa
# from core import utilities
from gui import (guiutils, interact) # noqa
# from gui.workspacegui import WorkspaceGuiMixin
from gui.widgets.anchoringcollapsiblewidget import AnchoringCollapsibleWidget

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

try:
    from gui.widgets.dataclasswidgets.dataexchangewidget_ui import Ui_DataExchangeWidget

except:
    Ui_DataExchangeWidget, _ = loadUiType(
        os.path.join(__module_path__, "dataexchangewidget.ui")
        )

class DataExchangeWidget(Ui_DataExchangeWidget, AnchoringCollapsibleWidget, QtWidgets.QWidget):
    r"""Common widget to use as 1st level child in various Scipyen compound widgets.
Contains a set of tool buttons for loading/saving data to/from piclkle files and
for importing/exporting data to the user workspace.

For information purposes, the widget also contains a label with the workspace
symbol bound to the data (if any).

The widget is meant to be used as a child widget of more complex widgets in Scipyen,
to offset data input/output operations here (loading from/saving to pickle files,
importing from/exporting to the user's workspace).

These operations communicate with the parent widget via Qt signal/slots.

The only prerequisites for the parent widget are:

1. On the "output side": the parent widget should send the data object via one
of two signals: sig_dataSaving and sig_dataExporting to trigger respectively,
saving and exporting logic. These two signals (in the parent widget) MUST be
connected to the public Qt slots of this widget: ``slot_saveData`` and ``slot_exportData``.

2. On the "input side": the parent widget should have at least one Qt slot connected to this
widget's Qt signals ``sig_dataLoaded`` and ``sig_dataImported`` to receive the incoming
data object after loading from file or importing from the workspace.

"""
    # sig_dataLoaded = Signal(object, name="sig_dataLoaded")
    sig_requestLoadData = Signal(name="sig_requestLoadData")
    sig_requestImportData = Signal(name="sig_requestImportData")
    # sig_dataImported = Signal(object, name="sig_dataImported")
    sig_requestDataExport = Signal(name="sig_requestDataExport")
    sig_requestDataSave = Signal(name="sig_requestDataSave")
    sig_requestDataCopy = Signal(name="sig_requestDataCopy")
    sig_requestNewObject = Signal(name="sig_requestNewObject")
    sig_symbolChanged = Signal(str, name="sig_symbolChanged")
    sig_closing = Signal(name="sig_closing")
    sig_moved = Signal(QtCore.QPoint, name="sig_moved")
    sig_collapsed = Signal(name="sig_collapsed")

    def __init__(self, objType: typing.Optional[type]=None,
                 parent: typing.Optional[QtWidgets.QWidget] = None,
                 **kwargs):
        if isinstance(objType, QtWidgets.QWidget):
            obj_ = parent
            if isinstance(parent, type):
                parent = objType
            else:
                parent = None
            objType = obj_

        if objType is None:
            objType = type(None)

        self._objectType_ = objType
        self._objSymbol_ = kwargs.pop("objSymbol", None)

        # AnchoringCollapsibleWidget.__init__(self, parent=parent, **kwargs)
        # super().__init__(parent, **kwargs)
        QtWidgets.QWidget.__init__(self, parent)
        AnchoringCollapsibleWidget.__init__(self, parent=parent, **kwargs)

        Ui_DataExchangeWidget.__init__(self)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        self.loadToolButton.clicked.connect(self.sig_requestLoadData)
        self.importToolButton.clicked.connect(self.sig_requestImportData)
        self.saveToolButton.clicked.connect(self.sig_requestDataSave)
        self.copyToolButton.clicked.connect(self.sig_requestDataCopy)
        self.exportToolButton.clicked.connect(self.sig_requestDataExport)
        self.newObjectToolButton.clicked.connect(self.sig_requestNewObject)

        self.sig_uiConfigured.connect(self._slot_uiConfigured_)
        self.sig_uiConfigured.emit()

    def setObjectSymbol(self, val: str):
        self.objectSymbolLabel.setText(val)

    @property
    def varName(self) -> str:
        ret = self.objectSymbolLabel.text()
        if not isinstance(ret, str):
            return ""
        else:
            return ret

    @property
    def dataType(self) -> type:
        return self._objectType_

    @dataType.setter
    def dataType(self, val:type):
        if val is None:
            self._objectType_ = type(None)
        elif not isinstance(val, type):
            raise TypeError(f"Expecting a type or None; instead got {type(val).__name__}")

        self._objectType_ = val

    def setValue(self, obj: typing.Any, objSymbol:typing.Optional[str]=None):
        self.dataType = type(obj)
        if isinstance(objSymbol, str) and len(objSymbol.strip()):
            self._objSymbol_ = objSymbol
        else:
            candidateSymbols = self.getDataSymbolInWorkspace(obj)
            if isinstance(candidateSymbols, str):
                self._objSymbol_ = candidateSymbols

            elif (isinstance(candidateSymbols, typing.Sequence) and
                len(candidateSymbols) and
                all(isinstance(s, str) for s in candidateSymbols)):
                self._objSymbol_ = candidateSymbols[0]
            else:
                self._objSymbol_ = None

        if isinstance(self._objSymbol_, str) and len(self._objSymbol_.strip()):
            self.objectSymbolLabel.setText(self._objSymbol_)
            self.objectSymbolLabel.setToolTip(f"'{self._objSymbol_}' is bound to a {type(obj).__name__} object in the workspace")
            self.sig_symbolChanged.emit(self._objSymbol_)
        else:
            self.objectSymbolLabel.clear()
            self.objectSymbolLabel.setToolTip("")
            self.sig_symbolChanged.emit("")

