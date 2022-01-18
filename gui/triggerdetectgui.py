# -*- coding: utf-8 -*-
import os, typing
from numbers import (Number, Real,)
from itertools import chain
#from itertools import (accumulate, chain,)

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType

import numpy as np
import quantities as pq
from neo import (Block, Segment,)

from core.quantities import (arbitrary_unit, check_time_units, units_convertible,
                            unit_quantity_from_name_or_symbol,quantity2str,)

from core.datatypes import UnitTypes

from core.traitcontainers import DataBag
from core.triggerevent import (TriggerEvent, TriggerEventType,)

from core.triggerprotocols import (TriggerProtocol,
                                   auto_detect_trigger_protocols,
                                   embed_trigger_protocol, 
                                   embed_trigger_event,
                                   get_trigger_events,
                                   parse_trigger_protocols,
                                   remove_trigger_protocol,
                                   parse_trigger_protocols,)

from core.neoutils import (concatenate_blocks, get_events,
                           check_ephys_data_collection, check_ephys_data)

from core.strutils import numbers2str

from gui import quickdialog as qd
from gui.signalviewer import SignalViewer

__module_path__ = os.path.abspath(os.path.dirname(__file__))

Ui_TriggerDetectWidget, QWidget = loadUiType(os.path.join(__module_path__, "triggerdetect.ui"), from_imports=True, import_from="gui")

class TriggerDetectWidget(QWidget, Ui_TriggerDetectWidget):
    """
    """
    
    sig_dataChanged = pyqtSignal()
    
    def __init__(self, ephys_start:typing.Union[Real, pq.Quantity]=0, 
                 ephys_end:typing.Union[Real, pq.Quantity]=1, n_channels:int=0,
                 presyn:typing.Optional[typing.Union[dict, tuple, list]]=None, 
                 postsyn:typing.Optional[typing.Union[dict, tuple, list]]=None,
                 photo:typing.Optional[typing.Union[dict, tuple, list]]=None,
                 imaging:typing.Optional[typing.Union[dict, tuple, list]]=None,  
                 clear:bool=False, parent:typing.Optional[QtWidgets.QWidget]=None):
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
        super().__init__(parent)

        self._sig_start_  = ephys_start
        self._sig_stop_   = ephys_end
        self._n_channels_ = n_channels
        
        self._configureUI_()
        
        self.setValues("pre", presyn)
        
        self.setValues("post", postsyn)
        
        self.setValues("photo", photo)
        
        self.setValues("imaging", imaging)
        
        #self.clearExisting = clear is True
        
    def _configureUI_(self):
        self.setupUi(self)
        self.presynNameLineEdit.redoAvailable=True
        self.presynNameLineEdit.undoAvailable=True
        
        self.postsynNameLineEdit.redoAvailable=True
        self.postsynNameLineEdit.undoAvailable=True
        
        self.photoNameLineEdit.redoAvailable=True
        self.photoNameLineEdit.undoAvailable=True
        
        self.imagingNameLineEdit.redoAvailable=True
        self.imagingNameLineEdit.undoAvailable=True
        
        self._update_channel_ranges_()
        self._update_time_ranges_()
        
    def setValues(self, target, src=None):
        """Populates the fields for the trigger event type corresponding to target
        """
        if target in ("pre", "presyn", "presynaptic"):
            groupBox        = self.presynGroupBox
            channelWidget   = self.presynChannelSpinBox
            nameWidget      = self.presynNameLineEdit
            startWidget     = self.presynStartDoubleSpinBox
            stopWidget      = self.presynStopDoubleSpinBox
            
        elif target in ("post", "postsyn", "postsynaptic"):
            groupBox        = self.postsynGroupBox
            channelWidget   = self.postsynChannelSpinBox
            nameWidget      = self.postsynNameLineEdit
            startWidget     = self.postsynStartDoubleSpinBox
            stopWidget      = self.postsynStopDoubleSpinBox
            
        elif target in ("photo", "photostim", "pstim", "phstim", 
                        "photostimulation", "uncage", "uncaging", 
                        "photoconv", "photoconversion"):
            groupBox        = self.photoGroupBox
            nameWidget      = self.photoNameLineEdit
            channelWidget   = self.photoChannelSpinBox
            startWidget     = self.photoStartDoubleSpinBox
            stopWidget      = self.photoStopDoubleSpinBox
            
        elif target in ("imaging", "frame", "imaging_frame", "imgframe"):
            groupBox        = self.imagingGroupBox
            channelWidget   = self.imagingChannelSpinBox
            nameWidget      = self.imagingNameLineEdit
            startWidget     = self.imagingStartDoubleSpinBox
            stopWidget      = self.imagingStopDoubleSpinBox
            
        elif target == "clear":
            if src is None: # toggle
                self.clearExisting = not self.clearExisting
                
            elif isinstance(src, bool):
                self.clearExisting = src
            else:
                raise TypeError("When target is 'clear', src is expected to be None or a bool")
            
            self.clearExistingEventsCheckBox.setChecked(QtCore.Qt.Checked if self.clearExisting else QtCore.Qt.Unchecked)
            
        else:
            warnings.warn("Unknown options targeted")
            return
        
        if src is None:
            groupBox.setChecked(False)
            return
        
        signalBlockers = [QtCore.QSignalBlocker(w) for w in (channelWidget,
                                                             nameWidget,
                                                             startWidget,
                                                             stopWidget)]
        
        channel = 0
        name = target
        start = self._sig_start_
        stop = self._sig_stop_
        
        if isinstance(src, dict):
            channel = src.get("Channel", 0)
            name = src.get("Name", target)
            start = src.get("DetectionBegin", self._sig_start_)
            stop = src.get("DetectionEnd", self._sig_stop_)
            
        elif isinstance(src, (tuple, list)) and len(src) in (2,3):
            channel = src[0]
            name = src[1]
            if len(src) == 3 and isinstance(src[2], (tuple, list)) and len(src[2]) == 2:
                start = src[2][0]
                stop = src[2][1]
                
        else:
            raise TypeError("Unexpected argument for src: %s" % src)
        
        
        if isinstance(channel, int):
            if channel < 0:
                channel = 0
                
            elif isinstance(self._n_channels_, int) and channel >= self._n_channels_:
                channel = self._n_channels_ - 1
                
        else:
            channels = 0
            
            
        if not isinstance(name, str) or len(name.strip()) == 0:
            name = target
            
        channelWidget.setValue(channel)
        nameWidget.setText(name)
        startWidget.setValue(self._check_time_value_("start", start))
        stopWidget.setValue(self._check_time_value_("stop", stop))

        groupBox.setChecked(True)
            
    @property
    def nChannels(self):
        return self._n_channels_
    
    @nChannels.setter
    def nChannels(self, value):
        if isinstance(value, Real):
            if value < 0:
                self._n_channels_ = 0
                
            else:
                self._n_channels_ = int(value)
                
            self._update_channel_ranges_()
            
    @property
    def signalStart(self):
        return self._sig_start_
    
    @signalStart.setter
    def signalStart(self, value):
        value = self._check_time_value_("start", value)
        if isinstance(value, pq.Quantity):
            if check_time_units(value):
                value = float(value.rescale(pq.s).magnitude.flatten()[0])
                
            else:
                raise TypeError("Unexpected units for signal start: %s" % value.units.dimensionality)
            
        elif isinstance(value, Real):
            value = float(value)
            
        elif value is None:
            value = 0.
            
        else:
            raise TypeError("Unexpected type for signal start: %s" % type(value).__name__)
        
        self._sig_start_ = value
        
        self._sig_start_, self._sig_stop_ = np.sort([self._sig_start_, self._sig_stop_])
        
        self._update_time_ranges_()
        
    @property
    def signalStop(self):
        return self._sig_stop_
    
    @signalStop.setter
    def signalStop(self, value):
        value = self._check_time_value_("stop", value)
        
        self._sig_stop_ = value
        
        self._sig_start_, self._sig_stop_ = np.sort([self._sig_start_, self._sig_stop_])
        
        self._update_time_ranges_()
        
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
    def presyn(self):
        """Tuple: ( signal index, label, (t_start, t_stop) )
        """
        if self.presynGroupBox.isChecked():
            return (self.presynChannelSpinBox.value(),
                    self.presynNameLineEdit.text(),
                    (self.presynStartDoubleSpinBox.value() * pq.s,
                     self.presynStopDoubleSpinBox.value() * pq.s,),
                    )
        
        return ()
    
    @presyn.setter
    def presyn(self, value):
        self.setValues("presyn", value)
            
    @property
    def presynapticOptions(self):
        if self.presynGroupBox.isChecked():
            return DataBag({"Channel": self.presynChannelSpinBox.value(),
                            "DetectionBegin": self.presynStartDoubleSpinBox.value() * pq.s,
                            "DetectionEnd": self.presynStopDoubleSpinBox.value() * pq.s,
                            "Name": self.presynNameLineEdit.text()}, allow_none=True)
            
    @property
    def postsyn(self):
        if self.postsynGroupBox.isChecked():
            return (self.postsynChannelSpinBox.value(),
                    self.postsynNameLineEdit.text(),
                    (self.postsynStartDoubleSpinBox.value() * pq.s,
                     self.postsynStopDoubleSpinBox.value() * pq.s,),
                    )
                    
        return ()
    
    @postsyn.setter
    def postsyn(self, value):
        self.setValues("postsyn", value)
        
    @property
    def postsynapticOptions(self):
        if self.postsynGroupBox.isChecked():
            return DataBag({"Channel": self.postsynChannelSpinBox.value(),
                           "DetectionBegin": self.postsynStartDoubleSpinBox.value() * pq.s,
                           "DetectionEnd": self.postsynStopDoubleSpinBox.value() * pq.s,
                           "Name": self.postsynNameLineEdit.text()})
        
    @property
    def photo(self):
        if self.photoGroupBox.isChecked():
            return (self.photoChannelSpinBox.value(),
                    self.photoNameLineEdit.text(),
                    (self.photoStartDoubleSpinBox.value() * pq.s,
                     self.photoStopDoubleSpinBox.value() * pq.s,),
                    )
                    
        return ()
    
    @photo.setter
    def photo(self, value):
        self.setValues("photo", value)
        
    @property
    def photostimulationOptions(self):
        if self.photoGroupBox.isChecked():
            return DataBag({"Channel": self.photoChannelSpinBox.value(),
                            "DetectionBegin": self.photoStartDoubleSpinBox.value() * pq.s,
                            "DetectionEnd": self.photoStopDoubleSpinBox.value() * pq.s,
                            "Name": self.photoNameLineEdit.text()})
        
    @property
    def imaging(self):
        if self.imagingGroupBox.isChecked():
            return (self.imagingChannelSpinBox.value(),
                    self.imagingNameLineEdit.text(),
                    (self.imagingStartDoubleSpinBox.value() * pq.s,
                     self.imagingStopDoubleSpinBox.value() * pq.s,),
                    )
                    
        return ()
    
    @imaging.setter
    def imaging(self, value):
        self.setValues("imaging", value)
                
    @property
    def imagingFrameOptions(self):
        if self.imagingGroupBox.isChecked():
            return DataBag({"Channel": self.imagingChannelSpinBox.value(),
                            "DetectionBegin": self.imagingStartDoubleSpinBox.value() * pq.s,
                            "DetectionEnd": self.imagingStopDoubleSpinBox.value() * pq.s,
                            "Name": self.imagingNameLineEdit.text()})
                
        
    @pyqtSlot(int)
    @pyqtSlot(float)
    @pyqtSlot(str)
    def slot_paramValueChangedGui(self, value=None):
        self.sig_dataChanged.emit()
        
    def _check_time_value_(self, what, value):
        if what not in ("start", "stop"):
            raise ValueError("First argument expected to be either 'start' or 'stop'; got %s instead" % what)
        
        if isinstance(value, pq.Quantity):
            if value.size == 1:
                if check_time_units(value):
                    value = value.rescale(pq.s)
                    
                else:
                    raise TypeError("Wrong units for %s %s: %s" % (target, what, value.units.dimensionality))
            else:
                raise TypeError("%s value for %s must be a singleton; got %s instead" % (what, target, value))
            
            value = float(value.magnitude)
            
        elif isinstance(value, np.ndarray):
            if value.size != 1:
                raise TypeError("%s value for %s must be a singleton; got %s instead" % (what, target, value))
            
            value = float(value)
            
        elif isinstance(value, Real):
            value = float(value)
            
        elif value is None:
            if what == "start":
                value = 0.
                
            else:
                value = 1.
                
        else:
            raise TypeError("Unexpected %s value: %s" % (what, value))
            
        return value
    
    def _update_time_ranges_(self):
        widgets = (self.presynStartDoubleSpinBox,
                    self.presynStopDoubleSpinBox,
                    self.postsynStartDoubleSpinBox,
                    self.postsynStopDoubleSpinBox,
                    self.photoStartDoubleSpinBox,
                    self.photoStopDoubleSpinBox,
                    self.imagingStartDoubleSpinBox,
                    self.imagingStopDoubleSpinBox)
        
        signalBlockers = [QtCore.QSignalBlocker(w) for w in widgets]
        
        for w in widgets:
            w.setMinimum(self._sig_start_)
            w.setMaximum(self._sig_stop_)
        
    def _update_channel_ranges_(self):
        widgets = (self.presynChannelSpinBox,
                   self.postsynChannelSpinBox,
                   self.photoChannelSpinBox,
                   self.imagingChannelSpinBox)
        
        signalBlockers = [QtCore.QSignalBlocker(w) for w in widgets]
        
        for w in widgets:
            w.setMinimum(0)
            if self._n_channels_ == 0:
                w.setMaximum(0)
            else:
                w.setMaximum(self._n_channels_ - 1)
                
class TriggerDetectDialog(qd.QuickDialog):
    sig_detectTriggers = pyqtSignal(name="sig_detectTriggers")
    sig_undoDetectTriggers = pyqtSignal(name="sig_undoDetectTriggers")
    
    def __init__(self, ephysdata=None, title="Detect Trigger Events", clearEvents=False,
                 parent=None, ephysViewer=None, **kwargs):
        super().__init__(parent=parent, title=title) # calls ancestor's setupUi()
            
        self.eventDetectionWidget = TriggerDetectWidget(parent = self) 
        self.addWidget(self.eventDetectionWidget)
        
        self._clear_events_flag_ = clearEvents
        
        # NOTE: 2021-04-11 17:02:58
        # thsi only informs that the detection had been performed, NOT if any
        # events had been detected!
        self._triggers_detected_ = False # True does NOT imply trigger events had been detected!
        
        self.triggerProtocols = list()
        
        
        if not isinstance(ephysViewer, SignalViewer):
            self._ephysViewer_ = SignalViewer(win_title = "Trigger Events Detection")
            self._owns_viewer_ = True
            
        else:
            self._ephysViewer_ = ephysViewer
            self._owns_viewer_ = False
        
        self._ephysViewer_.frameChanged[int].connect(self._slot_ephysFrameChanged)
        
        self.clearEventsCheckBox = qd.CheckBox(self, "Clear existing")
        
        self.clearEventsCheckBox.setIcon(QtGui.QIcon.fromTheme("edit-clear-history"))
        self.clearEventsCheckBox.setChecked(self._clear_events_flag_)
        self.clearEventsCheckBox.stateChanged.connect(self._slot_clearEventsChanged)
        
        self.detectTriggersPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-find"),
                                                              "Detect", parent=self.buttons)
        self.detectTriggersPushButton.clicked.connect(self.slot_detect)
        
        self.undoTriggersPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("edit-undo"),
                                                            "Undo", parent=self.buttons)
        self.undoTriggersPushButton.clicked.connect(self.slot_undo)
        
        # NOTE: 2021-01-06 10:57:10
        # extend/reuse the Quickdialog's own button box => widgets nicely aligned
        # on the same row instead of occupying an additional row
        self.buttons.layout.insertWidget(0, self.clearEventsCheckBox)
        self.buttons.layout.insertWidget(1, self.detectTriggersPushButton)
        self.buttons.layout.insertWidget(2, self.undoTriggersPushButton)
        self.buttons.layout.insertStretch(3)
        
        # NOTE: 2021-01-06 11:14:37 also place fancy icons on quickdialog's standard buttons
        self.buttons.OK.setIcon(QtGui.QIcon.fromTheme("dialog-ok-apply"))
        self.buttons.Cancel.setIcon(QtGui.QIcon.fromTheme("dialog-cancel"))
        
        self.statusBar = QtWidgets.QStatusBar(parent=self)
        self.addWidget(self.statusBar)
        
        self.setWindowModality(QtCore.Qt.WindowModal)
        
        # parse ephysdata parameter
        self._ephys_= None
        
        self._set_ephys_data_(ephysdata)
        self.setSizeGripEnabled(True)
            
    def _set_ephys_data_(self, value):
        if check_ephys_data_collection(value, mix=False):
            # no mixing of types when ephysdata is a sequence ...
            self._ephys_ = value
            self._cached_events_ = get_events(self._ephys_)
            
            flat_events = get_events(self._ephys_, flat=True)
            
            if len(flat_events):
                nEvents = len(flat_events)
                nTriggers = len([t for t in flat_events if isinstance(t, TriggerEvent)])
                self.statusBar.showMessage("Data has %d events, of which %d are trigger events" % (nEvents, nTriggers))

            if self.isVisible():
                self._ephysViewer_.plot(self._ephys_)
            
            self._update_trigger_detect_ranges_(0)
            
        else:
            self._cached_events_ = list()
        

    def open(self):
        if self._ephys_:
            self._ephysViewer_.plot(self.ephysdata)
        super().open()
        
    def exec(self):
        if self._ephys_:
            self._ephysViewer_.plot(self.ephysdata)
        return super().exec()
        
    def closeEvent(self, evt):
        """for when the dialog is closed from the window's close button
        """
        print("closeEvent owns viewer", self._owns_viewer_)
        if self._ephysViewer_.isVisible():
            if self._owns_viewer_:
                self._ephysViewer_.close()
            else:
                self._ephysViewer_.refresh()
                
        # NOTE: 2021-04-16 11:30:35
        # unbind the SignalViewer reference from this symbol, otherwise the garbage
        # collector will try to double-delete C++ objects (in pyqtgraph)
        #self._ephysViewer_ = None
        
        super().closeEvent(evt)
        
    @pyqtSlot()
    def accept(self):
        #print("accept owns viewer", self._owns_viewer_)
        super().accept()
        # NOTE: 2021-04-16 11:24:35 this calls done(QDialog.Accepted), which 
        # does all the things commented below
        #if self._ephysViewer_.isVisible():
            #if self._owns_viewer_:
                #self._ephysViewer_.close()
            #else:
                #self._ephysViewer_.refresh()
                
        
    @pyqtSlot()
    def reject(self):
        #print("reject owns viewer", self._owns_viewer_)
        super().reject()
        # NOTE: 2021-04-16 11:24:48 this calls done(QDialog.Rejected), which 
        # does all the things commented below
        #if self._ephysViewer_.isVisible():
            #if self._owns_viewer_:
                #self._ephysViewer_.close()
            #else:
                #self._ephysViewer_.refresh()
        
    @pyqtSlot(int)
    def done(self, value):
        if value == QtWidgets.QDialog.Accepted and not self.detected:
            self.detect_triggers()
            
        #print("done owns viewer", self._owns_viewer_)
        if self._ephysViewer_.isVisible():
            if self._owns_viewer_:
                self._ephysViewer_.close()
            
            else:
                self._ephysViewer_.refresh()
                
        # NOTE: 2021-04-16 11:30:35
        # unbind the SignalViewer reference from this symbol, otherwise the garbage
        # collector will try to double-delete C++ objects (in pyqtgraph)
        #self._ephysViewer_ = None
            
        super().done(value)
        
    @pyqtSlot()
    def _slot_clearEventsChanged(self):
        self._clear_events_flag_ = self.clearEventsCheckBox.selection()
        
    @pyqtSlot(int)
    def _slot_ephysFrameChanged(self, value):
        self._update_trigger_detect_ranges_(value)
        
    @pyqtSlot()
    def slot_detect(self):
        if self._ephys_ is None:
            return
        
        self.detect_triggers()
        
        if self.isVisible():
            if self._ephysViewer_.isVisible() and  self._ephysViewer_.y:
                self._ephysViewer_.refresh()
            else:
                self._ephysViewer_.plot(self.ephysdata)
                
    @pyqtSlot()
    def slot_undo(self):
        """Quickly restore the events - no fancy stuff
        """
        self._restore_events_()
        if self.isVisible():
            if self._ephysViewer_.isVisible() and self._ephysViewer_.y:
                self._ephysViewer_.refresh()
            else:
                self._ephysViewer_.plot(self._ehys_)
                
        self.detected = False
        
    def _restore_events_(self):
        if len(self._cached_events_):
            if isinstance(self._ephys_, Block):
                for k, s in enumerate(self._ephys_.segments):
                    s.events[:] = self._cached_events_[k][:]
                    
            elif isinstance(self._ephys_, Segment):
                self._ephys_.events[:] = self._cached_events_[0][:]
                
            elif isinstance(self._ephys_, (tuple, list)):
                if all([isinstance(v, Block) for v in self._ephys_]):
                    for k, b in enumerate(self._ephys_):
                        for ks, s in enumerate(b.segments):
                            s.events[:] = self._cached_events_[k][ks][:]
                            
                elif all([isinstance(v, Segment) for v in self._ephys_]):
                    for k, s in enumerate(self._ephys_):
                        s.events[:] = self._cached_events_[k][:]
                        
    @property
    def detected(self):
        return self._triggers_detected_
    
    @detected.setter
    def detected(self, val):
        self._triggers_detected_ = val
        self.detectTriggersPushButton.setEnabled(not self._triggers_detected_)
        
    @property
    def ephysdata(self):
        return self._ephys_
    
    @ephysdata.setter
    def ephysdata(self, value):
        self._set_ephys_data_(value)
        ##if not isinstance(value, (Block, Segment, tuple, list)):
        #if not check_ephys_data_collection(value, mix=False):
            #return
        
        #self._ephys_ = value
        #self._cached_events_ = get_events(self._ephys_)
        #flat_events = get_events(self._ephys_, flat=True)
        #nEvents = len(flat_events)
        #nTriggers = len([t for t in flat_events is isinstance(t, TriggerEvent)])
        #self.statusBar.showMessage("Data has %d events, of which %d are trigger events" % (nEvents, nTriggers))
        
        #if self.isVisible():
            #self._ephysViewer_.plot(self._ephys_)
        
        #self._update_trigger_detect_ranges_(0)
        
    @property
    def presyn(self):
        return self.eventDetectionWidget.presyn
    
    @property
    def postsyn(self):
        return self.eventDetectionWidget.postsyn
    
    @property
    def photo(self):
        return self.eventDetectionWidget.photo
    
    @property
    def imaging(self):
        return self.eventDetectionWidget.imaging
    
    def detect_triggers(self):
        if self._ephys_ is None:
            self.detected=False
            return
        
        if any((self.presyn, self.postsyn, self.photo, self.imaging)):
            self._cached_events_ = get_events(self._ephys_) # cache all events, not just the trigger ones
            
            # NOTE: 2021-03-21 14:29:27
            # only clear existing trigger events
            clear_flag = "triggers" if self._clear_events_flag_ else False
            
            tp = auto_detect_trigger_protocols(self._ephys_,
                                        presynaptic = self.presyn,
                                        postsynaptic = self.postsyn,
                                        photostimulation = self.photo,
                                        imaging = self.imaging,
                                        clear = clear_flag,
                                        protocols=True)
            
            self.triggerProtocols[:] = tp[:]
            
            
            if len(self.triggerProtocols) == 0:
                self._restore_events_()
                self.detected = False
                
            else:
                self.detected = True
                
            nEvents = len(get_trigger_events(self.ephysdata, flat=True))
            
            self.statusBar.showMessage("%d trigger events detected" % nEvents)
        
       
    def _update_trigger_detect_ranges_(self, frameindex):
        if self._ephys_ is None:
            return
        
        segment = None
        
        if isinstance(self._ephys_, Block):
            if frameindex < 0 or frameindex >= len(self._ephys_.segments):
                raise ValueError("Incorrect frame index %s" % frameindex)
            
            segment = self._ephys_.segments[frameindex]
            
        elif isinstance(self._ephys_, Segment):
            segment = self._ephys_
            
        elif isinstance(self._ephys_, (tuple, list)):
            if all([isinstance(v, Block) for v in self._ephys_]):
                segments = list(chain(*(b.segments for b in self._ephys_)))
                segment = segments[frameindex]
                
            elif all([isinstance(v, Segment) for v in self._ephys_]):
                segment = self._ephys_[frameindex]
                
            else:
                return
            
        else:
            return
        
        if segment:
            nChannels = max([len(seg.analogsignals) + len(seg.irregularlysampledsignals) for seg in self._ephys_.segments])
            self.eventDetectionWidget.nChannels = nChannels
            #self.eventDetectionWidget.nChannels = len(segment.analogsignals)
            
            self.eventDetectionWidget.signalStart = float(min([sig.t_start for sig in segment.analogsignals]).magnitude)
            self.eventDetectionWidget.sgnalStop = float(max([sig.t_stop for sig in segment.analogsignals]).magnitude)
        
        
def guiDetectTriggers(data:Block):
    if isinstance(data, Block) and len(data.segments):
        eventDetectionDialog = TriggerDetectDialog(ephysdata = data,
                                                   clearEvents = True)
        
        result = eventDetectionDialog.exec()
        
        if result == QtWidgets.QDialog.Accepted:
            return eventDetectionDialog.triggerProtocols
    
