"""
    This module contains various generic GUI utilities: mostly dialogues
"""
# NOTE: 2018-04-15 10:34:03
# frameVisibility parameter in graphics object creation:
# only use it when creating a GraphicsObject from scratch; 
# ignore it when using a PlanarGraphics object (backend) to generate a GraphicsObject
# because the frames where the graphics object is visible are set by the frame-state
# associations of the backend

# NOTE: 2023-07-12 09:22:44
# these below moved to planargraphics.py
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
import sys, os, re, numbers, itertools, warnings, traceback, logging
import typing
import math
from collections import (ChainMap, namedtuple, defaultdict, OrderedDict,)
from functools import (partial, partialmethod,)
from enum import (Enum, IntEnum,)
from copy import copy


#### END core python modules

#### BEGIN 3rd party modules
from gui.pyqtgraph_patch import pyqtgraph as pg
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
#### END 3rd party modules

#### BEGIN pict.core modules
from core.traitcontainers import DataBag
from core.prog import (safeWrapper, deprecated,
                       timefunc, processtimefunc,)
from core.workspacefunctions import debug_scipyen

#### END pict.core modules

#### BEGIN pict.gui modules
from . import quickdialog
from . import resources_rc # OK this is resources_rc.py
# from . import icons_rc
# NOTE: 2023-07-12 09:23:22 are these needed here? FIXME/TODO
from .planargraphics import (Arc, ArcMove, Cubic, Cursor, Ellipse, Line, Move, Path,
                           PlanarGraphics, Point, Quad, Rect, Text, VerticalCursor,
                           HorizontalCursor, CrosshairCursor, PointCursor,
                           PlanarGraphicsType, GraphicsObjectType, GraphicsObject, 
                           __new_planar_graphic__, printQPainterPath)

#### END pict.gui modules

# FIXME 2023-07-12 09:24:29 TODO
# from BEGIN to END below move to another module (e.g. guiutils? or scipyen_colormaps?)
#### BEGIN FIXME 2023-07-12 09:24:29 TODO
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
    # TODO 2023-10-06 10:49:50
    # define this and use in objects like SignalViewer, etc
    pass

def genColorTable(cmap, ncolors=256):
    if cmap is None:
        return None
    x = np.arange(ncolors)
    cnrm = colors.Normalize(vmin=min(x), vmax=max(x))
    smap = cm.ScalarMappable(norm=cnrm, cmap=cmap)
    colortable = smap.to_rgba(x, bytes=True)
    return colortable

#### END FIXME 2023-07-12 09:24:29 TODO

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
    
class ProgressWorkerRunnable(QtCore.QRunnable):
    """
    ProgressWorkerRunnable thread

    Inherits from QRunnable to handle worker thread setup, signals and wrap-up.

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
        super(ProgressWorkerRunnable, self).__init__()
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
        
class ProgressWorkerThreaded(QtCore.QObject):
    """Wraps a worker function in a separate QThread.
        The worker function is typically executing a time-consuming loop (such
        as an iteration through some data, where each cycle involves a time-
        consuming operation).
        
        The worker instance should be `moved` to a QThread instance, and the 
        thread's `started` signal must be connected to this worker's `run` slot
        which then calls the worker function.
        
        The worker function is called from within the run 
        
    """
    def __init__(self, fn, /, progressDialog:typing.Optional[QtWidgets.QProgressDialog]=None, 
                 loopControl:typing.Optional[dict]=None, *args, **kwargs):
        """
        fn: callable
        progressDialog: QtWidgets.QProgressDialog
        loopControl:dict with a single mapping: "break" ↦ bool
        *args, **kwargs are passed to fn. When 'fn' is a (bound) instance method
            do not include the owner instance of fn (i.e., 'self') in *args.
        """
        super(ProgressWorkerThreaded, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = ProgressWorkerSignals()
        # print(f"{self.__class__.__name__}.__init__ signals = {self.signals} ")
        self.pd = None
        self.loopControl = loopControl
        self.kwargs['progressSignal'] = self.signals.signal_Progress
        self.kwargs["finishedSignal"] = self.signals.signal_Finished
        self.kwargs["canceledSignal"] = self.signals.signal_Canceled
        self.kwargs["resultSignal"] = self.signals.signal_Result
        self.kwargs["setMaxSignal"] = self.signals.signal_setMaximum
        self.kwargs["loopControl"] = self.loopControl
        
        if isinstance(progressDialog, QtWidgets.QProgressDialog):
            self.setProgressDialog(progressDialog)
            
    def setProgressDialog(self, progressDialog:QtWidgets.QProgressDialog):
        if isinstance(progressDialog, QtWidgets.QProgressDialog):
            self.pd = progressDialog
            self.pd.setValue(0)
            self.signals.signal_Progress.connect(self.progress)
            self.signals.signal_setMaximum.connect(self.pd.setMaximum)
            self.signals.signal_Finished.connect(self.pd.reset)
        else:
            self.pd is None
            
    @pyqtSlot(int)
    def progress(self, value):
        # print(f"{self.__class__.__name__}.progress({value})")
        if isinstance(self.pd, QtWidgets.QProgressDialog):
            self.pd.setValue(value)
        # else:
        #     print("\tno progress dialog!")
            
    @property
    def progressDialog(self):
        return self.pd
    
    @pyqtSlot()
    def run(self):
        # print(f"{self.__class__.__name__}.run()")
        # result = self.fn(*self.args, **self.kwargs)
        # self.signals.signal_Result.emit(result)  # Return the result of the processing
        # self.signals.signal_Finished.emit()  # Done
        try:
            result = self.fn(*self.args, **self.kwargs)
            
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sig_error.emit((exctype, value, traceback.format_exc()))
            
        else:
            self.signals.signal_Result.emit(result)  # Return the result of the processing
            self.signals.signal_Finished.emit()  # Done
            
        finally:
            self.signals.signal_Finished.emit()  # Done
        
class ProgressThreadController(QtCore.QObject):
    """The problem(s) with this approach:
• the progres dialog's timers would be stopped from another thread, thus generating
        'QObject::killTimer: Timers cannot be stopped from another thread' which 
        may crash Scipyen.
• the progress dialog cannot be moved itself to another thread, it being a member
        of the ProgressWorkerThreaded instance (although the threaded worker IS
    moved ot another thread)

"""
    sig_start = pyqtSignal(name="sig_start")
    sig_ready = pyqtSignal(object, name="sig_ready")
    
    # def __init__(self, fn, /, progressDialog=None, *args, **kwargs):
    def __init__(self, progressWorker:ProgressWorkerThreaded, /, *args, **kwargs):
        super().__init__()
        if not isinstance(progressWorker, ProgressWorkerThreaded):
            raise TypeError(f"Expecting a ProgressWorkerThreaded; instead, got a {type(progressWorker).__name__}")
        self.result = None
        
        # print(f"{self.__class__.__name__}.__init__(fn={fn}, progressDialog = {progressDialog})")
        self.workerThread = QtCore.QThread()
        self.worker = progressWorker
        # self.worker = ProgressWorkerThreaded(fn, progressDialog, *args, **kwargs)
        self.worker.moveToThread(self.workerThread)
        self.workerThread.started.connect(self.worker.run)
        self.workerThread.finished.connect(self.worker.deleteLater)
        self.worker.signals.signal_Result.connect(self.handleResult)
        if hasattr(self.worker, "pd") and isinstance(self.worker.pd, QtWidgets.QProgressDialog):
            self.worker.signals.signal_Finished.connect(self.worker.pd.reset)
        self.worker.signals.signal_Finished.connect(self.finished)
        self.worker.signals.signal_Canceled.connect(self.abort)
        self.worker.signals.signal_Progress[int].connect(self.worker.progress)
        # self.sig_start.connect(self.worker.run)
        self.workerThread.start()
        
    def __del__(self):
        self.workerThread.quit()
        self.workerThread.wait()
        # super().__del__()
        
    # def setProgressDialog(self, progressDialog):
    #     if isinstance(progressDialog, QtWidgets.QProgressDialog):
    #         self.worker.setProgressDialog(progressDialog)
            
    @pyqtSlot(object)
    def handleResult(self, result:object):
        # print(f"{self.__class__.__name__}.handleResult({result})")
        self.result = result
        if isinstance(self.worker.pd, QtWidgets.QProgressDialog):
            self.worker.pd.setValue(self.worker.progressDialog.maximum())
        self.sig_ready.emit(self.result)
        self.workerThread.quit()
        
    @pyqtSlot()
    def finished(self):
        # print(f"{self.__class__.__name__}.finished")
        self.workerThread.quit()
        
    @pyqtSlot()
    def abort(self):
        print(f"{self.__class__.__name__}.abort")
        self.sig_ready.emit(None)
        
class WorkerThread(QtCore.QThread):
    """Thread for an atomic function call in a loop.
See https://stackoverflow.com/questions/9957195/updating-gui-elements-in-multithreaded-pyqt/9964621#9964621
"""
    # sig_ready = pyqtSignal(object, name="sig_ready")
    
    def __init__(self, parent, fn:typing.Callable, /, 
                 loopControl:typing.Optional[dict]=None, *args, **kwargs):
        QtCore.QThread.__init__(self, parent)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.loopControl = loopControl
        self.signals = ProgressWorkerSignals()
        self.kwargs['progressSignal'] = self.signals.signal_Progress
        self.kwargs["finishedSignal"] = self.signals.signal_Finished
        self.kwargs["canceledSignal"] = self.signals.signal_Canceled
        self.kwargs["resultSignal"] = self.signals.signal_Result
        # self.kwargs["setMaxSignal"] = self.signals.signal_setMaximum
        self.kwargs["loopControl"] = self.loopControl
        
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.signal_Result.emit(result)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.sig_error.emit((exctype, value, traceback.format_exc()))
            
        else:
            # self.signals.signal_Result.emit(result)
            self.signals.signal_Finished.emit()
        finally:
            # self.signals.signal_Result.emit(result)
            self.signals.signal_Finished.emit()
            
