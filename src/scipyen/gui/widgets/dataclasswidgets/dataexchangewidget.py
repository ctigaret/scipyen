# -*- coding: utf-8 -*-
# $Id: dataexchangewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


import sys, os, typing, types, warnings, math, cmath # noqa
import numbers # noqa
import dataclasses
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
from core.prog import scipywarn # noqa
from core import utilities
from gui import (guiutils, interact) # noqa
from gui.workspacegui import WorkspaceGuiMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_DataExchangeWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "dataexchangewidget.ui")
    )

class DataExchangeWidget(Ui_DataExchangeWidget, QWidget, WorkspaceGuiMixin):
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

1. On the "output side": the parent widget shoulwd sends the data object via one
of two signals: sig_dataSaving and sig_dataExporting to trigger respectively,
saving and exporting logic. These two signals (in the parent widget) MUST be
connected to the public Qt slots of this widget: ``slot_saveData`` and ``slot_exportData``.

2. On the "input side": the parent widget should have at least one Qt slot connected to this
widget's Qt signals ``sig_dataLoaded`` and ``sig_dataImported`` to receive the incoming
data object after loading from file or importing from the workspace.

NOTE: This widget does NOT hold any reference to the data; hence it lacks a
`value()` method. On the other hand, the method `setValue(obj)` updates the internal
attributes of the widget to reflect the data type of `obj` and possibly the symbol
that `obj` is bound to, in the user space.

"""
    sig_dataLoaded = Signal(object, name="sig_dataLoaded")
    sig_dataImported = Signal(object, name="sig_dataImported")
    sig_requestDataExport = Signal(name="sig_requestDataExport")
    sig_requestDataSave = Signal(name="sig_requestDataSave")
    sig_requestDataCopy = Signal(name="sig_requestDataCopy")
    sig_requestNewObject = Signal(name="sig_requestNewObject")
    sig_symbolChanged = Signal(str, name="sig_symbolChanged")

    def __init__(self, objType: typing.Optional[type]=None,
                 parent: typing.Optional[QtWidgets.QWidget] = None, **kwargs):

        if isinstance(objType, QtWidgets.QWidget):
            obj_ = parent
            if isinstance(parent, type):
                parent = objType
            else:
                parent = None
            objType = obj_

        if objType is None:
            objType = type(None)

        QtCore.QObject.__init__(self, parent=parent)
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)

        self._objectType_ = objType

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        self.loadToolButton.clicked.connect(self._slot_loadData)
        self.importToolButton.clicked.connect(self._slot_importData)
        self.saveToolButton.clicked.connect(self.sig_requestDataSave)
        self.copyToolButton.clicked.connect(self.sig_requestDataCopy)
        # self.saveToolButton.clicked.connect(self._slot_saveData)
        self.exportToolButton.clicked.connect(self.sig_requestDataExport)
        self.newObjectToolButton.clicked.connect(self.sig_requestNewObject)
        # self.exportToolButton.clicked.connect(self._slot_exportData)

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

    @Slot()
    def _slot_loadData(self):
        fileNameFilter = "*.pkl"
        fn, fl = self.chooseFile(caption = f"Open {self._objectType_.__name__} Pickle File",
                                fileFilter = fileNameFilter,
                                single=True)

        if len(fn.strip()):
            obj = pio.loadFile(fn)
            if isinstance(obj, self._objectType_):
                if self.receivers(self.sig_dataLoaded) > 0:
                    self.sig_dataLoaded.emit(obj)
                    # varName = os.path.basename(fn)
                    # self.objectSymbolLabel.setText(varName)
                    # self.objectSymbolLabel.setToolTip(f"'{varName}' is a {type(obj).__name__} object")
                else:
                    self.setValue(obj)

            else:
                self.errorMessage(title = f"Open {self._objectType_.__name__} Pickle File",
                                text = f"Expecting a {self._objectType_.__name__}; intead got a {type(obj).__name__}")

    @Slot(object)
    def slot_saveData(self, obj):
        if not isinstance(obj, self._objectType_):
            return

        fileNameFilter = "*.pkl"

        fn, fl = self.chooseFile(caption = f"Save {self._objectType_.__name__} as Pickle File",
                                fileFilter = fileNameFilter,
                                single=True, save=True)

        if len(fn.strip()):
            pio.savePickle(obj, fn)


    @Slot()
    def _slot_importData(self):
        ret = self.importFromWorkSpace(dataTypes = self._objectType_,
                                    title=f"Select {self._objectType_.__name__} Object in Workspace",
                                    single=True,
                                    with_varName=True,
                                    retrieve_all = True)
        if isinstance(ret, dict) and len(ret) == 1:
            varName = list(ret.keys())[0]
            obj = ret[varName]
            if isinstance(obj, self._objectType_):
                if self.receivers(self.sig_dataImported) > 0:
                    self.sig_symbolChanged.emit(varName)
                    self.sig_dataImported.emit(obj)
                    # self.objectSymbolLabel.setText(varName)
                    # self.objectSymbolLabel.setToolTip(f"'{varName}' is bound to a {type(obj).__name__} object in the workspace")

    @Slot(object)
    def slot_exportData(self, obj):
        if isinstance(obj, self._objectType_):
            name = obj.name
            if not isinstance(name, str) or len(name.strip()) == 0:
                name = self._objectType_.__name__.lower()

            varName = self.exportDataToWorkspace(obj, name)

            if isinstance(varName, str):
                self.objectSymbolLabel.setText(varName)
                self.objectSymbolLabel.setToolTip(f"'{varName}' is bound to a {type(obj).__name__} object in the workspace")
                self.sig_symbolChanged.emit(varName)

    @Slot(object)
    def slot_copyData(self, obj):
        from copy import deepcopy
        if isinstance(obj, self._objectType_):
            obj1 = deepcopy(obj)
            name = obj1.name
            if not isinstance(name, str) or len(name.strip()) == 0:
                name = self._objectType_.__name__.lower()

            self.exportDataToWorkspace(obj1, name)

    def setValue(self, obj: typing.Any, objSymbol:typing.Optional[str]=None):
        self.dataType = type(obj)
        if isinstance(objSymbol, str) and len(objSymbol.strip()):
            varName = objSymbol
        else:
            candidateSymbols = self.getDataSymbolInWorkspace(obj)
            if isinstance(candidateSymbols, str):
                varName = candidateSymbols

            elif (isinstance(candidateSymbols, typing.Sequence) and
                len(candidateSymbols) and
                all(isinstance(s, str) for s in candidateSymbols)):
                varName = candidateSymbols[0]
            else:
                varName = None

        if isinstance(varName, str) and len(varName.strip()):
            self.objectSymbolLabel.setText(varName)
            self.objectSymbolLabel.setToolTip(f"'{varName}' is bound to a {type(obj).__name__} object in the workspace")
            self.sig_symbolChanged.emit(varName)
        else:
            self.objectSymbolLabel.clear()
            self.objectSymbolLabel.setToolTip("")
            self.sig_symbolChanged.emit("")


