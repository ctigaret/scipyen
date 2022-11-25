# -*- coding: utf-8 -*-
"""Widgets for parameter inputs
"""
import math, numbers, typing, os
import numpy as np
import quantities as pq
import pandas as pd
from core.strutils import str2symbol
from gui import guiutils
import gui.quickdialog as qd
from gui.widgets.small_widgets import QuantitySpinBox

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# Ui_TestParamsWidgets2, QWidget = loadUiType(os.path.join(__module_path__, "TestParamsWidget2.ui"), from_imports=True, import_from="gui")
# 
# class TestParamsWidgets2(QWidget, Ui_TestParamsWidgets2):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setupUi(self)

class ModelParametersWidget(QtWidgets.QWidget):
    """A widget composed of labels and spin boxes for input of numeric values
    The child widgets (input field and labels) are arranged in a grid.
    There is support for numerical scalar parameters only, used for model fitting.

    NOTE 1: For now, the minimum/maximum values of the spin boxes are -math.inf and
    math.inf, respectively (but they can be altered manually/programmatically by
    accessing the spin boxes via the `widgets` property)

    NOTE 2: Internally, the parameters names and their values passed to the 
    constructor are stored in a pandas DataFrame which reflects the vertical or 
    horizontal layout of the widget. 
    This DataFrame is accessible via the read-only property `parameteers` of the
    widget.
    ATTENTION: Changes in the values of the spin boxes are not reflected in
    changes of the corresponding values in the DataFrame.

    NOTE: 3: The orientation of the widget is fixed at construction; it cannot be
    modified on a live instance of ModelParametersWidget.

    NOTE 4: This widget is intended for use models that take a relatively small
    number of numeric parameters. Although it does support an arbitrary number of
    parameters, is can quickly become cumbersome. In such cases, the 
    ModelParametersEditor  widget is recommended.
    
    
    """
    sig_dataChanged = pyqtSignal(name="sig_dataChanged")
    #                                 index(row), column name
    sig_parameterChanged = pyqtSignal(str,        str,        name="sig_parameterChanged")
    sig_badBounds = pyqtSignal(str, name="sig_badBounds")
    sig_infeasible_x0 = pyqtSignal(str, name="sig_infeasible_x0")
    
    _default_spin_decimals_ = 4
    _default_spin_step_ = 1e-4
    _mandatory_columns_ = ("Initial Value:", "Lower Bound:", "Upper Bound:")
    
    def __init__(self, parent:QtWidgets.QWidget=None, **kwargs):
        """ Constructor of ModelParametersWidget.
    
            Positional parameters:
            ======================
    
            parent: parent widget or None
    
            Var-keywords:
            =============
    
            parameters: sequence (tuple, list, 1D array-like) with the initial
                        values for the fit model;
            default: None
    
            names: None (default) or a sequence of str with the names 
                        of the parameters (it must have same number of elements 
                        as `parameters`)
    
            lower: scalar or 1D array-like with the same shape as `parameters` - 
                    the lower bounds; optional, default is -math.inf (same as 
                    -np.inf)
    
            upper: scalar or 1D array-like; the upper bounds; optional, default
                    is math.inf (or np.inf)
    
            spinStep:float, optional (default is None). 
                    Thhe step change for the spin boxes of the widget. 
                    
                    When None (the default), it will be determined from 
                    `parameters`.
            
            spinDecimals:int. optional (default is None). 
                    The number of decimals for float representation in the spin 
                    boxes of the widget.
    
                    When None (the default), it will be determined from 
                    `parameters`.
    
            orientation:str, "vertical" or "horizontal" (case-insensitive), optional
                        Default is "vertical".
    
                        Sets the orientation of the input fields.
    
                        When "vertical", the parameters' initial values (and, if
                        given, the lower and upper bounds) will be 
        """
        QtWidgets.QWidget.__init__(self, parent=parent)
        
        parameters = kwargs.pop("parameters", [])
        names = kwargs.pop("names", None)
        spinStep = kwargs.pop("spinStep", self._default_spin_step_)
        spinDecimals = kwargs.pop("spinDecimals", self._default_spin_decimals_)
        lower = kwargs.pop("lower", None)
        upper = kwargs.pop("upper", None)
        orientation = kwargs.pop("orientation", "vertical")
            
        if not isinstance(spinDecimals, int) or spinDecimals < 0:
            self._spinDecimals_ = self._default_spin_decimals_
        else:
            self._spinDecimals_ = spinDecimals
            
        if not isinstance(spinStep, float) or spinStep < 0:
            self._spinStep_ = self._default_spin_step_
        else:
            self._spinStep_ = spinStep
        
        self._spin_min_ = -math.inf
        self._spin_max_ =  math.inf
        
        self.spinBoxes = list()
        
        if orientation.lower() == "horizontal":
            self._verticalLayout_ = False
        else:
            self._verticalLayout_ = True
            
        self._parameters_ = self.setParameters(parameters, lower, upper, names,
                                               refresh=False)
            
        # if not self._verticalLayout_:
        #     self._parameters_ = self._parameters_.T
        
        self._configureUI_()# mus be called
        
    def _generate_widgets(self):
        paramsDF = self._parameters_
        # if self._verticalLayout_:
        #     paramsDF = self._parameters_
        # else:
        #     paramsDF = self._parameters_.T
            
        header = ["Parameters:"] + [c for c in self._parameters_.columns]
        minSpinWidth = list()
        self.spinBoxes = list()

        for layout_col, c in enumerate(header):   
            # NOTE: 2022-10-31 09:31:48
            # top row is the header → the first widget in ANY column is a QLabel
            w = QtWidgets.QLabel(c, self)
            w.setObjectName(f"label_{str2symbol(c)}_header")

            self.widgetsLayout.addWidget(w, 0, layout_col, 1, 1)

            for ki, i in enumerate(paramsDF.index): # row index into the DataFrame
                layout_row = ki + 1

                if layout_col == 0:
                    w = QtWidgets.QLabel(i, self)
                    w.setObjectName(f"label_{str2symbol(i)}")
                    
                else:
                    p = paramsDF.loc[i,c]
                    w = QuantitySpinBox(self)
                    
                    # WARNING: 2022-11-03 23:39:21
                    # This is for general case.
                    # Depending on the model for which this is intended, one may
                    # have to restrict these to physically (and mathematically)
                    # reasonable values by accessing these spine boxes directly
                    # (based on parameter name and value type i.e. initial, lower
                    # or upper bound)
                    # This can be done using self.getSpinBox() method, see
                    # mPSCanalysis.MPSCAnalysis for an example
                    w.setMinimum(self._spin_min_)
                    w.setMaximum(self._spin_max_)
                    
                    w.setDecimals(self.spinDecimals)
                    w.setSingleStep(self.spinStep)
                    w.valueChanged[float].connect(self._slot_newvalue)
                    w.setAccelerated(True)
                    w.setValue(p)
                    
                    t = w.text()
                    minSpinWidth.append(guiutils.get_text_width(t))
                    w.setObjectName(f"{str2symbol(i)}_{str2symbol(c)}_spinBox")
                    self.spinBoxes.append(w)
                    
                self.widgetsLayout.addWidget(w, layout_row, layout_col, 1, 1)
                
        sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sp.setHorizontalStretch(1)
        sp.setVerticalStretch(0)
        minWidth = max(minSpinWidth)
        for w in self.spinBoxes:
            w.setMinimumWidth(minWidth + 3*minWidth//10)
            w.setSizePolicy(sp)
            
    def _configureUI_(self):
        if not self.objectName():
            self.setObjectName("ModelParametersWidget")
        
        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setObjectName(u"gridLayout")
        self.widgetsLayout = QtWidgets.QGridLayout()
        self.widgetsLayout.setObjectName(u"widgetsLayout")
        self.gridLayout.addLayout(self.widgetsLayout, 0, 0, 1, 1)
        if isinstance(self._parameters_, pd.DataFrame) and self._parameters_.size > 0:
            self._generate_widgets()
            
    def _clear_widgets(self):
        to_remove = list()
        for w in self.spinBoxes:
            w.setParent(None)
            w.valueChanged[float].disconnect(self._slot_newvalue)
            self.widgetsLayout.removeWidget(w)
            to_remove.append(w)
            
        for w in to_remove:
            del(self.spinBoxes[self.spinBoxes.index(w)])
            
        self.update()
        
            
    def getSpinBox(self, paramName:str, value_type:str):
        """Access the spin box of a numeric parameter initial value, or boundary.
        
        Useful to restrict the of values for a particular spin box to a range
        that is both physically and numerically reasonable, AFER the widget has
        been constructed.
        
        See mPSCanalysis.MPSCAnalysis for an example.
        
        Parameters:
        ==========
        paramName: the name of the parameter
        value_type: the name of the parameter value type (e.g. "Initial Value:"
                    or "Lower Bound:" etc)
        """
        paramsDF = self.parameters
        rowNdx = list(paramsDF.index)
        colNdx = list(paramsDF.columns)
        
        paramNdx = rowNdx if self.isVertical else colNdx
        valueNdx = colNdx if self.isVertical else rowNdx
        
        if paramName not in paramNdx:
            raise ValueError(f"Parameter named {paramName} not found")
        if value_type not in valueNdx:
            raise ValueError(f"Parameter value for {value_type} not found")
        
        paramRow = paramNdx.index(paramName) + 1
        paramCol = valueNdx.index(value_type) + 1
        
        return self.widgetsLayout.itemAtPosition(paramRow, paramCol).widget()
            
    @property
    def isVertical(self):
        return self._verticalLayout_
    
    def setVertical(self, value:bool):
        # TODO/FIXME 2022-11-24 23:57:52
        if value == True:
            if not self.isVertical:
                self._verticalLayout_ = True
                self._clear_widgets()
                self._generate_widgets()
                
        else:
            if self.isVertical:
                self._verticalLayout_ = False
                self._clear_widgets()
                self._generate_widgets()
                
    
    @property
    def parameters(self):
        """A pandas DataFrame with model parameters, lower and upper bounds.
            Follows the widget's orientation
        
        Orientation must be changed BEFORE setting new parameters via the setter
        of this property
        """
        if self._verticalLayout_:
            return self._parameters_
        else:
            return self._parameters_.T
            
    @parameters.setter
    def parameters(self, params):
        if isinstance(params, pd.DataFrame) and all(s in params.columns for s in ("Initial Value:", "Lower Bound:", "Upper Bound:")):
            self.setParameters(params["Initial Value:"], 
                               lower = params["Lower Bound:"], 
                               upper = params["Upper Bound:"],
                               names = params.index,
                               refresh=True)
            
    def setParameters(self, parameters:typing.Sequence, lower=None, upper=None, names=None, refresh = True):
        """Generates new parameters data frame.
        
        The diusplay is refreshed UNLESS refresh is False. The display update
        either changes individual values in the spin boxes (if the new parameters
        names match the current ones) or repopulates the widget with a new set 
        of spin boxes.
        
        In either case, the refresh uses the current orientation (vertical or 
        horizontal) of the data layout.
        
        If a different orientation is required, then it must be set BEFORE 
        setting the new parameters.
        
        
        """
        paramsDF = None
        
        if isinstance(parameters, (tuple, list)) and len(parameters):
            if all(isinstance(p, pq.Quantity) for p in parameters):
                units = [p.units for p in parameters]
            else:
                units = []
            
            if names is None:
                names  = [f"parameter_{k}" for k in range(len(parameters))]
                
            elif isinstance(names, (tuple,list)):
                if not all(isinstance(s, str) for s in names):
                    raise TypeError("Expecting strings for parameter names")
                
                if any(len(s.strip()) == 0 for s in names):
                    raise TypeError("Cannot accept empty string for parameter names")
                
                if len(names) != len(parameters):
                    raise ValueError(f"When a sequence, names must have the same number of elements as parameters {len(parameters)}; instead, got {names}")
                
            else:
                raise TypeError(f"'names' must be a sequence or None; instead, got {names}")
                    
            if isinstance(lower, numbers.Number):
                if len(units):
                    lower = [lower * u for u in units]
                else:
                    lower = [lower] * len(parameters)
                    
            elif isinstance(lower, (tuple, list)):
                if len(lower) != len(parameters):
                    raise TypeError(f"'lower' expected to be a sequence of {len(parameters)} elements; instead, got {lower}")
                
                if not all(isinstance(v, (numbers.Number, pq.Quantity)) for v in lower):
                    raise TypeError(f"'lower' expected to contain scalars or scalar Quantity; instead, got {lower}")
                
                if all(isinstance(v, pq.Quantity) for v in lower) and any(v.size != 1 for v in lower):
                    raise TypeError(f"'lower' expected to contain scalars or scalar Quantity; instead, got {lower}")
                
            else:
                raise TypeError(f"'lower' expected to be a scalar or a sequence of {len(parameters)} elements; instead, got {lower}")
            
            if isinstance(upper, numbers.Number):
                if len(units):
                    upper = [upper *u for u in units]
                else:
                    upper = [upper] * len(parameters)
                
            elif isinstance(upper, (tuple, list)):
                if len(upper) != len(parameters):
                    raise TypeError(f"'upper' expected to be a sequence of {len(parameters)} elements; instead, got {upper}")
                
                if not all(isinstance(v, (numbers.Number, pq.Quantity)) for v in upper):
                    raise TypeError(f"'upper' expected to contain scalars or scalar Quantities; instead, got {upper}")
                
                if all(isinstance(v, pq.Quantity) for v in upper) and any(v.size !=1 for v in upper):
                    raise TypeError(f"'upper' expected to contain scalars or scalar Quantities; instead, got {upper}")
                
            else:
                raise TypeError(f"'upper' expected to be a scalar or a sequence of {len(parameters)} elements; instead, got {upper}")
        
            paramsDF = pd.DataFrame({"Initial Value:": parameters,
                                     "Lower Bound:":lower,
                                     "Upper Bound:":upper},
                                     index = names)
        elif isinstance(parameters, pd.DataFrame):
            if any(c not in parameters.columns for c in self._mandatory_columns_):
                raise ValueError(f"Dataframe lacks mandatory columns {self._mandatory_columns_}")
            
            if any (c not in self._mandatory_columns_ for c in parameters.columns):
                raise ValueError(f"Dataframe has unexpected columns; they should be: {self._mandatory_columns_}")
                
            paramsDF = parameters
            
        # else:
        #     raise TypeError(f"Expecting sequences 'parameters', 'lower', 'upper', 'names' or a DataFrame with appropriate layout; got {(type(parameters).__name__)} instead")
            
        if isinstance(paramsDF, pd.DataFrame):
            # NOTE: 2022-11-24 23:14:36
            # perform sanity checks on bounds
            for i in paramsDF.index:
                if paramsDF.loc[i, "Lower Bound:"] > paramsDF.loc[i, "Upper Bound:"]:
                    lo = paramsDF.loc[i, "Upper Bound:"]
                    up = paramsDF.loc[i, "Lower Bound:"]
                    paramsDF.loc[i, "Lower Bound:"] = lo
                    paramsDF.loc[i, "Upper Bound:"] = up
                    sig_badBounds.emit(str(i))
                    
                if paramsDF.loc[i, "Lower Bound:"] > paramsDF.loc[i, "Initial Value:"]:
                    paramsDF.loc[i, "Lower Bound:"] = paramsDF.loc[i, "Initial Value:"]
                    sig_infeasible_x0.emit(str(i))
                    
                if paramsDF.loc[i, "Upper Bound:"] < paramsDF.loc[i, "Initial Value:"]:
                    paramsDF.loc[i, "Upper Bound:"] = paramsDF.loc[i, "Initial Value:"]
                    sig_infeasible_x0.emit(str(i))
            
            if refresh:
                if isinstance(self._parameters_, pd.DataFrame) and self._parameters_.shape == paramsDF.shape and np.all(self._parameters_index == paramsDF.index):
                    if self.isVertical:
                        pDF = paramsDF
                    else:
                        pDF = paramsDF.T
                        
                    for c in pDF.columns:
                        for r in pDF.index:
                            self.getSpinBox(r, c).setValue(pDF.loc[r,c])
                            
                else:
                    self._parameters_ = paramsDF
                    self._clear_widgets()
                    self._generate_widgets()
                        
                        
                
            return paramsDF
        
    
    @property
    def spinDecimals(self):
        return self._spinDecimals_
    
    @spinDecimals.setter
    def spinDecimals(self, value:int):
        self._spinDecimals_ = int(value)
        
    @property
    def spinStep(self):
        return self._spinStep_
    
    @spinStep.setter
    def spinStep(self, value:float):
        self._spinStep_ = float(value)
    
    @pyqtSlot(float)
    def _slot_newvalue(self, value):
        widget = self.sender()
        if self.isVertical: # FIXME/TODO/BUG
            paramsDF = self._parameters_
        else:
            paramsDF = self._parameters_.T
            
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            index = self.widgetsLayout.indexOf(widget)
            if index == -1: # this should never happen
                return

            layout_col = index // self.widgetsLayout.rowCount()
            layout_row = index % self.widgetsLayout.rowCount()
            
            param_col = self._parameters_.columns[layout_col-1]
            param_row = self._parameters_.index[layout_row-1]

            old_val = self._parameters_.iloc[layout_row-1, layout_col-1]
            
            if isinstance(old_val, pq.Quantity):
                new_val = value * old_val.units
            else:
                new_val = value
                
            if param_col == "Lower Bound:":
                init_val = self._parameters_.loc[param_row, "Initial Value:"]
                upper_val = self._parameters_.loc[param_row, "Upper Bound:"]
                
                if new_val > init_val:
                    # self.sig_badBounds.emit(str(param_row))
                    new_val = init_val
                    
                if new_val > upper_val:
                    # self.sig_badBounds.emit(str(param_row))
                    new_val = upper_val
                    
            elif param_col == "Upper Bound:":
                init_val = self._parameters_.loc[param_row, "Initial Value:"]
                lower_val = self._parameters_.loc[param_row, "Lower Bound:"]
                
                if new_val < init_val:
                    # self.sig_badBounds.emit(str(param_row))
                    new_val = init_val
                    
                if new_val < lower_val:
                    # self.sig_badBounds.emit(str(param_row))
                    new_val = upper_val
                    
            elif param_col == "Initial Value:":
                lower_val = self._parameters_.loc[param_row, "Lower Bound:"]
                upper_val = self._parameters_.loc[param_row, "Upper Bound:"]
                if new_val < lower_val:
                    # adjust lower bound:
                    lower_val = new_val
                    sb = self.getSpinBox(str(param_row), "Lower Bound:")
                    signalBlocker = QtCore.QSignalBlocker(sb)
                    sb.setMinimum(lower_val)
                    self._parameters_.loc[param_row, "Lower Bound:"] = lower_val
                    
                if new_val > upper_val:
                    # adjust lower bound:
                    upper_val = new_val
                    sb = self.getSpinBox(str(param_row), "Upper Bound:")
                    signalBlocker = QtCore.QSignalBlocker(sb)
                    sb.setMaximum(upper_val)
                    self._parameters_.loc[param_row, "Upper Bound:"] = upper_val
                    
            if new_val != value:
                sb = self.getSpinBox(str(param_row), str(param_col))
                signalBlocker = QtCore.QSignalBlocker(sb)
                sb.setValue(new_val)
                
            self._parameters_.iloc[layout_row-1, layout_col-1] = new_val
                    
            # if isinstance(old_val, pq.Quantity):
            #     self._parameters_.iloc[layout_row-1, layout_col-1] = value * old_val.units
            # else:
            #     self._parameters_.iloc[layout_row-1, layout_col-1] = value
                
            self.sig_dataChanged.emit()
            self.sig_parameterChanged.emit(self._parameters_.index[layout_row-1], 
                                           self._parameters_.columns[layout_col-1])
            
    def validate(self):
        """ Always returns True.
        This method is present so that ModelParametersWidget instances can be
        embedded in QuickDialog (which expects widgets with a `validate` method)
        """
        return True
    
    def value(self):
        return self.parameters
    
    def getParameterValue(self, parameter_name:str, what:str):
        return self.parameters.loc[parameter_name, what]
