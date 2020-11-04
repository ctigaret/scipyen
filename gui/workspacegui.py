# -*- coding: utf-8 -*-
import typing, warnings, os
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from core.utilities import safeWrapper


class WorkspaceGuiMixin:
    """Mixin class for windows that need to be aware of Scipyen's main workspace.
    
    Also provides common functionality needed in Scipyen's windows. 
    """
    
    def __init__(self, parent: (QtWidgets.QMainWindow, type(None)) = None,
                 pWin: (QtWidgets.QMainWindow, type(None))= None ):
        self._scipyenWindow_ = None
        
        if isinstance(pWin, QtWidgets.QMainWindow) and type(pWin).__name__ == "ScipyenWindow":
            self._scipyenWindow_  = pWin
        
        else:
            if isinstance(parent, QtWidgets.QMainWindow) and type(parent).__name__ == "ScipyenWindow":
                self._scipyenWindow_   = parent
        
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
        
        name_vars = getvarsbytype(dataTypes, ws = self._scipyenWindow_.workspace)
        
        if len(name_vars) == 0:
            return list()
        
        name_list = sorted([name for name in name_vars])
        
        selectionMode = QtWidgets.QAbstractItemView.SingleSelection if single else QtWidgets.QAbstractItemView.MultiSelection
        
        dialog = pgui.ItemsListDialog(parent=self, title=title,itemsList = name_list,
                                      selectmode = selectionMode)
        
        ans = dialog.exec()
        
        if ans == QWidgets.QDialog.Accepted:
            return [self._scipyenWindow_[i] for i in dialog.selectedItems]
            
        return list()
            
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
    def errorMessage(self, title, text):
        errMsgDlg = QtWidgets.QErrorMessage(self)
        errMsgDlg.setWindowTitle(title)
        errMsgDlg.showMessage(text)
        
    @safeWrapper
    def criticalMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.critical(self, title=title, text=text)
        
    @safeWrapper
    def informationMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.information(self, title=title, text=text)
        
    @safeWrapper
    def questionMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.question(self, title=title, text=text)
        
    @safeWrapper
    def warningMessage(self, title, text, default=QtWidgets.QMessageBox.No):
        QtWidgets.QMessageBox.warning(self, title=title, text=text)
        
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
        
