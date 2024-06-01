#
# TODO Code linking to ScanImage ?!?

# -*- coding: utf-8 -*-
"""Import routines for PrairieView data
"""
#### BEGIN core python modules
import os, sys, traceback, warnings, datetime, time, mimetypes, io, typing
from enum import Enum, IntEnum #, unique
from collections import OrderedDict
import concurrent.futures
import threading
#import xml
#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import quantities as pq
import neo
import vigra
from qtpy import (QtCore, QtWidgets, QtGui,)
from qtpy.QtCore import Signal, Slot
#from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
# from PyQt5 import (QtCore, QtWidgets, QtGui,)
# from PyQt5.QtCore import Signal, Slot
#### END 3rd party modules

#### BEGIN scipyen modules
from core.utilities import safeWrapper
from core.traitcontainers import DataBag
from core.triggerevent import (TriggerEvent, TriggerEventType, )
from core.triggerprotocols import (TriggerProtocol,
                                   auto_detect_trigger_protocols,
                                   embed_trigger_protocol, 
                                   embed_trigger_event,
                                   parse_trigger_protocols,
                                   remove_trigger_protocol,
                                   parse_trigger_protocols)

from core.neoutils import (concatenate_blocks, concatenate_signals,)

import core.xmlutils as xmlutils
import core.strutils as strutils
import core.datatypes  

import iolib.pictio as pio

from gui import resources_rc # as resources_rc
# from gui import icons_rc
from gui import quickdialog as qd
from gui.triggerdetectgui import TriggerDetectDialog, TriggerDetectWidget
from gui.protocoleditordialog import ProtocolEditorDialog
from gui import pictgui as pgui
from gui.workspacegui import WorkspaceGuiMixin
import gui.signalviewer as sv

from imaging import (imageprocessing as imgp, axisutils, axiscalibration,)
from imaging.scandata import (ScanData, ScanDataOptions, scanDataOptions,)

from imaging.vigrautils import (concatenateImages, insertAxis)

from imaging.axisutils import (axisTypeFromString, axisTypeName, 
                               axisTypeSymbol, axisTypeUnits,)

from imaging.axiscalibration import (AxesCalibration, 
                                     CalibrationData, 
                                     ChannelCalibrationData, 
                                     AxisCalibrationData)

import ephys.ephys as ephys

#### END scipyen modules

__module_path__ = os.path.abspath(os.path.dirname(__file__))
