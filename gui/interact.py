"""A collection of functions to prompt user input using GUI
"""
import typing
import pyqtgraph as pg # used throughout - based on Qt5 
pg.Qt.lib = "PyQt5" # pre-empt the use of PyQt5
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType
from . import quickdialog as qd
from gui.pictgui import ItemsListDialog

def selectWSData(*args, glob:bool=True, title="", single=True):
    from core.workspacefunctions import (lsvars, getvarsbytype, user_workspace)
    
    ws = user_workspace()
    user_ns_visible = dict([(k,v) for k,v in ws.items() if not k.startswith("_") and k not in ws["mainWindow"].workspaceModel.user_ns_hidden])
    
    name_vars = lsvars(*args, glob=glob, ws=user_ns_visible)
    
    if len(name_vars) == 0:
        return list()
        
    name_list = sorted([name for name in name_vars])
        
    selectionMode = QtWidgets.QAbstractItemView.SingleSelection if single else QtWidgets.QAbstractItemView.ExtendedSelection
    
    if len(title.strip()):
        dtitle = f"Select {title}"
    else:
        dtitle = "Select variable in workspace"
    
    dialog = ItemsListDialog(title=dtitle, itemsList = name_list,
                            selectmode = selectionMode)
        
    ans = dialog.exec()
    
    if ans == QtWidgets.QDialog.Accepted:
        return tuple(ws[i] for i in dialog.selectedItemsText)
        
    return list()
    

def getInput(prompts:dict,
             mapping:bool=False):
    """Opens a quick dialog to prompt user input for integer, float and string values
    
    Parameters:
    -----------
    prompts: a dict with str keys (the name of the prompted variable) mapped to
        dicts with keys: 
            "type" mapped to one of the supported types: int, float, str
            "default" mapped to a default value (which is expected to be an instance
                of the acceptable types in "type" or None)
                
    mapping:bool, optional default is False
    
    Returns:
    --------
    
    A tuple (when 'mapping' is False) else a dict.
    
    Returns None if the dialog was cancelled.
    
    The tuple contains object values in the same order as the keys in 'prompts'.
    
    The dict maps the keys in 'prompts' to the object values.
    
    In either case, the object values are those set in by interaction with the 
    diaog.
    
    """
    dlg = qd.QuickDialog(title="Input")
    if not isinstance(prompts, dict):
        raise TypeError(f"'prompts' expected to be a dict; got {type(prompts).__name__} instead")
    
    prompt_widgets = dict()
    
    group = qd.VDialogGroup(dlg)
    
    for k,v in prompts.items():
        if not isinstance(v, dict):
            raise TypeError(f"the 'prompts' dictionary expected to contain dict objects; got {type(v).__name__} instead")
        
        if any(s not in v for s in ("type", "default")):
            raise ValueError("inner dictionary missing 'type' and 'default' keys")
        
        #if isinstance(v["type"], (tuple, list)):
            #if all(isinstance(vv, type) for vv in v["type"]):
                #types = v["type"]
            #else:            
                #raise TypeError("'types' expected to contain Python type objects")
        
        #el
        if not isinstance(v["type"], type) or v["type"] not in (int, float, str, bool):
            raise TypeError(f"'type' must be maped to int, float or str")
            
        if v["default"] is not None:
            if not isinstance(v["default"], v["type"]):
                raise TypeError(f"specified default has wrong type {type(v['default'].__name__)}; expecting None or {v['type'].__name__}")
            
        def_text = str(v["default"]) if v["default"] is not None else ""
        
        label = QtWidgets.QLabel(f"{k}:", group)
        group.addWidget(label)
        group.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        
        if v["type"] == int:
            w = qd.IntegerInput(group,"")
            w.setValue(def_text)
            
        elif v["type"] == float:
            w = qd.FloatInput(group, "")
            w.setValue(def_text)
            
        elif v["type"] == str:
            w = qd.StringInput(group, "")
            w.setText(def_text)
            
        elif v["type"] == bool:
            w = qd.CheckBox(group, "")
            w.setCheckState(QtCore.Qt.Checked if v["default"] is True else QtCore.Qt.Unchecked)
            
        else:
            raise TypeError(f"{types[0]} types are not yet supported")
        
        if hasattr(w, "variable"):
            w.variable.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        else:
            w.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        group.addWidget(w, stretch=1)
        prompt_widgets[k] = w
            
    dlg.addWidget(group, stretch=1)
        
    dlg.resize(-1, -1)
        
    dlgret = dlg.exec()
    
    if dlgret:
        ret = tuple(w.text() if isinstance(w, qd.StringInput) else w.selection() if isinstance(w, qd.CheckBox) else w.value() for w in prompt_widgets.values())
        if mapping:
            return dict(zip(prompts.keys(), ret))
        return ret
    
    
    
    