
#### BEGIN core python modules
import os
# import sys
import collections
import traceback
import datetime
import numbers
import inspect
import itertools
import functools
from functools import singledispatch
import warnings
import typing
import types
# import difflib
# import re as _re
# from enum import Enum, IntEnum
# from abc import ABC
import dataclasses
from dataclasses import (dataclass, MISSING)
#### END core python modules

#### BEGIN 3rd party modules
# try:
#     import mypy
# except:
#     print("Please install mypy first")
#     raise
import numpy as np
import quantities as pq
import neo
from neo.core.objectlist import ObjectList as NeoObjectList
import h5py
import pandas as pd
from tribool import Tribool
# import pyabf

from scipy import optimize

# import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip # noqa
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


import matplotlib as mpl
# from core.pyqtgraph_patch import pyqtgraph as pg
#### END 3rd party modules

#### BEGIN pict.core modules
from core.basescipyen import BaseScipyenData
# from core.traitcontainers import DataBag
from core.prog import (safewrapper, with_doc, get_func_param_types, scipywarn)
from core.datasignal import (DataSignal, IrregularlySampledDataSignal)
from core.datazone import (DataZone, Interval)
from core.triggerevent import (DataMark, MarkType, TriggerEvent, TriggerEventType, )
from core.triggerprotocols import TriggerProtocol, TriggerProtocolList
from core.typeenum import TypeEnum
from core.scipyendataclasses import (Episode, Schedule, ScipyenDataclass)
from core import datatypes
from core.datatypes import (check_type, type2str)
from core import workspacefunctions
from core import signalprocessing as sigp
from core import utilities
from core import neoutils
from core import strutils
from core import curvefitting as crvf
from core import models as models

from core.utilities import (reverse_mapping_lookup,
                            get_index_for_seq,
                            sp_set_loc,
                            normalized_index,
                            unique,
                            GeneralIndexType)

from core.neoutils import (get_index_of_named_signal, concatenate_blocks)
from core import scipyen_quantities as scq
from core.scipyen_quantities import (unitsConvertible, checkTimeUnits,
                             checkElectricalCurrentUnits,
                             checkElectricalPotentialUnits,
                             checkRescale)

import core.pyabfbridge as pab

from core.deferredmeasures import * # noqa

from gui.cursors import (DataCursor, SignalCursor, SignalCursorTypes)

from ephys import ephys

from ephys.ephys_protocol import ElectrophysiologyProtocol

#from .patchneo import neo


#### END pict.core modules

class SynapticPathway: pass # noqa
class PathwaysStimulationLayout: pass # noqa

class RecordingEpisodeType(TypeEnum):
    r"""Once can define valid type combinations as follows:
    Tracking | Drug     (= 3)   ⇒ Tracking episode recorded in the presence of
                                    drug(s)
    Conditioning | Drug (= 5)   ⇒ Conditioning in the presence of drug(s)

    A Tracking (no Drug) episode that follows a Drug episode is interpreted as
    an episode of "drug washout".

    A value of 0 and any value > 5 are invalid.

    """
    Tracking        = 1 # used for tracking the electrophysiological behaviour of
                        # a source (e.g., synaptic responses, somatic spiking, etc);
                        # this is the most common type of electrophysiology recording
                        # epiode

    Monitoring      = Tracking

    Conditioning    = 2 # used for induction of plasticity (i.e. application of
                        # the induction protocol)

@with_doc(Episode, use_header=True, header_str = "Inherits from:")
class RecordingEpisode(Episode):
    r"""
    Specification of an electrophysiology recording episode.

    An "episode" is a contiguous series of sweeps recorded under a common set
    of experimental conditions -- typically, a subset of a larger
    experiment where distinct sets of conditions are applied in sequence.

    All sweeps in the episode must have been recorded using the same recording
    protocol (an ElectrophysiologyProtocol object) and, implicitly, from the
    same RecordingSource.

    The sweeps in an episode may belong to either:

    1) a single neo.Block — in this case the attributes 'beginFrame' and 'endFrame'
    indicate the limits of the segment sub-range in the Block) - this allows for
    the possibility that subsets of segments in the Block have been recorded under
    different conditions (and hence they would belong to distinct episodes),
    even if data was acquired using the same electrophysiology protocol.

    Normally, the segments of a Block are — by definition — recorded during the
    same experimental conditions (protocol, drug, etc). However, during some
    analyses, several of these blocks may be concatenated into a larger one —
    subject to being recorded using the same electrophysiology protocol — which
    leads to the situation where contiguous subsets of segments (or sweeps)
    recorded under distinct conditions are stored in the same Block object, a
    possibility covered by this contigency.

    2) a collection of neo.Block objects — in this case, the 'beginFrame' and 'endFrame'
    attributes cover the entire collection of segments ranges across the blocks.
    This is because several blocks are supposed to have been recorded during the SAME
    experimental conditions, such that an "episode" can be greaded as a standalone
    data "unit" (unlike the contigency described above).

    In this contigency, all the data Blocks must have been acquired using the
    same electrophysiology protocol.


    Examples:
    =========

    1) A sequence of three distinct episodes:
    • synaptic response recorded without drug
    ↓
    • recording in the presence of a drug
    ↓
    • recording after drug wash-out

    In each of the three episodes the synaptic respones are recorded with the
    SAME electrophysiology recording protocol.

    2) Segments recorded while testing for cross-talk between synaptic pathways,
    (and therefore, where the paired pulses are crossed between pathways) is a
    distinct episode from the one where each segment contains responses from the
    same synaptic pathway

    The sweeps in RecordingEpisode are a sequence of neo.Segment objects, where
    objects where each synaptic pathway has contributed data for a neo.Segment
    inside the Block.

    3) No segments are included in the episode - the episode is just a light-weight
    data grouping by protocol.

    Fields (constructor parameters):
    ================================

    • protocols: sequence of ElectrophysiologyProtocol objects
        Currently, only pyabfbridge.ABFProtocol objects are supported. The ABFProtocol
        is a subclass of ElectrophysiologyProtocol defined in this module.

    • episodeType: RecordingEpisodeType

    • pathways: optional, a list of SynapticPathways or None (default); can also
        be an empty list (same as if it was None).

        Indicates the SynapticPathways where this episode applies. Typically,
        an episode involves a single pathway. However, there are situations where
        an episode involving more pathways is meaningful, e.g., where additional
        pathways are stimulated and recorded simultaneously (e.g., in a cross-talk
        test, or during conditioning in order to test for 'associativity')

        The pathways define their own clamping modes and recording source.

    • pathActivationBySweep: a dict with key ↦ value mapping where:
        key: int (sweep indices) or tuples (start:int,step:int)
        value: tuples of SynapticPathway objects

        Optional, default is an empty dict.

        E.g., for two pathways, using int keys:
            0 ↦ (0,1)       ⇒ sweep 0 tests cross-talk from path 0 to path 1
            1 ↦ (1,0)       ⇒ sweep 1 tests cross-talk from path 1 to path 0

        or, as a tuple of two int:
            (0,2) ↦ (0,1)   ⇒ sweeps from 0 every 2 sweeps test cross-talk from
                                path 0 to path 1

            (1,2) ↦ (1,0)   ⇒ sweeps from 1 every 2 sweeps test cross-talk from
                                path 1 to path 0

        The keys should resolve to valid sweep indices in the data; then the keys are
        pairs (2-tuples) they contain the 'start' and 'step' values for constructing
        range objects indicating the sweeps where the test apples to the pathways
        given in the value mapped to the key, once the data is fully available.

        The order of the pathway indices in the values is the order in which each
        pathway was stimulated during the paired-pulse.

        WARNING: the pathways attribute must be a list of SynapticPathways.
    ---

    ¹Exceptions are possible:
        ∘ 'repatching' the cell (e.g. in order to dialyse with a drug, etc) see, e.g.
            Oren et al, (2009) J. Neurosci 29(4):939
            Maier et al, (2011) Neuron, DOI 10.1016/j.neuron.2011.08.016
        ∘ switch between field recording and patch clamp or sharp electrode recordings
        (theoretically possible, but then one may also think of this as being two
        distinct pathways)

    """
    # FIXME: 2024-09-29 23:32:05 TODO:
    # conversion to mapping protocol ↦ sweep indices across all blocks in the episode
    # actually, strike that: an episode must contain blocks recorded WITH THE SAME EPISODE
    #
    # NOTE: 2024-10-01 08:34:35
    # 'pathways' removed - one can get the pathways from pathActivationBySweep
    def __init__(self, blocks:typing.Optional[typing.Sequence[neo.Block]] = None,
                 protocol: typing.Optional[ElectrophysiologyProtocol] = None,
                 name: typing.Optional[str] = None,
                 episodeType: RecordingEpisodeType = RecordingEpisodeType.Tracking,
                 stimulusLayout: typing.Optional[PathwaysStimulationLayout] = None ,
                 **kwargs):
        r"""Constructor for RecordingEpisode.

        Named parameters:
        ------------------
        episodeType: type of the episode (see RecordingEpisodeType);
                default is Tracking or Monitoring (an alias to Tracking).

        name:str - the name of this episode (optional, default is None)
            When None, it is up to the user of this object to give an appropriate
            name

        protocol: ElectrophysiologyProtocol — the protocol used in common througout
            the episode

        pathActivationBySweep: dict — indicates which pathways are stimulated in
            which sweep; also useful for testing pathway cross-talk, or independence

            This is a key ↦ value mapping, where:

            • the keys are either:
                ∘ an int: the index of the segment¹ where the cross-stimulation
                    of the pathways indicated in the corresponsing tuple,
                    has occurred.

                ∘ a tuple of two int (x,y) where `x` is the index of the
                    first segment where cross-stimulation is applied, and
                    `y` is the number of segments skipped.

            • values are tuples of SynapticPathway objects, and their ORDER
                indicates the order in which the pathways are cross-stimulated
                in a given sweep;

                In theory, there can be any number of pathways, but in practice
                only first two pathways are tested for cross-talk.

                A tuple that contains only one pathway indicates no crosstalk in
                the sweep(s) specified by the key.

            Examples:
            A dictionary with the following structure:

            0 ↦ (path0, path1)
            1 ↦ (path1, path0)

            indicates a cross-stimulation of two pathwyas ('path0' & 'path1') in
            the order 'path0' → 'path1' in the 1ˢᵗ segment (sweep 0), and in
            the order 'path1' → 'path0' in the 2ⁿᵈ segment (sweep 1)


            A dictionary with the following structure:

            (0,2) ↦ (path0, path1)
            (1,2) ↦ (path1, path0)

            indicates cross-stimulation of two pathways ('path0' & 'path1') in
            the order 'path0' → 'path1' in every other segment starting with the
            1ˢᵗ  (segment index 0) , 𝑖.𝑒, on `even-numbered` segments,
            and in the order 'path1' → 'path0' in every other segment, starting
            with the 2ⁿᵈ (segment index 1) , 𝑖.𝑒,, on `odd-numbered` segments.

            By default the `pathActivationBySweep` attribute of a recording
            episode is an empty dict.

            ¹ Here a `segment` has the same meaning as a `sweep`; we use `segment`
            to also indicate that this refers to a neo.Segment object.

            Optional, default is an empty dictionary.

        Var-keyword parameters (kwargs)
        -------------------------------
        These are passed directly to the datatypes.Episode superclass (see documentation
        for Episode)

        See also the class documentation.
        """
        self._type_ = episodeType
        if not isinstance(name, str):
            name = self._type_.name


        self._begin_ = datetime.datetime.now()
        self._end_ = datetime.datetime.now()
        self._beginFrame_ = 0
        self._endFrame_ = 0

        self._protocol_ = None

        # sequence of neo.Block objects.
        # these may be references to existing Block objects, or can be owned by
        # the episode
        self._blocks_ = list()
        # self._pathways_ = list()

        super().__init__(name, **kwargs)

        if isinstance(blocks, (tuple, list, collections.deque)) and all(isinstance(v, neo.Block) for v in blocks):
            self._blocks_[:] = sorted(list(blocks), key = lambda x: x.rec_datetime)
            self._setup_from_blocks_() # also sets up protocols

        if isinstance(protocol, ElectrophysiologyProtocol):
            # NOTE: 2024-09-30 08:49:45
            # ignore (with warning) if protocol was set up from the 'blocks' argument
            if isinstance(self._protocol_, ElectrophysiologyProtocol):
                scipywarn("The episode's protocol was already set up by the 'blocks' argument; 'protocol' argument will be ignored")
            else:
                self._protocol_ = protocol

        # NOTE: 2023-10-15 13:27:27
        # crosstalk mapping: ATTENTION: in this context cross-talk represents an
        # overlap between synapses activated by ideally distinct axonal pathways
        # (encapsulated by SynapticStimulusChannel objects) in the same RecordingSource
        #
        # Testing the degree of pathway separation is based on short-term plasticity
        # at the synapses under study: the "facilitation" or "depletion" of the synaptic
        # responses seen when two individual stimuli are delivered to the same synapse
        # (or group of synapses) at a short time interval ("paired-pulse ratio").
        #
        # When the two stimuli are delievered to distinct axonal bundles that synapse
        # on the same cell, the lack of facilitation or depletion indicates that
        # the two axonal pathways activate completely separated groups of synapses
        # on the postsynaptic cell.
        #
        # sweep index:intᵃ or tuple of int ↦ ordered sequence of pathway
        # indexes (int),
        #   e.g., for two pathways, using int keys:
        #       0 ↦ (0,1)       ⇒ sweep 0 tests cross-talk from path 0 to path 1
        #       1 ↦ (1,0)       ⇒ sweep 1 tests cross-talk from path 1 to path 0
        #
        #   or, as a tuple of two int:
        #       (0,2) ↦ (0,1)   ⇒ sweeps from 0 every 2 sweeps test cross-talk from path 0 to path 1
        #       (1,2) ↦ (1,0)   ⇒ sweeps from 1 every 2 sweeps test cross-talk from path 1 to path 0
        #
        #   ᵃ NOTE: relative to the first sweep in the episode!
        #
        # NOTE: no checks are done on the value of the key(s) so expect errors
        #   when trying to match an episode with data having the wrong number of
        # sweeps
        #
        # if isinstance(pathActivationBySweep,dict):
        self._pAxS = stimulusLayout

        # NOTE: 2024-09-30 08:52:22
        # parameters for the superclass (dataytypes.Episode) constructor
        #
        begin = kwargs.pop("begin", None)
        end = kwargs.pop("end", None)
        beginFrame = kwargs.pop("beginFrame", None)
        endFrame = kwargs.pop("endFrame", None)

        if isinstance(begin, datetime.datetime):
            self.begin = begin
        if isinstance(end, datetime.datetime):
            self.end = end

        if isinstance(beginFrame, int):
            if beginFrame < 0:
                raise ValueError(f"Invalid 'beginFrame': {beginFrame}")

            if isinstance(endFrame, int):
                if endFrame < beginFrame:
                    raise ValueError(f"Invalid 'endFrame': {endFrame} must be larger than {beginFrame}")

                if len(self._blocks_):
                    nframes = self.nFrames # cache that:)
                    if endFrame >= nFrames:
                        raise ValueError(f"Invalid 'endFrame': {endFrame} must be smaller than {nFrames}  frames")

            self.beginFrame = beginFrame

        if isinstance(endFrame, int):
            self.endFrame = endFrame

    def __repr__(self) -> str:
        ret = list()
        ret.append(f"{self.__class__.__name__}(name='{self.name}', type={self.type.name}), with:")
        ret.append(f"\tBlocks: {self.nBlocks}")
        ret.append(f"\tFrames: {self.nFrames}")
        ret.append(f"\tbegin={self.begin}, end={self.end}")
        ret.append(f"\tbeginFrame={self.beginFrame}, endFrame={self.endFrame}")

        ret.append(f"\tPathway Stimulation by Sweep: {self.pathActivationBySweep}")

        ret.append(f"\tProtocol name: {self.protocol.name if isinstance(self.protocol, ElectrophysiologyProtocol) else None}")

        return "\n".join(ret)

    def _repr_pretty_(self, p, cycle):
        supertxt = super().__repr__() + " with :"

        if cycle:
            p.text(supertxt)
        else:
            p.text(supertxt)
            p.breakable()
            attr_repr = [" "]

            p.text("Protocol name:")
            # attr_repr.append("Protocol:")
            attr_repr.append(f"\t{self.protocol.name if isinstance(self.protocol, ElectrophysiologyProtocol) else None}")
            # attr_repr += [f"\t{s}" for s in repr(self.protocol).split("\n")]

            # with p.group(q4 ,"(",")"):
            with p.group(4 ,"",""):
                for t in attr_repr:
                    p.text(t)
                    p.breakable()
                p.text("\n")

            p.text("Pathways:")
            p.breakable()

            if isinstance(self.pathActivationBySweep, dict) and len(self.pathActivationBySweep):
                link = " \u2192 "
                txt = ["Pathway Stimulation by Sweep:"]

                for k,v in self.pathActivationBySweep.items():
                    txt.append(f"Sweeps {k} ↦ {v}")

                p.text("\n".join(txt))
                p.breakable()
                p.text("\n")

            p.breakable()

    def toHDF5(self,group:h5py.Group, name:str, oname:str,
                       compression:str, chunks:bool, track_order:bool,
                       entity_cache:dict) -> h5py.Group:
        r"""Overrides datatypes.Episode.toHDF5"""

        from iolib import h5io
        # print(f"{self.__class__.__name__}.toHDF5: {self.name}")
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity

        attrs = dict((x, getattr(self, x)) for x in ("name", "begin", "end", "beginFrame", "endFrame", "type",
                                                     "clampMode", "electrodeMode"))

        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)

        if isinstance(name, str) and len(name.strip()):
            target_name = name

        # entity = group.create_dataset(name, data = h5py.Empty("f"), track_order=track_order)
        entity = group.create_group(target_name, track_order=track_order)
        entity.attrs.update(obj_attrs)

        h5io.toHDF5(self.blocks, entity, name="blocks", oname="blocks",
                            compression=compression,chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)

        h5io.toHDF5(self.protocol, entity, name="protocol", oname="protocol",
                            compression=compression,chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)

        h5io.toHDF5(self.pathActivationBySweep, entity, name="pathActivationBySweep", oname="pathActivationBySweep",
                            compression=compression,chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)

        h5io.storeEntityInCache(entity_cache, self, entity)

        return entity

    @classmethod
    def fromHDF5(cls, entity:h5py.Group,
                             attrs:typing.Optional[dict]=None, cache:dict = {}):

        from iolib import h5io
        if entity in cache:
            return cache[entity]

        attrs = h5io.attrs2dict(entity.attrs)

        blocks = h5io.fromHDF5(entity["blocks"], cache=cache)
        protocol = h5io.fromHDF5(entity["protocol"], cache=cache)
        stimulationLayout = h5io.fromHDF5(entity["stimulationLayout"], cache=cache)

        name=attrs["name"]
        begin=attrs["begin"]
        end=attrs["end"]
        beginFrame=attrs["beginFrame"]
        endFrame=attrs["endFrame"]
        episodeType=attrs["type"]
        clampMode = attrs["clampMode"]
        electrodeMode = attrs["electrodeMode"]

        return cls(name=name, episodeType=episodeType, begin=begin, end=end,
                beginframe=beginFrame,endFrame=endFrame,
                protocol=protocol,
                blocks = blocks,
                stimulationLayout=stimulationLayout,
                clampMode = clampMode,
                electrodeMode = electrodeMode)


    @property
    def stimulationLayout(self) -> dict:
        r"""Maps a correspondence between the sweep(s) that stimulate pathways and the stimulated pathways
        """
        return self._pAxS

    @stimulationLayout.setter
    def stimulationLayout(self, layout: typing.Optional[PathwaysStimulationLayout] = None) -> None:
        if not isinstance(layout, PathwaysStimulationLayout):
            scipywarn(f"Expecting a PathwaysStimulationLayout or None; instead, got a {type(layout).__name__} ")
        self._pAxS = layout

    @property
    def isXTalk(self) -> bool:
        return isinstance(self.stimulationLayout, PathwaysStimulationLayout) and PathwaysStimulationLayout.isXTalkLayout(self.stimulationLayout)

    @property
    def blocks(self) -> list:
        return self._blocks_

    @blocks.setter
    def blocks(self, val:typing.Sequence[neo.Block]):
        r"""Assign new blocks to the episode.
        If val is an empty sequence, the blocks will be cleared.
        """
        if not isinstance(val, (tuple, list, collections.deque)):
            raise TypeError(f"Expecting a sequence of neo.Block objects; instead got {type(val).__name__}")

        if len(val):
            if not all(isinstance(v, neo.Block) for v in val):
                raise TypeError("All elements of the sequence must be neo.Block objects")

            self._blocks_[:] = sorted(list(val), key = lambda x: x.rec_datetime)

        else:
            self._blocks_.clear()

        self._setup_from_blocks_()

    def _setup_from_blocks_(self):
        if len(self._blocks_) == 0:
            return

        self.begin = self._blocks_[0].rec_datetime
        self.end = self._blocks_[-1].rec_datetime + datetime.timedelta(seconds = float(neoutils.block_duration(self._blocks_[-1])))

        self.beginFrame = 0
        self.endFrame = sum([len(b.segments) for b in self._blocks_]) - 1

        block_protocols = list()

        try:
            block_protocols = unique(list(filter(lambda x: isinstance(x, ElectrophysiologyProtocol), map(lambda x: getProtocol(x), self._blocks_))), idcheck=False)
        except:
            scipywarn("Cannot parse protocols from the Block objects")
            traceback.print_exc()

        if len(block_protocols) != 1:
            raise RuntimeError("An episode can have exactly one protocol")

        self._protocol_ = block_protocols[0]

    def addBlock(self, x:neo.Block):
        r"""Adds a new block; blocks will be reordered by rec_datetime if necessary"""
        if not isinstance(x, neo.Block):
            raise TypeError(f"Expecting a neo.Block; instead, got {type().__name__}")

        protocol = getProtocol(x)
        if isinstance(self._protocol_, ElectrophysiologyProtocol):
            # make sure they use the same protocol
            protocols = unique([protocol, self._protocol_], idcheck=False)
            if len(protocols) != 1:
                raise RuntimeError("Cannot add new block because is using a different protocol")

        else:
            self._protocol_ = protocol

        blocks = self._blocks_ + [x]
        self.blocks = blocks

    def removeBlock(self, index:typing.Union[int, str]):
        r"""Removes a block by name or by its index in the episode blocks"""
        if isinstance(index, str):
            blocknames = [b.name for b in self._blocks_]
            if index not in blocknames:
                raise ValueError(f"Block name {index} not found in this episode")

            x = blocknames.index(index)

        elif isinstance(index, int):
            if index>= len(self._blocks_):
                raise ValueError(f"Invalid block index {index} for {len(self._blocks_)} blocks")

        else:
            raise TypeError("")

        block = self._blocks_[index]

        del self._blocks_[index]

        protocol = getProtocol(block)
        if isinstance(protocol, ElectrophysiologyProtocol):
            if protocol in self._protocols_:
                ndx = self._protocols_.index(protocol)
                del self._protocols_[ndx]

        self._setup_from_blocks_() # will also update the protocols,

    def setFrameLimits(self, begin:int, end:int):
        if abs(end-begin) != self.nFrames-1:
            raise ValueError(f"Mismatch between number of frames {self.nFrames} and begin / end ({begin} / {end})")

        begin, end = min(begin, end), max(begin, end)

        self._beginFrame_ = begin
        self._endFrame_ = end

    @property
    def protocol(self) -> ElectrophysiologyProtocol:
        return self._protocol_

    @protocol.setter
    def protocol(self, val:ElectrophysiologyProtocol) -> None:
        if isinstance(val, ElectrophysiologyProtocol) or val is None:
            self._protocol_ = val

    @property
    def begin(self) -> datetime.datetime:
        return self._begin_

    @begin.setter
    def begin(self, val:datetime.datetime):
        if not isinstance(val, datetime.datetime):
            raise TypeError(f"Expecting a datetime.datetime; got {type(val).__name__} instead")

        if val > self.end:
            scipywarn(f"Setting 'begin' ({val}) to be later than 'end' ({self.end})")

        self._begin_ = val

    @property
    def end(self) -> datetime.datetime:
        return self._end_

    @end.setter
    def end(self, val:datetime.datetime):
        if not isinstance(val, datetime.datetime):
            raise TypeError(f"Expecting a datetime.datetime; got {type(val).__name__} instead")

        if val < self.begin:
            scipywarn(f"Setting 'end' ({val}) to be earlier than 'begin' ({self.begin})")

        self._end_ = val

    @property
    def beginFrame(self) -> int:
        return self._beginFrame_

    @beginFrame.setter
    def beginFrame(self, val:int):
        if not isinstance(val, int):
            raise TypeError(f"Expecting an int; got {type(val).__name__} instead")

        if val < 0:
            raise ValueError(f"Cannot set beginFrame to < 0 ({val})")

        if val > self.endFrame:
            scipywarn(f"Setting 'beginFrame' ({val}) to a value larger than 'endFrame' ({self.endFrame})")

        self._beginFrame_ = val

    @property
    def endFrame(self) -> int:
        return self._endFrame_

    @endFrame.setter
    def endFrame(self, val:int):
        if not isinstance(val, int):
            raise TypeError(f"Expecting an int; got {type(val).__name__} instead")

        if len(self._blocks_) and val >= self.beginFrame + self.nFrames:
            raise ValueError(f"'endFrame' ({val}) must be less than {self.nFrames} available frames")

        if val < 0:
            raise ValueError(f"'endFrame' cannot be < 0; got {val} instead")

        if val < self.beginFrame:
            scipywarn(f"Setting 'endFrame' ({val}) to a value less than 'beginFrame' ({self.beginFrame})")

        self._endFrame_ = val

    @property
    def nFrames(self) -> int:
        r"""Number of frames in this episode; """
        if len(self._blocks_) == 0:
            return 0

        return sum([len(b.segments) for b in self._blocks_])

    @property
    def nBlocks(self) -> int:
        return len(self._blocks_)

    @property
    def type(self) -> RecordingEpisodeType:
        return self._type_

    @type.setter
    def type(self, val:RecordingEpisodeType):
        if isinstance(val, RecordingEpisodeType):
            self._type_ = val
        else:
            scipywarn(f"Expecting a RecordingEpisodeType, instead got {val}")

    @property
    def pathways(self) -> typing.List[SynapticPathway]:
        ret = list()
        for v in self.pathActivationBySweep.values():
            p = [v_ for v_ in v if v_ not in ret]
            ret += p

        return ret

@with_doc(Schedule, use_header=True, header_str = "Inherits from:")
class RecordingSchedule(Schedule):
    def __init__(self, name: typing.Optional[str] = None, **kwargs):
        super().__init__(name, **kwargs)

    def __repr__(self):
        ret = list()
        ret.append(f"{self.__class__.__name__}(name='{self.name}'), with {len(self.episodes)} episodes:")
        for k,e in enumerate(self.episodes):
            ret.append(f"{k}: {e}")

        return "\n".join(ret)

    def __add__(self, other):
        if isinstance(other, self.__class__):
            newepisodes = self.episodes.__add__(other.episodes)
            return self.__class__(name=self.name, episodes = newepisodes)

        elif isinstance(other, typing.Sequence):
            if len(other) and not all(isinstance(e, RecordingEpisode)):
                raise TypeError("Can only add a sequence of RecordingEpisodes")
            newepisodes = self.episodes.__add__(other)
            return self.__class__(name=self.name, episodes = newepisodes)

        else:
            raise TypeError(f"Invalid argument type ({type(other).__name__})")

    def __iadd__(self, other):
        if isinstance(other, self.__class__):
            self.episodes.__iadd__(other.episodes)
            return self

        elif isinstance(other, typing.Sequence):
            if len(other) and not all(isinstance(e, RecordingEpisode)):
                raise TypeError("Can only add a sequence of RecordingEpisodes")
            self.episodes.__iadd__(other)
            return self

        else:
            raise TypeError(f"Invalid argument type ({type(other).__name__})")

    def append(self, value:RecordingEpisode):
        if not isinstance(value, RecordingEpisode):
            raise TypeError("A RecordingSchedule can only contain RecordingEpisodes")

        self.episodes.append(value)

    def insert(self, index:int, value:RecordingEpisode):
        if not isinstance(value, RecordingEpisode):
            raise TypeError("A RecordingSchedule can only contain RecordingEpisodes")

        self.episodes.insert(index, value)

    def remove(self, value:RecordingEpisode):
        if not isinstance(value, RecordingEpisode):
            raise TypeError("A RecordingSchedule can only contain RecordingEpisodes")

        self.episodes.remove(value)

    def extend(self, value):
        if isinstance(value, self.__class__):
            self.episodes.append(value.episodes)

        elif isinstance(value, typing.Sequence):
            if len(value):
                if all(isinstance(v, RecordingEpisode) for v in value):
                    self.episodes.append(value)
                else:
                    raise TypeError("A RecordingSchedule can only contain RecordingEpisodes")

        else:
            raise TypeError(f"Can only append a RecordingSchedule or a sequence of RecordingEpisodes")

    def index(self, episode:RecordingEpisode):
        if not isinstance(episode, RecordingEpisode):
            raise TypeError("A RecordingSchedule can only contain RecordingEpisodes")
        if episode not in self.episodes:
            raise ValueError("Episode is not contained in this RecordingSchedule")

        ndx = [k for k in range(len(self.episodes)) if self.episodes[k] == episode]

        return ndx[0]

    def count(self, episode:RecordingEpisode):
        if not isinstance(episode, RecordingEpisode):
            raise TypeError("A RecordingSchedule can only contain RecordingEpisodes")

        if episode not in self.episodes:
            return 0

        return len(e for e in self.episodes if e == episode)

    @property
    def nFrames(self) -> int:
        return sum([e.nFrames for e in self.episodes])

    @property
    def pathways(self):
        return unique(list(itertools.chain.from_iterable([e.pathways for e in self.episodes])))

    @property
    def blocks(self) -> typing.List[neo.Block]:
        ret = list()

        for episode in self.episodes:
            ret += episode.blocks

        return ret

    def updateEpisodeFrames(self):
        currentFrame = 0
        for k, episode in enumerate(self.episodes):
            episode.setFrameLimits(currentFrame, currentFrame + episode.nFrames - 1)
            # episode.endFrame = currentFrame + episode.nFrames - 1
            # episode.beginFrame = currentFrame
            currentFrame = episode.endFrame + 1


    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Group:
        # NOTE: 2024-07-20 18:48:45
        # although it inherits toHDF5 and fromHDF5 from
        # datatypes.Schedule, that method encodes datatype.Episode as h5py.Datasets
        # whereas here we need to encode RecordingEpisodes as h5py.Group
        from iolib import h5io
        # print(f"{self.__class__.__name__}.toHDF5: {self.name}")
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity

        attrs = {"name": getattr(self, "name")}

        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)

        if isinstance(name, str) and len(name.strip()):
            target_name = name

        entity = group.create_group(target_name, track_order=track_order)
        entity.attrs.update(obj_attrs)
        h5io.toHDF5(self.episodes, entity, name="episodes",
                            oname="episodes", compression=compression,
                            chunks=chunks, track_order=track_order,
                            entity_cache=entity_cache)

        h5io.storeEntityInCache(entity_cache, self, entity)
        return entity

    @classmethod
    def fromHDF5(cls, entity:h5py.Dataset,
                             attrs:typing.Optional[dict]=None, cache:dict={}):

        # NOTE: 2024-07-21 10:05:58 see NOTE: 2024-07-20 18:48:45

        from iolib import h5io
        if entity in cache:
            return cache[entity]

        attrs = h5io.attrs2dict(entity.attrs)

        name = attrs["name"]

        episodes = h5io.fromHDF5(entity["episodes"], cache)

        return cls(name, episodes=episodes)



class SynapticPathwayType(TypeEnum):
    r"""
    Synaptic pathway type.
    Encapsulates: Null, Test, Control, Auxiliary, UserDefined

    A Test pathway is defined by the presence of a Conditioning episode between
    two non-Conditioning episodes - see RecordingEpisodeType class.

        A non-Conditioning episode is usually a Tracking episode, but can also be
        a Crosstalk or Drug episode.

        Where justified, the test pathway may be "conditioned" more than once.
        In this case, the Conditioning episodes MUST be separated by at least
        one non-Conditioning episode (usually a Tracking episode).

        In addition, there may be any number of Crosstalk, Drug and Washout
        applied either before, or after the Conditioning episode.

    The Control pathway is defined by the presence of at least one Tracking
        episode. No Conditioning episodes are allowed in a Control pathway.

    A combination of types IS NOT ALLOWED. The values were chosen to prevent
    ambiguities. Thus,

    Null    | Control   ⇒ Control       (1)
    Null    | Test      ⇒ Test          (2)
    Control | Test      ⇒ Auxiliary     (3)
    Control | Auxiliary ⇒ UserDefined   (4)

    Any value > 4 is invalid.

    """
    Null        = 0 # undefined; can associate any episode type, EXCEPT for Conditioning and Tracking
    Undefined   = Null
    Control     = 1 # can associate any episode type, EXCEPT for Conditioning
    Test        = 2 # can associate any episode type
    Auxiliary   = 3 # can associate any episode type, EXCEPT for Tracking;
                    # NOTE: this requirement is for analysis purpose only; the
                    # pathway can be activated during any type of episode, but
                    # synaptic responses do not need to be analysed during the
                    # tracking episodes.
                    # auxiliary pathways can be:
                    # • present along the tracking pathway, during tracking only
                    # • present along the induction pathway, during induction only
                    # • present throughout
    UserDefined = 4 # can associate any episode type, EXCEPT for Tracking (see above)

class __BaseSynStimChannel__(typing.NamedTuple):
    name: str = "stim"
    channel: typing.Union[int, str] = 0
    dig: bool=True

class SynapticStimulusChannel(__BaseSynStimChannel__):
    # see https://stackoverflow.com/questions/61844368/how-to-initialize-a-namedtuple-child-class-different-ways-based-on-input-argumen
    __slots__ = ()

    __sig__ = ", ".join([f"{k}: {type2str(v)}" for (k,v) in __BaseSynStimChannel__.__annotations__.items()])

    __doc__ = "\n".join( ["Logical association between digital or analog outputs and synaptic stimulation.\n",
                    "Signature:\n",
                    f"\tSynapticStimulusChannel({__sig__})\n",
                    "where:",
                    "• name (str): the name of this synaptic simulus; default is 'stim'\n",
                    "• channel (int, str): index or name of the output channel sending TTL",
                    "   triggers to a synaptic stimulation device e.g. stimulus isolation box,",
                    "   uncaging laser modulator, LED device, 𝑒𝑡𝑐.",
                    "   Optional; default is 0\n",
                    "• dig (bool): indicates the type of the triggering channel",
                    "   (used when the 'channel' field is an int):",
                    "   when True, the channel is a digital output",
                    "   when False, the channel is a DAC that emulates TTL triggers",
                    "   Optional; default is True\n"
                    "",
                    "Channel indices are expected to be >= 0 and correspond to the",
                    "    logical channel indices in the acquisition protocol.\n",
                    "Channel names are as assigned in the acquisition protocol (if available).",
                    "",
                    "NOTE: The order of parameters matters, unless they are given as name↦value pairs.",
                    "",
                    "Since only DAC channels can be named in a protocol, specifying a str as 'channel'",
                    "   implied the stimulus is a DAC channel and not a DIG output channel."
                    ""])

    @classmethod
    def __new__(cls, *args, **kwargs):
        super_anns = super().__annotations__
        fields = list(super_anns.keys())
        super_defaults = super()._field_defaults

        args = args[1:] # drop cls

        if len(args) > len(super_anns):
            raise SyntaxError(f"Too many positional parameters ({len(args)}); expecting {len(fields)}")

        new_args = dict()
        for k, arg in enumerate(args):
            # if not isinstance(arg, super_anns[fields[k]]):
            if not datatypes.check_type(type(arg), super_anns[fields[k]]).value:
                raise TypeError(f"Expecting a {super_anns[fields[k]]}; instead, got a {type(arg)}")
            new_args[fields[k]] = arg

        if len(new_args) == len(super_anns):
            if len(kwargs):
                dups = [k for k in kwargs if k in fields]
                if len(dups):
                    raise SyntaxError(f"Duplicate specification of parameters: {dups}")
                else:
                    raise SyntaxError(f"Spurious additional keyword parameters: {kwargs}")

        else:
            if len(kwargs):
                dups = [k for k in kwargs if k in new_args]
                if len(dups):
                    raise SyntaxError(f"Duplicate specification of parameters: {dups}")

                spurious = [k for k in kwargs if k not in fields]
                if len(spurious):
                    raise SyntaxError(f"Unknown/unsupported keyword parameters specified: {spurious}")

                new_kwargs = dict((k,v) for k, v in kwargs.items() if k in fields and k not in new_args)

                new_args.update(new_kwargs)

            # finally, add the default unspecified args
            for (k,v) in super_defaults.items():
                if k not in new_args:
                    new_args[k] = v

        return super().__new__(cls, **new_args)

    def __eq__(self, other) -> bool:
        ret = type(self) == type(other)
        if not ret:
            return ret

        ret &= all(getattr(self, f) == getattr(other, f) for f in self._fields)

        return ret

    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Dataset:

        from iolib import h5io
        # print(f"{self.__class__.__name__}.toHDF5: {self.name} -> name: {name}, oname: {oname}")
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[name] = cached_entity
            return cached_entity

        attrs = {"name": self.name, "channel": self.channel, "dig": self.dig}

        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)

        if isinstance(name, str) and len(name.strip()):
            target_name = name

        entity = group.create_dataset(name, data = h5py.Empty("f"),
                                      track_order=track_order)
        entity.attrs.update(obj_attrs)
        h5io.storeEntityInCache(entity_cache, self, entity)

        return entity

    @classmethod
    def fromHDF5(cls, entity:h5py.Dataset,
                             attrs:typing.Optional[dict]=None, cache:dict = {}):

        from iolib import h5io
        if entity in cache:
            return cache[entity]

        attrs = h5io.attrs2dict(entity.attrs)

        name = attrs["name"]
        channel = attrs["channel"]

        if isinstance(channel, np.int64):
            channel = int(channel)

        dig = attrs["dig"]
        if isinstance(dig, np.bool_):
            dig = bool(dig)

        return cls(name, channel, dig)

SynapticStimulusChannel.name.__doc__ = "str: the name of this synaptic simulus; default is 'stim'"
SynapticStimulusChannel.channel.__doc__ = "int, str: index or name of the output channel sending TTL triggers"
SynapticStimulusChannel.dig.__doc__ = "bool: indicates if the triggering channel if a digital output (True) or a DAC (False)"

class SynapticStimulusChannelList(NeoObjectList):
    allowed_contents = (SynapticStimulusChannel, )

    def __init__(self, *items, name:typing.Optional[str] = None,
                 parent: object = None):
        self.name = "" if not isinstance(name, str) else name
        self._items = list()

        if len(items):
            if len(items) == 1:
                if isinstance(items[0], typing.Sequence):
                    items = items[0]
                else:
                    raise TypeError(f"Expecting a sequence, instead, got a {type(items[0]).__name__}")

            if any(
                not isinstance(i, self.allowed_contents)
                or not any(type(i).__name__ in n for n in list(map(lambda t: t.__name__, self.allowed_contents)))
                for i in items):
                raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(item).__name__}")

            self._items = list(items)

        if parent is not None and ScipyenDataclass not in inspect.getmro(type(parent)):
            raise TypeError(f"Parent must be a ScipyenDataclass or None; got {type(parent).__name__} instead")

        self._parent = parent

    @property
    def parent(self) -> ScipyenDataclass | None:
        return self._parent

    def __iter__(self):
        """Implement iter(self)"""
        for item in self._items:
            yield item

    def __delitem__(self, i: int) -> None:
        if len(self._items) == 0:
            return

        if i < len(self._items) and i >= -len(self._items):
            del(self._items[i])
        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __getitem__(self, i: int) -> SynapticStimulusChannel | None:
        """x.__getitem__(y) <==> x[y]"""
        if len(self._items) == 0:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

        if i < len(self._items) and i >= -len(self._items):
            return self._items[i]

        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __setitem__(self, i: int, value: SynapticStimulusChannel):
        if not isinstance(value, self.allowed_contents):
            raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(value).__name__}")

        if len(self._items) == 0:
            raise ValueError(f"Index {i} out of range for {len(self._items)} items")

        if i < len(self._items) and i >= -len(self._items):
            self._items[i] = value

        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __str__(self):
        """Return str(self)"""
        return f"<{self.__class__.__name__}> with {len(self._items)} {self.allowed_contents[0].__name__} objects"

    def __repr__(self):
        header = f"<{self.__class__.__name__}>"
        if isinstance(self.name, str) and len(self.name.strip()):
            header += f" '{self.name}'"

        s = [f"{header} with {len(self._items)} {self.allowed_contents[0].__name__} objects",
            ]

        if len(self._items):
            s[0]+= ":"
            s.extend(list(map(lambda p: f"{p[0]}: {p[1]}", enumerate(self._items))))

        return "\n".join(s)

    def __len__(self):
        """Return len(self)"""
        return len(self._items)

    def _add_items(self, other: typing.Self, in_place=False) -> typing.Self:
        self._items = self._items + other._items
        return self

    def __add__(self, other):
        """Return self + other"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return ret._add_items(other)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret

        else:
            return ret

    def __iadd__(self, other):
        """Return self"""
        if isinstance(other, self.__class__):
            return self._add_items(other, in_place=True)

        elif isinstance(other, self.allowed_contents):
            self._items.append(other)
            return self

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            self._items.extend(list(other))
            return self

        else:
            return self

    def __radd__(self, other):
        """Return other + self"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return other._add_items(ret)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret
        else:
            return ret

    def append(self, obj):
        """
        Appends a SynapticStimulusChannel

        Parameters
        ----------
        obj: SynapticStimulusChannel

        """
        if not isinstance(obj, self.allowed_contents):
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")
        self._items.append(obj)

    def extend(self, iterable):
        """Extends with additional SynapticStimulusChannel objects from an iterable

        Parameters
        ----------
        iterable: iterable[SynapticStimulusChannel]

        """
        if all (isinstance(o, self.allowed_contents) for o in iterable):
            self._items.extend(iterable)
        else:
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")


def synstim(name:str, channel:typing.Optional[int]=None, dig:bool=True) -> SynapticStimulusChannel:
    r"""Shorthand constructor of SynapticStimulusChannel (saves typing)"""
    return SynapticStimulusChannel(name, channel, dig)

class __BaseAuxInput__(typing.NamedTuple):
    name: str = "aux_in"
    adc: int = 0
    # adc: typing.Union[int, str] = 0
    cmd: Tribool = Tribool() # reflects an input that "copies" a command signal

class AuxiliaryInput(__BaseAuxInput__):
    __slots__ = ()
    __sig__ = ", ".join([f"{k}: {type2str(v)}" for (k,v) in __BaseAuxInput__.__annotations__.items()])
    __doc__ = "\n".join(["An auxiliary input identifies an ADC for recording a signal other than",
                "the primary amplifier output (e.g. a secondary amplifier output, 'copies' ",
                "of digital TTLs or DAQ command output signals sent to the amplifier, ",
                "output from auxiliary measurement device, 𝑒𝑡𝑐.)\n",
                "Signature:\n"
                f"\tAuxiliaryInput({__sig__})\n",
                "where:",
                "• name (str): name of this auxiliary input specification; default is 'aux_in'.\n",
                "• adc (int, str): index or name of the ADC channel used to record the auxiliary input.",
                "   Optional; default is 0.\n",
                "• cmd (bool, None): default is None; ",
                "   when True, this is a 'copy' of a command signal, or of an appropriately chosen",
                "       secondary amplifier output, as a 'proxy' of the command signal (e.g.",
                "       membrane potential in voltage clamp, or membrane current in current clamp)¹;",
                "   when False, this indicates that this auxiliary input is a copy or a trigger (TTL-like)",
                "       signal (either from a digital output or from a DAC);",
                "   when None, this auxiliary input carries any other signal NOT mentioned above.\n"
                "",
                "Channel indices are expected to be >= 0 and correspond to the logical channel",
                "    indices in the acquisition protocol.\n",
                "Channel names are as assigned in the acquisition protocol (if available).",
                "",
                "NOTE: The order of parameters matters, unless they are given as name↦value pairs.",
                "",
                "¹ In modern amplifiers the recording electrode switches between voltage measurement and current injection,",
                "   with a high cycle rate; therefore, both membrane potential and current are theoretically available "
                ""])

    @classmethod
    def __new__(cls, *args, **kwargs):
        super_anns = super().__annotations__
        fields = list(super_anns.keys())
        super_defaults = super()._field_defaults

        args = args[1:] # drop cls

        if len(args) > len(super_anns):
            raise SyntaxError(f"Too many positional parameters ({len(args)}); expecting {len(fields)}")

        new_args = dict()
        for k, arg in enumerate(args):
            if not datatypes.check_type(type(arg), super_anns[fields[k]]).value:
                raise TypeError(f"Expecting a {super_anns[fields[k]]}; instead, got a {type(arg)}")
            new_args[fields[k]] = arg

        if len(new_args) == len(super_anns):
            if len(kwargs):
                dups = [k for k in kwargs if k in fields]
                if len(dups):
                    raise SyntaxError(f"Duplicate specification of parameters: {dups}")
                else:
                    raise SyntaxError(f"Spurious additional keyword parameters: {kwargs}")

        else:
            if len(kwargs):
                dups = [k for k in kwargs if k in new_args]
                if len(dups):
                    raise SyntaxError(f"Duplicate specification of parameters: {dups}")

                spurious = [k for k in kwargs if k not in fields]
                if len(spurious):
                    raise SyntaxError(f"Unknown/unsupported keyword parameters specified: {spurious}")

                new_kwargs = dict((k,v) for k, v in kwargs.items() if k in fields and k not in new_args)

                new_args.update(new_kwargs)

            # finally, add the default unspecified args
            for (k,v) in super_defaults.items():
                if k not in new_args:
                    new_args[k] = v

        return super().__new__(cls, **new_args)

    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Dataset:
        from iolib import h5io
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity

        attrs = {"name":self.name, "adc":self.adc, "cmd":self.cmd}

        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)

        if isinstance(name, str) and len(name.strip()):
            target_name = name

        entity= group.create_dataset(target_name, h5py.Empty("f"),
                                     track_order=track_order)
        entity.attrs.update(obj_attrs)

        h5io.storeEntityInCache(entity_cache, self, entity)

        return entity

    @classmethod
    def fromHDF5(cls, entity:h5py.Dataset,
                             attrs:typing.Optional[dict]=None, cache:dict = {}):

        from iolib import h5io

        if entity in cache:
            return cache[entity]

        attrs = h5io.attrs2dict(entity.attrs)

        name=attrs["name"]
        adc =attrs["adc"]
        cmd =attrs["cmd"]

        return cls(name, adc, cmd)


AuxiliaryInput.name.__doc__ = "str: name of the auxiliary input specification; default is 'aux_in'"
AuxiliaryInput.adc.__doc__  = "int, str, None: index or name of the ADC channel used to record the auxiliary input; default is None."
AuxiliaryInput.cmd.__doc__  = "Tribool, None: indicates if the auxiliary ADC records (is a proxy of) a clamping command signal (True), a trigger (TTL-like) signal (False) or any other analog input (None); default is None"

class AuxiliaryInputList(NeoObjectList):
    allowed_contents = (AuxiliaryInput, )

    def __init__(self, *items, name:typing.Optional[str] = None,
                 parent: object = None):
        self.name = "" if not isinstance(name, str) else name
        self._items = list()

        if len(items):
            if len(items) == 1 and isinstance(items[0], typing.Sequence):
                items = items[0]

            if any(
                not isinstance(i, self.allowed_contents)
                or not any(type(i).__name__ in n for n in list(map(lambda t: t.__name__, self.allowed_contents)))
                for i in items):
                raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(item).__name__}")

            self._items = list(items)

        if parent is not None and ScipyenDataclass not in inspect.getmro(type(parent)):
            raise TypeError(f"Parent must be a ScipyenDataclass or None; got {type(parent).__name__} instead")

        self._parent = parent

    @property
    def parent(self) -> ScipyenDataclass | None:
        return self._parent

    def __iter__(self):
        """Implement iter(self)"""
        for item in self._items:
            yield item

    def __delitem__(self, i: int) -> None:
        if len(self._items) == 0:
            return

        if i < len(self._items) and i >= -len(self._items):
            del(self._items[i])
        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __getitem__(self, i: int) -> AuxiliaryInput | None:
        """x.__getitem__(y) <==> x[y]"""
        if len(self._items) == 0:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

        if i < len(self._items) and i >= -len(self._items):
            return self._items[i]

        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __setitem__(self, i: int, value: AuxiliaryInput):
        if not isinstance(value, self.allowed_contents):
            raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(value).__name__}")

        if len(self._items) == 0:
            raise ValueError(f"Index {i} out of range for {len(self._items)} items")

        if i < len(self._items) and i >= -len(self._items):
            self._items[i] = value

        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __str__(self):
        """Return str(self)"""
        return f"<{self.__class__.__name__}> with {len(self._items)} {self.allowed_contents[0].__name__} objects"

    def __repr__(self):
        header = f"<{self.__class__.__name__}>"
        if isinstance(self.name, str) and len(self.name.strip()):
            header += f" '{self.name}'"

        s = [f"{header} with {len(self._items)} {self.allowed_contents[0].__name__} objects",
            ]

        if len(self._items):
            s[0]+= ":"
            s.extend(list(map(lambda p: f"{p[0]}: {p[1]}", enumerate(self._items))))

        return "\n".join(s)

    def __len__(self):
        """Return len(self)"""
        return len(self._items)

    def _add_items(self, other: typing.Self, in_place=False) -> typing.Self:
        self._items = self._items + other._items
        return self

    def __add__(self, other):
        """Return self + other"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return ret._add_items(other)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret

        else:
            return ret

    def __iadd__(self, other):
        """Return self"""
        if isinstance(other, self.__class__):
            return self._add_items(other, in_place=True)

        elif isinstance(other, self.allowed_contents):
            self._items.append(other)
            return self

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            self._items.extend(list(other))
            return self

        else:
            return self

    def __radd__(self, other):
        """Return other + self"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return other._add_items(ret)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret
        else:
            return ret

    def append(self, obj):
        """
        Appends an AuxiliaryInput

        Parameters
        ----------
        obj: AuxiliaryInput

        """
        if not isinstance(obj, self.allowed_contents):
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")
        self._items.append(obj)

    def extend(self, iterable):
        """Extends with additional AuxiliaryInput objects from an iterable

        Parameters
        ----------
        iterable: iterable[AuxiliaryInput]

        """
        if all (isinstance(o, self.allowed_contents) for o in iterable):
            self._items.extend(iterable)
        else:
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")

def auxinput(name:str, adc:typing.Optional[int]=None, cmd:typing.Optional[bool]=None) -> AuxiliaryInput:
    r"""Constructs a run-of-the-mill AuxiliaryInput"""
    if adc is None:
        adc = 0
    elif not isinstance(adc, int):
        raise TypeError(f"'adc' expected an int; instead, got {type(adc).__name__}")
    return AuxiliaryInput(name, adc, cmd)

class __BaseAuxOutput__(typing.NamedTuple):
    name: str = "aux_out"
    channel: int = 0
    # channel: typing.Union[int, str] = 0
    # digttl: typing.Optional[bool] = None
    digttl: Tribool = Tribool()

class AuxiliaryOutput(__BaseAuxOutput__):
    __slots__ = ()
    __sig__ = ", ".join([f"{k}: {type2str(v)}" for (k,v) in __BaseAuxOutput__.__annotations__.items()])
    __doc__ = "\n".join(["An auxiliary (analog — DAC — or a digital — DIG) output channel of the DAQ device.\n",
                         "This channel is used for sending waveforms other than for clamping or synaptic ",
                         "stimulation (the latter being specified using SynapticStimulusChannel objects).\n",
                         "Signature:\n",
                         f"AuxiliaryOutput({__sig__})\n",
                         "where:"
                         "• name (str): name of this auxiliary output specification; default is 'aux_out'.\n",
                         "• channel (int, str): specifies the auxiliary output channel (index or name if a DAC channel, otherwise index only)\n",
                         "  Optional; default is 0.\n",
                         "• digttl (bool or None): flag to indicate if the output is used to send out triggers, with:",
                         "  True ⇒ the auxiliary output is a DIG channel (hence sending out exclusively TTL-like waveforms)",
                         "  False ⇒ the auxiliary output is a DAC channel used to emulaate TTLs",
                         "  None ⇒ the auxiliary outoyut is a DAC channel used to send arbitrary¹ waveforms",
                         "  Optional, default is None.\n",
                         "",
                         "Channel indices are expected to be >= 0 and correspond to the logical channel",
                         "    indices in the acquisition protocol.\n",
                         "Channel names are as assigned in the acquisition protocol (if available).",
                         "",
                         "NOTE: The order of parameters matters, unless they are given as name↦value pairs.",
                         "",
                         "¹ From the range of waveforms available in the acquisition software."
                         ])

    @classmethod
    def __new__(cls, *args, **kwargs):
        super_anns = super().__annotations__
        fields = list(super_anns.keys())
        super_defaults = super()._field_defaults

        args = args[1:] # drop cls

        if len(args) > len(super_anns):
            raise SyntaxError(f"Too many positional parameters ({len(args)}); expecting {len(fields)}")

        new_args = dict()
        for k, arg in enumerate(args):
            if not datatypes.check_type(type(arg), super_anns[fields[k]]).value:
                raise TypeError(f"Expecting a {super_anns[fields[k]]}; instead, got a {type(arg)}")
            new_args[fields[k]] = arg

        if len(new_args) == len(super_anns):
            if len(kwargs):
                dups = [k for k in kwargs if k in fields]
                if len(dups):
                    raise SyntaxError(f"Duplicate specification of parameters: {dups}")
                else:
                    raise SyntaxError(f"Spurious additional keyword parameters: {kwargs}")

        else:
            if len(kwargs):
                dups = [k for k in kwargs if k in new_args]
                if len(dups):
                    raise SyntaxError(f"Duplicate specification of parameters: {dups}")

                spurious = [k for k in kwargs if k not in fields]
                if len(spurious):
                    raise SyntaxError(f"Unknown/unsupported keyword parameters specified: {spurious}")

                new_kwargs = dict((k,v) for k, v in kwargs.items() if k in fields and k not in new_args)

                new_args.update(new_kwargs)

            # finally, add the default unspecified args
            for (k,v) in super_defaults.items():
                if k not in new_args:
                    new_args[k] = v

        return super().__new__(cls, **new_args)

    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Dataset:

        from iolib import h5io
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity

        attrs = {"name":self.name, "channel":self.channel, "digttl":self.digttl}

        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)

        if isinstance(name, str) and len(name.strip()):
            target_name = name

        entity= group.create_dataset(target_name, h5py.Empty("f"),
                                     track_order=track_order)
        entity.attrs.update(obj_attrs)

        h5io.storeEntityInCache(entity_cache, self, entity)

        return entity

    @classmethod
    def fromHDF5(cls, entity:h5py.Dataset,
                             attrs:typing.Optional[dict]=None, cache:dict = {}):

        from iolib import h5io

        if entity in cache:
            return cache[entity]

        attrs = h5io.attrs2dict(entity.attrs)

        name=attrs["name"]
        channel =attrs["channel"]
        digttl =attrs["digttl"]

        return cls(name, channel, digttl)

AuxiliaryOutput.name.__doc__ = "str: name of this auxiliary output specification; default is 'aux_out'"
AuxiliaryOutput.channel.__doc__ = "int, str: specifies the auxiliary output channel (index or name if a DAC channel, otherwise index only); default is 0"
AuxiliaryOutput.digttl.__doc__ = "Tribool: flag to indicate if the output is used to send out triggers via a DIG (Tribool(True)), emulated via a DAC (Tribool(False)) or other waveforms (Tribool(None)); default is Tribool(None)"

class AuxiliaryOutputList(NeoObjectList):
    allowed_contents = (AuxiliaryOutput, )

    def __init__(self, *items, name:typing.Optional[str] = None,
                 parent: object = None):
        self.name = "" if not isinstance(name, str) else name
        self._items = list()

        if len(items):
            if len(items) == 1 and isinstance(items[0], typing.Sequence):
                items = items[0]

            if any(
                not isinstance(i, self.allowed_contents)
                or not any(type(i).__name__ in n for n in list(map(lambda t: t.__name__, self.allowed_contents)))
                for i in items):
                raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(item).__name__}")

            self._items = list(items)

        if parent is not None and ScipyenDataclass not in inspect.getmro(type(parent)):
            raise TypeError(f"Parent must be a ScipyenDataclass or None; got {type(parent).__name__} instead")

        self._parent = parent

    @property
    def parent(self) -> ScipyenDataclass | None:
        return self._parent

    def __iter__(self):
        """Implement iter(self)"""
        for item in self._items:
            yield item

    def __delitem__(self, i: int) -> None:
        if len(self._items) == 0:
            return

        if i < len(self._items) and i >= -len(self._items):
            del(self._items[i])
        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __getitem__(self, i: int) -> AuxiliaryOutput | None:
        """x.__getitem__(y) <==> x[y]"""
        if len(self._items) == 0:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

        if i < len(self._items) and i >= -len(self._items):
            return self._items[i]

        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __setitem__(self, i: int, value: AuxiliaryOutput):
        if not isinstance(value, self.allowed_contents):
            raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(value).__name__}")

        if len(self._items) == 0:
            raise ValueError(f"Index {i} out of range for {len(self._items)} items")

        if i < len(self._items) and i >= -len(self._items):
            self._items[i] = value

        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __str__(self):
        """Return str(self)"""
        return f"<{self.__class__.__name__}> with {len(self._items)} {self.allowed_contents[0].__name__} objects"

    def __repr__(self):
        header = f"<{self.__class__.__name__}>"
        if isinstance(self.name, str) and len(self.name.strip()):
            header += f" '{self.name}'"

        s = [f"{header} with {len(self._items)} {self.allowed_contents[0].__name__} objects",
            ]

        if len(self._items):
            s[0]+= ":"
            s.extend(list(map(lambda p: f"{p[0]}: {p[1]}", enumerate(self._items))))

        return "\n".join(s)

    def __len__(self):
        """Return len(self)"""
        return len(self._items)

    def _add_items(self, other: typing.Self, in_place=False) -> typing.Self:
        self._items = self._items + other._items
        return self

    def __add__(self, other):
        """Return self + other"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return ret._add_items(other)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret

        else:
            return ret

    def __iadd__(self, other):
        """Return self"""
        if isinstance(other, self.__class__):
            return self._add_items(other, in_place=True)

        elif isinstance(other, self.allowed_contents):
            self._items.append(other)
            return self

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            self._items.extend(list(other))
            return self

        else:
            return self

    def __radd__(self, other):
        """Return other + self"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return other._add_items(ret)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret
        else:
            return ret

    def append(self, obj):
        """
        Appends an AuxiliaryOutput

        Parameters
        ----------
        obj: AuxiliaryOutput

        """
        if not isinstance(obj, self.allowed_contents):
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")
        self._items.append(obj)

    def extend(self, iterable):
        """Extends with additional AuxiliaryOutput objects from an iterable

        Parameters
        ----------
        iterable: iterable[AuxiliaryOutput]

        """
        if all (isinstance(o, self.allowed_contents) for o in iterable):
            self._items.extend(iterable)
        else:
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")


def auxoutput(name:str, channel:typing.Optional[int]=None, digttl:typing.Optional[bool]=None) -> AuxiliaryOutput:
    r"""Constructs a run-of-the-mill AuxiliaryOutput"""
    if channel is None:
        channel = 0

    if not isinstance(channel, int):
        raise TypeError(f"'channel' expected an int; instead, got {type(channel).__name__}")

    return AuxiliaryOutput(name, channel, digttl)

@dataclass
class RecordingSource():
    name: str = "cell"
    adc: int = 0
    dac: typing.Optional[int] = None
    syn: typing.Optional[SynapticStimulusChannelList]     = dataclasses.field(default_factory=SynapticStimulusChannelList)
    auxin: typing.Optional[AuxiliaryInputList]     = dataclasses.field(default_factory=AuxiliaryInputList)
    auxout: typing.Optional[AuxiliaryOutputList]   = dataclasses.field(default_factory=AuxiliaryOutputList)
    electrodeMode: ephys.ElectrodeMode = dataclasses.field(default=ephys.ElectrodeMode.Null)

    def __post_init__(self):
        # pathways = list()
        pathways = SynapticPathwayList(name=self.name)
        for syn in self.syn:
            # synList = SynapticStimulusChannelList(syn, name = syn.name)
            name = syn.name
            pathways.append(SynapticPathway(stimulus = syn,
                                    name = name, adc = self.adc,
                                    dac = self.dac,
                                    electrode = self.electrodeMode))
        self.pathways = pathways
        # self.pathways = tuple(pathways)

    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Group:
        from iolib import h5io
        # print(f"{self.__class__.__name__}.toHDF5: {self.name}")
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity

        attrs = {"name":self.name, "adc":self.adc, "dac":self.dac,
                 "electrodeMode": self.electrodeMode}

        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)

        if isinstance(name, str) and len(name.strip()):
            target_name = name

        entity = group.create_group(target_name, track_order=track_order)
        entity.attrs.update(obj_attrs)

        h5io.toHDF5(self.syn, entity, name="syn", oname="syn",
                            compression=compression, chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)

        h5io.toHDF5(self.auxin, entity, name="auxin", oname="auxin",
                            compression=compression, chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)

        h5io.toHDF5(self.auxout, entity, name="auxout", oname="auxout",
                            compression=compression, chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)

        h5io.storeEntityInCache(entity_cache, self, entity)
        return entity

    @classmethod
    def fromHDF5(cls, entity:h5py.Group,
                             attrs:typing.Optional[dict]=None, cache:dict = {}):

        from iolib import h5io
        if entity in cache:
            return cache[entity]

        attrs = h5io.attrs2dict(entity.attrs)

        name = attrs["name"]
        adc  = attrs["adc"]
        dac  = attrs["dac"]
        electrodeMode = attrs["electrodeMode"]

        syn = h5io.fromHDF5(entity["syn"], cache=cache)
        auxin = h5io.fromHDF5(entity["auxin"], cache=cache)
        auxout = h5io.fromHDF5(entity["auxout"], cache=cache)
        # pathways = h5io.fromHDF5(entity["pathways"], cache=cache)

        return cls(name=name, adc=adc, dac=dac, syn=syn,
                   auxin=auxin, auxout=auxout, electrodeMode = electrodeMode)

    @property
    def clamped(self) -> bool:
        r"""Returns True when a primary DAC is defined.

        A primary DAC is the index or name of the DAC channel used to send command
        waveforms to a clamped cell and is specified by the field 'dac'.

        NOTE: When a 'dac' channel is present (not None) the RecordingSource is considered
        'clamped' even if technically it is not (e.g. when using the amplifier's
        'I=0' mode, available in Axon amplifiers, or voltage follower).

        In field recordings (using voltage follower mode, or 'I=0' mode in Axon
        patch-clamp amplifiers) the primay DAC output ("active DAC") is still
        be present in the protocol, but it is not used.

        Setting 'dac' to None (in the constructor) simply flags up the ABSENCE of
        a clamp signal (and of command waveforms), and the fact that the "active DAC"
        in the protocol is to be ignored in subsequent analysis.
        """
        return isinstance(self.dac, (int, str))

    @property
    def syn_dig(self) -> tuple:
        r"""Tuple of DIG channels used for synaptic stimulation; may be empty.
        These channels emit TTLs to drive devices that elicit synaptic activity,
        such as stimulus isolation boxes, modulators for uncaging lasers, or LEDs
        for optogenetic stimulation.
        """
        if isinstance(self.syn, SynapticStimulusChannel):
            return (self.syn.channel,) if self.syn.dig else tuple()

        if isinstance(self.syn, typing.Sequence) and all(isinstance(s, SynapticStimulusChannel) for s in self.syn):
            return tuple(s.channel for s in self.syn if s.dig)

        return tuple()

    @property
    def syn_dac(self) -> tuple:
        r"""Tuple of DAC channels used for synaptic stimulation; may be empty.
        These channels emulate TTLs by emitting analog waveforms as pulses or steps
        in ± 5 V range, to drive devices that elicit synaptic activity
        such as stimulus isolation boxes, modulators for uncaging lasers, or LEDs
        for optogenetic stimulation.
        """
        if isinstance(self.syn, SynapticStimulusChannel):
            return (self.syn.channel, ) if not self.syn.dig else tuple()

        if isinstance(self.syn, typing.Sequence) and all(isinstance(s, SynapticStimulusChannel) for s in self.syn):
            return tuple(s.channel for s in self.syn if not s.dig)

        return tuple()

    # FIXME: 2024-10-17 22:35:04
    # this approach is WRONG, because it will create a new Python object
    # (SynapticPathway instance) every time the property getter is called; this
    # creates all sorts of trouble when attempting to use them by reference, down
    # the line (the new objects represent conceptually the same pathway even if
    # they are distinct Python objects!)
#     @property
#     def pathways(self) -> tuple:
#         r"""Factory for SynapticPathway objects based on the specifications in the `syn` field.
#         The SynapticPathway fields `pathwayType`, `schedule` and `measurement`
#         will have their default values.
#
#         Returns a possibly empty tuple of SynapticPathway objects where all their
#         fields are set to default values, except for their 'name', 'stimulus',
#         and 'source'.
#
#         """
#         if isinstance(self.syn, SynapticStimulusChannel):
#             return (SynapticPathway(source = self, stimulus = self.syn,
#                                     name = self.syn.name, adc = self.adc,
#                                     dac = self.dac,
#                                     electrode = self.electrodeMode), )
#
#         if isinstance(self.syn, (tuple, list)):
#             if len(self.syn) == 1:
#                 return tuple(SynapticPathway(source=self, stimulus = self.syn[0],
#                                        name = self.syn[0].name,
#                                        adc = self.adc, dac = self.dac,
#                                        electrode = self.electrodeMode))
#             elif len(self.syn) > 1:
#                 return tuple(SynapticPathway(source=self, stimulus = s,
#                                              name = s.name,
#                                              adc = self.adc, dac = self.dac,
#                                              electrode = self.electrodeMode) for s in self.syn)
#
#         return tuple()

    @property
    def in_daq_cmd(self) -> tuple:
        r"""Tuple of ADCs for recording DAQ-issued command waveforms other than TTLs.
        May be empty.

        These ADCs are specified in the 'auxin' field, and correspond to the auxiliary
        input channels of the DAQ device where a 'copy' of the clamping command
        signal is being fed. The inputs are configured in the recording protocol.

        NOTE: Technically, there should be only one such input, which can be:

        • a feed of the secondary amplifier output channel (when available, e.g.,
            membrane potential in voltage clamp, or membrane current in current clamp)
            into an auxiliary ADC input of the DAQ device, and used as a proxy
            for the clamping command signal itself;

        • a branch off the DAQ command output used for clamping (i.e. sent to the
            amplifier's command input); the branch is fed directly into an
            auxiliary ADC input to record a 'true' copy of the actual clamping
            command signal.

        A record copy of the command waveforms helps to identify, during subsequent
        analysis, the electrical manipulations of a cell — such as a membrane test,
        steps, ramps, pulses, induction of oscillatory phenomena or spikes, in a
        clamped cell, when these manipulations cannot be parsed (or reconstructed)
        from the recording protocol.

        """
        if isinstance(self.auxin, AuxiliaryInput):
            return (self.auxin.adc, ) if self.auxin.cmd is True else tuple()

        if isinstance(self.auxin, typing.Sequence) and all(isinstance(v, AuxiliaryInput) for v in self.auxin):
            return tuple(a.adc for a in self.auxin if a.cmd is True)

        return tuple()

    @property
    def in_daq_triggers(self) -> tuple:
        r"""Tuple of ADCs for recording DAQ-generated TTL signals;
        may be empty.

        These ADCs (analog inputs) are specified in the 'auxin' field and correspond
        to the auxiliary input channels of the DAQ device for recording a 'copy'
        of DAQ-issued triggers (other than for synaptic stimulaion purposes).

        These signals are configured in the recording protocol and can be branches
        off DIG (digital) or DAC (analog) outputs of the DAQ device, fed into
        auxiliary analog inputs.

        In the case of DAC outputs, these are the analog output channels where
        TTL-like waveforms are generated as pulses or steps in the range of ± 5 V
        and used in lieu of DIG outputs.

        Such inputs are useful to create a record copy of the TTLs sent out
        during an experiment, when these cannot be parsed from the recording
        protocol.

        """
        if isinstance(self.auxin, AuxiliaryInput):
            return tuple(self.auxin.adc) if self.auxin.cmd is False else tuple()

        if isinstance(self.auxin, typing.Sequence) and all(isinstance(v, AuxiliaryInput) for v in self.auxin):
            return tuple(a.adc for a in self.auxin if a.cmd is False)

        return tuple()

    @property
    def other_inputs(self) -> tuple:
        r"""Tuple of ADCs recording input signals not issued by the DAQ device.
        May be empty.

        These ADCs are specified in the 'auxin' field.

        Such inputs record auxiliary data signals other than clamping commands or
        TTLs, e.g. bath temperature, photodetector current, 'external' triggers,
        etc, and are neither generated by the source (cell or field) nor copies
        of command signal waveforms sent to the source in patch-clamp experiments.

        """
        if isinstance(self.auxin, AuxiliaryInput):
            return tuple(self.auxin.adc) if self.auxin.cmd is None else tuple()

        if isinstance(self.auxin, typing.Sequence) and all(isinstance(v, AuxiliaryInput) for v in self.auxin):
            return tuple(a.adc for a in self.auxin if a.cmd is None)

        return tuple()

    @property
    def syn_blocks(self) -> tuple:
        r"""Tuple of (name, neo.Block) tuples, one for each SynapticStimulusChannel.
        May be empty.
        """
        if isinstance(self.syn, SynapticStimulusChannel):
            return ((self.syn.name, neo.Block()),)

        if isinstance(self.syn, typing.Sequence) and all(isinstance(s, SynapticStimulusChannel) for s in self.syn):
            return tuple((s.name, neo.Block()) for s in self.syn)

        return tuple()

    @property
    def syn_blocks_dict(self) -> dict:
        r"""Returns syn_blocks as a dict with syn name ↦ empty neo.Block.
        """
        return dict(self.syn_blocks)

    @property
    def out_dig_triggers(self) -> tuple:
        r"""Tuple of DIG channels used to emit TTL (triggers) to 3ʳᵈ party devices.
        These TTLs are used for purposes other than synaptic stimulation.
        May be empty
        """
        if isinstance(self.auxout, AuxiliaryOutput):
            return (self.auxout.channel, ) if self.auxout.digttl is True else (tuple)

        if isinstance(self.auxout, typing.Sequence) and all(isinstance(v, AuxiliaryOutput) for v in self.auxout):
            return tuple(o.channel for o in self.auxout if o.digttl is True)

        return tuple()

    @property
    def out_dac_triggers(self) -> tuple:
        r"""Tuple of DAC channels used to emit TTL to 3ʳᵈ party devices.
        These TTLs are emulated (pulses or steps with ± 5 V range) and are used
        for purposes other than synaptic stimulation.
        """
        if isinstance(self.auxout, AuxiliaryOutput):
            return (self.auxout.channel, ) if self.auxout.digttl is False else (tuple)

        if isinstance(self.auxout, typing.Sequence) and all(isinstance(v, AuxiliaryOutput) for v in self.auxout):
            return tuple(o.channel for o in self.auxout if o.digttl is False)

        return tuple()

    @property
    def pathway_names(self) -> tuple:
        return tuple(map(lambda p: p.name), self.pathways)

    @property
    def other_outputs(self) -> tuple:
        if isinstance(self.auxout, AuxiliaryOutput):
            return (self.auxout.channel, ) if self.auxout.digttl is None else (tuple)

        if isinstance(self.auxout, typing.Sequence) and all(isinstance(v, AuxiliaryOutput) for v in self.auxout):
            return tuple(o.channel for o in self.auxout if o.digttl is None)

        return tuple()

    def getPathway(self, name:str):
        result = list(filter(lambda p: p.name == name, self.pathways))
        if len(result) == 1:
            return result[0]
        return result

    def getPathwaysByStimulationType(self, digital: typing.Optional[
                                                    typing.Union[bool, Tribool]
                                                    ] = Tribool(),
                                     asDict:bool=False
                                     ) -> typing.Union[tuple, dict[str, tuple]]:
        r"""Groups the synaptic pathways in this recording source by their means of activation.

        A synaptic pathway is activated by stimulating its synaptic inputs¹ using a
        physical "stimulus": e.g., electric pulse delivered to axons through electrodes,
        light pulses delivered from a light source, mechanical stimulus (piezo device).

        To control, the timing and, sometimes, the duration of the stimulus, the device
        that emits the stimulus is controlled va a TTL² electric signal delivered
        using a DAQ board, in one of two ways:
        • via a digital output channel ("DIG") - the most common way by far
        • as an analog waveform that emulates a TTL, via a digital to analog output
            channel (DAC) - typically used when no digital channels are available
            in the hardware.

        This function simply groups the SynapticPathway objects in the RecordingSource
        'src' according to whether the pathways use a digital (DIGPathways) or
        analog-to-digital channel (DACPathways).

        Parameters:
        -----------
        asDict:bool, optional default is False

        Returns:
        --------
        If `asDict` is False (default) return a pair of tuples, each containing
        a poibly empty sequence of SynapticPathway objects:
            • the first element contain pathways where the stimulus is delivered
                via a DAC using TTL emulation
            • the second element contains pathways where stimulus is delivered
                via a DIG channel

        If `asDict` is True, returns a dict with the keys "DACPathways",
            "DIGPathways" mapped to the sequences described above.

        NOTE: All fields of the SynapticPathway objects returned by this method
        have default values, except for those specified in this source ('name',
        'stimulus', and 'source').

        ¹ Neurotransmitter photo-uncaging is included here as method of activating
        synaptic inputs although technically it only emulates presynaptic neurotransmitter
        release.

        ² transistor-transistor-logic; this is typically a DC voltage pulse of 5 V
        amplitude (of either polarity) which "triggers" circuits in the controlled
        device (stimulus isolator, light shutter, piezo device, etc).  The controlled
        device can usually be configured to "react" to the rising or falling phase
        of the pulse, or to one of the two voltage levels of the pulse.

        See also:
        ---------
        • self.pathways

        """
        import more_itertools
        pathways = self.pathways
        if len(pathways) == 0:
            if asDict:
                return {"DACStimPathways": tuple(), "DIGStimPathways": tuple()}
            return tuple(), tuple()

        if isinstance(digital, bool):
            digital = Tribool(digital)
        elif digital is None:
            digital = Tribool()
        elif not isinstance(digital, Tribool):
            raise TypeError(f"'digital' parameters expected to be a Tribool, a bool, or None; instead got {type(digital).__name__}")


        if digital.value is True:
            dac_stim = tuple()
            dig_stim = tuple(x for x in pathways if x.stimulus.dig)
        elif digital.value is False:
            dac_stim = tuple(x for x in pathways if not x.stimulus.dig)
            dig_stim = tuple()
        else:
            dac_stim, dig_stim = tuple(tuple(x) for x in more_itertools.partition(lambda x: x.stimulus.dig, pathways))

        if asDict:
            return {"DACStimPathways": dac_stim, "DIGStimPathways": dig_stim}
        return dac_stim, dig_stim

    def pathwaysInProtocol(self, protocol:ElectrophysiologyProtocol, asDict:bool=False) -> typing.Union[tuple, dict[str, tuple]]:
        r"""SynapticPathway objects used in 'protocol'.

        The method identified which SynapticPathway objects defined by this
        RecordingSource are actually used in the specified protocol, by checking
        the usage of the pathway's ADC/DAC/DIG channels in the protocol.

        SynapticPathway objects are grouped by their stimulation
        method (DIG TTL or DAC emulation of TTL) and wrapped in a tuple or dict.

        To obtain a sequence of the SynapticPathway instances use the following
        idiom:

        ``` python

        tuple(unique(itertools.chain.from_iterable(src.pathwaysInProtocol(protocol)), idcheck=False))

        ```

        where 'src' is a RecordingSource object, and 'protocol' is an
        ElectrophysiologyProtocol object.

        See also:
        • self.pathways
        • self.getPathwaysByStimulationType

        """
        dac_stim_pathways, dig_stim_pathways = self.getPathwaysByStimulationType()

        adc = protocol.getADC(self.adc)
        dac = protocol.getDAC(self.dac)

        activeDAC  = protocol.getDAC()
        # digOutDacs = protocol.digitalOutputDACs

        mainDIGOut = protocol.digitalOutputs(alternate=False)
        altDIGOut  = protocol.digitalOutputs(alternate=True)

        if self.clamped:
            protocol_dac_stim_pathways = tuple(p for p in dac_stim_pathways if len(protocol.getDAC(p.stimulus.channel).emulatesTTL) and protocol.getDAC(p[1].stimulus.channel) not in (dac, activeDAC))
        else:
            protocol_dac_stim_pathways = tuple(p for p in dac_stim_pathways if len(protocol.getDAC(p.stimulus.channel).emulatesTTL))

        protocol_dig_stim_pathways = tuple(p for p in dig_stim_pathways if p.stimulus.channel in mainDIGOut or altDIGOut)

        if asDict:
            return {"DACStimPathways": protocol_dac_stim_pathways, "DIGStimPathways": protocol_dig_stim_pathways}

        return protocol_dac_stim_pathways, protocol_dig_stim_pathways

    def getPathwayActivationbBySweep(self, protocol:ElectrophysiologyProtocol) -> dict:
        r"""Distribution of pathway activation by sweep, in a given protocol.

        Returns:
        --------

        A key ↦ value mapping indicating which synaptic pathways are activated
            during specific sweeps, as configured in the protocol.

        key: int|tuple[int] — sweep index or indices

        value: tuple[SynapticPathway] — the pathways that are activated while
            recording the sweeps with index (indices) in the 'key'; may be empty.

        To obtain a sequence of all pathways used in the protocol one can use the
        following idiom:

        ``` python
        mapping = self.getPathwayActivationbBySweep(protocol)

        pathways = tuple(unique(itertools.chain.from_iterable(mapping.values()), idcheck=False))

        ```
        (NOTE: `idcheck` is set to False in order to force comparing the SynapticPathway
        objects by their properties, rather than their Python ID or memory locations)


        See also:
        ---------
        • self.pathwaysInProtocol

        """
        protocol_dac_stim_pathways, protocol_dig_stim_pathways = self.pathwaysInProtocol(protocol)
        if all(len(x) == 0 for x in (protocol_dac_stim_pathways, protocol_dig_stim_pathways)):
            return dict()

        uniquePathways = unique(protocol_dac_stim_pathways + protocol_dig_stim_pathways, idcheck=True)

        return getPathwayBySweepActivation(protocol, uniquePathways)

    def __repr__(self) -> str:
        import dataclasses
        ret = [f"{self.__class__.__name__}("]
        ret += ", ".join([f"{a.name}={getattr(self,a.name).name if a == 'electrodeMode' else getattr(self, a.name)}" for a in dataclasses.fields(self)])
        ret +=[")"]
        if len(self.pathways):
            ret += f" with {len(self.pathways)} synaptic pathways:\n"
            if len(self.pathways) <= 5:
                ret += ", ".join([f"'{p.name}'" for p in self.pathways])
            else:
                ret += ",\n".join([f"'{p.name}'" for p in self.pathways])
        return "".join(ret)

class PathwaysCrossTalk(typing.NamedTuple):
    r"""Encapsulates an ordered pair of synaptic pathways tested for crosstalk.

"""
    path0: typing.Union[SynapticPathway, str, int]
    path1: typing.Union[SynapticPathway, str, int]

@dataclasses.dataclass
class SweepPathCommands:
    r"""Encapsulates the DAC and DIG commands sent to the pathway during a given sweep.
    """
    pathway: SynapticPathway
    abfEpochs: dict = dataclasses.field(default_factory = dict)
    triggers: typing.Sequence[TriggerEvent] = dataclasses.field(default_factory = list)

class PathwaysStimulationLayout():
    r"""Represents the sequence of pathway stimulations per sweep, as defined in a protocol.

    .. |nbsp| unicode:: 0xA0
        :trim:

    This function helps identifying cases where an protocol is configured to |nbsp|
    digitally stimulate more than one synaptic pathway during the same sweep(s).

    This strategy is typically used to test cross-talk, or overlap, between two synaptic |nbsp|
    pathways based on short-term plasticity phenomena such as paired-pulse |nbsp|
    facilitation). cases, reporting the order in which |nbsp|
    the pathways are individually stimulated, in each sweep.


    The layout is stored as a (possibly empty) mapping key -> value, where:

        :key: index (``int``) of sweep in the protocol (0-based)

        :value: a ``list`` of tuples (X, Y, Z) with

            :X: SynapticPathway object (or name, or index)

            :Y: Dict mapping ABFEpoch number to a tuple of ABFEpoch and its role (see parseEpochs) for this pathway & sweep combination

            :Z: List of TriggerEvent objects with the time stamps for the activation of the SynapticPathway object X

            This captures the case when more than one pathway is activated during the same sweep.


    .. note::
        The fundamental difference from the ``getPathwayStimulationSequence`` function |nbsp|
    is that this function reports *which synaptic pathway* is stimulated during every |nbsp|
    protocol sweep, and *when* is that pathway stimulated, relative to the start of that sweep. |nbsp|
    In contrast, the ``getPathwayStimulationSequence`` function reports the sweep number(s) |nbsp|
    where a given ``SynapticPathway`` is stimulated, and the stimulation times within that sweep.

    Examples:
    ---------

    Example 1:
    ==========

    Consider a ``RecordingSource`` object "source" defining two SynapticPathway objects, |nbsp|
    and an ``ABFProtocol`` object "protocol" configured to deliver a pair of stimuli |nbsp|
    to each pathway, respectively via digital channels DIG 0 and DIG 1, on alternative sweeps. |nbsp|

    ::

        source = synevoke.twoPathwaysSource(0, 0, name="Two-pathways CA3-CA1 EPSCs")

    The stimulus pair is delivered at 0.26562 s since the start of the sweep, with 50 ms inter-stimulus interval) , according |nbsp|
    to the schematic below.

    .. note::
        In this example there is one epoch triggering a pathway in |nbsp|
        all sweeps, but the epochs uses a TTL train instead of a pulse.


    ::

        sweep 0 (even sweeps):

            path 0 (DIG 0)  ______|_|_________

            path 1 (DIG 1)  __________________



        sweep 1 (odd sweeps):

            path 0 (DIG 0)  __________________

            path 1 (DIG 1)  ______|_|_________


        synevoke.getPathwaysStimulationLayout(source.pathways, protocol, reportPathNames=True)

        ->

        {0: [('path0', {}, [TriggerEvent 'presynaptic' (presynaptic): EPSC0@0.26562 s, EPSC1@0.31562 s])],
        1: [('path1', {}, [TriggerEvent 'presynaptic' (presynaptic): EPSC0@0.26562 s, EPSC1@0.31562 s])]}


    Example 2:
    ==========
    The same source as in Example 1, but the protocol stimulates  the pathways |nbsp|
    according to the scheme below:


    ::

        sweep 0 (even sweeps):

            path 0 (DIG 0)  ______|___________

            path 1 (DIG 1)  ________|_________


        sweep 1 (odd sweeps):

            path 0 (DIG 0)  ________|_________

            path 1 (DIG 1)  ______|___________


    .. note::
        The postsynaptic cells still receives a pair of synaptic stimuli, but each |nbsp|
        stimulus in the pair comes via a *distinct* pathway; the *order* in which the |nbsp|
        pathways are stimulated is *different* in subsequent sweeps. Stimulus timings |nbsp|
        are as in Exmaple 1, above.

    ::

        synevoke.getPathwaysStimulationLayout(source.pathways, protocol, reportPathNames=True)

        ->

        {0: [('path0', {}, [TriggerEvent 'presynaptic' (presynaptic): ['EPSC0']@[0.2656] s]),
            ('path1', {}, [TriggerEvent 'presynaptic' (presynaptic): ['EPSC0']@[0.3156] s])],
        1: [('path1', {}, [TriggerEvent 'presynaptic' (presynaptic): ['EPSC0']@[0.2656] s]),
            ('path0', {}, [TriggerEvent 'presynaptic' (presynaptic): ['EPSC0']@[0.3156] s])]}



    """
    # NOTE: 2026-05-04 09:02:28
    # implementing dict API - put on hold for now...

    def __init__(self, source: typing.Union[RecordingSource,
                                            typing.Sequence[SynapticPathway]],
                 protocol: ElectrophysiologyProtocol, /,
                 temporalOrder: bool = True,
                 **kwargs,
                 ):
        """Constructor for PathwaysStimulationLayout.

        .. |nbsp| unicode:: 0xA0
            :trim:

        Parameters:
        -----------

        :pathways: sequence (tuple or list) of ``SynapticPathway`` objects

        :protocol: Acquisition protocol used in the experiment. Currently, only Clampex |nbsp|
            protocols (``ABFProtocol`` objects) are supported.

        :temporalOrder: When ``True`` (default), the reported pathway stimulation sequence |nbsp|
            reflects the temporal order of the pathway stimulations (see Examples, below) |nbsp|

            When ``False`` the reported pathway stimulation sequence reflects the |nbsp|
            order of the pathways in the pathways sequence (``pathways`` parameter).
        """
        # print(f"{self.__class__.__name__}.__init__: kwargs = {kwargs}")
        if isinstance(source, RecordingSource):
            assert len(source.pathways) and all(isinstance(p, SynapticPathway) for p in source.pathways), "'source' must be a RecordingSource with a non-empty sequence of SynapticPathway objects"
            self._source_ = source
            self._pathways_ = source.pathways

        elif isinstance(source, typing.Sequence):
            assert len(source) and all(isinstance(p, SynapticPathway) for p in source), "'source' must be a sequence of SynapticPathway objects"
            adc = source[0].adc
            dac = source[0].dac
            assert all(p.adc == adc for p in source[1:]), "All synaptic pathways should use the same ADC channel"
            assert all(p.dac == dac for p in source[1:]), "All synaptic pathways should use the same DAC channel"
            electrodeMode = kwargs.pop("electrodeMode", None)
            assert isinstance(electrodeMode, ElectrodeMode), f"The 'electrodeMode' keyword parameter must be specified with an ephys.ElectrodeMode enum value; got {type(electrodeMode).__name__} instead"
            name = kwargs.pop("name", None)
            assert (isinstance(name, str) and len(name.strip()) > 0), f"The 'name' keyword parameter must be specified with a non empty string; instead got {name}"

            self._pathways_ = source
            syn = tuple(map(lambda p: p.stimulus, self._pathways_))
            self._source_ = RecordingSource(name, adc, dac, syn, electrodeMode = electrodeMode)

        else:
            raise TypeError(f"'source' must be a Recording Source or a sequence of SynapticPathway objects; instead got {type(source).__name__}")

        assert isinstance(protocol, pab.ABFProtocol), f"'protocol' expected to be an ABFProtocol; instead got a  {type(protocol).__name__}"
        self._protocol_ = protocol
        self._layout_ = self._parseLayout_(temporalOrder)
        # self._layout_ = self._parseLayout_(pathways, protocol, temporalOrder)

    def _parseLayout_(self, temporalOrder: bool = True) -> dict:
        stimulationLayout = dict()

        stimByPaths = tuple(map(lambda p: (p, getPathwayStimulationSequence(p, self._protocol_)), self._pathways_))

        for sweep in range(self._protocol_.nSweeps):
            for path, pStim in stimByPaths:
                if sweep in pStim:
                    triggers = pStim[sweep]
                    epochsDict = parseEpochs(path, self._protocol_, sweep)

                    sPC = SweepPathCommands(path, epochsDict, triggers)

                    if sweep in stimulationLayout:
                        stimulationLayout[sweep].append(sPC)

                    else:
                        stimulationLayout[sweep] = [sPC]

        if temporalOrder:
            for sweep in stimulationLayout:
                pps = sorted(stimulationLayout[sweep],
                            key = lambda sPC: min(list(map(lambda tr: tr.times[0], sPC.triggers))))

                stimulationLayout[sweep] = pps

        return stimulationLayout

    @property
    def protocol(self):
        r"""The ABFProtocol used to generate this PathwaysStimulationLayout instance"""
        return self._protocol_

    @property
    def pathways(self):
        r"""The SynapticPathways in this instrance of PathwaysStimulationLayout"""
        return self._pathways_

    @property
    def source(self) -> RecordingSource:
        return self._source_

    @property
    def electrodeMode(self) -> ephys.ElectrodeMode:
        return self._source_.electrodeMode

    @property
    def sweeps(self) -> dict[int, list[SweepPathCommands]]:
        r"""Underlying dictionary holding the layout.
        .. |nbsp| unicode:: 0xA0
            :trim:

        This is a **read-only** mapping of sweep indexes (``int``) to sequences of |nbsp|
        SweepPathCommands objects, which is populated by "parsing" an ABFProtocol.
        """
        return self._layout_

    def getSweepsForPathway(self, pathway:SynapticPathway
                            ) -> typing.Optional[int | tuple[int]]:
        result = list()
        for sweep, sPCs in self.sweeps.items():
            if len(sPCs) == 0:
                continue

            for sPC in sPCs:
                if sPC.pathway == pathway:
                    result.append(sweep)

        if len(result) > 1:
            return tuple(result)

        elif len(result) == 1:
            return result[0]

    def _getSweepEpochsWithRoleForPathway_(self, pathway: SynapticPathway, sweep: int,
                            role: pab.ABFEpochRole,
                            ensureUnique: bool = True,
                            asNeoEpoch: bool = False) -> typing.Optional[
                                typing.Union[pab.ABFEpoch,
                                             typing.List[pab.ABFEpoch]
                                             ]
                                ]:
        assert isinstance(pathway, SynapticPathway), f"'pathway' expected to be an SynapticPathway; instead, got a {type(pathway).__name__}"
        assert isinstance(role, pab.ABFEpochRole), f"'role' expected to be an ABFEpochRole; instead, got a {type(role).__name__}"

        # sPC is a sweep/pathway combination
        sweepSPCs = list(filter(lambda sPC: sPC.pathway == pathway, self.sweeps[sweep]))

        if len(sweepSPCs) == 0:
            return

        if len(sweepSPCs) > 1:
            scipywarn(f"Pathway {pathway.name} has multiple SweepPathCommands entries for sweep {sweep}; will use the first one!")

        sPC = sweepSPCs[0]

        if len(sPC.abfEpochs) == 0:
            return

        # -> list of lists; inner lists are pairs of epoch, epoch role!
        epochs_roles = list(filter(lambda e: e[1] == role, sPC.abfEpochs.values()))

        if len(epochs_roles) == 0:
            return

        if len(epochs_roles) > 1:
            if ensureUnique:
                scipywarn(f"There are {len(epochs_roles)} membrane test epochs for pathway {pathway.name} in sweep {sweep}; will use the first one!")
                e = epochs_roles[0][0]
                return self._protocol_.getNeoEpoch(epoch=e, dac=pathway.dac, sweep=sweep) if asNeoEpoch else e
            else:
                return list(map(lambda e: self._protocol_.getNeoEpoch(epoch=e[0], dac=pathway.dac, sweep=sweep) if asNeoEpoch else e[0], epochs_roles))

        else:
            e = epochs_roles[0][0]
            return self._protocol_.getNeoEpoch(epoch=e, dac=pathway.dac, sweep=sweep) if asNeoEpoch else e

    def getEpochsWithRole(self, pathway:SynapticPathway, role: pab.ABFEpochRole,
                         ensureUnique: bool = False,
                         sweep:typing.Optional[int] = None,
                         asNeoEpoch: bool = False) -> typing.Optional[
                                                typing.Union[
                                                    pab.ABFEpoch,
                                                    neo.Epoch,
                                                    list[pab.ABFEpoch],
                                                    list[neo.Epoch],
                                                    dict[int, pab.ABFEpoch],
                                                    dict[int, neo.Epoch],
                                                    dict[int, list[neo.Epoch]]]
                                                ]:
        r"""Queries the epoch(s) fulfilling a specific role.

        .. |nbsp| unicode:: 0xA0
        :trim:

        Searches and returns the epochs that fulfil a specific role (see ABFEpochRole) |nbsp|
        on a given pathway, during a given sweep.


        Parameters:
        -----------
        :pathway: Must exist in the stimulation layout

        :role: Specific role for the Epoch. See ABFEpochRole enumeration for details.

        :ensureUnique: When True, warns if the stimulation layout for a specific pathway & sweep
            combination has more than one ABF epoch with the specified role, and returns
            the first epoch that was found. When False (the default) the method returns
            a sequence of epochs or just an epoch, if there is only one fulfilling the role.

        :sweep: Optional, default is None. When None, the method will query the stimulus
            layout for all the sweeps where the specified pathway is recorded. When an int,
            the query will be restricted to the combination of pathway and the specified sweep,
            if it exists in the stimulus layout.

        :asNeoEpoch: When True, the epochs will be returned as neo.Epoch objects with timings as output during the actual recording.
                This is useful for further analysis of recorded data.

                Optional, default is False.

        Returns:
        --------

        .. note::
            Below, an 'epoch' is either an pyabfbridge.ABFEpoch object or a neo.Epoch object, depending on the value of the 'asNeoEpoch' parameter.

        * When sweep is an integer (index of sweep in the protocol), then for the combination of 'pathway' and 'sweep':
            * if 'ensureUnique' is True, returns the single epoch fulfilling 'role', or None if no such epoch exists.

            * if 'ensureUnique' is False, returns a list of epochs fulfilling this role, or None if no such epoch exists

        * When 'sweep' is None, then for all the protocol sweeps where 'pathway' is recorded, returns a dictionary that

                maps sweep index to an epoch or list of epochs fulfiling the 'role', for the sweep where such epochs are found

                The dictionary may be empty.

        If 'pathway' is not recorded in the given sweep (or in any of the protocol's sweeps) returns None.

        """
        sweeps = self.getSweepsForPathway(pathway)

        if isinstance(sweeps, int):
            sweeps = [sweeps]

        elif not isinstance(sweeps, typing.Sequence) or len(sweeps) == 0 or not all(isinstance(s, int) for s in sweeps):
            return

        result = dict()

        if isinstance(sweep, int):
            if sweep not in sweeps:
                return

            return self._getSweepEpochsWithRoleForPathway_(pathway, sweep, role, ensureUnique, asNeoEpoch)

        for sweep in sweeps:
            if sweep not in self.sweeps:
                continue

            epochs = self._getSweepEpochsWithRoleForPathway_(pathway, sweep, role, ensureUnique, asNeoEpoch)
            if isinstance(epochs, (pab.ABFEpoch, neo.Epoch)):
                result[sweep] = epochs
            elif isinstance(epochs, list) and len(epochs) and all(isinstance(e, (pab.ABFEpoch, neo.Epoch)) for e in epochs):
                result[sweep] = epochs

        return result


    def getMembraneTestEpoch(self, pathway:SynapticPathway,
                             sweep: typing.Optional[int] = None,
                             asNeoEpoch: bool = False) -> typing.Optional[
                                            typing.Union[pab.ABFEpoch,
                                                        neo.Epoch,
                                                        dict[int, pab.ABFEpoch],
                                                        dict[int, neo.Epoch]]
                                            ]:
        r"""Returns the ABF epochs used for membrane test in a pathway during a given sweep.

        .. |nbsp| unicode:: 0xA0
        :trim:

        Parameters:
        -----------

        :pathway: The pathway where membrane test epochs are to be queried.

        :sweep: Index of the sweep (0-based) or None (default).

        :asNeoEpoch: When True, all returned epochs are neo.Epoch objects; otherwise, they are pyabfbridge.ABFEpoch objects.

        Returns:
        --------
        When ``sweep`` is None (default) returns a dictionary mapping sweep index to a possibly empty list of epochs

        When ``sweep`` is specified, returns the epoch used for membrane test or None if such epoch is not found.

        .. note::
                Membrane test epochs should be unique in any given sweep

        """
        return self.getEpochsWithRole(pathway, ABFEpochRole.MembraneTestRole,
                                     True, sweep, asNeoEpoch)


    def getBaselineEpoch(self, pathway: SynapticPathway,
                        sweep: typing.Optional[int] = None,
                        asNeoEpoch: bool = False) -> typing.Optional[
                                            typing.Union[pab.ABFEpoch,
                                                        neo.Epoch,
                                                        dict[int, pab.ABFEpoch],
                                                        dict[int, neo.Epoch]]
                                            ]:
        r"""Returns the epoch used for measuring the signal baseline.

        .. |nbsp| unicode:: 0xA0
        :trim:

        See self.getMembraneTestEpoch for details about parameters and return types.

        .. note::
            There shoud be only one such epoch in any given sweep.

            The notion of signal 'baseline' refers to the region of the signal |nbsp|
        *before* any challenge applied to the recording source (membrane test, |nbsp|
        stimulation, etc).

        """
        return self.getEpochsWithRole(pathway, ABFEpochRole.BaselineRole,
                                     True, sweep, asNeoEpoch)

    def getStimulationEpochs(self, pathway: SynapticPathway,
                             sweep: typing.Optional[int] = None,
                             asNeoEpoch: bool = False) -> typing.Optional[
                                                typing.Union[
                                                    pab.ABFEpoch,
                                                    neo.Epoch,
                                                    list[pab.ABFEpoch],
                                                    list[neo.Epoch],
                                                    dict[int, pab.ABFEpoch],
                                                    dict[int, neo.Epoch],
                                                    dict[int, list[neo.Epoch]]]
                                                ]:
        r"""Returns the epoch(s) where the pathway is stimulated during the given sweep.

        .. |nbsp| unicode:: 0xA0
        :trim:

        See self.getMembraneTestEpoch for details about parameters.

        .. note::
            Unlike for self.getMembraneTestEpoch or self.getBaselineEpoch, there can be more than one stimulation epoch in any given sweep.

        """
        return self.getEpochsWithRole(pathway, ABFEpochRole.StimulusRole,
                                      False, sweep, asNeoEpoch)

    def getCrossTalkLayout(self) -> dict:
        r"""Shows the layout of sweeps & pathways for cross-talk tests.

        .. |nbsp| unicode:: 0xA0
            :trim:

            Returns a mapping of sweep index (int) to a PathwaysCrossTalk named tuple. |nbsp|
            The mapping may be empty if the protocol does not test for pathway cross-talk.

            """
        return dict(filter(lambda i: self.isXTalkLayout(i[1]), self.sweeps.items()))

    @staticmethod
    def isXTalkLayout(l) -> bool:
        return (isinstance(l, (tuple, list, collections.deque))
                and len(l) == 2
                and all(isinstance(l_, SweepPathCommands) for l_ in l)
                and l[0].pathway != l[1].pathway
                )

@dataclass
class SynapticPathway:
    r"""Logical association of a SynapticStimulusChannel with a recording configuration.

    Also specifies the "type" of the SynapticPathway, which represents the role
    of the SynapticPathway in an experiment.

    """
    name: str = "pathway"
    adc: int = 0 # physical index of the ADC channel used in recording this pathway
    # adc: int|None = None # physical index of the ADC channel used in recording this pathway
    dac: int = 0 # physical index of the DAC channel used in recording this pathway
    # dac: int|None = None # physical index of the DAC channel used in recording this pathway
    stimulus: SynapticStimulusChannel = dataclasses.field(default_factory = SynapticStimulusChannel)
    # stimulus: SynapticStimulusChannelList = dataclasses.field(default_factory = SynapticStimulusChannelList)

    # NOTE: 2024-10-16 11:57:17
    # 'clampMode' is not needed, in a SynapticPathway, which can be recorded in
    # either clamp mode, and the clamp mode can change during a session (i.e.,
    # a sequence of recording trials).
    #
    # On the other hand it makes sense to define an electrode mode, as it cannot
    # change during the session - once impaled, it would be tricky to also patch
    # the cell, and vice-versa (although re-patching the cells has been reported,
    # e.g. see Lamsa et al, Science 315:1262, 2007, for the purpose of this
    # software one can consider a repatched cell as the same source, with same
    # electrode mode, but undergoing different episodes).
    #
    # Therefore:
    # NOTE: 2024-10-16 13:36:07
    # add clampMode to RecordingEpisode!
    electrode: dataclasses.InitVar[typing.Union[ephys.ElectrodeMode, int, str]] = ephys.ElectrodeMode.Null

    pathType: dataclasses.InitVar[typing.Union[SynapticPathwayType, int, str]] = SynapticPathwayType.Null

    schedule: RecordingSchedule = dataclasses.field(default_factory = RecordingSchedule)

    # CAUTION 2024-10-17 22:31:14 FIXME
    # these measurements MUST be mapped to the episode boundaries, so that one
    # can easily access the measurement values during a particular episode or
    # across several episodes of the schedule!
    # measurements: typing.Mapping[str, typing.Union[neo.IrregularlySampledSignal, IrregularlySampledDataSignal]] = dataclasses.field(default_factory = dict)

    # NOTE: 2026-05-13 14:52:36
    # using DeferredSignalMeasure objects (but others, too):
    # map the name of the measure (as it would appear in a results table) to
    # a sequence of measures (DeferredSignalMeasure, functions, etc): each of these
    # are to be executed in the order given in the sequence
    #
    measurements: dict[str, list] = dataclasses.field(default_factory = dict)
    # source: RecordingSource = dataclasses.field(default_factory = lambda: RecordingSource())

    def __post_init__(self, electrode:typing.Union[ephys.ElectrodeMode, int, str] = ephys.ElectrodeMode.Null,
                      pathType:typing.Union[SynapticPathwayType, int, str] = SynapticPathwayType.Null):

        if isinstance(electrode, (int, str)):
            if electrode not in ephys.ElectrodeMode:
                raise ValueError(f"Invalid electrode mode {electrode}")

            electrode = ephys.ElectrodeMode.type(electrode)

        if not isinstance(electrode, ephys.ElectrodeMode):
            raise TypeError(f"Invalid electrode mode {electrode}")

        self._electrodeMode_ = electrode

        if isinstance(pathType, (int, str)):
            if pathType not in SynapticPathwayType:
                raise ValueError(f"Invalid synaptic pathway type {pathType}")

            pathType = SynapticPathwayType.type(pathType)

        if not isinstance(pathType, SynapticPathwayType):
            raise TypeError(f"Invalid synaptic pathway type {pathType}")

        self._pathwayType_ = pathType
        self.pathType = self._pathwayType_

    @property
    def electrodeMode(self) -> ephys.ElectrodeMode:
        return self._electrodeMode_

    @electrodeMode.setter
    def electrodeMode(self, val:typing.Union[int, str, ephys.ElectrodeMode]):
        if isinstance(val, (int, str)):
            if val not in ephys.ElectrodeMode:
                raise ValueError(f"Invalid electrode mode {val}")

            val = ephys.ElectrodeMode.type(val)

        if not isinstance(val, ephys.ElectrodeMode):
            raise TypeError(f"Invalid electrode mode {val}")

        self._electrodeMode_ = val

    @property
    def pathwayType(self) -> SynapticPathwayType:
        return self._pathwayType_

    @pathwayType.setter
    def pathwayType(self, val:typing.Union[SynapticPathwayType, int, str]):
        if isinstance(val, (int, str)):
            if val not in SynapticPathwayType:
                raise ValueError(f"Invalid syaptic pathway type {val}")

            val = SynapticPathwayType.type(val)

        if not isinstance(val, SynapticPathwayType):
            raise TypeError(f"Invalid synaptic pathway type {val}")

        self._pathwayType_ = val
        self.pathType = self._pathwayType_

    def __repr__(self) -> str:
        import dataclasses
        all_attr_names = list(f.name for f in dataclasses.fields(self.__class__)) + [x[0] for x in inspect.getmembers_static(self, lambda x: isinstance(x, property))]
        ret = [f"{self.__class__.__name__}"]
        ret += ["("]

        ret += ", ".join([f"{a}={getattr(self,a).name if a in ('electrodeMode', 'pathwayType') else getattr(self, a)}" for a in all_attr_names])
        ret += [")"]

        return "".join(ret)

    def __eq__(self, other) -> bool:
        from dataclasses import fields
        ret = type(self) == type(other)

        if not ret:
            return ret

        ret &= all(getattr(self, f.name) == getattr(other, f.name) for f in fields(type(self)) if f.name != "source")

        if ret:
            ret &= self.pathwayType == other.pathwayType

        if ret:
            ret &= self.electrodeMode == other.electrodeMode

        return ret

    def toHDF5(self, group, name, oname, compression, chunks, track_order,
                       entity_cache) -> h5py.Group:

        from iolib import h5io
        # print(f"{self.__class__.__name__}.toHDF5: {self.name}")
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        if isinstance(cached_entity, h5py.Dataset):
            group[target_name] = cached_entity
            return cached_entity

        attrs = {"name": self.name,
                 "adc": self.adc,
                 "dac":self.dac,
                 "pathwayType": self.pathwayType,
                 "electrodeMode": self.electrodeMode,
                 }

        objattrs = h5io.makeAttrDict(**attrs)
        obj_attrs.update(objattrs)

        if isinstance(name, str) and len(name.strip()):
            target_name = name

        entity = group.create_group(target_name, track_order=track_order)
        entity.attrs.update(obj_attrs)

        # h5io.toHDF5(self.source, entity, name="source", oname="source",
        #                     compression=compression, chunks=chunks,
        #                     track_order=track_order,
        #                     entity_cache=entity_cache)

        h5io.toHDF5(self.stimulus, entity, name="stimulus", oname="stimulus",
                            compression=compression, chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)

        h5io.toHDF5(self.schedule, entity, name="schedule", oname="schedule",
                            compression=compression, chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)

        h5io.toHDF5(self.measurements, entity, name="measurements", oname="measurements",
                            compression=compression, chunks=chunks,
                            track_order=track_order,
                            entity_cache=entity_cache)

        h5io.storeEntityInCache(entity_cache, self, entity)

        return entity

    @classmethod
    def fromHDF5(cls, entity:h5py.Group,
                             attrs:typing.Optional[dict]=None, cache:dict = {}):

        from iolib import h5io
        if entity in cache:
            return cache[entity]

        attrs = h5io.attrs2dict(entity.attrs)
        name = attrs["name"]
        pathwayType = attrs["pathwayType"]
        electrodeMode = attrs["electrodeMode"]
        adc = attrs["adc"]
        dac = attrs["dac"]
        schedule = h5io.fromHDF5(entity["schedule"], cache=cache)
        stimulus = h5io.fromHDF5(entity["stimulus"], cache=cache)
        # source = h5io.fromHDF5(entity["source"], cache=cache)
        measurements = h5io.fromHDF5(entity["measurements"], cache=cache)

        return cls(name=name, adc=adc, dac=dac, pathType=pathwayType,
                   stimulus=stimulus, electrode=electrodeMode,
                   schedule=schedule, measurements=measurements)#, source=source)

    @classmethod
    def fromDict(cls, **kwargs):
        r"""Constructs an instance of this class using 'kwargs' keys that match the class fields.
        Keys in kwargs that are NOT valid field names for this class are silently
        ignored.
        """
        field_names = tuple(f.name for f in dataclasses.fields(cls))

        initkwargs = dict((i, kwargs[i]) for i in field_names if i in kwargs)

        return cls(**initkwargs)


class SynapticPathwayList(NeoObjectList):
    allowed_contents  = (SynapticPathway, )

    def __init__(self, *items, name:typing.Optional[str] = None,
                 parent: object = None):

        self.name = "" if not isinstance(name, str) else name
        self._items = list()

        if len(items):
            if len(items) == 1 and isinstance(items[0], typing.Sequence):
                items = items[0]

            if any(
                not isinstance(i, self.allowed_contents)
                or not any(type(i).__name__ in n for n in list(map(lambda t: t.__name__, self.allowed_contents)))
                for i in items):
                raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(item).__name__}")

            self._items = list(items)

        if parent is not None and ScipyenDataclass not in inspect.getmro(type(parent)):
            raise TypeError(f"Parent must be a ScipyenDataclass or None; got {type(parent).__name__} instead")

        self._parent = parent

    @property
    def parent(self) -> ScipyenDataclass | None:
        return self._parent

    def __iter__(self):
        """Implement iter(self)"""
        for item in self._items:
            yield item

    def __delitem__(self, i: int) -> None:
        if len(self._items) == 0:
            return

        if i < len(self._items) and i >= -len(self._items):
            del(self._items[i])
        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __getitem__(self, i: int) -> SynapticPathway | None:
        """x.__getitem__(y) <==> x[y]"""
        if len(self._items) == 0:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

        if i < len(self._items) and i >= -len(self._items):
            return self._items[i]

        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __setitem__(self, i: int, value: SynapticPathway):
        if not isinstance(value, self.allowed_contents):
            raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(value).__name__}")

        if len(self._items) == 0:
            raise ValueError(f"Index {i} out of range for {len(self._items)} items")

        if i < len(self._items) and i >= -len(self._items):
            self._items[i] = value

        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __str__(self):
        """Return str(self)"""
        return f"<{self.__class__.__name__}> with {len(self._items)} {self.allowed_contents[0].__name__} objects"

    def __repr__(self):
        header = f"<{self.__class__.__name__}>"
        if isinstance(self.name, str) and len(self.name.strip()):
            header += f" '{self.name}'"

        s = [f"{header} with {len(self._items)} {self.allowed_contents[0].__name__} objects",
            ]

        if len(self._items):
            s[0]+= ":"
            s.extend(list(map(lambda p: f"{p[0]}: {p[1]}", enumerate(self._items))))

        return "\n".join(s)

    def __len__(self):
        """Return len(self)"""
        return len(self._items)

    def _add_items(self, other: typing.Self, in_place=False) -> typing.Self:
        self._items = self._items + other._items
        return self

    def __add__(self, other):
        """Return self + other"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return ret._add_items(other)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret

        else:
            return ret

    def __iadd__(self, other):
        """Return self"""
        if isinstance(other, self.__class__):
            return self._add_items(other, in_place=True)

        elif isinstance(other, self.allowed_contents):
            self._items.append(other)
            return self

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            self._items.extend(list(other))
            return self

        else:
            return self

    def __radd__(self, other):
        """Return other + self"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return other._add_items(ret)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret
        else:
            return ret

    def append(self, obj):
        """
        Appends a SynapticStimulusChannel

        Parameters
        ----------
        obj: SynapticStimulusChannel

        """
        if not isinstance(obj, self.allowed_contents):
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")
        self._items.append(obj)

    def extend(self, iterable):
        """Extends with additional SynapticStimulusChannel objects from an iterable

        Parameters
        ----------
        iterable: iterable[SynapticStimulusChannel]

        """
        if all (isinstance(o, self.allowed_contents) for o in iterable):
            self._items.extend(iterable)
        else:
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")

def infer_schedule(*args, name:typing.Optional[str] = None) -> RecordingSchedule:
    r"""WARNING: Based on the naming of the trials (neo.Block objects).

    The names of the blocks must follow the format: aaa_<bbb_>*<xxxx>

    where a, b are any word character (a-zA-Z0-9_) and x is any digit.

    These names must be the values of the `name` attribute of the neo.Block
    objects (and it is useful if these sme  names would also be the symbols bound
    to these objects, in the workspace).

    Usually, this is achieved by applying the naming format AT ACQUISITION (e.g.,
    in Clampex) so that the naming of the stored files is taken up by the neo
    Block(s) created upon reading the files (and also assigned to tyhe workspace
    symbol).

    The `aaa_<bbb_>*<xxxx>` format folows the rule in Clampex (hence operating
    with ABF files) but should be easily implemented in other aquisition software
    such as Signal 5.

    Returns a RecordingSchedule.



    """
    if len(args) == 0:
        return

    if isinstance(args, (tuple, list, collections.deque)) and len(args) == 1:
        args = args[0]

    if not all(isinstance(v, neo.Block) for v in args):
        raise TypeError("Expecting a sequence of neo.Block objects")

    trials_seq , ordered_trials = trials_sequence_info(*args, return_sorted=True)
    # this below: tuple (running index of trial, trial basename, trial suffix index)
    # unique based on trial basename
    episode_names_ndx = unique(list(map(lambda x: (x[0], *(strutils.get_int_sfx(x[1]))), enumerate(trials_seq.name))),
                           key = lambda v: v[1])

    trials_ndx = list(map(lambda n: list(trials_seq.index[list(map(lambda x: n[1] in x, trials_seq.name))]), episode_names_ndx))

    episodes = list(map(lambda x: RecordingEpisode(name=x[0][1], blocks = [ordered_trials[k] for k in x[1]]),
                        zip(episode_names_ndx, trials_ndx)))

    schedule = RecordingSchedule(episodes=episodes)

    return schedule
    # return episodes

def parseEpochs(pathway: SynapticPathway, protocol: pab.ABFProtocol,
                sweep: int = 0) -> dict:
    r"""Suggests roles for the ABF Epochs 'active' on a given pathway during a specified sweep.

    .. |nbsp| unicode:: 0xA0
    :trim:

    Returns:
    ========
    a dict, mapping keys: int ↦ tuple (epoch: ABFEpoch, proposed_role: str)

    """
    # NOTE: 2026-05-04 08:55:37 DO NOT DELETE
    # this function, while at module level, is used by PathwaysStimulationLayout

    # TODO 2026-04-27 21:53:38
    # to return {epoch_number: (epoch, ABFEpochRole)}
    hoDACActive = protocol.activeDACChannel not in (0,1)
    isMainDAC = pathway.dac == protocol.activeDAC.physicalIndex

    dac = protocol.getDAC(pathway.dac)

    digTriggerEpochs = list()

    suggestFirst = True # normally I'd choose the first suitable epoch, unless
                        # all suitable epochs come AFTER some other perturbance
                        # (e.g., command waveforms or DIG TTL pulses), in which
                        # case the last one should be selected, giving hopefully
                        # enough time for the recording to settle

    if pathway.stimulus.dig:
        digTriggerEpochs = protocol.getTTLEmittingEpochsForDAC(dac,
                                                    pathway.stimulus.channel,
                                                    sweep)

    isMTEpoch = lambda epoch: (epoch.number not in digTriggerEpochs
                               and epoch.firstLevel != 0
                               and epoch.deltaLevel == 0)

    isFlatEpoch = lambda epoch: (epoch.number not in digTriggerEpochs
                                 # and epoch.firstLevel == 0
                                 and protocol.getEpochLevel(epoch, dac, sweep) == 0
                                 and epoch.deltaLevel == 0) # and epoch.deltaDuration == 0

    classifyEpoch = lambda epoch: (ABFEpochRole.MembraneTestRole if isMTEpoch(epoch) else
                                   ABFEpochRole.BaselineRole if isFlatEpoch(epoch) else
                                   ABFEpochRole.StimulusRole if epoch.number in digTriggerEpochs
                                   else ABFEpochRole.UnspecifiedRole)

    # NOTE: 2026-05-01 21:57:34
    # use a list instead of tuple so that Role can be changed in GUI
    epochsDict = dict(map(lambda e: (e.number, [e, classifyEpoch(e)]), dac.epochs))
    # epochsDict = dict(map(lambda e: (e.number, (e, classifyEpoch(e))), dac.epochs))

    flatEpochs = list(filter(isFlatEpoch, dac.epochs))

    if len(flatEpochs):
        if len(digTriggerEpochs):
            triggerStarts, triggerStops = tuple(
                                                zip(
                                                    *tuple(
                                                            map(
                                                                lambda e: protocol.getEpochStartStop(e, dac, sweep),
                                                                digTriggerEpochs
                                                                )
                                                        )
                                                    )
                                                )
            firstTriggerStart = min(triggerStarts)

            # by definition, ABF epochs are non-overlapping so I'm OK going by
            # epoch start times only

            # these would be flat epochs PRECEDING the earliest DIG TTL epoch
            maybeSuitable = list(filter(lambda e: protocol.getEpochStart(e, dac, sweep) < firstTriggerStart,
                                        flatEpochs))

            if len(maybeSuitable) == 0:
                # no flat epoch BEFORE the first DIG TTL one
                # => pick up one that comes later enough after the last DIG TTL epoch
                # in order to allow for the recording to settle (if there is any such epoch)
                lastTriggerStop = max(triggerStops)

                # these would be flat epochs SUCCEEDING the latest DIG TTL epoch
                maybeSuitable = list(filter(lambda e: protocol.getEpochStartStop(e, dac, sweep)[1] > lastTriggerStop,
                                            flatEpochs))

                suggestFirst = False # I'd want the very last of the above

            if len(maybeSuitable):
                contig = np.ediff1d(list(map(lambda e: e.number, maybeSuitable)),
                                    to_begin=0)

                ndx = np.where(contig > 1)[0]

                if ndx.size == 0:
                    # all are contiguous
                    dcEpoch = maybeSuitable[0] if suggestFirst else maybeSuitable[-1]

                else:
                    if ndx.size > 1:
                        ndx = int(ndx.min()) - 1 if suggestFirst else int(ndx.max())
                    else :
                        ndx = int(ndx[0]) - 1

                    dcEpoch = maybeSuitable[ndx]

                for eNumber, (epoch, epochRole) in epochsDict.items():
                    if epochRole == ABFEpochRole.BaselineRole and epoch is not dcEpoch:
                        epochsDict[eNumber][1] = ABFEpochRole.UnspecifiedRole
                        # epochsDict[eNumber] = (epoch, ABFEpochRole.UnspecifiedRole)

    return epochsDict

def getPathwayStimulationSequence(pathway: SynapticPathway,
                         protocol: pab.ABFProtocol,
                         concatenateEvents: bool = True) -> dict | None:
    r"""Outputs the sequence of synaptic stimuli (digital TTLs) a synaptic pathway.

.. |nbsp| unicode:: 0xA0
    :trim:

Identifies the sweeps where a protocol is configured to trigger synaptic stimuli |nbsp|
for a given SynapticPathway ('pathway') through TTL pulses or trains via digital |nbsp|
channels, and the timings of these stimuli, relative to the start of the sweep.

Parameters:
-----------
    :pathway: The synaptic pathway stimulated in the protocol

    :protocol: The acquisition protocol used in the trial. Currently, only |nbsp|
        Clampex protocols (core.pyabfbridge.ABFProtocol) are supported.

    :concatenateEvents: When ``True`` (default) and the pathway is stimulated on |nbsp|
        distinct acquisition epochs in the same sweep, the TriggerEvents from these
        epochs will be concatenated.


Returns:
--------
    A (possibly empty) mapping of key -> value, where:

    :key: (``int``) is the index of the sweep where the protocol triggers synaptic |nbsp|
        stimuli on the specified pathway.

        Sweeps during which the given pathway is **not** stimulated are excluded.

    :value: ``list`` of ``TriggerEvent`` objects with type ``TriggerEventType.presynaptic`` |nbsp|
        containing the timings of the synaptic stimuli  relative to the start of the sweep.

        For Clampex protocols, where a sweep is divided in a number of "epochs" |nbsp|
        (Scipyen's ``ABFEpoch`` objects) the function will generate a ``presynaptic`` |nbsp|
        ``TriggerEvent`` for each epoch that was configured, in the protocol, to |nbsp|
        emit synaptic stimuli.

        If needed, these ``TriggerEvent`` objects can be concatenated post-hoc |nbsp|
        to create a single ``TriggerEvent`` object of the same ``TriggerEventType``.


.. note::
    Only stimuli sent via digital channels are supported at the moment.


"""
    # NOTE: 2026-05-04 08:58:36 DO NOT DELETE
    # this function, while at module level, is used by PathwaysStimulationLayout

    assert pathway.adc in tuple(map(lambda d: d.physicalIndex, protocol.ADCs)), f"The pathway's ADC index not {pathway.adc} used in this protocol"
    assert pathway.dac in tuple(map(lambda d: d.physicalIndex, protocol.DACs)), f"The pathway's DAC index not {pathway.dac} used in this protocol"
    assert protocol.acquisitionMode == pab.ABFAcquisitionMode.episodic_stimulation, f"Expecting a protocol with episodic stimulation acquisition mode; isntead got ({protocol.acquisitionMode})"

    clampMode = protocol.getClampMode(pathway.adc, pathway.dac)

    # NOTE: 2026-04-21 22:14:31 We need to find out:
    # • which digital stimulus pattern is used (main or alternate)
    # • which epochs emit DIG output that stimulates the pathway

    digEpochs = protocol.epochsWithDigitalOutput

    triggerLabel = "EPSC" if clampMode == ephys.ClampMode.VoltageClamp else "EPSP" if clampMode == ephys.ClampMode.CurrentClamp else "fEPSP"

    hoDACActive = protocol.activeDACChannel not in (0,1)

    isMainDAC = pathway.dac == protocol.activeDAC.physicalIndex

    stimulation_sequence = dict() # mapping of sweep_index ↦ list of epoch_number(s)

    if pathway.stimulus.dig:
        protocolSEDs = protocol.getActiveDigitalChannels()

        for sed in protocolSEDs:
            sweep = sed["sweep"]
            wantsAltOutput = sweep % 2 > 0
            if protocol.alternateDigitalOutputsEnabled:
                # we want the pattern ACTUALLY being output, NOT the one defined in the DAC tab
                dp_variant = "alternate" if wantsAltOutput else "main"
            else:
                dp_variant = "main"

            for epoch, dp in sed["epochs"].items():
                digDACs = protocol.getDACsForEpoch(epoch)
                if len(digDACs) > 0 and pathway.dac in digDACs and pathway.stimulus.channel in dp[dp_variant]:
                    if hoDACActive:
                        if pathway.dac == 1 and wantsAltOutput:
                            myDac = protocol.getDAC(1)

                        elif pathway.dac == 0 and not wantsAltOutput:
                            myDac = protocol.getDAC(0)

                    else:
                        if pathway.dac == protocol.activeDACChannel:
                            mainDacNdx = digDACs.index(protocol.activeDACChannel)
                            if mainDacNdx > 0:
                                altDacNdx = mainDacNdx - 1
                            else:
                                altDacNdx = mainDacNdx + 1

                            if altDacNdx < len(digDACs):
                                altDac = protocol.getDAC(digDACs[altDacNdx])

                        myDac = altDac if wantsAltOutput else protocol.activeDAC

                    triggers = protocol.getEpochDigitalTriggers(epoch, sweep,
                                                                myDac,
                                                                pathway.stimulus.channel,
                                                                TriggerEventType.presynaptic,
                                                                label=triggerLabel,
                                                                enableEmptyEvent=False)

                    if isinstance(triggers, TriggerEvent):
                        triggers = [triggers]

                    elif not isinstance(triggers, typing.Sequence) or not all(isinstance(t, TriggerEvent) for t in triggers):
                        triggers = list()

                    if len(triggers): # skip empty triggers list
                        if concatenateEvents and len(triggers) > 1:
                            t = neoutils.concatenate_events(*triggers)
                            t.labels = triggerLabel

                        if sweep not in stimulation_sequence:
                            stimulation_sequence[sweep] = triggers
                        else:
                            stimulation_sequence[sweep].extend(triggers)

    else:
        # stimuli sent via DAC-emulated TTLs # TODO 2026-04-23 22:47:56
        pass

    return stimulation_sequence
