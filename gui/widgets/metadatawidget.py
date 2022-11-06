# -*- coding: utf-8 -*-
"""Common widget for meta-information in results
"""
import os, math, typing
import numpy as np
import quantities as pq
from core import quantities as scq
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType

from gui.widgets.small_widgets import QuantitySpinBox

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
        self._gender = kwargs.pop("gender", pd.NA)
        self._genotype = kwargs.pop("genotype", pd.NA)
        self._age_units = pq.postnatal_day
        
        self._configureUI_()
        
    def _configureUI_(self):
        self.setupUi(self)
        self.ageWidget.setLayout(QtWidgets.QGridLayout(self.ageWidget))
        self.ageSpinBox = QuantitySpinBox(parent=self.ageWidget)
        self.ageWidget.layout().addWidget(self.ageSpinBox)
        
        
