# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Small patches to neo.Epoch and neo.Events
"""

#__all__ = ["neo"]
import sys, os
import traceback
import inspect
import importlib
from functools import partial
from copy import deepcopy, copy
import numpy as np
import quantities as pq
from colorama import Fore, Back, Style
# import termcolor

import neo
from neo.core.baseneo import BaseNeo, _check_annotations
#from neo.rawio.baserawio import (BaseRawIO, _signal_channel_dtype, _unit_channel_dtype,
                        #_event_channel_dtype)

#from core.axonrawio_patch import AxonRawIO_v1
# # from core.neoevent import (_new_Event_v1, _new_Event_v2,)
import core
from core.workspacefunctions import scipyentopdir
from core.neoevent import Event
# # from core.neoepoch import _new_Epoch_v1
from core import neoepoch
from core.neoepoch import Epoch, _new_Epoch

# print(f"_new_Epoch: {_new_Epoch.__name__} in {_new_Epoch.__module__}")
from core.prog import (safeWrapper, signature2Dict, SpecFinder)

# #neo.io.axonio.AxonRawIO = _axonrawio.AxonRawIO_v1

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
    """Workarounds to load pickled neo data created a long time ago..."""
    # All params in neo's _new_* factory functions are NAMED !!!
    # since this 'patches' _new_* functions, the first element in args is
    # the actual class of the array type being created:
    
    cls = args[0]
    # print(f"\n_patch_new_neo for class {Fore.GREEN}{cls.__name__}:{Style.RESET_ALL}")
    
    # print(f"_patch_new_neo original_f: {original_f}")
    
    sig = signature2Dict(original_f)
    # print(f"originalsignature: {sig}\n")
    # print(f" {len(sig.positional)} positional parameters\n")
    sig_named = list(sig.named.keys())
    # print(f" {len(sig_named)} named parameters = {sig_named}\n")
    # named = dict()
    var = list()
    
    # first eat up the *args - CAUTION these may contain named params, but 
    # 'without' the names ... place these into args
    
    for k, a in enumerate(args):
        # NOTE: 2024-02-03 14:04:06 skip ChannelIndex
        # the module is reinstated temporarily so that pickle can find the 
        # definition of ChannelIndex; however, snce its removal from neo package,
        # neo object constructurs are oblivious to ChannelIndex
        if k < len(sig.positional):
            if type(a).__name__ == "ChannelIndex":
                var.append(None)
            else:
                var.append(a)
            
        elif k in range(len(sig.positional), len(sig_named)):
            var.append(a)
        
        # NOTE: if there is an excess of positional parameters, leave them out
        #else:
            #var.append(a)
            
    annotations_index = sig_named.index("annotations")
    # print(f" annotations_index = {annotations_index}")
    array_annotations_index = sig_named.index("array_annotations")
    # print(f" array_annotations_index = {array_annotations_index}")
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
            
    if not isinstance(var[annotations_index], dict):
        var[annotations_index] = dict()
            
    # print(f" {Fore.YELLOW}{original_f.__name__}{Style.RESET_ALL} will be called with {len(var)} arguments:")
    # for k in range(len(var)):
    #     arg_name = f" ({sig_named[k]})" #if k in sig.named else ""
    #     print(f"  {k}: {var[k]}{arg_name}")
            
    try:
        return original_f(*var)
    except Exception as e:
        if isinstance(e, ValueError):
            if "Incorrect length of array annotation" in str(e):
                # swap annotations with array annotations
                tmp = var[array_annotations_index]
                var[array_annotations_index] = dict()
                var[annotations_index] = tmp
                return original_f(*var)
            
            if "Array annotations must not be None" in str(e):
                var[array_annotations_index] = dict()
                return original_f(*var)
            
        raise
                

patches = dict((k, partial(_patch_new_neo, v)) for k,v in original.items())

# print(f"module patchneo: patches = {patches}")

def patch_channelindex():
    file_name = os.path.join(scipyentopdir(), "legacy", "neo", "core", "channelindex.py")
    module_name = inspect.getmodulename(file_name)
    module_spec = importlib.util.spec_from_file_location(module_name, file_name)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules["neo.core.channelindex"] = module
    module_spec.loader.exec_module(module)
    specFinder = SpecFinder({})
    specFinder.path_map[module_name] = file_name
    sys.meta_path.append(specFinder)

def unpatch_channelindex():
    sys.modules.pop("neo.core.channelindex", None)
    file_name = os.path.join(scipyentopdir(), "legacy", "neo", "core", "channelindex.py")
    module_name = inspect.getmodulename(file_name)
    
    finders_for_modules = [p for p in sys.meta_path if (hasattr(p, "path_map") and module_name in p.path_map.keys())]
    
    for i in finders_for_modules:
        ndx = sys.meta_path.index(i)
        del sys.meta_path[ndx]
        
@safeWrapper
def patch_neo_new():
#     from legacy.neo.core import channelindex
#     neo.core.channelindex = channelindex
#     
#     print(f"channelindex: {channelindex}")
#     print(f"neo.core.channelindex: {neo.core.channelindex}")
    
    # patch_channelindex()
    
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
            # print(f"\npatch_neo_new:\n\tkey = {key},\n\tobjpath = {objpath},\n\tmodule = {module}")
            if inspect.ismodule(module):
                setattr(module, fname, value)
                
        except:
            print(f"\nCannot patch function {key}\n")
            traceback.print_exc()
            raise
            
@safeWrapper
def restore_neo_new():
    # unpatch_channelindex()
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
            
        
