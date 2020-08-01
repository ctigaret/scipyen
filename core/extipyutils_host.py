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

from core.utilities import summarize_object_properties


__module_path__ = os.path.abspath(os.path.dirname(__file__))

__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

nrn_ipython_initialization_file = os.path.join(os.path.dirname(__module_path__),"neuron_python", "nrn_ipython.py")
nrngui_magic_cmd = "".join(["-i -n ", nrn_ipython_initialization_file, " 'gui'"])
nrnpy_magic_cmd = "".join(["-i -n ", nrn_ipython_initialization_file])


class contextExecutor(ContextDecorator):
    # TODO - what are you trying to resolve?
    
    #def __init__(self, f, *args, **kwargs):
        #self.func = f
        #self.args = args
        #self.kw = kwargs
    
    def __enter__(self):
        #print('Starting')
        
        return self

    def __exit__(self, *exc):
        #print('Finishing')
        return False
    
@magics_class
class NeuronMagics(Magics):
    @line_magic
    @needs_local_scope
    def nrngui(self, line, local_ns):
        """Starts NEURON modelling with gui
        """
        get_ipython().run_line_magic("run", nrngui_magic_cmd)
        
    @line_magic
    @needs_local_scope
    def nrnpy(self, line, local_ns):
        get_ipython().run_line_magic("run", nrnpy_magic_cmd)
        
get_ipython().register_magics(NeuronMagics)
        
