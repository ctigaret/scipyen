# -*- coding: utf-8 -*-
# $Id: triggerprotocolstablemodel.py $
# SPDX-FileCopyrightText: 2026 Cezar M. tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""


import os, numbers
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


    from qtpy.QtCore import Signal, Slot, Property
    from qtpy.uic import loadUiType


import numpy as np
import quantities as pq

from core.scipyen_quantities import (arbitrary_unit, checkTimeUnits, unitsConvertible,
                            unitQuantityFromNameOrSymbol, quantity2str, )
from core.datatypes import UnitTypes
from core.strutils import (numbers2str,)
from core.traitcontainers import DataBag
from core.triggerevent import (TriggerEvent, TriggerEventType,)
from core.triggerprotocols import TriggerProtocol
from core.qtutils import (qVariant, QVariantType, fromQVariant)

from gui.workspacegui import GuiMessages

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class TriggerProtocolsTableModel(QtCore.QAbstractTableModel):
    model_columns = ["Name", "Presynaptic", "Postsynaptic", "Photostimulation", "Imaging delay", "Frames"]

    sig_editCompleted = Signal(str, name="sig_editCompleted")

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
        return len(self.model_columns)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if self._data_ is None:
            return qVariant()

        if not index.isValid():
            return qVariant()

        if len(self._data_) == 0 or not all ((isinstance(p, TriggerProtocol) for p in self._data_)):
            return qVariant()

        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole):
            return qVariant()

        # rows: one for each defined protocol
        row = index.row()

        if row >= len(self._data_) or row < 0:
            return qVariant()

        # columns:
        # 0 = protocol name
        # 1 = presynaptic times
        # 2 = postsynaptic times
        # 3 = photostimulation times
        # 4 = imaging delay
        # 5 = frame indices
        col = index.column()

        if col < 0 or col >= len(self.model_columns):
            return qVariant()

        protocol = self._data_[row]

        value = qVariant()
        tip = qVariant()

        if col == 0: # protocol name
            value = protocol.name
            tip = protocol.name

            if len(value.strip()) == 0:
                value = qVariant("Protocol")
                tip = qVariant("Protocol")

        elif col == 1: # presynaptic trigger event
            if isinstance(protocol.presynaptic, TriggerEvent):
                value = qVariant(numbers2str(protocol.presynaptic.times))
                tip = qVariant(numbers2str(protocol.presynaptic.times, show_units=True))

        elif col == 2: # postsynaptic trigger event
            if isinstance(protocol.postsynaptic, TriggerEvent):
                value = qVariant(numbers2str(protocol.postsynaptic.times))
                tip = qVariant(numbers2str(protocol.postsynaptic.times, show_units = True))

        elif col == 3: # photostimulation trigger event
            if isinstance(protocol.photostimulation, TriggerEvent):
                value = qVariant(numbers2str(protocol.photostimulation.times))
                tip = qVariant(numbers2str(protocol.photostimulation.times, show_units = True))

        elif col == 4: # imaging frame trigger event (imaging delay)
            if isinstance(protocol.imagingDelay, np.ndarray):
                value = qVariant(numbers2str(protocol.imagingDelay))
                tip = qVariant(numbers2str(protocol.imagingDelay, show_units=True))

        else: # segment (frame) indices
            value = tip = qVariant(numbers2str(protocol.segmentIndices()))

        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return value
            #return qVariant(value)

        else:
            return tip
            #return qVariant(tip)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole) -> qVariant:
        if len(self._data_) == 0:
            return qVariant()

        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole, QtCore.Qt.AccessibleTextRole):
            return qVariant()

        if orientation == QtCore.Qt.Horizontal: # column header
            return qVariant(self.model_columns[section])

        else: # vertical (rows) header
            return qVariant("%d" % section)

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

        value = fromQVariant(value)

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
                            event_times = np.array(val)

                        elif isinstance(val, numbers.Number):
                            event_times = np.array([val])

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
                    except: # noqa
                        return False

        else:
            return False

        self.sig_editCompleted.emit(value)

        return True

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | super().flags(index)

    @property
    def modelData(self):
        r"""The reference to a protocol list.
        """
        return self._data_

    @modelData.setter
    def modelData(self, value):
        #print("\tTriggerProtocolsTableModel.modelData.setter\n", value)
        if isinstance(value, list) and all([isinstance(p, TriggerProtocol) for p in value]):
            self.beginResetModel()
            self._data_ = value
            self.endResetModel()
