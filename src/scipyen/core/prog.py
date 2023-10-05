# -*- coding: utf-8 -*-
'''
Helper functions and classes for programming, including:
decorators, context managers, and descriptor validators.


'''

#print("{}: {}".format(__file__, __name__))

import pprint

from abc import ABC, abstractmethod
from importlib import abc as importlib_abc
import enum, io, os, re, itertools, sys, time, traceback, types, typing
import collections
import importlib, inspect, pathlib, warnings, operator, functools
from inspect import Parameter, Signature
    
from functools import (singledispatch, singledispatchmethod, 
                       update_wrapper, wraps,)
from contextlib import (contextmanager, ContextDecorator,)
from dataclasses import MISSING

from traitlets.utils.importstring import import_item
from traitlets import Bunch

import numpy as np
import neo, vigra
import quantities as pq

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

class ArgumentError(Exception):
    pass


class AttributeAdapter(ABC):
    """Abstract Base Class as a callable for pre- and post-validation
    """
    @abstractmethod
    def __call__(self, obj, value):
        pass
    
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
        c.b = "31" # <- no effectk
        
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
    def __init__(self, name:str, /, *args, **kwargs):
        """
        args: sequence of objects or unary predicates;
            objects can be:
            regular instances
            types
            
            NOTE: unary predicates are functions that expect a Python object as 
                the first (only) argument and return a bool.
                
                Functions which expect additional arguments can be 'reduced' to
                unary predicates by using either:
                
                a) functools.partial (for unbound functions such as those defined
                outside classes)
                
                b) functools.partialmethod (for methods)
            
            Except the special cases below, all other elements of args will be 
            added to a set of hashables, if the element is hashable, or its 
            'id' will be added to the set of non_hashables, otherwise.
            
            Special cases:
                dotted names (str) - The validator will first try to import it
                    as a 'dotted name' to resolve a type by its fully qualified 
                    name; when that fails, the str will be added to the set of
                    hashables.
                    
                numpy arrays: these are not hashable, hence they will always be
                    compared against their id() which may fail. 
                    
                    To compare a numpy array value against a 'template', 
                    use **kwargs as detailed below.
                    
                dict: these are not hashable, hence they will always be
                    compared against their id() which may fail. ;
                    
                    To compare the STRUCTURE of a dict value agains a 'template',
                    use **kwargs as detailed below.
                    
        kwargs: maps Python types or special strings to additional criteria 
            (NOTE: a Python type is a hashable Python object).
            
                The additional criteria are ALWAYS dicts, with keys (str) mapped
                to values of the type indicated in the table below. These mappings
                are designed to probe additional specific properties of the value.
                However, these keys as detailed below need not be all present in
                the criterion dictionary; when absent they will simply be ignored.
                
                NOTE: The table below lists the expected criteria for maximal
                stringency; the last entry in the table sets the most generic case
            
        Key:                        Value:
        ------------------------------------------------------------------
                                        
        1.  numpy.ndarray               {"ndim": int,
                                        "shape": tuple,
                                        "dtype": numpy.dtype,
                                        "kind": numpy.dtype.kind}
                                        
        2.  pytyhon.Quantity            as for numpy.ndarray, plus:
                                        {"units": python.Quantity}
                                    
        3.  vigra.VigraArray            as for numpy.ndarray, plus:
                                        {"axistags": vigra.AxisTags,
                                        "order": str}
                                        
        4.  vigra.AxisInfo              {"key": str,
                                        "typeFlags": vigral.AxisType
                                        "resolution": float,
                                        "description": str}
                                        
        5.  dict                        { (key_name: value_type,)* }
                                        Where 'value_type' is a type
                        
        6.  <any other type, except     dict mapping property name to type of 
            for the special cases       property value, or to a dict as detailed
            below>                      in this table
        
        ------------------------------------------------------------------
    
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
        # will raise exceptions when called, otherwise
        self.predicates = set()
        self.types = set() # allowed value types
        self.hashables = set() # values for hashables (can be used as keys)
        self.non_hashables = set() # values for non-hashables - referenced by their id()
        self.dcriteria = dict() # dictionary of criteria as in the above table
        self._allow_none_ = False
        
        for a in args:
            if inspect.isfunction(a):
                self.predicates.add(a)
                
            elif isinstance(a,type):
                self.types.add(a)
                
            elif isinstance(a, dict):
                if all(isinstance(k, type) for k in a.keys()):
                    self.dcriteria.update(a)
                    
                else:
                    self.non_hashables.add(id(a))
                
            elif isinstance(a, collections.abc.Sequence):
                if all(isinstance(v, type) for v in a):
                    self.types |= set(a)
                    
                else:
                    if is_hashable(a):
                        self.hashables.add(a)
                    else:
                        self.non_hashables.add(id(a))
                
            elif isinstance(a, str):
                try:
                    self.types.add(import_str(a))
                except:
                    self.hashables.add(a)
                    
            elif is_hashable(a):
                self.hashables.add(a)
                
            else:
                self.non_hashables.add(id(a))
                
        # NOTE: more complex predicates, where a function or method expecting
        # an instance also takes additional argument (although these can be 
        # supplied as partial functions to *args)
        # FIXME 2021-12-05 10:52:13: ???
        # The code below does do what the docstring claims it would do! 
        # Either edit the dosctring or modify the code to fulfill the promise in
        # the dosctring.
        for key, val in kwargs.items():
            # this clause below covers case 6 in the table in docstring
            # TODO must implement the others as well!
            
            if isinstance(val, dict) and all(isinstance(k, str) for k in val):
                try:
                    typ = import_name(key)
                    self.dcriteria[typ] = val
                except:
                    continue
                
        
    @property
    def allow_none(self):
        return self._allow_none_
    
    @allow_none.setter
    def allow_none(self, val:bool):
        self._allow_none_ = val is True
        
    def validate(self, value):
        if len(self.types):
            comparand = tuple(self.types)
            if self.allow_none:
                comparand = comparand + (type(None),)
                
            if isinstance(value, type):
                if not issubclass(value, comparand):
                    raise AttributeError(f"For {self.private_name} a subclass of: {comparand} was expected; got {value.__name__} instead")
            
            if not isinstance(value, comparand):
                raise AttributeError(f"For {self.private_name} one of the types: {comparand} was expected; got {type(value).__name__} instead")
            
        # NOTE: 2021-11-30 10:42:08
        # it makes sense to validate further, only when allow_none is False
        if not self.allow_none:
            if len(self.predicates):
                if not functools.reduce(operator.and_, self.predicates, True):
                    raise AttributeError(f"Unexpected value for {self.private_name}: {value}")
                
            if is_hashable(value) and len(self.hashables):
                if value not in self.hashables:
                    raise AttributeError(f"Unexpected value for {self.private_name}: {value}")
                    
            if not is_hashable(value) and len(self.non_hashables):
                if id(value) not in self.non_hashables:
                    raise AttributeError(f"Unexpected value for {self.private_name}: {value}")
                
            if len(self.dcriteria):
                values = tuple(v for k, v in self.dcriteria.items() if is_type_or_subclass(value, k))

                if len(values) == 0:
                    raise AttributeError(f"For {self.private_name} a type or subclass of {list(self.dcriteria.keys())} was expected; got {value.__name__ if isinstance(value, type) else type(value).__name__}) instead")

                for val in values:
                    if isinstance(val, dict):
                        for k, v in val.items():
                            if k == "element_types":
                                if isinstance(value, (collections.abc.Sequence, collections.abc.Set)):
                                    if not all(isinstance(v_, v) for v_ in value):
                                        raise AttributeError(f"Expecting a sequence with {(v_.__name__ for v_ in v)} elements")
                                    
                                elif isinstance(value, collections.abc.Mapping):
                                    if not all(isinstance(v_, v) for v_ in value.values()):
                                        raise AttributeError(f"Expecting a mapping with {(v_.__name__ for v_ in v)} items")
                            else:
                                if isinstance(value, dict):
                                    if k not in value:
                                        raise KeyError(f"Key {k} not found in value")
                                    vval = value.get(k)
                                else:
                                    if not hasattr(value, k):
                                        raise AttributeError(f"Attribute {k} not found in value")
                                    
                                    vval = getattr(value, k)
                                    
                                if isinstance(v, type) or isinstance(v, collections.abc.Sequence) and all(isinstance(v_, type) for v_ in v):
                                    if not is_type_or_subclass(vval, v):
                                        raise AttributeError(f"{self.private_name} expected to have {k} with type {v}; got {vval} instead")
                                
                                if vval != v:
                                    raise AttributeError(f"{self.private_name} expected to have {k} with value {v}; got {vval} instead")

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
    
    def __enter__(self):
        # for use as context manager
        self.start()
        return self
    
    def __exit__(self):
        # for use as context manager
        self.stop()
        
# class SpecFinder(importlib.abc.MetaPathFinder):
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
    

def no_sip_autoconversion(klass):
    """Decorator for classes to suppresses sip autoconversion of Qt to Python
    types.
    
    Mostly useful to prevent sip to convert QVariant to a python type when
    a QVariant is passed as argument to methods of Qt objects, inside the
    decorated function or method.
    
    Parameter:
    ==========
    klass: a Qt :class:
    
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import sip
            oldValue = sip.enableautoconversion(klass, False)
            ret = func(*args, *kwargs)
            sip.enableautoconversion(klass, oldValue)
            return ret
        return wrapper
    return decorator
        
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
    ret = bool(getattr(x, "__hash__", None) is not None)
    if ret:
        try:
            # because some 3rd party packages 'get smart' and override __hash__()
            # to raise Exception 
            hash(x) 
            return True
        except:
            return False

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
            if rt["default_value_dtype"] is None:
                if isinstance(rt["default_value"], np.ndarray):
                    if rt["default_value"].dtype not in tuple(param):
                        raise ValueError(f"dtype of the default value type ({type(rt['default_value']).dtype}) is not in {param}")
                        
                rt["default_value_dtype"] = tuple(param)

        elif all(isinstance(x_, int) for x_ in param):
            if rt["default_value_shape"] is None or rt["default_value_ndim"] is None:
                if isinstance(rt["default_value"], np.ndarray):
                    if rt["default_value"].shape != tuple(param):
                        raise ValueError(f"Default value has wrong shape ({rt['default_value'].shape}); expecting {param}")

            rt["default_value_shape"] = tuple(param)
            rt["default_value_ndim"] = len( rt["default_value_shape"])
            
    elif isinstance(param, np.dtype):
        if rt["default_value_dtype"] is None:
            if isinstance(rt["default_value"], np.ndarray):
                if rt["default_value"].dtype != param and rt["default_value"].dtype.kind != param.kind:
                    raise ValueError(f"Wrong dtype of the default value ({rt['default_value'].dtype}); expecting {param}")
            rt["default_value_dtype"] = param

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
            

def __check_type__(attr_type, specs):
    if isinstance(specs, type):
        specs = (specs,)
        
    elif not isinstance(specs, collections.abc.Sequence) or not all(isinstance(v_, type, ) for v_ in specs if v_ is not None ):
        raise TypeError("__check_type__ expecting a type or sequence of types as second parameter")
    
    else:
        specs = tuple(s for s in specs if s is not None)
    
    if isinstance(attr_type, collections.abc.Sequence):
        return all(isinstance(v_, type) and issubclass(v_, specs) for v_ in attr_type if v_ is not None )
    
    return isinstance(attr_type, type) and issubclass(attr_type, specs)
                
def parse_descriptor_specification(x:tuple):
    """
    x: tuple with 1 to 6 elements.
    
        In the most general case (terms in angle brackets are optional):
    
        (str, instance, type or tuple of types, <default value(s)>, )
    
    
        x[0]: str, name of the attribute
        
        x[1]: str, type, tuple of types or anyhing else
            when a :str: is if first tested for a dotted type name ; if this is
                a dotted type name then it is interpreted as the type of the 
                attribute's value (type name qualified by module); 
                otherwise the attribute type is a str and its default value is x[1];
                
            when a type: this is the default value type of the attribute, and 
                the default value is the default constructor if it takes no 
                parameters, else None;
                
            when a tuple:
                this can be a tuple of types, or a tuple of instances; 
                * tuple of types: these are the acceptable types of the attribute
                
                    - when the first element is a dict, this indicates that the 
                    attribute is a dict; the rest of the type objects in the
                    tuple indicate acceptable types for the dict's values
                
                * tuple of instances: these are acceptable default values for the
                attribute; their types indicate acceptable types of the attribute
                
            antyhing else: this is the default value of the attribute, and its
                type is the type of the attribute
                
            NOTE: x[1] is meant to specify the attribute type and/or its 
            acceptable default value(s). 
            
            When x[1] is a single type object, a default value will be 
            instantiated with zero arguments, if possible. This attempt will 
            fail when either:
            
            a) the intializer of the specified type requires at leat one
            positional-only parameter (which in this case is absent)
            
            b) the specified type is an abstract :class: (see for example, 
            the module 'collections.abc')
            
            These initialization failures are ignored, and the "default" 
            attribute value will NOT be set (i.e. it is left as it is, which is 
            None by default).
    
            This may impact on attribute validators (see prog.BaseDescriptorValidator and 
            derived subclasses) used to build dynamic descriptors, UNLESS the
            validator's property 'allow_none' is set to True.
                
            NOTE: 2023-05-18 08:40:56
            The default value type is now determined in core.datatypes.default_value()
            and MAY return an actual instance of the specified type, or None
            
        x[2]: type or tuple of types
            a) When a type or tuple of types, this is either:
                a.1) the explicit type(s) expected for the attribute. 
                WARNING: this may overwrite the default value type determined
                    from x[1]
                
                a.2) the explicit type(s) of elements of a collection-type attribute
                
            b) When attribute type as determined from x[1] is a numpy ndarray, 
            or a subclass of numpy array (e.g., Python Quantity, VigraArray, 
            neo DataObect) x[2] may also be:
            
            tuple of np.dtype objects:  allowed array dtypes
            
            tuple of int:               allowed shape (number of dimensions is 
                                        deduced)
            int:                        allowed number of dimensions
            
            dtype:                      allowed array dtype
            
            pq.Quantity:                allowed units (when attribute type is 
                                        python Quantity)
                    NOTE: unit matching is based on the convertibility between 
                        the expected attribute 'units' property value and the
                        specified units
                            
            str:                        array order (for VigraArrays)
            
            NOTE: to avoid further confusions, dtypes must be specified directly    
                and a str will not be interpreted as dtype 'kind'
                
            NOTE: the size of sequence attributes is NOT checked (i.e., they can
            be empty) but, if given in x[2], they can only accept elements of the
            specified type
            
        x[3]-x[7]: as x[2] for numpy arrays
            NOTE: duplicate specifications will be ignored
            
        NOTE: For objects of any type OTHER than numpy ndarray, only the first
        three elements are sufficient
        

        NOTE: The specification for the first three elements of 'x' is intended 
            to cover the case of attribute definitions in BaseNeo objects.
            
        
    Returns:
    --------
    The following key ↦ value mapping:
    
    Key:                  Value type                  Semantic:
    ============================================================================
    name                  ↦ str                       Attribute name
    default_value         ↦ object or tuple           Default attribute  value
    default_value_type    ↦ type or tuple of types    Default attribute type
    default_element_types ↦ type of tuple of types    For sequence or set attributes
    default_item_types    ↦ type or tuple of types    For mapping-type attribute
    default_value_ndim    ↦ int or None               Only for ndarray attributes
    default_value_dtype   ↦ dtype or None             Only for ndarray attributes
    default_value_units   ↦ Quantity or None          Only for Python quantities.Quantity
        
    NOTE: 
    default_value is None when either:
        * it was specified as None (in x[1]) and was NOT overwritten in x[2]
        * default_value_type is a type that cannot be instantiated without 
            arguments
        * default_value_type is a tuple of types
    """
    from core.quantities import units_convertible
    from core.datatypes import (TypeEnum, is_enum, is_enum_value, default_value)
    if not isinstance(x, tuple):
        raise TypeError(f"Expecting a tuple, got {type(x).__name__} instead")
    # print(f"parse_descriptor_specification {x}")
                
    
    
    # (name, value or type, type or ndims, ndims or units, units)
    ret = dict(
        name = None,
        default_value = None,
        default_value_type = None,
        default_element_types = None,
        default_item_types = None,
        default_value_ndim = None,
        default_value_dtype = None,
        default_value_shape = None,
        default_value_units = None,
        default_array_order = None,
        default_axistags    = None,
        
        )
    
    if len(x):
        # set the attribute name
        if not isinstance(x[0], str):
            raise TypeError(f"First element of a descriptor specification must be a str; got {type(x[0]).__name__} instead")
        
        ret["name"] = x[0]
        
    if len(x) > 1:
        # set the attribute's default value and default value type
        #
        if isinstance(x[1], str):
            try:
                val_type = import_item(x[1]) # NOTE: import_item() def'ed in traitlets.utils.importstring
            except:
                ret["default_value"] = x[1]
                ret["default_value_type"] = str
                
        elif isinstance(x[1], type):
            ret["default_value_type"] = x[1]
            val = default_value(x[1]) # NOTE: default_value() def'ed in core.datatypes
            ret["default_value"] = val
                
        elif isinstance(x[1], tuple):
            if all(isinstance(x_, type) for x_ in x[1]): 
                # NOTE: x[1] is a tuple of types
                # this leaves ret["default_value"] as None
                ret["default_value_type"] = x[1] # any of the types in x[1]
            else:
                # NOTE: x[1] is a tuple of instances
                ret["default_value_type"] = tuple(type(x_) for x_ in x[1])
                ret["default_value"] = x[1]
            
        else:
            # x[1] is an instance
            ret["default_value"] = x[1]
            ret["default_value_type"] = type(x[1])
            
    # print(f"parse_descriptor_specification default_value = {ret['default_value']}, default_value_type = {ret['default_value_type']}")
            
    if len(x) > 2: 
        # by now, the expected type of the attribute should be established,
        # whether it is None, type(None), or anything else
        #
        # x[1]
        if __check_type__(ret["default_value_type"], (None, type(None))) or not __check_type__(ret["default_value_type"], np.ndarray):
             # NOTE: 2023-05-17 18:30:44
             # This branch executed when ret["default_value_type"] is None, NoneType, or IS NOT a np.ndarray subclass
            if isinstance(x[2], collections.abc.Sequence):
                # x[2] is a sequence (tuple, list, deque)
                if all(isinstance(x_, type) for x_ in x[2]):
                    # all elements in x[2] are types
                    if __check_type__(ret["default_value_type"], (collections.abc.Sequence, collections.abc.Set)):
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
                        # Here, the default value type is neither a sequnce or set, nor a mapping.
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
                    print(f"parse_descriptor_specification {x}")
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
    array_params = ("default_value_ndim", "default_value_dtype", 
                    "default_value_units", "default_value_shape", 
                    "default_array_order", "default_axistags")
    
    sequence_params = ("default_element_types", )
    
    dict_params = ("default_item_types", )
    
    if isinstance(ret["default_value_type"], type) and all(ret[k] is None for k in array_params + sequence_params + dict_params) or \
        (isinstance(ret["default_value_type"], collections.abc.Sequence) and all(isinstance(v_, type) for v_ in ret["default_value_type"])):
        
        args.append(ret["default_value_type"])
    
    else:
        type_dict = dict()
        
        if ret["default_value_ndim"] is not None:
            type_dict["ndim"] = ret["default_value_ndim"]
            
        if isinstance(ret["default_value_dtype"], np.dtype):
            type_dict["dtype"] = ret["default_value_dtype"]
            
        if isinstance(ret["default_value_units"], pq.Quantity):
            type_dict["units"] = ret["default_value_units"]
            
        if isinstance(ret["default_value_type"], vigra.VigraArray):
            type_dict["axistags"] = ret["default_axistags"]
            type_dict["order"] = ret["default_array_order"]
            
        if isinstance(ret["default_value_type"], (collections.abc.Sequence, collections.abc.Mapping, collections.abc.Set)):
            type_dict["element_types"] = ret["default_element_types"]
            
        args.append(type_dict)
        
    # NOTE: keys in kwargs can only be str; however, type_dict is mapped to
    # a type or tuple of types, therefore we include the dict enclosing
    # type_dict into the args sequence; the prog.DescriptorGenericValidator will take care
    # of it...
            
    result = {"name":ret["name"], "value": ret["default_value"], "args":tuple(args), "kwargs": kwargs}
    
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
    def setup_descriptor(cls, descr_params, **kwargs):
        """Default method for setting up descriptors based on specific conditions.
        
        This will dynamically generate instances of DescriptorGenericValidator.
        These objects implement the Python's descriptor protocol - i.e. they
        behave like `property` objects, by providing `__get__()` and `__set__()`
        methods whenever a private attribute is accessed or assigned to, 
        respectively, in the owner instance of type `cls`.
        
        Derived classes that expect to execute custom code besides the validation
        iof the new value, inside the  descriptor's __set__() method, need to 
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
        
        See AttributeAdapter for details.
    
        """
        args = descr_params.get("args", tuple())
        kw = descr_params.get("kwargs", {})
        name = descr_params.get("name", "")
        defval = descr_params.get("value", None)
        
        if not isinstance(name, str) or len(name.strip()) == 0:
            return
        
        desc_impl = getattr(cls, "_descriptor_impl_", None)
        
        if desc_impl is None:
            desc_impl = DescriptorGenericValidator
        
        descriptor = desc_impl(name, defval, *args, **kw)
        descriptor.allow_none = True
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
        
