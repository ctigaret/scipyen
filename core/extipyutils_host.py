# -*- coding: utf-8 -*-
"""Module with utilities for an external IPython kernel.
To be imported in the remote kernel namespace - facilitates code execution by 
Scipyen app and its internal console -- the "client" -- inside the remote kernel
-- the "host". the "host" is normally launched and interacted with by Scipyen's
External IPython Console
"""

from contextlib import (contextmanager,
                        ContextDecorator,)

from core.utilities import summarize_object_properties


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
    
