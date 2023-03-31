import _winreg as reg
import win32gui
import win32con


# read the value
key = reg.OpenKey(reg.HKEY_CURRENT_USER, 'Environment', 0, reg.KEY_ALL_ACCESS)
# use this if you need to modify the system variable and if you have admin privileges
#key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 0, reg.KEY_ALL_ACCESS)
try
    value, _ = reg.QueryValueEx(key, 'PATH')
except WindowsError:
    # in case the PATH variable is undefined
    value = ''

# modify it
value = ';'.join([s for s in value.split(';') if not r'\myprogram' in s])

# write it back
reg.SetValueEx(key, 'PATH', 0, reg.REG_EXPAND_SZ, value)
reg.CloseKey(key)

# notify the system about the changes
win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')

