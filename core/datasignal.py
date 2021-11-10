import numbers
import numpy as np

import quantities as pq

import neo
from neo.core import baseneo
from neo.core.baseneo import BaseNeo
from neo.core import basesignal
from neo.core.basesignal import BaseSignal
from neo.core import container
from neo.core.dataobject import DataObject, ArrayDict

from core.quantities import (units_convertible, name_from_unit)


def _new_DataSignal(cls, signal, units=None, dtype=None, copy=True,
                    t_start=0*pq.dimensionless, sampling_period=None,
                    sampling_rate=None, name=None, file_origin=None,
                    description=None, array_annotations=None, annotations=None,
                    #channel_index=None, 
                    segment=None):
    if not isinstance(array_annotations, ArrayDict):
        array_annotations = ArrayDict(signal.shape[-1])
    obj = cls(signal=signal, units=units, dtype=dtype, copy=copy,
              origin=origin, sampling_period=sampling_period, sampling_rate=sampling_rate,
              name=name, file_origin=file_origin, description=description,
              array_annotations=array_annotations,
              **annotations)
    
    #obj.channel_index = channel_index
    obj.segment = segment
    
    return obj

def _new_IrregularlySampledDataSignal(cls, domain, signal, units=None, 
                                      domain_units=None, dtype=None, copy=True, 
                                      name=None,file_origin=None,
                                      description=None,annotations=None,
                                      array_annotations=None,
                                      #channel_index=None,
                                      segment=None,
                                      ):
    if not isinstance(array_annotations, ArrayDict):
        array_annotations = ArrayDict(signal.shape[-1])
        
    obj = cls(domain=domain,signal=signal,units=units,domain_units=domain_units,
              dtype=dtype,copy=copy,name=name,file_origin=file_origin,
              description=description, array_annotations=array_annotations,**annotations)
    
    obj.segment=segment
    #obj.channel_index = channel_index
    
    return obj


class DataSignal(BaseSignal):
    """A "generic" neo.AnalogSignal with domain not restricted to time.
    
    Very much modeled after neo.AnalogSignal
    """
    #TODO 
    #NOTE: 2018-01-08 22:16:41
    # Grouping Objects in neo:
    #
    # 1) ChannelIndex:
    # is a set of indices into analogsignal objects and 
    # represent logical/physical recording channels:
    # *  links AnalogSignal objects recorded from the same electrode across several 
    #       segments
    #   - of particular significance for (multi)electrode recordings in vivo, 
    #   - for in vitro recordings, there are as many channels as recording electrodes
    #       used: commonly, only one channel for Ca imaging/uncaging expriments
    # * used by spike sorting algorithms (extracellular signals), where spikes are
    #   recorded by more than one electrode (recording channel), thus the ChannelIndex
    #   helps to associate each Unit with the group if recording channels from which
    #   it was obtained.
    #
    # 2) Unit:
    # * links the spiketrain objects within a block, possibly across multiple segments,
    #   that were emitted by the same cell
    # * linked to the ChannelIndex object from which the spikes were detected
    #
    
    # by analogy, we need to define the following grouping objects:
    #
    #
    _single_parent_objects = ("Segment", "ChannelIndex") 
    
    _quantity_attr = 'signal'
    
    _necessary_attrs = (('signal', pq.Quantity, 2),
                        ('sampling_period', pq.Quantity, 0),
                        ('origin', pq.Quantity, 0))
    
    _recommended_attrs = neo.baseneo.BaseNeo._recommended_attrs

    def __new__(cls, signal, units=None, dtype=None, copy=True, 
                t_start=0*pq.dimensionless, origin=0*pq.dimensionless, 
                sampling_period=None, sampling_rate=None, 
                name=None, file_origin=None, description=None, 
                array_annotations=None, **annotations):
        
        if units is None:
            if not hasattr(signal, "units"):
                units = pq.dimensionless
                
        elif isinstance(signal, pq.Quantity):
            if units != signal.units:
                signal = signal.rescale(units)
                
        obj = pq.Quantity(signal, units=units, dtype=dtype, copy=copy).view(cls)

        if obj.ndim == 1:
            obj.shape = (-1,1)
            
        obj._origin = 0 * pq.dimensionless
        
        if isinstance(origin, pq.Quantity):
            t_start = origin
        
        elif t_start is not None:
            if not isinstance(t_start, pq.Quantity):
                raise TypeError("Expecting a Quantity for origin; got %s instead" % (type(origin).__name__))
            
            elif t_start.size > 1:
                raise TypeError("origin must be a scalar quantity; got %s instead" % origin)
            
        obj._origin = t_start
        
        if sampling_period is None:
            # sampling period not given
            if sampling_rate is None:
                # sampling period not given and sampling rate not given =>
                # set default sampling_period
                obj._sampling_period = 1 * obj._origin.units # default sampling period
                
            elif isinstance(sampling_rate, pq.Quantity): # calculate from sampling rate if given
                # sampling period not given, sampling rate given as Quantity =>
                # calculate sampling_period from given sampling_rate
                if t_start.units == pq.dimensionless and sampling_rate.units != pq.dimensionless:
                    obj._origin = origin.magnitude * (1/sampling_rate).units
                    
                if sampling_rate.units != 1/obj._origin.units:
                    raise TypeError("Mismatch between sampling rate units and object units: %s and %s" % (sampling_rate.units, obj._origin.units))
                
                elif sampling_rate.size > 1:
                    raise TypeError("Sampling rate is expected to be a scalar quantity; got %s instead" % sampling_rate)
                
                else:
                    obj._sampling_period = 1/sampling_rate
                    
            elif isinstance(sampling_rate, numbers.Real):
                # sampling period not given; sampling rate given as a unitless scalar
                # => caluclate sampling period
                if sampling_rate <= 0:
                    raise ValueError("Sampling rate must have a strictly positive value; got %g instead" % sampling_rate)
                
                obj._sampling_period = 1/(sampling_rate * obj._origin.units)
                
            else:
                raise TypeError("Sampling rate expected to be a scalar python quantity; got %s instead" % (type(sampling_rate).__name__))
            
        elif isinstance(sampling_period, pq.Quantity):
            # sampling period given; disregard sampling rate if given at all
            if t_start.units == pq.dimensionless and sampling_period.units != pq.dimensionless:
                obj._origin = origin.magnitude * sampling_period.units
                
            if sampling_period.units != obj._origin.units:
                raise TypeError("Sampling period and signal domain have incompatible units: %s and %s" % (sampling_period.units, obj._origin.units))
            
            elif sampling_period.size > 1:
                raise TypeError("Sampling period is expected to be a scalar quantity; got %s instead" % sampling_period)
            
            else:
                obj._sampling_period = sampling_period
                
        elif isinstance(sampling_period, numbers.Real):
            if sampling_period <= 0:
                raise ValueError("Sampling period must be strictly positive; got %g instead" % sampling_period)
            
            obj._sampling_period = sampling_period * obj._origin.units
        
        obj.segment=None
        obj.channel_index=None

        return obj
    
    def __init__(self, signal, units=None, dtype=None, copy=True, 
                 t_start=0*pq.dimensionless, sampling_rate=None, sampling_period=None,
                 name=None, file_origin=None, description=None, 
                 array_annotations=None, **annotations):
        
        """DataSignal constructor.
        """
        
        DataObject.__init__(self, name=name, file_origin=file_origin, 
                         description=description, 
                         array_annotations=array_annotations, **annotations)
        
        self.__domain_name__ = name_from_unit(self.domain)
        
        if isinstance(name, str):
            self._name_ = name
            
        else:
            self._name_ = name_from_unit(self.units)
    
    def __array_finalize__(self, obj):
        super(DataSignal, self).__array_finalize__(obj)
        
        self._origin            = getattr(obj, "_origin", 0 * pq.dimensionless)
        
        self._sampling_period   = getattr(obj, "_sampling_period", 1 * pq.dimensionless)
        
        self.annotations        = getattr(obj, "annotations",   {})
        self.name               = getattr(obj, "name",          None)
        self.file_origin        = getattr(obj, "file_origin",   None)
        self.description        = getattr(obj, "description",   None)
        #self.channel_index      = getattr(obj, "channel_index", None)
        self.segment            = getattr(obj, "segment",       None)
        self.array_annotations  = getattr(obj, "array_annotations", None)
    
    def __reduce__(self):
        return _new_DataSignal, (self.__class__, 
                                 np.array(self),
                                 self.units, 
                                 self.dtype, 
                                 True,
                                 self.origin, 
                                 self.sampling_period, 
                                 self.sampling_rate,
                                 self.name, 
                                 self.file_origin, 
                                 self.description,
                                 self.annotations,
                                 self.array_annotations,
                                 #self.channel_index,
                                 self.segment)
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        
        new_DS = cls(np.array(self), 
                     units=self.units, 
                     dtype=self.dtype,
                     origin=self._origin, 
                     sampling_period=self._sampling_period,
                     name=self.name,
                     file_origin=self.file_origin, 
                     description=self.description)
        
        new_DS.__dict__.update(self.__dict__)
        memo[id(self)] = new_DS
        
        for k, v in self.__dict__.items():
            try:
                setattr(new_DS, k, deepcopy(v, memo))
                
            except:
                setattr(new_DS, k, v)
                
        return new_DS
    
    def __repr__(self):
        return ('<%s(%s, [%s, %s], sampling period: %s)>' %
                (self.__class__.__name__,
                 super(DataSignal, self).__repr__(), self.origin,
                 self.end, self.sampling_period))
                
    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j)) # NOTE: 2017-11-15 22:24:22 Python3 directly calls __getitem__
    
    def __getitem__(self, i):
        obj = super(DataSignal, self).__getitem__(i)
        if isinstance(i, (int, numbers.Integral, np.integer)): # a single point across all "channels"
            obj = pq.Quantity(obj.magnitude, units = obj.units)
            
        elif isinstance(i, tuple):
            j, k = i
            
            if isinstance(j, (int, numbers.Integral, np.integer)): # => quantity array
                obj = pq.Quantity(obj.magnitude, units=obj.units)
                
            elif isinstance(j, slice):
                if j.start:
                    obj.origin = (self.origin + j.start * self.sampling_period)
                    
                if j.step:
                    obj.sampling_period *= j.step
                        
            elif isinstance(j, np.ndarray): # FIXME TODO
                raise NotImplementedError("%s not suported" % (type(j).__name__))
            
            else:
                raise TypeError("%s not suported" % (type(j).__name__))
            
            if isinstance(k, (int, numbers.Integral, np.integer)):
                obj = obj.reshape(-1,1)
                
            # TODO channel index functionality: see neo/core/analogsignal.py
            
        elif isinstance(i, slice):
            if i.start:
                obj.origin = self.origin + i.start * self.sampling_period
                
        else:
            raise IndexError("Expecting an integer, tuple, or slice")
        
        return obj
    
    def __setitem__(self, i, value):
        if isinstance(i, int):
            i = slice(i, i+1)
            
        elif isinstance(i, tuple):
            j, k = i
            
            if isinstance(k, int):
                i = (j, slice(k, k+1))
                
        return super(DataSignal, self).__setitem__(i, value)
    
    def __eq__(self, other):
        '''
        Equality test (==)
        '''
        if (self.origin != other.origin or
                self.sampling_rate != other.sampling_rate):
            return False
        
        return super(DataSignal, self).__eq__(other)

    def __rsub__(self, other, *args):
        '''
        Backwards subtraction (other-self)
        '''
        return self.__mul__(-1, *args) + other

    def __ne__(self, other):
        '''
        Non-equality test (!=)
        '''
        return not self.__eq__(other)

    def __add__(self, other, *args):
        '''
        Addition (+)
        '''
        return self._apply_operator(other, "__add__", *args)

    def __sub__(self, other, *args):
        '''
        Subtraction (-)
        '''
        return self._apply_operator(other, "__sub__", *args)

    def __mul__(self, other, *args):
        '''
        Multiplication (*)
        '''
        return self._apply_operator(other, "__mul__", *args)

    def __truediv__(self, other, *args):
        '''
        Float division (/)
        '''
        return self._apply_operator(other, "__truediv__", *args)

    def __div__(self, other, *args):
        '''
        Integer division (//)
        '''
        return self._apply_operator(other, "__div__", *args)

    __radd__ = __add__
    __rmul__ = __sub__
    
    def range(self, **kwargs):
        return self.max(**kwargs) - self.min(**kwargs)

    def nanrange(self, **kwargs):
        return self.nanmax(**kwargs) - self.nanmin(**kwargs)
    
    @property
    def origin(self):
        """The domain coordinate of the first data sample in the signal.
        
        A convenience equivalent of neo.AnalogSignal.t_start
        """
        return self._origin
    
    @origin.setter
    def origin(self, value):
        if isinstance(value, pq.Quantity):
            if value.size > 1:
                raise TypeError("Expecting a scalar quantity; got %s instead" % value)
            
            if value.units != self._origin.units:
                warnings.warn("Changin domain units from %s to %s" % (self._origin.units, value.units))
                
            self._origin = value
            
        else:
            raise TypeError("Expecting a scalar quantity; got %s instead" % (type(value).__name__))
    
    @property
    def domain_begin(self):
        """Alias to self.origin
        """
        return self.origin
    
    @property
    def domain_end(self):
        """Alias to self.t_stop, which is an alias to self.domain[-1]
        """
        return self.origin + self.extent
    
    @property
    def t_start(self):
        """The domain coordinate of the first data sample in the signal.
        Alias to self.origin; convenience equivalent of neo.AnalogSignal.t_start
        
        """
        return self.origin
    
    @property
    def t_stop(self):
        """The domain coordinate of the last data sample in the signal.
        Read-only; alias to self.domain_end
        A convenience equivalent of neo.AnalogSignal.t_stop
        """
        return self.domain_end
    
    @t_start.setter
    def t_start(self, value):
        if isinstance(value, pq.Quantity):
            if value.size > 1:
                raise TypeError("Expecting a scalar quantity; got %s instead" % value)
            
            if value.units != self._origin.units:
                warnings.warn("Changin domain units from %s to %s" % (self._origin.units, value.units))
                
            self._origin = value
            
        else:
            raise TypeError("Expecting a scalar quantity; got %s instead" % (type(value).__name__))
    
    @property
    def sampling_period(self):
        return self._sampling_period
    
    @sampling_period.setter
    def sampling_period(self, value):
        if isinstance(value, pq.Quantity):
            if value.units != self.origin.units:
                raise TypeError("Expecting %s units; got %s instead" % (self.units, value.units))
            
            if value.size > 1:
                raise TypeError("Expecting a scalar quantity; got %s instead" % value)
            
            self._sampling_period = value
            
        else:
            raise TypeError("Expecting a python quantity; got %s instead" % (type(value).__name__))
            
    @property
    def sampling_rate(self):
        return 1/self._sampling_period
    
    @sampling_rate.setter
    def sampling_rate(self, value):
        if isinstance(value, pq.Quantity):
            if value.units != 1/self.origin.units:
                raise TypeError("Expecting %s units; got %s instead" % (1/self._origin.units, value.units))
            
            if value.size > 1:
                raise TypeError("Expecting a scalar quantity; got %s instead" % value)
            
            self._sampling_period = 1/value
            
    @property
    def extent(self):
        """The extent of the data domain of the signal, as a quantity.
        
        Also the equivalent of neo.AnalogSignal.duration property. Read-only.
        
        Can be altered indirectly by setting new values for origin, and sampling
        period or sampling rate.
        
        """
        return self.shape[0] * self.sampling_period
    
    @property
    def end(self):
        """The equivalent of neo.AnalogSignal.t_stop
        """
        return self.origin + self.extent
    
    @property
    def name(self):
        return self._name_
    
    @name.setter
    def name(self, val):
        if isinstance(val, str):
            self._name_ = val
    
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
    def extent(self):
        """The extent of this signal in its domain
        """
        return self.shape[0] / self.sampling_rate
    
    @property
    def duration(self):
        """Alias to self extent
        """
        return self.extent
    
    @property
    def domain(self):
        """The domain for the data samples in the signal.
        
        Equivalent to neo.AnalogSignal.times. Read-only.
        
        Can be altered indirectly by setting new values for origin, and sampling
        period or sampling rate.
        
        """
        return self.origin + np.arange(self.shape[0]) * self.sampling_period
    
    @property
    def domain_units(self):
        return self.domain.units
    
    @property
    def times(self):
        """The domain for the data samples in the signal.
        Alias to self.domain
        
        Provided for api compatibility with neo.AnalogSignal
        
        """
        return self.domain
    
    def _apply_operator(self, other, op, *args):
        '''
        Handle copying metadata to the new :class:`BaseSignal`
        after a mathematical operation.
        '''
        self._check_consistency(other)
        f = getattr(super(DataSignal, self), op)
        new_signal = f(other, *args)
        new_signal._copy_data_complement(self)
        return new_signal

    def as_array(self, units=None):
        """
        Return the signal as a plain NumPy array.

        If `units` is specified, first rescale to those units.
        """
        if units:
            return self.rescale(units).magnitude
        else:
            return self.magnitude

    def as_quantity(self):
        """
        Return the signal as a quantities array.
        """
        return self.view(pq.Quantity)
    
    def rescale(self, units):
        """Return a copy of the DataSignal object converted to specified units.
        
        """
        to_dims = pq.quantity.validate_dimensionality(units)
        
        if self.dimensionality == to_dims:
            to_u = self.units
            signal = np.array(self)
            
        else:
            to_u = pq.Quantity(1.0, to_dims)
            from_u = pq.Quantity(1.0, self.dimensionality)
            
            try:
                cf = pq.quantity.get_conversion_factor(from_u, to_u)
                
            except AssertionError:
                raise ValueError('Unable to convert between units of "%s" \
                                 and "%s"' % (from_u._dimensionality,
                                              to_u._dimensionality))
            signal = cf * self.magnitude
            
        obj = self.__class__(signal=signal, units=to_u,
                             sampling_rate=self.sampling_rate)
        
        obj._copy_data_complement(self)
        #obj.channel_index = self.channel_index #
        #obj.segment = self.segment             # FIXME TODO parent container functionality
        obj.annotations.update(self.annotations)

        return obj

    def duplicate_with_new_array(self, signal):
        '''
        Create a new :class:`AnalogSignal` with the same metadata
        but different data
        '''
        #signal is the new signal
        obj = self.__class__(signal=signal, units=self.units,
                             sampling_rate=self.sampling_rate)
        
        obj._copy_data_complement(self)
        obj.annotations.update(self.annotations)
        
        return obj

    def _check_consistency(self, other):
        '''
        Check if the attributes of another :class:`AnalogSignal`
        are compatible with this one.
        '''
        if isinstance(other, DataSignal):
            for attr in "origin", "sampling_rate", "sampling_period":
                if getattr(self, attr) != getattr(other, attr):
                    raise ValueError("Inconsistent values of %s" % attr)
            # how to handle name and annotations?

        # if not an array, then allow the calculation
        if not hasattr(other, 'ndim'):
            return
        # if a scalar array, then allow the calculation
        if not other.ndim:
            return
        # dimensionality should match
        if self.ndim != other.ndim:
            raise ValueError('Dimensionality does not match: %s vs %s' %
                             (self.ndim, other.ndim))
        # if if the other array does not have a times property,
        # then it should be okay to add it directly
        if not hasattr(other, 'times'):
            return

        # if there is a times property, the times need to be the same
        if not (self.times == other.times).all():
            raise ValueError('Times do not match: %s vs %s' %
                             (self.times, other.times))

    def _copy_data_complement(self, other):
        '''
        Copy the metadata from another :class:`AnalogSignal`.
        '''
        for attr in ("origin", "sampling_rate", "sampling_period", "name", "file_origin",
                     "description", "annotations"):
            setattr(self, attr, getattr(other, attr, None))
            
    def interval(self, start, stop):
        '''The equivalent of neo.AnalogSignal.time_slice.
        
        Creates a new AnalogSignal corresponding to the time slice of the
        original AnalogSignal between times t_start, t_stop. Note, that for
        numerical stability reasons if t_start, t_stop do not fall exactly on
        the time bins defined by the sampling_period they will be rounded to
        the nearest sampling bins.
        '''

        # checking start and transforming to start index
        if start is None:
            i = 0
            
        else:
            start = start.rescale(self.sampling_period.units)
            i = (start - self.origin) / self.sampling_period
            i = int(np.rint(i.magnitude))

        # checking stop and transforming to stop index
        if stop is None:
            j = len(self)
            
        else:
            stop = stop.rescale(self.sampling_period.units)
            j = (stop - self.origin) / self.sampling_period
            j = int(np.rint(j.magnitude))

        if (i < 0) or (j > len(self)):
            raise ValueError('Expecting start and stop to be within the analog \
                              signal extent')

        # we're going to send the list of indicies so that we get *copy* of the
        # sliced data
        obj = super(DataSignal, self).__getitem__(np.arange(i, j, 1))
        
        obj.origin = self.origin + i * self.sampling_period

        return obj
    
    def time_slice(self, start, stop):
        """Calls self.interval(start, stop).
        
        Provided for api compatibility with neo.AnalogSignal
        """
        
        return self.interval(start, stop)

    def merge(self, other):
        '''
        Merge another :class:`DataSignal` into this one.

        The :class:`DataSignal` objects are concatenated horizontally
        (column-wise, :func:`np.hstack`).

        If the attributes of the two :class:`DataSignal` are not
        compatible, an Exception is raised.
        '''
        if self.sampling_rate != other.sampling_rate:
            raise MergeError("Cannot merge, different sampling rates")
        
        if self.origin != other.origin:
            raise MergeError("Cannot merge, different origins")
        
        # NOTE: FIXME TODO implement parent container functionality
        #

        if hasattr(self, "lazy_shape"):
            if hasattr(other, "lazy_shape"):
                if self.lazy_shape[0] != other.lazy_shape[0]:
                    raise MergeError("Cannot merge signals of different length.")
                
                merged_lazy_shape = (self.lazy_shape[0], self.lazy_shape[1] + other.lazy_shape[1])
                
            else:
                raise MergeError("Cannot merge a lazy object with a real object.")
            
        if other.units != self.units:
            other = other.rescale(self.units)
            
        stack = np.hstack(map(np.array, (self, other)))
        
        kwargs = {}
        
        for name in ("name", "description", "file_origin"):
            attr_self = getattr(self, name)
            attr_other = getattr(other, name)
            if attr_self == attr_other:
                kwargs[name] = attr_self
            else:
                kwargs[name] = "merge(%s, %s)" % (attr_self, attr_other)
                
        merged_annotations = neo.core.baseneo.merge_annotations(self.annotations,
                                               other.annotations)
        kwargs.update(merged_annotations)
        
        signal = DataSignal(stack, units=self.units, dtype=self.dtype,
                              copy=False, origin=self.origint,
                              sampling_rate=self.sampling_rate,
                              **kwargs)
        
        # NOTE: 2017-11-15 23:34:23 FIXME TODO
        # implement channel index functionality
        #

        if hasattr(self, "lazy_shape"):
            signal.lazy_shape = merged_lazy_shape
            
        return signal

    def downsample(self, downsampling_factor, **kwargs):
        """
        Downsample the data of a signal.
        This method reduces the number of samples of the AnalogSignal to a fraction of the
        original number of samples, defined by `downsampling_factor`.
        This method is a wrapper of scipy.signal.decimate and accepts the same set of keyword
        arguments, except for specifying the axis of resampling, which is fixed to the first axis
        here.

        Parameters:
        -----------
        downsampling_factor: integer
            Factor used for decimation of samples. Scipy recommends to call decimate multiple times
            for downsampling factors higher than 13 when using IIR downsampling (default).

        Returns:
        --------
        downsampled_signal: :class:`AnalogSignal`
            New instance of a :class:`AnalogSignal` object containing the resampled data points.
            The original :class:`AnalogSignal` is not modified.

        Note:
        -----
        For resampling the signal with a fixed number of samples, see `resample` method.
        """

        if not HAVE_SCIPY:
            raise ImportError('Decimating requires availability of scipy.signal')

        # Resampling is only permitted along the time axis (axis=0)
        if 'axis' in kwargs:
            kwargs.pop('axis')

        downsampled_data = scipy.signal.decimate(self.magnitude, downsampling_factor, axis=0,
                                                 **kwargs)
        downsampled_signal = self.duplicate_with_new_data(downsampled_data)

        # since the number of channels stays the same, we can also copy array annotations here
        downsampled_signal.array_annotations = self.array_annotations.copy()
        downsampled_signal.sampling_rate = self.sampling_rate / downsampling_factor

        return downsampled_signal

    def resample(self, sample_count, **kwargs):
        """
        Resample the data points of the signal.
        This method interpolates the signal and returns a new signal with a fixed number of
        samples defined by `sample_count`.
        This method is a wrapper of scipy.signal.resample and accepts the same set of keyword
        arguments, except for specifying the axis of resampling which is fixed to the first axis
        here, and the sample positions. .

        Parameters:
        -----------
        sample_count: integer
            Number of desired samples. The resulting signal starts at the same sample as the
            original and is sampled regularly.

        Returns:
        --------
        resampled_signal: :class:`DataSignal`
            New instance of a :class:`DataSignal` object containing the resampled data points.
            The original :class:`DataSignal` is not modified.

        Note:
        -----
        For reducing the number of samples to a fraction of the original, see `downsample` method
        """

        if not HAVE_SCIPY:
            raise ImportError('Resampling requires availability of scipy.signal')

        # Resampling is only permitted along the time axis (axis=0)
        if 'axis' in kwargs:
            kwargs.pop('axis')
        if 't' in kwargs:
            kwargs.pop('t')

        resampled_data, resampled_times = scipy.signal.resample(self.magnitude, sample_count,
                                                                t=self.times, axis=0, **kwargs)

        resampled_signal = self.duplicate_with_new_data(resampled_data)
        resampled_signal.sampling_rate = (sample_count / self.shape[0]) * self.sampling_rate

        # since the number of channels stays the same, we can also copy array annotations here
        resampled_signal.array_annotations = self.array_annotations.copy()

        return resampled_signal

    def rectify(self, **kwargs):
        """
        Rectify the signal.
        This method rectifies the signal by taking the absolute value.
        This method is a wrapper of numpy.absolute() and accepts the same set of keyword
        arguments.

        Returns:
        --------
        resampled_signal: :class:`DataSignal`
            New instance of a :class:`DataSignal` object containing the rectified data points.
            The original :class:`DataSignal` is not modified.

        """

        # Use numpy to get the absolute value of the signal
        rectified_data = np.absolute(self.magnitude, **kwargs)

        rectified_signal = self.duplicate_with_new_data(rectified_data)

        # the sampling rate stays constant
        rectified_signal.sampling_rate = self.sampling_rate

        # since the number of channels stays the same, we can also copy array annotations here
        rectified_signal.array_annotations = self.array_annotations.copy()

        return rectified_signal

    def concatenate(self, *signals, overwrite:bool=False, padding:bool=False):
        """
        Concatenate multiple DataSignal objects across the domain axis.

        Units, sampling_rate and number of signal traces must be the same
        for all signals. Otherwise a ValueError is raised.
        Note that timestamps of concatenated signals might shift in oder to
        align the sampling times of all signals.

        Parameters
        ----------
        signals: DataSignal objects
            DataSignals that will be concatenated
        overwrite : bool
            If True, samples of the earlier (lower index in `signals`)
            signals are overwritten by that of later (higher index in `signals`)
            signals.
            If False, samples of the later are overwritten by earlier signal.
            Default: False
        padding : bool, scalar quantity
            Sampling values to use as padding in case signals do not overlap.
            If False, do not apply padding. Signals have to align or
            overlap. If True, signals will be padded using
            np.NaN as pad values. If a scalar quantity is provided, this
            will be used for padding. The other signal is moved
            forward in time by maximum one sampling period to
            align the sampling times of both signals.
            Default: False

        Returns
        -------
        signal: DataSignal
            concatenated output signal
        """

        # Sanity of inputs
        if not hasattr(signals, '__iter__'):
            raise TypeError('signals must be iterable')
        if not all([isinstance(a, DataSignal) for a in signals]):
            raise TypeError('Entries of anasiglist have to be of type neo.DataSignal')
        if len(signals) == 0:
            return self

        signals = [self] + list(signals)

        # Check required common attributes: units, sampling_rate and shape[-1]
        shared_attributes = ['units', 'sampling_rate']
        attribute_values = [tuple((getattr(anasig, attr) for attr in shared_attributes))
                            for anasig in signals]
        # add shape dimensions that do not relate to time
        attribute_values = [(attribute_values[i] + (signals[i].shape[1:],))
                            for i in range(len(signals))]
        if not all([attrs == attribute_values[0] for attrs in attribute_values]):
            raise MergeError(
                f'AnalogSignals have to share {shared_attributes} attributes to be concatenated.')
        units, sr, shape = attribute_values[0]

        # find gaps between Analogsignals
        combined_time_ranges = self._concatenate_time_ranges(
            [(s.t_start, s.t_stop) for s in signals])
        missing_time_ranges = self._invert_time_ranges(combined_time_ranges)
        if len(missing_time_ranges):
            diffs = np.diff(np.asarray(missing_time_ranges), axis=1)
        else:
            diffs = []

        if padding is False and any(diffs > signals[0].sampling_period):
            raise MergeError(f'Signals are not continuous. Can not concatenate signals with gaps. '
                             f'Please provide a padding value.')
        if padding is not False:
            logger.warning('Signals will be padded using {}.'.format(padding))
            if padding is True:
                padding = np.NaN * units
            if isinstance(padding, pq.Quantity):
                padding = padding.rescale(units).magnitude
            else:
                raise MergeError('Invalid type of padding value. Please provide a bool value '
                                 'or a quantities object.')

        t_start = min([a.t_start for a in signals])
        t_stop = max([a.t_stop for a in signals])
        n_samples = int(np.rint(((t_stop - t_start) * sr).rescale('dimensionless').magnitude))
        shape = (n_samples,) + shape

        # Collect attributes and annotations across all concatenated signals
        kwargs = {}
        common_annotations = signals[0].annotations
        common_array_annotations = signals[0].array_annotations
        for anasig in signals[1:]:
            common_annotations = intersect_annotations(common_annotations, anasig.annotations)
            common_array_annotations = intersect_annotations(common_array_annotations,
                                                             anasig.array_annotations)

        kwargs['annotations'] = common_annotations
        kwargs['array_annotations'] = common_array_annotations

        for name in ("name", "description", "file_origin"):
            attr = [getattr(s, name) for s in signals]
            if all([a == attr[0] for a in attr]):
                kwargs[name] = attr[0]
            else:
                kwargs[name] = f'concatenation ({attr})'

        conc_signal = DataSignal(np.full(shape=shape, fill_value=padding, dtype=signals[0].dtype),
                                   sampling_rate=sr, t_start=t_start, units=units, **kwargs)

        if not overwrite:
            signals = signals[::-1]
        while len(signals) > 0:
            conc_signal.splice(signals.pop(0), copy=False)

        return conc_signal

    def _concatenate_time_ranges(self, time_ranges):
        time_ranges = sorted(time_ranges)
        new_ranges = time_ranges[:1]
        for t_start, t_stop in time_ranges[1:]:
            # time range are non continuous -> define new range
            if t_start > new_ranges[-1][1]:
                new_ranges.append((t_start, t_stop))
            # time range is continuous -> extend time range
            elif t_stop > new_ranges[-1][1]:
                new_ranges[-1] = (new_ranges[-1][0], t_stop)
        return new_ranges

    def _invert_time_ranges(self, time_ranges):
        i = 0
        new_ranges = []
        while i < len(time_ranges) - 1:
            new_ranges.append((time_ranges[i][1], time_ranges[i + 1][0]))
            i += 1
        return new_ranges

class IrregularlySampledDataSignal(BaseSignal):
    """Almost literal copy of the neo.IrregularlySampledSignal, accepting a domain other than time
    """
    _single_parent_objects = ("Segment", "ChannelIndex") 
    
    _quantity_attr = 'signal'
    
    _necessary_attrs = (('signal', pq.Quantity, 2),
                        ('sampling_period', pq.Quantity, 0),
                        ('origin', pq.Quantity, 0))
    
    _recommended_attrs = neo.baseneo.BaseNeo._recommended_attrs

    def __new__(cls, domain, signal, units=None, domain_units=None, time_units=None,
                dtype=np.dtype("float64"), 
                copy=True, name=None, file_origin=None, description=None, 
                array_annotations=None, **annotations):
        
        if units is None:
            if not hasattr(signal, "units"):
                units = pq.dimensionless
                
        elif isinstance(signal, pq.Quantity):
            if units != signal.units:
                signal = signal.rescale(units)
                
        obj = pq.Quantity(signal, units=units, dtype=dtype, copy=copy).view(cls)

        if obj.ndim == 1:
            obj.shape = (-1,1)

            
        if domain_units is None:
            if isinstance(time_units, pq.Quantity):
                domain_units = time_units

            elif hasattr(domain, "units"):
                domain_units = domain.units
                
            else:
                raise TypeError("Domain units must be specified")
            
        elif isinstance(domain, pq.Quantity):
            if domain_units != domain.units:
                domain = domain.rescale(domain_units)
                
        obj._domain = pq.Quantity(domain, units = domain_units,
                                  dtype=float, copy=copy)
                
        obj.segment=None
        #obj.channel_index=None

        return obj
                
    def __init__(self, domain, signal, units=None, domain_units=None, time_units=None,
                 dtype=None, copy=True, name=None, file_origin=None, description=None,
                 array_annotations=None, **annotations):
        DataObject.__init__(self, name=name, file_origin=file_origin,
                            desciption=description, 
                            array_annotations=array_annotations,
                            **annotations)
        #baseneo.BaseNeo.__init__(self, name=name, file_origin=file_origin,
                                 #description=description, **annotations)
        
        self.__domain_name__ = name_from_unit(self._domain)
        
        if isinstance(name, str):
            self._name_ = name
        else:
            self._name_ = name_from_unit(self.units)
    
    def __reduce__(self):
        return _new_IrregularlySampledDataSignal, (self.__class__,
                                                   self._domain,
                                                   np.array(self),
                                                   self.units,
                                                   self.domain.units,
                                                   self.dtype,
                                                   True,
                                                   self.name,
                                                   self.file_origin,
                                                   self.description,
                                                   self.annotations,
                                                   self.array_annotations,
                                                   #self.channel_index,
                                                   self.segment,
                                                   )
    
    def __array_finalize__(self, obj):
        super(DataSignal, self).__array_finalize__(obj)
        self._domain = getattr(obj, "_domain", None)
        self.annotations        = getattr(obj, "annotations",   {})
        self.name               = getattr(obj, "name",          None)
        self.file_origin        = getattr(obj, "file_origin",   None)
        self.description        = getattr(obj, "description",   None)
        self.segment            = getattr(obj, "segment",       None)
        #self.channel_index      = getattr(obj, "channel_index", None)
        self.array_annotations  = getattr(obj, "array_annotations", None)
        self.__domain_name__    = name_from_unit(self._domain)
        
    def __deepcopy__(self, memo):
        cls = self.__class__
        new_signal = cls(self.domain, np.array(self), units=self.units,
                         domain_units=self.domain.units, dtype=self.dtype,
                         name=self.name, file_origin=self.file_origin, 
                         description=self.description,
                         array_annotations=self.array_annotations,
                         annotations = self.annotations)
        new_signal.__dict__.update(self.__dict__)
        memo[id(self)] = new_signal
        for k, v in self.__dict__.items():
            try:
                setattr(new_signal, k, deepcopy(v, memo))
            except TypeError:
                setattr(new_signal, k, v)
        return new_signal

    def __repr__(self):
        '''
        Returns a string representing the :class:`IrregularlySampledDataSignal`.
        '''
        #super_repr = super().__repr__()
        
        with np.printoptions(precision=2, linewidth=1000):
            values_str_list = self.as_array().__repr__().replace("array(", "").replace(")", "").replace("[[", "[").replace("]]", "]").replace(",", "").split("\n")
            
            times_str_list = np.array(self.times).__repr__().replace("array(", "").replace(")", "").replace("[", "").replace("]", "").replace(",", "").split()
            
            max_len = max([len(s) for s in times_str_list])
            
            repr_str_list = ["%s       %s" % (times_str_list[k].rjust(max_len), values_str_list[k].lstrip()) for k in range(len(times_str_list))]
            
        repr_str_list.insert(0, "%s       %s" % ("Domain", "Signal"))
        repr_str_list.append("* %s       * %s" % (self.times.units, self.units))
        
        ret = ["%s" % self.__class__.__name__] + repr_str_list
        
        return "\n".join(ret)
        
        #return '<%s(%s at domain %s)>' % (self.__class__.__name__,
                                         #super().__repr__(), self.domain)

    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j)) # NOTE: 2017-11-15 22:24:22 Python3 directly calls __getitem__
    
    def __getitem__(self, i):
        '''
        Get the item or slice :attr:`i`.
        '''
        obj = super(IrregularlySampledDataSignal, self).__getitem__(i)
        
        if isinstance(i, (int, np.integer)):  # a single point in time across all channels
            obj = pq.Quantity(obj.magnitude, units=obj.units)
            
        elif isinstance(i, tuple):
            j, k = i
            
            if isinstance(j, (int, np.integer)):  # a single point in time across some channels
                obj = pq.Quantity(obj.magnitude, units=obj.units)
                
            else:
                if isinstance(j, slice):
                    obj._domain = self._domain.__getitem__(j)
                    
                elif isinstance(j, np.ndarray):
                    # FIXME / TODO
                    raise NotImplementedError("Arrays not yet supported")
                
                else:
                    raise TypeError("%s not supported" % type(j))
                
                if isinstance(k, (int, np.integer)):
                    obj = obj.reshape(-1, 1)
                    # add if channel_index
        elif isinstance(i, slice):
            obj._domain = self.times.__getitem__(i)
            
        else:
            raise IndexError("index should be an integer, tuple or slice")
        return obj

    def __setitem__(self, i, value):
        if isinstance(i, int):
            i = slice(i, i+1)
            
        elif isinstance(i, tuple):
            j, k = i
            
            if isinstance(k, int):
                i = (j, slice(k, k+1))
                
        return super(IrregularlySampledDataSignal, self).__setitem__(i, value)
    
    def __eq__(self, other):
        '''
        Equality test (==)
        '''
        
        if len(self) != len(other):
            return False
        
        if self.ndim != other.ndim:
            return False
        
        if self.shape != other.shape:
            return False
        
        return (super(IrregularlySampledDataSignal, self).__eq__(other).all() and
                (self.times == other.times).all())

        #if (self.origin != other.origin or
                #self.sampling_rate != other.sampling_rate):
            #return False
        
        #return super(DataSignal, self).__eq__(other)

    def __rsub__(self, other, *args):
        '''
        Backwards subtraction (other-self)
        '''
        return self.__mul__(-1, *args) + other

    def __ne__(self, other):
        '''
        Non-equality test (!=)
        '''
        return not self.__eq__(other)

    def __add__(self, other, *args):
        '''
        Addition (+)
        '''
        return self._apply_operator(other, "__add__", *args)

    def __sub__(self, other, *args):
        '''
        Subtraction (-)
        '''
        return self._apply_operator(other, "__sub__", *args)

    def __mul__(self, other, *args):
        '''
        Multiplication (*)
        '''
        return self._apply_operator(other, "__mul__", *args)

    def __truediv__(self, other, *args):
        '''
        Float division (/)
        '''
        return self._apply_operator(other, "__truediv__", *args)

    def __div__(self, other, *args):
        '''
        Integer division (//)
        '''
        return self._apply_operator(other, "__div__", *args)

    __radd__ = __add__
    __rmul__ = __sub__
    
    def mean(self, interpolation=None):
        """
        TODO interpolation
        """
        if interpolation is None:
            return np.sum(self[:-1] * self.sampling_intervals.reshape(-1, 1), axis=1) / self.duration
        else:
            raise NotImplementedError
        
    def nanmean(self, interpolation=None):
        """
        TODO: Interpolation
        """
        if interpolation is None:
            return np.nansum(self[:-1] * self.sampling_intervals.reshape(-1, 1), axis=1) / self.duration
            
        else:
            raise NotImplementedError

    def resample(self, sample_count, **kwargs):
        """
        Resample the data points of the signal.
        This method interpolates the signal and returns a new signal with a fixed number of
        samples defined by `sample_count`.
        This function is a wrapper of scipy.signal.resample and accepts the same set of keyword
        arguments, except for specifying the axis of resampling which is fixed to the first axis
        here, and the sample positions. .

        Parameters:
        -----------
        sample_count: integer
            Number of desired samples. The resulting signal starts at the same sample as the
            original and is sampled regularly.

        Returns:
        --------
        resampled_signal: :class:`DataSignal`
            New instance of a :class:`DataSignal` object containing the resampled data points.
            The original :class:`IrregularlySampledDataSignal` is not modified.
        """

        if not HAVE_SCIPY:
            raise ImportError('Resampling requires availability of scipy.signal')

        # Resampling is only permitted along the time axis (axis=0)
        if 'axis' in kwargs:
            kwargs.pop('axis')
        if 't' in kwargs:
            kwargs.pop('t')

        resampled_data, resampled_times = scipy.signal.resample(self.magnitude, sample_count,
                                                                t=self.times.magnitude,
                                                                axis=0, **kwargs)

        new_sampling_rate = (sample_count - 1) / self.duration
        resampled_signal = DataSignal(resampled_data, units=self.units, dtype=self.dtype,
                                        t_start=self.t_start,
                                        sampling_rate=new_sampling_rate,
                                        array_annotations=self.array_annotations.copy(),
                                        **self.annotations.copy())

        # since the number of channels stays the same, we can also copy array annotations here
        resampled_signal.array_annotations = self.array_annotations.copy()
        return resampled_signal

    def resample_interp(self, at=None, interpolation=None):
        '''
        TODO
        Resample the signal, returning either an :class:`DataSignal` object
        or another :class:`IrregularlySampledDataSignal` object.

        Arguments:
            :at: either a :class:`Quantity` array containing the times at
                 which samples should be created (times must be within the
                 signal duration, there is no extrapolation), a sampling rate
                 with dimensions (1/Time) or a sampling interval
                 with dimensions (Time).
            :interpolation: one of: None, 'linear'
        '''
        # further interpolation methods could be added
        raise NotImplementedError
    
    def time_shift(self, t_shift):
        """
        Shifts a :class:`IrregularlySampledSignal` to start at a new time.

        Parameters:
        -----------
        t_shift: Quantity (time)
            Amount of time by which to shift the :class:`IrregularlySampledSignal`.

        Returns:
        --------
        new_sig: :class:`SpikeTrain`
            New instance of a :class:`IrregularlySampledSignal` object
            starting at t_shift later than the original :class:`IrregularlySampledSignal`
            (the original :class:`IrregularlySampledSignal` is not modified).
        """
        new_sig = deepcopy(self)

        new_sig.times += t_shift

        return new_sig

    @property
    def sampling_intervals(self):
        '''
        Interval between each adjacent pair of samples.

        (:attr:`times[1:]` - :attr:`times`[:-1])
        '''
        return self.domain[1:] - self.domain[:-1]

    @property
    def domain_begin(self):
        return self.domain[0]
    
    @property
    def domain_end(self):
        return self.domain[-1]
    
    @property
    def t_start(self):
        """The domain coordinate of the first data sample in the signal.
        A convenience equivalent of neo.AnalogSignal.t_start
        
        Read-only
        
        """
        return self.domain_begin
    
    @property
    def t_stop(self):
        """The domain coordinate of the last data sample in the signal.
        
        A convenience equivalent of neo.AnalogSignal.t_stop
        
        Read-only
        
        """
        
        return self.domain_end
    
    def range(self, **kwargs):
        return self.max(**kwargs) - self.min(**kwargs)

    def nanrange(self, **kwargs):
        return self.nanmax(**kwargs) - self.nanmin(**kwargs)
    
    @property
    def extent(self):
        """The extent of the data domain of the signal, as a quantity.
        
        Also the equivalent of neo.AnalogSignal.duration property. Read-only.
        
        Can be altered indirectly by setting new values for origin, and sampling
        period or sampling rate.
        
        """
        return self.domain[-1] - self.domain[0]
    
    @property
    def duration(self):
        return self.extent
    
    @property
    def end(self):
        """The equivalent of neo.AnalogSignal.t_stop
        """
        return self.domain[0] + self.extent
    
    @property
    def name(self):
        return self._name_
    
    @name.setter
    def name(self, val):
        if isinstance(val, str):
            self._name_ = val
    
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
    def domain(self):
        """The domain coordinate for the data samples in the signal.
        
        Equivalent to neo.AnalogSignal.times. 
        
        """
        return self._domain.flatten()
    
    @domain.setter
    def domain(self, value):
        if isinstance(value, np.ndarray):
            if value.ndim > 2 or (value.ndim==2 and value.shape[1]) > 1:
                raise ValueError("New domain must be a vector")
            
            if len(value) != len(self):
                raise ValueError("new domain has incompatible length (%d); expecting %d" % (len(value), len(self)))
            
            if isinstance(value, pq.Quantity):
                if not units_convertible(value, self.domain.units):
                    raise TypeError("incompatible units (%s) for new domain; expecting %s" % (value.units.dimensionality, self.domain.units.dimensionality))
                
                if value.units != self.domain.units:
                    value = value.rescale(self.domain.units)
                    
            else:
                value *= self.domain.units
                    
        else:
            raise TypeError("Expecting a numy arrtay or a quantity; got %s instead" % type(value).__name__)
        
        self._domain = value
    
    @property
    def domain_units(self):
        return self.domain.units
    
    @property
    def times(self):
        """The domain coordinate for the data samples in the signal.
        
        Provided for api compatibility with neo.AnalogSignal
        
        Return self.domain
        
        """
        return self.domain
    
    @times.setter
    def times(self, value):
        self.domain=value
    
    def _apply_operator(self, other, op, *args):
        '''
        Handle copying metadata to the new :class:`BaseSignal`
        after a mathematical operation.
        '''
        #print(op)
        self._check_consistency(other)
        f = getattr(super(IrregularlySampledDataSignal, self), op)
        new_signal = f(other, *args)
        new_signal._copy_data_complement(self)
        return new_signal

    def as_array(self, units=None):
        """
        Return the signal as a plain NumPy array.

        If `units` is specified, first rescale to those units.
        """
        if units:
            return self.rescale(units).magnitude
        else:
            return self.magnitude

    def as_quantity(self):
        """
        Return the signal as a quantities array.
        """
        return self.view(pq.Quantity)
    
    def rescale(self, units):
        """Return a copy of the DataSignal object converted to specified units.
        
        """
        to_dims = pq.quantity.validate_dimensionality(units)
        
        if self.dimensionality == to_dims:
            to_u = self.units
            signal = np.array(self)
            
        else:
            to_u = pq.Quantity(1.0, to_dims)
            from_u = pq.Quantity(1.0, self.dimensionality)
            
            try:
                cf = pq.quantity.get_conversion_factor(from_u, to_u)
                
            except AssertionError:
                raise ValueError('Unable to convert between units of "%s" \
                                 and "%s"' % (from_u._dimensionality,
                                              to_u._dimensionality))
            signal = cf * self.magnitude
            
        obj = self.__class__(domain=self.domain, signal=signal, units=to_u)
        
        obj._copy_data_complement(self)
        #obj.channel_index = self.channel_index 
        #obj.segment = self.segment             # FIXME TODO parent container functionality
        obj.annotations.update(self.annotations)

        return obj

    def duplicate_with_new_array(self, signal):
        '''
        Create a new :class:`IrregularlySampledDataSignal` with the same metadata
        but different data
        '''
        #signal is the new signal
        obj = self.__class__(domain=signal.domain, signal=signal, units=self.units)
        
        obj._copy_data_complement(self)
        obj.annotations.update(self.annotations)
        
        return obj

    def _check_consistency(self, other):
        '''
        Check if the attributes of another :class:`IrregularlySampledDataSignal`
        are compatible with this one.
        '''
        if isinstance(other, IrregularlySampledDataSignal):
            for attr in ("domain", "units", "domain_units"):
                if getattr(self, attr) != getattr(other, attr):
                    raise ValueError("Inconsistent values of %s" % attr)
            # how to handle name and annotations?

    def _copy_data_complement(self, other):
        '''
        Copy the metadata from another :class:`IrregularlySampledDataSignal`.
        '''
        for attr in ("origin", "name", "file_origin", "domain", "units", "domain_units",
                     "description", "annotations", "array_annotations"):
            setattr(self, attr, getattr(other, attr, None))
            
    def interval(self, start, stop):
        '''The equivalent of neo.AnalogSignal.time_slice.
        
        '''

        # checking start and transforming to start index
        if start is None:
            i = 0
            
        else:
            start = start.rescale(self.domain.units)
            i = np.where(np.isclose(self.domain, start))[0]
            if len(i):
                i = i[0]
                
            else:
                raise ValueError("domain value %s not found" % start)

        # checking stop and transforming to stop index
        if stop is None:
            j = len(self)
            
        else:
            stop = stop.rescale(self.sampling_period.units)
            j = np.where(np.isclose(self.domain, stop))[0]
            if len(j):
                j = j[-1]
                
            else:
                raise ValueError("domain value %s not found" % stop)

        if (i < 0) or (j > len(self)):
            raise ValueError('Expecting start and stop to be within the analog \
                              signal extent')

        # we're going to send the list of indicies so that we get *copy* of the
        # sliced data
        obj = super(IrregularlySampledDataSignal, self).__getitem__(np.arange(i, j, 1))
        
        return obj
    
    def time_slice(self, start, stop):
        """Calls self.interval(start, stop).
        
        Provided for api compatibility with neo.AnalogSignal
        """
        
        return self.interval(start, stop)

    def concatenate(self, other, allow_overlap=False):
        '''
        Combine this and another signal along the time axis.

        The signal objects are concatenated vertically
        (row-wise, :func:`np.vstack`). Patching can be
        used to combine signals across segments.
        Note: Only array annotations common to
        both signals are attached to the concatenated signal.

        If the attributes of the two signal are not
        compatible, an Exception is raised.

        Required attributes of the signal are used.

        Parameters
        ----------
        other : neo.BaseSignal
            The object that is merged into this one.
        allow_overlap : bool
            If false, overlapping samples between the two
            signals are not permitted and an ValueError is raised.
            If true, no check for overlapping samples is
            performed and all samples are combined.

        Returns
        -------
        signal : neo.IrregularlySampledDataSignal
            Signal containing all non-overlapping samples of
            both source signals.

        Raises
        ------
        MergeError
            If `other` object has incompatible attributes.
        '''

        for attr in self._necessary_attrs:
            if not (attr[0] in ['signal', 'times', 't_start', 't_stop', 'times']):
                if getattr(self, attr[0], None) != getattr(other, attr[0], None):
                    raise MergeError(
                        "Cannot concatenate these two signals as the %s differ." % attr[0])

        if hasattr(self, "lazy_shape"):
            if hasattr(other, "lazy_shape"):
                if self.lazy_shape[-1] != other.lazy_shape[-1]:
                    raise MergeError("Cannot concatenate signals as they contain"
                                     " different numbers of traces.")
                merged_lazy_shape = (self.lazy_shape[0] + other.lazy_shape[0], self.lazy_shape[-1])
            else:
                raise MergeError("Cannot concatenate a lazy object with a real object.")
        if other.units != self.units:
            other = other.rescale(self.units)

        new_times = np.hstack((self.times, other.times))
        sorting = np.argsort(new_times)
        new_samples = np.vstack((self.magnitude, other.magnitude))

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

        kwargs['array_annotations'] = intersect_annotations(self.array_annotations,
                                                            other.array_annotations)

        if not allow_overlap:
            if max(self.t_start, other.t_start) <= min(self.t_stop, other.t_stop):
                raise ValueError('Can not combine signals that overlap in time. Allow for '
                                 'overlapping samples using the "no_overlap" parameter.')

        t_start = min(self.t_start, other.t_start)
        t_stop = max(self.t_start, other.t_start)

        signal = IrregularlySampledDataSignal(signal=new_samples[sorting], times=new_times[sorting],
                                          units=self.units, dtype=self.dtype, copy=False,
                                          t_start=t_start, t_stop=t_stop, **kwargs)
        signal.segment = None

        if hasattr(self, "lazy_shape"):
            signal.lazy_shape = merged_lazy_shape

        return signal
    
    def merge(self, other):
        '''
        Merge another signal into this one.

        The signal objects are concatenated horizontally
        (column-wise, :func:`np.hstack`).

        If the attributes of the two signals are not
        compatible, an Exception is raised.

        Required attributes of the signal are used.
        '''

        if not np.array_equal(self.times, other.times):
            raise MergeError("Cannot merge these two signals as the sample times differ.")

        if self.segment != other.segment:
            raise MergeError(
                "Cannot merge these two signals as they belong to different segments.")
        if hasattr(self, "lazy_shape"):
            if hasattr(other, "lazy_shape"):
                if self.lazy_shape[0] != other.lazy_shape[0]:
                    raise MergeError("Cannot merge signals of different length.")
                merged_lazy_shape = (self.lazy_shape[0], self.lazy_shape[1] + other.lazy_shape[1])
            else:
                raise MergeError("Cannot merge a lazy object with a real object.")
        if other.units != self.units:
            other = other.rescale(self.units)
        stack = np.hstack((self.magnitude, other.magnitude))
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

        signal = self.__class__(self.times, stack, units=self.units, dtype=self.dtype,
                                copy=False, **kwargs)
        signal.segment = self.segment
        signal.array_annotate(**self._merge_array_annotations(other))

        if hasattr(self, "lazy_shape"):
            signal.lazy_shape = merged_lazy_shape

        return signal

