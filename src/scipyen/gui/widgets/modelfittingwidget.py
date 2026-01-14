# -*- coding: utf-8 -*-
# $Id: modelfittingwidget.py $
# SPDX-FileCopyrightText: 2022 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Widget for model parameter inputs
"""
import math, numbers, typing, os, types, sys, traceback
import numpy as np
import quantities as pq
import pandas as pd
import neo
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
from gui import guiutils, workspacegui
import gui.quickdialog as qd
from gui.widgets.small_widgets import QuantitySpinBox

__module_path__ = os.path.abspath(os.path.dirname(__file__))
Ui_ModelFittingWidget, QWidget = loadUiType(os.path.join(__module_path__, "ModelFittingWidget.ui"))

class ModelFittingWidget(Ui_ModelFittingWidget, QWidget, workspacegui.GuiMessages):
    sig_waveformReady = Signal(object, name="sig_waveformReady")
    def __init__(self, model: types.FunctionType,
                 coefficients:typing.Optional[typing.Union[pd.DataFrame, dict]] = None,
                 waveformUnits:typing.Optional[pq.Quantity]=None,
                 parent=None):
        r"""
Parameters:
===========

:model: a model function — a Python function decorated with the ``modelfunction`` decorator (see core.models)

    This function supplies a ``title`` for the mathematical model and a coefficients table containing coefficient names, their initial values and lower & upper bounds for curve fitting using the model function

Named Parameters:
=================
:coefficients: Optional, default is None

    * a pandas DataFrame with the following mandatory structure:
        * :index: model parameter symbols (strings)
        * :columns: 'Initial Value', 'Lower Bound', 'Upper Bound', 'Keep Feasible';

            The first three columns contain scalar floats or scalar python Quantity objects
            with the initial, lower and upper bound values for the corresponding model
            parameter in the respective row.
            The fourth column contains bool values.

    * a dictionary with the following mapping (all keys are str):
        :names:     ↦ sequence of coefficient names
        :intial:    ↦ sequence of scalars (initialcoefficient values for curve fitting)
        :lower:     ↦ sequence of scalars (lower bounds for curve fitting)
        :upper:     ↦ sequence of scalars (uppr bounds for curve fitting)

    .. attention::
        When given, it can be used to override the coefficents table extracted from the ``model`` parameter, provided it has a compatible structure (i.e. same number and names of coefficients)

            
"""
        QWidget.__init__(self, parent=parent)
        
        self._model_coefficients_:typing.Optional[pd.DataFrame] = None
        self._model_name_:typing.Optional[str] = None
        self._waveformDuration_:pq.Quantity = 1*pq.s
        self._waveformSamplingRate_:pq.Quantity = 1e4 * 1/self._waveformDuration_.units
        self._waveformUnits_:typing.Optional[pq.Quantity] = waveformUnits
        
        durationFamily = scq.getUnitFamily(self._waveformDuration_)
        if durationFamily == "Time":
            self._waveformSamplingRate_.rescale(pq.Hz)
        elif durationFamily in ("Length", "Space"):
            self._waveformSamplingRate_.rescale(pq.space_frequency_unit)
        elif durationFamily == "Angle" or self._waveformDuration_.units == pq.rad:
            self._waveformSamplingRate_.rescale(pq.angle_frequency_unit)
            
        
        if models.isModelFunction(model):
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
            # fitting_dict["Keep Feasible"] = [True] * len(coefficients)

            self._model_coefficients_ = pd.DataFrame(fitting_dict, index=coefficients)
            self._model_name_ = model.title

        else:
            raise ValueError(f"Expecting a model function; instead, got {model}")
            
        if isinstance(coefficients, pd.DataFrame):
            # NOTE: 2026-01-13 23:26:42
            # override coefficients given by model only if the indexes are the same
            if isinstance(self._model_coefficients_, pd.DataFrame):
                assert coefficients.size == self._model_coefficients_.size, "Incompatible coefficients data were supplied"
                assert all(c in coefficients.index for c in self._model_.coefficients) and all(c in self._model_.coefficients for c in coefficients), "Incompatible coefficients data were supplied"
            self._model_coefficients_ = coefficients
            
        elif isinstance(coefficients, dict):
            assert models.isFittingCoefficientsDict(coefficients), "Incompatible coefficients data supplied"
            fitting_dict["Initial Value"] = coefficients["initial"]
            fitting_dict["Lower Bound"] = coefficients["lower"]
            fitting_dict["Upper Bound"] = coefficients["upper"]
            fitting_dict["Upper Bound"] = coefficients["feasible"]
            # fitting_dict["Keep Feasible"] = [True] * len(coefficients["names"])
            if isinstance(self._model_coefficients_, pd.DataFrame):
                assert len(coefficients["names"]) == self._model_coefficients_.shape[0], "Incompatible coefficients data supplied"
                assert set(coefficients["names"]) == set(self._model_coefficients_.index), "Incompatible coefficients data supplied"
            self._model_coefficients_ = pd.DataFrame(fitting_dict, index=coefficients["names"])
            
        self._configureUI_()
        
        if isinstance(self._model_coefficients_, pd.DataFrame):
            self.setModelData(self._model_coefficients_)

        self.modelExpressionLabel.setScaledContents(True)
        self.exprPix = models.renderModelExpression(self._model_.expression)
        self.resizeEvent(None)

        if isinstance(self.exprPix, QtGui.QPixmap):
            scaledPix = self._rescaleExprPix_()
            self.modelExpressionLabel.setPixmap(scaledPix)

    def resizeEvent(self, evt:QtGui.QResizeEvent):
        if isinstance(self.exprPix, QtGui.QPixmap) and not self.exprPix.isNull() and self.modelExpressionLabel.size().isValid():
            scaledPix = self._rescaleExprPix_()
            self.modelExpressionLabel.setPixmap(scaledPix)



    def _rescaleExprPix_(self) -> QtGui.QPixmap:
        return self.exprPix.scaled(self.modelExpressionLabel.size(),
                                    QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)



    def _configureUI_(self):
        self.setupUi(self)
        if isinstance(self._model_name_, str) and len(self._model_name_.strip()):
            self.modelNameLabel.setText(self._model_name_)
        else:
            self.modelNameLabel.setText("")

        self.modelCoefficientsTable.sig_dataChanged.connect(self._slot_modelCoefficientsChanged)
        self.makeUnitAmplitudePushButton.clicked.connect(self._slot_makeUnitAmplitudeModel)
        self.durationSpinBox.setValue(self._waveformDuration_)
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
        self.durationSpinBox.sig_valueChanged.connect(self._slot_waveformDurationChanged)
        self.samplingRateSpinBox.sig_valueChanged.connect(self._slot_waveformSamplingRateChanged)
        # self.modelCoefficientsTable.spinStep = 1e-4
        # self.modelCoefficientsTable.spinDecimals = 4

        # self.modelCoefficientsTable.sig_parameterChanged[str, str].connect(self._slot_modelCoefficientsChanged)
        # self.modelCoefficientsTable.sig_badBounds[str].connect(self._slot_badBounds)
        # self.modelCoefficientsTable.sig_infeasible_x0[str].connect(self._slot_infeasible_x0s)
        # self.setMinimumSize(self.modelCoefficientsTable.tableView.viewportSizeHint())
        
        self.generateWaveformPushButton.clicked.connect(self._slot_generateWaveform)

    def setModelData(self, data:typing.Optional[pd.DataFrame]=None):
        if isinstance(data, pd.DataFrame):
            assert all(v in data.columns for v in ('Initial Value', 'Lower Bound', 'Upper Bound', 'Keep Feasible')), "Not a model parameters data frame"
            self._model_coefficients_ = data
            
        if isinstance(self._model_coefficients_, pd.DataFrame):
            self.modelCoefficientsTable.setData(self._model_coefficients_)
            # self.setMinimumSize(self.modelCoefficientsTable.tableView.viewportSizeHint())

    def _calculateWaveformSamples(self) -> int:
        assert(scq.unitsConvertible(1/self._waveformSamplingRate_, self._waveformDuration_)), f"Waveform duration ({self._waveformDuration_}) and sampling rate ({self._waveformSamplingRate_}) have incompatible units"
        return int(self._waveformDuration_ * self._waveformSamplingRate_.simplified.magnitude)
    
    def _generateWaveformDomain_(self) -> np.ndarray:
        t_start = 0* self._waveformDuration_.units
        return np.linspace(t_start.magnitude, self._waveformDuration_.magnitude, self._calculateWaveformSamples())
        
    @Slot()
    def _slot_modelCoefficientsChanged(self):
        pass
    
    @Slot()
    def _slot_generateWaveform(self):
        # print(f"{self.__class__.__name__}._slot_generateWaveform")
        from core import datasignal
        from gui.guiutils import getScipyenMainWindow
        if not isinstance(self._model_, types.FunctionType) or not models.isModelFunction(self._model_):
            return

        try:
            x = self._generateWaveformDomain_()

            coeffs = list(self._model_coefficients_["Initial Value"])
            y = self._model_(x, coeffs)
            sigUnits = self._waveformUnits_.units if isinstance(self._waveformUnits_, pq.Quantity) else pq.dimensionless
            if scq.checkTimeUnits(self._waveformDuration_):
                sig = neo.AnalogSignal(y, t_start = 0*self._waveformDuration_.units, units = sigUnits, sampling_rate=self._waveformSamplingRate_, name=self._model_name_)
            else:
                sig = datasignal.DataSignal(y, t_start = 0*self._waveformDuration_.units, units = sigUnits, domain_units = self._waveformDuration_.units,
                                        sampling_rate=self._waveformSamplingRate_, name=self._model_name_)

        except:
            exc = sys.exception()
            msg = "".join(traceback.format_exception_only(exc))
            self.errorMessage(type(exc).__name__, msg)
            return

        self.sig_waveformReady.emit(sig)

        if self.receivers(self.sig_waveformReady) == 0:
            varname = f"{self._model_name_}_waveform" if isinstance(self._model_name_, str) and len(self._model_name_.strip()) else "model_waveform"
            getScipyenMainWindow().assignToWorkspace(varname, sig)


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
        
    @property
    def waveformUnits(self) -> pq.Quantity | None:
        return self._waveformUnits_

    @waveformUnits.setter
    def waveformUnits(self, val:typing.Optional[pq.Quantity]):
        if not isinstance(val, pq.Quantity):
            self._waveformUnits_ = None
        else:
            self._waveformUnits_ = val.units
