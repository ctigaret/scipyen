# $Id: workspaceviewer.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r'''BUG 2026-08-08 09:31:01 FIXME
This does not work as expected when used in ScipyenWindow;
# for now, use a plain QTableview defined in gui.mainwindow module
'''
import sys, os, types, typing
import inspect
import traceback
# import qtpy # noqa
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

if sys.platform == "linux":
    try:
        from qtpy import QtDBus
        __has_qtdbus__ = True

    except: # noqa
        __has_qtdbus__ = False

from core.prog import safewrapper
from core.utilities import standard_obj_summary_headers

class WorkspaceViewer(QtWidgets.QTableView):
    r"""Inherits QTableView with customized drag & drop
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.dragStartPosition = QtCore.QPoint()

        self.mainWindow = None

        self._wspace_headers_ = [k for k in standard_obj_summary_headers if k != "Icon"]

        self.customContextMenuRequested[QtCore.QPoint].connect(
            self.slot_contextMenuRequest)

    @safewrapper
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragStartPosition = event.pos()

        event.accept()

    @safewrapper
    def contextMenuEvent(self, event):
        self.slot_contextMenuRequest(event.pos())

    @safewrapper
    def mouseMoveEvent(self, event):
        # NOTE: 2019-08-10 00:24:01
        # create QDrag objects for each dragged item
        # ignore the DropEvent mimeData in the console ()
        if event.buttons() & QtCore.Qt.LeftButton:
            if (event.pos() - self.dragStartPosition).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                indexList = [i for i in self.selectedIndexes()
                             if i.column() == 0]

                if len(indexList) == 0:
                    return

                if not isinstance(self.mainWindow, ScipyenWindow):
                    return

                varNames = [self.mainWindow.workspaceModel.item(
                    index.row(), 0).text() for index in indexList]

                for varName in varNames:
                    drag = QtGui.QDrag(self)
                    mimeData = QtCore.QMimeData()
                    mimeData.setText(varName)
                    drag.setMimeData(mimeData)
                    dropAction = drag.exec(QtCore.Qt.CopyAction) # noqa

    @Slot("QPoint")
    @safewrapper
    def slot_contextMenuRequest(self, point):
        r"""
        Contex menu requested by workspace viewer
        """
        indexList = self.selectedIndexes()

        if len(indexList) == 0:
            cm = QtWidgets.QMenu("Workspace", self)
            cm.setToolTipsVisible(True)
            clearWs = cm.addAction("Clear Workspace")
            clearWs.setToolTip(
                "Remove all variables from the internal workspace")
            clearWs.setStatusTip(
                "Remove all variables from the internal workspace")
            clearWs.setWhatsThis(
                "Remove all variables from the internal workspace")
            clearWs.triggered.connect(self.mainWindow._slot_clearInternalWorkspace)
            clearWs.hovered.connect(self.mainWindow._slot_showActionStatusMessage_)

            cm.popup(self.mapToGlobal(point))

            return

        # internal_var_indices = [ndx for ndx in indexList
        #                         if self.workspaceModel.item(ndx.row(), standard_obj_summary_headers.index("Workspace")).text() == "Internal"]
        internal_var_indices = [ndx for ndx in indexList
                                if self.model().item(ndx.row(), self._wspace_headers_.index("Workspace")).text() == "Internal"]

        external_var_indices = [
            ndx for ndx in indexList if ndx not in internal_var_indices]

        cm = QtWidgets.QMenu("Selected variables", self)
        # icon = QtGui.QIcon.fromTheme("object")
        icon = guiutils.getIcon("object", "object-group")
        # if icon.isNull():
        #     themeName = guiutils.autoChooseThemeName()
        #     icon = QtGui.QIcon(f":/icons/{themeName}/actions/object-group")
        cm.setIcon(icon)
        cm.setToolTipsVisible(True)

        if len(internal_var_indices):
            self._genInternalVarContextMenu(internal_var_indices, cm)

        if len(external_var_indices):
            self._genExternalVarContextMenu(external_var_indices, cm)

        cm.popup(self.mapToGlobal(point))
