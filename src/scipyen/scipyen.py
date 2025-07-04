# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# nuitka-project: --standalone
# nuitka-project: --enable-plugin=pyqt5

'''Main module for the Scipyen application '''


#### BEGIN core python modules

import sys, os, platform, pathlib, subprocess, traceback

import atexit, re, inspect, gc, io, time
import faulthandler, warnings
import xdg
from xdg import IconTheme

#### BEGIN Scipyen modules
#
from core.prog import scipywarn, print_styled
from core import sysutils, prog
from core import scipyen_config
#
#### END Scipyen modules


my_conda_env = os.environ.get("CONDA_DEFAULT_ENV", None)
conda_env_prefix = os.environ.get("CONDA_PREFIX", None)

my_virtualenv = os.environ.get("VIRTUAL_ENV", None)

if isinstance(my_conda_env, str) and len(my_conda_env.strip()):
    conda_env_prefix = os.environ.get("CONDA_PREFIX", None)

    if my_conda_env == conda_env_prefix:
        print(f"Scipyen is running in the conda environment {print_styled(my_conda_env, color='yellow')}\n")
    else:
        print(f"Scipyen is running in the conda environment {print_styled(my_conda_env, color='yellow')} (located at {print_styled(conda_env_prefix, color='green')})\n")
    
    if my_conda_env == "base":
        scipywarn("Scipyen should be run in its own conda environment.\n")
        
elif isinstance(my_virtualenv, str) and len(my_virtualenv.strip()):
    # pass # OK
    print(f"Scipyen is running in the virtualenv environment {print_styled(my_virtualenv, color='yellow')}\n")

elif getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    print(f"Scipyen is running in a {print_styled('PyInstaller bundle', color='yellow')}\n")
else:
    raise RuntimeError("Scipyen must be run in a virtualenv virtual Python environment, a conda environment, or a PyInstaller bundle\n")

os.environ["FORCE_COLOR"] = "1"

if sys.platform.startswith("linux"):
    # NOTE: 2024-05-04 10:14:08
    # forcing xcb platform when running on Wayland, in Linux, because we want to
    # restore window sizes and positions from Scipyen.conf (Wayland does not allow
    # an application 'client' to control window position)
    # NOTE: 2024-11-09 21:03:16
    # code below introuced to allow positoning of windows based on saved geometry(ies)
    # which doesn't work on wayland
    if os.getenv("XDG_SESSION_TYPE", None) == "wayland":
        os.environ["QT_QPA_PLATFORM"]="xcb"
    # if os.getenv("XDG_SESSION_TYPE", None) == "wayland":
    #     os.environ["QT_QPA_PLATFORM"]="wayland"
        
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
    
# TODO 2024-09-11 23:56:17 - NO! see NOTE: 2025-07-01 09:42:46
# use qtpaths or qtpaths6 to figure out where the platform QT5/6 is installed
# if at all
# then add the corresponding plugins dir to QT_PLUGINS_PATH
# so we won't have to build qt locally anymore, by the installer
#
# NOTE: 2025-07-01 09:42:46 -> the platform libraries likely to have different
# hence different build from what is installed from PyPI, thus crashing the 
# application

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
    
else:
    # NOTE: 2024-05-02 10:24:48
    # running from a locally built environment under Windows
    if sys.platform.startswith("win32") and sys.version_info.minor >= 9:
        if "CONDA_DEFAULT_ENV" not in os.environ:
            raise OSError("On windows platform, unbundled Scipyen must be run inside a conda environment")

#### END core python modules

#### BEGIN 3rd party modules
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
        
    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True
    
# # print(f"scipyen.py: qtpy.API is {qtpy.API}")

# hasQDarkTheme = False
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
mpath = pathlib.Path(__module_path__)

# iconsdir = mpath / "gui" / "resources" / "icons"
# iconsdir = mpath / "gui" / "resources" 

    
# NOTE: 2024-09-26 13:09:00
# this should extend the availability for Qt icons globally, in this Scipyen session
themePaths = QtGui.QIcon.themeSearchPaths()
fbPaths = QtGui.QIcon.fallbackSearchPaths()
if sys.platform.startswith("linux"):
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
if sys.platform.startswith("win32"):
    windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
    _,_,v,_ = windowColor.getHsv()
    themeName="breeze" if v > 128 else "breeze-dark"
    # print(f"windowColor HSV: {v} -> themeName: {themeName}")

    QtGui.QIcon.setThemeName(themeName)
    # if hasQDarkTheme:
    #     # qdarktheme.setup_theme("auto") # NOTE: 2025-03-02 20:52:51
    #                                      # this MUST be called after the initlization of the QApplication
    #                                      # see NOTE: 2025-03-02 20:53:09 below
    #     qdarktheme.enable_hi_dpi()
    #     QtGui.QIcon.setThemeName("breeze-dark")
    # else:
    #     windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
    #     _,_,v,_ = windowColor.getHsv()
    #     themeName="breeze" if v > 128 else "breeze-dark"
    #     # print(f"windowColor HSV: {v} -> themeName: {themeName}")
    #
    #     QtGui.QIcon.setThemeName(themeName)

        # if v > 128:
        #     QtGui.QIcon.setThemeName("breeze")
        # else:
        #     QtGui.QIcon.setThemeName("breeze-dark")

        # FIXME 2023-09-28 23:22:31 BUG
        # github merry-go-round replaces svg symbolic links (linux) with
        # simple text files containing the name of the target - this causes
        # the qt-svg plugin to sill out tons of error messages
        # TODO: either
        # 1) figure out how to ignore these symbolic links on Windows
        # 2) figure out how to ignore the qt-svg error messages
        #
        # I would prefer the first option; a contrived solution is to store on git hub
        # an archive of the icon directories, and ignore the icons directories in
        # .gitignore
        # unfortunately, this means that after each git pull we'd have to manually
        # expand these directory, once something has changed
        #
        # 3) incorporate these icons in qrc and resources.py files
        # the problem with that is that the py and qrc files sizes easily
        # get over the file size limit in github, unless I somehow break down
        # these into a qrc/py resource files for each subdirectory - brrr...
        #
        # until then, on Windows we will have to put up with the qt-svg messages
        # for now...

elif sys.platform.startswith("darwin"):
    windowColor = QtWidgets.QApplication.palette().color(QtGui.QPalette.Window)
    _,_,v,_ = windowColor.getHsv()
    themeName="breeze" if v > 128 else "breeze-dark"
    # print(f"windowColor HSV: {v} -> themeName: {themeName}")

    QtGui.QIcon.setThemeName(themeName)
    
        
#### END 3rd party modules

# NOTE: 2021-01-10 13:19:20
# the same Configuration object holds/merges both the user options and the 
# package defaults (therefore there is no need for two Configuration objects)
#scipyen_defaults = confuse.LazyConfig("Scipyen", "scipyen_defaults")

if hasattr(QtCore, "QLoggingCategory"):
    QtCore.QLoggingCategory.setFilterRules("qt.qpa.xcb=false")


class MyProxyStyle(QtWidgets.QProxyStyle):
    r"""To prevent repeats of valueChanged in QSpinBox controls for frame navigation.
    
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
    # NOTE: 2025-01-22 08:57:15 
    # this must be executed AFTER the QApplication is initialized.
    # See NOTE: 2025-01-22 08:56:42
    # see also WARNING: 2025-01-22 08:55:40 in gui.mainwindow
    # import gui.mainwindow as mainwindow
    # print(f"Using {os.environ['QT_API']} for GUI and {os.environ['PYQTGRAPH_QT_LIB']} for PyQtGraph\n")
    faulthandler.enable()
    
    # NOTE: 2021-08-17 10:02:20
    # this does not prevent crashes when exiting NEURON - leave here so
    # that we know we tried it and it didn't work
    #if sys.platform.startswith("linux"):
        #import subprocess
        #compl = subprocess.run(["xrdb", "-merge", os.path.join(__module_path__, "neuron_python",  "app-defaults", "nrniv")])
        #print("xrdb: ", compl.returncode)
    #sip.setdestroyonexit(True)
    
    if __has_PySide6__:
        appName = "Scipyen-PySide6"
    elif __has_PyQt6__:
        appName = "Scipyen-PyQt6"
    else:
        appName = "Scipyen"

    try:
        start = time.perf_counter()
        print("Scipyen is initializing, please wait...\n")
        # BEGIN 
        # 1. create the app
        app = QtWidgets.QApplication(sys.argv)
        # NOTE: 2025-07-01 14:45:39
        # this MUST be imported AFTER, and NOT BEFORE creating the app in the 
        # line above
        import gui.mainwindow as mainwindow
        translator = QtCore.QTranslator(app)
        if os.environ["QT_API"] == "pyside6":
            translator.load(QtCore.QLocale.system(), "qtbase", "_", QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.TranslationsPath))
        else:
            translator.load(QtCore.QLocale.system(), "qtbase", "_", QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath))
        app.installTranslator(translator)

        app.setDesktopFileName(appName)

        app.setApplicationName(scipyen_config.application_name)
        app.setOrganizationName(scipyen_config.organization_name)
        
        gc.enable()
        
        # ### BEGIN Splash screen shenanigans
        splash=None
        import gui.splash as guisplash
        
        if __has_PyQt6__ or __has_PySide6__:
            # BUG 2025-07-02 01:05:08 FIXME/TODO
            # splash shows as a black rectangle, so set aside for now, in PyQt6/PySide6
            # until I fire out the problem
            mainWindow = mainwindow.ScipyenWindow()
        else:
            icon = QtGui.QIcon.fromTheme("pythonbackend")
            pixmap = icon.pixmap(QtCore.QSize(256,256), state=QtGui.QIcon.On)
            
            splash = guisplash.ScipyenSplash(pixmap)
            # app.processEvents()
            # splash.setAttribute(QtCore.Qt.WA_StyledBackground)
            # splash.setAttribute(QtCore.Qt.WA_TranslucentBackground + QtCore.Qt.WA_StyledBackground + QtCore.Qt.WA_FramlessWindowHint)
            
            if splash:
                # app.processEvents()
                # splash.show()
                # NOTE: 2025-07-02 01:06:30
                # this WILL show, but signals from the mainwindow won't take effect due to queued connection;
                # on the other hand, if using direct connection or autoconnection (which resolves to direct connection
                # on account of both being in the same, main, thread) the menubar won't register with the dbus
                # through the Qt's default (built-in) mechanism.
                # Perhaps designing its own dbus interface might help, but need to learn moe about dbus and
                # then how to register with the AppMenu dbus service manually .. brrrr....
                
                
                splash.splashWidget.showMessage("Scipyen is initializing, please wait...",
                                QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter,
                                QtGui.QColor("yellow"))
                QtGui.QGuiApplication.processEvents() # app.processEvents()
            
                mainWindow = mainwindow.ScipyenWindow(splash=splash.splashWidget)
                # app.setActiveWindow(mainWindow)
                # app.processEvents()
                # mainWindow.menuBar().setNativeMenuBar(mainWindow.useNativeMenuBar)
                # splash.splashWidget.finish(mainWindow)
                # if mainWindow.isVisible():
                #     splash.close()
            else:
                mainWindow = mainwindow.ScipyenWindow()
                
        # mainWindow.show()
        
        # ### END   Splash screen shenanigans
    
        # mainWindow = mainwindow.ScipyenWindow()
        
        # NOTE: 2021-08-17 10:06:24 FIXME / TODO
        # come up with a nice icon?
        # see also NOTE: 2021-08-17 12:36:49 in gui.mainwindow
        #mainWindow.setWindowIcon(app.icon)
        
        # 3. show the main window
        # mainWindow.show()
        
        end = time.perf_counter()
        print(f"Scipyen initialization took {end - start} s")
        # 4. start the main GUI app (pyqt5) event loop
        app.exec()
    except Exception as e:
        #faulthandler.dump_traceback()
        traceback.print_exc()
        
if __name__ == '__main__':
    if sys.version_info.major < 3 or sys.version_info.minor < 9:
        raise OSError(f"Scipyen requires Python >= 3.9 but the script is using {sys.version}")
    # print(f"sys.argv: {sys.argv}")
    main()
    
