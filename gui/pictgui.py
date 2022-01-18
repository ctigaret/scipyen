"""
    This module contains:
    
    1) PlanarGraphics objects:
        Move (aliased to Point and Start)
        Line
        Arc
        ArcMove
        Cubic
        Cursor
        Quad
        Ellipse
        Rrect
        Path
        
    2) GraphicsObject 
    A GUI representation of PlanarGraphics objects in the Qt GraphicsView framework.
    
    3) Various generic GUI utilities: mostly dialogues
"""
# NOTE: 2018-04-15 10:34:03
# frameVisibility parameter in graphics object creation:
# only use it when creating a GraphicsObject from scratch; 
# ignore it when using a PlanarGraphics object (backend) to generate a GraphicsObject
# because the frames where the graphics object is visible are set by the frame-state
# associations of the backend

# TODO/FIXME 2018-02-11 22:11:38
# consider a single Point "class", with _qt_path_composition_call_ set to either
# moveTo or lineTo, depending on whether the Point is at the beginning of a (sub)path
# or not.
#
# Dedicate the Line "class" to a real line segment (x0,y0,x1,y1)
#
# I know this is highly likely to break backward compatibility with data already
# analysed  -- TODO: patch in appropriate code for conversion especially for
# unpickling old data
#
# TODO/FIXME define a pictgui.Geometry class for n-dimensional objects
# TODO subclasses: mesh, plane, cuboid, spheroid, pyramid, cylinder, 
# TODO              truncated_pyramid, truncated_cylinder
# TODO              torus, etc etc etc
# TODO read on Qt3D geometry
# TODO a very long shot !!!

#### BEGIN core python modules
# NOTE: use Python re instead of QRegExp
import sys, os, re, numbers, itertools, warnings, traceback
import typing
import math
from collections import (ChainMap, namedtuple, defaultdict, OrderedDict,)
from functools import (partial, partialmethod,)
from enum import (Enum, IntEnum,)
#from abc import ABCMeta, ABC
from copy import copy
#from traitlets.utils.bunch import Bunch


#### END core python modules

#### BEGIN 3rd party modules
#import vigra.pyqt.quickdialog as quickdialog
import pyqtgraph as pg
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__
#### END 3rd party modules

#print("pgui __name__", __name__, "__module_path__", __module_path__)

#### BEGIN pict.core modules
from core.traitcontainers import DataBag
from core.prog import (safeWrapper, deprecated,
                       timefunc, processtimefunc,)
#from core.utilities import (unique, index_of,)
from core.workspacefunctions import debug_scipyen


#### END pict.core modules

#### BEGIN pict.gui modules
from . import quickdialog
from . import resources_rc
from .planargraphics import (Arc, ArcMove, Cubic, Cursor, Ellipse, Line, Move, Path,
                           PlanarGraphics, Point, Quad, Rect, Text, VerticalCursor,
                           HorizontalCursor, CrosshairCursor, PointCursor,
                           PlanarGraphicsType, GraphicsObjectType, GraphicsObject, 
                           __new_planar_graphic__, printQPainterPath)

#### END pict.gui modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))

#Ui_EditColorMapWidget, QWidget = __loadUiType__(os.path.join(__module_path__,"editcolormap2.ui"))

Ui_ItemsListDialog, QDialog = __loadUiType__(os.path.join(__module_path__,"itemslistdialog.ui"))

Ui_LinearRangeMappingWidget, QWidget = __loadUiType__(os.path.join(__module_path__, "linearrangemappingwidget.ui"))

def generateColorCycle():
    pass

def generateBrushCycle(color:typing.Optional[QtGui.QColor] = None, 
                       gradients: typing.Optional[QtGui.QGradient] = None,
                       images=None,
                       pixmaps=None,
                       styles=None):
    if isinstance(values, (tuple, list)):
        if all([isinstance(v, int)]) and len(value) == 4:
            # single value spec (R,G,B,A)
            brushes = itertools.cycle(QtGui.Brush(QtGui.QColor(*c)))
            
    pass

def generatePenCycle():
    pass

def genColorTable(cmap, ncolors=256):
    if cmap is None:
        return None
    x = np.arange(ncolors)
    cnrm = colors.Normalize(vmin=min(x), vmax=max(x))
    smap = cm.ScalarMappable(norm=cnrm, cmap=cmap)
    colortable = smap.to_rgba(x, bytes=True)
    return colortable

class GuiWorkerSignals(QtCore.QObject):
    signal_finished = pyqtSignal()
    sig_error = pyqtSignal(tuple)
    signal_result = pyqtSignal(object)
    
class GuiWorker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(GuiWorker, self).__init__()
        
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        
        self.signals = GuiWorkerSignals()
        
    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            
        except:
            traceback.print_exc()

            exc_type, value = sys.exc_info()[:2]
            
            self.signals.sig_error.emit((exc_type, value, traceback.format_exc()))
            
        else:
            self.signals.signal_result.emit(result)  # Return the result of the processing
            self.signals.signal_finished.emit()  # Done
            
        finally:
            self.signals.signal_finished.emit()  # Done

class ProgressWorkerSignals(QtCore.QObject):
    """See Martin Fitzpatrick's tutorial on Multithreading PyQt applications with QThreadPool 
    https://martinfitzpatrick.name/article/multithreading-pyqt-applications-with-qthreadpool/
    
    Defines the signals available from a running worker thread.

    Supported signals are:

    signal_finished
        No data

    sig_error
        `tuple` (exctype, value, traceback.format_exc() )

    signal_result
        `object` data returned from processing, anything

    signal_progress
        `int` indicating % progress

    """
    
    signal_finished = pyqtSignal()
    sig_error = pyqtSignal(tuple)
    signal_result = pyqtSignal(object)
    signal_progress = pyqtSignal(int)
    signal_setMaximum = pyqtSignal(int)
    
class ProgressWorker(QtCore.QRunnable):
    """
    ProgressWorker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param fn:  The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
                     
    :type fn: function
    
        The function is expected to execute a loop computation and its signature
        should contain an optional named parameter "progressSignal" of type 
        pyqtSignal, to be emitted after each iteration of the loop code.

    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    
    NOTE: the entire loop is executed in a separate thread and periodically
    signals its progress by emitting the progressSignal, connected to a 
    progressDialog in the main (GUI) thread.

    """
    def __init__(self, fn, progressDialog, *args, **kwargs):
        """
        fn: callable
        progressDialog: QtWidgets.QProgressDialog
        *args, **kwargs are passed to fn
        """
        super(ProgressWorker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = ProgressWorkerSignals()
        self.pd = progressDialog
        
        if isinstance(self.pd, QtWidgets.QProgressDialog):
            self.pd.setValue(0)
            self.signals.signal_progress.connect(self.pd.setValue)
            self.signals.signal_setMaximum.connect(self.pd.setMaximum)
            self.kwargs['progressSignal'] = self.signals.signal_progress
            self.kwargs["setMaxSignal"] = self.signals.signal_setMaximum
            
        #else:
            #self.pd = None

        # Add the callback to our kwargs
        
        #print("ProgressWorker fn args", self.args)

    @pyqtSlot()
    def run(self):
        '''Initialise the runner function with passed args, kwargs.
        This is done by calling something like threadpool.start(worker)
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
            
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sig_error.emit((exctype, value, traceback.format_exc()))
            
        else:
            self.signals.signal_result.emit(result)  # Return the result of the processing
            
        finally:
            self.signals.signal_finished.emit()  # Done
            
def checkboxDialogPrompt(parent, title, slist):
    if not all([isinstance(s, str) for s in slist]):
        raise TypeError("Expecting a list of strings for the last argument")
    dlg = quickdialog.QuickDialog(parent, title)
    dlg.addWidget(QtWidgets.QLabel(title, parent=dlg))
    group = quickdialog.VDialogGroup(dlg)
    
    checkboxes = [quickdialog.CheckBox(group, value) for value in slist]
    
    dlg.resize(dlg.minimumSize())
    
    if dlg.exec() == 1:
        return [w.isChecked() for w in checkboxes]
    
    else:
        return [True for w in checkboxes]
    
class MouseEventSink(QtCore.QObject):
    def __init__(self, *args, **kwargs):
        super(MouseEventSink, self).__init__(*args, **kwargs)
        
    def eventFilter(self, obj, evt):
        if evt.type() in (QtCore.QEvent.GraphicsSceneMouseDoubleClick, 
                          QtCore.QEvent.GraphicsSceneMousePress, 
                          QtCore.QEvent.GraphicsSceneMouseRelease,
                          QtCore.QEvent.GraphicsSceneHoverEnter, 
                          QtCore.QEvent.GraphicsSceneHoverLeave, 
                          QtCore.QEvent.GraphicsSceneHoverMove,
                          QtCore.QEvent.GraphicsSceneMouseMove):
            return True
        
        else:
            return False
    
    # don't use validate as this overrides a QWidget method and breaks the dialog code below
    def validateItems(self, itemsList):
        if itemsList is None or not all([isinstance(x,(str,unicode)) for x in itemsList]):
            QtWidgets.QMessageBox.critical(None, "Error", QtCore.QString("Argument must be a list of string or unicode items."))
            return False
        return True

      
    def selectItem(self, item):
        self.selectedColorMap = item.text()
        self.itemSelected.emit(item.text()) # this is a QString !!!
        #print(item.text())

    
    def selectAndGo(self, item):
        self.selectedColorMap = item.text()
        self.itemSelected.emit(item.text())
        self.close()

class ItemsListDialog(QDialog, Ui_ItemsListDialog):
    itemSelected = QtCore.pyqtSignal(str)

    def __init__(self, parent = None, itemsList=None, title=None, 
                 preSelected=None, modal=False, 
                 selectmode=QtWidgets.QAbstractItemView.SingleSelection):
        super(ItemsListDialog, self).__init__(parent)
        self.setupUi(self)
        self.setModal(modal)
        self.preSelected = list()
        
        self.searchLineEdit.undoAvailable=True
        self.searchLineEdit.redoAvailable=True
        self.searchLineEdit.setClearButtonEnabled(True)
        
        self.searchLineEdit.textEdited.connect(self.slot_locateSelectName)
        
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
                
            self.listWidget.setMinimumWidth(w)

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
        
class SelectablePlotItem(pg.PlotItem):
    itemClicked = pyqtSignal()
    
    def __init__(self, **kwargs):
        super(SelectablePlotItem, self).__init__(**kwargs)
        
    def mousePressEvent(self, ev):
        super(SelectablePlotItem, self).mousePressEvent(ev)
        self.itemClicked.emit()
        
