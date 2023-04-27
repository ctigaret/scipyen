#import os, inspect, mimetypes
##print("gui/__init__.py %s" % __file__)
##print("gui/__init__.py %s" % os.path.dirname(__file__))
#import PyQt5
#from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
#from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
#from PyQt5.uic import loadUiType as __loadUiType__ 

##dw = os.scandir(os.path.dirname(__file__))

#from matplotlib.figure import Figure

#py_source_files = [os.path.join(os.path.dirname(__file__), e.name) for e in os.scandir(os.path.dirname(__file__)) if e.is_file() and 'text/x-python' in mimetypes.guess_type(e.name) and "_ui" not in e.name]

import matplotlib as mpl

from .scipyenviewer import (ScipyenViewer, ScipyenFrameViewer,)
from .dictviewer import DataViewer
from .matrixviewer import MatrixViewer
from .imageviewer import ImageViewer
from .signalviewer import SignalViewer
from .tableeditor import TableEditor
from .textviewer import TextViewer
from .xmlviewer import XMLViewer
from .widgets.breadcrumb_nav import Navigator

# NOTE: 2022-12-25 23:19:16
# plugins frameworm takes care of this
# gui_viewers = {DataViewer, MatrixViewer, ImageViewer, SignalViewer, 
#                TableEditor, TextViewer, XMLViewer}
#gui_viewers = [ScipyenViewer, ScipyenFrameViewer, DataViewer, MatrixViewer, ImageViewer, SignalViewer, 
               #TableEditor, TextViewer, XMLViewer]
