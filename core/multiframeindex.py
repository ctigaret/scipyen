import os, typing
from functools import partial
from collections import namedtuple
import collections.abc
from inspect import (getmembers, getattr_static)
from core.prog import (ArgumentError, OneOf, TypeValidator, GenericValidator,
                       get_descriptors, get_properties,
                       parse_descriptor_specification,
                       WithDescriptors, setup_descriptor)

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

#MultiFrameIndex = namedtuple("MultiFrameIndex", ("scene", "scans", "electrophysiology") module = __module_name__)
    
class MultiFrameIndex(WithDescriptors):
    """Maps a virtual data frame index to frame indices into its compoents
    """
        
    #@classmethod
    #def setup_descriptor(cls, descr_params):
        #args = descr_params.get("args", tuple())
        #kwargs = descr_params.get("kwargs", {})
        #name = descr_params.get("name", "")
        ##print(f"setting up {name} with {descr_params}")
        #if not isinstance(name, str) or len(name.strip()) == 0:
            #return
        #descriptor = GenericValidator(*args, **kwargs)
        #descriptor.allow_none = True
        #descriptor.__set_name__(cls, name)
        ##print(descriptor.private_name)
        #setattr(cls, name, descriptor)
        
    def __init__(self, *fields, **field_map):
        #super(WithDescriptors, self).__init__()
        for field in fields:
            if not isinstance(field, str) or len(field.strip()) == 0:
                raise TypeError(f"A field must be a non-empty string; got {field} instead")
            type(self).setup_descriptor({"name": field, "args": ((int, collections.abc.Sequence), int), "kwargs":{}})
            # NOTE: 2021-11-30 17:36:12
            # this MUST be called otherwise no attribute will be added to the instance
            # (this calls descriptor's __set__ function which does just that)
            setattr(self, name, None)
            
        for field, value in field_map.items():
            if not isinstance(field, str) or len(field.strip()) == 0:
                raise TypeError(f"A field must be a non-empty string; got {field} instead")
            
            type(self).setup_descriptor({"name": field, "args": ((int, collections.abc.Sequence), int), "kwargs":{}})
            setattr(self, field, value)
              
    def __str__(self):
        properties = get_properties(type(self))
        ret = list()
        for p in properties:
            ret.append(f"{p} = {getattr(self, p)}")
            
        return "\n".join(ret)
    
    def fields(self):
        return get_properties(self)
    
    def addField(self, name:typing.Optional[str] = None, value:typing.Optional[typing.Any]=None):
        if not isinstance(name, str) or len(name.strip()) == 0:
            return
        
        type(self).setup_descriptor({"name": name, "args":((int, collections.abc.Sequence), int), "kwargs":{}})
        # NOTE: see NOTE: 2021-11-30 17:36:12
        setattr(self, name, value) 
        
    
