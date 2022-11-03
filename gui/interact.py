"""A collection of functions to prompt user input using GUI
"""
import typing, collections, dataclasses
import pyqtgraph as pg # used throughout - based on Qt5 
pg.Qt.lib = "PyQt5" # pre-empt the use of PyQt5
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType
from . import quickdialog as qd
from gui.pictgui import ItemsListDialog


class _InputSpec():
    """Encapsulates arguments to interact.getInput(...)
    """
    __slots__ = ("_default", "_mytype")
    
    def __init__(self, mytype=type(dataclasses.MISSING), default = dataclasses.MISSING):
        if isinstance(mytype, type):
            if mytype in (type(dataclasses.MISSING), type(None)): # type not specified
                if default not in (dataclasses.MISSING, None): # get it from default's type
                    mytype = type(default)
                    
            if default in (dataclasses.MISSING, None) and mytype not in (type(dataclasses.MISSING), type(None)):
                # mytype specified, but no default given -> instantiate it from mytype
                default = mytype()
                
            elif not isinstance(default, mytype): # consistency/sanity check
                raise TypeError(f"default expected to be a {type.__name__}; got {type(default).__name__} instead")
            
        # else:
        #     mytype = type(default)

        self._default=default
        self._mytype=mytype
        
    @property
    def type(self):
        return self._mytype
    
    @property
    def default(self):
        return self._default
                

def selectWSData(*args, title="", single=True, asDict=False, **kwargs):
    """Selection of workspace variables from a list
    """
    from core.workspacefunctions import (lsvars, getvarsbytype, user_workspace)
    
    glob = kwargs.pop("glob", True)
    
    ws = kwargs.pop("ws", user_workspace())
    
    #ws = user_workspace()
    user_ns_visible = dict([(k,v) for k,v in ws.items() if not k.startswith("_") and k not in ws["mainWindow"].workspaceModel.user_ns_hidden])
    
    name_vars = lsvars(*args, glob=True, ws=user_ns_visible, **kwargs)
    
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
        if asDict:
            return dict((i, ws[i]) for i in dialog.selectedItemsText)
        
        return tuple(ws[i] for i in dialog.selectedItemsText)
        
    return dict() if asDict else list()


def getInputs(**kwargs):
    """Calls 'getInput' with a prompt mapping created from key/value pairs
    Returns a list.
    
    Typical use:
    
    a, b, c = getInputs(a=1, b=2, c=3)
    """
    
    return getInput(kwargs, mapping=False)

def packInputs(**kwargs):
    """Verison of getInputs that returns a dict
    Typical use:
    
    result = getInputs(a=1, b=2, c=3)
    
    resut
    {'a': 1, 'b': 2, 'c': 3}
    
    """
    
    return getInput(kwargs, mapping=True)

def getInput(prompts:dict, mapping:bool=False):
    """Opens a quick dialog to prompt user input for integer, float and string values
    
    Parameters:
    -----------
    prompts: a dict with str keys (the name of the prompted variable) mapped to
        either:
            an _InputSpec that enapsulates the default prompt value and type of
                the value; the latter is used to determine what kind of GUI input
                field will be used in the dialog as a prompt for the variable.
                
        any object: the object value is the default, and the object type determines
            what kind of gui input field should be used 
                
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
    dlg = qd.QuickDialog(title="Input values")
    if not isinstance(prompts, dict):
        raise TypeError(f"'prompts' expected to be a dict; got {type(prompts).__name__} instead")
    
    prompt_widgets = dict()
    
    group = qd.VDialogGroup(dlg)
    
    for k,v in prompts.items():
        if isinstance(v, _InputSpec):
            def_val  = v.default
            v_type = v.type
            
        elif isinstance(v, type):
            v_type = type
            def_val = _InputSpec(v).default
            
        else:
            def_val = v
            v_type = type(v)
        
        def_text = str(def_val) if def_val not in (dataclasses.MISSING, None) else ""
        
        label = QtWidgets.QLabel(f"{k}:", group)
        group.addWidget(label)
        group.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        
        if v_type == int:
            w = qd.IntegerInput(group,"")
            w.setValue(def_text)
            
        elif v_type == float:
            w = qd.FloatInput(group, "")
            w.setValue(def_text)
            
        elif v_type == str:
            w = qd.StringInput(group, "")
            w.setText(def_text)
            
        elif v_type == bool:
            w = qd.CheckBox(group, "")
            w.setCheckState(QtCore.Qt.Checked if def_val is True else QtCore.Qt.Unchecked)
            
        else:
            raise TypeError(f"{v_type} types are not yet supported")
        
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
    
    
    
    
    
