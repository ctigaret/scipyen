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
# import enum
# import pickle
# from functools import (singledispatch, singledispatchmethod)
# from collections import deque
# from dataclasses import MISSING
# import math
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

from gui import guiutils

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_file__ = "inlinefiledirchooser.ui"

if __has_PyQt6__ or __has_PySide6__:
    __UI_widget__, __QWidget__ = loadUiType(
        os.path.join(__module_path__, __ui_file__))
else:
    __UI_widget__, __QWidget__ = loadUiType(
        os.path.join(__module_path__, __ui_file__),
        from_imports = True, import_from = "gui.widgets")

class InlineFileDirChooserWidget(__UI_widget__, QtWidgets.QWidget):
    def __init__(self,
                 initial: typing.Optional[pathlib.Path] = None,
                 dirsOnly: bool = False,
                 parent: typing.Optional[QtWidgets.QWidget] = None):
        QtWidgets.QWidget.__init__(self, parent = parent)
        self._dirsOnly_ = dirsOnly is True

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
        self.launchPushButton.clicked.connect(self._slot_launchAction_)

    @Slot(bool)
    def _slot_setDirsOnly_(self, val: bool):
        self._dirsOnly_ = val is True

    @Slot()
    def _slot_launchAction_(self):
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

        if isinstance(ret, tuple):
            ret = ret[0]

        if len(ret):
            # print(f"{ret}")
            newPath = pathlib.Path(ret)
            if self.path != newPath:
                self.path = newPath

    @property
    def path(self) -> pathlib.Path:
        return self._path_

    @path.setter
    def path(self, val: pathlib.Path):
        if isinstance(val, pathlib.Path):
            if not val.exists():
                QtWidgets.QMessageBox.critical(
                    self, "Directory/File Chooser",
                    f"Path {val.as_posix()} does not exist"
                    )
                return

            if val != self._path_:
                self._path_ = val

                txt = guiutils.get_elided_text(
                    val.as_posix(),
                    self.launchPushButton.size().width(),
                    QtCore.Qt.ElideMiddle
                    )

            self.launchPushButton.setText(txt)

    @property
    def dirsOnly(self) -> bool:
        return self._dirsOnly_

    @dirsOnly.setter
    def dirsOnly(self, val:bool):
        self._dirsOnly_ = val is True
        sigBlock = QtCore.QSignalBlocker(self.dirsOnlyCheckBox)
        self.dirsOnlyCheckBox.setChecked(self._dirsOnly_ is True)
