# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Module for managing trigger protocols by way of special Event types embedded
in neo.Segment data structure

NOTE: 2020-10-07 17:42:06
core.neoutils code split and redistributed across core.neoutils, ephys.ephys and 
core.triggerprotocols

Functions and classes defined here:
====================================

I. Module-level functions for the management of trigger events and protocols
============================================================================
auto_define_trigger_events
auto_detect_trigger_protocols
detect_trigger_events
embed_trigger_event
embed_trigger_protocol
get_trigger_events
modify_trigger_protocol
parse_trigger_protocols
remove_events
remove_trigger_protocol

II. Classes
===========
TriggerEvent -> now defined in core.triggerevent
TriggerEventType -> now defined in core.triggerevent
TriggerProtocol

Functions and classes defined somewere else but used here:
===========================================================
clear_events - core.neoutils

"""
import typing, warnings, traceback, dataclasses, pathlib
from dataclasses import dataclass
from itertools import chain
from copy import (deepcopy, copy,)
from datetime import datetime, date, time, timedelta
from numbers import (Number, Real,)
from functools import partial
import numpy as np
import quantities as pq
import neo
#from neo.core import baseneo
#from neo.core import basesignal
#from neo.core import container
from neo.core.dataobject import (DataObject, ArrayDict,)

from core.datatypes import (is_string, 
                            RELATIVE_TOLERANCE, ABSOLUTE_TOLERANCE, EQUAL_NAN)

from core.quantities import (checkTimeUnits, unitsConvertible, QuantityDescriptorValidator)
from core.neoutils import (get_index_of_named_signal, remove_events, clear_events,
                           is_same_as, get_events)

from core.datasignal import (DataSignal, IrregularlySampledDataSignal, )
from core.prog import (safeWrapper, with_doc)
from core.triggerevent import (TriggerEvent, TriggerEventType,)
from core.traitcontainers import DataBag
from core.signalprocessing import detect_boxcar

#### BEGIN module-level default options
DEFAULTS = DataBag()
DEFAULTS["Presynaptic"] = DataBag()
DEFAULTS["Presynaptic"]["Channel"] = 0
DEFAULTS["Presynaptic"]["DetectEvents"] = False
DEFAULTS["Presynaptic"]["DetectionBegin"] = 0 * pq.s
DEFAULTS["Presynaptic"]["DetectionEnd"] = 1 * pq.s
DEFAULTS["Presynaptic"]["Name"] = "epsp"

DEFAULTS["Postsynaptic"] = DataBag()
DEFAULTS["Postsynaptic"]["Channel"] = 0
DEFAULTS["Postsynaptic"]["DetectEvents"] = False
DEFAULTS["Postsynaptic"]["DetectionBegin"] = 0 * pq.s
DEFAULTS["Postsynaptic"]["DetectionEnd"] = 1 * pq.s
DEFAULTS["Postsynaptic"]["Name"] = "bAP"

DEFAULTS["Photostimulation"] = DataBag()
DEFAULTS["Photostimulation"]["Channel"] = 0
DEFAULTS["Photostimulation"]["DetectEvents"] = False
DEFAULTS["Photostimulation"]["DetectionBegin"] = 0 * pq.s
DEFAULTS["Photostimulation"]["DetectionEnd"] = 1 * pq.s
DEFAULTS["Photostimulation"]["Name"] = "uepsp"

DEFAULTS["ImagingFrameTrigger"] = DataBag()
DEFAULTS["ImagingFrameTrigger"]["Channel"] = 0
DEFAULTS["ImagingFrameTrigger"]["DetectEvents"] = False
DEFAULTS["ImagingFrameTrigger"]["DetectionBegin"] = 0 * pq.s
DEFAULTS["ImagingFrameTrigger"]["DetectionEnd"] = 1 * pq.s
DEFAULTS["ImagingFrameTrigger"]["Name"] = "imaging"

#### END module-level default options
  
@dataclass
class TriggerProtocol:
    """Encapsulates an experimental stimulation protocol (a.k.a, "triggers").
    
    TriggerProtocol objects contain a combination of TriggerEvent types and the 
    indices of segments (sweep or data frame)¹ from a collection, where this 
    combination is appled. By "combination" we mean any association of a
    'presynaptic', 'postsynaptic', 'photostimulation', and 'imaging' TriggerEvent
    objects. 

    Technically a TriggerProtocol obejct has up to three TriggerEvent objects of 
    the following types:
        up to one presynaptic event type
        up to one postsynaptic event type
        up to one photostimulation event type

    and a possibly empty list of TriggerEvent objects of 'imaging_frame', 
    'imaging_line', or 'segment' types, collected under the attribute 'acquisition'.

    A TriggerProtocol has at least one type of TriggerEvent objects, and is
    associated with at least one neo.Segment, encapsulating the TTL triggers
    delivered during that particular segment (or "sweep").
    
    Note that each TriggerEvent may encapsulate a single TTL trigger or a sequence
    (a train) of TTL triggers. Each TriggerEvent type ('presynaptic',
    'postsynaptic', 'photostimulation', 'imaging') may occur at most once, in a
    protocol. Nevertheless, TriggerEvents of different types can be interlaved
    by an appropriate choice of time stamps for individual TTL triggers in the
    TriggerEvent objects.

    The same trigger protocol may occur in more than one segment. However, any
    one segment can be associated with at most one trigger protocol. The data 
    that owns the segments can associate several TriggerProtocol objects, to 
    reflecting the fact that that different protocols may be applied to distinct 
    segments of the data.
    
    Unlike TriggerEvent, a TriggerProtocol is not currently "embedded" in any of
    the neo containers. Instead, its component TriggerEvent objects are contained
    ("embedded") in the "events" attribute of the neo.Segment associated with this protocol.
    
    ¹ These terms are synonyms in a broader sense: a segment is an electrophysiology
    data 'sweep' and may correspond to a single imaging data frame. In Scipyen,
    an electrophysiology data sweep is encapsulated in a neo.Segment, and an
    imaging data frame is encapsulated as a VigraArray. The exception from this
    rule are the data frames in a neo.ImageSequence, whichh are encapsulated as 
    numpy arrays.
        
    A TriggerProtocol object has the following attributes:
        
    presynaptic:        Presynaptic event, typically generated via TTL pulses 
                        or trains sent via a digital output channel of the DAQ 
                        device. These TTL signals are used to evoke synaptic 
                        transmission (e.g., by routing to stimulus isolation
                        devices) or to activate synapses by other means (e.g., 
                        optically, such as photouncaging, optogenetic activation
                        but see below).

                        Can be None.

                        NOTE: TTL-like pulses or trains can also be emulated 
                        via short pulse-like DAC command waveforms, where the DAC
                        output is routed to a trigered device, instead of the 
                        headstage (and the cell) via the amplifier - these TTL-like
                        pulses are in V (!)

    postsynaptic:       Postsynaptic event, usually generated via the DAC output
                        using pulse-like command waveforms, typically used to 
                        evoke postsynaptic spikes

                        Can be None.

                        NOTE: These can also be generated via digital ("true" TTL)
                        outputs sent via stimulus isolators to axonal efferents
                        for antidromic activation of spiking in the recorded cell.

    photostimulation:   Photostimulation event - its main role is to distinguish,
                        where required, between synaptic stimulation via axonal 
                        activation and synaptic stimulation via photo-uncaging or 
                        optogenetics. These event types also flag the onset of
                        other light activated processes not necessarily associated
                        with synaptic function (such as photobleaching or
                        photoconversion of fluorescent proteins).

                        Can be None.
                        
    acquisition:        A list (posibly empty) of imaging_frame, imaging_line, or
                        sweep type events.

                        These events represent acquisition triggers for imaging
                        frame, imaging line, or sweep, in the cases where the 
                        the acquisition device is triggered externally

    segmentIndex:       indexing object (e.g, list of indices, a range, or a slice) 
                        for the frames (segments or sweeps) where this protocol 
                        applies; it may be empty.

    imaging_delay:      python Quantity scalar
        
    The first three event types describe above can each be a TriggerEvent object 
    or None.
    
    When 'segmentIndex' is empty, the protocol will apply to ALL data segments or
    frames in the collection.
    
    ATTENTION: In a collection of segments (e.g., neo.Block) each segment
        can have at most one protocol. It follows that a protocol with an
        empty segmentIndex cannot co-exist with other protocols given that
        segment collection (an empty segmentIndex implies that the protocol 
        applies to all segments in that collection) 
    
            
    The event_type atribute of the events will be overwritten according to the 
    named parameter to which they are assigned in the function call.
    
    NOTE: there can be at most ONE TriggerEvent each, of the presynaptic, postsynaptic,
    and photostimulation type.
    
    In turn, each of these events can contain an ARRAY of time values (i.e., 
    multiple time stamps), so a TriggerEvent can actually encapsulate the notion 
    of an array of events of th same type (e.g. a paired-pulse presynaptic 
    stimulation, etc).

    """
    # TODO validators for these below -- maybe ?
    presynaptic:typing.Optional[TriggerEvent] = dataclasses.field(default=None)
    postsynaptic:typing.Optional[TriggerEvent] = dataclasses.field(default=None)
    photostimulation:typing.Optional[TriggerEvent] = dataclasses.field(default=None)
    
    # TODO a validator for these two
    acquisition:list[TriggerEvent] = dataclasses.field(default_factory = list)
    userEvents:list[TriggerEvent] = dataclasses.field(default_factory = list)
    
    # This is the delay between the start of an electrophysiology segment and 
    # that of an image acquisition and helps to temporally map the events in 
    # the electrophysiology to those in the imaging data.
    # 
    # For experiments where the electrophysiology DRIVES the imaging (i.e. 
    # imaging acquisition is triggered by the electrophysiology hardware) 
    # this property is redundant.
    # 
    # However, imagingDelay is necessary in the inverse situation where the
    # electrophysiology is triggered by an imaging trigger (typically, by an
    # imaging frame trigger output by the imaging hardware) when the "delay"
    # cannot be calculated from the trigger waveforms recorded in the 
    # electrophysiology data.
    # 
    # NOTE: imagingDelay is a python Quantity (in time units, typically 's')
    # and IT IS NOT a TriggerEvent object. For this reason, the imagingDelay
    # will not have a corresponding event in a data segment's "events" list.
    #
    imagingDelay:QuantityDescriptorValidator = QuantityDescriptorValidator("imagingDelay", validator=checkTimeUnits) # 0*pq.s by default
    
    # TODO: a validator to check type and contents
    segments:typing.Union[int, list[int], tuple[int], range, slice] = dataclasses.field(default_factory = list)
    
    name:str = dataclasses.field(default="Protocol")
    # these are in addition to the _recommended_attrs inherited from BaseNeo
    file_origin:typing.Union[str, pathlib.Path] = dataclasses.field(default = "")
    file_datetime:datetime = dataclasses.field(default = datetime.now())
    rec_datetime:datetime = dataclasses.field(default = datetime.now())
    
#     _data_attributes_ = (("file_datetime", datetime),
#                          ("rec_datetime", datetime))
#     
#     _decsriptor_attributes_ = _data_attributes_ + neo.core.baseneo.BaseNeo._recommended_attrs
    
    def __len__(self):
        """The number of TriggerEvents, of any type, in this protocol
        """
        if self.presynaptic is None:
            pre = 0
            
        else:
            pre = self.presynaptic.size
            
        if self.postsynaptic is None:
            post = 0
            
        else:
            post = self.postsynaptic.size
            
        if self.photostimulation is None:
            photo = 0
            
        else:
            photo = self.photostimulation.size
            
        if isinstance(self.acquisition, (tuple, list)) and len(self.acquisition) and all(isinstance(e, TriggerEvent) for e in self.acquisition):
            imaging = sum(e.size for e in self.acquisition)
        else:
            imaging = 0
            
        # elif isinstance(self.acquisition, TriggerEvent):
        #     imaging = self.acquisition.size
            
        if isinstance(self.userEvents, (tuple, list)) and len(self.userEvents) and all(isinstance(e, (TriggerEvent, neo.Event)) for e in self.userEvents):
            user = sum(e.size for e in self.userEvents)
        else:
            user = 0
            
        return pre + post + photo + imaging + user
    
    def __str__(self):
        result = ["%s %s:" % (self.__class__.__name__, self.name)]
        
        if self.presynaptic is not None:
            result += ["\tpresynaptic:\n\t%s" % str(self.presynaptic)]
            
        if self.postsynaptic is not None:
            result += ["\tpostsynaptic:\n\t%s" % str(self.postsynaptic)]
            
        if self.photostimulation is not None:
            result += ["\tphotostimulation:\n\t%s" % str(self.photostimulation)]
            
        if isinstance(self.acquisition, (tuple, list)) and len(self.acquisition):
            result.append("\tacquisition:\n\t%s" % "\n".join([str(a) for a in self.acquisition]))
            
        elif isinstance(self.acquisition, TriggerEvent):
            result += ["\tacquisition:\n\t%s" % str(self.acquisition)]
            
        result += ["\timaging delay: %s" % str(self.imagingDelay)]
        
        result += ["\tframe (segment): %s" % str(self.segments)]
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
            return self.presynaptic
        
        elif event_type & TriggerEventType.postsynaptic:
            return self.postsynaptic
        
        elif event_type & TriggerEventType.photostimulation:
            return self.photostimulation
        
        elif event_type & TriggerEventType.acquisition:
            if isinstance(self.acquisition, (tuple, list)):
                if len(self.acquisition):
                    return self.acquisition[0]
            
            elif isinstance(self.acquisition, TriggerEvent):
                return self.acquisition
    
    @property
    def ntriggers(self):
        """Number of trigger events (of any type)
        """
        return len(self)
    
    @property
    def events(self):
        ret = list()
        
        if self.presynaptic is not None:
            ret.append(self.presynaptic)
            
        if self.postsynaptic is not None:
            ret.append(self.postsynaptic)
            
        if self.photostimulation is not None:
            ret.append(self.photostimulation)
        
        if isinstance(self.acquisition, (tuple, list)) and len(self.acquisition):
            ret.append(self.acquisition[0])
            
        elif isinstance(self.acquisition, TriggerEvent):
            ret.append(self.acquisition)
            
        return sorted(ret, key = lambda x: x.times.flatten()[0])
    
    @property
    def nsegments(self):
        """Number of neo.Segment objects to which this protocol applies
        """
        return len(self.segmentIndices())
    
    @safeWrapper
    def hasSameEvents(self, other, rtol = RELATIVE_TOLERANCE, atol = ABSOLUTE_TOLERANCE, equal_nan = EQUAL_NAN):
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
        
        if not hasattr(self, "userEvents"):
            self.userEvents = []
        
        pre     = False
        post    = False
        photo   = False
        acq     = False
        usr     = False
        
        img_del = False
        
        if self.presynaptic is None:
            if other.presynaptic is None:
                pre = True
                
        else:
            if other.presynaptic is not None:
                pre = self.presynaptic.is_same_as(other.presynaptic, 
                                                      rtol=rtol, atol=atol, equal_nan=equal_nan)
    
        if self.postsynaptic is None:
            if other.postsynaptic is None:
                post = True
                
        else:
            if other.postsynaptic is not None:
                post = self.postsynaptic.is_same_as(other.postsynaptic,
                                                        rtol=rtol, atol=atol, equal_nan=equal_nan)
                
        if self.photostimulation is None:
            if other.photostimulation is None:
                photo = True
                
        else:
            if other.photostimulation is not None:
                photo = self.photostimulation.is_same_as(other.photostimulation,
                                                             rtol=rtol, atol=atol, equal_nan=equal_nan)
                    
        img_del = self.imagingDelay is not None and other.imagingDelay is not None
        
        img_del &= self.imagingDelay.units == other.imagingDelay.units
        
        img_del &= np.all(np.isclose(self.imagingDelay.magnitude, other.imagingDelay.magnitude,
                          rtol-rtol, atol=atol, equal_nan=equal_nan))
                
        if not hasattr(other, "userEvents"):
            if len(self.userEvents):
                usr = False
                
            else:
                usr = True
        else:
            usr = len(self.userEvents) == len(other.userEvents)
        
        if usr and hasattr(other, "userEvents"):
            e_events = list()
            
            for (e0, e1) in zip(self.userEvents, other.userEvents):
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
            if isinstance(other.acquisition, list) and len(other.acquisition):
                acq = len(self.acquisition) == len(other.acquisition) and all((all(s.is_same_as(v) for v in other.acquisition) for s in self.acquisition))
                    
        return pre and post and photo and img_del and acq and usr
    
    def __eq__(self, other):
        """Compares pre-, post- and photo- events and frame index with those from other TriggerProtocol.
        The compared protocols may have different frame indices!
        """
        # Will raise exception if other is not a TriggerProtocol
        same_events = self.hasSameEvents(other)
        
        return same_events and self.name == other.name and \
            self.imagingDelay == other.imagingDelay
    
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
                    self.presynaptic = None
                    
                elif event_type & TriggerEventType.postsynaptic:
                    self.postsynaptic = None
                    
                elif event_type & TriggerEventType.photostimulation:
                    self.photostimulation = None
                    
                elif event_type & TriggerEventType.acquisition:
                    self.acquisition = None
            
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
            self.presynaptic = own_event
            
        elif event_type & TriggerEventType.postsynaptic:
            self.postsynaptic = own_event
            
        elif event_type & TriggerEventType.photostimulation:
            self.photostimulation = own_event
            
        elif event_type & TriggerEventType.acquisition:
            self.acquisition = own_event
            
    @property
    def imagingFrameTrigger(self):
        """Returns an imaging_frame trigger event, if any
        """
        return self.acquisition
        #return self.__get_acquisition_event__(TriggerEventType.imaging_frame)
        
    @imagingFrameTrigger.setter
    def imagingFrameTrigger(self, value):
        """Pass None to clear acquisition events
        """
        self.acquisition = value
        
    @property
    def imagingLineTrigger(self):
        """Returns an imaging_line trigger event, if any
        """
        return self.acquisition
    
    @imagingLineTrigger.setter
    def imagingLineTrigger(self, value):
        """Pass None to clear acquisition events
        """
        self.acquisition = value

    @property
    def isempty(self):
        return len(self) == 0
    
    # @safeWrapper
    # def copy(self):
    #     return TriggerProtocol(pre = self) # copy constructor
        
    @safeWrapper
    def updateSegmentIndex(self, value):
        """Update current segment index with the one specified in value.
        
        When value is a list or an int, the current segment index will be coerced to a list.
        """
        # NOTE: 2019-03-15 15:41:15
        # TODO FIXME this is pretty expensive and convoluted - 
        #            why not just decide to keep __segment_index__ as a list?
        
        if isinstance(self.segments, (range, slice)):
            mystart = self.segments.start
            mystop = self.segments.stop
            mystep = self.segments.step
            
            if isinstance(value, (range,slice)):
                otherstart  = value.start
                otherstop   = value.stop
                otherstep   = value.step
                
                
                if mystep != otherstep:
                    raise TypeError("Cannot update frame indexing %s and from %s" % (self.segments, value))
                
                if mystart is None or otherstart is None:
                    finalstart = None
                    
                else:
                    finalstart = min(mystart, otherstart)
                    
                finalstop = max(mystop, otherstop)
                
                if isinstance(self.segments, range):
                    if finalstart is None:
                        finalstart = 0
                        
                    self.segments = range(finalstart, mystep, finalstop)
                    
                else:
                    self.segments = slice(finalstart, mystep, finalstop)
                
            elif isinstance(value, (tuple, list)) and all([isinstance(v, int) for v in value]): 
                # NOTE: 2017-12-14 15:12:06
                # because the result may contain indices at irregular intervals,
                # which is not what a range or slice object produces, we need to
                # coerce self.segments to a list if not already a list
                #
                
                if isinstance(self.segments, range):
                    newlist = [f for f in self.segments]
                    
                else: # self.segments is a slice; realise its indices on the max index in value
                    if mystop is None:
                        newlist = [f for f in range(self.segments.indices(max(value)))]
                        
                    else:
                        newlist = [f for f in range(self.segments.indices(max(mystop, max(value))))]
                                                    
                newlist += (list(value)[:])
                    
                # NOTE: 2017-12-14 15:09:41#
                # coerce self.segments to a list
                self.segments = sorted(list(set(newlist))) 
                
            elif isinstance(value, int):# coerce self.segments to a list also
                # NOTE: 2017-12-14 15:12:06
                # because the result may contain indices at irregular intervals,
                # which is not what a range or slice object produces, we need to
                # coerce self.segments to a list if not already a list
                #
                
                if isinstance(self.segments, range):
                    newlist = [f for f in self.segments]
                    
                else:
                    if mystop is None:
                        # FIXME
                        newlist = [f for f in range(self.segments.indices(value+1))]
                        
                    else:
                        # FIXME
                        newlist = [f for f in range(self.segments.indices(max(mystop, value+1)))]
                     
                newlist.append(value)
                
                self.segments = sorted(list(set(newlist)))
                
            else:
                raise TypeError("Cannot update current frame indexing %s with %s)" % (self.segments, value))
            
        elif isinstance(self.segments, (tuple, list)):
            if isinstance(value, (tuple, list)):
                # this ensures unique and sorted frame index list
                self.segments = sorted(list(set(list(self.segments) + list(value))))
                
            elif isinstance(value, int):
                newlist = list(self.segments)
                newlist.append(value)
                self.segments = sorted(list(set(newlist)))
                
            elif isinstance(value, (range, slice)):
                otherstart  = value.start
                otherstop   = value.stop
                otherstep   = value.step
                
                if isinstance(value, range):
                    newlist = [f for f in value]
                    
                else:
                    if otherstop is None:
                        newlist = [f for f in range(value.indices(max(self.segments)+1))]
                        
                    else:
                        newlist = [f for f in range(value.indices(max(otherstop, max(self.segments)+1)))]
                        
                newlist += list(self.segments)[:]
                
                self.segments = sorted(list(set(newlist)))
                
            else:
                raise TypeError("Cannot update frame indexing %s with %s" % (self.segments, value))
                    
        elif isinstance(self.segments, int):
            if isinstance(value, int):
                self.segments = sorted([self.segments, value])
                
            elif isinstance(value, (tuple, list)):
                newlist = [f for f in value] + [self.segments]
                
                self.segments = sorted(list(set(newlist)))
                
            elif isinstance(value, (range, slice)):
                otherstart  = value.start
                otherstop   = value.stop
                otherstep   = value.step
                
                if isinstance(value, range):
                    newlist = [f for f in value]
                    
                else:
                    if otherstop is None:
                        newlist = [f for f in range(value.indices(self.segments+1))]
                        
                    else:
                        newlist = [f for f in range(value.indices(max(otherstop, self.segments+1)))]
                        
                newlist.append(self.segments)
                
                self.segments = sorted(list(set(newlist)))
                
            else:
                raise TypeError("Cannot update frame indexing %s with %s" % (self.segments, value))
    
    def segmentIndices(self, value=None):
        """Returns a list of segment indices.
        'value' is used only when segmentIndex is a python slice object, and it must be an int
        """
        
        if isinstance(self.segments, slice):
            if value is None:
                value = self.segments.stop
                
            if not isinstance(value, int):
                raise TypeError("When segment index is a slice a value of type int is required")
            
            return [x for x in range(*self.segments.indices(value))]
        
        elif isinstance(self.segments, range):
            return [x for x in self.segments]
        
        elif isinstance(self.segments, (tuple, list)):
            if len(self.segments) == 0 or all(isinstance(v, int) for v in self.segments):
                return self.segments
        
        elif isinstance(self.segments, int):
            return self.segments
        
    def toHDF5(self, group, name, oname, compression, chunks, track_order, entity_cache):
        import h5py
        from iolib import h5io
        
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity
            return cached_entity
        
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        if isinstance(name, str) and len(name.strip()):
            target_name = name
        
        entity = group.create_group(target_name)
        h5io.storeEntityInCache(entity_cache, self, entity)
        entity.attrs.update(obj_attrs)
        
        for name in ("presynaptic", "postsynaptic", "photostimulation", 
                     "acquisition", "imagingDelay" ,"segmentIndex"):
            # since these are (deep) copies - see NOTE: 2021-11-24 12:43:27
            # and TODO: 2021-11-24 12:33:57 - there are very good chances their
            # entities are NOT already in the cache
            trigger = getattr(self, name, None)
            
            if isinstance(trigger, TriggerEvent):
                oname = trigger.name
            else:
                oname = name
                
            h5io.toHDF5(trigger, entity,
                                  name=name, oname=oname, 
                                  compression = compression, chunks=chunks, 
                                  track_order = track_order, entity_cache=entity_cache)
            
        
        return entity
    
    @classmethod
    def fromHDF5(cls, entity, attrs:dict, cache:dict = {}):
        import h5py
        from iolib import h5io
        # print(f"cls {cls}, entity {entity}")
        if not isinstance(entity, h5py.Group):
            raise TypeError(f"Expecting a HDF5 Group; got {type(entity).__name__} instead")
        
        # TODO 2021-11-24 13:15:13 implement me!
        
        if entity in cache:
            return cache[entity]
        
        # attrs = h5io.attrs2dict(entity.attrs)
        
        components = dict()
        
        for name in ("presynaptic", "postsynaptic", "photostimulation", 
                     "acquisition", "imagingDelay" ,"segmentIndex"):
            # NOTE: 2024-07-18 09:59:58
            # restores the trigger events in the protocol
            obj_entity = entity.get(name, None)
            
            if obj_entity is None:
                components[name] = None
                
            elif obj_entity in cache:
                components[name] = cache[obj_entity]
                
            else:
                components[name] = h5io.fromHDF5(obj_entity, cache)
                
        return cls(pre              = components["presynaptic"],
                   post             = components["postsynaptic"],
                   photo            = components["photostimulation"],
                   acquisition      = components["acquisition"],
                   imaging_delay    = components["imagingDelay"],
                   segment_index    = components["segmentIndex"],
                   name             = attrs["name"])
                
            
        
        

#### BEGIN Module-level functions

# @with_doc(detect_trigger_events, use_header=True)
@safeWrapper
def auto_define_trigger_events(src:typing.Union[neo.Block, neo.Segment, typing.Sequence[neo.Segment]],
                               event_type:typing.Union[str,TriggerEventType], 
                               analog_index:typing.Union[int,str], 
                               times:typing.Optional[pq.Quantity] = None, 
                               label:typing.Optional[str] = None, 
                               name:typing.Optional[str] = None, 
                               use_lo_hi:bool = True, 
                               time_slice:typing.Optional[typing.Sequence[pq.Quantity]] = None, 
                               clear:bool = False, 
                               clearSimilarEvents:bool = True, 
                               clearTriggerEvents:bool = True, 
                               clearAllEvents:bool = False, reltimes:bool = True):
    """Constructs TriggerEvent objects from events detected in analog signals.
    
    TriggerEvent objects are constructed using either time stamps given as
    function parameters, or using events detected based on trigger-like waveforms
    in the analog signals in src.
    
    Trigger-like (or TTL-like) waveforms are upward ("up") or downward 
    ("down") rectangular deflections, or pulses, in the signal. A train of 
    TTL-like pulses represents a train of events.
    
    Event detection is done by searching for TTL-like waveforms in specific 
    neo.AnalogSignal objects contained in src, and specified by the 'analog_index'
    parameter.
    
    If found, the time stamps of the TTL-like waveforms (relative to the 
    time start of the signal) are used to construct TriggerEvent objects. These 
    will be stored in the 'events' attribute of the neo.Segment objects in src.
    
    TriggerEvent objects emulate a neo.Event: they contain 1D arrays of time 
    values (python Quantity), 1D arraty of strings (labels), and a name.
    
    In addition, they have a TriggerEventType attribute to distinguish between
    presynaptic, postsynaptic, photostimulation and image acquisition 
    trigger events.
    
    Calls detect_trigger_events()
    
    See also: TriggerEvent and TriggerEventType in triggerevent module.
    
    Parameters:
    ===========
    
    src: a neo.Block, a neo.Segment, or a list of neo.Segment objects
    
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
                
            or a valid TriggerEventType enum type, e.g. TriggerEventType.presynaptic
    
    analog_index:   specified which signal to use for event detection; can be one of:
    
                    int (index of the signal array in the data analogsignals)
                        assumes that _ALL_ segments in "src" have the desired analogsignal
                        at the same position in the analogsignals array
    
                    str (name of the analogsignal to use for detection) -- must
                        resolve to a valid analogsignal index in _ALL_ segments in 
                        "src"
                    
                    a sequence of int (index of the signal), one per segment in src 

    (see also detect_trigger_events(), TriggerEventType)
    
    Named parameters:
    =================
    times: either None, or a python quantity array with time units
    
        When "times" is None (the default) the function attempts to detect 
        trigger events by searching for TTL-like pulses in the analogsignal 
        specified by analog_index. The actual waveform search is performed by
        the detect_trigger_events() function in this module.
        
        Otherwise, the values in the "times" array will be used to define the 
        trigger events.
        
    label: common prefix for the individual trigger event label in the event array
            (see also detect_trigger_events())
    
    name: name for the trigger event array 
            (see also detect_trigger_events())
    
    use_lo_hi: boolean, (default is True);  
        when True, use the rising transition to detect the event time stamp
            ("up" logic, see also detect_trigger_events())
        
    time_slice: pq.Quantity tuple (t_start, t_stop) or None.
        When detecting events (see below) the time_slice can specify which part of  
        a signal can be used for automatic event detection.
        
        When time_slice is None this indicates that the events are to be detected 
        from the entire signal.
        
        The elements need to be Python Quantity objects compatible with the domain
        of the signal. For AnalogSignal, this is time (usually, pq.s)
        
    NOTE: The following parameters are passed directly to embed_trigger_event
    
    clear: see auto_detect_trigger_protocols; passed to embed_trigger_event
    
    Returns:
    ========
    The src parameter (a reference)
    
    Side effects:
        Creates and appends TriggerEvent objects to the segments in 'src'.
        The number of events detected (and embedded in 'src') can be retrieved
        using get_trigger_events(src)
    """
    if isinstance(src, neo.Block):
        data = src.segments
        
    elif isinstance(src, (tuple, list)):
        if all([isinstance(o, neo.Segment) for o in src]):
            data = src
            
        elif all([isinstance(o, neo.Block) for o in src]):
            data = chain(*[b.segments for b in src])
            
        else:
            raise TypeError("Expecting a sequence of neo.Block or neo.Segment objects")
        
    elif isinstance(src, neo.Segment):
        data = [src]
        
    else:
        raise TypeError("src expected to be a neo.Block, neo.Segment or a sequence of neo.Block or neo.Segment objects; got %s instead" % type(src).__name__)
    
    if isinstance(times, pq.Quantity):
        # simply construct TriggerEvents based on the supplied time stamps
        # NO SIGNAL PARSING is performed
        if not checkTimeUnits(times):  # event times passed at function call -- no detection is performed
            raise TypeError("times expected to have time units; it has %s instead" % times.units)

        for segment in data: # construct events, store them in segments
            event = TriggerEvent(times=times, units=times.units,
                                    event_type=event_type, labels=label, 
                                    name=name)
            
            embed_trigger_event(event, segment, clear=clear)
            
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
                            and all([isinstance(t, pq.Quantity) and checkTimeUnits(t) for t in time_slice]) \
                                and len(time_slice) == 2:
                                    
                            if reltimes:
                                t0, t1 = (t + s.analogsignals[sndx].t_start for t in time_slice)
                            else:
                                t0, t1 = time_slice
                                
                            event = detect_trigger_events(s.analogsignals[sndx].time_slice(t0, t1), 
                                                        event_type=event_type, 
                                                        use_lo_hi=use_lo_hi, 
                                                        label=label, name=name)
                            
                        else:
                            event = detect_trigger_events(s.analogsignals[sndx], 
                                                        event_type=event_type, 
                                                        use_lo_hi=use_lo_hi, 
                                                        label=label, name=name)
                            
                        if isinstance(event, TriggerEvent):
                            embed_trigger_event(event, s, clear=clear)
                            
                    else:
                        raise ValueError("Invalid signal index %d for a segment with %d analogsignals" % (ndx, len(s.analogsignals)))

        elif isinstance(analog_index, int):
            for ks, s in enumerate(data):
                if analog_index in range(len(s.analogsignals)):
                    if isinstance(time_slice, (tuple, list)) \
                        and all([isinstance(t, pq.Quantity) and checkTimeUnits(t) for t in time_slice]) \
                            and len(time_slice) == 2:
                        # print(f"auto_define_trigger_events:\n")
                        # print(f"signal start {s.analogsignals[analog_index].t_start}")
                        # print(f"signal stop {s.analogsignals[analog_index].t_stop}")
                        # print(f"time slice: {time_slice}")
                        
                        if reltimes:
                            t0, t1 = (t + s.analogsignals[analog_index].t_start for t in time_slice)
                        else:
                            t0, t1 = time_slice
                            
                        event = detect_trigger_events(s.analogsignals[analog_index].time_slice(t0, t1), 
                                                      event_type=event_type, 
                                                      use_lo_hi=use_lo_hi, 
                                                      label=label, name=name)
                        
                    else:
                        event = detect_trigger_events(s.analogsignals[analog_index], 
                                                      event_type=event_type, 
                                                      use_lo_hi=use_lo_hi, 
                                                      label=label, name=name)
                        
                    if isinstance(event, TriggerEvent):
                        embed_trigger_event(event, s, clear=clear)
                    
                else:
                    raise ValueError("Invalid signal index %d for a segment with %d analogsignals" % (analog_index, len(s.analogsignals)))
                
        else:
            raise RuntimeError("Invalid signal index %s" % str(analog_index))

    else:
        raise TypeError("times expected to be a python Quantity array with time units, or None")
                
                
    return src

def get_trigger_events(*src:typing.Union[neo.Block, neo.Segment, typing.Sequence], 
                       as_dict:bool=False, flat:bool=False, 
                       triggers:typing.Optional[typing.Union[str, int, type, typing.Sequence]]=None, 
                       match:str="==") -> list:
    """
    Returns a list of TriggerEvent objects embedded in the data.
    
    Delegates to neoutils.get_events
    
    Variadic Parameters:
    ====================
    *src: neo.Block, neo.Segment, sequence (tuple, list) of neo.Block, sequence  
        (tuple, list) of neo.Segment, or Non
    
    Named Parameters:
    ================
    as_dict:bool (*)
    flat:bool (*)
    triggers: TriggerEventType, str, int, or sequence (tuple, list) of these.
        Optional, default is None
        When None, neoutils.get_events is called with 'triggers=True'
        Otherwise, the value will be passed direcly to the 'triggers' parameter
        of neoutils.et_events.
        
    match:str (*)
    
    (*) Passed directly to neoutils.get_events()
    
    See also: neoutils.get_events()
    
    """
    if triggers is None:
        triggers = True
        
    return get_events(*src, triggers=triggers, as_dict=as_dict, flat=flat, match=match)

# @with_doc(detect_boxcar, use_header=True)
@safeWrapper
def detect_trigger_events(x, event_type, 
                          use_lo_hi=True, 
                          label=None, 
                          name=None):
    """Creates a datatypes.TriggerEvent object (array) of specified type.
    
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
            
    label: str, optional (default None): common label prefix for the individual 
        events in the generated triggerevent.TriggerEvent array
    
    name: str, optional (default  None): the name of the generated 
        triggerevent.TriggerEvent array
    
    Returns:
    ========
    
    A datatypes.TriggerEvent object (essentially an array of time stamps)
    
    """
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
   
    # lo_hi, hi_lo, _, _ , _, upward = detect_boxcar(x)
    boxdetect = detect_boxcar(x)
    # print(f"triggerprotocols.detect_trigger_events boxdetect = {boxdetect}")
    lo_hi, hi_lo, _ampl, _lvl, _lbl, _up = boxdetect
    
    if all([v is None for v in (lo_hi, hi_lo)]):
        return
    
    if use_lo_hi:
        times = lo_hi
        
    else:
        times = hi_lo
        
    if times.size > 1:
        if isinstance(label, str) and len(label.strip()):
            labels = [f"{label}{k}" for k in range(times.size)]
            
        elif isinstance(label, (tuple, list)):
            if len(label) > times.size:
                labels = label[:times.size]
                
            elif len(label) < times.size:
                labels = label + [f"{label[-1]}{k}" for k in range(len(label), times.size)]
                
            else:
                labels = label
                
        else:
            labels = [f"{event_type.name}{k}" for k in range(times.size)]
                
    else:
        labels = label
        
    trig = TriggerEvent(times=times, units=x.times.units, event_type=event_type, labels=labels, name=name)
    
    if name is None:
        # if label is not None:
        if isinstance(label, str) and len(label.strip()):
            trig.name = "%d%s" % (trig.times.size, label)
            
        else:
            if np.all(trig.labels == trig.labels[0]):
                trig.name = "%d%s" % (trig.times.size, label)
                
            else:
                trig.name = f"{trig.times.size}{event_type.name}"
                # trig.name = event_type.name
                
#         else:
#             trig.name = event_type.name
#                 
    elif isinstance(name, str) and len(name.strip()):
        trig.name = name
                
    return trig
    
    

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


def embed_trigger_event(event, segment, clear=False): 
    """
    Embeds the neo.Event object event in the neo.Segment object segment.
    
    In the segment's events list, the event is stored by reference.
    
    WARNING: one could easily append events with identical time stamps!
        While this is NOT recommended and it can be easily prevented by setting
        the "clear" parameer to "same", in which case the new trigger events
        will replace the old ones
        
        To add time stamps to a TriggerEvent, create a new TriggerEvent object
        by calling use TriggerEvent.append_times() or TriggerEvent.merge() then 
        embed it here.
        
        To add time stamps to a generic neo.Event, create a new Event by calling
        Event.merge() then embed it here.
        
        To remove time stamps use numpy array indexing on the event.
        
        See datatypes.TriggerEvent for details.
    
    Parameters:
    ===========
    
    event: a neo.Event, or a datatypes.TriggerEvent
    
    segment: a neo.Segment
    
    Named parameters:
    ===================
    clear: bool, str, TriggerEventType or sequence (tuple, list) - specifies
        the removal of existing events (if any) before embedding the new events.
        
        see auto_detect_trigger_protocols
    
    Returns:
    =======
    A reference to the segment.
    
    """
    if not isinstance(event, (neo.Event, TriggerEvent)):
        raise TypeError("event expected to be a neo.Event; got %s instead" % type(event).__name__)
    
    if not isinstance(segment, neo.Segment):
        raise TypeError("segment expected to be a neo.Segment; got %s instead" % type(segment).__name__)
    
    if isinstance(clear, bool) and clear:
        clear_events(segment)
        
    elif isinstance(clear, str):
        if clear == "all":
            clear_events(segment)
            
        elif clear == "triggers":
            clear_events(segment, triggersOnly=True)
            
        elif clear == "same":
            all_events_ndx = range(len(segment.events))
            evs = [(k,e) for (k,e) in enumerate(segment.events) if (isinstance(e, TriggerEvent) and e.is_same_as(event))]
            
            if len(evs):
                (evndx, events) = zip(*evs)
                
                keep_events = [segment.events[k] for k in all_events_ndx if k not in evndx]
                
                segment.events[:] = keep_events
                
        elif clear in TriggerEventType.names():
            clear_events(segment, triggerType=TriggerEventType[clear])
            
        else:
            raise ValueError("Cannot understand 'clear' parameter %s", clear)
        
    elif isinstance(clear, (TriggerEventType, tuple, list)):
        clear_events(segment, triggerType = clear) # see NOTE: 2021-01-06 12:38:32
        
    segment.events.append(event)
    
    return segment
            
        
@safeWrapper
def embed_trigger_protocol(protocol:TriggerProtocol, 
                           target:typing.Union[neo.Block, neo.Segment, typing.Sequence[neo.Segment]], 
                           useProtocolSegments:bool=True, 
                           clearTriggers:bool=True, 
                           clearEvents:bool=False):
    """ Embeds TriggerEvent objects found in the TriggerProtocol 'protocol', 
    in the segments of the neo.Block object 'target'.
    
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
    # TODO: 2021-10-11 14:24:47
    # replace clearEvents, clearTriggers with clear and pass on to neoutils.clear_events
    # check if there are synaptic events already in the scans data target:
    # each segment can hold at most one TriggerEvent object of each 
    # type (pre-, post-, photo-);
    # NOTE: a TriggerEvent actually holds an ARRAY of time points
    
    # NOTE: check parameters
    if not isinstance(protocol, TriggerProtocol):
        raise TypeError("'protocol' expected to be a TriggerProtocol; got %s instead" % type(protocol).__name__)
    
    if not isinstance(target, (neo.Block, neo.Segment)):
        raise TypeError("'target' was expected to be a neo.Block or neo.Segment; got %s instead" % type(target).__name__)
    
    if isinstance(target, neo.Block):
        segments = target.segments
        
        if len(protocol.segmentIndices()) > 0:
            value_segments = [i for i in protocol.segmentIndices() if i in range(len(segments))]
            
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
        
    if len(segments) == 0:
        return
    
    if len(value_segments) == 0:
        return
        
    for k in value_segments: 
        if clearTriggers:
            clear_events(segments[k], triggers=True)
                
        elif clearEvents:
            clear_events(segments[k])
            
        # now append events contained in protocol
        
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
def parse_trigger_protocols(src, return_source:typing.Optional[bool]=False):
    """Constructs a list of TriggerProtocol objects from embeded TriggerEvent objects.
    
    "src" may be a neo.Segment, neo.Block, a sequence of neo.Segment, or a
    sequence of neo.Block.
    
    Parameters:
    ==========
    "src": neo.Block with a non-empty segments list, or 
           neo.Segment, or
           sequence (tuple, list) of neo.Block
           sequence (sutple, list) of neo.Segment
           
    return_source:bool, optional, default is False
    
        When true, returns a list of TriggerProtocols, _AND_ a reference to 'src'
        
    Returns:
    =======
    When return_source is True:
        tuple (list, src)
        
    Otherwise, a list
    
    In both cases the list containes TriggerProtocol objects or is empty.
        
    ATTENTION: this constructs TriggerProtocol objects with default names.
    Usually this is NOT what you want but their names can be changed to a more 
    meaningful value after their creation.
    
    Individual TriggerEvent objects can be manually appended to the events 
        list of each neo.Segment.
    
    Alternatively, the function detect_boxcar() can help generate 
    TriggerEvent objects from specific neo.AnalogSignal arrays containing 
    trigger-like data (i.e., signals with transitions between a low and 
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
            When a trigger protocol, just update it (especially the segment indices)
            else: create a new TriggerProtocol
            
        index: int or None (default): index of segment in the collection; will
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
                    
            elif e.event_type == TriggerEventType.postsynaptic:
                if protocol.postsynaptic is None:
                    protocol.postsynaptic = e

                    pr_names.append(e.name)
                    pr_first.append(e.times.flatten()[0])
                        
            elif e.event_type == TriggerEventType.photostimulation:
                if protocol.photostimulation is None:
                    protocol.photostimulation = e

                    pr_names.append(e.name)
                    pr_first.append(e.times.flatten()[0])
                    
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
            
            if isinstance(index, Real):
                protocol.segmentIndex = int(index)
                
            if len(protocol_list) == 0:
                protocol_list.append(protocol)
                
            else:
                pp = [p_ for p_ in protocol_list if p_.hasSameEvents(protocol) and p_.imagingDelay == protocol.imagingDelay]
                
                if len(pp):
                    for p_ in pp:
                        p_.updateSegmentIndex(protocol.segmentIndices())
                        #print("p_", p_)
                        
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
                
    elif isinstance(src, (tuple, list)):
        if all([isinstance(v, neo.Segment) for v in src]):
            trigs = [ (k, [e for e in s.events if isinstance(e, TriggerEvent)]) \
                            for k,s in enumerate(src) if len(s.events)]
            
        elif all([isinstance(v, neo.Block) for v in src]):
            # NOTE: 2021-01-04 11:13:46:
            # detect/define trigger protocols in a list of neo.Blocks:
            # (ATTENTION: theblocks are NOT concatenated, therefore the segment
            # indices of the detected/defined protocols are inside each Block!)
            
            # sequence-block-segment indexing array 
            sqbksg = np.array([(q, *kg) for q, kg in enumerate(enumerate(chain(*((k for k in range(len(b.segments))) for b in src))))])
            
            trigs = [(sqbksg[k,2], [e for e in src[sqbksg[k,1]].segments[sqbksg[k,2]].events if isinstance(e, TriggerEvent)]) for k in sqbksg[:,0]]
            
        else:
            raise TypeError("Expecting a sequence of neo.Block or neo.Segment objects")
        
        # TODO: FIXME check/dump src return
        
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
            
    if return_source is True:
        return protocols, src
    
    return protocols

# @with_doc(auto_define_trigger_events, use_header=True)
def auto_detect_trigger_protocols(data: typing.Union[neo.Block, neo.Segment, typing.Sequence[neo.Block], typing.Union[neo.Segment]], 
                                  presynaptic:tuple=(), 
                                  postsynaptic:tuple=(), 
                                  photostimulation:tuple=(), 
                                  imaging:tuple=(), 
                                  clear:typing.Union[bool, str, int, tuple, list, ]=False, 
                                  up=True, protocols=True,
                                  reltimes:bool=True) -> typing.Optional[typing.List[TriggerProtocol]]:
    
    """Determines the set of trigger protocols in a neo.Block by searching for 
    trigger waveforms in the analogsignals contained in 'data'.
    
    Time stamps of the detected trigger protocols will then be used to construct
    TriggerEvent objects according to which of the keyword parameters below
    have been specified.
    
    Positional parameters:
    =====================
    
    data: a neo.Block, neo.Segment, or sequence (tuple, list) of either neo.Block
        or neo.Segment objects.
            
    Named parameters:
    =================
    
    presynaptic, postsynaptic, photostimulation, imaging: tuple
        Detection parameters, respectively, for the pre-, postsynaptic, 
        photostimulation and imaging trigger event types. 
    
        Each is a tuple with 0 (default), two, or three elements:
        
            (signal_index, label, (t_start, t_stop))
        
        This tuple specifies the following:
        
        • signal_index: int or str: index or name of the analog signal in 
            the Segments in 'data' where trigger event waveforms are searched.
            This signal is expected to contain a recording of the TTL 'pulses'
            emitted through the digital output of the acqusition board. Such
            recordings are made by 'branching' out the signal from the digital
            output, into an analog input port of the acquisition board.
        
        • label: str, a common label for the detected trigger events
        
        • (t_start, t_stop): quantities with time units, specifying the time 
            interval, within the signal, where the TTL waveforms will be 
            searched.

        In particular, the imaging trigger event also determines the delay
        between the acquisition of image and electrophysiology data, in experiments
        where imaging is synchronized with electrophysiology.
        
        Their values are passed along to the auto_define_trigger_events,
        detect_trigger_events, and detect_boxcar functions.

        When empty, no events of the specified type will be constructed.
        
        The tuple elements are as follows:
        ---------------------------------
        
        signal_index: int = the index of the analog signal in a Segment's 
            'analogsignals' attribute, where the trigger-like waveforms were
            recorded.
            
            A trigger-like waveform is a rectangular pulse, or a train
            of rectangular pulses with polarity (upward or downward) specified 
            by the 'up' parameter, which emulate a TTL signal.
            
            Currently, the functions supports only the "up" logic i.e., 
            upward-going TTL-like waveforms.
        
        label: str = a label to be assigned to the detected event
        
        (t_start, t_stop): pair of python Quantity objects defining a time slice
            or interval, of the signal, where the events are to be detected.
            
            This is optional. When given, the search for TTL-like waveforms 
            is restricted to the time interval between t_start and t_stop 
            (t_start is included in the interval). 
            
            Otherwise, by default, TTL-like waveforms are searched along the 
            entire duration of the signal.
            
            Recommended for signals that contain additional waveforms or are too 
            noisy.
        
    clear: bool, str, TriggerEventType or sequence (tuple, list) - specifies
        the removal of existing events (if any) before detecting TriggerEvents.
        ATTENTION: The event removal is done on ALL data segments.
        
        Optional (default is False).
        
        When False (default), the detected trigger event arrays will be appended
        to the list of neo.Event objects in the data segments. This list is the 
        'events' attribute of the neo.Segment objects.
        
        When True, all events will be removed before detecting trigger events.
        
        When a str, the allowed values are (WARNING: case-sensitive, and no 
                    spurious spaces):
            "all"       => same effect as when 'clear' is True
            
            "triggers"  => remove all existing TriggerEvents regardless of their 
                            TriggerEventType; other neo.Event objects are retained.
                            
            "same"      => remove trigger events that have values identical to  
                            the ones of the newly-created evets here; the
                            identity test checks for the length and values of the
                            time stamps, and the values of the event labels.
                            
            a valid TriggerEventType string (e.g. "presynaptic", "postsynaptic",
                etc., see triggerevent.TriggerEventType for details)
                        => remove only trigger event of the specified type
                
        When a sequence, its elements may be (type mixing is not allwed):
            * str = valid TriggerEventType strings as described above
            * TriggerEventType values
                NOTE: TriggerEventType is an enum.IntEnum;
                see triggerevent.TriggerEventType for details
                
    up:bool, optional (default is True). Specifies the direction of TTL-like 
        waveforms
        When True, TTL-like waveforms are expected to follow an "up" logic 
        (i.e., they are low-to-high, or upwards deflections).
        
    protocols:bool, default is True
        When True, the function also constructs and returns a list of 
        TriggerProtocol objects.
        
        When False, the function only detects (and embeds) trigger events in the
        data. TriggerProtocol objects can then be parsed from the data by
        calling parse_trigger_protocols() at a separate stage.
        
    reltimes:bool (default True). Indicates if the `t_start` and `t_stop` values
        in the detection parameter tuples are relative to the signal start, or
        absoule time values.
                
    Returns:
    =======
    When protocols is True, returns a list of trigger protocols; otherwise, 
    returns None
        
    CAUTION: When there is no TTL-like waveform, a large number of false-positive
        events will be "detected" - likely due to noise in the signal.
        
    WARNING: if running this is a loop iterated over the segments of a block,
        caling this function for each segment individually will assign the 
        'segment' index to 0 in the detected trigger protocol. Make sure you
        correct for that, accordingly.
        
    """
    # NOTE: 2021-01-06 11:28:23 NEW: introduced "up" parameter - to use the
    # ability to detect negative pulses ("down" logic); 
            
    # NOTE: 2021-01-06 13:54:58
    # any admissible value of 'clear' except for "same" is used here; then, the
    # call to auto_define_trigger_events() below gets 'clear' as either False
    # (if 'clear' has been used here) or as "same", which instructs the 
    # auto_define_trigger_events() function to, respectively, do nothing or to
    # remove existing triggers when they have identical parameters as the 
    # newly-created ones.
    if isinstance(clear, bool) and clear:
        clear_events(data)
        clear = False

    elif isinstance(clear, (TriggerEventType, str,  int, tuple, list)):
        if isinstance(clear, str) and clear in ("triggers", "all"):
            clear = True
        # NOTE: 2021-01-06 12:38:32
        # specifying triggerType implies triggersOnly is True
        clear_events(data, triggers = clear)
        # also, clear_events raises error if clear is a non compliant sequence
        clear = False
        
    if not all(isinstance(v, tuple) and len(v) in (0,2,3) for v in (presynaptic, postsynaptic, 
                                              photostimulation, imaging)):
        raise TypeError(f"All trigger specifications must be tuples with 0, 2 or 3 elements")
        
    # collect trigger parameter tuples in a mapping, to iterate
    tpars = {"presynaptic": presynaptic,
             "postsynaptic": postsynaptic,
             "photostimulation":photostimulation,
             "imaging_frame":imaging}
    
    # NOTE: 2019-03-14 21:43:21
    # depending on the length of the tuple in the keyword parameters
    # we detect events in the whole signal or we limit detetion to a defined 
    # time-slice of the signal
    
    # iterate through trigger parameter tuples - example given here for one loop
    # to be explicit:
    #### if len(presynaptic) >= 2:
    ####    pfun = partial(auto_define_trigger_events, event_type = "presynaptic", 
    ####               analog_index = presynaptic[0], label = presynaptic[1], 
    ####               use_lo_hi=up, clear=clear)
        
    ####    if len(presynaptic) == 3:
    ####        pfun(data, time_slice = presynaptic[2])
    ####    else:
    ####        pfun(data)
    
    for p_name, p_tuple in tpars.items():
        if len(tpars[p_name]) >= 2: # skip empty trigger spec
            pfun = partial(auto_define_trigger_events, event_type = p_name, 
                        analog_index = p_tuple[0], label = p_tuple[1], 
                        use_lo_hi=up, clear=clear)
            
            if len(p_tuple) == 3:
                if not isinstance(p_tuple[2], tuple) or len(p_tuple[2]) != 2 or (not all(isinstance(v_, pq.Quantity) and unitsConvertible(v_, pq.s) for v_ in p_tuple[2])):
                    raise ValueError(f"When specified, the third element in a {p_name} trigger specification must have exactly two time quantities")
                pfun(data, time_slice = p_tuple[2])
                
            else:
                pfun(data)
                
    if protocols:
        tp = parse_trigger_protocols(data)
        return tp
    

#### END Module-level functions
        

