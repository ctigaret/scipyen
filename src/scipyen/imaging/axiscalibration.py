# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# TODO: 2025-04-08 12:54:19 FIXME
# re-design based on dataclasses - NOW!

r"""Classes for attaching physical units to the axes of 𝒏-dimensional arrays.

The module is intended primarily for VigraArrays, where each axis has a defined
physical meaning (space, time, frequency, etc) including the "channels" axis,
which can be used to attach a physical dimensionality to the channel data.

For "non-channel" axes, the calibration assigns physical units to the axes
along the specified dimension of the array. NOTE that these units refer to the 
physical domain for the specified dimension (space, time, frequency etc), and
NOT the physical domain of the actual array values. The latter is managed
using "channel calibration objects" for a Channels axis, see below.

For a Channels axis, the physical domain of the actual values in the array is
managed individually for each "channel" of the array. VigraArrays can treat 
elements as represented by more than one channel "value" at the same array
coordinate. This effectively means that the array has one extra dimension: the 
Channels axis.

Here, a channels axis calibration is simply attaching a physical unit to the 
values in the array, without any numerical trasformation.

NOTE: This is NOT the same as calibrating the image channel data, which means 
attributing a numeric relationship between the value at each element in the 
(raw) pixel data and a define physical measure. This form of calibration 
effectively transforms raw pixel values (e.g, "intensities") into some physical 
measure with different numerical values, AND units.

For numpy arrays where all elements belong to the same physical domain,
Python Quantity arrays can, and should, be used instead. However, the physical
domain of their coordinate system can still benefit from this module.


Classes in this module:

CalibrationData: superclass for AxisCalibrationData and ChannelCalibrationData

AxisCalibrationData: type encapsulating the physical units (and domain) for an 
    axis. Contains channel calibration data for a Channel axis.
    
ChannelCalibrationData: type encapsulating the physical units of a channel in the
    array.

AxesCalibration: collects all AxisCalibrationData associated with an array

CalSpec: the named tuple (origin, maximum, units) - used as shorthand
for factory methods.



"""

import numbers, operator, math, dataclasses
from dataclasses import (dataclass, MISSING, field)
import inspect, functools, itertools, traceback, typing, warnings
from functools import (singledispatch, singledispatchmethod)
from collections import (deque, namedtuple)
from collections.abc import Sequence
from pprint import (pprint, pformat)
import h5py
from core.vigra_patches import vigra 
import numpy as np
import pandas as pd
import quantities as pq
from traitlets import Bunch

from core import datatypes, xmlutils
from core.xmlutils import getChildren as getXMLChildren
from core import quantities as cq
from core.quantities import (arbitrary_unit, 
                            space_frequency_unit,
                            angle_frequency_unit,
                            channel_unit,
                            pixel_unit,
                            quantity2scalar,
                            unitQuantityFromNameOrSymbol,
                            unitsConvertible,
                            )

from core.datatypes import (is_numeric, is_numeric_string,)
from core.constants import ( RELATIVE_TOLERANCE, ABSOLUTE_TOLERANCE, EQUAL_NAN)

from core.utilities import (reverse_mapping_lookup, unique, counter_suffix,
                            isclose, all_or_all_not)

from core.traitcontainers import DataBag

from core.prog import (ArgumentError, scipywarn)

from .axisutils import (axisTypeName, 
                        axisTypeSymbol, 
                        axisTypeUnits,
                        axisTypeFromString,
                        axisTypeStrings,
                        axisTypeFromUnits,
                        evalAxisTypeExpression,
                        sortedAxisTypes,
                        isValidAxisType,
                        isElementaryAxisType,
                        standardAxisTypeKeys,
                        )

CalSpec = namedtuple("CalSpec", ["origin", "maximum", "units"])

@dataclass
class CalibrationData:
    r'''Superclass for AxisCalibrationData and ChannelCalibrationData'''
    
    units:pq.Quantity = field(default=pq.arbitrary_unit)
    r'''The physical units'''
    
    name:typing.Optional[str] = field(default_factory = str)
    r'''The name of this calibration.
    For a Channels axis, this is the Channel name'''
    
    # NOTE: 2025-04-13 09:46:01
    # this may create confusion with the AxisInfo 'description' field; besides, 
    # I'm not sure about what this brings to the data...
    # description:typing.Optional[str] = field(default_factory = str)
    
    relative_tolerance:float = RELATIVE_TOLERANCE
    r'''Useful when comparing values'''
    
    absolute_tolerance:float = ABSOLUTE_TOLERANCE
    r'''Useful when comparing values'''
    
    equal_nan:bool = EQUAL_NAN
    r'''When comparing calibration data with NaN values, this determines whether
    NaN values are considwered equal overriding the default in Python.'''
    
    fc_template:bool = "{:.16f}"
    r'''String format template for loating point and complex scalars.
    see str.format() for details'''

    @classmethod
    def isCalibration(cls, x):
        fnames = list(map(lambda f: f.name, dataclasses.fields(cls)))
        return isinstance(x, cls) or (isinstance(x, dict) and all(k in fnames for k in x))
    
    def asdict(self) -> dict:
        r'''Creates a dict from this instance'''
        return dataclasses.asdict(self)
    
    @property
    def calibrationString(self) -> str:
        fnames = tuple(map(lambda f: self._to_xml_(f.name), dataclasses.fields(self)))
        return "".join(fnames)
        
    @staticmethod
    def _from_xml_text_(param, txt) -> object:
        if param == "units":
            value = unitQuantityFromNameOrSymbol(txt)
            
        elif param in ("key", "name"):
            value = txt
            
        elif param == "type":
            value = axisTypeFromString(txt)
            
        elif param == "fc_template":
            value = txt
            
        else:
            if txt is None:
                value = None
                
            elif isinstance(txt, str):
                if "nan" in txt:
                    value = np.nan
                elif "None" in txt:
                    value = None
                elif "MISSING" in txt:
                    value = dataclasses.MISSING
                else:
                    value = eval(txt)
                    
            else:
                value = None
            
        # print(f"param: {param}, txt: {txt}, value: {value}")
        return value
    
    def _to_xml_(self, param):
        # print(f"{self.__class__.__name__}_to_xml_(param = {param})")
        value = getattr(self, param, None)
        
        ss = [f"<{param}>"]
        
        if value is not None:
            if param == "type":
                s = "|".join(axisTypeStrings(value))
            
            elif param == "units":
                # output the dimensionality's string property
                s = value.units.dimensionality.string
                
            elif param == "index":
                s = "%d" % value
                
            elif isinstance(value, (float, complex)) or (isinstance(value, pq.Quantity) and value.ndim == 0): # ("origin", "resolution", "maximum", "minimum")
                # includes np.nan, math.nan, np.inf, math.inf
                # and purely scalar Quantities
                # NOTE: 2025-04-13 09:53:33 WARNING
                # posible loss of precision here!
                # hence we need the fc_template field
                s = self.fc_template.format(value)
                
            elif value is dataclasses.MISSING:
                s = "MISSING"
                
            else:
                # includes any int, str, pd.NA, None, bool, bytes, bytearray
                s =f"{value}"
                # raise TypeError(f"Unsupported value type {type(value).__name__}")
                
            ss.append(s)
        
        ss.append(f"</{param}>")
        
        return "".join(ss) 
    
    def __eq__(self, other):
        ret = self.__class__ == other.__class__
        if ret:
            if self.equal_nan and other.equal_nan:
                nanfields = list(filter(lambda x: np.isnan(x[1]), map(lambda f: (f.name, getattr(self, f.name)), dataclasses.fields(self))))
                print(f"{self.__class__.__name__}.__eq__: nanfields = {nanfields}")
                for f in nanfields:
                    ret &= getattr(other, f[0], np.nan) in (np.nan, math.nan)
                    
            else:
                ret &= super(self).__eq__(other)
                        
@dataclass
class ChannelCalibrationData(CalibrationData):
    r""" Calibration for a channel in a Channels axis """
    index:int = 0 
    r'''channel index'''
    
    origin:float = 0.0 # is this really needed?
    r"""channel's minimum value, in self.units, as float"""
    
    maximum:typing.Optional[float] = 1.0 # is this really needed?
    r"""channel's maximum value, in self.units, as float"""
    
    # is this channel virtual?
    # virtual:bool=False
    
    @property
    def calibrationString(self) -> str:
        name = self.name if isinstance(self.name, str) and len(self.name.strip()) else f"channel_{self.index}"

        strlist = [f"<{name}>"]
        for param in sorted(map(lambda x: x.name, dataclasses.fields(self.__class__))):
            strlist.append(self._to_xml_(param))
        strlist.append(f"</{name}>")
        
        return "".join(strlist)
        
    
@dataclass
class AxisCalibrationData(CalibrationData):
    index:int = 0
    r'''index of this axis in the array dimensions: 0-based.
    Must be ≥ 0
    '''
    
    origin:numbers.Number = 0.0
    r'''The origin of the axis coordinates.
    To what coordinate does the 0th element along the axis correspond?
    By default this is 0.0, but there can be good reasons for why axis might have
    a non-zero origin (i.e., an "offset")'''
    
    resolution:numbers.Number = 1.0
    r'''The sampling resolution (in 1/axis units).
    WARNING: Unlike the "resolution" field of a vigra.AxisInfo, where a value
    of 0 signals no defined resolution, here "resolution" represents the number
    number of axis elements corresponding to a unit of axis physical coordinates,
    e.g., number of pixels in a micrometer, etc.

    When the resolution is undetermined, the value of this field should be NaN here.
    
    By default, this ios set to 1.0 i.e., one axis element per axis physical unit
    (e.g., one pixel per micrometer).
    
    You almost surely want to change this.
    '''
    
    maximum:typing.Optional[numbers.Number] = None
    r'''The upper limit of the axis coordinates.
    To what coordinate does the last element along the axis correspond?'''
    
    type:typing.Optional[typing.Union[vigra.AxisType, int]] = field(default=vigra.AxisType.UnknownAxisType)
    r'''The type of the axis'''
    
    key:typing.Optional[str] = "?"
    r'''String symbol of the axis'''
    
    size:typing.Optional[int] = 1
    r'''Size of te axis (i.e. size of the array along the dimension of this axis).
    For a Channels axis, this is also the number of channels.
    Must be ≥ 1.
    '''
    
    channels:typing.Optional[typing.Sequence[CalibrationData]] = None
    r'''Sequence of ChannelCalibrationData, one per channel.
    For a NonChannel axis this MUST be None, or an empty list; for a Channels 
    axis, even a virtual one, this MUST have at least one ChannelCalibrationData'''
    
    # def __post_init__(self):
    #     r"""Allows constructing an AxisCalibrationData object from a single parameter.
    #     The following parameter types are allowed:
    #     vigra.AxisInfo
    #     str (calibraion string)
    #     CalSpec
    #     """
    #     # NOTE: 2025-04-13 22:27:49
    #     # by virtue of inheriting from CalibrationData, the first field set in the
    #     # __init__ generated by the dataclass decorator is 'units', which will
    #     # therefore 'swallow' the first parameter pased to the constructor
    #     print(f"{self.__class__.__name__}.__post_init__: self.units: {type(self.units).__name__}")
    #     if isinstance(self.units, vigra.AxisInfo):
            
    
    @singledispatchmethod
    @classmethod
    def new(cls, o:object):
        r"""Factory for AxisCalibrationData objects"""
        raise NotImplementedError(f"Not implemented for objects of type {type(o).__name__}")
    
    @new.register(vigra.AxisInfo)
    @classmethod
    def _(cls, arg:vigra.AxisInfo, index:typing.Optional[int] = None, 
        size: typing.Optional[int] = None,
        origin: typing.Optional[typing.Union[numbers.Number, pq.Quantity, CalSpec]] = None,
        maximum: typing.Optional[typing.Union[numbers.Number, pq.Quantity]] = None,
        units: typing.Optional[pq.Quantity] = None,
        channels: typing.Optional[typing.Sequence[CalSpec]] = None):
        # NOTE: 2025-04-13 13:42:52
        # in vigra.AxisInfo, a 'resolution' field 0.0 means axis resolution (in
        # the sense of sampling resolution, which should be in (axis units)⁻¹ ) 
        # is not defined !
        axtype = arg.typeFlags
        axkey = arg.key
        axres = 1. if arg.resolution == 0 else arg.resolution
        
        cal_str_start_stop = cls.findCalibrationString(arg.description)
        
        if cal_str_start_stop is None:
            ret = cls(type=axtype, key = axkey, name = axisTypeName(axtype), resolution = axres)
            
            # overwrite the defaults if needed:
            #
            if isinstance(index, int):
                if index >= 0 :
                    ret.index = index
                else:
                    raise ValueError(f"Invalid axis index: {index}")
                
            if isinstance(size, int):
                if size >= 1:
                    ret.size = size
                else:
                    raise ValueError(f"Invalid axis size: {size}")
                
            if arg.typeFlags & vigra.AxisType.Channels:
                ret.origin  = np.nan
                ret.maximum = np.nan
                ret.resolution = np.nan
                
                if isinstance(channels, typing.Sequence) and all(isinstance(v, CalSpec) for v in channels):
                    if len(channels) != ret.size:
                        if ret.size == 1:
                            ret.size = len(channels)
                        else:
                            raise ValueError(f"{len(channels)} wwre specified for a Channels axis of size {ret.size}")
                
                ret.channels = list(map(lambda k: ChannelCalibrationData(index=k, name=f"channel_{k}", **channels[k]), range(ret.size)))
                
            else:
                if isinstance(origin, CalSpec):
                    origin, maximum, units = origin
                
                if isinstance(units, pq.UnitQuantity):
                    ret.units = units
                
                elif isinstance(units, pq.Quantity):
                    ret.units = units.units
                    
                elif units is not None:
                    raise TypeError(f"Invalid type for units: {type(units)._name__}; a pq.Quantity, pq.UnitQuantity or None was expected")
                    
                if isinstance(origin, numbers.Number):
                    ret.origin = origin
                    
                elif isinstance(origin, pq.Quantity):
                    if origin.ndim > 0:
                        raise ValueError(f"Origin quantity must be a scalar")
                    if origin.units != ret.units:
                        if scq.unitsConvertible(origin.units, ret.units):
                            origin = origin.rescale(ret.units)
                        else:
                            raise ValueError(f"Wrong units ({origin.units}) for axis origin, for a calibration with units of {ret.units}")
                    
                    val = origin.magnitude
                    valdtype = val.dtype
                    if "int" in valdtype.name:
                        ret.origin = int(val)
                    elif "complex" in valdtype.name:
                        ret.origin = complex(val)
                    elif "float" in valdtype.name:
                        ret.origin = float(val)
                    else:
                        raise TypeError(f"Unsupported dtype: {valdtype}")
                    
                elif origin is not None:
                    raise TypeError(f"Invalid type for origin: {type(origin).__name__}; a number.Number, pq.Quantity, a CalSpec, or None was expected")
                    
                if isinstance(maximum, numbers.Number):
                    ret.maximum = maximum
                        
                elif isinstance(maximum, pq.Quantity):
                    if maximum.units != ret.units:
                        if scq.unitsConvertible(maximum.units, ret.units):
                            maximum = maximum.rescale(ret.units)
                        else:
                            raise ValueError(f"Wrong units ({maximum.units}) for axis maximum,  for a calibration with units of {ret.units}")
                    
                    val = maximum.magnitude
                    valdtype = val.dtype
                    if "int" in valdtype.name:
                        ret.maximum = int(val)
                    elif "complex" in valdtype.name:
                        ret.maximum = complex(val)
                    elif "float" in valdtype.name:
                        ret.maximum = float(val)
                    else:
                        raise TypeError(f"Unsupported dtype: {valdtype}")
                        
                elif maximum is not None:
                    raise TypeError(f"Invalid type for maximum: {type(maximum).__name__}; a number.Number, a pq.Quantity, or None was expected.")
                
                
            # return cls(type=axtype, key = axkey, name = axisTypeName(axtype), resolution = axres)
            
        else:
            # TODO 2025-04-13 13:45:58 FIXME parse the calibration string
            # embedded in this AxisInfo 'description'.
            calStr = arg.description[cal_str_start_stop[0]:cal_str_start_stop[1]]
            return cls.new(calStr)
        
    @new.register(dict)
    @classmethod
    def _(cls, d:dict):
        if cls.isCalibration(d):
            return cls(**d)
        
    @new.register(str)
    @classmethod
    def _(cls, s:str):
        r"""Parses a calibration string.
        
        For the structure of an XML-formatted calibration string see the
        documentation for the AxisCalibrationData.calibrationString property.
        
        Parameters:
        ==========
        
        s: str = XML-formatted calibration string (see documentation for
        AxisCalibrationData.calibrationString property)
        
        Returns:
        ========
        An AxisCalibrationData instance. 
            This either a reference to the AxisCalibrationData object passed as
            the 'cal' parameter, or a new AxisCalibrationData object, otherwise.
            
            When 's' is a string containing an XML-formatted calibration string 
            (see AxisCalibrationData.calibrationString()), the returned value
            (and 'cal', if passed) will be updated with the calibration values
            parsed from the string in 's'. Otherwise, the returned value is the
            original value of 'cal' (if 'cal' is an AxisCalibrationData object) 
            or a new, 'default' AxisCalibrationData object (as for an axis with 
            type flags UnknownAxisType).
        
        """
        import xml.etree.ElementTree as ET
        
        if not isinstance(s,str) or len(s.strip()) == 0 or not s.startswith("<axis_calibration>") or not s.endswith("</axis_calibration>"):
            raise ValueError("This is not an axis calibration string")
            
        cal = dict()
        
        # OK, now extract the relevant xml string
        try:
            cal_xml_element = ET.fromstring(s)
            
            # make sure we're OK
            if cal_xml_element.tag != "axis_calibration":
                raise ValueError("Wrong element tag; was expecting 'axis_calibration', instead got %s" % element.tag)
            
            # see NOTE: 2021-10-09 23:58:58
            # xml.etree.ElementTree.Element.getchildren() is absent in Python 3.9.7
            
            # fnames = tuple(map(lambda f: f.name, dataclasses.fields(cls)))
            
            # for param in fnames:
            for param in map(lambda f: f.name, dataclasses.fields(cls)):
                child_nodes = tuple(getXMLChildren(cal_xml_element, tagName=param))
                if len(child_nodes):
                    child_node = child_nodes[0]
                    txt = child_node.text
                    cal[param] = cls._from_xml_text_(param, txt)

        except Exception as e:
            traceback.print_exc()
            print(f"cannot parse calibration string {s}")
            raise e
            
        if cls.isCalibration(cal):
            return cls(**cal)

    @property
    def calibrationString(self) -> str:
        r"""
        An XML-formatted string with one of the following formats, depending on
        whether the axis is a Channels axis or not:
        
        1) For a NonChannel axis:
        ----------------------------
        
        <axis_calibration>
            <type>int</type>
            <key>str</key>
            <name>str</name>
            <size>int</size>
            <units>str</units>
            <origin>float</origin>
            <resolution>float</resolution>
            <maximum>float</maximum>
            <relative_tolerance>float</relative_tolerance>
            <absolute_tolerance>float</absolute_tolerance>
            <equal_nan>bool</equal_nan>
            <channels></channels>
        </axis_calibration>
        
        2) for a Channels axis:
        ----------------------------
        <axis_calibration>
            <type>int</type>
            <key>str</key>
            <name>str</name>
            <size>int</size>
            <channels>
                <channel_0>
                    <index>int</index>
                    <name>str</name>
                    <units>str</units>
                    <minimum>float|complex|int</minimum>
                    <maximum>float|complex|int</maximum>
                    <resolution>float</resolution>
                    <relative_tolerance>float</relative_tolerance>
                    <absolute_tolerance>float</absolute_tolerance>
                    <equal_nan>bool</equal_nan>
                    <formula>str</formula>
                </channel_0>
                <channel_1>
                    <index>int</index>
                    <name>str</name>
                    <units>str</units>
                    <minimum>float|complex|int</minimum>
                    <maximum>float|complex|int</maximum>
                    <resolution>float</resolution>
                    <relative_tolerance>float</relative_tolerance>
                    <absolute_tolerance>float</absolute_tolerance>
                    <equal_nan>bool</equal_nan>
                    <formula>str</formula>
                </channel_1>
                ... etc ...
            </channels> 
        </axis_calibration>
        
        NOTE: keep it simple: a virtual Channels-type axis has NO calibration data
        if a singleton channel needs calibration then the array MUST have a
        Channel axis defined.
        """
        

        strlist = ["<axis_calibration>"]
        
        # for param in sorted(self.__class__.parameters):
        for param in sorted(filter(lambda x: x != "channels", map(lambda x: x.name, dataclasses.fields(self)))):
            strlist.append(self._to_xml_(param))
            
        if self.type & vigra.AxisType.Channels and isinstance(self.channels, (list, tuple)) and len(self.channels):
            strlist.append("<channels>")
            for ch in self.channels:
                # NOTE: 2025-04-13 18:13:32
                # ch should be a ChannelCalibrationData
                # NOTE: 2025-04-08 14:39:48
                # see NOTE: 2025-04-08 14:39:08
                # NOTE: 2021-11-08 11:35:19
                # only append channel information if there are channel calibrations
                # if "virtual" not in ch[0]:
                if not ch.virtual:
                    strlist.append(f"<{ch.name}>")
                    strlist.append(ch.calibrationString)
                    strlist.append(f"</{ch.name}>")
                    
            strlist.append("</channels>")
                
        strlist.append("</axis_calibration>")
        
        return "".join(strlist)
    
    @staticmethod
    def findCalibrationString(s:str) -> typing.Optional[tuple]:
        start = s.find("<axis_calibration>")
        if start > -1:
            stop = s.rfind("</axis_calibration>") 
            if stop > -1:
                stop += len("</axis_calibration>")
            else:
                stop = start + len("<axis_calibration>")
            return (start, stop)
    
            
    

class AxesCalibration(object):
    r"""Encapsulates calibration of a set of axes.
    
    Associates physical units (and names) to a vigra array axis.
    
    An axes calibration for a VigraArray is uniquely determined by the axis type
    and the attributes 'name', 'units', 'origin', and 'resolution', for each 
    AxisInfo object attached to the VigraArray.
    
    VigraArray axes calibrations are encapsulated in AxisCalibrationData objects.
    
    In addition, for the calirbation for a Channels axis contains
    ChannelCalibrationData for each channel defined along the axis.
    
    Quick reminder on vigra.AxisTags, vigra.AxisInfo, and vigra.AxisType objects:
    ----------------------------------------------------------------------------
    
    AxisTags: describes the axis properties AND ordering in a VigraArray
        * constructed from a sequence of AxisInfo objects
        * minimal iterable interface 
            e.g. let data.axistags an AxisTags object:
            
            `(a for a in data.axistags)` iterates through the AxisInfo objects in 
                the AxisTags object)
            
            `data.axistags[k]` with `k` an `int` OR a `str`
                when `k` is an `int` AND `0 <= k < len(data.axistags)` or `0 <= k < data.ndim`
                    returns the k_th AxisInfo object
                    
                when `k` is a `str` AND is a KEY of an AxisInfo objects contained
                in the `data.axistags`
                    returns the AxisInfo object with `key == k`
                    
            `data.axistags.index(k)`
                where `k` is a `str`:
                    returns the `int` index of the AxisInfo with `key == k`
                    
                if an AxisInfo object with `key == k` is NOT found, returns 
                `data.ndim`
            
    AxisInfo: describes a SINGLE axis.
        Relevant attributes (dot access):
        
        `key`: `str` - values are from the standard set prescribed by vigranumpy,
            and enhanced by Scipyen in `imaging.axisutils.axisTypeflags`
        
        `resolution`: `float`
        `description`: `str`
        
        Read-only:
        `typeFlags`: vigra.AxisType
        
    AxisType: enum type encoding the type of the axis described by an AxisInfo.
    
    """

    def __init__(self, *args):
        r"""
        Var-positional parameters:
        ==========================
        *args = a vigra.VigraArray, a vigra.AxisTags, up to to five 
                vigra.AxisInfo, XML-formatted calibration strings or 
                AxisCalibrationData objects.
                
        NOTE: 
        The AxisInfo objects used in the AxesCalibration's initialization WILL
        NOT gain a calibration string in their `description` attribute (i.e., 
        the AxisInfo will not be automatically 'calibrated').
            
        The user of the AxesCalibration object must call its 'calibrateAxes()'
        method in order to embed an XML-formatted calibration string into
        the AxisInfo `description` attribute.
        
        
        """
        
        self.relative_tolerance = RELATIVE_TOLERANCE
        self.absolute_tolerance = ABSOLUTE_TOLERANCE
        self.equal_nan = EQUAL_NAN
        
        # NOTE 2021-10-25 10:27:54
        # keep this as a LIST - this to allow several axes with the same 
        # typeFlags (and key).
        self._calibration_ = list()
        
        if len(args) == 1 and isinstance(args[0], (tuple, list , deque)):
            args = args[0]
        
        if len(args):
            if isinstance(args[0], vigra.VigraArray):
                self._axistags_ = args[0].axistags
                
                self._calibration_ = list(map(lambda x: AxisCalibrationData(x), args[0].axistags))
                # self._calibration_ = [AxisCalibrationData(axinfo) for axinfo in args[0].axistags]
                
                #set up channel calibrations with default values:
                if args[0].channelIndex != args[0].ndim: # real channel axis exists
                    channel_axis_index = args[0].axistags.index("c")
                    # Make sure we don't overwrite existing channel calibrations
                    if len(self._calibration_[channel_axis_index].channels) < args[0].channels:
                        for k in range(len(self._calibration_[channel_axis_index].channels), args[0].channels):
                            self._calibration_[channel_axis_index].addChannelCalibration(ChannelCalibrationData(name=f"channel_{k}", index=k), name=f"channel_{k}")
                    elif len(self._calibration_[channel_axis_index].channels) > args[0].channels:
                        extra = list()
                        for k in range(args[0].channels, len(self._calibration_[channel_axis_index].channels)):
                            extra.append(self._calibration_[channel_axis_index].channels[k])
                            
                        for k,c in extra:
                            self._calibration_[channel_axis_index]._data_.pop(k, None)
                
                return

            elif isinstance(args[0], vigra.AxisTags):
                self._axistags_ = args[0]
                
                self._calibration_ = [AxisCalibrationData(axinfo) for axinfo in args[0]]
            
                # the AxisInfo objects MUST be calibrated maunally (the
                # AxisCalibrationData c'tor does NOT do this automatically)
                #for k, axinfo in enumerate(self._axistags_):
                    #self._calibration_[k].calibrateAxis(axinfo)
                    
                return
            
            elif isinstance(args[0], int):
                # NOTE: 2021-10-25 10:25:39
                # here we use the strategy in vigra.AxisTags constructor: an int
                # indicates HOW MANY axes are there, and therefore NOT an axis 
                # type flag
                if args[0] <= 0:
                    raise ValueError(f"Cannot create an AxesCalibration object for {args[0]} axes")
                
                self._axistags_ = vigra.AxisTags(args[0])
                
                self._calibration_ = [AxisCalibrationData(axinfo) for axinfo in self._axistags_]
                
                # the AxisInfo objects MUST be calibrated maunally (the
                # AxisCalibrationData c'tor does NOT do this automatically)
                #for k, axinfo in enumerate(self._axistags_):
                    #self._calibration_[k].calibrateAxis(axinfo)
                    
                return
                    
            else:
                # NOTE: 2021-10-25 10:44:30
                # The vigra.AxisTags constructor takes up to five individual 
                # AxisInfo objects (as a comma-separated sequence of parameters), 
                # a sequence of AxisInfo objects, an int, or no parameter. 
                #
                # The last three cases allow the creation of axistags for arrays
                # of arbitrary number of dimensions (the no-parameter case 
                # creates an empty array to which AxisInfo objects can be
                # appended).
                #
                self._axistags_ = vigra.AxisTags()
                for k, arg in enumerate(args):
                    if isinstance(arg, vigra.AxisInfo):
                        cal = AxisCalibrationData(arg)
                        #cal.calibrateAxis(arg) # MUST calibrate AxisInfo manually
                        self._axistags_.append(arg)
                        self._calibration_.append(cal)
                                        
                    elif isinstance(arg, str):
                        try:
                            cal = AxisCalibrationData(arg)
                        except:
                            cal = AxisCalibrationData() #  create default UnknownAxisType
                            
                        #self._axistags_.append(cal.axisInfo) 
                        self._calibration_.append(cal)
                        
                    elif isinstance(arg, AxisCalibrationData):
                        #self._axistags_.append(arg.axisInfo) 
                        self._calibration_.append(arg)
                        
                    else:
                        if k == 0:
                            raise TypeError(f"Expecting a vigra.VigraArray, vigra.AxisTags, vigra.AxisInfo, str, int, AxisCalibrationData or a sequence of these; got {type(arg).__name} instead")
                        else:
                            raise TypeError(f"{k}th argument is not a vigra.AxisInfo, str or AxisCalibrationData")
                        

        if not self.__check_cal_axinfo__():
            raise RuntimeError("Axis calibration data is inconsistent with axis info objects")
        
    def __check_cal_axinfo__(self):
        ret = len(self._axistags_) == len(self._calibration_)
        
        if ret:
            ret &= all(cal.key in self._axistags_ for cal in self._calibration_)
            
        if ret:
            calkeys = (cal.key for cal in self._calibration_)
            ret &= all(axinfo.key in calkeys for axinfo in self._axistags_)
            
        return ret
        
    def __iter__(self):
        r"""Iterates through the AxisCalibrationData objects contained within self
        """
        yield from (cal for cal in self._calibration_ if cal.key in self._axistags_)
        #yield from (cal.key for cal in self._calibration_ if cal.key in self._axistags_)
        
    def __contains__(self, item):
        r"""Membership test.
        item: CalibrationData, str (calibration key or name), or type flag 
            (int or vigra.AxisType)
        """
        if isinstance(item, str):
            return any(item in (getattr(cal, "key", None), getattr(cal, "name", None)) for cal in self._calibration_)
        
        elif isinstance(item, (int, vigra.AxisType)):
            return item in (getattr(cal, "type", None) for cal in self._calibration_)
        
        elif isinstance(item, CalibrationData):
            return item in self._calibration_
        
        return False
     
    def __getitem__(self, index:typing.Union[int, slice, range, str, vigra.AxisInfo]) -> typing.Union[AxisCalibrationData, typing.List[AxisCalibrationData]]:
        r"""Indexed access to the AxisCalibrationData for an axis.
        
        Parameters:
        ===========
        index:
                int, slice, range => return the AxisCalibrationData at index
                
                str: axis key or name
                    returns the first AxisCalibrationData found, having
                    name == index; failing that, returns the first 
                    AxisCalibrationData found, having key == index; when this
                    also fails raises IndexError
                    
                    If key is "c" and there is no Channel axis calibration, 
                    returns  a default AxisCalibrationData("c") with 
                    ChannelCalibrationData for the 'virtual' channel 0
                    
                    This behaviour emulates that of vigra.AxisTags.
                    
        NOTE
        A VigraArray (and by extension, an AxesCalibration object) can 
        theoretically contain several axes with the same key.
            
        To obtain ALL the axes with a given key,  use the idiom:
        
            `[cal for cal in axcal.calibrations if cal.key == key]`
        
        where `axcal` is an AxesCalibration object.
            
        """
        if isinstance(index, vigra.AxisInfo):
            index = index.key # a str
            
        if isinstance(index, (int, slice, range)):
            return self._calibration_[index] # raises IndexError if inappropriate
        
        elif isinstance(index, str):
            if index in self:
                ret = [cal for cal in self._calibration_ if index in (cal.name, cal.key)]
                if len(ret):
                    return ret[0]
                
                raise IndexError(f"Calibration for axis {index} not found")
                    
            elif index =="c": # Channels axis - not found in condition above so it's virtual
                return AxisCalibrationData("c")
            
            else:
                raise IndexError(f"Calibration for axis {index} not found")
            
    def __setitem__(self, index, obj):
        r"""Indexed setter.
        index: int
        obj: AxisCalibrationData object 
        """

        if isinstance(index, int):
            if not isinstance(obj, AxisCalibrationData):
                raise TypeError(f"Expecting an AxisCalibrationData object; got {type(obj).__name__} instead")

            self._calibration_[item] = obj # raises corresponding exception for list API
            self._axistags_[item] = obj.axisInfo
            
        else:
            raise TypeError(f"Index must eb an int; got {type(index).__name} instead")
        
    def __len__(self):
        return len(self._calibration_)
    
    def index(self, item:typing.Union[int, str]):
        r"""
        item: AxisCalibrationData, or str (key or name)
            When a str, returns the first AxisCalibrationData with key == index
            
            When item is 'c' returns the number of axes when no Channels axis exists
        """
        if isinstance(item, AxisCalibrationData):
            return self._calibration_.index(item) # raises appropriate exception for list API
        
        elif isinstance(item, str):
            ret = [k for k, c in enumerate(self._calibration_) if c.key == item ]
            if len(ret):
                return ret[0]
            else:
                if item == "c":
                    return len(self)
                raise KeyError(f"AxisCalibrationData for axis {item} not found")
            
    def isclose(self, other, key, channel = 0, ignore=None, 
                   rtol = RELATIVE_TOLERANCE, 
                   atol =  ABSOLUTE_TOLERANCE, 
                   equal_nan = EQUAL_NAN):
        r"""Compares calibration items between two axes, each calibrated by two AxesCalibration objects.
        
        AxesCalibration objects are considered similar if:
        1) the underlying axes are of the same type
        
        2) they have compatible units (meaning that their units can be easily 
            converted to each other)
            
        3) have numerically close origins and resolutions, whereby "numerically
            close" means their floating point values are within a prescribed 
            tolerance (see numpy.isclose(...) for details)
            
        4) for channel axes, clauses (2) and (3) hold for each channel
        
        These criteria can be relaxed using the "skip" parameter (see below)
        
        The description and name are deliberately NOT compared, as they are not
        considered unique determinants of the calibration.
        
        To compare objects using standard python semantics use the "==" binary operator
        
        Positional parameter:
        =====================
        
        other: AxesCalibration object
        
        Named parameters:
        =================
        
        ignore (default is None): What (if any) calibration properties may be ignored.
            Acceptable values are None or one of the following string keywords:
            "origin"
            "resolution"
            "units"
             or the sequence with any of these keywords
            
            
            
        rtol, atol, equal_nan: passed directly to numpy.isclose(...); See numpy.isclose(...) for details
        
        
        
        """
        
        if not isinstance(other, AxesCalibration):
            raise TypeError("Expecting an AxesCalibration object; got %s instead" % type(other).__name__)
        
        if isinstance(key, vigra.AxisInfo):
            key = key.key
            
        if not self.hasAxis(key):
            raise KeyError("Axis key %s not found in this object" % key)
        
        if not other.hasAxis(key):
            raise KeyError("Axis key %s not found in the object compared against" % key)
        
        if not self.axistags[key].compatible(other.axistags[key]):
            raise ValueError("The two axes are not type-compatible, although they have the same key")
        
        ignoreOrigin=False
        ignoreResolution=False
        ignoreUnits = False
        
        if isinstance(ignore, str) and ignore.lower() in ["units", "origin", "resolution"]:
            if ignore.lower() == "origin":
                ignoreOrigin = True
                
            elif ignore.lower() == "resolution":
                ignoreResolution = True
                
            elif ignore.lower() == "units":
                ignoreUnits = True
            
        elif isinstance(ignore, (tuple, list)) and all([isinstance(s, str) for s in ignore]):
            sk = [s.lower() for s in ignore]
            
            if "origin" in sk:
                ignoreOrigin = True
                
            if "resolution" in sk:
                ignoreResolution = True
                
            if "units" in sk:
                ignoreUnits = True
        
        result = self.getAxisType(key) == other.getAxisType(key)
        
        if result and not ignoreUnits:
            units_compatible = other.getUnits(key) == self.getUnits(key)
            
            if not units_compatible:
                self_dim    = pq.quantity.validate_dimensionality(self.getUnits(key))
                
                other_dim   = pq.quantity.validate_dimensionality(other.getUnits(key))
                
                if self_dim != other_dim:
                    try:
                        cf = pq.quantity.get_conversion_factor(other_dim, self_dim)
                        units_compatible = True
                        
                    except AssertionError:
                        units_compatible = False
                        
                else:
                    units_compatible = True
                    
            result &= units_compatible
        
        if result and not ignoreOrigin:
            result &= np.isclose(self.getDimensionlessOrigin(key), other.getDimensionlessOrigin(key), 
                                 rtol=rtol, atol=atol, equal_nan=equal_nan)
            
        if result and not ignoreResolution:
            result &= np.isclose(self.getDimensionlessResolution(key), other.getDimensionlessResolution(key),
                                 rtol=rtol, atol=atol, equal_nan=equal_nan)
            
        if result:
            if self.getAxisType(key) & vigra.AxisType.Channels > 0:
                result &= self.numberOfChannels() == other.numberOfChannels() # check if they have the same number of channels
                
                if result:
                    for chIndex in range(len(self.channelIndices(key))):
                        if not ignoreUnits:
                            channel_units_compatible = self.getUnits(key, self.channelIndices(key)[str(chIndex)]) == other.getUnits(key, other.channelIndices(key)[str(chIndex)])
                            if not channel_units_compatible:
                                self_dim = pq.quantity.validate_dimensionality(self.getUnits(key, self.channelIndices(key)[chIndex]))
                                other_dim = pq.quantity.validate_dimensionality(other.getUnits(key, other.channelIndices(key)[chIndex]))
                                
                                if self_dim != other_dim:
                                    try:
                                        cf = pq.quantity.get_conversion_factor(other_dim, self_dim)
                                        channel_units_compatible = True
                                        
                                    except AssertionError:
                                        channel_units_compatible = False
                                        
                                else:
                                    channel_units_compatible = True
                                    
                            result &= channel_units_compatible
                        
                        if result and not ignoreOrigin:
                            result &= np.isclose(self.getDimensionlessOrigin(key, self.channelIndices(key)[chIndex]),
                                                other.getDimensionlessOrigin(key, other.channelIndices(key)[chIndex]),
                                                rtol=rtol, atol=atol, equal_nan=equal_nan)
                            
                        if result and not ignoreResolution:
                            result &= np.isclose(self.getDimensionlessResolution(key, self.channelIndices(key)[chIndex]),
                                                other.getDimensionlessResolution(key, other.channelIndices(key)[chIndex]),
                                                rtol=rtol, atol=atol, equal_nan=equal_nan)
                                
        return result
    
    def __str__(self):
        repr_str = self.__repr__().split()
        return "\n".join([f"{self.__repr__()} with {len(self._calibration_)} axes:"] + [cal.__str__() for cal in self._calibration_])
    
    def _repr_pretty_(self, p, cycle):
        p.text(f"{self.__class__.__name__} with {len(self._calibration_)} axes:")
        p.breakable()
        for cal in self._calibration_:
            p.pretty(cal)
        
    def hasAxis(self, key):
        r"""Queries if the axis key is calibrated by this object
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        return key in self.axiskeys and key in self._axistags_
    
    @property
    def axiskeys(self):
        r"""A generator of axiskeys
        """
        yield from (cal.key for cal in self._calibration_)
    
    # @property
    def keys(self):
        r"""Alias to self.axiskeys
        """
        yield from self.axiskeys
    
    @property
    def axistags(self):
        r"""Read-only
        """
        return self._axistags_
    
    @property
    def channels(self):
        return len(self["c"].channels)
    
    @property
    def calibrations(self):
        return self._calibration_
    
    #@property
    def values(self):
        yield from (cal for cal in self)
        
    def items(self):
        yield from ((cal.key, cal) for cal in self)
    
    #@property
    def typeFlags(self, key):
        r"""Read-only
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s is not calibrated by this object" % key)
        
        return self[key]["type"]
    
    def addAxis(self, axisInfo, index = None):
        r"""Register a new axis with this AxesCalibration object.
        
        The calibration values for the new axis can be atomically set using
        the setXXX methods
        
        By default a Channels axis will get a single channel (singleton axis).
        More channels can then be added using setChannelCalibration(), and calibration
        data for each channel can be modified using other setXXX methods
            
        FIXME/WARNING: this function breaks axes bookkeeping by the VigraArray object
        that owns the axistags!!!
        
        Parameters:
        ===========
        axisInfo: vigra.AxisInfo object
        
        Named parameters:
        ================
        index: int or None (default) index of the axis
            when an int, it must be in the closed interval
            [0, len(self.axistags)]
        
        """
        if not isinstance(axisInfo, vigra.AxisInfo):
            raise TypeError("Expecting an AxisInfo object; got %s instead" % type(axisInfo).__name__)
        
        cal = AxisCalibrationData(axInfo)
        axInfo = cal.calibrateAxis(axInfo)
        
        if index is None:
            self._axistags_.append(axInfo)
            self._calibration_.append(cal)
            
        elif isinstance(index, int):
            if index < 0:
                raise ValueError("index must be between 0 and %d, inclusive" % len(self.axistags))
            
            if index == len(self.axistags):
                self._axistags_.append(axInfo)
                self._calibration_.append(cal)
                
            elif index < len(self.axistags):
                self._axistags_.insert(index, axInfo)
                self._calibration_.insert(index, cal)
                
                
        # parse calibration string from axisInfo, it if exists
        self._initialize_calibration_with_axis_(axInfo)
        
    def writeHDF5(self, filenameOrGroup:typing.Union[str, h5py.Group],
                  pathInFile:typing.Optional[str] = "axis_calibrations",
                  mode:typing.Optional[str]="a"):
        from iolib.h5io import get_file_group_child
        
        file, group, childname = get_file_group_child(filenameOrGroup, pathInFile, mode)
        
        axcalgroup = group.create_group(childname)
        
        for k in self:
            caldict = self[k]
            
            axcal_dataset = axcalgroup.create_dataset(caldict.axiskey, data=[caldict.origin, caldict.resolution])
            axcal_dataset.attrs["axis_type"] = axisTypeStrings(caldict["axistype"])
            
    def removeAxis(self, axis):
        r"""Removes the axis and its associated calibration data
        
        Raises KeyError is axis is not found
        
        WARNING: this function breaks axes bookkeeping by the VigraArray object
        that owns the axistags!!!
        
        Parameters:
        ==========
        axis: str or vigra.AxisInfo; when a str, it must be a valid AxisInfo key.
        """
        if isinstance(axis, vigra.AxisInfo):
            key = axis.key
            if axis not in self._axistags_:
                raise KeyError("Axis %s not found" % key)
            
        elif isinstance(axis, str):
            key = axis
            if key not in self._axistags_.keys():
                raise KeyError("Axis %s not found" % key)
                
            axis = self._axistags_[key]
            
        if key not in self._calibration_.keys():
            raise KeyError("Axis %s has no calibration data" % key)
                
                
        self._calibration_.pop(key, None)
        del(self._axistags_[key])
        
    def synchronize(self):
        r"""Synchronizes the axis calibration data.
        
        Updates the AxesCalibration values using the axistags instance contained
        within this AxesCalibration object.
        
        This should be called after calling any VigraArray methods that change 
        the axes layout (inserting or removing an axis, e.g. by creating a lesser
        dimension view, etc). Such methods modify the axistags reference contained
        in this object.
        
        The axistags take priority in the following cases: 
        
        1) if, as a result of Vigra library functions, the axistags have GAINED 
        a new axis, this new axis will get default calibration values which can 
        be later modified individually, by calling one of the setXXX() methods
        of the AxesCalibration object.
        
            NOTE: a Channels axis will get calibration data for channel 0; 
            calibration data for more channels can be added manually, by calling 
            setChannelCalibration().
        
        2) if the axistags have LOST an axis, its calibration data will be removed
        
        """
        new_axes = [axInfo for axInfo in self._axistags_ if axInfo.key not in self._calibration_.keys()]
        obsolete_keys = [key for key in self._calibration_.keys() if key not in self._axistags_.keys()]

        for axInfo in new_axes:
            #self._initialize_calibration_with_axis_(axInfo)
            self.calibrateAxis(axInfo)
        
        for key in obsolete_keys:
            self._calibration_.pop(key, None)
                
        
    def calibrateAxes(self):
        r"""Attaches a calibration string to all axes registered with this object.
        """
        for k, ax in enumerate(self._axistags_):
            self._calibration_[k].calibrateAxis(ax)
            
def hasNameString(s):
    return AxesCalibration.hasNameString(s)
    
def axisChannelName(axisinfo, channel):
    r"""
    Parameters:
    ===========
    axisinfo: vigra.AxisInfo object
    
    channel: int >=0 (0-based index of the channel)
    """
    return AxisCalibrationData(axisinfo).getChannelName(channel)

def axisName(axisinfo):
    r"""Returns the axis name stored in the axis description.
    
    Parameters:
    ===========
    axisinfo: vigra.AxisInfo
    
    Returns:
    =======
    
    A two-elements tuple: (names, indices), where:
    
        names = a list of str
    
        indices = a list of int. 
        
    When axisinfo.isChannel() is True the list of names contains the channel
    names, and the list of indices contains the corresponding channel index.
    
    When axisinfo.isChannel() is False the list of names has only one element
    which is the name of the axis, and the list of indices is empty.
    
    When axisinfo does not have a name XML-formatted string in its description,
    both lists are empty.
    
    It is not guaranteed that the number of channel names equals the size
    of the axis with this axisinfo. If this is required, then it should be 
    checked outside this function.
    
    """
    return AxesCalibration(axisinfo).axisName
    
def isCalibrated(axisinfo):
    r"""Syntactic shorthand for hasCalibrationString(axisinfo.description).
    
    NOTE: Parameter checking is implicit
    
    """
    return AxesCalibration.isAxisCalibrated(axisinfo)

def calibration(axisinfo, asTuple=True):
    r"""Returns the calibration triplet (units, origin, resolution) of an axis.
    
    The tuple is obtained by parsing the calibration string contained in the
    description attribute of axisinfo, where axisinfo is a vigra.AxisInfo object.
    
    If axis is uncalibrated, the function returns (dimensionless, 0.0, 1.0) when
    axis is a channel axis or (pixel_unit, 0.0, 1.0) otherwise.
    
    NOTE: Parameter checking is implicit
    
    """
    if isinstance(axisinfo, vigra.AxisInfo):
        return 
    result = AxesCalibration(axisinfo)
    
    if asTuple:
        return result.calibrationTuple()
    
    else:
        return result
    
def resolution(axisinfo):
    return AxesCalibration(axisinfo).resolution

def hasCalibrationString(s):
    r"""Simple test for what MAY look like a calibration string.
    Does nothing more than saving some typing; in particular it DOES NOT verify
    that the calibration string is conformant.
    
    NOTE: Parameter checking is implicit
    
    """
    return AxesCalibration.hasCalibrationString(s)

def removeCalibrationData(axInfo):
    return AxesCalibration.removeCalibrationData(axInfo)

def removeCalibrationFromString(s):
    r"""Returns a copy of the string with any calibration substrings removed.
    Convenience function to clean up AxisInfo description strings.
    
    NOTE: Parameter checking is implicit
    
    """
    
    return AxesCalibration.removeCalibrationFromString(s)
    
def calibrationString(units=pq.dimensionless, origin=0.0, resolution=1.0, channel = None):
    r"""Generates an axis calibration string from an units, origin and resolution
    
    Positional kewyord parameters:
    
    "units": python quantities Quantity (default is dimensionless)
    
    "origin": float, default is 0.0
    
    "resolution": float, default is 1.0
    
    "channel": integer or None (default); only used for channel axisinfo objects 
    (see below)
    
    Returns an xml string with the following format:
    
    <axis_calibration>
        <units>str0</units>
        <origin>str1</origin>
        <resolution>str2</resolution>
    </axis_calibration>
    
    where:
    
    str0 = string representation of the unit quantity such that it can be passed to
            python' eval() built-in function and, given appropriate namespace or 
            globals dict, return the unit quantity object.
    
    str1, str2 = string representations that can be evaluated to Real scalars, 
        for origin and resolution, respectively.
        
    NOTE 2018-04-29 11:31:04: 
    Channel axes can have more than one channel. Therefore, a calibration
    string will contain an extra (intermediate) node level for the channel index
    (indices are 0-based). 
    
    the channel parameters must then be an integer >= 0
    
    <axis_calibration>
        <channel0>
            <units>str0</units>
            <origin>str1</origin>
            <resolution>str2</resolution>
        </channel0>
        
        <channel1>
            <units> ... </units>
            <origin> ... </origin>
            <resolution> ... </resolution>
        </channel1>
        
        ... etc...
        
    </axis_calibration>
    
    For backward compatibility, channel axes are allowed to contain the old-style
    calibration string (without channel elements) which implies this calibration 
    applies to ALL channels in the data.
    
    
    """
    
    axcal = AxesCalibration(units = units, origin = origin, resolution = resolution,
                            channel = channel)
    
    return axcal.calibrationString(includeChannelCalibration = channel is not None)
    

# def parseDescriptionString(s):
#     r"""Performs the reverse operation to calibrationString.
#     DEPRECATED
#     Positional parameters:
#     ======================
# 
#     s = an XML - formatted string (as returned by calibrationString), or a 
#         free-form string _CONTAINING_ an XML - formatted string as returned 
#         by calibrationString.
#         
#     The function tries to detect whether the argument string 's' contains a
#     "calibration string" with the format as returned by calibrationString 
#     then parses that substring to return a (unit,origin) tuple.
#     
#     If such a (sub)string is not found, the function returns the default 
#     values of (dimensionless, 0.0). If found, the (sub)string must be 
#     correctly formatted (i.e. start/end tags must exist) otherwise the 
#     function raises ValueError.
#     
#     Returns :
#     =========
#     
#     A tuple (python Quantity, real_scalar, real_scalar) containing respectively,
#     the unit, origin and resolution. 
#     
#     Raises ValueError if a calibration string is not found in s
#     
#     """
#     return AxesCalibration.parseDescriptionString(s)

def calibrateAxis(axInfo, cal, channel=None, channelname=None):
    r"""Attaches a dimensional calibration to an AxisInfo object.
    Calibration is inserted as an xml-formatted string.
    (see calibrationString)
    
    Positional parameters:
    ====================
    axInfo = a vigra.AxisInfo object
    
    cal = tuple, list, a python Quantity, or a calibration string
            
        When "cal" is a tuple or list it can contain up to three items:
        
        (Quantity, float, float): units, origin, resolution
    
        (Quantity, float): units, origin (defaut resolution set to 1.0 or what 
            the axInfo provides)
    
        (Quantity,): units; default origin and resolution set to 0.0 and 1.0
        
        When "cal" is a Quantity, the function behaves as above.
        
        When "cal" is a string, it will be checked if it contains an XML-formatted
        calibration string. If found, such a (sub-) string will be inserted in 
        the description attribute of the AxisInfo object (see below).
        
    Named parameters:
    =================
    channel None (default) or a non-negative integer.
        Used only when axInfo.isChannel() is True, in which case it specifies
        to which channel th calibration applies.
        
    Returns:
    ========
    axInfo, axcal
    
    axInfo: A reference to the axInfo with modified description string containing calibration
    information.
    
    axcal: AxesCalibration object
    
    What this function does:
    ========================
    The function creates an XML-formatted calibration string (see 
    calibrationString()) that will be inserted in the description attribute 
    of the axInfo parameter
        
    NOTE (1) If axInfo.description already contains a calibration string, it will 
    be replaced with a new calibration string. No dimensional analysis takes place.
    
    NOTE (2) The default value for the resolution in vigra.AxisInfo is 0.0, which 
    is not suitable. When axInfo.resolution == 0.0, and no resolution parameter
    is supplied, the function will set its value to 1.0; otherwise, resolution 
    will take the value provided in the axInfo.
    
    Technically, resolution values should be strictly positive. However, this
    is NOT enforced.
    
    """
    # set default resolution value if not specified
    resolution = 1.0 if axInfo.resolution == 0 else axInfo.resolution 
    
    if isinstance(cal, (tuple, list)):
        if not isinstance(cal[0], pq.Quantity):
            raise TypeError("First element in a calibration tuple must be a Quantity")
        
        if len(cal) == 1: # (units)
            c_ = (cal[0], 0.0, resolution)
            
        elif len(cal) == 2: # (units, origin)
            c_ = (cal[0], cal[1], resolution)
            
        elif len(cal) == 3: # (units, origin, resolution)
            c_ = [c for c in cal] # if cal is a tuple it isimmutable so we build up a temporary list here
            
            # NOTE also write to the resolution attribute of the axis info object
            resolution = c_[2]
            
        axcal = AxesCalibration(units = c_[0], origin = c_[1], resolution = c_[2],
                                key = axInfo.key, axisname = axisTypeName(axInfo),
                                channel = channel, channelname=channelname)
            
    elif isinstance(cal, pq.Quantity):
        c_ = [cal.units, 0.0, resolution]
        
        axcal = AxesCalibration(units = c_[0], origin = c_[1], resolution = c_[2],
                                key = axInfo.key, axisname = axisTypeName(axInfo),
                                channel = channel, channelname=channelname)
            
            

    elif isinstance(cal, str):
        axcal = AxesCalibration(axisinfo=cal, channel=channel, channelname=channelname) # will raise ValueError if cal not conformant
        
    else:
        raise TypeError("Unexpected type (%s) for calibration argument." % type(cal).__name__)
        
    
    axcal.calibrateAxis(axInfo)
        
    return axInfo, axcal

def getAxisResolution(axisinfo:vigra.AxisInfo, 
                      channel:typing.Optional[typing.Union[int, str]] = None):
    r"""Returns the resolution of the axisinfo object as a Python Quantity.
    """
    if not isinstance(axisinfo, vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    
    axcal = AxisCalibrationData(axisinfo)
    
    if axisinfo.typeFlags & vigra.AxisType.NonChannel == 0:
        if isinstance(channel, (int, str)):
            return axcal.getChannelResolution(channel)
        
        else:
            return axcal.getChannelResolution(0)
        
    else:
        return axcal.resolution
    
def getAxisUnits(axisinfo:vigra.AxisInfo,
                 channel:typing.Optional[typing.Union[int,str]] = None) -> pq.Quantity:
    if not isinstance(axisinfo, vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    axcal = AxisCalibrationData(axisinfo)
    
    if axisinfo.typeFlags & vigra.AxisType.NonChannel == 0:
        if isinstance(channel, (int, str)):
            return axcal.getChannelUnits(channel)
        
        else:
            return axcal.getChannelUnits(0)
        
    else:
        return axcal.units
    
    
def getCalibratedAxisSize(image, axis):
    r"""Returns a calibrated length for "axis" in "image" VigraArray, as a python Quantity
    
    If axisinfo is not calibrated (i.e. does not have a calibration string in its
    description attribute) then returns the size of the axis in pixel_unit.
    
    Parameters:
    ==========
    
    image: vigra.VigraArray
    
    axis: vigra.AxisInfo, axis info key string, or an integer; any of these must 
        point to an existing axis in the image
    
    """
    
    if isinstance(axis, int):
        axsize = image.shape[axis]
        axisinfo = image.axistags[axis]
        
    elif isinstance(axis, str):
        axsize = image.shape[image.axistags.index(axis)]
        axisinfo = image.axistags[axis]

    elif isinstance(axis, vigra.AxisInfo):
        axsize = image.shape[image.axistags.index(axis.key)]
        axisinfo = axis

    else:
        raise TypeError("axis expected to be an int, str or vigra.AxisInfo; got %s instead" % type(axis).__name__)
    
    axcal = AxisCalibrationData(axisinfo)
    
    # FIXME what to do when there are several channels?
    
    return axcal.calibratedDistance(axsize)

def getAxisOrigin(axisinfo):
    r"""Returns the axis origin as a Python Quantity
    """
    if not isinstance(axisinfo. vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    
    # FIXME what to do when there are several channels?
    
    axcal = AxesCalibration(axisinfo)
    
    return axcal.getOrigin(axisinfo.key)
    
# NOTE: for old pickles
AxisCalibration = AxisCalibrationData
