# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUiType as __loadUiType__


__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_SpinBoxSlider, QWidget = __loadUiType(os.path.join(__module_path__, "spinboxslider.ui"))

class SpinBoxSlider(QWidget, Ui_SpinBoxSlider):
    """Compound widget with a SpinBox and Slider.
    Only a minimal set of QSPinBox and QSlider are exposed.
    For more atomic changes access self.framesQSpinBox and self.framesQSlider 
    directly
    """
    valueChanged = pyqtSignal(int, name="valueChanged")
    
    def __init__(self, parent=None):
        self._singleStep_ = 1
        self._pageStep_ = 10
        self._minimum_ = 0
        self._maximum_ = 0
        self._tracking_ = True
        self._prefix_ = ""
        self._value_ = 0

        self._configureUI_()
        
        
    def _configureUI_(self):
        self.setupUi(self)
        self.framesQSpinBox.setKeyboardTracking(False)
        self.framesQSlider.valueChanged.connect(self.slot_setValue)
        self.framesQSpinBox.valueChanged.connect(self.slot_setValue)
        
    @property
    def minimum(self):
        return self._minimum_
    
    @minimum.setter
    def minimum(self, value:int):
        val = int(value)
        self._minimum_ = val
        self.framesQSpinBox.setMinimum(val)
        self.framesQSlider.setMinimum(val)
        
    @property
    def maximum(self):
        return self.maximum
    
    @maximum.setter
    def maximum(self, value:int):
        val = int(value)
        self._maximum_ = val
        self.framesQSpinBox.setMaximum(val)
        self.framesQSlider.setMaximum(val)
        
    @property
    def singleStep(self):
        return self._singleStep_
    
    @singleStep.setter
    def singleStep(self, value:int):
        val = int(val)
        self._singleStep_ = val
        self.framesQSpinBox.setSingleStep(val)
        self.framesQSlider.setSingleStep(val)
        
    @property
    def pageStep(self):
        return self._pageStep_
    
    @pageStep.setter
    def pageStep(self, value:int):
        val = int(value)
        self._pageStep_ = val
        self.framesQSlider.setPageStep(val)
        
    @property
    def tracking(self):
        return self._tracking_
    
    @tracking.setter
    def tracking(self, value:bool):
        val = value == True
        self._tracking_ = True
        self.framesQSpinBox.setTracking(val)
        self.framesQSlider.setTracking(val)
        
    @property
    def prefix(self):
        return self._prefix_
    
    @prefix.setTitlePrefixdef prefix(self, value:str):
        if isinstance(value, str):
            self._prefix_ = value
            self.framesQSpinBox.setPrefix(self._prefix_)

    def setMinimum(self, value:int):
        self.minimum = value
        
    def setMaximum(self, value:int):
        self.maximum = value
        
    def setRange(self, minimum:int, maximum:int):
        self.minimum = minimum
        self.maximum = maximum
        
    def setSingleStep(self, value:int):
        self.singleStep = value
    
    def setPageStep(self, value:int):
        self.pageStep = value

    @pyqtSlot(int)
    def _slot_setValue(self, value:int):
        val = int(value)
        if val in range(self.minimum, self.maximum+1):
            self._value_ = val
            signalBlockers = [QtCore.QSignalBlocker(widget) for widget in \
                (self.framesQSpinBox, self.framesQSlider)]
            self.framesQSpinBox.setValue(self._value_)
            self.framesQSlider.setValue(self._value_)
            self.valueChanged.emit(self._value_)
            
           
            
