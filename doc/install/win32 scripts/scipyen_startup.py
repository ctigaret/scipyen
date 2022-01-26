import os, sys
# NOTE: copy this to scipyen sdk directory
# in scipyact.bat set PYTHONSTARTUP to the fuilly qualified path to this module

__module_path__ = os.path.abspath(os.path.dirname(__file__))
if sys.platform == "win32":
    scipyenvdir = os.getenv("VIRTUAL_ENV")
    if scipyenvdir is None:
        sys.exit("You are NOT inside a virtual Python environment")

    scipyen_sdk = __module_path__
    #scipyen_sdk = r"c:\scipyen_sdk"

    #print(f"scipyen_sdk: {scipyen_sdk}")

    scipyenvbin     = os.path.join(scipyen_sdk,"bin")
    scipyenvlib     = os.path.join(scipyen_sdk,"lib")
    scipyenvlib64   = os.path.join(scipyen_sdk,"lib64")

    if os.path.isdir(scipyenvbin):
        os.add_dll_directory(scipyenvbin)
    else:
        print(f"{scipyenvbin} directory not found; functionality will be limited")
    if os.path.isdir(scipyenvlib):
        os.add_dll_directory(scipyenvlib)
    else:
        print(f"{scipyenvlib} directory not found; functionality will be limited")
    if os.path.isdir(scipyenvlib64):
        os.add_dll_directory(scipyenvlib64)
    else:
        print(f"{scipyenvlib64} directory not found; functionality will be limited")

    del scipyenvbin, scipyenvlib, scipyenvlib64
