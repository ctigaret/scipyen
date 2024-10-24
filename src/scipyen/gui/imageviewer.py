# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

'''
Image viewer: designed for viewing vigra arrays (primarily)
Based on GraphicsView Qt framework
Supports cursors defined in pictgui module.
Dependencies:
python >= 3.4
PyQt5
vigra built python 3)
boost C++ libraries built against python 3 (for building vigra against python3)
numpy (for python 3)
quantities (for python 3)
matplotlib for colormaps & colors

'''

# NOTE: 2017-05-25 08:47:01
# TODO:
# 1. colormap editor
# 
# 2. DONE remember last applied colormap or rather make a default colormap configurable
# 
# 3. cursors:
#
# 3.1. really constrain the movement of cursors within the image boundaries; -- DONE
# 
# 3.2. implement edit cursor properties dialog NEARLY DONE
# 
# 3.3. streamline cursor creation from a neo.Epoch -- check if they support
#      spatial units, not just time -- it apparently DOES WORK:
# 
#      epc = neo.Epoch(times=[15, 20, 25], durations=[5, 5, 5], labes=["r0", "r1", "r2"], units=pq.um, name="SpineROIs")
# 
# 
# 3.4  implement the reverse operation of generating an epoch from an array of 
#      cursors
#
# 3.5 for 3.3 and 3.4 be mindful that we can have epochs in BOTH directions, in
#      an image -- I MIGHT contemplate "epochs" in the higher dimensions, for where 
#      this makes sense
# 
# 
# 4. ROIs: probably the best approach is to inherit from QGraphicsObject, see GraphicsObject
# 

#### BEGIN core python modules
from __future__ import print_function
import sys, os
import numbers, traceback, inspect, threading, warnings, typing, math
import weakref, copy, itertools
from functools import partial
from enum import Enum, IntEnum
from dataclasses import MISSING
#### END core python modules

#### BEGIN 3rd party modules
from traitlets import Bunch
import numpy as np
import quantities as pq
from gui.pyqtgraph_patch import pyqtgraph as pgraph
import neo
from core.vigra_patches import vigra
from pandas import NA
#from core.vigra_patches import vigra.pyqt 
import matplotlib as mpl

from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__

#### END 3rd party modules

#### BEGIN scipyen core modules
from core import utilities
from core.prog import (safeWrapper, deprecation, iter_attribute,
                       filter_type, filterfalse_type, 
                       filter_attribute, filterfalse_attribute,
                       filter_attr, filterfalse_attr)

from core import strutils as strutils
from core import datatypes  
from core.quantities import quantity2str
from core.traitcontainers import DataBag
from core.scipyen_config import markConfigurable
from core.sysutils import adapt_ui_path

from imaging import (axisutils, axiscalibration, vigrautils as vu,)
from imaging.axisutils import (axisTypeFromString,
                               axisTypeName, 
                               axisTypeSymbol, 
                               axisTypeUnits, )

from imaging.axiscalibration import (AxesCalibration, AxisCalibrationData,)

#from core import neo
#from core import metaclass_solver
#### END scipyen core modules

#### BEGIN scipyen iolib modules
from iolib import pictio as pio
from iolib import h5io
#### END scipyen iolib modules

#### BEGIN scipyen gui modules
from gui.scipyenviewer import (ScipyenViewer, ScipyenFrameViewer)
from gui.graphicsimageviewer import (GraphicsImageViewerScene, 
                                     GraphicsImageViewerWidget)
from gui.colormapeditor import ColorMapEditor


from gui import signalviewer as sv
from gui import pictgui as pgui

# NOTE 2020-11-28 10:04:05
# this should automatically import our custom colormaps AND ocean colormaps if found
from gui import scipyen_colormaps as colormaps 
from gui import quickdialog
from gui.itemslistdialog import ItemsListDialog
#### END scipyen gui modules

# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
__scipyen_plugin__ = None

mpl.rcParams['backend']='Qt5Agg'

#__viewer_info__ = {"alias": "iv", "class": "ImageViewer"}

if sys.version_info[0] >= 3:
    xrange = range

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# __ui_path__ = adapt_ui_path(__module_path__)
    
import qimage2ndarray 
from qimage2ndarray import gray2qimage, array2qimage, alpha_view, rgb_view, byte_view

#Ui_ItemsListDialog, QDialog = __loadUiType__(os.path.join(__module_path__,'itemslistdialog.ui'))

# used for ImageWindow below
Ui_ImageViewerWindow, QMainWindow = __loadUiType__(adapt_ui_path(__module_path__, 'imageviewer.ui'))

Ui_AxesCalibrationDialog, QDialog = __loadUiType__(adapt_ui_path(__module_path__, "axescalibrationdialog.ui"))

Ui_TransformImageValueDialog, QDialog = __loadUiType__(adapt_ui_path(__module_path__,"transformimagevaluedialog.ui"))

class ComplexDisplay(Enum):
    """TODO
    """
    real  = 1
    imag  = 2
    dual  = 3
    abs   = 4
    mod   = 4
    phase = 5
    arg   = 5
    
class IntensityCalibrationLegend(pgraph.graphicsItems.GraphicsWidget.GraphicsWidget):
    def __init__(self, image):
        GraphicsWidget.__init__(self)
        if not isinstance(image, vigra.VigraArray):
            raise TypeError("Expectign a VigraArray; got %s instead" % type(image).__name__)
        
        #if 
        
        w = image.width
        h = image.height
        self.layout = QtGui.QGraphicsGridLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.vb = pgraph.ViewBox(parent=self)
        self.vb.setMaximumWidth(w)
        self.vb.setMinimumWidth(w)
        self.vb.setMaximumHeight(h)
        self.vb.setMinimumHeight(h)
        self.axis = AxisItem('left', linkView=self.vb, maxTickLength=-10, parent=self)
        self.layout.addItem(self.vb, 0, 0)
        self.layout.addItem(self.axis, 0, 1)
        
        
class ImageBrightnessDialog(QDialog, Ui_TransformImageValueDialog):
    """
    """
    signalAutoRange             = Signal(name="signalAutoRange")
    signalDefaultRange          = Signal(name="signalDefaultRange")
    signalApply                 = Signal(name="signalApply")
    signalFactorValueChanged    = Signal(float, name="signalFactorValueChanged")
    signalMinRangeValueChanged  = Signal(float, name="signalMinRangeValueChanged")
    signalMaxRangeValueChanged  = Signal(float, name="signalMaxRangeValueChanged")
    
    
    
    def __init__(self, parent=None, title=None):
        super(ImageBrightnessDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.factorLabel.setText("Brightness")
        
        if title is None:
            self.setWindowTitle("Adjust Brightness")
        else:
            self.setWindowTitle("Adjust Brightness for %s" % title)
            
        
        self.autoRangePushButton.clicked.connect(self.slot_requestAutoRange)
        self.defaultRangePushButton.clicked.connect(self.slot_requestDefaultRange)
        self.applyPushButton.clicked.connect(self.slot_requestApplyToData)
        self.factorSpinBox.valueChanged[float].connect(self.slot_sendNewFactorValue)
        self.rangeMinSpinBox.valueChanged[float].connect(self.slot_sendNewRangeMinValue)
        self.rangeMaxSpinBox.valueChanged[float].connect(self.slot_sendNewRangeMaxValue)
        
    @Slot()
    def slot_requestAutoRange(self):
        self.signalAutoRange.emit()
        
    @Slot()
    def slot_requestDefaultRange(self):
        self.signalDefaultRange.emit()
    
    @Slot()
    def slot_requestApplyToData(self):
        self.signalApply.emit()
        
    @Slot(float)
    def slot_sendNewFactorValue(self, val):
        self.signalFactorValueChanged.emit(val)
        
    @Slot(float)
    def slot_sendNewRangeMinValue(self, val):
        self.signalMinRangeValueChanged.emit(val)
        
    @Slot(float)
    def slot_sendNewRangeMaxValue(self, val):
        self.signalMaxRangeValueChanged.emit(val)
        
    @Slot(float)
    def slot_newFactorValueReceived(self, val):
        self.factorSpinBox.setValue(val)
        
    @Slot(float)
    def slot_newMinRangeValueReceived(self, val):
        self.rangeMinSpinBox.setValue(val)
        
    @Slot(float)
    def slot_newMaxRangeValueReceived(self, val):
        self.rangeMaxSpinBox.setValue(val)
        

class AxesCalibrationDialog(QDialog, Ui_AxesCalibrationDialog):
    def __init__(self, image, pWin=None, parent=None):
        super(AxesCalibrationDialog, self).__init__(parent)
        
        self.arrayshape=None
        self._data_=None
        
        if isinstance(image, vigra.AxisTags):
            self.axistags = image
            self._data_ = None
            
        elif isinstance(image, vigra.VigraArray):
            self.axistags = image.axistags
            self.arrayshape = image.shape
            self._data_ = image
            
        else:
            raise TypeError("A VigraArray instance was expected; got %d instead" % (type(image).__name__))
        
        #self._data_ = image
        
        self.resolution = 1.0
        self.origin = 0.0
        self.units =  datatypes.pixel_unit
        
        self.selectedAxisIndex = 0
        
        #self.axesCalibration = AxesCalibration(img)
        
        self.axisMetaData = dict()
        
        for axisInfo in self.axistags:
            self.axisMetaData[axisInfo.key]["calibration"] = axiscalibration.AxesCalibration(axisInfo)
                
            self.axisMetaData[axisInfo.key]["description"] = axiscalibration.AxesCalibration.removeCalibrationFromString(axisInfo.description)

        self.units          = self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["calibration"].units
        self.origin         = self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["calibration"].origin
        self.resolution     = self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["calibration"].resolution
        self.description    = self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["description"]
        
        self._configureUI_()
        
    def _configureUI_(self):
        self.setupUi(self)
        
        self.setWindowTitle("Calibrate axes")
        
        self.axisIndexSpinBox.setMaximum(len(self.axistags) -1)
        
        self.axisIndexSpinBox.setValue(self.selectedAxisIndex)
        
        if self.arrayshape is None:
            self.axisInfoLabel.setText("Axis key: %s, type: %s" % (self.axistags[self.selectedAxisIndex].key, axisTypeName(self.axistags[self.selectedAxisIndex])))
        else:
            self.axisInfoLabel.setText("Axis key: %s, type: %s, length: %d" % (self.axistags[self.selectedAxisIndex].key, axisTypeName(self.axistags[self.selectedAxisIndex]), self.arrayshape[self.selectedAxisIndex]))
            
        self.unitsLineEdit.setClearButtonEnabled(True)
        
        self.unitsLineEdit.undoAvailable = True
        
        self.unitsLineEdit.redoAvailable = True
        
        self.unitsLineEdit.setText(self.units.__str__().split()[1])
        
        #self.unitsLineEdit.setValidator( datatypes.UnitsStringValidator())
        
        self.unitsLineEdit.editingFinished.connect(self.slot_unitsChanged)
        
        #self.unitsLineEdit.returnPressed.connect(self.slot_unitsChanged)
        
        self.axisIndexSpinBox.valueChanged[int].connect(self.slot_axisIndexChanged)
        
        self.originSpinBox.setValue(self.origin)
        
        self.originSpinBox.valueChanged[float].connect(self.slot_originChanged)
        
        self.resolutionRadioButton.setDown(True)
        
        self.resolutionRadioButton.toggled[bool].connect(self.slot_resolutionChecked)
        
        self.resolutionSpinBox.setValue(self.resolution)
        
        self.resolutionSpinBox.setReadOnly(True)
        
        self.pixelsDistanceRadioButton.toggled[bool].connect(self.slot_pixelsDistanceChecked)
        
        self.calibratedDistanceRadioButton.toggled[bool].connect(self.slot_calibratedDistanceChecked)
        
        self.resolutionSpinBox.valueChanged[float].connect(self.slot_resolutionChanged)
        
        self.pixelsDistanceSpinBox.valueChanged[int].connect(self.slot_pixelDistanceChanged)
        
        self.calibratedDistanceSpinBox.valueChanged[float].connect(self.slot_calibratedDistanceChanged)
        
        #self.axisDescriptionEdit.setUndoRedoEnabled(True)
        
        self.axisDescriptionEdit.plainText = self.description
        
        self.axisDescriptionEdit.textChanged.connect(self.slot_descriptionChanged)
        
    def updateFieldsFromAxis(self):
        self.units          = self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["calibration"].units
        self.origin         = self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["calibration"].origin
        self.resolution     = self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["calibration"].resolution
        self.description    = self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["description"]

        if self.arrayshape is None:
            self.axisInfoLabel.setText("Axis key: %s, type: %s" % (self.axistags[self.selectedAxisIndex].key, axisTypeName(self.axistags[self.selectedAxisIndex])))
        else:
            self.axisInfoLabel.setText("Axis key: %s, type: %s, length: %d" % (self.axistags[self.selectedAxisIndex].key, axisTypeName(self.axistags[self.selectedAxisIndex]), self.arrayshape[self.selectedAxisIndex]))
            
        self.unitsLineEdit.setText(self.units.__str__().split()[1])
        self.originSpinBox.setValue(self.origin)
        self.resolutionSpinBox.setValue(self.resolution)
        
        if self.resolutionRadioButton.isChecked():
            self.calibratedDistanceSpinBox.setValue(self.resolution * self.pixelsDistanceSpinBox.value())
            
        else:
            self.slot_resolutionChanged(self.resolution)
    
        self.axisDescriptionEdit.clear()
        self.axisDescriptionEdit.plainText = self.description
        
    @Slot(int)
    @safeWrapper
    def slot_axisIndexChanged(self, value):
        self.selectedAxisIndex = value
        self.updateFieldsFromAxis()
        #self.slot_generateCalibration()
        
    @Slot()
    @safeWrapper
    def slot_unitsChanged(self):
        try:
            self.units = eval("1*%s" % (self.unitsLineEdit.text()), pq.__dict__)
            #print("%s --> %s" % (self.unitsLineEdit.text(),self.units))
        except:
            pass
            #print("Try again!")
        
        self.slot_generateCalibration()

    @Slot(bool)
    @safeWrapper
    def slot_resolutionChecked(self, value):
        self.resolutionSpinBox.setReadOnly(value)
        self.pixelsDistanceSpinBox.setReadOnly(not value)
        self.calibratedDistanceSpinBox.setReadOnly(not value)
    
    @Slot(bool)
    @safeWrapper
    def slot_pixelsDistanceChecked(self, value):
        self.pixelsDistanceSpinBox.setReadOnly(value)
        self.resolutionSpinBox.setReadOnly(not value)
        self.calibratedDistanceSpinBox.setReadOnly(not value)
        
    @Slot(bool)
    @safeWrapper
    def slot_calibratedDistanceChecked(self, value):
        self.calibratedDistanceSpinBox.setReadOnly(value)
        self.pixelsDistanceSpinBox.setReadOnly(not value)
        self.resolutionSpinBox.setReadOnly(value)
    
    @Slot()
    @safeWrapper
    def slot_generateCalibration(self):
        self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["calibration"].units = \
            eval("1*%s" % (self.unitsLineEdit.text()), pq.__dict__)
        
        self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["calibration"].origin = \
            self.origin
        
        self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["calibration"].resolution = \
            self.resolution
        
        self.axisMetaData[self.axistags[self.selectedAxisIndex].key]["description"] = \
            self.description
        
        
    
    @Slot(float)
    @safeWrapper
    def slot_originChanged(self, value):
        self.origin = value
        
        self.slot_generateCalibration()


    @Slot(float)
    @safeWrapper
    def slot_resolutionChanged(self, value):
        if self.pixelsDistanceRadioButton.isChecked(): # calculate distance in pixels
            self.pixelsDistanceSpinBox.setValue(int(self.calibratedDistanceSpinBox.value() // value))
            
        elif self.calibratedDistanceRadioButton.isChecked(): # calculate calibrated distance
            self.calibratedDistanceSpinBox.setValue(value * self.pixelsDistanceSpinBox.value())
            
        self.resolution = value
        
        self.slot_generateCalibration()

    @Slot(int)
    @safeWrapper
    def slot_pixelDistanceChanged(self, value):
        if self.resolutionRadioButton.isChecked(): # calculate resolution
            self.resolutionSpinBox.setValue(self.calibratedDistanceSpinBox.value() / value)
            
            self.resolution = self.resolutionSpinBox.value()
            
        elif self.calibratedDistanceRadioButton.isChecked(): # calculate calibrated distance
            self.calibratedDistanceSpinBox.setValue(self.resolutionSpinBox.value() * value)
    
        self.slot_generateCalibration()
        
    @Slot(float)
    @safeWrapper
    def slot_calibratedDistanceChanged(self, value):
        if self.resolutionRadioButton.isChecked(): # calculate resolution
            self.resolutionSpinBox.setValue(value / self.pixelsDistanceSpinBox.value())
            
            self.resolution = self.resolutionSpinBox.value()
            
        elif self.pixelsDistanceSpinBox.isChecked(): # calculate pixels distance
            self.pixelsDistanceSpinBox.setValue(int(value // self.resolutionSpinBox.value()))
        
        self.slot_generateCalibration()
        
    @Slot()
    @safeWrapper
    def slot_descriptionChanged(self):
        self.description = self.axisDescriptionEdit.toPlainText()
        self.slot_generateCalibration()

    def calculateResolution(self, pixels=None, distance=None):
        if pixels is None:
            pixels = self.pixelsDistanceSpinBox.value()
            
        if distance is None:
            distance = self.calibratedDistanceSpinBox.value()
            
        self.resolution = distance / pixels
        
        self.resolutionSpinBox.setValue(self.resolution)

        self.slot_generateCalibration()
        
class ImageViewer(ScipyenFrameViewer, Ui_ImageViewerWindow):
    closeMe                 = Signal(int)
    
    signal_graphicsObjectAdded      = Signal(object, name="signal_graphicsObjectAdded")
    signal_graphicsObjectChanged    = Signal(object, name="signal_graphicsObjectChanged")
    signal_graphicsObjectRemoved    = Signal(object, name="signal_graphicsObjectRemoved")
    signal_graphicsObjectSelected   = Signal(object, name="signal_graphicsObjectSelected")
    signal_graphicsObjectDeselected = Signal(name="signal_graphicsObjectDeselected")
    
    # TODO 2019-11-01 22:41:39
    # implement viewing of Kernel2D, numpy.ndarray with 2 <= ndim <= 3
    # list and tuple of 2D VigraArray 2D, Kernel2D, 2D numpy.ndarray, QImage, QPixmap
    viewer_for_types = {vigra.VigraArray:99, 
                        vigra.filters.Kernel2D:99, 
                        np.ndarray:0, 
                        QtGui.QImage:99, 
                        QtGui.QPixmap:99, 
                        tuple:0, 
                        list:0}
    
    # view_action_name = "Image"
    
    # image = the image (2D or volume, or up to 5D (but with up to 3 spatial
    #           dimensions e.g., xyztc, etc))
    # title = name of image data to be displayed on the view's label -- defaults to "image ID"
    # 
    # normalize = boolean or (min,max) or None
    #
    # gamma = None (for now)
    #
    # "colormap" = singleton or list of colortables or None
    #
    
    # NOTE: 2021-09-15 10:40:44 KISS!
    # for cursor & roi label backgrounds we should limit ourselved to one of:
    # a) transparent
    # b) any color (although preferable either black or white)
    # and this is applied across the board (i.e. all cursors & rois)
    #
    # Regarding hover color, the same one-for-all rule should apply: use the same
    # hover color for any graphics item we hover (if we decide to use hover color, 
    # which might be nice!)
    #
    # Also, NOTE that these are defaults for top level imageviewer windows only.
    # Client windows will have to set their own cursor/roi colors by supplying
    # the appropriate parameter to the cursor/roi creation method in this :class:
    #
    #
    # To get/set the color for a SPECIFIC graphics item (cursor or ROI) use the
    # getter / setter methods
    #
    # getPlanarGraphicsColor / setPlanarGraphicsColor; NOTE these are NOT defined
    # as configurables for this :class:. Instead they should be linked into (i.e.,
    # called, perhaps, indirectly, by) a configurable getter/setter of the 
    # viewer's owner :class: such as LSCaTWindow. In this way the appearance of
    # a subset of planargraphics of a certain type (which share a common meaning)
    # appear similarly
    #
    
    
    defaultRoisColor = "#aaff00"
    
    defaultCursorColors = Bunch({"crosshair_cursor":"#C173B088", 
                                 "horizontal_cursor":"#B1D28F88", 
                                 "vertical_cursor":"#ff007f88",
                                 "point_cursor":"#aaaa00"})
    
    defaultLinkedCursorColors = Bunch({"crosshair_cursor":QtGui.QColor(defaultCursorColors["crosshair_cursor"]).darker().name(QtGui.QColor.HexArgb),
                                       "horizontal_cursor":QtGui.QColor(defaultCursorColors["horizontal_cursor"]).darker().name(QtGui.QColor.HexArgb),
                                       "vertical_cursor":QtGui.QColor(defaultCursorColors["vertical_cursor"]).darker().name(QtGui.QColor.HexArgb),
                                       "point_cursor":QtGui.QColor(defaultCursorColors["point_cursor"]).darker().name(QtGui.QColor.HexArgb)})
    
    defaultGraphicsLabelBackgroundColor = QtCore.Qt.transparent
    
    defaultGraphicsHoverColor = "red"

    def __init__(self, data: (vigra.VigraArray, vigra.filters.Kernel2D, np.ndarray, QtGui.QImage, QtGui.QPixmap, tuple, list) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, ID:(int, type(None)) = None, win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None, frame:(int, type(None)) = None, displayChannel = None, normalize: (bool, ) = False, gamma: (float, ) = 1.0, *args, **kwargs):

        self._image_width_ = 0
        self._image_height_ = 0
        self._imageNormalize             = None
        self._imageGamma                 = None
        self._colorMap                   = None
        self._tempColorMap               = None
        self._prevColorMap               = None
        self._colorBar                   = None
        self._colorbar_width_            = 20
        
        #self._separateChannels           = False
        
        self.cursorsColor               = None # to remove
        self.linkedCursorsColor         = None # to remove
        self.cursorLabelTextColor       = None # to remove
        self.linkedCursorLabelTextColor = None # to remove
        self.cursorLabelBackgroundColor = None # to property
        self.roisColor                  = None # to property
        self.linkedROIsColor            = None # to property
        self.roiLabelTextColor          = None # to remove
        self.linkedROILabelTextColor    = None # to remove
        self.roiLabelBackgroundColor    = None # to remove
        self.opaqueCursorLabel          = True # replace with self._graphicsBackgroundColor_
        self.opaqueROILabel             = True # replace with self._graphicsBackgroundColor_
        
        self._cursorColors_             = self.defaultCursorColors
        self._graphicsBackgroundColor_  = self.defaultGraphicsLabelBackgroundColor
        self._linkedCursorColors_       = self.defaultLinkedCursorColors
        self._roisColor_                = self.defaultRoisColor
        self._graphicsHoverColor_       = self.defaultGraphicsHoverColor
        
        
        if displayChannel is None:
            self._displayedChannel_      = "all"
            
        else:
            if isinstance(displayChannel, str):
                if displayChannel.lower().strip()!="all":
                    raise ValueError("When a str, displayChannel must be 'all'; got %s instead" % displayChannel)
                
            elif isinstance(displayChannel, int):
                if displayChannel < 0:
                    raise ValueError("When an int, display channel must be >= 0")
                
            self._displayedChannel_ = displayChannel
                
                
        #self.isComplex                 = False
        #self.nChannels                 = 1
        #self._current_frame_index_      = 0
        #self._number_of_frames_         = 1
        self.tStride                    = 0
        self.zStride                    = 0
        self.userFrameAxisInfo          = None
        # NOTE: 2021-12-02 10:50:17
        # the 3 beow are int see NOTE: 2021-12-02 10:39:54
        self.frameAxis                  = None
        self.widthAxis                  = None # this is "visual" width which may not be on a spatial axis "x"
        self.heightAxis                 = None # this is "visual" height which may not be on a spatial axis "y"
        #self.frameIterator              = None # ??? FIXME what's this for ???
        self._currentZoom_              = 0
        #self.complexDisplay            = ComplexDisplay.real # one of "real", "imag", "dual" "abs", "phase" (cmath.phase), "arg"
        self._currentFrameData_         = None
        
        # QGraphicsLineItems -- outside the roi/cursor GraphicsObject framework!
        self._scaleBarColor_             = QtGui.QColor(255, 255, 255)
        self._xScaleBar_                 = None
        self._xScaleBarTextItem_         = None
        self._yScaleBar_                 = None
        self._yScaleBarTextItem_         = None
        self._scaleBarTextPen_           = QtGui.QPen(QtCore.Qt.SolidLine)
        self._scaleBarPen_               = QtGui.QPen(QtGui.QBrush(self._scaleBarColor_, 
                                                                  QtCore.Qt.SolidPattern),
                                                     2.0,
                                                     cap = QtCore.Qt.RoundCap,
                                                     join = QtCore.Qt.RoundJoin)
        
        #self.qsettings                   = QtCore.QSettings()
        
        self._display_horizontal_scalebar_ = True
        self._display_vertical_scalebar_   = True
        
        self._display_time_vertical_           = True
        
        self._showsScaleBars_            = True
        
        self._showsIntensityCalibration_ = False
        
        self._scaleBarOrigin_            = (0, 0)
        self._scaleBarLength_            = (10,10)
        
        # NOTE: 2021-08-25 09:42:54
        # ScipyenFrameViewer initialization - also does the following:
        # 1) calls self._configureUI_() overridden here:
        #   1.1) sets up the UI defined in the .ui file (setupUi)
        #
        # 2) calls self.loadSettings() inherited from 
        # ScipyenViewer <- WorkspaceGuiMixin <- ScipyenConfigurable
        #
        # NOTE: 2022-01-17 16:27:30
        # pass None for data to prevent super().__init__ from calling setData
        # next call our own setData
        super().__init__(data=None, parent=parent, ID=ID, win_title=win_title, 
                         doc_title=doc_title, frameIndex=frame, **kwargs)
        
        self.observed_vars = DataBag(allow_none=True, mutable_types=True)
        self.observed_vars.verbose=True
        self.observed_vars.observe(self.var_observer)
        
        # NOTE: 2022-01-17 16:29:57
        # call super.setData() directly, as we don't need to treat 'data' 
        # specially (unlike in SignalViewer's case)
        #
        # in turn, super.setData() calls self._set_data_(...)
        if isinstance(data, tuple(ImageViewer.viewer_for_types.keys())) or any([t in type(data).mro() for t in tuple(ImageViewer.viewer_for_types.keys())]):
            self.setData(data, doc_title=self._docTitle_)
            
        
    ####
    # properties
    ####
    
    @property
    def colorMapObj(self):
        """The colormap used as default for displaying gray-scale images
        This is not a configurable property; however, changing it will result in
        a new value of the colorMap property
        """
        if not isinstance(self._colorMap, colormaps.mpl.colors.Colormap):
            if isinstance(self._prevColorMap, colormaps.mpl.colors.Colormap):
                self._colorMap = self._prevColorMap
            else:
                self._colorMap = colormaps.get("grey")
        
        return self._colorMap
    
    @colorMapObj.setter
    def colorMapObj(self, val:colormaps.mpl.colors.Colormap):
        if isinstance(val, colormaps.mpl.colors.Colormap):
            self._colorMap = val
        
    @property
    def colorMap(self):
        """Name of the colormap used as default for displaying gray-scale images.
        This is the 'name' attribute (str) of a matplotlib.colors.Colormap object.
        This is so that the name can be safely stored in QSettings.
        
        The colorMap property setter accepts a matplotlib.colors.Colormap object
        or a str (valid colormap name, see gui.sciyen_colormaps module).
        If str is not a valid colormap name the default color map will not be changed.
        """
        if not isinstance(self._colorMap, colormaps.mpl.colors.Colormap):
            if isinstance(self._prevColorMap, colormaps.mpl.colors.Colormap):
                self._colorMap = self._prevColorMap
            else:
                self._colorMap = colormaps.get("grey")
            #self.displayFrame()
            
        return self._colorMap.name
    
    @markConfigurable("ColorMap")
    @colorMap.setter
    def colorMap(self, val:typing.Union[str, colormaps.mpl.colors.Colormap]):
        """Setter for colorMap
        """
        if isinstance(val, colormaps.mpl.colors.Colormap):
            cmap_name = val.name
            cmap = val
            
        elif isinstance(val, str):
            cmap = colormaps.get(val, None)
            if not isinstance(cmap, colormaps.mpl.colors.Colormap):
                return
            cmap_name = val
                
        else:
            raise TypeError(f"Expecting a str or a maptplotlib.cm.Colormap; got {type(val).__name__} instead")
        
        if isinstance(self._colorMap, colormaps.mpl.colors.Colormap):
            self._prevColorMap = self._colorMap
        
        self._colorMap = cmap
        #self._colorMap = val
        if isinstance(getattr(self, "configurable_traits", None), DataBag):
            self.configurable_traits["ColorMap"] = cmap_name
        
        self.displayFrame()
        
    @property
    def frameIndexBinding(self):
        if not isinstance(self._data_, vigra.VigraArray):
            return (None, 0)
        
        # NOTE when a frame axis index equals data.ndim this means there is no
        # frame axis there!
        
        #print("in frameIndexBinding: self.frameAxis", self.frameAxis)
        #print("in frameIndexBinding: self._number_of_frames_", self._number_of_frames_)
        if isinstance(self._number_of_frames_, int):
            return tuple((self.frameAxis if self.frameAxis < self._data_.ndim else None, k) for k in range(self._number_of_frames_))
        
        else:
            traversal = tuple(tuple((ax,i) for i in range(axSize)) for ax, axSize in zip(reversed(self.frameAxis), reversed(self._number_of_frames_)))
            #traversal = tuple(tuple((ax,i) for i in range(axSize)) for ax, axSize in zip(self.frameAxis, self._number_of_frames_))
            return tuple(itertools.product(*traversal))
            
        
    @property
    def temporaryColorMap(self):
        """Name of a temporary colormap or None.
        A temporary colormap is to be used for displaying 'channel' images (e.g.,
        2D Vigra arrays representing an image 'channel').
        In order to be used, the temporary colormap needs to be passed as the
        'colorMap' parameter to self.displayFrame().
        By default, the temporary colormap is None.
        The setter of this property acceps either a str (colormap name) or a 
        mpl.colors.Colormap object. 
        When a str, if this is not a valid colormap name, the temporary colormap
        is set to None.
        This is not a configurable property.
        """
        if isinstance(self._tempColorMap, colormaps.mpl.colors.Colormap):
            return self._tempColorMap.name
            
    @temporaryColorMap.setter
    def temporaryColorMap(self, val:typing.Union[colormaps.mpl.colors.Colormap,str]):
        if val is None:
            self._tempColorMap = None
        elif isinstance(val, str):
            self._tempColorMap = colormaps.get(val, None)
        elif isinstance(val, colormaps.mpl.colors.Colormap):
            self._tempColorMap = val
        else:
            raise TypeError(f"Expecting a str, matplotlib colormap or None; got {type(val).__name__} instead")
        
        if isinstance(self._tempColorMap, colormaps.colors.Colormap):
            self.displayFrame(colorMap = self._tempColorMap)
        
        
    def getPlanarGraphicsColor(self, ID):
        # TODO
        pass
    
    def setPlanarGraphicsColor(self, ID, val):
        # TODO
        pass
        
    def setDataDisplayEnabled(self, value):
        self.viewerWidget.setEnabled(value is True)
        self.viewerWidget.setVisible(value is True)
            
    @property
    def currentFrame(self):
        return self._current_frame_index_
    
    @currentFrame.setter
    def currentFrame(self, val):
        """
        Emits self.frameChanged signal
        """
        missing = (isinstance(self._missing_frame_value_, (int, float)) and val == self._missing_frame_value_) or \
            self._missing_frame_value_ in (MISSING, NA) and val is self._missing_frame_value_
        
        if missing or val not in self.frameIndex:
            self.setDataDisplayEnabled(False)
            return
        else:
            self.setDataDisplayEnabled(True)
            
        self._current_frame_index_ = int(val)
        
        # NOTE: 2018-09-25 23:06:55
        # recipe to block re-entrant signals in the code below
        # cleaner than manually docinenctign and re-connecting
        # and also exception-safe
        
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
            (self.framesQSpinBox, self.framesQSlider)]
        
        self.framesQSpinBox.setValue(val)
        self.framesQSlider.setValue(val)

        self.displayFrame()

        if type(self._scipyenWindow_).__name__ == "ScipyenWindow":
            # updates the graphics items positions from their backend store
            # ONLY is this is an independent window (ie. it is not a client
            # to some other app e.g. LSCaT)
            #
            # when a client to such app, it falls to that app to manage the 
            # graphics items' backends (i.e., to set the index of their current 
            # frame) followed by the backends' responsibility to update
            # their frontends
            #
            for o in self.graphicsObjects:
                if o.backend.currentFrame != self._current_frame_index_: # check to avoid race conditions and recurrence
                    o.backend.currentFrame = self._current_frame_index_
                    
            # NOTE: 2021-07-08 10:53:01
            # Alternatively:
            for o in self.planarGraphics:
                if o.currentFrame != self._current_frame_index_: # check to avoid race conditions and recurrence
                    o.currentFrame = self._current_frame_index_
                    
            self.frameChanged.emit(self.currentFrame)
        
        # NOTE: 2018-05-21 20:59:18
        # managed to do away with guiClient here
    
    @property
    def graphicsObjects(self):
        return list(self.viewerWidget.graphicsObjects)
    
    @property
    def planarGraphics(self):
        return list(set(self.viewerWidget.planarGraphics))
    
    @property
    def graphicsCursors(self):
        """List of Cursor planar graphics.
        This is the list of unique planar graphics cursor backends for the 
        displayed cursors
        """
        return list(self.viewerWidget.graphicsCursors)
    
    def getGraphicsCursors(self, **kwargs):
        """List with a specific subset of Cursor planar graphics objects.
        
        Var-keyword parameters
        ======================
        kwargs: key/value pairs for cursor properties for selecting the cursors
            subset.
            
            When no var-keyword parameters are passed, the function returns 
            self.graphicsCursors property directly.
        
        (see core.prog.filter_attr)
        """
        if len(kwargs):
            return list(filter_attr(self.viewerWidget.graphicsCursors, **kwargs))
        
        return self.graphicsCursors
    
    @safeWrapper
    def imageCursor(self, value:typing.Optional[typing.Any]=None, *args, **kwargs):
        """Returns a list of pictgui.Cursor selected by one or more attributes.
        
        By default, compares the value of the 'name' attribute of the 
        PlanarGraphics Cursor object to the 'value' parameter.
        
        Delegates to GraphicsImageViewerWidget.imageCursor, documented below
        
        Parameters: (from GraphicsImageViewerWidget.cursor(...) docstring)
        ==========
        value: any type
            The value against which the value of the named attribute is compared.
               
        Named Parameters:
        =================
        attribute: str, default is "name" - the name of the attribute for which
            the value will be compared against 'value'
        
        predicate: a callable that takes two parameters and returnss a bool.
            Performs the actual comparison between 'value' and the named attribute
            value.
            
            The first parameter of the predicate is a place holder for the value
            of the attribute given in 'attribute'
            
            The second parameter is the placeholder for 'value'
            
            In short, the predicate compares the vlue of the named attribute to
            that given in 'value'
            
            Optional: default is the identity (lambda x,y: x==y)
        """
        return list(self.viewerWidget.imageCursor(value, *args, **kwargs))

    @safeWrapper
    def hasCursor(self, *args, **kwargs):
        """Tests for existence of a GraphicsObject cursor with specified ID or name (label).
        
        Delegates to self.imageCursor(...)
        """
        return len(set(self.imageCursor(*args, **kwargs))) > 0
    
    @property
    def rois(self):
        """List of non-Cursor planargraphics
        This is the list of unique planar graphics cursor backends for the 
        displayed cursors
        """
        return list(set(self.viewerWidget.rois))
    
    @safeWrapper
    def roi(self, value:typing.Optional[typing.Any]=None, *args, **kwargs):
        """Returns a list of PlanarGraphics ROI roi with a specific attribute value.
        
        Delegates to GraphicsImageViewerWidget.roi(...); by default, compares
        the value of the 'name' attribute of the PlanarGraphics to the 'value'
        parameter.
        
        Parameters: (from GraphicsImageViewerWidget.roi(...) docstring)
        ==========
        value: any type
            The value against which the value of the named attribute is compared.
               
        Named Parameters:
        =================
        attribute: str, default is "name" - the name of the attribute for which
            the value will be compared against 'value'
        
        predicate: a callable that takes two parameters and returnss a bool.
            Performs the actual comparison between 'value' and the named attribute
            value.
            
            The first parameter of the predicate is a place holder for the value
            of the attribute given in 'attribute'
            
            The second parameter is the placeholder for 'value'
            
            In short, the predicate compares the vlue of the named attribute to
            that given in 'value'
            
            Optional: default is the identity (lambda x,y: x==y)
            
        """
        return list(set(self.viewerWidget.roi(value, *args, **kwargs)))
        
    @safeWrapper
    def hasRoi(self, *args, **kwargs):
        """Tests for existence of a PlanarGraphics ROI roi with a given attribute.
        
        Delegates to self.roi(...)
        
        """
        return len(set(self.roi(*args, **kwargs))) > 0
    
    @property
    def colorBarWidth(self):
        return self._colorbar_width_
    
    @markConfigurable("ColorBarWidth", "qt")
    @colorBarWidth.setter
    def colorBarWidth(self, value):
        if isinstance(value, str):
            value = int(value)
                
        if not isinstance(value, int):
            raise TypeError("Expecting an int; got %s instead" % type(value).__name__)
        
        if value <= 0:
            raise ValueError("Expecting a strictly positive value (>=0); got %d instead" % value)
        
        self._colorbar_width_ = value
    
    @property
    def viewer(self):
        return self.viewerWidget
    
    @property
    def scene(self):
        """A reference to viewerWidget's QGraphicsScene.
        """
        return self.viewer.scene
    
    
    @property
    def selectedRoi(self):
        """A reference to the selected ROI
        """
        return self.viewer.selectedRoi
    
    @property
    def selectedCursor(self):
        """A reference to the selected cursor
        """
        return self.viewer.selectedCursor
    
    @property
    def imageWidth(self):
        """Width of the displayed image (in pixels); read-only; 0 if no image
        """
        return self._image_width_
    
    @property
    def imageHeight(self):
        """Height of the displayed image (in pixels); read-only; 0 if no image
        """
        return self._image_height_
    
    
    
    ####
    # slots
    ####
    
    # helper for export slots
    
    def _export_scene_helper_(self, file_format):
        if not isinstance(file_format, str) or file_format.strip().lower() not in ("svg", "tiff", "png"):
            raise ValueError("Unsupported export file format %s" % file_format)
        
        if file_format.strip().lower() == "svg":
            file_filter = "Scalable Vector Graphics Files (*.svg)"
            caption_suffix = "SVG"
            
        elif file_format.strip().lower() == "tiff":
            file_filter = "TIFF Files (*.tif)"
            caption_suffix = "TIFF"
            qimg_format = QtGui.QImage.Format_ARGB32
            
        elif file_format.strip().lower() == "png":
            file_filter = "Portable Network Graphics Files (*.png)"
            caption_suffix = "PNG"
            qimg_format = QtGui.QImage.Format_ARGB32
            
        else:
            raise ValueError("Unsupported export file format %s" % file_format)

        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        if self._scipyenWindow_ is not None:
            targetDir = self._scipyenWindow_.currentDir
            
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                                caption="Export figure as %s" % caption_suffix,
                                                                filter = file_filter,
                                                                directory = targetDir,
                                                                **kw)
            
        else:
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                                caption="Export figure as %s" % caption_suffix,
                                                                filter = file_filter,
                                                                **kw)
            
        if len(fileName) == 0:
            return
        
        if file_format.strip().lower() == "svg":
            generator = QtSvg.QSvgGenerator()
            generator.setFileName(fileName)
            
            generator.setSize(QtCore.QSize(int(self.viewerWidget.scene.width()), 
                                           int(self.viewerWidget.scene.height())))
            
            generator.setViewBox(QtCore.QRect(0, 0, 
                                              int(self.viewerWidget.scene.width()),
                                              int(self.viewerWidget.scene.height())))
            
            generator.setResolution(300)
            
            #font = QtGui.QFont("sans-serif", pointSize = 4)
            font = QtGui.QGuiApplication.font()
            
            painter = QtGui.QPainter()
            painter.begin(generator)
            painter.setFont(font)
            self.viewerWidget.scene.render(painter)
            painter.end()
        
        else:
            out = QtGui.QImage(int(self.viewerWidget.scene.width()), 
                               int(self.viewerWidget.scene.height()),
                               qimg_format)
            
            out.fill(QtCore.Qt.black)
            
            painter = QtGui.QPainter(out)
            self.viewerWidget.scene.render(painter)
            painter.end()
            out.save(fileName, file_format.strip().lower(), 100)
    
    @Slot()
    @safeWrapper
    def slot_exportSceneAsPNG(self):
        if self._data_ is None:
            return
        
        self._export_scene_helper_("png")
        
    @Slot()
    @safeWrapper
    def slot_exportSceneAsSVG(self):
        if self._data_ is None:
            return
        
        self._export_scene_helper_("svg")
        
    @Slot()
    @safeWrapper
    def slot_exportSceneAsTIFF(self):
        if self._data_ is None:
            return
        
        self._export_scene_helper_("tiff")
        
    @Slot()
    @safeWrapper
    def slot_saveTIFF(self):
        if self._data_ is None:
            return
        
        if sys.platform == "win32":
            options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
            kw = {"options":options}
        else:
            kw = {}

        if self._scipyenWindow_ is not None:
            targetDir = self._scipyenWindow_.currentDir
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                                caption="Save image data as TIFF", 
                                                                filter="TIFF Files (*.tif)",
                                                                directory=targetDir, **kw)
        else:
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
                                                                caption="Save image data as TIFF", 
                                                                filter="TIFF Files (*.tif)", **kw)
        
        if len(fileName) == 0:
            return
        
        #if image
        
        pio.saveImageFile(self._data_, fileName)
        
    
    @Slot()
    @safeWrapper
    def slot_editCursor(self):
        self.viewerWidget.slot_editAnyCursor()
    
    @Slot()
    @safeWrapper
    def slot_editSelectedCursor(self):
        self.viewerWidget.slot_editSelectedCursor()
    
    @Slot()
    @safeWrapper
    def slot_removeAllCursors(self):
        self.viewerWidget.slot_removeAllCursors()

    @Slot()
    @safeWrapper
    def slot_removeSelectedCursor(self):
        self.viewerWidget._removeSelectedPlanarGraphics(True)
        # self.viewerWidget.slot_removeSelectedCursor()
    
    @Slot()
    @safeWrapper
    def slot_removeAllRois(self):
        self.viewerWidget.slot_removeAllRois()
        
    @Slot(str)
    @safeWrapper
    def slot_removeRoi(self, roiId):
        self.removeRoi(roiId)
        # self.viewerWidget.slot_removeRoiByName(roiId)

    @Slot()
    @safeWrapper
    def slot_removeSelectedRoi(self):
        self.viewerWidget._removeSelectedPlanarGraphics(False)
        # self.viewerWidget.slot_removeSelectedRoi()
    
    @Slot()
    @safeWrapper
    def slot_zoomIn(self):
        self._currentZoom_ +=1
        self.viewerWidget.slot_zoom(2**self._currentZoom_)
        
    @Slot()
    @safeWrapper
    def slot_zoomOriginal(self):
        self._currentZoom_ = 0
        self.viewerWidget.slot_zoom(2**self._currentZoom_)
        
    @Slot(object)
    def slot_varModified(self, obj):
        """Connected to _scipyenWindow_.workspaceModel.varModified signal
        """
        self.displayFrame()
        
    @Slot()
    @safeWrapper
    def slot_refreshDataDisplay(self):
        self.displayFrame()
        
    @Slot()
    @safeWrapper
    def slot_zoomOut(self):
        self._currentZoom_ -=1
        self.viewerWidget.slot_zoom(2**self._currentZoom_)
        
    @Slot()
    @safeWrapper
    def slot_selectZoom(self):
        self.viewerWidget.interactiveZoom()
        
    @Slot(bool)
    @safeWrapper
    def slot_displayColorBar(self, value):
        if value:
            self._setup_color_bar_()
            
        else:
            if self._colorBar is not None:
                self.viewerWidget.scene.removeItem(self._colorBar)
                
    def _setup_color_bar_(self):
        #try:
            #import qimage2ndarray as q2a
        #except:
            #traceback.print_exc()
            #return
        
        
        if isinstance(self._data_, vigra.VigraArray):
            self._currentFrameData_, _ = self._frameView_(self._displayedChannel_)
            
            imax = self._currentFrameData_.max()
            imin = self._currentFrameData_.min()
            
            imin, imax = sorted((imin, imax))
            
            image_range = abs(imax - imin)
            
            bar_x = self._currentFrameData_.shape[0]
            bar_height = self._currentFrameData_.shape[1]
            
            
            if image_range == 0:
                return
            
            bar_column = np.linspace(self._currentFrameData_.max(), 
                                    self._currentFrameData_.min(),
                                    bar_height)
            
            # 1) prepare a gradient image:
            
            bar_image = vigra.VigraArray(np.concatenate([bar_column[:,np.newaxis] for k in range(self._colorbar_width_)], 
                                                        axis=1).T,
                                        axistags = vigra.VigraArray.defaultAxistags("xy"))
            
            if self._colorMap is None or self._currentFrameData_.channels > 1:
                bar_qimage = bar_image.qimage(normalize = self._imageNormalize)
                
            else:
                bar_qimage = self._applyColorTable_(bar_image).qimage(normalize = self._imageNormalize)
                    
                    
            if self._colorBar is None:
                self._colorBar =  QtWidgets.QGraphicsItemGroup()
                
                self.viewerWidget.scene.addItem(self._colorBar)
                #self._colorBar.setPos(bar_x, 0)
                    
            else:
                for item in self._colorBar.childItems():
                    self._colorBar.removeFromGroup(item)
                    
                #self._colorBar.setPos(bar_x, 0)
                    
                
            cbar_pixmap_item = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(bar_qimage))
            cbar_pixmap_item.setPos(bar_x, 0)
            
            # 2) draw a rect around the gradient image
            cbar_rect = QtWidgets.QGraphicsRectItem(bar_x, 0, self._colorbar_width_, bar_height)
            cbar_rect.setPen(pgraph.mkPen(pgraph.mkColor("k")))
            
            # 3) calculate ticks (thanks to Luke Campagnola, author of pyqtgraph)
            
            # 3.a) tick spacing
            
            optNTicks = max(2., np.log(bar_height))
            
            optTickSpc = image_range/optNTicks
            
            #print("optTickSpc", optTickSpc)
            
            max_p10_spacing = 10 ** np.floor(np.log10(optTickSpc))
            
            #print("max_p10_spacing", max_p10_spacing)
            
            intervals = np.array([1., 2., 10, 20., 100.]) * max_p10_spacing
            
            #print("intervals", intervals)
            
            minorIndex = 0
            
            while intervals[minorIndex+1] <= optTickSpc:
                minorIndex += 1
                
            #print("minorIndex", minorIndex)
                
            # each element is a tuple (spacing, offset)
            levels = [(intervals[minorIndex+2], 0),
                      (intervals[minorIndex+1], 0)]
            
            #print("levels", levels)
            
            minSpc = min(bar_height/20., 30.)
            
            #print("minSpc", minSpc)
            
            maxNTicks = bar_height / minSpc
            
            #print("maxNTicks", maxNTicks)
            
            if image_range / intervals[minorIndex] <= maxNTicks:
                levels.append((intervals[minorIndex], 0))
                
            #print("levels", levels)
            
            tick_values = np.array([])
            
            # will have tuple of (spacing, sequence of tick values)
            ticks = []
                
            for k in range(len(levels)):
                spacing, offset = levels[k]
                
                start = np.ceil((imin-offset)/spacing) * spacing + offset
                
                nticks = int((imax-start) / spacing) + 1
                
                values = np.arange(nticks) * spacing + start
                
                values = list(filter(lambda x: all(np.abs(tick_values-x) > spacing * 0.01), values) )
                
                tick_values = np.concatenate([tick_values, values])
                
                ticks.append( (spacing, values))
                
            #print(ticks)
            
            final_tick_values = ticks[-1][1]
            
            tick_strings = ["%d" % value for value in final_tick_values]
            #print("tick_strings", tick_strings)
            
            tick_y_positions = [(bar_height - ((value -imin) * bar_height) / image_range) for value in final_tick_values]
            
            #print("tick_y_positions", tick_y_positions)
            
            tick_labels_width = []
            
            font = QtGui.QGuiApplication.font()
            
            font_metrics = QtGui.QFontMetrics(font)
            
            tick_lines = []
            tick_labels = []
            
            for k, tick_y in enumerate(tick_y_positions):
                tick_line = QtWidgets.QGraphicsLineItem(bar_x, tick_y, self._colorbar_width_ + bar_x, tick_y)
                tick_line.setPen(pgraph.mkPen(pgraph.mkColor("k")))
                
                
                tick_text = QtWidgets.QGraphicsTextItem(tick_strings[k])
                tick_text.setFont(font)
    
                font_rect = font_metrics.boundingRect(tick_strings[k])
                ##print("fRect", fRect)
                #tick_labels_width.append(fRect.width())
                
                tick_labels_width.append(font_rect.width())# * 1.1)
                
                tick_text.setPos(self._colorbar_width_ + bar_x, tick_y + font_rect.y())
                
                tick_lines.append(tick_line)
                tick_labels.append(tick_text)
                
                
            back_rect = QtWidgets.QGraphicsRectItem(bar_x, 0, (self._colorbar_width_ + max(tick_labels_width))*1.2, bar_height)
            back_rect.setPen(pgraph.mkPen(pgraph.mkColor("w")))
            back_rect.setBrush(pgraph.mkBrush("w"))
            #back_rect.setZValue(-1)
            
            self._colorBar.addToGroup(back_rect)
            self._colorBar.addToGroup(cbar_pixmap_item)
            self._colorBar.addToGroup(cbar_rect)
            
            for k,l in enumerate(tick_lines):
                self._colorBar.addToGroup(l)
                self._colorBar.addToGroup(tick_labels[k])
                
            
            
        elif isinstance(self._data_, (QtGui.QImage, QtGui.QPixmap)):
            # TODO/FIXME figure out how to get the image min and max from a QImage!
            #if isinstance(self._data_, QtGui.QImage):
                #if image.depth() == 24:
                    #pass
            #bar_height = self._data_.height()
            #bar_x = self._data_.width()
            
            return
            
            
        else:
            return
        
            
            
        
    @Slot(bool)
    @safeWrapper
    def slot_displayScaleBar(self, value):
        """
        """
        if value:
            if self._data_ is None:
                return
            
            xcal = None
            ycal = None
            
            x_units =  datatypes.pixel_unit
            y_units =  datatypes.pixel_unit
            
            if isinstance(self._data_, vigra.VigraArray):
                w = self._data_.shape[0]
                h = self._data_.shape[1]
                
                if self.frameAxis is not None:
                    if isinstance(self.frameAxis, tuple):# and len(self.frameAxis) == 2:
                        ndx1 = self._current_frame_index_ // self._data_.shape[self._data_.axistags.index(self.frameAxis[0].key)]
                        ndx0 = self._current_frame_index_ - ndx1 * self._data_.shape[self._data_.axistags.index(self.frameAxis[0].key)]
                        
                        img = self._data_.bindAxis(self.frameAxis[0].key,ndx0).bindAxis(self.frameAxis[1].key,ndx1)
                        
                    else:
                        img = self._data_.bindAxis(self.frameAxis.key, self._current_frame_index_)
                        
                else:
                    img = self._data_
                    
                xcal = axiscalibration.AxesCalibration(img.axistags[0])
                ycal = axiscalibration.AxesCalibration(img.axistags[1])
                
                x_units = xcal.getUnits(img.axistags[0])
                y_units = ycal.getUnits(img.axistags[1])
                
            elif isinstance(self._data_, (QtGui.QImage, QtGui.QPixmap)):
                w = self._data_.width()
                h = self._data_.height()
                
            else:
                return # shouldn't really get here
        
            def_x       = self._scaleBarOrigin_[0] # in pixels!
            def_x_len   = self._scaleBarLength_[0]
            
            if xcal is not None:
                def_x       = float(xcal.getCalibratedAxialDistance(def_x, img.axistags[0]).magnitude)
                def_x_len   = float(xcal.getCalibratedAxialDistance(def_x_len, img.axistags[0]).magnitude)
                
            #print("def_x", def_x)
            #print("def_x_len", def_x_len)
            
            def_y       = self._scaleBarOrigin_[1] # in pixels!
            def_y_len   = self._scaleBarLength_[1]
            
            if ycal is not None:
                def_y       = float(ycal.getCalibratedAxialDistance(def_y, img.axistags[1]).magnitude)
                def_y_len   = float(ycal.getCalibratedAxialDistance(def_y_len, img.axistags[1]).magnitude)
            
            #print("def_y", def_y)
            #print("def_y_len", def_y_len)
            
            dlg = quickdialog.QuickDialog(self, "Display scale bars")
            
            display_group = quickdialog.HDialogGroup(dlg)
            
            show_x = quickdialog.CheckBox(display_group, "Horizontal")
            show_x.setToolTip("Show horizontal scalebar")
            show_x.setChecked(self._display_horizontal_scalebar_)
            
            show_y = quickdialog.CheckBox(display_group, "Vertical")
            show_y.setToolTip("Show vertical scalebar")
            show_y.setChecked(self._display_vertical_scalebar_)
            
            x_prompt = quickdialog.FloatInput(dlg, "X coordinate (in %s)" % x_units)
            x_prompt.variable.setClearButtonEnabled(True)
            x_prompt.variable.redoAvailable = True
            x_prompt.variable.undoAvailable = True
            x_prompt.setValue(def_x)
            
            y_prompt = quickdialog.FloatInput(dlg, "Y coordinate (in %s)" % y_units)
            y_prompt.variable.setClearButtonEnabled(True)
            y_prompt.variable.redoAvailable = True
            y_prompt.variable.undoAvailable = True
            y_prompt.setValue(def_y)
            
            x_len_prompt = quickdialog.FloatInput(dlg, "Length on X axis (in %s)" % x_units)
            x_len_prompt.variable.setClearButtonEnabled(True)
            x_len_prompt.variable.redoAvailable = True
            x_len_prompt.variable.undoAvailable = True
            x_len_prompt.setValue(def_x_len)
            
            y_len_prompt = quickdialog.FloatInput(dlg, "Length on Y axis (in %s)" % y_units)
            y_len_prompt.variable.setClearButtonEnabled(True)
            y_len_prompt.variable.redoAvailable = True
            y_len_prompt.variable.undoAvailable = True
            y_len_prompt.setValue(def_y_len)
            
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                self._display_horizontal_scalebar_ = show_x.selection()
                self._display_vertical_scalebar_ = show_y.selection()
                
                if xcal is not None:
                    cal_x       = x_prompt.value() * xcal.getUnits(img.axistags[0].key)
                    cal_x_len   = x_len_prompt.value() * xcal.getUnits(img.axistags[0].key)
                    
                    x           = xcal.getDistanceInSamples(cal_x, img.axistags[0].key)
                    x_len       = xcal.getDistanceInSamples(cal_x_len, img.axistags[0].key)
                    
                else:
                    x           = int(x_prompt.value())
                    x_len       = int(x_len_prompt.value())
                    
                    cal_x       = x
                    cal_x_len   = y_len
                    
                if ycal is not None:
                    cal_y       = y_prompt.value() * ycal.getUnits(img.axistags[1].key)
                    cal_y_len   = y_len_prompt.value() * ycal.getUnits(img.axistags[1].key)
                    
                    y           = ycal.getDistanceInSamples(cal_y, img.axistags[1].key)
                    y_len       = ycal.getDistanceInSamples(cal_y_len, img.axistags[1].key)
                    
                else:
                    y           = int(y_prompt.value())
                    y_len       = int(y_len_prompt.value())
                    
                    cal_y       = y
                    cal_y_len   = y_len
                    
                self._scaleBarOrigin_ = (x, y)
                self._scaleBarLength_ = (x_len, y_len)
                
                self.showScaleBars(calibrated_length = (cal_x_len, cal_y_len))
            
        else:
            if self._xScaleBar_ is not None:
                self._xScaleBar_.setVisible(False)
                
            if self._yScaleBar_ is not None:
                self._yScaleBar_.setVisible(False)
            
    def _setup_channels_display_actions_(self):
        if isinstance(self._data_, vigra.VigraArray):
            if self._data_.channels > 1:
                for channel in range(self._data_.channels):
                    action = self.channelsMenu.addAction("%d" % channel)
                    action.setCheckable(True)
                    action.setChecked(False)
                    action.triggered.connect(self.slot_displayChannel)
                    self.displayIndividualChannelActions.append("Channel %d" % channel)
                    
            else:
                self.channelsMenu.clear()
                    
                self.displayIndividualChannelActions.clear()
                
        else:
            pass
                
    
    @Slot()
    def slot_displayChannel(self):
        sender = self.sender()
        
        if sender in self.displayIndividualChannelActions:
            text = sender.text()
            
            try:
                channel_index = int(eval(text))
                
                self.displayChannel(channel_index)
                
            except:
                return
            
    @Slot()
    def slot_loadImageFromWorkspace(self):
        from core.workspacefunctions import getvarsbytype
        
        if self._scipyenWindow_ is None:
            return
        
        img_vars = dict(getvarsbytype(vigra.VigraArray, ws = self._scipyenWindow_.workspace))
        
        if len(img_vars) == 0:
            return
        
        name_list = sorted([name for name in img_vars.keys()])
        
        choiceDialog = ItemsListDialog(parent=self, itemsList = name_list)
        
        ans = choiceDialog.exec()
        
        if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
            image = img_vars[choiceDialog.selectedItemsText[0]]
            image_title = choiceDialog.selectedItemsText[0]
            self._data_var_name_ = choiceDialog.selectedItemsText[0]
            
            if isinstance(self._displayedChannel_, int):
                if self._displayedChannel_ >= image.channels:
                    self._displayedChannel_ = "all"
            
            self.view(image, doc_title = image_title, displayChannel = self._displayedChannel_)
        
    @Slot(bool)
    def slot_displayAllChannels(self, value):
        if value:
            self.displayAllChannels()
            
        
    # NOTE: 2017-07-25 22:07:49
    # TODO: generate calibrated coordinates here as well
    # as done for slot_displayMousePos;
    # TODO: factor out code for coordinate string generation 
    # (started in _displayValueAtCoordinates)
    # be aware that here the coordinates are a list
    # which may contain cursor window size as well
    @Slot(str, list)
    @safeWrapper
    def slot_displayCursorPos(self, value, coords):
        self._displayValueAtCoordinates(coords, value)

    @Slot(int,int)
    @safeWrapper
    def slot_displayMousePos(self, x, y):
        self._displayValueAtCoordinates((x,y))
        
    @Slot(object)
    @safeWrapper
    def slot_graphicsObjectAdded(self, obj):
        self.signal_graphicsObjectAdded.emit(obj)
        
    @Slot(object)
    @safeWrapper
    def slot_graphicsObjectChanged(self, obj):
        self.signal_graphicsObjectChanged.emit(obj)
        
    @Slot(object)
    @safeWrapper
    def slot_graphicsObjectRemoved(self, obj):
        self.signal_graphicsObjectRemoved.emit(obj)
        
    @Slot(object)
    @safeWrapper
    def slot_graphicsObjectSelected(self, obj):
        self.signal_graphicsObjectSelected.emit(obj)
        
    @Slot()
    @safeWrapper
    def slot_graphicsObjectDeselected(self):
        self.signal_graphicsObjectDeselected.emit()
        
    ####
    # private methods
    ####
    
    def _parseVigraArrayData_(self, img:vigra.VigraArray):
        """ Extract information about image axes to figure out how to display it.
        
        For now ImageViewer only accepts images with up to three dimensions.
        
        NOTE:
        1) a 3D 'image' (or 'volume') MAY be represented as a 4D vigra array 
            with a channel axis
        
        2) a 2D image MAY be represented as a 3D vigra array with a channel axis
        
        img is a vigra.VigraArray object
        
        """
        # NOTE: 2021-12-02 10:39:54
        # use axis indices instead of AxisInfo, in proposeLayout
        import io
        
        if img is None:
            return False
        
        if np.any(np.iscomplex(img)):
            self.criticalMessage("Error", "ImageViewer cannot yet display complex-valued data")
            return False
            
        try:
            layout = vu.proposeLayout(img, userFrameAxis = self.userFrameAxisInfo,
                                      timeVertical = self._display_time_vertical_,
                                      indices=True)
            
        except Exception as e:
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            self.errorMessage(type(e).__name__, "\n".join([sei[0].__class__.__name__, s.getvalue()]))
            return False
            
        try:
            # there may be a previous image stored here
            if self._data_ is not None and len(self.graphicsCursors) > 0: # parse width/height of previos image if any, to check against existing cursors
                if self._data_.shape[layout.horizontalAxis] != img.shape[layout.horizontalAxis] or \
                    self._data_.shape[layout.verticalAxis] != img.shape[layout.verticalAxis]:
                    self.questionMessage("Imageviewer:", "New image geometry will invalidate existing cursors.\nLoad image and bring all cursors to center?")
                    
                    ret = msgBox.exec()
                    
                    if ret == QtWidgets.QMessageBox.Cancel:
                        return False
                    
                    for c in self.graphicsCursors:
                        c.rangeX = img.shape[layout.horizontalAxis]
                        c.rangeY = img.shape[layout.verticalAxis]
                        c.setPos(img.shape[layout.horizontalAxis]/2, img.shape[layout.verticalAxis]/2)
            
            #self._number_of_frames_ = layout.nFrames if isinstance(layout.nFrames, (int, type(None))) else np.prod(layout.nFrames)
            self._data_frames_ = 0 if layout.nFrames is None else layout.nFrames if isinstance(layout.nFrames, int) else np.prod(layout.nFrames)

            if self._data_frames_ is None:
                self.criticalMessage("Error", "Cannot determine the number of frames in the data")
                return False
            
            #self.frameIndex = range(self._data_frames_)
        
            self.frameAxis  = layout.framesAxis
            
            self.widthAxis  = layout.horizontalAxis
            self.heightAxis = layout.verticalAxis
            
            with self.observed_vars.observer.hold_trait_notifications():
                self.observed_vars["data"] = self._data_
            
            return True
                
        except Exception as e:
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            self.errorMessage(type(e).__name__, "\n".join([sei[0].__class__.__name__, s.getvalue()]))
            #traceback.print_exc()
            return False
        
    def _applyColorTable_(self, image: vigra.VigraArray, colorMap:typing.Optional[colormaps.colors.Colormap]=None):
        """Applies the internal color table to the 2D array.
        
        Parameters:
        -----------
        image: vigra.VigraArray with ndim == 2: a 2D array, or a 2D slice view
            of a higher dimension array.
            
            NOTE: 2019-11-13 14:01:28
            This is called with self._currentFrameData_ passed as the "image"
            parameter.
            
            self._currentFrameData_ is either a 2D slice view, or a copy of it
            with np.nan values replaced by 0.0
            
        Returns:
        --------
        vigra.VigraArray: uint8 image with 4 channels. This is a copy of image, 
        with applied color table (see vigra.colors.applyColortable)
        """
        if not isinstance(colorMap, colormaps.colors.Colormap):
            colorMap  = self._colorMap
            
        if isinstance(image, vigra.VigraArray):
            if not isinstance(colorMap, colormaps.colors.Colormap):
                return image
            
            if np.isnan(image).any():
                return image
            
            if image.min() == image.max():
                return image
            
            lrMapImage = vigra.colors.linearRangeMapping(image)
            
            nMap = colormaps.colors.Normalize(vmin=0, vmax=255)
            
            sMap = colormaps.cm.ScalarMappable(norm = nMap, cmap = colorMap)
            
            sMap.set_array(range(256))
            cTable = sMap.to_rgba(range(256), bytes=True)
            #cFrame = vigra.colors.applyColortable(image.astype('uint32'), cTable)
            if image.ndim > 2:
                if image.channelIndex < image.ndim and image.channels > 1: # TODO FIXME
                    # NOTE 2017-10-05 14:17:00
                    # do NOT apply colormap to multi-band image
                    #cFrame = lrMapImage.copy()
                    return image
                else:
                    cFrame = vigra.colors.applyColortable(lrMapImage.astype('uint32'), cTable)
                    
            else:
                cFrame = vigra.colors.applyColortable(lrMapImage.astype('uint32'), cTable)
                
            return cFrame
        
        elif isinstance(image, (QtGui.QImage, QtGui.QPixmap)):
            return image
            # FIXME/TODO 2019-11-13 13:58:31
            # figure out how to apply color table to a QImage/QPixmap!
            #if isinstance(image, QtGui.QPixmap):
                #qimg = image.toImage()
                
            #else:
                #qimg = image
                
            #if qimg.isGrayScale():
                #q
    
    def _frameView_(self, channel):
        """Returns a slice (frame) of self._data_ along the self.frameAxis
        
        If the slice contains np.nan returns a copy of the image slice.
        
        Otherwise, returns a REFERENCE to the image slice.
        
        """
        if not isinstance(self._data_, vigra.VigraArray):
            raise RuntimeError("Wrong function call for a non-vigra array image")
        
        img_view = self._data_
        dimindices = []
        
        if self.frameAxis is not None:
            # NOTE: 2019-11-13 13:52:46
            # frameAxis is None only for 2D data arrays or 3D arrays with channel axis
            index = self.frameIndexBinding[self._current_frame_index_]
            dimindices = [index]
        
            if all(isinstance(ndx, tuple) for ndx in index):
                for ndx in index:
                    # NOTE: 2021-12-02 10:40:17
                    # axis infos are now axis indices (ints)
                    # see  NOTE: 2021-12-02 10:39:54
                    img_view = img_view.bindAxis(ndx[0], ndx[1])
                    #img_view = img_view.bindAxis(img_view.axistags.index(ndx[0].key), ndx[1])
                    
            else:
                #print("in self._frameView_: index", index)
                img_view = img_view.bindAxis(index[0], index[1])
                #img_view = img_view.bindAxis(img_view.axistags.index(index[0].key), index[1])
            
        #else:
            #img_view = self._data_
            
        # up to now, img_view is a 2D slice view of self._data_, will _ALL_ available channels
            
        # get a channel view on the 2D slice view of self._data_
        if isinstance(channel, int) and "c" in self._currentFrameData_.axistags and channel_index in range(self._currentFrameData_.channels):
            img_view = img_view.bindAxis("c", channel)
            
        # check for NaNs
        if np.isnan(img_view).any():             # if there are nans
            img_view = img.view.copy()           # make a copy
            img_view[np.isnan(img_view)] = 0.0   # replace nans with 0
            
            
        return img_view, dimindices
        
    @safeWrapper
    def displayFrame(self, channel_index = None, colorMap:typing.Optional[colormaps.colors.Colormap] = None, asAlphaChannel:bool=False):
        if channel_index is None:
            channel_index = self._displayedChannel_
            
        if not isinstance(colorMap, colormaps.colors.Colormap):
            colorMap = self._colorMap
                
        if isinstance(channel_index, str):
            if channel_index.lower().strip() != "all":
                raise ValueError("When a string, channel_index must be 'all' -- case-insensitive; got %s instead" % channel_index)
            
        elif isinstance(channel_index, int):
            if channel_index < 0:
                raise ValueError("When an int, channel_index must be >= 0; got %d instead" % channel_index)
            
            if isinstance(self._data_, vigra.VigraArray):
                if channel_index >= self._data_.channels:
                    raise ValueError("Invalid channel_index %d for an image with %d channels" % (channel_index, self._data_.channels))
        
        if channel_index is not self._displayedChannel_:
            self._displayedChannel_ = channel_index
        
        if isinstance(self._data_, vigra.VigraArray):
            self._currentFrameData_, _ = self._frameView_(channel_index) # this is an array view !
            
            if asAlphaChannel:
                if self._currentFrameData_.channels == 1:
                    if self._currentFrameData_.channelIndex < self._currentFrameData_.ndim:
                        self._currentFrameData_ = self._currentFrameData_.squeeze()
                        
                    red = vigra.VigraArray(np.full(self._currentFrameData_.shape, fill_value=0.),
                                             axistags=vigra.VigraArray.defaultAxistags('xy'))
                    
                    green = vigra.VigraArray(np.full(self._currentFrameData_.shape, fill_value=0.),
                                             axistags=vigra.VigraArray.defaultAxistags('xy'))
                    
                    blue = vigra.VigraArray(np.full(self._currentFrameData_.shape, fill_value=0.),
                                             axistags=vigra.VigraArray.defaultAxistags('xy'))
                    
                    frame = vigra.VigraArray(np.concatenate((red[Ellipsis, np.newaxis],
                                                             green[Ellipsis, np.newaxis],
                                                             blue[Ellipsis,np.newaxis],
                                                             self._currentFrameData_[Ellipsis,np.newaxis]),
                                                            axis=2),
                                            axistags = vigra.VigraArray.defaultAxistags('xyc'))
                    
                    self.viewerWidget.view(frame.qimage(normalize=False))
                    #if frame.min() == frame.max():
                        #self.viewerWidget.view(frame.qimage(normalize=False))
                    #else:
                        #self.viewerWidget.view(frame.qimage(normalize=self._imageNormalize))
                    
            else:
                if isinstance(colorMap, colormaps.colors.Colormap):
                    if self._currentFrameData_.channels == 1:
                        if self._currentFrameData_.channelIndex < self._currentFrameData_.ndim:
                            self._currentFrameData_ = self._currentFrameData_.squeeze()
                            
                        cFrame = self._applyColorTable_(self._currentFrameData_, colorMap)
                        # print(f"ImageViewer {self.windowTitle()} displayFrame colorMap {colorMap.name} image dtype {cFrame.dtype}")
                        if cFrame.min() == cFrame.max():
                            self.viewerWidget.view(cFrame.qimage(normalize = False))
                        else:
                            self.viewerWidget.view(cFrame.qimage(normalize = self._imageNormalize))
                        
                    else: # don't apply color map to a multi-band frame data
                        #warnings.warn(f"{self.__class__.__name__} <{self.windowTitle()}>: Cannot apply color map to a multi-band image")
                        self._currentFrameData_ = self._currentFrameData_.squeeze().copy()
                        self.viewerWidget.view(self._currentFrameData_.qimage(normalize = self._imageNormalize))
                
                else:
                    if self._currentFrameData_.min() == cFrame.max():
                        self.viewerWidget.view(self._currentFrameData_.qimage(normalize = False))
                    else:
                        self.viewerWidget.view(self._currentFrameData_.qimage(normalize = self._imageNormalize))
                
            # TODO FIXME: what if we view a transposed array ???? (e.g. viewing it on
            # Y or X axis instead of the Z or T axis?)
            #width_axis_ndx = self._data_.axistags.index(self.widthAxis.key)
            #height_axis_ndx = self._data_.axistags.index(self.heightAxis.key)
            w = self._data_.shape[self.widthAxis] # this is not neccessarily space!
            h = self._data_.shape[self.heightAxis] # this is not neccessarily space!
            
            self._image_width_ = w
            self._image_height_= h
            
            # NOTE: 2017-07-26 22:18:14
            # get calibrates axes sizes
            if self._axes_calibration_ is not None:
                cals = "(%s x %s)" % (self._axes_calibration_.calibrations[self.widthAxis].calibratedDistance(w),
                                      self._axes_calibration_.calibrations[self.heightAxis].calibratedDistance(h))
            else:
                cals = "(%s x %s)" % \
                    (quantity2str(vu.getCalibratedAxisSize(self._data_, self.widthAxis)), \
                        quantity2str(vu.getCalibratedAxisSize(self._data_, self.heightAxis)))
    
            shapeTxt = "%s x %s: %d x %d %s" % \
                (axisTypeName(self._data_.axistags[self.widthAxis]), \
                    axisTypeName(self._data_.axistags[self.heightAxis]), \
                    w, h, cals)
            
            self.slot_displayColorBar(self.displayColorBarAction.isChecked())

        elif isinstance(self._data_, (QtGui.QImage, QtGui.QPixmap)):
            # NOTE 2018-09-14 11:45:13
            # TODO/FIXME adapt code to select channels from a Qimage is not allGray() or not isGrayscale()
            self.viewerWidget.view(self._data_)
            
            w = self._data_.width()
            h = self._data_.height()
            shapeTxt = "W x H: %d x %d " % (w, h)
            
        elif isinstance(self._data_, np.ndarray):
            if self._data_.ndim == 1:
                pass
            
        else:
            return # shouldn't really get here
        
        self.viewerWidget.setTopLabelText(shapeTxt)
        
        z_coord_str = self._display_Z_coordinate()
        if len(z_coord_str.strip()):
            self.statusBar().showMessage(z_coord_str)
            
    def setDataDisplayEnabled(self, value):
        self.viewerWidgetContainer.setEnabled(value is True)
        
    def _configureUI_(self):
        self.setupUi(self)
        
        #self.setWindowTitle("Image Viewer")
        
        # NOTE: 2022-11-05 23:26:25
        # adding a custom widget in a placeholder in the UI form; this is because
        # widgets defined in Scipyen have no Qt 5 Designer equivalent
        # the placeholder is a QWidget () in the UI form
        # we set the placeholder's layout to a gridlayout with tight spacing &
        # margins
        # then we create an instance of the custom widgtet with this placeholder
        # as parent
        # finally, we add the custom Scipyen widget to the placeholder grid 
        # layout at position 0,0
        #
        # The placeholder here is self.viewerWidgetContainer (defined in the 
        # Designer UI form)
        if self.viewerWidgetContainer.layout() is None:
            self.viewerWidgetContainer.setLayout(QtWidgets.QGridLayout(self.viewerWidgetContainer))
            
        self.viewerWidgetContainer.layout().setSpacing(0)
        self.viewerWidgetContainer.layout().setContentsMargins(0,0,0,0)
        
        self.intensityCalibrationWidget = None
            
        self.viewerWidget = GraphicsImageViewerWidget(parent = self.viewerWidgetContainer, imageViewer=self)
        
        # NOTE: 2022-11-05 23:28:39
        # presumably, these tweaks are redundant
        self.viewerWidgetContainer.layout().setHorizontalSpacing(0)
        self.viewerWidgetContainer.layout().setVerticalSpacing(0)
        self.viewerWidgetContainer.layout().contentsMargins().setLeft(0)
        self.viewerWidgetContainer.layout().contentsMargins().setRight(0)
        self.viewerWidgetContainer.layout().contentsMargins().setTop(0)
        self.viewerWidgetContainer.layout().contentsMargins().setBottom(0)
        
        self.viewerWidgetContainer.layout().addWidget(self.viewerWidget, 0,0)
        
        # NOTE: 2017-12-18 09:37:07 this relates to mouse cursor position!!!
        self.viewerWidget.signalCursorAt[str, list].connect(self.slot_displayCursorPos)
        
        self.viewerWidget.scene.signalMouseAt[int, int].connect(self.slot_displayMousePos)
        
        self.viewerWidget.signalCursorAdded[object].connect(self.slot_graphicsObjectAdded)
        #self.viewerWidget.signalCursorChanged[object].connect(self.slot_graphicsObjectChanged)
        self.viewerWidget.signalCursorRemoved[object].connect(self.slot_graphicsObjectRemoved)
        self.viewerWidget.signalGraphicsObjectSelected[object].connect(self.slot_graphicsObjectSelected)
        
        self.viewerWidget.signalRoiAdded[object].connect(self.slot_graphicsObjectAdded)
        #self.viewerWidget.signalRoiChanged[object].connect(self.slot_graphicsObjectChanged)
        self.viewerWidget.signalRoiRemoved[object].connect(self.slot_graphicsObjectRemoved)
        self.viewerWidget.signalRoiSelected[object].connect(self.slot_graphicsObjectSelected)
        
        self.viewerWidget.signalGraphicsDeselected.connect(self.slot_graphicsObjectDeselected)
        
        self.actionView.triggered.connect(self.slot_loadImageFromWorkspace)
        self.actionRefresh.triggered.connect(self.slot_refreshDataDisplay)
        
        self.actionExportAsPNG.triggered.connect(self.slot_exportSceneAsPNG)
        self.actionExportAsSVG.triggered.connect(self.slot_exportSceneAsSVG)
        self.actionExportAsTIFF.triggered.connect(self.slot_exportSceneAsTIFF)
        self.actionSaveTIFF.triggered.connect(self.slot_saveTIFF)
        
        self.displayMenu = QtWidgets.QMenu("Display", self)
        self.menubar.addMenu(self.displayMenu)
        
        self.channelsMenu = QtWidgets.QMenu("Channels", self)
        self.displayMenu.addMenu(self.channelsMenu)
        
        self.showAllChannelsAction = self.channelsMenu.addAction("All channels")
        self.showAllChannelsAction.setCheckable(True)
        self.showAllChannelsAction.setChecked(True)
        self.showAllChannelsAction.toggled[bool].connect(self.slot_displayAllChannels)
        
        self.displayIndividualChannelActions = list()
        
        self.displayScaleBarAction = self.displayMenu.addAction("Scale bar")
        self.displayScaleBarAction.setCheckable(True)
        self.displayScaleBarAction.setChecked(False)
        self.displayScaleBarAction.toggled[bool].connect(self.slot_displayScaleBar)
        
        self.displayColorBarAction = self.displayMenu.addAction("Intensity Scale")
        self.displayColorBarAction.setCheckable(True)
        self.displayColorBarAction.setChecked(False)
        self.displayColorBarAction.toggled[bool].connect(self.slot_displayColorBar)
        
        self.brightContrastGammaMenu = QtWidgets.QMenu("Brightness Contrast Gamma", self)
        self.displayMenu.addMenu(self.brightContrastGammaMenu)
        
        self.imageBrightnessAction = self.brightContrastGammaMenu.addAction("Brightness")
        self.imageGammaAction = self.brightContrastGammaMenu.addAction("Gamma")
        
        self.cursorsAppearanceMenu = QtWidgets.QMenu("Cursor appearance", self)
        self.displayMenu.addMenu(self.cursorsAppearanceMenu)
        
        self.chooseCursorColorAction = self.cursorsAppearanceMenu.addAction("Line")
        self.chooseCursorColorAction.triggered.connect(self.slot_chooseCursorsColor)
        
        self.chooseCursorLabelTextColorAction = self.cursorsAppearanceMenu.addAction("Label text")
        self.chooseCursorLabelTextColorAction.triggered.connect(self.slot_chooseCursorLabelTextColor)
        
        self.chooseCursorLabelBGColorAction = self.cursorsAppearanceMenu.addAction("Label background")
        self.chooseCursorLabelBGColorAction.triggered.connect(self.slot_chooseCursorLabelBGColor)
        
        self.linkedCursorColorsMenu = QtWidgets.QMenu("Linked cursors", self)
        self.cursorsAppearanceMenu.addMenu(self.linkedCursorColorsMenu)
        
        self.chooseLinkedCursorColorAction = self.linkedCursorColorsMenu.addAction("Line")
        self.chooseLinkedCursorColorAction.triggered.connect(self.slot_chooseLinkedCursorsColor)
        
        self.chooseLinkedCursorLabelTextColorAction = self.linkedCursorColorsMenu.addAction("Label text")
        self.chooseLinkedCursorLabelTextColorAction.triggered.connect(self.slot_chooseLinkedCursorLabelTextColor)
        
        self.chooseLinkedCursorLabelBGColorAction = self.linkedCursorColorsMenu.addAction("Label background")
        self.chooseLinkedCursorLabelBGColorAction.triggered.connect(self.slot_chooseLinkedCursorBGColor)
        
        self.opaqueCursorLabelAction = self.cursorsAppearanceMenu.addAction("Opaque cursor labels")
        self.opaqueCursorLabelAction.setCheckable(True)
        self.opaqueCursorLabelAction.setChecked(self.opaqueCursorLabel)
        self.opaqueCursorLabelAction.toggled[bool].connect(self.slot_setOpaqueCursorLabels)
    
        self.roisAppearanceMenu = QtWidgets.QMenu("ROI appearance", self)
        self.displayMenu.addMenu(self.roisAppearanceMenu)
        
        self.chooseRoiColorAction = self.roisAppearanceMenu.addAction("Set rois color")
        self.chooseRoiColorAction.triggered.connect(self.slot_chooseRoisColor)
    
        self.chooseROILabelTextColorAction = self.roisAppearanceMenu.addAction("Set text color for ROI labels")
        self.chooseROILabelTextColorAction.triggered.connect(self.slot_chooseRoisLabelTextColor)
    
        self.linkedROIColorsMenu = QtWidgets.QMenu("Linked ROIs", self)
        self.cursorsAppearanceMenu.addMenu(self.linkedROIColorsMenu)
        
        self.chooseLinkedRoiColorAction = self.linkedROIColorsMenu.addAction("Set color for linked rois")
        self.chooseLinkedRoiColorAction.triggered.connect(self.slot_chooseLinkedRoisColor)
        
        self.chooseLinkedROILabelTextColorAction = self.linkedROIColorsMenu.addAction("Set text color for linked ROI labels")
        self.chooseLinkedROILabelTextColorAction.triggered.connect(self.slot_chooseLinkedRoisLabelTextColor)
    
        self.opaqueROILabelAction = self.cursorsAppearanceMenu.addAction("Opaque ROI labels")
        self.opaqueROILabelAction.setCheckable(True)
        self.opaqueROILabelAction.setChecked(self.opaqueCursorLabel)
        self.opaqueROILabelAction.toggled[bool].connect(self.slot_setOpaqueROILabels)
    
        self.colorMapMenu = QtWidgets.QMenu("Color Map", self)
        self.displayMenu.addMenu(self.colorMapMenu)
        
        self.colorMapAction = self.colorMapMenu.addAction("Choose Color Map")
        self.editColorMapAction = self.colorMapMenu.addAction("Edit Color Map")
        
        self.framesQSlider.setMinimum(0)
        self.framesQSlider.setMaximum(0)
        self.framesQSlider.valueChanged.connect(self.slot_setFrameNumber)
        
        self._frames_slider_ = self.framesQSlider
        
        self.framesQSpinBox.setKeyboardTracking(False)
        self.framesQSpinBox.setMinimum(0)
        self.framesQSpinBox.setMaximum(0)
        self.framesQSpinBox.valueChanged.connect(self.slot_setFrameNumber)
        
        self._frames_spinner_ = self.framesQSpinBox

        self.editColorMapAction.triggered.connect(self._editColorMap)

        self.colorMapAction.triggered.connect(self.slot_chooseColorMap)
        self.imageBrightnessAction.triggered.connect(self._editImageBrightness)
        self.imageGammaAction.triggered.connect(self._editImageGamma)
        
        self.cursorsMenu = QtWidgets.QMenu("Cursors", self)
        
        self.menubar.addMenu(self.cursorsMenu)
        
        self.addCursorsMenu = QtWidgets.QMenu("Add Cursors", self)
        self.cursorsMenu.addMenu(self.addCursorsMenu)
        
        self.addVerticalCursorAction = self.addCursorsMenu.addAction("Vertical Cursor")
        self.addVerticalCursorAction.triggered.connect(self.viewerWidget.slot_newVerticalCursor)
        
        self.addHorizontalCursorAction = self.addCursorsMenu.addAction("Horizontal Cursor")
        self.addHorizontalCursorAction.triggered.connect(self.viewerWidget.slot_newHorizontalCursor)
        
        self.addCrosshairCursorAction = self.addCursorsMenu.addAction("Crosshair Cursor")
        self.addCrosshairCursorAction.triggered.connect(self.viewerWidget.slot_newCrosshairCursor)
        
        self.addPointCursorAction = self.addCursorsMenu.addAction("Point Cursor")
        self.addPointCursorAction.triggered.connect(self.viewerWidget.slot_newPointCursor)
        
        self.editCursorsMenu = QtWidgets.QMenu("Edit cursors", self)
        self.cursorsMenu.addMenu(self.editCursorsMenu)
        
        self.editCursorAction = self.editCursorsMenu.addAction("Edit Properties for Selected Cursor...")
        self.editCursorAction.triggered.connect(self.viewerWidget.slot_editSelectedCursor)
        
        self.editAnyCursorAction = self.editCursorsMenu.addAction("Edit Cursor Properties...")
        self.editAnyCursorAction.triggered.connect(self.viewerWidget.slot_editAnyCursor)
        
        self.removeCursorsMenu = QtWidgets.QMenu("Remove Cursors")
        
        self.removeCursorAction = self.removeCursorsMenu.addAction("Remove Selected Cursor")
        self.removeCursorAction.triggered.connect(self.viewerWidget.slot_removeSelectedCursor)
        
        self.removeCursorsAction = self.removeCursorsMenu.addAction("Remove cursors ...")
        self.removeCursorsAction.triggered.connect(self.viewerWidget.slot_removeCursors)
        
        self.removeAllCursorsAction = self.removeCursorsMenu.addAction("Remove All Cursors")
        self.removeAllCursorsAction.triggered.connect(self.viewerWidget.slot_removeAllCursors)
        
        self.cursorsMenu.addMenu(self.removeCursorsMenu)
        
        self.roisMenu = QtWidgets.QMenu("ROIs", self)
        
        # NOTE: 2017-08-10 10:23:52
        # TODO: add Point, Line, Rectangle, Ellipse, Polygon, Path, Text
        # for each of the above, give option to use the Mouse, or a dialogue for coordinates
        # to be able to generate several cursors and/or ROIs without clicking via too many
        # menus, TODO toolbar buttons (toggable) to create these
        #
        # TODO in addition, give the option to create pies and chords (secants), closed/open
        #
        # NOTE: all signals must be connected to appropriate viewerWidget slots!
        
        self.menubar.addMenu(self.roisMenu)
        
        self.addROIsMenu = QtWidgets.QMenu("Add ROIs", self)
        self.roisMenu.addMenu(self.addROIsMenu)
        
        self.newROIAction = self.addROIsMenu.addAction("New ROI")
        self.newROIAction.triggered.connect(self.viewerWidget.buildROI)
        
        self.editRoisMenu = QtWidgets.QMenu("Edit ROIs")
        self.roisMenu.addMenu(self.editRoisMenu)
        
        self.editSelectedRoiShapeAction = self.editRoisMenu.addAction("Selected ROI shape")
        self.editSelectedRoiShapeAction.triggered.connect(self.viewerWidget.slot_editRoiShape)
        
        self.editSelectedRoiPropertiesAction = self.editRoisMenu.addAction("Selected ROI Properties")
        self.editSelectedRoiPropertiesAction.triggered.connect(self.viewerWidget.slot_editRoiProperties)
        
        self.editRoiAction = self.editRoisMenu.addAction("Edit ROI...")
        self.editRoiAction.triggered.connect(self.viewerWidget.slot_editRoi)
        
        self.removeRoisMenu = QtWidgets.QMenu("Remove ROIs")
        self.roisMenu.addMenu(self.removeRoisMenu)
        
        self.removeSelectedRoiAction = self.removeRoisMenu.addAction("Remove Selected ROI")
        self.removeSelectedRoiAction.triggered.connect(self.viewerWidget.slot_removeSelectedRoi)
        
        self.removeAllRoisAction = self.removeRoisMenu.addAction("Remove All ROIS")
        self.removeAllRoisAction.triggered.connect(self.viewerWidget.slot_removeAllRois)
        
        self.toolBar = QtWidgets.QToolBar("Main", self)
        self.toolBar.setObjectName("%s_Main_Toolbar" % self.__class__.__name__)
        
        refreshAction = self.toolBar.addAction(QtGui.QIcon.fromTheme("view-refresh"), "Refresh")
        refreshAction.triggered.connect(self.slot_refreshDataDisplay)
        
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        
        self.zoomToolBar = QtWidgets.QToolBar("Zoom Toolbar", self)
        self.zoomToolBar.setObjectName("ImageViewerZoomToolBar")
        
        self.zoomOutAction = self.zoomToolBar.addAction(QtGui.QIcon.fromTheme("zoom-out"), "Zoom Out")
        self.zoomOriginalAction = self.zoomToolBar.addAction(QtGui.QIcon.fromTheme("zoom-original"), "Original Zoom")
        self.zoomInAction = self.zoomToolBar.addAction(QtGui.QIcon.fromTheme("zoom-in"), "Zoom In")
        self.zoomAction = self.zoomToolBar.addAction(QtGui.QIcon.fromTheme("zoom"), "Zoom")
        
        self.zoomOutAction.triggered.connect(self.slot_zoomOut)
        self.zoomOriginalAction.triggered.connect(self.slot_zoomOriginal)
        self.zoomInAction.triggered.connect(self.slot_zoomIn)
        self.zoomAction.triggered.connect(self.slot_selectZoom)

        self.addToolBar(QtCore.Qt.TopToolBarArea, self.zoomToolBar)
        
    def _editColorMap(self):
        pass
    
    @Slot(str)
    @safeWrapper
    def slot_testColorMap(self, item:str):
        # NOTE 2020-11-28 10:19:07
        # upgrade to matplotlib 3.x
        if item in  mpl.colormaps:
            colorMap =  mpl.colormaps.get(item)
            self.displayFrame(colorMap=colorMap)
          
    @Slot()
    @safeWrapper
    def slot_chooseColorMap(self, *args):
        if self._data_ is None:
            return
        
        if not isinstance(self._data_, vigra.VigraArray) or self._currentFrameData_.channels > 1:
            QtWidgets.QMessageBox.information(self,"Choose Color Map","Cannot apply color maps to multi-channel images")
            return
        
        self._prevColorMap = self._colorMap # cache the current colorMap
        
        # NOTE 2020-11-28 10:19:07
        # upgrade to matplotlib 3.x
        colormapnames = sorted([n for n in mpl.colormaps.keys()])
        
        if isinstance(self._colorMap, colormaps.colors.Colormap):
            d = ItemsListDialog(self, itemsList=colormapnames,
                                     title="Select color map",
                                     preSelected=self._colorMap.name)
            
        else:
            d = ItemsListDialog(self, itemsList=colormapnames, 
                                     title="Select color map", 
                                     preSelected="None")
            
        d.itemSelected.connect(self.slot_testColorMap) # this will SET self._colorMap to the selected one
    
        a = d.exec_()

        if a == QtWidgets.QDialog.Accepted:
            selItems = d.selectedItemsText
            if len(selItems):
                self.colorMap = selItems[0]
            self.displayFrame()
            
        else:
            self.colorMap = self._prevColorMap
            self.displayFrame()

    def _editImageBrightness(self):
        dlg = ImageBrightnessDialog(self)
        # dlg = pgui.ImageBrightnessDialog(self)
        dlg.show()
        
    def _editImageGamma(self):
        pass;
    

    def _displayValueAtCoordinates(self, coords, crsId=None):
        """
        coords: a list or tuple with 2 -- 4 elements:
                (x,y), (x,y,wx), (x,y,wx,wy) where any can be None
                x,y = coordinates in the displayed frame
                wx, wy = range along the horizontal (wx) and vertical (wy) axis 
                         centered around x and y coordinate, respectively
                         
        crsId: string with cursor ID or None
        """
        if self._data_ is None:
            return
        
        #if self._currentFrameData_ is None:
            #return
            
        # NOTE: 2021-12-03 09:40:11 because self.frameAxis is now an int or a 
        # tuple of ints we need tpo convert these back to axisinfo
        
        if coords[0] is not None:
            x = int(coords[0])
        else:
            x = None
            
        if coords[1] is not None:
            y = int(coords[1])
        else:
            y = None
        
        if len(coords) == 3:
            wx = coords[2]
        else:
            wx = None
        
        if len(coords) == 4:
            wy = coords[3]
        else:
            wy = None
            
        if isinstance(self._data_, vigra.VigraArray):
            # this can also be a PictArray! 
            # NOTE: 2020-09-04 08:51:38 PictArray is defunct and removed from the API
            # NOTE: 2017-07-24 09:03:38
            # w and h are a convention here
            #w = self._data_.shape[0]
            #h = self._data_.shape[1]
            
            #widthAxisIndex = self._data_.axistags.index(self.widthAxis.key)
            #heightAxisIndex = self._data_.axistags.index(self.heightAxis.key)
            
            w = self._data_.shape[self.widthAxis]
            h = self._data_.shape[self.heightAxis]
            
            # NOTE: 2021-12-02 10:57:24
            # this is now requires because of NOTE: 2021-12-02 10:39:54
            wAxInfo = self._data_.axistags[self.widthAxis]
            hAxInfo = self._data_.axistags[self.heightAxis]
            
            #
            # below, img is a view NOT a copy !
            #
            
            img, _ = self._frameView_(self._displayedChannel_)
            
            viewWidthAxisIndex = img.axistags.index(wAxInfo.key)
            viewHeightAxisIndex = img.axistags.index(hAxInfo.key)
            
            viewW = img.shape[viewWidthAxisIndex]
            viewH = img.shape[viewHeightAxisIndex]
            
            # NOTE: 2021-10-25 22:26:53
            # when given, wx and wy below are, horizontal & vertical cursor
            # windows, respectively
            
            if wx is not None:
                if self._axes_calibration_:
                    cwx = self._axes_calibration_[viewWidthAxisIndex].calibratedDistance(wx)
                    swx = " +/- %d (%s) " % (wx//2, quantity2str(cwx/2))
                    
            else:
                swx = ""
                
            if wy is not None:
                if self._axes_calibration_:
                    cwy = self._axes_calibration_[viewHeightAxisIndex].calibratedDistance(wy)
                    swy = " +/- %d (%s) " % (wy//2, quantity2str(cwy/2))
                    
            else:
                swy = ""
            
            if crsId is not None:
                crstxt = "%s " % (crsId)
                
            else:
                crstxt = ""
                
            if x is not None and x >= w:
                x = w-1
                
            if x is not None and x < 0:
                x = 0
                
            if y is not None and y >= h:
                y = h-1
                
            if y is not None and y < 0:
                y = 0

            #print("w: %f, x: %f, h: %f, y: %f" % (w, x, h, y))
            
            if all([v_ is not None for v_ in (x,y)]):
                if img.ndim >= 2: # there may be a channel axis
                    if self._axes_calibration_:
                        cx = self._axes_calibration_[viewWidthAxisIndex].calibratedMeasure(x)
                        cy = self._axes_calibration_[viewHeightAxisIndex].calibratedMeasure(y)
                        scx = quantity2str(cx)
                        scy = quantity2str(cy)
                    else:
                        scx = ""
                        scy = ""
                        
                    widthAxisKey = img.axistags[viewWidthAxisIndex].key 
                    heightAxisKey = img.axistags[viewHeightAxisIndex].key
                    
                    if img.ndim > 2: # this is possible only when there is a channel axis!
                        if img.channels > 1:
                            val = [float(img.bindAxis("c", k)[x,y,...]) for k in range(img.channels)]
                            
                            if self._axes_calibration_:
                                channelNdx = self._axes_calibration_["c"].channelIndices
                                cval = [self._axes_calibration_["c"].getChannelCalibration(channelNdx[k])[1].calibratedMeasure(val[k]) for k in range(img.channels)]
                                sval = "(%s)" % "; ".join(["%s" % quantity2str(v) for v in cval])
                                
                            else:
                                sval = "(%s)" % "; ".join(["%.2f" % v for v in val])
                        
                        else: 
                            # NOITE: 2022-10-06 17:15:22
                            # single channel => channelCalibration only has ONE channel
                            # but WARNING: if calling with index argument, one MUST specify
                            # the value of the channel's property, which is not always
                            # what you expect.
                            #
                            # If in doubt, then just call without specifying the index
                            val = float(img[x,y])
                            if self._axes_calibration_:
                                cval = self._axes_calibration_["c"].getChannelCalibration().calibratedMeasure(val)
                                # cval = self._axes_calibration_["c"].getChannelCalibration()[1].calibratedMeasure(val)
                                sval = "(%s)" % quantity2str(cval)
                            else:
                                sval = "(%.2f)" % val
                            
                        if self.frameAxis is not None:
                            #if isinstance(self.frameAxis, vigra.AxisInfo):
                            if isinstance(self.frameAxis, int):
                                if self.frameAxis >= self._data_.ndim:
                                    raise RuntimeError(f"frame axis {self.frameAxis} not found in the image")
                                frameAxis = self._data_.axistags[self.frameAxis]
                                zAxisKey = frameAxis.key
                                
                                if self._axes_calibration_:
                                    cz = self._axes_calibration_[frameAxis.key].calibratedMeasure(self._current_frame_index_)
                                    scz = quantity2str(cz)
                                else:
                                    scz = ""
                                
                                coordTxt = "%s<X: %d (%s: %s)%s, Y: %d (%s: %s)%s, Z: %d (%s: %s)> %s" % \
                                    (crstxt, 
                                    x, widthAxisKey, scx, swx, 
                                    y, heightAxisKey, scy, swy,
                                    self._current_frame_index_, zAxisKey, scz,
                                    sval)
                            
                            else: # self.frameAxis is a tuple
                                #frameAxis = tuple(self._data_.axistags.index(ax) for ax in self.frameAxis)
                                if self._axes_calibration_:
                                    sz_cz = ", ".join([f"{ndx[0]}: {ndx[1]} ({quantity2str(self._axes_calibration_[self._data_.axistags[ndx[0]]].calibratedDistance(ndx[1]))})" for ndx in reversed(self.frameIndexBinding[self._current_frame_index_])])
                                else:
                                    sz_cz = ", ".join([f"{ndx[0]}: {ndx[1]}" for ndx in reversed(self.frameIndexBinding[self._current_frame_index_])])
                                
                                #if self._axes_calibration_:
                                    #sz_cz = ", ".join([f"{ndx[0].key}: {ndx[1]} ({quantity2str(self._axes_calibration_[ndx[0].key].calibratedDistance(ndx[1]))})" for ndx in reversed(self.frameIndexBinding[self._current_frame_index_])])
                                #else:
                                    #sz_cz = ", ".join([f"{ndx[0].key}: {ndx[1]}" for ndx in reversed(self.frameIndexBinding[self._current_frame_index_])])
                                
                                coordTxt = "%s<X: %d (%s: %s)%s, Y: %d (%s: %s)%s, Z: %d (%s)> %s" % \
                                    (crstxt, \
                                    x, widthAxisKey, scx, swx, \
                                    y, heightAxisKey, scy, swy, \
                                    self._current_frame_index_, sz_cz, \
                                    val)
                                    
                        else:
                            if isinstance(val, float):
                                coordTxt = "%s<X: %d (%s: %s)%s, Y: %d (%s: %s)%s> %s" % \
                                    (crstxt, \
                                    x, widthAxisKey, scx, swx, \
                                    y, heightAxisKey, scy, swy, \
                                    val)
                                
                            elif isinstance(val, (tuple, list)):
                                valstr = "(" + " ".join(["%.2f" % v for v in val]) + ")"
                                    
                                coordTxt = "%s<X: %d (%s: %s)%s, Y: %d (%s: %s)%s> %s" % \
                                    (crstxt, \
                                    x, widthAxisKey, scx, swx, \
                                    y, heightAxisKey, scy, swy, \
                                    valstr)
                                
                                
                    else: # ndim == 2
                        val = float(np.squeeze(img[x,y]))
                        
                        coordTxt = "%s<X: %d (%s: %s)%s, Y: %d (%s: %s)%s> %.2f" % \
                            (crstxt, \
                            x, widthAxisKey, scx, swx, \
                            y, heightAxisKey, scy, swy, \
                            val)
                    
                else: # ndim < 2 shouldn't realy get here, should we ?!?
                    val = float(img[x])
                    
                    if self._axes_calibration_:
                        cx = self._axes_calibration_[viewWidthAxisIndex].calibratedMeasure(x)
                        scx = quantity2str(cx)
                    else:
                        scx = ""

                    widthAxisKey = img.axistags[viewWidthAxisIndex].key
                    
                    coordTxt = "%s<X: %d (%s: %s)%s> %.2f" % \
                        (crstxt, x, widthAxisKey, scx, swx, val)
                    
            else:
                c_list = list()
                
                if y is None:
                    if self._axes_calibration_:
                        cx = self._axes_calibration_[viewWidthAxisIndex].calibratedMeasure(x)
                        scx = quantity2str(cx)
                    else:
                        scx = ""

                    widthAxisKey = img.axistags[viewWidthAxisIndex].key
                    
                    c_list.append("%s<X: %d (%s: %s)%s" % ((crstxt, x, widthAxisKey, scx, swx)))
                    
                elif x is None:
                    if self._axes_calibration_:
                        cy = self._axes_calibration_[viewHeightAxisIndex].calibratedMeasure(y)
                        scy = quantity2str(cy)
                    else:
                        scy = ""

                    heightAxisKey = img.axistags[viewHeightAxisIndex].key
                    
                    c_list.append("%s<Y: %d (%s: %s)%s" % ((crstxt, y, heightAxisKey, scy, swy)))
                
                if img.ndim > 2:
                    if self.frameAxis is not None:
                        if isinstance(self.frameAxis, (vigra.AxisInfo, int)):
                            #if self.frameAxis not in self._data_.axistags:
                            if self.frameAxis >= img.ndim:
                                raise RuntimeError(f"frame axis {self.frameAxis} %s not found in the image")
                        
                            if self._axes_calibration_:
                                cz = quantity2str(self._axes_calibration_[self._data_.axistags[self.frameAxis].key].calibratedMeasure(self._current_frame_index_))
                            else:
                                cz = ""
                        
                            sz = self.frameAxis.key if isinstance(self.frameAxis, vigra.AxisInfo) else self._data_.axistags[self.frameAxis].key
                        
                            c_list.append(", Z: %d (%s: %s)>" % (self._current_frame_index_, sz, cz))
                            
                        else:
                            if self._axes_calibration_:
                                sz_cz = ", ".join(["%s: %s" % (self._data_.axistags[ax].key, quantity2str(self._axes_calibration_[self._data_.axistags[ax].key].calibratedMeasure(self._current_frame_index_))) for ax in self.frameAxis])
                                
                            else:
                                sz_cz = ", ".join(["%s: %s" % (sedlf._data_.axistags[ax].key, self._current_frame_index_) for ax in self.frameAxis])
                                
                            c_list.append("(%s)" % sz_cz)
    
                    else:
                        c_list.append(">")
                    
                else:
                    c_list.append(">")
                
                coordTxt = "".join(c_list)
                
                    
            self.statusBar().showMessage(coordTxt)
            
        elif isinstance(self._data_, (QtGui.QImage, QtGui.QPixmap)):
            w = self._data_.width()
            h = self._data_.height()
        
            if wx is not None:
                swx = " +/- %d " % (wx//2)
            else:
                swx = ""
                
            if wy is not None:
                swy = " +/- %d " % (wy//2)
            else:
                swy = ""
            
            if crsId is not None:
                crstxt = "%s " % (crsId)
            else:
                crstxt = ""

            if isinstance(self._data_, QtGui.QImage):
                #val = self._data_.pixel(x,y)
                if self._data_.isGrayscale():
                    val = self._data_.pixel(x,y)
                    
                else:
                    pval = self._data_.pixelColor(x,y)
                    val = "R: %d, G: %d, B: %d, A: %d" % (pval.red(), pval.green(), pval.blue(), pval.alpha())
                    
                    
                msg = "%s<X %d%s, Y %d%s> : %s" % \
                    (crstxt, x, swx, y, swy, val)

            elif isinstance(self._data_, QtGui.QPixmap):
                pix = self._data_.toImage()
                if pix.isGrayscale():
                    val = pix.pixel(x,y)
                    
                else:
                    pval = pix.pixelColor(x,y)
                    val = "R: %d, G: %d, B: %d, A: %d" % (pval.red(), pval.green(), pval.blue(), pval.alpha())
                
                msg = "%s<X %d%s, Y %d%s> : %s" % \
                    (crstxt, x, swx, y, swy, val)

            else:
                val = None

            self.statusBar().showMessage(msg)
            
        else:
            return # shouldn't really get here
        
    def _display_Z_coordinate(self):
        ret = f"Z: {self._current_frame_index_}"
        if self.frameAxis is not None:
            index = self.frameIndexBinding[self._current_frame_index_]
            if all(isinstance(ndx, tuple) for ndx in index):
                if self._axes_calibration_:
                    z = ", ".join([f"{self._data_.axistags[ndx[0]].key}: {ndx[1]} ({quantity2str(self._axes_calibration_[self._data_.axistags[ndx[0]].key].calibratedDistance(ndx[1]))})" for ndx in reversed(index)])
                else:
                    z = ", ".join([f"{self._data_.axistags[ndx[0]].key}: {ndx[1]}" for ndx in reversed(index)])
                    
            else:
                if self._axes_calibration_:
                    z = f"{self._data_.axistags[index[0]].key}: {index[1]} ({quantity2str(self._axes_calibration_[self._data_.axistags[index[0]].key].calibratedDistance(index[1]))})"
                else:
                    z = f"{self._data_.axistags[index[0]].key}: {index[1]}"
                
            ret += f": {z}"
            
        return ret
        
    ####
    # public methods
    ####
    
    @safeWrapper
    def slot_removeCursorByName(self, crsId):
        self.removeCursor(crsId)
        
    @safeWrapper
    def slot_removeRoiByName(self, crsId):
        self.removeGraphicsObject(crsId)
        
    @safeWrapper
    def removeGraphicsObject(self, item:typing.Union[str, pgui.GraphicsObject]):
        """Removes a GraphicsObject from the viewer's scene.
        A GraphicsObject is a Qt graphics object used as frontend for a PlanarGraphics.
        WARNING: This only removes the object from the viewer scene; the viewer and
        the PlanarGraphics backend still retain a reference to the GraphicsObject!
        Most likely you want to avoid this.
        
        For the most general case use removePlanarGraphics method
        
        Parameters:
        ===========
        
        item: str (name or ID of the GraphicsObject) or a GraphicsObject. If the 
            latter, the object to be removed is looked up by its name or ID.
        
        """
        objects = self.graphicsObjects
        if len(objects) ==0:
            return
        
        if isinstance(item, str) and len(item.strip()):
            objs = [o for o in objects if o.name == item]
            for o in objs:
                self.viewerWidget.slot_removeGraphicObject(o)
                
        elif isinstance(item, pgui.GraphicsObject) and item in objects:
            self.viewerWidget.slot_removeGraphicObject(item)
            
    @safeWrapper
    def removePlanarGraphics(self, item:typing.Union[str, pgui.PlanarGraphics]):
        """Removes a planar graphics from the viewer's scene.
        Parameters:
        ===========
        item: a str (PlanarGraphics 'name' attribute) or a PlanarGraphics. If the
            latter, the object is looked up by its 'name' attribute.
        """
        objects = self.graphicsObjects
        if len(objects) == 0:
            return
        
        if isinstance(item, str) and len(item.strip()):
            name = item
        elif isinstance(item, pgui.PlanarGraphics):
            name = item.name
        else:
            raise TypeError(f"Expecting a str or pgui.PlanarGraphics; instead, got a {type(item).__name__}")
            
        if name in [o.name for o in objects]:
            self.viewerWidget._removePlanarGraphics(name)
                
    @safeWrapper
    def removeCursor(self, item:typing.Union[str, pgui.Cursor]):
        objects = self.graphicsCursors
        if len(objects) == 0:
            return
        
        if isinstance(item, str) and len(item.strip()):
            name = item
        elif isinstance(item, pgui.Cursor):
            if item not in objects:
                return
            name = item.name
        else:
            raise TypeError(f"Expecting a str or a pgui.Cursor; instead, got a {type(item).__name__}")
            
        if name in [o.name for o in objects]:
            self.viewerWidget._removePlanarGraphics(name, True)
            # self.viewerWidget.slot_removeCursorByName(name)
            
    def removeRoi(self, item:typing.Union[str, pgui.PlanarGraphics]):
        objects = self.rois
        if len(objects) == 0:
            return
        
        if isinstance(item, str) and len(item.strip()):
            name = item
            
        elif isinstance(item, pgui.PlanarGraphics) and not isinstance(item, pgui.Cursor):
            if item not in objects:
                return
            name = item.name
        else:
            raise TypeError(f"Expecting a str or a pgui.Cursor; instead, got a {type(item).__name__}")
            
        if name in [o.name for o in objects]:
            self.viewerWidget._removePlanarGraphics(name, True)
            # self.viewerWidget.slot_removeCursorByName(name)
            
    def loadViewerSettings(self):
        # FIXME TODO 2021-08-22 22:08:19
        pass
        # transfer this to confuse settings
        #colorMapName = self.qsettings.value("ImageViewer/ColorMap", None)
        #colorMapName = self.qsettings.value("/".join([self.__class__.__name__, "ColorMap"]), None)
        
        ##print("ImageViewer %s loadViewerSettings colorMapName" % self, colorMapName)
        
        #if isinstance(colorMapName, str):
            #self._colorMap = colormaps.get(colorMapName, None)
                
        #elif isinstance(colorMapName, colormaps.colors.Colormap):
            #self._colorMap = colorMapName
            
        #else:
            #self._colorMap = None
        
        #color = self.qsettings.value("/".join([self.__class__.__name__, "CursorColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.cursorsColor = color
            
        #color = self.qsettings.value("/".join([self.__class__.__name__, "CursorLabelTextColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.cursorLabelTextColor = color
            
        #color = self.qsettings.value("/".join([self.__class__.__name__, "LinkedCursorColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.linkedCursorsColor = color
            
        #color = self.qsettings.value("/".join([self.__class__.__name__, "LinkedCursorLabelTextColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.linkedCursorLabelTextColor = color
            
        #color = self.qsettings.value("/".join([self.__class__.__name__, "CursorLabelBackgroundColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.linkedCursorLabelTextColor = color
            
        #color = self.qsettings.value("/".join([self.__class__.__name__, "OpaqueCursorLabel"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.opaqueCursorLabel = color
            
        #color = self.qsettings.value("/".join([self.__class__.__name__, "RoiColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.roisColor = color
        
        #color = self.qsettings.value("/".join([self.__class__.__name__, "ROILabelTextColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.roiLabelTextColor = color
            
        #color = self.qsettings.value("/".join([self.__class__.__name__, "LinkedROIColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.linkedROIsColor = color
        
        #color = self.qsettings.value("/".join([self.__class__.__name__, "LinkedROILabelTextColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.linkedROILabelTextColor = color
            
        #color = self.qsettings.value("/".join([self.__class__.__name__, "ROILabelBackgroundColor"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.roiLabelBackgroundColor = color
            
        #color = self.qsettings.value("/".join([self.__class__.__name__, "OpaqueROILabel"]), None)
        #if isinstance(color, QtGui.QColor) and color.isValid():
            #self.opaqueROILabel = color
            
    def saveViewerSettings(self):
        pass
        #if isinstance(self._colorMap, colormaps.colors.Colormap):
            #self.qsettings.setValue("/".join([self.__class__.__name__, "ColorMap"]), self._colorMap.name)
            
        #else:
            #self.qsettings.setValue("/".join([self.__class__.__name__, "ColorMap"]), None)
        
        #self.qsettings.setValue("/".join([self.__class__.__name__, "CursorColor"]), self.cursorsColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "CursorLabelTextColor"]), self.cursorLabelTextColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "LinkedCursorColor"]), self.linkedCursorsColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "LinkedCursorLabelTextColor"]), self.linkedCursorLabelTextColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "CursorLabelBackgroundColor"]), self.cursorLabelBackgroundColor)
        ##self.qsettings.setValue("/".join([self.__class__.__name__, "LinkedCursorLabelBackgroundColor"]), self.LinkedCursorLabelBackgroundColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "OpaqueCursorLabel"]), self.opaqueCursorLabel)
        
        #self.qsettings.setValue("/".join([self.__class__.__name__, "RoiColor"]), self.roisColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "ROILabelTextColor"]), self.roiLabelTextColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "LinkedROIColor"]), self.linkedROIsColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "LinkedROILabelTextColor"]), self.linkedROILabelTextColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "ROILabelBackgroundColor"]), self.roiLabelBackgroundColor)
        #self.qsettings.setValue("/".join([self.__class__.__name__, "OpaqueROILabel"]), self.opaqueROILabel)
        
        
    def setImage(self, image, doc_title=None, normalize=True, colormap=None, gamma=None, frameAxis=None, displayChannel=None):
        self.setData(image, doc_title=doc_title, normalize=normalize, colormap=colormap, gamma=gamma,
                     frameAxis=frameAxis, displayChannel=displayChannel)
        
    def displayChannel(self, channel_index):
        if isinstance(self._data_, vigra.VigraArray):
            if channel_index < 0 or channel_index >= self._data_.channels:
                raise ValueError("channel_index must be in the semi-open interval [0, %d); got %s instead" % (self._data_.channels, channel_index))
            
        # see NOTE: 2018-09-25 23:06:55
        sigBlock = QtCore.QSignalBlocker(self.showAllChannelsAction)
        
        self.showAllChannelsAction.setChecked(False)
        
        self.displayFrame(channel_index)
        self._displayedChannel_ = channel_index
        
    def displayAllChannels(self):
        # see NOTE: 2018-09-25 23:06:55
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in self.displayIndividualChannelActions]
        for action in self.displayIndividualChannelActions:
            action.setChecked(False)
            
        self.displayFrame("all")
        self._displayedChannel_ = "all"
        
    def var_observer(self, change):
        self.displayFrame()
        
        
    def view(self, image, doc_title=None, normalize=True, colormap=None, gamma=None, frameAxis=None, displayChannel=None, asAlphaChannel=False, frameIndex=None, get_focus=True):
        # NOTE: 2020-09-24 14:19:57
        # this calls ancestor's instance method ScipyenFrameViewer.setData(...)
        # which then delegates back to _set_data() here.
        self.setData(image, doc_title=doc_title, normalize=normalize, colormap=colormap, gamma=gamma,
                     frameAxis=frameAxis, frameIndex=None, displayChannel=displayChannel, 
                     asAlphaChannel=asAlphaChannel, get_focus=get_focus)
        
    def _set_data_(self, data, normalize=True, colormap = None, gamma = None, tempColorMap = None, frameAxis=None, frameIndex=None, arrayAxes:(type(None), vigra.AxisTags) = None, displayChannel = None, doc_title:(str, type(None)) = None, asAlphaChannel:bool=False, *args, **kwargs):
        '''
        SYNTAX: self.view(image, title = None, normalize = True, colormap = None, gamma = None, separateChannels = False, frameAxis = None)
    
        Parameters:
        ============
            image: a vigra.VigraArray object with up to 4 dimensions (for now) or a QImage or QPixmap
      
            title: a str, default None
            
            normalize: bool, default True
            
            colormap: default None; when given, overrides the colormap configuration
                set up in preferences ONLY for this image
                
            
            gamma: float scalar or None (default)
            
            frameAxis: int, str, vigra.AxisInfo or None (default)
            
            displaychannel: int, "all", or None (default)
        '''
        
        self._imageNormalize     = normalize
        self._imageGamma         = gamma
        
        if isinstance(colormap, colormaps.colors.Colormap):
            self._colorMap = colormap
            
        elif isinstance(colormap, str):
            cmap = colormaps.get(colormap, None)
            if isinstance(cmap, colormaps.colors.Colormap):
                self._colorMap = cmap

        if self._colorBar is not None:
            self.viewerWidget.scene.removeItem(self._colorBar)
            
        if isinstance(tempColorMap, colormaps.colors.Colormap):
            self._tempColorMap = tempColorMap
            
        elif isinstance(tempColorMap, str):
            cmap = colormaps.get(tempColorMap, None)
            if isinstance(cmap, colormaps.colors.Colormap):
                self._tempColorMap = cmap
                
        else:
            self._tempColorMap = None
            
        self._colorBar = None
        
        self._axes_calibration_ = None
                
        if displayChannel is None:
            self._displayedChannel_      = "all"
            
        else:
            if isinstance(displayChannel, str):
                if displayChannel.lower().strip()!="all":
                    raise ValueError("When a str, displayChannel must be 'all'; got %s instead" % displayChannel)
                
            elif isinstance(displayChannel, int):
                if displayChannel < 0:
                    raise ValueError("When an int, display channel must be >= 0")
                
            self._displayedChannel_ = displayChannel

        if isinstance(data, vigra.VigraArray):
            if isinstance(frameAxis, (int, str, vigra.AxisInfo)):
                self.userFrameAxisInfo  = frameAxis
                
            if self._parseVigraArrayData_(data):
                # NOTE: 2022-01-17 16:32:15
                # self._parseVigraArrayData_ sets up _number_of_frames_ and 
                # _data_frames_
                self._data_  = data
                self.frameIndex = frameIndex or range(self._data_frames_) # set by _parseVigraArrayData_
                self._number_of_frames_ = len(self.frameIndex)
                self._axes_calibration_ = AxesCalibration(data)
                self._setup_channels_display_actions_()
                self.displayFrame(asAlphaChannel=asAlphaChannel)
                
                #totalFrames = self._number_of_frames_ if isinstance(self._number_of_frames_, int) else np.prod(self._number_of_frames_)
        
                self.framesQSlider.setMaximum(self._number_of_frames_ - 1)
                self.framesQSlider.setToolTip("Select frame.")
                
                self.framesQSpinBox.setMaximum(self._number_of_frames_ - 1)
                self.framesQSpinBox.setToolTip("Select frame.")
                self.nFramesLabel.setText("of %d" % self._number_of_frames_)
                
  
        elif isinstance(data, (QtGui.QImage, QtGui.QPixmap)):
            self._number_of_frames_ = 1
            self.frameIndex = range(self._number_of_frames_)
            self._data_  = data
            self.frameAxis = None
            self.displayFrame()
            
        elif isinstance(data, np.ndarray):
            if arrayAxes is None:
                if data.ndim  == 1:
                    arrayAxes = vigra.VigraArray.defaultAxistags("x")
                    
                elif data.ndim == 2:
                    if  datatypes.is_vector(data):
                        arrayAxes = vigra.VigraArray.defaultAxistags("y")
                    else:
                        arrayAxes = vigra.VigraArray.defaultAxistags("xy")
                    
                else:
                    arrayAxes = vigra.VigraArray.defaultAxistags(data.ndim, noChannels=True)
                    
            # NOTE: 2021-10-25 16:29:38
            # For display purposes only, we construct a VigraArray on the numpy
            # ndarray passed as 'image'
            
            array_data = vigra.VigraArray(data, axistags=arrayAxes)
            if self._parseVigraArrayData_(array_data):
                self._data_  = array_data
                self.frameIndex = frameIndex or range(self._number_of_frames_) # set by _parseVigraArrayData_
                self._axes_calibration_ = AxesCalibration(array_data)
                self._setup_channels_display_actions_()
                self.displayFrame(asAlphaChannel=asAlphaChannel)
            
        else:
            raise TypeError("First argument must be a VigraArray, a numpy.ndarray, a QtGui.QImage or a QtGui.QPixmap")
        
    def clear(self):
        """Clears all image data cursors and rois from this window
        """
        self._number_of_frames_ = 0
        self._current_frame_index_ = 0
        self.framesQSlider.setMaximum(0)
        self.framesQSpinBox.setMaximum(0)
        self._data_ = None
        self._separateChannels           = False
        self.tStride                    = 0
        self.zStride                    = 0
        self.frameAxis              = None
        self.userFrameAxisInfo          = None
        self._display_time_vertical_        = True
        self.widthAxis              = None # this is "visual" width which may not be on a spatial axis "x"
        self.heightAxis             = None # this is "visual" height which may not be on a spatial axis "y"
        self._currentZoom_               = 0
        self._currentFrameData_          = None
        self._xScaleBar_                 = None
        self._xScaleBarTextItem_         = None
        self._yScaleBar_                 = None
        self._yScaleBarTextItem_         = None
        
        # see NOTE: 2018-09-25 23:06:55
        sigBlock = QtCore.QSignalBlocker(self.displayScaleBarAction)
        #self.displayScaleBarAction.toggled[bool].disconnect(self.slot_displayScaleBar)
        self.displayScaleBarAction.setChecked(False)
        #self.displayScaleBarAction.toggled[bool].connect(self.slot_displayScaleBar)
        
        if self._colorBar is not None:
            self.viewerWidget.scene.removeItem(self._colorBar)
            
            self._colorBar = None
        
        self.viewerWidget.clear()
        
    def showScaleBars(self, origin=None, length=None, calibrated_length=None, pen=None, units=None):
        """Shows a scale bar for both axes in the display
        origin: tuple or list with (x,y) coordinates of scale bars origin
        length: tuple or list with the length of the respective scale bars (x and y)
        
        NOTE: both values are in pixels (i.e. ints)
        
        """
        
        if self._data_ is None:
            return
        
        if isinstance(self._data_, vigra.VigraArray):
            w = self._data_.shape[0]
            h = self._data_.shape[1]

        elif isinstance(self._data_, (QtGui.QImage, QtGui.QPixmap)):
            w = self._data_.width()
            h = self._data_.height()
            
        else:
            return # shouldn't really get here
    
        if origin is None:
            origin = self._scaleBarOrigin_
            
        if length is None:
            length = self._scaleBarLength_
            
        if calibrated_length is not None:
            cal_x = calibrated_length[0]
            cal_y = calibrated_length[1]
            
        else:
            cal_x = None
            cal_y = None
            
        if pen is None:
            pen = self._scaleBarPen_
            
        elif not isinstance(pen, QtGui.QPen):
            raise TypeError("Expecting a QtGui.QPen or None; got %s instead" % type(pen).__name__)
        
        if isinstance(pen, QtGui.QPen):
            self._scaleBarPen_ = pen
            
        if isinstance(units, tuple) and len(units) == 2 \
            and all([isinstance(u, (pq.Quantity, pq.UnitQuantity)) for u in units]):
                
            units_x = str(units[0].dimensionality)
            units_y = str(units[1].dimensionality)
                
        else:
            units_x = None
            units_y = None
        
        if self._display_horizontal_scalebar_:
            if self._xScaleBar_ is None:
                self._xScaleBar_ = QtWidgets.QGraphicsLineItem()
                #self._xScaleBar_.setAcceptedMouseButtons(QtCore.Qt.NoButton)
                self._xScaleBar_.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
                self._xScaleBar_.setPen(self._scaleBarPen_)

                if self._xScaleBarTextItem_ is None:
                    self._xScaleBarTextItem_ = QtWidgets.QGraphicsTextItem(self._xScaleBar_)
                    self._xScaleBarTextItem_.setDefaultTextColor(self._scaleBarColor_)
                    self._xScaleBarTextItem_.setFont(QtGui.QFont("sans-serif"))
                    self._xScaleBarTextItem_.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
                    self._xScaleBarTextItem_.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
                
                self.scene.addItem(self._xScaleBar_)
                
            self._xScaleBar_.setLine(origin[0], origin[1], 
                                    origin[0] + length[0], 
                                    origin[1])
        
            if cal_x is not None:
                self._xScaleBarTextItem_.setPlainText("%s" % cal_x)
                
            else:
                if units_x is not None:
                    self._xScaleBarTextItem_.setPlainText("%d %s" % (length[0], units_x))
                    
                else:
                    self._xScaleBarTextItem_.setPlainText("%d" % length[0])
                
            self._xScaleBarTextItem_.setPos(length[0]-self._xScaleBarTextItem_.textWidth(),
                                           3 * self._xScaleBar_.pen().width())
            
            self._xScaleBar_.setVisible(True)

        if self._display_vertical_scalebar_:
            if self._yScaleBar_ is None:
                self._yScaleBar_ = QtWidgets.QGraphicsLineItem()
                self._yScaleBar_.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
                #self._yScaleBar_.setAcceptedMouseButtons(QtCore.Qt.NoButton)
                self._yScaleBar_.setPen(self._scaleBarPen_)

                if self._yScaleBarTextItem_ is None:
                    self._yScaleBarTextItem_ = QtWidgets.QGraphicsTextItem(self._yScaleBar_)
                    self._yScaleBarTextItem_.setDefaultTextColor(self._scaleBarColor_)
                    self._yScaleBarTextItem_.setFont(QtGui.QFont("sans-serif"))
                    self._yScaleBarTextItem_.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
                    self._yScaleBarTextItem_.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
                
                self.scene.addItem(self._yScaleBar_)
                
            self._yScaleBar_.setLine(origin[0], origin[1],
                                    origin[0],
                                    origin[1] + length[1])
        
            if cal_y is not None:
                self._yScaleBarTextItem_.setPlainText("%s" % cal_y)
                
            else:
                if units_y is not None:
                    self._yScaleBarTextItem_.setPlainText("%d %s" % (length[1], units_y))
                    
                else:
                    self._yScaleBarTextItem_.setPlainText("%d" % length[1])
                
            self._yScaleBarTextItem_.setPos(3 * self._yScaleBar_.pen().width(), 0)
            
            self._yScaleBarTextItem_.setRotation(-90)
                
            self._yScaleBar_.setVisible(True)
            
        self._scaleBarLength_ = length
        self._scaleBarOrigin_ = origin
        
    def addCursors(self, **kwargs):
        """Programmatically creates a set of cursors from cursor parameters.
        
        Creates gui.planargraphics.Cursor objects and their 
        gui.planargraphics.GraphicsObject frontends.
        
        The method provides a quick shorthand for creating new cursors in the 
        ImageViewer's scene.
        
        Var-keyword parameters:
        =======================
        Mapping of cursor name (str) to a dict with fields:
            "type": str (valid PlanarGraphicsType name)
            "pos": tuple (x,y) of coordinates
            
        Returns:
        ========
        A (possibly empty) tuple of gui.planargraphics.Cursor objects.
        
        Example:
        
        c = addCursors(**dict(map(lambda k: ("Cursor%i"%k, {"type":"vertical", "pos": (50 + 50 * k, 0)}), range(2))))
        
        """
        objects = list()
        
        if self.viewerWidget.scene.rootImage is not None:
            #k = 0
            
            for name, type_pos in kwargs.items():
                ctype = type_pos.get("type", None)
                cpos = type_pos.get("pos", None)
                
                if isinstance(ctype, str):
                    cursor_type_names = filter(lambda x: x.endswith("_cursor"), pgui.PlanarGraphicsType.names())
                    sub_match = list(filter(lambda x: ctype in x, cursor_type_names))
                    if ctype in cursor_type_names:
                        ctype = pgui.PlanarGraphicsType["ctype"]
                        
                    elif len(sub_match):
                        ctype = pgui.PlanarGraphicsType[sub_match[0]]
                        
                    else:
                        continue # no known cursor type
                    
                elif isinstance(ctype, pgui.PlanarGraphicsType):
                    if not ctype.is_primitive() or not ctype.name.endswith("_cursor"):
                        continue
                    
                else:
                    continue
                        
                if not isinstance(cpos, (tuple, list)) or len(cpos) != 2 or not all((isinstance(v, numbers.Number) for v in cpos)):
                    continue
                
                if ctype == pgui.PlanarGraphicsType.vertical_cursor:
                    factory = pgui.VerticalCursor
                    
                elif ctype == pgui.PlanarGraphicsType.horizontal_cursor:
                    factory = pgui.HorizontalCursor
                    
                elif ctype == pgui.PlanarGraphicsType.crosshair_cursor:
                    factory = pgui.CrosshairCursor
                    
                elif ctype == pgui.PlanarGraphicsType.point_cursor:
                    factory = pgui.PointCursor
                    
                else:
                    continue
                
                obj = factory(cpos[0], cpos[1],
                            self.viewerWidget.scene.sceneRect().width(),
                            self.viewerWidget.scene.sceneRect().height(),
                            self.viewerWidget.__cursorWindow__, 
                            self.viewerWidget.__cursorWindow__,
                            self.viewerWidget.__cursorRadius__,
                            name=name,
                            frameindex=[],
                            currentFrame = self.currentFrame,
                            )
                
                obj=self.addPlanarGraphics(obj, showLabel=True, labelShowsPosition=True)
                # NOTE: 2021-09-16 12:11:54
                # these two are needed to that we can move the thing with the mouse
                # FIXME this should not happen
                obj.x = cpos[0]
                obj.y = cpos[1]
                
                objects.append(obj)
            
        return objects
        
    def addPlanarGraphics(self, item:pgui.PlanarGraphics, movable:bool = True, editable:bool = True, showLabel:bool = True, labelShowsPosition:bool = True, autoSelect:bool = True, transparentLabel:bool = False, returnGraphics:bool=False):
        """Add a roi or a cursor to the underlying scene.
        
        The function generates a gui.planargraphics.GraphicsObject as a frontend
        to a gui.plarangraphics.PlanarGraphics object.
        
        The ImageViewer does not own the PlanarGraphics object, but a reference
        to the PlanarGraphics object is accessible to the GraphicsObject 
        instance as the 'backend'. attribute.
        
        In turn, a PlanarGraphics object can hold references to potentially more
        than one GraphicsObject 'frontends' (e.g. one for a distinct instance
        of ImageViewer) such that changes in the PlanarGraphics object shape
        descriptors are visible in all frontends.
        
        
        Parameters:
        ===========
        
        item: gui.PlanarGraphics object
        
        Keyword parameters:
        ==================
        returnGraphics:bool, optional, default is False
            When True, returns the newly-created gui.planargraphics.GraphicsObject
            ( a PyQt5.QtWidgets.QGraphicsItem); otherwise, returns the 
            PlanarGraphics objects passed as 'item'
        
        The following are optional (default values shownn in parantheses) and
        are passed directly to the GraphicsObject constructor via the method
        GraphicsImageViewerWidget.newGraphicsObject(...):
        
        movable:bool (True)
        editable:bool (True)
        showLabel:bool (True)
        labelShowsPosition:bool (True); for gui.planargraphics.Cursor objects
        autoSelect:bool (True)
        transparentLabel:bool (False)
        
        
        
        NOTE: To manually add a roi or cursor in the window, use the window menu
        
        Returns:
        ========
        The PlanarGraphics object passed in the 'item' argument.
        
        """
        obj = self.viewerWidget.newGraphicsObject(item, 
                                                  movable             = movable,
                                                  editable            = editable, 
                                                  showLabel           = showLabel,
                                                  labelShowsPosition  = labelShowsPosition,
                                                  autoSelect          = autoSelect)
        
        if isinstance(obj.backend, pgui.Cursor):
            if isinstance(self.cursorsColor, QtGui.QColor) and self.cursorsColor.isValid():
                obj.color = self.cursorsColor
                
        else:
            if isinstance(self.roisColor, QtGui.QColor) and self.roisColor.isValid():
                obj.color = self.roisColor
                
        obj.setTransparentLabel(transparentLabel)

        return obj if returnGraphics else obj.backend
        
    @Slot()
    @safeWrapper
    def slot_chooseCursorsColor(self):
        if isinstance(self.cursorsColor, QtGui.QColor):
            initial = self.cursorsColor
            
        else:
            initial = QtCore.Qt.white

        color = QtWidgets.QColorDialog.getColor(initial=initial, 
                                                title="Choose cursors color",
                                                options=QtWidgets.QColorDialog.ShowAlphaChannel)
            
        self.setGraphicsObjectColor(color, "cursor")

    @Slot()
    @safeWrapper
    def slot_chooseLinkedCursorsColor(self):
        if isinstance(self.cursorsColor, QtGui.QColor):
            initial = self.cursorsColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color for linked Cursors")
        
        self.setGraphicsObjectColor(color, "linkedcursor")
        
    @Slot()
    @safeWrapper
    def slot_chooseCursorLabelTextColor(self):
        if isinstance(self.cursorLabelTextColor, QtGui.QColor):
            initial = self.cursorLabelTextColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color cursor labels text")
        self.setGraphicsObjectColor(color, "cursorLabelText")
        
    @Slot()
    @safeWrapper
    def slot_chooseLinkedCursorLabelTextColor(self):
        if isinstance(self.linkedCursorLabelTextColor, QtGui.QColor):
            initial = self.linkedCursorLabelTextColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color cursor labels text")
        self.setGraphicsObjectColor(color, "linkedcursorlabeltext")
        
    @Slot()
    @safeWrapper
    def slot_chooseCursorLabelBGColor(self):
        # TODO/FIXME: 2021-05-12 09:33:30
        # not used yet
        if isinstance(self.cursorLabelBackgroundColor, QtGui.QColor):
            initial = self.cursorLabelBackgroundColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color cursor labels background")
        
        self.setGraphicsObjectColor(color, "cursorLabelBackground")
            
    @Slot()
    @safeWrapper
    def slot_chooseLinkedCursorBGColor(self):
        # TODO/FIXME: 2021-05-12 09:33:30
        # not used yet
        if isinstance(self.cursorLabelBackgroundColor, QtGui.QColor):
            initial = self.cursorLabelBackgroundColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color cursor labels background")
        
        self.setGraphicsObjectColor(color, "cursorLabelBackground")
            
    @Slot()
    @safeWrapper
    def slot_chooseRoisColor(self):
        if isinstance(self.roisColor, QtGui.QColor):
            initial = self.roisColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color for ROIs")
        
        self.setGraphicsObjectColor(color, "rois")
            
        
    @Slot()
    @safeWrapper
    def slot_chooseLinkedRoisColor(self):
        if isinstance(self.linkedROIsColor, QtGui.QColor):
            initial = self.linkedROIsColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color for linked ROIs")
        
        self.setGraphicsObjectColor(color, "linkedroi")
        
    @Slot()
    @safeWrapper
    def slot_chooseRoisLabelTextColor(self):
        if isinstance(self.roiLabelTextColor, QtGui.QColor):
            initial = self.roiLabelTextColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color for linked ROIs")
        
        self.setGraphicsObjectColor(color, "roilabeltext")
        
    @Slot()
    @safeWrapper
    def slot_chooseLinkedRoisLabelTextColor(self):
        if isinstance(self.linkedROILabelTextColor, QtGui.QColor):
            initial = self.linkedROILabelTextColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color for linked ROIs")
        
        self.setGraphicsObjectColor(color, "linkedroilabeltext")
        
    @Slot()
    @safeWrapper
    def slot_chooseROILabelBGColor(self):
        # TODO/FIXME: 2021-05-12 09:33:30
        # not used yet
        if isinstance(self.roiLabelBackgroundColor, QtGui.QColor):
            initial = self.roiLabelBackgroundColor
            
        else:
            initial = QtCore.Qt.white

        color = self._showColorChooser(initial, "Choose color cursor labels background")
        
        self.setGraphicsObjectColor(color, "roilabelbackground")
        
    @Slot(bool)
    @safeWrapper
    def slot_setOpaqueCursorLabels(self, value):
        self.setOpaqueGraphicsLabel(cursors=True, opaque=value)
            
    @Slot(bool)
    @safeWrapper
    def slot_setOpaqueROILabels(self, value):
        self.setOpaqueGraphicsLabel(cursors=False, opaque=value)
            
    def _showColorChooser(self, initial:QtGui.QColor, title:str="Choose color"):
        return QtWidgets.QColorDialog.getColor(initial=initial, 
                                                title=title,
                                                options=QtWidgets.QColorDialog.ShowAlphaChannel,
                                                parent=self)
        
    def setGraphicsObjectColor(self, color:QtGui.QColor, what:str):
        cursor = what.lower() in ("cursor", "linkedcursor",
                                  "cursorlabeltext", "linkedcursorlabeltext",
                                  "cursorlabelbackground")
        
        if cursor:
            filtfn = partial(filter, lambda x: isinstance(x.backend, pgui.Cursor))
        else:
            filtfn = partial(itertools.filterfalse, lambda x: isinstance(x.backend, pgui.Cursor))
            
        if isinstance(color, QtGui.QColor) and color.isValid():
            if what.lower() == "cursor":
                self.cursorsColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.penColor = self.cursorsColor
                    
            elif what.lower() == "linkedcursor":
                self.linkedCursorsColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.linkedPenColor = self.linkedCursorsColor
                    
            elif what.lower() == "cursorlabeltext":
                self.cursorLabelTextColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.textColor = self.cursorLabelTextColor
                    
            elif what.lower() == "linkedcursorlabeltext":
                self.linkedCursorLabelTextColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.linkedTextColor = self.linkedCursorLabelTextColor
                    
            elif what.lower() == "cursorlabelbackground":
                self.cursorLabelBackgroundColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.textBackgroundColor = self.cursorLabelBackgroundColor
                    
            elif what.lower() == "roi":
                self.roisColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.penColor = self.roisColor
                    
            elif what.lower() == "linkedroi":
                self.linkedROIsColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.linkedPenColor = self.linkedROIsColor
                    
            elif what.lower() == "roilabeltext":
                self.roiLabelTextColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.textColor = self.roiLabelTextColor
                    
            elif what.lower() == "linkedroilabeltext":
                self.linkedROILabelTextColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.linkedTextColor = self.linkedROILabelTextColor
                    
            elif what.lower() == "roilabelbackground":
                self.roiLabelBackgroundColor = color
                for obj in filtfn(self.viewerWidget.graphicsObjects):
                    obj.textBackgroundColor = self.roiLabelBackgroundColor
        
    def setOpaqueGraphicsLabel(self, cursors:bool=False, opaque:bool=True):
        if cursors:
            self.opaqueCursorLabel = opaque
            objs = [o for o in filter(lambda x: isinstance(x.backend, pgui.Cursor), 
                                        self.viewerWidget.graphicsObjects)]
        else:
            self.opaqueROILabel = opaque
            objs = [o for o in itertools.filterfalse(lambda x: isinstance(x.backend, pgui.Cursor), 
                                                    self.viewerWidget.graphicsObjects)]
        for obj in objs:
            obj.opaqueLabel = opaque
            
