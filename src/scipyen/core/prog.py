# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

'''
Helper functions and classes for programming, including:
decorators, context managers, and descriptor validators.


'''

#print("{}: {}".format(__file__, __name__))

import pprint

from abc import ABC, abstractmethod
from importlib import abc as importlib_abc
import enum, io, os, re, itertools, sys, time, traceback, types, typing
from types import SimpleNamespace
import collections
from collections import deque
import importlib, inspect, pathlib, warnings, operator, functools
from warnings import WarningMessage
from inspect import Parameter, Signature
    
from functools import (singledispatch, singledispatchmethod, 
                       update_wrapper, wraps,)
from contextlib import (contextmanager, ContextDecorator,)
from dataclasses import (MISSING, dataclass, field, KW_ONLY)

from traitlets.utils.importstring import import_item
from traitlets import Bunch

import numpy as np
import neo, vigra
import quantities as pq
import pandas as pd

import colorama

# try:
#     import mypy
# except:
#     print("Please install mypy first")
#     raise

# from . import workspacefunctions
# from .workspacefunctions import debug_scipyen
from .strutils import InflectEngine

CALLABLE_TYPES = (types.FunctionType, types.MethodType,
                  types.WrapperDescriptorType, types.MethodWrapperType,
                  types.BuiltinFunctionType, types.BuiltinMethodType,
                  types.MethodDescriptorType, types.ClassMethodDescriptorType)

class NoData():
    """Empty placeholder class that signifies lack of any data.
        Used in Descritpr validation, in order to allow the use of None, MISSING,
        pandas NAType as values in descriptors.
    Cannot be instantiated.
    """
    def __new__(cls):
        return cls
    def __repr__(self):
        return "NoData"

class ArgumentError(Exception):
    pass

class DescriptorException(Exception):
    pass


class AttributeAdapter(ABC):
    """Abstract Base Class as a callable for pre- and post-validation
    """
    @abstractmethod
    def __call__(self, obj, value):
        pass
    
@dataclass
class AttributeSpecification:
    """The non-keyword fields are set to match neo attribute specifications"""
    name:str # decriptor name
    types:typing.Union[type, typing.Tuple[type], typing.Callable] # descriptor types or predicates
    ndim:typing.Union[int, dict] = 0 # ndim (neo model), dtype
    dtype:typing.Union[np.dtype, dict] = field(default_factory = lambda: np.dtype(float))
    _: KW_ONLY
    default:typing.Any = NoData
    length:int = 0
    shape:tuple = tuple()
    units:pq.Quantity = pq.dimensionless
    element_types:tuple = tuple()
    key_types:tuple = tuple()
    key_value_mappings:tuple = tuple()
    
    allow_none:bool = False
    
    def __post_init__(self):
        print(f"{self.__class__.__name__}.__post_init__:\nself.types: {self.types}")
        if not (isinstance(self.types, type)) and not (isinstance(self.types, tuple) and all(isinstance(t_, type) for t_ in self.types)):
                raise DescriptorException(f"Incorrect type specification")
            
        if self.default is MISSING:
            if self._allow_none:
                self.default = None
            else:
                if isinstance(self.types, type):
                    type_ = self.types
                elif isinstance(self.types, tuple) and all(isinstance(t_, type) for t_ in self.types):
                    type_ = self.types[0]
                    
                try:
                    self.default = self.types()
                except:
                    scipywarn(f"Cannot construct a default value for type {type_}")
                    raise
                        
                        
    
    
    
    
    
class BaseDescriptorValidator(ABC):
    """Abstract superclass that implements a Python descriptor with validation.
    
    The descriptor operated on a private attribute of the owner by exposing a
    public name to the user as getter/setter accessor.
    
    """
    @staticmethod
    def get_private_name(name:str) -> str:
        """Find out what private name this would operate on
        """
        return f"_{name}_"
    
    def __set_name__(self, owner, name:str) -> None:
        """Call this in the implementation's __init__
        """
        self.private_name = f"_{name}_"
        self.public_name = name
        
    def __get__(self, obj, objtype=None) -> object:
        """Implements access to a data descriptor value (attribute access).
        """
        return getattr(obj, self.private_name)
    
    def __set__(self, obj, value) -> None:
        """Assigns a new value to the private attribute accessed by the descriptor.
        
        The value is first validated by calling the 'validate' method of the 
        descriptor validator, which MUST be implemented in subclasses of 
        BaseDescriptorValidator. the validated value is then assigned to the 
        private attribute that is wrapped by this descriptor
        
        If the descriptor owner contains at least one of the dict attributes
        '_preset_hooks_' and '_postset_hooks_' mapping the descriptor's public
        name to an AttributeAdapter instance, then the adapter instance will be
        called BEFORE (respectively, AFTER) assignment of 'value' to descriptor.
        
        """
        # NOTE: 2022-01-03 20:45:48
        # value should be validated BEFORE anything
        self.validate(value)
        
        if hasattr(obj, "_preset_hooks_") and isinstance(obj._preset_hooks_, dict):
            preset_func = obj._preset_hooks_.get(self.public_name, None)
            if isinstance(preset_func, AttributeAdapter):
                preset_func(obj, value)
                
            elif isinstance(preset_func, types.MethodType) and inspect.ismethod(getattr(obj, preset_func.__name__, None)):
                fargs = inspect.getfullargspec(preset_func)
                if len(fargs.args) == 0:
                    preset_func(obj)
                    
                else:
                    preset_func(obj, value)
                
            elif isinstance(preset_func, types.FunctionType):
                fargs = inspect.getfullargspec(preset_func)
                if len(fargs.args) == 1:
                    preset_func(obj)
                elif len(fargs.args) > 1:
                    preset_func(obj,value)
                
        setattr(obj, self.private_name, value)
        
        # NOTE: 2021-12-06 12:43:48 
        # call postset hooks ONLY AFTER the descriptor value had been set
        # (last line of code, above)
        if hasattr(obj, "_postset_hooks_") and isinstance(obj._postset_hooks_, dict):
            postset_func = obj._postset_hooks_.get(self.public_name, None)
            if isinstance(postset_func, AttributeAdapter):
                postset_func(obj, value)
            elif isinstance(postset_func, types.MethodType) and inspect.ismethod(getattr(obj, postset_func.__name__, None)):
                fargs = inspect.getfullargspec(postset_func)
                if len(fargs.args) == 0:
                    postset_func()
                else:
                    postset_func(value)
                    
            elif isinstance(postset_func, types.FunctionType):
                fargs = inspect.getfullargspec(postset_func)
                if len(fargs.args) == 1:
                    postset_func(obj)
                elif len(fargs.args) > 1:
                    postset_func(obj,value)
                
        
    def __delete__(self, obj):
        if hasattr(obj, self.private_name):
            delattr(obj, self.private_name)
            
        # complete wipe-out
        if hasattr(obj.__class__, self.public_name):
            delattr(obj.__class__, self.public_name)
        
    @abstractmethod
    def validate(self, value):
        pass
    
class ImmutableDescriptor(BaseDescriptorValidator):
    """
        Crude implementation of a read-only descriptor.
        
        Useful for implementing 'dataclass' classes that are not frozen, but 
        have read-only attributes.
        
        Usage in a 'dataclass' definition:
        
        @dataclass
        class SomeClass:
            a: int = 0
            b: ImmutableDescriptor = ImmutableDescriptor(default="abc")
        
        c = SomeClass()
        c.a = 20 # <- OK
        c.b = "31" # <- no effect
        
    """
    def __init__(self, *, default):
        self._default = default
        
    def __get__(self, obj, objtype=None) -> object:
        if obj is None:
            return self._default
        
        return getattr(obj, self.private_name, self._default)
     
    def __set__(self, obj, value):
        pass
    
    def validate(self, value):
        return value == self._default
        
class OneOf(BaseDescriptorValidator):
    def __init__(self, name:str, /, *options):
        self.options = set(options)

    def validate(self, value):
        if value not in self.options:
            raise ValueError(f'Expected {value!r} to be one of {self.options!r}')

class DescriptorTypeValidator(BaseDescriptorValidator):
    def __init__(self, name:str, /, *types):
        self.types = set(t for t in types if isinstance(t, type))
        
    def validate(self, value):
        if not isinstance(value, tuple(self.types)):
            raise TypeError(f"For {self.private_name} one of {self.types} was expected; got {type(value).__name__} instead")
        
class DescriptorGenericValidator(BaseDescriptorValidator):
    # NOTE: 2024-07-29 17:14:57 TODO/FIXME
    # check rehaul of parse_descriptor_specification and of the 
    # WithDescriptors.setup_descriptor class method
    def __init__(self, name:str, defval:typing.Any, /, *args, **kwargs):
        """
        name: `public` name of the descriptor
    
        defval: default value (may be None if allow_none)
    
        args: tuple of types or unary predicates;
            
            NOTE: unary predicates are functions that expect a Python object as 
                the first (only) argument and return a bool.
                
                Functions which expect additional arguments can be 'reduced' to
                unary predicates by using either:
                
                a) functools.partial (for unbound functions such as those defined
                outside classes)
                
                b) functools.partialmethod (for methods)
            
        kwargs: currently two keywords are supported:
            "allow_none": bool (default True) ↦ allow None as a descriptor value
            "dcriteria": dict (default empty) ↦ speified additional criteria for
                descriptor values that are collection-like or array-like
                Use with CAUTION.
            
        When 'dcriteria' is empty, then no additional criteria are defined, and 
        the descriptor value is validated based on 'name' and 'args' and the 
        'allow_none' keyword.
    
        WARNING: In relation to data types (and dtypes): the current implementation
        is not strict, in the sense that it will allow values with types (or dtypes)
        that inherit from the type(s) or dtype(s) specified in the criteria below.
    
        Another current limitation is that collection elements that are themselves
        array-like or collection-like are NOT subject to the validation process,
        i.e., the validation does NOT recurse to deeper levels beyond the top
        container of a nested data structure.
    
        Table with type-related properties in the dcriteria dict:
        key         value is always a nested dict — an empty dict here mean no 
        (a type)        criteria are defined and the descriptor value is validated
                        based on 'name' and types or predicates in 'args'
                    
        ========================================================================
                    Nested dict key:str ↦ value; 
                    default is in <angle brackets>'; 
                    <> means no default
        ------------------------------------------------------------------------
    
        bytes       'len' ↦ int <NoData>  prescribed length; when NoData, then 
        bytearray         an object with any length is valid
        str
        
        tuple       'len' ↦ int, <NoData>;  prescribed length; when NoData, then 
        list        a tuple with any length is valid
        deque       'types' ↦ tuple, <(,)>;  prescribed element types; when empty,
                    then a tuple is any element type is valid. 
        
        dict        'len' ↦ int, <NoData>; prescribed length; when NoData, then 
                    a dict with any length is valid
    
                    'types' ↦ tuple, <(,)>;  prescribed value types for the dict 
                        elements; when empty, then the dict elements can have any
                        any value type. 
    
                    'key_types' ↦ tuple; <(,)>; prescribed key types for the dict 
                        elements; when empty, the dict can use any hashable 
                        object as keys (NOTE: a dict can use any — and only — 
                        hashable type as keys)
    
                    'keys' ↦ tuple of hashable objects, <(,)>; prescribed actual
                        keys that must be present in the dict (the value they're
                        mapped to is irrelevant); when empty, then the dict can
                        contain any key
                        NOTE: as noted above, these objects MUST be hashable
    
                    'mapping' ↦ dict of key:hashable type ↦ type or tuple of types,
                        <>;
                        This is the most stringent criterion, where a dict 
                        descriptor value is valid if it maps specific keys to 
                        to specific type or types of values.
    
        numpy.ndarray 
                    'ndim' ↦ int, <NoData>; when NoData, ndms is irrelevant
                    'shape' ↦ tuple[int], <(,)>; when empty, the array shape is
                            irrelevant
    
                    CAUTION: Problem is ill-defined: is the criterion enforcing
                    a specific dtype or does it also accept dtypes that inherit
                    from the criterion dtype ? Current implementation does the
                    latter.
                    
                    'dtype' ↦ numpy.dtype, tuple of numpy.dtype, <(,)>; when an 
                            empty tuple, the dtype is irrelevant
    
                    WARNING: 2024-08-02 10:38:40 not implemented 
                    'kind'  ↦ numpy.dtype.kind, tuple of numpy.dtype.kind, <(,)>;
                            when an empty tuple, this criterion is irrelevant
    
        quantities.Quantity — in addition to the criteria for numpy.ndarray:
                    'units' ↦ pq.Quantity, <NoData>; when NoData, this criterion
                            is irrelevant; otherwise, the descriptor value (a 
                            pq.Qyuantity) must be convertibel to what is specified
                            here)
    
        vigra.VigraArray   — in addition to the criteria for numpy.ndarray:
                    'axistags' ↦ vigra.AxisTags, <NoData>; when NoData, this
                        criterion is irrelevant
    
        pandas.Series       
                        'shape' ↦ tuple[int] <(,)>
                        'index_type' ↦ subclass of pandas.Index, <NoData>
                        'dtype' ↦ numpy.dtype, tuple of numpy.dtype <(,)>
    
        pandas.DataFrame
                        'shape' ↦ tuple[int] <(,)>
                        'index_type' ↦ subclass of pandas.Index, <NoData>
                        'columns_type' ↦ subclass of pandas.Index, <NoData>
    

    
        NOTE: Validation is performed in the following order:
        
        1) if args contains types or str elements that can be resolved to types, 
            validation fails when either:
            
                a) value is NOT an instance of any of the specified types 
                    (checked using 'isinstance' builtin)
                    
                b) value is a type and is NOT a subclass of any of the specified
                    types (checked using the 'issubclass' builtin)
                    
        2) if args contains predicate functions, the validation fails when either
            predicate return False
            
            
        3) if value is hashable, validation fails if it is not among the hashable
        elements in args
        
        4) if value is not hashable, validation fails if id(value) is not among
        the id() of the non-hashable elements in args
        
        5) if additional criteria are given in kwargs:
        
            validation fails when:
            
            a) type(value) is not among the keys of kwargs, OR
            
            b) properties of value are distinct from those specified in the 
            additional criteria (see table above)
            
        An exception is raised when the validation fails.
        
        To bypass any of (1-4) simply omit those elements in *args;
        
        To bypass (5) simply omit any kwargs.
        
        To check for a type regardless of any additional property, one can:
        
        a) pass the type as argument
        
        e.g. DescriptorGenericValidator(np.ndarray)
        
        b) pass a dict with the type name as key, mapped to an empty dict
        
        e.g. DescriptorGenericValidator({"np.ndarray": {}})
        
        CAUTION: passing the type as a named argument is a syntax error:
        
        DescriptorGenericValidator(np.ndarray = {})
        --> SyntaxError: expression cannot contain assignment, perhaps you meant "=="?
        
            
        """
        self.private_name = f"_{name}_"
        self.public_name = name
        
        # NOTE: predicates must be unary predicates; 
        # otherwise, they will raise exceptions when called
        self.predicates = set()
        self.types = set() # allowed value types
        # self.hashables = set() # values for hashables (can be used as keys)
        # self.non_hashables = set() # values for non-hashables - referenced by their id()
        # self.dcriteria = dict() # dictionary of criteria:
                                
        self._allow_none_ = kwargs.get("allow_none", True)
        
        for a in args: # tease these apart
            if inspect.isfunction(a):
                self.predicates.add(a)
                
            elif isinstance(a,type):
                self.types.add(a)
                
        dcriteria = kwargs.pop("criteria", dict())
                
        if len(dcriteria) and all(isinstance(k, type) and isinstance(v, dict)for k,v in dcriteria.items()):
            self.dcriteria = dcriteria
        else:
            self.dcriteria = dict()
            
    @property
    def allow_none(self):
        return self._allow_none_
    
    @allow_none.setter
    def allow_none(self, val:bool):
        self._allow_none_ = val is True
        
    def validate(self, value):
        """Validate `value` against the criteria set in __init__"""
        
        # NOTE: 2024-08-01 10:46:58 Explannation of what is being done here
        #
        # 1) check if there are contraints on the range of acceptable object 
        #   types that the descriptor can accept (self.types); if there are,
        #   then check that the supplied value is of one of these types (or
        #   inherits from them)
        #
        #    optionally, allow a None to be passed (is self.allow_none)
        #
        #    also, if the value to be validate is actually a `type`, then check
        #    if it inherits from any of the self.types
        
        value_type = type(value)
        
        if len(self.types):
            comparand = tuple(self.types)
            if self.allow_none:
                comparand = comparand + (type(None),)
                
            if isinstance(value, type):
                if not issubclass(value, comparand):
                    raise AttributeError(f"{self.__class__.__name__}: For {self.private_name} a subclass of: {comparand} was expected; got {value.__name__} instead")
            
            if not isinstance(value, comparand):
                raise AttributeError(f"{self.__class__.__name__}: For descriptor '{self.public_name}' ('{self.private_name}') one of the types: {comparand} was expected; got {type(value).__name__} instead")
            
        # NOTE: 2021-11-30 10:42:08
        # it makes sense to validate further, only when allow_none is False
        if not self.allow_none:
            if len(self.predicates):
                if not functools.reduce(operator.and_, self.predicates, True):
                    raise AttributeError(f"{self.__class__.__name__}: Unexpected value for {self.private_name}: {value}")
                
            #  NOTE: 2024-08-01 15:14:12 what's this for ?!?
#             if is_hashable(value) and len(self.hashables):
#                 if value not in self.hashables:
#                     raise AttributeError(f"{self.__class__.__name__}: Unexpected value for {self.private_name}: {value}")
#                     
#             if not is_hashable(value) and len(self.non_hashables):
#                 if id(value) not in self.non_hashables:
#                     raise AttributeError(f"{self.__class__.__name__}: Unexpected value for {self.private_name}: {value}")
                
            if len(self.dcriteria):
                # check to see if type of value is a key in criteria
                # value has already passed initial validation by type
                criteria = tuple(v for k, v in self.dcriteria.items() if is_type_or_subclass(value, k))
                criterion = dict()
                if len(criteria) and all(isinstance(c, dict) for c in criteria):
                    for crit in criteria:
                        criterion.update(crit)
                        
                self._check_value_special_criteria_(value, criterion)
                
    def _check_value_special_criteria_(self, value, crit:dict):
        from core.utilities import unique
        from core.quantities import units_convertible
        
        if len(crit) == 0:
            return
        
        if isinstance(value, (str, bytes, bytearray, deque, list, tuple, dict)):
            c = crit.get("len", NoData)
            if isinstance(c, int) and c >= 0:
                if len(value) != c:
                    raise AttributeError(f"Unexpected length of {type(value).__name__}; expecting {c}, got {len(value)}")
                
            if isinstance(value, (deque, list, tuple, dict)):
                c = crit.get("types", tuple())
                
                if isinstance(c, type) or (isinstance(c, tuple) and len(c) and all(isinstance(c_, type) for c_ in c)):
                    if isinstance(value, (deque, list, tuple)):
                        if not all(isinstance(e, c) for e in value):
                            raise AttributeError(f"Collection's elements have unexpected types. Expecting {c}, got {tuple(type(e).__name__ for e in value)}")
                    
                    if isinstance(value, dict):
                        if not all(isinstance(v, c) for v in value.values()):
                            raise AttributeError(f"Mapping's values have unexpected types. Expecting {c}, got {tuple(type(v).__name__ for v in value.values())}")

                if isinstance(value, dict):
                    c = crit.get("key_types", tuple())
                    v_keys = unique(tuple(value.keys()))
                    if isinstance(c, type) or (isinstance(c, tuple) and len(c) and all(isinstance(c_, type) for c_ in c)):
                        if not all(isinstance(k, c) for k in v_keys):
                            raise AttributeError(f"Mapping's keys have unexpected types. Expecting {c}, got {tuple(type(v).__name__ for v in v_keys)}")
                        
                    c = crit.get("keys", tuple())
                    if isinstance(c, tuple) and len(c):
                        c_keys = unique(tuple(c))
                        if v_keys != c_keys():
                            raise AttributeError(f"Mapping's keys ({v_keys}) do not match the criterion ({c_keys})")
                        
                    c = crit.get("mapping", dict())
                    if isinstance(c, dict) and len(c):
                        c_keys = unique(tuple(c.keys()))
                        if v_keys != c_keys():
                            raise AttributeError(f"Mapping's keys ({v_keys}) do not match the criterion ({c_keys})")
                        
                        for k in v_keys:
                            if isinstance(c[k], type) or (isinstance(c[k], tuple) and len(c[k]) and all(isinstance(c_, type) for c_ in c[k])):
                                if not isinstance(value[k], c[k]):
                                    raise AttributeError(f"Key {k} expected to be mapped to a type in {c[k]}; instead got {type(value[k]).__name__}")
                        
                        
        if isinstance(value, np.ndarray):
            c = crit.get("ndim", NoData)
            
            if isinstance(c, int) and c >= 0:
                if value.ndim != c:
                    raise AttributeError(f"Expecting an array with {c} dimensions; instead, got {value.ndim}")
                
            c = crit.get("shape", tuple())
            
            if isinstance(c, tuple) and len(c) and all(isinstance(c_, int) and c_ >= 0 for c_ in c):
                if value.shape != c:
                    raise AttributeError(f"Expecting an array with shape {c}; instead, got {value.shape}")
                
            c = crit.get("dtype", tuple())
            
            if isinstance(c, np.dtype):
                if not np.issubdtype(value.dtype, c):
                    raise AttributeError(f"Expecting an array with dtype inheriting from {c}; got {value.dtype} instead")
            
            elif isinstance(c, tuple) and len(c) and all(isinstance(c_, np.dtype)):
                if not any(np.issubdtype(value.dtype, c_) for c_ in c):
                    raise AttributeError(f"Expecting an array with dtype inheriting from one of {c}; got {value.dtype} instead")
                
            if isinstance(value, pq.Quantity):
                c = crit.get("units", NoData)
                
                if isinstance(c. pq.Quantity):
                    if not units_convertible(value, c):
                        raise AttributeError(f"Value units {value.units} are incompatible with {c}")
                    
            if isinstance(value, vigra.VigraArray):
                c = crit.get("axistags", NoData)
                
                if isinstance(c, vigra.AxisTags):
                    if value.AxisTags != c:
                        raise AttributeError(f"Expecting c{ axistags}; got {value.axistags} instead")
                
        if isinstance(value, (pd.Series, pd.DataFrame)):
            c = crit.get("shape", tuple())
            
            if isinstance(c, tuple) and len(c) and all(isinstance(c_, int) and c_ >= 0 for c_ in c):
                if value.shape != c:
                    raise AttributeError(f"Expecting {type(value).__name__} with shape {c}; instead, got {value.shape}")
                
            c = crit.get("index_type", NoData)
            if isinstance(c, type) and issubclass(c, pd.Index):
                if not isinstance(value.index, c):
                    raise AttributeError(f"Invalid index type ({type(value.index).__name__}); expecting {c}")
                
            if isinstance(value, pd.Series):
                c = crit.get("dtype", tuple())
                if isinstance(c, np.dtype):
                    c = (c,)
                if isinstance(c, tuple) and len(c) and all(isinstance(c, np.dtype)):
                    if not any(np.issubdtype(value.dtype, d) for d in c):
                        raise AttributeError(f"Invalid dtype ({value.dtype}); expecting {c}")
                    
            if isinstance(value, pd.DataFrame):
                c = crit.get("columns_type", NoData)
                if isinstance(c, type) and issubclass(c, pd.Index):
                    if not isinstance(value.columns, c):
                        raise AttributeError(f"Invalid columns type ({type(value.columns).__name__}); expecting {c}")
                

class ContextExecutor(ContextDecorator):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
    
class Timer(object):
    """Recipe 13.13 "Making a Stopwatch Timer" in Python Cookbook 3rd Ed. 2013
    """
    def __init__(self, func = time.perf_counter):
        self.elapsed = 0.0
        self._func = func
        self._start = None
        
    def start(self):
        if self._start is not None:
            raise RuntimeError("Already started")
        
        self._start = self._func()
        
    def stop(self):
        if self._start is None:
            raise RuntimeError("Not started")
        
        end = self._func()
        
        self.elapsed += end - self._start
        self._start = None
        
    def reset(self):
        self.elapsed = 0.0
        
    @property
    def running(self):
        return self._start is not None
    
    def __enter__(self, *args):
        # for use as context manager
        self.start()
        return self
    
    def __exit__(self):
        # for use as context manager
        self.stop()
        
class SpecFinder(importlib_abc.MetaPathFinder):
    """
    See https://stackoverflow.com/questions/62052359/modulespec-not-found-during-reload-for-programmatically-imported-file-in-differe
    """
    def __init__(self, path_map:dict):
        self.path_map = path_map
        
    def find_spec(self, fullname, path, target=None):
        if fullname in self.path_map:
            return importlib.util.spec_from_file_location(fullname, self.path_map[fullname])
        
    def find_module(self, fullname, path):
        return
        
# ### BEGIN module functions

def signature2Dict(sig, name:typing.Optional[str]=None, 
                   qualname:typing.Optional[str]=None,
                   module:typing.Optional[str]=None,
                   allstr:typing.Optional[bool]=False) -> Bunch:
    """A dictionary-like presentation of an inspect.Signature object.
    
    Useful especially in generic initialization of objects based 
    on the signatures of their `__init__` or `__new__` methods, but also
    to store the signature of user-defined callables in a human-readable
    way (e.g. using json - see iolib.jsonio - etc.)
    
    For details on Signature objects see the documentation for Python's
    'inspect' module.
    
    Parameters:
    -----------
    sig: a callable (preferably), or an inspect.Signature object
    
    name: str, optional, default None; 
        This should be the callable's __name__ attribute
        
        REQUIRED when 'sig' is a Signature object
        
    qualname:str, optional, default None; 
        This should be the callable's __qualname__ attribute
        
        REQUIRED when 'sig' is a Signature object
        
    module: str, optional, default is None
        This should be the name of the module where the function is 
        defined (callable's __module__ attribute)
        
        REQUIRED, when 'sig' is a Signature object.
        
    Returns:
    --------
    
    a traitlets.Bunch object with the following attributes:
    
    'name': str - the name of the callable or None
    
    'qualname': str - the qualified name of the callable or None
    
    'module': str - the module name where the callable was defined, 
            or None
    
    'positional': dict; maps name: annotation for those parameters that are
        positional-only (BEFORE '/' in the parameters list if the callable)
        
        These parameters are of the inspect.Parameter.POSITIONAL_ONLY kind
    
    'named': dict; maps name to the tuple(default value, type) for the 
        positional or keyword parameters of the callable.
        
        These parameters are of inspect.Parameter.POSITIONAL_OR_KEYWORD kind.
        
        The default value for the positional or keyword parameters without a 
        default value is set to dataclasses.MISSING.
        
        This is because the distinction between a positional and keyword
        parameter is somewhat blurred, see 'About function parameters in Python'
        below.
                
    'varpos': dict; maps name: None, with the name of the var-positional
        parameter of the callable (e.g. 'args' when the callable signature
        includes `*args`).
        
        These parameters are of the inspect.Parameter.VAR_POSITIONAL kind.
        
    'kwonly': dict; maps name to the tuple (default_value, type) for the 
        keyword only parameters (i.e., those that can only be passed as keywords,
        and hence they are after * or var-positional parameters, AND before
        var-keyword parameters, in the signature).
        
        These parameters are of the inspect.Parameter.KEYWORD_ONLY kind.
        
    'varkw': dict - mapping of name: None, with the name of the var-kweyword
        parameter if the callable (e.g. 'kwargs' when the callable signature
        includes `**kwargs`)
        
        These parameters are of the inspect.Parameter.VAR_KEYWORD kind.
        
    'returns': type, if the callable signature has an annotated return, 
        or `inspect._empty` otherwise
    
    
    About function parameters in Python:
    ====================================
    Python allows function signatures such as the following: 
    
    f(a, b, /, c, d=3, e=5, *args, f=6, g=7, **kwargs)
    
    where:
    
    'a', 'b' are POSITIONAL_ONLY; these are passed BEFORE the '/' in the 
        parameters list.
        
    NOTE: if '/' is missing, then there are NO POSITIONAL_ONLY parameters.
    
    'c' is positional but is classified as POSITIONAL_OR_KEYWORD, although it
        doesn't have a default value.
        
    'd', 'e' are positional parameters with default value ('keyword'-like)
        therefore they are also classified as POSITIONAL_OR_KEYWORD.
        
    NOTE: POSITIONAL_OR_KEYWORD parameters ('c', 'd', 'e' in this example)
    always appear AFTER the '/' in the parameters list, and BEFORE the varpos
    parameter, '*args' or '*' (see below for the latter form, '*').
    
    If '/' is missing from the parameters list then ALL parameters BEFORE the
    varpos ('*args' or '*') are POSITIONAL_OR_KEYWORD.
        
    'f', 'g' are KEYWORD_ONLY (i.e. they MUST have a default value even if it is
        None).
        
    NOTE: KEYWORD_ONLY parameters are passed AFTER the varpos parameter ('*args'
        or '*') and BEFORE the var-keyword parameter '**kwargs'.
        
        The '*' varpos parameter indicates that there are no varpos parameters
        in the signature, but what follows are KEYWORD_ONLY parameters.
            
        
    
    """
    if isinstance(sig, Signature):
        if not isinstance(name, str) or len(name.strip()) == 0:
            raise ValueError(f"With Signature objects, 'funcname' is REQUIRED; got {name} instead")
    
        if not isinstance(qualname, str) or len(qualname.strip()) == 0:
            raise ValueError(f"With Signature objects, 'qualname' is REQUIRED; got {qualname} instead")
    
        if not isinstance(module, str) or len(module.strip()) == 0:
            raise ValueError(f"With Signature objects, 'modname' is REQUIRED; got {module} instead")
    
    if isinstance(sig, CALLABLE_TYPES):
        name = sig.__name__
        if hasattr(sig, "__qualname__"):
            qualname = sig.__qualname__
        else:
            # 'Boost.Python.function' object has no attribute '__qualname__'
            # and there may be others…
            qualname = sig.__name__
        module = getattr(sig, "__module__", None)
        
        # FIXME: 2022-10-07 23:19:18 
        # no signature found for Boost.Python.function objects
        # …and may be others too…
        # since I cannot easily fix this, best is to avoid calling this
        sig = inspect.signature(sig)
        
    if not isinstance(sig, Signature):
        raise TypeError(f"Expecting a Signature object, a function, or a method; got {type(sig).__name__} instead")
    
    if not isinstance(name, str) or len(name.strip()) == 0:
        raise RuntimeError(f"'name' must be a non-empty str")
        
    if not isinstance(qualname, str) or len(qualname.strip()) == 0:
        raise RuntimeError(f"'qualname' must be a non-empty str")
        
    #if not isinstance(module, str) or len(module.strip()) == 0:
        #raise RuntimeError(f"'module' must be a non-empty str")
        
    posonly_params  = Bunch()    # POSITIONAL_ONLY
    named_params    = Bunch()    # POSITIONAL_OR_KEYWORD
    varpos_params   = Bunch()    # VAR_POSITIONAL
    kwonly_params   = Bunch()    # KEYWORD_ONLY
    varkw_params    = Bunch()    # VAR_KEYWORD
    
    for parname, val in sig.parameters.items():
        #print("parameter name:", parname, "value:", val, "kind:", val.kind, "default:", val.default, "annotation:", val.annotation)
        
        default = val.default
        annotation = str(val.annotation) if allstr else val.annotation
        
        if val.kind is Parameter.POSITIONAL_ONLY:
            posonly_params[parname] = annotation
            
        elif val.kind is Parameter.POSITIONAL_OR_KEYWORD:
            if val.kind is Parameter.VAR_KEYWORD:
                varkw_params[parname] = annotation
                
            elif val.kind is Parameter.VAR_POSITIONAL:
                varpos_params[parname] = annotation
                
                
            elif val.kind is Parameter.KEYWORD_ONLY:
                kwonly_params[parname] = (default, annotation)
                
            else:
                named_params[parname] = (default, annotation)
                
        elif val.kind is Parameter.VAR_KEYWORD:
            varkw_params[parname] = annotation
            
        elif val.kind is Parameter.VAR_POSITIONAL:
            varpos_params[parname] = annotation
            
        elif val.kind is Parameter.KEYWORD_ONLY:
            kwonly_params[parname] = (default, annotation)
                
    return Bunch(name = name, qualname = qualname, module = module,
                         positional = posonly_params, named = named_params, 
                         varpos = varpos_params, kwonly=kwonly_params, varkw = varkw_params,
                         returns = sig.return_annotation)

def makeSignature(dct:Bunch) -> Signature:
    parameters = list()
    for p, val in dct.positional.items():
        # no default value for these ones
        parameters.append(Parameter(p, Parameter.POSITIONAL_ONLY, annotation = val))
        
    for p, val in dct.named.items():
        parameters.append(Parameter(p, Parameter.POSITIONAL_OR_KEYWORD, default=val[0],
                                    annotation=val[1]))
        
    for p, val in dct.varpos.items():
        parameters.append(Parameter(p, Parameter.VAR_POSITIONAL, annotation=val))
        
    for p, val in dct.kwonly.items():
        parameters.append(Parameter(p, Parameter.KEYWORD_ONLY, default=val[0], annotation=val[1]))
        
    for p, val in dct.varkw.items():
        parameters.append(Parameter(p, Parameter.VAR_KEYWORD, annotation=val))
        
        
    return Signature(parameters, return_annotation = dct.returns)
        
        

#def sig2func(dct):
    ## FIXME/TODO 2021-12-22 23:38:58
    #return

def signature2Str(f:typing.Union[types.FunctionType, inspect.Signature, Bunch], \
                        as_constructor:bool=False):
    """Turns a signature dict into an executable str.
    
    Parameters: 
    ----------
    f: function, inspect.Signature, or traitlets.Bunch (the latter being the 
        result of a signature2Dict() call)
        
    """
    if isinstance(f, (types.FunctionType, inspect.Signature)):
        f = signature2Dict(f)
        
    elif not isinstance(f, Bunch):
        raise TypeError(f"Expecting a function, a function Signature, or a traitlets.Bunch; got {type(f).__name__} instead")
    
    if f.name in ("__init__", "__new__"):
        as_constructor = True
        
    if as_constructor:
        clsname = f.qualname.split(".")[0]
        func = [".".join([f.module, clsname])]
    else:
        func = [".".join([f.module, f.qualname])]
    func.append("(")
    params = list(f.positional.keys())
    if len(params):
        params.append("/")
    params.extend(list(f.named.keys()))
    params.extend([f"*{argname}" for argname in f.varpos.keys()])
    params.extend([f"**{argname}" for argname in f.varkw.keys()])
    func.append(", ".join(params))
    func.append(")")
    
    return "".join(func)

def printStyled(s:str, color:str='yellow', bright:bool=True):
    c = getattr(colorama.Fore, color.upper())
    pre = f"{c}{colorama.Style.BRIGHT}" if bright else c
    return f"{pre}{s}{colorama.Style.RESET_ALL}"

def scipywarn(message, category=None, stacklevel=1, source=None, out=None):
    from warnings import (filters, defaultaction)
    if isinstance(message, Warning):
        category = message.__class__
    # Check category argument
    if category is None:
        category = UserWarning
    if not (isinstance(category, type) and issubclass(category, Warning)):
        raise TypeError("category must be a Warning subclass, "
                        "not '{:s}'".format(type(category).__name__))
    try:
        if stacklevel <= 1 or _is_internal_frame(sys._getframe(1)):
            # If frame is too small to care or if the warning originated in
            # internal code, then do not try to hide any frames.
            frame = sys._getframe(stacklevel)
        else:
            frame = sys._getframe(1)
            # Look for one frame less since the above line starts us off.
            for x in range(stacklevel-1):
                frame = _next_external_frame(frame)
                if frame is None:
                    raise ValueError
    except ValueError:
        globals = sys.__dict__
        filename = "sys"
        lineno = 1
    else:
        globals = frame.f_globals
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
    if '__name__' in globals:
        module = globals['__name__']
    else:
        module = "<string>"
    registry = globals.setdefault("__warningregistry__", {})
    
    # this from warn_explicit
    # ### BEGIN
    if module is None:
        module = filename or "<unknown>"
        if module[-3:].lower() == ".py":
            module = module[:-3] # XXX What about leading pathname?
    if registry is None:
        registry = {}
    # if registry.get('version', 0) != _filters_version:
    #     registry.clear()
    #     registry['version'] = _filters_version
    if isinstance(message, Warning):
        text = str(message)
        category = message.__class__
    else:
        text = message
        message = category(message)
    key = (text, category, lineno)
    # Quick test for common case
    if registry.get(key):
        return
    # Search the filters
    for item in filters:
        action, msg, cat, mod, ln = item
        if ((msg is None or msg.match(text)) and
            issubclass(category, cat) and
            (mod is None or mod.match(module)) and
            (ln == 0 or lineno == ln)):
            break
    else:
        action = defaultaction
    # Early exit actions
    if action == "ignore":
        return
    
    import linecache
    # linecache.getlines(filename, module_globals)
    linecache.getlines(filename, globals)

    if action == "error":
        raise message
    # Other actions
    if action == "once":
        registry[key] = 1
        oncekey = (text, category)
        if onceregistry.get(oncekey):
            return
        onceregistry[oncekey] = 1
    elif action == "always":
        pass
    elif action == "module":
        registry[key] = 1
        altkey = (text, category, 0)
        if registry.get(altkey):
            return
        registry[altkey] = 1
    elif action == "default":
        registry[key] = 1
    else:
        # Unrecognized actions are errors
        raise RuntimeError(
              "Unrecognized action (%r) in warnings.filters:\n %s" %
              (action, item))
    # ### END
    
    # Print message and context
    msg = WarningMessage(message, category, filename, lineno, file=out, source=source)
    _myshowarning(msg)
    
def _myshowarning(msg:WarningMessage):#, category, filename, lineno, file=None, line=None):
    # msg = WarningMessage(message, category, filename, lineno, file, line)
    file = msg.file
    if file is None:
        file = sys.stderr
        if file is None:
            # sys.stderr is None when run with pythonw.exe:
            # warnings get lost
            return
    category = msg.category.__name__
    if sys.platform == "win32":
        s =  f"In {msg.filename}, line {msg.lineno}: \n{category} {msg.message}\n"
    else:
        s =  f"In {msg.filename}, line {msg.lineno}: \n\x1b[0;33m{category}\x1b[0m: {msg.message}\n"
    # s =  f"{msg.filename}:{msg.lineno}:\n\x1b[0;33;47m{category}\x1b[0m:\n {msg.message}\n"
    try:
        file.write(s)
    except:
        pass
    
def showwarning(message, category, filename, lineno, file=None, line=None):
    """To replace stock Python warnings.showwarning"""
    if file is None:
        file = sys.stderr
        if file is None:
            return
        
    if isinstance(category, type):
        category = category.__name__
        
    text = f"In {filename}, line {lineno}: \n\x1b[0;33m{category}\x1b[0m: {message}\n"
                                                           
    if line is None:
        try:
            import linecache
            line = linecache.getline(filename, lineno)
        except Exception:
            # When a warning is logged during Python shutdown, linecache
            # and the import machinery don't work anymore
            line = None
            linecache = None

    if line:
        line = line.strip()
        text += f"  \x1b[0;36m{line}\x1b[0m\n"
                                         
    try:
        file.write(text)
    except OSError:
        # the file (probably stderr) is invalid - this warning gets lost.
        pass
    # return text
    
# def formatwarning(message, category, filename, lineno, line=None):
#     """To replace stock Python warnings.formatwarning
#     TODO
#     Do NOT use yet
#     """
#     s =  f"{filename}:{lineno}: {category}: {message}\n"
#     return s
        
def term_has_colors():
    if "NO_COLOR" in os.environ:
        return False
    if "CLICOLOR_FORCE" in os.environ:
        return True
    return sys.stdout.isatty()

def test_ANSI():
    RESET = "\x1b[0m"
    print("To reset attributes: \\x1b[0m\n")
    for i in range(0, 8):
        print("\x1b[1;3{0}m\\x1b[1;3{0}m{1} \x1b[0;3{0}m\\x1b[0;3{0}m{1} "
            "\x1b[1;4{0};3{0}m\\x1b[1;3{0};4{0}m{1}".format(i, RESET))
        
    print("Test other characters")
    print("\x1b[3;37m{0}{1}".format("italic", RESET))
    print("\x1b[4;37m{0}{1}".format("underline", RESET))
        
def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
    log = file if hasattr(file, "write") else sys.stderr
    traceback.print_stack(file=log)
    log.write(warnings.formatwarning(message, category, filename, lineno, line))
    
def deprecation(msg):
    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    
def get_func_param_types(func:typing.Callable):
    """Quick'n dirty parser of function parameter types
    
    Returns a dict: param_name ↦ tuple(type_or_types, kind), where:
    • param_name (str) is the name of the parameter
    
    • type_or_types is the type (or types) of the parameter
    
    • kind is the kind of the parameter (see inspect.Parameter for details)
    
        As a remainder, the parameter kinds in Python are:
    
Kind:                               Example:
---------------------------------------------------------------------------
Parameter.POSITIONAL_ONLY           'a' in foo(a, /, b, c = 3, …)
Parameter.POSITIONAL_OR_KEYWORD     'b' and 'c' in foo(a, /, b, c = 3. …)
Parameter.VAR_POSITIONAL            'args' in bar(*args, b, c=0, …)
Parameter.KEYWORD_ONLY              'b' and 'c' in bar(*args, b, c=0, …)
Parameter.VAR_KEYWORD               'kwargs' in baz(a, b, **kwargs)
    
    
    """
    if isinstance(func, functools.partial):
        fn = func.func
        pargtypes = tuple(type(a) for a in func.args)
    else:
        pargtypes = ()
        fn = func
        
    params = inspect.get_annotations(fn)
    
    signature = inspect.signature(fn)
    
    ret = dict()
    
    for name, ptype in params.items():
        if name == "return": # skip the return annotation if present
            continue
        # print(f"prog.get_func_param_types name = {name}")
        kind = signature.parameters[name].kind
        if isinstance(ptype, type):
            t = ptype
            
        elif isinstance(ptype, (tuple, list)) and all(isinstance(t, type) for t in ptype):
            t = tuple(ptype)
            
        elif type(ptype).__name__ in dir(typing):
            t = typing.get_origin(ptype)
            if t.__name__ in dir(typing):
                t = typing.get_args(ptype)
                
        else:
            warnings.warn(f"Cannot parse the type of {name} parameter")
            
        if (isinstance(t, (tuple, list)) and all(t_ not in pargtypes for t_ in t)) or (t not in pargtypes):
            ret[name] = (t, kind)
        
    return ret
    
def iter_attribute(iterable:typing.Iterable, 
                   attribute:str, 
                   silentfail:bool=True):
    """Iterator accessing the specified attribute of the elements in 'iterable'.
    Elements lacking the specified attribute yield None, unless 'silentfail' is 
    False.
    
    Positional parameters:
    ======================
    iterable: An iterable

    attribute:str The name of the attribute that is sought

    silentfail:bool, optional (default is True)
        When True, elements that lack the attribute yield None; otherwise, an
        AttributeError is raised when such an element is found in 'iterable'.
        
    Returns:
    ========
    Generator expression
    
    """
    if silentfail:
        return (getattr(item, attribute, None) for item in iterable)
    else:
        return (getattr(item, attribute) for item in iterable)
    
def filter_type(iterable:typing.Iterable, klass:typing.Type):
    """Iterates elements of 'iterable' that are of type specified by 'klass'
    
    Parameters:
    ===========
    iterable: An iterable
    klass: a type
    """
    return filter(lambda x: isinstance(x, klass), iterable)

def filterfalse_type(iterable:typing.Iterable, klass:typing.Type):
    """The negated version of filter_type.
    Iterates elements that are NOT of type specified in 'klass'

    Parameters:
    ===========
    iterable: An iterable
    klass: a type
    """
    return filter(lambda x: not isinstance(x, klass), iterable)

def filter_attr(iterable:typing.Iterable, 
                op:typing.Callable[[typing.Any, typing.Any], bool] = operator.and_, 
                indices:bool = False, 
                indices_only:bool = False, 
                exclude:bool = False,
                **kwargs):
    """Filter an iterable using predicates applied to attributes of its elements.
    
    This is an enhanced version of filter_attribute. Furthermore, it fails
    silently if no element of the iterable satisfies the predicate(s).
    
    At least one predicate should be given in **kwargs (see below), to test for
    the value of an attribute of the elements in 'iterable'.
    
    When there are several predicates, their results can be tested for truth value
    using the logial operator specified in 'op'.
    
    Parameters:
    ==========
    iterable: an iterable
    
    op: builtin, or user-defined binary predicate function or method.
        Optional, default is operator.and_
        
        This must have the form: f(x,y) -> bool and is used to collapse the
        resutls from several predicates in kwargs into one boolean value.
    
    indices:bool, optional (default is False)
        When False (default), returns an iterator through the elements of the
            iterable that satisfy the predicate(s) in kwargs (see below)
            
        When True, also gives access to the indices, inside the iterable, of the 
            elements that satisfy the predicates in kwargs. Depending on the 
            'indices_only' flag (see below), this can be:
                
                * an iterator through tuples (index, element) when index_only is
                    False (the default)
                
                * an iterator through int indices, when indices_only is True.
                
        NOTE: ALL the indices of the found elements will be returned. 
            This behaviour is distinct from that of Python's list.index()
            method, which returns the index of the FIRST element found.
            
    indices_only:bool, optional (default is False)
        When True, returns an iterator through the indices of the elements that
            satisy the predicate(s)
            
        When False (default) returns an iterator through the tuples 
            (index, element) for the elements that satisfy the predicate(s)
            
        NOTE: Setting the 'indices_only' flag to True, automatically sets 'indices'
        to True as well (this will save some typing).
        
    exclude:bool, ooptioinal (default is False)
        When True, the function NEGATES the evaluation of the predicates.
    
    Var-keyword parameters (kwargs):
    ================================
    
    Mapping of attr_name (str) ->  predicate (function or value). 
        When the attr_name is mapped to a function, this is expected to be a
        unary predicate of the form f(x) -> bool, where the comparison value for
        the attribute is hardcoded.
        
        When attr_name is mapped to any other type, the predicate will be the
        stock python's identity operator (operator.eq).
        
        CAUTION when comparing against numpy arrays one should supply a custom
        comparison function that takes into account the array shape, etc.
        
        WARNING The python's stock operator.eq DOES NOT WORK with numpy arrays!
    
    Returns:
    ========
    None; the function is a generator (yields an iterator).
    
    NOTE: When no predicates are specified (i.e. **kwargs resolves to an empty
    mapping) then, the behaviour is as detailed in the table below:
    
    'exclude'   'indices'   'indices_only'      Function yields:
    ============================================================================
        True                                        Nothing

        False   True        True                    Unfiltered index iterator
        
                True        False                   Unfiltered iterator (index, element)

        False   False       False                   Unfiltered element iterator
        
    Example 1.:
    ===========
    
    Let 'ephysdata' a neo.Segment where ephysdata.analogsignals contains a
    neo.AnalogSignal with the 'name' attribute being 'Im_prim2'.
    
    The named analog signal is obtained using an unary predicate that compares 
    the signal's 'name' attribute to a str. The unary predicate function 
    lambda x: x== 'Im_prim2' is passed as the keyword 'name'.
    
    The expression:
    
    [s for s in prog.filter_attr(ephysdata.analogsignals, name = lambda x: x=='Im_prim2')]
    
    constructs a list with ALL the analog signals named 'Im_prim2' (if found in 
    ephysdata.analogsignals).
    
    Example 2.:
    ===========
    Accomplishes the same as Example 1 but the name 'attribute' is compared 
    directly.
    
    [s for s in prog.filter_attr(ephysdata.analogsignals, name = 'Im_prim2')]
    
    Example 3.:
    ===========
    
    Return all analog signals with name 'Im_prim2' AND with units of picoampere
    
    [s for s in prog.filter_attr(ephysdata.analogsignals, name = 'Im_prim2', units = pq.pA)]
    
    Example 4.: 
    ===========
    Accomplishes the same thing as Example 2 but illustrates the use of an
    attribute's attribute.
    
    NOTE The use of multiple predicates as an 'unpacked' mapping ( **{...} ), 
    useful when we are using the value of a dotted attribute name (i.e., the 
    value of the attribute's attribute) as one of the predicate.
    
    In this case the attribute's attribute is units.dimensionality. 
    
    Since keyword literals cannot be dotted strings, we pass a dict that we 
    build and 'unpack' 'on the fly'.
    
    [s for s in prog.filter_attr(ephysdata.analogsignals, **{'name' : 'Im_prim2', 'units.dimensionality' : pq.pA.dimensionality})]
    
    """
    from core.datatypes import is_dotted_name
    
    
    if indices_only is True:
        indices = True
        
    if not isinstance(op, (types.FunctionType, types.LambdaType, types.BuiltinFunctionType, types.MethodType)):
        raise TypeError(f"'op' expected to be a function, buitlin, lambda or method; got {op} instead")
    
    #if not inspect.isbuiltin(op) and not inspect.isfunction(op):
        #raise TypeError(f"'op' parameter ({op}) expected to be a function or builtin; got {type(op).__name__} instead")
    
    if len(inspect.getfullargspec(op).args) != 2:
        raise TypeError(f"'op' parameter expected to be a binary function, i.e., with call syntax op(a,b)")
    
    def _check_dotted_attr_(x, attrname):
        if not is_dotted_name(attrname):
            return False
        
        obj = x
        
        for name in attrname.split('.'):
            obj = getattr(obj, name, None)
            if obj is None:
                return False
            
        return True
    
    def _tf_(x, key, f):
        """
        x: the element where attribute check takes place
        key: name of the attribute; can be a dotted attribute name
        f: predicate: function or value; when value, the comparison is made by
            way of operator.eq
        """
        if exclude:
            return (not f(operator.attrgetter(key)(x)) if _check_dotted_attr_(x,key) else not f(getattr(x, key, None))) if inspect.isfunction(f) else not operator.attrgetter(key)(x) == f if _check_dotted_attr_(x, key) else f != getattr(x, key, None)
        else:
            return (f(operator.attrgetter(key)(x)) if _check_dotted_attr_(x,key) else f(getattr(x, key, None))) if inspect.isfunction(f) else operator.attrgetter(key)(x) == f if _check_dotted_attr_(x, key) else f == getattr(x, key, None)
        
    if len(kwargs) == 0:
        if exclude is True:
            yield
        else:
            if not indices:
                yield from iterable
            else:
                if indices_only:
                    yield from range(len(list(iterable)))
                else:
                    yield from enumerate(iterable)
            
    else:
        if indices:
            if indices_only:
                yield from (i[0] for i in filter(lambda x: functools.reduce(op, (_tf_(x[1], k, f) for k,f in kwargs.items())), enumerate(iterable)))
            else:
                yield from filter(lambda x: functools.reduce(op, (_tf_(x[1], k, f) for k,f in kwargs.items())), enumerate(iterable))
        else:
            yield from filter(lambda x: functools.reduce(op, (_tf_(x, k, f) for k,f in kwargs.items())), iterable)
    
def filterfalse_attr(iterable:typing.Iterable, **kwargs):
    """'Negative' form of filter_attr.
    
    Calls filter_attr with 'exclude' set to True.
    
    """
    kwargs.pop("exclude", True)
    
    return filter_attr(iterable, exclude=True, **kwargs)
    
    #return itertools.chain.from_iterable((filter(lambda x: not f(getattr(x, n, None)) if inspect.isfunction(f) else f != getattr(x, n, None),
                                                 #iterable) for n,f in kwargs.items()))

    
def filter_attribute(iterable:typing.Iterable, attribute:str, value:typing.Any,
                     predicate:typing.Callable[...,bool]=lambda x,y: x==y, 
                     silentfail:bool=True):
    """Iterates elements in 'iterable' for which 'attribute' satisfies 'predicate'.
    
    DEPRECATED. Use filter_attr instead
    
    Positional parameters:
    ======================
    iterable: an iterable
    
    attribute: str - The name of the attribute of the elements in iterable
    
    value: object - the value against which the attribute value is compared
    
    predicate: binary callable taking two parans returning bool
        Optional; by default this is lambda x,y: x == y
        With x being the element attribute value and y being the value compared 
        against
        
    silentfail:bool Optional, default is True.
        When True, yield None if 'attribute' is not found in elements of 'iterable';
        otherwise, raise AttributeError
        
    Example:
    ========
    
    Let 'ephysdata' a neo.Segment where ephysdata.analogsignals contains a
    neo.AnalogSignal with the 'name' attribute being 'Im_prim2'.
    
    We can directly retrieve the named analog signal from its container 
    (the ephysdata.analosignals list).
    
    The expression:
    
    [s for s in prog.filter_attribute(ephysdata.analogsignals, 'name', 'Im_prim2')]
    
    will return a list with ALL the analog signals named 'Im_prim2' (if found in 
    ephysdata.analogsignals).
    
    """
    deprecation("Use prog.filter_attr")
    return filter(lambda x: predicate(getattr(x, attribute, None) if silentfail else getattr(x, attribute),
                                      value),
                  iterable)
    
def filterfalse_attribute(iterable:typing.Iterable, attribute:str, value:typing.Any, \
                     predicate:typing.Callable[...,bool]=lambda x,y: x==y,\
                     silentfail:bool=True):
    """The negated version of filter_attribute.
    DEPRECATED
    Iterates elements in 'iterable' for which 'attribute' does NOT satisfy 'predicate'.
    Positional parameters:
    ======================
    iterable: an iterable
    
    attribute: str - The name of the attribute of the elements in iterable
    
    value: object - the value against which the attribute value is compared
    
    predicate: binary callable taking two parans returning bool
        Optional; by default this is lambda x,y: x == y
        With x being the element attribute value and y being the value compared 
        against
        
    silentfail:bool Optional, default is True.
        When True, yield None if 'attribute' is not found in elements of 'iterable';
        otherwise, raise AttributeError
        
    silentfail:bool Optional, default is True.
        When True, yield None if 'attribute' is not found in elements of 'iterable';
        otherwise, raise AttributeError
        
    """
    deprecation("Use prog.filterfalse_attr")
    return filter(lambda x: not predicate(getattr(x, attribute, None) if silentfail else getattr(x, attribute),
                                          value), iterable)
    

def get_properties(obj):
    if not isinstance(obj, type):
        obj = type(obj)
        
    return [i[0] for i in inspect.getmembers(obj, lambda x: isinstance(x, property))]

def get_descriptors(obj, with_properties:bool=True):
    if not isinstance(obj, type):
        obj = type(obj)
    if with_properties:
        return [i[0] for i in inspect.getmembers(obj, lambda x: inspect.isdatadescriptor(x) or isinstance(x, property))]
    else:
        return [i[0] for i in inspect.getmembers(obj, lambda x: inspect.isdatadescriptor(x))]

def get_methods(obj):
    if not isinstance(obj, type):
        obj = type(obj)
        
    return [i[0] for i in inspect.getmembers(obj, lambda x: inspect.isfunction(x, property))]
    
def full_class_name(data):
    if not isinstance(data, type):
        data = type(data)
        
    return ".".join([data.__module__, data.__name__])    
    
def parent_types(data):
    """Returns a tuple of the immediate ancestor types of data.
    The order is as specified in the data type's definition, if data is an 
    instance, or in data definition if data is a type.
    
    Parameter:
    =========
    data: instance or type
    
    Returns:
    ========
    A tuple, possibly empty, with the immediate ancestor types of data
    
    The tuple is useful in reconstructing the data's type (or data if itself is 
    a type).
    
    """
    if not isinstance(data, type):
        data = type(data)
    types = inspect.getmro(data)[1:-1] # omit data ([0]) and object ([-1])
    anc = set(types)
    for typ in types:
        anc = anc - set(inspect.getmro(typ)[1:-1])
        
    ndx = [types.index(t) for t in anc]
    
    return tuple(types[k] for k in sorted(ndx))

def class_def(data):
    if not isinstance(data, type):
        data = type(data)
        
    ss = "(" + ", ".join([f"{p.__module__}.{p.__name__}" for p in parent_types(data)]) + ")"
    return full_class_name(data) + ss
    
                    
# ### END module functions

# ### BEGIN Decorators

def deprecated(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            deprecation("%s is deprecated" % f)
            return f(*args, **kwargs)
        
        except Exception as e:
            traceback.print_exc()
            
    return wrapper
    
def safeWrapper(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
            
        except Exception as e:
            stars = "".join(["*"]*len(f.__name__))
            print("\n%s\nIn function %s:\n%s" % (stars, f.__name__, stars))
            traceback.print_exc()
            
    return wrapper

def safeGUIWrapper(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        
        except Exception as e:
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QMessageBox()
            msgbox.setIcon(QMessageBox.Critical)
            msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            
    return wrapper

def timefunc(func):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        r = func(*args, **kwargs)
        end = time.perf_counter()
        print("{}.{} : {}".format(func.__module__, func.__name__, end-start))
        return r
    return wrapper

def processtimefunc(func):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.process_time()
        r = func(*args, **kwargs)
        end = time.process_time()
        print("{}.{} : {}".format(func.__module__, func.__name__, end-start))
        return r
    return wrapper

# NOTE: 2023-06-02 13:11:28
# this below deprecated in favour of our own with_doc class (see above)
# def with_doc_after(f):
#     """TODO/FIXME
#     see for example vigra.arraytypes._preserve_doc decorator
#     """
#     def wrap(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             func.__doc__ = "\n".join([func.__doc__, f.__doc__])
#             print(func.__doc__)
#             return func
#         return wrapper
#     return wrap
    

        
#def cli_export(name:str):
    #def wrapper(f):
        #if inspect.isfunction(f):
            #fname = f.__name__
            #if fname.startswith("slot_"):
                #exname = fname.replace("slot_", "")
                
            #elif fname.startswith("slot"):
                #exname = fname.replace("slot", ""))

            #else:
                #exname = fname
                
        #return f
    #return wrapper
            
# ### END Decorators

# ### BEGIN Context managers

@contextmanager
def timeblock(label, verbose:bool=True):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    if verbose:
        start = time.perf_counter()
        try:
            yield
        finally:
            end = time.perf_counter()
            print("{} : {}".format(label, end-start))
    else:
        yield

@contextmanager
def processtimeblock(label):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    start = time.process_time()
    try:
        yield
    finally:
        end = time.process_time()
        print("{} : {}".format(label, end-start))

# ### END Context managers

def is_hashable(x):
    """Returns True if x is hashable, i.e. hash(x) succeeds and returns an int"""
    ret = bool(getattr(x, "__hash__", None) is not None)
    if ret:
        try:
            # because some classes may override __hash__() to raise Exception 
            hash(x) 
            return True
        except:
            return False
        
    return ret

def is_type_or_subclass(x, y):
    if isinstance(x, type):
        return issubclass(x, y)
    
    return isinstance(x, y)

def __check_array_attribute__(rt, param):
    from core.quantities import units_convertible
    # print(f"rt = {rt}; param = {param}")
    if rt["default_value"] is not None:
        if not isinstance(rt["default_value"], np.ndarray):
            raise ValueError(f"Type of the default value type {type(rt['default_value']).__name__} is not a numpy ndarray")
        
    if isinstance(param, collections.abc.Sequence):
        if all(isinstance(x_, np.dtype) for x_ in param):
            if rt["default_value_dtypes"] is None:
                if isinstance(rt["default_value"], np.ndarray):
                    if rt["default_value"].dtype not in tuple(param):
                        raise ValueError(f"dtype of the default value type ({type(rt['default_value']).dtype}) is not in {param}")
                        
                rt["default_value_dtypes"] = tuple(param)

        elif all(isinstance(x_, int) for x_ in param):
            if rt["default_value_shape"] is None or rt["default_value_ndim"] is None:
                if isinstance(rt["default_value"], np.ndarray):
                    if rt["default_value"].shape != tuple(param):
                        raise ValueError(f"Default value has wrong shape ({rt['default_value'].shape}); expecting {param}")

            rt["default_value_shape"] = tuple(param)
            rt["default_value_ndim"] = len( rt["default_value_shape"])
            
    elif isinstance(param, np.dtype):
        if rt["default_value_dtypes"] is None:
            if isinstance(rt["default_value"], np.ndarray):
                if rt["default_value"].dtype != param and rt["default_value"].dtype.kind != param.kind:
                    raise ValueError(f"Wrong dtype of the default value ({rt['default_value'].dtype}); expecting {param}")
            rt["default_value_dtypes"] = param

    elif isinstance(param, int):
        if rt["default_value_ndim"] is None:
            if isinstance(rt["default_value"], np.ndarray):
                if rt["default_value"].ndim != param:
                    raise ValueError(f"Wrong dimensions for the default value ({rt['default_value'].ndim}); expecting {param}")
            
            rt["default_value_ndim"] = param

    if issubclass(rt["default_value_type"], vigra.VigraArray):
        if rt["default_value"] is not None and not isinstance(rt["default_value"], vigra.VigraArray):
            raise TypeError(f"Wrong default value type ({type(rt['default_value']).__name__}; expecting a vigra.VigraArray")
                            
        if isinstance(param, str):
            if rt["default_array_order"] is None:
                if isinstance(rt["default_value"], vigra.VigraArray):
                    if rt["default_value"].order != param:
                        raise ValueError(f"Default value has wrong array order ({rt['default_value'].order}); expecting {param} ")
                    
                rt["default_array_order"] = param
                                    
        elif isinstance(param, vigra.AxisTags):
            if rt["default_axistags"] is None:
                if isinstance(rt["default_value"], vigra.VigraArray):
                    if rt["default_value"].axistags != param:
                        raise ValueError(f"Default value has wrong axistags ({rt['default_value'].axistags}); expecting {param} ")
                    
                rt["default_axistags"] = param
            
    if issubclass(rt["default_value_type"], pq.Quantity):
        if rt["default_value"] is not None and not isinstance(rt["default_value"], pq.Quantity):
            raise TypeError(f"Wrong default value type ({type(rt['default_value']).__name__}; expecting a Python Quantity")
                        
        if isinstance(param, pq.Quantity):
            if rt["default_value_ndim"] is None:
                if isinstance(rt["default_value"], pq.Quantity) and not units_convertible(rt["default_value"].units, param.units):
                    raise ValueError(f"Default value has wrong units ({rt['default_value'].units}); expecting {param} ")
                
            rt["default_value_units"] = param
            

def __check_type__(attr_type:typing.Union[type, typing.Tuple[type]], 
                   specs:typing.Union[type, typing.Tuple[type]], 
                   exclspecs:typing.Optional[typing.Union[type, typing.Tuple[type]]] = None) -> bool:
    """Checks if attr_type is a subclass of types in specs.
    Optionally, checks that attr_type it NOT a subclass of types in 
    exclspecs.
    
    Parameters:
    -----------
    attr_type: a type or sequence of types (in the latter case, all it elements 
        will be checked)
    
    specs: a type or a tuple of types that must be a superclass of attr_type;
        It may contain `None` objects.
        (NOTE: I chose the name `specs` to avoid clashes with the `types` module)
    
    
    exclspecs: type or sequence of types that must NOT be a superclass of attr_type
    
    Returns a bool
    --------------
    
    """
    if isinstance(specs, type):
        specs = (specs,)
        
    elif not isinstance(specs, tuple) or not all(isinstance(v_, type, ) for v_ in specs if v_ is not None ):
        raise TypeError("__check_type__ expecting a type or tuple of types as second parameter")
    
    specs = tuple(s for s in specs if s is not None)
        
    if exclspecs is None:
        exclspecs = tuple()
    
    if isinstance(exclspecs, type):
        exclspecs = (exclspecs,)
        
    elif isinstance(exclspecs, tuple):
        if len(exclspecs) and not all(isinstance(e_, type) for e_ in exclspecs):
            raise TypeError("__check_type__: When a tuple, `exclspecs` must contain only types")
        
    else:
        raise TypeError(f"__check_type__: `exclspecs` expected to be a type, a tuple of types, or None; got {type(exclspecs).__name__} instead")
        
        
    if isinstance(attr_type, collections.abc.Sequence) and len(attr_type):
        if isinstance(exclspecs, tuple) and len(exclspecs) and all(isinstance(e_, type) for e_ in exclspecs):
            return all(isinstance(v_, type) and issubclass(v_, specs) and not issubclass(v_, exclspecs) for v_ in attr_type if v_ is not None )
        
        return all(isinstance(v_, type) and issubclass(v_, specs) for v_ in attr_type if v_ is not None )
    
    elif isinstance(attr_type, type):
        if isinstance(exclspecs, tuple) and len(exclspecs) and all(isinstance(e_, type) for e_ in exclspecs):
            return isinstance(attr_type, type) and issubclass(attr_type, specs) and not issubclass(attr_type, exclspecs)
        
        return isinstance(attr_type, type) and issubclass(attr_type, specs)
    
    return False

def parse_descriptor_specification(x:tuple, allow_none:bool=True):
    pass
                
# NOTE: 2024-07-29 09:43:00
# overhauled
def parse_descriptor_specification_old(x:tuple, allow_none:bool=True):
    """
    x: tuple with attribute name, attribute type(s), collection element types, array dtypes, default value
    
        In the most general case (terms in angle brackets are optional):
    
        element:        type & meaning:
        0               str: the name of the attribute
    
        1               a type or a (possibly empty) sequence of types representing
                        the acceptable type(s) of the attribute (can be augmented 
                        as below)
    
                        NOTE: numpy arrays and array-like types (including pandas
                        series and dataframes) should NOT be mixed with other 
                        types, here
    
        2               • when attribute type is a sequence type (deque, list, tuple), 
                        but NOT a str, bytes or bytearray, then x[2] is the 
                        the acceptable type or sequence of acceptable types 
                        of the the attribute elements (see below); otherwise it is 
                        ignored (and can be an empty tuple)
    
    
                        •NOTE: when x[1] is a mapping type, then x[2] can be:
                            ∘ a type -> the acceptable type of the mapping values
                            ∘ a sequence of types -> acceptable types of the mapping values
                            ∘ a mapping of type or tuple of types ↦ type or sequence of types ->
                                    acceptable key types and acceptable value types
                        
                        is the acceptable type or sequence of acceptable types) of the mapping values
                        (NOT keys — these are always any hashable type)
    
        3               when attribute type is a numpy array or pandas series/dataframe
                        this is the acceptable dtype, or a sequence of acceptable
                        dtypes; otherwise it is ignored (and can be an empty tuple)
    
        4               futher array predicates: a dict (possibly empty) with
                        the following keys: "units", "ndim", "shape", "axistags"
                        where:
    
                        units ↦ pq.Quantity or pq.UnitQuantity

                        ndim ↦ int (strictly positive, i.e., > 0)
    
                        shape ↦ tuple of ints;
                            its lenth must be equal to the value of 'ndim' if
                            'ndim' is specified, else , its length will set the 
                            value of 'ndim'
    
                        axistags ↦ vigra.AxisTags, same length as value of ndim
                                and same length as shape
    
                        NOTE: axistags is used when vigra.VigraArray is among the
                        attribute types (x[1]); when it is specified, 'axistags' 
                        length must be:
                            1) equal to 'ndim' (unless 'ndim' is absent, in which
                            case 'axistags' will set the value of 'ndim' to the
                            length of the 'axistags' object)
    
                            2) equal to the length of 'shape' (if 'shape' is
                            specified)
                        
                        
        5               the default attribute value (may be skipped; by default this is set to None)
    
    
    Returns:
    ------------
    A dictionary suitable for the `descr_params` parameter to the 
    `setup_descriptor` class method of `WithDescriptors`:
    
    'name'      ↦ str: name of the descriptor — mandatory
    'value'     ↦ object: default value of the descriptor
    'args'      ↦ tuple: acceptable value types that can be set for the descriptor;
                    by default, this is empty
    'kwargs'    ↦   'allow_none' ↦ bool <True>
                    'dcriteria'  ↦ dict <empty dict> — as detailed in the 
                                    documentation for DescriptorGenericValidator.__init__()
    
    """
    
  
    
    from core.quantities import units_convertible
    from core.datatypes import (
        TypeEnum, is_enum, is_enum_value, default_value, sequence_element_type)
    from core.utilities import (unpack, unique)
    
    if not isinstance(x, tuple):
        raise TypeError(f"Expecting a tuple, got {type(x).__name__} instead")
    
    
    # (name, value or type, type or ndims, ndims or units, units)
    attrs = SimpleNamespace(
        name=NoData,
        type_or_value=NoData,
        types=NoData,
        eltypes=NoData,
        keyvaltypes=NoData,
        dtypes=NoData,
        default=NoData,
        array_params=NoData
        )
    
    result = dict(
        name = None,
        value = None,
        args = tuple(),
        kwargs = dict(
            allow_none = allow_none,
            dcriteria  = dict()
            )
        )
    
    unpacked = unpack(x, attrs.__dict__.keys())
    # print(f"unpacked = {unpacked}")
    
    for u in unpacked:
        setattr(attrs, u[0], u[1])
    
    print(f"attrs = {attrs}")
                                        # parameters of Descriptor c'tor:
    descriptor_name = NoData            # -> name 
    descriptor_default_value = NoData   # -> defval 
    descriptor_types = NoData           # -> *args
    dcriteria = dict()                  # -> "dcriteria" keyword
    # descriptor_element_types = tuple()
    # descriptor_mapping_key_value_types = tuple()
    # descriptor_dtypes = tuple()
    # descriptor_array_params = tuple()
    
    # return attrs

    if not isinstance(attrs.name, str) or len(attrs.name.strip()) == 0:
        raise ValueError("A name for the attribute is mandatory")
    
    descriptor_name = attrs.name
    
    if attrs.type_or_value is NoData:
        descriptor_types = (str,)
        descriptor_value = ""
    
    elif isinstance(attrs.type_or_value, (tuple, list, deque, set)):
        # This may be a sequence of types, or a sequence object.
        #
        if all(isinstance(v, type) for v in attrs.type_or_value):
            # This is a collection of types, which can be either the acceptable 
            #   types of the descriptor, or the default value of the descriptor 
            #   (i.e. we want to set it to a collection of types).
            #
            # The only way to discern this is to look ahead at the attrs.types:
            #
            #   Case (A): if attrs.types is undefined (either NoData or an empty collection),
            #       then attrs.type_or_value is interpreted as a sequence
            #       of acceptable descriptor types; default values, if any are
            #       taken from attrs.default, if given, or from a default 
            #       constructor with no arguments (if it is defined, otherwise is
            #       set to None)
            #
            #   Case (B): if attrs.types is defined, then attrs.type_or_value can 
            #   only be the default descriptor value (a sequence type), and its
            #   elements must all be subclasses of attrs.types
            #
            #   In other words, if you want an attribute to be a collection of
            #   types without restriction on what those types might be, then 
            #   construct this as ("name", (int, float, str), type).
            #
            #   On the other hand, if you want to restrict the types to a limited
            #   range, then the third element should be a type or tuple of types
            #   other than "type"
            
            #   
            if (attrs.types is NoData) or (isinstance(attrs.types, (tuple, list)) and len(attrs.types) == 0):
                # first bullet above; also sets the default value
                descriptor_types = unique(tuple(attrs.type_or_value))
                
                # now try and set a default value
                if attrs.default is NoData:
                    # try to set the default value from the first type in descriptor_types
                    try:
                        defval = descriptor_types[0]()
                    except:
                        if allow_none:
                            defval = None
                        else:
                            raise DescriptorException(f"A default value cannot be inferred, and must be specified for {descriptor_types[0].__name__}")
                        
                    descriptor_default_value = defval
                    
                else:
                    if isinstance(attrs.default, descriptor_types):
                        descriptor_default_value = attrs.default
                    else:
                        raise DescriptorException(f"Specified default value {attrs.default} does not match prescribed types {descriptor_types}")
                
            elif isinstance(attrs.types, type) or (isinstance(attrs.types, (tuple, list)) and all(isinstance(t, type) for t in attrs.types)):
                # second bullet above: type_or_value says the descriptor 
                #  default value is a sequence of types, hence descriptor value 
                # type is a sequence, and its element types must be all 'type'
                #
                # then attrs.types specify acceptable class hierarchy for the types 
                # in the default value (e.g. accept (tuple, list) but not (tuple, dict))
                # 
                # CAUTION: 2024-08-02 13:31:04
                # if attrs.default is also specified, this is silently ignored;
                # if attrs.eltypes are also specified, they are silently ignored
                #
                descriptor_default_value = attrs.type_or_value
                descriptor_types = (type(descriptor_default_value),) # a sequence type
                
                # element superclasses (also types)
                checktypes = (attrs.types,) if isinstance(attrs.types, type) else tuple(attrs.types)
                
                if not all(issubclass(v, checktypes) for v in descriptor_default_value):
                    raise DescriptorException("Element type mismatch")
                
                dcriteria["types"] = unique(tuple(checktypes))
                
        else:
            # This is a collection of objects (other than types) — it is interpreted
            # as trhe descriptor's default value, and the descriptor value type is its type.
            #
            # (see above for the case where the value of the descriptor is itself 
            #   a type or a collection of types)
            #
            # furthermore, its element types must conform with attrs.types or
            # attrs.eltypes, if specified
            #
            # CAUTION: attrs.default will be silently ignored, here
            #
            # hence the descriptor_type is a sequence type
            # and its element types are specified by the attrs.types (attrs.eltypes
            # are silently ignored)
            descriptor_default_value = attrs.type_or_value # this may be an empty sequence!
            descriptor_types = (type(attrs.type_or_value), ) # tuple, or list
            
            # now, look ahead to attrs.types and see if element types are specified
            # if they are, IN THIS PARTICULAR CASE they are taken to be element
            # types; if, in addition, attrs.eltypes are also given, raise SyntaxError
            # beacuse of ambiguity
            if isinstance(attrs.types, type) or (isinstance(attrs.types, (tuple, list)) and all(isinstance(t, type) for t in attrs.types)):
                if isinstance(attrs.eltypes, type) or (isinstance(attrs.eltype, (tuple, list)) and all(isinstance(t, type) for t in attrs.eltype)):
                    raise DescriptorException(f"Ambiguous descriptor specification:\n{x}\nelement types appear to have been defined twice")
                types = (attrs.types,) if isinstance(attrs.types, type) else tuple(attrs.types)
                dcriteria["types"] = unique(types)
                
                if len(descriptor_default_value):
                    if not all(isinstance(v, types) for v in descriptor_default_value):
                        raise DescriptorException(f"Default value {descriptor_default_value} does not follw prescribed types {types}")

            else:
                # if attrs.types are not given, check attrs.eltypes
                if isinstance(attrs.eltypes, type) or (isinstance(attrs.eltypes, (tuple, list)) and all(isinstance(t, type) for t in attrs.eltypes)):
                    types = (attrs.eltypes,) if isinstance(attrs.eltypes, type) else tuple(attrs.eltypes)
                    dcriteria["types"] = unique(types)
                
                    if len(descriptor_default_value):
                        if not all(isinstance(v, types) for v in descriptor_default_value):
                            raise DescriptorException(f"Default value {descriptor_default_value} does not follow prescribed types {types}")
                        
    elif isinstance(attrs.type_or_value, type):
        # apply the same logic as for the cases A and B of a collection of types
        # TODO 2024-08-02 22:55:12 FIXME,  currently this does something else !!!
        descriptor_types = (attrs.type_or_value,)
        if attrs.default is not NoData:
            if not isinstance(attrs.default, descriptor_types):
                raise DescriptorException(f"Default value type ({type(attrs.default).__name__}) should be {descriptor_type[0].__name__}")
            
            descriptor_default_value = attrs.default
            
        else:
            try:
                descriptor_default_value = descriptor_types[0]()
            except:
                if allow_none:
                    descriptor_default_value = None
                else:
                    raise DescriptorException(f"A default value must be specified for {descriptor_types[0].__name__}")
                
        if issubclass(attrs.type_or_value, (tuple, list, deque, set, bytes, bytearray, str, dict)):
            # check for prescribed element types
            if isinstance(attrs.types, type) or (isinstance(attrs.types, (tuple, list)) and all(isinstance(t, type) for t in attrs.types)):
                if isinstance(attrs.eltypes, type) or (isinstance(attrs.eltype, (tuple, list)) and all(isinstance(t, type) for t in attrs.eltype)):
                    raise DescriptorException(f"Ambiguous descriptor specification:\n{x}\nelement types appear to have been defined twice")
                
                types = (attrs.types,) if isinstance(attrs.types, type) else tuple(attrs.types)
                dcriteria["types"] = unique(types)
                
                if len(descriptor_default_value):
                    if not all(isinstance(v, types) for v in descriptor_default_value):
                        raise DescriptorException(f"Default value {descriptor_default_value} does not follow prescribed types {types}")

            elif isinstance(attrs.eltypes, type) or (isinstance(attrs.eltypes, (tuple, list)) and all(isinstance(t, type) for t in attrs.eltypes)):
                types = (attrs.eltypes,) if isinstance(attrs.eltypes, type) else tuple(attrs.eltypes)
                dcriteria["types"] = unique(types)
            
                if len(descriptor_default_value):
                    if not all(isinstance(v, types) for v in descriptor_default_value):
                        raise DescriptorException(f"Default value {descriptor_default_value} does not follow prescribed types {types}")
                    
            if issubclass(attrs.type_or_value, dict):
                if isinstance(attrs.keyvaltypes, (tuple, list)):
                    pass
            
            if isinstance(attrs.array_params, dict) and isinstance(attrs.array_params.get("len", None), int):
                length = attrs.array_params["len"]
                if len(descriptor_default_value) != length:
                    raise DescriptorException(f"Default value {descriptor_default_value} does not match prescribed length {length}")
                dcriteria["len"] = length
                
    elif isinstance(attrs.type_or_value, (bytes, bytearray, str, set)):
        
        if attrs.default is NoData:
            if not isinstance(attrs.types, type) and not (isinstance(attrs.types, (tuple, list)) and all(isinstance(t, type) for t in attrs.types)):
                if attrs.types is NoData:
                    descriptor_types = (type(attrs.type_or_value), )
                
            descriptor_default_value = attrs.type_or_value
            # descriptor_default_value = descriptor_types[0]()
            
        else:
            if attrs.types is NoData:
                if isinstance(attrs.default, descriptor_types):
                    descriptor_default_value = attrs.default
                else:
                    raise DescriptorException(f"Specified default value {attrs.default} does not match prescribed types {descriptor_types}")
            
        if isinstance(attrs.array_params, dict) and isinstance(attrs.array_params.get("len", None), int):
            length = attrs.array_params["len"]
            if len(descriptor_default_value) != length:
                raise DescriptorException(f"Default value {descriptor_default_value} does not match prescribed length {length}")
            dcriteria["len"] = length
            
    elif isinstance(attrs.type_or_value, dict):
        descriptor_types = (type(attrs.type_or_value), )
        if not isinstance(attrs.default, NoData):
            if isinstance(attrs.default, descriptor_types):
                descriptor_default_value = attrs.default
            else:
                raise DescriptorException(f"Specified default value {attrs.default} does not match prescribed types {descriptor_types}")
            
        else:
            descriptor_default_value = descriptor_types[0]()
            
        if isinstance(attrs.array_params, dict):
            if isinstance(attrs.array_params.get("len", None), int):
                length = attrs.array_params["len"]
                if len(descriptor_default_value) != length:
                    raise DescriptorException(f"Default value {descriptor_default_value} does not match prescribed length {length}")
                dcriteria["len"] = length
            
            dict_value_types = attrs.array_params.get("types", None)
            
            if isinstance(dict_value_types, tuple) and all(isinstance(t, type) for t in dict_value_types):
                dcriteria["types"] = dict_value_types
            elif isinstance(dict_value_types, type):
                dcriteria["types"] = (dict_value_types, )
                
            # dict_key_types = 
            

#     elif __check_type__(attrs.type_or_value, ()):
#         pass
#         
#     
#     if isinstance(attrs.types, (tuple, list)):
#         descriptor_types = tuple(attrs.types)
#         
#     else:
#         descriptor_types = tuple()
#         
#     
#     if isinstance(attrs.type_or_value, type):
#         if isinstance(attrs.types, list):
#             attrs.types.append(attrs.type_or_value)
#         else:
#             attrs.types = [attrs.type_or_value]
#             
#         attrs.type_or_value = NoData # consume this
#         
#     elif isinstance(attrs.type_or_value, str):
#         try:
#             val_types = [import_item(attrs.type_or_value)]
#             if isinstance(attrs.types, list):
#                 attrs.types.extend(val_types)
#             else:
#                 attrs.types = val_types
#         except:
#             if isinstance(attrs.types, list):
#                 if str not in attrs.types:
#                     attrs.types.append(str)
#                     
#             else:
#                 attrs.types = [str]
#                     
#             attrs.default = attrs.type_or_value
#             
#         attrs.type_or_value = NoData # consume this
#         
#     elif attrs.type_or_value is not NoData:
#         attrs.default = attrs.type_or_value
#         val_type = type(attrs.default)
#         if isinstance(attrs.types, list):
#             if val_type not in attrs.types:
#                 attrs.types.append(val_type)
#         else:
#             attrs.types = [val_type]
#                 
#         attrs.type_or_value = NoData # consume this
        
    # by now, attrs.types should have been taken care of
    result["name"]  = descriptor_name
    result["value"] = descriptor_default_value
    result["args"]  = descriptor_types
    # descriptor_types = tuple()
    
    # if __check_type__(attrs.types, (str, bytes, bytearray))
#     
#     if __check_type__(attrs.types, collections.abc.Sequence, (str, bytes, bytearray)):
#         # here, attrs.eltypes should be a type or tuple of types
#         if attrs.eltypes is not NoData:
#             if isinstance(attrs.eltypes, type):
#                 descriptor_element_types = tuple(attrs.eltypes)
#             elif isinstance(attrs.eltypes, (tuple, list)) and len(attrs.eltypes) and all(isinstance(v_, type) for v_ in attrs.eltypes):
#                 descriptor_element_types = tuple(attrs.eltypes)
#                 
#             else:
#                 descriptor_element_types = tuple()
#                 
#     elif __check_type__(attrs.types, collections.abc.Mapping):
#         if attrs.keyvaltypes is NoData:
#             # use eltypes to set the acceptable value types in a mapping
#             pass
#             
            
        
    
#     # -------
#     
#     val_types = list()
#     el_types = list()
#     k_types = list() # types of keys of a mapping
#     v_types = list() # types of values in a mapping
#     a_dtypes = list() # accetpable dtypes in a numpy array or pandas Series, DataFrame, Index
#     further_array_params = {"units": MISSING, "ndims": MISSING, "shape": MISSING,
#                             "axistags":MISSING}
#     # units = list() # acceptable Quantities units for a pq.Quantity array
#     # ndims = list() # acceptable number of array dimensions (for np.ndarrays)
#     # axtags = list() # acceptable axistags for vigra arrays
#     
#     # if len(x) not in range(5,7):
#     #     raise ValueError(f"Expecting a tuple with 5 or 6 elements; instead got a {len(x)}-tuple")
#     
#     
#     if not isinstance(x[0], str):
#         raise TypeError(f"First element of a descriptor specification must be a str; got {type(x[0]).__name__} instead")
#     
#     attr_name = x[0]
#     
#     if len(x) == 2:
#         if isinstance(x[1], type):
#             val_types.append(x[1])
#             
#         elif isinstance(x[1], (tuple, list)) and len(x[1]) and all(isinstance(x_, type) for x_ in x[1]):
#             val_types += list(x[1])
#         
#     # NOTE: 2024-07-29 11:21:19 REMEMBER:
#     # list, tuple, deque -> collections.abc.Sequence < Collection < Iterable < Container
#     # dict, OrderedDict -> collections.abc.Mapping < Collection < ...
#     # np.ndarray -> collections.abc.Collection (!!!)
#     # pd.Series -> collections.abc.Collection (!!!)
#     # pd.DataFrame -> collections.abc.Collection (!!!)
#     # pf.Index  -> collections.abc.Collection (!!!)
#     
#     # if len(x) == 3:
#     
#     if any(issubclass(t, collections.abc.Sequence) and not issubclass(t, (str, bytes, bytearray)) for t in val_types):
#         if isinstance(x[2], (tuple, list)) and len(x[2]) and all(isinstance(x_, type) for x_ in x[2]):
#             el_types += list(x[2])
#             
#         elif isinstance(x[2], type):
#             el_types.append(x[2])
#             
#     if any(issubclass(t, collections.abc.Mapping) for t in val_types):
#         if isinstance(x[2], type):
#             v_types.append(x[1])
#             
#         elif isinstance(x[2], (tuple, list)) and len(x[1]) and all(isinstance(x_, type) for x_ in x[2]):
#             v_types += list(x[2])
#             
#         elif isinstance(x[2], dict) and len(x[2]):
#             for key, val in x[2].items():
#                 if isinstance(key, type):
#                     k_types.append(key)
#                 elif isinstance(key, (tuple, list)) and all(isinstance(k_, type) for k_ in key):
#                     k_types += list(key)
#                     
#                 if isinstance(val, type):
#                     v_types.append(val)
#                     
#                 elif isinstance(val, (tuple, list)) and all(isinstance(v_, type) for v_ in val):
#                     v_types += list(val)
#                     
#     if any(issubclass(t, (np.ndarray, pd.Series, pd.DataFrame, pd.Index)) for t in val_types):
#         if isinstance(x[3], np.dtype):
#             a_dtypes.append(x[3])
#             
#         elif isinstance(x[3], (tuple, list)) and len(x[3]) and all(isinstance(x_, np.dtype) for x_ in x[3]):
#             a_dtypes += list(x[3])
#             
#         if isinstance(x[4], dict) and any(k in x[4] for k in ("units", "ndim", "shape", "axistags")):
#             if any(issubclass(t, p.Quantity) for t in val_types):
#                 if "units" in x[4] and issubclass(x[4]["units"], pq.Quantity):
#                     further_array_params["units"] = x[4]["units"]
#                 else:
#                     further_array_params["units"] = pq.dimensionless
#                     
#                 
#             if "ndim" in x[4] and isinstance(x[4]["ndim"], int) and x[4]["ndim"] > 0:
#                 further_array_params["ndim"] = x[4]["ndim"]
#                 
#             if "shape" in x[4] and isinstance(x[4]["shape"], tuple) and all(isinstance(s, int) and s >=0 for s in x[4]["shape"]):
#                 shape = x[4]["shape"]
#                 
#                 ndim = further_array_params.get("ndim", MISSING)
#                 
#                 if isinstance(ndim, int):
#                     if len(shape) != ndim:
#                         raise ValueError(f"Mismatch between the specified shape: {shape} and the number of dimensions: {ndim}")
#                     
#                 else:
#                     further_array_params["ndim"] = len(shape)
#                     
#                 further_array_params["shape"] = shape
#                 
#             if any(issubclass(t, vigra.VigraArray) for t in val_types):
#                 if "axistags" in x[4] and isinstance(x[4]["axistags"], vigra.AxisTags):
#                     axistags = x[4]["axistags"]
#                     shape = further_array_params.get("shape", MISSING)
#                     ndim = further_array_params.get("ndim", MISSING)
#                     
#                     if isinstance(ndim, int):
#                         if len(axistags) != ndim:
#                             raise ValueError(f"Mismatch between the number of axistags ({len(axistags)}) and the specified number of dimensions ({ndim})")
#                     else:
#                         further_array_params["ndim"] = len(axistags)
#                     
#                     
#                     if isinstance(shape, tuple) and all(isinstance(s, int) for s in shape) and len(axistags) != len(shape):
#                         raise ValueError(f"Mismatch between the number of axistags ({len(axistags)}) and dimensions expected from shape ({len(shape)})")
#                     
#                     further_array_params["axistags"] = axistags
#             
#             
#             if len(x) == 6 and x[5]:
#                 default_value = x[5]
#                 if x[5] is not None: # and x[5] is not MISSING:
#                     assert isinstance(default_value, val_types+[type(None)]), f"Default value type ({type(default_value)} is not an instance of the acceptable types)"
#                     
#                     if isinstance(default_value, (np.ndarray, pd.Index, pd.Series, pd.DataFrame)):
#                         if len(a_dtypes):
#                             assert any(np.issubdtype(default_value, dtype) for dtype in a_dtypes), f"Default value dtype ({default_value.dtype}) is not in any hierachy of specified dtypes ({a_dtypes})"
#                             
#                         if isinstance(further_array_params["ndim"], int):
#                             assert default_value.ndim == further_array_params["ndim"], f"Mismatch between default value dimensions ({default_value.ndim}) and the number of specified dimensions ({further_array_params['ndim']})" 
# 
#                         if isinstance(further_array_params["shape"], tuple):
#                             assert default_value.shape == further_array_params["shape"], f"Mismatch between the shape of default value ({default_value.shape}) and the specified dhape ({further_array_params['shape']})"
# 
#                         if isinstance(default_value, vigra.VigraArray):
#                             if isinstance(further_array_params["axistags"], vigra.AxisTags):
#                                 assert(default_value.axistags == further_array_params["axistags"]), f"Axistags mismatch between default value ({default_value.axistags}) and the specified axistags ({further_array_params['axistags']})"
#             else:
#                 default_value = None
#                 
#     # args = val_types + [type(None)]
#     args = val_types
#     kwargs = dict()
#     kwargs["element_types"] = tuple(el_types)
#     kwargs["key_types"] = tuple(k_types)
#     kwargs["value_types"] = tuple(v_types)
#     kwargs["dtypes"] = tuple(a_dtypes)
#     kwargs["array_specs"] = further_array_params
#     kwargs["default"] = default_value
#                     
#     result = {"name": attr_name, 
#               "value": default_value, 
#               "args":tuple(args), 
#               "kwargs": kwargs}
#     
    return result
    
    
    
    
    # ---- NOTE: 2024-07-29 11:03:19 to remove to end of function definition
    
#     if len(x):
#         # set the attribute name
#         if not isinstance(x[0], str):
#             raise TypeError(f"First element of a descriptor specification must be a str; got {type(x[0]).__name__} instead")
#         
#         ret["name"] = x[0]
#         
        
    if len(x) > 1:
        # set the attribute's default value and default value type
        #
        if isinstance(x[1], str):
            try:
                val_types = [import_item(x[1])] # NOTE: import_item() def'ed in traitlets.utils.importstring
            except:
                ret["default_value"] = x[1]
                val_types = [str]
                
        elif isinstance(x[1], type):
            val_types = [x[1]]
            # ret["default_value_type"] = x[1]
            val = default_value(x[1]) # NOTE: default_value() def'ed in core.datatypes
            ret["default_value"] = val
                
        elif isinstance(x[1], (tuple, list)):
            if all(isinstance(x_, type) for x_ in x[1]): 
                # NOTE: x[1] is a tuple of types
                # this leaves ret["default_value"] as None
                val_types = list(x[1])
                # ret["default_value_type"] = x[1] # any of the types in x[1]
            else:
                # NOTE: x[1] is a tuple of instances
                val_types = list(type(x_) for x_ in x[1])
                # ret["default_value_type"] = tuple(type(x_) for x_ in x[1])
                ret["default_value"] = x[1]
            
        else:
            # x[1] is an instance
            ret["default_value"] = x[1]
            val_types = [type(x[1])]
            # ret["default_value_type"] = type(x[1])
            
    # print(f"parse_descriptor_specification default_value = {ret['default_value']}, default_value_type = {ret['default_value_type']}")
            
    if len(x) > 2: 
        # by now, the expected type of the attribute should be established,
        # whether it is None, type(None), or anything else
        #
        # x[1]
        # if __check_type__(ret["default_value_type"], (None, type(None))) or not __check_type__(ret["default_value_type"], np.ndarray):
        if not __check_type__(value_types, np.ndarray):
             # NOTE: 2023-05-17 18:30:44
             # This branch executed when ret["default_value_type"] is None, NoneType, or IS NOT a np.ndarray subclass
            if isinstance(x[2], collections.abc.Sequence):
                # x[2] is a sequence (tuple, list, deque)
                if all(isinstance(x_, type) for x_ in x[2]):
                    # all elements in x[2] are types
                    if __check_type__(ret["default_value_type"], (collections.abc.Sequence, collections.abc.Set)):
                        # here, default_value_type as parsed from x[1] is a Sequence or Set
                        # hence x[2] must specify acceptable types for the elements in the Sequence or Set
                        #
                        # The default attribute value type has been set as sequence or set:
                        #   ⇒ x[2] specifies acceptable element types
                        ret["default_element_types"] = tuple(x[2])
                        
                        # Now, check that the default attribute value (if given) 
                        #   conforms with the acceptable element types
                        if ret["default_value"] is not None:
                            if not isinstance(ret["default_value"], ret["default_value_type"]):
                                raise ValueError(f"Default value expected to be a {type(ret['default_value_type'].__name__)}; got {type(ret['default_value']).__name__} instead")
                            
                            if not all(isinstance(v_, tuple(x[2])) for v_ in ret["default_value"]):
                                raise ValueError(f"Default value expected to be contain {x[2]} elements; got {set((type(v_).__name__ for v_ in ret['default_value']))} instead")
                        
                    elif __check_type__(ret["default_value_type"], collections.abc.Mapping):
                        # here, default_value_type as parsed from x[1] is a Mapping (e.g. a dict)
                        # hence x[2] must specify acceptable types for the values in the mapping
                        #
                        # The default attribute value type has been set as a mapping
                        # ⇒ x[2] specifies acceptable types for the values of the mapping
                        #   i.e., default item types
                        ret["default_item_types"] = tuple(x[2])
                        
                        # Now, check that the default value (if given) conforms
                        #   with the acceptable item types
                        if ret["default_value"] is not None:
                            if not isinstance(ret["default_value"], collections.abc.Mapping):
                                raise ValueError(f"Default value expected to be a mapping; got {type(ret['default_value']).__name__} instead")
                            
                            if not all(isinstance(v_, tuple(x[2])) for v_ in ret["default_value"].values()):
                                raise ValueError(f"Default value expected to be contain {x[2]} items; got {set((type(v_).__name__ for v_ in ret['default_value'].values()))} instead")
                        
                    else:
                        # Here, the default value type as determined from x[1] is
                        # neither a sequence, set, nor a mapping.
                        # Check that the default value (if given) conforms - i.e., 
                        # has any of the types specified in x[2]
                        
                        if ret["default_value"] is not None:
                            if not isinstance(ret["default_value"], tuple(set(x[2]))):
                                raise ValueError(f"Type of the default value type {type(ret['default_value']).__name__} is different from the specified default value type {x[2]}")
                        
                        # Finally, overwrite the default attribute value type
                        ret["default_value_type"] = tuple(set(x[2])) # make it unique
                    
            elif isinstance(x[2], type):
                # x[2] specifies a single type
                if __check_type__(ret["default_value_type"], (collections.abc.Sequence, collections.abc.Set)):
                    # If attribute value type is set as a sequence or set, then 
                    # x[2] is considered to specify the element type in the sequence or set
                    #
                    # Verify that the default value (if given) conforms (i.e., is a sequence or set)
                    # but allow for the default value to be empty, or None !
                    if isinstance(ret["default_value"], ret["default_value_type"]):
                        # if default value is NOT empty, check its elements are of
                        # the type specified in x[2]
                        if len(ret["default_value"]) > 0:
                            if not all(isinstance(v_, x[2]) for v_ in ret["default_value"]):
                                raise TypeError(f"Default value was expected to have {x[2].__name__} elements; got {(type(v_).__name__ for v_ in ret['default_value'])} instead")
                            
                    elif ret["default_value"] is not None or (isinstance(ret["default_value"], type) and not issubclass(ret["default_value"], type(None))):
                        raise TypeError(f"Default value was expected to be a sequence or None; got {type(ret['default-value']).__name__} instead")
                     
                    # Finally, set up the element types
                    # TODO: 2023-05-18 09:26:08
                    # might not need to check if it's None. just overwrite it...
                    if ret["default_element_types"] is None:
                        ret["default_element_types"] = x[2]
                        
                elif __check_type__(ret["default_value_type"], collections.abc.Mapping):
                    # Attribute value type is set to be a mapping ⇒ x[2] is
                    # considered to specify the type of the values in the mapping
                    #
                    # Verify that the default value conforms, but allow it to be 
                    # an empty mapping or None
                    if isinstance(ret["default_value"], collections.abc.Mapping):
                        if len(ret["default_value"]) > 0:
                            if not all(isinstance(v_, x[2]) for v_ in ret["default_value"].values()):
                                raise TypeError(f"Default value was expected to have {x[2].__name__} items; got {(type(v_).__name__ for v_ in ret['default_value'].values())} instead")
                            
                    elif ret["default_value"] is not None or (isinstance(ret["default_value"], type) and not issubclass(ret["default_value"], type(None))):
                        raise TypeError(f"Default value was expected to be a mapping or None; got {type(ret['default-value']).__name__} instead")
                        
                    # Finally, set up the item types
                    # TODO: 2023-05-18 09:26:08
                    # might not need to check if it's None. just overwrite it...
                    if ret["default_item_types"] is None:
                        ret["default_item_types"] = x[2]
                        
                else: # NOTE: 2023-05-17 18:29:25 x[2] is a type !!!
                    # Default attribute value type is NOT a collection
                    # print(f"parse_descriptor_specification {x}")
                    if not isinstance(ret["default_value_type"], x[2]):
                        raise ValueError(f"Type of the default value type {ret['default_value_type']} is different from the specified default value type {x[2]}")
                    # if not isinstance(x[2], (ret["default_value_type"], type(None))):
                    #     raise ValueError(f"Type of the default value type {type(x[2]).__name__} is different from the specified default value type {ret['default_value_type']}")

                    ret["default_value_type"] = x[2]
                    
            else:
                if not isinstance(x[2], (type(None), ret["default_value_type"])):
                    raise TypeError(f"Default value expected to be None or {ret['default_value_type']}; instead, got {x[2]}")
                
                ret["default_value"] = x[2]
                
                
        else:
            __check_array_attribute__(ret, x[2])
            
        if len(x) > 3:
            for x_ in x[3:]:
                __check_array_attribute__(ret, x_)
                    
    # NOTE: 2021-11-29 17:27:07
    # generate arguments for a DescriptorGenericValidator
    type_dict = dict()
    args = list()
    kwargs = dict()
    
    # NOTE: 2021-11-30 10:26:04
    # the following are set only for numpy ndarray objects and optionally some of
    # their subclasses:
    #
    array_params = ("default_value_ndim", "default_value_dtypes", 
                    "default_value_units", "default_value_shape", 
                    "default_array_order", "default_axistags")
    
    sequence_params = ("default_element_types", )
    
    dict_params = ("default_item_types", )
    
    # if ret["name"] == "age":
    #     print(f"\nprog.parse_descriptor_specification {x} ->\n\tret = {ret}")
    
    
    if isinstance(ret["default_value_type"], type) and all(ret[k] is None for k in array_params + sequence_params + dict_params) or \
        (isinstance(ret["default_value_type"], collections.abc.Sequence) and all(isinstance(v_, type) for v_ in ret["default_value_type"])):
        
        args.append(ret["default_value_type"])
        
    elif isinstance(ret["default_value_type"], tuple) and all(isinstance(e, type) for e in ret["default_value_type"]):
        args.extend(ret["default_value_type"])
    
    else:
        type_dict = dict()
        
        if ret["default_value_ndim"] is not None:
            type_dict["ndim"] = ret["default_value_ndim"]
            
        if isinstance(ret["default_value_dtypes"], np.dtype):
            type_dict["dtype"] = ret["default_value_dtypes"]
            
        if isinstance(ret["default_value_units"], pq.Quantity):
            type_dict["units"] = ret["default_value_units"]
            
        if isinstance(ret["default_value_type"], vigra.VigraArray):
            type_dict["axistags"] = ret["default_axistags"]
            type_dict["order"] = ret["default_array_order"]
            
        if isinstance(ret["default_value_type"], (collections.abc.Sequence, collections.abc.Mapping, collections.abc.Set)):
            type_dict["element_types"] = ret["default_element_types"]
            
        # args.append(type_dict) # NOTE: TODO/FIXME 2024-07-31 10:06:51 should be in kwargs
        
    # NOTE: keys in kwargs can only be str; however, type_dict is mapped to
    # a type or tuple of types, therefore we include the dict enclosing
    # type_dict into the args sequence; the prog.DescriptorGenericValidator will take care
    # of it...
    
    kwargs = type_dict
        
            
    result = {"name":ret["name"], "value": ret["default_value"], "args":tuple(args), "kwargs": kwargs}
    
    # if ret["name"] == "age":
    #     print(f"\nprog.parse_descriptor_specification {x} -> \n\tresult =\n\t{result}")
                
    
    return result

        
class WithDescriptors(object):
    """ Base for classes that create their own descriptors.
    
    A descriptor is specified in the :class: definition as the :class: attribute
    '_descriptor_attributes_' (a tuple of tuples).
    
    Each elements in the '_descriptor_attributes_' tuple contains at least two 
    elements, where:
    
    1) the first element is always a str: the public name of the descriptor, 
        i.e. the name under which the user accesses the underlying data as an 
        instance attribute)
        
    2) an object (the default value, type specification, validation parameters,
        see the documentation for the `parse_descriptor_specification` function 
        in this module, and 'BaseScipyenData' in module core.basescipyen for 
        concrete examples)
    
    Together with the validator classes (Python descriptors) defined in this
    module, and with AttributeAdapter, this provides a framework that implements
    the Python's descriptors protocol, useful for code factoring.
    
    In addition, derived :classes: wishing to execute additional code either 
    immediately before, or after a value is set to a descriptor, also need to
    contain the attributes '_preset_hooks_' and '_postset_hooks_', respectively.
    
    These are dictionaries that map public descriptor names (as given in 
    '_descriptor_attributes_') to instances of AttributeAdapter.
    
    An AttributeAdapter instance is a callable that performs certain actions on
    the attributes of its owner whenever a descriptor is 'set' to a certain
    value. These action do not necessarily validate the new value, unless the
    descriptors is implemented by types other than BaseDescriptorValidator (or
    its subclasses defined here).
    
    
    NOTE:
    
    These descriptors DO NOT implement the trait observer design pattern as found
    in the 'traitlets' package (https://traitlets.readthedocs.io/en/stable/).
    They are not a replacement for, nor are they intended for use with, the
    'HasDescriptors' classes in the 'traitlets' package.
    
    Therefore, this mechanism is not used for storing configurables for various
    GUI components in Scipyen.
    
    Rather, it should be used to provide a consistent data attributes structure 
    for special Scipyen data types
    
    
    """
    # Tuple of attribute public name (str) to attribute specification, see the
    # 'parse_descriptor_specification' function in this module, for details.
    _descriptor_attributes_ = tuple()
    
    # Mapping (attribute name) : str ↦ AttributeAdapter
    # Maps a public attribute name (see above) to an instance of AttributeAdapter.
    # Needed for those descriptors that execute collateral code in the 
    # owner, BEFORE validating (optional) then setting the value via the 
    # descriptor's '__set__()' method.
    #
    # When present, the AttributeAdapter is called from the descriptor's '__set__()' method.
    #
    # The AttributeAdapter may also perform validation especially where the 
    # descriptor does NOT provide its own 'validate' method (which is also called
    # from the descriptor's '__set__()' method)
    #
    _preset_hooks_ = dict()
    
    # Maps a public attribute name (see above) to an instance of AttributeAdapter
    # only needed for those descriptors that execute collateral code in the 
    # owner, AFTER setting the value via the descriptor's '__set__()' method;
    # when present, the AttributeAdapter is called from the descriptor's 
    # '__set__()' method.
    #
    # Since the postset hook is called AFTER value validation and assignment 
    # inside the descriptor's '__set__()' method, any further validation performed
    # by the AttributeAdapter instances here are ignored.
    #
    _postset_hooks_ = dict()
    
    # allow for subclasses to set up their own descriptor protocol implementation
    # BUT with the constraints that the implementation's initializer MUST take
    # one mandatory name (str) parameter
    _descriptor_impl_ = DescriptorGenericValidator
    
    @classmethod
    def setup_descriptor(cls, descr_params:dict, **kwargs):
        """Default method for setting up descriptors based on specific conditions.
        
        This class method dynamically generates instances of DescriptorGenericValidator.
    
        These objects implement the Python's descriptor protocol - i.e. they
        behave like `property` objects, by providing `__get__()` and `__set__()`
        methods whenever a private attribute is accessed or assigned to, 
        respectively, in the owner (instance of `cls`).
        
        Derived classes that execute custom code besides the validation of the
        new value, (called from the  descriptor's __set__() method) need to 
        define at least one of two dictionary attributes called 
        '_preset_hooks_' and '_postset_hooks_'.
        
        These dictionaries are expected to map the descriptor's public name (i.e.
        the name under which the underlying data descriptor is accessed by the 
        :class: public API) to an AttributeAdapter instance. Attribute adapters
        are callables executed by the __set__() method to perform those custom
        actions, either BEFORE ('_preset_hooks_') or AFTER ('_postset_hooks_) 
        the validation of the new value and its assignment to the descriptor.
        
        NOTE: the __set__() method of any BaseDescriptorValidator (from which
        DescriptorGenericValidator inherit) already define a 'validate' method
        that checks the value set for assignment conforms with a set of criteria.
        
        The 'preset' and 'postset' hooks only perform computations intended to 
        modify other attributes of the instance owner of the descriptor, based 
        on the new value (to be) assigned to the descriptor.
        
        Parameters:
        -----------
        descr_params: a dictionary that maps str keys as follows:
        
        'name'      ↦ str: descriptor name
        'defval'    ↦ default descriptor value; this can be None if the descriptor
                        allows it (see below)
        'args'      ↦ tuple of acceptable types, or predicates (unary functions)
        'kwargs'    ↦ dictionary with EXACTLY two keys:
                        'allow_none'    ↦ bool — by default this is set to True
                        'dcriteria'     ↦ dictionary of additional type-specific
                            constraints (by default, this is set to an empty dict))
    
        For details, see the documentation for DescriptorGenericValidator.__init__
                    
        
        """
        name = descr_params.get("name", "") # the name of the descriptor
        defval = descr_params.get("value", None) # descriptor default value
        args = descr_params.get("args", tuple()) # the acceptable types
        kw = descr_params.get("kwargs", {})
        # kw["allow_none"] = True
        
        if not isinstance(name, str) or len(name.strip()) == 0:
            return
        
        desc_impl = getattr(cls, "_descriptor_impl_", None)
        
        if desc_impl is None:
            desc_impl = DescriptorGenericValidator
            
        if isinstance(desc_impl, DescriptorGenericValidator):
            descriptor = desc_impl(name, defval, *args, **kw)
            
        elif isinstance(desc_impl, (DescriptorTypeValidator, OneOf)):
            descriptor = descl_impl(name, *args)
            
        elif isinstance(desc_impl, ImmutableDescriptor):
            descriptor = desc_impl(default=defval)
            
        else:
            raise TypeError(f"Invalid descriptor validator class — expecting a BaseDescriptorValidator; instead, got {type(desc_impl).__name__}")
        # descriptor.allow_none = True
        setattr(cls, name, descriptor)
        
    @classmethod
    def remove_descriptor(cls, name):
        if hasattr(cls, name):
            delattr(cls, name)
            
    def __init__(self, *args, **kwargs):
       for attr in self._descriptor_attributes_:
            attr_dict = parse_descriptor_specification(attr)
            suggested_value = kwargs.pop(attr[0], attr_dict["value"])
            if isinstance(suggested_value, tuple) and len(suggested_value):
                proposed_value = suggested_value[0]
            else:
                proposed_value = suggested_value
                
            kw = dict()
            if attr[0] == "age":
                print(f"\nWithDescriptors<{self.__class__.__name__}>.__init__ to set up attr {attr}:\n\tattr_dict = {attr_dict},\n\tproposed value = {proposed_value}")
            type(self).setup_descriptor(attr_dict, **kw)
            setattr(self, attr_dict["name"], proposed_value)
            
    def __setstate__(self, state):
        """Restores the descriptors.
        
        Pickling a WithDescriptors only saves the private attributes accessed by 
        the descriptors. Because of this, the unpickled class LACKS the public 
        counterpart (the descriptor itself).
        
        This method is invoked by the Python interpreter upon unpickling
        and tries to compensate for this shortcoming.
        
        NOTE: unpickling bypasses __init__() !
        """
        
        #print(f"<{type(self).__name__}>: state = {list(state.keys())}")
        
        # first take descriptor stuff out of state and allocate/assign via the
        # descriptor implementation
        desc_impl = getattr(self, "_descriptor_impl_", None)
        
        if desc_impl is None:
            desc_impl = DescriptorGenericValidator
  
        for attr_spec in self._descriptor_attributes_:
            attr_dict = parse_descriptor_specification(attr_spec)
            attr_name = desc_impl.get_private_name(attr_spec[0])
            # check if state brings a private attribute wrapped in a descriptor
            # if it does, use it and remove it from state,
            # else use default proposed by parsing
            suggested_value = state.pop(attr_name, attr_dict["value"])
            if isinstance(suggested_value, tuple) and len(suggested_value):
                proposed_value = suggested_value[0]
            else:
                proposed_value = suggested_value
                
            kw = dict()
            type(self).setup_descriptor(attr_dict, **kw)
            setattr(self, attr_dict["name"], proposed_value)
            
        # for types derived from BaseNeo, also check state against their
        # _recommended_attrs; add annotations too, although they bypass the 
        # descriptor mechanism - this is so that objects dating since older 
        # Scipyen APIs might still be unpickled and return the same type as 
        # currently defined in Scipyen
        #
        if isinstance(self, neo.core.baseneo.BaseNeo):
            for attr_spec in self._recommended_attrs:
                attr_name = desc_impl.get_private_name(attr_spec[0])
                attr_dict = parse_descriptor_specification(attr_spec)
                suggested_value = state.pop(attr_name, attr_dict["value"])
                if isinstance(suggested_value, tuple) and len(suggested_value):
                    proposed_value = suggested_value[0]
                else:
                    proposed_value = suggested_value
                
                kw=dict()
                type(self).setup_descriptor(attr_dict, **kw)
                setattr(self, attr_dict["name"], proposed_value)
                
            annots = dict()
            
            if "_annotations_" in state:
                annots = state.pop("_annotations_")
                
            elif "annotations" in state:
                annots = state.pop("annotations")
                
            neo.core.baseneo._check_annotations(annots)
            self.annotations = annots
            
        # now that the state dict has been 'cleaned' of descriptor and BaseNeo 
        # stuff, we can`
        # use it to update the instance __dict__ as the default object.__setstate__()
        # would do
        self.__dict__.update(state)
        
    def _repr_pretty_(self, p, cycle):
        p.text(self.__class__.__name__)
        p.breakable()
        properties = tuple(d for d in get_descriptors(type(self)) if not d.startswith("_"))
        if len(properties)==0:
            properties = sorted(tuple(k for k in self.__dict__ if not k.startswith("_")))
        first = True
        for pr in properties:
            if hasattr(self, pr):
                value = getattr(self, pr)
                if first:
                    first = False
                else:
                    p.breakable()
                    
                with p.group(indent=-1):
                    p.text(f"{pr}:")
                    p.pretty(value)
                
        
setup_descriptor = WithDescriptors.setup_descriptor
remove_descriptor= WithDescriptors.remove_descriptor

def resolveObject(modName, objName):
    """Returns an object based on object's symbol and module's name.
    
    The object's symbol 'objName' is expected to be defined at module level in
    the module named by modName.
    
    The object may be: a type, a function, or an instance created at module
    level.
    
    """
    if modName is None: 
        # likely in the 'builtins' module; this is the ONLY deviance we allow
        # check to see if objName is a qualified name
        parts = objName.split(".")
        owner = ".".join(parts[:-1])
        name = parts[-1]
        if len(owner.strip()) == 0:
            return MISSING # no owner type/module specified - no way to resolve that
        
        try:
            # specifically check for builtins
            builtins = import_item("builtins")
            owner = eval(owner, builtins.__dict__)
            return getattr(owner, name, MISSING)
        except:
            return MISSING
    
    if modName in sys.modules:
        module = sys.modules[modName]
        try:
            return eval(objName, module.__dict__)
        except:
            #traceback.print_exc()
            print(f"prog.resolveObject: objName = {objName}, module = {module}")
            return MISSING
    
    else:
        rep = ".".join([modName, objName])
        try:
            return import_item(rep)
        except ModuleNotFoundError:
            return MISSING
            
            
def is_module_loaded(m:types.ModuleType):
    modname = m.__name__
    if modname in sys.modules:
        return True
    
    m_rev_path = list(reversed(modname.split('.')))
    
    for p in m_rev_path:
        if p in sys.modules:
            sysm = sys.modules[p]
            return (inspect.ismodule(sysm) and sysm.__spec__.origin == m.__spec__.origin)
        
    return False


@singledispatch
def get_loaded_module(m):
    raise NotImplementedError(f"This function is not implemented for {type(m).__name__} objects")

@get_loaded_module.register(types.ModuleType)
def _(m:types.ModuleType):
    """Returns a reference to module `m` in sys.modules.

    If `m` has not been loaded at all (even as an alias) returns None.
    
    Identity check is performed on the `origin` attribute of the module's 
    __spec__ attribute. A module's __spec__ attribute is an instance of 
    `importlib.machinery.ModuleSpec`.
    
    Two modules with the same `__spec__.origin` are considered identical even if
    they are mapped to different symbols (keys) in the `sys.modules` dictionary.
    """
    # NOTE: 2022-12-25 00:11:46
    # The following modules are example of modules where __spec__ is None, yet 
    # they are present in sys.modules:
    # • The REPL main module (__main__)
    # • cython_runtime, valrious _cython* modules, pyexpat submodules
    # • the __main__module excuted by python runtime from source file (e.g. the 
    #   __main__ module generated by python upon running 'scipyen.py')
    #
    # In addition, all but the last in the above exampke DO NOT have a __file__
    # attribute; this is useful to distinguish between "pure" runtime modules
    # and runtime modules created from a python source file.
    #
    ModSpec = importlib.machinery.ModuleSpec        # saves me some typing
    sysmodules = [v for v in sys.modules.values()]  # saves me some typing
    modname = m.__name__
    modspec = getattr(m, "__spec__", None)
    modfile = getattr(m, "__file__", None)
    
    if not isinstance(modspec, ModSpec):
        modules = list(filter(lambda x: x == m, [v for v in sysmodules]))
        if len(modules):
            return modules[0]
        else:
            return
    
    if modname in sys.modules:
        module = sys.modules[modname]
        if inspect.ismodule(module) and isinstance(getattr(module, "__spec__", None), ModSpec) and module.__spec__.origin == modspec.origin:
            return m
        
    else:
        modules = filter(lambda x: x == m, sysmodules)
        if len(modules):
            return modules[0]
        
        modules = filter(lambda x: inspect.ismodule(x) and isinstance(getattr(x, "__spec__", None), ModSpec) and getattr(x.__spec__, "origin", None) == modspec.origin,  sysmodules)
        if len(modules):
            return modules[0]
    
@get_loaded_module.register(importlib.machinery.ModuleSpec)
def _(spec:importlib.machinery.ModuleSpec):
    ModSpec = importlib.machinery.ModuleSpec        # saves me some typing
    sysmodules = [v for v in sys.modules.values()]  # saves me some typing
    modname = spec.name
    modorigin = spec.origin
    
    # print(f"get_loaded_module(spec) modname {modname} spec {spec} origin {spec.origin}")
    
    if modname in sys.modules:
        module = sys.modules[modname]
        if inspect.ismodule(module) and isinstance(getattr(module, "__spec__", None), ModSpec) and module.__spec__.origin == modorigin:
            return module
        
    modules = list(filter(lambda x: inspect.ismodule(x) and isinstance(x.__spec__, ModSpec) and x.__spec__.origin == modorigin, sysmodules))
    
    if len(modules):
        return modules[0]
    
@get_loaded_module.register(str)
def _(modname:str):
    if not isinstance(modname, str) or len(modname.strip()) == 0:
        return
    
    if modname in sys.modules:
        return sys.modules[modname]
    
    m_rev_path = list(itertools.accumulate(reversed(modname.split('.')), lambda x,y: ".".join(y,x)))
    
    for p in m_rev_path:
        if p in sys.modules:
            sysm = sys.modules[p]
            if inspect.ismodule(sysm):
                return sysm
        
def is_class_defined_in_module(x:typing.Any, m:types.ModuleType):
    """Checks if 'x' is a class or instance of a class defined in module 'm'.
    """
    
    if not inspect.isclass(x):
        x = type(x)
        
    if not inspect.ismodule(m):
        warnings.warn(f"Expecting a module; got {type(m).__name__} instead")
        return False
    
    x_module = get_loaded_module(x.__module__)
    
    if x_module is None:
        return False
    
    module = get_loaded_module(m)
    
    if module is None:
        return False
    
    # try to find x's module
    if x.__module__ in sys.modules:
        x_module = sys.modules[x.__module__]
        
    else:
        x_rev_module_path = list(reversed(x.__module__.split('.')))
        for p in x_rev_module_path:
            if p in sys.modules:
                x_module = sys.modules[p]
                break
            
    if x_module is None:
        # shouldn't happen; x being a class or instance implies its module has been 
        # imported already, hence present in sys.modules, UNLESS x is something
        # dynamically generated - in which case it would NOT have been found in
        # any of th currently importd modules anyway
        return False
        
    
    return x_module.__spec__.origin == m.__spec__.origin


def parse_module_class_path(x:str) -> typing.Union[type, types.ModuleType]:
    from core.utilities import unique
    parts = list()
    
    a = x
    
    while len(x):
        xx = x.partition('.')
        parts.append(xx[0])
        x = xx[-1]
        
    symbol = parts[-1]
    
    modules = [v for k,v in sys.modules.items() if hasattr(v, symbol)]
    
    obj = unique(list(map(lambda x: getattr(x, symbol), modules)))
    
    if len(obj)>1:
        raise RuntimeError(f"Ambiguous module.class specification {a} - are there duplicates?")
    
    if len(obj) == 0:
        raise RuntimeError(f"The module.class specification {a} is not found. HAs it been defined and imported at all?")
    
    if isinstance(obj, type):
       parent_module_name = obj.__module__ 
    
    return obj[0]
    
    
def show_caller_stack(stack):
    for s in stack:
        print(f"\tcaller\t {s.function} at line {s.lineno} in {s.filename}")
    
class with_doc:
    """
    This decorator combines the docstrings of the provided and decorated objects
    to produce the final docstring for the decorated object.
    
    Modified version of python quantities.decorators.with_doc
    
    """

    def __init__(self, method:typing.Union[typing.Type, typing.Callable, typing.Sequence[typing.Union[typing.Type, typing.Callable]]], 
                 use_header=True, 
                 header_str:typing.Optional[str] = None,
                 indent:str = "   ",
                 indent_factor:int = 1):
        # self.method = method
        if isinstance(method, (tuple, list)):# and all(isinstance(v, typing.Callable) for v in method) or all(isinstance(v, typing.Type) for v in method):
            self.method = tuple(method)
        elif isinstance(method, typing.Callable):
            self.method = (method,)
        elif isinstance(method, typing.Type):
            self.method = tuple()
        else: 
            self.method = tuple()
            
        if not isinstance(header_str, str) or len(header_str.strip()) == 0:
            if len(self.method):
                if all(isinstance(v, typing.Type) for v in self.method):
                    header_str = f"inherits from the {InflectEngine.plural('class', len(self.method))}:"
                elif all(isinstance(v, typing.Callable) for v in self.method):
                    header_str = f"calls the {InflectEngine.plural('function', len(self.method))}:"
                else:
                    header_str = "Notes:"
            else:
                header_str = "Notes:"
                
        self.use_header = use_header
        
        if use_header:
            self.header = [header_str, "-" * len(header_str)]
            
        else:
            self.header = []
            
        self.indent = indent
        self.factor = indent_factor

    def __call__(self, new_method):
        original_doc = new_method.__doc__
        new_method_name = new_method.__name__
        
        if self.use_header:
            if new_method_name:
                header = [new_method.__name__ + " " + self.header[0]]
                header.append("-" * len(header[0]))
                
            else:
                header = self.header
                header[0] = header[0].capitalize()
                
        else:
            header = []
            
        if len(self.method):
            if len(self.method) > 1:
                if original_doc:
                    docs = [original_doc]
                    docs.extend(header)
                else:
                    docs = header
                    
                docs += [self.indent_lines(f"{k}) {m.__name__}: \n{m.__doc__} \n------\n" if m.__doc__ else f"{m.__name__}\n------\n") for k, m in enumerate(self.method)]
                new_doc =  "\n".join(docs)
                
                new_method.__doc__ = new_doc
                
            else:
                m_doc = self.method[0].__doc__
                if original_doc:
                    docs = [original_doc]
                    docs.extend(header)
                else:
                    docs = header
                    
                if m_doc:
                    docs += [self.indent_lines(f"{self.method[0].__name__}: \n{m_doc}")]
                    
                new_doc = "\n".join(docs)
                new_method.__doc__ = new_doc

        return new_method
    
    def indent_lines(self, docstr:str, times:int=1):
        doclines = docstr.split("\n")
        
        indlines = list(map(lambda x: f"{self.indent * self.factor * times}{x}", doclines))
        
        return "\n".join(indlines)
        
