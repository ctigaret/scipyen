# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Module with housekeeping utilities for an external IPython kernel.

To be run/imported inside a REMOTE ipython kernel (see extipyutils_client).

This module includes code for communication between the external (or REMOTE)
IPython kernel and Scipyen's internal (embedded) IPython kernel, as well as code
managing custom magics, see below) which are not needed for regular user access.

NOTE: 2022-02-06 22:26:01
Some initialization has already occurred, driven by extipyutils_client.py (and
from there, via extipy_init.py) BEFORE this module.

In fact, this module is imported as hostutils via executing the init_commands in 
extipyutils_client.

To expose Scipyen API inside the REMOTE IPython kernel workspace, either insert
relevant import statements in the init_commands list inside extipyutils_client
module. NOTE: extipy_init module cannot be used for importing Scipyen API in 
the REMOTE kernel namespace, as it is oblivious of Scipyen's module paths.

NOTE: NeuronMagics are useful to start NEURON manually from an external IPython
kernel, optionally with ('nrngui') or without NEURON GUI ('nrnpy')
"""

import os, sys

# NOTE: 2023-04-03 19:27:55
# don't need this anymore, do we?
#if sys.platform == 'win32':
    ## Try conda first
    #scipyenvdir = os.getenv("CONDA_PREFIX")

    #if scipyenvdir is None:
        #scipyenvdir = os.getenv("VIRTUAL_ENV")
        #if scipyenvdir is None:
            #sys.exit("You are NOT inside a virtual Python environment")
        #else:

            #scipyenvbin     = os.path.join(scipyenvdir,"bin")
            #scipyenvlib     = os.path.join(scipyenvdir,"lib")
            #scipyenvlib64   = os.path.join(scipyenvdir,"lib64")


        #if os.path.isdir(scipyenvbin):
            #os.add_dll_directory(scipyenvbin)
        #else:
            #print(f"{scipyenvbin} directory not found; functionality will be limited")
        #if os.path.isdir(scipyenvlib):
            #os.add_dll_directory(scipyenvlib)
        #else:
            #print(f"{scipyenvlib} directory not found; functionality will be limited")
        #if os.path.isdir(scipyenvlib64):
            #os.add_dll_directory(scipyenvlib64)
        #else:
            #print(f"{scipyenvlib64} directory not found; functionality will be limited")

        #vigranumpyextdir = os.path.join(scipyenvdir, "lib", "site-packages", "vigra")

        #if os.path.isdir(vigranumpyextdir):
            #sys.path.append(vigranumpyextdir)
            #os.add_dll_directory(vigranumpyextdir)


        #del scipyenvbin, scipyenvlib, scipyenvlib64, vigranumpyextdir


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
        """Starts NEURON modelling with gui, in this kernel
        """
        get_ipython().run_line_magic("run", self.nrngui_magic_cmd)
        
    @line_magic
    @needs_local_scope
    def nrnpy(self, line, local_ns):
        """Starts NEURON modelling (without gui), in this kernel
        """
        get_ipython().run_line_magic("run", self.nrnpy_magic_cmd)
        
#get_ipython().register_magics(NeuronMagics)
shell.register_magics(NeuronMagics)


        
