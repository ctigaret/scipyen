# -*- coding: utf-8 -*-
# $Id: modelfittingwidget.py $
# SPDX-FileCopyrightText: 2022 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Widget for model parameter inputs
"""
import math, numbers, typing, os, types
import numpy as np
import quantities as pq
import pandas as pd
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
    
from core.strutils import str2symbol
from core import models
from gui import guiutils
import gui.quickdialog as qd
from gui.widgets.small_widgets import QuantitySpinBox

__module_path__ = os.path.abspath(os.path.dirname(__file__))
Ui_ModelFittingWidget, QWidget = loadUiType(os.path.join(__module_path__, "ModelFittingWidget.ui"))

class ModelFittingWidget(Ui_ModelFittingWidget, QWidget):
    def __init__(self, model: typing.Optional[typing.Union[pd.DataFrame, types.FunctionType]]=None,
                 moodelName:typing.Optional[str]=None,
                 parent=None):
        r"""
Parameters:
===========

:model: one of
    * a pandas DataFrame with the following mandatory structure:
        * index: model parameter symbols (strings)
        * columns: 'Initial Value', 'Lower Bound', 'Upper Bound', 'Keep Feasible';
            The first three columns contain scalar floats or scalar python Quantity objects
            with the initial, lower and upper bound values for the corresponding model
            parameter in the respective row.
            The fourth column contains bool values.
    * a model function — a Python function decorated with the ``modelfunction`` decorator (see core.models)

    Optional, default is None

:modelName: str or None;

    .. note::
        When *model* is a model function (see above) model name is taken from the ``title`` attribute of the model function
            
"""
        QWidget.__init__(self, parent=parent)
        
        self._data_:typing.Optional[pd.DataFrame] = None
        self._model_name_:typing.Optional[str] = None
        
        if isinstance(model, pd.DataFrame):
            assert all(v in model.columns for v in ('Initial Value', 'Lower Bound', 'Upper Bound', 'Keep Feasible')), "Not a model parameters data frame"
            self._data_ = model
            
        elif models.is_modelfunction(model):
            fitting_dict = dict()
            coefficients = model.coefficients
            if model.fitting:
                fitting_dict["Initial Value"] = model.fitting["initial"]
                fitting_dict["Lower Bound"] = model.fitting["lower"]
                fitting_dict["Upper Bound"] = model.fitting["upper"]
            else:
                fitting_dict = {'Initial Value': [0.] * len(coefficients), 'Lower Bound': [-np.inf] * len(coefficients), "Upper Bound": [np.inf] * len(coefficients)}
            fitting_dict["Keep Feasible"] = [True] * len(coefficients)

            self._data_ = pd.DataFrame(fitting_dict, index=coefficients)
            self._model_name_ = model.title

        elif isinstance(model, dict):
            assert models.isFittingCoefficientsDict(model), "'model' is Not a fitting coefficient mapping"
            fitting_dict["Initial Value"] = model["initial"]
            fitting_dict["Lower Bound"] = model["lower"]
            fitting_dict["Upper Bound"] = model["upper"]
            fitting_dict["Keep Feasible"] = [True] * len(fitting_dict["Initial Value"])
            self._data_ = pd.DataFrame(fitting_dict, index=coefficients)

        if not isinstance(self._model_name_, str) or len(self._model_name_.strip()) == 0:
            if isinstance(modelName, str) and len(modelName.strip()):
                self._model_name_ = modelName

        self._configureUI_()
        
        if isinstance(self._data_, pd.DataFrame):
            self.setModelData(self._data_)

    def _configureUI_(self):
        self.setupUi(self)
        if isinstance(self._model_name_, str) and len(self._model_name_.strip()):
            self.modelNameLabel.setText(self._model_name_)
        else:
            self.modelNameLabel.setText("")

        self.modelCoefficientsTable.sig_dataChanged.connect(self._slot_modelParameterChanged)

        # self.modelCoefficientsTable.spinStep = 1e-4
        # self.modelCoefficientsTable.spinDecimals = 4

        # self.modelCoefficientsTable.sig_parameterChanged[str, str].connect(self._slot_modelParameterChanged)
        # self.modelCoefficientsTable.sig_badBounds[str].connect(self._slot_badBounds)
        # self.modelCoefficientsTable.sig_infeasible_x0[str].connect(self._slot_infeasible_x0s)
        self.setMinimumSize(self.modelCoefficientsTable.tableView.viewportSizeHint())


    @Slot()
    def _slot_modelParameterChanged(self):
        pass

    def setModelData(self, data:pd.DataFrame):
        self.modelCoefficientsTable.setData(self._data_)
        self.setMinimumSize(self.modelCoefficientsTable.tableView.viewportSizeHint())

