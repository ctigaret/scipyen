#### BEGIN core python modules
from __future__ import print_function

import os, warnings, types, traceback, itertools, inspect, dataclasses, numbers
from collections import deque
from dataclasses import MISSING
import math
#### END core python modules

#### BEGIN 3rd party modules
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot, QEnum, Property
# from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtCore import Signal, Slot, QEnum, Q_FLAGS, Property

from pyqtgraph import (DataTreeWidget, TableWidget, )
#from pyqtgraph.widgets.TableWidget import _defersort

import neo
import quantities as pq
import numpy as np
import pandas as pd
#### END 3rd party modules

#### BEGIN pict.core modules
import core.datatypes  

import imaging.axiscalibration
from imaging.axiscalibration import AxesCalibration

import imaging.scandata
from imaging.scandata import (ScanData, AnalysisUnit)

from core.triggerprotocols import TriggerProtocol
from core.triggerevent import (TriggerEvent, TriggerEventType)

import core.datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)

from core import xmlutils, strutils

from core.workspacefunctions import validate_varname

#from core.utilities import (get_nested_value, set_nested_value, counter_suffix, )

from core.utilities import NestedFinder

from core.prog import (safeWrapper, safeGUIWrapper, )

from core.traitcontainers import (DataBag, DataBagTraitsObserver,)

# from gui.tableeditor import (TableEditorWidget, TabularDataModel,)

class SimpleTableWidget(TableWidget): # TableWidget imported from pyqtgraph
    """Another simple table widget, which allows zero-based row/column indices.
    
    gui.widgets.tableeditorwidget.TableEditorWidget does that too, and more, but is too slow. 
    
    In contrast, pyqtgraph's TableWidget is much more efficient
    
    """
    def __init__(self, *args, natural_row_index=False, natural_col_index=False, **kwds):
        self._pythonic_col_index = not natural_col_index
        self._pythonic_row_index = not natural_row_index
        super().__init__(*args, **kwds)
        
    def setData(self, data):
        super().setData(data)
        #if isinstance(data, neo.core.dataobject.DataObject):
            
        if isinstance(data, (np.ndarray, tuple, list, deque)):
            if self._pythonic_col_index:
                self.setHorizontalHeaderLabels(["%d"%i for i in range(self.columnCount())])
                
            if self._pythonic_row_index:
                self.setVerticalHeaderLabels(["%d"%i for i in range(self.rowCount())])
                
        elif isinstance(data, pd.Series):
            self.setHorizontalHeaderLabels(["%s"%i for i in data.index])
            self.setVerticalHeaderLabels([data.name])
            
        elif isinstance(data, pd.DataFrame):
            self.setHorizontalHeaderLabels(["%s"%i for i in data.index])
            self.setVerticalHeaderLabels([data.columns])
            
        elif isinstance(data, pd.Index):
            self.setHorizontalHeaderLabels(["%s"%i for i in data])
            
        
    def iterFirstAxis(self, data):
        """Overrides TableWidget.iterFirstAxis.
        
        Avoid exceptions when data is a dimesionless array.
        
        In the original TableWidget from pyqtgraph this method fails when data 
        is a dimesionless np.ndarray (i.e. with empty shape and ndim = 0).
        
        This kind of arrays unfortunately can occur when creating a numpy
        array (either directly in the numpy library, or in the python Quantities
        library):
        
        Example 1 - using python quantities:
        ------------------------------------
        
        In: import quantities as pq
        
        In: a = 1*pq.s
        
        In: a
        Out: array(1.)*s
        
        In: a.shape
        Out: ()
        
        In: a.ndim
        Out: 0
        
        In: a[0]
        IndexError: too many indices for array: array is 0-dimensional, but 1 were indexed
        
        Example 2 - directly creating a numpy array:
        --------------------------------------------
        
        In: b = np.array(1)
        
        In: b
        Out: array(1)
        
        In: b.shape
        Out: ()
        
        In: b.ndim
        Out: 0
        
        In: b[0]
        IndexError: too many indices for array: array is 0-dimensional, but 1 were indexed
        
        This will cause self.iterFirstAxis(a) to raise 
        IndexError: tuple index out of range
        
        
        HOWEVER, the value of the unique element of the array can be retrieved
        by using its "take" method:
        
        In: a.take(0)
        Out: 1.0
        
        In: b.take(0)
        Out: 1

        
        """
        if len(data.shape) == 0 or data.ndim == 0:
            yield(data.take(0))
            
        else:
            for i in range(data.shape[0]):
                yield data[i]
