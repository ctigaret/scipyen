# $Id: modelfittingwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Widget for model parameter inputs
"""
import math, numbers, typing, os, types, sys, traceback, warnings, itertools, io # noqa

import numpy as np
import quantities as pq
import pandas as pd
import neo
from scipy import optimize

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

import matplotlib as mpl

from matplotlib import pyplot as plt

from core.strutils import (str2symbol, is_svg, str2svg, get_int_sfx)
from core import models
from core import scipyen_quantities as scq
from core import datasignal
from core.datasignal import DataSignal
from core import neoutils
from core import curvefitting as crvf

from iolib import pictio as pio
from gui import guiutils, workspacegui
import gui.quickdialog as qd
from gui.widgets.small_widgets import QuantitySpinBox

__module_path__ = os.path.abspath(os.path.dirname(__file__))
try:
    # from gui.widgets.modelfittingwidget_ui import Ui_ModelFittingWidget
    from gui.widgets.ModelFittingWidget_ui import Ui_ModelFittingWidget

except:
    Ui_ModelFittingWidget, _ = loadUiType(os.path.join(__module_path__, "ModelFittingWidget.ui"))

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


class ModelFittingWidget(Ui_ModelFittingWidget, QtWidgets.QWidget, workspacegui.GuiMessages):
    # NOTE: 2026-01-21 10:44:11 TODO URGENT
    # Currently inserting rows for starred coefficients is implemented by means
    # of redefining the coefficients data frame
    # In the (near) future I should try to implement this in the TabularDataModel
    # used by the TableEditorWidget
    sig_waveformReady = Signal(object, name="sig_waveformReady")

    def __init__(self, model: types.FunctionType|None = None,
                 data:typing.Optional[neo.AnalogSignal | DataSignal] = None,
                 duration:pq.Quantity = 1*pq.dimensionless,
                 start:pq.Quantity = 0*pq.dimensionless,
                 samplingRate:pq.Quantity = 1e4*pq.dimensionless,
                 coefficients:typing.Optional[typing.Union[pd.DataFrame, dict]] = None,
                 waveformUnits:typing.Optional[pq.Quantity]=None,
                 waveViewer:typing.Optional[typing.Union[mpl.figure.Figure, QtWidgets.QMainWindow]] = None,
                 # initial = None,
                 # lbubkf = None,
                 parent=None,
                 **kwargs):
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
        QtWidgets.QWidget.__init__(self, parent=parent)
        # super(Ui_ModelFittingWidget, self).__init__()

        self._nStarredCoeffs_:int = 0
        self._nStarredGroups_:int = 0
        self._destarredCoeffs_:typing.Sequence = list()

        self._data_:typing.Optional[neo.AnalogSignal | DataSignal] = None
        self._dataChannel_:int = 0

        self._fittedCurve_: np.ndarray | None = None
        self._modelWaveform_: np.ndarray | None = None
        self._fitResult_: types.SimpleNamespace | None = None
        # self._use_fitted_: bool = False

        self._plot_data_overlaid_: bool = False

        self._model_: types.FunctionType | None = None

        self._model_fit_coefficients_: pd.DataFrame | None = None

        self._model_name_: str | None = None
        self._model_expression_svg_: QtGui.QPixmap | None = None
        self._waveformStart_: typing.Optional[pq.Quantity] = None
        self._waveformDuration_:typing.Optional[pq.Quantity] = None
        self._waveformSamplingRate_:typing.Optional[pq.Quantity] = None
        self._waveformUnits_:typing.Optional[pq.Quantity] = None
        self._model_expression_window_:typing.Optional[QtWidgets.QMainWindow] = None
        self._expressionWindow_:typing.Optional[QtWidgets.QMainWindow] = None

        self._decimals_ = kwargs.pop("decimals", None)

        if not isinstance(self._decimals_, int) or self._decimals_ < 0:
            self._decimals_ = None

        self._configureUI_()

        self._waveViewer_ = waveViewer if (isinstance(waveViewer, mpl.figure.Figure) or (isinstance(waveViewer, QtWidgets.QMainWindow) and type(waveViewer).__name__ == "SignalViewer")) else None

        # if initial is None:
        #     initial = list()
        #
        # if lbubkf is None:
        #     lbubkf = dict()

        if isinstance(model, types.FunctionType):
            self._setModelData_(model, data, start, duration, samplingRate, waveformUnits, coefficients)# , *initial, **lbubkf)

            if isinstance(self._model_fit_coefficients_, pd.DataFrame):
                self._populateCoefficientsTable_(self._model_fit_coefficients_)

    def _configureUI_(self):
        from gui.guiutils import svg2pixmap
        self.setupUi(self)
        dsvg = str2svg("1:1", 16, 16, x=8, y=15, font_size=16,
                       text_anchor="middle",
                       dominant_baseline="hanging").as_svg()
        pix = svg2pixmap(dsvg)
        if not pix.isNull():
            self.makeUnitAmplitudePushButton.setIcon(QtGui.QIcon(pix))
            self.makeUnitAmplitudePushButton.setText("")
        else:
            self.makeUnitAmplitudePushButton.setText("Unit Amplitude")
        self.makeUnitAmplitudePushButton.setFlat(True)

        dsvg = str2svg("SI", 16, 16, x=8, y=15, font_size=16,
                       text_anchor="middle",
                       dominant_baseline="hanging").as_svg()
        pix = svg2pixmap(dsvg)
        if not pix.isNull():
            self.waveformUnitsPushButton.setIcon(QtGui.QIcon(pix))
            self.waveformUnitsPushButton.setText("")
        else:
            self.waveformUnitsPushButton.setText("Change")
        self.waveformUnitsPushButton.setFlat(True)

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
        self.fitDataPushButton.clicked.connect(self._slot_fitData)
        self.channelSpinBox.valueChanged.connect(self._slot_dataChannelChanged_)

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
        self.channelSpinBox.setVisible(False)

        self.overlayDataCheckbox.setChecked(self._plot_data_overlaid_)
        self.overlayDataCheckbox.setEnabled(False)

        self.overlayDataCheckbox.toggled.connect(self._slot_setDataOverlay_)
        self.modelCoefficientsTable.enforceFloat = False
        self.modelCoefficientsTable.readOnly = False

        self.setAsX0ToolButton.clicked.connect(self._slot_setWaveStartAsX0)
        self.setAsX0ToolButton.setEnabled(False)

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
        csizes = self.controlsSplitter.sizes()
        # print(f"{self.__class__.__name__}._configureUI_: csizes = {csizes}")
        csizes[-1] = self.modelCoefficientsTable.size().width()
        csizes[0] = (self.size().width() - self.modelCoefficientsTable.size().width()) // 2
        # print(f"{self.__class__.__name__}._configureUI_: csizes adjusted = {csizes}")
        self.controlsSplitter.setSizes(csizes)

        # self.exportModelWaveformToolButton.setEnabled(False)
        self.exportModelWaveformToolButton.clicked.connect(self._slot_exportModelWaveform)

        self.exportFitResultPushButton.setEnabled(False)
        self.exportFitResultPushButton.clicked.connect(self._slot_exportFitResult)

        self.exportFitCurveToolButton.setEnabled(False)
        self.exportFitCurveToolButton.clicked.connect(self._slot_exportFittedCurve)

    def _setModelData_(self, model:types.FunctionType,
                       data:typing.Optional[neo.AnalogSignal | DataSignal] = None,
                       start:pq.Quantity=0*pq.dimensionless,
                       duration:pq.Quantity=1*pq.dimensionless,
                       samplingRate:pq.Quantity=1e4*pq.dimensionless,
                       waveformUnits:pq.Quantity = pq.dimensionless,
                       coefficients:typing.Optional[typing.Union[dict, pd.DataFrame]] = None,
                       ):
        assert isinstance(start, pq.Quantity) and start.size==1, f"'duration' must be a scalar quantity; instead, got {start}"
        assert isinstance(duration, pq.Quantity) and duration.size==1, f"'duration' must be a scalar quantity; instead, got {duration}"
        assert isinstance(samplingRate, pq.Quantity) and samplingRate.size==1 and samplingRate.units == 1/duration.units, f"'samplingRate' must be a scalar quantity in units of, or convertible to, {1/duration.units}; instead, got {samplingRate}"
        assert (isinstance(waveformUnits, pq.Quantity) and waveformUnits.size==1) or waveformUnits is None, f"'waveformUnits' , must be a scalar quantity or None; instead, gor {waveformUnits}"

        assert models.isModelFunction(model), f"Expecting a model function — which is NOT a regular Python function; instead, got {model}"

        if isinstance(data, (neo.AnalogSignal, DataSignal)):
            self.setData(data)
            self._fitResult_ = None
            self.exportFitResultPushButton.setEnabled(False)

        elif not isinstance(self._data_, (neo.AnalogSignal, DataSignal)):
            # NOTE: 2026-05-06 11:37:56
            # upon changing the model when curve data is already set, leave the
            # wave controls unchanged
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
            else:
                waveformUnits = pq.dimensionless

            self._data_ = None
            self._fitResult_ = None
            self.exportFitResultPushButton.setEnabled(False)
            self.fitDataPushButton.setEnabled(False)

            self._waveformStart_ = start
            self._waveformDuration_ = duration
            self._waveformSamplingRate_ = samplingRate
            self._waveformUnits_ = waveformUnits

            self._populate_WaveControls_()

        self._setModelFunction_(model, coefficients)# , *initial, **lbubkf)

    def _populate_WaveControls_(self):
        domainUnitsFamily = scq.getUnitFamily(self._waveformDuration_)
        if domainUnitsFamily == "Time":
            self._waveformSamplingRate_.rescale(pq.Hz)

        elif domainUnitsFamily in ("Length", "Space"):
            self._waveformSamplingRate_.rescale(pq.space_frequency_unit)

        elif domainUnitsFamily == "Angle" or self._waveformDuration_.units == pq.rad:
            self._waveformSamplingRate_.rescale(pq.angle_frequency_unit)

        else:
            self._waveformSamplingRate_.rescale(1/self._waveformDuration_.units)

        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), [self.startSpinBox, self.durationSpinBox, self.samplingRateSpinBox]))#, self.waveformUnitsChooser])) # noqa
        # print(f"{self.__class__.__name__}._populate_WaveControls_:")
        # print(f"\t\tself._waveformStart_ -> {self._waveformStart_}")
        # print(f"\t\tself._waveformDuration_ -> {self._waveformDuration_}")
        # print(f"\t\tself._waveformSamplingRate_ -> {self._waveformSamplingRate_}")
        # print(f"\t\tself._waveformUnits_ -> {self._waveformUnits_}")
        decimals = len(f"{float(self._waveformStart_)}".split(".")[-1]) + 2
        self._decimals_ = decimals
        self.startSpinBox.setDecimals(decimals)
        self.startSpinBox.setValue(self._waveformStart_)
        self.durationSpinBox.setDecimals(decimals)
        self.durationSpinBox.setValue(self._waveformDuration_)
        self.samplingRateSpinBox.setDecimals(decimals)
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)
        self.waveformUnits = self._waveformUnits_ # will also set up the unitsLabel
        self.modelCoefficientsTable.decimals = self._decimals_


    def _setModelFunction_(self, model:types.FunctionType, coefficients=None):
        # from core.strutils import is_svg
        assert models.isModelFunction(model), f"Expecting a model function — which is NOT a regular Python function; instead, got {model}"
        self._model_ = model
        self._model_name_ = model.title

        self.modelNameLabel.setText(f"{self._model_name_} model formula: ↴")
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

        fitting_df = self._parseModelCoefficients_(model, coefficients) #, *initial, **lbupkf)

        # print(f"{self.__class__.__name__}._setModelFunction_: fitting_df = {fitting_df}")

        if isinstance(fitting_df, pd.DataFrame):
            self._model_fit_coefficients_ = fitting_df
            self._populateCoefficientsTable_(self._model_fit_coefficients_)
            self.setAsX0ToolButton.setEnabled("x0" in self._model_fit_coefficients_.index)

        self._generateModelExpressionSVG()

        self._setupExpressionWindow()

        self.addStarredRowsPushButton.setEnabled(self._nStarredCoeffs_ > 0)
        self.removeStarredRowsPushButton.setEnabled(self._nStarredCoeffs_ > 0 and self._nStarredGroups_ > 1)

        self._fitResult_ = None
        self.exportFitResultPushButton.setEnabled(False)


    def _parseModelCoefficients_(self, model:types.FunctionType,
                                 coefficients:typing.Optional[typing.Union[pd.DataFrame, dict]]=None) -> pd.DataFrame:
        assert models.isModelFunction(model), f"Expecting a model function — which is NOT a regular Python function; instead, got {model}"
        ret = pd.DataFrame()

        if isinstance(coefficients, pd.DataFrame):
            assert all(v in list(coefficients.columns) for v in ("Initial Value", "Lower Bound", "Upper Bound", "Keep Feasible")), f"Invalid coefficients given {coefficients}"
            initial = list(coefficients["Initial Value"])
            if len(model.coefficients):
                self._nStarredCoeffs_ = len(model.starred_coefficients)
                self._nStarredGroups_ = model.starredRepeats(*initial)
                destarred = list(map(lambda c: c.strip("*"), model.starred_coefficients))
                self._destarredCoeffs_ = tuple(itertools.chain.from_iterable(map(lambda k: tuple(map(lambda c: f"{c}{k}", destarred)), range(self._nStarredGroups_))))
            else:
                self._nStarredCoeffs_ = 0
                self._destarredCoeffs_= list()
                self._nStarredGroups_ = 0

            ret = coefficients

        else:
            if isinstance(coefficients, dict):
                names = coefficients.get("names", list()),
                if len(names):
                    fd = {"Initial Value": coefficients.get("initial", list()),
                        "Lower Bound": coefficients.get("lower", list()),
                        "Upper Bound": coefficients.get("upper", list()),
                        "Keep Feasible": coefficients.get("feasible", list())}

                    # NOTE: 2026-01-21 13:18:29
                    # same as for NOTE: 2026-01-21 13:14:04 above
                    ret = pd.DataFrame(fd, index = (names))

            elif len(model.coefficients):
                starred = model.starred_coefficients
                if models.isFittingCoefficientsDict(model.fitting):
                    initial = model.fitting["initial"]
                    lbubkw = {"lower": model.fitting["lower"], "upper": model.fitting["upper"]}
                else:
                    initial = tuple()
                    lbubkw = dict()

                ret, destarred, starredGroups, all_names = model.generateFitTable(*initial, **lbubkw)

                self._nStarredCoeffs_ = len(model.starred_coefficients)
                self._destarredCoeffs_= destarred
                self._nStarredGroups_ = starredGroups

            else:

                self._nStarredCoeffs_ = 0
                self._destarredCoeffs_= list()
                self._nStarredGroups_ = 0


        # print(f"{self.__class__.__name__}._parseModelCoefficients_: ret -> {ret}")

        return ret

    def _generateModelExpressionSVG(self):
        worker = _ModelFunctionExpressionSVGGenerator_(self._model_, parent=self)
        worker.ready.connect(self._slot_modelExpressionGenerated)
        worker.run()
        worker.deleteLater()

    @Slot(str)
    def _slot_modelExpressionGenerated(self, svg: str|None):
        self._model_expression_svg_ = svg
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
    def modelWaveform(self):
        return self.generateModelWaveform()

    @property
    def model(self) -> types.FunctionType:
        return self._model_

    def setData(self, val:typing.Optional[typing.Union[
                                            neo.AnalogSignal,
                                            DataSignal,
                                            np.ndarray
                                            ]
                                         ] = None) -> None:
        # print(f"\n{self.__class__.__name__}.setData({type(val).__name__})\n")
        sigBlock = QtCore.QSignalBlocker(self.channelSpinBox)
        if not isinstance(val, (neo.AnalogSignal, DataSignal, np.ndarray)):
            self._data_ = None
            self._dataChannel_ = 0
            self.channelSpinBox.setMinimum(0)
            self.channelSpinBox.setMaximum(0)
            self.channelSpinBox.setValue(self._dataChannel_)

            self.channelSpinBox.setEnabled(False)
            self.channelSpinBox.setVisible(False)
            self.fitDataPushButton.setEnabled(False)
            self.overlayDataCheckbox.setEnabled(False)
            self.overlayDataCheckbox.setChecked(False)

            return

        if val.size == 0:
            raise ValueError("Received an empty signal!")

        start = val.t_start
        duration = val.duration
        samplingRate = val.sampling_rate
        waveformUnits = val.units

        if val.ndim == 1 or (val.ndim==2 and val.shape[1] > 0):
            self._dataChannel_ = 0
            self.channelSpinBox.setMinimum(0)
            self.channelSpinBox.setMaximum(0)
            self.channelSpinBox.setValue(0)
            self.channelSpinBox.setVisible(False)
            self.channelSpinBox.setEnabled(False)
            self.fitDataPushButton.setEnabled(True)

        elif val.ndim == 2:

            if self._dataChannel_ < -val.shape[1]:
                self._dataChannel_ = -val.shape[-1]

            elif self._dataChannel_ >= val.shape[-1]:
                self._dataChannel_ = val.shape[-1]-1

            self.channelSpinBox.setMinimum(-val.shape[1])
            self.channelSpinBox.setMaximum(val.shape[1]-1)

            self.channelSpinBox.setVisible(True)
            self.channelSpinBox.setEnabled(True)
            self.fitDataPushButton.setEnabled(True)
            self.channelSpinBox.setValue(self._dataChannel_)
            self.overlayData.setEnabled(True)
        else:
            raise ValueError("Data with more than two dimensions is not supported")

        self._data_ = val
        self._waveformStart_ = start
        self._waveformDuration_ = duration
        self._waveformSamplingRate_ = samplingRate
        self._waveformUnits_ = waveformUnits

        self._populate_WaveControls_()

        self.overlayDataCheckbox.setEnabled(True)
        self.overlayDataCheckbox.setChecked(False)

        self._fitResult_ = None
        self.exportFitResultPushButton.setEnabled(False)

    def setModel(self, model:types.FunctionType, coefficients: typing.Optional[pd.DataFrame] = None):
        if models.isModelFunction(model):
            if not isinstance(coefficients, pd.DataFrame):
                if models.isFittingCoefficientsDict(model.fitting):
                    d = {"Initial Value": model.fitting["initial"],
                        "Lower Bound": model.fitting["lower"],
                        "Upper Bound": model.fitting["upper"],
                        "Keep Feasible": model.fitting["feasible"]}
                    coefficients = pd.DataFrame(d, index = model.fitting["names"])
                else:
                    coefficients, variadics, groups, coefnames = model.generateFitTable()

            if all(v in coefficients.columns for v in ("Initial Value", "Lower Bound", "Upper Bound", "Keep Feasible")):
                # print(f"{self.__class__.__name__}.setModel {model.__name__  } -> coefficients =\n{coefficients}\n({type(coefficients).__name__})")
                self._setModelData_(model, coefficients=coefficients)
                self._model_fit_coefficients_ = coefficients
                self._populateCoefficientsTable_(self._model_fit_coefficients_)
            else:
                raise ValueError("Invalid coefficients DataFrame")
        else:
            raise ValueError("'model' is not a model function")

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
        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), blockedWidgets))#, self.waveformUnitsChooser])) # noqa
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

        signalBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), [self.samplingRateSpinBox]))#, self.waveformUnitsChooser])) # noqa
        self.samplingRateSpinBox.setValue(self._waveformSamplingRate_)

    @property
    def waveViewer(self) -> typing.Optional[mpl.figure.Figure | QtWidgets.QMainWindow]:
        return self._waveViewer_

    @waveViewer.setter
    def waveViewer(self, val:typing.Optional[typing.Union[mpl.figure.Figure, QtWidgets.QMainWindow]]=None):
        if val is None or (isinstance(val, QtWidgets.QMainWindow) and type(val).__name__ == "SignalViewer") or isinstance(val, mpl.figure.Figure):
            self._waveViewer_ = val

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
        self.modelCoefficientsTable.decimals = self._decimals_
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

    def generateModelWaveform(self, *coeffs) -> neo.basesignal.BaseSignal | None:
        if not isinstance(self._model_, types.FunctionType) or not models.isModelFunction(self._model_):
            return

        try:
            self._waveformStart_ = self.startSpinBox.value()
            self._waveformDuration_ = self.durationSpinBox.value()
            self._waveformSamplingRate_ = self.samplingRateSpinBox.value()
            x = self._generateWaveformDomain_()
            coeffs = coeffs or self.coefficientValues
            # coeffs = list(self._model_fit_coefficients_["Initial Value"])

            with warnings.catch_warnings(record=True) as wrn:
                y = self._model_(x, coeffs)

            sigUnits = self._waveformUnits_.units if isinstance(self._waveformUnits_, pq.Quantity) else pq.dimensionless
            sigName = f"{self._model_name_} model"

            name = f"{self._model_name_} model" if  self._waveformUnits_.units==pq.dimensionless else f"{scq.unitFamilyName(self._waveformUnits_.units)}"

            # if sig.units != pq.dimensionless.units:
            #     sig.name = scq.unitFamilyName(sig.units)

            if scq.unitsConvertible(self._waveformUnits_.units, pq.V):
                sigName = "Potential"

            if scq.checkTimeUnits(self._waveformDuration_):
                sig = neo.AnalogSignal(y, t_start = self._waveformStart_, units = sigUnits, sampling_rate=self._waveformSamplingRate_, name=name, codomain_name=sigName)

            else:
                sig = datasignal.DataSignal(y, t_start = self._waveformStart_, units = sigUnits, domain_units = self._waveformDuration_.units,
                                        sampling_rate=self._waveformSamplingRate_, name=name, codomain_name=sigName)


            sig.array_annotate(channel_names = [f"Realization of {self._model_.title}"])

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

        return sig

    def generateWaveform(self, fitted:bool = False) -> neo.basesignal.BaseSignal | None:
        r"""Generates curve for the model using intial or the fitted coefficients.
    """
        from gui.guiutils import getScipyenMainWindow

        if not isinstance(self._model_, types.FunctionType) or not models.isModelFunction(self._model_):
            return

        try:
            yData = None
            if isinstance(self._data_, (neo.AnalogSignal, DataSignal)):
                yData = self._data_

                if "channel_names" not in yData.array_annotations:
                    yData.array_annotate(channel_names = list(map(lambda k: f"Channel {k}", range(yData.shape[1]))))

            # if self._use_fitted_:
            if fitted is True:
                if isinstance(yData, (neo.AnalogSignal, DataSignal)) and isinstance(self._fittedCurve_, np.ndarray) and self._fittedCurve_.shape[0] == yData.shape[0]:
                    name = yData.name
                    if not isinstance(name, str) or len(name.strip()):
                        name = f"Model fit through data"
                    else:
                        name = f"Model fit through {name}"

                    y_ = type(yData)(self._fittedCurve_, units = yData.units,
                                    t_start = yData.t_start,
                                    sampling_rate = yData.sampling_rate,
                                    name = f"{self._model_.title} model fit through {yData.name}")

                    y_.array_annotate(channel_names = [f"Fitted data channel {self._dataChannel_}"])

                elif isinstance(self._fitResult_, types.SimpleNamespace):
                    y_ = self.generateModelWaveform(self._fitResult_.Coefficients.Fitted)
                    y_.name = f"{self._model_.title} model fit"
                    y_.array_annotate(channel_names = ["Fitted data channel"])
            else:
                y_ = self.generateModelWaveform()

            # print(f"{self.__class__.__name__}.generateWaveform: yData: {type(yData).__name__}, y_: {type(y_).__name__}")

            if isinstance(yData, (neo.AnalogSignal, DataSignal)) and self._plot_data_overlaid_ :
                sig = neoutils.concatenate_signals(yData, y_, axis=1)
                # if self._use_fitted_:
                if fitted is True:
                    placeHolder = f"{self._model_.title} fit"

                else:
                    placeHolder = f"{self._model_.title} model"

                name = yData.name if isinstance(yData.name, str) and len(yData.name) else yData.annotations.get("codomain_name", None)

                yDataName = f"{name if (isinstance(name, str) and len(name.strip())) else "Data"} + {placeHolder}"
                # y_Name = f"{self._model_.title} fit" if (not isinstance(y_.name, str) or len(y_.name.strip()) == 0) else y_.name
                # sig.name = f"Overlay of {yDataName} and {y_.name}"
                sig.name = yDataName
                sig.array_annotate(**neoutils.merge_array_annotations(yData.array_annotations,
                                                                      y_.array_annotations))
            else:
                sig = y_

        except: # noqa
            traceback.print_exc()
            exc = sys.exception()
            msg = "".join(traceback.format_exception_only(exc))
            self.errorMessage(type(exc).__name__, msg)
            return

        if isinstance(sig, neo.basesignal.BaseSignal):
            self.sig_waveformReady.emit(sig)

            if __has_PySide6__:
                receivers = self.receivers("sig_waveformReady")
            else:
                receivers(self.sig_waveformReady)

            if receivers == 0:
                if isinstance(self._waveViewer_, mpl.figure.Figure):
                    plt.figure(self._waveViewer_)
                    plt.plot(sig)

                elif isinstance(self._waveViewer_, QtWidgets.QMainWindow):
                    self._waveViewer_.view(sig)

                else:
                # if self._waveViewer_ is None:
                    varname = f"{self._model_name_}_waveform" if isinstance(self._model_name_, str) and len(self._model_name_.strip()) else "model_waveform"
                    # getScipyenMainWindow().assignToWorkspace(varname, sig)

            return sig

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
            groupsList = sorted(list(grset))
            lastGroup = groupsList[-1]

            nextGroupNdx = len(groupsList)# lastGroup +1
            self._nStarredGroups_ += 1

            self.removeStarredRowsPushButton.setEnabled(self._nStarredCoeffs_ > 0 and self._nStarredGroups_ > 1)

            print(f"{self.__class__.__name__}._slot_addRowsForStarredCoeffs: groups = {groups}, lastGroup = {lastGroup},  nextGroupNdx = {nextGroupNdx}")

            extra = {"Names": list()}
            extra.update(dict(map(lambda k: (k, list()), df.columns)))

            for ds in self._destarredCoeffs_:
                extra["Names"].append(f"{ds}{nextGroupNdx}")
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

    @Slot(bool)
    def _slot_setDataOverlay_(self, val:bool):
        self._plot_data_overlaid_ = val is True

    @Slot()
    def _slot_generateWaveform(self):
        # self._use_fitted_ = False
        self.generateWaveform()

    @Slot()
    def _slot_setWaveStartAsX0(self):
        x0 = self.startSpinBox.value()
        if isinstance(x0, pq.Quantity):
            x0 = float(x0.flatten()[0].magnitude)
        self._model_fit_coefficients_.loc["x0", "Initial Value"] = x0


    @Slot(int)
    def _slot_dataChannelChanged_(self, val:int):
        if not isinstance(val, int) or val < 0:
            self._dataChannel_ = 0
        else:
            self._dataChannel_ = val

    @property
    def dataChannel(self) -> int:
        return self._dataChannel_

    @dataChannel.setter
    def dataChannel(self, val:int):
        print(f"{self.__class__.__name__}.dataChannel.setter({val})")
        if not isinstance(val, int):
            raise TypeError(f"Expecting an int; got {type(val).__name__} instead")

        if self._data_:
            if self._data_.ndim ==1 or self._data_.ndim==2 and self._data_.shape[1] == 1:
                if val != 0:
                    raise ValueError(f"Wrong channel index {val} for 1D data or a singleton second dimension")

            elif val < -self._data_.shape[1] or val >= self._data_.shape[1]:
                raise ValueError(f"Wrong channel index {val}. New channel index must be between {-self._data_.shape[1]} and {self._data_.shape[1]-1}")
        else:
            if val != 0:
                raise ValueError(f"In the absence of data the channel can only be 0")

        self._dataChannel_ = val
        signalBlock = QtCore.QSignalBlocker(self.channelSpinBox)
        self.channelSpinBox.setValue(self._dataChannel_)

    @Slot()
    def _slot_fitData(self):
        self._fitResult_ = None
        if not isinstance(self._data_, (neo.AnalogSignal, DataSignal)) or self._data_.size == 0:
            return

        if not models.isModelFunction(self._model_):
            return

        fitParams = self._model_fit_coefficients_
        if not isinstance(fitParams, pd.DataFrame) or \
            not all(v in fitParams.columns for v in ("Initial Value", "Lower Bound", "Upper Bound", "Keep Feasible")) or \
                fitParams.size == 0:
            return

        if self._data_.ndim==2 and self._data_.shape[1] > 1:
            if self._dataChannel_ not in range(-self._data_.shape[1], self._data_.shape[1]):
                return

            data = self._data_[:,self._dataChannel_].flatten().magnitude

        else:
            data = self._data_.flatten().magnitude

        x = self._data_.times.flatten().magnitude

        p0 = list(fitParams["Initial Value"])
        lb = list(fitParams["Lower Bound"])
        ub = list(fitParams["Upper Bound"])
        kf = list(fitParams["Keep Feasible"])

        bounds = optimize.Bounds(lb=lb, ub=ub, keep_feasible = kf)

        try:
            self._fittedCurve_, self._fitResult_ = crvf.fit_model(data, self._model_, p0, x = x, bounds=bounds)

        except Exception as e:
            print(e)
            with io.StringIO() as bf:
                traceback.print_exc(file=bf)
                msg = bf.getvalue()
                eType = type(e).__name__
                eMsg = str(e)
                self.detailedMessage(f"Curve Fitting {eType}", eMsg, detail = msg)

        if self._fitResult_:
            self._model_fit_coefficients_["Fitted"] = self._fitResult_.Coefficients.Fitted
            self._populateCoefficientsTable_(self._model_fit_coefficients_)
            fitInfo  = [
                        f"message:\t{self._fitResult_.Fit.message}",
                        f"success:\t{self._fitResult_.Fit.success}",
                        f"cost:\t{self._fitResult_.Fit.cost}",
                        f"optimality:\t{self._fitResult_.Fit.optimality}",
                        ]
            fitInfo += list(map(lambda i: f"{i[0]}:\t{i[1]}", self._fitResult_.Coefficients.GoF.__dict__.items()))

            self.fitResultsTextEdit.setPlainText ("\n".join(fitInfo))
            # self._use_fitted_ = True
            self.generateWaveform(True)
            self.exportFitResultPushButton.setEnabled(True)
            self.exportFitCurveToolButton.setEnabled(True)

        else:
            self.fitResultsTextEdit.setPlainText("")
            self.exportFitResultPushButton.setEnabled(False)
            self.exportFitCurveToolButton.setEnabled(False)

    @Slot()
    def _slot_exportModelWaveform(self):
        from gui.guiutils import getScipyenMainWindow, getEnclosingQMainWindow
        from gui.workspacegui import WorkspaceGuiMixin

        wave = self.generateModelWaveform()
        if isinstance(wave, np.ndarray):
            varname = f"{self._model_name_}_modelCurve" if isinstance(self._model_name_, str) and len(self._model_name_.strip()) else "modelCurve"

            ancestorWindow = getEnclosingQMainWindow(self)
            if isinstance(ancestorWindow, WorkspaceGuiMixin):
                ancestorWindow.exportDataToWorkspace(wave, varname,
                                                        title="Export Model Curve")
            else:
                getScipyenMainWindow().assignToWorkspace(varname, wave)

    @Slot()
    def _slot_exportFittedCurve(self):
        from gui.guiutils import getScipyenMainWindow, getEnclosingQMainWindow
        from gui.workspacegui import WorkspaceGuiMixin

        wave = self.generateWaveform(True)
        if isinstance(wave, np.ndarray):
            varname = f"{self._model_name_}_fittedCurve" if isinstance(self._model_name_, str) and len(self._model_name_.strip()) else "fittedCurve"

            ancestorWindow = getEnclosingQMainWindow(self)
            if isinstance(ancestorWindow, WorkspaceGuiMixin):
                ancestorWindow.exportDataToWorkspace(wave, varname,
                                                     title="Export Fitted Curve")
            else:
                getScipyenMainWindow().assignToWorkspace(varname, wave)

    @Slot()
    def _slot_exportFitResult(self):
        from gui.guiutils import getScipyenMainWindow, getEnclosingQMainWindow
        from gui.workspacegui import WorkspaceGuiMixin
        if isinstance(self._fitResult_, types.SimpleNamespace):
            varname = f"{self._model_name_}_fitResult" if isinstance(self._model_name_, str) and len(self._model_name_.strip()) else "fitResult"

    @Slot()
    def _slot_makeUnitAmplitudeModel(self):
        # TODO 2026-05-06 11:49:36 FIXME
        # finalize this!!!
        if not isinstance(self._model_, types.FunctionType) or not models.isModelFunction(self._model_):
            return

    @Slot()
    def _slot_pythonHelpForModel(self):
        from gui import guiutils
        if not isinstance(self._model_, types.FunctionType) or not models.isModelFunction(self._model_):
            return

        mainWindow = guiutils.getScipyenMainWindow()
        mainWindow.runPythonHelpGUI(f"{self._model_.__module__}.{self._model_.__name__}") # BUG 2026-05-05 23:25:59 in pythonhelpviewer FIXME

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
    def fitResult(self) -> types.SimpleNamespace | None:
        r"""The result of the curve fitting; read-only"""
        return self._fitResult_

    @property
    def fittedCurve(self) -> np.ndarray | None:
        return self._fittedCurve_

    @property
    def overlayData(self) -> bool:
        return self._plot_data_overlaid_

    @overlayData.setter
    def overlayData(self, val:bool):
        self._plot_data_overlaid_ = val is True
        sigBlock = QtCore.QSignalBlocker(self.overlayDataCheckbox)
        self.overlayDataCheckbox.setChecked(self._plot_data_overlaid_)

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

    @property
    def decimals(self) -> int | None:
        return self._decimals_

    @decimals.setter
    def decimals(self, val: int | None = None):
        if isinstance(val, int) and val >= 0:
            self._decimals_ = val
        else:
            self._decimals_ = None
