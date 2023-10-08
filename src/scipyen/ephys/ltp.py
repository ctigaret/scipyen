# -*- coding: utf-8 -*-

#### BEGIN core python modules
import os, sys, traceback, inspect, numbers, warnings, pathlib, time
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
                            unique,
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
from gui.workspacegui import (DirectoryFileWatcher, FileStatChecker)
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

class _LTPOnlineSupplier_(QtCore.QThread):
    abfRunReady = pyqtSignal(pathlib.Path, name="abfRunReady")
    
    def __init__(self, parent,
                 abfRunBuffer:collections.deque, 
                 emitterWindow,
                 directory):
        QtCore.QThread.__init__(self, parent)
        # self._mutex_ = mutex
        # self._guard_ = guard
        self._abfRunBuffer_ = abfRunBuffer
        # self._bufferEmptyCondition_ = bufferEmptyCondition
        # self._bufferNotEmptyCondition_ = bufferNotEmptyCondition
        self._filesQueue_ = collections.deque()
        # print(f"{self.__class__.__name__}.__init__ to watch: {self._watchedDir_}\n")
        self._pending_ = dict() # pathlib.Path are hashable; hence we use the RSV ↦ ABF

        wsp = wf.user_workspace()
        
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
        
        # watches for changes (additions and removals of files) in the monitored
        # directory
        self._dirMonitor_ = DirectoryFileWatcher(emitter = self._emitterWindow_,
                                                 directory = self._watchedDir_,
                                                 observer = self)
        
        self._abfListener_ = FileStatChecker(interval = 10, maxUnchangedIntervals = 5,
                                             callback = self.supplyFile)

    def newFiles(self, val:typing.Union[typing.Sequence[pathlib.Path]]):
        """Needed by DirectoryFileWatcher"""
        # print(f"{self.__class__.__name__}.newFiles {[v.name for v in val]}\n")
        self._filesQueue_.extend(val)
        self._setupPendingAbf_()

        # print(f"\t→ pending: {self._pending_}\n")
        # self._a_ += 1

    def changedFiles(self, val:typing.Union[typing.Sequence[pathlib.Path]]):
        """Needed by DirectoryFileWatcher"""
        # print(f"{self.__class__.__name__}.changedFiles {[v.name for v in val]}\n")
        # print(f"\t→ latestAbf = {self._latestAbf_}\n")
        # self._a_ += 1
        pass
        
    def removedFiles(self, val:typing.Union[typing.Sequence[pathlib.Path]]):
        """Needed by DirectoryFileWatcher"""
        # print(f"{self.__class__.__name__}.removedFiles {[v.name for v in val]}\n")
        # self._a_ += 1
        if not all(isinstance(v, pathlib.Path) and v.parent == self._watchedDir_ and v.suffix in (".rsv", ".abf") for v in val):
            return

        # if len(val) > 1:
        #     # CAUTION!
        #     return

        removed = val[0]

        # expecting the rsv file to be removed by Clampex;
        # when this is done, watch the pending ABF file for changes
        # print(f"\t→ pending = {self._pending_}\n")
        if removed.suffix == ".rsv":
            if removed in self._pending_:
                self._latestAbf_ = self._pending_[removed]
                if self._abfListener_.active:
                    self._abfListener_.stop()
                if  not self._latestAbf_.exists() or not self._latestAbf_.is_file():
                    self._latestAbf_ = None
                    self._pending_.clear()
                    self._filesQueue_.clear()
                    return
                self._abfListener_.monitoredFile = self._latestAbf_
                self._abfListener_.start()
                # print(f"\t\t→ latest = {self._latestAbf_}\n")
                self._pending_.clear()
                # NOTE: to stop monitoring abf file after it has been processed
                # in the processAbfFile(…)
                
    def filesChanged(self, filePaths:typing.Sequence[str]):
        """
        Used in communicating with the directory monitor
        """
        # print(f"{self.__class__.__name__}.filesChanged {filePaths}\n")
        for f in filePaths:
            fp = pathlib.Path(f)
            stat = fp.stat()
            # print(f"\t → {fp.name}: {stat.st_size}, {stat.st_atime_ns, stat.st_mtime_ns, stat.st_ctime_ns}")
        # self._a_ += 1
        
    def _rsvForABF_(self, abf:pathlib.Path):
        """Returns the rsv file paired with the abf
        Used in communicating with the directory monitor
        """
        paired = [f for f in self._filesQueue_ if f.suffix == ".rsv" and f.stem == abf.stem and f.parent == abf.parent]
        if len(paired):
            return paired[0]

    def _abfForRsv_(self, rsv:pathlib.Path):
        """Returns the abf file paired with the rsv.
        Used in communicating with the directory monitor
        """
        paired = [f for f in self._filesQueue_ if f.suffix == ".abf" and f.stem == rsv.stem and f.parent == rsv.parent]
        if len(paired):
            return paired[0]
        
    def _setupPendingAbf_(self):
        """
        Used in communicating with the directory monitor
        """
        self._pending_.clear()

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
            if rsv in self._filesQueue_:
                self._filesQueue_.remove(rsv)
                
            if abf in self._filesQueue_:
                self._filesQueue_.remove(abf)
            
    def run(self):
        self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, True)
            

    def supplyFile(self, abfFile:pathlib.Path):
        # print(f"{self.__class__.__name__}.supplyFile to buffer: abfFile {abfFile.name}\n")
        self._abfListener_.reset()
        self.abfRunReady.emit(abfFile)
        
    @property
    def abfListener(self) -> FileStatChecker:
        return self._abfListener_
    
    @property
    def watchedDirectory(self) -> pathlib.Path:
        return self._watchedDir_

class _LTPOnlineFileProcessor_(QtCore.QThread):
    """Helper class for LTPOnline.
        Runs analysis on a single Clampex trial in a separate thread.
    """
    # def __init__(self, parent, abfBuffer:collections.deque,
    #              abfRunTimes:list, abfRunDeltaTimes:list, 
    #              adcChannel:int, dacChannel:int, clampMode:ephys.ClampMode, 
    #              monitorProtocol:pab.ABFProtocol, conditioningProtocol:pab.ABFProtocol,
    #              episode:str,
    #              responseBaselineDuration:pq.Quantity,
    #              mbTestAmplitude:pq.Quantity,
    #              mbTestStart: pq.Quantity,
    #              mbTestDuration: pq.Quantity,
    #              presynapticTriggers: dict,
    #              landmarks:dict,
    #              resultsData:dict, 
    #              resultsAnalysis:dict,
    #              viewers:dict,
    #              sigIndex:typing.Optional[int],
    #              signalAxes:list):
    def __init__(self, parent, abfBuffer:collections.deque,
                 abfRunParams:dict,
                 presynapticTriggers: dict,
                 landmarks:dict,
                 resultsData:dict, 
                 resultsAnalysis:dict,
                 viewers:dict):
        QtCore.QThread.__init__(self, parent)
        
        self._abfRunBuffer_ = abfBuffer
        # self._guard_ = guard
        # self._mutex_ = mutex
        # self._bufferEmptyCondition_ = bufferEmptyCondition
        # self._bufferNotEmptyCondition_ = bufferNotEmptyCondition
        # self._abfRunTimes_ = abfRunTimes
        # self._abfRunDeltaTimes_ = abfRunDeltaTimes
        # self._dacChannel_ = dacChannel
        # self._adcChannel_ = adcChannel
        # self._clampMode_ = clampMode
        # self._monitorProtocol_ = monitorProtocol
        # self._conditioningProtocol_ = conditioningProtocol
        # self._responseBaselineDuration_ = responseBaselineDuration
        # self._mbTestAmplitude_ = mbTestAmplitude
        # self._mbTestStart_ = mbTestStart
        # self._mbTestDuration_ = mbTestDuration
        self._runParams_ = abfRunParams
        self._presynaptic_triggers_ = presynapticTriggers
        self._landmarks_ = landmarks
        self._data_ = resultsData
        self._results_ = resultsAnalysis
        self._viewers_ = viewers
        # self._signalAxes_ = signalAxes
        # self._sigIndex_ = sigIndex
        
    @safeWrapper
    @pyqtSlot(pathlib.Path)
    def processAbfFile(self, abfFile:pathlib.Path):
        # print(f"{self.__class__.__name__}.processAbfFile: abfFile: {abfFile}\n")
        # WARNING: the Abf file may not be completed at this time, depending on when this is called!
        
        abfRun = pio.loadAxonFile(str(abfFile))
        
        self._runParams_._abfRunTimes_.append(abfRun.rec_datetime)
        deltaMinutes = (abfRun.rec_datetime - self._abfRunTimes_[0]).seconds/60
        self._runParams_._abfRunDeltaTimes_.append(deltaMinutes)
        
        protocol = pab.ABFProtocol(abfRun)

        # check that the number of sweeps actually stored in the ABF file/neo.Block
        # equals that advertised by the protocol
        # NOTE: mistamtches can happen when trials are acquired very fast (i.e.
        # back to back) - in this saase check the sequencing key in Clampex!
        assert(protocol.nSweeps) == len(abfRun.segments), f"In {abfRun.name}: Mismatch between number of sweeps in the protocol ({protocol.nSweeps}) and actual sweeps in the file ({len(abfRun.segments)}); check the sequencing key?"

        dac = protocol.outputConfiguration(self._runParams_._dacChannel_)
        

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

        # TODO/FIXME: 2023-10-03 23:25:04 - the following is a procedural convention
        # need to make it more generic
        # we assume the very first abfRun is a monitoring one => baseline episode
        # we add subsequent runs to the baseline episode until protocol changes
        #   => assume new protocol is conditioning protocol, which MAY be repeated
        #       for several runs => add subsequent runs to the conditioning episode
        #       until protocol changes again => the new protocol must be identical
        # to the monitoring protocol => chase episode
        #
        # TODO allow for several conditioning episodes (with same or different
        # conditioning protocols), possibly interleaved with monitoring episodes
        # which should have the same monitoring protocol
        #
        
        if self._runParams_._monitorProtocol_ is None:
            if protocol.clampMode() == self._runParams_._clampMode_:
                assert(protocol.nSweeps in range(1,3)), f"Protocols with {protocol.nSweeps} are not supported"
                if protocol.nSweeps == 2:
                    assert(dac.alternateDigitalOutputStateEnabled), "Alternate Digital Output should have been enabled"
                    assert(not dac.alternateDACOutputStateEnabled), "Alternate Waveform should have been disabled"
                    
                    # TODO check for alternate digital outputs → True ; alternate waveform → False
                    # → see # NOTE: 2023-10-07 21:35:39 - DONE ?!?
                self._monitorProtocol_ = protocol
                self.processMonitorProtocol(protocol)
            else:
                raise ValueError(f"First run protocol has unexpected clamp mode: {protocol.clampMode()} instead of {self._clampMode_}")
            
        else:
            if protocol != self._monitorProtocol_:
                # if self._conditioningProtocol_ is None:
                if len(self._conditioningProtocols_) == 0:
                    if protocol.clampMode() == self._conditioningClampModes_:
                        self._conditioningProtocol_ = protocol
                    else:
                        raise ValueError("Unexpected conditioning protocol")
                    
                else:
                    if protocol != self._conditioningProtocol_:
                        raise ValueError("Unexpected protocol for current run")
            
        if self._monitorProtocol_.nSweeps == 2:
            if not self._monitorProtocol_.alternateDigitalOutputStateEnabled:
                # NOTE: this is moot, because the protocol has already been checked
                # in the processMonitorProtocol
                raise ValueError("When the protocol defines two sweeps, alternate digtal outputs MUST have been enabled in the protocol")
            # NOTE: 2023-10-07 21:35:39
            # we are alternatively stimulating two pathways
            # NOTE: the ABF Run should ALWAYS have two sweeps in this case - one
            # for each pathway - regardless of how many runs there are per trial
            # if number of runs > 1 then the ABF file stores the average record
            # of each sweep, across the number of runs (or however the averaging mode
            # was set in the protocol; WARNING: this last bit of information is 
            # NOT currently used here)
            
        elif self._monitorProtocol_.nSweeps != 1:
            raise ValueError(f"Expecting 1 or 2 sweeps in the protocol; instead, got {self._monitorProtocol_.nSweeps}")
            
        # From here on we do things differently, depending on whether protocol is a
        # the monitoring protocol or the conditioning protocol
        if protocol == self._monitorProtocol_:
            adc = protocol.inputConfiguration(self._adcChannel_)
            sigIndex = neoutils.get_index_of_named_signal(abfRun.segments[0].analogsignals, adc.name)
            # for k, seg in enumerate(abfRun.segments[:1]): # use this line for debugging
            for k, seg in enumerate(abfRun.segments):
                pndx = f"path{k}"
                if k > 1:
                    break
                
                adcSignal = seg.analogsignals[sigIndex]
                
                sweepStartTime = protocol.sweepTime(k)
                
                self._data_["baseline"][pndx].segments.append(abfRun.segments[k])
                if isinstance(self._presynaptic_triggers_[pndx], TriggerEvent):
                    self._data_["baseline"][pndx].segments[-1].events.append(self._presynaptic_triggers_[pndx])
                    
                viewer = self._viewers_[pndx]#["synaptic"]
                viewer.view(self._data_["baseline"][pndx],
                            doc_title=pndx,
                            showFrame = len(self._data_["baseline"][pndx].segments)-1)
                
                self._signalAxes_[pndx] = viewer.axis(adc.name)
                
                viewer.currentAxis = self._signalAxes_[pndx]
                # viewer.xAxesLinked = True
                
                viewer.plotAnalogSignalsCheckBox.setChecked(True)
                viewer.plotEventsCheckBox.setChecked(True)
                viewer.analogSignalComboBox.setCurrentIndex(viewer.currentAxisIndex+1)
                viewer.analogSignalComboBox.activated.emit(viewer.currentAxisIndex+1)
                # viewer.currentAxis.vb.enableAutoRange()
                # viewer.currentAxis.vb.autoRange()
                self._signalAxes_[pndx].vb.enableAutoRange()
                
                cnames = [c.name for c in viewer.dataCursors]
                
                if self._clampMode_ == ephys.ClampMode.VoltageClamp:
                    for landmarkname, landmarkcoords in self._landmarks_.items():
                        if k > 0 and landmarkname in ("Rbase", "Rs", "Rin"):
                            # don't need those in both pathways!
                            continue
                        if landmarkname not in cnames:
                            if landmarkname ==  "Rs":
                                # overwrite this with the local signal extremum
                                # (first capacitance transient)
                                sig = adcSignal.time_slice(self._mbTestStart_+ sweepStartTime,
                                                                                self._mbTestStart_ + self._mbTestDuration_+ sweepStartTime)
                                if self._mbTestAmplitude_ > 0:
                                    # look for a local maximum in the dac
                                    transientTime = sig.times[sig.argmax()]
                                else:
                                    transientTime = sig.times[sig.argmin()]
                                    # look for local minimum in the dac
                                    
                                start = transientTime - self._responseBaselineDuration_/2
                                duration = self._responseBaselineDuration_
                                
                            else:
                                if any(v is None for v in landmarkcoords):
                                    # for the case when only a single pulse was used
                                    continue
                                start, duration = landmarkcoords
                                
                            x = float((start + duration / 2 + sweepStartTime).rescale(pq.s))
                            xwindow = float(duration.rescale(pq.s))
                            # print(f"x = {x}, xwindow = {xwindow}")
                            viewer.addCursor(sv.SignalCursorTypes.vertical,
                                            x = x,
                                            xwindow = xwindow,
                                            label = landmarkname,
                                            follows_mouse = False,
                                            axis = self._signalAxes_[pndx],
                                            relative=True,
                                            precision=5)
                            
                    # we allow cursors to be repositioned during the recording
                    # therefore we do not generate neo.Epochs anymore
                    
                    if k == 0:
                        # calculate DC, Rs, and Rin for pathway 0 only
                        Rbase_cursor = viewer.dataCursor("Rbase")
                        coords = ((Rbase_cursor.x - Rbase_cursor.xwindow/2) * pq.s, (Rbase_cursor.x + Rbase_cursor.xwindow/2) * pq.s)
                        Idc = np.mean(adcSignal.time_slice(*coords))
                                      
                        self._results_["DC"].append(Idc)
                        
                        Rs_cursor = viewer.dataCursor("Rs")
                        coords = ((Rs_cursor.x - Rs_cursor.xwindow/2) * pq.s, (Rs_cursor.x + Rs_cursor.xwindow/2) * pq.s)
                        if self._mbTestAmplitude_ > 0:
                            Irs = np.max(adcSignal.time_slice(*coords))
                        else:
                            Irs = np.min(adcSignal.time_slice(*coords))
                            
                        Rs  = (self._mbTestAmplitude_ / (Irs-Idc)).rescale(pq.MOhm)
                        
                        self._results_["Rs"].append(Rs)
                        
                        Rin_cursor = viewer.dataCursor("Rin")
                        coords = ((Rin_cursor.x - Rin_cursor.xwindow/2) * pq.s, (Rin_cursor.x + Rin_cursor.xwindow/2) * pq.s)
                        Irin = np.mean(adcSignal.time_slice(*coords))
                            
                        Rin = (self._mbTestAmplitude_ / (Irin-Idc)).rescale(pq.MOhm)
                        
                        self._results_["Rin"].append(Rin)
                        
                        
                    Ipsc_base_cursor = viewer.dataCursor("PSCBase")
                    coords = ((Ipsc_base_cursor.x - Ipsc_base_cursor.xwindow/2) * pq.s, (Ipsc_base_cursor.x + Ipsc_base_cursor.xwindow/2) * pq.s)
                    
                    IpscBase = np.mean(adcSignal.time_slice(*coords))
                    
                    Ipsc0Peak_cursor = viewer.dataCursor("PSC0Peak")
                    coords = ((Ipsc0Peak_cursor.x - Ipsc0Peak_cursor.xwindow/2) * pq.s, (Ipsc0Peak_cursor.x + Ipsc0Peak_cursor.xwindow/2) * pq.s)
                    
                    Ipsc0Peak = np.mean(adcSignal.time_slice(*coords))
                    
                    Ipsc0 = Ipsc0Peak - IpscBase
                    
                    self._results_[pndx]["Response0"].append(Ipsc0)
                    
                    if self._presynaptic_triggers_[pndx].size > 1:
                        Ipsc1Peak_cursor = viewer.dataCursor("PSC1Peak")
                        coords = ((Ipsc1Peak_cursor.x - Ipsc1Peak_cursor.xwindow/2) * pq.s, (Ipsc1Peak_cursor.x + Ipsc1Peak_cursor.xwindow/2) * pq.s)
                        
                        Ipsc1Peak = np.mean(adcSignal.time_slice(*coords))
                        Ipsc1 = Ipsc1Peak - IpscBase
                        
                        self._results_[pndx]["Response1"].append(Ipsc1)
                        
                        self._results_[pndx]["PairedPulseRatio"].append(Ipsc1/Ipsc0)
                    
                    
            responses = dict(amplitudes = dict(path0 = None, path1 = None), 
                             pprs = dict(path0 = None, path1 = None), 
                             rs = None, rincap = None, dc = None)
#             pprs = dict(path0 = None, path1 = None)
#             
#             mbTest = dict(rs = None, rincap = None)
#             
            for field, value in self._results_.items():
                if not field.startswith("path"):
                    if len(value):
                        # pts = IrregularlySampledDataSignal(np.arange(len(value)),
                        #                                     value, units = value[0].units,
                        #                                     time_units = pq.dimensionless,
                        #                                     name = field,
                        #                                     domain_name="Sweep")
                        
                        pts = IrregularlySampledDataSignal(self._abfRunDeltaTimes_,
                                                           value, units = value[0].units,
                                                           time_units = pq.min,
                                                           name = field,
                                                           domain_name="Time")
                        
                        if field in ("DC", "tau"):
                            responses["dc"] = pts
                            # self._viewers_["dc"].view(pts)
                                
                        elif field == "Rs":
                            responses["rs"] = pts
                            # mbTest["rs"] = pts
                            # self._viewers_["rs"].view(pts)
                            
                        elif field in ("Rin", "Cap"):
                            responses["rincap"] = pts
                            # mbTest["rincap"] = pts
                            # self._viewers_["rin"].view(pts)
                            
                else:
                    pname = field
                    resp0 = value["Response0"]
                    if len(resp0) == 0:
                        continue
                    
                    resp1 = value["Response1"]
                    
                    sname = "Slope" if self._clampMode_ == ephys.ClampMode.CurrentClamp and self._useSlopeInIClamp_ else "Amplitude"
                    
#                     if len(resp1) == len(resp0):
#                         response = IrregularlySampledDataSignal(np.arange(len(resp0)),
#                                                            np.vstack((resp0, resp1)).T,
#                                                            units = resp0[0].units,
#                                                            time_units = pq.dimensionless,
#                                                            domain_name = "Sweep",
#                                                            name = f"{sname} {pname}")
#                         
#                     else:
#                         response = IrregularlySampledDataSignal(np.arange(len(resp0)),
#                                                            resp0,
#                                                            units = resp0[0].units,
#                                                            time_units = pq.dimensionless,
#                                                            domain_name = "Sweep",
#                                                            name = f"{sname} {pname}")
                    # NOTE: 2023-10-06 08:21:13 
                    # only plot the first response amplitude
                    response = IrregularlySampledDataSignal(self._abfRunDeltaTimes_,
                                                        resp0,
                                                        units = resp0[0].units,
                                                        time_units = pq.min,
                                                        domain_name = "Time",
                                                        name = f"{sname} {pname}")
                        
                    # response = IrregularlySampledDataSignal(np.arange(len(resp0)),
                    #                                     resp0,
                    #                                     units = resp0[0].units,
                    #                                     time_units = pq.dimensionless,
                    #                                     domain_name = "Sweep",
                    #                                     name = f"{sname} {pname}")
                        
                    # self._viewers_[pname]["amplitudes"].view(pts)
                    
                    responses["amplitudes"][pname] = response
                    
                    ppr = value["PairedPulseRatio"]
                    
                    if len(ppr):
                        pts = IrregularlySampledDataSignal(self._abfRunDeltaTimes_,
                                                           ppr,
                                                           units = pq.dimensionless,
                                                           time_units = pq.min,
                                                           domain_name = "Time",
                                                           name = f"PPR {pname}")
                        
                        # pts = IrregularlySampledDataSignal(np.arange(len(ppr)),
                        #                                    ppr,
                        #                                    units = pq.dimensionless,
                        #                                    time_units = pq.dimensionless,
                        #                                    domain_name = "Sweep",
                        #                                    name = f"PPR {pname}")
                        
                        responses["pprs"][pname] = pts
                        # pprs[pname] = pts
                        
            resultsPlot = list()
            
            if isinstance(responses["amplitudes"]["path0"], IrregularlySampledDataSignal):
                resultsPlot.append(responses["amplitudes"]["path0"])
                if isinstance(responses["amplitudes"]["path1"], IrregularlySampledDataSignal):
                    resultsPlot.append(responses["amplitudes"]["path1"])
                
            if isinstance(responses["pprs"]["path0"], IrregularlySampledDataSignal):
                resultsPlot.append(responses["pprs"]["path0"])
                if isinstance(responses["pprs"]["path1"], IrregularlySampledDataSignal):
                    resultsPlot.append(responses["pprs"]["path1"])
                    
            if isinstance(responses["rs"], IrregularlySampledDataSignal):
                resultsPlot.append(responses["rs"])
                
                if isinstance(responses["rincap"], IrregularlySampledDataSignal):
                    resultsPlot.append(responses["rincap"])
                    
            if isinstance(responses["dc"], IrregularlySampledDataSignal):
                resultsPlot.append(responses["dc"])
                
            self._viewers_["results"].view(resultsPlot, symbolColor="black", symbolBrush="black")
            
            return (self._data_, self._results_)
            
            
#             if isinstance(responses["amplitudes"]["path0"], IrregularlySampledDataSignal):
#                 if isinstance(responses["amplitudes"]["path1"], IrregularlySampledDataSignal):
#                     self._viewers_["amplitudes"].view([responses["amplitudes"]["path0"], responses["amplitudes"]["path1"]], 
#                                                       name=("Path 0", "Path 1"))
#                 else:
#                     self._viewers_["amplitudes"].view(responses["amplitudes"]["path0"], 
#                                                       symbolColor="black", symbolBrush="black")
#                     
#                 if len(self._abfRunDeltaTimes_) <= 1: # first run
#                     self._viewers_["amplitudes"].showLegends(True)
                    
                    
            # if isinstance(responses["pprs"]["path0"],IrregularlySampledDataSignal):
            #     if isinstance(responses["pprs"]["path1"], IrregularlySampledDataSignal):
            #         self._viewers_["ppr"].view([responses["pprs"]["path0"], responses["pprs"]["path1"]], 
            #                                    symbolColor="black", symbolBrush="black")
            #     else:
            #         self._viewers_["ppr"].view(responses["pprs"]["path0"], 
            #                                    symbolColor="black", symbolBrush="black")
                    
                # if len(self._abfRunDeltaTimes_) <= 1: # first run
                #     self._viewers_["ppr"].showLegends(True)
                    
            # if isinstance(responses["rs"], IrregularlySampledDataSignal):
            #     if isinstance(responses["rincap"], IrregularlySampledDataSignal):
            #         self._viewers_["rs"].view([mbTest["rs"], mbTest["rincap"]],symbolColor="black", symbolBrush="black")
            #     else:
            #         self._viewers_["rs"].view(mbTest["rs"],symbolColor="black", symbolBrush="black")
                        
                # if len(self._abfRunDeltaTimes_) <= 1: # first run
                #     self._viewers_["rs"].showLegends(True)
                        

    def processMonitorProtocol(self, protocol:pab.ABFProtocol):
        """Infers the timings of the landmarks from protocol.
        Called only when self._monitorProtocol_ is None (i.e., at first run)
        """
        # TODO: 2023-10-03 12:31:19
        # implement the case where TTLs are emulated with a DAC channel (with its
        # output routed to a simulus isolator)
        #
        # NOTE: 2023-10-04 18:42:34
        # the code below assumes voltage-clamp and EPSCs hence relies on signal
        # baseline before the response to measure amplitude
        #
        # TODO: 2023-10-04 18:43:12 URGENT FIXME
        # code for current-clamp/field recordings where we measure the slope of 
        #   the rising phase of the synaptic potentials !
        #
        
        
        # the DAC used to send out the command waveforms
        dac = protocol.outputConfiguration(self._dacChannel_)
        
        # Guess which DAC output has digital outputs enabled.
        #
        # In Clampex, there can be only one!¹
        #
        # Ths is necessary because one may have confgured dig outputs in a DAC
        # different from the one used for command waveform.
        #
        # HOWEVER, this is only possble when alternate digital outputs are 
        # enabled in the protocol - and, hence, this dac must have the same epochs
        # defined as the DAC used for clamping.
        #
        # ¹) For this reason, additional triggers can only be sent out by emulating
        #    TTL waveforms in the analog command epochs on additional DAC outputs.
        #
        digOutDacs = list(filter(lambda x: x.digitalOutputEnabled, (protocol.outputConfiguration(k) for k in range(protocol.nDACChannels))))
        
        if len(digOutDacs) == 0:
            raise ValueError("The protocol indicates there are no DAC channels with digtal output enabled")
        
        digOutDACIndex = digOutDacs[0].number
        
        if digOutDACIndex != self._dacChannel_:
            if not protocol.alternateDigitalOutputStateEnabled:
                raise ValueError(f"Digital outputs are enabled on DAC {digOutDACIndex} and command waveforms are sent via DAC {self._dacChannel_}, but alternative digital outputs are disabled in the protocol")
        
            assert protocol.nSweeps % 2 == 0, "For alternate DIG pattern the protocol is expected to have an even number of sweeps"
            
        # DAC where dig out is enabled;
        # when alt dig out is enabled, this stores the main dig pattern
        # (the dig pattern sent out on even sweeps 0, 2, 4, etc)
        # whereas the "main" dac retrieved above stores the alternate digital pattern
        # (the dig pattern set out on odd sweeps, 1,3, 5, etc)
        
        digdac = protocol.outputConfiguration(digOutDACIndex)
        
        if len(digdac.epochs) == 0:
            raise ValueError("DAC with digital outputs has no epochs!")
        
        digEpochsTable = digdac.epochsTable(0)
        dacEpochsTable = dac.epochsTable(0)
        
        digEpochsTable_reduced = digEpochsTable.loc[[i for i in digEpochsTable.index if not i.startswith("Digital Pattern")], :]
        dacEpochsTable_reduced = dacEpochsTable.loc[[i for i in dacEpochsTable.index if not i.startswith("Digital Pattern")], :]
        
        digEpochsTableAlt = None
        digEpochsTableAlt_reduced = None
        
        if digOutDACIndex != self._dacChannel_:
            # a this point, this implies protocol.alternateDigitalOutputStateEnabled == True
            #
            # What we check here:
            # when alternate digital output is enabled, AND the dig dac is dfferent 
            # from the main dac, the epochs defned in each of the dacs MUST be the same
            # EXCEPT for the reported (stored) digital patterns
            # 
            # The idea is that the main experimental epochs are defined in the dacChannel,
            # but the digital outputs may be defined in the "alternative" DAC channel,
            # with the condition that the same epochs are defined there
            # 
            # NOTE: In general this is a SOFT requirement (one can imagine 
            # doing completely different things in the "alternate" digital output)
            #
            # However, for a synaptic plasticity experiment, sending stimuli at
            # different times on the alternate pathway is an unnecessary complication
            # hence, HERE, this is is a HARD requirement (for now...)
            #
            digEpochsTableAlt = digdac.epochsTable(1)
            digEpochsTableAlt_reduced = digEpochsTableAlt.loc[[i for i in digEpochsTableAlt.index if not i.startswith("Digital Pattern")], :]
            assert(np.all(digEpochsTable_reduced == dacEpochsTable_reduced)), "Epochs table mismatch between DAC channels"
            assert(np.all(digEpochsTableAlt_reduced == dacEpochsTable_reduced)), "Epochs table mismatch between DAC channels with alternate digital outputs"
        
        
        # Locate the presynaptic triggers epoch
        # first try and find epochs with digital trains
        # there should be only one such epoch, sending at least one TTL pulse per train
        #
        
        synStimEpochs = list(filter(lambda x: len(x.trainDigitalOutputChannels("all"))>0, 
                                    digdac.epochs))
        
        # synStimEpochs = list(filter(lambda x: any(x.hasDigitalTrain(d) for d in stimDIG), 
        #                             digdac.epochs))
        
        # ideally there is only one such epoch
        if len(synStimEpochs) > 1:
            warnings.warn(f"There are {len(synStimEpochs)} in the protocol; will use the first one")
            synStimEpochs = [synStimEpochs[0]]
            # return False
        
        elif len(synStimEpochs) == 0:
            # Try prestim triggers defined as digital pulses instead of trains.
            #
            # Here we can expect to have more than one such epochs, together 
            #   emulating a train of TTL pulses (with one pulse per epoch).
            #
            # There should be no intervening epochs here...
            #
            # Obviously, this is a contrived scenario that might work for the 
            # synaptic monitoring episodes of the experiment (when one might use
            # single,  paired-pulse, or even a few pulses - although I am not 
            # sure there is good case for the latter) but is not so usable during 
            # conditioning episodes, especially those using high frequency trains
            # (one would run out of epochs pretty fast...); nevertheless, I can 
            # imagine case where low frequency triggers could be generated
            # using pulses instead of trains for conditioning as well (e.g.
            # low frequency stimulations)
            #
            synStimEpochs = list(filter(lambda x: len(x.pulseDigitalOutputChannels("all"))>0, 
                                        digdac.epochs))
        
            # synStimEpochs = list(filter(lambda x: any(x.hasDigitalPulse(d) for d in stimDIG), 
            #                             digdac.epochs))
            if len(synStimEpochs) == 0:
                raise ValueError("There are no epoch sending digital triggers")
            
        # store these for later
        stimDIG = unique(synStimEpochs[0].usedDigitalOutputChannels("all"))
            
        # We need:
        # start of membrane test
        # duration of membrane test
        # magnitude of membrane test
        
        # locate the membrane test epoch; this is a step or pulse epoch, with:
        # (• are hard requirements, ∘ are soft requirements)
        # • first level !=0
        # • delta level == 0
        # • delta duration == 0
        # ∘ no digital info 
        
        mbTestEpochs = list(filter(lambda x: x.epochType in (pab.ABFEpochType.Step, pab.ABFEpochType.Pulse) \
                                            and not any(x.hasDigitalOutput(d) for d in stimDIG) \
                                            and x.firstLevel !=0 and x.deltaLevel == 0 and x.deltaDuration == 0, 
                                   dac.epochs))
        
        # NOTE: for the moment, I do not expect to have more than one such epoch
        # WARNING we require a membrane test epoch in voltage clamp;
        # in current clamp this is not mandatory as we may be using field recordings
        if len(mbTestEpochs) == 0:
            if self._clampMode_ == ephys.ClampMode.VoltageClamp:
                raise ValueError("No membrane test epoch appears to have been defined")
            self._membraneTestEpoch_ = None
            
        else:
            self._membraneTestEpoch_ = mbTestEpochs[0]
        
        if self._membraneTestEpoch_ is None:
            self._mbTestAmplitude_ = None
            self._mbTestStart_ = None
            self._mbTestDuration_ = None
            self._signalBaselineStart_ = 0 * pq.s
            self._signalBaselineDuration_ = dac.epochRelativeStartTime(synStimEpochs[0], 0)
            self._responseBaselineStart_ = self._signalBaselineStart_
            self._responseBaselineDuration_ = self._signalBaselineDuration_
        else:
            self._mbTestAmplitude_ = self._membraneTestEpoch_.firstLevel
        
            self._mbTestStart_ = dac.epochRelativeStartTime(self._membraneTestEpoch_, 0)
            self._mbTestDuration_ = self._membraneTestEpoch_.firstDuration
        
        
            # Figure out the global signal baseline and the baseline for synaptic 
            # responses, based on the relative timings of the membrane test and trigger
            #   epochs
            #
            # For this purpose I guess could use the epoch number or letter but since
            #   I need the timings, I prefer to do it as below.
            #

            # NOTE: 2023-10-05 12:16:09
            # Setup landmark timings - all relative to the sweep start time
            #
            # 1) parse the protocol for epochs
            #
            if dac.epochRelativeStartTime(self._membraneTestEpoch_, 0) + self._membraneTestEpoch_.firstDuration < digdac.epochRelativeStartTime(synStimEpochs[0], 0):
                # membrane test is delivered completely sometime BEFORE triggers
                #
                
                if self._mbTestStart_ == 0:
                    # membrane test is at the very beginning of the sweep (but always 
                    # after the holding time; odd, but allowed...)
                        
                    self._signalBaselineStart_ = 0 * pq.s
                    self._signalBaselineDuration_ = dac.epochRelativeStartTime(self._membraneTestEpoch_, 0)
                    
                else:
                    # are there any epochs definded BEFORE mb test?
                    initialEpochs = list(filter(lambda x: dac.epochRelativeStartTime(x, 0) + x.firstDuration <=  dac.epochRelativeStartTime(self._membraneTestEpoch_, 0) \
                                                        and x.firstDuration > 0 and x.deltaDuration == 0, 
                                                    dac.epochs))
                    
                    if len(initialEpochs):
                        baselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0, initialEpochs))
                        if len(baselineEpochs):
                            self._signalBaselineStart_ = dac.epochRelativeStartTime(baselineEpochs[0], 0)
                            self._signalBaselineDuration_ = baselineEpochs[0].firstDuration
                        else:
                            self._signalBaselineStart_ = 0 * pq.s
                            self._signalBaselineDuration_ = dac.epochRelativeStartTime(initialEpochs[0], 0)
                            
                    else:
                        # no epochs before the membrane test (odd, but can be allowed...)
                        self._signalBaselineStart_ = max(self._mbTestStart_ - 2 * dac.holdingTime, 0*pq.s)
                        self._signalBaselineDuration_ = max(dac.holdingTime, self._membraneTestEpoch_.firstDuration)
                
                
                # Finally, get an epoch for the synaptic response baseline;
                # NOTE: IN the case where membrane test is delivered BEFORE the triggers,
                # we would expect to have another epoch intervening between the 
                # membrane test and the first epoch in synStimEpochs -  we will use
                # that to calculate the baseline for the synaptic responses
                #
                # This is not mandatory, but it would make more sense to let the cell
                # membrane "settle" after a membrane test before delivering a synaptic
                # stimulus.
                #
                # NOTE: 2023-10-04 18:34:59
                # we take 5 ms duration for this (arbitrary)
                #
                
                responseBaselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0 and x.firstDuration >= self._responseBaselineDuration_ \
                                                            and dac.epochRelativeStartTime(x, 0) > self._mbTestStart_ + self._mbTestDuration_ \
                                                            and dac.epochRelativeStartTime(x, 0) + x.firstDuration <= digdac.epochRelativeStartTime(synStimEpochs[0], 0) - self._responseBaselineDuration_,
                                                    dac.epochs))
                
                if len(responseBaselineEpochs):
                    # take the last one
                    self._responseBaselineStart_ = dac.epochRelativeStartTime(responseBaselineEpochs[-1], 0)
                
                else:
                    self._responseBaselineStart_ = digdac.epochRelativeStartTime(synStimEpochs[0], 0) - 2 * self._responseBaselineDuration_
                    
                
                    
            elif dac.epochRelativeStartTime(self._membraneTestEpoch_, 0) > digdac.epochRelativeStartTime(synStimEpochs[-1], 0) + synStimEpochs[-1].firstDuration:
                # membrane test delivered somwehere towards the end of the sweep, 
                # surely AFTER the triggers (and hopefully when the synaptic responses
                # have decayed...)
                #
                # in this case, best is to use the first epoch before the synStimEpochs (if any)
                # or the dac holding
                #
                initialEpochs = list(filter(lambda x: dac.epochRelativeStartTime(x, 0) + x.firstDuration <=  digdac.epochRelativeStartTime(synStimEpochs[0], 0) \
                                                    and x.firstDuration > 0 and x.deltaDuration == 0, 
                                                dac.epochs))
                
                if len(initialEpochs):
                    # there are epochs before synStimEpochs - are any of these baseline-like?
                    baselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0, initialEpochs))
                    if len(baselineEpochs):
                        self._signalBaselineStart_ = dac.epochRelativeStartTime(baselineEpochs[0], 0)
                        self._signalBaselineDuration_ = baselineEpochs[0].firstDuration
                    else:
                        self._signalBaselineStart_ = 0 * pq.s
                        self._signalBaselineDuration_ = dac.epochRelativeStartTime(initialEpochs[0], 0)
                        
                else:
                    # no epochs before the membrane test (odd, but can be allowed...)
                    self._signalBaselineStart_ = max(digdac.epochRelativeStartTime(synStimEpochs[0], 0) - 2 * dac.holdingTime, 0*pq.s)
                    self._signalBaselineDuration_ = max(dac.holdingTime, synStimEpochs[0].firstDuration)
            
                # Now, determine the response baseline for this scenario.
                responseBaselineEpochs = list(filter(lambda x: x.firstLevel == 0 and x.deltaLevel == 0 and x.firstDuration >= self._responseBaselineDuration_ \
                                                            and dac.epochRelativeStartTime(x, 0) > self._mbTestStart_ + self._mbTestDuration_ \
                                                            and dac.epochRelativeStartTime(x, 0) + x.firstDuration <= digdac.epochRelativeStartTime(synStimEpochs[0], 0) - self._responseBaselineDuration_,
                                                    dac.epochs))
                
                if len(responseBaselineEpochs):
                    # take the last one
                    self._responseBaselineStart_ = dac.epochRelativeStartTime(responseBaselineEpochs[-1], 0)
                
                else:
                    self._responseBaselineStart_ = digdac.epochRelativeStartTime(synStimEpochs[0], 0) - 2 * self._responseBaselineDuration_
        #
        # 2) create trigger events
        #
        for path in range(protocol.nSweeps):
            pndx = f"path{path}"
            pathEpochs = sorted(synStimEpochs, key = lambda x: dac.epochRelativeStartTime(x, path))
            trig = dac.triggerEvents(pathEpochs[0], path) # will add sweep start time here
            if len(pathEpochs) > 1:
                for e in pathEpochs[1:]:
                    trig = trig.merge(dac.triggerEvents(e, path))#, label="EPSC"))
                
            ntrigs = trig.size
            ll = [f"EPSC{k}" for k in range(ntrigs)]
            trig.labels = ll
            
            if not isinstance(self._presynaptic_triggers_.get(pndx, None), TriggerEvent):
                self._presynaptic_triggers_[pndx] = trig
            else: # not needed, really, because we set these up only upon the first run...
                assert(trig == self._presynaptic_triggers_[pndx]), f"Presynaptic triggers mismatch {trig} vs path0 trigger {self._presynaptic_triggers_[pndx]}"
                
        #
        # 3) populate the landmarks dictionary
        #
        # TODO: populate self._landmarks_ with neo.Epochs-like lists (start, duration)
        # use these to generate cursors in the corresponding pathway signal viewer
        # DECIDE: we need:
        #
        # • for voltage clamp:
        #
        #   ∘ global baseline Rbase epoch interval  -> aveage of signal slice
        #
        #   ∘ Rs epoch interval                     -> extremum of signal slice
        #       ⋆ max for positive Vm step, min for negative Vm step
        #
        #   ∘ Rin epoch interval                    -> average of signal slice
        #   
        #   ∘ EPSCbase interval (or EPSC0Base and EPSC1Base intervals) 
        #       ⋆ NOTE a single EPSCBase should also be used for paire-pulse,
        #           where we use it as a common baseline for BOTH EPSCs -> 
        #           TODO Adapt functions for LTP analysis in this module
        #
        #   ∘ EPSCPeak interval (or EPSC0Peak and EPSC1Peak intervals)
        #       ⋆ NOTE needs two intervals for paired-pulse
        # 
        # • for current-clamp:
        #
        #   ∘ global baseline Baseline epoch interval  -> aveage of signal slice
        #
        #   ∘ measure the membrane test with membrane.passive_Iclamp(…) 
        #       ⋆ => calculate tau, Rin and capacitance
        #
        #   ∘ EPSP interval or EPSP0 and EPSP1 intervals (for paired-pulse)
        #       ⋆ measure slope of 10-90% of rising phase
        #
        if self._clampMode_ == ephys.ClampMode.VoltageClamp:
            self._landmarks_["Rbase"] = [self._signalBaselineStart_, self._signalBaselineDuration_]
            
            # Rs landmark will be overwritten after find out local extremum in 
            # the adc signal (searching for the first capacitance transient)
            # also, NOTE that we only need Rbase, Rs, and Rin for the pathway 0
            #
            self._landmarks_["Rs"] = [dac.epochRelativeStartTime(self._membraneTestEpoch_), 
                                      self._responseBaselineDuration_]
            self._landmarks_["Rin"] = [dac.epochRelativeStartTime(self._membraneTestEpoch_) + self._membraneTestEpoch_.firstDuration - 2 * self._responseBaselineDuration_,
                                       self._responseBaselineDuration_]
            self._landmarks_["PSCBase"] = [self._responseBaselineStart_, self._responseBaselineDuration_]
            self._landmarks_["PSC0Peak"] = [self._presynaptic_triggers_["path0"].times[0] - protocol.sweepTime(0) + 15 * pq.ms,
                                           2 * pq.ms]
            if self._presynaptic_triggers_["path0"].size > 1:
                self._landmarks_["PSC1Peak"] = [self._presynaptic_triggers_["path0"].times[1] - protocol.sweepTime(0) + 15 * pq.ms,
                                            2 * pq.ms]
        else:
            # WARNING - needs more work to adapt to what passive_Iclamp needs:
            # vm signal (slice of the adc data on VmTest)
            # im as a list of amplitude, VmTest start, VmTest stop
            # steadystate duration - default is 50 ms
            self._landmarks_["Base"] = [self._signalBaselineStart_,self._signalBaselineDuration_]
            if self._membraneTestEpoch_ is not None:
                self._landmarks_["VmTest"] = [dac.epochRelativeStartTime(self._membraneTestEpoch_),
                                            self._membraneTestEpoch_.firstDuration]
            
class LTPOnline(QtCore.QObject):

    test_protocol_properties = ("activeDACChannelIndex",
                                "nSweeps",
                                "acquisitionMode",
                                "samplingRate",
                                "alternateDigitalOutputStateEnabled",
                                "alternateDACOutputStateEnabled")
    
    timings_fields = ("dcStart", "dcStop", 
                      "RsStart", "RsStop",
                      "RinStop", "RinStop",
                      "EPSC0BaseStart", "EPSC0BaseStop",
                      "EPSC0PeakStart", "EPSC0PeakStop",
                      "EPSC1BaseStart", "EPSC1BaseStop",
                      "EPSC1PeakStart", "EPSC1PeakStop",
                      )
    
    resultsReady = pyqtSignal(object, name="resultsReady")
    

    def __init__(self,
                 mainClampMode:typing.Union[int, ephys.ClampMode] = ephys.ClampMode.VoltageClamp,
                 conditioningClampMode:typing.Union[int, ephys.ClampMode]=ephys.ClampMode.CurrentClamp,
                 adcChannel:int = 0,
                 dacChannel:int = 0,
                 digOutDacChannel:int = 0,
                 responseBaselineDuration:pq.Quantity = 5 * pq.ms,
                 useEmbeddedProtocol:bool=True,
                 useSlopeInIClamp:bool = True,
                 synapticDigitalTriggersOnDac:typing.Optional[int]=None,
                 stimDIG:typing.Sequence[int] = (0,1),
                 synapticTriggersOnDac:typing.Optional[int]=None,
                 mbTest:typing.Optional[pq.Quantity] = None,
                 mbTestStart:pq.Quantity = 0.05*pq.s,
                 mbTestDuration:pq.Quantity = 0.1 * pq.s,
                 steadyStateDurationIClampTest = 0.05 * pq.s,
                 emitterWindow:typing.Optional[QtWidgets.QMainWindow] = None,
                 directory:typing.Optional[typing.Union[str, pathlib.Path]] = None,
                 autoStart:bool=True,
                 parent=None,
                 ):
        """
        mainClampMode: expected clamping mode; one of ephys.ClampMode.VoltageClamp
            or ephys.ClampMode.CurrentClamp, or their respective int values (2, 4)

            NOTE: even if recording field potentials (I=0 "clamping mode") the units
            of the DAC and ADC should pair up as for current clamp (i.e., DAC in mV
            and ADC in pA) because I=0 is actually current clamp without actual clamping
            (i.e. no current injected into the cell whatsoever)

            Also NOTE this is irrespective of electrode mode: patch clamp can
            record in either clamp modes; on the other hand, sharp (intracellular)
            or field recording electrodes are useless in voltage clamp...

        conditioningMode: as above;
            for patch-clamp recordings one may choose to trigger postsynaptic
                activity by current injection (current clamp) or 'emulated' in
                voltage-clamp with AP-like waveforms, dynamic clamp and such...
                (if the cell can be voltage-clamped with some degree of accuracy)

                therefore, any of voltage- or current-clasmp modes are valid
        
        adcChannel:int, default is 0 (first ADC input channel)
            Index of the ADC input channel used in recording.
        
            NOTE: This cannot be unambguously determined from the Clampex protocol,
            because the user may decide to "record" signals from more than one
            amplifier primary output
        
        dacChannel:int, default is 0 (first DAC output channel)
            Index of the DAC output channel used for sending analog
            waveform commands to the recorded cell (e.g. holding potential
            or current, membrane test, postsynaptc spikng, etc).
            
            In the protocol, the corresponding ABFOutput configuration MUST have 
            'analogWaveformEnabled' == True.
            
            NOTE: This cannot be unambiguously determined from the protocol,
            because the experimenter may decide to enable command waveform
            in more than one DAC (e.g. for emulating triggers, or any other
            event)
        
            WARNING: For experiments using alternative pathways, only the first
            two DACs (0 and 1) can be used for "Alternative waveform stimulation".
        
        digOutDacChannel: int, default is 0
            The index of the DAC channel where digital output is enabled.
        
            This is important because the index of this channel, in Clampex,
            is not necessarily the same as the index of the DAC channel used for
            analog waveforms commands.
        
            If this channel is distinct from dacChannel, AND digital outputs ARE 
            enabled in this channel, AND alternative digital outputs ARE enabled 
            in the Clampex protocol, then THIS channel stores the digital pattern 
            sent out during even sweeps (0,2, etc) whereas the "other" DAC channel 
            used (see above) stores the alternative digital pattern (sent out during
            odd sweeps: 1,3, etc).
        
        responseBaselineDuration: time Quantity (default is 5 * pq.ms)
            Duration of baseline before the response - used in Voltage clamp
        
        synapticDigitalTriggersOnDac: index of the DAC where digital triggers are 
                enabled, for synaptic stimulation. Default is None (read on).
        
                By default, synaptic transmission is evoked via digital TTL pulses
                or trains, with the digital output enabled on the active DAC - 
                this is the most common case and the default here.
        
                One may specify here the index of the DAC where digital outputs
                are enabled.
        
                REMEMBER:
                There can be up to 4 or 8 physical DAC channels (respectively,
                for DigiData 1440 or 1500 series).
        
                The "active" DAC can be 0 or 1, depending which amplifier channel
                is used for recording and for sending command signals to the cell
                (e.g., membranbe holding potential in voltage clamp, etc).
        
                The timings of the triggers for synaptic stimulation are taken 
                from the Epochs, defined in the active DAC, that have digital
                outputs enabled.
        
                For a two pathway experiment (where two synaptic pathway are 
                monitored via alternative stimulation) both first two DACs need
                epochs with digital outputs configured, and alternate digital 
                output must be enabled in Clampex's protocol editor (Waveforms 
                tab). 
        
                Moreover, alternative waveform must be DISABLED in Clampex's 
                protocol editor (Waveforms tab).
        
        NOTE: All lof the following parameters are in development (not relevant 
        at this stage) and should be left wth their default values for the moment
        (some are yet to be documented)
        
        stimDIG: list of 1 or 2 indices of the digital channel(s) sending out 
                synaptic stimuli as TTL triggers (e.g. via stimulus isolators)
                In experiments that monitor a single single synaptic pathway only
                the first element of the list is used.
     
                By default this is [0,1] 

            CAUTION: when stimulus isolators are NOT available, the DIG outputs
            are NOT used, but can be emulated through additional DAC outputs;
            At the time of this writing, I believe that alternative DAC outputs
            cannot be configured for DIG emulation on higher DAC indices.

        synapticTriggersOnDac: int or None; When an int, this is the index of the
            DAC channel that emulates TTLs
        
            WARNING: In Clampex one cannot use DACs to stimulate distinct paths 
            alternatively, because turning alternative waveforms ON only affects
            the first two DAC channels.
        
            When None, the epochs in the "active" DAC are used to retrieve the
            timings of the synaptic stimulus triggers (through the digital outputs)
        
        """
        
        super().__init__(parent=parent)
        
        # NOTE: 2023-10-07 11:20:22
        # _emitterWindow_ needed here, to set up viewers
        wsp = wf.user_workspace()
        
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
        
        self._monitorProtocol_ = None

        self._conditioningProtocol_ = None
        
        self._conditioningProtocols_ = list()
        
        self._adcChannel_ = adcChannel
        self._dacChannel_ = dacChannel
        
        self._sigIndex_ = None  # when set, this is an int index of the signal 
                                # of interest; must be the same across runs

        if isinstance(mainClampMode, int):
            if mainClampMode not in ephys.ClampMode.values():
                raise ValueError(f"Invalid mainClampMode {mainClampMode}; expected values are {list(ephys.ClampMode.values())}")
            self._clampMode_ = ephys.ClampMode.type(mainClampMode)
            
        elif isinstance(mainClampMode, ephys.ClampMode):
            self._clampMode_ = mainClampMode
            
        else:
            raise TypeError(f"mainClampMode expected to be an int or an ephys.ClampMode enum value; instead, got {type(mainClampMode).__name__}")

        # NOTE: 2023-10-08 09:41:39
        # conditioning protocols should not really matter!
        # but they SHOULD be different from the monitor protocol
        
#         if isinstance(conditioningClampMode, int):
#             if conditioningClampMode not in ephys.ClampMode.values():
#                 raise ValueError(f"Invalid conditioningClampMode {conditioningClampMode}; expected values are {list(ephys.ClampMode.values())}")
#             
#             self._conditioningClampModes_ = [ephys.ClampMode.type(conditioningClampMode)]
#             
#         elif isinstance(conditioningClampMode, ephys.ClampMode):
#             self._conditioningClampModes_ = [conditioningClampMode]
#             
#         else:
#             raise TypeError(f"conditioningClampMode expected to be an int or an ephys.ClampMode enum value; instead, got {type(conditioningClampMode).__name__}")

        self._useSlopeInIClamp_ = useSlopeInIClamp
        self._mbTestStart_ = mbTestStart
        self._mbTestDuration_ = mbTestDuration
        self._mbTestAmplitude_ = mbTest
        self._signalBaselineStart_ = 0 * pq.s
        self._signalBaselineDuration_ = None
        self._responseBaselineStart_ = None
        self._responseBaselineDuration_ = responseBaselineDuration
        self._steadyStatePassiveVmTest_ = steadyStateDurationIClampTest
        
        self._abfRunTimes_ = []
        self._abfRunDeltaTimes_ = []
        
        self._results_ = dict() # Episode:str ↦ episodeResultsDict
        
        self._episode_ = "baseline"

        # NOTE: 2023-10-08 09:27:47
        # passed by reference to the processor thread
        self._runParams_= dict(adcChannel = self._adcChannel_,
                               dacChannel = self._dacChannel_,
                               clampMode = self._clampMode_,
                               conditioningClampModes = self._conditioningClampModes_,
                               monitorProtocol = self._monitorProtocol_,
                               condtioningProtocols = self._conditioningProtocols_,
                               signalIndex = self._sigIndex_,
                               useSlopeInIClamp = self._useSlopeInIClamp_,
                               mbTestAmplitude = self._mbTestAmplitude_,
                               mbTestStart = self._mbTestStart_,
                               mbTestDuration = self._mbTestDuration_,
                               responseBaselineDuration = self._responseBaselineDuration_,
                               steadyStateDurationIClampTest = self._steadyStatePassiveVmTest_,
                               abfRunTimes = self._abfRunTimes_,
                               abfRunDeltaTimes = self._abfRunDeltaTimes_,
                               currentEpisode = self._episode_
                               )
        
        # WARNING: 2023-10-05 12:10:40
        # below, all timings in self._landmarks_ are RELATIVE to the start of the sweep!
        # timings are stored as [start time, duration] (all Quantity scalars, with units of time)
        if self._clampMode_ == ephys.ClampMode.VoltageClamp:
            self._episodeResults_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "DC": [], "Rs":[], "Rin":[], }
            
            self._landmarks_ = {"Rbase":[self._signalBaselineStart_, self._signalBaselineDuration_], 
                                "Rs":[None, None], 
                                "Rin":[None, None], 
                                "PSCBase":[None, None],
                                            
                                "PSC0Peak":[None, None], 
                                "PSC1Peak":[None, None]}
    
        else:
            self._episodeResults_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "tau":[], "Rin":[], "Cap":[], }
            
            if self._useSlopeInIClamp_:
                self._landmarks_ = {"Base":[self._signalBaselineStart_, self._signalBaselineDuration_], 
                                    "VmTest":[None, None], 
                                    "PSP0Base":[None, None],
                                    "PSP0Peak":[None, None],
                                    "PSP1Base":[None, None],
                                    "PSP1Peak":[None, None]}
            else:
                self._landmarks_ = {"Base":[self._signalBaselineStart_, self._signalBaselineDuration_], 
                                    "VmTest":[None, None], 
                                    "PSPBase":[None, None],
                                    "PSP0Peak":[None, None],
                                    "PSP1Peak":[None, None]}
        
                
        #### BEGIN about ABF epochs

        # expected epochs layout (and order):
        #
        # Role                              ABF Epoch                   Comments
        # ======================================================================
        # baseline (for DC, Rs and Rin)     A or None                   When None use DAC holding time
        #
        # membrane test                     B (when A present)          Can be AFTER synaptic response
        #
        # synaptic baseline                 C (when A, B present)       Can be the baseline when mb test AFTER syn resp
        #
        # synaptic response                 D (1 or 2 pulses DIG train) The first epoch with a DIG train


        # just one Epoch;
        # • if ABF Epoch, then it needs to be the first one, type Step,
        #   ∘ first duration > 0, delta duration == 0
        #   ∘ first level == 0, delta level == 0
        # • if NOT an ABF epoch then:
        #   ∘ by default corresponds to the DAC holding time
        #
        self._baselineEpoch_ = None

        # just one epoch:
        # for voltage clamp needs:
        # • type Step,
        # • first duration > 0
        # • delta duration == 0
        # • first level != 0
        # • delta level == 0
        #
        self._membraneTestEpoch_ = None

        # baseline before 1ˢᵗ synaptic stimulation below
        #   it must STOP before  1ˢᵗ synaptic stimulation below
        #   MAY be the same as baseline if membrane test comes AFTER the last
        #       synaptic response epoch (as is usual in current clamp)
        #
        self._synapticBaselineEpoch_ = None

        # list of one or two epochs
        # 1) the 1ˢᵗ (and possibly, the only) one is the stimulation for the 1ˢᵗ
        #   synaptic response
        # 2) the 2ⁿᵈ (if present) is the stimulation for the 2ⁿᵈ synaptic response
        #
        self._synapticStimulationEpochs = list()

        #### END   about ABF epochs

        self._signalAxes_ = dict(path0 = None, path1 = None)

        self._presynaptic_triggers_ = dict()
        
       # TODO: 2023-09-29 13:57:13
        # make this an intelligent thing - use SynapticPathway, PathwayEpisodes, etc.
        # for now, baseline & chase are just one or two neo.Blocks
        #
        self._data_ = dict(baseline = dict(path0 = neo.Block(), path1 = neo.Block()),
                           conditioning = dict(path0 = neo.Block(), path1 = neo.Block()),
                           chase = dict(path0 = neo.Block(), path1 = neo.Block()))

        synapticViewer0 = sv.SignalViewer(parent=self._emitterWindow_, scipyenWindow = self._emitterWindow_, win_title = "path0 Recording")
        synapticViewer0.annotationsDockWidget.hide()
        synapticViewer0.cursorsDockWidget.hide()
        
        synapticViewer1 = sv.SignalViewer(parent=self._emitterWindow_, scipyenWindow = self._emitterWindow_, win_title = "path1 Recording")
        synapticViewer1.annotationsDockWidget.hide()
        synapticViewer1.cursorsDockWidget.hide()
        
        resultsViewer = sv.SignalViewer(parent=self._emitterWindow_, scipyenWindow = self._emitterWindow_, win_title = "Analysis")
        resultsViewer.annotationsDockWidget.hide()
        resultsViewer.cursorsDockWidget.hide()
        
        self._viewers_ = dict(path0 = synapticViewer0,
                              path1 = synapticViewer1,
                              results = resultsViewer)
        
        #### BEGIN TODO move to a producer thread
        #
        # self._abfListener_ = FileStatChecker(interval = 10, maxUnchangedIntervals = 5,
        #                                      callback = self.fileProcessor)
        # self._abfListener_ = FileStatChecker(interval = 10, maxUnchangedIntervals = 5,
        #                                      callback = self.processAbfFile)
        
        #
        #### END   TODO move to a producer thread
        
        # for each new file, create an _LTPOnlineFileProcessor_ and move it here?
        # need to synchronize, as files may come in faster than we can process 
        # them
        self._abfRunBuffer_ = collections.deque()
        # self._guard_ = dict(nABFs = len(self._abfRunBuffer_))
        # self._mutex_ = QtCore.QMutex()
        # self._abfRunBufferEmptyCondition_ = QtCore.QWaitCondition()
        # self._abfRunBufferNotEmptyCondition_ = QtCore.QWaitCondition()
        
        self._abfSupplierThread_ = _LTPOnlineSupplier_(self, self._abfRunBuffer_,
                                    self._emitterWindow_, self._watchedDir_)
        
        self._abfProcessorThread_ = _LTPOnlineFileProcessor_(self, self._abfRunBuffer_,
                                                             self._runParams_,
                                    self._presynaptic_triggers_, self._landmarks_,
                                    self._data_, self._results_, self._viewers_)
        
        self._abfSupplierThread_.abfRunReady.connect(self._abfProcessorThread_.processAbfFile,
                                                     QtCore.Qt.QueuedConnection)
        
        if autoStart:
            self._abfSupplierThread_.start()
            self._abfProcessorThread_.start()
            

    def __del__(self):
        for viewer in self._viewers_.values():
            viewer.close()
        if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)
        self._abfSupplierThread_.abfListener.stop()
        self._abfSupplierThread_.quit()
        self._abfSupplierThread_.wait()
        self._abfProcessorThread_.quit()
        self._abfProcessorThread_.wait()
            
        self._abfSupplierThread_.deleteLater()
        self._abfProcessorThread_.deleteLater()
        
        # if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
        #     self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)
        # self._abfProcessorThread_.quit()
        # self._abfProcessorThread_.wait()
            
        if hasattr(super(object, self), "__del__"):
            super().__del__()
            
    @pyqtSlot()
    def doWork(self):
        self.start()

    @property
    def data(self) -> dict:
        return self._data_
    
    @property
    def adcChannel(self) -> int:
        return self._adcChannel_
    
    @adcChannel.setter
    def adcChannel(self, val:int):
        self._adcChannel_ = val
    
    @property
    def dacChannel(self) -> int:
        return self._dacChannel_
    
    @dacChannel.setter
    def dacChannel(self, val:int):
        self._dacChannel_ = val
    
    def stop(self):
        self._abfSupplierThread_.abfListener.stop()
        self._abfSupplierThread_.quit()
        self._abfSupplierThread_.wait()
        self._abfProcessorThread_.quit()
        self._abfProcessorThread_.wait()
        
        if self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, False)
            
        self.resultsReady.emit((self._data_, self._results_))
        
    def reset(self):
        self._monitorProtocol_ = None
        self._conditioningProtocol_ = None
        
        self._data_["baseline"]["path0"].segments.clear()
        self._data_["baseline"]["path1"].segments.clear()
        self._data_["chase"]["path0"].segments.clear()
        self._data_["chase"]["path1"].segments.clear()
        self._data_["conditioning"]["path0"].segments.clear()
        self._data_["conditioning"]["path1"].segments.clear()
        
        if self._clampMode_ == ephys.ClampMode.VoltageClamp:
            self._results_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "DC": [], "Rs":[], "Rin":[], }
            
            self._landmarks_ = {"Rbase":[self._signalBaselineStart_, self._signalBaselineDuration_], 
                                "Rs":[None, None], 
                                "Rin":[None, None], 
                                "PSCBase":[None, None],
                                            
                                "PSC0Peak":[None, None], 
                                "PSC1Peak":[None, None]}
    
        else:
            self._results_ = {"path0": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "path1": {"Response0":[], "Response1":[], "PairedPulseRatio":[]},
                              "tau":[], "Rin":[], "Cap":[], }
            
            if self._useSlopeInIClamp_:
                self._landmarks_ = {"Base":[self._signalBaselineStart_, self._signalBaselineDuration_], 
                                    "VmTest":[None, None], 
                                    "PSP0Base":[None, None],
                                    "PSP0Peak":[None, None],
                                    "PSP1Base":[None, None],
                                    "PSP1Peak":[None, None]}
            else:
                self._landmarks_ = {"Base":[self._signalBaselineStart_, self._signalBaselineDuration_], 
                                    "VmTest":[None, None], 
                                    "PSPBase":[None, None],
                                    "PSP0Peak":[None, None],
                                    "PSP1Peak":[None, None]}
        
                
        for viewer in self._viewers_.values():
            viewer.clear()
            

    def start(self, directory:typing.Optional[typing.Union[str, pathlib.Path]] = None):
        # if self._emitterWindow_ is None:
        #     raise ValueError("You must set an emiter window first...")

        if directory is None:
            if self._watchedDir_ is None:
                self._watchedDir_ = pathlib.Path(self._emitterWindow_.currentDir).absolute()

        elif isinstance(directory, str):
            self._watchedDir_ = pathlib.Path(directory)

        elif isinstance(directory, pathlib.Path):
            self._watchedDir_ = directory

        else:
            raise TypeError(f"'directory' expected to be a str, a pathlib.Path, or None; instead, got {type(directory).__name__}")
    
        if self._abfSupplierThread_._dirMonitor_.directory != self._watchedDir_:
            self._abfSupplierThread_._dirMonitor_.directory = self._watchedDir_

        self._pending_.clear() # pathlib.Path are hashable; hence we use the RSV ↦ ABF

        self._latestAbf_ = None # last ABF file to have been created by Clampex

        if not self._emitterWindow_.isDirectoryMonitored(self._watchedDir_):
            self._emitterWindow_.enableDirectoryMonitor(self._watchedDir_, True)
            
        self._abfSupplierThread_.start()
        self._abfProcessorThread_.start()
            
   
    
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


