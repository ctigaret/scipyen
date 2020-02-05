# NOTE: 2016-03-10 22:41:15
# modified after ipython example internal_ipkernel.py -- 
# see also internal_ipkernel_mod.py in my IPython examples directory

# TODO: 2016-03-10 22:42:45 make this IPyhton version agnostic
# TODO: and PyQt4/PyQt5/PySide agnostic -- if necessary, and where possible

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys

#from IPython.lib.kernel import connect_qtconsole
from IPython.kernel.zmq.kernelapp import IPKernelApp

from subprocess import Popen, PIPE
from IPython.kernel import *

#import rlcompleter, readline

#from IPython.utils.ipstruct import Struct

#-----------------------------------------------------------------------------
# Functions and classes
#-----------------------------------------------------------------------------

# TODO: 2016-03-10 22:44:55 make it IPython version agnostic
def connect_qt_console(connection_file=None, argv=None, profile=None):
    """Re-write of stock (IPython 3.x) connect_qtconsole to avoid prompting upon
    console exit
    
    Connect a qtconsole to the current kernel.
    
    This is useful for connecting a second qtconsole to a kernel, or to a
    local notebook.
    
    Parameters
    ----------
    connection_file : str [optional]
        The connection file to be used. Can be given by absolute path, or
        IPython will search in the security directory of a given profile.
        If run from IPython, 
        
        If unspecified, the connection file for the currently running
        IPython Kernel will be used, which is only allowed from inside a kernel.
    argv : list [optional]
        Any extra args to be passed to the console.
    profile : str [optional]
        The name of the profile to use when searching for the connection file,
        if different from the current IPython session or 'default'.
    
    
    Returns
    -------
    :class:`subprocess.Popen` instance running the qtconsole frontend
    """
    argv = [] if argv is None else argv
    
    if connection_file is None:
        # get connection file from current kernel
        cf = get_connection_file()
    else:
        cf = find_connection_file(connection_file, profile=profile)
        
    #print(cf)
    
    # TODO: 2016-03-10 22:42:18 make this IPython version agnostic
    cmd = ';'.join([
        "from IPython.qt.console import qtconsoleapp",
        "qtconsoleapp.main()"
    ])
    
    seq = [sys.executable, '-c', cmd, '--no-confirm-exit', '--existing', cf]
    
    #print(seq)
    
    return Popen(seq + argv,
        stdout=PIPE, stderr=PIPE, close_fds=(sys.platform != 'win32'),
    )


def mpl_kernel(gui):
    """Launch and return an IPython kernel with matplotlib support for the desired gui
    """
    kernel = IPKernelApp.instance()
    kernel.initialize(['python', '--matplotlib=%s' % gui,
                       #'--log-level=10'
                       ])
    return kernel


class InternalIPKernel(object):

    def init_ipkernel(self, backend):
        '''
         Start IPython kernel with GUI event loop and mpl support
        '''
        
        # 2016-03-11 15:41:24 ipkernel.shell returns the same instance of
        # IPython.kernel.zmq.zmqshell.ZMQInteractiveShell as calling
        # get_ipython() from the qt console
        self.ipkernel = mpl_kernel(backend)
        #self.ipkernel.shell.set_readline_completer()
        
        # TODO: define a cutom magic for this message
        self.ipkernel.shell.banner2 = u'\n*** NOTE: ***\n\nUser variables created here will be accessible both from the Qt console and the PyCaT window GUI.\n' +\
                                      u'\n\nThe PyCaT main window GUI object is accessible from the console as `mainWindow` or `pw` variables.' +\
                                      u'\n\nExcept for user variables, if any of `pw`, `mainWindow`, or loaded modules are deleted from the console workspace by calling del(...), they can be restored using the `Console/Restore Namespace` menu item.'
        
        # To create and track active qt console
        self.console = None
        
        # This application will also act on the shell user namespace
        self.workspace = self.ipkernel.shell.user_ns
        
        #self.workspace = dict() # 2016-03-11 12:46:01 NOT HERE!
        
        # NOTE:  2016-03-10 23:01:22 
        # This is where data variables should be stored and manipulated, 
        # from both PyCaT window _AND_ the Qt console
        #self.namespace['workspace'] = self.workspace # 2016-03-11 12:46:11 NOT HERE!

        # Example: a variable that will be seen by the user in the shell, and
        # that the GUI modifies (the 'Counter++' button increments it):
        #self.namespace['app_counter'] = 0
        #self.namespace['ipkernel'] = self.ipkernel  # dbg

    # TODO: 2016-03-11 16:30:13 remove this function
    #def print_workspace(self, evt=None):
        #print("\n*** Variables in User namespace ***")
        #for k, v in self.workspace.items():
            #if not k.startswith('_'):
                #print('%s -> %r' % (k, v))
        #sys.stdout.flush()

    def init_qt_console(self, evt=None):
        """start a new qtconsole connected to our kernel"""
        #self.console = connect_qt_console(self.ipkernel.connection_file, profile=self.ipkernel.profile)
        if self.console is None:
            self.console = connect_qt_console(self.ipkernel.connection_file, profile=self.ipkernel.profile)
        elif isinstance(self.console, Popen):
            self.console.kill()
            self.console = connect_qt_console(self.ipkernel.connection_file, profile=self.ipkernel.profile)
            

    #def count(self, evt=None):
        #self.namespace['app_counter'] += 1
        
    def closeConsole(self, evt=None):
        if self.console is not None:
            self.console.kill()
            self.console=None

    #def cleanup_consoles(self, evt=None):
        #for c in self.consoles:
            #c.kill()
