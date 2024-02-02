"""Small patches to neo.Epoch and neo.Events
"""

#__all__ = ["neo"]

import traceback
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
# from core.neoevent import (_new_Event_v1, _new_Event_v2,)
import core
from core.neoevent import Event
# from core.neoepoch import _new_Epoch_v1
from core import neoepoch
from core.neoepoch import Epoch, _new_Epoch

print(f"_new_Epoch: {_new_Epoch.__name__} in {_new_Epoch.__module__}")

from core.prog import (safeWrapper, signature2Dict,)

#neo.io.axonio.AxonRawIO = _axonrawio.AxonRawIO_v1

original ={"neo.core.analogsignal._new_AnalogSignalArray": neo.core.analogsignal._new_AnalogSignalArray,
           "neo.core.irregularlysampledsignal._new_IrregularlySampledSignal":neo.core.irregularlysampledsignal._new_IrregularlySampledSignal,
           "neo.core.spiketrain._new_spiketrain":neo.core.spiketrain._new_spiketrain,
           "neo.core.epoch._new_epoch": neo.core.epoch._new_epoch,
           "neo.core.event._new_event": neo.core.event._new_event,
           # "core.neoepoch._new_Epoch": core.neoepoch._new_Epoch,
           # "neoepoch._new_Epoch": neoepoch._new_Epoch,
           # # "_new_Epoch": _new_Epoch,
           } 

def _patch_new_neo(original_f, *args, **kwargs):
    """All params in neo's _new_* factory functions are NAMED !!!"""
    # print(f"_patch_new_neo original_f: {original_f}")
    sig = signature2Dict(original_f)
    # print(f"originalsignature: {sig}\n")
    sig_named = list(sig.named.keys())
    # print(f"named parameters= {sig_named}\n")
    # named = dict()
    var = list()
    
    # first eat up the *args - CAUTION these may contain named params, but 
    # 'without' the names ... place these into args
    
    for k, a in enumerate(args):
        if k < len(sig.positional):
            var.append(a)
            
        elif k in range(len(sig.positional), len(sig_named)):
            var.append(a)
        
        # NOTE: if there is an excess of positional parameters, leave them out
        #else:
            #var.append(a)
            
    annotations_index = sig_named.index("annotations")
    # print(f"_patch_new_neo annotations_index = {annotations_index}")
    # now eat up kwargs - distribute across named or a new kw
    kw = list(kwargs.keys())
    
    for k in kw:
        v = kwargs.pop(k)
        if k in sig.named:
            # named[k] = v
            # CAUTION: 2024-02-02 16:35:41
            # could overwrite staff in vars
            k_ndx = sig_named.index(k)
            var[k_ndx] = v
            
    if len(kwargs):
        # merge unused kwargs into annotations
        if isinstance(var[annotations_index], dict):
            var[annotations_index].update(kwargs)
        else:
            var[annotations_index] = kwargs
            
    if var[annotations_index] is None:
        var[annotations_index] = dict()
            
    # print(f"_patch_new_neo vars {original_f.__name__} will be called with {len(var)} arguments:")
    # for k in range(len(var)):
    #     print(f"{k}: {var[k]}")
            
    return original_f(*var)

patches = dict((k, partial(_patch_new_neo, v)) for k,v in original.items())

# print(f"module patchneo: patches = {patches}")

@safeWrapper
def patch_neo_new():
    for key, value in patches.items():
        try:
            if '.' in key:
                objpath = key.split('.')
                # print(f"objpath: {objpath}")
                fname = objpath[-1]
                module = eval('.'.join(objpath[:-1]))
            else:
                objpath = key
                fname = value.args[0].__name__ # NOTE: 2024-02-02 23:34:15 value is a partial!
                module = value.args[0].__module__
            print(f"patch_neo_new:\n\tkey = {key},\n\tobjpath = {objpath},\n\tmodule = {module}")
            if inspect.ismodule(module):
                setattr(module, fname, value)
                
        except:
            print(f"\nCannot patch function {key}\n")
            traceback.print_exc()
            raise
            
@safeWrapper
def restore_neo_new():
    for key, value in original.items():
        try:
            if '.' in key:
                objpath = key.split('.')
                fname = objpath[-1]
                module = eval('.'.join(objpath[:-1]))
            else:
                objpath = key
                fname = value.args[0].__name__
                module = value.args[0].__module__
            if inspect.ismodule(module):
                setattr(module, fname, value)
                
        except:
            print(f"\nCannot restore patched function {key}\n")
            traceback.print_exc()
            raise
            
        
