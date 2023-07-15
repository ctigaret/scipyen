import os, sys
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

# NOTE: 2023-07-14 16:32:06
# necessary to adapt to the situation where Scipyen is bundled
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
#      # WARNING this must be reflected in scipyen.spec file!
#     __ui_path__ = os.path.join(__module_path__, "UI")
# else:
#     __ui_path__ = __module_path__

__ui_path__ = adapt_ui_path(__module_path__, "itemslistdialog.ui")

# print(f"__ui_path__ {__ui_path__}")
    
Ui_ItemsListDialog, QDialog = __loadUiType__(__ui_path__)
# Ui_ItemsListDialog, QDialog = __loadUiType__(os.path.join(__ui_path__,"itemslistdialog.ui"))

class ItemsListDialog(QDialog, Ui_ItemsListDialog):
    itemSelected = QtCore.pyqtSignal(str)

    def __init__(self, parent = None, itemsList=None, title=None, preSelected=None, modal=False, selectmode=QtWidgets.QAbstractItemView.SingleSelection):
        super(ItemsListDialog, self).__init__(parent)
        self.setupUi(self)
        self.setModal(modal)
        self.preSelected = list()
        
        self.searchLineEdit.undoAvailable=True
        self.searchLineEdit.redoAvailable=True
        self.searchLineEdit.setClearButtonEnabled(True)
        
        self.searchLineEdit.textEdited.connect(self.slot_locateSelectName)
        
        if isinstance(selectmode, str):
            if selectmode.lower == "single":
                selectmode = QtWidgets.QAbstractItemView.SingleSelection
            elif selectmode.lower == "contiguous":
                selectmode = QtWidgets.QAbstractItemView.ContiguousSelection
            elif selectmode.lower == "extended":
                selectmode = QtWidgets.QAbstractItemView.ExtendedSelection
            elif selectmode.lower == "multi":
                selectmode = QtWidgets.QAbstractItemView.MultiSelection
            else:
                warnings.warn(f"I don't know what '{selectmode}' selection means...")
                selectmode = QtWidgets.QAbstractItemView.SingleSelection
                
            
        if not isinstance(selectmode, QtWidgets.QAbstractItemView.SelectionMode):
            selectmode = QtWidgets.QAbstractItemView.SingleSelection
        
        self.listWidget.setSelectionMode(selectmode)
    
        if title is not None:
            self.setWindowTitle(title)
    
        self.listWidget.itemClicked.connect(self.selectItem)
        self.listWidget.itemDoubleClicked.connect(self.selectAndGo)

        self.selectionMode = selectmode
        
        if isinstance(itemsList, (tuple, list)) and \
            all([isinstance(i, str) for i in itemsList]):
            
            if isinstance(preSelected, str) and preSelected in itemsList:
                self.preSelected = [preSelected]
                
            elif isinstance(preSelected, (tuple, list)) and all([(isinstance(s, str) and len(s.strip()) and s in itemsList) for s in preSelected]):
                self.preSelected = preSelected
                
            self.setItems(itemsList)
            
    @pyqtSlot(str)
    def slot_locateSelectName(self, txt):
        found_items = self.listWidget.findItems(txt, QtCore.Qt.MatchContains | QtCore.Qt.MatchCaseSensitive)
        if len(found_items):
            for row in range(self.listWidget.count()):
                self.listWidget.item(row).setSelected(False)
                
            for k, item in enumerate(found_items):
                item.setSelected(True)
                self.itemSelected.emit(str(item.text()))
                
            sel_indexes = self.listWidget.selectedIndexes()
            
            if len(sel_indexes):
                self.listWidget.scrollTo(sel_indexes[0])
                if len(sel_indexes) == 1:
                    self.itemSelected.emit(str(found_items[0].text()))
                #self.itemSelected.emit()
            
    def validateItems(self, itemsList):
        # 2016-08-10 11:51:07
        # NOTE: in python3 all str are unicode
        if itemsList is None or isinstance(itemsList, list) and (len(itemsList) == 0 or not all([isinstance(x,(str)) for x in itemsList])):
            QtWidgets.QMessageBox.critical(None, "Error", "Argument must be a list of string or unicode items.")
            return False
        return True

    @property
    def selectedItemsText(self):
        """A a list of str - text of selected items, which may be empty
        """
        return [str(i.text()) for i in self.listWidget.selectedItems()]
        
    @property
    def selectionMode(self):
        return self.listWidget.selectionMode()
    
    @selectionMode.setter
    def selectionMode(self, selectmode):
        if not isinstance(selectmode, (int, QtWidgets.QAbstractItemView.SelectionMode, str)):
            raise TypeError("Expecting an int or a QtWidgets.QAbstractItemView.SelectionMode; got %s instead" % type(selectmode).__name__)
        
        if isinstance(selectmode, int):
            if selectmode not in range(5):
                raise ValueError("Invalid selection mode:  %d" % selectmode)
            
        elif isinstance(selectmode, str):
            if selectmode.strip().lower() not in ("single", "multi"):
                raise ValueError("Invalid selection mode %s", selectmode)
            
            if selectmode == single:
                selectmode = QtWidgets.QAbstractItemView.SingleSelection
                
            else:
                selectmode = QtWidgets.QAbstractItemView.MultiSelection
            
        self.listWidget.setSelectionMode(selectmode)
                
    def setItems(self, itemsList, preSelected=None):
        """Populates the list dialog with a list of strings :-)
        
        itemsList: a python list of python strings :-)
        """
        if self.validateItems(itemsList):
            self.listWidget.clear()
            self.listWidget.addItems(itemsList)
            
            if isinstance(preSelected, (tuple, list)) and len(preSelected) and all([(isinstance(s, str) and len(s.strip()) and s in itemsList) for s in preSelected]):
                self.preSelected=preSelected
                
            elif isinstance(preSelected, str) and len(preSelected.strip()) and preSelected in itemsList:
                self.preSelected = [preSelected]
            
            longestItemNdx = np.argmax([len(i) for i in itemsList])
            longestItem = itemsList[longestItemNdx]
            
            for k, s in enumerate(self.preSelected):
                ndx = itemsList.index(s)
                item = self.listWidget.item(ndx)
                self.listWidget.setCurrentItem(item)
                self.listWidget.scrollToItem(item)
                
            fm = QtGui.QFontMetrics(self.listWidget.font())
            w = fm.width(longestItem) * 1.1
            
            if self.listWidget.verticalScrollBar():
                w += self.listWidget.verticalScrollBar().sizeHint().width()
                
            self.listWidget.setMinimumWidth(int(w))

    @pyqtSlot(QtWidgets.QListWidgetItem)
    def selectItem(self, item):
        self.itemSelected.emit(str(item.text())) # this is a QString !!!
        
    @pyqtSlot(QtWidgets.QListWidgetItem)
    def selectAndGo(self, item):
        self.itemSelected.emit(item.text())
        self.accept()
        
    @property
    def selectedItems(self):
        return self.listWidget.selectedItems()
        
