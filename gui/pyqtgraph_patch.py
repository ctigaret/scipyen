import traceback

import pyqtgraph

pyqtgraph.Qt.lib = "PyQt5" # pre-empt the use of PyQt5
pyqtgraph.setConfigOptions(background="w", foreground="k", editorCommand="kate")

def setViewList(obj, views):
    names = ['']
    obj.viewMap.clear()
    
    ## generate list of views to show in the link combo
    for v in views:
        name = v.name
        if name is None:  ## unnamed views do not show up in the view list (although they are linkable)
            continue
        names.append(name)
        obj.viewMap[name] = v
        
    for i in [0,1]:
        # NOTE: 2022-11-21 11:01:18 CT
        #### BEGIN CT 
        try:
            c = obj.ctrl[i].linkCombo
            current = c.currentText()
            c.blockSignals(True)
            changed = True
            try:
                c.clear()
                for name in names:
                    c.addItem(name)
                    if name == current:
                        changed = False
                        c.setCurrentIndex(c.count()-1)
            finally:
                c.blockSignals(False)
                
            if changed:
                c.setCurrentIndex(0)
                c.currentIndexChanged.emit(c.currentIndex())
        except RuntimeError:
            print(f"RuntimeError in {obj.__class__.__name__}")
            traceback.print_exc()
            continue
        #### END CT

setattr(pyqtgraph.ViewBox, "setViewList", setViewList)



