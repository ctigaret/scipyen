# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

from copy import deepcopy
import numbers, warnings, typing
import numpy as np

import quantities as pq

import neo
from neo.core import baseneo
from neo.core.baseneo import BaseNeo
from neo.core import basesignal
from neo.core.basesignal import BaseSignal
from neo.core import container
from neo.core.dataobject import DataObject, ArrayDict

from core.quantities import (unitsConvertible, nameFromUnit)
from core.strutils import is_path #, is_pathname_valid


def _new_DataSignal(cls, signal, units=None, domain_units=None, dtype=None, domain_dtype=None, copy=True,t_start=0*pq.dimensionless, sampling_period=None,sampling_rate=None, name=None, domain_name=None, file_origin=None,description=None, array_annotations=None, annotations=None,segment=None):
    if not isinstance(array_annotations, ArrayDict):
        array_annotations = ArrayDict(signal.shape[-1])
        
    if not isinstance(annotations, dict):
        if annotations is None:
            annotations = dict()
        else:
            try:
                annotations = dict(annotations)
            except:
                annotations = dict() # just so that we aren't left hanging out
                
    obj = cls(signal=signal, units=units, domain_units=domain_units, dtype=dtype, copy=copy,
              t_start=t_start, sampling_period=sampling_period, sampling_rate=sampling_rate,
              name=name, domain_name=domain_name,file_origin=file_origin, description=description,
              array_annotations=array_annotations,
              **annotations)
    
    #obj.channel_index = channel_index
    obj.segment = segment
    
    return obj

def _new_IrregularlySampledDataSignal(cls, domain, signal, units=None, domain_units=None, dtype=None, domain_dtype=None, copy=True, name=None,domain_name=None,file_origin=None,description=None,array_annotations=None,annotations=None,segment=None):
    if not isinstance(array_annotations, ArrayDict):
        array_annotations = ArrayDict(signal.shape[-1])
        
    if not isinstance(annotations, dict):
        if annotations is None:
            annotations = dict()
        else:
            try:
                annotations = dict(annotations)
            except:
                annotations = dict() # just so that we aren't left hanging out
                
    obj = cls(domain=domain,signal=signal,units=units,domain_units=domain_units,
              dtype=dtype,copy=copy,name=name,domain_name=domain_name,file_origin=file_origin,
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
    #_single_parent_objects = ("Segment", "ChannelIndex") 
    
    _parent_objects = ('Segment',)
    _parent_attrs = ('segment',)
    _quantity_attr = 'signal' # ?!? FIXME/TODO 

    _necessary_attrs = (('signal', pq.Quantity, 2),
                        ('sampling_period', pq.Quantity, 0),
                        ('origin', pq.Quantity, 0))
    
    _recommended_attrs = neo.baseneo.BaseNeo._recommended_attrs

    def __new__(cls, signal, units=None, domain_units=None, time_units = None, dtype=np.dtype("float64"), copy=True, t_start=0*pq.dimensionless, sampling_period=None, sampling_rate=None, name=None, domain_name=None, file_origin=None, description=None, array_annotations=None, **annotations):
        # NOTE: 2021-12-09 21:45:08 try & sort out the mess from pickles saved with prev APIs
        # WARNING: This is NOT guaranteed to succeed
        # if trying to load an old pickle fails, you're better off going to the
        # original data and re-analyse!
        #
        # What we need to set up here are the following:
        # • the data itself (as a Quantity) - needs `units`, `dtype`, `copy`
        # • attribute `segment`
        #
        # Hence we pick only the relevant named params here (all others are 
        # passed by Python to __init__ anyway)
        
        quants = {"units": None}
        
        dtypes = {"dtype":None}
        
        bools = {"copy": True}
        
        call_arg_names = ("units", "dtype")
        
        segment = None
        
        # take attributes from signal, if possible, then overwrite them with
        # passed arguments if not None
        if isinstance(signal, (neo.AnalogSignal, DataSignal)):
            call_args = dict((name, getattr(signal, name, None)) for name in call_arg_names)
            call_args["copy"] = copy
            segment = signal.segment
        elif isinstance(signal, (tuple, list)):
            signal = np.atleast_2d(np.array(signal))
            call_args = {"copy": copy}
            # call_args = dict((name, getattr(signal, name, None)) for name in call_arg_names)
            # call_args["copy"] = copy
            # segment = signal.segment
        else:    
            call_args = dict()
        
        # NOTE: 2022-11-24 11:57:08
        # see NOTE: 2022-11-24 11:59:04 and NOTE: 2022-11-24 11:22:34 for the logic
        for v in call_arg_names + ("copy",):
            val = eval(v)
            if v in call_args:
                if call_args[v] is None and val is not None:
                    call_args[v] = val
            else:
                call_args[v] = val
            
        # print(f"call_args {call_args}")
        # distribute call args 
        for k,v in call_args.items():
            if isinstance(v, bool): # there is only one bool arg expected
                bools["copy"] = v
                
            elif isinstance(v, np.dtype): # there is only one dtype arg expected
                dtypes["dtype"] = v

            elif isinstance(v, pq.Quantity):
                if v.size == 1: # a scalar ; note signal is treated from the outset
                    quants["units"] = v
                    
        if quants["units"] is None:
            quants["units"] = pq.dimensionless
            
        if isinstance(signal, pq.Quantity):
            if quants["units"].units != signal.units:
                signal = signal.rescale(quants["units"].units)
                            
        obj = pq.Quantity(signal, 
                          units=quants["units"].units, 
                          dtype=dtypes["dtype"], 
                          copy=bools["copy"]).view(cls)
        
        if obj.ndim == 1:
            obj.shape = (-1,1)
            
        obj.segment = segment
        
        # NOTE: 2022-11-24 12:13:04
        # obj.channel_index=None 

        return obj
    
    def __init__(self, signal, units=None, domain_units = None, time_units = None, dtype=None, copy=True, t_start=0*pq.dimensionless, sampling_rate=None, sampling_period=None, name=None, domain_name = None, file_origin=None, description=None, array_annotations=None, **annotations):
        
        """DataSignal constructor.
        """
        # ATTENTION: __init__ is called AFTER __new__ so `self` is already 
        # partly initialized here !!!
        # In particular, it SHOULD already contain:
        # • the data itself (as a Quantity)
        # • attribute `segment`
        # 
        # we need to deal with thing again because __class__(...) jumps right
        # to init (see e.g., rescale)
        
        strings  = {"name":None, "domain_name":None, "file_origin":None, "description": None}
        
        quants = {"units": None, "domain_units": None, "time_units": None}
        
        domainargs = {"t_start": None, "sampling_period":None, "sampling_rate":None}
        
        annots    = {"array_annotations":None, "annotations": None}
        
        dtypes   = {"dtype":None} # dealt with in __new__
        
        bools = {"copy": None} # dealt with in __new__
        
        call_arg_names = ("units", "domain_units", "time_units", "dtype", "t_start",
                          "sampling_period", "sampling_rate", "name", 
                          "file_origin", "description", "array_annotations",
                          "annotations")
        
        
        # take attributes from signal, if possible, then overwrite them with
        # passed arguments if not None
        if isinstance(signal, (neo.AnalogSignal, DataSignal)):
            call_args = dict((name, getattr(signal, name, None)) for name in call_arg_names)
            call_args["copy"] = True 
            call_args["domain_units"] = getattr(signal, "t_start", 0.*pq.s).units
            
        elif isinstance(signal, (tuple, list)):
            signal = np.atleast_2d(np.array(signal))
            call_args = dict((name, getattr(signal, name, None)) for name in call_arg_names)
            call_args["copy"] = True 
            call_args["domain_units"] = getattr(signal, "t_start", 0.*pq.s).units
        else:    
            call_args = dict()
        
        # NOTE: 2022-11-24 11:59:04
        # check if a value is assigned to a call arg (i.e. is not None)
        # • call arg is in the dict AND is mapped to None then:
        #   ∘ if the corresponding named param supplies a value, use that value
        #       — NOTE that if the call arg has a value taken from corresponding
        #           attribute of signal, this will be overwritten ONLY if
        #           the corresponding named param is not None
        # • otherwise, use whatever value the corresponding named param has
        #
        # NOTE: 2022-11-24 11:22:34 IN OTHER WORDS:
        # check if param already in call_args, probably taken from signal
        # • if not there, then assign the value passed as named parameter for the call
        # • if there, only replace if the value from signal is not None AND the 
        #   named param supplied to the call is not None
        #   → this is so that we don't overwrite the value taken from signal
        for v in call_arg_names:
            val = eval(v) # evals locally, so available only if given as named param 
            # print(f"\t{v} = {val}")
            if v in call_args: 
                if call_args[v] is None and val is not None:
                    # only replace with named param if value in call_args is None
                    # and val is not None; else, leave it as None anyway
                    call_args[v] = val
            else: # param not there hence add it
                call_args[v] = val
            
        # NOTE: 2022-11-24 12:10:17
        # distribute call args in categories
        for k,v in call_args.items():
            if isinstance(v, bool): # there is only one bool arg expected
                bools["copy"] = v
                
            elif isinstance(v, np.dtype): # there is only one dtype arg expected
                if k in ("dtype", "domain_dtype"):
                    dtypes[k] = v

            elif isinstance(v, str):
                if k == "file_origin" and is_path(v):
                    # likely a file path name
                    strings["file_origin"] = v
                    
                elif k in ("name", "domain_name", "description"):
                    strings[k] = v
                    
            elif isinstance(v, dict):
                if isinstance(v, ArrayDict): # only array_annotations are ArrayDict
                    annots["array_annotations"] = v
                    
                elif isinstance(v, dict): # can be array_annotations or anotations; brrr...
                    if len(v) == signal.shape[1]: # likely array annotations, too
                        if annots["array_annotations"] is None:
                            arr_ann = ArrayDict(signal.shape[1])
                            for ka,va in v.items():
                                arr_ann[ka] = va
                            annots["array_annotations"] = arr_ann
                        else:
                            annots["annotations"] = v
                            
                    else:
                        annots["annotations"] = v
                        
            elif isinstance(v, pq.Quantity):
                if v.size == 1: # a scalar ; note signal is treated from the outset
                    # precedence: units, domain_units, t_start, sampling_period, sampling_rate
                    if k in ("units", "domain_units", "time_units"):
                        quants[k] = v.units # not needed -- supplied at __new__
                    elif k in ("t_start", "sampling_period", "sampling_rate"):
                        domainargs[k] = v
                        
        # harmonize time_units with domain_units
        if quants["domain_units"] is None:
            quants["domain_units"] = quants["time_units"]
        # print(f"{self.__class__.__name__}.__init__ call_args {call_args}\n")
        # print(f"{self.__class__.__name__}.__init__ strings {strings}\n")
        # print(f"{self.__class__.__name__}.__init__ quants {quants}\n")
        # print(f"{self.__class__.__name__}.__init__ domainargs {domainargs}\n")
        # print(f"{self.__class__.__name__}.__init__ annots {annots}\n")
        
        if isinstance(domainargs["sampling_period"], pq.Quantity):
            #print("sampling_period", domainargs["sampling_period"])
            if unitsConvertible(1/domainargs["sampling_period"], quants["domain_units"]):
                domainargs["sampling_rate"] = domainargs["sampling_period"]
                domainargs["sampling_period"] = 1/domainargs["sampling_period"]
        else:
            if not isinstance(domainargs["t_start"], pq.Quantity):
                domainargs["t_start"] = 0*pq.dimensionless

            domainargs["sampling_period"] = 1 * domainargs["t_start"].units
                
        # else:
        #     sp = domainargs["sampling_period"]
            
                
        if isinstance(domainargs["sampling_rate"], pq.Quantity):
            if unitsConvertible(domainargs["sampling_rate"], quants["domain_units"]):
                domainargs["sampling_period"] = 1/domainargs["sampling_rate"]
            
        if all(isinstance(d, pq.Quantity) for d in (domainargs["t_start"], domainargs["sampling_period"])) :
            if domainargs["t_start"] == 1/domainargs["sampling_period"]:
                sr = domainargs["sampling_period"]
                domainargs["sampling_period"] = domainargs["t_start"]
                domainargs["sampling_rate"] = sr
                domainargs["t_start"] = 0 * quants["domain_units"]
            
        elif all(isinstance(d, pq.Quantity) for d in (domainargs["t_start"], domainargs["sampling_rate"])) :
            if domainargs["t_start"] == 1/domainargs["sampling_rate"]:
                domainargs["sampling_period"] = domainargs["t_start"]
                domainargs["t_start"] = 0 * quants["domain_units"]
                
                
        anns = annots.get("annotations", dict())
        
        if anns is None:
            anns = dict()
        

        DataObject.__init__(self, name=strings["name"], 
                            file_origin=strings["file_origin"], 
                            description=strings["description"], 
                            array_annotations=annots["array_annotations"], 
                            **anns)
        
        self._domain_name_ = strings["domain_name"]
        self._origin = domainargs["t_start"]
        self._sampling_period = domainargs["sampling_period"]

        if not isinstance(self._domain_name_, str) or len(self._domain_name_.strip()) == 0:
            self._domain_name_ = nameFromUnit(self._origin)
        
        if not hasattr(self, "_name_") or not isinstance(self._name_, str) or len(self._name_.strip()) == 0:
            self._name_ = nameFromUnit(self.units)
    
    def __array_finalize__(self, obj):
        super(DataSignal, self).__array_finalize__(obj)
        
        self._origin            = getattr(obj, "_origin", 0 * pq.dimensionless)
        
        self._sampling_period   = getattr(obj, "_sampling_period", 1 * pq.dimensionless)
        
        self.annotations        = getattr(obj, "annotations",   {})
        self.name               = getattr(obj, "name",          None)
        self.file_origin        = getattr(obj, "file_origin",   None)
        self.description        = getattr(obj, "description",   None)
        
        # NOTE: this attribute was removed from neo API
        #self.channel_index      = getattr(obj, "channel_index", None)
        
        self.segment            = getattr(obj, "segment",       None)
        self.array_annotations  = getattr(obj, "array_annotations", None)
        self._domain_name_    = nameFromUnit(self._origin)
    
    def __reduce__(self):
        return _new_DataSignal, (self.__class__, 
                                 np.array(self),
                                 self.units, 
                                 self.domain.units,
                                 self.dtype, 
                                 self.domain.dtype,
                                 True,
                                 self.origin, 
                                 self.sampling_period, 
                                 self.sampling_rate,
                                 self.name, 
                                 self.domain_name,
                                 self.file_origin, 
                                 self.description,
                                 self.array_annotations,
                                 self.annotations,
                                 self.segment)
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        
        new_DS = cls(np.array(self), 
                     units=self.units, 
                     domain_units = self.domain.units,
                     dtype=self.dtype,
                     origin=self._origin, 
                     sampling_period=self._sampling_period,
                     name=self.name,
                     domain_name=self.domain_name,
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
            if len(i) == 1 and isinstance(i[0], np.ndarray): # advanced indexing
                obj = pq.Quantity(obj.magnitude, units = obj.units)
            else:
                j, k = i
                
                if isinstance(j, (int, numbers.Integral, np.integer)): # => quantity array
                    obj = pq.Quantity(obj.magnitude, units=obj.units)
                    
                elif isinstance(j, slice):
                    if j.start:
                        obj.origin = (self.origin + j.start * self.sampling_period)
                        
                    if j.step:
                        obj.sampling_period *= j.step
                            
                # elif isinstance(j, np.ndarray): # FIXME TODO
                #     raise NotImplementedError("%s not suported" % (type(j).__name__))
                
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
        if self._domain_name_ is None:
            self._domain_name_ = nameFromUnit(self.domain)
            
        return self._domain_name_
    
    
    @domain_name.setter
    def domain_name(self, value):
        if isinstance(value, str) and len(value.strip()):
            self._domain_name_ = value
            
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
    
    def time_index(self, t):
        """Copied from neo.AnalogSignal"""
        i = (t - self.t_start) * self.sampling_rate
        i  = np/rint(i.simplified.magitude).astype(np.int64)
        
        return i
    
    def domain_index(self, x):
        return self.time_index(x)

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
        
        domain_units = self.times.units
        
        if self.dimensionality == to_dims:
            to_u = self.units
            signal_data = np.array(self)
            
        else:
            to_u = pq.Quantity(1.0, to_dims)
            from_u = pq.Quantity(1.0, self.dimensionality)
            
            try:
                cf = pq.quantity.get_conversion_factor(from_u, to_u)
                
            except AssertionError:
                raise ValueError('Unable to convert between units of "%s" \
                                 and "%s"' % (from_u._dimensionality,
                                              to_u._dimensionality))
            signal_data = cf * self.magnitude
            
        obj = self.__class__(signal=signal_data, units=to_u,
                             domain_units = self.domain_units,
                             name = self.name,
                             domain_name = self.domain_name,
                             array_annotations = self.array_annotations,
                             description = self.description,
                             file_origin = self.file_origin,
                             sampling_rate=self.sampling_rate)
        
        # obj._copy_data_complement(self)
        #obj.channel_index = self.channel_index #
        obj.segment = self.segment             # FIXME TODO parent container functionality
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
    _parent_objects = ('Segment',)
    _parent_attrs = ('segment',)
    _quantity_attr = 'signal' # ?!? FIXME/TODO 
    _necessary_attrs = (('domain', pq.Quantity, 1), 
                        ('signal', pq.Quantity, 2))

    _recommended_attrs = neo.baseneo.BaseNeo._recommended_attrs

    def __new__(cls, domain, signal, units=None, domain_units=None, time_units=None, dtype=np.dtype("float64"), domain_dtype = np.dtype("float64"), domain_name = None, copy=True, name=None, file_origin=None, description=None, array_annotations=None, **annotations):
        # NOTE: 2022-11-24 15:49:27
        # see NOTE: 2021-12-09 21:45:08
        #
        # What we need to set up here are the following:
        # • the data itself (as a Quantity) - here, needs `units`, `dtype`, `copy`
        # • attribute `segment`
        # • attribute `domain` as a Quantity - here, needs domain_units, domain_dtype
        quants = {"units": None, "domain_units": None}#, "time_units": None}
        
        dtypes = {"dtype":None, "domain_dtype": None}
        
        bools = {"copy": True}
        
        call_arg_names = ("units", "dtype", "domain_units", "time_units", "domain_dtype")
        
        segment = None
        
        call_args = dict()
        
        # collapse domain_units and time_units into one argument
        
        if not isinstance(domain_units, pq.Quantity):
            if isinstance(time_units, pq.Quantity):
                domain_units = time_units
            else:
                domain_units = None
        else:
            domain_units = None
        
        default_domain_units = pq.dimensionless
        default_signal_units = pq.dimensionless
        
        # check signal, infer units is possible
        # if isinstance(signal, (neo.AnalogSignal, DataSignal)):
        if isinstance(signal, pq.Quantity):
            call_args = dict((name, getattr(signal, name, None)) for name in call_arg_names)
            call_args["copy"] = copy
            if isinstance(signal, neo.core.basesignal.BaseSignal):
                segment = signal.segment
            # else:
            #     segment = None
            quants["units"] = signal.units
            
        elif isinstance(signal, typing.Sequence):
            if not all(isinstance(v, pq.Quantity) for v in signal):
                if any(isinstance(v, pq.Quantity) for v in signal):
                    raise TypeError("Signal data cannot mix quantities and non-quantities")
                
            else:
                quants["units"] = signal[0].units # this WILL fail in Quantities module if units of the other elements are not convertible
            
        # check domain, infer domain_units if possible
        if isinstance(domain, (pq.Quantity)):
            call_args["domain"] = domain
            quants["domain_units"] = domain.units
            
        elif isinstance(domain, typing.Sequence):
            if not all(isinstance(v, pq.Quantity) for v in domain):
                if any(isinstance(v, pq.Quantity) for v in domain):
                    raise TypeError("Domain data cannot mix quantities and non-quantities")
                
            else:
                quants["domain_units"] = domain[0].units # this WILL fail in Quantities module if units of the other elements are not convertible
        
        # NOTE: 2022-11-24 11:57:08
        # see NOTE: 2022-11-24 11:59:04 and NOTE: 2022-11-24 11:22:34 for the logic → FIXME
        for v in call_arg_names + ("copy",):
            val = eval(v)
            if v in call_args:
                if call_args[v] is None and val is not None:
                    call_args[v] = val
            else:
                call_args[v] = val
            
        for k,v in call_args.items():
            if isinstance(v, bool): # there is only one bool arg expected
                bools["copy"] = v
                
            elif isinstance(v, np.dtype): # there is only one dtype arg expected
                if k in ("dtype", "domain_dtype"):
                    dtypes[k] = v

        # deal with units specifications
        # when quants["units"] were determined as above, ignore the "units" argument
        # 
        if not isinstance(quants["units"], pq.Quantity):
            if isinstance(units, pq.Quantity):
                quants["units"] = units if isinstance(units, pq.UnitQuantity) else units.units
            else:    
                quants["units"] = pq.dimensionless
            
        else:
            # units specified on the command line; check if they are compatible with
            # what has been inferred from above
            # in other words we DO NOT allow overriding the units inferred from the data
            # but we do allow rescaling
            # If this behaviour is not what you want then pass a non-quantity array as signal
            if isinstance(units, pq.Quantity):
                if not unitsConvertible(quants["units"], units):
                    raise TypeError(f"Specified units {units} are incompatible with those inferred from the signal data {quants['units']}")
                
                
        if not isinstance(quants["domain_units"], pq.Quantity):
            if isinstance(domain_units, pq.Quantity):
                quants["domain_units"] = domain_units if isinstance(domain_units, pq.UnitQuantity) else domain_units.units
                
            else:
                quants["domain_units"] = pq.dimensionless
                
        else:
            if isinstance(domain_units, pq.Quantity):
                if not unitsConvertible(quants["domain_units"], domain_units):
                    raise TypeError(f"Specified domain units {domain_units} are incompatible with those inferred from the domain data {quants['domain_units']}")

        # now,, rescale signal data if supplied as quantity(ies)
        if isinstance(signal, pq.Quantity):
            if signal.units != quants["units"]:
                signal = signal.rescale(quants["units"])
                
        elif isinstance(signal, typing.Sequence) and all(isinstance(v, pq.Quantity) for v in signal):
            signal = signal.__class__([v.rescale(quants["units"]) if v.units != quants["units"] else v for v in signal])
                
        if isinstance(domain, pq.Quantity):
            if domain.units != quants["domain_units"]:
                domain = domain.rescale(quants["domain_units"])
                
        elif isinstance(domain, typing.Sequence) and all(isinstance(v, pq.Quantity) for v in domain):
            domain = domain.__class__([v.rescale(quants["domain_units"]) if v.units != quants["domain_units"] else v for v in domain])
                            
        obj = pq.Quantity(signal, 
                          units=quants["units"], 
                          dtype=dtypes["dtype"], 
                          copy=bools["copy"]).view(cls)

        if obj.ndim == 1:
            obj.shape = (-1,1)

        obj._domain = pq.Quantity(domain, 
                                  units = quants["domain_units"],
                                  dtype = dtypes["domain_dtype"], 
                                  copy=bools["copy"])
                
        obj.segment=None

        return obj
                
    def __init__(self, domain, signal, units=None, domain_units=None, time_units=None, dtype=None, domain_dtype=None, domain_name=None, copy=True, name=None, file_origin=None, description=None,array_annotations=None, **annotations):
        """IrregularlySampledDataSignal constructor
        Similar to the neo.IrregularlySampledSignal but not restricted to the 
        time domain.
    
        NOTE: the first positional parameter (`domain`) corresponds to the first
        positional parameter `time` in neo.IrregularlySampledSignal
    
        """
        # ATTENTION: __init__ is called AFTER __new__ so `self` is already 
        # partly initialized here !!!
        # In particular, it SHOULD already contain:
        # • the data itself (as a Quantity)
        # • attribute `_domain` (as a Quantity)
        # • attribute `segment`
        # • attribute `channel_index`

        strings  = {"name":None,"file_origin":None, "description": None,"domain_name":None}
        
        quants = {"units": None, "domain_units": None}
        
        annots    = {"array_annotations":None, "annotations": None}
        
        dtypes   = {"dtype":None, "domain_dtype": None}
        
        bools = {"copy": None}
        
        call_arg_names = ("units", "domain_units", "dtype", "domain_dtype",
                          "name", "domain_name",
                          "file_origin", "description", "array_annotations",
                          "annotations")
        
        call_args = dict()
        
        if isinstance(signal, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
            call_args = dict((name, getattr(signal, name, None)) for name in call_arg_names)
            call_args["copy"] = True
            call_args["domain_units"] = getattr(signal, "times", 0.*pq.s).units
        elif isinstance(signal, (tuple, list)):
            signal = np.array(signal)
            
        elif isinstance(signal, np.ndarray):
            if isinstance(signal, pq.Quantity):
                call_args["units"] = signal.units
                
        else:    
            raise TypeError(f"Unexpected type ({type(signal).__name__}) for signal's data")
        
        # print(f"signal.shape")
        siglen = signal.shape[0]
        channels = 1 if signal.ndim == 1 else signal.shape[1]
        
        for v in call_arg_names:
            val = eval(v) # evals locally, so available only if given as named param 
            if v in call_args: 
                if call_args[v] is None and val is not None:
                    call_args[v] = val
            else: # param not there hence add it
                call_args[v] = val
            
        for k,v in call_args.items():
            if isinstance(v, bool): # there is only one bool arg expected
                bools["copy"] = v
                
            elif isinstance(v, np.dtype): # 
                if k == "dtype":
                    dtypes[k] = v

            elif isinstance(v, str):
                # there are 4 str args expected: name, file_origin and description;
                if k == "file_origin" and is_path(v):
                    # likely a file path name
                    strings["file_origin"] = v
                elif k in ("name", "domain_name", "description"):
                    strings[k] = v
                    
            elif isinstance(v, dict):
                if isinstance(v, ArrayDict): # only array_annotations are ArrayDict
                    annots["array_annotations"] = v
                    
                elif isinstance(v, dict): # can be array_annotations or anotations; brrr...
                    # if len(v) == signal.shape[1]: # likely array annotations, too
                    if len(v) == channels: # likely array annotations, too
                        if annots["array_annotations"] is None:
                            arr_ann = ArrayDict(signal.shape[1])
                            for ka,va in v.items():
                                arr_ann[ka] = va
                            annots["array_annotations"] = arr_ann
                        else:
                            annots["annotations"] = v
                            
                    else:
                        annots["annotations"] = v
                        
            elif isinstance(v, pq.Quantity):
                if v.size == 1: # a scalar ; note signal is treated from the outset
                    quants[k] = v.units
                        
        DataObject.__init__(self, name = strings["name"], 
                            file_origin=strings["file_origin"],
                            description=strings["description"], 
                            array_annotations=annots["array_annotations"],
                            **annots["annotations"])

        
        self._domain_name_ = nameFromUnit(self._domain)
        
        if isinstance(name, str):
            self._name_ = name
        else:
            self._name_ = nameFromUnit(self.units)
    
    def __reduce__(self):
        return _new_IrregularlySampledDataSignal, (self.__class__,
                                                   self._domain,
                                                   np.array(self),
                                                   self.units,
                                                   self.domain.units,
                                                   self.dtype,
                                                   self.domain.dtype,
                                                   True,
                                                   self.name,
                                                   self.domain_name,
                                                   self.file_origin,
                                                   self.description,
                                                   self.array_annotations,
                                                   self.annotations,
                                                   self.segment,
                                                   )
    
    def __array_finalize__(self, obj):
        super(IrregularlySampledDataSignal, self).__array_finalize__(obj)
        self._domain            = getattr(obj, "_domain", getattr(obj, "times", None))
        self.annotations        = getattr(obj, "annotations",   {})
        self.name               = getattr(obj, "name",          None)
        self.file_origin        = getattr(obj, "file_origin",   None)
        self.description        = getattr(obj, "description",   None)
        self.segment            = getattr(obj, "segment",       None)
        #self.channel_index      = getattr(obj, "channel_index", None)
        self.array_annotations  = getattr(obj, "array_annotations", None)
        if isinstance(self._domain, pq.Quantity):
            self._domain_name_    = nameFromUnit(self._domain)
        else:
            self._domain_name_    = "Dimensionless"
        
    def __deepcopy__(self, memo):
        cls = self.__class__
        new_signal = cls(self.domain, np.array(self), units=self.units,
                         domain_units=self.domain.units, dtype=self.dtype,
                         domain_dtype=self.domain.dtype,
                         name=self.name, doman_name=self.domain_name,
                         file_origin=self.file_origin, 
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
        
        if self.size == 0:
            return "\n".join(["%s       %s" % ("Domain", "Signal"),
                              "",
                              "* %s       * %s" % (self.times.units, self.units)])
        
        with np.printoptions(precision=2, linewidth=1000):
            values_str_list = self.as_array().__repr__().replace("array(", "").replace(")", "").replace("[[", "[").replace("]]", "]").replace(",", "").split("\n")
            
            times_str_list = np.array(self.times).__repr__().replace("array(", "").replace(")", "").replace("[", "").replace("]", "").replace(",", "").split()
            if len(times_str_list) == 0:
                reps_str_list = [""]
            else:
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
            if len(i) == 1 and isinstance(i[0], np.ndarray): # advanced indexing
                obj = pq.Quantity(obj.magnitude, units = obj.units)
                obj._domain_ = self.times.__getitem__((i[0][:,0],))
            else:        
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
            
        elif isinstance(i, np.ndarray):
            obj._domain_ = self.times.__getitem__(i)
            
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
        from core import quantities as scq
        if isinstance(other, self.__class__):
            if len(self) != len(other):
                return False
            
            if self.ndim != other.ndim:
                return False
            
            if self.shape != other.shape:
                return False
            
            return (super(IrregularlySampledDataSignal, self).__eq__(other).all() and
                    (self.times == other.times).all())
        
        elif isinstance(other, (float)):
            return self.magnitude == other
            
        elif isinstance(other, pq.Quantity):
            if other.size == 1:
                if not unitsConvertible(other.units, self.units):
                    ret = np.full_like(self, False)
                else:
                    ret = self.magnitude == (other.rescale(self.units)).magnitude
                    
                return ret
                    
            else:
                if other.size != self.size:
                    return False
                
                if other.shape != self.shape:
                    return False
                
                if not unitsConvertible(other.units, self.units):
                    ret = np.full_like(self, False)
                else:
                    ret = self.magnitude == (other.rescale(self.units)).magnitude1
        
                return ret
            
        return False

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
    
    # def mean(self, axis:typing.Optional[int] = None, interpolation:bool=None):
    def mean(self, interpolation:bool=None):
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
        if self._domain_name_ is None:
            self._domain_name_ = nameFromUnit(self.domain) if isinstance(self.domain, pq.Quantity) else "Dimensionless"
            
        return self._domain_name_
    
    @domain_name.setter
    def domain_name(self, value):
        if isinstance(value, str) and len(value.strip()):
            self._domain_name_ = value
    
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
                if not unitsConvertible(value, self.domain.units):
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
        # self._check_consistency(other)
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
            signal_data = np.array(self)
            
        else:
            to_u = pq.Quantity(1.0, to_dims)
            from_u = pq.Quantity(1.0, self.dimensionality)
            
            try:
                cf = pq.quantity.get_conversion_factor(from_u, to_u)
                
            except AssertionError:
                raise ValueError('Unable to convert between units of "%s" \
                                 and "%s"' % (from_u._dimensionality,
                                              to_u._dimensionality))
            signal_data = cf * self.magnitude
            
        obj = self.__class__(domain=self.domain, signal=signal_data, 
                             units=to_u,
                             domain_units = self.domain_units,
                             domain_name = self.domain_name,
                             array_annotations = self.array_annotations,
                             description = self.description,
                             file_origin = self.file_origin)
        
        # obj._copy_data_complement(self)
        #obj.channel_index = self.channel_index 
        obj.segment = self.segment             # FIXME TODO parent container functionality
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
        #for attr in ("origin", "name", "file_origin", "domain", "units", "domain_units",
                     #"description", "annotations", "array_annotations"):
        for attr in ("origin", "name", "file_origin", "description", 
                     "annotations", "array_annotations"):
            setattr(self, attr, deepcopy(getattr(other, attr, None)))
            #print("attr", attr)
            #if attr == "units":
                
            #elif attr == "domain_units":
                
                #setattr(self, attr, deepcopy(getattr(other, attr, pq.dimensionless)))
            #else:
            
    def interval(self, start, stop):
        '''The equivalent of neo.AnalogSignal.time_slice.
        Except that when start == stop it returns the value at start (if found)
        '''
        

        u = self.domain.units

        if not isinstance(start, pq.Quantity):
            start *= u
        else:
            start = start.rescale(u)
            
        if not isinstance(stop, pq.Quantity):
            stop *= u
        else:
            stop = stop.rescale(u)
            
        start, stop = (np.min([start, stop])*u, np.max([start,stop])*u)
        
        # get index of start
        if start is None:
            i = 0
        else:
            i = np.where(np.isclose(self.domain.magnitude, start.magnitude))[0]
            if len(i):
                i = i[0]
            else:
                raise ValueError("domain value %s not found" % start)

        # get index of stop
        if stop is None:
            j = len(self)
        else:
            j = np.where(np.isclose(self.domain.magnitude, stop.magnitude))[0]
            if len(j):
                j = j[-1]
            else:
                raise ValueError("domain value %s not found" % stop)

        if (i < 0) or (j > len(self)):
            raise ValueError('Expecting start and stop to be within the signal extent')

        if i == j:
            obj = self[i]
        else:
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

