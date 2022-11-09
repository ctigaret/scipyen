# -*- coding: utf-8 -*-
"""Common widget for meta-information in results
"""
import os, math, typing
import numpy as np
import quantities as pq
from core import quantities as scq
from core import strutils
from core.datatypes import UnitType, GENOTYPES
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType

from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget

__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_MetaDataWidget, QWidget = loadUiType(os.path.join(__module_path__, "metadatawidget.ui"))

class MetaDataWidget(Ui_MetaDataWidget, QWidget):
    def __init__(self, parent=None, **kwargs):
        QWidget.__init__(self, parent=parent)
        
        self._dataVarName = kwargs.pop("varname", "")
        self._dataName = kwargs.pop("name", "")
        
        for name in ("sourceID, cell, field, sex, genotype"):
            val = kwargs.pop(name, pd.NA)
            
            if isinstance(val, str) and len(val.strip()):
                setattr(self, f"_{name}", val)
            else:
                setattr(self, f"_{name}", pd.NA)
        
        val = kwargs.pop("age", pd.NA)
        if isinstance(val, pq.Quantity) and scq.check_time_units(val):
            self._age = val
        else:
            self._age = pd.NA
        
        self._available_genotypes_ = kwargs.pop("default_genotypes", GENOTYPES)
        
        if isinstance(self._genotype, str):
            if len(self._genotype.strip()):
                if self._genotype not in self._available_genotypes_:
                    self._available_genotypes.append(self._genotype)
                    
                elif self._genotype in ("NA", "<NA>"):
                    self._genotype = pd.NA
                    
            else:
                self._genotype = pd.NA
                
        else:
            self._genotype = pd.NA
        
        
        self._biometrics_ = kwargs.pop("biometrics", dict())
        
        self._procedures_ = kwargs.pop("procedures", dict())
        
        self._annotations_ = kwargs.pop("annotations", dict())
        
        self._data_description_ = kwargs.pop("description", "")
        
        if isinstance(self._age, pq.Quantity):
            if not scq.check_time_units(self._age):
                raise TypeError(f"Age must be given in time units; instead got {self._age}")
            
            self._age_units = self._age.units
        else:
            self._age_units = pq.div
            self._age  = self._age * self._age_units
            
        self._sex = kwargs.pop("sex", pd.NA)
        self._genotype = kwargs.pop("genotype", pd.NA)
        
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
        self.ageSpinBox.units = self._age.units if isinstance(self._age, pq.Quantity) else pd.dimensionless
        self.ageSpinBox.singleStep = 0.01
        self.ageSpinBox.decimals = 2
        self.ageSpinBox.setValue(self._age)
        
        sex = ["NA", "F", "M"]
        
        self.sexComboBox.setEditable(False)
        self.sexComboBox.addItems(sex)
        self.sexComboBox.setCurrentIndex(sex_ndx)
        
        my_genotype = str(self._genotype).strip("<>")
        
        # NOTE: 2022-11-07 14:03:58
        # allow custom genotype strings
        if self._genotype is pd.NA or self._genotype not in self._available_genotypes_:
            genotype_ndx = 0
        else:
            genotype_ndx = self._available_genotypes_.index(self._genotype) + 1
            

        genotype_ndx = self._available_genotypes.index(my_genotype)
            
        self.genotypeComboBox.setEditable(True)
        self.genotypeComboBox.lineEdit().setClearButtonEnabled(True)
        self.genotypeComboBox.lineEdit().redoAvailable = True
        self.genotypeComboBox.lineEdit().undoAvailable = True
        self.genotypeComboBox.addItems(self._available_genotypes)
        self.genotypeComboBox.setCurrentIndex(genotype_ndx)
        
        self.biometricsPushButton.clicked.connect(self._slot_editBiometrics)
        self.procedurePushButton.clicked.connect(self._slot_editProcedures)
        self.triggersPushButton.clicked.connect(self._slot_editTriggers)
        self.dateTimePushButton.clicked.connect(self._slot_editDateTime)
        self.annotationsPushButton.clicked.connect(self._slot_editAnnotations)
        self.notesPushButton.clicked.connect(self._slot_editNotes)
        
    def value(self):
        """Returns a dict with field values takes from individual children
        """
        ret = dict()
        ret["VarName"] = strutils.str2symbol(self._dataVarName)
        ret["Name"] = self.dataNameLineEdit.text()
        ret["Source"] = self.sourceIDLineEdit.text()
        ret["Cell"] = self.cellIDLineEdit.text()
        ret["Field"] = self.fieldIDLineEdit.text()
        ret["Age"] = self.ageSpinBox.value() # will return units of time
        ret["Sex"] = self.sexComboBox.currentText()
        ret["Genotype"] = self.genotypeComboBox.currentText()
        
        return ret
    
    @pyqtSLot()
    def _slot_setDataName(self):
        self._dataName = strutils.str2symbol(self.dataNameLineEdit.text())
        
    @pyqtSlot()
    def _slot_setSourceID(self):
        self._sourceID = self.sourceIDLineEdit.text()
        if self._sourceID in ("NA", "<NA>"):
            self._sourceID = pd.NA
    
    @pyqtSlot()
    def _slot_setCell(self):
        self._cell = self.cellIDLineEdit.text()
        if self._cell in ("NA", "<NA>"):
            self._cell = pd.NA
    
    @pyqtSlot()
    def _slot_setField(self):
        self._field = self.fieldIDLineEdit.text()
        if self._field in ("NA", "<NA>"):
            self._field = pd.NA
    
    @pyqtSlot()
    def _slot_editAnnotations(self):
        # TODO 2022-11-08 08:31:20
        # enable a scrollable view in GenericMappingDialog
        # when there are more than 5-6 entries in the mapping
        # use that to edit annotations
        pass
    
    @pyqtSlot()
    def _slot_editBiometrics(self):
        # TODO 2022-11-08 08:32:12
        # use GenericMappingDialog
        pass
    
    @pyqtSlot()
    def _slot_editDateTime(self):
        # TODO 2022-11-08 08:32:23
        # create DateTimeInput widget in gui.quickdialog, use here wrapped
        # in a quickdialog
        pass
    
    @pyqtSlot()
    def _slot_editNotes(self):
        # TODO: 
        # create a simple (rich) text editor GUI, use here
        # (check examples in Qt5 stack)
        pass
    
    @pyqtSlot()
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
        pass
    
    @pyqtSlot()
    def _slot_editTriggers(self):
        # TODO: 2022-11-08 08:36:10
        # use gui.protocoleditordialog.ProtocolEditorDialog
        # but with the following functions enabled conditionally: 
        #
        # trigger detection ↔ is there ephysdata available
        pass    
    
    @property
    def dataVarName(self):
        return self._dataVarName
    
    @dataVarName.setter
    def dataVarName(self, value:str):
        if isinstance(value, str) and len(value.strip()):
            val = strutils.str2symbol(value)
            self._dataVarName = val
            self.dataVarNameLabel.setText(val)
    
    @property
    def dataName(self):
        """Getter & setter for the data name"""
        return self._dataName
    
    @dataName.setter
    def dataName(self, value:str):
        # WARNING: 2022-11-09 16:07:02 
        # do NOT use this setter from within the slot connected to the
        # dataNameLineEdit!
        if isinstance(value, str):
            self._dataName = strutils.str2symbol(value)
            signalBlocker = QtCore.QSignalBlocker(self.dataNameLineEdit)
            self.dataNameLineEdit.setText(self._dataName)
            
    @property
    def sourceID(self, value:str):
        return self._sourceID
    
    @sourceID.setter
    def sourceID(self, value:typing.Union[str, type(pd.NA)]):
        if isinstance(value, str) and len(value.strip()):
            self._sourceID = value
            if self._sourceID in ("NA", "<NA>"):
                self._souceID = pd.NA
        else:
            self._sourceID = pd.NA
            
        signalBlocker = QtCore.QSignalBlocker(self.sourceIDLineEdit)
        self.sourceIDLineEdit.setText(f"{self._sourceID}")
            
    @property
    def cell(self):
        return self._cell
    
    @cell.setter
    def cell(self, value:typing.Union[str, type(pd.NA)]):
        if isinstance(value, str) and len(value.strip()):
            self._cell = value
            if self._cell in ("NA", "<NA>"):
                self._cell = pd.NA
        else:
            self._cell = pd.NA
            
        signalBlocker = QtCore.QSignalBlocker(self.cellIDLineEdit)
        self.cellIDLineEdit.setText(f"{self._cell}")
            
    @property
    def field(self):
        return self._field
    
    @field.setter
    def field(self, value:typing.Union[str, type(pd.NA)]):
        if isinstance(value, str) and len(value.strip()):
            self._field = value
            if self._field in ("NA", "<NA>"):
                self._field = pd.NA
        else:
            self._field = pd.NA
