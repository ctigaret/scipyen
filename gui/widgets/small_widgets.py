import typing, warnings, math, os
from core.utilities import get_least_pwr10
from PyQt5 import (QtCore, QtWidgets, QtGui)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType
from gui.painting_shared import (FontStyleType, standardQtFontStyles, 
                                 FontWeightType, standardQtFontWeights)

from gui import quickdialog as qd

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
        
        self._currentUnit = None
        
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
        self._currentUnit = self._currentFamilyUnits[self.unitComboBox.currentIndex()]
        self.unitChanged.emit(self._currentUnit)
        
        
    @pyqtSlot(int)
    def _slot_unitComboNewIndex(self, value):
        self._currentUnit = self._currentFamilyUnits[self.unitComboBox.currentIndex()]
        
        # print(f"self.__class__.__name__._slot_unitComboNewIndex {currentUnit}, type: {type(currentUnit).__name__}, dimensionality: {currentUnit.dimensionality}")
        
        self.unitChanged.emit(self._currentUnit)
        
    @property
    def currentUnit(self):
        return self._currentUnit
        

class QuantitySpinBox(QtWidgets.QDoubleSpinBox):
    """Subclass of QDoubleSpinBox aware of Python quantities.
    Single step, number of decimals and units suffix are all configurable.
    """
    def __init__(parent=None):
        super().__init__(self, parent=parent)
        
        self._default_units_ = pq.dimensionless
        self._units_ = pq.dimensionless
        
        self._default_singleStep = 1e-2
        self._singleStep = self._default_singleStep
        
        self._default_decimals = -math.log10(self._singleStep) if self._singleStep < 1 else 1
        self._decimals = self._default_decimals
        
        self.setSingleStep(self._singleStep)
        self.setDecimals(self._decimals)
        
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        
    @property
    def units(self):
        return self._units_
    
    @units.setter
    def units(self, value:typing.Optional[pq.Quantity] = None):
        if isinstance(value, pq.Quantity):
            self._units_ = value.units
            super().setSuffix(f" {self._value_.dimensionality.unicode}")
        else:
            self._units_ = pq.dimensionless
            super().setSuffix("")
            
    def contextMenuEvent(self, evt):
        cm = QtWidgets.QMenu("Options", self)
        setUnitsAction = cm.addAction("Set quantity units")
        setUnitsAction.triggered.connect(self._slot_setUnits)
        setSingleStepAction = cm.addAction("Set single step")
        setPrecisionAction.triggered.connect(self._slot_setSingleStep)
        setDecimalsAction = cm.addAction("Set decimals")
        setDecimalsAction.triggered.connect(self._slot_setDecimals)
        resetAction = cm.addAction("Reset")
        resetAction.triggered.connect(self._slot_reset)
        cm.popup(evt.pos())
        
    @pyqtSlot()
    def _slot_setUnits(self):
        dlg = qd.QuickDialog(parent = self)
        quantityWidget = QuantityChooserWidget(parent = dlg)
        dlg.addWidget(quantityWidget)
        if dlg.exec():
            self.units = quantityWidget.currentUnit
            
    @pyqtSlot()
    def _slot_setSingleStep(self):
        dlg = qd.Quickdialog(parent=self)
        floatInput = qd.FloatInput(dlg, "Step (float)")
        floatInput.setValue(f"{self._singleStep}")
        dlg.addwidget(floatInput)
        if dlg.exec():
            value = floatInput.value()
            self.setSingleStep(value)
            
    @pyqtSlot()
    def _slot_setDecimals(self):
        dlg = qd.Quickdialog(parent=self)
        intInput = qd.IntegerInput(dlg, "Decimals (int, > 0)")
        intInput.setValue(f"{self._decimals}")
        dlg.addwidget(intInput)
        if dlg.exec():
            value = intInput.value()
            if value < 0:
                value  = 0
            self.setDecimals(value)
            
    @pyqtSlot()
    def _slot_reset(self):
        self.setSingleStep(self._default_singleStep)
        self.setDecimals(self._default_decimals)
        self.units = self._default_units_
            
    
        
        
        
            
    
