# $Id: scriptmanager.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import sys, os, types, typing

import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False

if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    # import PySide6
    # from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut

else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

        # from qtpy.uic import loadUiType

        QAction = QtWidgets.QAction
        QActionGroup = QtWidgets.QActionGroup
        QShortcut = QtWidgets.QShortcut

        __has_qtdbus__ = False

try:
    from qtpy import QtDBus
    __has_qtdbus__ = True

except: # noqa
    __has_qtdbus__ = False

from core.prog import (timefunc, timemethod, safewrapper)
from core.scipyen_config import (saveWindowSettings, loadWindowSettings, ) # noqa

from gui.scriptmanagerwindow_ui import Ui_ScriptManagerWindow
from gui.workspacegui import WorkspaceGuiMixin
from iolib import pictio as pio
r"""
"""
class ScriptManager(QtWidgets.QMainWindow, Ui_ScriptManagerWindow, WorkspaceGuiMixin):
    signal_forgetScripts = Signal(object)
    signal_executeScript = Signal(str)
    signal_importScript = Signal(str)
    signal_pasteScript = Signal(str)
    signal_editScript = Signal(str)
    signal_openScriptFolder = Signal(str)
    signal_pythonFileReceived = Signal(str, QtCore.QPoint)
    signal_pythonFileAdded = Signal(str)
    signal_scriptManagerClosed = Signal()

    # NOTE recently run scripts is managed by ScipyenWindow instance mainWindow
    # FIXME 2021-09-18 14:16:14 Change this so that it is managed instead by
    # ScriptManager
    # We then need to connect pasting/dropping script file onto Scipyen mainWindow
    # or the internal console to script execution and adding of script file to
    # the internal scripts list  here.

    # @timemethod
    def __init__(self, parent=None, scipyenWindow=None):
        super(ScriptManager, self).__init__(parent) # noqa
        super(Ui_ScriptManagerWindow, self).__init__()
        WorkspaceGuiMixin.__init__(self, parent=parent, scipyenWindow=scipyenWindow)

        self._configureUI_()

        self.setWindowTitle("Scipyen Script Manager")

        self.loadSettings()

    # @timemethod
    def _configureUI_(self):
        self.setupUi(self)
        addScript = self.menuScripts.addAction("Add scripts...")
        addScript.triggered.connect(self.slot_addScripts)
        self.scriptsTable.customContextMenuRequested[QtCore.QPoint].connect(
            self.slot_customContextMenuRequested)
        self.scriptsTable.cellDoubleClicked[int, int].connect(
            self.slot_cellDoubleClick)
        self.scriptsTable.setSortingEnabled(True)
        # self.scriptsTable.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.acceptDrops = True
        self.scriptsTable.acceptDrops = True

    def closeEvent(self, evt):
        self.saveSettings()
        evt.accept()
        self.close()

        evt.accept()
        # self.signal_scriptManagerClosed.emit()

    def loadSettings(self):
        loadWindowSettings(self.qsettings, self)

    def saveSettings(self):
        saveWindowSettings(self.qsettings, self)

    def setData(self, scriptsDict):
        if not isinstance(scriptsDict, dict):
            return

        self.scriptsTable.clearContents()

        if len(scriptsDict) == 0:
            return

        self.scriptsTable.setRowCount(len(scriptsDict))

        for k, (key, value) in enumerate(scriptsDict.items()):
            # print(f"ScriptManager.setData {k}: key={key}, value={value}")
            path_item = QtWidgets.QTableWidgetItem(key)
            path_item.setToolTip(key)

            script_item = QtWidgets.QTableWidgetItem(value)
            script_item.setToolTip(value)

            self.scriptsTable.setItem(k, 0, script_item)
            self.scriptsTable.setItem(k, 1, path_item)

        # self.scriptsTable.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.scriptsTable.resizeColumnToContents(0)

    @safewrapper
    def dragEnterEvent(self, event):
        event.acceptProposedAction()
        event.accept()

    @safewrapper
    def dropEvent(self, evt):
        if evt.mimeData().hasUrls():
            urls = evt.mimeData().urls()
            for url in urls:
                if (url.isRelative() or url.isLocalFile()) and os.path.isfile(url.path()):
                    # check if this is a python source file
                    mimeType = QtCore.QMimeDatabase().mimeTypeForFile(QtCore.QFileInfo(url.path()))
                    # print(mimeType.name())
                    if all([s in mimeType.name() for s in ("text", "python")]):
                        self.signal_pythonFileAdded.emit(url.path())

            # if len(urls) == 1 and (urls[0].isRelative() or urls[0].isLocalFile()) and os.path.isfile(urls[0].path()):
                # check if this is a python source file
                # mimeType = QtCore.QMimeDatabase().mimeTypeForFile(QtCore.QFileInfo(urls[0].path()))
                # print(mimeType.name())
                # if all([s in mimeType.name() for s in ("text", "python")]):
                    # self.signal_pythonFileAdded.emit(urls[0].path())

        evt.accept()

    def clear(self):
        self.scriptsTable.clearContents()
        self.scriptsTable.setRowCount(0)

    @property
    def scriptsCount(self):
        return self.scriptsTable.rowCount()

    @property
    def scriptNames(self):
        return [self.scriptsTable.item(row, 0).text() for row in range(self.scriptsTable.rowCount())]

    @property
    def scriptFileNames(self):
        return [self.scriptsTable.item(row, 1).text() for row in range(self.scriptsTable.rowCount())]

    @Slot("QPoint")
    @safewrapper
    def slot_customContextMenuRequested(self, pos):
        items = self.scriptsTable.selectedItems()

        cm = QtWidgets.QMenu("Open Scripts Manager", self)
        # actions = list()

        if len(items):
            if len(items) == 1:
                execItem = cm.addAction("Run")
                execItem.setToolTip("Execute selected script")
                execItem.triggered.connect(self.slot_executeScript)

                # actions.append(execItem)

                pasteItem = cm.addAction("Paste in Console")
                pasteItem.setToolTip("Paste script contents in console")
                pasteItem.triggered.connect(self.slot_teleportScript)

                # actions.append(pasteItem)

                editItem = cm.addAction("Edit")
                editItem.setToolTip(
                    "Edit script in system's default text editor")
                editItem.triggered.connect(self.slot_editScript)

                openFolderItem = cm.addAction("Open Containing Folder")
                openFolderItem.setToolTip("Open Containing Folder")
                openFolderItem.triggered.connect(self.slot_openScriptFolder)

            cm.addSeparator()

            delItems = cm.addAction("Forget")
            delItems.setToolTip("Forget selected scripts")
            delItems.triggered.connect(self.slot_forgetScripts)
            # actions.append(delItems)

            clearAction = cm.addAction("Forget All")
            clearAction.setToolTip("Forget All")
            clearAction.triggered.connect(self.slot_forgetAll)

        # actions.append(clearAction)
        cm.addSeparator()
        registerScript = cm.addAction("Add script...")
        registerScript.triggered.connect(self.slot_addScript)

        cm.popup(self.scriptsTable.mapToGlobal(pos))

    @Slot(int, int)
    @safewrapper
    def slot_cellDoubleClick(self, row, col):
        item = self.scriptsTable.item(row, 1)

        self.signal_executeScript.emit(item.text())

    @Slot()
    @safewrapper
    def slot_addScript(self):
        targetDir = os.getcwd()
        fileFilter = "Python script (*.py)"
        fileName = self.chooseFile(caption=u"Add python script",
                                   fileFilter="Python script (*.py)",
                                   targetDir=targetDir)

        # print(f"ScriptManager.slot_addScript fileName: { fileName}" )

        if isinstance(fileName, tuple):
            # NOTE: PyQt5 QFileDialog.getOpenFileName returns a tuple (fileName, filter string)
            fileName, fileFilter = fileName

        if pio.checkFileReadAccess(fileName):
            mime_file_type = pio.getMimeAndFileType(fileName)
            # print(f"ScriptManager.slot_addScript {mime_file_type}")
            # for s in mime_file_type:
            # print(f"ScriptManager.slot_addScript s: {s}, type: {type(s).__name__}")
            if any("python" in s for s in mime_file_type if isinstance(s, str)):
                self.signal_pythonFileAdded.emit(fileName)

            elif any("text" in s for s in mime_file_type if isinstance(s, str)) and os.path.splitext(fileName)[-1] == ".py":
                self.signal_pythonFileAdded.emit(fileName)

    @Slot()
    @safewrapper
    def slot_addScripts(self):
        targetDir = os.getcwd()

        # NOTE: returns a tuple (path list, filter)
        # fileNames, fileFilter = QtWidgets.QFileDialog.getOpenFileNames(self, caption=u"Run python script", filter="Python script (*.py)", directory = targetDir)

        fn, fl = self.chooseFile(caption=u"Add python scripts",
                                 filter="Python script (*.py)",
                                 targetDir=targetDir,
                                 single=False)

        if pio.checkFileReadAccess(fn):
            for fileName in fn:
                mft = pio.getMimeAndFileType(fileName)
                if any("python" in s for s in mft):
                    self.signal_pythonFileAdded.emit(fileName)

    @Slot()
    @safewrapper
    def slot_forgetScripts(self):
        if len(self.scriptsTable.selectedItems()) == 0:
            return

        rows = list(set([i.row() for i in self.scriptsTable.selectedItems()]))

        items = [self.scriptsTable.item(r, 1).text() for r in rows]

        for r in rows:
            self.scriptsTable.removeRow(r)

        self.signal_forgetScripts.emit(items)

    @Slot()
    @safewrapper
    def slot_forgetAll(self):
        items = [self.scriptsTable.item(r, 1).text()
                 for r in range(self.scriptsTable.rowCount())]

        self.scriptsTable.clearContents()
        self.scriptsTable.setRowCount(0)

        self.signal_forgetScripts.emit(items)

    @Slot()
    @safewrapper
    def slot_executeScript(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        item = self.scriptsTable.item(row, 1).text()

        self.signal_executeScript.emit(item)

    @Slot()
    @safewrapper
    def slot_importAsModule(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        item = self.scriptsTable.item(row, 1).text()

        self.signal_importScript.emit(item)

    @Slot()
    @safewrapper
    def slot_editScript(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        fileName = self.scriptsTable.item(row, 1).text()

        self.scipyenWindow.slot_systemEditScript(fileName)

        # self.signal_editScript.emit(fileName)

    @Slot()
    @safewrapper
    def slot_openScriptFolder(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        item = self.scriptsTable.item(row, 1).text()

        self.signal_openScriptFolder.emit(item)

    @Slot()
    @safewrapper
    def slot_teleportScript(self):
        if len(self.scriptsTable.selectedItems()) != 1:
            return

        row = [i.row() for i in self.scriptsTable.selectedItems()][0]

        item = self.scriptsTable.item(row, 1).text()

        self.signal_pasteScript.emit(item)

