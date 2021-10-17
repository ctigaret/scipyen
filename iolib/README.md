***
# STRATEGY
***

`h5py` supports numeric datasets almost transparently (for strings, see 
`https://docs.h5py.org/en/latest/strings.html` and below)

## Keep to the `first principles` laid out in HDF5 specification (h5py)
### What we want is just to store data persistently and INSENSITIVE to possible API changes in 3rd party libraries (such as neo :-(  )

+ Write "codecs" to convert between basic python types to HDF and back
+ For collections, focus on:
    + lists, tuple, deque, dict <-> HDF5 groups
        + use attributes to identify Python class
        
    + entirely numeric sequences (including numpy arrays but EXCLUDING VigraArray
    and Quantities (pq module)) -> as numeric datasets
    + investigate numpy array attributes 
    + conversions to/from numpy dtypes
        
+ User-defined classes:
    + HDF5 Group
        + attributes:
            + "class" = qualified class name (i.e., package.module.class)
    + children (HDF5 Groups):
        + class_attributes: HDF5 Group
            + each a HDF5 Dataset with optional attributes
        + instance_attributes: HDF5 Group
            + each a HDF5 Dataset with optional attributes
    
**NOTE** might require changes in the data class designs (ScanData, AnalysisUnit,
PlanarGraphics) but must have sufficiently flexible heuristic to read/write neo 
data types and our own (e.g. DataSignal, TriggerEvent, etc)

## PyTables: the underlying engine for pandas <-> HDF5
Too complex and yet limited:
+ geared towards pandas API (one can perform many of the pandas operations on
pytables "files")
+ like nix (see below) relies on existing physical files which precludes easy
ways to directly 'inject' data in HDF5 groups



## `neo.NixIO` write operations - relies on `nix` (`nixpy`): 
Too complex and yet limited:
+ `nix` API unnecessarily convoluted to adapt (a limited set of) data structures to the underlying HDF5 data sets
+ no (easy) support for:
    + multidimensional arrays
    + nested Python containers / collections (e.g., dict elements of an iterable,
iterable values in a dict, and so on...)
+ requires direct access to a physical file (limitation of `nix`):
    + the underlying HDF5 h5py.File object, although accessible, is a private attribute of `nix.File`
    + this encumbers the opportunity for using a h5py.File as a h5py.Group (which vigra.impex does successfully)
+ writing a VigraArray (with its own bells and whistles) possible, e.g. by using a tempfile, **BUT** no easy way to read it back using `neo.NixIO`/`nix` API


`write` => inherited from `neo.io.baseio.BaseIO`:  

+ works only if `neo.Block` is among the classes that the IO object can read/write
    + which is the case with `neo.NixIO`
+ calls:
    + `write_all_blocks` if argument is a `collections.abc.Sequence` (of `neo.Block`)
        + iterates through all `neo.Block` and calls `write_block` for each
    + `write_block` if argument is a `neo.Block`


`write_block(block:neo.Block, use_obj_names:bool=False` => converts the `block:neo.Block` to a `nix.Block`:  

+ ensures a `nix_name` exists, as a block annotation
+ check if `nix_name` maps to a `nix.Block` --> if it does, then remove the `nix.Block`
+ create a `nix.Block`:
    1. `nixblock = nix_file.create_block(nix_name, "neo.block"`
        + *signature*: `nix.File.create_block(name:str="", type:str="", compression:nix.compression.Compression(Enum)=Compression.Auto, copy_from=None,keep_copy_id=True)`
    2. populate `nixblock.metadata` (a `nix.Section`): 
        + create a section then assign it to the `metadata` attribute of the `nix.Block` (`@property metadata.setter`):  
        `nixblock.metadata = nix_file.create_section(nix_name, "neo.block.metadata")`
            + *signature*: `nix.File.create_section(name:str, type_:str="undefined, oid=None)`
        + create `neo_name` property of `nixblock.metadata` with the value of `block.name` attribute :
            calls `nixblock.metadata.__setitem__(key, data)` --> this effectively calls `Section.create_property(self, key, data)` with data wrapped in a `list`;  
            **NOTE** This is **not** a Python property but a `nix.Property` object, that maps to  a `nix.h5dataset`; properties are collected in a `nix.h5group`. 

            `nixblock.metadata["neo_name"] = block.name` 

    3. populate the `nixblock.definition`:   
    
        `nixblock.definition = block.description`
        
    4. use convenient API to set creation time and update time:
    
        `nixblock.force_created_at(int(block.rec_datetime.strftime("%s")` 
        
        `fdt, annotype = dt_to_nix(block.file_datetime)`
        
        `fdtprop = metadata.create_property("file_datetime", fdt)`
        
        `fdtprop.definition = annotype`
        
    5. Write block's annotations: 
    
        `if block.annotations:`
        
        `    for k, v in block.annotations.items():`
        
        `        self._write_property(metadata, k, v)`

    6. Descend and write each of the block's segments:  
    
        `for seg in block.segments:`
        
        `   self._write_segment(seg, nixblock`)
        
    7. Finally, do the same with the block's groups (if any):
    
        `for group in block.groups:`
        
        `   self._write_group(group, nixblock)`
        
+ write functions for a block's children:
    1. `_write_property`
    2. `_write_segment`
    3. `_write_group`

# Snippets of code for reading/writing to HDF5 files and "glue" with nixpy (nixio)

## Possible strategies:

1. either add relevant io functions to every user-defined class (PITA)
2. create generic hdf5 io based on something like inspect.getmembers(obj)
(but careful: don;t make it too general)


See STRATEGY above
~~~
:::python hl_lines="38"
import tempfile
import h5py
import neo
import nixio as nix 

newAxisInfo = vigra.AxisInfo(key="t1", typeFlags=vigra.AxisType.Time, resolution=1, description=defaultAxisTypeName(axisTypeFlags["t"]))

newAxisCal = AxisCalibration(newAxisInfo, units=pq.s,origin=0, resolution=1, axisname=defaultAxisTypeName(newAxisInfo))

ch1 = imgp.concatenateImages(*[imgp.insertAxis(img, newAxisInfo, 2) for img in (base_000_Cycle00001_CurrentSettings_Ch1_000001, base_000_Cycle00002_CurrentSettings_Ch1_000001, base_000_Cycle00003_CurrentSettings_Ch1_000001)], axis=newAxisInfo)

ephysdata = neoutils.concatenate_blocks(base_0000, base_0001, base_0002)


# Writing strings:

with h5py.File("test.hdf5", "a") as f:
    f["test_string"] = b

# Writing strings nested in a group
with h5py.File("test.hdf5", "a") as f:
    f["/string_group/test_string"] = b


# reading strings:
a = test_hdf5["/string_group/test_string"][()].decode("utf-8")


# writing vigra arrays
f = h5py.File("scans_000.h5", "a")
scans_list = f.create_group("scans")
subgroup
scans_list
dir(base_000)
base_000.scansChannels
base_000.scansChannelNames
    
# NOTE: vigra.impex writes directly into a HDF5 file (which is also a HDF5 group
# therefore it can be included in a "real" HDF5 file )
# when first parameter to writeHDF5 is a HDF5 Group, the HDF5 file to which it
# belogns (and was opened beforehand) is left OPEN!
for k, channel_name in enumerate(base_000.scansChannelNames):
    vigra.impex.writeHDF5(base_000.scans[k], f, f"/scans/{channel_name}")
f.close()

# alternatively <- preferred way:
with h5y.File("scans.h5", "a") as f:
    for k, channel_name in enumerate(base_000.scansChannelNames):
        vigra.impex.writeHDF5(base_000.scans[k], f, f"/scans/{channel_name}")
        
        
# reading vigra arrays -> there is a problem that vigra.impex.readHDF5 expects a 
# 'value' attribute to HDF5 datasets - which raises AtributeError with h5py 3.4.0
#

# writing neo data: <- caveats
with h5y.File("ephys_data.h5", "a") as f:
    with tempfile.TemporaryFile() as tmpfile:
        with neo.NixIO(tempfile) as nixfile:
            pass
        
# writing pandas data:
# Pandas uses Pytables (tables) which is a Python interface to HDF5 distinct
# from h5py; for this reason, vigra HDF5 IO API cannot be used with pytables/pandas
# and vice-versa
# NOTE: To use pytabels with pandas you must build PyTables if using a more recent
# Python version built from sources - the stock (PyPi) pytables (tables 3.6.1)
# crashes the built Python interpreter
df = pd.DataFrame(np.random.randn(8, 3))
store = pd.HDFStore("dataframetest.h5")
store["df"] = df
store.close()

store = pd.HDFStore("dataframetest_tableformat.h5")
store.put("df", df, format="table")

store.close()

#######
## 2021-10-14 18:28:08
neo_nixio_file = neo.NixIO("test_neo_nixio_file.nix")
nix_file = neo_nixio_file.nix_file
nix_file._h5file # this is a HDF5 file; can one add vigra writeHDF5 to it?


###########
## 2021-10-15 22:09:47 
# combine a neo block and a VigraArray in a HDF5 file through nix (nixpy)
# 1. writing:
newAxisInfo = vigra.AxisInfo(key="t1", typeFlags=vigra.AxisType.Time, 
                                                       resolution=1, 
                                                       description=defaultAxisTypeName(axisTypeFlags["t"]))
newAxisCal = AxisCalibration(newAxisInfo,
                                                       units=pq.s,
                                                       origin=0,
                                                       resolution=1,
                                                       axisname=defaultAxisTypeName(newAxisInfo))
ch1 = imgp.concatenateImages(*[imgp.insertAxis(img, newAxisInfo, 2) for img in (base_000_Cycle00001_CurrentSettings_Ch1_000001, base_000_Cycle00002_CurrentSettings_Ch1_000001, base_000_Cycle00003_CurrentSettings_Ch1_000001)], axis=newAxisInfo)

ephysdata = neoutils.concatenate_blocks(base_0000, base_0001, base_0002)

neo_nixio_file = neo.NixIO("data_test_ephys_vigra.h5")
neo_nixio_file.write_block(ephysdata)



h5file = neo_nixio_file.nix_file._h5file

name = f"{ch1.__class__.__name__}.{uuid.uuid4().hex}"

gcpl=h5py.h5p.create(h5py.h5p.GROUP_CREATE)

gcpl.set_link_creation_order(h5py.h5p.CRT_ORDER_TRACKED | h5py.h5p.CRT_ORDER_INDEXED)

gid = h5py.h5g.create(h5file.id, name.encode("utf-8"), gcpl=gcpl)


vigra_group = h5py.Group(gid)

vigra.writeHDF5(ch1, vigra_group, "Ch1")

neo_nixio_file.nix_file._root.open_group(name) # this writes the ch1 group to the nix_file

neo_nixio_file.close() # => saves BOTH the ephysdata block AND VigraArray inside
                       # the same nix hdf5 file
                       
# NOTE: the neo_nixio_file does NOT need to contain/save any ephysdata

# 2. reading back:
# the neo.NixIO api disregards the vigra_group
# this can be read with h5io.readHDF5Vigra (because it conform to the more 
# recent h5py Dataset API)

~~~

