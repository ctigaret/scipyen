from copy import deepcopy, copy

import numpy as np
import quantities as pq

from neo.core.baseneo import BaseNeo, merge_annotations
from neo.core.dataobject import DataObject, ArrayDict

from core import quantities as cq

def _newDataZone(cls, places=None, extents=None, labels=None, units=None,
             name=None, segment=None, description=None, file_origin=None,
             array_annotations=None, annotations=None):
    
    obj = DataZone(places=places, extents=extents, labels=labels,
                   units=units,name=name,file_origin=file_origin,
                   description=description,array_annotations=array_annotations,
                   **annotations)
    
    
class DataZone(DataObject):
    """neo.Epoch-like for DataSignals
    
    The name 'DataZone' was chosen to avoid possible confusions arising from
    using 'region' in the name (which may imply higher dimensions of the data
    space, as in 'region of interest' or 'volume of interest').
    
    The data domain is not restricted to time or space (as the latter might also
    be implied from using 'region')
    
    """
    _parent_objects = ('Segment',)
    _parent_attrs = ('segment',)
    _quantity_attr = ('places', 'times')
    _necessary_attrs = (('places', pq.Quantity, 1),
                        ('times', pq.Quantity, 1), 
                        ('extents', pq.Quantity, 1),
                        ('durations', pq.Quantity, 1),
                        ('labels', np.ndarray, 1, np.dtype('U')))

    def __new__(cls, places=None, times=None, extents=None, durations=None,
                labels=None, units=None, name=None, 
                description=None, file_origin=None, segment=None,
                array_annotations=None, **annotations):
        if places is None:
            if times is None:
                places = np.array([])
            elif isinstance(times, (tuple, list)):
                places = np.array(times)
            elif isinstance(times, pq.Quantity):
                places = times
                
        elif instance(places, (tuple, list)):
            places = np.array(places)
            
        elif not isinstance(places, pq.Quantity):
            places = np.array([])
            
        if extents is None:
            if durations is None:
                extents = np.array([])
            elif isinstance(durations, (tuple, list)):
                extents = np.array(durations)
            elif isinstance(durations, pq.Quantity):
                extents = durations
                
        elif isinstance(places, (tuple, list)):
            places = np.array(places)
            
        elif not isinstance(places, pq.Quantity):
            places = np.array([])
            
        if extents.size != places.size:
            if extents.size == 1:
                extents = extents* np.ones_like(places)
                
            else:
                raise ValueError("Extents and places have different lengths")
            
        if not isinstance(units, pq.Quantity):
            if isinstance(places, pq.Quantity):
                units = places.units
            else:
                raise ValueError("Units must be specified")
        else:
            if not isinstance(places, pq.Quantity):
                places = places * units
                
            else:
                if not cq.units_convertible(places, units):
                    units = places.units
            
            if isinstance(extents, pq.Quantity):
                if not cq.units_convertible(places, extents):
                    raise TypeError(f"Extents dimensionality {extents.dimensionality.string} is incompatible with {places.dimensionality.string}")
            else:
                extents = extents * places.units
                
        if labels is None:
            labels = np.array([], dtype='U')
        else:
            labels = np.array(labels)
            if labels.size != places.size and labels.size:
                raise ValueError("Labels array has different length to times")
            
        obj = pq.Quantity.__new__(cls, times, units = places.dimensionality)
        
        obj._labels = labels
        obj._extents = extents
        obj.segment = segment
        return obj
    
    def __init__(self, place=None, times=None, extents=None, durations=None,
                 labels=None, units=None, name=None, description=None,
                 file_origin=None, array_annotations=None, **annotations):
        DataObject.__init__(self, name=name, file_origin=file_origin,
                            description=description, 
                            array_annotations=array_annotations, **annotations)
                
            
            
    def __reduce__(self):
        return _newDataZone, (self.__class__, self.places, self.extents,
                              self.labels, self.units, self.name, self.segment,
                              self.description, self.file_origin, 
                              self.array_annotations, self.annotations)
        
    def __array_finalize__(self, obj):
        super().__array_finalize__(obj)
        self._extents = getattr(obj, "extents", getattr(obj, "durations", None))
        self._labels = getattr(obj, "labels", None)
        self.annotations = getattr(obj, "annotations", None)
        self.name = getattr(obj, "name", None)
        self.file_origin = getattr(obj, "file_origin", None)
        self.description = getattr(obj, "description", None)
        self.segment = getattr(obj, "segment", None)
        
        if not hasattr(self, "array_annotations"):
            self.array_annotations = ArrayDict(self._get_arr_ann_length())
            
    def __repr__(self):
        objs = ['%s@%s for %s' % (label, str(time), str(dur)) for label, time, dur in
                zip(self.labels, self.times, self.durations)]
        return f"<{self.__class___.__name__}:{', '.join(objs)}>"

    def _repr_pretty_(self, pp, cycle):
        super()._repr_pretty_(pp, cycle)

    def rescale(self, units):
        '''
        Return a copy converted to the specified units
        :return: Copy of self with specified units
        '''
        # Use simpler functionality, if nothing will be changed
        dim = pq.quantity.validate_dimensionality(units)
        if self.dimensionality == dim:
            return self.copy()

        # Rescale the object into a new object
        obj = self.duplicate_with_new_data(
            places=self.view(pq.Quantity).rescale(dim),
            durations=self.durations.rescale(dim),
            labels=self.labels,
            units=units)

        # Expected behavior is deepcopy, so deepcopying array_annotations
        obj.array_annotations = deepcopy(self.array_annotations)
        obj.segment = self.segment
        return obj
      
        
    def __getitem__(self, i):
        '''
        Get the item or slice :attr:`i`.
        '''
        obj = super().__getitem__(i)
        obj._durations = self.durations[i]
        if self._labels is not None and self._labels.size > 0:
            obj._labels = self.labels[i]
        else:
            obj._labels = self.labels
        try:
            # Array annotations need to be sliced accordingly
            obj.array_annotate(**deepcopy(self.array_annotations_at_index(i)))
            obj._copy_data_complement(self)
        except AttributeError:  # If Quantity was returned, not Epoch
            obj.times = obj
            obj.durations = obj._durations
            obj.labels = obj._labels
        return obj

    def __getslice__(self, i, j):
        '''
        Get a slice from :attr:`i` to :attr:`j`.attr[0]

        Doesn't get called in Python 3, :meth:`__getitem__` is called instead
        '''
        return self.__getitem__(slice(i, j))

    def merge(self, other):
        '''
        Merge the another :class:`Epoch` into this one.

        The :class:`Epoch` objects are concatenated horizontally
        (column-wise), :func:`np.hstack`).

        If the attributes of the two :class:`Epoch` are not
        compatible, and Exception is raised.
        '''
        othertimes = other.times.rescale(self.times.units)
        otherdurations = other.durations.rescale(self.durations.units)
        times = np.hstack([self.times, othertimes]) * self.times.units
        durations = np.hstack([self.durations,
                               otherdurations]) * self.durations.units
        labels = np.hstack([self.labels, other.labels])
        kwargs = {}
        for name in ("name", "description", "file_origin"):
            attr_self = getattr(self, name)
            attr_other = getattr(other, name)
            if attr_self == attr_other:
                kwargs[name] = attr_self
            else:
                kwargs[name] = "merge({}, {})".format(attr_self, attr_other)

        merged_annotations = merge_annotations(self.annotations, other.annotations)
        kwargs.update(merged_annotations)

        kwargs['array_annotations'] = self._merge_array_annotations(other)

        return DataZone(times=times, durations=durations, labels=labels, **kwargs)

    def _copy_data_complement(self, other):
        '''
        Copy the metadata from another :class:`Epoch`.
        Note: Array annotations can not be copied here because length of data can change
        '''
        # Note: Array annotations cannot be copied because length of data could be changed
        # here which would cause inconsistencies. This is instead done locally.
        for attr in ("name", "file_origin", "description"):
            setattr(self, attr, deepcopy(getattr(other, attr, None)))
        self._copy_annotations(other)

    def _copy_annotations(self, other):
        self.annotations = deepcopy(other.annotations)

    def duplicate_with_new_data(self, times, durations, labels, units=None):
        '''
        Create a new :class:`Epoch` with the same metadata
        but different data (times, durations)

        Note: Array annotations can not be copied here because length of data can change
        '''

        if units is None:
            units = self.units
        else:
            units = pq.quantity.validate_dimensionality(units)

        new = self.__class__(places=times, extents=durations, labels=labels, units=units)
        new._copy_data_complement(self)
        new._labels = labels
        new._extents = durations
        # Note: Array annotations can not be copied here because length of data can change
        return new

    def zone_slice(self, begin, end):
        '''
        Creates a new :class:`Epoch` corresponding to the time slice of
        the original :class:`Epoch` between (and including) times
        :attr:`t_start` and :attr:`t_stop`. Either parameter can also be None
        to use infinite endpoints for the time interval.
        '''
        _t_start = begin
        _t_stop = end
        if _t_start is None:
            _t_start = -np.inf
        if _t_stop is None:
            _t_stop = np.inf

        indices = (self >= _t_start) & (self <= _t_stop)

        # Time slicing should create a deep copy of the object
        new_epc = deepcopy(self[indices])

        return new_epc
    
    def time_slice(self, t_start, t_stop):
        return self.zone_slice(t_start, t_stop)
        
    def shift(self, shift):
        """
        Shifts by a given amount.

        Parameters:
        -----------
        shift: Quantity
            Amount by which to shift.

        Returns:
        --------
            New instance object starting at 'shift' later than the
            original (the original is not modified).
        """
        new_epc = self.duplicate_with_new_data(times=self.times + t_shift,
                                               durations=self.durations,
                                               labels=self.labels)

        # Here we can safely copy the array annotations since we know that
        # the length of the Epoch does not change.
        new_epc.array_annotate(**self.array_annotations)

        return new_epc
    
    def time_shift(self, t_shift):
        """
        Shifts by a given amount.

        Parameters:
        -----------
        t_shift: Quantity (time)
            Amount of time by which to shift the :class:`Epoch`.

        Returns:
        --------
        epoch: :class:`Epoch`
            New instance of an :class:`Epoch` object starting at t_shift later than the
            original :class:`Epoch` (the original :class:`Epoch` is not modified).
        """
        return self.shift(t_shift)

    @property
    def places(self):
        return pq.Quantity(self)

    @property
    def times(self):
        """Alias to self.places for API compatibility with neo.Epoch
        """
        return self.places
    
    @property
    def extents(self):
        return self._extents
    
    @extents.setter
    def extents(self, extents):
        if extents is not None and self.extents.size > 0 and len(extents) != self.extents.size:
            raise ValueError(f"Argument has wrong size {len(extents)}; expecting {self.extents.size}")
        
    @property
    def durations(self):
        return self.extents
    
    @durations.setter
    def durations(self, val):
        self.extents = val
        
    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels):
        if self.labels is not None and self.labels.size > 0 and len(labels) != self.size:
            raise ValueError("Labels array has different length to times ({} != {})"
                             .format(len(labels), self.size))
        self._labels = np.array(labels)
