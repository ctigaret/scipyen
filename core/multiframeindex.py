from functools import partial
from inspect import getmembers, getattr_static
from core.prog import get_properties
    
class MultiFrameIndex(object):
    """Maps a virtual data frame index to frame indices into its compoents
    """
    @staticmethod
    def __getter__(obj, name:str):
        return getattr(obj, name)

    @staticmethod
    def __setter__(obj, value, name:str):
        if not isinstance(value, int):
            raise TypeError(f"Expecting an int; got {type(value).__name__} instead")
        setattr(obj, name, value)
        
    def __init__(self, *fields, **field_map):
        for field in fields:
            if not isinstance(field, str) or len(field.strip()) == 0:
                raise TypeError(f"A field must be a non-empty string; got {field} instead")
            obj_attr_name = f"_{field}_"
            setattr(self, obj_attr_name, None)
            getter_func = partial(MultiFrameIndex.__getter__, name = obj_attr_name)
            setter_func = partial(MultiFrameIndex.__setter__, name = obj_attr_name)
            
            setattr(type(self), field, property(getter_func, setter_func))
            
            
        for field, value in field_map.items():
            if not isinstance(field, str) or len(field.strip()) == 0:
                raise TypeError(f"A field must be a non-empty string; got {field} instead")
            if not isinstance(value, (int, type(None))):
                raise TypeError(f"A field value must be an int or None; got {type(value).__name__} instead")
                
            obj_attr_name = f"_{field}_"
            if not hasattr(type(self), obj_attr_name):
                setattr(self, obj_attr_name, value)
            
            if not isinstance(getattr_static(type(self), field, None), property):
                getter_func = partial(MultiFrameIndex.__getter__, name = obj_attr_name)
                setter_func = partial(MultiFrameIndex.__setter__, name = obj_attr_name)
                setattr(type(self), field, property(getter_func, setter_func))
              
    def __str__(self):
        properties = get_properties(type(self))
        ret = list()
        for p in properties:
            ret.append(f"{p} = {getattr(self, p)}")
            
        return "\n".join(ret)
    
    def fields(self):
        return get_properties(type(self))
    
    def _repr_pretty_(self, p, cycle):
        p.text(self.__class__.__name__)
        p.breakable()
        properties = get_properties(type(self))
        first = True
        for pr in properties:
            value = getattr(self, pr)
            if first:
                first = False
            else:
                p.breakable()
                
            with p.group(indent=-1):
                p.text(f"{pr}:")
                p.pretty(value)
                
        
    
