import typing, warnings, math
from core.utilities import get_least_pwr10
from PyQt5 import (QtCore, QtWidgets, QtGui)
from gui.painting_shared import (FontStyleType, standardQtFontStyles, 
                                 FontWeightType, standardQtFontWeights)

import quantities as pq

class DoubleSpinBox(QtWidgets.QDoubleSpinBox):
    # TODO 2022-10-31 16:43:09 maybe 
    def __init__(parent=None):
        super().__init__(self, parent=parent)
        
    
