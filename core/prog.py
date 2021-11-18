# -*- coding: utf-8 -*-
'''
Decorators, context managers, and helper functions & classes for programming
'''

#print("{}: {}".format(__file__, __name__))

from pprint import pprint

import enum, io, os, re, itertools, sys, time, traceback, types, typing, collections
import importlib, inspect, pathlib, warnings, operator, functools
from functools import singledispatch, update_wrapper, wraps
from contextlib import (contextmanager, ContextDecorator,)

import neo
from . import patchneo
from . import workspacefunctions
from .workspacefunctions import debug_scipyen
#from . import patchneo as patchneo
#from . import neoevent as neoevent
#from . import neoepoch as neoepoch

from iolib import jsonio

CALLABLES = (types.FunctionType, types.MethodType,
             types.WrapperDescriptorType, types.MethodWrapperType,
             types.BuiltinFunctionType, types.BuiltinMethodType,
             types.MethodDescriptorType, types.ClassMethodDescriptorType)

class SignatureDict(types.SimpleNamespace):
    def __init__(self, / , *args, **kwargs):
        #self.__signature__ = None
        super().__init__(*args, **kwargs)
        

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

def classify_signature(sig, 
                       funcname:typing.Optional[str]=None,
                       modname:typing.Optional[str]=None) -> SignatureDict:
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
    
    pos_params = dict((parname, None if val.annotation is Parameter.empty else val.annotation) for parname, val in sig.parameters.items() if val.kind is Parameter.POSITIONAL_ONLY)
    
    named_params = dict((parname, (None if val.default is Parameter.empty else val.default, None if val.annotation is Parameter.empty else val.annotation)) for (parname, val) in sig.parameters.items() if parname not in ("cls", "self") and parname not in pos_params and val.kind not in (Parameter.VAR_KEYWORD, Parameter.VAR_POSITIONAL))
    
    varkw_params = dict((parname, None if val.annotation is Parameter.empty else val.annotation) for parname, val in sig.parameters.items() if val.kind is Parameter.VAR_KEYWORD)
    
    varpos_params = dict((parname, None if val.annotation is Parameter.empty else val.annotation) for parname, val in sig.parameters.items() if val.kind is Parameter.VAR_POSITIONAL)
    
    return SignatureDict(name = funcname, qualname = qualname, module = modname,
                         positional = pos_params, named = named_params, 
                         varpos = varpos_params, varkw = varkw_params,
                         returns = sig.return_annotation)

def stringify_signature(f:typing.Union[types.FunctionType, inspect.Signature, SignatureDict], 
                        as_constructor:bool=False):
    
    if isinstance(f, (types.FunctionType, inspect.Signature)):
        f = classify_signature(f)
        
    elif not isinstance(f, SignatureDict):
        raise TypeError(f"Expecting a function, a function Signature, or a SignatureDict")
    
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
    
def check_neo_patch(exc_info:tuple):
    stack_summary = traceback.extract_tb(exc_info[2])
    frame_names = [f.name for f in stack_summary]
    
    last_frame_summary = stack_summary[-1]
    
    obj_name = last_frame_summary.name
    
    print(obj_name)
    
    return identify_neo_patch(obj_name)
    
    #if any([s in last_frame_summary.name.lower() for s in  ("neo", "event", "epoch", "analogsignalarray", "analogsignal", "irregularlysampledsignal")]):
    #if any([s in obj_name.lower() for s in  patchneo.patches.keys()]):
        #module_name = inspect.getmodulename(last_frame_summary.filename)
        
    #for key in patchneo.patches.keys():
        #if obj_name in key:
            #return (key, patchneo.patches[key])
        
def identify_neo_patch(obj_name):
    if debug_scipyen():
        print("\nLooking for possible patch for %s" % obj_name)
        
    for key in patchneo.patches.keys():
        if obj_name in key:
            val = patchneo.patches[key]
            if debug_scipyen():
                print("\t Found patch", val, "for", key)
            return (key, val)
    
    
def import_module(name, package=None):
    """An approximate implementation of import."""
    absolute_name = importlib.util.resolve_name(name, package)
    try:
        return sys.modules[absolute_name]
    except KeyError:
        pass

    path = None
    
    if '.' in absolute_name:
        parent_name, _, child_name = absolute_name.rpartition('.')
        parent_module = import_module(parent_name)
        path = parent_module.__spec__.submodule_search_locations
        
    if debug_scipyen():
        print("import_module: path =", path)
        
    for finder in sys.meta_path:
        if hasattr(finder, "find_spec"):
            spec = finder.find_spec(absolute_name, path)
            if spec is not None:
                break
    else:
        raise ImportError(f'No module named {absolute_name!r}')
        
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[absolute_name] = module
    
    if path is not None:
        setattr(parent_module, child_name, module)
        
    return module

def import_relocated_module(mname):
    spec = get_relocated_module_spec(mname)
    
    if spec is not None:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[mname] = module
    
def get_relocated_module_spec(mname, scipyen_path=None):
        #print("get_relocated_module_spec: modname =", mname)
        
        if isinstance(scipyen_path, str) and os.path.isdir(scipyen_path):
            file_path = os.path.join(*(scipyen_path, "%s.py" % mname))
            
        else:
            if scipyen_path is None:
                scipyen_path = pathlib.Path(sys.path[0]) # this is where scipyen is located
                
            elif not isinstance(scipyen_path, pathlib.Path):
                raise ValueError("scipyen_path expected to be a valid directory path string, a pathlib.Path, or None; got %s instead\n" % scipyen_path)
            
            
            mloc = list(scipyen_path.glob("**/%s.py" % mname))
            
            if len(mloc)==0: # py source file not found
                raise FileNotFoundError("Could not find a module source file for %s\n" % mname)
            
            
            file_path = os.path.join(*mloc[0].parts)
        
        #print("get_relocated_module_spec: file_path =", file_path)
        
        if isinstance(file_path, str) and len(file_path):
            return importlib.util.spec_from_file_location(mname, file_path)
        
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
        
    #return [i[0] for i in inspect.getmembers(obj, lambda x: inspect.isdatadescriptor(x) and isinstance(x), property)]
    return [i[0] for i in inspect.getmembers(obj, lambda x: isinstance(x, property))]
    
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

