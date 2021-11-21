""" Various utilities for handling objects and data structures in the neo package.
FIXME/TODO:: 2021-10-03 12:37:31 
Unit and ChannelIndex are deprecated in neo
Everything in here MUST reflect that!
0.9.0 and removed in neo 0.10.0
NOTE: 2020-10-07 09:45:08
Code split and redistributed in core.neoutils, ephys.ephys and core.triggerprotocols

The following functions are specific to this module:

I. Signal manipulations: assigning values to signal, signal intervals, or 
isolated signal samples; signal channels; spike trains
=============================================================================
assign_to_signal
assign_to_signal_in_epoch
batch_normalise_signals
batch_remove_offset
concatenate_blocks
concatenate_signals
set_relative_time_start
clear_events

II. Management of events, epochs, spike trains
===========================================================
clear_events
remove_events
get_epoch_named_interval
get_non_empty_epochs
get_non_empty_events
get_non_empty_spike_trains


III. Lookup functions
=====================
get_index_of_named_signal
get_non_empty_epochs
get_non_empty_events
get_non_empty_spike_trains
get_segments_in_channel_index -> removed 2021-10-03 12:52:25
get_signal_names_indices
get_time_slice
inverse_lookup
is_same_as
lookup
normalized_signal_index
normalized_segment_index


IV. Generic indexing for the neo framework (provisional)
========================================================
    Structured indices:
    
    child_collection_name is obtained by calling neo_child_container_name(...)
    
        it can be a 
        
        data_child_collection_name (sequence of data objects), 
        
        or a
        
        container_child_collection_name (sequence of container objects)
        
        In both cases these are prescribed attribute names of 
        neo.container.Container objects.
    
    indices = an iterable of int (i.e., tuple, list or range), NOT a slice
    
    root container: a top level neo container object (neo.container.Container)
    
    subcontainer: a neo container object that is contained in another neo container.
    
    containment of neo objects can be:
    
    a) direct containment: the neo object is an element of a sequence of neo 
        objects of the same type, and this sequence is a member (attribute) of 
        a neo.container.Container object. 
        
        For example, a neo.AnalogSignal object is an element of "analogsignals", 
        which is a member of a neo.Segment object: the Segment object contains 
        the AnalogSignal object "directly"; the AnalogSignal object is contained
        "directly" by the Segment object.
        
        The Segment object is the "root" container; the search for the neo 
        object starts with the root.
        
    b) indirect containment: a neo object is contained in a neo container which
        itself is directly contained by a root neo container.
        
        For example:
        
        A neo.AnalogSignal object is directly contained by a neo.Segment object,
        and the Segment object is directly contained by a neo.Block object.
        
        Therefore the AnalogSignal object is contained indirectly by the Block.
        
        The Block object is the "root" (top level) container, and the Segment 
        object is a sub container. 
        
        There can be more than one level of indirect containment (see the 
        composition hierarchy schematics below).
    
    Below, child_collection_name is specific for the type of neo object that
    if looked up _for_
    
    
    
    NOTATION:
    ========
    container: a neo.Container
    
    contained type: a type that is an element of a member collection
    
    member: an attribute of a type instance (gettable by calling getattr)
    
    member collection  = sequence (list or tuple) of objects, that is
    a member of a neo.Container
    
    COMPOSITION HIERARCHIES for neo 0.8.0
    =====================================
    Data object containers are specialized on the types of data object they
    may contain. The neo library allows for a data object type to be
    simultaneously contained in different types of container objects.
    
    The top-level container in neo library is a Block. However, data
    objects are never direcly contained in a block. Instead, a Block
    instance is composed of iterable collections of container objects. In 
    turn, each container object in the collection is composed of collections
    of data objects.
    
    In short, objects in the neo library are never directly contained. Instead,
    tey are stored in appropriate collection of objects with the same type.
    
    For example, neo.AnalogSignal objects are contained in a list which can
    be a member of a neo.Container instance, either a Segment, or a
    ChannelIndex (or both).
    
    Therefore, analog signals have two types of parents: Segment and 
    ChannelIndex, and both of these are in turn contained in collection members
    of a Block instance. The composition hierarchy looks like a diamond:
    
                         AnalogSignal                                    
                    IrregularlySampledSignal                                    
                         DataSignal                                    
                  IrregularlySampledDataSignal                                    
                        /               \                                     
                       /                 \                                     
                      /                   \                                     
                     /                     \                                    
                    /                       \                                    
    Segment.analogsignals             ChannelIndex.analogsignals                                    
    Segment.irregularlysampledsignals ChannelIndex.irregularlysampledsignals                                    
                    \                        /                                    
                     \                      /                                    
                      \                    /                                    
                       \                  /                                    
                        \                /                                    
                Block.segments        Block.channel_indexes                                    
                           \           /                                    
                            \         /                                    
                               Block                                    
        
    
    Likewise, neo.SpikeTrain objects can only be found in th member list of
    of a Segment (Segment.spiketrains) or a Unit. Unit is a Container which 
    is only contained in a ChannelIndex (although it can be also accessed in
    read-only mode from a Block). The composition hierarchy looks like this:
        
                      SpikeTrain    
                    /            \ 
                   /              \ 
                  /                \ 
                 /                  \
                /                    \
        Segment.spiketrains         Unit.spiketrains
                \                     |            \
                 \                    |             \   
                  \            ChannelIndex.units    \
                   \                 /                \
                    \               /                 |
              Block.segments  Block.channel_indexes   |
                      \           /                   |
                       \         /                    |
                          Block  - - - - - Block.list_units
                          
        
    For all other BaseSignal types there a direct (linear) composition 
    hierarchy:
        
              ImageSequence, Epoch, Event
                            |
                            |
                            |
             Segment member colection name: 
             imagesequences, epochs, events
                            |
                            |
                            |
                          Block
        
    And also for other neo object types:
        
                     RegionOfInterest
                            |
                            |
                            |
                  Block.regionsofinterest
                            |
                            |
                            |
                          Block
        
        
    As a design decision, when the container is a Block and we lookup a
    neo.AnalogSignal, we traverse the container's Segments.
    When the container if another container (which for a signal can 
    only be a ChannelIndex) when then get directly to its analogsignals
    member collection.
    
    For information, these are the INHERITANCE HIERARCHIES in neo:
    ==============================================================
         object
           |
           V
        BaseNeo
           |                    pq.Quantity
           |\                       |
           | \                      V
           |  ----------------> DataObject -------> BaseSignal
           |                        |                   |        
           V                        V                   V    
        Container               Epoch               AnalogSignal    
           |                    Event               IrregularlySampledSignal
           V                    SpikeTrain          ImageSequence
        Block                                       
        Segment                                     
        Unit                                        outside neo, in scipyen:
        ChannelIndex                                dataypes.DataSignal
                                                    datatypes.IrregularlySampledDataSignal

        object --> RegionOfInterest ------> RectangularRegionOfInterest,
                                            CircularRegionOfInterest,
                                            PolygonRegionOfInterest

    Case 1: index of neo objects in a generic python sequence of object of the
    same type:
    ============================================================================
    returns:
        indices
    
    code:
    
        utilities.normalized_index(seq, index_obj) => tuple or range
    
    checks: 
    
    1) when index_obj is a str, or a sequence where at least one element is a
        str, check if the neo objects have a "name" attribute,  that "name" is
        not empty, and equals the value(s) in index_obj.
        
        if silent, return None for each str index_obj value that does not find
        a neo object with that name, and issue a warning
        
        otherwise, raise IndexError
    
    2) when index_obj is an int or a sequence where at least one element is an
        int, check the int values in index_obj are <= len(seq)
        
        if silent, return None for each of the invalid int values and issue a
        warning
        
        otherwise raise IndexError
        
    3) when index_obj is a range, check that 0 < len(index_obj) <= len(seq)
    
        if silent, return (None,) otherwise raise IndexError
    
    4) when index_obj is a slice, check that len(index_obj.indices(len(seq))) > 0
        is silent return (None,) otherwise raise IndexError.
    
    
    Case 2: index of neo objects contained directly in a neo.Container 
    ("root container" can be a Block, a Segment, a ChannelIndex, or a Unit):
    ============================================================================
    
    returns:
        {child_collection_name0: indices, 
         child_collection_name1: indices,
         etc...}
    
    child_collection_name can refer to a data child, or a container child.
    
    There is one child_collection_name for each type of object that is being
    looked up
    
    Root container type:    data child collection:     container child collection:
    -----------------------------------------------------------------------------
    Segment                 "analogsignals", 
                            "irregularlysampledsignals", 
                            "imagesequences", 
                            "spiketrains", 
                            "epochs", 
                            "events"
                                    
    ChannelIndex            "analogsignals"             "units"
    
    Unit                    "spiketrains"
    
    Block                                               "segments"
                                                        "channel_indexes"
                                                        "list_units" - read-only!
    
    code :
        for each object type call silently
            setup child_collection_name
            execute Case 1 for getattr(container, child_collection_name)
                                       
            if child_collection_name is appropriate and call was successful then
                map child_collection_name (key) to the return from the call (value)
                               
    checks:
    
        in addition to case 1: data_child_collection_name is an attribute of container.
    
    
    Case 3: index of neo objects in a generic python sequence of containers 
    (each container contains the objects directly)
    ============================================================================
    
    returns:
        {index0: {child_collection_name0: indices, 
                  child_collection_name1:indices,
                  etc...}, 
         index1: {...},
         etc...}
     
    index0, index1, etc: indices of the container in the sequence where the 
            lookup was successful
     
    These indices are not necessarily the same as Segment.index or ChannelIndex
    value! Instead they are the indices of said objects in the collection where
    the lookup takes place.
    
    code:
        for each container in seq enumeration:
            execute Case 2 => "inner" dict
                    
            if result not empty:
                map container index in enumeration (key) to result (value)
                
    checks:
        all checks of Case 2, for each member of seq
    
    
    Case 4: search objects contained indirectly in root container (nested search)
    ============================================================================
    
    returns:
    
    {container_collection_name0: {index0 : {child_collection_name0: indices,
                                            child_collection_name1: indices,
                                            etc...},
                                  index1 : {...},
                                  etc...},
     container_collection_name0: {...},
     etc...}
     
    NOTE: there can be more than one container child collection in case of 
    "diamond" composition hierarchy.
     
     
    code:
        for each obj_type:
            if hasattr(container, neo_child_container_name(obj_type)):
                # find out if object type is contained directly in this container
                # we use our own function which covers more possibilities than
                # neo.container.Container._data_child_containers and
                # neo.container.Container._container_child_containers
                #
                # first, these two functions would have to be called separately
                # (or distinctly) for neo data objects and neo container objects
                #
                # second, neo_child_container_name also takes into account
                # RegionOfInterest objects (currently only neo.Block can have these)
                
                execute Case 2 on getattr(container, neo_child_container_name(obj_type)
                
                map key = neo_child_container_name(obj_type) to
                    value = result
                
            else: 
                if hasattr(container, neo_child_property_name(obj_type)):
                    # find out if object type is contained child_properties
                    # (currently only Block has "Units" among its child_properties,
                    # referenced as "list_units"; for all other container types 
                    # _child_properties is an empty tuple, but this may change)
                    # also we use neo_child_property_name for a more generic coverage
                    # (see comments above)
                    
                    execute Case 2 on getattr(container, neo_child_property_name(obj_type))
                    
                    map key = neo_child_property_name(obj_type) to
                        value = result
                    
                else:
                    # obj_type not found in either child containers or in child
                    # properties - we need to descend one level into the current 
                    # chid containers & properties of container
                    
                    for each container_type in obj_type._single_parent_objects:
                    
                        if hasattr(container, neo_child_container_name(container_type)):
                            execute Case 2 on getattr(container, neo_child_container_name(container_type))
                            map key = neo_child_container_name(container_type) to
                                value = result
                            
                        elif hasattr(container, neo_child_property_name(container_type)):
                            execute Case 2
                            map key = neo_child_property_name(container_type) to
                                value = result
                                
                        else:
                            continue
                
                for each discovered container collection name:
                    execute Case 3 on getattr(container, container_collection_name)
                    
                    map contained_collection_name (key) to result (value)
        
            
    checks:
        
    
    
    Case 5: Case 3 with indirect containment
    ========================================
    
    For spike trains in a sequence of ChannelIndex, one may also select the units:
    
    {index0: {container_child_collection_name: {nested_index0:{data_child_collection_name: indices}}},
     index1: {...},
     etc...}
     
     Here index0/1/etc: indices of the channel index in the sequence
          nested_index0/1/etc: indices of the Units

        
    Example 5: nested index of signal in a Block
    =============================================
    {container_child_collection_name: {index0: {data_child_collection_name: indices},
                                      index1: {...},
                                      etc... },
                                        
    for analog signals, should indicate preference between "segments" and "channel_indexes"
        default is "segments"
    
    for spike trains, should indicate preference between "segments" and "units"
        default is "segments"
        if "units", this implies traversing "channel_indexes" if looking up in
        a Block
    

    Example 6: nested index of signal in a sequence of blocks
    =========================================================
    {index1:    {"segments": {index1: {child_collection_name: indices},
                              index2: {...},
                              etc... },
                 "channel_indexes": {index: {child_collection_name: indices}, 
                                     etc... }},
     index2:    {"segments": {index1: {child_collection_name: indices},
                              index2: {...},
                              etc... },
                 "channel_indexes": {index: {child_collection_name: indices}, 
                                     etc... }},
     etc...}
    



"""
#### BEGIN core python modules
import traceback, datetime, numbers, inspect, warnings, typing, types
from collections import deque
import collections.abc
import operator
from itertools import chain, filterfalse
from functools import (partial, reduce, singledispatch)
from copy import deepcopy
from enum import (Enum, IntEnum,)
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import quantities as pq
import neo
from neo.core.baseneo import (MergeError, merge_annotations, intersect_annotations)
from neo.core.dataobject import (DataObject, ArrayDict)
import matplotlib as mpl
import pyqtgraph as pg
#### END 3rd party modules

#### BEGIN pict.core modules
#from . import plots
from .prog import (safeWrapper, deprecation, 
                   filter_attr, filterfalse_attr,
                   filter_type, filterfalse_type,
                   iter_attribute)

from .datatypes import (is_string, is_vector,
                        RELATIVE_TOLERANCE, ABSOLUTE_TOLERANCE, EQUAL_NAN,)

from .quantities import units_convertible, check_time_units

from .datasignal import (DataSignal, IrregularlySampledDataSignal,)

from .triggerevent import (TriggerEvent, TriggerEventType,)

from . import workspacefunctions
from . import signalprocessing as sigp
from . import utilities
from core.utilities import (normalized_index, name_lookup, elements_types, index_of)

#from .patchneo import neo


#### END pict.core modules

ephys_data = (neo.Block, neo.Segment, neo.AnalogSignal, neo.IrregularlySampledSignal, 
              neo.SpikeTrain, DataSignal, IrregularlySampledDataSignal,
              )

ancillary_neo_data = (neo.ImageSequence, neo.Event, neo.Epoch)

ephys_data_collection = (neo.Block, neo.Segment)#, neo.Unit)
#ephys_data_collection = (neo.Block, neo.Segment, neo.Unit)

# NOTE: 2021-10-13 12:44:51
# the below is on its way out!
type_to_container_member_name = {
    neo.Segment: {
        DataSignal: "analogsignals",
        IrregularlySampledDataSignal: "irregularlysampledsignals",
        neo.AnalogSignal: "analogsignals",
        neo.IrregularlySampledSignal: "irregularlysampledsignals",
        neo.SpikeTrain: "spiketrains",
        neo.Event: "events",
        neo.Epoch: "epochs",
        neo.ImageSequence: "imagesequences",
        },
    neo.Block: {
        neo.RectangularRegionOfInterest: "regionsofinterest",
        neo.CircularRegionOfInterest: "regionofinterest",
        neo.PolygonRegionOfInterest: "regionsofinterest",
        neo.Segment: "segments",
        neo.Group: "groups",
        },
    neo.Group: {
        neo.Segment: "segments",
        DataSignal: "analogsignals",
        IrregularlySampledDataSignal: "irregularlysampledsignals",
        neo.AnalogSignal: "analogsignals",
        neo.IrregularlySampledSignal: "irregularlysampledsignals",
        neo.SpikeTrain: "spiketrains",
        neo.Event: "events",
        neo.Epoch: "epochs",
        neo.ImageSequence: "imagesequences",
        },
    }

#type_to_container_member_name = {
    #neo.Segment: {
        #DataSignal: "analogsignals",
        #IrregularlySampledDataSignal: "irregularlysampledsignals",
        #neo.AnalogSignal: "analogsignals",
        #neo.IrregularlySampledSignal: "irregularlysampledsignals",
        #neo.SpikeTrain: "spiketrains",
        #neo.Event: "events",
        #neo.Epoch: "epochs",
        #neo.ImageSequence: "imagesequences",
        #},
    #neo.Block: {
        #neo.RectangularRegionOfInterest: "regionsofinterest",
        #neo.CircularRegionOfInterest: "regionofinterest",
        #neo.PolygonRegionOfInterest: "regionsofinterest",
        #neo.Segment: "segments",
        #neo.ChannelIndex: "channel_indexes",
        #neo.Group: "groups",
        #neo.Unit: "list_units",
        #},
    #neo.Unit: {
        #neo.SpikeTrain: "spiketrains",
        #},
    #neo.Group: {
        #neo.Segment: "segments",
        #DataSignal: "analogsignals",
        #IrregularlySampledDataSignal: "irregularlysampledsignals",
        #neo.AnalogSignal: "analogsignals",
        #neo.IrregularlySampledSignal: "irregularlysampledsignals",
        #neo.SpikeTrain: "spiketrains",
        #neo.Event: "events",
        #neo.Epoch: "epochs",
        #neo.ImageSequence: "imagesequences",
        #},
    #}


if __debug__:
    global __debug_count__

    __debug_count__ = 0
    
##@singledispatch
#def get_container_elements(container:neo.core.container.Container, 
                           #index:typing.Union[int, str, tuple, list, range, slice, collections.abc.Iterable],
                           #) -> typing.Sequence:
    #if isinstance(index, (int, slice)):
        #ret = container[index]
        
        #if isinstance(index, int):
            #return [ret]
        #return ret
    
    #if isinstance(index, range):
        #return [container[k] for k in index]
    
    #if isinstance(index, str):
        #indices = index_of([obj.name for obj in container], index, 
                           #multiple=True, comparator = operator.eq)
        
        #return [container[k] for k in indices]
    
    #if isinstance(index, (tuple, list)):
        #if all(isinstance(v, int) for v in index):
            #return [container[v] for v in index]
        
        #elif all(isinstance(v, str) for v in index):
            #return list(chain.from_iterable([[container[k] for k in index_of([o.name for o in container], name, multiple=True, comparator=operator.eq)] for name in index]))
    
        #else:
            #raise TypeError("When 'index' is a sequence it must contain str or int elements")
    #else:
        #raise TypeError("'index' expected to be an int, str, tuple, list, range, slice, or a sequence of int or str")
    
#def normalize_index_to_container(container:neo.core.container.Container, 
                           #index:typing.Union[int, str, tuple, list, range, slice, types.Iterable],
                           #) -> typing.Sequence:
    #if isinstance(index, int):
        #if index < -len(container) or index >= len(container):
            #raise IndexError(f"{type(index).__name__} 'index' {index} out of range for {type(container).__name__} 'container' with {len(container)} elements")
        
        #return index
    
    #if isinstance(index, slice):
        #return range(index.indices(len(container)))
    
    #if isinstanc
    
    #if isinstance(index, str):
        #return index_of([o.name for o in container], index,
                        #multiple=True, comparator=operator.eq)
    
        #ret = container[index]
        
        #if isinstance(index, int):
            #return [ret]
        #return ret
    
    #if isinstance(index, range):
        #return [container[k] for k in index]
    
    #if isinstance(index, str):
        #indices = index_of([obj.name for obj in container], index, 
                           #multiple=True, comparator = operator.eq)
        
        #return [container[k] for k in indices]
    
    #if isinstance(index, (tuple, list)):
        #if all(isinstance(v, int) for v in index):
            #return [container[v] for v in index]
        
        #elif all(isinstance(v, str) for v in index):
            #return list(chain.from_iterable([[container[k] for k in index_of([o.name for o in container], name, multiple=True, comparator=operator.eq)] for name in index]))
    
        #else:
            #raise TypeError("When 'index' is a sequence it must contain str or int elements")
    #else:
        #raise TypeError("'index' expected to be an int, str, tuple, list, range, slice, or a sequence of int or str")
    

def copy_to_segment(obj:neo.core.dataobject.DataObject, new_seg:neo.Segment):
    new_obj = obj.copy()
    new_obj.segment = new_seg
    
    return new_obj
    
def merge_array_annotations(a0:ArrayDict, a1:ArrayDict):
    if not all(isinstance(a, (ArrayDict, dict)) for a in (a0,a1)):
        raise TypeError("Expecting two neo.core.dataobject.ArrayDict objects")
    
    merged_array_annotations = {}
    omitted_keys_a0 = []
    # Concatenating arrays for each key
    
    for key in a0:
        #length = len(a0[key])
        try:
            value = deepcopy(a0[key])
            other_value = deepcopy(a1[key])
            # Quantities need to be rescaled to common unit
            if isinstance(value, pq.Quantity):
                try:
                    other_value = other_value.rescale(value.units)
                except ValueError:
                    raise ValueError("Could not merge array annotations "
                                        "due to different units")
                merged_array_annotations[key] = np.append(value, other_value) * value.units
            else:
                merged_array_annotations[key] = np.append(value, other_value)
                
            #length = len(merged_array_annotations[key])

        except KeyError:
            # Save the  omitted keys to be able to print them
            omitted_keys_a0.append(key)
            continue
    # Also save omitted keys from 'other'
    omitted_keys_a1 = [key for key in a1 if key not in a0]

    # Warn if keys were omitted
    if omitted_keys_a1 or omitted_keys_a0:
        warnings.warn("The following array annotations were omitted, because they were only "
                        "present in one of the merged objects: {} from the one that was merged "
                        "into and {} from the one that was merged into the other"
                        "".format(omitted_keys_a0, omitted_keys_a1), UserWarning)

    # Return the merged array_annotations
    length = max(len(v) for v in merged_array_annotations.values())
    ret = ArrayDict(length)
    for k,v in merged_array_annotations.items():
        ret[k] = v
    
    return ret
    
    
def combine_time_ranges(time_ranges):
    """This is neo.AnalogSignal._concatenate_time_ranges()
    Copied here for use with DataSignal object too
    """
    time_ranges = sorted(time_ranges)
    new_ranges = time_ranges[:1]

    for t_start, t_stop in time_ranges[1:]:
        if t_start > new_ranges[-1][1]:
            new_ranges.append((t_start, t_stop))
        
        elif t_stop > new_ranges[-1][1]:
            new_ranges[-1] = (new_ranges[-1][0], t_stop)
            
    return new_ranges

def invert_time_ranges(time_ranges):
    """This is neo.AnalogSignal._invert_time_ranges()
    """
    i=0
    new_ranges = list()
    while i < len(time_ranges)-1:
        new_ranges.append((time_ranges[i][1], time_ranges[i+1][0]))
        i += 1
        
    return new_ranges
    
    
    
def get_member_collections(container:typing.Union[type, neo.core.container.Container],
                           membertype:typing.Union[type, tuple, list]) -> list:
    if isinstance(container, type):
        if not neo.core.container.Container in inspect.getmro(container):
            raise TypeError("Cannot handle %s" % container)
        
        if container not in type_to_container_member_name.keys():
            raise TypeError("Cannot handle %s" % container)
        
        cont_type = container
        
    else:
        cont_type = type(container)
        
        if not neo.core.container.Container in inspect.getmro(cont_type):
            raise TypeError("Cannot handle container with type" % cont_type)
        
        if cont_type not in type_to_container_member_name.keys():
            raise TypeError("Cannot handle container with type" % cont_type)
        
    cont_dict = type_to_container_member_name[cont_type]
    
    if isinstance(membertype, (tuple, list)) and all([isinstance(t, type) and t in cont_dict.keys() for t in membertype]):
        attrnames = [cont_dict[t] for t in membertype]
        
    #elif isinstance(membertype, type) and membertype in 

def get_neo_version() -> tuple:
    major, minor, dot = neo.version.version.split(".")
    return eval(major), eval(minor), eval(dot)

@safeWrapper
def assign_to_signal(dest:neo.AnalogSignal, src:[neo.AnalogSignal, pq.Quantity], 
                     channel:[int, type(None)]=None):
    """Assigns values in src to values in dest, for the specified channel, or all channels
    
    Parameters:
    ==========
    dest: destination AnalogSignal
    
    src: source AnalogSignal or a scalar python quantity with same units as dest
    
        when source is an AnalogSignal, its time domain must be WITHIN or 
        equal to the destination time domain
            
    channel int or None; when int it must point to a valid channel index into both signals
    
    """
    if not isinstance(dest, neo.AnalogSignal):
        raise TypeError("dest expected to be an AnalogSignal; got %s instead" % (type(dest).__name__))

    if isinstance(src, neo.AnalogSignal):
        if src.t_start < dest.t_start:
            raise ValueError("Source signal starts (%s) before destination signal (%s)" % (src.t_start, dest.t_start))
        
        if src.t_stop > dest.t_stop:
            raise ValueError("Source signal stops (%s) after destination signal (%s)" % (src.t_stop, dest.t_stop))
        
        if src.units != dest.units:
            raise TypeError("Mismatch between destination unts (%s) and source units (%s)" % (dest.units, src.units))
    
        ndx = np.where((dest.times >= src.t_start) & (dest.times < src.t_stop))
        
        if channel is None:
            dest[ndx[0],:] = src[:,:]
            
        else:
            dest[ndx[0],channel] = src[:,channel]

    elif isinstance(src, pq.Quantity) and src.units == dest.units:# and src.size == 1:
        if channel is None:
            dest[:,:] = src
            
        else:
            dest[:,channel] = src
            
    elif isinstance(src, np.ndarray) and is_vector(src):
        # TODO
        if channel is None:
            pass
        else:
            pass
        
            
    else:
        raise TypeError("source expected to be an AnalogSignal or a scalar python quantity of same units as destination")
    
        
@safeWrapper
def assign_to_signal_in_epoch(dest:neo.AnalogSignal, 
                              src:[neo.AnalogSignal, pq.Quantity], 
                              epoch:neo.Epoch, 
                              channel:[int, type(None)] = None):
    """Assigns values in src to values in dest, within an epoch, for the specified channel, or all channels
    """
    
    if not isinstance(dest, neo.AnalogSignal):
        raise TypeError("dest expectyed to be an AnalogSignal; got %s instead" % (type(dest).__name__))

    if not isinstance(epoch, neo.Epoch):
        raise TypeError("epoch expected to be a neo.Epoch; got %s instead" % (type(epoch).__name__))
    
    if isinstance(src, neo.AnalogSignal):
        if src.t_start < dest.t_start:
            raise ValueError("Source signal starts (%s) before destination signal (%s)" % (src.t_start, dest.t_start))
        
        if src.t_stop > dest.t_stop:
            raise ValueError("Source signal stops (%s) after destination signal (%s)" % (src.t_stop, dest.t_stop))
    
        if src.units != dest.units:
            raise TypeError("Mismatch between destination unts (%s) and source units (%s)" % (dest.units, src.units))
    
        if any([t < dest.t_start for t in epoch.times]):
            raise ValueError("Epoch cannot start before destination")
        
        if any([(epoch.times[k] + epoch.durations[k]) > dest.t_stop for k in range(len(epoch))]):
            raise ValueError("Epoch cannot extend past destination end")
        
        if any([t < src.t_start for t in epoch.times]):
            raise ValueError("Epoch cannot start before source")
    
        if any([(epoch.times[k] + epoch.durations[k]) > src.t_stop for k in range(len(epoch))]):
            raise ValueError("Epoch cannot extend past source end")
        
        for k in range(len(epoch)):
            src_ndx = np.where((dest.times >= epoch.times[k]) & (dest.times < (epoch.times[k] + epoch.durations[k])))
            
            dest_ndx = np.where((src.times >= epoch.times[k]) & (src.times < (epoch.times[k] + epoch.durations[k])))
    
            if len(src_ndx[0]) != len(dest_ndx[0]):
                raise RuntimeError("Mismatch array lenghts")
            
            if channel is None:
                dest[dest_ndx[0],:] = src[src_ndx[0],:]
                
            else:
                dest[dest_ndx[0], channel] = srdc[src_ndx[0], channel]
                
    elif isinstance(src, pq.Quantity) and src.units == dest.units and src.size == 1:
        if any([t < dest.t_start for t in epoch.times]):
            raise ValueError("Epoch cannot start before destination")
        
        if any([(epoch.times[k] + epoch.durations[k]) > dest.t_stop for k in range(len(epoch))]):
            raise ValueError("Epoch cannot extend past destination end")
        
        for k in range(len(epoch)):
            dest_ndx = np.where((dest.times >= epoch.times[k]) & (dest.times < (epoch.times[k] + epoch.durations[k])))
            
            if channel is None:
                dest[dest_ndx[0],:] = src
                
            else:
                dest[dest_ndx[0], channel] = src
                
    else:
        raise TypeError("source expected to be an AnalogSignal or a scalar python quantity of same units as destination")
    
    
@safeWrapper
def get_signal_names_indices(data: typing.Union[neo.Segment, typing.Sequence],
                             analog: bool = True) -> typing.List[str]:
    """Returns a list of analog signal names in data.
    
    Produces a list of signal names in the data; for signals that do not have a
    name ('name' attribute is either None or the empty string after stripping 
    blank characters) the list contains a string representation of the signal
    indices in the data in the form of "signal_k" where "k" stands for the signal
    iteration index; signals with "name" attribute that is not a string will
    be treated similarly.
    
    NOTE: here, signal "indices" represent their position in the signal collection
    in the data, in iteration order and should not be confused with the signal's 
    "index" attribute (whch has a totally different mreaning in neo library).
    
    The function is useful especially for GUI programming when a list of signal 
    names may be used for populating a combo box, for instance.
    
    Parameters:
    ==========
    
    data: a neo.Segment, or a sequence of neo.AnalogSignal, datatypes.DataSignal, 
            and/or neo.IrregularlySampledSignal objects
    
    analog: boolean, default True: returns the names/indices of analosignals and
            datasignals otherwise returns the names/indices of irregularly 
            sampled signals
            
            used only when data is a neo.Segment (as it may contain either of the above)
    
    """
    if isinstance(data, neo.Segment):
        if analog:
            if not hasattr(data, "analogsignals"):
                return list()
            
            signals = data.analogsignals
            
        else:
            if not hasattr(data, "irregularlysampledsignals"):
                return list()
            
            signals = data.irregularlysampledsignals
        
    elif isinstance(data, (tuple, list)):
        if all([isinstance(s, (neo.AnalogSignal, DataSignal, neo.IrregularlySampledSignal, IrregularlySampledDataSignal)) for s in data]):
            signals = data
            
        else:
            raise TypeError("The sequence should contain only neo.AnalogSignal, datatypes.DataSignal and neo.IrregularlySampledSignal objects")

    else:
        raise TypeError("Expecting a neo.Segment or a sequence of neo.AnalogSignal, datatypes.DataSignal and neo.IrregularlySampledSignal objects; got %s instead" % type(data).__name__)
    
    sig_indices_names = [[k, sig.name] for k, sig in enumerate(signals)]
    
    #print("sig_indices_names", sig_indices_names)
    
    for k in range(len(signals)):
        if sig_indices_names[k][1] is None or not isinstance(sig_indices_names[k][1], str) or len(sig_indices_names[k][1].strip()) == 0:
            sig_indices_names[k][1] = "signal_%d" % sig_indices_names[k][0]
            
    return [item[1] for item in sig_indices_names]
    
def normalized_segment_index(src: neo.Block,
                             index: typing.Union[int, str, range, slice, typing.Sequence]):
    """Returns integral indices of a Segment in a neo.Block or list of Segments.
    """
    
    if isinstance(src, neo.Block):
        src = src.segments
        
    elif isinstance(src, neo.Segment):
        src = [src]
        
    elif not isinstance(src, (tuple, list)) or not all([isinstance(s, neo.Segment) for s in src]):
        raise TypeError("src expected to be a neo.Block, a sequence of neo.Segments, or a neo.Segment; got %s instead" % type(src).__name__)
    
    data_len = len(src)
    
    if isinstance(index, (int, range, slice, np.ndarray, type(None))):
        return normalized_index(data_len, index)
    
    elif isinstance(index, str):
        if slient:
            return utilities.silentindex([i.name for i in src], index)

        return [i.name for i in src].index(index)
    
    elif isinstance(index, (tuple, list)):
        indices = list()
        
        for ndx in index:
            if isinstance(ndx, int):
                indices.append(normalized_index(data_len, ndx))
                
            elif isinstance(ndx, str):
                if silent:
                    indices.append(utilities.silentindex([i.name for i in src], ndx))
                    
                else:
                    indics.append([i.name for i in src].index(ndx))
                    
            else:
                raise TypeError("Invalid index element type %s" % type(ndx).__name__)
        return indices
    
    else:
        raise TypeError("Invalid indexing: %s" % index)
    
#def neo_child_property_name(type_or_obj):
    #"""Provisional.OBSOLETE
    #As of neo 0.8.0 this only works for neo.Unit, in neo.Block
    #"""    
    #return "list_%s" % neo_child_container_name(type_or_obj)

def neo_child_container_name(type_or_obj):
    """Provisional: name of member collection.
    Returns a valid child container name; doesn't tell is a container actually
    HAS these children
    """
    if inspect.isclass(type_or_obj):
        if neo.regionofinterest.RegionOfInterest in inspect.getmro(type_or_obj):
            return "regionsofinterest"
        
        else:
            return neo.baseneo._container_name(type_or_obj.__name__)
        
    elif isinstance(type_or_obj, str):
        if type_or_obj in dir(neo.regionofinterest):
            return "regionsofinterest"
        
        else:
            return neo.baseneo._container_name(type_or_obj)
        
    else:
        if isinstance(type_or_obj, neo.regionofinterest.RegionOfInterest):
            return "regionsofinterest"
        
        else:
            return neo.baseneo._container_name(type(type_or_obj).__name__)
            
        
def __get_container_collection_attribute__(container, attrname,
                                           container_index=None,
                                           multiple=True):
    
    ret = getattr(container, attrname, None)
    
    if container_index is None:
        return [(k, c) for k, c in enumerate(ret)]
    
    else:
        return [(k, ret[k]) for k in normalized_index(len(ret), container_index, multiple=multiple)]
            
def __container_lookup__(container: neo.container.Container, 
                         index_obj: typing.Union[str, int, tuple, list, np.ndarray, range, slice],
                         contained_type: neo.baseneo.BaseNeo,
                         multiple:bool = True, 
                         return_objects:bool = False,
                         **kwargs) -> dict:
    """
    Lookup and optionally return children of specified contained_type 
    inside a neo.container.Container.
    
    What we want:
    
    given a neo.Block b, we want to know the index of analog signals with 
    specific names and extract them.
    
    We may specify the signal index as a tuple of ints
    
    Since the neo API is a moving goal post this is rewritten as of 
    2021-10-12 17:30:30 and the module docstring is outdated & obsolete.
    
    Basically DO NOT rely on ANY class or instance attrobutes that start with '_'
    in the neo hierarchy!!!
    
    Cases 2 & 4       
    """
    # 1) check if the container's type is among the contained_type._parent_objects
    
    if isinstance(container, neo.container.Container):
        pfun0 = partial(normalized_index, index=index_obj, multiple=multiple)
        
        signal_collection_name = neo_child_container_name(contained_type)
        #member_collection_names = [neo_child_container_name(contained_type), neo_child_property_name(contained_type)]
        
        collection = getattr(container, signal_collection_name, None)
        
        if collection is None:
            container_children = container.container_children
            ret = dict((type(c).__name, list()) for c in container_children)
            
            
            
            
        
        if collection is not None:
            t = pfun0(collection)
            if len(t):
                if return_objects:
                    ret = {signal_collection_name: t}
                else:
                    ret = {signal_collection_name: [collection[t_] for t in t]}
                    
            else:
                return dict()
            
        
    
        
        #member_collections = [getattr(container, cname, None) for cname in member_collection_names]
            
        ret = dict((cname, t) for cname, t in zip(member_collection_names, map(pfun0, member_collections)) if len(t) > 0)
        
        if len(ret) == 0:
            # might by indirectly contained
            # this is where additional index objects for collection of data that may be in kwargs should be applied
            
            direct_containers = contained_type._parent_containers
            #direct_containers = contained_type._single_parent_objects # removed in neo 0.10.0
            
            child_container_names = [neo_child_container_name(c) for c in direct_containers]
            
            child_container_collections = [getattr(container, cname, None) for cname in child_container_names]
            
            child_container_collections2 = [__get_container_collection_attribute__(container, cname, kwargs.get(cname, None)) for cname in child_container_names]
            
            pfun = partial(__collection_lookup__, 
                                    index_obj = index_obj,
                                    contained_type = contained_type,
                                    multiple = multiple,
                                    return_objects = return_objects)
            
            ret = dict((cname, d) for cname, d in zip(child_container_names, map(pfun, child_container_collections)) if len(d) > 0)
            
        return ret

    raise TypeError(f"Expecting a neo.Container; got {type(container).__name__} instead.")
        
def __collection_lookup__(seq: typing.Sequence, 
                          index_obj: typing.Union[str, int, tuple, list, np.ndarray, range, slice],
                          contained_type: neo.baseneo.BaseNeo,
                          seq_index: typing.Optional[typing.Union[int, tuple, list, range, slice]] = None,
                          multiple:bool = True, 
                          return_objects:bool = False,
                          **kwargs) -> dict:
    """ Case 3
    """
    if seq is None:
        return dict()
    
    pfun = partial(__container_lookup__, 
                             index_obj = index_obj,
                             contained_type = contained_type, 
                             multiple = multiple,
                             return_objects = return_objects)
    
    if seq_index is None:
        return dict((k, d) for k, d in enumerate(map(pfun, seq)) if len(d) > 0 and any([len(val) > 0 for key, val in d.items()]))
    
    elif isinstance(seq_index, (tuple, list, range)) and all([isinstance(v, int) for v in seq]):
        k_ = [k for k in seq_index]
        seq_ = [seq[k] for k in k_]
        
        return dict((k, d) for k, d in zip(map(pfun, seq), k_) if len(d) > 0 and any([len(val) > 0 for key, val in d.items()]))
    
    elif isinstance(seq_index, slice):
        k_ = [k for k in seq_index.indices(len(seq))]
        seq_ = seq[seq_index]
        
        return dict((k, d) for k, d in zip(map(pfun, seq), k_) if len(d) > 0 and any([len(val) > 0 for key, val in d.items()]))
    
    else:
        return dict()
    
def is_empty(x:typing.Union[neo.core.container.Container, neo.core.dataobject.DataObject, 
                            typing.Sequence[typing.Union[neo.core.container.Container,neo.core.dataobject.DataObject]]],
            ignore:typing.Optional[typing.Union[typing.Sequence[type], type]]=None):
    """Checks whether x contains any data.
    Parameters:
    ==========
    x: neo container or data object
    ignore: type, sequence of types, optional (default is None)
        When present and 'x' is a neo container, the children containers or data
            objects of the type given in ignore are NOT considered when checking 
            if 'x' is empty (helpful, e.g., when checking if, say, a neo.Block
            contains any signals aprt from events, or spike trains, etc.)
            
            NOTE: This parameter is only used for neo containers, not data objects
            (which by definition DO NOT have children containers or data objects)
    """
    if isinstance(ignore, type):
        ignore = [ignore]
    
    if ignore is not None:
        if not isinstance(ignore, (tuple, list)) or not all((isinstance(t, type) for t in ignore)):
            raise TypeError("'ignore' expected to be a type, a sequence of types;, or None got %s" % ignore)
        
    if isinstance(x, neo.core.container.Container):
        if ignore is None:
            container_children = x.container_children_recur
            data_children = x.data_children_recur
            
        else:
            container_children = tuple(c for c in x.container_children_recur if not isinstance(c, tuple(ignore)))
            data_children = tuple(c for c in x.data_children_recur if not isinstance(c, tuple(ignore)))
            
        ret = len(container_children) > 0 and len(data_children) > 0
            
        if ret:
            ret &= sum((len(c) for c in data_children))> 0
            
        return not ret
    
    elif isinstance(x, neo.core.dataobject.DataObject):
        return len(x) == 0
            
    
    elif isinstance(x, (tuple, list)) and all((isinstance(xx, (neo.core.container.Container, neo.core.dataobject.DataObject)) for xx in x)):
        return all((is_empty(xx, ignore=ignore) for xx in x))
    
    else:
        raise TypeError("Expecting a neo Container, DataObject or a sequence of these; got %s instead" % type(x).__name__)
    

        
def neo_lookup(*args: typing.Union[neo.core.container.Container, typing.Sequence[neo.core.container.Container]],
               data_obj_type: typing.Union[typing.Sequence[type], type] = neo.AnalogSignal,
               op = operator.and_, 
               indices:bool = False, 
               indices_only:bool = False,
               exclude: bool = False,
               **kwargs):
    """Enhanced filtering of child data objects inside neo containers.
    
    Looks up data objects by type and any combination of data object attributes
    inside a neo container (i.e., Block, Segment, or a sequence of these), 
    recursively.
    
    CAUTION: Use neo_lookup ONLY for this purpose.
    
    To select signals directly from a regular Python sequence, use prog.filter_attr()
    (poissibly in combination with prog.filter_type()).
    
    For a flat iterator for neo data objects, and when their indices inside the 
    container or sequence are irrelevant, use the
    neo.core.container.Container.filter() method or the 
    neo.core.container.filterdata() function.
    
    Returns a nested dictionary where the leaves are lists of child data objects,
    their indices in the corresponding data object collection, or tuples 
    (index, child data object).
    
    Below a 'sequence' denotes a collections.deque, list, or tuple.
    
    Parameters:
    ==========
    
    src: neo container (e.g, Block, Segment, Group) or sequence (collections.deque,
        list or tuple) of neo containers
        
    data_obj_type: type or sequence of type
    
    Returns:
    ========
    
    Nested indexing dictionary of the format:
        
        {container_type_collection_name (str):                      # e.g., 'blocks' or groups
            {container_type_index_0 (int):                          # e.g., 0, 1, ... index of containers in src
                {subcontainer_type_collection_name (str):           # either, 'segments', or 'groups'
                    {subcontainer_type_index_0 (int):               # e.g., 0,1,... index of segment in segmentsi.e., 
                        {signal_type_0_collection_name (str):       # e.g., 'analogsignals','spiketrains','events'
                            sequence of data objects, indices, or 
                            (index, data object) tuples} 
                    },
                    {subcontainer_type_index_0 (int):                
                        {signal_type_0_collection_name (str): 
                            tuple of objects } 
                    },
                    ... as many subcontainers found to contain specified data object type with specified attribute value
                        (NOTE: if both groups and segments are present, 
                        the data object will be returned twice!)
                },
                            
                {subcontainer_type_1_collection_name (str):         # max of two subcontainers: 'segments', 'groups'
                    {subcontainer_type_0_index (int): 
                        {signal_type_0_collection_name (str): 
                            tuple of objects } } 
                },
                
            } ,
    
            {container_index_1 (int): 
                {subcontainer_collection_name (str): 
                    {subcontainer_index (int): 
                        {signal_collection_name (str): 
                            tuple of objects } } } }, 
                            
        ... etc ... for as many containers in src, where src is a container sequence

        }
        
    Example 1: 
    ========
    Let ephysdata_src a neo.Block with three segments. We look for the analog 
    signals named "Im_prim2":

    >>> neoutils.neo_lookup(ephysdata_src, name="Im_prim2")

    {'blocks': 
        {0: 
            {'segments': 
                {0: 
                    {'analogsignals': 
                                        (AnalogSignal with 1 channels of length 40000; units pA; datatype float32 
                                         name: 'Im_prim2'
                                         annotations: {'stream_id': '0'}
                                         sampling rate: 40000.0 Hz
                                         time: 0.0 s to 1.0 s,)
                    },
                 1: 
                    {'analogsignals': 
                                        (AnalogSignal with 1 channels of length 40000; units pA; datatype float32 
                                         name: 'Im_prim2'
                                         annotations: {'stream_id': '0'}
                                         sampling rate: 40000.0 Hz
                                         time: 0.0 s to 1.0 s,)
                    },
                 2: 
                    {'analogsignals': 
                                        (AnalogSignal with 1 channels of length 40000; units pA; datatype float32 
                                         name: 'Im_prim2'
                                         annotations: {'stream_id': '0'}
                                         sampling rate: 40000.0 Hz
                                         time: 0.0 s to 1.0 s,)
                    } 
                } 
            } 
        } 
    }
        
    Example 2:
    ==========
    As above, but we are interesed in the indices of the analog signals named "Im_prim2":
    
    >>> neoutils.neo_lookup(ephysdata_src, name="Im_prim2", indices_only=True)
    
    {'blocks': 
        {0: 
            {'segments': 
                {0: 
                    {'analogsignals': 
                        (2,)
                    },
                 1: 
                    {'analogsignals': 
                        (2,)
                    },
                 2: 
                    {'analogsignals': 
                        (2,)
                    } 
                } 
            } 
        } 
    }
    
    Here, analog signals named "Im_prim2" were found at index 2 in the 
    'analogsignals' list attributes of segments 0, 1, and 2, in the first (and
    only) block in the argument list.
    
    This index can then be stored and (re)applied to retrieve the signal(s) from 
    selected blocks, or segments.

    In contrast to the neo.core.container.filterdata() module-level function and
    the neo.core.container.Container.filter() method, which are possibly faster,
    this function keeps track of the original container where the data object 
    was found.
    
    CAVEATS:
    ========
    1. The index can become out of sync with the data source if the contents of 
    the data source (i.e. of the block/segment/analogsignals list)
    have changed. 
    
    2. When a sequence, src can only contain a mixture of neo container objects
    (i.e., Block and Segment) OR it can be a sequence of neo data objects

    NOTE:
    =====
    Neo data types hierarchy (as of version 0.10.0):
    
    1. Containers:
    ==============
    
    Block   -> container of:
        Segment         (Block.segments), 
        Group(*)        (Block.groups)
        
    Segment -> container of data objects collected in list attributes named from
        the data object type name (e.g. 'analogsignals', etc)
                         
    2. Data objects:
    ================
    2.1 'Regular' data objects:
    ---------------------------
    AnalogSignal, IrregularlySampledSignal, SpikeTrain, Event, Epoch, 
    ImageSequence
    
    2.2. Metadata-like objects:
    ---------------------------
    ArrayDict
    
    RegionOfInterest: 
        CircularRegionOfInterest, PolygonRegionOfInterest, RectangularRegionOfInterest
                         
    3. Object types orthogonal to the hierarchy (*):
    ================================================
    Group   -> container of Neo object types (that are allowed at construction):
        Group           (Group.groups)
        Segment         (Group.segments)
        data objects    
                         
    ChannelView - virtual grouping of analog signals or irregularly sampled signals
    
    SpikeTrainList - virtual grouping of spike trains (not intended for user access)

    
    """

    if isinstance(data_obj_type, type):
        data_obj_type = (data_obj_type, )
            
    if isinstance(data_obj_type, (tuple, list, deque)) and all((isinstance(d, type) and neo.core.dataobject.DataObject in inspect.getmro(d)) for d in data_obj_type):
        signal_collection_names = tuple(map(neo.core.baseneo._container_name, (d.__name__ for d in data_obj_type)))
    else:
        raise ValueError(f"'data_obj_type' expected to be a descendant of neo.core.dataobject.DataObject, or a sequence (deque, list, tuple) of such types; got {data_obj_type.__name__} instead")
    
    #print("signal_collection_names", signal_collection_names)
    
    # NOTE: 2021-10-14 09:05:28
    # *args introduced so that we can feed a comma-separated list of neo objects
    if len(args)==0:
        return {}
    
    if len(args) == 1:
        src = args[0]
        
    else:
        src = args
        
    if isinstance(src, neo.core.container.Container):
        containers = [src]
        
    elif isinstance(src, (tuple, list, deque)):
        if all(isinstance(s, neo.core.container.Container) for s in src):
            containers = src
            
        elif all(isinstance(s, neo.core.dataobject.DataObject) for s in src):
            # a colleciton of possibly mixed signals - just return a 'vanilla'
            # dict
            if all(type(s) == type(src[0]) for s in src):
                # if all data obejcts have the same type return a 'mock' 
                # named container list
                key = neo.core.container._container_name(type(src[0]).__name__)
            else:
                #
                key = "signals"
                
            return {key: tuple([i for i in filter_attr(src, op=op, indices=indices,
                                                             indices_only=indices_only,
                                                             exclude=exclude, **kwargs)])}
    else:
        raise TypeError("'src' expected to be a descendant of neo.core.container.Container, or a sequence (deque, list, tuple) of such, or of data objects")
    
    container_names = tuple(map(lambda x: neo.core.baseneo._container_name(type(x).__name__), containers))
    
    #rr = dict((container_names[k], {k:dict((signal_collection_name, tuple([i for i in filter_attr(collection, 
                                                                             #op=op, 
                                                                             #indices=indices, 
                                                                             #indices_only=indices_only, 
                                                                             #exclude=exclude, 
                                                                             #**kwargs)])))}) for k, container in enumerate(containers))
    
    ret = dict()
    
    # ### BEGIN blueprint code - it actually works - do not delete !!!
    for k, container in enumerate(containers):
        container_name = container_names[k]
        
        cdict = dict()
        
        for l, signal_collection_name in enumerate(signal_collection_names):
            collection = getattr(container, signal_collection_name, None)
            if collection is not None:
                cdict.update({signal_collection_name: tuple([i for i in filter_attr(collection, 
                                                                             op=op, 
                                                                             indices=indices, 
                                                                             indices_only=indices_only, 
                                                                             exclude=exclude, 
                                                                             **kwargs)])})
                
            else:
                for child_container_name in container._child_containers:
                    ccdict  = neo_lookup(getattr(container, child_container_name),
                                         data_obj_type=data_obj_type,
                                         op=op,
                                         indices=indices,
                                         indices_only=indices_only,
                                         exclude=exclude,
                                         **kwargs)
                    
                    if isinstance(ccdict, dict):
                        cdict.update(ccdict)
                        
        if len(cdict):
            if container_name in ret:
                ret[container_name].update({k:cdict})
            else:
                ret[container_name] = {k:cdict}
    
    if len(ret):
        return ret
                
    # ### END blueprint code - it actually works!
    
#def neo_lookup2(*args:
               #data_obj_type: typing.Union[typing.Sequence[type], type] = neo.AnalogSignal,
               #op = operator.and_, 
               #indices:bool = False, 
               #indices_only:bool = False,
               #exclude: bool = False,
               #**kwargs):
    
    #if len(args) == 0:
        #return {}

    #if isinstance(data_obj_type, type):
        #data_obj_type = (data_obj_type, )
            
    #if isinstance(data_obj_type, (tuple, list, deque)) and all((isinstance(d, type) and neo.core.dataobject.DataObject in inspect.getmro(d)) for d in data_obj_type):
        #signal_collection_names = tuple(map(neo.core.baseneo._container_name, (d.__name__ for d in data_obj_type)))
    #else:
        #raise ValueError(f"'data_obj_type' expected to be a descendant of neo.core.dataobject.DataObject, or a sequence (deque, list, tuple) of such types; got {data_obj_type.__name__} instead")
    
    #ret = dict()
    
    ## NOTE: 
    ## 'container_list_name' = name of attribute that is a list of containers
    ##   e.g., 'segments' (most typically) but also 'groups'
    ##   we also allow fictitous ones:
    ##   'blocks' to index in a collection of 
    ## 'object_list_name' = name of attribute that is a list of data object
    
    #for arg in args:
        #if isinstance(arg, neo.core.container.Container):
            #container_name = neo.core.container._container_name(type(arg).__name__)
            
            ## get the indexing dict for container arg
            
            #if container_name in ret:
                
            
            
        
    
    #if len(src) == 1:
        #src = src[0]
        
            
def neo_use_lookup_index(*args: typing.Union[neo.container.Container, typing.Sequence],
                    ndx: dict) -> tuple:
    """Access data objects using an indexing dictionary returned by neo_lookup.
    neo_lookup must have been called with indices_onlt set to True.
    
    """
    if __debug__:
        global __debug_count__
        __debug_count__ += 1
        
        __debug_indent__ = "   " * (__debug_count__ -1)
        
    if not isinstance(ndx, dict):
        raise TypeError(f"'ndx' expected to be a dict; got {type(ndx).__name__} instead")
        
    if len(args) == 0:
        return
    
    if len(args) == 1:
        src = args[0]
        
    else:
        src = args
        
    ret = list()
    
    if isinstance(src, neo.core.container.Container):
        src = [src]
        
    elif not (isinstance(src, (tuple, list, deque)) and all(isinstance(s, neo.core.baseneo.BaseNeo) for s in src)):
        raise TypeError("'src' expected ot be a neo container or a sequence of neo objects")
    
    for kdata, data in enumerate(src):
        data_container_name = neo.core.baseneo._container_name(type(data).__name__)
        
        if data_container_name in ndx.keys():
            data_subindex = ndx[data_container_name]
            if isinstance(data_subindex, dict) and all(isinstance(k, int) for k in data_subindex):
                dsub = data_subindex[kdata]
                
                    
                
    
    if isinstance(src, (tuple, list)): # NOTE: 2020-03-23 23:41:16 sequence of containers or data objects
        if isinstance(ndx, (tuple, list, deque, range)) and all([isinstance(k, int) for k in ndx]): # sequence of ints
            ret += [src[k] for k in ndx] # simply return the k^th element, for k in ndx
            
        elif isinstance(ndx, int):
            ret += [src[ndx]] # return the ndx^th element
            
        elif isinstance(ndx, dict):
            for key, index in ndx.items():
                if isinstance(key, int):
                    ret_ = neo_use_lookup_index(src[key], index)
                    ret += [v for v in ret_ if all([not is_same_as(v, v_) for v_ in ret])]
                              
                else:
                    raise IndexError("Unexpected index:%s at key:%s = %s, for src:%s" % (type(index).__name__, type(key).__name__, key, type(src).__name__))
            
        else:
            raise TypeError("Unexpected indexing type %s for %s object" % (type(ndx).__name__, type(src).__name__))
        
    elif isinstance(src, neo.container.Container): # typical entry point
        if isinstance(ndx, dict):
            src_container_name = neo.core.baseneo._container_name(type(src).__name__)
            if src_container_name in ndx.keys():# and all (isinstance(k, int) for k in ndx[src_container_name].keys()):
                subindex = ndx[src_container_name]
                #if all(isinstance(k, int) for k in subindex.keys()): # {...}{0:}, {1:}, etc;
                    #for k in 
                #if 
                for subcontainer_name , subcontainer_ndx in subindex.items():
                    # does subcontainer_name refer to a collection of neo containers or neo data objects?
                    subcontainer_or_collection = getattr(src, subcontainer_name, None)
                    #if subcontainer_or_collection is not None:
                        #if isinstance(subcontainer_ndx, dict):
                            ## 
                            #for subcontainer_k,  in subcontainer_ndx
                        
                    
                    ret.extend(getattr(src, ))
            for key, index in ndx.items(): # iterate through the ndx dict's key/value pairs
                if isinstance(key, str): # works on Container's attribute in 'key'
                    collection = getattr(src, key, None) # sequence of containers or data objects
                    
                    if collection is None:
                        raise AttributeError("%s is an invalid attribute of %s" % (key, type(src).__name__))
                    
                    if isinstance(index, (dict, tuple, list)):
                        ret += [v for v in neo_use_lookup_index(collection, index) if v not in ret] # enters at NOTE: 2020-03-23 23:41:16 
                        
                    else:
                        raise KeyError("Unexpected indexing structure type %s for %s object" % (type(index).__name__, type(collection).__name__))
                    
    else:
        raise IndexError("Invalid indexing structure type: %s" % type(ndx).__name__)
    

    if __debug__:
        __debug_count__ -= 1
        
    return tuple(ret)
            
def normalized_signal_index(src: neo.core.container.Container,
                            index: typing.Union[int, str, range, slice, typing.Sequence],
                            ctype: type = neo.AnalogSignal, 
                            silent: bool = False) -> typing.Union[range, list]:
    """Returns the integral index of a signal in its container.
    
    Useful to get the index of data by its name. 
    CAUTION Indexing by name assumes that all data in the container have unique names.
    
    Parameters:
    ----------
    
    src: neo container
    
    index: int, str, tuple, list, range, or slice; any valid form of indexing
        including by the value of the signal's "name " attribute.
    
    ctype: type object; the type of signal to index; valid signal types are 
        neo.AnalogSignal, neo.IrregularlySampledSignal, 
        neo.Event, neo.Epoch, neo.SpikeTrain, neo.ImageSequence, neo.Unit,
        datatypes.DataSignal and datatypes.IrregularlySampledDataSignal
        
        Defaults is neo.AnalogSignal.
        
        
        
        WARNING: AS OF 2021-10-03 13:08:37 ChannelIndex and Unit are OUT 
        
        Segment objects contain analog & irregularly sampled signals, events,
            epochs, spike trains, channel indexes, and image sequences.
            
        Unit objects contain only spike trains.
        
    Returns:
    --------
    a range or list of integer indices
    
    """
    major, minor, dot = get_neo_version()
    
    data_len = None
    
    if not isinstance(src, neo.Segment):
        raise TypeError("Expecting a neo.Segment; got %s instead" % type(src).__name__)
    
    #### BEGIN figure out what signal collection we're after
    if ctype in (neo.AnalogSignal, DataSignal):
        if not isinstance(src, neo.Segment):
            raise TypeError("%s does not contain %s" % (type(src).__name__, ctype.__name__))
        
        signal_collection = src.analogsignals
        
    elif ctype in (neo.IrregularlySampledSignal, IrregularlySampledDataSignal):
        if not isinstance(src, neo.Segment):
            raise TypeError("%s does not contain %s" % (type(src).__name__, ctype.__name__))
        
        signal_collection = src.irregularlysampledsignals
        
    elif ctype is neo.SpikeTrain:
        if not isinstance(src, neo.Segment):
            raise TypeError("%s does not contain %s" % (type(src).__name__, ctype.__name__))
        
        signal_collection = src.spiketrains
        
    elif ctype is neo.Event:
        if not isinstance(src, neo.Segment):
            raise TypeError("%s does not contain %s" % (type(src).__name__, ctype.__name__))
            
        signal_collection = src.events
        
    elif ctype is neo.Epoch:
        if not isinstance(src, neo.Segment):
            raise TypeError("%s does not contain %s" % (type(src).__name__, ctype.__name__))
            
        signal_collection = src.epochs
        
    elif any([major >= 0, minor >= 8]) and ctype is neo.core.ImageSequence:
        if not isinstance(src, neo.Segment):
            raise TypeError("%s does not contain %s" % (type(src).__name__, ctype.__name__))
            
        # ImageSequence: either a 3D numpy array [frame][row][column] OR
        # a sequence (list) of 2D numpy arrays [row][column]
        signal_collection = src.imagesequences
        
        if not all([(hasattr(i, "image_data") and hasattr(i, "name")) for i in signal_collection]):
            raise TypeError("Inconsistent collection of image sequences")
        
        if len(signal_collection) == 1:
            img = signal_collection[0].image_data
            
            if img.ndim == 3:
                data_len = img.shape[0]
                
            else:
                raise TypeError("Ambiguous image sequence data type")
            
        elif len(signal_collection) > 1:
            if any([i.image_data.ndim != 2 for i in signal_collection]):
                raise TypeError("Ambiguous image sequence data type")
            
            data_len = len(signal_collection)
            
    else:
        raise TypeError("Cannot handle %s" % ctype.__name__)
    
    #### END figure out what signal collection we're after'

    if signal_collection is None or len(signal_collection) == 0:
        return range(0)
    
    if data_len is None:
        data_len = len(signal_collection)
        
    #print("data_len", data_len)
    
    if isinstance(index, (int, range, slice, np.ndarray, type(None))):
        return normalized_index(data_len, index)    
        
    elif isinstance(index, str):
        if silent:
            return utilities.silentindex([i.name for i in signal_collection], index)
        
        return [i.name for i in signal_collection].index(index)
    
    elif isinstance(index, (tuple, list)):
        indices = list()
        
        for ndx in index:
            if isinstance(ndx, int):
                indices.append(normalized_index(data_len, ndx))
                
            elif isinstance(ndx, str):
                if silent:
                    indices.append(utilities.silentindex([i.name for i in signal_collection], ndx))
                    
                else:
                    indices.append([i.name for i in signal_collection].index(ndx) )
                    
            else:
                raise TypeError("Invalid index element type %s" % type(ndx).__name__)
                
        return indices
                
    else:
        raise TypeError("Invalid indexing: %s" % index)
    
#def get_segments_in_channel_index(channelIndex:neo.ChannelIndex) -> tuple:
    #"""Query the segments linked to the channel index.
    
    #Parameters:
    #----------
    #channelIndex: neo.ChannelIndex
    
    #Returns:
    #-------
    #a tuple of segments that contain the signals linkes to this channel index

    #NOTE: the segments may or may not belong to the same Block; this can be 
    #queried by testing the identity of segment.block attribute
    
    #"""
    #if not isinstance(channelIndex, neo.ChannelIndex):
        #raise TypeError("Expecting a neo.ChannelIndex; got %s instead" % type(channelIndex).__name__)
    
    ## use generator expression
    #genex = (x.segment for x in channelIndex.analogsignals + channelIndex.irregularlysampledsignals if isinstance(x.segment, neo.Segment))
    
    #return tuple(set(genex))
    
#@safeWrapper
def get_index_of_named_signal(src, names, stype=neo.AnalogSignal, silent=False):
    """Returns a list of indices of signals named as specified by 'names', 
    and contained in src.
    
    Positional parameters:
    ----------------------
    
    Src: a neo.Block or a neo.Segment, or a list of signal-like objects
    
    
    names: a string, or a list or tuple of strings
    
    Keyword parameters:
    -------------------
    
    stype:  a type (python class ) of signal; optional, default is neo.AnalogSignal
                other valid types are:
                DataSignal
                neo.IrregularlySampledSignal
                neo.SpikeTrain
                neo.Event
                neo.Epoch
            
            or the tuple (neo.AnalogSignal, datatypes.DataSignal)
            
            TODO: or a tuple of types as above # TODO FIXME
            
    silent: boolean (optional, default is False): when True, the function returns
        'None' for each signal name not found; otherwise it will raise an exception
    
    Returns
    ======= 
    
    Depending on what 'src' and 'names' are, returns a list of indices, or a list of
    nested lists of indices:
    
    If 'src' is a neo.Block:
    
        if 'names' is a str, the function returns a list of indices of the signal
            named as specified by 'names', with as many elements as there are segments
            in the block.
            
        if 'names' is a sequence of str, the function returns a list of nested lists
            where each inner list is as above (one inner list for each element of
            'names'); 
            
    If 'src' is a neo.Segment:
    
        if 'names' is str the function simply returns the index of the signal named 
            by 'names'
            
        if 'names' is a sequence of str, then the function returns a list of indices
            as above (one integer index for each element of 'names')
    
    NOTE:
    When a signal with the specified name is not found:
        If 'silent' is True, then the function places a None in the list of indices.
        If 'silent' is False, then the function raises an exception.
    
    ATTENTION:
    1) The function presumes that, when 'src' is a Block, it has at least one segment
    where the 'analogsignals' attribute a list) is not empty. Likewise, when 
    'src' is a Segment, its attribute 'analogsignals' (a list) is not empty.
    
    2) iT IS ASSUMED THAT ALL SIGNALS HAVE A NAME ATTRIBUTE THAT IS NOT None
    (None is technically acceptable value for the name attribute)
    
    Such signals will be skipped / missed!
    """
    signal_collection = "%ss" % stype.__name__.lower()
    
    if signal_collection == "datasignals":
        signal_collection = "analogsignals"
    
    if isinstance(src, neo.core.Block) or (isinstance(src, (tuple, list)) and all([isinstance(s, neo.Segment) for s in src])):
        # construct a list of indices (or list of lists of indices) of the named
        # signal(s) in each of the Block's segments
        
        if isinstance(src, neo.Block):
            data = src.segments
            
        else:
            data = src
        
        if isinstance(names, str):
            ret = [k for k in filter_attr(getattr(j,signal_collection), name = names)]
            if silent:
                return [utilities.silentindex([i.name for i in getattr(j, signal_collection)], names, multiple=False) for j in data]
            
            return [[i.name for i in getattr(j, signal_collection)].index(names) for j in data]
             
        elif isinstance(names, (list, tuple)):
            if np.all([isinstance(i,str) for i in names]):
                # proceed only if all elements in names are strings and return a 
                # list of lists, where each list element has the indices for a given
                # signal name
                if silent:
                    return [[utilities.silentindex([i.name for i in getattr(j, signal_collection)], k, multiple=False) for k in names] for j in data]
                
                return [[[i.name for i in getattr(j, signal_collection)].index(k) for k in names ] for j in data]
                
    elif isinstance(src, neo.core.Segment):
        objectList = getattr(src, signal_collection)
        
        if isinstance(names, str):
            if silent:
                return utilities.silentindex([i.name for i in objectList], names, multiple=False)
            
            return [i.name for i in objectList].index(names)
            
        elif isinstance(names, (list, tuple)):
            if np.all([isinstance(i,str) for i in names]):
                if silent:
                    return [utilities.silentindex([i.name for i in objectList], j, multiple=False) for j in names]
                
                return [[i.name for i in objectList].index(j) for j in names]
            
        else:
            raise TypeError("Invalid indexing")
        
    else:
        raise TypeError("First argument must be a neo.Block object, a list of neo.Segment objects, or a neo.Segment object; got %s instead" % type(src).__name__)

@safeWrapper
def get_epoch_named_interval(epoch: neo.Epoch, label: typing.Union[str, bytes], 
                             duration:bool=False) -> tuple:
    """Returns a tuple of time quantities for the epoch interval having a specific label.
    
    Parameters:
    ----------
    epoch: neo.Epoch - Its intervals should each carry a label
    
    label: str or bytes - The label of the interval that is requested
        When bytes, it must an utf-8 - encoded bytes string (i.e., identical to
            the result of calling bytes("xx", "utf-8") where "xx" is a str
            
        This must not be empty, and must be present in the epoch's "labels" array.
        This implies epoch.labels.size == epoch.times.size == epoch.size
        
    duration: bool Optional (default is False)
        When True, returns the (time, duration) tuple for the specified interval.
        When False (default), returns the (time, time + duration) tuple corresponding
        to the specified interval.
        
    Returns:
    --------
    
    A tuple of two Python Quantities with time units, that depending on the value
    of the 'duration' parameter, represent either:
    
    (time, duration)
    
    or:
    
    (time, time + duration) - i.e., a (t0, t1) time tuple useful for time slicing
    of neo-style data arrays
    
    """
    if not isinstance(epoch, neo.Epoch):
        raise TypeError("'epoch' expected to be a neo.Epoch; got %s instead" % type(epoch).__name__)
    
    if not isinstance(label, (str, bytes)):
        raise TypeError("'label' expected to be a str or bytes; got %s instead" % type(label).__name__)
    
    if len(label.strip()) == 0:
        raise ValueError("'label' is empty!")
    
    if isinstance(label, bytes):
        if not label.isalnum():
            raise ValueError("'labe' expected to be alphanumeric; got %s instead" % label)
    
    if isinstance(label, str):
        label = bytes(label, "utf-8")
        
    if label not in epoch.labels:
        raise KeyError("Interval labelled %s not found" % label.decode("utf-8"))
    
    ndx = int(np.where(epoch.labels == label)[0])
    
    return (epoch.times[ndx], epoch.durations[ndx]) if duration else (epoch.times[ndx], epoch.times[ndx]+epoch.durations[ndx])
    
    

@safeWrapper
def get_time_slice(data, t0, t1=None, window=0, \
                    segment_index=None, \
                    analog_index=None, \
                    irregular_index=None,\
                    spiketrain_index=None, \
                    epoch_index=None,\
                    event_index=None):
    """Returns a time slice from a neo.Block or neo.Segment object.
    
    The time slice is a Block or a Segment (depending on the type of "data"
    object) with the time slice of all signals or from selected signals.
    
    WARNING: All segments are expected to have the same relative start time
    
    NOTE: neo.AnalogSignals.time_slice() member function fulfills the same role.
    
    Positional parameters:
    ---------------------
    
        data: a neo.Block or a neo.Segment
        
        t0: a neo.Epoch, a scalar or a python quantity in time units
        
            When 't0' is an Epoch, it already specifies both the start time and 
            the duration of the time slice.
            
            When 't0' is a scalar real or a python quantity, it only specifies 
            the start time; then, either 't1' (end time) or 'window' must be 
            also given (see below).
        
        
    Keyword parameters:
    -------------------
        t1: (optional, default = None) scalar, a python quantity in time units, 
            or None;
            
            NOTE that when 't0' is an epoch, 't1' is calculated from 't0' and 
            the value given for 't1' here is discarded:
            
                t1 = t0.times + t0.durations
                
                t0 = t0.times
            
        window (optional, default = 0): scalar, or python quantity in time units.
        
            NOTE: window is MANDATORY when 't1' is None and 't0' is NOT an epoch
            (see NOTE below)
            
        segment_index (optional, default = None): scalar index or sequence of indices
            for the segments in the data, from which the time slice is to be extracted.
            
            Only used when data is a neo.Block.
            
            When None, the result will contain the time slices taken from all segments.
            
        analog_index (optional, default = None): index or sequence of indices
            for the AnalogSignals (regularly sampled) in each segment. 
            When None, the function will return time slices from all signals found.
            
            The index can be specified as an integer, or as a string containing
            the signal name.
            
        irregular_index (optional, default = None): 
            as for analog_index, this is an index or sequence of indices
            for the IrregularlySampledSignals in each segment. When None, the 
            function will return time slices from all signals found.
            
            The index can be specified as an integer, or as a string containing
            the signal name.
            
        spiketrain_index (optional, default is None): index of sequence of indices
            of spiketrains; same semantics as for analog_index
            
        epoch_index (optional, default is None): index of sequence of indices
            of epochs; same semantics as for analog_index
            
        event_index (optional, default is None): index of sequence of indices
            of event ARRAYS; same semantics as for analog_index
            
            NOTE: each segment may contain several neo.Event arrays; this index
            specifies the Event ARRAY, not the index of individual events WITHIN
            an Event array! Similar to the other cases above, neo.Event arrays
            can also be selected by their "name" attribute (which is the name of 
            the entire Event array, and NOT the name of individual events in the
            array).
        
    NOTE: 
        When 't0' is a scalar, the time slice is specified as 't0', 't1', or as
        't0', 'window'.
        
        In the latter case, the window gives the duration CENTERED AROUND t0 and 
            the time slice is calculated as:
            
            t1 = t0 + window/2
            
            t0 = t0 - window/2.
    
    NOTE: 2019-11-25 20:38:44
    
    From neo version 0.8.0 segments also support time_slicing
    
    """
    # get_time_slice (1) check for t1 first
    
    if isinstance(t1, pq.Quantity):
        _d_ = [k for k in t0.dimensionality.keys()][0]
        if not isinstance(_d_, pq.time.UnitTime):
            raise ValueError("The t1 quantity must be in time unit; got %s instead" % type(_d_).__name__)
        
    elif isinstance(t1, numbers.Real):
        t1 =t1 * pq.s
        
    elif t1 is not None:
        raise TypeError("When given, t1 must be a real scalar, time python quantity, or None; got %s instead" % type(t1).__name__)
        
        
    # get_time_slice (2) check for t0, override t1 if t0 is an epoch
    
    if isinstance(t0, neo.Epoch):
        if t0.size != 1:
            raise ValueError("When given as a neo Epoch, t0 must have size 1; instead it has %d" % (t0.size))
        
        t1 = t0.times + t0.durations
        t0 = t0.times
    
    elif isinstance(t0, pq.Quantity):
        _d_ = [k for k in t0.dimensionality.keys()][0]
        
        if not isinstance(_d_, pq.time.UnitTime):
            raise ValueError("The t0 quantity must be in time unit; got %s instead" % type(_d_).__name__)
        
    elif isinstance(t0, numbers.Real):
        t0 = t0 * pq.s
        
    else:
        raise TypeError("t0 must be a neo.Epoch, real scalar or python quantity in time units; got %s instead" % type(t0).__name__)


    # get_time_slice (3) if t1 is None, check for window and calculate t1
    
    if t1 is None:
        if isinstance(window, pq.Quantity):
            _d_ = [k for k in window.dimensionality.keys()][0]
            
            if not isinstance(_d_, pq.time.UnitTime):
                raise ValueError("The window quantity must be in time units; got %d instead" % type(_d__).__name__)
            
        elif isinstance(window, numbers.Real):
            window = window * pq.s
            
        elif window is None:
            raise TypeError("When t1 is missing, window must be given")
            
        else:
            raise TypeError("When given, window must be a time python quantity or a real scalar; got %s instead" % type(window).__name__)
    
        t1 = t0 + window/2
        t0 = t0 - window/2
        
    # get_time_slice (4) now picks up the time slice and construct the return value: 
    # a neo.Block, if data is a neo.Block, or a neo.Segment, if data is a neo.Segment, 
    # or raise exception if data is neither
    
    if isinstance(data, neo.Block): # yes, this function calls itself = recursion
        ret = neo.core.Block()
        if segment_index is None: # get time slice from ALL segments
            ret.segments = [get_time_slice(seg, t0=t0, t1=t1, 
                                           analog_index=analog_index, 
                                           irregular_index=irregular_index, 
                                           spiketrain_index=spiketrain_index, 
                                           event_index=event_index,
                                           epoch_index=epoch_index) for seg in data.segments]
            
        elif isinstance(segment_index, int): # or from just the selected segments
            ret.segments = [get_time_slice(data.segments[segment_index], t0=t0, t1=t1,
                                           analog_index=analog_index,
                                           irregular_index=irregular_index, 
                                           spiketrain_index=spiketrain_index, 
                                           event_index=event_index, 
                                           epoch_index=epoch_index)]
            
        elif isinstance(segment_index, (range, tuple, list)):
            ret.segments = [get_time_slice(data.segments[k], t0=t0, t1=t1, 
                                           analog_index=analog_index, 
                                           irregular_index=irregular_index,
                                           spiketrain_index=spiketrain_index,
                                           event_index=event_index,
                                           epoch_index=epoch_index) for k in segment_index]
            
        elif isinstance(segment_index, slice):
            ndx = segment_index.indices(len(data.segments))
            ret.segments = [get_time_slice(data.segments[k], t0=t0, t1=t1, 
                                           analog_index=analog_index, 
                                           irregular_index=irregular_index,
                                           spiketrain_index=spiketrain_index,
                                           event_index=event_index,
                                           epoch_index=epoch_index) for k in ndx]
            
        else:
            raise TypeError("Unexpected segment indexing type")
        
    elif isinstance(data, neo.Segment): 
        ret = neo.Segment()
        
        # get the time slice from a single segment;
        # 'time_slice' method will check that t0 and t1 fall within each signal 
        # time base
        
        # 1) AnalogSignals
        
        if len(data.analogsignals) > 0:
            if analog_index is None: # from ALl signals
                ret.analogsignals = [a.time_slice(t0,t1) for a in data.analogsignals]
                
            elif isinstance(analog_index, (str, int)):
                if isinstance(analog_index,str):
                    analog_index= get_index_of_named_signal(data, analog_index)
                
                ret.analogsignals = [data.analogsignals[analog_index].time_slice(t0,t1)]
                
            elif isinstance(analog_index, (list, tuple, range)):
                if all([isinstance(s, str) for s in analog_index]):
                    analog_index = [get_index_of_named_signal(data, s) for s in analog_index]
                
                ret.analogsignals = [data.analogsignals[k].time_slice(t0,t1) for k in analog_index]
                
            elif isinstance(analog_index, slice):
                ndx = analog_index.indices(len(data.analogsignals))
                ret.analogsignals = [data.analogsignals[k].time_slice(t0,t1) for k in ndx]
                
            else:
                raise TypeError("Unexpected analog_index type")
        
        # 2) IrregularlySampledSignals
        
        if len(data.irregularlysampledsignals) > 0:
            if irregular_index is None: # from ALl signals
                ret.irregularlysampledsignals = [a.time_slice(t0,t1) for a in data.irregularlysampledsignals]
                
            elif isinstance(irregular_index, (str, int)):
                if isinstance(irregular_index,str):
                    irregular_index = get_index_of_named_signal(data, irregular_index, stype=neo.IrregularlySampledSignal)
                
                ret.irregularlysampledsignals = [data.irregularlysampledsignals[irregular_index].time_slice(t0,t1)]
                
            elif isinstance(irregular_index, (list, tuple, range)):
                if all([isinstance(s, str) for s in irregular_index]):
                    irregular_index = [get_index_of_named_signal(data, s, stype = neo.IrregularlySampledSignal) for s in irregular_index]
                
                ret.irregularlysampledsignals = [data.irregularlysampledsignals[k].time_slice(t0,t1) for k in irregular_index]
                
            elif isinstance(irregular_index, slice):
                ndx = irregular_index.indices(len(data.irregularlysampledsignals))
                ret.irregularlysampledsignals = [data.irregularlysampledsignals[k].time_slice(t0,t1) for k in ndx]
                
            else:
                raise TypeError("Unexpected irregular_index index type")
            
            
        # 3) Spike trains
        
        if len(data.spiketrains) > 0:
            if spiketrain_index is None: # ALL spike trains
                ret.spiketrains = [a.time_slice(t0, t1) for a in data.spiketrains]
                
            elif isinstance(spiketrain_index, (str, int)):
                if isinstance(spiketrain_index, str):
                    spiketrain_index = get_index_of_named_signal(data, spiketrain_index, stype=neo.SpikeTrain)
                    
                ret.spiketrains = [data.spiketrains[spiketrain_index].time_slice(t0,t1)]
                
            elif isinstance(spiketrain_index, (list, tuple, range)):
                if all([isinstance(s, str) for s in spiketrain_index]):
                    spiketrain_index = [get_index_of_named_signal(data, s, stype=neo.SpikeTrain) for s in spiketrain_index]
                    
                ret.spiketrains = [data.spiketrains[k].time_slice(t0,t1) for k in spiketrain_index]
                
            elif isinstance(spiketrain_index, slice):
                ndx = spiketrain_index.indices(len(data.spiketrains))
                ret.spiketrains = [data.spiketrains[k].time_slice(t0,t1) for k in ndx]
                
            else:
                raise TypeError("Unexpected spiketrain index type")
            
                
        # 4) Event
        
        if len(data.events) > 0:
            if event_index is None:
                ret.events = [e.time_slice(t0, t1) for e in data.events]
                
            elif isinstance(event_index, (str, int)):
                if isinstance(event_index, str):
                    event_index = get_index_of_named_signal(data, event_index, stype=neo.Event)
                    
                ret.event = [data.events[event_index].time_slice(t0,t1)]
                
            elif isinstance(event_index, (tuple, list, range)):
                if all([isinstance(s, str) for s in event_index]):
                    event_index = [get_index_of_named_signal(data, s, stype=neo.Event) for s in event_index]
                    
                ret.events = [data.events[k].time_slice(t0, t1) for k in event_index]
                
            elif isinstance(event_index, slice):
                ndx = event_index.indices(len(data.events))
                ret.events = [data.events[k].time_slice(t0, t1) for k in ndx]
                
            else:
                raise TypeError("Unexpected event index type")
            
                
        # 5) Epoch
        
        if len(data.epochs) > 0:
            if epoch_index is None:
                ret.epochs = [e.time_slice(t0, t1) for e in data.epochs]
                
            elif isinstance(epoch_index, (str, int)):
                if isinstance(epoch_index, str):
                    event_index = get_index_of_named_signal(data, epoch_index, stype=neo.Event)
                    
                ret.event = [data.epochs[epoch_index].time_slice(t0,t1)]
                
            elif isinstance(epoch_index, (tuple, list, range)):
                if all([isinstance(s, str) for s in epoch_index]):
                    epoch_index = [get_index_of_named_signal(data, s, stype=neo.Event) for s in epoch_index]
                    
                ret.epochs = [data.epochs[k].time_slice(t0, t1) for k in epoch_index]
                
            elif isinstance(epoch_index, slice):
                ndx = epoch_index.indices(len(data.epochs))
                ret.epochs = [data.epochs[k].time_slice(t0, t1) for k in ndx]
                
            else:
                raise TypeError("Unexpected epoch index type")
        
    elif isinstance(data, (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal)):
        return data.time_slice(t0,t1)
    
    else:
            
        raise TypeError("Expecting data to be a neo.Block or neo.Segment; got %s instead" % (type(data).__name__))
        
    
    # set up attributes below, that are common to neo.Block and neo.Segment
    
    if data.name is not None:
        ret.name = data.name + " Time slice %g - %g" % (t0,t1)
        
    else:
        ret.name = "Time slice %g - %g" % (t0,t1)
        
    ret.rec_datetime = datetime.datetime.now()
        
    return ret

@safeWrapper
def concatenate_signals(*args, axis:int = 1, 
                        ignore_domain:bool = False, 
                        ignore_units:bool = False,
                        set_domain_start:typing.Optional[float] = None, 
                        force_contiguous:bool=True,
                        padding:typing.Optional[typing.Union[bool, pq.Quantity]]=False,
                        overwrite:bool=False,
                        ):
    """Concatenates regularly sampled signals.
    
    Implements the functionality of neo.AnalogSignal's merge() and concatenate()
    but allows a sequence of signals instead of being restricted to two signals.
    
    When the 'axis' parameters is the default (1, one) this is useful to collapse
    several analog signals into a single multi-channel signal ('merging').
    
    Here a "channel" is one data column in the signal.
    
    When the 'axis' parameter is 0, this simply collates the signals 'end-to-end'
    ('concatenating').
    
    Source signals should have identical units, and compatible domains.
    
    Concatenating signals brings a few restrictions in addition to those derived
    from concatenating numpy arrays; these restrictions can be relaxed by setting
    the 'ignore_domain' and 'ignore_units' flags to True.
    
    1) all signals should have the same sampling rate
    2) all signals should have the same units or their units should be compatible
        (i.e., convertible to each other)
    2) all signals should have identical domains (units, origin e.g. 't_start', 
        and sampling_rate)
        
    This function can concatenate signals belonging to different segments (in 
    this case, the resulting signal's segment attribute is set to None!)
        
    
    Var-positional parameters:
    -------------------------
    
    a sequence of signals, or a comma-separated list of signals.
    
    All signals must have the same shape except for the dimension of the 
    concatenating axis.
    
    Named parameters:
    ----------------
    axis: int; default is 1
        The concatenation axis
        
    ignore_domain: bool, default is False
        When False (default) all signals must have identical time domains 
        (t_start, units and sampling_rate)
        
        When True, the data will be concatenated and a new time domain will be
        generated with the units, t_start and sampling_rate taken from the first
        signal in the sequence.
        
    ignore_units = bool, default False
        When True, will skip checks for units compatibilty among signals.
        
    force_contiguous:bool, default True
        When concatenating signals across the domain axis, assign new domain
        values when signals' domains overlap
        
    padding, overwrite: parameters used when signals are concatenated across the
    domain axis (see neo.AnalogSignal.concatenate() for details)
    
    """
    def __get_default_attr__(val, default):
        return default if val is None else val
    
    def __get_attrs__(s):
        yield from (__get_default_attr__(getattr(s, attr[0], None), attr[1]) for attr in (("description", ""),
                                                                                          ("name", ""), 
                                                                                          ("file_origin", ""),
                                                                                          ("annotations", {}),
                                                                                          ("array_annotations", ArrayDict(s.shape[-1]))))
        
    
    if len(args) == 1:
        if isinstance(args[0], (tuple, list)):
            signals = args[0]
            
        else:
            raise TypeError("Expecting a sequence; got %s instead" % type(args[0]).__name__)
    else:
        signals = args
        
    # NOTE 2019-09-11 12:31:00:
    # a sequence of signals
    # break-up the conditions so that we enforce all element to be of the SAME type
    # instead of either one of the two types -- i.e. do NOT accept sequences of
    # mixed types !!!
    if all([isinstance(sig, neo.AnalogSignal) for sig in signals]) or \
        all([isinstance(sig, DataSignal) for sig in signals]):
        sig_klass = type(signals[0])
        
        sig_shapes = [[s for s in sig.shape] for sig in signals]
        
        for s in sig_shapes:
            s[axis] = None
            
        if not all(sig_shapes[0] == s for s in sig_shapes):
            raise MergeError("Signals do not have identical shapes on non-concatenating axes")
        
        # this is needed for any concatenation axis!
        if not ignore_domain:
            if not all([sig.times.units] == signals[0].times.units for sig in signals[1:]):
                raise MergeError("Cannot concatenate signals having different domain units ")
            
            if not all([np.isclose(sig.sampling_rate.magnitude, signals[0].sampling_rate.magnitude) for sig in signals[1:]]):
                raise MergeError("Cannot concatenate signals having different sampling rates")
            
            # NOTE: axis 0 is the domain axis!
            if axis > 0 or axis == -1:
                if not all([sig.t_start == signals[0].t_start for sig in signals[1:]]):
                    raise MergeError("Cannot merge channels of signals that have different domains ")
                
        #sig_names = ["signal_%d" % k if sig.name is None else sig.name for (k, sig) in enumerate(signals)]
            
        #concat_sig_names = ", ".join(sig_names)
        
        sampling_rate = signals[0].sampling_rate
        
        units_0 = signals[0].units
        
        if ignore_units:
            signal_data = [sig.magnitude for sig in signals]
            
        else:
            if not all([units_convertible(sig.units, signals[0].units) for sig in signals[1:]]):
                raise MergeError("There are signals with non-convertible units; this may become an error in the future")
            
            signal_data = [signals[0].magnitude] + [sig.rescale(units_0).magnitude if sig.units != units_0 else sig.magnitude for sig in signals[1:]]
            
        action = "merged" if axis == 1 else "concatenated"
        
        descr, names, files, annots, aannots = tuple(((zip(*tuple(tuple(__get_attrs__(s)) for s in signals)))))
        #descr, names, files, annots, aannots = tuple(((zip(*tuple(tuple(map(lambda x: "" if x is None else x, __get_attrs__(s))) for s in signals)))))
        
        kwargs = dict()
        
        if sum(len(x) for x in descr) > 0:
            kwargs["description"] = f"{action}(" + ", ".join(descr) + ")"
            
        if sum(len(x) for x in names) > 0:
            kwargs["name"] = f"{action}(" + ", ".join(names) + ")"
            
                               
        if sum(len(x) for x in files) > 0:
            kwargs["file_origin"] = f"{action}(" + ", ".join(files) + ")"
        
        
        f_annots = intersect_annotations if axis == 0 else merge_annotations
        f_aannots = intersect_annotations if axis == 0 else merge_array_annotations
        
        new_annotations = reduce(f_annots, annots)
        new_array_annotations = reduce(f_aannots, aannots)
        
        if axis == 0:
            kwargs["annotations"] = new_annotations
        else:
            kwargs.update(new_annotations)
            
        kwargs["array_annotations"] = new_array_annotations
        
        if axis == 1: #  merging
            # NOTE: 2021-11-08 19:39:33
            # code parts from neo.core.basesignal.BaseSignal.merge()
            data = np.hstack(signal_data)
            
            if isinstance(set_domain_start, float):
                t_start = set_domain_start * signals[0].times.units
            
            else:
                t_start = signals[0].t_start
            
            result = sig_klass(data, units=units_0, t_start=t_start,
                               dtype = signals[0].dtype,
                               sampling_rate=sampling_rate, **kwargs)
            
                
        else: # concatenation on the domain axis
            # NOTE: 2021-11-08 19:39:04
            # code parts from neo.AnalogSignal.concatenate()
            # check gaps and overlaps in the signal's domains
            if force_contiguous:
                data = np.vstack(signal_data)
                t_start = signals[0].t_start
            else:
                if ignore_domain:
                    t_start = 0*signals[0].times.units
                    t_stop = sum(s.duration.magnitude.item() for s in signals) * signals[0].times.units
                else:
                    combined_time_ranges = combine_time_ranges(((s.t_start, s.t_stop) for s in signals))
                    
                    missing_time_ranges=invert_time_ranges(combined_time_ranges)
                    
                    if len(missing_time_ranges):
                        diffs = np.diff(np.asarray(missing_time_ranges), axis=1)
                    else:
                        diffs = list()
                        
                    if any(diffs > signals[0].sampling_period):
                        if padding is False:
                            padding = True
                            
                        if padding is True:
                            padding = np.nan * units_0
                            
                        if isinstance(padding, pq.Quantity):
                            padding = padding.rescale(units_0).magnitude
                        else:
                            raise MergeError(f"Invalid padding {padding}")
                        
                    else:
                        padding = np.nan
                        
                    t_start = min([s.t_start for s in signals])
                    t_stop = max([s.t_stop for s in signals])
                    
                n_samples = int(np.rint(((t_stop - t_start) * sampling_rate).rescale("dimensionless").magnitude))
                
                #print("t_start", t_start, "t_stop", t_stop, "n_samples", n_samples)
                
                shape = (n_samples, ) + signals[0].shape[1:]
                
                data = np.full(shape=shape, fill_value=padding, dtype=signals[0].dtype)
            
                
            if isinstance(set_domain_start, float):
                t_start = set_domain_start * signals[0].times.units
            
            result = sig_klass(data,
                               sampling_rate = sampling_rate, 
                               t_start = t_start,
                               units = units_0,
                               **kwargs)
            
            if not force_contiguous:
                if not overwrite:
                    signals = signals[::-1]
                    
                sigs = list(signals)
                
                while len(sigs) > 0:
                    result.splice(sigs.pop(0), copy=False)
                
        if all(s.segment == signals[0].segment for s in signals):
            result.segment = signals[0].segment
                                    
        return result
           
    else:
        raise TypeError("Expecting a sequence of neo.AnalogSignal or datatypes.DataSignal objects")
                
def block_data_subset(block, **kwargs) -> neo.Block:
"""
    Parameters:
    ----------
    block: neo.Block
    
    Var-keyword parameters:
    ----------------------
    
    segment:    int or None; 
                when None, all segments in each block will be used;
                when int then only segments with given index will be used
                (i.e. only one segment from each block will be retained in 
                the concatenated data)
                    
    analog:     int, str, range, slice, typing.Sequence
                Indexing of analog signal(s) into each of the segments, that
                will be retained in the concatenated data. These include
                neo.AnalogSignal and datatypes.DataSignal
                
                This index can be (see neo_use_lookup_index):
                int, str (signal name), sequence of int or str, a range, a
                slice, or a numpy array of int or booleans.
                    
    irregular:  as analog, for irregularly sampled signals. These 
                include neo.IrregularlySampledSignal and 
                datatypes.IrregularlySampledDataSignal
    
    image:      as analog, for neo.ImageSequence objects (for neo version
                from 0.8.0 onwards)
                
    spikes:     as analog, for the spiketrains in the block's segments
    
"""             

@safeWrapper
def concatenate_blocks(*args, **kwargs):
    """Concatenates the segments in *args into a new Block.
    
    Copies of neo.Segment objects in the source data (*args) are appended in the
    order they are encountered.
    
    Optionally a subset of the signals contained in the source data are retained
    in the concatenated Block.
    
    Events, spike trains and epochs contained in the selected segments will be
    copied to the concatenated Block.
    
    Var-positional parameters:
    --------------------------
    args : a comma-separated list of neo.core.Block or neo.core.Segment objects
    
    Var-keyword parameters:
    -----------------------
    
    name            see neo.Block docstring
    description     see neo.Block docstring
    rec_datetime    see neo.Block docstring
    file_origin     see neo.Block docstring
    file_datetime   see neo.Block docstring
    annotation      see neo.Block docstring
    
    segment:    int or None; 
                when None, all segments in each block will be used;
                when int then only segments with given index will be used
                (i.e. only one segment from each block will be retained in 
                the concatenated data)
                    
    analog:     int, str, range, slice, typing.Sequence
                Indexing of analog signal(s) into each of the segments, that
                will be retained in the concatenated data. These include
                neo.AnalogSignal and datatypes.DataSignal
                
                This index can be (see neo_use_lookup_index):
                int, str (signal name), sequence of int or str, a range, a
                slice, or a numpy array of int or booleans.
                    
    irregular:  as analog, for irregularly sampled signals. These 
                include neo.IrregularlySampledSignal and 
                datatypes.IrregularlySampledDataSignal
    
    images:     as analog, for neo.ImageSequence objects (for neo version
                from 0.8.0 onwards)
                
    spikes:     as analog, for the spiketrains in the block's segments
                
    rename_segments:bool, optional (default True) - segments are renamed to the
        generic format f"segment_{k}" with 0<= k < len(ret.segments)
                    
                    
    Returns:
    -------
    a new neo.Block object
    
    NOTE: this is different from Block.merge() and Segment.merge() which basically
    append analog signals to same segments (thus requiring identical time bases)
    
    Example:
    
    block = concatenate_blocks2(getvars("data_name_prefix*"), segment_index=0)
    
    will concatenate the first segment (segment_index = 0) from all neo.Block 
    variables having names beginning with 'data_name_prefix' in the user 
    workspace.

    
    """
    from neo.core.spiketrainlist import SpikeTrainList
    if len(args) == 0:
        return None
    
    if len(args) == 1:
        if isinstance(args[0], str):
            try:
                args =  workspacefunctions.getvars(args[0], sort=True, sortkey=lambda x: x.rec_datetime)
                
            except Exception as e:
                print("String argument did not resolve to a list of neo.Block objects")
                traceback.print_exc()
                return
        else:
            args = args[0] # unpack the args tuple
    
    name = kwargs.get("name", "Concatenated block")
    description = kwargs.get("description", "Concatenated block")
    file_origin = kwargs.get("file_origin", "")
    file_datetime = kwargs.get("file_datetime", None)
    rec_datetime = kwargs.get("datetime", datetime.datetime.now())
    annotations = kwargs.get("annotations", dict())
    
    segment_index = kwargs.get("segment", None)
    analog_index = kwargs.get("analog", None)
    irregular_index = kwargs.get("irregular", None)
    image_index = kwargs.get("images", None)
    #channel_index = kwargs.get("channel", None)
    
    rename_segments = kwargs.get("rename_segments", True)
    
     # the returned data:
    ret = neo.core.Block(name=name, description=description, file_origin=file_origin,
                         file_datetime=file_datetime, rec_datetime=rec_datetime, 
                         **annotations)
    
    if isinstance(args, neo.core.Block):
        # a single Block object => make a deepcopy if no special children indices
        # are specified else return a new block
        
        new_block = deepcopy(args)
        
        if segment_index is not None:
            keep_segs_ndx = normalized_index(args.segments, segment_index)
            
        keep_segs = list(new_block.segments[k] for k in keep_segs_ndx)
        
        for s in keep_segs:
            if signal_index is not None:
                keep_ndx = normalized_index(s.analogsignals, signal_index)
                keep_signals = list(s.analogsignals[k] for k in keep_ndx)
                s.analogsignals[:] = keep_signals
                
            if irregular_index is not None:
                keep_ndx = normalized_index(s.irregularlysampledsignals, irregular_index)
                keep_signals = list(s.irregularlysampledsignals[k] for k in keep_ndx)
                s.irregularlysampledsignals[:] = keep_signals
            
            if image_index is not None:
                keep_ndx = normalized_index(s.imagesequences, irregular_index)
                keep_signals = list(s.imagesequences[k] for k in keep_ndx)
                s.imagesequences[:] = keep_signals
                
            if spiketrain_index is not None:
                keep_ndx = normalized_index(list(s.spiketrains), irregular_index) # because SpikeTrainList is Iterable but not Sequence
                keep_signals = list(s.spiketrains[k] for k in keep_ndx)
                s.spiketrains = SpikeTrainList(items = keep_signals)
                
        new_block.segments[:] = keep_segs
        
        if isinstance(args.name, str) and len(args.name.strip()):
            original_block_name = f" Block {args.name}"
        else:
            original_block_name = ""
            
    elif isinstance(args,(tuple, list)):
        for (k,arg) in enumerate(args):
            if isinstance(arg, neo.core.Block):
                if isinstance(arg.name, str) and len(arg.name.strip()):
                    original_block_name = f" of Block {arg.name}"
                else:
                    original_block_name = ""
                    
                if segment_index is None:
                    for (l,seg) in enumerate(arg.segments):
                        if isinstance(seg.name, str) and len(seg.name.strip()):
                            original_segment_name = f" ({seg.name})"
                        else:
                            original_segment_name = ""
                            
                        segment_origin_str = f"{original_segment_name}{original_block_name}"
                            
                        seg_name = seg.name if isinstance(seg.name, str) and len(seg.name.strip()) else f"Segment {l}{original_block_name}"
                        
                        if analog_index is None:
                            seg_ = deepcopy(seg)
                            #seg_ = neo_copy(seg)
                        else:
                            seg_ = neo.Segment(rec_datetime = seg.rec_datetime)
                            seg_.merge_annotations(seg)
                            # select signal indices
                            if isinstance(analog_index, str):
                                seg_.analogsignals.append(seg.analogsignals[get_index_of_named_signal(seg, analog_index)].copy())
                                
                            elif isinstance(analog_index, int):
                                seg_.analogsignals.append(seg.analogsignals[analog_index].copy())
                                
                            elif isinstance(analog_index, (tuple, list)):
                                for sigNdx in analog_index:
                                    if isinstance(sigNdx, str):
                                        sigNdx = get_index_of_named_signal(seg, sigNdx)
                                        
                                    elif not isinstance(sigNdx, int):
                                        raise TypeError("Signal index expected to be a str or an int; got %s instead" % type(sigNdx).__name__)
                                        
                                    seg_.analogsignals.append(seg.analogsignals[sigNdx].copy())
                                    
                            else:
                                raise TypeError("analog_index parameter expected to be None, a str, int or a sequence of these types; got %s instead" % type(analog_index).__name__)
                            
                        seg_.name = seg_name
                        seg_.annotate(origin=arg.file_origin, original_segment=f"Segment {l}{segment_origin_str}")
                        ret.segments.append(seg_)
        
                else:
                    if segment_index < len(arg.segments):
                        seg = arg.segments[segment_index]
                        
                        if isinstance(seg.name, str) and len(seg.name.strip()):
                            original_segment_name = f" ({seg.name})"
                        else:
                            original_segment_name = ""
                            
                        segment_origin_str = f"{original_segment_name}{original_block_name}"
                            
                        seg_name = seg.name if isinstance(seg.name, str) and len(seg.name.strip()) else f"Segment {segment_index}{original_block_name}"
                        
                        if analog_index is None:
                            seg_ = deepcopy(seg)
                            #seg_ = neo_copy(seg)
                        else:
                            seg_ = neo.Segment(rec_datetime = seg.rec_datetime)
                            seg_.merge_annotations(seg)
                            if isinstance(analog_index, str):
                                seg_.analogsignals.append(seg.analogsignals[get_index_of_named_signal(seg, analog_index)].copy())
                                
                            elif isinstance(analog_index, int):
                                seg_.analogsignals.append(seg.analogsignals[analog_index].copy())
                                
                            elif isinstance(analog_index, (tuple, list)):
                                for sigNdx in analog_index:
                                    if isinstance(sigNdx, str):
                                        sigNdx = get_index_of_named_signal(seg, sigNdx)
                                        
                                    elif not isinstance(sigNdx, int):
                                        raise TypeError("Signal index expected to be a str or an int; got %s instead" % type(sigNdx).__name__)
                                        
                                    seg_.analogsignals.append(seg.analogsignals[sigNdx].copy())
                                    
                            else:
                                raise TypeError("analog_index parameter expected to be None, a str, int or a sequence of these types; got %s instead" % type(analog_index).__name__)
                                
                        seg_.name = seg_name
                        seg_.annotate(origin=arg.file_origin, original_segment=f"Segment {segment_index}{segment_origin_str}")
                        ret.segments.append(seg_)
        
            elif isinstance(arg, neo.core.Segment):
                if isinstance(arg.name, str) and len(arg.name.strip()):
                    seg_name = arg.name
                else:
                    seg_name = f"Segment {k}"
                    
                if analog_index is None:
                    seg_ = copy(arg)
                    
                else:
                    seg_ = neo.Segment(rec_datetime = arg.rec_datetime)
                    
                    if isinstance(analog_index, str):
                        seg_.analogsignals.append(arg.analogsignals[get_index_of_named_signal(arg, analog_index)].copy())
                        
                    elif isinstance(analog_index, int):
                        seg_.analogsignals.append(arg.analogsignals[analog_index].copy())
                        
                    elif isinstance(analog_index, (tuple, list)):
                        for sigNdx in analog_index:
                            if isinstance(sigNdx, str):
                                sigNdx = get_index_of_named_signal(arg, sigNdx)
                                
                            elif not isinstance(sigNdx, int):
                                raise TypeError("Signal index expected to be a str or an int; got %s instead" % type(sigNdx).__name__)
                                
                            seg_.analogsignals.append(arg.analogsignals[sigNdx].copy())
                            
                    else:
                        raise TypeError("analog_index parameter expected to be None, a str, int or a sequence of these types; got %s instead" % type(analog_index).__name__)
                        
                seg_.name = seg_name
                seg_.annotate(origin=arg.file_origin, original_segment=seg_name)
                ret.segments.append(seg_)
                    
    else:
        raise TypeError("Expecting a neo.Block or a sequence of neo.Block objects, got %s instead" % type(args).__name__)
            
    if rename_segments:
        for k, s in enumerate(ret.segments):
            s.name = f"segment_{k}"
            
    return ret

@safeWrapper
def concatenate_blocks2(*args, **kwargs):
    """Concatenates the segments in *args into a new Block.
    
    Copies of neo.Segment objects in the source data (*args) are appended in the
    order they are encountered.
    
    Optionally a subset of the signals contained in the source data are retained
    in the concatenated Block.
    
    Events, spike trains and epochs contained in the selected segments will be
    copied to the concatenated Block.
    
    Var-positional parameters:
    --------------------------
    args : a comma-separated list of neo.core.Block or neo.core.Segment objects
    
    Var-keyword parameters:
    -----------------------
    
    name            see neo.Block docstring
    description     see neo.Block docstring
    rec_datetime    see neo.Block docstring
    file_origin     see neo.Block docstring
    file_datetime   see neo.Block docstring
    annotation      see neo.Block docstring
    
    segment:    int or None; 
                when None, all segments in each block will be used
                when int then only segments with given index will be used
                (i.e. only one segment from each block will be retained in 
                the concatenated data)
                    
    analog:     int, str, range, slice, typing.Sequence
                Indexing of analog signal(s) into each of the segments, that
                will be retained in the concatenated data. These include
                neo.AnalogSignal and datatypes.DataSignal
                
                This index can be (see neo_use_lookup_index):
                int, str (signal name), sequence of int or str, a range, a
                slice, or a numpy array of int or booleans.
                    
    irregular:  as analog, for irregularly sampled signals. These 
                include neo.IrregularlySampledSignal and 
                datatypes.IrregularlySampledDataSignal
    
    image:      as analog, for neo.ImageSequence objects (for neo version
                from 0.8.0 onwards)
                
                
    channel:    int, index  of the neo.ChannelIndex DEPRECATED
                    
                    
    Returns:
    -------
    a new neo.Block object
    
    NOTE: this is different from Block.merge() and Segment.merge() which basically
    append analog signals to same segments (thus requiring identical time bases)
    
    Example:
    
    block = concatenate_blocks(getvars("data_name_prefix*"), segment_index=0)
    
    will concatenate the first segment (segment_index = 0) from all neo.Block 
    variables having names beginning with 'data_name_prefix' in the user 
    workspace.

    
    """
    major, minor, dot = get_neo_version()
    
    neo_ge_8 = any([major >=0, minor >= 8])
    
    #if not isinstance(arg0, (neo.core.Block, neo.core.Segment)):
        #raise TypeError("First argument must be a Block or a Segment")
        
    if len(args) == 0:
        return None
    
    if len(args) == 1:
        if isinstance(args[0], str):
            try:
                args =  workspacefunctions.getvars(args[0], sort=True, sortkey=lambda x: x.rec_datetime)
                
            except Exception as e:
                print("String argument did not resolve to a list of neo.Block objects")
                traceback.print_exc()
                return
        else:
            args = args[0] # unpack the tuple
    
    name = kwargs.get("name", "Concatenated block")
    description = kwargs.get("description", "Concatenated block")
    file_origin = kwargs.get("file_origin", "")
    file_datetime = kwargs.get("file_datetime", None)
    rec_datetime = kwargs.get("datetime", datetime.datetime.now())
    annotations = kwargs.get("annotations", dict())
    
    segment_index = kwargs.get("segment", None)
    analog_index = kwargs.get("analog", None)
    irregular_index = kwargs.get("irregular", None)
    image_index = kwargs.get("image", None)
    channel_index = kwargs.get("channel", None)
    
     # the returned data:
    ret = neo.core.Block(name=name, description=description, file_origin=file_origin,
                         file_datetime=file_datetime, rec_datetime=rec_datetime, 
                         **annotations)
    
    #print(len(args))
    
    if isinstance(args, neo.core.Block):
        if segment_index is None:
            for (l,seg) in enumerate(args.segments):
                if analog_index is None:
                    #seg_ = copy(seg)
                    seg_ = deepcopy(seg)
                    #seg_ = neo_copy(seg)
                    seg_.name = "%s_%s" % (args.name, seg.name)
                    seg_.annotate(origin=args.file_origin, original_segment=segment_index)
                    ret.segments.append(seg_)
                    
                else:
                    # NOTE: 2020-03-13 08:48:10 
                    # we do NOT copy; instead we create a new segment, that we
                    # then populate with selected signals
                    seg_ = neo.Segment(rec_datetime = seg.rec_datetime, name="%s_%s" % (args.name, seg.name))
                    
                    seg_.merge_annotations(seg)
                    
                    seg_.annotate(origin=args.file_origin, original_segment=segment_index)
                    
                    signal_index = neo_use_lookup_index(seg, analog_index)
                    
                    sig_ = seg.analogsignals[signal_index]
                    sig_.segment = seg_
                    
                    #if isinstance(analog_index, str):
                        #seg_.analogsignals.append(seg.analogsignals[get_index_of_named_signal(seg, analog_index)].copy())
                        
                    #elif isinstance(analog_index, int):
                        #seg_.analogsignals.append(seg.analogsignals[analog_index].copy())
                        
                    #elif isinstance(analog_index, (tuple, list)):
                        #for sigNdx in analog_index:
                            #if isinstance(sigNdx, str):
                                #sigNdx = get_index_of_named_signal(seg, sigNdx)
                                
                            #elif not isinstance(sigNdx, int):
                                #raise TypeError("Signal index expected to be a str or an int; got %s instead" % type(sigNdx).__name__)
                                
                            #seg_.analogsignals.append(seg.analogsignals[sigNdx].copy())
                            
                    #else:
                        #raise TypeError("analog_index parameter expected to be None, a str, int or a sequence of these types; got %s instead" % type(analog_index).__name__)
                        
                    ret.segments.append(seg_)
        else:
            if segment_index < len(args.segments):
                # NOTE: 2020-03-13 08:51:32
                # get a reference to the segment with index "index"
                # then either:
                # a) copy it, if all signals are to be retained
                # b) create a new segment populated only with the selected signals
                seg = args.segments[segment_index] # a reference
                
                if analog_index is None:
                    seg_ = copy(seg)
                    seg_.name = "%s_%s" % (args.name, seg.name)
                    seg_.annotate(origin=args.file_origin, original_segment=segment_index)
                    ret.segments.append(seg_) # copy of original seg
                    
                else:
                    seg_ = neo.Segment(rec_datetime = seg.rec_datetime, name="%s_%s" % (args.name, seg.name)) # new seg
                    seg_.merge_annotations(seg)
                    seg_.annotate(origin=args.file_origin, original_segment=segment_index)
                    
                    analog_index = neo_use_lookup_index(seg, analog_index, )
                    
                    if isinstance(analog_index, str):
                        signal = seg.analogsignals[get_index_of_named_signal(seg, analog_index)].copy()
                        signal.segment = seg_
                        seg_.analogsignals.append(signal)
                        #seg_.analogsignals.append(seg.analogsignals[get_index_of_named_signal(seg, analog_index)].copy())
                        
                    elif isinstance(analog_index, int):
                        signal = seg.analogsignals[analog_index].copy()
                        signal.segment = seg_
                        seg_.analogsignals.append(signal)
                        
                    elif isinstance(analog_index, (tuple, list)):
                        for sigNdx in analog_index:
                            if isinstance(sigNdx, str):
                                sigNdx = get_index_of_named_signal(seg, sigNdx)
                                
                            elif not isinstance(sigNdx, int):
                                raise TypeError("Signal index expected to be a str or an int; got %s instead" % type(sigNdx).__name__)
                                
                            signal = seg.analogsignals[sigNdx].copy()
                            signal.segment = seg_
                            seg_.analogsignals.append(signal)
                            
                    else:
                        raise TypeError("analog_index parameter expected to be None, a str, int or a sequence of these types; got %s instead" % type(analog_index).__name__)
                        
                    ret.segments.append(seg_)
        
    elif isinstance(args,(tuple, list)):
        for (k,arg) in enumerate(args):
            if isinstance(arg, neo.core.Block):
                if segment_index is None:
                    for (l,seg) in enumerate(arg.segments):
                        seg_ = deepcopy(seg)
                        #seg_ = neo_copy(seg)
                        if analog_index is None:
                            seg_.annotate(origin=arg.file_origin, original_segment=segment_index)
                            ret.segments.append(seg_)
                            
                        else:
                            seg_ = neo.Segment(rec_datetime = seg.rec_datetime)
                            seg_.annotate(origin=arg.file_origin, original_segment=segment_index)
                            
                            if isinstance(analog_index, str):
                                seg_.analogsignals.append(seg.analogsignals[get_index_of_named_signal(seg, analog_index)].copy())
                                
                            elif isinstance(analog_index, int):
                                seg_.analogsignals.append(seg.analogsignals[analog_index].copy())
                                
                            elif isinstance(analog_index, (tuple, list)):
                                for sigNdx in analog_index:
                                    if isinstance(sigNdx, str):
                                        sigNdx = get_index_of_named_signal(seg, sigNdx)
                                        
                                    elif not isinstance(sigNdx, int):
                                        raise TypeError("Signal index expected to be a str or an int; got %s instead" % type(sigNdx).__name__)
                                        
                                    seg_.analogsignals.append(seg.analogsignals[sigNdx].copy())
                                    
                            else:
                                raise TypeError("analog_index parameter expected to be None, a str, int or a sequence of these types; got %s instead" % type(analog_index).__name__)
                                
                            ret.segments.append(seg_)
        
                            
                else:
                    if segment_index < len(arg.segments):
                        if analog_index is None:
                            seg_ = deepcopy(arg.segments[segment_index])
                            #seg_ = neo_copy(arg.segments[segment_index])
                            seg_.annotate(origin=arg.file_origin, original_segment=segment_index)
                            ret.segments.append(seg_)
                            #ret.segments.append(arg.segments[segment_index])
                            #ret.segments[-1].annotate(origin=arg.file_origin, original_segment=segment_index)
                            
                        else:
                            seg = arg.segments[segment_index]
                            
                            seg_ = neo.Segment(rec_datetime = seg.rec_datetime)
                            seg_.annotate(origin=arg.file_origin, original_segment=segment_index)
                            
                            if isinstance(analog_index, str):
                                seg_.analogsignals.append(seg.analogsignals[get_index_of_named_signal(seg, analog_index)].copy())
                                
                            elif isinstance(analog_index, int):
                                seg_.analogsignals.append(seg.analogsignals[analog_index].copy())
                                
                            elif isinstance(analog_index, (tuple, list)):
                                for sigNdx in analog_index:
                                    if isinstance(sigNdx, str):
                                        sigNdx = get_index_of_named_signal(seg, sigNdx)
                                        
                                    elif not isinstance(sigNdx, int):
                                        raise TypeError("Signal index expected to be a str or an int; got %s instead" % type(sigNdx).__name__)
                                        
                                    seg_.analogsignals.append(seg.analogsignals[sigNdx].copy())
                                    
                            else:
                                raise TypeError("analog_index parameter expected to be None, a str, int or a sequence of these types; got %s instead" % type(analog_index).__name__)
                                
                            ret.segments.append(seg_)
        
            elif isinstance(arg, neo.core.Segment):
                if analog_index is None:
                    ret.segments.append(arg)
                    
                else:
                    seg_ = neo.Segment(rec_datetime = arg.rec_datetime)
                    seg_.annotate(origin=arg.file_origin, original_segment=segment_index)
                    
                    if isinstance(analog_index, str):
                        seg_.analogsignals.append(arg.analogsignals[get_index_of_named_signal(arg, analog_index)].copy())
                        
                    elif isinstance(analog_index, int):
                        seg_.analogsignals.append(arg.analogsignals[analog_index].copy())
                        
                    elif isinstance(analog_index, (tuple, list)):
                        for sigNdx in analog_index:
                            if isinstance(sigNdx, str):
                                sigNdx = get_index_of_named_signal(arg, sigNdx)
                                
                            elif not isinstance(sigNdx, int):
                                raise TypeError("Signal index expected to be a str or an int; got %s instead" % type(sigNdx).__name__)
                                
                            seg_.analogsignals.append(arg.analogsignals[sigNdx].copy())
                            
                    else:
                        raise TypeError("analog_index parameter expected to be None, a str, int or a sequence of these types; got %s instead" % type(analog_index).__name__)
                        
                    ret.segments.append(seg_)
        
                    
    else:
        raise TypeError("Expecting a neo.Block or a sequence of neo.Block objects, got %s instead" % type(args).__name__)
            
    return ret

@safeWrapper
def get_events(*src:typing.Union[neo.Block, neo.Segment, typing.Sequence],
               as_dict:bool=False, flat:bool=False,
               triggers:typing.Optional[typing.Union[bool, str, int, type, typing.Sequence]]=None,
               match:str="==", clear:bool=False) -> list:
    """ Returns a collection of neo.Events embedded in data.
    
    Useful as a cache of events in neo data.
    
    NOTE: Below, the 'type' of a TriggerEvent is a TriggerEventType enum value.
    
    Variadic Parameters:
    ====================
    *src: neo.Block, neo.Segment, sequence (tuple, list) of neo.Block, sequence  
        (tuple, list) of neo.Segment, or None
        
    Named Parameters:
    =================
    as_dict: bool, default False
        When True, return a dictionary as explained below, under 'Returns'. 
        Otherwise, return a (possibly, ragged nested) list (see 'Returns')
        
    flat: bool, default False
        Used when as_dict is False.
        When 'flat' is True, returns a simple (1D) list of events in the order 
        of the neo.Block (and of neo.Segment in each block) in 'src'; segment 
        index if the faster-running index
        
        When False (the default), returns a ragged nested list of events, as
        explained below, under 'Returns'
        
    triggers:bool, TriggerEventType, str, int, or sequence of TriggerEventType, 
        str and/or int (mixed elements allowed in the sequence).
        
        Optional, default is None.
        
        
        When None, return all events found in data (i.e., both neo.Event and 
        core.triggerevent.TriggerEvent objects)
        
        If True, include only TriggerEvent objects (if found) in the return.
        
        If False, exclude TriggerEvent from the return
        
        If a TriggerEventType (see core.triggerevent module), return only those 
        TriggerEvent objects that have the type identical or related(*) to the 
        type(s) specified in 'triggers'.
        
        If a str, return only TriggerEvent objects with type identical or 
        related(*) to the TriggerEventType with name specified in 'triggers'
        
        If an int, return only TriggerEvent objects with type identical or 
        related(*) to the TriggerEventType with the value specified in 'triggers'.
        
        When a sequence (i.e. tuple or list), 'triggers' can contain a mixture of
        int, str, TriggerEventType, treated as above.
        
        (*) The default behaviour is to return TriggerEvent objects with type that
        match exactly the specification in 'triggers'. This behaviour can be finely
        tuned using the 'match' parameter, below.
        
    match: str, (optional, default is 'strict') - the rule for mathcing the type 
        of the returned TriggerEvent objects to the type(s) in 'triggers'
        
        Used when 'triggers' is a TriggerEventType object, a TriggerEventType 
        name (str), a TriggerEventType value (int), or a sequences of any of 
        these.
        
        Allowed values: 
        
        "strict" (default), "s", "==": 
            returns TriggerEvent objects with types that matches exactly the 
            TrigggerEventType object(s) specified by 'triggers'.
            
            When 'triggers' is a sequence, all TriggerEvent objects with types 
            that match any of those in 'triggers' will be returned.
        
        "up", "u", ">=": 
            returns TriggerEvent objects with types equal to those in 'triggers' 
            or derived from those in 'triggers' - i.e. included in these
            ('up-matching').
            
            The types in 'triggers' may be primitive or composite.
        
        "updistinct", "ud", ">": 
            returns TriggerEvent objects with composite types derived from those
            'triggers' (i.e. they include them) but are distinct from them
        
        "down", "dn", "d", "<=": 
            returns TriggerEvent objects with types equal to, or components of,
            those in 'triggers' - i.e. are included in the types in 'triggers'
            ('down-matching')
        
        "downdistinct", "dnd", "dd", "<": 
            returns TriggerEvent objects with types that are components of those
            those in 'triggers' (i.e. included by these) but are distinct from them
        
        "downprimitive", "dnp", "dp" "<<": 
            returns TriggerEvent objects with primitive type that are included 
            in those in 'triggers'
        
        "related", "rel", "r", "sim", "~": 
            returns TriggerEvent objects with types that are qeual to, include or
            are included in the types in 'triggers'
        
        "distinctrelated", "drel", "dr", "lgt", ><": 
            returns TriggerEvent objects with type that includes or is included
            y those in 'triggers' yet are distinct from them
            
        "distinct", "dt", "diff", "<>":
            returns TriggerEvent objects with type distinct from any of those
            in 'triggers' (but they may be included, or may include any of these)
            
        "unrelated", "ur", "/=":
            return TriggerEvent objects with types distinct and unrelated to those
            in 'triggers' (i.e. do not include and are not included in any of these)
        
        
        For the meaning of 'primitive' and 'composite' TriggerEventType objects,
        ans their inclusion relationships,  see the documentation for 
        triggerevent.TriggerEventType
        
    clear:bool. Optional(default is False)
        When True, clears the selected events from the data; returns None
    
    Returns:
    =======
    By default (i.e. with as_dict and flat both False) returns a ragged nested
    list of neo.Event (or TriggerEvent) objects, with nesting level dependent on
    what is contained in 'src':
    
        Type of src:                Indexing levels of the returned list:
        --------------------------------------------------------------------------
        Sequence of neo.Block       3   e.g.,
                                            [
                                                [...],  # block index
                                                [
                                                    [...], # segment index
                                                    [...,block_i_ segment_j_event_k, ...],
                                                    [...]
                                                ],
                                                [...]
                                            ]
        
                                    outer index (level 0) = index (i) of block 
                                                            in src sequence
                                    level 1 index         = index (j) of the 
                                                            segment in block_i
                                    inner index (level 2) = index (k) of the 
                                                            event in segment j 
                                                            of block i
        
        neo.Block, 
        sequence of neo.Segments    2   e.g., 
                                            [
                                                [...], # segment index
                                                [
                                                    [...],
                                                    [..., segment_i_event_j],
                                                    [...]
                                                ],
                                                [...]
                                            ]
                                            
                                    outer index (level 0) = index (i) of the
                                                            segment in src (or
                                                            src.segments when
                                                            src is a neo.Block)
                                                            
                                    inner index (level 1) = index (j) of the event
                                                            in segment i
                                                            
            NOTE that in the case of neo.Block, its 'segments' is in fact a sequence
            of neo.Segment objects
        
        neo.Segment                 1   i.e., [..., event_i, ...]
        
        None                        0   i.e., [] - empty list!
        
    
    When 'as_dict' is True, returns a dict which depends on the contents of 'src':
    
        When 'src' is a sequence of neo.Block objects, returns:
    
            {"block_i": {"segment_j": event_list}}
        
            where:
                'i' runs from 0 to the number of neo.Block objects in 'src'
                'j' runs from 0 to len(block_i.segments), for each block (i.e., 
                    'j' runs varies faster)
        
        When 'src' is a neo.Block object or a sequence of neo.Segments:
            {"segment_i": event_list}
            
            where 'i' runs from 0 to len(src) (or len(src.segments) is src is 
                a neo.Block)
                
        When 'src' is a neo.Segment:
            {"segment_0": event_list}
            
        When no events have been found in 'src' the function returns an empty list.
        
    """
    # NOTE 2021-03-21 17:54:12
    # src is an unpacked tuple! It may be convenient to supply data already packed
    # as a single tuple or list parameter - this will be assigned to src[0]
    # NOTE: 2021-03-21 18:13:04
    # new return type!
    
    from .triggerprotocols import (TriggerEvent, TriggerEventType,)
    
    # NOTE: 2021-04-14 09:39:42
    # below, x is a TriggerEvent object and y is a TriggerEventType object, or a
    # list of TriggerEventType objects
    
    if not isinstance(match, str):
        raise TypeError("match rule expected a str; got %s instead" % type(match).__name__)
    
    if match in ("strict", "s", "=="):
        typefilter = lambda x,y: x.type == y if isinstance(y, TriggerEventType) else any([x.type == y_ for y_ in y])
        
    elif match in ("down", "dn", "d", "le", "<="):
        # match y to trigger events with same type as y or with a type that is a 
        # component of y;
        # y must be composite
        typefilter = lambda x, y: (x.type == y or x.type.is_component_of(y)) if isinstance(y, TriggerEventType) else any([(x.type == y_ or x.type.is_component_of(y_)) for y_ in y])
        
    elif match in ("downdistinct", "dnd", "dd", "lt", "<"):
        # match y to trigger events with type that is a component of y, but different
        # from y;
        # y must be composite
        typefilter = lambda x, y: x.type.is_component_of(y) if isinstance(y, TriggerEventType) else any([x.type.is_component_of(y_) for y_ in y])
        
    elif match in ("downprimtive", "dnp", "dp", "lp", "<<"):
        # find trigger events of types that are primitives of y;
        # y must be composite;
        # since this returns primitives, events with type that exactly match y
        # will be excluded
        typefilter = lambda x, y: x.type.is_primitive_of(y) if isinstance(y, TriggerEventType) else any([x.type.is_primitive_of(y_) for y_ in y])
        
    elif match in ("up", "u", "ge", ">="):
        # match trigger event with same type as y or with a type that is a 
        # composite of y (ncludes y)
        # y can be a primitive type or a composite type
        typefilter = lambda x, y: (x.type == y or x.type.includes(y)) if isinstance(y, TriggerEventType) else any([(x.type == y_ or x.type.includes(y_)) for y_ in y])
        
    elif match in ("updistinct", "ud", "gt", ">"):
        # match trigger event with type that is a composite of (includes) y
        # yet is different than y
        typefilter = lambda x, y: x.type.includes(y) if isinstance(y, TriggerEventType) else any([x.type.includes(y_) for y_ in y])
        
    elif match in ("related", "rel", "r", "sim", "~"):
        typefilter = lambda x, y: (x.type == y or x.type.is_component_of(y) or x.type.includes(y)) if isinstance(y, TriggerEventType) else any([(x.type == y_ or x.type.is_component_of(y_) or x.type.includes(y_)) for y_ in y])
        
    elif match in ("distinctrelated", "drel", "dr", "lgt", "><"):
        typefilter = lambda x, y: (x.type.is_component_of(y) or x.type.includes(y)) if isinstance(y, TriggerEventType) else any([(x.type.is_component_of(y_) or x.type.includes(y_)) for y_ in y])
        
    elif match in ("distinct", "dt", "diff", "<>"):
        typefilter = lambda x, y: x.type != y if isinstance(y, TriggerEventType) else all([x.type != y_ for y_ in y])
        
    elif match in ("unrelated", "ur", "/="):
        typefilter = lambda x, y: (x.type != y and not x.type.includes(y) and not y.includes(x.type)) if isinstance(y, TriggerEventType) else all([(x.type != y_ and not x.type.includes(y_) and not y_.includes(x.type)) for y_ in y])
        
    else:
        raise ValueError("Unknown match rule specification %s" % match)
    
    if len(src) == 0:
        return []
    
    elif len(src) == 1:
        src = src[0]
        
    if isinstance(triggers, bool):
        filtfn = partial(filter, lambda x: isinstance(x, TriggerEvent)) if triggers else partial(filterfalse, lambda x: isinstance(x, TriggerEvent))
        
    elif isinstance(triggers, (int, str, TriggerEventType)):
        if isinstance(triggers, (int, str)):
            #if triggers not in TriggerEventType.values() and triggers not in TriggerEventType.names():
                #raise ValueError("Unknown trigger event type %s" % triggers)
            
            triggers = TriggerEventType.type(triggers)
            
        filtfn = partial(filter, lambda x: isinstance(x, TriggerEvent) and typefilter(x, triggers))
            
    elif isinstance(triggers, (tuple, list)):
        triggers = [TriggerEventType.type(t) for t in triggers if isinstance(t, (TriggerEventType, int, str))]
        
        filtfn = partial(filter, lambda x: isinstance(x, TriggerEvent) and any([typefilter(x, tr) for tr in triggers]))
        
    else:  # anything esle: return all events
        filtfn = partial(filter, lambda x: True)
        
    if clear: # function is used to clear events
        if isinstance(src, neo.Block):
            target = src.segments
        elif isinstance(src, neo.Segment):
            target = [src]
        elif isinstance(src, (tuple, list)):
            if all([isinstance(x, neo.Segment) for x in src]):
                target = src
            elif all([isinstance(x, neo.Block) for x in src]):
                target = chain(*[x.segments for x in src])
                
        else:
            raise TypeError("Expecting a sequence of neo.Block or neo.Segments (no type mixing)")
        
        
        if triggers is None:
            for s in target:
                s.events.clear()
                
            return
        
        else:
            for s in target:
                evts = [e for e in filtfn(s.events)]
                all_events_ndx = range(len(evts))
                out_events = [(endx, e) for endx, e in enumerate(evts)]
                if len(out_events):
                    (evndx, evs) = zip(*out_events)
                    keep_events = [evts[k] for k in all_events_ndx if k not in evndx]
                    s.events[:] = keep_events
                    
            return
        
    else: # function is used to query events
        if isinstance(src, neo.Block):
            if as_dict:
                return {"block_0": dict([("segment_%d" % k, [e for e in filtfn(s.events)]) for k, s in enumerate(src.segments)])}
            else:
                ret = [[e for e in filtfn(s.events)] for s in src.segments] # ragged nested sequence
                if flat: 
                    return [e for e in chain.from_iterable(ret)] # flattened list
                else:
                    return ret
                    #return [e for e in chain.from_iterable([[e for e in filtfn(s.events)] for s in src.segments])]
                #else: # ragged nested sequence
                    #return [[e for e in filtfn(s.events)] for s in src.segments]
        
        elif isinstance(src, neo.Segment):
            if as_dict:
                return {"segment_0": [e for e in filtfn(src.events)]}
            else:
                return [e for e in filtfn(src.events)] # by default only a flattened list

        elif isinstance(src, (tuple, list)):
            if all([isinstance(v, neo.Block) for v in src]):
                if as_dict:
                    return dict([("block_%d" % kb, dict([("segment_%d" % k, [e for e in filtfn(s.events)]) for k,s in enumerate(b.segments)])) for kb, b in enumerate(src)])
                else:
                    #ret = [[[e for e in filtfn(s.events)] for s in b.segments] for b in src]
                    if flat:
                        #return [e for e in chain.from_iterable([ee for ee in chain()])]
                        return [e for e in chain.from_iterable([[e for e in filtfn(s.events)] for s in chain(*[b.segments for b in src])])]
                    else:  # ragged nested sequence
                        return [[[e for e in filtfn(s.events)] for s in b.segments] for b in src]
            
            elif all([isinstance(s, neo.Segment) for s in src]):
                if as_dict:
                    return dict([("segment_%d" % k, [e for e in filtfn(s.events)]) for k, s in enumerate(src)])
                else:
                    if flat:
                        return [e for e in chain(*[[o for o in filtfn(s.events)] for s in src])]
                    else: # ragged nested sequence
                        return [[e for e in filtfn(s.events)] for s in src]
            
            else:
                raise TypeError("Expecting a uniformly typed sequence of neo.Block or neo.Segment objects")
            
        elif src is None:
            return []
            
        else:
            raise TypeError("Unexpected parameter type %s" % type(src[0]).__name__)
        
def check_ephys_data_collection(x:typing.Any, mix:bool=False):
    """Checks if x is a data type representing a collection of electrophysiology data.
    This check is performed too often not to warrant a function for it.
    
    Parameters:
    ----------
    x: data to be checked
    mix: bool (optional, default is False)
        When True, allow mixing of neo.Block and neo.Segment in x, when x is a 
        sequence (tuple, list)
    
 
    See neoutils.check_ephys_data for what is understood by electrophysiolgy data
    
    """
    if isinstance(x, ephys_data_collection):
        return True
    
    if isinstance(x, (tuple, list)):
        if mix:
            return all([isinstance(x_, ephys_data_collection) for x_ in x])
            
        else:
            return any([all([isinstance(x_, e_type) for x_ in x]) for e_type in ephys_data_collection])
        
    else:
        if mix:
            return isinstance(x, ephys_data_collection)
        
        else:
            return any([isinstance(x, e_type) for e_type in ephys_data_collection])
            
    return False
    
def check_ephys_data(x:typing.Any, mix:bool=False):
    """Checks if x is a electrophysiology data type.
    
    This check is performed too often not to warrant a function for it.
    
    Electrophysiology data types are:
    neo.Block, neo.Segment, neo.AnalogSignal, neo.IrregularlySampledSignal, 
    neo.SpikeTrain, 
    core.datatypes.DataSignal, and core.datatypes.IrregularlySampledDataSignal
    
    They MAY contain attributes that are ancillary data types such as neo.Event, 
    neo.Epoch, and other (non-signal-like) data types, as well as 
    core.triggerevent.TriggerEvent objects. However, these are hardly useful on
    their own, as electrophysiology data.
    
    DataSignal and IrregularlySampledDataSignal are included because they emulate
    their respective neo counterparts but allow the signal domain to be other 
    than time. While electrophysiology data usually represents a physical quantity
    that varies over time, these two data types can be used to represent quantities
    that vary over space, for example, the fluorescence intensity of an ion or
    voltage indicator.
    
    Although electrophysiology data can be represented by less specialized data 
    types such as arrays and matrices (numpy arrays, pandas Series, etc)  they
    are rather too generic to be considered here.
        
    Parameters:
    ----------
    x: data to be checked
    
    mix: bool (optional, default is False)
        When True, allow mixing of neo.Block and neo.Segment in x, when x is a 
        sequence (tuple, list)
    
    """
    if isinstance(x, (tuple, list)):
        if mix:
            return all([isinstance(x_, ephys_data) for x_ in x])
        
        else:
            return any([all([isinstance(x_, e_type) for x_ in x]) for e_type in ephys_data])
    
    else:
        if mix:
            return isinstance(x, ephys_data)
        else:
            return any([isinstance(x, e_type) for e_type in ephys_data])
    
    return False
        
def clear_events(*src:typing.Union[neo.Block, neo.Segment, typing.Sequence], 
                 triggers:typing.Optional[typing.Union[bool, str, int, type, typing.Sequence]]=None,
                 match:str="=="):
                 #triggersOnly:bool=False, triggerType=None):
    """Shorthand for clearing neo.Event objects embedded in src.
    
    This includes TriggerEvent objects!
    
    e.g. [s.events.clear() for s in src.segments] where src is a neo.Block
    
    NOTE: To remove a specific event, use remove_events.
    
    See also: remove_events
    
    Parameters:
    ===========
    
    src: a neo.Block, or a neo.Segment, or a sequence (tuple, list) whith
        elements of the same type, either neo.Segment or neo.Block.
    
    Keyword parameters:
    ==================
    
    triggers:bool, TriggerEventType, str, int, or sequence of TriggerEventType, 
        str and/or int (mixed elements allowed in the sequence).
        
        Optional, default is None.
        
        
        When None, remove all events found in data (i.e., both neo.Event and 
        core.triggerevent.TriggerEvent objects)
        
        If True, remove only TriggerEvent objects (if found).
        
        If False, remove all except TriggerEvent objects
        
        If a TriggerEventType (see core.triggerevent module), remove only those 
        TriggerEvent objects that have the type identical or related(*) to the 
        type(s) specified in 'triggers'.
        
        If a str, remove only TriggerEvent objects with type identical or 
        related(*) to the TriggerEventType with name specified in 'triggers'
        
        If an int, remove only TriggerEvent objects with type identical or 
        related(*) to the TriggerEventType with the value specified in 'triggers'.
        
        When a sequence (i.e. tuple or list), 'triggers' can contain a mixture of
        int, str, TriggerEventType, treated as above.
        
        (*) The default behaviour is to remove TriggerEvent objects with type that
        matches exactly the specification in 'triggers'. This behaviour can be finely
        tuned using the 'match' parameter, below.
        
    match: str, (optional, default is 'strict') - the rule for mathcing the type 
        of the returned TriggerEvent objects to the type(s) in 'triggers'
        
        Used when 'triggers' is a TriggerEventType object, a TriggerEventType 
        name (str), a TriggerEventType value (int), or a sequences of any of 
        these.
        
        Allowed values: 
        
        "strict" (default), "s", "==": 
            select TriggerEvent objects with types that matches exactly the 
            TrigggerEventType object(s) specified by 'triggers'.
            
            When 'triggers' is a sequence, all TriggerEvent objects with types 
            that match any of those in 'triggers' will be returned.
        
        "up", "u", ">=": 
            select TriggerEvent objects with types equal to those in 'triggers' 
            or derived from those in 'triggers' - i.e. included in these
            ('up-matching').
            
            The types in 'triggers' may be primitive or composite.
        
        "updistinct", "ud", ">": 
            select TriggerEvent objects with composite types derived from those
            'triggers' (i.e. they include them) but are distinct from them
        
        "down", "dn", "d", "<=": 
            select TriggerEvent objects with types equal to, or components of,
            those in 'triggers' - i.e. are included in the types in 'triggers'
            ('down-matching')
        
        "downdistinct", "dnd", "dd", "<": 
            select TriggerEvent objects with types that are components of those
            those in 'triggers' (i.e. included by these) but are distinct from them
        
        "downprimitive", "dnp", "dp" "<<": 
            select TriggerEvent objects with primitive type that are included 
            in those in 'triggers'
        
        "related", "rel", "r", "sim", "~": 
            select TriggerEvent objects with types that are qeual to, include or
            are included in the types in 'triggers'
        
        "distinctrelated", "drel", "dr", "lgt", ><": 
            select TriggerEvent objects with type that includes or is included
            y those in 'triggers' yet are distinct from them
            
        "distinct", "dt", "diff", "<>":
            select TriggerEvent objects with type distinct from any of those
            in 'triggers' (but they may be included, or may include any of these)
            
        "unrelated", "ur", "/=":
            select TriggerEvent objects with types distinct and unrelated to those
            in 'triggers' (i.e. do not include and are not included in any of these)
        
        
        For the meaning of 'primitive' and 'composite' TriggerEventType objects,
        ans their inclusion relationships,  see the documentation for 
        triggerevent.TriggerEventType
    See also: get_events
        
        
    """
    get_events(*src, triggers=triggers, clear=True)
    #from .triggerprotocols import (TriggerEvent, TriggerEventType,)

    ## NOTE: 2021-04-14 09:39:42
    ## below, x is a TriggerEvent object and y is a TriggerEventType object.
    
    #if not isinstance(match, str):
        #raise TypeError("match rule expected a str; got %s instead" % type(match).__name__)
    
    #if match in ("strict", "s", "=="):
        #typefilter = lambda x,y: x.type == y
        
    #elif match in ("down", "dn", "d", "le", "<="):
        ## match y to trigger events with same type as y or with a type that is a 
        ## component of y;
        ## y must be composite
        #typefilter = lambda x, y: x.type == y or x.type.is_component_of(y)
        
    #elif match in ("downdistinct", "dnd", "dd", "lt", "<"):
        ## match y to trigger events with type that is a component of y, but different
        ## from y;
        ## y must be composite
        #typefilter = lambda x, y: x.type.is_component_of(y)
        
    #elif match in ("downprimtive", "dnp", "dp", "lp", "<<"):
        ## find trigger events of types that are primitives of y;
        ## y must be composite;
        ## since this returns primitives, events with type that exactly match y
        ## will be excluded
        #typefilter = lambda x, y: x.type.is_primitive_of(y)
        
    #elif match in ("up", "u", "ge", ">="):
        ## match trigger event with same type as y or with a type that is a 
        ## composite of y (ncludes y)
        ## y can be a primitive type or a composite type
        #typefilter = lambda x, y: x.type == y or x.type.includes(y)
        
    #elif match in ("updistinct", "ud", "gt", ">"):
        ## match trigger event with type that is a composite of (includes) y
        ## yet is different than y
        #typefilter = lambda x, y: x.type.includes(y)
        
    #elif match in ("related", "rel", "r", "sim", "~"):
        #typefilter = lambda x, y: x.type == y or x.type.is_component_of(y) or x.type.includes(y)
        
    #elif match in ("distinctrelated", "drel", "dr", "lgt", "><"):
        #typefilter = lambda x, y: x.type.is_component_of(y) or x.type.includes(y)
        
    #elif match in ("distinct", "dt", "diff", "<>"):
        #typefilter = lambda x, y: x.type != y
        
    #elif match in ("unrelated", "ur", "/="):
        #typefilter = lambda x, y: x.type != y and not x.type.includes(y) and not y.includes(x.type)
        
    #else:
        #raise ValueError("Unknown match rule specification %s" % match)
    #if isinstance(src, neo.Block):
        #target = src.segments
        
    #elif isinstance(src, neo.Segment):
        #target = [src]
        
    #elif isinstance(src, (tuple, list)):
        #if all([isinstance(x, neo.Segment) for x in src]):
            #target = src
            
        #elif all([isinstance(x, neo.Block) for x in src]):
            #target = chain(*[x.segments for x in src])
            
        #else:
            #raise TypeError("Expecting a sequence of neo.Block or neo.Segments (no type mixing)")
        
    #else:
        #raise TypeError("Expecting a neo.Block, a neo.Segment or a sequence of neo.Segment objects; got %s instead" % type(src).__name__)
    
    #for s in target:
        #all_events_ndx = range(len(s.events))
        
        #trigs = []
        ## if triggerType has been specified, remove only trigger events of those
        ## types
        
        #if triggers is None:
            #s.events.clear()
        #else:
            #if isinstance(triggers, bool):
                #if triggers:
                    #out_events = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent)]
                    
                #else:
                    #out_events = [(endx, e) for (endx, e) in enumerate(s.events) if not isinstance(e, TriggerEvent)]
                    
            #elif isinstance(triggers, int):
                #if triggers not in TriggerEventType.values():
                    #raise ValueError("Unknown trigger event type value %d" % triggers)
                
                #out_events = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent) and e.type.value & triggers]
            
            #elif isinstance(triggers, str):
                #if triggers not in TriggerEventType.names():
                    #raise ValueError("Unknown trigger event type name %s" % triggers)
                #out_events = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent) and e.type.nameand(triggers)]
            
            #elif isinstance(triggers, TriggerEventType):
                #out_events = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent) and e.type & triggers]

            #elif isinstance(triggers, (tuple, list)) and all([isinstance(v, (int, str, TriggerEventType)) for v in triggers]):
                #bad_type_names = [t for t in triggers if isinstance(t, str) and t not in TriggerEventType.names()]
                
                #if len(bad_type_names):
                    #raise ValueError("Unknown trigger event type names %s" % " ".join(bad_type_names))
                
                #bad_type_values = [t for t in triggers if isinstance(t, int) and t not in TriggerEventType.values()]
                
                #if len(bad_type_values):
                    #raise ValueError("Unknown trigger event type valuess %s" % bad_type_values)
                    
                #out_events = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent) and (e.type in triggers or e.type.name in triggers or e.type.value in triggers)]
                
            #else:
                #out_events = [(endx, e) for (endx, e) in enumerate(s.events)]
                
            #if len(out_events):
                #(evndx, evs) = zip(*out_events)
                
                #keep_events = [s.events[k] for k in all_events_ndx if k not in evndx]
                
                #s.events[:] = keep_events
            
        
        #if isinstance(triggerType, TriggerEventType):
            #trigs = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent) and e.type & triggerType]
            
        #elif isinstance(triggerType, str):
            #if triggerType in TriggerEventType.names():
                #trigs = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent) and e.type & TriggerEventType[triggerType]]
                
            #else:
                #raise ValueError("Unknown trigger event type %s" % triggerType)
            
        #elif isinstance(triggerType, int):
            #if triggerType in TriggerEventType.values():
                #trigs = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent) and e.type & TriggerEventType(triggerType)]
                
            #else:
                #raise ValueError("Unknown trigger event type %d" % triggerType)
                
        #elif isinstance(triggerType, (tuple, list)):
            #if all([isinstance(t, TriggerEventType) for t in triggerType]):
                #ttypes = triggerType
                
            #elif all([isinstance(t, str) and t in TriggerEventType.names() for t in triggerType]):
                #ttypes = [TriggerEventType[t] for t in triggerType]
                
            #elif all([isinstance(t, int) and t in TriggerEventType.values() for t in triggerType]):
                #ttypes = [TriggerEventType(t) for t in triggerType]
                
            #else:
                #raise TypeError("Invalid 'triggerType' parameter %s" % triggerType)
            
            #trigs = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent) and e.type in ttypes]
            
        #elif triggersOnly:
            ## remove all trigger events regardless of their type as triggerType
            ## had not been specified
            #trigs = [(endx, e) for (endx, e) in enumerate(s.events) if isinstance(e, TriggerEvent)]
            

        #if len(trigs):
            ##selective removal of trigger events, optionally of specified type(s)
            #(endx, evs) = zip(*trigs)
            
            #keep_events = [s.events[k] for k in all_events_ndx if k not in endx]
            
            #s.events[:] = keep_events
            
        #else:
            #s.events.clear()
                
@safeWrapper
def get_non_empty_events(sequence:(tuple, list)):
    from .triggerprotocols import TriggerEvent
    #from .triggerprotocols import (TriggerEvent, TriggerEventType, TriggerProtocol)
    if len(sequence) == 0:
        return list()
    
    if not all([isinstance(e, (neo.Event, TriggerEvent)) for e in sequence]):
        raise TypeError("Expecting a sequence containing only neo.Event or datatypes.TriggerEvent objects")
    
    return [e for e in sequence if len(e)]

@safeWrapper
def get_non_empty_spike_trains(sequence:(tuple, list)):
    if len(sequence) == 0:
        return list()
    
    if not all([isinstance(e, neo.SpikeTrain) for e in sequence]):
        raise TypeError("Expecting a sequence containing only neo.SpikeTrain objects")
    
    return [s for s in sequence if len(s)]
    
@safeWrapper
def get_non_empty_epochs(sequence:(tuple, list)):
    if len(sequence) == 0:
        return list()
    
    if not all([isinstance(e, neo.Epoch) for e in sequence]):
        raise TypeError("Expecting a sequence containing only neo.Epoch objects")
    
    return [e for e in sequence if len(e)]
    
def remove_events(event, segment, byLabel=True):
    """Removes a specific event from the neo.Segment "segment"
    
    Parameters:
    ==========
    event: a neo.Event, an int, a str or a datatypes.TriggerEventType.
    
        When a neo.Event (or TriggerEvent), the functions remove the reference 
        to that event, if found, or any event that is identical to the specified 
        one, if found.
        NOTE: two event objects can have identical time stamps, labels,
        names, units, and in the case of TriggerEvent, event type, even if they
        are distinct Python objects (e.g., one is a deep copy of the other).
        
        When an int, the function removes the event at index "event" in the
            segment's events list (if the index is valid)
            
        When a str, the function removes _ALL_ the events for having either the
            label (if byLabel is True) or name (is byLabel is False) equal to 
            the "event" parameter, if such events are found in the segment.
            
        When a TriggerEventType, _ALL_ TriggerEvent objects of this type will be
        removed, if found - NOTE: This is similar to calling clear_events with
        specific triggerType parameter.
        
        See also: clear_events
            
    Keyword parameters:
    ==================
    byLabel: boolean default True. Used when event is a str (see above)
        
        When True, _ALL_ events with label given by "event" parameter will be removed,
            if found.
            
        Otherwise, _ALL_ events with name given by "event" parameter will be removed,
            if found.
    """
    if not isinstance(segment, neo.Segment):
        raise TypeError("segment expected to be a neo.Segment; got %s instead" % type(segment).__name__)
    
    if len(segment.events) == 0:
        return
    
    if isinstance(event, neo.Event):
        if event in segment.events: # find event reference stored in events list
            evindex = segment.events.index(event)
            del segment.events[evindex]
            
        else: # find events stored in event list that have same attributes as event
            evs = [(k,e) for (k,e) in enumerate(segment.events) if e.is_same_as(event)]
            
            if len(evs):
                (evndx, events) = zip(*evs)
                all_events_ndx = range(len(segment.events))
                
                keep_events = [segment.events[k] for k in all_events_ndx if k not in evndx]
                
                segment.events[:] = keep_events
                
    elif isinstance(event, int):
        if event in range(len(segment.events)):
            del segment.events[event]
            
    elif isinstance(event, str):
        evs = []
        
        if byLabel:
            evs = [(k,e) for (k,e) in segment.events if np.any(e.labels == event)]
            
        else:
            evs = [(k,e) for (k,e) in segment.events if e.name == event]
            
        if len(evs):
            (evndx, events) = zip(*evs)
            all_events_ndx = range(len(segment.events))
            
            keep_events = [segment.events[k] for k in all_events_ndx if k not in evndx]
            
            segment.events[:] = keep_events
            
    elif isinstance(event, TriggerEventType):
        evs = [(k,e) for (k,e) in segment.events if isinstance(e, TriggerEvent) and e.type & event]

        if len(evs):
            (evndx, events) = zip(*evs)
            all_events_ndx = range(len(segment.events))
            
            keep_events = [segment.events[k] for k in all_events_ndx if k not in evndx]
            
            segment.events[:] = keep_events
            
    else:
        raise TypeError("event expected to be a neo.Event, an int, a str or a datatypes.TriggerEventType; got %s instead" % type(event).__name__)
    
        
def is_same_as(e1, e2, rtol = 1e-4, atol =  1e-4, equal_nan = True):
    """Returns True if the neo.Events e1 and e2 have identical time stamps, units, labels and names.
    
    In addition, if e1 and e2 are datatype.TriggerEvents, checks if they have the 
    same type.
    
    Time stamps are compared within a relative and absolute tolerances by
    calling numpy.isclose()
    
    Parameters:
    ==========
    
    e1, e2: neo.Event objects (including datatypes.TriggerEvent)
    
    Keyword parameters:
    ==================
    
    rtol, atol: float values, default for both is 1e-4 (see numpy.isclose())
    
    equal_nan: boolean default is True (see numpy.isclose())
    
    """
    if any([not isinstance(e, (neo.Event, TriggerEvent)) or "Event" not in type(e).__name__ for e in (e1,e2)]):
        return False
    
    if all([isinstance(e, TriggerEvent) for e in (e1,e2)]):
        return e1.is_same_as(e2)
    
    compatible_units = e1.units == e2.units
    
    if not compatible_units:
        e1_dim    = pq.quantity.validate_dimensionality(e1.units)
        
        e2_dim   = pq.quantity.validate_dimensionality(e2.units)
        
        if e1_dim != e2_dim:
            try:
                cf = pq.quantity.get_conversion_factor(e2_dim, e1_dim)
                compatible_units = True
                
            except AssertionError:
                compatible_units = False
            
    result = compatible_units
    
    if result:
        result &= e2.times.flatten().size == e1.times.flatten().size
    
    if result:
        result &= np.all(np.isclose(e2.times.magnitude, e1.times.magnitude,
                                    rtol=rtol, atol=atol,equal_nan=equal_nan))
    
    if result: 
        result &= np.all(np.isclose(e2.magnitude, e1.magnitude, 
                                    rtol=rtol, atol=atol, equal_nan=equal_nan))
        
    if result:
        result &= e2.labels.flatten().size == e1.labels.flatten().size
        
    if result:
        result &= np.all(e2.labels.flatten() == e2.labels.flatten)
        
    if result:
        result &= e1.name == e2.name
        
    return result
    
        
    
def lookup(signal, value, channel=0, rtol=1e-05, atol=1e-08, equal_nan = False, right=False):
    """Lookup signal values for given domain value(s).
    
    Parameters:
    ----------
    signal: one of neo.AnalogSignal, neo.IrregularlySampledSignal, 
            datatypes.DataSignal, or datatypes.IrregularlySampledDataSignal.
        
    value: float scalar, the nominal value of the domain, or a monotonic 
            sequence (tuple, list) of scalars.
            
            When a scalar, the function looks up the signal samples that correspond 
            to domain values close to value within the atol and rtol, 
            using numpy.isclose().
            
            NOTE 1:
            
            `a` and `b` are "close to" each other when
            
            absolute(`a` - `b`) <= (`atol` + `rtol` * absolute(`b`))
            
            When a sequence, its elements are boundaries of bins to which domain
            values belong (half-open intervals, direction specified by the 
            value of `right`); the function looks up signal samples for the 
            domain values with indices that fall these bins, as determined using 
            numpy.digitize().
            
            NOTE 2: From numpy.digitize docstring:
            
            numpy.digitize(x, bins, right=False)[source]
                
                Return the indices of the bins to which each value in input array belongs.
                right     order of bins   returned index i satisfies  meaning
                False     increasing      bins[i-1] <= x <  bins[i]   x in [bins[i-1], bins[i])
                True      increasing      bins[i-1] <  x <= bins[i]   x in (bins[i-1], bins[i]]
                False     decreasing      bins[i-1] >  x >= bins[i]   x in [bins[i], bins[i-1])
                True      decreasing      bins[i-1] >= x >  bins[i]   x in (bins[i], bins[i-1]]

            If values in x are beyond the bounds of bins, 0 or len(bins) is 
            returned as appropriate.        
            
    channel: int, default 0: the index of the signal channel; must be 
        0 <= channel < signal.shape[1]
        
    rtol, atol: float scalars defaults are, respectively, 1e-05 and 1e-08 as
        per numpy.isclose(); used when value is a scalar
        
    equal_nan: bool, default False; specifies if np.nan values are treated as
        equal; used when value is a scalar
        
    right: bool, default False; see documentation for numpy.digitize() for details
        used when value is a sequence
        
    Returns:
    -------
    ret: Array with signal values where signal samples in the specified channel
        channel are
        
            "close to" the specified nominal value (see the NOTE 1, above).
        
            OR 
            
            fall within the boundaries of specified in value
        
    index: Indexing array used to extract ret from the domain
    
    domain_vals: Subarray of the signal, indexed using the "index" array.
    
    CAUTION:
    For regularly sampled signals (e.g. neo.AnalogSignal or datatypes.DataSignal)
    this function will almost surely fail to return all signal values where the 
    domain is close to the specified nominal value. The success depends on the 
    sampling rate and signal quantization error.
    
    A better strategy is to search for the INTERSECTION between domain sample 
    indices where domain <= upper limit and those where domain >= lower limit.
    
    """
    if not isinstance(signal, (neo.AnalogSignal, neo.IrregularlySampledSignal, 
                             DataSignal, IrregularlySampledDataSignal)):
        raise TypeError("signal expected to be a signal; got %s instead" % type(signal).__name__)
    
    if not isinstance(value, (numbers.Number, tuple, list)):
        raise TypeError("value expected to be a float, or sequence of one or two floats; got %s instead" % type(value).__name__)
    
    if isinstance(value, (tuple, list)):
        if len(value) < 1 or len(value) > 2:
            raise TypeError("When a tuple, value must contain at most two elements; got %d instead" % len(value))
        
        if not all([isinstance(v, numbers.Number) for v in value]):
            raise TypeError("value sequence must contain only scalars")
    
    if not isinstance(channel, int):
        raise TypeError("channel expected to be an int; got %s instead" % type(channel).__name__)
    
    if channel < 0 or channel >= signal.shape[1]:
        raise ValueError("channel index %d out of range for a signal with %d channels" % (channel, signal.shape[1]))
    
    if not isinstance(rtol, numbers.Number):
        raise TypeError("rtol expected to be a float; got %s instead" % type(rtol).__name__)
    
    if not isinstance(atol, numbers.Number):
        raise TypeError("atol expected to be a float; got %s instead" % type(atol).__name__)
    
    if not isinstance(equal_nan, bool):
        raise TypeError("equal_nan expected to be a bool; got %s instead" % type(equal_nan).__name__)
    
    signal_values = signal.as_array(units=signal.units)[:,channel]
    
    domain = signal.times
    
    ret = [np.nan]
    
    domain_vals = [np.nan]
    
    index = [np.nan]
    
    if isinstance(value, (tuple, list)):
        digital = np.digitize(domain, value, right=right)
        bin_k = [np.where(digital == k)[0] for k in range(1, len(value))]
        
        if len(bin_k):
            index = np.concatenate(bin_k)
            
            ret = signal_values[index]
            
            domain_vals = domain[index]
            
    else:
        ndx = np.isclose(np.array(domain), value, atol=atol, rtol=rtol, equal_nan=equal_nan)
        
        if ndx.any():
            index = np.where(ndx)[0]
            
            ret = signal_values[index]
            
            domain_vals = domain[index]
            
            
    return ret, index, domain_vals

def inverse_lookup(signal, value, channel=0, rtol=1e-05, atol=1e-08, equal_nan = False, right=False):
    """Look-up for domain values given a nominal signal value.
    
    The function addresses the question "what is (are) the value(s) of the 
    signal's domain for signal samples with value close to a specific value?"
    
    For the inverse correspondence see lookup().
    
    Parameters:
    ----------
    signal: one of neo.AnalogSignal, neo.IrregularlySampledSignal, 
            datatypes.DataSignal, or datatypes.IrregularlySampledDataSignal.
        
    value: float scalar, the nominal value of the signal, or a monotonic
            sequence (tuple, list) of scalars.
            
            When a scalar, the function looks up the domain values corresponding 
            to signal samples that are close to value within the atol and rtol, 
            using numpy.isclose().
            
            NOTE 1:
            
            `a` and `b` are "close to" each other when
            
            absolute(`a` - `b`) <= (`atol` + `rtol` * absolute(`b`))
            
            When a sequence, its elements are boundaries of bins to which signal
            values belong (half-open intervals, direction specified by the 
            value of `right`); the function looks up the domain values for the 
            signal samples with indices fall in these bins, as determined using 
            numpy.digitize().
            
            NOTE 2: From numpy.digitize docstring:
            
            numpy.digitize(x, bins, right=False)[source]
                
                Return the indices of the bins to which each value in input array belongs.
                right     order of bins   returned index i satisfies  meaning
                False     increasing      bins[i-1] <= x <  bins[i]   x in [bins[i-1], bins[i])
                True      increasing      bins[i-1] <  x <= bins[i]   x in (bins[i-1], bins[i]]
                False     decreasing      bins[i-1] >  x >= bins[i]   x in [bins[i], bins[i-1])
                True      decreasing      bins[i-1] >= x >  bins[i]   x in (bins[i], bins[i-1]]

            If values in x are beyond the bounds of bins, 0 or len(bins) is 
            returned as appropriate.        

    channel: int, default 0: the index of the signal channel; must be 
        0 <= channel < signal.shape[1]
        
    rtol, atol: float scalars defaults are, respectively, 1e-05 and 1e-08 as
        per numpy.isclose(); used when value is a scalar
        
    equal_nan: bool, default False; specifies if np.nan values are treated as
        equal; used when value is a scalar
        
    right: bool, default False; see documentation for numpy.digitize() for details
        used when value is a sequence
        
    Returns:
    -------
    ret: Array with domain values where signal samples in the specified channel
        channel are
        
            "close to" the specified nominal value (see the NOTE 1, above).
        
            OR 
            
            fall within the boundaries of specified in value
        
    index: Indexing array used to extract ret from the domain
    
    sigvals: Subarray of the signal, indexed using the "index" array.
    
    CAUTION:
    For regularly sampled signals (e.g. neo.AnalogSignal or datatypes.DataSignal)
    this function will almost surely fail to return all domain values where the 
    signal is close to the specified nominal value. The success depends on the 
    sampling rate and signal quantization error.
    
    A better strategy is to search for the INTERSECTION between domain indices where
    signal is <= upper value limit and indices where signal >= lower value limit.
    
    WARNING: Do not confuse with the functionality of pynverse module.
    
    Considering the signal as being the realization of a function y = f(x) where
    x is the signal's domain and y the signal values, one might be inclined to 
    use the pynverse module by Alvaro Sanchez-Gonzalez to calculate its inverse
    function x = g(y) numerically. 
    
    However, pynverse uses functional programming to calculate the inverse of a 
    mathematical function represented as a python function, or callable, and 
    not an array realization of that function (see pynverse documentation for 
    details).
    
    """
    if not isinstance(signal, (neo.AnalogSignal, neo.IrregularlySampledSignal, 
                             DataSignal, IrregularlySampledDataSignal)):
        raise TypeError("signal expected to be a signal; got %s instead" % type(signal).__name__)
    
    if not isinstance(value, (numbers.Number, tuple, list)):
        raise TypeError("value expected to be a float, or sequence of one or two floats; got %s instead" % type(value).__name__)
    
    if isinstance(value, (tuple, list)):
        if len(value) < 1:
            raise TypeError("When a tuple, value must contain at least one element; got %d instead" % len(value))
        
        if not all([isinstance(v, numbers.Number) for v in value]):
            raise TypeError("value sequence must contain only scalars")
    
    if not isinstance(channel, int):
        raise TypeError("channel expected to be an int; got %s instead" % type(channel).__name__)
    
    if channel < 0 or channel >= signal.shape[1]:
        raise ValueError("channel index %d out of range for a signal with %d channels" % (channel, signal.shape[1]))
    
    if not isinstance(rtol, numbers.Number):
        raise TypeError("rtol expected to be a float; got %s instead" % type(rtol).__name__)
    
    if not isinstance(atol, numbers.Number):
        raise TypeError("atol expected to be a float; got %s instead" % type(atol).__name__)
    
    if not isinstance(equal_nan, bool):
        raise TypeError("equal_nan expected to be a bool; got %s instead" % type(equal_nan).__name__)
    
    
    signal_values = signal.as_array(units=signal.units)[:,channel]
    
    domain = signal.times
    
    ret = [np.nan]
    
    sigvals = [np.nan]
    
    index = [np.nan]
    
    if isinstance(value, (tuple, list)):
        # see numpy.digitize:
        #    numpy.digitize(x, bins, right=False)[source]
        #       
        #     Return the indices of the bins to which each value in input array belongs.
        #     right     order of bins   returned index i satisfies  meaning
        #     False     increasing      bins[i-1] <= x <  bins[i]   x in [bins[i-1], bins[i])
        #     True      increasing      bins[i-1] <  x <= bins[i]   x in (bins[i-1], bins[i]]
        #     False     decreasing      bins[i-1] >  x >= bins[i]   x in [bins[i], bins[i-1])
        #     True      decreasing      bins[i-1] >= x >  bins[i]   x in (bins[i], bins[i-1]]

        #    If values in x are beyond the bounds of bins, 0 or len(bins) is 
        #    returned as appropriate.        
        
        digital = np.digitize(signal_values, value, right=right)
        
        # leave out:
        # digital == 0 indices where signal values are left of the leftmost boundary
        # digital == len(value) where signal values are right of the rightmost boundary
        # np.nan falls 
        # to the left (if right is False) or right, otherwise
        bin_k = [np.where(digital==k)[0] for k in range(1,len(value))]
        
        if len(bin_k):
            index = np.concatenate(bin_k)
            
            ret = domain[index]
            
            sigvals = signal_values[index]
            
    else:
        ndx = np.isclose(signal_values, value, atol=atol, rtol=rtol, equal_nan=equal_nan)
    
        if ndx.any():
            index = np.where(ndx)[0]
            
            ret = domain[index]
            
            sigvals = signal_values[index]
    
    return ret, index, sigvals

