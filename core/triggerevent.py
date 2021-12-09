# -*- coding: utf-8 -*-
"""TriggerEvent class

Changelog:
2021-01-06 14:34:02 tolerances and equal_nan moved to datatypes module, 
    as module contants

"""
import warnings
from enum import IntEnum
from numbers import (Number, Real,)
from copy import (deepcopy, copy,)
from itertools import chain
import numpy as np
import quantities as pq
import neo
from neo.core.dataobject import (DataObject, ArrayDict,)
from core.datatypes import (is_string, TypeEnum,
                            RELATIVE_TOLERANCE, ABSOLUTE_TOLERANCE, EQUAL_NAN,)
from core.quantities import check_time_units
#from core.utilities import unique

def _new_DataMark(cls, places = None, labels=None, units=None, name=None, 
                  file_origin=None, description=None, mark_type=None,
                  segment=None, array_annotations=None, annotations={}):
    if not isinstance(annotations, dict):
        if annotations is None:
            annotations = dict()
        else:
            try:
                annotations = dict(annotations)
            except:
                annotations = dict() # just so that we aren't left hanging out
                
    e = cls(places=places, labels=labels, units=units, name=name, 
            mark_type=mark_type, file_origin=file_origin, 
            description=description, array_annotations=array_annotations,
            **annotations)
    
    e.segment=segment
    
    return e

def _new_TriggerEvent(cls, times = None, labels=None, units=None, name=None, 
               file_origin=None, description=None, event_type=None,
               segment=None, array_annotations=None, annotations={}):
    """Keep for old pickles
    """
    if not isinstance(annotations, dict):
        if annotations is None:
            annotations = dict()
        else:
            try:
                annotations = dict(annotations)
            except:
                annotations = dict() # just so that we aren't left hanging out
                
    e = TriggerEvent(times=times, labels=labels, units=units,name=name,
                      file_origin=file_origin, description=description, 
                      event_type=event_type, array_annotations=array_annotations,
                      **annotations)
    
    e.segment=segment
    
    return e
    
class MarkType(TypeEnum):
    """Some standard data mark types
    """
    up      =  1 # step up
    down    =  2 # step down
    edge    =  4
    angle   =  8
    trough  = 16
    peak    = 32
    user    = 64
    place   = up | down | edge | angle | trough | peak | user
    
    

class TriggerEventType(TypeEnum):
    """Convenience enum type for trigger event types.
    
    Inherits introspection methods from dataypes.TypeEnum.
    
    Types are defined as follows:
    =============================
    
    Primitive types:
    -----------------
    presynaptic         =  1 # synaptic stimulus (e.g. delivered via TTL to stim box)
    postsynaptic        =  2 # typically a squre pulse of current injection e.g. at the soma, to elicit APs
    photostimulation    =  4 # typically an uncaging event (generally a TTL which opens a soft or hard shutter for a stimulation laser, or a laser diode)
    imaging_frame       =  8 # TTL that triggers the acquisition of an image frame
    imaging_line        = 16 # TTL trigger for a scanning line of the imaging system
    sweep               = 32 # "external" trigger for electrophysiology acquisition
    user                = 64 # anything else
    
    frame               = imaging_frame (*)
    line                = imaging_line (*)
    
    Composite (or derived) types:
    -----------------------------
    synaptic            = presynaptic | postsynaptic  = 3
    stimulus            = presynaptic | postsynaptic | photostimulation = 7
    imaging             = imaging_frame | imaging_line = 24
    acquisition         = imaging | sweep = 56
    
    (*) this is just an alias
    
    """
    presynaptic         =  1 # synaptic stimulus (e.g. delivered via TTL to stim box)
    postsynaptic        =  2 # typically a squre pulse of current injection e.g. at the soma, to elicit APs
    synaptic            = presynaptic | postsynaptic # 3
    photostimulation    =  4 # typically an uncaging event (generally a TTL which opens a soft or hard shutter for a stimulation laser, or a laser diode)
    stimulus            = presynaptic | postsynaptic | photostimulation # 7
    imaging_frame       =  8 # TTL that triggers the acquisition of an image frame
    imaging_line        = 16 # TTL trigger for a scanning line of the imaging system
    sweep               = 32 # "external" trigger for electrophysiology acquisition
    user                = 64 # anything else
    frame               = imaging_frame                 #  8
    line                = imaging_line                  # 16
    imaging             = imaging_frame | imaging_line  # 24
    acquisition         = imaging | sweep               # 56
    
class DataMark(DataObject):
    """Similar to neo.Event but suitable to all domains, not just time
    """
    _single_parent_objects = ('Segment',)
    _single_parent_attrs = ('segment',)
    _quantity_attr = ('places', 'times',)
    _necessary_attrs = (('places', pq.Quantity, 1), 
                        ('times', pq.Quantity, 1),
                        ('labels', np.ndarray, 1, np.dtype('U')))
    
    _parent_attrs = ("segment", )

    #@staticmethod
    @classmethod
    def parseValues(cls, value, units=None):
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
            if isinstance(value, DataMark):
                if cls is TriggerEvent:
                    if not isinstance(value, TriggerEvent):
                        raise TypeError(f"Expecting a TriggerEvent for this {cls.__name__} object; got {type(value).__name__} instead")
                units = value.units
                
            else:
                units = pq.arbitrary_unit
            
        elif not isinstance(units, pq.Quantity):
            raise TypeError("units expected to be a Python Quantity; got %s instead" % type(units).__name__)
        
            units = units.units
        
        if not check_time_units(units):
            raise TypeError("expecting a time unit; got %s instead" % units)
            
        if isinstance(value, (tuple, list)):
            # value is a sequence of...
            if all([isinstance(v, Number) for v in value]): # plain numbers
                times = np.array(value) * units
                
            #elif all([isinstance(v, pq.Quantity) and check_time_units(v) for v in value]): # python quantities
            elif all([isinstance(v, pq.Quantity) for v in value]): # python quantities
                if cls is TriggerEvent:
                    if not all(check_time_units(v) for v in value):
                        raise TypeError(f"Expecting time units for a {cls.__name__} object")
                    
                if any([v.ndim > 0 for v in value]):
                    # in case the values in the sequence are dimensioned arrays
                    # but reject if any has ndim > 1 (enforce time stamps to be
                    # row vectors)
                    if any([v.ndim > 1 for v in value]):
                        raise TypeError("Cannot accept places as python quantity arrays with more than one dimension")
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
                    times = np.hstack(times_list) * units
                    
                else:
                    raise ValueError("cannot convert %s to time stamps" % value)
                
            else:
                raise TypeError("When a sequence, the value must contain elements of the same type, either number scalars or python quantities with time units")
                    
        elif isinstance(value, Number):
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
            
        elif isinstance(value, cls):
            times = value.times
            
        else:
            raise TypeError("value expected to be a numeric scalar, python quantity with time units, a numpy array, a sequence of these, or a TriggerEvent; got %s instead" % type(value).__name__)
            
        return times

    def __new__(cls, places=None, times=None, labels=None, units=None, name=None, 
                description=None, file_origin=None, mark_type=None, event_type=None, 
                array_annotations=None, **annotations):
        
        if places is None:
            if times is None:
                places = np.array([])
                
            elif isinstance(times, (list, tuple)):
                places = np.array(times)
                
            elif isinstance(places, np.ndarray):
                places = np.array(times)
                
            elif isinstance(times, (neo.Event, DataMark)):
                # for copy c'tor
                evt = times
                units = evt.units
                places = evt.times.flatten() * units
                labels = evt.labels
                name = evt.name
                description = evt.description
                file_origin = evt.file_origin
                annotations = evt.annotations
                
        elif isinstance(places, (list, tuple)):
            places = np.array(places)
            
        elif isinstance(places, np.ndarray):
            places = np.array(places)
            
        elif isinstance(places, (neo.Event, DataMark)):
            evt = times
            units = evt.units
            places = evt.times.flatten() * units
            labels = evt.labels
            name = evt.name
            description = evt.description
            file_origin = evt.file_origin
            annotations = evt.annotations
            
        if not isinstance(units, pq.Quantity):
            if isinstance(places, pq.Quantity):
                units = places.units
            else:
                if cls is TriggerEvent:
                    units = pq.s
                else:
                    units = pq.arbitrary_unit
                    
        if not isinstance(places, pq.Quantity):
            places = places * units
            
        times = places
            
        if labels is None:
            labels = np.array([], dtype='S')
            
        else:
            if isinstance(labels, str):
                labels = np.array([labels] * times.size)
                
            elif isinstance(labels, (tuple, list)):
                if not all([isinstance(l, str) for l in labels]):
                    raise TypeError("When ''labels' is a sequence, all elements must be str")
                
                if len(labels) < times.size:
                    labels += [labels[-1]] * (times.size - len(labels))
                    
                elif len(labels) > times.size:
                    labels = labels[:times.size]
                    
                labels = np.array(labels)
                
            elif isinstance(labels, np.ndarray):
                if not is_string(labels):
                    raise TypeError("When 'labels' is a numpy array, it must contain strings")
                
                if labels.size < times.size:
                    labels = np.append(labels, [labels[-1]] * (times.size - labels-size))
                elif labels.size > times.size:
                    labels = labels[:times.size]
                    
            else:
                raise TypeError("'labels' must be either a str, a sequence of str or a numpy array of strings; got %s instead" % type(labels).__name__)
                    
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
                
        if mark_type is None:
            if isinstance(event_type, (int, TriggerEventType)):
                mark_type = event_type
                
        # NOTE: 2021-11-11 09:39:49
        # ONLY for TriggerEvent
        # check to make sure the units are time
        # this approach is much faster than comparing the
        # reference dimensionality
        if cls.__name__ == "TriggerEvent":
            if (len(dim) != 1 or list(dim.values())[0] != 1 or not isinstance(list(dim.keys())[0],
                                                                            pq.UnitTime)):
                ValueError("Unit {} has dimensions {}, not [time]".format(units, dim.simplified))

        ##if not isinstance(annotations, dict):
            ##annotations = dict()
            
        obj = pq.Quantity(places, units=dim).view(cls)
        obj._labels = labels
        obj.segment = None
        return obj

    
    def __init__(self, places=None, times=None, labels=None, units=None, 
                 name=None, description=None,file_origin=None, 
                 mark_type=None, event_type=None, 
                 array_annotations=None, **annotations):
        """Constructs a DataMark.
        
        For DataMark objects, event_type is by default MarkType.place
        
        For TriggerEvent objects, the default values of 'event_type' is 
        TriggerEventType.presynaptic.
        """
        DataObject.__init__(self, name=name, file_origin=file_origin, description=description,
                            array_annotations=array_annotations, **annotations)

        if not isinstance(annotations, dict):
            annotations = dict()
        
        self.annotations = annotations
        
        # NOTE: see NOTE: 2021-11-11 09:39:49
        
        if self.__class__.__name__ == "TriggerEvent":
            if event_type is None:
                self.__mark_type__ = TriggerEventType.presynaptic
                
            elif isinstance(event_type, str):
                if event_type in TriggerEventType.__members__:
                    self.__mark_type__ = TriggerEventType[event_type]
                    
                else:
                    warngins.warning("Unknown event type %s; event_type will be set to %s " % (event_type, TriggerEventType.presynaptic))
                    self.__mark_type__ = TriggerEventType.presynaptic
            
            elif isinstance(event_type, TriggerEventType):
                self.__mark_type__ = event_type
                
            else:
                warngins.warn("'event_type' parameter expected to be a TriggerEventType enum value, a TriggerEventType name, or None; got %s instead" % type(event_type).__name__)
                self.__mark_type__ = TriggerEventType.presynaptic
                
        else:
            self.__mark_type__ = MarkType.place
            
        self.setLabel(labels)
        
        if isinstance(name, str) and len(name.strip()):
            self._name_ = name
                
        else:
            if self.__class__.__name__ == "TriggerEvent":
                self._name_ = self.event_type.name
            else:
                self._name_ = "DataMark"

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
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
        super(DataMark, self).__array_finalize__(obj)
        self.__mark_type__ = getattr(obj, "__mark_type__", MarkType.place)
        
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
        if self.__class__.__name__ == "TriggerEvent":
            tail = f"({self.event_type.name}): {self.name}, {', '.join(objs)}"
        else:
            tail = f": {self.name}, {', '.join(objs)}"
            
        result = f"{self.__class__.__name__} {tail}"
        
        return result
    
    def __reduce__(self):
        if not isinstance(self.annotations, dict):
            annots = {}
            
        else:
            annots = self.annotations
        
        if not hasattr(self, 'array_annotations'):
            self.array_annotations = ArrayDict(self._get_arr_ann_length())

        new_fn = eval(f"_new_{self.__class__.__name__}")

        return _new_DataMark, (self.__class__, self.times, self.labels, 
                               self.units, self.name, self.__mark_type__, 
                               self.file_origin, self.description,
                               self.segment, self.array_annotations, annots)
    
    def set_labels(self, labels):
        if self.labels is not None and self.labels.size > 0 and len(labels) != self.size:
            raise ValueError("Labels array has different length to places ({} != {})"
                            .format(len(labels), self.size))
        self._labels = np.array(labels)

    def get_labels(self):
        return self._labels

    def merge(self, other):
        """Merge this event with the time stamps from other event
        Both events must have the same type.
        
        Returns:
        ========
        
        A new TriggerEvent with the same type as self
        
        NOTE the new time stamps are stored in sorted order, by value!
        
        """
        if isinstance(self, TriggerEvent):
            if other.__event_type__ != self.__mark_type__:
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
                
        if isinstance(self, TriggerEvent):
            kwargs["event_type"] = self.__mark_type__

        merged_annotations = self.annotations.copy()
        
        merged_annotations.update(other.annotations)
        
        kwargs['array_annotations'] = self._merge_array_annotations(other)

        kwargs.update(merged_annotations)
        
        return self.__class__(times=times, labels=new_labels, **kwargs)
        #return TriggerEvent(times=times, labels=new_labels, **kwargs)
    
    def rescale(self, units):
        '''
        Return a copy converted to the specified units
        '''
        obj = super(self.__class__, self).rescale(units)
        obj.segment = self.segment
        return obj

    def setLabel(self, value):
        #print("setLabel: event_type", self.__mark_type__)
        if isinstance(value, str):
            setattr(self, "_labels", np.array([value] * self.times.size))
            
        elif isinstance(value, (tuple, list)) and all([isinstance(l, str) for l in value]):
            if len(value) == self.times.flatten().size:
                setattr(self, "_labels", np.array(value))
                
            else:
                raise ValueError("When given as a list, value must have as many elements as times (%d); got %d instead" % (self.times.flatten().size, len(value)))

        elif isinstance(value, np.ndarray) and is_string(value):
            if value.flatten().size == 0:
                if isinstance(self, TriggerEvent):
                    setattr(self, "_labels", np.array([TriggerEvent.defaultLabel(self.__mark_type__)] * self.times.size))
                else:
                    setattr(self, "_labels", np.array(["DataMark"] * self.times.size))
                    
            elif value.flatten().size != self.times.flatten().size:
                setattr(self, "_labels", np.array([value.flatten()[0]] * self.times.size))
                
            else:
                setattr(self, "_labels", value)
                
        elif value is None:
            if isinstance(self, TriggerEvent):
                def_label = TriggerEvent.defaultLabel(self.__mark_type__)
            else:
                def_label = "DataMark"
            #print("setLabel: def_label", def_label)
            if isinstance(self, TriggerEvent):
                setattr(self, "_labels", np.full_like(self.times.magnitude, TriggerEvent.defaultLabel(self.__mark_type__), dtype=np.dtype(str)))
            else:
                setattr(self, "_labels", np.full_like(self.times.magnitude, "DataMark", dtype=np.dtype(str)))
                    
    def setLabels(self, value):
        self.setLabel(value)
        
    def shift(self, value, copy=False):
        """Adds value to the places attribute (shifting).
        
        Value must be a pq.Quantity with the same units as the times attribute,
        or a scalar
        """
        if copy:
            ret = self.copy()
            
        else:
            ret = self
            
        if isinstance(value, Real):
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
            if isinstance(self, TriggerEvent):
                if (len(dim) != 1 or list(dim.values())[0] != 1 or
                        not isinstance(list(dim.keys())[0], pq.UnitTime)):
                    ValueError("value %s has dimensions %s, not [time]" %
                            (value, dim.simplified))

        else:
            raise TypeError("value was expected to be a scalar or a python Quantity with %s units; got %s insteads" % (self.time.units, value))

        ret += value
        
        return ret # for convenience so that we can chain this e.g. "return obj.copy().shift()"
        
    def place_shift(self, t_shift):
        """
        Shifts places by given amount.

        Parameters:
        -----------
        t_shift: Quantity
            Amount of time by which to shift the :class:`Event`.

        Returns:
        --------
        New instance of an this object :class: starting at t_shift later than the
        original. The original is left unchanged.
        """
        new_evt = self.duplicate_with_new_data(times=self.times + t_shift,
                                               labels=self.labels)

        # Here we can safely copy the array annotations since we know that
        # the length of the Event does not change.
        new_evt.array_annotate(**self.array_annotations)

        return new_evt
    
    def time_shift(self, t_shift):
        """Delegates to place_shift.
        for API compatibility with neo.Event
        """
        return self.place_shift(t_shift)

    def __getitem__(self, i):
        obj = super(self.__class__, self).__getitem__(i)
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
            
        if isinstance(self, TriggerEvent):
            setattr(self, "__event_type__", getattr(other, "__event_type__", TriggerEventType.presynaptic))
        
    def duplicate_with_new_data(self, times, labels=None, units=None):
        '''
        Create a new object with the same metadata but different data
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

    def append_marks(self, value):
        """Appends more marks
        
        Parameters:
        ==========
        value: See DataMark.parseValues
        
        Returns:
        =======
        A TriggerEvent with updated time stamps but with the same event type and 
        labels as self. 
        
        NOTE the new time stamps are stored in the given order and NOT sorted
        by value!
        
        In addition, the labels array is updated to have the same length as the 
        times attribute of the returned event object.
        """
        appended_times = self.__class__.parseValues(value, self.units)
        
        new_times = np.hstack((self.times, appended_times)) * self.units
        
        evt_type = self.__mark_type__
        
        new_labels = np.full_like(new_times.magnitude, self.labels[0], dtype=self.labels.dtype)
        
        name = self.name
        
        # take care of the other constructor parameters
        kwargs = {}

        for name in ("name", "description", "file_origin"):#, "__protocol__"):
            attr_self = getattr(self, name)
            
            kwargs[name] = getattr(self, name)
            
        kwargs["event_type"] = self.__mark_type__

        kwargs.update(self.annotations)

        return self.__class__(times = new_times, labels=new_labels, **kwargs)
    
    def region_slice(self, t_start, t_stop):
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
        
        new_obj = self.__class__(times=times, labels=labels, 
                                 units=self.units, name=self.name,
                                 description=self.description,
                                 file_origin=self.file_origin,
                                 array_annotations=self.array_annotations,
                                 **self.annotations)
        
        if isinstance(self, TriggerEvent):
            new_obj.event_type = self.event_type
        
        return new_obj
    
    def time_slice(self, t_start, t_stop):
        """Delegates to region_slice.
        For API compatibility with neo.Event
        """
        return self.region_slice(t_start, t-stop)
    
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
    
    def is_same_as(self, other, rtol = RELATIVE_TOLERANCE, atol =  ABSOLUTE_TOLERANCE, 
                   equal_nan = EQUAL_NAN):
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
        if not isinstance(other, self.__class__):
            raise TypeError(f"A {self.__class__.__name__} object was expected; got {type(other).__name__} instead")
        
        if isinstance(self, TriggerEvent):
            result = other.event_type == self.event_type
            
        else:
            result = True
        
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
            result &= other.flatten().size == self.flatten().size
            
        if result: 
            result &= np.all(np.isclose(other.magnitude, self.magnitude, 
                                        rtol=rtol, atol=atol, equal_nan=equal_nan))
        
        if result:
            result &= other.labels.size == self.labels.size
            
        if result:
            result &= np.all(other.labels.flatten() == self.labels.flatten())
            
        if result:
            result &= other.name == self.name
        
        return result
            
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

    labels = property(get_labels, set_labels)
    
    @property
    def places(self):
        return pq.Quantity(self)
    
    @property
    def times(self):
        return self.places
    
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
    def type(self):
        return self.__mark_type__
    
    @type.setter
    def type(self, value):
        if isinstance(self, TriggerEvent) and  not isinstance(value, TriggerEventType):
            raise TypeError("Expecting a TriggerEventType enum value; got %s instead" % type(value).__name__)
        
        elif not isinstance(value, MarkType):
            raise TypeError("Expecting a MarkType enum value; got %s instead" % type(value).__name__)
        
        self.__mark_type__ = value

    @property
    def mark_type(self):
        return self.type
    
    @mark_type.setter
    def mark_type(self, value):
        self.type = value
        

class TriggerEvent(DataMark):
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
    _necessary_attrs = (('times', pq.Quantity, 1), 
                        ('labels', np.ndarray, 1, np.dtype('S')), 
                        ("__event_type__", TriggerEventType, TriggerEventType.presynaptic))

    #relative_tolerance = 1e-4
    #absolute_tolerance = 1e-4
    #equal_nan = True
    
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
        
    parseTimeValues = DataMark.parseValues
    
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
            if isinstance(labels, str):
                labels = np.array([labels] * times.size)
            elif isinstance(labels, (tuple, list)):
                if not all([isinstance(l, str) for l in labels]):
                    raise TypeError("When ''labels' is a sequence, all elements must be str")
                
                if len(labels) < times.size:
                    labels += [labels[-1]] * (times.size - len(labels))
                    
                elif len(labels) > times.size:
                    labels = labels[:times.size]
                    
                labels = np.array(labels)
                
            elif isinstance(labels, np.ndarray):
                if not is_string(labels):
                    raise TypeError("When 'labels' is a numpy array, it must contain strings")
                
                if labels.size < times.size:
                    labels = np.append(labels, [labels[-1]] * (times.size - labels-size))
                elif labels.size > times.size:
                    labels = labels[:times.size]
                    
            else:
                raise TypeError("'labels' must be either a str, a sequence of str or a numpy array of strings; got %s instead" % type(labels).__name__)
                    
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

        obj = pq.Quantity(times, units=dim).view(cls)
        obj._labels = labels
        obj.segment = None
        return obj

    
    def __init__(self, times=None, labels=None, units=None, name=None, description=None,
                file_origin=None, event_type=None, array_annotations=None, **annotations):
        """Constructs a TriggerEvent.
        
        By default its __mark_type__ is TriggerEventType.presynaptic
        """
        super().__init__(times=times, labels=labels, units=units, description=description,
                         file_origin=file_origin, event_type=event_type,
                         array_annotations=array_annotations, **annotations)
        
    def __array_finalize__(self, obj):
        super(TriggerEvent, self).__array_finalize__(obj)
        #print("TriggerEvent.__array_finalize__", type(obj).__name__)
        #super().__array_finalize__(obj)
        
        self.__mark_type__ = getattr(obj, "__mark_type__", TriggerEventType.presynaptic)
        
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


    def append_times(self, value):
        """Appends time values to this event.
        
        Parameters:
        ==========
        value: See DataMark.parseValues
        
        Returns:
        =======
        A TriggerEvent with updated time stamps but with the same event type and 
        labels as self. 
        
        NOTE the new time stamps are stored in the given order and NOT sorted
        by value!
        
        In addition, the labels array is updated to have the same length as the 
        times attribute of the returned event object.
        """
        return self.append_marks(value) # inherited from DataMark

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

    @property
    def event_type(self):
        return self.type
    
    @event_type.setter
    def event_type(self, value):
        self.type = value
        
