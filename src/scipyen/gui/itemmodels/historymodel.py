# -*- coding: utf-8 -*-
# $Id: historymodel.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import gc
import contextlib
import itertools
import seaborn as sb
import numpy as np
import matplotlib as mpl
import matplotlib.mlab as mlb
import matplotlib.pyplot as plt
from matplotlib._pylab_helpers import Gcf as Gcf
import traceback
import typing
import inspect
import os
import asyncio
import warnings
from copy import deepcopy
from functools import partial
from collections import deque
import datetime
import json

from traitlets import Bunch
# from jupyter_client.session import Message
from IPython.core.history import HistoryAccessor

from gui.guiutils import (get_text_width, get_elided_text)
from gui import pictgui as pgui
from core.traitcontainers import DataBag
from core.utilities import (summarize_object_properties,
                            standard_obj_summary_headers,
                            safe_identity_test,
                            reverse_mapping_lookup,
                            )
from core.strutils import (is_cached_output_varname, is_cached_input_varname)

from core.prog import (safewrapper, timefunc, processtimefunc, timeblock, print_styled)
from core.typeenum import TypeEnum
# from jupyter_core.paths import jupyter_runtime_dir

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

from gui.itemmodels.roles import *

class HistoryModel(QtGui.QStandardItemModel): # TODO: 2026-05-02 15:48:07 finalize me

    def __init__(self, shell, parent=None):
        super().__init__(0,2,parent)
        self._history_ = dict[str, str]()
        self.shell = shell
        self.setHorizontalHeaderLabels(["Session & Line:", "Session Date & Time or Expression:"])
        self.historyAccessor = HistoryAccessor()
        self.sessionNo = None
        self.itemsFont = QtWidgets.QApplication.font()
        hist = self.historyAccessor.search('*')

        sessionItem = None
        sessionRow = 0
        lineRow = 0
        for session, line, inline in hist:
            if self.sessionNo is None or self.sessionNo != session:
                self.sessionNo = session
                sessionInfo = self.historyAccessor.get_session_info(self.sessionNo)
                sessionItems = self._historySessionInfo_(self.sessionNo)
                sessionItem = sessionItems[0]
                self.invisibleRootItem().insertRow(sessionRow, sessionItems)
                sessionRow += 1
                lineRow = 0

            lineItems = self._historyLineInfo_(line, inline)
            sessionItem.insertRow(lineRow, lineItems)
            lineRow += 1

        currentSessionItems = self._historySessionInfo_(None)
        self.currentSessionItem = currentSessionItems[0]
        self.invisibleRootItem().insertRow(sessionRow, currentSessionItems)



    # def _historySessionInfo_(self, session:int, /,
    #                          asString:bool=False) -> tuple[QtGui.QStandardItem]:
    def _historySessionInfo_(self, session:int) -> tuple[QtGui.QStandardItem]:
        sessionInfo = self.historyAccessor.get_session_info(session)

        if sessionInfo is None: # this is / should be the current session
            sessionInfo = ("Current session", datetime.datetime.now(), None)
            sessionName = "Current"
            sessionInfoText = sessionInfo[0]
        else:
            sessionName = f"{sessionInfo[0]}"
            sessionInfoText = f"Session {sessionName}"

        if isinstance(sessionInfo[1], datetime.datetime):
            startDateTime = f"{sessionInfo[1].date().isoformat()} {sessionInfo[1].time().isoformat()}"
        else:
            startDateTime = ""

        if isinstance(sessionInfo[2], datetime.datetime):
            stopDateTime = f"{sessionInfo[2].date().isoformat()} {sessionInfo[2].time().isoformat()}"
        else:
            stopDateTime = ""

        sessionTimes = " "

        if len(startDateTime):
            sessionTimes = f"{startDateTime} - "
            if len(stopDateTime):
                sessionTimes = f"{startDateTime} - {stopDateTime}"

        elif len(stopDateTime):
            sessionTimes = f" - {stopDateTime}"

        # sessionInfoText = f"{sessionInfo[0]}"

        item0 = QtGui.QStandardItem(sessionName)
        item0.setData(sessionName, QtCore.Qt.DisplayRole)
        item0.setData(sessionInfoText, QtCore.Qt.ToolTipRole)
        item0.setData(f"#\n# {sessionInfoText}: {sessionTimes}", ObjectDataAccessRole)

        item1 = QtGui.QStandardItem(sessionTimes)
        item1.setData(sessionTimes, QtCore.Qt.DisplayRole)
        item1.setData(f"Session dates & times: {sessionTimes}", QtCore.Qt.ToolTipRole)
        item1.setData(f"#\n# {sessionInfoText}: {sessionTimes}", ObjectDataAccessRole)
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled
        for item in (item0, item1):
            item.setFlags(flags)
            item.setData(self.itemsFont, QtCore.Qt.FontRole)

        return (item0, item1)

        # if asString:
        #     return f"#\n# Session {sessionInfoText}: {sessionTimes}\n#"
        #
        # return [sessionInfoText, sessionTimes]

    # def _historyLineInfo_(self, line:int, inline:str, /,
    #                           asString:bool = False,
    #                           lineNumbers:bool = True) -> typing.Union[
    #                                                                     str,
    #                                                                     list[str]
    #                                                                   ]:

    def _historyLineInfo_(self, line:int, inline:str,
                            lineNumbers:bool = True) -> tuple[QtGui.QStandardItem]:
            item0 = QtGui.QStandardItem(f"{line}")
            item0.setData(f"{line}", QtCore.Qt.DisplayRole)
            item0.setData(f"Statement # {line}", QtCore.Qt.ToolTipRole)
            item0.setData(f"{line}: {inline}", ObjectDataAccessRole)

            item1 = QtGui.QStandardItem(inline)
            item1.setData(inline, QtCore.Qt.DisplayRole)
            item1.setData(f"Statement # {line} contents", QtCore.Qt.ToolTipRole)
            item0.setData(inline, ObjectDataAccessRole)

            flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled
            for item in (item0, item1):
                item.setFlags(flags)
                item.setData(self.itemsFont, QtCore.Qt.FontRole)

            return (item0, item1)


        # if asString:
        #     if lineNumbers:
        #         return f"{line}: {inline}"
        #     else:
        #         return inline
        #
        # return [repr(line), inline]

    def _updateHistory_(self, lineno, inline):
        mustUpdateSessionID = not self.currentSessionItem.hasChildren()
        lineItems = self._historyLineInfo_(lineno, inline)
        self.currentSessionItem.insertRow(self.currentSessionItem.rowCount(), lineItems)

    def setData(self: typing.Self, modelIndex: QtCore.QModelIndex,
                value: object, role = QtCore.Qt.EditRole) -> bool:
        pass # disallowed!

    def mimeData(self, indexes: typing.Sequence[QtCore.QModelIndex]) -> QtCore.QMimeData:
        import pickle
        from iolib import jsonio
        from core import strutils
        mData = super().mimeData(indexes)

        if len(indexes):
            wscol = list(map(lambda c: self.headerData(c, QtCore.Qt.Horizontal),
                               range(self.columnCount()))).index("Session & Line:")

            session_line_no_items = list(map(lambda i: self.item(i.row(), 0), indexes))

            # statement_items = =



            # varnames = list(filter(lambda t: t in self.shell.user_ns,
            #                         map(lambda i: i.data(QtCore.Qt.DisplayRole),
            #                             filter(lambda i: self.item(i.row(), wscol).text() == "Internal",
            #                                     items)
            #                             )
            #                         )
            #                 )
            #
            # if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier):
            #     varnames = list(map(lambda s: f'"{s}"', varnames))
            #
            # if bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier):
            #     data = ",\n".join(varnames)
            # else:
            #     data = ", ".join(varnames)

            # mData.setText(data)

            return mData
