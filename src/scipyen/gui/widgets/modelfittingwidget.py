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
    
from core.strutils import (str2symbol, is_svg, str2svg)
from core import models
from core import scipyen_quantities as scq
from gui import guiutils, workspacegui
import gui.quickdialog as qd
from gui.widgets.small_widgets import QuantitySpinBox

__module_path__ = os.path.abspath(os.path.dirname(__file__))
Ui_ModelFittingWidget, QWidget = loadUiType(os.path.join(__module_path__, "ModelFittingWidget.ui"))

class _ModelFunctionExpressionSVGGenerator_(QtCore.QThread):
    ready = Signal(str, name="ready")
    
    def __init__(self, modelFunc:typing.Union[types.FunctionType, str], parent:QtCore.QObject):
        QtCore.QThread.__init__(self, parent)
        self._modelFunc_ = modelFunc
        
    def run(self):
        # from core import strutils
        # svg_out = models.renderModelExpression(self._modelFunc_, out="svg")
        svg = self._modelFunc_.expressionAsSVG()
        if is_svg(svg):
            self.ready.emit(svg)
        else:
            self.ready.emit("")
    

class ModelFittingWidget(Ui_ModelFittingWidget, QWidget, workspacegui.GuiMessages):
    sig_waveformReady = Signal(object, name="sig_waveformReady")
    def __init__(self, model: types.FunctionType|None = None,
                 duration:pq.Quantity = 1*pq.s,
                 start:pq.Quantity = 0*pq.s,
                 samplingRate:pq.Quantity = 1e4*pq.Hz,
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
        
        self._model_:typing.Optional[types.FunctionType] = None
        self._model_fit_coefficients_:typing.Optional[pd.DataFrame] = None
        self._model_name_:typing.Optional[str] = None
        self._model_expression_svg_:typing.Optional[QtGui.QPixmap] = None
        self._waveformStart_:typing.Optional[pq.Quantity] = None
        self._waveformDuration_:typing.Optional[pq.Quantity] = None
        self._waveformSamplingRate_:typing.Optional[pq.Quantity] = None
        self._waveformUnits_:typing.Optional[pq.Quantity] = None
        self._model_expression_window_:typing.Optional[QtWidgets.QMainWindow] = None
        self._expressionWindow_:typing.Optional[QtWidgets.QMainWindow] = None
        
        self._configureUI_()
        
        if isinstance(model, types.FunctionType):
            self._setModelData_(model, start, duration, samplingRate, waveformUnits, coefficients)
        
            if isinstance(self._model_fit_coefficients_, pd.DataFrame):
                self.populateCoefficientsTable(self._model_fit_coefficients_)

    def _configureUI_(self):
        from gui.guiutils import svg2pixmap
        self.setupUi(self)
        dsvg = str2svg("1:1", 16, 16, x=8, y=15, font_size=16, text_anchor="middle", dominant_baseline="hanging").as_svg()
        pix = svg2pixmap(dsvg)
        if not pix.isNull():
            self.makeUnitAmplitudePushButton.setIcon(QtGui.QIcon(pix))
            self.makeUnitAmplitudePushButton.setText("")
            self.makeUnitAmplitudePushButton.setFlat(True)
        self.makeUnitAmplitudePushButton.clicked.connect(self._slot_makeUnitAmplitudeModel)
        self.startSpinBox.sig_valueChanged.connect(self._slot_waveformStartChanged)
        self.durationSpinBox.sig_valueChanged.connect(self._slot_waveformDurationChanged)
        self.durationSpinBox.sig_valueChanged.connect(self._slot_waveformDurationChanged)
        self.samplingRateSpinBox.sig_valueChanged.connect(self._slot_waveformSamplingRateChanged)
        self.waveformUnitsPushButton.clicked.connect(self._slot_changeWaveformUnits)
        self.generateWaveformPushButton.clicked.connect(self._slot_generateWaveform)
        self.waveformExpressionPushButton.clicked.connect(self._slot_showModelExpression)
        self.pythonHelpPushButton.clicked.connect(self._slot_pythonHelpForModel)
        self.pythonHelpPushButton.setEnabled(False)
        self.generateWaveformPushButton.setEnabled(False)
        self.waveformExpressionPushButton.setEnabled(False)
        self.makeUnitAmplitudePushButton.setEnabled(False)
        self.waveformUnitsPushButton.setEnabled(False)
        self.startSpinBox.setEnabled(False)
        self.durationSpinBox.setEnabled(False)
        self.samplingRateSpinBox.setEnabled(False)

        if self._waveformUnits_ is None:
            self.unitsLabel.setText("")
            self.unitsLabel.setToolTip("Dimensionless")
        else:
            symbol = scq.shortSymbol(self._waveformUnits_)
            self.unitsLabel.setText(symbol)
            self.unitsLabel.setToolTip(symbol)
            
        # NOTE: 2026-01-19 15:35:18
        # have the expression widget (svgWidget) collapsed in the splitter, by default
        sizes = self.labelsSplitter.sizes()
        # print(f"{self.__class__.__name__}._configureUI_: lapbelsSplitter.sizes() -> {sizes}")
        sizes[0] = 0
        sizes[-1] = self.modelCoefficientsTable.size().height()
        self.labelsSplitter.setSizes(sizes)
            
    def _setModelData_(self, model:types.FunctionType, start:pq.Quantity=0*pq.s, duration:pq.Quantity=1*pq.s, samplingRate:pq.Quantity=1e4*pq.Hz, 
                 waveformUnits:pq.Quantity = pq.dimensionless,
                 coefficients:typing.Optional[typing.Union[dict, pd.DataFrame]] = None):
        assert isinstance(start, pq.Quantity) and start.size==1, f"'duration' must be a scalar quantity; instead, got {start}"
        assert isinstance(duration, pq.Quantity) and duration.size==1, f"'duration' must be a scalar quantity; instead, got {duration}"
        assert isinstance(samplingRate, pq.Quantity) and samplingRate.size==1 and samplingRate.units == 1/duration.units, f"'samplingRate' must be a scalar quantity in units of, or convertible to, {1/duration.units}; instead, got {samplingRate}"
        assert (isinstance(waveformUnits, pq.Quantity) and waveformUnits.size==1) or waveformUnits is None, f"'waveformUnits' , must be a scalar quantity or None; instead, gor {waveformUnits}"
        
        self._waveformStart_ = start
        self._waveformDuration_ = duration
        self._waveformSamplingRate_ = samplingRate
        self._waveformUnits_ = waveformUnits if isinstance(waveformUnits, pq.Quantity) else pq.dimensionless
        
        domainUnitsFamily = scq.getUnitFamily(self._waveformDuration_)
        if domainUnitsFamily == "Time":
            self._waveformSamplingRate_.rescale(pq.Hz)
        elif domainUnitsFamily in ("Length", "Space"):
            self._waveformSamplingRate_.rescale(pq.space_frequency_unit)
        elif domainUnitsFamily == "Angle" or self._waveformDuration_.units == pq.rad:
            self._waveformSamplingRate_.rescale(pq.angle_frequency_unit)
        else:
            self._waveformSamplingRate_.rescale(1/self._waveformDuration_.units)
            
        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), [self.startSpinBox, self.durationSpinBox, self.samplingRateSpinBox]))#, self.waveformUnitsChooser]))
        self.startSpinBox.setValue(self._waveformStart_)
        self.durationSpinBox.setValue(self._waveformDuration_)
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
           
        self._setModelFunction_(model)
        
        if isinstance(coefficients, (pd.DataFrame, dict)):
            self.fittingCoefficients = coefficients
        else:
            if isinstance(self._model_fit_coefficients_, pd.DataFrame):
                self.populateCoefficientsTable(self._model_fit_coefficients_)
                
    def _setModelFunction_(self, model:types.FunctionType):
        # from core.strutils import is_svg
        assert models.isModelFunction(model), f"Expecting a model function — which is NOT a regular Python function; instead, got {model}"
        self._model_ = model
        self._model_name_ = model.title
        
        self.modelNameLabel.setText(self._model_name_)
        self.modelNameLabel.setToolTip(f"Model function: {self._model_.__module__}.{self._model_.__name__}")
        self.pythonHelpPushButton.setToolTip(f"Python help for function {self._model_.__module__}.{self._model_.__name__}")
        self.pythonHelpPushButton.setEnabled(True)
        self.generateWaveformPushButton.setEnabled(True)
        self.waveformExpressionPushButton.setEnabled(True)
        # NOTE: 2026-01-18 01:06:02 TODO
        # make this contingent on the modelfunction offering a solution to this problem
        self.makeUnitAmplitudePushButton.setEnabled(True)
        self.waveformUnitsPushButton.setEnabled(True)
        self.startSpinBox.setEnabled(True)
        self.durationSpinBox.setEnabled(True)
        self.samplingRateSpinBox.setEnabled(True)

        fitting_dict = dict()
        new_fit_params = False
        if model.fitting:
            fitting_dict["Initial Value"] = model.fitting["initial"]
            fitting_dict["Lower Bound"] = model.fitting["lower"]
            fitting_dict["Upper Bound"] = model.fitting["upper"]
            new_fit_params = True
        else:
            fitting_dict = {'Initial Value': [0.] * len(model.coefficients), 'Lower Bound': [-np.inf] * len(model.coefficients), "Upper Bound": [np.inf] * len(model.coefficients)}
            
        fitting_dict["Keep Feasible"] = [True] * len(model.coefficients)
        
        fitting_df = pd.DataFrame(fitting_dict, index=(model.coefficients))
        
        # print(f"{self.__class__.__name__}._setModelFunction_: fitting_df = {fitting_df}")
        
        
        if not(isinstance(self._model_fit_coefficients_, pd.DataFrame) and self._model_fit_coefficients_.shape == fitting_df.shape and self._model_fit_coefficients_.index == fitting_df.index) or new_fit_params:
            self._model_fit_coefficients_ = fitting_df
            
        if not isinstance(self.modelCoefficientsTable._data_, pd.DataFrame) or self.modelCoefficientsTable._data_.size==0:
            self.populateCoefficientsTable(self._model_fit_coefficients_)

        self._generateModelExpressionSVG()
        
        self._setupExpressionWindow()
        
    def _generateModelExpressionSVG(self):
        worker = _ModelFunctionExpressionSVGGenerator_(self._model_, parent=self)
        worker.ready.connect(self._slot_modelExpressionGenerated)
        worker.run()
        worker.deleteLater()
        
    @Slot(str)
    def _slot_modelExpressionGenerated(self, svg:str|None):
        # if isinstance(d, dict) and "svg" in d:
            # print(f"{self.__class__.__name__}._setModelFunction_: {svg_out['svg']} \n is svg: {is_svg(svg_out['svg'])}")
        self._model_expression_svg_ = svg
        # print(f"{self.__class__.__name__}._setModelFunction_: self._model_expression_svg_ is svg@ {is_svg(self._model_expression_svg_)}")
        self.svgWidget.setSvg(self._model_expression_svg_)
        if is_svg(self._model_expression_svg_):
            svgSize = self.svgWidget.svgSize()
            if svgSize.width()>0 and svgSize.height() > 0:
                splitterMinSize = self.labelsSplitter.minimumSize()
                newSplitterMinSize = QtCore.QSize(splitterMinSize)
                newSplitterMinSize.setHeight(svgSize.height())
        self._setupExpressionWindow()
            
    @property
    def model(self) -> types.FunctionType:
        return self._model_
    
    @model.setter
    def model(self, model:types.FunctionType):
        # NOTE: 2026-01-16 15:30:46
        # this exclusively sets the model function and dependent attributes,
        # leaving duration, sampling rate and waveform units unchanged
        if models.isModelFunction(model):
            if models.isModelFunction(self._model_):
                # just change the model function
                self._setModelFunction_(model)
                self.populateCoefficientsTable(self._model_fit_coefficients_)
                if isinstance(self._model_name_, str) and len(self._model_name_.strip()):
                    self.modelNameLabel.setText(self._model_name_)
                else:
                    self.modelNameLabel.setText("")
            else:
                self._setModelData_(model)
        else:
            self.clear()
        
    @property
    def waveformStart(self) -> pq.Quantity:
        return self._waveformStart_
    
    @waveformStart.setter
    def waveformStart(self, val:pq.Quantity):
        assert isinstance(val, pq.Quantity) and val.size==1, f"'duration' must be a scalar quantity; instead, got {val}"
        if isinstance(self._waveformStart_, pq.Quantity):
            newUnits = False
            if self._waveformStart_.units != val.units:
                if scq.unitsConvertible(val, self._waveformStart_):
                    val = val.rescale(self._waveformStart_.units)
                else:
                    newUnits = True
        else:
            newUnits = True
                
        # print(f"{self.__class__.__name__} start setter: newUnits: {newUnits}")
                
        self._waveformStart_ = val
    
        if newUnits:
            self._waveformDuration_ = self._waveformDuration_.magnitude * self._waveformStart_.units
            if scq.unitsConvertible(self.waveformDuration, 1/self._waveformSamplingRate_.units):
                domainUnitsFamily = scq.getUnitFamily(self._waveformStart_)
                if domainUnitsFamily == "Time":
                    self._waveformSamplingRate_.rescale(pq.Hz)
                elif domainUnitsFamily in ("Length", "Space"):
                    self._waveformSamplingRate_.rescale(pq.space_frequency_unit)
                elif domainUnitsFamily == "Angle" or self._waveformStart_.units == pq.rad:
                    self._waveformSamplingRate_.rescale(pq.angle_frequency_unit)
            else:
                self._waveformSamplingRate_ = self._waveformSamplingRate_.magnitude / self._waveformStart_.units

        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), [self.startSpinBox, self.durationSpinBox, self.samplingRateSpinBox]))#, self.waveformUnitsChooser]))
        self.startSpinBox.setValue(self._waveformStart_)
        self.durationSpinBox.setValue(self._waveformDuration_)
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
        
        
    @property
    def waveformDuration(self) -> pq.Quantity:
        return self._waveformDuration_
    
    @waveformDuration.setter
    def waveformDuration(self, val:pq.Quantity):
        # NOTE: 2026-01-16 15:35:43
        # setting a new duration with different units:
        # if new units are not scalable to the current duration units, this will 
        #   also change the sampling rate units but leave their magnitude untouched
        # is new units ARE scalable/convertible to the current duration units, then
        #   the new duration will be rescaled to the current duration units
        assert isinstance(val, pq.Quantity) and val.size==1, f"'duration' must be a scalar quantity; instead, got {val}"
        
        if isinstance(self._waveformDuration_, pq.Quantity):
            newUnits = False
            if self._waveformDuration_.units != val.units:
                if scq.unitsConvertible(val, self._waveformDuration_):
                    val = val.rescale(self._waveformDuration_.units)
                else:
                    newUnits = True
        else:
            newUnits = True
            
        self._waveformDuration_ = val

        if newUnits:
            self._waveformStart_ = self._waveformStart_.magnitude * self._waveformDuration_.units
            if scq.unitsConvertible(self._waveformDuration_, 1/self._waveformSamplingRate_.units):
                domainUnitsFamily = scq.getUnitFamily(self._waveformDuration_)
                if domainUnitsFamily == "Time":
                    self._waveformSamplingRate_.rescale(pq.Hz)
                elif domainUnitsFamily in ("Length", "Space"):
                    self._waveformSamplingRate_.rescale(pq.space_frequency_unit)
                elif domainUnitsFamily == "Angle" or self._waveformDuration_.units == pq.rad:
                    self._waveformSamplingRate_.rescale(pq.angle_frequency_unit)
            else:
                self._waveformSamplingRate_ = self._waveformSamplingRate_.magnitude /  1/self._waveformDuration_.units

        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), [self.startSpinBox, self.durationSpinBox, self.samplingRateSpinBox]))#, self.waveformUnitsChooser]))
        self.startSpinBox.setValue(self._waveformStart_)
        self.durationSpinBox.setValue(self._waveformDuration_)
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
    
    @property
    def waveformSamplingRate(self)->pq.Quantity:
        return self._waveformSamplingRate_
    
    @waveformSamplingRate.setter
    def waveformSamplingRate(self, val:pq.Quantity):
        assert isinstance(val, pq.Quantity) and val.size==1 and scq.unitsConvertible(val.units, 1/self._waveformDuration_.units), f"'sampling rate' must be a scalar quantity in units of, or convertible to, {1/self._waveformDuration_.units}; instead, got {val}"
        self._waveformSamplingRate_ = val
        
        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), [self.samplingRateSpinBox]))#, self.waveformUnitsChooser]))
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
        
        
    @property
    def fittingCoefficients(self) -> pd.DataFrame:
        return self._model_fit_coefficients_
    
    @fittingCoefficients.setter
    def fittingCoefficients(self, coefficients: typing.Union[pd.DataFrame, dict]):
        if isinstance(coefficients, pd.DataFrame):
            # NOTE: 2026-01-13 23:26:42
            # override coefficients given by model only if the indexes are the same
            if isinstance(self._model_fit_coefficients_, pd.DataFrame):
                assert coefficients.size == self._model_fit_coefficients_.size, "Incompatible coefficients data were supplied"
                assert all(c in coefficients.index for c in self._model_.coefficients) and all(c in self._model_.coefficients for c in coefficients), "Incompatible coefficients data were supplied"
            
            self._model_fit_coefficients_ = coefficients
            
        elif isinstance(coefficients, dict):
            assert models.isFittingCoefficientsDict(coefficients), "Incompatible coefficients data supplied"
            fitting_dict["Initial Value"] = coefficients["initial"]
            fitting_dict["Lower Bound"] = coefficients["lower"]
            fitting_dict["Upper Bound"] = coefficients["upper"]
            fitting_dict["Upper Bound"] = coefficients["feasible"]
            # fitting_dict["Keep Feasible"] = [True] * len(coefficients["names"])
            if isinstance(self._model_fit_coefficients_, pd.DataFrame):
                assert len(coefficients["names"]) == self._model_fit_coefficients_.shape[0], "Incompatible coefficients data supplied"
                assert set(coefficients["names"]) == set(self._model_fit_coefficients_.index), "Incompatible coefficients data supplied"
            self._model_fit_coefficients_ = pd.DataFrame(fitting_dict, index=coefficients["names"])
        
        if isinstance(self._model_fit_coefficients_, pd.DataFrame):
            self.populateCoefficientsTable(self._model_fit_coefficients_)
            
    @property
    def modelName(self) -> str:
        return self._model_name_
    
    @modelName.setter
    def modelname(self, val:str):
        self._model_name_ = val
        
    def clear(self):
        from gui.widgets import svgwidgets
        self.modelNameLabel.setText("")
        self.modelNameLabel.setToolTip(f"")
        self.pythonHelpPushButton.setToolTip(f"")
        self.pythonHelpPushButton.setEnabled(False)
        self.generateWaveformPushButton.setEnabled(False)
        self.waveformExpressionPushButton.setEnabled(False)
        self.makeUnitAmplitudePushButton.setEnabled(False)
        self.waveformUnitsPushButton.setEnabled(False)
        self.startSpinBox.setEnabled(False)
        self.durationSpinBox.setEnabled(False)
        self.samplingRateSpinBox.setEnabled(False)
        self.populateCoefficientsTable(pd.DataFrame())
        if isinstance(self._expressionWindow_, QtWidgets.QMainWindow):
            if isinstance(self._expressionWindow_.centralWidget(), svgwidgets.SimpleSVGWidget):
                self._expressionWindow_.centralWidget().setSvg(None)
            elif isinstance(self._expressionWindow_.centralWidget(), QtCore.QLabel):
                self._expressionWindow_.centralWidget().setPixmap(QtGui.QPixmap())
        self._model_ = None
        self._model_name_ = None
        self._model_expression_svg_ = None
        self.svgWidget.setSvg(self._model_expression_svg_)

    def populateCoefficientsTable(self, data:typing.Optional[pd.DataFrame]=None):
        if isinstance(data, pd.DataFrame) and data.size > 0:
            assert all(v in data.columns for v in ('Initial Value', 'Lower Bound', 'Upper Bound', 'Keep Feasible')), "Not a model parameters data frame"
            self._model_fit_coefficients_ = data
            self.modelCoefficientsTable.setData(self._model_fit_coefficients_)
            
        else:
            self._model_fit_coefficients_ = None
            self.modelCoefficientsTable.clear()
            

    def _calculateWaveformSamples(self) -> int:
        assert(scq.unitsConvertible(1/self._waveformSamplingRate_, self._waveformDuration_)), f"Waveform duration ({self._waveformDuration_}) and sampling rate ({self._waveformSamplingRate_}) have incompatible units"
        return int(self._waveformDuration_ * self._waveformSamplingRate_.magnitude)
    
    def _generateWaveformDomain_(self) -> np.ndarray:
        # t_start = 0* self._waveformDuration_.units
        return np.linspace(self._waveformStart_.magnitude, self._waveformStart_.magnitude + self._waveformDuration_.magnitude, self._calculateWaveformSamples())
        
    # @Slot()
    # def _slot_modelCoefficientsChanged(self):
    #     pass
    
    @Slot()
    def _slot_showModelExpression(self):
        # from core.strutils import is_svg
        if not isinstance(self._model_expression_svg_, QtGui.QPixmap) and not is_svg(self._model_expression_svg_):
            # print("invalid expression")
            return
        self._setupExpressionWindow()
            
        if not self._expressionWindow_.isVisible():
            self._expressionWindow_.resize(self._expressionWindow_.centralWidget().svgSize())
            self._expressionWindow_.show()
            
    def _setupExpressionWindow(self):
        # from core.strutils import is_svg
        from gui.widgets import svgwidgets
        if not isinstance(self._expressionWindow_, QtWidgets.QMainWindow):
            self._expressionWindow_ = QtWidgets.QMainWindow()
            sWidget = svgwidgets.SimpleSVGWidget(parent=self._expressionWindow_)
            self._expressionWindow_.setCentralWidget(sWidget)
            
        if is_svg(self._model_expression_svg_):
            self._expressionWindow_.centralWidget().setSvg(self._model_expression_svg_)
        else:
            self._expressionWindow_.centralWidget().setSvg(None)
                
        if isinstance(self._model_name_, str):
            self._expressionWindow_.setWindowTitle(f"{QtWidgets.QApplication.instance().applicationName()} - {self._model_name_} model")
        else:
            self._expressionWindow_.setWindowTitle(f"{QtWidgets.QApplication.instance().applicationName()} - no model")
    
    @Slot()
    def _slot_generateWaveform(self):
        from core import datasignal
        from gui.guiutils import getScipyenMainWindow
        if not isinstance(self._model_, types.FunctionType) or not models.isModelFunction(self._model_):
            return

        try:
            x = self._generateWaveformDomain_()

            coeffs = list(self._model_fit_coefficients_["Initial Value"])
            y = self._model_(x, coeffs)
            sigUnits = self._waveformUnits_.units if isinstance(self._waveformUnits_, pq.Quantity) else pq.dimensionless
            
            if scq.checkTimeUnits(self._waveformDuration_):
                sig = neo.AnalogSignal(y, t_start = self._waveformStart_, units = sigUnits, sampling_rate=self._waveformSamplingRate_, name=self._model_name_)
            else:
                sig = datasignal.DataSignal(y, t_start = self._waveformStart_, units = sigUnits, domain_units = self._waveformDuration_.units,
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
        if not isinstance(self._model_, types.FunctionType) or not models.isModelFunction(self._model_):
            return
        pass
    
    @Slot()
    def _slot_pythonHelpForModel(self):
        from gui import guiutils
        if not isinstance(self._model_, types.FunctionType) or not models.isModelFunction(self._model_):
            return
        
        mainWindow = guiutils.getScipyenMainWindow()
        mainWindow.runPythonHelpGUI(f"{self._model_.__name__}")
    
    @Slot()
    def _slot_changeWaveformUnits(self):
        from gui.quickdialog import QuickDialog
        from gui.widgets import small_widgets
        dlg = QuickDialog(title="Choose waveform units")
        units = self._waveformUnits_.units if isinstance(self._waveformUnits_, pq.Quantity) else pq.dimensionless
        qc = small_widgets.QuantityChooserWidget(parent=dlg, unit = units)
        dlg.addWidget(qc)
        if dlg.exec():
            self.waveformUnits = qc.value()
            
    @Slot(object)
    def _slot_waveformStartChanged(self, val:typing.Union[pq.Quantity, float, int, np.float64, np.int64]):
        # print(f"{self.__class__.__name__}._slot_waveformStartChanged({val})")
        start = self._waveformStart_
        if isinstance(val, pq.Quantity):
            assert(val.size == 1), "Expecting a scalar Quantity"
            start = val
            
        elif isinstance(val, (float, np.float64, int, np.int64)):
            start = val * self._waveformStart_.units
            
        else:
            raise TypeError(f"Wrong value type ({type(val).__name__})")
        
        self.waveformStart = start
        
#         rate = self._waveformSamplingRate_
#         
#         if scq.unitsConvertible(1/self._waveformSamplingRate_, start):
#             if start.units != 1/self._waveformSamplingRate_:
#                 rate = self._waveformSamplingRate_.rescale(1/start.units)
#                 
#         else:
#             rate = self._waveformSamplingRate_.magnitude / start.units
#             
#         self._waveformStart_ = start
#             
#         if rate != self._waveformSamplingRate_:
#             self._waveformSamplingRate_ = rate
#             signalBlocker = QtCore.QSignalBlocker(self.samplingRateSpinBox)
#             self.samplingRateSpinBox.setValue(rate)
        
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
        
        self.waveformDuration = duration
        
#         rate = self._waveformSamplingRate_
#         
#         if scq.unitsConvertible(1/self._waveformSamplingRate_, duration):
#             if duration.units != 1/self._waveformSamplingRate_:
#                 rate = self._waveformSamplingRate_.rescale(1/duration.units)
#                 
#         else:
#             rate = self._waveformSamplingRate_.magnitude / duration.units
#             
#         self._waveformDuration_ = duration
#             
#         if rate != self._waveformSamplingRate_:
#             self._waveformSamplingRate_ = rate
#             signalBlocker = QtCore.QSignalBlocker(self.samplingRateSpinBox)
#             self.samplingRateSpinBox.setValue(rate)
            
    
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
        
        self.waveformSamplingRate = rate
        
#         duration = self._waveformDuration_
#             
#         if not scq.unitsConvertible(1/rate, self._waveformDuration_):
#             if self._waveformDuration_.units != 1/rate.units:
#                 duration = self._waveformDuration_.rescale(1/rate.units)
#         else:
#             duration = self._waveformDuration_.magnitude  / rate.units
#             
#         self._waveformSamplingRate_ = rate
#         
#         if duration != self._waveformDuration_:
#             self._waveformDuration_ = duration
#             signalBlocker = QtCore.QSignalBlocker(self.durationSpinBox)
#             self.durationSpinBox.setValue(duration)
        
    @property
    def waveformUnits(self) -> pq.Quantity | None:
        return self._waveformUnits_

    @waveformUnits.setter
    def waveformUnits(self, val:typing.Optional[pq.Quantity]):
        if not isinstance(val, pq.Quantity):
            self._waveformUnits_ = None
        else:
            self._waveformUnits_ = val.units
            
        if self._waveformUnits_ is None:
            self.unitsLabel.setText("")
            self.unitsLabel.setToolTip("Dimensionless")
        else:
            symbol = scq.shortSymbol(self._waveformUnits_)
            self.unitsLabel.setText(symbol)
            self.unitsLabel.setToolTip(symbol)
            
