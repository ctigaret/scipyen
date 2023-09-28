# -*- coding: utf-8 -*-
'''Main module for the Scipyen application '''


#### BEGIN core python modules

import sys, os, platform, pathlib

import atexit, re, inspect, gc, io, traceback
import faulthandler, warnings
#import cProfile
__version__ = "0.0.1"

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

__bundled__ = False

# has_breeze_resources_for_win32 = False
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    print(f'\nScipyen is running in a PyInstaller bundle with frozen modules: {sys.frozen}; _MEIPASS: {sys._MEIPASS}; __file__: {__file__}\n\n')
    # print("WARNING: External consoles (including NEURON) are currently NOT supported\n\n")
    if os.path.isfile(os.path.join(__module_path__, "bundle_origin")):
        with open(os.path.join(__module_path__, "bundle_origin"), "rt", encoding="utf-8") as origin_file:
            for line in origin_file:
                print(line, end="")
    # os.environ["SCIPYEN_UI_PATH"] = "UI"
    __bundled__ = True

else:

    if sys.platform == "win32" and sys.version_info.minor >= 9:
        if "CONDA_DEFAULT_ENV" not in os.environ:
            raise OSError("On windows platform, unbundled Scipyen must be run inside a conda environment")
#         import win32api
#         vigraimpex_mod = "vigraimpex"
#         path_to_vigraimpex = win32api.GetModuleFileName(win32api.LoadLibrary(vigraimpex_mod))
#         os.add_dll_directory(os.path.dirname(path_to_vigraimpex))
#         lib_environ = os.environ.get("LIB", "")
#
#
#         if len(lib_environ.strip()):
#             libdirs = lib_environ.split(os.pathsep)
#             for d in libdirs:
#                 if len(d.strip()) and  os.path.isdir(d):
#                     os.add_dll_directory(d)

    os.environ["QT_API"] = "pyqt5"

    # try:
    #     import breeze_resources
    #     has_breeze_resources_for_win32 = True
    # except:
    #     has_breeze_resources_for_win32 = False



#### END core python modules

#### BEGIN 3rd party modules

from PyQt5 import (QtCore, QtWidgets, QtGui, )
import sip
hasQDarkTheme = False
# try:
#     import qdarktheme
#     hasQDarkTheme = True
# except:
#     pass

# NOTE: 2023-09-28 22:12:25 
# this does the trick on windows -  now my local breeze icons are available
# so we keep with those (they're too nice, anyway!)
#
# works in conjunction with code at NOTE: 2023-09-28 22:06:54
#
#
# on linux, we rely on platform-level modules, which get packed by pyinstaller
# when building the bundle
#
# MAYBE TODO/FIXME 2023-09-28 22:17:16 MAY
# try a similar trick for linux
if sys.platform == "win32":
    mpath = pathlib.Path(__module_path__)

    iconsdir = mpath / "gui" / "resources" / "icons"

    if iconsdir.is_dir():
        themePaths = QtGui.QIcon.themeSearchPaths()
        themePaths.append(str(iconsdir))
        QtGui.QIcon.setThemeSearchPaths(themePaths)
        # QtGui.QIcon.setThemeName("breeze-dark") 
    

#### END 3rd party modules

#### BEGIN Scipyen modules
from core import scipyen_config
#### END Scipyen modules


# else:
#     print('Running in a normal Python process\n\n')
    
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
    # this does not prevent crashes when exiting NEURON - leave here so
    # that we know we tried and didn't work
    #if sys.platform == "linux":
        #import subprocess
        #compl = subprocess.run(["xrdb", "-merge", os.path.join(__module_path__, "neuron_python",  "app-defaults", "nrniv")])
        #print("xrdb: ", compl.returncode)
    #sip.setdestroyonexit(True)

    try:
        sip.setdestroyonexit(True) # better leave to default
        
        # NOTE: 2021-08-17 10:07:11 is this needed?
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        QtGui.QGuiApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
        
        # BEGIN 
        # 1. create the pyqt5 app
        app = QtWidgets.QApplication(sys.argv)
        
        # NOTE: 2023-09-28 22:06:54
        # this should be necessary only on windows platform
        # see also NOTE: 2023-09-28 22:12:25
        #
        # On linux we rely on platform plugins (which also get bundled when
        # building a pyinstaller bundle, as per scipyen.spec)
        if sys.platform == "win32":
            if hasQDarkTheme:
                qdarktheme.setup_theme("auto")
                QtGui.QIcon.setThemeName("breeze-dark")
            else:
                windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
                _,_,v,_ = windowColor.getHsv()
                if v > 128:
                    QtGui.QIcon.setThemeName("breeze")
                else:
                    QtGui.QIcon.setThemeName("breeze-dark")
                
                # QtGui.QIcon.setThemeName("breeze")
            
        # NOTE: 2023-01-08 00:48:47
        # avoid global menus - must be called AFTER we have an instance of app!
        # QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_DontUseNativeMenuBar)
        
        # if has_breeze_resources_for_win32:
        #     file = QtCore.QFile(":/dark/stylesheet.qss")
        #     file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text)
        #     stream = QtCore.QTextStream(file)
        #     app.setStyleSheet(stream.readAll())
            
        
        # NOTE: 2021-08-17 10:05:20
        # explore the possibility to customize look and feel
        # for now, we just use whatever the system uses
        #app.setStyle(QtWidgets.QStyleFactory.create("Breeze"))
        #app.setStyle(MyProxyStyle())
        
        app.setApplicationName(scipyen_config.application_name)
        app.setOrganizationName(scipyen_config.organization_name)
        
        #print(f"scipyen.main() global qsettings {qsettings.fileName()}")
        
        gc.enable()

        #import pudb
        
        # 2. initialize main window
        mainWindow = mainwindow.ScipyenWindow(app, bundled = __bundled__)# qsettings = qsettings)
        
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
    if sys.version_info.major < 3 or sys.version_info.minor < 9:
        raise OSError(f"Scipyen requires Python >= 3.9 but the script is using {sys.version}")
    main()
    
