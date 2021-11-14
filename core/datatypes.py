# -*- coding: utf-8 -*-
''' Utilities for generic and numpy array-based data types such as quantities
Changelog:
2021-01-06 14:35:30 gained module-level constants:
RELATIVE_TOLERANCE
ABSOLUTE_TOLERANCE
EQUALS_NAN

'''

from __future__ import print_function

#### BEGIN core python modules
import collections 
from collections import deque
import datetime
from enum import (Enum, IntEnum,)
import inspect
import numbers
import sys
import time
import traceback
import typing
import warnings
import weakref
from copy import (deepcopy, copy,)

#### END core python modules

#### BEGIN 3rd party modules
from PyQt5 import (QtGui, QtCore, QtWidgets,)
import numpy as np
from numpy import ndarray
import numpy.matlib as mlib
import pandas as pd
import quantities as pq
import vigra
import neo
from neo.core import (baseneo, basesignal, container,)
from neo.core.dataobject import (DataObject, ArrayDict,)
#### END 3rd party modules

#### BEGIN pict.core.modules
from core import quantities as cq
from . import xmlutils
from . import strutils
from .prog import safeWrapper

#from imaging.imageprocessing import *
#### END pict.core.modules

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
abbreviated_type_names = {'IPython.core.macro.Macro' : 'Macro'}
sequence_types = (list, tuple, deque)
sequence_typenames = (t.__name__ for t in sequence_types)
#sequence_typenames = ('list', 'tuple', "deque")
set_types = (set, frozenset)
set_typenames = (t.__name__ for t in set_types)
#set_typenames = ("set", "frozenset")
dict_types = (dict,)
dict_typenames = (t.__name__ for t in dict_types)
#dict_typenames = ("dict",)
# NOTE: neo.Segment class name clashes with nrn.Segment
neo_containernames = ("Block", "Segment",)
# NOTE: 2020-07-10 12:52:57
# PictArray is defunct
signal_types = ('Quantity', 'AnalogSignal', 'IrregularlySampledSignal', 
                'SpikeTrain', "DataSignal", "IrregularlySampledDataSignal",
                "TriggerEvent",)
                
ndarray_type = ndarray.__name__

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


RELATIVE_TOLERANCE = 1e-4
ABSOLUTE_TOLERANCE = 1e-4
EQUAL_NAN = True



def is_vector(x):
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
        
def is_column_vector(x):
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
    
def is_uniform_sequence(s):
    ret = isinstance(s, collections.abc.Sequence) 

    if ret:
        ret &= all(isinstance(v, type(s[0])) for v in s[1:])

    return ret

def sequence_element_type(s):
    from utilities import unique
    return unique((type(e) for e in s))
    
    
def array_slice(data:np.ndarray, slicing:(dict, type(None))):
    """Dynamic slicing of nD arrays and introducing new axis in the array.
    """
    if not isinstance(data, np.ndarray):
        raise TypeError("data expected to be a numpy ndarray or a type derived from numpy ndarray; got %s instead" % type(data).__name__)
    
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

def is_hashable(x):
    ret = bool(getattr(x, "__hash__", None) is not None)
    if ret:
        try:
            # because some 3rd party packages 'get smart' and override __hash__()
            # to raise Exception 
            hash(x) 
            return True
        except:
            return False
        

def is_dotted_name(s):
    return isinstance(s, str) and '.' in s

def is_namedtuple(x):
    if isinstance(x, type):
        ret = issubclass(x, tuple)
    else:
        ret = issubclass(type(x), tuple)
        
    if ret: 
        ret &= all([hasattr(x, a) for a in ("_asdict", "_fields", "_make", "_replace")])
        
    return ret
    
def is_string(array):
    """Determine whether the argument has a string or character datatype, when
    converted to a NumPy array.
    
    String or character (including unicode) have dtype.kind of "S" or "U"
    
    """
    return np.asarray(array).dtype.kind in NUMPY_STRING_KINDS

def is_numeric_string(array):
    """Determines if the argument is a string array that can be parsed as numeric.
    """
    if isinstance(array, str):
        array = [array]
        
    return is_string(array) and not np.isnan(np.genfromtxt(array)).any()
        

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
    
class TypeEnum(IntEnum):
    """Common ancestor for enum types used in Scipyen
    """
    @classmethod
    def names(cls):
        """Iterate through the names in TypeEnum enumeration.
        """
        for t in cls:
            yield t.name
    
    @classmethod
    def values(cls):
        """Iterate through the int values of TypeEnum enumeration.
        """
        for t in cls:
            yield t.value
        
    @classmethod
    def types(cls):
        """Iterate through the elements of TypeEnum enumeration.
        Useful to quickly remember what the members of this enum are (with their
        names and values).
        
        A TypeEnum enum member is by definition a member 
        of TypeEnum enum and an instance of TypeEnum.
        
        """
        for t in cls:
            yield t
            
    @classmethod
    def namevalue(cls, name:str):
        """Return the value (int) for given name;
        If name is not a valid TypeEnum name returns -1
        """
        if name in cls.names():
            return getattr(cls, name).value
        
        return -1
    
    @classmethod
    def type(cls, t):
        if isinstance(t, str):
            if t in cls.names():
                return [_t for _t in cls if _t.name == t][0]
            else:
                # check for user-defined composite type - break it down to a list
                # of existing types, if possible
                if "|" in t:
                    t_hat = [cls.type(_t.strip()) for _t in t.split("|")]
                    if len(t_hat):
                        return t_hat
                    else:
                        raise ValueError("Unknown %s type name %s" % (cls.__name__, t))
                else:
                    raise ValueError("Unknown %s type name %s" % (cls.__name__, t))
            
        elif isinstance(t, int):
            if t in cls.values():
                return [_t for _t in cls if _t.value == t][0]
            else:
                # check for implicit composite type (i.e. NOT listed in the definition)
                ret = [_t for _t in cls if _t.value & t]
                if len(ret):
                    return ret
                else:
                    raise ValueError("Unknown %s type value %d" % (cls.__name__, t))
            
        elif isinstance(t, cls):
            return t
        
        else:
            raise TypeError("Expecting a %s, int or str; got %s instead" % (cls.__name__, type(t).__name__))
            
    @classmethod
    def strand(cls, name1:str, name2:str):
        """ Emulates '&' operator for type names 'name1' and 'name2'.
        If neither arguments are valid names returns 0
        """
        if any([n not in cls.names() for n in [name1, name2]]):
            return 0
        
        val1 = cls.namevalue(name1)
        val2 = cls.namevalue(name2)
        
        return val1 & val2
    
    @classmethod
    def is_primitive_type(cls, t):
        """Checks if 't' is a primitive type in this types enumeration.
        
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)
        
            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)
        
        """
        return len(cls.primitive_component_types(t)) == 0
    
    @classmethod
    def is_derived_type(cls, t):
        """Checks if 't' is a compound type (i.e. derived from other type enums)
        
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)
        
            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)
        
        """
        return len(cls.component_types(t)) > 0
        #return len(cls.primitive_component_types(t)) > 0
        
    @classmethod
    def is_composite_type(cls, t):
        """Alias of TypeEnum.is_derived_type()
        
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)
        
            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)
        
        """
        return cls.is_derived_type(t)
    
    @classmethod
    def primitive_component_types(cls, t):
        """ Returns a list of primitive TypeEnum objects that compose 't'.
        If 't' is already a primitive type, returns an empty list.
        
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)
        
            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)
        
        """
        from .utilities import unique
        if isinstance(t, (int, str)):
            t_hat = cls.type(t)
            if isinstance(t_hat, list):
                return unique([__t for __t in chain.from_iterable([[_t for _t in cls if _t.is_primitive() and _t.value <= t_.value] for t_ in t_hat])])
            else:
                t = t_hat
                
        elif not isinstance(t, cls):
            raise TypeError("Expecting a TypeEnum, int or str; got %s instead" % type(t).__name__)
        
        return [_t for _t in filter(lambda x: x & t, cls) if _t.value < t.value and _t.is_primitive()]
        
    @classmethod
    def component_types(cls, t):
        """ Returns a list of TypeEnum objects that compose 't'.
        If 't' is already a primitive type, returns an empty list.
    
        The TypeEnum objects can also be composite types.
        
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)
        
            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)
        
        """
        from .utilities import unique
        if isinstance(t, (int, str)):
            t_hat = cls.type(t)
            if isinstance(t_hat, list):
                # NOTE: 2021-04-14 23:33:22
                # by definition this only occurs with a composite type
                return unique([__t for __t in chain.from_iterable([[_t for _t in cls if _t.value <= t_.value] for t_ in t_hat])])
            else:
                t = t_hat
                
        elif not isinstance(t, cls):
            raise TypeError("Expecting a %s, int or str; got %s instead" % (cls.__name__, type(t).__name__))
        
        return [_t for _t in filter(lambda x: x & t, cls) if _t.value < t.value]
    
    @classmethod
    def derived_types(cls, t):
        """ Returns the composite TypeEnum objects where 't' participates.
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)
        
            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)
        
        """
        if isinstance(t, (int, str)):
            t_hat = cls.type(t)
            if isinstance(t_hat, list):
                return unique([__t for __t in chain.from_iterable([[_t for _t in cls if _t is not t_ and _t.value > t_.value] for t_ in t_hat])])
            else:
                t = t_hat
                
        elif not isinstance(t, cls):
            raise TypeError("Expecting a %s, int or str; got %s instead" % (cls.__name__, type(t).__name__))
        
        return [_t for _t in filter(lambda x: x & t, cls) if not _t.is_primitive() and _t is not t and _t.value > t.value]# _t.value > t.value]
        
    
    def is_derived(self):
        """Return True if this TypeEnum object is a composite (i.e., derived) type.
        """
        return self.is_derived_type(self)
    
    def is_composite(self):
        """Return True if this TypeEnum object is a composite (i.e., derived) type.
        """
        return self.is_derived()
    
    def is_primitive(self):
        return self.is_primitive_type(self)
    
    def primitives(self):
        """Returns a list of primitive types used to generate this type.
        
        Compound types are generated from primitive types through the logical
        OR operator (bitwise OR).
        
        Returns an empty list of this is a primitive type.
        """
        return self.primitive_component_types(self)
    
    def components(self):
        """Returns a list of components for this TypeEnum object.
        
        Compound types are generated from primitive types through the logical
        OR operator (bitwise OR).
        
        If this TypeEnum object is a primitive returns an empty list
        """
        return self.component_types(self)
    
    def includes(self, t):
        """Returns True if 't' is a component of this TypeEnum object.
        
        't' may be a primitive or a composite type.
        
        Always returns False when this is a primitive.
        """
        t = self.type(t)
            
        return t in self.components()
    
    def is_primitive_of(self, t):
        """Returns True if this TypeEnum object is a primitive of 't'.
        
        Always returns False when this TypeEnum object is a composite (i.e., 
        even if it is a component of 't').
        """
        t = self.type(t)
            
        return self in t.primitives()
    
    def is_component_of(self, t):
        """Returns True if this TypeEnum object is a component of 't'.
        """
        t = self.type(t)
        
        return self in t.components()
    
    def nameand(self, name:str):
        """ Applies strand() to the name of this object and the argument.
        """
        return self.strand(self.name, name)
        
        
