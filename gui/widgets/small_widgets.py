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
    """Compound widget allowing the user to choose a physical dimensionality.
    Convenience UI elements to attach quantities to various numeric variables.
    
    By default, the user is prompted to select a unit quantity from one of several
    "families" of unit quantities (e.t., Time, Length, etc)
    
    This choice can be restricted to a single family.
    """
    unitChanged = pyqtSignal(object, name="unitChanged")
    
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None, unit:typing.Optional[pq.Quantity]=None, unitFamily:typing.Optional[str]=None):
        """
        Named parameters:
        =================
        parent:     the parent QWidget; optional, default is None
        unit:       pre-selected unit; optional, default is None
        unitFamily: str, restrict options or a given unit family; 
                    optional, default is None
                    For a list of units families, type `scq.unitFamilies()` in
                    Scipyen's console
        """
        QWidget.__init__(self, parent=parent)
        
        if unitFamily in scq.UNITS_DICT:
            self._unitFamilies = [unitFamily]
            
        else:
            _irreds = [k for k in scq.UNITS_DICT if len(scq.UNITS_DICT[k]["irreducibles"])]
            _derived = [k for k in scq.UNITS_DICT if len(scq.UNITS_DICT[k]["irreducibles"])==0]
            self._unitFamilies = list(_irreds + _derived)
        
        # set up some defaults
        self._currentUnitsFamily = None # when set, this will be a str
        self._currentFamilyUnits = list() # when set, this will be a list of pq.Quantity objects (UnitQuantity to be exact)
        self._currentUnit = pq.dimensionless
        
        # NOTE: 2022-11-07 10:22:22
        # will also set up:
        # • self._currentUnitsFamily
        # • self._currentFamilyUnits
        # • self._currentUnit
        self._configureUI_() # will also assign the initial value of self._currentUnitsFamily 
        
        if isinstance(unit, pq.Quantity):
            self.currentUnit = unit

    def _configureUI_(self):
        self.setupUi(self)
        
        self._setupFamilyCombo()
        
        self.unitFamilyComboBox.currentIndexChanged.connect(self._slot_refresh_unitComboBox)
        
        
        self._setupUnitCombo() # also sets up self._currentFamilyUnits
        
        self.unitComboBox.setCurrentIndex(0)
        
        self._selectedUnitIndex = self.unitComboBox.currentIndex()
        self.unitComboBox.currentIndexChanged.connect(self._slot_unitComboNewIndex)
        
        self._currentUnit = self._currentFamilyUnits[self._selectedUnitIndex]
    
    def _generateCurrentFamilyUnits(self):
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
        
    def _setupFamilyCombo(self):
        """Called by _configureUI_ but also when manually setting the units family
        """
        signalBlocker = QtCore.QSignalBlocker(self.unitFamilyComboBox)
        self.unitFamilyComboBox.clear()
        self.unitFamilyComboBox.addItems(self._unitFamilies)
        if self._currentUnitsFamily in self._unitFamilies:
            self.unitFamilyComboBox.setCurrentIndex(self._unitFamilies.index(self._currentUnitsFamily))
        else:
            self.unitFamilyComboBox.setCurrentIndex(0)
            self._currentUnitsFamily = self._unitFamilies[self.unitFamilyComboBox.currentIndex()]
        
    def _setupUnitCombo(self):
        """Called by _configureUI_ but also when manually setting up a unit
        """
        self._generateCurrentFamilyUnits()
        signalBlocker = QtCore.QSignalBlocker(self.unitComboBox)
        self.unitComboBox.clear()
        self.unitComboBox.addItems([u.name for u in self._currentFamilyUnits])
        u_names = [u.name for u in self._currentFamilyUnits]
        if self._currentUnit.name in u_names:
            self.unitComboBox.setCurrentIndex(u_names.index(self._currentUnit.name))
        else:
            self.unitComboBox.setCurrentIndex(0)
            self._currentUnit = self._currentFamilyUnits[self.unitComboBox.currentIndex()]
        
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
    def unitFamily(self):
        return self._currentUnitsFamily
    
    @unitFamily.setter
    def unitFamily(self, value:typing.Optional[str]=None):
        if value in scq.UNITS_DICT:
            self._unitFamilies = [value]
            self._currentUnitsFamily = value
            self._setupFamilyCombo()
            self._setupUnitCombo()
        
    @property
    def currentUnit(self):
        return self._currentUnit
    
    @currentUnit.setter
    def currentUnit(self, value:typing.Optional[pq.Quantity]=None):
        if value is None:
            value = pq.dimensionless
            
        if isinstance(value, pq.Quantity):
            family_index = None
            unit_index_in_family = None
            unit = value.units
            
            # find the units family where value's units might belong
            for k, family in enumerate(self._unitFamilies):
                units = scq.UNITS_DICT[family]["irreducibles"] | scq.UNITS_DICT[family]["derived"]
                u_names = [u.name for u in units]
                
                # then find the index of the value's units in the family of units
                # to be more accurate, use name, not the units itself
                if unit in units and unit.name in u_names:
                    unit_index_in_family = u_names.index(unit.name)
                    family_index = k
                    # exit loop after first units found
                    break
                
            if isinstance(family_index, int) and family_index in range(self.unitFamilyComboBox.maxCount()):
                if isinstance(unit_index_in_family, int) and unit_index_in_family in range(self.unitComboBox.maxCount()):
                    signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.unitFamilyComboBox, self.unitComboBox)]
                    self.unitFamilyComboBox.setCurrentIndex(family_index)
                    self.unitComboBox.setCurrentIndex(unit_index_in_family)
                    self._currentUnitsFamily = self._unitFamilies[family_index]
                    self._generateCurrentFamilyUnits()
                    self._currentUnit = self._currentUnitsFamily[unit_index_in_family]
                
    def value(self):
        """For compatibilty with qd.QuickDialog"""
        return self.currentUnit
    
    def setValue(self, value:typing.Optional[pq.Quantity]=None):
        """For compatibilty with qd.QuickDialog"""
        if value is None:
            value = pq.dimensionless
        self.currentUnit = value
        
    def validate(self):
        """For compatibilty with qd.QuickDialog"""
        return True
    
    def restrictToUnitFamily(self, value:typing.Optional[str]=None):
        if value in scq.UNITS_DICT:
            self._unitFamilies = [value]
            self.unitFamily = value
        

class QuantitySpinBox(QtWidgets.QDoubleSpinBox):
    """Subclass of QDoubleSpinBox aware of Python quantities.
    Single step, number of decimals and units suffix are all configurable.
        
    Most methods are inherited directly from QDoubleSpinBox, with the following
    exceptions:
        
    • setMinimum(), setMaximum(), setRange(), are overloaded to accept quantity
    scalars as well as float arguments, or None; 
        ∘ when None, the 'minimum' and 'maximum' properties will be set to 
            -math.inf and math.inf, respectively.
        
    • minimum() and maximum() are overloaded to return python Quantity scalars
        WARNING: This means that the minimum() and maximum() values will ALWAYS
        be quantities (even if their units are `dimensionless`)
        
    By default, the 'minimum' property is set to -math.inf. 
        
    """
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None, units:typing.Optional[pq.Quantity]=None, unitsFamily:typing.Optional[str]=None, singleStep:typing.Optional[float]=None, decimals:typing.Optional[int]=None):#, minimum:typing.Optional[typing.Union[pq.Quantity, float]]=None, maximum:typing.Optional[typing.Union[pq.Quantity, float]]=None):
        """
        Named parameters:
        =================
        parent: parent widget; optional, default is None
        units: initial units; optional, default is pq.dimensionless
        unitFamily: restrict to units in given family; optoonal, default is None
    
        """
        # minimum, maximum: min & max values of the spin box - to be set manually
        
        QtWidgets.QDoubleSpinBox.__init__(self, parent=parent)
        
        # FIXME/TODO: 2022-11-07 13:32:41
        # This setting is not right; NA should be somewhat mapped to NA, NOT
        # to minimum - what do we do if minimum is set to 0 which is a valid value?
        # super().setSpecialValueText("NA") # shown when value is at minimum
        
        self._default_units_ = pq.dimensionless
        
        if isinstance(units, pq.Quantity):
            self._units_ = units.units
        else:
            self._units_ = self._default_units_
        
        if unitsFamily in scq.UNITS_DICT:
            self._unitFamily_ = unitsFamily
        else:
            self._unitFamily_ = None
        
        self._default_singleStep = super().singleStep()
        if isinstance(singleStep,float):
            self._singleStep = singleStep
            
        elif singleStep is None:
            self._singleStep = self._default_singleStep
        else:
            raise TypeError(f"singleStep expected to be a float or None; instead, got {singleStep}")
            
        self._default_decimals = -int(math.log10(abs(self._singleStep))) if (self._singleStep < 1 and self._singleStep > -1) else 1
        if isinstance(decimals, int) and decimals >= 0:
            self._decimals = decimals
            
        elif decimals is None:
            self._decimals = self._default_decimals
            
        else:
            raise TypeError(f"decimals expected to be an int >= 0 or None; instead, got {decimals}")
        
        self._default_internal_minimum = -math.inf
        self._default_internal_maximum = math.inf
        
        self._internal_minimum = self._default_internal_minimum
        self._internal_maximum = self._default_internal_maximum
        
        self.setSingleStep(self._singleStep)
        self.setDecimals(self._decimals)
        self.setRange(self._internal_minimum, self._internal_maximum)
        
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        
    @property
    def units(self):
        return self._units_
    
    @units.setter
    def units(self, value:typing.Optional[pq.Quantity] = None):
        if not isinstance(value, pq.Quantity):
            value = pq.dimensionless
            
        self._units_ = value.units
        
        if self._units_.dimensionality == pq.dimensionless.dimensionality:
            super().setSuffix("")
        else:
            super().setSuffix(f" {self._units_.dimensionality.unicode}")
            
    def contextMenuEvent(self, evt):
        cm = QtWidgets.QMenu("Options", self)
        setUnitsAction = cm.addAction("Set units")
        setUnitsAction.triggered.connect(self._slot_setUnits)
        setSingleStepAction = cm.addAction("Set single step")
        setSingleStepAction.triggered.connect(self._slot_setSingleStep)
        setDecimalsAction = cm.addAction("Set decimals")
        setDecimalsAction.triggered.connect(self._slot_setDecimals)
        resetAction = cm.addAction("Reset")
        resetAction.triggered.connect(self._slot_reset)
        cm.popup(self.mapToGlobal(evt.pos()))
        
    def setMinimum(self, value:typing.Optional[typing.Union[float, pq.Quantity]]=None):
        """Overloads QDoubleSpinBox.setMinimum, to accept:
        • a None
        • a float
        • a scalar Quantity
    
        When None, the minimum value will be set to -math.inf
        """
        if value is None:
            super().setMinimum(self._internal_minimum)
            
        elif isinstance(value, float):
            super().setMinimum(value)
            
        elif isinstance(value, pq.Quantity):
            if value.size > 1:
                raise TypeError(f"Expecting a scalar quantity, not an array")
            val = float(value.magnitude)
            units = value.units
            super().setMinimum(val)
            self.units = units
        
    def setMaximum(self, value:typing.Optional[typing.Union[float, pq.Quantity]]=None):
        """Overloads QDoubleSpinBox.setMaximum, to accept:
        • a None
        • a float
        • a scalar Quantity
    
        When None, the maximum value will be set to math.inf
        """
        if value is None:
            super().setMaximum(self._internal_maximum)
            
        elif isinstance(value, float):
            super().setMaximum(value)
            
        elif isinstance(value, pq.Quantity):
            if value.size > 1:
                raise TypeError(f"Expecting a scalar quantity, not an array")
            val = float(value.magnitude)
            units = value.units
            super().setMaximum(val)
            self.units = units
            
    def setRange(self, minimum:typing.Optional[typing.Union[float, pq.Quantity]]=None, maximum:typing.Optional[typing.Union[float, pq.Quantity]]=None):
        """Overloads QDoubleSpinBox.setRange to accept:
        • floats
        • scalar Quantity
        • None
    
        for either 'minimum' or 'maximum'
    
        When either is None, the 'minimum' and 'maximum' will be set to
        -math.inf and math.inf, respectively.
        """
        # print(f"{self.__class__.__name__}.setRange({minimum}, {maximum})")
        # parameter sanity checks:
        if all(isinstance(v, pq.Quantity) for v in (minimum, maximum)):
            # NOTE: 2022-11-07 09:55:43
            # sanity check when both are quantities
            if any(v.size > 1 for v in (minimum, maximum)):
                raise TypeError("Expecting scalar quantities for both minimum and maximum ")
            
            if scq.units_convertible(minimum, maximum):
                # NOTE: 2022-11-09 09:07:15
                # rescale to minimum units explicitly, 
                # in case minimum magnitude is 0 (and thus raise exception)
                maximum = maximum.rescale(minimum.units)
                
            else:
                raise TypeError(f"{minimum} and {maximum} have incompatible units")
            
        else:
            # NOTE: 2022-11-07 09:57:07
            # DO accept None
            if minimum is None:
                minimum = -math.inf
                
            if maximum is None:
                maximum = math.inf
                
            # NOTE: 2022-11-07 09:55:58
            # propagate units from one the other if only one is a quantity
            if isinstance(minimum, pq.Quantity):
                if minimum.size > 1:
                    raise TypeError("Expecting a scalar quantity for 'minimum")
                maximum = maximum * minimum.units
                
            elif isinstance(maximum, pq.Quantity):
                if maximum.size>1:
                    raise TypeError("Expecting a scalar quantity for maximum")
                minimum = minimum * maximum.units
                
            elif not all(isinstance(v, (float, type(None))) for v in (minimum, maximum)):
                # NOTE: 2022-11-07 09:56:09
                # finally, only accept  scalar floats or None
                raise TypeError("Expecting floats, scalar quantities or None as minimum and maximum")
                
        minVal = float(minimum.magnitude) if isinstance(minimum, pq.Quantity) else minimum
        minUnits = minimum.units if isinstance(minimum, pq.Quantity) else None
        maxVal = float(maximum.magnitude) if isinstance(maximum, pq.Quantity) else maximum
        maxUnits = maximum.units if isinstance(maximum, pq.Quantity) else None
        
        # NOTE: 2022-11-07 10:00:21
        # both minUnits and maxUnits should have been checked and now be identical
        # see NOTE: 2022-11-07 09:55:43 and NOTE: 2022-11-07 09:55:58
        # 
        super().setMinimum(minVal)
        super().setMaximum(maxVal)
        self.units = minUnits
        
    def minimum(self):
        return super().minimum() * self.units
    
    def maximum(self):
        return super().maximum() * self.units
    
    def value(self):
        """ Overloads QDoubleSpinBox.value() to return a quantity
        """
        # NOTE: use NA as a volatile; once we've moved away from it we're done
        # by the way, one can only move away from NA by entering a numeric value 
        # in the spin box field
        val = super().value()
        if val == super().minimum() and self.specialValueText() == "NA":
            return pd.NA * self.units
        
        super().setMinimum(self._internal_minimum)
        super().setSpecialValueText("")
        
        return val * self.units
        
    def setValue(self, value:typing.Union[pq.Quantity, float, type(pd.NA)]):
        """Also allows changing the units if not convertible to current ones.
        Otherwise the value will be rescales to current units.
        """
        if isinstance(value, pq.Quantity):
            if value.size > 1:
                raise TypeError("Only scalar quantities are allowed")
            
            if scq.units_convertible(self.units, value.units):
                val = float(value.rescale(self.units).magnitude)
            else:
                self.units = value.units
                val = float(value.magnitude)
        else:
            val = value
        
        # FIXME/TODO: 2022-11-07 13:51:37
        # at the moment, this will fail silently; find a way to notify user/caller
        if isinstance(val, float):
            if val > self._internal_minimum:
                super().setMinimum(self._internal_minimum)
                super().setValue(val)
                super().setSpecialValueText("")
            # else:
            #     QtWidgets.QMessageBox.critical(self, "Value is too small", text)
            
        elif val is pd.NA:
            super().setMinimum(-math.inf)
            super().setSpecialValueText("NA")
            super().setValue(-math.inf)
                
        else:
            raise TypeError(f"Expecting a scalar quantity or a float; instead, got {value}")
        
    @property
    def unitFamily(self):
        return self._unitFamily_
    
    def unitFamily(self, value:typing.Optional[str]=None):
        if value in scq.UNITS_DICT:
            self._unitFamily_ = value
        else:
            self._unitFamily_ = None
        
        
    @pyqtSlot()
    def _slot_setUnits(self):
        dlg = qd.QuickDialog(parent = self, title="Set units")
        quantityWidget = QuantityChooserWidget(parent = dlg)
        quantityWidget.currentUnits = self._units_
        if self._unitFamily_ in scq.UNITS_DICT:
            quantityWidget.restrictToUnitFamily(self._unitFamily_)
        dlg.addWidget(quantityWidget)
        if dlg.exec():
            self.units = quantityWidget.currentUnit
            
    @pyqtSlot()
    def _slot_setSingleStep(self):
        dlg = qd.QuickDialog(parent=self, title="Set single step")
        floatInput = qd.FloatInput(dlg, "Step (float)")
        floatInput.setValue(f"{super().singleStep()}")
        dlg.addWidget(floatInput)
        if dlg.exec():
            value = floatInput.value()
            self.setSingleStep(value)
            newDecimals = -int(math.log10(abs(value))) if (value < 1 and value > -1) else 1
            # NOTE: 2022-11-07 12:19:00
            # adapt to new decimals
            #
            if self.decimals() != newDecimals:
                self.setDecimals(newDecimals)
            
    @pyqtSlot()
    def _slot_setDecimals(self):
        dlg = qd.QuickDialog(parent=self, title="Set decimals")
        intInput = qd.IntegerInput(dlg, "Decimals (int) >= 0")
        intInput.setValue(f"{self._decimals}")
        dlg.addWidget(intInput)
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
            
    
        
        
        
            
    
