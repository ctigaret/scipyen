# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import collections, numbers, typing, itertools, dataclasses, os
from dataclasses import dataclass
from copy import deepcopy, copy

import numpy as np
import quantities as pq
import neo
from neo.core.baseneo import BaseNeo, merge_annotations
from neo.core.dataobject import DataObject, ArrayDict
import pyqtgraph as pg

from core import scipyen_quantities as cq
from core.scipyen_quantities import (checkTimeUnits, unitsConvertible)
from core.scipyendataclasses import ScipyenDataclass
# from core.utilities import counter_suffix
from .prog import (safewrapper, with_doc, scipywarn)

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
        
    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

# 
# import qtpy
# qtpy.API = os.environ["QT_API"]
# if os.environ["QT_API"] == "pyside6":
#     import PySide6
#     from PySide6 import QtWidgets
# else:
#     from qtpy import QtWidgets

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
    obj.segment=segment
    return obj

# class DataZone(DataObject):
class DataZone(neo.Epoch):
    r"""neo.Epoch-like for DataSignals
    
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
                labels:typing.Optional[typing.Union[str, typing.Sequence[str], np.ndarray]]=None, 
                units:typing.Optional[pq.Quantity]=None, 
                name:typing.Optional[str]=None, 
                description:typing.Optional[str]=None, 
                file_origin:typing.Optional[str]=None, 
                segment:typing.Optional[int]=None, 
                relative:typing.Optional[bool]=None,
                array_annotations=None, **annotations):
        r"""
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
                if not cq.unitsConvertible(places, units):
                    units = places.units
            
            if isinstance(extents, pq.Quantity):
                if not cq.unitsConvertible(places, extents):
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
                
        self.__domain_name__ = cq.unitFamilyName(self.places)
            
            
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
        if not hasattr(self, "array_annotations"):
            self.array_annotations = ArrayDict(self._get_arr_ann_length())
        self.__domain_name__ = cq.unitFamilyName(self.units)
        
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
        r"""
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
        r"""
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
        r"""For API compatibility with neo.Epoch
        """
        self.extents = durations
        
    def get_durations(self):
        return self.extents
    
    @property
    def relative(self) -> bool:
        r"""Indicates if the coordinates are relative to signal's domain origin.
        This is independent of the extents of the data zone.
        """
        return getattr(self, "_relative", False)
    
    @relative.setter
    def relative(self, val:bool):
        self._relative = val == True

    @property
    def domain_name(self):
        r"""A brief description of the domain name
        """
        if self.__domain_name__ is None:
            self.__domain_name__ = unitFamilyName(self.domain)
            
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
        r"""Alias to self.places for API compatibility with DataSignal
        """
        return self.places

    @property
    def times(self):
        r"""Alias to self.places for API compatibility with neo.Epoch
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
        
def _newInterval_(cls, times = None, durations = None, units=None, labels=None, 
                extent:bool=None, name=None, description=None,
                file_origin = None, segment = None,
                array_annotations = None, annotations = None):
    
    if not isinstance(annotations, dict):
        if annotations is None:
            annotations = dict()
        else:
            try:
                annotations = dict(annotations)
            except:
                annotations = dict() # just so that we aren't left hanging out
        
    obj = Interval(times=times, durations=durations, units=units, labels=labels,
                   extent=extent, name=name, description=description,
                   file_origin=file_origin, segment=segment,
                   array_annotations=array_annotations,
                   **annotations)
    obj.segment=segment
    return obj
        
class Interval(DataObject):
    r"""
Class similar to neo.Epoch and DataZone with the following characteristics:
        
1. As neo.Epoch and DataZone, the domain coordinates are stored as two Quantity
1D arrays (vectors) of the same size and physical units, and with as many elements
as there are sub-intervals.
        
These coordinates are accessible via the `times` and `durations` attributes,
with the same semantics as in neo.Epoch and in DataZone. To avoid confusion, an
Interval does NOT have `places` and `extents` attributes of DataZone (which are
effectively aliased `times` and `durations`).
        
2. In addition, an Interval objects has the dynamic properties `t0` and `t1`, 
and the bool attribute `extent` which defines how `t0` and `t1` are calculated
from the `times` and `durations` attributes:
        
When `extent` is True, a sub-interval 𝒌 is defined as :

    self[𝒌] - self.durations[𝒌]/2 ⋯ self[𝒌] ⋯ self[𝒌] + self.durations[𝒌]/2
        
    i.e., self[𝒌] is the MID-point of an interval with size = self.durations[𝒌]

    Therefore:
        
    `t0` is calculated as self - self.durations/2
    `t1` is calculated as self + self.durations/2
        
    This behaviour is similar to that of a SignalCursor, which is defined by a 
central coordinate and a symmetric window around it.
        
When `extent` is False, a sub-interval 𝒌 is defined as:

    self[𝒌] ⋯ self[𝒌] + self.durations[𝒌]

    i.e., self[𝒌] is the start of the sub-interval, whwereas the end of the 
sub-interval is the start + the sub-interval's duration. 

    Therefore:
    
    `t0` is self
    `t1` is calculated as self + self.durations
        
The advantage of this is that one can switch the behaviour by setting the `extent`
attribute to True or False and query `t0` and `t1` without any changes to the 
underlying domain coordinates `times` and `durations`.

3. As for DataZone, the physical units (or dimensionality) of the domain 
coordinates are NOT restricted to time units.


 """
    from core.datasignal import DataSignal
    _parent_objects = ('Segment',)
    _parent_attrs = ('segment',)
    _quantity_attr = ('t0', 't1')
    _necessary_attrs = (('t0', pq.Quantity, 1),
                        ('t1', pq.Quantity, 1), 
                        ('labels', np.ndarray, 1, np.dtype('U')),
                        ('extent', bool, 1, False))
    
    def __new__(cls, times = None, durations = None, 
                units: typing.Optional[pq.Quantity]=None, 
                labels: typing.Optional[typing.Union[str, typing.Sequence[str], np.ndarray]]=None, 
                extent: typing.Optional[bool]=None, 
                name: typing.Optional[str]=None,
                description: typing.Optional[str]=None,
                file_origin:typing.Optional[str] = None, 
                segment: typing.Optional[int] = None,
                array_annotations = None, 
                **annotations):
        units_ = None
        if isinstance(times, np.ndarray):
            assert(times.ndim <= 1), "times must be a 1D array"
            if isinstance(times, pq.Quantity):
                units_ = times.units
                times = times.flatten()
                
        elif isinstance(times, typing.Sequence) and alltimes(isinstance(v, numbers.Number) for v in times):
            times = np.array(times).flatten()
            
        elif isinstance(times, numbers.Number):
            times = np.array([times]).flatten()
            
        else:
            raise TypeError(f"Invalid 'times' ({type(times).__name__})")
        
        if isinstance(durations, np.ndarray):
            assert(durations.ndim <= 1), "durations must be a 1D array"
            if durations.ndim == 0:
                durations = durations.flatten()
            assert durations.size == times.size, "times and durations must have identical size"
            if isinstance(durations, pq.Quantity):
                if isinstance(times, pq.Quantity):
                    if durations.units != times.units:
                        if unitsConvertible(durations, times):
                            durations = durations.rescale(times.units)
                        else:
                            raise ValueError(f"Units of durations ({durations.units}) are incompatible with those of times ({times.units})")
                else:
                    units_ = durations.units
                    times = times * durations.units
            
        elif isinstance(durations, typing.Sequence) and all(isinstance(v, numbers.Number) for v in durations):
            assert len(durations) == times.size, "times and durations must have identical size"
            durations = np.array(durations).flatten()
            
        elif isinstance(durations, numbers.Number):
            assert times.size == 1, "times and durations must have identical size"
            durations = np.array([durations]).flatten()
            
        else:
            raise TypeError(f"Invalid 'durations' ({type(durations).__name__})")
        
        if isinstance(times, pq.Quantity) and not isinstance(durations, pq.Quantity):
            durations = durations * times.units
        
        if isinstance(units_, pq.Quantity):
            if all(isinstance(v, pq.Quantity) for v in (times, durations)):
                # NOTE: 2025-04-27 10:39:14
                # ignore silently
                # if units is not None:
                #     scipywarn("Ignoring 'units' because times and durations already have them")
                units = units_
            else:
                times = times * units
                durations = durations * units
                
        else:
            if not isinstance(units, (pq.Quantity, pq.dimensionality.Dimensionality)):
                raise TypeError(f"'units' must be a pq.Quantity; instead got {type(units)}")

            if not all(isinstance(v, pq.Quantity) for v in (times, durations)):
                times = times * units
                durations = durations * units
        
        if not isinstance(extent, bool):
            extent = False
        if extent:
            if np.any(durations < 0):
                # because the window around times cannot be negative
                raise ValueError("durations must contain only values > = 0")
            
        if labels is None:
            labels = np.array([], dtype='U')

        elif not isinstance(labels, np.ndarray):
            labels = np.array(labels)
            if labels.size != times.size and labels.size:
                raise ValueError("Labels array has different length to times")

        if not isinstance(segment, (neo.Segment, type(None))):
            raise TypeError(f"'segment' expected to be a neo.Segment or None; instead, got {type(segment).__name__}")

        obj = pq.Quantity.__new__(cls, times, units = units.dimensionality)
        obj._labels = labels
        obj._t1 = durations
        obj._extent = extent == True
        obj._segment = segment
        
        return obj
    
    def __init__(self, times = None, durations = None, units=None, labels=None, 
                extent:bool=None, name=None, description=None,
                file_origin = None, segment = None,
                array_annotations = None, **annotations):
        DataObject.__init__(self, name=name, description=description,
                            file_origin = file_origin,
                            array_annotations = array_annotations,
                            **annotations)
        
        self.__domain_name__ = cq.unitFamilyName(self.times)
        
    def __reduce__(self):
        return _newInterval_, (self.__class__, pq.Quantity(self), self._t1, self.units,
                              self.labels, self.extent, self.name, self.description, 
                              self.file_origin, self.segment,
                              self.array_annotations, self.annotations)
    
    def __array_finalize__(self, obj):
        super().__array_finalize__(obj)
        # self._t0 = getattr(obj, "_t0", None)
        self._t1 = getattr(obj, "_t1", None)
        self._labels = getattr(obj, "labels", None)
        self.extent = getattr(obj, "extent", None)
        self.name = getattr(obj, "name", None)
        self.annotations = getattr(obj, "annotations", None)
        self.file_origin = getattr(obj, "file_origin", None)
        self.description = getattr(obj, "description",  None)
        self.segment = getattr(obj, "segment", None)
        if not hasattr(self, "array_annotations"):
            self.array_annotations = ArrayDict(self._get_arr_ann_length())
        self.__domain_name__ = cq.unitFamilyName(self.units)
        
    def __repr__(self):
        times = list(self.times)
        durations = list(self.durations)
        # print(f"{self.__class__.__name__}.__repr__: labels = {self.labels}")
        if isinstance(self.labels, np.ndarray) and self.labels.ndim>0 and self.labels.size>0:
            labels = list(self.labels)
        else:
            labels = [""]
        objs = ['%s@%s for %s' % (label, str(time), str(dur)) for label, time, dur in
                zip(labels, times, durations)]
        return f"<{self.__class__.__name__}:{', '.join(objs)}>"

    def _repr_pretty_(self, pp, cycle):
        super()._repr_pretty_(pp, cycle)
        
    def copy(self) -> typing.Self:
        times = self.times.magnitude
        durations = self.durations.magnitude
        labels = np.array(self.labels)
        description = str(self.description)
        segment = int(self.segment) if isinstance(self.segment, int) else None # an int !
        array_annotations = deepcopy(self.array_annotations)
        extent = self.extent
        units = self.units
        
        obj = self.__class__(times = times, durations = durations,
                                           labels = labels, units = units)
        obj.description = description
        obj.array_annotations = array_annotations
        obj.segment = segment
        obj.extent = extent
        obj.annotations.update(self.annotations)
        
        return obj
    
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
            t0=self.view(pq.Quantity).rescale(dim),
            t1=self._t1.rescale(dim),
            labels=self.labels,
            units=units)

        # Expected behavior is deepcopy, so deepcopying array_annotations
        obj.array_annotations = deepcopy(self.array_annotations)
        obj.segment = self.segment
        obj.extent = self.extent
        return obj

    def __getitem__(self, i):
        '''
        Get the item or slice :attr:`i`.
        '''
        obj = super().__getitem__(i)
        obj._t0 = self.t0[i]
        obj._t1 = self.t1[i]
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

        The :class:`Interval` objects are concatenated horizontally
        (column-wise), :func:`np.hstack`).

        If the attributes of the two :class:`Epoch` are not
        compatible, and Exception is raised.
        '''
        if self.extent != other.extent:
            raise ValueError("'extent' attribute must be the same in both Interval objects")
        
        othert0 = other.rescale(self.units)
        othert1 = other._t1.rescale(self.units)
        t0 = np.hstack([self, othert0]) * self.units
        t1 = np.hstack([self._t1, othert1]) * self.units
        labels = np.hstack([self.labels, other.labels])
        kwargs = {}
        kwargs["extent"] = self.extent
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

        return Interval(t0=t0, t1=t1, labels=labels, **kwargs)

    def _copy_data_complement(self, other):
        '''
        Copy the metadata from another :class:`Interval`.
        Note: Array annotations can not be copied here because length of data can change
        '''
        # Note: Array annotations cannot be copied because length of data could be changed
        # here which would cause inconsistencies. This is instead done locally.
        for attr in ("name", "file_origin", "description"):
            setattr(self, attr, deepcopy(getattr(other, attr, None)))
        self._copy_annotations(other)

    def _copy_annotations(self, other):
        self.annotations = deepcopy(other.annotations)

    def duplicate_with_new_data(self, t0, t1, labels, units=None, extent=False):
        '''
        Create a new :class:`Interval` with the same metadata
        but different data (t0, t1, labels, units, extent)

        Note: Array annotations can not be copied here because length of data can change
        '''

        if units is None:
            units = self.units
        else:
            units = pq.quantity.validate_dimensionality(units)

        new = self.__class__(t0=t0, t1=t1, labels=labels, units=units)
        new._copy_data_complement(self)
        new._labels = labels
        new._extent = extent
        new.segment = self.segment
        # Note: Array annotations can not be copied here because length of data can change
        return new

    def interval_slice(self, begin, end):
        '''
        Creates a new :class:`Interval` corresponding to the time slice of
        the original :class:`Interval` between (and including) times
        :attr:`t_start` and :attr:`t_stop`. Either parameter can also be None
        to use infinite endpoints for the time interval.
        '''
        _t_start = begin
        _t_stop = end
        if _t_start is None:
            _t_start = -np.inf
        if _t_stop is None:
            _t_stop = np.inf

        indices = (self.t0 >= _t_start) & (self.t0 <= _t_stop)

        # Time slicing should create a deep copy of the object
        new_epc = deepcopy(self[indices])

        return new_epc
    
    def time_slice(self, t_start, t_stop):
        return self.interval_slice(t_start, t_stop)
        
    def shift(self, shift):
        r"""
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
        t0 = self + t_shift
        t1 = self._t1
        new_epc = self.duplicate_with_new_data(t0=t0, t1=t1, labels=self.labels)

        # Here we can safely copy the array annotations since we know that
        # the length of the Interval does not change.
        new_epc.array_annotate(**self.array_annotations)

        return new_epc
    
    def time_shift(self, t_shift):
        r"""
        Shifts by a given amount.

        Parameters:
        -----------
        t_shift: Quantity (time)
            Amount of time by which to shift the :class:`Interval`.

        Returns:
        --------
        epoch: :class:`Interval`
            New instance of an :class:`Interval` object starting at t_shift later than the
            original :class:`Interval` (the original :class:`Interval` is not modified).
        """
        return self.shift(t_shift)
    
    @property
    def domain_name(self):
        r"""A brief description of the domain name
        """
        if self.__domain_name__ is None:
            self.__domain_name__ = unitFamilyName(self.units)
            
        return self.__domain_name__
    
    @domain_name.setter
    def domain_name(self, value):
        if isinstance(value, str) and len(value.strip()):
            self.__domain_name__ = value
    
    @property
    def times(self):
        r"""Read-only. 
    To create an object with new times use self.duplicate_with_new_data(…)
    """
        # for comaptibility wiht neo.Epoch/DataZone, always return self
        return pq.Quantity(self)
    
    @property
    def durations(self):
        # this is always self._t1
        return self._t1

    @durations.setter
    def durations(self, val):
        self._t1 = val
        
    @property
    def t0(self):
        r"""The start points of each interval.
    Read-only.
    To create an object with new times use self.duplicate_with_new_data(…)
    """
        # NOTE: 2025-04-27 12:03:48
        # The array in 'self' is always a START point, as in neo.Epoch
        # self._t1 is always a duration as in neo.Epoch
        # but when we query 't0' or 't1', they MUST be calculated according to 
        # 'extent':
        #
        # When extent is True, an interval 𝒌 is defined as :
        #
        #   self[𝒌] - self._t1[𝒌]/2 ⋯ self[𝒌] ⋯ self[𝒌] + self._t1[𝒌]/2
        #
        #   => 
        #   t0 is self - self._t1/2
        #   t1 is self + self._t1/2
        #
        # When extent is False, an interval 𝒌 is:
        #
        #   self[𝒌] ⋯ self[𝒌] + self._t1[𝒌]
        #
        #   =>
        #   t0 is self
        #   t1 is self + self._t1
        # 
        
        if self.extent:
            return pq.Quantity(self - self._t1/2)
        else:
            return pq.Quantity(self)

    @property
    def t1(self):
        r"""The second (end) point of the intrervals.
    Read-only
    To create an object with new times use self.duplicate_with_new_data(…)
    """
        # see NOTE: 2025-04-27 12:03:48
        # The array in 'self' is always a START point, as in neo.Epoch
        # self._t1 is always a duration as in neo.Epoch
        # but when we query 't0' or 't1', they MUST be calculated according to 
        # 'extent':
        #
        # When extent is True, an interval 𝒌 is defined as :
        #
        #   self[𝒌] - self._t1/2[𝒌] ⋯ self[𝒌] ⋯ self[𝒌] + self._t1/2[𝒌]
        #
        #   => 
        #   t0 is self - self._t1/2
        #   t1 is self + self._t1/2
        #
        # When extent is False, an interval 𝒌 is:
        #
        #   self[𝒌] ⋯ self[𝒌] + self._t1[𝒌]
        #
        #   =>
        #   t0 is self
        #   t1 is self + self._t1
        # 
        if self.extent:
            return pq.Quantity(self + self._t1/2)
        else:
            return pq.Quantity(self + self._t1)
        
    @property
    def boundaries(self) -> tuple:
        r"""Tuple (self.t0, self.t1)"""
        return (self.t0, self.t1)
        
    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels):
        if self.labels is not None and self.labels.size > 0 and len(labels) != self.size:
            raise ValueError("Labels array has different length to times ({} != {})"
                             .format(len(labels), self.size))
        self._labels = np.array(labels)
        
    @property
    def extent(self) -> bool:
        return self._extent
    
    @extent.setter
    def extent(self, val:bool):
        if not isinstance(val, bool):
            val = False
        self._extent = val
        
    @property
    def segment(self) -> neo.Segment | None:
        return self._segment
    
    @segment.setter
    def segment(self, val:typing.Optional[neo.Segment] = None):
        self._segment = val
    
    @classmethod
    def fromNeoEpoch(cls:type, 
                   epoch: typing.Union[neo.Epoch, DataZone],  
                   index: typing.Optional[typing.Union[str, bytes, np.str_, int, typing.Sequence[typing.Union[str, bytes, np.str_, int]], np.ndarray, range, slice]] = None,
                   extent: bool = False,
                   merge: bool = False,
                   name: typing.Optional[str] = None,
                   description: typing.Optional[str] = None):
        r"""
        Factory for Interval using a neo.Epoch.
        
        WARNING: Floating point divisions during conversion will introduce
    errors when converting between neo.Epoch and Interval when 'extent' is 
    True. These errors will accumulate when converting from Epoch to Interval
    and back to Epoch.
    """
        # WARNING 2025-04-27 11:31:48 FIXME/TODO
        # I could avert floating point division errors by applying these operations
        # lazily - store the start and stop values as (t0, t0+duration) REGARDLESS
        # OF THE VALUE OF 'extent', then apply these operations only when the 
        # corresponding properties (t0 or t1) are queried, and according to the 
        # value of 'extent'
        #
        # I will, however, have to adjust the code for instantiation (__new__, 
        # __init__, __array_finalize__) and serialization (_newInterval_,
        # __reduce__) to take this contigency into account.
        #
        from . import neoutils
        import neo
        
        if not isinstance(epoch, (neo.Epoch, DataZone)):
            raise TypeError(
                f"'epoch' expected to be a neo.Epoch; got {type(epoch).__name__} instead"
            )
        
        if isinstance(index, (str, np.str_, bytes)):
            if isinstance(index, bytes):
                index = index.decode()

            if index not in epoch.labels:
                raise ValueError(f"Interval label {index} not found")

            ndx = np.flatnonzero(epoch.labels == index)
            epoch = epoch[ndx]

        elif isinstance(index, int):
            if index not in range(-len(epoch), len(epoch)):
                raise ValueError(
                    f"Invalid index {index} for an epoch with {len(epoch)} intervals"
                )
            ndx = np.array([index])
            epoch = epoch[ndx]
            
        elif isinstance(index, typing.Sequence):
            if all(isinstance(v, bytes) for v in index):
                index = list(map(lambda v: v.decode()))
                
            if all(isinstance(v, (str, np.str_)) for v in index):
                try:
                    ndx = np.array(list(map(lambda v: np.flatnonzero(epoch.labels == v), index))).ravel()
                except:
                    print(f"'index' {index} contains invalid labels")
                    raise
            elif all(isinstance(v, int) for v in index):
                ndx = np.array(index).ravel()
            else:
                raise TypeError(f"Invalid index specified: {index}")
                
            # ndx = np.array(list(map(lambda v: np.flatnonzero(epoch.labels == v.decode()) if isinstance(v, str, np.str_, bytes) else v)))
            epoch = epoch[ndx]
            
        elif isinstance(index, (np.ndarray, slice, range)):
            epoch = epoch[index]
            
        elif index is not None:
            raise TypeError(
                f"Invalid index type: {type(index).__name__}"
            )
        
        t = epoch.times.flatten()
        d = epoch.durations.flatten()
        labels = epoch.labels
        name = name if isinstance(name, str) and len(name.strip()) else epoch.name
        description = description if isinstance(description, str) and len(description.strip()) else epoch.description
        segment = epoch.segment
        # name = epoch.labels[ndx].flatten()[0] if ndx in range(epoch.labels.size) else epoch.labels[ndx]
        
        if merge and len(epoch) > 1:
            if ndx is None:
                # full duration: the very last start time + corresponding duration, minus the very first start time
                d = t[-1]+d[-1] + t[0] 
                # the very first start time;
                t = t[0] 
            
        t0, t1 = (t, d)

        return cls(t0, t1, units=None, labels=labels, extent=extent, 
                  name=name, description=description, segment=segment)
    
    def toDomainSlices(self, shift:typing.Optional[pq.Quantity] = None) -> np.ndarray:
        r"""Returns a 2D Quantity array with (t0,t1) row-wise, for each interval"""
        if shift is None:
            return np.transpose(np.vstack((self.t0, self.t1))) * self.units
        else:
            return np.transpose(np.vstack((self.t0+shift, self.t1+shift))) * self.units
    
    def sliceSignal(self, signal:typing.Union[neo.AnalogSignal, DataSignal],
                    index=None) -> typing.Sequence:
        domain_slices = self.toDomainSlices()
        if np.any(domain_slices.flatten() < signal.t_start) :
            domain_slices = self.toDomainSlices(signal.t_start)
            
        if np.any(domain_slices.flatten() > signal.t_stop):
            raise ValueError(f"The interval {self.t0} — {self.t1} falls outside, or crosses, the signal's domain boundaries ({signal.t_start} — {signal.t_stop}). Consider shifting the interval first")
        
        if index is not None:
            domain_slices = domain_slices[index:]
            
        return tuple(map(lambda k: signal.time_slice(*domain_slices[k,:]), range(domain_slices.shape[0])))
    
    def reduceSignal(self, fun, signal, index): # TODO 2025-04-27 23:40:01 see ephys.interval_reduce
        pass
    
    def toSignalCursors(self,
                        signalViewer = None,
                        axis: typing.Optional[typing.Union[pg.PlotItem, pg.GraphicsScene, type(dataclasses.MISSING), int, str]]=None,
                        **kwargs) -> typing.Sequence:
        r"""Creates vertical or horizontal SignalCursor objects from the sub-intervals.
        
        axis:   when None, indicates that we want to go across all axes (hence use the scene)
                when MISSING, indicates we want to use the currently active axis in the signal viewer
        
        signalViewer: when not a SignalViewer instance, this returns the stacked
            cursor coordinates with one (central coord, window) per row for each
            sub-interval
    """
        from gui.signalviewer import SignalViewer
        from gui.cursors import SignalCursor, SignalCursorTypes
        
        keep_units = kwargs.pop("keep_units", False)
        cursor_type = SignalCursorTypes.getType(kwargs.pop("cursor_type", "vertical"))
        
        if cursor_type in (SignalCursorTypes.crosshair, SignalCursorTypes.point):
            raise ValueError(f"{cursor_type} cursors are not supported")
        
        # a cursor is defined by the central coordinate and a symmetric window 
        # around it; therefore:
        if self.extent:
            # when `extent` is True we need to pass the `times`  (mid-points) and `durations`
            c = self.times # cursor coordinate
            w = self.durations # cursor window
        else:
            # when extent is False we need to calculate the mid-points and pass `durations`
            c = self + self.durations/2 # cursor coordinate
            w = self.durations # cursor window
        
        # pack these in a 2D Quantity array, with each row as
        coords = np.transpose(np.vstack((c, w))) * self.units
        
        if isinstance(signalViewer, SignalViewer):
            if axis is None:
                axis = signalViewer.scene # multi-axes cursors
            elif axis is dataclasses.MISSING:
                axis = signalViewer.currentAxis
            elif isinstance(axis, (int, str)):
                axis = signalViewer.axis(axis)
            else:
                if isinstance(axis, pg.PlotItem) and axis not in signalViewer.axes:
                    raise ValueError(f"The specified axis was not found in the signal viewer")
                
                elif isinstance(axis, pg.GraphicsScene) and axis is not signalViewer.scene:
                    raise ValueError(f"The specified axis (a scene) does not belong to the signalViewer")
                
            cursorsDict = signal_viewer.getSignalCursors(cursor_type)
            nExistingCursors = len(cursorsDict)
            
            gen_label = lambda k: self.labels[k] if len(self.labels[k]) else f"{cursor_type.name[0]}{nExistingCursors + k}" # e.g. v0, v1, etc
                
            gen_cursor = lambda k: SignalCursor(axis, x = coords[k,0], xwindow = coords[k,1], 
                                                        cursor_type = cursor_type, cursorID = gen_label[k]) \
                                    if cursor_type == SignalCursorTypes.vertical else \
                                    SignalCursor(axis, y = coords[k,0], ywindow = coords[k,1], 
                                                    cursor_type = cursor_type, cursorID = gen_label[k])
                                
            cursors = tuple(map(lambda k: gen_cursor(k), range(coords.shape[0])))
            
            cursorPen = QtGui.QPen(QtGui.QColor(signalViewer.cursorColors[cursor_type.name]), 1, QtCore.Qt.SolidLine)
            cursorPen.setCosmetic(True)
            hoverPen = QtGui.QPen(QtGui.QColor(signalViewer.cursorHoverColor), 1, QtCore.Qt.SolidLine)
            hoverPen.setCosmetic(True)
            linkedPen = QtGui.QPen(QtGui.QColor(signalViewer.linkedCursorColors[cursor_type.name]), 1, QtCore.Qt.SolidLine)
            linkedPen.setCosmetic(True)
            
            if isinstance(axis, pg.PlotItem):
                cursorPrecision = signal_viewer.getAxis_xDataPrecision(axis)
                
            elif isinstance(axis, pg.GraphicsScene):
                pi_precisions = [signal_viewer.getAxis_xDataPrecision(ax) for ax in signal_viewer.plotItems]
                cursorPrecision = min(pi_precisions)
                
            else: 
                cursorPrecision = None

            for c in cursors:
                signalViewer.registerCursor(c, pen = cursorPen, hoverPen = hoverPen,
                                            linkedPen = linkedPen,
                                            precision = cursorPrecision,
                                            showValue = signalViewer.cursorsShowValue)
            return cursors
        
        return coords

    def toNeoEpoch(self, enforceDataZone:bool=False, compensateExtent:bool=True) -> neo.Epoch | DataZone:
        r"""Export to neo.Epoch or DataZone
    Constructs a neo.Epoch or a DataZone based on the values of 't0' and 't1'.
    
    Returns a neo.Epoch is this Interval is defined in the time domain and
    'enforceDataZone' is False (the default); otherwise, returns a DataZone.
    
    An epoch 𝒌 is defined as:
    
    epoch.times[𝒌] ⋯ epoch.times[𝒌] + epoch.durations[𝒌]
    
    An interval i[𝒌] is defined as:
    
    i[𝒌] ⋯ i[𝒌] + i.durations[𝒌], when 'extent' is False
    
        i.e., i[𝒌] is the start point
    
    i[𝒌] - i.durations[𝒌]/2 ⋯ i[𝒌] ⋯ i[𝒌] + i.durations[𝒌]/2, when extent is True
        
        i.e., i[𝒌] is the MIDDLE point
    
    Therefore, if the interval was created from a neo.Epoch or DataZone with 
    'extent' True, the method will generate a DataZone or neo.Epoch left-shifted
    by an amount equal to half the duration of the original neo.Epoch or DataZone.
    
    To recreate the original neo.Epoch or DataZone, when the interval has extent
    True one must compensate the shift by passing compensateExtent = True to this
    method, which will result in a neo.Epoch or DataZone based on the internal
    times of the Interval.
    
    By default, compensateExtent is True, so that Interval objects created from
    a neo.Epoch or DataZone using extent True will always recreate the original
    neo.Epoch or DataZone by this method. To circumvent this behaviour and create
    a left-shifted verison of the original neo.Epoch or DataZone, the pass
    'compensateExtent=False'.
     
    'compensateExtent' is is ignored when self.extent is False.
    
    """
        name = self.name
        labels = self.labels
        
        cls = neo.Epoch if (cq.checkTimeUnits(self) and not enforceDataZone) else DataZone
        
        if self.extent and compensateExtent:
            times = pq.Quantity(self)
        else:
            times = self.t0
                
        
        return cls(times=times, durations=self.durations, labels=self.labels, 
                        units=self.units, name=self.name,
                        description=self.description, file_origin=None,
                        array_annotations = self.array_annotations,
                        **self.annotations)
                
def epoch2intervals(epoch: typing.Union[neo.Epoch, DataZone], keep_units:bool = True,
                    duration:bool=False) -> typing.List[Interval]:
    r"""Generates a sequence of datatypes.Interval objects
    
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
    
@safewrapper
def intervals2epoch(*args, **kwargs):
    r"""Construct a neo.Epoch or DataZone from a sequence of Interval objects.
    All numeric values in the intervals must be python Quantities.
    
    TODO: 2023-06-13 23:48:09
    
    Var-positional parameters:
    --------------------------
    
    Interval objects
    
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
    from core.strutils import counter_suffix
    def __make_unique_label__(label, collection):
        if label in collection:
            label = counter_suffix(label, collection)
        
        collection.append(label)
        return label
    
    # duration = kwargs.pop("duration", False)
    zone = kwargs.pop("zone", False)
    prefix = kwargs.pop("prefix", "interval")
    
    # print(len(args))
    
    if len(args) == 1 and isinstance(args[0], (tuple, list)) and all(isinstance(a, Interval) for a in args[0]):
        intervals = args[0]
        
    else:
        intervals = args
    
    
    # print(f"intervals2epoch intervals: {[(i, type(i)) for i in intervals]}")
    
    if not all(isinstance(a, Interval) for a in intervals):
        raise TypeError(f"Expecting a sequence of Interval objects")
    
    # takes care of getting durations right, for "true" intervals, and also
    # checks interval labels uniqueness
    interval_labels = kwargs.pop("labels", list()) # used in the comprehension below, via __make_unique_label__
    uniquename = lambda x:  __make_unique_label__(x.name, interval_labels) if len(interval_labels) else x.name
    epoch_intervals = list(map(lambda x: (x.t0, x.t1, uniquename(x)) if x.extent else (x.t0, x.t1-x.t0, uniquename(x)), intervals))
    # epoch_intervals = list(map(lambda x: (x.t0, x.t1, __make_unique_label__(x.name, interval_labels)) if x.extent else (min(x.t0, x.t1), abs(x.t1-x.t0), __make_unique_label__(x.name, interval_labels)), args))

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
    
    klass = DataZone if zone or not checkTimeUnits(units) else neo.Epoch
    
    name = kwargs.pop("name", klass.__name__)
    
    return klass(times.flatten(), durations=durations.flatten(), labels=labels, name=name)
    
@safewrapper
def epoch2cursors(epoch: typing.Union[neo.Epoch, DataZone], 
                  signal_viewer: typing.Optional[QtWidgets.QMainWindow] = None, 
                  axis: typing.Optional[typing.Union[int, str, pg.PlotItem, pg.GraphicsScene]] = None, 
                  **kwargs):
    r"""Creates vertical signal cursors from a neo.Epoch.
    
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
    r"""Creates a sequence of SignalCursor objects from a sequence of intervals.
    The intervals in `args` are NOT Interval objects - please see Interval.toSignalCursors()
    
    WARNING: This function will be DEPRECATED
    
"""
    from gui.signalviewer import SignalViewer
    from gui.cursors import SignalCursor, SignalCursorTypes

    keep_units = kwargs.pop("keep_units", False)
    cursor_type = kwargs.pop("cursor_type", "vertical")
    
    if len(args) == 1 and isinstance(args[0], (tuple, list)) and all(isinstance(a, Interval) for a in args[0]):
        intervals = args[0]
        
    else:
        intervals = args
    
    
    # print(f"intervals2epoch intervals: {[(i, type(i)) for i in intervals]}")
    
    if not all(isinstance(a, Interval) for a in intervals):
        raise TypeError(f"Expecting a sequence of Interval objects")

    if not isinstance(keep_units, bool):
        keep_units = False
        
    def __strip_units__(v):
        return float(v.magnitude) if (isinstance(v, pq.Quantity) and not keep_units) else v
        
    ret = [(__strip_units__(i.t0+i.t1/2) if i.extent else __strip_units__(i.t0 + (i.t1 - i.t0)/2), __strip_units__(i.t1) if i.extent else __strip_units__(i.t1-i.t0), i.name) for i in intervals]

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
    
