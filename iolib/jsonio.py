"""JSON codecs
"""

import json, sys, traceback, typing
import numpy as np
import quantities as pq
import vigra
from core import quantities as cq

class CustomEncoder(json.JSONEncoder):
    """Almost complete round trip for a subset of Python types - read side.
    
    Implemented types:
    type
    complex
    UnitQuantity
    Quantity
    numpy chararray, structured array, recarray and ndarray (with caveats, 
    see below)
    
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
        if isinstance(obj, complex):
            return {"__complex__", [obj.real, obj.imag]}
        
        if isinstance(obj, type):
            return {"__type__": f"{obj.__module__}.{obj.__name__}"}
        
        #if isinstance(obj, pq.Quantity):
            #if isinstance(obj, pq.UnitQuantity):
                #return {"__unitquantity__": obj.dimensionality.string}

            #return {"__quantity__": {"value": obj.magnitude.tolist(), 
                                     #"units": obj.units.dimensionality.string,
                                     #"dtype": dtype2json(obj.dtype)}
                    #}
            
        if isinstance(obj, np.ndarray):
            # NOTE: 2021-11-16 16:21:24
            # this includes numpy chararray (usually created as a 'view'
            # of a numpy array with string dtypes)
            # for strings it is recommended to create numpy arrays with
            # np.unicode_ as dtype
            fields = obj.dtype.fields   # mapping proxy for numpy structured 
                                        # arrays and recarrays, 
                                        # None for regular arrays
                                        
            if fields is not None:
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
                
            #return {entry: {"value": obj.tolist(),
                            #"dtype": dtype2json(obj.dtype)}}
            
            if isinstance(obj, pq.Quantity):
                if isinstance(obj.UnitQuantity):
                    return {entry: obj.dimensionality.string}
                else:
                    return {entry: {"value": obj.magnitude.tolist(), 
                                    "units": obj.units.dimensionality.string,
                                    "dtype": dtype2json(obj.dtype)}}
                
            elif isinstance(obj, vigra.VigraArray):
                return {entry: {"value": obj.tolist(),
                                "dtype": dtype2json(obj.dtype),
                                "axistags":obj.axistags.toJSON(),
                                "order": obj.order}}
            
            else:
                return {entry: {"value": obj.tolist(),
                                "dtype": dtype2json(obj.dtype)}}
                
                
            #if fields is not None:
                #if obj.dtype.name.startswith("record"): # recarray
                    #return  {"__recarray__": {"value": obj.tolist(),
                                              #"dtype":dtype2json(obj.dtype)}
                            #}
                #else:
                    #return  {"__structarray__": {"value": obj.tolist(),
                                                 #"dtype":dtype2json(obj.dtype, True)}
                            #}
                    
            #else:
                #if isinstance(obj, np.chararray):
                    #return {"__chararray__": {"value": obj.tolist(), 
                                        #"dtype": dtype2json(obj.dtype)}
                            #}
                #else:
                    #return {"__numpyarray__": {"value": obj.tolist(), 
                                        #"dtype": dtype2json(obj.dtype)}
                            #}
        
        return json.JSONEncoder.default(self, obj)
    
def dtype2json(d:np.dtype, struct:bool=False) -> typing.Union[str, dict]:
    """Roundtrip numpy dtype - json string format - write side
    An alternative to the np.lib.format.dtype_to_descr
    Returns a dict for recarray dtypes; a str in any other case.
    """
    if not isinstance(d, np.dtype):
        raise TypeError(f"Expecting a numpy dtype instance; got {type(d).__name__} instead")
    
    if d.name.startswith("record"):
        return dict((name, (dtype2json(value[0]), value[1])) for name, value in d.fields.items())
        
    else:   
        if struct:
            return str(d)
        return np.lib.format.dtype_to_descr(d) #does not perform well for strutured arrays?
    
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
                #try:
                    #return np.lib.format.descr_to_dtype(s)
                #except:
                    #raise
                
    elif isinstance(s, dict): # for recarrays
        return np.dtype(s) 

def decode_hook(dct):
    """ Almost complete round trip for a subset of Python types - read side.
    
    Implemented types:
    type
    complex
    UnitQuantity
    Quantity
    numpy chararray, structured array, recarray and ndarray (with caveats, see
    documentation for CustomEncoder in ths module)
    
    Pass this as the 'object_hook' parameter to json.load & json.loads (this is
    what the load and loads functions in this module do).
    
    Use it whenever the json was dumped using the CustomEncoder :class: (defined
    in this module) as 'cls' parameter.
    """
    if len(dct) == 1: # only work on dict with a single entry here
        if "__complex__" in dct:
            val = dct["__complex__"]
            if isinstance(val, (tuple, list)) and len(val) == 2:
                return complex(val[0], val[1])
            
            elif isinstance(val, dict) and all(k in val for k in ("real", "imag")):
                return complex(val["real"], val["imag"])
            
            else:
                return val
            
        elif "__unitquantity__" in dct:
            val = dct["__unitquantity__"]
            return cq.unit_quantity_from_name_or_symbol(val)
        
        #elif "__quantity__" in dct:
            #val = dct["__quantity__"]
            #magnitude = np.array(val["value"], dtype = json2dtype(val["dtype"]))
            #units = cq.unit_quantity_from_name_or_symbol(val["units"])
            #return magnitude * units
        
        elif any(e.endswith("array__") for e in dct):
            entry = list(dct.keys())[0]
            val = dct[entry]
            if entry in ("__structarray__", "__recarray__"):
                value = list(tuple(x) for x in val["value"])
            else:
                value = val["value"]
                
            if entry == "__recarray__":
                dtype = json2dtype(dict((name, (json2dtype(value[0]), value[1])) for name, value in val["dtype"].items()))
            else:
                dtype = json2dtype(val["dtype"])
            
            ret = np.array(value, dtype=dtype)
            
            if entry in ("__chararray__", "__recarray__"):
                artype = eval(entry.replace("__", ""), np.__dict__)
                return ret.view(artype)
            
            if entry == "__quantityarray__":
                units = cq.unit_quantity_from_name_or_symbol(val["units"])
                return ret * units
            
            if entry == "__vigraarray__":
                return vigra.VigraArray(ret, axistags=vigra.AxisTags.fromJSON(val["axistags"]), 
                                       order=val.get("order", None))
                
            return ret
        
        elif "__type__" in dct:
            val = dct["__type__"]
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


    
