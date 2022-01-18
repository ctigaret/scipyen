# -*- coding: utf-8 -*-
"""Module with utilities for an external IPython kernel.
To be imported in the remote kernel namespace - facilitates code execution by 
Scipyen app and its internal console -- the "client" -- inside the remote kernel
-- the "host". the "host" is normally launched and interacted with by Scipyen's
External IPython Console
"""

import os, sys

if sys.platform == 'win32':
    scipyenvdir = os.getenv("VIRTUAL_ENV")
    if scipyenvdir is None:
        sys.exit("You are NOT inside a virtual Python environment")

    scipyenvbin     = os.path.join(scipyenvdir,"bin")
    scipyenvlib     = os.path.join(scipyenvdir,"lib")
    scipyenvlib64   = os.path.join(scipyenvdir,"lib64")


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

    vigranumpyextdir = os.path.join(scipyenvdir, "lib", "site-packages", "vigra")

    if os.path.isdir(vigranumpyextdir):
        sys.path.append(vigranumpyextdir)
        os.add_dll_directory(vigranumpyextdir)


    del scipyenvbin, scipyenvlib, scipyenvlib64, vigranumpyextdir


from contextlib import (contextmanager,
                        ContextDecorator,)

from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic,
                                needs_local_scope)

from ipykernel import (get_connection_file, get_connection_info, 
                       connect_qtconsole)

from core.utilities import summarize_object_properties
from core.prog import ContextExecutor


__module_path__ = os.path.abspath(os.path.dirname(__file__))

__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

nrn_ipython_initialization_file = os.path.join(os.path.dirname(__module_path__),"neuron_python", "nrn_ipython.py")

shell = get_ipython()
shell.run_cell("from ipykernel import (get_connection_file, get_connection_info, connect_qtconsole)")
#shell.run_cell(os.path.join())

@magics_class
class NeuronMagics(Magics):
    nrngui_magic_cmd = "".join(["-i -n ", nrn_ipython_initialization_file, " 'gui'"])
    nrnpy_magic_cmd = "".join(["-i -n ", nrn_ipython_initialization_file])
    
    @line_magic
    @needs_local_scope
    def nrngui(self, line, local_ns):
        """Starts NEURON modelling with gui
        """
        get_ipython().run_line_magic("run", self.nrngui_magic_cmd)
        
    @line_magic
    @needs_local_scope
    def nrnpy(self, line, local_ns):
        get_ipython().run_line_magic("run", self.nrnpy_magic_cmd)
        
#get_ipython().register_magics(NeuronMagics)
shell.register_magics(NeuronMagics)


        
