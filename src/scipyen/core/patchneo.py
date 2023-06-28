"""Small patches to neo.Epoch and neo.Events
"""

#__all__ = ["neo"]

import inspect
from functools import partial
from copy import deepcopy, copy
import numpy as np
import quantities as pq

import neo
from neo.core.baseneo import BaseNeo, _check_annotations
#from neo.rawio.baserawio import (BaseRawIO, _signal_channel_dtype, _unit_channel_dtype,
                        #_event_channel_dtype)

#from core.axonrawio_patch import AxonRawIO_v1
#from core.neoevent import (_new_Event_v1, _new_Event_v2,)
#from core.neoepoch import _new_Epoch_v1

from core.prog import (safeWrapper, signature2Dict,)

#neo.io.axonio.AxonRawIO = _axonrawio.AxonRawIO_v1

original ={"neo.core.analogsignal._new_AnalogSignalArray": neo.core.analogsignal._new_AnalogSignalArray,
           "neo.core.irregularlysampledsignal._new_IrregularlySampledSignal":neo.core.irregularlysampledsignal._new_IrregularlySampledSignal,
           "neo.core.spiketrain._new_spiketrain":neo.core.spiketrain._new_spiketrain,
           "neo.core.epoch._new_epoch": neo.core.epoch._new_epoch,
           "neo.core.event._new_event": neo.core.event._new_event,
           } 

def _patch_new_neo(original_f, *args, **kwargs):
    sig = signature2Dict(original_f)
    #print(f"sig: {sig}")
    sig_named = list(sig.named.keys())
    named = dict()
    var = list()
    
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
            
    #print(f" var {var}, named {named}, kwargs {kwargs}")
    return original_f(*var, **named, **kwargs)


patches = dict((k, partial(_patch_new_neo, v)) for k,v in original.items())

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
            
        
