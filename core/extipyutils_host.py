# -*- coding: utf-8 -*-
"""Module with utilities for an external IPython kernel.
To be imported in the remote kernel namespace - facilitates code execution by 
Scipyen app and its internal console -- the "client" -- inside the remote kernel
-- the "host". the "host" is normally launched and interacted with by Scipyen's
External IPython Console
"""

import os

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


        
