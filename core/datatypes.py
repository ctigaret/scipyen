# -*- coding: utf-8 -*-
''' Utilities for generic and numpy array-based data types such as quantities


'''

from __future__ import print_function

#### BEGIN core python modules
import collections 
import datetime
from enum import Enum, IntEnum
import inspect
import numbers
import sys
import time
import traceback
import typing
import warnings
import weakref
from copy import deepcopy, copy

#### END core python modules

#### BEGIN 3rd party modules
from PyQt5 import QtGui, QtCore, QtWidgets
import numpy as np
import numpy.matlib as mlib
import pandas as pd
import quantities as pq
import vigra
import neo
from neo.core import baseneo
from neo.core import basesignal
from neo.core import container
from neo.core.dataobject import DataObject, ArrayDict
#### END 3rd party modules

#### BEGIN pict.core.modules

from . import xmlutils
from . import strutils

#import utilities
from .utilities import counter_suffix, unique
from .prog import safeWrapper

from imaging.imageprocessing import *

#import patchneo
#from .patchneo import neo

#from . import ephys

#### END pict.core.modules

#### BEGIN pict.systems modules
#from systems import * # PrairieView, soon ScanImage also
#### END pict.systems modules

# CHANGELOG (most recent first)
#
# NOTE: 2017-07-06 23:54:19
# NEW PHILOSOPHY:
# 1) operations on VigraArrays need not change the original axis calibration; 
#    1.a)   if an axis is gone, then that calibration could simply be ignored.
#
#    1.b)   when a new axis is added -- well, it receives a default axis tag anyway
#           so one might as well check/correct for the calibration manually
#
#    1.c)   transpositions should not really affect the calibrations; their order 
#           does not define a calibration; calibration should simply be retrieved 
#           by the axisinfo (tag) key
#
# 2) AxisInfo only accepts "free form" user data as a string (the "description" field)
#
#   Therefore a mechanism to attach a calibration to an axis info object
#   short of subclassing AxisInfo (in C++ !) is to generate a conversion from e.g.,
#   a calibration "tuple" to a string with a standardized format that conveys 
#   the unit of measure (e.g. pq.Quantity) and an origin value (a Real scalar, 
#   by default 0.0) -- for example: 
#
#   "UnitLength('micrometer', 0.001 * mm, 'um')|0.0"
#
#   where both elemens in the tuple (UnitLength('micrometer', 0.001 * mm, 'um'), 0.0)
#   are represented by two "|" - separated substrings
#
#
#   The calibration tuple could then be re-created by splitting this string and 
#   evaluating the resulting substrings (the first substring needs to be eval-ed
#   using the quantities module __dict__ as globals, see parseDescriptionString, below)
#
#
#   2.a) because the description should not be limited to a calibration string,
#       the format of this string should be distinctive and specific, therefore 
#       "|" - spearated format doesn't cut it
#
#   2.b) one could choose XML (xml.etree.ElementTree module)
#
#   to generate a string like:
#
#   <calibration><units>units_str</units><origin>offset_val_str</origin></calibration>
#
#   "calibration" xml tag is too generic -- change it to "axis_calibration"
#
#
#   Advantages of this approach:
#
#   when VigraArray operations change the axistags, the calibration is carried trough
#
#   no need for manually synchronize calibration in __MOST__ of the cases, except for
# the case when a new axis is added (vigra.newaxis), which I must then immediately 
# follow by calibrate(...) or something
#   
NUMPY_NUMERIC_KINDS = set("buifc")
NUMPY_STRING_KINDS = set("SU")

UnitTypes = collections.defaultdict(lambda: "NA", 
                                    {"a":"axon", "b":"bouton", "c":"cell", 
                                     "d":"dendrite", "e":"excitatory", 
                                     "g":"granule",  "i":"inhibitory", 
                                     "l":"stellate", "p":"pyramidal",  
                                     "m":"microglia", "n":"interneuron", 
                                     "s":"spine", "t":"terminal",
                                     "y":"astrocyte"})
                                    
Genotypes = ["NA", "wt", "het", "hom"]

sipfx = ("yotta", "zetta", "exa", "peta", "tera", 
       "giga", "mega", "kilo", "hecto", "deca", 
       "deci", "centi", "milli", "micro", "nano",
       "pico", "femto", "atto", "zepto", "yotto",)

sisymb = ("Y", "Z", "E", "P", "T", "G", "M", "k", "h", "da",
          "d", "c", "m", "mu", "n", "p", "f", "a", "z", "y",)

exps = tuple([k for k in range(24,2,-3)] + [2,1,-1,-2] + [k for k in range(-3, -37, -3)])


SI10Powers = dict([(p, dict([("exponent", e), ("symbol", s)])) for (p,e,s) in zip(sipfx, exps, sisymb)])



#NOTE: do not confuse with pq.au which is one astronomical unit !!!
arbitrary_unit = arbitraryUnit = ArbitraryUnit = pq.UnitQuantity('arbitrary unit', 1. * pq.dimensionless, symbol='a.u.')
pixel_unit  = pixelUnit = PixelUnit = pixel = pq.UnitQuantity('pixel', 1. * pq.dimensionless, symbol='pixel')

day_in_vitro = div = pq.UnitQuantity("day in vitro", 1 * pq.day, symbol = "div")
week_in_vitro = wiv = pq.UnitQuantity("week in vitro", 1 * pq.week, symbol = "wiv")

postnatal_day = pnd = pq.UnitQuantity("postnatal day", 1 * pq.day, symbol = "pnd")
postnatal_week = pnw = pq.UnitQuantity("postnatal week", 1 * pq.week, symbol = "pnw")
postnatal_month = pnm = pq.UnitQuantity("postnatal month", 1 * pq.month, symbol = "pnm")

embryonic_day = emd = pq.UnitQuantity("embryonic day", 1 * pq.day, symbol = "emd")
embryonic_week = emw = pq.UnitQuantity("embryonic week", 1 * pq.week, symbol = "emw")
embryonic_month = emm = pq.UnitQuantity("embryonic month", 1 * pq.month, symbol = "emm")

# NOTE: 2017-07-21 16:05:38
# a dimensionless unit for channel axis (when there are more than one channel in the data)
# NOTE: NOT TO BE CONFUSED WITH THE UNITS OF THE DATA ITSELF!
channel_unit = channelUnit = ChannelUnit = pq.UnitQuantity("channel", 1. * pq.dimensionless, symbol="channel")

space_frequency_unit = spaceFrequencyUnit = sfu = pq.UnitQuantity('space frequency unit', 1/pq.m, symbol='1/m')

# not to be confused with angular frequency which is radian/s (or Hz, if you consider radian to be dimensionless)
# thus 1 angle frequency equal one cycle per radian -- another form of space frequency
# where space is expressed in "angle" (e.g. visual angle)
angle_frequency_unit = angleFrequencyUnit = afu = pq.UnitQuantity('angle frequency unit', 1/pq.rad, symbol='1/rad')

custom_unit_symbols = dict()
custom_unit_symbols[arbitrary_unit.symbol] = arbitrary_unit
custom_unit_symbols[pixel_unit.symbol] = pixel_unit
custom_unit_symbols[channel_unit.symbol] = channel_unit
custom_unit_symbols[space_frequency_unit.symbol] = space_frequency_unit
custom_unit_symbols[angle_frequency_unit.symbol] = angle_frequency_unit
custom_unit_symbols[div.symbol] = div
custom_unit_symbols[wiv.symbol] = wiv
custom_unit_symbols[pnd.symbol] = pnd
custom_unit_symbols[pnw.symbol] = pnw
custom_unit_symbols[pnm.symbol] = pnm
custom_unit_symbols[emd.symbol] = emd
custom_unit_symbols[emw.symbol] = emw
custom_unit_symbols[emm.symbol] = emm

def make_scaled_unit_quantity(base_quantity, power):
    if not isinstance(base_quantity, (pq.Quantity,pq.UnitQuantity)):
        raise TypeError("base_quantity expected to be a UnitQuanitity or a Quantity; got %s instead" % type(base_quantity).__name__)
    
    if not isinstance(power, str):
        raise TypeError("power expected to be a str; got %s instead" % type(power).__name__)
    
    if power not in SI10Powers.keys():
        raise ValueError("Power %s is invalid" % power)
    
    name = "%s%s" % (power, base_quantity.units.dimensionality)
    factor = pow(10, SI10Powers[power]["exponent"])
    symbol = "%s%s" % (SI10Powers[power]["symbol"],base_quantity.units.symbol)
    
    return pq.UnitQuantity(name, factor * base_quantity, symbol=symbol)
    
kiloohm = kohm = make_scaled_unit_quantity(pq.ohm, "kilo")
custom_unit_symbols[kohm.symbol] = kohm
megaohm = Mohm = make_scaled_unit_quantity(pq.ohm, "mega")
custom_unit_symbols[Mohm.symbol] = Mohm
gigaohm = Gohm = make_scaled_unit_quantity(pq.ohm, "giga")
custom_unit_symbols[Gohm.symbol] = Gohm

#kiloohm = kohm = pq.UnitQuantity("kiloohm", 1e3 * pq.ohm, symbol="kohm")
#megaohm = Mohm = pq.UnitQuantity("megaohm", 1e6 * pq.ohm, symbol="Mohm")
#gigaohm = Gohm = pq.UnitQuantity("gigaohm", 1e9 * pq.ohm, symbol="Gohm")


# some other useful units TODO

#relative_tolerance = 1e-4
#absolute_tolerance = 1e-4
#equal_nan = True
    
def isVector(x):
    """Returns True if x is a numpy array encapsulating a vector.
    
    A vector is taken to be a numpy array with one dimension, or a numpy
    array with two dimensions (ndim == 2) with one singleton dimension
    """
    import numpy as np
    
    if not isinstance(x, np.ndarray):
        return False
    
    if x.ndim == 1:
        return True
    
    elif x.ndim == 2:
        return any([s == 1 for s in x.shape])
        
    else:
        return False
        
def isColumnVector(x):
    """Returns True if x is a numpy arrtay encapsulating a column vector.
    
    A column vector is taken to be a numpy array with one dimension or a numpy
    array with two dimensions where axis 1 is singleton
    """
    import numpy as np
    
    if not isinstance(x, np.ndarray):
        return False
    
    if x.ndim == 1:
        return True
    
    elif x.ndim == 2:
        return x.shape[1] == 1
        
    else:
        return False
        
def isRowVector(x):
    """Returns True if x is a numpy array encapsulating a column vector.
    
    A column vector is taken to be a numpy array with one dimension or a numpy
    array with two dimensions where axis 0 is singleton
    """
    import numpy as np
    
    if not isinstance(x, np.ndarray):
        return False
    
    if x.ndim == 1:
        return True
    
    elif x.ndim == 2:
        return x.shape[0] == 1
        
    else:
        return False
    
def arraySlice(data:np.ndarray, slicing:(dict, type(None))):
    """Dynamic slicing of nD arrays and introducing new axis in the array.
    """
    if not isinstance(data, np.ndarray):
        raise TypeError("data expected to be a numpy ndarray or vigra array; got %s instead" % type(data).__name__)
    
    indexobj = [slice(0,k) for k in data.shape]
    
    
    oldaxisNdx = list()
    oldaxisSlc = list()
    newaxisNdx = list()
    newaxisSlc = list()
    
    currentAxes = [k for k in range(data.ndim)]
    dimensions = data.ndim
    
    if isinstance(slicing, dict):
        for k in slicing.keys():
            if isinstance(k, (str, vigra.AxisInfo)):
                if not isinstance(data, vigra.VigraArray):
                    raise TypeError("str or AxisInfo axis indices are only supported by vigra arrays")
                
                if isinstance(k, vigra.AxisInfo):
                    if k.key not in data.axistags:
                        if data.ndim == 5:
                            raise ValueError("AxisInfo %s not found in data, and data already has maximum of 5 dimensions" % k.key)
                        
                        else:
                            newaxisNdx.append(data.ndim)
                            newaxisSlc.append(vigra.newaxis())
                            dimensions += 1
                            
                    else:
                        oldaxisNdx.append(data.axistags.index(k.key))
                        oldaxisSlc.append(slicing[k])
                    
                else:
                    if k not in data.axistags:
                        if data.ndim == 5:
                            raise ValueError("Axis key %s not found in data and data already has five dimensions" % k.key)
                        
                        else:
                            newaxisNdx.append(data.ndim)
                            newaxisSlc.append(vigra.newaxis())
                            dimensions += 1
                    else:
                        oldaxisNdx.append(data.axistags.index(k))
                        oldaxisSlc.append(slicing[k])
                    
            elif isinstance(k, int):
                if k < 0:
                    raise ValueError("Axis index must be >= 0")
                
                if k >= dimensions:
                    if isinstance(data, vigra.VigraArray) and data.ndim == 5:
                        raise ValueError("Data already has the maximum of five dimensions")
                    
                    else:
                        n_ax = k-dimensions+1
                        newaxisNdx += [i for i in range(dimensions, k+1)]
                        newaxisSlc += [np.newaxis] * n_ax
                        dimensions += n_ax
                        #print("n_ax", n_ax)
                    
                else:
                    ndx = k
                    slc = slicing[k]
                    
                    if slc is None:
                        # this means we want to INSERT a new axis at position k
                        if isinstance(data, vigra.VigraArray):
                            raise TypeError("New axis for vigra arrays must be specified as a vigra.AxisInfo object")
                        
                        newaxisNdx.append(k)
                        newaxisSlc.append(slc)
                        dimensions += 1
                        
                    else:
                        oldaxisNdx.append(k)
                        oldaxisSlc.append(slc)
                
            else:
                raise TypeError("Invalid slicing key type; admissible types are int, str, vigra.AxisInfo (last two for vigra arrays) but got %s instead" % type(k).__name__)
            
        #print("oldaxisNdx", oldaxisNdx, "oldaxisSlc", oldaxisSlc)
        
        for k, s in zip(oldaxisNdx, oldaxisSlc):
            if isinstance(s, range):
                s = slice(s.start, s.stop, s.step)
                
            elif not isinstance(s, (int, slice)):
                raise TypeError("Invalid slice type %s for existing axis %d" % (type(s).__name__, k))
                
            indexobj[k] = s
            
        #print("newaxisNdx", newaxisNdx, "newaxisSlc", newaxisSlc)
        
        for k, s in zip(newaxisNdx, newaxisSlc):
            if not isinstance(s, (type(None), vigra.AxisInfo)):
                # s can be either None, or vigra.newaxis()
                raise TypeError("For a new axis at index %d the slicing can be only None or vigra.AxisInfo; got %s instead" % (k, type(s).__name__))

            indexobj.insert(k, s)
            
    elif slicing is not None:
        raise TypeError("Slicing expected to be a dict or None; got %s instead" % type(slicing).__name__)
    
    return tuple(indexobj)
    
def is_string(array):
    """Determine whether the argument has a string or character datatype, when
    converted to a NumPy array.
    
    String or character (including unicode) have dtype.kind of "S" or "U"
    
    """
    return np.asarray(array).dtype.kind in NUMPY_STRING_KINDS

def is_numeric_string(array):
    """Determines of the argumen is a string array that can be parsed as numeric.
    """
    return is_string(array) and not np.isnan(np.genfromtxt(value)).any()
        

def is_numeric(array):
    """Determine whether the argument has a numeric datatype, when
    converted to a NumPy array.

    Booleans, unsigned integers, signed integers, floats and complex
    numbers are the kinds of numeric datatype.

    Parameters
    ----------
    array : array-like
        The array to check.

    Returns
    -------
    is_numeric : `bool`
        True if the array has a numeric datatype, False if not.
        
    NOTE: 
    from https://codereview.stackexchange.com/questions/128032/check-if-a-numpy-array-contains-numerical-data

    """
    return np.asarray(array).dtype.kind in NUMPY_NUMERIC_KINDS


def normalized_axis_index(data:np.ndarray, axis:(int, str, vigra.AxisInfo)) -> int:
    """Returns an integer index for a specific array axis
    """
    if not isinstance(data, np.ndarray):
        raise TypeError("Expecting a numpy array or a derivative; got %s instead" % type(data).__name__)
    
    if not isinstance(axis, (int, str, vigra.AxisInfo)):
        raise TypeError("Axis expected to be an int, a str or a vigra.AxisInfo; got %s instead" % type(axis).__name__)
    
    if isinstance(axis, (str, vigra.AxisInfo)):
        # NOTE: 2019-11-22 12:39:30
        # for VigraArray only, normalize axis index from str or AxisInfo to int
        if not isinstance(data, vigra.VigraArray):
            raise TypeError("Generic numpy arrays do not support axis index as strings or AxisInfo objects")
        
        if isinstance(axis, str):
            axis = data.axitags.index(axis)
            
        elif isinstance(axis, vigra.AxisInfo):
            axis = data.axistags.index(axis.key)
            
    # NOTE: 2019-11-22 12:39:17
    # by now, axis is an int
    if axis < 0 or axis > data.shape[axis]:
        raise ValueError
    
    return axis

def normalized_index(data: typing.Optional[typing.Union[typing.Sequence, int]],
                     index: typing.Optional[typing.Union[str, int, tuple, list, np.ndarray, range, slice]] = None,
                     multiple:bool = True) -> typing.Union[range, tuple]:
    """Returns a generic indexing in the form of an iterable of indices.
    
    Also checks the validity of the index for an iterable of data_len samples.
    
    Parameters:
    -----------
    data: a sequence, or an int; the index will be normalized against its length
        When an int, data is the length of a putative sequence
    
    index: int, tuple, list, np.ndarray, range, slice, None (default).
        When not None, it is the index to be normalized
    
        CAUTION: negative integral indices are valid and perform the reverse 
            indexing (going "backwards" in the iterable).
    
    Returns:
    --------
    ret - an iterable index (range or list of integer indices) that can be
        used with list comprehension
    
    """
    if data is None:
        return tuple()
    
    if not isinstance(data, (int, tuple, list)):
        raise TypeError("Expecting an int or a sequence (tuple, or list) or None; got %s instead" % type(data).__name__)
    
    data_len = data if isinstance(data, int) else len(data)
    
    if index is None:
        return range(data_len)
    
    elif isinstance(index, int):
        # NOTE: 2020-03-12 22:40:31
        # negative values ARE supported: they simply go backwards from the end of
        # the sequence
        if index >= len(data):
            raise ValueError("Index %s is invalid for %d elements" % (index, len(data)))
        
        if flat:
            return index
        
        return tuple([index]) # -> (index,)
    
    elif isinstance(index, str):
        if not isinstance(data, (tuple, list)):
            raise TypeError("Name lookup requires a sequence")
        
        ret = __name_lookup__(data, index, multiple=multiple)
        #ret = __name_lookup__(data, index, silent=silent, multiple=multiple)
        
        if isinstance(ret, numbers.Number):
            return tuple([ret])
        
        elif isinstance(ret, (tuple, list)):
            if len(ret) > 1:
                return tuple(ret)
            
            else:
                return tuple([ret[0]])
            
        else:
            return tuple()
            
    elif isinstance(index, (tuple,  list)):
        if not all([isinstance(v, (int, str)) for v in index]):
            raise TypeError("Index sequence %s is expected to contain int only" % index)
        
        if any([isinstance(v, str) for v in index]):
            if not isinstance(data, (tuple, list)):
                raise TypeError("Name lookup requires a sequence")
            
            return tuple([v if isinstance(v, int) and v < data_len else __name_lookup__(data, v, multiple=multiple) for v in index])
            
        else:
            if not all([v < data_len for v in index]):
                raise ValueError("Index sequence %s contains invalid values for %d elements" % (index, data_len))
            
            return tuple(index) # -> index as a tuple
    
    elif isinstance(index, range):
        if index.start < 0 or index.stop < 0:
            warnings.warn("Range %s will produce reverse indexing" % index)
            
        if max(index) >= data_len:
            raise ValueError("Index %s out of range for %d elements" % (index, data_len))
        
        return index # -> index IS a range
    
    elif isinstance(index, slice):
        if index.start < 0 or index.stop < 0:
            warnings.warn("Index %s will produce reverse indexing or an empty indexing list" % index)
            
        if max(index) >= data_len:
            raise ValueError("Index %s out of range for %d elements" % (index, data_len))
        
        ndx = index.indices(data_len)
        
        if len(ndx) == 0:
            raise ValueError("Indexing %s results in an empty indexing list" % index)
        
        if any(ndx) >= data_len:
            raise ValueError("Slice %s generates out of range indices (%s) for %d elements" % (index, ndx, data_len))
        
        if any(ndx) < 0:
            warnings.warn("Index %s will produce reverse indexing" % index)
            
        return ndx # -> ndx IS a tuple
    
    elif isinstance(index, np.ndarray):
        if not isVector(index):
            raise TypeError("Indexing array must be a vector; instead its shape is %s" % index.shape)
            
        if index.dtype.kind == "i": # index is an array of int
            return tuple([k for k in index])
        
        elif index.dtype.kind == "b": # index is an array of bool
            if len(index) != data_len:
                raise TypeError("Boolean indexing vector must have the same length as the iterable against it will be normalized (%d); got %d instead" % (data_len, len(index)))
            
            return tuple([k for k in range(data_len) if index[k]])
            
    else:
        raise TypeError("Unsupported data type for index: %s" % type(index).__name__)
    
def normalized_sample_index(data:np.ndarray, 
                            axis: typing.Union[int, str, vigra.AxisInfo], 
                            index: typing.Optional[typing.Union[int, tuple, list, np.ndarray, range, slice]]=None) -> typing.Union[range, list]:
    """Calls normalized_index on a specific array axis.
    Also checks index validity along a numpy array axis.
    
    Parameters:
    ----------
    data: numpy.ndarray or a derivative (e.g. neo.AnalogSgnal, vigra.VigraArray)
    
    axis: int, str, vigra.AxisInfo. The array axis along which the index is normalized.
    
    index: int, tuple, list, np.ndarray, range, slice, None (default).
        When not None, it is the index to be normalized.
        
        CAUTION: negative integral indices are valid and perform the indexing 
        "backwards" in an array.
    
    Returns:
    --------
    ret - an iterable (range or list) of integer indices
    
    """
    if not isinstance(data, np.ndarray):
        raise TypeError("Expecting a numpy array or a derivative; got %s instead" % type(data).__name__)
    
    if not isinstance(axis, (int, str, vigra.AxisInfo)):
        raise TypeError("Axis expected to be an int, a str or a vigra.AxisInfo; got %s instead" % type(axis).__name__)
    
    axis = normalized_axis_index(data, axis)
    
    data_len = data.shape[axis]
    
    try:
        return normalized_index(data_len, index)
    
    except Exception as exc:
        raise RuntimeError("For data axis %d with size %d:" % (axis, data_len)) from exc

def __default_none__():
    return None

def __default_units__():
    return arbitrary_unit

def __default_undimensioned__():
    return pq.dimensionless

def unit_quantity_from_name_or_symbol(s):
    if not isinstance(s, str):
        raise TypeError("Expecting a string; got %s instead" % type(s).__name__)
    
    if s in pq.__dict__:
        ret = eval(s, pq.__dict__)
        #try:
            #ret = eval(s, pq.__dict__)
            
        #except Exception as err:
            #warnings.warn("String %s could not be evaluated to a Python Quantity" % s, RuntimeWarning)
            #ret = pq.dimensionless
            
    elif s in custom_unit_symbols.keys():
        ret = custom_unit_symbols[s]
        
    elif s in [u.name for u in custom_unit_symbols.values()]:
        ret = [u for u in custom_unit_symbols.values() if u.name == s]
        
    else:
        warnings.warn("Unknown unit quantity %s" % s, RuntimeWarning)
        
        ret = pq.dimensionless
        
    return ret
        
def name_from_unit(u):
    """
    FIXME make it more intelligent!
    """
    d_name = ""
    
    if not isinstance(u, (pq.UnitQuantity, pq.Quantity)):
        return d_name
        #raise TypeError("Expecting a Quanity or UnitQuanity; got %s instead" % type(u).__name__)
    
    unitQuantity = [k for k in u.dimensionality.keys()]
    
    
    if len(unitQuantity):
        unitQuantity = unitQuantity[0] 
    
        d_name = unitQuantity.name
        
        if d_name in ("Celsius", "Kelvin", "Fahrenheit"):
            d_name = "Temperature"
            
        elif d_name in ("arcdegree"):
            d_name = "Angle"
            
        elif "volt" in d_name:
            d_name = "Potential"
            
        elif "ampere" in d_name:
            d_name = "Current"
            
        elif "siemens" in d_name:
            d_name = "Conductance"
            
        elif "ohm" in d_name:
            d_name = "Resistance"
            
        elif "coulomb" in d_name:
            d_name = "Capacitance"
            
        elif "hertz" in d_name:
            d_name = "Frequency"
        
        elif any([v in d_name for v in ("meter", "foot", "mile","yard")]):
            d_name = "Length"
            
        elif any([v in d_name for v in ("second", "minute", "day","week", "month", "year")]):
            d_name = "Time"
            
    return d_name
            
    

def check_time_units(value):
    if not isinstance(value, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("Expecting a python UnitQuantity or Quantity; got %s instead" % type(value).__name__)
    
    ref = pq.s
    
    return value._reference.dimensionality == ref.dimensionality
    
def conversion_factor(x, y):
    """Calculates the conversion factor from y units to x units.
    """
    if not isinstance(x, (pq.Quantity, pq.UnitQuantity)):
        raise TypeError("x expected to be a python Quantity; got %s instead" % type(x).__name__)
    
    if not isinstance(y, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("y expected to be a python UnitQuantity or Quantity; got %s instead" % type(y).__name__)
    
    if x._reference.dimensionality != y._reference.dimensionality:
        raise TypeError("x and y have incompatible units (%s and %s respectively)" % (x.units, y.units))

    x_dim = pq.quantity.validate_dimensionality(x)
    y_dim = pq.quantity.validate_dimensionality(y)
    
    if x_dim != y_dim:
        try:
            cf = pq.quantity.get_conversion_factor(x_dim, y_dim)
            
        except AssertionError:
            raise ValueError("Cannot convert from %s to %s" % (origin_dim.dimensionality, self_dim.dimensionality))
        
        return cf
    
    else:
        return 1.0

def units_convertible(x, y):
    """Checks that the units of python Quantities x and y are identical or convertible to each other.
    NOTE: To check that x and y have IDENTICAL units simply call 'x.units == y.units'
    """
    if not isinstance(x, (pq.Quantity, pq.UnitQuantity)):
        raise TypeError("x expected to be a python Quantity; got %s instead" % type(x).__name__)
    
    if not isinstance(y, (pq.UnitQuantity, pq.Quantity)):
        raise TypeError("y expected to be a python UnitQuantity or Quantity; got %s instead" % type(y).__name__)
    
    return x._reference.dimensionality == y._reference.dimensionality

    
def categorize_data_frame_columns(data, *column_names, inplace=True):
    """"""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)
    
    if len(column_names) == 0:
        raise TypeError("Expectign at least one column")
    
    if any([not isinstance(c, str) for c in column_names]):
        raise TypeError("All column names expected to be strings")
    
    if any([c not in data.columns for c in column_names]):
        raise ValueError("At least one of the specified columns does not exist in data")
    
    if inplace:
        for c in column_names:
            data[c] = pd.Categorical(data[c].astype("category"))
            
        return data
            
    else:
        ret = data.copy()
        for c in column_names:
            ret[c] = pd.Categorical(data[c].astype("category"))
            
        return ret

class UnitsStringValidator(QtGui.QValidator):
    def __init__(self, parent=None):
        super(UnitsStringValidator, self).__init__(parent)
        
    def validate(self, s, pos):
        try:
            u = eval("1*%s" % (s[0:pos]), pq.__dict__)
            return QtGui.QValidator.Acceptable
        
        except:
            return QtGui.QValidator.Invalid
        
    
#__AnalysisUnit__ = AnalysisUnit

class IndicatorCalibration(object):
    def __init__(self, name=None, Kd = None, Fmin = None, Fmax = None):
        super().__init__(self)
        
        self.name=name
        self.Kd = Kd
        self.Fmin = Fmin
        self.Fmax = Fmax
        
        
#class PictArray(vigra.VigraArray):
    #"""DO NOT USE -- inheritance from VigraArray is broken
    #Extends vigra.VigraArray with axes calibration concept.
    #Does NOT replicate VigraArray static methods!!!
    
    #To calibrate an axis (or an individual channel in a Channels axis)
    #call one of the setXXX() methods of its "axiscalibration" property.
    
    #FIXME: after calling VigraArray methods such as bindAxis, the PictArray
    #will lose its __axiscalibration__ attribute
    
    #"""
    
    #def __new__(cls, obj, dtype=np.float32, order=None, init=True, value=None, axistags=None):
        ##print("__new__ Cls:", cls)
        ##print("__new__ type(args[0]):", type(obj))
        
        ##ret = vigra.VigraArray(obj, dtype=dtype, order=order, init=init, value=value, axistags=axistags)
        
        ##ret.__class__.__name__ = "PictArray"
        
        ## NOTE: 2018-09-11 15:48:12
        ## this doesn't work because internally (at C++ level)0 this expects cls to be VigraArray
        ## 
        #ret = super(PictArray, cls).__new__(cls, obj, dtype=dtype, order=order, init=init, value=value, axistags=axistags)
        
        ##print("__new__ type(ret)", type(ret))
        
        #return ret

    #def __init__(self, *args, **kwargs):
        ##print("__init__ type(self)", type(self))
        ##print("__init__ args", args)
        #if not hasattr(self, "__axiscalibration__"):
            #self.__axiscalibration__ = AxisCalibration(self)
            #for ax in self.axistags:
                #self.__axiscalibration__.calibrateAxis(ax)
            

    #def __array_finalize__(self, obj):
        #super(PictArray, self).__array_finalize__(obj)
        
        ##print("__array_finalize__", type(obj))
        
        #if not hasattr(self, "__axiscalibration__"):
            #self.__axiscalibration__ = AxisCalibration(obj)
        #else:
            #self.__axiscalibration__.synchronize()
        ##if isinstance(obj, vigra.VigraArray):
        
    #@property
    #def axiscalibration(self):
        #if not hasattr(self, "__axiscalibration__"):
            #self.__axiscalibration__ = AxisCalibration(self)

        #return self.__axiscalibration__
    
    #@axiscalibration.setter
    #def axiscalibration(self, value):
        #if not isinstance(value, AxisCalibration):
            #raise TypeError("Expectign an AxisCalibration object; got %s instead" % type(value).__name__)
        
        #if any([key not in self.axistags for key in value.keys()]):
            #raise ValueError("AxisCalibration axis %s does not exist in this PictArray object" % key)
        
        #self.__axiscalibration__ = value
        
        #for ax in self.axistags:
            #self.__axiscalibration__.calibrateAxis(ax)
            
