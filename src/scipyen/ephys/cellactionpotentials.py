# -*- coding: utf-8 -*-
"""Processing of electrophysiology signal data: detection and measurements of APs
TODO!
"""

#### BEGIN core python modules
import sys, traceback, inspect, numbers, typing, datetime, dataclasses
import warnings
import os, pickle
import collections
import itertools
import functools
import math
from copy import deepcopy
from dataclasses import (dataclass, asdict, MISSING)
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import pandas as pd
import quantities as pq

import matplotlib as mpl
import matplotlib.pyplot as plt

import scipy
from scipy import optimize, cluster

# NOTE: 2019-05-02 22:38:20 
# progress display in QtConsole seems broken - that is because QtConsole is NOT
# a terminal like your usual shell console
# try:
#     # NOTE: progressbar does not work on QtConsole
#     #from progressbar import ProgressBar, Percentage, Bar, ETA
#     
#     # and neither does this as it should !
#     from pyprog import ProgressBar
#     
#     
# except Exception as e:
#     ProgressBar = None

# NOTE: 2019-07-29 13:09:02 do I really need these 2 lines?
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, QEnum, Property
# from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
# from PyQt5.QtCore import Signal, Slot, QEnum, Q_FLAGS, Property

import neo

#### END 3rd party modules

#### BEGIN pict.core modules
import core.workspacefunctions as wf
import core.pyabfbridge as pab
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.models as models
import core.datatypes as datatypes 
import plots.plots as plots
import core.datasignal as datasignal
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import (DataZone, Interval)
from core import quantities as scq
from core.quantities import units_convertible
import core.neoutils as neoutils
# from core.utilities import unique
#import core.triggerprotocols
from core.triggerevent import (TriggerEvent, TriggerEventType)
from core.triggerprotocols import (TriggerProtocol, auto_define_trigger_events, auto_detect_trigger_protocols)
#import imaging.scandata
from imaging.scandata import ScanData

from core.prog import (safeWrapper, with_doc, scipywarn)
#from core.patchneo import *

#### END pict.core modules

#### BEGIN pict.gui modules
import gui.signalviewer as sv
import gui.cursors as cursors
from gui.cursors import SignalCursor
import gui.pictgui as pgui

#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

#### BEGIN pict.ephys modules
import ephys.ephys as ephys
#### END pict.ephys modules



