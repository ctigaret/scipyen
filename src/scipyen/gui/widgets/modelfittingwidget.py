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
from core import scipyen_quantities as scq
from gui import guiutils
import gui.quickdialog as qd
from gui.widgets.small_widgets import QuantitySpinBox

__module_path__ = os.path.abspath(os.path.dirname(__file__))
Ui_ModelFittingWidget, QWidget = loadUiType(os.path.join(__module_path__, "ModelFittingWidget.ui"))

class ModelFittingWidget(Ui_ModelFittingWidget, QWidget):
    def __init__(self, model: typing.Optional[typing.Union[pd.DataFrame, types.FunctionType]]=None,
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

            
"""
        QWidget.__init__(self, parent=parent)
        
        self._data_:typing.Optional[pd.DataFrame] = None
        self._model_name_:typing.Optional[str] = None
        self._waveformDuration_:pq.Quantity = 1*pq.s
        self._waveformSamplingRate_:pq.Quantity = 1e4 * 1/self._waveformDuration_.units
        
        durationFamily = scq.getUnitFamily(self._waveformDuration_)
        if durationFamily == "Time":
            self._waveformSamplingRate_.rescale(pq.Hz)
        elif durationFamily in ("Length", "Space"):
            self._waveformSamplingRate_.rescale(pq.space_frequency_unit)
        elif durationFamily == "Angle" or self._waveformDuration_.units == pq.rad:
            self._waveformSamplingRate_.rescale(pq.angle_frequency_unit)
            
        
        if models.is_modelfunction(model):
            self._model_ = model
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
        self.makeUnitAmplitudePushButton.clicked.connect(self._slot_makeUnitAmplitudeModel)
        self.durationSpinBox.setValue(self._waveformDuration_)
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
        self.durationSpinBox.sig_valueChanged.connect(self._slot_waveformDurationChanged)
        self.samplingRateSpinBox.sig_valueChanged.connect(self._slot_waveformSamplingRateChanged)
        # self.modelCoefficientsTable.spinStep = 1e-4
        # self.modelCoefficientsTable.spinDecimals = 4

        # self.modelCoefficientsTable.sig_parameterChanged[str, str].connect(self._slot_modelParameterChanged)
        # self.modelCoefficientsTable.sig_badBounds[str].connect(self._slot_badBounds)
        # self.modelCoefficientsTable.sig_infeasible_x0[str].connect(self._slot_infeasible_x0s)
        # self.setMinimumSize(self.modelCoefficientsTable.tableView.viewportSizeHint())

    def setModelData(self, data:typing.Optional[pd.DataFrame]=None):
        if isinstance(data, pd.DataFrame):
            assert all(v in data.columns for v in ('Initial Value', 'Lower Bound', 'Upper Bound', 'Keep Feasible')), "Not a model parameters data frame"
            self._data_ = data
            
        if isinstance(self._data_, pd.DataFrame):
            self.modelCoefficientsTable.setData(self._data_)
            # self.setMinimumSize(self.modelCoefficientsTable.tableView.viewportSizeHint())

    def _calculateWaveformSamples(self) -> int:
        assert(scq.unitsConvertible(1/self._waveformSamplingRate_, self._waveformDuration_)), f"Waveform duration ({self._waveformDuration_}) and sampling rate ({self._waveformSamplingRate_}) have incompatible units"
        return int(self._waveformDuration_ * self._waveformSamplingRate_).simplified.magnitude
    
    def _generateWaveformDomain_(self) -> np.ndarray:
        t_start = 0* self._waveformDuration_.units
        return np.linspace(t_start.magnitude, self._waveformDuration_.magnitude, self._calculateWaveformSamples())
        
    def _generateWaveform_(self) -> np.ndarray:
        return self._model_(self._generateWaveformDomain_(), self._data_["Initial Values"])
        
    @Slot()
    def _slot_modelParameterChanged(self):
        pass


    @Slot()
    def _slot_makeUnitAmplitudeModel(self):
        pass
    
    @Slot(object)
    def _slot_waveformDurationChanged(self, val:typing.Union[pq.Quantity, float, int, np.float64, np.int64]):
        duration = self._waveformDuration_
        
        if isinstance(val, pq.Quantity):
            assert(val.size == 1), "Expecting a scalar Quantity"
            duration = val
            
        elif isinstance(val, (float, np.float64, int, np.int64)):
            duration = val * self._waveformDuration_.units
            
        else:
            raise TypeError(f"Wrong value type ({type(val).__name__})")
        
        rate = self._waveformSamplingRate_
        
        if scq.unitsConvertible(1/self._waveformSamplingRate_, duration):
            if duration.units != 1/self._waveformSamplingRate_:
                rate = self._waveformSamplingRate_.rescale(1/duration.units)
            # else:
            #     rate = self._waveformSamplingRate_ * 1/duration.units
                
        else:
            rate = self._waveformSamplingRate_.magnitude / duration.units
            
        self._waveformDuration_ = duration
            
        if rate != self._waveformSamplingRate_:
            self._waveformSamplingRate_ = rate
            signalBlocker = QtCore.QSignalBlocker(self.samplingRateSpinBox)
            self.samplingRateSpinBox.setValue(rate)
            
    
    @Slot(object)
    def _slot_waveformSamplingRateChanged(self, val:typing.Union[pq.Quantity, float, int, np.float64, np.int64]):
        rate = self._waveformSamplingRate_
        
        if isinstance(val, pq.Quantity):
            assert(val.size == 1), "Expecting a scalar Quantity"
            rate = val
            
        elif isinstance(val, (float, np.float64, int, np.int64)):
            rate = val * self._waveformSamplingRate_.units
            
        else:
            raise TypeError(f"Wrong value type ({type(val).__name__})")
        
        duration = self._waveformDuration_
            
        if not scq.unitsConvertible(1/rate, self._waveformDuration_):
            if self._waveformDuration_.units != 1/rate.units:
                duration = self._waveformDuration_.rescale(1/rate.units)
        else:
            duration = self._waveformDuration_.magnitude  / rate.units
            
        self._waveformSamplingRate_ = rate
        
        if duration != self._waveformDuration_:
            self._waveformDuration_ = duration
            signalBlocker = QtCore.QSignalBlocker(self.durationSpinBox)
            self.durationSpinBox.setValue(duration)
        
