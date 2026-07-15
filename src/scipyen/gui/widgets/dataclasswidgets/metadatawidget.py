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
        self.biologicalSourceWidget.anchoringWidget = self
        self.biologicalSourceWidget.overrideAnchor=True
        self.biologicalSourceWidget.setValue(self._data_.source, objSymbol="source")

        self._collapsibleChildren_["biologicalSourceWidget"] = self.biologicalSourceWidget

    def closeEvent(self, evt):
        self.biologicalSourceWidget.collapseSubWidgets()
        super().closeEvent(evt)
        evt.accept()

    def value(self):
        r"""Returns a dict with field values takes from individual children
        """
        ret = dict()
        ret["VarName"] = strutils.str2symbol(self._dataVarName)
        ret["Name"] = self.dataNameLineEdit.text()
        ret["SourceID"] = self.sourceIDLineEdit.text()
        ret["Cell"] = self.cellIDLineEdit.text()
        ret["Field"] = self.fieldIDLineEdit.text()
        ret["Age"] = self.ageSpinBox.value() # will return units of time
        ret["Sex"] = self.sexComboBox.currentText()
        ret["Genotype"] = self.genotypeComboBox.currentText()

        return ret

    def setValue(self, data: bsc.BaseScipyenData, **kwargs):
        if not isinstance(data, bsc.BaseScipyenData):
            self._data_ = bsc.BaseScipyenData()
        else:
            self._data_ = data

        super().setValue(self._data_, **kwargs)
        # if isinstance(data, dict):
        #     self.dataVarName = os.path.splitext(os.path.basename(fileName))
        #     self.dataName = data.get("Name", self.dataVarName)
        #     self.sourceID = data.get("SourceID", pd.NA)
        #     self.cell = data.get("Cell", pd.NA)
        #     self.field = data.get("Field", pd.NA)
        #     self.age = data.get("Age", pd.NA)
        #     self.sex = data.get("Sex", pd.NA)
        #     self.genotype = data.get("Genotype", pd.NA)

    # def clear(self):
    #     self.dataVarName = ""
    #     self.dataName = ""
    #     self.sourceID = pd.NA
    #     self.cell = pd.NA
    #     self.field = pd.NA
    #     self.age = pd.NA
    #     self.sex = pd.NA
    #     self.genotype = pd.NA

    @Slot(QtCore.QDateTime)
    def _slot_analysisDateTimeChanged(self, val: QtCore.QDateTime):
        self._data_.analysis_datetime = qtutils.datetimeFromQt(val)

    # @Slot()
    # def _slot_setDataName(self):
    #     self._dataName = strutils.str2symbol(self.dataNameLineEdit.text())
    #     self.sig_valueChanged.emit()
    #
    # @Slot()
    # def _slot_setSourceID(self):
    #     self._sourceID = self.sourceIDLineEdit.text()
    #     if self._sourceID in ("NA", "<NA>"):
    #         self._sourceID = pd.NA
    #
    #     self.sig_valueChanged.emit()
    #
    # @Slot()
    # def _slot_setCell(self):
    #     self._cell = self.cellIDLineEdit.text()
    #     if self._cell in ("NA", "<NA>"):
    #         self._cell = pd.NA
    #
    #     self.sig_valueChanged.emit()
    #
    # @Slot()
    # def _slot_setField(self):
    #     self._field = self.fieldIDLineEdit.text()
    #     if self._field in ("NA", "<NA>"):
    #         self._field = pd.NA
    #
    #     self.sig_valueChanged.emit()
    #
    # @Slot(str)
    # def _slot_setGenotype(self, value:str):
    #     if value in ("NA", "<NA>"):
    #         self._genotype = pd.NA
    #
    #     elif len(value.strip()) == 0: # this should never happen, right?
    #         self._genotpye = pd.NA
    #
    #     elif value not in self._available_genotypes_: # and neither this, right?
    #         self._available_genotypes_.append(value)
    #         self._genotype = value
    #
    #     else:
    #         self._genotype = value
    #
    #     self.sig_valueChanged.emit()
    #
    # @Slot(float)
    # def _slot_setAge(self, value):
    #     spinBox = self.sender()
    #     self._age = value * spinBox.units
    #     self._age_units = spinBox.units
    #
    #     self.sig_valueChanged.emit()
    #
    #     # alternatively:
    #     # self._age = spinBox.value()
    #     # self._age_units = self._age.units
    #
    # @Slot(str)
    # def _slot_speciesChanged(self: typing.Self, val: str):
    #     # TODO: 2026-02-15 09:42:03
    #     # choose atlas for species, use interactive modes
    #     # then populate atlas comboBox
    #     if not bgbridge.hasBrainGlobeAtlasAPI:
    #         return
    #
    #     if val == self._current_species_:
    #         # do nothing if species is the same
    #         return
    #
    #     signalBlocker = QtCore.QSignalBlocker(self.atlasesComboBox)
    #
    #     if val in self._available_species_:
    #         # when another species was chose, the list of atlases available for
    #         # the (new) species must be built, and the atlases combo box re-populated
    #         # self._current_species_ = val
    #         atlas_names_for_current_species = self._atlas_manager_.getAtlasNamesForSpecies(val)
    #
    #         if len(atlas_names_for_current_species):
    #             if self.default_brain_atlas_name in atlas_names_for_current_species:
    #                 self._atlas_ = self._atlas_manager_.initAtlas(self.default_brain_atlas_name, interactive=False)
    #             else:
    #                 self._atlas_ = self._atlas_manager_.initAtlas(atlas_names_for_current_species, interactive=True)
    #
    #             if isinstance(self._atlas_, bgbridge.BrainGlobeAtlas):
    #                 self._atlas_names_for_current_species_ = atlas_names_for_current_species
    #                 self._current_species_ = val
    #                 self._current_atlas_name_ = self._atlas_.atlas_name
    #
    #                 self.atlasesComboBox.clear()
    #                 self.atlasesComboBox.addItems(self._atlas_names_for_current_species_)
    #                 ndx = self._atlas_names_for_current_species_.index(self._current_atlas_name_)
    #                 self.atlasesComboBox.setCurrentIndex(ndx)
    #
    #         else:
    #             if (
    #                 isinstance(self._atlas_, bgbridge.BrainGlobeAtlas)
    #                 and isinstance(self._current_atlas_name_, str)
    #                 and self._current_atlas_name_ in self._atlas_names_for_current_species_
    #                 ):
    #                 ndx = self._atlas_names_for_current_species_.index(self._current_atlas_name_)
    #                 self.atlasesComboBox.setCurrentIndex(ndx)
    #
    #             else:
    #                 self.atlasesComboBox.clear() # also consider making it inactive ?
    #                 self._atlas_ = None
    #                 self._current_atlas_name_ = None
    #                 self._atlas_names_for_current_species_ = list()
    #
    # @Slot(str)
    # def _slot_atlasChanged(self: typing.Self, val: str):
    #     # only select from the locally available atlases for the given species;
    #     # to avid complex (and possibly recurrent) code execution, at any one
    #     # time:
    #     # 1) there can be only one species "active"
    #     # 2) there can be only one atlas "active" among the locally available
    #     #   atlases for the currently "active" species
    #     #
    #     #
    #     # In other words, FIRST select a species, THEN select an atlas from
    #     # those available for THAT species, if any.
    #     if not bgbridge.hasBrainGlobeAtlasAPI:
    #         return
    #
    #     atlas = self._atlas_manager_.initAtlas(val, interactive=False)
    #     if atlas.atlas_name == self._atlas_.atlas_name:
    #         return
    #     signalBlocker = QtCore.QSignalBlocker(self.structuresComboBox)
    #     currently_selected_structure_name = self.structuresComboBox.currentText()
    #     structure = bgbridge.get_atlas_structure(currently_selected_structure_name,
    #                                              atlas)
    #     self._atlas_ = atlas
    #     self._current_atlas_name_ = self._atlas_.atlas_name
    #     self.structuresComboBox.clear()
    #
    #
    # @Slot(str)
    # def _slot_setSex(self, value:str):
    #     if value in ("NA", "<NA>"):
    #         self._sex = pd.NA
    #     elif value not in self._available_sex_: # this should never happen, right?
    #         self._sex = pd.NA
    #
    #     else:
    #         self._sex = value
    #
    #     self.sig_valueChanged.emit()
    #
    # @Slot()
    # def _slot_editAnnotations(self):
    #     # TODO 2022-11-08 08:31:20
    #     # enable a scrollable view in GenericMappingDialog
    #     # when there are more than 5-6 entries in the mapping
    #     # use that to edit annotations
    #     self.sig_valueChanged.emit()
    #
    #     print("edit annotations")
    #
    # @Slot()
    # def _slot_editBiometrics(self):
    #     # TODO 2022-11-08 08:32:12
    #     # use GenericMappingDialog
    #     self.sig_valueChanged.emit()
    #
    #     print("edit biometrics")
    #
    # @Slot()
    # def _slot_editDateTime(self):
    #     r"""Edits the date & time of analysis.
    #     Recording date & time should be immutable
    #     """
    #     # TODO 2022-11-08 08:32:23
    #     # create DateTimeInput widget in gui.quickdialog, use here wrapped
    #     # in a quickdialog
    #
    #     from gui import quickdialog as qd
    #
    #     qde = QtWidgets.QDateTimeEdit(self._dateTime)
    #     dfmt = qde.displayFormat()
    #     dlg = qd.QuickDialog(parent=self, title = "Set analysis date and time")
    #     dlg.addWidget(qde)
    #     dlg.adjustSize()
    #     ret = dlg.exec()
    #
    #     if ret == QtWidgets.QDialog.Accepted:
    #         self._dateTime = qde.dateTime().toPyDateTime()
    #
    #     self.sig_valueChanged.emit()
    #
    #     print("edit datetime")
    #
    # @Slot()
    # def _slot_descriptionChanged(self):
    #     self._data_description_ = self._descriptionEditor.text(True)
    #     self.sig_valueChanged.emit()
    #
    # @Slot()
    # def _slot_editDescription(self):
    #     self._descriptionEditor.setData(self._data_description_)
    #     self._descriptionEditor.show()

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

        self.sig_valueChanged.emit()
        print("edit procedures")

    @Slot()
    def _slot_editTriggers(self):
        # TODO: 2022-11-08 08:36:10
        # use gui.triggerprotocolseditordialog.TriggerProtocolsEditorDialog
        # but with the following functions enabled conditionally:
        #
        # trigger detection ↔ is there ephysdata available

        self.sig_valueChanged.emit()
        print("edit triggers")

    # @Slot()
    # def _slot_importMetaData(self):
    #     from gui.workspacegui import WorkspaceGuiMixin
    #     parentWindow = self.window()
    #     if isinstance(parentWindow, WorkspaceGuiMixin):
    #         objs = parentWindow.importWorkspaceData((dict,),
    #                                                 title="Import MetaData from workspace",
    #                                                 single=True,
    #                                                 with_varName=False)
    #
    #         if len(objs) == 1:
    #             self.setValue(objs[0])
    #

    # @Slot()
    # def _slot_exportMetaData(self):
    #     from gui.workspacegui import WorkspaceGuiMixin
    #     value = self.value()
    #     parentWindow = self.window()
    #     if len(value) and isinstance(parentWindow, WorkspaceGuiMixin):
    #         parentWindow.exportDataToWorkspace(value, "MetaData", title="Export MetaData to Workspace")
    #
    # @Slot()
    # def _slot_loadMetaData(self):
    #     from gui.workspacegui import WorkspaceGuiMixin
    #     parentWindow = self.window()
    #     if isinstance(parentWindow, WorkspaceGuiMixin):
    #         fileName, fileFilter = self.chooseFile(caption="Open electrophysiology file",
    #                                             single=True,
    #                                             save=False,
    #                                             fileFilter=";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]))
    #         if isinstance(fileName, str) and os.path.isfile(fileName):
    #             if "HDF5" in fileFilter:
    #                 data = pio.loadHDF5File(fileName)
    #             elif "Pickle" in fileFilter:
    #                 data = pio.loadPickleFile(fileName)
    #             else:
    #                 return
    #
    #         self.setValue(data)

    # @Slot()
    # def _slot_saveMetaData(self):
    #     from gui.workspacegui import WorkspaceGuiMixin
    #     value = self.value()
    #     parentWindow = self.window()
    #     if len(value) and isinstance(parentWindow, WorkspaceGuiMixin):
    #         fileName, fileFilter = parentWindow.chooseFile(caption="Save electrophysiology data",
    #                                             single=True,
    #                                             save=True,
    #                                             fileFilter=";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]))
    #         if isinstance(fileName, str) and len(fileName.strip()):
    #             if "HDF5" in fileFilter:
    #                 pio.saveHDF5(value, fileName)
    #             else:
    #                 pio.savePickleFile(value, fileName)


    # @property
    # def dataVarName(self):
    #     return self._dataVarName
    #
    # @dataVarName.setter
    # def dataVarName(self, value:str):
    #     if isinstance(value, str) and len(value.strip()):
    #         val = strutils.str2symbol(value)
    #         self._dataVarName = val
    #     else:
    #         self._dataVarName = ""
    #
    #     self.dataVarNameLabel.setText(self._dataVarName)

    # @property
    # def dataDescription(self):
    #     return self._data_description_
    #
    # @dataDescription.setter
    # def dataDescription(self, value:typing.Optional[str] = None):
    #     if value is None:
    #         self._data_description_ = ""
    #     else:
    #         self._data_description_ = str(value)
    #
    # @property
    # def dataName(self):
    #     r"""Getter & setter for the data name"""
    #     return self._dataName
    #
    # @dataName.setter
    # def dataName(self, value:str):
    #     # WARNING: 2022-11-09 16:07:02
    #     # do NOT use this setter from within the slot connected to the
    #     # dataNameLineEdit!
    #     signalBlocker = QtCore.QSignalBlocker(self.dataNameLineEdit)
    #     if isinstance(value, str) and len(value.strip()):
    #         self._dataName = strutils.str2symbol(value)
    #     else:
    #         self._dataName = ""
    #
    #     self.dataNameLineEdit.setText(self._dataName)

        self.sig_valueChanged.emit()

    # @property
    # def sourceID(self):
    #     return self._sourceID
    #
    # @sourceID.setter
    # def sourceID(self, value:typing.Union[str, type(pd.NA)]):
    #     signalBlocker = QtCore.QSignalBlocker(self.sourceIDLineEdit)
    #     if isinstance(value, str) and len(value.strip()):
    #         self._sourceID = value
    #         if self._sourceID in ("NA", "<NA>"):
    #             self._souceID = pd.NA
    #     else:
    #         self._sourceID = pd.NA
    #
    #     self.sourceIDLineEdit.setText(f"{self._sourceID}")
    #
    #     self.sig_valueChanged.emit()

    # @property
    # def cell(self):
    #     return self._cell
    #
    # @cell.setter
    # def cell(self, value:typing.Union[str, type(pd.NA)]):
    #     signalBlocker = QtCore.QSignalBlocker(self.cellIDLineEdit)
    #     if isinstance(value, str) and len(value.strip()):
    #         self._cell = value
    #         if self._cell in ("NA", "<NA>"):
    #             self._cell = pd.NA
    #     else:
    #         self._cell = pd.NA
    #
    #     self.cellIDLineEdit.setText(f"{self._cell}")
    #
    #     self.sig_valueChanged.emit()
    #
    # @property
    # def analysisDateTime(self):
    #     return self._dateTime
    #
    # @analysisDateTime.setter
    # def analysisDateTime(self, value:datetime.datetime):
    #     if not isinstance(value, datetime.datetime):
    #         raise TypeError(f"Expecting a datetime.datetime; got {type(value).__name__} instead")
    #
    #     self._dateTime = value

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




