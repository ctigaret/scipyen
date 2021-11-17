"""Collection of functions to read/write objects to HDF5 files.

STORING SIGNALS AND IMAGES IN HDF5 OBJECT HIERARCHY:
====================================================

NOTE: HDF5 object hierarchy consists of:
h5py.Group (this type is an ancestor of h5py.File which behavies like a 
h5py.Group with IO functionality)
    
A Group is a container of:
    
h5py.Dataset - similar to a numpy array including having the 'ndim' and 'shape'
    properties.

Dimension scales:
    A data set can associate a dimension scale with each axis (or dimension);
    while these are opaque objects whuch are not supposed to be directly 
    constructed by the user, they are managed by the Dataset accessed via its
    'dims' property:
    
    dataset.dims[0] ... dataset.dims[k] for 0 <= k < len(dataset.dims))
    
    A dimension scale can be constructed from another data set (as a reference)
    stored along the main data set preferably in the same group, but certainly in
    the same file (although HDF5 allows external references, I will keep the code
    simpler and avoid this strategy).
    
Both Group and Dataset objects associate attributes ('attr' property) which is a
dict-like object (a 'mapping') with str keys mapped to any type of basic Python
data type (numeric scalars and strings, but not Python containers)!


NOTE: 1D signals are BY CONVENTION represented as column vectors.
    
    Representation of time-varying quantity (a 'signal') of N samples:
    * with data recorded through a single recording channel:
        - 1D numpy array -> just one axis - axis 0 - the 'domain axis' 
            shape: (N, ), vector
            
        - 2D numpy array with the second axis (axis 1) being a singleton axis
            shape: (N, 1), 'column vector'
        
        In either case, axis 0 is the domain axis with domain_name = "Time"
        and axis_name "Time"; axis 1 (when it exists) is the channel axis.
        
    * with data recorded through more than one channel:
        2D numpy array with shape (N,M) where M is the number of channels
            axis 0 - the domain axis (as above)
            axis 1 - channel axis
            
    The domain axis usually associates units of the quantity representing the 
    domain of the signal: e.g. 's' for time, 'um' for space, etc.

    All channels of a signal SHOULD have the same units, since they contain
    values of the same physical measure (albeit possibly with different 
    scaling or amplification factors). Furthermore, the sampling period (and 
    obviously, rate) is identical for all the channels - hence the domain is
    common.
    
    In electrophysiology, fortunately most acquisition systems usually manage
    the channel calibration such that the data stored in a channel represents 
    the values of the physical measure recorded by the system, instead of the
    raw (uncalibrated) amplifier output.
    
    In imaging, however, as in the more general case, the concept of 
    channels may be taken in a looser sense (unfortunately): most image 
    acquisition system record pixel intensity data in each channel.
    
    In multiphoton imaging an "acquisition signal" can represent fluorescent
    data from an indicator, or data obtained from a transmitted light detector
    (sometimes dubbed the "DIC" channel in some acquisition software). 
    
    Even two fluorescent "channels" acquired from the same source or field 
    of view can represent two different quantities, depending on what the
    fluorescent indicator is used for.
    
    For this reason, each channel needs to associate its own calibration data
    to account for the correspondence between the pixel intensity in that 
    channel and the value of the imaged physical measure.
    
    Furthermore, from a numerical point of view, the pixel intensities can 
    be represented as scalar values (in "gray-scale" images) or as sequences
    of scalars (RGB, RGBAlpha, Luv, etc) in so-called multi-band images
    (also loosely called multi-channel images).
    
    The distinction between a "pixel channel" and a data channel can be
    further blurred when gray scale images (each form one "data" channel)
    are merged into a multi-band image (mostly for display convenience).
    
    One thing that all the image channels have in common is the definition
    domain of the physical measure (time, space, frequency, etc) and hence
    their sampling period (or "resolution").
    
    
    In a nutshell:
    
        domain axis, or axes: common to all signal/image channels
            one axis for 1D arrays or for 2D arrays where second axis (axis 1)
            is a singleton axis
            
            two axes for numpy arrays with at least two dimensions; these
            can be any combination of (space, time, frequency, angle) axes 
            as appropriate (see vigra.AxisType for details).
            
        channel axis: (for whatever a "channel" is taken to represent)
            only exists for numpy arrays with at least two dimensions
            typically is the highest-order axis (e.g, 2nd axis for a 1D signal
            3rd axis for an image, 4th axis for a volume, etc).
            
        For imaging, vigra library saves the day through the AxisTags concepts
        (see vigranumpy documentation). Acipyen add to this the concept of
        CalibrationData: AxisCalibrationData and ChannelCalibrationData, with
        the latter used to encapsulate calibrate the pixel intensities in a 
        given image channel.
        
        For electrophysiology, the neo package considers all signals as
        column vectors, with the domain given in the neo object metadata
        ('times' attribute). Scipyen extents this for signals defined on 
        domains other than time (see DataSignal, IrregularlySampledDataSignal,
        DataZone, DataMark).
        
    Representation of signals and images as h5py Dataset objects ('signal datasets'):
    
    * Each dimension of the data set associates a dimension scale. The dimension
    scales are made from h5py Dataset objects stored in a h5py.Group usually 
    located in the same group as the dataset's parent, and named after the 
    signal's dataset name suffixed with "_axes".
    
    The <dataset_name>_axes group contains the data sets that store axis 
    information ('axis data sets'). With few exceptions, the axis information 
    itself is stored as attributes of the axis data set (key/value pairs in the
    axis data set 'attrs' property)
    
    The exceptions are for the domain axis of irregularly sampled signals, 
    neo.Epoch and DataZone objects which associate additional array-like domain 
    information:
    * the actual "times" values for irregular signals
    * the "durations" values for Epoch and DataZone objects
    
    Dimension scales are constructed from these 'axis data sets' using the 
    'Dataset.make_scale()' method, then attached to the corresponding dimension of
    the 'signal data set' using the Dimension scale's 'attach_scale()' method.
    
    The various combinations are described in the table below
    
Object      Signal  Data            Dimension   Comment Axis data   Axis data set
type        data    set             cale               data        attrs keys:
type        set     attrs                              set
================================================================================  
BaseSignal(1)

* regularly sampled signals(2):

            2D      metadata        dims[0]     domain  empty set   'units': str(4)          
                    including       'label'             (3)         't_start' OR 'origin':  float scalar       
                    annotations      =                               
                                    signal.name                                              
                                                                    'sampling_rate' OR        
                                                                    'sampling_period': float scalar                  
                                                                    
                                                                    'sampling_rate_units': str
                                                                    'sampling_period_units': str
                                                            
                                                                    'name': str = the domain name(5)
                                                
                                    dims[1]     signal  empty set   'units' : str(3)       
                                                                    'name':str = signal name    
                                                                    
                                                                    << optional keys >>    
                                                                    
                                                                    'origin': float scalar                  
                                                                    'resolution': float scalar    
                                                                    'ADClevels': float scalar    
                                                                    
                                                channel empty set   'units':str    
                                                (6)                 'name': str = signal.name_channel_k for kth channel 
                                                                    
                                                                    << optional keys >>    
                                                                    
                                                                    'origin': float scalar                  
                                                                    'resolution': float scalar        
                                                                    'ADClevels': float scalar  
                                                                    'index': int = k
                                                                    
                                                                    other keys from  'array_annotations'    
                                    
                                    
* irregularly sampled signals (7):

            2D      metadata,       dims[0]     domain  'times'    'units' : str(4)      
                    annotations     'label'             values     't_start' OR 'origin':float scalar     
                                     =                          
                                    signal.name                                          
                                                            
                                                                    'name':str = the domain name(5)
                                                
                                    dims[1]     signal  empty set   'units' : str(3)   
                                                                    'name':str = signal name
                                                                    
                                                                    << optional keys >>
                                                                    
                                                                    'origin': float scalar              
                                                                    'resolution': float scalar
                                                                    'ADClevels': float scalar
                                                                    
                                                channel empty set   'units':str
                                                (6)                 'name': str = signal.name_channel_k for kth channel
                                                                
                                                                    << optional keys >>
                                                                    
                                                                    'origin': float scalar              
                                                                    'resolution': float scalar    
                                                                    'ADClevels': float scalar
                                                                    
                                                                    other keys from 'array_annotations'
                                        
                                    
* neo.ImageSequence:   by definition these are gray-scale (single-channel or
                        single-band images) ; their units and signal name go 
                        as attributes of the signal data set, in the metadata

            3D      metadata,       dims[0]  frame axis             'sampling_rate': float scalar
                    anotations                                      'sampling_rate_units' : str
                    
                                    dims[1]  height axis            'spatial_scale: float_scalar
                                                                    'spatial_scale_units': str
                                                                    
                                    dims[2]  width axis             'spatial_scale'
                                                                    'spatial_scale_units': str


DataObject other than BaseSignal (8)
        For these, the signal data set already contains their "times" values.
        moreover, these are by defintion single-channel.

neo.Event, DataMark (including TriggerEvent)

            1D      metadata        dims[0]     domain  'labels'    'name':str = the domain name           
                    annotations    'label'               values     
                                    set to                                      
                                    signal.name                                          
                                                
neo.Epoch, DataZone - the data set contains the 'times' or 'places' in column 0 
                        and 'durations' or 'extents', respectively, in column 1

            2D      metadata        dims[0]     domain  empty set   'name':str = the domain name           
                    annotations     'label'                           
                                    set to                                      
                                    signal.name                                          
                                                                                
                                    dims[1]             'labels' 
                                    'label'             (numpy dtype(U))
                                    set to 'labels'
                                    
neo.SpikeTrain - the data set can be multi-channel (each channel from a different 
                cell) with the 'times' for each channel in a column
                
    SpikeTrain objects also have a 'waveforms' propery which when not empty it is 
    a pq.Quantity array (all waveforms are assumed to represent the same physical
    measure, typically electrical potential, the "data" associated with each spike
    "time stamp"). 
    
    This is stored as a h5py Dataset in the axes group is also added as dimension
    scale to the dims[1] of the signal data set of the spike train.
    
    The waveforms data set has its own dimension scales (see below).
                
            2D      metadata        dims[0]     domain  empty set   'name': str = "Time"
                    annotations
                                    dims[1]     channel empty set   'name': str = channel_k
                                               
                                                waveforms (see below)
                                               
                                               
neo.SpikeTrain.waveforms: neo API specifies a 3D pq.Quantity array:

            3D     'name':str       dims[0]     spike    empty set   'name': str = 'spike #'
    [spike_number, 'waveforms'                                       'units': str = 'dimensionless'
     channel,      'units':str =  
     time]         waveform.units                               
                                    dims[1]     channel  empty set    'name': str = 'channel_k'
                      
                                    dims[2]     domain   empty set    'name': str ='Time' 
                    
                    
    However, the 3D layout is not enforced and waveforms from a singleton channel
    can be stored as a 2D array [spike, time]
    
            2D      'name':str      dims[0]     spike    empty set     'name': str = 'spike #'
                    'waveforms'                                        'units' : str = 'dimensionless'
                    'units' str =
                    waveforms.units
                    
                                    dims[1]     domain   empty set     'name': str = domain's name, usually "Time"
                                                                       'units': str = domain units e.g. 's'
                                                                       
vigra.VigraArray- N-dimensional numeric arrays
    ND data set containing the VigraArray data transposed to numpy order
                    
            ND      metadata        dims[k]     kth axis empty set 
                    'axistags'
                                                constructed from corresponding 
                                                AxisCalibrationData object and
                                                has the following atrributes:
                                                'key'
                                                'name'
                                                'units'
                                                'origin'
                                                'resolution'
                                                
        NOTE: when kth axis is a Channels axis (at most one) then dims[k]
        associated dimension scales for each channel created in a 
        group '<signal_name>_channels' alongside the axes group.
        
        A channel dimension scale is constructed from empty data sets
        and has the following attributes:
        'name', 
        'units', 
        'origin', 
        'resolution', 
        'maximum',
        'index': int the channel's index along the channels axis
        
        The atttributes are populated from ChannelCalibrationData for the 
        corresponding channel.
        
vigra.filters.Kernel1D: - stored as 2D array (column vectors) with the 
        domain (kernel sample coordinates) on column 0 and
        kernel sample values on column 1 (see vigrautils.kernel2array())
        
        ATTENTION: No dimension scales are attached to the data set
    
        NOTE: to reconstitute an 1D kernel:
        k1d = vigra.filters.Kernel1D()
        xy = group[dataset_name] => 2D array
        left = int(xy[0,0])
        right = int(xy[-1,0])
        contents = xy[:,1]
        l1d.initExplicitly(left, right, xy[:,1])
        
vigra.filters.Kernel2D: stored as 3D array with:
        [x coordinates, y coordinates, sample values] slices where each 
        slice if a 2D array (see vigrautils.kernel2array)
    
        ATTENTION: No dimension scales are attached to the data set
                
        NOTE: to reconstitute a 2D kernel:
        k2d = vigra.filters.Kernel2D()
        xy = group[dataset_name] => 3D array
        upperLeft = (int(xy[-1,-1,0]), int(xy[-1,-1,1]))
        lowerRight = (int(xy[0,0,0]), int(xy[0,0,1]))
        contents = xy[:,:,2]
        k2d.initExplicitly(upperLeft, lowerRight, contents)
        
Python quantities.Quantity arrays (pq.Quantity):
        ND data set; attrs keys include
        'units' : str = data.units.dimensionality.string
              
        ATTENTION: No dimension scales are attached to the data set
        
Pandas data structures (pd) TODO WORK IN PROGRESS

pd.Series:

pd.DataFrame
        
numpy array:
        ND data set; attrs include only the generic data attributs ('metadata')
        
        ATTENTION: No dimension scales are attached to the data set
        
numpy chararray, string, numpy array with dtype.kind 'S' or 'U':
    stored as datasets with dtype h5py.string_dtype() array (variable length strings)

numpy structured arrays and recarrays: ATTENTION: NOT YET SUPPORTED
        
homogeneous lists of fundamental numeric python data types (numbers.Number,
    bytes)
        1D data set
        
        ATTENTION: No dimension scales are attached to the data set
        
homogeneous nested lists (that can be converted to plain ND numpy arrays)
        ND data set
        
        ATTENTION: No dimension scales are attached to the data set


        ATTENTION: No dimension scales are attached to the data set
        
basic Python scalars (numbers.Number, bytes, str) -> 1D data set

NOTE: python strings can be stored directly as values to dataset attr keys!

================================================================================
(1) neo.core.basesignal.BaseSignal type of objects; these include:
    neo's signals types:    neo.AnalogSignal, neo.IrregularlySampledSignal
    Scipyen's signal types: DataSignal, IrregularlySampledDataSignal
    
(2): neo.AnalogSignal, DataSignal
    
(3) h5py.Empty("f") except for irregular signals and neo DataObject types that 
    are NOT BaseSignal types: neo.Epoch, DataZone

(4) This is the value of units.dimensionality.string where units is the domain's
'units' property (a pq.Quantity object)

(5) "Time" for neo signals or the signal's 'domain_name' property

(6) in addition to the signal empty set; ONLY for multi-channel signals

(7) These are irregularly sampled signals (neo.IrregularlySampledSignal and 
    Scipyen's IrregularlySampledDataSignal) that inherit from neo's BaseSignal
   
(8) neo.Event, DataMark, neo.Epoch, DataZone

=> 'signal data sets' are 2D data sets 
        with len(dims) == 2:
        dims[0]: the domain axis;
            the dimension scale is constructed from an empty data set
    
    => 1D or 2D data sets, with
    dims[0] = the domain axis (see above)
    dims[1] = the "channels" axis;
        
    
STORING PYTHON CONTAINER OBJECTS IN HDF5 OBJECT HIERARCHY
================================================================================
Inhomogeneous sequences/iterables (list, tuple, deque):

    stored as a group with attrs populated from the object metadata 
    
    for each element, create a nested subgroup named after the index of the 
    element in the sequence
    
        this subgroup will contain either:
            a dataset (if the element is a data object type as in the table 
            above, or a plain basic Python type such as number, bytes or str)
            
            a group (if the element is a inhomogeneous sequence or mapping)

    
Mappings (dict and all dict-like flavours except for DataBag): 
    stored as a group with attrs populated from the object metadata 
    
    for each key/value pair:
        create a nested subgroup named appropriately (see below); the subgroup's
        'attrs' property contains metadata indicating the type of the key (str,
        int, or any hashable object) and a way to construct it.
        
        the nested subgroup contains a dataset or a subgroup according to the
        type of object mapped to the key (the 'value')
        
Specific Scipyen types (should) define their own toHDF5 and fromHDF5 methods 
using function calls in this module.

TriggerProtocol
ModelExpression
FitModel
ScanData
        

================================================================================
    
"""


    
    #NOTE: 2021-10-12 09:29:38

    #==============
    #Design notes:
    #==============

    #An object is the HDF5 File root (/)
    
    #Instance attributes & properties (but NEITHER methods, NOR :class: attributes)
    #correspond to the following HDF5 structures:
    
    #Python types:               HDF5 Structure:          Attribute:
    #============================================================================
    #bool and numeric scalars    dataset                 "type": type's name
    #sequences (list, tuple)     
    #str                         
    
    
    #Possible strategies: 
    #A) embed a VigraArray as HDF5 in a nix.File accessed via
    #neo.NixIO:
    
    #1) create a neo.NixIO file -> a physical file in the file system
    #2) access the nix_file inside the neo_nixio file object
    #3) access the _h5file of the nix_file
    #4) create a group inside the _h5file using h5py API:
    
    #4.1) this is a HDF5 Group, NOT a nix H5Group!
    
    #4.2) we can create it using the strategy in nix i.e., via low-level h5py api
        #e.g. h5g.create() a groupid, to enable group creation with order tracked
        #and order indexed flags - see h5p api - followed by instatiation of the
        #h5py.Group(groupid)
        
    #5) use the newly-created group as a fileNameOrGroup parameter to vigra.writeHDF5()
    
    #CAUTION: a nix.File cannot be used as context manager (i.e. one cannot
    #use the idiom with nix.File(...) as nixfile: ...)
    #But the neo.NixIO can be used as context manager:
    #with neo.NixIO(...) as neo_nixio_file: ...
        #(the underlying HDF5 file object is open in the neo.NixIO c'tor)
    
    #see history_snipper_scandata_vigra_export_hdf5.py

# NOTE: 2021-10-15 10:43:03
# 
# Low-level h5py API:
# modules:
#   h5      -> configuration
#   h5a     -> attribute
#   h5ac    -> cache configuration
#   h5d     -> dataset
#   h5ds    -> dimension scale
#   h5f     -> file
#   h5fd    -> file driver
#   h5g     -> group
#   h5i     -> identifier
#   h5l     -> linkproxy
#   h5o     -> H5O (object)
#   h5p     -> property list
#   h5pl    -> plugins
#   h5r     -> object and region references
#   h5s     -> data space
#   h5t     -> data type
#   h5z     -> filter
#   
# vigra.impex supports read/write from/to a group, as well as a hdf5 file !
#   operates DIRECTLY at the h5py API level - GOOD!
#
# neo.NixIO -> operates on actual file system files only (unlike h5py where a file 
# is also a group!)
#
#   it is a layer upon nixpy ('nix' module) which is a layer over h5py
# 
#   IMHO, that is BAD
#
# =============================================================================
# neo.NixIO:
# =============================================================================
#
# init expects a file system file name
#
#   initializes a nix.File (see below) as the 'nix_file' attribute
#
#
# =============================================================================
# nixpy (nix) File object
# =============================================================================
# uses h5py low-level API to generate groups
#
# init, broadly, requires a physical file (checked with os.path.exists(...))
#   this is used to create a h5py.File - which also behaves like a group - assigned
#   to the nix.File attribute _h5file:
#
#       _h5file: is a h5py File object
#           is private, there is no guarantee it won't change in the future
#
#   1) create h5py file ID; the file ID is generating by either
#       create or open (depending on whether the physcial file exists or not)
#
#   1.a) If physical file does no exist yet => create:
#       create a file ID object: fid = h5py.h5f.create(path, flags=h5mode, ...)
#       
#       fapl is always h5py.h5p.FILE_ACCESS
#       fcpl is a h5py.h5p.PropFCID (file creation property list)
#           with set_link_creation_order (h5py.h5p.CRT_ORDER_TRACKED | h5py.h5p.CRT_ORDER_INDEXED)
#
#   1.b) If physical file DOES exist: => open:
#       create file ID object: h5py.h5f.open(path)
#       use fapl as above
#
#   2) create _h5file: h5py.File(fid)
#
#   3) wrap the _h5file root ('/') group into a nix.H5Group object
#       'H5Group(parent, name, create=False)' -> when create is True or name 
#               exists in parent  this simply assigns the HDF5 group to the 
#               'group' attribute of the H5Group object
#
#       if file existing:
#           _root = H5Group(_h5file, '/') 
#       else:
#           _root = H5Group(_h5file, '/', create=True)
#
#       in either case above, the h5py.File's '/' group will be assigned to the
#       'group' attribute of _root
#
#       'create' trigger the creation of a HDF5 Group through a scheme similar to
#       that used for _h5file: create group ID then create h5py Group:
#           gpcl = group create property list with link creation order set to 
#           (h5py.h5p.CRT_ORDER_TRACKED | h5py.h5p.CRT_ORDER_INDEXED)
#
#           gid = h5py.h5g.create(parent's id, name, gpcl)
#           group = h5py.Group(gid)
#           
#
#       in either case, alias _root to _h5group
#
#   4) Also create two more groups - children of _root: _data and _metadata
#   4.1) uses _root.create_group -> generates nix.H5Group ad a child, AFTER it
#       ensures that _root is assigned to the 'group' attribute of the H5Group
#       (more generally, parent.create_group ensures this)
#
#   5) Adorn h5py File _directly_ with attributes (_h5file.attrs):
#       "created_at", "updated_at"
#
#        These are nix.util.time_to_str(nix.util.now_int())
#
#   6) set compression attribute (of the nix.File object)
#
#   7) Finally, set _blocks and _sections attrbutes of the nix.File object
#       uninitialized
#
#   nix.File.blocks: is a nix.Container: wraps a h5py Group used as a container 
#   for other groups
#
# --------------------------------------------
#  neo.NixIO taps into _blocks and _sections
# --------------------------------------------
#
# NixIO.write_block:
#   convert neo Block to NIX Block then write to NIX file
#
#   looks for a NIX block with same nix_name, in nix_file.blocks
#       if found then clean out previous nix_name block
#           delete nix_file.block[nix_name]
#           delete nix_file.sections[nix_name]
#
#       nixblock = nix_file.create_block(...)
#       nixblock is a nix Block, inherits from nix.Entity




import os, sys, tempfile, traceback, warnings
import types, typing, inspect, functools, itertools
from functools import singledispatch
from pprint import (pprint, pformat)
import collections, collections.abc
from collections import (deque, namedtuple)
from uuid import uuid4
import json, pickle
import h5py
import numpy as np
import nixio as nix 
import vigra
import pandas as pd
import quantities as pq
import neo
from neo.core.dataobject import ArrayDict

from . import jsonio # brings the CustomEncoder type and the decode_hook function
import core
from core.prog import (safeWrapper, classify_signature,)
from core import prog
from core.traitcontainers import DataBag
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datazone import DataZone
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType)
from core.triggerprotocols import TriggerProtocol

from core.quantities import(arbitrary_unit, 
                            pixel_unit, 
                            channel_unit,
                            space_frequency_unit,
                            angle_frequency_unit,
                            day_in_vitro,
                            week_in_vitro, postnatal_day, postnatal_month,
                            embryonic_day, embryonic_week, embryonic_month,
                            unit_quantity_from_name_or_symbol,
                            name_from_unit, units_convertible)

from core.datatypes import (TypeEnum,UnitTypes, Genotypes, 
                            is_uniform_sequence, is_namedtuple, is_string,
                            is_numeric_string, is_numeric, NUMPY_STRING_KINDS,
                            )

from core.modelfitting import (FitModel, ModelExpression,)
from core.triggerevent import (TriggerEvent, TriggerEventType,)
from core.triggerprotocols import TriggerProtocol
from core.utilities import unique
from core.strutils import (str2symbol, str2float, numbers2str, get_int_sfx,)
from core import modelfitting
import imaging
from imaging.axiscalibration import (AxesCalibration, 
                                     AxisCalibrationData, 
                                     ChannelCalibrationData)

from imaging.indicator import IndicatorCalibration # do not confuse with ChannelCalibrationData
from imaging.scandata import (AnalysisUnit, ScanData, ScanDataOptions,)
from imaging import vigrautils as vu
from gui.pictgui import (Arc, ArcMove, CrosshairCursor, Cubic, Ellipse, 
                         HorizontalCursor, Line, Move, Quad, Path, 
                         PlanarGraphics, Rect, Text, VerticalCursor,)

# NOTE: 2021-10-18 12:08:18 in all functions below:
# FIXME: 2021-11-07 16:50:14
# fileNameOrGroup is either:
#   a str, the file name of a target HDF5 file (possible, relative to cwd)
#
#       In this case, the functions will work on the root group ('/') of the 
#       HDF5 filename.
#
#   a h5py.Group object
#
# pathInFile is a str: the name of the h5py.Dataset.
#
#   This can be a HDF5 'path' (from the root '/' to, and including, the data set
#       name) or just the data set name (in which case the data set will be
#       relative to the fileNameOrGroup)
#   
#   for reading functions, the named data set must already exist in the group
#   (for data sets deeply nested, the intermediary groups must also be present)
#   

class HDFDataError(Exception):
    pass

def print_hdf(v):
    return v if isinstance(v, str) else v.decode() if isinstance(v, bytes) else v[()]

def h5py_dataset_iterator(g:h5py.Group, prefix:str=''):
    """HDF5 Group traverser.
    
    See Answer 1 in 
    https://stackoverflow.com/questions/50117513/can-you-view-hdf5-files-in-pycharm
    
    Moved outside of exploreHDF ("traverse_datasets") to be widely accessible
    
    Parameters:
    ===========
    g:h5py.Group (this can also be a h5py.File).
        It is the responsibility of the caller to manage `g` (e.g. close it, if
        it is a File object).
        
    prefix:str, optional default is ""; name of the parent
    
    """
    for key in g.keys():
        item = g[key]
        path = '{}/{}'.format(prefix, key)
        if isinstance(item, h5py.Dataset): # test for dataset
            #yield (path, item)
            yield (path, item, item.attrs)
        elif isinstance(item, h5py.Group): # test for group (go down)
            print(f"Group '{item.name}' attributes:")
            for k,v in item.attrs.items():
                print(f"\t{k}: {print_hdf(v)}")
            #pprint(dict(item.attrs))
            yield from h5py_dataset_iterator(item, path)
            
def exploreHDF(hdf_file:typing.Union[str, h5py.Group]):
    """Traverse all datasets across all groups in HDF5 file.

    See Answer 1 in 
    https://stackoverflow.com/questions/50117513/can-you-view-hdf5-files-in-pycharm
    
    exploreHDF('file.h5')

    /DataSet1 <HDF5 dataset "DataSet1": shape (655559, 260), type "<f4">
    /DataSet2 <HDF5 dataset "DataSet2": shape (22076, 10000), type "<f4">
    /index <HDF5 dataset "index": shape (677635,), type "|V384">
    
    """

    #import h5py # already imported at the top
    
    
    def __print_iter__(path, dset, attrs):
        print(path, f"Dataset '{dset.name}':", dset)
        print("with attributes:")
        for k,v in attrs.items():
            print(f"\t{k}: {print_hdf(v)}")
        #pprint(dict(attrs))
        print("\n")
        if len(dset.dims):
            print("with dimension scales:")
            for kd, dim in enumerate(dset.dims):
                print(f"\tdimension {kd}:")
                for k,v in dim.items():
                    print(f"\t\t{k}: {print_hdf(v)}, (type: {type(v)}, dtype: {v.dtype.kind})")
                #pprint(dim)
            print("\n")

    if isinstance(hdf_file, str):
        if os.path.isfile(hdf_file):
            with h5py.File(hdf_file, 'r') as f:
                for (path, dset, attrs) in h5py_dataset_iterator(f):
                    __print_iter__(path, dset, attrs)
                #for (path, dset) in h5py_dataset_iterator(f):
                    #print(path, dset)
                    
    elif isinstance(hdf_file, h5py.Group):
        # file created/opened outside this function; 
        # the caller should manage/close it as they see fit
        for (path, dset, attrs) in h5py_dataset_iterator(hdf_file):
            __print_iter__(path, dset, attrs)
        #for (path, dset) in h5py_dataset_iterator(f):
            #print(path, dset)

    #return None

def string2hdf(s):
    if not isinstance(s, str):
        raise TypeError(f"Expecting a str; got {type(s).__name__} instead")
    
    return np.array(s, dtype=h5py.string_dtype())

def make_attr(x:typing.Union[str, list, tuple, dict, deque, np.ndarray]):
    """Returns a representation of 'x' as atttribute of a Group or Dataset
    
    Parameters:
    -----------
    'x': basic Python type (str or scalar number), or numpy array
    
    Returns:
    --------
    A string when 'x' is a str, or is a container with elements that can be
        written to a JSON-formatted string.
        
        As a rule of thumb, these objects should be relatively small, and the 
        container should be relatively simple.
    
    A numpy array with dtype j5py.string_dtype() when 'x' is a numpy array with
    dtype.kind of 'S' or 'U' (i.e., strings)
    
    'x' itself in any other case.
    
    CAUTION h5py will raise exception when 'x' is of a type that h5py cannot 
    store as attrs value to a Group or Dataset.
    
    """
    if isinstance(x, str):
        return string2hdf(x)
    
    if isinstance(x, (list, tuple, dict)): 
        # will raise exception if elements or values are not json-able
        # CAUTION Do not use large data objects here!
        # We use the CustomEncoder which has wider coverage and its own 
        # limitations/caveats
        # 
        try:
            return jsonio.dumps(x)
        except:
            raise HDFDataError(f"The object {x}\n with type {type(x).__name__} cannot be serialized in json")
    
    if isinstance(x, np.ndarray):
        #print("dtype", x.dtype, "kind", x.dtype.kind)
        if x.dtype.kind in NUMPY_STRING_KINDS:
            return np.asarray(x, dtype=h5py.string_dtype(), order="K")
        
        else:
            # NOTE: for UnitQuantities stores dimensionality string
            #
            return jsonio.dumps(x) 
    
    return x

def make_attr_dict(**kwargs):
    """Generates a dict with contents to be stored in a Group or Dataset 'attrs'.
    
    The returned dict object maps keys (str) to values that can be stored as
    attrs values into a h5py Group or Dataset.
    
    To store the dict, simply call:
    
        `obj.attrs.update(x)`
        
        , where:
    
            'obj' is a h5py Group or Dataset
            'x' is the dict object returned by this function.
    
    """
    ret = dict()
    
    for k,v in kwargs.items():
        ret[k] = make_attr(v)
        
    return ret

def from_attr_dict(attrs):
    """Generates a dict object from a h5py Group or Dataset 'attrs' property.
    Not exactly a complete roundtrip...
    """
    ret = dict()
    for k,v in attrs.items():
        # NOTE: 2021-11-10 12:47:52
        # FIXME / TODO
        if hasattr(v, "dtype"):
            if v.dtype == h5py.string_dtype():
                v = np.array(v, dtype=np.dtype("U"))[()]
                
            elif v.dtype.kind == "O":
                if type(v[()]) == bytes:
                    v = v[()].decode()
                    
                else:
                    v = v[()]
                    
            else:
                v = v[()]
                
            if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
                v = jsonio.loads(v)
                
        elif isinstance(v, str):
            if v.startswith("{") and v.endswith("}"):
                v = jsonio.loads(v)
                
        ret[k] = v
        
    return ret
                
#@singledispatch
def generic_data_attrs(data, prefix=""):
    if not isinstance(data, type):
        data_type = type(data)
        
    else:
        data_type = data

    if isinstance(prefix, str) and len(prefix.strip()):
        if not prefix.endswith("_"):
            prefix += "_"
        
    else:
        prefix = ""
        
    attrs = dict()
    
    attrs[f"{prefix}type_name"] = data.__name__
    attrs[f"{prefix}module_name"] = data.__module__
    attrs[f"{prefix}python_class"] = ".".join([data.__module__, data.__name__])
    
    if is_namedtuple(data_type):
        fields_list = list(f for f in data_type._fields)
        attrs[f"{prefix}python_class_def"] = f"{data_type.__name__} = collections.namedtuple({data.__name__}, {list(fields_list)})"
    else:
        attrs[f"{prefix}python_class_def"] = prog.class_def(data_type)
        
    if hasattr(data_type, "__new__"):
        sig_dict = classify_signature(getattr(data_type, "__new__"))
        
        new_func_name = ".".join([sig_dict["module"], sig_dict["qualname"]])
        
        positional = list(sig_dict["positional"])
        
        named = list(sig_dict)
        
        
        attrs[f"{prefix}python_new"] = new_cmd
        
        
    return attrs
    attrs = dict()
    
    if isinstance(prefix, str) and len(prefix.strip()):
        if not prefix.endswith("_"):
            prefix += "_"
        
    else:
        prefix = ""
        
    attrs = generic_data_attrs(type(data), prefix=prefix)
        
    if inspect.isfunction(data):
        attrs[f"{prefix}func_name"] = data.__name__            
    
    return attrs

#@generic_data_attrs.register(types.FunctionType)
#def _(obj, prefix:str="") -> dict:
    #if isinstance(prefix, str) and len(prefix.strip()):
        #if not prefix.endswith("_"):
            #prefix += "_"
        
    #else:
        #prefix = ""
        
    #return {f"{prefix}func_name": data.__name__}
    
    
def get_file_group_child(fileNameOrGroup:typing.Union[str, h5py.Group],
                       pathInFile:typing.Optional[str] = None, 
                       mode:typing.Optional[str]=None) -> typing.Tuple[typing.Optional[h5py.File], h5py.Group, typing.Optional[str]]:
    """Common tool for coherent syntax of h5io read/write functions.
    Inspired from vigra.impex.readHDF5/writeHDF5, (c) U.Koethe
    """
    if mode is None or not isinstance(mode, str) or len(mode.strip()) == 0:
        mode = "r"
        
    external = False
    print("get_file_group_child fileNameOrGroup", fileNameOrGroup, "pathInFile", pathInFile, "mode", mode)
    
    if isinstance(fileNameOrGroup, str):
        file = h5py.File(fileNameOrGroup, mode=mode)
        group = file['/']
        
    elif isinstance(fileNameOrGroup, h5py.File):
        file = fileNameOrGroup
        if file:
            external = True
        group = file['/']
        
    elif isinstance(fileNameOrGroup, h5py.Group):
        file = None
        group = fileNameOrGroup
    else:
        raise TypeError(f"Expecting a str, h5py File or h5py Group; got {type(fileNameOrGroup).__name__} instead")
    
    childname = None
        
    if isinstance(pathInFile, str) and len(pathInFile.strip()):
        levels = pathInFile.split('/')
        
        for groupname in levels[:-1]:
            if len(groupname.strip()) == 0:
                continue
            
            g = group.get(groupname, default=None)
            
            if g is None:
                group = group.create_group(groupname, track_order=True)
                
            elif not isinstance(g, h5py.Group):
                raise IOError(f"Invalid path: {pathInFile}")
            
            else:
                group = g
        
        childname = levels[-1]
        
    if not isinstance(childname, str) or len(childname.strip()) == 0:
        childname = group.name

    return file, group, childname, external

    
def parse_func(f):
    sig = inspect.signature(f)
    
    def __identify__(x):
        if x is None:
            return str(x)
        
        elif isinstance(x, type):
            return x.__name__
        
        else:
            return {"type": type(x).__name__, "value": x}
        
    
    return dict((p_name, {"kind":p.kind.name, 
                          "default": __identify__(p.default),
                          "annotation": __identify__(p.annotation),
                          }) for p_name, p in sig.parameters.items())

def hdf_entry(x:typing.Any, attr_prefix="key"):#, parent:h5py.Group):
    attrs = make_attr_dict(**generic_data_attrs(x, attr_prefix))
    
    if not isinstance(x, str):
        name = f"{type(x).__module__}.{type(x).__name__}_{uuid4().hex}"
        #name = json.dumps(x)
    else:
        name = x
    
    return type(x), name, attrs

@singledispatch
def make_dataset_attrs(obj):
    """Generates an attribute dict for HDF5 datasets.
    The result is passed through make_attr_dict before mergins into a HDF5 
    Dataset attrs property.
    
    This is used for the actual numeric data of the object, NOT for its axes.
    
    ============================================================================
    Mandatory key/value pairs 
    
    Key name        Object type                     type: value
    ============================================================================
    name            DataObject                      str: obj.name
    units           DataObject                      str (JSON): obj.units
    file_origin                                     str: obj.file_origin
    description                                     str: obj.description
    
    segment                                         None or h5py reference to 
                                                    segment data set
    <field_name>                                    as in the obj.annotations
                                                    dictionary
    
    ============================================================================
    
    ============================================================================
    Optional key/value pairs 
    
    Key name        Object type                     type: value
    ============================================================================
    unit            SpikeTrain                      ???? Unit is out of neo hierarchy
    ============================================================================
    """
    

@make_dataset_attrs.register(neo.core.dataobject.DataObject)
def _(obj):
    ret = {"name": obj.name,
           "units":obj.units,
           "segment": "__ref__" if obj.segment else None
           }
    if isinstance(obj, (neo.core.basesignal.BaseSignal)):
        ret.update(
                    {"file_origin": obj.file_origin,
                     "description": obj.description,
                    }
                    )
    if isinstance(obj, neo.SpikeTrain):
        ret["unit"] = obj.unit
    
    ret.update(obj.annotations)
    
    return make_attr_dict(**ret)
    
    
@singledispatch
def make_axis_dict(obj, axisindex:int):
    """Returns a dict with axis information for storage in HDF5 hierarchy.
    
    Used to build dimension scales for a signal dataset and where necessary,
    additional datasets with data array associated with the axis.
    
    The dimension scale for a signal dataset axis (or dimension) is constructed
    from an axis dataset (h5py.Dataset) stored in an axes group alongside the
    object's data set (i.e. in the same parent group as the object's data set).
    
    Semantic interpretation of the array axes:
    ------------------------------------------
    * Axes for neo and neo-like objects
    
    Signals in neo package have up to two axes (except for ImageSequence and
    SpikeTrain.waveforms property, which have up to three axes):
    
    axis 0 is the domain axis:
        for objects in the neo package the domain is always time; 
        
        for Scipyen's own neo-like objects (DataSignal, IrregularlySampledDataSignal,
        DataMark, DataZone) this domain can by anything that makes sense semantically,
        for the signal (time, space, etc.).
        
        for SpikeTrain.waveforms data, this axis is the spike index axis
        
        for ImageSequence objects, this is the "frame index" axis
    
    axis 1: 
        for "proper" signals - that inherit from neo's Basesignal type - this 
            is the "channels" axis and always exists (signals are 2D arrays) 
            even if the signal has only  one channel; 
            
            the channel information is typically stored in the 'array_annotations' 
            property of the signal which, when present, contains fields (str) 
            mapped to 1D numpy arrays of scalar dtypes (numbers or str) with as 
            many elements as the number of channels in the signal.
            
        
        for ImageSequence objects this is a spatial axis (vertical direction)
        
        for SpikeTrain.waveforms data, 
            when the waveform data is a 3D array, this axis is the "channel" axis 
            (in the sense of recording channel)
            
            when the waveform data is a 2D array, this axis is the "signal" axis
            (in units of the signal, typically, electrical potential units)
        
        NOTE: absent in SpikeTrain, Event, Epoch, DataMark and DataZone objects 
            because they are 1D arrays (of times or places, etc.).
        
    axis 2: present in ImageSequence and optionally in SpikeTrain.waveforms data
        
        for ImageSequence objects this is a spatial axis (orthogonal to axis 1, 
            i.e. in the horizontal direction)
        
        for SpikeTrain.waveforms as 3D arrays, it is the "signal" axis itself
            (see above)
        
        NOTE: absent in SpikeTrain, Event, Epoch, DataMark and DataZone objects 
            because they are 1D arrays (of times or places, etc.).
        
    * VigraArrays benefit from the vigra's framework of objects that make
        understanding the semantics of the array axes very easy.
        
        Each axis brings its own vigra.AxisInfo objects which encapsulate the 
        axis' semantics. the AxisInfo objects are stored in the VigraArray
        'axistags' property.
        
        Except for a Channels axis, all other axes represent a domain (time, 
        space, angle, edge, frequency) such that the data array is defined on a
        combination of domains indicated by their corresponding axes.
        
        For example:
        space, or time, or frequency, etc   -> 1D signal (e.g, a single line scan or a point scan over time)
        space x space                       -> image 
        time x space                        -> time sequence of signals along space (e.g time series of line scans)
        space x space x space               -> volume 
        space x space x time                -> time sequence of images
        space x space x space x time        -> time sequence of volumes
        space frequency x space frequency   >  forward Fourier transform of an image

        ... and so on ...
        
        The Channels axis may be absent in single-channel data (is a "virtual" axis).
        
        When present, the Channels axis is usually (or should be) on the highest 
        dimension of the array  - although this is not strictly enforced. This
        axis carries the information of the physical measure encoded in the 
        data's 'pixels'.
        
        The semantic of each axis in a VigraArray is represented by the associated
        vigra.AxisInfo objects, stored in the array's axis tags.
        
        The axes datasets for Vigra arrays are always empty. The information
        associated with each axis is retrieved from the corresponding 
        vigra.AxisInfo object contained in the array's 'axistags' property, 
        using a Scipyen AxisCalibrationData object as intermediary.
        
        For a Channels axis, the AxisCalibrationData also contains information
        for each of the channels in the image, when available.
        
    Contents of the axis dataset:
    ------------------------------
    With the exceptions described below, the axis dataset is an empty HDF5 
    dataset (h5py.Empty("f")) where the 'attrs' property stores axis information 
    of numeric scalar or string types, as key/value pairs.
        
    * Domain axis exceptions:
        
    1) For irregularly sampled signals, the axis data set for the signal's domain
    (e.g. time or space) contains the actual time, or more generally, the domain,
    values when (or where) each of the signal samples were recorded. 
    
    2) neo.Epoch, and Scipyen's own DataZone objects are array-like neo data 
    objects, not to be treated as signals.
    
    Their main dataset already contains time (or domain) values where the epochs 
    (or data zones) start. 
    
    The domain axis data sets contains additional domain values, namely, the 
    'durations' of the epochs or the 'extents' of the data zones (for compatibility,
    both objects store this information in their 'durations' property).
    
    Additional HDF5 data sets:
    --------------------------
    1) 'waveforms' data set for neo.SpikeTrain objects.
    
    neo.SpikeTrain objects associate a 2D or 3D numeric numpy array with the 
    spike waveforms, with axes: [spike, channel, time]
    
    This array is stored as a 'waveforms' dataset in the same
    group as the axis datasets of the spike train.
    
    NOTE: that a SpikeTrain itself is an array of time values, possibly with
    multiple channels (as column vectors), all belonging to the same 'unit' or 
    'cell' (the channels are recording channels). A neo.Segment can store
    several spike trains in its 'spiketrains' property which is a 
    neo.spiketrainlisyt.SpikeTrainList object; each spike train there comes from
    a different 'unit' or 'cell'.
    
    Therefore the axis dataset for axis 0 (domain) of a SpikeTrain is empty; its
    'attrs' property is expected to store the units information (time units).
    
    However, the waveforms dataset has its own dimension scales as follows:
    
    axis 0: spikes axis
    axis 1: channel (3D waveforms array) or time (2D waveforms array)
    axis 2: times (domain) only for 3D waveforms array)
    
    
    2) 'labels' data set for Epoch, Event, DataMark and DataZone objects
    
    This sata set stores the 'labels' property of these objects.
    
    neo.Event, neo.Epoch, and Scipyen's own DataMark and DataZone objects are 
    array-like neo objects where the main data is the domain itself (time, space,
    etc) and the values (e.g. "time stamps") stored in the main HDF5 data set.
    
    In this respect, they are similar to the SpikeTrain objects.
    
    Each event, epoch, data mark or data zone associates a str label, stored in 
    the 'labels' property - this is a 1D array of strings, with as many elements
    as the number of events/epochs/marks/zones in the object.
    
    In most cases the axis dataset is an Empty dataset (h5py.Empty("f")).
    
    Exceptions are irregularly sampled signal types and the DataObject types 
    Epoch and DataZone where the axis datasets contains:
    
    * the 'times' property of irregularly sampled signals
    
    * the 'durations' property of Epoch and DataZone
    
    3) 'channels' data sets: for each channel calibration in a VigraArray
    Channels axis, and additional empty HDF5 data set is created in the axes
    group, ONLY if channel calibration is provided in the Channels axis
    axistag (i.e. "virtual"channel axes atre skipped)
    
    
    As mentioned above, additional HDF5 data sets are created in the same 
    axes group (h5py.Group object) as the axes data sets.
    
    Contents of the axis attrs dictionary:
    --------------------------------------
    NOTE 1: Below, 
    neo.BaseSignal objects are:
        neo.AnalogSignal, neo.IrregularlySampledSignal, neo.ImageSequence
        core.datasignal.DataSignal, 
        core.datasignal.IrregularlySampledDataSignal
        
    neo.DataObject objects are: BaseSignal objects AND:
        neo.Epoch, neo.Event, neo.SpikeTrain
        core.triggerevent.DataMark, 
        core.datazone.DataZone
        
    For space reasons the modules there they are defined are omitted
    from the type name.
    
    NOTE 2: 'waveforms' are python Quantity arrays
    
    ============================================================================
    Mandatory key/value pairs 
    
    Key name        Object type                     type: value
                                                    semantics
                                                    specific storage
    ============================================================================
    key             VigraArray                      str:                     
                                                    AxisInfo.key             
    
                    BaseSignal                      str: <1 or 2 chars>, 
                                                    domain type name (axis 0)
                                                    physical measure name (axis 1)
                                                    applies heuristic in
                                                    core.quantities.name_from_unit
                                                
                    ImageSequence                   str:                     
                                                    "t" for axis 0           
                                                    "y" for axis 1         
                                                    "x" for axis 2         
                                                
    name            VigraArray                      str                      
    
                    ImageSequence                   str:                     
                                                    "frames" for axis 0       
                                                    "height" for axis 1         
                                                    "width"  for axis 2         
                                                
                    BaseSignal                      str:                     
                                                    domain name for axis 0   
                                                    signal name for axis 1         
                                                
    units           VigraArray                      str:                     
                                                    dimensionality of        
                                                    asociated physical     
                                                    measure     
                                                
                    BaseSignal                      str:                     
                                                    axis 0: domain units     
                                                    axis 1: signal units      
                                                
                    ImageSequence                   str:                     
                                                    axis 0: time units       
                                                    axs 1 & 2: space units     
                                                
    ============================================================================
    
    ============================================================================
    Optional key/value pairs (present only for the specific object types below):
    
    Key name        Object type                     type: value
                                                    semantics
                                                    specific storage
    ============================================================================
    axinfo_description     
                    VigraArray                      str:                        
                                                    AxisInfo.description 
                                                    
    axinfo_key      VigraArray                      str:
                                                    AxisInfo.key
                                                    
    axinfo_typeFlags
                    VigraArray                      int: 
                                                    AxisInfo.typeFlags
                                                    
    axinfo_resolution
                    VigraArray                      float, int
                                                    AxisInfo.resolution
                    
    
    origin          VigraArray                      float:                      
                                                    CalibrationData.origin      
                                                    (default 0.0)
    
                    AnalogSignal,                   float: signal.t_start
                    DataSignal,                     (only for axis 0)
                    ImageSequence,
                    SpikeTrain
                            
    domain          IrregularlySampledSignal,       1D ndarray float dtype:
                    IrregularlySampledDataSignal    this is signal.times
                                                    property 
                                                    stored AS the axis dataset;
                                                    only for axis 0
                                                    
                    Epoch                           1D ndarray, float dtype:
                    DataZone                        this is signal.durations
                                                    stored AS the axis dataset;
                                                    only for axis 0
                            
    labels          Event,                          1d ndarray dtype <U
                    DataMark                        signal.labels property
                    Epoch                           stored as axis_labels
                    DataZone                        dataset alongside the axis
                                                    dataset;
                                                    
                                                    
    waweforms       SpikeTrain                      2D or 3D ndarray float dtype:
                                                    'waveforms' property
                                                    stored as separate dataset
                                                    with its own dimension scales
    
    resolution      VigraArray                      float:
                                                    CalibrationData.resolution
                                                    (default: AxisInfo.resolution
                                                    or 1.0)
    
    sampling_rate   AnalogSignal,                   float: signal.sampling_rate
                    DataSignal,                     axis 0 only

                    ImageSequence                   float: data.sampling_rate
                                                    axis 0 only
                                                    
                    SpikeTrain                      float: sampling_rate of
                                                    the train's waveforms
                                                    stored as dimension scale
                                                    in that data set;
                                                    only when waveforms are 
                                                    present
                                                    NOTE: because waveforms are
                                                    just a pq.Quantity, this 
                                                    information is "grafted" to 
                                                    the waveforms' axis '
                                                    although it belongs to the 
                                                    SpikeTrain itself
                                                    
    sampling_period 
                    AnalogSignal,                   float: signal.sampling_period
                    DataSignal                      axis 0 only
                            
                    ImageSequence                   float: 
                                                    axis 0: data.frame_duration
                                                    axes 1  2: data.spatial_scale
                                                    NOTE: spatial_scale is not well
                                                    documented and appears to be
                                                    just a scalar float
                                                    
                            
    left_sweep      SpikeTrain                      float
                                                    axis 0 (domain) only
                                                    assumed to have the times'
                                                    units
                                                    
    end             SpikeTrain                      float: obj.t_stop
                                                    axis 0 (domain) only
                                                    assumed to have the times'
                                                    units
                                                    
                                                    
    <channel name
    string>         VigraArray                      dict (only for Channels axes)
                                                    this will be used to generate
                                                    channel_axis datasets
                                                    
    <field name     DataObject                      numpy array
     string>        EXCEPT                          only for axis 1 (channels)
                    ImageSequence                   and only if array_annotations
                                                    if present and conformant.
    ============================================================================
    
    NOTE 3: axis units are pq.Quantities (including pq.UnitQuantities) and 
    are stored in JSON format
    """
    raise NotImplementedError(f"{type(obj).__name__} objects are not yet supported")

@make_axis_dict.register(vigra.VigraArray)
def _(obj, axisindex:typing.Union[int, str]):
    from imaging import axisutils, axiscalibration
    from imaging.axiscalibration import (AxisCalibrationData, ChannelCalibrationData, AxesCalibration)
    if isinstance(axisindex, int):
        if axisindex < 0 or axisindex >= obj.ndim:
            raise ValueError(f"Invalid axisindex {axisindex}")
        
    elif isinstance(axisindex, str):
        if axisindex not in obj.axistags:
            raise ValueError(f"Invalid axisindex {axisindex}")
        
    else:
        raise TypeError(f"Invalid axisindex type; expecting a str or int, got {type(axisindex).__name__} instead.")
    
    axisinfo = obj.axistags[axisindex]
    
    axiscal = AxisCalibrationData(axisinfo)
    
    data = axiscal.data
    
    return make_attr_dict(axinfo_key = axisinfo.key,
                          axinfo_typeFlags = axisinfo.typeFlags,
                          axinfo_description = axisinfo.description, 
                          axinfo_resolution=axisinfo.resolution, 
                          **axiscal._data_)
    
@make_axis_dict.register(vigra.AxisTags)
def _(obj, axisindex:typing.Union[int, str]):
    from imaging import axisutils, axiscalibration
    from imaging.axiscalibration import (AxisCalibrationData, ChannelCalibrationData, AxesCalibration)
    if isinstance(axisindex, int):
        if axisindex < 0 or axisindex >= len(obj):
            raise ValueError(f"Invalid axisindex {axisindex}")
        
    elif isinstance(axisindex, str):
        if axisindex not in obj:
            raise ValueError(f"Invalid axisindex {axisindex}")
        
    else:
        raise TypeError(f"Invalid axisindex type; expecting a str or int, got {tytpe(axisindex).__name__} instead.")
    
    
    axisinfo = obj[axisindex]
    
    axiscal = AxisCalibrationData(axisinfo)
    
    return make_attr_dict(axinfo_key = axisinfo.key,
                          axinfo_typFlags = axisinfo.typeFlags,
                          axinfo_description = axisinfo.description, 
                          axinfo_resolution=axisinfo.resolution,
                          **axiscal.data)

@make_axis_dict.register(neo.core.dataobject.DataObject)
def _(obj, axisindex:int):
    # axis 0 = domain axis (e.g. times)
    # axis 1 = channel axis (may be singleton for a single-channel signal)
    if isinstance(axisindex, int):
        if axisindex < 0 or axisindex >= obj.ndim:
            raise ValueError(f"Invalid axisindex {axisindex} for {type(obj).__name__} object")
        
    else:
        raise TypeError(f"'axisindex' expected to be an int; got {type(axisindex).__name__} instead")
    
    seed = dict()
    seed["key"] = cq.name_from_unit(obj.times.units) if axisindex == 0 else cs.name_from_unit(obj.units)
    seed["name"] = seed["key"] if axisindex == 0 else getattr(obj, "name", type(obj).__name__)
    seed["units"] = obj.times.units if axisindex == 0 else obj.units
    
    if axisindex == 1: 
        # channels axis
        #  NOTE: 2021-11-17 13:41:04
        # array annotations SHOULD be empty for non-signals
        # ImageSequence does NOT have array_annotations member
        array_annotations = getattr(obj,"array_annotations", None)
        if isinstance(array_annotations, ArrayDict) and len(array_annotations): # this is the number of fields NOT channels!
            # NOTE: skip silently is length different for obj size on axis 1
            if array_annotations.length == obj.shape[1]:
                for field, value in array_annotations:
                    ret[field] = value
    
    if isinstance(obj, neo.core.basesignal.BaseSignal):
        ret = make_neo_signal_axis_dict(obj, axisindex)
    else:
        ret = make_neo_data_axis_dict(obj, axisindex)
    seed.update(ret)
    
    return make_attr_dict(**seed)
        
@singledispatch        
def make_neo_signal_axis_dict(obj, axisindex:int):
    """See make make_axis_dict for details
    """
    raise NotImplementedError(f"{type(obj).__name__} objects are not supported")

@make_neo_signal_axis_dict.register(neo.AnalogSignal)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        # domain axis
        ret["origin"] = obj.t_start
        ret["sampling_rate"] = obj.sampling_rate
        ret["sampling_period"] = obj.sampling_period

    return ret

@make_neo_signal_axis_dict.register(DataSignal)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        # domain axis
        ret["origin"] = obj.t_start
        ret["sampling_rate"] = obj.sampling_rate
        ret["sampling_period"] = obj.sampling_period

    return ret

@make_neo_signal_axis_dict.register(neo.IrregularlySampledSignal)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["domain"] = obj.times
        
    return ret

@make_neo_signal_axis_dict.register(IrregularlySampledDataSignal)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["domain"] = obj.times
        
    return ret

@make_neo_signal_axis_dict.register(neo.ImageSequence)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["key"] = "t"
        ret["name"] = "frames"
        ret["units"] = obj.t_start.units
        ret["origin"] = obj.t_start
        ret["sampling_rate"] = obj.sampling_rate
        
    else: # axis 1 or 2
        ret["key"] = "s"
        ret["name"] = "height" if axisindex == 1 else "width"
        ret["spatial_scale"] = obj.spatial_scale
        

@singledispatch
def make_neo_data_axis_dict(obj, axisindex):
    raise NotImplementedError(f"{type(obj).__name__} objects are not supported")
    
@make_neo_data_axis_dict.register(neo.SpikeTrain)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["origin"] = obj.t_start
        ret["left_sweep"] = obj.left_sweep
        ret["waveforms"] = obj.waveforms
        ret["end"] = obj.t_stop
        if obj.waveforms.size > 0:
            ret["sampling_rate"] = obj.sampling_rate
        
    return ret

@make_neo_data_axis_dict.register(neo.Event)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["labels"] = obj.labels
    return ret

@make_neo_data_axis_dict.register(DataMark)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["labels"] = obj.labels
    return ret

@make_neo_data_axis_dict.register(neo.Epoch)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["labels"] = obj.labels
        ret["durations"] = obj.durations
    return ret

@make_neo_data_axis_dict.register(DataZone)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["labels"] = obj.labels
        ret["durations"] = obj.durations
    return ret


        
def make_axis_scale(dset:h5py.Dataset, 
                    axesgroup:h5py.Group,
                    dimindex:int, 
                    axdict: dict,
                    axis_name:str, 
                    domain_name:str,
                    units: pq.Quantity,
                    array_annotations:typing.Optional[ArrayDict]=None,
                    axis_array:typing.Optional[np.ndarray] = None,
                    **kwargs
                    ):
    """
    Creates an axis dataset used to generate dimension scales for the dimension
    speficied in dimindex
    
    Parameters:
    -----------
    
    dset: h5py.Dataset - the target dataset
    
    axesgroup: h5py.Group - target group where addtional axis-related datasets
        will be written, when necessary
    
    dimindex: int; index of the dset's dimension scale: 
        0 <= dimindex < len(dset.dims)
        
    axisdict: a dictionary with key:str mapped to values: objects usable as
        attributes for the axis data set (see make_attr_dict and make_attr)
        
        The keys depend on the type of the Python object written to the target
        data set and are detailed in the documentation of this module.
        
        However, the following keys/value type pairings are mandatory:
        'axis_name': str
        'axis_title': str
        'units': str string representation of axis units
        
        See also make_axis_dict
    
    domain_name:str name of the axis domain, e.g. "Time", "Potential", "Current",
        etc.
        
    axis_name:str axis name - the name of the axis 
        for 1D signals this is typically the domain name (see 'domain_name') but
        for 2D signals where both axes are in the same domain (e.g. an image)
        this further qualifies the axis (e.g., 'width', 'height')
        
    units: pq.Quantity - this is EITHER:
        the units associated with the data in 'dset', when the axis is the
            'signal axis', OR:
            
        the units of the definition domain of the data in 'dset', when the 
        axis if the domain axis of the data in 'dset'.
        
        
    origin: scalar pq.Quantity; optional, default is None
        This is the value of the signal's 't_start' property, for regularly
        sampled signals neo.AnalogSignal, DataSignal, and neo.ImageSequence
        
    sampling_rate, sampling_period: scalar pq.Quantity 
        only one should be given, as appropriate for the signal
        
        Some signals offers both. Note that in some cases one of them is a 
        stored value, and the other is calculated (dynamic property).
    
    array_annotations: neo.core.dataobject.ArrayDict or None
    
        In most cases this is None. When an ArrayDict, it will be used to 
        populate the attributes of the data set used as axis dimension scale
        
        This is typically useful to provide channel information for axes 
        in the signal domain.
        
        If passed as an ArrayDict, a channel group named "channels" will be
        created in the specific axesgroup, to store the channel information
        used to create dimension scales for the axis
        
    axis_array: numpy array or None
    
    **kwargs: name/value pairs where name: obj attribute name (property) and
        value is a pq.Quantity
        
        The keys are names of properties available for the signal object, e.g.
        such as 't_start', 'sampling_rate', etc.
        
        NOTE: All Quantities must have units compatible with the axis's units
        
    """
    
    # create an empty data set, store in its 'attrs' property
    # NOTE: irregular signals and array-like data objects Epoch & Zone also
    # provide a 'parallel' set of data  - the 'durations' property - we store 
    # that separately as a dimension scale labeled 'durations' attached to
    # this data set (see NOTE: 2021-11-12 16:05:29 and NOTE: 2021-11-12 17:35:27
    # in self.writeDataObject) 
    
    if isinstance(axis_array, np.ndarray):
        axis_dset = axesgroup.create_dataset(f"{axis_name}_values", data = axis_array)
        
    else:
        axis_dset = axesgroup.create_dataset(axis_name, data = h5py.Empty("f"))
        
    axis_dset.attrs["name"] = axis_name
    # these are either signal units, or domain units
    axis_dset.attrs["units"] = units.dimensionality.string 
    
    if isinstance(array_annotations, ArrayDict) and len (array_annotations):
        # CAUTION Only for signal domain!
        channels_group = axesgroup.create_group("channels", track_order=True)
        channels_group.attrs["array_annotations"] = jsonio.dumps(array_annotations, cls=jsonio.CustomEncoder)
        
        for l in array_annotations.length:
            if "channel_ids" in array_annotations:
                channel_id = array_annotations["channel_ids"][l].item()
            else:
                channel_id = f"{l}"
                
            if "channel_names" in array_annotations:
                channel_name = array_annotations["channel_names"][l].item()
            else:
                channel_name = f"{l}"
                
            channel_dset = channels_group.create_dataset(f"channel_{l}", data=h5py.Empty("f"))
            channel_dset.attrs["id"] = channel_id
            channel_dset.attrs["name"] = channel_name
            
            for key in array_annotations:
                if key not in ("channel_ids", "channel_names"):
                    channel_dset.attrs[key] = array_annotations[key][k].item()
                    
            channel_dset.make_scale(f"channel_{l}")
            dset.dims[axis].attach_scale(channel_dset)
            
    for key, val in kwargs.items():
        if not isinstance(val, (pq.Quantity, np.ndarray)):
            raise TypeError(f"Expecting a python quantity or a numpy array; got {type(val).__name__} instead")
        
        if key == "sampling_rate":
            if isinstance(val, pq.Quantity) and not units_convertible(val, 1/units):
                warnings.warn(f"Writing {key} with units {val.units} incompatible with axis units {1/units}")
        else:
            if isinstance(val, pq.Quantity) and not units_convertible(val, units):
                warnings.warn(f"Writing {key} with units {val.units} incompatible with axis units {units}")
                
        if key in ("origin", "t_start"):
            axis_dset.attrs["origin"] = val.magnitude
        else:
            axis_dset.attrs[key] = val.magnitude
            
    axis_dset.make_scale(axis_name)
    dset.dims[axis].attach_scale(axis_dset)
    dset.dims[axis].label = domain_name
    
    return axis_dset

@singledispatch
def get_metadata(obj):
    raise TypeError(f"Objects of type {type(obj).__name__} are not yet supported")

@get_metadata.register(neo.core.dataobject.DataObject)
def _(obj):
    x_type, x_name, x_attrs = hdf_entry(obj, "")
    
    x_meta = dict()
    x_meta.update(x_attrs)
    
    x_meta["description"] = make_attr("" if obj.description is None else f"{obj.description}")
    x_meta["file_origin"] = make_attr(f"{obj.file_origin}")

    # NOTE: 2021-11-12 11:25:23
    # below we migrate to using our own custom json codec (see jsonio module)
    # we still keep the pickle fallback until we are satisfied we can do away
    # with it ...
    # any future changes must be brought to the custom codec to accomodate
    # "non-json-able" data
    annot = None
    try:
        annot = json.dumps(obj.annotations, cls=jsonio.CustomEncoder)
    except:
        # unencodable in json:
        try:
            annot = pickle.dumps(obj.annotations) # pickling is a bit cheating ...
        except:
            warnings.warn(f"Cannot encode anotations {obj.annotations}")
        
    if annot is not None:
        x_meta["annotations"] = annot
        
    if hasattr(obj, "mark_type"): 
        # TriggerEvent and DataMark
        x_meta["EventType"] = make_attr(obj.type.name)
        
    if hasattr(obj, "labels"): 
        # neo.Event, TriggerEvent, DataMark, neo.Epoch, and DataZone
        x_meta["labels"] = make_attr(obj.labels)
        
    data_name = getattr(obj, "name", None)
    
    return x_meta, data_name
    
    
    
    


def from_dataset(dset:typing.Union[str, h5py.Dataset],
                 group:typing.Optional[h5py.Group]=None, 
                 order:typing.Optional[str]=None):
    if isinstance(dset, str) and len(dset.strip()):
        if not isinstance(group, h5py.Group):
            raise TypeError(f"When the data set is indicated by its name, 'group' must a h5py.Group; got {type(group).__name__} instead")
        dset = group[dset] # raises exception if dset does not exist in group
        
    elif not isinstance(dset, h5py.Dataset):
        raise TypeError(f"Expecting a str (data set name) or HDF5 data set; got {type(dset).__name__} instead")
    
    data = dset[()]
    data_name = dset.name.split('/')[-1]
    
    if not isinstance(group, h5py.Group):
        group = dset.parent

    if "python_class" in dset.attrs:
        try:
            klass = eval(dset.attrs["python_class"])
        except:
            traceback.print_exc()
            klass = None
            
    if klass is vigra.VigraArray or "axistags" in dset.attrs:
        data = data.view(vigra.VigraArray)
        
        if "axistags" in dset.attrs: # => vigra array
            data = data.view(vigra.VigraArray)
            data.axistags = vigra.arraytypes.AxisTags.fromJSON(dset.attrs["axistags"])
            
            # NOTE: 2021-11-07 21:54:25
            # code below will override whatever calibration info was embedded in
            # the axistags at the time of writing into the HDF5 dataset, IF such
            # information is found in the HDF5 Dimension scales objects
            for dim in dset.dims: 
                if all(s in dim.keys() for s in ("name", "units", "origin", "resolution")) and dim.label in data.axistags:
                    cal = dict()
                    if "name" in dim:
                        cal["name"] = dim["name"][()].decode()
                        
                    if "units" in dim:
                        cal["units"] = unit_quantity_from_name_or_symbol(dim["units"][()].decode())
                        
                    if "origin" in dim:
                        cal["origin"] = float(dim["origin"][()])
                
                    if "resolution" in dim:
                        cal["resolution"] = float(dim["resolution"][()])
                        
                    if isinstance(dim.label, str) and len(dim.label.strip()):
                        cal["type"] = dim.label
                        cal["key"] = dim.label
                        
                    if AxisCalibrationData.isCalibration(cal):
                        axcal = AxisCalibrationData(cal)
                        if axcal.type & vigra.AxisType.Channels:
                            channels = unique(["_".join(key.split('_')[:2]) for key in dim.keys() if any(key.endswith(s) for s in ("_name", "_units", "_origin", "_resolution", "_maximum", "_index"))])
                            print("channels", channels)
                            for ch_key in channels:
                                chcal = dict()
                                if f"{ch_key}_name" in dim:
                                    chcal["name"] = dim[f"{ch_key}_name"][()].decode()
                                if f"{ch_key}_units" in dim:
                                    chcal["units"] = unit_quantity_from_name_or_symbol(dim[f"{ch_key}_units"][()].decode())
                                if f"{ch_key}_origin" in dim:
                                    chcal["origin"] = float(dim[f"{ch_key}_origin"][()])
                                if f"{ch_key}_resolution" in dim:
                                    chcal["resolution"] = float(dim[f"{ch_key}_resolution"][()])
                                if f"{ch_key}_maximum" in dim:
                                    chcal["maximum"] = float(dim[f"{ch_key}_maximum"][()])
                                if f"{ch_key}_index" in dim:
                                    chcal["index"] = int(dim[f"{ch_key}_index"][()])
                                    
                                if ChannelCalibrationData.isCalibration(chcal):
                                    axcal.addChannelCalibration(ChannelCalibrationData(chcal), name=ch_key)
                                    
                        axcal.calibrateAxis(data.axistags[dim.label])
                        
            if order is None:
                order = vigra.VigraArray.defaultOrder
            elif order not in ("V", "C", "F", "A", None):
                raise IOError(f"Unsupported order {order} for VigraArray")
            
            if order == "F":
                data = data.transpose()
            else:
                data = data.transposeToOrder(order)
                
    elif klass in (neo.AnalogSignal, neo.IrregularlySampledSignal, DataSignal, IrregularlySampledDataSignal):
        attrs = dict(dset.attrs)
        
        file_origin = attrs.pop("file_origin", None)
        if file_origin is None:
            file_origin = ""
        elif not isinstance(file_origin, str):
            file_origin = file_origin[()].decode()
            
        description = attrs.pop("description", None)
        if description is None:
            description = ""
        elif not isinstance(description, str):
            description = description[()].decode()
            
        annotations = dict()
            
        annotations = attrs.pop("annotations", None)
        if annotations is None:
            annotations = dict()
            
        if isinstance(annotations, str):
            try:
                annotations = json.loads(annotations)
            except:
                warnings.warn(f"Cannot read annotations {annotations} from json")
                
        elif isinstance(annotations, bytes):
            try:
                annotations = json.loads(annotations[()].decode())
            except:
                warnings.warn(f"Cannot read annotations {annotations} from json")
                try:
                    annotations = pickle.loads(annotations)
                except:
                    warnings.warn(f"Cannot read annotations {annotations}")
                
                
        data = data.view(np.ndarray).transpose()
        sigcal = {"units": pq.dimensionless, "name": klass.__name__}
        domcal = {"units": pq.s if klass in (neo.AnalogSignal, neo.IrregularlySampledSignal) else pq.dimensionless,
                  "name": "",
                  "t_start": 0.,
                  "sampling_rate": None,
                  "sampling_rate_units": pq.Hz if klass in (neo.AnalogSignal, DataSignal) else pq.dimensionless,
                  "times": None # will be populated from domain data set for irregular signals
                  }
        
        arr_ann = {"channel_ids": list(), "channel_names": list()}
        
        for k, dim in enumerate(dset.dims):
            # NOTE: these are for transposed axes!
            #print(k, "dim:")
            #print([v for v in dim.values()])
            if k == 0: # => signal axis (1) in the final data!
                if "units" in dim:
                    sigcal["units"] = unit_quantity_from_name_or_symbol(dim["units"][()].decode())
                if "name" in dim:
                    sigcal["name"] = dim["name"][()].decode()
                    
                channel_data = unique([(k,v) for k,v in dim.items() if k.startswith("channel_")])
                #print("channel_data", channel_data)
                entries = unique([k[0].split("_")[-1] for k in channel_data])
                #print("entries", entries)
                
                for k in range(data.shape[-1]):
                    for entry in entries:
                        if f"channel_{k}_{entry}" in dim.keys():
                            val = dim[f"channel_{k}_{entry}"]
                            #print(k, "entry", entry, "val", val)
                            if entry == "id":
                                arr_ann["channel_ids"].append(val[()].decode())
                            elif entry == "name":
                                arr_ann["channel_names"].append(val[()].decode())
                            else:
                                if entry not in arr_ann:
                                    arr_ann[entry] = list()
                                    
                                if val.dtype == h5py.string_dtype():
                                    val = val[()].decode()
                                elif val.dtype.kind == "O":
                                    if type(val[()]) == bytes:
                                        val = val[()].decode()
                                    else:
                                        val = val[()]
                                    
                                else:
                                    val = val[()]
                                
                                arr_ann[entry].append(val)
                    
            else: # => domain axis (0) in the final data - dimension scales here ONLY for AnalogSignal and DataSignal
                if "domain_origin" in dim:
                    domcal["t_start"] = dim["domain_origin"][()]
                    
                if "domain_units" in dim:
                    domcal["units"] = unit_quantity_from_name_or_symbol(dim["domain_units"][()].decode())
                    
                if "domain_name" in dim:
                    domcal["name"] = dim["domain_name"][()].decode()
                    
                if "sampling_rate" in dim:
                    domcal["sampling_rate"] =dim["sampling_rate"][()]
                    
                if "sampling_rate_units" in dim:
                    domcal["sampling_rate_units"] = unit_quantity_from_name_or_symbol(dim["sampling_rate_units"][()].decode())
                    
        array_annotations = ArrayDict(data.shape[-1], **arr_ann)
            
        if klass in (neo.AnalogSignal, DataSignal):
            data = klass(data, units = sigcal["units"], name=sigcal["name"],
                            t_start = domcal["t_start"] * domcal["units"],
                            sampling_rate = domcal["sampling_rate"] * domcal["sampling_rate_units"],
                            file_origin=file_origin,
                            description=description,
                            array_annotations = array_annotations,
                            **annotations)
            data.segment = None
            
        elif klass in (neo.IrregularlySampledSignal, IrregularlySampledDataSignal):
            # need to read the domain data set:
            domain_group = group.get(f"{data_name}_domain", None)
            if isinstance(domain_group, h5py.Group):
                dom_dset = domain_group.get(f"{data_name}_domain_set", None)
                if isinstance(dom_dset, h5py.Dataset):
                    domcal["times"] = dom_dset[()]
                    dim = dom_dset.dims[0]
                    # everything else is in the dimension scales
                    if "domain_units" in dim:
                        domcal["units"] = unit_quantity_from_name_or_symbol(dim["domain_units"][()].decode())
                        
                    if "domain_name" in dim:
                        domcal["name"] = dim["domain_name"][()].decode()
                        
                else:
                    raise HDFDataError(f"Cannot find a domain Dataset for the irregularly sampled signal {data_name}")
            else:
                raise HDFDataError(f"Cannot find a domain Group for the irregularly sampled signal {data_name}")

            if klass is neo.IrregularlySampledSignal:
                data = klass(domcal["times"] * domcal["units"], data, units = sigcal["units"],
                            time_units=domcal["units"], name=sigcal["name"],
                            file_origin = file_origin,
                            description = description,
                            array_annotations = array_annotations, **annotations)
            else:
                data = klass(domcal["times"] * domcal["units"], data, units = sigcal["units"],
                            domain_units=domcal["units"], name=sigcal["name"],
                            file_origin = file_origin,
                            description = description,
                            array_annotations = array_annotations, **annotations)
                
            data.segment = None
            
    elif klass in (neo.Event, TriggerEvent, DataMark):
        attrs = dict(dset.attrs)
        
        file_origin = attrs.pop("file_origin", None)
        if file_origin is None:
            file_origin = ""
        elif not isinstance(file_origin, str):
            file_origin = file_origin[()].decode()
            
        description = attrs.pop("description", None)
        if description is None:
            description = ""
        elif not isinstance(description, str):
            description = description[()].decode()
            
        annotations = dict()
            
        annotations = attrs.pop("annotations", None)
        if annotations is None:
            annotations = dict()
            
        if isinstance(annotations, str):
            try:
                annotations = json.loads(annotations)
            except:
                warnings.warn(f"Cannot read annotations {annotations} from json")
                
        elif isinstance(annotations, bytes):
            try:
                annotations = json.loads(annotations[()].decode())
            except:
                warnings.warn(f"Cannot read annotations {annotations} from json")
                try:
                    annotations = pickle.loads(annotations)
                except:
                    warnings.warn(f"Cannot read annotations {annotations}")
                
        labels = attrs.pop("labels", None)
        
        if isinstance(labels, str):
            if not labels.isidentifier():
                try:
                    labels = json.loads(labels)
                except:
                    traceback.print_exc()
                    labels = None
                
        elif isinstance(labels, np.ndarray):
            labels = np.asarray(labels, dtype=np.dtype("U"))
                
        elif labels is not None: # how ot interpret anything else? loose it for now
            labels = None
                
        data = data.view(np.ndarray).transpose()
        
        dim = dset.dims[1]
        
        #name = dim.label
        
        if "units" in dim:
            units = unit_quantity_from_name_or_symbol(dim["units"][()].decode())
        else:
            units = pq.arbitrary_unit if klass is DataMark else pq.s
            
            
        data = klass(times=data, labels=labels,units=units,name=data_name,
                    description=description,file_origin=file_origin,
                    **annotations)
        
        if klass is DataMark:
            event_type = attrs.pop("MarkType", None)
            if event_type is not None:
                data.type = event_type
                
        elif klass is TriggerEventType:
            event_type = attrs.pop("TriggerEventType", None)
            if event_type is not None:
                data.type = event_type
            
        arr_ann = dict()
        
        for key in dim:
            if key != "units":
                val = dim[key]
                if key not in arr_ann:
                    arr_ann[key] = list()
                    
                if val.dtype == h5py.string_dtype():
                    val = val[()].decode()
                    
                elif val.dtype.kind == "O":
                    if type(val[()]) == bytes:
                        val = val[()].decode()
                    else:
                        val = val[()]
                else:
                    val = val[()]
                arr_ann[key].append(val)
                
        if len(arr_ann):
            array_annotations = ArrayDict(data._get_arr_ann_length(), **arr_ann)
            
            data.array_annotations = array_annotations
            
        data.segment=None
            
    elif klass in (neo.Epoch, DataZone):
        attrs = dict(dset.attrs)
        
        file_origin = attrs.pop("file_origin", None)
        if file_origin is None:
            file_origin = ""
        elif not isinstance(file_origin, str):
            file_origin = file_origin[()].decode()
            
        description = attrs.pop("description", None)
        if description is None:
            description = ""
        elif not isinstance(description, str):
            description = description[()].decode()
            
        annotations = dict()
            
        annotations = attrs.pop("annotations", None)
        if annotations is None:
            annotations = dict()
            
        if isinstance(annotations, str):
            try:
                annotations = json.loads(annotations)
            except:
                warnings.warn(f"Cannot read annotations {annotations} from json")
                
        elif isinstance(annotations, bytes):
            try:
                annotations = json.loads(annotations[()].decode())
            except:
                warnings.warn(f"Cannot read annotations {annotations} from json")
                try:
                    annotations = pickle.loads(annotations)
                except:
                    warnings.warn(f"Cannot read annotations {annotations}")
                
        labels = attrs.pop("labels", None)
        
        if isinstance(labels, str):
            if not labels.isidentifier():
                try:
                    labels = json.loads(labels)
                except:
                    traceback.print_exc()
                    labels = None
                
        elif isinstance(labels, np.ndarray):
            labels = np.asarray(labels, dtype=np.dtype("U"))
                
        elif labels is not None: # how ot interpret anything else? loose it for now
            labels = None
                
        dim = dset.dims[1]
        
        #name = dim.label
        
        if "units" in dim:
            units = unit_quantity_from_name_or_symbol(dim["units"][()].decode())
        else:
            units = pq.arbitrary_unit if klass is DataMark else pq.s
            
            
        data = data.view(np.ndarray).transpose()
        
        times = np.atleast_1d(data[:,0])
        
        if data.shape[-1] == 2:
            durations = np.atleast_1d(data[:,1])
            
        else:
            durations = None
        
        data = klass(times=data, durations=durations, labels=labels,units=units,
                     name=data_name, description=description, file_origin=file_origin,
                    **annotations)
        
        arr_ann = dict()
        
        for key in dim:
            if key != "units":
                val = dim[key]
                if key not in arr_ann:
                    arr_ann[key] = list()
                    
                if val.dtype == h5py.string_dtype():
                    val = val[()].decode()
                    
                elif val.dtype.kind == "O":
                    if type(val[()]) == bytes:
                        val = val[()].decode()
                    else:
                        val = val[()]
                else:
                    val = val[()]
                arr_ann[key].append(val)
                
        if len(arr_ann):
            array_annotations = ArrayDict(data._get_arr_ann_length(), **arr_ann)
            
            data.array_annotations = array_annotations
            
        data.segment = None
            
    elif isinstance(data, bytes):
        data = data.decode()
            
    return data

def make_dataset(x:typing.Any, group:h5py.Group, 
                 name:typing.Optional[str]=None,
                 compression:typing.Optional[str]=None,
                 chunks:typing.Optional[bool]=None):
    """Creates a HDF5 datasets for supported Python types
    
    NOTE: 2021-11-12 11:56:12
    
    I am migrating to the scenario when this function is ONLY used for basic
    Python object type hierarchy plus generic numpy arrays.
    
    For specialized objects in 3rd party packages one MUST create an IO class
    in this module.
    
    Specialized objects in Scipyen should EITHER:
    a) supply their own 'toJSON'/'fromJSON' methods, OR
    b) use a generic IO class in this module (to be written)
    
    TODO: for neo.DataObjects make reference to segment when segment is included
        in the same HDF file
        
    TODO: neo.DataObject
        TODO: neo.SpikeTrain
        TODO: neo.ImageSequence
        
    TODO: neo.Container:
        TODO: neo.Block
        TODO: neo.Group
        
    TODO: neo.ChannelView
    TODO: neo.RegionOfInterest
    
    TODO: vigra.filters.Kernel1D, Kernel2D
    
    TODO: pictgui.PlanarGraphics
    
    TODO: TriggerProtocol
    
    TODO: pandas.Series, pandas.DataFrame
    
    TODO: core.modelfitting.FitModel, ModelExpression
    
    TODO: imaging:
        TODO: scandata.ScanData, AnalysisUnit
        TODO: axiscalibration.AxesCalibration, AxisCalibrationData, ChannelCalibrationData
            NOTE: these are written as DimensionScales; since they are 'volatile'
                objects, there is no real need to write them to HDF5 as such.
                
                HOWEVER, in the interest of generality I should perhaps contemplate
                a way to read/write objects of these types from/to HDF5 data 
                structure.
                CAUTION: this may confuse a library user: are these objects to be
                attached to a (vigra array, numpy array, etc) when they are found
                inside a HDF5 data structure, or treated as independent objects
                with a life of their own?
                
                As a rule of thumb, these objects are NEVER to be written directly
                into the usual HDF5 hierarchy (Group/Dataset) unless there is a
                specific intention to do so, and with the explicit purpose of
                storing them as 'free-standing' entities (not that it would make
                much sense to do so...)
                
                I all other scenarios - i.e. when they ARE attached to an array
                - they are to be 'decomposed' and their elements are to be written
                into the array's dimension scales (to be later read and used to
                'recompose' the array information).
                
                See the case for VigraArray in make_dataset and from_dataset
                functions.
                
    NOTE: About array annotations of neo data objects.
        These are used to store information associated with a specific 'channel'
        in the numeric array of the neo data object (a.k.a 'signal channel')
        
        An array annotation is a so-called ArrayDict where each key is mapped to 
        a 1D numpy array with the same length as the number of channels in the 
        signal (at least this is what I understand from reading the source code;
        the official documentation in the neo package tends to be somewhat
        ambiguous).
    
    Parameters:
    ===========
    x: a Python object
    group: parent group where the data set is created
    compression, chunks - passed on to create_dataset
    
    Returns:
    =======
    h5py.Dataset or None (if the python object is not supported)
    
    Its `attrs` member contains a generic set of data attributes relevant to the
    Python object `x`.
    
    Side effects:
    ============
    
    One or more, possibily nested, h5py.Group objects may be created in the parent
    `group`, alongside the newly-created dataset. 
    These additional groups contain ancillary data (or `metadata`) associated with
    the Python object, such as HDF5 dimension scales (containing axes information 
    for numpy arrays and types derived from numpy arrays) and other datasets 
    pertaining to members of the Python object (when themselves are of more elaborate
    types).
    
    Other object `metadata` are stored as HDF attributes of the created data set.
    
    
    """
    x_type, x_name, x_attrs = hdf_entry(x, "")
    
    data_name = getattr(x, "name", None)
    
    if not isinstance(data_name, str) or len(data_name.strip()) == 0:
        data_name = name
                    
    if not isinstance(name, str) or len(name.strip()) == 0:
        name = x_name
        
    if isinstance(x, (bool, bytes, complex, float, int)):
        dset = group.create_dataset(name, data = x)
        dset.attrs.update(x_attrs)
        
    elif isinstance(x, str):
        dset = group.create_dataset(name, data = x, dtype = h5py.string_dtype())
        
    elif isinstance(x, vigra.VigraArray):
        # NOTE: 2021-11-07 13:58:50
        # writeHDF5 stores a transposeToNumpyOrder() view of the vigra array in
        # a HDF5 dataset; the axistags are embedded (json version) in the HDF5
        # dataset attribute 'axistags' (attrs)
        # NO HDF5 dimension scales are used/populated by vigra API
        # NOTE: 2021-11-07 14:04:56
        # there is nothing inherently wrong in using dimension scales; it is up
        # to the HDF5 file reader if dimension scales are to be used, and how;
        # (the only objection might be that dimension scales in this context are
        # reduntant information, but I think the space cost is acceptable)
        # The advantage of using dimension scales is that they can be reveal
        # more easily (or 'naturally') the axes calibrations to a generic
        # HDF5 viewer/reader, whereas the information in axistags is relatively
        # more cryptic.
        
        # We want the dimension scales to reflect the axes in the order they are
        # stored in the dataset.
        data = x.transposeToNumpyOrder()
        dset = group.create_dataset(name, data=data, compression=compression, chunks=chunks)
        x_attrs["axistags"] = string2hdf(data.axistags.toJSON())
        dset.attrs.update(x_attrs)
        
        # For each axis, we attach FOUR HDF5 dimension scales: 
        # name (str), units (str), origin (float), and resolution (float)
        # in addition, for a Channels axis (of which there can be at most ONE)
        # we create four dimension scales for each channel - except when the
        # Channels axis is non-existent: the data has one 'virtual' channel which
        # by definition is uncalibrated.
        x_tr_axcal = AxesCalibration(data)
        
        calgrp = group.create_group(f"{name}_axes", track_order=True)
        
        for k, cal in enumerate(x_tr_axcal):
            axcalgrp = calgrp.create_group(f"{cal.key}", track_order=True)
            
            ds_origin = make_dataset(cal.origin, axcalgrp, name = "origin")
            ds_origin.make_scale("origin")
            
            ds_resolution = make_dataset(cal.resolution, axcalgrp, name = "resolution")
            ds_resolution.make_scale("resolution")
            
            ds_units = make_dataset(cal.units.dimensionality.string, axcalgrp,
                                    name="units")
            ds_units.make_scale("units")
            
            ds_name = make_dataset(cal.name, axcalgrp, name = "name")
            ds_name.make_scale("name")
                
            dset.dims[k].attach_scale(ds_name)
            dset.dims[k].attach_scale(ds_units)
            dset.dims[k].attach_scale(ds_origin)
            dset.dims[k].attach_scale(ds_resolution)
            
            if cal.type & vigra.AxisType.Channels:
                # check to see if there are non-virtual channel calibrations
                # a singleton channels axis might be virtual hence without a
                # concrete channel calibration
                channels = [ch for ch in cal.channels if "virtual" not in ch[0]]
                if len(channels):
                    channels_group = axcalgrp.create_group("channels", track_order=True)
                    for channel in channels:
                        channel_group = channels_group.create_group(channel[0], track_order=True)
                        
                        ds_chn_origin = make_dataset(channel[1].origin, channel_group, name=f"{channel[0]}_origin")
                        ds_chn_origin.make_scale(f"{channel[0]}_origin")
                        
                        ds_chn_resolution = make_dataset(channel[1].resolution, channel_group, name=f"{channel[0]}_resolution")
                        ds_chn_resolution.make_scale(f"{channel[0]}_resolution")
                        
                        ds_chn_maximum = make_dataset(channel[1].maximum, channel_group, name = f"{channel[0]}_maximum")
                        ds_chn_maximum.make_scale(f"{channel[0]}_maximum")
                        
                        ds_chn_index = make_dataset(channel[1].index, channel_group, name=f"{channel[0]}_index")
                        ds_chn_index.make_scale(f"{channel[0]}_index")
                        
                        ds_chn_units = make_dataset(channel[1].units.dimensionality.string, channel_group, 
                                                    name = f"{channel[0]}_units")
                        ds_chn_units.make_scale(f"{channel[0]}_units")
                        
                        ds_chn_name = make_dataset(channel[1].name, channel_group, name=f"{channel[0]}_name")
                        ds_chn_name.make_scale(f"{channel[0]}_name") # channel name, not axis name!
                        
                        dset.dims[k].attach_scale(ds_chn_name)
                        dset.dims[k].attach_scale(ds_chn_units)
                        dset.dims[k].attach_scale(ds_chn_index)
                        dset.dims[k].attach_scale(ds_chn_origin)
                        dset.dims[k].attach_scale(ds_chn_resolution)
                        dset.dims[k].attach_scale(ds_chn_maximum)
                        
            dset.dims[k].label = f"{cal.key}"
            
    elif isinstance(x, (neo.AnalogSignal, DataSignal, neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
        # axis 0 is the domain axis; for irregularly sampled signals we store 
        # the domain separately
        # axis 1 is the signal axis
        # after transposition, signal axis is axis 0; domain axis is axis 1
        data = np.transpose(x.magnitude) # axis 0 becomes axis 1 and vice-versa!
        x_meta = dict()
        x_meta.update(x_attrs)
        
        x_meta["description"] = make_attr("" if x.description is None else f"{x.description}")
        x_meta["file_origin"] = make_attr(f"{x.file_origin}")
        annot = None
        try:
            annot = json.dumps(x.annotations)
        except:
            # unencodable in json:
            try:
                annot = pickle.dumps(x.annotations) # pickling is a bit cheating ...
            except:
                warnings.warn(f"Cannot encode anotations {x.annotations}")
            
        if annot is not None:
            x_meta["annotations"] = annot
        
        dset = group.create_dataset(name, data = data)
        #print("x_meta", x_meta)
        dset.attrs.update(x_meta)
        dom_dset = None # place holder for irregularly sampled signals' domain data
        
        if isinstance(x, (IrregularlySampledDataSignal, neo.IrregularlySampledSignal)):
            domain_group = group.create_group(f"{name}_domain", track_order = True)
            domain_name = x.domain_name if isinstance(x, IrregularlySampledDataSignal) else "Time"
            dom_dset = make_dataset(x.times.magnitude, domain_group, name=f"{name}_domain_set")
            dom_dset.attrs["name"] = domain_name
        
        calgrp = group.create_group(f"{name}_axes", track_order=True)
        
        # axis 0 is now the signal axis
        signal_axis_group = calgrp.create_group(f"signal_axis", track_order=True)
        ds_units = make_dataset(x.dimensionality.string, signal_axis_group, name="units")
        ds_units.make_scale("units")
        # (un)fortunately(?), individual channels (i.e. data columns) in
        # neo signals are not named
        #data_name = getattr(x, "name", None)
        
        #if not isinstance(data_name, str) or len(data_name.strip()) == 0:
            #data_name = name
            
        #print("data_name", data_name, "name", name)
        ds_name = make_dataset(data_name, signal_axis_group, name = "name")
        ds_name.make_scale("name")
        
        dset.dims[0].attach_scale(ds_name)
        dset.dims[0].attach_scale(ds_units)

        channels_group = signal_axis_group.create_group("channels", track_order=True)
        
        array_annotations = getattr(x, "array_annotations", None)
        
        if isinstance(array_annotations, ArrayDict):
            channels_group.attrs.update(make_attr_dict(**array_annotations))
            
        else:
            array_annotations = dict() # shim for below
        
        for l in range(x.shape[-1]):
            if "channel_ids" in array_annotations:
                channel_id = array_annotations["channel_ids"][l].item()
            else:
                channel_id = f"{l}"
                
            if "channel_names" in array_annotations:
                channel_name = array_annotations["channel_names"][l].item()
            else:
                channel_name = f"{l}"
                
            channel_group = channels_group.create_group(f"channel_{l}", track_order=True)
            
            ds_chn_id = make_dataset(channel_id, channel_group, name=f"channel_{l}_id")
            ds_chn_id.make_scale(f"channel_{l}_id")
            
            ds_chn_name = make_dataset(channel_name, channel_group, name=f"channel_{l}_name")
            ds_chn_name.make_scale(f"channel_{l}_name")
            
            dset.dims[0].attach_scale(ds_chn_id)
            dset.dims[0].attach_scale(ds_chn_name)
            
            for key in array_annotations:
                if key not in ("channel_ids", "channel_names"):
                    ds_chn_key = make_dataset(array_annotations[key][k].item(), channel_group, name=f"channel_{l}_{key}")
                    ds_chn_key.make_scale(f"channel_{l}_{key}")
                    dset.dims[0].attach_scale(ds_chn_key)
            
        dset.dims[0].label = data_name
                    
        # axis 1 is now the time (or domain) axis
        domain_axis_group = calgrp.create_group(f"signal_domain", track_order=True)
        #if isinstance(x, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)):
            #continue # save this axis as a separate dataset
        if isinstance(x, (DataSignal, IrregularlySampledDataSignal)):
            domain_name = x.domain_name
        else:
            domain_name = "Time"
            
        ds_dom_units = make_dataset(x.times.units.dimensionality.string, domain_axis_group, name="domain_units")
        ds_dom_units.make_scale("domain_units")
        
        ds_dom_name = make_dataset(domain_name, domain_axis_group, name="domain_name")
        ds_dom_name.make_scale("domain_name")
        
        if isinstance(x, (DataSignal, neo.AnalogSignal)):
            ds_dom_origin = make_dataset(x.t_start.magnitude.item(), domain_axis_group, name="domain_origin")
            ds_dom_origin.make_scale("domain_origin")
            
            ds_dom_rate = make_dataset(x.sampling_rate.magnitude.item(), domain_axis_group, name="sampling_rate")
            ds_dom_rate.make_scale("sampling_rate")

            ds_dom_rate_units = make_dataset(x.sampling_rate.units.dimensionality.string, domain_axis_group, name="sampling_rate_units")
            ds_dom_rate_units.make_scale("sampling_rate_units")
        
        if isinstance(x, (IrregularlySampledDataSignal, neo.IrregularlySampledSignal)) and isinstance(dom_dset, h5py.Dataset):
            #dom_dset created above
            dom_dset.dims[0].attach_scale(ds_dom_name)
            dom_dset.dims[0].attach_scale(ds_dom_units)
        else:
            dset.dims[1].attach_scale(ds_dom_name)
            dset.dims[1].attach_scale(ds_dom_origin)
            dset.dims[1].attach_scale(ds_dom_units)
            dset.dims[1].attach_scale(ds_dom_rate)
            dset.dims[1].attach_scale(ds_dom_rate_units)
        
        dset.dims[1].label = domain_name
                
    elif isinstance(x, (neo.Event, TriggerEvent, DataMark)):
        # NOTE: 2021-11-11 22:23:15
        # even if this is tranposed, there is only one (relevant) axis: that
        # containing the domain (which is the same as the signal)
        data = np.transpose(np.atleast_1d(x.times.magnitude.flatten()))
        x_meta = dict()
        x_meta.update(x_attrs)
        x_meta["description"] = make_attr("" if x.description is None else f"{x.description}")
        x_meta["file_origin"] = make_attr(f"{x.file_origin}")
        
        annot = None
        try:
            annot = json.dumps(x.annotations)
        except:
            # unencodable in json:
            try:
                annot = pickle.dumps(x.annotations) # pickling is a bit cheating ...
            except:
                warnings.warn(f"Cannot encode anotations {x.annotations}")
            
        if annot is not None:
            x_meta["annotations"] = annot
            
        array_annotations = getattr(x, "array_annotations", None)
        
        x_meta["labels"] = make_attr(x.labels)
        
        if isinstance(x, TriggerEvent):
            x_meta["TriggerEventType"] = x.type
            
        elif isinstance(x, DataMark):
            x_meta["MarkType"] = x.type
            
        dset = group.create_dataset(name, data=data)
        dset.attrs.update(x_meta)
        
        # these groups store axis information; we do NOT have AxisCalibrationData
        # objects for these kind of arrays (yet...; maybe I should extend AxisCalibrationData
        # to neo signals-like data as well)
        calgrp = group.create_group(f"{name}_axes", track_order=True)
        axcalgrp = calgrp.create_group("signal_domain", track_order=True)
        
        dset.dims[0].label = data_name
        if isinstance(array_annotations, ArrayDict):
            axcalgrp.attrs.update(make_attr_dict(**array_annotations))
            
        else:
            array_annotations = dict() # shim for below
            
        for key in array_annotations:
            ds_key = make_dataset(array_annotations[key][0].item(), axcalgroup, name=key)
            ds_key.make_scale(key)
            dset.dims[0].attach_scale(ds_key)
            
                
        ds_units = make_dataset(x.times.units.dimensionality.string, axcalgrp, name="units")
        ds_units.make_scale("units")
        dset.dims[1].attach_scale(ds_units)
        dset.dims[1].label=name_from_unit(x.times.units)
        
        # NOTE: events and datamarks are ALWAYS 1D (or supposed to be) so we
        # don't iterate through 2nd dimension here (axis 1)
        
    elif isinstance(x, neo.Epoch, DataZone):
        if len(x.durations):
            data = np.transpose(np.concatenate((np.atleast_1d(x.times.magnitude.flatten()),
                                   np.atleast_1d(x.durations.magnitude.flatten())),
                                   axis=1))
            
        else:
            data = np.transpose(np.at_least_1d(x.times.magnitude.flatten()))
            
        x_meta = dict()
        x_meta.update(x_attrs)
        x_meta["description"] = make_attr("" if x.description is None else f"{x.description}")
        x_meta["file_origin"] = make_attr(f"{x.file_origin}")
        
        annot = None
        try:
            annot = json.dumps(x.annotations)
        except:
            # unencodable in json:
            try:
                annot = pickle.dumps(x.annotations) # pickling is a bit cheating ...
            except:
                warnings.warn(f"Cannot encode anotations {x.annotations}")
            
        if annot is not None:
            x_meta["annotations"] = annot
            
        array_annotations = getattr(x, "array_annotations", None)
        
        x_meta["labels"] = make_attr(x.labels)
        
        dset = group.create_dataset(name, data=data)
        dset.attrs.update(x_meta)
        
        dset.dims[0].label = data_name
        
        calgrp = group.create_group(f"{name}_axes", track_order=True)
        axcalgrp = calgrp.create_group("signal_domain", track_order=True)
        
        if isinstance(array_annotations, ArrayDict):
            axcalgrp.attrs.update(make_attr_dict(**array_annotations))
            
        else:
            array_annotations = dict() # shim for below
                
        # NOTE: events and datamarks are ALWAYS 1D (or supposed to be) so we
        # don't iterate through 2nd dimension here (axis 1)
        for key in array_annotations:
            ds_key = make_dataset(array_annotations[key][0].item(), axcalgroup, name=key)
            ds_key.make_scale(key)
            dset.dims[0].attach_scale(ds_key)
            
        ds_units = make_dataset(x.times.units.dimensionality.string, axcalgrp, name="units")
        ds_units.make_scale("units")
        dset.dims[1].attach_scale(ds_units)
        dset.dims[1].label=name_from_unit(x.times.units)
        
    elif isinstance(x, neo.SpikeTrain):
        x_meta = dict()
        x_meta.update(x_attrs)
        
        x_meta["description"] = make_attr("" if x.description is None else f"{x.description}")
        x_meta["file_origin"] = make_attr(f"{x.file_origin}")
        
        annot = None
        try:
            annot = json.dumps(x.annotations)
        except:
            # unencodable in json:
            try:
                annot = pickle.dumps(x.annotations) # pickling is a bit cheating ...
            except:
                warnings.warn(f"Cannot encode anotations {x.annotations}")
            
        if annot is not None:
            x_meta["annotations"] = annot
            
        times = x.times.magnitude
        
        # this one should go to a dataset of its own
        waveforms = x.waveforms # quantity array 3D (spike, channel, time)
        
        # data to go into the main dataset's dimension scales for the domain axis (axis 0):
        sampling_rate = x.sampling_rate # scalar quantity
        left_sweep = x.left_sweep # 1D quantity array (but really, a scalar...?)
        duration = x.duration # quantity scalar
        units = x.times.units
        sampling_rate_units = x.sampling_rate.units
        t_start = x.t_start # quantity scalar
        t_stop = x.t_stop # quantity scalar
        
        # NOTE: 2021-11-11 22:22:04
        # here we only transpose the times array (column vector -> row vector)
        # after tranposition axis 0 is the signal axis; axis 1 is the domain axis
        
        dset = group.create_dataset(name, data=times.transpose())
        dset.attrs.update(x_meta)
        
        
        calgrp = group.create_group(f"{name}_axes", track_order=True)
        signal_group = calgrp.create_group("")
        domain_group = calgrp.create_group("signal_domain", track_order=True)
        
        dset.dims[0].label = data_name
        if isinstance(array_annotations, ArrayDict):
            axcalgrp.attrs.update(make_attr_dict(**array_annotations))
            
        else:
            array_annotations = dict() # shim for below
                
        for key in array_annotations:
            ds_key = make_dataset(array_annotations[key][0].item(), axcalgroup, name=key)
            ds_key.make_scale(key)
            dset.dims[0].attach_scale(ds_key)
            
        
        ds_units = make_dataset(units.dimensionality.string, axcalgrp, name="units")
        ds_units.make_scale("units")
        dset.dims[1].attach_scale(ds_units)
        dset.dims[1].label=name_from_unit(x.times.units)
        
        ds_dom_origin = make_dataset(x.t_start.magnitude.item(), axcalgrp, name="domain_origin")
        ds_dom_origin.make_scale("domain_origin")
        
        ds_dom_end = make_dataset(x.t_stop.magnitude.item(), axcalgrp, name="domain_end")
        ds_dom_origin.make_scale("domain_end")
        
        ds_dom_rate = make_dataset(x.sampling_rate.magnitude.item(), axcalgrp, name="sampling_rate")
        ds_dom_rate.make_scale("sampling_rate")

        ds_dom_rate_units = make_dataset(x.sampling_rate.units.dimensionality.string, axcalgrp, name="sampling_rate_units")
        ds_dom_rate_units.make_scale("sampling_rate_units")
                
        # NOTE: events and datamarks are ALWAYS 1D (or supposed to be) so we
        # don't iterate through 2nd dimension here (axis 1)
        for key in array_annotations:
            ds_key = make_dataset(array_annotations[key][0].item(), axcalgroup, name=key)
            ds_key.make_scale(key)
            dset.dims[0].attach_scale(ds_key)
            
    elif isinstance(x, pq.Quantity):
        dset = make_dataset(x.magnitude, group, name=name)
        x_attrs.update(make_attr_dict(units = x.dimensionality.string))
        dset.attrs.update(x_attrs)
        
    elif isinstance(x, np.ndarray):
        dset = group.create_dataset(name, data = x)
        dset.attrs.update(x_attrs)
        
    elif isinstance(x, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
        dset = group.create_dataset(name, data = vu.kernel2array(x, True)) # 'True' returns a numpy array
        dset.attrs.update(x_attrs)
        
        # NOTE: 2021-11-15 17:44:13
        # to reconstitute 1D kernel:
        # k1d = vigra.filters.Kernel1D()
        # xy = group[dataset_name] => 2D array
        # left = int(xy[0,0])
        # right = int(xy[-1,0])
        # contents = xy[:,1]
        # k1d.initExplicitly(left, right, xy[:,1])
        #
        # to reconstitute 2D kernel:
        # k2d = vigra.filters.Kernel2D()
        # xy = group[dataset_name] => 3D array
        # upperLeft = (int(xy[-1,-1,0]), int(xy[-1,-1,1]))
        # lowerRight = (int(xy[0,0,0]), int(xy[0,0,1]))
        # contents = xy[:,:,2]
        # k2d.initExplicitly(upperLeft, lowerRight, contents)
        
    else:
        dset = None
        
    return dset

def data2hdf(x:typing.Any, 
             fileNameOrGroup:typing.Union[str, h5py.Group], 
             pathInFile:typing.Optional[str]=None,
             mode:typing.Optional[str] = None) -> None:
    
    if mode is None or not isinstance(mode, str) or len(mode.strip()) == 0:
        mode = "w"
    
    #if not isinstance(x, collections.abc.Mapping):
        #raise TypeError(f"Expecting a mapping; got {type(x).__name__} instead")
    
    file, group, childname, external = get_file_group_child(fileNameOrGroup, pathInFile, mode)
    
    print("data2hdf file", file, "group", group, "childname", childname, "external", external)
    
    try:
    
        #x_attrs = generic_data_attrs(x)
        x_type, x_name, x_attrs = hdf_entry(x)
        
        entry_name = childname if isinstance(childname, str) and len(childname.strip()) else x_name
        
        if isinstance(x, (bool, bytes, complex, float, int, str)): # -> Dataset
            
            dsetname = f"{x.__class__.__name__}"
            dset = group.create_dataset(entry_name, data = x)
            dset.attrs.update(x_attrs)
            
        elif isinstance(x, vigra.VigraArray): # -> Dataset
            target = group if file is None else file
            dset = writeHDF5_VigraArray(x, target, entry_name)
            dset.attrs.update(x_attrs)
            
        elif isinstance(x, neo.core.container.Container): # -> Group
            pass
            
        elif isinstance(x, neo.core.dataobject.DataObject): # -> Dataset
            pass
            
        elif isinstance(x, pq.Quantity): # -> Dataset
            # generic Quantity object: create a Dataset for its magnitude,
            # adorn attrs with dimensionality
            pass
        
        elif isinstance(x, np.ndarray): # -> Dataset
            if x.dtype is np.dtype(object):
                raise TypeError("Numpy arrays of Python objects are not supported")
            
            dset = group.create_dataset(entry_name, data=x)
            dset.attrs.update(x_attrs)
            #group[childname]=dset
            
        else:
            if issubclass(x_type, collections.abc.Iterable):
                #print("data2hdf Iterable")
                if issubclass(x_type, collections.abc.Mapping): # -> Group with nested Group objects
                    #print("data2hdf Mapping")
                    objgroup = group.create_group(entry_name, track_order=True)
                    for key, val in x.items():
                        print(f"key: {key}; value: ", type(val))
                        key_type, keyname, attrs = hdf_entry(key)
                        print(f"keyname: {keyname}")
                        print("attrs\n", attrs)
                        keygroup = objgroup.create_group(keyname, track_order=True)
                        keygroup.attrs.update(attrs)
                        print("keygroup", keygroup)
                        print("call data2hdf")
                        data2hdf(val, keygroup, pathInFile=keygroup.name)
                elif issubclass(x_type, collections.abc.Sequence): #-> Group or Dataset
                    #print("data2hdf Sequence")
                    if all(isinstance(v, (bool, bytes, complex, float, int, str)) for v in x):
                        dset = group.create_dataset(x_name, data = x) 
                        dset.attrs.update(x_attrs)
                    else:
                        grp = group.create_group(entry_name, track_order=True)
                        for k, v in enumerate(x):
                            keyname = f"{k}"
                            keygroup = group.create_group(keyname, track_order=True)
                            keyattrs = generic_data_attrs(k, "index")
                            keygroup.attrs.update(keyattrs)
                            print("keygroup", keygroup)
                            print("call data2hdf")
                            data2hdf(v, keygroup)
                
                else:
                    raise TypeError(f"Object type {x_type.__name__} not yet supported")
                
            else: # (user-defined class) -> Group 
                pass
            
    except:
        traceback.print_exc()
        
    #print("file", file)
    #print("external", external)
        
    if not external:
        if file:
            file.close
            
#def readHDF5_VigraArray(fileNameOrGroup:typing.Union[str, h5py.Group], 
                        #pathInFile:str, 
                        #order:typing.Optional[str]=None):
    #'''Read an array from an HDF5 file.
    
    #Modified version of vigra.impex.readHDF5() for the new h5py API:
    #A Dataset object does NOT have a "value" attribute in h5py v3.4.0
    
    #Parameters:
    #===========
    
    #'fileNameOrGroup' : str or h5py.Group
        #When a str, it contains a filename
        #When a hy5py.Group this is a group object referring to an already open 
        #HDF5 file, or present in an already open HDF5 file
        
    #'pathInFile' : str is the name of the dataset to be read, including 
    #intermediate groups (when a HDF5 'path' - like string). If 'fileNameOrGroup'
    #is a group object, the path is relative to this group, otherwise it is 
    #relative to the file's root group.

    #If the dataset has an attribute 'axistags', the returned array
    #will have type :class:`~vigra.VigraArray` and will be transposed
    #into the given 'order' ('vigra.VigraArray.defaultOrder'
    #will be used if no order is given).  Otherwise, the returned
    #array is a plain 'numpy.ndarray'. In this case, order='F' will
    #return the array transposed into Fortran order.

    #Requirements: the 'h5py' module must be installed.
    #'''
    ##import h5py
    #file, group, _ = get_file_group_child(fileNameOrGroup)
        
    #try:
        #dataset = group[pathInFile]
        #if not isinstance(dataset, h5py.Dataset):
            #raise IOError("readHDF5(): '%s' is not a dataset" % pathInFile)
        #if hasattr(dataset, "value"):
            ## NOTE: keep this for older h5py API
            #data = dataset.value # <- offending line (cezar.tigaret@gmail.com)
        #else:
            ## NOTE: 2021-10-17 09:38:13
            ## the following returns a numpy array, see:
            ## https://docs.h5py.org/en/latest/high/dataset.html#reading-writing-data
            #data = dataset[()] 
            
        #axistags = dataset.attrs.get('axistags', None)
        #if axistags is not None:
            #data = data.view(vigra.arraytypes.VigraArray)
            #data.axistags = vigra.arraytypes.AxisTags.fromJSON(axistags)
            #if order is None:
                #order = vigra.arraytypes.VigraArray.defaultOrder
            #data = data.transposeToOrder(order)
        #else:
            #if order == 'F':
                #data = data.transpose()
            #elif order not in [None, 'C', 'A']:
                #raise IOError("readHDF5(): unsupported order '%s'" % order)
    #finally:
        ## NOTE: 2021-10-17 09:42:50 Original code
        ## This only closes 'file' when fileNameOrGroup if a HDF5 File object
        ## otherwise does nothing
        #if file is not None:
            #file.close()
    #return data

#def readHDF5_str(fileNameOrGroup, pathInFile):
    #file, group = get_file_group_child(fileNameOrGroup)
        
    #try:
        #dataset = group[pathInFile]
        #if not isinstance(dataset, h5py.Dataset):
            #raise IOError("readHDF5(): '%s' is not a dataset" % pathInFile)
        
        #encoding = group.attrs.get("encoding", "utf-8")

        #data = dataset[()]
        
        #if isinstance(data, bytes):
            #data = data.decode(encoding)
            
    #finally:
        #if file is not None:
            #file.close()
            
    #return data

#def writeHDF5_VigraArray(x, fileNameOrGroup, pathInFile, mode="a", compression=None, chunks=None):
    #"""Variant of vigra.impex.writeHDF5 returning the created h5py.Dataset object
    #Also populates the dataset's dimension scales.
    
    #Modified from vira.impex.writeHDF5 (C) U.Koethe
    #"""
    #if isinstance(fileNameOrGroup, h5py.Group):
        #file = None
        #group = fileNameOrGroup
    #else:
        #file = h5py.File(fileNameOrGroup, mode=mode)
        #group = file['/']
        
    ##dataset = None
        
    #try:
        #levels = pathInFile.split('/')
        #for groupname in levels[:-1]:
            #if groupname == '':
                #continue
            #g = group.get(groupname, default=None)
            #if g is None:
                #group = group.create_group(groupname)
            #elif not isinstance(g, h5py.Group):
                #raise IOError("writeHDF5(): invalid path '%s'" % pathInFile)
            #else:
                #group = g
        #dataset = group.get(levels[-1], default=None)
        #if dataset is not None:
            #if isinstance(dataset, h5py.Dataset):
                #del group[levels[-1]]
            #else:
                #raise IOError("writeHDF5(): cannot replace '%s' because it is not a dataset" % pathInFile)
        #try:
            #x = x.transposeToNumpyOrder()
        #except:
            #pass
        #dataset = group.create_dataset(levels[-1], data=x, compression=compression, chunks=chunks)
        #if hasattr(x, 'axistags'):
            #dataset.attrs['axistags'] = x.axistags.toJSON()
            #axcalgroup = group.create_group("axis")
            #for k, axt in enumerate(x.axistags):
                #dataset.dims[k].label = axt.key
            
            
    #finally:
        #if file is not None:
            #file.close()
            
    #return dataset


    

def writeHDF5_NeoBlock(data, fileNameOrGroup, pathInFile, use_temp_file=True):
    if not isinstance(data, neo.Block):
        raise TypeError(f"Expecting a neo.Block; got {type(data).__name__} instead")
    
    if not isinstance(data.name, str) or len(data.name.strip()) == 0:
        data_name = ".".join([data.__class__.__module__, data.__class__.__name__])
        
    else:
        data_name = data.name
        
    file, group = get_file_group_child(fileNameOrGroup)
    
    try:
        levels = pathInFile.split('/')
        for groupname in levels[:-1]:
            if groupname == '':
                continue
            g = group.get(groupname, default=None)
            if g is None:
                group = group.create_group(groupname)
            elif not isinstance(g, h5py.Group):
                raise IOError("writeHDF5(): invalid path '%s'" % pathInFile)
            else:
                group = g
        
        # NOTE: in the future, check use_temp_file:
        # if use_temp_file:
        # else:
        # write stuff directly through nix (if low-level nix api allows it)
        with tempfile.TemporaryFile() as tmpfile:
            with neo.NixIO(tmpfile) as neonixfile:
                neonixfile.write_block(data)
                if data_name in group:
                    del group[data_name]
                neonixfile.nix_file._h5file.copy(neonixfile.nix_file._h5file['/'], group, name=data_name,
                                                    expand_soft=True, expand_external=True,
                                                    expand_refs=True)
                group[data_name].attrs["python_class"] = ".".join([data.__class__.__module__, data.__class__.__name__])
                
        os.remove(str(tmpfile))
            
    finally:
        if file is not None:
            file.close()

    
def write_dict(data, fileNameOrGroup, pathInFile):
    if not isinstance(data, dict):
        raise TypeError(f"Expecting a dict; got {type(data).__name__} instead")
    
    pass

class NeoContainerHDFIO(object):
    pass
    
class NeoDataObjectHDFIO(object):
    def __init__(self, h5group:h5py.Group, name:str, 
                 compression:typing.Optional[str]="gzip", 
                 chunks:typing.Optional[bool]=None):
        self.group          = h5group
        self.name           = str2symbol(name)
        self.compression    = compression
        self.chunks         = chunks
        
    def get_meta(self, obj:neo.core.dataobject.DataObject) -> tuple: 
        """This must be called at the beginning of every write... method
        """
        if not isinstance(obj, neo.core.dataobject.DataObject):
            raise TypeError(f"Object type {type(obj).__name__} is not supported")
        x_type, x_name, x_attrs = hdf_entry(obj, "")
        
        
        x_meta = dict()
        
        x_meta.update(x_attrs)
        
        x_meta["description"] = make_attr("" if obj.description is None else f"{obj.description}")
        x_meta["file_origin"] = make_attr(f"{obj.file_origin}")

        # NOTE: 2021-11-12 11:25:23
        # below we migrate to using our own custom json codec (see jsonio module)
        # we still keep the pickle fallback until we are satisfied we can do away
        # with it ...
        # any future changes must be brought to the custom codec to accomodate
        # "non-json-able" data
        annot = None
        try:
            annot = json.dumps(obj.annotations, cls=jsonio.CustomEncoder)
        except:
            # unencodable in json:
            try:
                annot = pickle.dumps(obj.annotations) # pickling is a bit cheating ...
            except:
                warnings.warn(f"Cannot encode anotations {obj.annotations}")
            
        if annot is not None:
            x_meta["annotations"] = annot
            
        if hasattr(obj, "mark_type"): 
            # TriggerEvent and DataMark
            x_meta["EventType"] = make_attr(obj.type.name)
            
        if hasattr(obj, "labels"): 
            # neo.Event, TriggerEvent, DataMark, neo.Epoch, and DataZone
            x_meta["labels"] = make_attr(obj.labels)
            
        data_name = getattr(obj, "name", None)
        return x_meta, data_name
    
    def make_axis_scale(self,
                        dset:h5py.Dataset, 
                        axesgroup:h5py.Group,
                        axis:int, 
                        domain_name:str,
                        axis_name:str, 
                        units: pq.Quantity,
                        array_annotations:typing.Optional[ArrayDict]=None,
                        axis_array:typing.Optional[np.ndarray] = None,
                        **kwargs
                        ):
        """
        
        Creates dimension scales attached to the dataset dimension indicated by
        the 'axis' parameter.
        
        dset: h5py.Dataset - the target dataset
        
        axesgroup: h5py.Group where addtional datasets will be written
            This is supposed to reside alongside dset, in dset's parent group.
        
        axis: int: 0 <= axis < obj.ndim
        
        domain_name:str name of the domain correspondiong to the axis e.g. "Time"
            "Potential", "Current" etc
            
        axis_name:str axis name - for 1D signals this is typically the domain 
            name (see 'domain_name') but for 2D signals (e.g. image sequence)
            where both axes are in the same domain, this is an additional qualifier
            (e.g., 'width', 'height')
            
        units: pq.Quantity - this is EITHER:
            obj.units when making scales for a signal's axis , OR:
            obj's domain units when writing scales for a signal's domain axis
                NOTE: In neo object types hierarchy, the 'domain' is the value of 
                'obj.times' property; for strictly neo objects, and for 
                Scipyen's TriggerEvent objects, 'times' is always time (with
                units of pq.s).
                
                In addition, Scipyen defines the following types:
                DataSignal, IrregularlySampledDataSignal, DataZone and DataMark
                
                that implement neo DataObject API without restricting the domain
                to time; the 'times' property of these objects returns a domain
                where the units are NOT necessarily time units!
        
        origin: scalar pq.Quantity; optional, default is None
            This is the value of the signal's 't_start' property, for regularly
            sampled signals neo.AnalogSignal, DataSignal, and neo.ImageSequence
            
        sampling_rate, sampling_period: scalar pq.Quantity 
            only one should be given, as appropriate for the signal
            
            Some signals offers both. Note that in some cases one of them is a 
            stored value, and the other is calculated (dynamic property).
        
        array_annotations: neo.core.dataobject.ArrayDict or None
        
            In most cases this is None. When an ArrayDict, it will be used to 
            populate the attributes of the data set used as axis dimension scale
            
            This is typically useful to provide channel information for axes 
            in the signal domain.
            
            If passed as an ArrayDict, a channel group named "channels" will be
            created in the specific axesgroup, to store the channel information
            used to create dimension scales for the axis
            
        axis_array: numpy array or None
        
        **kwargs: name/value pairs where name: obj attribute name (property) and
            value is a pq.Quantity
            
            The keys are names of properties available for the signal object, e.g.
            such as 't_start', 'sampling_rate', etc.
            
            NOTE: All Quantities must have units compatible with the axis's units
            
        """
        
        # create an empty data set, store in its 'attrs' property
        # NOTE: irregular signals and array-like data objects Epoch & Zone also
        # provide a 'parallel' set of data  - the 'durations' property - we store 
        # that separately as a dimension scale labeled 'durations' attached to
        # this data set (see NOTE: 2021-11-12 16:05:29 and NOTE: 2021-11-12 17:35:27
        # in self.writeDataObject) 
        
        if isinstance(axis_array, np.ndarray):
            axis_dset = axesgroup.create_dataset(axis_name, data = axis_array)
            
        else:
            axis_dset = axesgroup.create_dataset(axis_name, data = h5py.Empty("f"))
            
        axis_dset.attrs["name"] = axis_name
        # these are either signal units, or domain units
        axis_dset.attrs["units"] = units.dimensionality.string 
        
        if isinstance(array_annotations, ArrayDict) and len (array_annotations):
            # CAUTION Only for signal domain!
            channels_group = axesgroup.create_group("channels", track_order=True)
            channels_group.attrs["array_annotations"] = jsonio.dumps(array_annotations, cls=jsonio.CustomEncoder)
            
            #for l in range(x.shape[-1]):
            for l in array_annotations.length:
                if "channel_ids" in array_annotations:
                    channel_id = array_annotations["channel_ids"][l].item()
                else:
                    channel_id = f"{l}"
                    
                if "channel_names" in array_annotations:
                    channel_name = array_annotations["channel_names"][l].item()
                else:
                    channel_name = f"{l}"
                    
                channel_dset = channels_group.create_dataset(f"channel_{l}", data=h5py.Empty("f"))
                channel_dset.attrs["id"] = channel_id
                channel_dset.attrs["name"] = channel_name
                
                for key in array_annotations:
                    if key not in ("channel_ids", "channel_names"):
                        channel_dset.attrs[key] = array_annotations[key][k].item()
                        
                channel_dset.make_scale(f"channel_{l}")
                dset.dims[axis].attach_scale(channel_dset)
                
        for key, val in kwargs.items():
            if not isinstance(val, (pq.Quantity, np.ndarray)):
                raise TypeError(f"Expecting a python quantity or a numpy array; got {type(val).__name__} instead")
            
            if key == "sampling_rate":
                if isinstance(val, pq.Quantity) and not units_convertible(val, 1/units):
                    warnings.warn(f"Writing {key} with units {val.units} incompatible with axis units {1/units}")
            else:
                if isinstance(val, pq.Quantity) and not units_convertible(val, units):
                    warnings.warn(f"Writing {key} with units {val.units} incompatible with axis units {units}")
                    
            if key in ("origin", "t_start"):
                axis_dset.attrs["origin"] = val.magnitude
            else:
                axis_dset.attrs[key] = val.magnitude
                
        axis_dset.make_scale(axis_name)
        dset.dims[axis].attach_scale(axis_dset)
        dset.dims[axis].label = domain_name
        
        return axis_dset

    def make_dimensions_scales(self, obj, data_name, dset):
        data_name = str2symbol(data_name)
        
        axesgrp = self.group.create_group(f"{self.name}_axes", track_order = True)
        
        sig_kind = name_from_unit(obj.units)
        domain_name = obj.domain_name if isinstance(obj, (neo.IrregularlySampledDataSignal, DataSignal)) else "Time"
        
        if isinstance(obj, neo.ImageSequence):
            self.make_axis_scale(dset, axesgrp, 0, domain_name, "frames",
                                 obj.frame_duration.units, 
                                 origin = obj.t_start,
                                 sampling_period=obj.frame_duration,
                                 )
            self.make_axis_scale(dset, axesgrp, 1, sig_kind, "dim 1",
                                 obj.units,
                                 sampling_period = obj.spatial_scale
                                 )
            self.make_axis_scale(dset, axesgrp, 2, sig_kind, "dim 2",
                                 obj.units,
                                 sampling_period = obj.spatial_scale
                                 )

        else:
            
            self.make_axis_scale(dset, axesgrp, 0, sig_kind, "signal_axis", 
                                unit=obj.units,
                                array_annotations=getattr(obj, "array_annotations", None))
            
            
            
            # NOTE 2021-11-12 17:37:15
            # store the 'times' in a dataset ins a separate axis dataset
            # see also NOTE: 2021-11-12 17:35:27  in self.writeDataObject
            if isinstance(obj, neo.IrregularlySampledSignal, IrregularlySampledDataSignal):
                dom_ax_dset = self.make_axis_scale(dset, axesgrp, 1, domain_name, "domain_axis",
                                    units = obj.times.units,
                                    axis_array = obj.times.magnitude)
                
            else:
                dom_ax_dset = self.make_axis_scale(dset, axesgrp, 1, domain_name, "domain_axis",
                                    units = obj.times.units,
                                    origin = obj.t_start,
                                    sampling_rate=obj.sampling_rate)
            
    def writeDataObject(self, obj:neo.core.dataobject.DataObject, x_meta=None, data_name=None) -> h5py.Dataset:
        """Creates a h5py.Dataset with dimension axes, for a DataObject object.
        
        neo.core.dataobject.DataObject objects in Scipyen are:
        
        core.triggerevent.DataMark,
        
        core.triggerevent.TriggerEvent,
        
        core.datazone.DataZone,
        
        neo.Epoch,
        
        neo.SpikeTrain,
        
        neo.BaseObject objects (see writeSignal for details)
        
        NOTE The types defined in the modules in the 'core' subpackage are 
            specific to Scipyen
        
        """
        if any(v is None for v in (x_meta, data_name)):
            x_meta, data_name = self.get_meta(obj)
            
        data_name = str2symbol(data_name)
            
        #print("x_meta", x_meta)
            
        if not isinstance(obj, neo.core.dataobject.DataObject):
            raise TypeError(f"{type(obj).__name__} objects are not supported")
        
        
        if isinstance(obj, neo.ImageSequence):
            dset = self.writeImageSequence(obj, x_meta, data_name)
            
        elif isinstance(obj, neo.core.basesignal.BaseSignal):
            dset = self.writeSignal(obj, x_meta, data_name)
            
        else:
            # NOTE: 2021-11-12 16:05:29
            # Epoch, DataZone, Event, DataMark, TriggerEvent and SpikeTrain all 
            # are effectively 1D signals.
            # in spite of all tempations, the values of the 'durations'
            # property of Epoch and DataZone objects should be stored as attribute
            # to the signal axis dimension scale, and NOT in the main data set
            # (see also NOTE: 2021-11-12 16:03:29)
            data = np.transpose(np.atleast_1d(obj.times.magnitude.flatten()))
            dset = self.group.create_dataset(self.name, data=data)
            
            dset.attrs.update(x_meta)
            dset.attrs["name"] = data_name
            
            axesgrp = self.group.create_group(f"{self.name}_axes", track_order=True)
            
            if isinstance(obj, DataMark):
                aux_name = "Events" if isinstance(obj, TriggerEvent) else "Marks"
                
            elif isinstance(obj, DataZone):
                aux_name = "Extents"
                
            elif isinstance(obj, neo.Epoch):
                aux_name = "Durations"
                
            elif isinstance(obj, neo.SpikeTrain):
                aux_name = "Spikes"
                
            else:
                aux_name = type(obj).__name__.capitalize()
            
            if isinstance(obj, (TriggerEvent, neo.Epoch, neo.Event, neo.SpikeTrain)):
                domain_name = "Times"
            else:
                domain_name = getattr(obj, "domain_name", "domain")
            
            if isinstance(obj, (neo.Epoch, DataZone)):
                self.make_axis_scale(dset, axesgrp, 0, domain_name, aux_name, 
                                    units = obj.units,
                                    axis_array = obj.durations.magnitude)
                
            else:
                kwargs = dict()
                if isinstance(obj, neo.SpikeTrain):
                    kwargs["t_start"] = obj.t_start
                    kwargs["t_stop"] = obj.t_stop
                    kwargs["left_sweep"] = obj.left_sweep
                    kwargs["sampling_rate"] = obj.sampling_rate
                    
                self.make_axis_scale(dset, axesgrp, 0, domain_name, aux_name,
                                     units = obj.units,
                                     **kwargs)
                
            # NOTE: 2021-11-12 18:32:23
            # finally, store the waveforms in the spiketrain
            # By CONVENTION, these are a quantity array 3D (spike K , channel L, 
            # time, T) such that:
            # for each spike (axis 0), in each channel (axis 1) there is a 
            # vector of data over time (axis 2) representing the spike data
            # recorded in channel L for the Kth spike !!!
            #
            # This means that:
            # the element at slice T, column L, row K is a sample from spike K
            # in channel L, at time T:
            #
            # waveforms[K, L, T]
            #
            # and the waveform of the individual spike K in channel L is
            #
            # waveforms[K, L, :]
            #
            # CAUTION: this layout is currently NOT enforced in neo (as of 0.10.0),
            # and the waveforms can be just a simple numpy array (even a 2D one)
            # 
            # for a 2D waveforms data (matrix) a single channel is assumed such
            # that element at column L, row K is a sample of spike K at time L:
            #
            # waveforms[K,L]
            #
            # and the waveform of the individual spike K is:
            #
            # waveforms [K,:]
            #
            
            if isinstance(obj, neo.SpikeTrain):
                waveforms = getattr(obj, "waveforms", None)
                if isinstance(waveforms, np.ndarray) and waveforms.size > 0 and waveforms.ndim in (2,3):
                    if isinstance(waveforms, pq.Quantity):
                        units = waveforms.units
                        waveforms = waveforms.magnitude
                    else:
                        units = pq.dimensionless
                        
                    
                    wave_dset = axesgrp.create_dataset("waveforms", data = waveforms)
                    wave_dset.attrs["units"] = units
                    self.make_axis_scale(wave_set, axesgrp, 0, "Spikes", "spike #",
                                         units=pq.dimensionless)
                    
                    if waveforms.ndim == 2:
                        self.make_axis_scale(wave_set, axesgrp, 1, "Time", name_from_unit(waveform.units),
                                            units=obj.units)
                        
                    else:
                        self.make_axis_scale(wave_set, axesgrp, 1, "Channels", "channel #",
                                            units=pq.dimensionless)
                        
                        self.make_axis_scale(wave_set, axesgrp, 2, "Time", name_from_unit(waveform.units),
                                            units=obj.units)
                    
                
            
        return dset
            
    def writeSignal(self, obj:neo.core.basesignal.BaseSignal, x_meta=None, data_name=None) -> h5py.Dataset:
        """Creates a h5py.Dataset with dimension scales for BaseSignal objects.
        
        neo.core.basesignal.BaseSignal objects in Scipyen are:
        
        neo.AnalogSignal, 
        
        neo.IrregularlySampledSignal,
        
        neo.ImageSequence, 
        
        core.datasignal.DataSignal
        
        core.datasignal.IrregularlySampledDataSignal.
        
        NOTE The types defined in the modules in the 'core' subpackage are 
            specific to Scipyen
        
        """
        if not isinstance(obj, neo.core.basesignal.BaseSignal):
            raise TypeError(f"{type(obj).__name__} objects are not supported")
        
        if any(v is None for v in (x_meta, data_name)):
            x_meta, data_name = self.get_meta(obj)
            
        data_name = str2symbol(data_name)
            
        # NOTE: 2021-11-12 16:03:29
        # in spite of all temptations, I won't store the 'times' values in the 
        # same numpy array as the object values; this is simply because obj
        # can have more than one channel; therefore, the 'times' values will have 
        # to be stored in a separate data set and referenced as dimension scales
        # for the domain axis
        data = np.transpose(obj.magnitude)
        dset = self.group.crate_dataset(self.name, data=data)
        dset.attrs.update(x_meta)
        dset.attrs["name"] = data_name
        
        self.make_dimensions_scales(obj, data_name, dset)
        
        return dset
    
    def writeImageSequence(self, obj:neo.ImageSequence, x_meta=None, data_name=None) -> h5py.Dataset:
        if not isinstance(obj, neo.ImageSequence):
            raise TypeError(f"{type(obj).__name__} objects are not supported")
        
        if any(v is None for v in (x_meta, data_name)):
            x_meta, data_name = self.get_meta(obj)
            
        data_name = str2symbol(data_name)
        
        # NOTE: Three axes: frame, row, column; 
        # of these, 'frame' is in temporal domain (sampling rate/frame duration)
        # row, column (y, x) are in spatial domain
        # so this is effectively like a channel-less vigra array transposed to 
        # numpy order (i.e.the axistags would be 'z','y','x')
        # 
        # e.g. va = VigraArray(data, axistags='xyzc')
        # image_seq = va.dropChannelAxis().transposetoNumpyOrder() =>
        # => axistags are 'zyx'
        
        if isinstance(obj.image_data, list):
            image_data = np.concatenate(obj.image_data, axis=0)
        
        dset = self.group.create_dataset(obj.image_data)
        dset.attrs.update(x_meta)
        dset.attrs["name"] = data_name
        
        self.make_dimensions_scales(obj, data_name, dset)

        return dset
