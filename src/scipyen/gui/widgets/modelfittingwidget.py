# -*- coding: utf-8 -*-
# $Id: modelfittingwidget.py $
# SPDX-FileCopyrightText: 2022 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Widget for model parameter inputs
"""
import math, numbers, typing, os, types, sys, traceback, warnings
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
    
from core.strutils import (str2symbol, is_svg, str2svg, get_int_sfx)
from core import models
from core import scipyen_quantities as scq
from core import datasignal

from iolib import pictio as pio
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
    # NOTE: 2026-01-21 10:44:11 TODO URGENT
    # Currently inserting rows for starred coefficients is implemented by means
    # of redefining the coefficients data frame
    # In the (near) future I should try to implement this in the TabularDataModel
    # used by the TableEditorWidget
    sig_waveformReady = Signal(object, name="sig_waveformReady")
    def __init__(self, model: types.FunctionType|None = None,
                 duration:pq.Quantity = 1*pq.dimensionless,
                 start:pq.Quantity = 0*pq.dimensionless,
                 samplingRate:pq.Quantity = 1e4*pq.dimensionless,
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
        When given, it can be used to override the coefficients table extracted from the ``model`` parameter, provided it has a compatible structure (i.e. same number and names of coefficients)

            
"""
        QWidget.__init__(self, parent=parent)
        
        self._nStarredCoeffs_:int = 0
        self._nStarredGroups_:int = 0
        self._destarredCoeffs_:typing.Sequence = list()
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
                self._populateCoefficientsTable_(self._model_fit_coefficients_)

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
        self.startSpinBox.setDecimals(5)
        self.startSpinBox.sig_valueChanged.connect(self._slot_waveformStartChanged)
        self.durationSpinBox.setDecimals(5)
        self.durationSpinBox.sig_valueChanged.connect(self._slot_waveformDurationChanged)
        self.samplingRateSpinBox.setDecimals(5)
        self.samplingRateSpinBox.sig_valueChanged.connect(self._slot_waveformSamplingRateChanged)
        self.waveformUnitsPushButton.clicked.connect(self._slot_changeWaveformUnits)
        self.generateWaveformPushButton.clicked.connect(self._slot_generateWaveform)
        self.waveformExpressionPushButton.clicked.connect(self._slot_showModelExpression)
        self.pythonHelpPushButton.clicked.connect(self._slot_pythonHelpForModel)
        self.addStarredRowsPushButton.clicked.connect(self._slot_addRowsForStarredCoeffs)
        self.removeStarredRowsPushButton.clicked.connect(self._slot_removeRowsForStarredCoeffs)
        self.pythonHelpPushButton.setEnabled(False)
        self.generateWaveformPushButton.setEnabled(False)
        self.waveformExpressionPushButton.setEnabled(False)
        self.makeUnitAmplitudePushButton.setEnabled(False)
        self.waveformUnitsPushButton.setEnabled(False)
        self.startSpinBox.setEnabled(False)
        self.durationSpinBox.setEnabled(False)
        self.samplingRateSpinBox.setEnabled(False)
        self.addStarredRowsPushButton.setEnabled(False)
        self.removeStarredRowsPushButton.setEnabled(False)

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
            
    def _setModelData_(self, model:types.FunctionType,
                       start:pq.Quantity=0*pq.dimensionless,
                       duration:pq.Quantity=1*pq.dimensionless,
                       samplingRate:pq.Quantity=1e4*pq.dimensionless,
                       waveformUnits:pq.Quantity = pq.dimensionless,
                       coefficients:typing.Optional[typing.Union[dict, pd.DataFrame]] = None):
        assert isinstance(start, pq.Quantity) and start.size==1, f"'duration' must be a scalar quantity; instead, got {start}"
        assert isinstance(duration, pq.Quantity) and duration.size==1, f"'duration' must be a scalar quantity; instead, got {duration}"
        assert isinstance(samplingRate, pq.Quantity) and samplingRate.size==1 and samplingRate.units == 1/duration.units, f"'samplingRate' must be a scalar quantity in units of, or convertible to, {1/duration.units}; instead, got {samplingRate}"
        assert (isinstance(waveformUnits, pq.Quantity) and waveformUnits.size==1) or waveformUnits is None, f"'waveformUnits' , must be a scalar quantity or None; instead, gor {waveformUnits}"
        
        assert models.isModelFunction(model), f"Expecting a model function — which is NOT a regular Python function; instead, got {model}"
        
        if isinstance(start, (float, int)):
            start = start*pq.s
        elif not isinstance(start, pq.Quantity):
            start = 0*pq.s
            
        if isinstance(duration, (float, int)):
            duration = duration*pq.s
        elif not isinstance(start, pq.Quantity):
            start = 0*pq.s
            
        assert scq.unitsConvertible(duration, start), f"Duration rate units ({duration.units}) and domain units ({start.units}) are incompatible"
        assert duration > 0, f"Cannot accept duration <= {0*duration.units}"
        
        if isinstance(samplingRate, (float, int)):
            samplingRate = samplingRate*pq.Hz
        elif not isinstance(samplingRate, pq.Quantity):
            samplingRate = 0*pq.Hz
            
        assert scq.unitsConvertible(1/samplingRate.units, start.units), f"Sampling rate units ({samplingRate.units}) and domain units ({start.units}) are incompatible"
        assert samplingRate > 0, f"Cannot accept duration <= {0*samplingRate.units}"
        
        if isinstance(model.domainUnits, pq.Quantity):
            start = start.magnitude * model.domainUnits.units
            duration = duration.magnitude * model.domainUnits.units
            samplingRate = samplingRate.magnitude / model.domainUnits.units
            
        if isinstance(model.units, pq.Quantity):
            waveformUnits = waveformUnits.magnitude * model.units if isinstance(waveformUnits, pq.Quantity) else waveformUnits * model.units if isinstance(waveformUnits, float) else 1*model.units
            
        self._waveformStart_ = start
        self._waveformDuration_ = duration
        self._waveformSamplingRate_ = samplingRate


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
        self.waveformUnits = waveformUnits # will also set up the unitsLabel
        # self.waveformUnitsChooser.setValue(self._waveformUnits_)
           
        self._setModelFunction_(model, coefficients)
        
    def _setModelFunction_(self, model:types.FunctionType, coefficients=None):
        # from core.strutils import is_svg
        assert models.isModelFunction(model), f"Expecting a model function — which is NOT a regular Python function; instead, got {model}"
        self._model_ = model
        self._model_name_ = model.title

        self.modelNameLabel.setText(self._model_name_)
        self.modelNameLabel.setToolTip(f"Model function: {self._model_.__module__}.{self._model_.__name__}\nDrag (⇓) the splitter below to reveal the mathematical formula")
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

        fitting_df = self._parseModelCoefficients_(model, coefficients)

        # print(f"{self.__class__.__name__}._setModelFunction_: fitting_df = {fitting_df}")
        
        if isinstance(fitting_df, pd.DataFrame):
            self._model_fit_coefficients_ = fitting_df
            self._populateCoefficientsTable_(self._model_fit_coefficients_)
            

        # if not(isinstance(self._model_fit_coefficients_, pd.DataFrame) and self._model_fit_coefficients_.shape == fitting_df.shape and np.all(self._model_fit_coefficients_.index == fitting_df.index)) or new_fit_params:
        #     self._model_fit_coefficients_ = fitting_df
        # 
        # if not isinstance(self.modelCoefficientsTable._data_, pd.DataFrame):# or self.modelCoefficientsTable._data_.size==0:
        #     self._populateCoefficientsTable_(self._model_fit_coefficients_)

        self._generateModelExpressionSVG()

        self._setupExpressionWindow()

        self.addStarredRowsPushButton.setEnabled(self._nStarredCoeffs_ > 0)
        self.removeStarredRowsPushButton.setEnabled(self._nStarredCoeffs_ > 0 and self._nStarredGroups_ > 1)

        # if isinstance(fitting_df, pd.DataFrame):
        #     self.fittingCoefficients = fitting_df
        # else:
        #     if isinstance(self._model_fit_coefficients_, pd.DataFrame):
        #         self._populateCoefficientsTable_(self._model_fit_coefficients_)


    def _parseModelCoefficients_(self, model:types.FunctionType,
                                 coefficients:typing.Optional[typing.Union[pd.DataFrame, dict]]=None) -> pd.DataFrame:
        assert models.isModelFunction(model), f"Expecting a model function — which is NOT a regular Python function; instead, got {model}"
        ret = pd.DataFrame()

        if len(model.coefficients):
            starred = model.starred_coefficients
            ret, destarred, starredGroups = model.generateFitTable()
            
            self._nStarredCoeffs_ = len(starred)
            self._destarredCoeffs_= destarred
            self._nStarredGroups_ = starredGroups
            
#             starred = list(filter(lambda c: c.endswith("*"), model.coefficients))
#             destarred = list(map(lambda c: c.strip("*"), starred))
#             unstarred = list(filter(lambda c: not c.endswith("*"), model.coefficients))
# 
#             order = list(map(lambda c: model.coefficients.index(c), unstarred + starred))
#             unstarredorder = list(map(lambda c: model.coefficients.index(c), unstarred))
#             starredorder = list(map(lambda c: model.coefficients.index(c), starred))
# 
#             concrete_names = unstarred + list(map(lambda c: f"{c}0", destarred))
# 
#             self._nStarredCoeffs_ = len(starred)
#             self._destarredCoeffs_= destarred
#             self._nStarredGroups_ = 1
# 
# 
#             # NOTE: 2026-01-21 12:03:46
#             # for the actual function call, the starred coefficients ALWAYS go last
#             # as sequence c0_0, c1_0, c2_0, c0_1, c1_1, c2_1, ... etc
# 
#             # so, currently we need to create a tuple of starred coeffs and repeat this at least once
# 
#             fdict = dict()
# 
#             fdict["Names"] = concrete_names
#             fdict["Initial Value"] = [0.] * len(fdict["Names"])
#             fdict["Lower Bound"] = [-np.inf] * len(fdict["Names"])
#             fdict["Upper Bound"] = [np.inf] * len(fdict["Names"])
#             fdict["Keep Feasible"] = [True] * len(fdict["Names"])
# 
#             if not models.isFittingCoefficientsDict(model.fitting):
#                 fd = fdict.copy()
#                 fd.pop("Names")
#                 ret = pd.DataFrame(fd, index=(concrete_names))
#                 return ret
# 
#             mfd = {"Names":list(), "Initial Value": list(), "Lower Bound": list(), "Upper Bound": list(), "Keep Feasible": list()}
# 
#             names       = model.fitting.get("names", list())
#             ncoeffs     = len(names)
# 
#             assert(ncoeffs >= len(fdict["Names"]) and (ncoeffs-len(unstarred)) % len(starred) ) == 0, f"Unexpected number of coefficients ({ncoeffs}); must be {self._nStarredCoeffs_} × n + {len(unstarred)} for n components"
# 
#             initial     = model.fitting.get("initial", list())
#             lower       = model.fitting.get("lower", list())
#             upper       = model.fitting.get("upper", list())
#             feasible    = model.fitting.get("feasible", list())
# 
#             assert(all(len(v) == len(initial) for v in (lower, upper, feasible))), "Model has inconsistent fitting attribute"
# 
#             for k, name in enumerate(names):
#                 if name in fdict["Names"]:
#                     ndx = fdict["Names"].index(name)
#                     if ndx < len(initial):
#                         fdict["Initial Value"][ndx] = initial[ndx]
#                     if ndx < len(lower):
#                         fdict["Lower Bound"][ndx] = lower[ndx]
#                     if ndx < len(upper):
#                         fdict["Upper Bound"][ndx] = upper[ndx]
#                     if ndx < len(feasible):
#                         fdict["Keep Feasible"][ndx] = feasible[ndx]
# 
# 
#                 else:
#                     # add possibly extra concrete values for starred coeffs
#                     stripped, sfx = strutils.get_int_sfx(name, sep="")
#                     if f"{stripped}*" in starred:
#                         fdict["Names"].append(name)
#                         fdict["Initial Value"].append(initial[k])
#                         fdict["Lower Bound"].append(lower[k])
#                         fdict["Upper Bound"].append(upper[k])
#                         fdict["Keep Feasible"].append(feasible[k])
# 
#             fd = fdict.copy()
#             fd.pop("Names")
#             ret = pd.DataFrame(fd, index=(fdict["Names"]))

        else:
            if isinstance(coefficients, pd.DataFrame):
                # NOTE: 2026-01-21 13:14:04
                # too complicated to verify this w/o a model.coefficients, so take a risk, hedge your bets
                ret = coefficients

            elif isinstance(coefficients, dict):
                names = coefficients.get("names", list()),
                if len(names):
                    fd = {"Initial Value": coefficients.get("initial", list()),
                        "Lower Bound": coefficients.get("lower", list()),
                        "Upper Bound": coefficients.get("upper", list()),
                        "Keep Feasible": coefficients.get("feasible", list())}

                    # NOTE: 2026-01-21 13:18:29
                    # same as for NOTE: 2026-01-21 13:14:04 above
                    ret = pd.DataFrame(fd, index = (names))


        # print(f"{self.__class__.__name__}._parseModelCoefficients_: ret -> {ret}")

        return ret

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
    def domain(self) -> np.ndarray|None:
        return self._generateWaveformDomain_()
            
    @property
    def model(self) -> types.FunctionType:
        return self._model_
    
    @model.setter
    def model(self, model:types.FunctionType):
        # NOTE: 2026-01-16 15:30:46
        # this exclusively sets the model function and dependent attributes,
        # leaving duration, sampling rate and waveform units unchanged
        if models.isModelFunction(model):
            self._setModelData_(model)
        else:
            if model is not None:
                msg = f"Expecting a model function\n(Python function decorated with the '@modelfunction' decorator);\ninstead, got a {type(model).__name__}."
                self.detailedMessage("Error", msg)
            self.clear()
        
    @property
    def waveformStart(self) -> pq.Quantity:
        self._waveformStart_ = self.startSpinBox.value()
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

            if scq.unitsConvertible(self._waveformDuration_, 1/self._waveformSamplingRate_.units):
                domainUnitsFamily = scq.getUnitFamily(self._waveformStart_)
                if domainUnitsFamily == "Time":
                    self._waveformSamplingRate_.rescale(pq.Hz)
                elif domainUnitsFamily in ("Length", "Space"):
                    self._waveformSamplingRate_.rescale(pq.space_frequency_unit)
                elif domainUnitsFamily == "Angle" or self._waveformStart_.units == pq.rad:
                    self._waveformSamplingRate_.rescale(pq.angle_frequency_unit)
            else:
                self._waveformSamplingRate_ = self._waveformSamplingRate_.magnitude / self._waveformStart_.units

        blockedWidgets = [self.startSpinBox, self.durationSpinBox, self.samplingRateSpinBox]
        # blockedWidgets.extend(list(map(lambda w: w.lineEdit(), blockedWidgets)))
        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), blockedWidgets))#, self.waveformUnitsChooser]))

        self.startSpinBox.setValue(self._waveformStart_)
        self.durationSpinBox.setValue(self._waveformDuration_)
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
        
        
    @property
    def waveformDuration(self) -> pq.Quantity:
        self._waveformDuration_ = self.durationSpinBox.value()
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
            
        # print(f"{self.__class__.__name__} duration setter: newUnits: {newUnits}")

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

        blockedWidgets = [self.startSpinBox, self.durationSpinBox, self.samplingRateSpinBox]
        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), blockedWidgets))#, self.waveformUnitsChooser]))
        self.startSpinBox.setValue(self._waveformStart_)
        self.durationSpinBox.setValue(self._waveformDuration_)
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
    
    @property
    def waveformSamplingRate(self)->pq.Quantity:
        self._waveformSamplingRate_ = self.samplingRateSpinBox.value()
        return self._waveformSamplingRate_
    
    @waveformSamplingRate.setter
    def waveformSamplingRate(self, val:pq.Quantity):
        assert isinstance(val, pq.Quantity) and val.size==1 and scq.unitsConvertible(val.units, 1/self._waveformDuration_.units), f"'sampling rate' must be a scalar quantity in units of, or convertible to, {1/self._waveformDuration_.units}; instead, got {val}"
        self._waveformSamplingRate_ = val
        
        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), [self.samplingRateSpinBox]))#, self.waveformUnitsChooser]))
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
        
    @property
    def coefficientValues(self) -> typing.Sequence:
        return list(self._model_fit_coefficients_["Initial Value"])
        
    @property
    def fittingCoefficients(self) -> pd.DataFrame | None:
        return self._model_fit_coefficients_
    
    @fittingCoefficients.setter
    def fittingCoefficients(self, coefficients: pd.DataFrame):
        if not models.isModelFunction(self._model_):
            return
        
        if isinstance(coefficients, pd.DataFrame):
            OK, unstarred, var, groups = models.parseCoefficientsFitTable(self._model_, coefficients)
            
            if OK:
                self._model_fit_coefficients_ = coefficients
                self._populateCoefficientsTable_(self._model_fit_coefficients_) # just replace it all, for now
                
            else:
                self.criticalMessage("Table is not compatible with this model")
                
#                 # NOTE: 2026-01-13 23:26:42
#                 # override coefficients given by model only if the indexes are the same
#                 if isinstance(self._model_fit_coefficients_, pd.DataFrame) and models.parseCoefficientsFitTable(self._model_,self._model_fit_coefficients_)[0]:
#                     for c in unstarred:
#                         self._model_fit_coefficients_.loc[c,:] = coefficients.loc[c,:]
#                     varToAdd = list()
#                     for v in var:
#                         if c in self._model_fit_coefficients_.index:
#                             self._model_fit_coefficients_.loc[c,:] = coefficients.loc[c,:]
#                         else:
#                             self._model_fit_coefficients_ = pd.concat([self._model_fit_coefficients_, pd.DataFrame(coefficients.loc[c,:])].T)
#                             
#                     for g in groups:
#                         for c in g:
#                             if c in self._model_fit_coefficients_.index:
#                                 self._model_fit_coefficients_.loc[c,:] = coefficients.loc[c,:]
#                             else:
#                                 self._model_fit_coefficients_ = pd.concat([self._model_fit_coefficients_, pd.DataFrame(coefficients.loc[c,:])].T)
                            
                    
                    
            
        
            # # NOTE: 2026-01-13 23:26:42
            # # override coefficients given by model only if the indexes are the same
            # if isinstance(self._model_fit_coefficients_, pd.DataFrame):
            #     assert coefficients.size == self._model_fit_coefficients_.size, "Incompatible coefficients data were supplied"
            #     assert all(c in coefficients.index for c in self._model_.coefficients) and all(c in self._model_.coefficients for c in coefficients), "Incompatible coefficients data were supplied"
            # 
            # self._model_fit_coefficients_ = coefficients
            # self._populateCoefficientsTable_(self._model_fit_coefficients_)

#         elif isinstance(coefficients, dict):
#             assert models.isFittingCoefficientsDict(coefficients), "Incompatible coefficients data supplied"
#             fitting_dict["Initial Value"] = coefficients["initial"]
#             fitting_dict["Lower Bound"] = coefficients["lower"]
#             fitting_dict["Upper Bound"] = coefficients["upper"]
#             fitting_dict["Upper Bound"] = coefficients["feasible"]
#             # fitting_dict["Keep Feasible"] = [True] * len(coefficients["names"])
#             if isinstance(self._model_fit_coefficients_, pd.DataFrame):
#                 assert len(coefficients["names"]) == self._model_fit_coefficients_.shape[0], "Incompatible coefficients data supplied"
#                 assert set(coefficients["names"]) == set(self._model_fit_coefficients_.index), "Incompatible coefficients data supplied"
#             self._model_fit_coefficients_ = pd.DataFrame(fitting_dict, index=coefficients["names"])
#
#         if isinstance(self._model_fit_coefficients_, pd.DataFrame):
#             self._populateCoefficientsTable_(self._model_fit_coefficients_)

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
        self._populateCoefficientsTable_(pd.DataFrame())
        if isinstance(self._expressionWindow_, QtWidgets.QMainWindow):
            if isinstance(self._expressionWindow_.centralWidget(), svgwidgets.SimpleSVGWidget):
                self._expressionWindow_.centralWidget().setSvg(None)
            elif isinstance(self._expressionWindow_.centralWidget(), QtCore.QLabel):
                self._expressionWindow_.centralWidget().setPixmap(QtGui.QPixmap())
        self._model_ = None
        self._model_name_ = None
        self._model_expression_svg_ = None
        self.svgWidget.setSvg(self._model_expression_svg_)

    def _populateCoefficientsTable_(self, data:typing.Optional[pd.DataFrame]=None):
        if isinstance(data, pd.DataFrame) and data.size > 0:
            assert all(v in data.columns for v in ('Initial Value', 'Lower Bound', 'Upper Bound', 'Keep Feasible')), "Not a model parameters data frame"
            # if isinstance(self._model_fit_coefficients_, pd.DataFrame) and not np.all(data.index == self._model_fit_coefficients_.index):
            #     self.modelCoefficientsTable.clear

            self._model_fit_coefficients_ = data
            self.modelCoefficientsTable.setData(self._model_fit_coefficients_)

        else:
            self._model_fit_coefficients_ = None
            self.modelCoefficientsTable.clear()
            

    def _calculateWaveformSamples(self) -> int:
        self._waveformDuration_ = self.durationSpinBox.value()
        self._waveformSamplingRate_ = self.samplingRateSpinBox.value()
        assert(scq.unitsConvertible(1/self._waveformSamplingRate_.units, self._waveformDuration_.units)), f"Waveform duration ({self._waveformDuration_}) and sampling rate ({self._waveformSamplingRate_}) have incompatible units"
        return int(self._waveformDuration_ * self._waveformSamplingRate_.magnitude)
    
    def _generateWaveformDomain_(self) -> np.ndarray:
        # t_start = 0* self._waveformDuration_.units
        self._waveformStart_ = self.startSpinBox.value()
        self._waveformDuration_ = self.durationSpinBox.value()
        self._waveformSamplingRate_ = self.samplingRateSpinBox.value()
        return np.linspace(self._waveformStart_.magnitude, self._waveformStart_.magnitude + self._waveformDuration_.magnitude, self._calculateWaveformSamples())
        
    def generateWaveform(self) -> neo.basesignal.BaseSignal | None:
        from gui.guiutils import getScipyenMainWindow
        if not isinstance(self._model_, types.FunctionType) or not models.isModelFunction(self._model_):
            return
        try:
            self._waveformStart_ = self.startSpinBox.value()
            self._waveformDuration_ = self.durationSpinBox.value()
            self._waveformSamplingRate_ = self.samplingRateSpinBox.value()

            x = self._generateWaveformDomain_()

            coeffs = self.coefficientValues
            # coeffs = list(self._model_fit_coefficients_["Initial Value"])

            with warnings.catch_warnings(record=True) as wrn:
                y = self._model_(x, coeffs)

            sigUnits = self._waveformUnits_.units if isinstance(self._waveformUnits_, pq.Quantity) else pq.dimensionless
            sigName = f"{self._model_name_} model"

            name = f"{self._model_name_} model" if  self._waveformUnits_.units==pq.dimensionless else f"{scq.unitFamilyName(self._waveformUnits_.units)}"
            
            if scq.checkTimeUnits(self._waveformDuration_):
                sig = neo.AnalogSignal(y, t_start = self._waveformStart_, units = sigUnits, sampling_rate=self._waveformSamplingRate_, name=name, signal_name=sigName)
            else:
                sig = datasignal.DataSignal(y, t_start = self._waveformStart_, units = sigUnits, domain_units = self._waveformDuration_.units,
                                        sampling_rate=self._waveformSamplingRate_, name=name, signal_name=sigName)
                # if scq.unitsConvertible(sig.times.units, pq.V):
                #     scq.domain_name = "Potential"
                
            if sig.units != pq.dimensionless.units:
                sig.name = scq.unitFamilyName(sig.units)
            

            if wrn:
                warningMessages = self.unpackWarnings(wrn)
                msgBox = QtWidgets.QMessageBox(self)
                msgBox.setWindowTitle("Warning")
                msgBox.setText(warningMessages)
                msgBox.setTextFormat(QtCore.Qt.RichText)
                msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                msgBox.exec()
                # self.warningMessage(self.modelName, warningMessages,default=QtWidgets.QMessageBox.NoButton)

        except:
            traceback.print_exc()
            exc = sys.exception()
            msg = "".join(traceback.format_exception_only(exc))
            self.errorMessage(type(exc).__name__, msg)
            return

        self.sig_waveformReady.emit(sig)

        if self.receivers(self.sig_waveformReady) == 0:
            varname = f"{self._model_name_}_waveform" if isinstance(self._model_name_, str) and len(self._model_name_.strip()) else "model_waveform"
            getScipyenMainWindow().assignToWorkspace(varname, sig)
            
        return sig
        
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
    def _slot_addRowsForStarredCoeffs(self): # TODO 2026-01-21 12:43:22
        import itertools
        df = self._model_fit_coefficients_
        if not isinstance(df, pd.DataFrame):
            return

        # NOTE: 2026-01-21 15:23:05
        # figure out how many groups are there already - for a model with starred coeffs
        # there should be at least one group (indexed at 0)!
        fdnames = list(df.index)
        dfdestarred = list(itertools.chain.from_iterable(map(lambda c: filter(lambda n: n.startswith(c), fdnames), self._destarredCoeffs_)))

        if len(dfdestarred):
            groups = list(map(lambda s: get_int_sfx(s, sep="")[1], dfdestarred))
            grset = set(groups)
            assert(len(grset) > 0), "There must be at least one group of concrete values for starred coefficients"
            lastGroup = sorted(list(grset))[-1]

            nextGroup = lastGroup +1
            self._nStarredGroups_ += 1

            self.removeStarredRowsPushButton.setEnabled(self._nStarredCoeffs_ > 0 and self._nStarredGroups_ > 1)

            # print(f"{self.__class__.__name__}._slot_addRowsForStarredCoeffs: groups = {groups}, lastGroup = {lastGroup},  nextGroup = {nextGroup}")

            extra = {"Names": list()}
            extra.update(dict(map(lambda k: (k, list()), df.columns)))

            for ds in self._destarredCoeffs_:
                extra["Names"].append(f"{ds}{nextGroup}")
                extra["Initial Value"].append(0.0)
                extra["Lower Bound"].append(-np.inf)
                extra["Upper Bound"].append(np.inf)
                extra["Keep Feasible"].append(True)

            d = extra.copy()
            d.pop("Names")
            newD = pd.DataFrame(d, index = extra["Names"])
            newDf = pd.concat([df, newD])

            self._populateCoefficientsTable_(newDf)

            # return newDf
        # pass

    @Slot()
    def _slot_removeRowsForStarredCoeffs(self): # TODO: 2026-01-21 12:43:27
        if self._nStarredCoeffs_ == 0:
            return

        if self._nStarredGroups_ == 1:
            # ensure there is at least one
            return

        df = self._model_fit_coefficients_
        newDf = df.iloc[:len(df.index)-self._nStarredCoeffs_, :]
        self._nStarredGroups_ -= 1

        self.removeStarredRowsPushButton.setEnabled(self._nStarredCoeffs_ > 0 and self._nStarredGroups_ > 1)
        self._populateCoefficientsTable_(newDf)
        # pass

    @Slot()
    def _slot_generateWaveform(self):
        self.generateWaveform()


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
        qc = small_widgets.QuantityChooserWidget(parent=dlg)
        qc.units = units
        dlg.addWidget(qc)
        if dlg.exec():
            self.waveformUnits = qc.units
            
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

    @Slot(object)
    def _slot_waveformDurationChanged(self, val:typing.Union[pq.Quantity, float, int, np.float64, np.int64]):
        # print(f"{self.__class__.__name__}._slot_waveformStartChanged({val})")
        duration = self._waveformDuration_

        if isinstance(val, pq.Quantity):
            assert(val.size == 1), "Expecting a scalar Quantity"
            duration = val

        elif isinstance(val, (float, np.float64, int, np.int64)):
            duration = val * self._waveformDuration_.units

        else:
            raise TypeError(f"Wrong value type ({type(val).__name__})")

        self.waveformDuration = duration

    @Slot(object)
    def _slot_waveformSamplingRateChanged(self, val:typing.Union[pq.Quantity, float, int, np.float64, np.int64]):
        # print(f"{self.__class__.__name__}._slot_waveformStartChanged({val})")
        rate = self._waveformSamplingRate_
        
        if isinstance(val, pq.Quantity):
            assert(val.size == 1), "Expecting a scalar Quantity"
            rate = val
            
        elif isinstance(val, (float, np.float64, int, np.int64)):
            rate = val * self._waveformSamplingRate_.units
            
        else:
            raise TypeError(f"Wrong value type ({type(val).__name__})")
        
        self.waveformSamplingRate = rate
        
    @property
    def waveformUnits(self) -> pq.Quantity | None:
        return self._waveformUnits_

    @waveformUnits.setter
    def waveformUnits(self, val:typing.Optional[pq.Quantity]):
        if not isinstance(val, pq.Quantity):
            self._waveformUnits_ = None
        else:
            self._waveformUnits_ = val.units
            
        if self._waveformUnits_ is None or (isinstance(self._waveformUnits_, pq.Quantity) and self._waveformUnits_.units == pq.dimensionless):
            self.unitsLabel.setText("")
            self.unitsLabel.setToolTip("Dimensionless")
        else:
            symbol = scq.shortSymbol(self._waveformUnits_)
            self.unitsLabel.setText(symbol)
            self.unitsLabel.setToolTip(symbol)
            
