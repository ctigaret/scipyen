# -*- coding: utf-8 -*-
import typing, warnings, os, inspect
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
    """Mixin class for windows that need to be aware of Scipyen's main workspace.
    
    Also provides common functionality needed in Scipyen's windows. 
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
            
        
def saveWindowSettings(qsettings, win, parent=None, entry_name:typing.Optional[str]=None, 
                       use_group:bool=True, group_name:typing.Optional[str]=None):
    # NOTE: 2021-07-11 18:32:56
    # QSettings support maximum one nesting level (i.e., group/entry)
    
    if parent is None:
        if isinstance(win, QtWidgets.QMainWindow):
            parent = win.parent()
            
        elif isinstance(win, mpl.figure.Figure):
            parent = None # FIXME 2021-08-23 18:39:32
        
    if isinstance(parent, QtWidgets.QMainWindow):
        use_group = True
        if not isinstance(group_name, str) or len(group_name.strip()):
            group_name = parent.__class__.__name__
            
    if isinstance(group_name, str) and len(group_name.strip()):
        use_group = True
        
    if use_group:
        if not isinstance(group_name, str) or len(group_name.strip()):
            group_name = win.__class__.__name__
        qsettings.beginGroup(group_name)
        
    if isinstance(entry_name, str) and len(entry_name.strip()):
        ename = "%s_" % entry_name
    else:
        ename=""
        
    print("workspacegui.saveWindowSettings viewer %s, group %s, entry %s " % (win.__class__, group_name, entry_name))
    
    qsettings.setValue("%sWindowSize" % ename, win.size())
    qsettings.setValue("%sWindowPosition" % ename, win.pos())
    qsettings.setValue("%sWindowGeometry" % ename, win.geometry())
    
    if hasattr(win, "saveState"):
        qsettings.setValue("%sWindowState" % ename, win.saveState())
        
    if use_group:
        qsettings.endGroup()
    
def loadWindowSettings(qsettings, win, parent=None, entry_name:typing.Optional[str]=None, 
                       use_group:bool=True, group_name:typing.Optional[str]=None):
    
    if parent is None:
        if isinstance(win, QtWidgets.QMainWindow):
            parent = win.parent()
            
        elif isinstance(win, mpl.figure.Figure):
            parent = None # FIXME 2021-08-23 18:39:32
        
    if isinstance(parent, QtWidgets.QMainWindow):
        use_group = True
        if not isinstance(group_name, str) or len(group_name.strip()):
            group_name = parent.__class__.__name__
        
    if isinstance(group_name, str) and len(group_name.strip()):
        use_group = True
        
    if use_group:
        if not isinstance(group_name, str) or len(group_name.strip()):
            group_name = win.__class__.__name__
        qsettings.beginGroup(group_name)
        
    if isinstance(entry_name, str) and len(entry_name.strip()):
        ename = "%s_" % entry_name
    else:
        ename=""
        
    print("workspacegui.loadWindowSettings viewer %s, group %s, entry %s " % (win.__class__, group_name, entry_name))
        
    windowSize = qsettings.value("%sWindowSize" % ename, None)
    if windowSize:
        win.resize(windowSize)
        
    windowPos = qsettings.value("%sWindowPosition" % ename, None)
    if windowPos:
        win.move(windowPos)
    
    windowGeometry = qsettings.value("%sWindowGeometry" % ename, None)
    if windowGeometry:
        win.setGeometry(windowGeometry)
        
    if hasattr(win, "restoreState"):
        windowState = qsettings.value("%sWindowState" % ename, None)
        if windowState:
            win.restoreState(windowState)
    
    if use_group:
        qsettings.endGroup()
