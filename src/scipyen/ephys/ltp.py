# -*- coding: utf-8 -*-

#### BEGIN core python modules
import os, sys, traceback, inspect, numbers, warnings, pathlib, timer
import functools, itertools
import collections, enum
import typing, types
import dataclasses
from dataclasses import (dataclass, KW_ONLY, MISSING, field)

#### END core python modules

#### BEGIN 3rd party modules
import numpy as np
import pandas as pd
import quantities as pq
# from quantities.decorators import with_doc
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
from core.workspacefunctions import (user_workspace, validate_varname, get_symbol_in_namespace, assignin)
import core.signalprocessing as sigp
import core.curvefitting as crvf
import core.pyabfbridge as pab
import core.datatypes  
from core.datatypes import (Episode, Schedule, TypeEnum)
import plots.plots as plots
import core.models as models
import core.neoutils as neoutils
from core.neoutils import (clear_events, get_index_of_named_signal, is_empty, 
                           concatenate_blocks, concatenate_signals,
                           average_segments)

from core.sysutils import adapt_ui_path

import core.triggerprotocols as tp
from core.triggerprotocols import (TriggerProtocol,
                                   embed_trigger_protocol, 
                                   embed_trigger_event,
                                   parse_trigger_protocols,
                                   remove_trigger_protocol,)

from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType,)
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import DataZone

from core import (prog, traitcontainers, strutils, neoutils, models,)
from core.prog import (safeWrapper, AttributeAdapter, with_doc)
from core.basescipyen import BaseScipyenData
from core.traitcontainers import DataBag
from core import quantities as cq
from core.quantities import(arbitrary_unit, 
                            pixel_unit, 
                            channel_unit,
                            space_frequency_unit,
                            angle_frequency_unit,
                            day_in_vitro,
                            week_in_vitro, postnatal_day, postnatal_month,
                            embryonic_day, embryonic_week, embryonic_month,
                            unit_quantity_from_name_or_symbol,
                            check_time_units,
                            units_convertible)

from core.utilities import (safeWrapper, 
                            reverse_mapping_lookup, 
                            get_index_for_seq, 
                            sp_set_loc,
                            normalized_index,
                            GeneralIndexType)

#### END pict.core modules

#### BEGIN pict.gui modules
import gui.signalviewer as sv
import gui.textviewer as tv
import gui.tableeditor as te
import gui.matrixviewer as matview
import gui.pictgui as pgui
from gui.itemslistdialog import ItemsListDialog
import gui.quickdialog as quickdialog
import gui.scipyenviewer as scipyenviewer
from gui.scipyenviewer import ScipyenViewer, ScipyenFrameViewer
from gui.cursors import SignalCursor
from gui.workspacegui import DirectoryFileWatcher
#### END pict.gui modules

#### BEGIN pict.iolib modules
import iolib.pictio as pio
#### END pict.iolib modules

import ephys.ephys as ephys
from ephys.ephys import ClampMode, ElectrodeMode
from ephys.ephys import LocationMeasure
from ephys import membrane


LTPOptionsFile = os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl")
optionsDir     = os.path.join(os.path.dirname(__file__), "options")

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__,"LTPWindow.ui")
    

#__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPWindow.ui"))
# __UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__module_path__,"LTPWindow.ui"), 
# __UI_LTPWindow__, __QMainWindow__ = __loadUiType__(os.path.join(__ui_path__,"LTPWindow.ui"), 
__UI_LTPWindow__, __QMainWindow__ = __loadUiType__(__ui_path__, 
                                                   from_imports=True, 
                                                   import_from="gui") #  so that resources can be imported too

#"def" pairedPulseEPSCs(data_block, Im_signal, Vm_signal, epoch = None):

class SynapticPathway: pass # forward declaration for PathwayEpisode; redefined below

class PathwayType(TypeEnum):
    """
    Synaptic pathway type.
    Encapsulates: Null, Test, Control, and up to six additional types
    """
    # TODO: 2023-05-22 14:28:53
    # To emulate a cross-talk - style recording, this should be associated with
    # a mapping detailing the order of the cross-stimulation
    
    Null = 0
    # NOTE: 2023-06-02 15:41:59 
    # In synaptic plasticity experiments, Tracing and Induction pathways are
    #   recorded FROM THE SAME CELL, in SEPARATE SWEEPS, ONE PER PATHWAY.
    #
    #   Each sweep contains an instance of synaptic response on the corresponding
    #   pathway.
    #
    #   When more than one pathway is recorded, tracking the synaptic responses 
    #   must use the same pattern of activity in all pathways. This ensures
    #   equal treament of all pathways. The only exception to this rule is during 
    #   plasticity induction, where only a subset of pathways are exposed to the
    #   induction protocol (the "Test" pathways), whereas the others ("Control"
    #   pathways) are left unperturbed.
    #
    # Theoretically, this can be achieved either:
    #
    # • in INTERLEAVED mode (typical) ⇒ the number of neo.Segment objects 
    #   (a.k.a 'sweeps') in the neo.Block (a.k.a, the 'trial') is expected to be
    #   an integer multiple of the TOTAL number of pathways; THE ORDER of the 
    #   pathway-specific sweeps IS THE SAME IN ALL trials.
    #
    #   NOTE: in Clampex, a 'trial' may consist of:
    #   ∘ several 'runs', meaning that the stored trial data contains AN AVERAGE
    #       of the corresponding individual sweeps across several runs in the trial.
    #       The result is like a "running" average across as many runs that were 
    #       recorded per total duration of the trial - see Clampex protocol editor
    #       for details. 
    #
    #       In the most typical scenario (for two pathways):
    #       ⋆ 'trials' are repeated every minute
    #       ⋆ each 'trial' contains six 'runs' repeated every 10 s
    #       ⋆ each 'run' contains two sweeps, at 5 s delay (so that the pathway 
    #       responses are evoked with similar delays) and sweeps last 1 s
    #
    #           In these conditions, Clampex records a synaptic response from
    #       each pathway every 10 s for six times, then saves their (minute)
    #       average on disk.
    #
    #   ∘ a single 'run' ⇒ there is no distinction between 'run' and 'trial'. 
    #       However, a single 'run' per 'trial' means that each 'sweep' in the 
    #       save file contains just one instance of the synaptic response, NOT an
    #       average! As we are usually interested in the minute-averaged responses
    #       the 'runs' are executed several times per minute at a fixed interval
    #       (e.g, six runs per minute every 10 s). Data will need to be averaged
    #       off-line.
    #
    #
    # • in contiguous mode (atypical)
    #       A 'trial' contains responses recorded from a single pathway; when
    #       there are more pathways, responses on distinct pathways are recorded
    #       in distinct 'trials' or 'runs' - this is unwieldy, and may result in 
    #       patterns of activity that are distinct between pathways
    #
    
    Tracking = 1 # used for tracking synaptic responses
    Control = Tracking # alias; this is the "normal" case where no induction is applied 
    Induction = 2 # used for induction of plasicity (i.e. application of the induction protocol)
    Test = Tracking | Induction # the Tracking pathway where Induction was applied
    # auxiliary pathways can be:
    # • present along the tracking pathway, during tracking only
    # • present along the induction pathway, during induction only
    # • present throughout
    Auxiliary = 4 # e.g. ripple, etc
    Type1 = 8
    Type2 = 16
    Type3 = 32
    Type4 = 64
    Type5 = 128
    CrossTalk = 65536
    
@with_doc(Episode, use_header=True, header_str = "Inherits from:")
class PathwayEpisode(Episode):
    """
Specification of an episode in a synaptic pathway.

An "episode" is a series of sweeps recorded during a specific set of
experimental conditions -- possibly, a subset of a larger experiment where
several conditions were applied in sequence.

All sweeps in the episode must have been recorded during the same conditions.

NOTE: A Pathway Episode does NOT store any data; it only stores indices into
segments (a.k.a sweeps) of a neo.Block object containing the data.

It can be used to create a new such Block object from source neo.Blocks -
i.e., passing it to the neoutils.concatenate_blocks(...) function.


Examples:
=========

1) A response recorded without drug, followed by a response recorded in the
presence of a drug, then followed by a drug wash-out are all three distinct
"episodes".

2) Segments recorded while testing for cross-talk between synaptic pathways,
(and therefore, where the paired pulses are crossed between pathways) is a
distinct episode from one where each segment contains responses from the
same synaptic pathway

The sweeps in PathwayEpisode are a sequence of neo.Segment objects, where
objects where each synaptic pathway has contributed data for a neo.Segment
inside the Block.

Fields (constructor parameters):
================================
• name:str - mandatory, name of the episode

The PathwayEpisode only stores arguments needed to (re)create a new neo.Block
by concatenating several source neo.Block data.

The other fields indicate optional indices into the data segments and signals
of the source data.

• response : int or str - respectively, the index or the name of the
    analog signal in each sweep, containing the pathway-specific synaptic
    response

    NOTE: During an experiment, the recording may switch between episodes with
    different clamping modes, or electrode modes (see below). This results in
    episodes with different response and command signals. Therefore we attach
    this information here, instead of the SynapticPathway instance to which this
    episode belongs to.`

• analogStimulus : int or str - index or name of the analog signal containing
    voltage- or current-clamp command signal (or None); such a signal is
    typically recorded - when available - by feeding the secondary output of
    the amplifier into an ADC input in the acquisition board.

• digitalStimulus: int or str - index or name of the analog signal containing
    a recorded version of the triggers for extracellular stimulation.

    When available, these are triggers sent to stimulus isolation boxes to
    elicit an extracellular stimulus.

    The triggers themselves are typically TTL signals, either taken directly
    from the acquisition board digital output, or "emulated" by an analog
    (DAC) output containing a rectangulare wave of 5 V amplitude.

    In either case, these triggers can be routed into an ADC input of the
    acquisition board, for recording (e.g., using a BNC "tee" splitter).

•   electrodeMode: ephys.ElectrodeMode (default is ElectrodeMode.Field)

    NOTE: With exceptions¹, the responses in a synaptic pathway are recorded
    using the same electrode during an experiment (i.e. either Field, *Patch, or
    or Sharp).

    This attribute allows for episodes with distinct electrode 'mode' for the
    same pathway.

• clampMode: ephys.ClampMode (default is ClampMode.NoClamp)
    The recording "mode" - no clamping, voltage clamp or current clamp.

    NOTE: Even though a pathway may have been recorded with the same electrode
    mode throughout an experiment, one may switch between different clamping modes,
    where it makes sense, e.g., voltage clamp during tracking and current clamp
    during conditioning.

    This attribute helps distinguish episodes with different clamping modes.

• xtalk: optional, a list of SynapticPathways or None (default); can also be an
    empty list (same as if it was None)

    Only used for 'virtual' synaptic pathways where the recording tests for
    the cross-talk between two 'real' pathways using paired-pulse stimulation.

    Indicates the order in which each pathway was stimulated during the
    paired-pulse.

• pathways: optional, a list of SynapticPathways or None (default); can also be
    an empty list (same as if it was None).

    Indicates the SynapticPathways to which this episode applies. Typically,
    an episode applied to a single pathway. However, there are situations where
    an episode involving more pathways is meaningful, e.g., where additional
    pathways are stimulated and recorded simultaneously (e.g., in a cross-talk
    test, or during conditioning in order to test for 'associativity')

---

¹Exceptions are possible:
    ∘ 'repatching' the cell (e.g. in order to dialyse with a drug, etc) see, e.g.
        Oren et al, (2009) J. Neurosci 29(4):939
        Maier et al, (2011) Neuron, DOI 10.1016/j.neuron.2011.08.016
    ∘ switch between field recording and patch clamp or sharp electrode recordings
     (theoretically possible, but then one may also think of this as being two
    distinct pathways)
    
"""
    @with_doc(concatenate_blocks, use_header=True, header_str = "See also:")
    def __init__(self, name:str, /, *args,
                 segments:typing.Optional[GeneralIndexType] = None,
                 response:typing.Optional[typing.Union[str, int]] = None, 
                 analogStimulus:typing.Optional[typing.Union[str, int]] = None, 
                 digitalStimulus:typing.Optional[typing.Union[str, int]] = None, 
                 electrodeMode:ElectrodeMode = ElectrodeMode.Field,
                 clampMode:ClampMode = ClampMode.NoClamp,
                 xtalk:typing.Optional[typing.List[SynapticPathway]] = None,
                 pathways:typing.Optional[typing.List[SynapticPathway]] = None,
                 sortby:typing.Optional[typing.Union[str, typing.Callable]] = None,
                 ascending:typing.Optional[bool] = None,
                 glob:bool = True,
                 **kwargs):
        """Constructor for PathwayEpisode.
Mandatory parameters:
--------------------
name:str - the name of this episode

Var-positional parameters (args):
--------------------------------
neo.Blocks, or a sequence of neo.Blocks, a str, or a sequence of str
    When a str or a sequence of str, these are (a) symbol(s) in the workspace,
    bound to neo.Blocks

    When a str, if it contains the '*' character then the str is interpreted as 
    a global search string (a 'glob'). See neoutils.concatenate_blocks(…) for 
    details.

    NOTE: args represent the source data to which this episode applies to, but
is NOT stored in the PathwayEpisode instance. The only use of the data is to
assign values to the 'begin', 'end', 'beginFrame', 'endFrame' attributes of the 
episode.

Named parameters:
------------------
These are the attributes of the instance (see the class documentation), PLUS
the parameters 'segments', 'glob', 'sortby' and 'ascending' with the same types
and semantincs as for the function neoutils.concatenate_blocks(…).

NOTE: Data is NOT concatenated here, but these two parameers are used for 
        temporarily ordering the source neo.Block objects in args.

Var-keyword parameters (kwargs)
-------------------------------
These are passed directly to the datatypes.Episode superclass (see documentation
for Episode)

See also the class documentation.
    """
        if not isinstance(name, str):
            name = ""
        super().__init__(name, **kwargs)
        
        self.response=response
        self.analogStimulus = analogStimulus
        self.digitalStimulus = digitalStimulus
        
        if not isinstance(electrodeMode, ElectrodeMode):
            electrodeMode = ElectrodeMode.Field
        
        self.electrodeMode = electrodeMode
        
        if not isinstance(clampMode, ClampMode):
            clampMode = ClampMode.NoClamp
            
        self.clampMode = clampMode
        
        if isinstance(pathways, (tuple, list)):
            if len(pathways):
                if not all(isinstance(v, SynapticPathway) for v in pathways):
                    raise TypeError(f"'pathways' must contain only SynapticPatwhay instances")
            self.pathways = pathways
        else:
            self.pathways = []
        
        if isinstance(xtalk, (tuple, list)):
            if len(xtalk):
                if not all(isinstance(v, SynapticPathway) for v in xtalk):
                    raise TypeError(f"'xtalk' must contain only SynapticPatwhay instances")
                
            self.xtalk = xtalk
            
        else:
            self.xtalk = []
                
        sort = sortby is not None
        
        reverse = not ascending
        
        if len(args): 
            if all(isinstance(v, neo.Block) for v in args):
                source = args
                
            elif all(isinstance(v, str) for v in args):
                source = wf.getvars(*args, var_type = (neo.Block,),
                               sort=sort, sortkey = sortby, reverse = reverse)
                
            elif len(args) == 1:
                if isinstance(args[0], (tuple, list)) :
                    if all(isinstance(v, neo.Block) for v in args[0]):
                        source = args[0]
                        
                    elif all(isinstance(v, str) for v in args[0]):
                        source = wf.getvars(args[0], var_type = (neo.Block,),
                                          sort=sort, sortkey = sortby, reverse=reverse)
                
            else:
                raise TypeError(f"Bad source arguments")
        else:
            source = []
        
        if len(source):
            self.begin = source[0].rec_datetime
            self.end = source[-1].rec_datetime
            if segments is not None:
                seg_ndx = [normalized_index(b.segments, index=segments) for b in source]
                nsegs = sum(len(n) for n in seg_ndx)
            else:
                nsegs = sum(len(b.segments) for b in source)
            self.beginFrame = 0
            self.endFrame = nsegs-1 if nsegs > 0 else 0
        
    def _repr_pretty_(self, p, cycle):
        supertxt = super().__repr__() + " with :"
    
        if cycle:
            p.text(supertxt)
        else:
            p.text(supertxt)
            p.breakable()
            attr_repr = [" "]
            attr_repr += [f"{a}: {getattr(self,a).__repr__()}" for a in ("response", "analogStimulus",
                                                         "digitalStimulus",
                                                         "electrodeMode",
                                                         "clampMode")]
            
            with p.group(4 ,"(",")"):
                for t in attr_repr:
                    p.text(t)
                    p.breakable()
                p.text("\n")
                
            p.text("\n")
                
            p.text("Pathways:")
            p.breakable()
            
            if isinstance(self.pathways, (tuple, list)) and len(self.pathways):
                with p.group(4, "(",")"):
                    for pth in self.pathways:
                        p.text(pth.name)
                        p.breakable()
                    p.text("\n")
                
            if isinstance(self.xtalk, (tuple, list)) and len(self.xtalk):
                link = " \u2192 "
                p.text(f"Test for independence: {link.join([pth.name for pth in self.xtalk])}")
                p.breakable()
                p.text("\n")
                
            p.breakable()
        
@with_doc(BaseScipyenData, use_header=True)
class SynapticPathway(BaseScipyenData):
    """Encapsulates a logical stimulus-response relationship between signals.

    Signals are identified by name or their integer index in the collection of a 
    neo.Segment (sweep) analogsignals. They are NOT stored in the SynapticPathway
    instance.

    These signals are:
    • response (analog, regularly sampled): recorded synaptic responses
    
    • analogStimulus (analog, regularly sampled): the recorded command waveform;
        typically, this is a record of the secondary output of the amplifier, 
        when available, that has been fed into an auxiliary analog input port of
        the acquisition device; this signal carries the amplifier "command", e.g. 
        the voltage command in voltage clamp, or injected current, in current clamp.
    
    • digitalStimulus (analog, regularly sampled): the TTL (a.k.a the "digital")
        output signal from the acquisition board, typically recorded by feeding this 
        output into an analog input port, when available.
    
    Of these, only the first ("response") is required, whereas the others can be
    None. When present, these command signals are analysed to determine the 
    protocol used (i.e., the clamping voltage, and the timings of the presynaptic
    stimulation). Otherwise, these parameters need to be entered manually for 
    further analysis.

    In addition, the synaptic pathway has a pathwayType attribute which specifies
    the pathway's role in a synaptic plasticity experiment.
    
    """
    _data_children_ = (
        ("data", neo.Block(name="Data")),
        )
    
    _data_attributes_ = (
        ("pathwayType", PathwayType, PathwayType.Test),
        ("responseSignal", (str, int), 0),
        ("analogCommandSignal", (str, int), 1),
        ("digitalCommandSignal", (str, int), 2),
        ("schedule", Schedule, Schedule()),         # one or more PathwayEpisode objects
        )
    
    _descriptor_attributes_ = _data_children_ + _data_attributes_ + BaseScipyenData._descriptor_attributes_
    
    @with_doc(concatenate_blocks, use_header = True)
    def __init__(self, *args, data:typing.Optional[neo.Block] = None, 
                 pathwayType:PathwayType = PathwayType.Test, 
                 name:typing.Optional[str]=None, 
                 index:int = 0,
                 segments:GeneralIndexType=0,
                 response:typing.Optional[typing.Union[str, int]]=None, 
                 analogStimulus:typing.Union[typing.Union[str, int]] = None, 
                 digitalStimulus:typing.Optional[typing.Union[str, int]] = None, 
                 schedule:typing.Optional[typing.Union[Schedule, typing.Sequence[PathwayEpisode]]] = None, 
                 **kwargs):
        """SynapticPathway constructor.

Var-positional parameters (may be empty)
-----------------------------------------
When present, they specify source neo.Block objects wthat will need to be 
    concatenated to create the underlying data.

Named parameters:
-----------------
data: A neo.Block obtained from concatenating several source neo.Blocks (see the
    function neoutils.concatenate_blocks(…) for details). Optional, default is 
    None.
    
    When specified, the values in *args will be ignored.
    
pathwayType: PathwayType
    The role of the pathway in a synaptic plasticity experiment
                (Test, Control, Other)

name: str
     Name of the pathway (by default is the name of the pathwayType)
    
index: int
    The index of the Pathway ( >= 0); default is 0
    
segments: GeneralIndexType¹
    The index of the segments in the source data in *args.
    
    Used only when 'data' is constructed by concatenating the neo.Blocks in *args

response: GeneralIndexType
    The index of the analog signal(s) containing the synaptic response.
    Default is None.
    
    NOTE: This is also used when 'data'is constructed from *args. Therefore, it
    should typically resolve to subset of signals distinct from those indicated 
    by the 'analogStimulus' and 'digitalStimulus' parameters (see next)
    

analogStimulus: GeneralIndexType
    Index of the analog signal(s) containing the clamping command, or None.
    NOTE: Also used to construct the data from *args.

digitalStimulus: GeneralIndexType
    Index of the analog signal(s) containing the digital command, or None (default)
    NOTE: Also used to construct the data from *args.
    
schedule: a Schedule, or a sequence (tuple, list) of PathwayEpisodes; 
        optional, default is None.
    
    CAUTION: Currently, the episodes (whether packed in a Schedule or given as a
    sequence) are NOT checked for consistency with the number and recording time 
    stamps of the segments in the 'data' parameter.
    
Var-keyword parameters (kwargs):
--------------------------------
These are passed directly to the superclass constructor (BaseScipyenData).
    
Notes:
-----
¹see core.utilities.GeneralIndexType
    
    """
        super().__init__(**kwargs)
        
        # if not isinstance(data, neo.Block):
        #     if len(args):
        #         data = concatenate_blocks(*args, segments=segments)
        
    @staticmethod
    def fromBlocks(pathName:str, pathwayType:PathwayType=PathwayType.Test, 
                   *episodeSpecs:typing.Sequence[PathwayEpisode]):
        """
        Factory for SynapticPathway.
        
        Parameters:
        ==========
        pathName:str - name of the pathway
        pathwayType:PathwayType - the type of the pathway (optional, default is PathwayType.Test)
        
        *episodeSpecs: sequence of PathwayEpisode objects
            see help PathwayEpisode
        
        """
        
        
        
        # NOTE: 2023-05-19 17:08:53
        # an episode spec is a mapping of str ↦ sequence of neo Blocks
        # 
        # The blocks in the sequence are ordered here by their rec_datetime
        # WARNING/TODO: check argument types
        #
        
        epiNameSet = set(episodeSpecs.keys())
        
        if len(epiNameSet) != len(episodeSpecs):
            dupl_ = [k for k in episodeSpecs.keys() if k not in epiNameSet]
            raise ValueError(f"Duplicate episode names were specified: {dupl_}")
        
        nBlocks = sum(len(bl) for bl in episodeSpecs.values())
        
        segments = list()
        
        episodes = list()
        episodeBlocks = list() # temporary store of episode blocks
                            # will be concatenated to generate final data for the
                            # pathway
                            
        # NOTE: 2023-05-20 11:06:02
        # Because we want to concatenate all segments in a single neo.Block for
        # this pathway (associated with the 'data' field) we store references
        # to the start frame & end frame in the episode
        beginFrame = 0
        
        for episodeName, blocks, in episodeSpecs.items():
            bb = sorted(blocks, key = lambda x: x.rec_datetime)
            
            for k, b in enumerate(bb):
                try:
                    _ = normalized_index(b.segments, segments) 
                except:
                    raise ValueError(f"Invaid segment index {segments} for block {k} ({b.name}) in episode {episodeName}")
            
            datetime_start = bb[0].rec_datetime
            datetime_end = bb[-1].rec_datetime
            
            # TODO/FIXME: 2023-05-21 23:41:45
            # copy segments directly with data subset, here
            # fullBlockList.extend(bb)
            
            # episodeBlock = concatenate_blocks(*bb, segments=segments,
            #                                   analogsignals=analogsignals,
            #                                   irregularlysampledsignals=irregularlysampledsignals,
            #                                   imagesequences=imagesequences,
            #                                   spiketrains=spiketrains,
            #                                   epochs=epochs,event=events)

            

            episodes.append(Episode(episodeName, 
                              begin=datetime_start,
                              end=datetime_end,
                              beginFrame=beginFrame,
                              endFrame=beginFrame + sum(len(b.segments) for b in bb)-1))
            
            # episodeBlocks.append(episodeBlock)
            
            beginFrame += len(episodeBlock.segments)
            
        data = concatenate_blocks(*episodeBlocks) # no data subset selection here
        
        schedule = Schedule(episodes)
        
        return SynapticPathway(data=data, name=pathName,
                               pathwayType=pathwayType,
                               response=response,
                               analogStimulus=analogStimulus,
                               digitalStimulus=digitalStimulus,
                               schedule=schedule)
        
        
class SynapticPlasticityData(BaseScipyenData):
    _data_children_ = (
        ("pathways", (list, tuple), SynapticPathway),
        )
    
    _derived_data_children_ = (
        ("Rs", neo.IrregularlySampledSignal, neo.IrregularlySampledSignal([], [], units=pq.Mohm, time_units=pq.s, name="Rs")),
        ("Rin", neo.IrregularlySampledSignal, neo.IrregularlySampledSignal([], [], units=pq.Mohm, time_units=pq.s, name="Rin")),
        ("SynapticResponse", list, neo.IrregularlySampledSignal, neo.IrregularlySampledSignal([], [], units=pq.dimensionless, time_units=pq.s, name="")) # one per pathway
        )
    
    
    _result_data_ = (
        ("result", pd.DataFrame),
        )
    
    _graphics_attributes_ = (
        ("dataCursors", dict),
        ("epochs", dict)
        )
    
    _data_attributes_ = (
        ("clampMode", ClampMode, ClampMode.VoltageClamp),
        ("electrodeModel", ElectrodeMode, ElectrodeMode.WholeCellPatch),
        ("baselineReference", range),
        )
    
    _option_attributes_ = ()
    
    _descriptor_attributes_ = _data_children_ + _derived_data_children_ + _result_data_ + _data_attributes_ + _graphics_attributes_ + BaseScipyenData._descriptor_attributes_
        
    def __init__(self, pathways:typing.Optional[typing.Sequence[SynapticPathway]]=None, **kwargs):
        super().__init__(**kwargs)
        
    # def __reduce__(self): # TODO
    #     pass
    
class LTPOnline(object):
    # TODO: 2023-09-27 15:42:11
    # the DirectoryFileWatcher should also know about the directory
    # being watched; unlink from mainWindow changing of work dir i.e, keep
    # watching the same directory even if the user navigates somewhere else in
    # Scipyen's main window => needs change in mainwindow (ScipyenWindow) code
    #------------------------------------------------------------------------
    # we need to watch out for new files output by clampex
    #
    # these can be an xyz.abf file and/or xyz.rsv file
    #
    # it seems like an rsv file is always created, regardless of
    #   whether the protocol enables automatic analysis in other
    #   programs or uses multiple runs per trial (thus only saving the
    #   averaged data)
    #
    #   the rsv file is temporary; when its is created, Clampex also
    #   created an abf file with the same name, in the working directory
    #   such that the only rsv file present is paired with the newly created
    #   abf file.

    #   when an xyz.rsv and xyz.abf are newly created:
    #       IF they have the same path (without extension) =>
    #       the rsv file is a temporary store for ABF data in
    #       its paired abf file => we do not read the abf file until
    #       the rsv file has been removed (by Clampex)
    #
    #
    # my tests so far using the mainWindow.dirFileMonitor indicate
    # that the rsv file is created BEFORE its paired abf file
    #
    # but I don't think this is guaranteed?
    #
    # here is a typical sequence of events during a Clampex run
    #   ScipyenWindow._slot_directoryChanged newItems = {'base_0002.rsv'}
    #   ScipyenWindow._slot_directoryChanged newItems = {'base_0002.abf'}
    #   ScipyenWindow._slot_directoryChanged removedItems = {'base_0002.rsv'}
    #   ScipyenWindow._slot_directoryChanged changedItems = ('base_0002.abf',)
    #
    # So, basically this means that
    #
    #   1) at the start of a trial Clampex creates the rsv file THEN the ABF file
    #   2) during the trial data is (probably) stored in the rsv file (although
    #       there is nothing in the file system to indicate this has changed)
    #   3) at end of trial, Clampex:
    #   3.1) removes the rsv file => file removed signal above
    #   3.2) writes the recorded (and maybe averaged¹) data to the abf file
    #       => file changed signal above
    #
    #       ¹ NOTE: when the trial has > 1 runs
    #
    #  Algorithm:
    #
    # when a new rsv file is received, it is pushed (append) in the queue
    # when a new abf file is received:
    #   push it to the queue (append)
    #       check to see if it is paired with an abf file in the queue
    #       for now assume it isn't => wait for a paired abf to arrive
    #   check if it is paired with an rsv in the queue =>
    #       if it isn't then wait until a paired rsv arrives
    #       (for now assume it is paired with the rsv file added just before it)
    # when the latest rsv file is removed:
    #       wait for the paired abf file to change
    #       exit the rsv from the queue
    # when the paired abf file has changed => do stuff with it:
    #       if it is the first one (i.e., first trial²) in the experiment:
    #           parse the protocol for membrane test and a digital pulse train
    #           of one or two pulses ->:
    #               extract the membrane test timings and intensity from the
    #                   comand waveform
    #               figure out if there are alernate pathways (they SHOULD be)
    #               extract the digital train pulses; if pulse count is 2, figure
    #                   out if this is a paired pulse (i;e in the same pathway)
    #                   or a test for crosstalk
    #
    #           expect two sweeps (one per pathway) -> plot them in separate
    #               signal viewer windows
    #
    #           use the parsed protocol or the user's configuration³ to set up
    #               cursors
    #
    #           if the protocol says averaging in use then measure Rs Rin, DC,
    #               and EPSC amplitude(s)
    #
    #                   distribute the results to the same (if paired pulse) or
    #                   alternative dathways  (crosstalk test)
    #
    #                   plot the point in separate signal viewers
    #
    #           else:
    #               the user config should mention how to average
    #               as more files are loaded, perform the average, then
    #                   measure on the final result, as above
    #               save the final result
    #
    #       else
    #           parse the protocol as above, check against the already created one
    #           check protocol is the same
    #           measure as above
    #
    # When eperiment is stopped, stop the session (manually)
    #
    # ² NOTE: how to determine that ?!? the counter may not always start at 0000!
    #
    # ³ NOTE: decide what a configuration should look like: numbers for coordinates,
    #       cursor objects, epochs, etc? - should it be passed to the __init__,
    #       or read from a file, etc?
    #

    test_protocol_properties = ("activeDACChannelIndex",
                                "nSweeps",
                                "acquisitionMode",
                                "samplingRate",
                                "alternateDigitalOutputStateEnabled",
                                "alternateDACOutputStateEnabled")

    def __init__(self, emitterWindow:typing.Optional[QtWidgets.QMainWindow] = None,
                 directory:typing.Optional[typing.Union[str, pathlib.Path]] = None):

        wsp = wf.user_workspace()
        
#         print(f"LTPOnline.__init__ wsp: {len(wsp)}")
#         
#         assignin(wsp, "wsp")
        
        if emitterWindow is None:
            self._emitterWindow_ = wsp["mainWindow"]

        elif type(emitterWindow).__name__ != 'ScipyenWindow':
            raise ValueError(f"Expecting an instance of ScipyenWindow; instead, got {type(emitterWindow).__name__}")

        else:
            self._emitterWindow_ = emitterWindow

        if directory is None:
            self._watchedDir_ = pathlib.Path(self._emitterWindow_.currentDir).absolute()
            
        elif isinstance(directory, str):
            self._watchedDir_ = pathlib.Path(directory)

        elif isinstance(directory, pathlib.Path):
            self._watchedDir_ = directory
            
        else:
            raise TypeError(f"'directory' expected to be a str, a pathlib.Path, or None; instead, got {type(directory).__name__}")
        
        
        self._filesQueue_ = collections.deque()

        # cbDict = dict(newFiles = self.newFiles, changedFiles = self.changedFiles,
        #               removedFiles = self.removedFiles)

        self._monitor_ = DirectoryFileWatcher(emitter = self._emitterWindow_,
                                                 directory = self._watchedDir_,
                                                 observer = self)
        
        # print(f"{self.__class__.__name__}.__init__ to watch: {self._watchedDir_}\n")

        self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, True)
        
        self._pending_ = dict() # pathlib.Path are hashable; hence we use the RSV ↦ ABF

        self._latestAbf_ = None # last ABF file to have been created by Clampex

        self._abfProtocol_ = None

        # TODO: 2023-09-29 13:57:13
        # make this an intelligent thing - use SynapticPathway, PathwayEpisodes, etc.
        #
        # for now, baseline & chase are just one or two neo.Blocks
        self._data_ = dict(baseline = dict(path0 = neo.Block(), path1 = neo.Block()),
                           conditioning = dict(path0 = neo.Block(), path1 = neo.Block()),
                           chase = dict(path0 = neo.Block(), path1 = neo.Block()))

        self._viewer_path0_Records = self._emitterWindow_.newViewer(sv.SignalViewer)
        self._viewer_path0_Amplitudes = self._emitterWindow_.newViewer(sv.SignalViewer)
        self._viewer_path1_Records = self._emitterWindow_.newViewer(sv.SignalViewer)
        self._viewer_path1_Amplitudes = self._emitterWindow_.newViewer(sv.SignalViewer)

        self._viewer_Rseries = self._emitterWindow_.newViewer(sv.SignalViewer)
        self._viewer_DC = self._emitterWindow_.newViewer(sv.SignalViewer)
        
        self._a_ = 0


    def __del__(self):
        if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)

        super().__del__()

    @property
    def data(self) -> dict:
        return self._data_

    def stop(self):
        if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)
            
        monitoredFiles = self._monitor_._source_.dirFileMonitor.files()
        if len(monitorFiles):
            self._monitor_._source_.dirFileMonitor.removePaths(monitoredFiles)
            
        self._a_ = 0

    def start(self, directory:typing.Optional[typing.Union[str, pathlib.Path]] = None):
        if self._emitterWindow_ is None:
            raise ValueError("You must set an emiter window first...")

        if directory is None:
            if self._watchedDir_ is None:
                self._watchedDir_ = pathlib.Path(self._emitterWindow_.currentDir).absolute()

        elif isinstance(directory, str):
            self._watchedDir_ = pathlib.Path(directory)

        elif isinstance(directory, pathlib.Path):
            self._watchedDir_ = directory

        else:
            raise TypeError(f"'directory' expected to be a str, a pathlib.Path, or None; instead, got {type(directory).__name__}")
    
        if self._monitor_.directory != self._watchedDir_:
            self._monitor_.directory = self._watchedDir_

        self._a_ = 0
        self._pending_.clear() # pathlib.Path are hashable; hence we use the RSV ↦ ABF

        self._latestAbf_ = None # last ABF file to have been created by Clampex

        self._abfProtocol_ = None

        self._data_["baseline"]["path0"].segments.clear()
        self._data_["baseline"]["path1"].segments.clear()
        self._data_["chase"]["path0"].segments.clear()
        self._data_["chase"]["path1"].segments.clear()
        self._data_["conditioning"]["path0"].segments.clear()
        self._data_["conditioning"]["path1"].segments.clear()
        
        if not self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, True)
            

    def newFiles(self, val:typing.Union[typing.Sequence[pathlib.Path]]):
        print(f"{self._a_} ⇒ {self.__class__.__name__}.newFiles {[v.name for v in val]}\n")
        self._filesQueue_.extend(val)
        self._setupPendingAbf_()

        # print(f"\t→ pending: {self._pending_}\n")
        self._a_ += 1

    def changedFiles(self, val:typing.Union[typing.Sequence[pathlib.Path]]):
        print(f"{self._a_} ⇒ {self.__class__.__name__}.changedFiles {[v.name for v in val]}\n")
        # print(f"\t→ latestAbf = {self._latestAbf_}\n")
        self._a_ += 1
        
        
        # if not all(isinstance(v, pathlib.Path) and v.parent == self._watchedDir_ and v.suffix in (".rsv", ".abf") for v in val):
        #     return

        # if len(val) > 1:
        #     # CAUTION!
        #     return

        # changed = val[0]

        # expecting to see an ABf files changed by clampex AFTER removal of its
        # paired rsv

        # NOTE: 2023-10-01 21:46:24
        # not here !
#         if changed == self._latestAbf_:
#             # print(f"\t→ to process: {changed}\n")
#             
#             # self.processAbfFile(changed)
#             self._pending_.clear()
#             self._latestAbf_ = None
            

    def removedFiles(self, val:typing.Union[typing.Sequence[pathlib.Path]]):
        print(f"{self._a_} ⇒ {self.__class__.__name__}.removedFiles {[v.name for v in val]}\n")
        self._a_ += 1
        if not all(isinstance(v, pathlib.Path) and v.parent == self._watchedDir_ and v.suffix in (".rsv", ".abf") for v in val):
            return

        # if len(val) > 1:
        #     # CAUTION!
        #     return

        removed = val[0]

        # expecting the rsv file to be removed by Clampex at this stage
        # print(f"\t→ pending = {self._pending_}\n")
        if removed.suffix == ".rsv":
            if removed in self._pending_:
                self._latestAbf_ = self._pending_[removed]
                # print(f"\t\t→ latest = {self._latestAbf_}\n")
                self._pending_.clear()
                # NOTE: to stop monitoring abf file after it has been processed
                # in the processAbfFile(…)

    def processAbfFile(self, abfFile:pathlib.Path):
        # WARNING: the AbF file may not be completed at this time, depending on when this is called!
        
        # fileStat = abfFile.stat()
        # sz0 = fileStat.st_size
        # k=0
        # while abfFile.stat().st_size > sz0 and k < 10:
        #     k += 1
        #     print(f"{sz0} → file size: {abfFile.stat().st_size}")
        
        return 
    
        abfRun = pio.loadAxonFile(str(abfFile))
        protocol = pab.ABFProtocol(abfRun)

        # NOTE: 2023-09-29 14:12:56
        # we need:
        #
        # 1) the recording mode must be the same, either:
        #   VoltageClamp, CurrentClamp, or NoClamp (i=0), for field recordings
        #
        # 2) on the active DAC index there must be epochs:
        #   2.a) for patch clamp experiments:
        #       2.a.0) optional baseline step epoch with firstLevel == 0 and deltaLevel == 0
        #           alternatively the next epoch must start at First Duration > 0
        #       2.a.1) for membrane test: step epoch with firstLevel != 0, in :
        #           [mV] for VoltageClamp,
        #           [pA] for CurrentClamp


        if self._abfProtocol_ is None: # FIXME: 2023-09-29 14:32:24 see next line
            # make the condition here that data blocks have no segments
            self._abfProtocol_ = protocol

        # else:
        #     # make sure protocols are compatible
        #     assert all(getattr(protocol, x, None) == getattr(self._abfProtocol_, x, None)), "Abf files have incompatible protocols"

        # WARNING this is bogus code - it runs, but what it does in only part of
        # what this object is intended to do

        # TODO: 2023-09-29 14:23:21
        # check that the abf has as many segments as advertised in the protocol
        if len(abfRun.segments) != self._abfProtocol_.nSweeps:
            warnings.warn(f"abf has {len(abfRun.segments)} but protocol says {self._abfProtocol_.nSweeps}")
            # return

        if len(abfRun.segments) == 1:
            # => single pathway! CAUTION may backfire when recording is interrupted in Clampex
            # TODO: for now we just populate the baseline
            # but in the real world we need to distinguish between various episodes
            self._data_["baseline"]["path0"].segments.append(abfRun.segments[0])

            self._viewer_path0_Records.view(self._data_["baseline"]["path0"],showFrame = len(self._data_["baseline"]["path0"].segments)-1)

        elif len(abfRun.segments) == 2: # WARNING we only support two alternative pathways
            self._data_["baseline"]["path0"].segments.append(abfRun.segments[0])
            self._viewer_path0_Records.view(self._data_["baseline"]["path0"],showFrame = len(self._data_["baseline"]["path0"].segments)-1)
            self._data_["baseline"]["path1"].segments.append(abfRun.segments[1])
            self._viewer_path1_Records.view(self._data_["baseline"]["path1"],showFrame = len(self._data_["baseline"]["path1"].segments)-1)

    def filesChanged(self, filePaths:typing.Sequence[str]):
        # print(f"{self._a_} → {self.__class__.__name__}.filesChanged {filePaths}\n")
        for f in filePaths:
            fp = pathlib.Path(f)
            stat = fp.stat()
            print(f"\t → {fp.name}: {stat.st_size}, {stat.st_atime_ns, stat.st_mtime_ns, stat.st_ctime_ns}")
        # self._a_ += 1
        
    def _rsvForABF_(self, abf:pathlib.Path):
        """Returns the rsv file paired with the abf"""
        paired = [f for f in self._filesQueue_ if f.suffix == ".rsv" and f.stem == abf.stem and f.parent == abf.parent]
        if len(paired):
            return paired[0]

    def _abfForRsv_(self, rsv:pathlib.Path):
        paired = [f for f in self._filesQueue_ if f.suffix == ".abf" and f.stem == rsv.stem and f.parent == rsv.parent]
        if len(paired):
            return paired[0]
        
    def _setupPendingAbf_(self):
        self._pending_.clear()
        if isinstance(self._monitor_, DirectoryFileWatcher):
            monitoredFiles = self._monitor_._source_.dirFileMonitor.files()
            if len(monitoredFiles):
                self._monitor_._source_.dirFileMonitor.removePaths(monitoredFiles)
        else:
            raise RuntimeError("We haven't got a dirFileMonitor yet!")
        
        if len(self._filesQueue_) < 2:
            return
        
        latestFile = self._filesQueue_[-1]
        
        if latestFile.suffix == ".rsv":
            abf = self._abfForRsv_(latestFile)
            if isinstance(abf, pathlib.Path) and abf.is_file():
                self._pending_[latestFile] = abf
                
        elif latestFile.suffix == ".abf":
            rsv = self._rsvForABF_(latestFile)
            if isinstance(rsv, pathlib.Path) and rsv.is_file():
                self._pending_[rsv] = latestFile
            
        for rsv, abf in self._pending_.items():
            print(f"To monitor {abf.name}")
            self._monitor_.monitorFile(abf)
            

def makePathwayEpisode(*args, **kwargs) -> PathwayEpisode:
    """Helper function for the SynapticPathway factory function
    args: list of neo.Blocks
    name: str, default is ""
    pathways: list of SynapticPathways, default is []
    xtalk: list of SynapticPathways, default is []
    
"""
    name = kwargs.pop("name", "")
    
    if not isinstance(name, str):
        name = ""
        
    ret = PathwayEpisode(name)
    
    if len(args): 
        if all(isinstance(v, neo.Block) for v in args):
            source = args
            
        elif len(args) == 1 and isinstance(args[0], (tuple, list)) and all(isinstance(v, neo.Block) for v in args[0]):
            source = args[0]
            
        else:
            raise TypeError(f"Bad source arguments")
    else:
        source = []
    
    pathways = kwargs.pop("pathways", [])
    if isinstance(pathways, (tuple, list)):
        if len(pathways):
            if not all(isinstance(v, SynapticPathway) for v in pathways):
                raise TypeError(f"'pathways' must contain only SynapticPatwhay instances")
        ret.pathways = pathways
    else:
        ret.pathways = []
        
    xtalk = kwargs.pop("xtalk", [])
    
    if isinstance(xtalk, (tuple, list)):
        if len(xtalk):
            if not all(isinstance(v, SynapticPathway) for v in xtalk):
                raise TypeError(f"'xtalk' must contain only SynapticPatwhay instances")
            
            ret.xtalk = xtalk
            
        else:
            ret.xtalk = []
            
    if len(source):
        ret.begin = source[0].rec_datetime
        ret.end = source[-1].rec_datetime
        nsegs = sum(len(b.segments) for b in source)
        ret.beginFrame = 0
        ret.endFrame = nsegs-1 if nsegs > 0 else 0
        
    clampMode = kwargs.pop("clampMode", ClampMode.NoClamp)
    if not isinstance(clampMode, ClampMode):
        clampMode = ClampMode.NoClamp
        
    ret.clampMode = clampMode
    
    electrodeMode = kwargs.pop("electrodeMode", ElectrodeMode.Field)
    if not isinstance(electrodeMode, ElectrodeMode):
        electrodeMode = ElectrodeMode.Field
        
    ret.electrodeMode = electrodeMode
            
    return ret
    
def makeSynapticPathway(**kwargs):
    """Factory for a SynapticPathway
        Var-keyword parameters only:
        ---------------------------
        segments
        response
        analogStimulus
        digitalStimulus
        pathwayType
        episodes: list of episodeDicts:
            name
            source: list of blocks
            pathways: list of SynapticPathway or empty
            xtalk: list of SynapticPathway or empty
            
"""
    name = kwargs.pop("name", "")
    
    
    
def generate_synaptic_plasticity_options(npathways, mode, /, **kwargs):
    """Constructs a dict with options for synaptic plasticity experiments.
    
    Positional parameters:
    ======================
    npathways: int - the number of pathways recorded from - must be >= 1
        
    mode: int, one of 0, 1, 2 or str, one of "voltage", "current", or "field"
    
    Var-keyword parameters:
    =======================
    "pathways": dict with pathway designation, mapping a str (pathway type)
        to int (pathway index)
        
        e.g. {"test":0, "control":1, "ripples": 2, etc}
        
        default is {"test":0, "control":1}
        
        The keys must contain at least "test".
        
        The indices must be valid given the number of pathways in npathways
        
    "cursors": dict with vertical cursor coordinates for each pathway where 
        measurements are made, this must contain the following key-value pairs
        (default values are show below):
        
        "Labels" = ["Rbase", "Rs", "Rin", "EPSC0Base", "EPSC0Peak", "EPSC1Base", "EPSC1Peak"]
        "Windows" = [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]
        "Pathways" = [
                        [0.06, 0.066, 0.16, 0.26, 0.28, 0.31, 0.33],
                        [5.06, 5.066, 5.16, 5.26, 5.28, 5.31, 5.33]]
    
    "average":int = number of consecutive single-run trials to average 
        off-line (default: 6).
        
        NOTE: Any value < 2 indicates no off-line averaging. 
        
    "every":int   = number of consecutive single-run trials to skip before next 
        offline average (default: 6)
        
        NOTE: This is only considered when average is >= 2
        
    "reference":int  = number of minute-average responses used to assess 
        plasticity; this is the number of reponses at the end of the chase
        stage, and it equals the number of responses at the end of the baseline
        stage. Therefore it cannot be larger than the duration of the baseline 
        stage, in minutes.
        
        Default is 5 (i.e. compare the average of the last 5 minute-averaged 
            responses of the chase stage, to the average of the last 5 
            minute-averaged responses of the baseline stage, in each pathway)
            
            
    "cursor_measures": dict = cursor-based measurements used in analysis.
        Can be empty.
        
        Each key is a str (measurement name) that is mapped to a nested dict 
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
                
            "channel": (optional) if present, it must contain an int, which is
                the index of the signal where the cursors are used
            
            "pathway": int, the index of the pathway where the measurement is
                performed, or None (applied to both pathways)
                
        "epoch_measures": dict: epoch-based measurements
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
        
    "Im": str, int: name or index of the signal carrying synaptic responses (epscs, for
        voltage-clamp experiments) or command current (for current-clamp experiments)
        
        Default is 0
        
        NOTE: This signal must be present in all sweeps!
        
    "Vm": str, int: name or index of the signal carrying command voltage (for 
        voltage-clamp experiments) or synaptic responses (epsp, for current-clamp experiments)
        
        Default is 1
        
        NOTE: This signal must be present in all sweeps!
        
    "stim": list of signal names or indices containing the digital triggers 
        for the recorded pathways (e.g. 1st is for pathway 0, etc)
    
        Default is [2]
    
    Description
    ============
        
    The function constructs an options dict specifying synaptic pathways, 
    analysis cursors and optional minute-by-minute averaging of data from 
    synaptic plasticity experiments.
    
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
    6. Heuristic for cursors set up (single or paired pulse?); voltage clamp,
        current clamp,, or field recordings (we calculate Rs Rin only for voltage-clamp)
        
        
    """
    
    recording_types = {1:"voltage",2:"current", 3:"field"}
    
    if npathways < 1:
        raise ValueError(f"Expecting at least one pathway; got {npathways} instead")
    
    if isinstance(mode, str):
        if mode not in ("voltage", "current", "field"):
            raise ValueError(f"Invalid mode; expecting one of 'voltage', 'current', 'field'; got {mode} instead")
        
    elif isinstance(mode, int):
        if mode not in [1,2,3]:
            raise ValueError(f"Invalid mode; expecting 1, 2, or 3; got {mode} instead")
        
        mode = recording_types[mode]
        
    else:
        raise TypeError(f"Invalid mode type; expecting a str or int; got {type(mode).__name__} instead")
    
    # field = kwargs.pop("field", False)
#     
#     test_pathway_index = kwargs.pop("test", 0)
#     
#     if test_pathway_index < 0 or test_pathway_index >= npathways:
#         raise ValueError(f"Invalid test path index {test_pathway_index}; expecting a value between 0 and {npathways-1}")
#     
#     control_pathway_index = kwargs.pop("control", None)
#     
#     if npathways >= 2:
#         if control_path is None:
#             control_path = 1 if test_path == 0 else 0
#         elif control_path == test_path:
#             raise ValueError(f"control path cannot have the same index ({control_path}) as the test path index ({test_path})")
#     else:
#         control_path = None
        
#     if isinstance(control_path, int):
#         if control_path < 0 or control_path > 1:
#             raise ValueError("Invalid control path index (%d) expecting 0 or 1" % control_path)
#         
#         if control_path == test_path:
#             raise ValueError("Control path index must be different from the test path index (%d)" % test_path)
    
    average = kwargs.pop("average", 6)
    average_every = kwargs.pop("every", 6)
    
    reference = kwargs.pop("reference", 5)
    
    measure = kwargs.pop("measure", "amplitude")
    
    default_cursors_dict = dict()
    
    default_cursors_dict["Labels"] = ["Rbase", "Rs", "Rin", "EPSC0Base", "EPSC0Peak", "EPSC1Base", "EPSC1Peak"]
    default_cursors_dict["Windows"] = [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]
    default_cursors_dict["Pathways"] = list()
    default_cursors_dict["Pathways"].append([0.06, 0.066, 0.16, 0.26, 0.28, 0.31, 0.33])
    default_cursors_dict["Pathways"].append([c + 5 for c in default_cursors_dict["Pathways"][0]])
    
    cursors = kwargs.pop("cursors", default_cursors_dict)
    if len(cursors) == 0:
        raise ValueError(f"cursors must be specified")
    
    default_pathways = {"test":0}
    if npathways > 1:
        default_pathways["control"] = 1
    
    pathways = kwargs.pop("pathways", default_pathways)
    
    if "test" not in pathways.keys():
        raise ValueError("The index of the test pathway must be specified")

    if max(pathways.values()) >= npathways:
        raise ValueError(f"Invalid pathway value {max(pathways.values())} for {npathways} pathways")
    
    Im = kwargs.pop("Im", 0)
    Vm = kwargs.pop("Vm", 1)
    stim = kwargs.pop("stim", list())
    
    if len(stim) > npathways:
        raise ValueError(f"When specified, triggers must have the same length as the number of pathways or less")
    
    pathways_conf = list()

    for k in range(npathways):
        path = {"Im":Im, "Vm": Vm}
        
        if k < len(stim):
            path["stim"] = stim[k]
            
        if k < len(cursors["Pathways"]):
            path["cursors"] = cursors["Pathways"][k]
            
        path["assignment"] = reverse_mapping_lookup(pathways, k)
        
        pathways_conf.append(path)

    signals = [Im, Vm]
    signals.extend(stim)
    
    LTPopts = dict()
    
    LTPopts["Average"] = {'Count': average, 'Every': average_every}
    LTPopts["Pathways"] = pathways_conf

    LTPopts["Reference"] = reference
    
    LTPopts["Signals"] = signals
    
    LTPopts["Cursors"] = dict()
    LTPopts["Cursors"]["Labels"]  = cursors["Labels"]
    LTPopts["Cursors"]["Windows"] = cursors["Windows"]
    
    
#     if mode=="field":
#         LTPopts["Signals"] = kwargs.get("Signals",['Vm_sec_1'])
#         
#         if len(cursors):
#             LTPopts["Cursors"] = cursors
#             
#         else:
#             LTPopts["Cursors"] = {"fEPSP0_10": (0.168, 0.001), 
#                                   "fEPSP0_90": (0.169, 0.001)}
#             
#             #LTPopts["Cursors"] = {'Labels': ['fEPSP0','fEPSP1'],
#                                 #'time': [0.168, 0.169], 
#                                 #'Pathway1': [5.168, 5.169], 
#                                 #'Windows': [0.001, 0.001]} # NOTE: cursor windows are not used here
#             
#         
#     else:
#         LTPopts["Signals"] = kwargs.get("Signals",['Im_prim_1', 'Vm_sec_1'])
#         LTPopts["Cursors"] = {'Labels': ['Rbase','Rs','Rin','EPSC0Base','EPSC0Peak','EPSC1Base','EPSC1peak'],
#                               'Pathway0': [0.06, 0.06579859882206893, 0.16, 0.26, 0.273, 0.31, 0.32334583993039734], 
#                               'Pathway1': [5.06, 5.065798598822069,   5.16, 5.26, 5.273, 5.31, 5.323345839930397], 
#                               'Windows': [0.01, 0.003, 0.01, 0.01, 0.005, 0.01, 0.005]}
#         
    
    return LTPopts
    
def generate_LTP_options(cursors, signal_names, path0, path1, baseline_minutes, 
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
    
    Failing that, one can use Vm=True in further analyses and supply the value of the test Vm pulse in 
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
def load_synaptic_plasticity_options(LTPOptionsFile:[str, type(None)]=None, 
                                     **kwargs):
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
    
    if len(kwargs) == 0 and (LTPOptionsFile is None or len(LTPOptionsFile.strip()) == 0):
        LTPOptionsFile = os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl")
    
    if LTPOptionsFile is None or not os.path.isfile(LTPOptionsFile):
        
        LTPopts = generate_synaptic_plasticity_options(**kwargs)
        
        print("Now, save the options as %s" % os.path.join(os.path.dirname(__file__), "options", "LTPOptions.pkl"))
        
        #raise RuntimeError("No options file found. Have you ever run save_LTP_options ?")
    else:
        with open(LTPOptionsFile, "rb") as fileSrc:
            LTPopts = pickle.load(fileSrc)
        
    return LTPopts

@safeWrapper
def generate_minute_average_data_for_LTP(prefix_baseline, prefix_chase, 
                                         LTPOptions, test_pathway_index, result_name_prefix):
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
                                                segments = LTPOptions["Pathway0"],
                                                analogsignals = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_baseline"),
                    neoutils.concatenate_blocks(baseline_blocks,
                                                segments = LTPOptions["Pathway1"],
                                                analogsignals = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_baseline")]
    else:
        baseline    = [neoutils.average_blocks(baseline_blocks,
                                            segment = LTPOptions["Pathway0"],
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"],
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_baseline"),
                    neoutils.average_blocks(baseline_blocks,
                                            segment = LTPOptions["Pathway1"],
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"], 
                                            name = result_name_prefix + "_path1_baseline")]
              
    baseline[test_pathway_index].name += "_Test"
    baseline[1-test_pathway_index].name += "_Control"
    
    
    if LTPOptions["Average"] is None:
        chase   = [neoutils.concatenate_blocks(chase_blocks,
                                                segments = LTPOptions["Pathway0"],
                                                analogsignals = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path0_chase"),
                   neoutils.concatenate_blocks(chase_blocks,
                                                segments = LTPOptions["Pathway1"],
                                                analogsignals = LTPOptions["Signals"],
                                                name = result_name_prefix + "_path1_chase")]
        
    else:
        chase   = [neoutils.average_blocks(chase_blocks,
                                            segment = LTPOptions["Pathway0"], 
                                            analog = LTPOptions["Signals"],
                                            count = LTPOptions["Average"]["Count"], 
                                            every = LTPOptions["Average"]["Every"],
                                            name = result_name_prefix + "_path0_chase"),
                   neoutils.average_blocks(chase_blocks,
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
    Calculates the slope of field EPSPs. TODO
    
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
                                    signal_index_Im, /, 
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
    
    # print(f"calculate_LTP_measures_in_block signal_index_Im, {signal_index_Im}")
    
    if isinstance(signal_index_Im, str):
        signal_index_Im = ephys.get_index_of_named_signal(block, signal_index_Im)
        
    # print(f"calculate_LTP_measures_in_block signal_index_Im, {signal_index_Im}")
    
    if isinstance(signal_index_Vm, str):
        signal_index_Vm = ephys.get_index_of_named_signal(block, signal_index_Vm)
        
    if isinstance(trigger_signal_index, str):
        trigger_signal_index = ephys.get_index_of_named_signal(block, trigger_signal_index)
        
    for (k, seg) in enumerate(block.segments):
        #print("segment %d" % k)
        if isinstance(signal_index_Im, (tuple, list)):
            im_signal = signal_index_Im[k]
        else:
            im_signal = signal_index_Im
            
        if isinstance(signal_index_Vm, (tuple, list)):
            vm_signal = signal_index_Vm[k]
        else:
            vm_signal = signal_index_Vm
            
        (irbase, rs, rin, epsc0, epsc1, ppr, isi_) = segment_synplast_params_v_clamp(seg, 
                                                                                    im_signal, 
                                                                                    signal_index_Vm=vm_signal, 
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
        
        When present, it will be used to determine the inter-stimulus interval.
        
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
        
    membrane_test_intervals = [b"Rbase", b"Rs", b"Rin"]
    mandatory_intervals = [b"EPSC0Base", b"EPSC0Peak"]
    optional_intervals = [b"EPSC1Base", b"EPSC1Peak"]
    
    if epoch is None:
        if len(s.epochs) == 0:
            raise ValueError("Segment has no epochs, and no external epoch has been defined either")
        
        ltp_epochs = [e for e in s.epochs if (isinstance(e.name, str) and e.name.strip().lower() == "ltp")]
        
        if len(ltp_epochs) == 0:
            raise ValueError("Segment seems to have no LTP epoch defined, and no external epoch has been defined either")
        
        elif len(ltp_epochs) > 1:
            warnings.warn("There seem to be more than one LTP epoch defined in the segment; only the FIRST one will be used")
        
        epoch = ltp_epochs[0]
        
    if epoch.size != 5 and epoch.size != 7:
        raise ValueError("The LTP epoch (either supplied or embedded in the segment) has incorrect length; expected to contain 5 or 7 intervals")
    
    if epoch.labels.size == 0 or epoch.labels.size != epoch.size:
        raise ValueError("Mismatch between epoch size and number of labels in the epoch")
    
    membrane_test_intervals_ndx = [__interval_index__(epoch.labels, l) for l in membrane_test_intervals]
    mandatory_intervals_ndx = [__interval_index__(epoch.labels, l) for l in mandatory_intervals]
    optional_intervals_ndx = [__interval_index__(epoch.labels, l) for l in optional_intervals]
    
    
    # [Rbase, Rs, Rin]
    t_test = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in membrane_test_intervals_ndx]
    
    
    # [EPSC0Base, EPSC0Peak]
    t = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in mandatory_intervals_ndx]
    
    Idc    = np.mean(s.analogsignals[signal_index_Im].time_slice(t_test[0][0], t_test[0][1]))
    
    Irs    = np.max(s.analogsignals[signal_index_Im].time_slice(t_test[1][0], t_test[1][1])) 
    
    Irin   = np.mean(s.analogsignals[signal_index_Im].time_slice(t_test[2][0], t_test[2][1]))

    
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
        
        vm_signal = s.analogsignals[signal_index_Vm]
        
        if not units_convertible(vm_signal, pq.V):
            warnings.warn(f"The Vm signal has wrong units ({vm_signal.units}); expecting electrical potential units")
            warnings.warn(f"The Vm signal will be FORCED to correct units ({pq.mV}). If this is NOT what you want then STOP NOW")
            klass = type(vm_signal)
            vm_signal = klass(vm_signal.magnitude, units = pq.mV, 
                                         t_start = vm_signal.t_start, sampling_rate = vm_signal.sampling_rate,
                                         name=vm_signal.name)
        
        # vm_signal = s.analogsignals[signal_index_Vm].time_slice(t[0][0], t[0][1])
        # vm_signal = vm_signal.time_slice(t[0][0], t[0][1])
        
        Vbase = np.mean(vm_signal.time_slice(t_test[0][0], t_test[0][1])) # where Idc is measured
        # Vbase = np.mean(s.analogsignals[signal_index_Vm].time_slice(t[0][0], t[0][1])) # where Idc is measured
        #print("Vbase", Vbase)

        Vss   = np.mean(vm_signal.time_slice(t_test[2][0], t_test[2][1])) # where Rin is calculated
        # Vss   = np.mean(s.analogsignals[signal_index_Vm].time_slice(t[2][0], t[2][1])) # where Rin is calculated
        #print("Vss", Vss)
        
        testVm  = Vss - Vbase

    # print("testVm", testVm)
    
    Rs     = (testVm / (Irs - Idc)).rescale(pq.Mohm)
    Rin    = (testVm / (Irin - Idc)).rescale(pq.Mohm)
        
    #print("dIRs", (Irs-Idc), "dIRin", (Irin-Idc), "Rs", Rs, "Rin", Rin)
        
    Iepsc0base = np.mean(s.analogsignals[signal_index_Im].time_slice(t[0][0], t[0][1])) 
    
    Iepsc0peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t[1][0], t[1][1])) 

    EPSC0 = Iepsc0peak - Iepsc0base
    
    if len(epoch) == 7 and len(optional_intervals_ndx) == 2:
        
        # [EPSC1Base, EPSC1Peak]
        t = [(epoch.times[k], epoch.times[k] + epoch.durations[k]) for k in optional_intervals_ndx]
        
        Iepsc1base = np.mean(s.analogsignals[signal_index_Im].time_slice(t[0][0], t[0][1])) 
        
        Iepsc1peak = np.mean(s.analogsignals[signal_index_Im].time_slice(t[1][0], t[1][1])) 
        
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
            ltp_events = [e for e in s.events if (isinstance(e, TriggerEvent) and e.event_type == TriggerEventType.presynaptic and isinstance(e.name, str) and e.name.strip().lower() == "ltp")]
            
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
                           /, 
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

    The baseline and chase blocks are expected to contain segments from the same 
    synaptic pathway. That is, they were obtained by calling 
    neoutils.concatenate_blocks passing the index of the segments for the desired
    as the 'segments' parameter (see neoutils.concatenate_blocks for details)
    
    """
    # TODO 2020-10-26 09:18:18
    # analysis of fEPSPs
    # analysis of EPSPs (LTP experiments in I-clamp)
    
    #if field:
        #pass
        
    #else:
    
    # print(f"analyse_LTP_in_pathway signal_index_Im = {signal_index_Im}")


    baseline_result     = calculate_LTP_measures_in_block(baseline_block, signal_index_Im, 
                                                          signal_index_Vm = signal_index_Vm, 
                                                          trigger_signal_index = trigger_signal_index,
                                                          testVm = testVm, 
                                                          epoch = baseline_epoch,
                                                          stim = stim,
                                                          isi = isi)
    
    chase_result        = calculate_LTP_measures_in_block(chase_block, signal_index_Im, 
                                                            signal_index_Vm = signal_index_Vm, 
                                                            trigger_signal_index = trigger_signal_index,
                                                            testVm = testVm, 
                                                            epoch = chase_epoch,
                                                            stim = stim,
                                                            isi = isi)

    result = pd.concat([baseline_result, chase_result],
                       ignore_index = True, axis=0)#, sort=True)
    
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

# def LTP_analysis_new(path0_base:neo.Block, path0_chase:neo.Block, path0_options:dict,\
#                  path1_base:typing.Optional[neo.Block]=None, \
#                  path1_chase:typing.Optional[neo.Block]=None, \
#                  path1_options:typing.Optional[dict]=None,\
#                  basename:typing.Optional[str]=None):
#     """
#     path0_base: neo.Block with minute-averaged sweeps with synaptic responses
#             on pathway 0 before conditioning
#                 
#     path0_chase: neo.Block with minute-average sweeps with synaptic reponses
#             on pathway 0 after conditioning
#                 
#     path0_options: a mapping (dict-like) wiht the key/value items listed below
#             (these are passed directly as parameters to analyse_LTP_in_pathway):
#                 
#             Im: int, str                    index of the Im signal
#             Vm: int, str, None              index of the Vm signal
#             DIG: int, str, None             index of the trigger signal
#             base_epoch: neo.Epoch, None
#             chase_epoch: neo.Epoxh, None
#             testVm: float, python Quantity, None
#             stim: TriggerEvent, None
#             isi: float, Quantity, None
#             normalize: bool
#             field: bool                     Vm must be a valid index
#             is_test: bool
#             v_clamp:bool
#             index: int
#             baseline_sweeps: iterable (sequence of ints, or range)
#                 
#     
#     """
#     pass
    
def LTP_analysis(mean_average_dict, current_signal, vm_command, /, LTPOptions=None, 
                 results_basename=None, normalize=False):
    """
    LTP analysis for voltage-clamp experiments with paired-pulse stimulation
    interleaved on two pathways.
    
    Positional arguments:
    ====================
    mean_average_dict = dictionary (see generate_minute_average_data_for_LTP)
    
    current_signal: index or name of the signal carrying synaptic response (EPSCs)
    
    vm_command: index or name of the signal carrying the command voltage
    
    Named arguments:
    ================
    result_basename = common prefix for result variables
    LTPoptions      = dictionary (see generate_LTP_options()); optional, default 
        is None, expecting that mean_average_dict contains an "LTPOptions" key.
    
    normalize:bool  = flag whether to calculate EPSC amplitude normalization
                    default is False
        
    Returns:
    
    ret_test, ret_control - two dictionaries with results for test and control 
        (as calculated by analyse_LTP_in_pathway)
    
    NOTE 1: The segments in the blocks inside mean_average_dict must have already been assigned epochs from cursors!
    NOTE 2: The "Test" and "Control" dictionaries in mean_average_dict must contain a field "Path" with the actual path index
    
    """
    
    if results_basename is None:
        if "name" in mean_average_dict:
            results_basename = mean_average_dict["name"]
            
        else:
            warnings.warn("LTP Data dictionary lacks a 'name' field and a result basename has not been supplied; results will get a default generic name")
            results_basename = "Minute_averaged_LTP_Data"
            
    elif not isinstance(results_basename, str):
        raise TypeError("results_basename parameter must be a str or None; for %s instead" % type(results_basename).__name__)
    
    if LTPOptions is None:
        LTPOptions = mean_average_dict["LTPOptions"]
    
    ret_test = analyse_LTP_in_pathway(mean_average_dict["Test"]["Baseline"],
                                 mean_average_dict["Test"]["Chase"], 
                                 current_signal, 
                                 mean_average_dict["Test"]["Path"], 
                                 baseline_range=range(-1*LTPOptions["Reference"], -1),
                                 signal_index_Vm = vm_command,
                                 basename=results_basename+"_test", 
                                 normalize=normalize)
    
    ret_control = analyse_LTP_in_pathway(mean_average_dict["Control"]["Baseline"], 
                                         mean_average_dict["Control"]["Chase"], 
                                         current_signal,
                                         mean_average_dict["Control"]["Path"], 
                                         baseline_range=range(-1*LTPOptions["Reference"], -1),
                                         signal_index_Vm = vm_command,
                                         basename=results_basename+"_control", 
                                         normalize=normalize)
    
    return (ret_test, ret_control)


#"def" plotAverageLTPPathways(data, state, viewer0, viewer1, keepCursors=True, **kwargs):
def plotAverageLTPPathways(data, state, viewer0=None, viewer1=None,
                           keepCursors=True, **kwargs):
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
        
    
    viewer.setupCursors("v", LTPOptions["Cursors"]["Pathway%d"%pathway], 
                        xwindow = LTPOptions["Cursors"]["Windows"],
                        labels = LTPOptions["Cursors"]["Labels"])
        
def extract_sample_EPSPs(data, test_base_segments_ndx, test_chase_segments_ndx, 
                         control_base_segments_ndx, control_chase_segments_ndx, 
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
        
        
        
    average_test_base = neoutils.set_relative_time_start(ephys.average_segments([data["Test"]["Baseline"].segments[ndx] for ndx in test_base_segments_ndx], 
                                                        signal_index = data["LTPOptions"]["Signals"][0])[0])

    test_base = neoutils.set_relative_time_start(ephys.get_time_slice(average_test_base, t0, t1))
    
    average_test_chase = neoutils.set_relative_time_start(ephys.average_segments([data["Test"]["Chase"].segments[ndx] for ndx in test_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    test_chase = neoutils.set_relative_time_start(ephys.get_time_slice(average_test_chase, t0, t1))
    
    control_base_average = neoutils.set_relative_time_start(ephys.average_segments([data["Control"]["Baseline"].segments[ndx] for ndx in control_base_segments_ndx],
                                                            signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_base = neoutils.set_relative_time_start(ephys.get_time_slice(control_base_average, t0, t1))
    
    control_chase_average = neoutils.set_relative_time_start(ephys.average_segments([data["Control"]["Chase"].segments[ndx] for ndx in control_chase_segments_ndx],
                                          signal_index = data["LTPOptions"]["Signals"][0])[0])
    
    control_chase = neoutils.set_relative_time_start(ephys.get_time_slice(control_chase_average, t0, t1))
    
    
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


