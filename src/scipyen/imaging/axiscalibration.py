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
import xml.etree.ElementTree as ET
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
from core import scipyen_quantities as scq
from core.scipyen_quantities import (arbitrary_unit, 
                            space_frequency_unit,
                            angle_frequency_unit,
                            channel_unit,
                            pixel_unit,
                            quantity2scalar,
                            unitQuantityFromNameOrSymbol,
                            unitsConvertible,
                            )

from core.datatypes import (is_numeric, is_numeric_string, MissingType)
from core.constants import ( RELATIVE_TOLERANCE, ABSOLUTE_TOLERANCE, EQUAL_NAN)

from core.utilities import (reverse_mapping_lookup, unique, counter_suffix,
                            isclose, all_or_all_not)

from core.traitcontainers import DataBag

from core.prog import (ArgumentError, scipywarn, print_styled)

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
                        getAxisTypeFlagsInt
                        )

# forward declaration needed for the descriptor classes below.
class AxisCalibrationData: pass
class ChannelCalibrationData: pass

class CalSpec(typing.NamedTuple):
    origin: typing.Optional[typing.Union[numbers.Number, pq.Quantity, MissingType]] = None
    maximum: typing.Optional[typing.Union[numbers.Number, pq.Quantity, MissingType]] = None
    units:typing.Optional[typing.Union[pq.Quantity, MissingType]] = None
    
class NamedCalSpec(typing.NamedTuple):
    origin:typing.Optional[typing.Union[numbers.Number, pq.Quantity, MissingType]] = None
    maximum:typing.Optional[typing.Union[numbers.Number, pq.Quantity, MissingType]] = None
    units:typing.Optional[typing.Union[pq.Quantity, MissingType]] = None
    name:typing.Optional[str] = None
    
class FullCalSpec(typing.NamedTuple):
    origin:typing.Optional[typing.Union[numbers.Number, pq.Quantity, MissingType]] = None
    maximum:typing.Optional[typing.Union[numbers.Number, pq.Quantity, MissingType]] = None
    units:typing.Optional[typing.Union[pq.Quantity, MissingType]] = None
    name:typing.Optional[str] = None
    index:int = 0,
    size:int = 0,
    type:vigra.AxisType = vigra.AxisType.UnknownAxisType
    
# NOTE: 2025-04-17 13:28:42 
# Don't use slots=True because it messes up the Descriptor functionality
@dataclass(eq=False)
class CalibrationData:
    r'''Superclass for AxisCalibrationData and ChannelCalibrationData'''
    
    # units:pq.Quantity = field(default=pq.arbitrary_unit)
    # r'''The physical units
    # Currently, this must be set to MISSING for a Channels-type axis.
    # '''
    
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
    def owner(self) -> AxisCalibrationData | None:
        r"""Alias to self.parent"""
        return self.parent
    
    @owner.setter
    def owner(self, obj:typing.Optional[AxisCalibrationData]):
        self.parent = obj
    
    
    @property
    def calibrationString(self) -> str:
        fnames = tuple(filter(lambda x: x is not None, map(lambda f: self._to_xml_(f.name), dataclasses.fields(self))))
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
    
    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text(f"{self.__class__.__name__}")
        else:
            with p.group(4, f"{self.__class__.__name__}:\n"):
                for k, f in enumerate(dataclasses.fields(self)):
                    if k == 0:
                        p.text(f"    {f.name}: ")
                    else:
                        p.text(f"{f.name}: ")
                        
                    # value = getattr(self, f.name, None)
                    # if f.name == "parent" and isinstance(value, AxisCalibrationData):
                    #     value = value.key if (isinstance(value.key, str) and len(value.key.strip())) else value.name if (isinstance(value.name, str) and len(value.name.strip())) else axisTypeStrings(value.type)
                    # p.pretty(value)
                    p.pretty(getattr(self, f.name, None))
                    p.breakable()
        
    def _to_xml_(self, param):
        # print(f"{self.__class__.__name__}_to_xml_(param = {param})")
        value = getattr(self, param, None)
        if value is dataclasses.MISSING:
            return
        
        ss = [f"<{param}>"]
        
        if value is not None:
            if param == "type":
                s = "|".join(axisTypeStrings(value))
            
            elif param == "units":
                # output the dimensionality's string property
                if isinstance(value, pq.Quantity):
                    s = value.units.dimensionality.string
                else:
                    return
                
            elif param == "index":
                s = "%d" % value
                
            elif isinstance(value, (float, complex)) or (isinstance(value, pq.Quantity) and value.ndim == 0): # ("origin", "resolution", "maximum", "minimum")
                # includes np.nan, math.nan, np.inf, math.inf
                # and purely scalar Quantities
                # NOTE: 2025-04-13 09:53:33 WARNING
                # posible loss of precision here!
                # hence we need the fc_template field
                s = self.fc_template.format(value)
                
            else:
                # includes any int, str, pd.NA, None, bool, bytes, bytearray
                s =f"{value}"
                # raise TypeError(f"Unsupported value type {type(value).__name__}")
                
            ss.append(s)
        
        ss.append(f"</{param}>")
        
        return "".join(ss) 
    
    def __eq__(self, other) -> bool:
        # print(f"{self.__class__.__name__}.__eq__")
        ret = self.__class__ == other.__class__
        ret &= self.equal_nan == other.equal_nan
        if ret:
            if self.equal_nan:
                nanfields = list(filter(lambda x: math.isnan(x[1]), filter(lambda x: x[0] != "channels" and isinstance(x[1], numbers.Number), map(lambda f: (f.name, getattr(self, f.name)), dataclasses.fields(self)))))
                ret &= all(map(lambda f: math.isnan(getattr(other, f[0], np.nan)), nanfields))
                
                if ret and getattr(self, "isChannels", False):
                    if ret:
                        channels = getattr(self, "channels", list())
                        ochannels = getattr(other, "channels", list())
                        ret &= len(channels) == len(ochannels)
                        
                        if ret and len(channels):
                            ret &= all(map(lambda x: ochannels[x[0]] == x[1], enumerate(channels))) 
                    
            else:
                ret &= super(self).__eq__(other)
                
        return ret
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def isclose(self, other, 
                rtol = RELATIVE_TOLERANCE, 
                atol = ABSOLUTE_TOLERANCE,
                equal_nan = EQUAL_NAN,
                use_math=True,
                ignore:typing.Optional[typing.Union[str, tuple, list]] = None):
        
        # print(f"\n{self.__class__.__name__}.isclose:")
        # print(f"\tself: {self}\n")
        # print(f"\tother: {other}\n")
        
        if ignore is not None:
            if all(v not in ignore for v in ('units', 'origin','resolution','maximum')):
                ignore = None
        
        if rtol is None:
            rtol = self.relative_tolerance
            
        if atol is None:
            atol = self.absolute_tolerance
        
        # print(f"\n{self.__class__.__name__}.isclose: other class is self class: {other.__class__ == self.__class__}")
        ret = other.__class__ == self.__class__
        if ret:
            if hasattr(self, "isChannels"):
                ret &= hasattr(other, "isChannels")
                if ret:
                    ret &= self.isChannels == other.isChannels
            
        if ret:
            if hasattr(self, "isChannels") and self.isChannels:
                ret &= self.nChannels == other.nChannels
                if ret:
                    ret &= all(list(map(lambda c: self.channels[c].isclose(other.channels[c], rtol=rtol, atol=atol, equal_nan=equal_nan, use_math=use_math, ignore=ignore), range(self.nChannels))))
                    
                # print(f"\n{self.__class__.__name__}.isclose: testing channels: -> {ret}")
                    
                
            else:
                if ret and (ignore is None or "units" not in ignore):
                    # print(f"\n{self.__class__.__name__}.isclose: testing units: {self.units} <-> {other.units}")
                    try:
                        if all(isinstance(u, pq.Quantity) for u in (self.units, other.units)):
                            ret &= unitsConvertible(self.units, other.units)
                            
                        elif any(u in (MISSING, None) for u in (self.units, other.units)):
                            ret &= self.units == other.units
                        else:
                            ret &= False
                        # ret &= unitstest
                        # if not unitstest:
                        #     print(f"\n{self.__class__.__name__}.isclose: convertible units: {unitstest}")
                    except:
                        traceback.print_exc()
                        print(f"self.units: {self.units}, other.units: {other.units}")
                    
                if ignore is not None and "units" in ignore:
                    if isinstance(ignore, str):
                        ignore = ignore.replace("units", "")
                        if len(ignore.strip()) == 0:
                            ignore = None
                            
                    elif isinstance(ignore, (tuple, list)):
                        ignore = list(s for s in ignore if s != "units")
                        if len(ignore)==0:
                            ignore = None
                            
                
                # print(f"\n{self.__class__.__name__}.isclose: ignore is {ignore}")
                if ret:
                    if ignore is None:
                        cal_p = list(getattr(self, p) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if hasattr(self, p))
                        
                        if self.units != other.units:
                            oth_p = list(getattr(other, p).rescale(self.units) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if hasattr(self, p))
                            # oth_p = list(v.rescale(getattr(other, p), self.units) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if hasattr(self, p))
                            
                        else:
                            oth_p = list(getattr(other, p) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if hasattr(self, p))
#                             
#                         print(f"\n{self.__class__.__name__}.isclose with ignore: {ignore}")
#                         print(f"\t in\n\t{self} and\n\t{other}:")
#                         print(f"\ncal_p = {cal_p}")
#                         print(f"\noth_p = {oth_p}")
                    else:
                        cal_p = list(getattr(self, p) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if p not in ignore and hasattr(self, p))
                        oth_p = list(getattr(other, p) for p in ("calibratedOrigin", "calibratedResolution", "calibratedMaximum") if p not in ignore and hasattr(other, p))
                                
                                
                        # print(f"\n{self.__class__.__name__}.isclose with ignore: {ignore}")
                        # print(f"\ncal_p = {cal_p}")
                        # print(f"\noth_p = {oth_p}")
                            
                    ret &= len(cal_p) == len(oth_p) and all(isclose(p[0], p[1], rtol=rtol, atol=atol, equal_nan=equal_nan, use_math=use_math) for p in zip(cal_p, oth_p))
                    
                    
        # if not ret:
        #     print(f"\n{self.__class__.__name__}.isclose will return {ret}")
        return ret
                 
class CalibrationUnitsDescriptor:
    r"""Use this for the 'units' attribute of an AxisCalibrationData object.
    This enforces the rule that only NonChannel axes have this attribute with a
    pq.Quantity value, while setting it to dataclasses.MISSING for a Channels
    axis."""
    def __init__(self, *, default:typing.Union[pq.Quantity, MissingType, str] = pq.arbitrary_unit):
        if isinstance(default, str):
            default = scq.str2quantity(default)
        if isinstance(default, pq.Quantity):
            default = default.units # see NOTE: 2025-04-17 13:49:04 below
        elif not isinstance(default, MissingType):
            raise TypeError(f"Expecting a Quantity, a string representation of a Quantity, or dataclasses.MISSING; instead, got a {type(default).__name__}")
        
        self._default_ = default
        
    def __set_name__(self, owner, name:str):
        self._name_ = f"_{name}_"
        
    def __get__(self, obj, type_):
        if obj is None:
            return self._default_
        
        if isinstance(obj, ChannelCalibrationData):
            return getattr(obj, self._name_, self._default_)
        
        if not isinstance(obj, AxisCalibrationData):
            return self._default_
        
        obj_axtype = getattr(obj, "type", None)
        if obj_axtype is None:
            scipywarn(f"Undetermined axis type flag")
            return 
        if not obj_axtype & vigra.AxisType.AllAxes:
            return
        if obj_axtype & vigra.AxisType.Channels:
            # scipywarn(f"The {self._name_} fields for a Channels axis is meaningless — try one of its Channel calibrations")
            return dataclasses.MISSING
        
        ret = getattr(obj, self._name_, self._default_)
        return ret
    
    def __set__(self, obj, value:typing.Union[pq.Quantity, str, MissingType]):
        # print(f"{self.__class__.__name__}.__set__: value = {value}")
        if not isinstance(obj, (AxisCalibrationData, ChannelCalibrationData)):
            return
        
        if isinstance(value, str):
            value = scq.str2quantity(value)
        if isinstance(value, pq.Quantity):
            value = value.units
        elif not isinstance(value, (numbers.Number, MissingType, str)):
            raise TypeError(f"Expecting a scalar Quantity, a numbers.Number or a string representation of a scalar Quantity; instead, got {type(value).__name__}")
        
        if isinstance(obj, ChannelCalibrationData):
            if isinstance(value, MissingType):
                # enforce the units on ChannelCalibrationData
                value = pq.arbitrary_unit
            setattr(obj, self._name_, value)
            return
        
        obj_axtype = getattr(obj, "type", None)
        
        if not obj_axtype & vigra.AxisType.AllAxes:
            scipywarn(f"The owner (a {type(obj).__name__}) has an invalid type attribute: {obj_axtype}")
            return
        
        elif obj_axtype & vigra.AxisType.Channels:
            setattr(obj, self._name_, dataclasses.MISSING)
        else:
            if isinstance(value, str):
                value = scq.str2quantity(value)
                
            if isinstance(value, pq.Quantity):
                # NOTE: 2025-04-17 13:49:04
                # either Quantity.units or UnitQuantity.units returns a 
                # UnitQuantity so no need to check if it is scalar 
                value = value.units 
                
            elif isinstance(value, MissingType):
                # silently enforce a unit on NonChannel AxisCalibrationData
                value = pq.arbitrary_unit
            else:
                raise TypeError(f"Expecting a Quantity, or a string representation of a Quantity; instead, got a {type(value).__name__}")
            setattr(obj, self._name_, value)
        
class CalibrationScalarDescriptor:
    r"""Use this for the following scalar attributes of AxisCalibrationData:
    'origin', 'maximum', 'resolution'
    This enforces the rule that these attributes get numeric values only for 
    NonChannel axes, but are set to dataclasses.MISSING for Channels axes.
    WARNING:
    Before setting a value to any of these attributes, the 'unit' attrribute of
    the AxisCalibrationDatamust have been appropriately set!.
    
    """
    def __init__(self, *, default:typing.Union[numbers.Number, pq.Quantity, MissingType, str]=0.0):
        if isinstance(default, str):
            default = scq.str2quantity(default)
            
        if isinstance(default, pq.Quantity):
            if not scq.isScalar(default):
                raise ValueError(f"Expecting a scalar Quantity; instead, got a Quantity array with {default.size} elements")
            default = scq.ensureScalar(default).magnitude
            # NOTE: 2025-04-15 23:02:24
            # strip away the units
            default = scq.quantity2scalar(default)
            
        elif not isinstance(default, (numbers.Number, MissingType, str)):
            raise TypeError(f"Expecting a numbers.Number, a scalar Quantity, or a string representation of a scalar quantity; instead, got {type(default).__name__}")
        
        self._default_ = default
        
    def __set_name__(self, owner, name:str):
        self._name_ = f"_{name}_"
        
    def __get__(self, obj, type_):
        r"""Returns None if the owner is invalid"""
        if obj is None:
            return self._default_
        
        if isinstance(obj, ChannelCalibrationData):
            return getattr(obj, self._name_, self._default_)
        
        if not isinstance(obj, AxisCalibrationData):
            return self._default_
        
        obj_axtype = getattr(obj, "type", None)
        if obj_axtype is None:
            scipywarn(f"Undetermined axis type flag")
            return 
        if not obj_axtype & vigra.AxisType.AllAxes:
            scipywarn(f"The owner (a {type(obj).__name__}) has an invalid type attribute: {obj_axtype}")
            return
        if obj_axtype & vigra.AxisType.Channels:
            # scipywarn(f"The {self._name_} fields for a Channels axis is meaningless — try one of its Channel calibrations")
            return datatypes.MISSING
        return getattr(obj, self._name_, self._default_)
    
    def __set__(self, obj, value:typing.Union[numbers.Number, pq.Quantity, MissingType, str]):
        r"""Setter. The owner object must have a valid 'type' attribute"""
        # print(f"{self.__class__.__name__}.__set__ value = {value}")
        if not isinstance(obj, (AxisCalibrationData, ChannelCalibrationData)):
            return
        
        if isinstance(value, str):
            value = scq.str2quantity(value)
        if isinstance(value, pq.Quantity):
            value  = scq.ensureScalar(value)
            units = getattr(obj, "units", None)
            # NOTE: 2025-04-16 23:14:39
            # check and rescale to calibration units
            if isinstance(units, pq.Quantity):
                if value.units != units:
                    if scq.unitsConvertible(value, units):
                        value = value.rescale(units)
                    else:
                        raise TypeError(f"Value has {value.units} that are incompatible with the units of this object ({units})")
            value = scq.quantity2scalar(value)
            
        elif not isinstance(value, (numbers.Number, MissingType, str)):
            raise TypeError(f"Expecting a scalar Quantity, a numbers.Number or a string representation of a scalar Quantity; instead, got {type(value).__name__}")
        
        if isinstance(obj, ChannelCalibrationData):
            setattr(obj, self._name_, value)
            return 
        
        obj_axtype = getattr(obj, "type", None)
        if not obj_axtype & vigra.AxisType.AllAxes:
            scipywarn(f"The owner (a {type(obj).__name__}) has an invalid type attribute: {obj_axtype}")
            return
        # NOTE: 2025-04-15 23:03:56
        # set this to MISSING in case obj is an AxisCalibrationData for a Channels axis
        if obj_axtype & vigra.AxisType.NonChannel:
            setattr(obj, self._name_, value)
        else:
            # see NOTE: 2025-04-15 23:03:56
            setattr(obj, self._name_, dataclasses.MISSING)
        
class CalibrationChannelsDescriptor:
    def __init__(self, *, default:typing.Sequence=list()):
        self._default_ = list()
        # self._default_ = dataclasses.MISSING
        if isinstance(default, typing.Sequence):
            chcals = list(filter(lambda x: isinstance(x, ChannelCalibrationData), map(lambda x: ChannelCalibrationData(**x._asdict()) if isinstance(x, CalSpec) else ChannelCalibrationData(**x) if isinstance(x, dict) else x if isinstance(x, ChannelCalibrationData) else None, default)))
            if len(chcals):
                self._default_ = chcals
            else:
                self._default_ = list()
        
    def __set_name__(self, owner, name:str):
        self._name_ = f"_{name}_"

    def __get__(self, obj, type_):
        if obj is None:
            ret = self._default_
        else:
            obj_axtype = getattr(obj, "type", None)
            if not obj_axtype & vigra.AxisType.AllAxes:
                scipywarn("Not a valid axis type flag")
                ret = list()
            
            elif obj_axtype & vigra.AxisType.NonChannel:
                scipywarn("Noft a Channels axis!")
                ret = list()
                # ret = dataclasses.MISSING
                
            else: ret = getattr(obj, self._name_, self._default_)
            
        return ret
    
    def __set__(self, obj, value:typing.Sequence = list()):
        obj_axtype = getattr(obj, "type", None)
        if not obj_axtype & vigra.AxisType.AllAxes:
            setattr(obj, self._name_, list())
            return
        # NOTE: 2025-04-15 23:05:35
        # set this attribute only for a Channels axis; otherwise set it to MISSING
        if isinstance(value, typing.Sequence):
            if obj_axtype & vigra.AxisType.Channels:
                obj_size = getattr(obj, "size", 0)
                chcals = list(filter(lambda x: isinstance(x, ChannelCalibrationData), map(lambda x: ChannelCalibrationData(**x._asdict()) if isinstance(x, CalSpec) else ChannelCalibrationData(**x) if isinstance(x, dict) else x if isinstance(x, ChannelCalibrationData) else None, value)))
                if len(chcals):
                    # NOTE: 2025-04-18 11:51:28
                    # ensure the channel calibrations get this object as parent
                    for chcal in chcals:
                        chcal.parent = obj
                    if obj_size == 0 and len(chcals) > 1:
                        scipywarn(f"Mismatch between owner axis size (0), and {len(chcals)} ChannelCalibrationData objects being assigned; owner size will be adjusted")
                        setattr(obj, "size", len(chcals))
                    elif obj_size > 1 and obj_size != len(chcals):
                        scipywarn(f"Mismatch between owner axis size ({obj_size}), and {len(chcals)} ChannelCalibrationData objects being assigned; owner size will be adjusted")
                        setattr(obj, "size", len(chcals))
                        
                else:
                    if len(chcals) == 0:
                        if obj_size == 0:
                            chcals = [ChannelCalibrationData(name="channel_0", index=0, parent=obj)] # ensure a single ChannelCalibrationData
                        else:
                            # BUG: 2025-04-15 23:34:01 FIXME/TODO
                            # not sure this is a bug or feature ?!? surely poor design...
                            scipywarn("No valid channel calibrations were specified; this will ERASE the channels attribute an set the owner axis size to 0")
                            setattr(obj, "size", len(chcals))
                        
                setattr(obj, self._name_, chcals)
                
            else:
                # setattr(obj, self._name_, dataclasses.MISSING)
                setattr(obj, self._name_, list())
                
        else:
            raise TypeError(f"Expecting a sequence; instead got {type()}")

# Don't use slots=True because it messes up the Descriptor functionality
@dataclass(eq=False)
class ChannelCalibrationData(CalibrationData):
    r""" Calibration for a channel in a Channels axis 
        
    Fields inherited from CalibrationData:
        'name' : str — here, the name of the channel
        'relative_tolerance' : float — used for numerical comparison e.g.
            np.isclose or math.isclose
        'absolute_tolerance' : float — used for numerical comparison e.g.
            np.isclose or math.isclose
        'equal_nan' : bool — used in comparing two ChannelCalibrationData objects.
            Python treats two NaN numbers are distinct, i.e., 
                math.nan == math.nan
                -> False
        
            This results in two CalibrationData object beign "seen" as different
            when the same numeric field has math.nan value in both of them, even
            though the other fields are numerically identical.
        
            Setting 'equal_nan' to True (the default) avoids this effect.
        
        'fc_template': str — format template for string represntations of
            numeric data (sets the precision for converting to/from an 
            AxisInfo description string)
        
    Specific fields (all scalars):
        'index': int  = the channel index
        
        'origin':float = 0.0, the channel's minimum value, in self.units
        
        'maximum':float = math.nan, the channel's maximum value, in self.units
    
        'units':pq.Quantity = pq.arbitrary_unit (scalar), the physical units 
            associated with the values in this channel. See NOTE 3 below.
        
        'parent': AxisCalibrationData or None; the "owner" of this ChannelCalibrationData
            object.
        
        'expression': str or None - algebraic expression relating pixel value 'x'
            to physical measure 'y'. 
        
            The expression is evaluated in the scope where the 'calibrated'
            physical measure is calculated — this is can be:
            • the scope of the imaging.axiscalibration module,
            • anywhere else this expression might have to be evaluated: 
                ∘ the module of a function call that evalutes it,
                ∘ the Scipyen console workspace
        
            The expression can contain:
            • literals of unary mathematical functions (i.e., that take one 
            argument, e.g. sin, gamma, etc); these functions are defined in 
            the math module of the standard Python library, or in the numpy
            module; 
                ∘ if evaluating directly, these function literals MUST be given 
                    with the name of their defining module (e.g. math.sin, 
                    math.gamma, np.sin) UNLESS they have been imported directly
                    in the scope (namespace) where the expession is evaluated
        
                ∘ if using pymep, then the 'math.' module need not be 
                    supplied
        
                ∘ openexpression does NOT easily/directly support mathematical
                functions, just arithmetic operators (and boolean, in the boolean mode)
                This seems quite powerful, but requires customization.
        
                ∘ binary of higher order functions can be transformed to unary
                functions through the functools.partial (or functools.partialmethod)
                functions; however, I am not yet sure if they can be parsed by
                existing expression parsers (e.g., openexpressions, pymep, etc);
                thus they are better used only when directly evaluating the
                expression string, provided they are in the scope.
        
            • numeric literals will be parsed as constants in the expression
                these can be scalars, or scalar Quantities; however, NOTE that
                some parsers (openexpressions) do NOT directly support Quantity 
                literals
        
                The workaround for openexpressions is to use a symbol for the 
                Quantity units and then include that symbol in the evaluation 
                "context", e.g. :
        
                mathematical expression: Kd * x / fMax
        
                where Kd = 2.3 μM a Quantity constant, fMax is a scalar constant, 
                    say 4096
        
                This can be evaluated using openexpressions in several ways:
        
                a) s1 = "kd * x / xMax" 
                   var1 = {"kd": 2.3*pq.uM, "x":<pixel value>, "xMax": 4096} 
                   expr1 = openexpressions.Parser.Parser().parse(s1)
                   expr1.eval(var1)
        
                   Here, both constants are given as symbols.
        
                b) s2 = "2.3 * um * x / xMax" 
                   var2 = {"um": pq.uM, "x":<pixel value>, "xMax": 4096} 
                   expr1 = openexpressions.Parser.Parser().parse(s2)
                   expr2.eval(var2)
        
                   Here, magnitude of the quantity constant is given as numeric 
                   literal, but its units are given as a symbol
        
                c) s3 = "2.3 * um * x / 4096" 
                   var3 = {"um": pq.uM, "x":<pixel value>} 
                   expr3 = openexpressions.Parser.Parser().parse(s3)
                   expr3.eval(var3)

                   Here, both constant are given as numeric literals; only the 
                   units are passed as symbol
        
                In all three examples, the actual pixel value must be supplied
                in the "context" dictionary mapped to the MANDATORY symbol 'x'
                (lower case).
        
        
            • symbol literals (name of constants)
                ∘ when using direct evaulation, these symbols MUST be defined 
                (i.e. bound to numerical values - scalar or arrays) in the scope
                
                ∘ when using openexpressions, these symbols must be supplied as
                a dict (symbol ↦ value) to the eval method of the expression; 
                this supports Quantity literals as values
        
                ∘ the only restriction here is that the symbol 'x' (lower case)
                is reserved to the 'pixel' value in the array
        
        NOTE 1: There is no 'resolution' field in this class.
        
        NOTE 2: The physical measure represented by the data points in one channel
        of the array ('pixels', 'voxels', etc) is usually a continuous, i.e., analog,
        quantity; yet, the array data point itself is a discrete one. This 
        discretization process is called "quantization" and depends on the underlying
        numerical precision of the system that recorded the data (and thus on the 
        number of bits, or 'quantization level' 𝑳, allocated for a data point)
        In the future, I may add a 'resolution' field to reflect this. 
        
        To put it in another way, a digital "image" is a "many-to-few" mapping of
        values from a large, and often continuous (hence infinite and uncountable)
        "input" set — e.g the intensity of light captured by the light-sensing 
        device — to values on a smaller (and countable) "output" set, possibly 
        with infinite cardinality.
        
        Quantization introduces rounding and truncating, which can be uniform 
        (i.e., with a constant step size) or not. 
        
        This process is non-linear and irreversible.
        
        When the "output" set is finite, its cardinality represents the number of 
        possible values it contains — or "quantization levels". In computers, this
        depends on the memory size allocated for each value, in bits: 
        
            𝒏 bits store 2ⁿ different values 
        
        For an array of data recorded in 16 bit values, the output set contains
        2¹⁶ = 65536 possible discrete values. In reality the array data may span
        a subset of this, especially when there is a "ceiling" or a "floor" in
        the input set; also, the actual physical input might have been produced by
        a sequence of physical interactions (photelectric effect, further electronic
        amplification, etc) before beng wuantized. This which makes the concept of
        "resolution", and its use, far less trivial that it may appear.
        
        NOTE 3: This channel "calibration" attaches a physical quantity to
        the (discrete) values in the array. The relation between the array data
        elements ('pixel' intensities) and the physical measure is a transformation
        ranging from the simplest identity transform (i.e. attaching a physical unit
        to the 'pixel' value) to linear or non-linear expressions.
        
        In the former case, the pixel numerical value is unchanged; in the latter,
        a completely new value is assigned¹ to the pixel.
        
        FIXME: re-write the documentation
        
        Therefore it should NOT be confused 
        with the physical calibration that sets up a map between the values of the 
        array's data points and the underlying quantity that generated the array's
        data. The latter is typically used to infer (or estimate) the physical 
        measure from the array data values (or pixel itensity, in imaging terms)
        sich as "calibrating" fluorescence data obtained from a fluorescent 
        "indicator". Such process effectively generates a new array of values from
        an array of data points (pixel intensities), wgere the new values are related
        to the original ones by a linear or non-linear transformation. For eaxmple,
        see Helmchen, F. "Calibration of Fluorescent Calcium Indicators" (2011),
        Cold Spring Harb Protoc; doi:10.1101/pdb.top120
        
        WARNING about the 'units' field and related and scalar fields 
        'origin', and 'maximum'
        
        The units can be changed by assigning this field any python Quantity, but 
        the scalar values for 'origin', & 'maximum' will NOT be recalculated 
        or rescaled. Theis values should be recalculated as necessary and set to 
        corerect values manually.
        
        A Quantity can also be assigned directly to the 'origin' and 'maximum',
        however:
        • The field will only store its "magnitude" (i.e. numerical value without
        dimensionality) in the respective field
        • If the units of the new value are different from the units of the 
        calibration, but convertible to these, then the numerical value assigned
        to the field will first be rescaled to the units of the calibration. If
        the units of the new value are not convertible to the units of the 
        calibration, an Exception will be raised.
        
        Therefore the recommended way to change a calibration is:
        1) Assign new units
        2) If the new units are convertible to the original units,
            rescale each value of the scalar field to the new units, assign back
            the resulting magnitude to the respective field .
            Othwerise, ATTENTION:  make sure that the scalar field values make 
            sense given the new units.
    """
        
    index:int = 0 
    r'''channel index'''
    
    acquisition_index:int = 0
    r"""channel acquisition index.
    Some acquistion software may start channel numbering at 1; moreover, several
    channels may be save as separate files, yet are assigned different channel 
    numbers to indicate they belong to the same data set.
    
    Therefore, in the final vigra array, a channel with acquisition index of, say,
    1, may actually correspond to the 0ᵗʰ channel in the channels axis. When
    other channels are acquired but stored in separate single-channel image arrays, 
    the 0ᵗʰ channel of those image arrays will corresponds to higher channel
    acqusition indices, etc.
    
    So for reaons of sanity, let's store this variable as well.
    """
    
    origin:CalibrationScalarDescriptor = CalibrationScalarDescriptor(default = 0.0) # is this really needed?
    r"""channel's minimum value, in self.units, as float"""
    
    maximum:CalibrationScalarDescriptor = CalibrationScalarDescriptor(default = np.nan) # is this really needed?
    r"""channel's maximum value, in self.units, as float"""
    
    units:CalibrationUnitsDescriptor = CalibrationUnitsDescriptor(default=pq.arbitrary_unit)
    
    parent:typing.Optional[AxisCalibrationData] = None
    
    def __post_init__(self):
        r"""Performs a limitaed curation of the fields.
        If name is not set, then it will be set to 'channel_<index>' where
        <index> if the value of the 'index' attribute.
    
        NOTE: The value of the 'index' attribute is NOT checked; make sure 
        that this value is unique among other channel calibration data in a given 
        axis
        """
        if not isinstance(self.name, str) or len(self.name.strip()) == 0:
            self.name = f"channel_{self.index}"
    
    @property
    def calibrationString(self) -> str:
        name = self.name if isinstance(self.name, str) and len(self.name.strip()) else f"channel_{self.index}"

        strlist = [f"<{name}>"]
        for param in sorted(filter(lambda x: x!= "parent", map(lambda x: x.name, dataclasses.fields(self.__class__)))):
            txt = self._to_xml_(param)
            if isinstance(txt, str): 
                strlist.append(txt)
        strlist.append(f"</{name}>")
        
        return "".join(strlist)
    
    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text(f"{self.__class__.__name__}")
        else:
            g = 2
            with p.group(g, f"{self.__class__.__name__}:\n"):
                for k, f in enumerate(dataclasses.fields(self)):
                    # p.text(f"{f.name}: ")
                    if k == 0:
                        p.text(f"{' '*p.indentation}{f.name}: ")
                    else:
                        p.text(f"{f.name}: ")
                        
                    value = getattr(self, f.name, None)
                    if f.name == "parent":
                        if isinstance(value, AxisCalibrationData):
                            vkey = value.key if (isinstance(value.key, str) and len(value.key.strip())) else "?"
                            vname = value.name if (isinstance(value.name, str) and len(value.name.strip())) else axisTypeStrings(value.type)
                            # value = f"{type(value).__name__}: name = '{vname}' (index = {value.index}, key = '{vkey}')"
                            p.text(type(value).__name__)
                            p.text(" (")
                            p.text("index = ")
                            p.text(f"{value.index}")
                            p.text(", name = ")
                            p.text(f"'{vname}'")
                            p.text(", key = ")
                            p.text(f"'{vkey}'")
                            p.text(")")
                        else:
                            p.text(None)
                    else:
                        p.pretty(value)
                    p.break_()

    def rescale(self, u:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality, str]) -> None:
        if isinstance(u, str):
            u = scq.str2quantity(u)
        if not scq.unitsConvertible(u, self.units):
            raise ValueError(f"New units ({u}) are incompatible with current units ({self.units}) and therefore, the calibration cannot be rescaled.")
            
        # NOTE: 2025-04-17 10:44:36
        # the next two calls will throw exceptions if self.units are not convertible
        # to the new units
        new_o = self.calibratedOrigin.rescale(u)
        new_m = self.calibratedMaximum.rescale(u)
        self.origin = scq.quantity2scalar(new_o)
        self.maximum = scq.quantity2scalar(new_m)
        self.units = u
        
    def calibratedValue(self, value) -> pq.Quantity:
        r"""Simply applies the physical units to the array value"""
        return value * self.units
    
    def calibratedMeasure(self, value) -> pq.Quantity:
        r"""Calls self.calibratedValue(value).
        For backward compatibility.
        """
        return self.calibratedValue(value)
    
    @property
    def calibratedOrigin(self) -> pq.Quantity:
        return self.origin * self.units
    
    @property
    def calibratedMaximum(self) -> pq.Quantity:
        return self.maximum * self.units
        
    @singledispatchmethod
    @classmethod
    def new(cls, o:object):
        raise NotImplementedError(f"This method does not support {type(o).__name_} arguments")

    @new.register(str)
    @classmethod
    def _(cls, s:str):
        return cls.new(ET.fromstring(s))
    
    @new.register(dict)
    @classmethod
    def _(cls, d:dict):
        if cls.isCalibration(d):
            return cls(**d)
    
    @new.register(ET.Element)
    @classmethod
    def _(cls, e:ET.Element):
        fnames = tuple(map(lambda f: f.name, dataclasses.fields(cls)))
        # print(f"{print_styled(f'\n{cls.__name__}.new[ET.Element]: fnames -> {fnames}', color='yellow')}")
        data = dict()
        for c in e:
            if c.tag in fnames:
                # val = cls._from_xml_text_(c.tag, c.text)
                # print(f"{print_styled(f'\n\tc.tag: {c.tag} -> {val}', color='yellow')}")
                # data[c.tag] = val
                
                data[c.tag] = cls._from_xml_text_(c.tag, c.text)
                
        # print(f"{cls.__name__}.new({data})")
        return cls.new(data)
        
# Don't use slots=True because it messes up the Descriptor functionality
@dataclass(eq=False)
class AxisCalibrationData(CalibrationData):
    r"""Calibration data for an array axis.
        
        Applicable to vigra.VigraArray objects, where it provides a mechanism to 
        attach a physical dimensionality to vigra.AxisInfo objects which, in turn,
        are used to attach semantics to the axes of a vigra.VigraArray (see vigra 
        documentation for details).
        
        A vigra.VigraArray object associates one vigra.AxisInfo with each of its 
        array axes.
        
        The AxisCalibrationData can be used to attach the physical dimensionality
        to an AxisInfo in a persistent manner, by seralizing it to an XML-formatted
        string embedded in the 'description' attribute of the AxisInfo object.
        
        Conversely, the string contained in AxisInfo.description can be used to
        recreate the AxisCalibrationData object.
        
        Constructing an AxisCalibrationData object:
        ===========================================
        
        An AxisCalibrationData object can be constructed by supplying field values
        directly (see the description of fields, below), in the order of their 
        definition in the class, i.e.:

            calibration = AxisCalibrationData(index, key, type, <…, channels = … >)
        
            NOTE that the 'channels' field is always supplied as a keyword parameter,
            i.e.as 'key = value' pair. 
        
            In this form, the constructor assigns the parameters to the fields in
            the order of their definition, until all parameters are 'consumed'; 
            remanig unassigned fields will receive their default values. It 
            follows that "skipping" fields in the constructor can have unintended
            consequences.
        
        The recommended way to construct an AxisCalibrationData object is to supply
            field values as 'key=value' pairs. Fields can be supplied in ANY order, 
            and skipped fields will get their default values implicitly.
        
        An alternative way to instantiate an AxisCalibrationData is to use its
            "new" class method factory, which has an overloaded syntax:
        
        • AxisCalibrationData.new(x:dict), 
            where 'x' is a dictionary with field names as keys mapped to field value
        
        • AxisCalibrationData.new(x:str),
            where 'x' is an XML-formatted axis calibration string
            (see AxisCalibrationData.calibrationString for details)
        
        • AxisCalibrationData.new(x:vigra.AxisInfo, <index, size, units, origin, 
                                    maximum, resolution, channels>),
            where 'x' is an AxisInfo.
            This form will "parse" the AxisInfo for a calibration string and, if
            found, will use it to crate an instance of AxisCalibrationData.
        
            If a calibration string is not found in the AxisInfo, the factory
            will initiate some of the fields ('key', 'type', 'origin', 'resolution',
            'units') based on the AxisInfo data. 

            The optional parameters following 'x' can be used to override the 
            field values. If given, they must be supplied in the order described
            here, without skipping; unspecified fields will not be modified.
        
        AxisCalibrationData class has the following fields:
        
        • Universal fields — valid for all AxisType flags, 
            see vigra.AxisType for details; see also CalibrationData:
        
            ∘ Fields defined in the CalibrationData superclass:
                'name' : str — the name of the calibration object (reflective of 
                    the axis type flag)
                'relative_tolerance' : float — used for numerical comparison e.g.
                    np.isclose or math.isclose
                'absolute_tolerance' : float — used for numerical comparison e.g.
                    np.isclose or math.isclose
                'equal_nan' : bool — used in comparing two ChannelCalibrationData
                objects.
                    Python treats two NaN numbers are distinct, i.e., 
                        math.nan == math.nan
                        -> False
                
                    This results in two CalibrationData object beign "seen" as different
                    when the same numeric field has math.nan value in both of them, even
                    though the other fields are numerically identical.
                
                    Setting 'equal_nan' to True (the default) avoids this effect.
        
                'fc_template': str — format template for string represntations of
                    numeric data (sets the precision for converting to/from an 
                    AxisInfo description string)
        
            ∘ Fields defined in this class:
                'index': int — the index of the axis in the array's dimensions
        
        • Fields specific for a NonChannel axis (see vigra.AxisType for details):
            'units':    scalar pq.Quantity — the physical units associated with 
                calibrated axis. 
            'origin': float or complex — the axis minimum coordinate, in axis units
            'maximum': float or complex — the axis maximum coordinate, in axis units
            'reslution': float or complex — the sampling resolution along the 
                dimension of this axis. In other words, the physical units 
                corresponding to one element along the axis coordinates — e.g., 
                number of microns per pixel. Do not confuse with samplin "rate"
                wich is the inverse of resolution (i.e., number or axis elements
                for one physical unit).
        
            'channels' -> always an empty list for a NonChannel axis
        
        • Fields specific for a Channels axis (see vigra.AxisType for details):
            'channels' -> a list of ChannelCalibrationData objects.
                NOTE: for a 'virtual' channel axis this field will always contain a
                ChannelCalibrationData object, either using default values, or the 
                values given in the constructor parameters.
        
            The 'units', 'origin', 'maximum' and 'resolution' fields are always 
            MISSING when the AxisCalibrationData relates to a Channels axis.
        
        See also:
        ChannelCalibrationData
        
        WARNING about the 'units' field and related and scalar fields 
        'origin', 'maximum' and 'resolution':
        
        When the units associated with an AxisCalibrationData or ChannelCalibrationData
        are changed by assigning any python Quantity to this field, the scalar
        values for 'origin', 'maximum' and 'resolution' will NOT be recalculated 
        or rescaled. Therefore, 'origin', 'maximum' and 'resolution' values 
        should be recalculated as necessary and set to corerect values manually.
        
        A Quantity can also be assigned directly to the 'origin', 'maximum' or 
        'resolution' field, however:
        • Make sure you assign a Quantity scalar (i.e. magnitude * dimensionality,
          where magnitude is a scalar), not a higher dimension Quantity array 
          (unless it has just one element) and not a UnitQuantity, which by 
          definition has a magnitude of 1. See python Quantities package
          documentation for details about Quantity and UnitQuantity.
          
        • The field will only store its "magnitude" (i.e. numerical value without
          dimensionality)
        
        • If the units of the new value are different from, but convertible to,
          the units of the calibration object, the numerical value assigned to
          the field will be rescaled to the units of the calibration object. 
        
        • If the units of the new value are not convertible to the units of the 
          calibration object, an Exception will be raised.
        
        Therefore the recommended way to change a calibration is:
        
        1) If the new units are convertible to the current units, assign rescaled
            values to the fields before changing the calibration's units field.
        
            The AxisCalibrationData.rescale method does exactly this, so use it
            instead.
        
            WARNING: Rescaling may incur a loss of precision and floating point
            rounding errors.
            
        2) If the new units are completely different (say you want to change
            a channel's calibration from picoampere — pq.pA — to millivolt —
            pq.mV — because the acquisition assigned the wrong units to the channel
            calibration data; or you want to change the units of a non-channel axis 
            from micrometer — pq.um — to millisecond — pq.ms — because the acquisition
            incorectly interpreted the axis as a Space not a Time axis) then just
            assign a new Quantity (or UnitQuantity) to the calibration's 'units' 
            field. The scalar values of the fields 'origin', 'maximum' and 'resolution'
            will be left unchanged. Therefore, make sure that the scalar field 
            values make sense given the new units.
        
    """
    
    index:int = 0
    r'''index of this axis in the array dimensions: 0-based.
    Must be ≥ 0
    '''
    
    key:typing.Optional[str] = "?"
    r'''String symbol of the axis'''
    
    type:typing.Optional[typing.Union[vigra.AxisType, int]] = field(default=vigra.AxisType.UnknownAxisType)
    r'''The type of the axis — see vigra.AxisType enumeration'''
    
    size:int = 0
    r'''Size of the axis (i.e. size of the array along the dimension of this axis).
    Must be ≥ 0, although 0 is only useful for virtual axes.
    
    NOTE: For a virtual Channels axis, size is 0 but there should be at lest one 
    ChannelCalibrationData in the 'channels' attribute (see below). For a non-virtual
    channel axis the axis size wil be adjusted to match the number of channel
    calibration data objects in the 'channel' attribute.
    '''
    
    units:CalibrationUnitsDescriptor = CalibrationUnitsDescriptor(default=pq.arbitrary_unit)
    r'''The physical units
    Currently, this is set (and fixed) to MISSING for a Channels-type axis.
    
    New units can be set by assigning a Quantity, UnitQuantity, or a string symbol
    of the units (any invalid string will raise exception) e.g., "um" for micrometer
    "pA" for picoampere, etc.
    
    ''' 
    
    origin:CalibrationScalarDescriptor = CalibrationScalarDescriptor(default = 0.0)
    # _origin_:dataclasses.InitVar[numbers.Number] = 0.0
    r'''The origin of the axis coordinates.
    To what coordinate does the 0th element along the axis correspond?
    By default this is 0.0, but there can be good reasons for why axis might have
    a non-zero origin (i.e., an "offset").

    Currently, this must be set to MISSING for a Channels-type axis
    '''
    
    resolution:CalibrationScalarDescriptor = CalibrationScalarDescriptor(default=1.0)
    # _resolution_:dataclasses.InitVar[numbers.Number] = 1.0
    r'''The sampling resolution (in axis units).
    WARNING: Unlike the "resolution" field of a vigra.AxisInfo, where a value
    of 0 signals no defined resolution, here "resolution" represents the number
    of axis physical coordinates covered by one element along the axis — for
    example, micrometers corresponding to one pixel.

    When the resolution is undetermined, the value of this field should be NaN here.
    
    By default, this is set to 1.0 i.e., one axis physical units per axis element
    (e.g., one micrometer per pixel).
    
    WARNING: This is set to MISSING for a Channels-type axis, regardless of what
    is passed to the constructor.
    '''
    
    maximum:CalibrationScalarDescriptor = CalibrationScalarDescriptor(default = np.nan)
    r'''The upper limit of the axis coordinates.
    To what coordinate does the last element along the axis correspond?
    Currently, this must be set to MISSING for a Channels-type axis.
    '''
    
    _:dataclasses.KW_ONLY
    
    channels:CalibrationChannelsDescriptor = dataclasses.field(default_factory=list)
    r'''Sequence of ChannelCalibrationData, one per channel
    Currently, this will be set to MISSING for a NonChannel-type axis.
    For a Channels axis, setting this attribute MAY result in a change of the 
    AxisCalibrationData size attribute (see above).
    '''

    def __post_init__(self):
        r"""Further curates the fields after construction:
    
        • for all axis types, tries to make the 'key' parameter as consistent as
            possible given the axis type flag and its index
            WARNING: This requires the 'type' and 'index' fields to be properly
            set.
    
        • for a Channels axis, ensures that:
            ∘ 'units', 'origin', 'maximum' and 'resolution' are set to MISSING
                (they do not make sense here; instead, they need to be present in
                the ChannelCalibrationData)
    
            ∘ if no channels are specified, a ChannelCalibrationData object is
                constructed with default values 
    
            ∘ assigns this object as the parent for all ChannelCalibrationData
                (this is something that the CalibrationChannelsDescriptor also 
                does in its __set__ method; this means that a ChannelCalibrationData
                object always get the owner object as its 'parent')
    
        • for a NonChannel axis, ensures that:
            ∘ the 'channels' field is always an empty list, whic makes sense for
                this type of axis.
    
            ∘ if the 'units' field is NOT a pq.Quantity, it will be set to the 
                default units inferred from the axis type flag — for details,
                see imaging.axisutils.axisTypeUnits() function.
    
        NOTE: To create an AxisCalibrationData object from a vigra.AxisInfo object,
        a dict, or a calibration string (xml-formatted) please use the "new" 
        factory class methods.
        """
        typeFlagKey = axisTypeSymbol(self.type)
        # print(f"{self.__class__.__name__}.__post_init__: typeFlagKey = {typeFlagKey}")
        if not isinstance(self.key, str) or len(self.key.strip()) == 0:
            self.key = typeFlagKey
            
        elif self.key == "?":
            if self.isChannels:
                self.key = "c"
            else:
                space_keys = ["x", "y", "z"]
                if "s" in typeFlagKey:
                    if self.index in range(3):
                        typeFlagKey.replace("s", space_keys[self.index])
                        
                self.key = typeFlagKey
            
        # print(f"{self.__class__.__name__}.__post_init__: is Channels =  {self.isChannels}")
        if self.isChannels:
            # bounce these to ChannelCalibrationData if needed , and set them to 
            # MISSING at the top level
            u = self.units if isinstance(self.units, pq.Quantity) else pq.arbitrary_unit
            o = self.origin if isinstance(self.origin, numbers.Number) else 0.0
            
            # NOTE: 2025-04-16 17:37:15
            # the line below adapts to ChannelCalibrationData using NaN unless a
            # scalar value is given
            m = self.maximum if isinstance(self.maximum, numbers.Number) else math.nan 
            
            if len(self.channels) == 0:
                self.channels = [ChannelCalibrationData(name="channel_0", units = u, 
                                                        origin = 0, maximum = m,
                                                        index=0, parent=self)]
                
            else:
                for channel in self.channels:
                    channel.parent = self
                
            self.units = dataclasses.MISSING
            self.origin = dataclasses.MISSING
            self.maximum = dataclasses.MISSING
            self.resolution = dataclasses.MISSING
            
        else:
            # NOTE: 2025-04-16 22:41:29
            # To avoid messing up the scalar fields throught rescaling (see
            # CalibrationScalarDescriptor), I avoid setting up the units here
            # in accordance to the typeFlag self.type. This is best left to 
            # setting the units at construction time (in the __init_ generated by
            # 'dataclass' decorator).
            #
            # NOTE: 2025-04-16 22:43:43
            # enforce empty channels list for a NonChannel axis
            if isinstance(self.channels, typing.Sequence) and len(self.channels):
                self.channels.clear()
            else:
                self.channels = list()
                
            if not isinstance(self.units, pq.Quantity) or self.units == pq.arbitrary_unit:
                self.units = axisTypeUnits(self.type)
                
    @singledispatchmethod
    @classmethod
    def new(cls, o:object):
        r"""Factory for AxisCalibrationData objects"""
        raise NotImplementedError(f"Not implemented for objects of type {type(o).__name__}")
    
    @new.register(vigra.AxisInfo)
    @classmethod
    def _(cls, arg:vigra.AxisInfo, index:typing.Optional[int] = None, 
          name: typing.Optional[str] = None, 
          size: typing.Optional[int] = None,
          units: typing.Optional[typing.Union[pq.Quantity, str, MissingType]] = None,
          origin: typing.Optional[typing.Union[numbers.Number, pq.Quantity, CalSpec]] = None,
          maximum: typing.Optional[typing.Union[numbers.Number, pq.Quantity]] = None,
          resolution: typing.Optional[typing.Union[numbers.Number, pq.Quantity]] = None,
          channels: typing.Optional[typing.Union[CalSpec, ChannelCalibrationData, typing.Sequence[CalSpec | ChannelCalibrationData]]] = None):
        r"""Factory for constructing an AxisCalibrationData using vigra.AxisInfo"""
        # NOTE: 2025-04-13 13:42:52
        # in vigra.AxisInfo, a 'resolution' field 0.0 means axis resolution, in
        # the sense of sampling resolution, which should be in axis units, is not
        # defined
        axtype = arg.typeFlags
        axkey = arg.key
        axres = 1. if arg.resolution == 0 else arg.resolution
        
        # print(f"{cls.__name__}.new: axkey = {axkey}")
        
        ischannels = axtype & vigra.AxisType.Channels
        
        cal_str_start_stop = cls.findCalibrationString(arg.description)
        
        if cal_str_start_stop is None:
            if ischannels:
                ret = cls(type = axtype, key = axkey, name = axisTypeName(axtype), 
                        units = dataclasses.MISSING, origin = dataclasses.MISSING,
                        maximum = dataclasses.MISSING, resolution = dataclasses.MISSING,
                        channels = list())
            else:
                ret = cls(type = axtype, key = axkey, name = axisTypeName(axtype), 
                        resolution = axres, channels=list())
                
            
            # overwrite the defaults if needed, using the descriptor classes for
            # units, origin, maximum, resolution, and channels
            if isinstance(index, int):
                if index >= 0 :
                    ret.index = index
                else:
                    raise ValueError(f"Invalid axis index: {index}")
                
            if isinstance(name, str):
                ret.name = name
                
            if isinstance(size, int):
                if size >= 0:
                    ret.size = size
                else:
                    raise ValueError(f"Invalid axis size: {size}")
                
            if ischannels:
                if isinstance(channels, typing.Sequence):
                    if all(isinstance(c, (CalSpec, ChannelCalibrationData)) for c in channels):
                        ret.channels = channels # use the CalibrationChannelsDescriptor
                    else:
                        raise TypeError("Incompatible types in channels specification")
                elif isinstance(channels (CalSpec, ChannelCalibrationData)):
                    ret.channel = [channels]
                    
                elif channels is not None:
                    raise TypeError(f"Wrong 'channels' specification. expecting a CalSpec, ChannelCalibrationData, or a sequence of these; instead, got {type(channels).__name__}")
                    
                else:
                    if len(ret.channels) == 0:
                        ret.channels.append(ChannelCalibrationData(name = "channel_0", index=0)) # a default, for one channel!
            else:
                if isinstance(origin, CalSpec):
                    origin, maximum, units = origin
                    
                if isinstance(units, (pq.Quantity, str)):
                    if isinstance(units, str):
                        units = scq.str2quantity(units)
                    ret.units = units
                        
                if isinstance(origin, (numbers.Number, pq.Quantity)):
                    ret.origin = origin
                    
                if isinstance(maximum, (numbers.Number, pq.Quantity)):
                    ret.maximum = maximum
                        
            return ret
            
        else:
            calStr = arg.description[cal_str_start_stop[0]:cal_str_start_stop[1]]
            return cls.new(calStr)
            
        
    @new.register(dict)
    @classmethod
    def _(cls, d:dict):
        if cls.isCalibration(d):
            return cls(**d) # channels parents will be set in __post_init__
        
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
        # import xml.etree.ElementTree as ET
        
        if not isinstance(s,str) or len(s.strip()) == 0 or not s.startswith("<axis_calibration>") or not s.endswith("</axis_calibration>"):
            raise ValueError("This is not an axis calibration string")
            
        cal = dict()
        # these will be treated differently according to the axis type flags
        cal["units"] = dataclasses.MISSING
        cal["origin"] = dataclasses.MISSING
        cal["maximum"] = dataclasses.MISSING
        cal["resolution"] = dataclasses.MISSING
        # cal["channels"] = dataclasses.MISSING
        cal["channels"] = list()
        
        # OK, now extract the relevant xml string
        try:
            cal_xml_element = ET.fromstring(s)
            
            # make sure we're OK
            if cal_xml_element.tag != "axis_calibration":
                raise ValueError("Wrong element tag; was expecting 'axis_calibration', instead got %s" % element.tag)
            
            # first, get the type of the axis:
            type_nodes = tuple(getXMLChildren(cal_xml_element, tagName = "type"))
            if len(type_nodes) == 0:
                raise ValueError(f"Missing 'type' child element")
            
            cal["type"] = cls._from_xml_text_("type", type_nodes[0].text)
            
            ischannels = cal["type"] & vigra.AxisType.Channels
            
            # custonmize creation based on axis typeflag
            # these below are SKIPPED from being translated to the calibration string
            # so without that there is the risk of them being assigned default values elsewhere.
            #
            # in addition, "channels" field is always treated specially accordin to
            # the axis type flags
            #
            if ischannels:
                # cal["units"] = dataclasses.MISSING
                # cal["origin"] = dataclasses.MISSING
                # cal["maximum"] = dataclasses.MISSING
                # cal["resolution"] = dataclasses.MISSING
                skipfields = ("units", "origin", "maximum", "resolution", "channels", "type")
            else:
                # cal["channels"] = dataclasses.MISSING
                skipfields = ("channels", "type")
                
            for param in filter(lambda x: x not in skipfields, map(lambda f: f.name, dataclasses.fields(cls))):
                child_nodes = tuple(getXMLChildren(cal_xml_element, tagName=param))
                if len(child_nodes):
                    child_node = child_nodes[0]
                    txt = child_node.text
                    cal[param] = cls._from_xml_text_(param, txt)
                    
                # print(f"{cls.__name__}.new({type(s).__name__}): cal[{param}] = {cal[param]}")
                        
            # NOTE: 2025-07-06 22:30:44 Now, populate channel calibration data
            if ischannels:
                child_nodes = tuple(getXMLChildren(cal_xml_element, tagName="channels"))
                if len(child_nodes):
                    child_node = child_nodes[0]
                    channel_elems = tuple(e for e in child_node)
                    if len(channel_elems):
                        cal["channels"] = list(map(lambda e: ChannelCalibrationData.new(e), channel_elems)) 
                    else:
                        cal["channels"] = [ChannelCalibrationData(name="channel_0", index=0)]
                else:
                    # enforce the calibration of a virtual channel.
                    # technically, this case should never occur
                    cal["channels"] = [ChannelCalibrationData(name="channel_0", index=0)]
        

        except Exception as e:
            traceback.print_exc()
            print(f"Invalid calibration string {s}")
            raise e
            
        if cls.isCalibration(cal):
            return cls(**cal)
        
    @property
    def isChannels(self):
        r"""True if the AxisCalibrationData object relates to a Channels axis"""
        return self.type & vigra.AxisType.Channels > 0
    
    @property
    def nChannels(self):
        if self.isChannels:
            return len(self.channels)
        
        return 0
    
    @property
    def channelCalibrations(self) -> list:
        r"""Alias to self.channels.
        for backward compatibility
        This is empty in an AxisCalibrationData for a NonChannel axis.
        """
        return self.channels
    
    @property
    def channelIndices(self) -> tuple:
        r"""A tuple of channel indices, from their calibration data.
        These include the virtual channel (if it exists).
        
        This tuple is empty if the AxisCalibrationData corresponds to a 
        non-Channels axis.
        """
        return tuple(map(lambda c: c.index, self.channels))
    
    @property
    def channelAqcuisitionIndices(self) -> tuple:
        r"""A tuple of channel indices, from their calibration data.
        These include the virtual channel (if it exists).
        
        This tuple is empty if the AxisCalibrationData corresponds to a 
        non-Channels axis.
        """
        return tuple(map(lambda c: c.acquisition_index, self.channels))

    @property
    def channelNames(self) -> tuple[str] | None:
        r"""A tuple of channel names, from their calibration data.
        These include the virtual channel (if it exists).
        
        This list is empty if the AxisCalibrationData corresponds to a 
        non-Channels axis.
        """
        if self.isChannels:
            return tuple(map(lambda c: c.name, self.channels))
    
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
        
        NOTE: For a virtual Channels axis, there will always be one ChannelCalibrationData
        with either default values, or values given at the constructor
        
        """
        ischannels = self.type & vigra.AxisType.Channels

        skipfields = ("channels", ) # always treat channels field specially
        
        if ischannels:
            skipfields += ("units", "origin", "maximum", "resolution")
        
        strlist = ["<axis_calibration>"]
        
        for param in sorted(filter(lambda x: x not in skipfields, map(lambda x: x.name, dataclasses.fields(self)))):
            # print(f"{self.__class__.__name__}.calibrationString: ischannels: {ischannels} -> param = {param}")
            s = self._to_xml_(param)
            if isinstance(s, str):
                strlist.append(self._to_xml_(param))
            
        if ischannels and isinstance(self.channels, typing.Sequence):
            strlist.append("<channels>")
            for ch in self.channels:
                if isinstance(ch, ChannelCalibrationData):
                    strlist.append(ch.calibrationString)
            strlist.append("</channels>")
                
        strlist.append("</axis_calibration>")
        
        return "".join(strlist)
    
    @property
    def calibratedOrigin(self) -> pq.Quantity | None:
        r"""Axis origin, in physical units, for a NonChannel axis.
            This property is None for a Channels axis.
        """
        if not self.isChannels:
            return self.origin * self.units
    
    @property
    def calibratedResolution(self) -> pq.Quantity | None:
        r"""Axis resolution, in physical units, for a NonChannel axis.
            This property is None for a Channels axis.
        """
        if not self.isChannels:
            return self.resolution * self.units
        
    @property
    def calibratedMaximum(self) -> pq.Quantity:
        r"""Axis maximum, in physical units, for a NonChannel axis.
            For a Channels axis this is None.
        """
        if not self.isChannels:
            return self.maximum * self.units
    
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
        
    @staticmethod
    def isCalibrated(o:vigra.AxisInfo) -> bool:
        start_stop = AxisCalibrationData.findCalibrationString(o.description)
        return start_stop is not None
    

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text(f"{self.__class__.__name__}")
        else:
            g = p.indentation+2
            with p.group(g, f"{self.__class__.__name__}:\n"):
                for k, f in enumerate(dataclasses.fields(self)):
                    if f.name == "channels" and len(getattr(self, f.name, list())):
                        with p.group(g, f"{f.name}:\n", ""):
                            for kc, c in enumerate(getattr(self, f.name, list())):
                                if kc == 0:
                                    p.text(f"{' '*(g+2)}{kc}: ")
                                else:
                                    p.text(f"{kc}: ")
                                p.pretty(c)
                                p.break_()
                    else:
                        # print(f"p.indentation = {p.indentation}")
                        # p.text(f"{f.name}: ")
                        if k == 0:
                            p.text(f"{' '*(g+2)}{f.name}: ")
                        else:
                            p.text(f"{f.name}: ")
                            
                        p.pretty(getattr(self, f.name, None))
                    p.break_()
        
    def rescale(self, u:typing.Union[pq.Quantity, pq.dimensionality.Dimensionality, str]) -> None:
        r"""Rescales the units and the scalar fields to new units.
        The new units must be convertible to the current ones. 
        For the general case of re-assigning completely different units, 
        the fields must be recalculated manually after the units field is re-asigned.
        
        """
        if isinstance(u, str):
            u = scq.str2quantity(u)
        if not scq.unitsConvertible(u, self.units):
            raise ValueError(f"New units ({u}) are incompatible with current units ({self.units}) and therefore, the calibration cannot be rescaled.")
            
        # NOTE: 2025-04-17 10:44:36
        # the next two calls will throw exceptions if self.units are not convertible
        # to the new units
        new_o = self.calibratedOrigin.rescale(u)
        new_m = self.calibratedMaximum.rescale(u)
        self.origin = scq.quantity2scalar(new_o)
        self.maximum = scq.quantity2scalar(new_m)
        if not self.isChannels:
            new_r = self.calibratedResolution.rescale(u)
            self.resolution = scq.quantity2scalar(new_r)
            
        self.units = u
        
    def addChannelCalibration(self, val:ChannelCalibrationData):
        if not self.type & vigra.AxisType.Channels:
            return
        
        self.channels.append(val)
        
        
    def calibrateAxis(self, axinfo:vigra.AxisInfo) -> vigra.AxisInfo:
        assert self.type == axinfo.typeFlags, f"Cannot apply a {self.type} axis calibration to a {axinfo.typeFlags} axis"
        
        description = axinfo.description.strip()
        calStr = self.calibrationString
        start_stop = self.findCalibrationString(description)
        if start_stop is not None:
            newDescr = " ".join([description[:start_stop[0]],
                        calStr,
                        description[start_stop[1]:]])
        else:
            newDescr = " ".join([description, calStr])
            
        axinfo.description = newDescr
        return axinfo
    
    @staticmethod
    def getOriginalDescription(axinfo:vigra.AxisInfo) -> str:
        return AxisCalibrationData.clearCalibrationFromString(axinfo.description.strip())
        
    @staticmethod
    def clearCalibrationFromString(s:str) -> str:
        start_stop = AxisCalibrationData.findCalibrationString(s)
        if start_stop is not None:
            return " ".join([s[:start_stop[0]],
                        s[start_stop[1]:]])
        
        return s
        
    @staticmethod
    def removeAxisCalibration(axinfo:vigra.AxisInfo) -> vigra.AxisInfo:
        d = AxisCalibrationData.getOriginalDescription(axinfo)
        axinfo.description = d
        # description = axinfo.description.strip()
        # start_stop = AxisCalibrationData.findCalibrationString(description)
        # if start_stop is not None:
        #     newDescr = " ".join([description[:start_stop[0]],
        #                 description[start_stop[1]:]])
        #     axinfo.description = newDescr
            
        return axinfo
    
    def calibratedCoordinate(self, value) -> pq.Quantity | None:
        r"""Converts a axis coordinate to its value in physical units.
            This is equvalent to the calibrated distance from the axis origin, 
            along the axis dimension, for a NonChannels axis.
            For Channels axis returns None
        """
        if self.isChannels:
            return
        if not isinstance(value, numbers.Number):
            raise TypeError("expecting a scalar; got %s instead" % type(value).__name__)
        return (value * self.resolution + self.origin) * self.units
        
    def calibratedMeasure(self, value:numbers.Number) -> pq.Quantity | None:
        r"""Converts a value in number of samples along the axis, physical units.
            Applies to a NonChannels axis. 
            For Channels axis returns None
        """
        if self.isChannels:
            return
        if not isinstance(value, numbers.Number):
            raise TypeError(f"Expecting a numbers.Number; got {type(value).__name__} instead")
        return value * self.resolution * self.units
    
    def calibratedDistance(self, value) -> pq.Quantity | None:
        r"""Calls calibratedMeasure(value).
        For backward compatibility.
        """
        return self.calibratedMeasure(value)
        
    def coordinateInSamples(self, value:pq.Quantity) -> int | None:
        r"""Converts a calibrated distance from axis origin to number of samples.
            This performs the inverse of self.calibratedCoordinate.
            Returns an int with rounding up (math.ceil function).
            Applies to a NonChannels axis. 
            For Channels axis returns None
        """
        if self.isChannels:
            return
        if not isinstance(value, pq.Quantity):
            raise TypeError(f"Expecting a Quantity; got {type(value).__name__} instead")
        
        if scq.isScalar(value):
            value = scq.ensureScalar(value)
        else:
            raise TypeError(f"Expecting a scalar Quantity; instead, got a {value.size}-sized Quantity")
        
        if value.units != self.units:
            if not scq.unitsConvertible(value.units, self.units):
                raise TypeError(f"Cannot convert between {value.units} and {self.units}")
            value = value.rescale(self.units)
        
        return math.ceil((value - self.calibratedOrigin) / self.resolution)
    
    def measureInSamples(self, value: pq.Quantity) -> int | None:
        r"""Converts a distance along the axis (in physical units) to samples.
            Performs the inverse of calibratedMeasure.
            Applies to a NonChannels axis. 
            For Channels axis returns None
        """
        if self.isChannels:
            return
        return math.ceil(value/ self.resolution)

    @singledispatchmethod
    def channelCalibration(self, o):
        r"""Returns the ChannelCalibrationData for a specific channel.
        
        Returns None if the AxisCalibrationData object does NOT relate to a 
        Channels axis, or the specified channel does not exist in the AxisCalibrationData
        object.
        
        The channel can be specified by the value of the 'index' (int) or 'name'
        (str) attribute of the ChannelCalibrationData objects in self.channels.
        
        If self.channels is not a sequence of ChannelCalibrationData objects, or
        does not contain a ChannelCalibrationData object with the specified 'index'
        or 'name', returns None.
        
        NOTE: To retrieve a ChannelCalibrationData object by its index in the 
        self.channels sequence just use the usual sequence indexing method, e.g.:
        
                self.channels[𝑘]
        
        to access the 𝑘ᵗʰ ChannelCalibrationData. 
    
        This assumes that this instance of AxisCalibrationData relates to a 
        Channels axis, and:
        
            -len(self.channels) ≤ 𝑘 < len(self.channels)
        
        The 'channels' attribute of an AxisCalibrationData object for a NonChannel 
        axis is MISSING.
        
        """
        raise NotImplementedError(f"Not implemented for {type(o).__name__} objects")
    
    @channelCalibration.register(int)
    def _(self, channel:int):
        if self.isChannels:
            chCal = list(filter(lambda c: getattr(c, "index", None) == channel, self.channels))
            if len(chCal):
                return chCal[0]
        else:
            scipywarn("Not a Channels axis")
            
    @channelCalibration.register(str)
    def _(self, channel:str):
        if self.isChannels:
            chCal = list(filter(lambda c: getattr(c, "name", None) == channel, self.channels))
            if len(chCal):
                return chCal[0]
        else:
            scipywarn("Not a Channels axis")
            
    def getChannelCalibration(self, o:int | str = 0) -> ChannelCalibrationData | None:
        return self.channelCalibration(o) # alias for backward compatibility
    
    def getChannelUnits(self, o:int|str = 0) -> pq.Quantity | None:
        if self.isChannels:
            chCal = self.getChannelCalibration(o)
            return chCal.units
            
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
    
        Side effects:
        =============
        For a VigraArray WITHOUT a real channels axis, the AxesCalibration
        object will append a singleton channels axis to the array.
                
        NOTE 1: 
        The AxisInfo objects used in the AxesCalibration's initialization WILL
        NOT gain a calibration string in their `description` attribute (i.e., 
        the AxisInfo will not be automatically 'calibrated').
            
        The user of the AxesCalibration object must call its 'calibrateAxes()'
        method in order to embed an XML-formatted calibration string into
        the AxisInfo `description` attribute.
        
        NOTE 2:
        The form where a VigraArray is the first (and only) parameter also 
        generates an AxisCalibrationData object for a "virtual" channels axis,
        when the array does not contain such axis, i.e., when
    
            array.channelIndex == array.ndim
    
        """
        
        self.relative_tolerance = RELATIVE_TOLERANCE
        self.absolute_tolerance = ABSOLUTE_TOLERANCE
        self.equal_nan = EQUAL_NAN
        
        # NOTE 2021-10-25 10:27:54
        # keep this as a LIST - this to allow several axes with the same 
        # typeFlags (and key).
        self._axescalibrations_ = list()
        self._axistags_ = None
        
        if len(args) == 1 and isinstance(args[0], (tuple, list , deque)):
            # unpack args[0] when it is a single sequence
            args = args[0]
        
        if len(args):
            if isinstance(args[0], vigra.VigraArray):
                # img = args[0]
                # NOTE: 2025-04-20 21:58:11
                # work on a copy of the array; do NOT modify the original
                img = args[0].copy()
                if img.channelIndex == img.ndim: # a real channel axis does NOT exist
                    # will set up a channels axis calibrations with default values, further below
                    img = img.insertChannelAxis()
                    # NOTE: 2025-04-19 00:00:43
                    # AVOID this as it will mess up the array!
                    # if self._axistags_.channelIndex == len(self._axistags_):
                    #     self._axistags_.insertChannelAxis() # this places the singleton Channels axis at the end of axistags
                    
                # create a copy of the image's axistags
                self._axistags_ = vigra.AxisTags(list(map(lambda x: vigra.AxisInfo(key=x.key, 
                                                                                   typeFlags=x.typeFlags, 
                                                                                   resolution=x.resolution, 
                                                                                   description=x.description), 
                                                          img.axistags)))
                
                
                self._axescalibrations_ = list(map(lambda x: AxisCalibrationData.new(x), self._axistags_))
                
                for k, axInfo in enumerate(self._axistags_):
                    if axInfo.typeFlags & vigra.AxisType.Channels:
                        channel_axis_index = self._axistags_.index("c")
                        if args[0].channelIndex == args[0].ndim:
                            self._axescalibrations_[channel_axis_index].size = 0
                        else:
                            self._axescalibrations_[channel_axis_index].size = args[0].shape[channel_axis_index]
                            
                        # change ownership for the ChannelCalibrationData objects
                        for ch in self._axescalibrations_[channel_axis_index].channels:
                            ch.parent = self._axescalibrations_[channel_axis_index]
                            
                        # Make sure we don't overwrite existing channel calibrations
                        if len(self._axescalibrations_[channel_axis_index].channels) < img.channels:
                            for k in range(len(self._axescalibrations_[channel_axis_index].channels), img.channels):
                                self._axescalibrations_[channel_axis_index].channels.append(ChannelCalibrationData(index=k, parent=self._axescalibrations_[channel_axis_index]))
                                
                        elif len(self._axescalibrations_[channel_axis_index].channels) > img.channels:
                            self._axescalibrations_[channel_axis_index].channels = self._axescalibrations_[channel_axis_index].channels[:img.channels]
                            
                    else:
                        self._axescalibrations_[k].size = img.shape[k]
                return

            elif isinstance(args[0], vigra.AxisTags):
                # NOTE: 2025-04-18 13:38:42
                # here I cannot check if the Channels axis is real or virtual
                # because there no array data is supplied.
                # create a copy of the axistags
                self._axistags_ = vigra.AxisTags(list(map(lambda x: vigra.AxisInfo(key=x.key, 
                                                                                   typeFlags=x.typeFlags, 
                                                                                   resolution=x.resolution, 
                                                                                   description=x.description), 
                                                          args[0])))
                self._axescalibrations_ = list(map(lambda x: AxisCalibrationData.new(x), self._axistags_))
                
                for axCal in self._axescalibrations_:
                    if axCal.type & vigra.AxisType.Channels:
                        for ch in axCal.channels:
                            ch.parent = axCal
                return
            
            elif isinstance(args[0], int):
                # NOTE: 2021-10-25 10:25:39
                # here we use the strategy in vigra.AxisTags constructor: an int
                # indicates HOW MANY axes are there, and therefore NOT an axis 
                # type flag
                if args[0] <= 0:
                    raise ValueError(f"Cannot create an AxesCalibration object for {args[0]} axes")
                
                # create AxisTags
                self._axistags_ = vigra.AxisTags(args[0])
                self._axescalibrations_ = list(map(lambda x: AxisCalibrationData.new(x), self._axistags_))
                for axCal in self._axescalibrations_:
                    if axCal.type & vigra.AxisType.Channels:
                        for ch in axCal.channels:
                            ch.parent = axCal
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
                        cal = AxisCalibrationData.new(arg)
                        self._axistags_.append(arg)
                        self._axescalibrations_.append(cal)
                                        
                    elif isinstance(arg, str):
                        try:
                            cal = AxisCalibrationData.new(arg)
                        except:
                            cal = AxisCalibrationData() #  create default UnknownAxisType
                            
                        self._axescalibrations_.append(cal)
                        
                    elif isinstance(arg, AxisCalibrationData):
                        self._axescalibrations_.append(arg)
                        self._axistags_.append(vigra.AxisInfo(key = arg.key, typeFlags=arg.type, 
                                                              resolution = arg.resolution if not arg.isChannels else 0.0,
                                                              description=arg.name))
                        
                    else:
                        if k == 0:
                            raise TypeError(f"Expecting a vigra.VigraArray, vigra.AxisTags, vigra.AxisInfo, str, int, AxisCalibrationData or a sequence of these; got {type(arg).__name} instead")
                        else:
                            raise TypeError(f"{k}th argument is not a vigra.AxisInfo, str or AxisCalibrationData")
                        
                for axCal in self._axescalibrations_:
                    if axCal.type & vigra.AxisType.Channels:
                        for ch in axCal.channels:
                            ch.parent = axCal
                            
        if not self.__check_cal_axinfo__():
            raise RuntimeError("Axis calibration data is inconsistent with axis info objects")
        
    @property
    def isValid(self):
        r"""Checks validity of this AxesCalibration object.
        The object is valid when all the conditions below are satisfied:
        • 'axistags' property if a vigra.AxisTags object
        • 'calibrations' property is a sequence of AxisCalibrationData objects
        • 'axistags' and 'calibrations' have the same, non-zero, length
        • all axis keys in the 'calibrations' sequence are present in the same 
            order in the 'axistags' and vice-versa.
        """
        ret = isinstance(self._axistags_, vigra.AxisTags)
        
        if ret:
            ret &= all(isinstance(v, AxisCalibrationData) for v in self._axescalibrations_)
            
        if ret:
            ret &= len(self._axistags_) > 0 and len(self._axistags_) == len(self._axescalibrations_)
            
        if ret:
            ret &= list(map(lambda x: x.key, self._axistags_)) == list(map(lambda x:x.key, self._axescalibrations_ ))
        
        return ret 
        
    def __check_cal_axinfo__(self):
        if (self._axistags_ is None or len(self._axistags_) == 0) and len(self._axescalibrations_) == 0:
            return True
        
        ret = len(self._axistags_) == len(self._axescalibrations_)
        
        if ret:
            ret &= all(cal.key in self._axistags_ for cal in self._axescalibrations_)
            
        if ret:
            calkeys = (cal.key for cal in self._axescalibrations_)
            ret &= all(axinfo.key in calkeys for axinfo in self._axistags_)
            
        return ret
        
    def __iter__(self):
        r"""Iterates through the AxisCalibrationData objects contained within self
        """
        yield from (cal for cal in self._axescalibrations_ if cal.key in self._axistags_)
        #yield from (cal.key for cal in self._axescalibrations_ if cal.key in self._axistags_)
        
    def __contains__(self, item):
        r"""Membership test.
        item: AxisCalibrationData, str (calibration key or name), or type flag 
            (int or vigra.AxisType)
        """
        if isinstance(item, str):
            return any(item in (getattr(cal, "key", None), getattr(cal, "name", None)) for cal in self._axescalibrations_)
        
        elif isinstance(item, (int, vigra.AxisType)):
            return item in (getattr(cal, "type", None) for cal in self._axescalibrations_)
        
        elif isinstance(item, CalibrationData):
            return item in self._axescalibrations_
        
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
            return self._axescalibrations_[index] # raises IndexError if inappropriate
        
        elif isinstance(index, str):
            if index in self:
                ret = [cal for cal in self._axescalibrations_ if index in (cal.name, cal.key)]
                if len(ret):
                    return ret[0]
                ndx = f"'{index}" if isinstance(index, str) else f"{index}"
                raise IndexError(f"Calibration for axis {ndx} not found")
                    
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

            self._axescalibrations_[item] = obj # raises corresponding exception for list API
            self._axistags_[item] = obj.axisInfo
            
        else:
            raise TypeError(f"Index must eb an int; got {type(index).__name} instead")
        
    def __len__(self):
        return len(self._axescalibrations_)
    
    def index(self, item:typing.Union[int, str]):
        r"""
        item: AxisCalibrationData, or str (key or name)
            When a str, returns the first AxisCalibrationData with key == index
            
            When item is 'c' returns the number of axes when no Channels axis exists
        """
        if isinstance(item, AxisCalibrationData):
            return self._axescalibrations_.index(item) # raises appropriate exception for list API
        
        elif isinstance(item, str):
            ret = [k for k, c in enumerate(self._axescalibrations_) if c.key == item ]
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
        return "\n".join([f"{self.__repr__()} with {len(self._axescalibrations_)} axes:"] + [f"{k}.\t" + cal.__str__()+"\n" for k, cal in enumerate(self._axescalibrations_)])
    
    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text(f"{self.__class__.__name__} with {len(self._axescalibrations_)} axes")
        else:
            g = 2
            with p.group(g, f"{self.__class__.__name__} with {len(self._axescalibrations_)} axes:\n"):
                for k, cal in enumerate(self._axescalibrations_):
                    if k == 0:
                        p.text(f"{' '*2}{k}: ")
                    else:
                        p.text(f"{k}: ")
                    p.pretty(cal)
                    p.break_()
    
    def hasAxis(self, key):
        r"""Queries if the axis key is contained in the 'axistags' attribute.
        WARNING: This does not guarantee that the axis is also calibrated.
        To check if an axis with this key is also calibrated, call
        'key in self'
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        return key in self.axiskeys and key in self._axistags_
    
    def axiskeys(self):
        r"""A generator of axiskeys
        """
        yield from (cal.key for cal in self._axescalibrations_)
    
    # @property
    def keys(self):
        r"""Alias to self.axiskeys
        """
        yield from self.axiskeys()
    
    @property
    def axistags(self) -> vigra.AxisTags:
        r"""Read-only
        """
        return self._axistags_
    
    @property
    def channels(self) -> list:
        r"""List of image channel calibration data; possibly empty.
        When there exists a non-virtual channel axis, this property is the list
        of channel calibration data for that axis
    """
        if "c" in self:
            return len(self["c"].channels)
        else:
            return list()
    
    @property
    def calibrations(self) -> list:
        return self._axescalibrations_
    
    #@property
    def values(self):
        yield from (cal for cal in self)
        
    def items(self):
        yield from ((cal.key, cal) for cal in self)
    
    def typeFlags(self, key):
        r"""Read-only
        """
        if isinstance(key, vigra.AxisInfo):
            key = key.key
        
        if key not in self.keys() or key not in self._axistags_:
            raise KeyError("Axis with key %s is not calibrated by this object" % key)
        
        # return self[key]["type"]
        return self[key].type
    
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
            self._axescalibrations_.append(cal)
            
        elif isinstance(index, int):
            if index < 0:
                raise ValueError("index must be between 0 and %d, inclusive" % len(self.axistags))
            
            if index == len(self.axistags):
                self._axistags_.append(axInfo)
                self._axescalibrations_.append(cal)
                
            elif index < len(self.axistags):
                self._axistags_.insert(index, axInfo)
                self._axescalibrations_.insert(index, cal)
                
                
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
            
        if key not in self._axescalibrations_.keys():
            raise KeyError("Axis %s has no calibration data" % key)
                
                
        self._axescalibrations_.pop(key, None)
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
        new_axes = [axInfo for axInfo in self._axistags_ if axInfo.key not in self._axescalibrations_.keys()]
        obsolete_keys = [key for key in self._axescalibrations_.keys() if key not in self._axistags_.keys()]

        for axInfo in new_axes:
            #self._initialize_calibration_with_axis_(axInfo)
            self.calibrateAxis(axInfo)
        
        for key in obsolete_keys:
            self._axescalibrations_.pop(key, None)
                
        
    def calibrateAxes(self):
        r"""Attaches a calibration string to all AxisInfo objects in self.axistags.
        """
        for k, ax in enumerate(self._axistags_):
            # in case a virtual channels axis was detected, this was added to the
            # axistags in __init__
            self._axescalibrations_[k].calibrateAxis(ax)
            
    def calibrateImage(self, img:vigra.VigraArray) -> vigra.VigraArray:
        r"""Applies the axis calibrations to the given vigra array 'img'.
        Returns a copy of 'img' with axistags containing calibration strings in their
        description attributes.
        
        If 'img' does not contain a channels axis (i.e. channelIndex == array.ndims)
        then the returned copy will receive a singleton channel axis.
    
    """
        if img.channelIndex == img.ndim: # no real channels axis in img
            img = img.insertChannelAxis()
        else:
            img = img.copy()
            
        for axtag in self.axistags:
            if axtag.key in img.axistags:
                imgAxTag = img.axistags[axtag.key]
                self[axtag.key].calibrateAxis(imgAxTag)

        return img
                
            
def hasNameString(s):
    return AxesCalibration.hasNameString(s)
    
def axisChannelName(axisinfo:vigra.AxisInfo, channel:int) -> str | None:
    r"""
    Parameters:
    ===========
    axisinfo: vigra.AxisInfo object
    
    channel: int >=0 (0-based index of the channel)
    
    Returns
    =======
    Channel name, or None for NonChannel axis
    """
    # return AxisCalibrationData(axisinfo).getChannelName(channel)
    if axisinfo.isChannel:
        return AxisCalibrationData.new(axisinfo).channelNames[channel]

def axisName(axisinfo:vigra.AxisInfo) -> str | None:
    r"""Returns the axis name stored in the axis description.
    
    To get the name of a channel (valid only for Channel axis) use axisChannelName
    
    Parameters:
    ===========
    axisinfo: vigra.AxisInfo
    
    
    """
    return AxisCalibrationData(axisinfo).axisName
    # return AxesCalibration(axisinfo).axisName
    
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
                 channel:typing.Optional[typing.Union[int,str]] = None) -> pq.Quantity | None:
    r"""For a channels axis, return the units of the specified channel or channel 0.
For a Nonchannel axis returns the axis units"""
    if not isinstance(axisinfo, vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    axcal = AxisCalibrationData.new(axisinfo)
    
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
