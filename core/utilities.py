# -*- coding: utf-8 -*-
'''
Various utilities
'''
import traceback, re, itertools, time, typing, warnings

from .prog import safeWrapper

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
