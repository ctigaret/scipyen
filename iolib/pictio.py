# -*- coding: utf-8 -*-
'''
special input/output

NOTE: 2017-05-08 16:15:04
BYE-BYE bioformats!

NOTE: 2020-02-17 09:52:12
Add signature annotations to file loaders to help file data handling

'''
#### BEGIN core python modules
from __future__ import print_function

import inspect, keyword, os, sys, traceback, typing, warnings, io, importlib
# import  threading
import pickle, pickletools, copyreg, csv, numbers, mimetypes
import concurrent.futures
import collections
#from functools import singledispatch
#from contextlib import (contextmanager,
                        #ContextDecorator,)
#### END core python modules

#### BEGIN 3rd party modules
import scipy
import scipy.io as sio
import quantities as pq
import numpy as np
import pandas as pd
#import xarray as xa
import h5py
import vigra
import neo
import confuse # for programmatic read/write of non-gui settings
from PyQt5 import QtCore, QtGui, QtWidgets
#### END 3rd party modules

#### BEGIN pict.core modules
#from core import neo
#from core import patchneo
from core import (xmlutils, strutils, datatypes, datasignal,
                  triggerprotocols, neoutils,)


from core.prog import (ContextExecutor, safeWrapper, check_neo_patch, 
                       identify_neo_patch,  import_relocated_module)

from core.workspacefunctions import (user_workspace, assignin, debug_scipyen,
                                     get_symbol_in_namespace,)

from imaging import (axisutils, axiscalibration, scandata, )

from imaging.axisutils import *

#import datatypes
#### END pict.core modules

#import signalviewer as sv
#import javabridge
#import bioformats


# NOTE: 2019-04-21 18:14:23 using pyxdg introduced in pict
# CAUTION this is pyxdg; do not confuse with xdg
# this is usually supplied by your Linux distro
# in case it is not, call pip3 install --user pyxdg
try:
    import xdg # CAUTION this is from pyxdg
    from xdg import Mime as xdgmime
    
except Exception as e:
    warnings.warn("Python module 'pyxdg' not found; xdg mime info utilities not available")
    xdg = None
    xdgmime = None

# NOTE: 2019-04-21 18:34:08 
# somewhat redundant but I found that the Mime module in pyxdg distributed with
# openSUSE does not do is_plain_text(), or get_type2()
# so also use the binding to libmagic here
# ATTENTION: for Windows you need DLLs for libmagic installed separately
# for 64 bit python, install libmagicwin64
# ATTENTION: on Mac OSX you also needs to install libmagic (homebrew) or file (macports)
try:
    import magic as libmagic # file identification using libmagic
    
except Exception as e:
    warnings.warn("Python module 'magic' not found; advanced file type identification will be limited")
    libmagic = None




# NOTE: 2016-04-01 10:58:32
# let's have this done once and for all
__vigra_formats__ = vigra.impex.listExtensions()
__ephys_formats__ = ["abf"]
__generic_formats__ = ["pkl", "h5", "csv"]
__tabular_formats__ = ["xls", "xlsx", "xlsm", "xlsb", "odf", "ods", "odt", "csv", "tsv" ]

#SUPPORTED_IMAGE_TYPES = __vigra_formats__.split() + [i for i in bioformats.READABLE_FORMATS if i not in __vigra_formats__]
SUPPORTED_IMAGE_TYPES = __vigra_formats__.split() # + [i for i in bioformats.READABLE_FORMATS if i not in __vigra_formats__]
#del(i)
SUPPORTED_IMAGE_TYPES.sort()

SUPPORTED_EPHYS_FILES = __ephys_formats__
SUPPORTED_EPHYS_FILES.sort()

SUPPORTED_GENERIC_FILES = __generic_formats__
SUPPORTED_GENERIC_FILES.sort()

# NOTE: 2017-06-29 14:36:20
# move file handling from ScipyenWindow here

# NOTE: 2019-04-21 17:50:38
# add user's mime.types defined by 3rd party software -- these are typically 
# stored in ~/.mime.types

mimetypes_knownfiles = mimetypes.knownfiles

user_mime_types_file = os.path.join(os.path.expanduser("~"), ".mime.types")

if os.path.isfile(user_mime_types_file):
    mimetypes_knownfiles.append(user_mime_types_file)


mimetypes.init(mimetypes_knownfiles)

for ext in SUPPORTED_IMAGE_TYPES:
    if mimetypes.guess_type("_."+ext)[0] is None:
        mimetypes.add_type("image/"+ext, "."+ext)
        
# NOTE: 2019-04-21 18:16:01
# manual, old & cumbersome way
# NOTE: 2019-04-23 10:09:36
# using pyxdg distributed with the OS (provides xdg.Mime)
# keeping manual mime-type registratin as a fallback
mimetypes.add_type("application/axon-binary-file", ".abf")
mimetypes.add_type("application/axon-text-file", ".atf")
mimetypes.add_type("application/x-hdf", ".h5")
mimetypes.add_type("application/x-pickle", ".pkl")
mimetypes.add_type("application/x-matlab", ".mat")
mimetypes.add_type("application/x-octave", ".oct")
mimetypes.add_type("text/plain", ".cfg") # adds to already known extensions

class CustomUnpickler(pickle.Unpickler):
    """ Custom unpickler
        NOTE: 2020-10-30 16:30:16
        This is supposed to deal with pickled data expects classes or functions
        to be defined in modules as advertised inside the pickle data stream, but
        this no longerhappens at the time of unpickling.
        
        It is possible that between the time of pickling and this unpickling, the
        definitions of some classes and functions have been moved to a "new" module.
        
        It is also possible that the original module was moved (e.g. in a different
        package or it is a submodule of another module).
        
        The following contingencies are possible:
        
        a) the definitions of the classes or functions have been moved to a 
        "new" module, but both the "old" (original) and the "new" module have been
        successfully imported (hence, they are present in sys.modules)
        
        b) the definitions of the classes and/or functions have been moved to a
        "new" module, and only the "new" module is loaded (the "old" module has
        been removed from the API, since pickling)
        
        c) definitions have been moved to a new module that hasn't been loaded
        (imported) yet
        
        
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def load(self):
        return super().load()
    
    def _find_module_for_symbol_(self, symbol, old_modname=None):
        """Deals with contingencies (a) and (b):
            "old" (original) module and the "new" module have been succesfully
            imported and are present in sys.modules
            
        More importantly, the "new" module MUST have been imported, hence it is
        one of sys.modules keys.
        
        Returns the module that currently contains the symbol in symbol
            
        """
        
        def __test_containment__(item_names, modname, obj ):
            direct = modname in item_names
            
            is_attribute = any([hasattr(obj, i) for i in item_names])
            
            is_scipyen = False
            
            if inspect.ismodule(obj):
                if hasattr(obj, "__path__"): # obj is a package - maybe a namespace package
                    if hasattr(obj, "__file__"):
                        pth = obj.__file__
                        
                    else:
                        pth = obj.__path__
                        
                        if isinstance(pth, list):
                            if len(pth):
                                pth = pth[0]
                            else:
                                pth = ""
                                
                        elif type(pth).__name__ == "_NamespacePath":
                            pth = obj.__path__._path[0]
                        
                else:
                    pth = getattr(obj, "__file__", "") # bulltin modules have no __file__ atribute
            
            else:
                m = inspect.getmodule(obj)
                
                pth = getattr(m, "__file__", "")
                
            is_scipyen = "scipyen" in pth
            
            return (direct or is_attribute) and is_scipyen
            
        inames = symbol.split(".") # to cover the case of nested classes
        
        if debug_scipyen():
            print("\n\tCustomUnpickler._find_module_for_symbol_(%s, %s): itemnames = %s" % (symbol, old_modname, inames))
        
        #NOTE: 2020-11-12 11:30:25
        # restrict the e=search for symbols & moduels in the scipyen tree, else
        # we end up with classes imported from system packages when their name 
        # is identical to that of classes found in system packages
        #
        # so let's try to import old_modname first:
        
        loaded_containing_modules = [k for k,v in sys.modules.items() if __test_containment__(inames, k, v)]
        
        imported_modules = dict()
        imported_classes = dict()
        imported_functions = dict()
        
        result = None
        
        if len(loaded_containing_modules):
            for m in loaded_containing_modules:
                mm = sys.modules[m]
                
                mdls = dict(inspect.getmembers(mm, inspect.ismodule))
                clss = dict(inspect.getmembers(mm, inspect.isclass))
                fncs = dict(inspect.getmembers(mm, inspect.isfunction or inspect.isgeneratorfunction or inspect.iscoroutinefunction))
                
                if inames[-1] in mdls:
                    if inames[-1] in imported_modules:
                        imported_modules[inames[-1]].append(mdls[inames[-1]])
                        
                    else:
                        imported_modules[inames[-1]] = [mdls[inames[-1]]]
                        
                elif inames[-1] in clss:
                    if inames[-1] in imported_classes:
                        imported_classes[inames[-1]].append(clss[inames[-1]])
                        
                    else:
                        imported_classes[inames[-1]] = [clss[inames[-1]]]
                        
                elif inames[-1] in fncs:
                    if inames[-1] in imported_functions:
                        imported_functions[inames[-1]].append(fncs[inames[-1]])
                        
                    else:
                        imported_functions[inames[-1]] = [fncs[inames[-1]]]
                        
            if inames[-1] in imported_modules:
                mods = imported_modules[inames[-1]]
                result = mods[0]
            
            elif inames[-1] in imported_classes:
                objs = imported_classes[inames[-1]]
                
                result = getattr(inspect.getmodule(objs[0]), inames[-1])
                    
            elif inames[-1] in imported_functions:
                objs = imported_functions[inames[-1]]
                result = getattr(inspect.getmodule(objs[0]), inames[-1])
                
            else:
                for k, v in enumerate(inames[:-1]):
                    obj = self._find_member_for_symbol_(v, inames[k+1])
                    if obj is not None:
                        result = obj
                    
            if debug_scipyen():
                print("\t\timported_modules", imported_modules)
                print("\t\timported_classes",imported_classes)
                print("\t\timported_functions",imported_functions)
            
        if debug_scipyen():
            result_module = None
            if result is not None:
                result_module = inspect.getmodule(result)
                
                if result_module is not None:
                    print("\t\t***FOUND***:", result,
                        "in module:", result_module)
                else:
                    print("\t\t***FOUND***:", result)
                    
            else:
                print("\t\t### NOT FOUND ###")
                
        #print("resukt:", result)
            
        return result
    
    def _find_member_for_symbol_(self, name, symbol):
        if debug_scipyen():
            print("\nCustomUnpickler._find_member_for_symbol_(%s, %s)\n" % (name, symbol))
            
        #possible_patch = identify_neo_patch(name)
        #if isinstance(possible_patch, tuple) and len(possible_patch) == 2:
            #if debug_scipyen():
                #print("Possible_patch for:", name, "=", possible_patch)
            #with mock.patch(possible_patch[0], new = possible_patch[1]):
                #parent = self._find_module_for_symbol_(name)
                #if parent is not None:
                    #if hasattr(parent, symbol):
                        #return getattr(parent, symbol)
                
        #else:
            #parent = self._find_module_for_symbol_(name)
            #if parent is not None:
                #if hasattr(parent, symbol):
                    #return getattr(parent, symbol)
        
        parent = self._find_module_for_symbol_(name)
        if parent is not None:
            if hasattr(parent, symbol):
                return getattr(parent, symbol)
    
    
    def find_class(self, modname, symbol):
        # FIXME 2020-12-23 15:12:15
        # finding relocated classes can be confused by classes with same name but
        # defined in different packages - best example is for pictgui.Cursor being
        # confused with matplotlib.widgets.Cursor (hence the latter is returned
        # in lieu of the former) - see also NOTE: 2020-12-23 15:11:49 in pictgui.py
        from unittest import mock
        #print("\n***CustomUnpickler.find_class(%s, %s)***\n" % (modname, symbol))
        if debug_scipyen():
            print("\n***CustomUnpickler.find_class(%s, %s)***\n" % (modname, symbol))
        
        try:
            # NOTE: 2020-10-30 14:54:16
            # see if the 'symbol' symbol is found where expected
            #
            # NOTE: this requires that modname exists and is present is
            # sys.modules i.e. it has successfully been imported;
            #
            
            #  NOTE: forget about these modules: patch the original ones
            if "neoevent" in modname:
                modname = "neo.core.event"
                
            elif "neoepoch" in modname:
                modname = "neo.core.epoch"
                
            possible_patch = identify_neo_patch(symbol)
            
            if isinstance(possible_patch, tuple) and len(possible_patch)==2:
                with mock.patch(possible_patch[0], new = possible_patch[1]):
                    return super().find_class(modname, symbol)
                
            else:
                return super().find_class(modname, symbol)
        
        except Exception as e:
            #print(type(e))
            if debug_scipyen():
                print(type(e))
            if isinstance(e, (AttributeError, ModuleNotFoundError)):
                
                #  NOTE: forget about these modules: patch the original ones
                if "neoevent" in modname:
                    modname = "neo.core.event"
                    
                elif "neoepoch" in modname:
                    modname = "neo.core.epoch"
                    
                possible_patch = identify_neo_patch(symbol)
                
                if isinstance(possible_patch, tuple) and len(possible_patch)==2:
                    with mock.patch(possible_patch[0], new = possible_patch[1]):
                        return self._find_module_for_symbol_(symbol, old_modname=modname)
                    
                else:
                    return self._find_module_for_symbol_(symbol, old_modname=modname)
                
            else:
                try:
                    #print("\tCustomUnpickler.find_class(): old module", modname, "for symbol", symbol, "is NOT in sys.modules")
                    
                    # NOTE: 2020-11-12 11:19:23
                    # this fails silently, but when successful, the call below should
                    # work
                    import_relocated_module(modname)
                    result = super().find_class(modname, symbol)
                    if modname in sys.modules:
                        sys.modules.pop(modname, None)
                        
                    return result
                
                except Exception as e1:
                    traceback.print_exc()
                    exc_info = sys.exc_info()
                    #print("\t### CustomUnpickler.find_class(...) Exception: ###")
                    #print("\t### exc_info: ###", exc_info)
                    raise
        
def __ndArray2csv__(data, writer):
    for l in data:
        writer.writerow(l)
        
    
# NOTE: 2017-09-21 16:34:21
# BioFormats dumped mid 2017 because there are nor good python ports to it
# (it uses javabridge which is suboptimal)
def loadImageFile(fileName:str, asVolume:bool=False, axisspec:[collections.OrderedDict, None]=None) -> ([vigra.VigraArray, np.ndarray],):
    ''' Reads pixel data from an image file
    Uses the vigra impex library.
    
    
    asVolume: boolean, optional (default is False):
        
        When True, this function will call vigra.readVolume which, when the 
            fileName looks like the first in a series of files with multi-frame
            data (e.g., a "volume"), it will read the entire volume.
        
        The default option (False) bypasses this and only loads the file specified 
        by the "fileName" argument. If this is not what is wanted, then pass
        "asVolume = True" in the call.
        
    
    axisspec: a collections.OrderedDict with valid keys (x, y, z, c, t) and integer values,
                with the constraint that the product of the values MUST equal the
                numbr of pixels in the data
    
    TODO: come up with  smart way of "guessing" which of the xyzct dimensions are actually used in the TIFF
            this could be very hard, because TIFF specification does not mandate this, 
            and therefore TIFF writers do no necessarily include this information either.
            
    axisspec = collections.OrderedDict with the following constraints:
            1) must contain maximum five elements
            2) acceptable keys: 'x', 'y', 'z', 'c', and 't'
            3) values are 'k', '~', or integers: when 'k', they will be replaced by the values 
             read from the file; when '~', they are calculated from the total numbers of samples
            4) the _order_ of the keys as specified in the axisspec will take
             precedence over what is read from the file
             
             This may result in a reshape() called on the returned data.
             
             Raises an error if the new shape is not compatible with the number of samples in the data.
             
    NOTE: Things to be aware of:
    
    If fileName is the first in what looks like an image series, asVolume=True 
    WILL result in the vigra impex library loading up the entire series, as a "volume".
    
    While this is very convenient, one has to be aware of that when loading files
    form within a scan object (e.g. a PVScan object) and stop after the first cycle.
    
    '''    
    #else:
    
    # NOTE: 2018-02-20 12:56:02
    # coerce reading a volume as a volume!
    nFrames = vigra.impex.numberImages(fileName)
    
    if nFrames > 1:
        asVolume = True
    
    if asVolume:
        ret = vigra.readVolume(fileName)
        
    else:
        ret = vigra.readImage(fileName)
        
    #mdata = readImageMetadata(fileName)
    
    if axisspec is not None:# TODO FIXME we're not using this kind of axisspec anymore, are we?
        if type(axisspec) is collections.OrderedDict:
            parsedAxisspec = collections.OrderedDict(zip(ret.axistags.keys(), ret.shape))
            
            axisspec = verifyAxisSpecs(axisspec, parsedAxisspec)
            
            # by now, all tags given in axisspec should have values different than None
            #print("axisspec: ", axisspec)
            
            ret.shape = axisspec.values()
            ret.axistags = vigra.VigraArray.defaultAxistags(tagKeysAsString(axisspec))
                    
        else:
            raise ValueError('axisspec must be a collections.OrderedDict, or None')
        
    #return (ret, mdata)
    return ret
        
# TODO: diverge onto HDF5, and bioformats handling
def saveImageFile(data, fileName:str, separateChannels:bool=True) -> None:
    """
    Writes a vigra array to one of the image file formats supported by Vigra
    library
    
    Positional parameters:
    ======================
    data: VigraArray
    fileName: string 
    
    Keyword parameters:
    ===================
    separateChannels: bool (default True); if more than one channels, will try to 
        write each channel to a separate file suffixed with "_channel_X"
        
        When FALSE, will try to save data as a VectorXVolume (or VectorXImage). 
        This depends on whether, after "stripping" the channel axis, the data
        has 3D or 2D.
        
    TODO: diverge for HDF5, netcdf, 
    TODO: support for higher dimensions (up to 5, the upper limit in Vigra)
    by writing to a sequence of files each containing a 3D array
    TODO: support for 4 channels (e.g. RGBA, or ARGB?)
    """
    #print("ndim:", data.ndim, "nchannels: ", data.channels, "shape:", data.shape)
    
    if data.ndim == 2: # trivial
        vigra.impex.writeImage(data, fileName, "")
        
    elif data.ndim == 3: # less trivial
        if data.channels == 1:
            # NOTE: 2019-01-21 12:01:21
            # even arrays without channel axis report one channel, so dropping
            # the channel axis is NOT guaranteed to result in a lower dimensionality
            
            if data.dropChannelAxis().ndim == 2:
                # dropping channel axis does indeed decrease dimensionality
                vigra.impex.writeImage(data.dropChannelAxis(), fileName, "")
                
            else:
                vigra.impex.writeVolume(data.dropChannelAxis(), fileName, "")
            
        else:
            # NOTE: 2019-01-21 14:13:02 multi-band data; 
            # vigra impex library only supports single or 3-band data for TIFFs
            # so we can write multi-band TIFFs only when there are three channels
            
            # NOTE: 2019-01-21 14:20:01
            # packed multi-pand pixel data (i.e. VectorX...) is not supported
            # by vigra.impex unless there are three bands (channels)
            
            if data.channels == 3 and not separateChannels:
                vigra.impex.writeImage(vigra.RGBImage(data), fileName, "")
                    
            else:
                bname, ext = os.path.splitext(fileName)
                
                for c in range(data.channels):
                    out = data.bindAxis("c", c) # 2D array
                    vigra.impex.writeImage(out, "%s_channel_%d%s" % (bname, c, ext), "")
                    
    elif data.ndim == 4: # not trivial
        if data.channels == 1:
            # NOTE: 2019-01-21 12:02:29
            # see NOTE: 2019-01-21 12:01:21
            if data.dropChannelAxis().ndim == 3:
                # convert to a 3D array by dropping its channel axis then write as volume
                vigra.impex.writeVolume(data.dropChannelAxis(), fileName, '')
                
            else:
                # NOTE: 2019-01-21 12:10:28
                # Here obviously data has a virtual channel axis so dropping it 
                # does NOT reduce the array dimensionality;
                #
                # We "slice" data on the outermost axis then write individual 
                # "slices" as separate volumes (each slice will have 1-less dimensions)
                # suffixed with "_x_k" where "x" stands for the key of the outermost 
                # axistag and "k" is the kth coordinate on axis "x"
                bname, ext = os.path.splitext(fileName)
                
                for k in range(data.shape[-1]):
                    vigra.impex.writeVolume(data.bindAxis(data.axistags[-1], k), "%s_%s_%d%s" % (bname, data.axistags[-1].key, k, ext), "")
        
        else: 
            # NOTE: 2019-01-21 14:21:50
            # there is more than one channel (band),
            # and the array definitely has a channel axis
            # as per NOTE: 2019-01-21 14:20:01 we can only write an RGB volume
            # if data has three bands; otherwise we revert to separate channels
            
            if data.channels == 3 and not separateChannels:
                # pack data in an RGB volume
                vigra.impex.writeVolume(vigra.RGBVolume(data), fileName, "")
                
            else:
                # force separate channels -- iterate (bind) over the
                # channel axis => 3D single-band volumes
                    
                bname, ext = os.path.splitext(fileName)
                
                for c in range(data.channels):
                    out = data.bindAxis("c", c) # 3D volume, single-band
                    vigra.impex.writeVolume(out, "%s_channel_%d%s" % (bname, c, ext), "")
        
    elif data.ndim == 5:
        if data.channels == 1:
            if data.dropChannelAxis().ndim == 4: 
                # NOTE: 2019-01-21 12:16:49
                # data has a real channel axis; dropping it reduces dimensionality to 4
                # behave as for a 4D data without channel axis, see NOTE: 2019-01-21 12:10:28
                
                bname, ext = os.path.splitext(fileName)
                
                for k in range(data.dropChannelAxis().shape[-1]):
                    vigra.impex.writeVolume(data.dropChannelAxis().bindAxis(data.dropChannelAxis().axistags[-1], k), "%s_%s_%d%s" % (bname, data.dropChannelAxis().axistags[-1].key, k, ext), "")
        
                
            else:
                # NOTE: 2019-01-21 12:19:25
                # data has a virtual channel axis so dropping it does not reduce
                # its dimensionality
                # we iterate along the two outermost axes and generate 3D slices 
                # that we then write as individual volumes
                bname, ext = os.path.splitext(fileName)
                for k0 in range(data.shape[-1]):
                    for k1 in range(data.shape[-2]):
                        vigra.impex.writeVolume(data.bindAxis(data.axistags[-1],k0).bindAxis(data.axistags[-2],k1), "%s_%s_%d_%s_%d%s" % (bname, data.axistags[-1].key, k0, data.axistags[-2].key, k1, ext), "")
                        
        else: 
            # NOTE: 2019-01-21 13:19:22
            # there definitely is a channel axis; channel (band) data is 4D, so 
            # we pack pixel data in a multi-band format then iterate on the
            # outermost non-channel axis axis to generate multi-banded 3D sub-volumes
            
            # ATTENTION: vigra impex only supports TIFFs with a single or three bands
            bname, ext = os.path.splitext(fileName)
            
            if data.channelIndex == data.ndim-1:
                outerSliceAxis = data.axistags[data.channelIndex-1]
                innerSliceAxis = data.axistags[data.channelIndex-2]
                
            elif data.channelIndex == data.ndim-2:
                outerSliceAxis = data.axistags[-1]
                innerSliceAxis = data.axistags[data.channelIndex-1]
                
            else:
                outerSliceAxis = data.axistags[-1]
                innerSliceAxis = data.axistags[-2]
                
            if data.channels == 3 and not separateChannels:
                for k_out in range(data.shape[data.axistags.index(outerSliceAxis.key)]):
                    out = vigra.RGBVolume(data.bindAxis(outerSliceAxis.key, k_out)) # 4D but multi band with packed pixels
                    vigra.impex.writeVolume(out, "%s_%s_%d%s" % (bname, outerSliceAxis.key, k_out, ext), "")
                    
            else:
                for c in data.channels: # binds each channel to a 4D data single-band
                    for k_out in range(data.shape[data.axistags.index(outerSliceAxis.key)]):
                        out = data.bindAxis("c", c).bindAxis(outerSliceAxis.key, k_out)
                        vigra.impex.writeVolume(out, "%s_channel_%d_%s_%d%s" % (bname, c, outerSliceAxis.key, k_out, ext), "")
            
    else:
        raise TypeError("VigraArrays with %d dimensions are not supported" % data.ndim)
    
def loadOctave(fileName):
    raise RuntimeError("Loading of Octave binary files is not yet supported; please convert them to matlab files first")
    
def loadMatlab(fileName:str, **kwargs) -> dict:
    """Simple wrapper around scipy.io.loadmat.
    
    Parameters:
    ----------
    
    fileName: str; name of the file (or fully qualified path name)
    
    Returns:
    -------
    mat_dict: dict or None; 
        the output from scipy.io.loadmat (see scipy.io.loadmat for details)
        The keys in mat_dict represent the name of the variables in the mat file.
    """
    if not os.path.isfile(fileName):
        raise OSError("File %s not found" % fileName)
        
    try:
        return sio.loadmat(fileName) # a dict
        
    except Exception as e:
        traceback.print_exc()
        
    
def loadCFSmatlab(fileName:str) -> neo.Block:
    """Load CFS data exported from Signal5 as matlab
    CAUTION: under development
    Returns an analog signal (?)
    """
    
    # loadmat returns a python dict containing the variables saved in the matlab 
    # file; this dict maps keys (variable names as stored in the file) to values 
    # (the variables themselves, in the form of numpy record arrays)
    # all keys in this dict are strings
    
    matlab_dict = sio.loadmat(fileName)
    
    # this could be any matlab file; check if it's what's expected
    
    if len(matlab_dict) == 0:
        return
    
    # typical keys are: "__header__", "__globals__", "__version__"
    cfs2mat_keys = ["__globals__", "__header__", "__version__"]
    
    # the actual signals are contained in "wave_data"
    
    # in addition, RECORDED data contains additional channels such as keyboard markers
    # and digital channel (NOT to be confused with the digital TTL outputs)
    # the presence and names of these channels vary according to the setup and to
    # the particular configuration file under which the data has been recorded
    
    # Depending on what was selected on the Matlab export dialogue in Signal,
    # or what values have been passed to the FileExportAs function in a Signal
    # script):
    #
    # 1) the variables containing the extra channel may be given their actual
    # names (e.g. "Keyboard", "Digital") instead of generic names (e.g. "Ch2", "Ch3")
    #
    # 2) In addition, the names of the matlab variables containing the "wave" data and
    # the extra channels may be prefixed with the source name (name of the CFS 
    # file to which the data was written)
    #
    
    # so, "__globals__", "__header__", "__version__" must always be present
    # check for their presence
    
    if not all([k in matlab_dict for k in cfs2mat_keys]):
        raise RuntimeError("The mat file %s does not appear to contain Signal data" % fileName)
    
    # the fields are numpy arrays of objects!
    
    # if this is from a cfs file that has been exported to a matlab file then it
    # should have a key containing/ending in "wave_data"
    
    # there should be at most one
    wave_data_keys = [k for k in matlab_dict if k.endswith("wave_data")]
    
    is_cfs = False
    wave_data = None
    xy_data = None
    mandatory_wave_records = ('xlabel', 'xunits', 'start', 'interval', 'points', 'chans', 'frames', 'chaninfo', 'frameinfo', 'values')
    
    if len(wave_data_keys) == 1:
        wave_data = matlab_dict[wave_data_keys[0]]
        is_cfs = True
        
    elif len(wave_data_keys) > 1:
        raise RuntimeError("Too many wave data keys in matlab file %s" % fileName)
    
    if wave_data is not None:
        # this should be the tuple ('xlabel', 'xunits', 'start', 'interval', 'points', 'chans', 'frames', 'chaninfo', 'frameinfo', 'values')
        record_names = wave_data.dtype.names
        
        if record_names is None:
            raise RuntimeError("Expecting a record array in wave data")
        
        if isinstance(record_names, tuple) and len(record_names) == 0:
            raise RuntimeError("Wave data record array names is an empty tuple")
        
        missing_wave_records = [r for r in mandatory_wave_records if r not in record_names]
        
        if len(missing_wave_records):
            raise RuntimeError("Missing wave data records %s" % (str(missing_wave_records)))
        
        try:
            xlabel = str(wave_data["xlabel"][0][0][0])
            
        except:
            xlabel = ""
        
        xunits = eval("pq.%s" % (str(wave_data["xunits"][0][0][0])))
        
        x_start = float(wave_data["start"]) * xunits

        sampling_period = float(wave_data["interval"]) * xunits
        
        n_samples = int(wave_data["points"])  # ditto
        
        n_channels = int(wave_data["chans"])  # also works instead of int(wave_data["chans"][0][0])
        
        n_segments = int(wave_data["frames"]) # as for chans
        
        channel_info = wave_data["chaninfo"][0][0] # record array with fields: ('number', 'title', 'units')
        
        frame_info = wave_data["frameinfo"][0][0] # record array with fields: ('number', 'points', 'start', 'state', 'tag', 'sweeps', 'label')
        
        signals = np.array(wave_data["values"][0][0], copy=False) # get a reference to the data array
        
        assert signals.size > 0, "Empty signal data in file %s" % fileName
        
        assert signals.shape[0] == n_samples,  "Signals axis 0 size %d is incompatible with the advertised number of samples %d"  % (signals.shape[0], n_samples)
        
        if signals.ndim >= 2:
            assert signals.shape[1] == n_channels, "Signals axis 1 size %d is incompatible with the advertised number of channels %d" % (signals.shape[1], n_channels)
            
        if signals.ndim >= 3:
            assert signals.shape[2] == n_segments, "Signals axis 2 size %d is incompatible with the advertised number of segments %d" % (signals.shape[2], n_segments)
        
        
        ret = neo.Block(file_origin = fileName, name=fileName, description="From CED Signal exported as matlab", software="CEDSignal") # CEDSignal goes into annotations
        
        for k_seg in range(n_segments):
            assert int(frame_info["points"]) == n_samples, "Segment %d has a different number of points than advertised in wave data %d" % (int(frame_info["points"]), n_samples)
            
            seg = neo.Segment(index = int(frame_info["number"][k_seg]), name = str(frame_info["label"][k_seg][0][0]), file_origin = fileName,
                              state = int(frame_info["state"][k_seg]), tag = int(frame_info["tag"][k_seg]), sweep = int(frame_info["sweeps"][k_seg]),
                              start = float(frame_info["start"][k_seg]))
            
            for k_channel in range(n_channels):
                sig_units = eval("pq.%s" % str(channel_info["units"][k_channel][0][0]))
                
                if signals.ndim == 2:
                    sig = neo.AnalogSignal(signals[:,k_channel], units = sig_units, t_start = x_start, sampling_period = sampling_period,
                                        name = str(channel_info["title"][k_channel][0][0]), file_origin = fileName, channel=int(channel_info["number"][k_channel]))
                else:
                    sig = neo.AnalogSignal(signals[:,k_channel,k_seg], units = sig_units, t_start = x_start, sampling_period = sampling_period,
                                        name = str(channel_info["title"][k_channel][0][0]), file_origin = fileName, channel=int(channel_info["number"][k_channel]))
                    
                seg.analogsignals.append(sig)
                
            ret.segments.append(seg)
            
            
        return ret
    
    
    else: # likely an sxy file exported to matlab; it may contain several signals, NOT necessarily in the time domain
        # these are record arrays with the following fields:
        # ('title', 'yunits', 'xunits', 'points', 'xvalues', 'yvalues')

        xy_signals_name_values = [(key, value) for key, value in matlab_dict.items() if key not in cfs2mat_keys]
        
        if len(xy_signals_name_values) == 0:
            raise RuntimeError("The file %s does not appear to contain any XY data" % fileName)
            
        ret = neo.Block(file_origin = fileName, name=fileName, description="From CED Signal exported as matlab", software="CEDSignal") # CEDSignal goes into annotations
        
        #
        # NOTE: this is always a SINGLE FRAME as it is produced by an XY plot in CED Signal
        #
        
        seg = neo.Segment(file_origin = fileName)
        
        for xy_signal in xy_signals_name_values:
            sig_points = int(xy_signal[1]["points"])
            assert xy_signal["xvalues"][0][0].size == sig_points
            assert xy_signal["yvalues"][0][0].size == sig_points
            sig = neo.IrregularlySampledSignal(xy_signal["xvalues"][0][0], xy_signal["yvalues"][0][0],
                                               units = sig_units, time_units = domain_units, 
                                               name = str(xy_signal["title"][0][0][0]), 
                                               file_origin = fileName,
                                               description = xy_signal[0])
            
            seg.segments.append(sig)
            
        ret.segments.append(seg)
        
        
        return ret
        
def loadAxonTextFile(fileName:str) -> neo.Block:
    """Reads the contents of an axon text file.
    
    Returns:
    -------
    result: neo.Block
    
    NOTE: 2020-02-17 18:14:51
    The header structure is now embedded in the "annotations" attribute of the
    return variable
    
    NOTE: 2020-02-17 09:35:28
    Also returns the metadata (it used to be optional)
    
    """
    if not os.path.isfile(fileName):
        raise OSError("File %s not found" % fileName)
    
    skip_header = 2 # two mandatory header lines in ATF files EXCLUDING column names
    n_data_columns = 0
    
    records = list()
    
    data_names = None
    data_units = list()
    
    field_names_translations = str.maketrans(dict([(c, "_") for c in ("\t", "\n")]))
    
    # quick header inspection to see is this is a conformant ATF file
    with open(fileName, mode="rt") as file_object:
        header = file_object.readline()
        skip_header += 1
        # NOTE: 2019-04-22 17:03:10
        # "ATF" in the header is not really reinforced (Clampfit can read ascii 
        # files saved as ATF)
        if "ATF" in header:
            header2 = file_object.readline()
            a,b = header2.split()
            
            skip_header += int(a)
            n_data_columns = int(b)
            
            
            for k in range(int(a)):
                records.append(file_object.readline())
                
            
            # NOTE: 2019-04-22 16:48:36
            # this is preferred albeit more convoluted, because column names 
            # may contain spaces and thus np.genfromtxt will interpret the headings
            # to expect more data columns than there actually are 
            #
            # column names may contain white spaces (e.g. "Time (ms)")
            # which complicates things; furthermore they are, in principle
            # tab-separated (which again is not guaranteed); finally 
            # the last column name is followed by a "\n" (on Unix, at least)
            #
            # we replace these with "_" to facilitate splitting into
            # tokens which otherwise may contain spaces or other punctuation
            # characters
            
            # NOTE: 2019-04-22 16:49:09
            # below we ensure data_names and data_units are never empty
            try:
                column_names = file_object.readline().translate(field_names_translations).split("_")
                
                # a nested list of the form as in this example:
                # [['Time', 'ms'], ['Template', 'mV']]
                d_names = [[n.strip('"()') for n in name.split()] for name in column_names if len(name.strip())]
                data_names = [n[0] for n in d_names] # the actual data column names
                
                data_units_str = list()
                
                for col_name in d_names:
                    if len(col_name) > 1:
                        data_units_str.append(col_name[1])
                    
                    else:
                        data_units_str.append("dimensionless")
                        
                if len(data_units_str) == len(data_names):
                    for s in data_units_str:
                        try:
                            data_units.append(pq.Quantity([1], units=s))
                            
                        except Exception as e:
                            warnings.warn("Cannot parse data units from %s; setting units to dimensionless" % s)
                            data_units.append(pq.Quantity([1], units = pq.dimensionless))
                        
            except Exception as e:
                data_names = ["Column_%d" % k for k in n_data_columns]
                data_units = [pq.Quantity([1], units=pq.dimensionless) for k in n_data_columns]
                
            skip_header += 1

        # NOTE: 2019-04-22 17:13:09
        # allow plain ascii files "masquerading" as ATF files
            
    #print("data_units", data_units)
        
    # NOTE: 2019-04-22 16:55:12
    # this is a structured numpy array (ndim = 1) as data_names is never 
    # empty (see NOTE: 2019-04-22 16:49:09)
    try:
        data = np.genfromtxt(fileName, skip_header=skip_header, names=data_names)
        
    except Exception as e:
        traceback.print_exc()
        return
    
    if data.dtype.fields is not None: # structured array
        if len(data.dtype.fields) != n_data_columns:
            raise RuntimeError("Data has different columns (%d) than indicated by the file (%d)" % (len(data.dtype.fields), n_data_columns))
        
        data_col_names = [n for n in data.dtype.fields]

        if "Time" in data.dtype.fields:
            time_vector = data["Time"]
            
            # NOTE: 2019-04-22 16:53:14
            # although time_vector = data["Time"] is more direct, the ATF file 
            # may "mangle" the data column names with units e.g. "Time (ms)" 
            # therefore messing up np.genfromtxt interpretation, 
            # see NOTE: 2019-04-22 16:48:36
            
            # A more flexible approach albeit convoluted, allowing us to collect
            # the "other" (non-time) data columns separately.
            time_column_index = data_col_names.index("Time")
            
            channel_names = [name for name in data_col_names if name != "Time"]
            
            if len(data_units):
                time_units = data_units[time_column_index]
                channel_units = [unit for k, unit in enumerate(data_units) if k != time_column_index]
                
            else: # assume time is in "s"
                time_units = pq.s
                channel_units = [pq.dimensionless for c in channel_names]
                
            
            chndx = neo.ChannelIndex(index=np.arange(len(channel_names)),
                                        channel_ids = range(len(channel_names)),
                                        channel_names = channel_names,
                                        name = "Channels")

            # try to guess if this is a regularly sampled signal
            dtime = np.ediff1d(time_vector)
            
            analog = np.all(np.isclose(dtime, dtime[0], rtol=1e-5, atol=1e-5))
            
            if analog:
                # seems like a regularly sampled signal
                sampling_period = np.mean(time_vector) * time_units
                
                t_start = time_vector[0] * time_units
                
                signals = [neo.AnalogSignal(data[name], 
                                        units = channel_units[k],
                                        t_start = t_start, 
                                        sampling_period = sampling_period,
                                        name = name) \
                        for k,name in enumerate(channel_names)]
                
            else: # likely an IrregularlySampledSignal
                signals = [neo.IrregularlySampledSignal(time_vector, 
                                                        data[name],
                                                        units = channel_units[k],
                                                        time_units = time_units,
                                                        name = name) \
                        for k, name in enumerate(channel_names)]
                
            for k, sig in enumerate(signals):
                sig.channel_index = chndx[k]
                    
        else: # no "Time" column
            # we assume all data columns are analog signals, sampled at 1 Hz
            # the user must then change this manually later
            time_units = pq.s
            t_start = 0 * time_units
            sampling_period = 1 * pq.s
            
            chndx = neo.ChannelIndex(index = np.arange(len(data_col_names)),
                                        channel_ids = range(len(data_col_names)),
                                        channel_names = data_col_names,
                                        name = "Channels")
            
            if len(data_units):
                signals = [neo.AnalogSignal(data[name],
                                        units = data_units[k],
                                        t_start = t_start,
                                        sampling_period = sampling_period,
                                        name = name) \
                        for name in data_col_names]
                
            else:
                signals = [neo.AnalogSignal(data[name],
                                        units = pq.dimensionless,
                                        t_start = t_start,
                                        sampling_period = sampling_period,
                                        name = name) \
                        for name in data_col_names]
                
            for k, sig in enumerate(signals):
                sig.channel_index = chndx[k]
                
                
    else:
        data_col_names = ["Signal_%d" % k for k in range(data.shape[1])]
        
        time_units = pq.s
        t_start = 0 * time_units
        sampling_period = 1 * pq.s
        
        chndx = neo.ChannelIndex(index = np.arange(len(data_col_names)),
                                    channel_ids = range(len(data_col_names)),
                                    channel_names = data_col_names,
                                    name = "Channels")
        
        if len(data_units):
            signals = [neo.AnalogSignal(data[:,k],
                                        units = data_units[k],
                                        t_start = t_start,
                                        sampling_period = sampling_period,
                                        name = data_col_names[k]) \
                    for k in range(data.shape[1])]
            
        else:
            signals = [neo.AnalogSignal(data[:,k],
                                        units = pq.dimensionless,
                                        t_start = t_start,
                                        sampling_period = sampling_period,
                                        name = data_col_names[k]) \
                    for k in range(data.shape[1])]
            
        for k, sig in enumerate(signals):
            sig.channel_index = chndx[k]
            
            
    segment = neo.Segment()

    analog = True
    
    segment.analogsignals[:] = signals
            
    result = neo.Block(name=os.path.basename(fileName),
                       file_origin = fileName)
    
    result.channel_indexes.append(chndx)
    
    result.segments.append(segment)
    
    result.annotate(header=records)
    
    return result
    #return result, records
    #if with_optional_header:
    
    #return result

def loadAxonFile(fileName:str, create_group_across_segment:typing.Union[bool, dict]=False,
                 signal_group_mode:typing.Optional[str]="split-all") -> neo.Block:
    """Loads a binary Axon file (*.abf).
    
    Parameters:
    -----------
    
    fileName : str; a fully qualified path & file name
    
    create_group_across_segment: bool or dict (optional, default is False)
        Controls grouping like signal types.
        
        Propagated to neo 0.9.0 neo.io.axonio.AxonIO
        
        If True :
        * Create a neo.Group to group AnalogSignal segments
        * Create a neo.Group to group SpikeTrain across segments
        * Create a neo.Group to group Event across segments
        * Create a neo.Group to group Epoch across segments
        
        With a dict the behavior can be controlled more finely
        create_group_across_segment = { 'AnalogSignal': True, 'SpikeTrain': False, ...}

        When False (default): no grouping occurs.
        
        
    signal_group_mode: str (optional, default is "split-all")
        Possible values:
            None - default behaviour according to the IO type
            "split-all" - each channel gives an AnalogSignal
            "group-by-same-units" - all channels sharing same quantity units are
                grouped in a 2D Analogsignal.
            
        Controls grouping of channels in the ABF file into AnalogSignal.
        
        Propagated to neo 0.9.0 neo.io.axonio.AxonIO.
        
        Since version 0.9.0, channels are, by default, grouped in "ChannelView"
        objects. While this is seemingly OK for tetrode recordings, it breaks
        the "one channel per signal" view of "traditional" in vitro or ex vivo 
        recordings such as those obtained with Axon, or CED, software.
        
        The 'signal_group_mode' parameter allows to control this behaviour, with
        its default value of "split-all" being conducive of the traditional
        "one channel per signal" view.
        
        When None, this is supposed to get a default value that depends on the 
        specific IO object; however, this default seems inappropriate for Axon
        files where the "split-all" (allowing for one channel per signal) might
        be expected.
        
        Should the user NOT wish to enforce this "traditional" behaviour, then 
        the signal_group_mode should be given one of the other values, i.e.
            None --> to revert to the current default behaviour
            "group-by-same-units"
    
    Returns:
    ---------
    
    data : neo.Block; its "annotations" attribute is updated to include
        the axon_info "meta data" augumented with t_start and sampling_rate
        
    NOTE: 2020-02-17 09:31:05
    This now handles only axon binary files, and returns the data AND the metadata
    in axon file as well.
    
    NOTE: 2020-02-17 18:07:53
    Reverting back to a single return variable: a neo.Block. The metadata is
    appended to the annotation block of the variable.
    The "protocol_sweeps" are not useful: all signals contain zeros!
    """
    
    if not os.path.isfile(fileName):
        raise OSError("File %s not found" % fileName)
    
    data = neo.Block()
    axon_info = dict()
    #protocol_sweeps = list()
    
    try:
        axonIO = neo.io.AxonIO(filename=fileName)
        
        # NOTE: 2020-12-23 17:33:36
        # adapt to the neo 0.9.0 API
        data = axonIO.read_block(signal_group_mode=signal_group_mode)
        #data = axonIO.read_block()
        
        if isinstance(data, list) and len(data) == 1:
            data = data[0]

        if isinstance(data, (neo.Block, neo.Segment, neo.AnalogSignal, neo.IrregularlySampledSignal)):
            data.annotate(software="Axon")
            
            if data.name is None or (isinstance(data.name, str) and len(data.name.strip()) == 0):
                data.name = os.path.splitext(os.path.basename(fileName))[0]
                
            if isinstance(data, neo.Block):
                for k, s in enumerate(data.segments):
                    if s.name is None or (isinstance(s.name, str) and len(s.name.strip()) == 0):
                        s.name = "segment_%d" % k
        
        #protocol_sweeps = axonIO.read_protocol()
        axon_info = axonIO._axon_info
        axon_info["t_starts"] = axonIO._t_starts
        axon_info["sampling_rate"] = axonIO._sampling_rate
        
        data.annotate(**axon_info)
        
        return data
        #return (data, axon_info, protocol_sweeps)
    
        #if readProtocols:
            ##protocol_sweeps = neo.io.AxonIO(filename=fileName).read_protocol()
        
        #return data
    
    except Exception as e:
        traceback.print_exc()
        
@safeWrapper
def importDataFrame(fileName):
    fileType = getMimeAndFileType(fileName)[0]
    
    if any([s in fileType for s in ("excel", "spreadsheet")]):
        return pd.read_excel(fileName)
        
    elif any([s in fileType for s in ("csv", "tab-separated-values")]):
        # figure out separator: tab or comma?
        # NOTE: 2020-10-01 23:29:35 csv can also be tab-separated !!!
        with open(fileName, "rt") as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.read(2048))
            
        if dialect.delimiter in ("\t", " "): # tab-separated
            return pd.read_table(fileName)
            
        elif dialect.delimiter == ",": # comma-separated
            return pd.read_csv(fileName)
        
        else:
            warnings.warn("Unsupported delimiter: %s" % dialect.delimiter)
            
    else:
        warnings.warn("Unsupported file type: %s" % fileType)
        
def custom_unpickle(src:typing.Union[str, io.BufferedReader]):#, 
                    #exc_info:typing.Optional[typing.Tuple[typing.Any, ...]]=None) -> object:
    if isinstance(src, str):
        if os.path.isfile(src):
            with open(src, mode="rb") as fileSrc:
                return CustomUnpickler(fileSrc).load()
                #return CustomUnpickler(fileSrc, exc_info=exc_info).load()
            
        else:
            raise FileNotFoundError()
            
    elif isinstance(src, io.BufferedReader):
        return CustomUnpickler(src).load()
        #return CustomUnpickler(src, exc_info=exc_info).load()
    
    else:
        raise TypeError("Expecting a str containing an exiting file name or a BufferedReader; got %s instead" % type(src).__name__)
        
    return ret

def loadPickleFile(fileName):
    """Loads pickled data.
    ATTENTION: 
    Doesn't load data from pickle files saved with old (pre-git) Scipyen versions
    where module hierarchies (and paths) have changed.
    
    Will also fail to load pickle files that contain objects of dynamic types
    such as those created in the user workspace - a good example is that of
    namedtuple instances - unless they are defined in a loaded module.
    
    """
    with open(fileName, mode="rb") as fileSrc:
        result = pickle.load(fileSrc)
        
    return result
    
            
def loadPickleFile_old(fileName):
    from unittest import mock
    try:
        # NOTE: try pickle first - in  python3 this is fast (via cPickle)
        with open(fileName, mode="rb") as fileSrc:
            result = pickle.load(fileSrc)
            
    except Exception as e:
        #traceback.print_exc()
        try:
            result = custom_unpickle(fileName)#, exc_info=exc_info)
            #result = custom_unpickle(fileName, exc_info=exc_info)
            
        except:
            exc_info = sys.exc_info()
            
            possible_patch = check_neo_patch(exc_info)
            
            if isinstance(possible_patch, tuple) and len(possible_patch) == 2:
                if debug_scipyen():
                    print("\t### patching in neo ###\n")
                try:
                    with mock.patch(possible_patch[0], new=possible_patch[1]):
                        result = loadPickleFile(fileName)
                        
                except Exception as e1:
                    traceback.print_exc()
                    raise e1
            else:
                raise e
        
    if type(result).__name__ in ("ScanData", "AnalysisUnit", "AxisCalibration", "PlanarGraphics"):
        #print("loaded", type(result))
        result._upgrade_API_()
        
    elif isinstance(result, (neo.Block, neo.Segment, dict)):
        neoutils.upgrade_neo_api(result) # in-place
        
    return result

def savePickleFile(val, fileName, protocol=None):
    #if inspect.isfunction(val): # DO NOT attempt to pickle unbound functions
        #return
    
    if protocol is None:
        protocol = pickle.HIGHEST_PROTOCOL
    
    (name,extn) = os.path.splitext(fileName)
    if len(extn)==0 or extn != ".pkl":
        fileName += ".pkl"
        
    with open(fileName, mode="wb") as fileDest:
        #print("Writing %s" % fileName)
        pickle.dump(val, fileDest, protocol=protocol)
    
def saveNixIOFile(val, fileName):
    (name,extn) = os.path.splitext(fileName)
    if len(extn)==0 or extn != ".h5":
        fileName += ".h5"
        
    nixio = neo.NixIO(fileName=fileName)
    nixio.write(val)
    
    nixio.close()
    
def loadNixIOFile(fileName):
    if os.path.isfile(fileName):
        nixio = neo.NixIO(fileName=fileName)
        ret = nixio.read()
        nixio.close()
        return ret
    else:
        raise OSError("File Not Found)")
    
def signal_to_atf(data, fileName=None):
    if not isinstance(data, neo.AnalogSignal):
        raise TypeError("Expecting a neo.AnalogSignal; got %s instead" % (type(data).__name__))
    
    if fileName is None:
        cframe = inspect.getouterframes(inspect.currentframe())[1][0]
        try:
            for (k,v) in cframe.f_globals.items():
                if not type(v).__name__ in ("module","type", "function", "builtin_function_or_method"):
                    if v is data and not k.startswith("_"):
                        fileName = strutils.str2symbol(k)
                        #print(fileName)
                    #print(type(v).__name__)
        finally:
            del(cframe)
            
    if fileName is None or not isinstance(fileName, str):
        raise TypeError("Expecting a file name")
        
    
    (name,extn) = os.path.splitext(fileName)
    
    if len(extn) == 0 or extn != ".atf":
        fileName += ".atf"
        
    nColumns = data.shape[1] + 1
        
    csvfile = open(fileName, "w", newline="")
    writer = csv.writer(csvfile, delimiter="\t", quotechar='|', quoting=csv.QUOTE_MINIMAL)
    
    
    # NOTE: 2017-11-24 17:39:19 for clampex up to and including 10.7
    # forget about header and such (clampex keeps complaining, probably because this files
    # comes from UN*X), 
    # just output the time + data columns, then import the file in clampfit where you
    # will be given the chance to set units and time domain
    #
    # actually one could only just save the magnitudes of the signal and specify the time
    # domain in clampex import dialog.
    
    # once imported in clampex then save it as axon binary file, but remember to select
    # fixed interval acquisition mode (otherwise the protocol editor won't be able 
    # to use this file as stimulus file)
    
    try:
        #writer.writerow(["ATF","1.0"])
        #writer.writerow([nColumns,3])
        #writer.writerow(["Type=StimulusFile"])
        #writer.writerow(["DataFileName=%s" % fileName])
        #writer.writerow(["Comment="])
        #writer.writerow(["Time_(%s)" % data.times.units] + ["Amplitude_(%s)" % data.units] * data.shape[1])
        
        values = np.concatenate([data.times.rescale(pq.ms).magnitude[:,np.newaxis], data.magnitude[:]], axis=1)
        
        for l in range(values.shape[0]):
            writer.writerow(values[l,:])
                
        csvfile.close()
        
    except Exception as e:
        traceback.print_exc()
        csvfile.close()
    
def segment_to_atf(segment, fileName=None, 
                   skipHeader=True,
                   skipTimes=True,
                   acquisition_mode="Episodic Stimulation",
                   comment="",
                   SyncTimeUnits=3.33333):
    """
    """
    # NOTE: one segment => one sweep!
    
    if not isinstance(segment, neo.Segment):
        raise TypeError("Expectign a neo.Segment object; got %s instead" % type(segment).__name__)
    
    if len(segment.analogsignals) == 0:
        raise ValueError("Segment has no analogsignals")
    
    if len(segment.analogsignals) > 1:
        sampling_rate =segment.analogsignals[0].sampling_rate
        
        if not all([sig.sampling_rate == sampling_rate for sig in segment.analogsignals[1:]]):
            raise ValueError("All signals in the segment must have the same sampling rate")
        
        t_start = segment.analogsignals[0].t_start
        
        if not all([sig.t_start == t_start for sig in segment.analogsignals[1:]]):
            raise ValueError("All signals in the segment must have the same t_start")
        
        duration = segment.analogsignals[0].duration
        
        if not all([sig.duration == duration for sig in segment.analogsignals[1:]]):
            raise ValueError("All signals in the segment must have the same duration")
        
    if not all([sig.shape[1] == 1 for sig in segment.analogsignals]):
        raise TypeError("All analog signals in the segment must have a single channel (column vectors)")
        
    signal_names = [sig.name for sig in segment.analogsignals]
    
    signal_units = [str(sig.units.dimensionality) for sig in segment.analogsignals]
    
    atf_header = list()
    atf_header.append(["AcquisitionMode=%s" % acquisition_mode])
    atf_header.append(["Comment=%s" % comment])
    atf_header.append(["SweepStartTimeMS=%0.3f" % float(segment.analogsignals[0].t_start.magnitude)])
    atf_header.append(["SignalsExported=%s" % ",".join(signal_names)])
    atf_header.append(["Signals=%s" % "\t".join(signal_names)]) # just ONE sweep !
    
    column_header = ["Time (%s)" % segment.analogsignals[0].t_start.units.dimensionality]
    
    for sig in segment.analogsignals:
        column_header.append("Trace #1 (%s)" % sig.units.dimensionality)
    
    headerlist = list()
    headerlist.append(["ATF\n1.0"])
    
    headerlist.append("%d\n%d" % (len(atf_header), len(column_header)))
    headerlist += atf_header
    headerlist.append(column_header)
    
    #print(headerlist)
    
    if fileName is None:
        cframe = inspect.getouterframes(inspect.currentframe())[1][0]
        try:
            for (k,v) in cframe.f_globals.items():
                if not type(v).__name__ in ("module","type", "function", "builtin_function_or_method"):
                    if v is data and not k.startswith("_"):
                        fileName = strutils.str2symbol(k)

        finally:
            del(cframe)
            
    if fileName is None or not isinstance(fileName, str):
        raise TypeError("Expecting a file name")
        
    
    (name,extn) = os.path.splitext(fileName)
    
    if len(extn) == 0 or extn != ".atf":
        fileName += ".atf"
        
        
    data_columns = list()
    
    if not skipTimes:
        times_array = segment.analogsignals[0].times.rescale(pq.ms).magnitude.flatten()[:,np.newaxis] # force column vector
        data_columns.append(times_array)
    
    data_columns += [sig.magnitude.flatten()[:,np.newaxis] for sig in segment.analogsignals]
    
    data = np.concatenate(data_columns, axis=1)
    
    csvfile = open(fileName, "w", newline="")
    writer = csv.writer(csvfile, delimiter="\t")
    
    try:
        if not skipHeader:
            writer.writerows(headerlist)
            
        for l in data:
            writer.writerow(l)
                
        csvfile.close()

    except Exception as e:
        traceback.print_exc()
        csvfile.close()


    #elif isinstance(data, np.ndarray):
        #if header is not None:
            #if isinstance(header, (tuple, list)):
                #if data.ndim != 2:
                    #raise ValueError("When header is given, data is expected to have two dimensions; instead, it has %d" % data.ndim)
                
                #if len(header) != data.shape[1]:
                    #raise ValueError("When header is given, it must have as many elements as columns in data (%d); instead it has %d" %(data.shape[1], len(header)))
                
                #if isinstance(header, tuple):
                    #headerlist = list(header)
                    
                #else:
                    #headerlist = header

            #elif isinstance(header, np.ndarray) and header.dtype.str.startswith("<U") and header.shape[1]==data.shape[1]:
                #headerlist = [list(r) for r in header]
                
            #else:
                #raise TypeError("Unexpected data type for header; should have been a list or tuple with %d element or a np.ndarray with %d columns and %s dtype; instead I've got %s" %(data.shape[1], data.shape[1], "<U10", type(header).__name__))
            
        #else:
            #headerlist = None
            
@safeWrapper
def writeCsv(data, fileName=None, header=None):
    """Exports data to a csv (TAB-separated) file
    
    data: a column vector or a matrix (np.ndarray)
    
    fileName: file name to write to (".csv" extension will be appended if missing)
    
    countRows: boolean, optional (default False); when True, row number (0-based) 
                will be prepended to each row of data (excluding header rows)
                
    header: optional header (default None); it can be:
            * a sequence of strings (list or tuple) with as many elements as columns
                in data
                
            * a 2D np array of strings (dtype "<U10") with as mny columns as 
                data columns and as many rows as needed
                
            * any other data structure will raise TypeError
    
    """
    
    if fileName is None:
        cframe = inspect.getouterframes(inspect.currentframe())[1][0]
        try:
            for (k,v) in cframe.f_globals.items():
                if not type(v).__name__ in ("module","type", "function", "builtin_function_or_method"):
                    if v is data and not k.startswith("_"):
                        fileName = strutils.str2symbol(k)
                        #print(fileName)
                    #print(type(v).__name__)
        finally:
            del(cframe)
            
    if fileName is None or not isinstance(fileName, str):
        raise TypeError("Expecting a file name")
        
    
    (name,extn) = os.path.splitext(fileName)
    
    #print(extn)
    
    if len(extn) == 0 or extn != ".csv":
        fileName += ".csv"
        
    if isinstance(data, neo.SpikeTrain):
        pass
    
    elif isinstance(data, (pd.Series, pd.DataFrame)):
        data.to_csv(fileName, header=True, na_rep="NA")
    
    elif isinstance(data, dict):
        raise NotImplementedError("Exporting dict to CSV files is not supported")
        #fieldnames = list(data.keys())
        #fieldnames.sort()
        
        ##NOTE: 2017-10-11 21:42:01
        ##DictWriter is good for plain & simple dictionaries where the values are POD types
        ##but falls short of requirements for more complex data structures, and
        ##in particular for NESTED dictionaries to any level
        
        ##TODO I need to emulate a "tree-like" structure here, 
        ##see about writing dict as CSV files.py in this directory
        
        #with open(fileName, "w") as csvfile:
            #writer = csv.DictWriter(csvfile, fieldnames, \
                #extrasaction="ignore", restval="None", \
                #delimiter = "\t")
            
            #writer.writeheader()
            
            #for (k,v) in data.items():
                #row_dict = {k : "%s:" % (type(v).__name__)}
                #if isinstance(v, (str, numbers.Number)):
                    #writer.writerow({k: v})
                #else:
                    #writer.writerow({k : "%s:" % (type(v).__name__)})
                ## TODO FIXME
                ##if isinstance(v, neo.SpikeTrain):
                ##elif isinstance(v, )
                                  
                ##if isinstance(v, np.ndarray):
                    ##for l in 
                    
    ## TODO for neo & datatypes signals must export the domain values too (e.g. time, etc)
    ## in column 0 of the csv
    elif isinstance(data, (neo.IrregularlySampledSignal, datasignal.IrregularlySampledDataSignal)):
        if header is not None:
            if isinstance(header, (tuple, list)):
                if data.ndim != 2:
                    raise ValueError("When header is given, data is expected to have two dimensions; instead, it has %d" % data.ndim)
                
                if len(header) != data.shape[1]:
                    raise ValueError("When header is given, it must have as many elements as columns in data (%d); instead it has %d" %(data.shape[1], len(header)))
                
                if isinstance(header, tuple):
                    headerlist = list(header)
                    
                else:
                    headerlist = header

            elif isinstance(header, np.ndarray) and header.dtype.str.startswith("<U") and header.shape[1]==data.shape[1]:
                headerlist = [list(r) for r in header]
                
            else:
                raise TypeError("Unexpected data type for header; should have been a list or tuple with %d element or a np.ndarray with %d columns and %s dtype; instead I've got %s" %(data.shape[1], data.shape[1], "<U10", type(header).__name__))
            
        else:
            headerlist = ["Time", strutils.str2symbol(data.name)] if isinstance(data, neo.IrregularlySampledSignal) else [strutils.str2symbol(data.domain_name), 
                                                                                                                                            strutils.str2symbol(data.name)]
            
        csvfile = open(fileName, "w", newline="")
        writer = csv.writer(csvfile, delimiter="\t")
            
        try:
            if headerlist is not None:
                writer.writerow(headerlist)
                
            for t, l in zip(data.times, data):
                writer.writerow(["%f %s" % (t, t.units.dimensionality), "%f %s" % (l, l.units.dimensionality)])
                    
            csvfile.close()

        except Exception as e:
            print(str(e))
            csvfile.close()
            
        
        
    elif isinstance(data, np.ndarray):
        if data.ndim > 2:
            raise NotImplementedError("Exporting a numpy array with more than two dimensions as csv is not supported.")
        
        if header is not None:
            if isinstance(header, (tuple, list)):
                if data.ndim != 2:
                    raise ValueError("When header is given, data is expected to have two dimensions; instead, it has %d" % data.ndim)
                
                if len(header) != data.shape[1]:
                    raise ValueError("When header is given, it must have as many elements as columns in data (%d); instead it has %d" %(data.shape[1], len(header)))
                
                if isinstance(header, tuple):
                    headerlist = list(header)
                    
                else:
                    headerlist = header

            elif isinstance(header, np.ndarray) and header.dtype.str.startswith("<U") and header.shape[1]==data.shape[1]:
                headerlist = [list(r) for r in header]
                
            else:
                raise TypeError("Unexpected data type for header; should have been a list or tuple with %d element or a np.ndarray with %d columns and %s dtype; instead I've got %s" %(data.shape[1], data.shape[1], "<U10", type(header).__name__))
            
        else:
            headerlist = None
            
        csvfile = open(fileName, "w", newline="")
        writer = csv.writer(csvfile, delimiter="\t")
        
        try:
            if headerlist is not None:
                writer.writerow(headerlist)
                
            for l in data:
                writer.writerow(l)
                    
            csvfile.close()

        except Exception as e:
            print(str(e))
            csvfile.close()
            
def loadXMLFile(fileName):
    if os.path.isfile(fileName):
        ret = xmlutils.xml.dom.minidom.parse(fileName)
        # augument with a text node called "document_filesource"
        #print("loadXMLFile: doc path",  os.path.dirname(fileName))
        #print("loadXMLFile: doc file name",  os.path.basename(fileName))
        
        doc_filepath = ret.createElement("DocPath")
        doc_path = ret.createTextNode(os.path.dirname(fileName))
        doc_filepath.appendChild(doc_path)
        ret.documentElement.appendChild(doc_filepath)
        
        doc_name = ret.createElement("DocFileName")
        doc_fn = ret.createTextNode(os.path.basename(fileName))
        doc_name.appendChild(doc_fn)
        ret.documentElement.appendChild(doc_name)
        
        return ret
    else:
        raise OSError("File %s not found" % fileName)
    
    
#"def" loadBinaryFile(fileName, buffered=True):
    #""" TODO """
    #if os.path.isfile(fileName):
        #pass
    #else:
        #raise OSError("File %s not found" % fileName)

def loadTextFile(fileName, forceText=False):
    if os.path.isfile(fileName):
        # we may have been landed here from an Axon Text File
        root, ext = os.path.splitext(fileName)
        
        if ext.lower() == ".atf":
            return loadAxonTextFile(fileName)
        
        f = open(fileName, "r", encoding="utf-8")
        text = f.readlines()
        f.close()
        
        ret = "".join(text)
        
        # NOTE: 2017-06-29 14:29:01
        # sometimes a text file contains XML data but it has not been recognized
        # as such by the mime type / magic systems
        if "<?xml version" in text[0] and not forceText:
            import xml.dom.minidom
            try:
                text1 = ret.replace("&#x1;", "; ")
                ret = xml.dom.minidom.parseString(text1)
                # augument with a text node called "document_filesource"
                
                #print("loadTextFile: doc path",  os.path.dirname(fileName))
                #print("loadTextFile: doc file name",  os.path.basename(fileName))
                
                doc_filepath = ret.createElement("DocPath")
                doc_path = ret.createTextNode(os.path.dirname(fileName))
                doc_filepath.appendChild(doc_path)
                ret.documentElement.appendChild(doc_filepath)
                
                doc_name = ret.createElement("DocFileName")
                doc_fn = ret.createTextNode(os.path.basename(fileName))
                doc_name.appendChild(doc_fn)
                ret.documentElement.appendChild(doc_name)
                
                return ret
            except Exception as e:
                excInfo = sys.exc_info()
                traceback.print_exception(excInfo[0], excInfo[1], excInfo[2])
                
        #ret = xmlutils.xml.dom.minidom.parse(fileName)
        return ret
    else:
        raise OSError("File %s not found" % fileName)
    
    
#NOTE:2017-06-29 15:32:58
# this MUST be left here as it needs the functions above to have been defined
fileLoaders = collections.defaultdict(lambda: None) # default dict where missing keys return None

for e in SUPPORTED_IMAGE_TYPES:
    fileLoaders["image/"+e] = loadImageFile
    
fileLoaders["application/axon-data"] = loadAxonFile
fileLoaders["application/x-crossover-abf"] = loadAxonFile
fileLoaders["application/axon-binary-file"] = loadAxonFile
fileLoaders["application/x-crossover-atf"] = loadAxonTextFile
fileLoaders["application/axon-text-file"] = loadAxonTextFile
fileLoaders["application/x-pickle"] = loadPickleFile
fileLoaders["application/x-hdf"] = loadNixIOFile
fileLoaders["text/xml"] = loadXMLFile
fileLoaders["text/plain"] = loadTextFile
fileLoaders["application/x-matlab"] = loadMatlab
fileLoaders["application/x-octave"] = loadOctave
fileLoaders["application/octet-stream"]

def getLoaderForFile(fName):
    if "pkl" in os.path.splitext(fName)[-1]:
        return fileLoaders["application/x-pickle"]
    
    mime_type, file_type, _ = getMimeAndFileType(fName)
    
    ret = fileLoaders[mime_type] # fileLoaders is a default dict with None the default value
    
    if ret is None: 
        # fileLoaders doesn't have a mapping for this mime_type
        ret = loadTextFile # fallback
        
        if file_type == "data":
            with open(fName, mode="rb") as file_object:
                header = file_object.readline()
                if b"ABF" in header:
                    ret = loadAxonFile
                    
                else:
                    warnings.warn("Don't know how to open %s" % fName, RuntimeWarning)

        
        ## plain python mimtype module has failed;
        ## try pyxdg Mime submodule:
        #if Mime is not None:
            ## Mime is a class in pyxdg
            ## for unknown stuff Mime returns text/plain?
            #mime = Mime.get_type(fName)
            #mime_type = "/".join([mime.media, mime.subtype]) # e.g. "text/plain"
            ##mime_type = mime.get_comment() # this can be more than just media/subtype !
            
            ## if this is recognized as text/plain, make sure it is so:
            #if "text" in mime_type and "plain" in mime_type:
                ## as a last resort use libmagic to find out a bit more about this file
                #if magic is not None:
                    #if os.path.isfile(fName):
                        #file_type = magic.from_file(fName).decode() # from_file returns a bytes object
                        ## most of the times, this just confirms the above?
                        #if "text" in file_type:
                            #with open(fName, mode="rt") as file_object:
                                #header = file_object.readline()
                                #if "ATF" in header:
                                    #ret = loadAxonFile
                                    
                                #else:
                                    #ret = loadTextFile
                                    
    return ret

def getMimeAndFileType(fileName):
    """Returns the mime type and the file type for the file specified by fileName.
    
    Parameters:
    -----------
    fileName : str; the name of a file (can be relative or absolute path)
    
    Returns:
    --------
    mime_type: str or None; 
        the mime type of the file as defined in the system's mime-type utilities 
        (mime.magic or desktop environments aware of freedesktop.org standards)
        
        Will be set to None when the mime type could not be determined
        
    file_type: str or None; 
        the type of the file (ASCII, binary, etc) as returned by libmagic
        
        Will be set to None if the file type could not be determined
        
    encoding: str or None; 
        the encoding of the file as reported by the system's mime-type utilities 
    """
    
    file_type = None
    mime_type = None
    encoding = None
    
    # NOTE: 2020-02-16 18:15:34
    # 1) DETERMINE THE FILE TYPE
    # 1.1) try the python-magic first
    if libmagic is not None:
        # magic module is loaded
        try:
            if os.path.isfile(fileName):
                file_type = libmagic.from_file(fileName)
            
                if isinstance(file_type, bytes):
                    file_type = file_type.decode()
                
        except Exception as e:
            traceback.print_exc()
            
    # 1.2) try the system "file" command
    if file_type is None:
        try:
            if os.path.isfile(fileName):
                file_type = os.popen("file %s" % fileName).read()

        except Exception as e:
            traceback.print_exc()
            
    # 2) DETERMINE THE MIME TYPE
    # 2.1) try the pyxdg module
    if xdgmime is not None:
        try:
            mime = xdgmime.get_type(fileName)
            mime_type = "/".join([mime.media, mime.subtype]) # e.g. "text/plain"
            #mime_type = mime.get_comment() # don't rely on this as it can have more than just "media/subtype" !
        
        except Exception as e:
            traceback.print_exc()
            
    # 2.2) try the mimetypes module
    # NOTE: 2021-04-12 11:31:29
    # this is in case the actual file type and mime type are not registered
    # with either the global or the user mime data base(s)
    if mime_type in ["application/executable", None] or file_type is "data":
        _mime_type, encoding = mimetypes.guess_type(fileName)
        if _mime_type is not None:
            # NOTE: 2021-04-12 11:31:24
            # if mimetypes report None for type, revert to what xdgmime returned
            mime_type = _mime_type
        
    return mime_type, file_type, encoding
        
def loadFile(fName):

    value = None
    
    fileLoader = getLoaderForFile(fName)
    
    value = fileLoader(fName)
    
    return value

@safeWrapper
def writeHDF5(obj, filenameOrGroup, pathInFile, compression=None, chunks=None, track_order=True):
    """
    TODO Work in progress, do NOT use
    """
    if not isinstance(obj, dict):
        raise TypeError("Expecting a dict; got %s instead" % type(obj).__name__)
    
    group = None
    
    if isinstance(filenameOrGroup, str):
        if len(filenameOrGroup.strip()) == 0:
            raise ValueError("when a str, 'filenameOrGroup' must not be empty")
        
        else:
            filenameOrGroup = h5py.File(filenameOrGroup, "w")
            
    elif not isinstance(filenameOrGroup, h5py.Group):
        raise TypeError("'filenameOrGroup' expected to be a str or a h5py.Group; got %s instead" % type(filenameOrGroup).__name__)
    
    if isinstance(pathInFile, str):
        if len(pathInFile.strip()) == 0:
            raise ValueError("'pathInFile' must not be empty")
        
    else:
        raise TypeError("'pathInFile' expected to be astr; got %s instead" % pathInFile)
    
    group = filenameOrGroup.create_group(pathInFile, track_order=track_order)
    
    if isinstance(obj. dict):
        for key, value in obj.items():
            key_group = writeHDF5(value, group, key, track_order = track_order)
            
    elif isinstance(value, vigra.VigraArray):
        vigra.impex.writeHDF5(value, group, key,compression=compression, chunks=chunks)
        
    elif isinstance(value, np.ndarray):
        group.create_dataset(key, shape=value.shape, dtype=value.dtype, data=data, 
                            chunks=chunks, compression=compression, track_order=track_order)
        
    elif isinstance(value, (tuple, list)):
        array = np.array(value)
        group.create_dataset(key, shape=array.shape, dtype=array.dtype, data=array, 
                            chunks=chunks, compression=compression, track_order=track_order)
        

    #if "/" in pathInFile:
        #group_path = [s for s in pathInFile.split("/") if len(s.strip())]
        
    if isinstance(filenameOrGroup, h5py.File):
        filenameOrGroup.close()
        
    return filenameOrGroup
    
@safeWrapper
def export_to_hdf5(obj, filenameOrGroup, name=None):
    """
    Parameters:
    ----------
    
    obj: Python object
    
    file_name: str
        name of the hdf5 file written to disk
        
    name: str or None (default)
        group name for storing the object inside the file
        
        When None (default) or an empty string, the object is stored under a 
        group called "object" unless object is a dict in which case its members are
        stored at the top level in the file.
        
    """
    # TODO
    if not isinstance(filenameOrGroup, str):
        raise TypeError("file_name must be a str; got %s instead" % type(file_name).__name__)
    
    if len(file_name.strip()) == 0:
        raise ValueError("file_name is empty")
    
    fn, fext = os.path.splitext(file_name)
    
    if len(fext.strip) <= 1:
        fext = ".hdf5"
        
        file_name = "".join((fn, fext))

    f = h5py.File(file_name, "w")
    
    if isinstance(obj, dict):
        if isinstance(name, str) and len(name.strip()):
            obj_group = f.create_group(name, track_order=True)
            
        else:
            for k, v in obj.items():
                key_group = f.create_group("%s" % k, track_order=True)
            
    else:
        if isinstance(name, str) and len(name.strip()):
            obj_group = f.create_group(name, track_order=True)
            
        else:
            obj_group = f.create_group("object", track_order=True)
            
    

    f.close()
    
@safeWrapper
def save_settings(config:typing.Optional[confuse.Configuration]=None, filename:typing.Optional[str]=None, 
                  full:bool=True, redact:bool=False, as_default:bool=False,
                  default_only:bool=False) -> bool:
    """Saves Scipyen non-gui configuration options to an yaml file.
    Settings are saved implicitly to the config.yaml file located in the 
    application configuration directory and stored in the 'filename' attribute
    of the first configuration source.
    
    What can be dumped (below, 'default' refers to the 'package default' settings
    stored in config_default.yaml located in scipyen directory):
    
    1) all settings even if they are no different from the defaults - useful to
    genereate/update the default settings when 'as_default' is True
    
    2) only settings that are different from the defaults 
    WARNING specifying 'as_default' True will overwrite the default settings.
    
    3) of either (1) or (2) the redacted settings may be left out
    
    Named parameters:
    ================
    config: a confuse.ConfigView object, or None (default)
        
        When None, this defaults to the 'scipyen_settings' in the user workspace.
        
        Otherwise, this can be a confuse.Configuration (or confuse.LazyConfig) 
        object, or a confuse.SubView (the latter is useful to dump a subset of 
        configuration settings to a local file).
    
    filename: str or None (default).
        Specifies the file where the configuration will be dumped. An '.yaml'
        extension will be added to the file if not present.
        
        When None (the default) the configuration settings are saved to 
        the user's 'config.yaml' file, or to the config_default.yaml file located
        in scipyen directory if 'as_default' is True
        
    full: bool
        When True (default) dump as in case (1) above
    
    redact: bool
        When False (default) the redacted settings are left out 
        (i.e., not dumped)
        
    as_default:bool. 
        When False (default) the settings will be dumped to the file specified 
        by 'filename', or to the 'config_default.yaml' file in the application
        configuration directory
        
    default_only:bool, default is False
        When True, only the package default values will be saved to the 
        config_default.yaml. The 'full' and 'as_default' parameters are ignored.
    
    """
    if config is None:
        user_ns = user_workspace()
        config = user_ns["scipyen_settings"]
        
    if not isinstance(config, confuse.ConfigView):
        return False
    
    defsrc = [s for s in config.sources if s.default] # default source
    src = [s for s in config.sources if not s.default] # non-default sources
    out = ""
    
    if default_only:
        as_default = True # force saving to the package default
    
    if filename is None or (isinstance(filename, str) and len(filename.strip()) == 0):
        if as_default:
            filename = defsrc[-1].filename
        else:
            filename = src[-1].filename
    else:
        (fn, ext) = os.path.splitext(filename)
        if ext != ".yaml":
            filename = ".".join([fn, "yaml"])
            
    if isinstance(config, confuse.Configuration): # Configuration and LazyConfig
        out = config.dump(full=full, redact=redact)
        
    else:
        if full:
            out = config.flatten(redact=redact)
        else: # exclude defaults
            temp_root = confuse.RootView(src)
            temp_root.redactions = config.redactions
            out = temp_root.flatten(redact=redact)

    #NOTE: 2021-01-13 17:23:36
    # allow the use of empty output - effectively this wipes out the yaml file
    # NOTE: 2021-01-13 17:25:25
    # because of this, we allow here a GUI dialog (QMessageBox) warning the user
    # to the possiblity of wiping out the config_default.yaml file!
    if len(out) == 0:
        txt = "The configuration file %s is about to be cleared. Do you wish to continue?" % filename
        ret = QtWidgets.QMessageBox.warning(None,"Scipyen configuration",txt)
        
        if ret != QtWidgets.QMessageBox.OK:
            return False
        
    with open(filename, "wt") as yamlfile:
        yamlfile.write(out)
        
    return True
    

@safeWrapper
def save(*args:typing.Optional[typing.Any], name:typing.Optional[str]=None, 
             ws:typing.Optional[dict]=None, mode:str="pkl", **kwargs):
    """Saves variable(s) in the current working directory.
    WARNING Do not confuse with IPython %save line magic
    TODO adapt to other modes
    """
    
    # NOTE: 2020-10-22 13:41:18
    # better to set this here so that get_symbol_in_namespace looks up in the
    # correct namespace
    if ws is None:
        ws = user_workspace()
        
    if len(args) == 1:
        x = args[0]
        
        if name is None or (isinstance(name, str) and len(name.strip()) == 0):
            names = get_symbol_in_namespace(x, ws=ws)
            
        if len(names):
            fileName = names[0]
            
        else:
            fileName = "object"
            
        if mode == "pkl":
            savePickleFile(x, fileName)
            
        elif mode == "csv":
            writeCsv(x, fileName)  # this picks up if x is a pandas data object and calls the appropriate function
            
        elif mode == "hdf":
            raise NotImplementedError("Saving to HDF5 files not yet supported")
        
        elif mode in ("tif", "png", "jpg"):
            saveImageFile(x, fileName)
            
        elif mode in ("txt", "ascii"):
            with open(fileName, mode="wt") as fileDest:
                fileDest.write(x)
        
        else:
            raise ValueError("Unexpected mode %s" % mode)
        
    else:
        if len(kwargs) > 0:
            if len(kwargs) != len(args):
                raise ValueError("For saving multiple variables, keyword params must be either empty or have the same length as the variadic parameter")
            
            kw = [k for k in kwargs]
            
        else:
            kw = []
            
        for k,x in enumerate(args):
            if len(kw):
                name = kw[k]
                mode = kwargs[kw[k]]
            
            save(x, name=name, mode=mode, ws = ws)
        
    
