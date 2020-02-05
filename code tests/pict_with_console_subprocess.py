#!/usr/bin/env python
# -*- coding: utf-8 -*-

## ###! /usr/bin/python

#
# NOTE: 2016-03-10 22:38:36 This uses IPython 3.x API;
#
# NOTE: NOT YET READY FOR IPYTHON 4.X API
#

# NOTE: 2016-03-12 22:13:00 
#
# OK, so we want to operate on data types, mainly via the GUI (all children of the Pict main window)
# but we also want to have access to this data via a console, bidirectinally:
#
# 1) any modifications brought to data through the GUI are seen when data is 
#    accessesed via the console
#
# 2) any modification brought to data via the console are seen by the GUI code 
#    in Pict main window and its children
#
# 3) Ideally we would AVOID / FORBID modification of non-data variables (e.g. Qt widgets, 
#    module functions, etc.) but ALLOW access to their values from the console -- 
#
#    -- ideally there should be only a subset of "public" API accessible from the console
#
# Points (1) - (3) are hard to simultaneously satisfy in python without serious customization 
# (e.g., we'd like to have read/write access to data, access to almost all the modules loaded in Pict, but no access
# to at least some of the widgets -- or their member variables -- in the Pict window and its children
# even though the usefuleness of such access may seem to overcome the risk of crashing the application).
#
#
# Possible strategies for points (1) and (2):
#
# a) maintain a global dictionary (e.g. "workspace") where data is stored (the leys are the variable names)
#
#    accessing the data from the console soon becomes cumbersome because of the dict access syntax in python
#
#     -- alteratively try workspace being a Struct from IPython.utils.ipstruct which basically wraps the dict such as one
#       has access to its elements using dot syntax. 
#
#     -- alterntively try workspace being a custom class
#
#   all alteratives WORK AS LONG AS workspace IS EXPLICITLY INJECTED INTO THE CONSOLE'S NAMESPACE!!!
#
#   we set for the second alternative (Struct)
#
#  would this break the access to workspace from other (sub)modules?
#
#
# b) export the Pict main window to the console workspace and make data as instance 
# members on the Pict main window object -- this would clutter Pict object, and also expose _ALL_ the API from ScipyenWindow
#
# For Point (3):
#
#
# Create a "public API" class / module that exposes to the console the public API and delegates to various GUI components
#
# Also this should allow creation & editing of plugins, as dynamically (re)loadable modules
#
# TODO: FIXME do NOT expose Pict window anymore
#
# Think about a simple plugin architecture.
#
# 

# TODO, NOTE, 2016-03-13 22:22:09 provide a mechanism for the user to select between
# a subset of the public names/API for usual work, and all names/API for developer's work
# e.g., by specifying a given command line argument to main()
# for now, heep them all public

# TODO: 2016-03-15 13:57:40 
# think of a clever way to select and export the public API --
# or just rely on python's default naming convention

from __future__ import print_function

#__import_all__ = True

#__public_names__ = ()
#__public_names__ = list()

##__public_names__ = #__public_names__ + ("print_function",)
#__public_names__.append("print_function")


import sys, os
os.environ['QT_API'] = 'pyqt'

##__public_names__ = #__public_names__ + ("sys","os",)
#__public_names__.append("sys")
#__public_names__.append("os")

# 2016-03-19 22:35:09
#from PyQt4 import QtGui, QtCore
# 2016-03-19 22:39:06 try embedded ipython
#from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
#from IPython.qt.inprocess import QtInProcessKernelManager


import PyQt4.QtCore as QtCore
##__public_names__ = #__public_names__ + ("PyQt4.QtCore",)
##__public_names__.append("PyQt4")
#__public_names__.append("QtCore")

import PyQt4.QtGui as QtGui
##__public_names__ = #__public_names__ + ("PyQt4.QtGui",)
#__public_names__.append("QtGui")

from PyQt4.QtCore import SIGNAL, SLOT

#__public_names__.append("SIGNAL")
#__public_names__.append("SLOT")

from PyQt4.uic import loadUiType as __loadUiType__ 

import numpy as np
##__public_names__ = #__public_names__ + ("np",)
#__public_names__.append("np")

import matplotlib as mpl
##__public_names__ = #__public_names__ + ("mpl",)
#__public_names__ .append("mpl")

import matplotlib.pyplot as plt
##__public_names__ = #__public_names__ + ("plt",)
#__public_names__.append("plt")

import matplotlib.pylab as plb
##__public_names__ = #__public_names__ + ("plb",)
#__public_names__.append("plb")

import matplotlib.mlab as mlb
##__public_names__ = #__public_names__ + ("mlb",)
#__public_names__.append("mlb")

import pandas as pd
##__public_names__ = #__public_names__ + ("pd",)
#__public_names__.append("pd")

import quantities as pq
##__public_names__ = #__public_names__ + ("pq",)
#__public_names__.append("pq")

import scipy.io as sio
##__public_names__ = #__public_names__ + ("sio",)
#__public_names__.append("sio")

import javabridge as java
##__public_names__ = #__public_names__ + ("java",)
#__public_names__.append("java")

from javabridge import kill_vm as kill_java
#__public_names__.append("kill_java")

import bioformats as bf
##__public_names__ = #__public_names__ + ("bf",)
#__public_names__.append("bf")

import vigra
##__public_names__ = #__public_names__ + ("vigra",)
#__public_names__.append("vigra")

import vigra.pyqt as vigra_pyqt
##__public_names__ = #__public_names__ + ("vigra.pyqt",)
#__public_names__.append("vigra_pyqt")

import signalviewer as sv
##__public_names__ = #__public_names__ + ("sv",)
#__public_names__ .append("sv")

import pictio as pio
##__public_names__ = #__public_names__ + ("pio",)
#__public_names__.append("pio")

import datatypes
##__public_names__ = #__public_names__ + ("datatypes",)
#__public_names__.append("datatypes")

#kill_java = java.kill_vm
###__public_names__ = #__public_names__ + ("java.kill_vm",)

from axisutils import *

# NOTE: 2016-03-19 22:29:57 use ipython kernel with a console subprocess
from internalIPkernel import InternalIPKernel as __InternalIPKernel__ # 2016-03-11 12:10:39 keep things private


from IPython.utils.ipstruct import Struct as IPStruct
##__public_names__ = #__public_names__ + ("IPStruct",)
#__public_names__.append("IPStruct")

import types
##__public_names__ = #__public_names__ + ("types",)
#__public_names__.append("types")

import atexit
##__public_names__ = #__public_names__ + ("atexit",)
#__public_names__.append("atexit")

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

def start_java():
    try:
        java.start_vm(class_path=bf.JARS)
        print("If you are in an interactive Python shell you must call kill_java() BEFORE calling exit()")
    except:
        print("Could not start a java VM. OME BioFormats functionality is unavailable")
    finally:
        #print("Could not start a java VM. OME BioFormats functionality is unavailable")
        pass

#__public_names__.append("start_java")

atexit.register(java.kill_vm)

#kill_java = javabridge.kill_vm

##__public_names__.append("kill_java")

# NOTE: 2016-03-11 12:10:47 make these private
__Ui_PictWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"PictWindow.ui"))

class Struct(IPStruct):
    def __init__(self, *args, **kw):
        super(Struct, self).__init__(*args, **kw)
    
    def remove(self, key):
        if self.hasattr(key):
            return self.pop(key)
        
##__public_names__ = #__public_names__ + ("Struct",)
#__public_names__.append("Struct")


#__all__ = __public_names__

# NOTE: 2016-03-14 15:42:43 not needed anymore !!!
#workspace = Struct() # 2016-03-13 22:30:39 _WILL_ be pushed into the ipkernel workspace anyway, later

__imported_modules__ = u'\n\nFor convenience, the following modules are imported (custom names indicated where appropriate):' +\
                    u'\n\nnumpy --> np\nmatplotlib --> mpl\nmatplotlib.pyplot --> plt\nmatplotlib.pylab --> plb\nmatplotlib.mlab --> mlb\n' +\
                    u'pandas --> pd\nscipy.io --> sio\nvigra\nvigra.pyqt\nPyQt4.QtCore\nPyQt4.QtGui\ntypes\nsys\nos\n' +\
                    u'IPython.utils.ipstruct --> Struct'+\
                    u'\n\nAnd from the Pict package:\npictio --> pio\nsignalviewer --> sv\n' +\
                    u'\n\nTherefore ipython line magics such as %pylab or %mtplotlib, although still available, are not necessary anymore\n'

# NOTE: 2016-03-19 22:31:02 try embedded ipython kernel
class ScipyenWindow(__QMainWindow__, __Ui_PictWindow__, __InternalIPKernel__):
    '''
    Launches an internal ipython kernel that starts the main gui event loop.
    
    Also offers a Qt console as a separate process (subprocess) as a frontend to
    the ipython kernel via the zmq library.
    
    All work on data is normally done by the user through the gui, which calls the 
    appropriate library functions (e.g. from vigra, tiwt, etc) directly within 
    the workspace of the python interpreter that runs the application. 
    
    The same work can also be done through the ipython kernel via the Qt
    console. To enable this we confine the data variables to a "workspace" dictionary
    that is exposed to the kernel, such that modifications brought to data from 
    "one side" (e.g., from within the console) are automatically seen from "the other
    size as well" (e.g. by the GUI app).
    
    Dependencies imported by the Pict module are made visible to the ipython 
    kernel so that they can be used from the console as well.
    
    '''
    def __init__(self, app, parent=None):
        super(ScipyenWindow, self).__init__(parent)
        self.app = app
        self.setupUi(self)
        self.init_ipkernel('qt')
        #self.ipkernel.start()


        # NOTE: 2016-03-14 15:46:53 self.workspace _WILL_ be the custom workspace of the console
        #
        #
        # NOTE: Internally, _ALL_ data worked on by the GUI has to reside (either directly
        # or as reference) inside this dictionary
        #
        #
        # NOTE: Deleting a variable in this workspace from within the console will 
        # have one of two consequences:
        #
        # a) for variables instantiated OUTSIDE the self.workspace, this will
        #    just unbind the symbol and hide them from the console workspace; 
        #    call self.__restore_workspace() ("Console/Restore workspace" menu item)
        #    to recover them, or 'pw.__restore_workspace()' from the console
        #
        #    example of variables in this category: 
        #
        #    class instances (e.g. ScipyenWindow)
        #
        # b) for variables created directly in the self.workspace (e.g. from 
        #    within the console) such as data variables, loaded modules, aliases,
        #    this will really delete them.
        #
        #
        #    Execept for variables created from within the console, delted ones 
        #    can be restored to their default values by calling self.__restore_workspace()
        #    from the GUI ("Console/Restore workspace" menu item) or 
        #    'pw.__restore_workspace()' from the console
        # 
        
        # NOTE: 2016-03-15 12:03:47 worspace is defined to be
        # the ipkernel.shell.user_ns in the superclass; just populate this with
        # required modules, and interqactive variables which will be seen by PycaT code
        # as elements in the workspace dict
        #self.workspace = self.ipkernel.shell.user_ns # 2016-03-15 11:51:59 done in internalIPkernel
        
        # NOTE: 2016-03-14 15:50:37
        # 
        # for convenience we export this ScipyenWindow instance to the console's workspace; 
        #
        # NOTE: the same stands for all other variables in the console's workspace
        # including loaded modules
        self.workspace['mainWindow'] = self                 # 2016-03-11 12:15:33 also expose this object to user via console
        self.workspace['pw'] = self.workspace['mainWindow'] # self # alias
        
        # NOTE: 2016-03-12 16:07:59 
        # this does not work !!! -- see below for the working solution -- 
        # 2016-03-15 12:05:52 
        # now obsolete for the reason explained further below
        #self.ipkernel.shell.prepare_user_module(user_module=types.ModuleType('Pict'))#, user_ns=workspace) # leave this as None default
        
        # NOTE: 2016-03-14 15:29:58 replace kernel workspace with self.workspace,
        # NOTE: but after self.workspace was updated with the kernel's default workspace
        #
        # NOTE: 2016-03-15 12:03:01 don't do this anymore, because it breaks the autocompletion feature
        # in the console -- why ?!?
        #self.workspace.update(self.ipkernel.shell.user_ns)
        #self.ipkernel.shell.user_ns = self.workspace
        
        
        # NOTE: 2016-03-14 15:34:52 restrict access from the console to a subset
        # NOTE imported modules and the main window object
        
        # NOTE: this is what is needed instead:
        # NOTE: I think it is OK to import * from curent module into the console
        # namespace, as we want to use it as a quick prototyper
        impcmd = ' '.join(['from', __module_name__, 'import *'])
        self.ipkernel.shell.run_cell(impcmd)
        
        # 2016-03-16 23:49:05
        # get a list of non-user-generated variable names in the workspace; these
        # will be exlcuded from the worspace listing in the GUI
        self.__noninteractive_variables__ = [i for i in self.workspace]
        
        self.app.connect(self.app, SIGNAL("lastWindowClosed()"),
                         self.appQuit)
        
        self.actionQuit.triggered.connect(self.appQuit)
        
        self.actionOpen_Console.triggered.connect(self.init_qt_console)
        #self.actionTo_Console.triggered.connect(self.print_workspace)
        self.actionList_Workspace.triggered.connect(self.__list_workspace)
        self.actionRestore_Workspace.triggered.connect(self.__restore_workspace)
        self.actionHelp_On_Console.triggered.connect(self.__help_on_console)
        self.actionOpenFile.triggered.connect(self.openScanDataFile)
        
        # 2016-03-11 16:49:13 jus' checkin'
        #self.ipkernel.shell.run_cell('testvar = 123')
        #self.print_workspace()
        
        # 2016-03-13 13:44:29 let's have the console ON by default
        self.init_qt_console() 
        
        #self.workspace['data']=vigra.VigraArray((256,256))
        
    def __list_workspace(self):
        self.workspaceTextEdit.clear()
        
        # 2016-03-16 23:40:29
        # emulate the who_ls magic of ipython
        out = [ i for i in self.workspace if not i.startswith('_') and i not in self.__noninteractive_variables__]
        
        for i in out:
            self.workspaceTextEdit.append(i)
        
        #for k, v in self.workspace.items():
            #if not k.startswith('_'):
                #self.workspaceTextEdit.append('%s -> %r' % (k, v))

                
    def __restore_workspace(self):
        impcmd = ' '.join(['from', __module_name__, 'import *'])
        self.ipkernel.shell.run_cell(impcmd)
        self.workspace['mainWindow'] = self
        self.workspace['pw'] = self.workspace['mainWindow']
        
        #self.workspace['workspace'] = workspace
        #self.workspace['ws'] = self.workspace['workspace']
        
    def __help_on_console(self):
        print(self.ipkernel.shell.banner2)
        print(__imported_modules__)
        sys.stdout.flush()
        
    def openScanDataFile(self):
        pass

    def appQuit(self):
        kill_java()
        
        if self.console is not None:
            self.console.kill()
            self.console=None
            
        quit()
        
    # NOTE: 2016-03-19 22:41:09 try embedded ipython
    #def init_qt_console(self):
        #self.console = EmbedIPython(a=self.a, testing=self.testing ) # this works, see comments in but_write
        #self.console.executed.connect(self.displayWorkspace)
        #self.ipkernel = self.console.kernel
        #self.workspace = self.console.kernel.shell.user_ns
        #self.workspace['mainWindow'] = self
        #self.workspace['ipkernel'] = self.ipkernel
        #self.workspace['console'] = self.console
        #self.console.show()
        
        
    
        


if __name__ == "__main__":
    
    # 2016-03-19 22:51:03 try embedded ipython
    
    import sys
    
    #print(QtCore)
    #print(QtGui)
    
    #app = QtGui.QApplication(sys.argv)
    #print(type(app))
    
    
    try:
        # NOTE: 2016-03-10 22:51:05 in case this has been launched from within an IPython session
        # although this scenario is bound to fail as in this situation we cannot launch a second kernel
        from IPython.lib.guisupport import get_app_qt4
        app = get_app_qt4()
        #print(type(app))
    except ImportError:
        print("Error importing get_app_qt4")
        app = QtCore.QGuiApplication(sys.argv)
        #print(type(app))
    
    
    try:
        java.start_vm(class_path=bf.JARS)
        #print("\n\nIf you are in an interactive Python shell you must call pict.kill_java() BEFORE calling exit()\n\n")
    except:
        print("\n\nCould not start a java VM. OME BioFormats functionality is unavailable\n\n")
    finally:
        print("Could not start a java VM. OME BioFormats functionality is unavailable")
        pass

    #app = QtApplication([]);
    
    try:
        win = ScipyenWindow(app)
        win.show()
        
        #sys.exit(app.exec_())
        # 2016-03-19 22:52:12 try internal ipkernel + console subprocess
        win.ipkernel.start() # MUST be started HERE when using internal ipkernel
    except:
        kill_java()
    
    
