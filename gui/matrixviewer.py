# -*- coding: utf-8 -*-
"""
Qt5-based viewer window for two dimensional ndarrays

"""
#### BEGIN 3rd party modules
import numpy as np
import vigra
from PyQt5 import QtCore, QtWidgets, QtGui
#### END 3rd party modules

#### BEGIN pict.iolib modules
from iolib import pictio as pio

#### END pict.iolib modules

#### BEGIN pict.gui modules
from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from . import quickdialog
from . import resources_rc
#### END pict.gui modules

# TODO / FIXME: 2019-11-10 16:33:13 Merge with TableEditor
class MatrixViewer(ScipyenViewer):
    """Simple table viewer for numpy arrays and vigra.filters.Kernel* objects.
    
    No context menu or editing capabilities are implemented.
    
    On its way to deprecation -- use TableEditor (see below)
    
    See also:
    * gui.dictviewer.ScipyenTableWidget
    * gui.tableeditor.TableEditorWidget for extended functionality
    
    """
    supported_types = (
                       np.ndarray, 
                       vigra.VigraArray,
                       vigra.filters.Kernel1D, 
                       vigra.filters.Kernel2D,
                       )
    view_action_name = "Matrix"
    
    #def __init__(self, data: (np.ndarray, vigra.VigraArray, vigra.filters.Kernel1D, vigra.filters.Kernel2D, type(None)) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, 
                 #pWin: (QtWidgets.QMainWindow, type(None))= None, ID:(int, type(None)) = None,
                 #win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None,
                 #*args, **kwargs) -> None:
        #super().__init__(data=data, parent=parent, pWin=pWin, win_title=win_title, doc_title=doc_title, ID=ID, *args, **kwargs)
        
    def __init__(self, data: (np.ndarray, vigra.VigraArray, vigra.filters.Kernel1D, vigra.filters.Kernel2D, type(None)) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, 
                 ID:(int, type(None)) = None, win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None,
                 *args, **kwargs) -> None:
        super().__init__(data=data, parent=parent, win_title=win_title, doc_title=doc_title, ID=ID, *args, **kwargs)
        
    def _configureUI_(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction("&Save As...", self.saveAsFile, "Ctrl+Sift+S")
        
        self._tableWidget = QtWidgets.QTableWidget(self)
        #self._tableWidget.setSortingEnabled(False) # this IS the default!
        
        self.setCentralWidget(self._tableWidget)
            
    def _set_data_(self, data, *args, **kwargs):
        if data is not None:
            if isinstance(data, np.ndarray) and data.ndim in (1,2):
                self._data_ = data
            else:
                raise ValueError("Data must be a 1D or 2D numpy array")
            
        else:
            self._data_ = data
            
        self._setupView_()
        
        if kwargs.get("show", True):
            self.activateWindow()
            
    def _setupView_(self): # this can be expensive!
        if self._data_ is None:
            return
        
        if self._data_.ndim == 2:
            self._tableWidget.setRowCount(self._data_.shape[0])
            self._tableWidget.setVerticalHeaderLabels(["%d" % r for r in range(self._data_.shape[0])])
            
            self._tableWidget.setColumnCount(self._data_.shape[1])
            self._tableWidget.setHorizontalHeaderLabels(["%d" % c for c in range(self._data_.shape[1])])
            
            for c in range(self._data_.shape[1]):
                for r in range(self._data_.shape[0]):
                    self._tableWidget.setItem(r, c, QtWidgets.QTableWidgetItem("%f" % self._data_[r,c]))
            
        elif self._data_.ndim == 1:
            self._tableWidget.setRowCount(self._data_.size)
            self._tableWidget.setVerticalHeaderLabels(["%d" % r for r in range(self._data_.size)])
            
            self._tableWidget.setColumnCount(1)
            self._tableWidget.setHorizontalHeaderLabels(["0"])
            
            for r in range(self._data_.size):
                self._tableWidget.setItem(r,0, QtWidgets.QTableWidgetItem("%f" % self._data_[r]))
        
    def saveAsFile(self):
        if self._data_ is None:
            return
        
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save CSV Document", filter="CSV files (*.csv)")
            
        if len(filePath) > 0:
            pio.writeCsv(self._data_, filePath)
                
