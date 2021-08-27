# -*- coding: utf-8 -*-
import typing, warnings, os, inspect
from pprint import pprint
#### BEGIN Configurable objects with traitlets.config
from traitlets import (config, Bunch)
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
    # NOTE: 2021-08-26 11:32:25
    # key:str = QSettings key
    # value: 
    #   EITHER: tuple (str, str) = getter method name, setter method name
    #           where:
    #               getter method name: name of instance or class method that
    #                                   returns a Python object (CAUTION: when
    #                                   the method returns SEVERAL obejcts they
    #                                   will be captured in a tuple!)
    #               setter method name: name of the instance or class method that
    #                                   accepts ONE Python object as parameter
    #                                   which corresponds to the return value of
    #                                   the getter method
    #
    #   OR:     tuple (str, ) = property
    #           where: property is the name of a descriptor with read-write access
    #
    #
    #
    _qtcfg = Bunch({"WindowSize":       ("size",        "resize"),
                    "WindowPosition":   ("pos",         "move"),
                    "WindowGeometry":   ("geometry",    "setGeometry"),
                    "WindowState":      ("saveState",   "restoreState")})
    
    _ownqtcfg = Bunch()
    
    _cfg = Bunch()
    
    _owncfg = Bunch()
    
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
            
        self._qtconfigurables = Bunch()
        self._configurables = Bunch()
        
    @property
    def qtconfigurables(self):
        """A str -> type mapping of configurable properties for QSettings.
        
        The keys of the mapping (str) are attributes or descriptors with read &
        write access, defined in the viewer class. 
        
        WARNING: use carefully, as this may overwrite class or instance members
        
        The values are expected to be built-in Python types, EXCLUDING:
        - context managers
        - modules
        - classes
        - functions and methods
        - code objects
        - type objects
        - Ellipsis
        - NotImplemented
        - stack frame objects
        - traceback objects
        
        NOTE: No type checking is performed.
        
        Support for one level of nested mappings:
        When the key is not an attribute/descriptor of the viewer but the
        mapped value is a (nested) mapping type where all keys are str AND 
        represent a descriptor or attribute of the viewer, then the nested mapping
        is used to read-write the decsriptor or attribute of the viewer, with the
        'parent' key being used as 'prefix'.
        
        This mechanism ensures a 'pseudo-grouping' of configurables inside the
        Scipyen.conf file used by QSettings.
        
        """
        # TODO 2021-08-25 16:47:16
        # if using traitlets.config framework then make functions to write atomic
        # qsettings keyts to the conf file, as the configurble is changed
        return self._qtconfigurables
    
    @property
    def configurables(self):
        return self._configurables

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
                       prefix:typing.Optional[str]=None) -> typing.Tuple[str, str]:
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
    return syncWindowSettings(qsettings, win, group_name, prefix, True)
    
def syncWindowSettings(qsettings:QtCore.QSettings, 
                       win:typing.Union[QtWidgets.QMainWindow, mpl.figure.Figure], 
                       group_name:typing.Optional[str]=None,
                       prefix:typing.Optional[str]=None,
                       save:bool=True)-> typing.Tuple[str, str]:
    """Synchronize user-specifc settings with the Scipyen's Qt configuration file.
    
    The Scipyen's configuration file is in native format, and on Linux it usually
    is $HOME/.config/Scipyen/Scipyen.conf. For details, please see QSettings 
    class documentation in Qt Assistant, or at:
    https://doc.qt.io/qt-5/qsettings.html
    
    The direction of synchronization is determined by the :bool: value of the 
    'save' parameter: when True, the settings are save to the file; otherwise,
    they are loaded.
    
    The general idea is that the QSettings conf file only supports one level of
    grouping for qsetting key/value entries. Subgroups can be emulated with
    distinct prefixes to the qsettings key.
    
    What exactly is synchronized is specified in the class attributes '_qtcfg'
    and '_ownqtcfg' of win.
    
    All window classes in Scipyen that inherit from gui.workspacegui.WorkspaceGuiMixin
    have at least the '_qtcfg' attribute.
    
    _qtcfg is a mapping of QSettings key names to a tuple of str containing:
    * either a single element - corresponding to an instance property with read/write access
    * or two elements corresponding to the getter and setter method (in this order)
        for the particular setting
        
    By default, '_qtcfg' is:
    
    {'WindowSize':      ('size',        'resize'),
     'WindowPosition':  ('pos',         'move'),
     'WindowGeometry':  ('geometry',    'setGeometry'),
     'WindowState':     ('saveState',   'restoreState')
     }
     
    In subclasses of WorkspaceGuiMixin '_qtcfg' should be augmented by a similar
    mapping in '_ownqtcfg'
    
    E.g., for SignalViewer, the '_ownqtcfg' is 
    
    {'VisibleDocks': ('visibleDocks',)}
    
    where 'visibleDocks' is a dynamic property that retrieves a dict 
    {dock_name1: visible bool, dock_name2: visible bool, <etc...>} and its 
    setter expects the same.
    
    The '_qtcfg'-based mechanism ensures that the following keys are always
    synchronized whenever the win's class provides 'getter' and 'setter' methods
    for access:
    
    QSettings key     Getter method                   Setter method
    ------------------------------------------------------------------------------
    Window size       win.size()      -> QSize        win.resisze(QSize)
    Window position   win.pos()       -> QPoint       win.move(QPoint)
    Window geometry   win.geometry()  -> QRect        win.setGeometry(QRect)
    Window state      win.saveState() -> QByteArray   win.restoreState(QByteArray)
    
    Of these, the first three are available for all objects derived from QWidget
    (including RichJupyterWidget,such as Cipyen's console); the window state is 
    only available for objects derived from QMainWindow.
    
    This mechanism can be bypassed in order to save/load QSettings keys directly
    using the QSettings API, or, for a more consistent group and key nomenclature, 
    via qSettingsGroupPfx(), followed by saveQSettingsKey() or loadQsettingsKey()
    functions in this module.
    
    Settings are always saved in groups inside the Scipyen.conf file. The group's
    name is determined automatically, or it can be specified.
    
    Because the conf file only supports one level of group nesting (i.e. no 
    "sub-groups") an optional extra-nesting level is emulated by prepending
    a custom prefix to the setting's name (or key).
    
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
    
    gname, pfx = qSettingsGroupPfx(win)
    
    if isinstance(group_name, str) and len(group_name.strip()):
        # NOTE: 2021-08-24 15:04:31 override internally determined group name
        gname = group_name
        
    if isinstance(prefix, str) and len(prefix.strip()):
        # NOTE: 2021-08-24 15:04:31 override internally determined group name
        pfx = prefix
        
    if isinstance(pfx, str) and len(pfx.strip()):
        key_prefix = "%s_" % pfx
    else:
        key_prefix=""
        
    settings = dict()
    
    qtcfg = dict()
    qtcfg.update(getattr(type(win), "_qtcfg", {}))
    qtcfg.update(getattr(type(win), "_ownqtcfg", {}))
    
    print("syncWindowSettings %s: save %s, qtcfg =" % (type(win), save), qtcfg)
    
    for key, getset in qtcfg.items():
        val = getattr(win, getset[0], None)
        if len(getset) == 1:
            if save:
                if val is not None:
                    saveQSettingsKey(qsettings, gname, key_prefix, key, val)
            else:
                newval = loadQSettingsKey(qsettings, gname, key_prefix, key, val)
                setattr(win, getset[0], newval)
            
        elif len(getset) == 2:
            if save:
                if val is not None:
                    saveQSettingsKey(qsettings, gname, key_prefix, key, val())
            else:
                setter = getattr(win, getset[1])
                default = val()
                newval = loadQSettingsKey(qsettings, gname, key_prefix, key, val)
                setter(newval)
            
    return gname, pfx
    
def loadWindowSettings(qsettings:QtCore.QSettings, 
                       win:typing.Union[QtWidgets.QMainWindow, mpl.figure.Figure], 
                       group_name:typing.Optional[str]=None,
                       prefix:typing.Optional[str]=None) -> typing.Tuple[str, str]:
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
    return syncWindowSettings(qsettings, win, group_name, prefix, False)

def qSettingsGroupPfx(win:typing.Union[QtWidgets.QMainWindow, QtWidgets.QWidget, mpl.figure.Figure]) -> typing.Tuple[str, str]:
    """Generates a QSettings group name and, optionally, a prefix.
    
    Parameters:
    ===========
    win: QMainWindow, QWidget, or matplotlib Figure
    
    Returns:
    =======
    
    A tuple of str (group_name, prefix), where:
    
        * group_name is the name of the settings group in the QSettings .conf 
            file (on Linux this is $HOME/.config/Scipyen/Scipyen.conf)
    
        * prefix is to be prepended to the QSettings key name (pseudo-subgroups)
         and may be the empty string.
        
    For Scipyen's top-level instances of QMainWindow (see NOTE 1):
        * 'group_name' is the name of the viewer's class
        * 'prefix' is the empty string.
        
    For Scipyen's viewers that are not 'top-level':
        * 'group_name' is the name of the viewer's parent class
        * 'prefix' is composed of the name of the viewer's class and a persistent
            tag string that differentiates the specific win instance from other
            instances of the same class as win.
            
    This ensures that the QSettings are consistent among all the instances 
    of the viewer. For example, if there are several ImageViewer instances,
    the window geometry, colormap and other GUI-related settings are those
    of the last ImageViewer window being closed.
    
    Since there can be any number of ImageViewer windows open during a Scipyen
    session, managing the settings for each individual instance is not only 
    difficult, but does not make sense.
        
    For QMainWindow instances that are managed by a Scipyen top-level window it
    is assumed that there is a maximum number of such instances, and managing 
    their settings individually not only is possible but it may also make more 
    sense.
    
    The typical example is that of LSCaT where the main GUI window is a 
    'top-level' Scipyen viewer and manages a fixed number of ImageViewer windows
    (up to the number of image channels). The settings for these individual
    ImageViewer windows need to be persistent across sessions and managed
    individually (e.g., a given channel should always be viewed in the same 
    colormap, etc).
    
    NOTE 1: A 'top-level' window is any Scipyen viewer that operates directly in 
            Scipyen's workspace and is managed by Scipyen's main window.
            
            These include Scipyen's main window (ScipyenWindow), the console
            classes (ScipyenConsole, ExternalConsole, and ExternalConsoleWindow)
            and all matplotlib figures managed by matplotlib.pyplot
            
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
        
    return gname, pfx
                
    

def saveQSettingsKey(qsettings:QtCore.QSettings, 
                    gname:str, pfx:str, key:str, val:typing.Any) -> None:
    if len(gname.strip()) == 0:
        gname = "General"
    key_name = "%s%s" % (pfx, key)
    qsettings.beginGroup(gname)
    qsettings.setValue(key_name, val)
    qsettings.endGroup()
    
def loadQSettingsKey(qsettings:QtCore.QSettings,
                     gname:str, pfx:str, key:str, default:typing.Any) -> typing.Any:
    if len(gname.strip()) == 0:
        gname = "General"
    key_name = "%s%s" % (pfx, key)
    qsettings.beginGroup(gname)
    ret = qsettings.value(key_name, default)
    qsettings.endGroup()
    return ret
    
    
