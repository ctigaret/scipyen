# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-
# $Id: filesystemmodel.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
r"""
"""
import os, sys, pathlib, traceback, typing, types, stat, datetime # noqa
import dataclasses
import psutil
from functools import (singledispatch, singledispatchmethod) # noqa
from enum import Enum, IntEnum # noqa
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
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

class FileSystemModel(QtGui.QFileSystemModel):
    CutItemRole = QtCore.Qt.UserRole=1
    def __init__(self, parent:typing.Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)
        self._cutIndexes_:typing.Sequence[QtCore.QModelIndex] = list()
        self._modifiedTimeFormat_: typing.Optional[QtCore.Locale.FormatType] = None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int) -> QtCore.QVariant:
        if orientation == QtCore.Qt.Horizontal and section == 3 and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant("Modified")

        return super().headerData(section, orientation, role)

    def data(self, index:QtCore.QModelIndex, role:QtCore.Qt.ItemDataRole=QtCore.Qt.DisplayRole) -> QtCore.QVariant:
        from gui import guiutils
        # NOTE: 2026-01-25 21:20:01
        # not sure this does anything meaningful...
        # simply because the stock QTreeView does not seem to ever query the ForegroundRole
        # and because this model does define a custom setData(…) to set a ForegroundRole for the items.
        #
        # besides, I don;t think this approach works; rather, I use a custom QStyledItemDelegate defined in gui.delegates
        if index in self._cutIndexes_:
            if role == QtCore.Qt.ForegroundRole:
                return QtWidgets.QApplication.palette().brush(QtGui.QPalette.Inactive, QtGui.QPalette.Text)

        if isinstance(self.timeFormat, (QtCore.QLocale.FormatType, str)):
            if role == QtCore.Qt.DisplayRole and index.column() == 3:
                lastMod = index.data(self.FileInfoRole).lastModified() # a QDateTime
                if isinstance(self.timeFormat, QtCore.QLocale.FormatType):
                    return QtCore.QVariant(guiutils.formatRelativeDateTime(lastMod, self.timeFormat))
                elif isinstance(self.timeFormat, str) and self.timeFormat in ("Fancy Short", "Fancy Narrow"):
                    tFormat = QtCore.QLocale.ShortFormat if self.timeFormat == "Fancy Short" else QtCore.QLocale.NarrowFormat
                    return QtCore.QVariant(guiutils.formatRelativeDateTime(lastMod, tFormat, fancy=True))

        return super().data(index, role)

    @property
    def timeFormat(self) -> typing.Optional[typing.Union[QtCore.QLocale.FormatType, str]]:# QtCore.QLocale.FormatType | None:
        return self._modifiedTimeFormat_

    @timeFormat.setter
    def timeFormat(self, val: typing.Union[QtCore.QLocale.FormatType, str]) -> None:
        if isinstance(val, QtCore.QLocale.FormatType):
            self._modifiedTimeFormat_ = val

        elif isinstance(val, str) and val in (
            "LongFormat", "ShortFormat", "NarrowFormat", "Standard",
            "Fancy Short", "Fancy Narrow"
            ):

            if val in ("LongFormat", "ShortFormat", "NarrowFormat"):
                self._modifiedTimeFormat_ = getattr(QtCore.QLocale.FormatType, val)
            elif val == "Standard":
                self._modifiedTimeFormat_ = None
            else:
                self._modifiedTimeFormat_ = val

        else:
            self._modifiedTimeFormat_ = None

    @property
    def cutIndexes(self) -> list:
        return self._cutIndexes_

    @cutIndexes.setter
    def cutIndexes(self, value:typing.Sequence[QtCore.QModelIndex]):
        if len(value) and not all(isinstance(v, QtCore.QModelIndex) for v in value):
            return

        self._cutIndexes_ = value

    def getFileIcon(self, index: QtCore.QModelIndex,
                    size: QtCore.QSize = QtCore.QSize(48, 48)) -> QtGui.QPixmap:
        icon = index.data(QtGui.QFileSystemModel.FileIconRole)
        return icon.pixmap(size)

    def getFileInfoText(self, index: QtCore.QModelIndex):
        mimeDb = QtCore.QMimeDatabase()
        fileInfo = index.data(QtGui.QFileSystemModel.FileInfoRole)
        infoData = ["<html>"]
        infoData.append(fileInfo.fileName())
        mimeType = mimeDb.mimeTypeForFile(fileInfo)
        mimeName = mimeType.name()
        mimeAliases = mimeType.aliases()
        mimeComment = mimeType.comment()
        infoData.append(f"<p><b>Mime Type:</b> {mimeName}<br>")
        if len(mimeAliases):
            infoData.append(f"<b>Mime Aliases:</b> {', '.join(mimeAliases)}<br>")
        infoData.append(f"<b>Mime Comment:</b> {mimeComment}</p>")
        infoData.append(f"<p><b>Path:</b> {fileInfo.absolutePath()}</p>")
        if fileInfo.isSymbolicLink():
            infoData.append(f"<p><b>Linked To:</b> {fileInfo.symLinkTarget()}</p>")

        bTime = fileInfo.birthTime()
        lastMod = fileInfo.lastModified()
        if isinstance(self.timeFormat, QtCore.QLocale.FormatType):
            infoData.append(f"<p><b>Created:</b> {guiutils.formatRelativeDateTime(bTime, self.timeFormat)}<br>")
            infoData.append(f"<b>Modified:</b> {guiutils.formatRelativeDateTime(lastMod, self.timeFormat)}</p>")
        elif isinstance(self.timeFormat, str) and self.timeFormat in ("Fancy Short", "Fancy Narrow"):
            tFormat = QtCore.QLocale.ShortFormat if self.timeFormat == "Fancy Short" else QtCore.QLocale.NarrowFormat
            infoData.append(f"<p><b>Created:</b> {guiutils.formatRelativeDateTime(bTime, tFormat, fancy=True)}<br>")
            infoData.append(f"<b>Modified:</b> {guiutils.formatRelativeDateTime(lastMod, tFormat, fancy=True)}</p>")

        size = fileInfo.size()
        infoData.append(f"<p><b>Size (bytes):</b> {size}</p>")

        owner = fileInfo.owner()
        if len(owner):
            infoData.append(f"<p><b>Owner:</b> {owner}")

        group = fileInfo.group()
        if len(group):
            if len(owner):
                infoData.append(f"<br><b>Group:</b> {group}<p>")
            else:
                infoData.append(f"<p><b>Group:</b> {group}<p>")
        else:
            infoData.append("<p>")

        infoData.append(f"<p><b>Readable:</b> {fileInfo.isReadable()}<br>")
        infoData.append(f"<b>Writable:</b> {fileInfo.isWritable()}<br>")
        infoData.append(f"<b>Executable:</b> {fileInfo.isExecutable()}</p>")
        infoData.append("</html>")
        return "\n".join(infoData)

        # if not self.isDir(index):
        #     fileInfo = index.data(QtGui.QFileSystemModel.FileInfoRole)
        #     infoData = list()
        #     infoData.append(fileInfo.fileName())
        #     infoData.append(f"Path: {fileInfo.absolutePath()}")
        #     if fileInfo.isSymbolicLink():
        #         infoData.append(f"Linked to: {fileInfo.symLinkTarget()}")
        #
        #     bTime = fileInfo.birthTime()
        #     lastMod = fileInfo.lastModified()
        #     if isinstance(self.timeFormat, QtCore.QLocale.FormatType):
        #         infoData.append(f"Created: {guiutils.formatRelativeDateTime(bTime, self.timeFormat)}")
        #         infoData.append(f"Modified: {guiutils.formatRelativeDateTime(lastMod, self.timeFormat)}")
        #     elif isinstance(self.timeFormat, str) and self.timeFormat in ("Fancy Short", "Fancy Narrow"):
        #         tFormat = QtCore.QLocale.ShortFormat if self.timeFormat == "Fancy Short" else QtCore.QLocale.NarrowFormat
        #         infoData.append(f"Created: {guiutils.formatRelativeDateTime(bTime, tFormat, fancy=True)}")
        #         infoData.append(f"Modified: {guiutils.formatRelativeDateTime(lastMod, tFormat, fancy=True)}")
        #
        #
        #     group = fileInfo.group()
        #     if len(group):
        #         infoData.append(f"Group: {group}")
        #
        #     owner = fileInfo.owner()
        #     if len(owner):
        #         infoData.append(f"Owner: {owner}")
        #
        #     infoData.append(f"Readable: {fileInfo.isReadable()}")
        #     infoData.append(f"Writable: {fileInfo.isWritable()}")
        #     infoData.append(f"Executable: {fileInfo.isExecutable()}")
        #     return "\n".join(infoData)

        # return ""

