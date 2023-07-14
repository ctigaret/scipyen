"""System and platform utilities
"""
import os, sys, subprocess, shutil, platform
from shutil import which

from PyQt5 import (QtCore, QtWidgets, QtGui, QtDBus)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)

def get_wm():
    """Retrieves the name of the window manager, on Linux platforms.
    On any other platforms returns None.
    Somewhat redundant to get_desktop()
    """
    # NOTE: 2023-01-07 16:08:36
    # From
    # https://stackoverflow.com/questions/3333243/how-can-i-check-with-python-which-window-manager-is-running
    if not sys.platform.startswith("linux"):
        return
    
    # wmctrl = which("wmctrl")
    wmctrl = shutil.which("wmctrl")
    
    if len(wmctrl):
        wmctrl = os.path.basename(wmctrl)
        
        out = subprocess.run([wmctrl, "-m"], text=True,
                             stdout=subprocess.PIPE,
                             stderr =subprocess.PIPE)
        
        if len(out.stdout) == 0:
            print(out.stderr)
            return
        
        wmname = [s for s in out.stdout.split("\n") if s.startswith("Name: ")]
        
        if len(wmname):
            return wmname[0].strip("Name: ")
        
    else:
        inxi = shutil.which("inxi")
        if len(inxi):
            inxi = os.path.basename(inxi)
            out = subprocess.run([inxi, "-Sxx", "-y", "1", "--indents", "0"],
                                 text=True,
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE)
            
            if len(out.stdout) == 0:
                print(out.stderr)
                return
            
            inxiout = dict(filter(lambda x: len(x) == 2, (tuple(s.split(": ")) for s in out.stdout.split("\n"))))
            
            if len(inxiout) == 0:
                return
            
            desktop = inxiout.get("Desktop", None)
            tk = inxiout.get("tk", None)
            wm = inxiout.get("wm", None)
            
            return wm
            

def get_desktop(what:str="desktop"):
    """Somewhat redundant to get_wm()
    """
    if sys.platform.startswith("linux"):
        if what == "wm":
            return os.environ.get("WINDOWMANAGER", None)
        
        elif what == "session":
            return os.environ.get("XDG_SESSION_TYPE", None)
        
        else:
            return os.environ.get("XDG_CURRENT_DESKTOP", None)
                
    else:
        return sys.platform

def get_dbus_service_names(what:str="session"):
    """
    what: one of "session", "system"
    """
    if platform.system() != "Linux":
        return
    
    if not isinstance(what, str):
        raise TypeError(f"Expecting a str; instead, got {type(what).__name__}")
    
    if what == "system":
        busConnection = QtDBus.QDBusConnection.systemBus()
    else:
        busConnection = QtDBus.QDBusConnection.sessionBus()
        
    return busConnection.interface().registeredServiceNames().value()
    
def is_kde_x11():
    if platform.system() != "Linux":
        return False
    
    return get_desktop("session") == "x11" and get_desktop() == "KDE"

def adapt_ui_path(module_path, uifile):
    # NOTE: CAUTION: 2023-07-14 18:10:01
    # make sure this is in sync with the destination for uitoc in scipyen.spec file
    # if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    uifull = os.path.join(module_path, uifile)
    if os.path.isfile(uifull):
        return uifull
    
    module_place = os.path.dirname(module_path)
    # print(f"adapt_ui_path module_place {module_place}")
    return os.path.join(module_place, "UI", module_path, uifile)

#     if hasattr(sys, "_MEIPASS"):
#         return os.path.join(module_place, "UI", module_path)
#     
#     return module_path
