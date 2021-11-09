"""Collection of functions to read/write to HDF5 files
To avoid circular module dependencies, this module should be imported
independently from pictio.

    NOTE: 2021-10-12 09:29:38

    ==============
    Design notes:
    ==============

    An object is the HDF5 File root (/)
    
    Instance attributes & properties (but NEITHER methods, NOR :class: attributes)
    correspond to the following HDF5 structures:
    
    Python types:               HDF5 Structure:          Attribute:
    ============================================================================
    bool and numeric scalars    dataset                 "type": type's name
    sequences (list, tuple)     
    str                         
    
    
    Possible strategies: 
    A) embed a VigraArray as HDF5 in a nix.File accessed via
    neo.NixIO:
    
    1) create a neo.NixIO file -> a physical file in the file system
    2) access the nix_file inside the neo_nixio file object
    3) access the _h5file of the nix_file
    4) create a group inside the _h5file using h5py API:
    
    4.1) this is a HDF5 Group, NOT a nix H5Group!
    
    4.2) we can create it using the strategy in nix i.e., via low-level h5py api
        e.g. h5g.create() a groupid, to enable group creation with order tracked
        and order indexed flags - see h5p api - followed by instatiation of the
        h5py.Group(groupid)
        
    5) use the newly-created group as a fileNameOrGroup parameter to vigra.writeHDF5()
    
    CAUTION: a nix.File cannot be used as context manager (i.e. one cannot
    use the idiom with nix.File(...) as nixfile: ...)
    But the neo.NixIO can be used as context manager:
    with neo.NixIO(...) as neo_nixio_file: ...
        (the underlying HDF5 file object is open in the neo.NixIO c'tor)
    
    see history_snipper_scandata_vigra_export_hdf5.py
    
"""

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




import os, sys, tempfile, traceback
import types, typing, inspect, functools, itertools
import collections, collections.abc
from uuid import uuid4
import json
import h5py
import numpy as np
import nixio as nix 
import vigra
import pandas as pd
import quantities as pq
import neo
from neo.core.dataobject import ArrayDict

from core.prog import safeWrapper
from core import prog
from core.traitcontainers import DataBag
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)

from core.quantities import(arbitrary_unit, 
                            pixel_unit, 
                            channel_unit,
                            space_frequency_unit,
                            angle_frequency_unit,
                            day_in_vitro,
                            week_in_vitro, postnatal_day, postnatal_month,
                            embryonic_day, embryonic_week, embryonic_month,
                            unit_quantity_from_name_or_symbol,)

from core.datatypes import (TypeEnum,UnitTypes, Genotypes, 
                            is_uniform_sequence, is_namedtuple,
                            )

from core.modelfitting import (FitModel, ModelExpression,)
from core.triggerevent import (TriggerEvent, TriggerEventType,)
from core.triggerprotocols import TriggerProtocol
from core.utilities import unique
from imaging.axiscalibration import (AxesCalibration, 
                                     AxisCalibrationData, 
                                     ChannelCalibrationData)

from imaging.indicator import IndicatorCalibration # do not confuse with ChannelCalibrationData
from imaging.scandata import (AnalysisUnit, ScanData,)
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

def generic_data_attrs(data, prefix=""):
    attrs = dict()
    
    if isinstance(prefix, str) and len(prefix.strip()):
        if not prefix.endswith("_"):
            prefix += "_"
        
    else:
        prefix = ""

    if isinstance(data, type): # in case data is already a type
        attrs[f"{prefix}type_name"] = data.__name__
        attrs[f"{prefix}module_name"] = data.__module__
        attrs[f"{prefix}python_class"] = ".".join([data.__module__, data.__name__])
        
        if is_namedtuple(data):
            fields_list = list(f for f in data._fields)
            attrs[f"{prefix}python_class_def"] = f"{data.__name__} = collections.namedtuple({data.__name__}, {list(fields_list)})"
        else:
            
            attrs[f"{prefix}python_class_def"] = prog.class_def(data)
    else:
        attrs[f"{prefix}type_name"] = type(data).__name__
        attrs[f"{prefix}module_name"] = type(data).__module__
        attrs[f"{prefix}python_class"] = ".".join([attrs[f"{prefix}module_name"], attrs[f"{prefix}type_name"]])
        if is_namedtuple(data):
            fields_list = list(f for f in data._fields)
            attrs[f"{prefix}python_class_def"] = f"{type(data).__name__} = collections.namedtuple({type(data).__name__}, {fields_list})"
            init = list()
            init.append(f"{type(data).__name__}(")
            init.append(", ".join(list(n + ' = {}' for n in data._fields)))
            init.append(")")
            attrs[f"{prefix}python_data_init"] = "".join(init)
        else:
            attrs[f"{prefix}python_class_def"] = prog.class_def(data)
            
        
        if inspect.isfunction(data):
            attrs[f"{prefix}func_name"] = data.__name__
            
    
    return attrs
    
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
    attrs = generic_data_attrs(x, attr_prefix)
    if not isinstance(x, str):
        name = f"{type(x).__module__}.{type(x).__name__}_{uuid4().hex}"
        #name = json.dumps(x)
    else:
        name = x
    
    return type(x), name, attrs

def from_dataset(dset:typing.Union[str, h5py.Dataset],
                 group:h5py.Group:typing.Optional[h5py.Group]=None, 
                 order:typing.Optional[str]=None):
    if isinstance(dset, str) and len(dset.strip()):
        if not isinstance(group, h5py.Group):
            raise TypeError(f"When the data set is indicated by its name, 'group' must a h5py.Group; got {type(group).__name__} instead")
        dset = group[dset] # raises exception if dset does not exist in group
        
    elif not isinstance(dset, h5py.Dataset):
        raise TypeError(f"Expecting a str (data set name) or HDF5 data set; got {type(dset).__name__} instead")
    
    data = dset[()]
    data_name = dset.name.split('/')[-1]
    
    if not isinstance(group, h5py.Group): # not really required, is it?!?
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
                            channels = unique(key.split('_')[0] for key in dim.keys() if any(key.endswith(s) for s in ("_name", "_units", "_origin", "_resolution", "_maximum", "_index")))
                            for ch in channels:
                                chcal = dict()
                                if f"{ch}_name" in dim:
                                    chcal["name"] = dim[f"{ch}_name"][()].decode()
                                if f"{ch}_units" in dim:
                                    chcal["units"] = unit_quantity_from_name_or_symbol(dim[f"{ch}_units"][()].decode())
                                if f"{ch}_origin" in dim:
                                    chcal["origin"] = float(dim[f"{ch}_origin"][()])
                                if f"{ch}_resolution" in dim:
                                    chcal["resolution"] = float(dim[f"{ch}_resolution"][()])
                                if f"{ch}_maximum" in dim:
                                    chcal["maximum"] = float(dim[f"{ch}_maximum"][()])
                                if f"{ch}_index" in dim:
                                    chcal["index"] = int(dim[f"{ch}_index"][()])
                                    
                                if ChannelCalibrationData.isCalibration(chcal):
                                    axcal.addChannelCalibration(ChannelCalibrationData(chcal))

                        axcal.calibrateAxis(data.axistags[dim.label])
                        
            if order is None:
                order = vigra.VigraArray.defaultOrder
            elif order not in ("V", "C", "F", "A", None):
                raise IOError(f"Unsupported order {order} for VigraArray")
            
            if order == "F":
                data = data.transpose()
            else:
                data = data.transposeToOrder(order)
            
    elif isinstance(data, bytes):
        data = data.decode()
            
    return data

def make_dataset(x:typing.Any, group:h5py.Group, 
                 name:typing.Optional[str]=None,
                 compression:typing.Optional[str]=None,
                 chunks:typing.Optional[bool]=None):
    x_type, x_name, x_attrs = hdf_entry(x, "")
    
    if not isinstance(name, str) or len(name.strip()) == 0:
        name = x_name
        
    if isinstance(x, (bool, bytes, complex, float, int, str)):
        dset = group.create_dataset(name, data = x)
        dset.attrs.update(x_attrs)
        
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
        x_attrs["axistags"] = data.axistags.toJSON()
        dset.attrs.update(x_attrs)
        
        # For each axis, we attach FOUR HDF5 dimension scales: 
        # name (str), units (str), origin (float), and resolution (float)
        x_tr_axcal = AxesCalibration(data)
        
        calgrp = group.create_group(f"{name}_axes", track_order=True)
        
        #for k, cal, axistag in enumerate(zip(x_tr_axcal, data.axistags)):
        for k, cal in enumerate(x_tr_axcal):
            axcalgrp = calgrp.create_group(f"{cal.key}", track_order=True)
            ds_origin = axcalgrp.create_dataset("origin", data = cal.origin)
            ds_origin.make_scale("origin")
            ds_resolution = axcalgrp.create_dataset("resolution", data = cal.resolution)
            ds_resolution.make_scale("resolution")
            ds_units = axcalgrp.create_dataset("units", data = cal.units.dimensionality.string)
            ds_units.make_scale("units")
            ds_name = axcalgrp.create_dataset("name", data = cal.name)
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
                        ds_chn_origin = channel_group.create_dataset(f"{channel[0]}_origin", data = channel[1].origin)
                        ds_chn_origin.make_scale(f"{channel[0]}_origin")
                        ds_chn_resolution = channel_group.create_dataset(f"{channel[0]}_resolution", data = channel[1].resolution)
                        ds_chn_resolution.make_scale(f"{channel[0]}_resolution")
                        ds_chn_maximum = channel_group.create_dataset(f"{channel[0]}_maximum", data=channel[1].maximum)
                        ds_chn_maximum.make_scale(f"{channel[0]}_maximum")
                        ds_chn_index = channel_group.create_dataset(f"{channel[0]}_index", data = channel[1].index)
                        ds_chn_index.make_scale(f"{channel[0]}_index")
                        ds_chn_units = channel_group.create_dataset(f"{channel[0]}_units", data = channel[1].units.dimensionality.string)
                        ds_chn_units.make_scale(f"{channel[0]}_units")
                        ds_chn_name = channel_group.create_dataset(f"{channel[0]}_name", data = channel[1].name)
                        ds_chn_name.make_scale(f"{channel[0]}_name") # channel name, not axis name!
                        
                        dset.dims[k].attach_scale(ds_chn_name)
                        dset.dims[k].attach_scale(ds_chn_units)
                        dset.dims[k].attach_scale(ds_chn_index)
                        dset.dims[k].attach_scale(ds_chn_origin)
                        dset.dims[k].attach_scale(ds_chn_resolution)
                        dset.dims[k].attach_scale(ds_chn_maximum)
                        
            dset.dims[k].label = f"{cal.key}"
            
    elif isinstance(x, (neo.AnalogSignal, DataSignal)):
        data = np.transpose(x.magnitude) # axis 0 becomes axis 1 and vice-versa!
        x_meta = dict()
        x_meta["description"] = x.description
        x_meta["file_origin"] = x.file_origin
        x_meta.update(x.annotations)
        x_meta.update(x_attrs)
        
        dset = group.create_dataset(f"{name}", data = data)
        dset.attrs.update(x_meta)
        
        calgrp = group.create_group(f"{name}_axes", track_order=True)
        
        for k in range(2):
            axcalgrp = calgrp.create_group(f"axis_{k}", track_order=True)
            
            if k == 0: # axis 0 is now the channels axis
                ds_units = axcalgrp.create_dataset("signal_units", data = x.dimensionality.string)
                ds_units.make_scale("signal_units")
                # (un)fortunately(?), individual channels (i.e. data columns) in
                # neo signals are not named
                data_name = getattr(x, "name", None)
                if not isinstance(data_name, str) or len(data_name.strip()) == 0:
                    data_name = x_name
                ds_name = axcalgrp.create_dataset("signal_name", data = data_name)
                ds_name.make_scale("signal_name")
                
                dset.dims[k].attach_scale(ds_name)
                dset.dims[k].attach_scale(ds_units)

                channels_group = axcalgrp.create_group("channels", track_order=True)
                
                array_annotations = getattr(x, "array_annotations", None)
                
                if isinstance(array_annotations, ArrayDict):
                    channels_group.attrs.update(array_annotations)
                    
                else:
                    array_annotations = dict() # shim for below
                
                for k in x.shape[-1]:
                    if "channel_ids" in array_annotations:
                        channel_id = array_annotations["channel_ids"][k].item()
                    else:
                        channel_id = f"{k}"
                        
                    if "channel_names" in array_annotations:
                        channel_name = array_annotations["channel_names"][k].item()
                    else:
                        channel_name = f"{k}"
                        
                    ds_chn_index = channels_group.create_dataset(f"channel_{k}_index", data=k)
                    ds_chn_index.make_scale(f"channel_{k}_index")
                    
                    ds_chn_id = channels_group.create_dataset(f"channel_{k}_id", data = channel_id)
                    ds_chn_id.make_scale(f"channel_{k}_id")
                    
                    ds_chn_name = channels_group.create_dataset(f"channel_{k}_name", data = channel_name)
                    ds_chn_name.make_scale(f"channel_{k}_name")
                    
                    dset.dims[k].attach_scale(ds_chn_index)
                    dset.dims[k].attach_scale(ds_chn_id)
                    dset.dims[k].attach_scale(ds_chn_name)
                    
                    for key in array_annotations:
                        if key not in ("channel_ids", "channel_names"):
                            ds_chn_key = channels_group.create_dataset(f"channel_{k}_{key}", data = array_annotations[key][k].item())
                            ds_chn_key.make_scale(f"channel_{k}_{key}")
                            dset.dims[k].attach_scale(ds_chn_key)
                    
                dset.dims[k].label = data_name
                    
            else: # axis 1 is now the time (or domain) axis
                ds_origin = axcalgrp.create_dataset("domain_origin", data = x.t_start.magnitude.item())
                ds_origin.make_scale("domain_origin")
                ds_units = axcalgrp.create_dataset("domain_units", data = x.t_units.dimensionality.string)
                ds_units.make_scale("domain_units")
                ds_rate = axcalgrp.create_dataset("sampling_rate", data = x.sampling_rate.magnitude.item())
                ds_rate.make_scale("sampling_rate")
                ds_rate_units = axcalgrp.create_dataset("sampling_rate_units", data = x.sampling_rate.units.dimensionality.string)
                ds_rate_units.make_scale("sampling_rate_units")
                
                dset.dims[k].attach_scale(ds_origin)
                dset.dims[k].attach_scale(ds_units)
                dset.dims[k].attach_scale(ds_rate)
                dset.dims[k].attach_scale(ds_rate_units)
                
                if isinstance(x, DataSignal):
                    dset.dims[k].label = x.domain_name
                else:
                    dset.dims[k].label="Time"
            
        
    elif isinstance(x, pq.Quantity):
        dset = group.create_dataset(name, data=x.magnitude)
        x_attrs.update({"units": x.dimensionality.string})
        dset.attrs.update(x_attrs)
        
    elif isinstance(x, np.ndarray):
        dset = group.create_dataset(name, data = x)
        dset.attrs.update(x_attrs)
        
        

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
            
def readHDF5_VigraArray(fileNameOrGroup:typing.Union[str, h5py.Group], 
                        pathInFile:str, 
                        order:typing.Optional[str]=None):
    '''Read an array from an HDF5 file.
    
    Modified version of vigra.impex.readHDF5() for the new h5py API:
    A DataSet object does NOT have a "value" attribute in h5py v3.4.0
    
    Parameters:
    ===========
    
    'fileNameOrGroup' : str or h5py.Group
        When a str, it contains a filename
        When a hy5py.Group this is a group object referring to an already open 
        HDF5 file, or present in an already open HDF5 file
        
    'pathInFile' : str is the name of the dataset to be read, including 
    intermediate groups (when a HDF5 'path' - like string). If 'fileNameOrGroup'
    is a group object, the path is relative to this group, otherwise it is 
    relative to the file's root group.

    If the dataset has an attribute 'axistags', the returned array
    will have type :class:`~vigra.VigraArray` and will be transposed
    into the given 'order' ('vigra.VigraArray.defaultOrder'
    will be used if no order is given).  Otherwise, the returned
    array is a plain 'numpy.ndarray'. In this case, order='F' will
    return the array transposed into Fortran order.

    Requirements: the 'h5py' module must be installed.
    '''
    #import h5py
    file, group, _ = get_file_group_child(fileNameOrGroup)
        
    try:
        dataset = group[pathInFile]
        if not isinstance(dataset, h5py.Dataset):
            raise IOError("readHDF5(): '%s' is not a dataset" % pathInFile)
        if hasattr(dataset, "value"):
            # NOTE: keep this for older h5py API
            data = dataset.value # <- offending line (cezar.tigaret@gmail.com)
        else:
            # NOTE: 2021-10-17 09:38:13
            # the following returns a numpy array, see:
            # https://docs.h5py.org/en/latest/high/dataset.html#reading-writing-data
            data = dataset[()] 
            
        axistags = dataset.attrs.get('axistags', None)
        if axistags is not None:
            data = data.view(vigra.arraytypes.VigraArray)
            data.axistags = vigra.arraytypes.AxisTags.fromJSON(axistags)
            if order is None:
                order = vigra.arraytypes.VigraArray.defaultOrder
            data = data.transposeToOrder(order)
        else:
            if order == 'F':
                data = data.transpose()
            elif order not in [None, 'C', 'A']:
                raise IOError("readHDF5(): unsupported order '%s'" % order)
    finally:
        # NOTE: 2021-10-17 09:42:50 Original code
        # This only closes 'file' when fileNameOrGroup if a HDF5 File object
        # otherwise does nothing
        if file is not None:
            file.close()
    return data

def readHDF5_str(fileNameOrGroup, pathInFile):
    file, group = get_file_group_child(fileNameOrGroup)
        
    try:
        dataset = group[pathInFile]
        if not isinstance(dataset, h5py.Dataset):
            raise IOError("readHDF5(): '%s' is not a dataset" % pathInFile)
        
        encoding = group.attrs.get("encoding", "utf-8")

        data = dataset[()]
        
        if isinstance(data, bytes):
            data = data.decode(encoding)
            
    finally:
        if file is not None:
            file.close()
            
    return data

def writeHDF5_VigraArray(x, fileNameOrGroup, pathInFile, mode="a", compression=None, chunks=None):
    """Variant of vigra.impex.writeHDF5 returning the created h5py.Dataset object
    Also populates the dataset's dimension scales.
    
    Modified from vira.impex.writeHDF5 (C) U.Koethe
    """
    if isinstance(fileNameOrGroup, h5py.Group):
        file = None
        group = fileNameOrGroup
    else:
        file = h5py.File(fileNameOrGroup, mode=mode)
        group = file['/']
        
    #dataset = None
        
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
        dataset = group.get(levels[-1], default=None)
        if dataset is not None:
            if isinstance(dataset, h5py.Dataset):
                del group[levels[-1]]
            else:
                raise IOError("writeHDF5(): cannot replace '%s' because it is not a dataset" % pathInFile)
        try:
            x = x.transposeToNumpyOrder()
        except:
            pass
        dataset = group.create_dataset(levels[-1], data=x, compression=compression, chunks=chunks)
        if hasattr(x, 'axistags'):
            dataset.attrs['axistags'] = x.axistags.toJSON()
            axcalgroup = group.create_group("axis")
            for k, axt in enumerate(x.axistags):
                dataset.dims[k].label = axt.key
            
            
    finally:
        if file is not None:
            file.close()
            
    return dataset


    

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
    
    
    
