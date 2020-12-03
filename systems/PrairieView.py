# -*- coding: utf-8 -*-
"""Import routines for PrairieView data
"""
#### BEGIN core python modules
import os, sys, traceback, warnings, datetime, time, mimetypes, io, typing
from enum import Enum, IntEnum #, unique
from collections import OrderedDict
import concurrent.futures
import threading
#import xml
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import quantities as pq
import neo
import vigra
#import vigra.pyqt.quickdialog as quickdialog
#### END 3rd party modules

#### BEGIN pict.core modules
from core.utilities import safeWrapper
from core.traitcontainers import DataBag
from core.triggerprotocols import TriggerProtocol
import core.xmlutils as xmlutils
import core.strutils as strutils
import core.datatypes as dt
from core.neoutils import (concatenate_blocks, concatenate_blocks2, 
                           concatenate_signals,)

#### END pict.core modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

#### BEGIN pict.gui modules
#from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5 import (QtCore, QtWidgets, QtGui,)
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUiType as __loadUiType__ 
#from gui import *
#from gui import __loadUiType__ as __loadUiType__
from gui import resources_rc as resources_rc
#from gui import pyqtSignal as pyqtSignal
#from gui import pyqtSlot as pyqtSlot
from gui import quickdialog as quickdialog
from gui import pictgui as pgui
from gui.workspacegui import WorkspaceGuiMixin
import gui.signalviewer as sv
#### END pict.gui modules

from imaging import (imageprocessing as imgp, axisutils, axiscalibration,)
from imaging.scandata import (ScanData, ScanDataOptions, scanDataOptions,)

from imaging.axisutils import (axisTypeFlags, defaultAxisTypeName, 
                               defaultAxisTypeSymbol, defaultAxisTypeUnits,)
from imaging.axiscalibration import AxisCalibration

import ephys.ephys as ephys

__module_path__ = os.path.abspath(os.path.dirname(__file__))

__UI_PVImporterDialog__, __QDialog__ = __loadUiType__(os.path.join(__module_path__,"PVImporterDialog.ui"), from_imports=True, import_from="gui")
__UI_PrairieImporter, __QDialog__ = __loadUiType__(os.path.join(__module_path__, "PrairieImporter.ui"), from_imports=True, import_from="gui")

# TODO:
# factor out common functions in a superclass

""" NOTE: 2017-09-22 09:28:23
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

# TODO: work out other linescan modes
## FIXME: for linescans other than Freehand coordinates is empty!
# NOTE: circle is converted into freehand!
class PVLinescanDefinition(object):
    def __init__(self, node, parent=None):
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "PVLinescanDefinition":
            raise ValueError("Expecting an element node named 'PVLinescanDefinition")
        
        self.__parent__ = None
        
        if parent is not None:
            if isinstance(parent, PVSequence) and parent.typename == "Linescan":
                self.__parent__ = parent
                
            else:
                raise TypeError("Parent of a PVLinescanDefinition can only be None or a PVSequence of Linescan type")
        
        self.__attributes__ = dict()
        
        if node.attributes is not None:
            for k in node.attributes.values():
                try:
                    val=eval(k.value)
                except:
                    val = k.value
                    
                if k.name == "mode":
                    self.__attributes__[k.name] = PVLinescanMode[val].value
                else:
                    self.__attributes__[k.name] = val
                
        if self.__attributes__["mode"] == PVLinescanMode.freeHand:
            freehandnodes = node.getElementsByTagName("Freehand")
            
            if len(freehandnodes) > 0:
                self.__coordinates__ = [(eval(n.attributes.getNamedItem("x").value), eval(n.attributes.getNamedItem("y").value)) for n in freehandnodes]
            else:
                self.__coordinates__ = [] # TODO/FIXME what is a good default here?
                    
        #elif self.__dict__["mode"] == PVLinescanMode.straightLine.value:
        elif self.__attributes__["mode"] == PVLinescanMode.straightLine:
            linenodes = node.getElementsByTagName("Line")
            if len(linenodes) > 0:
                if len(linenodes) == 1:
                    self.__coordinates__ = [(eval(linenodes[0].attributes.getNamedItem("startPixelX").value), \
                                             eval(linenodes[0].attributes.getNamedItem("startPixelY").value)),\
                                            (eval(linenodes[0].attributes.getNamedItem("stopPixelX").value), \
                                             eval(linenodes[0].attributes.getNamedItem("startPixelY").value))]
                else:
                    self.__coordinates__ = [((eval(n.attributes.getNamedItem("startPixelX").value), \
                                            eval(n.attributes.getNamedItem("startPixelY").value)), \
                                            (eval(n.attributes.getNamedItem("stopPixelX").value), \
                                            eval(n.attributes.getNamedItem("startPixelY").value))) for n in linenodes]
                    
        else: # TODO code for other linescan modes
            self.__coordinates__ = [] # for now!
            
        self.line_length = eval(node.getElementsByTagName("Line")[0].attributes.getNamedItem("lineLength").value)
        
    @property
    def parent(self):
        """The parent PVSequence object, or None
        """
        return self.__parent__
    
    @parent.setter
    def parent(self, val):
        if (isinstance(val, PVSequence) and parent.typename == "Linescan") or val is None:
            self.__parent__ = val
            
        else:
            raise TypeError("Parent  of a PVLinescanDefinition can only be None or a PVSequence object of Linescan type")
    
    @property
    def sequence(self):
        """Alias for parent
        """
        return self.parent
    
    @sequence.setter
    def sequence(self, val):
        self.parent=val
    
    @property
    def attributes(self):
        return self.__attributes__
    
    @property
    def mode(self): # read only
        return self.__attributes__["mode"]
    
    @property
    def coordinates(self):
        return self.__coordinates__
    
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
        if len(self.__attributes__) > 0:
            for k,v in self.__attributes__.items():
                ret.append(" %s = %s\n" % (k, v))
        ret.append(" coordinates (x, y):\n ")
        for c in self.__coordinates__:
            ret.append("  %s\n" % (c.__str__()))
        ret.append(" length = %g\n" % (self.line_length))
        
        return "".join(ret)
    
    def metadata(self):
        metadata = dict()
        metadata["attributes"] = self.__attributes__
        metadata["coordinates"] = self.__coordinates__
        metadata["line_length"] = self.line_length
        
        return DataBag(metadata)
        

class PVLaser(object):
    def __init__(self, node, parent=None):
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "Laser":
            raise ValueError("Expecting an element node named 'Laser'")
        
        self.__parent__ = None
        
        if parent is not None:
            if isinstance(parent, PVSystemConfiguration):
                self.__parent__ = parent
                
            else:
                raise TypeError("Parent can only be None on a PVSystemConfiguration object")

        #if node.attributes is not None:
            #self.__dict__.update(xmlutils.attributesToDict(node))
        ##else:
            ##self.__attributes__ = dict()
            ##self.__dict__.update(dict([(k.name, k.value) for k in node.attributes.values()]))
            
        if node.attributes is not None:
            self.__attributes__ = DataBag(xmlutils.attributesToDict(node))
        else:
            self.__attributes__ = DataBag(dict())
            #self.__dict__.update(dict([(k.name, k.value) for k in node.attributes.values()]))
            
    @property
    def parent(self):
        """The parent PVSystemConfiguration object, or None
        """
        return self.__parent__
    
    @parent.setter
    def parent(self, val):
        if isinstance(val, (None, PVSystemConfiguration)):
            self.__parent__ = val
            
        else:
            raise TypeError("Parent can only be None or a PVSystemConfiguration object")
    
    @property
    def attributes(self):
        return self.__attributes__
    
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = ["Laser:\n"]
        ret += [" %s = %s\n" % (i[0], i[1]) for i in self.__attributes__.items()]
        
        return "".join(ret)

class PVSystemConfiguration(object):
    def __init__(self, node, parent=None):
        #print("PVSystemConfiguration.__init__: node = %s (node name: %s)" % (node, node.nodeName))
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "SystemConfiguration":
            raise ValueError("Expecting an element node named 'SystemConfiguration'")

        self.__parent__ = None
        
        if parent is not None:
            if isinstance(parent, PVScan):
                self.__parent__ = parent
                
            else:
                raise TypeError("Parent of a PVSystemConfiguration can only be one or a PVScan object")

        if node.attributes is not None:
            self.__attributes__ = DataBag(xmlutils.attributesToDict(node))
            
        else:
            self.__attributes__ = DataBag(dict())
        
        lasers = node.getElementsByTagName("Laser")
        
        self.lasers = [PVLaser(l) for l in lasers]
        
    @property
    def parent(self):
        """The parent PVScan object, or None
        """
        return self.__parent__
    
    @parent.setter
    def parent(self, val):
        if isinstance(val, (type(None), PVScan)):
            self.__parent__ = val
            
        else:
            raise TypeError("Parent of a PVSystemConfiguration can only be None or a PVScan object")
    
    @property
    def scan(self):
        """Alias for parent
        """
        return self.parent
    
    @scan.setter
    def scan(self, val):
        self.parent=val
    
    @property
    def attributes(self):
        return self.__attributes__
    
    def as_dict(self):
        ret = dict()
        ret.update(self.attributes)
        ret["lasers"] = [laser.attributes for laser in self.lasers]
        
        return DataBag(ret)
    
    #def laser(self, index):
        #return self.lasers[index]

    #@property
    #def numLasers(self):
        #return len(self.lasers)
        
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = ["System Configuration:"]
        ret += ["%s = %s" % (i[0], i[1]) for i in self.__attributes__.items()]
        #ret += ["%s = %s" % (i[0], i[1]) for i in self.__dict__.items()]
        for l in self.lasers:
            ret.append(l.__str__())

        return "\n".join(ret)
        
class PVStateShard(object):
    def __init__(self, node, parent=None):
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "PVStateShard":
            raise ValueError("Expecting an element node 'PVStateShard")

        keyNodes = node.getElementsByTagName("Key")
        
        self.__parent__ = None
        
        if parent is not None:
            if isinstance(parent, PVFrame):
                self.__parent__ = parent
                
            else:
                raise TypeError("Parent of a PVStateShard can only be None or a PVFrame object")
        
        self.__attributes__ = DataBag(dict())

        for n in keyNodes:
            try:
                self.__attributes__[n.getAttribute("key")] = eval(n.getAttribute("value"))
            except:
                self.__attributes__[n.getAttribute("key")] = n.getAttribute("value")
                
    @property
    def parent(self):
        """The parent PVFrame object, or None
        """
        return self.__parent__
    
    @parent.setter
    def parent(self, val):
        if isinstance(val, (type(None), PVFrame)):
            self.__parent__ = val
            
        else:
            raise TypeError("Parent of a PVStateShard can only be None or a PVFrame object")
        
    @property
    def frame(self):
        """Alias for parent
        """
        return self.parent
    
    @frame.setter
    def frame(self, val):
        self.parent=val
    
    @property
    def attributes(self):
        return self.__attributes__
    
    @property # dictionary view
    def keys(self):
        """dict_view of the keys
        """
        #return self.__attributes__.keys()
        return self.__dict__.keys()
    
    @property # dictionary view
    def items(self):
        """dict_view of the items
        """
        #return self.__attributes__.items()
        return self.__dict__.items()
    
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        ret = [" State:\n"]
        ret += ["  %s = %s\n" % (i[0], i[1]) for i in self.__attributes__.items()]
        #ret += ["  %s = %s\n" % (i[0], i[1]) for i in self.__dict__.items()]
        #ret.append("\n")
        
        return "".join(ret)

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
class PVFrame(object):
    def __init__(self, node, parent=None):
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "Frame":
            raise ValueError("Expecting an element node named 'Frame'")
        
        self.__parent__ = None
        
        if parent is not None:
            if isinstance(parent, PVSequence):
                self.__parent__ = parent
                
            else:
                raise TypeError("Parent of a PVFrame can only be None or a PVSequence")
        
        #if node.attributes is not None:
            #self.__dict__.update(xmlutils.attributesToDict(node))
        ##else:
            ##self.__attributes__ = dict()
            
        if node.attributes is not None:
            self.__attributes__ = DataBag(xmlutils.attributesToDict(node))
        else:
            self.__attributes__ = DataBag(dict())
            
        self.__files__ = [DataBag(xmlutils.attributesToDict(n)) for n in node.getElementsByTagName("File")]
        
        #for f in self.__files__:
            #if not "source" in f.keys():
                #f["source"] = ""
        
        ep = node.getElementsByTagName("ExtraParameters")
        
        if len(ep) > 0:
            self.ExtraParameters = [DataBag(xmlutils.attributesToDict(n)) for n in ep]
        else:
            self.ExtraParameters = None
        
        self.__stateshard__ = PVStateShard(node.getElementsByTagName("PVStateShard")[0], \
                                            parent=self)
        
        self.__mergeChannelsOnOutput__ = False
        
        
    @property
    def parent(self):
        """The parent PVSequence object, or None
        """
        return self.__parent__
    
    @parent.setter
    def parent(self, val):
        if isinstance(val, (type(None), PVSequence)):
            self.__parent__ = val
            
        else:
            raise TypeError("Parent of a PVFrame can only be None or a PVSequence object")
        
    @property
    def sequence(self):
        """Alias for parent
        """
        return self.parent
    
    @sequence.setter
    def sequence(self, val):
        self.parent=val
    
    @property
    def attributes(self):
        return self.__attributes__
        
    @property
    def channels(self):
        """Returns the number of channels
        
        To obtain the channel data use "files" property.
        """
        return len(self.__files__)
    
    @property
    def files(self):
        return self.__files__
    
    @property
    def state(self):
        return self.__stateshard__
    
    @property
    def multiBandOutput(self):
        """If True, the () operator reads this frame's files as a multiband image.
        This requires that each file corresponds to one channel and that all files 
        have a channel axis. Only applies when there are between 2 and 4 files per frame.
        """
        return self.__mergeChannelsOnOutput__
    
    @multiBandOutput.setter
    def multiBandOutput(self, val):
        """Permanently sets the state of the multiBandOutput property to val.
        
        Parameters:
        "val: boolean
        """
        self.__mergeChannelsOnOutput__ = val
    
    def mergeChannels(self, val=True, filepath=None):
        """Coerce reading the files as a multiband image.
        
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
        v = self.__mergeChannelsOnOutput__
        self.__mergeChannelsOnOutput__= True
        try:
            data = self.__call__(filepath=filepath)
        except Exception as e:
            self.__mergeChannelsOnOutput__ = v
            raise e
        
        self.__mergeChannelsOnOutput__ = v
        
        return data
    
    def __call__(self, filepath=None):
        """Reads the specified files and returns a vigra array corresponding to
        the image files that compose the frame.
        
        Keyword parameter:
        ==================
        
        filepath = str or None (default); when given, the image filenames
        will be prepended with the value of path to create absolute file names.
        
        This value overrides any value from the parent PVSequence (when the latter
        is not None).
        
        """
        
        #metadata to be retrieved from the associated PVStateShard
        #=================================
        #Some of these parameters whe present, are passed to PictArray constructor
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
        
        # NOTE: 2017-10-18 22:37:05
        # make sure the channel numbers are in increasing order
        channelIndex = [f["channel"] for f in self.files]
        
        mdata = self.metadata()
        
        if filepath is None:
            if self.parent is not None:
                filepath = self.parent.filepath
        
        frameData = list()
        
        sourceData = list()
        
        for k in range(len(mdata["files"])):
            if filepath is not None:
                fdata = pio.loadImageFile(os.path.join(filepath, self.files[k]["filename"]))
            
            else:
                fdata = pio.loadImageFile(self.files[k]["filename"])
                
            if fdata.ndim == 2 and fdata.channelIndex == fdata.ndim:
                fdata.insertChannelAxis() # make sure there is a channel axis
                
            # NOTE: 2018-06-03 22:15:10
            # axis_0_info is the AxisInfo object for the 1st (spatial) dimension (axis)
            axis_0_info = fdata.axistags[0]
            axis_0_cal  = AxisCalibration(axis_0_info,
                                                    units=pq.um,
                                                    origin=0.0,
                                                    resolution=self.state.attributes["micronsPerPixel_XAxis"],
                                                    axisname=defaultAxisTypeName(axis_0_info))
            
            #print("PVFrame.__call__() axis_0_cal", axis_0_cal)
            
            axis_0_info = axis_0_cal.calibrateAxis(axis_0_info)
            
            
            # NOTE: 2018-06-03 22:15:54
            # axis_1_info is the AxisInfo objects for the 2nd (spatial or temporal) dimension (axis)
            #
            # what type of PVSequence does this frame belong to?
            # we need to know this in order to set appropriate axis information
            if self.parent is not None and self.parent.type == PVSequenceType.Linescan:
                axis_1_info = vigra.AxisInfo(key="t", 
                                             typeFlags=vigra.AxisType.Time, 
                                             resolution = self.state.attributes["scanlinePeriod"])
                
                axis_1_cal  = AxisCalibration(axis_1_info,
                                                        units=pq.s,
                                                        origin=0.0,
                                                        resolution=self.state.attributes["scanlinePeriod"],
                                                        axisname=defaultAxisTypeName(axis_1_info))
                
                axis_1_info = axis_1_cal.calibrateAxis(axis_1_info)
                
            else:
                axis_1_info = fdata.axistags[1]
                
                axis_1_cal = AxisCalibration(axis_1_info,
                                                       units = pq.um,
                                                       origin=0.0,
                                                       resolution = self.state.attributes["micronsPerPixel_YAxis"],
                                                       axisname=defaultAxisTypeName(axis_1_info))
                
                axis_1_info = axis_1_cal.calibrateAxis(axis_1_info)
            
            # NOTE: 2018-06-03 22:16:26
            # axis_2_info is the AxisInfo object for 3rd dimension (channel axis !!!)
            #
            
            if fdata.channelIndex == fdata.ndim:
                # NOTE: 2018-08-01 16:43:58
                # make sure there IS a channel axis
                axis_2_info = vigra.AxisInfo.c(description=self.files[k]["channelName"])
                
            else:
                axis_2_info = fdata.axistags["c"]
            
            axis_2_cal = AxisCalibration(axis_2_info, 
                                                   units = defaultAxisTypeUnits(axis_2_info),
                                                   origin=0.0,
                                                   resolution = 1.0,
                                                   axisname=self.files[k]["channelName"])
            
            axis_2_cal.setChannelCalibration(0, name=self.files[k]["channelName"],
                                             origin=0.0,
                                             resolution = 1.0)
                                                   
            
            axis_2_info = axis_2_cal.calibrateAxis(axis_2_info)
            
            newaxistags = vigra.AxisTags(axis_0_info, axis_1_info, axis_2_info)
            
            frame = vigra.VigraArray(fdata, axistags=newaxistags)
            
            channel_axis_info = frame.axistags["c"]
            
            frameData.append(frame)
        
            if "source" in self.files[k] and all(self.files[k]["source"]):
                # NOTE: 2018-06-03 22:18:03
                # axis_x_info are AxisInfo objects as mentioned in above NOTE comments
                if filepath is not None:
                    sdata = pio.loadImageFile(os.path.join(filepath, self.files[k]["source"]))
                    
                else:
                    sdata = pio.loadImageFile(self.files[k]["source"])
                    
                if sdata.ndim == 2 and sdata.channelIndex == sdata.ndim:
                    sdata.insertChannelAxis() # make sure there is a channel axis
                    
                axis_0_info = sdata.axistags[0]
                axis_0_cal = AxisCalibration(axis_0_info,
                                                       units=pq.um, 
                                                       origin=0.0, 
                                                       resolution=self.state.attributes["micronsPerPixel_XAxis"],
                                                       axisname=defaultAxisTypeName(axis_0_info))
                
                axis_0_info = axis_0_cal.calibrateAxis(axis_0_info)
                
                axis_1_info = sdata.axistags[1]
                axis_1_cal = AxisCalibration(axis_1_info,
                                                       units=pq.um, 
                                                       origin=0.0, 
                                                       resolution=self.state.attributes["micronsPerPixel_YAxis"],
                                                       axisname=defaultAxisTypeName(axis_1_info))
                
                axis_1_info = axis_1_cal.calibrateAxis(axis_1_info)
                
                axis_2_info = sdata.axistags["c"]
                
                axis_2_cal = AxisCalibration(axis_2_info,
                                                       units=defaultAxisTypeUnits(axis_2_info), 
                                                       origin=0.0, 
                                                       resolution=1.0)
                axis_2_cal.setChannelCalibration(0, name = self.files[k]["channelName"],
                                                 origin=0.0, 
                                                 resolution=1.0)
                
                axis_2_cal = axis_2_cal.calibrateAxis(axis_2_info)
                
                newaxistags = vigra.AxisTags(axis_0_info, axis_1_info, axis_2_info)
                
                source = vigra.VigraArray(sdata, axistags=newaxistags)
                
                sourceData.append(source)
                
        if len(sourceData) == 0:
            sourceData = None
            
        if len(self.files) > 1 and len(self.files) <= 4:
            # this could be returned as a multiband (multichannel) array 
            # if so requested
            
            # NOTE: 2017-11-06 19:40:44
            # concatenation will lose the image metadata
            # therefore we need to collect it then pass it back onto the result
            if self.__mergeChannelsOnOutput__:
                channels = [int(self.files[k]["channel"]) for k in range(len(self.files))]
                channel_names = [self.files[k]["channelName"] for k in range(len(self.files))]
                
                mergedFrameData = imgp.concatenateImages(*frameData, axis="c", allowConcatenationFor=("origin", "resolution"))
                
                merged_channel_axis_info = mergedFrameData.axistags["c"]
                
                merged_channel_axis_cal = AxisCalibration(merged_channel_axis_info,
                                                                    axisname = defaultAxisTypeName(merged_channel_axis_info))
                
                for channel in channels:
                    if channel not in merged_channel_axis_cal.channelIndices:
                        merged_channel_axis_cal.addChannel(channel)
                        
                    merged_channel_axis_cal.setChannelName(channel, channel_names[channels.index(channel)])
                
                if sourceData is not None:
                    mergedSourceData = imgp.concatenateImages(*sourceData, axis="c")
                    
                    merged_source_channel_axis_info = mergedSourceData.axistags["c"]
                    
                    merged_source_channel_axis_cal = AxisCalibration(merged_source_channel_axis_info,
                                                                               axisname = defaultAxisTypeName(merged_source_channel_axis_info))
                    
                    for channel in channels:
                        if channel not in merged_source_channel_axis_cal.channeIndices:
                            merged_source_channel_axis_cal.addChannel(channel)
                        merged_source_channel_axis_cal.setChannelName(channel, channel_names[channels.index(channel)])
                        
                else:
                    mergedSourceData = None
                    
                return mergedFrameData, mergedSourceData
                    
        return frameData, sourceData
    
    def metadata(self):
        """Returns metadata associated with this frame.
        """
        
        channelIndex = [f["channel"] for f in self.files]
        
        #print(channelIndex)
        
        orderedIndex = np.argsort(channelIndex)
        
        #print(orderedIndex)
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
            
        for k in self.__attributes__.keys():
            ret.append("  %s = %s\n" % (k, self.__attributes__[k]))
            
        ret.append(" Files:\n")
        for f in self.__files__:
            for t in f.keys():
                ret.append("  %s = %s\n" % (t, f[t]))
                
        ret.append(self.__stateshard__.__str__())
        
        if self.ExtraParameters is not None:
            ret.append(" Extra Parameters:\n")
            for ep in self.ExtraParameters:
                for i in ep.items():
                    ret.append("  %s = %s\n" % (i[0], i[1]))
            
        return "".join(ret)
        
        
# NOTE: 2017-08-03 09:24:20
# TODO: make the instances sortable by cycle number (found in attributes
class PVSequence (object):
    """Sequence data structures are common enough to guarantee the 
    need for a new data type here
    """
    def __init__(self, node, parent=None):
        if node.nodeType != xmlutils.xml.dom.Node.ELEMENT_NODE or node.nodeName != "Sequence":
            raise ValueError("Expecting an element node named 'Sequence'")
        
        self.__mergeChannelsOnOutput__ = False
        
        self.__parent__ = None
        
        if parent is not None:
            if isinstance(parent, PVScan):
                self.__parent__ = parent
            else:
                raise TypeError("Parent of a PVSequence can only be None or a PVScan object")
        
        self.__attributes__ = DataBag(dict())
        
        if node.attributes is not None:
            for k in node.attributes.values():
                try:
                    val=eval(k.value)
                except:
                    val = k.value
                    
                if k.name == "type": 
                    self.__attributes__["sequencetype"] = PVSequenceType[val.split()[0]].value
                else:
                    self.__attributes__[k.name] = val
                    
            self.__attributes__["sequencetypename"] = PVSequenceType(self.__attributes__["sequencetype"]).name
        
        if self.__attributes__["sequencetype"] == PVSequenceType.Linescan:
            self.__definition__ = PVLinescanDefinition(node.getElementsByTagName("PVLinescanDefinition")[0], \
                                                        parent=self)
            
            self.__syncZAxis__ = DataBag(xmlutils.attributesToDict(node.getElementsByTagName("PVLinescanSynchZ")[0]))
            
        else: # TODO / FIXME code for other sequence tyes
            self.__definition__ = None
            self.__syncZAxis__ = None
                
        self.frames = [PVFrame(n, parent=self) for n in node.getElementsByTagName("Frame")]
        
    def __len__(self):
        return len(self.frames)
    
    def __call__(self, filepath=None):
        """Load the images from the file(s) define in its frames attribute
        
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
        # or one multi-band image if self.__mergeChannelsOnOutput__ is True 
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
        # axistags management taken care of by imgp.concatenateImages
        
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
                if self.__mergeChannelsOnOutput__:
                    data = self.frames[0].mergeChannels(filepath=filepath) # a tuple of frameData, sourceData
                    
                else:
                    data = self.frames[0](filepath=filepath)# a tuple of frameData, sourceData
                    
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
            if self.__mergeChannelsOnOutput__:
                data = [f.mergeChannels(filepath=filepath) for f in self.frames]# a tuple of frameData, sourceData
                
            #else:
                #data = [f() for f in self.frames]
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
                    frameTimes = [float(f.attributes["absoluteTime"]) for f in self.frames]

                    diffTimes = np.diff(frameTimes) # there will be some jitter

                    framePeriod = float(diffTimes.mean())# * pq.s
                
                    newAxisInfo = vigra.AxisInfo(key="t", typeFlags=vigra.AxisType.Time, \
                                                resolution=framePeriod, \
                                                description=defaultAxisTypeName(axisTypeFlags["t"]))
                    
                    newAxisCal = AxisCalibration(newAxisInfo,
                                                           units=pq.s, 
                                                           origin=float(self.frames[0].attributes["absoluteTime"]), 
                                                           resolution = framePeriod,
                                                           axisname=defaultAxisTypeName(newAxisInfo))
                    
                    newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                    
                else: # Z series
                    #print("PVSequence() ZSeries")
                    # get the Z axis resolution from the frames state
                    z_pos = [float(f.state.attributes["positionCurrent_ZAxis"]) for f in self.frames]
                    z_steps = np.diff(z_pos)
                    
                    if len(z_steps) > 1:
                        if not all(z == z_steps[0] for z in z_steps):
                            raise ValueError("Irregular Z axis sampling not supported")
                        
                    zres = z_steps[0]
                    
                    newAxisInfo = vigra.AxisInfo(key="z", typeFlags=vigra.AxisType.Space,\
                                                resolution=zres, \
                                                description=defaultAxisTypeName(axisTypeFlags["z"]))
                    
                    newAxisCal = AxisCalibration(newAxisInfo,
                                                           units=pq.um, 
                                                           origin=float(self.frames[0].state.attributes["positionCurrent_ZAxis"]), 
                                                           resolution=zres,
                                                           axisname=defaultAxisTypeName(newAxisInfo))
                    
                    newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                
                # NOTE: 2018-08-01 17:03:52
                # see NOTE: 2018-08-01 17:04:06
                channelAxisDim = data[0].axistags.channelIndex
                
                if channelAxisDim == data[0].ndim-1:
                    newAxisDim = channelAxisDim
                    
                else:
                    newAxisDim = data[0].ndim
                    
                #print("insert axis")
                images = [imgp.insertAxis(img, newAxisInfo, newAxisDim) for img in data]
            
                # NOTE: 2017-10-25 00:51:06 source data is None here
                # so we just return None for it
                #print("return, concatenate")
                return imgp.concatenateImages(images, axis=newAxisInfo), None
            
            else: # separate channels
                data = [f(filepath=filepath) for f in self.frames] # for each frame: a tuple of frame data & src data if linescan
                
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
                    
                if self.sequencetype == PVSequenceType.TSeries:
                    framePeriods = [float(f.attributes["absoluteTime"]) for f in self.frames]
                    
                    diffTimes = np.diff(frameTimes) # there will be some jitter

                    framePeriod = float(diffTimes.mean())#framePeriods[0]
                
                    newAxisInfo = vigra.AxisInfo(key="t", typeFlags = vigra.AxisType.Time, \
                                                resolution=framePeriod, \
                                                description=defaultAxisTypeName(axisTypeFlags["t"]))
                    
                    newAxisCal = dt.AxisCcalibration(units=pq.s, 
                                                            origin=float(self.frames[0].attributes["absoluteTime"]), 
                                                            resolution=framePeriod,
                                                            axisname=defaultAxisTypeName(newAxisInfo))
                    
                    newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                    
                else: # ZSeries
                    # get the Z axis resolution from the frames state
                    z_pos = [float(f.state.attributes["positionCurrent_ZAxis"]) for f in self.frames]
                    z_steps = np.diff(z_pos)

                    zres = abs(z_steps[0])
                    
                    newAxisInfo = vigra.AxisInfo(key="z", typeFlags=vigra.AxisType.Space, \
                                                resolution=zres, \
                                                description=defaultAxisTypeName(axisTypeFlags["z"]))
                    
                    newAxisCal = AxisCalibration(newAxisInfo,
                                                           units=pq.um, 
                                                           origin=float(self.frames[0].state.attributes["positionCurrent_ZAxis"]), 
                                                           resolution=zres,
                                                           axisname=defaultAxisTypeName(newAxisInfo))
                    
                    newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                    
                # NOTE: 2018-08-01 17:03:52
                # see NOTE: 2018-08-01 17:04:06
                channelAxisDim = data[0][0].axistags.channelIndex
                
                if channelAxisDim == data[0][0].ndim-1:
                    newAxisDim = channelAxisDim
                    
                else:
                    newAxisDim = data[0][0].ndim
                    
                return [imgp.concatenateImages([imgp.insertAxis(data[frame][channel], newAxisInfo, newAxisDim) \
                                                        for frame in range(len(self.frames))], \
                                                        axis=newAxisInfo) \
                                                    for channel in range(len(data[0]))], None
                
        elif self.sequencetype == PVSequenceType.Single:
            # one sequence, one frame
            
            # NOTE: 2017-10-25 00:34:44
            # be mindful that frames __call__() return a TUPLE of
            # frame data and source data; except for Linescan frames, source data
            # is None,so we eliminate it here
                
            if self.__mergeChannelsOnOutput__:
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
        """Coerce reading the files as a multiband image.
        
        The self.multiBandOutput property is temporarily set to True, then 
        reverted to its previous value after the image files were read.
        
        """
        v = self.__mergeChannelsOnOutput__
        self.__mergeChannelsOnOutput__= True
        try:
            data = self.__call__(filepath=filepath)
        except Exception as e:
            self.__mergeChannelsOnOutput__ = v
            raise e
        self.__mergeChannelsOnOutput__ = v
        return data
    
    def metadata(self):
        """Returns metadata for this sequence.
        
        This is an ordered dictionary with the following fields:
        attributes    = dictionary with the sequence attributes
        length      = number of frames in the sequence
        definition  = for Linescan sequences this is the actual linescan definition; this is None for other sequence types
        zsync       = Z axis synchronization parameters
        filepath    = path to the data files 
        frames      = a list with metadata for each frame in the sequence
        """
        metadata = dict()
        
        metadata["attributes"]  = self.attributes
        metadata["length"]      = self.length
        metadata["definition"]  = self.definition.metadata()
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
    def parent(self):
        """The parent PVScan object, or None
        """
        return self.__parent__
    
    @parent.setter
    def parent(self, val):
        if isinstance(val, (type(None), PVScan)):
            self.__parent__ = val
            
        else:
            raise TypeError("Parent of a PVSequence can only be None or a PVScan object")
        
    @property
    def scan(self):
        """Alias for parent
        """
        return self.parent
    
    @scan.setter
    def scan(self, val):
        self.parent=val
    
    @property
    def multiBandOutput(self):
        """If True, the () operator reads this frame's files as a multiband image.
        This requires that each file corresponds to one channel and that all files 
        have a channel axis. Only applies when there are between 2 and 4 files per frame.
        """
        return self.__mergeChannelsOnOutput__
    
    @multiBandOutput.setter
    def multiBandOutput(self, val):
        """Permanently sets the state of the multiBandOutput property to val.
        
        Parameters:
        "val: boolean
        """
        self.__mergeChannelsOnOutput__ = val
    
    @property
    def attributes(self):
        return self.__attributes__
        
    @property
    def length(self):
        return len(self.frames)
    
    @property
    def definition(self):
        return self.__definition__
    
    @property
    def zAxisSynchronization(self):
        return self.__syncZAxis__
    
    @property
    def cycle(self):
        return self.__attributes__["cycle"]
        #return self.__dict__["cycle"]
        
    @property # read only
    def sequencetype(self):
        return self.__attributes__["sequencetype"]
        #return self.__dict__["sequencetype"]
    
    @property # read only
    def type(self):
        """ Alias to sequencetype property
        """
        return self.sequencetype
    
    @property # read only
    def typename(self):
        """Alias to sequencetypename property
        """
        return self.sequencetypename
    
    @property
    def sequencetypename(self):
        return PVSequenceType(self.__attributes__["sequencetype"]).name
        #return PVSequenceType(self.__dict__["sequencetype"]).name
    
    @property
    def filepath(self):
        """Returns the absolute path to the data referred to in this object.
        
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
        for k in self.__attributes__.keys():
            if k != "sequencetype":
                ret.append("  %s = %s\n" % (k, self.__attributes__[k]))
                #ret.append("  %s = %s\n" % (k, self.__dict__[k]))
                
        if self.__definition__ is not None:
            ret.append("\n Sequence definition:\n")
            ret.append(self.__definition__.__str__())

        if self.__syncZAxis__ is not None:
            ret.append("\n Z Axis Synchronization:\n")
            for k in self.__syncZAxis__.keys():
                ret.append("  %s = %s\n" % (k, self.__syncZAxis__[k]))

        ret.append("\n")
            
        for f in self.frames:
            ret.append(f.__str__())
        
        #ret.append("\n")
        
        return ("".join(ret))
        
                

class PVScan(object):
    """Encapsulates a PrairieView scan data.
    Stores a scan configuration object as parsed from an XML file, 
    optionally with data from a *Config file (also an XMl file but saved as ascii).
    The two files must have been read and parsed into valid xml documents and 
    xml element, respectively.
    
    This is so that scan data from various systems can be used/brought to a 
    common denominator (to the extent possible) represented by ScanData in this 
    framework.
    
    The other system planned for support is ScanImage (under progress)
    
    """
    
    def __init__(self, doc, configElement=None, name=None):
        if not isinstance(doc, xmlutils.xml.dom.minidom.Document):
            raise TypeError("Expecting a xmlutils.xml.dom.minidom.Document as argument; got %s instead" % (type(doc).__name__))
        
        if doc.documentElement is None or doc.documentElement.nodeName != "PVScan":
            raise ValueError("Expecting a valid PVScan XML data")
        
        # FIXME DO NOT store the documentElement attributes, directly in __dict__
        # NOTE:2017-10-31 08:37:19
        # storing attributed in __dict__ will result in infinite recursions in __str__()
        # at various places in the code, unless you write code to manage it.
        # -- too work for little benefit
        if doc.documentElement.attributes is not None:
            self.__attributes__ = DataBag(xmlutils.attributesToDict(doc.documentElement))
        else:
            self.__attributes__ = DataBag(dict())
            
        # query its children
        if not doc.documentElement.hasChildNodes():
            raise ValueError("PVScan XML data is empty!")
        
        self.__mergeChannelsOnOutput__ = False
        
        # the document element has both text nodes (simply rubbish of the form "\n  ") 
        # and element nodes which contain relevant information
        
        # We could just go and iterate blindly through all of these, or query
        # specific fields/data structures, provided the PVScan XML files we have
        # are enough to cover the entire PV data structures API
        
        # READ THE "about PVScan" file; go and fetch element nodes by their name
        
        # NOTE: 2017-08-03 09:22:43
        # there should be only ONE SystemConfiguration element node
        self.__systemConfiguration__ = PVSystemConfiguration(doc.documentElement.getElementsByTagName("SystemConfiguration")[0], \
                                        parent=self)

        self.sequences = [PVSequence(n, parent=self) for n in doc.documentElement.getElementsByTagName("Sequence")]
        
        try:
            self.__path__ = doc.documentElement.getElementsByTagName("DocPath")[0].childNodes[0].nodeValue
            
        except Exception as e:
            traceback.print_exc()
            #(tp, val, tb) = sys.exc_info()
            #print(traceback.print_tb(tb))
            warnings.warn("PVScan object path will be set to None")
            self.__path__ = None
            
        try:
            self.__filename__ = doc.documentElement.getElementsByTagName("DocFileName")[0].childNodes[0].nodeValue
        
        except Exception as e:
            traceback.print_exc()
            #(tp, val, tb) = sys.exc_info()
            #print(traceback.print_tb(tb))
            warnings.warn("PVScan object filename will be set to None")
            self.__filename__ = None
            
        if isinstance(name, str):
            self.__name__ = name
            
        else:
            if self.__filename__ is not None:
                self.__name__ = os.path.splitext(self.__filename__)[0]
            
    def __len__(self):
        return len(self.sequences)
    
    def __call__(self, filepath=None):
        # NOTE: 2017-10-24 22:47:12
        # get the type of the first sequence; this should be the same for ALL
        # sequences in this scan (otherwise, behaviour is undefined)
        # TODO try to accommodate more generality here, it at all possible
        # (see comments below)
        
        if not all([sequence.sequencetype == self.sequences[0].sequencetype for sequence in self.sequences]):
            raise ValueError("Mixed types of PVSequence are not supported")
        
        # NOTE: 2017-11-08 00:42:30 
        # DEPRECATION: PictArray dropped from the API
        
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
            
            
        #print("PVSCan(): filepath", filepath)
            
        #max_workers = len(self.sequences)
        
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
                    
                #print("PVScan.__call__() framePeriod", framePeriod)
                    
                newAxisInfo = vigra.AxisInfo(key="t1", typeFlags=vigra.AxisType.Time, 
                                                       resolution=framePeriod, 
                                                       description=defaultAxisTypeName(axisTypeFlags["t"]))
                
                newAxisCal = AxisCalibration(newAxisInfo,
                                                       units=pq.s,
                                                       origin=float(self.sequences[0].frames[0].attributes["absoluteTime"]),
                                                       resolution=framePeriod,
                                                       axisname=defaultAxisTypeName(newAxisInfo))

                newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)
                
                #print("PVScan.__call__() newAxisInfo", newAxisInfo)
                
                # NOTE: 2017-10-29 15:36:00 
                # incorporate the absolute source path to the XML document on the
                # file system is read from (so that we can load image data from
                # anywhere in the filesystem)
                
                # NOTE: 2017-10-25 00:34:44
                # be mindful that frames __call__() return a TUPLE of
                # frame data and source data; 
                # except for Linescan frames, source data is None
                if self.__mergeChannelsOnOutput__:
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
                    fdata = imgp.concatenateImages([imgp.insertAxis(img, newAxisInfo, newAxisDim) \
                                                        for img in frmdata], axis=newAxisInfo)
                    
                    channelAxisDim = srcdata[0].axistags.channelIndex
                    
                    if channelAxisDim == srcdata[0].ndim-1:
                        newAxisDim = channelAxisDim
                        
                    else:
                        newAxisDim = srcdata[0].ndim
                    
                    sdata = imgp.concatenateImages([imgp.insertAxis(img, newAxisInfo, newAxisDim) \
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
                    #print("fdata")
                    fdata = [imgp.concatenateImages(*[imgp.insertAxis(frmdata[sequence][channel], newAxisInfo, newAxisDim) \
                                                        for sequence in range(len(self.sequences))], \
                                                        axis=newAxisInfo) \
                            for channel in range(len(frmdata[0]))]
                    
                    #print("sdata")
                    sdata = [imgp.concatenateImages(*[imgp.insertAxis(srcdata[sequence][channel], newAxisInfo, newAxisDim) \
                                                        for sequence in range(len(self.sequences))], \
                                                        axis=newAxisInfo) \
                            for channel in range(len(srcdata[0]))]
                
            
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
            if self.__mergeChannelsOnOutput__:
                return self.sequences[0].mergeChannels() # (frameData, None)
                
            else:
                return self.sequences[0]() # (frameData, None)
            
        elif self.sequences[0].sequencetype == PVSequenceType.Single.value:
            # again, nothing to do here -- this pertains to SingleImage 
            # acquisition in PrairieView and consists of one sequence with one frame
            # TODO - FIXME can these ever have mmore thann one sequence? can each
            # of these sequences ever have more than one frame?
            
            if self.__mergeChannelsOnOutput__:
                return self.sequences[0].mergeChannels() # (frameData, None)
                
            else:
                return self.sequences[0]() # (frameData, None)
            
        
        elif self.sequences[0].sequencetype == PVSequenceType.Point.value:
            raise NotImplementedError("Point scan sequence parsing not implemented yet")
            # TODO - FIXME figure out what this does and how to parse it sensibly
            
        else:                           # do nothing here
            raise ValueError("Unknown sequence type %d" % self.sequencetype)
            

    def scanData(self, mergeChannels=False, analysisOptions=None, electrophysiology=None, name=None):
        """Returns a datatypes.ScanData object
        """
        
        if mergeChannels:
            caller = self.mergeChannels
            
        else:
            caller = self.__call__
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(caller)]
            
        for future in concurrent.futures.as_completed(futures):
            (scans, scene) = future.result()
        
        meta = self.metadata()
        #print("PVScan.scanData  c'tuct ScanData")
        ret = ScanData(scene=scene, scans=scans, metadata=meta, name=self.name)
        
        if analysisOptions is not None:
            ret.analysisOptions = analysisOptions
            
        if isinstance(electrophysiology, neo.Block):
            ret.electrophysiology = electrophysiology
            
        if isinstance(name, str) and len(name) > 0:
            ret.name = name
            
        return ret
    
    def scandata(self, *args, **kwargs):
        return self.scanData(*args, **kwargs)
        
            
    def metadata(self):
        """Returns metadata associated with this PVSCan
        """
        
        metadata = dict()
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
        
        return DataBag(metadata)
    
    def mergeChannels(self, filepath=None):
        """Coerce reading the files as a multiband image.
        
        The self.multiBandOutput property is temporarily set to True, then 
        reverted to its previous value after the image files were read.
        
        """
        v = self.__mergeChannelsOnOutput__
        self.__mergeChannelsOnOutput__= True
        try:
            data = self.__call__(filepath=filepath)
        except Exception as e:
            self.__mergeChannelsOnOutput__ = v
            raise e
        
        self.__mergeChannelsOnOutput__ = v
        return data
    
    @property
    def filepath(self):
        return self.__path__
    
    @filepath.setter
    def filepath(self, val):
        from os import path
        if os.path.isdir(val):
            self.__path__ = val
        else:
            raise ValueError("A valid directory path was expected")
        
    @property
    def filename(self):
        return self.__filename__
    
    @property
    def name(self):
        return self.__name__
    
    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError("expecting a str; got %s instead" % type(value).__name__)
        
        self.__name__ = value
        
    @property
    def datapath(self):
        """Alias for the filepath property
        """
        return self.filepath
    
    
    @datapath.setter
    def datapath(self, val):
        self.filepath = val
        
    @property
    def multiBandOutput(self):
        """If True, the () operator reads this frame's files as a multiband image.
        This requires that each file corresponds to one channel and that all files 
        have a channel axis. Only applies when there are between 2 and 4 files per frame.
        """
        return self.__mergeChannelsOnOutput__
    
    @multiBandOutput.setter
    def multiBandOutput(self, val):
        """Permanently sets the state of the multiBandOutput property to val.
        
        Parameters:
        "val: boolean
        """
        self.__mergeChannelsOnOutput__ = val
    
    @property
    def attributes(self):
        return self.__attributes__
        
    @property
    def cycles(self):
        return self.sequences
    
    @property
    def configuration(self):
        return self.__systemConfiguration__
    
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        ret = ["%s %s with %d sequences:\n" % (type(self).__name__, "object", len(self.sequences))]
        
        ret.append("Attributes:")
        #for k in self.__dict__.keys():
            #ret.append(" %s = %s" % (k, self.__dict__[k]))
            
        for k in self.__attributes__.keys():
            ret.append(" %s = %s" % (k, self.__attributes__[k]))
            
        ret.append("\n")

        #ret.append("Configuration:")
        ret.append(self.__systemConfiguration__.__str__())
        
        ret.append("\n")

        ret.append("SEQUENCES:")
        
        for k, s in enumerate(self.sequences):
            ret.append("Sequence %d:" % k)
            ret.append(s.__str__())
            
        ret.append("\n")
            
        return "\n".join(ret)
    
    
class PVImportDialog(WorkspaceGuiMixin, __UI_PVImporterDialog__, __QDialog__):
    """TODO
    """
    def __init__(self, currentdir=None, 
                 presyn_trigger_detect=None, 
                 postsyn_trigger_detect=None, 
                 photo_trigger_detect=None, 
                 imaging_trigger_detect=None, 
                 name=None,
                 pvdata_name=None, 
                 ephys_name=None, 
                 options=None, 
                 **kwargs):
        super(WorkspaceGuiMixin, self).__init__(**kwargs)
        super().__init__(self, **kwargs)
        
        if not isinstance(currentdir, str):
            currentdir = os.getcwd()
            #raise TypeError("currentdir expected to be a string; got %s instead" % type(currentdir).__name__)
        
        if not os.path.exists(currentdir) or not os.path.isdir(currentdir) or not os.access(currentdir, os.R_OK):
            raise ValueError("%s is not a readable directory" % currentdir)
        
        for n, t in zip(("presyn_trigger_detect", "postsyn_trigger_detect", "photo_trigger_detect", "imaging_trigger_detect"),
                        (presyn_trigger_detect, postsyn_trigger_detect, photo_trigger_detect, imaging_trigger_detect)):
        
            if not t is None:
                if not isinstance(t, (tuple, list)):
                    raise TypeError("%s expected to be a tuple or list; got %s instead" % (n, type(t).__name__))
                
                if len(t) not in (3, 4):
                    raise TypeError("%s expected to have three or four elements; got %d instead" % (n, len(t)))
                
                if not isinstance(t[0], bool):
                    raise TypeError("first element of %s expected to be a bool; got %s instead" % (n, type(t[0]).__name__))
                
                if not isinstance(t[1], int):
                    raise TypeError("second element of %s expected to be an int; got %s instead" % (n, type(t[1]).__name__))
                
                if t[1] < 0:
                    raise ValueError("second element of %s must be >= 0; got %d instead" % (n, t[1]))
                
                if not isinstance(t[2], str):
                    raise TypeError("third element of %s expected to be a str; got %s instead" % (n, type(t[2]).__name__))
                
                if len(t[2]) == 0:
                    raise ValueError("third element of %s must not be an empty string" % n)
                
                if len(t) == 4:
                    if not insinstance(t[3], tuple):
                        raise TypeError("fourth element of %s must be a tuple; got %s instead" % (n, type(t[3]).__name__))
                    
                    if len(t[3]) != 2:
                        raise TypeError("fourth element of %s must have two elements; got %d instead" % (n, len(presyn_trigger_detect[3])))
                    
                    if not all([isinstance(p, float) for p in t[3]]):
                        raise TypeError("fourth element of %s must contain float values" % n)
        
        if not isinstance(name, (str, type(None))):
            raise TypeError("'name' expected to be a string, or None; got %s instead" % type(name).__name__)
        
        if not isinstance(pvdata_name, (str, type(None))):
            raise TypeError("'pvdata_name' extected to be a string, or None; got %s instead" % type(pvdata_name).__name__)
        
        if isinstance(pvdata_name, str) and len(pvdata_name.strip()) == 0:
            raise ValueError("'pvdata_name' cannot be an empty string")
        
        if not isinstance(ephys_name, (str, type(None))):
            raise TypeError("'ephys_name' expected to be astring; got %s instead" % type(ephys_name).__name__)
        
        if isinstance(ephys_name, str) and len(ephys_name.strip()) == 0:
            raise ValueError("'ephys_name' cannot be an empty string")
        
        if not isinstance(options, (dict, type(None))):
            raise TypeError("'options' expected to be a dict or None; got %s instead" % type(options).__name__)
        
        self.targetdir              = currentdir
        self.presyn_trigger_detect  = presyn_trigger_detect
        self.postsyn_trigger_detect = postsyn_trigger_detect
        self.photo_trigger_detect   = photo_trigger_detect
        self.imaging_trigger_detect = imaging_trigger_detect
        
        self.xmlFileFilter          = "XML Files (*.xml)"
        self.pickleFileFilter       = "Pickle Files (*.pkl)"
        self.ephysFilesFilter       = ";;".join(["Axon files (*.abf)", "Pickle files (*.pkl)"])
        
        self.name                   = name
        self.pvdata_name            = pvdata_name
        self._ephys_name            = ephys_name
        
        self.pvXMLfileName          = None
        self.pvscan                 = None
        self.scanDataOptions        = None
        
        self.ephysdata              = None
        
        self.scandata               = None
        self.__configure_UI__()
        
    def __configure_UI__(self):
        self.setupUi(self)
        #self.pvScanFileChooserToolButton.clicked.connect(self.slot_choosePVFile)
        #self.pvScanImportFromWorkspaceToolButton.clicked.connect(self.slot_importPVData)
        
        pass
        
        
    @pyqtSlot()
    def slot_choosePVFile(self):
        self.pvXMLfileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                                 caption="Open PrairieView file", 
                                                                 filter=self.xmlFileFilter,
                                                                 directory=self.targetdir)
        
        if len(self.pvXMLfileName) == 0:
            return
        
        try:
            self.pvScan = PrairieView.PVScan(pio.loadXMLFile(pvXMLfileName))
            
        except Exception as e:
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QtWidgets.QMessageBox()
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            return
            
            
    @pyqtSlot()
    def slot_chooseEphysFiles(self):
        ephysFileNames, _ = QtWidgets.QFileDialog.getOpenFileNames(self, 
                                                               caption="Open electrophysiology files",
                                                               filter=self.ephysFilesFilter,
                                                               directory=self.targetdir)
        blocks = list()
        
        self.ephysData = None
        
        try:
            if len(ephysFileNames) > 0:
                if all([mimetypes.guess_type(f)[0] == "application/axon-data" for f in ephysFileNames]):
                    blocks = [pio.loadAxonFile(f) for f in ephysFileNames]
                    
                else:
                    blocks = [pio.loadPickleFile(f) for f in ephysFileNames]
                    
            if len(blocks) > 0:
                if all([isinstance(b, neo.Block) for b in blocks]):
                    self.ephysData = concatenate_blocks(*blocks)
                    
                elif all([isinstance(b, neo.Segment) for b in blocks]):
                    self.ephysData = neo.Block()
                    self.ephysData.segments[:] = blocks[:]
                    
                else:
                    QtWidgets.QMessageBox.critical("Electrophysiology files must contain neo.Blocks or individual neo.Segments")
                    return
                        
        except Exception as e:
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QtWidgets.QMessageBox()
            msgbox.setIcon(QtWidgets.QMessageBox.Critical)
            msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            return

    @pyqtSlot()
    def slot_chooseOptionsFile(self):
        from imaging.scandata import (scanDataOptions, ScanDataOptions, )
        epscatOptionsFileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                                         caption="Open EPSCaT Options file", 
                                                                         filter=self.pickleFileFilter,
                                                                         directory=self.targetdir)
        
        if len(epscatOptionsFileName) == 0:
            self.scanDataOptions = scanDataOptions()
            
        else:
            try:
                self.scanDataOptions = pio.loadPickleFile(epscatOptionsFileName)
                
            except Exception as e:
                s = io.StringIO()
                sei = sys.exc_info()
                traceback.print_exception(file=s, *sei)
                msgbox = QtWidgets.QMessageBox()
                msgbox.setIcon(QtWidgets.QMessageBox.Critical)
                msgbox.setWindowTitle(sei[0].__class__.__name__)
                msgbox.setText(sei[0].__class__.__name__)
                msgbox.setDetailedText(s.getvalue())
                msgbox.exec()
                return
                
        
    @pyqtSlot()
    def slot_importPVData(self):
        from core.workspacefunctions import getvarsbytype
        pvdatadocs = getvarsbytype(xmlutils.xml.dom.minidom.Document)
        
        
        
# NOTE: 2020-11-30 23:45:00
# place the mixin before other base classes so that it is initialized
# then super(...).__init__ it
class PrairieViewImporter(WorkspaceGuiMixin, __QDialog__, __UI_PrairieImporter, ):
    def __init__(self, 
                 name: typing.Optional[str] = None,
                 pvScanFileName: typing.Optional[str]=None, 
                 optionsFileName: typing.Optional[str]=None, 
                 ephysFileNames: typing.Optional[typing.Union[str, tuple, list]]=None,
                 protocolFileName: typing.Optional[str]=None,
                 **kwargs): # parent, flags - see documentation for QDialog constructor in Qt Assistant
        
        super(WorkspaceGuiMixin, self).__init__(**kwargs)
        super().__init__(**kwargs)
        
        self.scanData = None # the outcome: a ScanData object
        
        self.pvscan = None # the xml.dom.minidom.Document that specifies the
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
        
        #self.pvscan = None  # the PVScan document - generated from self.pvScanFileName
        self.scanDataOptions = None # ScanDataOptions object - to be assigned to lsdata
        
        self.ephys = None   # a neo.Block with electrophysiology recordings associated
                            # with lsdata
                            
        self.triggerProtocols = list()    # list of TriggerProtocol objects associated
                                        # with lsdata
                                        
        if isinstance(name, str) and len(name.strip()):
            self.dataName = name
            self.scanDataVarName = strutils.string_to_valid_identifier(self.dataName)
        
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
        
        self._configureUI_()
        
        self.generateScanData()
        
    def _configureUI_(self):
        self.setupUi(self)
        
        self.dataNameLineEdit.undoAvailable=True
        self.dataNameLineEdit.redoAvailable=True
        self.dataNameLineEdit.setClearButtonEnabled(True)
        if len(self.dataName):
            self.dataNameLineEdit.setText(self.dataName)
        self.dataNameLineEdit.editingFinished.connect(self._slot_setDataName)
        
        self.pvScanFileNameLineEdit.undoAvailable=True
        self.pvScanFileNameLineEdit.redoAvailable=True
        self.pvScanFileNameLineEdit.setClearButtonEnabled(True)
        if len(self.pvScanFileName):
            self.pvScanFileNameLineEdit.setText(self.pvScanFileName)
        self.pvScanFileNameLineEdit.editingFinished.connect(self._slot_setPVScanFileName)
        
        self.pvScanFileChooserToolButton.clicked.connect(self._slot_choosePVScanFile)
        self.pvScanImportFromWorkspaceToolButton.clicked.connect(self._slot_importPVScanFromWorkspace)
        
        self.optionsFileNameLineEdit.undoAvailable=True
        self.optionsFileNameLineEdit.redoAvailable=True
        self.optionsFileNameLineEdit.setClearButtonEnabled(True)
        
        if len(self.optionsFileName):
            self.optionsFileNameLineEdit.setText(self.optionsFileName)
        self.optionsFileNameLineEdit.editingFinished.connect(self._slot_setOptionsFileName)
        
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
        
        self.triggerProtocolFileChooserToolButton.clicked.connect(self._slot_chooseProtocolFile)
        self.protocolsImportToolButton.clicked.connect(self._slot_importProtocolFromWorkspace)
        
        self.detectTriggersToolButton.clicked.connect(self._slot_detectTriggers)
        
        
    @pyqtSlot()
    @safeWrapper
    def _slot_choosePVScanFile(self):
        fileFilter = ";;".join(["XML Files (*.xml)", "Pickle files (*.pkl)", "All files (*.*)"])
        
        self.pvScanFileName, fileFilter = self.chooseFile(caption="Open PrairieView file",
                                   fileFilter=fileFilter)
        
        if self.loadPVScan(self.pvScanFileName):
            self.generateScanData()

    @pyqtSlot()
    @safeWrapper
    def _slot_setPVScanFileName(self):
        self.pvScanFileName = self.pvScanFileNameLineEdit.text().strip()
        
        if self.loadPVScan(self.pvScanFileName):
            self.generateScanData()
                
    @pyqtSlot()
    @safeWrapper
    def _slot_setOptionsFileName(self):
        self.optionsFileName = self.optionsFileNameLineEdit.text()
        if self.loadOptions(self.optionsFileName):
            if not isinstance(self.scanData, ScanData):
                self.generateScanData()
                
            else:
                self.scanData.analysisOptions = self.scanDataOptions
        
    @pyqtSlot()
    @safeWrapper
    def _slot_chooseOptionFile(self):
        caption = "Open ScanData Options file for %s" % self.scanDataVarName if (isinstance(self.scanDataVarName, str) and len(self.scanDataVarName.strip())) else "Open EPSCaT Options file"
        
        self.optionsFileName, _ = self.chooseFile(caption=caption, fileFilter="Pickle Files (*.pkl)")
        
        if self.loadOptions(self.optionsFileName):
            if not isinstance(self.scanData, ScanData):
                self.generateScanData()
                
            else:
                self.scanData.analysisOptions = self.scanDataOptions
        
    @pyqtSlot()
    @safeWrapper
    def _slot_setEphysFileNames(self):
        self.ephysFileNames = self.ephysFileNameLineEdit.text().split(os.pathsep)
        if self.loadEphys(self.ephysFileNames):
            if isinstance(self.scanData, ScanData):
                self.scanData.electrophysiology = self.ephys
                
            else:
                self.generateScanData()
        
    @pyqtSlot()
    @safeWrapper
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
            if self.loadEphys(self.ephysFileNames):
                if isinstance(self.scanData, ScanData):
                    self.scanData.electrophysiology = self.ephys
                    
                else:
                    self.generateScanData()
    
    @pyqtSlot()
    @safeWrapper
    def _slot_setDataName(self):
        self.dataName = self.dataNameLineEdit.text()
        if len(self.dataName):
            self.scanDataVarName = strutils.string_to_valid_identifier(self.dataName)
            
            if isinstance(self.scanData, ScanData):
                self.scanData.name = self.dataName
                
            else:
                self.generateScanData()
        
    @pyqtSlot()
    @safeWrapper
    def _slot_setProtocolFileName(self):
        self.protocolFileName = self.triggerProtocolFileNameLineEdit.text()
        if self.loadProtocols(self.protocolFileName):
            if isinstance(self.ldata, ScanData):
                self.scanData.protocols = self.triggerProtocols
                
            else:
                self.generateScanData()
        
    @pyqtSlot()
    @safeWrapper
    def _slot_chooseProtocolFile(self):
        targetdir = os.getcwd()
        caption = "Open Trigger Protocol file for %s" % self.scanDataVarName if (isinstance(self.scanDataVarName, str) and len(self.scanDataVarName.strip())) else "Open Trigger Protocol file"
            
        self.protocolFileName, _ = self.chooseFile(caption=caption, filefilter="Pickle Files (*.pkl)")
        
        if len(self.protocolFileName):
            self.triggerProtocolFileNameLineEdit.setText(self.protocolFileName)
            if self.loadProtocols(self.protocolFileName):
                if isinstance(self.ldata, ScanData):
                    self.scanData.protocols = self.triggerProtocols
                    
                else:
                    self.generateScanData()
            
        else:
            self.triggerProtocolFileNameLineEdit.clear()
        
    @pyqtSlot()
    @safeWrapper
    def _slot_importPVScanFromWorkspace(self):
        vars_ = self.importWorkspaceData(xmlutils.xml.dom.minidom.Document,
                                         title="Import PVSCan Document",
                                         single=True)
        
        if len(vars_):
            self.pvscan = vars_[0]
            self.pvScanFileNameLineEdit.clear()
            
            self.generateScanData()
            
            
    @pyqtSlot()
    @safeWrapper
    def _slot_importOptionsFromWorkspace(self):
        vars_ = self.importWorkspaceData([ScanData, dict],
                                        title="Import Options",
                                        single=True)
        
        if len(vars_):
            options = vars_[0]
            
            if isinstance(options, ScanData):
                options = options.analysisOptions
                
            self.scanDataOptions = options
            self.optionsFileNameLineEdit.clear()
            
            if isinstance(self.scanData, ScanData):
                self.scanData.analysisoptions = self.scanDataOptions
                
            else:
                self.generateScanData()
            
    @pyqtSlot()
    @safeWrapper
    def _slot_importEphysFromWorkspace(self):
        import neo
        from imaging.scandata import ScanData
        
        vars_ = self.importWorkspaceData([ScanData, neo.Block, neo.Segment, 
                                          neo.AnalogSignal, tuple, list],
                                        title="Import electrophysiology",
                                        single=False)
        if len(vars_) == 1:
            if isinstance(vars_[0], ScanData):
                self.ephys = vars_[0].electrophysiology
                
            elif isinstance(vars_[0], neo.Block):
                self.ephys = vars_[0]
                
            elif isinstance(vars_[0], neo.Segment):
                self.ephys = neo.Block()
                self.ephys.segments[:] = vars_[0]
                
            elif isinstance(vars_[0], neo.AnalogSignal):
                self.ephys = neo.Block()
                self.ephys.segments.append(neo.Segment())
                self.ephys.segments[0].analogsignals.append(vars_[0])
                
            elif isinstance(vars_[0], (tuple, list)) and len(vars_[0]):
                if all([isinstance(v, neo.Segment) for v in vars_[0]]):
                    self.ephys = neo.Block()
                    self.ephys.segments[:] = vars_[0][:]
                    
                elif all([isinstance(v, neo.AnalogSignal) for v in vars_[0]]):
                    self.ephys = neo.Block()
                    self.ephys.segments.append(neo.Segment())
                    self.ephys.segments[0].analogsignals[:] = vars_[0][:]
                    
                else:
                    raise TypeError("Cannot import ephys data %s" % vars_[0])
                
            else:
                raise TypeError("Cannot import ephys data %s" % vars_[0])
                
            self.ephysFileNameLineEdit.clear()
                
        elif len(vars_) > 1:
            if all([isinstance(v, neo.Segment) for v in vars_]):
                self.ephys = neo.Block()
                self.ephys.segments[:] = vars_[:]
                
            else:
                raise TypeError("Cannot import ephys data %s" % vars_)

            self.ephysFileNameLineEdit.clear()
            
        if isinstance(self.ephys, neo.Block):
            if isinstance(self.scanData, ScanData):
                self.scanData.electrophysiology = self.ephys
                
            else:
                self.generateScanData()

    @pyqtSlot()
    @safeWrapper
    def _slot_importProtocolFromWorkspace(self):
        from core.triggerprotocols import (TriggerProtocol,)
        from imaging.scandata import ScanData
        
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
                    raise TypeError("Expecting a ScanData, a TriggerProtocol or a sequence of TriggerProtocol objects; got %s instead" % vars_[0])
                    
                self.triggerProtocolFileNameLineEdit.clear()
                
            else:
                if all([isinstance(v, TriggerProtocol) for v in vars_]):
                    self.triggerProtocols[:] = vars_[:]
                    
                else:
                    raise TypeError("Expecting a multiple selection of TriggerProtocol objects; got %s instead" % vars_)
        
                self.triggerProtocolFileNameLineEdit.clear()
                
        if len(self.triggerProtocols) and all([isinstance(p, TriggerProtocol) for p in self.triggerProtocols]):
            if isinstance(self.scanData, ScanData):
                self.scanData.protocols = self.triggerProtocols
                
            else:
                self.generateScanData()
        
    @pyqtSlot()
    @safeWrapper
    def _slot_detectTriggers(self):
        if self.scanData is None:
            return
        
        if isinstance(self.scanData.electrophysiology, neo.Block) and len(self.scanData.electrophysiology.segments):
            ephys_preview = sv.SignalViewer(pWin = self._scipyenWindow_)
            ephys_preview.plot(self.ephys)
            # TODO call protocol dialog wizard
        
            
        
    @safeWrapper
    def loadPVScan(self, fileName):
        signalblockers = [QtCore.QSignalBlocker(w) for w in (self.pvScanFileNameLineEdit, self.dataNameLineEdit)]
        
        if len(fileName) and os.path.isfile(fileName):
            mime_type, file_type, encoding = pio.getMimeAndFileType(fileName)
            
            if "xml" in mime_type:
                self.pvscan = PVScan(pio.loadXMLFile(fileName))
                
            elif "pickle" in mime_type:
                self.pvscan = pio.loadPickleFile(fileName)
                
            else:
                self.errorMessage("PrairieView Importer - Prairiew View Scan file", "%s is not an XML or Pickle file" % self.pvScanFileName)
                self.pvScanFileNameLineEdit.clear()
                self.pvScanFileName=""
                self.scanDataVarName = ""
                self.dataName = ""
                return False
            
            self.pvScanFileNameLineEdit.setText(fileName)
            
            tempDataVarName = os.path.splitext(os.path.basename(fileName))[0]
            self.scanDataVarName = strutils.string_to_valid_identifier(tempDataVarName)
            
            if len(self.dataName) == 0:
                self.dataName = self.scanDataVarName
                self.dataNameLineEdit.setText(self.dataName)
                
            return True
        
        return False
    
    @safeWrapper
    def loadEphys(self, fileNamesList):
        if len(fileNamesList):
            bad_files = [f for f in fileNamesList if not os.path.isfile(f)]
            if len(bad_files):
                self.criticalMessage("PrairieView Importer - Electrophysiology files ", "The following files could not be found %s" % os.pathsep.join(fileNamesList))
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
                self.errorMessage("PrairieView Importer - Electrophysiology files ", "Expecting Axon or Pickle files for electrophysiology")
                return False
                    
            if len(blocks):
                if all([isinstance(b, neo.Block) for b in blocks]):
                    self.ephys = concatenate_blocks(*blocks)
                    
                    return True
                    
                elif all([isinstance(b, neo.Segment) for b in blocks]):
                    self.ephys = neo.Block()
                    self.ephys.segments[:] = blocks[:]
                    
                    return true
                    
                else:
                    QtWidgets.QMessageBox.critical("PrairieView Importer - Electrophysiology files must contain neo.Blocks or individual neo.Segments")
                    
        return False
    
    @safeWrapper
    def loadOptions(self, fileName):
        signalblockers = [QtCore.QSignalBlocker(w) for w in (self.optionsFileNameLineEdit,)]
        
        if len(fileName) and os.path.isfile(fileName) and "pickle" in pio.getMimeAndFileType(fileName)[0]:
            self.optionsFileName = fileName
            self.optionsFileNameLineEdit.setText(self.optionsFileName)
            self.scanDataOptions = pio.loadPickleFile(fileName)
            return True
        
        else:
            self.errorMessage("PrairieView Importer - Options file", "%s is not an XML or Pickle file" % self.pvScanFileName)
            self.optionsFileName = ""
            self.optionsFileNameLineEdit.clear()
            return False
        
    @safeWrapper
    def loadProtocols(self, fileName):
        signalblockers = [QtCore.QSignalBlocker(w) for w in (self.triggerProtocolFileNameLineEdit,)]
        mime_type = pio.getMimeAndFileType(fileName)[0]
        if len(fileName) and os.path.isfile(fileName) and "pickle" in mime_type:
            self.protocolFileName = fileName
            self.triggerProtocolFileNameLineEdit.setText(self.protocolFileName)
            self.triggerProtocols = pio.loadPickleFile(self.protocolFileName)
            return True        
        
        else:
            self.errorMessage("PrairieView Importer - Protocols File", "Expecting a Pickle file; got %s which is a %s instead" % (fileName, mime_type))
            self.protocolFileName = ""
            self.triggerProtocolFileNameLineEdit.clear()
            return False
        
        
    @safeWrapper
    def generateScanData(self):
        import neo
        
        if isinstance(self.pvscan, PVScan):
            self.scanData = self.pvscan.scandata()
            
        if isinstance(self.scanData, ScanData):
            if len(self.dataName):
                self.scanData.name = self.dataName
                
            if isinstance(self.ephys, neo.Block):
                # NOTE: 2020-10-06 19:32:24 the check below is performed by 
                # ScanData setter
                #if len(self.ephys.segments) != self.scanData.nScansFrames:
                    #self.warningMessage("PrairieView Importer", "Mismatch between the number of electrophysiology swweeps (%d) and that of scans sweeps (%d)" % (len(self.ephys.segments), self.scanData.nScansFrames))
                        
                self.scanData.electrophysiology = self.ephys
                
            if isinstance(self.scanDataOptions, (ScanDataOptions, dict)):
                self.scanData.analysisOptions = self.scanDataOptions
                
            if isinstance(self.triggerProtocols, (tuple, list)) and all([isinstance(v, triggerprotocols.TriggerProtocol) for v in self.triggerProtocols]):
                self.scanData.triggerProtocols = self.triggerProtocols
            
