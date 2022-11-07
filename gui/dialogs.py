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

class GenericMappingDialog(qd.QuickDialog, WorkspaceGuiMixin):
    def __init__(self, mapping:typing.Optional[dict] = None, title:typing.Optional[str]="Biometrics", parent:typing.Optional[QtWidgets.QWidget]=None):
        """The key parameter is 'mapping', which is a Python dict object
        with str keys and basic python data types (number.Numbers, str).

            Each key/value pair will results in a QuickDialog custom widget (see gui.quickdialog)

            For practical purposes, there should only be a limited number of key/value
            pairs in the mapping. If this number is too large then the context where the
            dialog is used should be re-designed.
        
        """
        self._title_ = title if isinstance(title, str) and len(title.strip()) else "Biometrics"
        
        super().__init__(parent=parent, title=self._title_)
        
        if mapping is None:
            self._mapping_ = dict()
        elif isinstance(mapping, dict):
            self._mapping_ = mapping
        else:
            raise TypeError(f"Expecting a mapping (dict); instead, got {type(mapping).__name__}")
        
        widgets = self._generate_widgets()
        
        for w in widgets:
            self.addWidget(w)
        
        addEntryPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("list-add"),
                                                   "Add entry",
                                                   parent = self.buttons)
        self.buttons.layout.addWidget(addEntryPushButton)
        addEntryPushButton.clicked.connect(self._slot_addEntry)
        
        removeEntryPushButton = QtWidgets.QPushButton(QtGui.QIcon.fromTheme("list-remove"),
                                                      "Remove entry",
                                                      parent = self.buttons)
        self.buttons.layout.addWidget(removeEntryPushButton)
        removeEntryPushButton.clicked.connect(self._slot_removeEntry)
        
    def _generate_widgets(self):
        widgets = list()
        for k, v in self._mapping_:
            if isinstance(v, int):
                factory = qd.IntegerInput
            elif isinstance(v, float):
                factory = qd.FloatInput
            elif isinstance(v, complex):
                factory = qd.ComplexInput
            elif isinstance(v, str):
                factory = qd.StringInput
            else:
                raise TypeError(f"Unsupported value type {type(v).__name__} in {k}")
            
            w=factory(parent=self, label=k)
            w.setValue(v)
            widgets.append(w)
            
        return widgets
        
    def _clearWidgets(self):
        to_remove = list()
        for w in self.widgets: # this is inherited from QuickDialog; it is not the local widgets in other methods !!!
            w.setParent(None)
            self.layout.removeWidget(w)
            to_remove.append(w)
            
        for w in to_remove:
            del(self.widgets[self.widgets.index(w)])
            
        dlg.update()
        
    def _slot_addEntry(self):
        dlg = qd.QuickDialog(parent=self, title="Add entry")
        ename = qd.StringInput(parent = dlg, label="Entry name")
        etype = qd.StringInput(parent = dlg, label="Entry type")
        dlg.addWidget(ename)
        dlg.addWidget(etype)
        if dlg.exec():
            factory = None
            val_factory = None
            entry_name = strutils.str2symbol(ename.text())
            entry_type = etype.text()
            valid_types = ("complex", "float", "int", "str", "string")
            if entry_type.lower() not in valid_types:
                self.criticalMessage("Entry type:", f"Expecting one of {valid_types}; instead, got {entry_type}")
                return
            else:
                if entry_type.lower() == "complex":
                    val_factory = complex
                    factory = qd.ComplexInput
                elif entry_type.lower() == "float":
                    val_factory = float
                    factory = qd.FloatInput
                elif entry_type.lower() == "int":
                    val_factory = int
                    factory = qd.IntegerInput
                elif entry_type.lower() in ("str", "string"):
                    val_factory = str
                    factory = qd.StringInput
                    
                else:
                    return
                
            self._mapping_[entry_name] = val_factory()
            
            self._clearWidgets()
            
            widgets = self._generate_widgets()
            
            for w in widgets:
                self.addWidget(w)
                
            self.update()
    
    def _slot_removeEntry(self):
        dlg = qd.QuickDialog(parent=self, title="Remove Entry")
        entriesCombo = qd.QuickDialogComboBox(parent=dlg,label="Entry name:")
        entriesCombo.setItems([k for k in self._mapping_])
        dlg.addWidget(entriesCombo)
        
        if dlg.exec():
            entry = entriesCombo.text()
            
            del(self._mapping_[entry]
            
            self._clearWidgets()
            
            widgets = self._generate_widgets()
            
            for w in widgets:
                self.addWidget(w)
                
            self.update()
            
    def value(self):
        ret = dict((w.label, w.value()) for w in self.widgets)
            
        
            
            
                
