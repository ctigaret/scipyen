#### BEGIN core python modules
from __future__ import print_function

import os, inspect, warnings, traceback, datetime, typing
#### END core python modules

#### BEGIN 3rd party modules
import pandas as pd
import quantities as pq
#import xarray as xa
import numpy as np
import neo
import vigra

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.pylab as plb
import matplotlib.mlab as mlb
#### END 3rd party modules

#### BEGIN pict.core modules
#from core.patchneo import *
import core.datatypes as dt

import core.strutils as strutils
from core.strutils import str2float

from core.prog import (safeWrapper, )

from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType)
from core.triggerprotocols import TriggerProtocol
from core.datazone import DataZone

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)
from core.datatypes import array_slice

#### END pict.core modules

#### BEGIN pict.gui modules
# from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
# from . import quickdialog
from gui import resources_rc
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

class MetaHeaderView(QtWidgets.QHeaderView):
    #Re: How to edit Horizontal Header Item in QTableWidget, on QtCentre
    # WARNING do not use yet
    def __init__(self,orientation,parent=None):
        super(MetaHeaderView, self).__init__(orientation,parent)
        self.setMovable(True)
        self.setClickable(True)
        # This block sets up the edit line by making setting the parent
        # to the Headers Viewport.
        self.line = QtWidgets.QLineEdit(parent=self.viewport())  #Create
        self.line.setAlignment(QtCore.Qt.AlignTop) # Set the Alignmnet
        self.line.setHidden(True) # Hide it till its needed
        # This is needed because I am having a werid issue that I believe has
        # to do with it losing focus after editing is done.
        self.line.blockSignals(True)
        self.sectionedit = 0
        # Connects to double click
        self.sectionDoubleClicked.connect(self.editHeader)
        self.line.editingFinished.connect(self.doneEditing)

    def doneEditing(self):
        # This block signals needs to happen first otherwise I have lose focus
        # problems again when there are no rows
        self.line.blockSignals(True)
        self.line.setHidden(True)
        oldname = self.model().dataset.field(self.sectionedit)
        newname = str(self.line.text())
        self.model().dataset.changeFieldName(oldname, newname)
        self.line.setText('')
        self.setCurrentIndex(QtCore.QModelIndex())

    def editHeader(self,section):
        # This block sets up the geometry for the line edit
        edit_geometry = self.line.geometry()
        edit_geometry.setWidth(self.sectionSize(section))
        edit_geometry.moveLeft(self.sectionViewportPosition(section))
        self.line.setGeometry(edit_geometry)

        self.line.setText(self.model().dataset.field(section).name)
        self.line.setHidden(False) # Make it visiable
        self.line.blockSignals(False) # Let it send signals
        self.line.setFocus()
        self.line.selectAll()
        self.sectionedit = section

