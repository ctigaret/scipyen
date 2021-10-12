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
ephysdata = neoutils.concatenate_blocks(base_0000, base_0001, base_0002)
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

