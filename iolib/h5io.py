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
        
    5) use the newly-created group as a filenameOrGroup parameter to vigra.writeHDF5()
    
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




import os, sys, tempfile
import numpy as np
import h5py
import nixio as nix 
import vigra
import pandas as pd
import quantities as pq
import neo

from core.prog import safeWrapper
from core.traitcontainers import DataBag
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datatypes import (TypeEnum,UnitTypes, Genotypes, arbitrary_unit, pixel_unit, 
                            channel_unit,
                            space_frequency_unit,
                            angle_frequency_unit,
                            custom_unit_symbols,
                            unit_quantity_from_name_or_symbol,
                            day_in_vitro,
                            week_in_vitro, postnatal_day, postnatal_month,
                            embryonic_day, embryonic_week, embryonic_month,
                            )
from core.modelfitting import (FitModel, ModelExpression,)
from core.triggerevent import (TriggerEvent, TriggerEventType,)
from core.triggerprotocols import TriggerProtocol
from imaging.axiscalibration import AxisCalibration
from imaging.indicator import IndicatorCalibration
from imaging.scandata import (AnalysisUnit, ScanData,)
from gui.pictgui import (Arc, ArcMove, CrosshairCursor, Cubic, Ellipse, 
                         HorizontalCursor, Line, Move, Quad, Path, 
                         PlanarGraphics, Rect, Text, VerticalCursor,)


def readHDF5_VigraArray(filenameOrGroup, pathInFile, order=None):
    '''Read an array from an HDF5 file.
    
    Modified version of vigra.impex.readHDF5() for the new h5py API:
    A DataSet object does NOT have a "value" attribute in h5py v3.4.0
    
    'filenameOrGroup' can contain a filename or a group object
    referring to an already open HDF5 file. 'pathInFile' is the name
    of the dataset to be read, including intermediate groups. If the
    first argument is a group object, the path is relative to this
    group, otherwise it is relative to the file's root group.

    If the dataset has an attribute 'axistags', the returned array
    will have type :class:`~vigra.VigraArray` and will be transposed
    into the given 'order' ('vigra.VigraArray.defaultOrder'
    will be used if no order is given).  Otherwise, the returned
    array is a plain 'numpy.ndarray'. In this case, order='F' will
    return the array transposed into Fortran order.

    Requirements: the 'h5py' module must be installed.
    '''
    #import h5py
    if isinstance(filenameOrGroup, h5py.Group):
        file = None
        group = filenameOrGroup
    else:
        file = h5py.File(filenameOrGroup, 'r')
        group = file['/']
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
            data = data.view(arraytypes.VigraArray)
            data.axistags = arraytypes.AxisTags.fromJSON(axistags)
            if order is None:
                order = arraytypes.VigraArray.defaultOrder
            data = data.transposeToOrder(order)
        else:
            if order == 'F':
                data = data.transpose()
            elif order not in [None, 'C', 'A']:
                raise IOError("readHDF5(): unsupported order '%s'" % order)
    finally:
        # NOTE: 2021-10-17 09:42:50 Original code
        # This only closes 'file' when filenameOrGroup if a HDF5 File object
        # otherwise does nothing
        if file is not None:
            file.close()
    return data

def readHDF5_str(filenameOrGroup, pathInFile):
    if isinstance(filenameOrGroup, h5py.Group):
        file = None
        group = filenameOrGroup
    else:
        file = h5py.File(filenameOrGroup, 'r')
        group = file['/']
        
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

def writeHDF5_NeoBlock(data, filenameOrGroup, pathInFile, use_temp_file=True):
    if not isinstance(data, neo.Block):
        raise TypeError(f"Expecting a neo.Block; got {type(data).__name__} instead")
    
    if not isinstance(data.name, str) or len(data.name.strip()) == 0:
        data_name = ".".join([data.__class__.__module__, data.__class__.__name__])
        
    else:
        data_name = data.name
    
    if isinstance(filenameOrGroup, h5py.Group):
        file = None
        group = filenameOrGroup
    else:
        file = h5py.File(filenameOrGroup, 'a')
        group = file['/']
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
        #dataset = group.get(levels[-1], default=None)
        #if dataset is not None:
            #if isinstance(dataset, h5py.Dataset):
                #del group[levels[-1]]
            #else:
                #raise IOError("writeHDF5(): cannot replace '%s' because it is not a dataset" % pathInFile)
        
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

    
