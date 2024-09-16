# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import collections, numbers, typing, itertools
from copy import deepcopy, copy
from dataclasses import (dataclass, KW_ONLY, MISSING, field)

import numpy as np
import quantities as pq
import neo
from neo.core.baseneo import BaseNeo, merge_annotations
from neo.core.dataobject import DataObject, ArrayDict
import pyqtgraph as pg

from core import quantities as cq
from core.quantities import check_time_units
# from core.utilities import counter_suffix
from .prog import (safeWrapper, with_doc)
from qtpy import QtWidgets
# from PyQt5 import QtWidgets

def _newDataZone(cls, places=None, extents=None, labels=None, units=None,
             name=None, segment=None, description=None, file_origin=None,
             relative=None, array_annotations=None, annotations=None):
    
    if not isinstance(annotations, dict):
        if annotations is None:
            annotations = dict()
        else:
            try:
                annotations = dict(annotations)
            except:
                annotations = dict() # just so that we aren't left hanging out
        
    obj = DataZone(places=places, extents=extents, labels=labels,
                   units=units,name=name,file_origin=file_origin,
                   description=description,relative=relative,
                   array_annotations=array_annotations,
                   **annotations)
    

# class DataZone(DataObject):
class DataZone(neo.Epoch):
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
                        ('labels', np.ndarray, 1, np.dtype('U')),
                        ('relative', bool, 1, False))

    def __new__(cls, places=None, times=None, extents=None, durations=None, 
                labels=None, units=None, name=None, description=None, 
                file_origin=None, segment=None, relative=None,
                array_annotations=None, **annotations):
        """
        """
        if places is None:
            if times is None:
                places = np.array([])
            elif isinstance(times, (tuple, list)):
                places = np.array(times).flatten()
            elif isinstance(times, pq.Quantity):
                places = times.flatten()
                
        elif instance(places, (tuple, list)):
            places = np.array(places)
            
        elif not isinstance(places, (pq.Quantity, np.ndarray)):
            places = np.array([])
            
        else:
            places = places.flatten()
            
        if extents is None:
            if durations is None:
                extents = np.array([])
            elif isinstance(durations, (tuple, list)):
                extents = np.array(durations).flatten()
            elif isinstance(durations, pq.Quantity):
                extents = durations
                
        elif isinstance(extents, (tuple, list)):
            extents = np.array(extents)
            
        elif not isinstance(extents, (pq.Quantity, np.ndarray)):
            extents = np.array([])
            
        if extents.size != places.size:
            if extents.size == 1:
                extents = extents* np.ones_like(places)
                
            else:
                raise ValueError("Extents and places have different lengths")
            
        if not isinstance(units, pq.Quantity):
            if isinstance(places, pq.Quantity):
                units = places.units
                
            elif places is not None:
                units = pq.dimensionless
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
            
        if not isinstance(relative, bool):
            relative = False
            
        obj = pq.Quantity.__new__(cls, places, units = units.dimensionality)
        
        obj._labels = labels
        obj._extents = extents
        obj._relative = relative
        obj.segment = segment
        return obj
    
    def __init__(self, place=None, times=None, extents=None, durations=None,
                 labels=None, units=None, name=None, description=None,
                 file_origin=None, relative=None, array_annotations=None, **annotations):
        DataObject.__init__(self, name=name, file_origin=file_origin,
                            description=description, 
                            array_annotations=array_annotations, **annotations)
                
        self.__domain_name__ = cq.name_from_unit(self.places)
            
            
    def __reduce__(self):
        return _newDataZone, (self.__class__, self.places, self.extents,
                              self.labels, self.units, self.name, self.segment,
                              self.description, self.file_origin, self.relative,
                              self.array_annotations, self.annotations)
        
    def __array_finalize__(self, obj):
        super().__array_finalize__(obj)
        self._extents = getattr(obj, "extents", getattr(obj, "durations", None))
        self._labels = getattr(obj, "labels", None)
        self._relative = getattr(obj, "relative", False)
        self.annotations = getattr(obj, "annotations", None)
        self.name = getattr(obj, "name", None)
        self.file_origin = getattr(obj, "file_origin", None)
        self.description = getattr(obj, "description", None)
        self.segment = getattr(obj, "segment", None)
        self.__domain_name__ = cq.name_from_unit(self.units)
        
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
    
    def set_durations(self, durations):
        """For API compatibility with neo.Epoch
        """
        self.extents = durations
        
    def get_durations(self):
        return self.extents
    
    @property
    def relative(self) -> bool:
        """Indicates if the coordinates are relative to signal's domain origin.
        This is independent of the extents of the data zone.
        """
        return getattr(self, "_relative", False)
    
    @relative.setter
    def relative(self, val:bool):
        self._relative = val == True

    @property
    def domain_name(self):
        """A brief description of the domain name
        """
        if self.__domain_name__ is None:
            self.__domain_name__ = name_from_unit(self.domain)
            
        return self.__domain_name__
    
    @domain_name.setter
    def domain_name(self, value):
        if isinstance(value, str) and len(value.strip()):
            self.__domain_name__ = value
    
    @property
    def places(self):
        return pq.Quantity(self)

    @property
    def domain(self):
        """Alias to self.places for API compatibility with DataSignal
        """
        return self.places

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
        if extents is not None and self.places.size > 0 and len(extents) != self.extents.size:
            raise ValueError(f"Argument has wrong size {len(extents)}; expecting {self.places.size}")
        
        self._extents = extents
        
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

@dataclass
class Interval:
    """Encapsulates an interval of a signal in a Cartesian axis system.
This can be specified by two landmarks, or by a landmark and an extent
(or duration) - in this case is similar to a neo.Epoch or DataZone, except that
if specifies an unique interval.

This class is intended to be a light-weight, convergent common data type useful
for accessing a signal region (a.k.a "slice") encapsulated in a neo.Epoch, 
DataZone or SignalCursor.
        
Suppose you write a function to calculate a measure in a signal based on a cursor
or an epoch interval. Since a SignalCursor and a neo.Epoch are very different 
types, you may have to write two separate pieces of code for doing the same thing
i.e., to calculate something based on the signal values in the region defined by
        
    • the SignalCursor xwindow around its x coordinate
    • the Epoch's interval defined by its time and duration.
        
The separate pieces of code will differ in the way that the two parameters
('x' and 'xwindow', for a SignalCursor, or times[k] and durations[k], for 
the kᵗʰ interval in an Epoch) are used to determine the start and stop times
of the signal regions where the calculation is to be made.
        
An Interval object brings this to a common denominator, so that it can be used
directly instead of either a cursor or a Epoch's interval, although functions
using either types are available as well in the 'ephys.ephys' module in Scipyen.
        
An Interval it that it allows storing Epoch intervals SEPARATELY, instead of 
storing the entire Epoch when that is not desired (one could extract one
interval from an Epoch and use it to construct another Epoch to be stored; 
however, the first part of this exercise is already done bny constructing an #
Interval).
        
Another use of Interval is to store SignalCursor coordinates to files; since a
SignalCursor is a Qt object that handles graphic items, IT IS NOT SERIALIZABLE
HENCE IT CANNOT BE "PICKLED" or otherwise "saved" to a file.
        
The only thing an Interval does not know about is the type of the cursor where 
the coordinates come from (i.e., vertical or horizontal) but that can be deduced 
from the context.

A croshair cursor, for example might be stored as a pair of
Interval objects according to an ad-hoc convention (e.g. the horizontal coordinates
first, then the vertical coordinates).
        
Changelog:
    2024-02-09 09:53:36 this is now mutable
        
"""
    # __slots__ = ()
    t0: typing.Union[numbers.Number, pq.Quantity]
    t1: typing.Union[numbers.Number, pq.Quantity]
    name: str = "Interval"
    extent: bool = False
    
    def __init__(self, t0: typing.Union[numbers.Number, pq.Quantity],
                 t1: typing.Union[numbers.Number, pq.Quantity],
                 name: str = "Interval", extent:bool=False):
        OK = all(isinstance(v, numbers.Number) for v in (t0, t1)) or all(isinstance(v, pq.Quantity) and v.ndim==0 for v in (t0, t1))
        
        if not OK:
            raise TypeError(f"Expecting scalar numbers or quantities")
        
        if all(isinstance(v, pq.Quantity) for v in (t0,t1)):
            if t0.units != t1.units:
                if not units_convertible(t0, t1):
                    raise TypeError(f"t0 units ({t0.units}) are incompatible with t1 units ({t1.units})")
                
                t1 = t1.rescale(t0)
                
        if extent:
            if t1 < 0:
                raise ValueError(f"extent {t1} must be > = 0)")
        else:
            if t0 > t1:
                raise ValueError(f"t0 ({t0}) should precede t1 ({t1})")
        
        if not isinstance(name, str) or len(name.strip()) == 0:
            name = self.__class__.__name__

        super().__init__()
        self.t0 = t0
        self.t1 = t1
        
    @classmethod
    def from_epoch(cls:type, epoch: typing.Union[neo.Epoch, DataZone],  
                           index: typing.Union[str, bytes, np.str_, int],
                           duration: bool = False):
        from . import neoutils
        import neo
        interval = neoutils.get_epoch_interval(epoch, index, duration=False)
        if len(interval) == 2: # empty labels
            if isinstance(epoch.name, str) and len(epoch.name.strip()):
                name = epoch.name
            else:
                name = "Interval"
            interval = tuple([*interval] + [name])
            
        return cls(*interval, extent=duration)

    
def epoch2intervals(epoch: typing.Union[neo.Epoch, DataZone], keep_units:bool = True,
                    duration:bool=True) -> typing.List[Interval]:
    """Generates a sequence of datatypes.Interval objects
    
    Each interval coresponds to the epoch's interval.
    
    Parameters:
    ----------
    epoch: neo.Epoch
    
    keep_units: bool (default False)
        When True, the t_start and t_stop in each interval are scalar python 
        Quantity objects (units borrowed from the epoch)
    
    """
    if (epoch.labels.size) > 0:
        labels = epoch.labels
    else:
        labels = [f"Interval_{k}" for k in range(len(epoch))]
        
    if keep_units:
        return [Interval(t, d if duration else t+d, l, duration) for (t,d,l) in zip(epoch.times, epoch.durations, labels)]
        
    else:
        return [Interval(t, d if duration else t+d, l, duration) for (t,d,l) in zip(epoch.times.magnitude, epoch.durations.magnitude, labels)]
    
@safeWrapper
def intervals2epoch(*args, **kwargs):
    """Construct a neo.Epoch or DataZone from a sequence of intervals.
    All numeric values in the intervals must be python Quantities.
    
    TODO: 2023-06-13 23:48:09
    
    Var-positional parameters:
    --------------------------
    
    datatypes.Interval objects
    
    NOTE: When args contains only one element, this can sequence of interval
    tuples as above.
    
    WARNING: 
    • The first two elements of the interval tuples, when quantities, MUST have
        compatible units (i.e. units that can be inter-converted)
    
    • The structure of the interval tuples is NOT checked 
    
    Var-keyword parameters:
    -----------------------
    
    zone:bool, default is False; flags whether to FORCE creation of a DataZone 
        object (this is always True when the interval tuples are quantities with
        units other than time units)
    
    prefix: str, default is 'interval'; the default prefix for interval names when the tuples 
        contain only two elements
    
    name:str, default is "epoch" or "zone", depending on that is returned; this 
        is the name of the gerenated neo.Epoch or DataZone object

"""
    from core.utilities import counter_suffix
    def __make_unique_label__(label, collection):
        if label in collection:
            label = counter_suffix(label, collection)
        
        collection.append(label)
        return label
    
    # duration = kwargs.pop("duration", False)
    zone = kwargs.pop("zone", False)
    prefix = kwargs.pop("prefix", "interval")
    
    if len(args) == 1 and isinstance(args[0], (tuple, list)) and not isinstance(args[0], Interval):
        args = args[0]
    
    if not all(isinstance(a, Interval) for a in args):
        raise TypeError(f"Expecting a sequence of Interval objects")
    
    # takes care of getting durations right, for "true" intervals, and also
    # checks interval labels uniqueness
    interval_labels = [] # used in the comprehension below,via __make_unique_label__
    epoch_intervals = list(map(lambda x: (x.t0, x.t1, __make_unique_label__(x.name, interval_labels)) if x.extent else (x.t0, x.t1-x.t0, __make_unique_label__(x.name, interval_labels)), args))

    # cache the units, because conversion from a list to a numpy array 'slices'
    # them out
    if isinstance(epoch_intervals[0][0], pq.Quantity):
        units = epoch_intervals[0][0].units
    else:
        units = pq.s

    # convert the above into numpy arrays, apply the units 
    times = np.array([x[0] for x in epoch_intervals]) * units

    durations = np.array([x[1] for x in epoch_intervals]) * units
    
    labels = np.array([x[2] for x in epoch_intervals])
    
    klass = DataZone if zone or not check_time_units(units) else neo.Epoch
    
    name = kwargs.pop("name", klass.__name__)
    
    return klass(times, durations=durations, labels=labels, name=name)
    
@safeWrapper
def epoch2cursors(epoch: typing.Union[neo.Epoch, DataZone], 
                  signal_viewer: typing.Optional[QtWidgets.QMainWindow] = None, 
                  axis: typing.Optional[typing.Union[int, str, pg.PlotItem, pg.GraphicsScene]] = None, 
                  **kwargs):
    """Creates vertical signal cursors from a neo.Epoch.
    
    Parameters:
    ----------
    epoch: neo.Epoch
    
    signal_viewer:SignalViewer instance, or None (the default)
        When given, the cursors will also be registered with the signal viewer
        instance that owns the axis.
    
        Prerequisite: the axis must be owned by the signal viewer instance.
    
    axis: (optional) pyqtgraph.PlotItem, pyqtgraph.GraphicsScene, or None.
    
        Default is None, in which case the function returns cursor parameters.
    
        When not None, the function populates 'axis' with a sequence of 
        vertical SignalCursor objects and returns their references in a list.
        
    Var-keyword parameters:
    ----------------------
    keep_units: bool, optional default is False
        When True, the numeric cursor parameters are python Quantities with the
        units borrowed from 'epoch'
        
    Other keyword parameters are passed to the cursor constructors:
    parent, follower, xBounds, yBounds, pen, linkedPen, hoverPen
    
    See the documentation of gui.cursors.SignalCursor.__init__ for details.
    
    Returns:
    --------
    When axis is None, returns a list of tuples of vertical cursor parameters
        (time, window, labels) where:
        
        time = epoch.times + epoch.durations/2.
        window = epoch.durations
        labels = epoch.labels -- the labels of the epoch's intervals
        
    When axis is a pyqtgraph.PlotItem or a pyqtgraph.GraphicsScene, the function
    adds vertical SignalCursors to the axis and returns a list with references
    to them.
    
    Side effects:
    -------------
    When axis is not None, the cursors are added to the PlotItem or GraphicsScene
    specified by the 'axis' parameter.
    """
    
    from gui.signalviewer import SignalViewer
    from gui.cursors import SignalCursor, SignalCursorTypes
    from qtpy import QtGui, QtCore
    # from PyQt5 import QtGui, QtCore

    keep_units = kwargs.pop("keep_units", False)
    if not isinstance(keep_units, bool):
        keep_units = False
        
    epoch_name = epoch.name if isinstance(epoch.name, str) and len(epoch.name.strip()) else "i"
        
    if keep_units:
        ret = [(t + d/2. if d else t, d if d else 0*t.units, l if l else f"{epoch_name}_{k}") for (t, d, l, k) in itertools.zip_longest(epoch.times, epoch.durations, epoch.labels, range(len(epoch)))]
        
    else:
        ret = [(t + d/2. if d else t, d if d else 0, l if l else f"{epoch_name}_{k}") for (t, d, l, k) in itertools.zip_longest(epoch.times.magnitude, epoch.durations.magnitude, epoch.labels, range(len(epoch)))]
        
    # signal_viewer = kwargs.pop("signal_viewer", None)
    
    if isinstance(axis, (int, str)):
        if not isinstance(signal_viewer, SignalViewer):
            raise TypeError(f"When axis is indicated by its index or name ({axis}) then signal_viewer must be a SignalViewer instance")
        
        if isinstance(axis, str) and axis.lower() == "all":
            axis = signal_viewer.signalsLayout.scene()
        
        else:
            if isinstance(axis, (int, str)):
                axis = signal_viewer.axis(axis)
            
    if axis is None and isinstance(signal_viewer, SignalViewer):
        axis = signal_viewer.currentAxis()
    
    if isinstance(axis, (pg.PlotItem, pg.GraphicsScene)):
        # NOTE: 2020-03-10 18:23:03
        # cursor constructor accepts python Quantity objects for its numeric
        # parameters x, y, xwindow, ywindow, xBounds and yBounds
        # NOTE: below, parent MUST be set to axis, else there will be duplicate
        # cursor lines when registering with signal viewer instance
        cursors = [SignalCursor(axis, x=t, xwindow=d,
                                cursor_type=SignalCursorTypes.vertical,
                                cursorID=l, parent=axis, relative=True) for (t,d,l) in ret]
        
        if isinstance(signal_viewer, SignalViewer):
            if isinstance(axis, pg.PlotItem):
                if axis not in signal_viewer.axes:
                    return cursors
                
            elif isinstance(axis, pg.GraphicsScene):
                if axis is not signal_viewer.signalsLayout.scene():
                    return cursors
                
                pIs = [i for i in axis.items() if isinstance(i, pg.PlotItem)]
                
                if len(pIs):
                    min_x_axis = np.min([p.viewRange()[0][0] for p in pIs])
                    max_x_axis = np.max([p.viewRange()[0][1] for p in pIs])
                    
                    min_point = pIs[0].vb.mapViewToScene(QtCore.QPointF(min_x_axis, 0))
                    max_point = pIs[0].vb.mapViewToScene(QtCore.QPointF(max_x_axis, 0))
                    
                    xbounds = [min_point.x(), max_point.x()]
                    
                    for c in cursors: # BUG 2023-06-19 12:20:36 FIXME
                        c.setBounds(xBounds = xbounds)
                        # newX = 
                        

                    pi_precisions = [signal_viewer.getAxis_xDataPrecision(ax) for ax in signal_viewer.plotItems]
                    precision = min(pi_precisions)
                else:                 
                    scene_rect = axis.sceneRect()
                    xbounds = (scene_rect.x(), scene_rect.x() + scene_rect.width())
                    precision=None
                
                
            cursorDict = signal_viewer.getSignalCursors(SignalCursorTypes.vertical)
            cursorPen = QtGui.QPen(QtGui.QColor(signal_viewer.cursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            cursorPen.setCosmetic(True)
            hoverPen = QtGui.QPen(QtGui.QColor(signal_viewer.cursorHoverColor), 1, QtCore.Qt.SolidLine)
            hoverPen.setCosmetic(True)
            linkedPen = QtGui.QPen(QtGui.QColor(signal_viewer.linkedCursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            linkedPen.setCosmetic(True)
            if isinstance(axis, pg.PlotItem):
                cursorPrecision = signal_viewer.getAxis_xDataPrecision(axis)
            elif isinstance(axis, pg.GraphicsScene):
                pi_precisions = [signal_viewer.getAxis_xDataPrecision(ax) for ax in signal_viewer.plotItems]
                cursorPrecision = min(pi_precisions)
                
            else: 
                cursorPrecision = None
               
            for c in cursors:
                signal_viewer.registerCursor(c, pen=cursorPen, hoverPen=hoverPen,
                                             linkedPen=linkedPen,
                                             precision=cursorPrecision,
                                             showValue = signal_viewer.cursorsShowValue)
        
        return cursors
    
    return ret

def intervals2cursors(*args,
                      axis: typing.Optional[typing.Union[pg.PlotItem, pg.GraphicsScene]] = None, 
                      **kwargs):
    from gui.signalviewer import SignalViewer
    from gui.cursors import SignalCursor, SignalCursorTypes
    from qtpy import QtGui, QtCore
    # from PyQt5 import QtGui, QtCore

    keep_units = kwargs.pop("keep_units", False)
    cursor_type = kwargs.pop("cursor_type", "vertical")
    
    if not isinstance(keep_units, bool):
        keep_units = False
        
    def __strip_units__(v):
        return float(v.magnitude) if (isinstance(v, pq.Quantity) and not keep_units) else v
        
    ret = [(__strip_units__(i.t0+i.t1/2) if i.extent else __strip__units__(i.t0 + (i.t1 - i.t0)/2), __strip_units__(i.t1) if i.extent else __strip_units__(i.t1-i.t0), i.name) for i in args]

    signal_viewer = kwargs.pop("signal_viewer", None)
    
    if isinstance(axis, (pg.PlotItem, pg.GraphicsScene)):
        cursors = [SignalCursor(axis, x = t, window = d, cursorID=l,
                                cursor_type=SignalCursorTypes.vertical,
                                parent=axis, relative=True) for (t,d,l) in ret]
        
        if isinstance(signal_viewer, SignalViewer):
            if isinstance(axis, pg.PlotItem):
                if axis not in signal_viewer.axes:
                    return cursors
                
            elif isinstance(axis, pg.GraphicsScene):
                if axis is not signal_viewer.signalsLayout.scene():
                    return cursors
                
            cursorDict = signal_viewer.getSignalCursors(SignalCursorTypes.vertical)
            cursorPen = QtGui.QPen(QtGui.QColor(signal_viewer.cursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            cursorPen.setCosmetic(True)
            hoverPen = QtGui.QPen(QtGui.QColor(signal_viewer.cursorHoverColor), 1, QtCore.Qt.SolidLine)
            hoverPen.setCosmetic(True)
            linkedPen = QtGui.QPen(QtGui.QColor(signal_viewer.linkedCursorColors["vertical"]), 1, QtCore.Qt.SolidLine)
            linkedPen.setCosmetic(True)
            if isinstance(axis, pg.PlotItem):
                cursorPrecision = signal_viewer.getAxis_xDataPrecision(axis)
            elif isinstance(axis, pg.GraphicsScene):
                pi_precisions = [signal_viewer.getAxis_xDataPrecision(ax) for ax in signal_viewer.plotItems]
                cursorPrecision = min(pi_precisions)
                
            else: 
                cursorPrecision = None
               
            for c in cursors:
                signal_viewer.registerCursor(c, pen=cursorPen, hoverPen=hoverPen,
                                             linkedPen=linkedPen,
                                             precision=cursorPrecision,
                                             showValue = signal_viewer.cursorsShowValue)
        
        return cursors
    
    return ret
    
