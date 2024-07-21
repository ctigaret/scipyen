# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

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
if neo.__version__ >= '0.13.0':
    from neo.core.objectlist import ObjectList as NeoObjectList
    
else:
    NeoObjectList = list # alias for backward compatibility :(
    
from neo.core.dataobject import ArrayDict

from . import jsonio # brings the CustomEncoder type and the decode_hook function
import core
from core.prog import (safeWrapper, signature2Dict, 
                       parse_module_class_path, get_loaded_module)
from core import prog
from core.traitcontainers import DataBag
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datazone import DataZone
from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType, MarkType)
from core.triggerprotocols import TriggerProtocol
import ephys
from ephys import ephys

from core.quantities import(arbitrary_unit, 
                            pixel_unit, 
                            channel_unit,
                            space_frequency_unit,
                            angle_frequency_unit,
                            day_in_vitro,
                            week_in_vitro, postnatal_day, postnatal_month,
                            embryonic_day, embryonic_week, embryonic_month,
                            unit_quantity_from_name_or_symbol,
                            name_from_unit, units_convertible,
                            str2quantity, quantity2str)

from core.datatypes import (TypeEnum,UnitTypes, GENOTYPES, 
                            is_uniform_sequence, is_uniform_collection, 
                            is_namedtuple, is_string,
                            is_numeric_string, is_numeric, 
                            is_convertible_to_numpy_array,
                            NUMPY_STRING_KINDS,
                            )

from core.modelfitting import (FitModel, ModelExpression,)
# from core.triggerevent import (TriggerEvent, TriggerEventType,) # already done above
# from core.triggerprotocols import TriggerProtocol
from core.utilities import (gethash, unique)
from core.strutils import (str2symbol, str2float, numbers2str, get_int_sfx,)
from core import modelfitting
# from core import pyabfbridge as pab
import imaging
from imaging.axiscalibration import (AxesCalibration, 
                                     AxisCalibrationData, 
                                     ChannelCalibrationData)

from imaging.indicator import IndicatorCalibration # do not confuse with ChannelCalibrationData
# from imaging.scandata import (AnalysisUnit, ScanData, ScanDataOptions,)
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
    if d.shape is None:
        # empty dataset
        return ""
    return np.atleast_1d(d)[0].decode("utf-8")

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
        elif "datetime" in str(dtype): # FIXME: 2022-11-28 17:53:57 = done? in NOTE: 2022-11-28 17:54:36
            col_dtype = h5py.string_dtype() # remember to convert datetime data to str!!!
        else:
            col_dtype = dtype
            
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
    # TODO/FIXME: 2022-10-12 15:11:09
    # do we deal with multi-index and groupings at all ?!?
    # if not, then we must FIXME this
    
    categorical_info = dict()
    
    # NOTE: 2021-12-13 22:16:37
    # this always generates a DataFrame irrespective of whether 'obj' is a
    # DataFrame or a Series
    obj_rndx = obj.reset_index() # pd.DataFrame

    v = obj_rndx.values # np.ndarray
    
    obj_dtypes = obj_rndx.dtypes # pd.Series
    
    #numpy_struct_array_dtypes = [pandasDtype2HF5Dtype(obj_dtypes[col], obj_rndx.loc[:, col], categorical_info) for col in obj_rndx.columns]
    original_obj_dtypes, numpy_struct_array_dtypes = zip(*list((obj_dtypes[col], pandasDtype2HF5Dtype(obj_dtypes[col], obj_rndx.loc[:, col], categorical_info)) for col in obj_rndx.columns))

    dtype = np.dtype(list(numpy_struct_array_dtypes))
    
    sarr = np.zeros(v.shape[0], dtype)
    
    for (i, k) in enumerate(sarr.dtype.names):
        try:
            if h5py.check_string_dtype(dtype[k]):
                sarr[k] = [str(x) for x in v[:, i]]
            else:
                sarr[k] = v[:, i]
        except:
            print(k, v[:, i])
            raise

    return sarr, categorical_info, original_obj_dtypes
    #return sarr, dtype, categorical_info

def __check_make_entity_args__(obj, oname, entity_cache):
    target_name, obj_attrs = makeObjAttrs(obj, oname=oname)
    
    if isinstance(oname, str) and len(oname.strip()):
        target_name = oname
        
    if not isinstance(entity_cache, dict):
        entity_cache = dict()
    
    return target_name, obj_attrs, entity_cache

# def storeEntityInReadingCache(s:dict, obj:typing.Any, entity:typing.Union[h5py.Group, h5py.Dataset]):
#     if not isinstance(s, dict):
#         return
#     
#     if not isinstance(entity, (h5py.Group, h5py.Dataset)):
#         return
#     
#     s[id(obj)] = (obj, entity)

def storeEntityInCache(s:dict, obj:typing.Any, entity:typing.Union[h5py.Group, h5py.Dataset]):
    """Keeps of cache of HDF5-endoced objects and their HDF5 entities.
    
    The cache maps the id of the object stored as HDF5 entity to the entity itself
    
    NOTE: It would have been enough to just store the object id (id(obj)) as a key
    in the cache, but also storing a reference to the object helps on the reconstruction
    
    NOTE: 2022-10-08 10:35:07
    Using object hash (scipyen core.utilities.gethash) for persistent ID
    
    """
    if not isinstance(s, dict):
        return
    
    if not isinstance(entity, (h5py.Group, h5py.Dataset)):
        return
    
    # obj_hash = gethash(obj)
    # s[obj_hash] = entity
    
    s[id(obj)] = entity

def getCachedEntity(cache:dict, obj:typing.Any):
    if not isinstance(cache, dict) or len(cache) == 0:
        return
    
    # obj_hash = gethash(obj)
    # return cache.get(obj_hash, None)
    
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
            return objectFromHDF5Entity(item)
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

@singledispatch
def makeAttr(x):
    """Returns a representation of 'x' suitable as a HDF5 entity attribute.
    
    `x` is typically a basic Python type, and the representation is a JSON string.
    
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
    
    return x

@makeAttr.register(type(None))
def _(x):
    return jsonio.dumps(x)

@makeAttr.register(str)
def _(x):
    if isinstance(x, np.str_):
        return str(x)
    
    return x

@makeAttr.register(enum.Enum)
def _(x):
    mdl = x.__class__.__module__
    kls = x.__class__.__name__
    if mdl == "__main__":
        klass = kls
    else:
        klass = f"ENUM {mdl}.{kls}"
        
    return f"{klass}({x.value})"
        
    

@makeAttr.register(datetime.date)
@makeAttr.register(datetime.time)
@makeAttr.register(datetime.datetime)
def _(x):
    return f"{x.__class__.__module__}.{x.__class__.__name__} {x.isoformat()}"

@makeAttr.register(datetime.timedelta)
def _(x):
    raise NotImplementedError(f"{type(x).__name__} objects cannot (and should not) be encoded as HDF5 Attribute")
    # return f"{x.__class__.__module__}.{x.__class__.__name__}(days={x.days}, seconds={x.seconds})"
    

@makeAttr.register(list)
@makeAttr.register(tuple)
@makeAttr.register(dict)
def _(x):
    # BUG: 2024-07-20 14:28:52 FIXME
    # will raise exception if elements or values are not json-able
    # CAUTION Do not use large data objects here!
    # We use the CustomEncoder which has wider coverage and its own 
    # limitations/caveats
    # 
    try:
        return jsonio.dumps(x)
    except:
        raise HDFDataError(f"The object {x}\n with type {type(x).__name__} cannot be serialized in json")

@makeAttr.register(np.ndarray)
@makeAttr.register(pq.Quantity)
def _(x):
    if isinstance(x, pq.Quantity):
        if x.size > 1:
            raise ValueError("non-scalar quantities cannot be stored as HDF5 Attributes; convert them to HDF5 Dataset")
        
        return f"QUANTITY {quantity2str(x)}"
#         return f"{float(xx.magnitude)}, pq.{xx.units.dimensionality})"
#         xx = x.simplified
#         
#         return f"pq.Quantity({float(xx.magnitude)}, pq.{xx.units.dimensionality})"
    
    elif x.dtype.kind in NUMPY_STRING_KINDS:
        return np.array(x, dtype=h5py.string_dtype(), order="K")
    else:
        return jsonio.dumps(x) 
    

    

# def makeAttr(x:typing.Optional[typing.Union[str, list, tuple, dict, deque, np.ndarray, datetime.datetime]]=None):
#     """Returns a representation of 'x' suitable as a HDF5 entity attribute.
#     
#     `x` is typically a basic Python type, and the representation is a JSON string.
#     
#     Parameters:
#     -----------
#     'x': basic Python type (str or scalar number), or numpy array
#     
#     Returns:
#     --------
#     A string when 'x' is a str, or is a container with elements that can be
#         written to a JSON-formatted string.
#         
#         As a rule of thumb, these objects should be relatively small, and the 
#         container should be relatively simple.
#     
#     A numpy array with dtype j5py.string_dtype() when 'x' is a numpy array with
#     dtype.kind of 'S' or 'U' (i.e., strings)
#     
#     'x' itself in any other case.
#     
#     CAUTION h5py will raise exception when 'x' is of a type that h5py cannot 
#     store as attrs value to a Group or Dataset.
#     
#     """
#     if x is None:
#         return jsonio.dumps(x)
#     
#     if isinstance(x, str):
#         # because np.str_ resolves to str in later versions; but data saved with
#         # old numpy API msy still hold scalars of type np.str_
#         if isinstance(x, np.str_):
#             return str(x)
#         
#         return x
#     
#     # NOTE: 2022-11-28 17:54:36
#     # store datetime.datetime in their isoformat string representation
#     if isinstance(x, (datetime.datetime, datetime.date, datetime.time)):
#         return f"{x.__class__.__module__}.{x.__class__.__name__} {x.isoformat()}"
#         
#     if isinstance(x, (list, tuple, dict)): 
#         # will raise exception if elements or values are not json-able
#         # CAUTION Do not use large data objects here!
#         # We use the CustomEncoder which has wider coverage and its own 
#         # limitations/caveats
#         # 
#         try:
#             return jsonio.dumps(x)
#         except:
#             raise HDFDataError(f"The object {x}\n with type {type(x).__name__} cannot be serialized in json")
# 
#     if isinstance(x, np.ndarray):
#         if x.dtype.kind in NUMPY_STRING_KINDS:
#             return np.array(x, dtype=h5py.string_dtype(), order="K")
#         else:
#             return jsonio.dumps(x) 
#         
#     return x

def makeAttrDict(**kwargs):
    """Generates a dict suitable for storage as 'attrs' property of a HDF5 entity.
    
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

def group2neoContainer(g:h5py.Group, target_class:type, cache:dict = {}):
    # treats Segment, Block, Group -- TODO
    # neo.core.container.Containers are (as of neo 0.11.0):
    # • Block
    # • Segment
    # • Group
    
    attrs = attrs2dict(g.attrs)
    rec_attrs = dict((a[0], attrs[a[0]]) for a in target_class._recommended_attrs)
    
    child_containers = rec_attrs.pop("child_containers", tuple())

    if target_class == neo.Block:
        if len(child_containers) == 0:
            child_containers = ("segments", "groups", "annotations")
            
    elif target_class == neo.Segment:
        if len(child_containers) == 0:
            child_containers = ("analogsignals", "irregularlysampledsignals", 
                        "epochs", "events",
                        "spiketrains", "imagesequences", "annotations")
        
    elif target_class == neo.Group:
        for child_container in child_containers:
            entity = g.get(child_container, None)
            if isinstance(entity, (h5py.Group, h5py.Dataset)):
                child = objectFromHDF5Entity(entity, cache)
                setattr(obj, child_container, child)
            
    obj = target_class() # this automatically creates container children e.g. analosginals, etc
    
    cache[g] = obj

    for child_container in child_containers:
        entity = g.get(child_container, None)
        if isinstance(entity, (h5py.Group, h5py.Dataset)):
            child = objectFromHDF5Entity(entity, cache)
            # print(f"group2neoContainer child_container {child_container}, entity: {entity}, child: {type(child).__name__}")
            setattr(obj, child_container, child)
        
    for k,v in rec_attrs.items():
        setattr(obj, k, v)
    
    if "annotations" in g:
        annotations = objectFromHDF5Entity(g["annotations"], cache)
        if isinstance(annotations, dict):
            obj.annotations.update(annotations)
    
    return obj

def group2neoSignal(g:h5py.Group, target_class:type, cache:dict = {}):
    """Reconstructs neo.core.basesignal.BaseSignal objects from their HDF5 Group.

    These object types are:
    • neo.AnalogSignal
    • neo.IrregularlySampledSignal
    • DataSignal
    • IrregularlySampledDataSignal
    • neo.ImageSequence
    
    """
    # first prepare some defaults
    signal = []
    times = []
    annotations = dict()
    segment = None 
    
    # NOTE: 2022-10-09 15:16:30
    # Because neo Signals inherit from python Quantity, relevant object attributes
    # like dtype and units are stored in the attrs of the child dataset and not
    # in the attrs of the axis 1 dataset
    # 

    # domain axis
    ax0 = dict()
    ax0["t_start"]          = 0.*pq.s
    ax0["name"]             = "Time"
    ax0["sampling_rate"]    = 1.*pq.Hz
    ax0["key"]              = "T"
    ax0["units"]            = pq.s
    ax0["dtype"]            = np.dtype(float)
    
    # signal ("channels" axis)
    # but NOTE that the channels are typically stored as fields of the 
    # array_annotations property of the signal !
    ax1 = dict() 
    # NOTE: the signal units are stored in axis 1 Dataset attrs;
    ax1["units"]                = pq.dimensionless # → stored in the dataset attrs
    ax1["name"]                 = ""
    ax1["key"]                  = '?'
    ax1["dtype"]                = np.dtype(float)
    ax1["array_annotations"]    = None
    
    ax2 = dict() # for ImageSequence only
    ax2["units"]                = pq.dimensionless 
    ax2["name"]                 = ""
    ax2["key"]                  = '?'
    ax2["dtype"]                = np.dtype(float)
    # FIXME/TODO same as for units, above; stored in the dataset attrs (they inherit
    # from Quantity)
    # ax1["dtype"] = attrs.get("dtype", np.dtype(float))
    
    # NOTE:2022-10-09 08:51:31
    # this is a reference to the parent Segment; thic may have already been
    # reconstructed, therefore we check the cache, 
    # see NOTE: 2022-10-09 08:48:24
    
    # now extract metadata info from the signal's HDF5 Group
    # these are (in no particular order):
    # • name
    # • segment
    # • file_origin
    # • description
    # • units
    # 
    attrs = attrs2dict(g.attrs)
    rec_attrs = dict((a[0], attrs[a[0]]) for a in target_class._recommended_attrs)
    
    segment_entity = g.get("segment", None)
    if isinstance(segment_entity, h5py.Group):
        # NOTE: 2022-10-09 08:48:24 
        # in the next call, objectFromHDF5Entity will either:
        # • get the actual neo.Segment from cache (if this segment_entity is
        #   in the cahche, which means the neo.Segment instance has been 
        #   reconstructed already)
        # • create a new neo.Segment from the segment_entity, rthen cache it
        segment = objectFromHDF5Entity(segment_entity, cache)
        
    # data_set_name = f"{g.name.split('/')[-1]}_data"
    data_set = g.get("data", None)
    
    # axes_group_name = f"{g.name.split('/')[-1]}_axes"
    # NOTE: 2022-10-10 21:02:32
    # because the axes groups do NOT correspond to a python object, they bypass
    # the cache mechanism
    axes_group = g.get("axes", None)
    
    # • signal annotations ← Group of annotations
    # (these are NOT array_annotations !!!) 
    # annotations_group_name = f"{g.name.split('/')[-1]}_annotatinos"
    annotations_group = g.get("annotations", None)
    if isinstance(annotations_group, h5py.Group):
        # now, this might be cached, as it corresponds to a real-life python 
        # object: the neo object's annotations
        annotations = objectFromHDF5Entity(annotations_group)
    else:
        annotations = dict()

    # NOTE: 2022-10-10 21:04:28
    # the signal data set does not correspond to a final python object; it just
    # stored the numerical array data in the neo object (signal); therefore, it
    # bypasses the cache mechanism
    if isinstance(data_set, h5py.Dataset):
        signal = np.array(data_set)

        if isinstance(axes_group, h5py.Group):
            # NOTE: 2022-10-07 13:44:46 ATTENTION: ❗❗❗
            # for AnalogSignal and DataSignal, axis0 data set is empty, so no need
            # to cache it...
            # axis0 data set only contains data for irregular signals, where it
            # defines the DOMAIN (time for IrregularlySampledSignal and time, 
            # space or anything else for IrregularlySampledDataSignal)
            #
            # HOWEVER: ❗❗❗
            # the specifics of the domain are stored in this data set attrs property
            ax0ds = axes_group.get("axis_0", None)
            if isinstance(ax0ds, h5py.Dataset):
                if isinstance(ax0ds.shape, tuple):
                    times = np.array(ax0ds)
                ax0attrs = attrs2dict(ax0ds.attrs)
                ax0["units"]            = ax0attrs.get("units", pq.s)
                ax0["t_start"]          = ax0attrs.get("origin", 0.*ax0["units"])
                ax0["dtype"]            = ax0attrs.get("dtype", np.dtype(float))
                ax0["name"]             = ax0attrs.get("name", None)
                ax0["sampling_rate"]    = ax0attrs.get("sampling_rate", 1.*pq.Hz)
                ax0["key"]              = ax0attrs.get("key", "")
                
            # NOTE: 2022-10-07 13:45:37 ATTENTION: ❗❗❗
            # axis1 data set is ALWAYS empty i.e it has NO data !!!
            # the relevant meta information is contains in its attrs property.
            ax1ds = axes_group.get("axis_1", None)
            if isinstance(ax1ds, h5py.Dataset):
                ax1attrs = attrs2dict(ax1ds.attrs)
                ax1["name"]                 = ax1attrs.get("name", "")
                ax1["units"]                = ax1attrs.get("units", pq.dimensionless)
                ax1["key"]                  = ax1attrs.get("key", '?')
                ax1["dtype"]                = ax1attrs.get("dtype", np.dtype(float))
                ax1["array_annotations"]    = ax1attrs.get("array_annotations", None)
                # NOTE: this none is only present in ImageSequence
                ax1["spatial_scale"]        = ax1attrs.get("spatial_scale", 1.0*pq.um)
                
            ax2ds = axes_group.get("axis_2", None)
            if isinstance(ax2ds, h5py.Dataset):
                ax2attrs = attrs2dict(ax2ds.attrs)
                ax2["units"] = ax2attrs.get("units", pq.dimensionless)
                ax2["name"]  = ax2attrs.get("name", "")
                ax2["key"]   = ax2attrs.get("key", '?')
                ax2["dtype"] = ax2attrs.get("dtype",np.dtype(float))
                
    if target_class == neo.ImageSequence:
        t_start       = ax0["t_start"]
        sampling_rate = ax0["sampling_rate"]
        spatial_scale = ax1["spatial_scale"]
        units         = ax2["units"]
        dtype         = ax2["dtype"]
        
        obj = target_class(signal, t_start = t_start, 
                           sampling_rate = sampling_rate, 
                           spatial_scale = spatial_scale, units = units, 
                           dtype =dtype)
        
        for k,v in rec_attrs.items():
            setattr(obj, k, v)
        
    elif target_class == IrregularlySampledDataSignal:
        domain_units  = ax0["units"]
        domain_dtype  = ax0["dtype"]
        units         = ax1["units"]
        dtype         = ax1["dtype"]

        obj = target_class(times, signal, domain_units = domain_units, 
                           domain_dtype = domain_dtype, 
                           units = units, dtype = dtype)
        
        for k,v in rec_attrs.items():
            setattr(obj, k, v)
        
    elif target_class == neo.IrregularlySampledSignal:
        time_units      = ax0["units"]
        units           = ax1["units"]
        dtype           = ax1["dtype"]

        obj = target_class(times, signal, time_units = time_units, units = units,
                           dtype = dtype)

        for k,v in rec_attrs.items():
            setattr(obj, k, v)
        
    elif target_class == DataSignal:
        time_units      = ax0["units"]
        t_start         = ax0["t_start"]
        sampling_rate   = ax0["sampling_rate"]
        units           = ax1["units"]
        dtype           = ax1["dtype"]

        obj = target_class(signal, time_units = time_units, t_start = t_start,
                           sampling_rate = sampling_rate, units = units, 
                           dtype = dtype)

        for k,v in rec_attrs.items():
            setattr(obj, k, v)
        
    elif target_class == neo.AnalogSignal:
        time_units              = ax0["units"]
        t_start                 = ax0["t_start"]
        sampling_rate           = ax0["sampling_rate"]
        units                   = ax1["units"]
        dtype                   = ax1["dtype"]

        obj = target_class(signal, time_units = time_units, t_start = t_start,
                           sampling_rate = sampling_rate, units = units, 
                           dtype = dtype)
        
        for k,v in rec_attrs.items():
            setattr(obj, k, v)
        
    else:
        raise RuntimeError(f"Reading {target_class.name} objects is not implemented")
            
    obj.segment=segment
    obj.annotations.update(annotations)
    
    arrann = ax1.get("array_annotations", None)
    
    if arrann is not None:
        obj.array_annotations = arrann
        
    # NOTE: 2022-10-10 21:07:30
    # add the group entity and the encoded object to the cache, so that it can
    # be retrieved early in future call chains (thus avoiding infinite recursions)
    cache[g] = obj
    
    return obj

def group2neoDataObject(g:h5py.Group, target_class:type, cache:dict = {}):
    """Reconstructs neo.core.dataobject.DataObject objects from their HDF5 Group.
    
    These object types are:
    • Signal objects → delegated to group2neoSignal():
        ∘ neo.AnalogSignal
        ∘ neo.IrregularlySampledSignal
        ∘ DataSignal
        ∘ IrregularlySampledDataSignal
        ∘ neo.ImageSequence
        
    • neo.Epoch
    • DataZone
    • neo.Event
    • DataMark
    • TriggerEvent
    • neo.SpikeTrain
    
    """
    # delegate for signals 
    if neo.core.basesignal.BaseSignal in inspect.getmro(target_class):
        return group2neoSignal(g, target_class)
    
    # prepare defaults
    times = []
    durations = []
    annotations = dict()
    segment = None 
    
    # NOTE: 2022-10-07 10:59:48
    # For these objects, there is only one axis: 𝐚𝐱𝐢𝐬 𝟎 containing domain information
    ax0 = dict()
    ax0["t_start"]              = 0.*pq.s
    ax0["t_stop"]               = None
    ax0["sampling_rate"]        = 1.*pq.Hz
    ax0["left_sweep"]           = None
    ax0["time_units"]           = pq.s
    ax0["units"]                = pq.s
    ax0["dtype"]                = np.dtype(float)
    ax0["time_dtype"]           = np.dtype(float)
    ax0["array_annotations"]    = None
    ax0["labels"]               = []
    
#     ax1 = dict()
#     ax1["units"] = pq.dimensionless
#     ax1["dtype"] = np.dtype(float)
#     
    attrs = attrs2dict(g.attrs)
    rec_attrs = dict((a[0], attrs[a[0]]) for a in target_class._recommended_attrs)
    
    data_set = g.get("data", None)
    
    axes_group = g.get("axes", None)
    
    # NOTE: 2022-10-11 11:49:41 
    # these are stored in the axis0 attrs!
#     labels_set = g.get("labels", None)
#     
#     if isinstance(labels_set, h5py.Dataset):
#         labels = objectFromHDF5Entity(labels_set)
#     else:
#         labels = None
        
    durations_set = g.get("durations", None)
    if isinstance(durations_set, h5py.Dataset):
        durations = objectFromHDF5Entity(durations_set)
    else:
        durations = None
    
    segment_entity = g.get("segment", None)
    if isinstance(segment_entity, h5py.Group):
        # NOTE: 2022-10-09 08:48:24 
        # in the next call, objectFromHDF5Entity will either:
        # • get the actual neo.Segment from cache (if this segment_entity is
        #   in the cahche, which means the neo.Segment instance has been 
        #   reconstructed already)
        # • create a new neo.Segment from the segment_entity, rthen cache it
        segment = objectFromHDF5Entity(segment_entity, cache)
        
    # NOTE: 2022-10-10 14:27:21 ATTENTION
    # do NOT confuse with array_annotations
    # annotations_group_name = f"{g.name.split('/')[-1]}_annotations"
    annotations_group = g.get("annotations", None)
    
    if isinstance(annotations_group, h5py.Group):
        annotations = objectFromHDF5Entity(annotations_group)
    else:
        annotations = dict()

    if isinstance(data_set, h5py.Dataset):
        if isinstance(data_set.shape, tuple):
            times = np.array(data_set)
        
        if isinstance(axes_group, h5py.Group):
            # axis 0 is ALWAYS the domain axis
            # axis 1 is ALWAYS the signal axis (or channels axis)
            # for DataObject other than BaseSignal, axis 1 is just a tag-like
            # data - these all have one axis!!
            # ATTENTION: ❗❗❗ see NOTE: 2022-10-07 13:44:46 and NOTE: 2022-10-07 13:45:37
            #
            # NOTE: 2022-10-10 14:22:45
            # for DataObject NOT BaseSignal object types, array annotations go as
            # attrs of axis 0 data set - see NOTE: 2022-10-10 14:20:39
            ax0ds = axes_group.get("axis_0", None)
            
            if isinstance(ax0ds, h5py.Dataset):
                # for Epoch and DataZone the durations ARE the data in axis_0 Dataset
                ax0attrs = attrs2dict(ax0ds.attrs)
                if ax0ds.shape is not None and len(ax0ds.shape) > 0:
                    durations = np.array(ax0ds)
                ax0["units"]                = ax0attrs.get("units", pq.s)
                ax0["t_stop"]               = ax0attrs.get("end", None)
                ax0["t_start"]              = ax0attrs.get("origin", 0.*ax0["units"])
                ax0["sampling_rate"]        = ax0attrs.get("sampling_rate", 1.*pq.Hz)
                ax0["left_sweep"]           = ax0attrs.get("left_sweep", None)
                ax0["dtype"]                = ax0attrs.get("dtype", np.dtype(float))
                ax0["time_dtype"]           = ax0attrs.get("time_dtype", np.dtype(float))
                ax0["time_units"]           = ax0attrs.get("time_units", pq.s)
                ax0["array_annotations"]    = ax0attrs.get("array_annotations", None)
                ax0["labels"]               = ax0attrs.get("labels", [])
                
    # NOTE: 2022-10-09 13:36:56
    # briefly:
    # set up kwargs for the named arguments of the target_class
    # c'tor
    # update kwargs with a dict of recommended attrs (see neo API)
    
    if target_class == neo.SpikeTrain:
        waveforms_set_name = f"{g.name.split('/')[-1]}_waveforms"
        waveforms_set = g[waveforms_set_name] if waveforms_set_name in g else None
        
        if isinstance(waveforms_set, h5py.Dataset):
            waveforms  = np.array(waveforms_set)
        else:
            waveforms = None
            
        t_start       = ax0["t_start"]
        t_stop        = ax0["t_stop"]
        time_units    = ax0["time_units"]
        sampling_rate = ax0["sampling_rate"]
        left_sweep    = ax0["left_sweep"]
        units         = ax0["units"]
        dtype         = ax0["dtype"]
        # time_dtype    = ax0["time_dtype"] # not needed
            
        obj = target_class(times, t_start = ax0["t_start"], t_stop = ax0["t_stop"],
                           sampling_rate = ax0["sampling_rate"], 
                           left_sweep = ax0["left_sweep"],
                           units = ax0["units"], dtype = ax0["dtype"])
        
        for k,v in rec_attrs.items():
            setattr(obj, k, v)
    
    elif target_class == neo.Event:
        obj = target_class(times = times, labels = ax0["labels"], units = ax0["units"])
    
        for k,v in rec_attrs.items():
            setattr(obj, k, v)
    
    elif target_class in (neo.Epoch, DataZone):
        obj = target_class(times=times, durations=durations, labels=ax0["labels"], units = ax0["units"])
    
        for k,v in rec_attrs.items():
            setattr(obj, k, v)
    
    elif DataMark in inspect.getmro(target_class):
        g_attrs = attrs2dict(g.attrs)
        mark_type = g_attrs.get("name", "presynaptic") # assume a suitable default ?!?
        # mark_type = g.name.split("/")[-1]
        if target_class == TriggerEvent:
            etype = TriggerEventType[mark_type]
            obj = target_class(times = times, labels = ax0["labels"], units = ax0["units"], event_type = etype)
        else:
            etype = MarkType[mark_type]
            obj = target_class(times = times, labels = ax0["labels"], units = ax0["units"], mark_type = etype)
            
        
        for k,v in rec_attrs.items():
            setattr(obj, k, v)
    
    else:
        raise NotImplementedError(f"{target_class} if not yet supported")
        
    obj.segment = segment
    obj.annotations.update(annotations)
    
    if isinstance(ax0["array_annotations"], dict):
        obj.array_annotations = ax0["array_annotations"]
    
    # NOTE: 2022-10-10 21:08:49
    # add the object and its encoding entity (a h5py.Group) to the cache, to 
    # avoid infinite recursion
    cache[g] = obj
    return obj
    
def group2VigraArray(g:h5py.Group, cache:dict = {}):
    data_set = g.get("data", None)
    axes_group = g.get("axes", None)
    
    if isinstance(data_set, h5py.Dataset):
        data_attrs = attrs2dict(data_set.attrs)
        dtype = data_attrs.get("dtype", np.float32)
        axtags = data_attrs.get("axistags", None)
        data_array = np.array(data_set, dtype=dtype)
        axescalibrationdata = list()
        try:
            axinfos = [vigra.AxisInfo(d["key"], typeFlags=vigra.AxisType(d["typeFlags"]), 
                                      resolution=d["resolution"], description=d["description"])
                       for d in axtags["axes"]]
            
            if isinstance(axes_group, h5py.Group):
                # if len(axes_group.items()) not in (0, ret.ndim):
                #     raise RuntimeError(f"Mismatch between VIGRA array ndim {ret.ndim} and number of axes data sets {len(axes_group.items())}")
                
                axdd = dict([(k,i) for k,i in axes_group.items()])
                
                
                for k, (axdsetname, axdset) in enumerate(axes_group.items()):
                    axattrs = attrs2dict(axdset.attrs)
                    axcaldata = AxisCalibrationData(key = axattrs["cal_key"],
                                                    name = axattrs["cal_name"],
                                                    units = axattrs["cal_units"],
                                                    origin = axattrs["cal_origin"],
                                                    resolution = axattrs["cal_resolution"],
                                                    type = vigra.AxisType(axattrs["cal_type"])
                                                    )
                    axescalibrationdata.append(axcaldata)
                    
                    
            
        except:
            traceback.print_exc()
            axistags = vigra.defaultAxistags(data_array.ndim)
            
        ret = vigra.VigraArray(data_array, dtype = dtype, axistags = vigra.AxisTags(*axinfos), order="V")
        
        if len(axescalibrationdata) == ret.ndim and all(isinstance(v, AxisCalibrationData) for v in axescalibrationdata):
            for k, axcaldata in enumerate(axescalibrationdata):
                axcaldata.calibrateAxis(ret.axistags[k])
            
        return ret
            
    else:
        raise RuntimeError(f"Cannot parse a VigraArray from the HDF5 Group {g}")
                
def group2neo(g:h5py.Group, target_class:type, cache:dict = {}):
    """Reconstructs neo objects
    
    • neo.core.container.Container (neo.Block, neo.Segment, neo.Group)
    • neo.core.dataobject.DataObject:
        ∘ neo.core.basesignal.BaseSignal (neo.AnalogSignal, neo.IrregularlySampledSignal, 
                                          DataSignal, IrregularlySampledDataSignal)
        ∘ neo.Event, neo.Epoch, DataMark, TriggerEvent, DataZone
        
    • neo.ChannelView
    
    NOTE: neo.core.spiketrainlist.SpikeTrainList is NOT a BaseNeo object ❗
    
    """
    # TODO 2022-10-06 13:44:05 factoring out neo object reconstruction
    # call this after checking neo.core.baseneo.BaseNeo is in target's mro, 
    # in the caller
    
    # print(f"group2neo: target_class {target_class}")
    
    mro = inspect.getmro(target_class)
    
    # print(f"group2neo: {g}, ({target_class})")
    
    if neo.core.dataobject.DataObject in mro:
        return group2neoDataObject(g, target_class, cache)
    
    elif neo.core.container.Container in mro:
        return group2neoContainer(g, target_class, cache)
    
    elif target_class == neo.ChannelView:
        attrs = attrs2dict(g.attrs)
        rec_attrs = dict((a[0], attrs[a[0]]) for a in target_class._recommended_attrs)
        
        kwargs = dict()
        kwargs.update(rec_attrs)
        
        index_entity = g.get("index", None)
        index = None
        if isinstance(index_entity, h5py.Dataset):
            if index_entity in cache:
                index = cache[index_entity]
            else:
                index = np.array(index_entity)
                cache[index_entity] = index

        signal_entity = g.get("obj", None)
        signal = None
        if isinstance(signal_entity, h5py.Group):
            signal = objectFromHDF5Entity(signal_entity, cache)
            
        if all(o is not None for o in (index, signal)):
            obj = target_class(signal, time, **kwargs)
            cache[g] = obj
            return obj
        
    else:
        raise TypeError(f"Don't know how to manage {target_class}")
            
def objectFromHDF5Entity(entity:typing.Union[h5py.Group, h5py.Dataset], cache:dict={}):
    """attempt to round trip of makeHDF5Entity
    """
    # print("in objectFromHDF5Entity: ")
    # NOTE: 2022-10-08 13:16:14
    # HDF5 entities (Group, Dataset) are hashable;
    # hence, we can use them to store entity → object maps
    # this is useful for dealing with 'soft links' in the HDF5 so we 
    # don't duplicate data upon reading from the file
    
    # print(f"\tentity : {entity}")
    # print(f"\tentity name: {entity.name}")
    
    if entity in cache:
        return cache[entity]
    
    attrs = attrs2dict(entity.attrs)
    
    # print(f"objectFromHDF5Entity attrs = {attrs}")

    try:
        type_name = attrs.get("type_name", None)
        # print(f"\ttype_name: {type_name}")
        if type_name is None:
            return None
        python_class = attrs["python_class"]
        python_class_comps = python_class.split(".")
        module_name = attrs["module_name"]
        module_name_comps = module_name.split(".")
        
        if module_name_comps[0] == "builtins":
            target_class = eval(type_name)
        else:
            try:
                if module_name in sys.modules:
                    pymodule = sys.modules[module_name]
                    target_class = eval(type_name, pymodule.__dict__)
                    
                else:
                    if module_name_comps[0] not in sys.modules:
                        pymodule = importlib.import_module(module_name_comps[0])
                        
                    else:
                        pymodule = sys.modules[module_name_comps[0]]
                    
                    target_class = eval(".".join(python_class_comps[1:]), pymodule.__dict__)
                    
                # print(f"target_class: {target_class} from pymodule: {pymodule}")

                # NOTE: 2022-10-05 18:40:53 FIXME possible BUG
                # this doesn't work if the module is imported under an alias
                    
            except:
                traceback.print_exc()
                print(f"😢 \python_class: {python_class}")
                print(f"😢 objectFromHDF5Entity -> python_class_comps: {python_class_comps}")
                print(f"😢 objectFromHDF5Entity -> module_name: {module_name}")
                print(f"😢 objectFromHDF5Entity -> module_name_comps: {module_name_comps}")
                print(f"😢 objectFromHDF5Entity -> wanted target_class: {'.'.join(python_class_comps[1:])}")
                raise
            
    except:
        print(f"😢 objectFromHDF5Entity -> entity: {entity.name}")
        traceback.print_exc()
        raise
    
    # 😢
    # print(f"objectFromHDF5Entity target_class = {target_class}")
    
    if isinstance(inspect.getattr_static(target_class,"objectFromHDF5Entity", None),
                  prog.CALLABLE_TYPES + (classmethod,)):
        return target_class.objectFromHDF5Entity(entity, attrs, cache)
    
    if isinstance(entity, h5py.Dataset):
        # NOTE: 2022-10-06 11:57:32
        # for now, this code branch applies ONLY to "stand-alone" datasets, and 
        # not to data sets that are children of groups encapsulating more 
        # specialized objects such a neo signal etc
        # hence these will be dealt with in the "group" branch below; don't
        # call objectFromHDF5Entity on the children datsets there!
        if entity.shape is None or len(entity.shape) == 0: 
            # no axes imply no Dataset dimscales either
            # most likely a scalar and therefore we attempt to instantiate
            # one as such
            # print(f"target_class {target_class}")
            if target_class == bool:
                obj = target_class(entity)
                
            elif target_class == str:
                obj = dataset2string(entity)
                
            elif target_class in (bytes, bytearray):
                v = dataset2string(entity)
                obj = bytes.fromhex(v) if len(v) else bytes()
                
                if target_class == bytearray:
                    obj = bytearray(obj)
                
            elif target_class == datetime.timedelta:
                days = int(attrs.get("days", 0))
                microseconds = int(attrs.get("microseconds", 0))
                seconds = int(attrs.get("seconds", 0))
                obj = target_class(days=days, seconds=seconds, microseconds=microseconds)
                
            elif target_class in (datetime.date, datetime.time, datetime.datetime):
                try:
                    val = dataset2string(entity)
                    # print(f"val {val} decoded {val.decode()}")
                    obj = target_class.fromisoformat(val)
                except Exception as e:
                    traceback.print_exc()
                    raise
                
            elif any(k in inspect.getmro(target_class) for k in (int, float, complex)):
                # NOTE: 2022-10-08 13:20:20
                # numpy scalar types (e.g. numpy.float64 etc) are subclasses of
                # these 
                obj = target_class(entity[()])
                
            elif target_class == pq.Quantity:
                units = attrs.get("units", pq.dimensionless)
                data = np.array(entity)
                obj = data*units
                
            else:
                try:
                    obj = entity[()] # shouldn't get here but keep in case I've messed/missed smthng
                except:
                    obj = target_class
                    traceback.print_exc()
                    # raise
            
        else:
            if target_class == pq.Quantity:
                units = attrs.get("units", pq.dimensionless)
                data = np.array(entity)
                obj = data*units
                
            elif target_class == np.ndarray:
                obj = np.array(entity)
                
            elif target_class in (vigra.filters.Kernel1D, vigra.filters.Kernel2D):
                data = np.array(entity)
                obj = vu.kernelfromarray(data)
                
            else:
                obj = target_class # for now
            
    else: # entity is a group
        # NOTE: 2022-10-06 13:50:07
        # some specialized arrray-like data objects (e.g. neo DataObject etc)
        # are encapsulatd in h5py Group and store their actual array data in 
        # h5py Dataset children of this Group;
        # therefore, we parse these datasets HERE instead of calling objectFromHDF5Entity
        # recursively as we do for Groups storing regular python collections!
        
        if target_class == vigra.VigraArray:
            obj = group2VigraArray(entity, cache)
        else:
            mro = inspect.getmro(target_class)
            # print(f"\ttarget_class {target_class} MRO: {mro}")
            if dict in mro:
                obj = target_class()
                for k in entity.keys():
                    if k.endswith("_key"):
                        # custom dict keys
                        key_value_grp = entity[k]
                        # exepect two entities: "key" and "value"
                        key = objectFromHDF5Entity(key_value_grp["key"], {})
                        value = objectFromHDF5Entity(key_value_grp["value"], cache)
                        obj[key] = value
                    else:
                        # regular (sane) case of dict with str keys
                        obj[k] = objectFromHDF5Entity(entity[k], cache)
                        
                # print(f"objectFromHDF5Entity {obj.__class__.__name__}: {obj}")
                    
            # elif any(k in mro for k in (list, NeoObjectList)):
            elif list in mro:
                obj = target_class()
                for k in entity.keys():
                    o = objectFromHDF5Entity(entity[k], cache)
                    obj.append(o)
                    
            elif tuple in mro:
                obj = list()
                for k in entity.keys():
                    o = objectFromHDF5Entity(entity[k], cache)
                    obj.append(o)
                    
                obj = tuple(obj)
                
                    
            elif neo.core.baseneo.BaseNeo in inspect.getmro(target_class):
                obj = group2neo(entity, target_class, cache)
                
            elif target_class == neo.core.spiketrainlist.SpikeTrainList:
                items = list()
                for k in entity.keys():
                    o = objectFromHDF5Entity(entity[k], cache)
                    items.append(o)
                    
                obj = target_class(items = tuple(items))
                
            elif target_class == NeoObjectList:
                items = list()
                item_types = list()
                for k in entity.keys():
                    o = objectFromHDF5Entity(entity[k], cache)
                    items.append(o)
                    item_types.append(type(o))
                    
                # print(f"\tcontained types -> {item_types}")
                    
                obj = target_class(item_types)
                obj.extend(items)
                
            elif target_class in (pd.DataFrame, pd.Series):
                # TODO multi-index types, groupings ?!?
                data = np.array(entity["data"]) # a structarray
                
                # names of the data fields; 
                #"index" should aleready be there and represents the original
                # index of the original DataFrame stored here...
                names = [n for n in data.dtype.names if n != "index"]
                
                obj = target_class(data[names], index = data["index"])
                    
            else:
                # TODO:
                # vigra.VigraArray (follow the model for neo DataObject)
                obj = target_class # for now
            
    cache[entity] = obj
    
    # print(f"objectFromHDF5Entity: obj = {obj}")
    
    return obj


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
                        
                if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
                    v = jsonio.loads(v)
                    
            elif isinstance(v, str):
                if v.startswith("{") and v.endswith("}"):
                    v = jsonio.loads(v)
                    
                elif "datetime" in v:
                    # print(f"attrs2dict {v}")
                    parts = v.split(" ")
                    if len(parts) == 2:
                        klass, isofmt = parts
                        v = eval(f"{klass}.fromisoformat('{isofmt}')")
                    else:
                        v = None # BUG 2024-07-21 23:16:35 FIXME/TODO
                    #     klass = parts[0]
                    # klass, isofmt = v.split(" ")
                    # v = eval(f"{klass}.fromisoformat('{isofmt}')")
                    # if "timedelta" in v:
                    #     v = eval(v)
                    # else:
                    #     klass, isofmt = v.split(" ")
                    #     v = eval(f"{klass}.fromisoformat('{isofmt}')")
                    
                elif "pq.Quantity" in v:
                    # leave here for back-compatibility
                    try:
                        v = eval(v)
                    except:
                        vv = v.replace("pq.Quantity(", "").replace(")", "").replace("pq.", "")
                        v = str2quantity(vv)
                    
                elif v.startswith("QUANTITY "):
                    v = v.replace("QUANTITY ", "")
                    v = str2quantity(v)
                    
                elif v.startswith("ENUM "):
                    # print(f"attrs2dict: {v} ({type(v).__name__})")
                    _, v = v.split(" ")
                    # print(f"v.split: {_} {v} ({type(v).__name__})")
                    srcstr = v
                    try:
                        v = eval(v)
                    except:
                        target, args = v.split("(")
                        args = f"({args}" # reattach opening parenthesis
                            
                        obj = parse_module_class_path(target)
                        if not isinstance(obj, type):
                            raise RuntimeError(f"'{srcstr}' did not resolve to a type")
                        module = get_loaded_module(obj.__module__)
                        
                        v2 = f"{obj.__name__}{args}"
                        
                        # print(f"new eval: '{v2}'")
                        
                        v = eval(v2, module.__dict__)
                        # if isinstance(v, type)
                    
        except:
            # print(f"k = {k} v = {v} has dtype: {v.dtype if hasattr(v, 'dtype') else 'no'}")
            traceback.print_exc()
            
        ret[k] = v
        
    return ret

def extract_array_annotations(obj):
    """Extracts array annotations from neo data objects
    """
    # NOTE: 2022-10-07 11:27:36
    # we don't store array_annotations directly (as an ArrayDict); instead,
    # we copy it into a regular dict then we re-apply it to the object at
    # reconstruction time
    array_annotations = getattr(obj,"array_annotations", None)
    arrann = None
    if isinstance(array_annotations, ArrayDict) and len(array_annotations): 
        # len is the number of fields, not 'length' a.k.a channels!
        # NOTE: skip silently is length different for obj size on axis 1
        # ATTENTION: the 'length' property of the ArrayDict seems to be the 
        # same as the 2nd dimension of the signal's array (documentation
        # is a bit misleading), and NOT the same as then number of fields
        # in the ArrayDict !!! (each field is a numpy array)
        # 
        
        # print(f"h5io.extract_array_annotations: obj shape= {obj.shape}, array_annotations = {array_annotations}")
        arrann = dict(array_annotations)
            
        # if array_annotations.length == obj.shape[1]:
        #     arrann = dict(array_annotations)
                
    return arrann
                
def makeDataTypeAttrs(data):
    if not isinstance(data, type):
        data = type(data)

    attrs = dict()
    
    attrs["type_name"] = data.__name__
    attrs["module_name"] = data.__module__
    attrs["python_class"] = ".".join([data.__module__, data.__name__])
    
        
    return makeAttrDict(**attrs)
        
def getFileGroupChild(fileNameOrGroup:typing.Union[str, h5py.Group],
                       pathInFile:typing.Optional[str] = None, 
                       mode:typing.Optional[str]=None) -> typing.Tuple[typing.Optional[h5py.File], h5py.Group, typing.Optional[str]]:
    """Common tool for coherent syntax of h5io read/write functions.
    Inspired from vigra.impex.readHDF5/writeHDF5, (c) U.Koethe
    TODO/FIXME: Not used ?!?
    """
    if mode is None or not isinstance(mode, str) or len(mode.strip()) == 0:
        mode = "r"
        
    external = False
    # print("getFileGroupChild fileNameOrGroup", fileNameOrGroup, "pathInFile", pathInFile, "mode", mode)
    
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
        # FIXME: 2022-10-09 15:53:52
        # this is contentious for functions provided by 3rd party libraries, 
        # because there is no pythonic access to their signatures
        # (e.g. Boost.python.functions)
        return makeAttrDict (function_or_method = jsonio.dumps(prog.signature2Dict(obj)))
    
    if obj is None:
        return makeEntryName(obj), {}
    
    if not isinstance(oname, str) or len(oname.strip()) == 0:
        oname = getattr(obj, "name", "")
        
    obj_attrs = makeDataTypeAttrs(obj)
    
    if isinstance(obj, (neo.core.baseneo.BaseNeo)):
        # NOTE: 2022-10-09 17:36:29
        # these include ScanData, AnalysisUnit
        for a in obj._recommended_attrs:
            obj_attrs[a[0]] = makeAttr(getattr(obj, a[0]))
    
    # as_group = isinstance(obj, (collections.abc.Iterable, neo.core.container.Container)) and not isinstance(obj, (str, bytes, bytearray, np.ndarray))
    as_group = isinstance(obj, (collections.abc.Iterable, neo.core.baseneo.BaseNeo)) and not isinstance(obj, (str, bytes, bytearray, np.ndarray))
    
    if not as_group:
        obj_attrs.update(makeDatasetAttrs(obj))
    
    if as_group: # make sure there is a "name" attribute there
        if "name" not in obj_attrs:
            obj_attrs["name"] = makeAttr(oname)
        
    else:
        obj_attrs.update(makeDatasetAttrs(obj))
        
    target_name = makeEntryName(obj)
    
    return target_name, obj_attrs

@singledispatch
def makeDatasetAttrs(obj):
    """Generates an attribute dict for HDF5 datasets.
    Only to be used for hdf5 Datasets that actually store data (that is, 
    numeric arrays)
    """
    if isinstance(obj, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
        # NOTE: 2021-11-18 12:31:59
        # in vigranumpy all kernels are float ?
        return makeAttrDict(dtype = jsonio.dtype2JSON(np.dtype(float)))
        
    return dict()

@makeDatasetAttrs.register(np.ndarray)
def _(obj):
    attrs = dict()
    dtype = obj.dtype
    fields = dtype.fields
    attrs["dtype"] = jsonio.dtype2JSON(obj.dtype)
    if fields is not None: # structured array or recarray; type is in makeDataTypeAttrs
        attrs["dtype_fields"] = list(f for f in obj.dtype.fields)
    
    return makeAttrDict(**attrs)

@makeDatasetAttrs.register(pq.Quantity)
def _(obj):
    attrs = dict()
    attrs["dtype"] = jsonio.dtype2JSON(obj.dtype)
    attrs["units"] = obj.units
    
    return makeAttrDict(**attrs)

@makeDatasetAttrs.register(neo.core.dataobject.DataObject)
def _(obj):
    # NOTE: flag for deprecation:
    # these attributes are to be stored in the attrs of the parent entity
    # except for the dtype and units
    # moreover, segment needs to be stored as a separate child entity in the parent
    # group
    ret = {"name": obj.name}
    
    return makeAttrDict(**ret)

@makeDatasetAttrs.register(vigra.VigraArray)
def _(obj):
   return makeAttrDict(dtype = jsonio.dtype2JSON(obj.dtype), 
                       axistags = obj.axistags.toJSON())

@makeDatasetAttrs.register(datetime.timedelta)
def _(obj):
    attrs = dict()
    for attribute in ("days", "seconds", "microseconds"):
        attrs[attribute] = int(getattr(obj, attribute))
        
    
    # for attribute in ("days", "seconds", "microseconds"):
    #     attrs[f"resolution_{attribute}"] = int(getattr(obj.resolution, attribute))

    return attrs
        
@singledispatch
def makeAxisDict(obj, axisindex:int):
    """Returns a dict with axis information for storage in HDF5 hierarchy.
    
    Attached to the 'attrs' attribute of the axis Dataset in 'makeAxisSale'.
    
    The axis informtion depends on the type of obj (singledispatch function) 
    
    Used to build dimension scales for a signal dataset and where necessary,
    additional datasets with data array associated with the axis.
    
    The dimension scale for a signal dataset axis (or dimension) is constructed
    from an axis dataset (h5py.Dataset) stored in an axes group alongside the
    object's data set (i.e. in the same parent group as the object's data set).
    
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
    
    data = dict((f"cal_{k}", v) for k,v in axiscal.data.items()) # axiscal.data
    
    axdict = {"key": axisinfo.key,
              "typeFlags": axisinfo.typeFlags,
              "description": axisinfo.description,
              "resolution": axisinfo.resolution}
    
    axdict.update(data)
    
    return makeAttrDict(**axdict)
    
    # return makeAttrDict(key          = axisinfo.key,
    #                     typeFlags    = axisinfo.typeFlags,
    #                     description  = axisinfo.description, 
    #                     resolution   = axisinfo.resolution, 
    #                     **data)
    
@makeAxisDict.register(vigra.AxisTags)
def _(obj, axisindex:typing.Union[int, str]):
    # each dimenson has its own axistag
    from imaging import axisutils, axiscalibration
    from imaging.axiscalibration import (AxisCalibrationData, ChannelCalibrationData, AxesCalibration)
    if isinstance(axisindex, int):
        if axisindex < 0 or axisindex >= len(obj):
            raise ValueError(f"Invalid axisindex {axisindex}")
        
    elif isinstance(axisindex, str):
        if axisindex not in obj:
            raise ValueError(f"Invalid axisindex {axisindex}")
        
    else:
        raise TypeError(f"Invalid axisindex type; expecting a str or int, got {tytpe(axisindex).name} instead.")
    
    
    axisinfo = obj[axisindex]
    
    axiscal = AxisCalibrationData(axisinfo)
    
    data = dict((f"cal_{k}", v) for k,v in axiscal.data.items()) # axiscal.data
    
    return makeAttrDict(key            = axisinfo.key,
                        typeFlags      = axisinfo.typeFlags,
                        description    = axisinfo.description, 
                        resolution     = axisinfo.resolution,
                        **data)

@makeAxisDict.register(neo.core.dataobject.DataObject)
def _(obj:neo.core.dataobject.DataObject, axisindex:int):
    # NOTE: 2022-10-10 14:25:50 for ALL DataObject types
    # this INCLUDES BaseNeo types as well as neo.SpikeTrain
    # axis 0 = domain axis (e.g. times)
    # axis 1 = channel axis (may be singleton for a single-channel signal)
    #           contains array_annotations as well !!!
    if isinstance(axisindex, int):
        if axisindex < 0 or axisindex >= obj.ndim:
            raise ValueError(f"Invalid axisindex {axisindex} for {type(obj).__name__} object")
        
    else:
        raise TypeError(f"'axisindex' expected to be an int; got {type(axisindex).__name__} instead")
    
    seed = dict()
    seed["name"] = name_from_unit(obj.times.units) if axisindex == 0 else name_from_unit(obj.units)
    seed["key"] = name_from_unit(obj.times.units, True) if axisindex == 0 else name_from_unit(obj.units, True)
    seed["array_annotations"] = extract_array_annotations(obj)
    
    # NOTE: 2022-10-07 11:26:34
    # all dataobject seem to have array_annotations now, except for ImageSequence
    # if axisindex == 1:
    #     seed["array_annotations"] = extract_array_annotations(obj)
        
    if isinstance(obj, neo.core.basesignal.BaseSignal):
        ret = makeNeoSignalAxisDict(obj, axisindex)
        
    else: 
        # NOTE: 2022-10-10 22:41:09
        # data objects that are NOT base signals; 
        ret = makeNeoDataAxisDict(obj, axisindex)
        
    seed.update(ret)
    
    return makeAttrDict(**seed)

# this below is not used ?!?
@makeAxisDict.register(vigra.filters.Kernel1D)
def _(obj, axisindex):
    if axisindex < 0 or axisindex >= 2:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")
    
    ret = dict()
    ret["key"] = "x" if axisindex == 0 else "v"
    ret["name"] = "x" if axisindex == 0 else "values"
    
    return ret
    
# this below is not used ?!?
@makeAxisDict.register(vigra.filters.Kernel2D)
def _(obj, axisindex):
    if axisindex < 0 or axisindex >= 3:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")
    ret = dict()
    ret["key"] = "x" if axisindex == 0 else "y" if axisindex == 1 else "v"
    ret["name"] = "x" if axisindex == 0 else "y" if axisindex == 1 else "values"
    
    return ret
    
    # return {"key": "s"} if axisindex == 0 else {"key":"c"} if axisindex == 1 else {"key":"v"}
        
@singledispatch        
def makeNeoSignalAxisDict(obj, axisindex:int):
    """Encode object type-specific information into an Axis entity.
    
    Supplements 'makeAxisDict'
    
    """
    raise NotImplementedError(f"makeNeoSignalAxisDict: {type(obj).__name__} objects are not supported")

@makeNeoSignalAxisDict.register(neo.AnalogSignal)
def _(obj, axisindex):
    # only two axes
    ret = dict()
    if axisindex == 0:
        # domain axis
        ret["origin"]           = obj.t_start
        ret["sampling_rate"]    = obj.sampling_rate
        ret["sampling_period"]  = obj.sampling_period
        ret["units"]            = obj.t_start.units
        ret["dtype"]            = jsonio.dtype2JSON(obj.t_start.dtype)
        
    elif axisindex == 1: 
        # data (channel) axis
        # NOTE: channel information is stored in array_annotations
        # hence encoded as a separate entity; data in all channels have the
        # same "units" as they represent the same kind of physical measure
        # (unlike VigraArray, where each channel MAY represent different
        # physical measures, e.g. phase & angle in a Fourier transform...)
        ret["units"] = obj.units
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)

    return ret

@makeNeoSignalAxisDict.register(DataSignal)
def _(obj, axisindex):
    # only two axes
    ret = dict()
    if axisindex == 0:
        # domain axis
        ret["origin"]           = obj.t_start
        ret["sampling_rate"]    = obj.sampling_rate
        ret["sampling_period"]  = obj.sampling_period
        ret["units"]            = obj.t_start.units
        ret["dtype"]            = jsonio.dtype2JSON(obj.t_start.dtype)
        
    elif axisindex == 1:
        # NOTE: channel information is stored in array_annotations
        # hence encoded as a separate entity; data in all channels have the
        # same "units" as they represent the same kind of physical measure
        # (unlike VigraArray, where each channel MAY represent different
        # physical measures, e.g. phase & angle in a Fourier transform...)
        # data (channel) axis
        ret["units"] = obj.units
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)

    else:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")

    return ret

@makeNeoSignalAxisDict.register(neo.IrregularlySampledSignal)
def _(obj, axisindex):
    # only two axes
    ret = dict()
    if axisindex == 0:
        # domain axis
        # NOTE: the times (irregular sampling) are stored as a separate
        # Dataset 
        ret["origin"] = obj.t_start
        ret["units"] = obj.t_start.units
        ret["dtype"] = jsonio.dtype2JSON(obj.t_start.dtype)
        
    elif axisindex == 1:
        ret["units"] = obj.units
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)
        
    else:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")

    return ret

@makeNeoSignalAxisDict.register(IrregularlySampledDataSignal)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["origin"] = obj.t_start
        ret["units"] = obj.t_start.units
        ret["dtype"] = jsonio.dtype2JSON(obj.t_start.dtype)

    elif axisindex == 1:
        ret["units"] = obj.units
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)
        
    else:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")

    return ret

@makeNeoSignalAxisDict.register(neo.ImageSequence)
def _(obj, axisindex):
    # three axes but NOTE: 
    # 𝟏 First axis (axis 0) is the time axis (one image "frame"/time point)
    # 
    # 𝟐 Second axis (axis 1), IN THIS CONTEXT, applies to both 2nd and 3rd dimensions,
    # and represents the non-temporal domain (typically, space); these effectively
    # are the 1st (rows, a.k.a, "height") and second (columns, a.k.a "width") 
    # axes of ONE frame. This strategy is justified by the fact that both domain
    # dimensions 2 & 3 represent the same physical measure (e.g. space, etc) - 
    # unlike VigraArrays where rows and columns in a frame MAY represent different
    # physical dimensions (e.. phase & angle in a Fourier transform, etc)
    #
    # 𝟑 Third axis, IN THIS CONTEXT is the channel axis i.e. it stores the units 
    # associated with the physical mesaure represented by the pixel values
    # (this coresponds to the "units" parameter in ImageSequence constructor)
    ret = dict()
    if axisindex == 0:
        # time domain
        ret["key"] = "t"
        ret["name"] = "frames"
        ret["units"] = obj.t_start.units
        ret["origin"] = obj.t_start
        ret["sampling_rate"] = obj.sampling_rate
        
    elif axisindex == 1: # ImageSequence axis 1 or 2
        # space domain - same resolution & units
        ret["key"] = "s"
        ret["name"] = "height" if axisindex == 1 else "width"
        ret["spatial_scale"] = obj.spatial_scale # this is a python Quantity (usually, pq.um for μm) but is not enforced?
        ret["units"] = obj.spatial_scale.units if isinstance(obj.spatial_scale, pq.Quantity) else pq.um # good default ?!?
        
    elif axisindex == 3:
        ret["units"] = obj.units
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)
        ret["name"] = name_from_unit(obj.units)
        ret["key"] = name_from_unit(obj.units, True)
        
    else:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")

    return ret

@singledispatch
def makeNeoDataAxisDict(obj, axisindex):
    """Encode object type-specific information into an Axis entity.
    
    Supplements 'makeAxisDict'
    
    """
    raise NotImplementedError(f"makeNeoDataAxisDict: {type(obj).__name__} objects are not supported")
    
@makeNeoDataAxisDict.register(neo.SpikeTrain)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["origin"] = obj.t_start
        ret["time_units"] = obj.times.units
        ret["time_dtype"] = jsonio.dtype2JSON(obj.times.dtype)
        ret["left_sweep"] = obj.left_sweep
        #ret["__waveforms__"] = obj.waveforms # → as separate child Dataset
        ret["end"] = obj.t_stop
        ret["units"] = obj.units
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)
        waveforms = getattr(obj, "waveforms", None)
        if isinstance(waveforms, np.ndarray) and waveforms.size > 0:
            ret["sampling_rate"] = obj.sampling_rate
        
    else:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")

    return ret

@makeNeoDataAxisDict.register(neo.Event)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["labels"] = obj.labels # labels are contained in the axis_0 attrs
        ret["time_units"] = obj.times.units
        ret["time_dtype"] = jsonio.dtype2JSON(obj.times.dtype)
        ret["units"] = obj.units
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)
        
    else:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")

    return ret

@makeNeoDataAxisDict.register(DataMark) # includes TriggerEvent
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["labels"] = obj.labels # labels are contained in the axis_0 attrs
        ret["time_units"] = obj.times.units
        ret["time_dtype"] = jsonio.dtype2JSON(obj.times.dtype)
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)
        ret["units"] = obj.units

    else:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")

    return ret

@makeNeoDataAxisDict.register(neo.Epoch)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["labels"] = obj.labels # labels are contained in the axis_0 attrs
        # ret["durations"] = obj.durations # durations ARE the axis_0 dataset
        ret["time_units"] = obj.times.units
        ret["time_dtype"] = jsonio.dtype2JSON(obj.times.dtype)
        ret["units"] = obj.units
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)
        
    else:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")

    return ret

@makeNeoDataAxisDict.register(DataZone)
def _(obj, axisindex):
    ret = dict()
    if axisindex == 0:
        ret["labels"] = obj.labels # labels are contained in the axis_0 attrs
        # ret["durations"] = obj.durations # durations ARE the axis_0 dataset
        ret["time_units"] = obj.times.units
        ret["time_dtype"] = jsonio.dtype2JSON(obj.times.dtype)
        ret["units"] = obj.units
        ret["dtype"] = jsonio.dtype2JSON(obj.dtype)

    else:
        raise ValueError(f"Invalid axis index {axisindex} for {type(obj).__name__} object")

    return ret

@safeWrapper
# def makeAxisScale(obj, dset:h5py.Dataset, axesgroup:h5py.Group, dimindex:int,axisdict:dict,compression:str="gzip",chunks:bool=None,track_order=True):
def makeAxisScale(obj, dset:h5py.Dataset, axesgroup:h5py.Group, dimindex:int,
                  compression:str="gzip",chunks:bool=None,track_order=True):
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
    HDF5 Dataset: The newly-created axis data set. Its 'attrs' property contains
    specific axis attributes (e.g. unit, make, key, origin, sampling rate etc)
    depending on the type of obj (see 'makeAxisDict') 
        
    """
    
    # create an empty data set, store in its 'attrs' property
    # NOTE: irregular signals and array-like data objects Epoch & Zone also
    # provide a 'parallel' set of data  - the 'durations' property - we store 
    # that separately as a dimension scale labeled 'durations' attached to
    # this data set (see NOTE: 2021-11-12 16:05:29 and NOTE: 2021-11-12 17:35:27
    # in self.writeDataObject) 
    
    axis_dict  = makeAxisDict(obj, dimindex)
    # print(f"h5io.makeAxisScale axis_dict = {axis_dict}")
    
    axis_dset_name = f"axis_{dimindex}"
    
    if isinstance(obj, (neo.IrregularlySampledSignal, IrregularlySampledDataSignal,
                        neo.Event, DataMark)) and obj.size > 0:
        axis_dset = makeHDF5Entity(obj.times, axesgroup,
                                     name = axis_dset_name,
                                     compression = compression, 
                                     chunks = chunks,
                                     track_order = track_order)
        
    elif isinstance(obj, (neo.Epoch, DataZone)) and obj.size > 0:
        axis_dset = makeHDF5Entity(obj.durations, axesgroup,
                                     name = axis_dset_name,
                                     compression = compression, 
                                     chunks = chunks,
                                     track_order = track_order)
    else:
        axis_dset = axesgroup.create_dataset(axis_dset_name, data=h5py.Empty("f"))
        
    try:
        axis_dset.attrs.update(axis_dict)
        
        # for debugging:
        # for key, val in axis_dict.items():
        #     print(f"{key} : {val} ")
        #     axis_dset.attrs[key] = val
        
        axis_name = axis_dict["name"] if "name" in axis_dict else axis_dict["cal_name"] if "cal_name" in axis_dict else axis_dict["key"] if "key" in axis_dict else axis_dict["cal_key"] if "cal_key" in axis_dict else axis_dset_name
        
        axis_dset.make_scale(axis_name)
        dset.dims[dimindex].attach_scale(axis_dset)
        dset.dims[dimindex].label = axis_name
        
    except Exception as e:
        print(f"\n***\nIn object {type(obj).__name__}:")
        print(f"axis {dimindex}")
        # print(f"axis_dict: {axis_attrs} for axis {dimindex}")
        raise e
        
    return axis_dset

@safeWrapper
def makeHDF5Entity(obj, group:h5py.Group, name:typing.Optional[str]=None,
                   oname:typing.Optional[str]=None,
                   compression:typing.Optional[str]="gzip",
                   chunks:typing.Optional[bool]=None,
                   track_order:typing.Optional[bool] = True, 
                   entity_cache:typing.Optional[dict]=None,
                   **kwargs):# -> typing.Union[h5py.Group, h5py.Dataset]:
    """
    Encodes Python objects into a HDF5 entity (Group or Dataset).
    
    This is the "entry point" for encoding (writing) a Python object as a HDF5
    data structure (file), in Scipyen.
    
    Depending on the type of Python object, the object's data are stored as one
    or more HDF5 entities collected in a tree-like structure, in a parent HDF5
    Group. The tree-like layout is characteristic to the Python data type.
    
    As a rule of thumb, numeric scalars, arrays and other plain old data types
    (str, bool, bytes, bytearray) are stored as HDF5 Dataset "leaves".
    
    Iterable objects, as well as more complex object types are stored as HDF5
    Group objects, containing children (HDF5 Group or Dataset) that correspond 
    to specific attributes of the Python object.
    
    Information about the Python object's class and, where necessary, about any
    specific attributes of the Python's object, are stored in the 'attrs' property
    of the HDF5 entities.
    
    In addition, where possible, the Dataset entities associate axis scales 
    containing meta-information (e.g., physcial units) associated with the 
    numeric data in the Dataset.
    
    For details, please see doc/h5io.md in Scipyen's source tree.
    
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
        'pandas2Structarray' function); therefore, they will be stored as a
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

    # NOTE: 2024-07-18 14:00:22
    # 1. check if the data type defines an instance method 'makeHDF5Entity'; 
    entity_factory_method = getattr(obj, "makeHDF5Entity", None)
    
    # 2. check if a custom-made makeHDF5Entity function is passed here (this
    # will override the instance method above, if defined)
    if entity_factory_method is None:
        entity_factory_method = kwargs.pop("makeHDF5Entity", None)
        
    # 3. a makeHDF5Entity method or function is available from (1) or (2) above
    #   → use it 
    if inspect.ismethod(entity_factory_method):
        target_name, obj_attrs = makeObjAttrs(obj, oname=oname)
            
        if isinstance(name, str) and len(name.strip()):
            target_name = name
            
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity
            return cached_entity
        
        # call either the makeHDF5Entity method of the object;s class, or the 
        # custom (3rd party£makeHDF5Entity), if it exists
        return entity_factory_method(group, target_name, oname, compression, chunks,
                                     track_order, entity_cache)

    if not isinstance(group, h5py.Group):
        raise TypeError(f"'group' expected to be a h5py.Group (or h5py.File); got {type(group).__name__} instead")

    target_name, obj_attrs = makeObjAttrs(obj, oname=oname)
    
    if isinstance(name, str) and len(name.strip()):
        target_name = name
        
    if not isinstance(entity_cache, dict):
        entity_cache = dict()
    
    if obj is None:
        # → straight to Dataset child of group
        #
        # don't bother with hard links here...
        entity = group.create_dataset(target_name, data = h5py.Empty("f"))
        
        return entity
    
    if isinstance(obj, (vigra.filters.Kernel1D, vigra.filters.Kernel2D)):
        # vigra Kernel types → straight to HDF5 Dataset child of group
        # TODO: 2022-10-09 23:29:28
        # contemplate storing as h5py.Group with child Dataset and child
        # axes Group (although this complicates things...)
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity # hard link
            return cached_entity
            
        data = vu.kernel2array(obj, True) # need to pass compact=True to get an array!!!
        
        entity = group.create_dataset(target_name, data = data, 
                                      compression = compression, 
                                      chunks = chunks)
        
        entity.attrs.update(obj_attrs)
        
        storeEntityInCache(entity_cache, obj, entity)
        
        return entity
    
    elif isinstance(obj, (pd.DataFrame, pd.Series)):
        # pandas types → HDF5 Group child of group
        # TODO/FIXME: pandas_dtypes?
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity # hard link
            return cached_entity

        data, categorical_info, pandas_dtypes = pandas2Structarray(obj)

        entity = group.create_group(target_name,track_order=track_order)
        
        obj_entity = makeHDF5Dataset(data, entity, name="data",
                                     compression=compression,
                                     chunks=chunks,
                                     track_order=track_order,
                                     entity_cache = entity_cache)
        
        if len(categorical_info):
            catgrp = makeHDF5Group(categorical_info, entity, name="categories",
                                   compression=compression, chunks=chunks,
                                   track_order=track_order) # no entity cache here...
            
        entity.attrs.update(obj_attrs)
            
        storeEntityInCache(entity_cache, obj, entity)
        
        return entity
    
    elif isinstance(obj, (vigra.VigraArray, neo.core.dataobject.DataObject)):
        # NOTE: 2021-11-19 11:34:38
        # VigraArray and neo DataObjet are stored as a Group child of group.
        #
        # In turn the created group has  the following children:
        # • a Dataset with the array data
        # • a Group with axes Datasets:
        #   ∘ one axis Dataset per array dimension, with attrs property containing
        #       calibration data for the corresponding dimension (time, space, 
        #       etc)
        #   ∘ in particular, the channel axis Dataset attrs property contains 
        #       calibration data for the array values in each channel (i.e., 
        #       units, calibration factor: linear mapping between pixel value
        #       and physcial quantity)
        #   ∘ in turn, these axis datasets are used a s axis scales (dimscales)
        #     attached to the child data Dataset (see first bullet point above)
        
        
        # make a sub-group and place the main data set and axes data set inside
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity # hard link
            return cached_entity
                    
        # NOTE: 2022-10-08 12:10:27
        # this is the subgroup that's being created here, and is returned by this
        # function
        entity = group.create_group(target_name, track_order=track_order)
        
        # this call here WILL NOT check for cached obj_entity/store new obj_entity !
        # NOTE: 2021-11-21 12:49:10
        # obj_entity is a h5py.Group
        # for vigra.VigraArray and neo.core.dataobject.DataObject objects !!!
        # see single dispatched versions of makeDataset
        # 
        # makeHDF5Dataset populates 'entity' (here, a Group) with a Dataset
        # and returns the Dataset.
        #
        # The returned 'obj_entity' is the newly-created Dataset as a child of 
        # the newly-created Group 'entity', so technically we don't need it here.
        obj_entity = makeHDF5Dataset(obj, entity, name=target_name, 
                                       compression = compression,
                                       chunks = chunks, 
                                       track_order = track_order,
                                       entity_cache = entity_cache)
        
        entity.attrs.update(obj_attrs)
        
        storeEntityInCache(entity_cache, obj, entity)
        
        return entity
    
    elif isinstance(obj, neo.core.spiketrainlist.SpikeTrainList):
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity
            return cached_entity
        
        items = [s for s in obj] # list of SpikeTrain objects
        
        entity = makeHDF5Group(items, group, name = name, 
                               compression = compression, chunks = chunks,
                               track_order = track_order,
                               entity_cache = entity_cache)
        
        entity.attrs.update(obj_attrs) # will include name, description, file_origin
        
        storeEntityInCache(entity_cache, obj, entity)
        
    elif isinstance(obj, neo.ChannelView):
        # ChannelView → h5py.Group child of group
        cached_entity = getCachedEntity(entity_cache, obj)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity
            return cached_entity
        
        entity = group.create_group(target_name, track_order=track_order)
        
        entity.attrs.update(obj_attrs) # will include name, description, file_origin
        
        index_entity = getCachedEntity(entity_cache, obj.index)
        
        if isinstance(index_entity, (h5py.Dataset, h5py.Group)):
            entity["index"] = index_entity
        else:
            index_entity = makeHDF5Dataset(obj.index, entity, name="index",
                                        compression = compression, chunks = chunks, 
                                        track_order = track_order,
                                        entity_cache = entity_cache)
        
        
        # populate the channel view with signal entities (the "obj" property of ChannelView)
        signal_entity = getCachedEntity(entity_cache, obj.obj)
        
        if isinstance(signal_entity, (h5py.Dataset, h5py.Group)):
            entity["obj"] = signal_entity
        else:
            if isinstance(obj.obj, neo.core.basesignal.BaseSignal):
                signal_entity = makeHDF5Dataset(obj.obj, entity, name = "obj",
                                        compression = compression, chunks = chunks, 
                                        track_order = track_order,
                                        entity_cache = entity_cache)
            
        return entity
    
    elif isinstance(obj, enum.Enum):
        # we also can store Enums as HDF5 attr, see makeAttr in this module
        # → h5py.Dataset child of group,  with h5py.enum_dtype
        cached_entity = getCachedEntity(entity_cache, obj)
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
        if (isinstance(obj, (collections.abc.Iterable, neo.core.container.Container)) or hasattr(type(obj),"__iter__")) and \
            not isinstance(obj, (str, bytes, bytearray, np.ndarray, neo.core.spiketrainlist.SpikeTrainList)):
            # neo Container, tuple, list, dict → h5py.Group child of group
            # CAUTION: 2022-10-10 22:05:17
            # neo.core.spiketrainlist.SpikeTrainList is a collections.abc.Iterable
            # but NOT A LIST ❗
            # hence it deserved special treatment, above
            #
            # NOTE: 2024-06-18 19:09:09 added/included NeoObjectList
            factory = makeHDF5Group
            
        else:
            # everything else → h5py.Dataset child of group
            factory = makeHDF5Dataset
            
        # this call here WILL check for cached entities and WILL store entity if
        # not already in cache
        return  factory(obj, group, name = name, compression = compression, 
                       chunks = chunks, track_order = track_order, 
                       entity_cache = entity_cache)
        

def makeHDF5Dataset(obj, group: h5py.Group, name:typing.Optional[str]=None, 
                    compression:typing.Optional[str]="gzip", 
                    chunks:typing.Optional[bool] = None, track_order:typing.Optional[bool]=True, entity_cache:typing.Optional[dict] = None):
    """Creates a HDF5 Dataset in group based on obj.
    Delegates to makeDataset to create a data set then adorns its attrs 
    with obj-specific information via the singledispatch function 'makeDataset'.
    
    Returns a HDF5 Dataset that has been created as a child of 'group'.
    Therefore, thechnically you don't need to do anything with the returned
    Dataset, because it has already been added to the parent HDF5 Group 'group'.
    """
    target_name, obj_attrs = makeObjAttrs(obj)
    if isinstance(name, str) and len(name.strip()):
        target_name = name

    try:
        dset = makeDataset(obj, group, obj_attrs, target_name, 
                            compression = compression, chunks = chunks,
                            track_order = track_order, entity_cache = entity_cache)
        return dset
    except:
        print(f"makeHDF5Dataset offending object: {obj} (type: {type(obj)}) for target name {target_name}")
        raise
        

@singledispatch
def makeDataset(obj, group:h5py.Group, attrs:dict, name:str, 
                compression:typing.Optional[str]="gzip", chunks:typing.Optional[bool] = None, track_order=True, entity_cache = None):
    # for scalar objects only, and basic python sequences EXCEPT for strings
    # because reading back strings can be confused with stored bytes data
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    # NOTE: 2022-12-21 22:00:52
    # in Python 3.10 bool is a numbers.Number
    supported_types = (numbers.Number, tuple, list, deque)
    
    if not isinstance(obj, supported_types):
        warnings.warn(f"makeDataset: {type(obj).__name__} objects are not supported")
        dset = group.create_dataset(name, data = h5py.Empty("f"), track_order=track_order)
    else:
        # HDF5 prevents the use of compression and chunks with scalars!
        if isinstance(obj, numbers.Number):
            compression = None
            chunks = None
            
        dset = group.create_dataset(name, data = obj, compression=compression,
                                    chunks=chunks, track_order=track_order)
        
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(type(None))
def _(obj, group, attrs:dict, name:str, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    dset =  group.create_dataset(name, data = h5py.Empty("f"), track_order=track_order)
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(str)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    try:
        # replace NULLs with 0:
        # o = obj.replace("\0", "0")
        if len(obj.strip().strip(b"\x00".decode())) == 0: # empty string
            dset = group.create_dataset(name, data = h5py.Empty("f"), track_order=track_order)
        else:
            dset = group.create_dataset(name, data = np.array(obj, dtype = h5py.string_dtype()),
                                        track_order=track_order)
            
    except:
        print(f"makeDataset<str> offending object: {obj} (len: {len(obj)})")
        raise
            
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(bytes)
@makeDataset.register(bytearray)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    try:
        
        data = np.array(obj.hex(), dtype = h5py.string_dtype())
        
        # if obj.isascii():
        #     data = np.array(obj.decode(), dtype=h5py.string_dtype())
        # 
        # else:
        #     data = np.array(obj)
        
        if data.size == 0:
            dset = group.create_dataset(name, data = h5py.Empty(f), track_order=track_order)
        
        if data.size == 1:
            dset = group.create_dataset(name, data = data, track_order=track_order)
            
        else:
            dset = group.create_dataset(name, data = data, compression=compression,
                                        chunks = chunks, track_order=track_order)
        
    except:
        print(f"makeDataset<{type(obj).__name__}> offending object: {obj} (len: {len(obj)}) converted to {data}")
        try:
            data = np.array(obj.hex(), dtype=h5py.string_dtype())
            if data.size == 0:
                dset = group.create_dataset(name, data = h5py.Empty(f), track_order=track_order)
            
            if data.size == 1:
                dset = group.create_dataset(name, data = data, track_order=track_order)
                
            else:
                dset = group.create_dataset(name, data = data, compression=compression,
                                            chunks = chunks, track_order=track_order)
        except:
            raise
        
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset
    
@makeDataset.register(datetime.date)
@makeDataset.register(datetime.time)
@makeDataset.register(datetime.datetime)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    return makeDataset(obj.isoformat(), group, attrs, name, compression, chunks, track_order, entity_cache)
    
@makeDataset.register(datetime.timedelta)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    dset = group.create_dataset(name, data = h5py.Empty("f"), track_order=track_order)
    # print(f"attrs {attrs}")
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    
    return dset
    

@makeDataset.register(vigra.VigraArray)
def _(obj, group:h5py.Group, attrs:dict, name:str, compression=None, 
      chunks=None, track_order=True, entity_cache=None):
    """Variant of vigra.impex.writeHDF5 returning the created h5py.Dataset object
    Also populates the dataset's dimension scales.
    
    Modified from vigra.impex.writeHDF5 (python version, (C) U.Koethe)
    """
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    dset_name = "data"
    axgrp_name = "axes"
    
    if obj.size == 0:
        dset = group.create_dataset(dset_name, data = h5py.Empty("f"), track_order=track_order)
    
    # data = obj.transposeToNumpyOrder()
    data = obj
    
    if data.size == 1:
        dset = group.create_dataset(dset_name, data = data)
    else:
        dset = group.create_dataset(dset_name, data = data, track_order=track_order, 
                                    compression = compression, chunks=chunks)
    
    axesgroup = group.create_group(axgrp_name, track_order = track_order)
    
    for axindex in range(obj.ndim):
        makeAxisScale(obj, dset, axesgroup, axindex, compression=compression, 
                      chunks=chunks, track_order=track_order)
        
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
        
    return dset

@makeDataset.register(neo.core.dataobject.DataObject)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    # for all neo DataObject types:
    # 1) create a data set with their contents (these are time stamps)
    # 2) create an axes group with axis 0 
    # 3) if the object has a labels property: create a labels dataset
    # 4) if the object has a wavforms property: create a waveforms dataset
    # 5) create an annotations group (NOT array annotations!!!)
    # 
    # ATTENTION: 2022-10-10 22:44:06
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    dset_name = "data"
    axgrp_name = "axes"
    
    # 1. create a child data Dataset in group
    if obj.size == 0:
        return group.create_dataset(dset_name, data = h5py.Empty("f"), track_order=track_order)
    
    if obj.size == 1:
        dset = group.create_dataset(dset_name, data = obj.magnitude, track_order=track_order)
    else:
        dset = group.create_dataset(dset_name, data = obj.magnitude, track_order=track_order,
                                    compression = compression, chunks = chunks)
        
    # 2. create a child axes Group in group
    axgroup = group.create_group(axgrp_name, track_order=track_order)
    
    # 2.1 populate axes child group with axis Datasets and use these as axis 
    # scales attached to the data Dataset child created in 1. above
    
    for k in range(obj.ndim):
        makeAxisScale(obj, dset, axgroup, k, compression=compression,
                      chunks=chunks, track_order=track_order)
        
    # 3. make a labels Dataset child of group
    # NOTE: 2022-10-11 11:52:59
    # labels are stored in the axis 0 attrs
    # NOTE: 2021-11-20 13:38:33
    # labels for data object types neo.Event, neo.Epoch, DataMark, DataZone, TriggerEvent
    # should go into a Dataset child of the main data object group 'group'
    #
    # Attach the labels Dataset as a axis scale to dim[0] of child data Dataset
    # created at 1. above
    # labels = getattr(obj, "labels", None)
    # if isinstance(labels, np.ndarray) and labels.size:
    #     cached_entity = getCachedEntity(entity_cache, labels)
    #     if isinstance(cached_entity, (h5py.Group, h5py.Dataset)):
    #         group["labels"] = cached_entity
    #     else:
    #         labels_dset = makeHDF5Entity(labels, group, 
    #                                     name ="labels",
    #                                     compression = compression,
    #                                     chunks = chunks)
    #         labels_dset.make_scale("labels")
    #         dset.dims[0].attach_scale(labels_dset)
    
    # 4. Create a waveforms Dataset child of group; attach as axis scale to dim[0]
    # of child data Dataset created at 1. above
    #
    # NOTE: 2021-11-20 13:39:52
    # waveforms of the neo.SpikeTrain objects should go into the main data object
    # group
    #
    # NOTE: 2022-10-05 23:29:51
    # since just before neo 0.11.0 SpikeTrain also have a "left_sweep" attribute
    # which is taken care of by makeAxisScale/makeNeoDataAxisDict above (1.)
    #
    waveforms = getattr(obj, "waveforms", None)
    if isinstance(waveforms, np.ndarray) and waveforms.size > 0:
        cached_entity = getCachedEntity(entity_cache, waveforms)
        if isinstance(cached_entity, (h5py.Group, h5py.Dataset)):
            group["waveforms"] = cached_entity # (hard link)
        else:
            waveforms_dset = makeHDF5Entity(waveforms, group, 
                                            name = "waveforms",
                                            compression = compression,
                                            chunks = chunks,
                                            track_order = track_order)
            waveforms_dset.make_scale("waveforms")
            dset.dims[0].attach_scale(waveforms_dset)
        
    # 5. Create annotations child Group in group
    annotations = getattr(obj, "annotations", None)
    if isinstance(annotations, dict) and len(annotations):
        # use make HDF5Entity to store it in entity_cache
        cached_entity = getCachedEntity(entity_cache, annotations)
        if isinstance(cached_entity, h5py.Group):
            group["annotations"] = cached_entity # hard link
        else:
            annot_group = makeHDF5Entity(annotations, group, "annotations", 
                                        compression=compression, chunks=chunks,
                                        track_order = track_order)
        
    # 6. Create segment child entity (Group) in group
    segment = getattr(obj, "segment", None)
    if isinstance(segment, neo.Segment):
        seg_id = id(segment)
        if seg_id in entity_cache:
            # group["segment"] = h5py.SoftLink(entity_cache[seg_id].name)
            # NOTE: just use a reference (if you use HDFView you will see Obj Ref 
            # is identical to the one used before)
            group["segment"] = entity_cache[seg_id]
        else:
            makeHDF5Entity(segment, group, name="segment", 
                           compression=compression, chunks=chunks,
                           track_order=track_order)
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(pq.Quantity)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    # NOTE: 2021-11-18 14:41:47
    # units & dtype taken care of by makeObjAttrs() via makeDatasetAttrs()
    if obj.size == 0:
        dset = group.create_dataset(name, data = h5py.Empty("f"), track_order=track_order)
    
    if obj.size == 1:
        dset = group.create_dataset(name, data = obj.magnitude, track_order=track_order)
    else:
        dset = group.create_dataset(name, data = obj.magnitude, track_order=track_order, 
                                    compression = compression, chunks = chunks)
        
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

@makeDataset.register(np.ndarray)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    if isinstance(cached_entity, h5py.Dataset):
        group[name] = cached_entity # make a hard link
        return cached_entity
    
    if obj.size == 0:
        dset = group.create_dataset(name, data = h5py.Empty("f"), track_order=track_order)
    
    if obj.dtype.kind in NUMPY_STRING_KINDS:
        data = np.array(obj, dtype=h5py.string_dtype(), order="k")
    else:
        data = obj
        
    if obj.size == 1:
        dset = group.create_dataset(name, data = data, track_order=track_order, compression = compression)
    else:
        dset = group.create_dataset(name, data = data, track_order=track_order, compression = compression, 
                                    chunks = chunks)
    dset.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, dset)
    return dset

def makeHDF5Group(obj, group:h5py.Group, name:typing.Optional[str]=None, compression:typing.Optional[str]="gzip",  chunks:typing.Optional[bool]=None, track_order:typing.Optional[bool] = True, entity_cache:typing.Optional[dict] = None):# -> h5py.Group:
    """Writes python iterable collection and neo containers to a HDF5 Group.
        • iterable collections: tuple, list, dict (and subclasses)
        • neo containers: Block, Segment, Group
        • neo ChannelView
    """
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
              chunks:typing.Optional[bool]=None, track_order:typing.Optional[bool] = True, 
              entity_cache:typing.Optional[dict] = None):# -> h5py.Group:
    cached_entity = getCachedEntity(entity_cache, obj)
    
    if isinstance(cached_entity, h5py.Group):
        group[name] = cached_entity
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
        group[name] = cached_entity
        return cached_entity
        
    grp = group.create_group(name, track_order = track_order)
    grp.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, grp)
    
    if all(isinstance(k, str) for k in obj.keys()):
        for k, element in obj.items():
            cached_entity = getCachedEntity(entity_cache, element)
            if isinstance(cached_entity, (h5py.Group, h5py.Dataset)):
                grp[k] = cached_entity
            
            else:
                element_entity = makeHDF5Entity(element, grp, k, compression = compression, chunks = chunks,
                                track_order = track_order, entity_cache = entity_cache)
    else:
        for k, (key, element) in enumerate(obj.items()):
            key_type = type(key)
            key_value_grp_name = f"{k}_{key_type.__name__}_key"
            key_value_grp = grp.create_group(key_value_grp_name, track_order=track_order)
            
            key_entity = makeHDF5Entity(key, key_value_grp ,"key", compression = compression, chunks = chunks,
                                track_order = track_order, entity_cache = entity_cache)
            
            cached_entity = getCachedEntity(entity_cache, element)
            if isinstance(cached_entity, (h5py.Group, h5py.Dataset)):
                key_value_grp["value"] = cached_entity
            else:
                element_entity = makeHDF5Entity(element, key_value_grp, "value", compression = compression, chunks = chunks,
                                track_order = track_order, entity_cache = entity_cache)
            
            
    return grp

@makeGroup.register(collections.abc.Iterable)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    # tuple, list deque, etc
    cached_entity = getCachedEntity(entity_cache, obj)
    
    if isinstance(cached_entity, h5py.Group):
        group[name] = cached_entity
        return cached_entity
        
    grp = group.create_group(name, track_order = track_order)
    grp.attrs.update(attrs)
    storeEntityInCache(entity_cache, obj, grp)
    
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

@makeGroup.register(ephys.SynapticPathway) # TODO/FIXME 2024-06-18 14:46:55
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    
    if isinstance(cached_entity, h5py.Group):
        group[target_name] = cached_entity
        return cached_entity
    
    measurements = [m for m in obj.measurements]
        
    
@makeGroup.register(neo.core.container.Container)
def _(obj, group, attrs, name, compression, chunks, track_order, entity_cache):
    cached_entity = getCachedEntity(entity_cache, obj)
    
    if isinstance(cached_entity, h5py.Group):
        group[target_name] = cached_entity
        return cached_entity
        
    child_containers = [c for c in obj._child_containers]
    attrs["child_containers"] = child_containers
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
    
    if hasattr(obj, "annotations"):
        annotations = getattr(obj, "annotations", dict())
        
        # print(f"makeGroup: storing annotations")
        annotations_entity = makeHDF5Entity(annotations, grp, "annotations",
                                                    compression = compression, 
                                                    chunks = chunks,
                                                    track_order = track_order,
                                                    entity_cache = entity_cache,
                                                    parent_neo_container_entity = (obj,grp))
    
    return grp
    
def read_hdf5(h5file:h5py.File):
    ret = dict((k, objectFromHDF5Entity(i)) for k,i in h5file.items())
    # print(f"\nread_hdf5: ret = {ret}\n")
    if len(ret)==1:
        return [v for v in ret.values()][0]
    
    return ret
    
