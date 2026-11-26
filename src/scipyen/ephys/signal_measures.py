# $Id: signal_measures.py $
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
#### BEGIN core python modules
import os
# import sys
import collections
import traceback
import datetime
import numbers
import inspect
import itertools
import functools
from functools import singledispatch
import warnings
import typing
import types
# import difflib
# import re as _re
# from enum import Enum, IntEnum
# from abc import ABC
import dataclasses
from dataclasses import (dataclass, MISSING)
#### END core python modules

#### BEGIN 3rd party modules
# try:
#     import mypy
# except:
#     print("Please install mypy first")
#     raise
import numpy as np
import quantities as pq
import neo
from neo.core.objectlist import ObjectList as NeoObjectList
import h5py
import pandas as pd
from tribool import Tribool
from treelib import (Tree, Node)
# import pyabf

from scipy import optimize

# import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
# __has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    # import PySide6
    # from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    # from qtpy import sip # noqa
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    # __has_sip__ = True


import matplotlib as mpl
import psygnal
# from core.pyqtgraph_patch import pyqtgraph as pg
#### END 3rd party modules

#### BEGIN pict.core modules
from core.basescipyen import BaseScipyenData
# from core.traitcontainers import DataBag
from core.prog import (safewrapper, with_doc, get_func_param_types, scipywarn, timefunc)
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import (DataZone, Interval)
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import TriggerProtocol, TriggerProtocolList
from core.typeenum import TypeEnum
from core.scipyendataclasses import (Episode, Schedule, ScipyenDataclass)
from core import datatypes
from core.datatypes import (check_type, type2str)
from core import workspacefunctions
from core import signalprocessing as sigp
from core import utilities
from core import neoutils
from core import strutils
from core import curvefitting as crvf
from core import models as models

from core.utilities import (reverse_mapping_lookup,
                            get_index_for_seq,
                            sp_set_loc,
                            normalized_index,
                            unique,
                            GeneralIndexType)

from core.neoutils import (get_index_of_named_signal, concatenate_blocks)
from core import scipyen_quantities as scq
from core.scipyen_quantities import (unitsConvertible, checkTimeUnits,
                             checkElectricalCurrentUnits,
                             checkElectricalPotentialUnits,
                             checkRescale)
import core.pyabfbridge as pab

from core.deferredmeasures import * # noqa

from gui.cursors import (DataCursor, SignalCursor, SignalCursorTypes)

from ephys.ephys_protocol import ElectrophysiologyProtocol

#from .patchneo import neo


#### END pict.core modules

LOCATOR_TYPES = (SignalCursor, DataCursor, neo.Epoch, DataZone, Interval, type(MISSING))

LocatorTypeVar = typing.TypeVar('LocatorTypeVar', *LOCATOR_TYPES)

LOCATOR_SEQUENCE = typing.Sequence[LocatorTypeVar]

REGULAR_SIGNAL_TYPES = (neo.AnalogSignal, DataSignal)
IRREGULAR_SIGNAL_TYPES = (neo.IrregularlySampledSignal, IrregularlySampledDataSignal)
