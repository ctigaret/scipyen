import neuron
from neuron import h, rxd, units, nrn
from neuron.units import ms, mV

__module_path__ = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(2, __module_path__)

h("nrnversion()") # print NEURON version
h("nrnversion(8)")# print machine where this copy of NEURON was compiled

start_gui = "gui" in sys.argv

if start_gui:
    from neuron import gui

    h.load_file("stdrun.hoc")

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
    
del(sessions, hocs, start_gui)

#if __name__ == os.path.basename(os.path.splitext(__file__)[0]):
    ## run -n option
    #pass


            
