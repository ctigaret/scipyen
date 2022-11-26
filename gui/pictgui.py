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
# import pyqtgraph as pg
from gui.pyqtgraph_patch import pyqtgraph as pg
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

#Ui_EditColorMapWidget, QWidget = __loadUiType__(os.path.join(__module_path__,"widgets","editcolormap2.ui"))

# Ui_ItemsListDialog, QDialog = __loadUiType__(os.path.join(__module_path__,"itemslistdialog.ui"))

# Ui_LinearRangeMappingWidget, QWidget = __loadUiType__(os.path.join(__module_path__, "linearrangemappingwidget.ui"))

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
            
    #pass

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
    signal_Finished = pyqtSignal(name="signal_Finished")
    sig_error = pyqtSignal(tuple, name="sig_error")
    signal_Result = pyqtSignal(object, name="signal_Result")
    

    
class GuiWorker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(GuiWorker, self).__init__()
        
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        
        self.signals = GuiWorkerSignals()
        
        self.result = None
        
    @pyqtSlot()
    def run(self):
        try:
            self.result = self.fn(*self.args, **self.kwargs)
            self.signals.signal_Result.emit(self.result)  # Return the result of the processing
            
        except:
            traceback.print_exc()

            exc_type, value = sys.exc_info()[:2]
            
            self.signals.sig_error.emit((exc_type, value, traceback.format_exc()))
            
        else:
            #self.signals.signal_Result.emit(self.result)  # Return the result of the processing
            self.signals.signal_Finished.emit()  # Done
            
        finally:
            self.signals.signal_Finished.emit()  # Done

class ProgressWorkerSignals(QtCore.QObject):
    """See Martin Fitzpatrick's tutorial on Multithreading PyQt applications with QThreadPool 
    https://martinfitzpatrick.name/article/multithreading-pyqt-applications-with-qthreadpool/
    
    Defines the signals available from a running worker thread.

    Supported signals are:

    signal_Finished
        No data

    sig_error
        `tuple` (exctype, value, traceback.format_exc() )

    signal_Result
        `object` data returned from processing, anything

    signal_Progress
        `int` indicating % progress

    """
    
    signal_Finished = pyqtSignal()
    sig_error = pyqtSignal(tuple)
    signal_Result = pyqtSignal(object)
    signal_Progress = pyqtSignal(int)
    signal_setMaximum = pyqtSignal(int)
    signal_Canceled = pyqtSignal()
    
class ProgressRunnableWorker(QtCore.QRunnable):
    """
    ProgressRunnableWorker thread

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
    
    NOTE: because this inherits from a QRunnable, the operation cannot be aborted

    """
    # canceled = pyqtSignal(name="canceled")
    
    def __init__(self, fn, progressDialog, *args, **kwargs):
        """
        fn: callable
        progressDialog: QtWidgets.QProgressDialog
        *args, **kwargs are passed to fn
        """
        super(ProgressRunnableWorker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = ProgressWorkerSignals()
        self.pd = progressDialog
        self.setAutoDelete(True)
        
        if isinstance(self.pd, QtWidgets.QProgressDialog):
            self.pd.setValue(0)
            # self.pd.canceled.connect(self.slot_canceled)
            self.signals.signal_Progress.connect(self.pd.setValue)
            self.signals.signal_setMaximum.connect(self.pd.setMaximum)
            self.kwargs['progressSignal'] = self.signals.signal_Progress
            self.kwargs["setMaxSignal"] = self.signals.signal_setMaximum
            self.kwargs["progressUI"] = self.pd
            
        #else:
            #self.pd = None

        # Add the callback to our kwargs
        
        #print("ProgressRunnableWorker fn args", self.args)
        
    # @pyqtSlot()
    # def slot_canceled(self):
    #     self.signals.signal_Canceled(emit)

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
            self.signals.signal_Result.emit(result)  # Return the result of the processing
            
        finally:
            self.signals.signal_Finished.emit()  # Done
            
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

class ProgressThreadWorker(QtCore.QObject):
    def __init__(self, fn, /, progressDialog=None, *args, **kwargs):
        """
        fn: callable
        progressDialog: QtWidgets.QProgressDialog
        *args, **kwargs are passed to fn
        """
        super(ProgressThreadWorker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = ProgressWorkerSignals()
        self.pd = None
        self.poller = QtCore.QTimer(self)
        # self.poller.setInterval(200)
        self.poller.timeout.connect(self.progress_poll)
        
        if isinstance(progressDialog, QtWidgets.QProgressDialog):
            self.setProgressDialog(progressDialog)
            # self.pd = progressDialog
            # self.pd.setValue(0)
            # self.pd.canceled.connect(self.slot_canceled)
            # self.signals.signal_Progress.connect(self.pd.setValue)
            # self.signals.signal_setMaximum.connect(self.pd.setMaximum)
            # self.kwargs['progressSignal'] = self.signals.signal_Progress
            # self.kwargs["setMaxSignal"] = self.signals.signal_setMaximum
            # self.kwargs["progressUI"] = self.pd
        # else:
        #     self.pd = None
            
        print(f"{self.__class__.__name__}.__init__(fn = {fn}, progressDialog = {progressDialog})")
            
    def setProgressDialog(self, progressDialog:QtWidgets.QProgressDialog):
        if isinstance(progressDialog, QtWidgets.QProgressDialog):
            self.pd = progressDialog
            self.pd.setValue(0)
            # slot_canceled emits signal_Canceled
            self.pd.canceled.connect(self.slot_canceled)
            self.signals.signal_Progress.connect(self.pd.setValue)
            self.signals.signal_setMaximum.connect(self.pd.setMaximum)
            self.signals.signal_Finished.connect(self.pd.reset)
            self.kwargs['progressSignal'] = self.signals.signal_Progress
            self.kwargs["setMaxSignal"] = self.signals.signal_setMaximum
            self.kwargs["progressUI"] = self.pd
            self.kwargs["finished"] = self.signals.signal_Finished
        else:
            self.pd is None
            
    @property
    def progressDialog(self):
        return self.pd
    
    @pyqtSlot()
    def slot_canceled(self):
        print(f"{self.__class__.__name__}.slot_canceled")
        self.signals.signal_Canceled.emit()
        
    @pyqtSlot()
    def progress_poll(self):
        if isinstance(self.pd, QtWidgets.QProgressDialog):
            if self.pd.wasCanceled():
                self.signals.signal_Canceled.emit()
            
    @pyqtSlot()
    def run(self):
        print(f"{self.__class__.__name__}.run()")
        self.poller.start(200)
        try:
            result = self.fn(*self.args, **self.kwargs)
            
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sig_error.emit((exctype, value, traceback.format_exc()))
            
        else:
            self.signals.signal_Result.emit(result)  # Return the result of the processing
            
        finally:
            self.signals.signal_Finished.emit()  # Done
        
        
class ProgressThreadController(QtCore.QObject):
    sig_start = pyqtSignal(name="sig_start")
    sig_ready = pyqtSignal(object, name="sig_ready")
    
    def __init__(self, fn, /, progressDialog=None, *args, **kwargs):
        super().__init__()
        print(f"{self.__class__.__name__}.__init__(fn={fn}, progressDialog = {progressDialog})")
        self.workerThread = QtCore.QThread()
        self.worker = ProgressThreadWorker(fn, progressDialog, *args, **kwargs)
        self.worker.moveToThread(self.workerThread)
        self.workerThread.finished.connect(self.worker.deleteLater)
        self.sig_start.connect(self.worker.run)
        self.worker.signals.signal_Result.connect(self.handleResult)
        self.worker.signals.signal_Canceled.connect(self.abort)
        self.workerThread.start()
        
    def __del__(self):
        self.workerThread.quit()
        self.workerThread.wait()
        # super().__del__()
        
    def setProgressDialog(self, progressDialog):
        if isinstance(progressDialog, QtWidgets.QProgressDialog):
            self.worker.setProgressDialog(progressDialog)
            
    @pyqtSlot(object)
    def handleResult(self, result:object):
        if isinstance(self.worker.progressDialog, QtWidgets.QProgressDialog):
            self.worker.progressDialog.setValue(self.worker.progressDialog.maximum())
        self.sig_ready.emit(result)
        
    @pyqtSlot()
    def abort(self):
        print(f"{self.__class__.__name__}.abort")
        self.sig_ready.emit(None)
        
        
        
