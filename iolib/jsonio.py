""" JSON codecs

    General schema:
    
    Below, <key> is one of: 
    "python_type", "python_function_or_method", "python_method", 
    "python_object"
    
    {<key>:{
        "instance_type": str; the name of the object's type, when object is
                                an instance 
        
        "instance_module": str; the name of the module where the object's 
                            type is defined (when object is an instance)
        
        "type_name": str; for type objects, the name of the object 
                                (obj.'__name__');
                                
                              for instances, same value as instance_type
                              
        "type_module": str; for type objects, the name of the module where 
                                the object (a type) is defined;
                                
                                for instances, same value as instance_module
                                
        "type_factory": dict or None; 
            
            When a dict, it will be used when the type of the instance being
            serialized (or the type being serialized) cannot be imported (e.g. 
            in case of dynamically created classes such as named tuples).
            
            The type_factory dict expects the following structure:
            {
                "name": str: name for the type factory function.
                            This is the name of a callable to generate the 
                            object's type (for python instances) or the type
                            being serialized.

                            The parameters passed to this function are given in 
                            "posonly", "named", "varpos",
                            "kwonly", and "varkw", explained below.
                            
                "__qualname__": str: qualified name of the function (e.g
                    <object_type>.<name>)
                    
                "__module__": str: module where the function is defined
                            
                "posonly": tuple: values of the positional only parameters,
                    and of the "named" parameters without default value
                    
                "named": dict, mapping name to value for positional or 
                            keyword parameters, that have a default value
                            
                "varpos": tuple: values for the var-positional parameters
                            
                "kwonly": dict, mapping name to value for keyword only 
                            parameters
                            
                "varkw": dict, mapping name to value for any additional
                            keyword (var-keyword) parameters
                            
                "signature": None, or dict (result of prog.signature2Dict)
            }
            
            The type factory will use the parameters in __args__, named and 
            __kwargs__ (see below)
            
        "factory": dict or None
                    Object factory (either __init__ or __new__ or a factory
                    function, represented as a dict (similar to _type_factory__
                    as above), or None,
                    
                    When None, the object type will be used as callable with 
                    no arguments.
                
        "subtype": str or None
                When a str it is used specifically for numpy structured arrays
                and for Pandas extension dtypes
        
        "dtype": str; representation of the numpy dtye, or json representation
                    of a specialized dtype (such as h5py special dtypes, or 
                    pandas extension dtypes)
                        
        "value": str: JSON representation of the value, or None (a.k.a null)
                    this is usually the JSON representation for objects of
                    basic Python types that can be directly serialized (either
                    using Python's json or any other 3rd party library, e.g. 
                    orjson)
                            
        }
    }
    
NOTE: 2021-12-21 16:11:42
Testing the following alternative json libs/packages:
simplejson => NO
    + deals with named tuples BUT 
    - outputs as if a dict and
    - hardcoded in C
    
orjson 
    + hardcoded in C, claims to be the fastest (in any case faster than json, simplejson)
    + promising for datetime & numpy arrays
    + seems more flexible 
    + no JSONEncoder to inherit from; must supply a default callable, quite flexible.
        ~ claims not to serialize namedtuple but the 'default' mechanism works;
            however, I find that it is better to use my schema (despite the 
            overhead, it is flexible enough)
        + the 'default' can be a generic function (via single dispatch) - this
            can also be used with Python's own json module
            - CAUTION: errors in the default function are not propagated; instead
            the encoding fails with JSONEncodeError...
    ~ returns bytes instead of str - not a problem if str is required call
        bytes.decode("utf-8")
        - only works with utf-8, but that's OK (I guess...)
        
    ~ only has dumps/loads => for file IO use context manager e.g., 
        with open(...) as jsonfile:
            s = orjson.dumps(...)
            jsonfile.write(s)
            
    ~ loads takes only one argument i.e., the object to deserialize, and does 
        not accept any "optional" stuff like object-hook, etc:
        loads(__obj: Union[bytes, bytearray, memoryview, str]) -> Any: ...
        
        loads returns the basic types: dict, list, int, float, str, bool and None
        
        This allows for maximal flexibility (no more decode hook  malarkey) by 
        passing the result to whataver suits your fancy to recreate the original
        data. Hence on the encoding side, I can provide a 'default' to generate 
        slightly more complex JSON 'obejcts' (a.k.a. dict) adorned with class 
        and type hints
        
    + support for dataclass (new since Python 3.7) => we might consider using 
        this strategy in ScanData, AnalysisUnit, Results, etc.

    - unlike Python's own json module, it does not support +/- Infinity and NaN!

NOTE: 2022-01-01 23:35:28
Decided to stick with Python's own JSON as this provides (non-standard JSON) 
    support for +/- Infinity and NaNs.
    Disadvantages:
    - may be slow especially for large data sets
    - introduces potentially very large overheads (due to type and constructor
    hints) => the output (str) is not easily human-readable
    Advantage (MAJOR): flexible enough to store the data in text files, and pass
    it between the main Scipyen workspace and external kernels and back (these
    all require access to the Sciopyen's modules and 3rd party dependencies)
    
"""

import sys, traceback, typing, collections, inspect, types, dataclasses, math
import datetime, zoneinfo
from inspect import _empty
from dataclasses import MISSING
import json
#import simplejson as json
#import orjson
from collections import deque, namedtuple
import collections.abc
from functools import (singledispatch, singledispatchmethod, 
                       update_wrapper, wraps,)
import numpy as np
import numpy.ma as ma
import quantities as pq
import pandas as pd
import h5py
import vigra
from traitlets.utils.importstring import import_item
from traitlets import Bunch
from core import quantities as scq
from core import prog
from core.prog import (signature2Dict, resolveObject, ArgumentError, CALLABLE_TYPES)

# NOTE: 2021-12-25 15:45:55
# unfortunately, orjson does not expose supported numpy types so we need to
# hardcode these here

JSON_NUMPY_TYPES = (np.float64, np.float32, np.int64, np.int32, np.int8, 
                      np.uint64, np.uint32, np.uint8, np.uintp, np.intp, 
                      np.datetime64)

JSON_NUMPY_DTYPES = tuple(np.dtype(t) for t in JSON_NUMPY_TYPES)

# NOTE:2021-12-25 16:55:20
# potential instance methods for convertion to JSON; by no means exhaustive
# but at least covers 3rd party cases (e.g., vigra.AxisTags.toJSON, 
# vigra.AxisTags.fromJSON, pandas.DataFrame.to_json) and Scipyen's types
TO_JSON_INSTANCE_METHODS = ("tojson", "toJSON", "to_json", "to_JSON", 
                            "obj2json", "obj2JSON")

# NOTE: 2021-12-25 17:01:49
# WARNING pandas.read_json is NOT a complete round trip for multiindex! 
# As for TO_JSON_INSTANCE_METHODS this is by no means exhaustive, as it depends 
# on 3rd party developers
FROM_JSON_FACTORY_METHODS = ("fromjson", "fromJSON", "from_json", "from_JSON", 
                             "objfromjson", "objfromJSON",
                              "json2obj", "JSON2obj", "json2Obj", "JSON2OBJ",
                             "read_json", "read_JSON", "readJSON", "readjson")

def makeFuncStub(function:typing.Optional[typing.Union[CALLABLE_TYPES + (str, )]]=None):
    """Generate a stub dictionary.
    
    The result contains the following key/value pairs (see also general schema
    described in the module docstring):
    
    "signature": dict, result of prog.signature2Dict
    
    "posonly": tuple: values of the positional only parameters,
        and of the "named" parameters without default value
        
    "named": dict, mapping name to value for positional or 
                keyword parameters, thart have a default value
    "varpos": tuple: values for the var-positional parameters
                
    "kwonly": dict, mapping name to value for keyword only 
                parameters
                
    "varkw": dict, mapping name to value for any additional
                keyword (var-keyword) parameters
                
    
    
    In the stub, only the 'signature' is initialized; the other keys are set
    to their empty defaults (tuple() or dict()) which must be apporpriately
    populated by one of the module functions makeJSONStub and object2JSON.
    
    
    
    """
    stub = {"signature":    None,
            "posonly":      tuple(),
            "named":        dict(),
            "varpos":       tuple(),
            "kwonly":       dict(),
            "varkw":        dict(),
            }
    
    if function is None:
        return stub
    
    elif isinstance(function, str):
        stub["signature"] = function
        return stub
    
    elif not isinstance(function, CALLABLE_TYPES):
        raise TypeError(f"Expecting a callable type, one of {CALLABLE_TYPES}; got {type(function).__name__} instead")
    
    try:
        sig = signature2Dict(function)
    except:
        sig = {"name": function.__name__, "qualname": function.__qualname__, "module": function.__module__}
        
    stub["signature"] = sig
    return stub

def makeJSONStub(o):
    if isinstance(o, type):
        header = "python_type"
        ret = {"type_name":     o.__qualname__,
               "type_module":   o.__module__,
               "type_factory":  None,
               }
        
    elif isinstance(o, CALLABLE_TYPES):
        header = "python_function_or_method"
        ret = makeFuncStub(o)
                                            
    else:
        header = "python_object"
        ret = {"instance_type":     type(o).__qualname__,
               "instance_module":   type(o).__module__,
               "type_factory":      None,
               "factory":           None,
               "value":             None,
               "subtype":           None,
               "dtype":             None,
               }
                
    return header, ret


def makeH5PyOpaqueDtype(name):
    """Required because inspect.signature fails with h5py dtype factories
    """
    return h5py.opaque_dtype(np.dtype(name))

def makeH5PyEnumDtype(name):
    """Required because inspect.signature fails with h5py dtype factories
    """
    return h5py.enum_dtype(name)
    
def makeH5PyStringDtype(encoding, length):
    """Required because inspect.signature fails with h5py dtype factories
    """
    return h5py.string_dtype(encoding, length)

def makeH5PyVlenDtype(name):
    """Required because inspect.signature fails with h5py dtype factories
    """
    return h5py.vlen_dtype(name)

@singledispatch
def object2JSON(o):
    from core.datatypes import is_namedtuple
    #print("object2JSON<>", type(o))
    hdr, ret = makeJSONStub(o)
    if is_namedtuple(o):
        type_factory = makeFuncStub(collections.namedtuple)
        type_factory["named"] = {"typename": type(o).__name__,
                                     "field_names": tuple(f for f in o._fields)}
        ret["type_factory"] = type_factory

        factory = makeFuncStub(type(o).__new__)
        factory["named"] = dict((f, getattr(o,f)) for f in o._fields)
        ret["factory"] = factory
        
    else:
        to_json_ndx = list(k for k,m in enumerate(TO_JSON_INSTANCE_METHODS) if isinstance(getattr(o, m, None), CALLABLE_TYPES))
        if len(to_json_ndx):
            to_json = getattr(o, TO_JSON_INSTANCE_METHODS[to_json_ndx[0]])
            ret["value"] = to_json() # this SHOULD work for bound methods!
        
        else:
            raise NotImplementedError(f"{type(o).__name__} objects are not yet supported")

    return {hdr:ret}

@object2JSON.register(type(None))
def _(o:type(None)):
    return {"python_object":"None"} 

@object2JSON.register(type(dataclasses.MISSING))
def _(o:type(dataclasses.MISSING)):
    hdr,ret = makeJSONStub(o)
    factory = makeFuncStub(".".join([type(o).__module__, type(o).__name__]))
    ret["factory"] = factory
    return {hdr:ret}


@object2JSON.register(Bunch)
def _(o:Bunch):
    return dict(o)
    
@object2JSON.register(type)
def _(o:type):
    from core.datatypes import is_namedtuple
    hdr, ret = makeJSONStub(o)
    if is_namedtuple(o):
        type_factory = makeFuncStub(collections.namedtuple)
        type_factory["named"] = {"typename": type(o).__name__,
                                     "field_names": tuple(f for f in o._fields)}
        
        ret["type_factory"] = type_factory
        
    return {hdr:ret}

@object2JSON.register(np.generic)
def _(o:np.generic):
    # NOTE: 2021-12-27 22:15:52
    # numpy scalar types
    # FIXME/TODO 2021-12-27 23:06:03 can I do round-trip for np.void?
    hdr, ret = makeJSONStub(o)
    ret["value"] = str(o)
    return {hdr:ret}

@object2JSON.register(complex)
def _(o:complex):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(type(o).__new__)
    factory["posonly"] = (o.real, o.imag)
    ret["factory"] = factory
    
    return {hdr:ret}
    
@object2JSON.register(deque)
def _(o:deque):
    #print(type(o))
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(type(o).__new__)
    factory["posonly"] = (list(o),)
    factory["named"] = {"maxlen": o.maxlen}
    ret["factory"] = factory
    return {hdr:ret}
    
@object2JSON.register(vigra.filters.Kernel1D)
@object2JSON.register(vigra.filters.Kernel2D)
def _(o:typing.Union[vigra.filters.Kernel1D, vigra.filters.Kernel2D]):
    #print(type(o))
    from imaging.vigrautils import kernel2array
    hdr, ret = makeJSONStub(o)
    xy = kernel2array(o, True)
    # FIXME/TODO 2021-12-27 23:42:56
    # disentangle 'kernelFromJSON' from vigrautils so that jsonio can stand alone
    factory = makeFuncStub(kernelFromJSON)
    #factory["posonly"] = (xy.tolist(),) 
    # NOtE: 2021-12-25 14:46:16
    # this requires passing option=orjson.OPT_SERIALIZE_NUMPY to orjson.dumps
    factory["posonly"] = (xy,) 
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(vigra.AxisTags)
def _(o:vigra.AxisTags):
    #print(f"object2JSON<vigra.AxisTags>: {type(o)}: {o}")
    hdr, ret = makeJSONStub(o)
    value = o.toJSON()
    factory = makeFuncStub(type(o).fromJSON)
    factory["posonly"] = (value, )
    ret["factory"] = factory
    
    return {hdr:ret}

@object2JSON.register(np.ndarray)
def _(o:np.ndarray):
    #print("object2JSON", type(o))
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(np.array)
    factory["posonly"] = (o.tolist(), )
    factory["named"] = {"dtype": o.dtype}
    
    if o.dtype.fields is not None:
        # structarray or recarray
        ret["subtype"] = "recarray" if o.dtype.name.startswith("record") else "structarray"
        
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(ma.MaskedArray)
def _(o:ma.MaskedArray):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(ma.array)
    mask = False if o.mask is ma.nomask else o.mask.tolist()
    data = o.data.tolist()
    dtype = o.dtype
    fill_value = o.fill_value
    factory["posonly"] = (o.data.tolist(),)
    factory["named"] = {"mask": mask,
                            "dtype": o.dtype,
                            "copy": True,
                            }
    if not isinstance(fill_value, np.void):
        # NOTE: 2021-12-27 23:05:32
        # no conversion for np.void (yet !?)
        factory["named"]["fill_value"] = fill_value
    
    if o.dtype.fields is not None:
        # structarray or recarray
        ret["subtype"] = "recarray" if dtype.name.startswith("record") else "structarray"
        
    ret["factory"] = factory
    
    return {hdr:ret}

@object2JSON.register(vigra.VigraArray)
def _(o:vigra.VigraArray):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(vigra.VigraArray.__new__)
    if o.dtype in JSON_NUMPY_DTYPES or type(o.flatten()[0]) in JSON_NUMPY_TYPES:
        factory["named"]["obj"] = o.view(np.ndarray)
    else:
        factory["named"]["obj"] = o.tolist()
        
    #factory["named"]["dtype"] = o.dtype # avoid this; it will be taken from the numpy array data
    factory["named"]["order"] = o.order
    factory["named"]["axistags"] = o.axistags
    
    ret["factory"] = factory
    
    return {hdr:ret}

@object2JSON.register(datetime.timedelta)
def _(o:datetime.timedelta):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("datetime.timedelta")
    factory["named"] = {"days":o.days,
                            "seconds":o.seconds,
                            "microsecond":o.microsecond}
    
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(datetime.time)
def _(o:datetime.time):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("datetime.time")
    factory["named"] = {"hour":o.hour,
                            "minute":o.minute,
                            "second":o.second,
                            "microsecond":o.microsecond,
                            "tzinfo":o.tzinfo}
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(datetime.tzinfo)
def _(o:datetime.tzinfo):
    hdr,ret = makeJSONStub(o)
    factory = makeFuncStub(".".join((type(o).__module__, type(o).__name__)))
    factory["named"] = {"offset":o.utcoffset(None),
                            "name":o.tzname(None)}
    ret["factory"] = factory
    return {hdr:ret}
    

@object2JSON.register(datetime.timezone)
def _(o:datetime.timezone):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("datetime.timezone")
    factory["named"] = {"offset":o.utcoffset(None),
                            "name":o.tzname(None)}
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(datetime.date)
def _(o:datetime.date):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("datetime.date")
    factory["named"] = {"year":o.year,
                            "month":o.month,
                            "day":o.day}
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(datetime.datetime)
def _(o:datetime.datetime):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("datetime.datetime")
    factory["named"] = {"year":o.year,
                            "month":o.month,
                            "day":o.day,
                            "hour":o.hour,
                            "minute":o.minute,
                            "second":o.second,
                            "microsecond":o.microsecond,
                            "tzinfo":o.tzinfo}
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(zoneinfo.ZoneInfo)
def _(o:zoneinfo.ZoneInfo):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("zoneinfo.ZoneInfo")
    factory["posonly"] = (o.key,)
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(pd.Interval)
def _(o:pd.Interval):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("pd.Interval")
    factory["named"] = {"left": o.left, "right": o.right, "closed":o.closed}
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(pd.core.arrays.interval.IntervalArray)
def _(o:pd.core.arrays.interval.IntervalArray):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(type(o).__new__)
    factory["named"] = {"data":o.to_numpy(),
                            "dtype": o.dtype,
                            "closed": o.closed}
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(pd.DataFrame)
def _(o:pd.DataFrame):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("pd.DataFrame")
    #factory["posonly"] = (list(o.loc[i,:].to_numpy().tolist() for i in o.index), )
    factory["posonly"] = (list(o.iloc[i,:].to_numpy().tolist() for i in range(len(o))), )
    factory["named"] = {"index": o.index,
                            "columns": o.columns} 
    ret["factory"] = factory
    return {hdr:ret}
    
@object2JSON.register(pd.Series)
def _(o:pd.Series):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("pd.Series")
    #print(o.name)
    factory["posonly"] = (o.to_numpy().tolist(),)
    factory["named"] = {"index": o.index,
                            "dtype": o.dtype,
                            "name": str(o.name)}
    
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(type(pd.NA))
def _(o:type(pd.NA)):
    hdr, ret = makeJSONStub(o)
    ret["value"] = tuple()
    return {hdr:ret}
    #return "NA"
    
@object2JSON.register(pd.Timestamp)
def _(o:pd.Timestamp):
    hdr, ret = makeJSONStub(o)
    ret["value"] = str(o)
    return {hdr:ret}

@object2JSON.register(pd.Index)
def _(o:pd.Index):
    # NOTE: 2021-12-31 10:28:42
    # this should work for Pandas numerical indices except RangeIndex:
    # Int64Index, UInt64Index, Float64Index
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(pd.Index.__new__)
    # NOTE: 2021-12-31 09:40:52
    # dtype inferred from the array (hopefully)
    factory["posonly"] = (o.to_numpy().tolist(),)
    factory["named"] = {"name": o.name}
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(pd.RangeIndex)
def _(o:pd.RangeIndex):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(pd.RangeIndex.__new__)
    factory["named"] = {"start": o.start,
                            "stop": o.stop,
                            "step": o.step,
                            "name": o.name}
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(pd.CategoricalIndex)
def _(o:pd.CategoricalIndex):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(pd.CategoricalIndex.__new__)
    factory["posonly"] = (o.to_numpy().tolist(), )
    #factory["posonly"] = (o.to_numpy().tolist(), )
    factory["named"] = {"categories": o.categories.to_numpy().tolist(),
                            "name": o.name}
    # NOTE: 2022-01-01 13:19:44
    # Cannot specify `categories` or `ordered` together with `dtype`.
                            #"dtype":o.dtype}
    factory["dtype"] = o.dtype
    ret["factory"] = factory
    return {hdr:ret}
    
@object2JSON.register(pd.IntervalIndex)
def _(o:pd.IntervalIndex):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(pd.IntervalIndex.__new__)
    factory["named"] = {"data": o.values,
                            "closed": o.closed,
                            "dtype": o.dtype}
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(pd.MultiIndex)
def _(o:pd.Index):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub(pd.MultiIndex.__new__)
    factory["named"] = {"levels": o.levels,
                            "codes": o.codes,
                            "names": o.names}
    ret["factory"] = factory
    return {hdr:ret}
    
@object2JSON.register(np.dtype)
def _(o:np.dtype):
    return dtype2JSON(o)

@object2JSON.register(pd.CategoricalDtype)
def _(o:pd.CategoricalDtype):
    # NOTE: 2021-12-31 23:06:32
    # CategoricalDtype is NOT a subclass of numpy.dtype
    return pandasDtype2JSON(o)

@object2JSON.register(pq.UnitQuantity)
def _(o: pq.UnitQuantity):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub("core.quantities.unit_quantity_from_name_or_symbol")
    factory["posonly"] = (o.dimensionality.string, )
    ret["factory"] = factory
    return {hdr:ret}

@object2JSON.register(pq.Quantity)
def _(o:pq.Quantity):
    hdr, ret = makeJSONStub(o)
    factory = makeFuncStub()
    factory["signature"] = None
    factory["posonly"] = (o.magnitude.tolist(), )
    # NOTE: 2021-12-27 23:45:51
    # o.units are Quantity, not UnitQuantity hence the following avoids infinite
    # recursion
    factory["named"]["units"] = o.units.dimensionality.string
    factory["named"]["dtype"] = o.dtype
    
    ret["factory"] = factory
    
    return {hdr:ret}
    
def dtype2JSON(d):
    """Delegates to json converter for h5py, pandas or numpy (in this order)
    Also required as intermediate for recurdive call in numpyDtype2JSON.
    """
    jsonrep = h5pyDtype2JSON(d) or pandasDtype2JSON(d) or numpyDtype2JSON(d)
    return jsonrep

def numpyDtype2JSON(d:np.dtype) -> dict:
    """Roundtrip numpy dtype - json string format - write side
    An alternative to the np.lib.format.dtype_to_descr
    Returns a dict for recarray dtypes; a str in any other case.
    """
    if not isinstance(d, np.dtype):
        raise TypeError(f"Expecting a numpy dtype; got {type(d).__name__} instead")
    
    hdr, ret = makeJSONStub(d)
    ret["instance_type"] = "dtype"
    
    factory = makeFuncStub(np.dtype.__new__)
    
    fields = d.fields
    
    # NOTE: 2021-12-27 11:34:24
    # below, this also takes care of field titles for dtypes of structured arrays/recarrays
    if d.name.startswith("record"):
        value = dict((name, (dtype2JSON(value[0]), *value[1:])) for name, value in d.fields.items())
        ret["subtype"] = "recarray"
        
    else:   
        if fields is None:
            #print("dtype:", d)
            value = np.lib.format.dtype_to_descr(d) # does not perform well for structured arrays?
        else:
            value = dict((name, (dtype2JSON(value[0]), *value[1:])) for name, value in d.fields.items())
            
    factory["signature"] = "numpy.dtype"
    
    factory["posonly"] = (value,)
    
    ret["factory"] = factory
    
    return {hdr:ret}

def h5pyDtype2JSON(d):
    """Checks if d is a special h5py dtype.
    Returns a json representation (dict) if d is a h5py special dtype, or None.
    """
    hdr, ret = makeJSONStub(d)
    
    factory = None
    if h5py.check_opaque_dtype(d): # we're on our own here
        factory = makeFuncStub(makeH5PyOpaqueDtype)
        factory["posonly"] = (o.name,)
        
    else:
        vi = h5py.check_vlen_dtype(d) # a Python (base) type
        
        si = h5py.check_string_dtype(d) # None, or namedtuple with fields 'encoding' and 'length'
            
        ei = h5py.check_enum_dtype(d) # an enum :class: or None
        
        if ei is not None:
            factory = makeFuncStub(makeH5PyEnumDtype)
            factory["posonly"] = (ei.__name__, )
            
        elif vi is not None:
            if si is not None:
                factory = makeFuncStub(makeH5PyStringDtype)
                factory["posonly"] = (si.encoding, si.length)
                
            else:
                factory = makeFuncStub(makeH5PyVlenDtype)
                factory["posonly"] = (vi.__name__, )
                
        elif si is not None:
            factory = makeFuncStub(makeH5PyStringDtype)
            factory["posonly"] = (si.encoding, si.length)
            
        else:
            return
            
    ret["factory"]=factory
    return {hdr:ret}
            
def pandasDtype2JSON(d):
    """Checks if d is a pandas extension dtype (for standard pandas extensions)
    Returns a json representation (either str or dict) if d is a pandas extension
    dtype; returns None otherwise.
    """
    
    # NOTE: 2021-12-16 16:13:26
    # pandas stock extension dtypes are:
    # CategoricalDtype, IntervalDtype, PeriodDtype, SparseDtype, 
    # DatetimeTZDtype, StringDtype, BooleanDtype, UInt*Dtype, Int*Dtype
    #
    # The following are NOT extension dtypes even though pd.api.types provides
    # functions checking for these:
    # 'datetime64', 'datetime64[ns]', 'datetime64[<unit>]' strings for numpy dtype c'tors
    # dtype(np.complex_), dtype("complex128") etc
    #
    #
    # NOTE: 2021-12-16 16:41:37
    # pandas and datetime objects:
    # 
    # The most generic: pd.api.types.is_datetime64_any_dtype
    # can be np.datetime64, np.datetime64[<unit>] or a DatetimeTZDtype dtype
    # >>> is_datetime64_any_dtype(str) -> False
    # >>> is_datetime64_any_dtype(int) -> False
    # >>> is_datetime64_any_dtype(np.array(['a', 'b'])) -> False
    # >>> is_datetime64_any_dtype(np.array([1, 2])) -> False
    #
    # >>> is_datetime64_any_dtype(np.datetime64) -> True # can be tz-naive
    # >>> is_datetime64_any_dtype(DatetimeTZDtype("ns", "US/Eastern")) -> True
    # >>> is_datetime64_any_dtype(np.array([], dtype="datetime64[ns]")) -> True
    # >>> is_datetime64_any_dtype(pd.DatetimeIndex([1, 2, 3], dtype="datetime64[ns]")) -> True
    #
    # The next most generic: pd.api.types.is_datetime64_dtype
    #
    # >>> is_datetime64_dtype(object) -> False
    # >>> is_datetime64_dtype([1, 2, 3]) -> False
    # >>> is_datetime64_dtype(np.array([], dtype=int)) -> False
    # 
    # >>> is_datetime64_dtype(np.datetime64) -> True
    # >>> is_datetime64_dtype(np.array([], dtype=np.datetime64)) -> True
    #
    # More specific (includes unit specification): pd.api.types.is_datetime64_ns_dtype
    #
    # >>> is_datetime64_ns_dtype(str) -> False
    # >>> is_datetime64_ns_dtype(int) -> False
    # >>> is_datetime64_ns_dtype(np.array(['a', 'b'])) -> False
    # >>> is_datetime64_ns_dtype(np.array([1, 2])) -> False
    # >>> is_datetime64_ns_dtype(np.datetime64) -> False # no unit
    # >>> is_datetime64_ns_dtype(np.array([], dtype="datetime64")) -> False # no unit
    # >>> is_datetime64_ns_dtype(np.array([], dtype="datetime64[ps]")) -> False # wrong unit
    #
    # >>> is_datetime64_ns_dtype(DatetimeTZDtype("ns", "US/Eastern")) -> True
    # >>> is_datetime64_ns_dtype(pd.DatetimeIndex([1, 2, 3], dtype="datetime64[ns]")) -> True
    #
    # The most specific: pd.api.types.is_datetime64tz_dtype
    #
    # >>> is_datetime64tz_dtype(object) -> False
    # >>> is_datetime64tz_dtype([1, 2, 3]) -> False
    # >>> is_datetime64tz_dtype(pd.DatetimeIndex([1, 2, 3])) -> False # tz-naive
    #
    # >>> is_datetime64tz_dtype(pd.DatetimeIndex([1, 2, 3], tz="US/Eastern")) -> True
    # >>> is_datetime64tz_dtype(DatetimeTZDtype("ns", tz="US/Eastern")) -> True
    # >>> is_datetime64tz_dtype(.pd.Series([], dtype = DatetimeTZDtype("ns", tz="US/Eastern")) -> True
    #
    #
    if pd.api.types.is_extension_array_dtype(d):
        hdr, ret = makeJSONStub(d)
        if pd.api.types.is_categorical_dtype(d):
            #print("categorical", d.categories)
            # NOTE: 2021-12-15 23:29:07
            # d.categories is a pandas Index type
            # this may be: IntervalIndex, dtype(object), other pandas dtypes
            categories = list(d.categories) # convert to a list
            ordered = d.ordered
            categories_dtype = d.categories.dtype
            category_types = list(type(x).__name__ for x in categories) # python type of category values
            #print("category_types", category_types)
            categories_dtype = d.categories.dtype # dtype of 'categories' Index 
            #print(type(categories_dtype).__name__)
            factory = makeFuncStub("pd.CategoricalDtype")
            factory["named"] = {"categories": categories,
                                    "ordered":ordered,
                                    }
            ret["factory"] = factory
            return {hdr:ret}
            
            #return {d.name: {"__init__": f"CategoricalDtype({categories}, ordered={ordered})",
                             #"__ns__" : "pd",
                             #"categories":categories,
                             #"value_types":list(type(x) for x in d.categories),
                             #"dtype": dtype2JSON(categories_dtype),
                             #"ordered": ordered}}
        
        elif pd.api.types.is_interval_dtype(d):
            subtype = d.subtype
            closed = d.closed
            factory = makeFuncStub(pd.IntervalDtype.__new__)
            factory["named"] = {"subtype":subtype, "closed":closed}
            ret["factory"] = factory
            return {hdr:ret}
            #return{d.name: {"__init__": f"IntervalDtype(subtype={subtype}, closed={closed})",
                            #"__ns__": "pd"}}
        
        #elif pd.api.types.is_period_dtype(d):
            #factory = makeFuncStub(pd.PeriodDtype.__new__)
            #factory["named"] = {"freq": d.freq.name}
            #ret["factory"] = factory
            #return {hdr:ret}
            ##return {d.name: {"__init__": f"PeriodDtype(freq={d.freq.name})",
                             ##"__ns__": "pd",
                             ##"freq":d.freq.name}}
            
        elif pd.api.types.is_period_dtype(d):
            factory = makeFuncStub(pd.PeriodDtype.__new__)
            factory["named"] = {"freq":d.freq.name}
            ret["factory"] = factory
            return {hdr:ret}
            #return {d.name: {"__init__":f"PeriodDtype(freq={d.freq.name})",
                             #"__ns__": "pd",
                             #"freq":d.freq.name}}
        
        
        elif pd.api.types.is_datetime64_any_dtype(d):
            if pd.api.types.is_datetime64tz_dtype: # extension type
                # NOTE: 2021-12-16 17:02:46
                # as of pandas 1.3.3: DatetimeTZDtype only supports 'ns' as unit
                # as opposed to np.datetime64 which can have multiple flavors e.g.
                # np.dtype("datetime64[ps]") etc
                factory = makeFuncStub("pd.DatetimeTZDtype")
                factory["named"] = {"unit":d.unit, "tz": d.tz.zone}
                ret["factory"] = factory
                return {hdr:ret}
                #return {d.name: {"__init__": f"DatetimeTZDtype(unit={d.unit}, tz={d.tz.zone})",
                                #"__ns__": "pd",
                                #"unit": d.unit,
                                #"tz":d.tz.zone}}
            
            elif ps.api.types.is_datetime64_ns_dtype(d): # this is a numpy dtype, not sure if branch ever gets execd
                return numpyDtype2JSON(d)
                #ret["instance_type"] = "dtype"
                #factory = makeFuncStub(np.dtype.__new__)
                
                #ret["factory"] = factory
                #return d.name
            
            elif pd.api.types.is_datetime64_dtype(d): # this is a numpy dtype, not sure if branch ever gets execd
                return numpyDtype2JSON(d)
                #return d.name
        
        elif pd.api.types.is_sparse(d):
            factory = makeFuncStub("pd.SparseDtype")
            factory["named"] = {"dtype":d.type, "fill_value":d.fill_value}
            ret["factory"] = factory
            return {hdr:ret}
            #return {d.name: {"__init__": f"SparseDtype(dtype={d.type}, fill_value={d.fill_value})",
                             #"__ns__": "pd",
                             #"dtype": d.type,
                             #"fill_value": d.fill_value}}
        
        elif pd.api.types.is_string_dtype(d):
            factory = makeFuncStub("pd.StringDtype")
            factory["named"] = {"storage":d.storage}
            ret["factory"] = factory
            return {hdr:ret}
            #return {d.name: {"__init__": f"StringDtype(storage={d.storage})",
                             #"__ns__": "pd",
                             #"storage": d.storage}}
        
        else: # BooleanDtype, UInt*Dtype, Int*Dtype, Float*Dtype
            factory = makeFuncStub(f"pd.{type(d).__name__}")
            ret["factory"] = factory
            return {hdr:ret}
            #return {d.name: {"__init__": f"{type(d).__name__}()",
                             #"__ns__":"pd"}}
        
#def json2dtype(s):
    #"""Roundtrip numpy dtype - json string format - read side
    #An alternative to np.lib.format.descr_to_dtype
    #"""
    #if isinstance(s, str):
        #try:
            #return np.dtype(s)
        #except:
            #try:
                #return eval("np.dtype(" + s + ")") # for structured arrays
            #except:
                #raise
                
    #elif isinstance(s, dict): # for recarrays, h5py, pandas
        #return np.dtype(s) 

def decode_hook(dct):
    """ Almost complete round trip for a subset of Python types - read side.
    
    Implemented types:
    type
    complex
    UnitQuantity
    Quantity
    numpy chararray, structured array, recarray and ndarray (with caveats, see
    documentation for CustomEncoder in this module)
    
    Pass this as the 'object_hook' parameter to json.load & json.loads (this is
    what the load and loads functions in this module do).
    
    Use it whenever the json was dumped using the CustomEncoder :class: (defined
    in this module) as 'cls' parameter.
    """
    from core import prog
    
    if len(dct) == 1: # only work on dict with a single entry here
        key = list(dct.keys())[0]
        data = dct[key]
        if data is None or not isinstance(data, dict):
            return dct
        #print("data", data)
        val = data.get("value", None) # may be a dict, see below for *array__
        module = data.get("__module__", "builtins")
        
        if val is None:
            return dct
        
        if key == "complex":
            if isinstance(val, (tuple, list)) and len(val) == 2:
                return complex(*val)
            
            elif isinstance(val, dict) and all(k in val for k in ("real", "imag")):
                return complex(val["real"], val["imag"])
            
            else:
                return val
            
        elif key == "unitquantity":
            return scq.unit_quantity_from_name_or_symbol(val)
        
        elif key.endswith("SignatureDict"):
            return prog.SignatureDict(**val)
        
        elif key == "axistags":
            return vigra.AxisTags.fromJSON(val)
        
        elif key == "dtype":
            return np.dtype(val)
            
        elif key.endswith("array"):
            #entry = list(dct.keys())[0]
            #val = dct[entry]
            if key in ("structarray", "recarray"):
                value = list(tuple(x) for x in val)
            else:
                value = val #["value"]
                
            if key == "recarray":
                dtype = json2dtype(dict((name, (json2dtype(value[0]), value[1])) for name, value in data["dtype"].items()))
            else:
                dtype = json2dtype(data["dtype"])
            
            ret = np.array(value, dtype=dtype)
            
            if key in ("chararray", "recarray"):
                artype = eval(key, np.__dict__)
                return ret.view(artype)
            
            if key == "quantityarray":
                units = scq.unit_quantity_from_name_or_symbol(data["__units__"])
                return ret * units
            
            if entry == "vigraarray":
                return vigra.VigraArray(ret, axistags=vigra.AxisTags.fromJSON(data["axistags"]), 
                                    order=data.get("__order__", None))
            
            return ret
        
        elif key == "kernel1D":
            xy = np.array(val)
            left = int(xy[0,0])
            right = int(xy[-1,0])
            values = xy[:,1]
            ret = vigra.filters.Kernel1D()
            ret.initExplicitly(left, right, values)
            return ret
        
        elif key == "kernel2D":
            xy = np.array(val)
            upperLeft = (int(xy[-1,-1,0]), int(xy[-1,-1,1]))
            lowerRight = (int(xy[0,0,0]), int(xy[0,0,1]))
            values = xy[:,:,]
            ret = vigra.filters.Kernel2D()
            ret.initExplicitly(upperLeft, lowerRight, values)
            return ret
        
        elif key == "type":
            #print("val", val)
            if "." in val:
                components = val.split(".")
                objName = components[-1]
                modname = ".".join(components[:-1])
                module = sys.modules[modname]
                return eval(objName, module.__dict__)
            else:
                return eval(objName) # fingers crossed...
            
        else:
            return dct
    else:
        return dct

def dump(obj, fp, *args, **kwargs):
    kwargs["default"] = object2JSON
    #kwargs["cls"] = CustomEncoder
    json.dump(obj,fp, *args, **kwargs)
    
def dumps(obj, *args, **kwargs):
    kwargs["default"] = object2JSON
    return json.dumps(obj, *args, **kwargs)

def load(fp, *args, **kwargs):
    ret = json.load(fp, *args, **kwargs)
    return json2python(ret)
        
def loads(s):
    ret = json.loads(s)
    return json2python(ret)
    
def load(filename):
    with open(filename, mode="rt") as jsonfile:
        s = jsonfile.read()
        ret = loads(s)
        
    return ret

def json2python(jsonobj):
    """Restores a Python object from it JSON representation.
    
    WARNING: Functions, and, with a few exceptions, types and method objects 
    cannot be restored unless they are already defined in a module that can be 
    imported at runtime.
    
    The exceptions are types that can be (re)created dynamically at runtime using
    factory functions defined in modules that can be imported at runtime.
    
    Likewise, it may be possible to restore method objects that belong to types
    (re)created dynamically via factory functions.
    
    For general schema see module docstring.
    
    
    NOTE: Object initialization proceeds via the following steps:
    
    1) resolve object's type using object's type name and name of module where 
        it is defined (via traitlets.utils.importstring.import_item())
        
        if this fails, try to use type_factory to recreate the object type
        dynamically; finally, bail out if this also fails
    
    2) initialize the object
    
    1) when jsonobj["__init__"] and jsonobj["__new__"] are None (JSON 'null')
    
        Uses object's type as a callable; parameters are retrieved from the
        "posonly", "named", "varpos", "kwonly" and "varkw"
        entries in data.
        
    b) when data["__init__"] is a str that resolves to a function:
    
        Use the function as initializer; parameters are retrieved from 
        data["__args__"], data["named"],  and data["__kwargs__"]
        
    c) when data["__init__"] is a dict representation of function signature:
        c.1) When data["__init__"]["name"] is "__init__":
        
            creates a 'stub' object by calling the constructor:
            
            obj = object_type.__new__(object_type)
            
            then initializes the object:
            
            obj.__init__(...) 
            
            parameters for obj.__init__are retrieved from data["__args__"], 
            data["named"],  and data["__kwargs__"] <-- TODO: try to match 
            with __init__ signature
            
    """
    
    #if isinstance(jsonobj, collections.abc.Sequence):
        #ret = type(jsonobj)(tuple(json2python(v) for v in jsonobj))
        #return ret
        
    if isinstance(jsonobj, list):
        return list(json2python(v) for v in jsonobj)
    
    if isinstance(jsonobj, tuple):
        return tuple(json2python(v) for v in jsonobj)
    
    if not isinstance(jsonobj, dict):
        return jsonobj
    
    ret = dict()
    for key, val in jsonobj.items():
        if key == "python_type":
            if val == "None":
                return None
            
            ret = resolveObject(val["type_module"], val["type_name"])
            if ret == MISSING:
                raise RuntimeError(f"Cannot resolve {'.'.join([val['type_module'], val['type_name']])}")
            
            return ret
        
        elif key == "python_function_or_method":
            name = val["name"]
            modname = val["module"]
            qualname = val["qualname"]
            if qualname == name: # definitely a function
                ret = resolveObject(val["module"], val["qualname"])
                
            else: # might be a method
                owner_type_name = ".".join(qualname.strip(".")[:-1]) 
                owner = resolveObject(val["module"], owner_type_name)
                if owner == MISSING:
                    # likely an unbound function, but check
                    ret = resolveObject(val["module"], val["qualname"])
                
                else:
                    ret = inspect.getattr_static(owner, name, MISSING)
            
            
            if ret == MISSING:
                raise RuntimeError(f"Cannot resolve {'.'.join([val['module'], val['qualname']])}")
            
            return ret
        
        elif key == "python_method": # this branch is now DEPRECATED 2021-12-25 22:06:51
            name = val["name"]
            modname = val["module"]
            qualname = val["qualname"]
            owner_type_name = ".".join(qualname.strip(".")[:-1])
            owner = resolveObject(val["module"], owner_type_name)
            if owner == MISSING:
                raise RuntimeError(f"Cannot resolve {owner_type_name}")

            return inspect.getattr_static(owner, name)
            
        elif key == "python_object":
            obj_type = resolveObject(val["instance_module"], val["instance_type"])

            if obj_type is MISSING:
                # NOTE: 2021-12-22 23:24:38 
                # could not import obj_type; try to recreate it here
                type_factory_spec = val["type_factory"]
                if isinstance(type_factory_spec, dict):
                    signature = type_factory_spec["signature"]
                    type_factory_func = resolveObject(signature["module"], 
                                                      signature["qualname"])
                    
                    if type_factory_func == MISSING:
                        raise RuntimeError(f"Cannot resolve object type {obj_type}")
                        
                    if isinstance(type_factory_func, (types.FunctionType, types.MethodType)):
                        type_factory_args = type_factory_spec["posonly"] + type_factory_spec["varpos"]
                        type_factory_kwargs = dict()
                        type_factory_kwargs.update(type_factory_spec["named"])
                        type_factory_kwargs.update(type_factory_spec["kwonly"])
                        type_factory_kwargs.update(type_factory_spec["varkw"])
                        
                        obj_type = type_factory_func(*type_factory_args, **type_factory_kwargs)
                        
                    else:
                        raise RuntimeError(f"Cannot resolve object type")
                    
                else:
                    raise RuntimeError(f"Cannot resolve object type")
                    
            obj_factory_spec = val["factory"]
            
            if isinstance(obj_factory_spec, dict):
                posonly = obj_factory_spec.get("posonly", tuple())
                varpos = obj_factory_spec.get("varpos", tuple())
                
                obj_factory_args = list(json2python(v) for v in posonly)
                obj_factory_args.extend(list(json2python(v) for v in varpos))
                
                named = obj_factory_spec.get("named", dict())
                kwonly = obj_factory_spec.get("kwonly", dict())
                varkw = obj_factory_spec.get("varkw", dict())

                obj_factory_kwargs = dict((k, json2python(v)) for k, v in named.items())
                obj_factory_kwargs.update(dict((k, json2pyton(v)) for k,v in kwonly.items()))
                obj_factory_kwargs.update(dict((k, json2python(v)) for k,v in varkw.items()))
            
                obj_factory = None
                
                signature = obj_factory_spec["signature"]
                
                if isinstance(signature, dict):
                    if isinstance(signature["module"], str) and len(signature["module"].strip()):
                        obj_factory = resolveObject(signature["module"], 
                                                    signature["qualname"])
                        
                    else:
                        obj_factory = getattr(obj_type, signature["name"], None)
                        
                elif isinstance(signature, str):
                    try:
                        obj_factory = import_item(signature)
                    except:
                        pass
                    
                if isinstance(obj_factory, CALLABLE_TYPES):
                    if obj_factory.__name__ == "__new__":
                        obj_factory_args.insert(0, obj_type)
                        
                else:
                    obj_factory = obj_type # last ditch attempt
                
                if obj_factory == np.dtype:
                    if len(posonly) == 1 and isinstance(posonly[0], dict):
                        # NOTE: 2021-12-27 11:35:08
                        # this also takes care of field titles in dtypes of 
                        # structured arrays and recarrays
                        fields = dict((k, (json2python(v[0]), *v[1:])) for k,v in posonly[0].items())
                        return obj_factory(fields)
                        #return np.dtype(fields)
                    
                elif obj_factory == np.array:
                    #print("np.array")
                    if val["subtype"] in ("structarray", "recarray") or obj_type == np.recarray:
                        data = list(tuple(v) for v in posonly[0])
                        dtype = json2python(obj_factory_spec["named"]["dtype"])
                        
                        ret = obj_factory(data, dtype=dtype)
                        
                        if obj_type == np.recarray:
                            return ret.view(obj_type)
                        
                        elif val["subtype"] == "recarray":
                            arraytype = resolveObject("numpy", val["subtype"])
                            return ret.view(arraytype)
                        
                    else:
                        ret = obj_factory(*obj_factory_args, **obj_factory_kwargs)
                            
                    return ret
                    
                elif obj_factory == ma.array:
                    if val["subtype"] in ("structarray", "recarray") or obj_type == np.recarray:
                        mask = list(tuple(v) for v in obj_factory_spec["named"]["mask"])
                        data = list(tuple(v) for v in posonly[0])
                        dtype = json2python(obj_factory_spec["named"]["dtype"])
                        # NOTE: 2021-12-27 23:25:50
                        # no 'fill_value' for masked structarrays (because
                        # these have fill_value numpy.void, which json doesn't
                        # support); hence the fill value will fallback to the 
                        # default set in the c'tor
                        #fill_value = obj_factory_kwargs["fill_value"]
                        arr = np.array(data, dtype=dtype)
                        if val["subtype"] == "recarray":
                            arr = arr.view(np.recarray)
                            
                        return ma.array(arr, mask=mask) # see NOTE: 2021-12-27 23:25:50
                
                #print("obj_factory", obj_factory)
                return obj_factory(*obj_factory_args, **obj_factory_kwargs)
            
            else:
                # fingers crossed...
                if obj_type is not MISSING:
                    return obj_type(val["value"])
                
                else:
                    ret[json2python(key)] = json2python(val["value"])
            
        else:
            # recurse into jsonobj value
            ret[json2python(key)] = json2python(val)
            
    return ret
    
def kernelFromJSON(kernelcoords:list, *args, **kwargs):
    from imaging.vigrautils import kernelfromarray
    xy = np.array(kernelcoords)
    return kernelfromarray(xy)


