"""Small patches to neo.Epoch and neo.Events
"""

#__all__ = ["neo"]

import inspect
from copy import deepcopy, copy
import numpy as np
import quantities as pq

import neo
from neo.core.baseneo import BaseNeo, _check_annotations
#from neo.rawio.baserawio import (BaseRawIO, _signal_channel_dtype, _unit_channel_dtype,
                        #_event_channel_dtype)

#from core.axonrawio_patch import AxonRawIO_v1
from core.neoevent import (_new_Event_v1, _new_Event_v2,)
from core.neoepoch import _new_Epoch_v1

from core.prog import (safeWrapper, classify_signature,)

#neo.io.axonio.AxonRawIO = _axonrawio.AxonRawIO_v1

original ={"neo.core.analogsignal._new_AnalogSignalArray": neo.core.analogsignal._new_AnalogSignalArray,
           "neo.core.irregularlysampledsignal._new_IrregularlySampledSignal":neo.core.irregularlysampledsignal._new_IrregularlySampledSignal,
           "neo.core.spiketrain._new_spiketrain":neo.core.spiketrain._new_spiketrain,
           "neo.core.epoch._new_epoch": neo.core.epoch._new_epoch,
           "neo.core.event._new_event": neo.core.event._new_event,
           } 

def _normalize_array_annotations_v1(value, length):
    """Check consistency of array annotations

    Recursively check that value is either an array or list containing only "simple" types
    (number, string, date/time) or is a dict of those.

    Args:
        :value: (np.ndarray, list or dict) value to be checked for consistency
        :length: (int) required length of the array annotation

    Returns:
        np.ndarray The array_annotations from value in correct form

    Raises:
        ValueError: In case value is not accepted as array_annotation(s)

    """
    
    print("_normalize_array_annotations_v1 value", value, "length", length)

    # First stage, resolve dict of annotations into single annotations
    if isinstance(value, dict):
        for key in value.keys():
            if isinstance(value[key], dict):
                raise ValueError("Nested dicts are not allowed as array annotations")

            value[key] = _normalize_array_annotations_v1(value[key], length)

    elif value is None:
        raise ValueError("Array annotations must not be None")
    # If not array annotation, pass on to regular check and make it a list, that is checked again
    # This covers array annotations with length 1
    elif not isinstance(value, (list, np.ndarray)) or (
            isinstance(value, pq.Quantity) and value.shape == ()):
        _check_annotations(value)
        value = _normalize_array_annotations_v1(np.array([value]), length)

    # If array annotation, check for correct length, only single dimension and allowed data
    else:
        # Get length that is required for array annotations, which is equal to the length
        # of the object's data
        own_length = length

        # Escape check if empty array or list and just annotate an empty array (length 0)
        # This enables the user to easily create dummy array annotations that will be filled
        # with data later on
        if len(value) == 0:
            if not isinstance(value, np.ndarray):
                value = np.ndarray((0,))
            val_length = own_length
        else:
            # Note: len(o) also works for np.ndarray, it then uses the first dimension,
            # which is exactly the desired behaviour here
            val_length = len(value)

        if not own_length == val_length:
            raise ValueError(
                "Incorrect length of array annotation: {} != {}".format(val_length, own_length))

        # Local function used to check single elements of a list or an array
        # They must not be lists or arrays and fit the usual annotation data types
        def _check_single_elem(element):
            # Nested array annotations not allowed currently
            # If element is a list or a np.ndarray, it's not conform except if it's a quantity of
            # length 1
            if isinstance(element, list) or (isinstance(element, np.ndarray) and not (
                    isinstance(element, pq.Quantity) and (
                    element.shape == () or element.shape == (1,)))):
                raise ValueError("Array annotations should only be 1-dimensional")
            if isinstance(element, dict):
                raise ValueError("Dictionaries are not supported as array annotations")

            # Perform regular check for elements of array or list
            _check_annotations(element)

        # Arrays only need testing of single element to make sure the others are the same
        if isinstance(value, np.ndarray):
            # Type of first element is representative for all others
            # Thus just performing a check on the first element is enough
            # Even if it's a pq.Quantity, which can be scalar or array, this is still true
            # Because a np.ndarray cannot contain scalars and sequences simultaneously

            # If length of data is 0, then nothing needs to be checked
            if len(value):
                # Perform check on first element
                _check_single_elem(value[0])

            return value

        # In case of list, it needs to be ensured that all data are of the same type
        else:
            # Conversion to numpy array makes all elements same type
            # Converts elements to most general type

            try:
                value = np.array(value)
            # Except when scalar and non-scalar values are mixed, this causes conversion to fail
            except ValueError as e:
                msg = str(e)
                if "setting an array element with a sequence." in msg:
                    raise ValueError("Scalar values and arrays/lists cannot be "
                                     "combined into a single array annotation")
                else:
                    raise e

            # If most specialized data type that possibly fits all elements is object,
            # raise an Error with a telling error message, because this means the elements
            # are not compatible
            if value.dtype == object:
                raise ValueError("Cannot convert list of incompatible types into a single"
                                 " array annotation")

            # Check the first element for correctness
            # If its type is correct for annotations, all others are correct as well
            # Note: Emtpy lists cannot reach this point
            _check_single_elem(value[0])

    return value

def _new_AnalogSignalArray_v2(cls, signal, units=None, dtype=None, copy=True, t_start=0 * pq.s,
                           sampling_rate=None, sampling_period=None, name=None, file_origin=None,
                           description=None, array_annotations=None, annotations=None,
                           channel_index=None, segment=None):
    '''
    A function to map AnalogSignal.__new__ to function that
        does not do the unit checking. This is needed for pickle to work.
    '''
    
    if isinstance(array_annotations, dict) and annotations is None:
        annotations = deepcopy(array_annotations)
        array_annotations = None
    
    if annotations is None:
        annotations = dict()
    #elif isinstance(annotations, neo.ChannelIndex):
        #channel_index = annotations
        #annotations =dict()
        
        
    #if array_annotations is None:
        #array_annotations = dict()
        
    #print(type(annotations))
    
    obj = cls(signal=signal, units=units, dtype=dtype, copy=copy,
            t_start=t_start, sampling_rate=sampling_rate,
            sampling_period=sampling_period, name=name,
            file_origin=file_origin, description=description,
            array_annotations=array_annotations, **annotations)
    
    obj.channel_index = channel_index
    obj.segment = segment
    return obj

def _new_AnalogSignalArray_v1(cls, signal, units=None, dtype=None, copy=True, 
                              t_start=0 * pq.s, 
                              sampling_rate=None, sampling_period=None, name=None, 
                              file_origin=None,
                              description=None, annotations=None, 
                              channel_index=None, segment=None):
    '''
    A function to map AnalogSignal.__new__ to function that
        does not do the unit checking. This is needed for pickle to work.
    '''
    obj = cls(signal=signal, units=units, dtype=dtype, copy=copy,
            t_start=t_start, sampling_rate=sampling_rate,
            sampling_period=sampling_period, name=name,
            file_origin=file_origin, description=description,
            **annotations)

    obj.channel_index = channel_index
    obj.segment = segment
    return obj

def _new_AnalogSignalArray(*args, **kwargs):
    #print("kwargs", kwargs)
    original_f = original["neo.core.analogsignal._new_AnalogSignalArray"]
    sig = classify_signature(original_f)
    sig_named = list(sig.named.keys())
    named = dict()
    var = list()
    #varkw = dict()
    
    #k = 0
    
    # first eat up the *args - CAUTION these may contain named params, but 
    # 'without' the names ... place these into args
    
    for k, a in enumerate(args):
        if k < len(sig.positional):
            var.append(a)
            
        elif k in range(len(sig.positional), len(sig_named)):
            var.append(a)
            #name = sig_named[k-len(sig.positional)]
            #val = sig.named[name]
            #named[name] = a
        
        # NOTE: if there is an excess of positional parameters, leave them out
        #else:
            #var.append(a)
    # now eat up kwargs - distribute across named or a new kw
    kw = list(kwargs.keys())
    
    for k in kw:
        v = kwargs.pop(k)
        if k in sig.named:
            named[k] = v
            
    #print("var", var)
    #print("named", named)
    #print("kwargs", kwargs)
    #print(sig)
            
    return original["neo.core.analogsignal._new_AnalogSignalArray"](*var, **named, **kwargs)

def _new_spiketrain_v1(cls, signal, t_stop, units=None, dtype=None, copy=True,
                    sampling_rate=1.0 * pq.Hz, t_start=0.0 * pq.s, waveforms=None, left_sweep=None,
                    name=None, file_origin=None, description=None, array_annotations=None,
                    annotations=None, segment=None, unit=None):
    '''
    A function to map :meth:`BaseAnalogSignal.__new__` to function that
    does not do the unit checking. This is needed for :module:`pickle` to work.
    '''
    if annotations is None:
        annotations = {}
        
    if isinstance(array_annotations, dict): # these in fact are the annotations in the old API
        annotations = array_annotations
        
        obj = neo.SpikeTrain(signal, t_stop, units, dtype, copy, sampling_rate, t_start, waveforms,
                            left_sweep, name, file_origin, description, **annotations)
        
    else:
        obj = neo.SpikeTrain(signal, t_stop, units, dtype, copy, sampling_rate, t_start, waveforms,
                        left_sweep, name, file_origin, description, array_annotations, **annotations)
        
    obj.segment = segment
    obj.unit = unit
    return obj

def _new_IrregularlySampledSignal_v1(cls, times, signal, units=None, time_units=None, dtype=None,
                                  copy=True, name=None, file_origin=None, description=None,
                                  array_annotations=None, annotations=None, segment=None,
                                  channel_index=None):
    '''
    A function to map IrregularlySampledSignal.__new__ to a function that
    does not do the unit checking. This is needed for pickle to work.
    '''
    if annotations is None:
        annotations = {}
        
    if isinstance(array_annotations, dict): # these in fact are the annotations in the old API
        annotations = array_annotations
        
        iss = cls(times=times, signal=signal, units=units, time_units=time_units, dtype=dtype,
                copy=copy, name=name, file_origin=file_origin, description=description,
                **annotations)
        
    else:
        iss = cls(times=times, signal=signal, units=units, time_units=time_units, dtype=dtype,
                copy=copy, name=name, file_origin=file_origin, description=description,
                array_annotations=array_annotations, **annotations)
        
    iss.segment = segment
    iss.channel_index = channel_index
    return iss

# FIXME 2020-11-18 23:47:38
# I don't think patching _new_event is necessary
#patches = {"neo.io.axonio.AxonRawIO": AxonRawIO_v1,
           #"neo.core.analogsignal._new_AnalogSignalArray": _new_AnalogSignalArray_v2,
           #"neo.core.irregularlysampledsignal._new_IrregularlySampledSignal": _new_IrregularlySampledSignal_v1,
           #"neo.core.spiketrain._new_spiketrain": _new_spiketrain_v1,
           #"neo.core.epoch._new_epoch": _new_Epoch_v1,
           #"neo.core.event._new_event": _new_Event_v2}
           
patches = {"neo.core.analogsignal._new_AnalogSignalArray": _new_AnalogSignalArray,
           "neo.core.irregularlysampledsignal._new_IrregularlySampledSignal": _new_IrregularlySampledSignal_v1,
           "neo.core.spiketrain._new_spiketrain": _new_spiketrain_v1,
           "neo.core.epoch._new_epoch": _new_Epoch_v1,
           "neo.core.event._new_event": _new_Event_v2,
           }

@safeWrapper
def patch_neo_new():
    for key, value in patches.items():
        try:
            objpath = key.split('.')
            fname = objpath[-1]
            module = eval('.'.join(objpath[:-1]))
            if inspect.ismodule(module):
                setattr(module, fname, value)
                
        except:
            print(f"Cannot patch function {key}")
            raise
            
@safeWrapper
def restore_neo_new():
    for key, value in original.items():
        try:
            objpath = key.split('.')
            fname = objpath[-1]
            module = eval('.'.join(objpath[:-1]))
            if inspect.ismodule(module):
                setattr(module, fname, value)
                
        except:
            print(f"Cannot restore patched function {key}")
            raise
            
        
