# -*- coding: utf-8 -*-
"""Common widget for meta-information in results
"""
import os, math, typing, datetime, dataclasses
from dataclasses import MISSING
import numpy as np
import quantities as pq
from core import quantities as scq
from core import strutils
from core.datatypes import UnitTypes, GENOTYPES, NoData
from core.basescipyen import BaseScipyenData
import pandas as pd

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType

from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget
from gui.textviewer import TextViewer

__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_BaseScipyenDataWidget, QWidget = loadUiType(os.path.join(__module_path__, "basescipyendatawidget.ui"))

class BaseScipyenDataWidget(Ui_BaseScipyenDataWidget, QWidget):
    """Widget for displaying the most commonly used data attributes in Scipyen.
    Where implemented, it also supports editing.
    NOTE/WARNING: Under development
    """
    sig_valueChanged = Signal(name="sig_valueChanged")
    
    def __init__(self, parent=None, **kwargs):
        QWidget.__init__(self, parent=parent)
        
        self._dataVarName = kwargs.pop("varname", "")
        self._dataName = kwargs.pop("name", "")
        self._dateTime = datetime.datetime.now()
        
        for name in ("sourceID","cell","field","sex","genotype"):
            val = kwargs.pop(name, pd.NA)
            if isinstance(val, str) and len(val.strip()):
                setattr(self, f"_{name}", val)
            else:
                setattr(self, f"_{name}", pd.NA)


        self._available_genotypes_ = kwargs.pop("default_genotypes", GENOTYPES)
        self._available_sex_ = ["NA", "F", "M"]
        
        if isinstance(self._genotype, str):
            if len(self._genotype.strip()):
                if self._genotype not in self._available_genotypes_:
                    self._available_genotypes_.append(self._genotype)
                    
                elif self._genotype in ("NA", "<NA>"):
                    self._genotype = pd.NA
                    
            else:
                self._genotype = pd.NA
                
        else:
            self._genotype = pd.NA
        
        val = kwargs.pop("age", pd.NA)
        if isinstance(val, pq.Quantity) and scq.checkTimeUnits(val):
            self._age = val
        else:
            self._age = pd.NA
        
        if isinstance(self._age, pq.Quantity):
            if not scq.checkTimeUnits(self._age):
                raise TypeError(f"Age must be given in time units; instead got {self._age}")
            
            self._age_units = self._age.units
        else:
            self._age_units = pq.div
            self._age  = self._age * self._age_units
        
        self._biometrics_ = kwargs.pop("biometrics", dict())
        
        self._procedures_ = kwargs.pop("procedures", dict())
        
        self._annotations_ = kwargs.pop("annotations", dict())
        
        self._data_description_ = kwargs.pop("description", "")
        
        self._configureUI_()
        
    def _configureUI_(self):
        self.setupUi(self)
        
        self.dataVarNameLabel.setText(self._dataVarName)
        
        self.dataNameLineEdit.setClearButtonEnabled(True)
        self.dataNameLineEdit.undoAvailable = True
        self.dataNameLineEdit.redoAvailable =True
        self.dataNameLineEdit.setText(self._dataName)
        self.dataNameLineEdit.editingFinished.connect(self._slot_setDataName)
        
        self.sourceIDLineEdit.setText(f"{self._sourceID}")
        self.sourceIDLineEdit.setClearButtonEnabled(True)
        self.sourceIDLineEdit.undoAvailable = True
        self.sourceIDLineEdit.redoAvailable = True
        self.sourceIDLineEdit.editingFinished.connect(self._slot_setSourceID)
        
        self.cellIDLineEdit.setText(f"{self._cell}")
        self.cellIDLineEdit.setClearButtonEnabled(True)
        self.cellIDLineEdit.undoAvailable = True
        self.cellIDLineEdit.redoAvailable = True
        self.cellIDLineEdit.editingFinished.connect(self._slot_setCell)
        
        self.fieldIDLineEdit.setText(f"{self._field}")
        self.fieldIDLineEdit.setClearButtonEnabled(True)
        self.fieldIDLineEdit.undoAvailable = True
        self.fieldIDLineEdit.redoAvailable = True
        self.fieldIDLineEdit.editingFinished.connect(self._slot_setField)
        
        self.ageSpinBox.unitsFamily = "Time"
        self.ageSpinBox.units = self._age.units if isinstance(self._age, pq.Quantity) else pq.dimensionless
        self.ageSpinBox.singleStep = 0.01
        self.ageSpinBox.decimals = 2
        self.ageSpinBox.setValue(self._age)
        self.ageSpinBox.valueChanged.connect(self._slot_setAge)
        
        self.sexComboBox.setEditable(False)
        self.sexComboBox.addItems(self._available_sex_)
        if self._sex is pd.NA or self._sex not in self._available_sex_:
            sex_ndx = 0
        else:
            sex_ndx  = self._available_sex_.index(self._sex)
            
        self.sexComboBox.setCurrentIndex(sex_ndx)
        self.sexComboBox.currentTextChanged.connect(self._slot_setSex)
        
        self.genotypeComboBox.setEditable(True)
        # self.genotypeComboBox.setInsertPolicy(QtWidgets.QComboBox.InsertAtBottom)
        self.genotypeComboBox.lineEdit().setClearButtonEnabled(True)
        self.genotypeComboBox.lineEdit().redoAvailable = True
        self.genotypeComboBox.lineEdit().undoAvailable = True
        self.genotypeComboBox.addItems(self._available_genotypes_)
        # NOTE: 2022-11-07 14:03:58
        # allow custom genotype strings
        # NA is always at 0
        if self._genotype is pd.NA:
            genotype_ndx = 0
        else:
            if self._genotype not in self._available_genotypes_:
                self._available_genotypes_.append(f"{self._genotype}")
                
            genotype_ndx = self._available_genotypes_.index(self._genotype) 
            
        self.genotypeComboBox.setCurrentIndex(genotype_ndx)
        self.genotypeComboBox.currentTextChanged.connect(self._slot_setGenotype)
        
        self.biometricsToolButton.triggered.connect(self._slot_editBiometrics)
        self.procedureToolButton.triggered.connect(self._slot_editProcedures)
        self.triggersToolButton.triggered.connect(self._slot_editTriggers)
        self.dateTimeToolButton.triggered.connect(self._slot_editDateTime)
        self.annotationsToolButton.triggered.connect(self._slot_editAnnotations)
        self.notesToolButton.triggered.connect(self._slot_editDescription)
        
        self.exportToolButton.triggered.connect(self._slot_exportMetaData)
        self.saveToolButton.triggered.connect(self._slot_saveMetaData)
        self.importToolButton.triggered.connect(self._slot_importMetaData)
        self.loadToolButton.triggered.connect(self._slot_loadMetaData)
        
        self._descriptionEditor = TextViewer(self._data_description_, 
                                             parent=self, edit=True, 
                                             win_title="Edit description",
                                             doc_title="Edit description",
                                             title="mPSC Detect")
        self._descriptionEditor.setVisible(False)
        self._descriptionEditor.sig_textChanged.connect(self._slot_descriptionChanged)
        
    def value(self):
        """Returns a dict with field values takes from individual children
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
    
    def setValue(self, data:dict):
        if isinstance(data, dict):
            self.dataVarName = os.path.splitext(os.path.basename(data.get("file_origin", "")))[0]
            self.dataName = data.get("name", self.dataVarName)
            self.sourceID = data.get("sourceID", pd.NA)
            self.cell = data.get("cell", pd.NA)
            self.field = data.get("field", pd.NA)
            self.age = data.get("age", pd.NA)
            self.sex = data.get("sex", pd.NA)
            self.genotype = data.get("genotype", pd.NA)
            self.dataDescription = data.get("description", "")
            
    def populate(self, data:BaseScipyenData):
        self.setValue(dataclasses.asdict(data))
        
    def clear(self):
        self.dataVarName = ""
        self.dataName = ""
        self.sourceID = pd.NA
        self.cell = pd.NA
        self.field = pd.NA
        self.age = pd.NA
        self.sex = pd.NA
        self.genotype = pd.NA
        self.dataDescription = ""
            
    @Slot()
    def _slot_setDataName(self):
        self._dataName = strutils.str2symbol(self.dataNameLineEdit.text())
        self.sig_valueChanged.emit()
        
    @Slot()
    def _slot_setSourceID(self):
        self._sourceID = self.sourceIDLineEdit.text()
        if self._sourceID in ("NA", "<NA>"):
            self._sourceID = pd.NA
            
        self.sig_valueChanged.emit()
    
    @Slot()
    def _slot_setCell(self):
        self._cell = self.cellIDLineEdit.text()
        if self._cell in ("NA", "<NA>"):
            self._cell = pd.NA
            
        self.sig_valueChanged.emit()
    
    @Slot()
    def _slot_setField(self):
        self._field = self.fieldIDLineEdit.text()
        if self._field in ("NA", "<NA>"):
            self._field = pd.NA
            
        self.sig_valueChanged.emit()
            
    @Slot(str)
    def _slot_setGenotype(self, value:str):
        if value in ("NA", "<NA>"):
            self._genotype = pd.NA
        
        elif len(value.strip()) == 0: # this should never happen, right?
            self._genotpye = pd.NA
        
        elif value not in self._available_genotypes_: # and neither this, right?
            self._available_genotypes_.append(value)
            self._genotype = value
            
        else:
            self._genotype = value

        self.sig_valueChanged.emit()
            
    @Slot(float)
    def _slot_setAge(self, value):
        spinBox = self.sender()
        self._age = value * spinBox.units
        self._age_units = spinBox.units
        
        self.sig_valueChanged.emit()
            
        # alternatively:
        # self._age = spinBox.value()
        # self._age_units = self._age.units
            
    @Slot(str)
    def _slot_setSex(self, value:str):
        if value in ("NA", "<NA>"):
            self._sex = pd.NA
        elif value not in self._available_sex_: # this should never happen, right?
            self._sex = pd.NA
            
        else:
            self._sex = value
    
        self.sig_valueChanged.emit()
            
    @Slot()
    def _slot_editAnnotations(self):
        # TODO 2022-11-08 08:31:20
        # enable a scrollable view in GenericMappingDialog
        # when there are more than 5-6 entries in the mapping
        # use that to edit annotations
            
        print("edit annotations")
        # self.sig_valueChanged.emit()
    
    @Slot()
    def _slot_editBiometrics(self):
        # TODO 2022-11-08 08:32:12
        # use GenericMappingDialog
            
        print("edit biometrics")
        # self.sig_valueChanged.emit()
    
    @Slot()
    def _slot_editDateTime(self):
        """Edits the date & time of analysis.
        Recording date & time should be immutable
        """
        # TODO 2022-11-08 08:32:23
        # create DateTimeInput widget in gui.quickdialog, use here wrapped
        # in a quickdialog
        
        from gui import quickdialog as qd

        qde = QtWidgets.QDateTimeEdit(self._dateTime)
        dfmt = qde.displayFormat()
        dlg = qd.QuickDialog(parent=self, title = "Set analysis date and time")
        dlg.addWidget(qde)
        
        ret = dlg.exec()
        
        if ret == QtWidgets.QDialog.Accepted:
            self._dateTime = qde.dateTime().toPyDateTime()
        
        self.sig_valueChanged.emit()
            
        print("edit datetime")
        
    @Slot()
    def _slot_descriptionChanged(self):
        self._data_description_ = self._descriptionEditor.text(True)
        self.sig_valueChanged.emit()
            
    @Slot()
    def _slot_editDescription(self):
        self._descriptionEditor.setData(self._data_description_)
        self._descriptionEditor.show()
        
    @Slot()
    def _slot_editProcedures(self):
        # TODO: 2022-11-08 08:35:39 
        # use GenericMappingDialog
        # TODO: 2022-11-08 08:36:52
        # create an EpochWidget for gui.quickdialog, to edit/generate
        # neo.Epoch with intervals
        # SUGGEST: use ProtocolEditorDialog as a model of what an
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
        # use gui.protocoleditordialog.ProtocolEditorDialog
        # but with the following functions enabled conditionally: 
        #
        # trigger detection ↔ is there ephysdata available
        
        self.sig_valueChanged.emit()
        print("edit triggers")
    
    @Slot()
    def _slot_importMetaData(self):
        from gui.workspacegui import WorkspaceGuiMixin
        parentWindow = self.window()
        if isinstance(parentWindow, WorkspaceGuiMixin):
            objs = parentWindow.importWorkspaceData((dict,), 
                                                    title="Import MetaData from workspace",
                                                    single=True,
                                                    with_varName=False)
            
            if len(objs) == 1:
                self.setValue(objs[0])
                
        
    @Slot()
    def _slot_exportMetaData(self):
        from gui.workspacegui import WorkspaceGuiMixin
        value = self.value()
        parentWindow = self.window()
        if len(value) and isinstance(parentWindow, WorkspaceGuiMixin):
            parentWindow.exportDataToWorkspace(value, "MetaData", title="Export MetaData to Workspace")
        
    @Slot()
    def _slot_loadMetaData(self):
        from gui.workspacegui import WorkspaceGuiMixin
        parentWindow = self.window()
        if isinstance(parentWindow, WorkspaceGuiMixin):
            fileName, fileFilter = self.chooseFile(caption="Open electrophysiology file",
                                                single=True,
                                                save=False,
                                                fileFilter=";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]))
            if isinstance(fileName, str) and os.path.isfile(fileName):
                if "HDF5" in fileFilter:
                    data = pio.loadHDF5File(fileName)
                elif "Pickle" in fileFilter:
                    data = pio.loadPickleFile(fileName)
                else:
                    return
                
            self.setValue(data)

    @Slot()
    def _slot_saveMetaData(self):
        from gui.workspacegui import WorkspaceGuiMixin
        value = self.value()
        parentWindow = self.window()
        if len(value) and isinstance(parentWindow, WorkspaceGuiMixin):
            fileName, fileFilter = parentWindow.chooseFile(caption="Save electrophysiology data",
                                                single=True,
                                                save=True,
                                                fileFilter=";;".join(["Pickle files (*.pkl)", "HDF5 Files (*.hdf)"]))
            if isinstance(fileName, str) and len(fileName.strip()):
                if "HDF5" in fileFilter:
                    pio.saveHDF5(value, fileName)
                else:
                    pio.savePickleFile(value, fileName)
            
    
    @property
    def dataVarName(self):
        return self._dataVarName
    
    @dataVarName.setter
    def dataVarName(self, value:str):
        if isinstance(value, str) and len(value.strip()):
            val = strutils.str2symbol(value)
            self._dataVarName = val
        else:
            self._dataVarName = ""
            
        self.dataVarNameLabel.setText(self._dataVarName)
        
    @property
    def dataDescription(self):
        return self._data_description_
    
    @dataDescription.setter
    def dataDescription(self, value:typing.Optional[str] = None):
        if value is None:
            self._data_description_ = ""
        else:
            self._data_description_ = str(value)
    
    @property
    def dataName(self):
        """Getter & setter for the data name"""
        return self._dataName
    
    @dataName.setter
    def dataName(self, value:str):
        # WARNING: 2022-11-09 16:07:02 
        # do NOT use this setter from within the slot connected to the
        # dataNameLineEdit!
        signalBlocker = QtCore.QSignalBlocker(self.dataNameLineEdit)
        if isinstance(value, str) and len(value.strip()):
            self._dataName = strutils.str2symbol(value)
        else:
            self._dataName = ""
        
        self.dataNameLineEdit.setText(self._dataName)
        
        self.sig_valueChanged.emit()
            
    @property
    def sourceID(self):
        return self._sourceID
    
    @sourceID.setter
    def sourceID(self, value:typing.Union[str, type(pd.NA)]):
        signalBlocker = QtCore.QSignalBlocker(self.sourceIDLineEdit)
        if isinstance(value, str) and len(value.strip()):
            self._sourceID = value
            if self._sourceID in ("NA", "<NA>"):
                self._souceID = pd.NA
        else:
            self._sourceID = pd.NA
            
        self.sourceIDLineEdit.setText(f"{self._sourceID}")
        
        self.sig_valueChanged.emit()
            
    @property
    def cell(self):
        return self._cell
    
    @cell.setter
    def cell(self, value:typing.Union[str, type(pd.NA)]):
        signalBlocker = QtCore.QSignalBlocker(self.cellIDLineEdit)
        if isinstance(value, str) and len(value.strip()):
            self._cell = value
            if self._cell in ("NA", "<NA>"):
                self._cell = pd.NA
        else:
            self._cell = pd.NA
            
        self.cellIDLineEdit.setText(f"{self._cell}")
        
        self.sig_valueChanged.emit()
        
    @property
    def analysisDateTime(self):
        return self._dateTime
    
    @analysisDateTime.setter
    def analysisDateTime(self, value:datetime.datetime):
        if not isinstance(value, datetime.datetime):
            raise TypeError(f"Expecting a datetime.datetime; got {type(value).__name__} instead")
        
        self._dateTime = value
            
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
            
    @property
    def genotype(self):
        return self._genotype
    
    @genotype.setter
    def genotype(self, value:typing.Union[str, type(pd.NA)]):
        updateCombo = False
        if isinstance(value, str):
            if len(value.strip()):
                if value in ("NA", "<NA>"):
                    self._genotype = pd.NA
                elif value not in self._available_genotypes_:
                    self._available_genotypes_.append(value)
                    updateCombo = True
                    self._genotype = value
                else:
                    self._genotype = value
                    
        else:
            self._genotype = pd.NA
            
        signalBlocker = QtCore.QSignalBlocker(self.genotypeComboBox)
        if updateCombo:
            self.genotypeComboBox.clear()
            self.genotypeComboBox.setItems(self._available_genotypes_)
            
        if self._genotype is pd.NA:
            self.genotypeComboBox.setCurrentIndex(0)
        else:
            ndx = self._available_genotypes_.index(self._genotype)
            self.genotypeComboBox.setCurrentIndex(ndx)
            
        self.sig_valueChanged.emit()
        
    @property
    def sex(self):
        return self._sex
    
    @sex.setter
    def sex(self, value:typing.Union[str, type(pd.NA)]):
        if isinstance(value, str):
            if value in ("NA", "<NA>"):
                self._sex = pd.NA
                sex_ndx = 0
                
            elif value in self._available_sex_:
                self._sex = value
                sex_ndx = self._available_sex_.index(value)
                
            else:
                self._sex = pd.NA
                sex_ndx = 0
        else:
            self._sex = pd.NA
            sex_ndx = 0
            
        signalBlocker = QtCore.QSignalBlocker(self.sexComboBox)
        self.sexComboBox.setCurrentIndex(sex_ndx)
        
        self.sig_valueChanged.emit()
        
    @property
    def age(self):
        return self._age
    
    @age.setter
    def age(self, value):
        if isinstance(value, pq.Quantity):
            if not scq.checkTimeUnits(value):
                raise TypeError(f"Age must be given in time units; instead got {value}")
            
            self._age_units = value.units
        else:
            self._age_units = pq.div
            self._age  = value * self._age_units

        signalBlocker = QtCore.QSignalBlocker(self.ageSpinBox)
        self.ageSpinBox.setValue(self._age)
        
        self.sig_valueChanged.emit()
        
            
                
            
