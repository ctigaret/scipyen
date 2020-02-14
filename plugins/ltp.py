# -*- coding: utf-8 -*-

#### BEGIN core python modules
import sys, traceback, inspect, numbers
import warnings
import os, pickle
import collections
import itertools

#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import pandas as pd
import quantities as pq
import matplotlib as mpl
import matplotlib.pyplot as plt
import neo
from scipy import optimize, cluster#, where

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUiType as __loadUiType__ 

#### END 3rd party modules

#### BEGIN pict.core modules
import core.neoutils as neoutils
import core.workspacefunctions as wf
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.datatypes as datatypes
import core.plots as plots
import core.models as models

#from core.patchneo import neo
from core.utilities import safeWrapper
#### END pict.core modules

#### BEGIN pict.gui modules
import gui.signalviewer as sv
import gui.textviewer as tv
import gui.tableeditor as te
import gui.matrixviewer as matview
import gui.pictgui as pgui
import gui.quickdialog as quickdialog
import gui.scipyenviewer as scipyenviewer
from gui.scipyenviewer import ScipyenViewer, ScipyenFrameViewer
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

LTPOptionsFile = os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl")
optionsDir     = os.path.join(os.path.dirname(__file__), "options")

__module_path__ = os.path.abspath(os.path.dirname(__file__))

__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPGUI.ui"), from_imports=True)


# NOTE: 2017-05-07 20:18:37
# overwrite neo's Epoch with our own
#import neoepoch
#neo.core.epoch.Epoch = neoepoch.Epoch
#neo.core.Epoch = neoepoch.Epoch
#neo.Epoch = neoepoch.Epoch

"""
NOTE: 2020-02-14 16:54:19 LTP options revamp

1) allow for one or two pathways experiment

2) allow for single or paired-pulse stimulation (must be the same in both pathways)

3) allow for the following recording modes:
3.a) whole-cell patch clamp:
3.a.1) voltage clamp mode => measures:
        Rs, 
        Rin, 
        peak amplitude of 1st EPSC
        if paired-pulse stimulation: 
            peak amplitude of 2nd EPSC
            ratio 2nd EPSC peak amplitude / 1st EPSC peak amplitude
            
        EPSC amplitudes measurements:
            - at cursor placed at EPSC peak (manually) or by peak-finding
            - relative to baseline cursor before stimulus artifact
            - value = average of data within cursor's WINDOW
            
            
"""

#"def" pairedPulseEPSCs(data_block, Im_signal, Vm_signal, epoch = None):

class LTPWindow(ScipyenFrameViewer, __UI_LTPWindow__):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.settings = QtCore.QSettings()
        self.threadpool = QtCore.QThreadPool()
        
        self._data_ = None
        self._data_var_name_ = None
        
        self._ltpOptions_ = None
        
        
        
        
    
    
    
    
def generate_LTP_options(cursors, signal_names, path0, path1, baseline_minutes, \
                        average_count, average_every):
    """Save LTP options for Voltage-clamp experiments
    
    cursors = iterable with four elements
        labels              (iterable of str)
        times for path 0    (iterable of floats)
        times for path 1    (iterable of floats)
        windows             (iterable of floats)
        
        where each of which are iterables of same length, containing data types as described above.
        
        Obviously, this assumes that cursor times are the same for each segment (sweep) in a given pathway,
        and that all cursor widows are identical.
    
    signal_names   = sequence of two strings with the names of the analog signals for Im and Vm, respectively
                     or sequence of two integral indices (for the Im and Vm analog signals, respectively)

    path0   = int: index of the segments (within the block) holding data from the 1st pathway
    
    path1   = int or None: index of the segments (within the block) for the 2nd pathway (or None for single path experiments)
    
    baseline_minutes = int: number of last baseline minutes before conditioning, to consider for
                    normalizing the EPSCs
                    
    average: bool. Whether to average individual blocks in order to generage minute-average data.
        For pClamp:
            When the acquisition protocol specifies one run/trial, each Axon binary file
            contains individual sweeps (one per path)
    average_count  = int: number of trials to average per minute
    average_every  = int: number of trials to skip between two consecutive averages
                                        
    NOTE:
    
    For a two-pathway protocol (the GOLD STANDARD), the data is expected to have been recorded 
    as alternative segments (sweeps), one for each pathway. In Clampex this is achieved 
    by a "trial" with one "run", with two "sweeps" per "run" (protocol editor window,
    "Mode/Rate" tab. Furthermore, the sweeps are set up as "alternative" in the 
    "Waveform" tab (both "ALternate waveforms" and "Alternate digital outputs" are turned ON).
    The protocol is then repeated indefinitely while recording
    (by activating the "repeat" toggle button in the Acquisition toolbar of Clampex). 
    
    For voltage clamp, the membrane current AND the membrane voltage commands
    should be recorded (by making sure they are selected as inputs into the protocol 
    editor).
    
    This results in a single file per trial, containing unaveraged signals (sweeps)
    for each run, which when loaded individually in python, will generate a series
    of Block objects, each with two segments, corresponding to the repsonse in each 
    pathway, for each run (trial).
    
    For a single pathway, there should be one segment (sweep) per block. In clampex 
    this means one sweep per run.
    
    TODO: adapt for CED Signal data as well, bearing in mind that all experiment data 
    (excep for the protocol itself, see below) is saved in a single cfs file 
    (including baseline pre-conditioning, conditioning, AND chase post-conditioning). 
    For a two-pathway LTP protcol (which is the STANDARD) this would (should?) 
    result in a single Block with an even number of segments (alternatively probing
    each pathway).
    
    The command voltage is not immediately available in CED files (although the command
    voltage waveform and ist timings are save in the conguration file). This signal can.
    however, be recorded in Signal5 by routing from the amplifier into another analog input
    in the CED board (if available!) and recording it by apropriately configuring the Signal5.
    
    Failing that, one can use Vm=True in fruther analyses and supply the value of the test Vm pulse in 
    signal_index_Vm in LTP functions.
    
    The CED issue is not of immediate importance as this kind of analysis is easily done in Signal5
    directly and in real-time (or offline)

    CED protocols are saved independently of recording in sgc configuration files.
    
    TODO: specify the Vm when command voltage signal is not available in voltage-clamp
    
    TODO: adapt for current-clamp/field recording experiments as well.
    
    TODO: accept signal indices as well, not just names, although using names keeps it more
    generic and insensitive to changes in signal order inside a segment, between experiments
    
    """
    
    options = dict()
    
    #crs = collections.namedtuple("Cursors")
    
    options["Cursors"] = {"Labels":cursors[0], "Pathway0": cursors[1], "Pathway1": cursors[2], "Windows": cursors[3]}
    
    if signal_names is not None:
        if isinstance(signal_names, (list, tuple)) and len(signal_names) > 0 and len(signal_names) <=2 and all(isinstance(n, str) for n in signal_names):
            options["Signals"] = signal_names
        elif isinstance(signal_names,str):
            options["Signals"] = signal_names
        else:
            raise TypeError("Unexpected type for signal_names")
    else:
        raise ValueError("signal_names cannot be None")
    
    
    options["Pathway0"] = path0
    options["Pathway1"] = path1
    
    options["Reference"] = baseline_minutes
    
    options["Average"] = {"Count" : average_count, "Every" : average_every}
    
    return options
    
    
            
def save_LTP_options(val):
    if not os.path.isdir(optionsDir):
        os.mkdir(optionsDir)
        
    with open(LTPOptionsFile, "wb") as fileDest:
        pickle.dump(val, fileDest, pickle.HIGHEST_PROTOCOL)
    

def load_LTP_options(LTPOptionsFile=None, field=False):
    if not os.path.isfile(LTPOptionsFile):
        LTPopts = dict()
        LTPopts["Average"] = {'Count': 6, 'Every': 6}
        LTPopts["Cursors"] = {'Labels': ['Rbase','Rs','Rin','EPSC0base','EPSC0Peak','EPSC1base','EPSC1peak'],\
                'Pathway0': [0.06, 0.06579859882206893, 0.16, 0.26, 0.273, 0.31, 0.32334583993039734], \
                'Pathway1': [5.06, 5.065798598822069,   5.16, 5.26, 5.273, 5.31, 5.323345839930397], \
                'Windows': [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]}
        LTPopts["Pathway0"] = 0
        LTPopts["Pathway1"] = 1
        LTPopts["Reference"] =5
        LTPopts["Signals"] = ['Im_prim_1', 'Vm_sec_1']
        print("Now, save the options as %s" % os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl"))
        #raise RuntimeError("No options file found. Have you ever run save_LTP_options ?")
    else:
        with open(LTPOptionsFile, "rb") as fileSrc:
            LTPopts = pickle.load(fileSrc)
        
    return LTPopts

@safeWrapper
def generate_minute_average_data_for_LTP(prefix_baseline, prefix_chase, LTPOptions, test_pathway_index, result_name_prefix):
    """
    basenames : two-element tuple with regexp strings, respectively for the variable names of 
                the baseline and chase Blocks
                
    LTPOptions : a dict as returned by generate_LTP_options
    
    test_pathway_index : an int (0 or 1) indicating which of the two pathways is the test pathway
    
    Returns a dict with two fields: "Test" and "Control", mapping the data for the 
            Test and Control pathways, respectively.
            In turn the data is itself a dict with two fields: "Baseline" and "Chase"
            mapping onto the minute-by-minute average of the sweep data in the 
            respective pathway.
    
    """
    from operator import attrgetter, itemgetter, methodcaller
    
    if not isinstance(test_pathway_index, int):
        raise TypeError("Unexpected type for test_pathway_index: must be an int (0 or 1)")
    
    if test_pathway_index < 0 or test_pathway_index > 1:
        raise ValueError("Unexpected value for test pathway index: must be either 0 or 1")
    
    baseline_blocks = [b for b in wf.getvars(prefix_baseline) if isinstance(b, neo.Block)]
        
    baseline_blocks.sort(key = attrgetter("rec_datetime"))
    
    
    chase_blocks = [b for b in wf.getvars(prefix_chase) if isinstance(b, neo.Block)]
        
    chase_blocks.sort(key = attrgetter("rec_datetime"))
    
    #print(len(baseline_blocks))
    #print(len(chase_blocks))
    
    if LTPOptions["Average"] is None:
        baseline = [neoutils.concatenate_blocks(baseline_blocks,
                                                segment_index = LTPOptions["Pathway0"],
                                                signal_index = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_baseline"),
                    neoutils.concatenate_blocks(baseline_blocks,
                                                segment_index = LTPOptions["Pathway1"],
                                                signal_index = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_baseline")]
    else:
        baseline    = [neoutils.average_blocks(baseline_blocks,
                                            segment_index = LTPOptions["Pathway0"],
                                            signal_index = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"],
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_baseline"),
                    neoutils.average_blocks(baseline_blocks,
                                            segment_index = LTPOptions["Pathway1"],
                                            signal_index = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"], 
                                            name = result_name_prefix + "_path1_baseline")]
              
    baseline[test_pathway_index].name += "_Test"
    baseline[1-test_pathway_index].name += "_Control"
    
    
    if LTPOptions["Average"] is None:
        chase   = [neoutils.concatenate_blocks(chase_blocks,
                                                segment_index = LTPOptions["Pathway0"],
                                                signal_index = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_chase"),
                   neoutils.concatenate_blocks(chase_blocks,
                                                segment_index = LTPOptions["Pathway1"],
                                                signal_index = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_chase")]
        
    else:
        chase   = [neoutils.average_blocks(chase_blocks,
                                            segment_index = LTPOptions["Pathway0"], 
                                            signal_index = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_chase"),
                   neoutils.average_blocks(chase_blocks,
                                            segment_index = LTPOptions["Pathway1"], 
                                            signal_index = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path1_chase")]
                
    chase[test_pathway_index].name += "_Test"
    chase[1-test_pathway_index].name += "_Control"
    
    ret = {"Test"    : {"Baseline" : baseline[test_pathway_index],   "Chase" : chase[test_pathway_index],   "Path" : test_pathway_index}, \
           "Control" : {"Baseline" : baseline[1-test_pathway_index], "Chase" : chase[1-test_pathway_index], "Path" : 1-test_pathway_index}, \
           "LTPOptions": LTPOptions, "name":result_name_prefix}
        

    return ret
    
def calculateRmEPSCsLTP(block, signal_index_Im, signal_index_Vm, Vm = False, epoch = None, out_file=None):
    """
    block: a neo.Block; must have at least one analogsignal for Im and one for Vm; these signals
        must have the same indices in each segment's list og analogsignals in the block
    
    epoch: a neo.Epoch; must have 5 or 7 intervals defined:
        Rbase, Rs, Rin, EPSC0base, EPSC0peak (optionally, EPSC1base, EPSC1peak)
        
    signal_index_Im: index of the Im signal
    signal_index_Vm: index of the Vm signal (if Vm is False) else the detla Vm used in the Vmtest pulse
    
    Vm: boolean, optional( default it False); when True, then signal_index_Vm is taken to be the actul
        amount of membrane voltage depolarization (in mV) used during the Vm test pulse
        
    NOTE: NOT ANYMORE: Returns a tuple of np.arrays as follows: NOTE
    
    NOTE: 2017-04-29 22:41:16 API CHANGE
    Returns a dictionary with keys as follows:
    
    (Rs, Rin, DC, EPSC0) - if there are only 5 intervals in the epoch
    
    (Rs, Rin, DC, EPSC0, EPSC1, PPR) - if there are 7 intervals defined in the epoch
    
    Where EPSC0 and EPSC1 anre EPSc amplitudes, and PPR is the paired-pulse ratio (EPSC1/EPSC0)
    
    """
    Irbase = np.ndarray((len(block.segments)))
    Rs     = np.ndarray((len(block.segments)))
    Rin    = np.ndarray((len(block.segments)))
    EPSC0  = np.ndarray((len(block.segments)))
    EPSC1  = np.ndarray((len(block.segments)))
    
    ui = None
    ri = None
    
    
    if isinstance(signal_index_Im, str):
        signal_index_Im = neoutils.get_index(block, signal_index_Im)
    
    if isinstance(signal_index_Vm, str):
        signal_index_Vm = neoutils.get_index(block, signal_index_Vm)
        Vm = False
        
    for (k, seg) in enumerate(block.segments):
        (irbase, rs, rin, epsc0, epsc1) = calculateLTPSegment(seg, signal_index_Im, signal_index_Vm, Vm=Vm, epoch=epoch)
        ui = irbase.units
        ri = rs.units
        
        Irbase[k] = irbase
        Rs[k]     = rs
        Rin[k]    = rin
        EPSC0[k]  = epsc0
        EPSC1[k]  = epsc1

    ret = dict()
    
    ret["Rs"] = Rs * ri
    ret["Rin"] = Rin * ri
    ret["DC"] = Irbase * ui
    ret["EPSC0"] = EPSC0 * ui
    
    if all(EPSC1):
        ret["EPSC1"] = EPSC1* ui
        ret["PPR"] = ret["EPSC1"]/ ret["EPSC0"]
        
    if isinstance(out_file, str):
        if all(EPSC1):
            header = ["EPSC0", 
                      "EPSC1", 
                      "PPR", 
                      "Rs", 
                      "Rin", 
                      "DC"]
            
            units = [str(ui), 
                     str(ui), 
                     str(ret["PPR"].units), 
                     str((ret["Rs"]*1000).units), 
                     str((ret["Rin"]*1000).units),
                     str(ret["DC"].units)]
            
            out_array = np.concatenate((EPSC0[:,np.newaxis],
                                        EPSC1[:,np.newaxis],
                                        ret["PPR"].magnitude[:,np.newaxis],
                                        (Rs*1000)[:,np.newaxis],
                                        (Rin*1000)[:,np.newaxis],
                                        Irbase[:,np.newaxis]), axis=1)
            
        else:
            header = ["EPSC0", 
                      "Rs", 
                      "Rin", 
                      "DC"]
            
            units = [str(ui), 
                     str((ret["Rs"]*1000).units), 
                     str((ret["Rin"]*1000).units),
                     str(ret["DC"].units)]
            
            out_array = np.concatenate((EPSC0[:,np.newaxis],
                                        (Rs*1000)[:,np.newaxis],
                                        (Rin*1000)[:,np.newaxis],
                                        Irbase[:,np.newaxis]), axis=1)
            
        header = np.array([header, units])
        
        pio.writeCsv(out_array, out_file, header=header)
        
        
    return ret

def calculateLTPSegment(s, signal_index_Im, signal_index_Vm, Vm=False, epoch=None):
    if epoch is None:
        if len(s.epochs) == 0:
            raise ValueError("Segment has no epochs and no external epoch has been defined")
        epoch = s.epochs[0]
        
        if len(epoch) != 5 and len(epoch) != 7:
            raise ValueError("Epoch as supplied or taken from segment has incorrect length; expected to contain 5 or 7 intervals")
        
        t0 = epoch.times
        t1 = epoch.times + epoch.durations
    
        Irbase = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[0], t1[0]))
        
        Irs    = np.max(s.analogsignals[signal_index_Im].time_slice(t0[1], t1[1])) 
        
        Irin   = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[2], t1[2]))
        
        if Vm:
            Rs  = signal_index_Vm * pq.mV / (Irs - Irbase)
            Rin = signal_index_Vm * pq.mV / (Irin - Irbase)
            
        else:
            Vbase = np.mean(s.analogsignals[signal_index_Vm].time_slice(t0[0], t1[0])) 

            Vin   = np.mean(s.analogsignals[signal_index_Vm].time_slice(t0[2], t1[2])) 

            Rs     = (Vin - Vbase) / (Irs - Irbase)
            Rin    = (Vin - Vbase) / (Irin - Irbase)
            
        Iepsc0base = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[3], t1[3])) 
        
        Iepsc0peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[4], t1[4])) 
    
        EPSC0 = Iepsc0peak - Iepsc0base
        
        if len(epoch) == 7:
            
            Iepsc1base = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[5], t1[5])) 
            
            Iepsc1peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[6], t1[6])) 
            
            EPSC1 = Iepsc1peak - Iepsc1base
            
        else:
            EPSC1 = None
            
            

    return (Irbase, Rs, Rin, EPSC0, EPSC1)

                 
def analyzeLTPPathway(baseline_block, chase_block, signal_index_Im, signal_index_Vm, path_index, \
                        baseline_epoch=None, chase_epoch = None, \
                        Vm = False, \
                        baseline_range=range(-5,-1), \
                        basename=None, pathType=None, \
                        normalize=False):
    """
    baseline_block
    chase_block
    path_index
    signal_index_Im
    signal_index_Vm
    baseline_epoch  = None
    chase_epoch     = None
    Vm              = False
    baseline_range  = range(-5,-1)
    basename        = None
    """
    
    baseline_result     = calculateRmEPSCsLTP(baseline_block, signal_index_Im = signal_index_Im, signal_index_Vm = signal_index_Vm, Vm = Vm, epoch = baseline_epoch)
    chase_result        = calculateRmEPSCsLTP(chase_block,    signal_index_Im = signal_index_Im, signal_index_Vm = signal_index_Vm, Vm = Vm, epoch = chase_epoch)
    
    meanEPSC0baseline   = np.mean(baseline_result["EPSC0"][baseline_range])
    
    if normalize:
        baseEPSC0Norm       = baseline_result["EPSC0"]/meanEPSC0baseline
        chaseEPSC0Norm      = chase_result["EPSC0"]/meanEPSC0baseline
    
    else:
        baseEPSC0Norm       = baseline_result["EPSC0"]
        chaseEPSC0Norm      = chase_result["EPSC0"]
        
    #baseline_times      = [seg.rec_datetime for seg in baseline_block.segments] # not used atm
    
    if basename is None:
        basename = ""
        
    if path_index is not None:
        basename += "_path%d" % (path_index)
        
    if normalize:
        header = ["Index_path_%d_%s"        % (path_index, pathType), \
                  "EPSC0_norm_path_%d_%s"   % (path_index, pathType), \
                  "PPR_path_%d_%s"          % (path_index, pathType), \
                  "Rin_path_%d_%s"          % (path_index, pathType), \
                  "RS_path_%d_%s"           % (path_index, pathType), \
                  "DC_path_%d_%s"           % (path_index, pathType)]

    else:
        header = ["Index_path_%d_%s"        % (path_index, pathType), \
                  "EPSC0_path_%d_%s"        % (path_index, pathType), \
                  "PPR_path_%d_%s"          % (path_index, pathType), \
                  "Rin_path_%d_%s"          % (path_index, pathType), \
                  "RS_path_%d_%s"           % (path_index, pathType), \
                  "DC_path_%d_%s"           % (path_index, pathType)]
        
    units  = [" ",  str(baseEPSC0Norm.units), \
                    str(baseline_result["PPR"].units), \
                    str((baseline_result["Rin"]*1000).units), \
                    str((baseline_result["Rs"]*1000).units), \
                    str(baseline_result["DC"].units)]
    
    header = np.array([header, units])
    
    #print(header)
    #print(header.dtype)
    
    EPSC0NormOut_base = np.concatenate((np.arange(len(baseEPSC0Norm))[:,np.newaxis], \
                                        baseEPSC0Norm[:,np.newaxis].magnitude), axis=1)
    
    EPSC0NormOut_chase = np.concatenate((np.arange(len(chaseEPSC0Norm))[:, np.newaxis] ,\
                                        chaseEPSC0Norm[:,np.newaxis].magnitude), axis=1)
    
    EPSC0NormOut = np.concatenate((EPSC0NormOut_base, EPSC0NormOut_chase), axis=0)
    
    Rin_out = np.concatenate(((baseline_result["Rin"]*1000).magnitude, (chase_result["Rin"]*1000).magnitude))
    
    Rs_out = np.concatenate(((baseline_result["Rs"]*1000).magnitude, (chase_result["Rs"]*1000).magnitude))
    
    PPR_out = np.concatenate((baseline_result["PPR"].magnitude, chase_result["PPR"].magnitude))
    
    DC_out = np.concatenate((baseline_result["DC"].magnitude, chase_result["DC"].magnitude))
    
    Out_array = np.concatenate((EPSC0NormOut,   \
                PPR_out[:,np.newaxis],          \
                Rin_out[:,np.newaxis],          \
                Rs_out[:, np.newaxis],          \
                DC_out[:, np.newaxis]), axis=1)
    
    pio.writeCsv(Out_array, "%s_%s" % (basename, "result"), header=header)
        
    ret = dict()
    
    ret["%s_%s" % (basename, "baseline_result")]            = baseline_result
    ret["%s_%s" % (basename, "chase_result")]               = chase_result
    ret["%s_%s" % (basename, "baseline_EPSC0_mean")]        = meanEPSC0baseline
    ret["%s_%s" % (basename, "baseline_EPSC0_normalized")]  = baseEPSC0Norm
    ret["%s_%s" % (basename, "chase_EPSC0_normalized")]     = chaseEPSC0Norm
    
    return ret

    
def LTP_analysis(mean_average_dict, results_basename=None, LTPOptions=None, normalize=False):
    """
    Arguments:
    ==========
    mean_average_dict = dictionary (see generate_minute_average_data_for_LTP)
    result_basename = common prefix for result variables
    LTPoptions    = dictionary (see generate_LTP_options()); optional, default 
        is None, expecting that mean_average_dict contains an "LTPOptions"key.
        
    Returns:
    
    ret_test, ret_control - two dictionaries with results for test and control (as calculated by analyzeLTPPathway)
    
    NOTE 1: The segments in the blocks inside mean_average_dict must have already been assigned epochs from cursors!
    NOTE 2: The "Test" and "Control" dictionaries in mean_average_dict must contain a field "Path" with the actual path index
    """
    
    if results_basename is None:
        if "name" in mean_average_dict:
            results_basename = mean_average_dict["name"]
            
        else:
            warnings.warn("LTP Data dictionary lacks a 'name' field and a result basename has not eenb supllied; results will get a default gneric name")
            results_basename = "Minute_averaged_LTP_Data"
            
    elif not isinstance(results_basename, str):
        raise TypeError("results_basename parameter must be a str or None; for %s instead" % type(results_basename).__name__)
    
    ret_test = analyzeLTPPathway(mean_average_dict["Test"]["Baseline"], mean_average_dict["Test"]["Chase"], 0, 1, mean_average_dict["Test"]["Path"], \
                                basename=results_basename+"_test", pathType="Test", normalize=normalize)
    
    ret_control = analyzeLTPPathway(mean_average_dict["Control"]["Baseline"], mean_average_dict["Control"]["Chase"], 0, 1, mean_average_dict["Control"]["Path"], \
                                basename=results_basename+"_control", pathType="Control", normalize=normalize)
    
    return (ret_test, ret_control)


#"def" plotAverageLTPPathways(data, state, viewer0, viewer1, keepCursors=True, **kwargs):
def plotAverageLTPPathways(data, state, viewer0=None, viewer1=None, keepCursors=True, **kwargs):
    """Plots averaged LTP pathway data in two SignalViewer windows
    
    Arguments:
    =========
    
    data = a dict as returned by generate_minute_average_data_for_LTP()
    
    state: str, one of "baseline" or "chase"
    
    viewer0, viewer1: SignalViewer objects to show respectively, pathway 0 and 1
        These default to None, in which case two new SignalViewer windows will be created.
    
    keepCursors (boolean, optional, default True) 
        when False, a new set of LTP cursors will be created in both viewers, 
        replacing any existing cursors; 
        
        when True, previous cursors (if any) will be left in place; if thre are 
            no cursors, then new cursors will be added to the viewer window
            
            
    Keyword arguments:
    =================
    passed on to SignalViewer.plot() function (e.g. signal=...)
    
    """
    # NOTE: this should have been "injected" at module level by by PictMainWinow at __init__()
    # FIXME find out a more elegant way
    global appWindow 
    
    if not isinstance(data, dict):
        raise TypeError("Expecting a dict, got %s instead" % type(data).__name__)
    
    if not isinstance(state, str):
        raise TypeError("State is expected to be a str, got %s instead" % type(state).__name__)
    
    if state not in ("baseline", "Baseline", "base", "Base", "chase", "Chase"):
        raise ValueError("State is expected to be one of 'baseline' or 'chase'; got %s instead" % state)
    
    if state.lower() in ("baseline", "base"):
        state = "Baseline"
        
    else:
        state="Chase"
        
    if isinstance(viewer0, (tuple, list)) and len(viewer0) == 2 and all([isinstance(v, sv.SignalViewer) for v in viewer0]):
        viewer1 = viewer0[1]
        viewer0 = viewer0[0]
        
    else:
        if viewer0 is None:
            if appWindow is not None:
                viewer0 = appWindow.newSignalViewerWindow()
            else:
                raise TypeError("A SignalViewer must be specified for viewer0")
            
        if viewer1 is None:
            if appWindow is not None:
                viewer1 = appWindow.newSignalViewerWindow()
            else:
                raise TypeError("A SignalViewer must be specified for viewer1")
            
    if data["Test"]["Path"] == 0:
        viewer0.plot(data["Test"][state], **kwargs)
        viewer1.plot(data["Control"][state], **kwargs)
        
    else:
        viewer0.plot(data["Control"][state], **kwargs)
        viewer1.plot(data["Test"][state], **kwargs)

    if len(viewer0.verticalCursors) == 0 or not keepCursors:
        viewer0.currentAxes = 0
        setupLTPCursors(viewer0, data["LTPOptions"], 0)
        
    if len(viewer1.verticalCursors) == 0 or not keepCursors:
        viewer1.currentAxes = 0
        setupLTPCursors(viewer1, data["LTPOptions"], 1)
    
def setupLTPCursors(viewer, LTPOptions, pathway, axis=None):
    """ Convenience function for setting up cursors for LTP experiments:
    
    Arguments:
    ==========
    
    LTPOptions: a dict with the following mandatory key/value pairs:
    
        {'Average': {'Count': 6, 'Every': 6},

        'Cursors': 
            {'Labels':  ['Rbase',
                        'Rs',
                        'Rin',
                        'EPSC0base',
                        'EPSC0Peak',
                        'EPSC1base',
                        'EPSC1peak'],

            'Pathway0': [0.06,
                        0.06579859882206893,
                        0.16,
                        0.26,
                        0.273,
                        0.31,
                        0.32334583993039734],

            'Pathway1': [5.06,
                        5.065798598822069,
                        5.16,
                        5.26,
                        5.273,
                        5.31,
                        5.323345839930397],

            'Windows': [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]},

        'Pathway0': 0,

        'Pathway1': 1,

        'Reference': 5,

        'Signals': ['Im_prim_1', 'Vm_sec_1']}
        
    pathway: int = the pathway for which the cursors are shown: can be 0 or 1
    
    axis: optional default None: an int index into the axis receiving the cursors
        (when None, the fist axis i.e. at index 0, is chosen)
    """
    
    if not isinstance(viewer, sv.SignalViewer):
        raise TypeError("The parameter 'viewer' was expected to be a SignalViewer; got %s instead" % type(viewer).__name__)
    
    if axis is not None:
        if isinstance(axis, int):
            if axis < 0 or axis >= len(viewer.axesWithLayoutPositions):
                raise ValueError("When specified, axis must be an integer between 0 and %d" % len(viewer.axesWithLayoutPositions))
            
            viewer.currentAxes = axis
            
        else:
            raise ValueError("When specified, axis must be an integer between 0 and %d" % len(viewer.axesWithLayoutPositions))
        
    
    viewer.setupCursors("v", LTPOptions["Cursors"]["Pathway%d"%pathway])
        
def extract_sample_EPSPs(data, 
                         test_base_segments_ndx, 
                         test_chase_segments_ndx, 
                         control_base_segments_ndx, 
                         control_chase_segments_ndx,
                         t0, t1):
    """
    data: dict; an LTP data dict
    
    test_base_segments_ndx,
    test_chase_segments_ndx,
    control_base_segments_ndx, 
    control_chase_segments_ndx: indices of segments ot average in the corresponding path & state

    t0: Python Quantity in time units: start of time interval in the signal
    t1: Python Quantity in time units: end of the time interval
    
    Both t0 and t1 must be relative to 0
    
    Returns a neo.Segment
    
    """
    if not isinstance(data, dict):
        raise TypeError("Expecting a dict, got %s instead" % type(data).__name__)

    
    if not isinstance(test_base_segments_ndx, (tuple, list, range)):
        raise TypeError("test_base_segments_ndx expected a sequence or range; got %s instead" % type(test_base_segments_ndx).__name__)
    
    if isinstance(test_base_segments_ndx, (tuple, list)):
        if not all([isinstance(v, int) for v in test_base_segments_ndx]):
            raise TypeError("when a sequence, test_base_segments_ndx musy contain only integers")
        
        
    if not isinstance(test_chase_segments_ndx, (tuple, list, range)):
        raise TypeError("test_chase_segments_ndx expected a sequence or range; got %s instead" % type(test_chase_segments_ndx).__name__)
    
    if isinstance(test_chase_segments_ndx, (tuple, list)):
        if not all([isinstance(v, int) for v in test_chase_segments_ndx]):
            raise TypeError("when a sequence, test_chase_segments_ndx musy contain only integers")
        
        
    if not isinstance(control_base_segments_ndx, (tuple, list, range)):
        raise TypeError("control_base_segments_ndx expected a sequence or range; got %s instead" % type(control_base_segments_ndx).__name__)
    
    if isinstance(control_base_segments_ndx, (tuple, list)):
        if not all([isinstance(v, int) for v in control_base_segments_ndx]):
            raise TypeError("when a sequence, control_base_segments_ndx musy contain only integers")
        
        
    if not isinstance(control_chase_segments_ndx, (tuple, list, range)):
        raise TypeError("control_chase_segments_ndx expected a sequence or range; got %s instead" % type(control_chase_segments_ndx).__name__)
    
    if isinstance(control_chase_segments_ndx, (tuple, list)):
        if not all([isinstance(v, int) for v in control_chase_segments_ndx]):
            raise TypeError("when a sequence, control_chase_segments_ndx musy contain only integers")
        
        
        
    average_test_base = neoutils.set_relative_time_start(neoutils.average_segments([data["Test"]["Baseline"].segments[ndx] for ndx in test_base_segments_ndx], 
                                                        signal_index = data["LTPOptions"]["Signals"][0])[0])

    test_base = neoutils.set_relative_time_start(neoutils.get_time_slice(average_test_base, t0, t1))
    
    average_test_chase = neoutils.set_relative_time_start(neoutils.average_segments([data["Test"]["Chase"].segments[ndx] for ndx in test_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    test_chase = neoutils.set_relative_time_start(neoutils.get_time_slice(average_test_chase, t0, t1))
    
    control_base_average = neoutils.set_relative_time_start(neoutils.average_segments([data["Control"]["Baseline"].segments[ndx] for ndx in control_base_segments_ndx],
                                                            signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_base = neoutils.set_relative_time_start(neoutils.get_time_slice(control_base_average, t0, t1))
    
    control_chase_average = neoutils.set_relative_time_start(neoutils.average_segments([data["Control"]["Chase"].segments[ndx] for ndx in control_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_chase = neoutils.set_relative_time_start(neoutils.get_time_slice(control_chase_average, t0, t1))
    
    
    result = neo.Block(name = "%s_sample_traces" % data["name"])
    
    
    # correct for baseline
    
    #print(test_base.analogsignals[0].t_start)
    
    test_base.analogsignals[0] -= np.mean(test_base.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    test_chase.analogsignals[0] -= np.mean(test_chase.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    
    control_base.analogsignals[0] -= np.mean(control_base.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    control_chase.analogsignals[0] -= np.mean(control_chase.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    
    test_traces = neoutils.concatenate_signals(test_base.analogsignals[0], test_chase.analogsignals[0], axis=1)
    test_traces.name = "Test"
    
    control_traces = neoutils.concatenate_signals(control_base.analogsignals[0], control_chase.analogsignals[0], axis=1)
    control_traces.name= "Control"
    
    result_segment = neo.Segment()
    result_segment.analogsignals.append(test_traces)
    result_segment.analogsignals.append(control_traces)
    
    result.segments.append(result_segment)
    
    return result


    
    
