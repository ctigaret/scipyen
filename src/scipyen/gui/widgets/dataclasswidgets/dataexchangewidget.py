# -*- coding: utf-8 -*-
# $Id: dataexchangewidget.py $
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
from core.prog import scipywarn # noqa
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

"""
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

        # if not isinstance(objType, type):
        #     raise TypeError(f"First parameter must be a type; instead, got a {type(objType).__name__}")

        self._objectType_ = objType

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        self.loadToolButton.clicked.connect(self._slot_loadData)
        self.importToolButton.clicked.connect(self._slot_importData)
        self.saveToolButton.clicked.connect(self._slot_saveData)
        self.exportToolButton.clicked.connect(self._slot_exportData)

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
        if hasattr(self.parent(), "setValue"):
            fileNameFilter = "*.pkl"
            fn, fl = self.chooseFile(caption = f"Open {self._objectType_.__name__} Pickle File",
                                    fileFilter = fileNameFilter,
                                    single=True)

            if len(fn.strip()):
                obj = pio.loadFile(fn)
                if isinstance(obj, self._objectType_):
                    self.parent().setValue(obj)
                else:
                    self.errorMessage(title = f"Open {self._objectType_.__name__} Pickle File",
                                    text = f"Expecting a {self._objectType_.__name__}; intead got a {type(obj).__name__}")

            if hasattr(self.parent(), "sig_valueChanged"):
                self.parent().sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_saveData(self):
        if hasattr(self.parent(), "value"):
            obj = self.parent().value()

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
        if hasattr(self.parent(), "setValue"):
            ret = self.importFromWorkSpace(dataTypes = self._objectType_,
                                        title=f"Select {self._objectType_.__name__} Object in Workspace",
                                        single=True,
                                        retrieve_all = True)
            # print(f"{self.__class__.__name__}._slot_importData -> ret = {ret}\n\t({type(ret).__name__})")
            if isinstance(ret, typing.Sequence) and len(ret) and isinstance(ret[0], self._objectType_):
                self.parent().setValue(ret[0])

            if hasattr(self.parent(), "sig_valueChanged"):
                self.parent().sig_valueChanged.emit(self.value())

    @Slot()
    def _slot_exportData(self):
        if hasattr(self.parent, "value"):
            obj = self.parent().value()
            if isinstance(obj, self._objectType_):
                name = obj.name
                if not isinstance(name, str) or len(name.strip()) == 0:
                    name = self._objectType_.__name__.lower()

                self.exportDataToWorkspace(obj, name)
