# -*- coding: utf-8 -*-
"""Initialization code to use NEURON environment with external IPython kernels.
To be used on the "host" side (i.e. executed by the external kernel)

Should NOT be imported in Scipyen or its internal IPython console; instead, its
use is intended to be run as a script (i.e. as in "run -i -n" ) either:
a) by one of the custom IPython magics registered with the external IPython 
    kernel and defined in core.extipyutils_host.py; these are:
    
        nrngui and nrnpy
        
    which, when called in the external console, initialize the NEURON environment
    WITH (nrngui) or WITHOUT (nrnpy) NEURON's InterViews-based GUI tools.
    
b) as part of the initialization code when launching a NEURON-enabled external
    IPython kernel from within Scipyen.
    
    See for example:
    
        The module core.extipyutils_client.py for code executed upon external 
            IPython kernel initialization
        
        The methods create_neuron_tab() and start_neuron_in_current_tab() of
            gui.consoles.ExternalConsoleWindow

"""
import os, sys
import neuron
from neuron import h, rxd, units, nrn
from neuron.units import ms, mV, um

__module_path__ = os.path.abspath(os.path.dirname(__file__))


sys.path.insert(2, __module_path__)

h("nrnversion()") # print NEURON version
h("nrnversion(8)")# print machine where this copy of NEURON was compiled
h.ivoc_style("*foreground", "#000000")
h.ivoc_style("*MenuBar*foreground",  "#000000")
h.ivoc_style("*Button*foreground", "#000000")
h.ivoc_style("*Dialog*foreground", "#000000")
h.ivoc_style("*FieldEditor*foreground", "#000000")


start_gui = "gui" in sys.argv

if start_gui:
    ## NOTE: 2021-02-04 18:00:07
    ## On linux, prevent KDE or other DEs theming from overriding the resources 
    ## (colors etc) in the InterViews GUI
    #if sys.platform == "linux":
        #import subprocess
        #compl = subprocess.run(["xrdb", "-merge", os.path.join(__module_path__, "app-defaults", "nrniv")])
        #print("xrdb: ", compl.returncode)
    from neuron import gui
    h.load_file("stdrun.hoc")
    print("loaded stdrun.hoc")

sessions = [i for i in sys.argv if "ses" in os.path.splitext(i)[1]]

#print("sessions", sessions)

if len(sessions):
    session_file = sessions[0]
    
    if not os.path.isfile(session_file):
        warnings.warn("Session file %s not found" % session_file)
    
    if len(sessions) > 1:
        warnings.warn("Only the first session file will be loaded")

    if session_file is not None:
        h.load_file(session_file)
        
    del session_file
        
hocs = [i for i in sys.argv if "hoc" in os.path.splitext(i)[1]]

for hoc_file in hocs:
    h.load_file(hoc_file)
    print("loaded hoc file %s" % hoc_file)
    
del(sessions, hocs, start_gui)

#if __name__ == os.path.basename(os.path.splitext(__file__)[0]):
    ## run -n option
    #pass
