"""
snippet of commands as example for exporting scandata bits to hdf5
    to extend for exporting the entire object;
    need to make a group with instructions to reconstruct the
    scandata from the subgroups inside the hdf5 file (or better, user block?)
    
    factor out for general import/export of data types encountered in
    scipyen from/to HDF5: poss. strategies:
    1) either add relevant io functions to every user-defined class
    (PITA)
    2) create generic hdf5 io based on something like inspect.getmembers(obj)
    
    (but careful: don;t make it too general)
    
    
    Signed-off-by: Cezar M. Tigaret <cezar.tigaret@gmail.com>
"""
import tempfile
import h5py
import neo
import nixio as nix 

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


# writing strings:
with h5py.File("test.hdf5", "a") as f:
    f["test_string"] = b
    
# nested in a group
with h5py.File("test.hdf5", "a") as f:
    f["/string_group/test_string"] = b





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
for k, channel_name in enumerate(base_000.scansChannelNames):
    vigra.impex.writeHDF5(base_000.scans[k], f, f"/scans/{channel_name}")
f.close()

# alternatively <- preferred way:
with h5y.File("scans.h5", "a") as f:
    for k, channel_name in enumerate(base_000.scansChannelNames):
        vigra.impex.writeHDF5(base_000.scans[k], f, f"/scans/{channel_name}")
    

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

neo_nixio_file.nix_file._root.open_group(name)

neo_nixio_file.close() # => saves BOTH the ephysdata block AND VigraArray inside
                       # the same nix hdf5 file
                       
# NOTE: the neo_nixio_file does NOT need to save any ephysdata





