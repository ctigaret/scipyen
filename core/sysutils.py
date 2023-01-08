"""System and platform utilities
"""
import os, sys, subprocess

from PyQt5 import (QtCore, QtWidgets, QtGui, QtDBus)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)

def which(execname:str):
    if sys.platform.startswith("linux"):
        out = subprocess.run(["which", execname], text=True,
                             stdout=subprocess.PIPE,
                             stderr =subprocess.PIPE)
        
        if len(out.stdout):
            return out.stdout.strip("\n")
        
        else:
            print(out.stderr)

def get_wm():
    """Retrieves the name of the window manager, on Linux platforms.
    On any other platforms returns None.

    """
    # NOTE: 2023-01-07 16:08:36
    # From
    # https://stackoverflow.com/questions/3333243/how-can-i-check-with-python-which-window-manager-is-running
    if not sys.platform.startswith("linux"):
        return
    
    wmtester = None
    
    wmctrl = which("wmctrl")
    
    if len(wmctrl):
        wmctrl = os.path.basename(wmctrl)
        
        out = subprocess.run([wmctrl, "-m"], text=True,
                             stdout=subprocess.PIPE,
                             stderr =subprocess.PIPE)
        
        if len(out.stdout) == 0:
            print(out.stderr)
            return
        
        wmname = [s for s in out.stdout.split("\n") if s.startswith("Name: ")]
        
        if len(wname):
            return wname[0].strip("Name: ")
        
    else:
        inxi = which("inxi")
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
            

def get_desktop(what:str="wm"):
    if sys.platform.startswith("linux"):
        if what == "desktop":
            return os.environ.get("XDG_CURRENT_DESKTOP", None)
        
        elif what == "session":
            return os.environ.get("XDG_SESSION_TYPE", None)
        
        else:
            return os.environ.get("WINDOWMANAGER", None)
                
    else:
        return sys.platform

def get_dbus_service_names(what:str="session"):
    """
    what: one of "session", "system"
    """
    if not isinstance(what, str):
        raise TypeError(f"Expecting a str; instead, got {type(what).__name__}")
    
    if what == "system":
        busConnection = QtDBus.QDBusConnection.systemBus()
    else:
        busConnection = QtDBus.QDBusConnection.sessionBus()
        
    return busConnection.interface().registeredServiceNames().value()
    
