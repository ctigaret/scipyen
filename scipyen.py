#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''Main module for the Scipyen application '''


#### BEGIN core python modules

#from __future__ import print_function
#from __future__ import absolute_import # for python 2.5
import faulthandler
import sys, os, atexit, re, inspect, gc, sip, io, traceback

#import warnings


# NOTE: 2019-07-29 12:08:47 these are imported indirectly via pict.gui
from PyQt5 import QtCore, QtGui, QtWidgets

if hasattr(QtCore, "QLoggingCategory"):
    QtCore.QLoggingCategory.setFilterRules("qt.qpa.xcb=false")
    
#### END 3rd party modules

# NOTE: on opensuse pyqtgraph expect PyQt4 first, as qtlib; if not found this
# raises an exception; setting pq.Qt.lib later does not work.
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt5"
#os.putenv("PYQTGRAPH_QT_LIB", "PyQt5")


import gui.mainwindow as mainwindow



#app = None

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
    faulthandler.enable()

    sip.setdestroyonexit(True)

    try:
        #sip.setdestroyonexit(False)
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle(MyProxyStyle())
        
        app.setOrganizationName("Scipyen")
        app.setApplicationName("Scipyen")
    
        gc.enable()

        #import pudb
        mainWindow = mainwindow.ScipyenWindow(app)
        
        mainWindow.show()
        
        app.exec()
        
    except Exception as e:
        #faulthandler.dump_traceback()
        traceback.print_exc()
        
if __name__ == '__main__':
    main()
        
