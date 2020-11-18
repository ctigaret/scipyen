# -*- coding: utf-8 -*-
'''
Decorators, context managers, and helper functions & classes for programming
'''

#print("{}: {}".format(__file__, __name__))

import enum, io, os, re, itertools, sys, time, traceback, types, typing
import importlib, inspect, pathlib, warnings
from functools import singledispatch, update_wrapper, wraps
from contextlib import (contextmanager, ContextDecorator,)

import neo
from . import patchneo
from . import workspacefunctions
from .workspacefunctions import debug_scipyen
#from . import patchneo as patchneo
#from . import neoevent as neoevent
#from . import neoepoch as neoepoch


class ContextExecutor(ContextDecorator):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
    
#class NeoPatchCtx(ContextDecorator):
    ##from core import patchneo as patchneo
    ##from core import neoevent as neoevent
    ##from core import neoepoch as neoepoch
    
    ##import core.patchneo as patchneo
    ##import core.neoevent as neoevent
    ##import core.neoepoch as neoepoch
    
    #_new_AnalogSignalArray_orig_ = neo.core.analogsignal._new_AnalogSignalArray
    #_new_IrregularlySampledSignal_orig_ = neo.core.irregularlysampledsignal._new_IrregularlySampledSignal
    #_new_spiketrain_orig_ = neo.core.spiketrain._new_spiketrain
    
    #_new_event_orig_ = neo.core.event._new_event
    #Event_orig = neo.core.event.Event
    #Epoch_orig = neo.core.epoch.Epoch
    
    #_normalize_array_annotations_orig_ = neo.core.dataobject._normalize_array_annotations
    
    #def __init__(self):
        ##print("NeoPatchCtx: sys.path =", sys.path)
        ##self.sys_path = sys.path
        #self.scipyen_path = pathlib.Path(sys.path[0])
        
    #def __enter__(self):
        #self.neo_patches = load_patch_modules(self.scipyen_path, "neoevent", "neoepoch", "patchneo")
        
        #neo.core.dataobject._normalize_array_annotations = self.neo_patches["patchneo"]._normalize_array_annotations
        #neo.core.analogsignal._new_AnalogSignalArray = self.neo_patches["patchneo"]._new_AnalogSignalArray_v1
        #neo.core.spiketrain._new_spiketrain = self.neo_patches["patchneo"]._new_spiketrain_v1
        #neo.core.irregularlysampledsignal._new_IrregularlySampledSignal = self.neo_patches["patchneo"]._new_IrregularlySampledSignal_v1
        
        #neo.core.event._new_event = self.neo_patches["neoevent"]._new_event
        #neo.core.event.Event = self.neo_patches["neoevent"].Event
        #neo.core.Event = self.neo_patches["neoevent"].Event
        #neo.io.axonio.Event = self.neo_patches["neoevent"].Event
        #neo.Event = self.neo_patches["neoevent"].Event
        
        #neo.core.epoch.Epoch = self.neo_patches["neoepoch"].Epoch
        #neo.core.Epoch = self.neo_patches["neoepoch"].Epoch
        #neo.Epoch = self.neo_patches["neoepoch"].Epoch
        
        #return self

    #def __exit__(self, *exc):
        ##print ("NeoPatchCtx.__exit__: patchneo in sys.modules =", "patchneo" in sys.modules)
        #neo.core.dataobject._normalize_array_annotations = self._normalize_array_annotations_orig_
        
        #neo.core.analogsignal._new_AnalogSignalArray = self._new_AnalogSignalArray_orig_
        #neo.core.spiketrain._new_spiketrain = self._new_spiketrain_orig_
        #neo.core.irregularlysampledsignal._new_IrregularlySampledSignal = self._new_IrregularlySampledSignal_orig_
        
        #neo.core.event._new_event = self.Event_orig
        #neo.core.event.Event = self.Event_orig
        #neo.core.Event = self.Event_orig
        #neo.io.axonio.Event = self.Event_orig
        #neo.Event = self.Event_orig
        #neo.core.event._new_event = self._new_event_orig_
        
        #neo.core.epoch.Epoch = self.Epoch_orig
        #neo.core.Epoch = self.Epoch_orig
        #neo.Epoch = self.Epoch_orig
        
        #for mname in self.neo_patches:
            #if mname in sys.modules:
                #del sys.modules[mname]
        
        ##if "neoevent" in sys.modules:
            ##del sys.modules["neoevent"]
        
        ##if "neoepoch" in sys.modules:
            ##del sys.modules["neoepoch"]
        
        ##if "patchneo" in sys.modules:
            ##del sys.modules["patchneo"]

        #return False
    
class Timer(object):
    """Recipe 13.13 "Making a Stopwatch Timer" in Python Cookbook 3rd Ed. 2013
    """
    def __init__(self, func = time.perf_counter):
        self.elapsed = 0.0
        self._func = func
        self._start = None
        
    def start(self):
        if self._start is not None:
            raise RuntimeError("Already started")
        
        self._start = self._func()
        
    def stop(self):
        if self._start is None:
            raise RuntimeError("Not started")
        
        end = self._func()
        
        self.elapsed += end - self._start
        self._start = None
        
    def reset(self):
        self.elapsed = 0.0
        
    @property
    def running(self):
        return self._start is not None
    
    def __enter__(self):
        # for use as context manager
        self.start()
        return self
    
    def __exit__(self):
        # for use as context manager
        self.stop()
        
# ### BEGIN module functions

def check_neo_patch(exc_info:tuple):
    stack_summary = traceback.extract_tb(exc_info[2])
    frame_names = [f.name for f in stack_summary]
    
    last_frame_summary = stack_summary[-1]
    
    obj_name = last_frame_summary.name
    
    return identify_neo_patch(obj_name)
    
    #if any([s in last_frame_summary.name.lower() for s in  ("neo", "event", "epoch", "analogsignalarray", "analogsignal", "irregularlysampledsignal")]):
    #if any([s in obj_name.lower() for s in  patchneo.patches.keys()]):
        #module_name = inspect.getmodulename(last_frame_summary.filename)
        
    #for key in patchneo.patches.keys():
        #if obj_name in key:
            #return (key, patchneo.patches[key])
        
def identify_neo_patch(obj_name):
    if debug_scipyen():
        print("\nLooking for possible patch for %s" % obj_name)
        
    for key in patchneo.patches.keys():
        if obj_name in key:
            val = patchneo.patches[key]
            if debug_scipyen():
                print("\t Found patch", val, "for", key)
            return (key, val)
    
    
def import_module(name, package=None):
    """An approximate implementation of import."""
    absolute_name = importlib.util.resolve_name(name, package)
    try:
        return sys.modules[absolute_name]
    except KeyError:
        pass

    path = None
    
    if '.' in absolute_name:
        parent_name, _, child_name = absolute_name.rpartition('.')
        parent_module = import_module(parent_name)
        path = parent_module.__spec__.submodule_search_locations
        
    if debug_scipyen():
        print("import_module: path =", path)
        
    for finder in sys.meta_path:
        if hasattr(finder, "find_spec"):
            spec = finder.find_spec(absolute_name, path)
            if spec is not None:
                break
    else:
        raise ImportError(f'No module named {absolute_name!r}')
        
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[absolute_name] = module
    
    if path is not None:
        setattr(parent_module, child_name, module)
        
    return module

def import_relocated_module(mname):
    spec = get_relocated_module_spec(mname)
    
    if spec is not None:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[mname] = module
    
def get_relocated_module_spec(mname, scipyen_path=None):
        #print("get_relocated_module_spec: modname =", mname)
        
        if isinstance(scipyen_path, str) and os.path.isdir(scipyen_path):
            file_path = os.path.join(*(scipyen_path, "%s.py" % mname))
            
        else:
            if scipyen_path is None:
                scipyen_path = pathlib.Path(sys.path[0]) # this is where scipyen is located
                
            elif not isinstance(scipyen_path, pathlib.Path):
                raise ValueError("scipyen_path expected to be a valid directory path string, a pathlib.Path, or None; got %s instead\n" % scipyen_path)
            
            
            mloc = list(scipyen_path.glob("**/%s.py" % mname))
            
            if len(mloc)==0: # py source file not found
                raise FileNotFoundError("Could not find a module source file for %s\n" % mname)
            
            
            file_path = os.path.join(*mloc[0].parts)
        
        #print("get_relocated_module_spec: file_path =", file_path)
        
        if isinstance(file_path, str) and len(file_path):
            return importlib.util.spec_from_file_location(mname, file_path)
        
def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
    log = file if hasattr(file, "write") else sys.stderr
    traceback.print_stack(file=log)
    log.write(warnings.formatwarning(message, category, filename, lineno, line))
    
# ### END module functions

# ### BEGIN Decorators

def deprecated(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            warnings.warn("%s is deprecated" % f)
            return f(*args, **kwargs)
        
        except Exception as e:
            traceback.print_exc()
            
    return wrapper
    
    

#NOTE: 2017-11-22 22:00:40 FIXME TODO
# for pyqtSlots, place this AFTER the @pyqtSlot decorator
def safeWrapper(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
            
        except Exception as e:
            traceback.print_exc()
            
    return wrapper

def safeGUIWrapper(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        
        except Exception as e:
            s = io.StringIO()
            sei = sys.exc_info()
            traceback.print_exception(file=s, *sei)
            msgbox = QMessageBox()
            msgbox.setIcon(QMessageBox.Critical)
            msgbox.setWindowTitle(sei[0].__class__.__name__)
            msgbox.setText(sei[0].__class__.__name__)
            msgbox.setDetailedText(s.getvalue())
            msgbox.exec()
            
    return wrapper

def timefunc(func):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        r = func(*args, **kwargs)
        end = time.perf_counter()
        print("{}.{} : {}".format(func.__module__, func.__name__, end-start))
        return r
    return wrapper

def processtimefunc(func):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.process_time()
        r = func(*args, **kwargs)
        end = time.process_time()
        print("{}.{} : {}".format(func.__module__, func.__name__, end-start))
        return r
    return wrapper

# ### END Decorators

# ### BEGIN Context managers

@contextmanager
def timeblock(label):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        print("{} : {}".format(label, end-start))

@contextmanager
def processtimeblock(label):
    """Recipe 14.13 "Profiling and Timing Your Programs" 
        From Python Cookbook 3rd Ed. 2013
    """
    start = time.process_time()
    try:
        yield
    finally:
        end = time.process_time()
        print("{} : {}".format(label, end-start))

# ### END Context managers

