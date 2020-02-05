import os, inspect, mimetypes
#print("gui/__init__.py %s" % __file__)
#print("gui/__init__.py %s" % os.path.dirname(__file__))
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__ 

#dw = os.scandir(os.path.dirname(__file__))

from matplotlib.figure import Figure

py_source_files = [os.path.join(os.path.dirname(__file__), e.name) for e in os.scandir(os.path.dirname(__file__)) if e.is_file() and 'text/x-python' in mimetypes.guess_type(e.name) and "_ui" not in e.name]

from . import pictgui as pgui
from . import dictviewer as dv
from . import imageviewer as iv
from . import matrixviewer as matview
from . import signalviewer as sv
from . import tableeditor as te
from . import textviewer as tv
from . import xmlviewer as xv
from . import pictgui as pgui
from . import resources_rc as resources_rc
from . import quickdialog
from . import scipyenviewer



from .dictviewer import DataViewer
from .matrixviewer import MatrixViewer
from .imageviewer import ImageViewer
from .signalviewer import SignalViewer
from .tableeditor import TableEditor
from .textviewer import TextViewer
from .xmlviewer import XMLViewer

gui_viewers = [DataViewer, MatrixViewer, ImageViewer, SignalViewer, TableEditor, TextViewer, XMLViewer]
#gui_viewers = [DataViewer, MatrixViewer, ImageViewer, SignalViewer, TableEditor, TextViewer, XMLViewer, Figure]

__all__ = ["QtCore", "QtGui", "QtWidgets", "QtXmlPatterns", "QtXml", "QtSvg", 
           "pyqtSignal", "pyqtSlot", "Q_ENUMS", "Q_FLAGS", "pyqtProperty",
           "__loadUiType__", "resources_rc", 
           "dictviewer", "imageviewer", "matrixviewer", "pgui", "signalviewer", "tableeditor", "textviewer", "xmlviewer",
           "dv", "iv", "sv", "matview", "te", "tv", "xv",
           "DataViewer", "MatrixViewer", "ImageViewer", "SignalViewer", "TableEditor", "TextViewer", "XMLViewer", "gui_viewers"]

#print("scipyen.gui", __path__)
