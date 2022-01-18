2021-04-19 11:13:16
pictgui graphics primitives:
    frame navigation sluggish (on slower machines)
    finish simplifying PlanarGraphics API especially for frame-state associations
    in 3D data, and in particular for Path objects.
    
protocoleditordialog.py:
    finalize the code!
    
triggerdetectgui.py:
    finalize integration of protocoleditordialog
    
    
CaTanalysis, LSCaTWindow:
    1) creating a vertical cursor in the line scan image does NOT also create a 
    linked point cursor in the XY raster image (which should be contrained to 
    the scanline ROI)
    
    2) link 'Detect' button in the protocols tab to the TriggerDetectDialog gui.
    
    3) use protocoleditordialog (as embedded widget)
    
    4) importing Prairieview: no analysis channels set (when options are not 
    supplied to the importer)
    
ephys:
    ephys.py:
        electrophysiology data parser - also useful for ScanData, CaTanalysis etc
    membrane.py:
        AHP code
    finalize:
        AP analysis GUI (functions in membrane)
        LTP analysis GUI
    
