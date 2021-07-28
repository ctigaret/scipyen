# -*- coding: utf-8 -*-
'''
Various utilities
'''
import traceback, re, itertools, functools, time, typing, warnings, operator
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

from collections import deque
from numbers import Number
from sys import getsizeof
import numpy as np
from numpy import ndarray
from neo.core.dataobject import DataObject as NeoDataObject
from neo.core.container import Container as NeoContainer
import pandas as pd
#from pandas.core.base import PandasObject as PandasObject
from quantities import Quantity as Quantity
from vigra import VigraArray as VigraArray

try:
    from pyqtgraph import eq # not sure is needed
except:
    from operator import eq


from .prog import safeWrapper

from .strutils import get_int_sfx

# NOTE: 2021-07-24 15:03:53
# moved to core.datatypes
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
    
# NOTE: 2021-07-27 23:09:02
# define this here BEFORE NestedFinder so that we can use it as default value for
# comparator
@safeWrapper
def safe_identity_test2(x, y):
    return SafeComparator(comp=eq)(x, y)

@safeWrapper
def safe_identity_test(x, y):
    try:
        ret = True
        
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
    """Provides searching in deeply nesting data structures.
    
    A deeply nesting data structure is a mapping (dict) or sequence (tuple, 
    list, deque) where at least one elements (or value) is another nesting
    data structure (dict, tuple, list, deque).
    
    """
    supported_types = (np.ndarray, dict, list, tuple, deque, pd.Series, pd.DataFrame) # this implicitly includes namedtuple
    
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
        self._visited_ = deque()
        self._result_ = deque()
        self._values_ = deque()
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
        self._paths_.clear()
        self._visited_.clear()
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
    
    def _gen_elem(self, src, ndx):
        if ndx:
            if isinstance(src, dict):
                if ndx in src.keys():
                    yield src[ndx]
                    
            elif NestedFinder.is_namedtuple(src):
                if ndx in src._fields:
                    yield getattr(src, ndx)
                    
            elif isinstance(src, (tuple, list, deque)):
                if isinstance(ndx, int):
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
                    
            elif isinstance(src, np.ndarray):
                yield src[ndx]
                
            else:
                yield src
            
    def _gen_nested_value(self, src, path=None):
        #print("_gen_nested_value, path", path)
        if not path:
            #print("\tnot path")
            yield src
            
        if isinstance(path, deque): # begins here
            #print("start from deque")
            #while len(path):
            while path:
                pth = path.popleft()
                #print("\tpth", pth, "path", path)
                yield from self._gen_nested_value(src, pth)
                
        if isinstance(path, list): # first element is top index, then next nesting level etc
            while len(path):
                ndx = path.pop(0)
                g = self._gen_elem(src, ndx)
                try:
                    yield from self._gen_nested_value(next(g), path)
                except StopIteration:
                    pass
                
        else:# elementary indexing with POD scalars, ndarray or tuple of ndarray
            yield from self._gen_elem(src, path)
            
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
        
        NOTE: thanks to 
        
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
        # self._visited_
        
        if var is None:
            var = self.data
            
        # print("\n%s_gen_search in %s (parent: %s)" % ("".join(["\t"] * ntabs), type(var).__name__, parent), "visited:", self._visited_)
            
        if isinstance(var, dict): # search inside a dict
            # print("%sloop through %s members -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
            for k, v in var.items():
                self._visited_.append(k)
                
                # print("%scheck %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__),"visited:", self._visited_)
                if as_index:
                    #if safe_identity_test(k, item): # item should be hashable 
                    if self._comparator_(k, item): # item should be hashable 
                        self._paths_.append(list(self._visited_))
                        # print("%sFOUND in %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._visited_)
                        yield v
                        
                else:
                    #if safe_identity_test(v, item):
                    if self._comparator_(v, item):
                        self._paths_.append(list(self._visited_))
                        # print("%sFOUND in %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._visited_)
                        yield k
                        
                if isinstance(v, self.supported_types):
                    # print("%ssearch inside %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._visited_)
                    yield from self._gen_search(v, item, k, as_index)#, ntabs+1) # ntabs for debugging
                    
                # print("%sNOT FOUND in %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._visited_)
                
                if len(self._visited_):
                    self._visited_.pop()
                    # print("%sback up one from %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._visited_)
                    
            # print("%sNOT FOUND inside %s -" % ("".join(["\t"] * ntabs), type(var).__name__, ), "visited:", self._visited_)
                    
            if len(self._visited_):
                if not parent or parent != self._visited_[-1]:
                    self._visited_.pop()
                    # print("%sback up one from %s -" % ("".join(["\t"] * ntabs), type(var).__name__, ), "visited:", self._visited_)
                
        elif isinstance(var, (pd.DataFrame, pd.Series)):
            # TODO: 2021-07-28 14:07:12 TODO
            # searching for values in pandas objects is only trivial with 
            # trivial comparators (such as operator.eq)
            # TODO: for more complicated comparators e.g. numpy.isclose this needs more work
            if as_index:
                # the index appended to paths must be something to tell us that
                # it aplies to pandas DataFrame or Series objects; 
                if isinstance(var, pd.Series):
                    if isinstance(item, (tuple, list)):
                        self._visited_.append(item)
                        try:
                            v = [var.iloc[ix] if isinstance(ix, int) else var.loc[ix] for ix in item]
                            self._paths_.append(list(self._visited_))
                            yield v
                        except:
                            self._visited_.pop()
                        
                        
                    if isinstance(item, int):
                        self._visited_.append(item)
                        try:
                            v = var.iloc[item]
                            self._paths_.append(list(self._visited_))
                            yield v
                        except:
                            self._visited_.pop()
                        
                    else:
                        self._visited_.append(item)
                        try:
                            v = var.loc[item]
                            self._paths_.append(list(self._visited_))
                            yield v
                        except:
                            self._visited_.pop()
                        
                elif isinstance(var, pd.DataFrame):
                    if isinstance(item, list):
                        self._visited_.append(item)
                        try:
                            v = [var.iloc[ix[0], ix[1]] if all ([isinstance(i, int) for i in ix]) else var.loc[ix[0],ix[1]] for ix in item]
                            self._paths_.append(list(self._visited_))
                            yield v
                        except:
                            self._visited_.pop()
                            
                    elif isinstance(item, tuple):
                        self._visited_.append(item)
                        try:
                            v = var.loc[item[0], item[1]]
                            self._paths_.append(list(self._visited_))
                            yield v
                        except:
                            self._visited_.pop()
                            
                        
            else:
                # FIXME: only supports scalar numbers and str for now
                if isinstance(item, (Number, str)):
                    try:
                        ndx = self._comparator_(var, item)
                        if np.any(ndx):
                            # creates a sequence of (row indexer, column indexer) tuples
                            # where item was found
                            # each tuple element ix in nx can then be used as
                            # df.loc[ix[0], ix[1]] to retrieve the data value in
                            # the data frame
                            if isinstance(var, pd.DataFrame):
                                nx = [(ndx.index[ndx.loc[:,c]], c) for c in var.columns[ndx.any()]]
                                
                            else:
                                nx = ndx.index[ndx]
                                
                            self._visited_.append(nx)
                            self._paths_.append(list(self._visited_))
                            yield nx
                            
                    except:
                        pass
                            
            if len(self._visited_):
                if not parent or parent != self._visited_[-1]:
                    self._visited_.pop()
        
        
        elif isinstance(var, np.ndarray): # search inside an np.ndarray
            # print("%slookup in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
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
                            self._visited_.append(np.array[item])
                            self._paths_.append(list(self._visited_))
                            # print("%sFOUND in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
                            yield var[0]
                            
                    elif item < var.shape[0]:
                        self._visited_.append(np.array[item])
                        self._paths_.append(list(self._visited_))
                        # print("%sFOUND in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
                        yield var[item] # may yield a subdimensional array
                        
                elif isinstance(item, (tuple, list)) and all(filter(lambda x: isinstance(x, int) or (isinstance(x, np.ndarray) and x.size==1), item)):
                    # cases (b) and (c)
                    if len(item) == var.ndim:
                        self._visited_.append(np.array[item])
                        self._paths_.append(list(self._visited_))
                        # print("%sFOUND in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
                        yield var[tuple(item)]

            else: # search for index of value
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
                            self._visited_.append(nx)
                            self._paths_.append(list(self._visited_))
                            # print("%sFOUND in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
                            yield nx
                    except:
                        pass
                    
            # print("%sNOT FOUND inside %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
            
            # NOTE: 2021-07-26 17:31:03
            # DO NOT BACK UP ONE HERE: ndarray is a leaf !
            # upon reaching this point we haven't added anything to self._visited_
            # so there's nothing to back up (actually there is from the previous 
            # _gen_search call and popping it out eats out prev outcome)
            if len(self._visited_):
                if not parent or parent != self._visited_[-1]:
                    self._visited_.pop()
                    # print("%sback up one in %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
                
        elif NestedFinder.is_namedtuple(var): # search inside a namedtuple
            # print("%sloop through %s fields -" % ("".join(["\t"] * ntabs), type(var).__name__, ), "visited:", self._visited_)
            for k in var._fields:
                v = getattr(var, k)
                self._visited_.append(k)
                
                # print("%scheck %s field %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__), "visited:", self._visited_)
                if as_index:
                    if k == item:
                        self._paths_.append(list(self._visited_))
                        # print("%sFOUND in %s field %s: %s -" % "".join(["\t"] * (ntabs+1)), (type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                        yield v
                        
                else:
                    #if safe_identity_test(v, item):
                    if self._comparator_(v, item):
                        self._paths_.append(list(self._visited_))
                        # print("%sFOUND in %s field %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                        yield k
                        
                if isinstance(v, self.supported_types):
                    # print("%ssearch inside %s field %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                    yield from self._gen_search(v, item, k, as_index)#, ntabs+1) # ntabs for debugging
                        
                # print("%sNOT FOUND in %s field %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                
                if len(self._visited_):
                    self._visited_.pop()
                    # print("%sback up one from %s field %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                
            # print("%sNOT FOUND inside %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)

            # not needed !?!
            if len(self._visited_):
                if not parent or parent != self._visited_[-1]:
                    self._visited_.pop()
                    # print("%sback up one from %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
            
        elif isinstance(var, (list, tuple, deque)): # search inside a sequence other that any of the above
            # print("%sloop through %s elements -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
            for k, v in enumerate(var):
                self._visited_.append(k)
                
                # print("%scheck %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__), "visited:", self._visited_)
                if as_index:
                    if k == item:
                        self._paths_.append(list(self._visited_))
                        # print("%sFOUND in %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                        yield v
                        
                else:
                    #if safe_identity_test(v, item):
                    if self._comparator_(v, item):
                        self._paths_.append(list(self._visited_))
                        # print("%sFOUND in %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                        yield k
                        
                if isinstance(v, self.supported_types):
                    # print("%ssearch inside %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                    yield from self._gen_search(v, item, k, as_index)#, ntabs+1) # ntabs for debugging
                    
                # print("%sNOT FOUND in %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                
                if len(self._visited_):
                    self._visited_.pop()
                    # print("%sback up one from %s element %s: %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(v).__name__, ), "visited:", self._visited_)
                
            # print("%sNOT FOUND inside %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)

            # not needed !?!
            if len(self._visited_):
                if not parent or parent != self._visited_[-1]:
                    self._visited_.pop()
                    # print("%sback up one from %s -" % ("".join(["\t"] * ntabs), type(var).__name__), "visited:", self._visited_)
            
    def find(self, item:typing.Optional[typing.Any]=None, find_value:typing.Optional[bool]=None):
        """Search item in nesting data structure.
        
        When find_value is False, item is considered an indexing object (e.g. 
        a dict key, int index, ndarray or tuple of ndarrays), and the result is
        a sequence of (path, value) tuples, where:
        
        * 'path' is a list of indexing objects (or keys) leading from the top 
            level to the item's nesting level,
        * 'value' is the nested object that is equal (or identical) to item.
        
        Oherwise, the function locates the item and returns the indexing path(s)
        that lead to the nested object(s) with the same value as item (or are
        the item itself).
        
        In both cases, the read-only attributes self.values, self.paths, and 
        self.result are initialized then updated accordingly.
        
        The function returns a deep copy of self.result. This allows the result
        to be used in other code that may possibly 'consume' it (see, e.g., 
        self.get).
        
        See also the contrived example at the end of this docstring.
        
        Parameters:
        -----------
        
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
                'search by value' mode.
                
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
        
        Examples:
        --------
        
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
    
    def get(self, paths:typing.Optional[typing.Union[tuple, list,deque]]=None, single:bool=False):
        """Instance method. Retrieves nested value(s) from self.data using paths.
        
        A path is a list (or tuple) of atomic indexing objects, given in an 
        increasing order of nesting depth (think tree branches from the stem to
        a leaf).
        
        The data source is self.data.
        
        For other data sources use the static method NestedFinder.getvalue
        and an appropriate paths collection (e.g. found by another instance of
        NestedFinder).
        
        Parameters:
        ----------
        paths: tuple, list, deque; optional, default is None
        
            When None, use the deque paths collection from the last search
            (see self.find(), self.findindex, self.findkey, self.findvalue)
            
            When a list or tuple, the parameter 'single' MUST be used to specify
            if 'paths' is ONE path or a collection of paths.
            
            When a deque, 'paths' is a collection of path lists (or tuples).
            
            When 'paths' is passed by reference its elements will be "consumed".
            
            To avoid this pass a deep copy.
        
        single: bool, default is False
            Specifies if 'paths' is a collection of path sequences (False) or
            just a single path (True).
            
            See above for how this modifies the function's behaviour.
        
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
            if not single:
                paths = deque(paths)
            
        return list(self._gen_nested_value(self.data, paths))
            
    @staticmethod
    def getvalue(data, paths:typing.Optional[typing.Union[tuple, list, deque]]=None, single:bool = False):
        """Static version of NestedFinder.get.
        
        Parameters:
        -----------
        
        data: a nesting data structure
        
        paths: sequence of indexing paths or an indexing path.
        
            Optional, default is None, in which case returns an empty list.
            
        See NestedFinder.get for details
        
        WARNING: paths must reflect the nesting structure in 'data'
        
        """
        if not isinstance(paths, (deque, list, tuple)):
            return list()
        
        if not isinstance(paths, deque):
            if not single:
                paths = deque(paths)
                
        finder = NestedFinder()
        
        return list(finder._gen_nested_value(data, paths))
        
    
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
        ttip = "%s" % obj
    
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
            
        elif isinstance(obj, ndarray):
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
            
            if isinstance(obj, VigraArray):
                axes    = repr(obj.axistags)
                axestip = "axes: "
                
                arrayorder    = str(obj.order)
                ordertip = "array order: "
            
            
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
        
        # NOTE: 2021-06-12 12:22:38
        # append namespace name to the tooltip at the entries other than Name, as well
        for key, value in result.items():
            if key != "Name":
                value["tooltip"] = "\n".join([value["tooltip"], wspace_name])
            #wspace_name = "Namespace: %s" % result["Workspace"]["display"]
            #if key == "Name":
                #wnwidth = get_text_width(wspace_name)
                #if isinstance(obj, (str, Number, sequence_types, set_types, dict_types, pd.Series, pd.DataFrame, ndarray)):
                    #ttip = get_elided_text("%s: %s" % (value["tooltip"], obj), wnwidth)
                    #value["tooltip"] = "\n".join([ttip, wspace_name])
                    
            #else:
                #value["tooltip"] = "\n".join([value["tooltip"], wspace_name])
        
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
    """Returns a value contained in a nested structure src.
    
    Returns None if path is not found in dict.
    
    DEPRECATED: Use NestedFinder.getvalue or finder.get (where finder is a
    NestedFinder object)
    
    The function remains available for backward compatibility
    
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
    if not isinstance(src, NestedFinder.supported_types):
        raise TypeError("First parameter (%s) expected to be a %s; got %s instead" % (src, NestedFinder.supported_types, type(src).__name__))
    
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

