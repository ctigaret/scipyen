import ctypes
from ctypes.wintypes import HWND, UINT, WPARAM, LPARAM, LPVOID
LRESULT = LPARAM  # synonymous
import os
import sys
try:
    import winreg
    unicode = str
except ImportError:
    import _winreg as winreg  # Python 2.x

class Environment(object):
    path = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
    hklm = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    key = winreg.OpenKey(hklm, path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    SendMessage = ctypes.windll.user32.SendMessageW
    SendMessage.argtypes = HWND, UINT, WPARAM, LPVOID
    SendMessage.restype = LRESULT
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x1A
    NO_DEFAULT_PROVIDED = object()

    def get(self, name, default=NO_DEFAULT_PROVIDED):
        try:
            value = winreg.QueryValueEx(self.key, name)[0]
        except WindowsError:
            if default is self.NO_DEFAULT_PROVIDED:
                raise ValueError("No such registry key", name)
            value = default
        return value

    def set(self, name, value):
        if value:
            winreg.SetValueEx(self.key, name, 0, winreg.REG_EXPAND_SZ, value)
        else:
            winreg.DeleteValue(self.key, name)
        self.notify()

    def notify(self):
        self.SendMessage(self.HWND_BROADCAST, self.WM_SETTINGCHANGE, 0, u'Environment')

Environment = Environment()  # singletion - create instance

PATH_VAR = 'PATH'

def append_path_envvar(addpath):
    def canonical(path):
        path = unicode(path.upper().rstrip(os.sep))
        return winreg.ExpandEnvironmentStrings(path)  # Requires Python 2.6+
    canpath = canonical(addpath)
    curpath = Environment.get(PATH_VAR, '')
    if not any(canpath == subpath
                for subpath in canonical(curpath).split(os.pathsep)):
        Environment.set(PATH_VAR, os.pathsep.join((curpath, addpath)))

def remove_envvar_path(folder):
    """ Remove *all* paths in PATH_VAR that contain the folder path. """
    curpath = Environment.get(PATH_VAR, '')
    folder = folder.upper()
    keepers = [subpath for subpath in curpath.split(os.pathsep)
                if folder not in subpath.upper()]
    Environment.set(PATH_VAR, os.pathsep.join(keepers))

