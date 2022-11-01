"""Widgets for parameter inputs
"""
import math, numbers, typing, os
import pandas as pd
import quantities as pq
from core.strutils import str2symbol
from . import guiutils
import gui.quickdialog as qd

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
    def __init__(self, parameters:typing.Sequence, parameterNames:typing.Optional[typing.Sequence]=None, spinStep:typing.Optional[float]=None, spinDecimals:typing.Optional[int]=None, lower:typing.Optional[typing.Sequence]=None, upper:typing.Optional[typing.Sequence]=None, orientation:str ="vertical", parent:QtWidgets.QWidget=None):
        """ Constructor of ModelParametersWidget.
    
            Positional parameters:
            ======================
            parameters: sequence (tuple, list, 1D array-like) with the initial
                        values for the fit model
    
            parameterNames: None (default) or a sequence of str with the names 
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
        
        if all(isinstance(p, pq.Quantity) for p in parameters):
            units = [p.units for p in parameters]
        else:
            units = []
            
        
        if parameterNames is None:
            parameterNames  = [f"parameter_{k}" for k in range(len(parameters))]
            
        elif isinstance(parameterNames, (tuple,list)):
            if not all(isinstance(s, str) for s in parameterNames):
                raise TypeError("Expecting strings for parameter names")
            
            if any(len(s.strip()) == 0 for s in parameterNames):
                raise TypeError("Cannot accept empty string for parameter names")
            
            if len(parameterNames) != len(parameters):
                raise ValueError(f"When a sequence, parameterNames must have the same number of elements as parameters {len(parameters)}; instead, got {parameterNames}")
            
        else:
            raise TypeError(f"'parameterNames' must be a sequence or None; instead, got {parameterNames}")
                
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
        
        self._spinDecimals_ = spinDecimals
        self._spinStep_ = spinStep
        
        spinD, spinS = guiutils.get_QDoubleSpinBox_params(parameters + lower) 
        
        if self._spinDecimals_ is None:
            self._spinDecimals_ = spinD
            
        if self._spinStep_ is None:
            self._spinStep_ = spinS
            
        self._spin_min_ = -math.inf
        self._spin_max_ =  math.inf
        
        if orientation.lower() == "horizontal":
            self._verticalLayout_ = False
        else:
            self._verticalLayout_ = True
            
        self._parameters_ = pd.DataFrame({"Initial Value:": parameters,
                                          "Lower Bound:":lower,
                                          "Upper Bound:":upper},
                                        index = parameterNames)
        
        if not self._verticalLayout_:
            self._parameters_ = self._parameters_.T
        
        self._configureUI_()
        
    def _configureUI_(self):
        if not self.objectName():
            self.setObjectName("ModelParametersWidget")
        
        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setObjectName(u"gridLayout")
        self.widgetsLayout = QtWidgets.QGridLayout()
        self.widgetsLayout.setObjectName(u"widgetsLayout")
        
        header = ["Parameters:"] + [c for c in self._parameters_.columns]
        
        minSpinWidth = list()
        spinBoxes = list()

        for layout_col, c in enumerate(header):   
            # NOTE: 2022-10-31 09:31:48
            # top row is the header → the first widget in ANY column is a QLabel
            w = QtWidgets.QLabel(c, self)
            w.setObjectName(f"label_{str2symbol(c)}_header")

            self.widgetsLayout.addWidget(w, 0, layout_col, 1, 1)

            for ki, i in enumerate(self._parameters_.index): # row index into the DataFrame
                layout_row = ki + 1

                if layout_col == 0:
                    w = QtWidgets.QLabel(i, self)
                    w.setObjectName(f"label_{str2symbol(i)}")
                    
                else:
                    p = self._parameters_.loc[i,c]
                    w = QtWidgets.QDoubleSpinBox(self)
                    w.setMinimum(-math.inf)
                    w.setMaximum(math.inf)
                    
                    # TODO/FIXME2022-10-30 21:10:14
                    # if self._verticalLayout_:
                    #     if c not in (["Lower Bound:", "Upper Bound:"]):
                    #         lo = self._parameters_.loc[i, "Lower Bound:"]
                    #         up = self._parameters_.loc[i, "Upper Bound:"]
                    #     else:
                    #         lo = -math.inf
                    #         up = math.inf
                    # else:
                    #     if i not in (["Lower Bound:", "Upper Bound:"]):
                    #         lo = self._parameters_.loc["Lower Bound:", c]
                    #         up = self._parameters_.loc["Upper Bound:", c]
                    #     else:
                    #         lo = -math.inf
                    #         up = math.inf
                    # w.setMinimum(max(-math.inf, lo))
                    # w.setMaximum(min(math.inf, up))
                    
                    w.setDecimals(self.spinDecimals)
                    w.setSingleStep(self.spinStep)
                    w.valueChanged[float].connect(self._slot_newvalue)
                    w.setAccelerated(True)
                    
                    if isinstance(p, pq.Quantity):
                        w.setValue(p.magnitude)
                        
                        if p.units != pq.dimensionless:
                            w.setSuffix(f" {p.units.dimensionality}")
                        else:
                            w.setSuffix(" ")
                            
                    else:
                        w.setValue(p)
                        w.setSuffix(" ")
                            
                    t = w.text()
                    minSpinWidth.append(guiutils.get_text_width(t))
                    # print(f"minWidth {minWidth}")
                    # w.setMinimumWidth(minWidth)
                    w.setObjectName(f"{str2symbol(i)}_{str2symbol(c)}_spinBox")
                    spinBoxes.append(w)
                    
                    # TODO/FIXME - MAYBE
                    # if self._verticalLayout_:
                    #     if c == "Lower Bound:":
                    #         w.valueChanged.connect(self._slot_setSpinMinimum)
                    #     elif c == "Upper Bound:":
                    #         w.valueChanged.connect(self._slot_setSpinMaximum)
                    # else:
                    #     if i == "Lower Bound:":
                    #         w.valueChanged.connect(self._slot_setSpinMinimum)
                    #     elif i == "Upper Bound:":
                    #         w.valueChanged.connect(self._slot_setSpinMaximum)
                    
                self.widgetsLayout.addWidget(w, layout_row, layout_col, 1, 1)
        
        self.gridLayout.addLayout(self.widgetsLayout, 0, 0, 1, 1)
        
        sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sp.setHorizontalStretch(1)
        sp.setVerticalStretch(0)
        minWidth = max(minSpinWidth)
        for w in spinBoxes:
            w.setMinimumWidth(minWidth + 3*minWidth//10)
            w.setSizePolicy(sp)
            
        
    @property
    def widgets(self):
        return self._widgets_
    
    @property
    def parameters(self):
        return self._parameters_
    
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
        # print(f"ModelParametersWidget._slot_newvalue value {value}")
        widget = self.sender()
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            index = self.widgetsLayout.indexOf(widget)
            if index == -1: # this should never happen
                return
            
            # NOTE: 2022-10-30 08:36:35
            # linear indexing in the grid layout → column varies faster
            # 
            # Furthermore:
            # self.widgetsLayout.rowCount()      → self._parameters_.shape[0] + 1
            # self.widgetsLayout.columnCount()   → self._parameters_.shape[1] + 1 
            #
            
            layout_col = index // self.widgetsLayout.rowCount()
            layout_row = index % self.widgetsLayout.rowCount()

            # print(f"ModelParametersWidget._slot_newvalue widget {widget} value {value} index {index}, layout row {layout_row}, layout col {layout_col}")
            
            old_val = self._parameters_.iloc[layout_row-1, layout_col-1]
            if isinstance(old_val, pq.Quantity):
                self._parameters_.iloc[layout_row-1, layout_col-1] = value * old_val.units
            else:
                self._parameters_.iloc[layout_row-1, layout_col-1] = value
            
    @pyqtSlot(float)
    def _slot_setSpinMaximum(self, value:float):
        # TODO/FIXME 2022-10-30 21:09:27
        w = self.sender()
        if isinstance(w, QtWidgets.QDoubleSpinBox):
            index = self.widgetsLayout.indexOf(w)
            if index == -1:
                return
            
            col = index // self.widgetsLayout.rowCount()
            row = index % self.widgetsLayout.owCount()
            
            if self._verticalLayout_:
                target = self.widgetsLayout.itemAtPosition(row, 1).widget()
            else:
                target = self.widgetsLayout.itemAtPosition(1, col).widget()
                
            # print(target.value())
            
            if isinstance(target, QtWidgets.QDoubleSpinBox):
                target.setMinimum(value)
        
    @pyqtSlot(float)
    def _slot_setSpinMinimum(self, value:float):
        # TODO/FIXME 2022-10-30 21:09:27
        w = self.sender()
        if isinstance(w, QtWidgets.QDoubleSpinBox):
            index = self.widgetsLayout.indexOf(w)
            if index == -1:
                return
            
            col = index // self.widgetsLayout.rowCount()
            row = index % self.widgetsLayout.rowCount()
            
            if self._verticalLayout_:
                target = self.widgetsLayout.itemAtPosition(row, 1).widget()
            else:
                target = self.widgetsLayout.itemAtPosition(1, col).widget()
                
            if isinstance(target, QtWidgets.QDoubleSpinBox):
                target.setMaximum(value)
            
            
    def validate(self):
        """ Always returns True.
        This method is present so that ModelParametersWidget instances can be
        embedded in QuickDialog (which expects widgets with a `validate` method)
        """
        return True
    
    def getParameterValue(self, parameter_name:str, what:str):
        return self.parameters.loc[parameter_name, what]

class ModelFittingDialog(qd.QuickDialog):
    # TODO 2022-10-30 22:07:42
    def __init__(self, parameters:typing.Sequence, parameterNames:typing.Optional[typing.Sequence]=None, lower:typing.Optional[typing.Sequence]=None, upper:typing.Optional[typing.Sequence]=None, orientation:str ="vertical"):
        pass
