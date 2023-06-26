"""Used for importing modules from site-package.
Unless Scipyen is among those, import statements for Scipyen's modules won't
work here.
"""
has_hdf5 = False

try:
    import h5py
    h5py.enable_ipython_completer()
    has_hdf5 = True
except ImportError as e:
    pass

