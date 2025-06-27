# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


r"""Import routines for PrairieView data, and classes for various PrairiewView
data types.

Classes defined in this module: 
 'PVScan',
 'PVSystemConfiguration',
 'PVSequence',
 'PVSequenceType',
 'PVStateShard',
 'PVFrame',
 'PVLaser',
 'PVLinescanDefinition',
 'PVLinescanMode',
 'PrairieViewImporter'
 
Classes defined in other Scipyen modules and imported in this module:
 'AxesCalibration',
 'AxisCalibrationData',
 'CalibrationData',
 'ChannelCalibrationData',
 'DataBag',
 'ProtocolEditorDialog',
 'ScanData',
 'ScanDataOptions',
 'TriggerDetectDialog',
 'TriggerDetectWidget',
 'TriggerEvent',
 'TriggerEventType',
 'TriggerProtocol',
 'WorkspaceGuiMixin',
 
Qt packages & classes imported in this module:
 'QtCore',
 'QtGui',
 'QtWidgets',
 'Signal',
 'Slot',

Classes imported from Python standard library:
 'Enum',
 'IntEnum',
 'OrderedDict',
"""
#### BEGIN core python modules
import os, sys, traceback, warnings, mimetypes, io, typing, pathlib
import  datetime, time, dateutil
from enum import Enum, IntEnum #, unique
from collections import OrderedDict
import concurrent.futures
import threading
from dataclasses import MISSING
#import xml
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import quantities as pq
import neo
from core.vigra_patches import vigra
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
    

#### END 3rd party modules

#### BEGIN scipyen modules
from core.prog import (scipywarn, print_styled)
from core.utilities import safewrapper
from core.traitcontainers import DataBag
from core.triggerevent import (TriggerEvent, TriggerEventType, )
from core.triggerprotocols import (TriggerProtocol,
                                   auto_detect_trigger_protocols,
                                   embed_trigger_protocol, 
                                   embed_trigger_event,
                                   parse_trigger_protocols,
                                   remove_trigger_protocol,
                                   parse_trigger_protocols)

from core.neoutils import (concatenate_blocks, concatenate_signals,set_relative_time_start)

import core.xmlutils as xmlutils
import core.strutils as strutils
import core.datatypes  
from core.sysutils import adapt_ui_path

import iolib.pictio as pio

# from gui import resources_rc # as resources_rc
# from gui import icons_rc # as icons_rc
from gui import quickdialog as qd
from gui.triggerdetectgui import TriggerDetectDialog, TriggerDetectWidget
from gui.protocoleditordialog import ProtocolEditorDialog
from gui import pictgui as pgui
from gui.workspacegui import WorkspaceGuiMixin
import gui.signalviewer as sv
# from gui import resources_rc

from imaging import (imageprocessing as imgp, axisutils, axiscalibration,)
from imaging.scandata import (ScanData, ScanDataOptions, scanDataOptions,)

from imaging.vigrautils import (concatenateImages, insertAxis)

from imaging.axisutils import (axisTypeFromString, axisTypeName, 
                               axisTypeSymbol, axisTypeUnits,)

from imaging.axiscalibration import (AxesCalibration, 
                                     CalibrationData, 
                                     ChannelCalibrationData, 
                                     AxisCalibrationData)

import ephys.ephys as ephys

#### END scipyen modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__, "PrairieImporter.ui")

if os.environ["QT_API"] in ("pyqt5", "pyside2"):
    __UI_PrairieImporter, __QDialog__ = loadUiType(__ui_path__, from_imports=True, import_from="gui")
else:
    __UI_PrairieImporter, __QDialog__ = loadUiType(__ui_path__)


r""" NOTE: 2017-09-22 09:28:23
Image file organization with respect to (hyper-)volume data (hereafter I describe 
the data structures resulted form parsing an XML file):

PVFrame: collects data belonging to one "frame".

    Its "files" attribute is a list of dictionaries with the following fields:
        "channel"       : int = channel number
        "channelName"   : str = the name of the channel
        "filename"      : str = the name of the image file with actual data (see
                            "filename explained", below)
        "source"        : str = the name of the image file with the "source" data
                            (see "source explained", below)
                            
                            empty for SingleImage
        
        NOTE: the source data is the raster scan serving as a spatial reference
             frame for <ScanType>: the coordinates of whatever has been scanned 
             are defined in the coordinates frame of the source.
                                
    PrairieView saves images as single-frame TIF files, with the following naming 
        scheme:
        
===================
filename explained:
===================

===============================================
<ScanType>-<date>-<session number>-<run number>_Cycle<number>_<SettingsName>_Ch<channel number>_<image number>.tif
===============================================

Example:

LineScan_03102017_1039_000_Cycle00001_CurrentSettings_Ch1_000001.tif

where: 

ScanType  = one of: "LineScan", "SingleImage", "ZSeries"

date = date in the format "mmddyyyy" (e.g. 03102017 in US format, 
                                    meaning 10/03/2017 in European format)

session number = a counter of session (by scan type?); depends on what is already on disk
                only (?) relevant to identify several files as belonging to the same session
                
run number = typically a three-digit number -- the counter of the files recorded 
        within the same batch; relevant to identify the relative order in which the 
        files were recorded;  
        
        CAUTION: the counter does NOT automatically start at 000:
        the start value depends on what the user has entered in the save files 
        dialogue, even if the directory where they are saved is empty
        
        If there are several repeats in the batch (ie. "cycles") then all the files
        will bear the same run number.
        
        
        points to as many files as channels (or bands) in the data

Cycle<number> = the actual number of the cycle within the run; the numeric part 
            usually has five digits

SettingsName = the name of the settings used - typically this comes up as "CurrentSettings"

channel number = the integer index of the channel (starting at 1) -- this is rather
    confusing as it does not reproduce the (presumably user-given) channel name.

file number: file counter (6 digits), always starts at 1 (000001)
            for ZSeries, this gets incremented with each scanning plane 
            for LineScan and SingleImage is stays constant
            
=================
source explained:
=================

===============================================
<ScanType>-<date>-<session number>-<run number>_Cycle<number>_Ch<channel number>Source.tif
===============================================

Example (corrersponding to the file name example, above):

LineScan_03102017_1039_006_Cycle00001_Ch1Source

NOTE:   The sequence <ScanType>-<date>-<session number>-<run number> is also the
        name of the directory where both frame image files and "source" files
        are saved (so at least we know to what session/date/batch run these 
        files belong).
        
    

"""

#@unique
# NOTE: 2017-10-18 22:51:58
# NOTE: some type do not fit here because they're given as multi-word values:
# NOTE: "TSeries Timed Element"; "Point Scan"; testing for these MUST be done
# after splitting the attribute value
PVSequenceType = IntEnum("PVSequenceType", "Single Linescan TSeries ZSeries Point", qualname="PrairieView.PVSequenceType")

# TODO: augument this with the other Linescan types available in the PrairieView software
# circle spiral and lissajous all get internally convereted to freehand coordinates!
PVLinescanMode = IntEnum("PVLinescanMode", "straightLine, freeHand, circle, spiral, lissajous", qualname="PrairieView.PVLinescanMode")

class PVObject(object): 
    def __init__(self):
        self._parent_ = None
        self._stateshard_ = None
        
    @property
    def parent(self):
        return self._parent_
    
    @property
    def state(self):
        return self._stateshard_
    

# TODO: work out other linescan modes
## FIXME: for linescans other than Freehand coordinates is empty!
# NOTE: circle is converted into freehand!
class PVLinescanDefinition(PVObject):
    def __init__(self, node, parent=None):
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "PVLinescanDefinition":
            raise ValueError("Expecting an element node named 'PVLinescanDefinition")
        
        super().__init__()
        self._parent_ = None
        self.line_length = 0
        
        if parent is not None:
            if isinstance(parent, PVSequence) and parent.typename == "Linescan":
                self._parent_ = parent
                
            else:
                raise TypeError("Parent of a PVLinescanDefinition can only be None or a PVSequence of Linescan type")
        
        self._attributes_ = dict()
        
        if node.attributes is not None:
            for k in node.attributes.values():
                try:
                    val=eval(k.value)
                except:
                    val = k.value
                    
                if k.name == "mode":
                    self._attributes_[k.name] = PVLinescanMode[val].value
                else:
                    self._attributes_[k.name] = val
                
        if self._attributes_["mode"] == PVLinescanMode.freeHand:
            freehandnodes = xmlutils.getChildren(node, tagName = "Freehand")
            
            if len(freehandnodes) > 0:
                self._coordinates_ = [(eval(n.attributes.getNamedItem("x").value), eval(n.attributes.getNamedItem("y").value)) for n in freehandnodes]
            else:
                self._coordinates_ = [] # TODO/FIXME what is a good default here?
                    
        #elif self.__dict__["mode"] == PVLinescanMode.straightLine.value:
        elif self._attributes_["mode"] == PVLinescanMode.straightLine:
            linenodes = tuple(xmlutils.getChildren(node, tagName = "Line"))
            if len(linenodes) > 0:
                if len(linenodes) == 1:
                    self._coordinates_ = [(eval(linenodes[0].attributes.getNamedItem("startPixelX").value), \
                                             eval(linenodes[0].attributes.getNamedItem("startPixelY").value)),\
                                            (eval(linenodes[0].attributes.getNamedItem("stopPixelX").value), \
                                             eval(linenodes[0].attributes.getNamedItem("startPixelY").value))]
                else:
                    self._coordinates_ = [((eval(n.attributes.getNamedItem("startPixelX").value), \
                                            eval(n.attributes.getNamedItem("startPixelY").value)), \
                                            (eval(n.attributes.getNamedItem("stopPixelX").value), \
                                            eval(n.attributes.getNamedItem("startPixelY").value))) for n in linenodes]
                    
            self.line_length = linenodes[0].attributes.getNamedItem("lineLength").value
        else: # TODO code for other linescan modes
            self._coordinates_ = [] # for now!
            
        
    @property
    def version(self):
        return self.parent.version
    
    @property
    def versionString(self):
        return self.parent.versionString

    @property
    def parent(self):
        r"""The parent PVSequence object, or None
        """
        return self._parent_
    
    @property
    def attributes(self):
        return self._attributes_
    
    @property
    def mode(self): # read only
        return self._attributes_["mode"]
    
    @property
    def coordinates(self):
        return self._coordinates_
    
    def __as_string__(self, indent_level=0):
        # TODO: return a list of str
        # then, in the caller, pass indent_level > 0
        # to prepend indent_level spaces (or tab characters) to each element in 
        # the list (thus creating a pseudo-tree output)
        pass
    
    def __repr__(self):
        return self.__str__()
        
    def __str__(self): # TODO
        ret = [" Linescan mode: %s\n" % (PVLinescanMode(self.mode).name)]
        #for k,v in self.__dict__.items():
            #ret.append(" %s = %s\n" % (k, v))
        if len(self._attributes_) > 0:
            for k,v in self._attributes_.items():
                ret.append(" %s = %s\n" % (k, v))
        ret.append(" coordinates (x, y):\n ")
        for c in self._coordinates_:
            ret.append("  %s\n" % (c.__str__()))
        ret.append(" length = %g\n" % (self.line_length))
        
        return "".join(ret)
    
    def metadata(self):
        metadata = dict()
        metadata["attributes"] = self._attributes_
        metadata["coordinates"] = self._coordinates_
        metadata["line_length"] = self.line_length
        
        return DataBag(metadata)
        
class PVLaser(PVObject):
    def __init__(self, node, parent=None):
        # if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "Laser":
        # NOTE: 2025-04-01 22:59:10
        # adapt to newer PV version >= 5.5; keep backwards compatibility as much as possible
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName not in ("Laser", "PVLaser"): 
            raise ValueError("Expecting an element node named 'Laser' or 'PVLaser'")
        
        super().__init__()

        self._parent_ = None
        
        if parent is not None:
            if isinstance(parent, PVSystemConfiguration):
                self._parent_ = parent
                
            else:
                raise TypeError("Parent can only be None on a PVSystemConfiguration object")

        if node.attributes is not None:
            self._attributes_ = DataBag(xmlutils.attributesToDict(node))
        else:
            self._attributes_ = DataBag(dict())
            
    @property
    def version(self):
        return self.parent.version
    
    @property
    def versionString(self):
        return self.parent.versionString

    @property
    def parent(self):
        r"""The parent PVSystemConfiguration object, or None
        """
        return self._parent_
    
    @parent.setter
    def parent(self, val):
        if isinstance(val, (None, PVSystemConfiguration)):
            self._parent_ = val
            
        else:
            raise TypeError("Parent can only be None or a PVSystemConfiguration object")
    
    @property
    def attributes(self):
        return self._attributes_
    
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = ["Laser:\n"]
        ret += [" %s = %s\n" % (i[0], i[1]) for i in self._attributes_.items()]
        
        return "".join(ret)

class PVSystemConfiguration(PVObject):
    r"""Encapsulates the configuration of the PrairieView system used for acquisition.
        Sometime around PrairieView v5.5 this has changed from being a node named
        'SystemConfiguration' in the main XML file, to being an auxiliary *env file
        (also in XML format) where the top node is named 'Environment'.
        
        I think in PrairiewView >= 5.5 there is the option to save files in the 
        'old' ('legacy') format, but I haven't checked if this is compatible with
        the (old) code here dealing with PrairieView 5.0.
        
        Instead of renaming this class to PVEnvironment, I will just create an 
        alias to it, in this module.
    """
    def __init__(self, node, parent=None):
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName not in ("SystemConfiguration", "Environment"):
            raise ValueError("Expecting an element node named 'SystemConfiguration' or 'Environment'")

        super().__init__()
        self._parent_ = None
        self.lasers = list()
        
        if parent is not None:
            if isinstance(parent, PVScan):
                self._parent_ = parent
            else:
                raise TypeError("Parent of a PVSystemConfiguration can only be one or a PVScan object")

        if node.attributes is not None:
            self._attributes_ = DataBag(xmlutils.attributesToDict(node))
            v = self._attributes_.get("version", None)
            if isinstance(v, str) and len(v.strip()):
                try:
                    self.__version__ = tuple(map(lambda x: eval(x), v.split('.')))
                except:
                    scipywarn(f"Could not parse the Prairie Environment (SystemConfiguration) version data {v})")
                                        
            else: # get the parent's version
                self.__version__ = parent.version
            
            d = self._attributes_.get("date", None)
            # print(f"{self.__class__.__name__}.__init__: d for date = {d}")
            if isinstance(d, str) and len(d.strip()):
                try:
                    self._rec_datetime_ = dateutil.parser.parse(d)
                    # self._rec_datetime_ = datetime.datetime.fromisoformat(d)
                except:
                    traceback.print_exc()
                    scipywarn(f"Due to the above caught exception, rec_datetime will be set to `datetime.now()`")
            else: # get the parent's version
                self._rec_datetime_ = parent._rec_datetime_
            # else:
            #     scipywarn(f"No suitable date string found; rec_datetime will be set to `datetime.now()")
                
        else:
            self._attributes_ = DataBag(dict())
        
        if self.versionString >= '5.5':
            tag1 = "PVLasers"
            tag2 = "PVLaser"
        else:
            tag1 = "Lasers"
            tag2 = "Laser"
            
        lasersNodes = tuple(xmlutils.getChildren(node, tagName = tag1))
        if len(lasersNodes):
            laserNodes = xmlutils.getChildren(lasersNodes[0], tagName=tag2)
            self.lasers[:] = list(map(lambda l: PVLaser(l, self), laserNodes))
            
            
        self._data_ = xmlutils.elementToDict(node)
        self._name_ = node.nodeName
        
    @property
    def name(self) -> str:
        return self._name_
    
    @property
    def data(self)->dict:
        return self._data_
    
    @property
    def version(self) -> tuple[int]:
        r"""PrairieView software version as a 4-tuple of ints: (major, minor, micro dot)"""
        return self.__version__
    
    @property
    def versionString(self) -> str:
        r"""PrairieView software version as a string <major>.<minor>.<micro>.<dot>)
        See also self.version property"""
        return ".".join(map(lambda x: f"{x}", self.version))
    
    @property
    def parent(self):
        r"""The parent PVScan object, or None
        """
        return self._parent_
    
    @property
    def attributes(self):
        return self._attributes_
    
    def as_dict(self):
        ret = dict()
        ret.update(self.attributes)
        ret["lasers"] = [laser.attributes for laser in self.lasers]
        
        return DataBag(ret)
    
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = ["System Configuration:"]
        if self._attributes_.items() is not None:
            ret += ["%s = %s" % (i[0], i[1]) for i in self._attributes_.items() if i is not None]
        #ret += ["%s = %s" % (i[0], i[1]) for i in self.__dict__.items()]
        for l in self.lasers:
            ret.append(l.__str__())

        return "\n".join(ret)
        
PVEnvironment = PVSystemConfiguration

class PVStateShard(PVObject): pass # overwritten further below; here needed for PVStateValue

class PVIndexedValue(PVObject): pass
class PVSubIndexedValue(PVObject): pass
class PVSubIndexedValueList(PVObject): pass

class PVStateValue(PVObject):
    r"""Introduced in PrarieView v5.5 or later.
        A PVStateValue has:
        'key': str -> mandatory
        'value' str, number, OR list of PVIndexedValues, OR list of PVSubIndexedValueList
        
        A PVIndexedValue has:
        'value': str, int -> mandatory
        'index': str, int -> mandatory
        'description': str -> optional
        
        A PVSubIndexedValueList has:
        'index': str, int -> mandatory
        'value': a list of PVSubIndexedValue objects -> mandatory
        
        A PVSubIndexedValue has:
        'subindex': str, int -> mandatory
        'value': str, int -> mandatory
        'description': str -> optional
        
    """
    def __init__(self, node, parent):
        if not isinstance(parent, PVStateShard):
            raise TypeError("Parent of a PVStateValue can only be None or a PVStateShard object")
        
        super().__init__()
        self._parent_ = parent
                
        attributes = xmlutils.attributesToDict(node)
        # print(f"{self.__class__.__name__}.__init__: attributes = {attributes}")
        
        self._attributes_ = DataBag()
        for k,v in attributes.items():
            try:
                v = eval(v)
            except:
                pass
        
            self._attributes_[k] = v
        
        ivalueNodes = xmlutils.getChildren(node, tagName="IndexedValue")
        
        self._indexedValues_ = list(map(lambda n: PVIndexedValue(n, self), ivalueNodes))
        
        subIvaluesNodes = xmlutils.getChildren(node, tagName ="SubindexedValues")
        
        self._subIndexedValuesLists_ = list(map(lambda n: PVSubIndexedValueList(n, self), subIvaluesNodes))
        
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = [f"{self.__class__.__name__}:\n"]
        ret += ["  %s = %s\n" % (i[0], i[1]) for i in self._attributes_.items()]
        if len(self.indexedValues):
            ret += ["   IndexedValues:"]
            ret += list(map(lambda v: f"{   v}", self.indexedValues))
            
        if len(self.subIndexedValuesLists):
            ret += ["   SubindexedValues:"]
            ret += list(map(lambda v: f"{   v}", self.subIndexedValuesLists))
            
        ret += ["\n"]
        return "".join(ret)
    
    @property
    def parent(self):
        return self._parent_
    
    @property
    def key(self):
        return self.attributes.key

    @property
    def value(self):
        if "value" in self.attributes:
            return self.attributes.value
        
        elif len(self.indexedValues):
            return self.indexedValues
        
        elif len(self.subIndexedValuesLists):
            return self.subIndexedValuesLists
        
    def getIndexedValue(self, index):
        """Look up Indexed Values by index"""
        ivalues = tuple(filter(lambda v: v.index == index, self.indexedValues))
        if len(ivalues):
            return ivalues[0]
        else:
            raise IndexError(f"This {self.__class__.__name__} object does not contain an IndexedValue with index {index}")
        
    def getSubIndexedValueList(self, index):
        svalues = tuple(filter(lambda s: s.index == index, self.subIndexedValuesLists))
        
        if len(svalues):
            return svalues[0]
        else:
            raise IndexError(f"This {self.__class__.__name__} object does not contain a SubIndexedValueList with index {index}")
        
    @property
    def parent(self):
        return self._parent_
    
    @property
    def keys(self):
        yield from map(lambda s: s.index, self.values)
    
    @property
    def values(self):
        yield from self.indexedValues + self.subIndexedValuesLists
        
    @property
    def items(self):
        yield from map(lambda v: (v.index, v), self.values)
    
    def get(self, item, default=MISSING):
        try:
            return self[item]
        except KeyError as e:
            if default is MISSING:
                raise
            return default
        
    def __contains__(self, item):
        return item in tuple(self.keys)

    def __getitem__(self, item):
        if item not in self.keys:
            raise KeyError(f"Index {item} not found in {type(self.parent).__name__} object {self.key}")
        return tuple(filter(lambda v: v.index == item, self.indexedValues + self.subIndexedValuesLists))[0]
        
    def __len__(self):
        return len(tuple(self.keys))
    
    @property
    def attributes(self) -> DataBag:
        return self._attributes_
    
    @property
    def indexedValues(self) -> list:
        return self._indexedValues_
    
    @property
    def subIndexedValuesLists(self) -> list:
        return self._subIndexedValuesLists_
        
class PVIndexedValue(PVObject):
    def __init__(self, node, parent:PVStateValue):
        if not isinstance(parent, PVStateValue):
            raise TypeError("parent must be a PVStateValue")
        
        super().__init__()
        self._parent_ = parent
        
        attributes = xmlutils.attributesToDict(node)
        
        self._attributes_ = DataBag()
        for k,v in attributes.items():
            try:
                v = eval(v)
            except:
                pass
        
            self._attributes_[k] = v
        
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = [f" {self.__class__.__name__}:\n"]
        ret += ["  %s = %s\n" % (i[0], i[1]) for i in self._attributes_.items()]
        ret += ["\n"]
        return "".join(ret)
    
    @property
    def parent(self):
        return self._parent_

    @property
    def attributes(self) -> DataBag:
        return self._attributes_
    
    @property
    def key(self):
        return self.attributes.key
    
    @property
    def index(self):
        return self.attributes.index
    
    @property
    def value(self):
        return self.attributes.value
    
    @property
    def description(self):
        return self.attributes.get("description", None)
    
class PVSubIndexedValue(PVObject):
    def __init__(self, node, parent:PVSubIndexedValueList):
        if not isinstance(parent, PVSubIndexedValueList):
            raise TypeError("parent must be a PVSubIndexedValueList")
        
        super().__init__()
        self._parent_ = parent
        
        attributes = xmlutils.attributesToDict(node)
        
        self._attributes_ = DataBag()
        for k,v in attributes.items():
            try:
                v = eval(v)
            except:
                pass
        
            self._attributes_[k] = v

    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = [f" {self.__class__.__name__}:\n"]
        ret += ["  %s = %s\n" % (i[0], i[1]) for i in self._attributes_.items()]
        ret += ["\n"]
        return "".join(ret)
    
    @property
    def parent(self):
        return self._parent_

    @property
    def subindex(self):
        return self.attributes.subindex
    
    @property
    def value(self):
        return self.attributes.value
    
    @property
    def description(self):
        return self.attributes.get("description", None)
    
    @property
    def attributes(self) -> DataBag:
        return self._attributes_
    
class PVSubIndexedValueList(PVObject):
    def __init__(self, node, parent:PVStateValue):
        if not isinstance(parent, PVStateValue):
            raise TypeError("parent must be a PVStateValue")
        
        super().__init__()
        self._parent_ = parent
        
        attributes = xmlutils.attributesToDict(node)
        
        self._attributes_ = DataBag()
        for k,v in attributes.items():
            try:
                v = eval(v)
            except:
                pass
        
            self._attributes_[k] = v
        
        sIvalues = xmlutils.getChildren(node, tagName="SubindexedValue")
        
        self._subIndexedValues_ = list(map(lambda n: PVSubIndexedValue(n, self), sIvalues))
        
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = [f" {self.__class__.__name__}:\n"]
        ret += ["  %s = %s\n" % (i[0], i[1]) for i in self._attributes_.items()]
        if len(self.value):
            ret += ["   SubIndexedValues:"]
            ret += list(map(lambda v: f"   {v}", self.value))
            
        ret += ["\n"]
        return "".join(ret)

    @property
    def attributes(self) -> DataBag:
        return self._attributes_
    
    @property
    def index(self):
        return self.attributes.index
    
    @property
    def value(self) -> list:
        return self._subIndexedValues_
    
    @property
    def values(self):
        yield from self._subIndexedValues_
        
    @property
    def keys(self):
        yield from map(lambda v: v.subindex, self._subIndexedValues_)
        
    @property
    def items(self):
        yield from map(lambda v: (v.subindex, v), self._subIndexedValues_)
        
    def get(self, item, default=MISSING):
        try:
            return self[item]
        except KeyError as e:
            if default is MISSING:
                raise
            return default
        
    def __contains__(self, item):
        return item in tuple(self.keys)

    def __getitem__(self, item):
        if item not in self.keys:
            raise KeyError(f"Subindex {item} not found")
        return tuple(filter(lambda x: x.subindex == item, self._subIndexedValues_))[0]
    
    def __len__(self):
        return len(tuple(self.keys))
    
    def getSubIndexedValue(self, subindex):
        values = tuple(filter(lambda v: v.subindex == subindex, self.value))
        if len(values):
            return values[0]
        else:
            raise IndexError(f"This {self.__class__.__name__} object does not contain a SubIndexedValue with subimndex {subindex}")
    
    
class PVFrame(PVObject): pass # needed for below; overwritten later

class PVStateShard(PVObject):
    # NOTE: 2025-04-03 10:34:49
    # as of v5.5 at least, each Frame has a PVStateShard!, 
    def __init__(self, node, parent:PVObject):
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "PVStateShard":
            raise ValueError("Expecting an element node 'PVStateShard")
        
        if not isinstance(parent, PVObject):
            raise TypeError("Parent of a PVStateShard can only be None or a PVObject object")
        
        super().__init__()
        self._parent_ = parent

        self._state_values_ = list() # NOTE: 2025-04-03 09:53:22 new, in v >= 5.5
        
        self._attributes_ = DataBag(dict())
        
        # print(f"{self.__class__.__name__}.__init__ attributes: {dict(node.attributes)}")
            
        if node.attributes is not None:
            for k, v in node.attributes.items():
                try:
                    val=eval(v)
                except:
                    val = v
                    
                self._attributes_[k] = val
                    
                    
        if self.versionString >= "5.5":
            stateValueNodes = xmlutils.getChildren(node, tagName="PVStateValue")
        else:
            stateValueNodes = xmlutils.getChildren(node, tagName="Key")

        self._state_values_[:] = list(map(lambda node: PVStateValue(node, parent=self), stateValueNodes))
                
    @property
    def version(self):
        return self.parent.version
    
    @property
    def versionString(self):
        return self.parent.versionString

    @property
    def parent(self):
        r"""The parent PVObject
        """
        return self._parent_
    
    @property
    def states(self)->list:
        return self._state_values_
    
    @property
    def keys(self):
        yield from map(lambda s: s.key, self.states)
        
    @property
    def values(self):
        yield from self.states
    
    @property
    def items(self):
        yield from map(lambda s: (s.key, s), self.values) 
        
    def get(self, item, default=MISSING):
        try:
            return self[item]
        except KeyError as e:
            if default is MISSING:
                raise
            return default
        
    def __contains__(self, item):
        return item in tuple(self.keys)
        
    def __getitem__(self, item):
        if item not in tuple(self.keys):
            raise KeyError(f"Index {item} not found")
        return tuple(filter(lambda s: s.key == item, self.values))[0]
    
    def __len__(self):
        return len(tuple(self.keys))
    
    @property
    def attributes(self):
        return self._attributes_
    
    def getStateValue(self, key:str):
        states = tuple(filter(lambda s: s.attributes.get("key", None) == key and s.attributes.get("value", None) is not None, self.states))
        if len(states):
            return states[0].attributes.value
        
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = [f"{self.__class__.__name__}:\n"]
        ret += ["  %s = %s\n" % (i[0], i[1]) for i in self._attributes_.items()]
        ret += ["  State values:\n"]
        ret += list(map(lambda s: f"   {s}", self.values))
        
        return "".join(ret)
    
class PVSequence(PVObject): pass #needed for PVFrame below

# NOTE: 2017-08-07 12:55:53
# the "Files" element node point to file names of the linescan data (or whatever
# the sequence contains, PLUS the source which is a 2D raster; now, it seems to 
# me that the "source" contains the whole 2D raster data including all channels, 
# it is just repeatedly saved under another name; hmmm...
# also, for each frame in the same sequence (for linescans, at least) the "source"
# is the same (i.e the system does NOT acquire a new raster scan before each 
# linescan frame repetition within the same sequence -- for a good reason; why then
# having the same data saved n-teen times ???)
# )
#
#NOTE: 2017-08-07 13:08:59
# CORRECTION:
# I'm using vigra.readVolume, which is when fed file name as argument and vigraimpex
# DEDUCES that the file is  part of a volume when file name follows a pattern
# e.g.: 
# LineScan-02082017-0637-000-Cycle00001_Ch1Source.tif
# LineScan-02082017-0637-000-Cycle00001_Ch2Source.tif 
# LineScan-02082017-0637-000-Cycle00001_Ch3Source.tif,
# hence vigraimpex deduces that all three are to be read as a volume.
# That is OK, albeit unexpected; the linescans are not subject to this behavior 
# because their filenames break the pattern (I guess it is the common "unique" 
# suffix "000001" after the last underscore, thatg breaks it):
# LineScan-02082017-0637-000_Cycle00001_CurrentSettings_Ch1_000001.tif
# LineScan-02082017-0637-000_Cycle00001_CurrentSettings_Ch2_000001.tif
# LineScan-02082017-0637-000_Cycle00001_CurrentSettings_Ch3_000001.tif
#
# From vigra.readVolume() docstring:
#
# If the volume is stored in a by-slice manner (e.g. one file per
# z-slice), the 'filename' can refer to an arbitrary image from the set.
# readVolume() then assumes that the slices are enumerated like::
#
# name_base+[0-9]+name_ext
#
# where name_base, the index, and name_ext
# are determined automatically. All slice files with the same name base
# and extension are considered part of the same volume. Slice numbers
# must be non-negative, but can otherwise start anywhere and need not
# be successive. Slices will be read in ascending numerical (not
# lexicographic) order. All slices must have the same size.
#
#
# The other problem nevertheless still stands: with each frame in the sequence,
# PV saves the same 2d raster data as "cyclexx_chYsource..."
# which means I can get away with reading the source for the first frame only, in 
# a linescan sequence
#
#NOTE: 2017-08-07 13:48:03
# it looks like only PVSequence of type Linescan make use of "source" image files
# (as in 2D raster scans); for a Zseries or a Single image, there is no "source"
# attribute, whuch somewhat simplifies things.
#
#NOTE: 2017-08-07 13:49:49
# the behavior of vigraimpex towards file names that are paret of a sequence is quite handy
# with ZSeries also, as it can be used to load the entire ZSeries data for one channel
# into a single VigraArray
class PVFrame(PVObject):
    def __init__(self, node, index:int, parent:PVSequence):
        r"""PVFrame constructor:
        node: xmlutils.xml.dom.Node with type ELEMENT_NODE
        index: int index of the frame in the parent sequence; must be >= 0
            Also this shuldbe uniue among all the frames in a sequence (CAUTION: this is NOT enforced)
        parent: a PVSequence object
        
        """
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "Frame":
            raise ValueError("Expecting an element node named 'Frame'")
        
        super().__init__()
        self._parent_ = None
        
        if isinstance(parent, PVSequence):
            self._parent_ = parent
            
        else:
            raise TypeError("Parent of a PVFrame can only be a PVSequence")
        
        if not isinstance(index, int) or index < 0:
            raise ValueError(f"Invalid frame index specified: {index}; must be >= 0")
        
        self._index_ = index
        
        if node.attributes is not None:
            self._attributes_ = DataBag(xmlutils.attributesToDict(node))
        else:
            self._attributes_ = DataBag(dict())
            
        fileNodes = xmlutils.getChildren(node, tagName = "File")
            
        self._files_ = list(map(lambda n: DataBag(xmlutils.attributesToDict(n)), fileNodes))
        
        extraParamNodes = xmlutils.getChildren(node, tagName="ExtraParameters")
        
        self.ExtraParameters = list(map(lambda n: DataBag(xmlutils.attributesToDict(n)), extraParamNodes))

        stateShardNodes = tuple(xmlutils.getChildren(node, tagName="PVStateShard"))
        if len(stateShardNodes):
            self._stateshard_ = PVStateShard(stateShardNodes[0], self)
        
        self._mergeChannelsOnOutput_ = False
        
    @property
    def version(self):
        return self.parent.version
    
    @property
    def versionString(self):
        return self.parent.versionString
    
    @property
    def index(self)->int:
        return self._index_
        
    @property
    def parent(self):
        r"""The parent PVSequence object, or None
        """
        return self._parent_
    
    @parent.setter
    def parent(self, val):
        if isinstance(val, (type(None), PVSequence)):
            self._parent_ = val
            
        else:
            raise TypeError("Parent of a PVFrame can only be None or a PVSequence object")
        
    @property
    def attributes(self):
        return self._attributes_
        
    @property
    def channels(self):
        r"""Returns the number of channels
        
        To obtain the channel data use "files" property.
        """
        return len(self._files_)
    
    @property
    def files(self):
        return self._files_
    
    @property
    def state(self):
        return self._stateshard_
    
    @property
    def multiBandOutput(self):
        r"""If True, the () operator reads this frame's files as a multiband image.
        This requires that each file corresponds to one channel and that all files 
        have a channel axis. Only applies when there are between 2 and 4 files per frame.
        """
        return self._mergeChannelsOnOutput_
    
    @multiBandOutput.setter
    def multiBandOutput(self, val):
        r"""Permanently sets the state of the multiBandOutput property to val.
        
        Parameters:
        "val: boolean
        """
        self._mergeChannelsOnOutput_ = val
    
    def mergeChannels(self, val=True, filepath=None):
        r"""Coerce reading the files as a multiband image.
        
        The self.multiBandOutput property is temporarily set to True, then 
        reverted to its previous value after the image files were read.
        
        Keyword paraneters:
        ==================
        val: boolean => temporarily sets merging of channel output to given value
            optional, default is True

        filepath: str; optional, default is None; when given, it prepends the value
            to the image file names to generate absolute path names to the image 
            files (and thus overrides any path prefix taken from the parent PVSequence)
        
        """
        v = self._mergeChannelsOnOutput_
        self._mergeChannelsOnOutput_= True
        try:
            data = self.__call__(filepath=filepath)
        except Exception as e:
            self._mergeChannelsOnOutput_ = v
            raise e
        
        self._mergeChannelsOnOutput_ = v
        
        return data
    
    def __call__(self, filepath:typing.Optional[typing.Union[str, pathlib.Path]]=None) -> tuple:
        r"""Reads the specified files and returns a vigra array corresponding to
        the image files that compose the frame.
        
        Keyword parameter:
        ==================
        
        filepath = str or None (default); when given, the image filenames
        will be prepended with the value of path to create absolute file names.
        
        This value overrides any value from the parent PVSequence (when the latter
        is not None).
        
        Returns:
        ========
        A tuple (frame data, scene data), where:
        
        • frame data: contains the image data associated with the frame; the data
            is either a sequence of VigraArray (one per channel) or a single
            multi-channel VigraArray (if __mergeChannelsOnOutput__ is true)
        
        • scene data: for line scans only, this contains the image data associated
            with the "Scene" or context where the frame line scan image data was
            acquired.
        
            In all other PVScan types this is None (the "scene" or context data
            is the frame-associated image itself)
        
        """
        
        #metadata to be retrieved from the associated PVStateShard
        #=================================
        #Some of these parameters when present, are passed to PictArray constructor
        #(see datatypes.PictArray) and this function will return a PictArray instead
        #of a plain VigraArray.
        
        #name: str
        
        #description: str
        
        #axistags: a vigra.AxisTags object, or an array of vigra.AxisInfo objects;
            #this argument is used to supply calibration data for the axis (see 
            #NOTE 2, below)
        
        #filesource: str = fully qualified file name of the image data file
            #used in the construction of this object

        #datetime (datetime.datetime object) -- typically, the date & time when
            #this PictArray object was created
            
        #filedatetime (datetime.datetime object) -- the date & time when the
            #file source was created (i.e. date & time of the recording of the
            #underlying data array)
            
        
        #NOTE 1) there can be more than one file per frame (e.g. several channels)
        
        #NOTE 2) normally each frame is saved as a tuple of TIFF files (one for 
                # each channel); when read through the vigra impex library, the 
                # resulting VigraArray data will have default axistags added:
                # "x, y, c". 
                
                # In practice, the first two axes depend on the actual scan mode:
                
                #* in linescan mode, the first two axes are respectively, "space"
                # and "time" (because a linescan frame is composed of a series of 
                # 1D scans repeated for the duration of the frame); therefore the
                # second axis needs changing from its default, to a Time axis
                
                # This happens only when other axis calibration information
                # is also provided so that the function returns a PictArray object.
                
                # In the absence of such information, the function returns a 
                # "plain" VigraArray with default axistags as assigned by vigra 
                # impex library.
                
                #* in TSeries and ZSeries, each frame is raster scan, acquired
                # repeatedly at the same focal point (TSeries) or at different 
                # focal points (ZSeries), or "stacks". Here, the first two axes 
                # are (almost always?) space (e.g. "x", "y") so they don't need
                # any tweaks
                
                #* can a TSeries contain time-varying ZSeries? 
                
                # When files are read by this function, PVFrame has no information
                # about the axis semantic in the image files; this information is
                # normally stored in a separate data structure (for PrairieView it 
                # is the PVStateShard associated with each PVFrame) which is 
                # available as an instance attribute to the PVFrame object.
        
        #NOTE 3) calling this function directly will only load the files pertaining
                # to this individual frame
            
                # if the parent Sequence has more than one frame, use the parent 
                # Sequence __call__()  function to load the ENTIRE data series as a 
                # N-dimensional data "volume" (or "time series").
                # 
                # This happens when PVSequence is a TSeries or ZSeries
                #
                # see PVSequence.__call__() for details
            
                # 2) if the parent Sequence has only one frame (this one) AND there
                # are more than one sequence per scan, then use the PVScan.__call()__
                # of the parent of the sequence to load the entire data set
                #
                # This happens when PVSequence is a Linescan
            
        # grab the files in the frame
        # load these files individually, so that we do not end up reading the 
        # whole data (hyper-)volume, but just the files pertaining to this frame
        # (hence we do not pass asVolume=True to loadImageFile function)
        
        # STEP 1: read metadata
        mdata = self.metadata()
        
        # STEP 2: set up file names
        if filepath is None:
            if self.parent is not None:
                filepath = self.parent.filepath
        
        # STEP 3: set up vigra arrays and their axes
        frameData = list() # will contain vigra arrays for each scans frame, to be concatenated
        
        sourceData = list() # will contnain vigra arrays for each source frame, to be concatenated
        
        #channelNames = (f["channelName"] for f in self.files)
        
        # print(f"{self.__class__.__name__}.__call__")
        for k in range(len(mdata["files"])):
            fileName = self.files[k]['filename']
            # print(f"\treading {fileName}")
            # NOTE: 2022-01-06 00:10:42
            # fdata: frame data
            # sdata: source data
            if isinstance(filepath, str):
                filepath = pathlib.Path(filepath)
                
            if isinstance(filepath, pathlib.Path):
                fdata = pio.loadImageFile(filepath.parent / fileName)
                # fdata = pio.loadImageFile(os.path.join(filepath, fileName))
                # fdata = pio.loadImageFile(os.path.join(filepath, self.files[k]["filename"]))
            
            else:
                fdata = pio.loadImageFile(fileName)
                # fdata = pio.loadImageFile(self.files[k]["filename"])
                
            if fdata.ndim == 2 and fdata.channelIndex == fdata.ndim:
                fdata.insertChannelAxis() # make sure there is a channel axis
                
            # NOTE: 2021-10-27 22:06:14
            # Now `fdata` has default axistags ('x', 'y', 'c') as per vigra's
            # default behaviour

            # NOTE: 2021-10-26 10:34:59 NEW AXIS CALIBRATION FRAMEWORK
            # AxisCalibrationData pertains to a single axis
            # AxesCalibration collects several AxisCalibrationData objects (one 
            # for each axis in the vigra array)
            #
            # AxesCalibration c'tor with AxisInfo as parameter assigns default 
            # values to the array's axistags
            #
            
            # NOTE: 2021-10-27 21:59:09
            # Below, we calibrate axes individually using an AxisCalibrationData
            # object for each axis
            # 
            # AxisCalibrationData objects here are just used to embed calibration
            # strings in the `description` attribute for the corresponding
            # AxisInfo
                
            # NOTE: 2018-06-03 22:15:10
            # axis_0_info is the AxisInfo object for the 1st (spatial) dimension (axis)
            fdata_axis_0_info = fdata.axistags[0]
            
            # NOTE: 2021-10-26 15:48:42
            
            # fdata_axis_0_cal  = AxisCalibrationData(fdata_axis_0_info)
            fdata_axis_0_cal  = AxisCalibrationData.new(fdata_axis_0_info)
            print(f"{self.__class__.__name__}.__call__: calibration -> {fdata_axis_0_cal.type}")
            if self.versionString < "5.5":
                fdata_axis_0_cal.resolution = float(self.state["micronsPerPixel_XAxis"].value)
            else:
                # ATTENTION: 2025-04-04 15:07:52
                # axes resolutions are ALL in the state shard at PVScan level,  
                # NOT in the frame's stateshard, which contain frame-specific information
                # such as gain & laser power, ONLY WHEN APPROPRIATE (e.g. in a Z series)
                # 
                state = self.parent.parent.state
                        
                # print(f"{self.__class__.__name__}.__call__: query scales for {fdata_axis_0_info} - state keys: {tuple(state.keys)}")
                if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
                    fdata_axis_0_cal.resolution = float(state["micronsPerPixel"]["XAxis"].value)
                    fdata_axis_0_cal.units = pq.um
                else:
                    scipywarn(f"Cannot get the μm / pixel for axis {print_styled(f'{fdata_axis_0_info}', 'yellow')} in frame {print_styled(f'frame {self.index}', 'yellow')}")
            
            # embed calibration string into axis_0_info's description
            fdata_axis_0_info = fdata_axis_0_cal.calibrateAxis(fdata_axis_0_info)
            
            
            # NOTE: 2018-06-03 22:15:54
            # axis_1_info is the AxisInfo objects for the 2nd dimension (axis);
            # the type of this axis (spatial or temporal) depends on the type of 
            # PVSequence: for a Linescan, the this axis is a temporal one
            #
            # By default, vigra impex sets this axis to be a Space type ('y')
            # so we only modify this default behaviour when PVSequence is of 
            # Linescan type
            if self.parent is not None and self.parent.type == PVSequenceType.Linescan:
                fdata_axis_1_info = vigra.AxisInfo(key="t", 
                                             typeFlags=vigra.AxisType.Time, 
                                             resolution = self.state.attributes["scanlinePeriod"])
                
                fdata_axis_1_cal  = AxisCalibrationData.new(fdata_axis_1_info)
                fdata_axis_1_cal.units = pq.s
                
            else:
                fdata_axis_1_info = fdata.axistags[1] # by default vigra behaviour is Space 
                
                fdata_axis_1_cal = AxisCalibrationData.new(fdata_axis_1_info)
                if self.versionString < "5.5":
                    fdata_axis_1_cal.resolution = float(self.state["micronsPerPixel_YAxis"].value)
                else:
                    # NOTE: see ATTENTION: 2025-04-04 15:07:52
                    state = self.parent.parent.state
                    # if self.index == 0:
                    #     state = self.parent.parent.state
                    # else:
                    #     state = self.state
                    # if not isinstance(state, PVStateShard) or len(state) == 0 or "micronsPerPixel" not in state:
                    #     parent = self.parent
                    #     while len(self.state) == 0  and isinstance(parent, PVObject):
                    #         state = parent.state
                    #         if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
                    #             break
                    #         parent = parent.parent
                    # print(f"{self.__class__.__name__}.__call__: query scales for {fdata_axis_1_info} - state keys: {tuple(state.keys)}")
                    # state = self.state if len(self.state) else self.parent.parent.state
                    if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
                        fdata_axis_1_cal.resolution = float(state["micronsPerPixel"]["YAxis"].value)
                        fdata_axis_1_cal.units = pq.um
                    else:
                        scipywarn(f"Cannot get the μm / pixel for axis {print_styled(f'{fdata_axis_1_info}', 'yellow')} in frame {print_styled(f'frame {self.index}', 'yellow')}")
                
            # embed calibration string into axis_1_info's description
            fdata_axis_1_info = fdata_axis_1_cal.calibrateAxis(fdata_axis_1_info)
            
            # NOTE: 2018-06-03 22:16:26
            # axis_2_info is the AxisInfo object for 3rd dimension
            # Since all individual images saved by PrairieView are 2D, 
            # then the third axis is a Channels axis (by default vigra impex
            # assigns this as 'c' even if is singleton)
            #
            
            if fdata.channelIndex == fdata.ndim: # channel axis is virtual
                # NOTE: 2018-08-01 16:43:58
                # make sure there IS a channel axis
                fdata_axis_2_info = vigra.AxisInfo.c 
                
            else:
                fdata_axis_2_info = fdata.axistags["c"]
                
            fdata_axis_2_info.description = self.files[k]["channelName"]
            
            fdata_axis_2_cal = AxisCalibrationData.new(fdata_axis_2_info)
            fdata_axis_2_cal.addChannelCalibration(ChannelCalibrationData(index = self.files[k]["channel"],
                                                                          name=self.files[k]["channelName"]),
                                                   name=self.files[k]["channelName"],
                                                   index = self.files[k]["channel"])
            
            #fdata_axis_2_cal.setChannelName(0, self.files[k]["channelName"]) # also adds channel calibration to the channel axis calibration
                                        
            # embed calibration string into axis_2_info's description
            fdata_axis_2_info = fdata_axis_2_cal.calibrateAxis(fdata_axis_2_info)
            
            # construct a new VigraArray using fdata and new axistags initialized
            # from the calibrated AxisInfo objects
            newaxistags = vigra.AxisTags(fdata_axis_0_info, fdata_axis_1_info, fdata_axis_2_info)
            frame = vigra.VigraArray(fdata, axistags=newaxistags)
            
            frameData.append(frame)
        
            # NOTE: 2021-10-27 22:18:41
            # the source data is set up using the same blueprint as for frame data
            # ideally we should end up with one source data frame for each scans data frame
            if "source" in self.files[k] and all(self.files[k]["source"]):
                sourceFileName = self.files[k]["source"]
                # print(f"\treading source {sourceFileName}")
                if filepath is not None:
                    sdata = pio.loadImageFile(os.path.join(filepath, sourceFileName))
                    # sdata = pio.loadImageFile(os.path.join(filepath, self.files[k]["source"]))
                    
                else:
                    sdata = pio.loadImageFile(sourceFileName)
                    # sdata = pio.loadImageFile(self.files[k]["source"])
                    
                if sdata.ndim == 2 and sdata.channelIndex == sdata.ndim:
                    sdata.insertChannelAxis() # make sure there is a channel axis
                    
                sdata_axis_0_info = sdata.axistags[0]
                sdata_axis_0_cal = AxisCalibrationData.new(sdata_axis_0_info)
                if self.versionString < "5.5":
                    sdata_axis_0_cal.resolution = float(self.state["micronsPerPixel_XAxis"].value)
                else:
                    # NOTE: see ATTENTION: 2025-04-04 15:07:52
                    state = self.parent.parent.state
#                     if self.index == 0:
#                         state = self.parent.parent.state
#                     else:
#                         state = self.state
#                     
#                     if not isinstance(state, PVStateShard) or len(state) == 0:
#                         parent = self.parent
#                         while len(self.state) == 0  and isinstance(parent, PVObject):
#                             state = parent.state
#                             if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
#                                 break
#                             parent = parent.parent
                            
                    # print(f"{self.__class__.__name__}.__call__: query scales for SOURCE {sdata_axis_0_info} - state keys: {tuple(state.keys)}")
                    if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
                        sdata_axis_0_cal.resolution = float(state["micronsPerPixel"]["XAxis"].value)
                        sdata_axis_0_cal.units = pq.um
                    else:
                        scipywarn(f"Cannot get the μm / pixel for axis {print_styled(f'{sdata_axis_0_info}', 'yellow')} in frame {print_styled(f'frame {self.index}', 'yellow')}")
                        
                sdata_axis_0_info = sdata_axis_0_cal.calibrateAxis(sdata_axis_0_info)
                
                sdata_axis_1_info = sdata.axistags[1]
                sdata_axis_1_cal = AxisCalibrationData.new(sdata_axis_1_info)
                if self.versionString < "5.5":
                    sdata_axis_1_cal.resolution=float(self.state["micronsPerPixel_YAxis"].value)
                else:
                    # NOTE: see ATTENTION: 2025-04-04 15:07:52
                    state = self.parent.parent.state
#                     if self.index == 0:
#                         state = self.parent.parent.state
#                     else:
#                         state = self.state
#                         
#                     if not isinstance(state, PVStateShard) or len(state) == 0:
#                         parent = self.parent
#                         while len(self.state) == 0  and isinstance(parent, PVObject):
#                             state = parent.state
#                             if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
#                                 break
#                             parent = parent.parent
                            
                    # print(f"{self.__class__.__name__}.__call__: query scales for SOURCE {sdata_axis_1_info} - state keys: {tuple(state.keys)}")
                    if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
                        sdata_axis_1_cal.resolution=float(state["micronsPerPixel"]["YAxis"].value)
                        sdata_axis_1_cal.units = pq.um
                    else:
                        scipywarn(f"Cannot get the μm / pixel for axis {print_styled(f'{sdata_axis_1_info}', 'yellow')} in frame {print_styled(f'frame {self.index}', 'yellow')}")
                sdata_axis_1_info = sdata_axis_1_cal.calibrateAxis(sdata_axis_1_info)
                
                if sdata.channelIndex == sdata.ndim:
                    sdata_axis_2_info = vigra.AxisInfo.c
                else:
                    sdata_axis_2_info = sdata.axistags["c"]
                
                sdata_axis_2_cal = AxisCalibrationData.new(sdata_axis_2_info)
                sdata_axis_2_cal.addChannelCalibration(ChannelCalibrationData(index = self.files[k]["channel"],
                                                                          name=self.files[k]["channelName"]),
                                                        name = self.files[k]["channelName"],
                                                        index = self.files[k]["channel"])

                sdata_axis_2_cal = sdata_axis_2_cal.calibrateAxis(sdata_axis_2_info)
                
                newaxistags = vigra.AxisTags(sdata_axis_0_info, sdata_axis_1_info, sdata_axis_2_info)
                source = vigra.VigraArray(sdata, axistags=newaxistags)
                
                sourceData.append(source)
                
        if len(sourceData) == 0:
            sourceData = None
            
        # STEP 4: optionally merge into multi-band arrays if __mergeChannelsOnOutput__
        # then return frameData and sourceData
            
        if len(self.files) > 1 and len(self.files) <= 4:
            # this could be returned as a multiband (multichannel) array 
            # if so requested
            
            # NOTE: 2017-11-06 19:40:44
            # concatenation will lose the image metadata
            # therefore we need to collect it then pass it back onto the result
            if self._mergeChannelsOnOutput_:
                channels = [int(self.files[k]["channel"]) for k in range(len(self.files))]
                channel_names = [self.files[k]["channelName"] for k in range(len(self.files))]
                
                mergedFrameData = concatenateImages(*frameData, axis="c", allowConcatenationFor=("origin", "resolution"))
                
                merged_channels_axinfo = mergedFrameData.axistags["c"]
                
                merged_channels_axcal = AxesCalibration(merged_channels_axinfo,
                                                        axisname = axisTypeName(merged_channels_axinfo))
                
                for kch, channel in enumerate(channels):
                    merged_channels_axcal.addChannelCalibration(ChannelCalibrationData(name=channel_names[kch],
                                                                                         index=channel),
                                                                  name=channel_names[kch])
                    
                merged_channels_axinfo = merged_channels_axcal.calibrateAxis(merged_channels_axinfo)
                        
                if sourceData is not None:
                    mergedSourceData = concatenateImages(*sourceData, axis="c")
                    
                    merged_source_channel_axinfo = mergedSourceData.axistags["c"]
                    
                    merged_source_channel_axcal = AxesCalibration(merged_source_channel_axinfo,
                                                                    axisname = axisTypeName(merged_source_channel_axinfo))
                    
                    for kch, channel in enumerate(channels):
                        merged_source_channel_axcal.addChannelCalibration(ChannelCalibrationData(name=channel_names[kch],
                                                                                                    index = channel),
                                                                            name = channel_names[kch])
                        
                    merged_source_channel_axis_ino = merged_source_channel_axcal.calibrateAxis(merged_channels_axinfo)
                        
                else:
                    mergedSourceData = None
                    
                return mergedFrameData, mergedSourceData
                    
        return frameData, sourceData
    
    def metadata(self):
        r"""Returns metadata associated with this frame.
        """
        
        channelIndex = [f["channel"] for f in self.files]
        orderedIndex = np.argsort(channelIndex)
        metadata = dict()
        metadata["frame"] = self.attributes
        metadata["acq"] = self.state.attributes
        metadata["channels"] = self.channels
        metadata["channel_names"] = {int(self.files[k]["channel"]): self.files[k]["channelName"] for k in orderedIndex}
        metadata["files"] = [self.files[k] for k in orderedIndex]
        metadata["type"] = self.__class__.__name__
        
        return DataBag(metadata)
        
        
    def __repr__(self):
        return self.__str__()
        
    def __str__(self):
        ret = [" Frame:\n"]
            
        for k in self._attributes_.keys():
            ret.append("  %s = %s\n" % (k, self._attributes_[k]))
            
        ret.append(" Files:\n")
        for f in self._files_:
            for t in f.keys():
                ret.append("  %s = %s\n" % (t, f[t]))
                
        ret.append(self._stateshard_.__str__())
        
        if self.ExtraParameters is not None:
            ret.append(" Extra Parameters:\n")
            for ep in self.ExtraParameters:
                for i in ep.items():
                    ret.append("  %s = %s\n" % (i[0], i[1]))
            
        return "".join(ret)
        
class PVScan(PVObject): pass # needed for PVSequence below; overwritten further down
# NOTE: 2017-08-03 09:24:20
# TODO: make the instances sortable by cycle number (found in attributes
class PVSequence (PVObject):
    r"""a PVSequence in PVScan experiment file
    """
    def __init__(self, node, parent=PVScan):
        super().__init__()
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "Sequence":
            raise ValueError("Expecting an element node named 'Sequence'")
        
        self._mergeChannelsOnOutput_ = False
        
        self._parent_ = None
        if not isinstance(parent, PVScan):
            raise TypeError("Parent of a PVSequence can only be None or a PVScan object")
        self._parent_ = parent
        
        self._definition_ = None
        self._syncZAxis_ = None
        
        self._attributes_ = DataBag(dict())
        
        if node.attributes is not None:
            for k in node.attributes.values():
                try:
                    val=eval(k.value)
                except:
                    val = k.value
                    
                if k.name == "type": 
                    self._attributes_["sequencetype"] = PVSequenceType[val.split()[0]].value
                else:
                    self._attributes_[k.name] = val
                    
            self._attributes_["sequencetypename"] = PVSequenceType(self._attributes_["sequencetype"]).name
        
        if self._attributes_["sequencetype"] == PVSequenceType.Linescan:
            definitionNodes = tuple(xmlutils.getChildren(node, tagName="PVLinescanDefinition"))
            if len(definitionNodes):
                self._definition_ = PVLinescanDefinition(definitionNodes[0], self)
            syncZAxisNodes = tuple(xmlutils.getChildren(node, tagName = "PVLinescanSynchZ"))
            if len(syncZAxisNodes):
                self._syncZAxis_ = DataBag(xmlutils.attributesToDict(syncZAxisNodes[0]))
            
        else: # TODO / FIXME code for other sequence tyes
            self._definition_ = None
            self._syncZAxis_ = None
                
        frameNodes = xmlutils.getChildren(node, tagName="Frame")
        self.frames = list(map(lambda n: PVFrame(n[1], n[0], self), enumerate(frameNodes)))
        
    def __len__(self):
        return len(self.frames)
    
    def __call__(self, filepath=None):
        r"""Load the images from the file(s) define in its frames attribute
        
        If there is only one frame, then it will load that data and return it
        as a (possibly, multi-channel or "multi-band" ) vigra array
        
        Returns None if no frames are defined.
        
        Keyword parameter:
        ==================
        
        filepath = str or None; optional, default is None; when given, the image filenames
        will be prepended with the value of path to create absolute file names.
        
        This value overrides any value from the parent PVScan (when the latter
        is not None).
        
        """
        #from os.path import join
        
        if len(self.frames) == 0:
            return
        
        
        if filepath is None:
            filepath = self.filepath # may be None
        
        # NOTE: 2017-10-18 22:46:46
        # a sequence has more than one frame when its type is
        # TSeries (Timed Element)
        # ZSeries 
        #
        # Linescan type lissajous
        #
        # a sequence has ONE frame when it is:
        # Linescan - staightline, freehand, spiral
        # Single
        # Point Scan
        
        
        # HOWEVER:
        # Linescan can have MORE THAN ONE FRAME (i.e. two -- can it have more?) 
        # in the case of:
        # lissajous
        
        # NOTE: 2017-10-18 22:41:02
        # technically, all frames in the sequence should have the same axistags,
        # shape and importantly, contain image data with the same number of channels
        # (whether it is returned as multiband or not)
        
        # unpack the frameData:
        
        # if there is only one frame then this should return either:
        # either n single-channel (single-band) images, 
        #   where n = number of frames in the sequence
        #
        # or one multi-band image if self._mergeChannelsOnOutput_ is True 
        # (this is propagated to the underlying frame(s)), in which case
        # frame data for each frame is a 3D vigra array!
        
        # channel axis should be on the highest dimension (by convention, but
        # this is NOT guaranteed)
        
        # parse the axistags of the first image in the series; all images in the 
        # first and subsequent frames must have the same axistags
        
        # also, each individual file in the frame is supposed to be a 2D array
        # so concatenation must occur along a NEW AXIS which we must create as
        # a singleton, if it doesn't exist
        
        # for multi-band frame data (i.e, 3D arrays, see above) this will generate
        # a 4D array with a new axis tag
        
        # depending on the type of sequence, the new axis tag needs to be:
        #
        # Linescan, TSeries: time; 
        # ZSeries: z axis
        # Single: not applicable - just unpack the frameData
        # Point: not implemented
        
        # NOTE: 2017-10-23 10:46:11
        # axistags management taken care of by concatenateImages
        
        if self.sequencetype == PVSequenceType.Linescan:
            if self.definition.mode in (PVLinescanMode.straightLine, \
                                        PVLinescanMode.freeHand, \
                                        PVLinescanMode.circle, \
                                        PVLinescanMode.spiral): # one frame per sequence
                # just return the frame data - there should only be one frame
                lsmodename = [i.name for i in PVLinescanMode][[i.value for i in PVLinescanMode].index(self.definition.mode)]
                
                if len(self.frames) > 1:
                    warnings.warn("Expected only one frame in %s linescan mode; got %d instead.\nOnly data from the first frame will be returned" % (lsmodename, len(self.frames)))

                # NOTE: 2017-10-24 23:12:47
                # A linescan sequence is only one of possibly several repetitions
                # of a linescan; each sequence has only one frame, so there is nothing
                # really to concatenate here, but rather at the parent object level 
                # (i.e., in the parent PVScan)
                #
                # therefore the code here works on the assumption that there is
                # ONLY ONE FR10-24 23:12:47
                # A linescan sequence is only one of possibly several repetitions
                # of a linescan; each sequence has only one frame, so there is nothing
                # really to concatenate here, but rather at the parent object level 
                # (i.e., in the parent PVScan)
                #
                # therefore the code here works on the assumption that there is
                # ONLY ONE FRAME in this PVSequence object
                # TODO - FIXME what if there are more than one frame? e.g. lissajous
                # can there ever be 2+ frames per linescan sequence (apart lissajous)?
                
                # NOTE: 2017-10-25 00:23:21:
                # the frames in the linescan sequences also define "source" image files
                # whichAME in this PVSequence object
                # TODO - FIXME what if there are more than one frame? e.g. lissajous
                # can there ever be 2+ frames per linescan sequence (apart lissajous)?
                
                # NOTE: 2017-10-25 00:23:21:
                # the frames in the linescan sequences also define "source" image files
                # which contain a raster scan data of the "scene" where the linescan
                # was defined & acquired; 
                # load these too
            
                # NOTE: 2017-10-27 21:47:29
                # for linescans, the Y axis should be Time !!!
                if self._mergeChannelsOnOutput_:
                    data = self.frames[0].mergeChannels(filepath=filepath) # a tuple of frameData, sourceData, both multiband vigra arrays
                    
                else:
                    data = self.frames[0](filepath=filepath)# a tuple of frameData, sourceData, both lists
                    
                return data
                    
                
            elif self.definition.mode == PVLinescanMode.lissajous:  # two frames per sequence
                raise NotImplementedError("parsing lissajous linescan mode not yet implemented")
                # TODO - FIXME figure out what lissajous does an how to parse it
                # in a sensible fashion
                
            else:
                raise ValueError("Unexpected Linescan mode %s" % self.definition.mode)
            
        elif self.sequencetype in (PVSequenceType.TSeries, PVSequenceType.ZSeries): 
            # there are at least one frame per sequence (but at least one)
            # parent PVScan should only have one such sequence
            if self._mergeChannelsOnOutput_:
                data = [f.mergeChannels(filepath=filepath) for f in self.frames]# a tuple of frameData, sourceData
                
                # NOTE: 2017-10-25 00:34:44
                # be mindful that frames __call__() return a TUPLE of
                # frame data and source data; except for Linescan frames, source data
                # is None so we drop this out here
                sources = [d[1] for d in data]
                
                data = [d[0] for d in data]
                
                # NOTE: 2017-10-25 00:51:06 source data is None here
                # so we just return None for it
                
                # each frame has already been concatenated into a
                # multi-band image; what we have to do here is to 
                # create a new time or Z axis accordingly, on the highest
                # dimension, then concatenate along it
                
                #newAxisDim = data[0].ndim
                
                if self.type == PVSequenceType.TSeries:
                    if self.parent.versionString < "5.5":
                        frameTimes = [float(f.state["absoluteTime"].value) for f in self.frames]
                    else:
                        states = list(map(lambda f: f.state if len(f.state) else self.parent.state))
                        frameTimes = list(map(float(s["absoluteTime"].value), states))
                        

                    diffTimes = np.diff(frameTimes) # there will be some jitter

                    framePeriod = float(diffTimes.mean())# * pq.s
                
                    newAxisInfo = vigra.AxisInfo(key="t", 
                                                 typeFlags=vigra.AxisType.Time, 
                                                 resolution=framePeriod, 
                                                 description=axisTypeName(axisTypeFromString("t")))
                    
                    newAxisCal = AxisCalibrationData.new(newAxisInfo)
                    newAxisCal.units = pq.s,
                    newAxisCal.origin = frameTimes[0]
                    newAxisCal.resolution = framePeriod
                    newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                    
                else: # Z series
                    # get the Z axis resolution from the frames state
                    if self.parent.versionString < "5.5":
                        z_pos = list(map(lambda f: float(f.state["positionCurrent_ZAxis"].value), self.frames))
                    else:
                        frameStates = map(lambda f: f.state if len(f.state) else self.parent.state, self.frames)
                        z_pos = list(map(lambda s: float(s["positionCurrent"]["ZAxis"].value), frameStates))
                        
                    z_steps = np.diff(z_pos)
                    
                    if len(z_steps) > 1:
                        if not all(z == z_steps[0] for z in z_steps):
                            raise ValueError("Irregular Z axis sampling is not supported")
                        
                    zres = z_steps[0]
                    
                    newAxisInfo = vigra.AxisInfo(key="z", 
                                                 typeFlags=vigra.AxisType.Space,
                                                 resolution=zres,
                                                 description=axisTypeName(axisTypeFromString("z")))
                    
                    newAxisCal = AxisCalibrationData.new(newAxisInfo)
                    newAxisCal.units = pq.um
                    newAxisCal.origin = z_pos[0]
                    newAxisCal.resolution = zres
                    newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                
                # NOTE: 2018-08-01 17:03:52
                # see NOTE: 2018-08-01 17:04:06
                channelAxisDim = data[0].axistags.channelIndex
                
                if channelAxisDim == data[0].ndim-1:
                    newAxisDim = channelAxisDim
                    
                else:
                    newAxisDim = data[0].ndim
                    
                images = [imgp.insertAxis(img, newAxisInfo, newAxisDim) for img in data]
            
                # NOTE: 2017-10-25 00:51:06 source data is None here
                # so we just return None for it
                return concatenateImages(images, axis=newAxisInfo), None
            
            else: # separate channels
                # for frame κ, data[κ] is the tuple (frame data, src data) if this is a linescan;
                # else, just the tuple (frame data, None)
                data = [f(filepath=filepath) for f in self.frames] 
                
                # NOTE: 2017-10-25 00:34:44
                # be mindful that frames __call__() return a TUPLE of
                # frame data and source data; except for Linescan frames, source data
                # is None
                sources = [d[1] for d in data]
                
                data = [d[0] for d in data]
                
                # each frame outputs a list of single-band images with as many 
                # images per frame as channes were defined in the acquisition)
                
                # importantly, they all should have ndim == 3, with a singleton 
                # channel axis on the highest dimension (2)
                
                # we will have to keep these channels separate, and concatenate
                # along each corresponding channel
                
                # the result will therefore have to be a list of concatenated
                # data (3D); with as many elements as channels;
                
                # these will have ndim=4 (three non-channel axis + one channel
                # axis on the highest dimension)
                
                # the concatenation axis needs to be placed BEFORE the (singleton)
                # channel axis, such that channels are always on the highest dimension
                
                # this should "push" the channel axis to a higher dimension in the 
                # result
                channelAxisDim = data[0][0].axistags.channelIndex
                
                if channelAxisDim == data[0][0].ndim-1: # channel axis on highest dimension
                    newAxisDim = data[0][0].ndim-1 # use the dim immediately below channel axis, for concatenation axis
                    
                else: # either no channel axis, or channel axis is on an inner dimension:
                    # if on an inner dimension we assume there is a good reason for this
                    # do we concatenateon the highest (outer) dimension regardless
                    newAxisDim = data[0][0].ndim # use highest dimension for concatenation axis
                    
                if self.sequencetype == PVSequenceType.TSeries: # Tseries, separate channels
                    if self.parent.versionString < "5.5":
                        frameTimes = list(map(float(f.state["absoluteTime"].value), self.frames))
                    else:
                        states = map(lambda f: f.state if len(f.state) else self.parent.state)
                        frameTimes = list(map(lambda s: float(s["absoluteTime"].value), states))
                    
                    diffTimes = np.diff(frameTimes) # there will be some jitter

                    framePeriod = float(diffTimes.mean())#framePeriods[0]
                
                    newAxisInfo = vigra.AxisInfo(key="t", 
                                                 typeFlags = vigra.AxisType.Time,
                                                 resolution=framePeriod,
                                                 description=axisTypeName(axisTypeFromString("t")))
                    
                    newAxisCal = AxisCalibrationData(units = pq.s, 
                                                     origin = frameTimes[0], 
                                                     resolution = framePeriod,
                                                     name = axisTypeName(newAxisInfo))
                    
                    newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                    
                else: # ZSeries, separate channels
                    # get the Z axis resolution from the frames state
                    if self.parent.versionString < "5.5":
                        z_pos = list(map(lambda f: float(f.state["positionCurrent_ZAxis"].value), self.frames))
                    else:
                        frameStates = map(lambda f: f.state if len(f.state) else self.parent.state, self.frames)
                        z_pos = list(map(lambda s: float(s["positionCurrent"]["ZAxis"][0].value), frameStates))

                    z_steps = np.diff(z_pos)

                    zres = abs(z_steps[0])
                    
                    newAxisInfo = vigra.AxisInfo(key="z", 
                                                 typeFlags=vigra.AxisType.Space,
                                                 resolution=zres,
                                                 description=axisTypeName(axisTypeFromString("z")))
                    
                    newAxisCal = AxisCalibrationData.new(newAxisInfo)
                    newAxisCal.units=pq.um
                    newAxisCal.origin=z_pos[0]
                    newAxisCal.resolution=zres
                    newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                    
                # NOTE: 2018-08-01 17:03:52
                # see NOTE: 2018-08-01 17:04:06
                channelAxisDim = data[0][0].axistags.channelIndex
                
                if channelAxisDim == data[0][0].ndim-1:
                    newAxisDim = channelAxisDim
                    
                else:
                    newAxisDim = data[0][0].ndim
                    
                # NOTE: 2025-04-03 08:57:14
                # return the tuple (frame data, None), where
                # frame data is a sequence of frame image data for each channel,
                # as a 3D VigraArray containing the concatenation of frame images 
                # along the time (for TSeries) or z (for ZSeries) axis; there are
                # as many 3D image arrays as there are channels having been acquired
                return [concatenateImages([insertAxis(data[frame][channel], newAxisInfo, newAxisDim) 
                                                        for frame in range(len(self.frames))], 
                                                        axis=newAxisInfo) 
                                                    for channel in range(len(data[0]))], None
                
        elif self.sequencetype == PVSequenceType.Single:
            # one sequence, one frame
            
            # NOTE: 2017-10-25 00:34:44
            # be mindful that frames __call__() return a TUPLE of
            # frame data and source data; except for Linescan frames, source data
            # is None,so we eliminate it here
                
            if self._mergeChannelsOnOutput_:
                return self.frames[0].mergeChannels() #tuple of frame data & None
                
            else:
                return self.frames[0]() #tuple of frame data & None
        
            
            
        elif self.sequencetype == PVSequenceType.Point: # point scanning
            # this should really result in a 1D array of data. 
            # PrairieView saves (huge) csv files that I still need to understand
            # but also some kind of wrapped TIFFs along them, of similar size
            # (I reckon these might contain the same data as the csv files)
            raise NotImplementedError("Point scan sequence parsing not implemented yet")
            # TODO - FIXME figure out what this does and how to parse it sensibly
            
        else:                           # do nothing here
            raise ValueError("Unknown sequence type %s" % self.sequencetype)
            
        
    def mergeChannels(self, filepath=None):
        r"""Coerce reading the files as a multiband image.
        
        The self.multiBandOutput property is temporarily set to True, then 
        reverted to its previous value after the image files were read.
        
        """
        v = self._mergeChannelsOnOutput_
        self._mergeChannelsOnOutput_= True
        try:
            data = self.__call__(filepath=filepath)
        except Exception as e:
            self._mergeChannelsOnOutput_ = v
            raise e
        self._mergeChannelsOnOutput_ = v
        return data
    
    def metadata(self):
        r"""Returns metadata for this sequence.
        
        This is an ordered dictionary with the following fields:
        attributes    = dictionary with the sequence attributes
        length      = number of frames in the sequence
        definition  = for Linescan sequences this is the actual linescan definition; this is None for other sequence types
        zsync       = Z axis synchronization parameters
        filepath    = path to the data files 
        frames      = a list with metadata for each frame in the sequence
        """
        #metadata = dict()
        metadata = DataBag(mutable_types=True, allow_none=True)
        
        metadata["attributes"]  = self.attributes
        metadata["length"]      = self.length
        
        if isinstance(self.definition, PVLinescanDefinition):
            metadata["definition"]  = self.definition.metadata()
        else:
            metadata["definition"] = None
            
        metadata["zsync"]       = self.zAxisSynchronization
        metadata["file_path"]   = self.filepath
        
        if self.type == PVSequenceType.Linescan:
            if self.definition.mode in (PVLinescanMode.straightLine, \
                                        PVLinescanMode.freeHand, \
                                        PVLinescanMode.circle, \
                                        PVLinescanMode.spiral):
            
                lsmodename = [i.name for i in PVLinescanMode][[i.value for i in PVLinescanMode].index(self.definition.mode)]
                
                if len(self.frames) > 1:
                    warnings.warn("Expected only one frame in %s linescan mode; got %d instead.\nOnly data from the first frame will be returned" % (lsmodename, len(self.frames)))

                metadata["frame_period"] = 1 * pq.dimensionless
                
                metadata["frames"] = [self.frames[0].metadata()]
            
            elif self.definition.mode == PVLinescanMode.lissajous: # TODO implement me!
                # two frames per sequence
                raise NotImplementedError("parsing lissajous linescan mode not yet implemented")
            
        elif self.type in (PVSequenceType.TSeries, PVSequenceType.ZSeries, PVSequenceType.Single):
            if self.type == PVSequenceType.TSeries:
                frameTimes = [f.attributes["absoluteTime"] for f in self.frames]

                diffTimes = np.diff(frameTimes) # there will be some jitter

                framePeriod = float(diffTimes.mean()) * pq.s
        
            elif self.type == PVSequenceType.ZSeries:
                # get the Z axis resolution from the frames state
                z_pos = [f.state.attributes["positionCurrent_ZAxis"] for f in self.frames]
                z_steps = np.diff(z_pos)
                #if len(z_steps) > 1:
                    #if not all(z == z_steps[0] for z in z_steps):
                        #raise ValueError("Irregular Z axis sampling not supported")
                    
                framePeriod = abs(z_steps[0]) * pq.um
                
            else:
                framePeriod = 1 * pq.dimensionless
                    
            metadata["frame_period"] = framePeriod
                
            if len(self.frames) > 1:
                metadata["frames"] = [f.metadata() for f in self.frames]
                
            else:
                metadata["frames"] = [self.frames[0].metadata()]
                
        elif self.type == PVSequenceType.Point: # TODO implement me!
            raise NotImplementedError("Point scan sequence parsing not implemented yet")
        
        else:                           # do nothing here
            raise ValueError("Unknown sequence type %d" % self.type)
        
        metadata["type"] = self.__class__.__name__
        
        return DataBag(metadata)
    
    @property
    def version(self):
        return self.parent.version
    
    @property
    def versionString(self):
        return self.parent.versionString
        
    @property
    def parent(self):
        r"""The parent PVScan object, or None
        """
        return self._parent_
    
    @property
    def scan(self):
        r"""Alias for parent
        """
        return self.parent
    
    @property
    def multiBandOutput(self):
        r"""If True, the () operator reads this frame's files as a multiband image.
        This requires that each file corresponds to one channel and that all files 
        have a channel axis. Only applies when there are between 2 and 4 files per frame.
        """
        return self._mergeChannelsOnOutput_
    
    @multiBandOutput.setter
    def multiBandOutput(self, val):
        r"""Permanently sets the state of the multiBandOutput property to val.
        
        Parameters:
        "val: boolean
        """
        self._mergeChannelsOnOutput_ = val
    
    @property
    def attributes(self):
        return self._attributes_
        
    @property
    def length(self):
        return len(self.frames)
    
    @property
    def definition(self):
        return self._definition_
    
    @property
    def zAxisSynchronization(self):
        return self._syncZAxis_
    
    @property
    def cycle(self):
        return self._attributes_["cycle"]
        #return self.__dict__["cycle"]
        
    @property # read only
    def sequencetype(self):
        return self._attributes_["sequencetype"]
        #return self.__dict__["sequencetype"]
    
    @property # read only
    def type(self):
        r""" Alias to sequencetype property
        """
        return self.sequencetype
    
    @property # read only
    def typename(self):
        r"""Alias to sequencetypename property
        """
        return self.sequencetypename
    
    @property
    def sequencetypename(self):
        return PVSequenceType(self._attributes_["sequencetype"]).name
        #return PVSequenceType(self.__dict__["sequencetype"]).name
    
    @property
    def filepath(self):
        r"""Returns the absolute path to the data referred to in this object.
        
        Value of path is the attribute of the parent PVScan, or None if the 
        latter is None.
        """
        if self.parent is None:
            return
        
        return self.parent.filepath
    
    def __repr__(self):
        return self.__str__()
                
    def __str__(self):
        ret = [" %s %s:\n" % ("Sequence type: ", PVSequenceType(self.sequencetype).name)]
        
        ret.append(" Sequence attributes:\n")
        #for k in self.__dict__.keys():
        for k in self._attributes_.keys():
            if k != "sequencetype":
                ret.append("  %s = %s\n" % (k, self._attributes_[k]))
                #ret.append("  %s = %s\n" % (k, self.__dict__[k]))
                
        if self._definition_ is not None:
            ret.append("\n Sequence definition:\n")
            ret.append(self._definition_.__str__())

        if self._syncZAxis_ is not None:
            ret.append("\n Z Axis Synchronization:\n")
            for k in self._syncZAxis_.keys():
                ret.append("  %s = %s\n" % (k, self._syncZAxis_[k]))

        ret.append("\n")
            
        for f in self.frames:
            ret.append(f.__str__())
        
        #ret.append("\n")
        
        return ("".join(ret))
        
                

class PVScan(PVObject):
    r"""Encapsulates a PrairieView scan data.
    Stores a scan configuration object as parsed from an XML file, 
    optionally with data from a *Config file (also an XMl file but saved as ascii).
    The two files must have been read and parsed into valid xml documents and 
    xml element, respectively.
    
    This is so that scan data from various systems can be used/brought to a 
    common denominator (to the extent possible) represented by ScanData in this 
    framework.
    
    The other system planned for support is ScanImage (under progress)
    
    """
    
    def __init__(self, doc:typing.Union[str, xmlutils.xml.dom.minidom.Document, pathlib.Path], 
                 config:typing.Optional[typing.Union[str, xmlutils.xml.dom.minidom.Document, pathlib.Path]] = None,
                 name=None):
        super().__init__()
        self._path_ = None
        self._parent_ = None
        self._mergeChannelsOnOutput_ = False
        self._systemConfiguration_ = None
        self._stateshard_ = None # NOTE: 2025-04-03 09:43:50 this is a PVStateShard in versions >= 5.5
        self._sequences_ = list()
        self.__version__ = tuple() # major, minor, micro, dot
        self._rec_datetime_ = datetime.datetime.now() # fallback value
        
        if isinstance(doc, str):
            doc = pathlib.Path(doc)
        
        if isinstance(doc, pathlib.Path):
            if not doc.is_file():
                raise OSError(f"Cannot find the file {doc}")
            mime_type, file_type, encoding = pio.getMimeAndFileType(doc)
            if "xml" not in mime_type.lower() and "xml" not in file_type("lower"): # don't rely on the 'xml' extension
                raise ValueError(f"{doc} does not appear to be an XML file")
            self._path_ = doc.absolute()
            doc = loadPrairieViewXML(self._path_) # loadPrairieViewXML will augment the XML document with DocPath node; not needed at this point, but surely later
            
        elif not isinstance(doc, xmlutils.xml.dom.minidom.Document):
            raise TypeError("Expecting a xmlutils.xml.dom.minidom.Document or a pathlib.Path for an XMl file as argument; got %s instead" % (type(doc).__name__))
        
        if doc.documentElement is None or doc.documentElement.nodeName != "PVScan":
            raise ValueError("XML data is not a valid PVScan Document")
        
        if doc.documentElement.attributes is None or any(s not in doc.documentElement.attributes for s in ("version", "date", "notes")):
            raise ValueError("XML data is not a valid PVScan Document")
            
        if not doc.documentElement.hasChildNodes():
            raise ValueError("PVScan XML data is empty!")

        # ATTENTION NEVER store the documentElement attributes, directly in __dict__
        # NOTE:2017-10-31 08:37:19
        # storing attributed in __dict__ will result in infinite recursions in __str__()
        # at various places in the code, unless you write code to manage it.
        # -- too work for little benefit
        
        self._attributes_ = DataBag(xmlutils.attributesToDict(doc.documentElement))
        v = self._attributes_.get("version", None)
        if isinstance(v, str) and len(v.strip()):
            self.__version__ = tuple(map(lambda x: eval(x), v.split('.')))
        else:
            raise ValueError(f"Invalid 'version' attribute: {v}")
        
        d = self._attributes_.get("date", None)
        if isinstance(d, str) and len(d.strip()):
            self._rec_datetime_ = dateutil.parser.parse(d)
        else:
            raise ValueError(f"Invalid 'date' attribute: {d}")
        
        # NOTE: 2025-04-02 22:06:15
        # Get the configuration of the system where the data was acquired.
        #
        # In older PV versions (before around 5.5) the configuration was stored
        # in a "SystemConfiguration" child node of the main PSVScan XML file.
        #
        # Since around verison 5.5 the configuration is stored in a separate file ("*.env")
        # containing a single document element named "Environment"; in PV 5.5.64
        # (the latest I have access to) there is the option of saving in the "old"
        # format - not sure if that means the configuration being stored as 
        # before, in a "SystemConfiguration" node inside the main PVScan file
        #
        # So I'm goint out on a limb, here, expect trouble
        if self.versionString < "5.5":
            sysconfigNodes = tuple(xmlutils.getChildren(doc.documentElement, tagName="SystemConfiguration"))
            if len(sysconfigNodes):
                self._systemConfiguration_ = PVSystemConfiguration(sysconfigNodes[0], self)
                
        if self.versionString >= "5.5" or self._systemConfiguration_ is None: 
            # attempt to cover up intermediate verions I don't have access to.
            # keeping fingers crossed here, as even more recent versions may have
            # broken things
            
            # This first looks for the information necessary to locate and *.env 
            # embedded in the PVScan document - not sure if there is an option 
            # in PV software to specify where this file is to be saved. On the
            # system I work with, this file is by default saved in the same
            # directory as the main PVScan xml file, so I assume that this is a
            # workable default.
            #
            # If the main PVscan XML document was loaded with the custom loadPrairieViewXML
            # function defined in this module then it WILL have a "DocPath" child 
            # node "injected" by the loadPrairieViewXML function, with the attribute
            # 'value' set to the str of the full path of the XML document file;
            # otherwise, the configuration  MUST be supplied as a parameter to the
            # constructor
            if isinstance(self._path_, pathlib.Path): 
                # self._path_ WAS set up above IF doc argument is a XML file.
                # On the system I work with, the environment (or configuration) file 
                # is saved in the same directory as the main PVScan XML file
                # So, going out on a limb here.
                configFile = self._path_.with_suffix(".env")
                config = pio.loadXML(configFile)
                self._systemConfiguration_ = PVSystemConfiguration(config.documentElement, self)
            else: 
                # self._path_ has NOT been set; this is usually because the 
                # 'doc' argument is a document previously loaded (either using
                # the pio.loadXMLFile function, or the custom loadPrairieViewXML
                # function in this module. In the latter case it WILL HAVE BEEN
                # 'augmented' with a child node 'DocPath' with the 'value'
                # attribute set to the absolute path of the PVScan XML file.
                docPathNodes = tuple(xmlutils.getChildren(doc.documentElement, tagName="DocPath"))
                if len(docPathNodes):
                    # was loaded using loadPrairieViewXML; 
                    self._path_ = pathlib.Path(docPathNodes[0]).getAttributes("value")
                    # so I assume the env file saved in the same directory by default
                    configFile = self._path_.with_suffix(".env")
                    if not configFile.is_file():
                        # my assumption failed here
                        raise OSError(f"Cannot find the configuration file {configFile}")
                    config = pio.loadXML(configFile)
                    self._systemConfiguration_ = PVSystemConfiguration(config.documentElement, parent=self)
                
                else:
                    if isinstance(config, str):
                        config = pathlib.Path(config)
                        
                    if isinstance(config, pathlib.Path) and config.is_file() and config.suffix.lower() == ".env":
                        config = pio.loadXMLFile(config) # OK to use the generic XML loader in pio module
                    elif isinstance(config, xmlutils.xml.dom.minidom.Document):
                        self._systemConfiguration_ = PVSystemConfiguration(config.documentElement, parent=self)
                    else:                    
                        raise TypeError(f"For separately loaded XML documents created with PrairieView version {self.versionString}, a 'config' parameter must be given,\n either a absolute path to an existing configuration file, or as a loaded XML document")
                
            
        if isinstance(name, str):
            self._name_ = name
            
        else:
            self._name_ =self._path_.stem
                
        sequenceNodes = xmlutils.getChildren(doc.documentElement, tagName="Sequence")
        self._sequences_[:] = list(map(lambda n: PVSequence(n, self), sequenceNodes))
        
        # NOTE: 2025-04-03 09:41:47 
        # in v5.5. and later there is now common state shard
        if self.versionString >= "5.5":
            stateNodes= tuple(xmlutils.getChildren(doc.documentElement, tagName = "PVStateShard"))
            if len(stateNodes):
                self._stateshard_ = PVStateShard(stateNodes[0], self)
            
    def __len__(self):
        return len(self.sequences)
    
    def __call__(self, filepath=None):
        r"""Returns a tuple (scans, scene) where each element is a sequence of VigraArray"""
        # NOTE: 2017-10-24 22:47:12
        # get the type of the first sequence; this should be the same for ALL
        # sequences in this scan (otherwise, behaviour is undefined)
        # TODO try to accommodate more generality here, it at all possible
        # (see comments below)
        
        if not all([sequence.sequencetype == self.sequences[0].sequencetype for sequence in self.sequences]):
            raise ValueError("Mixed types of PVSequence are not supported")
        
        # NOTE: 2017-10-24 23:23:50  TODO / FIXME
        # the PVSequence object should also parse metdata, and return parts of it
        # as metadata attached to the image (e.g., generate axis calibrations and
        # return image data as datatypes.PictArray), and other parts of it as a 
        # separate entity e.g. laser sources, laser power, PMT voltage, on-line 
        # signal conditoning sch as averaging, galvo-related stuff, pixel dwell 
        # time, shutter delays, relative zoom & rotation, etc.
        #
        # TODO decide what goes in such entity to make it s gneric as possible
        # TODO such that this can be TODO FACTORED OUT TODO in a superclass
        # TODO suitable for other systems as well: ScanImage, Scientifica's,
        # and other legacy software (e.g. LaserSharp -- anyone using this nowadays?)
        
        # TODO FIXME 2017-10-25 00:19:26
        # Linescan PVFrames also have "source files" which contain the "scene" 
        # where the sequence has been acquired; load these too
        
        if filepath is None:
            filepath = self.filepath
            
        if self.sequences[0].sequencetype == PVSequenceType.Linescan:
            if self.sequences[0].definition.mode in (PVLinescanMode.straightLine, \
                                        PVLinescanMode.freeHand, \
                                        PVLinescanMode.circle, \
                                        PVLinescanMode.spiral): # one frame per sequence
                # collect data from each sequence's frame and concatenate here along a 
                # new temporal axis
                # all linescan sequences have one frame except for lissajous which
                # we do not parse at the moment (NotImplementedError will be raised)
                # TODO - FIXME figure out what lissajous linescan type does
                # by the way there can be several "repeats" in lisaaouds scan (as
                # with all Linescans) which effeciely results in multiple PVSequence 
                # objects
                #
                # also TODO- FIXME what if several Linescan sequences have more than 
                # two frames - can this ever happen?
                
                # except for lissajous (which for now we reject by raising 
                # NotImplementedError - TODO - FIXME) the code below works on the 
                # assumption that there is ONLY ONE FRAME PER SEQUENCE
                
                # NOTE: 2017-10-25 00:33:11 
                # for linescans, the "y" axis is actually a "t" axis (linescan vs time:
                # the time domain of each linescan series of a "frame")
                # whereas frames are also concatenated along a new time axis (time domain
                # for frame cycles, or repetitions)
                # however, vigra prevents two axes with the same "key" in the axistags
                # therefore we need to assign this axis a different key than the default
                # "t" which has alray been assigned to the frame's time axis
                
                # NOTE 2017-11-06 12:54:13: 
                # parse the state shard for frame period in the first frame  of each 
                # sequence
                
                frameTimes = [float(s.frames[0].attributes["absoluteTime"]) for s in self.sequences]
                
                if len(frameTimes) > 1:
                    diffTimes = np.diff(frameTimes) # there will be some jitter
                    
                    framePeriod = float(diffTimes.mean())
                    
                else:
                    framePeriod = 1.0
                    
                newAxisInfo = vigra.AxisInfo(key="t1", 
                                             typeFlags=vigra.AxisType.Time, 
                                             resolution=framePeriod)
                
                newAxisCal = AxisCalibrationData.new(newAxisInfo)
                newAxisCal.units = pq.s
                newAxisCal.origin = float(self.sequences[0].frames[0].attributes["absoluteTime"])
                newAxisCal.resolution = framePeriod
                
                newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                
                if self._mergeChannelsOnOutput_:
                    data = [s.mergeChannels(filepath=filepath) for s in self.sequences]
                    
                    srcdata = [d[1] for d in data]
                    
                    frmdata = [d[0] for d in data]
                    
                    # each frame has already been concatenated into a
                    # multi-band image; what we have to do here is to 
                    # create a new time axis accordingly, on the highest
                    # dimension, then concatenate along it
                    
                    # NOTE: 2018-08-01 17:18:38
                    # see NOTE: 2018-08-01 17:04:06
                    
                    channelAxisDim = frmdata[0].axistags.channelIndex
                    
                    if channelAxisDim == fmrdata[0].ndim-1:
                        newAxisDim = channelAxisDim
                        
                    else:
                        newAxisDim = fmrdata[0].ndim
                    
                    # NOTE: 2017-10-25 00:46:27
                    # returns tuple of multi-band frame & source data
                    fdata = concatenateImages([insertAxis(img, newAxisInfo, newAxisDim) \
                                                        for img in frmdata], axis=newAxisInfo)
                    
                    channelAxisDim = srcdata[0].axistags.channelIndex
                    
                    if channelAxisDim == srcdata[0].ndim-1:
                        newAxisDim = channelAxisDim
                        
                    else:
                        newAxisDim = srcdata[0].ndim
                    
                    sdata = concatenateImages([insertAxis(img, newAxisInfo, newAxisDim) \
                                                        for img in srcdata], axis=newAxisInfo)
                    
                    
                    return fdata, sdata
                
                else: # keep channels separate:
                    # each frame yields a list of three single-band arrays (a triplet, 
                    # see PVFrame.__call__())
                    #
                    # in turn, PVSequence.__call__() would return a list of such lists
                    # (one per frame); 
                    #
                    # under the "single frame per sequence" assumption (see above) 
                    # the PVSequence.__call__() unpacks this such that here
                    # we end up with a list of triplets (one per sequence)
                    data = [s(filepath=filepath) for s in self.sequences]
                    
                    frmdata = [d[0] for d in data] # take frame data
                    
                    srcdata = [d[1] for d in data] # take source data
                    
                    # NOTE: 2018-08-01 17:04:06
                    # there will always be a channel axis at this stage
                    # if channel axis is at the highest dimension, insert the 
                    # new axis (t1) right before it
                    # otherwise, insert it at the highest dimension
                    
                    channelAxisDim = frmdata[0][0].axistags.channelIndex

                    if channelAxisDim == frmdata[0][0].ndim-1: # channel axis on highest dimension
                        # insert new axis here so that channel axis will be 
                        # pushed further to the next higher dimension
                        newAxisDim = channelAxisDim 
                        
                    else: # channel axis is on an inner dimension:
                        # we assume there is a good reason for this so we insert
                        # concatenation axis on highest dimension anyway
                        newAxisDim = frmdata[0][0].ndim # use highest dimension for concatenation axis
                        
                    # NOTE: 2017-10-25 00:46:39
                    # returns a tuple of single-band frame data channels & single-band source data channels 
                    
                    # NOTE: 2025-04-03 08:46:21
                    # fdata is a sequence of single-band frame data channels
                    fdata = [concatenateImages(*[insertAxis(frmdata[sequence][channel], 
                                                                      newAxisInfo, 
                                                                      newAxisDim) for sequence in range(len(self.sequences))],
                                                        axis=newAxisInfo) for channel in range(len(frmdata[0]))]
                    
                    # NOTE: 2025-04-03 08:49:27
                    # sdata is a sequence of single-band scene data channels
                    sdata = [concatenateImages(*[insertAxis(srcdata[sequence][channel],
                                                                      newAxisInfo, 
                                                                      newAxisDim) for sequence in range(len(self.sequences))],
                                                        axis=newAxisInfo) for channel in range(len(srcdata[0]))]
                
            
            elif self.sequences[0].definition.mode == PVLinescanMode.lissajous:
                raise NotImplementedError("parsing lissajous linescan mode not yet implemented")
                
            else:
                raise ValueError("Unexpected Linescan mode")#
            
            return fdata, sdata # => scans, scene in scanData()
                
        elif self.sequences[0].sequencetype in (PVSequenceType.TSeries.value, PVSequenceType.ZSeries.value):
            # nothing to concatenate here, just return the result from PVSequence() call
            # on self.sequences[0]
            # working on the assumption that there is only one sequence in this 
            # PVScan instance so we only read the first element in self.sequences
            # the PVSequence() call will do the necessary concatenation
            # TODO - FIXME allow for multiple sequences here too -- should I?
            
            # NOTE: 2017-10-25 00:34:44
            # be mindful that frames __call__() return a TUPLE of
            # frame data and source data; except for Linescan frames, source data
            # is None; ths tuple is unravelled by the PVSequence, to return only
            # frame data (because TSeries and ZSeries frames have no "source"
            # attribute)
            if self._mergeChannelsOnOutput_:
                return self.sequences[0].mergeChannels() # (frameData, None)
                # return (self.sequences[0].mergeChannels(), None) # (frameData, None)
                
            else:
                return self.sequences[0]() #, None )# (frameData, None)
                # return (self.sequences[0](), None )# (frameData, None)
            
        elif self.sequences[0].sequencetype == PVSequenceType.Single.value:
            # again, nothing to do here -- this pertains to SingleImage 
            # acquisition in PrairieView and consists of one sequence with one frame
            # TODO - FIXME can these ever have mmore thann one sequence? can each
            # of these sequences ever have more than one frame?
            
            if self._mergeChannelsOnOutput_:
                return self.sequences[0].mergeChannels()# (frameData, None)
                # return (self.sequences[0].mergeChannels(), None )# (frameData, None)
                
            else:
                return self.sequences[0]() #, None )# (frameData, None)
                # return (self.sequences[0](), None )# (frameData, None)
            
        
        elif self.sequences[0].sequencetype == PVSequenceType.Point.value:
            raise NotImplementedError("Point scan sequence parsing not implemented yet")
            # TODO - FIXME figure out what this does and how to parse it sensibly
            
        else:  # do nothing here
            raise ValueError("Unknown sequence type %d" % self.sequencetype)
            

    def scanData(self, mergeChannels=False, analysisOptions=None, electrophysiology=None, name=None):
        r"""Returns a datatypes.ScanData object
        """
        
        if mergeChannels:
            caller = self.mergeChannels
            
        else:
            caller = self.__call__
            
            
        # read scans and scene vigra arrays concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(caller)]
            
        for future in concurrent.futures.as_completed(futures):
            (scans, scene) = future.result()
        
        meta = self.metadata()
        
        file_origin = self.filepath
        rec_datetime = self._rec_datetime_
            
        return ScanData(scene=scene, scans=scans, name=self.name,
                        electrophysiology=electrophysiology,
                        analysisOptions=analysisOptions,
                        file_origin=file_origin,
                        rec_datetime=rec_datetime,
                        metadata=self.metadata())

    def scandata(self, *args, **kwargs):
        return self.scanData(*args, **kwargs)
        
    def mergeChannels(self, filepath=None):
        r"""Coerce reading the files as a multiband image.
        
        The self.multiBandOutput property is temporarily set to True, then 
        reverted to its previous value after the image files were read.
        
        """
        v = self._mergeChannelsOnOutput_
        self._mergeChannelsOnOutput_= True
        try:
            data = self.__call__(filepath=filepath)
        except Exception as e:
            self._mergeChannelsOnOutput_ = v
            raise e
        
        self._mergeChannelsOnOutput_ = v
        return data
    
    @property
    def metadata(self):
        r"""Returns metadata associated with this PVScan
        """
        metadata = DataBag(mutable_types=True, allow_none=True)
        metadata["configuration"] = self.configuration.as_dict()
        metadata["file_path"] = self.filepath
        
        if self.sequences[0].type == PVSequenceType.Linescan:
            frameTimes = [float(s.frames[0].attributes["absoluteTime"]) for s in self.sequences]
            
            if len(frameTimes) > 1:
                diffTimes = np.diff(frameTimes) # there will be some jitter
                
                framePeriod = float(diffTimes.mean())
                    
                metadata["sequence_period"] = framePeriod * pq.s
                
            else:
                metadata["sequence_period"] = 1 * pq.dimensionless
                
            
        else:
            metadata["sequence_period"] = 1 * pq.dimensionless
        
        if len(self.sequences) > 1:
            metadata["sequences"] = [s.metadata() for s in self.sequences]
        else:
            metadata["sequences"] = [self.sequences[0].metadata()]
            
        metadata["type"] = self.__class__.__name__
        
        return metadata
    
    @property
    def state(self):
        return self._stateshard_
    
    @property
    def sequences(self):
        return self._sequences_
    
    @property
    def filepath(self):
        return self._path_
    
    @filepath.setter
    def filepath(self, val):
        from os import path
        if os.path.isdir(val):
            self._path_ = val
        else:
            raise ValueError("A valid directory path was expected")
        
    @property
    def filename(self):
        return self._path_.name
    
    @property
    def rec_datetime(self):
        return self._rec_datetime_
    
    @property
    def name(self):
        return self._name_
    
    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError("expecting a str; got %s instead" % type(value).__name__)
        
        self._name_ = value
        
    @property
    def datapath(self):
        r"""Alias for the filepath property
        """
        return self.filepath
    
    @property
    def multiBandOutput(self):
        r"""If True, the () operator reads this frame's files as a multiband image.
        This requires that each file corresponds to one channel and that all files 
        have a channel axis. Only applies when there are between 2 and 4 files per frame.
        """
        return self._mergeChannelsOnOutput_
    
    @multiBandOutput.setter
    def multiBandOutput(self, val):
        r"""Permanently sets the state of the multiBandOutput property to val.
        
        Parameters:
        "val: boolean
        """
        self._mergeChannelsOnOutput_ = val
        
    @property
    def version(self) -> tuple[int]:
        r"""Version of the PrairieView software used to acquire this PVScan object.
        Returns a tuple of int: (major, minor, micro, dot)"""
        return self.__version__
    
    @property
    def versionString(self) -> str:
        r"""Version of the PrairieView software used to acquire this PVScan object.
        Returns a stringof the form major.minor.micro.dot where each component is
        a string representation of an integer"""
        return ".".join(map(lambda x: f"{x}", self.version))
        
    @property
    def attributes(self):
        return self._attributes_
        
    @property
    def cycles(self):
        return self.sequences
    
    @property
    def configuration(self):
        return self._systemConfiguration_
    
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        ret = ["%s %s with %d sequences:\n" % (type(self).__name__, "object", len(self.sequences))]
        
        ret.append("Attributes:")
        #for k in self.__dict__.keys():
            #ret.append(" %s = %s" % (k, self.__dict__[k]))
            
        for k in self._attributes_.keys():
            ret.append(" %s = %s" % (k, self._attributes_[k]))
            
        ret.append("\n")

        #ret.append("Configuration:")
        ret.append(self._systemConfiguration_.__str__())
        
        ret.append("\n")

        ret.append("SEQUENCES:")
        
        for k, s in enumerate(self.sequences):
            ret.append("Sequence %d:" % k)
            ret.append(s.__str__())
            
        ret.append("\n")
            
        return "\n".join(ret)
    
# NOTE: 2020-11-30 23:45:00
# place the mixin before other base classes so that it is initialized
# then super(...).__init__ it
# class PrairieViewImporter(WorkspaceGuiMixin, __QDialog__, __UI_PrairieImporter, ):
#     sig_protocolRemoved = Signal(int, name="sig_protocolRemoved")
class PrairieViewImporter(QtWidgets.QDialog, __UI_PrairieImporter, WorkspaceGuiMixin):
    sig_protocolRemoved = Signal(int, name="sig_protocolRemoved")
    
    def __init__(self, parent=None,
                 name: typing.Optional[str] = None,
                 pvScanFileName: typing.Optional[str]=None, 
                 optionsFileName: typing.Optional[str]=None, 
                 ephysFileNames: typing.Optional[typing.Union[str, tuple, list]]=None,
                 protocolFileName: typing.Optional[str]=None,
                 clearTriggerEvents: typing.Optional[bool]=False,
                 auto_export:bool = False,
                 **kwargs): # parent, flags - see documentation for QDialog constructor in Qt Assistant
        r"""
        Parameters:
        -----------
        name:str (optional, default is None) - name of generated ScanData
        pvScanFileName:str (optional, default is None) - name of PrairieView scan experiment (XML) file
        optionsFileName:str (optional, default is None) - name of a pickle (*pkl) file containing ScanData options
        ephysFileNames:str or sequence of str - name(s) of Axon file(s) , or
                    pickle (*.pkl) files, containing associated electrophysiology
                            data.
                    
                    The Axon files can be text (*.atf) or binary (*.abf) files.
                    
                    Optional; default is None
                            
        protocolFileName:str (optional, default is None) - name of pickle (*.pkl) 
                    file with TriggerProtocols 

        clearTriggerEvents:bool (optional, default is False)
                            When True (default), remove all neo.Event objects
                            embedded in the electrophysiology data, before
                            detecting trigger events.
                            
        auto_export: bool (optional, default is False)
            When True, pressing "OK" button will export the generated ScanData
            to the workspace.
            
            This is a convenience to place data directly in Scipyen's workspace.
            
            When False (the default) the dialog simply generates the Scandata 
            object and stores it in the "scanData" attribute. TODO: Because this
            can be time consuming best is to call this asynchronously, when 
            auto_export is False.
        
        """
        # NOTE: 2021-04-18 11:49:52
        # 'parent' parameter is required; when called from a PyQt5 slot, 'parent'
        # should be set to the object which own the slot, so that it will take
        # owership fo the dialog; otherwise, the dialog will go out of scope when
        # the slot returns - this means its window will close and the C/C++
        # objects that compose it will be garbage collected (also meaning that 
        # later delete actions on these objects will throw exceptions)
        #
        # see also scipyen gui.mainwindow.ScipyenWindow.slot_importPrairieView()
        super().__init__(parent)
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)
        #super(WorkspaceGuiMixin, self).__init__(parent, **kwargs)
        
        self._scandata_ = None # the outcome: a ScanData object
        
        self._pvscan_ = None # the xml.dom.minidom.Document that specifies the
                            # the PVScan experiment
        
        self.dataName = "" # the value of lsdata "name" attribute
        
        self.pvScanFileName = "" # the PV Scan XML document file - contains
                                 # scan experiment information & location of
                                 # the files with the numerical data of lsdata
                                 
        self.scanDataVarName = "" # the name that will be assigned to lsdata in the
                                # user's workspace
                                
        self.protocolFileName = "" # pickle file containing the trigger protocols
        
        self.optionsFileName = "" # pickle file containing saved ESPCaT options
        
        self.ephysFileNames = list() 
        
        self.scanDataOptions = ScanDataOptions.default() # ScanDataOptions object - to be assigned to lsdata
        
        self._ephys_ = None # a neo.Block with electrophysiology recordings associated
                            # with lsdata
                            
        
        self.clearEvents = clearTriggerEvents if isinstance(clearTriggerEvents, bool) else False
                            
        self.triggerProtocols = list()  # list of TriggerProtocol objects associated
                                        # with lsdata
                                        
        self.cachedEvents = list()
        self.cachedProtocols = list()
        self.cachedProtocolFileName = ""
                                        
        if isinstance(name, str) and len(name.strip()):
            self.dataName = name
            self.scanDataVarName = strutils.str2symbol(self.dataName)
        
        if isinstance(pvScanFileName, str) and len(pvScanFileName.strip()):
            if os.path.isfile(pvScanFileName) and any([mime in pio.mimetypes.guess_type(pvScanFileName)[0] for mime in ("xml", "pickle")]):
                self.pvScanFileName = pvScanFileName
        
        if isinstance(optionsFileName, str) and len(optionsFileName.strip()):
            if os.path.isfile(optionsFileName) and "pickle" in pio.mimetypes.guess_type(optionsFileName)[0]:
                self.optionsFileName = optionsFileName
        
        if isinstance(ephysFileNames, str) and len(ephysFileNames.strip()):
            if os.path.isfile(ephysFileNames) and any([mime in pio.mimetypes.guess_type(ephysFileNames)[0] for mime in ("pickle", "axon")]):
                self.ephysFileNames = [ephysFileNames]
            
        elif isinstance(ephysFileNames, (tuple, list)) and all([isinstance(v, str) for v in ephysFileNames]):
            self.ephysFileNames = [s for s in ephysFileNames if (len(s.strip()) and any([mime in pio.mimetypes.guess_type(s)[0]]))]
        
        if isinstance(protocolFileName, str) and len(protocolFileName.strip()):
            if os.path.isfile(self.protocolFileName) and "pickle" in pio.mimetypes.guess_type(self.protocolFileName)[0]:
                self.protocolFileName = protocolFileName
                
        self.auto_export = auto_export
        
        self._configureUI_()
        self.setSizeGripEnabled(True)
        
    def _configureUI_(self):
        self.setupUi(self)
        
        self.dataNameLineEdit.undoAvailable=True
        self.dataNameLineEdit.redoAvailable=True
        self.dataNameLineEdit.setClearButtonEnabled(True)
        if len(self.dataName):
            self.dataNameLineEdit.setText(self.dataName)
        self.dataNameLineEdit.editingFinished.connect(self._slot_setDataName)
        self.dataNameLineEdit.textChanged.connect(self._slot_setDataName)
        
        self.pvScanFileNameLineEdit.undoAvailable=True
        self.pvScanFileNameLineEdit.redoAvailable=True
        self.pvScanFileNameLineEdit.setClearButtonEnabled(True)
        if len(self.pvScanFileName):
            self.pvScanFileNameLineEdit.setText(self.pvScanFileName)
        self.pvScanFileNameLineEdit.editingFinished.connect(self._slot_setPVScanFileName)
        self.pvScanFileNameLineEdit.textChanged.connect(self._slot_setPVScanFileName)
        
        self.pvScanFileChooserToolButton.clicked.connect(self._slot_choosePVScanFile)
        self.pvScanImportFromWorkspaceToolButton.clicked.connect(self._slot_importPVScanFromWorkspace)
        
        self.optionsFileNameLineEdit.undoAvailable=True
        self.optionsFileNameLineEdit.redoAvailable=True
        self.optionsFileNameLineEdit.setClearButtonEnabled(True)
        
        if len(self.optionsFileName):
            self.optionsFileNameLineEdit.setText(self.optionsFileName)
        self.optionsFileNameLineEdit.editingFinished.connect(self._slot_setOptionsFileName)
        self.optionsFileNameLineEdit.textChanged.connect(self._slot_setOptionsFileName)
        
        self.optionsFileChooserToolButton.clicked.connect(self._slot_chooseOptionFile)
        self.optionsImportToolButton.clicked.connect(self._slot_importOptionsFromWorkspace)
        
        self.ephysFileNameLineEdit.undoAvailable=True
        self.ephysFileNameLineEdit.redoAvailable=True
        self.ephysFileNameLineEdit.setClearButtonEnabled(True)
        self.ephysFileNameLineEdit.setText(os.pathsep.join(self.ephysFileNames))
        self.ephysFileNameLineEdit.editingFinished.connect(self._slot_setEphysFileNames)
        
        self.ephysFileChooserToolButton.clicked.connect(self._slot_chooseEphysFiles)
        self.ephysImportFromWorkspaceToolButon.clicked.connect(self._slot_importEphysFromWorkspace)
        
        self.triggerProtocolFileNameLineEdit.undoAvailable=True
        self.triggerProtocolFileNameLineEdit.redoAvailable=True
        self.triggerProtocolFileNameLineEdit.setClearButtonEnabled(True)
        
        if len(self.protocolFileName):
            self.triggerProtocolFileNameLineEdit.setText(protocolFile)
        self.triggerProtocolFileNameLineEdit.editingFinished.connect(self._slot_setProtocolFileName)
        self.triggerProtocolFileNameLineEdit.textChanged.connect(self._slot_setProtocolFileName)
            
        
        self.triggerProtocolFileChooserToolButton.clicked.connect(self._slot_chooseProtocolFile)
        
        self.protocolsImportToolButton.clicked.connect(self._slot_importProtocolFromWorkspace)
        
        self.detectTriggersToolButton.clicked.connect(self._slot_startTriggerEventDetectionGui)
        self.editTriggerProtocolsToolButton.clicked.connect(self._slot_editTriggerProtocols)
        self.buildScandataToolButton.clicked.connect(self.slot_generateScanData)
        
        # NOTE: 2021-10-09 23:55:03
        # below self._scipyenWindow_ is inherited from WorkspaceGuiMixin (initialized)
        self.ephysPreview = sv.SignalViewer(win_title = "Trigger Events Detection")
        
        #self.ephysPreview = sv.SignalViewer(parent = self._scipyenWindow_, 
                                            #win_title = "Trigger Events Detection")
        
        #self.ephysPreview = sv.SignalViewer(parent = self, 
                                            #win_title = "Trigger Events Detection")
        
        # NOTE: 2021-03-21 11:35:59 just a "place holder" here; the actual dialog 
        # created in _slot_startTriggerEventDetectionGui()
        self.eventDetectionDialog = None # when a TriggerDetectDialog, this caches the detection options & events
        
        #self.protocolEditorDialog = ProtocolEditorDialog(parent=self, title = "Edit Trigger Protocols")
        #self.protocolEditorDialog = ProtocolEditorDialog(parent=self._scipyenWindow_, title = "Edit Trigger Protocols")
        self.protocolEditorDialog = ProtocolEditorDialog(title = "Edit Trigger Protocols")
        
        # the ProtocolEditorDialog works on a reference to the list of 
        # TriggerProtocols stored in here.
        self.protocolEditorDialog.triggerProtocols = self.triggerProtocols
        self.protocolEditorDialog.sig_detectTriggers.connect(self._slot_startTriggerEventDetectionGui)
        self.protocolEditorDialog.sig_removeProtocol.connect(self._slot_removeProtocol)
        self.protocolEditorDialog.sig_requestProtocolAdd.connect(self._slot_protocolAddRequest)
        self.protocolEditorDialog.finished.connect(self._slot_protocolEditorFinished)
        
        # self.buttonBox.accepted.connect(self.slot_generateScanData)
        
    @Slot(int)
    def _slot_removeProtocol(self, index):
        r"""Removes a trigger protocol.
        """
        # TODO: contemplate the use of the traitlets' observer paradigm with
        # TriggerProtocol objects.
        
        if index < len(self.triggerProtocols):
            tp = self.triggerProtocols[index]
        
            if isinstance(self._scandata_, ScanData):
                self._scandata_.removeTriggerProtocol(index)
        
            if isinstance(self._ephys_, neo.Block):
                remove_trigger_protocol(tp, self._ephys_)
            
            self.sig_protocolRemoved.emit(index)
            
    @Slot()
    def _slot_protocolAddRequest(self):
        pass
    
    @Slot()
    def _slot_editTriggerProtocols(self):
        self.protocolEditorDialog.triggerProtocols = self.triggerProtocols
        self.protocolEditorDialog.open()
        
    @Slot()
    def _slot_protocolEditorFinished(self):
        pass
        
    @Slot()
    @safewrapper
    def _slot_startTriggerEventDetectionGui(self):
        r"""Opens the trigger event detection dialog.
        The following signals are connected to this slot:
            detectTriggersToolButton.clicked()
            protocolEditorDialog.sig_detectTrigger()
        """
        if self._ephys_ is None:
            return
        
        if isinstance(self._ephys_, neo.Block) and len(self._ephys_.segments):
            if self.eventDetectionDialog is None:
                self.eventDetectionDialog = TriggerDetectDialog(ephysdata=self._ephys_,
                                                                clearEvents=True,
                                                                ephysViewer = self.ephysPreview)
                                                                #parent=self._scipyenWindow_)
                self.eventDetectionDialog.finished.connect(self._slot_stopTriggerEventDetectionGui)
            
            #self.ephysPreview.plot(self._ephys_) # done in TriggerDetectDialog c'tor
            
            # NOTE: 2021-04-11 14:06:55
            # call open() instead of anything else to keep the GUI loop running
            # and NOT block interaction with other windows, especially with the
            # SignalViewer that plots the ephys data
            self.eventDetectionDialog.open() 
            
    @Slot()
    def _slot_stopTriggerEventDetectionGui(self):
        r"""Closes trigger event detection dialog and interprets the result.
        If dialog.result() is "accepted" (or yes/ok) then a new set collection
        of trigger protocols is generated.
    
        The following signals are connected to this slot:
            eventDetectionDialog.finished()
        """
        self.ephysPreview.close()
        if self.eventDetectionDialog.result():
            if not self.eventDetectionDialog.detected:
                self.eventDetectionDialog.detect_triggers()
                
            if len(self.eventDetectionDialog.triggerProtocols[:]):
                self.cachedProtocols[:] = self.triggerProtocols[:]
                self.cachedProtocolFileName = self.triggerProtocolFileNameLineEdit.text()
                self.triggerProtocols[:] = self.eventDetectionDialog.triggerProtocols[:]
            
                self.triggerProtocolFileNameLineEdit.setText("<detected>")
                
            else:
                self.triggerProtocolFileNameLineEdit.setText("")
            
    @Slot()
    def _slot_undoTriggers(self):
        if self._ephys_ is None:
            return
        
        signalblockers = [QtCore.QSignalBlocker(self.triggerProtocolFileNameLineEdit)]
        
        for k,s in enumerate(self._ephys_.segments):
            s.events.clear()
            if k < len(self.cachedEvents):
                s.events = self.cachedEvents[k]
                
        self.triggerProtocols[:] = self.cachedProtocols[:]
        self.ephysPreview.plot(self._ephys_)
        self.updateProtocolEditor()
        
        if len(self.protocolFileName):
            self.triggerProtocolFileNameLineEdit.setText(self.protocolFileName)
            
    @Slot(int)
    def _slot_clearEventsChanged(self, value):
        self.clearEvents = self.clearEventsCheckBox.isChecked()
        
    @Slot()
    @safewrapper
    def _slot_setPVScanFileName(self):
        # connected to editing the PVScan field
        if "imported" in self.pvScanFileNameLineEdit.text():
            return
        
        self.pvScanFileName = self.pvScanFileNameLineEdit.text().strip()
        
        if len(self.pvScanFileName.strip()):
            ret = self.loadPVScan(self.pvScanFileName)
            if not ret:
                self.pvScanFileName = ""
                self._pvscan_ = None
                self._scandata_ = None
        
        else:
            self.pvScanFileName = ""
            self._pvscan_ = None
            self._scandata_ = None
                
    @Slot()
    @safewrapper
    def _slot_choosePVScanFile(self):
        signalblockers = [QtCore.QSignalBlocker(w) for w in (self.pvScanFileNameLineEdit, self.dataNameLineEdit)]
        fileFilter = ";;".join(["XML Files (*.xml)", "Pickle files (*.pkl)", "All files (*.*)"])
        
        self.pvScanFileName, _ = self.chooseFile(caption="Open PrairieView file",
                                   fileFilter=fileFilter)
        
        if len(self.pvScanFileName.strip()):
            self._scandata_ = None # because we need to rebuild the scanData
            if self.loadPVScan(self.pvScanFileName):
                self.pvScanFileNameLineEdit.setText(self.pvScanFileName)
            else:
                self.pvScanFileNameLineEdit.clear()
                self.pvScanFileName = ""
                self._pvscan_ = None
                
        else:
            self.pvScanFileNameLineEdit.clear()
            self.pvScanFileName = ""
            self._pvscan_ = None

    @Slot()
    @safewrapper
    def _slot_setOptionsFileName(self):
        # connected to editing Options field
        if "imported" in self.optionsFileNameLineEdit.text():
            return
        self.optionsFileName = self.optionsFileNameLineEdit.text()
        if len(self.optionsFileName.strip()):
            ret = self.loadOptions(self.optionsFileName) 
            if not ret:
                self.optionsFileName = ""
                # NOTE: 2024-07-28 10:06:23
                # this may overwrite prev options, so chuck it 
                # self.scanDataOptions = ScanDataOptions.default()
                
        else:
            self.optionsFileName = ""
            # see NOTE: 2024-07-28 10:06:23
            # self.scanDataOptions = ScanDataOptions.default()

    @Slot()
    @safewrapper
    def _slot_chooseOptionFile(self):
        signalblockers = [QtCore.QSignalBlocker(w) for w in (self.optionsFileNameLineEdit,)]
        caption = "Open ScanData Options file for %s" % self.scanDataVarName if (isinstance(self.scanDataVarName, str) and len(self.scanDataVarName.strip())) else "Open EPSCaT Options file"
        
        self.optionsFileName, _ = self.chooseFile(caption=caption, fileFilter="HDF5 Files (*.h5)")
        # self.optionsFileName, _ = self.chooseFile(caption=caption, fileFilter="Pickle Files (*.pkl)")
        
        if len(self.optionsFileName.strip()):
            if self.loadOptions(self.optionsFileName):
                self.optionsFileNameLineEdit.setText(self.optionsFileName)
                
            else:
                self.optionsFileName = ""
                self.optionsFileNameLineEdit.clear()
                self.scanDataOptions = None
                
        else:
            self.optionsFileName = ""
            self.optionsFileNameLineEdit.clear()
            self.scanDataOptions = None
            
    @Slot()
    @safewrapper
    def _slot_setEphysFileNames(self):
        # NOTE: 2020-12-26 12:17:01 This always generates a list of str even if
        # the split results in only one element.
        if any([v in self.ephysFileNameLineEdit.text() for v in ("mutliple files", "imported")]):
            return
        
        self.ephysFileNames = self.ephysFileNameLineEdit.text().split(os.pathsep)
        
        if len(self.ephysFileNames):
            ret = self.loadEphys(self.ephysFileNames)
            if not ret:
                self._ephys_ = None
                
        else:
            self._ephys_ = None
                
    @Slot()
    @safewrapper
    def _slot_chooseEphysFiles(self):
        signalblockers =[QtCore.QSignalBlocker(w) for w in (self.ephysFileNameLineEdit,)]

        #targetDir = os.getcwd()
        caption = "Open Electrophysiology Data file(s) for %s" % self.scanDataVarName if (isinstance(self.scanDataVarName, str) and len(self.scanDataVarName.strip())) else "Open Electrophysiology Data file(s)"
        
        fileFilter = ";;".join(["Axon files (*.abf)", "Pickle files (*.pkl)"])
        
        self.ephysFileNames, _ = self.chooseFile(caption=caption, fileFilter=fileFilter, single=False)
        
        if len(self.ephysFileNames) == 1:
            self.ephysFileNameLineEdit.setText(self.ephysFileNames[0])
            
        elif len(self.ephysFileNames) > 1:
            self.ephysFileNameLineEdit.setText("<multiple files>")
            
        else:
            self.ephysFileNameLineEdit.clear()
            
        if len(self.ephysFileNames):
            ret = self.loadEphys(self.ephysFileNames)
            if not ret:
                self.ephysFileNameLineEdit.clear()
                self._ephys_ = None
    
    @Slot()
    @safewrapper
    def _slot_setDataName(self):
        self.dataName = self.dataNameLineEdit.text()
        if len(self.dataName.strip()):
            self.scanDataVarName = strutils.str2symbol(self.dataName)
            
    @Slot()
    @safewrapper
    def _slot_setProtocolFileName(self):
        if any([v in self.triggerProtocolFileNameLineEdit.text() for v in ("imported", "detected")]):
            return
        self.protocolFileName = self.triggerProtocolFileNameLineEdit.text()
        if len(self.protocolFileName.strip()):
            if self.loadProtocols(self.protocolFileName):
                self.cachedProtocolFileName = self.protocolFileName
        
        else:
            self.triggerProtocols.clear()
        
    @Slot()
    @safewrapper
    def _slot_chooseProtocolFile(self):
        signalblockers = [QtCore.QSignalBlocker(w) for w in (self.triggerProtocolFileNameLineEdit,)]
        targetdir = os.getcwd()
        caption = "Open Trigger Protocol file for %s" % self.scanDataVarName if (isinstance(self.scanDataVarName, str) and len(self.scanDataVarName.strip())) else "Open Trigger Protocol file"
            
        self.protocolFileName, _ = self.chooseFile(caption=caption, fileFilter="Pickle Files (*.pkl)")
        
        if len(self.protocolFileName.strip()):
            if self.loadProtocols(self.protocolFileName):
                self.triggerProtocolFileNameLineEdit.setText(self.protocolFileName)
                self.cachedProtocolFileName = self.protocolFileName
            
        else:
            self.triggerProtocolFileNameLineEdit.setText(self.cachedProtocolFileName)
            self.triggerProtocols.clear()
        
    @Slot()
    @safewrapper
    def _slot_importPVScanFromWorkspace(self):
        vars_ = self.importWorkspaceData([xmlutils.xml.dom.minidom.Document, PVScan],
                                         title="Import PVScan",
                                         single=True)
        
        if len(vars_):
            if isinstance(vars_[0], xmlutils.xml.dom.minidom.Document):
                self._pvscan_ = PVScan(vars_[0])
            elif isinstance(vars_[0], PVScan):
                self._pvscan_ = vars_[0]
            else:
                self.errorMessage("Import PrairieView", "Expecting a PVScan or an XML document; got %s instead." % type(vars_[0]).__name__)

            signalblockers = [QtCore.QSignalBlocker(w) for w in (self.pvScanFileNameLineEdit, self.dataNameLineEdit)]
            self.pvScanFileNameLineEdit.setText("<imported>")
            
    @Slot()
    @safewrapper
    def _slot_importOptionsFromWorkspace(self):
        vars_ = self.importWorkspaceData([ScanData, dict],
                                        title="Import Options",
                                        single=True)
        
        if len(vars_):
            options = vars_[0]
            
            if isinstance(options, ScanData):
                options = options.analysisOptions
                
            self.scanDataOptions = options
            signalblockers = [QtCore.QSignalBlocker(w) for w in (self.optionsFileNameLineEdit,)]
            self.optionsFileNameLineEdit.setText("<imported>")
            
    @Slot()
    @safewrapper
    def _slot_importEphysFromWorkspace(self):
        vars_ = self.importWorkspaceData([ScanData, neo.Block, neo.Segment, 
                                          neo.AnalogSignal, tuple, list],
                                        title="Import electrophysiology",
                                        single=False)
        if len(vars_):
            if len(vars_) == 1:
                if isinstance(vars_[0], ScanData):
                    self._ephys_ = vars_[0].electrophysiology
                    
                elif isinstance(vars_[0], neo.Block):
                    self._ephys_ = vars_[0]
                    
                elif isinstance(vars_[0], neo.Segment):
                    self._ephys_ = neo.Block()
                    self._ephys_.segments[:] = vars_[0]
                    
                elif isinstance(vars_[0], (tuple, list)) and len(vars_[0]):
                    if all([isinstance(v, neo.Segment) for v in vars_[0]]):
                        self._ephys_ = neo.Block()
                        self._ephys_.segments[:] = vars_[0][:]
                        
                    elif all([isinstance(v, neo.Block) for v in vars_[0]]):
                        self._ephys_ = concatenate_blocks(*vars_[0])
                        
                    else:
                        self.errorMessage("PrairieView Importer", "Import electrophysiology: \nCannot import from data %s which is %s" % (vars_[0], type(vars_[0].__name__)))
                        return
                    
                else:
                    self.errorMessage("PrairieView Importer", "Import electrophysiology: \nCannot import from data %s which is %s" % (vars_[0], type(vars_[0].__name__)))
                    return
                    
            elif len(vars_) > 1:
                if all([isinstance(v, neo.Segment) for v in vars_]):
                    self._ephys_ = neo.Block()
                    self._ephys_.segments[:] = vars_[:]
                    
                elif all([isinstance(v, neo.Block) for v in vars_]):
                    self._ephys_ = concatenate_blocks(*vars_)
                    
                else:
                    self.errorMessage("PrairieView Importer", "Import electrophysiology: \nExpecting a sequnce of neo.Segment or neo.Block objects")
                    return
            
            signalblockers =[QtCore.QSignalBlocker(w) for w in (self.ephysFileNameLineEdit,)]
            self.ephysFileNameLineEdit.setText("<imported>")
            
    @Slot()
    @safewrapper
    def _slot_importProtocolFromWorkspace(self):
        vars_ = self.importWorkspaceData([ScanData, TriggerProtocol, tuple, list],
                                         title="Import Protocol",
                                         single=False)
        
        if len(vars_):
            if len(vars_) == 1:
                if isinstance(vars_[0], ScanData):
                    self.triggerProtocols[:] = vars_[0].triggerProtocols[:]
                    
                elif isinstance(vars_[0], (tuple, list)) and all([isinstance(v, TriggerProtocol) for v in vars_[0]]):
                    self.triggerProtocols[:] = vars_[0][:]
                    
                elif isinstance(vars_[0], TriggerProtocol):
                    self.triggerProtocols = [vars_[0]]
                    
                else:
                    self.errorMessage("PrairieView Importer", "Expecting a ScanData, a TriggerProtocol or a sequence of TriggerProtocol objects; got %s instead" % vars_[0])
                    return
                    
            else:
                if all([isinstance(v, TriggerProtocol) for v in vars_]):
                    self.triggerProtocols[:] = vars_[:]
                    
                else:
                    self.errorMessage("PrairieView Importer", "Expecting a multiple selection of TriggerProtocol objects; got %s instead" % vars_)
                    return
        
            signalblockers = [QtCore.QSignalBlocker(w) for w in (self.triggerProtocolFileNameLineEdit,)]
            self.cachedProtocolFileName = self.triggerProtocolFileNameLineEdit.text()
            self.triggerProtocolFileNameLineEdit.setText("<imported>")
            
    @Slot()
    def _slot_addProtocol(self):
        newProtocol = TriggerProtocol()
        if self._scandata_ is not None:
            segments_with_protocol = [p.segmentIndices() for p in self._scandata_.triggerProtocols]
            
            data_segments = [k for k in range(self._scandata_.scansFrames)]
                
    @safewrapper
    def loadPVScan(self, fileName) -> bool:
        if len(fileName) and os.path.isfile(fileName):
            mime_type, file_type, encoding = pio.getMimeAndFileType(fileName)
            
            if "xml" in mime_type:
                pvscanDoc = pio.loadXMLFile(fileName)
                pvscanAttrs = xmlutils.attributesToDict(pvscanDoc.documentElement)
                pvVersion = pvscanAttrs.get("version", None)
                if not isinstance(pvVersion, str) or len(pvVersion.strip()) == 0:
                    scipywarn(f"Invalid 'version' attribute ({pvVersion})")
                    return False
                
                if pvVersion < "5.5":
                    self._pvscan_ = PVScan(fileName)
                else:
                    pvEnvFile = pathlib.Path(pathlib.Path(fileName).stem + ".env")
                    if not pvEnvFile.is_file():
                        fn, _ = self.chooseFile("Select PrairieView Environment File",
                                                    ".env")
                        if len(fn.strip()) == 0:
                            scipywarn(f"PVScan acquired with PrairieView version {pvVersion} require an 'environment' file (*.env)")
                            return False
                            
                        pvEnvFile = pathlib.Path(fn)
                        
                    self._pvscan_ = PVScan(fileName, pvEnvFile)
                
            else:
                self.errorMessage("PrairieView Import - Prairiew View Scan file", "%s is not an XML file" % self.pvScanFileName)
                return False
            
            tempDataVarName = os.path.splitext(os.path.basename(fileName))[0]
            if len(self.scanDataVarName.strip()) == 0:
                self.scanDataVarName = strutils.str2symbol(tempDataVarName)
            
            if len(self.dataName.strip()) == 0:
                #self.dataName = self.scanDataVarName
                self.dataNameLineEdit.setText(self.scanDataVarName)
                
            if fileName != self.pvScanFileName:
                signalblockers = [QtCore.QSignalBlocker(w) for w in (self.pvScanFileNameLineEdit, self.dataNameLineEdit)]
                self.pvScanFileName = fileName
                self.pvScanFileNameLineEdit.setText(self.pvScanFileName)
                
            return True
        
        else:
            self.errorMessage("PrairieView Import", "File %s not found" % fileName)
        
        return False
    
    @safewrapper
    def loadEphys(self, fileNamesList): # TODO 2024-07-28 09:49:36 streamline
        if len(fileNamesList):
            fileNamesList = [f for f in fileNamesList if len(f.strip())]
            if len(fileNamesList) == 0:
                return
            
            bad_files = [f for f in fileNamesList if not os.path.isfile(f)]
            if len(bad_files):
                self.errorMessage("PrairieView Importer", "The following files: %s could not be found" % os.pathsep.join(fileNamesList))
                return False
            
            blocks = list()
            
            if all([any([s in pio.getMimeAndFileType(f)[0] for s in ("axon", "abf", "atf")]) for f in fileNamesList]):
                # NOTE 2020-10-06 16:24:08
                # this is simple: each axon file generates one block
                blocks[:] = [pio.loadAxonFile(f) for f in fileNamesList]
                
            elif all(["pickle" in pio.getMimeAndFileType(f)[0] for f in fileNamesList]):
                # CAUTION 2020-10-06 16:22:25
                # when loading pickle files, they can contain either:
                # a) one block with one segment for each sweep => concatenate them
                # b) a single block with as many segments as sweeps => use ths first 
                # block and discard the others
                blocks[:] = [pio.loadPickleFile(f) for f in fileNamesList]
                
            else:
                self.errorMessage("PrairieView Importer", "Electrophysiology files\nExpecting Axon or Pickle files for electrophysiology")
                return False
                    
            if len(blocks):
                if all([isinstance(b, neo.Block) for b in blocks]):
                    self._ephys_ = set_relative_time_start(concatenate_blocks(*blocks))
                    self.cachedEvents = [s.events for s in self._ephys_.segments]
                    return True
                    
                elif all([isinstance(b, neo.Segment) for b in blocks]):
                    self._ephys_ = neo.Block()
                    self._ephys_.segments[:] = blocks[:]
                    self.cachedEvents = [s.events for s in self._ephys_.segments]
                    
                    return True
                    
                else:
                    self.errorMessage("PrairieView Importer", "Electrophysiology files must contain neo.Blocks or individual neo.Segments")
                    return False
                
                # WARNING 2024-07-27 09:42:55
                # concatenate_blocks does not reset the signals start time to 0
                # anymore - this is because the correct times are needed for 
                # establishing the correct temporal succession of the records in
                # post hoc analyses
                #
                # This MUST be taken into account in scandata analysis, downstream.
                
        else:
            return False
    
    @safewrapper
    def loadOptions(self, fileName): # TODO 2024-07-28 09:49:36 streamline
        # if len(fileName) and os.path.isfile(fileName) and "pickle" in pio.getMimeAndFileType(fileName)[0]:
        if len(fileName) == 0 or not os.path.isfile(fileName) or pio.getMimeAndFileType(fileName)[0] != "application/x-hdf":
            self.errorMessage("PrairieView Importer", f"Load options from file:\n{fileName} is not a suitable file" )
            return False
            
        self.scanDataOptions = pio.loadHDF5File(fileName)
        
        if fileName != self.optionsFileName:
            signalblockers = [QtCore.QSignalBlocker(w) for w in (self.optionsFileNameLineEdit,)]
            self.optionsFileName = fileName
            self.optionsFileNameLineEdit.setText(self.optionsFileName)
            
        return True
        
    @safewrapper
    def loadProtocols(self, fileName):
        mime_type = pio.getMimeAndFileType(fileName)[0]
        
        if len(fileName) and os.path.isfile(fileName) and "pickle" in mime_type:
            tp = pio.loadPickleFile(fileName)
            
            if isinstance(tp, (tuple, list)) and all([isinstance(v, TriggerProtocol) for v in tp]):
                self.triggerProtocols = tp
                
                if fileName != self.protocolFileName:
                    signalblockers = [QtCore.QSignalBlocker(w) for w in (self.triggerProtocolFileNameLineEdit,)]
                    self.protocolFileName = fileName
                    self.triggerProtocolFileNameLineEdit.setText(self.protocolFileName)
                
                return True        
            
            else:
                self.errorMessage("PrairieView Importer", "Load protocols from file:\nNo trigger protocols found in pickle file %s " % fileName)
                return False
        
        else:
            self.errorMessage("PrairieView Importer", "Load protocols from file:\nExpecting a Pickle file; got %s which is a %s instead" % (fileName, mime_type))
            return False
        
    @Slot()
    def done(self, value):
        r"""Generates ScanData object (if accepted) and closes the dialog.
        value: a QtWidgets.QDialog.DialogCode (Accepted = 1, Rejected = 2)
        NOTE: Clients need to connect custom slots to this dialog's accepted(),
        rejected(), or finished(int) signals
        """
        # print(f"Slot {self.__class__.__name__}.done")
        if value == QtWidgets.QDialog.Accepted:
            self.slot_generateScanData()
            
        super().done(value)        
        
    @Slot()
    def accept(self):
        # NOTE: 2021-04-16 11:24:35 this calls done(QDialog.Accepted)
        super().accept()
        
    @Slot()
    def reject(self):
        # NOTE: 2021-04-16 11:24:48 this calls done(QDialog.Rejected)
        super().reject()
        
    @Slot()
    @safewrapper
    def slot_generateScanData(self):
        r"""Creates a ScanData object based on the loaded data files.
        The created ScanData object is available as the property `scandata` or 
        `scanData`. If self.auto_export is True, the ScanData object is also 
        exported to the Scipyen workspace.
        """
        # print(f"{self.__class__.__name__}.slot_generateScanData")
        if isinstance(self._pvscan_, PVScan):
            self._scandata_ = self._pvscan_.scandata()
            
        if isinstance(self._scandata_, ScanData):
            if len(self.dataName):
                self._scandata_.name = self.dataName
                
            #print("ephys", type(self._ephys_))
            if isinstance(self._ephys_, neo.Block):
                self._scandata_.electrophysiology = self._ephys_
                
                self._scandata_.electrophysiology.name = self._scandata_.name
                for k, segment in enumerate(self._scandata_.electrophysiology.segments):
                    if not isinstance(segment.name, str) or len(segment.name.strip()) == 0:
                        segment.name = f"Sweep {k}"
                
            if isinstance(self.scanDataOptions, (ScanDataOptions, dict)):
                self._scandata_.analysisOptions = self.scanDataOptions
                
            if isinstance(self.triggerProtocols, (tuple, list)) and all([isinstance(v, TriggerProtocol) for v in self.triggerProtocols]):
                self._scandata_.triggers = self.triggerProtocols
                
            if self.auto_export:
                self._scipyenWindow_.assignToWorkspace(self.scanDataVarName, self.scanData)
            
    def updateProtocolEditor(self):
        self.protocolEditorDialog.triggerProtocols = self.triggerProtocols
        
        
    @property
    def ephysdata(self):
        return self._ephys_
    
    @property
    def pvscan(self):
        return self._pvscan_
    
    @property
    def scanData(self):
        return self._scandata_
    
    @property
    def scandata(self):
        r"""Alias to self.scanData
        """
        return self.scanData

def loadPrairieViewXML(filePath:typing.Union[str, pathlib.Path]) -> object:
    filePath = pathlib.Path(filePath).absolute()
    ret = pio.loadXML(filePath)
    if ret.documentElement.tagName != "PVScan":
        raise ValueError("Not a PVScan experiment file")
    # augument with the full path to this file
    doc_filepath = ret.createElement("DocPath")
    doc_filepath.setAttribute("value", filePath.as_posix())
    ret.documentElement.appendChild(doc_filepath)
    return ret

