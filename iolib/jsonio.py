"""JSON codecs
"""

import json, sys, traceback, typing, collections
from collections import deque, namedtuple
import numpy as np
import quantities as pq
import pandas as pd
import h5py
import vigra
from traitlets.utils.importstring import import_item
from core import quantities as cq
from core.prog import ObjectDescription

class CustomEncoder(json.JSONEncoder):
    """Almost complete round trip for a subset of Python types - read side.
    
    For now, use decode_hook() module function as counterpart for reading json
    
    Supported types:
    type
    complex
    UnitQuantity
    Quantity
    numpy chararray, structured array, recarray and ndarray (with caveats, 
    see below)
    vigra.filters Kernel1D, and Kernel2D
    
    Pass this :class: as the 'cls' parameter to json.dump & json.dumps
    (this is what dump and dumps functions in this module do)
    
    NOTE: This does NOT affect custom types that use their own encoding
    (e.g. vigra.AxisTags' toJSON() and fromJSON())
    
    WARNING: Caveats:
    Whiel this can be used to encode SMALL numpy arrays (including recarrays,
    structured arrays and chararrays) this is NOT recommended for storing
    large arays and arrays of complex types.
    """
    
    # NOTE: Note Keys in key/value pairs of JSON are always of the type str. 
    # When a dictionary is converted into JSON, all the keys of the dictionary
    # are coerced to strings. As a result of this, if a dictionary is converted 
    # into JSON and then back into a dictionary, the dictionary may not equal the 
    # original one. That is, loads(dumps(x)) != x if x has non-string keys. 
    
    # NOTE:
    
    # Python                                  JSON
    # ----------------------------------------------
    # dict                                    object
    # list, tuple                             array
    # str                                     string
    # int, float, int- & float-derived Enums  number
    # True                                    true
    # False                                   false
    # None                                    null
    
    # NOTE:
    
    # Built-in Python types -> numpy types	
    # Several python types are equivalent to a corresponding array scalar when 
    # used to generate a dtype object:
    #
    # int             np.int_       WARNING: np.int_ DEPRECATED for Python int; 
    #                               use np.dtype(int) directly
    # bool            np.bool_
    # float           np.float_
    # complex         np.cfloat
    # bytes           np.bytes_
    # str             np.str_ (a.k.a np.unicode_)
    # buffer          np.void
    # (all others)    np.object_    WARNING np.object_ DEPRECATED for the Python
    #                               'object' builtin;
    #                               use dtype(object) directly

    # NOTE: structured dtypes (for structured arrays):
    # Specified as 
    # 1) A list of tuples (fieldname, datatype, < shape >) one tuple per field:
    #
    #       fieldname: str or tuple of str (name, title)
    #           When empty str ('') will be assigned by numpy to f# where # is 
    #           the running index of the field (f2 for field 2 etc)
    #
    #       datatype: any object convertible to a datatype, including shorthand
    #               str (a.k.a array-protocol type strings, see below)
    #
    #       shape is optional: tuple of intergers (shape of the field)
    #
    # 2) A list of comma-separated dtype specifications:
    #
    # e.g.:
    #
    # >>> np.dtype('i8, f4, S3')
    #  dtype([('f0', '<i8'), ('f1', '<f4'), ('f2', 'S3')])
    # >>> np.dtype('3int8, float32, (2, 3)float64')
    #
    #  dtype([('f0', 'i1', (3,)), ('f1', '<f4'), ('f2', '<f8', (2, 3))])
    # 
    # 3) A dictionary of field parameter arrays
    #
    # The dictionary has two required keys, ‘names’ and ‘formats’, and four 
    # optional keys, ‘offsets’, ‘itemsize’, ‘aligned’ and ‘titles’. 
    #
    #
    # The values for ‘names’ and ‘formats’ should respectively be a list of field 
    # names and a list of dtype specifications, of the same length. 
    #
    # The optional ‘offsets’ value should be a list of integer byte-offsets, 
    # one for each field within the structure. If ‘offsets’ is not given the 
    # offsets are determined automatically. 
    #
    # The optional ‘itemsize’ value should be an integer describing the total size 
    # in bytes of the dtype, which must be large enough to contain all the fields. 
    #
    # e.g.:
    # >>> np.dtype({'names': ['col1', 'col2'], 'formats': ['i4', 'f4']})
    #  dtype([('col1', '<i4'), ('col2', '<f4')])
    #
    # >>> np.dtype({'names': ['col1', 'col2'],
    # ...           'formats': ['i4', 'f4'],
    # ...           'offsets': [0, 4],
    # ...           'itemsize': 12})
    #  dtype({'names':['col1','col2'], 'formats':['<i4','<f4'], 'offsets':[0,4], 'itemsize':12})
    #
    # The optional ‘aligned’ value can be set to True to make the automatic offset 
    # computation use aligned offsets 
    #
    # 4) A dictionary of field names (discouraged). 
    # The keys of the dictionary are the field names and the values are tuples 
    # specifying type and offset:
    #
    # >>> np.dtype({'col1': ('i1', 0), 'col2': ('f4', 1)})
    #  dtype([('col1', 'i1'), ('col2', '<f4')])    
    #
    #
    
    # NOTE: Array-protocol type strings (shorthand strings) for numpy datatypes:
    # 
    # character 0 is the type letter, followed by digits (item size or number of
    # chars):
    #
    # The first character specifies the kind of data and the remaining characters 
    # specify the number of bytes per item, except for Unicode, where it is 
    # interpreted as the number of characters. The item size must correspond to
    # an existing type, or an error will be raised. 
    #
    # The supported kinds are	
    # '?'       boolean
    # 'b'       (signed) byte
    # 'B'       unsigned byte
    # 'i'       (signed) integer
    # 'u'       unsigned integer
    # 'f'       floating-point
    # 'c'       complex-floating point
    # 'm'       timedelta
    # 'M'       datetime
    # 'O'       (Python) objects
    # 'S','a'   zero-terminated bytes (not recommended)
    # 'U'       Unicode string
    # 'V'       raw data (void)
    #
    # Examples:
    # dt = np.dtype('i4')   # 32-bit signed integer
    # dt = np.dtype('f8')   # 64-bit floating-point number
    # dt = np.dtype('c16')  # 128-bit complex floating-point number
    # dt = np.dtype('a25')  # 25-length zero-terminated bytes
    # dt = np.dtype('U25')  # 25-character string

    def default(self, obj):
        from imaging import vigrautils as vu
        from core import prog
        from core.datatypes import is_namedtuple
        
        #if any(hasattr(obj,name) for name in ("toJSON", "to_json", "write_json", "writeJSON")):
            #raise NotImplementedError(f"The {type(obj).__name__} object appears capable to write itself to JSON and is not supported here")
        
        if isinstance(obj, complex):
            
            return {type(obj).__name__: {"__init__":,
                                         "__module__": type(obj).__module__,
                                         "__value__": [obj.real, obj.imag]}}
            #return {"__complex__", {"__value__":[obj.real, obj.imag]}}
        
        if isinstance(obj, type):
            return {type(obj).__name__: {"__module__": type(obj).__module__,
                                         "__value__": f"{obj.__module__}.{obj.__name__}"}}
            #return {"__type__": {"__value__": f"{obj.__module__}.{obj.__name__}"}}
        
        if is_namedtuple(obj):
            fields = ", ".join([f"'{field}'" for f in obj._fields])
            return {".".join([type(obj).__module__, type(obj).__name__]):
                        {"__init__": "".join(["collections.namedtuple(", f"'{type(obj).__name__}', ", "(", fields, "))"]),
                         "__module__": tyoe(obj).__module__,
                         "__value__":obj,
                         "fields": fields}}
        
        if isinstance(obj, vigra.filters.Kernel1D):
            xy = vu.kernel2array(obj, True)
            return {"__kernel1D__": {"__value__":xy.toList()}}
        
        if isinstance(obj, vigra.filters.Kernel2D):
            xy = vu.kernel2array(obj, True)
            return {"__kernel2D__": {"__value__":xy.toList()}}
        
        if isinstance(obj, prog.SignatureDict):
            return {".".join([type(obj).__module__, type(obj).__qualname__]): {"__value__": obj.__dict__}}
        
        if isinstance(obj, np.ndarray):
            # NOTE: 2021-11-16 16:21:24
            # this includes numpy chararray (usually created as a 'view'
            # of a numpy array with string dtypes)
            # for strings it is recommended to create numpy arrays with
            # np.unicode_ as dtype
            fields = obj.dtype.fields   # mapping proxy for numpy structured 
                                        # arrays and recarrays, 
                                        # None for regular arrays
                                        
            if fields is not None: # structured array or recarray
                if obj.dtype.name.startswith("record"): # recarray
                    entry = "__recarray__"
                else:
                    entry = "__structarray__"
                    
            elif isinstance(obj, np.chararray):
                entry = "__chararray__"
                
            elif isinstance(obj, pq.Quantity):
                if isinstance(obj, pq.UnitQuantity):
                    entry = "__unitquantity__"
                else:
                    entry = "__quantityarray__"
                    
            elif isinstance(obj, vigra.VigraArray): # CAUTION NOT FOR DAY-TO-DAY USE
                entry = "__vigraarray__"
                
            else:
                entry = "__numpyarray__"
                
            if isinstance(obj, pq.Quantity):
                if isinstance(obj, pq.UnitQuantity):
                    return {entry: {"__value__": obj.dimensionality.string}}
                else:
                    return {entry: {"__value__": obj.magnitude.tolist(), 
                                    "__units__": obj.units.dimensionality.string,
                                    "__dtype__": dtype2json(obj.dtype)}}
                
            elif isinstance(obj, vigra.VigraArray):
                return {entry: {"__value__": obj.tolist(),
                                "__dtype__": dtype2json(obj.dtype),
                                "__axistags__":obj.axistags.toJSON(),
                                "__order__": obj.order}}
            
            elif isinstance(obj, vigra.AxisTags):
                return {"__axistags__": {"__value__": obj.toJSON()}}
            
            else:
                return {entry: {"__value__": obj.tolist(),
                                "__dtype__": dtype2json(obj.dtype)}}
            
        elif isinstance(obj, np.dtype):
            return {"__dtype__": {"__value__": str(obj)}}
        
        elif pd.api.types.is_extension_array_dtype(obj):
            return dtype2json(obj)
        
        elif isinstance(obj, (pd.DataFrame, pd.Index, pd.Series)):
            raise NotImplementedError(f"{type(obj).__name__} objects are not supported")
        
        elif isinstance(obj, pd.Interval):
            return {type(obj).__name__:{"__init__":f"{type(obj).__name__}(left={obj.left}, right={obj.right}, closed={obj.closed})",
                                        "__ns__": "pd",
                                        "left": obj.left,
                                        "right": obj.right,
                                        "closed": obj.closed}}
        
        # TODO: pd.Period, pd.Timestamp
            
        return json.JSONEncoder.default(self, obj)
    
def dtype2json(d:np.dtype) -> typing.Union[str, dict]:
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
    
    #print("dtype2json", d)
    
    h5pyjson = h5pydtype2json(d)
    
    if h5pyjson is not None:
        return h5pyjson
    
    pandasjson = pandasdtype2json(d)
    if pandasjson is not None:
        return pandasjson
    
    fields = d.fields
    
    if d.name.startswith("record"):
        return dict((name, (dtype2json(value[0]), value[1])) for name, value in d.fields.items())
        
    else:   
        if fields is None:
            return np.lib.format.dtype_to_descr(d) #does not perform well for structured arrays?
        else:
            return d.name
    
def h5pydtype2json(d):
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
            
def pandasdtype2json(d):
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
                             "dtype": dtype2json(categories_dtype),
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
                typename = components[-1]
                modname = ".".join(components[:-1])
                #print("modname", modname, "typename", typename)
                module = sys.modules[modname]
                return eval(typename, module.__dict__)
            else:
                return eval(typename) # fingers crossed...
            
        else:
            return dct
    else:
        return dct
    
        #try:
                
            #if key.startswith("__main__"):
                #typeobj = eval(dct[typename]["class"])
            #else:
                #typeobj = eval(key)
                
            #if is_namedtuple(typeobj):
                #return typeobj(*val)
                
            #return typeobj(val)
            
        #except:
            #if key == "__complex__":
                #if isinstance(val, (tuple, list)) and len(val) == 2:
                    #return complex(*val)
                
                #elif isinstance(val, dict) and all(k in val for k in ("real", "imag")):
                    #return complex(val["real"], val["imag"])
                
                #else:
                    #return val
                
            #elif key == "__unitquantity__":
                #return cq.unit_quantity_from_name_or_symbol(val)
            
            #elif key.endswith("SignatureDict"):
                #return prog.SignatureDict(**val)
            
            ##elif any(e.endswith("array__") for e in dct):
            #elif key.endswith("array__"):
                #entry = list(dct.keys())[0]
                #val = dct[entry]
                #if key in ("__structarray__", "__recarray__"):
                    #value = list(tuple(x) for x in val)
                #else:
                    #value = val["__value__"]
                    
                #if key == "__recarray__":
                    #dtype = json2dtype(dict((name, (json2dtype(value[0]), value[1])) for name, value in data["__dtype__"].items()))
                #else:
                    #dtype = json2dtype(data["__dtype__"])
                
                #ret = np.array(value, dtype=dtype)
                
                #if key in ("__chararray__", "__recarray__"):
                    #artype = eval(key.replace("__", ""), np.__dict__)
                    #return ret.view(artype)
                
                #if key == "__quantityarray__":
                    #units = cq.unit_quantity_from_name_or_symbol(data["__units__"])
                    #return ret * units
                
                #if entry == "__vigraarray__":
                    #return vigra.VigraArray(ret, axistags=vigra.AxisTags.fromJSON(data["__axistags__"]), 
                                        #order=data.get("__order__", None))
                    
                #return ret
            
            #elif key == "__kernel1D__":
                #xy = np.array(val)
                #left = int(xy[0,0])
                #right = int(xy[-1,0])
                #values = xy[:,1]
                #ret = vigra.filters.Kernel1D()
                #ret.initExplicitly(left, right, values)
                #return ret
            
            #elif key == "__kernel2D__":
                #xy = np.array(val)
                #upperLeft = (int(xy[-1,-1,0]), int(xy[-1,-1,1]))
                #lowerRight = (int(xy[0,0,0]), int(xy[0,0,1]))
                #values = xy[:,:,]
                #ret = vigra.filters.Kernel2D()
                #ret.initExplicitly(upperLeft, lowerRight, values)
                #return ret
            
            #elif key == "__type__":
                ##print("val", val)
                #if "." in val:
                    #components = val.split(".")
                    #typename = components[-1]
                    #modname = ".".join(components[:-1])
                    ##print("modname", modname, "typename", typename)
                    #module = sys.modules[modname]
                    #return eval(typename, module.__dict__)
                #else:
                    #return eval(typename) # fingers crossed...
                
            
def dumps(obj, *args, **kwargs):
    kwargs["cls"] = CustomEncoder
    return json.dumps(obj, *args, **kwargs)

def loads(s, *args, **kwargs):
    kwargs["object_hook"] = decode_hook
    return json.loads(s, *args, **kwargs)

def dump(obj, fp, *args, **kwargs):
    kwargs["cls"] = CustomEncoder
    json.dump(obj,fp, *args, **kwargs)
    
def load(fp, *args, **kwargs):
    kwargs["object_hook"] = decode_hook
    return json.load(fp, *args, **kwargs)


    
