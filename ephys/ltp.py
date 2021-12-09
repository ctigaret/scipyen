# -*- coding: utf-8 -*-
"""
The first aim in Scipyen's LTP analysis is to store minute-average synaptic 
responses recorded before ("baseline") and after conditioning ("chase"), separately 
for each of the pathways used in the experiment (see "Case 1" below).

To achieve this, LTP generates two neo.Block objects - baseline and chase - 
for each pathway. These blocks contain neo.Segments with minute-averaged data
(analog signals). The steps required to construct these blocks depend on how the 
data was acquired in Clampex, as explained below.

Clampex saves the data as a collection of ABF files. Each file contains signals
recorded for one trial, and upon loading in Scipyen yields a single neo.Block
object.

The Trial may contain a single Run. In this case, the neo.Block holds the data 
recorded during that Run. 

When a Trial is defined as having several Runs, Clampex averaged the run data so 
that the neo.Block holds the average data from several Runs per Trial.

Clampex Trial => one ABF file => neo.Block:
        single Run      => neo.Block contains the Run data
        several Runs    => neo.Block containes the data averaged across the Runs
                            of the Trial
                            
Clampex Runs contain at least one sweep. In Scipyen, a sweep corresponds to one
neo.Segment, and several Segments are collected in the Block's "segments" attribute
(a list)
    
Clampex Sweep => neo.Segment contained in the Block's "segments" attribute.
    
The signals recorded in a sweep are stored as neo.AnalogSignal objects which are
collected in the Segment's "analgosignals" attribute (a list).
        
The possible scenarios when using Clampex for recording are described here
(see also Clampex Lab Bench example at the end of this documentation for signal 
names and roles).

Case 1. 
======
Recording of two independent synaptic pathways converging on the same
post-synaptic cell (whole-cell recording) or in the same slice (field recording). 

Synaptic responses are recorded through the same ANALOG IN channel, and can be
EPSCs (in whole-cell voltage clamp) EPSPs (in whole-cell current clamp) or
fEPSPs (in field recording).

For whole-cell recordings, the same ANALOG OUT (corresponding to the same recording
channel of the amplifier) is used to send command signals in order to:
    - set the holding Vm (in voltage clampe) or Im (in current clamp)
    - deliver depolarizing test pulses used to calculate Rs and Rin (in voltage clamp)
        or hyperpolarizing current pulses used to calculate Rin (in current clamp)

Test stimuli are delivered ALTERNATIVELY to each pathway, usually at low frequency
(0.1 Hz, i.e., 1 test stimulus every 10 s on a given pathway). 

To help distinguish between pathway-specific responses while placing an equal
stimulation burden to both pathways, the test stimuli are interleaved, such that
they are delivered to the tissue at equal intervals.

This generates the following stimulation scheme, applied before and after
conditioning:

Stimulus        0                   1                   2   etc...

Time (s)        0         5         10        15        20  NOTE: __ = 1s = one "sweep"

Path 0          |___________________|___________________|_  NOTE: |_ = test stimulus

Path 1          __________|___________________|___________


This can be achieved in Clampex in three ways:

Case 1.1
--------
Ideal protocol: each pathway is alternatively stimulated in interleaved
sweeps => minute-averaged responses are saved on disk.

Protocol file: AltStim2PathwaysAvgTwoChannels.pro - see Example Protocol below.

Protocol defines ONE trial, to be run from a sequencer key which calls itself 
with 10 s delay, in an infinite loop.

In the acquisition toolbar turn Repeat mode OFF, otherwise trials will start 
right after the end of the previous one.

The Trial contains 6 runs (which automatically enables averaging of data from
corresponding sweeps in 6 consecutive runs). There is a start-to-start interval
of 10 s between runs in the same trial

Each Run contains 2 sweeps (one per pathway) with alternative digital outputs.

Data is saved as trial averages (each trial generates an average of 6 runs) => the
disk files (*.abf) contain minute-by-minute average data, each with two sweeps:

sweep 0  = the average of sweep 0 in all 6 runs/trial;
sweep 1  = the average of sweep 1 in all 6 runs/trial.

Upon loading in Scipyen, these files yield neo.Block objects (one from each file)
with two segments each (corresponding to the sweeps described above). 

These blocks need to be concatenated such that for each path there are two final 
blocks: the "baseline" and the "chase" block (four final blocks in total).

These blocks have sweeps from the same pathway, with each sweep holding
minute-average data.

Case 1.2
-------- 
Pathway stimulation in interleaved sweeps => sweep data is saved directly without
averaging.

The Protocol defines ONE Trial, to be run in an infinite loop from a sequenceer 
key.

The Trial contains a single run consisting of two sweeps as above. 

Each ABF file contains un-averaged synaptic reponse data, and there should be 6 
consecutive files per minute

Loading these files in Scipyen yields a sequence of neo.Block objects with two
segments each (containing individual pathway-specific responses as described 
above).

These need to be averaged using count=6 every=6, separately for baseline and 
chase.

Cases 1.1 and 1.2 cannot be distinguished based on the content of the ABF files.
The distinction must be made in the LTP GUI dialog.


Case 1.3
--------
Separate protocols for each  pathway; each pathway is alternatively stimulated,
and responses are recorded as individual sweeps (1 sweep per file) without 
averaging.

The protocols are interleaved in an infinite loop using the sequencer (assign a 
key to each protocol, then set the key for the first protocol to call the second
procotol after a 5 s delay, and vice-versa).

Each protocol defines a Trial with one Run containing one Sweep that stimulates 
a specific pathway.

Upon loading in Scipyen, the ABF files yield neo.Block objects each containing 
one segment.

In Scipyen, these blocks need to be assigned to a pathway, then averaged using 
count=6, every=6, to generate one baseline and one chase block per pathway.


To help in assigning the responses to their corresponding stimulated pathway, it
is useful to record the digital outputs as well. This can be done by tee-ing the 
digital OUT signal for each patwhay and feeding onto separate analog inputs of 
the digitizer, then including these inputs in the protocol (make sure they are 
defined in the lab bench, see signals 'Stim_0' and 'Stim_1' in the example Lab Bench
configuration given below).


NOTE: Minute-averaged data in each pathway could in principle, be also recorded 
using consecutive trials of 6 runs for each pathwa in turny (ie., one minute for
path 0, then next minute for path 1, then back to path 0, etc ). However, this 
will stimulate the two paths unequally.


NOTE TODO use the metadata stored in the ABF file to distinguish / "guess" which 
of the Cases 1.1, 1.2. 1.3 are used, and to determine to which pathway the 
signals belong.

### BEGIN Boilerplate analysis code
====================================

1) Generate baseline and chase blocks for each pathway

1.1) Case 1.1 - minute-averaged data is already saved => just concatenate the 
blocks:

path_0_baseline = neoutils.concatenate_blocks(getvars("base_avg_*"), segment=0, analog = [2,3,4])
path_0_chase = neoutils.concatenate_blocks(getvars("chase_avg_*"), segment=0, analog = [2,3,4])

path_1_baseline = neoutils.concatenate_blocks(getvars("base_avg_*"), segment=1, analog = [2,3,5])
path_1_chase = neoutils.concatenate_blocks(getvars("chase_avg_*"), segment=1, analog = [2,3,5])



1.2) Case 1.2 - pair of alternate sweeps (path 0 then path 1) saved per trial; 
expecting 6 trials per minute (each with two sweeps); need to average the blocks
(count = 6, every = 6) assuming that first segment in each block refers to the 
same pathway (and the second one, to the other pathway).

path_0_baseline = ephys.average_blocks("baseline_*", segment=0, count=6, every=6,
                                        analog=[2,3], 
                                        name="c03_3123_17b13_baseline_path_0")

path_0_chase = ephys.average_blocks("chase_*", segment=0, count=6, every=6, 
                                        analog=[2,3], 
                                        name="c03_3123_17b13_chase_path_0")

path_1_baseline = ephys.average_blocks("baseline_*", segment=1, count=6, every=6,
                                        analog=[2,3], 
                                        name="c03_3123_17b13_baseline_path_1")

path_1_chase = ephys.average_blocks("chase_*", segment=1, count=6, every=6, 
                                        analog=[2,3], 
                                        name="c03_3123_17b13_chase_path_1")

1.3) Case 1.3 - each ABF file is a block with a single segment corresponding to
one pathway.

2) Set up the parameters for constructing cursors

cursors_0 = [0.05, 0.066, 0.15, 0.26, 0.275, 0.31, 0.325]
labels = ["Rbase", "Rs", "Rin", "EPSC0Base", "EPSC0Peak", "EPSC1Base", "EPSC1Peak"]
xwindow=0.005

2.1) For Cases 1.1 and 1.2 the runs have two sweeps; the second sweep of each
runs start 5 s later (see the Example Protocol below); therefore we create a 
second collection of cursor times:

NOTE: this may be circumvented by setting all signals to start at 0 in the 
concatenated block (case 1.1) or averaged block (case 1.2), once they have been
created, e.g. by calling ephys.set_relative_time_start()

cursors_1 = [c + 5 for c in cursors_0] # call this ONLY it NOT calling set_relative_time_start()

3) Display the block with the baseline or control data from one pathway in a 
Signlaviewer

4) Add cursors to SignalViewer window that displays the baseline or chase block
for one pathway (pathway 0)

4.1) Make sure no other cursors exist in the window: they may not be visible if
outside the time base of the currently displayed segment (sweep).

    * use the SignalViewer Menu "Cursors/Remove cursors/Remove all cursors"
    
    * or, in Scipyen's console, call:
    
        SignalViewer_0.removeCursors()
    
4.2) Call:

SignalViewer_0.addCursors("v", *cursors_0, labels=labels, xwindow=xwindow)

    NOTE: make sure the asterisk is there before cursors_0

4.3) Use these cursors to create an Epoch named "LTP" and embedded in the 
block's segments:

4.3.1) Optionally, navigate through segments and adjust cursor positions.

NOTE The cursor's X position cannot be set on a per-segment basis. Therefore,
choose the optimal cursor position, allowing for some jitter in the synaptic
responses.


4.3.2) Use SignalViewer menu Cursors/Make Epochs in Data/From all cursors, OR
in Scipiyen's console, call:
    
SignalViewer_0.cursorsToEpoch(name="LTP", embed=True, overwrite=True)

Alternatively, to obtain a prompt for Epoch's name, call:
    SignalViewer_0.slot_cursorsToEpochInData()

    CAUTION: For LTP analysis the Epoch MUST be named "LTP".
    
    In the prompt dialog box:

        * Name the epoch as "LTP"

        * Un-check to option to embed in current segment only

        * Check the option to remove all epochs

5) proceed with the other pathway (pathway 1)
    CAUTION: in experiments where data was acquired according to Case 1.1 or 1.2
    the start time in every 2nd sweep in the run starts after the inter-sweep 
    delay (e.g  5s) 
    
    See point (2.1) above
    
    In this case go to (4.1)

ATTENTION: repeat the call in (4.2) but with cursors_1 if needed

SignalViewer_0.addCursors("v", *cursors_1, labels=labels, xwindow=xwindow)

In the experiments where all sweeps start at the same time in both pathways, you
may use the set of LTP cursors that already exists in the SignalWindow

6) Run the LTP analysis - this measures Rs, Rin , and the EPSC amplitudes;
optionally, and when the test stimulus is a paired-pulse, also measures the 
amplitude of the second EPSC and calculates paired-pulse ratio (PPR) - a 
measure of paired pulse facilitation.

c01_20i15_path_0 = ltp.analyse_LTP_in_pathway(path_0_base, path_0_chase, 0, 0,
                                              is_test=True, signal_index_Vm=1, 
                                              trigger_signal_index=2, 
                                              basename="c01_20i15", 
                                              normalize=True)
                                              
c01_20i15_path_1 = ltp.analyse_LTP_in_pathway(path_1_base, path_1_chase,1,0,is_test=True, signal_index_Vm=1, trigger_signal_index=2, basename="c01_20i15", normalize=True)
c01_20i15_path_1 = ltp.analyse_LTP_in_pathway(path_1_base, path_1_chase,0,1,is_test=True, signal_index_Vm=1, trigger_signal_index=2, basename="c01_20i15", normalize=True)


7) Obtain 5-min average EPSC waveforms, and plot to SVG:
7.1) sweep averages

E.g. considering the sweeps contain minute-average records:

7.1.a) to average last 5 sweeps of pre-conditioning, the segment_index must be range(-1, -5, -1):

path_0_baseline_averaged = ephys.average_segments_in_block(path_0_baseline, segment_index = range(-1, -5, -1))

7.1.b) to average 30-35 min of sweeps of pos-conditioning, set the segment_index to
range(30,36)

path_1_chase_averaged = ephys.average_segments_in_block(path_1_chase, segment_index = range(30, 36))

7.2) time slice holding the synaptic responses

epscs = neoutils.get_time_slice(path_X_Y_average, t0, t1,analog_index=0)

where:
    t0 = 0.25 * pq.s, t1 = 0.4 * pq.s OR
    t0 = 5.25 * pq.s, t1 = 5.4 * pq.s depending on which pathway is used (see 
    point (2.1) above)

epsc_0_base = neoutils.get_time_slice(path_0_baseline_averaged, 0.25*pq.s, 0.4*pq.s, analog_index = 0)
epsc_0_chase = neoutils.get_time_slice(path_0_chase_averaged, 0.25*pq.s, 0.4*pq.s, analog_index = 0)
epsc_1_base = neoutils.get_time_slice(path_1_baseline_averaged, 5.25*pq.s, 5.4*pq.s, analog_index = 0)
epsc_1_chase = neoutils.get_time_slice(path_1_chase_averaged, 5.25*pq.s, 5.4*pq.s, analog_index = 0)

7.3) remove the DC component (or at least bring signals to similar baseline)

epsc_0_base.segments[0].analogsignals[0] -= epsc_0_base.segments[0].analogsignals[0].max()
epsc_0_chase.segments[0].analogsignals[0] -= epsc_0_chase.segments[0].analogsignals[0].max()
epsc_1_base.segments[0].analogsignals[0] -= epsc_1_base.segments[0].analogsignals[0].max()
epsc_1_chase.segments[0].analogsignals[0] -= epsc_1_chase.segments[0].analogsignals[0].max()

TODO: can do better than the example above: instead of offsetting the signals by their max(),
offset them by the mean of a time slice BEFORE the stim artifact, e.g. the first 10 ms:

epsc_0_base.segments[0].analogsignals[0] -= epsc_0_base.segments[0].analogsignals[0].time_slice(0.25*pq.s, 0.26*pq.s).mean()
epsc_0_chase.segments[0].analogsignals[0] -= epsc_0_chase.segments[0].analogsignals[0].time_slice(0.25*pq.s, 0.26*pq.s).mean()
epsc_1_base.segments[0].analogsignals[0] -= epsc_1_base.segments[0].analogsignals[0].time_slice(5.25*pq.s, 5.26*pq.s).mean()
epsc_1_chase.segments[0].analogsignals[0] -= epsc_1_chase.segments[0].analogsignals[0].time_slice(5.25*pq.s, 5.26*pq.s).mean()


7.4) plot with matplotlib

x = epscs.segments[0].analogsignals[0].times
y = epscs.segments[0].analogsignals[0].magnitude

plt.plot(x,y)

or, better (make sure the correct title is assigned ot Test or Control pathways)

plots.plotNeoSignal(epsc_0_base.segments[0].analogsignals[0], label = "Pre-conditioning", ylabel="Membrane current (%s)" % epsc_0_base.segments[0].analogsignals[0].dimensionality, fig=Figure1, newPlot=True, color="black")
plots.plotNeoSignal(epsc_0_chase.segments[0].analogsignals[0], label = "Post-conditioning", ylabel="Membrane current (%s)" % epsc_0_chase.segments[0].analogsignals[0].dimensionality, fig=Figure1, newPlot=False, color="#DD0000", panel_size = (2.5,1.5), title="Control")




### END Boilerplate analysis code

### BEGIN Example Clampex Lab Bench 
### Lab Bench: ###
Input Signals:
=============
    Digitizer channels      Signals(1)(2)   Signal units(3) Amplifier(4)        Use:
    -----------------------------------------------------------------------------------------
    Analog IN #0:           Im_prim_0       pA              Channel 0 Primary   V-clamp
                            Vm_prim_0       mV                                  I-clamp
                            IN 0
                            
    Analog IN #1:           Vm_sec_0        mV              Channel 0 Secondary V-clamp
                            Im_sec_0        pA                                  I-clamp
                            IN 1
                            
    Analog IN #2:           Im_prim_1       pA                                  V-clamp
                            Vm_prim_1       mV                                  I-clamp
                            IN 2
                            
    Analog IN #3:           Vm_sec_1        mV                                  V-clamp
                            Im_sec_1        pA                                  I-clamp
                            IN 3

    Analog IN #5:           Stim_0                                              From digitizer DIG OUT 0
    Analog IN #6:           Stim_1                                              From digitizer DIG OUT 1
    
Output Signals:
===============
    Digitizer channels      Signals                         Amplifier           Use:
    ---------------------------------------------------------------------------------
    Analog OUT #0           V_clamp_0       mV              Command in          V-clamp
                            I_clamp_0       pA                                  I-clamp              
                            OUT 0
                            Cmd 0
                            
    Analog OUT #1           V_clamp_1                                           V-clamp
                            I_clamp_1                                           I-clamp
                            OUT 1
                            Cmd 1
                            
    Analog OUT #2           OUT 2
                            Cmd 2
                            
    Analog OUT #3           OUT 3   
                            Cmd 3
                            
    Digital OUT channels
    --------------------
    set in the protocol
    
    
    


NOTE:
(1) These are just labels; you may choose the appropriate one to understand the
role that the corresponding digitizer channel has, in the protocol.


(3) The scale should be set via telegraph, with the amplfier in the APPROPRIATE MODE
    i.e., V-clamp OR I-clamp !!!
    
(4) the actual analog signal send to the digitizer channel depends on the configuration
of the amplifier outputs, in the MultiClamp commander software

The primary and secondary outputs are usually configured to feed analogsignals
to the digitizer input(s) to which they are connected:

Amplifier Channel 0
    Voltage clamp:
        Primary   output => membrane current   -> to digitizer Analog IN #0
        Secondary output => membrane potential -> to digitizer Analog IN #1
        
        Command input <= command potential <- from digitizer Analog OUT #0
        
    Current clamp:
        Primary   output => membrane potential -> to digitizer Analog IN #0
        Secondary output => membrane current   -> to digitizer Analog IN #1
        
        Command input <= command current <- from digitizer Analog OUT #0

Amplifier Channel 1
    Voltage clamp:
        Primary   output => membrane current   -> to digitizer Analog IN #2
        Secondary output => membrane potential -> to digitizer Analog IN #3
        
        Command input <= command potential <- from digitizer Analog OUT #1
        
    Current clamp:
        Primary   output => membrane potential -> to digitizer Analog IN #2
        Secondary output => membrane current   -> to digitizer Analog IN #3
        
        Command input <= command current <- from digitizer Analog OUT #1

### END Example Clampex Lab Bench

### BEGIN Example protocol for case 1.1

Protocol parameters (Edit Protocol dialog):

Mode/rate:
==========
    Acquisition mode: episodic stimulation
    ----------------

    Trial hierarchy:
    ----------------
        Trial delay: 0 s
        Runs/Trial: 6, with 10 s start-to-start interval between runs
        Sweeps/run: 2, with  5 s start-to-start interva between sweeps
        Each sweep:
            1 s duration (50 k samples, for fast rate of 50 kHz)
    
Inputs: (Analog IN channels) - Digidata 1550 series supports 16 analog IN channels
=======
    ON  Channel #0: Im_prim_0
    ON  Channel #1: Vm_sec_0
    ON  Channel #2: Im_prim_1
    ON  Channel #3: Vm_sec_1
    OFF Channel #4: IN 4
    ON  Channel #5: Stim_0
    ON  Channel #6: Stim_1

    ... all other channels from #7 to #15 are OFF

Outputs: (Analog OUT channels) - Digidata 1550 series supports 4 analog OUT channels
========
    Channel #0: V_clamp_0 - all holding level 0 mV
    Channel #1: V_clamp_1
    Channel #2: Cmd 2
    Channel #3: Cmd 3

    Digital OUT holding pattern: 7 - 0 all unchecked 

Trigger:
=======
    Start trial with: Immediate 
    Trigger source: internal timer

    Scope trigger: OFF

    External Tags: OFF

Statistics: 
===========
    Shape Statistics: OFF

Comments: 
=========
    Comments: OFF

Math: 
=====
Math Signal: OFF

Waveform:
========
    Channel #0:
    ----------
        Waveform Analog OUT: V_clamp_0
        
        Analog Waveform: ON
            Epochs
            Intersweep holding level: Use holding
            
        Digital outputs: ON
            Active high logic for digital trains: ON
            Intersweep bit patters: Use holding.
            
        Epoch Table
            Description                 A       B       C       D   
            Type                        Step    Pulse   Step    Step
            First level (mV)            0       5       0       0
            Delta level (mV)            0       0       0       0
            First duration (ms)         50      100     100     100
            Delta duration (ms)         0       0       0       0
            Digital bit pattern (#3-0)  0000    0000    0000    000*
            Digital bit pattern (#7-4)  0000    0000    0000    0000
            Train rate (Hz)                     20              20
            Pulse width (ms)                    50              1
                                                                Pulse count 2
    Channel #1:
    ===========
        Waveform Analog OUT: V_clamp_1
        Analog Waveform: ON
            Epochs
            Intersweep holding level: Use holding
            
        Digital outputs: OFF ("enabled on Channel #0.")
        
        Epoch Table
            Description                 A       B       C       D   
            Type                        Step    Pulse   Step    Step
            First level (mV)            0       5       0       0
            Delta level (mV)            0       0       0       0
            First duration (ms)         50      100     100     100
            Delta duration (ms)         0       0       0       0
            Digital bit pattern (#3-0)  0000    0000    0000    00*0
            Digital bit pattern (#7-4)  0000    0000    0000    0000
            Train rate (Hz)                     20              20
            Pulse width (ms)                    50              1
                                                                Pulse count 2
                                                                
    Number of sweeps: 2 - Allocated time: 381.24 of 1000 ms
    Alternate Waveforms: OFF
    Alternate digital outputs: ON

### END example protocol for case 1.1

TODO 2020-10-20 21:45:35

1) finalize ephys.ElectrophysiologyDataParser, to "guess" the Clampex protocol
configuration from the ABF files (this metadata is stored in the "annotations"
attribute of the neo.Block objects)
2) GUI for LTP experiments - with fields to modify these parameters
    This should generate the baseline and chase blocks, for the LTP experiments.
    Choose between single- or dual pathway experiments.
    Parse (and then adjust) conditioning protocol.
    Prompt for cursor times
    Perform the analysis of LTP parameters :
    for V-clamp: Rs, Rin, EPSC0 amplitude, and optionally EPSC1 amplitude and PPR
    for I-clamps: Rin, EPSP0 slope, and optionally EPSP1 slope & PPR
    for field recordings: fEPSP0 slope, fibre volley amplitude, pop spike; 
        optionally, the same for second fEPSP, and PPR
        
        
    Adapt for data acquired using CED Signal 5.
    
    
"""


#### BEGIN core python modules
import sys, traceback, inspect, numbers
import warnings
import os, pickle
import collections
import itertools
import typing, types

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
import core.workspacefunctions as wf
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.datatypes as dt
from core.quantities import units_convertible
import core.plots as plots
import core.models as models
import core.triggerprotocols as tp
from core.triggerevent import (TriggerEvent, TriggerEventType,)

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

import ephys.ephys as ephys

LTPOptionsFile = os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl")
optionsDir     = os.path.join(os.path.dirname(__file__), "options")

__module_path__ = os.path.abspath(os.path.dirname(__file__))

#__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPWindow.ui"))
__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPWindow.ui"), 
                                                   from_imports=True, 
                                                   import_from="gui") #  so that resources can be imported too


"""
NOTE: 2020-02-14 16:54:19 LTP options revamp
NOTATIONS: Im = membrane current; Vm = membrane potential

Configurations for synaptic plasticity experiments (ex vivo slice) = dictionary with the following fields:

A synaptic plasticity experiment takes place in three stages:
        1. pre-conditioning ("baseline") test synaptic responses
        2. conditioning (plasticity induction protocol)
        3. post-conditioning ("chase") test synaptic responses
        
Test synaptic responses are evoked at low frequency (< 1 Hz) by stimulations of 
presynaptic axons. Because of normal fluctuations in the synaptic response, the 
average synaptic response during each minute is usually more relevant: for 0.1 Hz 
stimulation this is the average of six consecutive responses.

Averaging can be performed "on-line" during the experiment, and the minute-average
responses are recorded directly (Signal2 from CED, and Clampex from Axon/MolecularDevices
can do this). Alternatively, the averaging can be performed off-line, using the saved
data.

The synaptic responses can be recorded as:
    * evoked post-synaptic currents or potentials, using in whole-cell patch clamp 
        or with intracellular (sharp) electrodes, in current clamp;
        
    * evoked field potentials, using in extracellular field recordings.
        
Conditioning consists of a sequence of stimulations delivered to presynaptic axons,
optionally combined with depolarization of the postsynaptic cell(s). 

Postsynaptic cell depolarization:
--------------------------------
Postsynaptic current injections are used to elicit postsynaptic action potentials
(with intracellular sharp electrodes or whole-cell patch clamp), or tonic 
depolarization (whole-cell patch clamp with Na+ channel blockers in the intracellular 
solution). Antidromic stimulation of the efferent axons using extracellulal electrodes
can also be used to elicit postsynaptic action potentials in extracellular field 
recordings.

1. Single pathway experiments:
--------------------------------
A single stimulation electrode is used to stimulate a single pathway (bundle of 
presynaptic axons), and the evoked responses are recorded. 

Synaptic plasticity is determined by comparing the magnitude of the average 
synaptic response some time after conditioning, to that of the average synaptic 
response during the baseline immediately prior conditioning.

2. Dual-pathway experiments. 
--------------------------------
Synaptic responses are recorded, ideally, from two  pathways: 
* a conditioned ("Test") pathway - the pathway ot which the conditioning protocol
    is applied
    
* a non-conditioned ("Control") pathway which is left unperturbed (not stimulated)
    during conditioning.

The occurrence of synaptic plasticity is determined by comparing the averaged
synaptic responses some time after conditioning, to the averaged synaptic responses
during the baseline immediately before conditioning, in each pathway. 

Homosynaptic plasticity is indicated by a persistent change in synaptic response
magnitude in the Test pathway, and no change in the Control pathway.

3 Single recording electrode
--------------------------------
In dual-pathway experiments, the two pathways converge and make synapses on the 
same cell (in whole-cell recording) or within the same cell population (in 
extracellular field recording), and a single electrode is used to record the evoked
synaptic responses from both pathways. The Control pathway serves as a "reference" 
(or "internal control") for the stability of synaptic responses in the absence of
conditioning. 

To distinguish between the pathway source of synaptic responses, the experiment
records intervealed sweeps, with each pathway stimulated alternatively.

4 Two recording electrodes
------------------------------
Two recording electrodes may be used to combine whole-cell recording with 
extracellular field recording (e.g., Zalutsky & Nicoll, 1990).

This can be used in single- or dual-pathway configurations.

Configuration ("LTP_options") -- dictionary
-------------------------------------------

"paths": dictionary of path specifications, with each key being a path "name"

Must contain at least one key: "Test", mapped to the specification of the "test"
    pathway
    
Members (keys) of a pathway specification dictionary:
"sweep_index"
    


Configuration fields:
        
"paths": collection of one or two path dictionaries

    Test synaptic responses from each path are recorded in interleaved sweeps.
    
    For Clampex, this means the experiment is recorded in runs containing 
        
    The test responses during (or typically at the end of) the chase are compared
    to the average baseline test response, on a specific measure, e.g. the amplitude
    of the EPSC or EPSP, or the slope of the (field) EPSP, to determine whether
    synaptic plasticity has been induced.
        
    There is no prescribed duration of the baseline or chase stages - these
    depend on the protocol, recording mode and what it is sought by the
    experiment. 
    
    Very short baselines (less than 5 min) are not considered reliable. 
    Long baselines (15 min or more) while not commonly used in LTP experiments
    with whole-cell recordings in order to avoid "LTP wash-out", unless the 
    perforated patch technique is used. On the other hand, long baselines are 
    recommended for when using field potential recordings and for LTD 
    experiments with whole-cell recordings (wash-out is thought not to be an
    issue).
        
    When only a path dictionary is present, this is implied to represent the 
        conditioned (test) pathway.
    
    For two pathways, the conditioned pathway is indicated by the name 
        "Test". The other pathways can have any unique name, but the one that is
        used as a control should be distinguished by its name (e.g. "Control")
        
    Key/value pairs in the path dictionary:
        name: str, possible vales: "Test", "Control", or any name
        index: the index of the sweep that contains data recorded from this path
        
    
"mode":str, one of ["VC", "IC", "fEPSP"]



"paired":bool. When True, test stimulation is paired-pulse; this applies to all 
    paths in the experiment (see below)

"isi":[float, pq.quantity] - interval between stimuli in paired-pulse stimulation
    when a pq.quantity, it must be in time units compatible with the data
    when a float, the time units of the data are implicit
    

"paths":dict with keys "Test" and "Control", or empty
    paths["Test"]:int
    paths["Control"]:[int, NoneType]
    
    When present and non-empty, indicates that this is a dual pathway experiment
    where one is the test pathway and the other, the control pathway.
    
    The values of the "Test" pathway is the integer index of the sweep corresponding 
    to the test pathway, in each "Run" stored as an *.abf file
    
    Similarly, the value of "Control" is the integer index of the sweep containing
    data recorded on the control pathway, in each run stored in the *.abf file
    
    Although the paths key is used primarily when importing abf files into an
    experiment, it is also used during analysis, to signal that the experiment is
    a dual-pathway experiment.
    
    An Exception is raised when:
        a) both "Test" and "Control" have the same value, or
        b) any of "Test" and "Control" have values < 0 or > max number of sweeps
        in the run (NOTE: a run is stored internally as a neo.Block; hence the 
        number of sweeps in the run equals the number of segments in the Block)
    
    The experiment is implicitly considered to be single-pathway when:
    a) "paths" is absent
    b) "paths" is None or an empty dictionary
    c) "paths" only contains one pathway specification (any name, any value)
    d) "paths" contains both "Test", and "Control" fields but Control is either
        None, or has a negative value
        
"xtalk": dictionary with configuration parameters for testing cross-talk between
    pathways
    Ignored when "dual" is False.
    


1) allow for one or two pathways experiment

2) allow for single or paired-pulse stimulation (must be the same in both pathways)

3) allow for the following recording modes:
3.a) whole-cell patch clamp:
3.a.1) mode="VC": voltage clamp mode => measures series and input resistances,
    and the peak amplitude of EPSC (one or two, if paire-pulse is True
    
    field: "Rm": 
        defines the baseline region for series and input resistance calculation
            
        subfields:
        
        "Rbase" either:
            tuple(position:[float, pq.quantity], window:[float, pq.quantity], name:str)
            
            of sequence of two tuples as above
            
            each tuple defines a cursor;
                when a single cursor is defined, its window defines the baseline
                region
                
                when two cursors are defined, their positions delimit the baseline region
            
            
        
            sets up the cursor Rbase - for Rs and Rin calculations
            type: vertical, position, window, name = Rbase
            
            placed manually before the depolarizing Vm square waveform
            for the membrane resistance test 
        
        field: "Rs":
        
        tuple(position:[float, pq.quantity], window:[float, pq.quantity], name:str)
        
            sets up the second cursors for the calculation of Rs:
            this can be
        
        * Rs: 
            required LTP options fields:
                cursor 1 for resistance test baseline 
                        
                cursor 2 for peak of capacitance transient
                    type: vertical, position, window, name = Rs
                    
                    placed manually
                        either on the peak of the 1st capacitance transient at the
                        onset of the positive Vm step waveform for the membrane
                        resistance test
                        
                        or after this peak, to use with positive peak detection
                    
                value of Vm step (mV)
                
                name of the Im signal
                
                use peak detection: bool, default False
            
            calculation of Rs:
                Irs = Im_Rs - Im_Rbase where:
                    Im_Rs = average Im across the window of Rs cursor
                    Im_Rbase = averae Im across the window of the Rbase cursor
                
            Rs = Vm_step/Irs in megaohm
            
            
        * Rin:
            required LTP options fields:
                cursor 1 for steady-state Im during the positive (i.e. depolarizing)
                    VM step waveform
                    
                    type: vertical, position, window, name=Rin
                    
                    placed manualy towards the end of the Vm step waveform BEFORE repolarization
                    
            calculated as :
                Irin = Im_Rin - Im_Rbase, where:
                    Im_Rin = average Im acros the window of the Rin cursor
                    Im_Rbase -- see Rs
                    
                Rin = Vm_step/Irin
                
        * EPSC0: peak amplitude of 1st EPSC
            required LTP options fields:
                cursor for baseline before stimulus artifact
                type: vertical; position, window, name=EPSC0_base
                manually placed before stimuus artifact for 1st EPSC
                
                cursor for peak of EPSC0
                type: vertical, position, window, name=EPSC0
                placed either manually, or use inward peak detection between
                    two cursors
                
                
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
        
        self.qsettings = QtCore.QSettings()
        self.threadpool = QtCore.QThreadPool()
        
        self._data_ = dict()
        self._data_["Baseline"] = dict()
        self._data_["Baseline"]["Test"] = None
        self._data_["Baseline"]["Control"] = None
        self._data_["Chase"] = dict()
        self._data_["Chase"]["Test"] = None
        self._data_["Chase"]["Control"] = None
        
        self._viewers_ = dict()
        
        self._viewers_["baseline_source"] = None
        self._viewers_["conditioning_source"] = None
        self._viewers_["chase_source"] = None
        
        self._viewers_["pathways"] = dict()
        
        
        # NOTE: 2020-02-23 11:10:20
        # During conditioning the "Control" synaptic pathway is unperturbed but
        # it is possible to stimulate additional synaptic pathways for other
        # purposes: 
        # for NST+SWR experiments, a separate synmaptic pathway is used to
        # simulated sharp wave/ripple events
        # during cooperative LTP experiments, an additional "strong" pathway is 
        # stimulated concomitently with the "Test" (or "weak") pathway so that
        # LTP is induced in the weak pathway - without the strong pathway 
        # stimulation there would be no LTP on the weak ("Test") pathway.
        self._data_["Conditioning"] = dict()
        self._data_["Conditioning"]["Test"] = None
        
        
        # raw data: collections of neo.Blocks, sources from software 
        # vendor-specific data files. These can be:
        # a) axon (ABF v2) files (generated with Clampex)
        # 
        #    Each block contains data from a single trial.
        #
        #    In turn, each trial contains data ither from a single run, 
        #    or averaged data from several runs per trial (the timgins of 
        #    sweeps/run and run/trial should bve set so that they result
        #    in minute-by-minute averages). In the first case (single run per 
        #    trial) the data shuold be averaged offline, either manually or 
        #    using LTPWindow API.
        #
        # b) CFS files (generated with CED Signal) -- TODO
        #    there is usually a single file generated for the entire experiment
        #    but, depending on the script used for the acquisition, it may be
        #    accompanied by two other cfs files, each with pathway-specific 
        #    minute-by-minute average signals.
        #
        #    Notably, the "pulse" information is NOT saved with the file 
        #    unless extra ADC inputs are used to piggyback the digital output 
        #    signals (tee-ed out). Also, the sampling configuration allows
        #    several "pulse" protocols which can be selected / sequenced
        #    and do nto necessarily result in separate baseline and chase
        #    data.
        #
        self._baseline_source_data_ = list()
        self._chase_source_data_ = list()
        self._conditioning_source_data_ = list()
        self._path_xtalk_source_data_ = list()
        
        self._data_var_name_ = None
        
        self._ltpOptions_ = dict()
        
    def _configureUI_(self):
        self.setupUi(self)
        
        self.actionOpenExperimentFile.triggered.connect(self.slot_openExperimentFile)
        self.actionOPenBaselineSourceFiles.triggered.connect(self.slot_openBaselineSourceFiles)
        self.actionOpenChaseSourceFiles.triggered.connect(self.slot_openChaseSourceFiles)
        self.actionOpenConditioningSourceFiles.triggered.connect(self.slot_openConditioningSourceFiles)
        self.actionOpenPathwayCrosstalkSourceFiles.triggered.connect(self.slot_openPathwaysXTalkSourceFiles)
        
        #self.dataIsMinuteAvegaredCheckBox.stateChanged[int].connect(self._slot_averaged_checkbox_state_changed_)
        
        self.actionOpenOptions.triggered.connect(self.slot_openOptionsFile)
        self.actionImportOptions.triggered.connect(self.slot_importOptions)
        
        self.actionSaveOptions.triggered.connect(self.slot_saveOptionsFile)
        self.actionExportOptions.triggered.connect(self.slot_exportOptions)
        
        self.pushButtonBaselineSources.clicked.connect(self.slot_viewBaselineSourceData)
        
        
    @pyqtSlot()
    @safeWrapper
    def slot_openOptionsFile(self):
        pass
    
    @pyqtSlot()
    @safeWrapper
    def slot_importOptions(self):
        pass
    
    @pyqtSlot()
    @safeWrapper
    def slot_saveOptionsFile(self):
        pass
    
    @pyqtSlot()
    @safeWrapper
    def slot_exportOptions(self):
        pass
        
    @pyqtSlot()
    @safeWrapper
    def slot_viewBaselineSourceData(self):
        if len(self._baseline_source_data_) == 0:
            return

        data = None
        
        if not isinstance(self._viewers_["baseline_source"], sv.SignalViewer):
            self._viewers_["baseline_source"] = sv.SignalViewer()
            
        viewer = self._viewers_["baseline_source"]
            
        if len(self._baseline_source_data_) == 1:
            data = self._baseline_source_data_[0]
            
        else:
            nameList = [b.name for b in self._baseline_source_data_]
            choiceDialog = pgui.ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                data_index = nameList.index(choiceDialog.selectedItemsText[0])
                data = self._baseline_source_data_[data_index]


        if isinstance(data, neo.Block):
            viewer.view(data)
            
    @pyqtSlot()
    @safeWrapper
    def slot_viewChaseSourceData(self):
        if len(self._chase_source_data_) == 0:
            return

        data = None
        
        if not isinstance(self._viewers_["conditioning_source"], sv.SignalViewer):
            self._viewers_["conditioning_source"] = sv.SignalViewer()
            
        viewer = self._viewers_["conditioning_source"]
            
        if len(self._chase_source_data_) == 1:
            data = self._chase_source_data_[0]
            
        else:
            nameList = [b.name for b in self._chase_source_data_]
            choiceDialog = pgui.ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                data_index = nameList.index(choiceDialog.selectedItemsText[0])
                data = self._chase_source_data_[data_index]


        if isinstance(data, neo.Block):
            viewer.view(data)
            
            
    @pyqtSlot()
    @safeWrapper
    def slot_viewConditioningSourceData(self):
        if len(self._conditioning_source_data_) == 0:
            return

        data = None
        
        if not isinstance(self._viewers_["conditioning_source"], sv.SignalViewer):
            self._viewers_["conditioning_source"] = sv.SignalViewer()
            
        viewer = self._viewers_["conditioning_source"]
            
        if len(self._conditioning_source_data_) == 1:
            data = self._conditioning_source_data_[0]
            
        else:
            nameList = [b.name for b in self._conditioning_source_data_]
            choiceDialog = pgui.ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                data_index = nameList.index(choiceDialog.selectedItemsText[0])
                data = self._conditioning_source_data_[data_index]


        if isinstance(data, neo.Block):
            viewer.view(data)
            
    @pyqtSlot()
    @safeWrapper
    def slot_viewCrossTalkSourceData(self):
        if len(self._path_xtalk_source_data_) == 0:
            return

        data = None
        
        if not isinstance(self._viewers_["conditioning_source"], sv.SignalViewer):
            self._viewers_["conditioning_source"] = sv.SignalViewer()
            
        viewer = self._viewers_["conditioning_source"]
            
        if len(self._path_xtalk_source_data_) == 1:
            data = self._path_xtalk_source_data_[0]
            
        else:
            nameList = [b.name for b in self._path_xtalk_source_data_]
            choiceDialog = pgui.ItemsListDialog(parent=self, title="Select Baseline Trial", itemsList = nameList)
            
            ans = choiceDialog.exec()
            
            if ans == QtWidgets.QDialog.Accepted and len(choiceDialog.selectedItemsText):
                data_index = nameList.index(choiceDialog.selectedItemsText[0])
                data = self._path_xtalk_source_data_[data_index]


        if isinstance(data, neo.Block):
            viewer.view(data)
            
            
    #@pyqtSlot(int)
    #@safeWrapper
    #def _slot_averaged_checkbox_state_changed_(self, val):
        #checked = val == QtCore.Qt.Checked
        
        #self.sweepAverageGroupBox.setEnabled(not checked)
    
    
    def _parsedata_(self, newdata=None, varname=None):
        # TODO parse options
        if isinstance(newdata, (dict, type(None))):
            self._data_ = newdata
            
    @safeWrapper
    def _parse_clampex_trial_(self, trial:neo.Block):
        """TODO unfinished business
        """
        ret = dict()
        ret["interleaved_stimulation"] = False
        ret["averaged_sweeps"] = False
        ret["averaged_interval"] = 0*pq.s
        
        protocol = trial.annotations.get("protocol", None)
        
        if not isinstance(protocol, dict):
            return ret
        
        # by now the fields below should always be present
        nEpisodes = protocol["lEpisodesPerRun"]
        
        if nEpisodes != len(trial.segments):
            raise RuntimeError("Mismatch between protocol Episodes Per Run (%d) and number of sweeps in trial (%d)" % (nEpisodes, len(trial.segments)))
        
        runs_per_trial = protocol["lRunsPerTrial"]
        
        inter_trial_interval = protocol["fTrialStartToStart"] * pq.s
        inter_run_interval = protocol["fRunStartToStart"] * pq.s
        inter_sweep_interval = protocol["fEpisodeStartToStart"] * pq.s
        
        trial_duration = inter_run_interval * runs_per_trial
        if trial_duration == 0 * pq.s:
            raise RuntimeError("Trial metadata indicates trial duration of %s" % trial_duration )
        
        
        trials_per_minute = int((trial_duration + inter_trial_interval) / (60*pq.s))
        
        alternate_pathway_stimulation = protocol["nAlternateDigitalOutputState"] == 1
        
        alternate_command_ouptut = protocol["nAlternateDACOutputState"] == 1
        
        if alternate_pathway_stimulation:
            ret["interleaved_stimulation"] = True
            
        else:
            ret["interleaved_stimulation"] = False
            
            
        if runs_per_trial > 1:
            ret["averaged_sweeps"] = True
            if trials_per_minute == 1:
                ret["averaged_interval"] = 60*pq.s
                    
        # NOTE: 2020-02-23 14:46:57
        # find out if there is a protocol epoch for membrane test (whole-cell)
        
        protocol_epochs = trial.annotations["EpochInfo"]
        
        if len(protocol_epochs):
            if alternate_command_ouptut:
                # DAC0 and DAC1 commands are sent alternatively with each sweep
                # first sweep is DAC0;
                pass
        
        return ret
            
        
    @pyqtSlot()
    @safeWrapper
    def slot_openExperimentFile(self):
        import mimetypes, io
        targetDir = self._scipyenWindow_.currentDir
        
        pickleFileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                                  caption="Open Experiment file",
                                                                  filter="Pickle Files (*.pkl)",
                                                                  directory=targetDir)
    
    
        if len(pickleFileName) == 0:
            return
        
        data = pio.loadPickleFile(pickleFileName)
        
        if not self._check_for_linescan_data_(data):
            QtWidgets.QMessageBox.critical(self, "Open ScanData file", "Chosen file does not contain a valid ScanData object")
            return
        
        _data_var_name_ = os.path.splitext(os.path.basename(pickleFileName))[0]
        
        self._parsedata_(data, _data_var_name_)
        
        self._scipyenWindow_.assignToWorkspace(_data_var_name_, data)
        
    @pyqtSlot()
    @safeWrapper
    def slot_openBaselineSourceFiles(self):
        """Opens vendor-specific record files with trials for the baseline responses.
        
        Currently only ABF v2 files are supported.
        
        TODO add support for CED Signal files, etc.
        
        TODO Parse electrophysiology records meta information into a vendor-agnostic
        data structure -- see core.ephys module.
        """
        # list of neo.Blocks, each with a baseline trial
        # these may already contain minute-averages
        self._baseline_source_data_ = self.openDataAcquisitionFiles()
        
        #### BEGIN code to parse the record and interpret the protocol - DO NOT DELETE
        
        ## we need to figure out:
        ##
        ## 1) if the data contains averaged sweeps and if so, whether these are
        ##       minute averages
        ##
        ## 2) how many stimulation pathways are involved
        ##
        ## 3) what is the test stimulus: 
        ##       single or paired-pulse
        ##       stimulus onset (in each pathway)
        ##       if paired-pulse, what is the inter-stimulus interval
        
        #trial_infos = [self._parse_clampex_trial_(trial) for trial in self._baseline_source_data_]
        
        #for k, ti in enumerate(trial_infos[1:]):
            #for key in ti:
                #if ti[key] != trial_infos[0][key]:
                    #raise RuntimeError("Mismatch in %s betweenn first and %dth trial" % (key, k+1))
                
        
        
        
        #if trial_infos[0]["averaged_sweeps"]:
            #if trial_infos[0]["averaged_interval"] != 60*pq.s:
                #raise ValueError("Expecting sweeps averaged over one minute interval; got %s instead" % trial_infos[0]["averaged_interval"])
            
            #signalBlockers = [QtCore.QSignalBlocker(w) for w in [self.dataIsMinuteAvegaredCheckBox]]
            
            #self.dataIsMinuteAvegaredCheckBox.setCheckState(True)
            
            #self.sweepAverageGroupBox.setEnabled(False)
            
        #else:
            #self.dataIsMinuteAvegaredCheckBox.setCheckState(False)
            
            #self.sweepAverageGroupBox.setEnabled(True)
            
        #### END code to parse the record and interpret the protocol
            
    @pyqtSlot()
    @safeWrapper
    def slot_openChaseSourceFiles(self):
        self._chase_source_data_ = self.openDataAcquisitionFiles()
        
    @pyqtSlot()
    @safeWrapper
    def slot_openConditioningSourceFiles(self):
        self._conditioning_source_data_ = self.openDataAcquisitionFiles()
        
    @pyqtSlot()
    @safeWrapper
    def slot_openPathwaysXTalkSourceFiles(self):
        self._path_xtalk_source_data_ = self.openDataAcquisitionFiles()
        
    @safeWrapper
    def openDataAcquisitionFiles(self):
        """Opens electrophysiology data acquisition files.
        
        Currently supports the following electrphysiology acquisition software:
        pClamp(Axon binary files version 2 (*.abf) and axon text files, *.atf
        
        TODO: support for:
            CED Signal CED Filing System files (*.cfs)
            CED Spike2 files (SON library)
            Ephus (matlab files?)
        
        """
        import mimetypes, io
        targetDir = self._scipyenWindow_.currentDir
        
        # TODO: 2020-02-17 17:44:55 
        # 1) write code for CED Signal files (*.cfs)
        # 2) write code for Axon Text files
        # 3) write code for pickle files
        # 4) Allow all files then pick up the appropriate loader for each file.
        #
        # Although it may seem convenient for the user, cases 1-4 above complicate 
        # the code for the following reasons:
        # case 1: we need to actually write the CFS file reading logic :-)
        # case 2: the need to make sure that each text file resoves to an appropriate
        # neo.Block (adapt from the code for binary files?)
        # case 3: the pickle file may contain already concatenated records, so we 
        # need a way to distinguish that (adapt from the code for binary files?)
        # case 4: compounds all of the above PLUS resolve the file loader for each
        # file in the list
        # 
        # To keep it simple, we avoid the "All Files" case (for now)
        
        # TODO 2020-02-17 17:49:46
        # how to process axon text files?
        # Again, avoid this case also
        #file_filters = ";; ".join( ["Axon Binary Files (*.abf)",
                                    #"Axon Text Files (*.atf)",
                                    #"CED Signal Files (*.cfs)",
                                    #"Python Pickle Files (*.pkl)",
                                    #"All Files (*.*)"])
        
        file_filters = ";; ".join( ["Axon Binary Files (*.abf)"])
        
        
        
        
        # fileNames: list of fully qualified file names
        # fileFilter: the actual file filter used in the dialog
        fileNames, fileFilter = QtWidgets.QFileDialog.getOpenFileNames(mainWindow, 
                                                                       filter=file_filters)

        if len(fileNames) == 0:
            return
        
        if "Axon Binary" in fileFilter:
            record_data = [pio.loadAxonFile(f) for f in fileNames]
            
        else:
            raise RuntimeError("%s are not supported" % fileFilter)
        
        # NOTE: 2020-02-17 17:51:32
        #### BEGIN DO NOT DELETE - TO BE REVISITED
        #elif "Axon Text" in fileFilter:
            #axon_data = [pio.loadAxonTextFile(f) for f in fileNames]
            #data = [a[0] for a in axon_data]
            ## CAUTION 2020-02-17 17:40:17 test this !
            #metadata = [a[1] for a in axon_data]
            
        #elif "Pickle" in fileFilter:
            ## ATTENTION: 2020-02-17 17:41:58 keep fingers crossed
            #data = [pio.loadPickleFile(f) for f in fileNames]
            
        #elif "CED" in fileFilter:
            #warnings.warn("CED Signal Files not  yet supported")
        #### END DO NOT DELETE
            
        return record_data
    
            
def generate_synaptic_plasticity_options(**kwargs) -> dict:
    """Constructs a dict with options for synaptic plasticity experiments.
    
    The options specify synaptic pathways, analysis cursors and optional 
    minute-by-minute averaging of data from synaptic plasticity experiments.
    
    All synaptic plasticity experiments have a stimulation pathway 
    ("test pathway") where synaptic responses are monitored before and after 
    a conditioning protocol is applied. Homo-synaptic plasticity is considered
    to occur when the conditioning protocol induces changes in the magnitude
    of the synaptic response in the conditioned pathway.
    
    The "test" pathway is assigned index 0 by default, unless specified 
    otherwise.
    
    Ideally, synaptic responses are also monitored on a "control" pathway, which 
    is unperturbed during the conditioning, in order to distinguish the changes
    in synaptic responses in the conditioned ("test") pathway, from changes 
    induced by other causes conditioned (test) pathway.
    
    When a "control" pathway is present, the data from the two pathways is
    expected to have been recorded in alternative, interleaved sweeps.
    
    NOTE: These options are adapted for off-line analysis of data acquired with
    custom protocols in Clampex.
    
    TODO: 
    1. Accommodate data acquired in Clampex using the built-in LTP protocol
    2. Accommodate data acquired with CED Signal (v5 and later).
    3. Allow for single pathway experiments (i.e. test pathway only)
    4. Allow for monitoring extra synaptic pathways (e.g., cooperative LTP as in
       Golding et al, Nature 2002)
    5. Use in acquisition; on-line analysis.
    
    Var-keyword parameters:
    =======================
    
    "field":bool = flag indicating whether the options are for field recordings
        (when True) or whole-cell and intracellular recordings (False)
        Default is False.
    
    "average":int = number of consecutive single-run trials to average 
        off-line (default: 6).
        
        A value of 0 indicates no off-line averaging. 
        
    "every":int   = number of consecutive single-run trials to skip before next 
        offline average (default: 6)
        
    "reference":int  = number of minute-average responses used to assess 
        plasticity; this is the number of reponses at the end of the chase
        stage, and it equals the number of responses at the end of the baseline
        stage. Therefore it cannot be larger than the duration of the baseline 
        stage, in minutes.
        
        Default is 5 (i.e. compare the average of the last 5 minute-averaged 
            responses of the chase stage, to the average of the last 5 
            minute-averaged responses of the baseline stage, in each pathway)
            
            
    "cursor_measures": dict = cursor-based measurements used in analysis.
        Can be empty
        each key is a str (measurement name) that is mapped to a nested dict 
            with the following keys:
        
            "function": a cursor-based signal function as defined in the 
                ephys module, or membrane module
            
                function(signal, cursor0, cursor1,...,channel) -> Quantity
            
                The function accepts a neo.AnalogSignal or datatypes.DataSignal
                as first parameter, 
                followed by any number of vertical SignalCursor objects
                
                The functions must be defined and present in the scope therefore
                they can be specified as module.function, unless imported 
                directly in the workspace where ltp analysis is performed.
            
                Examples: 
                ephys.cursors_chord_slope()
                ephys.cursors_difference()
                ephys.membrane.cursor_Rs_Rin()
            
            "cursors": list of (x, xwindow, label) triplets that specify
             notional vertical signal cursors
                
                NOTE: SignalCursor objects cannot be serialized. Therefore, in 
                order for the options to be persistent, the cursors have to be
                represented by their parameter tuple (time, window) which can be
                stored on disk, and used to generate a cursor at runtime.
                
            "channel": (optional) if present, it must contain an int
            
            "pathway": int, the index of the pathway where the measurement is
                performed, or None (applied to both pathways)
                
        "epoch_measures": dict: epoch_based measurements
            Can be empty.
            
            Has a similar structure to cursor_measures, but uses epoch-based
            measurement functions instead.
            
            "function": epoch-based signal function as defined in the ephys and
                membrane modules
                
            "epoch": a single neo.Epoch (they can be serialized) or the tuple
                (times, durations, labels, name) with arguments suitable to 
                construct the Epoch at run time.
            
            Examples:
            ephys.epoch_average
        
        Using the examples above:
        
        measures[""]
        
        
        
    "test":int , default = 0 index of the "test" pathway, for dual pathway
        interleaved experiments.
        
        For data acquired using Clampex with a custom LTP protocol, this 
        represents the index of the test pathway sweep within each run.
        The sampling protocol is expected to record data alternatively
        from the test and control pathway. 
        
        Trials with a single run will be saved to disk as files contains two 
        sweeps, one for each pathway. 
        
        When the protocol specifies several runs per trial, the saved file will
        also contain two sweeps, with data for the corresponding pathway being 
        averaged acrosss the runs.
    
    "control":int, default = 1
    
    """
    field = kwargs.pop("field", False)
    
    test_path = kwargs.pop("test", 0)
    
    if test_path < 0 or test_path > 1:
        raise ValueError("Invalid test path index (%d); expecting 0 or 1" % test_path)
    
    control_path = kwargs.pop("control", None)
    
    if isinstance(control_path, int):
        if control_path < 0 or control_path > 1:
            raise ValueError("Invalid control path index (%d) expecting 0 or 1" % control_path)
        
        if control_path == test_path:
            raise ValueError("Control path index must be different from the test path index (%d)" % test_path)
    
    average = kwargs.pop("average", 6)
    average_every = kwargs.pop("every", 6)
    
    reference = keargs.pop("reference", 5)
    
    measure = kwargs.pop("measure", "amplitude")
    
    cursors = kwargs.pop("cursors", dict())
    
    LTPopts = dict()
    
    LTPopts["Average"] = {'Count': average, 'Every': average_every}
    LTPopts["Pathways"] = dict()
    LTPopts["Pathways"]["Test"] = test_path
    
    if isinstance(control_path, int):
        LTPopts["Pathways"]["Control"] = control_path
        
    LTPopts["Reference"] = kwargs.get("Reference", 5)
    
    
    if field:
        LTPopts["Signals"] = kwargs.get("Signals",['Vm_sec_1'])
        
        if len(cursors):
            LTPopts["Cursors"] = cursors
            
        else:
            LTPopts["Cursors"] = {"fEPSP0_10": (0.168, 0.001), 
                                  "fEPSP0_90": (0.169, 0.001)}
            
            #LTPopts["Cursors"] = {'Labels': ['fEPSP0','fEPSP1'],
                                #'time': [0.168, 0.169], 
                                #'Pathway1': [5.168, 5.169], 
                                #'Windows': [0.001, 0.001]} # NOTE: cursor windows are not used here
            
        
    else:
        LTPopts["Signals"] = kwargs.get("Signals",['Im_prim_1', 'Vm_sec_1'])
        LTPopts["Cursors"] = {'Labels': ['Rbase','Rs','Rin','EPSC0Base','EPSC0Peak','EPSC1Base','EPSC1peak'],
                              'Pathway0': [0.06, 0.06579859882206893, 0.16, 0.26, 0.273, 0.31, 0.32334583993039734], 
                              'Pathway1': [5.06, 5.065798598822069,   5.16, 5.26, 5.273, 5.31, 5.323345839930397], 
                              'Windows': [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]}
        
    
    return LTPopts
    
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
    
@safeWrapper
def load_synaptic_plasticity_options(LTPOptionsFile:[str, type(None)]=None, **kwargs):
    """Loads LTP options from a file or generates one from arguments.
    
    Parameters:
    ===========
    LTPOptionsFile: str or None (default)
        If a str, it should resolve to an existing pickle file containing a 
        dictionary with valid synaptic plasticity options.
        
        When None, a dictionary of LTP options is generated using kwargs and
        "reasonable" defaults.
        
        WARNING: the contents of the dictionary are not checked for validity as
        options in synaptic plasticity experiments.
        
    Var-keyword parameters:
    =======================
    Passed directly to generate_synaptic_plasticity_options(), used when 
    LTPOptionsFile is None or specifies a non-existent file. 
        
    
    """
    
    if LTPOptionsFile is None or not os.path.isfile(LTPOptionsFile):
        
        LTPopts = generate_synaptic_plasticity_options(**kwargs)
        
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
            
    DEPRECATED
    
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
        baseline = [ephys.concatenate_blocks(baseline_blocks,
                                                segment = LTPOptions["Pathway0"],
                                                analog = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_baseline"),
                    ephys.concatenate_blocks(baseline_blocks,
                                                segment = LTPOptions["Pathway1"],
                                                analog = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_baseline")]
    else:
        baseline    = [ephys.average_blocks(baseline_blocks,
                                            segment = LTPOptions["Pathway0"],
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"],
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_baseline"),
                    ephys.average_blocks(baseline_blocks,
                                            segment = LTPOptions["Pathway1"],
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"], 
                                            name = result_name_prefix + "_path1_baseline")]
              
    baseline[test_pathway_index].name += "_Test"
    baseline[1-test_pathway_index].name += "_Control"
    
    
    if LTPOptions["Average"] is None:
        chase   = [ephys.concatenate_blocks(chase_blocks,
                                                segment = LTPOptions["Pathway0"],
                                                analog = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_chase"),
                   ephys.concatenate_blocks(chase_blocks,
                                                segment = LTPOptions["Pathway1"],
                                                analog = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_chase")]
        
    else:
        chase   = [ephys.average_blocks(chase_blocks,
                                            segment = LTPOptions["Pathway0"], 
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_chase"),
                   ephys.average_blocks(chase_blocks,
                                            segment = LTPOptions["Pathway1"], 
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path1_chase")]
                
    chase[test_pathway_index].name += "_Test"
    chase[1-test_pathway_index].name += "_Control"
    
    ret = {"Test"    : {"Baseline" : baseline[test_pathway_index],   "Chase" : chase[test_pathway_index],   "Path" : test_pathway_index}, \
           "Control" : {"Baseline" : baseline[1-test_pathway_index], "Chase" : chase[1-test_pathway_index], "Path" : 1-test_pathway_index}, \
           "LTPOptions": LTPOptions, "name":result_name_prefix}
        

    return ret

def calculate_fEPSP(block:neo.Block,
                    signal_index:[int, str],
                    epoch:[neo.Epoch, type(None)]=None,
                    out_file:[str, type(None)]=None) -> dict:
    """
    Calculates the slope of field EPSPs.
    
    Parameters:
    ===========
    block: a neo.Block; must contain the analogsignal for the field potential,
        found at the same index in each segment's list of analogsignals,
        throughout the block.
        
    signal_index: int or str.
        When an int: the index of the field potential signal, in the collection
            of analog signals in each segment (same index throughout)
            
        When a str: the name of the analog signal containing the field potential
            data. It must be present in alll segments of the block.
        
            
    epoch: a neo.Epoch, or None (default).
        When a neo.Epoch, it must have at least one interval defined:
        fEPSP0, (optionally, fEPSP1)

     When None, the epoch is supposed to be found embedded in each segment of 
     the block.
     
    
    Returns
    =======
    
    A dict with the following keys:
    
    "fEPSP0" slope of the first field EPSP
    
    Optionally (if there are two intervas in the epoch):
    
    "fEPSP1" slope of the first field EPSP
    "PPR" (paired-pulse ratio)
    
    """
    
    if isinstance(signal_index, str):
        singal_index = ephys.get_index(block, signal_index)
        
    for k, seg in enumerate(block.segments):
        pass
    
def calculate_LTP_measures_in_block(block: neo.Block, 
                                    signal_index_Im, 
                                    signal_index_Vm = None, 
                                    trigger_signal_index = None,
                                    testVm = None, 
                                    epoch = None, 
                                    stim = None,
                                    isi = None,
                                    out_file=None) -> pd.DataFrame:
    """
    Calculates membrane Rin, Rs, and EPSC amplitudes in whole-cell voltage clamp.
    
    Parameters:
    ==========
    block: a neo.Block; must contain one analogsignal each for Im and Vm;
        these signals must be found at the same indices in each segment's list
        of analogsignals, throughout the block.
    
    signal_index_Im: (str, int) Name or index of the Im signal
    
    signal_index_Vm: (str, int, None) Optional (default None).
        Name or index of the Vm signal
        
    trigger_signal_index: (str, int, None) Optional (default None)
    
    Vm: (float, None) Optional (default None)
        When a float, this is taken to be the actual amplitude of the depolarizing
        VM test pulse. 
        
        When None, the amplitude of the test pulse is inferred from the Vm signal
        (selected using the signal_index_Vm given above)
        
    epoch: neo.Epoch (optional, default None)
        This must contain 5 or 7 intervals (Epochs) defined and named as follows:
        Rbase, Rs, Rin, EPSC0base, EPSC0peak (optionally, EPSC1base, EPSC1peak)
        
        When None, then this epoch is supposed to exist (embedded) in every
        segment of the block.
        
        used in the Vm test pulse
    
        
    Returns:
    ---------
    NOTE: 2020-09-30 14:56:00 API CHANGE
    
    A pandas DataFrame with the following columns:
    Rs, Rin, DC, EPSC0, and optionally, EPSC1, PPR, and ISI
    
    NOTE: 2017-04-29 22:41:16 API CHANGE
    Returns a dictionary with keys as follows:
    
    (Rs, Rin, DC, EPSC0) - if there are only 5 intervals in the epoch
    
    (Rs, Rin, DC, EPSC0, EPSC1, PPR) - if there are 7 intervals defined in the epoch
    
    Where EPSC0 and EPSC1 are EPSc amplitudes, and PPR is the paired-pulse ratio (EPSC1/EPSC0)
    
    """
    Idc = list()
    Rs     = list()
    Rin    = list()
    EPSC0  = list()
    EPSC1  = list()
    PPR    = list()
    ISI    = list()
    
    
    ui = None
    ri = None
    
    
    if isinstance(signal_index_Im, str):
        signal_index_Im = ephys.get_index_of_named_signal(block, signal_index_Im)
    
    if isinstance(signal_index_Vm, str):
        signal_index_Vm = ephys.get_index_of_named_signal(block, signal_index_Vm)
        
    if isinstance(trigger_signal_index, str):
        trigger_signal_index = ephys.get_index_of_named_signal(block, trigger_signal_index)
        
    for (k, seg) in enumerate(block.segments):
        #print("segment %d" % k)
        (irbase, rs, rin, epsc0, epsc1, ppr, isi_) = segment_synplast_params_v_clamp(seg, 
                                                                                    signal_index_Im, 
                                                                                    signal_index_Vm=signal_index_Vm, 
                                                                                    trigger_signal_index=trigger_signal_index,
                                                                                    testVm=testVm, 
                                                                                    stim=stim,
                                                                                    isi=isi,
                                                                                    epoch=epoch)
        ui = irbase.units
        ri = rs.units
        
        Idc.append(np.atleast_1d(irbase))
        Rs.append(np.atleast_1d(rs))
        Rin.append(np.atleast_1d(rin))
        EPSC0.append(np.atleast_1d(epsc0))
        EPSC1.append(np.atleast_1d(epsc1))
        PPR.append(np.atleast_1d(ppr))
        ISI.append(np.atleast_1d(isi_))

    ret = dict()
    
    ret["Rs"]       = np.concatenate(Rs) * Rs[0].units
    #print("Rin", Rin)
    ret["Rin"]      = np.concatenate(Rin) * Rin[0].units
    ret["DC"]       = np.concatenate(Idc) * Idc[0].units
    ret["EPSC0"]    = np.concatenate(EPSC0) * EPSC0[0].units
    
    EPSC1_array     = np.concatenate(EPSC1) * EPSC1[0].units
    PPR_array       = np.concatenate(PPR) # dimensionless
    ISI_array       = np.concatenate(ISI) * ISI[0].units
    
    if not np.all(np.isnan(EPSC1_array)):
        ret["EPSC1"] = EPSC1_array
        ret["PPR"]   = PPR_array
        ret["ISI"]   = ISI_array
        
        
    result = pd.DataFrame(ret)
    
    if isinstance(out_file, str):
        result.to_csv(out_file)
        
    return result


def segment_synplast_params_i_clamp(s: neo.Segment, 
                                       signal_index: int, 
                                       epoch: typing.Optional[neo.Epoch]=None) -> np.ndarray:
    if epoch is None:
        if len(s.epochs) == 0:
            raise ValueError("Segment has no epochs and no external epoch has been defined")

        epoch = s.epochs[0]
        
        if len(epoch) != 1 and len(epoch) != 2:
            raise ValueError("Expecting an Epoch with 1 or 2 intervals; got %d instead" % len(epoch))
        
        # each epoch interval should cover the signal time slice over which the 
        # chord slope of the field EPSP is calculated; this time slice should be
        # between the x coordinates of two adjacent cursors, placed respectively 
        # on 10% and 90% from base to (negative) peak (10-90 "rise time")
        
        t0 = epoch.times
        dt = epoch.durations
        t1 = epoch.times + dt
        
        signal = s.analogsignals[signal_index]
        
        epsp_rises = [signal.time_slice(t_0, t_1) for t_0, t_1 in zip(t0,t1)]
        
        chord_slopes = [((sig.max()-sig.min())/d_t).rescale(pq.V/pq.s) for (sig, d_t) in zip(epsp_rises, dt)]
        
        return chord_slopes
        
        
def segment_synplast_params_v_clamp(s: neo.Segment,
                                       signal_index_Im: int,
                                       signal_index_Vm: typing.Optional[int]=None,
                                       trigger_signal_index: typing.Optional[int] = None,
                                       testVm: typing.Union[float, pq.Quantity, None]=None,
                                       epoch: typing.Optional[neo.Epoch]=None,
                                       stim: typing.Optional[TriggerEvent]=None,
                                       isi:typing.Union[float, pq.Quantity, None]=None) -> tuple:
    """
    Calculates several signal measures in a synaptic plasticity experiment.
    
    See NOTE further below, for details about these parameters.
    
    Parameters:
    ----------
    s:neo.Segment
        The segment must contain one analog signal with the recording of the
        membrane current.
        
        Optionally, the segment may also contain:
        
        1) An analog signal containing the recorded membrane potential (in 
            Axon amplifiers this is usually the secondary output of the recording
            channel, in voltage-clamp configuration).
        
            When present, this is used to determine the amplitude of the 
            depolarizing test pulse, which is used to calculate Rs and Rin.
        
            WARNING 
            The function expects such a test pulse to be present in every sweep
            (segment), delivered shortly after the sweep onset, and typically 
            BEFORE the synaptic stimulus. This test pulse can also be delivered 
            towards the end of the sweep, after the synaptic responses. 
            
            Rs and Rin are calculated based on three mandatory intervals ("Rbase",
            "Rs" and "Rin") with their onset times set to fall before, and 
            during the test pulse defined inside the epoch parameter (or embedded in 
            the segment, see below).  The onset times for these intervals should
            be within the test pulse.
            
            The test puIf a depolarizing test pulse is absent, the calculated
        Rs and Rin values will make no sense.
        
        When absent, then the amplitude of such a test pulse MUST be given as a
        separate parameter ("testVm") see below.
        
        1) a neo.Epoch named "LTP" (case-insensitive) with intervals as defined
            in the NOTE further below - used to determine the regions of the 
            membrane current signal where measurements are made.
        
            When such an Epoch is missing, then it must be supplied as an 
            addtional parameter.
        
    signal_index_Im: int 
        Index into the segment's "analogsignals" collection, for the signal
        containing the membrane current.
        
    signal_index_Vm: int 
        Optional (default is None).
        Index into the segment's "analogsignals" collection, for the signal
        containing the recorded membrane potential
        
        ATTENTION: Either signal_index_Vm, or Vm (see below) must be specified and
            not None.
        
    trigger_signal_index: int
        Optional (default is None)
        Index of the signal containing the triggers for synaptic stimulation.
        Useful to determine the time of the synaptic stimulus and the inter-stimulus
        interval (when appropriate).
    
    testVm: scalar float or Python Quantity with units of membrane potential 
        (V, mV, etc)
        Optional (default is None).
        The amplitude of the Vm test pulse.
        
        ATTENTION: Either signal_index_Vm, or Vm must be specified and not None.
        
    stim: TriggerEvent 
        Optional, default is None.
        
        This must be a presynaptic trigger event (i.e. stim.event_type equals
        TriggerEventType.presynaptic) with one or two elements, corresponding to
        the first and, optionally, the second synaptic stimulus trigger.
        
        When present, it will be used to determine the inter-stimulsu interval.
        
        When absent, the interstimulus interval can be manually specified ("isi"
        parameter, below) or detected from a trigger signal (specified using the
        "trigger_signal_index" parameter, see above).
        
    epoch: neo.Epoch
        Optional (default is None).
        When present, indicates the segments of the membrane current signal 
        where the measures are determined -- see NOTE, below, for details.
        
        ATTENTION: When None, the neo.Segment "s" is expected to contain a
        neo.Epoch with intervals defined in the NOTE below.
        
    isi: scalar float or Python Quantity, or None.
        Optional (default is None).
        When None but either trigger_signal_index or stim parameters are specified
        then inter-stimulius interval is determined from these.
        
        
    Returns:
    --------
    
    A tuple of scalars (Idc, Rs, Rin, EPSC0, EPSC1, PPR, ISI) where:
    
    Idc: scalar Quantity = the baseline (DC) current (measured at the Rbase epoch
            interval, see below)
    
    Rs: scalar Quantity = Series (access) resistance
    
    Rin: scalar Quantity = Input resistance
    
    EPSC0: scalar Quantity = Amplitude of first synaptic response.
    
    EPSC1: scalar Quantity = Amplitude of second synaptic response in
            paired-pulse experiments,
            
            or np.nan in the case of single-pulse experiments
            
            In either case the value has membrane current units.
            
    PPR: float scalar = Paired-pulse ratio (EPSC0 / EPSC1, for paired-pulse experiments)
            or np.nan (single-pulse experiments)
            
    ISI: scalar Quantity;
        This is either the value explicitly given in the "isi" parameter or it
        is calculated from the "stim" parameter, or is determined from a trigger
        signal specified with "trigger_signal_index".
        
        When neither "isi", "stim" or "trigger_signal_index" are specified, then
        ISI is returned as NaN * time units associated with the membrane current
        signal.
        
        
    NOTE:
    There are two groups of signal measures:
    
    a) Mandatory measures:
        The series resistance (Rs), the input resistance (Rin), and the amplitude
        of the (first) synaptic response (EPSC0)
    
    b) Optional measures - only for paired-pulse experiments:
        The amplitude of the second synaptic response (EPSC1) and the paired-pulse
        ratio (PPR = EPSC1/EPSC0)
        
    The distinction between single- and paired-pulse stimulation is obtained 
    from the parameter "epoch", which must contain the following intervals or
    regions of the Im signal:
    
    Interval        Mandatory/  Time onset                  Measurement:
    #   label:      Optional:
    ============================================================================
    1   Rbase       Mandatory   Before the depolarizing     Baseline membrane current
                                test pulse.                 to calculate Rs & Rin.
                                                        
    2   Rs          Mandatory   Just before the peak of     The capacitive current
                                the capacitive current      at the onset of the
                                and after the onset of      depolarizing test pulse.
                                the depolarizing test       (to calculate series 
                                pulse.                      resistance).
                                                    
    3   Rin         Mandatory   Towards the end of the      Steady-state current
                                depolarizing pulse.         during the depilarizing
                                                            tets pulse (to calculate
                                                            input resistance).
                                
    4   EPSC0Base   Mandatory   Before the stimulus         Im baseline before  
                                artifact of the first       the first synaptic
                                presynaptic stimulus.       response (to calculate
                                                            amplitude of the first 
                                                            EPSC)
                                
        
    5   EPSC0Peak   Mandatory   At the "peak" (or, rather   Peak of the (first)  
                                "trough") of the first      EPSC (to calculate
                                EPSC                        EPSC amplitude).
                                
    6   EPSC1Base   Optional    Before the stimulus         Im baseline before  
                                artifact of the second      the second synaptic
                                presynaptic stimulus.       response (to calculate
                                                            amplitude of the 2nd 
                                                            EPSC and PPR)
        
    7   EPSC1Peak   Optional    At the "peak" (or, rather   Peak of the 2nd  
                                "trough") of the 2nd        EPSC (to calculate
                                EPSC                        2nd EPSC amplitude
                                                            and PPR).
    
    The labels are used to locate the appropriate signal regions for each 
    measurement and are case-sensitive.
    
    Epochs with 5 intervals are considered to belong to a single-pulse experiment.
    A paired-pulse experiment is represented by an epoch with 7 intervals.
    
    The intervals (and the epoch) can be constructed manually, or visually using
    vertical cursors in Scipyen's SignalViewer. In the latter case, the cursors
    should be labelled accordingly, then an epoch embedded in the segment can be 
    generated with the appropriate menu function in SignalViewer window.
    
    
    """
    def __interval_index__(labels, label):
        #print("__interval_index__ labels:", labels, "label:", label, "label type:", type(label))
        if labels.size == 0:
            raise ValueError("Expecting a non-empty labels array")
        
        if isinstance(label, str):
            w = np.where(labels == label)[0]
        elif isinstance(label, bytes):
            w = np.where(labels == label.decode())[0]
            
        else:
            raise TypeError("'label' expected to be str or bytes; got %s instead" % type(label).__name__)
        
        if w.size == 0:
            raise IndexError("Interval %s not found" % label.decode())
        
        if w.size > 1:
            warnings.warn("Several intervals named %s were found; will return the index of the first one and discard the rest" % label.decode())
        
        return int(w)
        
    mandatory_intervals = [b"Rbase", b"Rs", b"Rin", b"EPSC0Base", b"EPSC0Peak"]
    optional_intervals = [b"EPSC1Base", b"EPSC1Peak"]
    
    if epoch is None:
        if len(s.epochs) == 0:
            raise ValueError("Segment has no epochs, and no external epoch has been defined either")
        
        ltp_epochs = [e for e in s.epochs if (isinstance(e.name, str) and e.name.strip().lower() == "ltp")]
        
        if len(ltp_epochs) == 0:
            raise ValueError("Segment seems to have no LTP epoch defined, and no external epoch has been defined either")
        
        elif len(ltp_epochs) > 1:
            warnings.warn("Theres eem to be more than one LTP epoch defined in the segment; only the FIRST one will be used")
        
        epoch = ltp_epochs[0]
        
    if epoch.size != 5 and epoch.size != 7:
        raise ValueError("The LTP epoch (either supplied or embedded in the segment) has incorrect length; expected to contain 5 or 7 intervals")
    
    if epoch.labels.size == 0 or epoch.labels.size != epoch.size:
        raise ValueError("Mismatch between epoch size and number of labels in the epoch")
    
    mandatory_intervals_ndx = [__interval_index__(epoch.labels, l) for l in mandatory_intervals]
    optional_intervals_ndx = [__interval_index__(epoch.labels, l) for l in optional_intervals]
    
    # [Rbase, Rs, Rin, EPSC0Base, EPSC0Peak]
    t = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in mandatory_intervals_ndx]
    
    #print("t", t)
    
    Idc    = np.mean(s.analogsignals[signal_index_Im].time_slice(t[0][0], t[0][1]))
    
    Irs    = np.max(s.analogsignals[signal_index_Im].time_slice(t[1][0], t[1][1])) 
    
    Irin   = np.mean(s.analogsignals[signal_index_Im].time_slice(t[2][0], t[2][1]))
    
    #print("Idc", Idc, "Irin", Irin, "Irs", Irs)
    
    #t0 = epoch.times # t0: [Rbase, Rs, Rin, EPSC0Base, EPSC0Peak, EPSC1Base, EPSC1Peak]
    #t1 = epoch.times + epoch.durations

    #Idc = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[0], t1[0]))
    
    #Irs    = np.max(s.analogsignals[signal_index_Im].time_slice(t0[1], t1[1])) 
    
    #Irin   = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[2], t1[2]))
    
    if signal_index_Vm is None:
        if isinstance(testVm, numbers.Number):
            testVm = testVm * pq.mV
            
        elif isinstance(testVm, pq.Quantity):
            if not units_convertible(testVm, pq.V):
                raise TypeError("When a quantity, testVm must have voltage units; got %s instead" % testVm.dimensionality)
            
            if testVm.size != 1:
                raise ValueError("testVm must be a scalar; got %s instead" % testVm)
            
        else:
            raise TypeError("When signal_index_Vm is None, testVm is expected to be specified as a scalar float or Python Quantity, ; got %s instead" % type(testVm).__name__)

    else:
        # NOTE: 2020-09-30 09:56:30
        # Vin - Vbase is the test pulse amplitude
        Vbase = np.mean(s.analogsignals[signal_index_Vm].time_slice(t[0][0], t[0][1])) # where Idc is measured
        #print("Vbase", Vbase)

        Vss   = np.mean(s.analogsignals[signal_index_Vm].time_slice(t[2][0], t[2][1])) # where Rin is calculated
        #print("Vss", Vss)
        
        testVm  = Vss - Vbase

    #print("testVm", testVm)
    
    Rs     = (testVm / (Irs - Idc)).rescale(dt.Mohm)
    Rin    = (testVm / (Irin - Idc)).rescale(dt.Mohm)
        
    #print("dIRs", (Irs-Idc), "dIRin", (Irin-Idc), "Rs", Rs, "Rin", Rin)
        
    Iepsc0base = np.mean(s.analogsignals[signal_index_Im].time_slice(t[3][0], t[3][1])) 
    
    Iepsc0peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t[4][0], t[4][1])) 

    EPSC0 = Iepsc0peak - Iepsc0base
    
    if len(epoch) == 7 and len(optional_intervals_ndx) == 2:
        
        # [EPSC1Base, EPSC1Peak]
        t = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in optional_intervals_ndx]
        
        Iepsc1base = np.mean(s.analogsignals[signal_index_Im].time_slice(t[0][0], t[0][1])) 
        
        Iepsc1peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t[1][0], t[1][1])) 
        
        #Iepsc1base = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[5], t1[5])) 
        
        #Iepsc1peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t0[6], t1[6])) 
        
        EPSC1 = Iepsc1peak - Iepsc1base
        PPR = (EPSC1 / EPSC0).magnitude.flatten()[0] # because it's dimensionless
        
    else:
        EPSC1 = np.nan * pq.mV
        PPR = np.nan
            
    ISI = np.nan * s.analogsignals[signal_index_Im].times.units
    
    event = None
    
    if isinstance(isi, float):
        warnings.warn("Inter-stimulus interval explicitly given: %s" % isi)
        ISI = isi * s.analogsignals[signal_index_Im].times.units
        
    elif isinstance(isi, pq.Quantity):
        if isi.size != 1:
            raise ValueError("ISI given explicitly must be a scalar; got %s instead" % isi)
            
        if not units_convertible(isi, s.analogsignals[signal_index_Im].times):
            raise ValueError("ISI given explicitly has units %s which are incompatible with the time axis" % isi.units)
            
        warnings.warn("Inter-stimulus interval is explicitly given: %s" % isi)
        
        ISI = isi
        
    else:
        if isinstance(stim, TriggerEvent): # check for presyn stim event param
            if stim.event_type != TriggerEventType.presynaptic:
                raise TypeError("'stim' expected to be a presynaptic TriggerEvent; got %s instead" % stim.event_type.name)
            
            if stim.size < 1 or stim.size > 2:
                raise ValueError("'stim' expected to contain one or two triggers; got %s instead" % stim.size)
            
            event = stim
            
        elif len(s.events): # check for presyn stim event embedded in segment
            ltp_events = [e for e in s.events if (e.event_type == TriggerEventType.presynaptic and isinstance(e.name, str) and e.name.strip().lower() == "ltp")]
            
            if len(ltp_events):
                if len(ltp_events)>1:
                    warnings.warn("More than one LTP event array was found; taking the first and discarding the rest")
                    
                event = ltp_events[0]
                    
                
        if event is None: # none of the above => try to determine from trigger signal if given
            if isinstance(trigger_signal_index, (str)):
                trigger_signal_index = ephys.get_index_of_named_signal(s, trigger_signal_index)
                
            elif isinstance(trigger_signal_index, int):
                if trigger_signal_index < 0 or trigger_signal_index > len(s.analogsignals):
                    raise ValueError("invalid index for trigger signal; expected  0 <= index < %s; got %d instead" % (len(s.analogsignals), trigger_signal_index))
                
                event = tp.detect_trigger_events(s.analogsignals[trigger_signal_index], "presynaptic", name="LTP")
                
            elif not isinstance(trigger_signal_index, (int, type(None))):
                raise TypeError("trigger_signal_index expected to be a str, int or None; got %s instead" % type(trigger_signal_index).__name__)

            
        if isinstance(event, TriggerEvent) and event.size == 2:
            ISI = np.diff(event.times)[0]

    return (Idc, Rs, Rin, EPSC0, EPSC1, PPR, ISI)

                 
def analyse_LTP_in_pathway(baseline_block: neo.Block, 
                           chase_block: neo.Block, 
                           signal_index_Im: typing.Union[int, str], 
                           path_index: int,
                           baseline_range=range(-5,-1),
                           signal_index_Vm: typing.Union[int, str]=None, 
                           trigger_signal_index: typing.Union[int, str, None]=None,
                           baseline_epoch:typing.Optional[neo.Epoch]=None, 
                           chase_epoch:typing.Optional[neo.Epoch] = None,
                           testVm:typing.Optional[typing.Union[float, pq.Quantity]] = None,
                           stim:typing.Optional[TriggerEvent] = None,
                           isi:typing.Optional[typing.Union[float, pq.Quantity]] = None,
                           basename:str=None, 
                           normalize:bool=False,
                           field:bool=False,
                           is_test:bool = False,
                           v_clamp:bool = True,
                           out_file:typing.Optional[str]=None) -> pd.DataFrame:
    """
    Parameters:
    -----------
    baseline_block: neo.Block with baseline (pre-induction) sweeps (segments)
    chase_block: neo.Block with chase (post-induction) sweeps (segments)
    signal_index_Im: int
    signal_index_Vm: int or str
    trigger_signal_index
    path_index: 
    baseline_range  = range(-5,-1)
    baseline_epoch  = None
    chase_epoch     = None
    Vm              = False
    basename        = None

    """
    # TODO 2020-10-26 09:18:18
    # analysis of fEPSPs
    # analysis of EPSPs (LTP experiments in I-clamp)
    
    #if field:
        #pass
        
    #else:

    baseline_result     = calculate_LTP_measures_in_block(baseline_block, 
                                                          signal_index_Im = signal_index_Im, 
                                                          signal_index_Vm = signal_index_Vm, 
                                                          trigger_signal_index = trigger_signal_index,
                                                          testVm = testVm, 
                                                          epoch = baseline_epoch,
                                                          stim = stim,
                                                          isi = isi)
    
    chase_result        = calculate_LTP_measures_in_block(chase_block,    
                                                            signal_index_Im = signal_index_Im, 
                                                            signal_index_Vm = signal_index_Vm, 
                                                            trigger_signal_index = trigger_signal_index,
                                                            testVm = testVm, 
                                                            epoch = chase_epoch,
                                                            stim = stim,
                                                            isi = isi)

    result = pd.concat([baseline_result, chase_result],
                       ignore_index = True, axis=0, sort=True)
    
    # time index (minutes) relative to the first post-conditioning stimulus (set 
    # to minute zero); this is stored as the index of the data frame
    
    result.index = range(-len(baseline_result), len(chase_result))
    
    if normalize: # augment with normalized values
        meanEPSC0baseline   = np.mean(baseline_result["EPSC0"].iloc[baseline_range])
        result["EPSC0Norm"] = result["EPSC0"] / meanEPSC0baseline
        
        if not np.all(np.isnan(baseline_result["EPSC1"])):
            meanEPSC1baseline = np.nanmean(baseline_result["EPSC1"].iloc[baseline_range])
            result["EPSC1Norm"] = result["EPSC1"] / meanEPSC1baseline
        
    if basename is None:
        basename = ""
        
    name = "%s %s (%d)" % (basename, "Test" if is_test else "Control", path_index)
    
    if hasattr(result, "attr"):
        result.attr["Name"] = name  #requires more recent Pandas
    
    if isinstance(out_file, str):
        result.to_csv(out_file)
    
    return result

def LTP_analysis(path0_base:neo.Block, path0_chase:neo.Block, path0_options:dict,
                 path1_base:typing.Optional[neo.Block]=None, 
                 path1_chase:typing.Optional[neo.Block]=None, 
                 path1_options:typing.Optional[dict]=None,
                 basename:typing.Optional[str]=None):
    """
    path0_base: neo.Block with minute-averaged sweeps with synaptic responses
            on pathway 0 before conditioning
                
    path0_chase: neo.Block with minute-average sweeps with synaptic reponses
            on pathway 0 after conditioning
                
    path0_options: a mapping (dict-like) wiht the key/value items listed below
            (these are passed directly as parameters to analyse_LTP_in_pathway):
                
            Im: int, str                    index of the Im signal
            Vm: int, str, None              index of the Vm signal
            DIG: int, str, None             index of the trigger signal
            base_epoch: neo.Epoch, None
            chase_epoch: neo.Epoxh, None
            testVm: float, python Quantity, None
            stim: TriggerEvent, None
            isi: float, Quantity, None
            normalize: bool
            field: bool                     Vm must be a valid index
            is_test: bool
            v_clamp:bool
            index: int
            baseline_sweeps: iterable (sequence of ints, or range)
                
    
    """

    
def LTP_analysis_v0(mean_average_dict, LTPOptions, results_basename=None, normalize=False):
    """
    Arguments:
    ==========
    mean_average_dict = dictionary (see generate_minute_average_data_for_LTP)
    result_basename = common prefix for result variables
    LTPoptions    = dictionary (see generate_LTP_options()); optional, default 
        is None, expecting that mean_average_dict contains an "LTPOptions"key.
        
    Returns:
    
    ret_test, ret_control - two dictionaries with results for test and control (as calculated by analyse_LTP_in_pathway)
    
    NOTE 1: The segments in the blocks inside mean_average_dict must have already been assigned epochs from cursors!
    NOTE 2: The "Test" and "Control" dictionaries in mean_average_dict must contain a field "Path" with the actual path index
    
    DEPRECATED
    """
    
    if results_basename is None:
        if "name" in mean_average_dict:
            results_basename = mean_average_dict["name"]
            
        else:
            warnings.warn("LTP Data dictionary lacks a 'name' field and a result basename has not been supplied; results will get a default generic name")
            results_basename = "Minute_averaged_LTP_Data"
            
    elif not isinstance(results_basename, str):
        raise TypeError("results_basename parameter must be a str or None; for %s instead" % type(results_basename).__name__)
    
    ret_test = analyse_LTP_in_pathway(mean_average_dict["Test"]["Baseline"],
                                 mean_average_dict["Test"]["Chase"], 0, 1, 
                                 mean_average_dict["Test"]["Path"], 
                                 basename=results_basename+"_test", 
                                 pathType="Test", 
                                 normalize=normalize)
    
    ret_control = analyse_LTP_in_pathway(mean_average_dict["Control"]["Baseline"], mean_average_dict["Control"]["Chase"], 0, 1, mean_average_dict["Control"]["Path"], \
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
        
        
        
    average_test_base = ephys.set_relative_time_start(ephys.average_segments([data["Test"]["Baseline"].segments[ndx] for ndx in test_base_segments_ndx], 
                                                        signal_index = data["LTPOptions"]["Signals"][0])[0])

    test_base = ephys.set_relative_time_start(ephys.get_time_slice(average_test_base, t0, t1))
    
    average_test_chase = ephys.set_relative_time_start(ephys.average_segments([data["Test"]["Chase"].segments[ndx] for ndx in test_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    test_chase = ephys.set_relative_time_start(ephys.get_time_slice(average_test_chase, t0, t1))
    
    control_base_average = ephys.set_relative_time_start(ephys.average_segments([data["Control"]["Baseline"].segments[ndx] for ndx in control_base_segments_ndx],
                                                            signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_base = ephys.set_relative_time_start(ephys.get_time_slice(control_base_average, t0, t1))
    
    control_chase_average = ephys.set_relative_time_start(ephys.average_segments([data["Control"]["Chase"].segments[ndx] for ndx in control_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_chase = ephys.set_relative_time_start(ephys.get_time_slice(control_chase_average, t0, t1))
    
    
    result = neo.Block(name = "%s_sample_traces" % data["name"])
    
    
    # correct for baseline
    
    #print(test_base.analogsignals[0].t_start)
    
    test_base.analogsignals[0] -= np.mean(test_base.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    test_chase.analogsignals[0] -= np.mean(test_chase.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    
    control_base.analogsignals[0] -= np.mean(control_base.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    control_chase.analogsignals[0] -= np.mean(control_chase.analogsignals[0].time_slice(0.0002 * pq.s, 0.002 * pq.s))
    
    test_traces = ephys.concatenate_signals(test_base.analogsignals[0], test_chase.analogsignals[0], axis=1)
    test_traces.name = "Test"
    
    control_traces = ephys.concatenate_signals(control_base.analogsignals[0], control_chase.analogsignals[0], axis=1)
    control_traces.name= "Control"
    
    result_segment = neo.Segment()
    result_segment.analogsignals.append(test_traces)
    result_segment.analogsignals.append(control_traces)
    
    result.segments.append(result_segment)
    
    return result


    
    
