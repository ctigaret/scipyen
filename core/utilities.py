# -*- coding: utf-8 -*-
'''
Various utilities
'''
import traceback, re, itertools, time, typing, warnings, numbers
from sys import getsizeof
from numpy import ndarray

from .prog import safeWrapper

abbreviated_type_names = {'IPython.core.macro.Macro' : 'Macro'}
sequence_types = ['list', 'tuple', "deque"]
set_types = ["set", "frozenset"]
dict_types = ["dict"]
neo_containers =["Block", "Segment"]
# NOTE: 2020-07-10 12:52:57
# PictArray is defunct
#vigra_array_types = ["VigraArray", "PictArray"] 
vigra_array_types = ["VigraArray"]
signal_types = ['Quantity', 'AnalogSignal', 'IrregularlySampledSignal', 
                'SpikeTrain', "DataSignal", "IrregularlySampledDataSignal",
                "TriggerEvent",
                ]
ndarray_type = ndarray.__name__


standard_obj_summary_headers = ["Name","Workspace",
                                "Type","Data Type", 
                                "Minimum", "Maximum", "Size", "Dimensions",
                                "Shape", "Axes", "Array Order", "Memory Size",
                                ]


def summarize_object_properties(objname, obj, namespace="Internal"):
    """Returns a dict with object properties for display in Scipyen workspace.
    The dict keys represent the column names in the WorkspaceViewer table, and 
    are mapped to the a dict with two key: str value pairs: display, tooltip,
    where:
    
    "display" : str with the display string of the property (display role for the
                corresponding item)
    "tooltip" : str with the tooltip contents (for the tooltip role in the 
                workspace table)
                
    The contents of the dict will be used to generate a row in the Workspace Model
    with the items being displayed in the corresponding Workspace Table view in
    the Scipyen main window.
    
    """
    #NOTE: memory size is reported as follows:
        #result of obj.nbytes, for object types derived from numpy ndarray
        #result of total_size(obj) for python containers
            #by default, and as currently implemented, this is limited 
            #to python container classes (tuple, list, deque, dict, set and frozenset)
            
        #result of sys.getsizeof(obj) for any other python object
        
        #TODO construct handlers for other object types as well including 
        #PyQt5 objects (maybe)
            
    from numbers import Number
    
    result = dict(map(lambda x: (x, {"display":"", "tooltip":""}), standard_obj_summary_headers))
    
    objtype = type(obj)
    typename = objtype.__name__
    
    objcls = obj.__class__
    clsname = objcls.__name__
    
    result["Name"] = {"display": objname, "tooltip":objname}
    
    tt = abbreviated_type_names.get(typename, typename)
    
    if tt == "instance":
        tt = abbreviated_type_names.get(clsname, clsname)
        
    result["Type"] = {"display": tt, "tooltip": "type: %s" % tt}
    
    # these get assigned values below
    dtypestr = ""
    dtypetip = ""
    datamin = ""
    mintip = ""
    datamax = ""
    maxtip = ""
    sz = ""
    sizetip = ""
    ndims = ""
    dimtip = ""
    shp = ""
    shapetip = ""
    axes = ""
    axestip = ""
    arrayorder = ""
    ordertip= ""
    memsz = ""
    memsztip = ""
    

    try:
        if tt in sequence_types:
            if len(obj) and all([isinstance(v, numbers.Number) for v in obj]):
                datamin = str(min(obj))
                mintip = "min: "
                datamax = str(max(obj))
                maxtip = "max: "
            
            sz = str(len(obj))
            sizetip = "length: "
            
            #memsz    = str(total_size(obj)) # too slow for large collections
            memsz    = str(getsizeof(obj))
            memsztip = "memory size: "
            
        elif tt in set_types:
            if len(obj) and all([isinstance(v, numbers.Number) for v in obj]):
                datamin = str(min([v for v in obj]))
                mintip = "min: "
                datamax = str(max([v for v in obj]))
                maxtip = "max: "
            
            sz = str(len(obj))
            sizetip = "length: "
            
            memsz    = str(getsizeof(obj))
            #memsz    = str(total_size(obj)) # too slow for large collections
            memsztip = "memory size: "
            
        elif tt in dict_types:
            sz = str(len(obj))
            sizetip = "length: "
            
            #memsz    = str(total_size(obj)) # too slow for large collections
            memsz    = str(getsizeof(obj))
            memsztip = "memory size: "
            
        #elif tt in ('VigraArray', "PictArray"):
        elif tt in vigra_array_types:
            dtypestr = str(obj.dtype)
            dtypetip = "dtype: "
            
            if obj.size > 0:
                try:
                    if np.all(np.isnan(obj[:])):
                        datamin = str(np.nan)
                        
                    else:
                        datamin = str(np.nanmin(obj))
                        
                except:
                    pass
                
                mintip = "min: "
                
                try:
                    if np.all(np.isnan(obj[:])):
                        datamax = str(np.nan)
                    
                    else:
                        datamax  = str(np.nanmax(obj))
                        
                except:
                    pass
                
                maxtip = "max: "
                
            sz    = str(obj.size)
            sizetip = "size: "
            
            ndims   = str(obj.ndim)
            dimtip = "dimensions: "
            
            shp = str(obj.shape)
            shapetip = "shape: "
            
            axes    = repr(obj.axistags)
            axestip = "axes: "
            
            arrayorder    = str(obj.order)
            ordertip = "array order: "
            
            memsz    = str(obj.nbytes)
            #memsz    = "".join([str(getsizeof(obj)), str(obj.nbytes), "bytes"])
            memsztip = "memory size (array nbytes): "
            
        #elif tt in ('Quantity', 'AnalogSignal', 'IrregularlySampledSignal', 'SpikeTrain', "DataSignal", "IrregularlySampledDataSignal"):
        elif tt in signal_types:
            dtypestr = str(obj.dtype)
            dtypetip = "dtype: "
            
            if obj.size > 0:
                try:
                    if np.all(np.isnan(obj[:])):
                        datamin = str(np.nan)
                        
                    else:
                        datamin = str(np.nanmin(obj))
                        
                except:
                    pass
                    
                mintip = "min: "
                    
                try:
                    if np.all(np.isnan(obj[:])):
                        datamax = str(np.nan)
                        
                    else:
                        datamax  = str(np.nanmax(obj))
                        
                except:
                    pass
                
                maxtip = "max: "
                
            sz    = str(obj.size)
            sizetip = "size: "
            
            ndims   = str(obj.ndim)
            dimtip = "dimensions: "
            
            shp = str(obj.shape)
            shapetip = "shape: "
            
            memsz    = str(obj.nbytes)
            #memsz    = "".join([str(getsizeof(obj)), str(obj.nbytes), "bytes"])
            memsztip = "memory size (array nbytes): "
            
        #elif tt in ('Block', 'Segment'):
        elif tt in neo_containers:
            sz = str(obj.size)
            sizetip = "size: "
                
            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
        #elif tt == 'str':
        elif isinstance(obj, str):
            sz = str(len(obj))
            sizetip = "size: "
            
            ndims = "1"
            dimtip = "dimensions "
            
            shp = '('+str(len(obj))+',)'
            shapetip = "shape: "

            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
        elif isinstance(obj, Number):
            dtypestr = tt
            datamin = str(obj)
            mintip = "min: "
            datamax = str(obj)
            maxtip = "max: "
            sz = "1"
            sizetip = "size: "
            
            ndims = "1"
            dimtip = "dimensions: "
            
            shp = '(1,)'
            shapetip = "shape: "

            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
        #elif isinstance(obj, pd.Series):
        elif  tt == "Series":
            dtypestr = "%s" % obj.dtype
            dtypetip = "dtype: "

            sz = "%s" % obj.size
            sizetip = "size: "

            ndims = "%s" % obj.ndim
            dimtip = "dimensions: "
            
            shp = str(obj.shape)
            shapetip = "shape: "

            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
        #elif isinstance(obj, pd.DataFrame):
        elif tt == "DataFrame":
            sz = "%s" % obj.size
            sizetip = "size: "

            ndims = "%s" % obj.ndim
            dimtip = "dimensions: "
            
            shp = str(obj.shape)
            shapetip = "shape: "

            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
        elif tt == ndarray_type:
            dtypestr = str(obj.dtype)
            dtypetip = "dtype: "
            
            if obj.size > 0:
                try:
                    if np.all(np.isnan(obj[:])):
                        datamin = str(np.nan)
                        
                    else:
                        datamin = str(np.nanmin(obj))
                except:
                    pass
                    
                mintip = "min: "
                    
                try:
                    if np.all(np.isnan(obj[:])):
                        datamax = str(np.nan)
                        
                    else:
                        datamax  = str(np.nanmax(obj))
                        
                except:
                    pass
                
                maxtip = "max: "
                
            sz = str(obj.size)
            sizetip = "size: "
            
            ndims = str(obj.ndim)
            dimtip = "dimensions: "

            shp = str(obj.shape)
            shapetip = "shape: "
            
            memsz    = str(obj.nbytes)
            memsztip = "memory size: "
            
        else:
            #vmemsize = QtGui.QStandardItem(str(getsizeof(obj)))
            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
            
        #print("namespace", namespace)
            
        result["Data Type"]     = {"display": dtypestr,     "tooltip" : "%s%s" % (dtypetip, dtypestr)}
        result["Workspace"]     = {"display": namespace,    "tooltip" : "Location: %s kernel namespace" % namespace}
        result["Minimum"]       = {"display": datamin,      "tooltip" : "%s%s" % (mintip, datamin)}
        result["Maximum"]       = {"display": datamax,      "tooltip" : "%s%s" % (maxtip, datamax)}
        result["Size"]          = {"display": sz,           "tooltip" : "%s%s" % (sizetip, sz)}
        result["Dimensions"]    = {"display": ndims,        "tooltip" : "%s%s" % (dimtip, ndims)}
        result["Shape"]         = {"display": shp,          "tooltip" : "%s%s" % (shapetip, shp)}
        result["Axes"]          = {"display": axes,         "tooltip" : "%s%s" % (axestip, axes)}
        result["Array Order"]   = {"display": arrayorder,   "tooltip" : "%s%s" % (ordertip, arrayorder)}
        result["Memory Size"]   = {"display": memsz,        "tooltip" : "%s%s" % (memsztip, memsz)}
        
        for key, value in result.items():
            value["tooltip"] = "\n".join([value["tooltip"], "Namespace: %s" % result["Workspace"]["display"]])
        
    except Exception as e:
        traceback.print_exc()

    return result
    
def silentindex(a: typing.Sequence, b: typing.Any, multiple:bool = True) -> typing.Union[tuple, int]:
    """Alternative to list.index(), such that a missing value returns None
    of raising an Exception
    """
    if b in a:
        if multiple:
            return tuple([k for k, v in enumerate(a) if v is b])
        
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


def __name_lookup__(container: typing.Sequence, name:str, 
                    multiple: bool = True) -> typing.Union[tuple, int]:
    names = [getattr(x, "name") for x in container if (hasattr(x, "name") and isinstance(x.name, str) and len(x.name.strip())>0)]
    
    if len(names) == 0 or name not in names:
        warnings.warn("No element with 'name' == '%s' was found in the sequence" % name)
        return None
    
    if multiple:
        ret = tuple([k for k, v in enumerate(names) if v == name])
        
        if len(ret) == 1:
            return ret[0]
        
        return ret
        
    return names.index(name)

        
@safeWrapper
def safe_identity_test(x, y):
    from pyqtgraph import eq
    
    try:
        ret = True
        
        ret &= type(x) == type(y)
        
        if not ret:
            return ret
        
        if hasattr(x, "size"):
            ret &= x.size == y.size

        if not ret:
            return ret
        
        if hasattr(x, "shape"):
            ret &= x.shape == y.shape
            
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
