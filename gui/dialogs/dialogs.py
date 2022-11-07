# -*- coding: utf-8 -*-
"""Some common-use dialogs for metadata in Scipyen
"""

import os, math, typing
import numpy as np
import quantities as pq
from core import quantities as scq
from core import strutils
import pandas as pd

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType

from gui import quickdialog as qd
from gui.workspacegui import (GuiMessages, WorkspaceGuiMixin)

class BiometricsDialog(qd.QuickDialog, WorkspaceGuiMixin):
    pass
