# -*- coding: utf-8 -*-
"""Common widget for meta-information in results
"""
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import sys, os, typing
import pathlib
# import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    # import PySide6
    from PySide6 import Shiboken # noqa
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


from core.prog import safewrapper, scipywarn, print_styled
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

import math, datetime
import numpy as np
import quantities as pq
import pandas as pd

import core.bgbridge as bgbridge

from core import scipyendataclasses as sdc
from core import basescipyen as bsc
from core import scipyen_quantities as scq
from core import strutils
from core import qtutils
from core.datatypes import UnitTypes, GENOTYPES

from core import workspacefunctions as wsf
from dataclasses import (dataclass, asdict)

from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget
# from gui.textviewer import TextViewer
# from gui.widgets.datatreeview import DataTreeView

Ui_MetaDataWidget, QWidget = loadUiType(os.path.join(__module_path__, "metadatawidget.ui"))
# Ui_MetaDataWidget, QWidget = loadUiType(os.path.join(__module_path__, "metadatawidget_new_26b13.ui"))

class MetaDataWidget(Ui_MetaDataWidget, DataClassWidget):
    r"""Widget for displaying BaseScipyenData objectx.
    Where implemented, it also supports editing.
    NOTE/WARNING: Under development
    """
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    # default_brain_atlas_name =  'whs_sd_rat_39um'
    # default_species = "Rattus norvegicus"

    _objectTypes_ = (bsc.BaseScipyenData, )

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget]=None,
                 obj: typing.Optional[bsc.BaseScipyenData] = None,
                 **kwargs):
        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        if not isinstance(obj, self._objectTypes_):
            self._data_ = self._objectTypes_[0]()
        else:
            self._data_ = obj

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_() # DataClassWidget!

        file_origin = ""
        if isinstance(self._data_.file_origin, pathlib.Path):
            file_origin = self._data_.file_origin.as_posix()
        elif isinstance(self._data_.file_origin, str):
            file_origin = self._data_.file_origin

        if isinstance(self._data_.file_datetime, datetime.datetime):
            file_datetime = f"{self._data_.file_datetime}"
        else:
            file_datetime = ""

        if len(file_origin.strip()):
            if len(file_datetime.strip()):
                self.fileOriginLabel.setText(f"{file_origin} ({file_datetime})")
            else:
                self.fileOriginLabel.setText(file_origin)
        else:
            self.fileOriginLabel.setText("")

        if isinstance(self._data_.rec_datetime, datetime.datetime):
            self.recDateTimeLabel.setText(f"{self._data_.rec_datetime}")
        else:
            self.recDateTimeLabel.setText("")

        if isinstance(self._data_.analysis_datetime, datetime.datetime):
            self.analysisDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._data_.analysis_datetime))
        else:
            self.analysisDateTimeEdit.setDateTime(qtutils.datetime2Qt(datetime.datetime.now()))

        self.analysisDateTimeEdit.dateTimeChanged.connect(self._slot_analysisDateTimeChanged)

        self.biologicalSourceEditor = None
        self.bioSourceEditorToolButton.toggled.connect(self._slot_toggleBioSourceEditor)
        self._collapsibleChildren_["biologicalSourceEditor"] = self.biologicalSourceEditor

        self.asruEditor = None
        self.editASRUToolButton.toggled.connect(self._slot_toggleASRUEditor)
        self._collapsibleChildren_["asruEditor"] = self.asruEditor

    def closeEvent(self, evt):
        self.closeSubWidgets()
        super().closeEvent(evt)
        evt.accept()

    def closeSubWidgets(self):
        if isinstance(self.biologicalSourceEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.biologicalSourceEditor):
            self.biologicalSourceEditor.close()
            self.biologicalSourceEditor.deleteLater()
            self.biologicalSourceEditor = None

        super().closeSubWidgets()

    def value(self):
        r"""Returns a dict with field values takes from individual children
        """
        return self._data_

    def setValue(self, data: bsc.BaseScipyenData, **kwargs):
        if not isinstance(data, bsc.BaseScipyenData):
            self._data_ = bsc.BaseScipyenData()
        else:
            self._data_ = data

        super().setValue(self._data_, **kwargs)

        if isinstance(self.biologicalSourceEditor, DataClassWidget):
            sb = QtCore.QSignalBlocker(self.biologicalSourceEditor)
            self.biologicalSourceEditor.setValue(self._data_.source, objSymbol="source")

    @Slot()
    def _slot_editBiologicalSource(self):
        from gui.widgets.dataclasswidgets.biologicalsourcewidget import BiologicalSourceWidget
        anchoringWidget = self.anchoringWidget if (isinstance(self._anchoringWidget_, QtWidgets.QWidget) and self.overrideAnchor) else self if self.parent() is None else None
        if not isinstance(self._data_.source, BiologicalSourceWidget):
            if isinstance(self.biologicalSourceEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.biologicalSourceEditor):
                self.biologicalSourceEditor.close()
                self.biologicalSourceEditor.deleteLater()
                self.biologicalSourceEditor = None

            self.biologicalSourceEditor = BiologicalSourceWidget(anchoringWidget=anchoringWidget)
            self.biologicalSourceEditor.setWindowTitle("Source")
            self.biologicalSourceEditor.sig_valueChanged.connect(self._slot_biologicalSourceChanged)
            self.biologicalSourceEditor.sig_closing.connect(self._slot_biologicalSourceEditorClosing)
            self.biologicalSourceEditor.sig_collapsed.connect(self._slot_biologicalSourceEditorCollapsed)

        self._collapsibleChildren_["biologicalSourceEditor"] = self.biologicalSourceEditor
        self.biologicalSourceEditor.setValue(self._data_.source, objSymbol="source")

        if not self.biologicalSourceEditor.isVisible():
            self.biologicalSourceEditor.show()

    @Slot()
    def _slot_biologicalSourceEditorCollapsed(self):
        sb = QtCore.QSignalBlocker(self.bioSourceEditorToolButton) # noqa
        self.bioSourceEditorToolButton.setChecked(False)

    @Slot()
    def _slot_biologicalSourceEditorClosing(self):
        sb = QtCore.QSignalBlocker(self.bioSourceEditorToolButton) # noqa
        self.bioSourceEditorToolButton.setChecked(False)

    @Slot(object)
    def _slot_biologicalSourceChanged(self, val: sdc.BiologicalSource):
        if isinstance(val, sdc.BiologicalSource):
            self._data_.source = val
        else:
            self._data_.source = sdc.BiologicalSource()

        self.sig_valueChanged.emit(self._data_)

    @Slot(bool)
    def _slot_toggleBioSourceEditor(self, val: bool):
        if val is True:
            self._slot_editBiologicalSource()
        else:
            if isinstance(self.biologicalSourceEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.biologicalSourceEditor):
                self.biologicalSourceEditor.collapse(False)

    @Slot(bool)
    def _slot_toggleASRUEditor(self, val: bool):
        if val is True:
            self._slot_editASRU()
        else:
            if isinstance(self.asruEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.asruEditor):
                self.asruEditor.collapse(False)

    @Slot()
    def _slot_editASRU(self): # TODO
        pass
        # from gui.widgets.dataclasswidgets.asruwidgets import
    #     anchoringWidget = self.anchoringWidget if (isinstance(self._anchoringWidget_, QtWidgets.QWidget) and self.overrideAnchor) else self if self.parent() is None else None
    #     if not isinstance(self._data_.source, BiologicalSourceWidget):
    #         if isinstance(self.biologicalSourceEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.biologicalSourceEditor):
    #             self.biologicalSourceEditor.close()
    #             self.biologicalSourceEditor.deleteLater()
    #             self.biologicalSourceEditor = None
    #
    #         self.biologicalSourceEditor = BiologicalSourceWidget(anchoringWidget=anchoringWidget)
    #         self.biologicalSourceEditor.setWindowTitle("Source")
    #         self.biologicalSourceEditor.sig_valueChanged.connect(self._slot_biologicalSourceChanged)
    #         self.biologicalSourceEditor.sig_closing.connect(self._slot_biologicalSourceEditorClosing)
    #         self.biologicalSourceEditor.sig_collapsed.connect(self._slot_biologicalSourceEditorCollapsed)
    #
    #     self._collapsibleChildren_["biologicalSourceEditor"] = self.biologicalSourceEditor
    #     self.biologicalSourceEditor.setValue(self._data_.source, objSymbol="source")
    #
    #     if not self.biologicalSourceEditor.isVisible():
    #         self.biologicalSourceEditor.show()
    #
    # @Slot()
    # def _slot_biologicalSourceEditorCollapsed(self):
    #     sb = QtCore.QSignalBlocker(self.bioSourceEditorToolButton) # noqa
    #     self.bioSourceEditorToolButton.setChecked(False)
    #
    # @Slot()
    # def _slot_biologicalSourceEditorClosing(self):
    #     sb = QtCore.QSignalBlocker(self.bioSourceEditorToolButton) # noqa
    #     self.bioSourceEditorToolButton.setChecked(False)
    #
    # @Slot(object)
    # def _slot_biologicalSourceChanged(self, val: sdc.BiologicalSource):
    #     if isinstance(val, sdc.BiologicalSource):
    #         self._data_.source = val
    #     else:
    #         self._data_.source = sdc.BiologicalSource()
    #
    #     self.sig_valueChanged.emit(self._data_)

    @Slot(QtCore.QDateTime)
    def _slot_analysisDateTimeChanged(self, val: QtCore.QDateTime):
        self._data_.analysis_datetime = qtutils.datetimeFromQt(val)

        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_editProcedures(self):
        # TODO: 2022-11-08 08:35:39
        # use GenericMappingDialog
        # TODO: 2022-11-08 08:36:52
        # create an EpochWidget for gui.quickdialog, to edit/generate
        # neo.Epoch with intervals
        # SUGGEST: use TriggerProtocolsEditorDialog as a model of what an
        # EpochEditor may look like:
        # A QListView with Epoch names (thus being able to handle more
        # than one Epoch)
        # a QTableView with headings: "Name", "Start", "Duration" and one row
        # per Epoch interval - populated with data from the Epoch selected in
        # the list view
        #
        # TODO: 2022-11-08 08:37:39 (maybe)
        # create a Gantt chart-like widget viewer to include with the
        # epoch editor

        self.sig_valueChanged.emit(self._data_)
        print("edit procedures")

    @property
    def field(self):
        return self._field

    @field.setter
    def field(self, value:typing.Union[str, type(pd.NA)]):
        signalBlocker = QtCore.QSignalBlocker(self.fieldIDLineEdit)
        if isinstance(value, str) and len(value.strip()):
            self._field = value
            if self._field in ("NA", "<NA>"):
                self._field = pd.NA
        else:
            self._field = pd.NA

        self.fieldIDLineEdit.setText(f"{self._field}")

        self.sig_valueChanged.emit()

    # @property
    # def genotype(self):
    #     return self._genotype
    #
    # @genotype.setter
    # def genotype(self, value:typing.Union[str, type(pd.NA)]):
    #     updateCombo = False
    #     if isinstance(value, str):
    #         if len(value.strip()):
    #             if value in ("NA", "<NA>"):
    #                 self._genotype = pd.NA
    #             elif value not in self._available_genotypes_:
    #                 self._available_genotypes_.append(value)
    #                 updateCombo = True
    #                 self._genotype = value
    #             else:
    #                 self._genotype = value
    #
    #     else:
    #         self._genotype = pd.NA
    #
    #     signalBlocker = QtCore.QSignalBlocker(self.genotypeComboBox)
    #     if updateCombo:
    #         self.genotypeComboBox.clear()
    #         self.genotypeComboBox.setItems(self._available_genotypes_)
    #
    #     if self._genotype is pd.NA:
    #         self.genotypeComboBox.setCurrentIndex(0)
    #     else:
    #         ndx = self._available_genotypes_.index(self._genotype)
    #         self.genotypeComboBox.setCurrentIndex(ndx)
    #
    #     self.sig_valueChanged.emit()
    #
    # @property
    # def sex(self):
    #     return self._sex
    #
    # @sex.setter
    # def sex(self, value:typing.Union[str, type(pd.NA)]):
    #     if isinstance(value, str):
    #         if value in ("NA", "<NA>"):
    #             self._sex = pd.NA
    #             sex_ndx = 0
    #
    #         elif value in self._available_sex_:
    #             self._sex = value
    #             sex_ndx = self._available_sex_.index(value)
    #
    #         else:
    #             self._sex = pd.NA
    #             sex_ndx = 0
    #     else:
    #         self._sex = pd.NA
    #         sex_ndx = 0
    #
    #     signalBlocker = QtCore.QSignalBlocker(self.sexComboBox)
    #     self.sexComboBox.setCurrentIndex(sex_ndx)
    #
    #     self.sig_valueChanged.emit()
    #
    # @property
    # def age(self):
    #     return self._age
    #
    # @age.setter
    # def age(self, value):
    #     if isinstance(value, pq.Quantity):
    #         if not scq.checkTimeUnits(value):
    #             raise TypeError(f"Age must be given in time units; instead got {value}")
    #
    #         self._age_units = value.units
    #     else:
    #         self._age_units = pq.div
    #         self._age  = value * self._age_units
    #
    #     signalBlocker = QtCore.QSignalBlocker(self.ageSpinBox)
    #     self.ageSpinBox.setValue(self._age)
    #
    #     self.sig_valueChanged.emit()




