# -*- coding: utf-8 -*-
"""Common widget for meta-information in results
"""
import os, math, typing
import numpy as np
import quantities as pq
from core import quantities as scq
from core import strutils
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
        self._source = kwargs.pop("source", pd.NA)
        self._cell = kwargs.pop("cell", pd.NA)
        self._field = kwargs.pop("field", pd.NA)
        self._age = kwargs.pop("age", pd.NA)
        
        self._default_genotypes_ = kwargs.pop("default_genotypes", ["NA", "wt", "het", "hom","+/+", "+/-", "-/-"])
        
        self._available_genotypes = self._default_genotypes_
        
        if isinstance(self._age, pq.Quantity):
            if not scq.check_time_units(self._age):
                raise TypeError(f"Age must be given in time units; instead got {self._age}")
            
            self._age_units = self._age.units
        else:
            self._age_units = pq.div
            self._age  = self._age * self._age_units
            
        self._gender = kwargs.pop("gender", pd.NA)
        self._genotype = kwargs.pop("genotype", pd.NA)
        
        self._configureUI_()
        
    def _configureUI_(self):
        self.setupUi(self)
        self.dataVarNameLabel.setText(self._dataVarName)
        
        self.ageWidget.setLayout(QtWidgets.QGridLayout(self.ageWidget))
        self.ageSpinBox = QuantitySpinBox(parent=self.ageWidget, 
                                          unitsFamily="Time", 
                                          units=pq.div,
                                          singleStep = 1.0,
                                          decimals=1)

        self.ageSpinBox.setValue(self._age)
        if isinstance(self._age, pq.Quantity):
            self.ageSpinBox.units = self._age.units
            
        self.ageWidget.layout().addWidget(self.ageSpinBox)
        
        self.dataNameLineEdit.setClearButtonEnabled(True)
        self.dataNameLineEdit.undoAvailable = True
        self.dataNameLineEdit.redoAvailable =True
        self.dataNameLineEdit.setText(self._dataName)
        
        self.sourceIDLineEdit.setClearButtonEnabled(True)
        self.sourceIDLineEdit.undoAvailable = True
        self.sourceIDLineEdit.redoAvailable = True
        
        self.cellIDLineEdit.setClearButtonEnabled(True)
        self.cellIDLineEdit.undoAvailable = True
        self.cellIDLineEdit.redoAvailable = True
        
        self.fieldIDLineEdit.setClearButtonEnabled(True)
        self.fieldIDLineEdit.undoAvailable = True
        self.fieldIDLineEdit.redoAvailable = True
        
        gender = ["NA", "F", "M"]
        
        my_gender = str(self._gender).strip("<>")
        if my_gender in gender:
            gender_ndx = gender.index(my_gender)
        else:
            gender_ndx = 0 # → NA
        
        self.genderComboBox.setEditable(False)
        self.genderComboBox.addItems(gender)
        self.genderComboBox.setCurrentIndex(gender_ndx)
        
        my_genotype = str(self._genotype).strip("<>")
        
        # NOTE: 2022-11-07 14:03:58
        # allow custom genotype strings
        if my_genotype not in self._available_genotypes:
            self._available_genotypes.append(my_genotype)

        genotype_ndx = self._available_genotypes.index(my_genotype)
            
        self.genotypeComboBox.setEditable(True)
        self.genotypeComboBox.lineEdit().setClearButtonEnabled(True)
        self.genotypeComboBox.lineEdit().redoAvailable = True
        self.genotypeComboBox.lineEdit().undoAvailable = True
        self.genotypeComboBox.addItems(genotypes)
        self.genotypeComboBox.setCurrentIndex(genotype_ndx)
        
        
    def value(self):
        """Returns a dict with field values takes from individual children
        """
        ret = dict()
        ret["VarName"] = strutils.str2symbol(self.dataNameLineEdit.text())
        ret["Source"] = self.sourceIDLineEdit.text()
        ret["Cell"] = self.cellIDLineEdit.text()
        ret["Field"] = self.fieldIDLineEdit.text()
        ret["Age"] = self.ageSpinBox.value() # will return units of time
        ret["Gender"] = self.genderComboBox.currentText()
        ret["Genotype"] = self.genotypeComboBox.currentText()
        
        return ret
