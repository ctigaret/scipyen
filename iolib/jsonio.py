"""JSON codecs
"""

import json, sys, traceback, typing, collections
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
from core.prog import classify_signature

#class ObjectDescription(object):
    #"""Standardized object description for non-JSON-able objects
    #Attributes:
    #typename: object type name
    #typemodule: module where object type is defined
    #init: mapping: obj.__init__ signature
    #new: mapping: obj.__new__ signature
    #value: obj (instance of typename) or None
    
    #"""
    
    #def __init__(self, obj):
        #self._json_ = dict()
        #self._json_.update(self._makeStub_(obj))
        #self._init_func_ = self._obj_init_(obj)
        #self._new_func_ = classify_signature(obj.__new__)
        #self._makeJSON_(obj)
        ##try:
            ##self._json_ = json.JSONEncoder.default(self, obj)
        ##except TypeError as e:
        
    #def _makeStub_(self, o):
        #ret = {"__obj_type__": type(o).__qualname__,
               #"__obj_module__": type(o).__module__}
        
        #if isinstance(o, type):
            #ret.update({"__type_name__": o.__qualname__,
                        #"__type_module__": o.__module__})
            
        #else:
            #ret.update({"__type_name__":type(o).__qualname__,
                        #"__type_module__": type(o).__module__})
            
        #ret["__special__"] = None
        #ret["__args__"] = tuple()
        #ret["__kwargs__"] = dict()
        #ret["__value__"] = None
        
        #return ret
    
            
    #@singledispatchmethod
    #def _obj_init_(self, o):
        #init_sig = classify_signature(o.__init__)
        
    #@_obj_init_.register(complex)
    #def _(self, o:complex):
        #args = self._obj_init_args_(o)
        #return f"complex{args}"
    
    ## NOTE: str represent themselves
    
    #@_obj_init_.register(tuple)
    #@_obj_init_.register(list)
    #def _(self, o:typing.Union[tuple, list]):
        #if hasattr(o, "_fields"):
            #fields = ",".join([f"'{f}'" for f in o._fields])
            #args = tuple(getattr(o, f) for f in o._fields)
            #if self.typemodule == "__main__":
                #klassdef = f"collections.namedtuple('{type(o).__name__}', ({fields}))"
                #return f"eval('''{klassdef}'''){args}"
            #return f"{type(o).__module__}.{type(o).__name__}(*{args})"
        
        
    #@_obj_init_.register(collections.deque)
    #def _(self, o:collections.deque):
        #args=tuple(o)
        #maxlen = o.maxlen
        #klassdef = ".".join((self.typemodule, self.typename))
        #return "eval('''{klassdef}''')({args}, {maxlen})".format(klassdef=klassdef, args=args, maxlen=maxlen)
        
    #@singledispatchmethod
    #def _obj_init_args_(self, o):
        #return o
    
    #@_obj_init_args_.register(complex)
    #def _(self, o:complex):
        #return (o.real, o.imag)
    
    #@_obj_init_args_.register(type)
    #def _(self, o:type):
        #return ".".join((o.__module__, o.__name__))
    
    #@_obj_init_args_.register(tuple)
    #def _(self, o:tuple):
        #if hasattr(o, "_fields"): # named tuple
            #return tuple(getattr(o, field) for field in o._fields)
        
        #return o
    
    #@property
    #def typename(self):
        #return self._typename_
    
    #@property
    #def typemodule(self):
        #return self._typemodule_
    
    #@property
    #def init(self):
        #return self._init_func_
    
    #@property
    #def new(self):
        #return self._new_func_
    
    ##@property
    ##def value(self):
        ##return self._value_
    
    ##@property
    ##def attributes(self):
        ##return self._attributes_
    
    ##@property
    ##def value(self):
        ##return self._value_
    
    #@property
    #def object(self):
        #klass = import_item(".".join((self.typemodule, self.typename)))
        #return klass(*self._args_, **self._kwargs_)
    
class CustomEncoder(json.JSONEncoder):
    """Almost complete round trip for a subset of Python types - encoding side.
    
    To decode decode_hook() module function as counterpart for reading json
    
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
    While this can be used to encode SMALL numpy arrays (including recarrays,
    structured arrays and chararrays) this is NOT recommended for storing
    large arays and arrays of complex types.
    
    NOTE: general schema:
    
    {"__python_object__":{
        "__obj_type__": str, name of the object's type,
        
        "__obj_module__": str, the name of the module where object type is defined
        
        "__type_name__": str; for type objects, the name of the object 
                                (obj.'__name__');
                                
                              for instances, same value as __obj_type__
                              
        "__type_module__": str: for type objects, the name of the module where 
                                the object (a type) is defined;
                                
                                for instances, same value as __obj_module__
                                
        "__args__": tuple; parameters for object intialization, or empty tuple
        
        "__kwargs__": dict; keyword parameters for object initialization, or 
                            empty dict
                            
        "__subtype__": None or the str "__structarray__" (for numpy structarrays)
        
        "__dtype__": str; representation of the numpy dtye, or json representation
                        of a specialized dtype (such as h5py special dtypes, or 
                        pandas extension dtypes)
                        
        "__value__": str: JSON representation of the value, or None (a.k.a null)
                            this is usually the JSON representation for objects of
                            basic Python types that can be directly serializable
                            in JSON using Python's stock 'json' module.
                            
        
        
        }
    }
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

    def _makeStub_(self, o):
        if isinstance(o, type):
            ret = {"__python_type__":{"__type_name__": o.__qualname__,
                                      "__type_module__": o.__module__}}
        elif inspect.isfunction(o):
            ret = {"__python_function__": dict(prog.classify_signature(o))}
                                             
        elif inspect.ismethod(o):
            # NOTE/TODO: 2021-12-18 22:26:27
            # can I differentiate between class method and instance method?
            ret = {"__python_method__": dict(prog.classify_signature(o))}
                                             
        else:
            ret = {"__python_object__":{"__obj_type__": type(o).__qualname__,
                                        "__obj_module__": type(o).__module__,
                                        "__args__": tuple(),
                                        "__named__":dict(),
                                        "__kwargs__": dict(),
                                        "__value__": None,
                                        "__subtype__": None,
                                        "__dtype__": None,
                                        }
                  }
        
        return ret
    
    @singledispatchmethod
    def _makeJSON_(self, o):
        """General case for all types supported by Python's own json module
        """
        ret = self._make_stub_(o)
        ret["__value__"] = json.JSONEncoder.default(self, o)
    
    @_makeJSON_.register(complex)
    def _(self, o:complex):
        ret = self._make_stub_(o)
        ret["__args__"] = (o.real, o.imag)
        
    @_makeJSON_.register(vigra.filters.Kernel1D)
    def _(self, o:vigra.filters.Kernel1D):
        import vigrautils as vu
        xy = vu.kernel2array(obj, True)
        self._json_["__args__"] = xy
        
    def default(self, obj):
        # NOTE: 2021-12-17 22:59:34
        # 1) I need to generate something simple, yet with enough information to 
        #   reconstruct the object being encoded
        #
        # 2) It seems natural that the object should be encoded as a mapping of
        #   str keys to str values (i.e., a dict, itself encoded as a JSON 
        #   'object');
        #
        # 3) The main caveat of point (2) is that the output falls under the 
        #   umbrella of dicts: how to distinguish a dict that encodes a Python 
        #   object that is not serializable in Python, from any other dict?
        #
        # 4) Pandas seems to rely on generating a nested dict (with columns the
        #   highest level): 
        #
        #   {column0: JSON-representation of the Series of column 0, etc}
        #
        #   where each Series is a dict mapping index elements to Series element
        #   however, this has its own limtations, including:
        #       it fails when the dataframe or series index is NOT unique and 
        #       'orient' is 'columns' or 'index'
        #
        #       the JSON output needs to be decoded using Pandas.read_json, 
        #       which does not decode IntervalDtype (and possibly other Pandas 
        #       extension dtypes)
        #
        # 5) a workaround might be to generate a pickle (as a string) - but this
        #   is too volatile
        #
        #
        # 6) a better (?) workaround is to generate a dict with a single key
        #   '__python_object__' mapped to a dict with a set of specific keys:
        #
        #       __obj_type__
        #       __obj_module__
        #       __args__
        #       __kwargs__
        #
        #   for numpy arrays (and derived) this should also include:
        #       __fields__ for structured arrays
        #       __axistags__ for vigra arrays
        #       __units__  for python quantity arrays - CAUTION these can have ndim==0
        #
        #   for more specialized numpy arrays: neo data objects, neo containers
        #      
        #       
        #   pandas objects
        #
        # 7) for base Python objects that CAN be serialized with JSON (i.e. of 
        #   types supported by Python's json module) return their JSON 
        #   representation
        #
        from imaging import vigrautils as vu
        from core import prog
        from core.datatypes import is_namedtuple
        
        #if any(hasattr(obj,name) for name in ("toJSON", "to_json", "write_json", "writeJSON")):
            #raise NotImplementedError(f"The {type(obj).__name__} object appears capable to write itself to JSON and is not supported here")
        
        if isinstance(obj, complex):
            #return {type(obj).__name__: {"__module__": type(obj).__module__,
                                         #"__value__": [obj.real, obj.imag]}}
            #return {"__complex__", {"__value__":[obj.real, obj.imag]}}
            #return {type(obj).__name__, {"__value__":[obj.real, obj.imag]}}
        
            return {"__python_object__": {"__obj_type__": type(obj).__qualname__,
                                          "__obj_module__": type(obj).__module__,
                                          "__type_name__": type(obj).__qualname__,
                                          "__type_module__": type(obj).__module__,
                                          "__args__": (obj.real, obj.imag),
                                          "__kwargs__": None}}
        
        if isinstance(obj, type):
            # NOTE: for type objects __obj_module__ should indicate where the
            # type objects itself has been defined, NOT the module of the 'type'
            # ancestor (which is always 'builtins')
            
            return {"__python_object__":{"__obj_type__": type(obj).__name__,
                                         "__obj_module__": type(obj).__module__,
                                         "__type_name__": obj.__name__,
                                         "__type_module__": obj.__module__,
                                         "__args__": None, 
                                         "__kwargs__": None}}
        
            #return {type(obj).__name__: {"__module__": type(obj).__module__,
                                         #"__value__": f"{obj.__module__}.{obj.__name__}"}}
            #return {"__type__": {"__value__": f"{obj.__module__}.{obj.__name__}"}}
        
        if is_namedtuple(obj):
            fields = ", ".join([f"'{field}'" for f in obj._fields])
            return {".".join([type(obj).__module__, type(obj).__name__]):
                        {"__init__": "".join(["collections.namedtuple(", f"'{type(obj).__name__}', ", "(", fields, "))"]),
                         "__module__": type(obj).__module__,
                         "__value__":obj,
                         "fields": fields}}
        
        if isinstance(obj, vigra.filters.Kernel1D):
            xy = vu.kernel2array(obj, True)
            return {"__kernel1D__": {"__value__":xy.toList()}}
        
        if isinstance(obj, vigra.filters.Kernel2D):
            xy = vu.kernel2array(obj, True)
            return {"__kernel2D__": {"__value__":xy.toList()}}
        
        #if isinstance(obj, prog.SignatureDict):
            #return {".".join([type(obj).__module__, type(obj).__qualname__]): {"__value__": obj.__dict__}}
        
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
    
    @staticmethod
    def decode_hook(dct):
        if len(dct) == 1: # only work on dict with a single entry here
            key = list(dct.keys())[0]
            data = dct[key]
            if data is None or not isinstance(data, dict):
                return dct
            #print("data", data)
            val = data.get("__value__", None) # may be a dict, see below for *array__

            if val is None:
                module = data.get("__obj_module__", "builtins")
                return dct
            
            if key == "__python_type__":
                rep = ".".join([data["__type_module__"], data["__type_name__"]])
                
                return import_item(rep)
            
            elif key == "__python_function__":
                rep = ".".join(data["module"], data["qualname"])
                
                return import_item(rep)
            
            elif key == "__python_method__":
                name = data["name"]
                qualname = data["qualname"]
                owner = import_item("."join(qualname.strip(".")[:-1]))
                return getattr(owner, name)
            
            elif key == "__python_object__":
                if data["__value__"] is not None:
                    return data["__value__"]
                
                obj_type_spec = data["__obj_type__"] if data["__obj_module__"] == "builtins" else ".".join([data["__obj_module__"], data["__obj_type__"]])
                
                obj_type = import_item(obj_type_spec)
                
                
                    
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


    
