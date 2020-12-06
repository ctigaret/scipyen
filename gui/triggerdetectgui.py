# -*- coding: utf-8 -*-
import os
from numbers import (Number, Real,)

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__


import quantities as pq

from core.datatypes import (arbitrary_unit, check_time_units, units_convertible,
                            unit_quantity_from_name_or_symbol, UnitTypes)
from core.traitcontainers import DataBag
from core.triggerevent import (TriggerEvent, TriggerEventType,)
from core.triggerprotocols import TriggerProtocol
from gui.workspacegui import WorkspaceGuiMixin

__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_TriggerDetect, _QWidget_ = __loadUiType__(os.path.join(__module_path__, "triggerdetect.ui"))

class TriggerDetectWidget(QtWidgets.QWidget, Ui_TriggerDetect):
    """
    """
    
    def _init__(self, parent=None, presyn=None, postsyn=None, photo=None, imaging=None,
                ephys_start=None, ephys_end=None):
        """
        Named parameters:
        -----------------
        parent: None (default) or a QWidgets.QMainWindow object
            When None, parent is set to be Scipyen's main application window
            
        presyn, postsyn, photo, imaging: None (default) or dict
            Options for presynaptic, postsynaptic, photostimulation, and 
            imaging frame trigger events, respectively.
            
            When dict, they must contain the following fields (case-sensitive):
            "Channel": int
            "Name": str
            "DetectionBegin" : float or python suantity with time units
            "DetectionEnd": float or python suantity with time units
            
        ephys_start, ephys_end: None (default) or pq.Quantity in times units 
            (e.g. pq.s)
            
        """
        super()._init__(parent)
        self.setupUi(self)

        self.signalStart = ephys_start
        self.signalStop  = ephys_stop
        
        self._configure_UI_()
        
        self.setValues("pre", presyn)
        
        self.setValues("post", postsyn)
        
        self.setValues("photo", photo)
        
        self.setValues("imaging", imaging)
        
    def _configure_UI_(self):
        
        self.presynNameLineEdit.variable.redoAvailable=True
        self.presynNameLineEdit.variable.undoAvailable=True
        
        self.postsynNameLineEdit.variable.redoAvailable=True
        self.postsynNameLineEdit.variable.undoAvailable=True
        
        self.photoNameLineEdit.variable.redoAvailable=True
        self.photoNameLineEdit.variable.undoAvailable=True
        
        self.imagingNameLineEdit.variable.redoAvailable=True
        self.imagingNameLineEdit.variable.undoAvailable=True
        
        #self.presynChannelSpinBox.valueChanged.connect(self.slot_channelValueChanged)
        #self.postsynChannelSpinBox.valueChanged.connect(self.slot_channelValueChanged)
        #self.photoChannelSpinBox.valueChanged.connect(self.slot_channelValueChanged)
        #self.imagingChannelSpinBox.valueChanged.connect(self.slot_channelValueChanged)
        
        #self.presynStartDoubleSpinBox.valueChanged.connect(self.slot_timeValueChanged)
        #self.presynStopDoubleSpinBox.valueChanged.connect(self.slot_timeValueChanged)
        #self.postsynStartDoubleSpinBox.valueChanged.connect(self.slot_timeValueChanged)
        #self.postsynStopDoubleSpinBox.valueChanged.connect(self.slot_timeValueChanged)
        #self.photoStartDoubleSpinBox.valueChanged.connect(self.slot_timeValueChanged)
        #self.photoStopDoubleSpinBox.valueChanged.connect(self.slot_timeValueChanged)
        #self.imagingStartDoubleSpinBox.valueChanged.connect(self.slot_timeValueChanged)
        #self.imagingStopDoubleSpinBox.valueChanged.connect(self.slot_timeValueChanged)
        
    def setValues(self, target, src=None):
        if target == "pre":
            groupBox        = self.presynGroupBox
            channelWidget   = self.presynChannelSpinBox
            startWidget     = self.presynStartDoubleSpinBox
            stopWidget      = self.presynStopDoubleSpinBox
            nameWidget      = self.presynNameLineEdit
            
        elif target == "post":
            groupBox        = self.postsynGroupBox
            channeWidget    = self.postsynChannelSpinBox
            startWidget     = self.postsynStartDoubleSpinBox
            stopWidget      = self.postsynStopDoubleSpinBox
            nameWidget      = self.postsynNameLineEdit
            
        elif target == "photo":
            groupBox        = self.photoGroupBox
            stopWidget      = self.photoStopDoubleSpinBox
            channelWidget   = self.photoChannelSpinBox
            startWidget     = self.photoStartDoubleSpinBox
            nameWidget      = self.photoNameLineEdit
            
        elif target == "imaging":
            groupBox        = self.imagingGroupBox
            channelWidget   = self.imagingChannelSpinBox
            startWidget     = self.imagingStartDoubleSpinBox
            stopWidget      = self.imagingStopDoubleSpinBox
            nameWidget      = self.imagingNameLineEdit
            
        else:
            warnings.warn("Unknown options targeted")
            return
        
        if src is None:
            groupBox.setChecked(False)
            return
        
        elif isinstance(src, dict):
            groupBox.setChecked(True)
            signalBlockers = [QtCore.QSignalBlocker(w) for w in (channelWidget,
                                                                 startWidget,
                                                                 stopWidget,
                                                                 nameWidget)]
            
            channel = src.get("Channel", 0)
            
            if not isinstance(channel, Real):
                raise TypeError("Unexpected type for %s channel: %s" % (target, type(channel).__name__))
            
            channelWidget.setValue(int(channel))

            name = src.get("Name", target)
            if isinstance(name, str) and len(name.strip()):
                nameWidget.setText(name)
                
            else:
                nameWidget.setText(target)
                
            start = src.get("DetectionBegin", self._sig_start_)
            
            if isinstance(start, pq.Quantity):
                if check_time_units(start):
                    start = start.rescale(pq.s)
                    
                else:
                    raise TypeError("Wrong units for %s start: %s" % (target, start.units.dimensionality))
                    
                startWidget.setValue(float(start.magnitude.flatten()[0]))
                
            elif isinstance(start, Real):
                startWidget.setValue(float(start))
                
            elif sytart is None:
                startWidget.setValue(self.signalStart)
                
            else:
                raise TypeError("Unexpected type for %s start: %s" % (target, type(start).__name__))
                
            stop = src.get("DetectionEnd", self._sig_stop_)
            
            if isinstance(stop, pq.Quantity):
                if check_time_units(start):
                    stop = stop.rescale(pq.s)
                else:
                    raise TypeError("Wrong units for %s stop: %s" % (target, stop.units.dimensionality))
                    
                    
                stopWidget.setValue(float(stop.magnitude.flatten()[0]))
                
            elif isinstance(stop, Real):
                stopWidget.setValue(float(stop))
                
            elif stop is None:
                stopWidget.setValue(self.signalStop)
                
            else:
                raise TypeError("Unexpected type for %s stop: %s" % (target, type(stop).__name__))
            
    @property
    def signalStart(self):
        return self._sig_start_
    
    @signalStart.setter
    def signalStart(self, value):
        if isinstance(value, pq.Quantity):
            if check_time_units(value):
                self._sig_start_ = float(value.rescale(pq.s).magnitude.flatten()[0])
                
            else:
                raise TypeError("Unexpected units for signal start: %s" % value.units.dimensionality)
            
        elif isinstance(value, Real):
            self._sig_start_ = float(value)
            
        elif value is None:
            self._sig_start_ = 0.
            
        else:
            raise TypeError("Unexpected type for signal start: %s" % type(value).__name__)
        
    @property
    def signalStop(self):
        return self._sig_stop_
    
    @signalStop.setter
    def signalStop(self, value):
        if isinstance(value, pq.Quantity):
            if check_time_units(value):
                self._sig_stop_ = float(value.rescale(pq.s).magnitude.flatten()[0])
                
            else:
                raise TypeError("Unexpected units for signal stop: %s" % value.units.dimensionality)
            
        elif isinstance(value, Real):
            self._sig_stop_ = float(value)
            
        elif value is None:
            self._sig_stop_ = 0.
            
        else:
            raise TypeError("Unexpected type for signal stop: %s" % type(value).__name__)
        
    @property
    def hasPresynapticTrigger(self):
        return self.presynGroupBox.isChecked()
                
    @property
    def hasPostsynapticTrigger(self):
        return self.postsynGroupBox.isChecked()
                
    @property
    def hasPhotostimulationTrigger(self):
        return self.photoGroupBox.isChecked()
                
    @property
    def hasImagingFrameTrigger(self):
        return self.imagingGroupBox.isChecked()
    
    
    @property
    def presynapticTrigger(self):
        if self.presynGroupBox.isChecked():
            return DataBag({"Channel": self.presynChannelSpinBox.value(),
                            "DetectionBegin": self.presynStartDoubleSpinBox.value() * pq.s,
                            "DetectionEnd": self.presynStopDoubleSpinBox.value() * pq.s,
                            "Name": self.presynNameLineEdit.text()}, allow_none=True)
            
        
    @property
    def postsynapticTrigger(self):
        if self.postsynGroupBox.isChecked():
            return DataBag({"Channel": self.postsynChannelSpinBox.value(),
                           "DetectionBegin": self.postsynStartDoubleSpinBox.value() * pq.s,
                           "DetectionEnd": self.postsynStopDoubleSpinBox.value() * pq.s,
                           "Name": self.postsynNameLineEdit.text()})
        
    @property
    def photostimulationTrigger(self):
        if self.photoGroupBox.isChecked():
            return DataBag({"Channel": self.photoChannelSpinBox.value(),
                            "DetectionBegin": self.photoStartDoubleSpinBox.value() * pq.s,
                            "DetectionEnd": self.photoStopDoubleSpinBox.value() * pq.s,
                            "Name": self.photoNameLineEdit.text()})
        
    @property
    def imagingFrameTrigger(self):
        if self.imagingGroupBox.isChecked():
            return DataBag({"Channel": self.imagingChannelSpinBox.value(),
                            "DetectionBegin": self.imagingStartDoubleSpinBox.value() * pq.s,
                            "DetectionEnd": self.imagingStopDoubleSpinBox.value() * pq.s,
                            "Name": self.imagingNameLineEdit.text()})
                
    #@pyqtSlot(int)
    #def slot_channelValueChanged(self, value):
        #sender = self.sender()
        #if sender is self.presynChannelSpinBox:
            #target = self.presynapticOptions
        #elif sender is self.postsynChannelSpinBox:
            #target = self.postsynapticOptions
        #elif sender is self.photoChannelSpinBox:
            #target = self.phototriggerOptions
        #elif sender is self.imagingChannelSpinBox:
            #target = self.imagingframeOptions
            
        #else:
            #return
        
        #if isinstance(value, Real):
            #target.channel = int(value)
        
    #@pyqtSlot(float)
    #def slot_timeValueChanged(self, value):
        #sender = self.sender()
        
        #if sender is self.presynStartDoubleSpinBox:
            #target = self.presynapticOptions
            #field = "start"
        
        #elif sender is self.presynStopDoubleSpinBox:
            #target = self.presynapticOptions
            #field = "stop"
        
        #elif sender is self.postsynStartDoubleSpinBox:
            #target = self.postsynapticOptions
            #field = "start"
        
        #elif sender is self.postsynStopDoubleSpinBox:
            #target = self.postsynapticOptions
            #field = "stop"
        
        #elif sender is self.photoStartDoubleSpinBox:
            #target = self.phototriggerOptions
            #field = "start"
        
        #elif sender is self.photoStopDoubleSpinBox:
            #target = self.phototriggerOptions
            #field = "stop"
        
        #elif sender is self.imagingStartDoubleSpinBox:
            #target = self.imagingframeOptions
            #field = "start"
        
        #elif sender is self.imagingStopDoubleSpinBox:
            #target = self.imagingframeOptions
            #field = "stop"
            
        #else:
            #return
        
        #if isinstance(value, Real):
            #target[field] = float(value)
        
