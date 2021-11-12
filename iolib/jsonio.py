"""JSON codecs
"""

import json, sys, traceback
import numpy as np
import quantities as pq
from core import quantities as cq

class CustomEncoder(json.JSONEncoder):
    """Pass as the 'cls' parameter to json.dump & json.dumps
    NOTE: This does NOT affect custom types that use their own encoding
    (e.g. vigra.AxisTags' toJSON() and fromJSON())
    """
    def default(self, obj):
        if isinstance(obj, complex):
            return {"__complex__", [obj.real, obj.imag]}
        
        if isinstance(obj, type):
            return {"__type__": f"{obj.__module__}.{obj.__name__}"}
        
        if isinstance(obj, pq.Quantity):
            if isinstance(obj, pq.UnitQuantity):
                return {"__unitquantity__": obj.dimensionality.string}

            return {"__quantity__": {"value": obj.magnitude.tolist(), 
                                     "units": obj.units.dimensionality.string,
                                     "dtype": obj.dtype.name}
                    }
            
        if isinstance(obj,np.ndarray):
            return {"__numpy__": {"value": obj.tolist(), 
                                  "dtype": obj.dtype.name}
                    }
        
        return json.JSONEncoder.default(self, obj)
    
def decode_hook(dct):
    """ pass this as the 'object_hook' parameter to json.load & json.loads
    Use it whenever the json was dumped using the CustomEncoder :class: (defined
    in this module) as 'cls' parameter.
    """
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
            
    
    elif "__quantity__" in dct:
        val = dct["__quantity__"]
        magnitude = np.array(val["value"], dtype = val["dtype"])
        #return pq.Quantity(magnitude, val["units"], dtype)
        units = cq.unit_quantity_from_name_or_symbol(val["units"])
        return magnitude * units
        
    elif "__numpy__" in dct:
        val = dct["__numpy__"]
        data = np.ndarray(val["value"], dtype = dtype(val["dtype"]))
            
    elif "__type__" in dct:
        val = dct["__type__"]
        print("val", val)
        if "." in val:
            components = val.split(".")
            typename = components[-1]
            modname = ".".join(components[:-1])
            print("modname", modname, "typename", typename)
            module = sys.modules[modname]
            return eval(typename, module.__dict__)
        else:
            return eval(typename) # fingers crossed...
            
    else:
        return dct
            
