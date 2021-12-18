# -*- coding: utf-8 -*-
'''
Helper functions and classes for programming, including:
decorators, context managers, and descriptor validators.


'''

#print("{}: {}".format(__file__, __name__))

from pprint import pprint

from abc import ABC, abstractmethod
import enum, io, os, re, itertools, sys, time, traceback, types, typing
import collections
import importlib, inspect, pathlib, warnings, operator, functools
from functools import (singledispatch, singledispatchmethod, 
                       update_wrapper, wraps,)
from contextlib import (contextmanager, ContextDecorator,)
from traitlets.utils.importstring import import_item
from traitlets import Bunch

import numpy as np
import neo, vigra
import quantities as pq
from . import workspacefunctions
from .workspacefunctions import debug_scipyen

CALLABLES = (types.FunctionType, types.MethodType,
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
        """Find out what private name thus would operate on
        """
        return f"_{name}_"
    
    def __set_name__(self, name:str) -> None:
        """Call this in the implementation's __init__
        """
        self.private_name = f"_{name}_"
        self.public_name = name
        
    def __get__(self, obj, objtype=None) -> object:
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
        called BEFORE (respectively, AFTER)  validation of 'value' and its
        assignment.
        
        """
        if hasattr(obj, "_preset_hooks_") and isinstance(obj._preset_hooks_, dict):
            preset_validator = obj._preset_hooks_.get(self.public_name, None)
            if isinstance(preset_validator, AttributeAdapter):
                preset_validator(obj, value)
                
        self.validate(value)
        setattr(obj, self.private_name, value)
        
        # NOTE: 2021-12-06 12:43:48 
        # call postset hooks ONLY AFTER the descriptor value had been set
        # (last line of code, above)
        if hasattr(obj, "_postset_hooks_") and isinstance(obj._postset_hooks_, dict):
            postset_validator = obj._postset_hooks_.get(self.public_name, None)
            if isinstance(postset_validator, AttributeAdapter):
                postset_validator(obj, value)
        
    def __delete__(self, obj):
        if hasattr(obj, self.private_name):
            delattr(obj, self.private_name)
            
        # complete wipe-out
        if hasattr(obj.__class__, self.public_name):
            delattr(obj.__class__, self.public_name)
        
    @abstractmethod
    def validate(self, value):
        pass
    
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

#class SignatureDict(Bunch):
    #def __init__(self, / , *args, **kwargs):
        #super().__init__(*args, **kwargs)
        
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
        
# ### BEGIN module functions

def classify_signature(sig, funcname:typing.Optional[str]=None,
                       modname:typing.Optional[str]=None,
                       verbose:bool=False) -> Bunch:
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
    
    funcname: str, optional, default None; 
        This should be the callable's __name__ attribute and should be 
        passed to this function when 'sig' is a Signature object
        
    modname: str, optional, default is None
        This shoudl be the name of the module where the function is 
        defined (callable's __module__ attribute) and should be
        passed to thsi function when 'sig' is a Signature object.
        
    Returns:
    --------
    
    a traitlets.Bunch object with the following attributes:
    
    'name': str - the name of the callable or None
    
    'qualname': str - the qualified name of the callable or None
    
    'module': str - the module name where the callable was defined, 
            or None
    
    'positional': dict - mapping name: type for positional-only 
        parameters of the callable
    
    'named': dict - mapping name: (default, type) for named or positional
        parameters of the callable
        
    'varpos': duct - mapping name: None, with the name of the var-positional
        parameter of the callable (e.g. 'args' when the callable signature
        includes `*args`)
        
    'varkw': dict - mapping of name: None, with the name of the var-kweyword
        parametert if the callable (e.g. 'kwargs' when the callable signature
        includes `**kwargs`)
        
    'returns': type, if the callable signature has an annotated return, 
        or `inspect._empty` otherwise
    
    """
    from inspect import Parameter
    
    qualname = funcname
    if isinstance(sig, CALLABLES):
        funcname = sig.__name__
        modname = getattr(sig, "__module__", None)
        qualname = sig.__qualname__
        sig = inspect.signature(sig)
        
    if not isinstance(sig, inspect.Signature):
        raise TypeError(f"Expecting a Signature object, a function, or a method; got {type(sig).__name__} instead")
    
    if not isinstance(funcname, str) or len(funcname.strip()) == 0:
        funcname = None
        
    if not isinstance(modname, str) or len(modname.strip()) == 0:
        modname = None
        
    if not isinstance(qualname, str) or len(qualname.strip()) == 0:
        qualname = None
        
    posonly_params = dict()
    named_params = dict()
    varkw_params = dict()
    varpos_params = dict()
    
    for parname, val in sig.parameters.items():
        if verbose:
            print("parameter name:", parname, "value:", val, "kind:", val.kind, "default:", val.default, "annotation:", val.annotation)
        
        if val.kind is Parameter.POSITIONAL_ONLY:
            posonly_params[parname] = None if val.annotation is Parameter.empty else val.annotation
            
        elif val.kind is Parameter.POSITIONAL_OR_KEYWORD:
            if val.kind is Parameter.VAR_KEYWORD:
                varkw_params[parname] = None if val.annotation is Parameter.empty else val.annotation
            elif val.kind is Parameter.VAR_POSITIONAL:
                varpos_params[parname] = None if val.annotation is Parameter.empty else val.annotation
            else:
                named_params[parname] = (None if val.default is Parameter.empty else val.default, 
                                         None if val.annotation is Parameter.empty else val.annotation)
                
        elif val.kind is Parameter.VAR_KEYWORD:
            varkw_params[parname] = None if val.annotation is Parameter.empty else val.annotation
            
        elif val.kind is Parameter.VAR_POSITIONAL:
            varpos_params[parname] = None if val.annotation is Parameter.empty else val.annotation
                
    
    #posonly_params = dict((parname, None if val.annotation is Parameter.empty else val.annotation) for parname, val in sig.parameters.items() if val.kind is Parameter.POSITIONAL_ONLY)
    
    #named_params = dict((parname, (None if val.default is Parameter.empty else val.default, None if val.annotation is Parameter.empty else val.annotation)) for (parname, val) in sig.parameters.items() if parname not in ("cls", "self") and parname not in posonly_params and val.kind == Parameter.POSITIONAL_OR_KEYWORD and val.kind not in (Parameter.VAR_KEYWORD, Parameter.VAR_POSITIONAL))
    
    #varkw_params = dict((parname, None if val.annotation is Parameter.empty else val.annotation) for parname, val in sig.parameters.items() if val.kind is Parameter.VAR_KEYWORD)
    
    #varpos_params = dict((parname, None if val.annotation is Parameter.empty else val.annotation) for parname, val in sig.parameters.items() if val.kind is Parameter.VAR_POSITIONAL)
    
    return Bunch(name = funcname, qualname = qualname, module = modname,
                         positional = posonly_params, named = named_params, 
                         varpos = varpos_params, varkw = varkw_params,
                         returns = sig.return_annotation)

#def stringify_signature(f:typing.Union[types.FunctionType, inspect.Signature, SignatureDict], 
                        #as_constructor:bool=False):
def stringify_signature(f:typing.Union[types.FunctionType, inspect.Signature, Bunch], 
                        as_constructor:bool=False):
    
    if isinstance(f, (types.FunctionType, inspect.Signature)):
        f = classify_signature(f)
        
    #elif not isinstance(f, SignatureDict):
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
    
def iter_attribute(iterable:typing.Iterable, 
                   attribute:str, 
                   silentfail:bool=True)-> typing.Generator:
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
    
def filter_type(iterable:typing.Iterable, klass:typing.Type) -> typing.Iterator:
    """Iterates elements of 'iterable' that are of type specified by 'klass'
    
    Parameters:
    ===========
    iterable: An iterable
    klass: a type
    """
    return filter(lambda x: isinstance(x, klass), iterable)

def filterfalse_type(iterable:typing.Iterable, klass:typing.Type) -> typing.Iterator:
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
                **kwargs)-> typing.Iterator:
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
    
def filterfalse_attr(iterable:typing.Iterable, **kwargs)-> typing.Iterator:
    """'Negative' form of filter_attr.
    
    Calls filter_attr with 'exclude' set to True.
    
    """
    kwargs.pop("exclude", True)
    
    return filter_attr(iterable, exclude=True, **kwargs)
    
    #return itertools.chain.from_iterable((filter(lambda x: not f(getattr(x, n, None)) if inspect.isfunction(f) else f != getattr(x, n, None),
                                                 #iterable) for n,f in kwargs.items()))

    
def filter_attribute(iterable:typing.Iterable,attribute:str, value:typing.Any, 
                     predicate:typing.Callable[...,bool]=lambda x,y: x==y,
                     silentfail:bool=True) -> typing.Iterator:
    """Iterates elements in 'iterable' for which 'attribute' satisfies 'predicate'.
    DEPRECATED
    
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
    
def filterfalse_attribute(iterable:typing.Iterable, attribute:str, value:typing.Any, 
                     predicate:typing.Callable[...,bool]=lambda x,y: x==y,
                     silentfail:bool=True) -> typing.Iterator:
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
    
#NOTE: 2017-11-22 22:00:40 FIXME TODO
# for pyqtSlots, place this AFTER the @pyqtSlot decorator
def safeWrapper(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
            
        except Exception as e:
            stars = "".join(["*"]*len(f.__name__))
            print("\n%s\nIn function %s:\n%s" % (stars, f.__name__, stars))
            traceback.print_exc()
            #print("Call stack:")
            #traceback.print_stack()
            #print("%s" % stars)
            
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
def timeblock(label):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        print("{} : {}".format(label, end-start))

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

def parse_descriptor_specification(x:tuple) -> dict:
    """
    x: tuple with 1 to 6 elements:
        x[0]: str, name of the attribute
        
        x[1]: str, type, tuple of types or anyhing else
            when a :str: is if first tested for a dotted type name ; if a dotted
                type name this is interpreted as the type of the attribute's
                value; otherwise it is taken as the default value of a str-type 
                attribute;
                
            when a type or tuple of types: this is the default value type of the
                attribute, and the default value is the default constructor if 
                it takes no parameters, else None
                
            when a tuple:
                this can be a tuple of types, or objects; 
                in the former case, these are the acceptable types of the 
                attribute; 
                in the latter, the type of objects indicate the acceptable
                types of the attribute, AND the acceptable default values
                when a value is not specified otherwise
                
            antyhing else: this is the default value of the attribute, and its
                type is the acceptable type of the attribute
                
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
                
        x[2]: type or tuple of types
            a) When a type or tuple of types, this is either:
                a.1) the explicit type(s) expected for the attribute, when the
                expected type of the attributs had not been determined yet, 
                from x[1].
                
                a.2) the explicit type(s) of elements of a sequence or set 
                elements when the attribute type determined from x[1] is a
                sequence (e.g., tuple, list, or deque) or a set.
                
                a.3) the explicit type(s) of the values of a dict, when the 
                attribute type determined from x[1] is a dict.
        
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
    dict with the following key/values:
    
        name:str,
        default_value: Python object, or tuple of objects
        default_value_type: Python type or tuple of types
        default_value_ndim: int or None,
        default_value_dtype: numpy dtype object or None,
        default_value_units: Python Quantity object or None
        
    NOTE: 
    default_value is None when either:
        * it was specified as None (in x[1])
        * default_value_type is a type that cannot be instantiated without 
            arguments
        * default_value_type is a tuple of types
    """
    from core.quantities import units_convertible
    def __check_attr_type__(attr_type, specs):
        if isinstance(specs, type):
            specs = (specs,)
            
        elif not isinstance(specs, collections.abc.Sequence) or not all(isinstance(v_, type, ) for v_ in specs if v_ is not None ):
            raise TypeError("__check_attr_type__ expecting a type or sequence of types as second parameter")
        
        else:
            specs = tuple(s for s in specs if s is not None)
        
        if isinstance(attr_type, collections.abc.Sequence):
            return all(isinstance(v_, type) and issubclass(v_, specs) for v_ in attr_type if v_ is not None )
        
        return isinstance(attr_type, type) and issubclass(attr_type, specs)
                
                
    
    def __check_array_attribute__(rt, param):
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
                    if not units_convertible(rt["default_value"].units, param.units):
                        raise ValueError(f"Default value has wrong units ({rt['default_value'].units}); expecting {param} ")
                    
                rt["default_value_units"] = param
                
        
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
        ret["name"] = x[0]
        
    if len(x) > 1:
        if isinstance(x[1], str):
            try:
                val_type = import_item(x[1])
            except:
                ret["default_value"] = x[1]
                ret["default_value_type"] = str
                
        elif isinstance(x[1], type):
            ret["default_value_type"] = x[1]
            try:
                ret["default_value"] = x[1]()
            except:
                pass
                
        elif isinstance(x[1], tuple):
            if all(isinstance(x_, type) for x_ in x[1]):
                ret["default_value_type"] = x[1]
            else:
                ret["default_value_type"] = tuple(type(x_) for x_ in x[1])
                ret["default_value"] = x[1]
                #ret["default_value"] = x[0]
            
        else:
            ret["default_value"] = x[1]
            ret["default_value_type"] = type(x[1])
            
    if len(x) > 2: 
        # by now, the expected type of the attribute should be established,
        # whether it is None, type(None), or anything else
        
        if __check_attr_type__(ret["default_value_type"], (None, type(None))) or not __check_attr_type__(ret["default_value_type"], np.ndarray):
            if isinstance(x[2], collections.abc.Sequence):
                if all(isinstance(x_, type) for x_ in x[2]):
                    if __check_attr_type__(ret["default_value_type"], (collections.abc.Sequence, collections.abc.Set)):
                        ret["default_element_types"] = tuple(x[2])
                        if ret["default_value"] is not None:
                            if not isinstance(ret["default_value"], ret["default_value_type"]):
                                raise ValueError(f"Default value expected to be a {type(ret['default_value_type'].__name__)}; got {type(ret['default_value']).__name__} instead")
                            
                            if not all(isinstance(v_, tuple(x[2])) for v_ in ret["default_value"]):
                                raise ValueError(f"Default value expected to be contain {x[2]} elements; got {set((type(v_).__name__ for v_ in ret['default_value']))} instead")
                        
                    elif __check_attr_type__(ret["default_value_type"], collections.abc.Mapping):
                        ret["default_item_types"] = tuple(x[2])
                        if ret["default_value"] is not None:
                            if not isinstance(ret["default_value"], collections.abc.Mapping):
                                raise ValueError(f"Default value expected to be a mapping; got {type(ret['default_value']).__name__} instead")
                            
                            if not all(isinstance(v_, tuple(x[2])) for v_ in ret["default_value"].values()):
                                raise ValueError(f"Default value expected to be contain {x[2]} items; got {set((type(v_).__name__ for v_ in ret['default_value'].values()))} instead")
                        
                    else:
                        if ret["default_value"] is not None:
                            if not isinstance(ret["default_value"], tuple(set(x[2]))):
                                raise ValueError(f"Type of the default value type {type(ret['default_value']).__name__} is different from the specified default value type {x[2]}")
                        
                        ret["default_value_type"] = tuple(set(x[2])) # make it unique
                    
            elif isinstance(x[2], type):
                if __check_attr_type__(ret["default_value_type"], (collections.abc.Sequence, collections.abc.Set)):
                    if isinstance(ret["default_value"], ret["default_value_type"]):
                        if len(ret["default_value"]) > 0:
                            if not all(isinstance(v_, x[2]) for v_ in ret["default_value"]):
                                raise TypeError(f"Default value was expected to have {x[2].__name__} elements; got {(type(v_).__name__ for v_ in ret['default_value'])} instead")
                            
                    elif ret["default_value"] is not None or (isinstance(ret["default_value"], type) and not issubclass(ret["default_value"], type(None))):
                        raise TypeError(f"Default value was expected to be a sequence or None; got {type(ret['default-value']).__name__} instead")
                        
                    if ret["default_element_types"] is None:
                        ret["default_element_types"] = x[2]
                        
                elif __check_attr_type__(ret["default_value_type"], collections.abc.Mapping):
                    if isinstance(ret["default_value"], collections.abc.Mapping):
                        if len(ret["default_value"]) > 0:
                            if not all(isinstance(v_, x[2]) for v_ in ret["default_value"].values()):
                                raise TypeError(f"Default value was expected to have {x[2].__name__} items; got {(type(v_).__name__ for v_ in ret['default_value'].values())} instead")
                            
                    elif ret["default_value"] is not None or (isinstance(ret["default_value"], type) and not issubclass(ret["default_value"], type(None))):
                        raise TypeError(f"Default value was expected to be a mapping or None; got {type(ret['default-value']).__name__} instead")
                        
                    if ret["default_item_types"] is None:
                        ret["default_item_types"] = x[2]
                        
                else:
                    if ret["default_value"] is not None:
                        if not isinstance(ret["default_value"], x[2]):
                            raise ValueError(f"Type of the default value type {type(ret['default_value']).__name__} is different from the specified default value type {x[2]}")

                    ret["default_value_type"] = x[2]
                
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
        i.e. the name under which the user accesses the underlying data as if an 
        instance attribute)
        
    2) an object (the default value, type specification, validation parameters,
        see the documentation for the `parse_descriptor_specification` function 
        in this module, and 'BaseScipyenData' in module core.basescipyen for 
        concrete examples)
    
    Together with the validator classes (Python descriptors) defined in this
    module, and with AttributeAdapter, this provides framework implementing the
    Python's descriptors protocol, useful for code factoring.
    
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
    Therefore they are ARE NOT a replacement for, nor are they intended for use 
    with, the 'HasDescriptors' classes in the 'traitlets' package.
    
    
    """
    # Tuple of attribute public name (str) to attribute specification, see the
    # 'parse_descriptor_specification' function in this module, for details.
    _descriptor_attributes_ = tuple()
    
    # Maps a public attribute name (see above) to an instance of AttributeAdapter
    # only needed for those descriptors that execute collateral code in the 
    # owner, BEFORE validating (optional) then setting the value via the 
    # descriptor's '__set__()' method; when present, the AttributeAdapter is 
    # called from the descriptor's '__set__()' method.
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
        
        Classes derived from WithDescriptors and expecting to execute cutsom code 
        inside the descriptor's __set__() method, also need to define at least
        one of two dictionary attributes called 
        '_preset_hooks_' and '_postset_hooks_'.
        
        These dictionaries are expected to map the descriptor's public name (i.e.
        the name under which the underlying data descriptor is accessed by the 
        :class: public API) to an AttributeAdapter instance (emulated callable)
        which is then called by the __set__() method to perform those custom
        actions, either BEFORE ('_preset_hooks_') or AFTER 
        ('_postset_hooks_) the value is validated and assigned to the 
        descriptor data.
        
        NOTE: the __set__() method of any BaseDescriptorValidator (from which
        DescriptorGenericValidator inherit) already define a 'validate' method
        that checks the value set for assignment conforms with a set of criteria.
        
        The 'preset' and 'postset' hooks are intended to perform computations 
        intended to modify other attributes of the instance owner of the
        descriptor based on the new value (to be) assigned to the descriptor, 
        rather than validate and/or modify this value.
        
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

