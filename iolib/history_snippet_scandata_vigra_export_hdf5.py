f = h5py.File("scans_000.h5", "a")
scans_list = f.create_group("scans")
subgroup
scans_list
dir(base_000)
base_000.scansChannels
base_000.scansChannelNames
for k, channel_name in base_000.scansChannelNames:
    vigra.impex.writeHDF5(base_000.scans[k], f, f"/scans/{channel_name}")
for k, channel_name in enumerate(base_000.scansChannelNames):
    vigra.impex.writeHDF5(base_000.scans[k], f, f"/scans/{channel_name}")
f
f.close()

