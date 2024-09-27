# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# nuitka-project: --standalone
# nuitka-project: --enable-plugin=pyqt5

'''Main module for the Scipyen application '''


#### BEGIN core python modules

import sys, os, platform, pathlib, subprocess

import atexit, re, inspect, gc, io, traceback
import faulthandler, warnings
import xdg
from xdg import IconTheme

from core.prog import scipywarn

my_conda_env = os.environ.get("CONDA_DEFAULT_ENV", None)
conda_env_prefix = os.environ.get("CONDA_PREFIX", None)

my_virtualenv = os.environ.get("VIRTUAL_ENV", None)

if isinstance(my_conda_env, str) and len(my_conda_env.strip()):
    conda_env_prefix = os.environ.get("CONDA_PREFIX", None)
            
    print(f"Scipyen is running in the conda environment {my_conda_env} (located at {conda_env_prefix})\n")
    
    if my_conda_env == "base":
        scipywarn("Scipyen should be run in its own conda environment.\n")
        
elif isinstance(my_virtualenv, str) and len(my_virtualenv.strip()):
    print(f"Scipyen is running in the virtualenv environment {my_virtualenv}\n")
    
else:
    raise RuntimeError("Scipyen must be run in a virtualenv virtual Python environment or a conda environment\n")


# NOTE: 2024-05-02 10:22:39
# optional use of Qt6 as PyQt5/6 or PySide2/6
# but currently, force Qt5 (for now)
os.environ["QT_API"] = "pyqt5"
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt5"

# NOTE: 2024-05-04 10:14:08
# forcing xcb platform when running on Wayland, in Linux, because we want to
# restore window sizes and positions from Scipyen.conf (Wayland does not allow
# an application 'client' to control window position)
if sys.platform == "linux":
    if os.getenv("XDG_SESSION_TYPE", None) == "wayland":
        # print("In a wayland session")
        os.environ["QT_QPA_PLATFORM"]="xcb"
        # import pywayland
        
    new_xdg_data_dirs = [os.path.join(os.environ["HOME"], ".local", "share")]

    # conda_env_prefix was defined above
    if isinstance(conda_env_prefix, str) and len(conda_env_prefix.strip()):
        conda_env_xdg_data_dir = os.path.join(conda_env_prefix, "share")
        conda_env_icons_dir = os.path.join(conda_env_xdg_data_dir, "icons")
        if os.path.isdir(conda_env_xdg_data_dir):
            new_xdg_data_dirs.append(conda_env_xdg_data_dir)

        if os.path.isdir(conda_env_icons_dir):
            IconTheme.icondirs.append(conda_env_icons_dir)

    env_xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", None)

    if isinstance(env_xdg_data_dirs, str):
        xdg_data_dirs = env_xdg_data_dirs.split(":")
    else:
        xdg_data_dirs = list()

    xdg_data_dirs.extend(new_xdg_data_dirs)

    os.environ["XDG_DATA_DIRS"] = ":".join(xdg_data_dirs)
        
    # os.environ["QT_QPA_PLATFORM"]="xcb"
    
# TODO 2024-09-11 23:56:17
# use qtpaths or qtpaths6 to figure out where the platform QT5/6 is installed
# if at all
# then add the corresponding plugins dir to QT_PLUGINS_PATH
# so we won't have to build qt locally anymore, by the installer

if len(sys.argv) > 1:
    if "pyqt6" in sys.argv:
        os.environ["QT_API"] = "pyqt6"
        os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"
        
    elif "pyside2" in sys.argv:
        os.environ["QT_API"] = "pyside2" # for up to Qt5
        os.environ["PYQTGRAPH_QT_LIB"] = "PySide2"
        
    elif "pyside6" in sys.argv:
        os.environ["QT_API"] = "pyside6"
        os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"
        
    else:
        os.environ["QT_API"] = "pyqt5"
        os.environ["PYQTGRAPH_QT_LIB"] = "PyQt5"
        

#import cProfile
__version__ = "0.0.1"

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

__bundled__ = False

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # print(f'\nScipyen is running in a PyInstaller bundle with frozen modules: {sys.frozen}; _MEIPASS: {sys._MEIPASS}; __file__: {__file__}\n\n')
    # print("WARNING: External consoles (including NEURON) are currently NOT supported\n\n")
    if os.path.isfile(os.path.join(__module_path__, "bundle_origin")):
        with open(os.path.join(__module_path__, "bundle_origin"), "rt", encoding="utf-8") as origin_file:
            for line in origin_file:
                print(line, end="")
    __bundled__ = True
    
    # NOTE: 2024-05-31 11:10:49
    # internal plugins which are NOT imported via the usual importlib mechanism
    # are skipped by PyInstaller; hence we include their source files INSIDE the
    # bundle; then we need to make sys aware of their location
    # sys.path.append(os.path.join(sys._MEIPASS, 'src', 'scipyen'))

else:
    # NOTE: 2024-05-02 10:24:48
    # running from a locally built environment under Windows
    if sys.platform == "win32" and sys.version_info.minor >= 9:
        if "CONDA_DEFAULT_ENV" not in os.environ:
            raise OSError("On windows platform, unbundled Scipyen must be run inside a conda environment")

#### END core python modules

#### BEGIN 3rd party modules

if os.environ["QT_API"] in ("pyqt5", "pyqt6"):
    from qtpy import sip
    has_sip = True
else:
    has_sip = False

# NOTE: 2024-05-02 09:46:11
# you still need the QT_API in the environment
from qtpy import (QtCore, QtWidgets, QtGui, )
# from PyQt5 import (QtCore, QtWidgets, QtGui, )
# print(f"Scipyen is using Qt version {QtCore._qt_version}\n")

from core.prog import scipywarn

if os.environ["QT_API"] == "pyside2":
    scipywarn("PySide2 support is not fully implemented; expect trouble")

hasQDarkTheme = False
try:
    import qdarktheme
    hasQDarkTheme = True
except:
    pass


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
mpath = pathlib.Path(__module_path__)

# iconsdir = mpath / "gui" / "resources" / "icons"
# iconsdir = mpath / "gui" / "resources" 

    
# NOTE: 2024-09-26 13:09:00
# this should extend the availability for Qt icons globally, in this Scipyen session
themePaths = QtGui.QIcon.themeSearchPaths()
fbPaths = QtGui.QIcon.fallbackSearchPaths()
if sys.platform == "linux":
    themePaths.extend(IconTheme.icondirs)
    fbPaths.extend(IconTheme.icondirs)
    
    
# NOTE: 2023-09-30 15:49:27 
# this below is ALWAYS added by default in the Qt resource system
# themePaths.append(":/icons") 

# if iconsdir.is_dir():
#     themePaths.append(str(iconsdir))
#     fbPaths.append(str(iconsdir))
    
QtGui.QIcon.setThemeSearchPaths(themePaths)
QtGui.QIcon.setFallbackSearchPaths(fbPaths)


    
# NOTE: 2023-09-28 22:06:54
# this should be necessary only on windows platform
# see also NOTE: 2023-09-28 22:12:25
#
# On linux we rely on platform plugins (which also get bundled when
# building a pyinstaller bundle, as per scipyen.spec)
if sys.platform == "win32":
    if hasQDarkTheme:
        # qdarktheme.setup_theme("auto")
        qdarktheme.enable_hi_dpi()
        QtGui.QIcon.setThemeName("breeze-dark")
    else:
        windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
        _,_,v,_ = windowColor.getHsv()
        if v > 128:
            QtGui.QIcon.setThemeName("breeze")
        else:
            QtGui.QIcon.setThemeName("breeze-dark")
            
        # FIXME 2023-09-28 23:22:31 BUG
        # github merry-go-round replaces svg symbolic links (linux) with 
        # simple text files containing the name of the target - this causes 
        # the qt-svg plugin to sill out tons of error messages
        # TODO: either
        # 1) figure out how to ignore these symbolic links on Windows
        # 2) figure out how to ignore the qt-svg error messages
        #
        # I prefer the first option; a contrived solution is to store on git hub
        # an archive of the icon directories, and ignore the icons directories in 
        # .gitignore
        # unfortunately, this means that after each git pull we'd have to manually
        # expand these directory, onse something has changed
        #
        # 3) incorporate these icons in qrc and resources.py files
        # the problem with that is that the py and qrc files sizes easily 
        # get over the file size limit in github, unless I somehow break down
        # these into a qrc/py resource files for each subdirectory - brrr...
        #
        # until then, on Windows we will have to put up with the qt-svg messages
        # for now...
        
elif sys.platform == "darwin":
    windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
    _,_,v,_ = windowColor.getHsv()
    if v > 128:
        QtGui.QIcon.setThemeName("breeze")
    else:
        QtGui.QIcon.setThemeName("breeze-dark")
    
        
#### END 3rd party modules

#### BEGIN Scipyen modules
from core import scipyen_config
#### END Scipyen modules

# NOTE: 2021-01-10 13:19:20
# the same Configuration object holds/merges both the user options and the 
# package defaults (therefore there is no need for two Configuration objects)
#scipyen_defaults = confuse.LazyConfig("Scipyen", "scipyen_defaults")

if hasattr(QtCore, "QLoggingCategory"):
    QtCore.QLoggingCategory.setFilterRules("qt.qpa.xcb=false")


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
    # print(f"Using {os.environ['QT_API']} for GUI and {os.environ['PYQTGRAPH_QT_LIB']} for PyQtGraph\n")
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
        # BEGIN 
        # 1. create the pyqt5 app
        app = QtWidgets.QApplication(sys.argv)
        
            
        if sys.platform == "win32":
            if hasQDarkTheme:
                qdarktheme.setup_theme("auto")
                
        elif sys.platform == "linux":
            # NOTE: 2024-05-04 10:16:33
            # reuired on Wayland so that the window manager decorates the windows
            # with the appropriate icon instead of using the generic Wayland one.
            # NOTE that this good to have even when forcing the use xcb platform 
            # (see NOTE: 2024-05-04 10:14:08 above) as it conforms to the desktop
            # standards
            app.setDesktopFileName("Scipyen")


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
        mainWindow = mainwindow.ScipyenWindow(app)
        # mainWindow = mainwindow.ScipyenWindow(app, bundled = __bundled__)# qsettings = qsettings)
        
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
    
