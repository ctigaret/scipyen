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
from gui.guiutils import (DisplayHint, NumericStringValidator,
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
                     ] = None,
                 precision: typing.Optional[int] = None):

        if not isinstance(parent, QtWidgets.QWidget):
            if obj is None and isinstance(parent, (neo.Event, DataMark, TriggerEvent)):
                obj = parent
            parent = None

        if not isinstance(obj, (neo.Event, DataMark, TriggerEvent, type(None))):
            raise TypeError(f"Unsupported data: {type(obj).__name__}")

        QWidget.__init__(self, parent=parent)

        if obj is not None and not isinstance(obj, (neo.Event, DataMark, TriggerEvent)):
            scipywarn(f"This widget does not support objects of type {type(obj).__name__}")
            self._data_ = None
        else:
            self._data_ = obj

        self._event_type_ = None
        self._event_name_ = None
        self._event_labels_ = None

        self._precision_ = precision if (isinstance(precision, int) and precision > 0) else None

        # self._data_type_change_pending_ = None

        if self._data_ is not None:
            self._units_ = self._data_.times.units
            self._times_ = self._data_.times.magnitude
            self._data_class_ = type(self._data_)
            self._event_name_ = self._data_.name
            self._event_labels_ = self._data_.labels
        else:
            self._units_ = None
            self._times_ = None
            self._data_class_ = None

        if isinstance(self._data_, (DataMark, TriggerEvent)):
            self._event_type_ = self._data_.type

        self._configureUI_()

        if isinstance(self._data_, neo.Event):
            self._update_()

    def _configureUI_(self):
        self.setupUi(self)
        self.setEventClassAction = QtGui.QAction("Event Class")
        self.setEventClassAction.triggered.connect(self._slot_setEventClass)
        self.setEventTypeAction = QtGui.QAction("Event Type")
        self.setEventTypeAction.triggered.connect(self._slot_setEventType)
        self.setEventDomanUnitsAction = QtGui.QAction("Event Units")
        self.setEventDomanUnitsAction.triggered.connect(self._slot_setEventUnits)
        self.nameLabelsAction = QtGui.QAction("Name and labels")
        self.nameLabelsAction.triggered.connect(self._slot_setNameLabels)
        self.timesLineEdit.undoAvailable=True
        self.timesLineEdit.redoAvailable=True
        self.timesLineEdit.setClearButtonEnabled(True)
        self.timesLineEdit.installEventFilter(self)
        self.timesLineEdit.setToolTip("Right click for options")
        self.timesLineEdit.setValidator(NumericStringValidator(self))

        self.timesLineEdit.textChanged.connect(self._slot_timesChanged)
        self.timesLineEdit.sig_lazy.connect(self._slot_lazyTextChanges)

    def _update_(self):
        signalBlockers = QtCore.QSignalBlocker(self.timesLineEdit)
        if isinstance(self._times_, np.ndarray):
            # if not isinstance(self._precision_, int):
            #     pass
            if dt.is_vector(self._times_) or self._times_.ndim == 0:
                text = scq.quantity2str(self._times_ * self._units_)
                # text = ", ".join(list(map(lambda q: scq.quantity2str(q, precision=self._precision_), self._data_.times)))
                self.timesLineEdit.setText(text)
                # self.timesLineEdit.setText(strutils.numbers2str(self._times_))
                self.timesLineEdit.setReadOnly(False)
            else:
                self.timesLineEdit.setText(f"Array with shape {self._times_.shape}")
                # self.timesLineEdit.setReadOnly(True)
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


    def _createContextMenu_(self) -> QtWidgets.QMenu:
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.setEventClassAction)

        if (isinstance(self._data_, (DataMark, TriggerEvent))
            ):
            menu.addAction(self.setEventTypeAction)

            if (
                isinstance(self._data_, DataMark)
                and not isinstance(self._data_, TriggerEvent)
                ):
                menu.addAction(self.setEventDomanUnitsAction)

        menu.addAction(self.nameLabelsAction)

        return menu

    def eventFilter(self, obj: QtCore.QObject, evt: QtCore.QEvent) -> bool:
        if obj == self.timesLineEdit and isinstance(evt, QtGui.QContextMenuEvent):

            self.timesLineEdit.customMenu = self._createContextMenu_()
            self.timesLineEdit.contextMenuEvent(evt)
            return True
        else:
            self.timesLineEdit.customMenu = None
            return False

    def contextMenuEvent(self, evt: QtGui.QContextMenuEvent):
        if self._data_ is not None:
            menu = self._createContextMenu_()
            menu.exec(evt.globalPos())
            evt.setAccepted(True)

    @Slot()
    def _slot_setNameLabels(self):
        from gui import interact
        if self._data_ is None:
            name = None
            labels = None
        else:
            name = getattr(self._data_, "name", "")
            if len(name.strip()) == 0:
                name = type(self._data_).__name__

            labels = self._data_.labels
            # NOTE: 2026-03-15 16:19:54
            # Get the prefix & suffix for the labels (if any).
            # It generally makes sense for the labels in a neo.Event objects
            # (including DataMark objects) to have the form 'abc𝑘' where, BY
            # CONVENTION, 'abc' is a common string prefix, and '𝑘' is a string
            # representing a running integer index, usually starting at '0'.
            #
            # However, there is no rule that enforces this; therefore, one can
            # assign distinct labels to each time stamp in an Event object
            #
            # The code below tries to distinguish this, using the CONVENTION
            # that the magnitude values in the 'times' array is represented as
            # comma+space - separated numeric literals
            prefix, suffix = list(zip(*list(map(lambda s: strutils.get_int_sfx(str(s), sep="", use_re=True), labels))))

            # do they have a common prefix?
            if len(set(prefix)) == 1:
                # common prefix detected
                labels = prefix[0]

            else:
                labels = list(map(lambda s: str(s), labels))

            values = interact.packInputs(name=name, labels=labels)

            if values is None:
                return

            self._event_name_ = values["name"]

            labels = values["labels"].split(", ")

            if len(labels) > 1:
                if len(labels) >= self._data_.size:
                    labels = labels[0:self._data.size]

                elif len(labels) < self._data_.size:
                    prefix, suffix = list(zip(*list(map(lambda s: strutils.get_int_sfx(str(s), use_re=True), labels))))
                    print(f"{self.__class__.__name__}._slot_setNameLabels:\nprefix = {prefix},\nsuffix = {suffix}\n\n")
                    if len(set(prefix)) == 1:
                        pfx = prefix[0]
                    else:
                        pfx = prefix[-1]

                    if (
                        len(suffix) > 0
                        and all((
                            len(s.strip()) > 0
                            and strutils.isnumber(s)
                            ) for s in suffix)
                        ):
                        sfx = max(list(map(int, suffix))) + 1

                    else:
                        sfx = 0


                    for k in range(sfx, self._data_.size):
                        labels.append(f"{pfx}{k}")

            elif len(labels) == 1:
                labels = labels[0]

            else:
                return

            self._event_labels_ = labels

            self._createEventObject_()

    @Slot()
    def _slot_editTimes(self):
        r"""Called when times are edited in a TableEditorWidget"""
        from gui.widgets.tableeditorwidget import TableEditorWidget
        # if not self.timesLineEdit.isReadOnly():
        #     return

        if not isinstance(self._times_, np.ndarray):
            return

        dlg = qd.QuickDialog(self, title = "Edit values")
        te = TableEditorWidget(parent=dlg)
        te.setValue(self._times_)
        dlg.addWidget(te)
        dlg.adjustSize()

        if dlg.exec():
            self._times_ = te.value()
        self._createEventObject_()

    @Slot(str)
    def _slot_timesChanged(self, value:str):
        r"""Called when times are edited in-line (in a LineEdit widget)"""
        from core.prog import scipywarn
        # print(f"{self.__class__.__name__}._slot_timesChanged({value})")
        if len(value.strip()) == 0:
            self._times_ = None

        else:
            try:
                v = eval(value)
                # print(f"{self.__class__.__name__}._slot_timesChanged -> v = {v}")
                if isinstance(v, (tuple, list)):
                    self._times_ = np.array(v)

                elif isinstance(v, numbers.Number):
                    self._times_ = np.array([v])

            except:
                try:
                    # messing about...
                    # prevent units change via direct editing; use the contex menu instead
                    v = scq.str2quantity_2(value)
                    # print(f"{self.__class__.__name__}._slot_timesChanged: scq.str2quantity_2({value}) -> {v}")
                    if isinstance(v, pq.Quantity):
                        self._times_ = v.magnitude

                    elif isinstance(v, np.ndarray):
                        self._times_ = v

                    elif isinstance(v, typing.Sequence) and all(isinstance(x, pq.Quantity) for x in v):
                        if not all(x.units == v[0].units for x in v[1:]):
                            # scipywarn(f"Value {value} containes a mixture of Quantity units")
                            return

                        self._times_ = np.array(list(map(lambda x: x.magnitude, v)))


                    else:
                        # scipywarn(f"Cannot parse '{value}' to a Quantity")
                        return

                except:
                    # scipywarn(f"Cannot parse '{value}'")
                    return

        # print(f"{self.__class__.__name__}._slot_timesChanged: self._times_ = {self._times_}")
        self._createEventObject_()

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
        # dlg.resize(-1,-1)
        dlg.adjustSize()
        if dlg.exec():
            self._data_class_ = self.supported_types[cb.text()]

        event_type_needs_change: bool = False

        units_need_change: bool = False

        if self._data_class_ is TriggerEvent and isinstance(self._event_type_, MarkType):
            self._event_type_ = TriggerEventType.unspecified
            event_type_needs_change = True
            # self._slot_setEventType()

        elif self._data_class_ is DataMark and isinstance(self._event_type_, TriggerEventType):
            self._event_type_ = MarkType.unspecified
            event_type_needs_change = True
            # self._slot_setEventType()

        if self._data_class_ in (TriggerEvent, neo.Event) and not scq.checkTimeUnits(self._units_):
            units_need_change = True

        OK = True

        if units_need_change:
            OK &= self._ui_SetEventUnits()

        if event_type_needs_change:
            OK &= self._ui_SetEventType()

        if OK:
            self._createEventObject_()

    @Slot()
    def _slot_setEventType(self):

        if self._ui_SetEventType():
            self._createEventObject_()

        # dlg = qd.QuickDialog(self, title="Choose Event Type")
        # cb = qd.QuickDialogComboBox(dlg, "Type")
        # if type(self._data_) != self._data_class_:
        #     mytype = self._data_class_
        # else:
        #     mytype = type(self._data_)
        # # if isinstance(self._data_, TriggerEvent):
        # if mytype == TriggerEvent:
        #     evt_types = list(TriggerEventType.names())
        # elif mytype == DataMark:
        #     evt_types = list(MarkType.names())
        # else:
        #     return
        # cb.setItems(evt_types)
        #
        # if isinstance(self._event_type_, (MarkType, TriggerEventType)):
        #     cb.setCurrentIndex(evt_types.index(self._event_type_.name))
        #
        # dlg.addWidget(cb)
        # # dlg.resize(-1,-1)
        # dlg.adjustSize()
        #
        # if dlg.exec():
        #     evt_typename = cb.text()
        #
        #     if isinstance(self._data_, DataMark):
        #         self._event_type_ = getattr(MarkType, evt_typename)
        #     else:
        #         self._event_type_ = getattr(TriggerEventType, evt_typename)
        #
        #     self._createEventObject_()

    @Slot()
    def _slot_setEventUnits(self):
        if self._ui_SetEventUnits():
            self._createEventObject_()
        # from gui.widgets.small_widgets import QuantityChooserWidget
        # dlg = qd.QuickDialog(self, title="Choose Event Units")
        # if isinstance(self._units_, pq.Quantity):
        #     units = self._units_
        # elif self._data_ is None:
        #     units = pq.s
        # else:
        #     units = self._data_.units
        # qcw = QuantityChooserWidget(dlg, unit = units)
        # dlg.addWidget(qcw)
        # # dlg.resize(-1,-1)
        # dlg.adjustSize()
        # if dlg.exec():
        #     self._units_ = qcw.value()
        #
        # self._createEventObject_()

    def _ui_SetEventType(self):
        dlg = qd.QuickDialog(self, title="Choose Event Type")
        cb = qd.QuickDialogComboBox(dlg, "Type")
        if type(self._data_) != self._data_class_:
            mytype = self._data_class_
        else:
            mytype = type(self._data_)
        # if isinstance(self._data_, TriggerEvent):
        if mytype == TriggerEvent:
            evt_types = list(TriggerEventType.names())
        elif mytype == DataMark:
            evt_types = list(MarkType.names())
        else:
            return
        cb.setItems(evt_types)

        if isinstance(self._event_type_, (MarkType, TriggerEventType)):
            cb.setCurrentIndex(evt_types.index(self._event_type_.name))

        dlg.addWidget(cb)
        # dlg.resize(-1,-1)
        dlg.adjustSize()

        if dlg.exec():
            evt_typename = cb.text()

            if isinstance(self._data_, DataMark):
                self._event_type_ = getattr(MarkType, evt_typename)
            else:
                self._event_type_ = getattr(TriggerEventType, evt_typename)

            return True

        return False

    def _ui_SetEventUnits(self):
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
        # dlg.resize(-1,-1)
        dlg.adjustSize()
        if dlg.exec():
            self._units_ = qcw.value()
            return True
        return False

    def _createEventObject_(self) -> bool:
        if (isinstance(self._data_class_, type)
            and issubclass(self._data_class_, neo.Event)
            ):
            if self._data_class_ in (DataMark, TriggerEvent):
                if self._units_ is None:
                    units = pq.s
                else:
                    units = self._units_

            elif self._data_class_ is neo.Event:
                if self._units_ is None:
                    units = pq.s
                elif scq.unitFamilyName(self._units_) == "Time":
                    units = self._units_
                else:
                    # scipywarn("Neo Events only support time units")
                    return False

            if (not isinstance(self._times_, np.ndarray)
                and (not isinstance(self._times_, typing.Sequence)
                    or not all(isinstance(v, numbers.Number) for v in self._times_)
                    )
                ):
                self._times_ = None

            if isinstance(self._times_, np.ndarray):
                if (self._times_.ndim > 1
                    and any(v > 1 for v in self._times_.shape[1:])):
                    if self._data_class_ in (neo.Event, TriggerEvent):
                        # scipywarn("neo.Event and TriggerEvent can only take 1D arrays")
                        return False

            evt = self._data_class_(self._times_, units=self._units_, labels = self._event_labels_, name=self._event_name_)

            if isinstance(evt, TriggerEvent):
                if isinstance(self._event_type_, TriggerEventType):
                    evt.type = self._event_type_

                elif self._event_type_ is None:
                    self._event_type_ = TriggerEventType.unspecified
                else:
                    # scipywarn(f"Cannot assign a {type(self._event_type_.__name__)} as type of {type(evt).__name__}")
                    return False

            elif isinstance(evt, DataMark):
                if isinstance(self._event_type_, MarkType):
                    evt.type = self._event_type_
                elif self._event_type_ is None:
                    self._event_type_ = MarkType.unspecified
                else:
                    # scipywarn(f"Cannot assign a {type(self._event_type_).__name__} as type of {type(evt).__name__}")
                    return False

            self._data_ = evt
            self._times_ = self._data_.times.magnitude
            self._units_ = self._data_.times.units

            return True

        return False

            # self._update_()

    def value(self) -> typing.Optional[typing.Union[neo.Event, DataMark, TriggerEvent]]:
        return self._data_

    def setValue(self, val: typing.Optional[
                                typing.Union[neo.Event, DataMark, TriggerEvent]
                                ] = None):
        self._data_ = val
        if isinstance(self._data_, neo.Event):
            self._data_class_ = type(val)
            self._times_ = self._data_.times.magnitude
            self._units_ = self._data_.times.units
            self._event_labels_ = self._data_.labels
            if isinstance(self._data_, (DataMark, TriggerEvent)):
                self._event_type_ = self._data_.type

            self._update_()

        else:
            self._data_class_ = None
            self._times_ = None
            self._units_ = None
            self._event_labels_ = None
            self._event_type_ = None

    @Slot(bool)
    def _slot_lazyTextChanges(self, val:bool):
        if val is True:
            if self.timesLineEdit.receivers(self.timesLineEdit.textChanged) > 0:
                self.timesLineEdit.textChanged.disconnect(self._slot_timesChanged)
            self.timesLineEdit.sig_enterPressed.connect(self._slot_timesChanged)
        else:
            if self.timesLineEdit.receivers(self.timesLineEdit.sig_enterPressed) > 0:
                self.timesLineEdit.sig_enterPressed.disconnect(self._slot_timesChanged)
            self.timesLineEdit.textChanged.connect(self._slot_timesChanged)



