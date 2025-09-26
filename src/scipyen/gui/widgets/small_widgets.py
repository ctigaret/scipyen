# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2022 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import typing, warnings, math, cmath, os
import numpy as np
import quantities as pq
import pandas as pd
from core.utilities import get_least_pwr10
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
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
    

from gui.painting_shared import (FontStyleType, standardQtFontStyles, 
                                 FontWeightType, standardQtFontWeights)

from gui import quickdialog as qd
from gui.guiutils import (InftyDoubleValidator, ComplexValidator, validatorString)

from core import scipyen_quantities as scq

__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_QuantityChooserWidget, QWidget = loadUiType(os.path.join(__module_path__, "quantitychooserwidget.ui"))

class QuantityChooserWidget(Ui_QuantityChooserWidget, QWidget):
    r"""Compound widget allowing the user to choose a physical dimensionality.
    Convenience UI elements to attach quantities to various numeric variables.
    
    By default, the user is prompted to select a unit quantity from one of several
    "families" of unit quantities (e.t., Time, Length, etc)
    
    This choice can be restricted to a single family.
    """
    unitChanged = Signal(object, name="unitChanged")
    
    _default_units_ = pq.dimensionless
    
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None, 
                 unit:typing.Optional[pq.Quantity]=None, 
                 unitsFamily:typing.Optional[str]=None):
        r"""
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
        
        _irreds = [k for k in scq.UNITS_DICT if len(scq.UNITS_DICT[k]["irreducible"])]
        _derived = [k for k in scq.UNITS_DICT if len(scq.UNITS_DICT[k]["irreducible"])==0]
        self._family_names, self._families = zip(*list(scq.UNITS_DICT.items()))
        
        myunits = unit.units if isinstance(unit, pq.Quantity) else self._default_units_
        
        self._getUnitFamilyAndUnitFamilyUnits(myunits)
        
        self._restrictedToFamily_ = None
        
        self._units_ = myunits
        
        self._configureUI_() # will also assign the initial value of self._currentUnitsFamily 
        
    def _configureUI_(self):
        self.setupUi(self)
        
        self._setupFamilyCombo()
        
        self.unitFamilyComboBox.currentIndexChanged.connect(self._slot_unitsFamilyChanged)
        
        self._setupUnitCombo() 
        
        self.unitComboBox.setCurrentIndex(0)
        
        self._unitIndexInFamily = self.unitComboBox.currentIndex()
        self.unitComboBox.currentIndexChanged.connect(self._slot_unitsComboIndexChanged)
        
        self._units_ = self._currentUnitFamilyUnits[self._unitIndexInFamily]
        
    def _getUnitFamilyAndUnitFamilyUnits(self, unit:pq.Quantity):
        # print(f"{self.__class__.__name__}._getUnitFamilyAndUnitFamilyUnits (unit = {unit})")
        family_name, directly_found = scq.getUnitFamily(unit, show_components=False, 
                                                   as_string=True, 
                                                   indicate_if_directly_found=True)
        
        
        self._currentUnitsFamilyName = family_name
        self._currentUnitsFamily = scq.UNITS_DICT[self._currentUnitsFamilyName]
        self._currentUnitFamilyUnits = sorted(list(scq.familyUnits(family_name)), key = lambda x: x.name)
        
        if not directly_found:
            self._currentUnitFamilyUnits.insert(0, unit.units)
        
        self._familyIndex = list(scq.UNITS_DICT).index(family_name)
        
        self._unitIndexInFamily = self._currentUnitFamilyUnits.index(unit.units)
        
        # print(f"{self.__class__.__name__}._getUnitFamilyAndUnitFamilyUnits: unit = {unit}")
        # print(f"\tfamily -> {family_name}")
        # print(f"\tdirectly_found -> {directly_found}")
        # print(f"\t_currentUnitsFamily -> {self._currentUnitsFamily}")
        # print(f"\t_currentUnitsFamilyName -> {self._currentUnitsFamilyName}")
        # print(f"\t_currentUnitFamilyUnits -> {self._currentUnitFamilyUnits}")
        # print(f"\t_familyIndex -> {self._familyIndex}")
        # print(f"\t_unitIndexInFamily -> {self._unitIndexInFamily}")
        
    def _setupFamilyCombo(self):
        r"""Called by _configureUI_ but also when manually setting the units family
        """
        signalBlocker = QtCore.QSignalBlocker(self.unitFamilyComboBox)
        # signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.unitFamilyComboBox, self.unitComboBox)]
        self.unitFamilyComboBox.clear()
        self.unitFamilyComboBox.addItems(self._family_names)
        if self._currentUnitsFamilyName in self._family_names:
            self.unitFamilyComboBox.setCurrentIndex(self._families.index(self._currentUnitsFamily))
        else:
            self.unitFamilyComboBox.setCurrentIndex(0)
            self._currentUnitsFamily = self._families[self.unitFamilyComboBox.currentIndex()]
            self._currentUnitsFamilyName = self._family_names[self.unitFamilyComboBox.currentIndex()]
            self._currentUnitFamilyUnits = sorted(list(scq.familyUnits(self._family_names[self.unitFamilyComboBox.currentIndex()])), key = lambda x: x.name)
        
    def _setupUnitCombo(self):
        r"""Called by _configureUI_ but also when manually setting up a unit
        """
        # self._generateCurrentFamilyUnits()
        signalBlocker = QtCore.QSignalBlocker(self.unitComboBox)
        self.unitComboBox.clear()
        u_names = list(map(lambda x: x.name, self._currentUnitFamilyUnits))
        u_names_display = list(map(lambda x: f"{x.name} ({x.dimensionality.unicode})" if (x != pq.dimensionless and x.name != x.dimensionality.unicode) else x.name, self._currentUnitFamilyUnits))
        self.unitComboBox.addItems(u_names_display)
        if self._units_.name in u_names:
            self.unitComboBox.setCurrentIndex(u_names.index(self._units_.name))
        else:
            self.unitComboBox.setCurrentIndex(0)
        
    @Slot(int)
    def _slot_unitsFamilyChanged(self, value):
        # print(f"{self.__class__.__name__}._slot_unitsFamilyChanged: value = {value}")
        self._currentUnitsFamilyName = self._family_names[self.unitFamilyComboBox.currentIndex()]
        self._currentUnitsFamily = scq.UNITS_DICT[self._currentUnitsFamilyName]
        # print(f"\nself._currentUnitsFamily -> {self._currentUnitsFamily}")
        self._currentUnitFamilyUnits = sorted(list(scq.familyUnits(self._currentUnitsFamilyName)), key = lambda x: x.name)
        self._setupUnitCombo()
        self._units_ = self._currentUnitFamilyUnits[self.unitComboBox.currentIndex()]
        self.unitChanged.emit(self._units_)
        
    @Slot(int)
    def _slot_unitsComboIndexChanged(self, value):
        self._units_ = self._currentUnitFamilyUnits[self.unitComboBox.currentIndex()]
        self.unitChanged.emit(self._units_)
        
    @property
    def unitFamily(self):
        return self._currentUnitsFamilyName
    
    @unitFamily.setter
    def unitFamily(self, value:typing.Optional[str]=None):
        if value in scq.UNITS_DICT:
            self._unitFamilies = [value]
            self._currentUnitsFamilyName = value
            self._currentUnitsFamily = scq.UNITS_DICT[value]
            self._setupFamilyCombo()
            self._setupUnitCombo()
        
    @property
    def units(self):
        return self._units_
    
    @units.setter
    def units(self, value:typing.Optional[typing.Union[pq.UnitQuantity, pq.Quantity]]=None):
        # print(f"{self.__class__.__name__}.units.setter: value = {value}")
        if value is None:
            value = pq.dimensionless
            
        self._getUnitFamilyAndUnitFamilyUnits(value)
        self._units_ = self._currentUnitFamilyUnits[self._unitIndexInFamily]
        # print(f"\n{self.__class__.__name__}.units.setter:  _units_ -> {self._units_}")
        
        signalBlockers = [QtCore.QSignalBlocker(w) for w in (self.unitFamilyComboBox, self.unitComboBox)]
        currentUnitComboboxIndex = self.unitFamilyComboBox.currentIndex()
        # print(f"\n{self.__class__.__name__}.units.setter: ")
        # print(f"\t_familyIndex -> {self._familyIndex}")
        # print(f"\tcurrentUnitComboboxIndex -> {currentUnitComboboxIndex}")
        
        if currentUnitComboboxIndex != self._familyIndex:
            self.unitFamilyComboBox.setCurrentIndex(self._familyIndex)
            self._setupUnitCombo()
        else:
            self.unitComboBox.setCurrentIndex(self._unitIndexInFamily)
        
    def value(self):
        r"""For compatibilty with qd.QuickDialog"""
        return self.units
    
    def setValue(self, value:typing.Optional[pq.Quantity]=None):
        r"""For compatibilty with qd.QuickDialog"""
        if value is None:
            value = pq.dimensionless
        self.units = value
        
    def validate(self):
        r"""For compatibilty with qd.QuickDialog"""
        return True
    
    def restrictToCurrentUnitFamily(self, value:bool=False):
        self.unitFamilyComboBox.setEnabled(value)
            
    @property
    def familyRestriction(self) -> str:
        return self._restrictedToFamily_
    
    @familyRestriction.setter
    def familyRestriction(self, value:typing.Optional[str] = None):
        if isinstance(value, str):
            if value not in self._family_names:
                scipywarn(f"Family of units named {value} not found")
                return
            self._restrictedToFamily_ = value
            self.unitFamily = value
            self.unitFamilyComboBox.setEnabled(False)
        else:
            self.unitFamilyComboBox.setEnabled(True)
        
class QuantitySpinBox(QtWidgets.QDoubleSpinBox):
    r"""Subclass of QDoubleSpinBox aware of Python quantities.
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
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    
    _default_units_             =  pq.dimensionless
    _default_internal_minimum   = -math.inf
    _default_internal_maximum   =  math.inf
        
    
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None,
                 units:typing.Optional[typing.Union[pq.Quantity, float, int, complex]]=None, 
                 singleStep:typing.Optional[float]=None, 
                 stepType:typing.Optional[QtWidgets.QAbstractSpinBox.StepType] = None,
                 decimals:typing.Optional[int]=None,
                 minimum:typing.Optional[typing.Union[pq.Quantity, float]]=None, 
                 maximum:typing.Optional[typing.Union[pq.Quantity, float]]=None,
                 unitsFamily:typing.Optional[str]=None, 
                 fixUnitFamily:typing.Optional[typing.Union[str, bool]]=None,
                 rescaleWithUnitsChange:bool=False,
                 keepDimensionless:bool=False,
                 disableUnitChange:bool=False,
                 enforceImmutableUnits:bool=False,
                 ):
        r"""
        Named parameters:
        =================
        parent: parent widget; optional, default is None
        units: initial units, or initial value; optional, default is pq.dimensionless
        unitFamily: restrict to units in given family; optional, default is None
    
        """
        # minimum, maximum: min & max values of the spin box - to be set manually
        
        QtWidgets.QDoubleSpinBox.__init__(self, parent=parent)
        
        # FIXME/TODO: 2022-11-07 13:32:41
        # This setting is not right; NA should be somewhat mapped to NA, NOT
        # to minimum - what do we do if minimum is set to 0 which is a valid value?
        # super().setSpecialValueText("NA") # shown when value is at minimum
        
        # self._default_units_ = pq.dimensionless
        
        self._keepDimensionless_:bool = keepDimensionless
        self._disableUnitChange_:bool = disableUnitChange
        self._enforceImmutableUnits_:bool = enforceImmutableUnits
        if self._enforceImmutableUnits_:
            self._disableUnitChange_ = True
        self._restrictedToFamily_:typing.Optional[str] = None
        self._rescaleOnUnitChange_:bool = False
        self._forceDimensionless_:bool = False
        
        self._units_:pq.Quantity = self._default_units_
        self._magnitude_:float = 0.0
        self._prefix_ = ""
        self._suffix_ = ""
        
        if isinstance(units, pq.Quantity):
            self._units_ = units.units
            if not isinstance(units, pq.UnitQuantity):
                if units.size != 1:
                    raise TypeError(f"Expecting a scalar quantity; instead, got a Quantity array with {units.size} elements")
                self._magnitude_ = float(units.magnitude)
        else:
            if isinstance(units, (float, int)):
                self._magnitude_ = float(units)
            elif isinstance(units, complex):
                self._magnitude_ = abs(units)
            elif units is not None:
                raise TypeError(f"Invalid 'units' argument: {units}")
                
            self._units_ = self._default_units_
        
        self._unitFamily_ = scq.getUnitFamily(self._units_)
            
        if self._units_.dimensionality == pq.dimensionless.dimensionality:
            self._suffix_ = ""
            self._prefix_ = ""
        else:
            if not (self._keepDimensionless_ or self._forceDimensionless_):
                symbol = self._units_.dimensionality.unicode
                if self._unitFamily_ == "Currency":
                    self._suffix_ = ""
                    self._prefix_ = f"{symbol} "
                else:
                    self._suffix_ = f" {symbol}"
                    self._prefix_ = ""
                
        self._default_singleStep = super().singleStep()
        
        if isinstance(singleStep,float):
            self._singleStep_ = singleStep
            
        elif singleStep is None:
            self._singleStep_ = self._default_singleStep
        else:
            raise TypeError(f"singleStep expected to be a float or None; instead, got {singleStep}")
            
        self._default_decimals = -int(math.log10(abs(self._singleStep_))) if (self._singleStep_ < 1 and self._singleStep_ > -1) else 1
        self._decimals_ = self._default_decimals
        
        if isinstance(decimals, int) and decimals >= 0:
            self._decimals_ = decimals
        
        elif decimals is None:
            self._decimals_ = self._default_decimals
            
        else:
            raise TypeError(f"decimals expected to be an int >= 0 or None; instead, got {decimals}")

        # print(f"{self.__class__.__name__}.__init__:  decimals -> {self.decimals()}")
            
        self._internal_minimum = self._default_internal_minimum
        self._internal_maximum = self._default_internal_maximum
        
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        # print(f"{self.__class__.__name__}.__init__ DONE")
        
        super().setValue(self._magnitude_)
        super().setSingleStep(self._singleStep_)
        super().setDecimals(self._decimals_)
        if isinstance(stepType, QtWidgets.QAbstractSpinBox.StepType):
            super().setStepType(stepType)
        else:
            super().setStepType(QtWidgets.QAbstractSpinBox.DefaultStepType)
        
        super().setRange(self._internal_minimum, self._internal_maximum)
        if isinstance(stepType, QtWidgets.QAbstractSpinBox.StepType):
            super().setStepType(stepType)
        super().setSuffix(self._suffix_)
        super().setPrefix(self._prefix_)
        
        if isinstance(units, pq.Quantity) and not isinstance(units, pq.UnitQuantity):
            self.setValue(units)
        
        super().valueChanged.connect(self._slot_valueChanged)
        self.lineEdit().textChanged.connect(self._slot_valueTextChanged)
        
    @property
    def units(self):
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            return self._units_
    
    @units.setter
    def units(self, value:typing.Optional[pq.Quantity] = None):
        # print(f"{self.__class__.__name__}.units.setter: value = {value}")
        if self._keepDimensionless_ or self._forceDimensionless_:
            return 
        
        if not isinstance(value, pq.Quantity):
            value = pq.dimensionless
            
        if self._rescaleOnUnitChange_ and scq.unitsConvertible(value, self._units_) and float(self.value()) not in (math.nan, np.nan, -math.inf, math.inf, -np.inf, np.inf):
            newval = self.value().rescale(value)
            newfval = float(newval.magnitude)
            ratio = newfval/self._magnitude_
            self._singleStep_ *= ratio
            self._magnitude_ = float(newval.magnitude)
            self._units_ = newval.units
            super().setValue(self._magnitude_)
            self.setSingleStep(self._singleStep_)
        else:
            self._units_ = value.units
            
        self._unitFamily_ = scq.getUnitFamily(self._units_)
        
        self._suffix_ = ""
        self._prefix_ = ""
        
        if self._units_.dimensionality != pq.dimensionless.dimensionality:
            symbol = self._units_.dimensionality.unicode
            if self._unitFamily_ == "Currency":
                self._suffix_ = ""
                self._prefix_ = f"{symbol} "
            else:
                self._suffix_ = f" {symbol}"
                self._prefix_ = ""
        
        if np.isnan(self._magnitude_):
            text = "NaN"
            super().setSpecialValueText(text)
            
        elif np.isinf(self._magnitude_):
            text = "-Inf" if self._magnitude_ in (-np.inf, -math.inf) else "Inf"
            super().setSpecialValueText(text)
        else:
            text = f"{self._magnitude_:.{self.decimals()}}"
            
        super().setSuffix(self._suffix_)
        super().setPrefix(self._prefix_)
        
        if len(self._prefix_):
            text = f"{self._prefix_}{text}"
        if len(self._suffix_):
            text = f"{text}{self._suffix_}"
            
        self.lineEdit().setText(text)
            
    @Slot(str)
    def _slot_valueTextChanged(self, s:str):
        val = self.valueFromText(s)
        if isinstance(val, (pq.Quantity, float)):
            self._magnitude_ = float(val)
            self.sig_valueChanged.emit(self.value())
            
    @Slot(float)
    def _slot_valueChanged(self, val):
        self.sig_valueChanged.emit(self.value())
        
    @Slot(bool)
    def _slot_keepDimensionless(self, val:bool):
        self.keepDimensionless = val
            
    def contextMenuEvent(self, evt):
        # print(f"{self.__class__.__name__}.contextMenuEvent: _enforceImmutableUnits_ = {self._enforceImmutableUnits_}")
        cm = QtWidgets.QMenu("Options", self)
        if not (self._keepDimensionless_ or self._forceDimensionless_ or self._disableUnitChange_ or self._enforceImmutableUnits_):
            setUnitsAction = cm.addAction("Set units")
            setUnitsAction.triggered.connect(self._slot_setUnitsGUI)
        setDecimalsAction = cm.addAction("Set decimals")
        setDecimalsAction.triggered.connect(self._slot_setDecimalsGUI)
        setSingleStepAction = cm.addAction("Set single step")
        setSingleStepAction.triggered.connect(self._slot_setSingleStepGUI)
        adaptiveStepAction = cm.addAction("Adaptive step")
        adaptiveStepAction.setCheckable(True)
        adaptiveStepAction.setChecked(self.stepType() == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        adaptiveStepAction.toggled.connect(self._slot_setAdaptiveStep)
        setRangeAction = cm.addAction("Set range (min, max)")
        setRangeAction.triggered.connect(self._slot_setRangeGUI)
        if not (self._keepDimensionless_ or self._forceDimensionless_ or self._disableUnitChange_):
            cm.addSeparator()
            rescaleValueAction = cm.addAction("Rescale on unit change")
            rescaleValueAction.setCheckable(True)
            rescaleValueAction.setChecked(self._rescaleOnUnitChange_)
            rescaleValueAction.toggled.connect(self._slot_rescaleValueChanged)
            restrictAction = cm.addAction("Fix units family")
            restrictAction.setCheckable(True)
            restrictAction.setChecked(isinstance(self._restrictedToFamily_, str) and self._restrictedToFamily_ in scq.UNITS_DICT)
            restrictAction.toggled.connect(self._slot_familyRestrictionChanged)
            
        cm.addSeparator()
        if not (self._forceDimensionless_ or self._disableUnitChange_):
            toggleDimensionlessAction = cm.addAction("Ignore dimensionality")
            toggleDimensionlessAction.setCheckable(True)
            toggleDimensionlessAction.setChecked(self._keepDimensionless_)
            toggleDimensionlessAction.toggled.connect(self._slot_keepDimensionless)
            
        if not self._enforceImmutableUnits_:
            toggleUnitChange = cm.addAction("Immutable units")
            toggleUnitChange.setCheckable(True)
            toggleUnitChange.setChecked(self._disableUnitChange_)
            toggleUnitChange.toggled.connect(self._slot_toggleImmutableUnits)
        
        resetAction = cm.addAction("Reset")
        resetAction.triggered.connect(self._slot_reset)
        cm.popup(self.mapToGlobal(evt.pos()))
        
    def setMinimum(self, value:typing.Optional[typing.Union[float, pq.Quantity]]=None):
        r"""Overloads QDoubleSpinBox.setMinimum, to accept:
        • a None
        • a float
        • a scalar Quantity
    
        When None, the minimum value will be set to -math.inf
        """
        if value is None:
            super().setMinimum(self._default_internal_minimum)
            
        elif isinstance(value, float):
            super().setMinimum(value)
            
        elif isinstance(value, pq.Quantity):
            if value.size > 1:
                raise TypeError(f"Expecting a scalar quantity, not an array")
            val = float(value.magnitude)
            units = value.units
            super().setMinimum(val)
            self.units = units
            
        self._internal_minimum = super().minimum()
        
    def setMaximum(self, value:typing.Optional[typing.Union[float, pq.Quantity]]=None):
        r"""Overloads QDoubleSpinBox.setMaximum, to accept:
        • a None
        • a float
        • a scalar Quantity
    
        When None, the maximum value will be set to math.inf
        """
        if value is None:
            super().setMaximum(self._default_internal_maximum)
            
        elif isinstance(value, float):
            super().setMaximum(value)
            
        elif isinstance(value, pq.Quantity):
            if value.size > 1:
                raise TypeError(f"Expecting a scalar quantity, not an array")
            val = float(value.magnitude)
            units = value.units
            super().setMaximum(val)
            self.units = units
            
        self._internal_maximum = super().maximum()
            
    def setRange(self, minimum:typing.Optional[typing.Union[float, pq.Quantity]]=None, maximum:typing.Optional[typing.Union[float, pq.Quantity]]=None):
        r"""Overloads QDoubleSpinBox.setRange to accept:
        • floats
        • scalar Quantity
        • None
    
        for either 'minimum' or 'maximum'
    
        When either is None, the 'minimum' and 'maximum' will be set to
        -math.inf and math.inf, respectively.
        """
        
        if all(isinstance(v, pq.Quantity) for v in (minimum, maximum)):
            # NOTE: 2022-11-07 09:55:43
            # sanity check when both are quantities
            if any(v.size > 1 for v in (minimum, maximum)):
                raise TypeError("Expecting scalar quantities for both minimum and maximum ")
            
            if scq.unitsConvertible(minimum, maximum):
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
        ret = super().minimum() 
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret
        return ret  * self.units
    
    def maximum(self):
        ret = super().maximum() 
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret
        return ret * self.units
    
    def value(self) -> pq.Quantity:
        r""" Reimplements QDoubleSpinBox.value() to return a quantity
        """
        if self.specialValueText() == "NA":
            return pd.NA
        elif self.specialValueText() == "NaN":
            return np.nan * self.units
        else:
            ret = self._magnitude_
            if self._keepDimensionless_ or self._forceDimensionless_:
                return ret
            return ret * self.units
        
    def getDecimals(self) -> int:
        """
    """
        return self._decimals_
    
    def decimals(self) -> int:
        return self._decimals_
    
    def setDecimals(self, val:int):
        if val < 0:
            val = 0
        self._decimals_ = val
        super().setDecimals(self._decimals_)
    
    def validate(self, text, pos):
        validator = InftyDoubleValidator(parent=self)
        validator.suffix = self.suffix()
        validator.setDecimals(self.getDecimals()) 
        # NOTE: 2023-12-19 14:37:35
        # self.decimals() is a function !!!
        # validator.setDecimals(self.decimals) # self.decimals inherited from QDoubleSpinBox
        valid = validator.validate(text, pos)
        validstr = validatorString(valid[0])
        # print(f"{self.__class__.__name__}[{self.objectName()}].validate text: {text}, pos: {pos} ⇒ {validstr}")
        return valid
    
    def valueFromText(self, text:str):
        suffix = self._suffix_
        prefix = self._prefix_
        if suffix in text:
            s = text.strip(suffix)
        else:
            s = text
            
        if prefix in s:
            s = s.strip(prefix)
            
        s = s.replace(",", "")
        
        # print(f"{self.__class__.__name__}.valueFromText(text={text}) -> s: {s}")
            
        if s == "NA":
            return pd.NA
        elif s.lower() == "nan":
            return math.nan * self.units
        else:
            ret = float(s) if len(s) else math.nan
            # print(f"{self.__class__.__name__}.valueFromText(text={text}) -> ret {ret}")
            units = self.units
            return ret * units.units if isinstance(units, pq.Quantity) else ret

    def textFromValue(self, value:typing.Union[float, pq.Quantity, np.ndarray]):
        if isinstance(value, (pq.Quantity, np.ndarray)):
            if value.size > 1:
                return "NA"
                
            units = value.units if isinstance(value, pq.Quantity) else pq.dimensionless
            prefix = ""
            suffix = ""
            family = scq.getUnitFamily(units)
            if family == "Currency":
                prefix = f"{units.dimensionality.unicode}"
            else:
                suffix = f"{units.dimensionality.unicode}"
                
            fval = float(value.magnitude)
            
            if np.isnan(fval):
                ret = "NaN"
            elif np.isinf(fval):
                ret = "-Inf" if fval in (-np.inf, -mathl.inf) else "Inf"
            else:
                ret = f"{fval:.{self.decimals()}}"
                # ret = super().textFromValue(float(value.magnitude))
            
            if len(prefix):
                ret = f"{prefix} {ret}"
            if len(suffix):
                ret = f"{ret} {suffix}"
                
            return ret
            
        elif isinstance(value, float):
            if np.isnan(value):
                ret = "NaN"
            elif np.isinf(value):
                ret = "-Inf" if value == -np.inf else "Inf"
            else:
                ret = f"{value:.{self.decimals()}}"
                # ret = super().textFromValue(value)
            
            return ret

        else:
            return "NA"
            
    def setValue(self, value:typing.Union[pq.Quantity, float, int, type(pd.NA)]):
        r"""Also allows changing the units if not convertible to current ones.
        Otherwise the value will be rescaled to current units.
    WARNING: This is different from the case when new units are chosen while
    self.rescaleOnUnitChange is True.
    """
        if isinstance(value, pq.Quantity):
            if value.size > 1:
                # return # Only scalar quantities are allowed
                raise TypeError("Only scalar quantities are allowed")
            
            fval = float(value.magnitude)
            
            if not (self._keepDimensionless_ or self._forceDimensionless_):
                if scq.unitsConvertible(self.units, value.units):
                    if fval > -math.inf and fval < math.inf:
                        fval = float(value.rescale(self.units).magnitude)
                else:
                    self.units = value.units
                
            self._magnitude_ = fval
            
        elif value is pd.NA or value in(math.nan, np.nan):
            self._magnitude_ = value
            
        elif isinstance(value, float):
            self._magnitude_ = value
        
        elif isinstance(value, int):
            self._magnitude_ = float(value)
            
        else:
            raise ValueError(f"Incompatible value: {value}")
            
        if isinstance(self._magnitude_, float):
            super().setValue(self._magnitude_)
            text = f"{self._magnitude_:.{self.decimals()}}"
            specialText = "-inf" if self._magnitude_ == -math.inf else "inf" if self._magnitude_ == math.inf else ""
            if len(specialText):
                super().setSpecialValueText(specialText)
                text = specialText
                
            if len(self._prefix_):
                text = f"{self._prefix_} {text}"
                
            if len(self._suffix_):
                text = f"{text} {self._suffix_}"
                
            self.lineEdit().setText(text)
            
        elif self._magnitude_ in (pd.NA, math.nan, np.nan):
            super().setMinimum(-math.inf)
            specialText = "NA" if self._magnitude_ is pd.NA else "NaN"
            super().setSpecialValueText(specialText)
            super().setValue(-math.inf)
            
            text = specialText
            
            if len(self._prefix_):
                text = f"{self._prefix_} {text}"
                
            if len(self._suffix_):
                text = f"{text} {self._suffix_}"
            
            self.lineEdit().setText(text)
                
        else:
            raise TypeError(f"Expecting a scalar quantity, a float or pd.NA; instead, got {type(value).__name__}")
        
    @property
    def disableUnitChange(self) -> bool:
        return self._disableUnitChange_
    
    @disableUnitChange.setter
    def disableUnitChange(self, val:bool):
        self._disableUnitChange_ = val
    
    @property
    def rescaleOnUnitChange(self)->bool:
        if self._keepDimensionless_ or self._forceDimensionless_:
            return False
        return self._rescaleOnUnitChange_
    
    @rescaleOnUnitChange.setter
    def rescaleOnUnitChange(self, val:bool):
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            self._rescaleOnUnitChange_ = val
        
    @property
    def unitFamily(self):
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            return self._unitFamily_
    
    @property
    def familyRestriction(self) -> str:
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            return self._restrictedToFamily_
    
    @familyRestriction.setter
    def familyRestriction(self, value:typing.Optional[typing.Union[str, bool]] = None):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return 
        
        if isinstance(value, str):
            if value in scq.UNITS_DICT:
                self._restrictedToFamily_ = value
                
            elif isinstance(value, bool):
                if value:
                    self._restrictedToFamily_ = scq.getUnitFamily(self.units)
        else:
            self._restrictedToFamily_ = None
    
    @Slot()
    def _slot_setUnitsGUI(self):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return
        dlg = qd.QuickDialog(parent = self, title="Set units")
        quantityWidget = QuantityChooserWidget(parent = dlg)
        quantityWidget.units = self._units_
        if isinstance(self._restrictedToFamily_, str) and self._restrictedToFamily_ in scq.UNITS_DICT:
            quantityWidget.familyRestriction = self._restrictedToFamily_
        else:
            quantityWidget.familyRestriction = None
            
        dlg.addWidget(quantityWidget)
        dlg.adjustSize()
        if dlg.exec():
            self.units = quantityWidget.units
            
    @Slot()
    def _slot_setSingleStepGUI(self):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return 
        dlg = qd.QuickDialog(parent=self, title="Set single step")
        # stepInput = qd.HSpinBox(dlg, "Step (float)", widget_type="d")
        stepInput = qd.HSpinBox(dlg, "Step (float|Scalar quantity):", widget_type="q")
        stepInput.familyRestriction = scq.getUnitFamily(self.units)
        stepInput.rescaleOnUnitChange = True
        stepInput.units = self.units
        stepInput.setDecimals(3)
        stepInput.setValue(self.singleStep())
        adaptiveCheckBox = qd.CheckBox(dlg, "Adaptive")
        adaptiveCheckBox.setChecked(self.stepType() == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        dlg.addWidget(stepInput)
        dlg.addWidget(adaptiveCheckBox)
        dlg.adjustSize()
        if dlg.exec():
            value = stepInput.value()
            stepType = QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType if adaptiveCheckBox.isChecked() else QtWidgets.QAbstractSpinBox.DefaultStepType
            if value != self.singleStep():
                self.setSingleStep(value)
                
            if stepType != self.stepType():
                self.setStepType(stepType)
                
    @Slot(bool)
    def _slot_toggleImmutableUnits(self, val:bool):
        self.disableUnitChange = val
            
    @Slot(bool)
    def _slot_familyRestrictionChanged(self, value:bool):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return
        
        if value:
            family = scq.getUnitFamily(self.units)
            self._restrictedToFamily_ = family
        else:
            self._restrictedToFamily_ = None
            
    @Slot(bool)
    def _slot_setAdaptiveStep(self, value:bool):
        stepType = QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType if value else QtWidgets.QAbstractSpinBox.DefaultStepType
        
        if stepType != self.stepType():
            self.setStepType(stepType)
            
    @Slot(bool)
    def _slot_rescaleValueChanged(self, value:bool):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return
        self._rescaleOnUnitChange_ = value
            
    @Slot()
    def _slot_setDecimalsGUI(self):
        dlg = qd.QuickDialog(parent=self, title="Set decimals")
        decimalsInput = qd.HSpinBox(dlg, "Decimals (int) >= 0:")
        decimalsInput.setValue(self._decimals_)
        decimalsInput.setMinimum(0)
        dlg.addWidget(decimalsInput)
        dlg.adjustSize()
        if dlg.exec():
            value = decimalsInput.value()
            if value < 0:
                value  = 0
            self.setDecimals(value)
            
    @Slot()
    def _slot_setRangeGUI(self):
        dlg = qd.QuickDialog(parent=self, title="Set range (min, max)")
        group = qd.DialogGroup(dlg)
        unitsLabel = ""
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            unitsLabel = self._prefix_ if len(self._prefix_) else self._suffix_ if len(self._suffix_) else ""
        label = f" ({unitsLabel})" if len(unitsLabel) else ""
        minimumInput = qd.HSpinBox(group, f"Minimum{label}:", widget_type="f")
        minimumInput.setValue(super().minimum())
        maximumInput = qd.HSpinBox(group, f"Maximum{label}:", widget_type="f")
        maximumInput.setValue(super().maximum())
        group.addWidget(minimumInput)
        group.addWidget(maximumInput)
        dlg.addWidget(group)
        dlg.adjustSize()
        
        if dlg.exec():
            minimum = minimumInput.value()
            maximum = maximumInput.value()
            self.setMinimum(minimum)
            self.setMaximum(maximum)
            
    @Slot()
    def _slot_reset(self):
        self.setSingleStep(self._default_singleStep)
        self.setDecimals(self._default_decimals)
        self.units = self._default_units_
            
    def _calculateAdaptiveDecimalStep(self, steps:int) -> float:
        """Subject to future teaks, this is almost exactly what 
    QAbstractSpinBox.calculateAdaptiveDecimalStep() does.
    The difference is that we use self._magnitude_ instead of self.value()
    """
        value = self._magnitude_
        decimals = self.decimals()
        minStep = math.pow(10, -decimals)
        absVal = abs(value)
        
        if absVal < minStep:
            return minStep
        
        valNeg = value < 0
        stepsNeg = steps < 0
        
        if valNeg != stepsNeg:
            absVal /= 1.01
            
        shift = math.pow(10, 1 - math.floor(math.log(10, absVal)))
        absRound = round(absVal * shift, decimals) / shift
        logVal = math.floor(math.log(10, absRound)) - 1
        return max(minStep, math.pow(10, logVal))
        
    # # NOTE: 2025-09-15 18:22:34 TODO Finalize this
    def stepBy(self, steps:int):
        super().stepBy(steps)
        txt = self.lineEdit().displayText()
        val = self.valueFromText(txt)
        self._magnitude_ = float(val)
        self.sig_valueChanged.emit(self.value())
        
    def singleStep(self) -> pq.Quantity:
        ret = self._singleStep_
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret
        return ret * self.units
    
    def setSingleStep(self, value:float|pq.Quantity):
        if isinstance(value, pq.Quantity):
            if value.size != 1:
                raise TypeError("Scalar quantity expected")
            
            if not scq.unitsConvertible(value, self.units):
                raise ValueError(f"Cannot set single step with units (){value.units}) that are not scalable to the current units ({self.units})")
    
            v = float(value.rescale(self.units).magnitude)
            
        elif isinstance(value, float):
            v = value
        else:
            raise TypeError(f"Expecting a scalar quantity or float; instead, got a {type(value).__name__}")
        
        self._singleStep_ = v
        
        super().setSingleStep(self._singleStep_)
        
    @property
    def keepDimensionless(self) -> bool:
        return self._keepDimensionless_
    
    @keepDimensionless.setter
    def keepDimensionless(self, val:bool):
        self._keepDimensionless_ = val
        if self._keepDimensionless_ or self._forceDimensionless_:
            super().setSuffix("")
            super().setPrefix("")
        else:
            super().setSuffix(self._suffix_)
            super().setPrefix(self._prefix_)
            
        self.update()
        
    @property
    def forceDimensionless(self) -> bool:
        return self._forceDimensionless_
    
    @forceDimensionless.setter
    def forceDimensionless(self, val:bool):
        self._forceDimensionless_ = val
        self.update()

class ComplexSpinBox(QtWidgets.QFrame):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    
    _default_units_                =  pq.dimensionless
    _default_internal_minimum_real = _default_internal_minimum_imag = -math.inf
    _default_internal_maximum_real = _default_internal_maximum_imag =  math.inf
        
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None,
                 units:typing.Optional[typing.Union[pq.Quantity, float, complex, int]]=None, 
                 singleStepReal:typing.Optional[float]=None, 
                 singleStepImag:typing.Optional[float]=None, 
                 stepTypeReal:typing.Optional[QtWidgets.QAbstractSpinBox.StepType] = None,
                 stepTypeImag:typing.Optional[QtWidgets.QAbstractSpinBox.StepType] = None,
                 decimals:typing.Optional[int]=None,
                 decimalsReal:typing.Optional[int]=None,
                 decimalsImag:typing.Optional[int]=None,
                 minimumImag:typing.Optional[typing.Union[pq.Quantity, float]]=None, 
                 maximumReal:typing.Optional[typing.Union[pq.Quantity, float]]=None,
                 maximumImag:typing.Optional[typing.Union[pq.Quantity, float]]=None,
                 minimumReal:typing.Optional[typing.Union[pq.Quantity, float]]=None, 
                 useQuantities:bool=False,
                 unitsFamily:typing.Optional[str]=None, 
                 fixUnitFamily:typing.Optional[typing.Union[str, bool]]=None,
                 rescaleWithUnitsChange:bool=False,
                 keepDimensionless:bool=False, 
                 ):
        QtWidgets.QFrame.__init__(self, parent)
        if isinstance(parent, QtWidgets.QWidget):
            parent.addWidget(self)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.prefixLabel = QtWidgets.QLabel(self)
        self.prefixLabel.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.prefixLabel.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        
        # self.realSpinBox = QtWidgets.QSpinBox(self)
        self.realSpinBox = QuantitySpinBox(self, decimals=3)#, keepDimensionless = True)
        self.realSpinBox.forceDimensionless = True
        self.realSpinBox.sig_valueChanged.connect(self._slot_valueChanged)
        # self.imagSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.imagSpinBox = QuantitySpinBox(self, decimals=3)#, keepDimensionless = True)
        self.imagSpinBox.forceDimensionless = True
        self.imagSpinBox.sig_valueChanged.connect(self._slot_valueChanged)
        self.plusLabel = QtWidgets.QLabel(self)
        self.plusLabel.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.plusLabel.setText(" + ")
        self.plusLabel.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.jLabel = QtWidgets.QLabel(self)
        self.jLabel.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.jLabel.setText(" × j")
        self.jLabel.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.suffixLabel = QtWidgets.QLabel(self)
        self.suffixLabel.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.suffixLabel.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        
        self.layout.addWidget(self.prefixLabel)
        self.layout.addWidget(self.realSpinBox)
        self.layout.addWidget(self.plusLabel)
        self.layout.addWidget(self.imagSpinBox)
        self.layout.addWidget(self.jLabel)
        self.layout.addWidget(self.suffixLabel)
        self.layout.addStretch(5)
        
        self._restrictedToFamily_:typing.Optional[str] = None
        self._rescaleOnUnitChange_:bool = False
        self._keepDimensionless_ = keepDimensionless
        self._forceDimensionless_:bool = False
        
        self._units_:pq.Quantity = self._default_units_
        self._magnitude_:complex = complex(0.0, 0.0)
        self._prefix_ = ""
        self._suffix_ = ""
        
        if isinstance(units, pq.Quantity):
            self._units_ = units.units
            if not isinstance(units, pq.UnitQuantity):
                if units.size != 1:
                    raise TypeError(f"Expecting a scalar quantity; instead, got a Quantity array with {units.size} elements")
                self._magnitude_ = complex(units.magnitude)
        else:
            if isinstance(units, (float, int)):
                self._magnitude_ = complex(units)
            elif isinstance(units, complex):
                self._magnitude_ = units
            elif units is not None:
                raise TypeError(f"Invalid 'units' argument: {units}")
                
            self._units_ = self._default_units_
        
        self._unitFamily_ = scq.getUnitFamily(self._units_)
            
        if self._units_.dimensionality == pq.dimensionless.dimensionality:
            self._prefix_ = ""
            self._suffix_ = ""
        else:
            symbol = self._units_.dimensionality.unicode
            if self._unitFamily_ == "Currency":
                self._prefix_ = f"{symbol} "
                self._suffix_ = ""
            else:
                self._prefix_ = ""
                self._suffix_ = f" ({symbol})"
                
        self._default_singleStep_real = self.realSpinBox.singleStep()
        
        if isinstance(singleStepReal,float):
            self._singleStepReal_ = singleStepReal
            
        elif singleStepReal is None:
            self._singleStepReal_ = self._default_singleStep_real
        else:
            raise TypeError(f"singleStepReal expected to be a float or None; instead, got {singleStepReal}")
            
        self._default_singleStep_imag = self.imagSpinBox.singleStep()
        if isinstance(singleStepImag,float):
            self._singleStepImag_ = singleStepImag
            
        elif singleStepImag is None:
            self._singleStepImag_ = self._default_singleStep_imag
        else:
            raise TypeError(f"singleStepImag expected to be a float or None; instead, got {singleStepImag}")
            
        self._default_decimals_real = -int(math.log10(abs(self._singleStepReal_))) if (self._singleStepReal_ < 1 and self._singleStepReal_ > -1) else 1
        self._decimals_real = self._default_decimals_real
        
        if isinstance(decimalsReal, int) and decimalsReal >= 0:
            self._decimals_real = decimalsReal
        
        elif decimalsReal is None:
            if isinstance(decimals, int) and decimals >= 0:
                self._decimals_real = decimals
            else:
                self._decimals_real = self._default_decimals_real
            
        else:
            raise TypeError(f"decimalsReal expected to be an int >= 0 or None; instead, got {decimalsReal}")

        self._default_decimals_imag = -int(math.log10(abs(self._singleStepImag_))) if (self._singleStepImag_ < 1 and self._singleStepImag_ > -1) else 1
        self._decimals_imag = self._default_decimals_imag
        
        if isinstance(decimalsImag, int) and decimalsImag >= 0:
            self._decimals_imag = decimalsImag
            
        elif decimalsImag is None:
            if isinstance(decimals, int) and decimals >= 0:
                self._decimals_imag = decimals
            else:
                self._decimals_imag = self._default_decimals_imag
            
        else:
            raise TypeError(f"decimalsImag expected to be an int >= 0 or None; instead, got {decimalsImag}")

        self._internal_minimum_real = self._default_internal_minimum_real
        self._internal_maximum_real = self._default_internal_maximum_real
        
        self._internal_minimum_imag = self._default_internal_minimum_imag
        self._internal_maximum_imag = self._default_internal_maximum_imag
        
        if isinstance(stepTypeReal, QtWidgets.QAbstractSpinBox.StepType):
            self._stepType_real = stepTypeReal
        else:
            self._stepType_real = QtWidgets.QAbstractSpinBox.DefaultStepType
        
        if isinstance(stepTypeImag, QtWidgets.QAbstractSpinBox.StepType):
            self._stepType_imag = stepTypeImag
        else:
            self._stepType_imag = QtWidgets.QAbstractSpinBox.DefaultStepType
            
        self._setupSpinBox_(self.realSpinBox, self._internal_minimum_real,
                            self._internal_maximum_real, self._decimals_real,
                            self._singleStepReal_, self._stepType_real, self._magnitude_.real)
        
        self.realSpinBox.sig_valueChanged.connect(self._slot_valueChanged)
        
        self._setupSpinBox_(self.imagSpinBox, self._internal_minimum_imag,
                            self._internal_maximum_imag, self._decimals_imag,
                            self._singleStepImag_, self._stepType_imag,
                            self._magnitude_.imag)
        
        self.imagSpinBox.sig_valueChanged.connect(self._slot_valueChanged)
        
        self.prefixLabel.setText(self._prefix_)
        self.suffixLabel.setText(self._suffix_)
        
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        
    def _setupSpinBox_(self, spinBox, minimum, maximum, decimals, singleStep, stepType, value):
        spinBox.setMinimum(minimum)
        spinBox.setMaximum(maximum)
        spinBox.setDecimals(decimals)
        spinBox.setSingleStep(singleStep)
        spinBox.setStepType(stepType)
        spinBox.setValue(value)
        
    def value(self) -> complex | pq.Quantity:
        ret = self._magnitude_
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret
        
        return ret * self._units_
    
    def validate(self):
        r"""For compatibilty with qd.QuickDialog"""
        return True

    def setValue(self, value:typing.Union[complex, float, int, pq.Quantity]):
        if isinstance(value, pq.Quantity):
            if value.size > 1:
                # return # Only scalar quantities are allowed
                raise TypeError("Only scalar quantities are allowed")
            
            if value.dtype == np.dtype("complex"):
                cval = complex(value.magnitude)
            else:
                cval = complex(float(value.magnitude), 0.0)
                
            if not (self._keepDimensionless_ or self._forceDimensionless_):
                if scq.unitsConvertible(self.units, value.units):
                    if any( (v > -math.inf and v < math.inf) for v in (cval.real, cval.imag)):
                        cval = complex((cval*value.units).rescale(self.units).magnitude)
                else:
                    self.units = value.units
                    
            self._magnitude_ = cval
                    
        elif value in (pd.NA, math.nan, np.nan):
            self._magnitude_ = complex(value, value)
            
        elif isinstance(value, float):
            self._magnitude_ = complex(value, 0.0)
        
        elif isinstance(value, int):
            self._magnitude_ = complex(float(value), 0.0)
        
        else:
            raise ValueError(f"Incompatible value: {value}")
        
        self.realSpinBox.setValue(self._magnitude_.real)
        self.imagSpinBox.setValue(self._magnitude_.imag)
            
    def decimals(self) -> tuple:
        return (self.realSpinBox.getDecimals(), self.imagSpinBox.getDecimals())
    
    def setDecimals(self, value:typing.Union[int, typing.Sequence[int]]):
        if isinstance(value, typing.Sequence) and all(isinstance(v, int) for v in value):
            if any (v<0 for v in value):
                raise ValueError("Decimals must be >= 0")
            
            if len(value) < 2:
                self.realSpinBox.setDecimals(value[0])
                self.imagSpinBox.setDecimals(value[0])
            else:
                self.realSpinBox.setDecimals(value[0])
                self.imagSpinBox.setDecimals(value[1])
                
        elif isinstance(value, int):
            if value < 0:
                raise ValueError("Decimals must be >= 0")
            self.realSpinBox.setDecimals(value)
            self.imagSpinBox.setDecimals(value)
            
        
    def singleStep(self) -> tuple:
        ret = (self.realSpinBox.singleStep(), self.imagSpinBox.singleStep())
        if self._keepDimensionless_ or self._forceDimensionless_:
            return ret
        return tuple(map(lambda v: v * self.units, ret))
        
    def setSingleStep(self, value:typing.Union[typing.Sequence[float|int|pq.Quantity], float, int, pq.Quantity]):
        if isinstance(value, pq.Quantity):
            if value.size == 1:
                realStep = imagStep = float(value.magnitude)
            elif value.size == 2:
                realStep, imagStep = tuple(map(lambda v: float(v.magnitude), value))
            else:
                raise TypeError(f"Invalid number of elements in value argument: {value.size}; expecting 1 or 2")
            
            if not scq.unitsConvertible(value, self.units):
                raise ValueError(f"Cannot set single step with units ({value.units}) that are not scalable to the current units ({self.units})")
            realStep = float((realStep*value.units).rescale(self.units).magnitude)
            imagStep = float((imagStep*value.units).rescale(self.units).magnitude)
            
            
        elif isinstance(value, (float, int)):
            realStep = imagStep = float(value)
            
        elif isinstance(value, typing.Sequence):
            if len(value) == 1:
                value = value[0]
                if isinstance(value, (float, int)):
                    realStep = imagStep = float(value)
                    
                elif isinstance(value, pq.Quantity):
                    if not scq.unitsConvertible(value, self.units):
                        raise ValueError(f"Cannot set single step with units ({value.units}) that are not scalable to the current units ({self.units})")
                    realStep = imagStep = float(value.rescale(self.units).magnitude)
                else:
                    raise TypeError(f"Wrong value type: {type(value).__name__}")
                    
            elif len(value) >= 2:
                realStep, imagStep = value[0:2]
                
                if isinstance(realStep, (float, int)):
                    realStep = float(realStep)
                
                elif isinstance(realStep, pq.Quantity):
                    if not scq.unitsConvertible(realStep, self.units):
                        raise ValueError(f"Cannot set single step with units ({realStep.units}) that are not scalable to the current units ({self.units})")
                    realStep = float(realStep.rescale(self.units).magnitude)
                    
                else:
                    TypeError(f"Wrong real value type: {type(realStep).__name__}")
                    
                if isinstance(imagStep, (float, int)):
                    imagStep = float(imagStep)
                
                elif isinstance(imagStep, pq.Quantity):
                    if not scq.unitsConvertible(imagStep, self.units):
                        raise ValueError(f"Cannot set single step with units ({imagStep.units}) that are not scalable to the current units ({self.units})")
                    imagStep = float(imagStep.rescale(self.units).magnitude)
                    
                else:
                    TypeError(f"Wrong real value type: {type(imagStep).__name__}")
                    
            else:
                raise TypeError("Expecting at least one value in the sequence")
        else:
            raise TypeError(f"Expecting a scalar quantity, float, int or a sequence of at least twpo of these data types; instead, got a {type(value).__name__}")
        
        self.realSpinBox.setSingleStep(realStep)
        self.imagSpinBox.setSingleStep(imagStep)
        
    def stepType(self) -> tuple:
        return (self.realSpinBox.stepType(), self.imagSpinBox.stepType())
    
    def setStepType(self, value:typing.Sequence[QtWidgets.QAbstractSpinBox.StepType]):
        if isinstance(value, typing.Sequence) and len(value) == 2 and all(isinstance(v, QtWidgets.QAbstractSpinBox.StepType) for v in value):
            self.realSpinBox.setStepType(value[0])
            self.imagSpinBox.setStepType(value[1])
            
        else:
            raise ValueError(f"Incorrect step type specification ({value}); expecting a sequence of two QtWidgets.QAbstractSpinBox.StepType enum values")

    def contextMenuEvent(self, evt):
        cm = QtWidgets.QMenu("Options", self)
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            setUnitsAction = cm.addAction("Set units")
            setUnitsAction.triggered.connect(self._slot_setUnitsGUI)
        setDecimalsAction = cm.addAction("Set decimals")
        setDecimalsAction.triggered.connect(self._slot_setDecimalsGUI)
        setSingleStepAction = cm.addAction("Set single step")
        setSingleStepAction.triggered.connect(self._slot_setSingleStepGUI)
        # adaptiveStepAction = cm.addAction("Adaptive step")
        # adaptiveStepAction.setCheckable(True)
        # adaptiveStepAction.setChecked(self.stepType() == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        # adaptiveStepAction.toggled.connect(self._slot_setAdaptiveStep)
        # setRangeAction = cm.addAction("Set range (min, max)")
        # setRangeAction.triggered.connect(self._slot_setRangeGUI)
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            cm.addSeparator()
            rescaleValueAction = cm.addAction("Rescale on unit change")
            rescaleValueAction.setCheckable(True)
            rescaleValueAction.setChecked(self._rescaleOnUnitChange_)
            rescaleValueAction.toggled.connect(self._slot_rescaleValueChanged)
            restrictAction = cm.addAction("Fix units family")
            restrictAction.setCheckable(True)
            restrictAction.setChecked(isinstance(self._restrictedToFamily_, str) and self._restrictedToFamily_ in scq.UNITS_DICT)
            restrictAction.toggled.connect(self._slot_familyRestrictionChanged)
        cm.addSeparator()
        if not self.forceDimensionless:
            toggleDimensionlessAction = cm.addAction("Ignore dimensionality")
            toggleDimensionlessAction.setCheckable(True)
            toggleDimensionlessAction.setChecked(self._keepDimensionless_)
            toggleDimensionlessAction.toggled.connect(self._slot_keepDimensionless)
        resetAction = cm.addAction("Reset")
        resetAction.triggered.connect(self._slot_reset)
        cm.popup(self.mapToGlobal(evt.pos()))
        
    @Slot(float)
    def _slot_valueChanged(self, val):
        self.sig_valueChanged.emit(self.value())
        
    @Slot(bool)
    def _slot_keepDimensionless(self, val:bool):
        self.keepDimensionless = val
            
    @Slot()
    def _slot_setDecimalsGUI(self):
        realVal = self._decimals_real
        imagVal = self._decimals_imag
        dlg  = qd.QuickDialog(parent=self, title="Set decimals")
        realInput = qd.HSpinBox(dlg, "Decimals, real part (int) >= 0:")
        realInput.setMinimum(0)
        realInput.setValue(realVal)
        imagInput = qd.HSpinBox(dlg, "Decimals, imaginary part (int) >= 0:")
        imagInput.setMinimum(0)
        imagInput.setValue(imagVal)
        dlg.addWidget(realInput)
        dlg.addWidget(imagInput)
        dlg.adjustSize()
        if dlg.exec():
            realVal = realInput.value()
            if realVal < 0:
                realVal = 0
            imagVal = imagInput.value()
            if imagVal < 0:
                imagVal = 0
        self.realSpinBox.setDecimals(realVal)
        self.imagSpinBox.setDecimals(imagVal)
        
    @Slot()
    def _slot_setSingleStepGUI(self):
        realVal = self._singleStepReal_
        imagVal = self._singleStepImag_
        dlg  = qd.QuickDialog(parent=self, title="Set single step")
        realGrp = qd.DialogGroup(dlg)
        realInput = qd.HSpinBox(realGrp, "Real part:", widget_type="f")
        realInput.setValue(realVal)
        adaptiveRealCheckBox = qd.CheckBox(realGrp, "Adaptive")
        adaptiveRealCheckBox.setChecked(self.stepType()[0] == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        realGrp.addWidget(realInput, QtCore.Qt.AlignVCenter)
        realGrp.addWidget(adaptiveRealCheckBox, QtCore.Qt.AlignVCenter)
        # realInput.setMinimum(0)
        imagGrp = qd.DialogGroup(dlg)
        imagInput = qd.HSpinBox(imagGrp, "Imaginary part:", widget_type="f")
        imagInput.setValue(imagVal)
        adaptiveImagCheckBox = qd.CheckBox(imagGrp, "Adaptive")
        adaptiveImagCheckBox.setChecked(self.stepType()[1] == QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        imagGrp.addWidget(imagInput, QtCore.Qt.AlignVCenter)
        imagGrp.addWidget(adaptiveImagCheckBox, QtCore.Qt.AlignVCenter)
        # imagInput.setMinimum(0)
        
        # dlg.addWidget(realInput)
        # dlg.addWidget(imagInput)
        dlg.addWidget(realGrp)
        dlg.addWidget(imagGrp)
        dlg.adjustSize()
        if dlg.exec():
            realVal = realInput.value()
            imagVal = imagInput.value()
            adaptiveReal = QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType if adaptiveRealCheckBox.isChecked() else QtWidgets.QAbstractSpinBox.DefaultStepType
            adaptiveImag = QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType if adaptiveImagCheckBox.isChecked() else QtWidgets.QAbstractSpinBox.DefaultStepType
            self.realSpinBox.setSingleStep(realVal)
            self.realSpinBox.setStepType(adaptiveReal)
            self.imagSpinBox.setSingleStep(imagVal)
            self.imagSpinBox.setStepType(adaptiveImag)

    @Slot()
    def _slot_setUnitsGUI(self):
        dlg = qd.QuickDialog(parent = self, title="Set units")
        quantityWidget = QuantityChooserWidget(parent = dlg)
        quantityWidget.units = self._units_
        if isinstance(self._restrictedToFamily_, str) and self._restrictedToFamily_ in scq.UNITS_DICT:
            quantityWidget.familyRestriction = self._restrictedToFamily_
        else:
            quantityWidget.familyRestriction = None
            
        dlg.addWidget(quantityWidget)
        dlg.adjustSize()
        if dlg.exec():
            self.units = quantityWidget.units
            
    @Slot(bool)
    def _slot_rescaleValueChanged(self, value:bool):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return
        self._rescaleOnUnitChange_ = value
        # self.realSpinBox.rescaleOnUnitChange = value
        # self.imagSpinBox.rescaleOnUnitChange = value
            
    @Slot(bool)
    def _slot_familyRestrictionChanged(self, value:bool):
        if self._keepDimensionless_ or self._forceDimensionless_:
            return
        
        if value:
            family = scq.getUnitFamily(self.units)
            self._restrictedToFamily_ = family
        else:
            self._restrictedToFamily_ = None
            
    @Slot(object)
    def _slot_valueChanged(self, val_:object):
        self.sig_valueChanged.emit(self.value())
        
    @Slot()
    def _slot_reset(self):
        for w in (self.realSpinBox, self.imagSpinBox):
            w.self_reset()
        self.units = self._default_units_
            
    @property
    def units(self):
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            return self._units_
    
    @units.setter
    def units(self, value:typing.Optional[pq.Quantity] = None):
        # print(f"{self.__class__.__name__}.units.setter: value = {value}")
        if self._keepDimensionless_ or self._forceDimensionless_:
            return 
        
        if not isinstance(value, pq.Quantity):
            value = pq.dimensionless
            
        myVal = self.value()
        
        if isinstance(myVal, pq.Quantity) and myVal.dtype == np.dtype("complex"):
            myReal = float(myVal.magnitude.real) 
            myImag = float(myVal.magnitude.imag)
        else:
            myReal = float(myVal.magmitude)
            myImag = 0.0
            
        if self._rescaleOnUnitChange_ and scq.unitsConvertible(value, self._units_) and any(v not in (math.nan, np.nan, -math.inf, math.inf, -np.inf, np.inf) for v in (myReal, myImag)):
            scaledval = self.value().rescale(value)
            newval = complex(scaledval.magnitude) if scaledval.dtype == np.dtype("complex") else float(scaledval.magnitude)
            ratio = newval/self._magnitude_
            realStep = self.realSpinBox.singleStep() * ratio
            imagStep = self.imagSpinBox.singleStep() * ratio
            self._magnitude_ = complex(scaled.magnitude) if scaledval.dtype == np.dtype("complex") else float(scaledval.magnitude)
            self._units_ = newval.units
            self.realSpinBox.setValue(self._magnitude_.real)
            self.realSpinBox.setSingleStep(realStep)
            self.imagSpinBox.setValue(self._magnitude_.imag)
            self.imagSpinBox.setsingleStep(imagStep)
        else:
            self._units_ = value.units
            
        self._unitFamily_ = scq.getUnitFamily(self._units_)
        
        self._suffix_ = ""
        self._prefix_ = ""
        
        if self._units_.dimensionality != pq.dimensionless.dimensionality:
            symbol = self._units_.dimensionality.unicode
            if self._unitFamily_ == "Currency":
                self._prefix_ = f"{symbol} "
                self._suffix_ = ""
            else:
                self._prefix_ = ""
                self._suffix_ = f" ({symbol})"
        
        # if np.isnan(self._magnitude_):
        #     text = "NaN"
        #     super().setSpecialValueText(text)
            
        # elif np.isinf(self._magnitude_):
        #     text = "-Inf" if self._magnitude_ in (-np.inf, -math.inf) else "Inf"
        #     super().setSpecialValueText(text)
        # else:
        #     text = f"{self._magnitude_:.{self.decimals()}}"
            
        self.prefixLabel.setText(self._prefix_)
        self.suffixLabel.setText(self._suffix_)
        
    @property
    def keepDimensionless(self) -> bool:
        return self._keepDimensionless_
    
    @keepDimensionless.setter
    def keepDimensionless(self, val:bool):
        self._keepDimensionless_ = val
        if self._keepDimensionless_ or self._forceDimensionless_:
            super().setSuffix("")
            super().setPrefix("")
        else:
            super().setSuffix(self._suffix_)
            super().setPrefix(self._prefix_)
            
        self.update()
        
    @property
    def forceDimensionless(self) -> bool:
        return self._forceDimensionless_
    
    @forceDimensionless.setter
    def forceDimensionless(self, val:bool):
        self._forceDimensionless_ = val
        self.update()

    @property
    def rescaleOnUnitChange(self)->bool:
        if self._keepDimensionless_ or self._forceDimensionless_:
            return False
        return self._rescaleOnUnitChange_
    
    @rescaleOnUnitChange.setter
    def rescaleOnUnitChange(self, val:bool):
        if not (self._keepDimensionless_ or self._forceDimensionless_):
            self._rescaleOnUnitChange_ = val
        
