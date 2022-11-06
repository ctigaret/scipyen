import typing, warnings, math, os
from core.utilities import get_least_pwr10
from PyQt5 import (QtCore, QtWidgets, QtGui)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType
from gui.painting_shared import (FontStyleType, standardQtFontStyles, 
                                 FontWeightType, standardQtFontWeights)

import quantities as pq
from core import quantities as scq
import pandas as pd

__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_QuantityChooserWidget, QWidget = loadUiType(os.path.join(__module_path__, "quantitychooserwidget.ui"))

class QuantityChooserWidget(Ui_QuantityChooserWidget, QWidget):
    unitChanged = pyqtSignal(object, name="unitChanged")
    
    def __init__(self, parent=None, units=None):
        QWidget.__init__(self, parent=parent)
        if isinstance(units, pq.Quantity):
            self.units = units.units
            
        _irreds = [k for k in scq.UNITS_DICT if len(scq.UNITS_DICT[k]["irreducibles"])]
        
        _derived = [k for k in scq.UNITS_DICT if len(scq.UNITS_DICT[k]["irreducibles"])==0]
        
        self._unitFamilies = list(_irreds + _derived)
        
        self._currentUnitsFamily = None
        
        self._currentFamilyUnits = list()
        
        self._configureUI_()
        
    def _configureUI_(self):
        self.setupUi(self)
        
        self.unitFamilyComboBox.addItems(self._unitFamilies)
        
        self.unitFamilyComboBox.setCurrentIndex(0)
        
        self.unitFamilyComboBox.currentIndexChanged.connect(self._slot_refresh_unitComboBox)
        
        self._currentUnitsFamily = self._unitFamilies[self.unitFamilyComboBox.currentIndex()]
        self._setupUnitCombo()
        self.unitComboBox.setCurrentIndex(0)
        
        self._selectedUnitIndex = self.unitComboBox.currentIndex()
        self.unitComboBox.currentIndexChanged.connect(self._slot_unitComboNewIndex)
        
    def _setupUnitCombo(self):
        combo_units = list()
        unscalables = set()
        
        units = [u for u in scq.UNITS_DICT[self._currentUnitsFamily]["irreducibles"] | scq.UNITS_DICT[self._currentUnitsFamily]["derived"]]
        
        fdt_ = set()
        for u in units:
            try:
                fdt_.add(u.dimensionality.simplified)
            except:
                unscalables.add(u)
                
        fdt = list(fdt_)
        
        fdu_ = set()
        for u in units:
            try:
                if u.dimensionality in fdt:
                    fdu_.add(u)
                else:
                    unscalables.add(u)
            except:
                unscalables.add(u)
        
        fdu = list(fdu_)
        
        units_reduced = sorted([u for u in units if u not in fdu or (u in fdu and u.name not in [u_.name for u_ in fdu])], key = lambda x: x.name)
        
        for u in fdu:
            combo_units.append(u)
            u_s = set()
            for uu in units_reduced:
                try:
                    u_scale = float(uu.rescale(u).magnitude)
                    u_s.add((uu, u_scale))
                except:
                    unscalables.add(uu)
                    continue
            if len(u_s):
                u_ss = sorted(list(u_s), key = lambda x: x[1])
                combo_units += [v[0] for v in u_ss]
                
        combo_units += list(unscalables)
        
        self._currentFamilyUnits = list(combo_units)
        
        signalBlocker = QtCore.QSignalBlocker(self.unitComboBox)
        self.unitComboBox.clear()
        self.unitComboBox.addItems([u.name for u in self._currentFamilyUnits])
        
    @pyqtSlot(int)
    def _slot_refresh_unitComboBox(self, value):
        self._currentUnitsFamily = self._unitFamilies[self.unitFamilyComboBox.currentIndex()]
        self._setupUnitCombo()
        currentUnit = self._currentFamilyUnits[self.unitComboBox.currentIndex()]
        self.unitChanged.emit(currentUnit)
        
        
    @pyqtSlot(int)
    def _slot_unitComboNewIndex(self, value):
        currentUnit = self._currentFamilyUnits[self.unitComboBox.currentIndex()]
        
        # print(f"self.__class__.__name__._slot_unitComboNewIndex {currentUnit}, type: {type(currentUnit).__name__}, dimensionality: {currentUnit.dimensionality}")
        
        self.unitChanged.emit(currentUnit)
        

class QuantitySpinBox(QtWidgets.QDoubleSpinBox):
    # TODO 2022-10-31 16:43:09 maybe 
    def __init__(parent=None):
        super().__init__(self, parent=parent)
        
        self._units_ = pq.dimensionless
        
    @property
    def units(self):
        return self._units_
    
    @units.setter
    def units(self, value:typing.Optional[pq.Quantity] = None):
        if isinstance(value, pq.Quantity):
            self._units_ = value.units
            super().setSuffix(f" {self._value_.dimensionality}")
        else:
            self._units_ = pq.dimensionless
            super().setSuffix("")
            
    
            
    
