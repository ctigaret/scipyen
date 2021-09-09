# -*- coding: utf-8 -*-
'''Main module for the Scipyen application '''


#### BEGIN core python modules

import faulthandler
import sys, os, atexit, re, inspect, gc, io, traceback
import cProfile

#import warnings
#### END core python modules

#### BEGIN 3rd party modules

# NOTE: 2019-07-29 12:08:47 these are imported indirectly via pict.gui
from PyQt5 import (QtCore, QtWidgets, QtGui, )
#### END 3rd party modules

#### BEGIN Scipyen modules
from core import scipyen_config # non-gui-related settings
#### END Scipyen modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

# NOTE: 2021-01-10 13:19:20
# the same Configuration object holds/merges both the user options and the 
# package defaults (therefore there is no need for two Configuration objects)
#scipyen_defaults = confuse.LazyConfig("Scipyen", "scipyen_defaults")

if hasattr(QtCore, "QLoggingCategory"):
    QtCore.QLoggingCategory.setFilterRules("qt.qpa.xcb=false")

# NOTE: on opensuse pyqtgraph expect PyQt4 first, as qtlib; if not found this
# raises an exception; setting pq.Qt.lib later does not work.
# therefore is better to set this up early, here.
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt5"
#os.putenv("PYQTGRAPH_QT_LIB", "PyQt5")


class MyProxyStyle(QtWidgets.QProxyStyle):
    """To prevent repeats of valueChanged in QSpinBox controls for frame navigation.
    
    This raises the spin box SH_SpinBox_ClickAutoRepeatThreshold so that
    valueChanged is not repetedly called when frame navigation takes too long time.
    
    See https://bugreports.qt.io/browse/QTBUG-33128.
    
    """
    # NOTE: 2021-08-17 10:01:32 FIXME
    # not really used? TODO DEPRECATED
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

    # NOTE: 2021-08-17 10:02:20
    # thsi did not improve / prevent crashes when exiting NEURON - leave here so
    # that we know we tried and didn't work
    #if sys.platform == "linux":
        #import subprocess
        #compl = subprocess.run(["xrdb", "-merge", os.path.join(__module_path__, "neuron_python",  "app-defaults", "nrniv")])
        #print("xrdb: ", compl.returncode)
    #sip.setdestroyonexit(True)

    try:
        #sip.setdestroyonexit(False) # better leave to default
        
        # NOTE: 2021-08-17 10:07:11 is this needed?
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        
        # BEGIN 
        # 1. create the pyqt5 app
        app = QtWidgets.QApplication(sys.argv)
        
        # NOTE: 2021-08-17 10:05:20
        # explore the possibility to customize look and feel
        # for now, we just use whatever the system uses
        #app.setStyle(QtWidgets.QStyleFactory.create("Breeze"))
        #app.setStyle(MyProxyStyle())
        
        app.setOrganizationName("Scipyen")
        app.setApplicationName("Scipyen")
    
        gc.enable()

        #import pudb
        
        # 2. initialize main window
        mainWindow = mainwindow.ScipyenWindow(app)#, settings = scipyen_config.scipyen_config)
        
        # NOTE: 2021-08-17 10:06:24 FIXME / TODO
        # come up with a nice icon?
        # see also NOTE: 2021-08-17 12:36:49 in gui.mainwindow
        #mainWindow.setWindowIcon(app.icon)
        
        # 3. show the main window
        mainWindow.show()
        
        # 4. start the main GUI app (pyqt5) event loop
        app.exec()
        
    except Exception as e:
        #faulthandler.dump_traceback()
        traceback.print_exc()
        
if __name__ == '__main__':
    main()
    
    #cProfile.run("main()", "profile.txt", 2)
        
