# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


import os, numbers
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut


import numpy as np
import quantities as pq

from core.scipyen_quantities import (arbitrary_unit, checkTimeUnits, unitsConvertible,
                            unitQuantityFromNameOrSymbol, quantity2str, )
from core.datatypes import UnitTypes
from core.strutils import (numbers2str,)
from core.traitcontainers import DataBag
from core.triggerevent import (TriggerEvent, TriggerEventType,)
from core.triggerprotocols import TriggerProtocol
from gui.workspacegui import GuiMessages
from gui.itemmodels.triggerprotocolstablemodel import TriggerProtocolsTableModel

__module_path__ = os.path.abspath(os.path.dirname(__file__))

try:
    from gui.triggerprotocolseditordialog_ui import Ui_TriggerProtocolsEditorDialog


    if os.environ["QT_API"] in ("pyqt5", "pyside2"):
        Ui_TriggerProtocolsEditorDialog, _ = loadUiType(os.path.join(__module_path__, "triggerprotocolseditordialog.ui"), from_imports=True, import_from="gui")

    else:
        Ui_TriggerProtocolsEditorDialog, _ = loadUiType(os.path.join(__module_path__, "triggerprotocolseditordialog.ui"))
except:



class TriggerProtocolsEditorDialog(GuiMessages, QtWidgets.QDialog, Ui_TriggerProtocolsEditorDialog):
    r"""Gateway of GUI actions to triggers protocols management.
    The dialog uses Qt signal/slot communication to redirect GUI requests for
    trigger protocol changes, to caller code which actually implements these
    changes.
    """
    # NOTE: 2020-12-31 11:06:24
    #### BEGIN Qt signals:
    # emitted to inform the caller that GUI action(s) to add new protocol have
    # been enacted
    sig_requestProtocolAdd = Signal(int, name="sig_requestProtocolAdd")
    sig_removeProtocol = Signal(int, name="sig_removeProtocol")
    sig_detectTriggers = Signal(name="sig_detectTriggers")
    sig_clearProtocols = Signal(name="sig_clearProtocols")
    #### END Qt signals

    #                               row, col, txt
    sig_protocolEdited = Signal(int, int, str, name="sig_protocolEdited")

    def __init__(self, parent=None, title="Protocol Editor"):
        super().__init__(parent)
        super(Ui_TriggerProtocolsEditorDialog, self).__init__()

        self._dataModel_ = TriggerProtocolsTableModel(parent=self)
        self._configureUI_()
        if isinstance(title, str) and len(title.strip()):
            self.setWindowTitle(title)


    def _configureUI_(self):
        self.setupUi(self)
        self.addProtocolAction = QAction(QtGui.QIcon.fromTheme("list-add"),
                                                   "Add protocol", self)
        self.addProtocolAction.triggered.connect(self._slot_addProtocol)
        self.removeProtocolAction = QAction(QtGui.QIcon.fromTheme("list-remove"),
                                                      "Remove protocol", self)
        self.removeProtocolAction.triggered.connect(self._slot_removeProtocol)
        self.clearProtocolsAction = QAction(QtGui.QIcon.fromTheme("edit-clear-all"),
                                                      "Clear", self)

        self.clearProtocolsAction.triggered.connect(self._slot_clearProtocols)
        self.detectProtocolsAction = QAction(QtGui.QIcon.fromTheme("tools-wizard"),
                                                       "Detect trigger events", self)
        self.detectProtocolsAction.triggered.connect(self._slot_detectTriggers)

        self.importProtocolsAction = QAction(QtGui.QIcon.fromTheme("document-import"),
                                                      "Import triggers", self)
        self.importProtocolsAction.triggered.connect(self._slot_importProtocols)

        self.loadProtocolsAction = QAction(QtGui.QIcon.fromTheme("document-open"),
                                                     "Load protocols", self)
        self.loadProtocolsAction.triggered.connect(self._slot_loadProtocols)

        self.addProtocolToolButton.clicked.connect(self._slot_addProtocol) # adds a new protocol row
        self.removeProtocolToolButton.clicked.connect(self._slot_removeProtocol) # remove selected protocol row
        self.clearProtocolsToolButton.clicked.connect(self._slot_clearProtocols)

        self.detectProtocolsToolButton.clicked.connect(self._slot_detectTriggers) # detect triggers and generate protocols
        self.importProtocolsToolButton.clicked.connect(self._slot_importProtocols)

        self.protocolTableView.setModel(self._dataModel_)
        self.protocolTableView.horizontalHeader().setSectionsMovable(False)
        self.protocolTableView.verticalHeader().setSectionsMovable(False)
        self.protocolTableView.setAlternatingRowColors(True)
        self.protocolTableView.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.protocolTableView.model().dataChanged.connect(self._slot_dataChanged)
        self.protocolTableView.addAction(self.addProtocolAction)
        self.protocolTableView.addAction(self.removeProtocolAction)
        sep = QAction(self)
        sep.setSeparator(True)
        self.protocolTableView.addAction(sep)
        self.protocolTableView.addAction(self.detectProtocolsAction)
        self.protocolTableView.addAction(self.importProtocolsAction)
        self.protocolTableView.addAction(self.loadProtocolsAction)
        self.protocolTableView.addAction(self.clearProtocolsAction)

        #self.protocolTableView.itemChanged[QtWidgets.QTableWidgetItem].connect(self._slot_protocolTableEdited)

    @Slot(QtWidgets.QTableWidgetItem)
    def _slot_protocolTableEdited(self, item):
        col = item.column()
        row = item.row()
        txt = item.text()

        self.sig_protocolEdited.emit(row, col, txt)

        # columns:
        # 0 = protocol name
        # 1 = presynaptic times
        # 2 = postsynaptic times
        # 3 = photostimulation times
        # 4 = imaging delay
        # 5 = frame indices

        # rows: one for each defined protocol

    @Slot()
    def _slot_addProtocol(self):
        self.sig_requestProtocolAdd.emit()

    @Slot()
    def _slot_protocolAdded(self):
        pass

    @Slot()
    def _slot_loadProtocols(self):
        pass

    @Slot()
    def _slot_removeProtocol(self):
        index = self.protocolTableView.currentRow()
        self.sig_removeProtocol.emit(index)

    @Slot(int)
    def _slot_protocolRemoved(self, index):
        if index < len(self._dataModel_.modelData):
            pass
            #self.protocolTableView.removeRow(index)

    @Slot()
    def _slot_detectTriggers(self):
        r"""Emits sig_detectTriggers signal.

        This should be connected to a slot in the caller widget, which would
        execute (or call the appropriate functions to execute) the trigger event
        detection logic.

        In turn, the (external) trigger detection code should simply set the
        'triggerProtocols' property of this dialog in order to update the
        Protocols table synchronously with the detection.
        """
        self.sig_detectTriggers.emit()

    @Slot()
    def _slot_clearProtocols(self):
        pass

    @Slot()
    def _slot_importProtocols(self):
        pass

    @Slot()
    def _slot_dataChanged(self):
        print("TriggerProtocolsEditorDialog data changed")

    @property
    def triggerProtocols(self):
        return self._dataModel_.modelData

    @triggerProtocols.setter
    def triggerProtocols(self, value):
        #print("\tTriggerProtocolsEditorDialog.triggerProtocols.setter\n", value)
        if isinstance(value, (tuple, list)) and all([isinstance(v, TriggerProtocol) for v in value]):
            self._dataModel_.modelData = value

