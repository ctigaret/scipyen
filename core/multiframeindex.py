import os, typing, types
from functools import partial, partialmethod
from collections import namedtuple
import collections.abc
from inspect import (getmembers, getattr_static)
from core.prog import (ArgumentError,  WithDescriptors, 
                       get_descriptors, classify_signature)
from core.basescipyen import BaseScipyenData

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

#MultiFrameIndex = namedtuple("MultiFrameIndex", ("scene", "scans", "electrophysiology") module = __module_name__)
    
class MultiFrameIndex(WithDescriptors):
    """Maps a virtual data frame index to frame indices into its compoents
    """
        
    def __init__(self, *fields, **field_map):
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
    
    FrameIndexLookup is used with objects containing distinct data sets organized 
    in frames (views into data subsets to be displayed and/or analysed separately
    from the rest of the data). 
    
    The primary example are ScanData objects which contain a set of images 
    ("scans"), and possibly a set of reference image data ("scene") and a set of
    electrophysiology signals.
    
    Each of these data types can be viewed and analysed frame-by-frame, where a
    'frame' associates a single image in "scans", with an image in the "scene",
    and a corresponding 'sweep' in the electrophysiology data set.
    
    Ideally, there should be a direct, one-to-one correspondence between a frame
    in all three data components ("scans", "scene" and "electrophysiology"). 
    In practice this may not always happen e.g., when there is only one reference
    image in "scene" for all images in "scans", or when the number of 
    electrophysiology sweeps is different from the number of frames in the 
    "scans" data.
    
    The FrameIndexLookup introduces the notion of "virtual data frame" where 
    a data "frame index" is mapped to a real frame index into each of the 
    data components (e.g., for the ScanData in the example above, a virtual
    frame index would correspond to the frame with same index in "scans", but 
    always to frame index 0 in "scene").
    
    The data components corresponding to the virtual frame 0 can be accessed via
    FrameLookupIndex in a simple manner:
    
    frame[index].scene -> 0
    frame[index].scans -> index
    frame[index].electrophysiology -> None (assuming there is no electrophysiology
    data available)
    
    where 'index' is any valid index (in this example, "scans" have the largest
    number of frames and "drive" the frame indexing for the entire data in the 
    ScanData object)
    
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
    
    class __IndexProxy__(object):
        def __init__(self, field:str):
            if not isinstance(field, str) or len(field.strip()) == 0:
                raise ArgumentError(f"Expecting a non-empty str; got {field} instead")
            self._obj_ = None
            self._field_ = field
            
        def __get__(self, obj, objtype=None):
            # NOTE: 2021-12-01 22:44:11 reference needed in __get/setitem__
            self._obj_ = obj 
            # NOTE: 2021-12-01 22:08:48 
            # returns self so that setitem and getitem can be called upon it
            return self
        
        def __set__(self, obj, value=None):
            # NOTE: 2021-12-01 22:44:11 reference needed in __get/setitem__
            self._obj_ = obj
        
        def __getitem__(self, key:int):
            return getattr(self._obj_._map_[key], self._field_, key)
        
        def __setitem__(self, key:int, value:int):
            if key in self._obj_._map_:
                if self._field_ in self._obj_._map_[key]:
                    setattr(self._obj_._map_[key], self._field_, value)
                else: # CAUTION: subclasses of MultiFrameIndex MAY be immutable
                    try:
                        self._obj_._map_[key].addField(field, value)
                        self._obj_._field_names_.add(field) # NOOP if field exists
                    except:
                        pass
            else:# add a new frame
                if not isinstance(key, int):
                    raise TypeError(f"Expecting an int for master 'index'; got {type(key).__name__} ")
                # CAUTION: subclasses of MultiFrameIndex MAY expect specific arguments
                # NOTE: no checking on value's attributes here ... this MAY be done
                # by the MultiFrameIndex initializer (self._index_type_ SHOULD inherit
                # from this)
                init_sig = classify_signature(self._obj_._index_type_.__init__)
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
                    
                self._obj_._map_[key] = self._obj_._index_type_(*pos_only, **kwargs)
                self._obj_._field_names_.add(field) # NOOP if field exists
        
    
    def __init__(self, data:typing.Optional[BaseScipyenData]=None, *args):
        """
        data: python object where data is stored framewise in a '_data_children_'
        :class: attribute; optional, default is None
            
        *args: one or more dict with the following structure:
            int key : MultiFrameIndex object or None
                When a MultiFrameIndex this is expected to have the following 
                fields: 'scene', 'scans', 'electrophysiology', mapped to either
                an int value, or to None.
        """
        if len(args) == 0:
            if isinstance(data, dict) and all(isinstance(k, int) and isinstance(v, (type(None), MultiFrameIndex)) for k,v in data.items()):
                args = (data,)
                data = None
                
            elif not isinstance(data, (type(None), BaseScipyenData)):
                raise TypeError(f"'data expected to be a BaseScipyenData object or None; got {type(data).__name__} instead")
            
        data_children = getattr(data, "_data_children_", tuple())
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
            
            for k,v in enumerate(arg.values()):
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
                    
                    if len(field_names) == 0:
                        field_names = v_fields
                    else:
                        if field_names.isdisjoint(v_fields):
                            raise TypeError(f"{k}th MultiFrameIndex has incorrect fields {v_fields}; expecting {field_names}")
                        # update field_names
                        field_names |= v_fields
                        
            self._map_.update(arg)
            
        self._field_names_ = field_names if len(field_names) else set() # for reference
        
        for field in self._field_names_:
            setattr(type(self), field, self.__IndexProxy__(field))
             
    @property
    def map(self):
        return self._map_
    
    def __len__(self):
        return len(self._map_)
        
    def __getitem__(self, key:int):
        # NOTE: return the ke when nothing is mapped to it
        return self._map_.get(key, key)
    
        #return self._map_.get(key, None)
    
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
        
    
        
    #def scene(self, frame:int):
        #if frame in self._map_:
            #return self._map_[frame].scene if isinstance(self._map_, MultiFrameIndex) else None
        
    #def setScene(self, frame:int, value:typing.Optional[int] = None):
        #frameindex = self._map_.get(frame, None)
        #if isinstance(frameindex, MultiFrameIndex):
            #frameindex.scene = value
            
        #elif isinstance(value, int):
            ## create frame index of it doesn't exist and value is an int
            #self._map_[frame] = MultiFrameIndex(scene=value)
            
    #def scans(self, frame:int):
        #if frame in self._map_:
            #return self._map_[frame].scans if isinstance(self._map_, MultiFrameIndex) else None
        
    #def setScans(self, frame:int, value:typing.Optional[int]):
        #frameindex = self._map_.get(frame, None)
        #if isinstance(frameindex, MultiFrameIndex):
            #frameindex.scene = value
            
        #elif isinstance(value, int):
            #self._map_[frame] = MultiFrameIndex(scans=value)
        
    #def electrophysiology(self, frame:int):
        #if frame in self._map_:
            #return self._map_[frame].electrophysiology if isinstance(self._map_, MultiFrameIndex) else None
        
    #def setElectrophysiology(self, frame:int, value:typing.Optional[int]):
        #frameindex = self._map_.get(frame, None)
        #if isinstance(frameindex, MultiFrameIndex):
            #frameindex.electrophysiology = value
            
        #elif isinstance(value, int):
            #self._map_[frame] = MultiFrameIndex(electrophysiology = value)
        
