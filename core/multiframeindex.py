import os, typing, types
from functools import partial, partialmethod
from collections import namedtuple
import collections.abc
from inspect import (getmembers, getattr_static)
import numpy as np
import pandas as pd
from core.prog import (ArgumentError,  WithDescriptors, 
                       get_descriptors, signature2Dict)
from core.utilities import (nth, normalized_index, sp_set_loc, sp_get_loc)
from core.basescipyen import BaseScipyenData

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

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
    
    To keep things simple, a FrameLookupIndex instance exposes item and attribute
    access to these fields
    
    frames["scans"] is frames.scans --> True
    
    Access to the kth frame is obtained also by item access where 'item' is an
    int, or an indexing objects for the underlying DataFrame along its first 
    (index) axis, e.g.:
    
    frames[2] --> Pandas Series with index set to the columns attribute of the 
        underlying DataFrame 'map'.
        
    The frame mapping across the fields can be modified via a combination of
    attribute access (for the field) and index access for the master frame index
    e.g.,
    
    Let 'framesMap' be a frame index lookup with contents shown below:
    
        FrameIndexLookup with 3 frames.
        Data components: ('scans', 'scene', 'electrophysiology')
        Frame Indices Map (frame index -> index of component frame or segment):
                scans  scene  electrophysiology
        Frame                                 
        0          0      0                  0
        1          1      1                  1
        2          2      2               <NA>

    In 'framesMap', the 'electrophysiology' has only two frames which by default
    are mapped to the first two master frame indices.
    
    If this is not what was intended, the mapping can be modified with two calls:
    
        framesMap.electrophysiology[2] = 1
        
        framesMap.electrophysiology[1] = pd.NA
    
    
    and the result is:
    
        FrameIndexLookup with 3 frames.
        Data components: ('scans', 'scene', 'electrophysiology')
        Frame Indices Map (frame index -> index of component frame or segment):
                scans  scene  electrophysiology
        Frame                                 
        0          0      0                  0
        1          1      1               <NA>
        2          2      2                  1

    WARNING: These operations REQUIRE attribute (NOT index) access to the 
    particular field i.e., the following idiom does not work:
    
        framesMap["electrophysiology"][2] = 1
        
        --> TypeError: SparseArray does not support item assignment via setitem
        
        This is because the index access framesMap["electrophysiology"] returns
        a pandas.SparseArray. 
        
        In contrast, attribute access as in the example above works due to the
        descriptor protocol used in the implementation.
    
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
            core.utilities module) can be applied.
            
            To obtain the actual data associated with the field use the call 
            syntax.
            """
            #print(objtype)
            self._obj_ = obj
            return self
        
        def __len__(self):
            """Returns the number of registered component frame indices.
            
            A registered frame index is an int. 
            
            Technically this is not necessarily the same thing as the actual 
            number of frames in the data component although the two values MAY 
            be identical.
            
            The actual number of frames in the data component SHOULD be obtained
            by directly interrogating the data component itself.
            
            Contrived cases include:
            a) a component having N frames but only m < N of these are mapped to
            a virtual data frame
            
            b) a component for which a virtual data frame is mapped to the 
            "missingFrameIndex" (by default this is -1, pointing to the last 
            available frame in the component) which means it would appear to
            have more frames than it actually does.
            
            """
            data = self() # pandas Series
            
            return len(data.loc[~data.isna()])
            
        def __call__(self):
            """Returns the pandas series corresponding to self._field_
            
            The caller is responsible for appropriate indexing into the result.
            """
            if self._field_ in self._obj_._map_.columns:
                return self._obj_._map_.loc[:, self._field_] 
            
        def __set__(self, obj, value=None):
            # NOTE: 2021-12-01 22:44:11 reference needed in __get/setitem__
            self._obj_ = obj
            if isinstance(value, collections.abc.Sequence) and len(value) == len(self._obj_._map_) and all(isinstance(v, (int, type(pd.NA))) for v in value):
                sp_set_loc(self._obj_._map_, slice(None), self._field_, value)
                
            elif isinstance(value, pd.Series) and len(value) == len(self._obj_._map_):
                sp_set_loc(self._obj_._map_, slice(None), self._field_, value.loc[:])
                
            
        def __getitem__(self, key):
            return sp_get_loc(self._obj_._map_, key, self._field_)
        
        def __setitem__(self, key, value):
            sp_set_loc(self._obj_._map_, key, self._field_, value)
                        
    def __init__(self, field_frames:dict, 
                 field_missing=pd.NA, frame_missing = -1, index_name="Frame",
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
        
        #print(f"FrameIndexLookup.__init__ field_frames = {field_frames}")
        
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
        
        ndxname = index_name if isinstance(index_name, str) and len(index_name.strip()) else "Frame"
        
        self._map_.index.name = ndxname
        
        # finally, apply specific frame relationships in kwargs: 
        for k, v in kwargs:
            if k in field_frames: # only for named field we already know about
                if isinstance(v, tuple):
                    if len(v) == 2 and all(isinstance(v_, int) for v_ in v): # (master_index, field frame index)
                        
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
        
            return self._map_.loc[key, :]
        
        else:
            return sp_get_loc(self._map_, key, slice(None)) # use all columns (slice(None))
                
        # NOTE: return the key when nothing is mapped to it
        
    def __setitem__(self, key, value):
        """Item setter
        
        Parameters:
        -----------
        key: str: for indexing into the columns of DataFrame objects
             int, range, slice, or object valid for indexing into the rows
             of DataFrame objects
            
        When 'key' is a str, populate the Series at column 'key' with 'value'.
        
        When 'key' is a row (frame) index e.g., int, range, slice, etc then
        populate the row selected by 'key' with 'value'
        
        value: any object suitable as rvalue (right-hand value) for the 
            underlying 'map' DataFrame (e.g. pd.NA, int, range, sequence of int
            and/or pd.NA).
        
        NOTE: Pandas will raise Exception if either 'key' or 'value' are not
            suitable, although the messages will be somewhat cryptic...
        """
        if isinstance(key, str) and key in self._map_.columns:
            sp_set_loc(self._map_, slice(None), key, value)
            return
        
        if isinstance(key, range):
            key = slice(min(key), max(key), key.step)
            
        if isinstance(key, slice):
            self._map_.loc[key, :] = value
            
        elif isinstance(key, int):
            l = len(self._map_)
            if key not in range(-l,l):
                raise IndexError(f"Index {key} out of range {range(-l,l)}")
            
            if key < 0:
                self._map_.iloc[key, :] = value
            else:
                self._map_.loc[ndx, :] = value
                
        else:
            sp_set_loc(self._map_, key, slice(None), value)
            
    def _repr_pretty_(self, p, cycle):
        p.text(f"{self.__class__.__name__} with {len(self)} frames.")
        p.breakable()
        p.text(f"Data components: {tuple(self.keys())}\n")
        p.text(f"Frame Indices Map (frame index -> index of component frame or segment):\n")
        p.pretty(self._map_)
        #p.text(f"{self._map_}")
        
    def childFrames(self, field:str):
        if field in self._map_.columns:
            frames = self._map_.loc[~self._map_.loc[:,field].isna(), field]
            if len(frames):
                return max(frames) + 1
            return self._field_missing_
        
    def keys(self):
        yield from self._map_.columns
        
    def remap(self, field:str, newMap:dict={}):
        """Remaps master frame indices to new frame indices of 'field'.
        
        Parameters:
        ===========
        field:str the name of the field; raises AttributeError if the name in 
            'field' is not the name of an existing field in this FrameIndexLookup
            instance.
            
        newMap:dict; optional, default is {} (the empty dict).
            When not empty, it must satify the following constraints:
            
            1) contains unique int keys >=0 that mapped to int values or to 
            self.missingFieldFrameIndex (which by default is Pandas' NA).
            
            2) the values must be unique
            
        
        """
        if len(newMap):
            # NOTE: 2022-01-11 12:28:21
            # check for validity of keys and values
            if not all(isinstance(k, int) and k >= 0 for k in newMap.keys()):
                raise TypeError(f"When given, the newMap must contain int keys >= 0")
            
            if not all((isinstance(v, int) and v >= 0) or self.__check_missing__(v) for v in newMap.values()):
                raise ValueError(f"When given, the newMap must contain int values >= 0 or {self.missingFieldFrameIndex}")
            
            # NOTE: 2022-01-11 12:34:56
            # check for uniqueness of keys and values
            if len(set(newMap.values())) != len(newMap):
                raise ValueError("Mapping values must be unique")
        
            if len(set(newMap.keys())) != len(newMap):
                raise ValueError("Mapping keys must be unique")
            
            for k,v in newMap.items():
                #print(f"newMap k = {k}: v = {v}")
                getattr(self, field)[k] = v
            
    def __check_missing__(self, x):
        """Quick check for valid missing field frame index value
        """
        return x is self.missingFieldFrameIndex if not isinstance(self.missingFieldFrameIndex, int) else x == self.missingFieldFrameIndex
    
    @property
    def map(self):
        return self._map_
    
    @map.setter
    def map(self, value):
        if not isinstance(value, pd.DataFrame):
            raise TypeError(f"Expecting a DataFrame; got {type(value).__name__} instead")
        
        if len(value.columns) != len(self._map_.columns) or not np.all(value.columns == self._map_.columns):
            raise ValueError(f"Expecting {self._map_.columns} columns; got {value.columns} instead")
        
        self._map_ = value

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
        
    
