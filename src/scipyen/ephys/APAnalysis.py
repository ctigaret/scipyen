# -*- coding: utf-8 -*-
import os, typing, math, datetime, logging, traceback, warnings, inspect
from numbers import (Number, Real,)
# from itertools import chain

from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic,
                                needs_local_scope)

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot, QEnum, Property
from qtpy.uic import loadUiType as __loadUiType__
# from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtCore import Signal, Slot, QEnum, Q_FLAGS, Property
# from PyQt5.uic import loadUiType as __loadUiType__
import numpy as np
import scipy
import quantities as pq
import neo
# import pyqtgraph as pg
import pandas as pd

from iolib import pictio as pio
import core.neoutils as neoutils
import ephys.ephys as ephys
import core.workspacefunctions as wf
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.models as models

from core.datasignal import DataSignal

from core.scipyen_config import (markConfigurable, get_config_file)

from core.quantities import (arbitrary_unit, check_time_units, units_convertible,
                            unit_quantity_from_name_or_symbol, str2quantity)

# from core.datatypes import UnitTypes
from core.strutils import numbers2str
from ephys import membrane

import ephys.ephys as ephys

from core.prog import safeWrapper

from core.workspacefunctions import get_symbol_in_namespace

from gui import quickdialog as qd
import gui.scipyenviewer as scipyenviewer
from gui.scipyenviewer import ScipyenFrameViewer
import gui.signalviewer as sv
from gui.signalviewer import SignalCursor as SignalCursor
import gui.pictgui as pgui
from gui.itemslistdialog import ItemsListDialog
from gui.workspacegui import (GuiMessages, WorkspaceGuiMixin)
from gui.widgets.modelfitting_ui import ModelParametersWidget
from gui.widgets.spinboxslider import SpinBoxSlider
from gui.widgets.metadatawidget import MetaDataWidget
from gui.widgets import small_widgets
from gui.widgets.small_widgets import QuantitySpinBox
from gui import guiutils
from gui.tableeditor import TableEditor
from gui.pyqtgraph_patch import pyqtgraph as pg
from gui.pyqtgraph_symbols import (spike_Symbol, 
                                    event_Symbol, event_dn_Symbol, 
                                    event2_Symbol, event2_dn_Symbol)


import iolib.pictio as pio

