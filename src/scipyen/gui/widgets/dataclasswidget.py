# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r""" Editing dataclasses fields - options to explore:
1) use a Tree widget (as in dataViewer), make it editable;
    • The data model would be a (temporary) dict — a copy of the dataclass
    instance fields created by calling dataclasses.asdict(…)
    • editing fields:
        ∘ needs a proxy editor widget for the various data types, with an appropriate
            "delegate" as per Qt's document/view model
        ∘ widgets for PODs:             
            ▷ str: QLineEdit, 
            ▷ int: QSPinBox, 
            ▷ float: QDoubleSpinBox, 
            ▷ bool: QCheckBox
            ▷ complex: TODO -> see the model for QuantityChooserWidget, needs 
                two QDoubleSpinBox instances side by side (real & imaginary)
        ∘ widgets for special data types — might need to work with a subclass of 
                                            abstract item delegate
            ▷ pq.Quantity:  gui.widgets.small_widgets.QuantitySpinBox for editing
                            the value of a scalar quantity
                            gui.widgets.small_widgets.QuantityChooserWidget for
                            editing the value and units of a scalar quantity
                            (combines a QuantitySpinBoxwith a combobox)
                            
                            NOTE: At the moment, these do not have corresponding 
                            subclasses of QAbstractItemDelegate, therefore cannot
                            be used with instances of QAbstractItemView subclasses
                            yet (see Qt's model/view architecture).
                            
            ▷ datetime.datetime, datetime.time, datetime.timedelta: TODO
                -> contemplate subclassing, or composing with, a QDateTimeEdit, 
                QDateEdit, QTimeEdit; maybe also QCalendarWidget
            ▷ Enum, TypeEnum: TODO -> subclass QComboBox
                -> see e.g. classes in gui.widgets.stylewidgets:
                BrushComboBox & BrushComboDelegate
                PenComboBox & PenComboDelegate
            ▷ type, numpy.dtype, pandas.dtype TODO -> subclass QComboBox
                -> see e.g. classes in gui.widgets.stylewidgets:
                BrushComboBox & BrushComboDelegate
                PenComboBox & PenComboDelegate
            ▷ numpy array, pandas dataframe -> 
                -> there exists a TableEditor widget, which will need upgrading
                with item model delegates for dtype and value (see above)
            ▷ numpy array, vigra array ->
                -> there exists gui.imageviewer.ImageViewer but without editing
                capabilities - consider this
            ▷ ScipyenDataclass -> use a QTreeView (i.e. recursion) as sketched
                above;
                
2) QDataWidgetMapper
• would require a custom item model based on the dataclass field and field types
(CAUTION with descriptor types, here)
• for specific python data types would also need custom widgets (see above)
"""
import sys, os, typing
import qtpy as QtAPI
QtAPI.API = os.environ["QT_API"]
if os.environ["QT_API"] == "pyside6":
    import PySide6
    QtAPI = PySide6
else:
    pass
from qtpy import QtCore, QtGui, QtWidgets, QtSvg, QtNetwork, sip
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safewrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

import math, datetime
import numpy as np
import quantities as pq
from core import scipyen_quantities as scq
from core import strutils
from core import datatypes as dt
import pandas as pd

# from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget
# from gui.textviewer import TextViewer


class DataClassWidget(QtWidgets.QWidget):
    # TODO: 2024-12-11 09:46:03 work in progress
    def __init__(self, dataparent=None):
        super().__init__(parent=parent)
