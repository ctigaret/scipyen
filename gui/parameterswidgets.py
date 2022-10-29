"""Widgets for parameter inputs
"""
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType

class ModelParametersWidget(QtWidgets.QWidget):
    """A widget composed of labels and spin boxes for input of numeric values
    The child widgets (input field and labels) are arranged in a grid.
    There is support for numerical scalar parameters only, used for model fitting.

    The numerical parameters values can be accessed from the actual input widgets
    (spin boxes) held in the read-only property `widgets` (a dict).

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
    def __init__(self, parameters:dict, parameterNames:list, spinStep:float, spinDecimals:int, orientation:str ="vertical", parent:QtWidgets.QWidget=None):
        """ Constructor of ModelParametersWidget.
    
            Positional parameters:
            ======================
            parameters: dict mapping str keys to sequences of numerical scalar 
                        values
                        
                        All sequences in the dict MUST HAVE THE SAME NUMBER OF 
                        ELEMENTS.
                        
                        Typically, the keys are as follows:
                        • "Initial value:"
                        • "Lower bound:"
                        • "Upper bound:"
    
                        but there is no prescription on their names.
    
            parameterNames: list of str with the names of the parameters
    
            spinStep:float; the step change for the spin boxes of the widget
            
            spinDecimals:int; the number of decimals for float representation in
                            the spin boxes of the widget.
    
            orientation:str, "vertical" or "horizontal" (case-insensitive), optional
                        Default is "vertical".
    
                        Sets the orientation of the input fields.
    
                        When "vertical", the keys of the `parameters` dictionary
                        appear as columns, and the corresponding values (i.e., 
                        initial value, lower & upper bounds, using the example
                        above) are arranged column-wise
        """
        super().__init__(self, parent=parent)
        if orientation.lower() == "horizontal":
            self._verticalLayout_ = False
        else:
            self._verticalLayout_ = True
            
        self._widgets_ = dict()
        
        params = dict()
        params["Parameters:"] = parameterNames
        params.update(parameters)
        
        self._parameters_ = pd.DataFrame(params)
        
        if not self._verticalLayout_:
            self._parameters_ = self._parameters_.T
        
        self.spinDecimals = spinDecimals
        self.spinStep = spinStep
        
        self.setLayout(QtWidgets.QGridLayout(self))
        
        self._configureUI_()
        
    def _configureUI_(self):
        if self._verticalLayout_:
            for kc, c in enumerate(self._parameters_.columns):    for kc, c in enumerate(self._parameters_.columns):
                w = QtWidgets.QLabel(c, self)
                self.layout().addWidget(w, 0, kc, QtCore.Qt.AlignHCenter)
                
                for ki, i in enumerate(self._parameters_.index):
                    if i not in self._widgets_.keys():
                        self._widgets_[i] = dict()
                        
                    p = self._parameters_.loc[i,c]
                    # print(kc, c, ki, i, p)
                    
                    if isinstance(p, str):
                        w = QtWidgets.QLabel(p, self)
                    else:
                        w = QtWidgets.QDoubleSpinBox(self)
                        w.setMinimum(-math.inf)
                        w.setMaximum(math.inf)
                        w.setDecimals(self.spinDecimals)
                        w.setSingleStep(self.spinStep)
                        w.setValue(p)
                        
                    if c != "Parameters:":
                        self._widgets_[i][c] = w
                    
                    self.layout().addWidget(w, ki+1, kc, QtCore.Qt.AlignLeft)
                    
        else:
            for ki, i in enumerate(self._parameters_.index):
                self.layout().addWidget(QtWidgets.QLabel(i, self), ki, 0, QtCore.Qt.AlignLeft)
                for kc, c in enumerate(self._parameters_.columns):
                    p = self._parameters_.loc[i,c]
                    # print(kc, c, ki, i, p)
                    if c not in self._widgets_.keys():
                        self._widgets_[c] = dict()
                    
                    if isinstance(p, str):
                        w = QtWidgets.QLabel(p, self)
                    else:
                        w = QtWidgets.QDoubleSpinBox(self)
                        w.setMinimum(-math.inf)
                        w.setMaximum(math.inf)
                        w.setDecimals(self.spinDecimals)
                        w.setSingleStep(self.spinStep)
                        w.setValue(p)
                        self._widgets_[c][i] = w
                        
                    self.layout().addWidget(w, ki, kc+1, QtCore.Qt.AlignLeft)
                    
    @property
    def widgets(self):
        return self._widgets_
    
    @property
    def parameters(self):
        return self._parameters_
    
    @pyqtSlot(float)
    def _slot_newvalue(self, value):
        widget = self.sender()
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            # index = self.layout().indexOf(widget)
            
            # perform reverse lookup of the widget location in self._widgets_
            
            for k in self._widgets_.keys():
                if widget in self._widgets_[k].values():
                    wkeys = [j for j in self._widgets_[k].keys() if self._widgets_[k] is widget]
                    if len(wkeys):
                        wkey = wkeys[0]
                        if self._verticalLayout_:
                            self._parameters_.loc[wkey, k] = widget.value()
                        else:
                            self._parameters_.loc[k, wkey] = widget.value()
            
            
            
        # pass
