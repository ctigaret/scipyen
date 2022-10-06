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
        k1d.initExplicitly(left, right, contents)
        
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
# TODO: 2022-10-06 11:24:20
# • a LOT of code refactoring on the reading side
# • deal with neo DataObject array_annotations (how ?!?)
# • what to do with references to segment, unit, in neo.DataObject/Container ?

# wading into pandas writing as HDF5
# see https://stackoverflow.com/questions/30773073/save-pandas-dataframe-using-h5py-for-interoperabilty-with-other-hdf5-readers
# the strategy is to create a structured numpy array
# for multi-level DataFrame objects we use the examples at
# https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.reset_index.html?highlight=reset_index#pandas.DataFrame.reset_index
"""
df0 = pd.DataFrame([('bird', 389.0),
                    ('bird', 24.0),
                    ('mammal', 80.5),
                    ('mammal', np.nan)],
                   index=['falcon', 'parrot', 'lion', 'monkey'],
                   columns=('class', 'max_speed'))

index = pd.MultiIndex.from_tuples([('bird', 'falcon'),
                                    ('bird', 'parrot'),
                                    ('mammal', 'lion'),
                                    ('mammal', 'monkey')],
                                   names=['class', 'name'])
columns = pd.MultiIndex.from_tuples([('speed', 'max'),
                                     ('species', 'type')])
df1 = pd.DataFrame([(389.0, 'fly'),
                   ( 24.0, 'fly'),
                   ( 80.5, 'run'),
                   (np.nan, 'jump')],
                  index=index,
                  columns=columns)

df --> 
         class  max_speed
falcon    bird      389.0
parrot    bird       24.0
lion    mammal       80.5
monkey  mammal        NaN   

df1 --> 
               speed species
                 max    type
class  name                 
bird   falcon  389.0     fly
       parrot   24.0     fly
mammal lion     80.5     run
       monkey    NaN    jump    

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


import os, sys, tempfile, traceback, warnings, numbers, datetime, enum
import types, typing, inspect, functools, itertools, importlib
from functools import (partial, singledispatch)
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
from core.prog import (safeWrapper, signature2Dict,)
from core import prog
from core.traitcontainers import DataBag
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datazone import DataZone
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType, MarkType)
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

from core.datatypes import (TypeEnum,UnitTypes, GENOTYPES, 
                            is_uniform_sequence, is_uniform_collection, 
                            is_namedtuple, is_string,
                            is_numeric_string, is_numeric, 
                            is_convertible_to_numpy_array,
                            NUMPY_STRING_KINDS,
                            )

from core.modelfitting import (FitModel, ModelExpression,)
# from core.triggerevent import (TriggerEvent, TriggerEventType,) # already done above
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

# NOTE: 2021-11-19 09:15:37 guard variable
# during development: set this to True then insert print statements after
# 'if __DEBUG__:' clause
__DEBUG__=False


class HDFDataError(Exception):
    pass

def dataset2string(d:h5py.Dataset):
    return np.atleast_1d(d)[0].decode("utf-8")

def parseAxesGroup(g:h5py.Group):
    # TODO
    pass

def pandasDtype2HF5Dtype(dtype, col, categorical_info:dict=None):
    """Helper function for pandas2Structarray.
    
    Parameters:
    -----------
    dtype: dtype of data frame column
    
    col: pandas Series: the DataFrame column in question
    
    categorical_info: dict; optional default is None
        When present, is will be updated with information about the categorical
        data in column 'col' (if it contains any)
        
    Returns:
    --------
    A tuple: (column name, column dtype) used to define the structured array
        inside pandas2Structarray()
        
    Side effects:
    -------------
    
    Updates the 'categorical_info' dict it is was passed as parameters AND
    'col' contains categorical data.
    
    """
    if isinstance(col.name, tuple):
        col_name = "+".join(col.name)
    else:
        col_name = col.name
        

    try:
        if "object" in str(dtype):
            maxlens = col.dropna().str.len()
            if maxlens.any():
                col_dtype = h5py.string_dtype()
                
            else:
                col_dtype = np.dtype("float64")
        
        elif "category" in str(dtype):
            categories = dtype.categories # pd.Index
            ordered = dtype.ordered
            if "object" in str(categories.dtype):
                catlen = categories.dropna().str.len()
                if catlen.any():
                    col_dtype = h5py.string_dtype()
                else:
                    col_dtype = np.dtype("int64")
                    
            else:
                col_dtype = categories.dtype
                
            if isinstance(categorical_info, dict):
                categorical_info[col_name] = {"categories": np.array(categories, dtype=col_dtype),
                                              "ordered": 1 if dtype.ordered else 0, 
                                             }
        elif "datetime" in str(dtype):
            col_dtype = h5py.string_dtype() # remember to convert datetime data to str!!!
        else:
            col_dtype = dtype
            
        # NOTE: 2021-12-14 11:02:59 for debugging only!
        #print("col.name", col.name, "col_name", col_name, "dtype", dtype, "col_dtype", col_dtype)
        #si = h5py.check_string_dtype(col_dtype)
        #if si is not None:
            #print("\th5py string info", si )
        return col_name, col_dtype
    except:
        print(col.name, dtype, dtype.type, type(col))
        raise
        
def pandas2Structarray(obj):
    """
    Convert a pandas DataFrame object to a numpy structured array.
    
    Parameters:
    -----------
    obj: the pandas data frame or series to convert
    
    Returns:
    --------
    A tuple (sarr, categorical):
        sarr: numpy structured array representation of obj
        categorical: dict, possibly empty, with the names of the categorical 
            columns in 'obj' mapped to a dict with keys:
            
            'categories': numpy array with the categories
            'ordered': bool (whether the category dtype is ordered or not)
            
            NOTE 1:'categories' is populated ONLY if 'obj' contains categorical 
            data. In all other cases it is empty.
            
            When present, this should be used to update the 'attrs' property of 
            the HDF5 dataset generated with the structured array 'sarray'
            
    NOTE 2: About the algorithm.
    
    The conversion proceeds with the following steps:
    
    1) convert 'obj' to a 'reindexed' DataFrame that incorporates the index of 
        the original Pandas object as a column (calls obj.reset_index()); 
    
    2) a structured array dtype is generated based on the dtype of the
    'reindexed' DataFrame, with the following conversions:
    
    2.1) categorical data (Pandas CategoricalDtype) is converted to h5py 
        string dtype ; categories information is stored in the 'categorical'
        dict returned by the function.
        
    2.2) str type data in 'obj' is converted to h5py string dtype
    
    2.3) column multi-indices: the levels are concatenated together in a 
    single str (level names are separated by '+' character) so that they can be
    used as field names in the structured array
    
    2.4) row multi-indices: these are converted to columns in the reindexed data
    frame (generated by the call to obj.reset_index());
    the names of these columns will then appear as <name+> fields in the 
    structured array
    
    WARNING: This algorithm has not been tested extensively and may change in the
    future; any necessary changes will try to preserve the core h5io API, 
    although this it not 100% guaranteed.
    
    """
    
    categorical_info = dict()
    
    # NOTE: 2021-12-13 22:16:37
    # this always generates a DataFrame irrespective of whether 'obj' is a
    # DataFrame or a Series
    obj_rndx = obj.reset_index() # pd.DataFrame

    v = obj_rndx.values # np.ndarray
    obj_dtypes = obj_rndx.dtypes # pd.Series
    #numpy_struct_array_dtypes = [pandasDtype2HF5Dtype(obj_dtypes[col], obj_rndx.loc[:, col], categorical_info) for col in obj_rndx.columns]
    original_obj_dtypes, numpy_struct_array_dtypes = zip(*list((obj_dtypes[col], pandasDtype2HF5Dtype(obj_dtypes[col], obj_rndx.loc[:, col], categorical_info)) for col in obj_rndx.columns))

    #print("numpy_struct_array_dtypes", numpy_struct_array_dtypes)
    dtype = np.dtype(list(numpy_struct_array_dtypes))
    
    sarr = np.zeros(v.shape[0], dtype)
    
    for (i, k) in enumerate(sarr.dtype.names):
        try:
            #print(f"{i}: {k} {obj_dtypes[k]} -> {dtype[k]}")
            if h5py.check_string_dtype(dtype[k]):
                sarr[k] = [str(x) for x in v[:, i]]
            else:
                sarr[k] = v[:, i]
        except:
            print(k, v[:, i])
            raise

    return sarr, categorical_info, original_obj_dtypes
    #return sarr, dtype, categorical_info

def __mangle_name__(s):
    return f"__{s}__"

def __unmangle_name__(s):
    if s.startswith("__") and s.endswith("__"):
        s = s[2:-2]
        
    return s

def __mangle_dict__(d):
    return dict((f"__{k}__", v) for k,v in d.items())

def __unmangle_dict__(d):
    return dict((__unmangle_name__(k), v) for k,v in d.items())

def __check_make_entity_args__(obj, oname, entity_cache):
    target_name, obj_attrs = makeObjAttrs(obj, oname=oname)
    
    if isinstance(oname, str) and len(oname.strip()):
        target_name = oname
        
    if not isinstance(entity_cache, dict):
        entity_cache = dict()
    
    return target_name, obj_attrs, entity_cache

def storeEntityInCache(s:dict, obj:typing.Any, 
                        entity:typing.Union[h5py.Group, h5py.Dataset]):
    if not isinstance(s, dict):
        return
    
    if not isinstance(entity, (h5py.Group, h5py.Dataset)):
        return
    
    s[id(obj)] = entity

def getCachedEntity(cache:dict, obj:typing.Any):
    if not isinstance(cache, dict) or len(cache) == 0:
        return
    
    return cache.get(id(obj), None)
    
def printHdf(v):
    return v if isinstance(v, str) else v.decode() if isinstance(v, bytes) else v[()]

def h5pyIterator(g:h5py.Group, prefix:str='',
                 entity_cache:typing.Optional[dict]=None):
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
            return objectFromEntity(item)
            # yield (path, item, item.attrs)
        elif isinstance(item, h5py.Group): # test for group (go down)
            print(f"Group '{item.name}' attributes:")
            for k,v in item.attrs.items():
                print(f"\t{k}: {printHdf(v)}")
            #pprint(dict(item.attrs))
            yield from h5pyDatasetIterator(item, path)
            
def h5pyDatasetIterator(g:h5py.Group, prefix:str=''):
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
                print(f"\t{k}: {printHdf(v)}")
            #pprint(dict(item.attrs))
            yield from h5pyDatasetIterator(item, path)
            
def exploreHDF(hdf_file:typing.Union[str, h5py.Group]):
    """Traverse all datasets across all groups in HDF5 file.

    See Answer 1 in 
    https://stackoverflow.com/questions/50117513/can-you-view-hdf5-files-in-pycharm
    
    exploreHDF('file.h5')

    /DataSet1 <HDF5 dataset "DataSet1": shape (655559, 260), type "<f4">
    /DataSet2 <HDF5 dataset "DataSet2": shape (22076, 10000), type "<f4">
    /index <HDF5 dataset "index": shape (677635,), type "|V384">
    
    """
    def __print_iter__(path, dset, attrs):
        print(path, f"Dataset '{dset.name}':", dset)
        print("with attributes:")
        for k,v in attrs.items():
            print(f"\t{k}: {printHdf(v)}")
        print("\n")
        try:
            for kd, dim in enumerate(dest.dims):
                print(f"\t\t{k}: {printHdf(v)}, (type: {type(v)}, dtype: {v.dtype.kind})")
            print("\n")
        except:
            print(f"cannot read dimension scales in {dset.name}")
            pass
                
        # print(h5py.h5ds.get_num_scales(dset))
        
        # dimscales = [(k, d) for k, d in enumerate(dset.dims)]
        # if len(dimscales):
        #     print("with dimension scales:")
        #     for kd, dim in dimscales:
        #         print(f"\tdimension {kd}:")
        #         for k,v in dim.items():
        #             print(f"\t\t{k}: {printHdf(v)}, (type: {type(v)}, dtype: {v.dtype.kind})")
        #     print("\n")

    if isinstance(hdf_file, str):
        if os.path.isfile(hdf_file):
            with h5py.File(hdf_file, 'r') as f:
                for (path, dset, attrs) in h5pyDatasetIterator(f):
                    __print_iter__(path, dset, attrs)
                    
    elif isinstance(hdf_file, h5py.Group):
        # file created/opened outside this function; 
        # the caller should manage/close it as they see fit
        for (path, dset, attrs) in h5pyDatasetIterator(hdf_file):
            __print_iter__(path, dset, attrs)

def string2hdf(s):
    if not isinstance(s, str):
        raise TypeError(f"Expecting a str; got {type(s).__name__} instead")
    
    return np.array(s, dtype=h5py.string_dtype())

def makeAttr(x:typing.Optional[typing.Union[str, list, tuple, dict, deque, np.ndarray]]=None):
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
    if x is None:
        return jsonio.dumps(x)
    
    if isinstance(x, str):
        # because np.str_ resolves to str in later versions; but data saved with
        # old numpy API msy still hold scalars of type np.str_
        if isinstance(x, np.str_):
            return str(x)
        
        return x
    
    if isinstance(x, datetime.datetime):
        return str(x)
        
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
        if x.dtype.kind in NUMPY_STRING_KINDS:
            return np.array(x, dtype=h5py.string_dtype(), order="K")
        else:
            return jsonio.dumps(x) 
        
    return x

def makeAttrDict(**kwargs):
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
        ret[k] = makeAttr(v)
            
    return ret

def group2neoContainer(g, target_class):
    # treats Segment, Block, Group
    pass

def group2neoSignal(g, target_class):
    # treats AnalogSignal, IrregularlySampledSignal
    # DataSignal, IrregularlySampledDataSignal
    # ImageSequencene.
    attrs = attr2dict(g.attrs)
    

def group2neoDataObject(g, target_class):
    # treats SpikeTrain, Event, Epoch, TriggerEvent, DataZone
    # the following are delegated to group2neoSignal:
    # AnalgSignal, IrregularlySampledSignal,
    # DataSignal, IrregularlySampledDataSignal
    if neo.core.basesignal.BaseSignal in inspect.getmro(target_class):
        return group2neoSignal(g, target_class)
    
    attrs = attr2dict(g.attrs)
    name = attrs.get("__name__", None)
    units = attrs.get("__units__", pq.s)
    segment = attrs.get("__segment__", None)
    file_origin = attrs.get("__file_origin__", None)
    descripton = attrs.get("__description__", None)
    
    # unit = attrs.get("__unit__", None)
    
    data_set_name = f"{g.name.split('/')[-1]}_data"
    # data_set_name = "".join([g.name.split('/')[-1], "_data"])
    data_set = g.get(data_set_name, None)
    
    axes_group_name = f"{g.name.split('/')[-1]}_axes"
    # axes_group_name = "".join([g.name.split('/')[-1], "_axes"])
    axes_group = g.get(axes_group_name, None)
    
    # for Epoch, Event, DataMark, DataZone, TriggerEvent
    labels_set_name = f"{g.name.split('/')[-1]}_labels"
    labels_set = g.get(labels_set_name, None)
    
    if isinstance(labels_set, hyp5.Dataset):
        labels = objectFromEntity(labels_set)
    else:
        labels = None
    
    
    
    annotations_group_name = f"{g.name.split('/')[-1]}_annotations"
    # annotations_group_name = "".join([g.name.split('/')[-1], "_annotations"])
    annotations_group = g,get(annotations_group_name, None)
    
    if isinstance(annotations_group, h5py.Group):
        annotations = objectFromEntity(annotations_group)
    else:
        annotations = dict()

    times = []
    
    ax0 = dict()
    ax0["t_start"] = 0.*units
    ax0["t_stop"] = None
    ax0["sampling_rate"] = 1.*pq.Hz
    ax0["left_sweep"] = None
    
    ax1 = dict()
    
    
    if isinstance(data_set, h5py.Dataset):
        times = np.array(data_set)
        
        if isinstance(axes_group, h5py.Group):
            # axis 0 is ALWAYS the domain axis
            # axis 1 is ALWAYS the signal axis (or channels axis)
            # for DataObject other than BaseSignal, axis 1 is just a tag-like
            # data - these all have one axis!!
            ax0g = axes_group.get("axis_0", None)
            
            if isinstance(ax0g, h5py.Dataset):
                ax0attrs = attrs2dict(ax0g.attrs)
                ax0["t_stop"] = ax0attrs.get("__end__", None)
                ax0["t_start"] = ax0attrs.get("__origin__", 0.*units)
                ax0["sampling_rate"] = ax0attrs.get("__sampling_rate__", 1.*pq.Hz)
                ax0["left_sweep"] = ax0attrs.get("__left_sweep__", None)
            
            ax1g = axes_group.get("axis_1", None)
            
            if isinstance(ax1g, h5py.Group):
                ax1attrs = attrs2dict(ax1g.attrs)
    
    if target_class == neo.SpikeTrain:
        waveforms_set_name = f"{g.name.split('/')[-1]}_waveforms"
        # waveforms_set_name = "".join([g.name.split('/')[-1], "_waveforms"])
        waveforms_set = g[waveforms_set_name] if waveforms_set_name in g else None
        if isinstance(waveforms_set, h5py.Dataset):
            waveforms  = np.array(waveforms_set)
        else:
            waveforms = None
            
        obj = target_class(times, units=units,  
                           t_start = ax0["t_start"],
                           t_stop = ax0["t_stop"],
                           sampling_rate=ax0["sampling_rate"], 
                           left_sweep=ax0["left_sweep"], 
                           name=name, waveforms=waveforms, 
                           file_origin=file_origin, description = description)
    
    elif target_class == neo.Event:
        pass
    
    elif target_class == neo.Epoch:
        pass
    
    elif target_class == DataZone:
        pass
    
    elif DataMark in inspect.getmro(target_class):
        mark_type = entity.name.split("/")[-1]
        if target_class == TriggerEvent:
            
            obj = TriggerEvent(times=times, labels=labels, units=units,name=name,
                               description=description,file_origin=file_origin,
                               event_type = TriggerEventType[mark_type])
            obj.segment = segment
            return obj
        
        
        pass
    
    obj.annotations.update(annotations)
    obj.segment = segment
    
    return obj
    
        
def group2neo(g:h5py.Group, target_class:type):
    """Reconstructs BaseNeo objects
    """
    # TODO 2022-10-06 13:44:05 factoring out neo object reconstruction
    # call this after checking neo.core.baseneo.BaseNeo is in target's mro, 
    # in the caller
    mro = inspect.getmro(target_class)
    
    if neo.core.dataobject.DataObject in mro:
        return group2neoDataObject(g, target_class)
    elif neo.core.container.Container in mro:
        return group2neoContainer(g, target_class)
    elif target_class == neo.ChannelView:
        pass # TODO
    else:
        raise typeError(f"Don't know how to manage {target_class}")
            
    

def objectFromEntity(entity:typing.Union[h5py.Group, h5py.Dataset]):
    """attempt to round trip of makeHDF5Entity
    """
    # TODO 2022-10-06 11:02:41
    # factor out much of this code for related object types (i.e. with a
    # common package ancestor, such as all neo.DataObject, neo.Container)
    
    # NOTE: 2022-10-06 11:03:49
    # Brief reminder of what makeHDF5Entity does (see also this module docstrin)
    # 
    # Object type                       ->  Entity  Notes
    # ------------------------------------------------------------------------
    # <container> dict, list, deque         Group   The container's elements
    #                                               are stored as children
    #                                               which are either Group
    #                                               or Dataset
    #
    # <PODs> str, bytes, numpy ndarray
    # and numpy structured array            Dataset
    #
    # vigra.Kernel1D                        Dataset (via conversion to numpy
    # vigra.Kernel2D                        array)
    #
    # vigra.VigraArray
    # neo DataObject (AnalogSignal etc)     Group   contains with at least two
    #                                               Datasets, one for the array
    #                                               data, and one for each array
    #                                               axis
    #
    # bytes, bytearray                      Dataset stored by the way of a
    #                                               numpy array
    #                                   
    #                                               If the bytes or bytearray
    #                                               data is ascii then the 
    #                                               dataset has the dtype h5py.string_dtype
                                                
    attrs = attrs2dict(entity.attrs)
    
    
    try:
        type_name = attrs.get("__type_name__", None)
        if type_name is None:
            return None
        python_class = attrs["__python_class__"]
        python_class_comps = python_class.split(".")
        module_name = attrs["__module_name__"]
        module_name_comps = module_name.split(".")
        
        if module_name_comps[0] == "builtins":
            target_class = eval(type_name)
        else:
            try:
                # print(module_name in sys.modules)
                if module_name_comps[0] not in sys.modules:
                    # print(f"importing {module_name_comps[0]} for {module_name}")
                    pymodule = importlib.import_module(module_name_comps[0])
                    
                else:
                    pymodule = sys.modules[module_name_comps[0]]

                # NOTE: 2022-10-05 18:40:53
                # this doesn't work if the module is imported under an alias
                target_class = eval(".".join(python_class_comps[1:]), pymodule.__dict__)
                    
            except:
                # print(f"in entity {entity}")
                # print(f"module_name = {module_name}")
                # print(f"python_class = {python_class}")
                # print(f"type_name = {type_name}")
                traceback.print_exc()
                raise
            
    except:
        print(f"entity: {entity.name}")
        traceback.print_exc()
        raise
    
    # print(f"entity: {entity.name}, target_class: {target_class}")
    
    if isinstance(entity, h5py.Dataset):
        # NOTE: 2022-10-06 11:57:32
        # for now, this code branch applies ONLY to "stand-alone" datasets, and 
        # not to data sets that are children of groups encapsulating more 
        # specialized objects such a neo signal etc
        # hence these will be dealt with in the "group" branch below; don't
        # call objectFromEntity on the children datsets there!
        if entity.shape is None or len(entity.shape) == 0: 
            # no axes imply no Dataset dimscales either
            # most likely a scalar and therefore we attempt to instantiate
            # one as such
            if target_class == bool:
                obj = target_class(entity)
                
            elif target_class == str:
                obj = dataset2string(entity)
                
            elif target_class in [int, float]:
                obj = target_class(entity[()])
                
            elif target_class == pq.Quantity:# or ".".join([target_class.__module__, target_class.__name__]) == "quantities.quantity.Quantity":
                units = attrs.get("__units__", pq.dimensionless)
                data = np.array(entity)
                obj = data*units
            
            # TODO: numpy array, vigra kernels, vigra
                
            else:
                obj = target_class
        else:
            if target_class == pq.Quantity:# or ".".join([target_class.__module__, target_class.__name__]) == "quantities.quantity.Quantity":
                units = attrs.get("__units__", pq.dimensionless)
                data = np.array(entity)
                obj = data*units
            else:
                obj = target_class # for now
            
    else: # entity is a group
        # NOTE: 2022-10-06 13:50:07
        # some specilized arrray-like data objects (e.g. neo DataObject etc)
        # are encapsulatd in h5py Group and store their actual array data in 
        # h5py Dataset children of this Group;
        # therefore, we parse these datasets HERE instead of calling objectFromEntity
        # recursively as we do for Groups storing regular python collections!
        mro = inspect.getmro(target_class)
        # print(f"entity: {entity.name} mro {mro}")
        if dict in mro:
            obj = target_class()
            for k in entity.keys():
                obj[k] = objectFromEntity(entity[k])
                
        elif list in mro:
            obj = target_class()
            for k in entity.keys():
                obj.append(objectFromEntity(entity[k]))
                
        elif ".".join([target_class.__module__, target_class.__name__]) == "neo.core.spiketrain.SpikeTrain":
            # search for a child dataset with name set as this group's name and
            # suffixed with "_data"
            # obj = target_class # for now
            
            data_set_name = "".join([entity.name.split('/')[-1], "_data"])
            data_set = entity[data_set_name] if data_set_name in entity else None
            
            axes_group_name = "".join([entity.name.split('/')[-1], "_axes"])
            axes_group = entity[axes_group_name] if axes_group_name in entity else None
            
            annotations_group_name = "".join([entity.name.split('/')[-1], "_annotations"])
            annotations_group = entity[annotations_group_name] if annotations_group_name in entity else None
            
            waveforms_set_name = "".join([entity.name.split('/')[-1], "_waveforms"])
            waveforms_set = entity[waveforms_set_name] if waveforms_set_name in entity else None
            
            # NOTE: 2022-10-06 09:00:26
            # THIS below is the spike train's name!
            train_name = attrs.get("__name__", None)
            
            # train_unit = attrs.get("__unit__", None) # not sure this even exists in neo API anymore...
                
            # TODO/FIXME: 2022-10-06 09:04:15
            # in this case the segment property is a reference to the neo.Segment
            # where the spike train was originally defined
            #
            # this may be in a different file / data object, in which case
            # that reference sems to have been lost
            # (it is funny, though, as in the pickle version this segment 
            # AND its contents ARE saved (as a serialized copy) into the pickle)
            # which is probably the reason why the pickle containing the 
            # spike train on its owmn is actually LARGER than the pickle 
            #  containing the original segment, see the sxample files in 
            # analysis_Bruker_22i21)
            train_segment = attrs.get("__segment__", None)
            
            # NOTE: 2022-10-06 08:21:35
            # Prepare an empty SpikeTrain in case something goes awry
            # We will construct the real thing below
            #
            # NOTE 2022-10-06 08:28:07: mandatory arguments for the c'tor are:
            # times
            # t_stop
            # units (if neither times nor t_stop is a quantity)
            obj = neo.SpikeTrain([], t_stop = 0*pq.s, units = pq.s)
            # if data_set is None or data_set.shape is None:
                # empty SpikeTrain
                
            if data_set is not None and data_set.shape is not None:
                times = np.array(data_set)
                
                if axes_group is not None:
                    # TODO: 2022-10-06 10:31:02 factor out in parseAxesGroup()
                    # NOTE: 2022-10-06 10:31:07 iterate axes 
                    # NOTE: for non-signal DataObject there is only one axis !!!
                    # NOTE: Furthermore, this axis is empty (acts like a tag)
                    #       but its attrs property contains the relevant data:
                    #       expected to be present there (names mangled with '__'):
                    #       origin -> t_start
                    #       name
                    #       left_sweep
                    #       sampling_rate
                    #       units
                    #       end ->t_stop
                    #       
                    #       The following are NOT used by SpikeTrain:
                    #       key -> str
                    #       
                    #       The following SpikeTrain properties are NOT stored
                    #       in h5 data but we check for them:
                    #
                    #       sort (bool)
                    #
                    # NOTE: 2022-10-06 10:32:52 
                    # general comment for DataObjects axis groups:
                    # some of the members of the axis data set attributes are
                    # redundant with some fo these being reserved for later 
                    # (unspecified) use e.g. "__name__" , "__units__", etc, and 
                    # their information can sometimes be inferred from the concrete 
                    # type of DataObject
                    #
                    # Also, NOTE that properties like "units" are stored in attrs
                    # as json objects (hence why the use of attrs2dict is recommended
                    # instead of dict(attrs))
                    #
                    if "axis_0" in axes_group:
                        axis_set = axes_group["axis_0"]
                        
                        # NOTE: 2022-10-06 08:23:37
                        # this none below should do most of the conversions for us
                        #
                        axis_attributes = attrs2dict(axis_set.attrs)
                        t_stop = axis_attributes["__end__"] # this one MUST be present
                        t_start = axis_attributes.get("__origin__", 0.)
                        sampling_rate = axis_attributes.get("__sampling_rate__", None)
                        units = axis_attributes.get("__units__", pq.s) # just make sure we have units
                        name = axis_attributes.get("__name__",None)
                        left_sweep = axis_attributes.get("__left_sweep__", None)
                        key = axis_attributes.get("__key__", "")
                            
                        file_origin = axis_attributes.get("__file_origin__", None)
                        description = axis_attributes.get("__description__", None)
                        
                    else:
                        # NOTE: 2022-10-06 08:30:25
                        # supply reasonable defaults
                        units = pq.s
                        t_start = times[0]
                        t_stop = times[-1] # by default
                        name = None
                        key = ""
                        sampling_rate = 1.*pq.Hz
                        left_sweep = None
                        file_origin = None
                        description = None
                        
                if annotations_group is not None:
                    train_annotations = objectFromEntity(annotations_group)
                else:
                    train_annotations = dict()
            
                if waveforms_set is not None:
                    waveforms = np.array(waveforms_set)
                else:
                    waveforms = None
                    
                obj = neo.SpikeTrain(times, t_stop, units=units, t_start=t_start,
                                     sampling_rate=sampling_rate, 
                                     left_sweep=left_sweep, name=train_name,
                                     waveforms=waveforms, file_origin=file_origin,
                                     description = description)  
                
                # obj.unit = train_unit
                obj.segment = train_segment
                obj.annotations.update(train_annotations) # safer that via c'tor above
                
        # elif "neo.core.analogsignal.AnalogSignal" in python_class:
        elif ".".join([target_class.__module__, target_class.__name__]) == "neo.core.analogsignal.AnalogSignal":
            # NOTE: 2022-10-06 09:46:42
            # as all neo DataObjects these re also stored as a Group
            # contrary to SpikeTrain we don't have a waveform data set
            data_set_name = "".join([entity.name.split('/')[-1], "_data"])
            data_set = entity[data_set_name] if data_set_name in entity else None
            
            axes_group_name = "".join([entity.name.split('/')[-1], "_axes"])
            axes_group = entity[axes_group_name] if axes_group_name in entity else None
            
            annotations_group_name = "".join([entity.name.split('/')[-1], "_annotations"])
            annotations_group = entity[annotations_group_name] if annotations_group_name in entity else None
            
            signal_name = attrs.get("__name__", None)
            signal_segment = attrs.get("__segment__", None)
            description = attrs.get("__description__", None)
            
            if signal_segment in ["__ref__", "null"]:
                # FIXME: see TODO/FIXME: 2022-10-06 09:04:15
                signal_segment = None
                
            units = attrs.get("__units__", pq.s)
            name = attrs.get("__name__", "")
            file_origin = attrs.get("__file_origin__", None)
            description = attrs.get("__description__", None)
            signal_segment = attrs.get("__segment__", None)
            
            # prepare default; mandatory args are:
            # signal (e.g. empty array-like)
            # units
            # sampling rate
            obj = neo.AnalogSignal([], units = units, sampling_rate = 1*pq.Hz)
            
            if data_set is not None and data_set.shape is not None:
                # NOTE: 2022-10-06 10:48:24
                # some of the attrs of data_set are redundant since they 
                # are also present in `entity.attrs` or in the data_set.attrs
                # • __name__  = signal's name
                # • __units__ = signal's units
                # • __description__ = signal's description
                signal_data = np.array(data_set)
                
                if axes_group is not None:
                    # NOTE: see also:
                    # • TODO: 2022-10-06 10:31:02
                    # • NOTE: 2022-10-06 10:31:07
                    # • NOTE: 2022-10-06 10:32:52
                    # we expect two axes
                    if "axis_0" in axes_group:
                        axis_0_set = axes_group["axis_0"] # a Dataset for axis 0
                        # in the case of AnalogSignal this is the time axis
                        axis_0_attrs = attrs2dict(axis_0_set.attrs)
                        
                        t_start = axis_0_attrs.get("__origin__", 0.*pq.s)
                        sampling_rate = axis_0_attrs.get("__sampling_rate__", 1.*pq.Hz)
                    else:
                        t_start = 0.*pq.s
                        sampling_rate = 1.*pq.Hz
                    # axis_1_set = axes_group["axis_1"] #  the channels axis
                    # NOTE: 2022-10-06 10:54:31 this is an empty axis (sort of a
                    # pseudo-tag)
                    # redundant atrs members are (see entity.attrs)
                    # • name
                    # • units
                    #
                    # TODO: revisit this with real analog signals where there
                    # may be channel info
                    
                else:
                    t_start = 0*pq.s
                    sampling_rate = 1.*pq.Hz
                    
                if annotations_group is not None:
                    signal_annotations = objectFromEntity(annotations_group)
                else:
                    signal_annotations = dict()
                    
                    
                obj = neo.AnalogSignal(signal_data, units=units, t_start=t_start,
                                       sampling_rate=sampling_rate, name=name,
                                       description=description, file_origin=file_origin)
                
                obj.annotations.update(signal_annotations)
                
                obj.segment = signal_segment
                    
            
            
        else:
            obj = target_class # for now

    return obj

# def generateObject(klass, )
    
def attrs2dict(attrs:h5py.AttributeManager):
    """Generates a dict object from a h5py Group or Dataset 'attrs' property.
    
    Althogh one can simply call `dict(attrs)` or `dict(attrs.items())`, 
    this function also decodes the items of `attrs` to reverse the actions of 
    makeObjAttrs and makeDataTypeAttrs.
    
    This is important for those obkects that were stored as a json string
    inside attrs.
    
    Not exactly a complete roundtrip...
    
    Must be used with caution !!!
    """
    ret = dict()
    for k,v in attrs.items():
        # NOTE: 2021-11-10 12:47:52
        # FIXME / TODO
        try:
            if isinstance(v, str) and v == "null":
                v = None
            
            elif hasattr(v, "dtype"):
                if v.dtype == h5py.string_dtype():
                    v = list(v)
                    # v = v.decode("utf-8")
                    # v = np.array(v, dtype=np.dtype("U"))[()]
                    
                elif v.dtype.kind == "O":
                    if type(v[()]) == bytes:
                        v = v[()].decode()
                        
                    else:
                        v = v[()]
                        
                else:
                    if type(v) == bytes:
                        v = v.decode()
                        
                    # else:
                        # v = v[()]
                    # v = v[()]
                    
                if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
                    v = jsonio.loads(v)
                    
            elif isinstance(v, str):
                if v.startswith("{") and v.endswith("}"):
                    v = jsonio.loads(v)
                    
        except:
            print(f"k = {k} v = {v} v.dtype = {v.dtype}")
            traceback.print_exc()
            
        ret[k] = v
        
    return ret
                
def makeDataTypeAttrs(data):
    if not isinstance(data, type):
        data = type(data)

    attrs = dict()
    
    attrs["__type_name__"] = data.__name__
    attrs["__module_name__"] = data.__module__
    attrs["__python_class__"] = ".".join([data.__module__, data.__name__])
    
    #print("attrs", attrs)
    
    if data.__module__ != "builtins":
        if is_namedtuple(data):
            fields_list = list(f for f in data._fields)
            attrs["__python_class_def__"] = f"{data.__name__} = collections.namedtuple({data.__name__}, {list(fields_list)})"
        else:
            attrs["__python_class_def__"] = prog.class_def(data)
    
        if hasattr(data, "__new__"):
            sig_dict = signature2Dict(getattr(data, "__new__"))
            attrs["__python_new__"] = jsonio.dumps(sig_dict)
            
        if hasattr(data, "__init__"):
            init_dict = signature2Dict(getattr(data, "__init__"))
            attrs["__python_init__"] = jsonio.dumps(init_dict)
        
    return makeAttrDict(**attrs)
        
def getFileGroupChild(fileNameOrGroup:typing.Union[str, h5py.Group],
                       pathInFile:typing.Optional[str] = None, 
                       mode:typing.Optional[str]=None) -> typing.Tuple[typing.Optional[h5py.File], h5py.Group, typing.Optional[str]]:
    """Common tool for coherent syntax of h5io read/write functions.
    Inspired from vigra.impex.readHDF5/writeHDF5, (c) U.Koethe
    """
    if mode is None or not isinstance(mode, str) or len(mode.strip()) == 0:
        mode = "r"
        
    external = False
    print("getFileGroupChild fileNameOrGroup", fileNameOrGroup, "pathInFile", pathInFile, "mode", mode)
    
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

    
def parseFunc(f):
    sig = inspect.signature(f)
    
    def __identify__(x):
        if x is None:
            return str(x)
        
        elif isinstance(x, type):
            return x.__name__
        
        else:
            return {"__type__": type(x).__name__, "__value__": x}
        
    
    return dict((p_name, {"__kind__":p.kind.name, 
                          "__default__": __identify__(p.default),
                          "__annotation__": __identify__(p.annotation),
                          }) for p_name, p in sig.parameters.items())

def makeEntryName(obj):
    obj_name = getattr(obj, "name", None)
    if not isinstance(obj_name, str) or len(obj_name.strip()) == 0:
        obj_name = str2symbol(obj) if isinstance(obj, str) else ""
    
    if len(obj_name.strip()):
        return obj_name
    
    return type(obj).__name__
    
def makeObjAttrs(obj:typing.Any, oname:typing.Optional[str]=None):
    """Generates name and attrs dict for a HDF5 entity
    
    Parameters:
    ----------
    
    obj:python object
    
    oname: str, optional, default is None
        the name of the object (HDF5 Group or Dataset) to which the attributes
        will be attached
    
    """
    #print(type(obj))
    if isinstance(obj, prog.CALLABLE_TYPES):
        return makeAttrDict (__function_or_method__ = jsonio.dumps(prog.signature2Dict(obj)))
    
    if obj is None:
        return makeEntryName(obj), {}
    
    if not isinstance(oname, str) or len(oname.strip()) == 0:
        oname = getattr(obj, "name", "")
        
    obj_attrs = makeDataTypeAttrs(obj)
    
    as_group = isinstance(obj, (collections.abc.Iterable, neo.core.container.Container)) and not isinstance(obj, (str, bytes, bytearray, np.ndarray))
    
    if not as_group:
        obj_attrs.update(makeDatasetAttrs(obj))
    else:
        obj_attrs["__name__"] = makeAttr(oname)
        
    target_name = makeEntryName(obj)
    
    return target_name, obj_attrs

@singledispatch
def makeDatasetAttrs(obj):
    """Generates an attribute dict for HDF5 datasets.
    The result is passed through makeAttrDict before mergins into a HDF5 
    Dataset attrs property.
    
    For array-like object types such as those in the neo hierarchy, VigraArrays,
    vigra filter Kernel1D/2D, pq.Quantity, this is used for the actual 
    numeric data of the object, NOT for its axes.
    
    Key names are prefixed and suffixed with '__'
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
    if isinstance(obj, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
        # NOTE: 2021-11-18 12:31:59
        # in vigranumpy all kernels are float ?
        return makeAttrDict(__dtype__ = jsonio.dtype2JSON(np.dtype(float)))
        
    return dict()

@makeDatasetAttrs.register(np.ndarray)
def _(obj):
    attrs = dict()
    dtype = obj.dtype
    fields = dtype.fields
    attrs["__dtype__"] = jsonio.dtype2JSON(obj.dtype)
    if fields is not None: # structured array or recarray; type is in makeDataTypeAttrs
        attrs["__dtype_fields__"] = list(f for f in obj.dtype.fields)
    
    return makeAttrDict(**attrs)

@makeDatasetAttrs.register(pq.Quantity)
def _(obj):
    attrs = dict()
    attrs["__dtype__"] = jsonio.dtype2JSON(obj.dtype)
    attrs["__units__"] = obj.units
    
    return makeAttrDict(**attrs)

@makeDatasetAttrs.register(neo.core.dataobject.DataObject)
def _(obj):
    ret = {"__name__": obj.name,
           "__units__":obj.units,
           "__segment__": "__ref__" if obj.segment else None
           }
    
    if hasattr(obj, "rec_datetime"):
        ret["__rec_datetime__"] = str(obj.rec_datetime)
        
    if isinstance(obj, (neo.core.basesignal.BaseSignal)):
        ret.update(
                    {"__file_origin__": obj.file_origin,
                     "__description__": obj.description,
                    }
                    )
    if isinstance(obj, neo.SpikeTrain):
        ret["__unit__"] = obj.unit
    
    return makeAttrDict(**ret)

@makeDatasetAttrs.register(vigra.VigraArray)
def _(obj):
   return makeAttrDict(__dtype__ = jsonio.dtype2JSON(obj.dtype), 
                         __axistags__ = obj.axistags.toJSON())

@singledispatch
def makeAxisDict(obj, axisindex:int):
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
    
    NOTE 3: Key names are prefixed and suffixed with "__"
    ============================================================================
    Mandatory key/value pairs 
    
    Key name        Object type                     type: value
                                                    semantics
                                                    specific storage
    ============================================================================
    key             VigraArray                      str:                     
                                                    AxisInfo.key   
                                         
                    vigra.filters.Kernel1D          str:
                                                    "s" for axis 0
                                                    "v" for axis 1
    
                    vigra.filters.Kernel2D          str:
                                                    "s" for axis 0
                                                    "c" for axis 1
                                                    "v" for axis 2

                    NOTE: vigra filters Kernel1D and 2D are converted to
                    numpy arrays with 2 and 3 dimensions, respectively.
                    See imaging.vigrautils.kernel2array() for details.
    
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
    
    # NOTE: 2021-11-18 17:34:57
    # not via axis_dict because of dtype mangling -> moved to makeDataset
    domain          IrregularlySampledSignal,       1D ndarray float dtype:
                    IrregularlySampledDataSignal    this is signal.times
                                                    property 
                                                    stored AS the axis dataset;
                                                    only for axis 0
                                                    
                    Epoch                           1D ndarray, float dtype:
                    DataZone                        this is signal.durations
                                                    stored AS the axis dataset;
                                                    only for axis 0
                            
    # NOTE: 2021-11-18 17:34:57
    # NOTE: 2021-11-18 17:34:57
    labels          Event,                          1d ndarray dtype <U
                    DataMark                        signal.labels property
                    Epoch                           stored as axis_labels
                    DataZone                        dataset alongside the axis
                                                    dataset;
                                                    
                                                    
    # NOTE: 2021-11-18 17:34:57
    # not via axis_dict because of dtype mangling -> moved to makeDataset
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
    raise NotImplementedError(f"makeAxisDict: {type(obj).__name__} objects are not yet supported")

@makeAxisDict.register(vigra.VigraArray)
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
    
    data = dict((f"__{k}__", v) for k,v in axiscal.data.items()) # axiscal.data
    
    return makeAttrDict(__axinfo_key__            = axisinfo.key,
                          __axinfo_typeFlags__      = axisinfo.typeFlags,
                          __axinfo_description__    = axisinfo.description, 
                          __axinfo_resolution__     = axisinfo.resolution, 
                          **data)
    
@makeAxisDict.register(vigra.AxisTags)
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
    
    data = dict((f"__{k}__", v) for k,v in axiscal.data.items()) # axiscal.data
    
    return makeAttrDict(__axinfo_key__            = axisinfo.key,
                          __axinfo_typFlags__       = axisinfo.typeFlags,
                          __axinfo_description__    = axisinfo.description, 
                          __axinfo_resolution__     = axisinfo.resolution,
                          **data)

@makeAxisDict.register(neo.core.dataobject.DataObject)
def _(obj, axisindex:int):
    # axis 0 = domain axis (e.g. times)
    # axis 1 = channel axis (may be singleton for a single-channel signal)
    if isinstance(axisindex, int):
        if axisindex < 0 or axisindex >= obj.ndim:
            raise ValueError(f"Invalid axisindex {axisindex} for {type(obj).__name__} object")
        
    else:
        raise TypeError(f"'axisindex' expected to be an int; got {type(axisindex).__name__} instead")
    
    seed = dict()
    #name = name_from_unit(obj.times.units) if axisindex == 0 else name_from_unit(obj.units)
    #print("name", name)
    seed["__name__"] = name_from_unit(obj.times.units) if axisindex == 0 else name_from_unit(obj.units)
    #print("seed: __name__", seed["__name__"])
    seed["__key__"] = name_from_unit(obj.times.units, True) if axisindex == 0 else name_from_unit(obj.units, True)
    #print("seed: __key__", seed["__key__"])
    #seed["__key__"] = name_from_unit(obj.times.units) if axisindex == 0 else name_from_unit(obj.units)
    #seed["__name__"] = seed["__key__"] if axisindex == 0 else getattr(obj, "name", type(obj).__name__)
    seed["__units__"] = obj.times.units if axisindex == 0 else obj.units
    
    if isinstance(obj, neo.core.basesignal.BaseSignal):
        if axisindex == 1: 
            # channels axis
            #  NOTE: 2021-11-17 13:41:04
            # array annotations SHOULD be empty for non-signals
            # ImageSequence does NOT have array_annotations member
            array_annotations = getattr(obj,"array_annotations", None)
            if isinstance(array_annotations, ArrayDict) and len(array_annotations): # this is the number of fields NOT channels!
                # NOTE: skip silently is length different for obj size on axis 1
                if array_annotations.length == obj.shape[1]:
                    for field, value in array_annotations.items():
                        seed[__mangle_name__(field)] = value
        
        ret = makeNeoSignalAxisDict(obj, axisindex)
        
    else: # data objects that are NOT base signals; these include SpikeTrain!!!
        array_annotations = getattr(obj,"array_annotations", None)
        if isinstance(array_annotations, ArrayDict) and len(array_annotations): # this is the number of fields NOT channels!
            # NOTE: skip silently is length different for obj size on axis 1
            if array_annotations.length == obj.shape[1]:
                for field, value in array_annotations.items():
                    seed[__mangle_name__(field)] = value
                    
        ret = makeNeoDataAxisDict(obj, axisindex)
        
    seed.update(ret)
    
    return makeAttrDict(**seed)

@makeAxisDict.register(vigra.filters.Kernel1D)
def _(obj, axisindex):
    if axisindex < 0 or axisindex >= 2:
        raise ValueError(f"Invalid axis index {axisindex}")
    
    ret = dict()
    ret["__key__"] = "x" if axisindex == 0 else "v"
    ret["__name__"] = "x" if axisindex == 0 else "values"
    
    return ret
    
@makeAxisDict.register(vigra.filters.Kernel2D)
def _(obj, axisindex):
    if axisindex < 0 or axisindex >= 3:
        raise ValueError(f"Invalid axis index {axisindex}")
    ret = dict()
    ret["__key__"] = "x" if axisindex == 0 else "y" if axisindex == 1 else "v"
    ret["__name__"] = "x" if axisindex == 0 else "y" if axisindex == 1 else "values"
    
    return {"__key__": "s"} if axisindex == 0 else {"__key__":"c"} if axisindex == 1 else {"__key__":"v"}
        
@singledispatch        
def makeNeoSignalAxisDict(obj, axisindex:int):
    """See make makeAxisDict for details
    """
    raise NotImplementedError(f"makeNeoSignalAxisDict: {type(obj).__name__} objects are not supported")

@makeNeoSignalAxisDict.register(neo.AnalogSignal)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        # domain axis
        ret["__origin__"]           = obj.t_start
        ret["__sampling_rate__"]    = obj.sampling_rate
        ret["__sampling_period__"]  = obj.sampling_period

    return ret

@makeNeoSignalAxisDict.register(DataSignal)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        # domain axis
        ret["__origin__"]           = obj.t_start
        ret["__sampling_rate__"]    = obj.sampling_rate
        ret["__sampling_period__"]  = obj.sampling_period

    return ret

@makeNeoSignalAxisDict.register(neo.IrregularlySampledSignal)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["__origin__"]           = obj.t_start
        #ret["__domain__"] = obj.times
        
    return ret

@makeNeoSignalAxisDict.register(IrregularlySampledDataSignal)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["__origin__"]           = obj.t_start
        #ret["__domain__"] = obj.times
        
    return ret

@makeNeoSignalAxisDict.register(neo.ImageSequence)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["__key__"] = "t"
        ret["__name__"] = "frames"
        ret["__units__"] = obj.t_start.units
        ret["__origin__"] = obj.t_start
        ret["__sampling_rate__"] = obj.sampling_rate
        
    else: # axis 1 or 2
        ret["__key__"] = "s"
        ret["__name__"] = "height" if axisindex == 1 else "width"
        ret["__spatial_scale__"] = obj.spatial_scale
        

@singledispatch
def makeNeoDataAxisDict(obj, axisindex):
    raise NotImplementedError(f"makeNeoDataAxisDict: {type(obj).__name__} objects are not supported")
    
@makeNeoDataAxisDict.register(neo.SpikeTrain)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["__origin__"] = obj.t_start
        ret["__left_sweep__"] = obj.left_sweep
        #ret["__waveforms__"] = obj.waveforms
        ret["__end__"] = obj.t_stop
        waveforms = getattr(obj, "waveforms", None)
        if isinstance(waveforms, np.ndarray) and waveforms.size > 0:
            ret["__sampling_rate__"] = obj.sampling_rate
        
    return ret

@makeNeoDataAxisDict.register(neo.Event)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["__labels__"] = obj.labels
    return ret

@makeNeoDataAxisDict.register(DataMark)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["__labels__"] = obj.labels
    return ret

@makeNeoDataAxisDict.register(neo.Epoch)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["__labels__"] = obj.labels
        ret["__durations__"] = obj.durations
    return ret

@makeNeoDataAxisDict.register(DataZone)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["__labels__"] = obj.labels
        ret["__durations__"] = obj.durations
    return ret

@safeWrapper
def makeAxisScale(obj,
                    dset:h5py.Dataset, 
                    axesgroup:h5py.Group,
                    dimindex:int,
                    axisdict:dict,
                    compression:str="gzip",
                    chunks:bool=None,
                    track_order=True)-> h5py.Dataset:
    """
    Attaches a dimension scale for a specific dimension in a HDF5 Dataset.
    
    The dimension scale is constructed from an axis data set in the 
    HDF5 group 'axesgroup', initialized with the information contained in 
    'axisdict', then attached as a scale to the dimension 'dimindex' of the
    HDF5 Dataset 'dset'.
    
    Parameters:
    -----------
    
    obj: object stored in the 'dset' dataset
    
    dset: h5py.Dataset - the target dataset
    
    axesgroup: h5py.Group - target group where addtional axis-related datasets
        will be written, when necessary
    
    dimindex: int; index of the dset's dimension scale: 
        0 <= dimindex < len(dset.dims)
        
    axisdict: a dictionary with key:str mapped to values: objects usable as
        attributes for the axis data set (see makeAxisDict)
        
    compression:str (optional, default is "gzip"): compression algorithm for 
        the axis and the auxiliary data sets
        
    chunks:bool (optional, default is None): When True, the axis and auxiliary
        data sets are written in chunks.
        
        
    Returns:
    --------
    HDF5 Dataset: The newly-created axis data set.
        
    """
    
    # create an empty data set, store in its 'attrs' property
    # NOTE: irregular signals and array-like data objects Epoch & Zone also
    # provide a 'parallel' set of data  - the 'durations' property - we store 
    # that separately as a dimension scale labeled 'durations' attached to
    # this data set (see NOTE: 2021-11-12 16:05:29 and NOTE: 2021-11-12 17:35:27
    # in self.writeDataObject) 
    
    axis_dict = makeAxisDict(obj, dimindex)
    
    axis_dset_name = f"axis_{dimindex}"
    
    if isinstance(obj, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal,
                        neo.Epoch, DataZone, neo.Event, DataMark)) and obj.size > 0:
        axis_dset = makeHDF5Entity(obj.times, axesgroup,
                                     name = axis_dset_name,
                                     compression = compression, 
                                     chunks = chunks,
                                     track_order = track_order)
    else:
        axis_dset = axesgroup.create_dataset(axis_dset_name, data=h5py.Empty("f"))
        
    axis_dset.attrs.update(axis_dict)
    axis_dset.make_scale(axis_dict["__name__"])
    dset.dims[dimindex].attach_scale(axis_dset)
    dset.dims[dimindex].label = axis_dict["__name__"]
    
    return axis_dset

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

@safeWrapper
def makeHDF5Entity(obj, group:h5py.Group,
                    name:typing.Optional[str]=None,
                    oname:typing.Optional[str]=None,
                    compression:typing.Optional[str]="gzip",
                    chunks:typing.Optional[bool]=None,
                    track_order:typing.Optional[bool] = True, 
                    entity_cache:typing.Optional[dict]=None,
                    **kwargs) -> typing.Union[h5py.Group, h5py.Dataset]:
    """
    HDF5 entity  maker for Python objects.
    Generates a HDF5 Group or Dataset (NOTE: a HDF5 File has overlapping API
    with HDF5 Group).
    
    Parameters:
    -----------
    obj: object A python object to be stored as a HDF5 entity (Group or Dataset)
    
    group: h5py.Group The HDF5 parent group, where obj will be stored as a HDF5 
        entity 
        NOTE: this can be a h5py.File as well, opened for writing
        name: str, optional default is None:
            name of the entity which will contain obj data and will be created by
            this function.
            
        oname: str, optional, default is None:
            typically, the name (symbol) bound to the obj in the caller namespace,
            OR obj's `name` property (if present)
            
        compression: str, chunks: bool - parameters passed on to code that 
            creates HDF5 Dataset entities; both optional with default being None
            
        track_order:bool - flags passed on the code creating HDF5 Group entities
            optional, default is True
            
        entity_cache: dict, optional default is None
            When given it maps Python objects to the HDF5 entities that were 
                created for these objects (technically, maps object id values to
                entiti id values).
                Useful to track 'stored' objects in the HDF5 hierarchy to avoid
                storage duplication for data in 'obj', which otherwise has already
                generated an HDF5 entity
        
    Var-keyword parameters - used in special circumstances
    ------------------------------------------------------
    parent_neo_container: tuple(object, entity) where 'object' is a neo Container
        instance (e.g., Block, Segment) and 'entity' is the HDF5 entity (typically
        a h5py Group) created for the Container instance; optional, default is None.
        
        Used when storing neo DataObjects, such as AnalogSignal, etc, which hold a
        reference to their 'parent' neo container (e.g. the 'segment' property
        of an analog signal is a reference to the neo.Segment where the signal
        is stored). 
        
        Without it, the entity maker (for example for an analog signal), will
        generate an entity for the signals' container bound to the 'segment' 
        property. However, as this occurs _while_ the code making the entity for 
        the parent container is still running, the code will result in infinite 
        recursion and will crash the Python interpreter.
        
        
    NOTE: 2021-12-12 12:12:25
    Objects are stored in 'group', typically as a child Dataset, or as a child 
    Group containing one or more data sets. These child entities are generated 
    by delegating to 'makeHDF5Group' and 'makeHDF5Dataset', respectively, 
    according to the following general rule:
    
    * a container object (e.g., dict, list, deque) generates a child group 
        (via 'makeHDF5Group'), with the container's elements stored inside the 
        newly generated child group (either as a data set, or as a nested group,
        according to the object's type AND the rules described here)    
    
    * str, bytes, bytearray, numpy ndarray (including numpy structured array) 
        objects are stored directly as data sets (via makeHDF5Dataset)
    
    Object type specific information is stored in the 'attrs' dictionary of
    the child group or data set.
    
    A few types require special handling, hence they are EXCEPTIONS from this
    rule. 
    
    Kernel1D, Kernel2D (vigra.filters):
        These are converted to numpy array (see vigrautils.kernel2array) then 
        stored as child Dataset.
      
    VigraArray (vigra) and neo's DataObjects (e.g., AnalogSignal, etc), are ALL
        stored as a Group containing at least two Dataset objects:
        1. a Dataset that stores the main data  
        2. a Dataset for each axis, that stores the information for the 
        correspondong array axis.
      
        The main data set stores the (typically, numeric) array data of the 
        object.
      
        The axes data sets are either empty (for VigraArrays and neo-like 
        regularly sampled signals) or contain 'domain' information (e.g., 
        'times') for neo-like ireegularly samples signals, neo Epoch- and 
        neo.Event-like objects.
      
        In addition, the axis data sets 'attrs' contain information about axis
        calibration, name, units (VigraArrays and neo-like data objects) and 
        axistags (for VigraArrays).
      
    neo's ChannelView: 
        stored as a group + child data set (via makeHDF5Dataset)
    
    Python's Enum types:
        stored directly as data sets with h5py enum dtype 
      
    Pandas DataFrame and Series objects:
        These objects types are converted to a structured array first (see
        'pandas2Structarray' function); therefore, they will be stpred as a
        group, and the data itself as a data set generated on the structured 
        array
        Categorical data information, when present, is also stored as a nested
        child group in 'group' (named "categorical_info").
        
    Numpy array (other than Python Quantity, VigraArray, neo dataobjects), 
        objects of the Python iterable types: str, bytes, bytearray, and 
        Python homogeneous sequences (i.e., with ALL elements of the same scalar 
        type or str):
      strored as data set via makeHDF5Dataset
    
    Python iterable and neo's Container objects (e.g. Block, Segment, etc)
      stored as a group via makeHDF5Group
      
    Objects that define their own 'makeHDF5Entity' method are stored as defined
    by the method code. 
      
    """
    from imaging import vigrautils as vu
    #print("makeHDF5Entity:", type(obj))
    entity_factory_method = getattr(obj, "makeHDF5Entity", None)
    if entity_factory_method is None:
        entity_factory_method = kwargs.pop("makeHDF5Entity", None)
        
    if inspect.ismethod(entity_factory_method):
        target_name, obj_attrs = makeObjAttrs(obj, oname=oname)
            
        if isinstance(name, str) and len(name.strip()):
            target_name = name
            
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity
            return cached_entity
        
        return entity_factory_method(group, name, oname, compression,chunks,track_order,entity_cache)

    if not isinstance(group, h5py.Group):
        raise TypeError(f"'group' expected to be a h5py.Group (or h5py.File); got {type(group).__name__} instead")

    target_name, obj_attrs = makeObjAttrs(obj, oname=oname)
    
    if isinstance(name, str) and len(name.strip()):
        target_name = name
        
    if not isinstance(entity_cache, dict):
        entity_cache = dict()
    
    if obj is None:
        entity = group.create_dataset(target_name, data = h5py.Empty("f"))
        
        return entity
    
    if isinstance(obj, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity
            
        data = vu.kernel2array(obj)
        
        entity = group.create_dataset(target_name, data = data, 
                                      compression = compression, 
                                      chunks = chunks)
        
        entity.attrs.update(obj_attrs)
        
        storeEntityInCache(entity_cache, obj, entity)
        
        return entity
    
    elif isinstance(obj, (pd.DataFrame, pd.Series)):
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity

        data, categorical_info, pandas_dtypes = pandas2Structarray(obj)

        entity = group.create_group(target_name,track_order=track_order)
        
        obj_entity = makeHDF5Dataset(data, entity, name="PandasData",
                                     compression=compression,
                                     chunks=chunks,
                                     track_order=track_order,
                                     entity_cache = entity_cache)
        
        if len(categorical_info):
            catgrp = makeHDF5Group(categorical_info, entity, name="PandasCategoricalInfo",
                                   compression=compression, chunks=chunks,
                                   track_order=track_order) # no entity cache here...
            
        entity.attrs.update(obj_attrs)
            
        storeEntityInCache(entity_cache, obj, entity)
        
        return entity
    
    elif isinstance(obj, (vigra.VigraArray, neo.core.dataobject.DataObject)):
        # NOTE: 2021-11-19 11:34:38
        # make a sub group and place the main data set and axes data set within
        # this is because these objects need their own group to contain the 
        # main data set and the axes group, if any
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity
            return cached_entity
                    
        entity = group.create_group(target_name, track_order=track_order)
        
        # this call here WiLL NOT check for cached obj_entity/store new obj_entity !
        # NOTE: 2021-11-21 12:49:10
        # obj_entity is a h5py.Group
        # for vigra.VigraArray and neo.core.dataobject.DataObject objects !!!
        # see single dispatched versions of makeHDF5Dataset
        obj_entity = makeHDF5Dataset(obj, entity, name=target_name, 
                                       compression = compression,
                                       chunks = chunks, 
                                       track_order = track_order,
                                       entity_cache = entity_cache)
        
        # NOTE: 2021-11-21 12:25:41
        # neo DatObject objects also hold a reference to their parent segment
        # we deal with these here, storing them as references to any existing
        # segment representations in the parent group
        #
        if hasattr(obj, "segment"): 
            # we explicitly check for a 'segment' attribute first, because 
            # getattr(x,"segment", None) effectively bypasses this (i.e. it 
            # behaves as 'x' had this attribute albeit set to None
            parent_segment = getattr(obj, "segment")
            if isinstance(parent_segment, neo.Segment):
                # this almost surely will fail: when we execute this code, the 
                # parent segment's entity is not there yet?
                parent_segment_entity = getCachedEntity(entity_cache, parent_segment)
                if isinstance(parent_segment_entity, (h5py.Group, h5py.Dataset)):
                    entity["segment"] = parent_segment_entity
                    
                # NOTE: 2021-11-24 14:35:03
                # Since segment is a reference to the containing segment it is OK
                # if it doesn't show up in here; we just want to store a reference
                # to it, if possible
            
        entity.attrs.update(obj_attrs)
        
        storeEntityInCache(entity_cache, obj, entity)
        
        return entity
    
    elif isinstance(obj, neo.ChannelView):
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity
            return cached_entity
        
        entity = group.create_group(target_name, track_order=track_order)
        
        # NOTE: 2021-11-21 12:50:51
        # index_entity stores the ChannelView.index property values
        # this call here WiLL NEITHER check for cached index_entity NOR store new index_entity !
        index_entity = makeHDF5Dataset(obj.index, entity, name=f"{target_name}_index",
                                       compression = compression, chunks = chunks, 
                                       track_order = track_order,
                                       entity_cache = entity_cache)
        
        # populate the channel view with signal entities 
        cached_signal_entity = getCachedEntity(entity_cache, obj.obj)
        if isinstance(cached_entity, h5py.Dataset):
            entity[f"{target_name}_obj"] = cached_signal_entity
            
            
        else:
            # this call here WiLL NOT check for cached entity/store new entity !
            if isinstance(obj.obj, neo.core.basesignal.BaseSignal):
                signal_entity = makeHDF5Dataset(obj.obj, entity, name = f"{target_name}_obj",
                                        compression = compression, chunks = chunks, 
                                        track_order = track_order,
                                        entity_cache = entity_cache)
            
        return entity
    
    elif isinstance(obj, enum.Enum):
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity
        
        # NOTE: 2021-11-24 12:00:41
        # The type of an Enum MEMBER is Enum itself
        # The type of any Enum :class: is enum.EnumMeta
        # ATTENTION: HOWEVER, issubclass(Enum, EnumMeta) is ALWAYS False 
        # because metaclasses ARE NOT included in the mro !!!
        if type(obj) is enum.EnumMeta:
            isenummeta=True
            dt = h5py.enum_dtype(dict((member.name, member.value) for member in obj), basetype="i")
            shape = (1, len(obj))
        else:
            isenummeta=False
            dt = h5py.enum_dtype({obj.name: obj.value}, basetype="i")
            shape = (1,1)
            
        entity = group.create_dataset(target_name, shape, dtype=dt)
        
        if isenummeta:
            for k,member in enumerate(obj):
                entity[0,k] = member.value
        else:
            entity[0,0] = obj.value
            
        entity.attrs.update(obj_attrs)
        
        storeEntityInCache(entity_cache, obj, entity)
        
        return entity
    
    else:
        if isinstance(obj, (collections.abc.Iterable, neo.core.container.Container)) and not isinstance(obj, (str, bytes, bytearray, np.ndarray)):
            factory = makeHDF5Group
            
        else:
            factory = makeHDF5Dataset
            
        # this call here WILL check for cached entities and WILL store entity if
        # not already in cache
        return  factory(obj, group, name=name, compression=compression, 
                       chunks=chunks, track_order=track_order, entity_cache = entity_cache)
        

def makeHDF5Dataset(obj, group: h5py.Group, name:typing.Optional[str]=None,
                      compression:typing.Optional[str]="gzip",
                      chunks:typing.Optional[bool] = None,
                      track_order:typing.Optional[bool]=True,
                      entity_cache:typing.Optional[dict] = None,
                      ) -> h5py.Dataset:
    """Creates a HDF5 Dataset in group based on obj.
    Delegates to makeDataset to create a data set then adorns its attrs 
    with obj-specific information.
    """
    target_name, obj_attrs = makeObjAttrs(obj)
    if isinstance(name, str) and len(name.strip()):
        target_name = name

    dset = makeDataset(obj, group, obj_attrs, target_name, 
                        compression = compression, chunks = chunks,
                        track_order = track_order, entity_cache = entity_cache)
    
    #dset.attrs.update(obj_attrs)
    
    #storeEntityInCache(entity_cache, obj, dset)
    
    return dset

@singledispatch
def makeDataset(obj, group:h5py.Group, attrs:dict, name:str,
                 compression:typing.Optional[str]="gzip", 
                 chunks:typing.Optional[bool] = None,
                 track_order=True, entity_cache = None):
    #print(f"makeDataset for {type(obj).__name__} with name {name} in group {group}")
    # for scalar objects only, and basic python sequences EXCEPT for strings
    # because reading back strings can be confused with stored bytes data
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[target_name] = cached_entity # make a hard link
        return cached_entity
    
    if not isinstance(obj, (numbers.Number, tuple, list, deque)):
        warnings.warn(f"makeDataset: {type(obj).__name__} objects are not supported")
        dset = group.create_dataset(name, data = h5py.Empty("f"))
    else:
        dset = group.create_dataset(name, data = obj)
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(type(None))
def _(obj, group, attrs:dict, name:str, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[target_name] = cached_entity # make a hard link
        return cached_entity
    
    dset =  group.create_dataset(name, data = h5py.Empty("f"))
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(bytes)
@makeDataset.register(bytearray)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[target_name] = cached_entity # make a hard link
        return cached_entity
    
    if obj.isascii():
        data = np.array(obj.decode(), dtype=h5py.string_dtype())

    else:
        data = np.array(obj)
    
    if data.size == 0:
        dset = group.create_dataset(name, data = h5py.Empty(f))
    
    if data.size == 1:
        dset = group.create_dataset(name, data = data, compression=compression)
    else:
        dset =  group.create_dataset(name, data = data, compression=compression,
                                    chunks = chunks)
        
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset
    
            
@makeDataset.register(str)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[target_name] = cached_entity # make a hard link
        return cached_entity
    
    if len(obj)==0:
        dset = group.create_dataset(name, data = h5py.Empty("f"))
    else:
        dset = group.create_dataset(name, data = np.array(obj, dtype = h5py.string_dtype()))
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(vigra.VigraArray)
def _(obj, group:h5py.Group, attrs:dict, name:str, 
      compression=None, chunks=None, track_order=True, entity_cache=None):
    """Variant of vigra.impex.writeHDF5 returning the created h5py.Dataset object
    Also populates the dataset's dimension scales.
    
    Modified from vigra.impex.writeHDF5 (python version, (C) U.Koethe)
    """
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[target_name] = cached_entity # make a hard link
        return cached_entity
    
    dset_name = f"{name}_data"
    axgrp_name = f"{name}_axes"
    
    if obj.size == 0:
        dset = group.create_dataset(dset_name, data = h5py.Empty("f"))
    
    data = obj.transposeToNumpyOrder()
    
    if data.size == 1:
        dset = group.create_dataset(dset_name, data = data, compression = compression)
    else:
        dset = group.create_dataset(dset_name, data = data, compression = compression, chunks=chunks)
    
    axesgroup = group.create_group(axgrp_name, track_order = track_order)
    
    for axindex in range(obj.ndim):
        makeAxisScale(obj, dset, axesgroup, axindex, compression, chunks)
        
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
        
    return dset

@makeDataset.register(neo.core.dataobject.DataObject)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[target_name] = cached_entity # make a hard link
        return cached_entity
    
    dset_name = f"{name}_data"
    axgrp_name = f"{name}_axes"
    
    if obj.size == 0:
        return group.create_dataset(dset_name, data = h5py.Empty("f"))
    
    if obj.size == 1:
        dset = group.create_dataset(dset_name, data = obj.magnitude, compression = compression)
    else:
        dset = group.create_dataset(dset_name, data = obj.magnitude, compression = compression, chunks = chunks)
        
    axgroup = group.create_group(axgrp_name, track_order=track_order)
    
    for k in range(obj.ndim):
        makeAxisScale(obj, dset, axgroup, k, compression, chunks)
        
    # NOTE: 2021-11-20 13:38:33
    # labels for data object types neo.Event, neo.Epoch, DataMark, DataZone, TriggerEvent
    # should go into a Dataset child of the main data object group 'group'
    labels = getattr(obj, "labels", None)
    if isinstance(labels, np.ndarray) and labels.size:
        labels_dset = makeHDF5Entity(labels, group, 
                                       name =f"{name}_labels",
                                       compression = compression,
                                       chunks = chunks)
        labels_dset.make_scale(f"{name}_labels")
        dset.dims[0].attach_scale(labels_dset)
    
    # NOTE: 2021-11-20 13:39:52
    # waveforms of the neo.SpikeTrain objects should go into the main data object
    # group
    #
    # NOTE: 2022-10-05 23:29:51
    # since just before neo 0.11.0 SpikeTrain also have a "left_sweep" attribute
    # which is taken care of by makeAxisScale/makeNeoDataAxisDict
    waveforms = getattr(obj, "waveforms", None)
    if isinstance(waveforms, np.ndarray) and waveforms.size > 0:
        waveforms_dset = makeHDF5Entity(waveforms, group, 
                                          name = f"{name}_waveforms",
                                          compression = compression,
                                          chunks = chunks)
        waveforms_dset.make_scale(f"{name}_waveforms")
        dset.dims[0].attach_scale(waveforms_dset)
        
    annotations = getattr(obj, "annotations", None)
    if isinstance(annotations, dict) and len(annotations):
        annot_group = makeHDF5Group(annotations, group, f"{name}_annotations", 
                                      compression=compression, chunks=chunks,
                                      track_order = track_order)
        
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(pq.Quantity)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[target_name] = cached_entity # make a hard link
        return cached_entity
    
    # NOTE: 2021-11-18 14:41:47
    # units & dtype taken care of by makeObjAttrs() via makeDatasetAttrs()
    if obj.size == 0:
        dset = group.create_dataset(name, data = h5py.Empty("f"))
    
    if obj.size == 1:
        dset = group.create_dataset(name, data = obj.magnitude)
    else:
        dset = group.create_dataset(name, data = obj.magnitude, 
                                    compression = compression, chunks = chunks)
        
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(np.ndarray)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[target_name] = cached_entity # make a hard link
        return cached_entity
    
    if obj.size == 0:
        dset = group.create_dataset(name, data = h5py.Empty("f"))
    
    if obj.dtype.kind in NUMPY_STRING_KINDS:
        data = np.array(obj, dtype=h5py.string_dtype(), order="k")
    else:
        data = obj
        
    if obj.size == 1:
        dset = group.create_dataset(name, data = data, compression = compression)
    else:
        dset = group.create_dataset(name, data = data, compression = compression, 
                                    chunks = chunks)
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

def makeHDF5Group(obj, group:h5py.Group, name:typing.Optional[str]=None,
                    compression:typing.Optional[str]="gzip", 
                    chunks:typing.Optional[bool]=None,
                    track_order:typing.Optional[bool] = True,
                    entity_cache:typing.Optional[dict] = None) -> h5py.Group:
    target_name, obj_attrs = makeObjAttrs(obj)
    if isinstance(name, str) and len(name.strip()):
        target_name = name
        
    # NOTE: 2021-12-14 17:02:04
    # dispatched makeGroup variants descend into the container's elements to
    # call makeHDF5Entity for each
    entity = makeGroup(obj, group, obj_attrs, target_name, compression, chunks, track_order, entity_cache)
    
    return entity
    
@singledispatch
def makeGroup(obj, group:h5py.Group, attrs:dict, name:str, 
                    compression:typing.Optional[str]="gzip",
                    chunks:typing.Optional[bool]=None,
                    track_order:typing.Optional[bool] = True,
                    entity_cache:typing.Optional[dict] = None) -> h5py.Group:
    cached_entity = getCachedEntity(entity_cache, obj)
    
    if isinstance(cached_entity, h5py.Group):
        group[target_name] = cached_entity
        return cached_entity
        
    # NOTE: 2021-11-18 14:46:12
    # reserved for generic mapping objects
    grp = group.create_group(name, track_order = track_order)
    grp.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, grp)
    return grp
    
@makeGroup.register(dict)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    
    if isinstance(cached_entity, h5py.Group):
        group[target_name] = cached_entity
        return cached_entity
        
    grp = group.create_group(name, track_order = track_order)
    grp.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, grp)
    
    for k, element in obj.items():
        cached_entity = getCachedEntity(entity_cache, element)
        if isinstance(cached_entity, (h5py.Group, h5py.Dataset)):
            grp[k] = cached_entity
        
        else:
            element_entity = makeHDF5Entity(element, grp, k, compression = compression, chunks = chunks,
                            track_order = track_order, entity_cache = entity_cache)
        
    return grp

@makeGroup.register(collections.abc.Iterable)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    
    if isinstance(cached_entity, h5py.Group):
        group[target_name] = cached_entity
        return cached_entity
        
    grp = group.create_group(name, track_order = track_order)
    grp.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, grp)
    
    #_, obj_attrs = makeObjAttrs(obj)
    #grp.attrs.update(obj_attrs)
    
    for k, element in enumerate(obj):
        cached_entity = getCachedEntity(entity_cache, element)
        element_name = getattr(element, "name", type(element).__name__)
        element_entry_name = f"{k}_{element_name}"
        if isinstance(cached_entity, (h5py.Group, h5py.Dataset)):
            grp[element_entry_name] = cached_entity
        else:
            element_entity = makeHDF5Entity(element, grp, element_entry_name, compression = compression, chunks = chunks,
                            track_order = track_order, entity_cache = entity_cache)
            
    return grp

@makeGroup.register(neo.core.container.Container)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    
    if isinstance(cached_entity, h5py.Group):
        group[target_name] = cached_entity
        return cached_entity
        
    grp = group.create_group(name, track_order = track_order)
    grp.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, grp)
    
    children_dict = dict()
    
    for container_name in obj._child_containers:
        collection = getattr(obj, container_name, None)
        collection_group_name = container_name
        cached_entity = getCachedEntity(entity_cache, collection)
        if isinstance(cached_entity, (h5py.Group, h5py.Dataset)):
            grp[collection_group_name] = cached_entity
        else:
            collection_entity = makeHDF5Entity(collection, grp, collection_group_name, 
                                                 compression = compression, 
                                                 chunks = chunks,
                                                 track_order = track_order,
                                                 entity_cache = entity_cache,
                                                 parent_neo_container_entity = (obj,grp))
    return grp
    
def read_hdf5(h5file:h5py.File):
    groups = [k for k in h5file.keys()]
    if len(groups != 1):
        raise RuntimeError("Expecting a single group in the h5py File; got %d instead" % len(groups))

    root_name = groups[0]
    root = h5file[groups[0]]
    
