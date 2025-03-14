# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

''' Utilities for generic and numpy array-based data types such as quantities
Changelog:
2021-01-06 14:35:30 gained module-level constants:
RELATIVE_TOLERANCE
ABSOLUTE_TOLERANCE
EQUALS_NAN

    
'''

from __future__ import print_function

#### BEGIN core python modules
from abc import ABC, ABCMeta, abstractmethod
import collections 
from collections import deque, namedtuple
from functools import (singledispatch, singledispatchmethod)
import itertools
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
import h5py
import treelib
from copy import (deepcopy, copy,)

#### END core python modules

#### BEGIN 3rd party modules
from qtpy import (QtGui, QtCore, QtWidgets,)
import numpy as np
from numpy import ndarray
import numpy.matlib as mlib
import pandas as pd
import quantities as pq
from core.vigra_patches import vigra
import neo
from neo.core import (baseneo, basesignal, container,)
from neo.core.dataobject import (DataObject, ArrayDict,)

          
#### END 3rd party modules

#### BEGIN pict.core.modules
from core import quantities as scq
from core import xmlutils
from core import strutils
from core.prog import (safeWrapper, is_hashable, is_type_or_subclass, 
                       ImmutableDescriptor, scipywarn, NoData, printStyled)
from core.datazone import DataZone
from core.datasignal import (_new_DataSignal, _new_IrregularlySampledDataSignal, DataSignal, IrregularlySampledDataSignal)
from core import bgbridge
from core.bgbridge import (BGStructureDescriptor, BrainGlobeAtlas)
from core import taxonbridge
from core.taxonbridge import(Taxon, TaxonDescriptor)

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

# NOTE: 2024-07-28 15:46:49 
# these are utterly generic; almost surely you'd want to write your own
# e.g. Cacna1c+/-, etc...
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
    r""" Similar to is_callable but excludes classes with __call__ method.
    """
    
    function_types = (types.FunctionType, types.LambdaType, types.MethodType,
                      types.BuiltinFunctionType, types.BuiltinMethodType,
                      types.WrapperDescriptorType, types.MethodWrapperType,
                      types.CoroutineType, types.MethodDescriptorType,
                      types.ClassMethodDescriptorType)
    
    return isinstance(x, function_types)
    

def is_callable(x):
    r"""Brief reminder:
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
    r"""Returns True if x is a numpy array encapsulating a vector.
    
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
    r"""Returns True if x is a numpy arrtay encapsulating a column vector.
    
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
    r"""Returns True if x is a numpy array encapsulating a column vector.
    
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
    r"""Returns True when all elements in the sequence have the same type
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
    r"""Shorthand to apply is_uniform_sequence() to what can be converted to list.
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
    from core.utilities import unique
    return unique(tuple(type(e) for e in s))



def check_type(t:typing.Union[type, typing.Sequence[type], typing.Set[type]], 
                     ref:typing.Union[type, typing.Sequence[type], typing.Set[type], typing._UnionGenericAlias],
                     use_mro:bool=False,
                     use_ref_mro:bool=False,
                     check_elements:bool=False,
                     check_keys:bool=False) -> bool:
    r"""Checks a type in 't' against a reference type in 'ref'.
    
    't': a type, or a collection of types (i.e., tuple, list or set)
    
    'ref': a type, or a collection of types - the 'reference'
    
    Supported collections of types are tuple, list, and set.
    
    When 't' is a type, the function verifies if 't' is the same as 'ref' (when 
    'ref' is a type) or is in 'ref' (when 'ref' is a collection of types)
    
    When 't' is a collection of types (see above) the function verifies that any
    of the members in 't' are 'ref' (or in 'ref').
    
    WARNING: currently this does not check element types (or key/value types)
    in collections.
    
    Named parameters:
    -----------------
    use_mro: bool, optional, default is False; when True, the comparison extends
        to the type hierarchy of objects in 't'
    
    use_ref_mro: bool, optional, default is False; when True, the comparison extends
        to the type hierarchy of objects in 'ref'
    
    check_elements:bool - Not used
    check_keys:bool - Not used
    
    
    """
    # NOTE: 2024-01-07 00:12:32
    # the following five variables are not currently used; 
    # defined here for future code to check types nested in collections
    t_keys = t_vals = t_elems = None
    ref_keys = ref_vals = ref_elems = None
    
    if isinstance(t, type):
        # single type
        t_set = set(inspect.getmro(t)) if use_mro else {t}
        
    elif isinstance(t, (tuple, list, set) and all(isinstance(t_, type) for t_ in t)):
        # sequence of types
        t_set = set(itertools.chain_from_iterable([inspect.getmro(t_) for t_ in t])) if use_mro else {t}
        
    else:
        # any object OTHER THAN a type
        if issubclass(type(t), dict):
            # cache key/value types - not currently used
            # TODO 2024-01-06 23:54:37 
            # write code to check these
            t_keys, t_vals = tuple(map(lambda x: set(x), zip(*((type(k), type(v)) for k,v in t.items))))
            
        elif issubclass(type(t), (list, tuple, set, collections.deque)):
            # cache element types
            # TODO 2024-01-06 23:55:01
            # write code to check element types
            t_elems = set(type(v) for v in t)
            
        t = type(t)
        t_set = set(inspect.getmro(t)) if use_mro else {t}
        
    # else:
    #     raise TypeError(f"'t': Expecting a type, or a list, set, or tuple of types; instead, got {type(t).__name__}")
        
    if isinstance(ref, type):
        ref_set = set(inspect.getmro(ref)) if use_ref_mro else {ref}
        
    elif isinstance(ref, (list, tuple, set)):
        return any(check_types(t, r_) for r_ in ref)
        # ref = set(itertools.chain.from_iterable([inspect.getmro(t_) for t_ in ref])) if use_ref_mro else {ref}
        
    elif type(ref).__module__ == "typing":
        ref_origin = typing.get_origin(ref)
        ref_args = typing.get_args(ref)
        if ref_origin == typing.Union:
            if len(ref_args) == 0:
                raise RuntimeError(f"Cannot resolve {ref} with type arguments {ref_args}")
            
            ref_set = set(itertools.chain.from_iterable(map(lambda x: inspect.getmro(typing.get_origin(x) or x), ref_args))) if use_ref_mro else set(map(lambda x: typing.get_origin(x) or x, ref_args))
            
        else:
            ref_set = {inspect.getmro(ref_origin)} if use_ref_mro else {ref_origin}
            
            if len(ref_args):
                if issubclass(ref_origin, (dict, collections.abc.Mapping)):
                    if len(ref_args) != 2:
                        raise RuntimeError(f"Cannot resolve {ref} with type arguments {ref_args}")
                    ref_keys, ref_vals = ref_args
                    ref_keys = {ref_keys}
                    ref_vals = {ref_vals}
                    
                if issubclass(ref_origin (list, tuple, set, frozentset, collections.deque, collections.abc.Sequence)):
                    if len(ref_args) > 1:
                        raise RuntimeError(f"Cannot resolve {ref} with type arguments {ref_args}")
                    
                    if typing.get_origin(ref_args[0]) == typing.Union:
                        ref_elems = set(typing.get_args(ref_args[0]))
                    else:
                        ref_elems = set(ref_args)
                        
                # TODO 2024-01-07 00:12:02
                # unravel typing types
                        
        
    else:
        raise TypeError(f"'ref': Expecting a type, or a list, set, or tuple of types; instead, got {type(ref).__name__}")
    
    # print(f"final t: {t}")
    # print(f"final ref: {ref}")
    
    return len(t_set & ref_set) > 0 or any(issubclass(v, tuple(ref_set)) for v in t_set)

def enum2str(etype:Enum) -> str:
    r"""Returns the symbol (NOT the value) of the enum type"""
    enumItems = list(filter(lambda x: x[1] == etype, 
                            inspect.getmembers_static(etype, predicate = lambda x: isinstance(x, IntEnum))))
    
    if len(enumItems):
        enumNames = list(map(lambda x: x[0], enumItems))
        if len(enumNames):
            return enumNames[0]
    
    return str()

def enums2str(etypes: typing.Sequence[Enum]) -> list[str]:
    r"""Like enum2str but does a single pass throughn the sequence"""
    if len(etypes) == 0:
        return list()
    
    if len(etypes) == 1:
        return enum2str(etypes[1])
    
    assert all(isinstance(e, type(etypes[0])) for e in etypes[1:]), f"All enum types in the sequence must be of the same type: {type(etypes[0]).__name__}"
    
    enumItems = list(filter(lambda x: x[1] in etypes, 
                            inspect.getmembers_static(etypes[0], predicate = lambda x: isinstance(x, IntEnum))))
    if len(enumItems):
        return list(map(lambda x: x[0], enumItems))
    
    return list()
        

def type2str(t:type) -> str:
    if not isinstance(t, type):
        # print(f"{t} not a type")
        # if type(t).__name__ in typing.__dict__:
        if type(t).__module__ == "typing":
            type_origin = typing.get_origin(t)
            # print(f"type_origin: {type_origin}")
            t_args = typing.get_args(t)
            # print(f"t_args: {t_args}")
            if type_origin is None:
                return t.__name__
            if len(t_args):
                type_args = ", ".join([f"{type2str(_t)}" for _t in t_args])
                return f"{type_origin.__name__}[{type_args}]"
            return type_origin.__name__
            
        raise TypeError(f"Expecting a type; instead, got {type(t).__name__}")
    
    # if t.__name__ in typing.__dict__:
    if t.__module__ == "typing":
        # print(f"{t} is a type")
        type_origin = typing.get_origin(t)
        # print(f"type_origin: {type_origin}")
        t_args = typing.get_args(t)
        # print(f"t_args: {t_args}")
        if type_origin is None:
            return t.__name__
        if len(t_args):
            type_args = ", ".join([f"{type2str(_t)}" for _t in t_args])
            return f"{type_origin.__name__}[{type_args}]"
        return type_origin.__name__
    
    return t.__name__
    
def array_slice(data:np.ndarray, slicing:(dict, type(None))):
    r"""Dynamic slicing of nD arrays and introducing new axis in the array.
    
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
    r"""Determine whether the argument has a string or character datatype, when
    converted to a NumPy array.
    
    String or character (including unicode) have dtype.kind of "S" or "U"
    
    """
    return np.asarray(array).dtype.kind in NUMPY_STRING_KINDS

def is_numeric_string(array):
    r"""Determines if the argument is a string array that can be parsed as numeric.
    """
    if isinstance(array, str):
        array = [array]
        
    return is_string(array) and not np.isnan(np.genfromtxt(array)).any()

def is_numeric(array):
    r"""Determine whether the argument has a numeric datatype, when
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
    r""""""
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
    
class DoseDescriptor:
    def __init__(self, *, default:typing.Optional[pq.Quantity]=None):
        if isinstance(default, pq.Quantity):
            if not scq.checkDosageUnits(default):
                raise ValueError(f"Expecting dosage units; instead, got {default.units}")
            
        elif default is not None:
            raise TypeError(f"Expecting a scalar dosage Quantity or None; instead, got {type(default).__name__}")
        
        self._default = default
        
    def __set_name__(self, obj:object, name:str):
        if len(name.strip()) == 0:
            raise ValueError("Cannot accept an empty name")
        self._name = "_"+name
        
    def __get__(self, obj:object, objtype:type) -> object:
        if obj is None:
            return self._default
        return getattr(obj, self._name, self._default)
    
    def __set__(self, obj:object, value:typing.Optional[pq.Quantity] = None):
        if isinstance(value, pq.Quantity):
            if not scq.checkDosageUnits(value):
                raise ValueError(f"Expecting dosage units; instead got {value.units}")
            
        elif value is not None:
            raise TypeError(f"Expecting a scalar dosage Quantity, or None; instead got {type(value).__name__}")

        setattr(obj, self._name, value)
        
            
@dataclass
class ScipyenDataclass:
    r"""An 'enhanced' dataclass, ancestor of Scipyen data classes.

    WARNING: to derive (i.e. create a subclass) from ScipyenDataclass follow the 
    steps below:

    1) use the '@dataclass' decorator
    2) define the class attribute '__match_args__' of the subclass, to include 
        the elements of the parent class attribute '__match_args__'
    
    This is because inheriting from a dataclass is not as straightforward as it 
    is for general python classes; specifically, the '__match_args__' is set up
    by the decorator code unless defined in the subclass, yet we use it for 
    reconstituting the instance of the subclass from HDF5 data structure.

    NOTE: passing this through a set constructor ensures the fields are uniquely
    contained in __match_args__
    
    For example (pseudo-code, not supposed to run):
    
    @dataclass
    class MyClass(ScipyenDataclass):
        field1 …
        field2 …
        __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("field1", "field2")))
    
        ⋮
    
        <other code in your subclass definition>
    
    And, one step further in the inheritance chain (again pseudo-code, it won't run):
    
    @dataclass
    class MySubclass(MyClass):
        field_A …
        field_B …
        _:KW_ONLY
        field_C
        
        __match_args__ = tuple(set(MyClass.__match_args__ + ("field_A", "field_B", "field_C")))
    
        ⋮
        
        <other code in your subclass definition>
    
    So, the two new classes will show:
        
    MyClass.__match_args__
        -> ("name", "description", "field1", "field2")
    
    MySubClass.__match_args__
        -> ("name", "description", "field1", "field2", "field_A", "field_B", "field_C")
    
    
    Replicate this mechanism for sub-subclasses.
    
    """
    # BUG: 2024-12-15 12:33:55 FIXME
    # __match_args__ in subclasses must reflect superclass and keyword args
    name:str = dataclasses.field(default_factory=str)
    description: str = dataclasses.field(default_factory=str)
    
    def diff(self, other, showValues:bool=False) -> dict | tuple:
        # print(f"{self.__class__.__name__}.diff: ")
        from core.utilities import safe_identity_test
            
        if other.__class__ != self.__class__:
            raise TypeError(f"Expecting an object of type {self.__class__.__name__}; instead, got {type(other).__name__}")
        
        
        fields = tuple(map(lambda f: (f.name, getattr(self, f.name), getattr(other, f.name)), dataclasses.fields(self.__class__)))
        
        # test_eq = lambda x: ( pd.isna(x[0]) and pd.isna(x[1])) or \
        #     (math.isnan(x[0]) and math.isnan(x[1])) or (math.isinf(x[0]) and math.isinf(x[1])) or\
        #         ( np.all(x[0]==x[1]) if any(map(lambda x_: isinstance(x_, np.ndarray), x)) else (x[0] == x[1]) )
        
        diff_fields = tuple(filter(lambda f: type(f[1]) != type(f[2]) or not safe_identity_test(f[1], f[2]), fields))
        
        # diff_fields = tuple(filter(lambda f: np.all(getattr(self, f.name) != getattr(other, f.name)), dataclasses.fields(self.__class__)))
        
        if showValues:
            # return dict(map(lambda f: (f.name, (getattr(self, f.name), getattr(other, f.name))), diff_fields))
            return dict(map(lambda f: (f[0], (f[1], f[2])), diff_fields))
        
        return tuple(map(lambda f: f[0], diff_fields))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        
        return len(self.diff(other)) == 0
        
    def toHDF5(self, group:h5py.Group, name:str, oname:str, 
                       compression:str, chunks:bool, track_order:bool,
                       entity_cache:dict) -> h5py.Group:
        # BUG: 2024-12-12 00:43:33  FIXME
        # cannot store all fields as entity attributes, because subclasses of 
        # ScipyenDataclass MAY have composite types which cannot be encoded in json.
        #
        # Therefore: TODO: convert to dict using asdict then store it as if is was a dict!
        # TODO: adapt fromHDF5 to reflect this!
        
        # see examples in h5io.objectToEntity
        
        from iolib import h5io
        
        # print(f"\n\n### BEGIN {self.__class__.__name__}.toHDF5")
        
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            # print(f"{self.__class__.__name__}.toHDF5 found entity {cached_entity}")
            # print(f"### END {self.__class__.__name__}.toHDF5 \n\n")
            return cached_entity
        
        if isinstance(name, str) and len(name.strip()):
            target_name = name
            
        # calling asDict recursively converts all nested dataclass instances to
        # a dict -- effectively "peeling out" the dataclass
        data = dataclasses.asdict(self)
        
        # therefore, I need to inspect which of the fields ARE in fact, instances
        # of dataclass
        dataclass_fields = list(filter(lambda f: dataclasses.is_dataclass(getattr(self, f.name)), dataclasses.fields(self)))
        
        # then assign these back into the dictionary from above:
        data.update(dict(map(lambda f: (f.name, getattr(self, f.name)), dataclass_fields)))

        # NOTE: 2024-12-12 15:41:25
        # instead of creating a nested hf5 group, just populate this one with
        # the items from the updated data dict above
        entity = group.create_group(target_name, track_order = track_order)
        entity.attrs.update(obj_attrs)
        
        for name, value in data.items():
            cached_entity = h5io.getCachedEntity(entity_cache, value)
            if isinstance(cached_entity, (h5py.Group, h5py.Dataset)):
                entity[name] = cached_entity
            else:
                element_entity = h5io.toHDF5(value, entity, name=name,
                                             compression=compression,
                                             chunks=chunks,
                                             track_order=track_order,
                                             entity_cache=entity_cache)
                # if name == "dose":
                #     print(f"{self.__class__.__name__}.toHDF5 created entity {element_entity} for field '{name}' ({type(value).__name__})\n")
                
        # print(f"### END {self.__class__.__name__}.toHDF5 \n\n")
        return entity
        
    @classmethod
    def fromHDF5(cls, entity:h5py.Group, 
                attrs:typing.Optional[dict] = None, cache:dict = {}):
        from iolib import h5io
        
        # print(f"\n\n### BEGIN {cls.__name__}.fromHDF5 ")
        
        if entity in cache:
            val = cache[entity]
            # print(f"{cls.__name__}.fromHDF5 got cached entity {type(val).__name__}")
            return val
        
        attrs = h5io.attrs2dict(entity.attrs)
        
        # print(f"{cls.__name__}.fromHDF5: attrs = {attrs}")
        
        # assert attrs["python_class"] == str(cls).strip("<").strip(">").strip("class").strip()[1:-1], \
        assert attrs["python_class"] == cls, f"Object has unexpected class: {attrs['python_class']}"
        
        attrs_as_entities = [a for a in cls.__match_args__ if a not in attrs]
        
        kwargs = dict()
        
        for a in attrs_as_entities:
            if a in entity.keys():
                kwargs[a] = h5io.fromHDF5(entity[a], cache=cache)
                # print(f"{cls.__name__}.fromHDF5: got field '{a}' with type: {type(kwargs[a]).__name__}\n")
                    
        # print(f"### END {cls.__name__}.fromHDF5 \n\n")
        return cls(**kwargs)
    
    
TE = typing.TypeVar("TE", bound="TypeEnum")
class TypeEnum(IntEnum):
    r"""Common ancestor for enum types used in Scipyen
    """
    
    @classmethod
    def default(cls) -> type[TE]:
        r"""Aways returns the first member of the enum class
        """
        names = list(cls.names())
        return cls[names[0]]
    
    @classmethod
    def names(cls) -> typing.Generator[str, None, None]:
        r"""Iterate through the names in TypeEnum enumeration.
        """
        for t in cls:
            yield t.name
    
    @classmethod
    def values(cls) -> typing.Generator[int, None, None]:
        r"""Iterate through the int values of TypeEnum enumeration.
        """
        for t in cls:
            yield t.value
        
    @classmethod
    def types(cls) -> typing.Generator[type[TE], None, None]:
        r"""Iterate through the elements of TypeEnum enumeration.
        Useful to quickly remember what the members of this enum are (with their
        names and values).
        
        A TypeEnum enum member is by definition a member 
        of TypeEnum enum and an instance of TypeEnum.
        
        """
        for t in cls:
            yield t
            
    @classmethod
    def namevalue(cls, name:str) -> int:
        r"""Return the value (int) corresponding to a given name;
        WARNING If name is not a valid TypeEnum name returns -1
        """
        if name in cls.names():
            return getattr(cls, name).value
        
        return -1
    
    @classmethod
    def stringToType(cls, name:str) -> int:
        r"""Return the value (int) corresponding to a given name;
        WARNING If name is not a valid TypeEnum name returns -1
        """
        return cls.namevalue(name)
    
    @classmethod
    def __contains__(cls, value) -> bool:
        if isinstance(value, cls):
            return value in cls.types()
        
        elif isinstance(value, int):
            return value in cls.values()
        
        elif isinstance(value, str):
            return value in cls.names()
        
        else:
            return False

    @classmethod
    def type(cls, t:typing.Union[str, int]) -> type[TE]:
        r"""Returns the enum type corresponding to `t`, where
        `t` can be:
        • str: the name / symbol associated with the type in the enum
        • int: the value associated with the type in the enum
        
        
        """
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
    def strand(cls, name1:str, name2:str) -> int:
        r""" Emulates '&' operator for type names 'name1' and 'name2'.
        If neither arguments are valid names returns 0
        """
        if any([n not in cls.names() for n in [name1, name2]]):
            return 0
        
        val1 = cls.namevalue(name1)
        val2 = cls.namevalue(name2)
        
        return val1 & val2
    
    @classmethod
    def is_primitive_type(cls, t) -> bool:
        r"""Checks if 't' is a primitive type in this types enumeration.
        
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)
        
            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)
        
        """
        return len(cls.primitive_component_types(t)) == 0
    
    @classmethod
    def is_derived_type(cls, t) -> bool:
        r"""Checks if 't' is a compound type (i.e. derived from other type enums)
        
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)
        
            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)
        
        """
        return len(cls.component_types(t)) > 0
        #return len(cls.primitive_component_types(t)) > 0
        
    @classmethod
    def is_composite_type(cls, t) -> bool:
        r"""Alias of TypeEnum.is_derived_type()
        
        Parameters:
        -----------
        t: int, str, TypeEnum (or subclass)
        
            When an int or a str, the value must be a valid one (i.e., found in
            TypeEnum.values() or TypeEnum.names(), respectively)
        
        """
        return cls.is_derived_type(t)
    
    @classmethod
    def primitive_component_types(cls, t) -> typing.List[TE]:
        r""" Returns a list of primitive TypeEnum objects that compose 't'.
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
    def component_types(cls, t) -> typing.List[TE]:
        r""" Returns a list of TypeEnum objects that compose 't'.
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
    def derived_types(cls, t) -> typing.List[TE]:
        r""" Returns the composite TypeEnum objects where 't' participates.
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
        r"""Return True if this TypeEnum object is a composite (i.e., derived) type.
        """
        return self.is_derived_type(self)
    
    def is_composite(self) -> bool:
        r"""Return True if this TypeEnum object is a composite (i.e., derived) type.
        """
        return self.is_derived()
    
    def is_primitive(self) -> bool:
        return self.is_primitive_type(self)
    
    def primitives(self) -> typing.List[TE]:
        r"""Returns a list of primitive types used to generate this type.
        
        Compound types are generated from primitive types through the logical
        OR operator (bitwise OR).
        
        Returns an empty list of this is a primitive type.
        """
        return self.primitive_component_types(self)
    
    def components(self) -> typing.List[TE]:
        r"""Returns a list of components for this TypeEnum object.
        
        Compound types are generated from primitive types through the logical
        OR operator (bitwise OR).
        
        If this TypeEnum object is a primitive returns an empty list
        """
        return self.component_types(self)
    
    def includes(self, t) -> bool:
        r"""Returns True if 't' is a component of this TypeEnum object.
        
        't' may be a primitive or a composite type.
        
        Always returns False when this is a primitive.
        """
        t = self.type(t)
            
        return t in self.components()
    
    def is_primitive_of(self, t) -> bool:
        r"""Returns True if this TypeEnum object is a primitive of 't'.
        
        Always returns False when this TypeEnum object is a composite (i.e., 
        even if it is a component of 't').
        """
        t = self.type(t)
            
        return self in t.primitives()
    
    def is_component_of(self, t) -> bool:
        r"""Returns True if this TypeEnum object is a component of 't'.
        """
        t = self.type(t)
        
        return self in t.components()
    
    def nameand(self, name:str) -> TE:
        r""" Applies strand() to the name of this object and the argument.
        """
        return self.strand(self.name, name)
    
class CellCompartmentType(TypeEnum):
    r"""Follows SWC/CNIC specification augmented with 'spine', 'nucleus', 'nucleolus'. 
    See http://www.neuronland.org/NLMorphologyConverter/MorphologyFormats/SWC/Spec.html
    """
    undefined = 0
    cell = undefined
    soma = 1
    axon = 2
    dendrite = 3 # basal dendrite
    apical_dendrite = 4
    fork_point = 5
    end_point = 6
    spine = 7
    basal_dendrite_spine = dendrite | spine # = 10
    apical_dendrite_spine = apical_dendrite | spine # = 11
    nucleus = 12
    nucleolus = 13
    
class BioSourceType(TypeEnum):
    exvivo      = 1
    invitro     = 2
    insilico    = 4
    monolayer   = 8     # e.g. "primary" culture = invitro | monolayer = 10
    tissue      = 16    # e.g. acute brain slice = exvivo | tissue = 17 
                        # e.g. "organotypic" slice culture = invitro | tissue  = 18
    assembloid  = 32    # e.g. "organoid" = invitro | assembloid = 34
    
    invivo      = 64
    
    organism    = 128   
    
class ProcedureType(TypeEnum):
    null = 0
    mating = 1
    treatment = 2
    behaviour = 4 # includes navigation in real or virtual environment, rotarod, inclined plane, licking etc # TODO to refine
    surgery = 8
    biopsy = 16
    postop = 32
    tagging = 64
    weaning = 128
    cull = 256
    other = 512
    
class OrganismStage(TypeEnum):
    undefined   = 0
    zygote      = 1
    morula      = 2
    blastula    = 4
    gastrula    = 8
    embryo      = zygote | morula | blastula | gastrula # = 15
    foetal      = 16
    prenatal = embryo | foetal # = 31
    larva       = 32
    pup         = larva
    prepubertal = larva
    preweaning  = prepubertal
    adolescent  = 33
    adult       = 34
    juvenile    = larva | adolescent # = 65
    postnatal   = larva | adolescent | adult # = 99
    
class AdministrationRoute(TypeEnum):
    null = 0
    bath = 1 # relates to ex vivo tissue slices
    puff = 2 # relates to ex vivo tissue slices — e.g. picospritzer, pressurized micropipette, etc
    intraperitoneal = 4
    intramuscular = 8
    intravenous = 16
    intraarterial = 32
    intracerebral = 64
    intraventricular = 128 # can be in the heart!
    intracerebroventricular = intracerebral | intraventricular # 192
    intracardiac = 256
    intracardioventricular = intracardiac | intraventricular # 384
    subcutaneous = 512
    transcutaneous = 1024
    peros = 2048 # e.g. gavage
    inhalation = 4096
    intranasal = 8192
    intraorbital = 16384
    food_water = 32768
    other = 65536
    
    # aliases
    ip = intraperitoneal
    iv = intravenous
    ia = intraarterial
    im = intramuscular
    ic = intracerebral
    icv = intracerebroventricular
    icd = intracardiac
    icdv = intracardioventricular
    ins = intranasal # 'in' is a reserved Python keyword
    inh = inhalation
    io = intraorbital
    sc = subcutaneous
    tc = transcutaneous
    gavage = peros
    oral = peros
    custom = other
    bulk = bath
    
    
def inspect_members(obj, predicate=None):
    skips = ("__class__", "__module__", "__name__", "__qualname__", "__func__",
             "__self__", "__code__", "__defaults__", "__kwdefaults__", 
             "__globals__", "__builtins__", "__annotations__", "__doc__",
             "__dict__", "__delattr__", "__dir__")
    
    specials = ("fb_", "f_", "co_", "gi_", "cr_", "__")
    
    names = tuple(n for n in dir(obj) if n not in skips and all(not n.startswith(s) for s in specials))
    
    mbi = tuple((k, n, inspect.getattr_static(obj, n, None)) for k,n in enumerate(names))
    
    mb = list()
    
    for k, mbi_name, mbi_obj in mbi:
        try:
            v = getattr(obj, mbi_name)
        except:
            # print(f"Cannot parse member {k}: {mbi_name} which is a {type(mbi_obj)}")
            # traceback.print_exc()
            v = mbi_obj
            
        mb.append((mbi_name, v))
        
    
    # mb = tuple((n, getattr(obj, n, None)) for n in names)
    
    if inspect.isfunction(predicate):
        mb = tuple(filter(lambda x: predicate(x[1]), mb))
        
    return dict(mb)

@dataclass
class CellCompartment(ScipyenDataclass):
    # name:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    type:CellCompartmentType = CellCompartmentType.undefined
    id:int = 0
    
    __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("type", "id")))

    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class Biometrics(ScipyenDataclass):
    genotype:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # genotype of the source - keep it simple
    #
    # NOTE: avoid strings like (+/-, TSNeo/-, etc) as they don't play well when
    # importing data in, say, R
    # These are entirely conventional, and, within the same line of genetic 
    # animal model they would have a well-defined meaning
    #

    sex:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # ID of source sex (where appropriate); one of "f", "m", "na" (case-insensitive)
    #
    
    age:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # animal's age (more generaly the age of the biological source)- almost 
    # free-form string, see NOTE for animal ID - keep it
    #   simple, yet meaningful, and indicate units (e.g. 3_mo, or 20_d, or 1_yr)
    #
    # NOTE: these are simply for a quick information; in the future Scipyen will
    # provide a more standardized way to store this information, hopefully more
    # suitable to some sort of database management
    
    postnatal:bool=True
    
    weight:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA) 
    height:typing.Union[pq.Quantity, type(pd.NA)] = dataclasses.field(default=pd.NA)
    
    __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("genotype", "sex",
                                                                  "age", "postnatal",
                                                                  "weight", "height")))
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class Organism(ScipyenDataclass):
    taxon:TaxonDescriptor = TaxonDescriptor(default="Rattus")
    subspecies:str = "Sprague Dawley"
    strain:str = ""
    stage:OrganismStage = dataclasses.field(default=OrganismStage.postnatal)
    biometrics:Biometrics = dataclasses.field(default_factory=Biometrics)
    
    __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("taxon", "subspecies",
                                                                  "strain","stage",
                                                                  "biometrics")))
    
    def __post_init__(self):
        if isinstance(self.biometrics, Biometrics):
            self.biometrics.postnatal = self.stage > OrganismStage.prenatal
                
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class BiologicalSource(ScipyenDataclass):
    r"""
        TODO: 2024-11-17 21:11:13 : locate and use neuronal taxonomy API
    """
    organism:Organism = dataclasses.field(default_factory=Organism)
    # organ:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    
    # BUG: 2024-12-13 15:31:40 FIXME
    # accessing this will trigger the lazy initialization of the "mesh" object,
    # and invalidate future comparisons (e.g. see ScipyenDataclass.__eq__ and
    # ScipyenDataclass.diff)
    #
    #   NOTE: 2024-12-13 15:40:14
    #   understand how meshio obejcts are being compared - see meshio package!
    #   
    #   TODO: 2024-12-14 10:17:30 possible fix - no need for the above; becuase
    #   the meshio obejcts will ALWAYS be different (their comparison does NOT
    # compare actual data but rather object python id) we must use the strategy
    #   below:
    # a "source" is uniquely determined by its "id" (source id, not python id)
    # and by the atlas is belongs to; therefore they can be uniquely compared
    # for equality using only these two attributes (or rather elements of the
    # source underlying dictionary)(and, therefore, stored in HDF5)
    structure:BGStructureDescriptor = BGStructureDescriptor()
    # for now, only brain atlas api is supported
    
    
    cellType:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA) # e.g. "neuron"
    cellMorphologicalType:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA) # e.g."pyramidal"
    cellDescriptors:typing.Union[str, type(pd.NA), typing.Sequence[str]] = dataclasses.field(default=pd.NA)
    sourceType:BioSourceType = dataclasses.field(default=BioSourceType.exvivo)
    sourceID:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # identifier for the cell source: this may a (meaningful) combination of:
    #   animal ID,
    #   experimental date
    #   cortex region
    #
    #   e.g. TS2_1234567_01_02_22_VisCx_
    #
    # NOTE: the rules for naming the source are up to you, BUT:
    #   1) be consistent
    #   2) should contain ONLY alphanumeric characters and underscore ('_')
    #   3) should NOT begin with a digit or underscore ('_')

    cellID:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # identifier for this cell; there may be more than one cell from the same animal
    #
    # NOTE: the rules for constructing a cell ID are up to you, BUT:
    #   1) be consistent
    #   2) should contain ONLY alphanumeric characters and underscore ('_')
    #   3) should NOT begin with a digit or underscore ('_')
    # 
    
    # TODO: 2024-11-18 16:51:36
    # move this to ScanData metadata
    # fieldID:typing.Union[str, type(pd.NA)] = dataclasses.field(default=pd.NA)
    # # ID for a microscopy field — useful only for experiments involving imaging
    # # unique identifier for the microscopy field (e.g. one can record from more 
    # # than one field containing (sub)-regions of the same cell — spines, 
    # # dendritic segments, etc)
    
    cellCompartment:CellCompartment = dataclasses.field(default_factory=CellCompartment)
    # cellular compartment (there may be more than one in the same
    # field) — e,g, "spine", "dendrite", "axon", "soma"
    
    __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("organism",
                                                                  "structure",
                                                                  "cellType",
                                                                  "cellMorphologicalType",
                                                                  "cellDescriptors",
                                                                  "sourceType",
                                                                  "sourceID",
                                                                  "cellID",
                                                                  "cellCompartment",)))
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class Procedure(ScipyenDataclass):
    r"""An experimental procedure: what is being done during an Episode.
    
    A succession of procedures (attached to the episodes of a Schedule) 
        represents an experimental protocol.
        
    NOTE: The Treatment class is recommended for use in lieu of generic Procedure
    where procedureType is 'treatment'
    
    """
    # name:str = ""
    _:KW_ONLY
    type: ProcedureType = ProcedureType.null
    # description: str = ""
    
    __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("type", ) )) # "name" and "description" inherited from ScipyenDataclass
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class SubstanceDosage(ScipyenDataclass):
    r"""Logical mapping between a compund (or substance) and a dose, in a Treatment.
    Fields:
    name:str. Name of the compound (free-form within Python's rules)
    dose: pq.Quantity. This can be:
        • a scalar quantity - unique dose administered during a Treatment
        • a signal-like object:
            ∘ neo.AnalogSignal - a "continuously" time-varying dose, sampled at
                regular time intervals
            ∘ neo.IrregularlySampledSignal - different doses administered at 
                discrete, possibly irregular, times
    """
    name:str = "Vehicle"
    dose: DoseDescriptor = DoseDescriptor(default=None)
    
    __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("dose", )))
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
    
@dataclass
class Treatment(Procedure):
    r"""
    Encapsulates the administration of a dose of substance(s) via a specified route.
    
    name: treatment name (typically, the compound's name)
    substance: SubstanceDosage or sequence (tuple, list) of SubstanceDosage
    
    """
    name:str = "Treatment"
    __match_args__ = tuple(set(Procedure.__match_args__ + ("substance", "route", "type")))
    _:KW_ONLY
    substance:typing.Union[SubstanceDosage, typing.Sequence[SubstanceDosage]] = field(default_factory=SubstanceDosage)
    # allow combination of compounds
    route:AdministrationRoute = AdministrationRoute.null
    
    type:ImmutableDescriptor = ImmutableDescriptor(default=ProcedureType.treatment)
    
    def __post_init__(self):
        super().__init__(name=self.name, description=self.description, 
                         type = ProcedureType.treatment)
        
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
@dataclass
class Episode(ScipyenDataclass):
    r"""Generic episode for frame-based data.
        NOTE: The `beginFrame` and `endFrame` fields are inclusive indices.
        To use them in indexing a sequence (or frames), add 1 (one) to the 
        `endFrame` field, e.g.:
        range(data.beginFrame, data.endFrame +1)
        An Episode is an elementary part of a Schedule, and is logically associated
        with a Procedure.
        
        The defining attributes are: `name`, `begin`, `end`, `beginFrame`, `endFrame`
        and `procedure`.
        
        In addition, the `description` attribute (a str) has an informative role
        without affecting the identity of an Episode
    """
    # name:str = ""
    _:KW_ONLY
    begin:datetime.datetime = datetime.datetime.now()
    end:datetime.datetime = datetime.datetime.now()
    beginFrame:int = 0
    endFrame:int = 0
    # description:str = ""
    procedure:typing.Optional[Procedure] = field(default = None)
    
    __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("begin", "end", 
                                                                  "beginFrame", "endFrame",
                                                                  "procedure")))
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
# #         if not isinstance(other, self.__class__):
# #             return False
# #         
# #         ret = True
# #         ret &= self.name == other.name
# #         if ret:
# #             # don't compare description as this is not definitory
# #             ret &= all(getattr(self, f.name) == getattr(other, f.name) for f in list(filter(lambda x: x.name != "description", dataclasses.fields(self.__class__))))
# #             
#         return ret
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
@dataclass
class Schedule(ScipyenDataclass):
    r"""Logical grouping of a sequence of episodes.
        A Schedule can be logically considered a "protocol", where any of its
        constituent episodes may associate a Procedure. 
    """
    # name:str = ""
    _:KW_ONLY
    episodes:typing.Sequence[Episode] = field(default_factory = lambda : list())
    
    __match_args__ = tuple(set(ScipyenDataclass.__match_args__ + ("episodes",)))
    
    def __repr__(self):
        indent = lambda x: x.replace("\n", "\n\t")
        repr_attr = lambda x: f": {type(x).__name__} → '{x}'" if isinstance(x, str) else f": {type(x).__name__} → {indent(x.__repr__())}" if dataclasses.is_dataclass(type(x)) else f": {type(x).__name__} → {x}"
        ret = [f"{self.__class__.__name__}:"] + sorted([f"\t{a}{repr_attr(getattr(self, a))}" for a in self.__match_args__])
        return "\n".join(ret)
    
    def __eq__(self, other) -> bool:
        return super().__eq__(other)
    
#         if not isinstance(other, self.__class__):
#             return False
#         
#         ret = len(self.episodes) == len(other.episodes)
#         
#         if ret:
#             return all(e==e1 for (e,e1) in zip(self.episodes, other.episodes))
#         
#         return ret
    
    def __len__(self)->int:
        return len(self.episodes)
    
    def __getitem__(self, key:typing.Union[int, slice, range, tuple, list, collections.deque, str]):
        if isinstance(key, int):
            if key >= len(self.episodes) or key < -1 * len(self.episodes):
                raise IndexError(f"Index {key} out of range for {len(self.episodes)} episodes")
            return self.episodes[key]
        
        elif isinstance(key, str):
            if len(self.episodes) == 0:
                raise KeyError(f"Episode named {key} not found")
            
            ret = list(filter(lambda x:x.name == key, self.episodes))
            
            if len(ret) == 0:
                raise KeyError(f"Episode named {key} not found")
            elif len(ret) > 1:
                scipywarn(f"Duplicate episode name ({key}) found")
                
            return ret
        
        elif isinstance(key, slice):
            return self.episodes[key]
        
        elif isinstance(key, range):
            if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
            
            return [self.episodes[k] for k in key]
        
        elif isinstance(key, (tuple, list, collections.deque)):
            if len(key) == 0:
                return list()
            elif all(isinstance(k, int) for k in key):
                if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                    raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
                return [self.episodes[k] for k in key]
            
            else:
                raise KeyError("All indices must be int")
            
        else:
            raise TypeError(f"Invalid indexing key type {type(key).__name__}")
        
    def __setitem__(self, key:typing.Union[int, slice, range, tuple, list, collections.deque], 
                    value:typing.Union[Episode, typing.Iterable[Episode]]):
        if isinstance(key, int):
            if key >= len(self.episodes) or key < -1 * len(self.episodes):
                raise IndexError(f"Index {key} out of range for {len(self.episodes)} episodes")
            if not isinstance(value, Episode):
                raise TypeError(f"Expecting an Episode; instead, got {type(value).__name__}")
            
            self.episodes[key] = value
        
        elif isinstance(key, slice):
            if not isinstance(value, typing.Iterable):
                raise TypeError(f"The RHS of the assignment must be an iterable; instead, got {type(value).__name__}")
            if not all(isinstance(v, Episode) for v in value):
                raise TypeError(f"The RHS iterable must contain only Episode objects; instead got {unique((type(v).__name__ for v in value))}")
            l_indices = len(range(*key.indices(len(self.episodes))))
            if l_indices < len(value):
                raise ValueError(f"Too many RHS elements ({l_indices}); expecting {len(key)}")
            if l_indices > len(value):
                raise ValueError(f"Too few RHS elements ({l_indices}); expecting {len(key)}")
            
            self.episodes[key] = value
        
        elif isinstance(key, range):
            if not isinstance(value, typing.Iterable):
                raise TypeError(f"The RHS of the assignment must be an iterable; instead, got {type(value).__name__}")
            if not all(isinstance(v, Episode) for v in value):
                raise TypeError(f"The RHS iterable must contain only Episode objects; instead got {unique((type(v).__name__ for v in value))}")
            if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
            if len(key) < len(value):
                raise ValueError(f"Too many RHS elements ({l_indices}); expecting {len(key)}")
            if len(key) > len(value):
                raise ValueError(f"Too few RHS elements ({l_indices}); expecting {len(key)}")
            
            for k in key:
                self.episodes[k] = value[k]
            
        elif isinstance(key, (tuple, list, collections.deque)):
            if len(key) == 0:
                return
            elif all(isinstance(k, int) for k in key):
                if not isinstance(value, typing.Iterable):
                    raise TypeError(f"The RHS of the assignment must be an iterable; instead, got {type(value).__name__}")
                if not all(isinstance(v, Episode) for v in value):
                    raise TypeError(f"The RHS iterable must contain only Episode objects; instead got {unique((type(v).__name__ for v in value))}")
                if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                    raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
                if len(values) > len(key):
                    raise ValueError(f"Too many RHS elements ({l_indices}); expecting {len(key)}")
                if len(values) < len(key):
                    raise ValueError(f"Too few RHS elements ({l_indices}); expecting {len(key)}")
                
                for k in key:
                    self.episodes[k] = value[k]
            else:
                raise KeyError("All indices must be int")
            
        else:
            raise TypeError(f"Invalid indexing key type {type(key).__name__}")
        
    def __delitem__(self, key:typing.Union[int, slice, range, tuple, list, collections.deque, str]):
        if isinstance(key, int):
            if key >= len(self.episodes) or key < -1 * len(self.episodes):
                raise IndexError(f"Index {key} out of range for {len(self.episodes)} episodes")
            
            del self.episodes[key]
            
        elif isinstance(key, str):
            if len(self.episodes) == 0:
                raise KeyError(f"Episode named {key} not found")
            
            ret = list(filter(lambda x:x.name == key, self.episodes))
            
            if len(ret) == 0:
                raise KeyError(f"Episode named {key} not found")
            
            elif len(ret) > 1:
                scipywarn(f"Duplicate episode name ({key}) found")
                
            keep  = [e for e in self.episodes if e.name != key]

            self.episodes[:] = keep
        
        elif isinstance(key, slice):
             del self.episodes[key]
        
        elif isinstance(key, range):
            if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
            
            keep  = [self.episodes[k] for k in range(len(self.episodes)) if k not in key]
            self.episodes[:] = keep
            
        elif isinstance(key, (tuple, list, collections.deque)):
            if len(key) == 0:
                return
            
            elif all(isinstance(k, int) for k in key):
                if any(k >= len(self.episodes) or k < -1 * len(self.episodes) for k in key):
                    raise IndexError(f"Index out of range for {len(self.episodes)} episodes")
                
                keep  = [self.episodes[k] for k in range(len(self.episodes)) if k not in key]
                self.episodes[:] = keep
            
            # elif all(isinstance(k, str) for k in key):
            #     keep  = [self.episodes[k] for k in range(len(self.episodes)) if k not in key]
            #     self.episodes[:] = keep
            
            else:
                raise KeyError("All indices must be int or str")
            
        else:
            raise TypeError(f"Invalid indexing key type {type(key).__name__}")
        
    def __iter__(self):
        return self.episodes.__iter__()
    
    def __reversed__(self):
        return self.episodes.__reversed__()
    
    def __add__(self, other):
        if isinstance(other, self.__class__):
            newepisodes = self.episodes.__add__(other.episodes)
            return self.__class__(name=self.name, episodes = newepisodes)
            
        elif isinstance(other, typing.Sequence):
            if len(other) and not all(isinstance(e, Episode)):
                raise TypeError("Can only add a sequence of Episodes")
            newepisodes = self.episodes.__add__(other)
            return self.__class__(name=self.name, episodes = newepisodes)
        
        else:
            raise TypeError(f"Invalid argument type ({type(other).__name__})")
            
    def __iadd__(self, other):
        if isinstance(other, self.__class__):
            self.episodes.__iadd__(other.episodes)
            return self
            
        elif isinstance(other, typing.Sequence):
            if len(other) and not all(isinstance(e, Episode)):
                raise TypeError("Can only add a sequence of Episodes")
            self.episodes.__iadd__(other)
            return self
        
        else:
            raise TypeError(f"Invalid argument type ({type(other).__name__})")
        
    def __mul__(self, value:int):
        return self.__class__(name=self.name, episodes = self.episodes.__mul__(value))
            
    def __imul__(self, value:int):
        self.episodes.__imul__(value)
        return self
    
    def __contains__(self, value:Episode):
        return value in self.episodes
    
    def append(self, value:Episode):
        if not isinstance(value, Episode):
            raise TypeError("A Schedule can only contain Episodes")
        
        self.episodes.append(value)
        
    def insert(self, index:int, value:Episode):
        if not isinstance(value, Episode):
            raise TypeError("A Schedule can only contain Episodes")

        self.episodes.insert(index, value)
        
    def pop(self, index:int=-1) -> Episode:
        return self.episodes.pop(index)
    
    def remove(self, value:Episode):
        if not isinstance(value, Episode):
            raise TypeError("A Schedule can only contain Episodes")
        
        self.episodes.remove(value)
        
    def reverse(self):
        self.episodes.reverse()
        
    def sort(self, *args, **kwargs):
        self.episodes.sort(*argsm **kwargs)
    
    def extend(self, value):
        if isinstance(value, self.__class__):
            self.episodes.append(value.episodes)
            
        elif isinstance(value, typing.Sequence):
            if len(value):
                if all(isinstance(v, Episode) for v in value):
                    self.episodes.append(value)
                else:
                    raise TypeError("A Schedule can only contain Episodes")
                    
        else:
            raise TypeError(f"Can only append a Schedule or a sequence of Episodes")
        
    def index(self, episode:Episode):
        if not isinstance(episode, Episode):
            raise TypeError("A Schedule can only contain Episodes")
        if episode not in self.episodes:
            raise ValueError("Episode is not contained in this Schedule")
        
        ndx = [k for k in range(len(self.episodes)) if self.episodes[k] == episode]
        
        return ndx[0]

    def count(self, episode:Episode):
        if not isinstance(episode, Episode):
            raise TypeError("A Schedule can only contain Episodes")
        
        if episode not in self.episodes:
            return 0
        
        return len(e for e in self.episodes if e == episode)
    
        
    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Group:
        
        from iolib import h5io
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity
        
        attrs = {"name": getattr(self, "name")}
        
        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)
        
        if isinstance(name, str) and len(name.strip()):
            target_name = name
        
        entity = group.create_group(target_name, track_order=track_order)
        entity.attrs.update(obj_attrs)
        h5io.toHDF5(self.episodes, entity, name="episodes", 
                            oname="episodes", compression=compression,
                            chunks=chunks, track_order=track_order,
                            entity_cache=entity_cache)
        h5io.storeEntityInCache(entity_cache, self, entity)
        return entity
    
    @classmethod
    def fromHDF5(cls, entity:h5py.Group,
                             attrs:typing.Optional[dict] = None, cache:dict={}):
        
        from iolib import h5io
        if entity in cache:
            return cache[entity]
        
        attrs = h5io.attrs2dict(entity.attrs)
        
        name = attrs["name"]
        
        episodes = h5io.fromHDF5(entity["episodes"], cache)
        
        return cls(name, episodes=episodes)
    
    @singledispatchmethod
    def episode(self, ndx) -> Episode:
        raise NotImplementedError(f"Wrong index type: {type(ndx).__name__}")
    
    @episode.register(int)
    def _(self, ndx:int) -> Episode:
        if ndx >= len(self.episodes) or ndx < -1 * len(self.episodes):
            raise IndexError(f"Invalid episode index {ndx} for {len(self.episodes)}")
        
        return self.episodes[ndx]
    
    @episode.register(str)
    def _(self, name:str) -> Episode:
        episodes = [e for e in self.episodes if e.name == name]
        if len(episodes):
            return episodes[0]
        else:
            raise IndexError(f"Episode name {name} does not exist")
        
    def episodeNames(self) -> list[str]:
        return [e.name for e in self.episodes]
    
    def epsodeIndex(self, name:str) -> int:
        return self.episodeNames.index(name)
    
    def addEpisode(self, episode:Episode):
        if episode not in self.episodes:
            self.episodes.append(episode)
            
    def addEpisodes(self, episodes:typing.Sequence[Episode]):
        self.episodes.extend([e for e in episodes if e not in self.episodes])
        
    def removeEpisode(self, episode):
        if episode in self.episodes:
            self.episodes.remove(episode)
            
    @property
    def procedures(self):
        return [e.procedure for e in self.episodes]
    
