# -*- coding: utf-8 -*-
# $Id: neo_widgets.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import sys, os, typing, types, warnings, math, cmath
import numbers
import numpy as np
import quantities as pq
import neo

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
__has_qtdbus__ = False

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

try:
    from qtpy import QtDBus
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

from gui.painting_shared import (FontStyleType, standardQtFontStyles,
                                 FontWeightType, standardQtFontWeights)

from gui import quickdialog as qd
from gui.guiutils import (DisplayHint,
    InftyDoubleValidator, ComplexValidator, validatorString,
    get_elided_text, get_text_width)

from core import datatypes as dt
from core import scipyen_quantities as scq
from core import strutils as strutils
from core.triggerevent import (DataMark, MarkType,
                               TriggerEvent, TriggerEventType)

Ui_SimpleTriggerEventWidget, QWidget = loadUiType(
    os.path.join(__module_path__,
                 "simpletriggereventwidget.ui")
    )

class SimpleTriggerEventWidget(Ui_SimpleTriggerEventWidget, QWidget):
    r"""A simple widget for editing DataMark, TriggerEvents and neo.Event objects.
"""
    supported_types = dict(map(lambda t: (t.__name__, t),
                               (neo.Event, DataMark, TriggerEvent)
                               )
                        )

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None,
                 obj:typing.Optional[
                     typing.Union[neo.Event, DataMark, TriggerEvent]
                     ] = None):
        QWidget.__init__(self, parent=parent)

        if obj is not None and not isinstance(obj, (neo.Event, DataMark, TriggerEvent)):
            scipywarn(f"This widget does not support objects of type {type(obj).__name__}")
            self._data_ = None
        else:
            self._data_ = obj

        self._event_type_ = None
        self._event_name_ = None
        self._event_labels_ = None

        if self._data_ is not None:
            self._units_ = self._data_.times.units
            self._times_ = self._data_.times.magnitude
            self._data_type_ = type(self._data_)
            self._event_name_ = self._data_.name
            self._event_labels_ = self._data_.labels
        else:
            self._units_ = None
            self._times_ = None
            self._data_type_ = None

        if isinstance(self._data_, (DataMark, TriggerEvent)):
            self._event_type_ = self._data_.type

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self.setEventClassAction = QtGui.QAction("Event class")
        self.setEventClassAction.triggered.connect(self._slot_setEventClass)
        self.setEventTypeAction = QtGui.QAction("Event type")
        self.setEventTypeAction.triggered.connect(self._slot_setEventType)
        self.setEventDomanUnitsAction = QtGui.QAction("Units")
        self.setEventDomanUnitsAction.triggered.connect(self._slot_setEventUnits)
        # self.editTimesAction = QtGui.QAction("Edit...")
        # self.editTimesAction.triggered.connect(self._slot_editTimes)
        if isinstance(self._times_, np.ndarray):
            if dt.is_vector(self._times_):
                self.timesLineEdit.setText(strutils.numbers2str(self._times_))
                self.timesLineEdit.setReadOnly(False)
            else:
                self.timesLineEdit.setText(f"Array with shape {self._times_.shape}")
                self.timesLineEdit.setReadOnly(True)
            # NOTE: 2026-03-14 09:21:01
            # when performing the inverse conversion, KEEP IN MIND THE FOLLOWING:
            # by default, strutils.numbers2str():
            #
            # • produces a sequence of comma+space—separated numbers
            #   e.g. '0.2, 0.21'
            #
            # • uses the dot (.) as decimal separator
            #   and comma (,) as thousands separator
            #
            # • uses the 'general' number format ('g' flag)
            #
            # • uses a precision of 5 (i.e. 5 digits to the right of the decimal
            #   point) — WARNING: this WILL introduce a loss of precision when
            #   converting back to numbers
            #
            # • for Quantity objects, it does NOT represent their units
            #
            # In addition, numpy arrays are flatten()-ed first!

        self.timesLineEdit.textChanged.connect(self._slot_timesChanged)

    def contextMenuEvent(self, evt: QtGui.QContextMenuEvent):
        if self._data_ is not None:
            menu = QtWidgets.QMenu(self)
            if self.timesLineEdit.isReadOnly():
                editTimesAction = QtGui.QAction("Edit...")
                editTimesAction.triggered.connect(self._slot_editTimes)
                menu.addAction(editTimesAction)
                menu.addSeparator()

            menu.addAction(self.setEventClassAction)
            if isinstance(self._data_, (DataMark, TriggerEvent)):
                menu.addAction(self.setEventTypeAction)
                menu.addAction(self.setEventDomanUnitsAction)
            menu.exec(evt.globalPos())

            evt.setAccepted(True)

    @Slot()
    def _slot_editTimes(self):
        from gui.widgets.tableeditorwidget import TableEditorWidget
        if not self.timesLineEdit.isReadOnly():
            return

        if not isinstance(self._times_, np.ndarray):
            return

        dlg = qd.QuickDialog(self, title = "Edit values")
        te = TableEditorWidget(dlg)
        te.setValue(self._times_)
        dlg.addWidget(te)
        dlg.resize(-1,-1)

        if dlg.exec():
            self._times_ = te.value()
        self._createEvent_()

    @Slot(str)
    def _slot_timesChanged(self, value:str):
        if len(value.strip()) == 0:
            self._times_ = None

        else:
            v = eval(value)
            print(f"{self.__class__.__name__}._slot_timesChanged: v = {v}")
            if isinstance(v, (tuple, list)):
                self._times_ = np.array(v)
            elif isinstance(v, numbers.Number):
                self._times_ = np.array([v])

        print(f"{self.__class__.__name__}._slot_timesChanged: self._times_ = {self._times_}")
        self._createEvent_()

    @Slot()
    def _slot_setEventClass(self):
        dlg = qd.QuickDialog(self, title="Choose Event Class")
        cb = qd.QuickDialogComboBox(dlg, "Class")
        cb.setItems(list(self.supported_types.keys()))
        if self._data_ is None:
            cb.setCurrentIndex(0)
        else:
            ndx = list(self.supported_types.values()).index(type(self._data_))
            cb.setCurrentIndex(ndx)

        dlg.addWidget(cb)
        dlg.resize(-1,-1)
        if dlg.exec():
            self._data_type_ = self.supported_types[cb.text()]

        self._createEvent_()

    @Slot()
    def _slot_setEventType(self):
        dlg = qd.QuickDialog(self, title="Choose Event Type")
        cb = qd.QuickDialogComboBox(dlg, "Type")
        if isinstance(self._data_, TriggerEvent):
            evt_types = list(TriggerEventType.names())
        elif isinstance(self._data_, DataMark):
            evt_types = list(MarkType.names())
        else:
            return
        cb.setItems(evt_types)

        if isinstance(self._event_type_, (MarkType, TriggerEventType)):
            cb.setCurrentIndex(evt_types.index(self._event_type_.name))

        dlg.addWidget(cb)
        dlg.resize(-1,-1)

        if dlg.exec():
            evt_typename = cb.text()

        if isinstance(self._data_, DataMark):
            self._event_type_ = getattr(MarkType, evt_typename)
        else:
            self._event_type_ = getattr(TriggerEventType, evt_typename)

        self._createEvent_()

    @Slot()
    def _slot_setEventUnits(self):
        from gui.widgets.small_widgets import QuantityChooserWidget
        dlg = qd.QuickDialog(self, title="Choose Event Units")
        if isinstance(self._units_, pq.Quantity):
            units = self._units_
        elif self._data_ is None:
            units = pq.s
        else:
            units = self._data_.units
        qcw = QuantityChooserWidget(dlg, unit = units)
        dlg.addWidget(qcw)
        dlg.resize(-1,-1)
        if dlg.exec():
            self._units_ = qcw.value()

        self._createEvent_()

    def _createEvent_(self):
        if (isinstance(self._data_type_, type)
            and issubclass(self._data_type_, neo.Event)
            ):
            if self._data_type_ in (DataMark, TriggerEvent):
                if self._units_ is None:
                    units = pq.s
                else:
                    units = self._units_

            elif self._data_type_ is neo.Event:
                if self._units_ is None:
                    units = pq.s
                elif scq.unitFamilyName(self._units_) == "Time":
                    units = self._units_
                else:
                    raise ValueError("Neo Events only support time units")

            if (not isinstance(self._times_, np.ndarray)
                and (not isinstance(self._times_, typing.Sequence)
                    or not all(isinstance(v, numbers.Number) for v in self._times_)
                    )
                ):
                self._times_ = None

            if isinstance(self._times_, np.ndarray):
                if (self._times_.ndim > 1
                    and any(v > 1 for v in self._times_.shape[1:])):
                    if self._data_type_ in (neo.Event, TriggerEvent):
                        raise ValueError("neo.Event and TriggerEvent can only take 1D arrays")



            evt = self._data_type_(self._times_, units=self._units_)
            if isinstance(evt, TriggerEvent):
                if isinstance(self._event_type_, TriggerEventType):
                    evt.type = self._event_type_
                elif self._event_type_ is not None:
                    raise TypeError(f"Cannot assign a {type(self._event_type_.__name__)} as type of {type(evt).__name__}")

            elif isinstance(evt, DataMark):
                if isinstance(self._event_type_, MarkType):
                    evt.type = self._event_type_
                elif self._event_type_ is not None:
                    raise TypeError(f"Cannot assign a {type(self._event_type_).__name__} as type of {type(evt).__name__}")

            self._data_ = evt

    def value(self) -> typing.Optional[typing.Union[neo.Event, DataMark, TriggerEvent]]:
        return self._data_

    def setValue(self,
                 val: typing.Optional[
                     typing.Union[neo.Event, DataMark, TriggerEvent]
                     ] = None):
        self._data_ = val
        if isinstance(self._data_, neo.Event):
            self._data_type_ = type(val)
            self._times_ = self._data_.times.magnitude
            self._units_ = self._data_.times.units
            if isinstance(self._data_, (DataMark, TriggerEvent)):
                self._event_type_ = self._data_.type

        else:
            self._data_type_ = None
            self._times_ = None
            self._units_ = None
            self._event_type_ = None




