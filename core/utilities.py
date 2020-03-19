# -*- coding: utf-8 -*-
'''
Programming helper functions & decorators
'''
#### BEGIN core python modules
import traceback, re, io, sys, enum, itertools, time, typing, types, warnings
from functools import singledispatch, update_wrapper, wraps
from contextlib import contextmanager
#### END core python modules

#### BEGIN 3rd party modules
from PyQt5.QtWidgets import QMessageBox
import numpy as np
import pandas as pd
import vigra
#from . import datatypes
#### END 3rd party modules

#### BEGIN pict.core modules
#import datatypes as dt
from . import strutils
#### END pict.core modules

def silentindex(a, b, multiple:bool = True):
    """ Call this instead of list.index, such that a missing value returns None instead
    of raising an Exception
    """
    if b in a:
        if multiple:
            return [k for k, v in enumerate(a) if v is b]
        
        return a.index(b) # returns the index of first occurrence of b in a
    else:
        return None
    
def yyMdd(now=None):
    import string, time
    if not isinstance(now, time.struct_time):
        now = time.localtime()
        
    #year = time.strftime("%y", tuple(now))
    #month = string.ascii_lowercase[now.tm_mon-1]
    #day = time.strftime("%d", tuple(now))
    
    return "%s%s%s" % (time.strftime("%y", tuple(now)), string.ascii_lowercase[now.tm_mon-1], time.strftime("%d", tuple(now)))

# NOTE: 2017-08-11 08:56:01
# a little trick to use singledispatch as an instancemethod decorator
# I picked up from below:
# https://stackoverflow.com/questions/24601722/how-can-i-use-functools-singledispatch-with-instance-methods

def instanceMethodSingleDispatch(func):
    dispatcher = singledispatch(func)
    def wrapper(*args, **kw):
        return dispatcher.dispatch(args[1].__class__)(*args, **kw)
    wrapper.register = dispatcher.register
    # update_wrapper(wrapper, func)
    # or better, for the full interface of singledispatch:
    update_wrapper(wrapper, dispatcher)
    return wrapper


#def manage_ui_slot_connections(src, signals, dest, slots):
    #def __slot_manager_wrapper__(f,*args, **kwargs):
        #@wraps(f)
        #def __func_wrapper__(*args, **kwargs):
            #try:
                #for signal,slot in zip(signals, slots):
                    #signal.disconnect(slot)
                    
                #return f(*args, **kwargs)
            
                #for (signal, slor) in zip(signals, slots):
                    #signal.connect(slot)
            
            #except Exception as e:
                #traceback.print_exc()
                
        #return __func_wrapper__
    
    #return __slot_manager_wrapper__
            
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


#NOTE: 2017-11-22 22:00:40 FIXME TODO
# for pyqtSlots, place this AFTER the @pyqtSlot decorator
def safeWrapper(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
            
        except Exception as e:
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

def makeFileFilterString(extList, genericName):
    extensionList = [''.join(i) for i in zip('*' * len(extList), '.' * len(extList), extList)]

    fileFilterString = genericName + ' (' + ' '.join(extensionList) +')'

    individualExtensionList = ['{I} (*.{i})'.format(I=i.upper(), i=i) for i in extList]
    
    individualImageTypeFilters = ';;'.join(individualExtensionList)
    
    individualFilterStrings = ';;'.join([fileFilterString, individualImageTypeFilters])
    
    return (fileFilterString, individualFilterStrings)

def counterSuffix(x, strings):
    """Appends a counter suffix to x is x is found in the list of strings
    
    Parameters:
    ==========
    
    x = str: string to check for existence
    
    strings = sequence of str to check for existence of x
    
    """
    
    if not isinstance(strings, (tuple, list)) or not all ([isinstance(s, str) for s in strings]):
        raise TypeError("Second positional parameter was expected to be a sequence of str")
    
    count = len(strings)
    
    ret = x
    
    if count > 0:
        if x in strings:
            first   = strings[0]
            last    = strings[-1]
            
            m = re.match(r"([a-zA-Z_]+)(\d+)\Z", first)
            
            if m:
                suffix = int(m.group(2))

                if suffix > 0:
                    ret = "%s_%d" % (x, suffix-1)
                    
            else:
                m = re.match(r"([a-zA-Z_]+)(\d+)\Z", last)
                
                if m:
                    suffix = int(m.group(2))
                    
                    ret = "%s_%d" % (x, suffix+1)
                    
                else:
                    
                    ret = "%s_%d" % (x, count)
                    
    return ret
                
    
def get_nested_value(src, path):
    """Returns a value contained in the nested dictionary structure src.
    
    Returns None if path is not found in dict.
    
    Parameters:
    ===========
    
    src: a dictionary, possibily containing other nested dictionaries; 
        NOTE: all keys in the dictionary must be hashable objects
    
    path: a hashable object that points to a valid key in "src", or a list of
            hashable objects describing the path from the top-level dictionary src
            down to the individual "branch".
            
            Hashable objects are python object that define __hash__() and __eq__()
            functions, and have a hash value that never changes during the object's
            lifetime. Typical hashable objects are scalars and strings.
    
    """
    if not isinstance(src, (dict, tuple, list)):
        raise TypeError("First parameter (%s) expected to be a dict, tuple, or list; got %s instead" % (src, type(src).__name__))
    
    #if hasattr(path, "__hash__") and getattr(path, "__hash__") is not None: 
        ## list has a __hash__ attribute which is None
        #if path in src:
            #return src[path]
        
        #else:
            #return None
        
    elif isinstance(path, (tuple, list)):
        try:
            if isinstance(src, (tuple, list)):
                ndx = int(path[0])
                
            else:
                ndx = path[0]
            
            value = src[ndx]
            
            #print("path", path)
            #print("path[0]", path[0])
            #print("value type", type(value).__name__)
            
            if len(path) == 1:
                return value
            
            if isinstance(value, (dict, tuple, list)):
                return get_nested_value(value, path[1:])
            
            else:
                return value
            
        except:
            traceback.print_exc
            return None
        
    else:
        raise TypeError("Expecting a hashable object or a sequence of hashable objects, for path %s; got %s instead" % (path, type(path).__name__))
        
        
def set_nested_value(src, path, value):
    """Adds (or sets) a nested value in a mapping (dict) src.
    """
    #print(src)
    if not isinstance(src, dict):
        raise TypeError("First parameter (%s) expected to be a dict; got %s instead" % (src, type(src).__name__))
    
    if hasattr(path, "__hash__") and getattr(path, "__hash__") is not None: 
        # this either adds value under path key if path not in src, 
        # or replaces old value of src[path] with value
        src[path] = value 
    
    elif isinstance(path, (tuple, list)):
        if path[0] not in src:
            src[path[0]] = dict()
            
        else:
            if isinstance(src.path[0], dict):
                set_nested_value(src[path[0]], path[1:], value)
                
            else:
                src[path[0]] = value
        
    else:
        raise TypeError("Expecting a hashable object or a sequence of hashable objects, for path %s; got %s instead" % (path, type(path).__name__))
        
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
    """Returns True if x is a numpy arrtay encapsulating a column vector.
    
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
    
def nth(iterable, n, default=None):
    """Returns the nth item or a default value
    
    iterable: an iterable
    
    n: int, start index (>= 0)
    
    default: value to be returned when iteration stops (default is None)
    
    NOTE: Recipe found in the documentation for python itertools module.
    """
    return next(itertools.islice(iterable, n, None), default)

def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ...
    
    NOTE: Recipe from the documentation for python itertools module.
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

def unique(seq):
    """Returns a sequence of unique elements in sequence 'seq'.
    
    Parameters:
    -----------
    seq: an iterable sequence (tuple, list, range)
    
    Returns:
    A sequence containing unique elements in 'seq'.
    
    NOTE: Does not guarantee the order of the unique elements is the same as 
            their order in 'seq'
    
    """
    if not isinstance(seq, (tuple, list, range)):
        raise TypeError("expecting an iterable sequence (i.e., a tuple, a list, or a range); got %sinstead" % type(seq).__name__)
    
    seen = set()
    
    return [x for x in seq if x not in seen and not seen.add(x) ]

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

def normalized_index(data: typing.Union[typing.Sequence, int],
                     index:(str, int, tuple, list, np.ndarray, range, slice, type(None)) = None,
                     silent:bool=False, 
                     flat:bool = True,
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
    def __name_lookup__(container, name):
        names = [getattr(x, "name", None) for x in container]
        
        if silent:
            return silentindex(names, name, multiple=multiple)
        
        if len(names) == 0 or name not in names:
            warnings.warn("No element with a valid 'name' attribute or with name '%s' was found in the sequence" % name)
            return None
        
        if multiple:
            ret = [k for k, v in enumerate(names) if v == name]
            
            if len(ret) == 1:
                return ret[0]
            
            return ret
            
        return names.index(name)
            
    if not isinstance(data, (int, tuple, list)):
        raise TypeError("Expecting an int or a sequence (tuple, or list)")
    
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
        
        ret = __name_lookup__(data, index)
        
        if isinstance(ret, int) or (isinstance(ret, (tuple, list)) and len(ret) > 1):
            return tuple([ret])
        
        return tuple(ret)
        #if flat:
        
        
        #else:
            #return {}
        
        #return tuple([ret])
        
    elif isinstance(index, (tuple,  list)):
        if not all([isinstance(v, (int, str)) for v in index]):
            raise TypeError("Index sequence %s is expected to contain int only" % index)
        
        if any([isinstance(v, str) for v in index]):
            if not isinstance(data, (tuple, list)):
                raise TypeError("Name lookup requires a sequence")
            
            return tuple([v if isinstance(v, int) and v < data_len else __name_lookup__(data, v) for v in index])
            
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
        
@safeWrapper
def safe_identity_test(x, y):
    from pyqtgraph import eq
    
    try:
        ret = True
        
        ret &= type(x) == type(y)
        
        #print("safe_identity_test type(x): %s, type(y): %s" % (type(x).__name__, type(y).__name__))
        #print("safe_identity_test same type", ret)
        
        if not ret:
            return ret
        
        if hasattr(x, "size"):
            ret &= x.size == y.size
            #print("safe_identity_test same size", ret)

        if not ret:
            return ret
        
        if hasattr(x, "shape"):
            ret &= x.shape == y.shape
            #print("safe_identity_test same shape", ret)
            
        if not ret:
            return ret
        
        # NOTE: 2018-11-09 21:46:52
        # isn't this redundant after checking for shape?
        # unless an object could have shape attribte but not ndim
        if hasattr(x, "ndim"):
            ret &= x.ndim == y.ndim
        
        ret &= eq(x,y)
        
        return ret ## good fallback, though potentially expensive
    
    except Exception as e:
        #traceback.print_exc()
        #print("x:", x)
        #print("y:", y)
        return False

def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
    log = file if hasattr(file, "write") else sys.stderr
    traceback.print_stack(file=log)
    log.write(warnings.formatwarning(message, category, filename, lineno, line))
    
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
