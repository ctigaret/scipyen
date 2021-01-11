#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''Main module for the Scipyen application '''


#### BEGIN core python modules

#from __future__ import print_function
#from __future__ import absolute_import # for python 2.5
import faulthandler
import sys, os, atexit, re, inspect, gc, io, traceback

#import warnings
#### END core python modules

#### BEGIN 3rd party modules

import confuse # configuration library for non-gui options

# NOTE: 2019-07-29 12:08:47 these are imported indirectly via pict.gui
from PyQt5 import QtCore, QtWidgets
#### END 3rd party modules

#import scipyen_defaults

# ===================================================
# NOTE: 2021-01-08 10:59:00  Scipyen options/settings
# ===================================================
# While gui-related options (e.g., window size/position, recent files,
# recent directories, etc.) are stored using the PyQt5/Qt5 settings framework,
# non-gui options contain custom parameter values for various modules, e.g.
# options for ScanData objects, trigger detection, etc. 
# 
# These "non-gui" options are often represented by nested dictionary (hierarchical)
# structures not easily amenable to the linear (and binary) format of the Qt5 
# settings framework.
#

# NOTE: 2021-01-10 13:17:58
# LazyConfig inherits form confuse.Configuration, but its read() method must be 
# called explicitly/programmatically (i.e. unlike its ancestor Configuration,
# read is NOT called at initialization).
# 
# this is the passed to the mainWindow constructor as the 'settings' parameter
# where its read() method must be called exactly once!
scipyen_config = confuse.LazyConfig("Scipyen", "scipyen_defaults")

# NOTE: 2021-01-10 13:19:20
# the same Configuration object holds/merges both the user options and the 
# package defaults (therefore there is no need for two Configuration objects)
#scipyen_defaults = confuse.LazyConfig("Scipyen", "scipyen_defaults")

if hasattr(QtCore, "QLoggingCategory"):
    QtCore.QLoggingCategory.setFilterRules("qt.qpa.xcb=false")

# NOTE: on opensuse pyqtgraph expect PyQt4 first, as qtlib; if not found this
# raises an exception; setting pq.Qt.lib later does not work.
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt5"
#os.putenv("PYQTGRAPH_QT_LIB", "PyQt5")

#sys.path.insert(2, os.path.dirname(os.path.dirname(__file__)))


class MyProxyStyle(QtWidgets.QProxyStyle):
    """To prevent repeats of valueChanged in QSpinBox controls for frame navigation.
    
    This raises the spin box SH_SpinBox_ClickAutoRepeatThreshold so that
    valueChanged is not repetedly called when frame navigation takes too long time.
    
    See https://bugreports.qt.io/browse/QTBUG-33128.
    
    """
    def __init__(self, *args):
        super().__init__(*args)
        
    def styleHint(self, hint, *args, **kwargs):
        if hint == QtWidgets.QStyle.SH_SpinBox_ClickAutoRepeatRate:
            return 0
        
        elif hint == QtWidgets.QStyle.SH_SpinBox_ClickAutoRepeatThreshold:
            return 1000000
        
        return super().styleHint(hint, *args, **kwargs)

def main():
    import gui.mainwindow as mainwindow
    faulthandler.enable()

    #sip.setdestroyonexit(True)

    try:
        #sip.setdestroyonexit(False)
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        library_paths = QtCore.QCoreApplication.libraryPaths()
        #library_paths.insert(0,'/usr/lib64/qt5/plugins')
        library_paths.append('/usr/lib64/qt5/plugins')
        library_paths = QtCore.QCoreApplication.setLibraryPaths(library_paths)
        app = QtWidgets.QApplication(sys.argv)
        #app.setStyle(QtWidgets.QStyleFactory.create("Breeze"))
        #app.setStyle(MyProxyStyle())
        
        app.setOrganizationName("Scipyen")
        app.setApplicationName("Scipyen")
    
        gc.enable()

        #import pudb
        mainWindow = mainwindow.ScipyenWindow(app, 
                                              settings = scipyen_config)
        
        #mainWindow = mainwindow.ScipyenWindow(app, 
                                              #defaults = scipyen_defaults,
                                              #settings = scipyen_config)
        
        mainWindow.show()
        
        app.exec()
        
    except Exception as e:
        #faulthandler.dump_traceback()
        traceback.print_exc()
        
if __name__ == '__main__':
    main()
        
