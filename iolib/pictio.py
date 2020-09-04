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

import os, sys, traceback, inspect, keyword, warnings
# import  threading
import concurrent.futures
import pickle, pickletools, copyreg, csv, numbers, mimetypes
import collections
from functools import singledispatch
#### END core python modules

#### BEGIN 3rd party modules
import scipy
import scipy.io as sio
import quantities as pq
import numpy as np
import pandas as pd
import xarray as xa
import h5py
import vigra
import neo
from PyQt5 import QtCore, QtGui, QtWidgets
#### END 3rd party modules

#### BEGIN pict.core modules
#from core import neo
#from core import patchneo
from core import (xmlutils, strutils, axisutils, datatypes, datasignal,
                  scandata, axiscalibration, triggerprotocols,
                  neoutils,)

from core.axisutils import *

from core.prog import safeWrapper

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
    from xdg import Mime
    
except Exception as e:
    warnings.warn("Python module 'pyxdg' not found; xdg mime info utilities not available")
    xdg = None
    Mime = None

# NOTE: 2019-04-21 18:34:08 
# somewhat reductant but I found that the Mime module in pyxdg distributed with
# openSUSE does not do is_plain_text(), or get_type2()
# so also use the binding to libmagic here
# ATTENTION: for Windows you need DLLs for libmagic installed separately
# for 64 bit python, install libmagicwin64
# ATTENTION: on Mac OSX you also needs to install libmagic (homebrew) or file (macports)
try:
    import magic # file identification using libmagic
    
except Exception as e:
    warnings.warn("Python module 'magic' not found; advanced file type identification will be limited")
    magic = None




# NOTE: 2016-04-01 10:58:32
# let's have this done once and for all
__vigra_formats__ = vigra.impex.listExtensions()
__ephys_formats__ = ["abf"]
__generic_formats__ = ["pkl", "h5", "csv"]

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

def loadAxonFile(fileName:str) -> neo.Block:
    """Loads a binary Axon file (*.abf).
    
    Parameters:
    -----------
    
    fileName : str; a fully qualified path & file name
    
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
        
        data = axonIO.read_block()
        
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
        
def loadPickleFile(fileName):
    #from core import neoepoch, neoevent
    from core import neoepoch as neoepoch
    from core import neoevent as neoevent
    #from core import scandata, analysisunit, axiscalibration, triggerprotocols
    #from core import 
    #from core import datatypes
    from core.workspacefunctions import assignin
    from gui import pictgui
    from plugins import CaTanalysis
    result = None
    # NOTE: 2019-10-08 10:46:46
    # migration to a new package directory layout
    # breaks loading of old pickle files
    # this affects all pickles that rely on classes previosuly defined in 
    # modules that were present in the top level package but now have been
    # modev to sub-packages (notably, in core)
    # the following attempts to fix this
    sys.modules["neoevent"] = neoevent
    sys.modules["neoepoch"] = neoepoch
    #sys.modules["datatypes"] = datatypes
    sys.modules["pictgui"] = pictgui
    sys.modules["CaTanalysis"] = CaTanalysis
    
    try:
        with open(fileName, mode="rb") as fileSrc:
            result = pickle.load(fileSrc)
            
    except Exception as e:
        exc_info = sys.exc_info()
        frame_summaries = traceback.extract_tb(exc_info[2])
        
        #for kf, frame_summary in enumerate(frame_summaries):
            #print("frame %d" % kf, frame_summary.name)
            
        frame_names = [f.name for f in frame_summaries]
            
        last_frame = frame_summaries[-1]
        offending_module_filename = last_frame.filename
        offending_function = last_frame.name
        
        #print("offending module:", offending_module_filename)
        
        #if "neo" in offending_module_filename or any(["neo" in frn for frn in frame_names]):
        if any([any([s in frn for frn in frame_names]) for s in ("neo", "event", "epoch", "analogsignal", "irregularlysampledsignal")]):
            result = unpickleNeoData(fileName)
            
        else:
            raise e
        
    if isinstance(result, (scandata.ScanData, scandata.AnalysisUnit, axiscalibration.AxisCalibration, pictgui.PlanarGraphics)):
        result._upgrade_API_()
    
    if "neoevent" in sys.modules:
        del sys.modules["neoevent"]
        
    if "neoepoch" in sys.modules:
        del sys.modules["neoepoch"]
        
    #if "datatypes" in sys.modules:
        #del sys.modules["datatypes"]
        
    if "pictgui" in sys.modules:
        del sys.modules["pictgui"]
        
    if "CaTanalysis" in sys.modules:
        del sys.modules["CaTanalysis"]
    
    return result

def unpickleNeoData(fileName):
    import core.patchneo as patchneo
    import core.neoevent as neoevent
    import core.neoepoch as neoepoch
    
    current_new_AnalogSignalArray = neo.core.analogsignal._new_AnalogSignalArray
    current_new_IrregularlySampledSignal = neo.core.irregularlysampledsignal._new_IrregularlySampledSignal
    current_new_spiketrain = neo.core.spiketrain._new_spiketrain
    
    current_new_event = neo.core.event._new_event
    current_Event = neo.core.event.Event
    current_Epoch = neo.core.epoch.Epoch
    
    current_normalize_array_annotations = neo.core.dataobject._normalize_array_annotations
    
    
    try:
        sys.modules["neoevent"] = neoevent
        sys.modules["neoepoch"] = neoepoch
        
        neo.core.dataobject._normalize_array_annotations = patchneo._normalize_array_annotations
        
        neo.core.analogsignal._new_AnalogSignalArray = patchneo._new_AnalogSignalArray_v1
        neo.core.spiketrain._new_spiketrain = patchneo._new_spiketrain_v1
        neo.core.irregularlysampledsignal._new_IrregularlySampledSignal = patchneo._new_IrregularlySampledSignal_v1
        
        neo.core.event._new_event = neoevent._new_event
        neo.core.event.Event = neoevent.Event
        neo.core.Event = neoevent.Event
        neo.io.axonio.Event = neoevent.Event
        neo.Event = neoevent.Event
        
        neo.core.epoch.Epoch = neoepoch.Epoch
        neo.core.Epoch = neoepoch.Epoch
        neo.Epoch = neoepoch.Epoch
        
        
        with open(fileName, mode="rb") as fileSrc:
            result = pickle.load(fileSrc)
            
        del sys.modules["neoevent"]
        del sys.modules["neoepoch"]
                
    except:
        sys.modules["neoevent"] = neoevent
        sys.modules["neoepoch"] = neoepoch
        
        neo.core.dataobject._normalize_array_annotations = patchneo._normalize_array_annotations
        
        neo.core.analogsignal._new_AnalogSignalArray = patchneo._new_AnalogSignalArray_v2
        neo.core.spiketrain._new_spiketrain = patchneo._new_spiketrain_v1
        neo.core.irregularlysampledsignal._new_IrregularlySampledSignal = patchneo._new_IrregularlySampledSignal_v1
        
        neo.core.event._new_event = neoevent._new_event
        neo.core.event.Event = neoevent.Event
        neo.core.Event = neoevent.Event
        neo.io.axonio.Event = neoevent.Event
        neo.Event = neoevent.Event
        
        neo.core.epoch.Epoch = neoepoch.Epoch
        neo.core.Epoch = neoepoch.Epoch
        neo.Epoch = neoepoch.Epoch
        
        with open(fileName, mode="rb") as fileSrc:
            result = pickle.load(fileSrc)
                
        del sys.modules["neoevent"]
        del sys.modules["neoepoch"]
                
    neo.core.dataobject._normalize_array_annotations = current_normalize_array_annotations
    
    neo.core.analogsignal._new_AnalogSignalArray = current_new_AnalogSignalArray
    neo.core.spiketrain._new_spiketrain = current_new_spiketrain
    neo.core.irregularlysampledsignal._new_IrregularlySampledSignal = current_new_IrregularlySampledSignal
    
    neo.core.event._new_event = current_Event
    neo.core.event.Event = current_Event
    neo.core.Event = current_Event
    neo.io.axonio.Event = current_Event
    neo.Event = current_Event
    neo.core.event._new_event = current_new_event
    
    neo.core.epoch.Epoch = current_Epoch
    neo.core.Epoch = current_Epoch
    neo.Epoch = current_Epoch
    
    if "neoevent" in sys.modules:
        del sys.modules["neoevent"]
    
    if "neoepoch" in sys.modules:
        del sys.modules["neoepoch"]
    
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
                        fileName = strutils.string_to_valid_identifier(k)
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
                        fileName = strutils.string_to_valid_identifier(k)

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
                        fileName = strutils.string_to_valid_identifier(k)
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
            headerlist = ["Time", strutils.string_to_valid_identifier(data.name)] if isinstance(data, neo.IrregularlySampledSignal) else [strutils.string_to_valid_identifier(data.domain_name), 
                                                                                                                                            strutils.string_to_valid_identifier(data.name)]
            
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

def loadTextFile(fileName):
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
        if "<?xml version" in text[0]:
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
                    warnings.warning("Don't know how to open %s" % fName, RuntimeWarning)

        
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
        
    """
    #encoding: str or None; 
        #the encoding of the file as reported by the system's mime-type utilities 
    
    file_type = None
    mime_type = None
    encoding = None
    
    # NOTE: 2020-02-16 18:15:34
    # 1) find out the file type
    # 1.1) try the python-magic first
    if magic is not None:
        # magic module is loaded
        try:
            if os.path.isfile(fileName):
                file_type = magic.from_file(fileName)
            
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
            
    # 2) determine the mime type
    # 2.1) try the pyxdg module
    if Mime is not None:
        try:
            mime = Mime.get_type(fileName)
            mime_type = "/".join([mime.media, mime.subtype]) # e.g. "text/plain"
            #mime_type = mime.get_comment() # don't rely on this as it can have more than just "media/subtype" !
        
        except Exception as e:
            traceback_print_exc()
            
    # 2.2) try the mimetypes module
    if mime_type is None:
        mime_type, encoding = mimetypes.guess_type(fileName)
        
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
