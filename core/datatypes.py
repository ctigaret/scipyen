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
import xarray as xa
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
from .utilities import safeWrapper, counterSuffix, unique

from .imageprocessing import *

#import patchneo
#from .patchneo import neo

#from . import neoutils

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

UnitTypes = collections.defaultdict(lambda: "NA", 
                                    {"a":"axon", "b":"bouton", "c":"cell", 
                                    "d":"dendrite", "e":"excitatory", 
                                    "g":"granule",  "i":"inhibitory", 
                                    "l":"stellate", "p":"pyramidal",  
                                    "m":"microglia", "n":"interneuron", 
                                    "s":"spine", "t":"terminal",
                                    "y":"astrocyte"})
                                    
Genotypes = ["NA", "wt", "het", "hom"]


NUMPY_NUMERIC_KINDS = set("buifc")
NUMPY_STRING_KINDS = set("SU")

#NOTE: do not confuse with pq.au which is one astronomical unit !!!
arbitrary_unit = arbitraryUnit = ArbitraryUnit = pq.UnitQuantity('arbitrary unit', 1. * pq.dimensionless, symbol='a.u.')
pixel_unit  = pixelUnit = PixelUnit = pq.UnitQuantity('pixel', 1. * pq.dimensionless, symbol='pixel')

day_in_vitro = div = pq.UnitQuantity("day in vitro", 1 *pq.day, symbol = "div")
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

# some other useful units TODO

#relative_tolerance = 1e-4
#absolute_tolerance = 1e-4
#equal_nan = True
    
def is_string(array):
    """Determine whether the argument has a string or character datatype, when
    converted to a NumPy array.
    
    String or character (including unicode) have dtype.kind of "S" or "U"
    
    """
    return np.asarray(array).dtype.kind in NUMPY_STRING_KINDS

def is_numeric_string(array):
    
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
            
def __set_valid_key_names__(obj):
    if isinstance(obj, ScanData):
        __set_valid_key_names__(obj._analysis_unit_)
        
        for au in obj._analysis_units_:
            __set_valid_key_names__(au)
            
        if len(obj.analysisoptions) and isinstance(obj.analysisoptions, dict):
            __set_valid_key_names__(obj.analysisoptions)
                
            if "Discrimination" in obj.analysisoptions and isinstance(obj.analysisoptions["Discrimination"], dict):
                if "data_2D" in obj.analysisoptions["Discrimination"]:
                    d2d = obj.analysisoptions["Discrimination"]["data_2D"]
                    obj.analysisoptions["Discrimination"].pop("data_2D", None)
                    obj.analysisoptions["Discrimination"]["Discr_2D"] = d2d
                    
            if "Fitting" in obj.analysisoptions and isinstance(obj.analysisoptions["Fitting"], dict):
                if "CoefficientNames" in obj.analysisoptions["Fitting"] and \
                    isinstance(obj.analysisoptions["Fitting"]["CoefficientNames"], (tuple, list)) and \
                        len(obj.analysisoptions["Fitting"]["CoefficientNames"]):
                            __set_valid_key_names__(obj.analysisoptions["Fitting"]["CoefficientNames"])
            
    elif isinstance(obj, AnalysisUnit):
        __set_valid_key_names__(obj.descriptors)
        if "Dd_Length" in obj.descriptors:
            value = obj.descriptors["Dd_Length"]
            obj.descriptors["Dendrite_Length"] = value
            obj.descriptors.pop("Dd_Length", None)
            
                
    elif isinstance(obj, (DataBag, dict)):
        items = list(obj.items())#[item for item in obj.items()]
        
        for item in items:
            if isinstance(item[0], str):
                try:
                    item_type = type(eval(item[0])).__name__
                    if item_type == "function":
                        continue
                    
                except:
                    pass
                    
                value = item[1]
                
                if isinstance(value, (dict, list)):
                    __set_valid_key_names__(value)
                
                obj.pop(item[0], None)
                obj[strutils.string_to_valid_identifier(item[0])] = value
            
    
    elif hasattr(obj, "annotations"):
        if type(obj) in neo.__dict__.values() or isinstance(obj, DataSignal):
            __set_valid_key_names__(obj.annotations)
    
    elif isinstance(obj, (tuple, list)):
        for k, o in enumerate(obj):
            if isinstance(o, str):
                obj[k] = strutils.string_to_valid_identifier(o)
        #if isinstance(obj, list):
            ##for k, o in enumerate(obj):
                ##if not isinstance(o, str): # don't touch string values!
                    ##obj[k] = __set_valid_key_names__(o)
            
        #else:
            #oo = list(obj)
            #for o in oo
            #for k, o in enumerate(oo):
                #if not isinstance(o, str): # don't touch string values!
                    #oo[k] = __set_valid_key_names__(o)
                
            #obj = tuple(oo)
            
    #return obj

#@safeWrapper
#def _upgrade_attribute_(obj, old_name, new_name, attr_type, default_value):
    #needs_must = False
    #if not hasattr(obj, new_name):
        #needs_must = True
        
    #else:
        #attribute = getattr(obj, new_name)
        
        #if not isinstance(attribute, attr_type):
            #needs_must = True
            
    #if needs_must:
        #if hasattr(obj, old_name):
            #old_attribute = getattr(obj, old_name)
            
            #if isinstance(old_attribute, attr_type):
                #setattr(obj, new_name, old_attribute)
                #delattr(obj, old_name)
                
            #else:
                #setattr(obj, new_name, default)
                #delattr(obj, old_name)
                
        #else:
            #setattr(obj, new_name, default)
            
    #return obj


def check_apiversion(data):
    if isinstance(data, (AxisCalibration, AnalysisUnit, ScanData)):
        if not hasattr(data, "apiversion"):
            return False
        
        if not isinstance(data.apiversion, tuple) or len(data.apiversion) !=2:
            return False
        
        return data.apiversion[0] + data.apiversion[1]/10 >= 0.2
            
    return True
