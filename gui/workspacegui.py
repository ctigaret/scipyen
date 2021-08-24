# -*- coding: utf-8 -*-
import typing, warnings, os, inspect
from pprint import pprint
#### BEGIN Configurable objects with traitlets.config
from traitlets import config
#### END Configurable objects with traitlets.config
import matplotlib as mpl
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
#from traitlets.config import SingletonConfigurable
from core.utilities import safeWrapper
from core.workspacefunctions import user_workspace
from gui.pictgui import ItemsListDialog

#class ConfigurableQMainWindowMeta(type(config.Configurable), type(QtWidgets.QMainWindow)):
    #def __init__(self, config=None, parent=None, *args, **kwargs):
        #config.Configurable.__init__(self, config=config)
        #QtWidgets.QMainWindow.__init__(self, parent=parent)

class GuiMessages(object):
    @safeWrapper
    def errorMessage(self, title, text):
        errMsgDlg = QtWidgets.QErrorMessage(self)
        errMsgDlg.setWindowTitle(title)
        errMsgDlg.showMessage(text)
        
    @safeWrapper
    def criticalMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.critical(self, title, text)
        
    @safeWrapper
    def informationMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.information(self, title, text)
        
    @safeWrapper
    def questionMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.question(self, title, text)
        
    @safeWrapper
    def warningMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.warning(self, title, text)
        
    @safeWrapper
    def detailedMessage(self, title, text, detail="", msgType="Critical"):
        if not hasattr(QtWidgets.QMessageBox.Icon, msgType):
            raise ValueError("Invalid msgType %s. Expecting one of %s" % (msgType, ("NoIcon", "Question", "Information", "Warning", "Critical")))
        
        msgbox = QtWidgets.QMessageBox()
        msgbox.setSizeGripEnabled(True)
        msgbox.setIcon(getattr(QtWidgets.QMessageBox.Icon, msgType))
        msgbox.setWindowTitle(title)
        msgbox.setText(text)
        if isinstance(detail, str) and len(detail):
            msgbox.setDetailedText(detail)
            
        msgbox.exec()
        
class FileIOGui(object):
    @safeWrapper
    def chooseFile(self, caption:typing.Optional[str]=None, fileFilter:typing.Optional[str]=None, 
                   single:typing.Optional[bool]=True,
                   targetDir:typing.Optional[str]=None) -> typing.Tuple[typing.Union[str, typing.List[str]], str]:
        """Launcher of file open dialog
        
        Parameters:
        ----------
        caption: str, optional default is None - The caption of the file chooser dialog
        fileFilter: str, optional, default is None - The file filter for choosing
            from a specific subset of tile types. When present, it must have a 
            specific format, e.g. "Pickle Files (*.pkl);;Text Files (*.txt)"
            
        single:bool, optional (default: True)
           When False, the file chooser dialog will allow opening several files
           
        targetDir:str, optional (default is None) Target directory from where 
            files are chosen.
            
            When None, an empty string or a string that does NOT resolve to a
            directory, target 
            
        Returns:
        -------
        fn: str or list of str The selected file name (or file names, if "single"
            is False)
            
        fl: str The string containing the selected file filter (defaults to
            "All files (*.*)")
        
        """
        from functools import partial
        
        if targetDir is None:
            targetDir = os.getcwd()
            
        if isinstance(targetDir, str):
            if len(targetDir.strip()) == 0 or not os.path.isdir(targetDir):
                targetDir = os.getcwd()
                
        opener = QtWidgets.QFileDialog.getOpenFileName if single else QtWidgets.QFileDialog.getOpenFileNames
        
        if isinstance(caption, str) and len(caption.strip()):
            opener = partial(opener, caption=caption)
            
        if isinstance(fileFilter, str) and len(fileFilter.strip()):
            opener = partial(opener, filter=fileFilter)
        
        fn, fl = opener(parent=self, directory=targetDir)
        
        return fn, fl
    
    @safeWrapper
    def chooseDirectory(self, caption:typing.Optional[str]=None,
                        targetDir:typing.Optional[str]=None) -> str:
        
        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=caption, directory=targetDir))
        else:
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=caption))
            
        return dirName

class WorkspaceGuiMixin(GuiMessages, FileIOGui):
    """Mixin type for windows that need to be aware of Scipyen's main workspace.
    
    Also provides:
    1) common functionality needed in Scipyen's windows. 
    2) a custom ID useful when the window is a child of a Scipyen "app" (e.g.,
     LSCaT) instead of beign top level
    """
    # NOTE: 2021-08-23 10:39:20 inherits from object !!!
    
    def __init__(self, parent: (QtWidgets.QMainWindow, type(None)) = None,
                 title="", **kwargs):
        self._scipyenWindow_ = None
        
        # NOTE: 2020-12-05 21:12:43:
        # user_workspace(does NOT work here unless this is called by a 
        # constructor executed in the Scipyen console (so that the user workspace
        # is contained in the outermost frame))
        #ws = user_workspace()
        #print(ws)
        
        if isinstance(parent, QtWidgets.QMainWindow) and type(parent).__name__ == "ScipyenWindow":
            self._scipyenWindow_   = parent
            
        else:
            # NOTE: 2020-12-05 21:24:45
            # this successfully returns the user workspace ONLY when the 
            # constructor is invoked (directly or indirectly) from within
            # the console; otherwise, it is None
            ws = user_workspace()
            
            if ws is not None:
                self._scipyenWindow_ = ws["mainWindow"]
                
            else:
                frame_records = inspect.getouterframes(inspect.currentframe())
                for (n,f) in enumerate(frame_records):
                    if "ScipyenWindow" in f[0].f_globals:
                        self._scipyenWindow_ = f[0].f_globals["ScipyenWindow"].instance()
                        break
                
        if isinstance(title, str) and len(title.strip()):
            self.setWindowTitle(title)
            
    @property
    def isTopLevel(self):
        """Returns True when this window is a top level window in Scipyen.
        In Scipyen, a window is "top level" when its instance is not a member of
        a Scipyen "application" (e.g. LSCaT).
        
        For example, any viewer created upon double-clicking on a variable in
        the workspace viewer ("User Variables") is a top-level window.
        
        In contrast, viewers created from within a Scipyen "application" are
        members of the application and thus are not "top level".
        
        A Scipyen "application" is any facility that runs its own GUI inside
        Scipyen (e.g., LSCaT) - this is NOT a stand-alone PyQt5 application with
        which Scipyen communicates.
        
        """
        return self.appWindow is self.parent()
                
    @property
    def appWindow(self):
        """The application main window.
        This is a reference to the  Scipyen main window, unless explicitly given
        as something else at the viewer's initiation.
        
        appWindow gives access to Scipyen main window API (e.g. the workspace).
        """
        return self._scipyenWindow_
    
    @safeWrapper
    def importWorkspaceData(self, dataTypes:typing.Union[typing.Type[typing.Any], typing.Sequence[typing.Type[typing.Any]]],
                            title:str="Import from workspace",
                            single:bool=True) -> list:
        """Launches ItemsListDialog to import on or several workspace variables.
        
        Parameters:
        -----------
        dataTypes: type, or sequence of types
        """
        from core.workspacefunctions import getvarsbytype
        #print("dataTypes", dataTypes)
        
        user_ns_visible = dict([(k,v) for k,v in self._scipyenWindow_.workspace.items() if k not in self._scipyenWindow_.workspaceModel.user_ns_hidden])
        
        name_vars = getvarsbytype(dataTypes, ws = user_ns_visible)
        
        if len(name_vars) == 0:
            return list()
        
        name_list = sorted([name for name in name_vars])
        
        #selectionMode = QtWidgets.QAbstractItemView.SingleSelection if single else QtWidgets.QAbstractItemView.MultiSelection
        selectionMode = QtWidgets.QAbstractItemView.SingleSelection if single else QtWidgets.QAbstractItemView.ExtendedSelection
        
        dialog = ItemsListDialog(parent=self, title=title, itemsList = name_list,
                                 selectmode = selectionMode)
        
        ans = dialog.exec()
        
        if ans == QtWidgets.QDialog.Accepted:
            return [self._scipyenWindow_.workspace[i] for i in dialog.selectedItemsText]
            
        return list()
            
        
def saveWindowSettings(qsettings:QtCore.QSettings, 
                       win:typing.Union[QtWidgets.QMainWindow, mpl.figure.Figure], 
                       group_name:typing.Optional[str]=None,
                       prefix:typing.Optional[str]=None, 
                       **kwargs) -> typing.Tuple[str, str]:
    """Saves window settings to the Scipyen's Qt configuration file.
    
    On recent Linux distributions this is $HOME/.config/Scipyen/Scipyen.conf 
    
    The following mandatory settings will be saved:
    
    * For all QWidget-derived objects:
        * WindowSize
        * WindowPosition
        * WindowGeometry
        
    * Only for QMainWindow-derived objects, or objects that have a 'saveState()'
        method returning a QByteArray:
        * WindowState 
        
    Additional (custom) entries and values can be saved when passed as a mapping.
    
    Settings are always saved in groups inside the Scipyen.conf file. The group's
    name is determined automatically, or it can be specified.
    
    Because the conf file only supports one level of group nesting (i.e. no 
    "sub-groups") an extra-nesting level is emulated by prepending a custom
    prefix to the setting's name.
    
    Parameters:
    ==========
    
    qsettings: QtCore.QSettings. Typically, Scipyen's global QSettings.
    
    win: QMainWindow or matplotlib Figure. The window for which the settings are
        saved.
    
    group_name:str, optional, default is None. The qsettings group name under 
        which the settings will be saved.
        
        When specified, this will override the automatically determined group 
        name (see below).
    
        When group_name is None, the group name is determined from win's type 
        as follows:
        
        * When win is a matplotlib Figure instance, group name is set to the 
            class name of the Figure's canvas 
            
        * When win is an instance of a QMainWindow (this includes Scipyen's main
            window, all Scipyen viewer windows, and ExternalConsoleWindow):
            
            * for instances of WorkspaceGuiMixin:
                * if win is top level, or win.parent() is None:
                    group name is the name of the win's class
                    
                * otherwise:
                    group name is set to the class name of win.parent(); 
                    prefix is set to the win's class class name in order to
                    specify the settings entries
            
            * otherwise, the win is considered top level and the group name is
            set to the win's class name
            
        For any other window types, the group name is set to the window's class 
        name (for now, this is only the case for ScipyenConsole which inherits 
        from QWidget, and not from QMainWindow).
        
    prefix: str (optional, default is None)
        When given, it will be prepended to the settings entry name. This is 
        useful to distinguish between several windows of the same type which are
        children of the same parent, yet need distinct settings.
        
    **kwargs: A mapping of key(str) : value(typing.Any) for additional entries
        beyond the mandatory ones.
    
    Returns:
    ========
    
    A tuple: (group_name, prefix) 
        group_name is the qsettings group name under which the win's settings 
            were saved
            
        prefix is th prefix prepended to each setting name
        
        These are useful to append settings later
    
    """
    # NOTE: 2021-07-11 18:32:56
    # QSettings support maximum one nesting level (i.e., group/entry)
    pfx = ""
    
    if isinstance(win, QtWidgets.QMainWindow):
        if isinstance(win, WorkspaceGuiMixin):
            if win.parent() is None or win.isTopLevel:
                gname = win.__class__.__name__
            else:
                gname = win.parent().__class__.__name__
                pfx = win.__class__.__name__
        else:
            if win.parent() is None or "ScipyenWindow" in win.parent().__class__.__name__:
                gname = win.__class__.__name__
            else:
                gname = win.parent().__class__.__name__
                pfx = win.__class__.__name__
                
    elif isinstance(win, mpl.figure.Figure):
        gname = win.canvas.__class__.__name__
                
    else:
        gname = win.__class__.__name__
                
    if isinstance(group_name, str) and len(group_name.strip()):
        # NOTE: 2021-08-24 15:04:31 override internally determined group name
        gname = group_name
        
    if isinstance(prefix, str) and len(prefix.strip()):
        # NOTE: 2021-08-24 15:04:31 override internally determined group name
        pfx = prefix
        
    if isinstance(pfx, str) and len(pfx.strip()):
        ename = "%s_" % pfx
    else:
        ename=""
        
    #print("\nworkspacegui.saveWindowSettings viewer %s BEGIN" % win.__class__)
    #print("\tgroup name", gname)
    #print("\tpfx", pfx)
    #print("\tename", ename)
    
    settings = dict()
    
    settings["%sWindowSize" % ename] = win.size()
    settings["%sWindowPosition" % ename] = win.pos()
    settings["%sWindowGeometry" % ename] = win.geometry()
    
    if hasattr(win, "saveState"):
        settings["%sWindowState" % ename] = win.saveState()
        
    custom_settings = dict((("%s%s" % (ename,k), v) for k,v in kwargs.items() if isinstance(k, str) and len(k.strip())))

    settings.update(custom_settings)
    
    #print("settings to save")
    #pprint(settings)
    
    qsettings.beginGroup(gname)
    
    for k,v in settings.items():
        qsettings.setValue(k, v)
    
    qsettings.endGroup()
        
    #print("workspacegui.saveWindowSettings viewer %s, END" % win.__class__)
    #if use_group:
        #qsettings.endGroup()
        
    return gname, pfx
    
def loadWindowSettings(qsettings:QtCore.QSettings, 
                       win:typing.Union[QtWidgets.QMainWindow, mpl.figure.Figure], 
                       group_name:typing.Optional[str]=None,
                       prefix:typing.Optional[str]=None, 
                       custom:typing.Optional[dict]=None) -> typing.Tuple[str, str]:
    """Loads window settings from the Scipyen's Qt configuration file.
    
    On recent Linux distributions this is $HOME/.config/Scipyen/Scipyen.conf 
    
    The following mandatory settings will be loaded:
    
    * For all QWidget-derived objects:
        * WindowSize
        * WindowPosition
        * WindowGeometry
        
    * Only for QMainWindow-derived objects, or objects that have a 'saveState()'
        method returning a QByteArray:
        * WindowState 
        
    Additional (custom) entries and values can be loaded when passed as a mapping.
    
    Settings are always saved in groups inside the Scipyen.conf file. The group's
    name is determined automatically, or it can be specified.
    
    Because the conf file only supports one level of group nesting (i.e. no 
    "sub-groups") an extra-nesting level, when needed, is emulated by prepending
    a custom prefix to the setting's name.
    
    Parameters:
    ==========
    
    qsettings: QtCore.QSettings. Typically, Scipyen's global QSettings.
    
    win: QMainWindow or matplotlib Figure. The window for which the settings are
        loaded.
    
    group_name:str, optional, default is None. The qsettings group name under 
        which the settings will be saved.
        
        When specified, this will override the automatically determined group 
        name (see below).
    
        When group_name is None, the group name is determined from win's type 
        as follows:
        
        * When win is a matplotlib Figure instance, group name is set to the 
            class name of the Figure's canvas 
            
        * When win is an instance of a QMainWindow (this includes Scipyen's main
            window, all Scipyen viewer windows, and ExternalConsoleWindow):
            
            * for instances of WorkspaceGuiMixin:
                * if win is top level, or win.parent() is None:
                    group name is the name of the win's class
                    
                * otherwise:
                    group name is set to the class name of win.parent(); 
                    prefix is set to the win's class class name in order to
                    specify the settings entries
            
            * otherwise, the win is considered top level and the group name is
            set to the win's class name
            
        For any other window types, the group name is set to the window's class 
        name (for now, this is only the case for ScipyenConsole which inherits 
        from QWidget, and not from QMainWindow).
        
    prefix: str (optional, default is None)
        When given, it will be prepended to the settings entry name. This is 
        useful to distinguish between several windows of the same type which are
        children of the same parent, yet need distinct settings.
        
    custom: A key(str) : value(typing.Any) mapping for additional entries.
    
        The values in the mapping are default values used when their keys are 
        not found in qsettings.
        
        If found, their values will be mapped to the corresponding key in 'custom'
        
        Since 'custom' is passed by reference, the new settings values can be 
        accessed directly from there, in the caller namespace.
        
    Returns:
    ========
    
    A tuple: (group_name, prefix) 
        group_name is the qsettings group name under which the win's settings 
            were saved
            
        prefix is th prefix prepended to each setting name
        
        These are useful to append settings later
    
    """
    pfx = ""
    if isinstance(win, QtWidgets.QMainWindow):
        if isinstance(win, WorkspaceGuiMixin):
            if win.parent() is None or win.isTopLevel:
                gname = win.__class__.__name__
            else:
                gname = win.parent().__class__.__name__
                pfx = win.__class__.__name__
        else:
            if win.parent() is None or "ScipyenWindow" in win.parent().__class__.__name__:
                gname = win.__class__.__name__
            else:
                gname = win.parent().__class__.__name__
                pfx = win.__class__.__name__
                
    elif isinstance(win, mpl.figure.Figure):
        gname = win.canvas.__class__.__name__
        
    else:
        gname = win.__class__.__name__
                
    if isinstance(group_name, str) and len(group_name.strip()):
        # NOTE: 2021-08-24 15:04:31 override internally determined group name
        gname = group_name
        
    if isinstance(prefix, str) and len(prefix.strip()):
        # NOTE: 2021-08-24 15:04:31 override internally determined group name
        pfx = prefix
        
    if isinstance(pfx, str) and len(pfx.strip()):
        ename = "%s_" % pfx
    else:
        ename=""
        
    #print("\nworkspacegui.loadWindowSettings viewer %s BEGIN" % win.__class__)
    #print("\tgroup name", gname)
    #print("\tpfx", pfx)
    #print("\tename", ename)
    
    settings = dict()
    
    settings["%sWindowSize" % ename] = win.size()
    settings["%sWindowPosition" % ename] = win.pos()
    settings["%sWindowGeometry" % ename] = win.geometry()
    
    if hasattr(win, "saveState"):
        settings["%sWindowState" % ename] = win.saveState()
        
    if isinstance(custom, dict):
        custom_settings = dict((("%s%s" % (ename,k), v) for k,v in custom.items() if isinstance(k, str) and len(k.strip()) ))

        settings.update(custom_settings)
    
    #print("settings to load:")
    #pprint(settings)
    
    qsettings.beginGroup(gname)
    
    for k,v in settings.items():
        settings[k] = qsettings.value(k, v)
        
    qsettings.endGroup()
    
    #print("loaded settings")
    #pprint(settings)
    
    #windowSize = qsettings.value("%sWindowSize" % ename, None)
    windowSize = settings.get("%sWindowSize" % ename, None)
    if windowSize:
        win.resize(windowSize)
        
    #windowPos = qsettings.value("%sWindowPosition" % ename, None)
    windowPos = settings.get("%sWindowPosition" % ename, None)
    if windowPos:
        win.move(windowPos)
    
    #windowGeometry = qsettings.value("%sWindowGeometry" % ename, None)
    windowGeometry = settings.get("%sWindowGeometry" % ename, None)
    if windowGeometry:
        win.setGeometry(windowGeometry)
        
    if hasattr(win, "restoreState"):
        #windowState = qsettings.value("%sWindowState" % ename, None)
        windowState = settings.get("%sWindowState" % ename, None)
        if windowState:
            win.restoreState(windowState)
            
    #print("workspacegui.loadWindowSettings viewer %s END" % win.__class__)
    
    return gname, pfx
