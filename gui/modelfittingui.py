"""Widgets for parameter inputs
"""
import math, numbers, typing
import pandas as pd
from . import guiutils
import gui.quickdialog as qd

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType

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
        
        if parameterNames is None:
            parameterNames  = [f"parameter_{k}" for k in range(len(parameters))]
            
        elif isinstance(parameterNames, (tuple,list)):
            if not all(isinstance(s, str) for s in parameterNames):
                raise TypeError("Expecting strings for parameter names")
            
            if any(len(s.strip()) == 0 for s in parameterNames):
                raise TypeError("Cannot accept empty string for parameter names")
            
            if len(parameterNames) != len(parameters):
                raise ValueError(f"When a sequence, parameterNames must have the same number of elements as parameters {len(parameters)}; got {len(parameterNames)} instead")
            
        else:
            raise TypeError(f"'parameterNames' must be a sequence or None; got {type(parameterNames).__name__} instead")
                
        if isinstance(lower, numbers.Number):
            lower = [lower] * len(parameters)
            
        elif isinstance(lower, (tuple, list)):
            if len(lower) != len(parameters):
                raise TypeError(f"'lower' expected to be a sequence of {len(parameters)} elements")
            
            if not all(isinstance(v, numbers.Number) for v in lower):
                raise TypeError(f"'lower' expected to contain numbers")
            
        else:
            raise TypeError(f"'lower' expected to be a scalar or a sequence of {len(parameters)} elements")
        
        if isinstance(upper, numbers.Number):
            upper = [upper] * len(parameters)
            
        elif isinstance(upper, (tuple, list)):
            if len(upper) != len(parameters):
                raise TypeError(f"'upper' expected to be a sequence of {len(parameters)} elements")
            
            if not all(isinstance(v, numbers.Number) for v in upper):
                raise TypeError(f"'upper' expected to contain numbers")
            
        else:
            raise TypeError(f"'upper' expected to be a scalar or a sequence of {len(parameters)} elements")
        
        self._spinDecimals_ = spinDecimals
        self._spinStep_ = spinStep
        
        spinD, spinS = guiutils.get_QDoubleSpinBox_params(parameters + lower) 
        
        # print(f"spinS {spinS}, spinD {spinD}")
        
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
        
        self.setLayout(QtWidgets.QGridLayout(self))
        
        self._configureUI_()
        
    def _configureUI_(self):
        header = ["Parameters:"] + [c for c in self._parameters_.columns]
        for layout_col, c in enumerate(header):    
            w = QtWidgets.QLabel(c, self)
            # w.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            sp.setHorizontalStretch(3)
            sp.setVerticalStretch(0)
            sp.setHeightForWidth(w.sizePolicy().hasHeightForWidth())
            w.setSizePolicy(sp)
            self.layout().addWidget(w, 0, layout_col, QtCore.Qt.AlignHCenter)

            for ki, i in enumerate(self._parameters_.index): # row index into the DataFrame
                layout_row = ki + 1

                if layout_col == 0:
                    w = QtWidgets.QLabel(i, self)
                    
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
                    w.setValue(p)
                    w.valueChanged.connect(self._slot_newvalue)
                    w.setAccelerated(True)
                    # w.setGroupSeparator(True)
                    w.setSuffix(" ")
                    # TODO/FIXME
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
                    
                sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                sp.setHorizontalStretch(0)
                sp.setVerticalStretch(0)
                sp.setHeightForWidth(w.sizePolicy().hasHeightForWidth())
                w.setSizePolicy(sp)
                # w.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                # w.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
                self.layout().addWidget(w, layout_row, layout_col, QtCore.Qt.AlignLeft)
                
        # for c in range(self.layout().columnCount()):
        #     if c > 0:
        #         self.layout().setColumnStretch(c, 1)
                
        # self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
                    
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
        widget = self.sender()
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            index = self.layout().indexOf(widget)
            if index == -1: # this should never happen
                return
            
            # NOTE: 2022-10-30 08:36:35
            # linear indexing in the grid layout → column varies faster
            # 
            # Furthermore:
            # self.layout().rowCount()      → self._parameters_.shape[0] + 1
            # self.layout().columnCount()   → self._parameters_.shape[1] + 1 
            #
            
            layout_col = index // self.layout().rowCount()
            layout_row = index % self.layout().rowCount()

            # print(f"ModelParametersWidget._slot_newvalue widget {widget} value {value} index {index}, layout row {layout_row}, layout col {layout_col}")
            
            self._parameters_.iloc[layout_row-1, layout_col-1] = value
            
    @pyqtSlot(float)
    def _slot_setSpinMaximum(self, value:float):
        # TODO/FIXME 2022-10-30 21:09:27
        w = self.sender()
        if isinstance(w, QtWidgets.QDoubleSpinBox):
            index = self.layout().indexOf(w)
            if index == -1:
                return
            
            col = index // self.layout().rowCount()
            row = index % self.layout().rowCount()
            
            if self._verticalLayout_:
                target = self.layout().itemAtPosition(row, 1).widget()
            else:
                target = self.layout().itemAtPosition(1, col).widget()
                
            # print(target.value())
            
            if isinstance(target, QtWidgets.QDoubleSpinBox):
                target.setMinimum(value)
        
    @pyqtSlot(float)
    def _slot_setSpinMinimum(self, value:float):
        # TODO/FIXME 2022-10-30 21:09:27
        w = self.sender()
        if isinstance(w, QtWidgets.QDoubleSpinBox):
            index = self.layout().indexOf(w)
            if index == -1:
                return
            
            col = index // self.layout().rowCount()
            row = index % self.layout().rowCount()
            
            if self._verticalLayout_:
                target = self.layout().itemAtPosition(row, 1).widget()
            else:
                target = self.layout().itemAtPosition(1, col).widget()
                
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
