import os, typing, types
from functools import partial, partialmethod
from collections import namedtuple
import collections.abc
from inspect import (getmembers, getattr_static)
import numpy as np
import pandas as pd
from core.prog import (ArgumentError,  WithDescriptors, 
                       get_descriptors, classify_signature)
from core.utilities import (nth, normalized_index, sp_set_loc, sp_get_loc)
from core.basescipyen import BaseScipyenData

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

####MultiFrameIndex = namedtuple("MultiFrameIndex", ("scene", "scans", "electrophysiology") module = __module_name__)
    
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
        
    
class MultiFrameIndexLookup(object):
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
            
        def __get_ndx__(self, field, ndx, default):
            #nFramesForField = getattr(self._obj_, f"{self._field_}_nFrames", None)
            nFramesForField = self._obj_._n_child_frames_.get(self._field_, None)
            print(f"proxy, in __get_ndx__: nFrames for {self._field_}: {nFramesForField}; ndx: {ndx}")
            if isinstance(nFramesForField, int):
                return normalized_index(range(nFramesForField), ndx, silent=True)
        
        def __getitem__(self, key:int):
            index = self._obj_[key]
            print(f"proxy, in getitem: {key} -> {type(index).__name__}")
            if isinstance(index, MultiFrameIndex):
                # check for field in MultiFrameIndex
                if hasattr(index, self._field_):
                    val = getattr(index, self._field_)
                    #print(f"for index {index} of {self._field_} got {val}")
                    # CAUTION: 2021-12-03 16:19:05
                    # the one-liner:
                    # `return val if isinstance(val, int)`
                    # is NOT the same as the `if` clause below:
                    # the 1-liner ALWAYS returns (including None when 'val' is
                    # not an int)
                    # in contrast, the `if` clause below ONLY returns 'val' when
                    # 'val' is an int
                    if isinstance(val, int):
                        return val
                    
                    # from here on, val is explicitly None for given field in
                    # the MultiFrameIndex, or MFI doesn't have field, or key is
                    # NOT mapped to an MFI
                    #

            # try to use nth here (default on the last available frame)
            val = self.__get_ndx__(self._field_, key, -1)
            # NOTE: see CAUTION: 2021-12-03 16:19:05
            if isinstance(val, int):
                return val
            
            # finally, return key when all of the above failed
            return key
                        
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
        
    
    def __init__(self, *args, **kwargs):
        """
        *args: one or more dict with the following structure:
            int key : MultiFrameIndex object or None
                When a MultiFrameIndex this is expected to have the following 
                fields: 'scene', 'scans', 'electrophysiology', mapped to either
                an int value, or to None.
                
        *kwargs:
        -----------
        'data_children': tuple of strings, with the name of the data children attributes
            Each data child stores data frame-wise, and MAY NOT have the same 
            number of frames as the other data children;
            
            Empty tuple, by default
            
        'maxFrames': int >=0 or None. When given this represents the maximum 
            number of frames allowed in the lookup
            
        '*_nFrames': int >= 0 where * is str matching the field names of the 
            MultiFrameIndex passed via *args
            
        """
        #data_children = kwargs.pop("data_children", tuple())
        
        #if not isinstance(data_children, tuple)) or (len(data_children) > 0 and not all(isinstance(d, str) and len(d.strip())>0 for d in data_children)):
            #raise TypeError(f"'data expected to be a tuple of non-empty strings, or an empty tuple; got {data_children} instead")
        
        maxFrames = kwargs.pop("maxFrames", None)
        
        if isinstance(maxFrames, int):
            if maxFrames < 0:
                raise ValueError(f"'maxFrames' cannot be negative")
            
        elif maxFrames is not None:
            raise TypeError(f"'maxFrames' expected an int or None; got {type(maxFrames).__name__} instead")
            
        self._maxFrames_ = maxFrames
        
        self._map_ = dict()
        
        self._index_type_ = None
        
        field_names = set()
        
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
        self._n_child_frames_ = dict()
        for field in self._field_names_:
            self._n_child_frames_[field] = kwargs.pop(f"{field}_nFrames", None)
            setattr(type(self), field, self.__IndexProxy__(field))
             
    @property
    def map(self):
        return self._map_
    
    @property
    def maxFrames(self):
        return self._maxFrames_
    
    @maxFrames.setter
    def maxFrames(self, val):
        if isinstance(val, int):
            if val < 0:
                raise ValueError(f"maxFrames cannot be negative; got {val} instead")
            
            self._maxFrames_ = val
            
        elif val is not None:
            raise TypeError(f"Expecting an int or None; got {val} instead")
        
        else:
            self._maxFrames_ = None
    
    def __len__(self):
        return len(self._map_)
        
    def __getitem__(self, key:int):
        if isinstance(self._maxFrames_, int):
            if key not in range(-self._maxFrames_, self._maxFrames_):
                raise KeyError(f"Frame index{key}  out of range {(-self._maxFrames_, self._maxFrames_-1)}")
        
        # NOTE: return the key when nothing is mapped to it
        return self._map_.get(key, key)
    
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
        
class FrameIndexLookup(object):
    """Wrapper around multi-frame indexing using sparse pandas DataFrames.
    
    The correspondence between data master ("virtual") frame index and the 
    index of the frames in the child data objects of the owner are stored in a
    sparse array wrapped in a Pandas DataFrame.
    
    The owner's fields containing child data are stored as column names in 
    the underlying DataFrame (the 'map' attribute of the FrameLookupIndex 
    instance) and are accessed as descriptors of the FrameLookupIndex.

    For example, the 'framesMap' attribute of ScanData objects are instances of
    FrameLookupIndex with the 'scans', 'scene' and 'electrophysiology' as 
    FrameLookupIndex descriptors, and column names in the underlying DataFrame.
    
    To keep things simple, a FrameLookupIndex instance exposes item access to
    these fields, as well as attribute access, e.g.:
    
    frames["scans"] is frames.scans --> True
    
    Access to the kth frame is obtained also by item access where 'item' is an
    int, or an indexing objects for the underlying DataFrame along its first 
    (index) axis, e.g.:
    
    frames[2] --> Pandas Series with index set to the columns attribute of the 
        underlying DataFrame 'map'.
    
    
    
    """
    class __IndexProxy__(object):
        """Proxy for accessing a data field in the FrameIndexLookup.
        
        The data field itself is a Pandas Series with SparseDtype, contained
        in the 'map' attribute (a DataFrame) of the owner of this proxy, with 
        the owner being an instance of FrameIndexLookup.
        
        """
        def __init__(self, field:str):
            """Creates the descriptor corresponding to a data field in the owner.
            Also sets up the field's name as a descriptor of FrameIndexLookup
            """
            if not isinstance(field, str) or len(field.strip()) == 0:
                raise ArgumentError(f"Expecting a non-empty str; got {field} instead")
            self._obj_ = None
            self._field_ = field
            
        def __get__(self, obj, objtype=None):
            """Returns the descriptor itself.
            
            The descriptor forwards access & assignment to the corresponding
            Pandas Series object in the owner's 'map' attribute so that the
            special functions sp_set_loc and sp_get_loc (defined in the 
            core.utilities module) can be applied
            """
            self._obj_ = obj
            return self
            
        def __get2__(self, obj, objtype=None):
            """Returns a pandas series corresponding to self._field_
            
            The caller must ensure the appropriate indexing is applied to the 
            result.
            
            (alternative to self.__get__ - do not use)
            """
            self._obj_ = obj 
            # NOTE: 2021-12-01 22:08:48 
            # returns the pandas Series mapped to self._field_ so that 
            # owner's __getitem__ & __setitem__ can use sp_get_loc and sp_set_loc, 
            # respectively;
            # the drawback is that we cannot use negative indices here directly
            # 
            if self._field_ in self._obj_._map_.columns:
                return self._obj_._map_.loc[:, self._field_] 
            
            ## NOTE: return self so that we use a custom get/set item for the 
            ## owner's DataFrame in '_map_'
            
            ## if self._field_ is not among owner's _map_ columns return None
            ##return None
            
            ##return self # so now custom getitem/setitem can be applied
        
        def __set__(self, obj, value=None):
            # NOTE: 2021-12-01 22:44:11 reference needed in __get/setitem__
            self._obj_ = obj
            
        def __getitem__(self, key):
            return sp_get_loc(self._obj_._map_, key, self._field_)
        
        def __setitem__(self, key, value):
            sp_set_loc(self._obj_._map_, key, self._field_, value)
                        
    def __init__(self, field_frames:dict, field_missing=pd.NA, frame_missing = -1,
                 **kwargs):
        """
        Parameters:
        ------------
        field_frames: dict 
            
            This maps a str (field name) to an int (>=0, the number of available 
            data frames in that named field), or to None, if the named field is 
            absent from the owner of this FrameIndexLookup instance.
            
            NOTE 1: Named fields are attributes, properties or data descriptors 
            defined in the owner's :class:, accessing data objects that are
            stored in the owner's instance and can be viewed/sliced in 'frames'
            (more specifically, in Scipyen, such are VigraArray which can be
            sliced in 2D views, and the segments of neo.Block objects).
            
            The named fields may be advertised by the owner's :class: (see, for
            example, BaseScipyenData._data_attributes_) and are accessed by the
            field's name as a regular attribute, property (getter, setter) or 
            via the data descriptor protocol.
            
            A named field is 'absent' when an attempt to access it in the owner 
            returns None (as opposed to raising AttributeError or a similar
            exception which happens when the object doesn't know anything about
            the field's name).
            
            When present, the named field may be unable for provide any 'frames'
            (2D views, or segments). In this case, the number of frames of the 
            data in the field is 0 (zero).
            
        field_missing: int or pd.NA. Optional, default is pd.NA
        
            The frame index value standing in for a named field that is missing
            in the owner (see above)
            
            Optional, default is pd.NA
            
        frame_missing: int or pd.NA. Optional, default is -1
        
            The frame index value standing for a missing frame in the named field
            (i.e., when the named field has fewer frames than the highest number 
            of frames across all the named fields in 'field_frames')
            
        Var-keyword parameters:
        ------------------------
        When given, their names must be present in field_frames keys (otherwise
        are ignored) and their values are tuples of the form
            (master index:int, field frame index:int),
            
        or a sequence of such tuples
            
            These contain specific associations of frames in the named field 
            with a master field index in the owner.
            
            When a master field index in these tuples points to a frame index
            outside the current range of master frames of the owner, will raise
            an IndexError exception.
            
            (This is to keep the initialization code simple, although it is
            possible to 'add' new master frames to the object, but not at
            initialization time)
            
        Examples:
        ---------
        
        1) The trivial case of an owner (a ScanData) with scans and scene, each
        with 3 frames, and with electrophysiology a neo.Block with three segments.
        
        If there is a biunivocal correspondence of frame indices between ALL three
        fields ('scans', 'scene' and 'electrophysiology'), the owner does NOT need
        a FrameIndexLookup object. When present, the FrameIndexLookup object 
        exposes a DataFrame with the following structure:
        
                scans scene electrophysiology
        0       0     0      0
        1       1     1      1
        2       2     2      2
        
        where the index (left most column of numbers) if the master frame index 
        of the owner.
        
        2) The case where the ScanData owner object has only one scene frame.
        
        The frames map DataFrame MAY look like this (using frame_missing  = -1):
        
                scans  scene  electrophysiology
        0       0      0        0
        1       1     -1        1
        2       2     -1        2
        
        3) The case where the ScanData owner object has only one scene frame, 
        ans no electrophysiology
                scans  scene  electrophysiology
        0       0      0        <NA>
        1       1     -1        <NA>
        2       2     -1        <NA>
        
        NOTE 2: the field_missing and frame_missing values have no meaning for 
        the FrameLookupIndex object: they are just placeholders for the missing 
        field frames when the field is missing altogether, or when only some 
        frames are missing. In Examples 2 and 3 above, acessing master frame
        with index 1 in the owner will attempt to access the last available 
        frame in scene (-1); in example 3, accessing master frame 1 will 
        associate <NA> for electrophysilogy. It is up to the owner to decide
        what to do with these values.
        
        """
        # filter out missing fields, to figure out the maximum number of frames 
        # available to the owner of the FrameLookupIndex instance. Field that
        # ARE present but without frames have 0 frames
        
        print(f"FrameIndexLookup.__init__ field_frames = {field_frames}")
        
        if isinstance(field_frames, dict) and len(field_frames):
            field_nframes = dict((k,v) for k,v in field_frames.items() if k in field_frames and isinstance(v, int))
            
        else:
            field_nframes = dict()
            
        maxFrames = max(v for v in field_nframes.values()) if len(field_nframes) else None
        
        # create a dictionary of pandas Series, mapping field name to either:
        # a) range(maxFrames), - when field in field_frames is mapped to a number of frames
        #   (this implies that maxFrames is known)
        # b) [field_missing] * maxFrames, when field in field_frames is mapped to None AND maxFrames is known
        # c) field_missing, when field in field_names is mapped to None and maxFrames is not known
        #   (this implies that neither field is mapped to a number of frames in field_frames)
        dd = dict()
        
        for field,value in field_frames.items():
            if isinstance(value,int):
                sval = range(maxFrames)
                if value < maxFrames:
                    sval = [k if k < value else frame_missing for k in sval]
                
            else:
                if isinstance(maxFrames, int):
                    sval = [field_missing] * maxFrames
                else:
                    sval = field_missing
                    
            dd[field] = pd.Series(sval, name=field, dtype = pd.SparseDtype("int", field_missing))
            
            setattr(type(self), field, self.__IndexProxy__(field))
            
        # use the created dd dict to generate the map data frame
        self._map_ = pd.DataFrame(dd)
        
        #self._map_ = pd.DataFrame(dict((field, pd.Series(range(maxFrames) if isinstance(maxFrames, int) and isinstance(field_frames[field], int) else field_missing, 
                                                         #name=field, dtype=pd.SparseDtype("int", field_missing)))
                                        #for field in field_frames))
        
        # now adjust field frame index values according to each field's number of
        # frames using frame_missing value
        
        #for field, nframes in field_frames.items():
            #if isinstance(nframes, int) and nframes < maxFrames:
                #index = slice(nframes, maxFrames)
                #self._map_ = sp_set_loc(self._map_, index, field, frame_missing)
                
        # finally, apply specific frame relationships in kwargs
        
        for k, v in kwargs:
            if k in field_frames: # only for named field we already know about
                if isinstance(v, tuple):
                    if len(v) == 2 and all(isinstance(v_, int) for v_ in v):
                        # master_index, field frame index
                        
                        # check specified master index and field frame index are
                        # in their respective ranges, if possible
                        if isinstance(maxFrames, int) and v[0] not in range(-maxFrames, maxFrames): # allow negative indices
                            raise ValueError(f"master index {v[0]} out of range {(-maxFrames, maxFrames-1)}")
                        
                        if isinstance(field_frames[k], int):
                            if v[1] not in range(-field_frames[k], field_frames[k]):
                                raise ValueError(f"frame index {v[1]} for {k} out of range {(-field_frames[k], field_frames[k]-1)}")
                        
                        self._map_ = sp_set_loc(self._map_, v[0], k, v[1])
                        
                    elif all(isinstance(v_, tuple) and len(v_) == 2 and all(isinstance(_v_, int) for _v_ in v_) for v_ in v):
                        for v_ in v:
                            if isinstance(maxFrames, int) and v_[0] not in range(-maxFrames, maxFrames): # allow negative indices
                                raise ValueError(f"master index {v_[0]} out of range {(-maxFrames, maxFrames-1)}")
                            
                            if isinstance(field_frames[k], int):
                                if v_[1] not in range(-field_frames[k], field_frames[k]):
                                    raise ValueError(f"frame index {v_[1]} for {k} out of range {(-field_frames[k], field_frames[k]-1)}")
                            
                            self._map_ = sp_set_loc(self._map_, v_[0], k, v_[1])
                            
        self._frame_missing_ = frame_missing
        self._field_missing_ = field_missing
                            
    def __len__(self):
        return len(self._map_)
    
    def __contains__(self, item):
        if isinstance(item, str):
            return item in self._map_.columns
        
        elif isinstance(item, int):
            l = len(self._map_.index)
            return item in range(-l,l)
        
        return False
        
    def __getitem__(self, key:typing.Union[int, slice, range, collections.abc.Sequence, str]):
        """Returns the frame mapping for the master frame index given in 'key'.
        Parameters:
        ----------
        key: either:
            
            a) str - name of a field - index into the 2nd axis of the map DataFrame
            (i.e., into 'self.map.columns'); this has the same effect as the
            attribute access to the field
            
            
            b) int, slice, range, or anything that can be used to index into the 
            underlying 'map' DataFrame along the 1st axis ('self.map.index')
            
            NOTE: when key is an int it can be in the range (-l, l) where 'l' is
            the length of the underlying DataFrame (self.map). A negative int 
            value for key performs reverse indexing into the map's rows.
            
        """
        
        # NOTE: 2021-12-05 12:37:02
        # treat index as a sequence, allow key in range(-len(map.index, map.index))
        # we can do that because index is a range index (ints from 0 to max master
        # frames -1) and we want to emulate Python API enabling the use of 
        # negative indices,slices and ranges (the latter are OK with 1D arrays
        # what the map.index is)
        if isinstance(key, str):
            if key in self._map_.columns:
                return self._map_.loc[:,key]
            
            raise KeyError(f"key {key} not found")
        
        # adapt slice/range/int/sequence of ints
        # map's index is Int64-based (RangeIndex)
        if isinstance(key, range): # ranges are tricky to apply to pandas DFs 
            # therefore convert ranges to slice and fall through to the next 'if' 
            # clause
            key = slice(min(key), max(key), key.step)
        
        if isinstance(key, slice): 
            # this should also deal with ranges from code above
            return self._map_.loc[key,:]
            
        elif isinstance(key, int):
            l = len(self._map_)
            if key not in range(-l,l):
                raise IndexError(f"Index {key} out of range {range(-l,l)}")
            
            if key < 0:
                return self._map_.iloc[key, :]
        
            return self._map_.loc[ndx, :]
        
        else:
            return sp_get_loc(self._map_, key, slice(None)) # use all columns (slice(None))
                
        # NOTE: return the key when nothing is mapped to it
        
    def __setitem__(self, key:int, value:typing.Optional[pd.DataFrame] = None):
        raise NotImplementedError("FIXME: TODO 2021-12-04 23:40:02")
        if not isinstance(value, (pd.DataFrame, type(None))):
            raise TypeError(f"Expecting a pandas DataFrame or None; got {type(value).__name__} instead")
        
        if isinstance(value, pd.DataFrame):
            v_fields = set(value.columns)
            field_names = set(self._map_.columns)
            if len(self._field_names_):
                if self._field_names_.isdisjoint(v_fields):
                    raise TypeError(f"Argument has incorrect field names {v_fields}; expected {self._field_names_}")

            for column in value.columns:
                pass
        #self._map_[key] = value
        
    def childFrames(self, field:str):
        if field in self._map_.columns:
            frames = self._map_.loc[~self._map_.loc[:,field].isna(), field]
            if len(frames):
                return max(frames) + 1
            return self._field_missing_
        
    def keys(self):
        yield from self._map_.columns
        
    @property
    def map(self):
        return self._map_
    
    @property
    def masterFrames(self):
        return self._map_.index
    
    @property
    def missingFrameIndex(self):
        return self._frame_missing_
    
    @missingFrameIndex.setter
    def missingFrameIndex(self, val:typing.Union[int, type(pd.NA)]):
        if not isinstance(val, (int, type(pd.NA))):
            raise ArgumentError(f"'val' expectd an int or pd.NA; got {val} instead")
        self._frame_missing_ = val
        
    @property
    def missingFieldFrameIndex(self):
        return self._field_missing_
    
    @missingFieldFrameIndex.setter
    def missingFieldFrameIndex(self, val:typing.Union[int, type(pd.NA)]):
        if not isinstance(val, (int, type(pd.NA))):
            raise ArgumentError(f"'val' expectd an int or pd.NA; got {val} instead")
        self._field_missing_ = val
        
    
