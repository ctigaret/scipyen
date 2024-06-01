# -*- coding: utf-8 -*-
import typing, os
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot
from qtpy.uic import loadUiType as __loadUiType__
# from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
# from PyQt5.QtCore import Signal, Slot
# from PyQt5.uic import loadUiType as __loadUiType__

from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__, "spinboxslider.ui")

Ui_SpinBoxSlider, QWidget = __loadUiType__(__ui_path__)
# Ui_SpinBoxSlider, QWidget = __loadUiType__(os.path.join(__module_path__, "spinboxslider.ui"))

class SpinBoxSlider(QWidget, Ui_SpinBoxSlider):
    """Compound widget with a QSpinBox and QSlider.
    The widge is backed by a Python `range` object, meaning that its attributes
    are as follows:
    • minimum       ↦ min(self.range) = self.range.start
    • maximum       ↦ max(self.range) ≠ self.range.stop
    • singleStep    ↦ singleStep attribute of the QSpinBox component, independent 
                        of self.range.step
    • pageStep      ↦ pageStep attribute of the QSlider component, independent
                        of self.range.step
    
    NOTE:
    • self.range.step is 1 (one) ALWAYS
    
    A new range can be set up for this widget in two ways:
    
    ∘ by calling self.setRange(min, max) which behaves as the Qt counterpart i.e.,
        passing the minimum and maximum values the widget can take (NOT the start
        and stop values of a Python range !)
        
    ∘ by assigning a new Python range object to the self.range property
    
    Only a minimal set of QSPinBox and QSlider are exposed.
    For more atomic changes access self.framesQSpinBox and self.framesQSlider 
    directly
    """
    valueChanged = Signal(int, name="valueChanged")
    
    def __init__(self, parent=None, **kwargs):
        self._singleStep_ = kwargs.pop("singleStep", 1)
        self._pageStep_ = kwargs.pop("pageStep", 10)
        minimum = kwargs.pop("minimum", 0)
        maximum = kwargs.pop("maximum", 0)
        self._range_ = range(minimum, maximum, 1)
        self._tracking_ = kwargs.pop("tracking", True)
        self._prefix_ = kwargs.pop("prefix", "")
        self._label_ = kwargs.pop("label", "Frame:")
        self._value_ = kwargs.pop("value",0)
        self._toolTip_ = kwargs.pop("toolTip", 
                                    "Set current %s" if self._label_[:-1] is self._label_.endswith(":") else self._label_)

        self._whatsThis_ = kwargs.pop("whatsThis", self._toolTip_)
        self._statusTip_ = kwargs.pop("statusTip", self._toolTip_)
        

        super().__init__(parent=parent)
        self._configureUI_()
        
    def _configureUI_(self):
        self.setupUi(self)
        self.descriptionLabel.setText(self._label_)
        if len(self._range_):
            mn = min(self._range_)
            mx = max(self._range_)
        else:
            mn = mx = 0
        for w in (self.framesQSlider, self.framesQSpinBox):
            w.setMinimum(mn)
            w.setMaximum(mx)
            w.setSingleStep(self._range_.step)
            
        self.framesQSlider.setPageStep(self._pageStep_)
            
        self.totalFramesCountLabel.setText(f"of {len(self._range_)}")
        
        self.framesQSlider.setTracking(self._tracking_)
        self.framesQSpinBox.setKeyboardTracking(self._tracking_)
        self.framesQSlider.valueChanged.connect(self.slot_setValue)
        self.framesQSpinBox.valueChanged.connect(self.slot_setValue)
        
    @property
    def label(self):
        """A description of what the widget shows.
        This is the text in the self.descriptionLabel QLabel on the far left.
        Ideally this is one word, followed by a colon (e.g. "Frame:", "Segment:")
        """
        return self._label_
    
    @label.setter
    def label(self, value:str):
        if isinstance(value, str):
            if not value.endswith(":"):
                value += ":"
                
            self._label_ = value
                
            self.descriptionLabel.setText(self._label_)
        
    @property
    def minimum(self):
        return min(self._range_) if len(self._range_) else 0
    
    @minimum.setter
    def minimum(self, value:int):
        val = int(value)
        # step = self._range_.step
        mx = max(self._range_) if len(self._range_) else 0
        self.range = range(val, mx, 1)
        # avoid ∞ recursion
#         signalBlockers = [QtCore.QSignalBlocker(widget) for widget in (self, self.framesQSpinBox, self.framesQSlider)]
#         
#         self._minimum_ = val
#         self.framesQSpinBox.setMinimum(val)
#         self.framesQSlider.setMinimum(val)
        
    @property
    def maximum(self):
        """The maximum value in the spinbox and slider.
        Also sets up the value in the "of..." label.
        """
        return max(self._range_) if len(self._range_) else 0
    
    @maximum.setter
    def maximum(self, value:int):
        # step = self._range_.step
        val = int(value)
        mn = min(self._range_) if len(self._range_) else 0
        self.range = range(mn, val, 1)
        # self._maximum_ = val
        # avoid ∞ recursion
        # signalBlockers = [QtCore.QSignalBlocker(widget) for widget in (self, self.framesQSpinBox, self.framesQSlider)]
        # self.framesQSpinBox.setMaximum(self._maximum_)
        # self.framesQSlider.setMaximum(self._maximum_)
        # self.totalFramesCountLabel.setText(f" of {len(range(self._minimum_, self._maximum_))}")
        
    @property
    def singleStep(self):
        return self._singleStep_
    
    @singleStep.setter
    def singleStep(self, value:int):
        self._singleStep_ = val
        self.framesQSpinBox.setSingleStep(self._singleStep_)
        self.framesQSlider.setSingleStep(self._singleStep_)
        
    @property
    def pageStep(self):
        return self._pageStep_
    
    @pageStep.setter
    def pageStep(self, value:int):
        val = int(value)
        self._pageStep_ = val
        self.framesQSlider.setPageStep(val)
        
    @property
    def range(self):
        """The Python range for this widget
        """
        return self._range_
    
    @range.setter
    def range(self, value:range):
        if not isinstance(value, range):
            raise TypeError(f"Expecting a range; instead, got {type(value).__name__}")
        self._range_ = value
        # avoid ∞ recursion
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in (self, self.framesQSpinBox, self.framesQSlider)]
        if len(self._range_):
            mn = min(self._range_)
            mx = max(self._range_)
        else:
            mn = mx = 0
        self.framesQSpinBox.setMinimum(mn)
        self.framesQSpinBox.setMaximum(mx)
        self.framesQSlider.setMinimum(mn)
        self.framesQSlider.setMaximum(mx)
        self.totalFramesCountLabel.setText(f" of {len(self._range_)}")
        
    @property
    def tracking(self):
        return self._tracking_
    
    @tracking.setter
    def tracking(self, value:bool):
        val = value == True
        self._tracking_ = val
        self.framesQSpinBox.setKeyboardTracking(self._tracking_)
        self.framesQSlider.setTracking(self._tracking_)
        
    @property
    def prefix(self):
        return self._prefix_
    
    @prefix.setter
    def prefix(self, value:str):
        if isinstance(value, str):
            self._prefix_ = value
            self.framesQSpinBox.setPrefix(self._prefix_)
            
    @property
    def value(self):
        return self._value_
    
    @value.setter
    def value(self, value:int):
        # avoid ∞ recursion
        signalBlockers = [QtCore.QSignalBlocker(widget) for widget in (self, self.framesQSpinBox, self.framesQSlider)]
        self.slot_setValue(value)
        
    def setValue(self, value:int):
        """Convenience setter method - sets the 'value' property to value"""
        self.value = value

    def setMinimum(self, value:int):
        self.minimum = value
        
    def setMaximum(self, value:int):
        """Qt compatible:
        Set the maximum value displayed by this widget.
        This is ≠ self.range.stop.
        """
        self.maximum = value
        
    def setRange(self, minimum:int, maximum:int):
        """Sets the minimum and maximum values.
        Compatible with the Qt equivalent methods of QSlider and QSpinBox, 
        meaning that `maximum` is the maximum value the widget can take
        """
        self._range_= range(minimum, maximum + 1, 1)
        
    def getRange(self):
        """Returns a (self.minimum, self.maximum) tuple.
        """
        return (self.minimum, self.maximum)
        
    def setSingleStep(self, value:int):
        self.singleStep = value
    
    def setPageStep(self, value:int):
        self.pageStep = value
        
    def setToolTip(self, value:typing.Optional[str]=None):
        if isinstance(value, str):
            self._toolTip_ = value
        elif value is None:
            self._toolTip_ = "Set current %s" if self.label[:-1] is self.label.endswith(":") else self.label
        else:
            return
        
        self.framesQSlider.setToolTip(self._toolTip_)
        self.framesQSpinBox.setToolTip(self._toolTip_)
        self.descriptionLabel.setToolTip(self._toolTip_)
        self.totalFramesCountLabel.setToolTip(self._toolTip_)
        
    def setWhatsThis(self, value:str):
        if isinstance(value, str):
            self._whatsThis_ = value
        elif value is None:
            self._whatsThis_ = self._toolTip_
        else:
            return
        
        self.framesQSlider.setWhatsThis(self._toolTip_)
        self.framesQSpinBox.setWhatsThis(self._toolTip_)
        self.descriptionLabel.setWhatsThis(self._toolTip_)
        self.totalFramesCountLabel.setWhatsThis(self._toolTip_)
        
    def setStatusTip(self, value:str):
        if isinstance(value, str):
            self._statusTip_ = value
        elif value is None:
            self._statusTip_ = self._toolTip_
        else:
            return
        
        self.framesQSlider.setStatusTip(self._toolTip_)
        self.framesQSpinBox.setStatusTip(self._toolTip_)
        self.descriptionLabel.setStatusTip(self._toolTip_)
        self.totalFramesCountLabel.setStatusTip(self._toolTip_)
        
    @Slot(int)
    def slot_setValue(self, value:int):
        val = int(value)
        # if val in range(self.minimum, self.maximum+1):
        if val in self._range_:
            self._value_ = val
            # avoid ∞ recursion
            signalBlockers = [QtCore.QSignalBlocker(widget) for widget in (self.framesQSpinBox, self.framesQSlider)]
            self.framesQSpinBox.setValue(self._value_)
            self.framesQSlider.setValue(self._value_)
            self.valueChanged.emit(self._value_)
            
           
            
