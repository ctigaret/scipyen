# -*- coding: utf-8 -*-
"""Vigra input/output functions moved here so that we can separate dependencies
from vigranumpy (which may or may ont be available on the platform)
NOTE: 2021-11-09 17:47:35
Migration aborted: VIGRA is mandaotyr for scipyen on ALL platforms
"""
from __future__ import print_function
import sys, os, typing, traceback, inspect, warnings, io, importlib
import collections


has_vigra=False
try:
    import vigra
    has_vigra=True
    VigraType  = typing.TypeVar["VigraType", vigra.VigraArray]
except:
    VigraType  = typing.TypeVar["VigraType", np.ndarray]
    pass

 NOTE: 2017-09-21 16:34:21
# BioFormats dumped mid 2017 because there are no good python ports to it
# (it uses javabridge which is suboptimal)
#def loadImageFile(fileName:str, asVolume:bool=False, axisspec:[collections.OrderedDict, None]=None) -> ([vigra.VigraArray, np.ndarray],):
def loadImageFile(fileName:str, asVolume:bool=False, axisspec:[collections.OrderedDict, None]=None) -> VigraType:
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
    
