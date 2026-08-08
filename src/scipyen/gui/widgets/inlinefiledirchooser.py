# -*- coding: utf-8 -*-
# $Id: inlinefiledirchooser.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
New data viewer widget, based on datatreemodel
"""
from __future__ import print_function

import os, sys # noqa
# import warnings
# import types
import traceback
# import itertools
# import inspect
# import dataclasses
# import numbers
import pathlib
# import datetime
# import fractions
# import decimal
# import pkgutil
import typing
import types
# import enum
# import pickle
from functools import partial
# from functools import (singledispatch, singledispatchmethod)
# from collections import deque
# from dataclasses import MISSING
# import math
import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
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

    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

from gui import workspacegui
from core.prog import scipywarn

__module_path__ = os.path.abspath(os.path.dirname(__file__))

try:
    from gui.widgets.inlinefiledirchooser_ui import Ui_InlineFileDirChooser

except:
    __ui_file__ = "inlinefiledirchooser.ui"

    if __has_PyQt6__ or __has_PySide6__:
        Ui_InlineFileDirChooser, _ = loadUiType(
            os.path.join(__module_path__, __ui_file__))
    else:
        Ui_InlineFileDirChooser, _ = loadUiType(
            os.path.join(__module_path__, __ui_file__),
            from_imports = True, import_from = "gui.widgets")

class InlineFileDirChooserWidget(Ui_InlineFileDirChooser, QtWidgets.QWidget):
    sig_pathChanged = Signal(pathlib.Path, name = "sig_pathChanged")
    sig_dataChanged = Signal(name = "sig_dataChanged")
    _sig_newPath_ = Signal(pathlib.Path, name = "_sig_newPath_")
    if __has_PySide6__:
        sig_dispatchAction = Signal(object, name="sig_dispatchAction")
    else:
        sig_dispatchAction = Signal([partial], [types.FunctionType],
                                    name="sig_dispatchAction")

    def __init__(self,
                 initial: typing.Optional[pathlib.Path] = None,
                 dirsOnly: bool = False,
                 readOnly: bool = False,
                 asDelegate: bool = False,
                 parent: typing.Optional[QtWidgets.QWidget] = None):
        QtWidgets.QWidget.__init__(self, parent = parent)
        super(Ui_InlineFileDirChooser, self).__init__()
        self._dirsOnly_ = dirsOnly is True
        self._readOnly_ = readOnly is True
        self._pendingChange_: bool = False

        self._isDelegate_:bool = asDelegate is True

        # print(f"{self.__class__.__name__}.__init__({initial})\n")

        if (not isinstance(initial, pathlib.Path)
            or not initial.exists()):
            self._path_ = pathlib.Path(os.getcwd())

        else:
            if self._dirsOnly_ and not initial.is_dir():
                self._path_ = initial.parent
            else:
                self._path_ = initial

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        self.dirsOnlyCheckBox.setChecked(self._dirsOnly_ is True)
        self.dirsOnlyCheckBox.toggled.connect(self._slot_setDirsOnly_)
        icon_name = "document-open-folder" if self._dirsOnly_ else "document-open"
        self.launchPushButton.setIcon(QtGui.QIcon.fromTheme(icon_name))
        self.launchPushButton.setText(self._path_.as_posix())
        if self._isDelegate_:
            self.launchPushButton.clicked.connect(self._slot_dispatchAction_)
        else:
            self.launchPushButton.clicked.connect(self._slot_launchAction_)

    @Slot(bool)
    def _slot_setDirsOnly_(self, val: bool):
        self._dirsOnly_ = val is True

    @Slot()
    def _slot_dispatchAction_(self):
        if self._path_.is_file():
            # suggestedName = self._path_.name
            targetDir = self._path_.parent
        else:
            targetDir = self._path_
            # suggestedName = None
        if self._dirsOnly_:
            fn = partial(workspacegui.FileIOGui.chooseDirectory_static,
                         targetDir = self._path_,
                         asPath=True)
        else:
            fn = partial(workspacegui.FileIOGui.chooseFile_static,
                         targetDir = self._path_,
                         # fileName = suggestedName,
                         save=False, single=True, asPath=True)

        if __has_PySide6__:
            self.sig_dispatchAction.emit(fn)
        else:
            self.sig_dispatchAction[partial].emit(fn)

    @Slot()
    def _slot_launchAction_(self):
        # print(f"{self.__class__.__name__}._slot_launchAction_\n")
        if self._readOnly_:
            return

        self._pendingChange_ = True

        if self._dirsOnly_:
            if "win32" in sys.platform:
                flags = (QtWidgets.QFileDialog.DontUseNativeDialog
                        | QtWidgets.QFileDialog.ShowDirsOnly
                        | QtWidgets.QFileDialog.DontResolveSymlinks
                        )
            else:
                flags = (QtWidgets.QFileDialog.ShowDirsOnly
                        | QtWidgets.QFileDialog.DontResolveSymlinks
                        )

            ret = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Choose Directory",
                self._path_.as_posix(),
                flags,
                )

        else:
            if self._path_.is_file():
                _dir_ = self._path_.parent
            else:
                _dir_ = self._path_

            ret = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Choose File",
                _dir_.as_posix(),
                filter = None,
                initialFilter = None,
                options = QtWidgets.QFileDialog.DontResolveSymlinks
                )

        # print(f"{self.__class__.__name__}._slot_launchAction_ -> ret = {ret}\n")

        if isinstance(ret, tuple):
            ret = ret[0]

        if not isinstance(ret, str) or len(ret.strip()) == 0:
            self._pendingChange_ = False
            return

        newPath = pathlib.Path(ret)
        if newPath == self.path:
            self._pendingChange_ = False
            return

        self._sig_newPath_.emit(newPath)

    def value(self) -> pathlib.Path:
        # print(f"{self.__class__.__name__}.value() -> {self.path}\n")
        return self.path

    def setValue(self, path: pathlib.Path):
        # print(f"{self.__class__.__name__}.setValue({path})\n")
        if not isinstance(path, pathlib.Path) or not path.exists():
            scipywarn(f"Supplied value ({path}) is not a valid Path")
            return

        self.path = path

    @Slot(pathlib.Path)
    def _slot_newPath_(self, val: pathlib.Path):
        # print(f"{self.__class__.__name__}._slot_newPath({val})\n")
        if isinstance(val, pathlib.Path) and val.exists():
            self.path = val

    @property
    def readOnly(self) -> bool:
        return self._readOnly_

    @readOnly.setter
    def readOnly(self, val: bool):
        self._readOnly_ = val is True

    @property
    def path(self) -> pathlib.Path:
        return self._path_

    @path.setter
    def path(self, val: pathlib.Path):
        if not isinstance(val, pathlib.Path) or not val.exists():
            scipywarn(f"Supplied value ({val}) is not a valid Path")
            return

        if val != self._path_:
            self._pendingChange_ = False
            self._path_ = val
            self.launchPushButton.setText(val.as_posix())
            self.sig_pathChanged.emit(self._path_)
            self.sig_dataChanged.emit()

    @property
    def dirsOnly(self) -> bool:
        return self._dirsOnly_

    @dirsOnly.setter
    def dirsOnly(self, val:bool):
        self._dirsOnly_ = val is True
        sigBlock = QtCore.QSignalBlocker(self.dirsOnlyCheckBox) # noqa
        self.dirsOnlyCheckBox.setChecked(self._dirsOnly_ is True)

class InlineFileChooserWidget(InlineFileDirChooserWidget):
    def __init__(self,
                 initial: typing.Optional[pathlib.Path] = None,
                 readOnly: bool = False,
                 asDelegate: bool = False,
                 parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(initial=initial, dirsOnly=False,
                         readOnly=readOnly,
                         asDelegate=asDelegate,
                         parent = parent)
        self.dirsOnlyCheckBox.setVisible(False)

class InlineDirChooserWidget(InlineFileDirChooserWidget):
    def __init__(self,
                 initial: typing.Optional[pathlib.Path] = None,
                 readOnly: bool = False,
                 asDelegate: bool = False,
                 parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(initial=initial, dirsOnly=True,
                         readOnly=readOnly,
                         asDelegate=asDelegate,
                         parent=parent)
        self.dirsOnlyCheckBox.setVisible(False)
