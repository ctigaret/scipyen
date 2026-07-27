# -*- coding: utf-8 -*-
# $Id: delegates.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import os, sys, typing, types, math, pathlib, enum, datetime # noqa
from functools import partial
import dataclasses
import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip # noqa
    from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

__has_qtdbus__ = False

try:
    from qtpy import QtDBus # noqa
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

from core.datatypes import (is_namedtuple, TypeEnum) # noqa
from core.prog import (safewrapper, safeguiwrapper, scipywarn, print_styled) # noqa
from core.sysutils import adapt_ui_path # noqa

__module_path__ = os.path.abspath(os.path.dirname(__file__))

import numpy as np
import vigra
import quantities as pq
import pandas as pd
import neo
from tribool import Tribool
# from core import scipyen_quantities as scq
from core import strutils as strutils
from core import datatypes
from gui.widgets import small_widgets as smw
from gui.widgets import neo_widgets as neow
from gui.widgets import inlinefiledirchooser as ifdc
# from gui import quickdialog as qd
# from core import typeenum
from gui.itemmodels.roles import * # noqa
from gui import guiutils
from ephys import (ephys, ephys_pathways)

class ExternalEditorDelegate(QtWidgets.QMainWindow):
    r"""For use with external editing in PythonItemDelegate.


NOTE: To be used with my custom itemmodels


"""
    sig_valueChanged            = Signal(object)
    sig_closing                 = Signal()
    sig_indexChanged            = Signal([int, int], [QtCore.QModelIndex], name="sig_indexChanged")

    def __init__(self, data: object = None,
                 parent = None,
                 lazy: bool = False,
                 ):
        r"""
    CAUTION: The underlying central widget may call another instance of this !

    If ``lazy`` is True, then UI changes will not update the internal data
    representation until after the window is closed.
"""
        QtWidgets.QMainWindow.__init__(self, parent=parent)

        self._pendingChange_: bool = False
        self._lazy_ = lazy is True

        self._data_ = data
        self._widget_ = self.chooseEditor()

        # print (f"{self.__class__.__name__}.__init__ -> widget is {type(self._widget_).__name__}")

        if isinstance(self._widget_, QtWidgets.QWidget):
            self.setCentralWidget(self._widget_)
            self.resize(-1,-1)

        if not self._lazy_:
            self.show()

    @property
    def lazy(self) -> bool:
        return self._lazy_

    @lazy.setter
    def lazy(self, val: bool):
        self._lazy_ = val is True

    def closeEvent(self, evt):
        # print(f"{self.__class__.__name__}[{self.objectName()}].closeEvent:")
        self._pendingChange_ = False
        # store data from underlying central widget
        if isinstance(self._widget_, QtWidgets.QWidget) and hasattr(self._widget_, "value"):
            self._data_ = self._widget_.value()
        self.sig_closing.emit()
        self.sig_valueChanged.emit(self._data_)
        evt.accept()

    def chooseEditor(self) -> QtWidgets.QWidget:
        # print(f"{self.__class__.__name__}.chooseEditor for {type(self._data_).__name__}")
        from gui.widgets import (synapticstimuluswidget,
                                 synapticpathwaywidget,
                                 auxiliaryiowidget,
                                 recordingsourcewidget,
                                 recordingepisodewidget,
                                 tableeditorwidget,
                                 )
        widget = None
        editorName = f"{type(self._data_).__name__} Editor"
        self.setWindowTitle(editorName)
        if isinstance(self._data_, ephys_pathways.SynapticStimulusChannel):
            widget = synapticstimuluswidget.SynapticStimulusChannelWidget(
                parent=self, obj = self._data_,)
            widget.setObjectName(f"{editorName} Widget")

        elif isinstance(self._data_, (ephys_pathways.AuxiliaryInput, ephys_pathways.AuxiliaryOutput)):
            if isinstance(self._data_, ephys_pathways.AuxiliaryInput):
                widget = auxiliaryiowidget.AuxiliaryInputWidget(self,
                                                                self._data_,
                                                                )
            else:
                widget = auxiliaryiowidget.AuxiliaryOutputWidget(self,
                                                                 self._data_,
                                                                 )
            widget.setObjectName(f"{editorName} Widget")

        elif isinstance(self._data_, ephys_pathways.SynapticPathway):
            widget = synapticpathwaywidget.SynapticPathwayWidget(
                parent=self,
                obj = self._data_,
                )
            widget.setObjectName(f"{editorName} Widget")

        elif isinstance(self._data_, ephys_pathways.RecordingEpisode):
            widget = recordingepisodewidget.RecordingEpisodeWidget(self,
                                                                   self._data_
                                                                   )
            widget.setObjectName(f"{editorName} Widget")

        elif isinstance(self._data_, ephys_pathways.RecordingSource):
            widget = recordingsourcewidget.RecordingSourceWidget(self,
                                                                 self._data_,
                                                                 )
            widget.setObjectName(f"{editorName} Widget")

        elif isinstance(self._data_, typing.Sequence) or datatypes.is_iterable(self._data_):
            widget = tableeditorwidget.TableEditorWidget(self)
            widget.setObjectName(f"{editorName} Widget")
            widget.setData(self._data_)

        if isinstance(widget, QtWidgets.QWidget) and hasattr(widget, "sig_valueChanged"):
            # print(f"{self.__class__.__name__}.chooseEditor -> widget is a {type(widget).__name__}:")
            if isinstance(widget, tableeditorwidget.TableEditorWidget):
                widget.sig_valueChanged.connect(self.slot_dataChanged)
                widget.sig_indexChanged.connect(self.sig_indexChanged)
                widget.sig_indexChanged[QtCore.QModelIndex].connect(self.sig_indexChanged[QtCore.QModelIndex])
            else:
                widget.sig_valueChanged.connect(self.slot_valueChanged)

        return widget

    @Slot()
    def _slot_externalEditorClosing(self):
        self._pendingChange_ = False

    @Slot()
    def slot_dataChanged(self):
        obj = self.sender().value()
        if self._pendingChange_:
            return
        self._data_ = obj
        self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def slot_valueChanged(self, val):
        # print(f"{self.__class__.__name__}[{self.objectName()}].slot_valueChanged({val})")
        if self._pendingChange_:
            return

        self._data_ = val

        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def slot_Launch(self):
        if isinstance(self._widget_, QtWidgets.QWidget):
            if self.lazy:
                self._pendingChange_ = True
            else:
                self._pendingChange_ = False
            self.show()

    def setValue(self, data: object):
        self._data_ = data
        newWidget = self.chooseEditor()
        if isinstance(newWidget, QtWidgets.QWidget):
            oldWidget = self.takeCentralWidget()
            oldWidget.sig_valueChanged.disconnect()
            self._widget_ = newWidget
            oldWidget.close()
            self.setCentralWidget(self._widget_)
            self._widget_.sig_valueChanged.connect(self.slot_valueChanged)

    def value(self) -> object:
        return self._data_


class CutFileSystemItemDelegate(QtWidgets.QStyledItemDelegate):
    # WARNING: 2026-01-25 22:25:36 TODO
    # needs more work
    def paint(self, painter, option, index):
        # BUG: 2026-01-25 22:25:50 TODO/FIXME
        # screws up painting
        # print(f"{self.__class__.__name__}.paint: option = {option}\n")
        painter.setPen(QtWidgets.QApplication.palette().color(QtGui.QPalette.Inactive, QtGui.QPalette.Text))
        super().paint(painter, option, index)
        # self.initStyleOption()
        # painter.drawText(option.rect, option.displayAlignment, index.data())

class PythonItemDelegate(QtWidgets.QStyledItemDelegate):
    r"""Provides delegate widgets for editing individual items in tabular data models.

    By default, this provides the following editor widgets (all from QtWidgets,
    unless specified):

    Data type                       Widget
    -----------------------------------------
    int                             QSpinBox
    float                           QuantitySpinBox
    str                             QLineEdit or QComboBox¹, or QPlainTextEdit
    bool                            QCheckBox
    pq.Quantity (scalar)            small_widgets.QuantityChooserWidget
    Enum value                      QLineEdit or QComboBox¹

    ¹In addition, the delegate can be configured to use a QComboBox by passing
    a "columnChoices" parameter (dict) to the constructor, which allows the use
    of a combo box for selecting one of many categories (represented by strings)

    For details, see the documentation for the initializer and or the methods
    setColumnChoices and setChoicesForColumn.


"""
    sig_dataChanged = Signal(QtWidgets.QWidget, name = "sig_dataChanged")
    sig_contentsChanged = Signal(name="sig_contentsChanged")
    sig_editExternally = Signal(QtWidgets.QWidget, QtCore.QModelIndex, name = "sig_editExternally")
    sig_indexChanged = Signal([int, int], [QtCore.QModelIndex], name="sig_indexChanged")
    # TODO/FIXME: 2025-10-28 12:57:09
    # decide how to handle the case where the combo box is editable (and its
    # currentText() is not among the combo box items)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 columnChoices: typing.Optional[dict[int,
                                                     dict[typing.Sequence,
                                                          bool]]] = None,
                 enforceFloat: bool = False):
        r"""Instantiates a PythonItemDelegate.

    Parameters:
    ===========
    parent: parent QWidget; optional, default is None

    columnChoices: dict; sets up the delegate editor to be a QComboBox for specific
        table columns:

        column index:int ↦ data:dict with key:str ↦ sequence or bool as below:
                            — "choices": typing.Sequence[str]
                            — "editable": bool; when True, the combo box is editable
                              WARNING: this is not currently supported, and by default
                                this is False

        NOTE: The choices are always strings, and the data assocated with the EditRole
        of a model index MUST be a string that is present among the choices


        Example (setting choices for columns 0 and 3):

        {0: {   "choices": ["1","2","3"],
                "editable": False},
         3: {   "choices": ["test", "me", "now"],
                "editable": True}}

        NOTE: the "choices" field in the column sub-dictionary cannot be empty!

    immutableColumns, immutableRows: columns/rows of model indexes that are uneditable
    jointImmutability:
    """
        super().__init__(parent=parent)
        # self._model_ = None
        self._useObjectDataRole_: bool = False
        self._currentModelIndex_: typing.Optional[QtCore.QModelIndex] = None

        self._enforceFloat_:bool = enforceFloat

        if self._checkColumnChoiceDict_(columnChoices):
            self._columnChoices_ = columnChoices

        else:
            self._columnChoices_ = dict() # always keep it as a dict, even when empty

        self._currentData_:typing.Optional[typing.Any] = None
        self._externalDataEditor_: typing.Optional[QtWidgets.QWidget] = None
        # self.sig_contentsChanged.connect(self._slot_sendToExternalEditor)

    def _checkColumnChoiceDict_(self, d:dict) -> bool:
        if not isinstance(d, dict):
            return False

        # NOTE: 2025-10-28 08:48:37 allow wiping out the choices by passing an
        # empty dict
        #
        # if len(d) == 0:
        #     return False

        keys, values = list(zip(*d.items()))

        if not all(isinstance(k, int) and k >= 0 for k in keys):
            return False

        checkSubKeys = lambda v: all(k in ("editable", "choices") for k in v.keys()) # noqa
        checkChoices = lambda v: isinstance(v["choices"], typing.Sequence) and len(v["choices"]) > 0 and all(isinstance(o, str) for o in v["choices"]) # noqa
        checkEditable= lambda v: isinstance(v["editable"], bool) # noqa

        if not all(isinstance(v, dict) and checkSubKeys(v) and checkChoices(v) and checkEditable(v) for v in values):
            return False

        return True

    # @property
    # def immutability(self) -> dict:
    #     r"""Mapping row & col indexes where cell contents CANNOT be altered.
    # E.g.: {"columns": [2,3], "rows": [0,1], "joint":False}
    # """
    #     return self._immutability_
    #
    # @immutability.setter
    # def immutability(self, value:dict):
    #     # d = {"columns":list(), "rows": list(), "joint":False}
    #     if not isinstance(value, dict):
    #         self._immutability_ = {"columns":list(), "rows": list(), "joint":False}
    #     else:
    #         if "columns" in value and isinstance(value["columns"], typing.Sequence):
    #             if len(value["columns"]) == 0 or not all(isinstance(v, int) for v in value["columns"]):
    #                 self._immutability_["columns"] = list()
    #
    #             else:
    #                 self._immutability_["columns"] = list(value["columns"])
    #
    #         if "rows" in value and isinstance(value["rows"], typing.Sequence):
    #             if len(value["rows"]) == 0 or not all(isinstance(v, int) for v in value["rows"]):
    #                 self._immutability_["rows"] = list()
    #
    #             else:
    #                 self._immutability_["rows"] = list(value["rows"])
    #
    #         if "joint" in value:
    #             if isinstance(value["joint"], bool):
    #                 self._immutability_["value"] = value["joint"]
    #             else:
    #                 self._immutability_["value"] = False

    # @property
    # def jointImmutability(self) -> bool:
    #     return self._immutability_["joint"]
    #
    # @jointImmutability.setter
    # def jointImmutability(self, value:bool):
    #     self._jointImmutability_ = value is True
    #     self._immutability_["joint"] = self._jointImmutability_
    #
    # @property
    # def immutableColumns(self) -> typing.Sequence[int]:
    #     r"""Indexes of columns where the contents CANNOT be changed"""
    #     return self._immutability_["columns"]
    #
    # @immutableColumns.setter
    # def immutableColumns(self, value:typing.Sequence[int]):
    #     self._immutableColumns_ = value
    #     self._immutability_["columns"] = self._immutableColumns_
    #
    # @property
    # def immutableRows(self) -> typing.Sequence[int]:
    #     r"""Indexes of rows where the contents CANNOT be changed"""
    #     return self._immutability_["rows"]
    #
    # @immutableRows.setter
    # def immutableRows(self, value:typing.Sequence[int]):
    #     self._immutableRows_ = value
    #     self._immutability_["rows"] = self._immutableRows_

    @property
    def enforceFloat(self) -> bool:
        return self._enforceFloat_

    @enforceFloat.setter
    def enforceFloat(self, val: bool):
        self._enforceFloat_ = val is True

    @property
    def columnChoices(self) -> dict:
        r"""Returns a reference to the column choices.
    One may edit the contents directly
    """

    def setColumnChoices(
        self,
        choicesDict: typing.Optional[dict[int, dict[typing.Sequence,
                                                    bool]]] = None
        ):
        if choicesDict is None:
            self._columnChoices_ = dict() # wipes out current column choices

        elif self._checkColumnChoiceDict_(choicesDict): # may wipe out the choices if parameter is empty
            self._columnChoices_ = choicesDict
        else:
            scipywarn(
                f"{self.__class__.__name__}.setColumnChoices: inappropriate value"
                )

    def setChoicesForColumn(
        self: typing.Self, /,
        col: typing.Optional[int] = None,
        choiceData: typing.Optional[typing.Union[dict,
                                                    typing.Sequence,
                                                    bool]] = None,
        editable: typing.Optional[bool] = None
                    ):
        r"""Alter the choices for a specific column.
        Keyword-only parameters:
        col: int or None; column index; can be None when choiceData is a dict with
            the appropriate structure

        choiceData: dict specifying the choice data for a single column, e.g.:
            {1:  { "choices": ["1","2","3"], "editable": True }}

        Here, you can:
        • insert or edit the choices for a column
        """
        # TODO: 2025-09-25 23:42:02
        # for datetime.datetime use QDateTimeEdit (with QDate and QTime)
        # for datetime.date use QDateEdit (with QDate)
        # for datetime.time use QTimeEdit (with QTime)

        if self._checkColumnChoiceDict_(choiceData):
            if len(choiceData) == 1:
                if isinstance(self._columnChoices_, dict):
                    self._columnChoices_.update(choiceData)
                else:
                    self._columnChoices_ = choiceData
            else:
                scipywarn(f"{self.__class__.__name__}.setChoicesForColumn: incorrect choices specification: {choiceData}")
        else:
            # must specify a column index, here (col:int)
            if not isinstance(col, int) or col < 0:
                scipywarn(f"{self.__class__.__name__}.setChoicesForColumn: incorrect column specification: col = {col}")
                return
            if isinstance(choiceData, dict):
                # may be a choices subdictionary
                if all(k in ("choices", "editable") for k in choiceData.keys()) and isinstance(choiceData["choices"], typing.Sequence) and len(choiceData["choices"]) > 0 and all(isinstance(o, str) for o in choiceData["choices"]) and isinstance(choiceData["editable"], bool):
                    self._columnChoices_[col] = choiceData

                elif len(choiceData) == 0: # empty dict -> wipe out the choices for a specific column
                    if col in self._columnChoices_:
                        self._columnChoices_.pop(col)

            elif isinstance(choiceData, typing.Sequence): # create or remove choices for a column
                if len(choiceData) == 0: # also wipes out the choices for specified column
                    if col in self._columnChoices_:
                        self._columnChoices_.pop(col)

                    else:
                        scipywarn(f"{self.__class__.__name__}.setChoicesForColumn: no choices defined for column {col}")

                else:
                    if not all(isinstance(o, str) for o in choiceData):
                        scipywarn(f"{self.__class__.__name__}.setChoicesForColumn: choices must be strings")
                        return

                    if col in self._columnChoices_: # if choices for col exist, set them to a new value
                        self._columnChoices_[col]["choices"] = choiceData
                        # optionally also set their editable flag
                        if isinstance(editable, bool):
                            self._columnChoices_[col]["editable"] = editable

                    else: # otherwise, create a new column choices subdictionary, not editable by default
                        if not isinstance(editable, bool):
                            editable = False
                        self._columnChoices_[col] = {"choices": choiceData, "editable": editable}

            elif isinstance(choiceData, bool): # set the editable flag only if there are choices for this column
                if col in self._columnChoices_:
                    self._columnChoices_[col]["editable"] = choiceData

            else:
                scipywarn(f"{self.__class__.__name__}.setChoicesForColumn: invalid choiceData: {choiceData}")

    def createWidget(self, data:typing.Any,
        choices: typing.Optional[
                                typing.Union[
                                    typing.Sequence[
                                        typing.Union[enum.Enum,
                                                     enum.IntEnum,
                                                     enum.Flag,
                                                     TypeEnum,
                                                     str]
                                                    ],
                                    typing.Dict]
                                ] = None,
        inModel: bool=True,
        parent: typing.Optional[QtWidgets.QWidget] = None
                     ) -> QtWidgets.QWidget:
        r"""Work around for use independently of an item model.

        Bypasses the QModelIndex paradigm because a QTreeWidgetItem does not expose
        QModelIndex API

    """
        from gui.widgets.tableeditorwidget import TableEditorWidget # import here to avoid circular imports (delegates is imported by tableeditorwidget as well)
        # from gui.itemmodels.tabulardatamodel import TabularDataModel
        widget = None

        if isinstance(data, (bool, np.bool)):# or "bool" in type(data).__name__:
            widget = QtWidgets.QCheckBox(parent)
            # widget.setChecked(data is True)
            if not inModel:
                widget.setChecked(data is True)
            widget.toggled.connect(self.slot_dataChanged)

        elif isinstance(data, Tribool):
            widget = smw.GenericInputWidget(parent)
            if not inModel:
                widget.setValue(data)

            widget.sig_valueChanged.connect(self.slot_dataChanged)

        elif isinstance(data, (datetime.datetime, datetime.date, datetime.time)):
            if isinstance(data, datetime.datetime):
                qDate = QtCore.QDate(data.year, data.month, data.day)
                qTime = QtCore.QTime(data.hour, data.minute, data.second,
                                    int(np.round(data.microsecond/1000, 3)))
                qDateTime = QtCore.QDateTime(qDate, qTime)
                widget = QtWidgets.QDateTimeEdit(qDateTime, parent)
                if not inModel:
                    widget.setDateTime(qDateTime)

                widget.dateTimeChanged.connect(self.slot_dataChanged)

            elif isinstance(data, datetime.date):
                qDate = QtCore.QDate(data.year, data.month, data.day)
                widget = QtWidgets.QDateEdit(qDate, parent)
                if not inModel:
                    widget.setDate(qDate)

                widget.dateChanged.connect(self.slot_dataChanged)

            else:
                qTime = QtCore.QTime(data.hour, data.minute, data.second,
                                    int(np.round(data.microsecond/1000, 3)))
                widget = QtWidgets.QTimeEdit(qTime, parent)

                if not inModel:
                    widget.setTime(qTime)

                widget.timeChanged.connect(self.slot_dataChanged)

        elif isinstance(data, (int, float, np.floating, np.integer)):
            if (
                isinstance(choices, typing.Sequence)
                and len(choices) > 0
                and all(isinstance(v, (enum.Enum, str)) for v in choices)
                ) or (
                    isinstance(choices, dict)
                    and len(choices) > 0
                    and all(isinstance(k, str) for k in choices.keys())
                    ):
                if isinstance(choices, dict):
                    entries = list(choices.keys())
                    values = list(choices.values())
                else:
                    entries = list(map(lambda x: x.name if isinstance(x, enum.Enum) else x, choices))
                    values = list(map(lambda x: x.value if isinstance(x, enum.Enum) else choices.index(x), choices))

                if data in values:
                    ndx = values.index(data)
                    widget = QtWidgets.QComboBox(parent)
                    widget.insertItems(0, entries)
                    widget.setEditable(False)
                    widget.setCurrentIndex(ndx)

                    if hasattr(widget, "setFrame"):
                        widget.setFrame(False)

                    widget.setAutoFillBackground(True)

                    widget.currentIndexChanged.connect(self.slot_valueChanged)

                    return widget

                else:
                    scipywarn(f"Data ({data}) is not in the supplied choices ({choices})")
                    return
            else:
                if self._enforceFloat_:
                    # widget = smw.QuantitySpinBox(parent, data)
                    widget = QtWidgets.QDoubleSpinBox(parent, data)
                    widget.setMinimum(-math.inf)
                    widget.setMaximum(math.inf)
                    # widget.setSingleStep(1)
                    if not inModel:
                        widget.setValue(data)

                    widget.valueChanged.connect(self.slot_valueChanged)

                else:
                    if isinstance(data, (int, np.integer)):
                        widget = QtWidgets.QSpinBox(parent)
                        widget.setMinimum(-9999)
                        widget.setMaximum(9999)
                        if not inModel:
                            widget.setValue(data)

                        widget.valueChanged.connect(self.slot_valueChanged)

                    elif isinstance(data, (float, np.floating)):
                        # widget = smw.QuantitySpinBox(parent, data)
                        widget = QtWidgets.QDoubleSpinBox(parent)
                        widget.setMinimum(-math.inf)
                        widget.setMaximum(math.inf)
                        # widget.setSingleStep(1)
                        if not inModel:
                            widget.setValue(data)

                        widget.valueChanged.connect(self.slot_valueChanged)
                        # widget.sig_valueChanged.connect(self.slot_valueChanged)

        elif isinstance(data, (complex, np.complexfloating)):
            widget = smw.ComplexSpinBox(parent, data)
            # widget.setValue(data)
            if not inModel:
                widget.setValue(data)

            widget.sig_valueChanged.connect(self.slot_valueChanged)
            # TODO: 2026-02-03 09:31:21
            # set up other properties as well...

        elif isinstance(data, pq.Quantity):
            # print(f"{self.__class__.__name__}.createWidget({type(data).__name__})")
            if isinstance(data, pq.UnitQuantity): # unlikely, but here we go...
                widget = smw.QuantityChooserWidget(parent, data)
                # widget.setValue(data)
                if not inModel:
                    widget.setValue(data)

                widget.unitChanged.connect(self.slot_valueChanged)
            else:
                if isinstance(data, neo.Event):
                    widget = neow.SimpleTriggerEventWidget(parent, data)
                    if not inModel:
                        widget.setValue(data)

                    widget.sig_valueChanged.connect(self.slot_valueChanged)

                else:
                    isComplex = issubclass(data.dtype.type, np.complexfloating)
                    if data.ndim == 0 or (data.ndim == 1 and data.size == 1):
                        if isComplex:
                            widget = smw.ComplexSpinBox(parent, data, enforceImmutableUnits=True) # disallow units change for individual data points in a Quantity
                        else:
                            widget = smw.QuantitySpinBox(parent, data, enforceImmutableUnits=True) # disallow units change for individual data points in a Quantity

                        widget.setMinimum(-math.inf * data.units)
                        widget.setMaximum(math.inf * data.units)
                        widget.setSingleStep(1.0  * data.units)
                        widget.disableUnitChange = True

                        # widget.setValue(data)
                        if not inModel:
                            widget.setValue(data)

                        widget.sig_valueChanged.connect(self.slot_valueChanged)

                    else:
                        widget = TableEditorWidget(parent, readOnly=False)
                        if not inModel:
                            widget.setData(data)

                        widget.sig_dataChanged.connect(self.slot_dataChanged)
                        widget.sig_indexChanged.connect(self.sig_indexChanged) # connect signal 2 signal directly
                        # widget.sig_indexChanged[Qt].connect(self.sig_indexChanged) # connect signal 2 signal directly
                        # widget.sig_indexChanged

        elif isinstance(data, np.ndarray):
            if data.ndim == 0 or (data.ndim ==1 and data.size == 1):
                if issubclass(data.dtype.type, np.floating):
                    if isinstance(data, pq.Quantity):
                        widget = smw.QuantitySpinBox(parent, data, enforceImmutableUnits=True) # disallow units change for individual data points in a Quantity
                        widget.setMinimum(-math.inf * data.units)
                        widget.setMaximum(math.inf * data.units)
                        widget.setSingleStep(1.0  * data.units)
                        widget.disableUnitChange = True
                        if not inModel:
                            widget.setValue(data)

                        widget.sig_valueChanged.connect(self.slot_valueChanged)

                    else:
                        widget = QtWidgets.QDoubleSpinBox(parent, data)
                        widget.setMinimum(-math.inf)
                        widget.setMaximum(math.inf)
                        if not inModel:
                            widget.setValue(data)

                        widget.valueChanged.connect(self.slot_valueChanged)

                elif issubclass(data.dtype.type, np.complexfloating):
                    widget = smw.ComplexSpinBox(parent, data)
                    if not inModel:
                        widget.setValue(data)

                    widget.sig_valueChanged.connect(self.slot_valueChanged)

                elif issubclass(data.dtype.type, np.integer):
                    widget = QtWidgets.QSpinBox(parent)
                    widget.setMinimum(-9999)
                    widget.setMaximum(9999)
                    if not inModel:
                        widget.setValue(data)

                    widget.valueChanged.connect(self.slot_valueChanged)

                elif issubclass(data.dtype.type, np.character):
                    widget = smw.LineEdit(data, parent=parent, lazy=True)
                    widget.undoAvailable = True
                    widget.redoAvailable = True
                    widget.setClearButtonEnabled(True)
                    # widget = smw.LazyLineEdit(parent)
                    if not inModel:
                        widget.setValue(data)
                        # widget.setText(data)

                    widget.sig_textChanged.connect(self.slot_dataChanged)

            else:
                widget = TableEditorWidget(parent, readOnly=False)
                widget.setData(data)
                if not inModel:
                    widget.setData(data)

                widget.sig_dataChanged.connect(self.slot_dataChanged)
                widget.sig_indexChanged.connect(self.sig_indexChanged)

        elif isinstance(data, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
            widget = TableEditorWidget(parent, readOnly=False)
            widget.setData(data)
            if not inModel:
                widget.setData(data)

            widget.sig_dataChanged.connect(self.slot_dataChanged)
            widget.sig_indexChanged.connect(self.sig_indexChanged)

        elif isinstance(data, pathlib.Path):
            if data.is_dir():
                widget = ifdc.InlineDirChooserWidget(
                    initial=data, parent=parent, asDelegate=True)

            elif data.is_file():
                widget = ifdc.InlineFileChooserWidget(
                    initial=data, parent=parent, asDelegate=True)

            if hasattr(widget, "setFrame"):
                widget.setFrame(False)

            if not inModel:
                widget.setValue(data)

            widget.sig_dataChanged.connect(self.slot_dataChanged)
            widget.sig_dispatchAction.connect(self._slot_dispatchedAction_)

        elif isinstance(data, (str, np.character, bytes, bytearray)):
            if isinstance(data, str):
                if (
                    (
                    isinstance(choices, typing.Sequence)
                    and all(isinstance(v, (enum.Enum, enum.IntEnum, TypeEnum, enum.Flag, str)) for v in choices)
                    ) or isinstance(choices, (dict, types.MappingProxyType))
                    ) and len(choices) > 0:
                    if isinstance(choices, (dict, types.MappingProxyType)):
                        entries = list(choices.keys())
                        values = list(choices.values())
                    else:
                        entries = list(map(lambda x: x.name if isinstance(x, enum.Enum) else x, choices))
                        values = list(map(lambda x: x.value if isinstance(x, enum.Enum) else entries.index(x), choices))

                    if data in entries:
                        ndx = entries.index(data)
                        widget = QtWidgets.QComboBox(parent)
                        widget.insertItems(0, entries)
                        widget.setEditable(False)
                        widget.setCurrentIndex(ndx)

                        if hasattr(widget, "setFrame"):
                            widget.setFrame(False)
                        widget.setAutoFillBackground(True)

                        # widget.setValue(data)
                        if not inModel:
                            widget.setValue(data)

                        return widget

                    else:
                        scipywarn(f"Data ({data}) is not in the supplied choices ({choices})")
                        return
            # else:
            if len(data) > 100:
                txt = data if isinstance(data, str) else data.decode()
                widget = QtWidgets.QPlainTextEdit(txt, parent)
                widget.setMaximumHeight(200)
                widget.setPlainText(txt)
                if isinstance(data, str):
                    widget.setReadOnly(False)

                    widget.textChanged.connect(self.slot_dataChanged)

                else:
                    widget.setReadOnly(True)

            else:
                if isinstance(data, (str, np.character)):
                    # widget = QtWidgets.QLineEdit(parent)
                    widget = smw.LineEdit(parent, data, lazy=True)
                    widget.undoAvailable = True
                    widget.redoAvailable = True
                    widget.setClearButtonEnabled(True)
                    # widget = smw.LazyLineEdit(parent)
                    # widget.setText(data)
                    # widget.setValue(data)
                    if not inModel:
                        widget.setValue(data)

                    widget.sig_textChanged.connect(self.slot_dataChanged)

                else:
                    return

        elif isinstance(data, (pd.DataFrame, pd.Series, pd.MultiIndex, pd.Index)):
            widget = TableEditorWidget(parent, readOnly=False)
            if not inModel:
                widget.setData(data)

            widget.sig_dataChanged.connect(self.slot_dataChanged)
            widget.sig_indexChanged.connect(self.sig_indexChanged)

        else: # TODO: 2025-09-23 16:16:56 FIXME use a pushbutton to open a complex viewer/editor
            return

        if hasattr(widget, "setFrame"):
            widget.setFrame(False)
        widget.setAutoFillBackground(True)
        widget.setObjectName(f"{type(widget).__name__}_delegate")


        return widget

    @Slot(partial)
    @Slot(types.FunctionType)
    def _slot_dispatchedAction_(self,
                                fn: typing.Union[partial, types.FunctionType]):
        sender = self.sender()
        ret = fn()
        if isinstance(ret, tuple):
            ret = ret[0]

        if isinstance(ret, str) and len(ret.strip()):
            ret = pathlib.Path(ret)

        elif not isinstance(ret, pathlib.Path):
            return

        # print(f"{self.__class__.__name__}._slot_dispatchedAction_: ret = {ret}\n\tfrom sender: {type(sender)}\n")

        if (
            isinstance(ret, pathlib.Path)
            and isinstance(sender, ifdc.InlineFileDirChooserWidget)
            and isinstance(self._currentModelIndex_, QtCore.QModelIndex)
            ):
            model = self._currentModelIndex_.model()
            role = ObjectDataRole if self._useObjectDataRole_ else QtCore.Qt.EditRole
            model.setData(self._currentModelIndex_, ret, role)
            # if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            #     model.setData(self._currentModelIndex_, ret.as_posix(), QtCore.Qt.DisplayRole)

        self._currentModelIndex_ = None

    @Slot()
    def _slot_editDataExternally(self):
        # NOTE: 2026-06-07 11:56:17
        # external editor NEEDS a separate QMainWindow!
        # self.sig_editExternally.emit(self.sender(), index)
        sender = self.sender()
        if isinstance(sender, QtWidgets.QPushButton):
            if isinstance(self._currentModelIndex_, QtCore.QModelIndex) and self._currentModelIndex_.isValid():
                model = self._currentModelIndex_.model()
                modelData = getattr(model, "_modelData_", None)

                # CAUTION 2026-06-09 19:08:50
                # this is supposed to edit the python object represented by the
                # entire model data row!!!
                if isinstance(modelData, typing.Iterable):
                    self._externalDataEditor_ = ExternalEditorDelegate(modelData[self._currentModelIndex_.row()])
                    self._externalDataEditor_.sig_valueChanged.connect(self._slot_dataEditedExternally)
                    self._externalDataEditor_.sig_closing.connect(self._slot_externalEditorClosing)

    @Slot()
    def _slot_externalEditorClosing(self):
        self._externalDataEditor_ = None

    @Slot(object)
    def _slot_dataEditedExternally(self, val):
        from gui.itemmodels.tabulardatamodel import TabularDataModel
        # print(f"{self.__class__.__name__}._slot_dataEditedExternally -> {val}")
        if isinstance(self._currentModelIndex_, QtCore.QModelIndex):
            model = self._currentModelIndex_.model()
            modelData = getattr(model, "_modelData_", None)
            if isinstance(model, TabularDataModel) and isinstance(modelData, typing.Iterable):
                row = self._currentModelIndex_.row()
                modelData[row] = val
                topLeft = model.index(row, 0)
                bottomRight = model.index(row, model.columnCount()-1)
                model.dataChanged.emit(topLeft, bottomRight)

            self.sig_indexChanged[QtCore.QModelIndex].emit(self._currentModelIndex_)
            # self.sig_indexChanged.emit(self._currentModelIndex_.row(), self._currentModelIndex_.column())

    @Slot()
    def slot_commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

    @Slot()
    def slot_dataChanged(self):#, o:typing.Any):
        # print(f"{self.__class__.__name__}.slot_dataChanged({o})")
        if hasattr(self.sender(), "getValue"):
            obj = self.sender().getValue()

        elif hasattr(self.sender(), "value"):
            obj = self.sender().value()

        else:
            obj = dataclasses.MISSING

        if (
            (
                isinstance(obj, (bool, np.bool, Tribool,
                            datetime.datetime, datetime.date, datetime.time,
                            int, float, np.floating, np.integer,
                            complex, np.complexfloating,
                            vigra.filters.Kernel1D, vigra.filters.Kernel2D,
                            str, np.character,
                            # bytes, bytearray,
                            ))
                or (
                    isinstance(obj, (pq.Quantity, np.ndarray))
                    and (obj.ndim==0 or (obj.ndim==1 and obj.size==1))
                    )
            )
            and isinstance(self._currentModelIndex_, QtCore.QModelIndex)
            ):
            self.sig_indexChanged[QtCore.QModelIndex].emit(self._currentModelIndex_)
            # self.sig_indexChanged.emit(self._currentModelIndex_.row(), self._currentModelIndex_.column())

        self.sig_dataChanged.emit(self.sender())
        self.sig_contentsChanged.emit()

    @Slot(object)
    @Slot(int)
    @Slot(float)
    @Slot(complex)
    @Slot(str)
    @Slot(np.floating)
    @Slot(np.complexfloating)
    @Slot(np.character)
    @Slot(bool)
    def slot_valueChanged(self, o:object):
        # print(f"{self.__class__.__name__}.slot_valueChanged({o})")
        self.sig_dataChanged.emit(self.sender())
        self.sig_contentsChanged.emit()

    def createEditor(self, parent:QtWidgets.QWidget, option:int,
                     index:QtCore.QModelIndex) -> QtWidgets.QWidget | None:
        r"""Overrides QStyledItemDelegate.createEditor
    """
        self._currentModelIndex_ = index
        # NOTE: 2025-09-27 10:29:14 ATTENTION
        # editor data, although it can also be set here, it should be set through
        # self.setEditorData(), overridden below
        #
        # NOTE: 2025-10-28 12:44:09 FIXME
        # somewhere to provide interconversion between types and string
        # to be shown in the combo box, e.g.:
        # convert to string:                    convert from string
        # int -> str()
        # str -> as is
        # Enum -> 'name' property
        # unit quantity -> str()

        # WARNING: combo boxes can only deal with strings!
        # one should restrict everything to string, in the custom item model, as
        # as this cannot cover every possibility
        #

        data = index.data(ObjectDataRole) # noqa

        if data is not None:
            self._useObjectDataRole_ = True

        else:
            data = index.data(QtCore.Qt.EditRole)
            self._useObjectDataRole_ = False

        # print(f"{self.__class__.__name__}.createEditor -> data is {type(data).__name__}")

        # print(f"{self.__class__.__name__}.createEditor for {type(data).__name__} at row ({index.row()}), col {index.column()}")

        # disp = index.data(QtCore.Qt.DisplayRole)
        # CAUTION: Standard item model and standard items treat DisplayRole and
        # DisplayRole as being the same; in such case I need a custom role
        dataChoices = index.data(DataChoicesRole) # noqa
        if isinstance(data, enum.Enum):
            if dataChoices is None:
                dataChoices = dict(map(lambda x: (x.name, x.value), type(data)))

        # NOTE: 2025-09-27 11:06:52
        # some models may be able to prevent editing indexes with certain rows
        # and/or columns; AFAIK, this functionality is not provided by stock Qt
        # item models and must be implemented in my custom QAbstractItemModel
        # subclasses (e.g. TabularDataModel in tableeditorwidget.py). My implementation
        # employs two pythonic properties of the item model: 'immutableColumns' and
        # 'immutableRows', which I use below
        #
        model = index.model()

        if isinstance(getattr(model, "immutability", None), dict):
            # print(f"{self.__class__.__name__}.createEditor for column {index.column()} and row {index.row()}")
            immutableColumns = model.immutability.get("columns", list())
            immutableRows = model.immutability.get("rows", list())
            jointImmutability = model.immutability.get("joint", False)

            # print(f"\t-> joint immutability: {jointImmutability}")

            if jointImmutability :
                if (index.column() in immutableColumns and index.row() in immutableRows):
                    # print(f"\t-> jointly immutable")
                    return

            else:
                if index.column() in immutableColumns :
                    # print(f"\t-> immutable column")
                    return
                elif index.row() in immutableRows:
                    # print(f"\t-> immutable row")
                    return

        if hasattr(model, "_useExternalDataEditor_") and hasattr(model, "_modelDataColumnHeaders_"):
            if model._useExternalDataEditor_ is True and model._modelDataColumnHeaders_[index.column()] == "Edit":
                widget = QtWidgets.QPushButton(guiutils.getIcon("document-edit"), "", parent)
                # widget = QtWidgets.QPushButton(guiutils.getIcon("document-edit"), "...", parent)
                if hasattr(widget, "setFrame"):
                    widget.setFrame(False)
                    widget.setToolTip("Click to edit the object represented in this row")
                widget.setAutoFillBackground(True)
                widget.setObjectName(f"{type(widget).__name__}_LaunchExternalEdit_delegate")
                widget.clicked.connect(self._slot_editDataExternally)
                return widget

        choices = list()

        if (
            isinstance(dataChoices, typing.Sequence)
            and all(isinstance(v, (enum.Enum, str)) for v in dataChoices)
            ):
            choices = dataChoices

        elif (
            isinstance(dataChoices, dict)
            and all(isinstance(key, str) for key in dataChoices.keys())
            ):
            choices = dataChoices

        elif index.column() in self._columnChoices_:
            if not isinstance(data, str):
                scipywarn(f"{self.__class__.__name__}.createEditor: data type ({type(data).__name__}) is not supported for combo box")
                return
            self.endResetModel()


            choices = self._columnChoices_[index.column()]["choices"]

        w = self.createWidget(data, choices, True, parent)
        return w

    def setEditorData(self, editor: QtWidgets.QWidget,
                      index: QtCore.QModelIndex):
        r"""Sets the value of the editor widget based on the EditRole data in the QModelIndex.
    Overrides QStyledItemDelegate.setEditorData
    """
        from gui.widgets.tableeditorwidget import TableEditorWidget
        data = index.data(ObjectDataRole) # noqa

        # print(f"{self.__class__.__name__}.setEditorData({editor}, index -> data = {data})")

        if data is not None:
            self._useObjectDataRole_ = True
        else:
            data = index.data(QtCore.Qt.EditRole)
            self._useObjectDataRole_ = False

        # NOTE: 2026-02-10 09:48:29
        # because for QStandardItems EditRole and DisplayRole do the same thing
        disp = f"{index.data(QtCore.Qt.DisplayRole)}"
        dataChoices = index.data(DataChoicesRole) # noqa

        if dataChoices:
            choices = dataChoices

        elif index.column() in self._columnChoices_:
            choices = self._columnChoices_[index.column()]["choices"]

        else:
            choices = list()

        if isinstance(editor, QtWidgets.QComboBox):
            # case where we use a QComboBox
            if not isinstance(data, (enum.Enum, int, str)):
                scipywarn(f"{self.__class__.__name__}.createEditor: data type ({type(data).__name__}) is not supported for combo box")
                return

            if (
                isinstance(choices, typing.Sequence)
                and len(choices) > 0
                and all(isinstance(v, (enum.Enum, str)) for v in choices)
                ) or (
                    isinstance(choices, dict)
                    and all(isinstance(k, str) for k in choices.keys())
                    ):
                if isinstance(choices, dict):
                    entries = list(choices.keys())
                    values = list(choices.values())

                else:
                    entries = list(map(lambda x: x.name if isinstance(x, enum.Enum) else x, choices))
                    values = list(map(lambda x: x.value if isinstance(x, enum.Enum) else choices.index(x), choices))

                if (
                        (
                            isinstance(data, enum.Enum) and data.name in entries
                        )
                        or
                        (
                            isinstance(data, str) and data in entries
                        )
                    ):
                    ndx = entries.index(data.name) if isinstance(data, enum.Enum) else entries.index(data)

                elif (
                        (
                            isinstance(data, enum.Enum) and data.value in values
                        )
                        or
                        (
                            isinstance(data, int) and data in values
                        )
                    ):
                    ndx = values.index(data.value) if isinstance(data, enum.Enum) else values.index(data)

                else:
                    scipywarn(f"{self.__class__.__name__}.createEditor: data {data} does not belong to choices ({choices})")
                    return

                editor.setCurrentIndex(ndx)

        else:
            if isinstance(data, bool) or "bool" in type(data).__name__:
                assert isinstance(editor, QtWidgets.QCheckBox), f"Incompatible editor widget type ({type(editor).__name__}) for boolean data"
                editor.setChecked(bool(data) is True) # because data may be of numpy.bool type

            elif isinstance(data, int) or "int" in type(data).__name__:
                assert isinstance(editor, QtWidgets.QSpinBox), f"Incompatible editor widget type ({type(editor).__name__}) for integer data"
                editor.setValue(data)

            elif isinstance(data, float) or "float" in type(data).__name__:
                assert isinstance(editor, QtWidgets.QDoubleSpinBox), f"Incompatible editor widget type ({type(editor).__name__}) for floating point data"
                # NOTE: 2025-09-27 10:31:43
                # figure out how many decimals we've got here, according to
                # the DisplayRole, if DisplayRole is a representation of a
                # float; when there is no decimal point, leave ``decimals``
                # property as per default
                # see also NOTE: 2025-09-27 10:31:23
                if "." in disp:
                    decimals = len(disp[disp.index("."):])

                if isinstance(editor, smw.QuantitySpinBox):
                    editor.keepDimensionless = True
                    editor.forceDimensionless = True

                if "." in disp:
                    editor.setDecimals(decimals)

                editor.setValue(data)

            elif isinstance(data, complex) or "complex" in type(data).__name__:
                assert isinstance(editor, smw.ComplexSpinBox)
                if "." in disp:
                    decimals = len(disp[disp.index("."):])
                else:
                    decimals = 0
                editor.keepDimensionless = True
                editor.forceDimensionless = True
                editor.setDecimals(decimals)
                editor.setValue(data)

            elif isinstance(data, pq.Quantity):
                data_type_name = type(data).__name__
                if isinstance(data, neo.Event):
                    assert isinstance(editor, neow.SimpleTriggerEventWidget), f"Incompatible editor widget type ({type(editor).__name__}) for {data_type_name} data"

                elif isinstance(data, pq.UnitQuantity):
                    assert isinstance(editor, smw.QuantityChooserWidget), f"Incompatible editor widget type ({type(editor).__name__}) for {data_type_name} data"

                else:
                    assert isinstance(editor, (smw.QuantitySpinBox, smw.ComplexSpinBox, TableEditorWidget)), f"Incompatible editor widget type ({type(editor).__name__}) for {data_type_name} data"

                    if not isinstance(editor, TableEditorWidget) and data.ndim > 0:
                        return
                    # if data.ndim > 0: # no editing of Quantity ARRAYS; only scalar Quantities can be edited; unlikely to encounter this, but here we go...
                    #     return

                    # NOTE: 2025-09-27 10:31:23
                    if "." in disp:
                        decimals = len(disp[disp.index("."):])

                    if isinstance(editor, (smw.QuantitySpinBox, smw.ComplexSpinBox)):
                        if isinstance(data, neo.core.dataobject.DataObject):
                            editor.disableUnitChange = True
                        # editor.keepDimensionless = True
                        # editor.forceDimensionless = True
                        editor.setSingleStep(1.0  * data.units)

                        if "." in disp:
                            editor.setDecimals(decimals)

                editor.setValue(data)

            elif isinstance(data, str) or "str" in type(data).__name__:
                assert isinstance(editor, (QtWidgets.QLineEdit, QtWidgets.QPlainTextEdit)), f"Incompatible editor editor type ({type(editor).__name__}) for string data"
                if isinstance(editor, QtWidgets.QLineEdit):
                    editor.setText(data)
                else:
                    editor.setPlainText(data)

            elif isinstance(data, (datetime.datetime, datetime.date, datetime.time)):
                if isinstance(editor, QtWidgets.QDateTimeEdit):
                    if isinstance(data, datetime.datetime):
                        qDate = QtCore.QDate(data.year, data.month, data.day)
                        qTime = QtCore.QTime(data.hour, data.minute, data.second,
                                            int(np.round(data.microsecond/1000, 3)))
                        qDateTime = QtCore.QDateTime(qDate, qTime)
                        editor.setDateTime(qDateTime)

                    elif isinstance(data, datetime.date):
                        qDate = QtCore.QDate(data.year, data.month, data.day)
                        editor.setDate(qDate)

                    else:
                        qTime = QtCore.QTime(data.hour, data.minute, data.second,
                                            int(np.round(data.microsecond/1000, 3)))
                        editor.setTime(qTime)

            elif isinstance(data, pathlib.Path):
                assert isinstance(editor, ifdc.InlineFileDirChooserWidget), f"Incompatible editor editor type ({type(editor).__name__}) for pathlib.Path data"
                editor.setValue(data)


    def setModelData(self, editor: QtWidgets.QWidget,
                     model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        r"""Sets data back into the QModelIndex"""
        originalData = index.data(ObjectDataRole) # noqa

        if originalData is not None:
            self._useObjectDataRole_ = True

        else:
            originalData = index.data(QtCore.Qt.EditRole)
            self._useObjectDataRole_ = False


        if isinstance(editor, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox,
                               smw.QuantitySpinBox, smw.ComplexSpinBox,
                               neow.SimpleTriggerEventWidget)):
            data = editor.value()

        elif isinstance(editor, QtWidgets.QLineEdit):
            data = editor.text()

        elif isinstance(editor, QtWidgets.QComboBox):
            textValue = editor.currentText()
            ndxValue = editor.currentIndex()
            # print(f"{self.__class__.__name__}.setModelData from {type(editor).__name__}: textValue {textValue} -> ndxValue {ndxValue}, for originalData {originalData} ({type(originalData).__name__})")
            # originalData = index.data(ObjectDataRole)

            if isinstance(originalData, enum.Enum):
                data = type(originalData)[textValue]

            elif isinstance(originalData, str):
                data = textValue

            elif isinstance(originalData, int):
                data = ndxValue

            else:
                scipywarn(f"Index data ({type(originalData).__name__}) is not supported by a combo box")
                return

        elif isinstance(editor, QtWidgets.QDateTimeEdit):
            qDateTime = editor.dateTime()
            if not qDateTime.isNull() and qDateTime.isValid():
                qDate = qDateTime.date()
                qTime = qDateTime.time()
                if isinstance(originalData, datetime.datetime):
                    if qDate.isValid() and qTime.isValid():
                        data = datetime.datetime(
                            qDate.year(), qDate.month(), qDate.day(),
                            qTime.hour(), qTime.minute(), qTime.second(),
                            qTime.msec() * 1000)

                elif isinstance(originalData, datetime.date):
                    if qDate.isValid():
                        data = datetime.date(qDate.year(), qDate.month(),
                                              qDate.day())

                elif isinstance(originalData, datetime.time):
                    if qTime.isValid():
                        data = datetime.time(qTime.hour(), qTime.minute(),
                                             qTime.second(), qTime.msec()*1000)

                elif isinstance(originalData, str):
                    data = qDateTime.toString()

                else:
                    return

        elif isinstance(editor, QtWidgets.QCheckBox):
            data = editor.isChecked()

        else:
            return

        role = ObjectDataRole if self._useObjectDataRole_ else QtCore.Qt.EditRole  # noqa
        # print(f"{self.__class__.__name__}.setModelData -> editor: {type(editor).__name__}, row = {index.row()}, column = {index.column()}, data = {data} for role = {role}")
        model.setData(index, data, role)
        if isinstance(self._currentModelIndex_, QtCore.QModelIndex):
            self._currentModelIndex_ = None
