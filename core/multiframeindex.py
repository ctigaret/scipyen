import os, typing, types
from functools import partial
from collections import namedtuple
import collections.abc
from inspect import (getmembers, getattr_static)
from core.prog import (ArgumentError, OneOf, TypeValidator, GenericValidator,
                       get_descriptors, get_properties,
                       parse_descriptor_specification,
                       WithDescriptors, setup_descriptor,
                       classify_signature)

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
            type(self).setup_descriptor({"name": field, "args": (int,), "kwargs":{}})
            # NOTE: 2021-11-30 17:36:12
            # this MUST be called otherwise no attribute will be added to the instance
            # (this calls descriptor's __set__ function which does just that)
            setattr(self, name, None)
            
        for field, value in field_map.items():
            if not isinstance(field, str) or len(field.strip()) == 0:
                raise TypeError(f"A field must be a non-empty string; got {field} instead")
            
            type(self).setup_descriptor({"name": field, "args": (int,),  "kwargs":{}})
            #type(self).setup_descriptor({"name": field, "args": ((int, collections.abc.Sequence), int), "kwargs":{}})
            setattr(self, field, value)
              
    
    def __contains__(self, item:str):
        properties = tuple(d for d in get_descriptors(type(self)) if not d.startswith("_"))
        if len(properties) == 0:
            properties = sorted(tuple(k for k in self.__dict__ if not k.startswith("_")))
            
        return item in properties
    
    def __str__(self):
        properties = tuple(d for d in get_descriptors(type(self)) if not d.startswith("_"))
        if len(properties) == 0:
            properties = sorted(tuple(k for k in self.__dict__ if not k.startswith("_")))
            
        ret = list()
        for p in properties:
            if hasattr(self, p):
                ret.append(f"{p} = {getattr(self, p)}")
            
        return "\n".join(ret)
    
    def fields(self):
        return dict((f, getattr(self, f)) for f in self.fieldNames())
    
    def fieldNames(self):
        fields = tuple(d for d in get_descriptors(type(self)) if not d.startswith("_"))
        if len(fields) == 0:
            fields = sorted(tuple(k for k in self.__dict__ if not k.startswith("_")))
            
        return tuple(f for f in fields if hasattr(self, f))
    
    def addField(self, name:typing.Optional[str] = None, value:typing.Optional[int]=None):
        if not isinstance(name, str) or len(name.strip()) == 0:
            return
        
        type(self).setup_descriptor({"name": name, "args":(int,), "kwargs":{}})
        # NOTE: see NOTE: 2021-11-30 17:36:12
        setattr(self, name, value) 
        
    
class FrameIndexLookup(object):
    """Tools for frame synchronization between scans, scene and ephys data.
    
    FrameIndexLookup maps a virtual data frame to a frame index into each of its
    data child components (for ScanData, these are: 'scene', 'scans' and 
    'electrophysiology').
    
    The 'fields' in a FrameIndexLookup object are deduced from the data, or from
    the MultiFrameIndex objects passed in the constructor (see below).
    
    When given, the fields are checked for consistency.
    
    The component frame index is expected to be an int, or None.
    
    virtual_frame_0: MultiFrameIndex(scene:int or None,
                                        scans:int or None,
                                        electrophysiology:int or None)
                                         
    virtual_frame_1: None (implies that frame indices into each component are the
                            same as the virtual frame value for the data)
                                         
    virtual_frame_2: MultiFrameIndex(scene:int or None,
                                        scans:int or None,
                                        electrophysiology:int or None)
                                         
    Behaves like a dict with int keys mapped to instance of MultiFrameIndex 
    objects (see core.multiframeindex).
        
    """
    
    def __get_frame_index__(self, index:int, field: str):
        """Returns master index if field not found or index not mapped
        """
        if index in self._map_:
            return getattr(self._map_[index], field, index)
        
        return index
    
    def __set_frame_index__(self, index:int, field:str, value:typing.Union[int]=None):
        """Set the data frame index for the master frame index, to value
        """
        if not isinstance(value, type(None)):
            raise TypeError(f"Expecting an int or None; got {type(value).__name__} instead")
        
        if index in self._map_:
            if field in self._map_[index]:
                setattr(self._map_[index], field, value)
            else: # CAUTION: subclasses of MultiFrameIndex MAY be immutable
                try:
                    self._map_[index].addField(field, value)
                    self._field_names_.add(field) # NOOP if field exists
                except:
                    pass
                
        else: # add a new frame
            if not isinstance(index, int):
                raise TypeError(f"Expectinf an int for master 'index'; got {type(index).__name__} ")
            # CAUTION: subclasses of MultiFrameIndex MAY expect specific arguments
            # NOTE: no checking on value's attributes here ... this MAY be done
            # by the MultiFrameIndex initializer (self._index_type_ SHOULD inherit
            # from this)
            init_sig = classify_signature(self._index_type_.__init__)
            pos_named = init_sig.positional | init_sig.named
            
            kwargs = dict()
            
            if len(init_sig.varkw) == 0:
                if field not in pos_named:
                    raise ArgumentError(f"{field} is an unexpected argument for {self._index_type_.__name__}")
                
            elif field in init_sig.kwargs:
                kwargs[field] = value
                
            
            if field in init_sig.positional:
                pos_only = tuple(value if k == field else None for k in init_sig.positional if k != "self")
                
                if field in init_sig.named:
                    raise ArgumentError(f"duplicate specification for {field}")
                
            else:
                pos_only = tuple()
                
            if field in init_sig.named:
                # add it to kwargs!
                if field not in kwargs:
                    kwargs[field] = value
                else:
                    raise ArgumentError(f"duplicate specification for {field}")
                
            self._map_[index] = self._index_type_(*pos_only, **kwargs)
            self._field_names_.add(field) # NOOP if field exists
            
            #try:
            
            #except:
                #pass # fails silently
    
    @classmethod
    def __bind__(cls, func, instance, as_name=None):
        """
        See https://stackoverflow.com/questions/1015307/python-bind-an-unbound-method/1015405#1015405
        
        """
            
    def __init__(self, data=None, *args):
        """
        data: python object where data is stored framewise in a '_data_children_'
        :class: attribute; optional, default is None
            
        *args: one or more dict with the following structure:
            int key : MultiFrameIndex object or None
                When a MultiFrameIndex this is expected to have the following 
                fields: 'scene', 'scans', 'electrophysiology', mapped to either
                an int value, or to None.
        """
        data_children = getattr(data, "_data_children_", None)
        field_names = set(c[0] for c in data_children if isinstance(c[0], str) and len(c[0].strip()))
        
        self._map_ = dict()
        
        self._index_type_ = None
        
        for arg in args:
            if not isinstance(arg, dict) or len(arg) == 0 or not all(isinstance(k, int) for k in arg) or not all(isinstance(v, (MultiFrameIndex, type(None))) for v in arg.values()):
                raise TypeError("Expecting a mapping of int keys to MultiFrameIndex objects or to None")
            # NOTE: 2021-12-01 15:38:06
            # Loosely check for field names consistency:
            #
            # 1) use those supplied by the data, if any; else use those supplied
            # by the first encountered MultiFrameIndex object in args;
            #
            # 2) allow partial overlap between field names and those of subsequent
            # MultiFrameIndex objects (as they might in principle NOT supply a frame
            # index for all relevant fields)
            
            for v in arg.values():
                if v is not None:
                    # make sure that all multi frame index objects are instances of the same type
                    if self._index_type_ is None:
                        self._index_type_ = type(v)
                    else:
                        if type(v) != self._index_type_: # strict relation here, not accepting subclasses or ancestors
                            raise TypeError(f"Expecting a {self._index_type_.__name__}; got {type(v).__name__} instead")
                        
                    # make sure all field names in  the multi frame index instances are
                    # either the same, or at least have fields in common
                    v_fields = set(v.fieldNames())
                    
                    if len(field_names):
                        field_names = v_fields
                    else:
                        if field_names.isdisjoint(v_fields):
                            raise TypeError(f"{k}th MultiFrameIndex has incorrect fields {v_fields}; expecting {field_names}")
                        # update field_names
                        field_names |= v_fields
                        
            self._map_.update(arg)
            
            
        self._field_names_ = field_names # for reference
        
        for field in self._field_names_:
            pass
        
    @property
    def map(self):
        return self._map_
    
    def __len__(self):
        return len(self._map_)
        
    def __getitem__(self, key:int):
        return self._map_.get(key, None)
    
    def __delitem__(self, key:int):
        if key in self._map_:
            del(self._map_[key])
    
    def __setitem__(self, key:int, value:typing.Optional[MultiFrameIndex] = None):
        if not isinstance(value, (MultiFrameIndex, type(None))):
            raise TypeError(f"Expecting a MultiFrameIndex or None; got {type(value).__name__} instead")
        
        if isinstance(value, MultiFrameIndex):
            v_fields = set(value.fieldNames())
            if len(self._field_names_):
                if self._field_names_.isdisjoint(v_fields):
                    raise TypeError(f"Argument has incorrect field names {v_fields}; expected {self._field_names_}")
            else:
                self._field_names_ = v_fields
                
        self._map_[key] = value
        
    
        
    def scene(self, frame:int):
        if frame in self._map_:
            return self._map_[frame].scene if isinstance(self._map_, MultiFrameIndex) else None
        
    def setScene(self, frame:int, value:typing.Optional[int] = None):
        frameindex = self._map_.get(frame, None)
        if isinstance(frameindex, MultiFrameIndex):
            frameindex.scene = value
            
        elif isinstance(value, int):
            # create frame index of it doesn't exist and value is an int
            self._map_[frame] = MultiFrameIndex(scene=value)
            
    def scans(self, frame:int):
        if frame in self._map_:
            return self._map_[frame].scans if isinstance(self._map_, MultiFrameIndex) else None
        
    def setScans(self, frame:int, value:typing.Optional[int]):
        frameindex = self._map_.get(frame, None)
        if isinstance(frameindex, MultiFrameIndex):
            frameindex.scene = value
            
        elif isinstance(value, int):
            self._map_[frame] = MultiFrameIndex(scans=value)
        
    def electrophysiology(self, frame:int):
        if frame in self._map_:
            return self._map_[frame].electrophysiology if isinstance(self._map_, MultiFrameIndex) else None
        
    def setElectrophysiology(self, frame:int, value:typing.Optional[int]):
        frameindex = self._map_.get(frame, None)
        if isinstance(frameindex, MultiFrameIndex):
            frameindex.electrophysiology = value
            
        elif isinstance(value, int):
            self._map_[frame] = MultiFrameIndex(electrophysiology = value)
        
