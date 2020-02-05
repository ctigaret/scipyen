# -*- coding: utf-8 -*-
"""Custom magics for the IPython QtConsole
DEPRECATED
"""

from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic,
                                needs_local_scope)

@magics_class
class PictMagics(Magics):
    @line_magic
    @needs_local_scope
    def exit(self, line):
        """%exit line magic
        """
        pictwindow.slot_pictQuit()
        return line
    
def load_ipython_extension(ipython):
    """
    Any module file that define a function named `load_ipython_extension`
    can be loaded via `%load_ext module.path` or be configured to be
    autoloaded by IPython at startup time.
    """
    # You can register the class itself without instantiating it.  IPython will
    # call the default constructor on it.
    
    ipython.register_magics(PictMagics)
    
