import configparser, itertools, functools, inspect, warnings
import enum, collections, numbers, types, typing
from traitlets import Bunch
import numpy as np
import quantities as pq
import neo
import vigra
import h5py
import pandas as pd


from core import (prog, traitcontainers, strutils, neoutils, models,)
from core.prog import (safeWrapper, AttributeAdapter)
from core.basescipyen import BaseScipyenData
from core.traitcontainers import DataBag
from core import quantities as cq
from core.quantities import(arbitrary_unit, 
                            pixel_unit, 
                            channel_unit,
                            space_frequency_unit,
                            angle_frequency_unit,day_in_vitro,
                            week_in_vitro, postnatal_day, postnatal_month,
                            embryonic_day, embryonic_week, embryonic_month,
                            unit_quantity_from_name_or_symbol,
                            check_time_units)

from core.utilities import (get_index_for_seq, sp_set_loc )

from core.datatypes import (UnitTypes, GENOTYPES, )

from core.datasignal import (DataSignal, IrregularlySampledDataSignal,)

from core.datazone import DataZone

from core.multiframeindex import (FrameIndexLookup, )
#from core.multiframeindex import (MultiFrameIndex, FrameIndexLookup)

from core.triggerevent import (DataMark, TriggerEvent, TriggerEventType,)

from core.triggerprotocols import (TriggerProtocol,
                                   embed_trigger_protocol, 
                                   embed_trigger_event,
                                   parse_trigger_protocols,
                                   remove_trigger_protocol,)

from core.neoutils import (clear_events, get_index_of_named_signal, is_empty,)
#from core.neoutils import (clear_events, get_index_of_named_signal, neo_copy, is_empty,)
from ephys.ephys import (average_segments, )

from imaging.vigrautils import (proposeLayout, concatenateImages, croppedView, 
                                imageIndexTuple, resampleImage, resampleImageAxis,
                                removeSlice, padToShape, padAxis,)# nFrames)

from imaging.axiscalibration import (AxesCalibration, 
                                     AxisCalibrationData,
                                     ChannelCalibrationData)

from gui import pictgui as pgui
from gui.planargraphics import (PlanarGraphics, Cursor)

DEFAULTS = DataBag()
DEFAULTS["Name"] = "ScanDataOptions"
DEFAULTS["Channels"] = DataBag()
DEFAULTS["Channels"]["Reference"] = "ref"
DEFAULTS["Channels"]["Indicator"] = "ind"
DEFAULTS["Channels"]["Bleed"] = DataBag()
DEFAULTS["Channels"]["Bleed"]["Ref2Ind"] = 0.
DEFAULTS["Channels"]["Bleed"]["Ind2Ref"] = 0.

            
class ScanData(BaseScipyenData):
    """Dummy for AnalysisUnit; redefined below
    """
    
class ScanDataOptions(DataBag):
    """Do not use
    """
    def __init__(self, detection_predicate=1.3, roi_width = 10, roi_auto_width=False,
                  reference="Ch1", indicator="Ch2", 
                  bleed_ref_ind = 0., bleed_ind_ref = 0., 
                  f0_begin = 0.10*pq.s, f0_end = 0.15*pq.s,
                  fit_begin = 0.05 * pq.s, fit_end = 1 * pq.s, 
                  int_begin = 0. * pq.s, int_end = 0.5 * pq.s,
                  peak_begin = 0.15 * pq.s, peak_end = 0.3 * pq.s,
                  initial=[], lower=[], upper=[], **kwargs):
        
        mutable_types = kwargs.pop("use_mutable", False)
        use_casting = kwargs.pop("use_casting", False)
        allow_none = kwargs.pop("allow_none", False)
        
        
        DataBag.__init__(self, use_mutable=mutable_types, 
                         use_casting=use_casting,
                         allow_none=allow_none, 
                         **kwargs)
        
        self.options = self.__defaults__(detection_predicate = detection_predicate, 
                           roi_width = roi_width, 
                           roi_auto_width=roi_auto_width,
                           reference = reference,
                           indicator = indicator,
                           bleed_ref_ind = bleed_ref_ind, 
                           bleed_ind_ref = bleed_ind_ref, 
                           f0_begin = f0_begin, 
                           f0_end = f0_end,
                           fit_begin = fit_begin, 
                           fit_end = fit_end,
                           int_begin = int_begin, 
                           int_end = int_end,
                           peak_begin = peak_begin, 
                           peak_end = peak_end,
                           initial = initial, 
                           lower = lower, 
                           upper = upper)
    @property
    def defaults(self):
        return ScanDataOptions(self.__defaults__())
    
    def __defaults__(self, detection_predicate=1.3, roi_width = 10, roi_auto_width=False,
                    reference="Ch1", indicator="Ch2", 
                    bleed_ref_ind = 0., bleed_ind_ref = 0., 
                    f0_begin = 0.10*pq.s, f0_end = 0.15*pq.s,
                    fit_begin = 0.05 * pq.s, fit_end = 1 * pq.s, 
                    int_begin = 0. * pq.s, int_end = 0.5 * pq.s,
                    peak_begin = 0.15 * pq.s, peak_end = 0.3 * pq.s,
                    initial=[], lower=[], upper=[]):
        """
        TODO: Customize all parameters on function signature; also write a GUI for this
        """
        # NOTE: 2020-09-28 13:10:15
        # top container is a DataBag
        # NOTE: 2018-06-20 09:14:25
        # now uses OrderedDict (small overhead but worth it)
        # updated to include event (trigger protocol) detection from the ephys data
        # (mapped to the key: "TriggerEventDetection")
        
        #ret = collections.OrderedDict()
        ret = dict()
        #ret = DataBag()
        ret["name"] = "ScanDataOptions"
        
        #ret["Channels"] = collections.OrderedDict()
        ret["Channels"] = DataBag()
        ret["Channels"]["Reference"] = reference
        ret["Channels"]["Indicator"] = indicator
        ret["Channels"]["Bleed_ref_ind"] = bleed_ref_ind # fraction of reference channel that bleeds into indicator channel
        ret["Channels"]["Bleed_ind_ref"] = bleed_ind_ref # fraction of indicator channel that bleeds into reference channel
        
        #ret["IndicatorCalibration"] = collections.OrderedDict() # when all None, this is uncalibrated
        ret["IndicatorCalibration"] = DataBag() # when all None, this is uncalibrated
        # all must be either None, or scalars
        ret["IndicatorCalibration"]["Name"] = None
        ret["IndicatorCalibration"]["Kd"]   = np.nan
        ret["IndicatorCalibration"]["Fmin"] = np.nan
        ret["IndicatorCalibration"]["Fmax"] = np.nan

        #ret["Discrimination"] = collections.OrderedDict() # sucess vs failure
        ret["Discrimination"] = DataBag() # sucess vs failure
        
        # NOTE: 2017-11-22 11:46:41
        # mapping of a func_name to a dict of keyword params (**kwargs)
        # func signature must be func_name(x, **kwargs) and returns a scalar
        # default is below (Frobenius norm for matrices)):
        # axis is None because we operate on single-channel analogsignals (or datasignals)
        
        # NOTE: for multi component EPSCaTs (e.g.a train of EPSCaTs) there are more
        # than one base and peak intervals defined, respectively, before and after 
        # the trigger time for for the corresponding EPSCaT 
        #
        # since the comparison should be done between similarly sized regions, we 
        # define only one such window, that we the take UP TO the trigger time (for 
        # the base) or FROM the trigger time onward (for the peak) 
        
        # NOTE: the trigger times are established by trigger protocols, and NOT 
        # defined here
        
        #ret["Discrimination"]["Base"] = {"np.linalg.norm":{"axis":None, "ord":None}, "window": 0.05 * pq.s}
        ##ret["Discrimination"]["Peak"] = {"np.linalg.norm":{"axis":None, "ord":None}, "window": 0.05 * pq.s} 
        
        #ret["Discrimination"]["Function"] = {"np.linalg.norm":{"axis":None, "ord":None}}
        ret["Discrimination"]["Function"] = DataBag({"function":"np.linalg.norm",
                                                     "args": (),
                                                     "kwargs": {"axis":None, "ord":None}})
        ret["Discrimination"]["BaseWindow"] = 0.05 * pq.s
        ret["Discrimination"]["PeakWindow"] = 0.05 * pq.s
        ret["Discrimination"]["Discr_2D"] = False
        ret["Discrimination"]["WindowChoice"] = "delays" # one of "delays", "triggers", "cursors"
        ret["Discrimination"]["First"] = True

        ret["Discrimination"]["Predicate"] = "lambda x,y: x >= y" # binary predicate: 
                                                            # generates a function by 
                                                            # calling func = eval(str)
                                                            # where str is as shown here
                                                        
        ret["Discrimination"]["PredicateFunc"] = "lambda x,y: x/y" # calculates one scalar
                                                        # result between peak and base
                                                        
        ret["Discrimination"]["PredicateValue"] = detection_predicate # this will test a scalar (x) against
                                                # this value using the binary predicate 
                                                # given above
                                                #
                                                # scalar x is generated by PredicateFunc
                                                
        #ret["Roi"] = collections.OrderedDict()
        ret["Roi"] = DataBag()
        ret["Roi"]["width"] = roi_width # an int or "auto" => use widths generated by the scan roi detection algorithm
        ret["Roi"]["auto"] = roi_auto_width # when True, set use  # currently not used
        
        #ret["Intervals"] = collections.OrderedDict()
        ret["Intervals"] = DataBag()
        ret["Intervals"]["DarkCurrent"] = [None, None] #start, end, both quantities or None
        ret["Intervals"]["F0"] = [f0_begin, f0_end] # start, end both quantities
        ret["Intervals"]["Fit"] = [fit_begin, fit_end] # start, end both quantities
        ret["Intervals"]["Integration"] = [int_begin, int_end] # start, end, both quantities; 
        ret["Intervals"]["Peak"] = [peak_begin, peak_end] #  start, end both quantities
        
        ret["AmplitudeMethod"] = "direct" # one of "direct" or "levels"
        
        
        
        # Fitting model parameters
        # NOTE: 2017-12-23 13:06:45
        # for each EPSCaT there are n * 2 + 3 parameters packed in a list, where n 
        # is the number of decay components in a single EPSCaT (this is done for 
        # generality, although in most cases single EPSCaT data is fitted well by a 
        # transient with one decay component)
        #
        # NOTE: 2017-12-23 13:12:15 
        # the last parameter in the list is a so-called "delay" (or "onset") and
        # represents the "location" of the transient relative to the beginning of 
        # the sweep.
        # WARNING its value may be the string "trigger", meaning it will be updated 
        # from the trigger protocols
        
        # For multiple EPSCaTs (e.g. an EPSCaT train, or when stimuli generate several
        # individually resolvable EPSCaTs) a list of such parameters must be given 
        # for every single EPSCaT in the compound, and packed in a list
        
        # Hence the ["Fitting"]["Initial"] is a list of lists of parameters
        # and so are the ["Fitting"]["Lower"] and ["Fitting"]["Upper"], for the 
        # lower and upper bounds, respectively, to replicate ["Fitting"]["Initial"]
        
        #ret["TriggerEventDetection"] = collections.OrderedDict()
        #ret["TriggerEventDetection"]["Presynaptic"] = collections.OrderedDict()
        ret["TriggerEventDetection"] = DataBag()
        ret["TriggerEventDetection"]["Presynaptic"] = DataBag()
        ret["TriggerEventDetection"]["Presynaptic"]["Channel"] = 0
        ret["TriggerEventDetection"]["Presynaptic"]["DetectionBegin"] = 0.2 * pq.s
        ret["TriggerEventDetection"]["Presynaptic"]["DetectionEnd"] = 0.3 * pq.s
        ret["TriggerEventDetection"]["Presynaptic"]["DetectEvents"] = False
        ret["TriggerEventDetection"]["Presynaptic"]["Name"] = "epsp"
        
        #ret["TriggerEventDetection"]["Postsynaptic"] = collections.OrderedDict()
        ret["TriggerEventDetection"]["Postsynaptic"] = DataBag()
        ret["TriggerEventDetection"]["Postsynaptic"]["Channel"] = 1
        ret["TriggerEventDetection"]["Postsynaptic"]["DetectionBegin"] = 0.2 * pq.s
        ret["TriggerEventDetection"]["Postsynaptic"]["DetectionEnd"] = 0.3 * pq.s
        ret["TriggerEventDetection"]["Postsynaptic"]["DetectEvents"] = False
        ret["TriggerEventDetection"]["Postsynaptic"]["Name"] = "bAP"
        
        #ret["TriggerEventDetection"]["Photostimulation"] = collections.OrderedDict()
        ret["TriggerEventDetection"]["Photostimulation"] = DataBag()
        ret["TriggerEventDetection"]["Photostimulation"]["Channel"] = 0
        ret["TriggerEventDetection"]["Photostimulation"]["DetectionBegin"] = 0 * pq.s
        ret["TriggerEventDetection"]["Photostimulation"]["DetectionEnd"] = 0 * pq.s
        ret["TriggerEventDetection"]["Photostimulation"]["DetectEvents"] = False
        ret["TriggerEventDetection"]["Photostimulation"]["Name"] = "uepsp"
        
        ##ret["TriggerEventDetection"]["Photostimulation"] = collections.OrderedDict()
        #ret["TriggerEventDetection"]["Photostimulation"] = DataBag()
        #ret["TriggerEventDetection"]["Photostimulation"]["Channel"] = 0
        #ret["TriggerEventDetection"]["Photostimulation"]["DetectionBegin"] = 0 * pq.s
        #ret["TriggerEventDetection"]["Photostimulation"]["DetectionEnd"] = 0 * pq.s
        #ret["TriggerEventDetection"]["Photostimulation"]["DetectEvents"] = False
        #ret["TriggerEventDetection"]["Photostimulation"]["Name"] = "uepsp"
        
        #ret["TriggerEventDetection"]["Imaging frame trigger"] = collections.OrderedDict()
        ret["TriggerEventDetection"]["Imaging frame trigger"] = DataBag()
        ret["TriggerEventDetection"]["Imaging frame trigger"]["Channel"] = 3
        ret["TriggerEventDetection"]["Imaging frame trigger"]["DetectionBegin"] = 0.05 * pq.s
        ret["TriggerEventDetection"]["Imaging frame trigger"]["DetectionEnd"] = 0.1 * pq.s
        ret["TriggerEventDetection"]["Imaging frame trigger"]["DetectEvents"] = False
        ret["TriggerEventDetection"]["Imaging frame trigger"]["Name"] = "imaging"
        
        #ret["Fitting"] = collections.OrderedDict()
        ret["Fitting"] = DataBag()
        ret["Fitting"]["Fit"] = True
        ret["Fitting"]["FitComponents"] = True # when True, fits individual EPSCaT components in an EPSCaT train
        
        nParams = 0
        
        if len(initial) > 0:
            if all([isinstance(i, float) for i in initial]):
                ret["Fitting"]["Initial"] = [initial]
                if models.check_rise_decay_params(initial) <= 1:
                    raise ValueError("Incorrect number of initial EPSCaT parameter values: %d; must be N x 2 + 3, for N decays" % len(initial))
                
                nParams = [len(initial)]
                
            elif all([all([isinstance(i, (tuple, list)) for i in i_] for i_ in initial)]):
                if all([models.check_rise_decay_params(i) >= 1 for i in initial]):
                    ret["Fitting"]["Initial"] = initial
                    
                else:
                    raise ValueError("Incorrect number of initial EPSCaT parameter values")
                
                nParams = [len(initial) for i in initial]
                
            else:
                raise TypeError("Initial EPSCaT parameter values expected to be a list of floats or a list of lists of floats; got %s instead" % initial)
                
        else:
            ret["Fitting"]["Initial"] = [[1, 0.01, 0, 0.01, 0.25]]
            nParams = [5]
            
        if len(lower) > 0:
            if all([isinstance(i, float) for i in lower]):
                if len(lower) == 1:
                    ret["Fitting"]["Lower"] = [lower * p for p in nParams]
                    
                elif any([len(lower) != p for p in nParams]):
                    raise TypeError("Lower bounds must contain 1 or %d values; got %d instead" % (nParams, len(lower)))
                
                ret["Fitting"]["Lower"] = [lower] * len(initial)
                
            
            elif all([all([isinstance(i, float) for i in i_]) for i_ in lower]):
                if len(lower) == len(ret["Fitting"]["Initial"]):
                    if all([len(l) == p for p in nParams]):
                        ret["Fitting"]["Lower"] = lower
                
                else:
                    raise TypeError("Mismatch between number of initial EPSCaT parameter values and lower bounds")
                
            else:
                raise TypeError("Lower bounds expected to be a list of floats or a list of lists of floats; got %s instead" % lower)
            
        else:
            ret["Fitting"]["Lower"] = [[0, 0, 0, 0, 0]]
            
        if len(upper) > 0:
            if all([isinstance(i, float) for i in upper]):
                if len(upper) == 1:
                    ret["Fitting"]["Upper"] = [upper * p for p in nParams]
                    
                elif any([len(upper) != p for p in nParams]):
                    raise TypeError("Upper bounds must contain 1 or %d values; got %d instead" % (nParams, len(upper)))
                
                ret["Fitting"]["Upper"] = [upper] * len(initial)
                
            
            elif all([all([isinstance(i, float) for i in i_]) for i_ in upper]):
                if len(upper) == len(ret["Fitting"]["Initial"]):
                    if all([len(l) == p for p in nParams]):
                        ret["Fitting"]["Upper"] = upper
                
                else:
                    raise TypeError("Mismatch between number of initial EPSCaT parameter values and upper bounds")
                
            else:
                raise TypeError("Upper bounds expected to be a list of floats or a list of lists of floats; got %s instead" % upper)
            
            
        else:
            ret["Fitting"]["Upper"] = [[np.inf, np.inf, 1, np.inf, np.inf]]
            
        nDecays = max([models.check_rise_decay_params(i) for i in ret["Fitting"]["Initial"]])
        
        cfNames = list()
        
        for k in range(nDecays):
            cfNames.append("scale_%d" % k)
            cfNames.append("taudecay_%d" % k)
            
        cfNames += ["offset", "taurise", "delay"]
            
        ret["Fitting"]["CoefficientNames"] = cfNames
        
        return ret

class AnalysisUnit(BaseScipyenData):
    """ Encapsulates a ScanData analysis unit.
    
    An AnalysisUnit object semantically links together landmarks and attributes of
    ScanData objects.
    
    AnalysisUnit objects have the following attributes:
    
    parent: a ScanData object where this AnalysisUnit is defined.
    
    landmark: a pictgui.PlanarGraphics object that defines the structure or
                region of interest in the "scans" attribute of the parent.
                
    protocols: a list of TriggerProtocol objects present in the parent
                and which apply to the experiment(s) performed on this AnalysisUnit
                
    unit_type: a str, the type of the structure analysed (one of the values contained
            in the UnitTypes dict, defined in this module)
            
            This is typically derived from the landmark's name but this can be 
            overridden by the user.
                
    cell:   a str, the name of the cell to which this AnalysisUnit belongs
    
    field: a str, the name of the field of view where this AnalysisUnit was defined
            (it is assumed the field corresponds to a wider region of the cell,
            where the AnalysisUnit is defined)
            
    scene: boolean, default is False
            
        NOTE: by definition, AnalysisUnits are defined in, and associated with,
            the "scans" image data set of a ScanData object. However, by setting
            scene to True, AnalysisUnit object will be associated with scene,
            rather than scans, data.
                    
    Additional parameters (e.g. geometric descriptors) are given by the var-named
    parameters **kwargs of the constructor.
    
    """
    from gui import pictgui as pgui
    
    _descriptor_attributes_ = (("landmark", PlanarGraphics),
                           ("unit_type", "NA"),
                           ("unit_name", "NA"),
                           ("field", "NA"),
                           ("inscene", False)) + BaseScipyenData._descriptor_attributes_
    
    def __init__(self, parent, name=None, description=None, file_origin=None, **kwargs):
        
        """AnalysisUnit constructor.
        
        Positional parameters:
        ======================
        
        parent - a ScanData object; the AnalysisUnit object stores a reference
                    to it.
        
        Named parameters:
        =================
        name deacriptoin, file_origin - see BaseScipyenData
        
        landmark: a pictgui.PlanarGraphics object or None
        
            when None, the parent ScanData Object is considered a single AnalysisUnit
            
        protocol: a TriggerProtocol or a sequence (tuple, list) of TriggerProtocol objects
        
        unit_type: str or None (default)
        
            when None, it will be  determined from the name of the landmark if
            it is a PlanarGraphics, or the name of thr parent ScanData otherwise,
            according to the rules set in UnitTypes dictionary in this module
            
            when a string it must be non-empty and must not be made exclusively
            of blank characters (space, tab)
            
        cell: str, default value is "NA"
        
        field: str, default value is "NA"
        
        scene: bool (default, False). When True, this AnalysisObject is associated 
            with ScanData scene images
            
        name:
        
        Var-named parameters:
        =====================
        
        **kwargs should contain various geometrical descriptors (user-depedent, 
            should be consistent for a given unit type)
        
        """
        import gui.pictgui as pgui
        
        super().__init__(name, description, file_origin, **kwargs)
        
        if isinstance(self.parent, AnalysisUnit):
            self = parent.copy()
            return
        
        if not isinstance(parent, ScanData):
            raise TypeError("parent is expected to be a ScanData object; got %s instead" % type(parent).__name__)
        
        # NOTE that these frames are not necessarily identical to the frames
        # in the protocols, but there should be an overlap between protocol
        # frame indices and landmark frame indices, otherwise the analysis unit 
        # will be pointless
        #
        # NOTE that the self.frames property returns the intersection between
        # the protocol frames and landmark frames, calculated dynamically
        
        if self._landmark_ is None or len(self._landmark_.frameIndices) == 0:
            if self._inscene_:
                self._frames_ = range(parent.sceneFrames)
                
            else:
                self._frames_ = range(parent.scansFrames)
                
        else:
            # get the frames with ladmark states, irrespective of whether this
            # units is defined in scene or scans
            self._frames_ = self._landmark_.frameIndices
        
        if isinstance(self._protocols_, TriggerProtocol):
            self._protocols_ = [self._protocols_]
            
        elif isinstance(self._protocols_, (tuple, list)):
            if not all([isinstance(t, TriggerProtocol) for t in self._protocols_]):
                warnings.warn("'protocols' must be a sequence of TriggerProtocol objects")
                self._protocols_.clear()
                #raise ValueError("'protocols' must be a sequence of TriggerProtocol objects")
            names = [t.name for t in self._protocols_]
            
            if any([names.count(n)>1 for n in names]):
                warnings.warn("TriggerProtocol objects must have unique, distinct names; they will be renamed!")
                for k,p in enumerate(self._protocols_):
                    p.name = f"protocol_{k}_{p.name}"
                #raise ValueError("TriggerProtocol objects must have unique, distinct names")
            
        else:
            warnings.warn("'protocols' expected to be a TriggerProtocol object or a sequence of TriggerProtocol objects; got %s instead" % type(self._protocols_).__name__)
            
            self._protocols_ = list()
            #raise TypeError("'protocols' expected to be a TriggerProtocol object or a sequence of TriggerProtocol objects; got %s instead" % type(self._protocols_).__name__)
        
        
    def __str__(self):
        result = list()
        result.append("\n%s:" % self.__class__.__name__)
        result.append(self.__attr_str__())

        return "\n".join(result)
    
    def __repr__(self):
        return self.__str__()
    
    def hasAnalysis(self, frame_or_protocol=None):
        """Queries whether this analysis unit has been analysed in a given frame.
        
        To test against a specific protocol frames, 
        
        Named parameters:
        =================
        
        frame_or_protocol: an int (frame index) or a TriggerProtocol, or None
        
            When an int, it must be present in the self.frames property.
            
            When a TriggerProtocol, the funciton will query for analysis for all 
            the protocol's frames that are associated with this unit.
            
            When None, the function checks if the analysis unit has been 
            analysed in all frames with which it is associated.
        
        """
        if self.parent is None:
            warnings.warn("Analysis unit %s has no parent data" % self.name)
            return False
        
        if self.landmark is not None:
            name = self.landmark.name
            
        else:
            name= self.name

        test_frames = self.frames
        
        if isinstance(frame_or_protocol, int):
            if frame_or_protocol not in self.frames:
                raise ValueError("Specified frame (%d) is not normally associated with this unit (%s)" % (frame_or_protocol, self.name))
            test_frames = [frame_or_protocol]
            
        elif isinstance(frame_or_protocol, TriggerProtocol):
            if frame_or_protocol not in self.protocols:
                raise ValueError("Trigger protocol (%s) is not associated with this analysis unit (%s)" % (frame_or_protocol.name, self.name))
            test_frames [ [f for f in frame_or_protocol.segmentIndices() if f in self.frames]]
            
        elif frame_or_protocol is not None:
            raise TypeError("'frame_or_protocol' parameter expected to be an int, a TriggerProtocol, or None; got %s instead" % type(frame_or_protocol).__name__)
        
        if self.inScene:
            if len(self.parent.sceneBlock.segments) == 0:
                warnings.warn("Parent data %s of this analysis unit (%s) has not been analysed" % (self.parent.name, self.name))
                return False
            
            return all([f in range(len(self.parent.sceneBlock.segments)) and \
                    name in [sig.name for sig in self.parent.sceneBlock.segments[f].analogsignals] \
                    for f in test_frames])
            
        else:
            if len(self.parent.scansBlock.segments) == 0:
                warnings.warn("Parent data %s of this analysis unit (%s) has not been analysed" % (self.parent.name, self.name))
                return False
            
            return all([f in range(len(self.parent.scansBlock.segments)) and \
                    name in [sig.name for sig in self.parent.scansBlock.segments[f].analogsignals] \
                    for f in test_frames])
            
    @property
    def frameEventDetection(self):
        """Returns a nested dict of protocols and frame indices and their associated 
        success flags.
        
        The list contains two-element tuples, first element if the frame index,
        and the second element if a sequence of booleans each for as many event 
        successes were detected (problem-defined).
        
        E.g.:
        
        {'1bAP': {0: [True]},
         '2bAP': {1: [True]},
         '3bAP': {2: [True]},
         '5bAP': {3: [True]}}
                
        When no protocol is defined, this property is a dict with one element:
        {"no_protocol": {0: [True], {1: [False]}}} etc
         
        NOTE: It is not necessary that all frames have the same number of events, 
        but the number of boolean values must equal that of the number of events.
        
        ATTENTION:
        Will raise exception if any of the associated data frames haven't been 
        analysed. To avoid this use self.hasAnalysis() first.
        
        NOTE: 2018-08-05 10:57:48
        A unit may NOT associate all the frames in the data, for a given protocol.
        
        """
        if self.parent is None:
            raise RuntimeError("Analysis unit %s has no parent data" % self.name)
            
        if len(self.parent.scansBlock.segments) == 0:
            raise RuntimeError("Analysis unit %s has not been analysed" % self.name)
        
        result = collections.OrderedDict()
        
        #print("frameEventDetection:")
        #print("unit", self.name)
        
        # when no protocols exist, return a generic protocol named "no_protocol"
        if len(self.protocols):
            for protocol in sorted(self.protocols, key=lambda x: x.name):
                #print("protocol", protocol.name)
                
                frame_dict = dict()
                
                for f in protocol.segmentIndices():
                    if f not in self.frames:
                        continue
                    #print("frame", f)
                    
                    if self.inScene:
                        if f not in range(len(self.parent.sceneBlock.segments)):
                            warnings.warn("Frame %d does not appear to have been analysed for unit %s in scan data %s" % \
                                (f, self.name, self.parent.name), RuntimeWarning)
                        
                        if self.landmark is None:
                            signal_index = get_index_of_named_signal(self.parent.sceneBlock.segments[f], self.name, silent=True)
                            
                            if signal_index is None:
                                raise RuntimeError("Analysis unit %s on entire scan data %s does not appear to have been analysed for frame %d" %\
                                    (self.name, self.parent.name, f))
                            
                        else:
                            signal_index = get_index_of_named_signal(self.parent.sceneBlock.segments[f], self.landmark.name, silent=True)
                        
                            if signal_index is None:
                                raise RuntimeError("Analysis unit %s on landmark %s in scan data %s does not appear to have been analysed for frame %d" %\
                                    (self.name, self.landmark.name, self.parent.name, f))
                            
                        annotations = self.parent.sceneBlock.segments[f].analogsignals[signal_index].annotations
                    
                    else:
                        if f not in range(len(self.parent.scansBlock.segments)):
                            raise RuntimeError("Frame %d does not appear to have been analysed for unit %s in scan data %s" % \
                                (f, self.name, self.parent.name))
                        
                        if self.landmark is None:
                            signal_index = get_index_of_named_signal(self.parent.scansBlock.segments[f], self.name, silent=True)
                            
                            if signal_index is None:
                                raise RuntimeError("Analysis unit %s on entire scan data %s does not appear to have been analysed for frame %d" %\
                                    (self.name, self.parent.name, f))
                            
                        else:
                            signal_index = get_index_of_named_signal(self.parent.scansBlock.segments[f], self.landmark.name, silent=True)
                        
                            if signal_index is None:
                                raise RuntimeError("Analysis unit %s on landmark %s in scan data %s does not appear to have been analysed for frame %d" %\
                                    (self.name, self.landmark.name, self.parent.name, f))
                            
                        annotations = self.parent.scansBlock.segments[f].analogsignals[signal_index].annotations
                        
                    success_components = [bool(v) for v in annotations["FailSuccess"]["success"]]
                    
                    frame_dict[f] = success_components
                    #print("frame_dict", frame_dict)
                    
                if len(frame_dict):
                    result[protocol.name] = frame_dict
                
        else:
            # no protocols
            unit_frames = self.frames
            frame_dict = dict()
            for f in unit_frames:
                if self.inScene:
                    if f not in range(len(self.parent.sceneBlock.segments)):
                        raise RuntimeError("Frame %d does not appear to have been analysed for unit %s in scan data %s" % \
                            (f, self.name, self.parent.name))
                    
                    if self.landmark is None:
                        signal_index = get_index_of_named_signal(self.parent.sceneBlock.segments[f], self.name, silent=True)
                        
                        if signal_index is None:
                            raise RuntimeError("Analysis unit %s on entire scan data %s does not appear to have been analysed for frame %d" %\
                                (self.name, self.parent.name, f))
                        
                    else:
                        signal_index = get_index_of_named_signal(self.parent.sceneBlock.segments[f], self.landmark.name, silent=True)
                    
                        if signal_index is None:
                            raise RuntimeError("Analysis unit %s on landmark %s in scan data %s does not appear to have been analysed for frame %d" %\
                                (self.name, self.landmark.name, self.parent.name, f))
                        
                    annotations = self.parent.sceneBlock.segments[f].analogsignals[signal_index].annotations
                    
                else:
                    if f not in range(len(self.parent.scansBlock.segments)):
                        raise RuntimeError("Frame %d does not appear to have been analysed for unit %s in scan data %s" % \
                            (f, self.name, self.parent.name))
                    
                    if self.landmark is None:
                        signal_index = get_index_of_named_signal(self.parent.scansBlock.segments[f], self.name, silent=True)
                        
                        if signal_index is None:
                            raise RuntimeError("Analysis unit %s on entire scan data %s does not appear to have been analysed for frame %d" %\
                                (self.name, self.parent.name, f))
                        
                    else:
                        signal_index = get_index_of_named_signal(self.parent.scansBlock.segments[f], self.landmark.name, silent=True)
                    
                        if signal_index is None:
                            raise RuntimeError("Analysis unit %s on landmark %s in scan data %s does not appear to have been analysed for frame %d" %\
                                (self.name, self.landmark.name, self.parent.name, f))
                        
                    annotations = self.parent.scansBlock.segments[f].analogsignals[signal_index].annotations
                
                success_components = [bool(v) for v in annotations["FailSuccess"]["success"]]
                
                frame_dict[f] = success_components
                
            if len(frame_dict):
                result["no_protocol"] = frame_dict
            
        return result
            
    @property
    def parent(self):
        """A ScanData object that is the parent of this unit.
        """
        if not hasattr(self, "_parent_"):
            self._parent_ = None
            
        if hasattr(self, "_parent"):
            self._parent_ = self._parent
            del self._parent
            
        return self._parent_
    
    @parent.setter
    def parent(self, obj):
        if not isinstance(obj, ScanData):
            warnings.warn("Expecting a ScanData object; got %s instead" % type(ob).__name__)
        
        
        self._parent_ = obj
            
    @safeWrapper
    def protocol(self, index:typing.Union[str, int]):
        """Returns a trigger protocol specified by "index".
        
        Parameters:
        ==========
        "index" : a str (protocol name) or an int (index of data frame)
        
        When index is a str, it must be the name of a protocol associated with 
            this unit and that protocol, if found, is returned.
        
        When index is an int, it must be a frame index present in the 
            "frames" property of this analysis unit object. If found, it will
            return the protocol associatd with that frame (if any).
        
        Returns:
        ========
        
        TriggerProtocol: The trigger protocol named as specified by "index", or 
            associated with the frame specified by "index", depending on whether
            "index" is a string or an integer.
        
        None, when there is no trigger protocol with the name specified by 
            'index' (when 'index' is a str), or when the specified frame index 
            does not associate a protocol (when 'index' is an int).
        
        """
        if len(self.protocols) == 0:
            return None
        
        if isinstance(index, str):
            if index in [p.name for p in self.protocols]:
                
                protocols = [p for p in self.protocols if p.name == index]
                
                if len(protocols) > 1:
                    warnings.warn("There appears to be %d protocols named '%s'" % (len(protocols), index), RuntimeWarning)
                
                return protocols[0]
            
            else:
                return
                #raise ValueError("AnalysisUnit %s does not associate a protocol named %s" % (self.name, index))
            
        elif isinstance(index, int):
            if index not in self.frames:
                return None
                #raise ValueError("Frame index %d is not associated with this unit" % index)
        
            protocols = [p for p in self.protocols if index in p.segmentIndices()]
            
            if len(protocols) > 1:
                raise RuntimeError("Frame %d appears to associate %d protocols" % (index, len(protocols)))
            
            if len(protocols) == 0:
                return None
            
            return protocols[0]
        
        else:
            raise TypeError("'index' expected to be a str or an int; got %s instead" % type(name).__name__)
        
    @safeWrapper
    def getProtocols(self, names):
        if isinstance(names, (tuple, list)) and all([isinstance(n, str) for n in names]):
            pr_names = [p.name for p in self.protocols]
            
            if any([n not in pr_names for n in names]):
                raise ValueError("some or all names do not specify protocols associated with this AnalysisUnit")
            
            pr_list = list()
            for n in names:
                pr_list.append([p for p in self.protocols if p.name == n][0])
                
            return pr_list
        
        else:
            raise TypeError("A sequence of strings was expected")
        
    @property
    def protocols(self):
        """A list of TriggerProtocol objects (references)
        """
        if not hasattr(self, "_protocols_"):
            self._protocols_  = list()
            
        if hasattr(self, "_protocols"):
            self._protocols_ = self._protocols
            del self._protocols
            
        return self._protocols_
    
    @protocols.setter
    def protocols(self, value):
        if isinstance(value, TriggerProtocol):
            self._protocols_ = [value]
            
        elif isinstance(value, (tuple, list)) and all([isinstance(p, TriggerProtocol) for p in value]):
            self._protocols_[:] = value #  a reference !
            
            self._protocols_.sort(key=lambda x: x.segmentIndices()[0])
            
        else:
            raise TypeError("Expecting a TriggerProtocol, or a sequence of TriggerProtocol objects; got %s instead" % type(value).__name__)
        
        if hasattr(self, "_protocols"):
            del self._protocols_
            
    @property
    def frames(self):
        """A list of frame indices where landmark is defined, given the protocols.
        Read-only
        
        This property is the intersection between the set of frames associated with
        the unit's landmark and the set of frames where the unit's protocol or 
        protocols apply.
        
        To change, modify self.landmark.frameIndex and self.protocol(...).segmentIndex
        properties.
        
        For units based on entire ScanData set (i.e. not landmark-based), this property
        is the union of all the frame indices in the ScanData where the unit's protocol
        or protocols apply.
        
        When there are no protocols defined, then this property is the same
        as the landmark's frame indices (i.e. the data frames where the
        landmark applies).
        
        """
        if not hasattr(self, "_frames_"):
            self._frames_ = range(1)
            
        if hasattr(self, "_frames"):
            self._frames_ = self._frames
            del self._frames
            
        if not hasattr(self ,"_protocols_"):
            self._protocols_ = list()
            
        if hasattr(self, "_protocols"):
            self._protocols_ = self._protocols
            del self._protocols
            
        if self.landmark is None:
            if self.inScene:
                self._frames_ = range(self.parent.sceneFrames)
                
            else:
                self._frames_ = range(self.parent.scansFrames)
            
        else:
            self._frames_ = self.landmark.frameIndices
                
        if len(self._protocols_):
            protocol_frames = list()
            
            for p in self._protocols_:
                protocol_frames += p.segmentIndices()[:]
                
            result = [f for f in self._frames_ if f in protocol_frames]
            
        else:
            result = [f for f in self._frames_]
                
        return result
    
    def scanData(self, average=None):
        """Returns a ScanData object representing this AnalysisUnit only.
        This requires the parent ScanData object to be alive.
        
        The function delegates to the ScanData.exportScansAnalysisUnit() function.
        Image data will be cropped as necessary.
        
        Named parameter:
        ===============
        
        average: boolean or None; default is None; 
        
            When None (the default), the behaviour of this function is determined
            by the boolean value of "averaged" attribute in this object's descriptors
            if it exists. Failing that, the function will behave as if average=False
            was passed.
        
            When True, the function will average the frames in the parent ScanData
            (see ScanData.exportScansAnalysisUnit).
            
        """
        if average is None:
            average = True if self.annotations.get("averaged", None) is True else False
        
        result = self._parent_.extractAnalysisUnit(self.landmark, 
                                                   protocol=self.protocols,
                                                   average=average)
        
        return result
    
    def isSameAs(self, other):
        if not isinstance(other, AnalysisUnit):
            raise TypeError("Expecting an AnalysisUnit object; got %s instead" % type(other).__name__)
        
        sameName = self.name == other.name
        
        sameParent = self.parent == other.parent
        
        sameSource = self.inScene == other.inScene
        
        sameLandmark = self.landmark == other.landmark
        
        sameProtocols = all([p in other.protocols for p in self.protocols])
        
        sameType = self.unit_type == other.unit_type
        
        sameCell = self.cell == other.cell
        
        sameField = self.field == other.field
        
        sameDescriptors = self.descriptors == other.descriptors
        
        return sameParent and sameName and sameSource and sameLandmark and sameProtocols and sameType and sameCell and sameField and sameDescriptors
    
    def is_same_as(self, other):
        return self.isSameAs(other)
    
    def copy(self):
        """Returns a copy of this object.
        
        The result's landmark is a references to the landmark and of this unit.
        The result's protocols are deep copies of those in this unit.
        
        """
        # NOTE: 2021-11-26 08:42:21
        # use copy constructor strategy for trigger protocols so that the new 
        # AnalysisUnit objact is detached from the original data protocols; yet
        # it retains the reference to the 'parent'
        
        kwargs = dict((attr[0], getattr(self, attr[0], None)) for attr in self._descriptor_attributes_ )
        kwargs["protocols"] = [p.copy() for p in self.protocols]
        kwargs.update(self.annotations)
        
        result = AnalysisUnit(self.parent, **kwargs)
        
        return result
        
class ScanDataImageParser(AttributeAdapter):
    def __init__(self, owner=None, fieldname=None):
        self.fieldname = fieldname
        self.obj = owner
        
    def __call__(self, obj=None, value=None):
        self.parseImageData(value)
        
    def parseImageData(self, value):
        """Proposes a layout and calubrarion for VigraArray axes.
        Parameters:
        ==========
        value: VigraArray or list of VigraArray objects
        
        Returns
        =======
        layout:Bunch with the following key:str to value mapping 
            (value types are indicated below):
            
            nFrames -> int # number of data frames in the VigraArray
            
            horizontalAxis -> int # index of the axis displayed horizontally
            
            verticalAxis -> int # index of the axis dusplayed vertically
            
            channelsAxis -> int # index of the Channels axis tag, or the number
                of dimensions of the array (for 'virtual' Channels axis)
                
            framesAxis -> int or tuple of int # the index (or indices) of the 
                axis along which 2D data slices (frames) are displayed, one at 
                a time
                
        Side effects:
        ============
        The layout and the axes calibrations are assigned to the descriptors
        '<self.fieldname>Layout' and '<self.fieldname>AxesCalibration' in the 
        owner of this ScanDataImageParser object.
                
        See also: self.imageDataLayout method
            
        """
        if self.obj is None:
            return
        
        if not hasattr(self.obj, "_data_children_"):
            return
        
        if self.fieldname not in ("scans", "scene"):
            return

        if not hasattr(self.obj, self.fieldname):
            return
        
        imageLayout = getattr(self.obj, f"{self.fieldname}Layout", None)
        frameAxis = None if not isinstance(imageLayout, dict) else imageLayout.get(f"{self.fieldname}FrameAxis", None)
        axesCalibration = getattr(self.obj, f"{self.fieldname}AxesCalibration", None)
        
        data, layout, axesCalibration = self.imageDataLayout(value, 
                                                            frameAxis = frameAxis,
                                                            axescal = axesCalibration)
        
        setattr(self.obj, f"{self.fieldname}Layout", layout)
        setattr(self.obj, f"{self.fieldname}AxesCalibration", axesCalibration)
        
        return layout
    
    def imageDataLayout(self,data, 
                    frameAxis:typing.Optional[vigra.AxisInfo]=None, 
                    horizontalAxis:typing.Optional[vigra.AxisInfo]=None, 
                    verticalAxis:typing.Optional[vigra.AxisInfo]=None, 
                    axescal:typing.Optional[AxesCalibration]=None):
        """ Proposes an axes layout and axes calibration for the data.
        
        See also imaging.vigrautils.proposeLayout()
        
        Returns
        --------
        
        The tuple (data, layout, axes_calibration):
        
        'data': VigraArray object, or sequence of at least one VigraArray 
            object, or None.
            When a sequence, the vigra arrays must have have identical 
            shapes and axistag keys. If there is more than one vigra array
            in the sequence then all the arrays must have one channel only.
            
        'layout': traitlets.Bunch or None. When a Bunch, it maps the following
            key/value pairs:
            
            'nFrames':      int;
                            This is the total number of 2D data 
                            slices (or frames) that can be displayed in a 2D 
                            viewer one at a time.
                            
                            The 'frames' are defined along the data array axis 
                            that is orthogonal to the display plane. For more
                            details see imaging.vigrautils.proposeLayout().
                            
            'horizontalAxis': int; 
                            Index - or dimension - of the horizontal axis.
                            This is the axis corresponding to the 'horizontal'
                            dimension (or aspect) of the data for the purpose of
                            being displayed in a 2D image viewer.
                            
            'verticalAxis': int;
                            Index - or dimension - of the vertical axis
                            This is the axis corresponding to the 'vertical'
                            dimension (or aspect) of the data for the purpose of
                            being displayed in a 2D image viewer.
                            
            'channelsAxis': int; 
                            Index - or dimension - of the channels axis
                            For VigraArray objects, the size of the image data
                            array on this dimension (or axis) indicates the
                            number of data channels in each pixel.
                            
            'framesAxis':   int; 
                            Index - or dimenson - of the frames axis
                            This is the axis (or axes) along which 2D data 
                            frames (or slices) are taken to be displayed one at
                            a time in a 2D image viewer.
                            
            For a detailed explanation of the concept of frames and frames axis
            see imaging.vigrautils.proposeLayout()

        'axes_calibration': an imaging.axiscalibration.AxesCalibration object, 
                            or None.
                            
        """
        if data is None:
            return (None, None, None)
        
        if not isinstance(data, (vigra.VigraArray, tuple, list)):
            raise TypeError(f"Expecting a VigraArray or a sequence (tuple, list) of VigraArrays; got {type(data).__name__} instead")
        
        if isinstance(data, vigra.VigraArray):
            layout = proposeLayout(data, userFrameAxis = frameAxis, indices = True)
            
            if isinstance(axescal, AxesCalibration) and all(axescal.typeFlags(key) == x.typeFlags for (key, x) in zip(axescal.axiskeys, data.axistags)):
                axes_cal = [axscal]
            else:
                axes_cal = [AxesCalibration(data)]
                
            return ([data], layout, axes_cal)
            
        elif isinstance(data, (tuple, list)):
            if len(data):
                if not all([isinstance(s, vigra.VigraArray) for s in data]):
                    raise TypeError("When not empty, data is expected to contain VigraArray objects")

                if not all([s.shape == data[0].shape for s in data[1:]]):
                    raise TypeError("Image arrays in a sequence must have identical shapes")

                if not all([s.axistags == data[0].axistags for s in data[1:]]):
                    raise TypeError("Image arrays in a sequence must have identical axistags")
                
                if len(data) > 1 and any(s.channels > 1 for s in data):
                    raise TypeError("When more than one image array is supplied, these must have a single channel")

                if not all([s.channels == data[0].channels for s in data[1:]]):
                    raise TypeError("Image arrays in a sequence must have the same number of channels")

                # NOTE: 2022-01-06 10:38:28
                # when several images are contained in 'data' we assume they
                # all have the same axes layout
                layout = proposeLayout(data[0], userFrameAxis = frameAxis, indices = True)
                
                if isinstance(axescal, (tuple, list)):
                    if len(axescal) != len(data):
                        raise ValueError(f"Axes calibration expected to be a sequence with as many elements as 'data' ({len(data)}; got {len(axescal)} instead)")
                    
                    if not all(isinstance(ac, AxesCalibration) for ac in axescal):
                        raise TypeError("Expecting a tuple of AxesCalibration objects")
                    
                    if all(all(axcal.typeFlags(key) == x.typeFlags for (key, x) in zip(axcal.axiskeys, img.axistags)) for axcal,img in zip(axescal,data)):
                        axes_cal = [axcal for axcal in axescal]
                    else:
                        axes_cal = [AxesCalibration(img) for img in data]
                else:
                    axes_cal = [AxesCalibration(img) for img in data]
                
                return (data, layout, axes_cal)

            return (list(), None, None)
                
        return (None, None, None)
                    
class ScanDataFramesMapUpdater(AttributeAdapter):
    def __init__(self, owner=None, fieldname=None):
        self.fieldname = fieldname
        self.obj = owner
        
    def __call__(self, obj=None, value=None):
        self.updateFramesMap(value)
        
    def updateFramesMap(self, value):
        """Adapts the frames map to the electrophysiology's segments.
        
        Sets up a default correspondence:
        
        If the new electrophysiology Block has fewer segments that the number of 
        virtual frames in this ScanData object, its segment indices are mapped 
        to the first len(segments) data master frames, and the exceeding data 
        virtual frames are mapped to the last segment in the electrophysiology
        block.
        
        If the new electrophysiology block has more segments than the number of 
        frames in the ScanData object, the ScanData frames map is adjusted such
        that the total number of virtual frames equals len(segments), and the 
        scans and scene frames are mapped to the first electrophysiology
        segments ('sweeps' or 'frames'); the exceeding segments are mapped to
        the last frame in scans and scene.
        
        When the number of electrophysiology segments equals that of the virtual
        data frames, the segment indices are mapped 1-2-1 to the virtual frames
        in increasing order.
        
        For a more atomic configuration use self.setFramesRelationship() after
        assigning to self.electrophysiology
        
        """
        #  NOTE: 2021-12-06 12:42:06 
        # this is a "postset" validator - this means that value has already
        # been assigned to field!
        if self.obj is None:
            return
        
        if not hasattr(self.obj, "_data_children_"):
            return
        
        if self.fieldname not in tuple(c[0] for c in self.obj._data_children_):
            return

        if not hasattr(self.obj, self.fieldname):
            return
        
        if not hasattr(self.obj, "framesMap"):
            return
        
        framesMap = getattr(self.obj, "framesMap", None)
        
        field = getattr(self.obj, self.fieldname)
        
        if framesMap is None:
            field_frames = dict((c[0], 0) for c in self.obj._data_children_)
            for c in field_frames:
                if c in ("scene","scans"):
                    f = getattr(self.obj, f"{c}Layout", None)
                    nFrames = f.get("nFrames", 0) if isinstance(f, dict) else 0
                    val = nFrames if isinstance(nFrames, int) else np.prod(nFrames)
                    
                else:
                    data = getattr(self.obj, c, None)
                    val = len(data.segments) if isinstance(data, neo.Block) else 0
            
                field_frames[c] = val
            
            # NOTE: 2022-01-04 16:06:11
            # FrameIndexLookup is now MANDATORY - see also NOTE: 2022-01-04 16:05:12
            framesMap = FrameIndexLookup(field_frames)
            
            setattr(self.obj, "framesMap", framesMap)
        
        else:
            nframes = len(framesMap)
                
            if isinstance(field, neo.Block):
                newframes = len(field.segments)
                
            elif isinstance(field, list) and all(isinstance(v, vigra.VigraArray) for v in field):
                userFrameAxis = getattr(self.obj, f"{self.fieldname}FrameAxis", None)
                axesCalibration = getattr(self.obj, f"{self.fieldname}AxesCalibration", None)
                data, layout, axesCalibration = self.obj.imageDataLayout(field,
                                                                            frameAxis = userFrameAxis,
                                                                            axescal = axesCalibration)
                newframes = layout.nFrames
                
            else:
                newframes=0
            
            if newframes == nframes:
                # assume 1-2-1 correspondence with the index in framesMap
                self.obj.framesMap[self.fieldname] = range(newframes)
                
            elif newframes < nframes:
                value = list(range(newframes))
                value.extend([self.obj.framesMap.missingFrameIndex for k in range(newframes, nframes)])
                        
                framesMap[self.fieldname] = value
                
            else: # --> newframes > nframes
                # concatenate a new frame index lookup
                dd = dict()
                for c in self.obj._data_children_:
                    name = c[0]
                    if name != self.fieldname:
                        if np.any(self.obj.framesMap[name].isna()):
                            val = None
                        else:
                            val = 0
                        dd[name] = val
                        
                    else:
                        dd[name] = newframes - nframes
                        
                fil = FrameIndexLookup(dd)
                fil[self.fieldname] = range(nframes, newframes)
                
                newmap = pd.concat([self.obj.framesMap.map, fil.map], ignore_index=True)
                
                self.obj.framesMap.map = newmap

class ScanData(BaseScipyenData):
    """An almost direct translation of matlab LSData data structure.
    Work in progress.
    
    TODO/FIXME 2018-09-14 10:28:13 - place on back-burner...
    collapse scene and scans data into a multi-channel
    VigraArray, then adapt all methods to this scenario
    
    Difficult task, as I want to retain backward compatibility with 
    current situation where scene and scans are a list of VigraArrays.
    
    Perhaps I should create a new :class: for this (say ScanData2) adopting
    functionality from ScanData then, phase ScanData out: rename ScanData2 to ScanData
    and provide a way to convert already pickled (old) ScanData objects 
    to the new class, on the fly.
    
    On the upside, it should make the API less convoluted and more uniform
    (we will have to bindAxis("c"...) to access individual channels)
    
    NOTE: 2021-10-29 10:41:27 About data component frames
    
    Ideally there should be a biunivocal relationship between frames across all
    compoents, i.e.:
    
    scans frame K   -> electrophysiology block, segment K
                    |
                    -> scene frame K
                    
    However, this is not always practical.
    
    A frame index mapping algorithm is needed, which maps a frame index in the
    "primary" data component to frames in the "secondary" data components to
    allow "unbalanced" cases where a "secondary" data component has a different
    number of frames than the "primary" data component.
    
    In ScanData the "primary" data component is always stored in the "scans"
    attribute. When this is None or empty, then the primary data component is 
    "scene".
    
    The "scene" attribute is optional. When present, the scene's purpose is to
    contextualize the scan data (e.g., for line scans, the scene is a 2D raster
    scan of the field of view where the line scanning trajectory is defined).
    
    The table below gives an overview of the different possible acqusition types
    and their data components. This is currently based on PrairieView acqusition
    model but the aim is to extend this to ScanImage data as well.
    
    Scan data type  Scans           Scene               Electrophysiology
    (PrairieView)
    ============================================================================
    
    SingleImage     sequence of     None                None
                    one frame       
    
    ZSeries         sequence of     None                None
                    frames
                                
    TSeries         sequence of     None                None, or neo.Block
                    frames                              (e.g., in conjunction 
                                                        with photoactivation)
                                
    Line scan       sequence of     sequence of         neo.Block
                    frames          frames 
                                    (possibly just
                                    one frame)
    
    
    
    TODO Class documentation
    
    Properties of special interest:
    
    scansBlock
    
        neo.Block object containing time-varying imaging data derived from
        the analysis of ROIs or cursors in the scans data subset.
        
        NOTE: Referred to as "imaging block" in this documentation
    
        Only relevant when this is a linescan data or a time series with raster 
        scans.
        
        _scans_block_.segments
        
        Each segment corresponds to a single "trial" or "repetition", or "cycle", 
        and its "analogsignals" contain the time-varying image parameters
        measured in ROIs or along Cursors. See neo.Segment and neo.AnalogSignal.
        
        For time series, the _scans_block_ contains only one segment.
        
        _scans_block_.segments[k].analogsignals:
        
    FIXME:2019-03-17 18:28:07 WE NEED SOME SERIOUS DEBUGGING !
    
    1) removeAnalysisUnit does not seem to remove all linked cursor frontends
        when called from LSCaTWindow
        
    2) extractAnalysisUnit(..., average=True):
        scanRegion retains more states than necessary 
        
        For example, e.g. extracted & averaged unit data with 9 frames but having
        a scanRegion with states for 26 frames -- why? The original data had
        38 frames in this particular example -- see 18l12 CACNA1C152mHET/c01/sp01/ 
        Where the did the 26 come from?
        
    """
    from gui import pictgui as pgui
    
    # NOTE: 2022-01-11 13:48:37
    # to be able to load older pickles:
    ImageParser = ScanDataImageParser
    FramesMapUpdater = ScanDataFramesMapUpdater
    
    # TODO: provide for volume-mode analysis and ROIS; 
    class ScanDataType(enum.IntEnum):
        linescan    = 1
        timeseries  = 2
        zseries     = 3
        
    class ScanDataAnalysisMode(enum.IntEnum):
        frame       = 1
        volume      = 2
        
    # NOTE: 2021-11-30 16:07:40
    # 'triggers' is inherited from BaseScipyenData along with others
    _data_children_ = (
        ("scans",                           (list, tuple),   vigra.VigraArray),
        ("scene",                           (list, tuple),   vigra.VigraArray),
        ("electrophysiology",               (neo.Block(name="Electrophysiology"), None)),
        )
    
    _derived_data_children_ = (
        ("scansBlock",                      neo.Block(name="Scans")),
        ("scansProfiles",                   neo.Block(name="Scan region scans profiles")),
        ("sceneBlock",                      neo.Block(name="Scene")),
        ("sceneProfiles",                   neo.Block(name="Scan region scene profiles")),
        )
    
    _result_data_ = (
        ("electrophysiologyResult",         pd.DataFrame),
        ("imagingResult",                   pd.DataFrame),
        ("result",                          pd.DataFrame),
        )
    
    _data_attributes_ = (
        ("sceneAxesCalibration",            list,   AxesCalibration),
        ("scansAxesCalibration",            list,   AxesCalibration),
        ("sceneLayout",                     dict),
        ("scansLayout",                     dict),
        ("framesMap",                       FrameIndexLookup),
        )
    
    _graphics_attributes_ = (
        ("scansCursors",                    dict, Cursor),
        ("scansRois",                       dict, PlanarGraphics),
        ("scanTrajectory",                  (PlanarGraphics, type(None))),
        ("sceneCursors",                    dict, Cursor),
        ("sceneRois",                       dict, PlanarGraphics),
        )
    
    _metadata_attributes_ = (
        ("analysisUnits",                   set, AnalysisUnit),
        ("analysisUnit",                    AnalysisUnit),
        ("metadata",                        dict),
        )
    
    _option_attributes_ = (
        ("analysisOptions",                 dict),
        ("analysisMode",                    ScanDataAnalysisMode.frame),
        ("type",                            ScanDataType.linescan),
        )
    
    _descriptor_attributes_= _data_children_ + _derived_data_children_ + _result_data_ + _data_attributes_ + _graphics_attributes_ +_metadata_attributes_ + _option_attributes_ + BaseScipyenData._descriptor_attributes_
    
    def _get_data_child_component_(self, component:str):
        """
        Parameters:
        ==========
        component: str, one of: "scans", "scene", "electrophysiology"
        
        """
        if component not in (a[0] for a in self._data_children_):
            raise ValueError(f"Unknown data child component: {component}")
        
        return getattr(self, component, None)
    
    def _get_component_nFrames_(self, component:str):
        """Returns the number of data frames in one of the data components.
        
        Parameters:
        ==========
        component: str, one of "scene", "scans", "electrophysiology" 
                    (case-sensitive)
        """
        
        # NOTE: 2022-01-12 09:05:32
        # * for a neo.Block, return the number of segments
        # * for a VigraArray, return the size along its 'frames' axis defined
        # in the '<component_name>Layout' property of the ScanData object, with
        # 'component_name' being one of ('scene' , 'scans')
        #
        #   in the VigraArray case I use the 'nFrames' member of the layout 
        #   directly, if available, otherwise I calculate it using frameAxis 
        #   (as is it done below) and use the opportunity update the '<component_name>Layout'.
        
        data = self._get_data_child_component_(component)
        if isinstance(data, neo.Block):
            return len(data.segments)
        
        else:
            if isinstance(data, (tuple, list)): # scene or scans
                if len(data) == 0:
                    return 0
                layout = getattr(self, f"{component}Layout", None)
                if not isinstance(layout, dict):
                    layout = self.ImageParser(owner=self, fieldname=component).parseImageData(data)
                    
                nFrames = layout.get("nFrames", 0)
                return nFrames if isinstance(nFrames, int) else np.prod(nFrames)
            
    def __reduce__(self):
        kw = dict((d[0], getattr(self, d[0], None)) for d in self._descriptor_attributes_ if d[0] not in ("scene", "scans", "electrophysiology", "metadata"))
        
        return (_new_ScanData, (self.scans, self.scene, self.electrophysiology, 
                                self.metadata, kw))
            
    @safeWrapper
    def __init__(self, scans=None, scene=None, electrophysiology=None, metadata=None, **kwargs):
        """Constructs a ScanData object.
        
        Named parameters:
        =================
        
        For the name and value type of the expected parameters, see
        ScanData._descriptor_attributes_
        
        The description of the more important ones is given below.
        
        scans: a vigra.VigraArray or a list of vigra.VigraArray ojects, or None.
        
            When a the VigraArray, scans may contain more than one channel
                (multi-band array).
                
            When a sequence of VigraArrays, each VigraArray in the list MUST be
                single-band (corresponding to a single channel)
                
            Frames are automatically defined as array slices along the highest
            non-channel axis (or dimension), but this axis can be specified/overridden
            using "sceneFrameAxis" parameter (see below).
            
            Represents the "scene" where an imaging experiment took place (e.g.
            where a scanline trajectory or a set or imaging ROIs were defined
            for linescanning or multi-ROI imaging, respectively).
            
        scene: similar to "scans", this can be either one (possibly, multi-band) 
            VigraArray, or a list of single-band VigraArray objects, or None.
            
            In either case, the data layout must be resolve to a number of "frames"
            (possibly just one) along a non-channel axis.
            
            The frames can be:
                
            a) linescan frames (e.g. repetitions of a linescanning acquisition)
            
            b) raster scanning frames (for Z- or T-series)
            
        The frames in scans and scene are typically defined along the non-channel
            axis of the highest order of the image VigraArray. This can be 
            overridden using 'scansFrameAxis' and 'sceneFrameAxis'
            parameter (see below).
            
            The data in "scans" is the main subject for further analysis.
            
        metadata: a dictionary or DataBag with various parameters that determine
            what kind of imaging experiment is being stored in this object
            
            TODO elaborate documentation here.
            
            
        electrophysiology: a neo.Block containing associated electrophysiology data. It should
            contain as many segments as there are frames in "scans".
            
        sceneFrameAxis, scansFrameAxis: vigra.AxisInfo objects along which slices 
            of scene and scans arrays are taken as "frames";
            optional (default is None); when omitted, the frame axes will be 
            guessed from the image axistags
            
        name: str: object name for book keeping
        
        analysisOptions: DataBag; optional default is None
        
        framesMap: FrameIndexLookup; optional default is None

        triggers: either the string "auto", or None, or a list of TriggerProtocol 
            objects
            
            When "auto", try to "parse" TriggerProtocol from ephys neo.Block data.
                
        """
        
        if isinstance(scans, ScanData):
            self = scans.copy() # make a deep copy
            return
            
        self._availableGenotypes_ = [s for s in GENOTYPES]
        self._availableUnitTypes_ = [s for s in UnitTypes.values()]
        self._availableUnitTypes_.insert(0, "unknown")
        
        self._metadata_ = None
        self._modified_ = False
        
        self._processed_ = False
        
        self._scans_parser_ = self.ImageParser(self, "scans")
        self._scene_parser_ = self.ImageParser(self, "scene")
        
        # parse parameters, check images, frame axes & calibrations, electrophys.
        # and metadata --> populate kwargs and let super().init populate self
        # with everything else

        self._preset_hooks_ = {
            "scans": self._scans_parser_,
            "scene": self._scene_parser_,
            }
            
        self._postset_hooks_ = {
            "scans": self.FramesMapUpdater(self, "scans"),
            "scene": self.FramesMapUpdater(self, "scene"),
            "electrophysiology": self.FramesMapUpdater(self, "electrophysiology"),
            "metadata": self._parse_metadata_,
            }
    
        sceneLayout = kwargs.pop("sceneLayout", None)
        sceneFrameAxis = None if not isinstance(sceneLayout, dict) else sceneLayout.get("sceneFrameAxis", None)
        sceneAxesCalibration = kwargs.pop("sceneAxesCalibration", None)
        
        scansLayout = kwargs.pop("scansLayout", None)
        scansFrameAxis = None if not isinstance(scansLayout, dict) else scansLayout.get("scansFrameAxis", None)
        scansAxesCalibration = kwargs.pop("scansAxesCalibration", None)
        
        scene, scene_layout, scene_axes_cal = self._scene_parser_.imageDataLayout(scene, 
                                                                   frameAxis = sceneFrameAxis, 
                                                                   axescal = sceneAxesCalibration)
        
        scans, scans_layout, scans_axes_cal = self._scans_parser_.imageDataLayout(scans, 
                                                                   frameAxis = scansFrameAxis, 
                                                                   axescal = scansAxesCalibration)
        
        kwargs["scene"] = scene
        kwargs["sceneLayout"] = scene_layout if sceneLayout is None else sceneLayout
        kwargs["sceneAxesCalibration"] = scene_axes_cal if sceneAxesCalibration is None else sceneAxesCalibration
        
        kwargs["scans"] = scans
        kwargs["scansLayout"] = scans_layout if scansLayout is None else scansLayout
        kwargs["scansAxesCalibration"] = scans_axes_cal if scansAxesCalibration is None else scansAxesCalibration
        
        kwargs["electrophysiology"] = electrophysiology
        kwargs["metadata"] = metadata
        
        field_frames = dict((c[0], 0) for c in self._data_children_)
        for c in field_frames:
            if c in ("scene","scans"):
                layout = kwargs.get(f"{c}Layout", None)
                f = layout.get("nFrames", 0) if isinstance(layout, dict) else 0
                val = f if isinstance(f, int) else np.prod(f)
                
            else:
                val = len(kwargs[c].segments) if isinstance(kwargs[c], neo.Block) else 0
                
            field_frames[c] = val
            
        # NOTE: 2022-01-04 16:05:12 
        # FrameIndexLookup ALWAYS in use
        framesLookup = FrameIndexLookup(field_frames)
            
        # the user may have supplied a frame index lookup to the initializer
        framesMap = kwargs.pop("framesMap", framesLookup)
        
        kwargs["framesMap"] = framesMap
            
        # NOTE: the following sets up descriptors using the default 
        # setup_descriptor :class: method inherited from prog.WithDescriptors
        # 
        super().__init__(**kwargs) # BaseScipyenData/WithDescriptors

        # NOTE: 2022-01-02 23:22:32
        # metadata now set via the descriptor mechanism (WithDescriptors) in
        # super().__init__(**kwargs) above
        self._parse_metadata_()
        
        self._modified_ = False
        
    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text(f"{self.__class__.__name__} {self.name}")
        else:
            p.text(f"{self.__class__.__name__} {self.name}")
            p.breakable()
            p.text("With components:\n")
            for c in ("scene", "scans", "electrophysiology"):
                attr = getattr(self, c)
                frames = getattr(self, f"{c}Frames")
                if isinstance(attr, neo.Block):
                    p.text(f"\t{c} with {frames} segments")
                else:
                    channels = getattr(self, f"{c}Channels")
                    p.text(f"\t{c} with {frames} frames and {channels} channels: ")
                    with p.group(8, "(", ")"):
                        for idx, chn in enumerate(getattr(self, f"{c}ChannelNames")):
                            if idx:
                                p.text(",")
                                p.breakable()
                            p.pretty(chn)
                    
                p.breakable()
                
            p.text("\n")
            p.text("With frames map:")
            p.breakable()
            p.pretty(self.framesMap)
            p.text("\n")
            
            p.text("\n")
            p.text("With trigger protocols:")
            p.breakable()
            p.pretty(self.triggers)
            
            if len(self.analysisUnits):
                for a in self.analysisUnits:
                    p.pretty(a)
                    
            elif self.analysisUnit is not None:
                p.pretty(self.analysisUnit)
                
            
    
    def __str__(self):
        """
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray

        """
        result = list()
        result.append("%s: " % self.__class__.__name__)
        result.append("Name: %s;" % self.name)
        result.append("Type: %s;" % self.scanType.name)
        result.append("Analysis mode: %s;" % self.analysisMode.name)
        result.append("Scene channels: %s;" % str(self.sceneChannelNames))
        result.append("Scene frames: %d;" % self.sceneFrames)
        result.append("Scene frame axis: %s;" % self.sceneFrameAxis)
        result.append("Scans channels: %s;" % str(self.scansChannelNames))
        result.append("Scans frames: %d;" % self.scansFrames)
        result.append("Scans frame axis: %s;" % self.scansFrameAxis)
        
        if len(self.triggerProtocols):
            protocol_names = [p.name for p in self.triggerProtocols]
            result.append("Protocols: %s" % (", ".join(protocol_names)))
            
        result.append("Analysis unit (based on entire data):\n%s;" % self.analysisUnit())
        
        if len(self.analysisUnits):
            analysis_units = [a.__repr__() for a in self.analysisUnits]
            result.append("Nested analysis units: %s;" % "; ".join(analysis_units))
            
        result.append("Annotations:")
        
        for k, v in self.annotations.items():
            result.append("%s: %s" % (str(k), str(v)))
            
        return "\n".join(result)
    
    def _set_channel_names_(self, what:str, values:tuple):
        if what not in ("scene", "scans"):
            raise ValueError(f"Cannot set channel names for {what}")
        
        image_data = getattr(self, what)
        
        if len(image_data) == 0:
            return
        
        nChannels = getattr(self, f"{what}Channels")
        
        if isinstance(image_data, (tuple, list)) and all(isinstance(i, vigra.VigraArray) for i in image_data):
            image_channels = sum(i.channels for i in image_data)
            assert(nChannels == image_channels), f"{self.name} reports {nChannels} {what} channels which is different from theactual number of image channels ({image_channels})"
            
        elif isinstance(image_data, vigra.VigraArray):
            assert(nChannels==image_data.channels), f"Mismatch between actual number of image channels ({image_data.channels}) and reported number of channels ({nChannels}) in {what}"
            
    def _set_channel_name_(self, what:str, channel:int, value:typing.Optional[str]=None):
        if what not in ("scene", "scans"):
            raise ValueError(f"Cannot set channel names for {what}")
        
        image_data = getattr(self, what)
        
        if len(image_data) == 0:
            return
        
        nChannels = getattr(self, f"{what}Channels")
        
        if not isinstance(channel, int) or channel < 0 or channel >= nChannels:
            raise ValueError(f"Incompatible channel number {channel}")
        
        if len(image_data) == 1:
            axcal = getattr(self, f"{what}AxesCalibration")[0]
            axcal["c"].setChannelName(channel, value)
            axcal.calibrateAxis(image_data[0].axistags["c"])
            
        else:
            axcal = getattr(self, f"{what}AxesCalibration")[channel]
            axcal["c"].setChannelName(0, value)
    
    #@safeWrapper
    def _parse_image_arrays_(self, scene, scans, sceneFrameAxis=None, scansFrameAxis=None):
        """Assigns image data to the scene and scans data sets.
        CAUTION: Also resets all the data derived or associated with the image
        data:
        * associated: 
            all PlanarGraphics objects
            
        * derived: 
            _scene_block_, _scans_block_, __scanline_profiles_scans__, __scanline_profiles_scene__
        
        This is because assigning new image data will invalidate all derived/
        associated data based on original image data.
        
        FIXME/TODO 
        0) but don't do that in the initializer - it will clear cursors, etc set
        # by __init__
        1) adapt to a new scenario where all scene image data is a single  multi-channel VigraArray

        """
        new_scene, scene_frame_axis, scene_axes_calibrations = self.imageDataLayout(scene, frameAxis=sceneFrameAxis)
        
        #print(new_scene)
        new_scans, scans_frame_axis, scans_axes_calibrations = self.imageDataLayout(scans, frameAxis=scansFrameAxis)

        if new_scene is not None:
            self.sceneCursors.clear()
            self.sceneRois.clear()
            self.scanTrajectory = None
            self.scene = new_scene
            self.sceneFrameAxis = scene_frame_axis
            self.sceneAxesCalibration = scene_axes_calibrations

        if new_scans is not None:
            self.scansCursors.clear()
            self.scanCursors.clear()
            self.analysisUnits.clear()
            self.scans = new_scans
            self.scansFrameAxis = scans_frame_axis
            self.scansAxesCalibrations = scans_axes_calibrations
            
        #if new_scene is not None:
            #self._scenecursors_.clear()
            #self._scenerois_.clear()
            #self._scan_region_ = None
            #self._scene_ = new_scene
            #self._scene_frame_axis_ = scene_frame_axis
            #self._scene_axes_calibrations_ = scene_axes_calibrations

        #if new_scans is not None:
            #self._scanscursors_.clear()
            #self._scansrois_.clear()
            #self._analysis_units_.clear()
            #self._scans_ = new_scans
            #self._scans_frame_axis_ = scans_frame_axis
            #self._scans_axes_calibrations_ = scans_axes_calibrations
        
    @safeWrapper
    def _parse_metadata_(self):
        """Sets up analysis type
        """
        from gui import pictgui as pgui
        from systems.PrairieView import PVSequenceType
        # NOTE: 2022-01-04 17:15:31
        # self.metadata is assigned via the descriptor protocol 
        # (see ScanData.__init__())
        if self.metadata is None or len(self.metadata) == 0:
            return
        
        # NOTE: 2017-11-15 12:06:36
        # TODO adapt this for scanimage metadata as well !
        #
        # NOTE: 2018-05-19 12:04:20
        # there can be only one scene ROI that defines the scans sub-area (or 
        # scan line trajectory) in the scene, for any given ScanData object
        # this is stored as the self._scan_region_ attribute!
        # and is DISTINCT from any of the sceneRois or sceneCursors!
        
        value = self.metadata # save some replacing
        
        if isinstance(value, DataBag) and hasattr(value, "type"):
            if value.type == "PVScan":
                if value.sequences[0].attributes.sequencetype == PVSequenceType.Linescan:
                    self.analysisMode = ScanData.ScanDataAnalysisMode.frame
                    self.type = ScanData.ScanDataType.linescan

                    roi = pgui.Path(*value.sequences[0].definition.coordinates)
                    
                    if roi.type.name in ("line", "polyline", "arc", "quad", "cubic") or\
                        (roi.type.name == "path" and not roi.closed): 
                        roi.name = "scanline"
                    
                    else:
                        roi.name = "scanregion"
                        
                    self.scanTrajectory = roi
                        
            else: 
                raise NotImplementedError("%s data not yet supported" % value.type)
            
        else:
            raise TypeError("metadata was expected to be a DataBag or None; got %s instead" % type(self._metadata_).__name__)
        
    def embedTriggerEvents(self, tp=None, to_imaging=True):
        """
        # NOTE: 2017-12-20 22:06:48
        # because of imagingDelay, events in the _scans_block_ start at different
        # times from the times recorded for the electrophysiology block
        # when pasing the protocol from electrophysiology to imaging block these 
        # event times need to be adjusted (by subtracting the value of imaging-delay)
        # 
        # conversely, when passing events from the imaging block to the 
        # electrophysiology the imaging delay must again be taken into account, 
        # therefore in the imaging block, imagingDelay must have opposite sign
        # to that of the electrophysiology block
        
        # clear events first; if self.triggerProtocols is empty, then there is no
        # protocol to pass on so existing events should be wiped out
        
        Keyword parameters:
        ==================
        tp: a sequence of TriggerProtocol objects, or None
            When None, uses own list of trigger protocols
        
        to_imaging: boolean, default True
            
            When True (default) embeds protocol events into the 
                scansBlock and/or sceneBlock
                
            When False, embeds protocol events into the electrophysiology
                block
        """
        
        if tp is None:
            tp = self.triggerProtocols
            
        elif isinstance(tp, TriggerProtocol):
            tp = [tp]
            
        elif isinstance(tp, (tuple, list)) and all([isinstance(p, TriggerProtocol) for p in tp]):
            pass
        
        else:
            raise TypeError("Expecting a TriggerProtocol, a sequence of TriggerProtocol objects or None; got %s instead" % (type(tp).__name__))
            
        if len(tp):
            for p in tp:
                rev_p = p.reverseAcquisition(copy=True)
                if isinstance(self._electrophysiology_, neo.Block) and len(self._electrophysiology_.segments):
                    embed_trigger_protocol(p, self._electrophysiology_)
                    
                if isinstance(self._scans_block_, neo.Block) and len(self._scans_block_.segments):
                    embed_trigger_protocol(rev_p, self._scans_block_)
                    
                if isinstance(self._scene_block_, neo.Block) and len(self._scene_block_.segments):
                    embed_trigger_protocol(rev_p, self._scene_block_)
                
    @safeWrapper
    def validateElectrophysiology(self, value):
        """Validates new electrophysiology data and proposes frames lookup.
        
        Use case 1: When value is a neo.Block, the assignment is by reference.
        
        Use case 2: When value is a sequence of segments, the 'segments' 
        attribute (a list) of self._electrophysiology_ is populated with the new
        segments - hence it will store references to the new segments.
        
        WARNING Because self._electrophysiology_ is a 'reference' to a neo.Block
        object possibly present somewhere else, use case 2 will also modify the
        original neo.Block object. The only way to circumvent this effect (short
        of storing a deep copy of the neo.Block here) is to delete the original
        e.g. by using the 'del' statement. In python, the 'del' statement does
        NOT remove the obkect itself from memory; instead it breaks the link between the
        object and its symbol in a given namespace.
        
        ATTENTION Does NOT read trigger events from value. These are handled
        separately.
        
        """
        # NOTE: 2017-12-15 22:51:41
        # Trigger events handled elsewhere
        
        if isinstance(value, neo.Block): 
            if len(value.segments) != self.scansFrames:
                if len(value.segments) == 1:
                    value.segments *= self.scansFrames
                else:
                    warnings.warn("Expecting a neo.Block with as many segments as there are scan frames (%d); got %d segments instead" \
                        % (self.scansFrames, len(value.segments)), RuntimeWarning)
                    return
            
            self._electrophysiology_ = value # assigns reference
            
        elif isinstance(value, (tuple, list)) and all([isinstance(v, neo.Segment) for v in value]):
            # set it up from a sequence of neo.Segments
            if len(value) != self.scansFrames:
                if len(value) ==1:
                    value *= self.scansFrames
                else:
                    warnings.warn("Expecting as many segments as there are scan frames (%d); got %d instead" \
                        % (self.scansFrames, len(values)), RuntimeWarning)
                    
                    return
            
            self._electrophysiology_.segments[:] = [s for s in value]
            
            for k, s in enumerate(self._electrophysiology_.segments):
                s.index = k
                
                if s.name is None:
                    s.name = "Frame_%d" % s.index
                    
        elif isinstance(value, neo.Segment):
            if self.scansFrames > 1:
                value = [value] * self.scansFrames
                
            else:
                raise TypeError("Expecting as many segments as there are scan frames (%d); got 1 neo.Segment instead" \
                    % self.scansFrames)
                
            self._electrophysiology_.segments[:] = [value]
            
            for k, s in enumerate(self._electrophysiology_.segments):
                s.index = k
                
                if s.name is None:
                    s.name = "Frame_%d" % s.index
                    
        elif value is None:
            return
                    
        else:
            raise TypeError("Expecting one of: a neo.Block, a sequence of neo.Segment objects, a neo.Segment or None; got %s instead" % (type(value).__name__))
        
        # NOTE: the statement below does nothing, as the "src" is the actual
        # electrophysiology data embedded here
        self.adoptTriggerProtocols(self.electrophysiology)
        
    def _concatenate_image_data_(self, other, scene=True, pad_value=None):
        """
        Concatenates scene or scans images along the frame axis
        
        other: ScanData object
        scene: boolean (default is True); when False, concatenates scans images
        
        pad_value: None, float or np.nan: How to treat different image shapes 
            after resampling prior to concatenation:
            
        Theoretically, when concatenating the image data, the images should 
        ideally have identical shapes except along the concatenation axis. 
        In addition, the non-concatenation axes should, also have the same 
        calibration (units, origin and resolution).
        
        However, it may be possible that the same structure or signal may have been 
        sampled with different space and/o time resolution across successive runs
        within the same experiment. 
        
        While this is NOT ideal and it should be avoided, some laser scanning 
        software may allow this -- e.g. PrairieView which allows 1D scanning along
        a freehand line drawn in the scene. In such scenario, small drifts occcurring
        in the scanned structures between repeated linescan runs may prompt the 
        user to "redraw" the freehand line before the next linescan is acquired. 
        This will almost certainly result in a linescan image with different spatial
        and/or temporal resolution from the previously acquired one, especially if
        one of the linescan parameters is kept constant (e.g., image width,
        number of line sweeps, or pixel dwell time, etc).
        
        For this reason, we allow concatenation of successive linescan images 
        with different axial resolutions and/or size along the non-concatenation 
        axes, by resampling the "other" image array to bring its axial resolutions
        to the value of those of the recipient image array.
        
        One side effect is that the resampled image will alsomot surely have a 
        different size along the resampled axes, hence it would have to be cropped
        or padded, according to the sign of the change in size.
        
        To keep things simple, padding will append new values at the end along 
        the resampled axis, while cropping will remove samples from the end of 
        resampled axis.
        
        Whe padding, the choice of the value used for padding DOES matter. There
        are four options for the pad_value:
        
        1) np.nan - this will NOT add values to the signal (np.nan are placeholders
        for values that are not numbers)
        
            Pros:
                this is acceptable when the intention is to generate new data 
                using acumulator functions that calculate a statistical moment 
                from the data, along the concatenated axis; example: the average,
                as the new np.nan values will not contribute otwards the average (in 
                this example, this is achieved by using np.namean instead of np.mean).
            
            Cons:
                however, this is not acceptable when data processing algorithms 
                that do not expect nan values in the data arrays are employed 
                (basically, all signal processing filters)
            
        2) a float value - this introduces new values into the signal, effectively
            changing it
            
            Pros:
                may be acceptable for signal processing algorithms that do not 
                expect nan values
                
            Cons:
                introduces new values therefore not acceptable for either 
                acumulator functions or signal processing functions that operate 
                on a neighborhood (ie. not point-wise)
                
        3) "rep" - this keyword indicates padding with a replica of the data
            A bit more tricky to implement, goes some way to alleviate the problems
            with padding using a float value
            
        4)  None: avoid padding altogether: always crop the image where the axis
            is larger
            
            Pros:
                avoid any of the padding-related issues above
                
            Cons: 
                drops values of the signal -- depending on what is being 
                concatenated the result may lose significant segments of the 
                useful signal.
        
        
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        """
        
        #print("ScanData._concatenate_image_data_\nself: %s\nother: %s" % (self.name, other.name))

        if not isinstance(other, ScanData):
            raise TypeError("Expecting a ScanData object; got %s instead" % type(other).__name__)
        
        if scene:
            own = self.scene
            tgt = other.scene
            channels = self.sceneChannels
            channelNames = self.sceneChannelNames
            src_channels = other.sceneChannels
            src_channelNames = other.sceneChannelNames
            frameAxis = self.sceneFrameAxis
            src_frameAxis = other.sceneFrameAxis
            frameAxisIndex = self.sceneFrameAxisIndex
            src_frameAxisIndex = other.sceneFrameAxisIndex
            
            which_data = "scene"
            
        else:
            own = self.scans
            tgt = other.scans
            channels = self.scansChannels
            channelNames = self.scansChannelNames
            src_channels = other.scansChannels
            src_channelNames = other.scansChannelNames
            frameAxis = self.scansFrameAxis
            src_frameAxis = other.scansFrameAxis
            frameAxisIndex = self.scansFrameAxisIndex
            src_frameAxisIndex = other.scansFrameAxisIndex
            
            which_data = "scans"
        
        if len(own) != len(tgt):
            raise ValueError("Incompatible %s layout: expecting %d elements; got %d" % (which_data, len(own), len(tgt)))
        
        if channels != src_channels:
            raise ValueError("Different number of channels in %s" % which_data)
        
        if channelNames != src_channelNames:
            raise ValueError("Different channel names in %s" % which_data)
        
        if frameAxis != src_frameAxis:
            raise ValueError("Different frame axis in %s" % which_data)
        
        if frameAxisIndex != src_frameAxisIndex:
            raise ValueError("Frame axis is associated with different dimensions in %s" % which_data)
        
        result = list()
        
        if scene:
            for k, img in enumerate(own):
                result.append(concatenateImages(img, tgt[k], axis=frameAxis, ignore=["origin", "resolution"]))
            
            
        else:
            # NOTE: 2018-09-18 20:50:12
            # padding with nan generates numerical problems for denoising algorithms
            # padding with 0 generates signal processing problems as it introduces 0s
            # in the signal
            # therefore, after resampling, we must ALWAYS CROP to the smallest shape
            # with the caveat that this would eventually reduce the useful signal
            # the other possibility is to pad with nans, avoid denoising, then denoise on
            # averaged data 
            for k, img in enumerate(own):
                # NOTE: 2018-09-18 21:37:52
                # img0 is the receiver  (we concatenate TO)
                # img1 is the source    (we concatenate img1 TO img0)
                img0 = img.copy()
                img1 = tgt[k].copy()
                
                img0_axis_cals = AxesCalibration(img0)
                img1_axis_cals = AxesCalibration(img1)
                
                if img0_axis_cals.getDimensionlessResolution("x") != img1_axis_cals.getDimensionlessResolution("x"):
                    img1 = resampleImage(img1, img0, axis = "x")
                    
                if img0_axis_cals.getDimensionlessResolution("t") != img1_axis_cals.getDimensionlessResolution("t"):
                    img1 = resampleImage(img1, img0, axis="t")
                    
                # NOTE: 2018-09-18 21:37:47
                # img1 is resampled - the size along the non-concatenating
                # axes will almost surely have changed
                
                # NOTE: resampled image has a longer axis that img0 => crop it
                if img1.shape[img1.axistags.index("x")] > img0.shape[img0.axistags.index("x")]:
                    img1 = croppedView(img1, {"x": img0.shape[img0.axistags.index("x")]})

                # NOTE: resampled image has a shorter axis than img0 ; pad accoridng to pad_value
                elif img1.shape[img1.axistags.index("x")] < img0.shape[img0.axistags.index("x")]:
                    if pad_value is None:
                        # crop the receiver (img0)
                        img0 = croppedView(img0, {"x": img1.shape[img1.axistags.index("x")]})
                        own[k] = img0
                        
                    elif isinstance(pad_value, float): # this includes np.nan; pad with value
                        d = img0.shape[img0.axistags.index("x")] - img1.shape[img1.axistags.index("x")]
                        img1 = padAxis(img1, img1.axistags.index("x"), 0, d, pad_value)
                        #img1 = padToShape(img1, img0.shape, keep_axis = frameAxisIndex) # NOTE: 2018-09-18 18:13:20 pad with 0 (default)
                        #img1 = padToShape(img1, img0.shape, pad = pad_value, keep_axis = frameAxisIndex)
                        
                    elif isinstance(pad_value, str) and pad_value.lower().strip() == "rep": # pad with replication
                        d = img0.shape[img0.axistags.index("x")] - img1.shape[img1.axistags.index("x")]
                        img1 = padAxis(img1, img1.axistags.index("x"), 0, d, None)
                        
                    else:
                        raise ValueError("invalid pad_value %s" % pad_value)
                        # replicate
                    
                if img1.shape[img1.axistags.index("t")] > img0.shape[img0.axistags.index("t")]:
                    img1 = croppedView(img1, {"t": img0.shape[img0.axistags.index("t")]})
                                                                
                elif img1.shape[img1.axistags.index("t")] < img0.shape[img0.axistags.index("t")]:
                    if pad_value is None:
                        img0 = croppedView(img0, {"t": img1.shape[img1.axistags.index("t")]})
                        
                    elif isinstance(pad_value, float):# this includes np.nan
                        d = img0.shape[img0.axistags.index("t")] - img1.shape[img1.axistags.index("t")]
                        img1 = padAxis(img1, img1.axistags.index("t"), 0, d, pad_value)
                        
                    elif isinstance(pad_value, str) and pad_value.lower().strip() == "rep":
                        d = img0.shape[img0.axistags.index("t")] - img1.shape[img1.axistags.index("t")]
                        img1 = padAxis(img1, img1.axistags.index("t"), 0, d, None)
                        
                    else:
                        raise ValueError("invalid pad_value %s" % pad_value)
                        
                result.append(concatenateImages(img0, img1, axis = frameAxis, ignore=["origin", "resolution"]))
                
        return result
    
    # ###
        # public functions
        # ###
        
    @safeWrapper
    def copy(self):
        """
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        import copy
        from gui import pictgui as pgui

        from functools import partial as partial
        
        new_scene = [img.copy() for img in self.scene]
        new_scans = [img.copy() for img in self.scans]
        
        
        # FIXME -- WHAT'S WRONG???? this is a reference; 
        # deepcopy "slices" the events into quantities
        # if it is a reference, any modifications in the copy will also touch the
        # original !
        ephys = copy.deepcopy(self.electrophysiology)
        #ephys = neo_copy(self.electrophysiology)
        
        analysisOptions = copy.deepcopy(self.analysisOptions)
        
        result = ScanData(scene = new_scene,
                          scans = new_scans,
                          name = copy.deepcopy(self.name),
                          sceneFrameAxis = copy.deepcopy(self.sceneFrameAxis),
                          scansFrameAxis = copy.deepcopy(self.scansFrameAxis),
                          electrophysiology = ephys,
                          analysisOptions = analysisOptions)
        
        # MUST reassign triggerProtocols because the constructor above tries to 
        # parse the trigger events in electrophysiology which might result in 
        # name clashes
        
        # object containers
        if hasattr(self, "_scene_filters_"): # old API
            result._scene_filters_ = copy.deepcopy(self._scene_filters_)
            result._scans_filters_ = copy.deepcopy(self._scans_filters_)
        
        # neo.Block does not have a copy() method so we need to use our own
        result._scene_block_ = copy.deepcopy(self._scene_block_)
        result._scans_block_ = copy.deepcopy(self._scans_block_)
        #result._scene_block_ = neo_copy(self._scene_block_)
        #result._scans_block_ = neo_copy(self._scans_block_)
        
        result._scan_region_scans_profiles_ = copy.deepcopy(self._scan_region_scans_profiles_)
        result._scan_region_scene_profiles_ = copy.deepcopy(self._scan_region_scene_profiles_)
        #result._scan_region_scans_profiles_ = neo_copy(self._scan_region_scans_profiles_)
        #result._scan_region_scene_profiles_ = neo_copy(self._scan_region_scene_profiles_)
        
        #result._scan_region_scans_profiles_ = copy.deepcopy(self._scan_region_scans_profiles_)
        #result._scan_region_scene_profiles_ = copy.deepcopy(self._scan_region_scene_profiles_)
        
        if isinstance(self._scan_region_, PlanarGraphics):
            result._scan_region_ = self._scan_region_.copy()
        
        result._scenerois_.clear()
        result._scenecursors_.clear()
        result._scansrois_.clear()
        result._scanscursors_.clear()
        
        skip_objects = list()
        
        #### BEGIN copy planar graphics
        # dealing with linked cursors:
        # if copied object has links to other objects,
        # copy those objects directly to their corresponding dictionary
        # then manually create a link between this copy and the copies of the 
        # objects the original is linked to
        # also append the newly linked objects to the list of skipped objects
        # so that we don't duplicate them (or enter an infinite loop)
        
        for d, target in zip((self._scenerois_, self._scansrois_, self._scenecursors_, self._scanscursors_),
                             (result._scenerois_, result._scansrois_, result._scenecursors_, result._scanscursors_)):

            new_objects = dict()
            
            for k, i in d.items(): # does nothing if dict is empty
                obj = i.copy()
                
                if isinstance(result._scan_region_, PlanarGraphics):
                    cc_links = [(c, l) for (c,l) in i.objectLinks.items()]
                    for c, link in cc_links:
                        # see NOTE: 2018-07-02 08:36:58
                        if c != i:# technically this should not be linked to itself
                            cc = c.copy() # copy of the object we're linking TO
                            
                            # place this copy into the appropriate dictionary
                            if c in self._scansrois_.values():
                                result._scansrois_[cc.name] = cc
                                
                            elif c in self._scenerois_.values():
                                result._scenerois_[cc.name] = cc
                                
                            elif c in self._scanscursors_.values():
                                result._scanscursors_[cc.name] = cc
                                
                            elif c in self._scenecursors_.values():
                                result._scenecursors_[cc.name] = cc
                                
                            skip_objects.append(cc) # keep track of this so we don't add it again below
                                
                            pf = link[0]
                            
                            obj.linkToObject(cc, pf.func, result._scan_region_)
                        
                if obj not in skip_objects:
                    new_objects[k] = obj
                
            target.update(new_objects)
            
        #### END copy planar graphics
        
        #### BEGIN copy analysis units
        result._analysis_units_.clear
        
        self_units = self.analysisUnits # these are ALL landmark-based
        
        for unit in self_units:
            if result.hasSceneLandmark(unit.landmark):
                if isinstance(unit.landmark, pgui.Cursor):
                    landmark = result.sceneCursors[unit.landmark.name]
                    
                else:
                    landmark = result.sceneRois[unit.landmark.name]
                    
            elif result.hasScansLandmark(unit.landmark):
                if isinstance(unit.landmark, pgui.Cursor):
                    landmark = result.scansCursors[unit.landmark.name]
                    
                else:
                    landmark = result.scansRois[unit.landmark.name]
                    
            else:
                landmark = None
                
            if landmark is not None:
                analysis_unit = AnalysisUnit(result, landmark=landmark,
                                             protocols = unit.protocols,
                                             unit_type = unit.unit_type,
                                             cell = unit.cell,
                                             field = unit.field,
                                             scene = unit.inScene,
                                             **unit.descriptors)
                
                result.age      = unit.age
                result.genotype = unit.genotype
                result.gender   = unit.gender
                result.sourceID = unit.sourceID
                
                result._analysis_units_.add(analysis_unit)
        
        # NOTE: 2018-06-23 09:15:55
        # this is about the data-wide analysis unit (NOT landmark-based)
        for d in self._analysis_unit_.descriptors:
            result._analysis_unit_.setDescriptor(d, self._analysis_unit_.descriptors[d])
            
        result._analysis_unit_.cell = self._analysis_unit_.cell
        result._analysis_unit_.field = self._analysis_unit_.field
        result._analysis_unit_.age = self._analysis_unit_.age
        result._analysis_unit_.genotype = self._analysis_unit_.genotype
        result._analysis_unit_.gender= self._analysis_unit_.gender
        result._analysis_unit_.inScene= self._analysis_unit_.inScene
        result._analysis_unit_.sourceID = self._analysis_unit_.sourceID
        result._analysis_unit_.parent = self
            
        # POD types
        result._scene_frame_axis_ = self._scene_frame_axis_
        result._scans_frame_axis_ = self._scans_frame_axis_
        
        result._analysismode_ = self._analysismode_
        
        result._scandatatype_ = self._scandatatype_
        
        result._modified_ = self._modified_
        
        result._processed_ = self._processed_
        
        #### END copy analysis units
        
        result.triggerProtocols = self.triggerProtocols
        
        return result
    
    def hasImageData(self, image_section):
        """Checks if this objects contains image data for the specified section.
        
        Parameters:
        ===========
        image_section: str, valid values are "scene", "scans"
        
        "scene": a list with one multi-channel image, or several single-channel 
            images for the scene of the scan.
        "scans": a list with one multi-channel image, or several single-channel 
            images for the actual image scan (linescan, raster scan, etc)
        
        """
        
        if not isinstance(image_section, str):
            raise TypeError("Expectign a str; got %s instead" % type(image_section).__name__)
        
        data = getattr(self, image_section, None)
        
        if data is None:
            return False
        
        ret = isinstance(data, (vigra.VigraArray, list))
        
        if not ret:
            return ret
        
        if isinstance(data, list):
            ret &= all((isinstance(v, vigra.VigraArray) for v in data))
            
        return ret
    
    def hasSignalData(self, data_section):
        """Checks if this object contains signals in the specified data section.
        
        Parameters:
        ===========
        
        data_section: str, valid values are explained in the following table:
        
        data_section                what is checked
        --------------------------------------------
        "electrophysiology"         self.electrophysiology type, length of segments list and length of signals in each segment
        
        "ephys" -- alias for "electrophysiology"
        
        "scansProfiles"             self.scanRegionScansProfiles
        
        "sceneProfiles"             self.scanRegionSceneProfiles
        
        "scansBlock"                self.scansBlock
        
        "sceneBlock"                self.sceneBlock
        
        Returns:
        --------
        
        True if the following are satisfied:
        
            1) data_section is an instance of neo.Block
            2) len(data_section.segments) > 0
            3) There is at least one segment in data_section where
                len(analogsignals) > 0 or len(irregularlysampledsignals) > 0
        """
        
        if not isinstance(data_section, str):
            raise TypeError("expecting a str; got %s instead" % type(data_section).__name__)
        
        test_data = getattr(self, data_section, None)
        
        if test_data is None:
            return False
        
        ret = isinstance(test_data, neo.Block)
        
        if ret:
            ret &= len(test_data.segments)
            
        if ret:
            ret &= all([len(s.analogsignals) > 0 or len(s.irregularlysampledsignals) > 0 for s in test_data.segments])
            
        return ret
    
    def hasLandmark(self, landmark):
        """Returns False if self.locateLandmark(landmark) is None
        """
        from gui import pictgui as pgui

        if not isinstance(landmark, PlanarGraphics):
            raise TypeError("Expecting a pictgui.PlanarGraphics object; got %s instead" % type(landmark).__name__)
        
        return (self.locateLandmark(landmark)) is not None
    
    def hasSceneLandmark(self, landmark):
        """Checks that landmark in self.sceneCursors or self.sceneRois.
        Landmark lookup is performed by name and type.
        
        See self.locateLandmark for details.
        
        """
        from gui import pictgui as pgui
        
        if not isinstance(landmark, PlanarGraphics):
            raise TypeError("Expecting a pictgui.PlanarGraphics object; got %s instead" % type(landmark).__name__)
        
        if isinstance(landmark, pgui.Cursor):
            return landmark.name in self.sceneCursors and self.sceneCursors[landmark.name].type == landmark.type
    
        else:
            return landmark.name in self.sceneRois and self.sceneRois[landmark.name].type == landmark.type
        
    def hasScansLandmark(self, landmark):
        from gui import pictgui as pgui

        if not isinstance(landmark, PlanarGraphics):
            raise TypeError("Expecting a pictgui.PlanarGraphics object; got %s instead" % type(landmark).__name__)
            
        if isinstance(landmark, pgui.Cursor):
            return landmark.name in self.scansCursors and self.scansCursors[landmark.name].type == landmark.type
        
        else:
            return landmark.name in self.scansRois and self.scansRois[landmark.name] == landmark.type
        
    def locateLandmark(self, landmark):
        """Returns the dictionary it belongs to).
        
        This concerns the landmarks set up in the scene and scans data subsets,
        regardless of the existence of a scanRegion.
        
        The landmarks are looked up by the value of their "name" and "type" attributes.
        
        Positional parameters:
        ======================
        landmark: a pictgui.PlanarGraphics object
        
        Returns:
        =======
        
        The python dictionary that contains the landmark, a list of python 
        dictionaries containing this landmark, or None.
        
        NOTE: This function implements a "semantic" equivalence between landmarks.
        
        Landmark identity is determined by its "name" and "type" attributes,
        and thus allows for two landmark objects with the same name and type to
        have different frame-state associations and different parametric realizations.
        
        This is NOT the same thing as the two landmark objects being identical from
        a programing language point of view (i.e., they do not need to be stored 
        at the same memory address and contain the same byte information).
        
        """
        from gui import pictgui as pgui
        
        result = list()
        
        if not isinstance(landmark, PlanarGraphics):
            raise TypeError("Landmark expected to be a pictgui.PlanarGraphics; got %s instead.\n To locate a landmark by its name use self.locateLandmarkByNname()" % type(landmark).__name__)

        if isinstance(landmark, pgui.Cursor):
            landmark_dicts = [self.sceneCursors, self.scansCursors]
            
        else:
            landmark_dicts = [self.sceneRois, self.scansRois]
            
        for landmark_dict in landmark_dicts:
            if landmark.name in landmark_dict \
                and landmark_dict[landmark.name].type == landmark.type:
                result.append(landmark_dict)
                    
        # NOTE: 2018-06-22 22:51:15
        # technically, result should contain at most ONE element.
        
        if len(result) == 1:
            return result[0]
        
        elif len(result) == 0:
            return
        
        return result
        
    @safeWrapper
    def resampleSceneData(self, resolution, axis=0, down=1000):
        """Resamples Scene data along a specified axis.
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        Parameters:
        ===========
        
        resolution: scalar float or Python Quantity
        
        """
        self.scene = [resampleImageAxis(img, resolution, axis=axis, p=down) for img in self.scene]
    
    @safeWrapper
    def resampleScansData(self, resolution, axis=0, down=1000):
        """
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        self.scans = [resampleImageAxis(img, resolution, axis=axis, p=down) for img in self.scans]
    
    def updateAxesCalibrations(self):
        """Call this to keep axis calibration in sync with the image array data.
        """
        if isinstance(self.scene, vigra.VigraArray):
            self._scene_axes_calibrations_ = [AxesCalibration(self.scene)]
            
        elif isinstance(self.scene, (tuple, list)) and  len(self.scene) > 0:
            self._scene_axes_calibrations_ = [AxesCalibration(img) for img in self.scene]
            
        if isinstance(self.scans, vigra.VigraArray):
            self._scans_axes_calibrations_ = [AxesCalibration(self.scans)]
            
        elif isinstance(self.scans, (tuple, list)) and len(self.scans) > 0:
            self._scans_axes_calibrations_ = [AxesCalibration(img) for img in self.scans]
            
    #@safeWrapper
    def concatenate(self, source, strict = False, pad_value = None, scanregions=False):#, resample=False, alignment=0):#, src_slice = None, other_slice = None, axis=None):
        """Concatenates "source" to this object (the "receiver").
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        Parameters:
        ==========
        "source" : a ScanData object
        
        strict: boolean (default False); whether to be strict with respect to the
        to trigger protocol timings
        
        pad_value: None, float or np.nan (default) : value for image array padding
            before concatenating image data with different axial resolutions.
            
        NOTE: Concatenation of image arrays between two ScanData objects:
        
        Returns:
        =======
        Concatenated ScanData object
        
        """
        #from gui import pictgui as pgui

        def _increment_frame_index_(o, value):
            from gui import pictgui as pgui
            
            if isinstance(o, pgui.Path):
                for p in o:
                    _increment_frame_index_(p, value)
                    
            else:
                for s in o.states:
                    if s.z_frame is None:
                        s.z_frame = value
                        
                    else:
                        s.z_frame += value
                        
        #print("ScanData.concatenate() self copy() to result %s" % self.name )
        result = self.copy() # carries over trigger protocols in self
        
        #print("ScanData.concatenate() %s result=self.copy(): analysisMode:" % self.name, result._analysismode_)
        
        if not isinstance(source, ScanData):
            raise TypeError("Can only concatenate a ScanData object")
        
        if source._analysismode_ != result._analysismode_:
            raise ValueError("Cannot concatenate data with different analysis modes")
        
        if self._analysismode_ != ScanData.ScanDataAnalysisMode.frame:
            raise ValueError("Can only concatenate data with frame analysis mode")
        
        if source._scandatatype_ != result._scandatatype_:
            warnings.warn("Cannot concatenate data of different scan types")
        
        # check that the whole analysis unit is about the same cell and field
        # this can be easily circumvented by aligning the cell and field attributes
        analysis_unit   = result.analysisUnit()
        source_unit     = source.analysisUnit()
        
        original_scans_frames = result.scansFrames
        original_scene_frames = result.sceneFrames

        # NOTE: 2018-06-18 14:57:52
        # more elightning names for source and self when reporting errors
        # to be used instead ofs source.name and self.name in error messages
        source_name = source.name
        self_name   = result.name
        
        #print("concatenate %s with %s" % (source_name, self_name))
        #print("scene frames: source %d;  self %d" % (source.sceneFrames, self.sceneFrames))
        #print("scans frames: source %d;  self %d" % (source.scansFrames, self.scansFrames))
        #print("ephys segments: source %d; self %d" % (len(source.electrophysiology.segments), len(self.electrophysiology.segments)))
        #print("scans signals segments: source %d; self %d" % (len(source.scansBlock.segments), len(self.scansBlock.segments)))
        #print("***")
        
        if "extracted" in source.annotations:
            source_name += " from %s" % source.annotations["extracted"]["source"]
            
        if "extracted" in self.annotations:
            self_name += " from %s" % self.annotations["extracted"]["source"]
            
        #print("analysis unit cell", analysis_unit.cell, "field", analysis_unit.field,
              #"source unit cell", source_unit.cell, "source unit field", source_unit.field)
              
        if analysis_unit.cell != source_unit.cell or analysis_unit.field != source_unit.field:
            raise ValueError("Cannot concatenate data associated with different cells or fields")
        
        #print("concatenating %s to %s" % (source.name, result.name))
        
        #### BEGIN 1) concatenate scene data images
        try:
            #print("concatenating scene")
            result.scene[:] = result._concatenate_image_data_(source, scene=True, pad_value = pad_value)[:]
            #print("scene block segments %d" % len(result._scene_block_.segments))
            #print("scene profiles segments %d" % len(result._scan_region_scene_profiles_.segments))
            
            # enforce coherence between number of segments in blocks of derived data
            # and the actual number of frames
            if len(result._scene_block_.segments) < result.scansFrames:
                for k in range(len(result._scene_block_.segments), result.scansFrames):
                    result._scene_block_.segments.append(neo.Segment())
                    
            elif len(result._scene_block_.segments) > result.scansFrames:
                result._scene_block_.segments = result._scene_block_.segments[0:result.scansFrames]
            
            if len(result._scan_region_scene_profiles_.segments) < result.scansFrames:
                for k in range(len(result._scan_region_scene_profiles_.segments), result.scansFrames):
                    result._scan_region_scene_profiles_.segments.append(neo.Segment())
                    
            elif len(result._scan_region_scene_profiles_.segments) > result.scansFrames:
                result._scan_region_scene_profiles_.segments = result._scan_region_scene_profiles_.segments[0:result.scansFrames]
            
        except Exception as e:
            traceback.print_exc()
            print("when concatenating scene from %s to %s" % (source.name, result.name))
            raise e
        
        if len(result.scene) == 0 and len(result.scans) == 0:
            raise RuntimeError("ScanData %s has no scene, nor scans images!" % self_name)
        
        #### END concatenate scene data images
        
        #### BEGIN 2) concatenate scans data images
        try:
            result.scans[:] = result._concatenate_image_data_(source, scene=False, pad_value = pad_value)[:]
            
            # enforce coherence between number of segments in blocks of derived data
            # and the actual number of frames
            if len(result._scans_block_.segments) < result.scansFrames:
                for k in range(len(result._scans_block_.segments), result.scansFrames):
                    result._scans_block_.segments.append(neo.Segment())
                    
            elif len(result._scans_block_.segments) > result.scansFrames:
                result._scans_block_.segments = result._scans_block_.segments[0:result.scansFrames]
            
            if len(result._scan_region_scans_profiles_.segments) < result.scansFrames:
                for k in range(len(result._scan_region_scans_profiles_.segments), result.scansFrames):
                    result._scan_region_scans_profiles_.segments.append(neo.Segment())
                    
            elif len(result._scan_region_scans_profiles_.segments) > result.scansFrames:
                result._scan_region_scans_profiles_.segments = result._scan_region_scans_profiles_.segments[0:result.scansFrames]
            
        except Exception as e:
            traceback.print_exc()
            print("when concatenating scans from %s to %s" % (source.name, result.name))
            raise e

        #### END concatenate scans data images
        
        #### BEGIN 3) manage the scene landmarks
        # NOTE: 2018-06-17 21:42:08
        # concatenate frames for the scene landmarks (or adopt landmarks from 
        # source if not present in target) but make sure to assign correct frame
        # indices !!!
        #if len(result.scene):
            #result._scene_frames_ = result.scene[0].shape[result.scene[0].axistags.index(result.sceneFrameAxis)]
            
            # NOTE: 2018-06-17 21:42:21 
            # "merge" scan region of source with that from target
            # but only when scanregions parameter is True otherwise we may end
            # up paying a very high price (speed burden)
            
            if result.scanRegion is None:
                result.scanRegion = pgui.Path()
                    
            if scanregions:
                if source.scanRegion is None:
                    src_scan_region = pgui.Path()
                
                if isinstance(result.scanRegion, pgui.Path):
                    if len(result.scanRegion):
                        if isinstance(source.scanRegion, pgui.Path) and len(source.scanRegion):
                            src_scan_region = source.scanRegion.copy()
                            
                        elif isinstance(source.scanRegion, PlanarGraphics) and source.scanRegion.type & pgui.GraphicsObjectType.allShapeTypes:
                            src_scan_region = source.scanRegion.convertToPath()
                            
                else:
                    if isinstance(source.scanRegion, pgui.Path):
                        if len(source.scanRegion):
                            src_scan_region = source.scanRegion.copy()
                            
                        else:
                            src_scan_region = pgui.Path()
                            
                        result.scanRegion = result.scanRegion.convertToPath()
                        
                    else:
                        if source.scanRegion.type != result.scanRegion.type:
                            src_scan_region = source.scanRegion.convertToPath()
                            result.scanRegion = result.scanRegion.convertToPath()
                            
                # now, both are either pgui.Paths, or same non-path type
                
                if isinstance(result.scanRegion, pgui.Path):# implies the other is a pgui.Path as well
                    if len(result.scanRegion): 
                        max_frame = max(result.scanRegion.frameIndices)
                    
                        while isinstance(max_frame, (tuple, list)):
                            max_frame = max(max_frame)
                        
                        max_frame += 1
                        
                    else:
                        max_frame = result.scansFrames
                        
                    if len(src_scan_region):
                        for o in src_scan_region:
                            _increment_frame_index_(o, max_frame)
                            
                        result.scanRegion = result.scanRegion + src_scan_region
                            
                else: # implies both scan regions are planar grapnics of same type, but not pgui.Path
                    max_frame = max(result.scanRegion.frameIndices) + 1
                    
                    for s in src_scan_region.states:
                        if s.z_frame is None:
                            s.z_frame = max_frame
                            
                        else:
                            s.z_frame += max_frame
                            
                        result.scanRegion.states.append(s)
                        
                result.scanRegion.currentFrame = 0
                
            else:
                result.scanRegion = source.scanRegion.asPath(0)
            
            # next, "merge" source rois with target rois
            for obj in source.sceneRois.values():
                new_obj = obj.copy()
                
                new_obj.linkFrames(obj.frameIndices)

                new_frame_ndx = [f + original_scans_frames for f in obj.frameIndices]
                
                new_obj.remapFrameStateAssociations([m for m in zip(obj.frameIndices, new_frame_ndx)])
                
                if new_obj.name in result.sceneRois:
                    result.sceneRoi(new_obj.name).linkFrames(new_obj.frameIndices)
                    
                    if result.sceneRoi(new_obj.name).type != new_obj.type:
                        if not isinstance(result.sceneRoi(new_obj.name), pgui.Path):
                            result.sceneRois[new_obj.name] = result.sceneRoi(obj.name).convertToPath()
                            
                        if not isinstance(new_obj, pgui.Path):
                            new_obj = new_obj.convertToPath()
                        
                else:
                    result.sceneRois[new_obj.name] = new_obj
                
            # finally, "merge" source cursors with target cursors
            # we'll check if they are linked to scans landmarks, below
            #print(source.sceneCursors)
            
            for obj in source.sceneCursors.values():
                new_obj = obj.copy()
                
                new_obj.linkFrames(new_obj.frameIndices)

                new_frame_ndx = [f + original_scans_frames for f in obj.frameIndices]
                
                #print("source cursor: ", new_obj.name, new_frame_ndx)
                
                new_obj.remapFrameStateAssociations([m for m in zip(obj.frameIndices, new_frame_ndx)])
                    
                #print("source cursor: ", new_obj.name, new_obj.frameIndices)
                
                if new_obj.name in result.sceneCursors:
                    #print("existing cursor")
                    #print("result cursor: ", result.sceneCursor(new_obj.name).name, result.sceneCursor(new_obj.name).frameIndices)
                    #print("source cursor: ", new_obj.name, new_obj.frameIndices)
                    
                    if new_obj.type != result.sceneCursor(new_obj.name).type:
                        raise RuntimeError("Cursor name %s refers to different cursor types: %s in source data (%s) and %s in target data (%s)" % \
                            (new_obj.name, new_obj.type, source_name, result.sceneCursor(new_obj.name).type, self_name))
                    
                    result.sceneCursor(new_obj.name).linkFrames(new_obj.frameIndices)
                    #result.sceneCursor(new_obj.name)._framestates.update(new_obj.frameStates)
                    
                else:
                    #print("new cursor")
                    result.sceneCursors[new_obj.name] = new_obj
                    
                #print("after update: ", result.sceneCursors[new_obj.name].name, result.sceneCursors[new_obj.name].frameIndices)
                    
            #if len(source._scan_region_scene_profiles_.segments):
                #result._scan_region_scene_profiles_.segments += source._scan_region_scene_profiles_.segments
                
            #else:
                #result._scan_region_scene_profiles_.segments += [neo.Segment(name="frame_%d" % k + result._scene_frames_, index = k + result._scene_frames_) for k in range(source._scene_frames_)]
                
            result.generateScanRegionProfilesFromScene() # FIXME: what happens when there is no scan region or when scsan region is frameless?
        
        #### END manage the scene landmarks
        
        #### BEGIN 4) manage the scans landmarks
        if len(result.scans):
            #result._scans_frames_ = result.scans[0].shape[result.scans[0].axistags.index(result.scansFrameAxis)]
            
            # Here we merge scan landmarks:
            # a) if source contains a landmark present in target, we adjust the
            # frame indices for the source landmark frame-state associations then
            # and we append them to the target landmark frame-state associations
            #
            # b) if source bring a new landmark, we adjuyst the frame indices 
            #   of the soce landmark frame-state associations then add the landmark
            #   to the target's landmnarks dictionary
            #
            # we work on copies, so that frame-state associations of the original
            # source landmark are not modified.
            #
            # Because scans landmarks can have links to scene landmarks, we deal
            # with these here also, as detailed next.
            
            # landmark copy() function does NOT copy links to other PlanarGraphics
            # objects so we need to restore them here; the objects we link TO 
            # must already exist in the (new) self.scene. This requirement should
            # have been fulfilled in the scene code block, above.
            #
            # We restore the links AFTER remapping frame-state associations because
            # 1) the object we link TO, assuming it exists, already has the
            #   correct frame-state associations (dealt with above in the code
            #   block for the scene planar graphics)
            #
            # 2) remapping the frame-state associations of the new object does 
            #   not affect frame-state associations in the objects we link TO
            # 
            # 3) if the new object merely adds new frame-state associations to
            #   an existing scans planar graphic landmark, we assume that the
            #   target object (where frame-states are added) already has linked
            #   objects, so we do not touch these
            
            # first, "merge" scans rois in source with those in target (self)
            
            for obj in source.scansRois.values():
                new_obj = obj.copy()
                
                new_obj.linkFrames(new_obj.frameIndices)

                new_frame_ndx = [f + original_scans_frames for f in obj.frameIndices]
                
                new_obj.remapFrameStateAssociations([m for m in zip(obj.frameIndices, new_frame_ndx)])
                
                # this does NOT affect linked objects frame-state associations
                
                # also, this assumes scansRois do not link to scene graphics objects
                if new_obj.name in result.scansRois and new_obj.type == result.scansRois[new_obj.name].type:
                    result.scansRoi(new_obj.name).linkFrames(new_obj.frameIndices)
                    
                    if result.scansRoi(new_obj.name).type != new_obj.type:
                        if not isinstance(result.scansRoi(new_obj.name), pgui.Path):
                            result.scansRois[new_obj.name] = result.scansRoi(new_obj.name).convertToPath()
                            
                        if not isinstance(new_obj, pgui.Path):
                            new_obj = new_obj.convertToPath()
                        
                    #result.scansRois[new_obj.name]._framestates.update(new_obj.frameStates)
                    
                    # must also update the object links to reflect the new scanRegion
                    if len(result.scansRois[new_obj.name].objectLinks):
                        links = [link for link in result.scansRois[new_obj.name].objectLinks.items()]
                        #for link in result.scansRois[new_obj.name].objectLinks.items():
                        for l, mappingFcn in links:
                            #print("ScanData.concatenate: link", link)
                            
                            l = link[0]
                            mappingFcn = link[1][0].func
                            
                            # NOTE: 2018-09-17 16:33:42
                            # see NOTE: 2018-09-17 16:13:55 and NOTE: 2018-09-17 16:14:05
                            _args = [__a__ for __a__ in link[1][1]]
                            
                            if len(_args):
                                old_scanlines = [__o__ for __o__ in _args if isinstance(__o__, pgui.Path) and __o__.name.lower().strip() in ("scanline", "scanregion", "scanpath", "scantrajectory")]
                                
                                #print("ScanData.concatenate: old_scanlines", old_scanlines)
                                
                                if len(old_scanlines) == 1:
                                    # if there are more than one Path here this implies a complicated mapping
                                    # function -- I'm lifting my arms up!!!
                                    old_scanline = old_scanlines[0]
                                    
                                    _args[_args.index(old_scanline)] = result.scanRegion
                                    
                            _kwargs = link[1][2]
                            
                            if isinstance(l, pgui.Cursor):
                                if l.name in result.sceneCursors:
                                    # will replace link to l.name with new args & kwargs
                                    result.scansRois[new_obj.name].linkToObject(result.sceneCursors[l.name], mappingFcn, *_args, **_kwargs)
                                
                            else:
                                if l.name in result.sceneRois:
                                    # will replace link to l.name with new args & kwargs
                                    result.scansRois[new_obj.name].linkToObject(result.sceneRois[l.name], mappingFcn, *_args, **_kwargs)

                else: # new scans roi is added
                    # scans cursors MAY be linked to scene cursors
                    if len(new_obj.objectLinks):
                        # if this object has links to object already existing in, 
                        # or have been copied to, the scene planar graphics, 
                        # then restore the links; otherwise, do nothing 
                        # NOTE: this is DIFFERENT from what we do when extracting
                        # analysis unit data, see there for details
                        #
                        # ATTENTION: the mapping function should be constrained to
                        # the new scanregion!
                        
                        links = [l for l in new_obj.objectLinks.items()]
                        #for link in new_obj.objectLinks.items():
                        for l, mappingFcn in links:
                            l = link[0] # the object originally linked TO; it will be replaced with current cursor's copy
                            mappingFcn = link[1][0].func
                            _args = [__a__ for __a__ in link[1][1]] # NOTE: 2018-09-17 16:13:55 this MIGHT BE the _OLD_ scanregion path  -- needs replacing
                            
                            if len(_args):
                                # NOTE: 2018-09-17 16:14:05
                                # see NOTE: 2018-09-17 16:13:55
                                old_scanlines = [__o__ for __o__ in _args if isinstance(__o__, pgui.Path) and __o__.name.lower().strip() in ("scanline", "scanregion", "scanpath", "scantrajectory")]
                                
                                if len(old_scanlines) == 1:
                                    # if there are more than one Path here this implies a complicated mapping
                                    # function -- I'm lifting my arms up!!!
                                    old_scanline = old_scanlines[0]
                                    
                                    _args[_args.index(old_scanline)] = result.scanRegion
                                    
                            _kwargs = link[1][2]
                            
                            if isinstance(l, pgui.Cursor):
                                # object that we link TO is a cursor ...
                                if l.name in result.sceneCursors and l.type == result.sceneCursors[l.name].type:
                                    # ... a copy of which is defined in the scene (having the same name and type)
                                    new_obj.linkToObject(result.sceneCursors[l.name], mappingFcn, *_args, **_kwargs)
                                
                            else:
                                # object that we link TO is not a cursor ...
                                if l.name in result.sceneRois and l.type == result.sceneRois[l.name].type:
                                    # but a copy of it is present in the scene (having the same name and type)
                                    new_obj.linkToObject(result.sceneRois[l.name], mappingFcn, *_args, **_kwargs)

                    result.scansRois[new_obj.name] = new_obj
                
            for obj in source.scansCursors.values():
                # see comments above, for scansRois
                new_obj = obj.copy()
                
                new_obj.linkFrames(new_obj.frameIndices)

                new_frame_ndx = [f + original_scans_frames for f in obj.frameIndices]
                
                new_obj.remapFrameStateAssociations([m for m in zip(obj.frameIndices, new_frame_ndx)])
                    
                if new_obj.name in result.scansCursors and new_obj.type == result.scansCursors[new_obj.name].type:
                    # a cursor with this name & type already exists
                    if new_obj.type != result.scansCursor(new_obj.name).type:
                        raise RuntimeError("Cursor name %s refers to different cursor types: %s in source data (%s) and %s in target data (%s)" % \
                            (new_obj.name, new_obj.type, source_name, result.scansCursor(new_obj.name).type, self_name))
                    
                    result.scansCursors[new_obj.name].linkFrames(new_obj.frameIndices)
                    #result.scansCursors[new_obj.name]._framestates.update(new_obj.frameStates)
                    
                    # must also update the object links to reflect the new scanRegion
                    if len(result.scansCursors[new_obj.name].objectLinks):
                        links = [l for l in result.scansCursors[new_obj.name].objectLinks.items()]
                        #for link in result.scansCursors[new_obj.name].objectLinks.items():
                        for l, mappingFcn in links:
                            #print("ScanData.concatenate: link", link)
                            
                            l = link[0]
                            mappingFcn = link[1][0].func
                            
                            # NOTE: 2018-09-17 16:33:42
                            # see NOTE: 2018-09-17 16:13:55 and NOTE: 2018-09-17 16:14:05
                            _args = [__a__ for __a__ in link[1][1]]
                            
                            if len(_args):
                                old_scanlines = [__o__ for __o__ in _args if isinstance(__o__, pgui.Path) and __o__.name.lower().strip() in ("scanline", "scanregion", "scanpath", "scantrajectory")]
                                
                                #print("ScanData.concatenate: old_scanlines", old_scanlines)
                                
                                if len(old_scanlines) == 1:
                                    # if there are more than one Path here this implies a complicated mapping
                                    # function -- I'm lifting my arms up!!!
                                    old_scanline = old_scanlines[0]
                                    
                                    _args[_args.index(old_scanline)] = result.scanRegion
                                    
                            _kwargs = link[1][2]
                            
                            if isinstance(l, pgui.Cursor):
                                if l.name in result.sceneCursors:
                                    # will replace link to l.name with new args & kwargs
                                    result.scansCursors[new_obj.name].linkToObject(result.sceneCursors[l.name], mappingFcn, *_args, **_kwargs)
                                
                            else:
                                if l.name in result.sceneRois:
                                    # will replace link to l.name with new args & kwargs
                                    result.scansCursors[new_obj.name].linkToObject(result.sceneRois[l.name], mappingFcn, *_args, **_kwargs)

                        
                    
                else: # adds new cursor
                    if len(new_obj.objectLinks):
                        # if this object has links to object already existing in, 
                        # or have been copied to, the scene planar graphics, 
                        # then restore the links; otherwise, do nothing 
                        # NOTE: this is DIFFERENT from what we do when extracting
                        # analysis unit data, see there for details
                        links = [l for l in new_obj.objectLinks.items()]
                        #for link in new_obj.objectLinks.items():
                        for l, mappingFcn in links:
                            #print("ScanData.concatenate: link", link)
                            
                            l = link[0]
                            mappingFcn = link[1][0].func
                            
                            # NOTE: 2018-09-17 16:33:42
                            # see NOTE: 2018-09-17 16:13:55 and NOTE: 2018-09-17 16:14:05
                            _args = [__a__ for __a__ in link[1][1]]
                            
                            if len(_args):
                                old_scanlines = [__o__ for __o__ in _args if isinstance(__o__, pgui.Path) and __o__.name.lower().strip() in ("scanline", "scanregion", "scanpath", "scantrajectory")]
                                
                                #print("ScanData.concatenate: old_scanlines", old_scanlines)
                                
                                if len(old_scanlines) == 1:
                                    # if there are more than one Path here this implies a complicated mapping
                                    # function -- I'm lifting my arms up!!!
                                    old_scanline = old_scanlines[0]
                                    
                                    _args[_args.index(old_scanline)] = result.scanRegion
                                    
                            _kwargs = link[1][2]
                            
                            if isinstance(l, pgui.Cursor):
                                if l.name in result.sceneCursors:
                                    new_obj.linkToObject(result.sceneCursors[l.name], mappingFcn, *_args, **_kwargs)
                                
                            else:
                                if l.name in result.sceneRois:
                                    new_obj.linkToObject(result.sceneRois[l.name], mappingFcn, *_args, **_kwargs)

                    result.scansCursors[new_obj.name] = new_obj
                    
            if len(source._scan_region_scans_profiles_.segments):
                result._scan_region_scans_profiles_.segments += source._scan_region_scans_profiles_.segments
                
            if len(result.analysisUnits) > 0:
                result.generateScanRregionProfilesFromScans()
            
        #### END manage the scans landmarks
        
        #### BEGIN 5) concatenate scans block data 
        #print("concatenating scans blocks")
        
        if len(source._scans_block_.segments) == 0:
            for k in range(len(result._scans_block_.segments), result.scansFrames):
                result._scans_block_.segments.append(neo.Segment())
        else:
            if len(source._scans_block_.segments) > source.scansFrames:
                result._scans_block_.segments += [copy.deepcopy(s) for s in source._scans_block_.segments[0:source.scansFrames]]
                #result._scans_block_.segments += [neo_copy(s) for s in source._scans_block_.segments[0:source.scansFrames]]
                
            else:
                result._scans_block_.segments += [copy.deepcopy(s) for s in source._scans_block_.segments]
                #result._scans_block_.segments += [neo_copy(s) for s in source._scans_block_.segments]
                
                new_scans_frames = original_scans_frames + source.scansFrames
                #print("ScanData.concatenate: current scans frames %d" % result.scansFrames)
                #print("ScanData.concatenate: new_scans_frames %d" % new_scans_frames)
                
                if len(result._scans_block_.segments) < new_scans_frames:
                    for k in range(len(result._scans_block_.segments), new_scans_frames):
                        result._scans_block_.segments.append(neo.Segment())
                
        for k, s in enumerate(result._scans_block_.segments):
            s.index = k
            if isinstance(s.name, str) and len(s.name.strip()) == 0:
                s.name = "frame %d" % k
                
        #print("ScanData.concatenate: new scans block segments: %d" % len(result._scans_block_.segments))
                
        #### END concatenate scans block data 
        
        #### BEGIN 6) concatenate scene block data
        if len(source._scene_block_.segments) == 0:
            for k in range(len(result._scene_block_.segments), result.sceneFrames):
                result._scene_block_.segments.append(neo.Segment())
                
        else:
            if len(source._scene_block_.segments) > source.sceneFrames:
                result._scene_block_.segments += [copy.deepcopy(s) for s in source._scene_block_.segments[0:source.sceneFrames]]
                #result._scene_block_.segments += [neo_copy(s) for s in source._scene_block_.segments[0:source.sceneFrames]]
                
            else:
                result._scene_block_.segments += [copy.deepcopy(s) for s in source._scene_block_.segments]
                #result._scene_block_.segments += [neo_copy(s) for s in source._scene_block_.segments]
                
                new_scene_frames = original_scene_frames + source.sceneFrames
                
                if len(result._scene_block_.segments) < new_scene_frames:
                    for k in range(len(result._scene_block_.segments), new_scene_frames):
                        result._scene_block_.segments.append(neo.Segment())
        
        for k, s in enumerate(result._scene_block_.segments):
            s.index = k
            if isinstance(s.name, str) and len(s.name.strip())  == 0:
                s.name = "frame %d" % k
                
        #### END concatenate scene block data
        
        #### BEGIN 7) concatenate electrophysiology
        if len(source._electrophysiology_.segments):
            result._electrophysiology_.segments += [copy.deepcopy(s) for s in source._electrophysiology_.segments]
            #result._electrophysiology_.segments += [neo_copy(s) for s in source._electrophysiology_.segments]
            
        #else:
            # fill up with empty segments
            # CAUTION may cause problems with SignalViewer
            #result._electrophysiology_.segments += [neo.Segment(name="frame_%d" % k + result._scans_frames_, index = k + result._scans_frames_) for k in range(source._scans_frames_)]
        
        for k, s in enumerate(result._electrophysiology_.segments):
            s.index = k
            if isinstance(s.name, str) and len(s.name.strip()) == 0:
                s.name = "frame %d" % k
                
        #### END concatenate electrophysiology
        
        #### BEGIN 8) manage trigger protocols
        # NOTE: 2018-05-27 09:58:35
        # must COPY the trigger protocols first, followed by the analysis units,
        # because the latter depend on the protocols already defined in the result
        #print("concatenating protocols of %s to %s" % (source_name, self_name))
        
        #print("result.triggerProtocols", result.triggerProtocols)
        #print("source.triggerProtocols", source.triggerProtocols)
        
        if len(result.triggerProtocols):
            if len(source.triggerProtocols):
                for p in source.triggerProtocols:
                    # source protocols are APPENDED therefore the original 
                    # segment index (valid for source) must be added to the
                    # number of frames in the destination
                    new_seg_ndx = [s + original_scans_frames for s in p.segmentIndices()]
                    
                    #print("ScanData.concatenate: source protocol %s segments" % p.name, p.segmentIndices())
                    #print("ScanData.concatenate: new_seg_ndx", new_seg_ndx)
                    
                    # we first identify protocols by their name, so if p name is 
                    # found, we further check that the two events with same name 
                    # have identical trigger events (times and labels)
                    if p.name in [pp.name for pp in result.triggerProtocols]:
                        own_p = [pp for pp in result.triggerProtocols if pp.name == p.name][0]
                        
                        #print("ScanData.concatenate: result protocol ", own_p)
                        
                        # NOTE: 2018-07-03 23:24:07
                        # this works if the sweeps have the same relative time domain
                        # (which they should)
                        if own_p.hasSameEvents(p):
                            #print("ScanData.concatenate: own protocol %s segments" % p.name, own_p.segmentIndices())
                            
                            result.triggerProtocol(p.name).segmentIndex = result.triggerProtocol(p.name).segmentIndices() + new_seg_ndx
                            #print("ScanData.concatenate: own protocol segments", own_p.segmentIndices())
                            
                        else:
                            if strict:
                                    raise RuntimeError("Error concatenating %s to %s:\n\nTrigger event times of protocol %s in %s\n do not match those in %s" \
                                        % (source_name, self_name, p.name, source_name, self_name))
                                
                            else:
                                # NOTE: 2018-07-03 22:46:13
                                # attempt to find event times equivalence in the imaging
                                # side: even if the events have different time stamps
                                # in the ephys data they might come out the same in 
                                # the imaging data AFTER taking imagingDelay into account)
                                # TODO check user-defined events, too!
                                # CAUTION: this is a COMPROMISE based on the assumption
                                # that the imaging data ends up temporally well aligned
                                # which is what we're interested in
                                own_presyn  = own_p.presynaptic
                                own_postsyn = own_p.postsynaptic
                                own_photo   = own_p.photostimulation
                                own_delay   = own_p.imagingDelay
                                
                                other_presyn  = p.presynaptic
                                other_postsyn = p.postsynaptic
                                other_photo   = p.photostimulation
                                other_delay   = p.imagingDelay
                                
                                OK = False
                                
                                if own_delay is not None and other_delay is not None:
                                    OK = True
                                    
                                    if own_presyn is not None and other_presyn is not None:
                                        own_img_presyn = own_presyn - own_delay
                                        other_img_presyn= other_presyn - other_delay

                                        OK &= np.all(np.isclose(own_img_presyn.magnitude, other_img_presyn.magnitude))
                                        
                                    else:
                                        OK &= all([v is None for v in [own_presyn, other_presyn]])
                                        
                                    if own_postsyn is not None and other_postsyn is not None:
                                        own_img_postsyn = own_postsyn - own_delay
                                        other_img_postsyn = other_postsyn - other_delay
                                        
                                        OK &= np.all(np.isclose(own_img_postsyn.magnitude, other_img_postsyn.magnitude))
                                                    
                                    else:
                                        OK &= all([v is None for v in [own_postsyn, other_postsyn]])
                                        
                                    if own_photo is not None and other_photo is not None:
                                        own_img_photo = own_photo - own_delay
                                        other_img_photo = other_photo - other_delay
                                        
                                        OK &= np.all(np.isclose(own_img_photo.magnitude, other_img_photo.magnitude))
                                        
                                    else:
                                        
                                        OK &= all([v is None for v in [own_photo, other_photo]])
                                        
                                #print("ScanData.concatenate: OK", OK)
                                        
                                if not OK:
                                    raise RuntimeError("Error concatenating %s to %s:\n\nTrigger event times of protocol %s in %s\n do not match those in %s" \
                                        % (source_name, self_name, p.name, source_name, self_name))
                                
                                else:
                                    # NOTE: 2018-07-03 22:58:47
                                    # the protocols are COMPATIBLE from the imaging pov
                                    # so we use the current protocol, just adjust its segments
                                    # WARNING: this will be misaligned wrt the ephys data
                                    # CAUTION this is just a workaround
                                    # FIXME
                                    
                                    #warnings.warn("in ScanData.concatenate: \nTrigger event times mismatch for protocol %s in %s and %s\nShould treat %s separately." % (p.name, source_name, self_name, source.name), RuntimeWarning)
                                    
                                    result.triggerProtocol(p.name).segmentIndex = result.triggerProtocol(p.name).segmentIndices() + new_seg_ndx
                                    
                    else:
                        pp = p.copy()
                        pp.segmentIndex = new_seg_ndx
                        #print("ScanData.concatenate: new protocol %s from %s added to %s with segments" % (pp.name, source_name, self_name), pp.segmentIndices())
                        result.addTriggerProtocol(pp)
                        
        else:
            if len(source.triggerProtocols):
                for p in source.triggerProtocols:
                    pp = p.copy()
                    pp.segmentIndex = [s + result.nEphysSweeps for s in p.segmentIndices()]
                    #print("ScanData.concatenate: new protocol %s from %s added to %s, with segments" % (pp.name, source_name, self_name), pp.segmentIndices())
                    result.addTriggerProtocol(pp)
            
        #### END manage trigger protocols
        
        #### BEGIN 9) manage analysis units
        if len(source.analysisUnits):
            #print("ScanData.concatenate: merging landmark-based analysis units")
            for src_unit in source.analysisUnits:
                # check if source analysis unit points to an existing landmark
                src_landmark = src_unit.landmark
                
                if not result.hasLandmark(src_landmark):
                    raise RuntimeError("Landmark %s associated with analysis unit %s not found in source data %s" % \
                        (src_unit.landmark.name, s.name, source_name))
                
                #print("ScanData.concatenate: analysis units in %s" % self_name, [u.name for u in result.analysisUnits])
                
                if len(result.analysisUnits) and src_unit.name in [a.name for a in result.analysisUnits]:
                    a = [u for u in result.analysisUnits if u.name == src_unit.name] # technically this is never empty
                    
                    unit = a[0]
                    
                    # check unit identity:
                    if unit.unit_type != src_unit.unit_type:
                        raise RuntimeError("Type mismatch for analysis unit %s: unit has type %s in source (%s) and type %s in the target (%s)" % \
                            (src_unit.name, src_unit.unit_type, source_name, unit.unit_type, self_name) )
                    
                    if unit.landmark.type != src_unit.landmark.type:
                        raise RuntimeError("Landmark type mismatch for analysis unit %s: landmark is %s in source and %s in target (%s)" % \
                            (src_unit.name, src_unit.landmark.type, source_name, unit.landmark.type, self_name))
                    
                    for d in unit.descriptors.keys():
                        #if d not in src_unit.descriptors.keys():
                            #raise RuntimeError("Descriptors %s in analysis unit %s of source %s not found in analysis unit %s of target %s" % \
                                #(d, src_unit.name, source_name, unit.name, self_name))
                        
                        if d in src_unit.descriptors.keys():
                            if unit.descriptors[d] != src_unit.descriptors[d]:
                                raise RuntimeError("Value of descriptor %s in analysis unit %s of source %s (%s) is different from the value of descriptor %s in analysis unit %s of target %s (%s)" % \
                                                (d, src_unit.name, source_name, src_unit.descriptors[d], d, unit.name, self_name, unit.descriptors[d]))
                            
                    #print("ScanData.concatenate: found unit %s in %s" % (unit.name, self_name))
                    
                    # NOTE: 2018-07-03 23:23:22
                    # in view of NOTE: 2018-07-03 22:46:13
                    # check if this is a protocol with same events or it's just
                    # compatible from the imaging pov, in which case we may need
                    # some adjustments (otherwise it seems it does NOT register 
                    # the segment or frame with the planargraphics)
                    for p in src_unit.protocols:
                        if p not in result.triggerProtocols:
                            raise ValueError("Protocol %s of analysis unit %s in source (%s) not found in target (%s)" % \
                                (p.name, src_unit.name, source_name, self_name))
                        
                        #print("ScanData.concatenate: src unit %s protocol %s" % (src_unit.name, p.name))

                        if p not in unit.protocols:
                            #print("ScanData.concatenate: found in receiving unit %s" % unit.name)
                            # new protocol imported from source to be added to the unit in target
                            pp = p.copy()
                            # adjust the protocol's segments to reflect new data layout
                            pp.segmentIndex = [segment + original_scans_frames for segment in pp.segmentIndices()]
                            unit.protocols.append(pp)
                            #print("ScanData.concatenate: added protocol %s to unit %s with segments" % (pp.name, unit.name), pp.segmentIndices())
                            #print("ScanData.concatenate: new protocol for unit", pp.segmentIndices())
                            
                        else:
                            # protocol in target unit to be augumented with adjusted segment index from source
                            pp = [pr for pr in unit.protocols if pr == p][0]
                            # CAUTION:  this protocol (p) might already have segment indices augumented before :CAUTION:
                            #print("ScanData.concatenate: found protocol %s in unit %s with segments" % (pp.name, unit.name), pp.segmentIndices())
                            
                            new_segments = [segment + original_scans_frames for segment in p.segmentIndices()]
                            
                            if not any([s in pp.segmentIndices() for s in new_segments]):
                                pp.segmentIndex = pp.segmentIndices() + [segment + original_scans_frames for segment in p.segmentIndices()]
                                #print("ScanData.concatenate: augumented segments for protocol %s in unit %s" % (pp.name, unit.name), pp.segmentIndices())
                                
                else:
                    # completely new unit -- adjust frame indices for its protocols to reflect concatenated data frames
                    if src_unit.inScene:
                        if not result.hasSceneLandmark(src_unit.landmark):
                            raise RuntimeError("Landmark %s which is associated with analysis unit %s in the scene of source %s is not found among the scene landmarks in target %s" % \
                                (src_unit.landmark.name, src_unit.name, source_name, self_name))
                            
                    else:
                        if not result.hasScansLandmark(src_unit.landmark):
                            raise RuntimeError("Landmark %s which is associated with analysis unit %s in the scans of source %s is not found among the scans landmarks in target %s" % \
                                (src_unit.landmark.name, src_unit.name, source_name, self_name))
                        
                    ss = src_unit.copy()
                    #print("ScanData.concatenate: adding new unit %s on landmark %s to %s" % (ss.name, ss.landmark.name, self_name))
                    
                    for p in ss.protocols:
                        # p should be in result.triggerProtocols by now, see NOTE: 2018-05-27 09:58:35
                        if p not in result.triggerProtocols:
                            raise ValueError("Protocol %s brought by source analysis unit %s not found" % (p.name, s.name))
                        
                        p.segmentIndex = [segment + original_scans_frames for segment in p.segmentIndices()]
                        
                        #print("ScanData.concatenate: segments for protocol %s of added unit %s in %s" % (p.name, ss.name, self_name), p.segmentIndices())
                        
                    result._analysis_units_.add(ss)
                        
        #### END manage analysis units
        #print("\n *** \n\n")
        result.modified=True
        return result
        #print(len(self.scansBlock.segments))
        
    def addAnalysisUnit(self, *args):
        self.defineAnalysisUnit(*args)
    
    @safeWrapper
    def defineAnalysisUnit(self, landmark, scene=False, protocols=None):
        """
        Defines an AnalysisUnit object on a landmark in this ScanData.
        
        landmark: a pictgui.PlanarGraphics object or None.
                
                When a PlanarGraphics, it must be present in the appropriate dictionary
                for landmarks associated with the "scans" imge data set.
                
                When None, an AnalysisUnit object is defined on the entire scene or 
                scans data set according to the scene parameter.
                
        Named parameters:
        ================
        
        protocol: None (default), a TriggerProtocol object, or a sequence of 
                TriggerProtocol objects, or a string
        
            When a TriggerProtocol object, it must be present in 
                self._trigger_protocols_
                
            When a string, it must contain the name of an existing TriggerProtocol
                or it can be the keyword "all", meaning all available protocols are
                included
                
            When None, the function tries to get the associated protocols from the
                landmark's frame indices (i.e. those frames where the landmark is
                visible or has a state associated with).
                
            NOTE: Protocols are stored by reference in the AnalysisUnit object.
                
        Returns:
        =======
        A reference to the created analysis unit
                
        """
        #NOTE: 2018-03-09 16:26:14
        #DO NOT pass here cell and field: they are to be inherited from self
        
        # check for old API, upgrade self's structure if needed
        from gui import pictgui as pgui

        if isinstance(protocols, TriggerProtocol):
            if protocols not in self._trigger_protocols_:
                raise ValueError("data does not contain a protocol named %s" % protocols.name)
            
        elif isinstance(protocols, str):
            if protocols == "all":
                protocols = self._trigger_protocols_
                
            else:
                if protocols not in [p.name for p in self._trigger_protocols_]:
                    raise ValueError("data does not contain a protocol named %s" % protocols)
            
                protocols = [self.triggerProtocol(protocols)]
            
        elif isinstance(protocols, (tuple, list)):
            if all([isinstance(p, TriggerProtocol) for p in protocols]):
                if any([p not in self._trigger_protocols_ for p in protocols]):
                    raise ValueError("all protocols in the sequence must have been defined in this data")
                
            elif all([isinstance(p, str) for p in protocols]):
                protocols = self.getTriggerProtocols(protocols)
                
            else:
                raise TypeError("When protocols is a sequence, all of its elements must be either TriggerProtocol objects or strings")
            
        elif protocols is None:
            # try to figure out which protocols are associated, based on the 
            # landmark's frame-state associations
            # NOTE  this is done by the AnalysisUnit object property "frames"
            # that returns the intersection between protocol and landmark frames
            protocols = self._trigger_protocols_
            
        else:
            raise TypeError("protocol expected to be a TriggerProtocol object, a string (protocol name), a sequence of TriggerProtocol objects or of strings (protocol names); got %s instead" % type(protocol).__name__)
        
        if isinstance(landmark, (PlanarGraphics, str)):
            if scene:
                landmarks = list(self.sceneRois.values()) + list(self.sceneCursors.values()) # use scene landmarks
                
                where = "scene"
                
            else:
                landmarks = list(self.scansRois.values()) + list(self.scansCursors.values()) # use scans landmarks
                where = "scans"
                
            landmark_names = [l.name for l in landmarks]
            landmark_types = [l.type for l in landmarks]
            
            if isinstance(landmark, PlanarGraphics):
                if landmark not in landmarks or landmark.name not in landmark_names or landmark.type not in landmark_types:
                    raise ValueError("landmark %s does not exist in %s images of %s" % (landmark.name, where, self.name))
                
            elif isinstance(landmark, str):
                if landmark not in landmark_names:
                    raise ValueError("landmark %s not found" % landmark)
                
                # find the landmark with given name
                ldmrk = [l for l in landmarks if l.name == landmark]
                if len(ldmrk) == 0:
                    raise ValueError("landmark %s not found" % landmark)
                
                landmark = ldmrk[0]
                    
            
            # create analysis unit, add it to the self._analysis_units_ set 
            unit = AnalysisUnit(self, landmark=landmark, protocols=protocols, scene=scene, cell = self._analysis_unit_.cell, field=self._analysis_unit_.field)
            
            clear_up_units = [u for u in self.analysisUnits if u.inScene == scene and u.landmark not in landmarks]
            
            for u in clear_up_units:
                self.analysisUnits.remove(u)
                
            existing_unit_names = [u.name for u in self._analysis_units_]
            
            #if not any([unit.isSameAs(u) for u in self._analysis_units_]):
                # cannot use "in" or "==" because AnalysisUnit.__eq__ is not defined 
                # ans it's rather flimsy to rely on python's id()
            if unit.name not in existing_unit_names:
                unit.cell = self.analysisUnit().cell
                unit.field = self.analysisUnit().field
                unit.sourceID = self.analysisUnit().sourceID
                unit.genotype = self.analysisUnit().genotype
                unit.gender = self.analysisUnit().gender
                unit.age = self.analysisUnit().age
                
                for d in self.analysisUnit().descriptors:
                    unit.setDescriptor(d, self.analysisUnit().getDescriptor(d))
                    
                self._analysis_units_.add(unit)
                
            return unit
            
        elif landmark is None:
            # accept this => sets up the whole data set as a unit
            self._analysis_unit_.protocols = protocols
            
            return self._analysis_unit_
            
        else:
            raise TypeError("landmark expected to be a pictgui.PlanarGraphics, or None; got %s instead" % type(landmark).__name__)
        

    @safeWrapper
    def hasAnalysisUnit(self, obj):
        """ Checks for the existence of an analysis unit defined on a landmark.
        
        Parameter:
        =========
        obj: AnalysisUnit or str (name of an AnalysisUnit)
        """
        from gui import pictgui as pgui

        if len(self._analysis_units_) == 0:
            return False
        
        if isinstance(obj, str):
            return obj in [u.name for u in self._analysis_units_]# if isinstance(u, AnalysisUnit)]

        elif isinstance(obj, AnalysisUnit):
            return obj in self._analysis_units_
        
        elif isinstance(obj, PlanarGraphics):
            return obj in [u.landmark for u in self._analysis_units_]# if isinstance(u, AnalysisUnit)]
        
        else:
            return False
            
        
    @safeWrapper
    def setAnalysisUnitDescriptor(self, obj, name, value):
        """
        Obj : either None, a string or an AnalysisUnit object
            when None, then set a descriptor to the AnalysisUnit defined on this
                ScanData as a whole
                
            when a string, then set a descriptor to the AnalysisUnit with name "obj",
                if it is defined in the data
                
            when an AnalysisUnit object, then set its descriptor, provided that the
                object belong to this data.
            
        """
        if obj is None:
            self._analysis_unit_.setDescriptor(name, value)
            
        else:
            if self.hasAnalysisUnit(obj):
                if isinstance(obj, str):
                    self.analysisUnit(obj).setDescriptor(name, value)
                    
                elif isinstance(obj, AnalysisUnit):
                    obj.setDescriptor(name, value)
                    
                else:
                    raise TypeError("Expecting a string (unit name) or an AnalysisUnit object, or None; got %s instead" % type(obj).__name__)

            else:
                raise ValueError("AnalysisUnit %s not found" % obj)
        
        
        
    @safeWrapper
    def getAnalysisUnitDescriptor(self, obj, name):
        """
        Obj : either None, a string or an AnalysisUnit object
            when None, then set a descriptor to the AnalysisUnit defined on this
                ScanData as a whole
                
            when a string, then set a descriptor to the AnalysisUnit with name "obj",
                if it is defined in the data
                
            when an AnalysisUnit object, then set its descriptor, provided that the
                object belong to this data.
            
        """
        if obj is None:
            return self._analysis_unit_.getDescriptor(name)
        
        else:
            if self.hasAnalysisUnit(obj):
                if isinstance(obj, str):
                    return self.analysisUnit(obj).getDescriptor(name)
                    
                elif isinstance(obj, AnalysisUnit):
                    return obj.getDescriptor(name)
                    
                else:
                    raise TypeError("Expecting a string (unit name) or an AnalysisUnit object, or None; got %s instead" % type(obj).__name__)
                
            else:
                raise ValueError("AnalysisUnit %s not found" % obj)
            
    @safeWrapper
    def removeAnalysisUnit(self, unitOrName, removeLandmark=True):
        """Removes a landmark-based analysis unit.
        
        Also removes all derived analysis data associated with the unit.
        
        Optionally also removes the associated graphics landmark.
        
        Parameters:
        ==========
        unitOrName: str or AnalysisUnit
        
            When a str, it must neither be empty nor contain only blank characters
        
        Keyword parameters:
        ===================
        removeLandmark: boolean (default True)
        
            When True, also removes the associated landmark.
            
        Returns:
        =======
        The removed unit, if found, or None
        
        """
        unit = None
        
        if isinstance(unitOrName, str):
            if len(unitOrName.strip()) == 0:
                return
            
            units = [u for u in self._analysis_units_ if u.name == unitOrName]
            
            if len(units):
                unit = units[0]
                
        elif isinstance(unitOrName, AnalysisUnit):
            if unitOrName in self._analysis_units_:
                unit = unitOrName
                
        if unit is None:
            #warnings.warn("Analysis unit %s not found in %s" % (unitOrName, self.name))
            return
                
        #print("ScanData.removeAnalysisUnit: ", unit.name)
        
        for segment in self.scansBlock.segments:
            signal_index = get_index_of_named_signal(segment, unit.name, stype=(neo.AnalogSignal, DataSignal), silent=True)
            
            if signal_index is not None:
                del segment.analogsignals[signal_index]
            
            signal_index = get_index_of_named_signal(segment, unit.name, stype=neo.IrregularlySampledSignal, silent=True)
            
            if signal_index is not None:
                del segment.irregularlysampledsignals[signal_index]
            
        for segment in self.sceneBlock.segments:
            signal_index = get_index_of_named_signal(segment, unit.name, stype=(neo.AnalogSignal, DataSignal), silent=True)
            
            if signal_index is not None:
                del segment.analogsignals[signal_index]
        
            signal_index = get_index_of_named_signal(segment, unit.name, stype=neo.IrregularlySampledSignal, silent=True)
            
            if signal_index is not None:
                del segment.irregularlysampledsignals[signal_index]
        
        self._analysis_units_.remove(unit)
        
        if removeLandmark and unit.landmark is not None:
            self.removeLandmark(unit.landmark)
            
        return unit
                    
    def _remove_data_signal_from_block_(self, src, name):
        for segment in src:
            signal_index = get_index_of_named_signal(segment, name, stype=(neo.AnalogSignal, DataSignal), silent=True)
            if signal_index is not None:
                del segment.analogsignals[signal_index]
        
    
    def _select_protocol_frames_(self, event_frames, exclude_failures, test_comp, unit_name, self_name):
        """
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray

        """
        ret = collections.OrderedDict()
        
        if isinstance(event_frames, dict):
            # the simple case when a single analysis unit is analysed
            for protocol_name, protocol_dict in event_frames.items():
                ff = list()
                for protocol_frame, success_list in protocol_dict.items():
                    if exclude_failures:
                        if test_component == "all":
                            OK = all(success_list)
                            
                        elif test_component == "any":
                            OK = any(success_list)
                        
                        elif any([t < 0 or t >= len(success_list) for t in test_component]):
                            raise ValueError("'test_component' parameter contains indices that are invalid for the number of events/event components (%d) in the frame %d with protocol %s, for the analysis unit %s in scandata %s" %\
                                (len(success_list), protocol_frame, protocol_name, unit_name, self_name))
                        
                            OK = True
                            
                            for t in test_component:
                                OK &= success_list[t]
                                
                    else:
                        OK = True
                                
                    if OK:
                        ff.append(protocol_frame) # protocol_frame is an int
                            
                        
                if len(ff):
                    ret[protocol_name] = ff # only accept a protocol if it has any accepted frames left
            
        elif isinstance(event_frames, list) and all([isinstance(fev, dict) for fev in event_frames]):
            # the more complicated case when all landmark-based analysis units are tested
            for protocol_name, protocol_dict in event_frames[0].items():
                ff = list()
                for protocol_frame, success_list in protocol_dict.items():
                    if exclude_failures:
                        if test_component == "all":
                            OK = all(success_list)
                            
                        elif test_component == "any":
                            OK = any(success_list)
                        
                        elif any([t < 0 or t >= len(success_list) for t in test_component]):
                            raise ValueError("'test_component' parameter contains indices that are invalid for the number of events/event components (%d) in the frame %d with protocol %s, for the analysis unit %s in scandata %s" %\
                                (len(success_list), protocol_frame, protocol_name, unit_name, self_name))
                        
                            OK = True
                            
                            for t in test_component:
                                OK &= success_list[t]
                                
                    else:
                        OK = True
                                
                    if OK:
                        ff.append(protocol_frame) # protocol_frame is an int
                            
                        
                if len(ff):
                    ret[protocol_name] = ff # only accept a protocol if it has any accepted frames left
            
            for fev in event_frames:
                for protocol_name, protocol_dict in event_frames[0].items():
                    ff = list()
                    for protocol_frame, success_list in protocol_dict.items():
                        if exclude_failures:
                            if test_component == "all":
                                OK = all(success_list)
                                
                            elif test_component == "any":
                                OK = any(success_list)
                            
                            elif any([t < 0 or t >= len(success_list) for t in test_component]):
                                raise ValueError("'test_component' parameter contains indices that are invalid for the number of events/event components (%d) in the frame %d with protocol %s, for the analysis unit %s in scandata %s" %\
                                    (len(success_list), protocol_frame, protocol_name, unit_name, self_name))
                            
                                OK = True
                                
                                for t in test_component:
                                    OK &= success_list[t]
                                    
                        else:
                            OK = True
                                    
                        if OK:
                            ff.append(protocol_frame) # protocol_frame is an int
                                
                    if len(ff):
                        if protocol_name in ret:
                            ret[protocol_name] += [f for f in ff if f not in ret[protocol_name]]
                                    
                        else:
                            ret[protocol_name] = ff # only accept a protocol if it has any accepted frames left
        else:
            raise RuntimeError("event_frames expected to be a dict or a list of dict; got %s instead" % type(event_frames).__name__)
        
        #print("self._select_protocol_frames_ returns", ret)
        
        return ret
    
    def _extract_unit_adapt_landmark_frames_(self, obj, src_obj, protocol_frames_dict, 
                                               average=False,
                                               with_links=False, 
                                               linked_scene_cursors_dict=None, 
                                               linked_scene_rois_dict=None,
                                               scan_region=None):

        from gui import pictgui as pgui

        new_frame_index_for_landmark = list()
        
        for ndx, protocol_name in enumerate(protocol_frames_dict):
            protocol_frames = protocol_frames_dict[protocol_name]
            
            if any([f in protocol_frames for f in src_obj.frameIndices]):
                if average:
                    new_frame_index_for_landmark.append(ndx)
                    
                else:
                    new_frame_index_for_landmark += [k for k,f in enumerate(src_obj.frameIndices) if f in protocol_frames]
        
        obj.frontends.clear()
        
        obj.frameIndices = new_frame_index_for_landmark
        
        if with_links:
            if len(src_obj.objectLinks):
                links = [l for l in src_obj.objectLinks.items()]
                #for link in src_obj.objectLinks.items():
                for l, mappingFcn in links:
                    l = link[0] # original object to which src_obj is linked to
                    mappingFcn = link[1][0].func # linking function (mapping function)
                    _args = link[1][1] # args
                    _kwargs = link[1][2]
                    
                    if isinstance(l, pgui.Cursor):
                        #print("_extract_unit_adapt_landmark_frames_",l.name)
                        # object being linked to is a cursor
                        # has this LINKED object been copied over already?
                        if linked_scene_cursors_dict is not None:
                            if l.name in linked_scene_cursors_dict.keys():
                                linked_object = linked_scene_cursors_dict[l.name]
                                
                            else:
                                linked_object = l.copy()
                                linked_scene_cursors_dict[l.name] = linked_object
                                
                            obj.linkToObject(linked_scene_cursors_dict[l.name], mappingFcn, scan_region)
                        
                    else:
                        # same as above, but for ROIs
                        if linked_scene_rois_dict is not None:
                            if l.name in linked_scene_rois_dict.keys():
                                linked_object = linked_scene_rois_dict[l.name]
                                
                            else:
                                linked_object = l.copy()
                                linked_scene_rois_dict[l.name] = linked_object
                
                            obj.linkToObject(linked_scene_rois_dict[l.name], mappingFcn, scan_region)
                        
                    linked_object.elementsFrameIndices = new_frame_index_for_landmark

        obj._currentFrame = 0
        
        return obj
        
    @safeWrapper
    def clearAnalysis(self, name=None):
        """Removes the analysis data signal associated with the named analysis unit, from the analysis data blocks.
        
        The analysis data blocks are self.scansBlock and self.sceneBlock
        
        Parameters:
        ==========
        
        name: a str or None, or a sequence of str
        
            If name is None, clears the analysis data signal associated with the analysis unit of the entire data
            Otherwise, clear removes just the data signal associated with the specified analysis unit, if it exists.
            
            If name is "all" (case-insensitive) the clears ALL data signals present in the analysis data blocks
        
        """
        if isinstance(name, str):
            if name.lower() == "all":
                for segment in self.scansBlock:
                    segment.analogsignals.clear()
                    
                for segment in self.sceneBlock:
                    segment.analogsignals.clear()
                    
            else:
                self._remove_data_signal_from_block_(self.scansBlock, name)
                self._remove_data_signal_from_block_(self.sceneBlock, name)
            
        elif name is None:
            name = self.analysisUnit()
            self._remove_data_signal_from_block_(self.scansBlock, name)
            self._remove_data_signal_from_block_(self.sceneBlock, name)
            
        elif isinstance(name, (tuple, list)) and all([isinstance(n, str) for n in name]):
            for n in name:
                self._remove_data_signal_from_block_(self.scansBlock, name)
                self._remove_data_signal_from_block_(self.sceneBlock, name)
            
    @safeWrapper
    def clearAnalysisUnits(self, removeLandmarks=False):
        """Removes all defined analysis units, optionally the planar graphics associated with them
        """
        if len(self._analysis_units_) == 0:
            return
        
        if removeLandmarks:
            units = [u for u in self._analysis_units_]
            
            for u in units:
                self.removeAnalysisUnit(u, removeLandmark=True)
                
        else:
            self._analysis_units_.clear()
            
    @property
    def defaultAnalysisUnit(self):
        return self.getAnalysisUnit()
    
    @safeWrapper
    def analysisUnitSignal(self, landmark=None):
        # TODO: get the signal computed on this analysis unit; the analysis results
        # if present, are embedded in the signal's annotations attribute
        #
        # What to return:
        #
        # None if the analysis unit has not been analysed
        #
        # A neo.Block with one segment per frame (if multi-frame) and as many signals
        # per segment as the analysis of the unit would have returned
        #
        # give the options to select the frames, potentially returning a block wiht just one segment
        #
        # the frame selector should by default be set by the analysis uniit itself
        # but allow it to be overridden in the call parameters list, with the 
        # caveat that invalid frame indices should be flagged out.
        #
        pass
            
    @safeWrapper
    
    def getAnalysisUnit(self, landmark=None):
        """Access an AnalysisUnit object defined in this ScanData object.
        
        This can be an AnalysisUnit object associated with a specified landmark,
        or the AnalysisUnit associated with the entire data.
        
        Named parameters:
        =================
        
        landmark: string or None (default), or a PlanarGraphics.
        
            When None, the function returns the default analysis unit defined on 
            the whole ScanData object.
            
            When a string, the function returns the AnalysisUnit object with the
            given name, or None if such an AnalysisUnit does not exist.
            
            When a PlanarGraphics, the function returns the AnalysisUnit object
            defined on the specified PlanarGraphics object as landmark.
            
            In either case, the PlanarGraphics and the AnalysisUnit defined on it
            must be both present in this ScanData object.
            
        Returns:
        ========
        Returns the AnalysisUnit defined on the specified landmark parameter
        if the latter is not None AND it exists in this ScanData object, AND it has
        been associated with an AnalysisUnit object.
        
        If the specified landmark does not exist, or it has not been
        associated with an AnalysisUnit, returns None.
        
        When the landmark parameter is None (default) the function returns the
        data-wide AnalysisUnit associated with the whole data set.
        """
        import gui.pictgui as pgui

        if isinstance(landmark, str):
            if landmark in [u.name for u in self._analysis_units_]: # make sure there is an analysis unit with this name
                unit = [u for u in self._analysis_units_ if u.name == landmark]
                return unit[0]
            
            else:
                return None
            
        elif isinstance(landmark, PlanarGraphics):
            if landmark not in self.scansCursors.values() and \
                landmark not in self.sceneCursors.values() and \
                    landmark not in self.scansRois.values() and \
                        landmark not in self.sceneRois.values():
                            
                warnings.warn("Landmark %s does not exist in this ScanData object" % landmark)
                
                return None
            
            if landmark in [u.landmark for u in self._analysis_units_]:
                unit = [u for u in self._analysis_units_ if u.landmark == landmark]
                return unit[0]
            
            else:
                return None
            
        elif landmark is None:
            return self.analysisUnit
        
        else:
            raise TypeError("landmark expected to be a string, a pictgui.PlanarGraphics, or None; got %s instead" % type(landmark).__name__)
            
            
    #@safeWrapper
    def extractAnalysisUnit(self, analysis_unit, average=False, 
                                exclude_failures=False, 
                                test_component="any", 
                                name=None,
                                progressSignal = None,
                                progressValue = None):
        """Outputs a defined analysis unit as a ScanData object.
        
        FIXME/TODO 2022-01-04 17:13:13
        1) break up dependency on _parse_image_arrays_
        2) adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        This function returns a ScanData object where scans images contain only
        the data belonging to a single analysis unit. For landmark-based analysis
        units this is defined as the scans image data inside the region of interest
        set by the landmark.

        For example, the region of interest defined by a vertical cursor landmark
        is a rectangle with the width equal to the cursor's X window, and length
        equal to the scans image height.
        
        The frames generated using the same trigger protocol can be averaged to
        yield a single frame for that protocol in the result.
        
        Optionally, only the data frames where the event analysis was successful 
        can be extracted (by default all frames given the protocols associated 
        with the analysis unit are extracted).
        
        When data is itself a single analysis unit (e.g. it has been extracted
        already) this function can be used to extract only its "successful" frames
        (this implied that the previosu data extraction did not average protocol frames)
        
        NOTE A ScanData object already associates a default analysis unit defined
        on the entire data set, and it may associate landmark-based analysis units.
        
        Parameters:
        ==========
        analysis_unit: AnalysisUnit object, or str.
        
            When an AnalysisUnit object, this cann eb landmark-based, or it can 
            be the one defined on the entire data set.
            
            NOTE: When the "unit" is defined on the entire data set, if the 
            "exclude_failures" parameter (see below) is False, the result is simply
            a copy of the data. Otherwise, the result is a partial copy of the data
            containing only those frames deemed to be successful (possibly 
            in at least one landmark-based analysis unit, if there are any). This 
            latter case requires the data to have been analysed first.
            
            When a :str:, "unit" must be the name of a valid AnalysisUnit defined on
            a landmark contained in the data.
            
        average: boolean, default is False
        
            When True, the data frames belonging to a protocol will be averaged
            such that the result will contain a single frame for each protocol,
            and that frame is the average of all (if exclude_failures is False) or only 
            of the successful (if exclude_failures is True) frames for that protocol
            in the original data.
            
            When False, the data frames belonging to a protocol will be carried 
            over to the result provided theyare successfu;
            
            
        exclude_failures: bool, default False
        
            When True, only frames that test for success will be included.
            
        test_component: the keyword "any" (default), or the keyword "all",
            an int, or a sequence of ints.
            
            Used when exclude_failures is True and the analysis can distinguish 
            between failed and successful events in the data, according to the 
            fail/success discrimination set in the analysis options.
            
            For multiple events (or multi-component events such as compound EPSCaTs),
            this parameter indicates which event or event component will be used 
            to determine if the frame is included or rejected from the extracted data.
            
            The default value (keyword "any") indicates that at least one event or
            event component must have been deemed successful in order for the frame to
            be included in the extracted data.
            
            When the value if the keyword "all", then all analysed events or event
            components in the frame must be successful for the frame to be included.
            
            When an int, it simply indicates the index of the event or event component
            to be used as fail/success test. This index is zero-based and must be 
            valid given the number or events or event components analyzed in the frame.
            
            When a sequence of ints, these are unique indices for more than one event
            or event components to be used as fail/success test and must be valid 
            given the number fo events or event components analysed in the frame.
            
        name: a string or None (default) -- when a string, it will be assigned 
            as new name for the result.
            
        progressSignal None (default) or a pyqtSignal accepting an int as value
        
        progressValue None (default) or an int that will be emitted by progressSignal
                after the code has executed
            
        NOTE: ALL frames associated witht he given analysis unit and protocol(s)
        must have been analysed.
            
        Returns a ScanData object.
        
        """
        
        import gui.pictgui as pgui
        from copy import deepcopy
        from keyword import iskeyword
        
        #### BEGIN  check parameters of function call
        # parse the 'analysis_unit' parameter => must resolve to a single AnalysisUnit object
        # either landmark-based or whole data-based
        #
        if analysis_unit is None:
            analysis_unit = self.analysisUnit()
            
        elif isinstance(analysis_unit, str):
            if analysis_unit in [u.name for u in self.analysisUnits]:
                analysis_unit = self.analysisUnit(analysis_unit)
                
            elif analysis_unit == self.analysisUnit().name:
                analysis_unit = self.analysisUnit()
                
            else:
                raise ValueError("Analysis unit %s not found in scan data %s" % (analysis_unit, self.name))
            
        elif isinstance(analysis_unit, AnalysisUnit):
            if analysis_unit not in self.analysisUnits and analysis_unit is not self.analysisUnit():
                raise ValueError("Analysis unit %s not found in scan data %s" % (analysis_unit.name, self.name))
                
        else:
            raise TypeError("'analysis_unit' parameter was expected to be an AnalysisUnit object, a str, or None; got %s instead " % type(analysis_unit).__name__)
            
        if analysis_unit.landmark is not None:
            if exclude_failures and not analysis_unit.hasAnalysis():
                raise RuntimeError("Analysis unit %s has apparently not been analysed in %s" % (analysis_unit.name, self.name))
            
            if not isinstance(analysis_unit.landmark, pgui.Cursor):
                # TODO FIXME
                raise NotImplementedError("Only pictgui.Cursor landmarks are supported, for now")
            
            if analysis_unit.landmark.type != pgui.GraphicsObjectType.vertical_cursor:
                # TODO FIXME
                raise NotImplementedError("Only vertical cursor landmarks are supported, for now")
            
        if not isinstance(average, bool):
            raise TypeError("Average expected to be a bool; got %s instead" % type(average).__name__)
        
        if not isinstance(exclude_failures, bool):
            raise TypeError("Exclude_failures parameters expected to be a bool; got %s instead" % type(exclude_failures).__name__)
        
        if isinstance(test_component, str):
            if test_component.lower() not in ("all", "any"):
                raise ValueError("Test component keyword %s is invalid; expected to be one of 'all' or 'any'" % test_component)
            
            test_component = test_component.lower()
            
        elif isinstance(test_component, int):
            test_component = [test_component]
            
        elif isinstance(test_component, (tuple, list)):
            if not all([isinstance(t, int) for t in test_component]):
                raise TypeError("When a sequence, test component must contain int values")
            
        else:
            raise TypeError("Test component expected to be a str ('all' or 'any'), an int or a sequence of int; got %s instead" % \
                type(test_component).__name__)
        
        if not isinstance(name, (str, type(None))):
            raise TypeError("Name expected to be a str or None; got %s instead" % type(name).__name__)
        
        if isinstance(name, str):
            if iskeyword(name):
                raise ValueError("Name %s is a keyword" % name)
            
        #### END
            
        #### BEGIN frame selection
        protocols = analysis_unit.protocols
        
        if len(protocols) == 0:
            protocol_names_str = "all_frames"
            
        else:
            protocol_names_str = "_".join([p.name for p in protocols])
            
        if exclude_failures:
            protocol_names_str += "_success_only"
            
        # prepare to take into account success vs failures
        # nested list of frame indices where at least one event or event component is successful
        
        # NOTE: 2018-06-12 13:05:06
        # unit_frames_by_protocol_success is a dict, e.g.:
        
        # {'1bAP': {0: [True]},
        #  '2bAP': {1: [True]},
        #  '3bAP': {2: [True]},
        #  '5bAP': {3: [True]}}
                
        # When no protocol is defined, this is a dict with one element:
        # {"no_protocol": {0: [True], {1: [False]}}} etc
         
        
        # NOTE: 2018-06-16 22:22:01
        # having a valid (analysable and / or analysed) data-wide analysis units
        # or having valid analysable or analysed landmark-based units is
        # mutually exclusive
        
        #
        # NOTE: 2018-06-16 22:24:43
        # this works ONLY if the analysis unit has been analysed
        
        if analysis_unit.hasAnalysis():
            if analysis_unit.landmark is not None:
                unit_frames_by_protocol_success = analysis_unit.frameEventDetection
                
            elif analysis_unit == self.analysisUnit():
                if len(self.analysisUnits):
                    unit_frames_by_protocol_success = [u.frameEventDetection for u in self.analysisUnits]
                    
                else:
                    unit_frames_by_protocol_success = self.analysisUnit().frameEventDetection
                    
            else:
                raise RuntimeError("Ambiguous analysis unit specified: %s" % analysis_unit.name)
                
            selected_protocols_and_frames = self._select_protocol_frames_(unit_frames_by_protocol_success,
                                                                           exclude_failures,
                                                                           test_component,
                                                                           analysis_unit.name,
                                                                           self.name)
        else:
            if exclude_failures:
                raise ValueError("The analysis unit %s has not been analysed yet!" % analysis_unit.name)
            
            selected_protocols_and_frames = collections.OrderedDict()
            
            if len(self.triggerProtocols):
                for p in self.triggerProtocols:
                    selected_protocols_and_frames[p.name] = p.segmentIndices()
                    
            else:
                selected_protocols_and_frames["no_protocol"] = [f for f in range(self.scansFrames)]
                
        
        #print("ScanData.extractAnalysisUnit %s unit_frames_by_protocol_success: " % analysis_unit.name, unit_frames_by_protocol_success)
        #print("ScanData.extractAnalysisUnit %s selected_protocols_and_frames: " % analysis_unit.name, selected_protocols_and_frames)
        
        #
        #### END frame selection
        
        #### BEGIN generate stub ScanData object
        #
        result = ScanData()
        
        result._scandatatype_ = self.scanType
        result._analysismode_ = self.analysisMode
        result.analysisOptions  = deepcopy(self.analysisOptions)
        
        result._processed_ = self._processed_
        result._annotations_["extracted"] = dict()
        result._annotations_["extracted"]["source"] = self.name
        
        result._annotations_["extracted"]["landmark"] = dict()
        
        if analysis_unit.landmark is not None:
            result._annotations_["extracted"]["landmark"]["name"] = analysis_unit.landmark.name
            result._annotations_["extracted"]["landmark"]["scene"] = analysis_unit.inScene
            
        
        #
        #### END generate stub ScanData
        
        
        #### BEGIN create data collections
        # NOTE: 2018-06-12 21:20:14
        # now that we have a clear idea which frames get copied and, possibly,
        # averaged, we can:
        #
        # (1) create temporary data structures to store, for each protocol:
        #       image data
        #       electrophysiology segments
        #       scansBlock and sceneBlock segments - although these can be 
        #       recreated by analysing the resulting data.
        #
        #       we then average these if needed in which case we also create a
        #       cached protocol-frame index dictionary were the frame index is
        #       the index of the corresponding singleton frame in the new data
        #
        # (2) copy the landmarks, making sure that:
        #   (a) their frame indices reflect the new frame layout with the following
        #       caveats:
        #       * for hard frame-state associations we use the state associated
        #           with the first frame in the given protocol
        #
        #       * WE DO NOT copy the landmark used to define the analysis_unit
        #           that is being extracted (but we DO copy its linked objects
        #           defined in the opposite image set, we just DON'T recreate the
        #           links) -- this is self-evident, I think, because after all,
        #           we're extracintg the data regions delimited by the analysis 
        #           unit landmark, to begin with.
        #
        
        #   (b) copy the protocols (by name) and adjust their segmentIndex to 
        #       reflect the new data frame layout
        
        # dictionary of frame indices mapped to protocol_name 
        # (1 protocol name -> a scalar index value)
        # for new data containing frame-average images per protocol
        averaged_protocol_frames = collections.OrderedDict()
        
        # dictionary mapping the protocol name to the frame indices adapted to 
        # the extracted data frame layout: 
        # has same layout as selected_protocols_and_frames
        new_protocol_frames = collections.OrderedDict()
        
        # stores the copies of protocols with frame indices adjusted
        protocol_list = list()
        protocol_ephys_segments = list()
        protocol_scan_data_segments = list() # one element per protocol; each element is a list of segments
        protocol_scene_data_segments = list()
        protocol_scanline_scans_profiles = list()
        protocol_scanline_scene_profiles = list()
        
        
        protocol_scene_data_image_frames = list()
        
        # for each subarray in scene or scans, create an empty list
        # to each of these lists append the corresponding frames taken out from
        # the scene or scan vigra arrays: one list of frames per "channel" - the 
        # the general case is where there are several channels in the scans or 
        # scene list
        
        for s in range(len(self.scene)):
            protocol_scene_data_image_frames.append(list())
            
        protocol_scans_data_image_frames = list()
        
        for s in range(len(self.scans)):
            protocol_scans_data_image_frames.append(list())
       
        # list: linearized collection of frame indices from original data that were
        # selected above, in selected_protocols_and_frames
        selected_frames_index_list = list()
        
        # strided counter (non-constant stride) indicating how many frames
        # would be added to the new data, based on the protocol's selected 
        # frame indices (as defined in the original data)
        # this allows us to assign frame indices to the protocol in the NEW
        # data, based on the actual number of frames in the new data
        # e.g., consider that frame index 27 in original data belonging to the 
        # currently processed protocol has NOT been selected (because it was NOT
        # flagged as a success) but its neighbouring frames are flagged as 
        # successful and hence are selected; in this case, copying this protocol's
        # frames will leave frame 27 behind therefore the protocol's frame index
        # association will disagree with the frame numbers (or indices) in the 
        # new data
        # 
        # this variable therefore serves to keep track how many of this protocol's
        # frames were selected for copy so that we can set the association between
        # this protocol and the correct frame indices in the new data
        added_frames = 0
        
        #### END create data collections

        # NOTE: 2018-06-17 19:45:42
        # BEGIN data copy loop (without planar graphics)
        #
        for kprotocol, protocol_name in enumerate(selected_protocols_and_frames):
            # update the linearized index list of selected frames
            selected_frames_index_list += selected_protocols_and_frames[protocol_name]
            
            # actual frame indices in the original data, for the frames that will
            # be copied to the new data, or averaged into a single frame in the 
            # new data
            
            kprotocol_frames = selected_protocols_and_frames[protocol_name] 
            
            # simple counter so that in case of averaging the protocol will be
            # assigned to a single frame with index k
            averaged_protocol_frames[protocol_name] = [kprotocol]
            
            # copy the protocol, assign a single frame index if averaging, or
            # a set of frame indices if NOT averaging
            # but make sure these frame indices are valid for the NEW data
            if protocol_name == "no_protocol":
                current_protocol = TriggerProtocol(name="no_protocol")
                
            else:
                # a COPY of the protocol in self
                current_protocol = [p for p in protocols if p.name == protocol_name][0].copy()
                
            
            if average:
                new_protocol_segments_index = [kprotocol]
                
            else:
                new_protocol_segments_index= [f for f in range(added_frames, added_frames + len(kprotocol_frames))]
                
            current_protocol.segmentIndex = new_protocol_segments_index
            
            #print("ScanData.extractAnalysisUnit protocol %d, name %s => current_protocol" % (kprotocol, protocol_name), current_protocol)
            
            new_protocol_frames[current_protocol.name] = new_protocol_segments_index
            
            protocol_list.append(current_protocol)
            
            #### BEGIN copy electrophysiology
            # copy selected electrophysiology segments, average if necessary, then
            # store in the protocol_ephys_segments list ot be assigned later to
            # the electrophysiology field of the new data
            if len(self.electrophysiology.segments):
                if average:
                    # NOTE: 2018-06-15 09:59:21
                    # "segments" here is a list even if it has only one segment!
                    segments = average_segments([copy.deepcopy(self.electrophysiology.segments[f]) for f in kprotocol_frames])
                    #segments = average_segments([neo_copy(self.electrophysiology.segments[f]) for f in kprotocol_frames])
                    
                    if len(segments) > 1:
                        raise RuntimeError("averaging segments for protocol %s yielded in electrophysiology block more than one segment!" % current_protocol.name)
                    
                    for seg in segments:
                        seg.annotations["averaged"] = True
                        seg.annotations["failures_excluded"] = exclude_failures
                        seg.annotations["EPSCaT_fail_test"] = test_component
                        seg.name = current_protocol.name
                        seg.description = "%s_averaged" % current_protocol.name
                        seg.index = kprotocol
                        
                        
                else:
                    segments = [copy.deepcopy(self.electrophysiology.segments[f]) for f in kprotocol_frames]
                    #segments = [neo_copy(self.electrophysiology.segments[f]) for f in kprotocol_frames]
                    
                    for kseg, seg in enumerate(segments):
                        seg.name = current_protocol.name
                        seg.annotations["failures_excluded"] = exclude_failures
                        seg.annotations["EPSCaT_fail_test"] = test_component
                        seg.description = "%s frame %d" % (current_protocol.name, new_protocol_segments_index[kseg])
                        seg.index = new_protocol_segments_index[kseg]
                
            else:
                segments = list()
                
            protocol_ephys_segments += segments
            
            #### END copy electrophysiology
            
            # NOTE: 2018-06-17 20:05:19
            # copy (and average if needed) scans and scene data signals (if they have been analysed)
            
            #### BEGIN copy scans block
            if len(self.scansBlock.segments):
                # NOTE: 2018-08-21 12:26:43
                # some analysis units may not have a signal in a given segment; 
                # we therefore should FIRST extract the analogsignal (if found)
                # into a new set of segments and average these if necessary
                
                segments = [copy.deepcopy(self.scansBlock.segments[f]) for f in kprotocol_frames]
                #segments = [neo_copy(self.scansBlock.segments[f]) for f in kprotocol_frames]
                
                segments = list()
                
                for f in kprotocol_frames:
                    seg = copy.deepcopy(self.scansBlock.segments[f])
                    #seg = neo_copy(self.scansBlock.segments[f])
                    
                    signals = seg.analogsignals
                    
                    if analysis_unit.landmark is not None and len(signals) > 1:
                        keep_signal_ndx = get_index_of_named_signal(seg, analysis_unit.landmark.name, silent=True)
                    
                        if keep_signal_ndx is not None:
                            # epscat found for this analysis unit
                            signal = signals[keep_signal_ndx]
                            seg.analogsignals = [signal]
                            segments.append(seg)
                            
                        else:
                            continue
                            
                    else:
                        if len(signals) > 1:
                            warnings.warn("Too many EPSCaTs (%d) for analysis unit %s with no landmark, in %s" % (len(signals), analysis_unit.name, self.name), RuntimeWarning)
                            continue
                        
                        segments.append(seg)
                            
                if average:
                    segments = average_segments(segments)
                    
                    if len(segments) > 1:
                        raise RuntimeError("averaging segments for protocol %s in scans block yielded more than one segment!" % current_protocol.name)
                    
                    for seg in segments:
                        # NOTE: 2018-08-21 12:43:24
                        # epscat signal for specified unit extracted above see NOTE: 2018-08-21 12:26:43
                        seg.annotations["averaged"] = average
                        seg.annotations["failures_excluded"] = exclude_failures
                        seg.annotations["EPSCaT_fail_test"] = test_component
                        seg.name = current_protocol.name
                        seg.description = "%s_averaged" % current_protocol.name
                        seg.index = kprotocol
                        
                else:
                    for kseg, seg in enumerate(segments):
                        # NOTE: 2018-08-21 12:43:55
                        # epscat signal for specified unit extracted above see NOTE: 2018-08-21 12:26:43
                        seg.annotations["averaged"] = average
                        seg.annotations["failures_excluded"] = exclude_failures
                        seg.annotations["EPSCaT_fail_test"] = test_component
                        seg.name  = current_protocol.name
                        seg.description = "%s frame %d" % (current_protocol.name, new_protocol_segments_index[kseg])
                        seg.index = new_protocol_segments_index[kseg]
                        
            else:
                segments = list()
                
            protocol_scan_data_segments += segments
            
            #### END copy scans block
            
            #### BEGIN  copy scene block
                
            if len(self.sceneBlock.segments):
                if average:
                    segments = average_segments([copy.deepcopy(self.sceneBlock.segments[f]) for f in kprotocol_frames])
                    #segments = average_segments([neo_copy(self.sceneBlock.segments[f]) for f in kprotocol_frames])
                    
                    if len(segments) > 1:
                        raise RuntimeError("averaging segments for protocol %s in scene block yielded more than one segment!" % current_protocol.name)
                    
                    for seg in segments:
                        if analysis_unit.landmark is not None:
                            # remove signals NOT associated to this unit
                            # the association is based on name: landmark name is also
                            # the name of the signal
                            signals = seg.analogsignals
                            keep_signal_ndx = get_index_of_named_signal(seg, analysis_unit.landmark.name, silent=True)
                            
                            if keep_signal_ndx is not None:
                                signal = signals[keep_signal_ndx]
                                seg.analogsignals = [signal]
                            
                        seg.annotations["averaged"] = average
                        seg.annotations["failures_excluded"] = exclude_failures
                        seg.annotations["EPSCaT_fail_test"] = test_component
                        seg.name = current_protocol.name
                        seg.description = "%s_averaged" % current_protocol.name
                        seg.index = kprotocol
                    
                else:
                    segments = [copy.deepcopy(self.sceneBlock.segments[f]) for f in kprotocol_frames]
                    #segments = [neo_copy(self.sceneBlock.segments[f]) for f in kprotocol_frames]
                    
                    for kseg, seg in enumerate(segments):
                        if analysis_unit.landmark is not None:
                            # remove signals NOT associated to this unit
                            # the association is based on name: landmark name is also
                            # the name of the signal
                            signals = seg.analogsignals
                            keep_signal_ndx = get_index_of_named_signal(seg, analysis_unit.landmark.name, silent=True)
                            
                            if keep_signal_ndx is not None:
                                signal = signals[keep_signal_ndx]
                                seg.analogsignals = [signal]
                            
                        seg.annotations["averaged"] = average
                        seg.annotations["failures_excluded"] = exclude_failures
                        seg.annotations["EPSCaT_fail_test"] = test_component
                        seg.name  = current_protocol.name
                        seg.description = "%s frame %d" % (current_protocol.name, new_protocol_segments_index[kseg])
                        seg.index = new_protocol_segments_index[kseg]
                        
            else:
                segments = list()
                
            protocol_scene_data_segments += segments
            
            #### END copy scene block
            
            # NOTE: 2018-06-15 20:18:39 TODO
            # create an epoch on these profiles to mark the position of the original 
            # landmak (if used)
            # FIXME: cannot use neo.Epoch objects as they are defined in the
            # time domain only
            # TODO: define a class with the same functionality as Epoch, but using
            # other domain as well e.g., not just time, but also space, frequencies, 
            # (for the Fourier domain) etc.
            # TODO while at it, also create an equivalent for neo.SpikeTrain as 
            # well, to be used for domains other than time.
            
            #### BEGIN copy scan region profiles in scan data
            if len(self.scanRegionScansProfiles.segments) > 0:
                if average:
                    try:
                        segments = average_segments([copy.deepcopy(self.scanRegionScansProfiles.segments[f]) for f in kprotocol_frames])
                        #segments = average_segments([neo_copy(self.scanRegionScansProfiles.segments[f]) for f in kprotocol_frames])
                        
                    except:
                        segments = []
                    
                    if len(segments) > 1:
                        raise RuntimeError("averaging segments for protocol %s in scene block yielded more than one segment!" % current_protocol.name)
                    
                    for seg in segments:
                        seg.annotations["averaged"] = True
                        seg.annotations["failures_excluded"] = exclude_failures
                        seg.annotations["EPSCaT_fail_test"] = test_component
                        seg.name = current_protocol.name
                        seg.description = "%s_averaged" % current_protocol.name
                        seg.index = kprotocol
                    
                else:
                    segments = [copy.deepcopy(self.scanRegionScansProfiles.segments[f]) for f in kprotocol_frames]
                    #segments = [neo_copy(self.scanRegionScansProfiles.segments[f]) for f in kprotocol_frames]
                    
                    for kseg, seg in enumerate(segments):
                        seg.name  = current_protocol.name
                        seg.description = "%s frame %d" % (current_protocol.name, new_protocol_segments_index[kseg])
                        seg.index = new_protocol_segments_index[kseg]
                        
            else:
                segments = list()
                
            protocol_scanline_scans_profiles += segments
            
            #### END copy scan region profiles in scan data 
            
            #### BEGIN copy scan region profile in scene data
            if len(self.scanRegionSceneProfiles.segments) > 0:
                if average:
                    segments = average_segments([copy.deepcopy(self.scanRegionSceneProfiles.segments[f]) for f in kprotocol_frames])
                    #segments = average_segments([neo_copy(self.scanRegionSceneProfiles.segments[f]) for f in kprotocol_frames])
                    
                    if len(segments) > 1:
                        raise RuntimeError("averaging segments for protocol %s in scene block yielded more than one segment!" % current_protocol.name)
                    
                    for seg in segments:
                        seg.annotations["averaged"] = True
                        seg.annotations["failures_excluded"] = exclude_failures
                        seg.annotations["EPSCaT_fail_test"] = test_component
                        seg.name =current_protocol.name
                        seg.description = "%s_averaged" % current_protocol.name
                        seg.index = kprotocol
                    
                else:
                    segments = [copy.deepcopy(self.scanRegionSceneProfiles.segments[f]) for f in kprotocol_frames]
                    #segments = [neo_copy(self.scanRegionSceneProfiles.segments[f]) for f in kprotocol_frames]
                    
                    for kseg, seg in enumerate(segments):
                        seg.name  = current_protocol.name
                        seg.description = "%s frame %d" % (current_protocol.name, new_protocol_segments_index[kseg])
                        seg.index = new_protocol_segments_index[kseg]
                        
            else:
                segments = list()
                
            protocol_scanline_scene_profiles += segments
            
            #### END copy scan region profile in scene data
            
            #### BEGIN set up destination image data:
            # 1) figure out the shape
            # 2) figure out the region of the source image to be copied over 
            #    to the new data
            #
            # WARNING:
            #   scene and scans are lists of VigraArray:
            #   they contain either:
            #       one element of multi-channel VigraArrays (or single-channel VigraArray
            #           if image data only has one channel)
            #       several single-channel VigraArrays when channel data are stored separately
            #
            # CAUTION: 
            #   by definition, VigraArray storing the scene data can have EITHER:
            #   ONE frame (i.e. same frame for all scans frames) OR AS MANY FRAMES AS
            #   the VigraArrays storing the scans data
            #
            # ATTENTION We also set up the image regions to be copied over
            #
            # we create a list each for scene data:
            #   source X range, source Y range, destination X range, destination Y range
            #   
            # and the same for scans data
            #
            # each of these lists has as many elements as there are in self.scene and self.scans
            # lists, respectively (see above about the image data layout)
            #
            # in turn, each element of the list is also a list with as many elements 
            # (python slice objects) as there will be frames copied from the original data
            # (the copied frames are the ones that correspond to the selected analysis segments
            # at the beginning of this function)
            #
            # the slice objects are set according to the landmark parameters (if a landmark exists)
            # or are set to the full size of the frame -- we use slice object because they are 
            # easy to use to index into the vigra arrays
            #
            # For now, only vertical cursors in the scans images are used as analysis unit
            # landmarks, whereas the scene is copied entirely.
            #
            # I believe this approach is scalable for any PlanarGraphics type, in
            # both scene and scans, when analysis units will bne enabled in both scene 
            # and scans.
            
            destSceneShape = [int(s) for s in self.scene[0].shape]
            
            if self.sceneFrames > 1:
                destSceneShape[self.sceneFrameAxisIndex] = len(kprotocol_frames)
                
                srcSceneXRanges = [[slice(0, img.shape[0]) for f in range(len(kprotocol_frames))] for img in self.scene]
                srcSceneYRanges = [[slice(0, img.shape[1]) for f in range(len(kprotocol_frames))] for img in self.scene]
                
                destSceneXRanges = [[slice(0, img.shape[0]) for f in range(len(kprotocol_frames))] for img in self.scene]
                destSceneYRanges = [[slice(0, img.shape[1]) for f in range(len(kprotocol_frames))] for img in self.scene]
                
                
            else:
                destSceneShape[self.sceneFrameAxisIndex] = 1
            
                srcSceneXRanges = [[slice(0, img.shape[0])] for img in self.scene]
                srcSceneYRanges = [[slice(0, img.shape[1])] for img in self.scene]
                
                destSceneXRanges = [[slice(0, img.shape[0])] for img in self.scene]
                destSceneYRanges = [[slice(0, img.shape[1])] for img in self.scene]
                
            avgSceneShape = [int(s) for s in self.scene[0].shape]
            
            avgSceneShape[self.sceneFrameAxisIndex] = 1
                
            # *** #
            
            destScansShape = [int(s) for s in self.scans[0].shape]
            
            destScansShape[self.scansFrameAxisIndex] = len(kprotocol_frames)
            
            avgScansShape = [int(s) for s in self.scans[0].shape]
            
            avgScansShape[self.scansFrameAxisIndex] = 1
            
            if analysis_unit.landmark is None:
                srcScansXRanges = [[slice(0, img.shape[0]) for f in range(len(kprotocol_frames))] for img in self.scans]
                srcScansYRanges = [[slice(0, img.shape[1]) for f in range(len(kprotocol_frames))] for img in self.scans]
                
                destScansXRanges = [[slice(0, img.shape[0]) for f in range(len(kprotocol_frames))] for img in self.scans]
                destScansYRanges = [[slice(0, img.shape[1]) for f in range(len(kprotocol_frames))] for img in self.scans]
                
            elif isinstance(analysis_unit.landmark, pgui.Cursor):
                if analysis_unit.landmark.type == pgui.GraphicsObjectType.vertical_cursor:
                    # FIXME boundary problems on X
                    # NOTE: best is to avoid cursors too close to either boundary
                    
                    # NOTE: 2018-08-04 23:52:40
                    # allow for frame-associated variations in the xwindow: take the maximum window size here so that
                    # we concatenate images with equal spatial extent
                    
                    states = [s for s in (analysis_unit.landmark.getState(f) for f in kprotocol_frames)]
                    
                    xwindows = [s.xwindow for s in states if s is not None]
                    
                    if len(xwindows):
                        xwindow = max(xwindows)
                    
                    srcScansXRanges = [[slice(int(max([(s.x - xwindow/2), 0])), int(min([s.x + xwindow/2+1, img.shape[0]]))) for
                                        s in (analysis_unit.landmark.getState(f) for f in kprotocol_frames)]
                                      for img in self.scans]
                    
                    windows = [[a.stop-a.start for a in sl] for sl in srcScansXRanges]
                    
                    srcScansYRanges = [[slice(0, img.shape[1]) for f in range(len(kprotocol_frames))] for img in self.scans]
                    
                    destScansShape[0] = int(max([int(max([windows[kimg][kstate] for 
                                                          kstate, s in enumerate([analysis_unit.landmark.getState(f) for f in kprotocol_frames])]))
                                                for kimg, img in enumerate(self.scans)]))
                    
                    avgScansShape[0] = destScansShape[0]
                    
                    center = destScansShape[0]/2
                    
                    # make sure destScansXRanges comply with srcScansXRanges
                    destScansXRanges = [[slice(int(max([center-windows[kimg][kstate]/2,0])), int(min([center + windows[kimg][kstate]/2, destScansShape[0]])))
                                         for kstate, s in enumerate([analysis_unit.landmark.getState(f) for f in kprotocol_frames])]
                                        for kimg, img in enumerate(self.scans)]
                    
                    destScansYRanges = [[slice(0, img.shape[1]) for f in range(len(kprotocol_frames))] for img in self.scans]
                
                else:
                    # TODO FIXME
                    # NOTE 2018-05-31 21:46:11
                    # implement code for other planargraphics landmark types as well
                    raise NotImplementedError("Only vertical cursor landmarks are supported, for now")
            
            else:
                raise NotImplementedError("Only pictgui.Cursor landmarks are supported, for now")
                
            #### END set up destination image data
            
            #### BEGIN copy image data
            # this is destination scene for the current kprotocol!
            destScene = [vigra.VigraArray(destSceneShape, order=img.order,
                                          init=True, value=np.nan,
                                          axistags=img.axistags)
                        for img in self.scene]
            
            # this is destination scan for the current kprotocol!
            destScans = [vigra.VigraArray(destScansShape, order=img.order,
                                          init=True, value=np.nan,
                                          axistags=img.axistags)
                        for img in self.scans]
            
            if self.sceneFrames == 1:
                for ks, img in enumerate(self.scene):
                    destScene[ks].bindAxis(self.sceneFrameAxis,0)[destSceneXRanges[ks][0], destSceneYRanges[ks][0], ...] = \
                        img.bindAxis(self.sceneFrameAxis, 0)[srcSceneXRanges[ks][0], destSceneYRanges[ks][0], ...]
                    
                    if destScene[ks].channelIndex == destScene[ks].ndim:
                        destScene[ks].insertChannelAxis()
                        axcal = AxesCalibration(img.axistags["c"])
                        axcal.calibrateAxis(destScene[ks].axistags["c"])
                        
                    
            else:
                for kf, frame in enumerate(kprotocol_frames):
                    for ks, img in enumerate(self.scene):
                        destScene[ks].bindAxis(self.sceneFrameAxis, kf)[destSceneXRanges[ks][kf], destSceneYRanges[ks][kf], ...] = \
                            img.bindAxis(self.sceneFrameAxis, frame)[srcSceneXRanges[ks][kf], srcSceneYRanges[ks][kf], ...]
                        
            for ks, img in enumerate(self.scene):
                for axistag in img.axistags:
                    src_axiscal = AxesCalibration(axistag)
                    src_axiscal.calibrateAxis(destScene[ks].axistags[axistag.key])
                        
            for kf, frame in enumerate(kprotocol_frames):
                for ks, img in enumerate(self.scans):
                    destScans[ks].bindAxis(self.scansFrameAxis, kf)[destScansXRanges[ks][kf], destScansYRanges[ks][kf], ...] = \
                        img.bindAxis(self.scansFrameAxis, frame)[srcScansXRanges[ks][kf], destScansYRanges[ks][kf], ...]
                        
            for ks, img in enumerate(self.scans):
                for axistag in img.axistags:
                    src_axiscal = AxesCalibration(axistag)
                    src_axiscal.calibrateAxis(destScans[ks].axistags[axistag.key])
                        
            #### END copy image data
                        
            #### BEGIN averaging data
            if average:
                #### BEGIN average scene image data
                if self.sceneFrames > 1:
                    destAveragedScene = [vigra.VigraArray(avgSceneShape, order=img.order,
                                            init=True, value=np.nan,
                                            axistags=img.axistags)
                                        for img in self.scene]
                    
                    for ks in range(len(self.scene)):
                        avg_image_data = np.nanmean(destScene[ks], axis = self.sceneFrameAxis)
                        destAveragedScene[ks].bindAxis(self.sceneFrameAxis,0)[:] = avg_image_data[:]
                        destAveragedScene[ks].insertChannelAxis()
                        
                else:
                    destAveragedScene = destScene
                    
                for ks, img in enumerate(self.scene):
                    for axistag in img.axistags:
                        src_axiscal = AxesCalibration(axistag)
                        src_axiscal.calibrateAxis(destAveragedScene[ks].axistags[axistag.key])
                        
                for ks in range(len(self.scene)):
                    protocol_scene_data_image_frames[ks].append(destAveragedScene[ks])
                    
                #### END average scene image data
                
                #### BEGIN average scans image data

                destAveragedScans = [vigra.VigraArray(avgScansShape, order=img.order,
                                          init=True, value=np.nan,
                                          axistags=img.axistags)
                                    for img in self.scans]
                
                for ks in range(len(self.scans)):
                    avg_image_data = np.nanmean(destScans[ks], axis=self.sceneFrameAxis).insertChannelAxis()
                    destAveragedScans[ks].bindAxis(self.scansFrameAxis, 0)[:] = avg_image_data[:]
                    destAveragedScans[ks].insertChannelAxis()
                    
                for ks, img in enumerate(self.scans):
                    for axistag in img.axistags:
                        src_axiscal = AxesCalibration(axistag)
                        src_axiscal.calibrateAxis(destAveragedScans[ks].axistags[axistag.key])
                        
                for ks in range(len(self.scans)):
                    protocol_scans_data_image_frames[ks].append(destAveragedScans[ks])
                    
                #### END average scans image data
                
            else: # no averaging
                for ks in range(len(self.scene)):
                    protocol_scene_data_image_frames[ks].append(destScene[ks])
                    
                for ks in range(len(self.scans)):
                    protocol_scans_data_image_frames[ks].append(destScans[ks])
                
            # update the strided counter
            added_frames += len(kprotocol_frames)
            
            #### END averaging data

        #
        # NOTE: 2018-06-17 19:46:20
        # END data copy loop
        
        # NOTE: 2018-06-17 19:46:48
        # BEGIN  copy PlanarGraphics objects, start setting up result's 
        # name attribute
        #
        scan_region = None
        
        if self.scanRegion is not None:
            scan_region = self.scanRegion.copy()
            
            if average:
                # FIXME for now, we just keep ALL Path elements - overhead?
                # but this should be done more elegantly
                scan_region.elementsFrameIndices = [f for f in range(len(selected_protocols_and_frames))]
                
            else:
                scan_region.elementsFrameIndices = [f for f in range(added_frames)]
        
        # dictionaries with the other PlanarGraphics to be copied over to the returned data
        new_scene_rois      = collections.OrderedDict()
        new_scene_cursors   = collections.OrderedDict()
        new_scans_rois      = collections.OrderedDict()
        new_scans_cursors   = collections.OrderedDict()
        
        # the name for the returned data
        new_name = list()
        new_name.append(self.name)
        
        unit_landmark = analysis_unit.landmark

        if unit_landmark is None:
            # for data-wide analysis unit, copy all planar graphics to the new data
            for o in self.sceneCursors.items():
                src_obj = o[1]
                
                # copy the object if any of its frames were among the selected ones.
                if any([f in selected_frames_index_list for f in src_obj.frameIndices]):
                    obj = src_obj.copy()
                    
                    obj = self._extract_unit_adapt_landmark_frames_(obj, src_obj, 
                                                                      selected_protocols_and_frames,
                                                                      average=average)
                    
                    new_scene_cursors[obj.name] = obj
                    
            for o in self.sceneRois.items():
                src_obj = o[1]
                
                if any([f in selected_frames_index_list for f in src_obj]):
                    obj = src_obj.copy()
                    
                    obj = self._extract_unit_adapt_landmark_frames_(obj, src_obj, 
                                                                      selected_protocols_and_frames,
                                                                      average=average)
                    
                    new_scene_rois[obj.name] = obj
                    
            for o in self.scansRois.items():
                src_obj = o[1]
                
                if any([f in selected_frames_index_list for f in src_obj.frameIndices]):
                    obj = src_obj.copy()
                    
                    obj = self._extract_unit_adapt_landmark_frames_(obj, src_obj, 
                                                                      selected_protocols_and_frames,
                                                                      average=average)
                    
                    new_scans_rois[obj.name] = obj

            for o in self.scansCursors.items():
                src_obj = o[1]
                
                if any([f in selected_frames_index_list for f in src_obj.frameIndices]):
                    obj = src_obj.copy()
                    
                    obj = self._extract_unit_adapt_landmark_frames_(obj, src_obj, selected_protocols_and_frames, 
                                                                      average=average,
                                                                      with_links=True, 
                                                                      linked_scene_cursors_dict=new_scene_cursors,
                                                                      linked_scene_rois_dict=new_scene_rois,
                                                                      scan_region = scan_region)
                    
                    new_scans_cursors[obj.name] = obj
                    
            result._analysis_units_ = set([u.copy() for u in self.analysisUnits])
            
            result._analysis_unit_.unit_type = self.analysisUnit().unit_type
        
        elif unit_landmark.type == pgui.GraphicsObjectType.vertical_cursor:
            # extracted data should be devoid of the landmark used to define the 
            # analysis unit 
            #
            # NOTE: 2018-06-17 20:36:59
            # FIXME/TODO: currently only scans vertical cursors are supported
            # TODO copy all landmarks EXCEPT for the one that is used to define the 
            # TODO extracted image region 
            # TODO CAUTION when doing so, make sure the copied landmarks _ARE_ 
            # TODO within the coordinated of the copied region
            
            # this is the landmark used to determine the copied image region
            landmark_name = analysis_unit.landmark.name 

            if len(landmark_name.strip()) > 0:
                new_name.append(landmark_name) # append its name to the results "name" attribute
            
            # copy scene planar graphics, but CAUTION they will NOT be used
            # as link objects to the landmak used in the analysis unit we're 
            # extracting
            # in fact, for now they're not used as links for anything
            # TODO this must change in the future, when we wil be able to define
            # analysis units orthogonal/independent to this one
            for o in self.sceneRois.items():
                src_obj = o[1]
                
                if any([f in selected_frames_index_list for f in obj.frameIndices]):
                    obj = src_obj.copy()
                    
                    obj = self._extract_unit_adapt_landmark_frames_(obj, src_obj, 
                                                                      selected_protocols_and_frames,
                                                                      average=average)
                    
                    new_scene_rois[obj.name] = obj
                    
            # keep the scene graphics linked to the landmark
            if len(analysis_unit.landmark.linkedObjects):
                for link_obj in analysis_unit.landmark.linkedObjects:
                    if isinstance(link_obj, pgui.Cursor):
                        if link_obj in self.sceneCursors.values():
                            # NOTE: 2018-06-18 09:40:27
                            # there is a problem here as the linked cursor 
                            # of the landmark MAY be just a copy (from old API)
                            # and NOT found in self.sceneCursors
                            # this turns out in the landmark of the analysis unit
                            # NOT being the same as the cursor inside the data's
                            # dictionaries
                            obj = link_obj.copy()
                            obj = self._extract_unit_adapt_landmark_frames_(obj, link_obj,
                                                                              selected_protocols_and_frames,
                                                                              average=average)
                            new_scene_cursors[obj.name] = obj
                                
                    else:
                        if link_obj in self.sceneRois.values():
                            obj = link_obj.copy()
                            obj = self._extract_unit_adapt_landmark_frames_(obj, link_obj,
                                                                              selected_protocols_and_frames,
                                                                              average=average)

                            new_scene_rois[obj.name] = obj
                            
            # copy landmark-defined analysis unit as the default analysis_unit
            result.analysisUnit().name = analysis_unit.name

            result.analysisUnit().unit_type = analysis_unit.unit_type
            
            #print("ScanData.extractAnalysisUnit analysis unit name %s" % analysis_unit.name)
            for f in analysis_unit.descriptors.items():
                #print("ScanData.extractAnalysisUnit analysis unit %s descriptor %s = %s" % (analysis_unit.name, f[0], f[1]))
                result._analysis_unit_.setDescriptor(f[0], f[1])
        else:
            # TODO
            # NOTE 2018-05-31 21:46:54: 
            # runtime exception is raised above when same clause is reached
            # see NOTE 2018-05-31 21:46:11
            pass
        
        # 
        # NOTE: 2018-06-17 19:48:13
        # END copy PlanarGraphics objects
        
        # NOTE: 2018-06-17 19:48:37
        # BEGIN set up result's name attribute
        #
        if protocol_names_str not in self.name:
            new_name.append(protocol_names_str)
            
        if average and "averaged" not in self.name:
            new_name.append("averaged")
            
        if isinstance(name, str) and len(name.strip()) > 0:
            result.name = name
            
        else:
            result.name = "_".join(new_name)
            
        #
        # END finish setting up name
        
        # NOTE: 2018-06-17 19:49:05
        # BEGIN assign data into ScanData stub "result"
        #
        
        # BEGIN assign image data to result
        
        # BEGIN assign scene images
        targetScene = list()
        
        for ks in range(len(self.scene)):
            #print("ScanData.extractAnalysisUnit protocol_scene_data_image_frames in scene stack %d" % (len(protocol_scene_data_image_frames[ks]), ks))
            print("scene channel %d images for protocol" % ks, len(protocol_scene_data_image_frames[ks]))
            if len(protocol_scene_data_image_frames[ks]) == 0:
                continue
            
            scene_images = protocol_scene_data_image_frames[ks]
            img = concatenateImages(*scene_images, axis = self.sceneFrameAxis)
            
            print("targetSceneImage shape", img.shape)
            
            targetScene.append(img)
            
            #if len(protocol_scene_data_image_frames[ks]) == 1:
                #targetScene.append(protocol_scene_data_image_frames[ks][0])
            #else:
                #img = concatenateImages(*protocol_scene_data_image_frames[ks], axis = self.sceneFrameAxis)
                #targetScene.append(img)
        
        print("targetScene elements", len(targetScene))
        # END assign scene images
        
        
        # BEGIN assign scans images
        targetScans = list()
        
        for ks in range(len(self.scans)):
            #print("ScanData.extractAnalysisUnit protocol_scans_data_image_frames in scans stack %d" % (len(protocol_scans_data_image_frames[ks]), ks))
            
            if len(protocol_scans_data_image_frames[ks]) == 0:
                continue
            
            widths = [img.width for img in protocol_scans_data_image_frames[ks]]
            
            if not all ([w == widths[0] for w in widths]):
                maxWidth = max(widths)
                
                padded = list()
                
                for img in protocol_scans_data_image_frames[ks]:
                    if img.width < maxWidth:
                        pad = maxWidth - img.width
                        
                        pad_pre = pad//2
                        pad_post = pad//2 + pad%2
                        
                        new_img = padAxis(img, "x", pad_pre, pad_post, np.nan)
                        
                        padded.append(new_img)
                        
                    else:
                        padded.append(img)
                        
                images = padded
                        
            else:
                images = protocol_scans_data_image_frames[ks]
                
            img = concatenateImages(*images, axis = self.scansFrameAxis)
            
            print("targetScansImage shape" , img.shape)

            targetScans.append(img)
            
        print("targetScans elements", len(targetScans))
        
        # END assign scans images
        
        # NOTE: 2018-06-17 15:57:27
        # assign image data
        # ATTENTION do this first because _parse_image_arrays_ will reset the
        # data either derived from current image data (this IS a design feature):
        # _scans_block_, _scene_block_, 
        # _scan_region_scans_profiles_, and _scan_region_scene_profiles_
        #
        
        result._parse_image_arrays_(targetScene, targetScans, 
                                        sceneFrameAxis=self.sceneFrameAxis,
                                        scansFrameAxis=self.scansFrameAxis)
        # END image data
        
        # BEGIN assign scan profiles to result
        # NOTE: 2018-06-17 16:22:49
        # do this AFTER assigning image data (via _parse_image_arrays_)
        # see NOTE: 2018-06-17 15:57:27 and _parse_image_arrays_ docstring
        # to understand why
        result._scan_region_scans_profiles_.segments = protocol_scanline_scans_profiles
        result._scan_region_scene_profiles_.segments = protocol_scanline_scene_profiles
        
        result._scans_block_.segments = protocol_scan_data_segments
        result._scene_block_.segments = protocol_scene_data_segments
        
        # END assign scan profiles
        
        # BEGIN assign planar graphics to result
        # NOTE: 2018-06-17 16:23:32
        # assign PlanarGraphics objects
        result.scanRegion = scan_region
        
        # the __new__... dictionaries here have been populated above, 
        # see NOTE: 2018-06-17 19:46:48 and NOTE: 2018-06-17 20:36:59
        for obj in sorted([o for o in new_scene_cursors.values()], key=lambda x: x.name):
            result._scenecursors_[obj.name] = obj
            
        for obj in sorted([o for o in new_scene_rois.values()], key=lambda x: x.name):
            result._scenerois_[obj.name] = obj

        for obj in sorted([o for o in new_scans_rois.values()], key=lambda x: x.name):
            result._scansrois_[obj.name] = obj
            
        for obj in sorted([o for o in new_scans_cursors.values()], key=lambda x: x.name):
            result._scanscursors_[obj.name] = obj
            
        # END planar graphics
        
        # BEGIN assign electrophysiology data to result
        # NOTE: 2018-06-17 16:23:45
        # assign the electrophysiology to the result
        result._electrophysiology_.segments[:] = protocol_ephys_segments
        
        ret_unit = result.analysisUnit() # the AnalysisUnit of the entire result ScanData object
        
        # assign cell and field attributes 
        # the ScanData cell and field properties actually return references to
        # the unit's cell and field properties
        ret_unit.cell = self.analysisUnit().cell
        ret_unit.field = self.analysisUnit().field
        ret_unit.age = self.analysisUnit().age
        ret_unit.sourceID = self.analysisUnit().sourceID
        ret_unit.genotype = self.analysisUnit().genotype
        ret_unit.gender = self.analysisUnit().gender
        
        # force ret_unit's name to be that of the landmark (if present)
        if analysis_unit.landmark is not None:
            # we're already extracting a subset of data based on this unit's landmark
            ret_unit.name = analysis_unit.landmark.name.strip()
            
            # NOTE: 2018-06-17 20:42:45
            # TODO also copy other analysis units if they are WITHIN
            # the coordinates of the copied image region (given their frame indices
            # are also appropriate, see NOTE: 2018-06-17 20:36:59)
            # CAUTION  this needs to be properly thought through...
            
        else:
            # here, analysis_unit.landmark is None, meaning that we attempt to
            # "extract" the full extent of the data images.
            #
            # there are two alternatives here:
            # a) either there are no landmark-based units meaning this is a data-wide unit
            #
            # or:
            #
            # b) there are landmark-based units (meaning we just want to get the
            # whole data as it is, possibly with frames averaged per protocol, 
            # and possibly without the failed frames)
            #
            if len(self.analysisUnits) == 0:
                ret_unit.name  = self.analysisUnit().name.strip() # reference to result.analysisUnit()
                
            else:
                # case when the entire data is being returned
                for u in self.analysisUnits:
                    if u.inScene:
                        current_landmark_names = [l for l in result.sceneRois.keys()] + [l for l in result.sceneCursors.keys()]
                        
                        if u.landmark.name not in current_landmark_names:
                            new_landmark = result.adoptLandmark(self, u.landmark.name)
                            
                        else:
                            current_landmarks = [l for l in result.sceneRois.values()] + [l for l in result.sceneCursors.values()]
                            
                            new_landmark = [l for l in current_landmarks if l.name == u.landmark.name][0]
                                
                    else:
                        current_landmark_names = [l for l in result.scansRois.keys()] + [l for l in result.scansCursors.keys()]
                        if u.landmark.name not in current_landmark_names:
                            new_landmark = result.adoptLandmark(self, u.landmark.name)
                            
                        else:
                            current_landmarks = [l for l in result.scansRois.values()] + [l for l in result.scansCursors.values()]
                            
                            new_landmark = [l for l in current_landmarks if l.name == u.landmark.name][0]

                    new_unit = u.copy()
                    new_unit.landmark = new_landmark
                            
                    result._analysis_units_.add(new_unit)
                        
        if analysis_unit.landmark is not None:
            ret_unit.unit_type = UnitTypes[landmark_name[0]]
        
        for d in analysis_unit.descriptors.items():
            ret_unit.setDescriptor(d[0], d[1])
            
        ret_unit.setDescriptor("averaged", average)
        
        # END analysis unit data
        
        # END assign data into ScanData stub "result"
        
        if progressSignal is not None and isinstance(progressValue, int):
            progressSignal.emit(progressValue)
        
        result.triggerProtocols = protocol_list
        #print("extract analysis unit", result.name)
        return result
    
    def extractAnalysisUnits(self,  average=False, 
                                    exclude_failures=False, test_component="any", 
                                    simple_name=False,
                                    progressSignal = None):
        """Extract all individual analysis units from the scans data set.
        
        Delegates to self.extractAnalysisUnit called on individual landmark-based
        analysis units, or on the (default) analysis unit based on the entire data
        if no landmark-based units were defined.
        
        
        
        TODO -- maybe Move this outside ScanData API -- make it entirely client (3rd party) code
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        The extracted data is output as ScanData by calling extractAnalysisUnit()
        
        NOTE: If the data has no landmark-based analysis units, returns self
        (a default AnalysisUnit is associated with the entire data set).
        
        FIXME TODO code for all ladmark types (cursor, rois) in either data set
        (scene or scans)
        
        Calls extractAnalysisUnit(...) behind the scenes. 
        
        See extractAnalysisUnit documentation for details.
        
        Named parameters:
        ================
        protocol: None (default), a datatypes.TriggerProtocol, or str: a name of an 
            existing TriggerProtocol in scandata.
        
            In addition, "protocol" can be the keyword "all", meaning that 
                analysis units are extracted SEPARATELY for each available protocol.
                
            NOTE: for this function, the default value for protocol is "all"
                
        average: boolean (default is False) -- as for self.exportScansAnalysisUnit() function
        
        The results are returned as a dictionary.
        
        To have the contents of the dictionary directly into your workspace, from
        the IPython console call:
        
        appWindow.workspace.update(d)
        
        where d is the returned variable from this function call.
        
        Returns None if no scans cursors are defined (landmarks, in the future).
        
        """
        
        #print("ScanData.extractAnalysisUnits simple_name", simple_name)
        if len(self.analysisUnits) == 0:
            if simple_name:
                result = self.extractAnalysisUnit(self.analysisUnit(), average=average,
                                               exclude_failures = exclude_failures,
                                               test_component=test_component,
                                               name = self.analysisUnit().name)
                
            else:
                result = self.extractAnalysisUnit(self.analysisUnit(), average=average,
                                               exclude_failures = exclude_failures,
                                               test_component=test_component)
                
            
        else:
            if simple_name:
                result = [self.extractAnalysisUnit(u, average=average, 
                                                exclude_failures = exclude_failures,
                                                test_component=test_component,
                                                name = u.name, 
                                                progressSignal=progressSignal,
                                                progressValue=k) for k, u in enumerate(self.analysisUnits)]
                
            else:
                result = [self.extractAnalysisUnit(u, average=average, 
                                                exclude_failures=exclude_failures,
                                                test_component=test_component,
                                                progressSignal = progressSignal,
                                                progressValue = k) for k, u in enumerate(self.analysisUnits)]

        #print("extract analysis units", result.name)
        return result
            
    #@safeWrapper
    def adoptAnalysisOptions(self, source):
        if not isinstance(source, ScanData):
            raise TypeError("Expecting a ScanData object; got %s instead" % type(source).__name__)
        
        # NOTE: a local copy is made by the property setter
        self.analysisOptions = source.analysisOptions 
        
    #@safeWrapper
    def adoptAnalysisUnits(self, source):
        """Imports copies of the landmark-based analysis units from the ScanData object "source".
        
        The landmark-based units in the source must have the same values for their
        "cell" and "field" attributes as this ScanData object.
        
        Existing units with the same name will be overwritten.
        
        Importing a unit will also import its underlying landmarks, if they do 
        not already exist with same name and type.
        
        """
        if not isinstance(source, ScanData):
            raise TypeError("Expecting a ScanData object; got %s instead" % type(source).__name__)
        
        if len(source._analysis_units_):
            if any([u.cell != self.analysisUnit().cell or u.field != self.analysisUnit().field for u in source._analysis_units_]):
                raise ValueError("Cannot adopt analysis units from ScanData with nonmatching cell or field attributes")
        
            for u in source._analysis_units_:
                # check whether this unit is landmak-based
                if u.landmark is None:
                    # reject units that are not associated with a landmark
                    continue
                
                #print("ScanData.adoptAnalysisUnits %s.adoptAnalysisUnits(%s): unit = %s" % (self.name, source.name, u.name))
                
                # check the protocols are OK
                # NOTE: 2018-07-12 13:30:58
                # need to relax here:
                # some protocols in the source may have been removed (or frames 
                # were removed and thus single-frame protocols were removed)
                # but this still should NOT preclude importing this unit: the unit
                # should be defined NOT by its protocols, but purely by its physical
                # association with a structure (i.e., a LOCATION in the scene/scans!!!)
                # 
                # instead, the association between protocols and analysis units
                # should be "advisory", just to allow for selective treatment of 
                # data according to the protocol.
                #
                # NOTE: once imported, the unit shuould then be asociated with the 
                # protocols that ALREADY EXIST in THIS data !!!
                
                #if not all([p in self.triggerProtocols for p in u.protocols]):
                    #raise ValueError("The AnalysisUnit %s associates protocols that do not exist in this ScanData object" % u.name)
                
                # check whether unit is associated with a scene or scans landmark
                if u.name in [u_.name for u_ in self._analysis_units_]:
                    self.removeAnalysisUnit(u.name, removeLandmark=True) # remove existing unit AND its landmark
                
                if u.inScene:
                    current_landmark_names = [l for l in self.sceneRois.keys()] + [l for l in self.sceneCursors.keys()]
                    
                    if u.landmark.name not in current_landmark_names:
                        new_landmark = self.adoptLandmark(source, u.landmark.name)
                        
                    else:
                        current_landmarks = [l for l in self.sceneRois.values()] + [l for l in self.sceneCursors.values()]
                        
                        new_landmark = [l for l in current_landmarks if l.name == u.landmark.name][0]
                            
                else:
                    current_landmark_names = [l for l in self.scansRois.keys()] + [l for l in self.scansCursors.keys()]
                    
                    if u.landmark.name not in current_landmark_names:
                        new_landmark = self.adoptLandmark(source, u.landmark.name)
                        
                    else:
                        current_landmarks = [l for l in self.scansRois.values()] + [l for l in self.scansCursors.values()]
                        
                        new_landmark = [l for l in current_landmarks if l.name == u.landmark.name][0]
                        
                #print("ScanData.adoptAnalysisUnits new_landmark", new_landmark)
                new_unit = u.copy()
                # assign the new landmark (which is a copy of the old landmark
                # adjusted for the current data)
                new_unit.landmark = new_landmark
                
                # remove stale reference to / copies of protocols from previous data
                new_unit.protocols.clear()
                
                if len(new_unit.landmark.frameIndices):
                    for frame_ndx in new_unit.landmark.frameIndices:
                        for p in self.triggerProtocols:
                            if frame_ndx in p.segmentIndices():
                                if p not in new_unit.protocols:
                                    new_unit.protocols.append(p)
                                    
                else:
                    new_unit.protocols[:] = self.triggerProtocols
                        
                
                self._analysis_units_.add(new_unit)
        
    @safeWrapper
    def adoptScansCursors(self, source):
        """Adopts scan cursors from "source" ScanData object.
        
        Does nothing if source has no scans cursors defined.
        
        """
        import gui.pictgui as pgui
        
        # NOTE: 2018-03-03 11:17:50
        # make sure we also adopt their linked objects!
        # use the strategy of self.copy() and self.adoptGraphicsObjects()
        from functools import partial as partial
        
        if not isinstance(source, ScanData):
            raise TypeError("Expecting a ScanData object; got %s instead" % type(source).__name__)
        
        # cache the new cursors; we replace old cursors at the very end, 
        # unless something went wrong, including a clash of cursor names
        
        new_objects = dict() 
        
        if len(source.scansCursors):
            for c in source.scansCursors.values():
                if c.name in self.scansCursors.keys():
                    self.removeCursor(c.name, scans=True)
                
                c1 = c.copy()
                c1.frameIndices - [None]
                
                if len(self.scans):
                    if c1.type == pgui.GraphicsObjectType.vertical_cursor:
                        if c1.height != self.scans[0].shape[1]:
                            c1.height = self.scans[0].shape[1]
                    
                    elif c1.type == pgui.GraphicsObjectType.horizontal_cursor:
                        if c1.width != self.scans[0].shape[0]:
                            c1.width = self.scans[0].shape[0]
                    
                    elif c1.type == pgui.GraphicsObjectType.crosshair_cursor:
                        if c1.width != self.scans[0].shape[0]:
                            c1.width = self.scans[0].shape[0]
                            
                        if c1.height != self.scans[0].shape[1]:
                            c1.height = self.scans[0].shape[1]
            
                if isinstance(self.scanRegion, PlanarGraphics):
                    links = [l for l in c.objectLinks.items()]
                    
                    for cc, link in links:
                        # see NOTE: 2018-07-02 08:36:58
                        # cc is the cursor linked TO
                        # link is a tuple of 3 elements as follows: 
                        #
                        # 1) partial_func:
                        # this is a partial function on the :
                        #   mapping function
                        #   the planar graphics mapped FROM (e.g. the scans cursor)
                        #   the planar graphics mapped TO (e.g. the scene cursor)
                        #
                        # 2) planar graphics object that constraints the mapping
                        #   e.g. the scan region / scan line trajectory (pgui.Path) etc
                        #
                        # 3) a dict with further keyword arguments (may be empty)
                        cc1 = cc.copy()
                        cc1.frameIndices=[None]
                        
                        if cc in source._scansrois_.values():
                            self._scansrois_[cc1.name] = cc1
                            
                        elif cc in source._scenerois_.values():
                            self._scenerois_[cc1.name] = cc1
                            
                        elif cc in source._scanscursors_.values():
                            self._scanscursors_[cc1.name] = cc1
                            
                        elif cc in source._scenecursors_.values():
                            self._scenecursors_[cc1.name] = cc1
                            
                        # NOTE 2018-03-03 10:29:09:
                        # the arguments for the partial (first element in l tuple)
                        # must be changed to contain the COPIED objects  !!!
                        pf = link[0]
                        
                        c1.linkToObject(cc1, pf.func, self.scanRegion)
                    
                new_objects[c1.name] = c1
            
            self.scansCursors.clear()
            self.scansCursors.update(new_objects)
            
    @safeWrapper
    def adoptLandmark(self, source, name):
        import gui.pictgui as pgui
        from functools import partial as partial
        
        def _inner_adopt_landmark_(src, obj, target):
            new_obj = obj.copy()
            new_obj.frameIndices=[None]
            
            #print("ScanData.adoptLandmark._inner_adopt_landmark_ new_obj", new_obj)
            
            if isinstance(new_obj, pgui.Cursor):
                if target == self.sceneCursors:
                    if len(self.scene):
                        if new_obj.height != self.scene[0].shape[1]:
                            new_obj.height = self.scene[0].shape[1]
                            
                        if new_obj.width != self.scene[0].shape[0]:
                            new_obj.width = self.scene[0].shape[0]
                        
                elif target == self.scansCursors:
                    if len(self.scans):
                        if new_obj.height != self.scans[0].shape[1]:
                            new_obj.height = self.scans[0].shape[1]
                            
                        if new_obj.width != self.scans[0].shape[0]:
                            new_obj.width = self.scans[0].shape[0]
        
            if isinstance(self.scanRegion, PlanarGraphics):
                cc_links = [(c, l) for (c,l) in obj.objectLinks.items()]
                for cc, link in cc_links:
                    # NOTE: 2018-07-02 08:36:58
                    # cc is the cursor linked TO
                    # link is a tuple of 3 elements as follows: 
                    #
                    # 1) partial_func:
                    # this is a partial function on the :
                    #   mapping function
                    #   the planar graphics mapped FROM (e.g. the scans cursor)
                    #   the planar graphics mapped TO (e.g. the scene cursor)
                    #
                    # 2) planar graphics object that constraints the mapping
                    #   e.g. the scan region / scan line trajectory (pgui.Path) etc
                    #
                    # 3) a dict with further keyword arguments (may be empty)
                    cc1 = cc.copy()
                    cc1.frameIndices=[None]
                    
                    if cc in src._scansrois_.values():
                        self._scansrois_[cc1.name] = cc1
                        
                    elif cc in src._scenerois_.values():
                        self._scenerois_[cc1.name] = cc1
                        
                    elif cc in src._scanscursors_.values():
                        self._scanscursors_[cc1.name] = cc1
                        
                    elif cc in src._scenecursors_.values():
                        self._scenecursors_[cc1.name] = cc1
                        
                    else:
                        continue
                        
                    
                    pf = link[0] # a partial = mapping func with fixed arguments: 
                    
                    new_obj.linkToObject(cc1, pf.func, self.scanRegion)
                    
                
            if name in target:
                old_target = target.pop(name, None)
                if old_target is not None:
                    frontends = old_target.frontends
                    for f in frontends:
                        f.removeFromWidget()
                
            target[new_obj.name] = new_obj
            
            return new_obj
        
        if not isinstance(source, ScanData):
            raise TypeError("'source' must be a ScanData object; got %s instead" % type(source).__name__)
        
        if not isinstance(name, str):
            raise TypeError("'name' must be a str; got %s instead" % type(name).__name__)
        
        if name in source.sceneCursors:
            obj = source.sceneCursor(name)
            new_obj = _inner_adopt_landmark_(source, obj, self.sceneCursors)
            
        if name in source.sceneRois:
            obj = source.sceneRoi(name)
            new_obj = _inner_adopt_landmark_(source, obj, self.sceneRois)
            
        if name in source.scansCursors:
            obj = source.scansCursor(name)
            new_obj = _inner_adopt_landmark_(source, obj, self.scansCursors)
            
        if name in source.scansRois:
            obj = source.scansRoi(name)
            new_obj = _inner_adopt_landmark_(source, obj, self.scansRois)
            
        return new_obj
            
    @safeWrapper
    def adoptLandmarks(self, source, data = "all", landmark_type="all", clear=False):
        """Adopts landmarks from source.
        
        Imports landmarks defined in source.
        
        Optionally, only landmarks assopciated with the scene or the scans
        will be imported. 
        
        Also optinally, only the rois or only the cursors will be imported.
        
        If a landmark in the source's scene or scans has the same name as a 
        current landmark in the scene ro scans, respectively, it will be overwritten.
        
        Otherwise, landmarks will be added next to the existing landmarks unless
        clear is True (in which case current roi/cursor landmarks in the scene/scans
        will be removed first)
        
        Parameters:
        ==========
        source: ScanData object
        
        Named parameters:
        =================
        data: str, one of "all" (default), "scene", "scans"
        
        landmark_type: str, one of "all" (default), "rois", "cursors"
        
        clear: bool (default False)
        
        
        
        """
        import gui.pictgui as pgui
        from functools import partial as partial
        
        def _landmarks_adopt_inner_(objdict, targetdict, do_clear):
            #import gui.pictgui as pgui
            new_objects = dict()
            
            for k, obj in objdict.items():
                if obj.name in targetdict:
                    targetdict.pop(s, None)
                    for f in obj.frontends:
                        f.removeFromWidget()
                        
                new_obj = obj.copy()
                
                skip_objects = list()
                
                if isinstance(self.scanRegion, PlanarGraphics):
                    links = [l for l in obj.objectLinks.items()]
                    #for c, link in obj.objectLinks.items():
                    for c, link in links:
                        # see NOTE: 2018-07-02 08:36:58
                        cc = c.copy()
                        
                        if c in source._scansrois_.values():
                            self._scansrois_[cc.name] = cc
                            
                        elif c in source._scenerois_.values():
                            self._scenerois_[cc.name] = cc
                            
                        elif c in source._scanscursors_.values():
                            self._scanscursors_[cc.name] = cc
                            
                        elif c in source._scenecursors_.values():
                            self._scenecursors_[cc.name] = cc
                            
                        skip_objects.append(cc)
                        
                        pf = link[0]
                        
                        new_obj.linkToObject(cc, pf.func, self.scanRegion)
                        
                if new_obj not in skip_objects:
                    new_objects[k] = new_obj
                    
                if do_clear:
                    for old_obj in targetdir.values():
                        for f in old_obj.frontends:
                            f.removeFromWidget()
                            
                    targetdir.clear()
                    
                targetdir.update(new_objects)
            
        if not isinstance(source, ScanData):
            raise TypeError("'source' expected to be a ScanData object; got %s instead" % type(source).__name__)
        
        if not isinstance(data, str):
            raise TypeError("'what' expected to be a str; got %s instead" % type(data).__name__)
        
        if data.lower() not in ("all", "scene", "scans"):
            raise ValueError("'what' expected to be one of 'all', 'scene', 'scans' (case-insensitive); got %s instead" % what)

        if not isinstance(landmark_type, str):
            raise TypeError("#landmark_type' expected to be a str; got %s instead" % type(landmark_type).__name__)
        
        if landmark_type.lower() not in ('all', 'rois', 'cursors'):
            raise ValueError("'landmark_type' expected to be one of 'all', 'rois', or 'cursors'; got %s instead" % landmark_type)
        
        if not isinstance(clear, bool):
            raise TypeError("'clear' expected to be a bool; got %s instead" % type(clear).__name__)
        
        cursors = None
        rois = None
        cursorstarget = None
        roistarget = None
        
        if data.lower() == "scene":
            if landmark_type.lower() == "all":
                rois = source.sceneRois
                roistarget = self.sceneRois
                
                cursors = source.sceneCursors
                cursorstarget = self.sceneCursors
                
            elif landmark_type.lower() == "rois":
                rois = source.sceneRois
                roistarget = self.sceneRois
                
            else:
                cursors = source.sceneCursors
                cursorstarget = self.sceneCursor
            
        elif data.lower() == "scans":
            if landmark_type == "all":
                rois = source.scansRois
                roistarget = self.scansRois
                cursors = source.scansCursors
                cursorstarget = self.scansCursors
                
            elif landmark_type == "rois":
                rois = source.scansRois
                roistarget = self.scansRois
                
            else:
                cursors = source.scansCursors
                cursorstarget = self.scansCursors
        
        else:
            self.adoptLandmarks(source, "scene", landmark_type, clear)
            self.adoptLandmarks(source, "scans", landmark_type, clear)
            
            
        if rois is not None and roistarget is not None:
            _landmarks_adopt_inner_(rois, roistarget, clear)
            
        if cursors is not None and cursorstarget is not None:
            _landmarks_adopt_inner_(cursors, cursorstarget, clear)

        
    @safeWrapper
    def adoptSceneCursors(self, source, clear=False):
        """Adopts scene cursors from "source" ScanData object.
        
        Does nothing if source has no scene cursors defined.
        
        """
        import gui.pictgui as pgui
        from functools import partial as partial
        
        if not isinstance(source, ScanData):
            raise TypeError("Expecting a ScanData object; got %s instead" % type(source).__name__)
        
        new_objects = dict()
        
        if len(source.sceneCursors):
            # regardings linked graphics objects, 
            # use the same strategy as for self.copy()
            for c in source.sceneCursors.values():
                if c.name in self.sceneCursors.keys():
                    self.removeCursor(c.name, scans=False)
                
                c1 = c.copy()
                c1.frameIndices=[None]
                
                if len(self.scene):
                    if c1.type == pgui.GraphicsObjectType.vertical_cursor:
                        if c1.height != self.scene[0].shape[1]:
                            c1.height = self.scene[0].shape[1]
                        
                    elif c1.type == pgui.GraphicsObjectType.horizontal_cursor:
                        if c1.width != self.scene[0].shape[0]:
                            c1.width = self.scene[0].shape[0]
                        
                    elif c1.type == pgui.GraphicsObjectType.crosshair_cursor:
                        if c1.width != self.scene[0].shape[0]:
                            c1.width = self.scene[0].shape[0]
                            
                        if c1.height != self.scene[0].shape[1]:
                            c1.height = self.scene[0].shape[1]
                            
                
                if isinstance(self.scanRegion, PlanarGraphics):
                    links = [l for l in c.objectLinks.items()]

                    for cc, l in links:
                        # see NOTE: 2018-07-02 08:36:58
                        cc1 = cc.copy()
                        cc1.frameIndices=[None]
                        
                        if cc in source._scansrois_.values():
                            self._scansrois_[cc1.name] = cc1
                            
                        elif cc in source._scenerois_.values():
                            self._scenerois_[cc1.name] = cc1
                            
                        elif cc in source._scanscursors_.values():
                            self._scanscursors_[cc1.name] = cc1
                            
                        elif cc in source._scenecursors_.values():
                            self._scenecursors_[cc1.name] = cc1
                            
                        # NOTE 2018-03-03 10:29:09:
                        # the arguments for the partial (first element in l tuple)
                        # must be changed to contain the COPIED objects  !!!
                        pf = l[0]
                        
                        c1.linkToObject(cc1, pf.func, self.scanRegion)
                        
                new_objects[c1.name] = c1
                
            self.sceneCursors.clear()
            self.sceneCursors.update(new_objects)
            
            
    @safeWrapper
    def adoptScansRois(self, source):
        """Adopts scan rois from "source" ScanData object.
        
        Does nothing if source has no scans rois defined.
        
        """
        import gui.pictgui as pgui
        from functools import partial as partial
        
        if not isinstance(source, ScanData):
            raise TypeError("Expecting a ScanData object; got %s instead" % type(source).__name__)
        
        new_objects = dict()
        
        if len(source.scansRois):
            # regardings linked graphics objects, 
            # use the same strategy as for self.copy()
            for c in source.scansRois.values():
                if c.name in self.scansRois.keys():
                    self.removeRoi(c.name, scans=True)
                
                c1 = c.copy()
                
                if isinstance(self.scanRegion, PlanarGraphics):
                    links = [l for l in c.objectLinks.items()]
                    #for cc, link in c.objectLinks.items():
                    for cc, link in links:
                        # see NOTE: 2018-07-02 08:36:58
                        # cc is the cursor linked TO
                        # link is a tuple of 3 elements as follows: 
                        #
                        # 1) partial_func:
                        # this is a partial function on the :
                        #   mapping function
                        #   the planar graphics mapped FROM (e.g. the scans cursor)
                        #   the planar graphics mapped TO (e.g. the scene cursor)
                        #
                        # 2) planar graphics object that constraints the mapping
                        #   e.g. the scan region / scan line trajectory (pgui.Path) etc
                        #
                        # 3) a dict with further keyword arguments (may be empty)
                        cc1 = cc.copy()
                        
                        if cc in source._scansrois_.values():
                            self._scansrois_[cc1.name] = cc1
                            
                        elif cc in source._scenerois_.values():
                            self._scenerois_[cc1.name] = cc1
                            
                        elif cc in source._scanscursors_.values():
                            self._scanscursors_[cc1.name] = cc1
                            
                        elif cc in source._scenecursors_.values():
                            self._scenecursors_[cc1.name] = cc1
                            
                            
                        # NOTE 2018-03-03 10:29:09:
                        # the arguments for the partial (first element in l tuple)
                        # must be changed to contain the COPIED objects  !!!
                        pf = link[0]
                        
                        c1.linkToObject(cc1, pf.func, self.scanRegion)
                    
                new_objects[c1.name] = c1
                
            self.scansRois.clear()
            self.scansRois.update(new_objects)
            
    @safeWrapper
    def adoptSceneRois(self, source):
        """Adopts scene rois from "source" ScanData object.
        
        Overwrites existing ROIs with same name.
        
        Does nothing if source has no scene rois defined.
        
        """
        import gui.pictgui as pgui
        from functools import partial as partial
        
        if not isinstance(source, ScanData):
            raise TypeError("Expecting a ScanData object; got %s instead" % type(source).__name__)
        
        new_objects = dict()
        
        if len(source.sceneRois):
            # regardings linked graphics objects, 
            # use the same strategy as for self.copy()
            for c in source.sceneRois.values():
                if c.name in self.sceneRois.keys():
                    self.removeRoi(c.name, scans=False)
                
                c1 = c.copy()
                
                if isinstance(self.scanRegion, PlanarGraphics):
                    links = [l for l in c.objectLinks.items()]
                    #for cc, link in c.objectLinks.items():
                    for cc, link in links:
                        # see NOTE: 2018-07-02 08:36:58 
                        cc1 = cc.copy()
                        
                        if cc in source._scansrois_.values():
                            self._scansrois_[cc1.name] = cc1
                            
                        elif cc in source._scenerois_.values():
                            self._scenerois_[cc1.name] = cc1
                            
                        elif cc in source._scanscursors_.values():
                            self._scanscursors_[cc1.name] = cc1
                            
                        elif cc in source._scenecursors_.values():
                            self._scenecursors_[cc1.name] = cc1
                            
                        # NOTE 2018-03-03 10:29:09:
                        # the arguments for the partial (first element in l tuple)
                        # must be changed to contain the COPIED objects  !!!
                        pf = link[0]

                        c1.linkToObject(cc1, pf.func, self.scanRegion)
                    
                new_objects[c1.name] = c1
                
            self.sceneRois.clear()
            self.sceneRois.update(new_objects)
            
    @safeWrapper
    def adoptGraphicsObjects(self, source):
        """Adopts _ALL_ graphics objects (cursors, rois) defined in source.
        
        CAUTION: Overwrites existing objects, including the scanline ROI!!!
        
        """
        import gui.pictgui as pgui
        from functools import partial as partial
        
        if not isinstance(source, ScanData):
            raise TypeError("Expecting a ScanData object; got %s instead" % type(source).__name__)
        
        skip_objects = list()
        
        for d, target in zip((source._scenerois_, source._scansrois_, source._scenecursors_, source._scanscursors_),
                             (self._scenerois_, self._scansrois_, self._scenecursors_, self._scanscursors_)):

            new_objects = dict()
            
            if len(d):
                for k, i in d.items():
                    obj = i.copy()
                    
                    if isinstance(self.scanRegion, PlanarGraphics):
                        links = [l for l in i.objectLinks.items()]
                        #for c, link in i.objectLinks.items():
                        for c, link in links:
                            # see NOTE: 2018-07-02 08:36:58 
                            cc = c.copy()
                            # technically this should not be linked to itself
                            if c in source._scansrois_.values():
                                self._scansrois_[cc.name] = cc
                                
                            elif c in source._scenerois_.values():
                                self._scenerois_[cc.name] = cc
                                
                            elif c in source._scanscursors_.values():
                                self._scanscursors_[cc.name] = cc
                                
                            elif c in source._scenecursors_.values():
                                self._scenecursors_[cc.name] = cc
                                
                            skip_objects.append(cc)
                                
                            pf = link[0]

                            #ll = [l_ for l_ in link]
                            #new_pf = partial(pf.func, obj, cc)
                            #ll[0] = new_pf
                            #ll[1] = self.scanRegion
                            #obj.linkedObjects[cc] = tuple(ll)
                            
                            obj.linkToObject(cc, pf.func, self.scanRegion)
                            
                    if obj not in skip_objects:
                        new_objects[k] = obj
                    
                target.clear()
                target.update(new_objects)

    @safeWrapper
    def adoptTriggerProtocols(self, src, imaging_source=False):
        """Parses trigger and adopts trigger protocols from the neo.Block object "src".

        Named parameters:
        =================
        
        src: a ScanData, a neo.Block, a neo.Segment, or a sequence of neo.Segments.
        
            WARNING this should not be the same as this ScanData or any of its
            data blocks (electrophysiology, scans, or scene). This is checked
            against, but only by referecne (i.e. if src is a reference to 
            self, self.electrophysiology, etc). The code does not verify if
            "src" is a deep data copy of any part or whole of this ScanData.
        
        imaging_source: boolean (default False) - sets the sign of the imaging delay
            Used only when src is a neo.Block.
        
            When src is a neo.Block, this may contain electrophysiology data, or
            imaging data (e.g. 1D signals derived from 2D imaging data, etc).
            
            When imaging_source is True src is interpreted as a block containing
            imaging signals (e.g. a scansBlock); otherwise, src is interpreted as
            containing electrophysiology signals.
            
            This distinction arises from the fact that in most cases there is a
            non-zero delay between the start of imaging data acquisition and that
            of electrophysiology data. 
            
            Therefore, any trigger event occuring during the experiment will have
            different times in electrophysiology and the imaging data, with the 
            difference being  stored in the "imagingDelay" attribute of the protocol. When an
            event is copied from one type of data to another this delay must be
            be compensated.
            
            CAUTION: This matters because the actual event times for electrophysiology
                and imaging signals blocks need to be adjusted according to
                the delay between electrophysiology and imaging acquisition times.
                
            In this case protocols are "parsed" and costructed based on the 
            TriggerEvent objects found in src.
                
            If src is a ScanData object: the protocols in the ScanData object
            list will be COPIED over to self.
            
        WARNING: Overwrites self._trigger_protocols_ !!!
        
        CAUTION: Does nothing if the neo.Block src object has no trigger protocols
        
        """
        # NOTE: 2017-12-20 21:35:55
        # trigger events need to be adjusted for imagingDelay before being 
        # embedded into the _scans_block_ segments
        
        if isinstance(src, ScanData):
            # adopts trigger protocols contained in ScanData 'src'
            if src is self:
                return
            
            pp = [p.copy() for p in src.triggerProtocols]
            
            self._trigger_protocols_[:] = pp
            
            self._trigger_protocols_.sort(key=lambda x:x.segmentIndices()[0])
            
            # NOTE: 2019-03-16 21:56:11
            # in electrophysiology block, protocol events are stored by reference
            # in imaging block we store COPIES of protocol events with reversed acquisition!
            for p in self._trigger_protocols_:
                #print("ScanData.adoptTriggerProtocols:", p.name)
                rev_p = p.reverseAcquisition(copy=True)
                
                if not is_empty(self._electrophysiology_):
                    embed_trigger_protocol(p, 
                                            self._electrophysiology_,
                                            clearTriggers=True)
                    
                if not is_empty(self._scans_block_):
                    embed_trigger_protocol(rev_p, 
                                            self._scans_block_,
                                            clearTriggers=True)
                    
                if not is_empty(self._scene_block_):
                    embed_trigger_protocol(rev_p, 
                                            self._scene_block_,
                                            clearTriggers=True)
                
        else:
            if isinstance(src, neo.Block):
                # NOTE 2020-12-30 17:29:40: 
                # do nothing if the 'srouce' if the same as the detination
                if src in (self._electrophysiology_, self._scans_block_, self._scene_block_):
                    # do not run if the source is in this data
                    return
                
            # from here on, 'src' is neither of this data's own blocks (electrophysiology,
            # scans or scene blocks)
            
            # create a list of protocols based on the trigger events embedded in src
            src_protocols, _ = parse_trigger_protocols(src) 
                
            self._trigger_protocols_.clear()
            
            if len(src_protocols):
                for protocol in src_protocols:
                    # NOTE: 2019-03-16 21:56:11
                    # the electrophysiology block stores trigger events by reference
                    # the imaging block stores COPIES of trigger events where
                    # the timings for the imaging event have ben 'reversed'
                    # (i.e., if imaging event was delayed in electrophysiology,
                    # it is set to be at time 0 in the imaging)
                    
                    reversedProtocol = protocol.reverseAcquisition(copy=True)
                    
                    if imaging_source: # adopting protocol from a scans or scene block
                        # store ref to reversed acquisition of original
                        if not is_empty(self._electrophysiology_):
                            embed_trigger_protocol(reversedProtocol,
                                                            self._electrophysiology_,
                                                            clearTriggers=True)
                        
                        # store copy of original
                        if not is_empty(self._scans_block_):
                            embed_trigger_protocol(protocol,
                                                    self._scans_block_,
                                                    clearTriggers=True)
                            
                        if not is_empty(self._scene_block_):
                            embed_trigger_protocol(protocol,
                                                    self._scene_block_,
                                                    clearTriggers=True)
                        
                        self._trigger_protocols_.append(reversedProtocol)
                        
                    else: # adopting protocol from an ephys block
                        # store ref to original
                        if not is_empty(self._electrophysiology_):
                            embed_trigger_protocol(protocol,
                                                    self._electrophysiology_,
                                                    clearTriggers=True)
                        
                        # store ref to reverse acquisition copy of original
                        if not is_empty(self._scans_block_):
                            embed_trigger_protocol(reversedProtocol,
                                                    self._scans_block_,
                                                    clearTriggers=True)
                    
                        # store ref to reverse acquisition copy of original
                        if not is_empty(self._scene_block_):
                            embed_trigger_protocol(reversedProtocol,
                                                    self._scene_block_,
                                                    clearTriggers=True)
                        
                
                        self._trigger_protocols_.append(protocol)
                    
            if len(self._trigger_protocols_):
                self._trigger_protocols_.sort(key=lambda x:x.segmentIndices()[0])
            
    @safeWrapper
    def clearTriggerProtocols(self):
        self._trigger_protocols_.clear()
        
        clear_events(self._electrophysiology_,   triggersOnly = True)
        clear_events(self._scans_block_,         triggersOnly = True)
        clear_events(self._scene_block_,         triggersOnly = True)
        
    @safeWrapper
    def addTriggerProtocol(self, protocol, sort=False):
        """Adds a trigger protocol.
        
        Parameters:
        ============
        Event times are considered to be in the electrophysiology time domain.
        (i.e. relative to the ephys sweep origin).
        
        Keyword parameters:
        ==================
        sort: boolean, default False
        
            When True, the lost of protocols is listed in ascending order of the 
            first segment index of the protocol
            
            This is set to False by default to prevent expensive code from being
            executed when the function is called in an iteration.
            
            Set it manually to True for isolated calls to this function
        
        """
        ##### BEGIN debugging
        #frame = inspect.currentframe()
        #if frame is not None:
            #frames = inspect.getouterframes(frame)
            #print("ScanData.addTriggerProtocol: frames: ")
            #for f in frames:
                #print(f"\t{f.function} at line {f.lineno} in {f.filename}")
        ##### END debugging
        
        if not isinstance(protocol, TriggerProtocol):
            raise TypeError("Expecting a trigger protocol; got %s instead" % type(protocol).__name__)
        
        # set it by default to all scans frames
        if protocol.nsegments == 0:
            protocol.segmentIndex = range(self.scansFrames)
            
        elif any([f < 0 or f >= self.scansFrames for f in protocol.segmentIndices()]):
            raise ValueError("Protocol %s has segment indices (%s) that are invalid for the current data (%s) with %d scans frames" % \
                (protocol.name, str(protocol.segmentIndices()), self.name, self.scansFrames))
        
        # see NOTE: 2019-03-16 21:56:11
        # in electrophysiology block, protocol events are stored by reference
        # in imaging block we store COPIES of protocol events with reversed acquisition!
        rev_p = protocol.reverseAcquisition(copy=True)
        
        if not is_empty(self._electrophysiology_):
            embed_trigger_protocol(protocol,
                                    self._electrophysiology_,
                                    clearEvents=False)
        
        if not is_empty(self._scans_block_):
            embed_trigger_protocol(rev_p,
                                    self._scans_block_,
                                    clearEvents=False)
        
        if not is_empty(self._scene_block_):
            embed_trigger_protocol(rev_p,
                                    self._scene_block_,
                                    clearEvents=False)
        
        self._trigger_protocols_.append(protocol)
        
        if sort:
            self._trigger_protocols_.sort(key=lambda x: x.segmentIndices()[0])
        
        if protocol not in self._analysis_unit_.protocols:
            self._analysis_unit_.protocols.append(protocol)
            self._analysis_unit_.protocols.sort(key=lambda x: x.segmentIndices()[0])
            
        for u in self.analysisUnits:
            if protocol not in u.protocols:
                u.protocols.append(protocol)
                u.protocols.sort(key=lambda x: x.segmentIndices()[0])
        
    def removeTriggerProtocol(self, protocol):
        if isinstance(protocol, TriggerProtocol):
            if protocol not in self._trigger_protocols_:
                raise ValueError("protocol %s not found in %s" % (protocol.name, self.name))
            
            protocolNdx = self._trigger_protocols_.index(protocol)
            
        elif isinstance(protocol, str):
            if protocol in [p.name for p in self._trigger_protocols_]:
                protocol = [p for p in self._trigger_protocols_ if p.name == protocol][0]
                
                protocolNdx = self._trigger_protocols_.index(protocol)
                
            else:
                raise ValueError("protocol named %s not found in %s" % (protocol, self.name))
            
        elif isinstance(protocol, int):
            if protocol not in range(len(self._trigger_protocols_)):
                raise ValueError("protocol index %d is invalid for %d protocols in %s" % (protocol, len(self._trigger_protocols_), self.name))
            
            protocolNdx = protocol
            
            protocol = self._trigger_protocols_[protocolNdx]
            
        else:
            raise TypeError("Expecting a trigger protocol, a str (protocol name) or int (protocol index); got %s instead" % type(protocol).__name__)
        
        rev_p = protocol.reverseAcquisition(copy=True)
        
        remove_trigger_protocol(protocol, self._electrophysiology_)
        remove_trigger_protocol(rev_p, self._scans_block_)
        remove_trigger_protocol(rev_p, self._scene_block_)
        
        del self._trigger_protocols_[protocolNdx]
        
        if protocol in self._analysis_unit_.protocols:
            ndx = self._analysis_unit_.protocols.index(protocol)
            del self._analysis_unit_.protocols[ndx]
            
        for u in self.analysisUnits:
            ndx = u.protocols.index(protocol)
            del u.protocols[ndx]
        
    def protocol(self, index):
        """Alias to self.triggerProtocol(index)
        """
        return self.triggerProtocol(index)
    
    @safeWrapper
    def triggerProtocol(self, nameOrSegmentIndex):
        """Accesses a trigger protocol in this ScanData, specified by name or frame.
        
        Parameters:
        ==========
        
        nameOrSegmentIndex: a str (protocol name) or an int (frame index) which must be found
            in the segmentIndices attrbute of the exising protocols
            
            NOTE  when an int this is NOT the index of the protocol in 
            triggerProtocols list!
        
        Returns:
        ========
        
        When nameOrSegmentIndex is a str: a trigger protocol with the name specified by "nameOrSegmentIndex"
        
            Raises an Exception if no such protocol exists.
            
        When nameOrSegmentIndex is an int: a trigger protocol associated attached to the
            scans frame with the given nameOrSegmentIndex.
            
            Returns None if the specified frame index does not associate a protocol.
            
            Raises an Exception if frame index is outside the semi-open interval [0, self.scansFrames)
            or if the frame index associated more than one protocols.
            
        Returns None if there are not trigger protocols defined.
        
        """
        
        if len(self.triggerProtocols) == 0:
            return None
        
        if isinstance(nameOrSegmentIndex, str):
            if nameOrSegmentIndex in [p.name for p in self._trigger_protocols_]:
                
                protocols = [p for p in self._trigger_protocols_ if p.name == nameOrSegmentIndex]
                
                if len(protocols) > 1:
                    raise RuntimeError("There appears to be %d protocols named '%s' in %s" % (len(protocols), nameOrSegmentIndex, self.name))
                
                return protocols[0]
            
            else:
                raise ValueError("data does not contain a protocol named %s" % nameOrSegmentIndex)
            
        elif isinstance(nameOrSegmentIndex, int):
            if nameOrSegmentIndex < 0 or nameOrSegmentIndex >= self.scansFrames:
                raise ValueError("Invalid frame nameOrSegmentIndex %d); expected to be a value on the semi-open interval [0, %d) in %s" % (nameOrSegmentIndex, self.scansFrames, self.name))
        
            protocols = [p for p in self.triggerProtocols if nameOrSegmentIndex in p.segmentIndices()]
            
            if len(protocols) > 1:
                raise RuntimeError("Frame %d appears to associate %d protocols in %s" % (nameOrSegmentIndex, len(protocols), self.name))
            
            if len(protocols) == 0:
                return None
            
            return protocols[0]
            
        else:
            raise TypeError("expecting a string or an int; got %s instead" % type(nameOrSegmentIndex).__name__)
        
    #@safeWrapper
    def getNamedTriggerProtocols(self, names):
        if isinstance(names, (tuple, list)) and all([isinstance(n, str) for n in names]):
            pr_names = [p.name for p in self._trigger_protocols_]
            
            if any([n not in pr_names for n in names]):
                raise ValueError("some or all specified names are not found in data's protocol list")
            
            pr_list = list()
            for n in names:
                pr_list.append([p for p in self._trigger_protocols_ if p.name == n][0])
                
            return pr_list
        
        elif isinstance(names, str):
            names = [names]
        
        else:
            raise TypeError("A str or a sequence of str was expected")
        
    @safeWrapper
    def addLandmark(self, obj, scans=True):
        """Adds a landmark (pictgui.PlanarGraphics object: cursor or ROI) to the image data.
        
        To generate an AnalysisUnit object, call self.defineAnalysisUnit(...)
        AFTER the landmark has been added.
        
        If the PlanarGraphics is linked to other objects, these will also be added
        to self.
        
        See pictgui.PlanarGraphics for details.
        
        """
        import gui.pictgui as pgui
        
        if not isinstance(obj.PlanarGraphics):
            raise TypeError("expecting a pictgui.PlanarGraphics object; got %s instead" % type(obj).__name__)
        
        if isinstance(obj, pgui.Cursor):
            self.addCursor(obj, scans)
            
        else:
            self.addRoi(obj, scans)
            
        if len(obj.linkedObjects):
            for o in obj.linkedObjects:
                self.addLandmark(o)
                
    @safeWrapper
    def renameAnalysisUnit(self, value, analysis_unit=None):
        """Rename the analysis unit to the string in 'value'
        
        Parameters:
        ===========
        
        value: a string; if empty, it will be replaced with "NA"
        
        analysis_unit: optional, can be: None (default), AnalysisUnit, or str
        
            1) When None, the function renames the data-wide analysis unit.
            
            2) When an AnalysisUnit object, the name of this unit will be replaced 
                IF the object is nested in this data. The landmarks will also be
                renamed
                
            3) When a str, the nested landmark-based AnalysisUnit will be renamed
                as above.
                
            In cases 2 and 3 above, an error will be raised if
                a) value is a string already used by another analysis unit
                b) the specified analysis unit is not nestd in this data
                
            Clause (a) implies one cannot have more than one unnamed nested
            analysis units (i.e., with name attribute beign "NA")
            
        Returns:
        =======
        
        The renamed AnalysisUnit.
        
        """
        if not isinstance(value, str):
            raise TypeError("Expecting a str value; got %s instead" % type(value).__name__)
        
        if len(value.strip()) == 0:
            warnings.warn("An empty string was passed; it will be changed to 'NA'", RuntimeWarning)
            value="NA"
            
        if analysis_unit is None:
            # renaming the data-wide analysis unit
            self._analysis_unit_.name = value
            return self._analysis_unit_
            
        elif isinstance(analysis_unit, AnalysisUnit):
            if analysis_unit not in self._analysis_units_:
                raise KeyError("Analysis unit %s not found in this data %s" % analysis_unit.name)
            
            if value in [u.name for u in self.analysisUnits]:
                raise ValueError("The name '%s' is already in use by another nested analysis unit" % value)
            
            u_name = analysis_unit.name
            
        elif isinstance(analysis_unit, str):
            units = self.analysisUnits
            
            unit_names = [u.name for u in units]
            
            u_name = analysis_unit
            
            if u_name not in unit_names:
                raise KeyError("Analysis unit %s not found in this data %s" % (analysis_unit, self.name))
            
            if value in unit_names:
                raise ValueError("The name '%s' is already in use by another nested analysis unit" % value)
            
            analysis_unit = units[unit_names.index(u_name)]
            
        else:
            raise TypeError("analysis_unit expected to be a str (old name), an Analysis Unit, or None; got %s instead" % type(analysis_unit).__name__)
        
        #print("ScanData.renameAnalysisUnit: old name %s -> new name %s" % (u_name, value))
        
        for ks, segment in enumerate(self.scansBlock.segments):
            sig_names = [s.name for s in segment.analogsignals]
            irreg_sig_names = [s.name for s in segment.irregularlysampledsignals]
            
            if value in sig_names:
                raise ValueError("A signal named '%s' already exists in scansBlock segment %d" % (value, ks))
            
            if value in irreg_sig_names:
                raise ValueError("A signal named '%s' already exists in scansBlock segment %d" % (value, ks))
            
            sig_ndx = get_index_of_named_signal(segment, u_name, silent=True)
            
            #print("ScanData.renameAnalysisUnit: sig_ndx %d in segment %d" % (sig_ndx, ks))
            
            if sig_ndx is not None:
                segment.analogsignals[sig_ndx].name = value
            
            irreg_sig_ndx = get_index_of_named_signal(segment, u_name, stype=neo.IrregularlySampledSignal, silent=True)
            
            if irreg_sig_ndx is not None:
                segment.irregularlysampledsignals[irreg_sig_ndx].name = value
                
        for ks, segment in enumerate(self.sceneBlock.segments):
            sig_names = [s.name for s in segment.analogsignals]
            irreg_sig_names = [s.name for s in segment.irregularlysampledsignals]
            
            if value in sig_names:
                raise ValueError("A signal named '%s' already exists in scansBlock segment %d" % (value, ks))
            
            if value in irreg_sig_names:
                raise ValueError("A signal named '%s' already exists in scansBlock segment %d" % (value, ks))
            
            sig_ndx = get_index_of_named_signal(segment, analysis_unit.name, silent=True)
            
            if sig_ndx is not None:
                segment.analogsignals[sig_ndx].name = value
            
            irreg_sig_ndx = get_index_of_named_signal(segment, analysis_unit.name, stype=neo.IrregularlySampledSignal, silent=True)
            
            if irreg_sig_ndx is not None:
                segment.irregularlysampledsignals[irreg_sig_ndx].name = value
                
        analysis_unit.name = value
        
        #print("renameAnalysisUnit unit name %s,landmark name %s" % (analysis_unit.name, analysis_unit.landmark.name))
        
        if analysis_unit.name != analysis_unit.landmark.name:
            self.renameLandmark(analysis_unit.landmark, value)
            
        return analysis_unit
        
    @safeWrapper
    def renameLandmark(self, landmark, name):
        """Changes the name of the landmark.
        If the landmark is used for an analysis unit, and its name differs from
        the new name of the landmark, the unit is also renamed
        
        Parameters:
        ==========
        landmark: a pictgui.PlanarGraphics object
        
        name: str - must neither be empty, nor contain only blanks!
        
        Returns:
        =======
        
        Landmark-based AnalysisUnit if the renamed landmark is associated with
        one, or:
        
        the renamed PlanarGraphics landmark, if found, or:
        
        None.
        
        """
        import gui.pictgui as pgui

        if not isinstance(landmark, PlanarGraphics):
            raise TypeError("landmark expected to be a pictgui.PlanarGraphics; got %s instead" % type(landmark).__name__)
        
        if not isinstance(name, str):
            raise TypeError("name expected to be a string' got %s instead" % type(name).__name__)
        
        if len(name.strip()) == 0:
            raise ValueError("name is empty or contains only blank characters")
        
        #print("ScanData.renameLandmark old name %s -> new name %s" % (landmark.name, name))
        
        if landmark in self._scanscursors_.values():
            landmarkdict = self._scanscursors_
            
        elif landmark in self._scenecursors_.values():
            landmarkdict = self._scenecursors_
            
        elif landmark in self._scenerois_.values():
            landmarkdict = self._scenerois_
            
        elif landmark in self._scansrois_.values():
            landmarkdict  = self._scansrois_
            
        else:
            raise ValueError("Landmark named %s not found in this ScanData object" % landmark.name)
        
        old_name = landmark.name
        
        #print("renameLandmark old_name %s -> new name %s" % (old_name, name))
        
        landmark.name = name # also updates its frontends & linked objects
            
        # update the dictionaries
        lnd = landmarkdict.pop(old_name, None)
        landmarkdict[name] = landmark
        
        if len(self.analysisUnits):
            units = [u for u in self.analysisUnits if u.landmark == landmark]
            
            if len(units):
                if units[0].name != landmark.name:
                    return self.renameAnalysisUnit(landmark.name, units[0])
                
        else:
            return landmark
        

    @safeWrapper
    def removeLandmark(self, landmark, scans=True, cursor=True):
        """Removes a landmark
        
        If the landmark is associated with an analysis unit, it also removes 
        that analysis unit (together with the data derived from it)
        
        Parameters:
        ==========
        landmark: str (landmark name) or PlanarGraphics
            When a str it must neither be empty nor contain only blank characters
        
        Keyword parameters: -- only used when landmark is a str
        ==================
        scans: boolean (default True); When true, removes scans landmark elese removes scene landmark
        
        cursor: boolean (default True); Wwhen True removes a cursor else removes a ROI
            
        Returns:
        =======
        The removed landmark, if found, or None
        
        """
        import gui.pictgui as pgui

        if isinstance(landmark, str):
            if len(landmark.strip()) == 0:
                return
            
            if landmark not in [l.name for l in self.landmarks]:
                return
            
            lds = []
            
            if scene:
                if cursor:
                    lds = [l for l in self.sceneCursors.values() if l.name == landmark]
                    
                else:
                    lds = [l for l in self.sceneRois.values() if l.name == landmark]
                    
            else:
                if cursor:
                    lds = [l for l in self.scansCursors.values() if l.name == landmark]
                    
                else:
                    lds = [l for l in self.scansRois.values() if l.name == landmark]
                    
            if len(lds) == 0:
                return
            
            landmark = lds[0]
            
        elif not isinstance(landmark, PlanarGraphics):
            #warnings.warn("Expecting a pictgui.PlanarGraphics object or a str; got %s instead" % type(landmark).__name__)
            return
        
        #print("ScanData.removeLandmark: %s, %s " % (landmark.type, landmark.name))
        
        # first get rid of links
        #linked_objects = [obj for obj in landmark.objectLinks.keys()]
        
        for obj in landmark.linkedObjects:
            #print("ScanData.removeLandmark: removing linked object %s" % obj.name)
            landmark.objectLinks.pop(obj, None)
            
            if obj != landmark: # skip if object is "linked" to itself (although this should never happen)
                #print("ScanData.removeLandmark: found linked object %s, %s" % (obj.type, obj.name))
                if isinstance(obj, pgui.Cursor):
                    if obj in self.sceneCursors.values():
                        self.removeCursor(obj, scans=False)
                        
                    if obj in self.scansCursors.values():
                        self.removeCursor(obj, scans=True)
                        
                else:
                    if obj in self.sceneRois.values():
                        self.removeRoi(obj, scans=False)
                        
                    if obj in self.scansRois.values():
                        self.removeRoi(obj, scans=True)
                    
        #print("ScanData.removeLandmark: removing landmark itself %s" % obj.name)
        # then get rid of the landmark
        if isinstance(landmark, pgui.Cursor):
            if landmark in self.sceneCursors.values():
                self.removeCursor(landmark, scans=False)
                
            if landmark in self.scansCursors.values():
                self.removeCursor(landmark, scans=True)
                
        else:
            if landmark in self.sceneRois.values():
                self.removeRoi(landmark, scans=False)
                
            if landmark in self.scansRois.values():
                self.removeRoi(landmark, scans=True)
                
        if len(self._analysis_units_):
            units = [u for u in self._analysis_units_ if u.landmark is landmark]
            
            if len(units):
                #print("ScanData.removeLandmark: removing landmark analysis unit itself %s" % units[0].name)
                self.removeAnalysisUnit(units[0])
        
        return landmark
        
    @safeWrapper
    def addCursor(self, cursor, scans=True):
        """Appends a cursor to the specified frame of the specified data subset.
        
        To remove a cursor use removeCursor(...); to modify a cursor, use setCursor(...)
        
        Parameters:
        ===========
        
        cursor  = pictgui.Cursor object
        
        Keyword parameters:
        ===================
        scans   = boolean:
                            True (default) chooses the scans data subset
                            False chooses scene subset

        sceneCursors and scansCursors are dictionaries with int keys (frame number)
            mapped to a mapping of cursor ID (or name, a str) to a pictgui.Cursor
            object
        
        e.g.:
        
        {0: {"cursor01": <pictgui.Cursor object at xxxx>}}
        
        NOTE: the name of the displayed cursor in the image is formed by appending
        the frame number to the cursor name in this dictionary:
        
        "cursor01_0" will appear as label (unless, of course, specified otherwise
        in ImageViewer.addCursor() method)
        
        """
        self.setCursor(cursor, scans, True)
        
    @safeWrapper
    def addRoi(self, obj, scans=True):
        self.setRoi(obj, scans, True)
        
    @safeWrapper
    def getCursor(self, name, scans=True):
        """Returns a reference to a cursor, or None.
        
        A cursor is a pictgui.Cursor that is displayed in an image window through
        a linked GraphicsObject (an entity distinct from pictgui.Cursor;
        see pictgui.GraphicsObject for details)
        
        If cursor is not found, prints an error message to stderr and returns None.
        
        Parameters:
        ==========
        
        name    = str: cursor name (ID) present in the dictionary
        
        scans   = boolean: 
                            True (default) seeks cursor in the scans data subset
                            False seeks cursor in the scene data subset
        
        """
        if scans:
            cursordict = self._scanscursors_
        
        else:
            cursordict = self._scenecursors_
            
        try:   
            return cursordict[name]
        
        except:
            traceback.print_exc()
            
    @safeWrapper
    def sceneCursor(self, name):
        if name in self.sceneCursors.keys():
            return self.sceneCursors[name]
        
    @safeWrapper
    def sceneRoi(self, name):
        if name in self.sceneRois.keys():
            return self.sceneRois[name]
        
    @safeWrapper
    def scansCursor(self, name):
        if name in self.scansCursors.keys():
            return self.scansCursors[name]
        
    @safeWrapper
    def scanCursor(self, name):
        """Same as scansCursor
        """
        if name in self.scanCursors.keys():
            return self.scanCursors[name]
        
    @safeWrapper
    def scansRoi(self, name):
        if name in self.scansRois.keys():
            return self.scansRois[name]
        
    @safeWrapper
    def scanRoi(self, name):
        """Same as scansRoi
        """
        if name in self.scanRois.keys():
            return self.scanRois[name]
        
    @safeWrapper
    def setCursor(self, cursor, scans=True, append=False):
        """Sets or appends a cursor to the specified frame in a specified data subset.
        
        To remove a cursor use removeCursor()
        
        Parameters:
        ===========
        
        cursor  = pictgui.Cursor object
        
        Keyword parameters:
        ===================
        scans   = boolean:
                            True (default) chooses the scans data subset
                            False chooses scene subset
                    
        append  = boolean:
                    
                            False (default): 
                                if cursor.name exists in the dictionary keys it 
                                    will be replaced with THIS cursor
                                    
                                if cursor.name does NOT exist in the dictionary 
                                    keys, it will replace the ENTIRE contents of
                                    the dictionary with THIS cursor
                                    
                            True:
                                if cursor.name exists in the dictionary keys, its
                                    ID will be adjusted then it will be appended
                                    to the dictionary contents
                                    
                                if cursor.name does NOT exist it will simply be 
                                    appended to the  dictionary contents
        
        sceneCursors and scansCursors are dictionaries with int keys (frame number)
            mapped to a mapping of cursor ID (or name, a str) to a pictgui.Cursor
            object
        
        e.g.:
        
        {0: {"cursor01": <pictgui.Cursor object at xxxx>}}
        
        NOTE: the name of the displayed cursor in the image is formed by appending
        the frame number to the cursor name in this dictionary:
        
        "cursor01_0" will appear as label (unless, of course, specified otherwise
        in ImageViewer.addCursor() method)
        
        """
        import gui.pictgui as pgui

        if not isinstance(cursor, pgui.Cursor):
            raise TypeError("Expecting a pictgui.Cursor; got %s instead" % type(cursor).__name__)
        
        if scans:
            cursordict = self.scansCursors
            
        else:
            cursordict = self.sceneCursors
        
        if append:
            if cursor.name in cursordict.keys():
                cursor.name = counter_suffix(cursor.name, list(cursordict.keys()))
                
            if cursor in cursordict.values():
                cursor = cursor.copy()
            
        cursordict[cursor.name] = cursor
            
        return cursor.name
    
    @safeWrapper
    def removeChannel(self, name_or_index):
        try:
            self.removeScansChannel(name_or_index)
            
        except Exception as e:
            traceback.print_exc()
            warnings.warn("Channel name %s not found in scans" % name_or_index, RuntimeWarning)
            
        try:
            self.removeSceneChannel(name_or_index)
            
        except Exception as e:
            traceback.print_exc()
            warnings.warn("Channel name %s not found in scene" % name_or_index, RuntimeWarning)
    
    @safeWrapper
    def removeScansChannel(self, name_or_index):
        if isinstance(name_or_index, str):
            if name_or_index not in self.scansChannelNames:
                raise ValueError("Channel name %s not found in scans" % name_or_index)
            
            ch_index = self.scansChannelNames.index(name_or_index)
            
        elif isinstance(name_or_index, int):
            if name_or_index < 0 or name_or_index >= len(self.scansChannels):
                raise ValueError("Channel index must have value in the half-open interval [0, %d)" % self.scansChannels)
            
            ch_index = name_or_index
            
        del self._scans_[ch_index]
        self._scans_axes_calibrations_[:] = [AxesCalibration(img) for img in self._scans_]
            
    @safeWrapper
    def removeSceneChannel(self, name_or_index):
        if isinstance(name_or_index, str):
            if name_or_index not in self.sceneChannelNames:
                raise ValueError("Channel name %s not found in scans" % name_or_index)
            
            ch_index = self.sceneChannelNames.index(name_or_index)
            
        elif isinstance(name_or_index, int):
            if name_or_index < 0 or name_or_index >= len(self.sceneChannels):
                raise ValueError("Channel index must have value in the half-open interval [0, %d)" % self.sceneChannels)
            
            ch_index = name_or_index
            
        del self._scene_[ch_index]
        self._scene_axes_calibrations_[:] = [AxesCalibration(img) for img in self._scene_]
        
    def trimScans(self, interval, axis):
        """Removes image data OUTSIDE the specified interval along the specified axis .
        
        Axis cannot be a channel axis!
        """
        
        if isinstance(axis, str):
            if isinstance(axis, str) and axis not in self.scans[0].axistags:
                raise KeyError("Axis with key %s not found in %s scans images with axistags %s" % (axis, self.name, [ax.key for ax in self.scans[0].axistags]))
            
            if isinstance(axis, int) and (axis < 0 or axis >= len(self.scans[0].axistags)):
                raise KeyError("Invalid axis index %s for %s scans images with %d axes" % (axis, self.name, self.scans[0].shape))
            
            if self.scans[0].axistags[axis].isChannel():
                raise ValueError("Cannot operate on channel axis %s" % axis)
            
        elif isinstance(axis, vigra.AxisInfo):
            if axis not in self.scans[0].axistags:
                raise ValueError("Axis %s not found in % scans images" % (axis.key, self.name))
            
            if axis.isChannel():
                raise ValueError("Cannot operate on channel axis %s" % axis)
        
        slice_object = self.getScansAxesCalibration(0).getCalibratedIntervalAsSlice(interval, axis)
        
        slicing = imageIndexTuple(self.scans[0], {axis: slice_object})
        
        self.scans[:] = [s[slicing] for s in self.scans]
    
    def removeFrame(self, ndx):
        """
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        def _decrement_frame_index_path_(obj, ndx):
            for o in obj:
                _decrement_frame_ndx_(o, ndx)
            
        def _decrement_frame_ndx_(obj, ndx):
            if isinstance(obj, pgui.Path):
                _decrement_frame_index_path_(obj, ndx)
                
            else:
                frndx = obj.frameIndices
                for k, i in enumerate(frndx):
                    if i > ndx:
                        frndx[k] -= 1
                        
                obj.frameIndices = frndx
            
        if not isinstance(ndx, int):
            raise TypeError("Expecting an int; got %s instead" % type(ndx).__name__)
        
        if ndx not in range(self.scansFrames):
            raise ValueError("Expecting an int between 0 and %d; got %d instead" % (self.scansFrames, ndx))
        
        try:
            new_scans = [removeSlice(img, self.scansFrameAxis, ndx) for img in self.scans]
            
            if self.sceneFrames > 1:
                new_scene = [removeSlice(img, self.sceneFrameAxis, ndx) for img in self.scene]
                

            # figure out the remaining segment indices - adjust this for the remaining protcools and landmarks

            del_protocols = list()
            
            # after this we may end up with some (or all) of the protocols removed
            for protocol in self.triggerProtocols:
                #new_protocol = protocol.copy()
                
                segs = protocol.segmentIndices()
                
                if ndx in segs:
                    del segs[segs.index(ndx)]
                    
                # decrement the segment indices to the right of ndx
                for k, index in enumerate(segs):
                    if index > ndx:
                        segs[k] -= 1# slide the higher indices by 1
                        
                protocol.segmentIndex = segs
                
                if len(protocol.segmentIndices()) == 0:
                    del_protocols.append(protocol)
                    
            # remove frame index form the scan region planar graphic object
            # FIXME  ! this is a stitch-up
            if self.scanRegion is not None:
                self.scanRegion.removeState(ndx)
                
                if isinstance(self.scanRegion, pgui.Path):
                    _decrement_frame_index_path_(self.scanRegion, ndx)
                    
                else:
                    _decrement_frame_ndx_(self.scanRegion, ndx)
                    for o in self.scanRegion:
                        frndx = o.frameIndices
                        
                        for k, i in enumerate(frndx):
                            if i > ndx:
                                frndx[k] -= 1
                
                #if not self.scanRegion.hasCommonState:
                #if len(self.scanRegion.frameIndices) == 0:
                    #self.scanRegion = None
                    
                #else:
                    ## decrement the frame indices to the right of ndx
                    #if isinstance(self.scanRegion, pgui.Path):
                        #for obj in self.scanRegion:
                            #object_frame_ndx = obj.frameIndices
                            #for k, index in enumerate(object_frame_ndx):
                                #if index > ndx:
                                    #object_frame_ndx[k] -= 1
                                    
                            #obj.remapFrameStateAssociations([m for m in zip(obj.frameIndices, object_frame_ndx)])
                            
                    #else:
                        #object_frame_ndx = [k for k in self.scanRegion.frameIndices]
                        
                        #for k, index in enumerate(object_frame_ndx):
                            #if index > ndx:
                                #object_frame_ndx[k] -= 1
                                
                        #self.scanRegion.remapFrameStateAssociations([m for m in zip(self.scanRegion.frameIndices, object_frame_ndx)])
                
            scan_cursors = [o for o in self.scansCursors.values()]
            
            for o in scan_cursors:
                o.removeState(ndx)
                
                #if not o.hasCommonState:
                if len(o.frameIndices) == 0:
                    self.scanCursors.pop(o.name, None)
                    
                else:
                    # decrement the frame indices to the right of ndx
                    object_frame_ndx = [k for k in o.frameIndices]
                    
                    for k, index in enumerate(object_frame_ndx):
                        if index > ndx:
                            object_frame_ndx[k] -= 1
                            
                    o.remapFrameStateAssociations([m for m in zip(o.frameIndices, object_frame_ndx)])
                
            scan_rois = [o for o in self.scansRois.values()]
            
            for o in scan_rois:
                o.removeState(ndx) # does nothing if there are not hard frame associations

                #if not o.hasCommonState:
                if len(o.frameIndices) == 0:
                    self.scanRois.pop(o.name, None)
                    
                else:
                    # decrement the frame indices to the right of ndx
                    object_frame_ndx = [k for k in o.frameIndices]
                    
                    for k, index in enumerate(object_frame_ndx):
                        if index > ndx:
                            object_frame_ndx[k] -= 1
                            
                    o.remapFrameStateAssociations([m for m in zip(o.frameIndices, object_frame_ndx)])
                
            scene_cursors = [o for o in self.sceneCursors.values()]
            
            for o in scene_cursors:
                o.removeState(ndx)
                
                #if not o.hasCommonState:
                if len(o.frameIndices) == 0:
                    self.sceneCursors.pop(o.name, None)
                    
                else:
                    # decrement the frame indices to the right of ndx
                    object_frame_ndx = [k for k in o.frameIndices]
                    
                    for k, index in enumerate(object_frame_ndx):
                        if index > ndx:
                            object_frame_ndx[k] -= 1
                            
                    o.remapFrameStateAssociations([m for m in zip(o.frameIndices, object_frame_ndx)])
                
            scene_rois = [o for o in self.sceneRois.values()]
            
            for o in scene_rois:
                o.removeState(ndx)
                
                #if not o.hasCommonState:
                if len(o.frameIndices) == 0:
                    self.sceneRois.pop(o.name, None)
                    
                else:
                    # decrement the frame indices to the right of ndx
                    object_frame_ndx = [k for k in o.frameIndices]
                    
                    for k, index in enumerate(object_frame_ndx):
                        if index > ndx:
                            object_frame_ndx[k] -= 1
                            
                    o.remapFrameStateAssociations([m for m in zip(o.frameIndices, object_frame_ndx)])
                
            # by now we may have ended up with some (or all) of the planar graphics removed
                
            # remove frame index from the electrophysiology
            if len(self.electrophysiology.segments):
                del self.electrophysiology.segments[ndx]
                
            #for p in del_protocols:
                #self._trigger_protocols_.remove(p)
                
            #self.triggerProtocols = new_protocols
                
            if len(self.scansBlock.segments):
                del self.scansBlock.segments[ndx]
                
            if len(self.sceneBlock.segments):
                del self.sceneBlock.segments[ndx]
                
            if len(self.scanRegionScansProfiles.segments):
                del self.scanRegionScansProfiles.segments[ndx]
                
            if len(self.scanRegionSceneProfiles.segments):
                del self.scanRegionSceneProfiles.segments[ndx]
                
            new_units = set()
            
            self._scene_ = new_scene
            #self._scene_frames_ = self._scene_[0].shape[self.sceneFrameAxisIndex]
            self._scans_ = new_scans
            #self._scans_frames_ = self._scans_[0].shape[self.scansFrameAxisIndex]
            
            for p in del_protocols:
                p_ndx = self._trigger_protocols_.index(p)
                del self._trigger_protocols_[p_ndx]
                
            self._trigger_protocols_.sort(key=lambda x: x.segmentIndices()[0])
            
            for p in self._trigger_protocols_:
                rev_p = p.reverseAcquisition(copy=True)
                
                if not is_empty(self._electrophysiology_):
                    embed_trigger_protocol(p,
                                            self._electrophysiology_,
                                            clearTriggers=True,
                                            clearEvents=False)
                
                if not is_empty(self._scans_block_):
                    embed_trigger_protocol(rev_p,
                                            self._scans_block_,
                                            clearTriggers=True,
                                            clearEvents=False)
                
                if not is_empty(self._scene_block_):
                    embed_trigger_protocol(rev_p,
                                            self._scene_block_,
                                            clearTriggers=True,
                                            clearEvents=False)
                
            del_units = list()

            for u in self.analysisUnits:
                if u.landmark is not None:
                    if u.landmark.name not in self.scansCursors and \
                        u.landmark.name not in self.scansRois and \
                        u.landmark.name not in self.sceneCursors and \
                        u.landmark.name not in self.sceneRois:
                            
                        del_units.append(u)
                        
                    else:
                        for p in del_protocols:
                            if p in u.protocols:
                                p_ndx = u.protocols.index(p)
                                del u.protocols[p_ndx]
                                
            for u in del_units:
                self.removeAnalysisUnit(u)
                    
        except Exception as e:
            traceback.print_exc()
            return
        
        
        #self.electrophysiology = new_ephys
        #self._scans_block_ = new_scans_block
        #self._scene_block_ = new_scene_block
        #self._scan_region_scans_profiles_ = new_scans_profiles
        #self._scan_region_scene_profiles_ = new_scene_profiles
        
        return self
    
    #@safeWrapper
    def removeCursor(self, obj, scans=True):
        """Removes cursor obj from the data subset
        
        Parameters:
        ===========
        
        obj:  str (cursor name) or a pictgui.Cursor
        
        Keyword parameter:
        =================
        scans: boolean; when True, selects the scans subset; otherwise, 
                  selects scene subset
        
        Returns:
        =======
        The removed object (PlanarGraphics)
        
        """
        if scans:
            cursordict = self._scanscursors_
            where = "scans"
            
        else:
            cursordict = self._scenecursors_
            where = "scene"
            
        if isinstance(obj, str):
            if len(obj.strip()) == 0:
                return
            
            obj = cursordict.get(obj, None)

        
        if isinstance(obj, PlanarGraphics):
            #print("ScanData.removeCursor: %s, %s in %s" % (obj.type, obj.name, where))
            cursordict.pop(obj.name, None)
            
            #print("ScanData.removeCursor frontends", [f.name for f in obj.frontends])
            
            for kf, _ in enumerate(obj.frontends):
                f = obj.frontends[kf]
                #print("ScanData.removeCursor, removing frontend %d %s in %s" % (kf, f.name, f.parentwidget.windowTitle()))
                f.removeFromWidget()
                
            obj.frontends.clear()
            
        return obj
    
    @safeWrapper
    def removeCursors(self, scans=True):
        if scans:
            cursordict = self._scanscursors_
            
        else:
            cursordict = self._scenecursors_
            
        if len(cursordict) > 0:
            cursors = [c for c in cursordict.values()]
            
            for c in cursors:
                for f in c.frontends:
                    f.removeFromWidget()
                    
                c.frontends.clear()
                
        cursordict.clear()
            
    @safeWrapper
    def setCursors(self, *values, scans=True):
        """Constructs a nested dictionary of cursors.
        
        See getCursor() for details on cursors.
        
        Var-positional parameters:
        ==========================
        
        *values: expression list of one or several pictgui.Cursor objects
        
        NOTE: CAUTION: When empty, it will clear the entire cursors registry
                in the specified data subset 
        
        Keyword parameters:
        ====================
        
        scans = boolean: 
                True (default) sets the cursors in the scans data subset
                False: sets the cursors in the scene data subset
                
        
        Cursors registries "scansCursors" and "sceneCursors" are dictionaries 
        that map cursor ID (str) as keys to pictgui.Cursor objects as values.
        
        The frame(s) where a cursor is visible (and where it applies to) is determined
        by the cursor object frameIndices property.
        
        By default, cursors are visible in all frames available in the data.
        
        This can be changed by manipulating the cursor.frameIndices property
        
        See pictgui.PlanarGraphics for details.
        
        e.g.:
        
        {"spine01": <pictgui.Cursor object at xxxx>}
        
        """
        if scans:
            target = self.scans
            cursordict = self._scanscursors_
            #nFrames = self.scansFrames
            
        else:
            target = self.scene
            cursordict = self._scenecursors_
            #nFrames = self.sceneFrames
        
        if len(target) == 0:
            return
        
        if len(values) == 1:
            if isinstance(values[0], pgui.Cursor):
                cursordict[values[0].name] = values[0]
                    
            else:
                raise TypeError("Expecting a pictgui.Cursor")
            
        elif len(values) > 1:
            if all([isinstance(v, pgui.Cursor) for v in values]):
                for v in values:
                    cursordict[v.name] = v
                    
            else:
                raise TypeError("Expecting several pictgui.Cursor objects")
            
        else: # no var-pos params => clear the registry
            if len(cursordict):
                for c in cursordict.values():
                    c.frontends.clear()
                                               
            cursordict.clear()
            
    @safeWrapper
    def getRoi(self, name, scans=True):
        """Returns a reference to a roi, or None 
        
        A roi is a pictgui.PlanarGraphics object that is displayed in an image
        window by way of a pictgui.GraphicsObject "frontend". The PlanarGraphics
        object is the "backend" of the GUI GraphicsObject.
        
        If roi is not found, prints an error message to stderr and returns None.
        
        Parameters:
        ==========
        
        name    = str: roi name (ID) present in the dictionary
        
        frame   = int: index of the frame where roi is sought
        
        scans   = boolean: 
                            True (default) seeks roi in the scans data subset
                            False seeks roi in the scene data subset
        
        """
        if scans:
            roidict = self._scansrois_
            
        else:
            roidict = self._scenerois_
            
        try:
            return roidict[name]
        
        except:
            traceback.print_exc()
    
    @safeWrapper
    def setRoi(self, roi, scans=True, append=False):
        """Sets or appends a roi to the specified frame in a specified data subset.
        
        To remove a roi use removeRoi()
        
        Parameters:
        ===========
        
        roi     = pictgui.Path, pictgui.Rect or pictgui.Ellipse object
        
        Keyword parameters:
        ===================
        scans   = boolean:
                            True (default) chooses the scans data subset
                            False chooses scene subset
                    
        append  = boolean:
        
                            False (default): 
                                if roi.name exists in the dictionary keys it
                                    will be replaced with THIS roi
                                    
                                if roi.name does NOT exist in the dictionary 
                                    keys, it will replace the ENTIRE contents of
                                    the dictionary with THIS roi
                                    
                            True:
                                if roi.name exists in the dictionary keys, its 
                                    ID will be adjusted then it will be appended
                                    to the dictionary contents
                                    
                                if roi.name does NOT exist it will simply be 
                                    appended to the dictionary contents
        
        sceneRois and scansRois are dictionaries with str keys (roi ID) mapped to
            a pictgui.Path,  pictgui.Rect or pictgui.Ellipse object.
        
        e.g.:
        
        {"roi01": <pictgui.Rect object at xxxx>}
        
        """
        if not isinstance(roi, (pgui.Path, pgui.Rect, pgui.Ellipse)):
            raise TypeError("Expecting a pgui.Path, pgui.Rect, or a pgui.Ellipse; got %s instead" % type(value).__name__)
        
        if scans:
            roidict = self._scansrois_
            
        else:
            roidict = self._scenerois_
            
        if append:
            if roi.name in roidict.keys():
                roi.name = counter_suffix(roi.name, list(roidict.keys()))
                
            if roi in roidict.values():
                roi = roi.copy()
            
        roidict[roi.name] = roi
            
        return roi.name # why ? - answer to be used by the caller -- ?
        
    @safeWrapper
    def removeRoi(self, obj, scans=True):
        """Removes roi with roi ID (obj) "obj" from the data subset

        Parameters:
        ===========
        
        obj: str or roi obj

        Keyword parameter:
        =================
        scans: boolean; when True, selects scans subset; otherwise selects scene subset
        
        Returns:
        =======
        
        The removed object (a PlanarGraphics)
        
        """
        if scans:
            roidict = self._scansrois_
            where = "scans"
            
        else:
            roidict = self._scenerois_
            where = "scene"
            
        if isinstance(obj, str):
            if len(obj.strip()) == 0:
                return
            
            obj = roidict.get(obj, None)
            
        
        if isinstance(obj, PlanarGraphics):
            #print("ScanData.removeRoi: %s, %s in %s" % (obj.type, obj.name, where))
            roidict.pop(obj.name, None)
            
            for kf, f in enumerate(obj.frontends):
                #print("in removeRoi, removing frontend %d %s in %s" % (kf, f.name, f.parentwidget.windowTitle()))
                f.removeFromWidget()
                
            obj.frontends.clear()
        
        return obj
            
    @safeWrapper
    def removeRois(self, scans=True):
        if scans:
            roidict = self._scansrois_
            
        else:
            roidict = self._scenerois_
        
        if len(roidict) > 0:
            rois = [r for r in roidict.values()]
            
            for r in rois:
                for f in r.frontends:
                    f.removeFromWidget()
                    
                r.frontends.clear()
                
        roidict.clear()
            
    @safeWrapper
    def setRois(self, *values, scans=True):
        """Constructs a nested dictionary of rois.
        
        See getRoi() for details on ROIs.
        
        Var-positional parameters:
        ==========================
        
        *values: expression list of one or several 
                pictgui.Path, pictgui.Rect or pictgui.Ellipse objects
                
        NOTE: CAUTION: When empty, it will clear the entire ROIs registry
                in the specified data subset 
                
        NOTE: CAUTION: Rois given as parameters to this function call must have
                        distinct names.
                        Even when appending (see below), if a roi's name is found
                        in the registry keys, it will be replaced with the value 
                        specified here.
                
        
        Keyword parameters:
        ====================
        
        scans = boolean: 
                        True (default) sets the rois in the scans data subset
                        False: sets the rois in the scene data subset
                
        
        ROI registries "scansRois" and "sceneRois" are dictionaries that map
        roi ID (str) as keys, to a pictgui.Path, pictgui.Rect or pictgui.Ellipse 
        objects, as values.
        
        The frame(s) where a ROI is visible (and where it applies to) is determined
        by the ROI object frameIndices property.
        
        By default, rois are visible in all frames available in the data.
        
        This can be changed by manipulating the roi.frameIndices property
        
        See pictgui.PlanarGraphics for details.
        
        e.g.:
        
        {"spine01": <pictgui.Ellipse object at xxxx>}
        
        """
        if scans:
            target  = self.scans
            roidict = self._scansrois_
            #nFrames = self.scansFrames
            
        else:
            target  = self.scene
            roidict = self._scenerois_
            #nFrames = self.sceneFrames
            
        if len(target) == 0:
            return
        
        if len(values) == 1:
            if isinstance(values[0], (pgui.Path, pgui.Rect, pgui.Ellipse)):
                roidict[values[0].name] = values[0]
                
            else:
                raise TypeError("Expecting a pictgui.Path, pictgui.Rect or pictgui.Ellipse object; got %s instead" % type(values[0]).__name__)
                        
        elif len(values) > 1:
            if all([isinstance(r, (pgui.Path, pgui.rect, pgui.Ellipse)) for r in values]):
                for r in values:
                    roidict[r.name] = r
                        
            else:
                raise TypeError("Expecting several pictgui.Path, pictgui.Rect or pictgui.Ellipse objects")
            
        else: # no var-pos params => clear the registry
            if len(roidict):
                for r in roidict.values():
                    r.frontends.clear()
                    
            roidict.clear()
            
    def getSceneAxesCalibration(self, channel=0):
        """
        Gets the AxesCalibration for the specified scene channel (default 0)
        
        For multi-channel data, returns the AxesCalibration of the whole image;
        othwerwise returns the AxesCalibration for the single-channel scene image
        corresponding to the given channel index
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        if len(self.scene) == 0:
            return
        
        if not isinstance(channel, int):
            raise TypeError("channel index expected to be an int; got %s instead" % type(channel).__name__)
        
        if channel < 0:
            raise ValueError("channel index expected to be >= 0; got %d instead" % channel)
        
        if channel >= len(self.scene):
            # self.scene is a list with one possibly multi-channel VigraArray
            if len(self.scene) == 1:
                if channel > self.scene[0].channels:
                    raise ValueError("channel %d not found in self.scene[0] with %d channels" % (channel, self.scene[0].channels))
                
                else:
                    return self._scene_axes_calibrations_[0] # because there is only one VigraArray here
                
            else:
                raise ValueError("channel %d not found in self.scene with %d channels" % (channel, len(self.scene)))
                
                
        else:
            # self.scene is a list of single-channel VigraArrays
            return self._scene_axes_calibrations_[channel]
            
        
    def getScansAxesCalibration(self, channel=0):
        """
        Gets the AxesCalibration for the specified scans channel (default 0)
        
        For multi-channel data, returns the AxesCalibration of the whole image;
        othwerwise returns the AxesCalibration for the single-channel scans image
        corresponding to the given channel index
        
        FIXME/TODO adapt to a new scenario where all scans image data is a single
        multi-channel VigraArray
        
        """
        if len(self.scene) == 0:
            return
        
        if not isinstance(channel, int):
            raise TypeError("channel index expected to be an int; got %s instead" % type(channel).__name__)
        
        if channel < 0:
            raise ValueError("channel index expected to be >= 0; got %d instead" % channel)
        
        if channel >= len(self.scans):
            # self.scene is a list with one possibly multi-channel VigraArray
            if len(self.scans) == 1:
                if channel > self.scans[0].channels:
                    raise ValueError("channel %d not found in self.scans[0] with %d channels" % (channel, self.scans[0].channels))
                
                else:
                    return self._scans_axes_calibrations_[0] # because there is only one VigraArray here
                
            else:
                raise ValueError("channel %d not found in self.scans with %d channels" % (channel, len(self.scans)))
                
                
        else:
            # self.scene is a list of single-channel VigraArrays
            return self._scans_axes_calibrations_[channel]
            
        
        
            
    #@safeWrapper
    def averageFrames(self, frame_index=None, protocol=None):
        """Returns a new ScanData containing frame-average of data from 
        specified frames, or all data if frame_index is None
        
        FIXME
        ATTENTION: Assumes the entire scandata is an analysis unit. DO NOT USE WHEN
        THERE ARE SEVERAL UNITS DEFINED IN THE LINESCAN IMAGE(S)
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        result = ScanData()
        
        result._scandatatype_ = self.scanType
        result._analysismode_ = self.analysisMode
        result.analysisOptions  = deepcopy(self.analysisOptions)
        
        result._processed_ = self._processed_
        
        frameAxisNdx = self.scans[0].axistags.index(self.scansFrameAxis)
        
        if isinstance(protocol, str):
            tp = self.triggerProtocols
            
            if len(tp) == 0:
                raise RuntimeError("Data has no trigger protocols defined")
            
            else:
                pr = [p for p in tp if p.name == protocol]
                
                if len(pr) ==0:
                    raise RuntimeError("Protocol %s not found" % protocol)
                
                else:
                    protocol = pr[0]
                    
                    protocol_frames = protocol.segmentIndices()
                    protocol_name = protocol
        
        elif isinstance(protocol, dt.TriggerProtocol):
            protocol_frames = protocol.segmentIndices()
            protocol_name = protocol.name
            
        else:
            protocol_frames = [f for f in range(self.scansFrames)]
            protocol_name = ""
            
            if len(self.triggerProtocols) > 1:
                average=False # NOTE: 2018-01-30 22:38:12 cannot average across different protocols!
                
        if isinstance(frame_index, (tuple, list, range)):
            frame_ndx = [f for f in frame_index if f in protocol_frames]
            
        else:
            frame_ndx = protocol_frames
        
        if self.scans[0].shape[frameAxisNdx] > 1:
            avg_scans_shape = [s for s in self.scans[0].shape]
            avg_scans_shape[frameAxisNdx] = 1
            
            if len(frame_ndx):
                temp_scans_shape = [s for s in self.scans[0].shape]
                temp_scans_shape[frameAxisNdx] = len(frame_ndx)
                
                temp_scans = [vigra.VigraArray(temp_scans_shape, order = img.order, axistags = img.axistags)
                              for img in self.scans]
                
                for k, f in enumerate(frame_index):
                    for s, scan in enuemrate(self.scans):
                        temp_scans[s].bindAxis(selof.scansFrameAxis, k)[:] = \
                            scan.bindAxis(self.scansFrameAxis, f)[:]
                        
            else:
                temp_scans = self.scans
            
            avg_dest = [vigra.VigraArray(avg_scans_shape, order = img.order, axistags = img.axistags) for img in temp_scans]
            
            avg_dest = [np.mean(img, axis = frameAxisNdx) for img in temp_scans]
            
            result._parse_image_arrays_(None, avg_dest, scansFrameAxis = self.scansFrameAxis)
            
        else:
            result._parse_image_arrays_(None, self.scans, scansFrameAxis = self.scansFrameAxis)
            
        result.electrophysiology.segments.clear()
        
        if len(frame_ndx) > 1:
            # NOTE: 2018-01-30 23:11:10 no averaging needed when there's only one segment!
            events = self.electrophysiology.segments[frame_ndx[0]].events
            avg_segment = average_segments([self.electrophysiology.segments[f] for f in frame_ndx])
            avg_segment[0].events[:] = events
            
        else:
            avg_segment = average_segments(self.electrophysiology.segments)
            avg_segment[0].events[:] = self.electrophysiology.segments[0].events[:]
            
        result.electrophysiology.segments[:] = avg_segment
            
        result.scansBlock.segments.clear()
        
        if len(frame_ndx) > 1:
            avg_segment = average_segments([self.scansBlock.segments[f] for f in frame_ndx])
            
        else:
            avg_segment = average_segments(self.scansBlock.segments)
            
        result.scansBlock.segments[:] = avg_segment # NOTE: events will be assigned below

        #result.parseElectrophysiologyTriggerProtocols()
        
        # NOTE: will CREATE new protocols (with default names!) the OVERWRITE
        # the events in the signals blocks with references to the newly created
        # trigger events !!!
        result.adoptTriggerProtocols(self.electrophysiology)
        
        return result
        
                
    # ###
    # properties
    # ###
    
    @property
    def availableUnitTypes(self):
        return self._availableUnitTypes_
    
    @property
    def availableGenotypes(self):
        return self._availableGenotypes_
        
    @property
    def unitType(self):
        """Returns/sets the value of the type attribute of THIS ScanData object's analysis unit.
        """
        return self.analysisUnit.unit_type if isinstance(self.analysisUnit, AnalysisUnit) else "NA"
    
    #@unitType.setter
    #def unitType(self, value):
        #if isinstance(value, str):
            #if len(value.strip()) == 0:
                #self._analysis_unit_.unit_type = "unknown"
                
                #if len(self._analysis_units_):
                    #for unit in self._analysis_units_:
                        #unit.unit_type = None # reverts to the default
                
            #else:
                #self._analysis_unit_.unit_type = value
                
                #if len(self._analysis_units_):
                    #for units in self._analysis_units_:
                        #unit.unit_type = value
                
        #elif value is None:
            #self._analysis_unit_.unit_type = "unknown"
            
            #if len(self._analysis_unit_):
                #for unit in self._analysis_units_:
                    #unit.unit_type = None # reverts to the default
            
        #else:
            #raise TypeError("value expected to be a string or None; got %s instead" % type(value).__name__)
    
    @property
    def analysisUnits(self):
        """Returns the set of analysis units nested in this data, as a sorted list.
        These are/must be defined on landmarks (cursors or ROIs).
        The list is sorted by the names of the analysis units; it may be empty.
        
        NOTE: This property excludes the default analysis unit defined on the data.
        Instead, the latter is obtained by calling ScanData.getAnalysisUnit() 
        without parameters, or as the property ScanData.defaultAnalysisUnit
        
        See also ScanData.analysisUnit(...) for details.
        
        """
        return sorted([u for u in self._analysis_units_],
                       key = lambda x: x.name)
    
    @property
    def analysisUnitNames(self):
        """Returns the name of set of analysis units defined on landmarks in this Data.
        
        NOTE: This set does not contain the default analysis unit defined on the 
        entire data. The latter is obtained by calling ScanData.analysisUnit() 
        without parameters, or as the property ScanData.defaultAnalysisUnit
        
        See also ScanData.analysisUnit(...) for details.
        
        """
        return [u.name for u in self.analysisUnits]
        
    #@property
    #def sceneCursors(self):
        #"""Dictionary with str keys (cursor name) mapped to pictgui.Cursor objects
        
        
        #e.g.:
        
        #{"spine01": <pictgui.Cursor object at xxxx>}
        #"""   
        #if not hasattr(self, "_scenecursors_"):
            #if hasattr(self, "__scenecursors__"):
                #self._scenecursors_ = self.__scenecursors__
                #delattr(self, "__scenecursors__")
                
            #else:
                #self._scenecursors_ = collections.OrderedDict()
                
        #return self._scenecursors_
    
    #@property
    #def scansCursors(self):
        #"""Dictionary with str keys (cursor name) mapped to pictgui.Cursor objects
        
        
        #e.g.:
        
        #{"spine01": <pictgui.Cursor object at xxxx>}
        #"""   
        
        #return self._scanscursors_
    
    #@property
    #def scanCursors(self):
        #"""Same as scansCursors
        #"""
        #return self._scanscursors_
        
        
    #@property
    #def sceneRois(self):
        #""" A mapping of roi names to non-cursor PlanarGraphics
        
        #e.g.:
        
        #{"scanline":<pgui.Path object at xxx>}
        
        #Read-only; to adjust a roi access it via self.sceneRoi(name, frame) then 
        #adjust its values.
        
        #"""
        #return self._scenerois_
    
    #@property
    #def scansRois(self):
        #"""Read-only
        
        #scansRois is a dict with str keys (roi name) mapped to
        #pictgui.Path or pictgui.PathElements object
        #e.g.:
        
        #{"scanline":<pgui.Path object at xxx>}
        
        #Use direct access to scansRois members to adjust their values
        #"""
        #return self._scansrois_
    
    #@property
    #def scanRois(self):
        #"""Same as scansRois
        #"""
        #return self._scansrois_
    
    @property
    def scansLandmarks(self):
        """
        A list of landmarks defined in the scans images.
        
        The list is sorted by landmark name
        """
        return sorted([l for l in self.scansCursors.values()], key=lambda x:x.name)
    
    @property
    def scanLandmarks(self):
        """Same as scansLandmarks
        """
        return sorted([l for l in self.scansCursors.values()], key=lambda x:x.name)
    
    @property
    def sortedScansLandmarks(self):
        """
        A list of landmarks defined in the scans images.
        
        The list is sorted by the (X,Y) coordinates
        """
        return sorted([l for l in self.scansCursors.values()], key=lambda x:(x.x, x.y))
    
    @property
    def sceneLandmarks(self):
        """
        A list of landmarks defined in the scene images EXCLUDING the scanning landmark/trajectory/region.
        
        The list is sorted by landmark name
        """
        return sorted([l for l in self.sceneCursors.values()], key=lambda x:x.name)
    
    @property
    def sortedSceneLandmarks(self):
        """
        A list of landmarks defined in the scene images EXCLUDING the scanning landmark/trajectory/region.
        
        The list is sorted by the (X,Y) coordinates
        """
        return sorted([l for l in self.sceneCursors.values()], key=lambda x:(x.x, x.y))
    
    @property
    def landmarks(self):
        """A list of all the landmarks, EXCLUDING the scanning landmark/trajectory/region..
        """
        return [l for l in self.sceneCursors.values()]  + [l for l in self.sceneRois.values()] + \
               [l for l in self.scansCursors.values()] + [l for l in self.scansRois.values()]
    
    @property
    def landmarksDictionary(self):
        """A dict of all PlanarGraphics landmarks defined in this ScanData object.
        This EXCLUDES the scanRegion PlanarGraphics.
        
        The dict maps keywords to the PlanarGraphics dictionaries defined here:
        "scenecursors" -> self.sceneCursors
        "scenerois" -> self.sceneRois
        "scanscursors" -> self.scansCursors
        "scansrois" -> self.scansRois
        
        
        """
        return {"scenecursors":self.sceneCursors, "scenerois":self.sceneRois,\
                "scanscursors":self.scansCursors, "scansrois":self.scansRois}
    
    @property
    def modified(self):
        return self._modified_
    
    @modified.setter
    def modified(self, value:bool):
        if not isinstance(value, bool):
            raise TypeError("expecting a bool; got %s instead" % type(value).__name__)
        self._modified_ = value
        
    @property
    def processed(self):
        """True if image data has been processed in any way (i.e. filtered)
        """
        return self._processed_
    
    @property
    def scanRegion(self):
        """Alias to the self.scanTrajectory descriptor.
        Kept for backwards compatibility
        """
        return self.scanTrajectory
    
    @scanRegion.setter
    def scanRegion(self, value):
        self.scanTrajectory = value
    
    @processed.setter
    def processed(self, value:bool):
        if not isinstance(value, bool):
            raise TypeError("expecting a bool; fgot %s instead" % type(value).__name__)
        self._processed_ = value
        
    @property
    def electrophysiologySweeps(self):
        """Read-only.
        """
        
        return self.nFrames("electrophysiology")
    
    @property
    def electrophysiologySegments(self):
        """Read-only. Alias to self.electrophysiologySweeps
        """
        
        return self.electrophysiologySweeps
    
    @property
    def electrophysiologyFrames(self):
        """Read-only. Alias to self.electrophysiologySweeps
        """
        
        return self.electrophysiologySweeps
    
    @property
    def sceneFrames(self) -> int:
        """Read-only.
        
        Can only be changed indirectly, by either:
        1) changing the sceneFrameAxis
        2) appending/removing scene frames
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        """
        return self.nFrames("scene")
    
    @property
    def sceneFrameAxis(self) -> int:
        return self.sceneLayout.framesAxis
    
    @property
    def sceneChannels(self) -> int:
        """Read-only. 
        The number of channels in the scene data or 0 if no scene data exists.
         
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        """
        if len(self.scene) == 0:
            return 0
        
        if len(self.scene) == 1:
            return self.scene[0].channels
        
        else:
            return len(self.scene)

    @property
    def sceneChannelNames(self) -> tuple:
        """
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        if len(self.scene) == 0:
            return tuple()
        
        if len(self.scene) == 1:
            return (AxesCalibration(self.scene[0])["c"].channelNames, )
        
        return tuple(itertools.chain.from_iterable((AxesCalibration(self.scene[k])["c"].channelNames for k in range(len(self.scene)))))
        
    @sceneChannelNames.setter
    def sceneChannelNames(self, value:typing.Union[tuple, list, str]):
        """
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        if len(self.scene) == 0:
            return
        
        if self.sceneChannels > 1:
            if not isinstance(value, (tuple, list)) or not all([isinstance(v, str) for v in value]) or len(value) != self.sceneChannels:
                raise TypeError(f"Expecting a sequence of {self.sceneChannel} strings; got {value}")
            
        else:
            if isinstance(value, (tuple, list)) and len(value) >= 1:
                value = value[0]
                
            if not isinstance(value, str):
                raise TypeError(f"Expecting a str; got {value}")
            
        if len(self.scene) == 1:
            axcal = self.sceneAxesCalibration[0]
            for c in range(self.sceneChannels):
                axcal.setChannelName(c, value[c])
                
            axcal.calibrateAxis(self.scene[0].axistags["c"])
            
        else:
            for k,s in enumerate(self.scene):
                axcal = self.sceneAxesCalibration[k]
                axcal.setChannelName[0, value[k]]
                axcal.calibrateAxis(s.axistags["c"])
            
    @property
    def scansFrames(self) -> int:
        """Read-only.
        
        Can only be modifier indirectly by either:
        1) changing self.scansFrameAxis
        2) appending/removing scans frames
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        return self.nFrames("scans")
    
    @property
    def scansFrameAxis(self) -> int:
        return self.scansLayout.framesAxis
    
    @property
    def scansChannels(self) -> int:
        """The number of channels; read-only
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        if len(self._scans_) == 0:
            return 0
        
        if len(self.scans) == 1:
            return self.scans[0].channels
        
        else:
            return len(self.scans)
    
    @property
    def scansChannelNames(self) -> tuple:
        """
        """
        if len(self._scans_) == 0:
            return list()
        
        if len(self.scans) == 1: # this may be a multi-band image
            return AxesCalibration(self.scans[0])["c"].channelNames # to ensure we get a virtual channel if needed

        return tuple(itertools.chain.from_iterable((AxesCalibration(self.scans[k])["c"].channelNames for k in range(len(self.scans)))))
        
    @scansChannelNames.setter
    def scansChannelNames(self, value):
        """
        
        FIXME/TODO adapt to a new scenario where all scene image data is a single
        multi-channel VigraArray
        
        """
        if len(self._scans_) == 0:
            return
        
        if not isinstance(value, (tuple, list)) or not all([isinstance(v, str) for v in value]):
            raise TypeError("Expecting a list of strings")
        
        # check conformance to number of channels in the scene data
        if len(value) == self.scansChannels:
            if len(self.scans) == 1:
                axcal = AxisCalibrationData(self.scans[0].axistags["c"])
                axcal = self.getScansAxesCalibration(0)
                
                for c in range(self.scansChannels):
                    axcal.setChannelName(c, value[c])
                    
                axcal.calibrateAxis(self.scans[0].axistags["c"])

            else:
                for k, v in enumerate(value):
                    axcal = self.getScansAxesCalibration(k)
                    axcal.setChannelName(0, v)
                    axcal.calibrateAxis(self.scans[k].axistags["c"])
                
        else:
            raise ValueError("Expecting a str list with as many elements as channels (%d); got %d elements instead" % (self.scansChannels, len(value)))
        
    def nFrames(self, component:typing.Optional[str] = None) -> int:
        """Returns the number of frames in the data, or a specific data component.
        
        For data components containing 1D signals a 'frame' (a.k.a 'sweep') 
        corresponds to a neo.Segment; for image data, a 'frame' is a 2D slice 
        view of the data.
        
        Parameters:
        ==========
        component: str, one of: "scans", "scene", "electrophysiology", 
            Optional, default is None, in which case it reports the number of
            "master" frames in the framesMap property of the ScanData instance.
            
            
        NOTE: Secondary (derived) data children are organized in frames and
        have the same number of frames  or segments as the primary data children 
        from which they are derived.
        
        In ScanData, the secondary data children (and their sources) are:
        
        scansBlock (scans) 
            1D signals derived from ROIs or cursors in the scans (e.g., EPSCaTs 
            for Ca2+ imaging linescans).
            
        scansProfiles (scans)
            The pixel itensity profile along the scanning trajectory in the
            scans. 
            
        sceneBlock (scene)
            1D signals derived from ROIs or cursors in the scans (e.g., EPSCaTs 
            for Ca2+ imaging linescans).
            
        sceneProfiles (scene)
            The pixel itensity profile along the scanning trajectory in the
            scene.
            
        """
        if isinstance(component, str) and len(component.strip()):
            return self._get_component_nFrames_(component)

        else:
            # NOTE: 2022-01-12 09:02:05
            # use framesMap when available
            if isinstance(self.framesMap, FrameIndexLookup):
                return len(self.framesMap.masterFrames)
            else:
                return max(self._get_component_nFrames_(c[0]) for c in self._data_children_)
                
    #def remapFrames(self, )
    def makeHDF5Entity(self, group, name, oname, compression, chunks, track_order,
                       entity_cache):
        
        import h5py
        from iolib import h5io, jsonio
        
        cached_entity = h5io.getCachedEntity(entity_cache, self)
        
        if isinstance(cached_entity, h5py.Group):
            group[target_name] = cached_entity
            return cached_entity
        
        target_name, obj_attrs = h5io.makeObjAttrs(self, oname=oname)
        if isinstance(name, str) and len(name.strip()):
            target_name = name
        
        entity = group.create_group(target_name)
        h5io.storeEntityInCache(entity_cache, self, entity)
        entity.attrs.update(obj_attrs)

        
        # TODO: write the following as datasets in subgroups
        # scans
        # scene
        # ephys - avoid neo.NixIO/nix !
        # scans block
        # scene block
        # scans profiles
        # scene profiles
        # triggerProtocols
        #   check consistency with the trigger events embedded in 
        #   ephys, scans/scene block, analysis units
        # landmarks
        # analysis units
        # options
        # 
        # TODO write the following as group attributes
        # name
        # analysis mode
        # 
        
    def setFramesRelationship(self, *args, **kwargs):
        """TODO: 2021-12-05 23:11:07
        """
        pass
    

def concatenateScanData(*data, resample=True):
    if not all([isinstance(d, ScanData) for d in data]):
        raise TypeError("Incompatible data types: expecting ScanData objects")
    
    if len(data) <  2:
        raise RuntimeError("Need at least two objects to concatenate")
    
    result = data[0].copy()
    
    for d in data[1:]:
        result = result.concatenate(d)
        
    return result
    
def __set_valid_key_names__(obj):
    if isinstance(obj, ScanData):
        __set_valid_key_names__(obj._analysis_unit_)
        
        for au in obj._analysis_units_:
            __set_valid_key_names__(au)
            
        if len(obj.analysisOptions) and isinstance(obj.analysisOptions, dict):
            __set_valid_key_names__(obj.analysisOptions)
                
            if "Discrimination" in obj.analysisOptions and isinstance(obj.analysisOptions["Discrimination"], dict):
                if "data_2D" in obj.analysisOptions["Discrimination"]:
                    d2d = obj.analysisOptions["Discrimination"]["data_2D"]
                    obj.analysisOptions["Discrimination"].pop("data_2D", None)
                    obj.analysisOptions["Discrimination"]["Discr_2D"] = d2d
                    
            if "Fitting" in obj.analysisOptions and isinstance(obj.analysisOptions["Fitting"], dict):
                if "CoefficientNames" in obj.analysisOptions["Fitting"] and \
                    isinstance(obj.analysisOptions["Fitting"]["CoefficientNames"], (tuple, list)) and \
                        len(obj.analysisOptions["Fitting"]["CoefficientNames"]):
                            __set_valid_key_names__(obj.analysisOptions["Fitting"]["CoefficientNames"])
            
    elif isinstance(obj, AnalysisUnit):
        __set_valid_key_names__(obj.descriptors)
        if "Dd_Length" in obj.descriptors:
            value = obj.descriptors["Dd_Length"]
            obj.descriptors["Dendrite_Length"] = value
            obj.descriptors.pop("Dd_Length", None)
            
                
    elif isinstance(obj, (DataBag, dict)):
        items = list(obj.items())#[item for item in obj.items()]
        
        for item in items:
            if isinstance(item[0], str):
                try:
                    item_type = type(eval(item[0])).__name__
                    if item_type == "function":
                        continue
                    
                except:
                    pass
                    
                value = item[1]
                
                if isinstance(value, (dict, list)):
                    __set_valid_key_names__(value)
                
                obj.pop(item[0], None)
                obj[strutils.str2symbol(item[0])] = value
            
    
    elif hasattr(obj, "annotations"):
        if type(obj) in neo.__dict__.values() or isinstance(obj, DataSignal):
            __set_valid_key_names__(obj.annotations)
    
    elif isinstance(obj, (tuple, list)):
        for k, o in enumerate(obj):
            if isinstance(o, str):
                obj[k] = strutils.str2symbol(o)

def check_apiversion(data):
    if isinstance(data, (AxesCalibration, AnalysisUnit, ScanData)):
        if not hasattr(data, "apiversion"):
            return False
        
        if not isinstance(data.apiversion, tuple) or len(data.apiversion) !=2:
            return False
        
        return data.apiversion[0] + data.apiversion[1]/10 >= 0.2
            
    return True


@safeWrapper
def scanDataOptions(detection_predicate=1.3, roi_width = 10, 
                  reference="Ch1", indicator="Ch2", 
                  bleed_ref_ind = 0, bleed_ind_ref = 0, 
                  f0_begin = 0.10*pq.s, f0_end = 0.15*pq.s,
                  fit_begin = 0.05 * pq.s, fit_end = 1 * pq.s, 
                  int_begin = 0 * pq.s, int_end = 0.5 * pq.s,
                  peak_begin = 0.15 * pq.s, peak_end = 0.3 * pq.s,
                  initial=[], lower=[], upper=[]):
    """
    TODO: Customize all parameters on function signature; also write a GUI for this
    TODO: change API to use ScanDataOptions
    """
    # NOTE: 2018-06-20 09:14:25
    # now uses OrderedDict (small overhead but worth it)
    # updated to include event (trigger protocol) detection from the ephys data
    # (mapped to the key: "TriggerEventDetection")
    
    ret = Bunch()
    #ret = collections.OrderedDict()
    ret["name"] = "ScanDataOptions"
    
    ret["Channels"] = Bunch()
    #ret["Channels"] = collections.OrderedDict()
    ret["Channels"]["Reference"] = reference
    ret["Channels"]["Indicator"] = indicator
    ret["Channels"]["Bleed_ref_ind"] = bleed_ref_ind # fraction of reference channel that bleeds into indicator channel
    ret["Channels"]["Bleed_ind_ref"] = bleed_ind_ref # fraction of indicator channel that bleeds into reference channel
    
    ret["IndicatorCalibration"] = Bunch() # when all None, this is uncalibrated
    #ret["IndicatorCalibration"] = collections.OrderedDict() # when all None, this is uncalibrated
    # all must be either None, or scalars
    ret["IndicatorCalibration"]["Name"] = None
    ret["IndicatorCalibration"]["Kd"]   = np.nan
    ret["IndicatorCalibration"]["Fmin"] = np.nan
    ret["IndicatorCalibration"]["Fmax"] = np.nan

    ret["Discrimination"] = Bunch() # sucess vs failure
    #ret["Discrimination"] = collections.OrderedDict() # sucess vs failure
    
    # NOTE: 2017-11-22 11:46:41
    # mapping of a func_name to a dict of keyword params (**kwargs)
    # func signature must be func_name(x, **kwargs) and returns a scalar
    # default is below (Frobenius norm for matrices)):
    # axis is None because we operate on single-channel analogsignals (or datasignals)
    
    # NOTE: for multi component EPSCaTs (e.g.a train of EPSCaTs) there are more
    # than one base and peak intervals defined, respectively, before and after 
    # the trigger time for for the corresponding EPSCaT 
    #
    # since the comparison should be done between similarly sized regions, we 
    # define only one such window, that we the take UP TO the trigger time (for 
    # the base) or FROM the trigger time onward (for the peak) 
    
    # NOTE: the trigger times are established by trigger protocols, and NOT 
    # defined here
    
    #ret["Discrimination"]["Base"] = {"np.linalg.norm":{"axis":None, "ord":None}, "window": 0.05 * pq.s}
    ##ret["Discrimination"]["Peak"] = {"np.linalg.norm":{"axis":None, "ord":None}, "window": 0.05 * pq.s} 
    
    ret["Discrimination"]["Function"] = Bunch({"np.linalg.norm":Bunch({"axis":None, "ord":None})})
    #ret["Discrimination"]["Function"] = {"np.linalg.norm":{"axis":None, "ord":None}}
    ret["Discrimination"]["BaseWindow"] = 0.05 * pq.s
    ret["Discrimination"]["PeakWindow"] = 0.05 * pq.s
    ret["Discrimination"]["Discr_2D"] = False
    ret["Discrimination"]["WindowChoice"] = "delays" # one of "delays", "triggers", "cursors"
    ret["Discrimination"]["First"] = True

    ret["Discrimination"]["Predicate"] = "lambda x,y: x >= y" # binary predicate: 
                                                        # generates a function by 
                                                        # calling func = eval(str)
                                                        # where str is as shown here
                                                    
    ret["Discrimination"]["PredicateFunc"] = "lambda x,y: x/y" # calculates one scalar
                                                    # result between peak and base
                                                    
    ret["Discrimination"]["PredicateValue"] = detection_predicate # this will test a scalar (x) against
                                            # this value using the binary predicate 
                                            # given above
                                            #
                                            # scalar x is generated by PredicateFunc
                                            
    ret["Roi"] = Bunch()
    #ret["Roi"] = collections.OrderedDict()
    ret["Roi"]["width"] = roi_width # an int or "auto" => use widths generated by the scan roi detection algorithm
    #ret["Roi"]["auto"] = False # when True, set use 
    
    ret["Intervals"] = Bunch()
    #ret["Intervals"] = collections.OrderedDict()
    ret["Intervals"]["DarkCurrent"] = Bunch({"begin": None, "end": None}) #start, end, both quantities or None
    ret["Intervals"]["F0"] = Bunch({"begin":f0_begin, "end": f0_end}) # start, end both quantities
    ret["Intervals"]["Fit"] = Bunch({"begin":fit_begin, "end":fit_end}) # start, end both quantities
    ret["Intervals"]["Integration"] = Bunch({"begin":int_begin, "end":int_end}) # start, end, both quantities; 
    
    ret["AmplitudeMethod"] = "direct" # one of "direct" or "levels"
    
    #ret["Intervals"]["Peak"] = [peak_begin, peak_end] #  start, end both quantities
    
    
    # Fitting model parameters
    # NOTE: 2017-12-23 13:06:45
    # for each EPSCaT there are n * 2 + 3 parameters packed in a list, where n 
    # is the number of decay components in a single EPSCaT (this is done for 
    # generality, although in most cases single EPSCaT data is fitted well by a 
    # transient with one decay component)
    #
    # NOTE: 2017-12-23 13:12:15 
    # the last parameter in the list is a so-called "delay" (or "onset") and
    # represents the "location" of the transient relative to the beginning of 
    # the sweep.
    # WARNING its value may be the string "trigger", meaning it will be updated 
    # from the trigger protocols
    
    # For multiple EPSCaTs (e.g. an EPSCaT train, or when stimuli generate several
    # individually resolvable EPSCaTs) a list of such parameters must be given 
    # for every single EPSCaT in the compound, and packed in a list
    
    # Hence the ["Fitting"]["Initial"] is a list of lists of parameters
    # and so are the ["Fitting"]["Lower"] and ["Fitting"]["Upper"], for the 
    # lower and upper bounds, respectively, to replicate ["Fitting"]["Initial"]
    
    ret["TriggerEventDetection"] = Bunch()
    #ret["TriggerEventDetection"] = collections.OrderedDict()
    ret["TriggerEventDetection"]["Presynaptic"] = Bunch()
    #ret["TriggerEventDetection"]["Presynaptic"] = collections.OrderedDict()
    ret["TriggerEventDetection"]["Presynaptic"]["Channel"] = 0
    ret["TriggerEventDetection"]["Presynaptic"]["DetectionBegin"] = 0.2 * pq.s
    ret["TriggerEventDetection"]["Presynaptic"]["DetectionEnd"] = 0.3 * pq.s
    ret["TriggerEventDetection"]["Presynaptic"]["DetectEvents"] = False
    ret["TriggerEventDetection"]["Presynaptic"]["Name"] = "epsp"
    
    ret["TriggerEventDetection"]["Postsynaptic"] = Bunch()
    #ret["TriggerEventDetection"]["Postsynaptic"] = collections.OrderedDict()
    ret["TriggerEventDetection"]["Postsynaptic"]["Channel"] = 1
    ret["TriggerEventDetection"]["Postsynaptic"]["DetectionBegin"] = 0.2 * pq.s
    ret["TriggerEventDetection"]["Postsynaptic"]["DetectionEnd"] = 0.3 * pq.s
    ret["TriggerEventDetection"]["Postsynaptic"]["DetectEvents"] = False
    ret["TriggerEventDetection"]["Postsynaptic"]["Name"] = "bAP"
    
    ret["TriggerEventDetection"]["Photostimulation"] = Bunch()
    #ret["TriggerEventDetection"]["Photostimulation"] = collections.OrderedDict()
    ret["TriggerEventDetection"]["Photostimulation"]["Channel"] = 0
    ret["TriggerEventDetection"]["Photostimulation"]["DetectionBegin"] = 0 * pq.s
    ret["TriggerEventDetection"]["Photostimulation"]["DetectionEnd"] = 0 * pq.s
    ret["TriggerEventDetection"]["Photostimulation"]["DetectEvents"] = False
    ret["TriggerEventDetection"]["Photostimulation"]["Name"] = "uepsp"
    
    ret["TriggerEventDetection"]["Photostimulation"] = Bunch()
    #ret["TriggerEventDetection"]["Photostimulation"] = collections.OrderedDict()
    ret["TriggerEventDetection"]["Photostimulation"]["Channel"] = 0
    ret["TriggerEventDetection"]["Photostimulation"]["DetectionBegin"] = 0 * pq.s
    ret["TriggerEventDetection"]["Photostimulation"]["DetectionEnd"] = 0 * pq.s
    ret["TriggerEventDetection"]["Photostimulation"]["DetectEvents"] = False
    ret["TriggerEventDetection"]["Photostimulation"]["Name"] = "uepsp"
    
    ret["TriggerEventDetection"]["Imaging frame trigger"] = Bunch()
    #ret["TriggerEventDetection"]["Imaging frame trigger"] = collections.OrderedDict()
    ret["TriggerEventDetection"]["Imaging frame trigger"]["Channel"] = 3
    ret["TriggerEventDetection"]["Imaging frame trigger"]["DetectionBegin"] = 0.05 * pq.s
    ret["TriggerEventDetection"]["Imaging frame trigger"]["DetectionEnd"] = 0.1 * pq.s
    ret["TriggerEventDetection"]["Imaging frame trigger"]["DetectEvents"] = False
    ret["TriggerEventDetection"]["Imaging frame trigger"]["Name"] = "imaging"
    
    ret["Fitting"] = Bunch()
    #ret["Fitting"] = collections.OrderedDict()
    ret["Fitting"]["Fit"] = True
    ret["Fitting"]["FitComponents"] = True # when True, fits individual EPSCaT components in an EPSCaT train
    
    # NOTE: 2021-09-02 12:00:56
    # changed from nested lists to mappings
    
    ret["Fitting"]["Components"] = Bunch() # len of ret.Fitting.Components indicate how many components are there
    
    # by default we only define one component
    nDecays = 1
    parnames = [p for p in itertools.chain.from_iterable((("a%d"%k, "d%d"%k) for k in range(nDecays)))]
    parnames.extend(["o", "r", "x0"])
    
    for k in range(1):
        b = Bunch({})
        ret["Fitting"]["Components"]["%d"%k] = b
        
    ret["Fitting"]["Components"]["0"] = Bunch()
    ret["Fitting"]["Components"]["0"]
    
    
    
    # NOTE: below, "Initial", "Lower" and "Upper" are, respectively, the initial
    # EPSCaT model parameter values, and their lower & upper bounds, wrapped in a nested
    # list, where:
    # a) the OUTER list has as many elements as there are in the EPSCaT model
    # b) the INNER list (i.e. each element of the OUTER list) contains the
    # the ACTUAL parameter values for the corresponding EPSCaT component.
    #
    # NOTE: the EPSCaT fit model is a linear sum of several delayed waveforms, 
    # each with a single exponential rise + multiple exponential decays
    # (see core.models.compound_exp_rise_multi_decay()).
    #
    # A single Ca2+ transient event (single-component EPSCaT) is fitted by one such
    # waveform which takes at least five parameters
    # (see core.models.exp_rise_multi_decays() function):
    #
    #   x0              = onset (delay) of the transient; only makes sense when x0 >= 0
    #   r               = rising phase time constant; 
    #   a_0...a_(n-1)   = scale for each of the n decay components;
    #   d_0...d_(n-1)   = time constant for each of the decay components;
    #   o               = offset (`DC' component)
    #
    #
    # For a single EPSCaT as above, the "Initial", "Lower" and "Upper" lists
    # have one element each, namely, a list containing numerical values for as 
    # many parameter values as above.
    # 
    # For multi-component EPSCaTs the "Initial", "Lower" and "Upper" lists
    # contain one such list for every component.
    
    nParams = 0
    
    if len(initial) > 0:
        if all([isinstance(i, float) for i in initial]):
            ret["Fitting"]["Initial"] = [initial]
            if models.check_rise_decay_params(initial) <= 1:
                raise ValueError("Incorrect number of initial EPSCaT parameter values: %d; must be N x 2 + 3, for N decays" % len(initial))
            
            nParams = [len(initial)]
            
        elif all([all([isinstance(i, (tuple, list)) for i in i_] for i_ in initial)]):
            if all([models.check_rise_decay_params(i) >= 1 for i in initial]):
                ret["Fitting"]["Initial"] = initial
                
            else:
                raise ValueError("Incorrect number of initial EPSCaT parameter values")
            
            nParams = [len(initial) for i in initial]
            
        else:
            raise TypeError("Initial EPSCaT parameter values expected to be a list of floats or a list of lists of floats; got %s instead" % initial)
            
    else:
        ret["Fitting"]["Initial"] = [[1, 0.01, 0, 0.01, 0.25]]
        nParams = [5]
        
    if len(lower) > 0:
        if all([isinstance(i, float) for i in lower]):
            if len(lower) == 1:
                ret["Fitting"]["Lower"] = [lower * p for p in nParams]
                
            elif any([len(lower) != p for p in nParams]):
                raise TypeError("Lower bounds must contain 1 or %d values; got %d instead" % (nParams, len(lower)))
            
            ret["Fitting"]["Lower"] = [lower] * len(initial)
            
        
        elif all([all([isinstance(i, float) for i in i_]) for i_ in lower]):
            if len(lower) == len(ret["Fitting"]["Initial"]):
                if all([len(l) == p for p in nParams]):
                    ret["Fitting"]["Lower"] = lower
            
            else:
                raise TypeError("Mismatch between number of initial EPSCaT parameter values and lower bounds")
            
        else:
            raise TypeError("Lower bounds expected to be a list of floats or a list of lists of floats; got %s instead" % lower)
        
    else:
        ret["Fitting"]["Lower"] = [[0, 0, 0, 0, 0]]
        
    if len(upper) > 0:
        if all([isinstance(i, float) for i in upper]):
            if len(upper) == 1:
                ret["Fitting"]["Upper"] = [upper * p for p in nParams]
                
            elif any([len(upper) != p for p in nParams]):
                raise TypeError("Upper bounds must contain 1 or %d values; got %d instead" % (nParams, len(upper)))
            
            ret["Fitting"]["Upper"] = [upper] * len(initial)
            
        
        elif all([all([isinstance(i, float) for i in i_]) for i_ in upper]):
            if len(upper) == len(ret["Fitting"]["Initial"]):
                if all([len(l) == p for p in nParams]):
                    ret["Fitting"]["Upper"] = upper
            
            else:
                raise TypeError("Mismatch between number of initial EPSCaT parameter values and upper bounds")
            
        else:
            raise TypeError("Upper bounds expected to be a list of floats or a list of lists of floats; got %s instead" % upper)
        
        
    else:
        ret["Fitting"]["Upper"] = [[np.inf, np.inf, 1, np.inf, np.inf]]
        
    nDecays = max([models.check_rise_decay_params(i) for i in ret["Fitting"]["Initial"]])
    
    cfNames = list()
    
    for k in range(nDecays):
        cfNames.append("scale_%d" % k)
        cfNames.append("taudecay_%d" % k)
        
    cfNames += ["offset", "taurise", "delay"]
        
    ret["Fitting"]["CoefficientNames"] = cfNames
    
    return ret

def _new_ScanData(scans, scene, electrophysiology, metadata, kw):
    return ScanData(scans, scene, electrophysiology, metadata, **kw)
