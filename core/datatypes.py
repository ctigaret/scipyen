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
from functools import (singledispatch, singledispatchmethod)
import datetime
from enum import (Enum, IntEnum, EnumMeta)
import inspect
import numbers
import math
import dataclasses
from dataclasses import (dataclass, KW_ONLY, MISSING, field)
import sys
import time, datetime
import traceback
import typing
import types
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
from core import quantities as scq
from . import xmlutils
from . import strutils
from .prog import safeWrapper, is_hashable, is_type_or_subclass, ImmutableDescriptor

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
                                    
GENOTYPES = ["NA", "wt", "het", "hom", "+/+", "+/-", "-/-"]


RELATIVE_TOLERANCE = 1e-4
ABSOLUTE_TOLERANCE = 1e-4
EQUAL_NAN = True

def default_value(x:type):
    if not isinstance(x, type):
        return x
    try:
        if x == datetime.datetime:
            return datetime.datetime.now()
        elif x == datetime.date:
            return datetime.date.today()
        
        elif is_enum(x):
            if isinstance(x, TypeEnum):
                return x.default()
            else:
                mk = list(x.__members__.keys())
                return x[mk[0]]
        else:
            ret = x()
    except:
        return None

def is_enum(x):
    if not isinstance(x, type):
        return False
    
    return Enum in inspect.getmro(x)

def is_enum_value(x):
    if isinstance(x, type):
        return False
    
    return isinstance(type(x), EnumMeta)

def is_routine(x):
    """ Similar to is_callable but excludes classes with __call__ method.
    """
    
    function_types = (types.FunctionType, types.LambdaType, types.MethodType,
                      types.BuiltinFunctionType, types.BuiltinMethodType,
                      types.WrapperDescriptorType, types.MethodWrapperType,
                      types.CoroutineType, types.MethodDescriptorType,
                      types.ClassMethodDescriptorType)
    
    return isinstance(x, function_types)
    

def is_callable(x):
    """Brief reminder:
    An object is callable if it is:

    • a Python function (including created by a lambda expression) ↔ inspect.isfunction
        
        e.g., `def f(x): ... ` in a module

    • a bound method written in Python ↔ inspect.ismethod

        e.g. `def f(self, ...): ... ` inside a class definition block

    • a generator function ↔ inspect.isgeneratorfunction

        a function which returns a generator iterator by way of `yield` 
            instead of `return`

        e.f. `def f(x): ... yield x+1`

    • a coroutine function ↔ inspect.iscoroutinefunction

        a function which returns a coroutine object; these are defined with
        `async def` statement

    • an asynchronous generator ↔ inspect.isasyncgenfunction

        a function which returns an asynchronous generator iterator; these are
        defined with `async def` statement and use `yield` (not `return`)

    • a builtin function ↔ inspect.isbuiltin

        a built-in function or bound built-in method

    • a routine: user-defined or built-in function or method

    • an instance of a class that has a __call__ method

    """
    ret = is_routine(x)
    
    if not ret:
        ret = callable(x)
        # ret = inspect.ismethod(getattr(x, "__call__", None))
    
    return ret

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
    """Returns True when all elements in the sequence have the same type
    Can also be used with sets after conversion to list.
    """
    ret = isinstance(s, collections.abc.Sequence) 

    if ret:
        ret &= all(isinstance(v, type(s[0])) for v in s[1:])

    return ret

def is_convertible_to_numpy_array(s):
    ret = is_uniform_sequence(s)
    if ret:
        try:
            a = np.array(s)
        except:
            traceback.print_exc()
            ret = False
            
    return ret

def is_uniform_collection(obj):
    """Shorthand to apply is_uniform_sequence() to what can be converted to list.
    For dict collections, it applied to obj.values()
    """
    try:
        if isinstance(obj, dict):
            s = list(obj.values())
        else:
            s = list(obj)
            
        return is_uniform_sequence(s)
    except:
        return False
    
def sequence_element_type(s):
    from utilities import unique
    return unique((type(e) for e in s))
    
    
def array_slice(data:np.ndarray, slicing:(dict, type(None))):
    """Dynamic slicing of nD arrays and introducing new axis in the array.
    
    Parameters:
    ===========
    data: the array
    
    slicing: a dict with axis index ↦ axis coordinate, specifying the axis (or 
            dimension) from which a single coordinate needs to be retrieved. 
            For the array axes (or dimensions) that are excluded from the `slicing`,
            the entire extent of the array data alog those axes will be used.
    
            
        • The keys can be:
            ∘ a vigra.AxisInfo (when data is a VigraArray)
            ∘ an int on the half-open interval [ 0, data.ndim )
        
        • The coordinate can be:
            ∘ an int on the half-open interval [ 0, data.shape[key] )
            
    Examples:
    =========
    
    1) Let x a 2D array of shape (400, 215) (i.e. a matrix with 400 columns and 255 rows).
    
    To create an indexing tuple to access the array values at coordinate 0 on the
    second axis (effectively, the first "column", having 400 data points):
    
    ndx = array_slice(x, {1:0}) # ⇒ (slice(0, 400, None), 0)
    
    `ndx` can then be used to slice the array:
    
    x_slice = x[ndx] # ⇒ array with shape (400,)
    
    2) Indexing the array in Example 1 along the fist axis to obtain the first
    row (215 data points)
    
    ndx = array_slice(x, {0:0})
    
    x[ndx] # ⇒ array with shape (215,0)
    
    Returns
    =======
    
    An indexing tuple suitable to use for advanced numpy indexing.
    
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

def is_unavailable(x):
    return x is pd.NA or x is np.nan or x is math.nan or x is dataclasses.MISSING
    
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
    def default(cls):
        """Aways returns the first member of the enum class
        """
        names = list(cls.names())
        return cls[names[0]]
    
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
        
    
def inspect_members(obj, predicate=None):
    skips = ("__class__", "__module__", "__name__", "__qualname__", "__func__",
             "__self__", "__code__", "__defaults__", "__kwdefaults__", 
             "__globals__", "__builtins__", "__annotations__", "__doc__",
             "__dict__", "__delattr__", "__dir__")
    
    specials = ("fb_", "f_", "co_", "gi_", "cr_", "__")
    
    names = tuple(n for n in dir(obj) if n not in skips and all(not n.startswith(s) for s in specials))
    
    mb = tuple((n, getattr(obj, n, None)) for n in names)
    
    if inspect.isfunction(predicate):
        mb = tuple(filter(lambda x: predicate(x[1]), mb))
        
    return dict(mb)
                   
@dataclass
class Episode:
    name:str = ""
    _:KW_ONLY
    begin:datetime.datetime = datetime.datetime.now()
    end:datetime.datetime = datetime.datetime.now()
    beginFrame:int = 0
    endFrame:int = 1
    
            
@dataclass
class Schedule:
    name:str = ""
    _:KW_ONLY
    episodes:typing.Sequence[Episode] = field(default_factory = lambda : [Episode()])
    
    @singledispatchmethod
    def episode(self, ndx):
        pass
    
    @episode.register(int)
    def _(self, ndx:int):
        if ndx < 0 or ndx >= len(self.episodes):
            raise IndexError(f"Invalid episode index {ndx} for {len(self.episodes)}")
        
        return self.episodes[ndx]
    
    @episode.register(str)
    def _(self, name:str):
        episodes = [e for e in self.episodes if e.name == name]
        if len(episodes):
            return episodes[0]
        else:
            raise IndexError(f"Episode name {name} does not exist")
        
    def episodeNames(self):
        return [e.name for e in self.episodes]
    
    def addEpisode(self, episode:Episode):
        if episode not in self.episodes:
            self.episodes.append(episode)
            
    def addEpisodes(self, episodes:typing.Sequence[Episode]):
        self.episodes.extend([e for e in episodes if e not in self.episodes])
        
    def removeEpisode(self, episode):
        if episode in self.episodes:
            self.episodes.remove(episode)
    
class ProcedureType(TypeEnum):
    null = 0
    treatment = 1
    surgery = 2
    behaviour = 4 # to include navigation in real or virtual environment, rotarod, inclined plane, licking etc # TODO to refine
    biopsy = 8
    tagging = 16
    mating = 128
    cull = 255
    
class AdministrationRoute(TypeEnum):
    null = 0
    intraperitoneal = 1
    intramuscular = 2
    intravenous = 4
    intraarterial = 8
    intracerebral = 16
    intraventricular = 32
    intracerebroventricular = intracerebral | intraventricular # 48
    intracardiac = 64
    subcutaneous = 128
    transcutaneous = 256
    peros = 512 # e.g. gavage
    inhalation = 1024
    intranasal = 2048
    intraorbital = 4096
    food_water = 8192
    other = 8192
    
    # aliases
    ip = intraperitoneal
    iv = intravenous
    ia = intraarterial
    im = intramuscular
    icb = intracerebral
    icv = intracerebroventricular
    ic = intracardiac
    ins = intranasal # 'in' is a reserved keyword
    ih = inhalation
    io = intraorbital
    sc = subcutaneous
    tc = transcutaneous
    gavage = peros
    
@dataclass
class Procedure:
    name:str = ""
    _:KW_ONLY
    procedureType:ProcedureType = ProcedureType.null
    schedule:Schedule = Schedule()
    
@dataclass
class TreatmentProcedure(Procedure):
    _:KW_ONLY
    dose:pq.Quantity = field(default_factory=lambda : math.nan * pq.g)
    route:AdministrationRoute = AdministrationRoute.null
    procedureType:ImmutableDescriptor = ImmutableDescriptor(default=ProcedureType.treatment)
    
    def __post_init__(self):
        super().__init__(name=self.name, episodes = self.episodes)
        # super().__init__(name=self.name, procedureType = ProcedureType.treatment, episodes = self.episodes)
        
        unitFamily = scq.getUnitFamily(self.dose)
    
        acceptableUnitFamilies = ("Mass", "Volume", "Substance", "Concentration", "Flow")
    
        if unitFamily not in acceptableUnitFamilies:
            raise ValueError(f"'dose' has wrong units; the units should be units of {acceptableUnitFamilies}")
        
