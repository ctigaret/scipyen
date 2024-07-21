# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import os, sys
import pathlib
import importlib

from .workspacefunctions import (debug_scipyen, scipyentopdir)

def check_neo_patch(exc_info:tuple):
    stack_summary = traceback.extract_tb(exc_info[2])
    frame_names = [f.name for f in stack_summary]
    
    last_frame_summary = stack_summary[-1]
    
    obj_name = last_frame_summary.name
    
    # print(obj_name)
    
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
        if scipyen_path is None:
            # BUG 2024-02-02 22:09:31 
            # WRONG: this is NOT where scipyen is located
            # scipyen_path = pathlib.Path(sys.path[0]) # this is where scipyen is located 
            scipyen_path = pathlib.Path(scipyentopdir()) # this is where scipyen is located
        #print("get_relocated_module_spec: modname =", mname)
        
        elif isinstance(scipyen_path, str):
            if os.path.isdir(scipyen_path):
                scipyen_path = pathlib.Path(scipyen_path)
            else:
                raise ValueError("'scipyen_path' is not a directory")
            
        elif isinstance(scipyen_path, pathlib.Path):
            if not scipyen_path.is_dir():
                raise ValueError("'scipyen_path' is not a directory")
            
            file_path = os.path.join(*(scipyen_path, "%s.py" % mname))
            
        else:
            raise TypeError(f"'scipyen_path' expected to be a str or pathlib.Path or None; instead, got a {type(scipyen_path).__name__}")
                
            # elif not isinstance(scipyen_path, pathlib.Path):
            #     raise ValueError("scipyen_path expected to be a valid directory path string, a pathlib.Path, or None; got %s instead\n" % scipyen_path)
            
            
        mloc = list(scipyen_path.glob("**/%s.py" % mname))
        
        # print(f"get_relocated_module_spec: mname = {mname}, mloc = {mloc}")
            
        if len(mloc)==0: # py source file not found
            raise FileNotFoundError("Could not find a module source file for %s\n" % mname)
        
            
        file_path = os.path.join(*mloc[0].parts)
        
        #print("get_relocated_module_spec: file_path =", file_path)
        
        if isinstance(file_path, str) and len(file_path):
            return importlib.util.spec_from_file_location(mname, file_path)
        
def get_relocated_module_spec_old(mname, scipyen_path=None):
        #print("get_relocated_module_spec: modname =", mname)
        
        if isinstance(scipyen_path, str) and os.path.isdir(scipyen_path):
            file_path = os.path.join(*(scipyen_path, "%s.py" % mname))
            
        else:
            if scipyen_path is None:
                # BUG 2024-02-02 22:09:31 
                # WRONG: this is NOT where scipyen is located
                # scipyen_path = pathlib.Path(sys.path[0]) # this is where scipyen is located 
                scipyen_path = pathlib.Path(scipyentopdir()) # this is where scipyen is located
                
            elif not isinstance(scipyen_path, pathlib.Path):
                raise ValueError("scipyen_path expected to be a valid directory path string, a pathlib.Path, or None; got %s instead\n" % scipyen_path)
            
            
            mloc = list(scipyen_path.glob("**/%s.py" % mname))
            
            if len(mloc)==0: # py source file not found
                raise FileNotFoundError("Could not find a module source file for %s\n" % mname)
            
            
            file_path = os.path.join(*mloc[0].parts)
        
        #print("get_relocated_module_spec: file_path =", file_path)
        
        if isinstance(file_path, str) and len(file_path):
            return importlib.util.spec_from_file_location(mname, file_path)
        
