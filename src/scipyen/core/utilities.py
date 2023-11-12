# -*- coding: utf-8 -*-
'''
Various utilities
'''
import traceback, re, itertools, functools, time, typing, warnings, operator, inspect
import random, math, pprint
from numbers import Number
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
from functools import (partial, partialmethod, reduce, singledispatch)
from itertools import chain
import collections
import collections.abc
from collections import deque, OrderedDict
from dataclasses import MISSING
import numpy as np
import neo
from neo.core.dataobject import DataObject as NeoDataObject
from neo.core.container import Container as NeoContainer
import pandas as pd
import quantities as pq
import vigra
import pyqtgraph # for their own eq operator
#import language_tool_python

from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
# try:
#     from pyqtgraph import eq # not sure is needed
# except:
#     from operator import eq

from core import prog
from .prog import safeWrapper, deprecation, with_doc, is_hashable

from .strutils import get_int_sfx
from .quantities import units_convertible
from .datazone import DataZone

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
                                "Object Type","Data Type (DType)", 
                                "Minimum", "Maximum", "Size", "Dimensions",
                                "Shape", "Axes", "Array Order", "Memory Size",
                                ]

GeneralIndexType = typing.Union[str, int, typing.Union[typing.Sequence[str], typing.Sequence[int]], np.ndarray, range, slice, type(MISSING)]
"""Generic index type, used with normalized_indexed and similar functions"""

class SafeComparator(object):
    # NOTE: 2021-07-28 13:42:07
    # pg.eq does NOT work with numpy arrays and pandas objects!
    # operator.eq DOES work with numpy array and pandas objects!
    # and accepts non-numeric values
    # operator.le ge lt gt accept ONLY numeric values hence MAY not work with
    # either numpy array or pandas objects
    
    def __init__(comp=pyqtgraph.eq):
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
                if not hasattr(y, "size"):
                    return False
                ret &= x.size == y.size

            if not ret:
                return ret
            
            if hasattr(x, "shape"):
                if not hasattr(y, "shape"):
                    return False
                ret &= x.shape == y.shape
                
            if not ret:
                return ret
            
            # NOTE: 2018-11-09 21:46:52
            # isn't this redundant after checking for shape?
            # unless an object could have shape attribute but not ndim
            if hasattr(x, "ndim"):
                if not hasattr(y, "ndim"):
                    return False
                ret &= x.ndim == y.ndim
            
            if not ret:
                return ret
            
            if hasattr(x, "__len__") or hasattr(x, "__iter__"):
                if not hasattr(y, "__len__") and not hasattr(y, "__iter__"):
                    return False
                
                ret &= len(x) == len(y)

                if not ret:
                    return ret
                
                # NOTE: 2021-08-21 09:43:33 FIXME
                # ATTENTION Line below produces infinite recursion
                # when x contains a reference to itself
                #ret &= all(map(lambda x_: safe_identity_test(x_[0],x_[1]),zip(x,y)))
                
                # NOTE: 2021-08-21 09:45:48 FIXED
                ret &= all(map(lambda x_: hash_identity_test(x_[0],x_[1]),zip(x,y)))
                
                if not ret:
                    return ret
                
            ret &= self.comp(x,y)
            
            return ret ## good fallback, though potentially expensive
        
        except Exception as e:
            #traceback.print_exc()
            #print("x:", x)
            #print("y:", y)
            return False
        
def __check_isclose_args__(rtol:typing.Optional[Number]=None, 
                           atol:typing.Optional[Number]=None, 
                           use_math:bool=True, equal_nan:bool=True) -> bool:
    
    if not isinstance(rtol, Number):
        rtol = inspect.signature(math.isclose).parameters["rel_tol"].default if use_math else inspect.signature(np.isclose).parameters["rtol"].default
        
    if not isinstance(atol, Number):
        atol = inspect.signature(math.isclose).parameters["abs_tol"].default if use_math else inspect.signature(np.isclose).parameters["atol"].default
        
    f_isclose = partial(math.isclose, rel_tol=rtol, abs_tol=atol) if use_math else partial(np.isclose, rtol=rtol, atol=atol, equal_nan=equal_nan)
    
    return f_isclose, rtol, atol
        
@singledispatch
def is_same_as(x, y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
               use_math:bool=True, equal_nan:bool=False, comparator = operator.eq) -> bool:
    """Compares two objects.
    
    Parameters:
    ----------
    x,y: comparands; supported types are str, numeric scalar, complex, and
        numpy arrays (including python Quantity).
        
        NOTE: when numpy arrays, they MUST have the same dtypeand identical
        shapes, unless one of them has size 1 (one)
        
    comparator: either operator.eq (the default) or isclose (defined in this module)
        
    use_math:bool - used only when comparator is utilities.isclose, and passed on
        to that function.
        
        When True, utilities.isclose uses use math.isclose; else, use numpy.isclose
    
        NOTE: when x,y are numpy arrays, thre function uses numpy.isclose automatically.
        
    equal_nan: used only when comparator is utilities.isclose, and is passed on
    to that function
        
    rtol, atol: used when comparator is isclose and are passed on to that function
    
    """
    return operator.eq(x,y)

@is_same_as.register(str)
def _(x, y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
      use_math:bool=True, equal_nan:bool=False, comparator = operator.eq) -> bool:
    return comparator(x,y)

@is_same_as.register(np.ndarray)
def _(x,y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
      use_math:bool=True, equal_nan:bool=False, comparator = operator.eq) -> bool:
    
    if comparator not in (operator.eq, isclose):
        raise TypeError(f"'comparator' expected one of operator.eq or isclose;; got {comparator} instead")
    
    use_math = False
    
    _array_attrs_ = ("dtype", "size", "shape", "ndim")
    
    if comparator is isclose:
        comparator = partial(comparator, 
                             rtol=rtol, atol=atol, 
                             use_math=use_math, equal_nan=equal_nan)
    
    if isinstance(y, pq.Quantity):
        y = y.magnitude
        
    ret = reduce(operator.and_, (operator.eq(x_,y_) for x_, y_ in ((getattr(x, name, None), getattr(y, name, None)) for name in _array_attrs_)))
    
    if ret:
        ret &= np.all(comparator(x,y))
    
    return ret

@is_same_as.register(pq.Quantity)
def _(x,y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
      use_math:bool=True, equal_nan:bool=False, comparator = operator.eq) -> bool:
    
    if comparator not in (operator.eq, isclose):
        raise TypeError(f"'comparator' expected one of operator.eq or isclose; got {comparator} instead")
    
    use_math = False
    
    _array_attrs_ = ("dtype", "size", "shape", "ndim")
    
    if comparator is isclose:
        comparator = partial(comparator, 
                             rtol=rtol, atol=atol, 
                             use_math=use_math, equal_nan=equal_nan)
    
    if not isinstance(y, pq.Quantity):
        x = x.magnitude
        
    else:
        if not units_convertible(x,y):
            return False
        
        elif x.units != y.units:
            y = y.rescale(x.units)
            
        x=x.magnitude
        y=y.magnitude
        
    ret = reduce(operator.and_, (operator.eq(x_,y_) for x_, y_ in ((getattr(x, name, None), getattr(x, name, None)) for name in _array_attrs_)))
    
    if ret:
        ret &= np.all(comparator(x,y))
    
    return ret

@is_same_as.register(collections.abc.Sequence)
def _(x,y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None,
      use_math:bool=True, equal_nan:bool=False, comparator = operator.eq) -> bool:
    
    if comparator is isclose:
        comparator = partial(comparator, 
                             rtol=rtol, atol=atol, 
                             use_math=use_math, equal_nan=equal_nan)
    
    ret = len(x) == len(y)
    
    if ret:
        ret &= reduce(operator.and_, (comparator(x_, y_) for (x,y) in zip(x,y)))
        
    return ret

@is_same_as.register(collections.abc.Mapping)
def _(x,y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
      use_math:bool=True, equal_nan:bool=False, comparator = operator.eq) -> bool:
    
    # use for comparisons between mapping values
    simp_fun = partial(is_same_as, rtol=rtol, atol=atol, 
                       use_math=use_math, equal_nan=eual_nan,
                       comparator = comparator)
        
    if comparator is isclose:
        comparator = partial(comparator, 
                             rtol=rtol, atol=atol, 
                             use_math=use_math, equal_nan=equal_nan)
    ret = len(x) == len(y)
    if ret: # check for equality of mapping keys
        ret &= reduce(operator.and_, (operator.eq(k1, k2) for (k1, k2) in zip(x.keys(), y.keys())))
        
    if ret: # now compare the values
        ret &= reduce(operator.and_, (simp_fun(a,b) for (a,b) in zip(x.values(), y.values())))
        
    return ret

def ideq(x,y) -> bool:
    return id(x) == id(y)

@singledispatch
def isclose(x:typing.Union[Number, np.ndarray], y:typing.Union[Number, np.ndarray, pq.Quantity], rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, use_math:bool=True, equal_nan:bool=False):
    """Generalized isclose.
    
    Parameters:
    ==========
    x, y: numeric scalars or numpy arrays with identical shapes or where one of
        them has size 1; 
    
    use_math:bool, default is True
        When True, use math.isclose
        When False, use numpy.isclose
        
        When either 'x' or 'y' are numpy arrays with size > 1 the function will
        automatically switch to using numpy.isclose
        
        For differences between the math.isclose and numpy.isclose, see NOTE.
        
    rtol, atol:floats Optional, default values are as for 
        math.isclose (1e-09 and 0.0) or numpy.isclose (1e-05 and 1e-08)
        
    equal_nan:bool, optional, default is False
        Whether np.nan or math.nan are considered equal to each other
        
    Returns:
    ========
    bool scalar when math is True, else a numpy array with dtype('bool')
    
    NOTE:
    numpy.isclose:
    --------------
    Signature: np.isclose(a, b, rtol=1e-05, atol=1e-08, equal_nan=False)
    
    For finite values, isclose uses the following equation to test whether
    two floating point values are equivalent.

        absolute(`a` - `b`) <= (`atol` + `rtol` * absolute(`b`))

    Unlike the built-in `math.isclose`, the above equation is not symmetric
    in `a` and `b` -- it assumes `b` is the reference value -- so that
    `isclose(a, b)` might be different from `isclose(b, a)`. Furthermore,
    the default value of atol is not zero, and is used to determine what
    small values should be considered close to zero. the default value is
    appropriate for expected values of order unity: if the expected values
    are significantly smaller than one, it can result in false positives.
    `atol` should be carefully selected for the use case at hand. a zero value
    for `atol` will result in `False` if either `a` or `b` is zero.

    math.isclose:
    -------------
    Signature: math.isclose(a, b, *, rel_tol=1e-09, abs_tol=0.0)
    
    If no errors occur, the result will be: 
    
        abs(`a`-`b`) <= max(`rel_tol` * max(abs(`a`), abs(`b`)), `abs_tol`).

    For the values to be considered close, the difference between them
    must be smaller than at least one of the tolerances.

    -inf, inf and NaN behave similarly to the IEEE 754 Standard.  That
    is, NaN is not close to anything, even itself.  inf and -inf are
    only close to themselves.
    
    """
    raise NotImplementedError(f"{type(x).__name__} objects are not supported")

@isclose.register(str)
def _(x,y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
      use_math:bool=True, equal_nan:bool=False) -> bool:
    # TODO/FIXME: 2023-03-24 15:51:03
    # use difflib.SequenceMatcher
    from difflib import SequenceMatcher
    ret = SequenceMatcher(None, x, y).ratio()
    
    if isinstance(rtol, Number):
        return ret >= 1.0-abs(rtol)
    elif isinstance(atol, Number):
        return ret >= 1.0-abs(atol)
    else:
        return ret == 1.0
    
    # return x.lower() == y.lower()

@isclose.register(np.ndarray)
def _(x,y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
      use_math:bool=True, equal_nan:bool=False) -> bool:
    
    if any(v.size > 1 for v in (x,y)):
        use_math = False
    
    f_isclose, rtol, atol = __check_isclose_args__(rtol, atol, use_math)
    
    if isinstance(y, pq.Quantity):
        y = y.magnitude
    
    # emulate equal_nan for math.isclose
    if use_math:
        if all(v is math.nan or v is np.nan for v in (x,y)):
            return True
        
        return False
    
    return f_isclose(x,y)

@isclose.register(pq.Quantity)
def _(x,y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
      use_math:bool=True, equal_nan:bool=False) -> bool:
    
    if any(v.size > 1 for v in (x,y)):
        # use math only on scalars
        use_math = False
    
    f_isclose, rtol, atol = __check_isclose_args__(rtol, atol, use_math, equal_nan)
    
    if not isinstance(y, pq.Quantity):
        x = x.magnitude
        
    else:
        if not units_convertible(x,y):
            return False
        
        elif x.units != y.units:
            y = y.rescale(x.units)
            
        x = x.magnitude
        y = y.magnitude
    
    if use_math:
        # emulate equal_nan for math.isclose
        # NOTE: math.isclose operates only on scalars x and y
        if all(v in (math.nan, np.nan) for v in (x,y)):
            if equal_nan:
                return True
            return False
    
    return f_isclose(x,y)

@isclose.register(Number)
def _(x,y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
      use_math:bool=True, equal_nan:bool=False) -> bool:
    
    f_isclose, rtol, atol = __check_isclose_args__(rtol, atol, use_math)
    
    return f_isclose(x,y)

@isclose.register(complex)
def _(x,y, rtol:typing.Optional[Number]=None, atol:typing.Optional[Number]=None, 
      use_math:bool=True, equal_nan:bool=False) -> bool:
    
    f_isclose, rtol, atol = __check_isclose_args__(rtol, atol, use_math)
    
    return reduce(operator.and_, (f_isclose(x_, y_) for x_, y_ in ((getattr(x, name), getattr(y, name)) for name in ("real", "imag"))))

def all_or_all_not(*args) -> bool:
    """Returns True when elements in args are either all True or all False.
    """
    return all(args) or all(not(arg) for arg in args)

def hashiterable(x:typing.Iterable[typing.Any]) -> int:
    """Takes into account the order of the elements.
    
    NOTE: This works when the type of the elements contained in the iterable are
    basic Python type elements. 
    
    When the elements are iterables their type, and not their content, is 'hashed'
    in order to prevent infinite recursion when these elements contain reference(s)
    to the iterable being 'hashed'.
    
        
    """
    if not hasattr(x, "__iter__"):
        raise TypeError("Expecting an iterable; got %s instead" % type(x).__name__)
    
    # NOTE: 2021-08-21 10:02:46 FIXME
    # ATTENTION:
    # The line below generates infinite recursion when v contains references to x
    #return (gethash(v) * k ** p for v,k,p in zip(x, range(1, len(x)+1), itertools.cycle((-1,1))))
    # NOTE: 2021-08-21 10:08:01 FIXED
    return hash( (type(x),) + tuple(type(v) if hasattr(v, "__iter__") or v is x else v for v in x) )
    #return ( (hash(type(v)) if (hasattr(v, "__iter__") or v is x ) else gethash(v) ) * k ** p for v,k,p in zip(x, range(1, len(x)+1), itertools.cycle((-1,1))))
    #Example 1:
    
    #import random # to generate random sequences
    #random.seed()
    
    ## generate 10 random sequences
    #k = 11
    #seqs = [random.sample(range(k), k) for i in range(k)]

    #seqs
    
        #[[7, 5, 10, 1, 4, 2, 6, 3, 9, 8, 0],
         #[9, 0, 7, 1, 5, 8, 3, 10, 6, 4, 2],
         #[7, 10, 9, 3, 6, 4, 8, 1, 5, 0, 2],
         #[1, 6, 8, 2, 5, 10, 9, 4, 0, 7, 3],
         #[5, 7, 2, 0, 9, 6, 8, 4, 3, 10, 1],
         #[6, 0, 2, 9, 7, 1, 8, 3, 4, 10, 5],
         #[10, 2, 6, 7, 4, 1, 5, 9, 0, 8, 3],
         #[3, 7, 5, 1, 10, 0, 9, 6, 8, 4, 2],
         #[0, 5, 3, 8, 2, 9, 1, 6, 4, 7, 10],
         #[9, 10, 2, 3, 5, 8, 0, 1, 4, 7, 6],
         #[8, 9, 0, 3, 5, 7, 1, 4, 2, 6, 10]]    
        
    #sums = [sum(hashiterable(x)) for x in seqs]

    #sums

        #[103034808763.81586,
         #103034808806.43579,
         #103034808697.90562,
         #103034808809.05049,
         #103034808811.85916,
         #103034808796.93391,
         #103034808824.6124,
         #103034808735.8485,
         #103034808837.7218,
         #103034808790.48198,
         #103034808795.09956]
        
    #Example 2:
    
    #k = 10
    
    #eye = [[0]*k for i in range(k)]
    
    #for i, s in enumerate(eye):
        #s[i]=1
        
    #eye
    
        #[[1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
         #[0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
         #[0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
         #[0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
         #[0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
         #[0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
         #[0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
         #[0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
         #[0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
         #[0, 0, 0, 0, 0, 0, 0, 0, 0, 1]]

    #sums = [sum(hashiterable(x)) for s in eye]
    
    #sums
    
        #[102740977801.8254,
         #102740977802.8254,
         #102740977801.15872,
         #102740977804.8254,
         #102740977801.02539,
         #102740977806.8254,
         #102740977800.96825,
         #102740977808.8254,
         #102740977800.93651,
         #102740977810.8254]
    #return ( (hash(type(v)) if isinstance(v, (list, deque, dict)) else gethash(v) ) * k ** p for v,k,p in zip(x, range(1, len(x)+1), itertools.cycle((-1,1))))

@safeWrapper
def gethash(x:typing.Any) -> int:
    """Calculates a hash-like figure for objects (including non-hashable types)
    To be used for object comparisons.
    
    Not suitable for secure code.
    
    CAUTION: some types may return same hash even if they have different content:
    These are np.ndarray and subclasses
    
    WARNING: This is NOT NECESSARILY a hash
    In particular for mutable sequences, or objects containing immutable sequences
    is very likely to return floats
    """
    # from core.datatypes import is_hashable
    
    # FIXME 2021-08-20 14:23:26
    # for large data array, calculating the hash after converting to tuple may:
    # 
    # 1. incur significant overheads (for very large data)
    #
    # 2. may raise exception when the element type in the tuple is not hashable
    #   checking this may also increase overhead
    
    # Arguably, we don't need to monitor elemental vale changes in these large
    # data sets, just their ndim/shape/size/axistags, etc
    def _hasharr(_x):
        return hash((type(_x), _x.size, _x.shape))
        
    def _hasharrdtype(_x):
        return hash((type(x), _x.size, _x.shape, _x.dtype))

    try:
        if is_hashable(x):
            return hash(x)
        
        elif isinstance(x, pq.Quantity):
            return hash((type(x), x.size, x.shape, x.dtype, x.dimensionality))
        
        elif isinstance(x, vigra.VigraArray):
            return hash((type(x), x.size, x.shape, x.dtype, x.axistags))
        
        elif isinstance(x, vigra.vigranumpycore.ChunkedArrayBase):
            return hash((type(x), x.chunk_array_shape, x.chunk_shape))
        
        elif isinstance(x, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
            return hash(type(x), x)
        
        elif isinstance(x, np.ndarray):
            return _hasharrdtype(x)
        
        elif isinstance(x, pd.DataFrame):
            return hash((type(x), x.size, x.shape, x.dtype, x.index, x.columns))
        
        elif isinstance(x, pd.Series):
            return hash(type(x), x.size, x.shape, x.dtype, x.index, x.name)
        
        elif isinstance(x, pd.Index):
            return hash(type(x), tuple(x))
            
        elif hasattr(x, "__iter__"):
            return hash((type(x),tuple(x)))
            
        elif isinstance(x, dict):
            return hash((type(x), tuple(x)))
        
        elif not is_hashable(x):
            if hasattr(x, "__dict__"):
                return hash((type(x), x.__dict__))

            else:
                return hash(type(x)) # FIXME 2021-08-20 14:22:13
        
        else:
            # NOTE: 2021-08-19 16:18:20
            # tuples, like all immutable basic python datatypes are hashable and their
            # hash values reflect the order of the elements
            # All user-defined classes and objects of user-defined types are also
            # hashable
            return hash(type(x)) + hash(x)
    except:
        return hash(type(x))
        
def get_index_for_seq(index:int, test:typing.Sequence[typing.Any], 
                      target:typing.Sequence[typing.Any], 
                      mapping:typing.Optional[dict]=None) -> typing.Any:
    """Heuristic for computing an index into the target sequence.
    
    Returns an index into the `target` sequence given `index`:int index into
    the `test` sequence and an optional index mapping.
    
    Parameters:
    ===========
    index: int; If negative it will be treated as a negative sequence index
                (i.e., reversed indexing)
                
    test: Sequence or instance of a type implementing the methods 
        `__len__` and `__getitem__`, and for which `index` int is a valid 
        index.
    
    target: Sequence or instance of a type implementing the methods 
        `__len__` and `__getitem__`, and for which a corresponding int index
        is returned.
    
    mapping:dict; optional, default is None.
        When present, it is expected to contain key/value mappings such that:
        
        key: int, range, tuple : indices valid for the `test` sequence
        
        value: int: index valid for the `target` sequence
        
    Returns:
    =======
    int: index into the target sequence
    
    When both test and target have the same length, this is the same value 
        as `index`.
        
    When target has length 1, it always returns the value 0 (zero).
    
    Otherwise:
    
    When `mapping` is a dict with key/value pairs as above, 
        returns the value mapped to the key that:
        a) equals `index`, when key is a str
        b) contains `index`, when key is a tuple or range
        
    When `mapping` is None (the default):
    
    a) if `target` is shorter than `test`:
    a.1) for a positive `index`, the function returns:
        a.1.1) the value of `index` if index is in the semi-open interval 
            [0, len(target))
            
        a.1.2) -1 if index is >= len(target) (i.e., returns the index of
            the last element in `target`)
            
    a.2) for a negative `index` (reverse indexing) the function returns
        max(min(ndx, -1), -len(target)) where
        
        ndx = `index` + let(test) - len(target)
        
    b) if `target` is longer than `test`:
    b.1) for a positive `index` returns:
        
        min(index, len(test)-1)
        
    b.2) for a negative `index` returns:
    
        max(ndx, -len(target)) where
        
        ndx = index + len(test) - len(target)
    
    Examples:
    ========
    
    In [1]: from core.utilities import get_index_for_seq

    In [2]: a = [1,2,3,4,5,6]

    In [3]: b = [2,4,6]

    In [4]: b[get_index_for_seq(5,a,b)]
    Out[4]: 6

    In [5]: b[get_index_for_seq(2,a,b)]
    Out[5]: 6

    In [6]: b[get_index_for_seq(-1,a,b)]
    Out[6]: 6

    In [7]: b[get_index_for_seq(-5,a,b)]
    Out[7]: 4

    In [8]: b[get_index_for_seq(-6,a,b)]
    Out[8]: 2

    In [9]: a[get_index_for_seq(1, b, a)]
    Out[9]: 2

    In [10]: a[get_index_for_seq(-1, b, a)]
    Out[10]: 3

    In [11]: a[get_index_for_seq(-2, b, a)]
    Out[11]: 2

    In [12]: a[get_index_for_seq(-4, b, a)]
    
    IndexError: Index -4 out of range for test sequence

    In [13]: a[get_index_for_seq(-4, a, b)]
    Out[13]: 6
    
    
    
    """
    if not isinstance(index, int):
        raise TypeError(f"`index` expected to be an int; got {type(index).__name__} instead")
    
    if not isinstance(test, collections.abc.Sequence) or not all(hasattr(test, a) for a in ("__len__", "__getitem__")):
        raise TypeError(f"`test` expected to be a Sequence-like object; got {type(test).__name__} instead")
    
    if not isinstance(target, collections.abc.Sequence) or not all(hasattr(target, a) for a in ("__len__", "__getitem__")):
        raise TypeError(f"`target` expected to be a Sequence-like; got {type(target).__name__} instead")
    
    if index not in range(-len(test),(len(test))):
        raise IndexError(f"Index {index} out of range for test sequence")
    
    if len(target) == len(test):
        return index
    
    elif len(target) == 1:
        return 0
    
    elif isinstance(mapping, dict):
        for key in mapping:
            if (isinstance(key, int) and key == index) or (isinstance(key, range, tuple) and index in key):
                if mapping[key] in range(-len(target),(len(target))):
                    return mapping[key]
                else:
                    return IndexError(f"Index {mapping[key]} out of range for target sequence")
            
    else:
        if len(target) < len(test):
            # test posindex:    0,  1,  2,  3,  4,  5
            # test negindex:   -6, -5, -4, -3, -2, -1
            # trgt posindex:    0,  1,  2,  3
            # trgt negindex:   -4, -3, -2, -1
            # dlen = 2
            if index >= len(target):
                return - 1 # index of last element in target
                
            elif index < 0:
                dlen = len(test) - len(target)
                ndx = index + dlen
                return max(min(ndx, -1), -len(target))
                #if ndx >= 0:
                    #return -1
                #else:
                    #return ndx
                    
            else:
                return index
                
        else: # case len(target) == len(test) dealt with above
            # here len(target) > len(test)
            # test posindex:    0,  1,  2,  3
            # test negindex:   -4, -3, -2, -1
            # trgt posindex:    0,  1,  2,  3,  4,  5
            # trgt negindex:   -6, -5, -4, -3, -2, -1
            # dlen = -2
            # apply index to target[0:len(test)]
            if index < 0:
                dlen = len(test) - len(target)
                ndx = index + dlen
                return max(ndx, -len(target))
                #return min(max(ndx, -len(target)), -len(target))
                #if ndx < -len(target):
                    #return -len(target)
                #else:
                    #return ndx
            else:
                return min(index, len(test)-1)
            
def total_size(o, handlers={}, verbose=False) -> int:
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

    def sizeof(o_) -> int:
        if id(o_) in seen:       # do not double count the same object
            return 0

        seen.add(id(o_))
        
        s = getsizeof(o_, default_size)

        if verbose:
            print(s, type(o_), repr(o_), file=stderr)
            
        handler = all_handlers[type(o_)]
        
        s += sum(map(sizeof, handler(o_)))

        return s

    return sizeof(o)

# NOTE: 2021-07-27 23:09:02
# define this here BEFORE NestedFinder so that we can use it as default value for
# comparator

@safeWrapper
def hash_identity_test(x,y) -> bool:
    return gethash(x) == gethash(y)

def similar_strings(a:str, b:str) -> bool:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()

@safeWrapper
def safe_identity_test2(x, y) -> bool:
    """Uses SafeComparator object"""
    return SafeComparator(comp=eq)(x, y)

# @safeWrapper
def safe_identity_test(x, y, idcheck=False) -> bool:
    try:
        ret = True
        
        if x is y:
            return True
        
        if all(isinstance(v, type) for v in (x,y)):
            return x==y
        
        if idcheck:
            ret &= idcheck(x, y)
            if not ret:
                return ret
        
        ret &= type(x) == type(y)
        
        if not ret:
            return ret
        
        # if all(hasattr(v, "__eq__") and not isinstance(v, np.ndarray) for v in (x,y)):
        #     try:
        #         # return np.all(x == y)
        #         return x == y
        #     except:
        #         print(f"x is {type(x)}, y is {type(y)}")
        #         raise
        
        if isfunction(x):
            return x == y
        
        if isinstance(x, partial):
            return x.func == y.func and x.args == y.args and x.keywords == y.keywords
            
        if hasattr(x, "size"): # np arrays and subtypes
            if not hasattr(y, "size"):
                return False
            
            ret &= x.size == y.size

            if not ret:
                return ret
        
        elif hasattr(x, "__len__") or hasattr(x, "__iter__"): # any ContainerABC
            if not hasattr(y, "__len__") and not hasattr(y, "__iter__"):
                return False
            
            ret &= len(x) == len(y)
            
            if not ret:
                return ret
            
            if all(isinstance(v, dict) for v in (x,y)):
                # ret &= list(x.keys()) == list(y.keys())
                # if not ret:
                #     return ret
                
    #             x_items = list(filter(lambda x_: x_[1] not in (x,y), x.items()))
    #             y_items = list(filter(lambda x_: x_[1] not in (x,y), y.items()))
    #             
    #             ret &= all(map(lambda x_: safe_identity_test(x_[0], x_[1]), zip(x_items, y_items)))
                # FIXME: 2023-06-01 13:37:10
                # prone to infinite recursion when either dict is among either x.values() or y.values()
                ret &= all(map(lambda x_: safe_identity_test(x_[0], x_[1]), zip(x.items(), y.items())))
                if not ret:
                    return ret
            else:
                # FIXME: 2023-06-01 13:43:34
                # prone to infinite recursion when either element is in x or y
                ret &= all(map(lambda x_: safe_identity_test(x_[0],x_[1]),zip(x,y)))
            
            if not ret:
                return ret
            
        if hasattr(x, "shape"):
            if not hasattr(y, "shape"):
                return False
            
            ret &= x.shape == y.shape
                
            if not ret:
                return ret
        
        # NOTE: 2018-11-09 21:46:52
        # isn't this redundant after checking for shape?
        # unless an object could have shape attribte but not ndim
        if hasattr(x, "ndim"):
            if not hasattr(y, "ndim"):
                return False
            ret &= x.ndim == y.ndim
        
            if not ret:
                return ret
        
        if hasattr(x, "dtype"):
            if not hasattr(y, "dtype"):
                return False
            ret &= x.dtype == y.dtype
        
            if not ret:
                return ret
        
        if isinstance(x, (np.ndarray, str, Number, pd.DataFrame, pd.Series, pd.Index)):
            ret &= np.all(x==y)
            
            return ret
            # NOTE: 2023-05-17 08:54:39
            # event if ret was True here, not sure that falling throhugh to eq would
            # work for arrays
            # if not ret:
            #     return ret
            
        ret &= pyqtgraph.eq(x,y)
        
        return ret ## good fallback, though potentially expensive
    
    except:
        traceback.print_exc()
        frame = inspect.currentframe()
        call_stack = "\n".join([f"{fi.function} from {fi.filename} at line {fi.lineno}" for fi in inspect.getouterframes(frame)])
        print("Call stack:")
        print(call_stack)
        

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
    
    def __init__(self, src:typing.Optional[typing.Union[dict, list, tuple, deque]]=None, comparator:typing.Optional[typing.Union[str, typing.Callable[..., typing.Any]]]=safe_identity_test):
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
        """Sets the comparator function to a custom binary comparator.
        A binary comparator compares two arguments e.g., func(x, y) -> bool
        
        A comparator that also accept further optional parameters (i.e.
        named or keyword parameters) can be used by 'wrapping' in a partial where
        the ohter parameters are 'fixed' to some values:
        
        For example, the comparator:
        
        func(x, y, option=default) -> True
        
        can be passed as a partial:
        
        functools.partial(func, option=val)
        
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
            
    def _gen_elem(self, src:typing.Any, ndx:typing.Any, report:bool=False):
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
            
    def _gen_nested_value(self, src:typing.Any, path:typing.Optional[typing.List[typing.Any]]=None):
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
                
                if as_index:
                    if item == k:    # item should be hashable 
                        self._found_.append(k)
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s member %s(%s): %s -" % ("".join(["\t"] * (ntabs+1)), type(var).__name__, k, type(k).__name__, type(v).__name__, ), "visited:", self._found_)
                        yield v
                        
                else:
                    if self._comparator_(item, v):
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
                    if k == item:
                        #self._found_.append(k)
                        self._paths_.append(list(self._found_))
                        # print("%sFOUND in %s field %s: %s -" % "".join(["\t"] * (ntabs+1)), (type(var).__name__, k, type(v).__name__, ), "visited:", self._found_)
                        yield v
                        
                else:
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
    
    def findkey(self, obj):
        """Search for value given an atomic key or indexing object
        Returns a sequence of (path, value) tuples, where path is a list of
        indexing objects (or keys) from the top to the item's nesting level,
        and value is the nested value.
        
        Calls self.find(key_or_indexing_obj, False)
        """
        return self.find(obj, False)
    
    def findindex(self, obj):
        """Calls self.findkey(key_or_indexing_obj).
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
        
    
def reverse_dict(x:dict) -> dict:
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

def reverse_mapping_lookup(x:dict, y:typing.Any) -> typing.Optional[typing.Union[typing.Any, typing.Sequence[typing.Any]]]:
    """Looks up the key mapped to value y in the x mapping (dict)
    Parameters:
    ===========
    x:dict
    
    y: any type
    
    Returns:
    ========
    A tuple containing the key (if the mapping is unique) or the keys
    mapped to 'y'. This tuple may be empty if 'y' not found among 
    x.values()
    
    """
    #from .traitcontainers import (DataBag, Bunch, )
    #from collections import OrderedDict
    
    vals = list(x.values()) # bypass the errors raise when comparing np.arrays
    
    if any(isinstance(v, (np.ndarray, pd.DataFrame, pd.Series, pd.Index)) for v in vals) or isinstance(y, (np.ndarray, pd.DataFrame, pd.Series, pd.Index)):
        testincluded = any(safe_identity_test(y,v) for v in vals)
        
    else:
        testincluded = y in x.values()
    
    if testincluded:
        ret = [name for name, val in x.items() if safe_identity_test(y, val)]
        # ret = [name for name, val in x.items() if (np.all(y == val) if (isinstance(y, np.ndarray) or isinstance(val, np.ndarray)) else y == val)]
        
        return tuple(ret)
        
#         if len(ret) == 1:
#             return ret[0]
#         
#         elif len(ret) > 1:
#             return tuple(ret)
    else:
        return tuple()
    
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
    typemodulename = objtype.__module__
    objcls = obj.__class__
    clsname = objcls.__name__
    
    fqual = ".".join([objcls.__module__, clsname])
    ttip = ".".join([typemodulename, typename])
    
    if isinstance(obj, QtWidgets.QMainWindow):
        ttip = "\n".join([f"Window: {obj.windowTitle()}", ttip])
    
    wspace_name = "Namespace: %s" % namespace
    
    # NOTE: 2021-10-03 21:07:45
    # this consumes too much of resources (time & memory) and is unnecessary
    # use the short version above
    #if isinstance(obj, str):
        #ttip = obj
    #elif isinstance(obj, (tuple, list)):
        #ttip = "%s" % (obj,)
    #else:
        #try:
            #ttip = "%s" % obj
        #except:
            #ttip = typename
    
    result["Name"] = {"display": "%s" % objname, "tooltip":"\n".join([ttip, wspace_name])}
    
    tt = abbreviated_type_names.get(typename, typename)
    
    
    if tt in signal_types and hasattr(obj, "dimensionality"):
        tt += " (%s)" % obj.dimensionality
    
    if tt == "instance":
        tt = abbreviated_type_names.get(clsname, clsname)

    if objtype is type:
        tt += f" <{obj.__name__}>"
        
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
            
    # ttip += f"\n({fqual})"
    ttip += f"\n{fqual}"
    # result["Object Type"] = {"display": tt, "tooltip": "type: %s" % ttip}
    result["Object Type"] = {"display": tt, "tooltip": ttip}
    
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
        if isinstance(obj, type):
            pass
        elif isinstance(obj, sequence_types):
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
            sz = pprint.pformat(obj.size)
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
            dtype = obj.dtype
            dtypestr = "%s" % obj.dtype
            dtypetip = f"{type(dtype).__module__}.{type(dtype).__name__}"
            # dtypetip = ""
            # dtypetip = "dtype: "

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
            dtype = obj.dtype
            dtypestr = str(obj.dtype)
            dtypetip = f"{type(dtype).__module__}.{type(dtype).__name__}"
            # dtypetip = ""
            # dtypetip = "dtype: "
            
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
            
            if isinstance(obj, vigra.VigraArray) and hasattr(obj, "axistags"):
                axes    = repr(obj.axistags)
                axestip = "axes: "
                
                arrayorder    = str(obj.order)
                ordertip = "array order: "
            
        elif hasattr(obj, "__iter__"):
            if hasattr(obj, "__len__"):
                try:
                    # NOTE: 2023-01-31 17:36:53
                    # to avoid NEURON error: TypeError Most HocObject have no len()
                    sz = len(obj)
                except:
                    sz = ""
            else:
                sz = ""
            sizetip = "length:"
            memsz    = str(getsizeof(obj))
            memsztip = "memory size: "
            
        else:
            #vmemsize = QtGui.QStandardItem(str(getsizeof(obj)))
            memsz = str(getsizeof(obj))
            memsztip = "memory size: "
            
        result["Data Type (DType)"]     = {"display": dtypestr,     "tooltip" : dtypetip}
        # result["Data Type (DType)"]     = {"display": dtypestr,     "tooltip" : "%s%s" % (dtypetip, dtypestr)}
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
    
def silentindex(a: typing.Sequence, b: typing.Any, multiple:bool = True):
    """Alternative to list.index(), such that a missing value returns None
    instead of raising an Exception.
    DEPRECATED
    Use prog.filter_attr
    """
    if b in a:
        if multiple:
            return tuple([k for k, v in enumerate(a) if v is b])
        
        return a.index(b) # returns the index of first occurrence of b in a
    
    else:
        return None
    
def index_of(seq, obj, key=None, multiple=False, comparator=None):
    """Find the index of obj in the object sequence seq.
    
    Object finding can be based on the object's identity (by default) or by the 
    value of a specific object attribute. 
    
    In the former case, the object 'obj' must exist in 'seq'.
    
    In the latter case, 'key' must be a unary function - typically, a lambda
    function with access to a property of the object (i.e. calls a 'getter'
    method); the value of the property must support comparison operations
    (i.e., have at least the '__eq__' member function).
    
    This allows retrieving the index of an object with the same property value
    as 'obj', even if 'obj' is not in the sequence (when 'obj' is in the sequence,
    this MAY return the index of 'obj', when 'obj' is the first element 
    satisfying the condition in 'key')
    
    Functions with more than one parameter must accept an element of 'seq' as 
    first parameter, and can be converted to unary function using 
    functools.partial()
    
    e.g. 
    
    index = index_of(seq, obj, key = lambda x: x.attribute)
    
    OR:
    
    index = index_of(seq, obj, key = lambda x: getattr(x, "something", None) etc
        
        This represents the index of the first object with property 'something'
        having the same value as 'obj.something'
    
    Parameters:
    ----------
    seq: iterable
    
    obj: any pyton object
    
    key: function that accesses one of obj attributes; optional (default is None)
    
    multiple:bool, optional (default is False)
        When False (the default) returns a list with the index of the first 
            occurrence of 'obj' in 'seq' (that optionally satisfies 'key') - this
            behaviour is similar to that of the list.index method.
            
        When True, returns a (possibly empty) list of indices for the occurrences
            of obj in seq (that optionally also satisfy key).
            
    comparator: binary predicate function: a function taking two parameters
        and returning a bool value; optional,  default is None
        
        When None, comparison is made using the 'is' builtin.
        
        For comparing data, one may use functions in the 'operator' module
        e.g., 'operator.eq'
        
        Used when 'multiple' is True.
        
        NOTE: the 'is' builtin returns True when the two compared operands are
            symbols of the same python object (they have the same 'id').
            
            When a comparison of the contents contents of otherwise DISTINCT 
            objects is intended, then a 'comparator' binary predicate should be 
            used.
    
    Returns:
    -------
    
    A list of indices (possibly empty)
    
    """
    if key is None:
        if obj in seq:# returns None if object not in seq
            if multiple:
                if comparator is None:
                    return [k for k, o in enumerate(seq) if o is obj]
                else:
                    return [k for k, o in enumerate(seq) if comparator(o, obj)]
            return [seq.index(obj)]
        else:
            return []
    
    elif inspect.isfunction(key):
        lst = [key(o) for o in seq]
        if multiple:
            if comparator is None:
                return [k for k, v in enumerate(lst) if v is key(obj)]
            else:
                return [k for k, v in enumerate(lst) if comparator(v, key(obj))]
        else:
            if key(obj) in lst:
                return [lst.index(key(obj))]
            return list()
    
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

def elements_types(s) -> typing.Sequence[type]:
    """Returns the unique types in a sequence
    """
    return gen_unique(map(lambda x: type(x).__name__, s))


def counter_suffix(x:str, strings:typing.List[str], sep:str="_", start:int=0, ret:bool=False):
    """Appends a counter suffix to x if x is found in the list of strings
    
    Parameters:
    ==========
    
    x = str: string to check for existence
    
    strings = sequence of str to check for existence of x
    
    sep: str, default is "_"; suffix separator
    
    start: 
    
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
    
    # if len(sep.strip()) == 0:
    #     raise ValueError("Separator cannot be an empty string")
    
    if not isinstance(start, int):
        raise TypeError(f"'start' expected to be an int; got {type(start).__name__} instead")
    
    if start < 0:
        raise ValueError(f"'start' expected to be a positive int (>= 0); instead, got {start}")
    
    # print(f"counter_suffix: x = {x}, strings = {strings}, start = {start}")
    # print(f"counter_suffix: x = {x}, start = {start}, ret = {ret}")
    
    if len(strings):
        base, cc = get_int_sfx(x, sep=sep)#, bracketed=bracketed)
        
        # print(f"counter_suffix: base = {base}, cc = {cc}")
        
        #p = re.compile(base)
        # if bracketed:
        #     p = re.compile("^%s%s{0,1}\(\d*\)$" % (base, sep))
        # else:
        #     p = re.compile("^%s%s{0,1}\d*$" % (base, sep))
        p = re.compile("^%s%s{0,1}\d*$" % (base, sep))
        
        items = sorted(list(filter(lambda x: p.match(x), strings)))
        
        # print(f"counter_suffix items = {items}")
        newsfx = None
        if len(items):
            full_ndx = list(range(start, len(items)))
            currentsfx = list(x[1] for x in sorted(list(filter(lambda x: isinstance(x[1], int), (map(lambda x: get_int_sfx(x, sep=sep), items)))), key=lambda x: x[1]))
            # currentsfx = list(x[1] for x in sorted(list(filter(lambda x: isinstance(x[1], int), (map(lambda x: get_int_sfx(x, sep=sep, bracketed=bracketed), items)))), key=lambda x: x[1]))
            if len(currentsfx):
                min_current = min(currentsfx)
                max_current = max(currentsfx)
                if  len(full_ndx) == 0:
                    newsfx = 0
                else:
                    if min_current > min(full_ndx):
                        newsfx = min(full_ndx)
                    else:
                        # find out missing indices
                        if len(currentsfx) > 1:
                            dsfx = np.ediff1d(currentsfx)
                            locs = np.where(dsfx > 1)[0]
                            if len(locs):
                                newsfx = locs[0] + 1
                            else:
                                newsfx = currentsfx[-1] + 1
                        else:
                            newsfx = currentsfx[-1] + 1
                        
                    # newsfx = full_ndx[-1]
                    
            else:
                newsfx = start   
                
            # if bracketed:
            #     result = sep.join([base, "(%d)" % newsfx])
            # else:
            #     result = sep.join([base, "%d" % newsfx])
            result = sep.join([base, "%d" % newsfx])
            
            if ret:
                return result, newsfx
            
            return result
        
        else:
            result = x
            if ret:
                return x, None
            return x
        
    if ret:
        return x, None
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
    # if not isinstance(src, NestedFinder.supported_collection_types):
    #     raise TypeError("First parameter (%s) expected to be a %s; got %s instead" % (src, NestedFinder.supported_collection_types, type(src).__name__))
    
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

def pairwise(iterable)-> zip:
    """s -> (s0,s1), (s1,s2), (s2, s3), ...
    
    NOTE: Recipe from the documentation for python itertools module.
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

def sort_with_none(iterable, none_last = True) -> typing.Sequence:
    import math
    
    noneph = math.inf if none_last else -math.info
    
    return sorted(iterable, key=lambda x: x if x is not None else noneph)

def unique(seq, key=None) -> typing.Sequence:
    """Returns a sequence of unique elements in the iterable 'seq'.
    Functional version of gen_unique
    Parameters:
    -----------
    seq: an iterable (tuple, list, range, map)
    
    key: predicate for uniqueness (optional, default is None)
        Typically, this is an object returned by a lambda function
        
        e.g.
        
        unique(seq, lambda x: x._some_member_property_or_getter_function_)
    
    Returns:
    =======
    A tuple containing unique elements in 'seq'.
    
    NOTE: Does not guarantee the order of the unique elements is the same as 
            their order in 'seq'
            
    See also gen_unique for a generator version.
    
    """
    if not hasattr(seq, "__iter__"):
        raise TypeError(f"Expecting an iterable; got {type(seq).__name__} instead")
    
    return tuple(gen_unique(seq, key=key))

def gen_unique(seq, key=None):
    """Iterates through unique elements in seq
    
    Parameters:
    -----------
    seq: an iterable sequence (tuple, list, range)
    
    key: predicate for uniqueness (optional, default is None)
        When present, it is usually a unary predicate function taking an 
        element of the sequence as first parameter, and returning a bool.
        
        Predicates with more than one parameters (e.g., a comparator such as 
        operator.ge_, etc) can be converted to unary predicates by "fixing" the 
        second operand through functools.partial.
        
        
        Typically, this is an object returned by a lambda function
        
        e.g.
        
        unique(seq, lambda x: x._some_member_property_or_getter_function_)
    
    Yields:
    =======
    Unique elements in 'seq'.
    
    NOTE: Does not guarantee the order of the unique elements is the same as 
            their order in 'seq'
            
    NOTE: For most primitive and hashable python types, the following idiom is
    recommended:
    
    tuple(set(seq)) 

    where `seq` is an iterable collection of python objects.
    
    However, this function is useful to create collections of objects with unique
    elements based on a value of the objects' property, or the value of a unary 
    function applied to each object in the original collection.
    
    Also, the above idiom works only with hashable types, whereas this function
    also accepts objects of types that implement the special method __eq__, or 
    where it makes sense to compare objects using the `is` keyword.
    
    See also:
    ========
    
    unique for a function version
    
    """
    seenlist = list()
    seenset = set()
    
    # if not isinstance(seq, (tuple, list, range, deque, str)):
    if not hasattr(seq, "__iter__"):
        raise TypeError("expecting an iterable; got %s instead" % type(seq).__name__)
    
    def __check_fun_val_(x, key):
        val = key(x)
        if is_hashable(val):
            if val not in seenset:
                seenset.add(val)
                return True
            return False
            # return val not in seenset and not __add_to_seen__(val)
        else:
            if len(seenlist):
                if any(not safe_identity_test(val, x_) for x_ in seenlist):
                    seenlist.append(val)
                    ret = True
            else:
                seenlist.append(val)
                ret = True
                
            return False
            # return val not in seenlist and not __add_to_seen__(val)
            
    def __check_val__(x):
        if is_hashable(x):
            if x not in seenset:
                seenset.add(x)
                return True
            return False
            # return x not in seenset and not __add_to_seen__(x)
        else:
            if len(seenlist) == 0:
                seenlist.append(x)
                return True
                
            if all(not safe_identity_test(x, x_) for x_ in seenlist):
                seenlist.append(x)
                return True
                
            return False
        
    
    if key is None:
        # yield from (x for x in seq if x not in seen and not seen.add(x))
        # yield from (x for x in seq if x not in seen and x not in seenlist and not __add_to__seen__(x, seen, seenlist))
        yield from (x for x in seq if __check_val__(x))
    
    else:
        if inspect.isfunction(key):
            # yield from (x for x in seq if key(x) not in seen and not seen.add(key(x)))
            # yield from (x for x in seq if (key(x) not in seen and key(x) not in seenlist) and not __add_to__seen__(key(x), seen, seenlist))
            yield from (x for x in seq if __check_fun_val_(x, key))
        else:
            # yield from (x for x in seq if key not in seen and not seed.add(key))
            # yield from (x for x in seq if (key not in seen and key not in seenlist) and not __add_to__seen__(key, seen, seenlist))
            yield from (x for x in seq if __check_val__(key))
            
def name_lookup(container: typing.Sequence, name:str, multiple: bool = True) -> typing.Optional[typing.Union[int, typing.Sequence[int]]]:
    """Get indices of container elements with attribute 'name' of given value(s).
    """
    
    names = [getattr(x, "name") for x in container if (hasattr(x, "name") and isinstance(x.name, str) and len(x.name.strip())>0)]
    
    if len(names) == 0 or name not in names:
        warnings.warn(f"No element with 'name' {name} was found in the sequence")
        return None
    
    if multiple:
        ret = tuple([k for k, v in enumerate(names) if v == name])
        
        if len(ret) == 1:
            return ret[0]
        
        return ret
        
    return names.index(name)

def merge_indexes(*args) -> typing.Optional[GeneralIndexType]:
    """Merge several GeneralIndexType objects into one.
    Prerequisites:
    • each element in args must be of the same type or MISSING

    
    
    """
    
    if len(args) == 0:
        return
    
    if not all(isinstance(v, GeneralIndexType) for v in args):
        raise TypeError("Expecting a sequence of GeneralIndexType objects")
    
    not_missing = [a for a in args if not isinstance(a, type(MISSING))]
    
    if len(not_missing) == 0:
        return MISSING
    
    if not all(map(lambda x: type(x) == type(not_missing[0]), not_missing)):
        raise TypeError("All indices other than MISING must be of the same type")
    
    if isinstance(not_missing[0], (range, slice)):
        # NOTE: 2023-06-04 11:19:54
        # this works for either range or slice objects
        max_range_step = max(r.step for r in not_missing)
        min_range_start = min(r.start for r in not_missing)
        max_range_stop = max(r.stop for r in not_missing)
        mytype = type(not_missing[0])
        return mytype(min_range_start, max_range_stop, max_range_step)
    
    elif isinstance(not_missing[0], (int, str)):
        # already in a list ⇒ return it
        return not_missing
    
    elif isinstance(not_missing[0], np.ndarray):
        # concatenate, sort, then return
        if any(n.ndim > 1 for n in not_missing):
            raise TypeError(f"Expecting 1D arrays; got {not_missing[0].ndim} instead")
        
        return np.sort(np.concatenate())
    
    elif isinstance(not_missing[0], collections.abc.Iterable):
        if all(all(isinstance(v, int) for v in n) for n in not_missing) or all(all(isinstance(v, str) for v in n) for n in not_missing):
            ret = itertools.chain.from_iterable(not_missing)
            return sorted(ret)
        else:
            raise TypeError("Can only merge all int or all str indexing objects")
        
    else:
        raise TypeError(f"Invalid types for index merging: {type(not_missing[0]).__name__}")
    
@with_doc(prog.filter_attr, use_header = True)
# @singledispatch
def normalized_index(data: typing.Optional[typing.Union[collections.abc.Sequence, int, pd.core.indexes.base.Index, pd.DataFrame, pd.Series, np.ndarray]], 
                     index: typing.Optional[GeneralIndexType] = None, 
                     silent:bool=False, axis:typing.Optional[int] = None) -> typing.Union[range, typing.Iterable[int]]:
    """Transform various indexing objects to a range or an iterable of int indices.
    
Also checks the validity of the index for an iterable, given its size.

Parameters:
-----------
data: collections.abc.Sequence, int, pd.core.indexes.base.Index, pd.DataFrame, 
        pd.Series, np.ndarray
    
    When a Sequence, the index will be verified against len(data).
    
    When one of the pandas data types:
        DataFrame, Series: the index will be checked against the object's 
        'index' attribute
        
        pandas.core.indexes.base.Index: the index will be cheched against it
        (useful when passing the columns attribute of a DataFrame)
    
    For numpy arrays, return a flat index to be used with array.ravel()
        
    When an int, 'data' is the length of a virtual Sequence (hence data >= 0 is
    expected).
    
index: GeneralIndexType: a typing alias for:

    int → selects only the element with the specified int index

    str → selects only the element having a 'name' or 'label' attribute with the 
        value; for numpy arrays, returns the index of elements equal to the index

    range → selects the elements with int indices in the specified range

    slice → selects the elements within the slice range

    collections.abc.Sequence[int] → selects the elements with the specified 
            int indices

    collections.abc.Sequence[str] → selects the elements having a 'name'
            attribute with value in this parameter

    1D np.ndarray with integer dtype (i.e., np.dtype(int)) →  behaved like a flat
        array index (see online Numpy documentation)
        
        WARNING: This is simply converted to a tuple and returned (no checks 
        against values)
    
        ATTENTION: For array data, 1D int arrays should be used directly as flat
        indices into ravelled arrays (see Numpy documentation)
    
    1D np.ndarray with logical dtype  (i.e., np.dtype(bool)) → Used as a 
        'mask': returns the indices of the True values as a tuple of int
    
        ATTENTION: For array data, 1D logical arrays should be used directly as 
        flat indices into ravelled arrays (see Numpy documentation)

    MISSING ⇒ select NO elements from the data (returns an empty range)

    None (default) ⇒ select ALL elements in the data

    When 'index' is None, the function returns range(0, len(data)) when 
        'data' is a Sequence, else range(, data) when 'data' is an int.

    When index is MISSING, the function returns an empty range:
        range(0)
        
    CAUTION: negative integral indices are valid and perform the reverse 
        indexing (going "backwards" in the iterable).
    
    axis: int (optional, default is None)
        Used only for numpy array data; specifies the axis along which the 
        "normalized" index is to be returned.
        
Returns:
--------
ret - an iterable object (range, or tuple of integer indices) that can be 
    used in list comprehensions using 'data' (when 'data' is a Sequence) or
    any sequence with same length as 'data' (when 'data' is an int).
        
    """
    from core.datatypes import is_vector
    
    if data is None:
        return tuple()
    
    elif isinstance(data, int):
        assert(data >= 0)
        data_len = data
        data = None
        
    elif isinstance(data, collections.abc.Sequence):
        data_len = len(data)
        
    elif isinstance(data, (pd.Series, pd.DataFrame)):
        data_len = len(data)
        data = data.index
        
    elif isinstance(data, (pd.core.indexes.base.Index, neo.Epoch, DataZone)):
        data_len = len(data)
        
    elif isinstance(data, np.ndarray):
        if isinstance(axis, int):
            if axis not in range(-data.ndim, data.ndim):
                raise ValueError(f"Invalid axis index {axis} for an array with {data.ndim} dimensions")
            data_len = data.shape[axis]
        else:
            data_len = data.size
        
    else:
        raise TypeError("Expecting an int or a sequence (tuple, list, deque) or None; got %s instead" % type(data).__name__)
    
    # 1) index is None ⇒ return the entire range of data
    if index is None:
        return range(data_len)
    
    # 2) index is MISSING ⇒ return an empty range
    if isinstance(index, type(MISSING)):
        return range(0)
    
    # 3) index is an int ⇒ 
    if isinstance(index, int):
        # NOTE: 2020-03-12 22:40:31
        # negative values ARE supported: they simply go backwards from the end of
        # the sequence
        if index not in range(-data_len, data_len):
            if silent:
                return None
            raise ValueError(f"Index {index} is invalid for {len(data)} elements")
        
        if isinstance(data, pd.core.indexes.base.Index):
            return (data[index], )
        
        return (index,)
    
    # 4) index is a str ⇒
    #   Check that elements in data are either str, or have an attribute with 
    #   name given in index.
    #   Requires that 'data' is an actual collection, not the length of a virtual
    #   collection.
    if isinstance(index, (str, np.str_, bytes)):
        if isinstance(index, bytes):
            index = index.decode()
            
        if isinstance(data, (tuple, list)):
            if all(isinstance(data, (str, np.str_, bytes))):
                ret = tuple(filter(lambda x: x.decode() == index if isinstance(x, bytes) else x == index,
                                   data))
                if len(ret) == 0:
                    if silent:
                        return None
                    raise ValueError(f"Index {index} not found in data")
                return ret
            else:
                ret = tuple(prog.filter_attr(data, operator.or_, indices_only=True, 
                                             name=lambda x: x==index, label=lambda x: x==index))
                if len(ret) == 0:
                    if silent:
                        return None
                    raise AttributeError(f"The objects have no attribute named 'name' or 'label' with the value {index}")
                
                return ret
            
        if isinstance(data, (pd.core.indexes.base.Index)):
            if index in data:
                return (index,)
                #return (list(data).index(index), )
            
            if not silent:
                raise IndexError(f"Invalid 'index' specification {index}")
            
        if isinstance(data, np.ndarray):
            if index in data:
                ret = np.flatnonzero(data == index)
            else:
                if silent:
                    return None
                
                else:
                    raise ValueError(f"Index {index} not found in data array")
                
        raise TypeError("Name index requires 'data' to be a sequence of objects, or a pandas Index, Series, or DataFrame, or a numpy array")
        
    # 5) index is an Iterable of objects of the same type!
    elif isinstance(index, collections.abc.Iterable):
        # 5.1) of int values
        if all(isinstance(v, int) and v in range(-data_len, data_len) for v in index):
            if isinstance(data, pd.core.indexes.base.Index):
                return (data[v] for v in index )
            
            return index
        
        # 5.2) of str values
        elif all(isinstance(v, (str, np.str_, bytes) ) for v in index):
            if not isinstance(data, collections.abc.Iterable):
                raise TypeError("When indexing by name attribute (str), data must be an iterable")
            
            if isinstance(data, collections.abc.Sequence):
                return tuple(prog.filter_attr(data, name=lambda x: x in index, indices_only=True))
            
            if isinstance(data, pd.core.indexes.base.Index):
                return tuple(v for v in index if v in data)
        
                if not silent:
                    raise IndexError(f"Invalid 'index' specification {index}")
                
        # 5.3) of anything else ⇒ Error
        else:
            if silent:
                return None
            
            raise IndexError(f"Invalid 'index' specification {index}")
        
    # 6) index is a range
    elif isinstance(index, range):
        if max(index) >= data_len:
            if silent:
                return None
            raise IndexError(f"Index {index} out of range for {data_len} elements")
        
        return index # -> index IS a range
    
    # 7) index is a slice
    elif isinstance(index, slice):
        ndx = index.indices(data_len)
            
        if len(ndx) == 0:
            if silent:
                return None
            raise IndexError(f"Indexing {index} results in an empty indexing list")
        
        if max(ndx) >= data_len:
            if silent:
                return None
            raise IndexError(f"Index {index} out of range for {data_len} elements")
        
        if min(ndx) < -data_len:
            if silent:
                return None
            raise IndexError(f"Index {index} out of range for {data_len} elements")
        
        return ndx # -> ndx IS a tuple
    
    # 8) index is a 1D numpy array
    elif isinstance(index, np.ndarray):
        if not is_vector(index):
            raise TypeError(f"Indexing array must be a vector; instead its shape is %s" % index.shape)
            
        # 8.1) of integer dtype
        if index.dtype.kind == "i": # index is an array of int
            if np.any((index < 0) | (index >= data_len) ):
                if silent:
                    return None
                raise ValueError(f"Indexing array out of bounds")
            
            return tuple(index)
        
        # 8.2) of boolean dtype
        elif index.dtype.kind == "b": # index is an array of bool
            if len(index) != data_len:
                raise TypeError("Boolean indexing vector must have the same length as the iterable against it will be normalized (%d); got %d instead" % (data_len, len(index)))
            
            return tuple(np.arange(data_len)[index])
            #return tuple([k for k in range(data_len) if index[k]])
            
        # 8.3) of any other dtype ⇒ Error
        else:
            if silent:
                return
            raise TypeError(f"Invalid dtype {index.dtype} for indexing array")
            
    # 9) index is of any other type ⇒ Error
    else:
        if silent:
            return
        raise TypeError("Unsupported data type for index: %s" % type(index).__name__)
    
# @normalized_index.register(type(None))
# def _(data, )
    
def normalized_sample_index(data:np.ndarray, axis: typing.Union[int, str, vigra.AxisInfo], index: typing.Optional[typing.Union[int, tuple, list, np.ndarray, range, slice]]=None):
    """Calls normalized_index on a specific array axis.
    Also checks index validity along a numpy array axis.
    
    Parameters:
    ----------
    data: numpy.ndarray or a derivative (e.g. neo.AnalogSignal, vigra.VigraArray)
    
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

def normalized_axis_index(data:np.ndarray, axis:(int, str, vigra.AxisInfo)):
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

def sp_set_loc(x, index, columns, val):
    """Assign values to pandas.SparseArray
    Work around .loc idiom when fill value is pd.NA
    
    Parameters:
    -----------
    x : DataFrame with series formatted with Pandas SparseDtype
        Series formatted with Pandas SparseDtype
    
    index: str, or list, or slice object
        Same as one would use as first argument of .loc[]
        
    columns: str, list, or slice
        Same one would normally use as second argument of .loc[]
        Ignored when x is a Pandas Series (just pass None to ensure the parameter 
        is set)
        
    val: insert values

    Returns
    -------
    x: Modified DataFrame or Series

    NOTE:
    -------
    Modified from Answer 1 at
    https://stackoverflow.com/questions/49032856/assign-values-to-sparsearray-in-pandas
    
    'Insert data in a DataFrame with SparseDtype format'

    Only applicable for pandas version > 0.25
    
    """
    if isinstance(x, pd.Series):
        spdtypes = x.dtype
        #if np.any(x.isna):
        if np.any(x.isna()):
            x = np.asarray(x, dtype=np.dtype(object), order="k")
        else:
            x.sparse.to_dense()
        # NOTE: 2021-12-05 22:09:29 ignore columns for a pd.Series
        
        x.loc[index] = val
        x = x.astype(spdtyes)
        return x
    
    # NOTE: 2021-12-05 22:02:06
    # handle the case where columns is a slice, a list, or a pandas Index
    # Save the original sparse format for reuse later
    # trimmed-down version of full code for data frames, further below 
    spdtypes = x.dtypes[columns]

    if isinstance(columns, slice):
        columns = x.columns[columns] # => pd.Index !
    
    if isinstance(columns, (list, pd.Index)): # tuples (not lists) are used for multi-index
        for c in columns:
            #if np.any(x[c].isna):
            if np.any(x[c].isna()):
                # NOTE: see NOTE: 2021-12-04 20:06:50
                x[c] = np.asarray(x[c], dtype = np.dtype(object), order = "K")
            else:
                # NOTE: 2021-12-04 20:06:50
                # this fails when the sparse array has pd.NA as fill_value
                x[c] = x[c].sparse.to_dense() # original code

    else: 
        # Convert concerned Series to dense format
        #if np.any(x[columns].isna):
        if np.any(x[columns].isna()):
            # NOTE: see NOTE: 2021-12-04 20:06:50
            x[columns] = np.asarray(x[columns], dtype = np.dtype(object), order = "K")
        else:
            # NOTE: 2021-12-04 20:06:50
            # this fails when the sparse array has pd.NA as fill_value
            x[columns] = x[columns].sparse.to_dense() # original code

    # Do a normal insertion with .loc[]
    x.loc[index, columns] = val

    # Back to the original sparse format
    if isinstance(columns, (slice, list, pd.Index)): # tuples (not lists) are used for multi-index
        for c in columns:
            x[c] = x[c].astype(spdtypes[c])
    else:
        x[columns] = x[columns].astype(spdtypes)
    
    return x    

def get_least_pwr10(x:typing.Sequence)-> int:
    if not all(isinstance(v, Number) or (isinstance(v, pq.Quantity) and v.size == 1) for v in x):
        raise TypeError("Expecting a sequence of scalars or scalar Quantity objects")
    
    if any (math.isinf(v) for v in x):
        x = [v for v in x if not math.isinf(v)]
    
    fr = [abs(math.fmod(v, 10)) for v in x]
    return min(int(math.log10(v)) if v > 0 else 0 for v in fr)

def sp_get_loc(x, index, columns):
    """Retrieve values to pandas.SparseArray
    Work around .loc idiom when fill value is pd.NA
    
    See also sp_set_loc

    Only applicable for pandas version > 0.25

    Parameters:
    -----------
    x : DataFrame with series formatted with pd.SparseDtype, OR
        Series formatted with pd.SparseDtype
    
    index: str, or list, or slice object
        Same as one would use as first argument of .loc[]
        
    columns: str, list, or slice
        Same one would normally use as second argument of .loc[]
        Ignored when 'x' is a Pandas Series  (just pass None to ensure the 
        parameter is set)
        
    Returns
    -------
    x: DataFrame, Series, or scalar
        
    """
    # trimmed-down version of full code for data frames, further below 
    if isinstance(x, pd.Series):
        spdtypes = x.dtype
        #if np.any(x.isna):
        if np.any(x.isna()):
            x = np.asarray(x, dtype=np.dtype(object), order="k")
        else:
            x.sparse.to_dense()
        # NOTE: 2021-12-05 22:09:29 ignore columns for a pd.Series
        
        ret = x.loc[index]
        x = x.astype(spdtyes)
        if isinstance(ret, pd.Series):
            ret = ret.astype(spdtypes)
        return ret
    
    # Save the original sparse format for reuse later
    
    # NOTE:  datatypes.dtypes returns a Series!!! 
    # NOTE: it is 'dtypes' not 'dtype'!
    spdtypes = x.dtypes[columns] # this is a pd.Series with column names as row index
    
    if isinstance(columns, slice):
        columns = x.columns[columns] # => pd.Index
        #columns = [c for c in x.columns[columns]]
    
    if isinstance(columns, (list, pd.Index)): # tuples (not lists) are used for multi-index
        for c in columns:
            #if np.any(x[c].isna):
            if np.any(x[c].isna()):
                # NOTE: see NOTE: 2021-12-04 20:06:50
                x[c] = np.asarray(x[c], dtype = np.dtype(object), order = "K")
            else:
                # NOTE: 2021-12-04 20:06:50
                # this fails when the sparse array has pd.NA as fill_value
                x[c] = x[c].sparse.to_dense() # original code

    else: 
        # NOTE: should also cover tuples of columns (multiindex) but haven't checked yet        
        # Convert concerned Series to dense format
        #if np.any(x[columns].isna):
        if np.any(x[columns].isna()):
            # NOTE: see NOTE: 2021-12-04 20:06:50
            x[columns] = np.asarray(x[columns], dtype = np.dtype(object), order = "K")
        else:
            # NOTE: 2021-12-04 20:06:50
            # this fails when the sparse array has pd.NA as fill_value
            x[columns] = x[columns].sparse.to_dense() # original code

    # Access using .loc[]
    ret = x.loc[index, columns]

    # Back to the original sparse format
    if isinstance(columns, (slice, list, pd.Index)): # tuples (not lists) are used for multi-index
        for c in columns:
            x[c] = x[c].astype(spdtypes[c])
    else:
        x[columns] = x[columns].astype(spdtypes)
    
    # also apply original sparse dtype to the result
    if isinstance(ret, pd.Series):
        if isinstance(spdtypes, pd.Series):
            ret = ret.astype(spdtypes[ret.name])
            
        ret = ret.astype(spdtypes)
        
    elif isinstance(ret, pd.DataFrame):
        for c in ret.columns:
            ret[c] = ret[c].astype(spdtypes[c])
    
    return ret

def truncate_to_10_power(x):
    if isinstance(x, np.ndarray):
        u = None
        if isinstance(x, pq.Quantity):
            u = x.units
            x = x.magnitude
        
        pw10 = 10**np.trunc(np.log10(np.abs(x)))
        
        ret = np.trunc(x/pw10) * pw10
        
        if isinstance(u,pq.Quantity):
            return ret * u
        
        return ret
    
    elif isinstance(x, (float, int)):
        pw10 = 10**math.trunc(math.log(math.abs(x),10))
        return math.trunc(x/pw10) * pw10
        
            
            
