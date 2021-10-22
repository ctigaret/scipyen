# -*- coding: utf-8 -*-
import os
from numbers import (Number, Real,)

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType

import numpy as np
import quantities as pq

from core.quantities import arbitrary_unit
from core.datatypes import (check_time_units, units_convertible,
                            unit_quantity_from_name_or_symbol, UnitTypes, )
from core.strutils import (quantity2str, numbers2str,)
from core.traitcontainers import DataBag
from core.triggerevent import (TriggerEvent, TriggerEventType,)
from core.triggerprotocols import TriggerProtocol
from gui.workspacegui import GuiMessages

__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_ProtocolEditorDialog, QDialog = loadUiType(os.path.join(__module_path__, "protocoleditordialog.ui"), from_imports=True, import_from="gui")

class TriggerProtocolsModel(QtCore.QAbstractTableModel):
    model_columns = ["Name", "Presynaptic", "Postsynaptic", "Photostimulation", "Imaging delay", "Frames"]
    
    editCompleted = pyqtSignal(str, name="editCompleted")
    
    def __init__(self, protocols=None, parent=None):
        super().__init__(parent)
        
        # NOTE: 2020-12-31 11:34:50 passed by reference:
        # since this is a list, chamges to self._data_ are reflected in protocols
        # in the caller
        if isinstance(protocols, list) and all ((isinstance(p, TriggerProtocol) for p in protocols)):
            self._data_ = protocols 
            
        else:
            self._data_ = list() # starts with an empty protocols list
        
    def rowCount(self, parent):
        return len(self._data_)
    
    def columnCount(self, parent):
        return 6
    
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if self._data_ is None:
            return QtCore.QVariant()
            
        if not index.isValid():
            return QtCore.QVariant()

        if len(self._data_) == 0 or not all ((isinstance(p, TriggerProtocol) for p in self._data_)):
            return QtCore.QVariant()
        
        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole):
            return QtCore.QVariant()
        
        # rows: one for each defined protocol
        row = index.row()

        if row >= len(self._data_) or row < 0:
            return QtCore.QVariant()
        
        # columns:
        # 0 = protocol name
        # 1 = presynaptic times
        # 2 = postsynaptic times
        # 3 = photostimulation times
        # 4 = imaging delay
        # 5 = frame indices
        col = index.column()
        
        if col < 0 or col >= len(self.model_columns):
            return QtCore.QVariant()
        
        protocol = self._data_[row]
        
        value = QtCore.QVariant()
        tip = QtCore.QVariant()
        
        if col == 0: # protocol name
            value = protocol.name
            tip = protocol.name
            
            if len(value.strip()) == 0:
                value = QtCore.QVariant("Protocol")
                tip = QtCore.QVariant("Protocol")
                
        elif col == 1: # presynaptic trigger event
            if isinstance(protocol.presynaptic, TriggerEvent): 
                value = QtCore.QVariant(numbers2str(protocol.presynaptic.times))
                tip = QtCore.QVariant(numbers2str(protocol.presynaptic.times, show_units=True))
                
        elif col == 2: # postsynaptic trigger event
            if isinstance(protocol.postsynaptic, TriggerEvent):
                value = QtCore.QVariant(numbers2str(protocol.postsynaptic.times))
                tip = QtCore.QVariant(numbers2str(protocol.postsynaptic.times, show_units = True))
            
        elif col == 3: # photostimulation trigger event
            if isinstance(protocol.photostimulation, TriggerEvent):
                value = QtCore.QVariant(numbers2str(protocol.photostimulation.times))
                tip = QtCore.QVariant(numbers2str(protocol.photostimulation.times, show_units = True))
            
        elif col == 4: # imaging frame trigger event (imaging delay)
            if isinstance(protocol.imagingDelay, np.ndarray):
                value = QtCore.QVariant(numbers2str(protocol.imagingDelay))
                tip = QtCore.QVariant(numbers2str(protocol.imagingDelay, show_units=True))
            
        else: # segment (frame) indices
            value = tip = QtCore.QVariant(numbers2str(protocol.segmentIndices()))
            
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return value
            #return QtCore.QVariant(value)
        
        else:
            return tip
            #return QtCore.QVariant(tip)
        
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if len(self._data_) == 0:
            return QtCore.QVariant()
        
        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole):
            return QtCore.QVariant()
        
        if orientation == QtCore.Qt.Horizontal: # column header
            return QtCore.QVariant(self.model_columns[section])
        
        else: # vertical (rows) header
            return QtCore.QVariant("%d" % section)
        
    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.EditRole:
            return False
            
        row = index.row()
        
        if row < 0 or row >= len(self._data_):
            return False
        
        col = index.column()
        
        if col < 0 or col >= len(self.model_columns):
            return False
        
        protocol = self._data_[row]
        
        attribute = self.model_columns[col].lower()
        
        if attribute == "imaging delay":
            event_type = "imaging"
            attribute = "imagingDelay"
            
        else:
            event_type = attribute
            
        if not hasattr(protocol, attribute):
            return False
        
        target = getattr(protocol, attribute)
        
        if isinstance(value, QtCore.QVariant()) or hasattr(value, "value"):
            value = value.value()
            
        if isinstance(value, str):
            # deleting the time stamps for a trigger event should remove that 
            # trigger event type from the protocol
            if attribute == "name":
                if len(value.strip()) == 0: 
                    protocol.name = "Protocol_%d" % row # never have a nameless protocol
                else:
                    setattr(protocol, target, value)
        
            else:
                if isinstance(target, TriggerEvent):
                    labels = target.labels
                    
                    # ensure all times have same labels for the event
                    if len(labels) > 1:
                        labels = str(np.unique(labels)[0])
                        
                    else:
                        labels = str(labels[0])
                    
                    if len(value.strip()) == 0:
                        setattr(protocol, target, None) # remove protocol altogether
                        
                    else:
                        val = eval(value)
                        if isinstance(val, (tuple, list)):
                            event_times = np.array(v)
                            
                        elif isinstance(val, Number):
                            event_times = np.array([v])
                            
                        event = TriggerEvent(times = event_times * pq.s,
                                             event_type=event_type, labels=labels)
                        
                        setattr(protocol, target, event)
                        
                elif isinstance(target, pq.Quantity):
                    try:
                        assert(target is protocol.imagingDelay)
                        # by definition this is imaging delay, and should be 
                        # synchronized to the acquisition event.
                        # NOTE: 2020-12-31 17:28:59
                        # see NOTE: 2020-12-31 17:29:19 in triggerprotocols.py:
                        # as things currently stand, the acquisition event is
                        # ambiguous - it may mean imaging frame trigger, 
                        # imaging line trigger, or even an external trigger for
                        # electrophysiology
                        acq = protocol.acquisition
                        event_type = acq.event_type
                        labels = acq.labels
                        if len(labels)>1:
                            labels = str(np.unique(labels)[0])
                            
                        else:
                            labels = str(labels[0])
                            
                        if len(value.strip()) == 0:
                            protocol.imagingDelay = 0
                            protocol.acquisition = None
                            
                        else:
                            val = eval(value) * pq.s
                            protocol.imagingDelay = val
                            protocol.imagingFrameTrigger = TriggerEvent(times=val,
                                                                        event_type = event_type,
                                                                        labels = labels)
                    except:
                        return False
                    
        else:
            return False
        
        self.editCompleted.emit(value)
        
        return True
    
    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | super().flags(index)
    
    @property
    def modelData(self):
        """The reference to a protocol list.
        """
        return self._data_
    
    @modelData.setter
    def modelData(self, value):
        #print("\tTriggerProtocolsModel.modelData.setter\n", value)
        if isinstance(value, list) and all([isinstance(p, TriggerProtocol) for p in value]):
            self.beginResetModel()
            self._data_ = value
            self.endResetModel()
            
            #topLeft = self.createIndex(0,0)
            #if len(self._data_):
                #bottomRight = self.createIndex(len(self._data_)-1, len(self.model_columns)-1)
                
            #else:
                #bottomRight = topLeft
                
            #self.dataChanged.emit(topLeft, bottomRight, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
            
class ProtocolEditorDialog(GuiMessages, QDialog, Ui_ProtocolEditorDialog):
    """Gateway of GUI actions to triggers protocols management.
    The dialog uses Qt signal/slot communication to redirect GUI requests for
    trigger protocol changes, to caller code which actually implements these 
    changes.
    """
    # NOTE: 2020-12-31 11:06:24
    #### BEGIN Qt signals:
    # emitted to inform the caller that GUI action(s) to add new protocol have 
    # been enacted
    sig_requestProtocolAdd = pyqtSignal(int, name="sig_requestProtocolAdd")
    sig_removeProtocol = pyqtSignal(int, name="sig_removeProtocol")
    sig_detectTriggers = pyqtSignal(name="sig_detectTriggers")
    sig_clearProtocols = pyqtSignal(name="sig_clearProtocols")
    #### END Qt signals
    
    #                               row, col, txt
    sig_protocolEdited = pyqtSignal(int, int, str, name="sig_protocolEdited")
    
    def __init__(self, parent=None, title="Protocol Editor"):
        super().__init__(parent)
        self._dataModel_ = TriggerProtocolsModel(parent=self)
        self._configureUI_()
        if isinstance(title, str) and len(title.strip()):
            self.setWindowTitle(title)
            
        
    def _configureUI_(self):
        self.setupUi(self)
        self.addProtocolAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("list-add"),
                                                   "Add protocol", self)
        self.addProtocolAction.triggered.connect(self._slot_addProtocol)
        self.removeProtocolAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("list-remove"),
                                                      "Remove protocol", self)
        self.removeProtocolAction.triggered.connect(self._slot_removeProtocol)
        self.clearProtocolsAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-clear-all"),
                                                      "Clear", self)
        
        self.clearProtocolsAction.triggered.connect(self._slot_clearProtocols)
        self.detectProtocolsAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("tools-wizard"),
                                                       "Detect trigger events", self)
        self.detectProtocolsAction.triggered.connect(self._slot_detectTriggers)
        
        self.importProtocolsAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-import"),
                                                      "Import triggers", self)
        self.importProtocolsAction.triggered.connect(self._slot_importProtocols)
        
        self.loadProtocolsAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-open"),
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
        sep = QtWidgets.QAction(self)
        sep.setSeparator(True)
        self.protocolTableView.addAction(sep)
        self.protocolTableView.addAction(self.detectProtocolsAction)
        self.protocolTableView.addAction(self.importProtocolsAction)
        self.protocolTableView.addAction(self.loadProtocolsAction)
        self.protocolTableView.addAction(self.clearProtocolsAction)
        
        #self.protocolTableView.itemChanged[QtWidgets.QTableWidgetItem].connect(self._slot_protocolTableEdited)
        
    @pyqtSlot(QtWidgets.QTableWidgetItem)
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
        
    @pyqtSlot()
    def _slot_addProtocol(self):
        self.sig_requestProtocolAdd.emit()
        
    @pyqtSlot()
    def _slot_protocolAdded(self):
        pass
    
    @pyqtSlot()
    def _slot_loadProtocols(self):
        pass
    
    @pyqtSlot()
    def _slot_removeProtocol(self):
        index = self.protocolTableView.currentRow()
        self.sig_removeProtocol.emit(index)
        
    @pyqtSlot(int)
    def _slot_protocolRemoved(self, index):
        if index < len(self._dataModel_.modelData):
            pass
            #self.protocolTableView.removeRow(index)
    
    @pyqtSlot()
    def _slot_detectTriggers(self):
        """Emits sig_detectTriggers signal.
        
        This should be connected to a slot in the caller widget, which would
        execute (or call the appropriate functions to execute) the trigger event 
        detection logic.
        
        In turn, the (external) trigger detection code should simply set the 
        'triggerProtocols' property of this dialog in order to update the 
        Protocols table synchronously with the detection.
        """
        self.sig_detectTriggers.emit()
        
    @pyqtSlot()
    def _slot_clearProtocols(self):
        pass
    
    @pyqtSlot()
    def _slot_importProtocols(self):
        pass
    
    @pyqtSlot()
    def _slot_dataChanged(self):
        print("ProtocolEditorDialog data changed")
    
    @property
    def triggerProtocols(self):
        return self._dataModel_.modelData
    
    @triggerProtocols.setter
    def triggerProtocols(self, value):
        #print("\tProtocolEditorDialog.triggerProtocols.setter\n", value)
        if isinstance(value, (tuple, list)) and all([isinstance(v, TriggerProtocol) for v in value]):
            self._dataModel_.modelData = value
            
