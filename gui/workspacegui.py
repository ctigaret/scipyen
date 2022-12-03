# -*- coding: utf-8 -*-
import typing, warnings, os, inspect, sys, traceback
from pprint import pprint
#### BEGIN Configurable objects with traitlets.config
from traitlets import (config, Bunch)
#### END Configurable objects with traitlets.config
import matplotlib as mpl
from PyQt5 import (QtCore, QtWidgets, QtGui)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty)
#from traitlets.config import SingletonConfigurable
from core.utilities import safeWrapper
from core.workspacefunctions import (user_workspace, validate_varname,get_symbol_in_namespace)
from core.scipyen_config import (ScipyenConfigurable, 
                                 syncQtSettings, 
                                 markConfigurable, 
                                 loadWindowSettings,
                                 saveWindowSettings,
                                 confuse)
from core import strutils
from core.strutils import InflectEngine
import gui.quickdialog as qd
from gui.itemslistdialog import ItemsListDialog

#ScipyenConfigurable = ScipyenConfigurable2 # NOTE remove before release

class GuiMessages(object):
    @safeWrapper
    def errorMessage(self, title, text):
        errMsgDlg = QtWidgets.QErrorMessage(self)
        errMsgDlg.setWindowTitle(title)
        errMsgDlg.showMessage(text)
        
    @safeWrapper
    def criticalMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        return QtWidgets.QMessageBox.critical(self, title, text)
        
    @safeWrapper
    def informationMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        return QtWidgets.QMessageBox.information(self, title, text)
        
    @safeWrapper
    def questionMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        return QtWidgets.QMessageBox.question(self, title, text)
        
    @safeWrapper
    def warningMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        return QtWidgets.QMessageBox.warning(self, title, text)
        
    @safeWrapper
    def detailedMessage(self, title:str, text:str, info:typing.Optional[str]="", detail:typing.Optional[str]="", msgType:typing.Optional[typing.Union[str, QtGui.QPixmap]]="Critical"):
        """Detailed generic message dialog box
        title: str  = dialog title
        text:str =  main message
        info:str (optional, default is None) informative text
        detail:str (optional default is None) = detaile dtext shown by expanding
            the dialog
        msgType:str (optional default is 'Information')
            Allowed values are:
            "NoIcon", "Question", "Information", "Warning", "Critical", a valid
            pixmap file name, or a valid theme icon name.
            
        """
        if isinstance(msgType, str) and len(msgType.strip()):
            if getattr(QtWidgets.QMessageBox.Icon, msgType, None) is not None:
                icon = getattr(QtWidgets.QMessageBox.Icon, msgType, QtWidgets.QMessageBox.NoIcon)
            else:
                try:
                    if os.path.isfile(msgType):
                        pix = QtGui.QPixmap(msgType)
                    else:
                        pix = QtGui.Icon.fromTheme(msgType).pixmap(QtWidgets.QStyle.PM_MessageBoxIconSize)
                        msgBox.setIconPixmap(pix)
                        
                except:
                    icon = QtWidgets.QMessageBox.NoIcon
        
        msgbox = QtWidgets.QMessageBox(parent=self)
        msgbox.addButton(QtWidgets.QMessageBox.Ok)
        if isinstance(icon, QtGui.QPixmap):
            msgbox.setIconPixmap(icon)
        elif isinstance(icon, QtWidgets.QMessageBox.Icon):
            msgbox.setIcon(icon)
        else:
            msgbox.setIcon(QtWidgets,QMessageBox.NoIcon)
            
        msgbox.setSizeGripEnabled(True)
        msgbox.setWindowTitle(title)
        msgbox.setText(text)
        
        if isinstance(info, str) and len(info.strip()):
            msgbox.setInformativeText(info)
            
        if isinstance(detail, str) and len(detail.strip()):
            msgbox.setDetailedText(detail)
            
        return msgbox.exec()
        
class FileIOGui(object):
    @safeWrapper
    def chooseFile(self, caption:typing.Optional[str]=None, fileFilter:typing.Optional[str]=None, single:typing.Optional[bool]=True, save:bool=False, targetDir:typing.Optional[str]=None):
        """Launcher of file open dialog
        
        Parameters:
        ----------
        caption: str, optional default is None - The caption of the file chooser dialog
        
        fileFilter: str, optional, default is None - The file filter for choosing
            from a specific subset of tile types. When present, it must have a 
            specific format, e.g. "Pickle Files (*.pkl);;Text Files (*.txt)"
            
            See QtWidget.QDialog.getOpenFileName for details about fileFilter
            
        single:bool, optional (default: True)
           When False, the file chooser dialog will allow opening several files
           
           Ignored when 'save' is True (see below)
           
        save:bool, default False
            When True, signals the intention to SAVE to the selected file name, 
            and 'single' will eb ignored
            In this case it will ask for confirmation to overwrite the file.
           
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
                
        opener = QtWidgets.QFileDialog.getSaveFileName if save is True else QtWidgets.QFileDialog.getOpenFileName if single else QtWidgets.QFileDialog.getOpenFileNames
        
        if isinstance(caption, str) and len(caption.strip()):
            opener = partial(opener, caption=caption)
            
        if isinstance(fileFilter, str) and len(fileFilter.strip()):
            opener = partial(opener, filter=fileFilter)
        
        fn, fl = opener(parent=self, directory=targetDir)
        
        return fn, fl
    
    @safeWrapper
    def chooseDirectory(self, caption:typing.Optional[str]=None,targetDir:typing.Optional[str]=None):
        
        if targetDir is not None and targetDir != "" and os.path.exists(targetDir):
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=caption, directory=targetDir))
        else:
            dirName = str(QtWidgets.QFileDialog.getExistingDirectory(self, caption=caption))
            
        return dirName
    
class WorkspaceGuiMixin(GuiMessages, FileIOGui, ScipyenConfigurable):
    """Mixin type for windows that need to be aware of Scipyen's main workspace.
    
    Provides:
    1) Common functionality needed in Scipyen's windows:
        1.1) Standard dialogs for importing data from the workspace, file open 
        & save operations
        
        1.2) Message dialogs
    
    2) Management of Qt and non-Qt configurables
        
        2.1) Auguments ScipyenConfigurable with standard Qt configurables for
        :classes: derived from Qt QMainWindow and QWidget: size, position, 
        geometry and state (for QWindow-based :classes: only)
        
    3) Distinction between QWindow objects that are direct children of Scipyen's
    main window (so-called "top-level" windows) and those that are children of 
    one of Scipyen's 'apps'.
        Top-level windows include viewers launched directly by double-clicking
        on variables in the workspace, Scipyens consoles, and the main windows
        for the so-called Scipyen 'apps'.
        
        The latter run code which requires a customized GUI (provided by their
        own main window) including children windows of data viewers.
        
    About configurables.
    ====================
        
    Scipyen deals with two groups of configuration variables ("configurables",
    or "settings"):
        
    • Qt configurables: variables related to the appearance of Qt widgets and
        windows (e.g. position on screen, size, state)
        
    • non-Qt configurables (e.g. properties of cursors such as colors,
        and various preferences for non-gui objects). These are also called
        ":class:-configurables" because they contain preferences applied to a 
        non-gui object type
    
    WorkspaceGuiMixin manages both Qt and non-Qt settings and via its 
    ScipyenConfigurable ancestor type.
    
    Classes that inherit from WorkspaceGuiMixin also inherit the following
    from ScipyenConfigurable:
    
    • the methods 'self.loadSettings' and 'self.saveSettings' that load/save the
        Qt configurables from/to the Scipyen.conf file.
        
    • the attribute 'configurable_traits' - a DataBag that observes changes to
        non-Qt configurable instance attributes (treated as 'traits')
        
    • the (private) method _observe_configurables_() which is notified by the
        'configurable_traits' of attribute changes and synchronizes their value 
        with the config.yaml file.
    
    In order to save/load persistent configurations from/to Scipyen's 
    configuration files, a GUI :class: that inherits from WorkspaceGuiMixin
    needs to:
    
    1) Define python property setter, as well as the getter & setter methods for 
    the relevant attributes DECORATED with the `markConfigurable` decorator
    (defined in core.scipyen_config module). This decorator 'flags' the
    instance attributes as either Qt or non-Qt configurables.
    
    2) Call self.loadSettings() in its own __init__ method body.
        This is required for BOTH Qt and non-Qt configurables.
        
        For this to work with Qt configurables, loadSettings() needs to be 
        executed AFTER the GUI components have been defined and added to the 
        :class: attributes. In classes generated with Qt Designer, this is 
        not before calling self.setupUi(self) which initializes the GUI 
        components basd on a designer *.ui file, and certainly AFTER further 
        UI components are added manually.
        
        NOTE: By inheriting from WorkspaceGuiMixin (and, thus from
        ScipyenConfigurable) loadSettings() is called automatically. Nevertheless,
        this method may be reimplemented in the derived :class:.
        
    3) Call self.saveSetting() at an appropriate point during the life-time of 
        the instance of the :class:. 
        
        For Qt-based settings ('qtconfigurables') this is typically called upon
        closing the window or widget. A convenient way is to reimplement the 
        'closeEvent' method of the Qt base :class: to call saveSettings from
        within the new closeEvent body.
        
        The non-Qt configurables are synchronized with the config.yaml file
        whenever the configurable_traits notifies their change.
        
        However, saveSettings ensures that all changes in the 
        non-Qt configurables are saved to the config.yaml file.
        
        NOTE: As the loadSettings() method, the saveSetting() method is also 
        inherited from ScipyenConfigurable, but it may be reimplemented in the
        derived :class:
        
    """
    #In addition, further settings can be defined by either
    
    #1) populating the '_qtcfg' attribute of the derived window type with new
    #entries (see self.qtconfigurables for details),  - this will be updated with
    #WorkspaceGuiMixin._qtcfg contents upon initialization of the derived type,
    
    #or
    
    #2) creating in the derievd type an attribute named '_ownqtcfg' - a mapping 
    #of a similar structure to '_qtcfg'.
    
    #NOTE: this only needs to be done in the most derived type in a long
    #inheritance chain. This is done. e.g. in SignalViewer where the inheritance 
    #chains is:
    
    #SignalViewer <- ScipyenFrameViewer <- ScipyenViewer <- WorkspaceGuiMixin <- ScipyenConfigurable
    
    #or
    
    #3) by decorating the desired property in the derived type with the 
    #@markConfigurable  decorator
    # NOTE: 2021-08-26 11:32:25
    # key:str = QSettings key
    # value: 
    #   EITHER: tuple (str, str) = getter method name, setter method name
    #           where:
    #               getter method name: name of instance or :class: method that
    #                                   returns a Python object (CAUTION: when
    #                                   the method returns SEVERAL obejcts they
    #                                   will be captured in a tuple!)
    #               setter method name: name of the instance or :class: method that
    #                                   accepts ONE Python object as parameter
    #                                   which corresponds to the return value of
    #                                   the getter method
    #
    #   OR:     tuple (str, ) = property
    #           where: property is the name of a descriptor with read-write access
    #
    #
    # CAUTION: If present it will override whatever is set by ScipyenConfigurable
    # or makeConfigurable / markConfigurable decorators
    #
    # WARNING: These must be present here to augment ScipyenConfigurable
    _qtcfg = Bunch({"WindowSize":       Bunch({"getter":"size",        "setter":"resize"}),
                    "WindowPosition":   Bunch({"getter":"pos",         "setter":"move"}),
                    "WindowGeometry":   Bunch({"getter":"geometry",    "setter":"setGeometry"}),
                    "WindowState":      Bunch({"getter":"saveState",   "setter":"restoreState"}),
                    })
    
    _ownqtcfg = Bunch()
    
    _cfg = Bunch()
    
    _owncfg = Bunch()
    
    def workspaceSymbolForData(self, data):
        ws = self.appWindow.workspace
        return get_symbol_in_namespace(data, ws)        
    
    def __init__(self, parent: (QtWidgets.QMainWindow, type(None)) = None, title="", *args, **kwargs):
        ScipyenConfigurable.__init__(self, *args, **kwargs)
                
        self._scipyenWindow_ = None
        
        if isinstance(parent, QtWidgets.QMainWindow) and type(parent).__name__ == "ScipyenWindow":
            self._scipyenWindow_   = parent
            
        else:
            # NOTE: 2020-12-05 21:24:45 CAUTION FIXME/TODO
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
        This is a reference to the Scipyen main window, unless explicitly given
        as some other QMainWindow at the viewer's initiation.
        
        appWindow gives access to Scipyen main window API (e.g. the workspace).
        """
        return self._scipyenWindow_
    
    @safeWrapper
    def importWorkspaceData(self, dataTypes:typing.Union[typing.Type[typing.Any], typing.Sequence[typing.Type[typing.Any]]], title:str="Import from workspace", single:bool=True, preSelected:typing.Optional[str]=None, with_varName:bool=False):
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
        
        if isinstance(preSelected, str) and len(preSelected.strip()) and preSelected in name_list:
            dialog = ItemsListDialog(parent=self, title=title, itemsList = name_list,
                                    selectmode = selectionMode, preSelected=preSelected)
        else:
            dialog = ItemsListDialog(parent=self, title=title, itemsList = name_list,
                                    selectmode = selectionMode)
        
        ans = dialog.exec()
        
        if ans == QtWidgets.QDialog.Accepted:
            if with_varName:
                return [(i, self._scipyenWindow_.workspace[i]) for i in dialog.selectedItemsText]
            else:
                return [self._scipyenWindow_.workspace[i] for i in dialog.selectedItemsText]
            
        return list()
    
    @safeWrapper
    def exportDataToWorkspace(self, data:typing.Any, var_name:str, title:str="Export data to workspace"):
        newVarName = strutils.str2symbol(var_name)
        if self.appWindow:
            newVarName = validate_varname(newVarName, ws = self.appWindow.workspace)
        
        dlg = qd.QuickDialog(self, title)
        namePrompt = qd.StringInput(dlg, "Export data as:")
        
        namePrompt.variable.setClearButtonEnabled(True)
        namePrompt.variable.redoAvailable=True
        namePrompt.variable.undoAvailable=True
        
        namePrompt.setText(newVarName)
        
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            newVarName = namePrompt.text()
            # newVarName = validate_varname(namePrompt.text(), self._scipyenWindow_.workspace)
            if newVarName in self._scipyenWindow_.workspace:
                accept = self.questionMessage("Export to workspace", f"A variable named {newVarName} exists in the workspace. Overwrite?")
                if accept not in (QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Yes):
                    return
                
            self._scipyenWindow_.assignToWorkspace(newVarName, data)
            
            if hasattr(data, "modified") and isinstance(data.modified, bool):
                data.modified=False
            # self.displayFrame()
            
            self.statusBar().showMessage("Done!")
        
    def getDataSymbolInWorkspace_(self, data=None):
        """Calls workspacefunctions.get_symbol_in_namespace for the data.
        """
        if data is None:
            data = self._data_
        if data is not None and isinstance(self._scipyenWindow_, QtWidgets.QMainWindow) and self._scipyenWindow_.__class__.__name__.startswith("ScipyenWindow"):
            return get_symbol_in_namespace(data, self._scipyenWindow_.workspace)
    
            
        
