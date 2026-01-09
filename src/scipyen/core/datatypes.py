# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r''' Utilities for generic and numpy array-based data types such as quantities
Changelog:
2021-01-06 14:35:30 gained module-level constants:
RELATIVE_TOLERANCE
ABSOLUTE_TOLERANCE
EQUALS_NAN

2025-03-20 00:21:23 
the above constants moved to core.constants to avoid circular imports

    
'''

from __future__ import print_function

#### BEGIN core python modules
from abc import ABC, ABCMeta, abstractmethod
import collections 
from collections import deque, namedtuple
from functools import (singledispatch, singledispatchmethod)
import itertools
import datetime
from enum import (Enum, IntEnum, EnumMeta, EnumType)
import inspect
import numbers
import math
import dataclasses
from dataclasses import (dataclass, KW_ONLY, MISSING, field)
import sys, os
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
# 
# if os.environ["QT_API"] == "pyside6":
#     import PySide6
#     from PySide6 import (QtGui, QtCore, QtWidgets,)
#     import qtpy
#     qtpy.API = os.environ["QT_API"]
# else:
#     import qtpy
#     qtpy.API = os.environ["QT_API"]
#     from qtpy import (QtGui, QtCore, QtWidgets,)
    
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
from core import scipyen_quantities as scq
from core import xmlutils
from core import strutils
from core.prog import (safewrapper, is_hashable, is_type_or_subclass, 
                       ImmutableDescriptor, scipywarn, NoData, print_styled)
# from core.datazone import DataZone # not needed here, and it may results in circular imports if called here
from core.datasignal import (_new_DataSignal, _new_IrregularlySampledDataSignal, DataSignal, IrregularlySampledDataSignal)
# from core import bgbridge
# from core.bgbridge import (BGStructureDescriptor, BrainGlobeAtlas)
from core import taxonbridge
from core.taxonbridge import(Taxon, TaxonDescriptor)
from core.typeenum import TypeEnum
from core.constants import (RELATIVE_TOLERANCE, ABSOLUTE_TOLERANCE,
                            EQUAL_NAN, GENOTYPES)

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
subarray_type_map = {neo.AnalogSignal: neo.IrregularlySampledSignal,
                    DataSignal: IrregularlySampledDataSignal}
        
               
ndarray_type = ndarray.__name__

NUMPY_NUMERIC_KINDS = set("buifc")
NUMPY_STRING_KINDS = set("SU")

Real: typing.TypeAlias = typing.Union[int, float, np.int64, np.float64]
Complex: typing.TypeAlias = typing.Union[complex, np.complex128]
Number: typing.TypeAlias = typing.Union[Real, Complex]


UnitTypes = collections.defaultdict(lambda: "NA", 
                                    {"a":"axon", "b":"bouton", "c":"cell", 
                                     "d":"dendrite", "e":"excitatory", 
                                     "g":"granule",  "i":"inhibitory", 
                                     "l":"stellate", "p":"pyramidal",  
                                     "m":"microglia", "n":"interneuron", 
                                     "s":"spine", "t":"terminal",
                                     "y":"astrocyte"})


MissingType: typing.TypeAlias = type(MISSING)

# NOTE: 2024-07-28 15:46:49 
# these are utterly generic; almost surely you'd want to write your own
# e.g. Cacna1c+/-, etc...


# RELATIVE_TOLERANCE = 1e-4
# ABSOLUTE_TOLERANCE = 1e-4
# EQUAL_NAN = True

def enum_names(data:EnumType) -> list | None:
    r"""Lists the field names of an Enum.
WARNING: Use to inspect enumerated types (collections of enum values), NOT an  
individual enum value!
"""
    if isinstance(data, EnumType):
        return list(map(lambda x: x.name, data))
    
def enum_values(data:EnumType) -> list | None:
    r"""Lists the field values of an Enum
WARNING: Use to inspect enumerated types (collections of enum values), NOT an  
individual enum value!
"""
    if isinstance(data, EnumType):
        return list(pam(lambda x: x.value, data))
    
def enum_to_dict(data:EnumType) -> dict | None:
    r"""Creates a dictionary mapping field name ↦ fiueld value from an Enum
WARNING: Use to inspect enumerated types (collections of enum values), NOT an  
individual enum value!
"""
    if isinstance(data, EnumType):
        return dict(map(lambda x: (x.name, x.value), data))

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
    
    elif x.ndim > 2:
        return any(s == x.size for s in x.shape)
    
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

def check_mapping_fields(x:dict, constraints:list) -> bool:
    if not isinstance(x, dict):
        return False
    
    for constraint in constraints:
        field_name = constraint[0]
        field_type = constraint[1]
        field_predicate = constraint[2]
        
        if field_name not in x:
            return False
        
        if not isinstance(x[field_name], field_type):
            return False
        
        if isinstance(field_predicate, typing.Callable):
            if not field_predicate(x[field_name]):
                return False
            
    return True

def check_numpy_array(x:np.ndarray, /, dtype:typing.Optional[np.dtype] = None,
                      dtype_comparison:str="eq",
                      ndim:typing.Optional[int] = None, 
                      ndim_comparison:str="eq",
                      size:typing.Optional[int] = None, 
                      size_comparison:str="eq",
                      shape:typing.Optional[tuple] = None,
                      quantity:bool=False,
                      units:typing.Optional[pq.Quantity] = None,
                      units_convertible:bool=False,
                      ) -> bool:
    r"""Atomic check for a numpy ndarray attributes.

    Positional parameters:
    ======================
    x - the object to check
    
    Named parameters:
    =================
    dtype: optional, default is None; when given, x.dtype will be ckeched against
        it using 'dtype_comparison'
    dtype_comparison: default is "eq"; possible values are:
        "eq", "==", "gt", ">", "ge", ">=", "lt", "<", "le" and "<="
        anything else raises a ValueError
    ndim: optional, default is None; when given, x.ndim will be ckeched against 
        it using 'ndim_comparison'
    ndim_comparison: default is "eq"; possible values are:
        "eq", "==", "gt", ">", "ge", ">=", "lt", "<", "le" and "<="
        anything else raises a ValueError
    size: optional, default is None; when given, x.size will be ckeched against it using the 
        size_comparison
    size_comparison: default is "eq"; possible values are:
        "eq", "==", "gt", ">", "ge", ">=", "lt", "<", "le" and "<="
        anything else raises a ValueError
    shape: optional, default is None; when given, x.shape will be check for 
        equality to shape
    quantity: optional default is False; when True, checks that 'x' is a Quantity
        array (with any units)
        NOTE: this parameter can be omitted when at least 'units' is passed with
        a non-default value
    units: optional, defaulkt is None; when given, checks that 'x' is a Quantity 
        array with these units
    units_convertible: optional default is False; when True, then if 'units' is
        a pq.Quantity and x.units != units the array 'x' still checks True if 
        x.units are convertible to 'units';
    Returns:
    ========
    A bool
"""
    ret = isinstance(x, np.ndarray)
    if isinstance(dtype, np.dtype) and ret:
        if dtype_comparison in ("ge", ">="):
            ret &= x.dtype >= dtype
        elif dtype_comparison in ("gt", ">"):
            ret &= x.dtype > dtype
        elif dtype_comparison in ("le", "<="):
            ret &= x.dtype <= dtype
        elif dtype_comparison in ("lt", "<"):
            ret &= x.dtype < dtype
        elif dtype_comparison in ("eq", "=="):
            ret &= x.dtype == dtype
        else:
            raise ValueError(f"'dtype_comparison' must be one of 'eq', '==', 'gt', '>', 'ge', '>=', 'lt' '<', 'le', '<='; instead got {dtype_comparison}")
            
    if ret and isinstance(ndim, int):
        if ndim < 0:
            raise ValueError(f"'ndim' must be >= 0; got {ndim} instead")
        
        if ndim_comparison in ("ge", ">="):
            ret & x.ndim >= ndim
        elif ndim_comparison in ("gt", ">"):
            ret & x.ndim > ndim
        elif ndim_comparison in ("le", "<="):
            ret & x.ndim <= ndim
        elif ndim_comparison in ("lt", "<"):
            ret & x.ndim > ndim
        elif ndim_comparison in ("eq", "=="):
            ret & x.ndim == ndim
        else:
            raise ValueError(f"'ndim_comparison' must be one of 'eq', '==', 'gt', '>', 'ge', '>=', 'lt' '<', 'le', '<='; instead got {ndim_comparison}")
            
    if ret and isinstance(size, int):
        if size < 0:
            raise ValueError(f"'size' must be >= 0; got {size} instead")
        if size_comparison in ("ge", ">="):
            ret & x.size >= size
        elif size_comparison in ("gt", ">"):
            ret & x.size > size
        elif size_comparison in ("le", "<="):
            ret & x.size <= size
        elif size_comparison in ("lt", "<"):
            ret & x.size > size
        elif size_comparison in ("eq", "=="):
            ret & x.size == size
        else:
            raise ValueError(f"'size_comparison' must be one of 'eq', '==', 'gt', '>', 'ge', '>=', 'lt' '<', 'le', '<='; instead got {size_comparison}")
            
    if ret and isinstance(shape, tuple):
        ret &= x.shape == shape
        
    if ret and quantity:
        ret &= isinstance(x, pq.Quantity)
        
    if ret and isinstance(units, pq.Quantity):
        ret &= isinstance(x, pq.Quantity)
        if ret:
            ok = x.units == units
            if not ok and units_convertible:
                ok = scq.units_convertible(x.units, units)
            ret &= ok
        
    return ret

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
    r"""Like enum2str but does a single pass through the sequence"""
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
    
def array_slice(data:np.ndarray, slicing:(dict, type(None))) -> tuple:
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

def is_unavailable(x:typing.Any) -> bool:
    return x is pd.NA or x is np.nan or x is math.nan or x is dataclasses.MISSING
    
def is_dotted_name(s:typing.Any) -> bool:
    return isinstance(s, str) and '.' in s

def is_namedtuple(x:typing.Any) -> bool:
    if isinstance(x, type):
        ret = issubclass(x, tuple)
    else:
        ret = issubclass(type(x), tuple)
        
    if ret: 
        ret &= all([hasattr(x, a) for a in ("_asdict", "_fields", "_make", "_replace")])
        
    return ret
    
def is_string(array) -> bool:
    r"""Determine whether the argument has a string or character datatype, when
    converted to a NumPy array.
    
    String or character (including unicode) have dtype.kind of "S" or "U"
    
    """
    return np.asarray(array).dtype.kind in NUMPY_STRING_KINDS

def is_numeric_string(array) -> bool:
    r"""Determines if the argument is a string array that can be parsed as numeric.
    """
    if isinstance(array, str):
        array = [array]
        
    return is_string(array) and not np.isnan(np.genfromtxt(array)).any()

def is_numeric(array) -> bool:
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

def __default_none__() -> None:
    return None

def __default_units__() -> pq.Quantity:
    return arbitrary_unit

def __default_undimensioned__() -> pq.Quantity:
    return pq.dimensionless

def categorize_data_frame_columns(data:pd.DataFrame, *column_names, inplace:bool=True) -> pd.DataFrame:
    r""""""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expecting a pandas.DataFrame; got %s instead" % type(data).__name__)
    
    if len(column_names) == 0:
        raise TypeError("Expecting at least one column")
    
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
    
   
def inspect_members(obj:typing.Any, predicate:typing.Optional[typing.Callable] = None) -> dict:
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

def namespace2dict(x:types.SimpleNamespace) -> dict:
    r"""Returns a reference to the internal dictionary of the SimpleNamespace 'x'"""
    if not isinstance(x, types.SimpleNamespace):
        raise TypeError(f"Expecting a types.SimpleNamespace; instead got a {type(x).__name__}")
    return dict(map(lambda i: (i[0], namespace2dict(i[1]) if isinstance(i[1], types.SimpleNamespace) else i[1]), x.__dict__.items()))
    

def namespace_symbols(x:types.SimpleNamespace) -> typing.Generator:
    r"""Yields the symbols (keys) in the SimpleNamespace object 'x'"""
    if not isinstance(x, types.SimpleNamespace):
        raise TypeError(f"Expecting a types.SimpleNamespace; instead got a {type(x).__name__}")
    
    yield from x.__dict__.keys()
    
def namespace_values(x:types.SimpleNamespace) -> typing.Generator:
    r"""Yields the values in the SimpleNamespace object 'x'"""
    if not isinstance(x, types.SimpleNamespace):
        raise TypeError(f"Expecting a types.SimpleNamespace; instead got a {type(x).__name__}")
    
    yield from x.__dict__.values()
    
def namespace_objects(x:types.SimpleNamespace) -> typing.Generator:
    r"""Yields the items in the SimpleNamespace object 'x'"""
    if not isinstance(x, types.SimpleNamespace):
        raise TypeError(f"Expecting a types.SimpleNamespace; instead got a {type(x).__name__}")
    
    yield from x.__dict__.items()
