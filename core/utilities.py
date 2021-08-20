# -*- coding: utf-8 -*-
'''
Various utilities
'''
import traceback, re, itertools, functools, time, typing, warnings, operator, random
from sys import getsizeof, stderr
from copy import (copy, deepcopy,)
from inspect import (getmro, ismodule, isclass, isbuiltin, isfunction,
                     isgeneratorfunction, iscoroutinefunction,
                     iscoroutine, isawaitable, isasyncgenfunction,
                     isasyncgen, istraceback, isframe, 
                     isabstract, ismethoddescriptor, isdatadescriptor,
                     isgetsetdescriptor, ismemberdescriptor,
                     signature,
                     )
from functools import (partial, partialmethod,)
from itertools import chain
from collections import deque, OrderedDict
from numbers import Number
import numpy as np
#from numpy import ndarray
from neo.core.dataobject import DataObject as NeoDataObject
from neo.core.container import Container as NeoContainer
import pandas as pd
import quantities as pq
#from pandas.core.base import PandasObject as PandasObject
#from quantities import Quantity as Quantity
import vigra

#import xxhash

try:
    from pyqtgraph import eq # not sure is needed
except:
    from operator import eq


from .prog import safeWrapper

from .strutils import get_int_sfx

# NOTE: 2021-07-24 15:03:53
# moved TO core.datatypes
#abbreviated_type_names = {'IPython.core.macro.Macro' : 'Macro'}
#sequence_types = (list, tuple, deque)
#sequence_typenames = ('list', 'tuple', "deque")
#set_types = (set, frozenset)
#set_typenames = ("set", "frozenset")
#dict_types = (dict,)
#dict_typenames = ("dict",)
## NOTE: neo.Segment class name clashes with nrn.Segment
#neo_containernames = ("Block", "Segment",)
## NOTE: 2020-07-10 12:52:57
## PictArray is defunct
#signal_types = ('Quantity', 'AnalogSignal', 'IrregularlySampledSignal', 
                #'SpikeTrain', "DataSignal", "IrregularlySampledDataSignal",
                #"TriggerEvent",)
                
#ndarray_type = ndarray.__name__
random.seed()
HASHRANDSEED = random.randrange(4294967295)

# NOTE: 2021-08-19 09:47:18
# moved FROM copre.workspacefunctions:
# total_size

standard_obj_summary_headers = ["Name","Workspace",
                                "Type","Data Type", 
                                "Minimum", "Maximum", "Size", "Dimensions",
                                "Shape", "Axes", "Array Order", "Memory Size",
                                ]

class SafeComparator(object):
    # NOTE: 2021-07-28 13:42:07
    # pg.eq does NOT work with numpy arrays and pandas objects!
    # operator.eq DOES work with numpy array and pandas objects!
    # and accepts non-numeric values
    # operator.le ge lt gt accept ONLY numeric values hence MAY not work with
    # either numpy array or pandas objects
    
    def __init__(comp=eq):
        self.comp = comp
        
    def __call__(self, x, y):
        try:
            ret = True
            
            ret &= type(x) == type(y)
            
            if not ret:
                return ret
            
            if isfunction(x):
                return x == y
            
            if isinstance(x, partial):
                return x.func == y.func and x.args == y.args and x.keywords == y.keywords
                
            if isinstance(x, (np.ndarray, str, Number)):
                #return operator.eq(x,y)
                return self.comp(x,y)
            
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
            
            if not ret:
                return ret
            
            if hasattr(x, "__len__") or hasattr(x, "__iter__"):
                ret &= len(x) == len(y)

                if not ret:
                    return ret
                
                ret &= all(map(lambda x_: safe_identity_test(x_[0],x_[1]),zip(x,y)))
                
                if not ret:
                    return ret
                
            ret &= self.comp(x,y)
            
            return ret ## good fallback, though potentially expensive
        
        except Exception as e:
            #traceback.print_exc()
            #print("x:", x)
            #print("y:", y)
            return False
        
def hashlist(x:typing.Iterable[typing.Any]) -> Number:
    """Takes into account the order of the elements
    
    Example 1:
    
    import random # to generate random sequences
    random.seed()
    
    # generate 10 random sequences
    k = 11
    seqs = [random.sample(range(k), k) for i in range(k)]

    seqs
    
        [[7, 5, 10, 1, 4, 2, 6, 3, 9, 8, 0],
         [9, 0, 7, 1, 5, 8, 3, 10, 6, 4, 2],
         [7, 10, 9, 3, 6, 4, 8, 1, 5, 0, 2],
         [1, 6, 8, 2, 5, 10, 9, 4, 0, 7, 3],
         [5, 7, 2, 0, 9, 6, 8, 4, 3, 10, 1],
         [6, 0, 2, 9, 7, 1, 8, 3, 4, 10, 5],
         [10, 2, 6, 7, 4, 1, 5, 9, 0, 8, 3],
         [3, 7, 5, 1, 10, 0, 9, 6, 8, 4, 2],
         [0, 5, 3, 8, 2, 9, 1, 6, 4, 7, 10],
         [9, 10, 2, 3, 5, 8, 0, 1, 4, 7, 6],
         [8, 9, 0, 3, 5, 7, 1, 4, 2, 6, 10]]    
        
    sums = [sum(hashlist(x)) for x in seqs]

    sums

        [103034808763.81586,
         103034808806.43579,
         103034808697.90562,
         103034808809.05049,
         103034808811.85916,
         103034808796.93391,
         103034808824.6124,
         103034808735.8485,
         103034808837.7218,
         103034808790.48198,
         103034808795.09956]
        
    Example 2:
    
    k = 10
    
    eye = [[0]*k for i in range(k)]
    
    for i, s in enumerate(eye):
        s[i]=1
        
    eye
    
        [[1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
         [0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
         [0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
         [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
         [0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
         [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]]

    sums = [sum(hashlist(x)) for s in eye]
    
    sums
    
        [102740977801.8254,
         102740977802.8254,
         102740977801.15872,
         102740977804.8254,
         102740977801.02539,
         102740977806.8254,
         102740977800.96825,
         102740977808.8254,
         102740977800.93651,
         102740977810.8254]
        
    """
    if not hasattr(x, "__iter__"):
        raise TypeError("Expecting an iterable; got %s instead" % type(x).__name__)
    
    return (gethash(v) * k ** p for v,k,p in zip(x, range(1, len(x)+1), itertools.cycle((-1,1))))

def gethash(x:typing.Any) -> Number:
    """Calculates a hash-like figure for objects including non-hashable
    To be used for object comparisons.
    
    Not suitable for secure code.
    
    CAUTION: some types may return same hash even if they have different content:
    These are np.ndarray and subclasses
    
    WARNING: This is NOT NECESSARILY a hash
    In particular for mutable sequences, or objects containing immutable sequences
    is very likely to return floats
    """
    from core.datatypes import is_hashable
    
    # FIXME 2021-08-20 14:23:26
    # for large data array, calculating the hash after converting to tuple may:
    # 
    # 1. incur significant overheads (for very large data)
    #
    # 2. may raise exception when the element type in the tuple is not hashable
    #   checking this may also increase overhead
    
    # Arguably, we don't need to monitor elemental vale changes in these large
    # data sets, just their ndim/shape/size/axistags, etc
    
    try:
        if isinstance(x, dict): # order is not important
            return sum((gethash(v) for v in x.values()))
        
        elif isinstance(x, (set, frozenset)): # order is not important
            return sum((gethash(v) for v in x))
        
        elif isinstance(x, (list, deque)):
            return sum(hashlist(x))
        
        elif isinstance(x, pq.Quantity):
            return sum([hash(x.dtype), hash(x.ndim), hash(x.size), hash(x.shape), hash(x.dimensionality)])
            #return HASHRANDSEED + sum([hash(x.dtype), hash(x.ndim), hash(x.size), hash(x.shape), hash(x.dimensionality)])
        
        elif isinstance(x, vigra.VigraArray):
            return gethash(np.array(x)) + hash(x.axistags)
        
        elif isinstance(x, vigra.vigranumpycore.ChunkedArrayBase):
            arsum = sum([hash(x.dtype), hash(x.ndim), hash(x.size), hash(x.shape),])
            arsum += sum([hash(x.chunk_array_shape), hash(x.chunk_shape), ])
            return arsum
            #return HASHRANDSEED + arsum
        
        elif isinstance(x, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
            return hash(x)
            #return HASHRANDSEED + hash(x)
        
        elif isinstance(x, np.ndarray):
            return sum([hash(x.shape), hash(x.size), hash(x.ndim) , hash(x.dtype)])
            #return HASHRANDSEED + sum([hash(x.shape), hash(x.size), hash(x.ndim) , hash(x.dtype)])
        
        elif isinstance(x, pd.DataFrame):
            return hash(tuple(x.index)) + hash(tuple(x.columns)) + sum((gethash(x[c]) for c in df.columns))
        
        elif isinstance(x, pd.Series):
            return hash(tuple(x.index)) + hash(tuple(x.name))  + hash(x.dtype) # + hash(tuple(x))
            #return HASHRANDSEED + hash(tuple(x.index)) + hash(tuple(x.name)) + hash(tuple(x)) + hash(x.dtype)
        
        elif isinstance(x, pd.Index):
            return hash(tuple(x)) 
            #return HASHRANDSEED + hash(tuple(x)) 
        
        elif not is_hashable(x):
            if hasattr(x, "__dict__"):
                return gethash(x.__dict__)
            
            else:
                return hash(type(x)) # FIXME 2021-08-20 14:22:13
                #return HASHRANDSEED + hash(type(x)) # FIXME 2021-08-20 14:22:13
        
        else:
            # NOTE: 2021-08-19 16:18:20
            # tuples, like all immutable basic python datatypes are hashable and their
            # hash values reflect the order of the elements
            # All user-defined classes and objects of user-defined types are also
            # hashable
            return hash(x)
            #return HASHRANDSEED + hash(x)
    except:
        return hash(type(x))
        #return HASHRANDSEED + hash(type(x))
        
def total_size(o, handlers={}, verbose=False):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    Author:
    Raymond Hettinger
    
    Reference:
    Compute memory footprint of an object and its contents (python recipe)
    
    Raymond Hettinger python recipe 577504-1
    https://code.activestate.com/recipes/577504/
    
    """
    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    deque: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers, if given, take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o_):
        if id(o_) in seen:       # do not double count the same object
            return 0
        seen.add(id(o_))
        
        s = getsizeof(o_, default_size)

        if verbose:
            print(s, type(o_), repr(o_), file=stderr)
            
        handler = all_handlers[type(o_)]
        
        s += sum(map(sizeof, handler(o_)))

        #for typ, handler in all_handlers.items():
            #if isinstance(o_, typ):
                #s += sum(map(sizeof, handler(o_)))
                #break
        return s

    return sizeof(o)

# NOTE: 2021-07-27 23:09:02
# define this here BEFORE NestedFinder so that we can use it as default value for
# comparator
@safeWrapper
def safe_identity_test2(x, y):
    return SafeComparator(comp=eq)(x, y)

@safeWrapper
def safe_identity_test(x, y, idcheck=False):
    try:
        ret = True
        
        if idcheck:
            ret &= id(x) == id(y)
            
            if not ret:
                return ret
        
        ret &= type(x) == type(y)
        
        if not ret:
            return ret
        
        if isfunction(x):
            return x == y
        
        if isinstance(x, partial):
            return x.func == y.func and x.args == y.args and x.keywords == y.keywords
            
        if isinstance(x, (np.ndarray, str, Number, pd.DataFrame, pd.Series, pd.Index)):
            return np.all(x==y)
        
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
        
        if hasattr(x, "__len__") or hasattr(x, "__iter__"):
            ret &= len(x) == len(y)

            if not ret:
                return ret
            
            ret &= all(map(lambda x_: safe_identity_test(x_[0],x_[1]),zip(x,y)))
            
            if not ret:
                return ret
            
        #if isinstance(x, (pd.DataFrame, pd.Series, pd.Index)):
            #return (x==y).all().all()
        
        #if not ret:
            #return ret
        
        #ret &= x==y
        ret &= eq(x,y)
        
        return ret ## good fallback, though potentially expensive
    
    except Exception as e:
        #traceback.print_exc()
        #print("x:", x)
        #print("y:", y)
        return False

class NestedFinder(object):
    """Provides searching in nesting (hierarchical) data structures.
    
    A nesting, or hierarchical, data structure is a mapping (dict) or sequence 
    (tuple, list, deque) where at least one elements (or value) is another 
    hierarchical data structure (dict, tuple, list, collections.deque). 
    
    These types include collections.namedtuple objects.
    
    For practical purposes, numpy arrays and pandas data types (DataFrame,
    Index and Series) are considered "leaf" objects - i.e., no further search is
    performed INSIDE their elements when these elements are of a nesting type as
    described above.
    
    """
    supported_collection_types = (np.ndarray, dict, list, tuple, deque, pd.Series, pd.DataFrame, pd.Index) # this implicitly includes namedtuple
    supported_hierarchical_types = (dict, list, tuple, deque)
    nesting_types = supported_hierarchical_types
    
    def __init__(self, src:typing.Optional[typing.Union[dict, list, tuple, deque]]=None,
                 comparator:typing.Optional[typing.Union[str, typing.Callable[..., typing.Any]]]=safe_identity_test):
        """NestedFinder initializer.
        
        Parameters:
        -----------
        data: a possibily nesting data structure. 
        
            Supported types are:
        
            np.ndarray, dict, list, tuple, deque, pd.Series, pd.DataFrame
            
        comparator: function or functools.partial (optional)
            A callable taking at least two arguments, and returns a bool.
            
            Typical binary comparators are:
                operators.eq
                pyqtgraph.eq
                Scipyen's utilities.safe_identity_test. This is the default.
            
            When None, the finder's comparator reverts to operators.eq which
            when used with numpy array will very likely raise exceptions
            
            Comparator functions can be made from functions taking additional
            parameters or keyword parameters. 
            
            For example, to use numpy' isclose:
            
            from functools import partial
            import numpy as np
            fn = partial(np, atol=1e-2, rtol=1e-2)
            
            Then pass fn as comparator parameter to the NestedFinder initializer
        """
        self._paths_ = deque()
        self._found_ = deque() # indexing objects visited
        self._result_ = deque()
        self._values_ = deque()
        self._visited_ = deque() # visited nesting types - to avoid infinite recursion
        #self._visited_ = set()
        self._data_ = src
        self._item_as_index_ = None
        self._item_as_value_ = None
        
        self._comparator_ = operator.eq # see 'operator' module for other examples
        
        isbinfun = isfunction(comparator) and len(signature(comparator).parameters) == 2
        isparfun = isinstance(comparator, partial) and len(signature(comparator.func).parameters) >= 2
        
        if isbinfun or isparfun:
            # NOTE: this can be a functools.partial
            # Foe example, np.isclose can be fed into the finder and have its keyword
            # parameters such as 'atol' and 'rtol' fixed; e.g., 
            # fn = functools.partial(np.isclose, atol=2e-2, atol-2e-2)
            # pass fn as comparator parameter here (or to self.comparator setter)
            self._comparator_ = comparator
        
    def reset(self):
        """Clears book-keeping queues, results and removes data reference
        The comparator function is left the same.
        """
        self.initialize()
        self._data_ = None
        
    def initialize(self):
        """Clears the result and book-keeping queues.
        The comparator function is left unchanged.
        """
        self._visited_.clear()
        self._paths_.clear()
        self._found_.clear()
        self._result_.clear()
        self._values_.clear()
        self._item_as_index_ = None
        self._item_as_value_ = None
        
    @property
    def comparator(self):
        """Returns the comparator function used in searching of the str '=='
        """
        return self._comparator_
    
    @comparator.setter
    def comparator(self, fn:typing.Callable[..., typing.Any]):
        """Sets the comparator function to a custom binary callable.
        A binary callable compares two arguments.
        """
        if fn is None:
            self._comparator_ = operator.eq
            return
        
        isbinfun = isfunction(fn) and len(signature(fn).parameters) == 2
        isparfun = isinstance(fn, partial) and len(signature(fn.func).parameters) >= 2
        
        if isbinfun or isparfun:
            # NOTE: this can be a functools.partial
            self._comparator_ = fn
        
    @property
    def lastSearchIndex(self):
        """Read-only acces to the last search item
        """
        return self._item_as_index_
    
    @property
    def lastSearchValue(self):
        """Read-only acces to the last search item
        """
        return self._item_as_value_
    
    @property
    def paths(self):
        """Rad-only access to the collection of indexing paths.
        Since this may be consumed in other code (e.g. self.get or 
        NestedFinder.getvalue) this property returns a deep copy of the results.
        """
        return deepcopy(self._paths_)
        
        
    @property
    def result(self):
        """Read-only, deep copy of the search result.
        Since this may be consumed in other code (e.g. self.get or 
        NestedFinder.getvalue) this property returns a deep copy of the results.
        """
        return deepcopy(self._result_)
    
    @property
    def values(self):
        """Read-only, of the collection of values found with search by index.
        
        This is a deep copy so that modifications by other code does not alter
        the collection stored in the NestedFinder.
        """
        return deepcopy(self._values_)
    
    @property
    def data(self):
        """Read/write access to the nesting data structure"""
        return self._data_
    
    @data.setter
    def data(self, src:typing.Optional[typing.Union[dict, list, tuple, deque]]=None):
        self.reset()
        self._data_ = src
        
    @staticmethod
    def is_namedtuple(x):
        """ core.datatype.is_namedtuple imported here.
        """
        from core.datatypes import is_namedtuple
        return is_namedtuple(x)
    
    def _ndx_expr(self, src, ndx):
        if isinstance(src, dict):
            if ndx in src.keys():
                if isinstance(ndx, str):
                    return "['%s']" % ndx
                else:
                    return "[%s]" % ndx
            else:
                return ""
            
        elif NestedFinder.is_namedtuple(src):
            if ndx in src._fields:
                return ".%s" % ndx
            else:
                return ""
            
        elif isinstance(src, (tuple, list, deque)):
            #print("_ndx_expr ndx", ndx, "src", src)
            if isinstance(ndx, int):
                return "[%d]" % ndx
            
            else:
                return ""
    
        elif isinstance(src, pd.DataFrame): 
            if isinstance(ndx, list) and all([isinstance(i, tuple) and len(i)==2 for i in ndx]):
                warnings.warn("Cannot generate indexing expression from multiple DataFrame indexing tuples")
                return ""
            
            elif isinstance(ndx, tuple) and len(ndx) == 2: # (row index, col index)
                if all([isinstance(i, int) for i in ndx]):
                    return ".iloc[%d, %d]" % tuple(ndx)
                else:
                    # FIXME 2021-08-16 11:28:49
                    # assumes row & column indices (labels) given as str
                    # (which is probably the most common case for DataFrame
                    # objects, but check)
                    sndx = ", ".join(["'%s'" % n if isinstance(n, str) else "%s" % n for n in ndx])
                    return ".loc[%s]" % sndx
                
        elif isinstance(src, pd.Series):
            if isinstance(ndx, list):
                warnings.warn("Cannnot generate indexing expression from multiple Series indices")
                return ""
            
            elif isinstance(ndx, int):
                return ".iloc[%d]" % ndx
                
            else:
                # FIXME see FIXME 2021-08-16 11:28:49
                return ".loc['%s']" % ndx if isinstance(ndx, str) else ".loc[%s]" % ndx
            
        elif isinstance(src, np.ndarray):
            if isinstance(ndx, np.ndarray): # length should be equal to src.ndim but this is not checked here
                aexpr = ("%s" % ndx).replace(" ", ", ")
            elif isinstance(ndx, tuple): # again, length shoudl be equal to src.ndim but this is not checked here
                aexpr = "(%s)" % ", ".join(["%s" % n for n in ndx])
                
            elif isinstance(ndx, int):
                aexpr = "%d" % ndx
                
            else:
                return ""
                
            return "[%s]" % aexpr
            
        else:
            if isinstance(ndx, int):
                return "[%d]" % ndx
            
            elif isinstance(ndx, str):
                return "['%s']" % ndx
            
            else:
                return "[%s]" % ndx

        return ""
            
    def _gen_elem(self, 
                  src:typing.Any, ndx:typing.Any, 
                  report:bool=False) -> typing.Generator[typing.Any, None, None]:
        """Element retrieval from collection given key or index
        Parameters:
        -----------
        src: python object
        ndx: key or index
        
        Yields:
        ------
        A value - when src is a collection and ndx is a valid indexing object 
            appropriate for src, src if src is an elemental object (NOT a
            collection) or nothing
        
        """
        try:
            #if ndx: # NOTE: 2021-08-17 09:07:37 when ndx == 0 (perfectly valid) this is False!
            if ndx is not None: # better be explicit
                if isinstance(src, dict):
                    if ndx in src.keys():
                        yield src[ndx]
                        
                elif NestedFinder.is_namedtuple(src):
                    if ndx in src._fields:
                        yield getattr(src, ndx)
                        
                elif isinstance(src, (tuple, list, deque)):
                    if isinstance(ndx, int) and ndx in range(len(src)): # also check validity
                        yield src[ndx]
                        
                elif isinstance(src, pd.DataFrame): 
                    # can't just  check everything, just only the basics: 
                    # for DF ndx is a (row idx, col idx) tuple or list of such
                    # if ndx not appropriate raises exceptions
                    if isinstance(ndx, list) and all([isinstance(i, tuple) and len(i)==2 for i in ndx]):
                        yield [src.iloc[ix[0], ix[1]] if all([isinstance(i, int) for i in ix]) else src.loc[ix[0], ix[1]] for ix in ndx]
                        
                    elif isinstance(ndx, tuple) and len(ndx) == 2: # (row index, col index)
                        if all([isinstance(i, int) for i in ndx]):
                            yield src.iloc[ndx[0], ndx[1]] 
                        else:
                            yield src.loc[ndx[0], ndx[1]] 
                        
                elif isinstance(src, pd.Series):
                    # can't just  check everything, just only the basics: 
                    # for Series ndx can be an int, (row) index, or a list of such
                    if isinstance(ndx, list):
                        yield [src.iloc[i] if isinstance(i, int) else src.loc[i] for i in ndx]
                        
                    elif isinstance(ndx, int):
                        yield src.iloc[ndx]
                        
                    else:
                        yield src.loc[ndx] # will raise exc if ndx not appropriate
                        
                elif isinstance(src, (np.ndarray, pd.Index)):
                    yield src[ndx]
                    
                else:
                    yield src
            
        except:
            # optionally, give some feedfback on failure
            if report:
                traceback.print_exc()
            
    def _gen_nested_value(self, src:typing.Any, 
                          path:typing.Optional[typing.List[typing.Any]]=None) -> typing.Generator[typing.Any, None, None]:
        #print("_gen_nested_value, path", path)
        if path is None or (isinstance(path , list) and len(path) == 0):
            #print("\tnot path")
            yield src
            
        if isinstance(path, deque): # begins here
            #print("start from deque")
            #while path: # NOTE: 2021-08-17 09:03:28 DON'T: [0] resolves as False!!!
            while len(path):
                pth = path.popleft()
                #print("\tpth", pth, "path", path)
                yield from self._gen_nested_value(src, pth)
                
        if isinstance(path, list): # first element is top index, then next nesting level etc
            while len(path):
                #print("src", src)
                ndx = path.pop(0)
                #print("ndx", ndx)
                g = self._gen_elem(src, ndx)
                try:
                    yield from self._gen_nested_value(next(g), path)
                    #ng = next(g)
                    #print("next_g", ng)
                    #yield from self._gen_nested_value(ng, path)
                except StopIteration:
                    pass
                
        else:# elementary indexing with POD scalars, ndarray or tuple of ndarray
            yield from self._gen_elem(src, path)
            
    def _get_path_expression(self, src, path=None):
        if not path:
            return ""
        
        expr = list()
            
        if isinstance(path, deque): # begins here
            while path:
                pth = path.popleft()
                expr.append(self._get_path_expression(src, pth))
            
            return expr
                
        if isinstance(path, list): # first element is top index, then next nesting level etc
            while len(path):
                #print("_get_path_expression path", path)
                ndx = path.pop(0)
                #print("_get_path_expression ndx", ndx, "src", src)
                expr.append(self._ndx_expr(src, ndx))
                #print("_get_path_expression expr", expr)
                g = self._gen_elem(src, ndx)
                try:
                    expr.append(self._get_path_expression(next(g), path))
                except StopIteration:
                    continue
            #print("_get_path_expression expr", expr)
            return "".join(["%s" % s for s in expr])
                
        else:# elementary indexing with POD scalars, ndarray or tuple of ndarray
            return self._ndx_expr(src, path)
            
    def _gen_search(self, var, item, parent=None, as_index=False):#, ntabs=0): # ntabs - for debugging only!
        """Generator to search item in a nesting data structure.
        
        Item can be an indexing object, or a value.
        
        Parameters:
        ----------
        var: nested data structure (dict, tuple, list, deque)
        item: object to be found; see below for details
        parent: parent indexing object (optional, default None)
        as_index:bool (default True)
        
        A nested data structure is one of:
        1. a nested mapping (dict): 
            Some of the keys may be mapped to dict or sequences, which may be 
            themselves nested data structures
        2. a nested (or ragged) sequence (deque, list, tuple):
            Some of the elements may themselves by dict, be nested data structures
        
        When 'as_index' is True (default) uses `item' as an indexing object
        inside the nested data structure: as a mapping key for dict, or integer
        index for sequences as follows.
        
        1. when item is an int if will be used as index in a sequence
        2. when item is a str it will be used ad a mapping key and as a
            namedtuple field name
        3. when item is a hashable object it will be used as dict key.
        
        NOTE: inspired from code by 
        
        hexerei software
        https://stackoverflow.com/questions/9807634/find-all-occurrences-of-a-key-in-nested-dictionaries-and-lists
        
        for the original get_dict_extract function on which this is based
        
        
        Generates:
        ---------
        a) an indexing object when item is a value (as_index is False, default)
        b) a value, when item is an indexing object (as_index = True)
        
        """
        # NOTE: 2021-07-25 00:18:52
        # For all intents and purposes ndarray are considered leaf data here.
        # We rely on numpy search routines to retrieve the index of an item
        # (as long as it is a scalar type appropriate for the nested ndarray)
        
        # NOTE: 2021-07-27 10:39:33
        # New parameter optional 'parent' represents the indexing object of the 
        # item's container - necessary to avoid unnecessary trimming of 
        # self._found_
        
        if var is None:
            var = self.data
            
            
        if isinstance(var, NestedFinder.nesting_types) and id(var) not in self._visited_:
            self._visited_.append(id(var))
            
        #print("\n%s_gen_search in %s (parent: %s)" % ("".join(["\t"] * ntabs), type(var).__name__, parent), "visited:", self._found_)
                
        if isinstance(var, dict): # search inside a dict
            # print("%s loop through %s members -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
            for k, v in var.items():
                if isinstance(v, NestedFinder.nesting_types):
                    if id(v) in self._visited_:
                        continue
                    self._visited_.append(id(v))
                
                # print("%scheck %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__),"visited:", self._found_)
                #self._found_.append(k)
                
                if as_index:
                    #if safe_identity_test(k, item): # item should be hashable 
                    #if self._comparator_(k, item): # item should be hashable 
                    if k == item:    # item should be hashable 
                        self._found_.append(k)
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._found_)
                        yield v
                        
                else:
                    #if safe_identity_test(v, item):
                    if self._comparator_(v, item):
                        self._found_.append(k)
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._found_)
                        yield k
                        
                if isinstance(v, self.supported_collection_types):
                    self._found_.append(k)
                    # print("%ssearch inside %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._found_)
                    yield from self._gen_search(v, item, k, as_index)#, ntabs+1) # ntabs for debugging
                    self._found_.pop()
                    
                # print("%sNOT FOUND in %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._found_)
                #if len(self._found_):
                    #self._found_.pop()
                
            # print("%sNOT FOUND inside %s -" % ("".join(["\t"] * ntabs), type(var).__name__, ), "visited:", self._found_)
                    
            if len(self._found_):
                #if not parent or parent != self._found_[-1]:
                if not parent or not safe_identity_test(parent, self._found_[-1]):
                    self._found_.pop()
                    # print("%sback up one from %s -" % ("".join(["\t"] * ntabs), type(var).__name__, ), "visited:", self._found_)
            
        elif NestedFinder.is_namedtuple(var): # search inside a namedtuple
            # print("%s loop through %s fields -" % ("".join(["\t"] * ntabs), type(var).__name__, ), "visited:", self._found_)
            for k in var._fields:
                v = getattr(var, k)
                if isinstance(v, NestedFinder.nesting_types):
                    if id(v) in self._visited_:
                        continue
                    self._visited_.append(id(v))
                
                self._found_.append(k)
                # print("%scheck %s field %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__), "visited:", self._found_)
                if as_index:
                    #if self._comparator_(k, item):
                    if k == item:
                        #self._found_.append(k)
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s field %s: %s -" % "".join(["\t"] * (ntabs+1)), (type(var).__name__, k, type(v).__name__, ), "visited:", self._found_)
                        yield v
                        
                else:
                    #if safe_identity_test(v, item):
                    if self._comparator_(v, item):
                        #self._found_.append(k)
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s field %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._found_)
                        yield k
                        
                if isinstance(v, self.supported_collection_types):
                    #self._found_.append(k)
                    # print("%ssearch inside %s field %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._found_)
                    yield from self._gen_search(v, item, k, as_index)#, ntabs+1) # ntabs for debugging
                    #self._found_.pop()
                        
                # print("%sNOT FOUND in %s field %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._found_)
                if len(self._found_):
                    self._found_.pop()
                
            # print("%sNOT FOUND inside %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)

            if len(self._found_):
                if not parent or not safe_identity_test(parent, self._found_[-1]):
                    self._found_.pop()
                    # print("%sback up one from %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
            
        elif isinstance(var, (list, tuple, deque)): # search inside a sequence other that any of the above
            # print("%sloop through %s elements -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
            for k, v in enumerate(var):
                if isinstance(v, NestedFinder.nesting_types):
                    if id(v) in self._visited_:
                        continue
                    self._visited_.append(id(v))
                
                # print("%scheck %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__), "visited:", self._found_)
                self._found_.append(k)
                
                if as_index:
                    #if self._comparator_(k, item):
                    if k == item:
                        #self._found_.append(k)
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._found_)
                        yield v
                        
                else:
                    #if safe_identity_test(v, item):
                    if self._comparator_(v, item):
                        #self._found_.append(k)
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._found_)
                        yield k
                        
                if isinstance(v, self.supported_collection_types):
                    #self._found_.append(k)
                    # print("%ssearch inside %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._found_)
                    yield from self._gen_search(v, item, k, as_index)#, ntabs+1) # ntabs for debugging
                    #self._found_.pop()
                    
                # print("%sNOT FOUND in %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._found_)
                if len(self._found_):
                    self._found_.pop()
                
            # print("%sNOT FOUND inside %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)

            if len(self._found_):
                if not parent or not safe_identity_test(parent, self._found_[-1]):
                    self._found_.pop()
                    # print("%sback up one from %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)

        elif isinstance(var, pd.Index):#  pd.Index is a leaf collection
            #print("in index")
            if as_index: # expects a tuple of 1D int arrays!
                if isinstance(item, np.ndarray) and item.ndims == 1:
                    try:
                        self._found_.append((item,))
                        self._paths_.append(list(self._found_))
                        yield var[item]
                        
                    except:
                        # NOTE: 2021-07-28 16:42:06
                        # uncomment for debugging
                        #traceback.print_exc()
                        pass
                        
                if isinstance(item, (tuple, list)) and len(item) == 1 and isinstance(item[0], np.ndarray) and item[0].ndim==1:
                    try:
                        self._found_.append(item)
                        self._paths_.append(list(self._found_))
                        yield var[item]
                        
                    except:
                        # NOTE: 2021-07-28 16:42:06
                        # uncomment for debugging
                        #traceback.print_exc()
                        pass
                        
            else: # => if found yields a tuple with one numpy array of int indices where found!
                try:
                    ndx = var == item # should be a boolean ndarray
                    if np.any(ndx):
                        nx = np.nonzero(np.atleast_1d(ndx))
                        self._found_.append(nx)
                        self._paths_.append(list(self._found_))
                        yield nx # tuple(ndarray(), )
                except:
                    # NOTE: 2021-07-28 16:32:28
                    # uncomment for debugging
                    #traceback.print_exc()
                    pass
                
            if len(self._found_):
                #if not parent or parent != self._found_[-1]:
                if not parent or not safe_identity_test(parent, self._found_[-1]):
                    self._found_.pop()
                    # print("%sback up one from %s -" % ("".join(["\t"] * ntabs), type(var).__name__, ), "visited:", self._found_)
            
        elif isinstance(var, (pd.DataFrame, pd.Series)): # leaf collections
            # TODO: 2021-07-28 14:07:12 TODO
            # searching for values in pandas objects is only trivial with 
            # trivial comparators (such as operator.eq)
            # TODO: for more complicated comparators e.g. numpy.isclose this needs more work
            if as_index:
                # the index appended to paths must be something to tell us that
                # it aplies to pandas DataFrame or Series objects; 
                if isinstance(var, pd.Series):
                    if isinstance(item, (tuple, list)):
                        try:
                            v = [var.iloc[ix] if isinstance(ix, (int, slice, range)) else var.loc[ix] for ix in item]
                            self._found_.append(item)
                            self._paths_.append(list(self._found_))
                            yield v
                        except:
                            # NOTE: 2021-07-28 16:32:28
                            # uncomment for debugging
                            #traceback.print_exc()
                            pass
                        
                        
                    if isinstance(item, (int, slice, range)):
                        try:
                            v = var.iloc[item]
                            self._found_.append(item)
                            self._paths_.append(list(self._found_))
                            yield v
                        except:
                            # NOTE: 2021-07-28 16:32:28
                            # uncomment for debugging
                            #traceback.print_exc()
                            pass
                        
                    else:
                        try:
                            v = var.loc[item]
                            self._found_.append(item)
                            self._paths_.append(list(self._found_))
                            yield v
                        except:
                            # NOTE: 2021-07-28 16:32:28
                            # uncomment for debugging
                            #traceback.print_exc()
                            pass
                        
                elif isinstance(var, pd.DataFrame):
                    if isinstance(item, list): # list of row, col index pairs - either as int or as row & col index objects
                        try:
                            v = [var.iloc[ix[0], ix[1]] if all ([isinstance(i, (int, slice, range)) for i in ix]) else var.loc[ix[0],ix[1]] for ix in item]
                            self._found_.append(item)
                            self._paths_.append(list(self._found_))
                            yield v
                        except:
                            # NOTE: 2021-07-28 16:32:28
                            # uncomment for debugging
                            #traceback.print_exc()
                            pass
                            
                    elif isinstance(item, tuple): # tuple of row, col indexes - either as int or as row & col index objects
                        try: # will raise exception if neither elements in item are valid
                            v = var.iloc[item[0], item[1]] if all([isinstance(i, (int, slice, range)) for i in item]) else var.loc[item[0], item[1]]
                            self._found_.append(item)
                            self._paths_.append(list(self._found_))
                            yield v # a pd.DataFrame or a pd.Series!
                        except:
                            # NOTE: 2021-07-28 16:32:28
                            # uncomment for debugging
                            #traceback.print_exc()
                            pass
                            
                    elif isinstance(item, (int, range,slice)): # int index: for dataframe retrun the item_th row as a pd.Series
                        try:
                            v = var.iloc[item,:] # this is a series
                            self._found_.append([item, slice(var.shape[1])]) # => explicit (normalized) indexing: row, col
                            self._paths_.append(list(self._found_))
                            yield v # a pd.Series
                        except:
                            try:
                                v = var.iloc[:,item] # try columns
                                self._found_.append([slice(var.shape[0]), item]) # => explicit (normalized) indexing: row, col
                                self._paths_.append(list(self._found_))
                            except:
                                # NOTE: 2021-07-28 16:32:28
                                # uncomment for debugging
                                #traceback.print_exc()
                                pass
                            
                    elif isinstance(item, pd.Index): # try to see if the index applies to the dataframe rows; _IF_ it fails, then check columns
                        try:
                            v = var.loc[item,:] # this is now a DataFrame
                            self._found_.append([item, var.columns]) # => explicit (normalized) row/col indexing; item is a row ndex
                            self._paths_.append(list(self._found_))
                            yield v # a pd.DataFrame
                            
                        except:
                            try:
                                v = var.loc[:,item] # check columns
                                self._found_.append([var.index, item]) # => explicit (normalized) row/col indexing; item is a col index
                                self._paths_.append(list(self._found_))
                                yield v
                            except:
                                # NOTE: 2021-07-28 16:32:28
                                # uncomment for debugging
                                #traceback.print_exc()
                                pass
            else:
                # FIXME: 2021-07-28 15:18:51
                # only supports scalar numbers and str for now
                # and only support identity comparison (i.e. ignores self.comparator)
                # TODO: 2021-07-28 15:20:38
                # customized support for qualified comparators e.g., np.isclose
                # and string comparisons (using pandas parser. etc) according to
                # the column's dtype
                if isinstance(item, (Number, str)):
                    try:
                        ndx = var == item
                        if np.any(ndx): # check in values
                            # creates a sequence of (row indexer, column indexer) tuples
                            # where item was found
                            # each tuple element ix in nx can then be used as
                            # df.loc[ix[0], ix[1]] to retrieve the data value in
                            # the data frame
                            if isinstance(var, pd.DataFrame):
                                nx = [(ndx.index[ndx.loc[:,c]], c) for c in var.columns[ndx.any()]]
                                
                            else:
                                nx = ndx.index[ndx]
                                
                            # NOTE: 2021-07-28 15:32:26
                            # this will append a tuple of pandas indices (row ix, col ix)!
                            # treat carefully!
                            self._found_.append(nx)
                            self._paths_.append(list(self._found_))
                            yield nx
                            
                        else: #check in indices
                            #print("check in indices in %s" % type(var).__name__)
                            if isinstance(var, pd.Series): # only row indices for Series
                                ndx = var.index == item
                                if np.any(ndx):
                                    nx = ndx.index[ndx]
                                    self._found_.append(nx)
                                    self._paths_.append(list(self._found_))
                                    yield nx
                                    
                            if isinstance(var, pd.DataFrame):
                                rowndx = var.index == item
                                #print("rowndx", np.any(rowndx))
                                if np.any(rowndx):# -> row index + all columns
                                    nx = [(ndx.index[ndx.loc[:,c]], var.columns)]
                                    self._found_.append(nx)
                                    self._paths_.append(list(self._found_))
                                    yield nx
                                    
                                colndx = var.columns == item
                                found = np.any(colndx)
                                #print("colndx", found)
                                if found: # -> all rows, given cols
                                    nx = [(var.index, var.columns[colndx])]
                                    #print("col nx", nx)
                                    self._found_.append(nx)
                                    self._paths_.append(list(self._found_))
                                    #print(self._found_)
                                    #print(self._paths_)
                                    yield nx
                            
                    except:
                        # NOTE: 2021-07-28 16:32:51
                        # uncomment for debugging
                        #traceback.print_exc()
                        pass
                            
            #print(parent)
            #print(self._found_)
            if len(self._found_):
                #if not parent or parent != self._found_[-1]:
                if not parent or not safe_identity_test(parent, self._found_[-1]):
                    self._found_.pop()
        
        elif isinstance(var, np.ndarray): # leaf collection
            # print("%slookup in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
            if as_index: # search for value at index
                # NOTE 1: 2021-07-25 00:02:37
                #
                # We DO NOT support slice indexing, indexing arrays, or other
                # fancy ndarray indexing here.
                #
                # We ONLY support the following (simple) ndarray indexing:
                # (a) indexing by an int (flat index)
                # (b) indexing by a tuple of int (one element per ndarray axis)
                # (c) indexing by a tuple of "scalar" ndarrays (with size 1)
                #     (as if output by np.nonzero)
                #
                # NOTE 2:
                # We only support ndarrays with primitive data types (for now)
                #
                # NOTE 3: When 'item' is a suitable indexing object (see NOTE 1) 
                # the function yields an indexing ndarray of size 1 as in NOTE 1
                # case (c)
                #
                # NOTE 4: When 'item' is a value to be searched for, it must be
                # cast-able to the ndarray's dtype, or an ndarray of size one &
                # same dtype as the ndarray where the search is performed
                
                if isinstance(item, int): 
                    # case (a)
                    if len(var.shape)==0 or var.ndim==0:
                        if item == 0:
                            self._found_.append(np.array([item]))
                            self._paths_.append(list(self._found_))
                            # print("%sFOUND in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
                            yield var[0]
                            
                    elif item < var.shape[0]:
                        self._found_.append(np.array([item]))
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
                        yield var[item] # may yield a subdimensional array
                        
                elif isinstance(item, (tuple, list)) and all(filter(lambda x: isinstance(x, int) or (isinstance(x, np.ndarray) and x.size==1), item)):
                    # cases (b) and (c)
                    if len(item) == var.ndim:
                        self._found_.append(np.array([item]))
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
                        yield var[tuple(item)]

            else: # search for index of value
                # FIXME 2021-07-28 15:19:40
                # only supports identity; this will almost surely fail for floats
                # TODO: 2021-07-28 15:21:54
                # customized application of qualified comparators e..g, 
                # np.isclose for numeric arrays and other comparisons for non-numeric
                # dtypes
                if isinstance(item, (Number, str)) or (isinstance(item, np.ndarray) and item.size == 1):
                    try:
                        ndx = np.array([False])
                        if isinstance(item, (Number,str)):
                            ai = np.array([item])
                            if ai.dtype == var.dtype:
                                ndx = var == item
                        
                        else:
                            if item.dtype == var.dtype:
                                ndx = var == item
                                
                        if np.any(ndx):
                            nx = np.nonzero(np.atleast_1d(ndx))
                            self._found_.append(nx)
                            self._paths_.append(list(self._found_))
                            # print("%sFOUND in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
                            yield nx
                    except:
                        # NOTE: 2021-07-28 16:32:51
                        # uncomment for debugging
                        #traceback.print_exc()
                        pass
                    
            # print("%sNOT FOUND inside %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
            
            if len(self._found_):
                if not parent or not safe_identity_test(parent, self._found_[-1]):
                    self._found_.pop()
                    # print("%sback up one in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._found_)
                
            
    def find(self, item:typing.Optional[typing.Any]=None, find_value:typing.Optional[bool]=None):
        """Search for 'item' in a nesting data structure.
        
        A nesting data structure if a collection (sequence or mapping - a dict)
        that contains other sequnences or dicts nested inside (with arbitrary
        nesting levels).
        
        Parameters (for Usage, see below):
        ----------------------------------
        
        item: object of the search (optional, default is None)
            When None, the function re-runs the last search. 
            
            The search mode (by value or by index) is determined by 'find_value'
            parameter (see below).
            
        find_value: bool (optional, default is None) 
            Determines up the search mode: by value or by index.
            
            When True: 'search by value' mode
            
                * 'item' is cosidered a value possibly contained deep inside the
                    nesting data structure
                
                * the function returns a collection of paths leading to the 
                    values identical to that of 'item' (for primitive data types),
                    or that are references to the 'item' (for other objects)
                
                * if 'item' is None, the function re-runs the last search in 
                    'search by value' mode regardless of the mode of the previous 
                    search
                
            When False: 'search by index' mode (a.k.a index lookup)
            
                * 'item' is considered an atomic indexing object (e.g. str, int, 
                    ndarray or tuple of ndarrays) possibly valid for any of the
                    containers nested in data 
                
                * the function returns a collection of found values and their
                    paths inside the nesting data structure (see below)
                
                * If 'item' is None, the function re-runs the last search in 
                    'search by index' mode regardless of the mode of the previous 
                    search
                
            When anything else (i.e. NOT a bool):
                If 'item' is None, the function re-runs the last search with the
                same mode as the previous search.
                
                Otherwise, the function runs a search for 'item', using 
                'search by value' mode (i.e., as if find_value was passed as 
                True)
                
        Returns:
        -------
        A deque.
        
        In 'search by value' mode the returned value contains paths, where each 
        path consists of the indices into nested containers with increasing 
        nesting depth (think "tree branch") leading to where the 'item' was found.
        
        These paths (either individually, or their deque container returned here)
        can be used to retrieve these values later on (see, e.g., self.get() and
        NestedFinder.getvalue()). 
        
        CAUTION: When the nesting data structure has been modified externally, 
        these paths may not be valid anymore.
        
        In 'search by index' mode, the returned value contains ('path', 'value')
        tuples, where:
        
        * 'path' is the "tree branches" leading to (and ending with) the found 
            'item' (remember, 'item' is an atomic index)
            
        * 'value' is the object found at the index that was looked up ('item')
        
        Usage:
        ------
        
        Searching can be perfomred in two modes:
        
        1) 'search-by-value'
        
        To find the index branch path of a value inside the nesting data:
        
        * pass the value as 'item', and optionally specify 'find_value' as True
        
        * the method returns a collection (deque) of indexing paths from the 
        top level to the 'leaf' index where 'item' was found
        
        2) 'search-by-index-or-key'
        
        To find values at a given index (or indexing object) inside ALL the 
            collections contained in the nesting data structure:
        
        * pass the index as 'item' and specify 'find_value' as False. 
        
        * the method returns a collection (deque) of ('path', 'value') pairs,
            where:
            * 'path' is the indexing path from the top level to the index
            specfied by 'item' (if found, and if appropriate)
        
            * 'value' is the object found at 'item' index in each of the 
            collections contained inside the nesting data structure.
            
        To split out the index branch path the correspondng vales in two 
        sequences (tuples), use the idiom:
        
            paths, values = zip(*ret) 
        
        where 'ret' is the return value of this method.
        
        The indexing object:
        -------------------------------
        An indexing object is any python object that can be used for subscript-
        or key-based access, as follows:
        
        a) a hashable object usable as dict key
        
        b) int, range, slice - for indexing into sequences and pandas.Index objects
        
        c) a str - used as dict key, or as field name in a named tuple
        
        d) pandas Index object - for use with pandas Series and DataFrame objects
        
        e) numpy ndarray with integer elements - for indexing in numpy ndarrays
        
        f) a tuple of the above as appropriate
        
        The nesting data structure
        --------------------------
        This is a collection containing other collections as elements. These 
        'nested' collections can themselves contain other nested collections, 
        and so on to an arbitrary level.
        
        The tables below describe what python types are considered nesting data
        structures, leaf, and nested data types, and the type of indexing objects
        by convention accepted here, with brief notes about their use internally.
        
        Nesting data types are collections where the search is performed recursively;
        they can be nested inside a parent nesting data.
        
        Nesting data type           Indexing object type
        -------------------------------------------------
        dict (and subclasses)       Hashable object that can be used as a key
                                    (including but not limited to int, str)
                                     
        list, tuple, deque          int, range, slice
        
        namedtuple                  int, range, slice - as for tuple
                                    str - for named field attribute-like access
        
        The following data types, although they are specialized collection types, 
        are considered as 'leaf' objects: no recursive search is performed inside
        their elements.
        
        'Leaf' data type            Indexing object type
        ------------------------------------------------
        numpy ndarray               indexing array (numpy ndarray with int or bool 
                                    elements)
                                    tuple of indexing arrays (with length matching
                                    that of the array's shape)
                                    
        pandas.Index                int, range, slice, 
                                    indexing array (as for 1D numpy ndarray)
        
        pandas.Series               pandas.Index (via Series.loc)     
                                    int, range, slice (via Series.iloc property)
                                    
        pandas.DataFrame            (rows, cols) pair of pandas.Index objects 
                                        (via DataFrame.loc)
                                    tuple of int, range, slice (row, cols)
                                        (via DataFrame.iloc)
                                        
        NOTE: Numpy ndarray objects also accept imple indexing via int, range, 
            slice; however, for numpy arrays, the finder returns "canonical" 
            indexing arrays as described above.
        
        
        ATTENTION: When the nesting (or hierarchical) data contains circular 
        references to a hierarchical data (i.e., the same python object of a
        hierachical data type is stored as a value at distinct indexing paths)
        only the first of these references is traversed (as encountered in 
        depth-first order). This is to avoid runaway recursion into otherwise
        the same hierarchical collection type.
        
        Indexing path:
        --------------
        This is a sequence (deque) of indexing objects as above, representing 
        the 'tree' path from the top level nesting data (root) to the "leaf"; 
        the root is excluded from the path.
        
        To illustrate, given a dict dd as below:
        
        dd = {"a":1, "b":{"c":2}, "c":[1,2,3]}
        
        1) Finding items with a given value:
        
        Elements with value 1 are found at the following paths:
        
        ["a"] and ["c", 0]
        
            NestedFinder(dd).find(1) --> deque([['a'], ['c', 0]])
        
        Elements with value 2 are found at the following paths:
        ["b", "c"] and ["c", 1]
        
            NestedFinder(dd).find(2) --> deque([['b', 'c'], ['c', 1]])
            
        An element with value 3 is found at ["c",2]:
        
            NestedFinder(dd).find(3) --> deque([['c', 2]])
        
        
        Furthermore: 
        
            NestedFinder(dd).find([1,2,3]) --> deque([['c']])
            
            NestedFinder(dd).find({"c":2}) --> deque([['b']])
        
        However:
        
            NestedFinder(dd).find({"c":1}) --> deque([]) # i.e., not found!
            
            NestedFinder(dd).find(4) --> deque([]) # i.e., not found!
        
        
            NestedFinder(dd).find("c") --> deque([]) # i.e., not found!
            
        
        2) Finding values given an index:
            
            NestedFinder(dd).find("c", False) 
            
            --> deque([(['b', 'c'], 2), (['c'], [1, 2, 3])])
            
            (compare with the previous example)
            
            Capture paths and values separately:
            
            paths, values  = zip(*NestedFinder(dd).find("c", False))
            
            paths 
            --> (['b', 'c'], ['c'])
            
            values 
            --> (2, [1, 2, 3])
            
        Finally, the last search (with its search mode) can be re-run by 
        calling 'find' without parameters.
            
        
        In either search mode (1) or (2) a deep copy of the collection of indexing
        paths can be obtained as the NestedFinder object's property "paths".
        
        This can be used as the 'paths' parameter for the static method
        NestedFinder.getvalue and the instance method NestedFinder.get.
        
        WARNING: Both of these methods will 'consume' the 'paths' parameter 
        and therefore this collection should be treated as volatile.
        
        See also more contrived example below.
        
        Preamble:
        ---------
        
        from collections import namedtuple
        from core.utilities import NestedFinder
        Point = namedtuple("Point", ("x", "y"))
        p = Point(11,22)
        ar = np.arange(5)
           
        d = {'b': {
                    7: 8,
                    9: [10, 11, ar],
                    '9': ar,
                    'd': p
                    },
            'd': p,
            'e': (1, p)
            }
            
        finder = NestedFinder(d)
        
        Example 1: 'search by value' mode = searching for a value retrieves the
        paths leading to it.
        -----------------------------------
        
        # ALso shows how these paths can be used to retrieve the value that was 
        # searched for (for illustration purposes, as we already have the value 
        # because we used it in the search)
        
        finder.find(p)
        --> deque([['b', 'd'], ['d'], ['e', 1]]) #  a collection of indexing paths
        
        # use the internally stored collection of indexing paths to get the leaf 
        # objects
        finder.get()
        --> Point(x=11, y=22), Point(x=11, y=22), Point(x=11, y=22)]
        
        # find another value
        finder.find(11)
        --> deque([['b', 9, 1],
                    ['b', 9, 2, (array([11]),)],
                    ['b', '9', (array([11]),)],
                    ['b', 'd', 'x'],
                    ['d', 'x'],
                    ['e', 1, 'x']])
        
        # last search parameters are stored
        finder.lastSearchIndex --> None
        finder.lastSearchValue --> 11
        
        # repeat last search
        finder.find() 
        --> deque([['b', 9, 1],
                    ['b', 9, 2, (array([11]),)],
                    ['b', '9', (array([11]),)],
                    ['b', 'd', 'x'],
                    ['d', 'x'],
                    ['e', 1, 'x']])
                    
        # retrieve the leaves using the found indexing paths 
        #
        # we searched to objects with the value 11 (an int); these are either the
        # int objects stored at (IN 'PSEUDO-CODE'):
        #
        #   d['b'][9][1]    because d['b'] is a dict, and d['b'][9] is a list 
        #                   where element at index 1 equals 11
        #
        #   d['b']['d'].x   because d['b']['d'] is a Point (namedtuple) where 
        #                   the field 'x' equals 11
        #
        #   d['e'][1].x     because d['e'] is a tuple where element at index 1 
        #                   is a Point (namedtuple) with field 'x' equal to 11
        #
        # or the ndarray elements at:
        #
        # d['b'][9][2][(array([11]),)]
        #                   because element with index 2 in the d['b'][9] list
        #                   is a numpy array where the element at [11,] equals 11
        #
        # d['b']['9'][(array([11]),)]
        #                   because d['b']['9'] is a numpy array with the element
        #                   at [11,] equal to 11
        
        finder.get()
        --> [11, array([11]), array([11]), 11, 11, 11]
        
        finder.find("x")
        --> deque([])
        
        Example 2: 'search by index' mode
        ----------------------------------
        
        finder.find("x", False)
        --> deque([(['b', 'd', 'x'], 11), (['d', 'x'], 11), (['e', 1, 'x'], 11)])
        
        ret = finder.find()
        
        ret
        --> deque([(['b', 'd', 'x'], 11), (['d', 'x'], 11), (['e', 1, 'x'], 11)])
        
        finder.lastSearchIndex --> 'x'
        finder.lastSearchValue --> None
        
        # the found values can be retrieved directly from the result:
        vals = [v[1] for v in ret]
        vals
        --> [11, 11, 11]
        
        # but if the opportunity is lost, one can access the values using the 
        # paths found in 'search by index' mode
        
        finder.get() # uses internally stored paths from last find
        --> [11, 11, 11]
        
        # or even later, by passing an externally-generated paths collection
        pth = [v[0] for v in ret]
        pth
        --> [['b', 'd', 'x'], ['d', 'x'], ['e', 1, 'x']]
        
        finder.get(pth) --> [11,11,11] # WARNING "consumes" pth (and indirectly, ret)
        pth --> [[], [], []]
        ret --> deque([([], 11), ([], 11), ([], 11)])
        
        # ret can be retrieved back
        
        ret = finder.find()
        ret
        --> deque([(['b', 'd', 'x'], 11), (['d', 'x'], 11), (['e', 1, 'x'], 11)])
        
        pth = [v[0] for v in ret]
        pth
        --> [['b', 'd', 'x'], ['d', 'x'], ['e', 1, 'x']]
        
        finder.get(deque(pth)) # WARNING "consumes" pth (and indirectly, ret)
        --> [11, 11, 11]
        
        # restore paths collection (see above)
        ret = finder.find()
        pth = [v[0] for v in ret]
        
        finder.get(pth[0], True)
        --> [11]
        pth
        --> [[], ['d', 'x'], ['e', 1, 'x']] # WARNING consumes partially
        
        To avoid the paths arguement from being consumed, pass a deep copy:
        
        from copy import deepcopy
        finder.get(deepcopy(pth[0]), True)
        
        
        When feeding a list to finder.get one must specify 'single' True/False
        depending whether the list is ONE path or a collection of paths
        finder.get(pth, True) --> TypeError: unhashable type: 'list'
        
        Example 3: One can work "outside" of a NestedFinder object.
        ------------------------------------------------------------
        
        finder = NestedFinder(d)
        del finder # goodbye 
        
        ret = finder.find("x", False)
        pth = [v[0] for v in ret]
        
        NestedFinder.getvalue(d, deepcopy(pth))
        --> [11, 11, 11]

        """
        if item is None:
            if self.lastSearchIndex:
                item = self.lastSearchIndex
                if not isinstance(find_value, bool):
                    find_value = False
                
            elif self.lastSearchValue:
                item = self.lastSearchValue
                if not isinstance(find_value, bool):
                    find_value = True
                
            else:
                return deque()
            
        if not isinstance(find_value, bool): # force the default here
            find_value = True
            
        self.initialize()
        
        self._values_ = deque(self._gen_search(self.data, item, None, not find_value))
        
        if find_value:
            self._result_ = self._paths_
            self._item_as_value_ = item
        else:
            assert len(self._values_) == len(self._paths_)
            self._result_ = deque(zip(self._paths_, self._values_))
            self._item_as_index_ = item
            
        return deepcopy(self._result_)
        
    
    def findkey(self, key_or_indexing_obj):
        """Search for value given an atomic key or indexing object
        Returns a sequence of (path, value) tuples, where path is a list of
        indexing objects (or keys) from the top to the item's nesting level,
        and value is the nested value.
        
        Calls self.find(key_or_indexing_obj, False)
        """
        return self.find(key_or_indexing_obj, False)
    
    def findindex(self, key_or_indexing_obj):
        """Calls self.findkey(key_or_indexing_obj)
        """
        return self.findkey(key_or_indexing_obj)
    
    def findvalue(self, value):
        """Search for the key or indexing object nested in self.data.
        
        Calls self.find(value, True)
        """
        return self.find(value, True)
    
    def path_expression(self, paths:typing.Optional[typing.Union[tuple, list,deque]]=None, single:bool=True):
        """Generates a str expression to be valuated on the hierarchical data
        """
        if not isinstance(paths, (deque, list, tuple)):
            if not self._paths_:
                #warnings.warn("Must run self.findvalue(val) or self.find(val, True) first")
                return []
            paths = self.paths
            
        if not isinstance(paths, deque):
            if isinstance(paths, tuple):
                paths = [paths]
                
            if not single:
                paths = deque(paths)
            
        return self._get_path_expression(self.data, paths)
    
    @staticmethod
    def paths2expression(data, paths:typing.Optional[typing.Union[tuple, list,deque]]=None, single:bool=True):
        if not isinstance(paths, (deque, list, tuple)):
            return ""
        
        if not isinstance(paths, deque):
            if not single:
                paths = deque(paths)
                
        return NestedFinder()._get_path_expression(data, paths)
            
    def get(self, paths:typing.Optional[typing.Union[tuple, list,deque]]=None, single:bool=True):
        """Retrieves nested value(s) from the internal data using indexing paths.
        
        The internal data is the nesting (hierarchical) data type established at
        initialization or later by setting the 'data' property.
        
        An indexing path is a list of atomic indexing objects, given in an 
        increasing order of nesting depth (think tree branches from the stem to
        a leaf).
        
        Several paths collected in a deque may be passed, in which case the 
        function returns a collection (sequence) of values.
        
        For other (external) nesting data use NestedFinder.getvalue() static
        method with an appropriate collection of paths (e.g. found by another 
        instance of NestedFinder).
        
        Parameters:
        ----------
        paths: tuple, list, deque; optional, default is None
        
            When None, use the indexing paths generated by the last search, see:
            self.find(), self.findindex(), self.findkey(), and self.findvalue().
            
            Type    Interpretation
            ------------------------------------------
            
            tuple:  a tuple of cordinates in a 2D+ array or a pandas DataFrame
                         ('paths' must be a pair in this case)
                                       
            list:   when 'single' is True (default): an indexing path;
                        each element is an indexing object for each nesting level
                        in increasing order (excluding the top level)
                        
                    when 'single' is False: a collection of indexing paths
                                    
            deque:  collection of indexing paths ('single' is ignored)
            
            NOTE: When 'paths' is a list or tuple, the parameter 'single' 
                specifies if 'paths' is ONE indexing path or a collection of 
                indexing  paths.
            
            WARNING The elements in 'paths' will be "consumed" (i.e., removed 
            from the collection) during the process.
            
            To avoid this side-effect, pass a deep copy here.
        
        single: bool, default is True
        
            Specifies if 'paths' is a collection of path sequences (False) or
            just a single path (True).
            
            Ignored when 'paths' is a deque.
            
            See the table above for how this modifies the function's behaviour.
        
        Returns:
        -------
        
        A (possibly empty) list of values, one for each path in the 'paths' 
        collection.
        
        Examples:
        --------
        
        See examples in NestedFinder.find
        
        See also NestedFinder.getvalue
        
        """
        if not isinstance(paths, (deque, list, tuple)):
            if not self._paths_:
                #warnings.warn("Must run self.findvalue(val) or self.find(val, True) first")
                return []
            paths = self.paths
            
        if not isinstance(paths, deque):
            if isinstance(paths, tuple):
                paths = [paths]
                
            if not single:
                paths = deque(paths)
            
        return list(self._gen_nested_value(self.data, paths))
            
    @staticmethod
    def getvalue(data, paths:typing.Optional[typing.Union[tuple, list, deque]]=None, single:bool = True):
        """Static version of NestedFinder.get.
        
        Parameters:
        -----------
        
        data: a nesting data structure
        
        paths: sequence (deque, list, tuple) of indexing paths or an indexing path.
        
            Optional, default is None, in which case returns an empty list.
            
            When a deque, this is interpreted as a collection of indexing paths.
            
        single: bool, optional (default is True)
            Ignored if 'paths' is a deque.
            
            When True, 'paths' is a single indexing path.
            
        See NestedFinder.get for details
        
        WARNING: paths must reflect the nesting structure in 'data'
        
        """
        if not isinstance(paths, (deque, list, tuple)):
            return list()
        
        if not isinstance(paths, deque):
            if not single:
                paths = deque(paths)
                
        return list(NestedFinder()._gen_nested_value(data, paths))
    
        #finder = NestedFinder()
        
        #return list(finder._gen_nested_value(data, paths))
        
    
def reverse_dict(x:dict)->dict:
    """Returns a reverse mapping (values->keys) from x
    
    Parameters:
    ==========
    x:dict
        CAUTION: the keys in 'x' must be mapped to unique values, and 
                 the values in 'x' must be of hashable types
    
    Returns:
    =======
    
    A dict mapping values to keys ('inverse' projection of 'x')
    
    """
    from .traitcontainers import (DataBag, Bunch, )
    from collections import OrderedDict
    if isinstance(x, DataBag):
        ret = DataBag((v,i) for i,v in x.items())
    elif isinstance(x, Bunch):
        ret = Bunch((v,i) for i,v in x.items())
    elif isinstance(x, OrderedDict):
        ret = OrderedDict((v,i) for i,v in x.items())
    else:
        ret = dict((v,i) for i,v in x.items())
        
    return ret

def reverse_mapping_lookup(x:dict, y:typing.Any)->typing.Optional[typing.Any]:
    """Looks up the key mapped to value y in the x mapping (dict)
    Parameters:
    ===========
    x:dict
    
    y: any type
    
    Returns:
    ========
    The key mapped to 'y', if the mapping is unique, else a tuple of keys that
    map to the same value in 'y'.
    
    Returns None if 'y' is not found among x.values()
    
    """
    #from .traitcontainers import (DataBag, Bunch, )
    #from collections import OrderedDict
    
    if y in x.values():
        ret = [name for name, val in x.items() if y == val]
        
        if len(ret) == 1:
            return ret[0]
        
        elif len(ret) > 1:
            return tuple(ret)
    
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
    from core.datatypes import (abbreviated_type_names, dict_types, dict_typenames,
                                ndarray_type, neo_containernames, 
                                sequence_types, sequence_typenames, 
                                set_types, set_typenames, signal_types, is_namedtuple, 
                                UnitTypes, )
    # NOTE: 2021-07-19 10:41:55
    # FIXME for the above 2021-07-19 10:01:35:
    # eliding is now created in gui.WorkspaceModel._get_item_for_object
    
    #NOTE: memory size is reported as follows:
        #result of obj.nbytes, for object types derived from numpy ndarray
        #result of total_size(obj) for python containers
            #by default, and as currently implemented, this is limited 
            #to python container classes (tuple, list, deque, dict, set and frozenset)
            
        #result of sys.getsizeof(obj) for any other python object
        
        #TODO construct handlers for other object types as well including 
        #PyQt5 objects (maybe)
            
    
    result = dict(map(lambda x: (x, {"display":"", "tooltip":""}), standard_obj_summary_headers))
    
    objtype = type(obj)
    typename = objtype.__name__
    
    
    wspace_name = "Namespace: %s" % namespace
    if isinstance(obj, str):
        ttip = obj
    elif isinstance(obj, (tuple, list)):
        ttip = "%s" % (obj,)
    else:
        try:
            ttip = "%s" % obj
        except:
            ttip = typename
    
    result["Name"] = {"display": "%s" % objname, "tooltip":"\n".join([ttip, wspace_name])}
    
    tt = abbreviated_type_names.get(typename, typename)
    
    if tt in signal_types and hasattr(obj, "dimensionality"):
        tt += " (%s)" % obj.dimensionality
    
    if tt == "instance":
        objcls = obj.__class__
        clsname = objcls.__name__
        
        tt = abbreviated_type_names.get(clsname, clsname)
        
    ttip = tt
        
    if is_namedtuple(obj):
        ttip += " (namedtuple)"
        
    if isabstract(obj):
        ttip += " (abstract base class)"
        
    if isframe(obj):
        ttip += " (execution stack frame)"
        
    if istraceback(obj):
        ttip += " (execution stack traceback)"
        
    if isbuiltin(obj):
        ttip = " (builtin)"
    
    if isgeneratorfunction(obj):
        ttip += " (generator function)"
        
    if iscoroutinefunction(obj):
        ttip += " (coroutine)"
        
    if isasyncgenfunction(obj):
        ttip += " (asynchronous generator function)"
        
    # Not sure if these below are needed
    if isasyncgen(obj):
        ttip += " (asynchronous generator)"
        
    if isawaitable(obj): 
        ttip += " (awaitable)"
        
    if isdatadescriptor(obj):
        ttip += " (data descriptor)"
        
    if isgetsetdescriptor(obj):
        ttip += " (getset descriptor)"
        
    if ismethoddescriptor(obj):
        ttip += " (method descriptor)"
        
    if ismemberdescriptor(obj):
        ttip += " (member descriptor)"
            
    result["Type"] = {"display": tt, "tooltip": "type: %s" % ttip}
    
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
        if isinstance(obj, sequence_types):
            if len(obj) and all([isinstance(v, Number) for v in obj]):
                datamin = str(min(obj))
                mintip = "min: "
                datamax = str(max(obj))
                maxtip = "max: "
            
            sz = str(len(obj))
            sizetip = "length: "
            
            #memsz    = str(total_size(obj)) # too slow for large collections
            memsz    = str(getsizeof(obj))
            memsztip = "memory size: "
            
        elif isinstance(obj, set_types):
            if len(obj) and all([isinstance(v, Number) for v in obj]):
                datamin = str(min([v for v in obj]))
                mintip = "min: "
                datamax = str(max([v for v in obj]))
                maxtip = "max: "
            
            sz = str(len(obj))
            sizetip = "length: "
            
            memsz    = str(getsizeof(obj))
            #memsz    = str(total_size(obj)) # too slow for large collections
            memsztip = "memory size: "
            
        elif isinstance(obj, dict_types):
            sz = str(len(obj))
            sizetip = "length: "
            
            #memsz    = str(total_size(obj)) # too slow for large collections
            memsz    = str(getsizeof(obj))
            memsztip = "memory size: "
            
        elif isinstance(obj, NeoContainer):
            sz = str(obj.size)
            sizetip = "size: "
                
            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
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
            
        elif isinstance(obj, pd.Series):
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
            
        elif isinstance(obj, pd.DataFrame):
            sz = "%s" % obj.size
            sizetip = "size: "

            ndims = "%s" % obj.ndim
            dimtip = "dimensions: "
            
            shp = str(obj.shape)
            shapetip = "shape: "

            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
        elif isinstance(obj, np.ndarray):
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
            memsztip = "memory size (bytes): "
            
            if isinstance(obj, vigra.VigraArray):
                axes    = repr(obj.axistags)
                axestip = "axes: "
                
                arrayorder    = str(obj.order)
                ordertip = "array order: "
            
            
        else:
            #vmemsize = QtGui.QStandardItem(str(getsizeof(obj)))
            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
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
        
        # NOTE: 2021-06-12 12:22:38
        # append namespace name to the tooltip at the entries other than Name, as well
        for key, value in result.items():
            if key != "Name":
                value["tooltip"] = "\n".join([value["tooltip"], wspace_name])
        
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
    
def index_of(seq, obj, key=None):
    """Find the index of obj in the object sequence seq.
    
    Objetc finding can be based on the object's identity (by default) or by the 
    value of a specific object attribute.
    
    For the latter case, 'key' must be a function - typically, a lambda function, 
    which gives access (i.e. calls a "getter") on the object attribute; the 
    attribute must support at least __eq__ (i.e. must be comparable)
    
    e.g. 
    
    index = index_of(seq, obj, key = lambda x: x.attribute)
    
    OR:
    
    index = index_of(seq, obj, key = lambda x: getattr(x, "something", None) etc
    
    
    
    Parameters:
    ----------
    seq: iterable
    obj: any pyton object
    key: function that accesses one of obj attributes; optional (default is None)
    
    Returns:
    -------
    
    The integer index of obj in seq, or None if either obj is not found in seq,
    or key(obj) is not satisfied.
    
    """
    if obj in seq:# returns None if object not in seq
        if key is None:
            return seq.index(obj)
        
        elif inspect.isfunction(key):
            lst = [key(o) for o in seq]
            return lst.index(key(obj))
    
def yyMdd(now=None):
    import string, time
    if not isinstance(now, time.struct_time):
        now = time.localtime()
        
    #year = time.strftime("%y", tuple(now))
    #month = string.ascii_lowercase[now.tm_mon-1]
    #day = time.strftime("%d", tuple(now))
    
    return "%s%s%s" % (time.strftime("%y", tuple(now)), string.ascii_lowercase[now.tm_mon-1], time.strftime("%d", tuple(now)))



def make_file_filter_string(extList, genericName):
    extensionList = [''.join(i) for i in zip('*' * len(extList), '.' * len(extList), extList)]

    fileFilterString = genericName + ' (' + ' '.join(extensionList) +')'

    individualExtensionList = ['{I} (*.{i})'.format(I=i.upper(), i=i) for i in extList]
    
    individualImageTypeFilters = ';;'.join(individualExtensionList)
    
    individualFilterStrings = ';;'.join([fileFilterString, individualImageTypeFilters])
    
    return (fileFilterString, individualFilterStrings)


def counter_suffix(x, strings, sep="_"):
    """Appends a counter suffix to x if x is found in the list of strings
    
    Parameters:
    ==========
    
    x = str: string to check for existence
    
    strings = sequence of str to check for existence of x
    
    underscore_sfx: bool default is True: and underscore separated the numeric
     suffi from the root of the string
     When False, the separator is space
    
    """
    # TODO:
    
    #base = "AboveTheSky"
    #p = re.compile("^%s_{0,1}\d*$" % base)
    #p = re.compile("^%s_{0,1}\d*$" % base)
    #items = list(filter(lambda x: p.match(x), standardQtGradientPresets.keys()))
    #items
    #names = list(standardQtGradientPresets.keys())
    #names.append("AboveTheSky_1")
    #items = list(filter(lambda x: p.match(x), names))
    #items

    if not isinstance(strings, (tuple, list)) and not hasattr(strings, "__iter__"):
        raise TypeError("Second positional parameter was expected to be an iterable; got %s instead" % type(strings).__name__)
    
    if not all ([isinstance(s, str) for s in strings]):
        raise TypeError("Second positional parameter was expected to contain str elements only")
    
    if not isinstance(sep, str):
        raise TypeError("Separator must be a str; got %s instead" % type(sep).__name__)
    
    if len(sep) == 0:
        raise ValueError("Separator cannot be an empty string")
    
    
    if len(strings):
        base, cc = get_int_sfx(x, sep=sep)
        
        #p = re.compile(base)
        p = re.compile("^%s%s{0,1}\d*$" % (base, sep))
        
        items = list(filter(lambda x: p.match(x), strings))
        
        if len(items):
            fullndx = range(1, len(items))
            full = set(fullndx)
            currentsfx = sorted(list(filter(lambda x: x, map(lambda x: get_int_sfx(x, sep=sep)[1], items))))
            current = set(currentsfx)
            if len(currentsfx):
                if min(currentsfx) > 1:
                    # first slot (base_1) is missing - fill it 
                    newsfx = 1
                    
                else:
                    if current == full:
                        # full range if indices is taken;
                        # but the 0th slot may be missing (base)
                        if base not in items:
                            # 0th slot (base) is missing:
                            return base
                        # => get the next one up (base_x, x = len(items)
                        newsfx = len(items)
                        
                    else: # set cardinality may be different, or just their elements are different
                        if len(current) == len(full):
                            # same cardinality => different elements =>
                            # neither is a subset of the other
                            # check what elements from full are NOT in currentsfx
                            # while SOME currentsfx are in full
                            missing = full - current
                            if len (missing):
                                # get the minimal slot from missing
                                newsfx = min(missing)
                            else:
                                # full and currentsfx are disjoint
                                newsfx = min(full)
                        else:
                            return base # FIXME/TODO good default ?!?
            else:
                # base not found: return the next available slot (base_1)
                newsfx = 1
                
            return sep.join([base, "%d" % newsfx])
            
        else:
            return x
                
    return x
                
def get_nested_value(src, path):
    """Returns a value contained in a hierarchical data structure.
    
    Returns None if path is not found in dict.
    
    Parameters:
    ===========
    
    src: a dictionary, or a sequence (tuple, list), possibily containing other 
        nested dict/tuple/list; 
        NOTE: all keys in the dictionary must be hashable objects
    
    path: an indexing object that points to a valid key nested in "src", or a list of
            indexing objects describing the path from the top-level dictionary src
            down to the individual "branch".
            
            Hashable objects are python object that define __hash__() and __eq__()
            functions, and have a hash value that never changes during the object's
            lifetime. Typical hashable objects are scalars and strings.
            
            When src is a tuple or list, path is expected to be a sequence of int
            (or values that can be casted to int).
            
            When src is a collections.namedtuple or a dict, path may contain a mixture of str 
            and int.
            
            NOTE: the path represents depth-first traversal of src.
    
    """
    if not isinstance(src, NestedFinder.supported_collection_types):
        raise TypeError("First parameter (%s) expected to be a %s; got %s instead" % (src, NestedFinder.supported_collection_types, type(src).__name__))
    
    if isinstance(path, (tuple, list, deque)):
        try:
            if isinstance(src, (tuple, list)):
                # here path is expected to be a sequence of int unless src is a
                # named tuple
                if isinstance(src, tuple) and isinstance(path[0], str):
                        # will raise exception if src is not a named tuple or
                        # path[0] is not a field name of src
                        value = getattr(src, path[0]) 
                else:
                    # will raise exception if casting cannot be done
                    ndx = int(path[0]) 
                                   
                
            else:
                ndx = path[0]
            
            # will raise exception if ndx is not hashable
            value = src[ndx]
            
            if len(path) == 1:
                return value
            
            if isinstance(value, (dict, tuple, list)):
                return get_nested_value(value, path[1:])
            
            else:
                return value
            
        except:
            traceback.print_exc
            return None
        
    elif isinstance(path, (str, int)):
        return get_nested_value(src, [path])
        
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

def sort_with_none(iterable, none_last = True):
    import math
    
    noneph = math.inf if none_last else -math.info
    
    return sorted(iterable, key=lambda x: x if x is not None else noneph)

def unique(seq, key=None):
    """Returns a sequence of unique elements in sequence 'seq'.
    
    Parameters:
    -----------
    seq: an iterable sequence (tuple, list, range)
    
    key: predicate for uniqueness (optional, default is None)
        Typically, this is an object returned by a lambda function
        
        e.g.
        
        unique(seq, lambda x: x._some_member_property_or_getter_function_)
    
    Returns:
    A sequence containing unique elements in 'seq'.
    
    NOTE: Does not guarantee the order of the unique elements is the same as 
            their order in 'seq'
    
    """
    if not isinstance(seq, (tuple, list, range)):
        raise TypeError("expecting an iterable sequence (i.e., a tuple, a list, or a range); got %sinstead" % type(seq).__name__)
    
    seen = set()
    
    if key is None:
        return [x for x in seq if x not in seen and not seen.add(x)]
    
    else:
        return [x for x in seq if key not in seen and not seen.add(key)]


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

