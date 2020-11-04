# -*- coding: utf-8 -*-
"""
Module for managing trigger protocols by way of special Event types embedded
in neo.Segment data structure

NOTE: 2020-10-07 17:42:06
core.neoutils code split and redistributed across core.neoutils, ephys.ephys and 
core.triggerprotocols

Functions and classes defined here:

I. Module-level functions for the management of trigger events and protocols
============================================================================
auto_define_trigger_events
auto_detect_trigger_protocols
clear_events
detect_trigger_events
detect_trigger_times
embed_trigger_event
embed_trigger_protocol
modify_trigger_protocol
parse_trigger_protocols
remove_events
remove_trigger_protocol

II. Classes
===========
TriggerEvent
TriggerEventType
TriggerProtocol

"""
import enum, numbers, warnings
from copy import deepcopy, copy
import numpy as np
import quantities as pq
import neo
#from neo.core import baseneo
#from neo.core import basesignal
#from neo.core import container
from neo.core.dataobject import (DataObject, ArrayDict,)

from core.datatypes import (check_time_units, is_string,)
from core.neoutils import (get_index_of_named_signal, remove_events, )
from core.datasignal import (DataSignal, IrregularlySampledDataSignal, )

from core import prog
from core.prog import safeWrapper

def _new_TriggerEvent(cls, times = None, labels=None, units=None, name=None, 
               file_origin=None, description=None, event_type=None,
               segment=None, array_annotations=None, annotations={}):
    if not isinstance(annotations, dict):
        annotations = dict()
    
    e = TriggerEvent(times=times, labels=labels, units=units,name=name,
                      file_origin=file_origin, description=description, 
                      event_type=event_type, array_annotations=array_annotations,
                      **annotations)
    
    e.segment=segment
    
    return e
    

class TriggerEventType(enum.IntEnum):
    """Convenience enum type for trigger event types.
    
    Types are defined as follows:
    
    presynaptic         = 1 # synaptic stimulus (e.g. delivered via TTL to stim box)
    postsynaptic        = 2 # typically a squre pulse of current injection e.g. at the soma, to elicit APs
    photostimulation    = 4 # typically an uncaging event (generally a TTL which opens a soft or hard shutter for a stimulation laser, or a laser diode)
    imaging_frame       = 8 # TTL that triggers the acquisition of an image frame
    imaging_line        = 16 # TTL trigger for a scanning line of the imaging system
    sweep               = 32 # "external" trigger for electrophysiology acquisition
    user                = 64 # anything else
    
    frame               = imaging_frame (*)
    line                = imaging_line (*)
    imaging             = imaging_frame | imaging_line = 24
    
    acquisition         = imaging | sweep = 56
    
    (*) this is just an alias
    
    """
    presynaptic         = 1 # synaptic stimulus (e.g. delivered via TTL to stim box)
    postsynaptic        = 2 # typically a squre pulse of current injection e.g. at the soma, to elicit APs
    photostimulation    = 4 # typically an uncaging event (generally a TTL which opens a soft or hard shutter for a stimulation laser, or a laser diode)
    imaging_frame       = 8 # TTL that triggers the acquisition of an image frame
    imaging_line        = 16 # TTL trigger for a scanning line of the imaging system
    sweep               = 32 # "external" trigger for electrophysiology acquisition
    user                = 64 # anything else
    
    frame               = imaging_frame
    line                = imaging_line
    imaging             = imaging_frame | imaging_line # 24
    
    acquisition         = imaging | sweep # 56
    
class TriggerEvent(DataObject):
    """Trigger event.
    
    Encapsulates a neo.Event-like object that can be stored in a neo.Segment's
    "events" attribute.
    
    NOTE: 2019-10-13 11:38:13
    Changed to inherit neo.core.dataobject.DataObject, but still modeled as
    neo.Event (in fact a lot of code copied from neo.Event as of neo version
    0.8.0).
    
    Defines the additional attribute __event_type__ which can have one of the 
    values in the TriggerEventType enum.
    
    In addition, all labels must be the same, reflecting the trigger event type.
    
    Additional API:
    
    append_times: appends one or more time "stamps" to the event
    
    NOTE: to select only a few time "stamps" and have them as a TriggerEvent,
    use numpy array indexing methods, but with caveats as outlined below. 
    See also "Indexing" chapter in Numpy Reference  Manual.
    
    ATTENTION: Caveats of numpy array indexing (examples):
    
    Example 1: (basic indexing)
    ---------------------------
    event[k] 
        k is an int
        returns a python Quantity, not a TriggerEvent!
            this is an "undimensioned" object: 
                obj.ndim = 0; len(obj) raises TypeError
                and it needs to be flatten()-ed
    
    Example 2: (basic indexing/slicing)
    -------------------------------------
    event[k:l], event[:l], event[k:] etc ... 
        k, l are int
        returns a TriggerEvent of the same type as this one
        labels attribute is NOT indexed (i.e. stays the same as the original event)
        
    Example 3: (advanced indexing) 
    -------------------------------
    event[(k,l), ]      # NOTE the last comma!
        k, l are int
        returns a TriggerEvent of the same type
        again labels are not modified, as in Example 2
        
    Example 4:( boolean array indexing)
    ----------------------------------
    event[ndx] 
        ndx is a boolean array (e.g., np.array([True, True, False, True])
        returns a TriggerEvent of the same type
        again labels are not modified, as in Example 3
        
    SOLUTION: 
        For Example 1: construct a new TriggerEvent using the return object
            as times, then take all other constructor parameters from the original
            TriggerEvent object. 
            
            It is recommended to flatten() the return object first.
            
        For Examples 2:4 the workaround is to construct a new TriggerEvent using
        the returned object (TriggerEvent) as the only parameter to the constructor.
        
    
    """
    _single_parent_objects = ('Segment',)
    _single_parent_attrs = ('segment',)
    _quantity_attr = 'times'
    _necessary_attrs = (('times', pq.Quantity, 1), ('labels', np.ndarray, 1, np.dtype('S')), ("__event_type__", TriggerEventType, TriggerEventType.presynaptic))

    relative_tolerance = 1e-4
    absolute_tolerance = 1e-4
    equal_nan = True
    
    @staticmethod
    def defaultLabel(event_type):
        if event_type & TriggerEventType.presynaptic:
            return "epsp"
        
        elif event_type & TriggerEventType.postsynaptic:
            return "ap"
        
        elif event_type & TriggerEventType.photostimulation:
            return "photo"
        
        elif event_type & TriggerEventType.imaging:
            return "imaging"
        
        elif event_type & TriggerEventType.sweep:
            return "sweep"
        
        elif event_type & TriggerEventType.user:
            return "user"
        
        else:
            return "event"
    
    @staticmethod
    def parseTimeValues(value, units=None):
        """ Parses values to an array of quantities suitable for a TriggerEvent
        
        Parameters:
        ==========
        
        value:
        
            1) a number
            
            2) a python quantity with time units
            
            3) a numpy array with numbers or characters (in the latter case, must
                        be fully convertible to a numeric array)
            
            4) a sequence of where elements are all of the same type enumerated 
                above
                
                NOTE: sequences with a mixture of element types are not allowed
            
        units: a pyton.Quantity time unit or None
        
            When None, when value is a TriggerEvent the function uses the TriggerEvent units
            otherwise assigns the default (pq.s)
        
        """
        if units is None:
            if isinstance(value, TriggerEvent):
                units = value.units
                
            else:
                units = pq.s
            
        elif not isinstance(units, pq.Quantity):
            raise TypeError("units expected to be a Python Quantity; got %s instead" % type(units).__name__)
        
            units = units.units
        
        if not check_time_units(units):
            raise TypeError("expecting a time unit; got %s instead" % units)
            
        if isinstance(value, (tuple, list)):
            # value is a sequence of...
            if all([isinstance(v, numbers.Number) for v in value]): # plain numbers
                times = np.array(value) * units
                
            elif all([isinstance(v, pq.Quantity) and check_time_units(v) for v in value]): # python quantities
                if any([v.ndim > 0 for v in value]):
                    # in case the values in the sequence are dimensioned arrays
                    # but reject if any has ndim > 1 (enforce time stamps to be
                    # row vectors)
                    if any([v.ndim > 1 for v in value]):
                        raise TypeError("Cannot accept time stamps as python quantity arrays with more than one dimension")
                    times = np.hstack(value) * value[0].units
                    
                else:
                    times = np.array(value) * value[0].units
                    
            elif all([isinstance(v, np.ndarray) for v in value]):
                # sequence of numpy arrays
                times_list = list()
                for v in value:
                    if is_numeric(v):
                        times_list.append(v)
                        
                    elif is_string(v):
                        vv = np.genfromtxt(v)
                        if np.isnan(vv).any():
                            warngins.warn("Character array conversion produced nan values")
                            
                        times_list.append(vv)
                        
                    else:
                        raise TypeError("Incompatible numpy array kind %s" % v.dype.kind)
                    
                if len(times_list):
                    appeded_times = np.hstack(times_list) * units
                    
                else:
                    raise ValueError("cannot convert %s to time stamps" % value)
                
            else:
                raise TypeError("When a sequence, the value must contain elements of the same type, either number scalars or python quantities with time units")
                    
        elif isinstance(value, numbers.Number):
            times = np.array([value]) * units # create a dimensioned array
            
        elif isinstance(value, pq.Quantity):
            if not check_time_units(value):
                raise TypeError("value is expected to have units compatible to %s, but has %s instead" % (units, value.units))
            
            times = value.flatten() # enforce a row vector, even for undimensioned objects (with ndim = 0)
            
        elif isinstance(value, np.ndarray):
            # when value has ndim 0 (undimensioned), flatten() will enforce
            # a minimum of 1 dimension
            if is_numeric(value):
                times = value.flatten() * units
                
            elif is_string(value):
                ss = np.genfromtxt(value)
                
                if np.isnan(ss).any():
                    raise ValueError("Could not fully convert value %s to a numeric numpy array" % value)
                
                times = ss.flatten() * units
                
            else:
                raise TypeError("When value is a numpy array it must has a dtype that is either numeric or character; in the latter case is must be fully convertible to a numeric array")
            
        elif isinstance(value, TriggerEvent):
            times = value.times
            
        else:
            raise TypeError("value expected to be a numeric scalar, python quantity with time units, a numpy array, a sequence of these, or a TriggerEvent; got %s instead" % type(value).__name__)
            
        return times

    def __new__(cls, times=None, labels=None, units=None, name=None, description=None,
                file_origin=None, event_type=None, array_annotations=None, **annotations):
        
        if times is None:
            times = np.array([]) * pq.s
        
        elif isinstance(times, (list, tuple)):
            times = np.array(times)
            
        elif isinstance(times, (neo.Event, TriggerEvent)):
            # for copy c'tor
            evt = times
            times = evt.times.flatten()
            labels = evt.labels
            units = evt.units
            name = evt.name
            description = evt.description
            file_origin = evt.file_origin
            annotations = evt.annotations
            
            if isinstance(evt, TriggerEvent):
                event_type = evt.event_type
                
        if labels is None:
            labels = np.array([], dtype='S')
            
        else:
            labels = np.array(labels)
            if labels.size != times.size and labels.size:
                warnings.warn("Labels array has different length to times")
                #raise ValueError("Labels array has different length to times")
            
        if units is None:
            # No keyword units, so get from `times`
            try:
                units = times.units
                dim = units.dimensionality
            except AttributeError:
                raise ValueError('you must specify units')
        else:
            if hasattr(units, 'dimensionality'):
                dim = units.dimensionality
            else:
                dim = pq.quantity.validate_dimensionality(units)
        # check to make sure the units are time
        # this approach is much faster than comparing the
        # reference dimensionality
        if (len(dim) != 1 or list(dim.values())[0] != 1 or not isinstance(list(dim.keys())[0],
                                                                          pq.UnitTime)):
            ValueError("Unit {} has dimensions {}, not [time]".format(units, dim.simplified))

        #if not isinstance(annotations, dict):
            #annotations = dict()
            
        
                
        obj = pq.Quantity(times, units=dim).view(cls)
        obj._labels = labels
        obj.segment = None
        return obj

    
    def __init__(self, times=None, labels=None, units=None, name=None, description=None,
                file_origin=None, event_type=None, array_annotations=None, **annotations):
        """Constructs a TriggerEvent.
        
        By default its __event_type__ is TriggerEventType.presynaptic
        """
        DataObject.__init__(self, name=name, file_origin=file_origin, description=description,
                            array_annotations=array_annotations, **annotations)

        if not isinstance(annotations, dict):
            annotations = dict()
        
        self.annotations = annotations
        
        if event_type is None:
            self.__event_type__ = TriggerEventType.presynaptic
            
        elif isinstance(event_type, str):
            if event_type in TriggerEventType.__members__:
                self.__event_type__ = TriggerEventType[event_type]
                
            else:
                warngins.warning("Unknown event type %s; event_type will be set to %s " % (event_type, TriggerEventType.presynaptic))
                self.__event_type__ = TriggerEventType.presynaptic
                #raise ValueError("Unknown event type %s" % event_type)
        
        elif isinstance(event_type, TriggerEventType):
            self.__event_type__ = event_type
            
        else:
            warngins.warn("'event_type' parameter expected to be a TriggerEventType enum value, a TriggerEventType name, or None; got %s instead" % type(event_type).__name__)
            self.__event_type__ = TriggerEventType.presynaptic
            #raise TypeError("'event_type' parameter expected to be a TriggerEventType enum value, a TriggerEventType name, or None; got %s instead" % type(event_type).__name__)
        
        self.setLabel(labels)
        
        if isinstance(name, str) and len(name.strip()):
            self._name_ = name
                
        else:
            self._name_ = self.event_type.name
        
    def __eq__(self, other):
        if not isinstance(other, TriggerEvent):
            return False
        
        result =  self.is_same_as(other)
            
        if result:
            result &= self.name == other.name
            
        if result:
            result &= self.labels.size == other.labels.size
            
        if result:
            result &= self.labels.shape == other.labels.shape
            
        if result:
            result &= np.all(self.labels == other.labels)
        
        return result
        
    def __array_finalize__(self, obj):
        super(TriggerEvent, self).__array_finalize__(obj)
        #print("TriggerEvent.__array_finalize__", type(obj).__name__)
        #super().__array_finalize__(obj)
        
        self.__event_type__ = getattr(obj, "__event_type__", TriggerEventType.presynaptic)
        
        self._labels = getattr(obj, 'labels', None)
        self.annotations = getattr(obj, 'annotations', None)
        self.name = getattr(obj, 'name', None)
        self.file_origin = getattr(obj, 'file_origin', None)
        self.description = getattr(obj, 'description', None)
        self.segment = getattr(obj, 'segment', None)
        # Add empty array annotations, because they cannot always be copied,
        # but do not overwrite existing ones from slicing etc.
        # This ensures the attribute exists
        if not hasattr(self, 'array_annotations'):
            self.array_annotations = ArrayDict(self._get_arr_ann_length())

    def __repr__(self):
        result = str(self)
        return result
    
    def __str__(self):
        import itertools
        
        if self.times.size > 1:
            if self.labels is not None:
                if self.labels.size > 0:
                    objs = ['%s@%s' % (label, time) for label, time in itertools.zip_longest(self.labels, self.times, fillvalue="")]
                    
                elif self.labels.size == 0:
                    objs = ["%s" % time for time in self.times]
            
            else:
                objs = ["%s" % time for time in self.times]

        else:
            if self.labels is not None:
                if self.labels.size > 0:
                    objs = ["%s@%s" % (label, self.times) for label in self.labels]
                
                else:
                    objs = ["%s@%s" % (self.labels, self.times)]
                    
            else:
                objs = ["%s" % self.times]
            
        result = "TriggerEvent (%s): %s, %s" % (self.event_type.name, self.name, ", ".join(objs))
        
        return result
    
    def __reduce__(self):
        if not isinstance(self.annotations, dict):
            annots = {}
            
        else:
            annots = self.annotations
        
        if not hasattr(self, 'array_annotations'):
            self.array_annotations = ArrayDict(self._get_arr_ann_length())

        return _new_TriggerEvent, (self.__class__, self.times, self.labels, 
                                   self.units, self.name, self.file_origin, 
                                   self.description, self.__event_type__, 
                                   self.segment, self.array_annotations, annots)
        
    def set_labels(self, labels):
        if self.labels is not None and self.labels.size > 0 and len(labels) != self.size:
            raise ValueError("Labels array has different length to times ({} != {})"
                            .format(len(labels), self.size))
        self._labels = np.array(labels)

    def get_labels(self):
        return self._labels

    labels = property(get_labels, set_labels)

    @property
    def times(self):
        return pq.Quantity(self)

    def merge(self, other):
        """Merge this event with the time stamps from other event
        Both events must have the same type.
        
        Returns:
        ========
        
        A new TriggerEvent with the same type as self
        
        NOTE the new time stamps are stored in sorted order, by value!
        
        """
        if other.__event_type__ != self.__event_type__:
            raise TypeError("Can only merge synaptic events of the same type")
        
        othertimes = other.times.rescale(self.times.units)
        times = np.hstack([self.times, othertimes]).sort() * self.times.units
        labels = np.hstack([self.labels, other.labels]) # CAUTION this will mix the labels!
        
        # NOTE: 2019-03-15 18:45:20
        # preserve _MY_ labels!
        new_labels = np.full_like(labels, labels[0], dtype=labels.dtype)
        
        # take care of the other constructor parameters
        kwargs = {}

        for name in ("name", "description", "file_origin"):#, "__protocol__"):
            attr_self = getattr(self, name)
            attr_other = getattr(other, name)
            if attr_self == attr_other:
                kwargs[name] = attr_self
                
            else:
                kwargs[name] = "merge(%s, %s)" % (attr_self, attr_other)
                
        kwargs["event_type"] = self.__event_type__

        merged_annotations = self.annotations.copy()
        
        merged_annotations.update(other.annotations)
        
        kwargs['array_annotations'] = self._merge_array_annotations(other)

        kwargs.update(merged_annotations)
        
        return TriggerEvent(times=times, labels=new_labels, **kwargs)
    
    def rescale(self, units):
        '''
        Return a copy of the :class:`Event` converted to the specified
        units
        '''
        obj = super(TriggerEvent, self).rescale(units)
        obj.segment = self.segment
        return obj

    def setLabel(self, value):
        #print("setLabel: event_type", self.__event_type__)
        if isinstance(value, str):
            setattr(self, "_labels", np.array([value] * self.times.size))
            
        elif isinstance(value, (tuple, list)) and all([isinstance(l, str) for l in value]):
            if len(value) == self.times.flatten().size:
                setattr(self, "_labels", np.array(value))
                
            else:
                raise ValueError("When given as a list, value must have as many elements as times (%d); got %d instead" % (self.times.flatten().size, len(value)))

        elif isinstance(value, np.ndarray) and is_string(value):
            if value.flatten().size == 0:
                setattr(self, "_labels", np.array([TriggerEvent.defaultLabel(self.__event_type__)] * self.times.size))
                    
            elif value.flatten().size != self.times.flatten().size:
                setattr(self, "_labels", np.array([value.flatten()[0]] * self.times.size))
                
            else:
                setattr(self, "_labels", value)
                
        elif value is None:
            def_label = TriggerEvent.defaultLabel(self.__event_type__)
            #print("setLabel: def_label", def_label)
            setattr(self, "_labels", np.full_like(self.times.magnitude, TriggerEvent.defaultLabel(self.__event_type__), dtype=np.dtype(str)))
                    
        #else:
            #raise TypeError("'value' expected to be a str, a list of str, or a numpy array of str; got %s instead" % type(value).__name__)
        
    def setLabels(self, value):
        self.setLabel(value)
        
    def shift(self, value, copy=False):
        """Adds value to the times attribute.
        
        Value must be a pq.Quantity with the same units as the times attribute,
        or a scalar
        """
        if copy:
            ret = self.copy()
            
        else:
            ret = self
            
        if isinstance(value, numbers.Real):
            value = value * ret.times.units
            
        elif isinstance(value, pq.Quantity):
            # check for units
            if hasattr(value, 'dimensionality'):
                dim = value.dimensionality
            else:
                dim = pq.quantity.validate_dimensionality(value)
            # check to make sure the units are time
            # this approach is much faster than comparing the
            # reference dimensionality
            if (len(dim) != 1 or list(dim.values())[0] != 1 or
                    not isinstance(list(dim.keys())[0], pq.UnitTime)):
                ValueError("value %s has dimensions %s, not [time]" %
                        (value, dim.simplified))

        else:
            raise TypeError("value was expected to be a scalar or a python Quantity with %s units; got %s insteads" % (self.time.units, value))

        ret += value
        
        return ret # for convenience so that we can chain this e.g. "return obj.copy().shift()"
        
    #def shiftCopy(self, value):
        #"""Returns a shifted copy of this event
        #"""
        
        #return self.copy().shift(value)
        
    def __getitem__(self, i):
        obj = super(TriggerEvent, self).__getitem__(i)
        if self._labels is not None and self._labels.size > 0:
            obj._labels = self._labels[i]
        else:
            obj._labels = self._labels
            
        try:
            obj.array_annotate(**deepcopy(self.array_annotations_at_index(i)))
            obj._copy_data_complement(self)
        except AttributeError:  # If Quantity was returned, not Event
            obj.times = obj
        return obj

    def _copy_data_complement(self, other):
        '''
        Copy the metadata from another :class:`TriggerEvent`.
        '''
        for attr in ("labels", "name", "file_origin", "description", "annotations"):
            setattr(self, attr, getattr(other, attr, None))
            
        setattr(self, "__event_type__", getattr(other, "__event_type__", TriggerEventType.presynaptic))
        
    #def duplicate_with_new_data(self, signal):
        #new = self.__class__(times=signal)
        #new._copy_data_complement(self)
        #return new
    
    def duplicate_with_new_data(self, times, labels=None, units=None):
        '''
        Create a new :class:`TriggerEvent` with the same metadata
        but different data
        Note: Array annotations can not be copied here because length of data can change
        '''
        if units is None:
            units = self.units
        else:
            units = pq.quantity.validate_dimensionality(units)

        new = self.__class__(times=times, units=units)
        new._copy_data_complement(self)
        if labels is not None:
            new.labels = labels
        else:
            new.labels = self.labels
        # Note: Array annotations cannot be copied here, because length of data can be changed
        return new

    def append_times(self, value):
        """Appends time values to this event.
        
        Parameters:
        ==========
        value: See TriggerEvent.parseTimeValues
        
        Returns:
        =======
        A TriggerEvent with updated time stamps but with the same event type and 
        labels as self. 
        
        NOTE the new time stamps are stored in the given order and NOT sorted
        by value!
        
        In addition, the labels array is updated to have the same length as the 
        times attribute of the returned event object.
        """
        appended_times = TriggerEvent.parseTimeValues(value, self.units)
        
        new_times = np.hstack((self.times, appended_times)) * self.units
        
        evt_type = self.__event_type__
        
        new_labels = np.full_like(new_times.magnitude, self.labels[0], dtype=self.labels.dtype)
        
        name = self.name
        
        # take care of the other constructor parameters
        kwargs = {}

        for name in ("name", "description", "file_origin"):#, "__protocol__"):
            attr_self = getattr(self, name)
            
            kwargs[name] = getattr(self, name)
            
        kwargs["event_type"] = self.__event_type__

        kwargs.update(self.annotations)

        return TriggerEvent(times = new_times, labels=new_labels, **kwargs)
    
    def time_slice(self, t_start, t_stop):
        '''
        Creates a new :class:`TriggerEvent` corresponding to the time slice of
        the original :class:`TriggerEvent` between (and including) times
        :attr:`t_start` and :attr:`t_stop`. Either parameter can also be None
        to use infinite endpoints for the time interval.
        '''
        _t_start = t_start
        _t_stop = t_stop
        if t_start is None:
            _t_start = -np.inf
        if t_stop is None:
            _t_stop = np.inf

        indices = (self >= _t_start) & (self <= _t_stop)
        
        times = self.times[indices]
        labels = self.labels[indices]
        
        new_evt = TriggerEvent(times=times, labels=labels, 
                               units=self.units, name=self.name,
                               event_type=self.event_type,
                               description=self.description,
                               file_origin=self.file_origin,
                               array_annotations=self.array_annotations,
                               **self.annotations)
        
        #new_evt.labels = deepcopy(self.labels[indices])

        return new_evt

    def time_shift(self, t_shift):
        """
        Shifts an :class:`TriggerEvent` by an amount of time.

        Parameters:
        -----------
        t_shift: Quantity (time)
            Amount of time by which to shift the :class:`Event`.

        Returns:
        --------
        epoch: TriggerEvent
            New instance of an :class:`TriggerEvent` object starting at t_shift later than the
            original :class:`TriggerEvent` (the original :class:`TriggerEvent` is not modified).
        """
        new_evt = self.duplicate_with_new_data(times=self.times + t_shift,
                                               labels=self.labels)

        # Here we can safely copy the array annotations since we know that
        # the length of the Event does not change.
        new_evt.array_annotate(**self.array_annotations)

        return new_evt

    def to_epoch(self, pairwise=False, durations=None):
        """
        Returns a new Epoch object based on the times and labels in the TriggerEvent object.

        This method has three modes of action.

        1. By default, an array of `n` event times will be transformed into
           `n-1` epochs, where the end of one epoch is the beginning of the next.
           This assumes that the events are ordered in time; it is the
           responsibility of the caller to check this is the case.
           
        2. If `pairwise` is True, then the event times will be taken as pairs
           representing the start and end time of an epoch. The number of
           events must be even, otherwise a ValueError is raised.
           
        3. If `durations` is given, it should be a scalar Quantity or a
           Quantity array of the same size as the Event.
           Each event time is then taken as the start of an epoch of duration
           given by `durations`.

        `pairwise=True` and `durations` are mutually exclusive. A ValueError
        will be raised if both are given.

        If `durations` is given, epoch labels are set to the corresponding
        labels of the events that indicate the epoch start.

        If `durations` is not given, then the event labels A and B bounding
        the epoch are used to set the labels of the epochs in the form 'A-B'.
        """

        if pairwise:
            # Mode 2
            if durations is not None:
                raise ValueError("Inconsistent arguments. "
                                 "Cannot give both `pairwise` and `durations`")
            if self.size % 2 != 0:
                raise ValueError("Pairwise conversion of events to epochs"
                                 " requires an even number of events")
            times = self.times[::2]
            durations = self.times[1::2] - times
            labels = np.array(
                ["{}-{}".format(a, b) for a, b in zip(self.labels[::2], self.labels[1::2])])
        elif durations is None:
            # Mode 1
            times = self.times[:-1]
            durations = np.diff(self.times)
            labels = np.array(
                ["{}-{}".format(a, b) for a, b in zip(self.labels[:-1], self.labels[1:])])
        else:
            # Mode 3
            times = self.times
            labels = self.labels
        return neo.Epoch(times=times, durations=durations, labels=labels)

    def as_array(self, units=None):
        """
        Return the event times as a plain NumPy array.

        If `units` is specified, first rescale to those units.
        """
        if units:
            return self.rescale(units).magnitude
        else:
            return self.magnitude

    def as_quantity(self):
        """
        Return the event times as a quantities array.
        """
        return self.view(pq.Quantity)
    
    def is_same_as(self, other, rtol = relative_tolerance, 
                   atol =  absolute_tolerance, 
                   equal_nan = equal_nan):
        """Work around standard equality test
        Compares event type, time stamps, labels and name.
        
        Time stamps are compared within a relative and absolute tolerances by
        calling numpy.isclose()
        
        Positional parameters:
        =====================
        other: a TriggerEvent
        
        Named parameters (see numpy.isclose()):
        ================
        rtol, atol: float scalars: relative and absolute tolerances (see numpy.isclose())
            Their default values are the :class: variables TriggerEvent.relative_tolerance (1e-4) and 
            TriggerEvent.absolute_tolerance (1e-4)
        
        equal_nan: boolean, default if the :class: variable TriggerEvent.equal_nan (True)
            When True, two numpy.nan values are taken as equal.
            
        """
        if not isinstance(other, TriggerEvent):
            raise TypeError("A TriggerEvent object was expected; got %s instead" % type(other).__name__)
        
        result = other.event_type == self.event_type
        
        if result:
            compatible_units = other.units == self.units
            
            if not compatible_units:
                self_dim    = pq.quantity.validate_dimensionality(self.units)
                
                other_dim   = pq.quantity.validate_dimensionality(other.units)
                
                if self_dim != other_dim:
                    try:
                        cf = pq.quantity.get_conversion_factor(other_dim, self_dim)
                        compatible_units = True
                        
                    except AssertionError:
                        compatible_units = False
                    
            result &= compatible_units
            
        if result:
            result &= other.times.flatten().size == self.times.flatten().size
        
        if result:
            result &= np.all(np.isclose(other.times.magnitude, self.times.magnitude,
                                     rtol=rtol, atol=atol, equal_nan=equal_nan))
        
        if result: 
            result &= np.all(np.isclose(other.magnitude, self.magnitude, 
                                     rtol=rtol, atol=atol, equal_nan=equal_nan))
            
        if result:
            result &= other.labels.flatten().size == self.labels.flatten().size
            
        if result:
            result &= other.labels.shape == self.labels.shape
            
        if result:
            result &= np.all(other.labels.flatten() == self.labels.flatten)
            
        if result:
            result &= other.name == self.name
        
        return result
            
    
    @property
    def name(self):
        return self._name_
    
    @name.setter
    def name(self, value):
        if isinstance(value, str) or value is None:
            self._name_ = value
            
        else:
            raise TypeError("Expecting a str or None; got %s" % type(value).__name__)

    @property
    def times(self):
        return pq.Quantity(self)
    
    @property
    def event_type(self):
        return self.__event_type__
    
    @event_type.setter
    def event_type(self, value):
        if not isinstance(value, TriggerEventType):
            raise TypeError("Expecting a TriggerEventType enum value; got %s instead" % type(value).__name__)
        
        self.__event_type__ = value
        
    @property
    def type(self):
        return self.__event_type__
    
    @type.setter
    def type(self, value):
        self.event_type = value
    
class TriggerProtocol(object):
    """Encapsulates an experimental stimulation protocol (i.e., "triggers").
    
    A protocol is composed of at least one type of TriggerEvent objects, and
    is associatd with at least one neo.Segment, encapsulating the set of 
    triggers that ocurred during that particular segment (or "sweep").
    
    Containers of Segment objects (e.g. a neo.Block) can associate several 
    TriggerProtocol objects, such that distinct segments contain different
    sets of trigger events - where each such set represents a trigger
    protocol.
    
    A given trigger protocol can occuir in more than one segment. However, any
    one segment can be associated with at most one trigger protocol.
    
    Unlike TriggerEvent, a TriggerProtocol is not currently "embedded" in any of
    the neo containers. Instead, its component TriggerEvent are contained ("embedded")
    in the "events" attribute of the Segment associated with this protocol.
    
    Contains TriggerEvents and indices specifying which segments from a collection
    of segments, this protocol applies to.
        
    A TriggerProtocol object has the following attributes:
        
        presynaptic:        one presynaptic event or None
        postsynaptic:       one postsynaptic event or None
        photostimulation:   one photostimulation event or None
        acquisition:        a list (posibly empty) of imaging_frame, imaging_line, segment types events
        segmentIndex:       list of indices of frames where this protocol applies
        imaging_delay:      python Quantity scalar
        
        The first three can each be a TriggerEvent object or None.
        
        'segmentIndex' is an indexing object for frames (segments or sweeps) 
        where this protocol applies; it may be empty
        
        When segmentIndex is empty, the protocol will apply to ALL segments in 
        the collection.
        
        ATTENTION: In a collection of segments (e.g., neo.Block) each segment
            can have at most one protocol. It follows that a protocol with an
            empty segmentIndex cannot co-exist with other protocols given that
            segment collection (an empty segmentIndex implies that the protocol 
            applies to all segments in that collection) 
        
        (internally it can be a list of int, a range, or a slice)
        
        up to three TriggerEvent objects of the following types:
            up to one presynaptic event type
            up to one postsynaptic event type
            up to one photostimulation event type
            
        a list of TriggerEvent objects of imaging_frame, imaging_line, segment types
            
                
        The event_type atribute of the events will be overwritten according to the 
        named parameter to which they are assigned in the function call.
        
        NOTE: there can be at most ONE event each, of the presynaptic, postsynaptic,
        and photostimulation TriggerEvent objects.
        
        In turn these events can contain an ARRAY  of time values (i.e., multiple
        time stamps), so a TriggerEvent can actually encapsulate the notion of
        an array of events
    
    """
    def __init__(self, pre = None, post = None, photo = None, acquisition = None, 
                 events = None, segment_index = [], imaging_delay = 0 * pq.s, 
                 name="protocol"):
        """
        Named parameters:
        =================
        
        pre, post, photo: a SynapticEvent or None
        
        events: a sequence of TriggerEvent objects, or None
        
            When given, it must have up to three TriggerEvent objects, 
            each of a different type, and the named parameters "pre", "post" or
            "photo" will only be used to supply a TriggerEvent of a type not found
            in the events list.
            
            NOTE: a protocol is "empty" when it has no such events
            
            len(protocol) returns the number of events of any kind
            
        
        segment_index: an int, a sequence of int, a range object or a slice object
        
        imaging_delay: a python Quantity in UnitTime units; optional, default is 0 * pq.s
        
            - represents the delay between the start of imaging data frame 
                acquisition an the starts of the corresponding electrophysiology
                frame (a.k.a "segment" or "sweep") acquisition
            
            NOTE: 
            
            A POSITIVE delay signifies that imaging frame acquisition started 
                delay s AFTER the start of the electrophysiology data acquisition.
                
                The typical use case is when imaging frame acquisition has been 
                triggered by the electrophysiology acquisition software; this 
                MAY be represented by a TriggerEvent of imaging_frame 
                type  embedded in the "events" list of an electrophysiology sweep
                (i.e., a neo.Segment)
                
                
            A NEGATIVE delay signifies that the imaging frame acquisition started
                delay s BEFORE the start of electrophysiology data acquisition.
                
                The typical use case is when the electrophysiology recording has
                been triggered by the imaging software. This MAY be a special
                if the imaging metadata (dependent on the imaging system).
                
            CAUTION: A value of 0 s (default) _MAY_ indicate no delay between the
                acquisition of image and electrophysiology (e.g. triggered simultaneously)
                of that there was NO trigger between the two (ie. each were started
                manually)
                
                
        Passing a non-empty events parameters trumps the other parameters        
                    
        
        """
        super(TriggerProtocol, self).__init__()
        
        self.__presynaptic__        = None
        self.__postsynaptic__       = None
        self.__photostimulation__   = None
        self.__acquisition__        = None # forTriggerEventTypes imaging_frame, imaging_line, segment
        self.__segment_index__      = []
        #self.__imaging_delay__      = 0 * pq.s # NOTE: this IS NOT A TriggerEvent  !!!
        self.__imaging_delay__      = None#0 * pq.s # NOTE: this IS NOT A TriggerEvent  !!!
        self.__user_events__        = []
        self.__protocol_name__      = "protocol"
        
        if isinstance(events, (tuple, list)) and 1 <= len(events) <= 3 and all([isinstance(e, TriggerEvent) for e in events]):
            # contructs from a list of TriggerEvent objects passed as "events" argument
            for e in events:
                if e.event_type == TriggerEventType.presynaptic:
                    if self.__presynaptic__ is None:
                        self.__presynaptic__ = e.copy()
                        self.__presynaptic__.labels = e.labels
                        
                    else:
                        raise RuntimeError("A presynaptic event has already been specified")
                    
                elif e.event_type == TriggerEventType.postsynaptic:
                    if self.__postsynaptic__ is None:
                        self.__postsynaptic__ = e.copy()
                        self.__postsynaptic__.labels = e.labels
                        
                    else:
                        raise RuntimeError("A postsynaptic event has already been specified")
                    
                elif e.event_type == TriggerEventType.photostimulation:
                    if self.__photostimulation__ is None:
                        self.__photostimulation__ = e.copy()
                        self.__photostimulation__.labels = e.labels
                        
                    else:
                        raise RuntimeError("A photostimulation event has already been specified")
                    
                elif e.event_type & TriggerEventType.acquisition:
                    e_ = e.copy()
                    e_.labels = e.labels
                    #self.__acquisition__.append(e_)
                    self.__acquisition__ = e_ # NOTE: ONE acquisition event only!
                    
            overwrite = False
                    
        else:
            if events is not None:
                warning.warn("'events' parameter specified is invalid and will be disregarded; was expecting a list of 1 to 3 Synaptic Events of different types, or None; got %s instead" % type(events).__name__)
                
            overwrite = True
        
        if isinstance(pre, TriggerProtocol):
            # copy c'tor
            if pre.__presynaptic__ is not None:
                self.__presynaptic__ = pre.__presynaptic__.copy()
                self.__presynaptic__.labels = pre.__presynaptic__.labels
                
            if pre.__postsynaptic__ is not None:
                self.__postsynaptic__ = pre.__postsynaptic__.copy()
                self.__postsynaptic__.labels = pre.__postsynaptic__.labels
                
            if pre.__photostimulation__ is not None:
                self.__photostimulation__ = pre.__photostimulation__.copy()
                self.__photostimulation__.labels = pre.__photostimulation__.labels
                
            self.__imaging_delay__ = pre.__imaging_delay__.copy()
            
            # keep this for old API!
            if isinstance(pre.acquisition, (tuple, list)) and len(pre.acquisition):
                acq = pre.acquisition[0].copy()
                self.__acquisition__ = acq
                
            elif isinstance(pre.acquisition, TriggerEvent) and pre.acquisition.event_type & TriggerEventType.acquisition:
                self.__acquisition__ = pre.acquisition.copy()
                
            else:
                self.__acquisition__ = None
                
            if isinstance(pre.__segment_index__, slice):
                self.__segment_index__ = slice(pre.__segment_index__.start, pre.__segment_index__.stop, pre.__segment_index__.step)
                
            elif isinstance(pre.__segment_index__, range):
                self.__segment_index__ = [x for x in pre.__segment_index__]
                
            else:
                self.__segment_index__ = pre.__segment_index__[:]
                
            self.__protocol_name__ = pre.name
            
            return
        
        elif isinstance(pre, TriggerEvent):
            if self.__presynaptic__ is None:
                self.__presynaptic__ = pre
                self.__presynaptic__.event_type = TriggerEventType.presynaptic
                
            else:
                raise RuntimeError("A presynaptic event has already been specified")
            
        elif pre is None:
            if overwrite:
                self.__presynaptic__ = None
            
        else:
            raise TypeError("'pre' expected to be a TriggerEvent or None; got %s instead" % type(pre).__name__)
            
        if isinstance(post, TriggerEvent):
            if self.__postsynaptic__ is None:
                self.__postsynaptic__ = post
                self.__postsynaptic__.event_type = TriggerEventType.postsynaptic
                
            else:
                raise RuntimeError("A postsynaptic event has already been specified")
            
        elif post is None:
            if overwrite:
                self.__postsynaptic__ = None
            
        else:
            raise TypeError("'post' expected to be a TriggerEvent or None; got %s instead" % type(post).__name__)
        
        if isinstance(photo, TriggerEvent):
            if self.__photostimulation__ is None:
                self.__photostimulation__ = photo
                self.__photostimulation__.event_type = TriggerEventType.photostimulation
                
            else:
                raise RuntimeError("A photostimulation event has already been specified")
            
        elif photo is None:
            if overwrite:
                self.__photostimulation__ = None
            
        else:
            raise TypeError("'photo' expected to be a TriggerEvent or None; got %s instead" % type(photo).__name__)
        
        if isinstance(acquisition, TriggerEvent) and acquisition.event_type & TriggerEventType.acquisition:
            self.__acquisition__ = acquisition
            #self.__acquisition__.append(acquisition)
            
        elif isinstance(acquisition, (tuple, list)) and \
            all([isinstance(a, TriggerEvent) and a.event_type & TriggerEventType.acquisition for a in acquisition]):
                self.__acquisition__ = acquisition[0]
                #self.__acquisition__ += list(acquisition)
                
        else:
            self.__acquisition__ = None
            #self.__acquisition__ = []

        if isinstance(segment_index, int):
            self.__segment_index__ = [segment_index]
            
        elif isinstance(segment_index, (tuple, list)) and (len(segment_index)==0 or all([isinstance(x, int) for x in segment_index])):
            self.__segment_index__ = segment_index
            
        elif isinstance(segment_index, (range, slice)):
            if segment_index.start is not None and segment_index.start < 0:
                raise ValueError("Negative start values for range or slice frame indexing are not supported ")
            
            if segment_index.step is not None and segment_index.step < 0:
                raise ValueError("Negative step values for range or slice frame indexing are not supported ")
            
            if segment_index.stop < 0 :
                raise ValueError("Negative stop values for range or slice frame indexing are not supported ")
                
            self.__segment_index__ = segment_index
            
        else:
            raise TypeError("'segment_index' expected to be an int, a sequence of int, a range or a slice; got %s instead" % type(segment_index).__name__)
        
        if isinstance(name, str):
            self.__protocol_name__ = name
            
        else:
            raise TypeError("'name' expected to be a str; got %s instead" % type(name).__name__)
        
        if isinstance(imaging_delay, pq.Quantity):
            if imaging_delay.units != pq.s:
                dim = imaging_delay.units.dimensionality
                
                if not isinstance(list(dim.keys())[0], pq.UnitTime):
                    raise TypeError("Expecting a temporal quantity for imaging_delay; got %s instead" % imaging_delay)
                
            self.__imaging_delay__ = imaging_delay
            
        else:
            raise TypeError("Expecting a python Quantity with time units for imaging_delay; got %s instead" % type(imaging_delay).__name__)
        
    def __len__(self):
        """The number of TriggerEvents, of any type, in this protocol
        """
        if self.__presynaptic__ is None:
            pre = 0
            
        else:
            pre = self.__presynaptic__.size
            
        if self.__postsynaptic__ is None:
            post = 0
            
        else:
            post = self.__postsynaptic__.size
            
        if self.__photostimulation__ is None:
            photo = 0
            
        else:
            photo = self.__photostimulation__.size
            
        if self.__acquisition__ is None:
            imaging = 0
            
        elif isinstance(self.__acquisition__, (tuple, list)):
            imaging = self.__acquisition__[0].size
            
        elif  isinstance(self.__acquisition__, TriggerEvent):
            imaging = self.__acquisition__.size
            
        return pre + post + photo + imaging
    
    def __str__(self):
        result = ["%s %s:" % (self.__class__.__name__, self.name)]
        
        if self.__presynaptic__ is not None:
            result += ["\tpresynaptic:\n\t%s" % str(self.__presynaptic__)]
            
        if self.__postsynaptic__ is not None:
            result += ["\tpostsynaptic:\n\t%s" % str(self.__postsynaptic__)]
            
        if self.__photostimulation__ is not None:
            result += ["\tphotostimulation:\n\t%s" % str(self.__photostimulation__)]
            
        if isinstance(self.__acquisition__, (tuple, list)) and len(self.__acquisition__):
            result.append("\tacquisition:\n\t%s" % "\n".join([str(a) for a in self.__acquisition__]))
            
        elif isinstance(self.__acquisition__, TriggerEvent):
            result += ["\tacquisition:\n\t%s" % str(self.__acquisition__)]
            
        result += ["\timaging delay: %s" % str(self.__imaging_delay__)]
        
        result += ["\tsegment index: %s" % str(self.__segment_index__)]
        result += ["\n"]
        
        return "\n".join(result)
    
    def __repr__(self):
        return self.__str__()
    
    def getEvent(self, event_type):
        """Returns the event specified by type
        """
        if isinstance(event_type, str):
            if event_type in TriggerEventType.__members__:
                event_type = TriggerEventType[event_type]
                
            else:
                raise ValueError("Unknown event_type %s" % event_type)
                
        elif not isinstance(event_type, TriggerEventType):
            raise TypeError("event_type expected a string, a TriggerEventType or None; got %s instead"% type(event_type).__name__)
        
        if event_type & TriggerEventType.presynaptic:
            return self.__presynaptic__
        
        elif event_type & TriggerEventType.postsynaptic:
            return self.__postsynaptic__
        
        elif event_type & TriggerEventType.photostimulation:
            return self.__photostimulation__
        
        elif event_type & TriggerEventType.acquisition:
            if isinstance(self.__acquisition__, (tuple, list)):
                if len(self.__acquisition__):
                    return self.__acquisition__[0]
            
            elif isinstance(self.__acquisition__, TriggerEvent):
                return self.__acquisition__
    
    @property
    def ntriggers(self):
        """Number of trigger events (of any type)
        """
        return len(self)
    
    @property
    def events(self):
        ret = list()
        
        if self.__presynaptic__ is not None:
            ret.append(self.__presynaptic__)
            
        if self.__postsynaptic__ is not None:
            ret.append(self.__postsynaptic__)
            
        if self.__photostimulation__ is not None:
            ret.append(self.__photostimulation__)
        
        if isinstance(self.__acquisition__, (tuple, list)) and len(self.__acquisition__):
            ret.append(self.__acquisition__[0])
            
        elif isinstance(self.__acquisition__, TriggerEvent):
            ret.append(self.__acquisition__)
            
        return sorted(ret, key = lambda x: x.times.flatten()[0])
    
    @property
    def nsegments(self):
        """Number of neo.Segment objects to which this protocol applies
        """
        return len(self.segmentIndices())
    
    @safeWrapper
    def hasSameEvents(self, other, 
                      rtol = TriggerEvent.relative_tolerance, 
                      atol = TriggerEvent.absolute_tolerance, 
                      equal_nan = TriggerEvent.equal_nan):
        """Compares pre-, post- and photo- events with those from other TriggerProtocol.
        
        NOTE: 2018-06-07 22:42:04
        This way to compare protocols, also used by overloaded __eq__, is recommended
        because direct comparison of floating point values for identity is almost
        guaranteed to fail due to rounding errors.
        
        Positional parameter:
        =====================
        other: a TriggerProtocol object
        
        Named parameters:
        =================
        withlabels: boolean (default True) also compares the labels.
            When False, label identity is not checked
            
        rtol, atol: floating point scalars: relative and absolute tolerance, respectively
            for test (see numpy.isclose())
            
        equal_nan: treat numpy.nan values as being equal (see numpy.isclose())
        
        Default values are TriggerEvent :class: variables relative_tolerance, absolute_tolerance,
        and equal_nan, respectively: 1e-4, 1e-4 and True
            
        """
        if not isinstance(other, TriggerProtocol):
            raise TypeError("A TriggerProtocol object was expected; got %s instead" % type(other).__name__)
        
        if not hasattr(self, "__user_events__"):
            self.__user_events__ = []
        
        pre     = False
        post    = False
        photo   = False
        acq     = False
        usr     = False
        
        img_del = False
        
        if self.__presynaptic__ is None:
            if other.__presynaptic__ is None:
                pre = True
                
        else:
            if other.__presynaptic__ is not None:
                pre = self.__presynaptic__.is_same_as(other.__presynaptic__, 
                                                      rtol=rtol, atol=atol, equal_nan=equal_nan)
    
        if self.__postsynaptic__ is None:
            if other.__postsynaptic__ is None:
                post = True
                
        else:
            if other.__postsynaptic__ is not None:
                post = self.__postsynaptic__.is_same_as(other.__postsynaptic__,
                                                        rtol=rtol, atol=atol, equal_nan=equal_nan)
                
        if self.__photostimulation__ is None:
            if other.__photostimulation__ is None:
                photo = True
                
        else:
            if other.__photostimulation__ is not None:
                photo = self.__photostimulation__.is_same_as(other.__photostimulation__,
                                                             rtol=rtol, atol=atol, equal_nan=equal_nan)
                    
        img_del = self.__imaging_delay__ is not None and other.__imaging_delay__ is not None
        
        img_del &= self.__imaging_delay__.units == other.__imaging_delay__.units
        
        img_del &= np.all(np.isclose(self.__imaging_delay__.magnitude, other.__imaging_delay__.magnitude,
                          rtol-rtol, atol=atol, equal_nan=equal_nan))
                
        if not hasattr(other, "__user_events__"):
            if len(self.__user_events__):
                usr = False
                
            else:
                usr = True
        else:
            usr = len(self.__user_events__) == len(other.__user_events__)
        
        if usr and hasattr(other, "__user_events__"):
            e_events = list()
            
            for (e0, e1) in zip(self.__user_events__, other.__user_events__):
                e_usr = e0.is_same_as(e1, rtol=rtol, atol=atol, equal_nan=equal_nan)
                
                if withlabels:
                    e_usr &= e0.labels.size == e1.labels.size
                    
                    if e_usr:
                        e_usr &= e0.labels.shape == e1.labels.shape
                        
                    if e_usr:
                        e_usr &= np.all(e0.labels == e1.labels)
                    
                e_events.append(e_usr)
                
            usr &= all(e_events)
            
        if self.acquisition is None:
            if other.acquisition is None:
                acq = True
            
        else:
            if other.acquisition is not None:
                acq = self.acquisition.is_same_as(other.acquisition)
                    
        return pre and post and photo and img_del and acq and usr
    
    def __eq__(self, other):
        """Compares pre-, post- and photo- events and frame index with those from other TriggerProtocol.
        The compared protocols may have different frame indices!
        """
        # Will raise exception if other is not a TriggerProtocol
        same_events = self.hasSameEvents(other)
        
        return same_events and self.name == other.name and \
            self.__imaging_delay__ == other.__imaging_delay__
    
    @property
    def acquisition(self):
        """The acquisition event
        """
        return self.getEvent(TriggerEventType.acquisition)
        ## NOTE: 2019-03-15 18:10:19
        ## upgrade to new API
        #if isinstance(self.__acquisition__, (tuple, list)):
            #if len(self.__acquisition__):
                #self.__acquisition__ = self.__acquisition__[0]
                
        #return self.__acquisition__
    
    @acquisition.setter
    def acquisition(self, value):
        if value is None:
            self.__acquisition__ = value
            
        elif isinstance(value, TriggerEvent):
            if value.event_type & TriggerEventType.acquisition:
                self.__acquisition__ = value.copy()
                
            else:
                raise TypeError("Cannot use this event type (%s) for acquisition" % value.event_type)
                
        else:
            raise TypeError("Expecting a TriggerEvent or None; got %s instead" % type(value).__name__)
        
    def shift(self, value, copy=False):
        """Shifts all events by given value 
        See TriggerEvent shift
        """
        
        if copy:
            ret = self.copy()
            
        else:
            ret = self
        
        for event in ret.events:
            event.shift(value)
            
        ret.imagingDelay += value
        
        return ret # so we can chain this call e.g. return self.copy().shift(value)
        
    def reverseAcquisition(self, copy=False):
        if copy:
            ret = self.copy()
            
        else:
            ret = self
            
        if ret.acquisition is not None:
            ret.acquisition *= -1
            
        ret.imagingDelay *= -1
        
        return ret
            
    def setEvent(self, event_type, value, event_label=None, replace=True):
        """Set or updates the time stamps of an event type.
        
        Parameters:
        ==========
        event_type: a str (valid TriggerEventType name) or a TriggerEventType
        
        value: see TriggerEvent.parseTimeValues
        
        event_label: str to be used in case a new event is created
        
        replace: boolean (default is True)
            When True, if an event of the specified type already exists in the protocol
            it will be replaced with a new one of the same type, but with the specified
            time stamps. Otherwise, the time stamps will be merged with those of
            the existing event.
            
            If an event with the specified type does not exist, it will be added
            to the protocol.
        
        """
        if event_type is None:
            event_type = TriggerEventType.presynaptic
            
        elif isinstance(event_type, str):
            if event_type in TriggerEventType.__members__:
                event_type = TriggerEventType[event_type]
                
            else:
                raise ValueError("Unknown event_type %s" % event_type)
                
        elif not isinstance(event_type, TriggerEventType):
            raise TypeError("event_type expected a string, a TriggerEventType or None; got %s instead"% type(event_type).__name__)
        
        own_event = self.getEvent(event_type)
        
        if own_event is None:
            units = pq.s
            times = TriggerEvent.parseTimeValues(value, units)
            
            own_event = TriggerEvent(times=times, event_type = event_type, labels = event_label)
                
        else:
            if isinstance(value, TriggerEvent):
                if value.event_type != own_event.event_type:
                    raise TypeError("value trigger event expected to be of %s type; it has %s instead" % (own_event.event_type, value.event_type))
                
                if value.is_same_as(own_event):
                    return
                
                if replace:
                    own_event = value.copy() # do NOT store references!
                    
                else:
                    own_event = own_event.merge(value)
                    
                if event_label is not None:
                    own_even.setLabel(event_label)
                    
            elif value is None:
                if event_type & TriggerEventType.presynaptic:
                    self.__presynaptic__ = None
                    
                elif event_type & TriggerEventType.postsynaptic:
                    self.__postsynaptic__ = None
                    
                elif event_type & TriggerEventType.photostimulation:
                    self.__photostimulation__ = None
                    
                elif event_type & TriggerEventType.acquisition:
                    self.__acquisition__ = None
            
                return
                
            else:
                units = own_event.units
                times = TriggerEvent.parseTimeValues(value, units)
                event = TriggerEvent(times=times, event_type = event_type, label = event_label)
                
                if replace:
                    own_event = event
                    
                else:
                    own_event = own_event.merge(value)
            
                if event_label is not None:
                    own_even.setLabel(event_label)
            
        if event_type & TriggerEventType.presynaptic:
            self.__presynaptic__ = own_event
            
        elif event_type & TriggerEventType.postsynaptic:
            self.__postsynaptic__ = own_event
            
        elif event_type & TriggerEventType.photostimulation:
            self.__photostimulation__ = own_event
            
        elif event_type & TriggerEventType.acquisition:
            self.__acquisition__ = own_event
            
    @property
    def presynaptic(self):
        return self.getEvent(TriggerEventType.presynaptic)

    @presynaptic.setter
    def presynaptic(self, value):
        self.setEvent(TriggerEventType.presynaptic, value)
        #if value is None:
            #self.__presynaptic__ = value
            
        #elif isinstance(value, TriggerEvent):
            #self.__presynaptic__ = value.copy()
            #self.__presynaptic__.event_type = TriggerEventType.presynaptic
                
        #else:
            #raise TypeError("Expecting a TriggerEvent or None; got %s instead" % type(value).__name__)
        
    @property
    def postsynaptic(self):
        return self.getEvent(TriggerEventType.postsynaptic)
    
    @postsynaptic.setter
    def postsynaptic(self, value):
        self.setEvent(TriggerEventType.postsynaptic, value)
        #if value is None:
            #self.__postsynaptic__ = value
            
        #elif isinstance(value, TriggerEvent):
            #self.__postsynaptic__ = value.copy()
            #self.__postsynaptic__.event_type = TriggerEventType.postsynaptic
                    
        #else:
            #raise TypeError("Expecting a TriggerEvent or None; got %s instead" % type(value).__name__)
        
    @property
    def photostimulation(self):
        return self.getEvent(TriggerEventType.photostimulation)
    
    @photostimulation.setter
    def photostimulation(self, value):
        self.setEvent(TriggerEventType.photostimulation, value)
        #if value is None:
            #self.__photostimulation__ = value
        
        #elif isinstance(value, TriggerEvent):
            #self.__photostimulation__ = value.copy()
            #self.__photostimulation__.event_type = TriggerEventType.photostimulation
                
        #else:
            #raise TypeError("Expecting a TriggerEvent or None; got %s instead" % type(value).__name__)
        
    @property
    def imagingDelay(self):
        """
        This is the delay between the start of an electrophysiology segment and 
        that of an image acquisition and helps to temporally map the events in 
        the electrophysiology to those in the imaging data.
        
        For experiments where the electrophysiology DRIVES the imaging (i.e. 
        imaging acquisition is triggered by the electrophysiology hardware) 
        this property is redundant.
        
        However, imagingDelay is necessary in the inverse situation where the
        electrophysiology is triggered by an imaging trigger (typically, by an
        imaging frame trigger output by the imaging hardware) when the "delay"
        cannot be calculated from the trigger waveforms recorded in the 
        electrophysiology data.
        
        NOTE: imagingDelay is a python Quantity (in time units, typically 's')
        and IT IS NOT a TriggerEvent object. For this reason, the imagingDelay
        will not have a corresponding event in a data segment's "events" list.
        
        """
        return self.__imaging_delay__
    
    @imagingDelay.setter
    def imagingDelay(self, value):
        """Allow chaning of imaging delay.
        
        """
        if isinstance(value, pq.Quantity):
            if value.units != pq.s:
                dim = value.units.dimensionality
                
                if not isinstance(list(dim.keys())[0], pq.UnitTime):
                    raise TypeError("Expecting a temporal quantity; got %s instead" % value)
                
            self.__imaging_delay__ = value
            
        elif value is not None:
            raise TypeError("Expecting a python Quantity with time units, or None; got %s instead" % type(value).__name__)
            
        else:
            self.__imaging_delay__ = None
        
    @property
    def imagingFrameTrigger(self):
        """Returns an imaging_frame trigger event, if any
        """
        return self.__acquisition__
        #return self.__get_acquisition_event__(TriggerEventType.imaging_frame)
        
    @imagingFrameTrigger.setter
    def imagingFrameTrigger(self, value):
        """Pass None to clear acquisition events
        """
        self.__acquisition__ = value
        #self.__set_acquisition_event__(value)
        
    @property
    def imagingLineTrigger(self):
        """Returns an imaging_line trigger event, if any
        """
        return self.__acquisition__
        #return self.__get_acquisition_event__(TriggerEventType.imaging_line)
    
    @imagingLineTrigger.setter
    def imagingLineTrigger(self, value):
        """Pass None to clear acquisition events
        """
        self.__acquisition__ = value
        #self.__set_acquisition_event__(value)

    @property
    def sweep(self):
        """Returns a sweep trigger event, if any
        """
        return self.__acquisition__
        #return self.__get_acquisition_event__(TriggerEventType.sweep)
    
    @sweep.setter
    def sweep(self, value):
        self.__acquisition__ = value
        #self.__set_acquisition_event__(value)
        
    @property
    def name(self):
        return self.__protocol_name__
    
    @name.setter
    def name(self, value):
        if isinstance(value, str):
            self.__protocol_name__ = value
            
        else:
            raise TypeError("Expecting a str; got %s instead" % type(value).__name__)
        
    @property
    def segmentIndex(self):
        """The segment indexing object where this protocol applies.
        
        CAUTION This can be a list of int, a range object or a slice object
        """
        return self.__segment_index__
    
    @segmentIndex.setter
    def segmentIndex(self, index):
        """The segment indexing object where this protocol applies.
        
        CAUTION This can be a list of int, a range object or a slice object
        """
        if isinstance(index, int):
            self.__segment_index__ = [index]
            
        elif isinstance(index, (tuple, list)) and (len(index)==0 or all([isinstance(i, int) for i in index])):
            self.__segment_index__ = [k for k in index]
            
        elif isinstance(index, (range, slice)):
            self.__segment_index__ = index
            
        else:
            raise TypeError("Expecting an int, a possibly empty sequence of int values, a range or a slice; got %s instead" % type(index).__name__)
            
    @property
    def isempty(self):
        return len(self) == 0
    
    @safeWrapper
    def copy(self):
        return TriggerProtocol(pre = self) # copy constructor
        
    @safeWrapper
    def updateSegmentIndex(self, value):
        """Update current segment index with the one specified in value.
        
        When value is a list or an int, the current segment index will be coerced to a list.
        """
        # NOTE: 2019-03-15 15:41:15
        # TODO FIXME this is pretty expensive and convoluted - 
        #            why not just decide to keep __segment_index__ as a list?
        
        if isinstance(self.__segment_index__, (range, slice)):
            mystart = self.__segment_index__.start
            mystop = self.__segment_index__.stop
            mystep = self.__segment_index__.step
            
            if isinstance(value, (range,slice)):
                otherstart  = value.start
                otherstop   = value.stop
                otherstep   = value.step
                
                
                if mystep != otherstep:
                    raise TypeError("Cannot update frame indexing %s and from %s" % (self.__segment_index__, value))
                
                if mystart is None or otherstart is None:
                    finalstart = None
                    
                else:
                    finalstart = min(mystart, otherstart)
                    
                finalstop = max(mystop, otherstop)
                
                if isinstance(self.__segment_index__, range):
                    if finalstart is None:
                        finalstart = 0
                        
                    self.__segment_index__ = range(finalstart, mystep, finalstop)
                    
                else:
                    self.__segment_index__ = slice(finalstart, mystep, finalstop)
                
            elif isinstance(value, (tuple, list)) and all([isinstance(v, int) for v in value]): 
                # NOTE: 2017-12-14 15:12:06
                # because the result may contain indices at irregular intervals,
                # which is not what a range or slice object produces, we need to
                # coerce self.__segment_index__ to a list if not already a list
                #
                
                if isinstance(self.__segment_index__, range):
                    newlist = [f for f in self.__segment_index__]
                    
                else: # self.__segment_index__ is a slice; realise its indices on the max index in value
                    if mystop is None:
                        newlist = [f for f in range(self.__segment_index__.indices(max(value)))]
                        
                    else:
                        newlist = [f for f in range(self.__segment_index__.indices(max(mystop, max(value))))]
                                                    
                newlist += (list(value)[:])
                    
                # NOTE: 2017-12-14 15:09:41#
                # coerce self.__segment_index__ to a list
                self.__segment_index__ = sorted(list(set(newlist))) 
                
            elif isinstance(value, int):# coerce self.__segment_index__ to a list also
                # NOTE: 2017-12-14 15:12:06
                # because the result may contain indices at irregular intervals,
                # which is not what a range or slice object produces, we need to
                # coerce self.__segment_index__ to a list if not already a list
                #
                
                if isinstance(self.__segment_index__, range):
                    newlist = [f for f in self.__segment_index__]
                    
                else:
                    if mystop is None:
                        # FIXME
                        newlist = [f for f in range(self.__segment_index__.indices(value+1))]
                        
                    else:
                        # FIXME
                        newlist = [f for f in range(self.__segment_index__.indices(max(mystop, value+1)))]
                     
                newlist.append(value)
                
                self.__segment_index__ = sorted(list(set(newlist)))
                
            else:
                raise TypeError("Cannot update current frame indexing %s with %s)" % (self.__segment_index__, value))
            
        elif isinstance(self.__segment_index__, (tuple, list)):
            if isinstance(value, (tuple, list)):
                # this ensures unique and sorted frame index list
                self.__segment_index__ = sorted(list(set(list(self.__segment_index__) + list(value))))
                
            elif isinstance(value, int):
                newlist = list(self.__segment_index__)
                newlist.append(value)
                self.__segment_index__ = sorted(list(set(newlist)))
                
            elif isinstance(value, (range, slice)):
                otherstart  = value.start
                otherstop   = value.stop
                otherstep   = value.step
                
                if isinstance(value, range):
                    newlist = [f for f in value]
                    
                else:
                    if otherstop is None:
                        newlist = [f for f in range(value.indices(max(self.__segment_index__)+1))]
                        
                    else:
                        newlist = [f for f in range(value.indices(max(otherstop, max(self.__segment_index__)+1)))]
                        
                newlist += list(self.__segment_index__)[:]
                
                self.__segment_index__ = sorted(list(set(newlist)))
                
            else:
                raise TypeError("Cannot update frame indexing %s with %s" % (self.__segment_index__, value))
                    
                    
        elif isinstance(self.__segment_index__, int):
            if isinstance(value, int):
                self.__segment_index__ = sorted([self.__segment_index__, value])
                
            elif isinstance(value, (tuple, list)):
                newlist = [f for f in value] + [self.__segment_index__]
                
                self.__segment_index__ = sorted(list(set(newlist)))
                
            elif isinstance(value, (range, slice)):
                otherstart  = value.start
                otherstop   = value.stop
                otherstep   = value.step
                
                if isinstance(value, range):
                    newlist = [f for f in value]
                    
                else:
                    if otherstop is None:
                        newlist = [f for f in range(value.indices(self.__segment_index__+1))]
                        
                    else:
                        newlist = [f for f in range(value.indices(max(otherstop, self.__segment_index__+1)))]
                        
                newlist.append(self.__segment_index__)
                
                self.__segment_index__ = sorted(list(set(newlist)))
                
            else:
                raise TypeError("Cannot update frame indexing %s with %s" % (self.__segment_index__, value))
        
    
    def segmentIndices(self, value=None):
        """Returns a list of segment indices.
        'value' is used only when segmentIndex is a python slice object, and it must be an int
        """
        
        if isinstance(self.__segment_index__, slice):
            if value is None:
                value = self.__segment_index__.stop
                
            if not isinstance(value, int):
                raise TypeError("When segment index is a slice a value of type int is required")
            
            return [x for x in range(*self.__segment_index__.indices(value))]
        
        elif isinstance(self.__segment_index__, range):
            return [x for x in self.__segment_index__]
        
        elif isinstance(self.__segment_index__, (int, tuple, list)):
            return self.__segment_index__
        

#### BEGIN Module-level functions

@safeWrapper
def auto_define_trigger_events(src, analog_index, event_type, 
                               times=None, label=None, name=None, 
                               use_lo_hi=True, time_slice=None, 
                               clearSimilarEvents=True, clearTriggerEvents=True, 
                               clearAllEvents=False):
    """Populates the events lists for the segments in src with TriggerEvent objects.
    
    Searches for trigger waveforms in signals specified by analog_index, to define
    TriggerEvent objects.
    
    A TriggerEvent is an array of time values and will be added to the events list
    of the neo.Segment objects in src.
    
    Calls detect_trigger_events()
    
    Parameters:
    ===========
    
    src: a neo.Block, a neo.Segment, or a list of neo.Segment objects
    
    analog_index:   specified which signal to use for event detection; can be one of:
    
                    int (index of the signal array in the data analogsignals)
                        assumes that _ALL_ segments in "src" have the desired analogsignal
                        at the same position in the analogsignals array
    
                    str (name of the analogsignal to use for detection) -- must
                        resolve to a valid analogsignal index in _ALL_ segments in 
                        "src"
                    
                    a sequence of int (index of the signal), one per segment in src 

    event_type: a str that specifies the type of trigger event e.g.:
                'acquisition',
                'frame'
                'imaging',
                'imaging_frame',
                'imaging_line',
                'line'
                'photostimulation',
                'postsynaptic',
                'presynaptic',
                'sweep',
                'user'
                
            or a valid datatypes.TriggerEventType enum type, e.g. TriggerEventType.presynaptic
    
    (see detect_trigger_events(), datatypes.TriggerEventType)
    
    Named parameters:
    =================
    times: either None, or a python quantity array with time units
    
        When "times" is None (the default) the function calls detect_trigger_events() 
        on the analogsignal specified by analog_index in src, to detect trigger 
        events. The specified analogsignal must therefore contain trigger waveforms 
        (typically, rectangular pulses).
        
        Otherwise, the values in the "times" array will be used to define the 
        trigger events.
        
    label: common prefix for the individual trigger event label in the event array
            (see also detect_trigger_events())
    
    name: name for the trigger event array 
            (see also detect_trigger_events())
    
    use_lo_hi: boolean, (default is True);  
        when True, use the rising transition to detect the event time 
            (see also detect_trigger_events())
        
    time_slice: pq.Quantity tuple (t_start, t_stop) or None.
        When detecting events (see below) the time_slice can specify which part of  
        a signal can be used for automatic event detection.
        
        When time_slice is None this indicates that the events are to be detected 
        from the entire signal.
        
        The elements need to be Python Quantity objects compatible with the domain
        of the signal. For AnalogSignal, this is time (usually, pq.s)
        
    NOTE: The following parameters are passed directly to embed_trigger_event
    
    clearSimilarEvents: boolean, default is True: 
        When True, existing neo.Event objects with saame time stamps, labels,
            units and name as those of the parameter "event" will be removed. 
            In case of TriggerEvent objects the comparison also considers the 
            event type.
            
        NOTE: 2019-03-16 12:06:14
        When "event" is a TriggerEvent, this will clear ONLY the pre-exising
        TriggerEvent objects of the same type as "event" 
        (see datatypes.TriggerEventType for details)
        
    clearTriggerEvents: boolean, default is True
        when True, clear ALL existing TriggerEvent objects
        
        NOTE: 2019-03-16 12:06:07
        to clear ONLY existing TriggerEvent objects with the same type
            as the "event" (when "event" is also a TriggerEvent) 
            set clearSimilarEvents to True; see NOTE: 2019-03-16 12:06:14
    
    clearAllEvents: boolean, default is False:
        When True, clear ANY existing event in the segment.
        
    Returns:
    ========
    The src parameter (a reference)
    
    Side effects:
        Creates and appends TriggerEvent objects to the segments in src
    """
    from . import datatypes as dt
    
    if isinstance(src, neo.Block):
        data = src.segments
        
    elif isinstance(src, (tuple, list)) and all([isinstance(s, neo.Segment) for s in src]):
        data = src
        
    elif isinstance(src, neo.Segment):
        data = [src]
        
    else:
        raise TypeError("src expected to be a neo.Block, neo.Segment or a sequence of neo.Segment objects; got %s instead" % type(src).__name__)
    
    if isinstance(times, pq.Quantity):
        if not check_time_units(times):  # event times passed at function call -- no detection is performed
            raise TypeError("times expected to have time units; it has %s instead" % times.units)

        for segment in data: # construct eventss, store them in segments
            event = TriggerEvent(times=times, units=times.units,
                                    event_type=event_type, labels=label, 
                                    name=name)
            
            embed_trigger_event(event, segment,
                                clearTriggerEvents = clearTriggerEvents,
                                clearSimilarEvents = clearSimilarEvents,
                                clearAllEvents = clearAllEvents)
            
    elif times is None: #  no event times specified =>
        # auto-detect trigger events from signal given by analog_index
        if isinstance(analog_index, str):
            # signal specified by name
            analog_index = get_index_of_named_signal(data, analog_index)
            
        if isinstance(analog_index, (tuple, list)):
            if all(isinstance(s, (int, str)) for s in analog_index):
                if len(analog_index) != len(data):
                    raise TypeError("When a list of int, analog_index must have as many elements as segments in src (%d); instead it has %d" % (len(data), len(analog_index)))
                
                for (s, ndx) in zip(data, analog_index):
                    if isinstance(ndx, str):
                        sndx = get_index_of_named_signal(s, ndx, silent=True)
                        
                    else:
                        sndx = ndx
                        
                    if sndx in range(len(s.analogsignals)):
                        if isinstance(time_slice, (tuple, list)) \
                            and all([isinstance(t, pq.Quantity) and check_time_units(t) for t in time_slice]) \
                                and len(time_slice) == 2:
                            event = detect_trigger_events(s.analogsignals[sndx].time_slice(time_slice[0], time_slice[1]), 
                                                        event_type=event_type, 
                                                        use_lo_hi=use_lo_hi, 
                                                        label=label, name=name)
                            
                        else:
                            event = detect_trigger_events(s.analogsignals[sndx], 
                                                        event_type=event_type, 
                                                        use_lo_hi=use_lo_hi, 
                                                        label=label, name=name)
                            
                        embed_trigger_event(event, s, 
                                            clearTriggerEvents = clearTriggerEvents,
                                            clearSimilarEvents = clearSimilarEvents,
                                            clearAllEvents = clearAllEvents)
                        
                    else:
                        raise ValueError("Invalid signal index %d for a segment with %d analogsignals" % (ndx, len(s.analogsignals)))

        elif isinstance(analog_index, int):
            for s in data:
                if analog_index in range(len(s.analogsignals)):
                    if isinstance(time_slice, (tuple, list)) \
                        and all([isinstance(t, pq.Quantity) and dt.check_time_units(t) for t in time_slice]) \
                            and len(time_slice) == 2:
                        event = detect_trigger_events(s.analogsignals[analog_index].time_slice(time_slice[0], time_slice[1]), 
                                                      event_type=event_type, 
                                                      use_lo_hi=use_lo_hi, 
                                                      label=label, name=name)
                        
                    else:
                        event = detect_trigger_events(s.analogsignals[analog_index], 
                                                      event_type=event_type, 
                                                      use_lo_hi=use_lo_hi, 
                                                      label=label, name=name)
                        
                    embed_trigger_event(event, s, 
                                        clearTriggerEvents = clearTriggerEvents,
                                        clearSimilarEvents = clearSimilarEvents,
                                        clearAllEvents = clearAllEvents)
                    
                else:
                    raise ValueError("Invalid signal index %d for a segment with %d analogsignals" % (analog_index, len(s.analogsignals)))
                
        else:
            raise RuntimeError("Invalid signal index %s" % str(analog_index))

    else:
        raise TypeError("times expected to be a python Quantity array with time units, or None")
                
                
    return src

@safeWrapper
def detect_trigger_events(x, event_type, use_lo_hi=True, label=None, name=None):
    """Creates a datatypes.TriggerEvent object (array) of specified type.
    
    Calls detect_trigger_times(x) to detect the time stamps.
    
    Parameters:
    ===========
    
    x: neo.AnalogSsignal
    
    event_type: a datatypes.TriggerEventType enum value or datatypes.TriggerEventType name (str)
    
    Named parameters:
    ================
    use_lo_hi: boolean, optional (default is True): 
    
        The datatypes.TriggerEvent objects will be created from low -> high 
        state transition times when "use_lo_hi" is True, otherwise from the 
        high -> low state transition times.
            
    label: str, optional (default None): the labels for the events in the 
        datatypes.TriggerEvent array
    
    name: str, optional (default  None): the name of the generated 
        datatypes.TriggerEvent array
    
    Returns:
    ========
    
    A datatypes.TriggerEvent object (essentially an array of time stamps)
    
    """
    #from . import datatypes as dt
    
    if not isinstance(x, (neo.AnalogSignal, DataSignal, np.ndarray)):
        raise TypeError("Expecting a neo.AnalogSignal, or a datatypes.DataSignal, or a np.ndarray as first parameter; got %s instead" % type(x).__name__)
    
    if isinstance(event_type, str):
        if event_type in list(TriggerEventType.__members__.keys()):
            event_type = TriggerEventType[event_type]
            
        else:
            raise (ValueError("unknown trigger event type: %s; expecting one of %s" % event_type, " ".join(list([TriggerEventType.__members__.keys()]))))
        
    elif not isinstance(event_type, TriggerEventType):
        raise TypeError("'event_type' expected to be a datatypes.TriggerEventType enum value, or a str in datatypes.TriggerEventType enum; got %s instead" % type(event_type).__name__)

    if label is not None and not isinstance(label, str):
        raise TypeError("'label' parameter expected to be a str or None; got %s instead" % type(label).__name__)
    
    if name is not None and not isinstance(name, str):
        raise TypeError("'name' parameter expected to be a str or None; got %s instead" % type(name).__name__)
    
    if not isinstance(use_lo_hi, bool):
        raise TypeError("'use_lo_hi' parameter expected to be a boolean; got %s instead" % type(use_lo_hi).__name__)
    
    [lo_hi, hi_lo] = detect_trigger_times(x)
    
    if use_lo_hi:
        times = lo_hi
        
    else:
        times = hi_lo
        
    trig = TriggerEvent(times=times, units=x.times.units, event_type=event_type, labels=label, name=name)
    
    if name is None:
        if label is not None:
            trig.name = "%d%s" % (trig.times.size, label)
            
        else:
            if np.all(trig.labels == trig.labels[0]):
                trig.name = "%d%s" % (trig.times.size, label)
                
            else:
                trig.name = "%dtriggers" % trig.times.size
                
    
    return trig
    
    
@safeWrapper
def detect_trigger_times(x):
    """Detect and returns the time stamps of rectangular pulse waveforms in a neo.AnalogSignal
    
    The signal must undergo at least one transition between two distinct states 
    ("low" and "high").
    
    The function is useful in detecting the ACTUAL time of a trigger (be it 
    "emulated" in the ADC command current/voltage or in the digital output "DIG") 
    when this differs from what was intended in the protocol (e.g. in Clampex)
    """
    from scipy import cluster
    from scipy import signal
    
    #flt = signal.firwin()
    
    if not isinstance(x, neo.AnalogSignal):
        raise TypeError("Expecting a neo.AnalogSignal object; got %s instead" % type(x).__name__)
    
    # WARNING: algorithm fails for noisy signls with no TTL waveform!
    cbook, dist = cluster.vq.kmeans(x, 2)
    
    #print("code_book: ", cbook)
    
    #print("sorted code book: ", sorted(cbook))
    
    code, cdist = cluster.vq.vq(x, sorted(cbook))
    
    diffcode = np.diff(code)
    
    ndx_lo_hi = np.where(diffcode ==  1)[0].flatten() # transitions from low to high
    ndx_hi_lo = np.where(diffcode == -1)[0].flatten() # hi -> lo transitions
    
    if ndx_lo_hi.size:
        times_lo_hi = [x.times[k] for k in ndx_lo_hi]
        
    else:
        times_lo_hi = None
        
    if ndx_hi_lo.size:
        times_hi_lo = [x.times[k] for k in ndx_hi_lo]
        
    else:
        times_hi_lo = None
        
    return times_lo_hi, times_hi_lo


def remove_trigger_protocol(protocol, block):
    """Removes embedded trigger events associated with a specified trigger protocol
    """
    if not isinstance(protocol, TriggerProtocol):
        raise TypeError("'protocol' expected to be a TriggerProtocol; got %s instead" % type(protocol).__name__)
    
    if not isinstance(block, neo.Block):
        raise TypeError("'block' was expected to be a neo.Block; got % instead" % type(block).__name__)
    
    if len(protocol.segmentIndices()) > 0:
        protocol_segments = protocol.segmentIndices()
        
    else:
        protocol_segments = range(len(block.segments))
        
    for k in protocol_segments:
        if k >= len(block.segments):
            warnings.warn("skipping segment index %d of protocol %s because it points outside the list of segments with %d elements" % (k, protocol.name, len(block.segments)), 
                          RuntimeWarning)
            continue
        
        if k < 0:
            warnings.warn("skipping negative segment index %d in protocol %s" % (k, protocol.name), RuntimeWarning)
            continue
        
        for event in protocol.events:
            remove_events(event, block.segments[k])
        
        block.segments[k].annotations.pop("trigger_protocol", None)
                
def modify_trigger_protocol(protocol, block):
    """
    Uses the events in the protocol to add TriggerEvents or modify exiting ones,
    in the segment indices specified by this protocol's segment indices.
    """
    if not isinstance(protocol, TriggerProtocol):
        raise TypeError("'value' expected to be a TriggerProtocol; got %s instead" % type(value).__name__)
    
    if not isinstance(block, neo.Block):
        raise TypeError("'block' was expected to be a neo.Block; got % instead" % type(block).__name__)
    
    if len(protocol.segmentIndices()) > 0:
        protocol_segments = protocol.segmentIndices()
        
    else:
        protocol_segments = range(len(block.segments))
        
    for k in protocol_segments:
        if k >= len(block.segments):
            warnings.warn("skipping segment index %d of protocol %s because it points outside the list of segments with %d elements" % (k, protocol.name, len(block.segments)), 
                          RuntimeWarning)
            continue
        
        if k < 0:
            warnings.warn("skipping negative segment index %d in protocol %s" % (k, protocol.name), RuntimeWarning)
            continue
        
        # check if the segment has any events of the type found in the protocol
        # remove them and add the protocol's events instead
        # NOTE: ONE segment -- ONE protocol at all times.
        if isinstance(protocol.presynaptic, TriggerEvent) and protocol.presynaptic.event_type == TriggerEventType.presynaptic:
            presynaptic_events = [e for e in block.segments[k].events if isinstance(e, TriggerEvent) and e.event_type == TriggerEventType.presynaptic]
            
            for event in presynaptic_events:
                # should contain AT MOST ONE event object
                block.segments[k].events.remove(event)
                
            block.segments[k].events.append(protocol.presynaptic)
                
        if isinstance(protocol.postsynaptic, TriggerEvent) and protocol.postsynaptic.event_type == TriggerEventType.postsynaptic:
            postsynaptic_events = [e for e in block.segments[k].events if isinstance(e, TriggerEvent) and e.event_type == TriggerEventType.postsynaptic]
            
            for event in postsynaptic_events:
                block.segments[k].events.remove(event)
                
            block.segments[k].events.append(protocol.postsynaptic)
            
            
        if isinstance(protocol.photostimulation, TriggerEvent) and protocol.photostimulation.event_type == TriggerEventType.photostimulation:
            photostimulation_events = [e for e in block.segments[k].events if isinstance(e, TriggerEvent) and e.event_type == TriggerEventType.photostimulation]
            
            for event in photostimulation_events:
                block.segments[k].events.remove(event)
                
            block.segments[k].event.append(protocol.photostimulation)
            
        if len(protocol.acquisition):
            for event in protocol.acquisition:
                existing_events = [e for e in block.segments[k].events if isinstance(e, TriggerEvent) and e.event_type == event.event_type]
                
                for e in existing_events:
                    block.segments[k].events.remove(e)
                    
                block.segments[k].events.append(event)
                
        if isinstance(protocol.name, str) and len(protocol.name.strip()) > 0:
            pr_name = protocol.name
            
        else:
            pr_name = "unnamed_protocol"
            
        block.segments[k].annotations["trigger_protocol"] = pr_name


def embed_trigger_event(event, segment, clearSimilarEvents=True, clearTriggerEvents=True, clearAllEvents=False):
    """
    Embeds the neo.Event object event in the neo.Segment object segment.
    
    In the segment's events list, the event is stored by reference.
    
    WARNING: one could easily append events with identical time stamps!
        While this is NOT recommended, it cannot be easily prevented.
        
        To add time stamps to a TriggerEvent, create a new TriggerEvent object
        by calling use TriggerEvent.append_times() or TriggerEvent.merge() then 
        embed it here.
        
        To add time stamps to a generic neo.Event, create a new Event by calling
        Event.merge() then embed it here.
        
        To remove time stamps ise numpy array indecing on the event.
        
        See datatypes.TriggerEvent for details.
    
    Parameters:
    ===========
    
    event: a neo.Event, or a datatypes.TriggerEvent
    
    segment: a neo.Segment
    
    Named parameters:
    ===================
    
    clearSimilarEvents: boolean, default is True: 
        When True, existing neo.Event objects with saame time stamps, labels,
            units and name as those of the parameter "event" will be removed. 
            In case of TriggerEvent objects the comparison also considers the 
            event type.
            
        NOTE: 2019-03-16 12:06:14
        When "event" is a TriggerEvent, this will clear ONLY the pre-exising
        TriggerEvent objects of the same type as "event" 
        (see datatypes.TriggerEventType for details)
        
    clearTriggerEvents: boolean, default is True
        when True, clear ALL existing TriggerEvent objects
        
        NOTE: 2019-03-16 12:06:07
        to clear ONLY existing TriggerEvent objects with the same type
            as the "event" (when "event" is also a TriggerEvent) 
            set clearSimilarEvents to True; see NOTE: 2019-03-16 12:06:14
    
    clearAllEvents: boolean, default is False:
        When True, clear ANY existing event in the segment.
        
    Returns:
    =======
    A reference to the segment.
    
    """
    if not isinstance(event, (neo.Event, TriggerEvent)):
        raise TypeError("event expected to be a neo.Event; got %s instead" % type(event).__name__)
    
    if not isinstance(segment, neo.Segment):
        raise TypeError("segment expected to be a neo.Segment; got %s instead" % type(segment).__name__)
    
    if clearAllEvents:
        segment.events.clear()
        
    else:
        all_events_ndx = range(len(segment.events))
        evs = []
    
        if clearSimilarEvents:
            evs = [(k,e) for (k,e) in enumerate(segment.events) if is_same_as(event, e)]
            
        elif clearTriggerEvents:
            evs = [(k,e) for (k,e) in enumerate(segment.events) if isinstance(e, TriggerEvent)]
            
        if len(evs):
            (evndx, events) = zip(*evs)
            
            keep_events = [segment.events[k] for k in all_events_ndx if k not in evndx]
            
            segment.events[:] = keep_events
            
    segment.events.append(event)
    
    return segment
            
        
@safeWrapper
def embed_trigger_protocol(protocol, target, useProtocolSegments=True, clearTriggers=True, clearEvents=False):
    """ Embeds TriggerEvent objects found in the TriggerProtocol 'protocol', 
    in the segments of 'target'.
    
    Inside the target, trigger event objects are stored by reference!
    
    Parameters:
    ==========
    protocol: a dataypes.TriggerProtocol object
    
    target: a neo.Block, neo.Segment or a sequence of neo.Segment objects
    
    Keyword parameters:
    ==================
    
    useProtocolSegments: boolean, default True: use the segments indices given by the protocol
        to embed only in those segments in the "target"
        
        when False, "target" is expected to be a sequence of neo.Segments as long as
        the protocol's segmentIndices
        
        this is ignored when "target" is a neo.Block or a neo.Segment
    
    clearTriggers: boolean, default True; when True, existing TriggerEvent obects will be removed
    
    clearEvents: boolean, default False; when True, clear _ALL_ existing neo.Event objects
        (including TriggerEvents!)
    
    CAUTION: This will wipe out existing trigger events in those segments
    indicated by the 'segmentIndices' attribute of 'protocol'.
    """
    # check if there are synaptic events already in the scans data target:
    # each segment can hold at most one TriggerEvent object of each 
    # type (pre-, post-, photo-);
    # NOTE: a TriggerEvent actually holds an ARRAY of time points
    
    if not isinstance(protocol, TriggerProtocol):
        raise TypeError("'protocol' expected to be a TriggerProtocol; got %s instead" % type(protocol).__name__)
    
    if not isinstance(target, (neo.Block, neo.Segment)):
        raise TypeError("'target' was expected to be a neo.Block or neo.Segment; got %s instead" % type(target).__name__)
    
    if isinstance(target, neo.Block):
        segments = target.segments
        
        if len(protocol.segmentIndices()) > 0:
            value_segments = [i for i in protocol.segmentIndices() if i in range(len(segments))]
            value_segments = protocol.segmentIndices()
            
        else:
            value_segments = range(len(segments))
            
        if len(value_segments) == 0:
            warnings.warn("No suitable segment index found in protocol %s with %s, given %d segments in for %s %s" % (protocol.name, protocol.segmentIndices(), len(segments), type(target).__name__, target.name))
            return
        
        
    elif isinstance(target, (tuple, list)) and all([isinstance(s, neo.Segment) for s in target]):
        segments = target
        if not useProtocolSegments:
            if len(segments) != len(protocol.segmentIndices):
                raise ValueError("useProtocolSegments is False, but target has %d segments whereas protocol indicates %d segments" % (len(segments), len(protocol.segmentIndices())))
            
            value_segments = range(len(segments))
            
        else:
            # the list of segments 
            if len(protocol.segmentIndices()) > 0:
                value_segments = [i for i in protocol.segmentIndices() if i in range(len(segments))]
                value_segments = protocol.segmentIndices()
                
            else:
                value_segments = range(len(segments))
            
        if len(value_segments) == 0:
            warnings.warn("No suitable segment index found in protocol %s with %s, given %d segments in for %s %s" % (protocol.name, protocol.segmentIndices(), len(segments), type(target).__name__, target.name))
            return
        
    elif isinstance(target, neo.Segment):
        segments = [target]
        value_segments = [0]
    
    if len(value_segments) == 0:
        warnings.warn("No suitable segment index found in protocol %s with %s, given %d segments in for %s %s" % (protocol.name, protocol.segmentIndices(), len(segments), type(target).__name__, target.name))
        return
        
    #print("embed_trigger_protocol: value_segments ", value_segments, " target segments: %d" % len(target.segments))
        
    for k in value_segments: 
        if clearTriggers:
            trigs = [(evndx, ev) for (evndx, ev) in enumerate(segments[k].events) if isinstance(ev, TriggerEvent)]

            if len(trigs): # TriggerEvent objects found in segment
                (trigndx, trigevs) = zip(*trigs)
                
                all_events_ndx = range(len(segments[k].events))
                
                keep_events = [segments[k].events[i] for i in all_events_ndx if i not in trigndx]
                
                segments[k].events[:] = keep_events
                
        elif clearEvents:
            segments[k].events.clear()
            
        # now go and append events contained in protocol
        
        #print("embed_trigger_protocol: in %s (segment %d): protocol.name %s; acquisition: %s" % (target.name, k, protocol.name, protocol.acquisition))
        
        if isinstance(protocol.acquisition, (tuple, list)) and len(protocol.acquisition):
            # for old API
            segments[k].events.append(protocol.acquisition[0]) # only ONE acquisition event per protocol!
                
        elif isinstance(protocol.acquisition, TriggerEvent):
            segments[k].events.append(protocol.acquisition)
                
        if protocol.presynaptic is not None:
                segments[k].events.append(protocol.presynaptic)
            
        if protocol.postsynaptic is not None:
                segments[k].events.append(protocol.postsynaptic)
            
        if protocol.photostimulation is not None:
                segments[k].events.append(protocol.photostimulation)
                                
        if isinstance(protocol.name, str) and len(protocol.name.strip()) > 0:
            pr_name = protocol.name
            segments[k].name = protocol.name
            
        else:
            pr_name = "unnamed_protocol"
            
        segments[k].annotations["trigger_protocol"] = pr_name


@safeWrapper
def parse_trigger_protocols(src):
    """Constructs a list of TriggerProtocol objects using embeded TriggerEvent objects.
    
    "src" may be a neo.Segment, or a neo.Block (see below).
    
    Parameters:
    ==========
    "src" can be a neo.Block with a non-empty segments list, or 
        a list of neo.Segments, or just a neo.Segment
        
    Returns:
    =======
    A list of protocols
    src
        
    ATTENTION: this constructs TriggerProtocol objects with default names.
    Usually this is NOT what you want !!!
    
    Individual TriggerEvent objects can be manually appended to the events 
        list of each neo.Segment.
    
    Alternatively, the function detect_trigger_times() in "ephys" module can 
    help generate TriggerEvent objects from particular neo.AnalogSignal arrays
    containing recorded trigger-like data (with transitions between a low and 
    a high state, e.g. rectangular pulses, or step functions).
    
    Returns an empty list if no trigger events were found.
    
    NOTE: each segment in "src" can have at most ONE protocol
    
    NOTE: each protocol can have at most one event for each event type in 
        presynaptic, postsynaptic, and photostimulation
    
    NOTE: each event object CAN contain more than one time stamp  (i.e. a 
        pq.Quantity array -- which in fact derives from np.ndarray)
    
    NOTE: several segments CAN have the same protocol!
    
    Once generated, the TriggerProtocol objects should be stored somewhere, for 
    example in the "annotations" dictoinary of the block or segment so that they
    won't have to be recreated (especially when their names/event time stamps
    will have been customized at later stages)
    
    CAUTION: The TriggerEvent objects in the protocols are COPIES of those found
        in "src". This means that any permissible modification brought to the 
        events in the TriggerProtocol is NOT reflected in the events of the source
        "src".
        
        To enable this, call embed_trigger_protocol() by using:
            each protocol in the result list
            "src" as target
            clearTriggers parameter set to True
    
        NOTE: Permissible modifications to TriggerEvents are changes to their 
            labels, names, and units. These will be reflected in the embedded
            events when they are stored by reference.
        
            Event time stamps can only be changed by creating an new TriggerEvent.
            To reflect time stamp changes in the "src" events, call remove_events()
            then embed_trigger_event() for the particular event and neo.Segment 
            in "src".
            
        
    """
    def __compose_protocol__(events, protocol_list, index = None):
        """
        events: a list of TriggerEvent objects
        
        protocol: TriggerProtocol or None (default); 
            when a trigger protocol, just update it (especially the segment indices)
            else: create a new TriggerProtocol
            
        segment_index: int or None (default): index of segment in the collection; will
            be appended to the protocol's segment indices
            
            When None the protocol's segment indices will not be changed
        
        """
        pr_names = []
        pr_first = []
            
        imaq_names = []
        imaq_first = []
        
        protocol = TriggerProtocol() # name = protocol_name)
        
        for e in events:
            if e.event_type == TriggerEventType.presynaptic:
                if protocol.presynaptic is None:
                    protocol.presynaptic = e
                    
                    pr_names.append(e.name)
                    pr_first.append(e.times.flatten()[0])
                    
                else:
                    warnings.warn("skipping presynaptic event array %s as protocol %s has already got one (%s)" % (e, protocol.name, protocol.presynaptic))
                    
            elif e.event_type == TriggerEventType.postsynaptic:
                if protocol.postsynaptic is None:
                    protocol.postsynaptic = e

                    pr_names.append(e.name)
                    pr_first.append(e.times.flatten()[0])
                        
                    
                else:
                    warnings.warn("skipping postsynaptic event array %s as protocol %s has already got one (%s)" % (e, protocol.name, protocol.postsynaptic))
                    
            elif e.event_type == TriggerEventType.photostimulation:
                if protocol.photostimulation is None:
                    protocol.photostimulation = e

                    pr_names.append(e.name)
                    pr_first.append(e.times.flatten()[0])
                    
                else:
                    warnings.warn("skipping photostimulation event array %s as protocol %s has already got one (%s)" % (e, protocol.name, protocol.photostimulation))
                    
            elif e.event_type & TriggerEventType.acquisition:
                # NOTE: only ONE acquisition trigger event per segment!
                if isinstance(protocol.acquisition, (tuple, list)) and len(protocol.acquisition) == 0: # or e not in protocol.acquisition:
                    protocol.acquisition[:] = [e]
                    
                else:
                    protocol.acquisition = e

                imaq_names.append(e.name)
                imaq_first.append(e.times.flatten()[0])
                
                if e.event_type == TriggerEventType.imaging_frame:
                    protocol.imagingDelay = e.times.flatten()[0]
                
        # NOTE 2017-12-16 10:08:20 DISCARD empty protocols
        if len(protocol) > 0: 
            # assign names differently if only imaging events are present
            if len(pr_first) > 0 and len(pr_first) == len(pr_names):
                plist = [(k, t,name) for k, (t, name) in enumerate(zip(pr_first, pr_names))]
                
                plist.sort()
                
                pr_names = [name_ for k, p, name_ in plist]
                
            elif len(imaq_names) > 0 and len(imaq_first) == len(imaq_names):
                plist = [(k,t,name) for k, (t,name) in enumerate(zip(imaq_first, imaq_names))]
                plist.sort()
                
                pr_names = [name_ for k, p, name_ in plist]
                    
            protocol.name = " ".join(pr_names)
            
            if isinstance(index, int):
                protocol.__segment_index__ = [index]
            
            if len(protocol_list) == 0:
                protocol_list.append(protocol)
                
            else:
                pp = [p_ for p_ in protocol_list if p_.hasSameEvents(protocol) and p_.imagingDelay == protocol.imagingDelay]
                
                if len(pp):
                    for p_ in pp:
                        p_.updateSegmentIndex(protocol.segmentIndices())
                        
                else:
                    protocol_list.append(protocol)
        
    protocols = list()
    
    if isinstance(src, neo.Block):
        # NOTE: 2019-03-14 22:01:20
        # trigs is a sequence of tuples: (index, sequence of TriggerEvent objects)
        # segments without events are skipped
        # segment events that are NOT TriggerEvent objects are skipped
        trigs = [ (k, [e for e in s.events if isinstance(e, TriggerEvent)]) \
                        for k,s in enumerate(src.segments) if len(s.events)]
        
        if len(trigs) == 0:
            return protocols, src
        
        for (index, events) in trigs:
            __compose_protocol__(events, protocols, index=index)
            
        if len(protocols):
            for p in protocols:
                for s in p.segmentIndices():
                    src.segments[s].annotations["trigger_protocol"] = p.name
        
    elif isinstance(src, neo.Segment):
        trigs = [e for e in src.events if isinstance(e, TriggerEvent)]
        
        if len(trigs) == 0:
            return protocols, src
        
        __compose_protocol__(trigs, protocols, index=0)
        
        if len(protocols):
            src.annotations["trigger_protocol"] = protocols[0].name
                
    elif isinstance(src, (tuple, list) and all([isinstance(v, neo.Segment) for v in src])):
        trigs = [ (k, [e for e in s.events if isinstance(e, TriggerEvent)]) \
                        for k,s in enumerate(src) if len(s.events)]
        
        if len(trigs) == 0:
            return protocols, src
        
        for (index, events) in trigs:
            __compose_protocol__(events, protocols, index)
            
        if len(protocols):
            for p in protocols:
                for f in p.segmentIndices():
                    src[f].annotations["trigger_protocol"] = p.name
                
    else:
        raise TypeError("src expected to be a neo.Block, neo.Segment, or a sequence of neo.Segment objects; got %s instead" % type(src).__name__)
            
    return protocols, src

def auto_detect_trigger_protocols(data: neo.Block, 
                               presynaptic:tuple=(), 
                               postsynaptic:tuple=(),
                               photostimulation:tuple=(),
                               imaging:tuple=(),
                               clear:bool=False):
    
    """Determines the set of trigger protocols in a neo.Block by searching for 
    trigger waveforms in the analogsignals contained in data.
    
    Time stamps of the detected trigger protocols will then be used to construct
    TriggerEvent objects according to which of the keyword parameters below
    have been specified.
    
    Positional parameters:
    =====================
    
    data:   a neo.Block object
            
    Named parameters:
    =================
    
    presynaptic, postsynaptic, photostimulation, imaging:
    
        each is a tuple with 0 (default), two or three elements that specify 
        parameters for the detection of pre-, post-synaptic, photo-stimulation
        or imaging (trigger) event types, respectively.
        
        First element (int): the index of the analog signal in the electrophysiology 
            block segments, containing the trigger signal (usually a square pulse, 
            or a train of square pulses)
        
        Second element (str): a label to be assigned to the detected event
        
        Third (optional) element:  a tuple of two python Quantity objects defining
            a time slice within the signal, used for the detection of the events.
            
            This is recommended in case the trigger signal contains other 
            waveforms in addition to the trigger waveform.
            In this case, the trigger waveform will be searched/analysed within
            the signal regions between these two time points (right-open interval).
            
        When empty, no events of the corresponding type will be constructed.
        
    clear: bool (default False)
        When False (default), detected event arrays will be appended.
        
        When True, old events will be cleared from data.electrophysiology
        
    Returns:
    =======
    A list of trigger protocols
        
    """
    if not isinstance(data, neo.Block):
        raise TypeError("Expecting a neo.Block; got %s instead" % type(data).__name__)
    
    
    if not isinstance(clear, bool):
        raise TypeError("clear parameter expected to be a boolean; got %s instead" % type(clear).__name__)
        
    target = data
    #print("auto_detect_trigger_protocols: presynaptic", presynaptic)
    #print("auto_detect_trigger_protocols: postsynaptic", postsynaptic)
    #print("auto_detect_trigger_protocols: photostimulation", photostimulation)
    #print("auto_detect_trigger_protocols: imaging", imaging)
        
    if clear:
        clear_events(target)
    
    # NOTE: 2019-03-14 21:43:21
    # depending on the length of the keword parameters (see the docstring)
    # we detect events in the whole signal or we limit detetion to a defined 
    # time-slice of the signal
    
    if len(presynaptic) == 2:
        auto_define_trigger_events(target, presynaptic[0], "presynaptic", label=presynaptic[1])
        
    elif len(presynaptic) == 3:
        auto_define_trigger_events(target, presynaptic[0], "presynaptic", label=presynaptic[1], time_slice = presynaptic[2])
        
    if len(postsynaptic) == 2:
        auto_define_trigger_events(target, postsynaptic[0], "postsynaptic", label = postsynaptic[1])
        
    elif len(postsynaptic) == 3:
        auto_define_trigger_events(target, postsynaptic[0], "postsynaptic", label = postsynaptic[1], time_slice = postsynaptic[2])
        
    if len(photostimulation) == 2:
        auto_define_trigger_events(target, photostimulation[0], "photostimulation", label=photostimulation[1])
        
    elif len(photostimulation) == 3:
        auto_define_trigger_events(target, photostimulation[0], "photostimulation", label=photostimulation[1], time_slice = photostimulation[2])
        
    if len(imaging) == 2:
        auto_define_trigger_events(target, imaging[0], "frame", label = imaging[1])
        
    elif len(imaging) == 3:
        auto_define_trigger_events(target, imaging[0], "frame", label = imaging[1], time_slice = imaging[2])
        
    tp, _ = parse_trigger_protocols(target)
    
    return tp

        

@safeWrapper
def auto_define_trigger_events(src, analog_index, event_type, 
                               times=None, label=None, name=None, 
                               use_lo_hi=True, time_slice=None, 
                               clearSimilarEvents=True, clearTriggerEvents=True, 
                               clearAllEvents=False):
    """Populates the events lists for the segments in src with TriggerEvent objects.
    
    Searches for trigger waveforms in signals specified by analog_index, to define
    TriggerEvent objects.
    
    A TriggerEvent is an array of time values and will be added to the events list
    of the neo.Segment objects in src.
    
    Calls detect_trigger_events()
    
    Parameters:
    ===========
    
    src: a neo.Block, a neo.Segment, or a list of neo.Segment objects
    
    analog_index:   specified which signal to use for event detection; can be one of:
    
                    int (index of the signal array in the data analogsignals)
                        assumes that _ALL_ segments in "src" have the desired analogsignal
                        at the same position in the analogsignals array
    
                    str (name of the analogsignal to use for detection) -- must
                        resolve to a valid analogsignal index in _ALL_ segments in 
                        "src"
                    
                    a sequence of int (index of the signal), one per segment in src 

    event_type: a str that specifies the type of trigger event e.g.:
                'acquisition',
                'frame'
                'imaging',
                'imaging_frame',
                'imaging_line',
                'line'
                'photostimulation',
                'postsynaptic',
                'presynaptic',
                'sweep',
                'user'
                
            or a valid datatypes.TriggerEventType enum type, e.g. TriggerEventType.presynaptic
    
    (see detect_trigger_events(), datatypes.TriggerEventType)
    
    Named parameters:
    =================
    times: either None, or a python quantity array with time units
    
        When "times" is None (the default) the function calls detect_trigger_events() 
        on the analogsignal specified by analog_index in src, to detect trigger 
        events. The specified analogsignal must therefore contain trigger waveforms 
        (typically, rectangular pulses).
        
        Otherwise, the values in the "times" array will be used to define the 
        trigger events.
        
    label: common prefix for the individual trigger event label in the event array
            (see also detect_trigger_events())
    
    name: name for the trigger event array 
            (see also detect_trigger_events())
    
    use_lo_hi: boolean, (default is True);  
        when True, use the rising transition to detect the event time 
            (see also detect_trigger_events())
        
    time_slice: pq.Quantity tuple (t_start, t_stop) or None.
        When detecting events (see below) the time_slice can specify which part of  
        a signal can be used for automatic event detection.
        
        When time_slice is None this indicates that the events are to be detected 
        from the entire signal.
        
        The elements need to be Python Quantity objects compatible with the domain
        of the signal. For AnalogSignal, this is time (usually, pq.s)
        
    NOTE: The following parameters are passed directly to embed_trigger_event
    
    clearSimilarEvents: boolean, default is True: 
        When True, existing neo.Event objects with saame time stamps, labels,
            units and name as those of the parameter "event" will be removed. 
            In case of TriggerEvent objects the comparison also considers the 
            event type.
            
        NOTE: 2019-03-16 12:06:14
        When "event" is a TriggerEvent, this will clear ONLY the pre-exising
        TriggerEvent objects of the same type as "event" 
        (see datatypes.TriggerEventType for details)
        
    clearTriggerEvents: boolean, default is True
        when True, clear ALL existing TriggerEvent objects
        
        NOTE: 2019-03-16 12:06:07
        to clear ONLY existing TriggerEvent objects with the same type
            as the "event" (when "event" is also a TriggerEvent) 
            set clearSimilarEvents to True; see NOTE: 2019-03-16 12:06:14
    
    clearAllEvents: boolean, default is False:
        When True, clear ANY existing event in the segment.
        
    Returns:
    ========
    The src parameter (a reference)
    
    Side effects:
        Creates and appends TriggerEvent objects to the segments in src
    """
    if isinstance(src, neo.Block):
        data = src.segments
        
    elif isinstance(src, (tuple, list)) and all([isinstance(s, neo.Segment) for s in src]):
        data = src
        
    elif isinstance(src, neo.Segment):
        data = [src]
        
    else:
        raise TypeError("src expected to be a neo.Block, neo.Segment or a sequence of neo.Segment objects; got %s instead" % type(src).__name__)
    
    if isinstance(times, pq.Quantity):
        if not dt.check_time_units(times):  # event times passed at function call -- no detection is performed
            raise TypeError("times expected to have time units; it has %s instead" % times.units)

        for segment in data: # construct eventss, store them in segments
            event = TriggerEvent(times=times, units=times.units,
                                    event_type=event_type, labels=label, 
                                    name=name)
            
            embed_trigger_event(event, segment,
                                clearTriggerEvents = clearTriggerEvents,
                                clearSimilarEvents = clearSimilarEvents,
                                clearAllEvents = clearAllEvents)
            
    elif times is None: #  no event times specified =>
        # auto-detect trigger events from signal given by analog_index
        if isinstance(analog_index, str):
            # signal specified by name
            analog_index = get_index_of_named_signal(data, analog_index)
            
        if isinstance(analog_index, (tuple, list)):
            if all(isinstance(s, (int, str)) for s in analog_index):
                if len(analog_index) != len(data):
                    raise TypeError("When a list of int, analog_index must have as many elements as segments in src (%d); instead it has %d" % (len(data), len(analog_index)))
                
                for (s, ndx) in zip(data, analog_index):
                    if isinstance(ndx, str):
                        sndx = get_index_of_named_signal(s, ndx, silent=True)
                        
                    else:
                        sndx = ndx
                        
                    if sndx in range(len(s.analogsignals)):
                        if isinstance(time_slice, (tuple, list)) \
                            and all([isinstance(t, pq.Quantity) and dt.check_time_units(t) for t in time_slice]) \
                                and len(time_slice) == 2:
                            event = detect_trigger_events(s.analogsignals[sndx].time_slice(time_slice[0], time_slice[1]), 
                                                        event_type=event_type, 
                                                        use_lo_hi=use_lo_hi, 
                                                        label=label, name=name)
                            
                        else:
                            event = detect_trigger_events(s.analogsignals[sndx], 
                                                        event_type=event_type, 
                                                        use_lo_hi=use_lo_hi, 
                                                        label=label, name=name)
                            
                        embed_trigger_event(event, s, 
                                            clearTriggerEvents = clearTriggerEvents,
                                            clearSimilarEvents = clearSimilarEvents,
                                            clearAllEvents = clearAllEvents)
                        
                    else:
                        raise ValueError("Invalid signal index %d for a segment with %d analogsignals" % (ndx, len(s.analogsignals)))

        elif isinstance(analog_index, int):
            for s in data:
                if analog_index in range(len(s.analogsignals)):
                    if isinstance(time_slice, (tuple, list)) \
                        and all([isinstance(t, pq.Quantity) and dt.check_time_units(t) for t in time_slice]) \
                            and len(time_slice) == 2:
                        event = detect_trigger_events(s.analogsignals[analog_index].time_slice(time_slice[0], time_slice[1]), 
                                                      event_type=event_type, 
                                                      use_lo_hi=use_lo_hi, 
                                                      label=label, name=name)
                        
                    else:
                        event = detect_trigger_events(s.analogsignals[analog_index], 
                                                      event_type=event_type, 
                                                      use_lo_hi=use_lo_hi, 
                                                      label=label, name=name)
                        
                    embed_trigger_event(event, s, 
                                        clearTriggerEvents = clearTriggerEvents,
                                        clearSimilarEvents = clearSimilarEvents,
                                        clearAllEvents = clearAllEvents)
                    
                else:
                    raise ValueError("Invalid signal index %d for a segment with %d analogsignals" % (analog_index, len(s.analogsignals)))
                
        else:
            raise RuntimeError("Invalid signal index %s" % str(analog_index))

    else:
        raise TypeError("times expected to be a python Quantity array with time units, or None")
                
                
    return src
