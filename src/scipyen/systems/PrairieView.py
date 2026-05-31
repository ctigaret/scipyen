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
 'TriggerProtocolsEditorDialog',
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
# from core.sysutils import adapt_ui_path

import iolib.pictio as pio

# from gui import resources_rc # as resources_rc
# from gui import icons_rc # as icons_rc
# from gui import quickdialog as qd
# from gui.triggerdetectgui import TriggerDetectDialog, TriggerDetectWidget
# from gui.triggerprotocolseditordialog import TriggerProtocolsEditorDialog
# from gui import pictgui as pgui
# from gui.workspacegui import WorkspaceGuiMixin
# import gui.signalviewer as sv
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
# __ui_path__ = adapt_ui_path(__module_path__, "PrairieImporter.ui")
#
# if os.environ["QT_API"] in ("pyqt5", "pyside2"):
#     __UI_PrairieImporter, __QDialog__ = loadUiType(__ui_path__, from_imports=True, import_from="gui")
# else:
#     __UI_PrairieImporter, __QDialog__ = loadUiType(__ui_path__)


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

    def as_dict(self): pass # must implement in subclasses

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

            self.line_length = float(linenodes[0].attributes.getNamedItem("lineLength").value)
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

    def as_dict(self) -> dict:
        if len(list(self.items)):
            return dict(self.items)
        return {self.key:self.value}

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

    def as_dict(self)->dict:
        return dict(filter(lambda i: i[0] != "index", self.attributes.items()))

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

    def as_dict(self)->dict:
        return dict(filter(lambda i: i[0] != "subindex", self.attributes.items()))

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

    def as_dict(self)->dict:
        return dict(self.items)

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

    def as_dict(self) -> dict:
        return dict(self.items)

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
# the behavior of vigraimpex towards file names that are parent of a sequence is quite handy
# with ZSeries also, as it can be used to load the entire ZSeries data for one channel
# into a single VigraArray
class PVFrame(PVObject):
    r"""Encapsulates a PrairieView Frame.
        A ferame may contain several "File"s which are encapsulated by DataBag objects
    """
    def __init__(self, node, index:int, parent:PVSequence):
        r"""PVFrame constructor:
        node: xmlutils.xml.dom.Node with type ELEMENT_NODE
        index: int index of the frame in the parent sequence; must be >= 0
            Also this shuold be unique among all the frames in a sequence (CAUTION: this is NOT enforced)
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

    def as_dict(self)->dict:
        return {"Files": self.files, "State": self.state}

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

        # ### BEGIN STEP 1: read metadata
        #
        mdata = self.metadata()
        #
        # ### END   STEP 1: read metadata

        # ### BEGIN STEP 2: set up file names
        #
        if filepath is None:
            if self.parent is not None:
                filepath = self.parent.filepath
        #
        # ### END   STEP 2: set up file names

        # ### BEGIN STEP 3: set up vigra arrays and their axes, using the "files"
        # metadata field
        #
        #
        # ### END   STEP 3: set up vigra arrays and their axes
        frameData = list() # will contain vigra arrays for each scans frame, to be concatenated

        sourceData = list() # will contain vigra arrays for each source frame, to be concatenated

        for k in range(len(mdata["files"])):
            fileName = self.files[k]['filename']
            channel_acquisition_index = self.files[k]['channel']
            channel_name = self.files[k]['channelName']
            # NOTE: 2022-01-06 00:10:42
            # fdata: frame data
            # sdata: source data
            if isinstance(filepath, str):
                filepath = pathlib.Path(filepath)

            # ### BEGIN load frame data
            #
            if isinstance(filepath, pathlib.Path):
                fdata = pio.loadImageFile(filepath.parent / fileName)

            else:
                fdata = pio.loadImageFile(fileName)
            #
            # ### END   load frame data

            # ### BEGIN set up frame data axes and calibrations
            #

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

            # ### BEGIN Axis 0 (i.e., 1st dimension)
            #
            fdata_axis_0_info = fdata.axistags[0]

            fdata_axis_0_cal  = AxisCalibrationData.new(fdata_axis_0_info)
            fdata_axis_0_cal.units = pq.um
            if self.versionString < "5.5":
                fdata_axis_0_cal.resolution = float(self.state["micronsPerPixel_XAxis"].value)*pq.um

            else:
                # ATTENTION: 2025-04-04 15:07:52 for PrairieView v >= 5.5, axes
                # resolutions are ALL in the state shard at PVScan level, NOT in
                # the frame's stateshard, which contains frame-specific information
                # such as gain & laser power, ONLY WHEN APPROPRIATE (e.g. in a Z series)
                #
                state = self.parent.parent.state

                if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
                    fdata_axis_0_cal.resolution = float(state["micronsPerPixel"]["XAxis"].value)*pq.um
                else:
                    scipywarn(f"Cannot get the μm / pixel for axis {print_styled(f'{fdata_axis_0_info}', 'yellow')} in frame {print_styled(f'frame {self.index}', 'yellow')}")

            # embed calibration string into axis_0_info's description
            fdata_axis_0_info = fdata_axis_0_cal.calibrateAxis(fdata_axis_0_info)

            #
            # ### END   Axis 0 (i.e., 1st dimension)

            # ### BEGIN Axis 1 (i.e., 2nd dimension)
            #
            # NOTE: 2018-06-03 22:15:54
            # the type of this axis (spatial or temporal) depends on the type of
            # PVSequence: for a Linescan, this axis is in the time domain.
            #
            # By default, vigra impex sets this axis to be a Space type ('y')
            # so we only modify this default behaviour when PVSequence is of
            # Linescan type
            if self.parent is not None and self.parent.type == PVSequenceType.Linescan:
                if self.versionString < "5.5":
                    fdata_axis_1_info = vigra.AxisInfo(key="t",
                                                typeFlags=vigra.AxisType.Time,
                                                resolution = float(self.state.attributes["scanlinePeriod"]))
                    resolution = float(self.state.attributes["scanlinePeriod"])*pq.s
                else:
                    state = self.parent.parent.state
                    fdata_axis_1_info = vigra.AxisInfo(key="t",
                                                typeFlags=vigra.AxisType.Time,
                                                resolution = float(state["scanLinePeriod"].value))
                    resolution = float(state["scanLinePeriod"].value)*pq.s


                fdata_axis_1_cal  = AxisCalibrationData.new(fdata_axis_1_info)
                fdata_axis_1_cal.resolution = resolution
                fdata_axis_1_cal.units = pq.s

            else: # NOT a line scan — this implies axis 1 is in the space domain
                fdata_axis_1_info = fdata.axistags[1] # by default vigra behaviour is Space

                fdata_axis_1_cal = AxisCalibrationData.new(fdata_axis_1_info)
                fdata_axis_1_cal.units = pq.um
                if self.versionString < "5.5":
                    fdata_axis_1_cal.resolution = float(self.state["micronsPerPixel_YAxis"].value)*pq.um
                else:
                    # NOTE: see ATTENTION: 2025-04-04 15:07:52
                    state = self.parent.parent.state
                    if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
                        fdata_axis_1_cal.resolution = float(state["micronsPerPixel"]["YAxis"].value)*pq.um
                    else:
                        scipywarn(f"Cannot get the μm / pixel for axis {print_styled(f'{fdata_axis_1_info}', 'yellow')} in frame {print_styled(f'frame {self.index}', 'yellow')}")


            # embed calibration string into axis_1_info's description
            fdata_axis_1_info = fdata_axis_1_cal.calibrateAxis(fdata_axis_1_info)

            #
            # ### END   Axis 1 (i.e., 2nd dimension)

            # ### BEGIN Axis 2 (i.e., 3rd dimension)
            #

            # NOTE: 2018-06-03 22:16:26
            # axis_2_info is the AxisInfo object for 3rd dimension
            # Since all individual images saved by PrairieView are 2D,
            # then the third axis is a Channels axis (by default vigra impex
            # assigns this as 'c' even if is singleton)
            #

            # NOTE: 2025-07-06 22:58:05 Create a channel axis calibration
            if fdata.channelIndex == fdata.ndim: # channel axis is virtual
                # NOTE: 2018-08-01 16:43:58
                # make sure there IS a channel axis
                fdata_axis_2_info = vigra.AxisInfo.c

            else:
                fdata_axis_2_info = fdata.axistags["c"]

            chCal = ChannelCalibrationData(index = 0,
                                           acquisition_index = channel_acquisition_index,
                                           name = channel_name)

            # print(f"\n{self.__class__.__name__}.__call__: frame {k}: scans data chCal -> \n{print_styled(f'\n{chCal}', color='yellow')}")

            fdata_axis_2_info.description = channel_name
            fdata_axis_2_cal = AxisCalibrationData.new(fdata_axis_2_info, channels = [chCal])
            # print(f"\nfdata_axis_2_cal: \n{print_styled(fdata_axis_2_cal, 'yellow')}")
            fdata_axis_2_info = fdata_axis_2_cal.calibrateAxis(fdata_axis_2_info)
            # print(f"\nfdata_axis_2_info.description: \n{print_styled(fdata_axis_2_info.description, 'yellow')}")

            #
            # ### END   Axis 2 (i.e., 3rd dimension)

            #
            # ### END   set up frame data axes and calibrations

            # ### BEGIN append a new frame scan data: VigraArray constructed from fdata and the new axistags
            # (initialized from the calibrated AxisInfo objects)
            #
            newaxistags = vigra.AxisTags(fdata_axis_0_info, fdata_axis_1_info, fdata_axis_2_info)
            frame = vigra.VigraArray(fdata, axistags=newaxistags)

            frameData.append(frame)
            #
            # ### END   append a new VigraArray constructed from fdata and the new axistags


            # NOTE: 2021-10-27 22:18:41
            # the source data is set up using the same blueprint as for frame data
            # ideally we should end up with one source data frame for each scans data frame
            if "source" in self.files[k] and all(self.files[k]["source"]):
                sourceFileName = self.files[k]["source"]
                # print(f"\treading source {sourceFileName}")
                if isinstance(filepath, pathlib.Path):
                    sdata = pio.loadImageFile(filepath.parent / sourceFileName)

                else:
                    sdata = pio.loadImageFile(sourceFileName)

                if sdata.ndim == 2 and sdata.channelIndex == sdata.ndim:
                    sdata.insertChannelAxis() # make sure there is a channel axis

                sdata_axis_0_info = sdata.axistags[0]
                sdata_axis_0_cal = AxisCalibrationData.new(sdata_axis_0_info)
                sdata_axis_0_cal.units = pq.um

                if self.versionString < "5.5":
                    sdata_axis_0_cal.resolution = float(self.state["micronsPerPixel_XAxis"].value)*pq.um
                else:
                    # NOTE: see ATTENTION: 2025-04-04 15:07:52
                    state = self.parent.parent.state

                    # print(f"{self.__class__.__name__}.__call__: query scales for SOURCE {sdata_axis_0_info} - state keys: {tuple(state.keys)}")
                    if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
                        sdata_axis_0_cal.resolution = float(state["micronsPerPixel"]["XAxis"].value)*pq.um
                    else:
                        scipywarn(f"Cannot get the μm / pixel for axis {print_styled(f'{sdata_axis_0_info}', 'yellow')} in frame {print_styled(f'frame {self.index}', 'yellow')}")

                sdata_axis_0_info = sdata_axis_0_cal.calibrateAxis(sdata_axis_0_info)

                sdata_axis_1_info = sdata.axistags[1]
                sdata_axis_1_cal = AxisCalibrationData.new(sdata_axis_1_info)
                sdata_axis_1_cal.units = pq.um

                if self.versionString < "5.5":
                    sdata_axis_1_cal.resolution=float(self.state["micronsPerPixel_YAxis"].value) * pq.um
                else:
                    # NOTE: see ATTENTION: 2025-04-04 15:07:52
                    state = self.parent.parent.state
                    # print(f"{self.__class__.__name__}.__call__: query scales for SOURCE {sdata_axis_1_info} - state keys: {tuple(state.keys)}")
                    if isinstance(state, PVStateShard) and "micronsPerPixel" in state:
                        sdata_axis_1_cal.resolution=float(state["micronsPerPixel"]["YAxis"].value)* pq.um
                    else:
                        scipywarn(f"Cannot get the μm / pixel for axis {print_styled(f'{sdata_axis_1_info}', 'yellow')} in frame {print_styled(f'frame {self.index}', 'yellow')}")

                sdata_axis_1_info = sdata_axis_1_cal.calibrateAxis(sdata_axis_1_info)

                if sdata.channelIndex == sdata.ndim:
                    sdata_axis_2_info = vigra.AxisInfo.c
                else:
                    sdata_axis_2_info = sdata.axistags["c"]

                sChCal = ChannelCalibrationData(index = 0,
                                                acquisition_index = channel_acquisition_index,
                                                name = channel_name)
                # print(f"\n{self.__class__.__name__}.__call__: frame {k} scene data sChCal -> \n{print_styled(f'\n{sChCal}', color='yellow')}")

                sdata_axis_2_info.description = channel_name
                sdata_axis_2_cal = AxisCalibrationData.new(sdata_axis_2_info, channels = [sChCal])
                # print(f"\nsdata_axis_2_cal: \n{print_styled(sdata_axis_2_cal, 'yellow')}")
                sdata_axis_2_cal = sdata_axis_2_cal.calibrateAxis(sdata_axis_2_info)
                # print(f"\nsdata_axis_2_info.description: \n{print_styled(sdata_axis_2_info.description, 'yellow')}")

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
                channel_indicess = list(range(len(self.files)))
                channel_acquisition_indices = [int(self.files[k]["channel"]) for k in range(len(self.files))]
                channel_names = [self.files[k]["channelName"] for k in range(len(self.files))]

                mergedFrameData = concatenateImages(*frameData, axis="c", allowConcatenationFor=("origin", "resolution"))

                merged_channels_axinfo = mergedFrameData.axistags["c"]

                merged_channel_calibrations = list(map(lambda c: ChannelCalibrationData(index = c[0], acquisition_index=c[1], name=c[2]), zip(channel_indices, channel_acquisition_indices, channel_names)))

                merged_channels_axcal = AxesCalibration.new(merged_channels_axinfo,
                                                            name = axisTypeName(merged_channels_axinfo),
                                                            channels = merged_channel_calibrations)

                # for kch, channel in enumerate(channels):
                #     merged_channels_axcal.addChannelCalibration(ChannelCalibrationData(name=channel_names[kch],
                #                                                                          index=channel))
                merged_channels_axinfo = merged_channels_axcal.calibrateAxis(merged_channels_axinfo)

                if sourceData is not None:
                    mergedSourceData = concatenateImages(*sourceData, axis="c")

                    merged_source_channel_axinfo = mergedSourceData.axistags["c"]

                    merged_source_channel_axcal = AxesCalibration(merged_source_channel_axinfo,
                                                                  name = axisTypeName(merged_source_channel_axinfo),
                                                                  channels = merged_channel_calibrations)

                    # for kch, channel in enumerate(channels):
                    #     merged_source_channel_axcal.addChannelCalibration(ChannelCalibrationData(name=channel_names[kch],
                    #                                                                                 index = channel))

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
        r"""Load the images from the file(s) defined in its frames attribute.

        In line scanning mode, PrairieView also saves "sources" TIFF files alongside
        the line scanning data. Scipyen uses these "source" files as the "scene":
        a reference frame where the line scanning data was acquired.

        For T- or Z-stacks, the scans and the scene refer to the same field of view
        (albeit possibly with different spatial/temporal resolutions and acquisition
        channels).

        The "scene" data is more useful for linescans, as is represents the
        reference frame where the linescan was acquired.

        When present, each frame has set of "source" files, one per acquisition
        channel, which are used to construct the corresponding scene.

        If there is only one frame, then it will load that data and return it
        as a (possibly, multi-channel or "multi-band" ) vigra array.

        Returns None if no frames are defined.

        Keyword parameter:
        ==================

        filepath = str or None; optional, default is None; when given, the image filenames
        will be prepended with the value of path to create absolute file names.

        This value overrides any value from the parent PVScan (when the latter
        is not None).

        Returns:
        =======
        A sequence of

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

                # print(f"{self.__class__.__name__}.__call__: filepath = {filepath}")

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
                    newAxisCal.resolution = framePeriod * pq.s
                    newAxisInfo = newAxisCal.calibrateAxis(newAxisInfo)

                else: # Z series
                    # get the Z axis resolution from the frames state
                    if self.parent.versionString < "5.5":
                        zres = float(self.parent.state["micronsPerPixel_ZAxis"].value)*pq.um
                        # z_pos = list(map(lambda f: float(f.state["positionCurrent_ZAxis"].value), self.frames))
                    else:
                        zres = float(self.parent.state["micronsPerPixel"]["ZAxis"].value)*pq.um

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
                # print(f"\tchannelAxisDim -> {channelAxisDim}")

                if channelAxisDim == data[0].ndim-1:
                    newAxisDim = channelAxisDim

                else:
                    newAxisDim = data[0].ndim


                # print(f"\tnewAxisDim -> {newAxisDim}")

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


                # NOTE: 2025-07-06 18:10:28 Prepare the concatenation axis
                # ### BEGIN Prepare the concatenation axis
                #

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
                    zres = self.parent.state["micronsPerPixel"]["ZAxis"]
                    if self.parent.versionString < "5.5":
                        z_pos = list(map(lambda f: float(f.state["positionCurrent_ZAxis"].value), self.frames))
                    else:
                        # NOTE: get the frame state, else parent's (i.e. PVSCan's state)
                        frameStates = map(lambda f: f.state if len(f.state) else self.parent.state, self.frames)
                        # WARNING: some more recent build versions of PV do NOT include
                        # a Z axis positionCurrent in the stateshard of the first frame - not sure why is that,
                        # unless it has something to do with setting imaging laser intensity to some function
                        # of the imaging Z axis coordinate; in such cases, I suspect the Z position of the first
                        # fraem is to be found int e PVStateshard of the parent PVScan (NOT its sequence)
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

                    # print(f"{self.__class__.__name__}.__call__: sequence {self.sequencetypename} with {len(self.frames)} frames")
                    # print(f"\tnewAxisInfo -> {newAxisInfo} with newAxisCal -> {newAxisCal}")


                # NOTE: 2018-08-01 17:03:52
                # see NOTE: 2018-08-01 17:04:06
                channelAxisDim = data[0][0].axistags.channelIndex
                # print(f"\tchannelAxisDim -> {channelAxisDim}")


                if channelAxisDim == data[0][0].ndim-1:
                    newAxisDim = channelAxisDim

                else:
                    newAxisDim = data[0][0].ndim
                #
                # ### END   Prepare the concatenation axis
                # print(f"\tnewAxisDim -> {newAxisDim}")

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
                if self.versionString >= "5.5":
                    # NOTE: 2025-07-04 10:51:23
                    # Frame-specific Z position appears to have been removed from the
                    # per-frame state shard
                    # my guess s that is may have been updated in the parent PVSvcan during
                    # acquisition.
                    # Therefore I cannot infer the Z axis resollution from this data anymore
                    # Intead, I must use PVScan's state["micronsPerPixel"]["ZAxis"]
                    # z_pos = [f.state.attributes["positionCurrent"]["ZAxis"] for f in self.frames]
                    framePeriod = float(self.parent.state["micronsPerPixel"]["ZAxis"].value) * pq.um
                else:
                    z_pos = [f.state.attributes["positionCurrent_ZAxis"] for f in self.frames]
                    z_steps = np.diff(z_pos)

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

    def as_dict(self)->dict:
        return {"State": self.state, "Frames": self.frames}

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
                # config = loadPrairieViewXML(configFile)
                config = pio.loadXML(configFile)
                config_filepath = config.createElement("DocPath")
                config_filepath.setAttribute("value", configFile.as_posix())
                config.documentElement.appendChild(config_filepath)
                self._systemConfiguration_ = PVSystemConfiguration(config.documentElement, self)
            else:
                # self._path_ has NOT been set; this is usually because the
                # 'doc' argument is a document previously loaded (either using
                # the pio.loadXMLFile function, or the custom loadPrairieViewXML
                # function in this module. In the latter case it WILL HAVE BEEN
                # 'augmented' with a child node 'DocPath' with the 'value'
                # attribute set to the absolute path of the PVScan XML file.
                docPathNodes = tuple(xmlutils.getChildren(doc.documentElement, tagName="DocPath"))
                if len(docPathNodes) == 0:
                    raise ValueError("Document should have been loaded with 'loadPrairieViewXML'")

                # was loaded using loadPrairieViewXML;
                self._path_ = pathlib.Path(docPathNodes[0]).getAttributes("value")
                # so I assume the env file saved in the same directory by default
                configFile = self._path_.with_suffix(".env")
                if configFile.is_file():
                    config = loadPrairieViewXML(configFile)
                else:
                    # my assumption failed here;
                    # allow for the possibility that a config file or Document
                    # was supplied separately
                    if not isinstance(config, xmlutils.xml.dom.minidom.Document):
                        if isinstance(config, str):
                            config = pathlib.Path(config)

                        if isinstance(config, pathlib.Path) and config.is_file() and config.suffix.lower() == ".env":
                            config = loadPrairieViewXML(config)
                        else:
                            raise TypeError(f"For separately loaded XML documents created with PrairieView version {self.versionString}, a 'config' parameter must be given,\n either a absolute path to an existing configuration file, or as a loaded XML document")

                    raise OSError(f"Cannot find the configuration file {configFile}")

                systemConfiuration = PVSystemConfiguration(config.documentElement, parent=self)
                assert systemConfiguration.versionstring == self.versionString, "Experiment and environment files were cerated with distinct versions of PrairieView"
                self._systemConfiguration_ = systemConfiguration

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

        # print(f"{self.__class__.__name__}.__call__: sequencetype: {self.sequences[0].sequencetypename} with {len(self.sequences)} sequences")

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
                return self.sequences[0].mergeChannels()

            else:
                return self.sequences[0]()

        elif self.sequences[0].sequencetype == PVSequenceType.Single.value:
            # again, nothing to do here -- this pertains to SingleImage
            # acquisition in PrairieView and consists of one sequence with one frame
            # TODO - FIXME can these ever have mmore than one sequence? can each
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


        meta = self.metadata

        file_origin = self.filepath
        rec_datetime = self._rec_datetime_

        return ScanData(scans=scans, scene=scene, name=self.name,
                        electrophysiology=electrophysiology,
                        analysisOptions=analysisOptions,
                        file_origin=file_origin,
                        rec_datetime=rec_datetime,
                        metadata=self.metadata)

    def scandata(self, *args, **kwargs):
        r"""Alias of (delegates to) self.scanData.
        This method is kept so that it does not break older Scipyen API.
    """
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

    def as_dict(self)->dict:
        return {"State": self.state, "Sequences":self.sequences}

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

def loadPrairieViewXML(filePath:typing.Union[str, pathlib.Path]) -> object:
    filePath = pathlib.Path(filePath).absolute()
    ret = pio.loadXML(filePath)
    if ret.documentElement.tagName not in ("PVScan", "Environment"):
        raise ValueError("Not a PVScan experiment or PVScan environment file")
    # augument with the full path to this file
    doc_filepath = ret.createElement("DocPath")
    doc_filepath.setAttribute("value", filePath.as_posix())
    ret.documentElement.appendChild(doc_filepath)
    return ret

__all__ = ("PVObject","PVScan", "PVSequence", "PVSequenceType", "PVFrame",
           "PVSystemConfiguration", "PVLinescanMode", "PVStateShard",
           "PVStateValue", "PVIndexedValue", "PVSubIndexedValue",
           "PVSubIndexedValueList", "PVLinescanDefinition")
