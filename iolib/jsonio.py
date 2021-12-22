"""JSON codecs
NOTE: 2021-12-21 16:11:42
Testing the following alternative json libs/packages:
simplejson => NO
    + deals with named tuples BUT 
    - outputs as if a dict and
    - hardcoded in C
    
orjson 
    + hardcoded in C, claims the fastest (in nay case faster than json, simplejson)
    + promising for datetime & numpy arrays
    + seems more flexible 
    + no JSONEncoder to inherit from; must supply a default callable, quite flexible.
        ~ claims not to serialize namedtuple but the 'default' mechanism works;
        + the default can be a generic function (via single dispatch
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
"""

import sys, traceback, typing, collections, inspect
import json
#import simplejson as json
import orjson
from collections import deque, namedtuple
from functools import (singledispatch, singledispatchmethod, 
                       update_wrapper, wraps,)
import numpy as np
import quantities as pq
import pandas as pd
import h5py
import vigra
from traitlets.utils.importstring import import_item
from core import quantities as cq
from core import prog
from core.prog import (classifySignature, resolveObject, MISSING )

def makeJSONStub(o):
    if isinstance(o, type):
        header = "__python_type__"
        ret = {"__type_name__":     o.__qualname__,
               "__type_module__":   o.__module__,
               "__type_factory__":      {"__init__": None,
                                         "__args__": tuple(),
                                         "__named__": dict(),
                                         "__kwargs__": dict(),
                                         },
               }
        
    elif inspect.isfunction(o):
        header = "__python_function__"
        ret = dict(prog.classifySignature(o))
                                            
    elif inspect.ismethod(o):
        header = "__python_method__"
        # NOTE/TODO: 2021-12-18 22:26:27
        # can I differentiate between class method and instance method?
        ret = dict(prog.classifySignature(o))
                                            
    else:
        header = "__python_object__"
        ret = {"__instance_type__":     type(o).__qualname__,
               "__instance_module__":   type(o).__module__,
               "__type_factory__":      {"__init__": None,
                                         "__args__": tuple(),
                                         "__named__": dict(),
                                         "__kwargs__": dict(),
                                         },
               "__init__":              None,
               "__new__":               None,
               "__args__":              tuple(),
               "__named__":             dict(),
               "__kwargs__":            dict(),
               "__value__":             None,
               "__subtype__":           None,
               "__dtype__":             None,
               }
                
    return header, ret
        
@singledispatch
def object2JSON(o):
    from core.datatypes import is_namedtuple
    hdr, ret = makeJSONStub(o)
    if is_namedtuple(o):
        ret.update({"__named__": dict((f, getattr(o,f)) for f in o._fields),
                    "__type_factory__": {"__init__": "collections.namedtuple",
                                         "__named__": {"typename": type(o).__name__,
                                                       "field_named": tuple(f for f in o._fields)}}})
    return {hdr:ret}
    
@object2JSON.register(type)
def _(o:type):
    from core.datatypes import is_namedtuple
    hdr, ret = makeJSONStub(o)
    if is_namedtuple(o):
        ret.update({"__type_factory__": {"__init__": "collections.namedtuple",
                                         "__named__": {"typename": type(o).__name__,
                                                       "field_named": tuple(f for f in o._fields)}}})
    return {hdr:ret}
    
@object2JSON.register(complex)
def _(o:complex):
    return {"__args__": (o.real, o.imag)}

@object2JSON.register(deque)
def _(o:deque):
    hdr, ret = makeJSONStub(o)
    ret.update({"__args__": (list(o),)})
    #ret.update({"__value__": list(o)})
    return {hdr:ret}
    
@object2JSON.register(vigra.filters.Kernel1D)
@object2JSON.register(vigra.filters.Kernel2D)
def _(o:typing.Union[vigra.filters.Kernel1D, vigra.filters.Kernel2D]):
    from imaging.vigrautils import kernel2array
    hdr, ret = makeJSONStub(o)
    xy = kernel2array(o, True)
    ret.update({"__args__" : (xy.tolist(),),
                "__init__": classifySignature(kernelfromjson)})
    return {hdr:ret}

def dtype2JSON(d:np.dtype) -> typing.Union[str, dict]:
    """Roundtrip numpy dtype - json string format - write side
    An alternative to the np.lib.format.dtype_to_descr
    Returns a dict for recarray dtypes; a str in any other case.
    """
    # NOTE: 2021-12-14 22:51:17
    # for pandas dtypes return either a str or a dict
    # for special h5py dtypes returns a dict:
    # * mapping original dtype (or type) as str mapped to the h5py dtype initializer(as str)
    if not isinstance(d, np.dtype) and not pd.api.types.is_extension_array_dtype(d):
        raise TypeError(f"Expecting a numpy dtype, or pandas extvension dtype instance; got {type(d).__name__} instead")
    
    #print("dtype2JSON", d)
    
    h5pyjson = h5pyDtype2JSON(d)
    
    if h5pyjson is not None:
        return h5pyjson
    
    pandasjson = pandasDtype2JSON(d)
    if pandasjson is not None:
        return pandasjson
    
    fields = d.fields
    
    if d.name.startswith("record"):
        return dict((name, (dtype2JSON(value[0]), value[1])) for name, value in d.fields.items())
        
    else:   
        if fields is None:
            return np.lib.format.dtype_to_descr(d) #does not perform well for structured arrays?
        else:
            return d.name
    
def h5pyDtype2JSON(d):
    """Checks if d is a special h5py dtype.
    Returns a json representation (dict) if d is a h5py speciall dtype, or None.
    """
    if h5py.check_opaque_dtype(d): # we're on our own here
        return {str(d): {"__init__": f"opaque_dtype(np.dtype('{str(d)}'))",
                         "__ns__": "h5py"}}
    else:
        vi = h5py.check_vlen_dtype(d) # a Python (base) type
        
        si = h5py.check_string_dtype(d) # None, or namedtuple with fields 'encoding' and 'length'
            
        ei = h5py.check_enum_dtype(d) # an enum :class: or None
        
        if ei is not None:
            return {ei.__name__: {"__init__": f"enum_dtype({ei.__name__})",
                                "__ns__": "h5py"}}
        
        elif vi is not None:
            if si is not None: 
                return {vi.__name__: {"__init__": f"string_dtype('{si.encoding}', {si.length})",
                                    "__ns__": "h5py"}}
            else:
                return {vi.__name__: {"__init__": f"vlen_dtype({vi.__name__})",
                                    "__ns__": "h5py"}}

        elif si is not None:
            return {vi.__name__: {"__init__": f"string_dtype('{si.encoding}', {si.length})",
                                "__ns__": "h5py"}}
            
def pandasDtype2JSON(d):
    """Checks if d is a pandas extension dtype (for standard pandas extensions)
    Returns a json representation (either str or dict) id d is a pandas extension
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
        if pd.api.types.is_categorical_dtype(d):
            #print("categorical", d.categories)
            # NOTE: 2021-12-15 23:29:07
            # d.categories is a pandas Index type
            # this may be: IntervalIndex, dtype(object), other pandas dtypes
            categories = list(d.categories) # convert to a list
            ordered = d.ordered
            categories_dtype = d.categories.dtype
            category_types = list(type(x).__name__ for x in categories) # python type of category values
            print("category_types", category_types)
            categories_dtype = d.categories.dtype # dtype of 'categories' Index 
            print(type(categories_dtype).__name__)
            return {d.name: {"__init__": f"CategoricalDtype({categories}, ordered={ordered})",
                             "__ns__" : "pd",
                             "categories":categories,
                             "value_types":list(type(x) for x in d.categories),
                             "dtype": dtype2JSON(categories_dtype),
                             "ordered": ordered}}
        
        elif pd.api.types.is_interval_dtype(d):
            subtype = d.subtype
            closed = d.closed
            return{d.name: {"__init__": f"IntervalDtype(subtype={subtype}, closed={closed})",
                            "__ns__": "pd"}}
        
        elif pd.api.types.is_period_dtype(d):
            return {d.name: {"__init__": f"PeriodDtype(freq={d.freq.name})",
                             "__ns__": "pd",
                             "freq":d.freq.name}}
            
        
        elif pd.api.types.is_datetime64_any_dtype(d):
            if pd.api.types.is_datetime64tz_dtype: # extension type
                # NOTE: 2021-12-16 17:02:46
                # as of pandas 1.3.3: DatetimeTZDtype only supports 'ns' as unit
                # as opposed to np.datetime64 which can have multiple flavors e.g.
                # np.dtype("datetime64[ps]") etc
                return {d.name: {"__init__": f"DatetimeTZDtype(unit={d.unit}, tz={d.tz.zone})",
                                "__ns__": "pd",
                                "unit": d.unit,
                                "tz":d.tz.zone}}
            
            elif ps.api.types.is_datetime64_ns_dtype(d): # this is a numpy dtype, not sure if branch ever gets execd
                return d.name
            
            elif pd.api.types.is_datetime64_dtype(d): # this is a numpy dtype, not sure if branch ever gets execd
                return d.name
        
        elif pd.api.types.is_sparse(d):
            return {d.name: {"__init__": f"SparseDtype(dtype={d.type}, fill_value={d.fill_value})",
                             "__ns__": "pd",
                             "dtype": d.type,
                             "fill_value": d.fill_value}}
        
        elif pd.api.types.is_string_dtype(d):
            return {d.name: {"__init__": f"StringDtype(storage={d.storage})",
                             "__ns__": "pd",
                             "storage": d.storage}}
        
        elif pd.api.types.is_period_dtype(d):
            return {d.name: {"__init__":f"PeriodDtype(freq={d.freq.name})",
                             "__ns__": "pd",
                             "freq":d.freq.name}}
        
        else: # BooleanDtype, UInt*Dtype, Int*Dtype, Float*Dtype
            return {d.name: {"__init__": f"{type(d).__name__}()",
                             "__ns__":"pd"}}
        
def json2dtype(s):
    """Roundtrip numpy dtype - json string format - read side
    An alternative to np.lib.format.descr_to_dtype
    """
    if isinstance(s, str):
        try:
            return np.dtype(s)
        except:
            try:
                return eval("np.dtype(" + s + ")") # for structured arrays
            except:
                raise
                
    elif isinstance(s, dict): # for recarrays, h5py, pandas
        return np.dtype(s) 

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
        val = data.get("__value__", None) # may be a dict, see below for *array__
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
            
        elif key == "__unitquantity__":
            return cq.unit_quantity_from_name_or_symbol(val)
        
        elif key.endswith("SignatureDict"):
            return prog.SignatureDict(**val)
        
        elif key == "__axistags__":
            return vigra.AxisTags.fromJSON(val)
        
        elif key == "__dtype__":
            return np.dtype(val)
            
        elif key.endswith("array__"):
            #entry = list(dct.keys())[0]
            #val = dct[entry]
            if key in ("__structarray__", "__recarray__"):
                value = list(tuple(x) for x in val)
            else:
                value = val #["__value__"]
                
            if key == "__recarray__":
                dtype = json2dtype(dict((name, (json2dtype(value[0]), value[1])) for name, value in data["__dtype__"].items()))
            else:
                dtype = json2dtype(data["__dtype__"])
            
            ret = np.array(value, dtype=dtype)
            
            if key in ("__chararray__", "__recarray__"):
                artype = eval(key.replace("__", ""), np.__dict__)
                return ret.view(artype)
            
            if key == "__quantityarray__":
                units = cq.unit_quantity_from_name_or_symbol(data["__units__"])
                return ret * units
            
            if entry == "__vigraarray__":
                return vigra.VigraArray(ret, axistags=vigra.AxisTags.fromJSON(data["__axistags__"]), 
                                    order=data.get("__order__", None))
            
            return ret
        
        elif key == "__kernel1D__":
            xy = np.array(val)
            left = int(xy[0,0])
            right = int(xy[-1,0])
            values = xy[:,1]
            ret = vigra.filters.Kernel1D()
            ret.initExplicitly(left, right, values)
            return ret
        
        elif key == "__kernel2D__":
            xy = np.array(val)
            upperLeft = (int(xy[-1,-1,0]), int(xy[-1,-1,1]))
            lowerRight = (int(xy[0,0,0]), int(xy[0,0,1]))
            values = xy[:,:,]
            ret = vigra.filters.Kernel2D()
            ret.initExplicitly(upperLeft, lowerRight, values)
            return ret
        
        elif key == "__type__":
            #print("val", val)
            if "." in val:
                components = val.split(".")
                objName = components[-1]
                modname = ".".join(components[:-1])
                #print("modname", modname, "objName", objName)
                module = sys.modules[modname]
                return eval(objName, module.__dict__)
            else:
                return eval(objName) # fingers crossed...
            
        else:
            return dct
    else:
        return dct
    
#def dumps(obj, *args, **kwargs):
    #from core.datatypes import is_namedtuple
    #kwargs["cls"] = CustomEncoder
    ##if is_namedtuple(obj):
        ##obj = NamedTupleWrapper(obj)
    #return json.dumps(obj, *args, **kwargs)

#def dump(obj, fp, *args, **kwargs):
    #kwargs["cls"] = CustomEncoder
    #json.dump(obj,fp, *args, **kwargs)
    

#def loads(s, *args, **kwargs):
    #kwargs["object_hook"] = decode_hook
    #return json.loads(s, *args, **kwargs)

#def load(fp, *args, **kwargs):
    #kwargs["object_hook"] = decode_hook
    #return json.load(fp, *args, **kwargs)

def dumps(obj, *args, **kwargs):
    kwargs["default"] = object2JSON
    return orjson.dumps(obj, *args, **kwargs).decode("utf-8")

def dump(filename, obj, *args, **kwargs):
    with open(filename, mode="wt") as jsonfile:
        jsonfile.write(dumps(obj, *args, **kwargs))
        
def loads(s):
    ret = orjson.loads(s)
    
    if isinstance(ret, dict):
        return json2python(ret)
        
    else:
        return ret

def load(filename):
    with open(filename, mode="rt") as jsonfile:
        s = jsonfile.read()
        ret = loads(s)
        
    return ret

def json2python(dct):
    """
    NOTE: general schema:
    
    Below, <key> is one of: 
    "__python_type__", "__python_function__", "__python_method__", 
    "__python_object__"
    
    {<key>:{
        "__instance_type__": str; the name of the object's type, when object is
                                an instance 
        
        "__instance_module__": str; the name of the module where the object's 
                            type is defined (when object is an instance)
        
        "__type_name__": str; for type objects, the name of the object 
                                (obj.'__name__');
                                
                              for instances, same value as __instance_type__
                              
        "__type_module__": str; for type objects, the name of the module where 
                                the object (a type) is defined;
                                
                                for instances, same value as __instance_module__
                                
        "__type_factory__": dict or None; 
            
            When not None, it will be used when the type of the instance being
            serialized (or the type being serialized) cannot be imported (e.g. 
            in case of dynamically created classes such as named tuples).
            
            When a dict, it expects the following structure:
            {
                "__func__": str or signature dict for the type factory
                            When a str, this is the name of a callable to generate
                            the object's type (for python instances) or the type
                            being serialized.
                            When a dict, this represents the signature of a type 
                            factory as above.
                            The parameters passed to this function are given in 
                            "__args__", "__named__" and "__kwargs__", detailed 
                            next; CAUTION not to be confused with the __args__,
                            __named__ and __kwargs__ for the constructor/initializer
                            which are explained further below.
                            
                "__args__": tuple
                "__named__": dict
                "__kwargs__": dict
            }
            
            The type factory will use the parameters in __args__, __named__ and 
            __kwargs__ (see below)
            
        "__init__": one of: 
                    :str: = the qualified name of instance initializer function 
                    or method
                    
                    :dict: = the signature of the initializer function or method
                    
                    
                    By default this contains the dict of the signature of the
                    instance type __init__ method.
                    
        "__new__": dict, or None
                    :str: = the qualified name of the constructor function or
                    method
                    
                    :dict: = the signature of the constructor function or method
                    
                    The parameters passed to this function are given in 
                    "__args__", "__named__" and "__kwargs__", detailed below
        
                    By default this contains the dict of the signature of the
                    instance type __new__ method.
                    
        "__args__": tuple; parameters for object intialization, or empty tuple
        
        "__kwargs__": dict; keyword parameters for object initialization, or 
                            empty dict
                            
        "__subtype__": str or None
                When a str it is used specifically for numpy structured arrays
                and for Pandas extension dtypes
        
        "__dtype__": str; representation of the numpy dtye, or json representation
                    of a specialized dtype (such as h5py special dtypes, or 
                    pandas extension dtypes)
                        
        "__value__": str: JSON representation of the value, or None (a.k.a null)
                    this is usually the JSON representation for objects of
                    basic Python types that can be directly serialized (either
                    using Python's json or any other 3rd party library, e.g. 
                    orjson)
                            
        }
    }
    
    
    
    NOTE: Object initialization from a JSON data structure ('data'):
    
    a) when both data["__init__"] and data["__new__"] are None (JSON 'null')
    
        Uses object's type as a callable; parameters are retrieved from 
        data["__args__"], data["__named__"],  and data["__kwargs__"]
        
    b) when data["__init__"] is a str that resolves to a function:
    
        Use the function as initializer; parameters are retrieved from 
        data["__args__"], data["__named__"],  and data["__kwargs__"]
        
    c) when data["__init__"] is a dict representation of function signature:
        c.1) When data["__init__"]["name"] is "__init__":
        
            creates a 'stub' object by calling the constructor:
            
            obj = object_type.__new__(object_type)
            
            then initializes the object:
            
            obj.__init__(...) 
            
            parameters for obj.__init__are retrieved from data["__args__"], 
            data["__named__"],  and data["__kwargs__"] <-- TODO: try to match 
            with __init__ signature
            
    """
    if not isinstance(dct, dict):
        return dct
    
    ret = dict()
    for key, val in dct.items():
        if key == "__python_type__":
            return resolveObject(val["__type_module__"], val["__type_name__"])
        
        elif key == "__python_function__":
            return resolveObject(val["module"], val["qualname"])
        
        elif key == "__python_method__":
            name = val["name"]
            modname = val["module"]
            qualname = val["qualname"]
            owner_type_name = ".".join(qualname.strip(".")[:-1])
            owner = resolveObject(val["module"], owner_type_name)
            #return getattr(owner, name)
            return inspect.getattr_static(owner, name)
            
        elif key == "__python_object__":
            obj_type = resolveObject(val["__instance_module__"], val["__instance_type__"])
            if obj_type is MISSING:
                # NOTE: 2021-12-22 23:24:38 
                # could not import obj_type; try to recreate it here
                factory = val["__type_factory__"]
                if isinstance(factory, dict):
                    init = factory["__init__"]
                    if isinstance(init, str):
                        try:
                            init = import_item(init)
                            
                        except:
                            raise ValueError("fCannot resolve {init}")
                        
                    elif isinstance(init, dict):
                        init = sig2func(init) # FIXME/TODO 2021-12-22 23:38:30 see prog.
                    
            init_func_data = val["__init__"]
            args = val["__args__"]
            kwargs = val["__named__"]
            kwargs.update(val["__kwargs__"])
            #print(f"obj_type {obj_type}")
            #print(f"init_func_data {init_func_data}")
            if isinstance(init_func_data, str): 
                # expects a fully qualified name, i.e., package.module.function
                #   e.g., imaging.vigrautils.kernelfromarray
                # Won't work with a method name i.e., package.module.type.method_name
                #   e.g., imaging.scandata.ScanData.__init__
                
                init_func = import_item(init_func_data)
                
            elif isinstance(init_func_data, dict):
                # check if this is obj_type.__init__
                if init_func_data["name"] == "__init__" and "." in init_func_data["qualname"]:
                    owner_type_name = ".".join(init_func_data["qualname"].split(".")[:-1])
                    owner_type = resolveObject(init_func_data["module"], owner_type_name)
                    
                    if owner_type is not obj_type:
                        raise ValueError(f"signature of '__init__' indicates has a different owner: {owner.__name__}; expecting {obj_type.__name__}")
                    
                    init_func = obj_type
                    
                elif init_func_data["name"] == "__new__" and "." in init_func_data["qualname"]:
                    owner_type_name = ".".join(init_func_data["qualname"].split(".")[:-1])
                    owner_type = resolveObject(init_func_data["module"], owner_type_name)
                    
                    if owner_type is not obj_type:
                        raise ValueError(f"signature of '__new__' indicates a different owner: {owner.__name__}; expecting {obj_type.__name__}")
                    
                    init_func = inspect.getattr_static(obj_type, "__new__")
                    
                else:
                    init_func_name = ".".join([init_func_data["module"], init_func_data["qualname"]])
                    init_func = import_item(init_func_name)
                    
            else: # init_func_data is either None or some gobbledygook => fallback on calling obejct type as c'tor/initalizer'
                init_func = obj_type
                    
            return init_func(*args, **kwargs)
            
        else:
            ret[key] = json2python(val)
            
    return ret
    
def kernelfromjson(kernelcoords:list, *args, **kwargs):
    from imaging.vigrautils import kernelfromarray
    xy = np.array(kernelcoords)
    return kernelfromarray(xy)

