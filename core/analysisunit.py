from core import prog
from core.prog import safeWrapper

class AnalysisUnit(object):
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
            scene to True, AnalysisUnit object will be forecuflly associated with
            scene data, rather than scans data.
                    
    Additional parameters (e.g. geometric descriptors) are given by the var-named
    parameters **kwargs of the constructor.
    
    """
    from gui import pictgui as pgui
    
    #"def" __init__(self, parent, source = "scans", landmark=None, protocols=None, 
                 #unit_type=None, cell=None, field=None, **kwargs):
        
    def __init__(self, parent, landmark=None, protocols=None, 
                 unit_type=None, cell=None, field=None, scene=False, name=None, **kwargs):
        
        """AnalysisUnit constructor.
        
        Positional parameters:
        ======================
        
        parent - a ScanData object; the AnalysisUnit object stores a reference.
        
        Named parameters:
        =================
        
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
        
        self.apiversion = (0,2)
        
        super().__init__()
        
        if not isinstance(parent, ScanData):
            raise TypeError("parent is expected to be a ScanData object; got %s instead" % type(parent).__name__)
        
        # NOTE: 2018-03-10 16:24:50 
        # weak references cannot be pickled
        #self._parent_ = weakref.ref(parent) 
        
        self._parent_ = parent
        
        self._inscene_ = scene
        
        self._unit_type_ = "unknown"
        
        self._cell_ = "NA"
        
        self._field_ = "NA"
        
        self._unit_name_ = None
        
        # NOTE:2019-01-14 21:08:02
        # a string identifying the source of the sample (animal ID, patient ID, 
        # culture ID, etc) as per experiment
        self._sample_source_ = "NA"
        
        # NOTE: 2019-01-16 14:05:10
        # a string for genotype: one of "wt", "het", "hom", or "na" (not available/unknown)
        self._genotype_ = "NA"
        
        self._gender_ = "NA"
        
        self._age_ = "NA" # str ("NA") or python time quantity
                            # (so that we can report it using custom age units in this module)
        
        self._protocols_ = list() #  holds REFERENCES to TriggerProtocols in the parent
        
        self._descriptors_ = DataBag()
        
        if not isinstance(landmark, (pgui.PlanarGraphics, type(None))):
            raise TypeError("landmark expected to be a pictgui.PlanarGraphics; got %s instead" % type(landmark).__name__)
        
        self._landmark_ = landmark
        
        # self._frames_ is a list of frame indices where the landmark is defined
        # Whe landmark is None, self._frames_ is the range object for all frames 
        # in the parent scene or scans, depending on the source
        #
        # NOTE that these frames are not necessarily identical to the frames
        # in the protocols, but there should be an overlap between protocol(s)
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
            # get the frames with ladnark states, irrespective of whether this
            # is defined in scene or scans
            self._frames_ = landmark.frameIndices
        
        if isinstance(protocols, TriggerProtocol):
            self._protocols_ = [protocols]
            
        elif isinstance(protocols, (tuple, list)) and all([isinstance(t, TriggerProtocol) for t in protocols]):
            names = [t.name for t in protocols]
            
            if any([names.count(n)>1 for n in names]):
                raise ValueError("Protocols must have unique names")
            
            self._protocols_ = protocols # a reference!
            
        elif protocols is None:
            self._protocols_ = list()
            
        else:
            raise TypeError("protocol expected to be a TriggerProtocol object or a sequence of TriggerProtocol objects; got %s instead" % type(protocol).__name__)
        
        if isinstance(unit_type, str):
            if len(unit_type.strip()) == 0:
                raise ValueError("unit_type cannot be an empty string and cannot contain only blanks")
            
            if unit_type not in ("unknown", "NA"):
                self._unit_type_ = strutils.string_to_valid_identifier(unit_type)
                #self._unit_type_ = strutils.string_to_R_identifier(unit_type)
                
            else:
                self._unit_type_  = unit_type
                
        elif unit_type is None:
            if self._landmark_ is None:
                self._unit_type_ = "unknown"
                
            else:
                # UnitTypes is a defaultdict object, therefore the line below
                # automatically sets unit_type to unknown if gthe first character
                # in the landmark name is not found in UnitTypes keys
                # FIXME come up with a better lookup criterion
                self._unit_type_ = UnitTypes[self._landmark_.name[0]] 
                
        else:
            raise TypeError("unit_type expected to be a string, or None; got %s instead" % type(unit_type).__name__)
        
        if cell is None:
            self._cell_ = "NA"
        
        elif isinstance(cell, str):
            self._cell_ = strutils.string_to_valid_identifier(cell)
            #self._cell_ = strutils.string_to_R_identifier(cell)
            
        else:
            raise TypeError("cell expected to be a str or None; got %s instead" % type(cell).__name__)
        
        if field is None:
            self._field_ = "NA"
                
        elif isinstance(field, str):
            self._field_ = strutils.string_to_valid_identifier(field)
            #self._field_ = strutils.string_to_R_identifier(field)
            
        else:
            raise TypeError("field expected to be a str or None; got %s instead" % type(field).__name__)
        
        if isinstance(name, str) and len(name.strip()) > 0:
            self._unit_name_ = name
            
        elif name is not None:
            raise TypeError("name expected to be a str or None; got %s instead" % type(name).__name__)
            
        self._descriptors_.update(kwargs)
        
    def _upgrade_API_(self):
        from gui import pictgui as pgui
        
        def _upgrade_attribute_(old_name, new_name, attr_type, default):
            needs_must = False
            if not hasattr(self, new_name):
                needs_must = True
                
            else:
                attribute = getattr(self, new_name)
                
                if not isinstance(attribute, attr_type):
                    needs_must = True
                    
            if needs_must:
                if hasattr(self, old_name):
                    old_attribute = getattr(self, old_name)
                    
                    if isinstance(old_attribute, attr_type):
                        setattr(self, new_name, old_attribute)
                        delattr(self, old_name)
                        
                    else:
                        setattr(self, new_name, default)
                        delattr(self, old_name)
                        
                else:
                    setattr(self, new_name, default)
                    
        if hasattr(self, "apiversion") and isinstance(self.apiversion, tuple) and len(self.apiversion)>=2 and all(isinstance(v, numbers.Number) for v in self.apiversion):
            vernum = self.apiversion[0] + self.apiversion[1]/10
            
            if vernum >= 0.2:
                return
            
        _upgrade_attribute_("__parent__", "_parent_", ScanData, ScanData())
        _upgrade_attribute_("__inscene__", "_inscene_", bool, False)
        _upgrade_attribute_("__unit_type__", "_unit_type_", str, "unknown")
        _upgrade_attribute_("__cell__", "_cell_", str, "NA")
        _upgrade_attribute_("__field__", "_field_", str, "NA")
        _upgrade_attribute_("__genotype__", "_genotype_", str, "NA")
        _upgrade_attribute_("__gender__", "_gender_", str, "NA")
        _upgrade_attribute_("__age__", "_age_", str, "NA")
        _upgrade_attribute_("__sample_source__", "_sample_source_", str, "NA")
        _upgrade_attribute_("__unit_name__", "_unit_name_", (str, type(None)), None)
        _upgrade_attribute_("__protocols__", "_protocols_", list, list())
        _upgrade_attribute_("__descriptors__", "_descriptors_", DataBag, DataBag())
        _upgrade_attribute_("__landmark__", "_landmark_", (pgui.PlanarGraphics, type(None)), None)
        
        if isinstance(self._landmark_, pgui.PlanarGraphics):
            self._landmark_._upgrade_API_()
        
        self.apiversion = (0, 2)
        
    #"def" __eq__(self, other):
        #if not isinstance(other, AnalysisUnit):
            #return False
        
        #sameName = self.name == other.name
        
        #sameParent = self._parent_ == other._parent
        
        #sameSource = self._source == other._source
        
        #sameLandmark = self._landmark_ == other._landmark
        
        #sameProtocols = all([p in other._protocols for p in self._protocols_])
        
        #sameType = self._unit_type_ == other._type
        
        #sameCell = self._cell_ == other._cell_
        
        #sameField = self._field_ == other._field_
        
        #sameDescriptors = self._descriptors_ == other._descriptors_
        
        #return sameParent and sameName and sameSource and sameLandmark and sameProtocols and sameType and sameCell and sameField and sameDescriptors
    
    def __str__(self):
        result = list()
        result.append("\n%s:" % self.__class__.__name__)
        result.append("Name: %s" % self.name)
        result.append("Cell: %s" % self.cell)
        result.append("Field: %s" % self.field)
        result.append("Unit Type: %s" % self.type)
        result.append("Landmark: %s" % str(self.landmark))
        
        result.append("Protocol(s):")
        p_list = list()
        for p in self.protocols:
            p_list.append("\t%s on frames %s" % (p.name, str(p.segmentIndices())))
            
        if len(p_list)>1:
            result.append(", ".join(p_list))
        else:
            result.append("".join(p_list))
            
        result.append("Frames:")
        result.append(str(self.frames))
            
        result.append("Descriptors:")
        d_list = list()
        for key in self._descriptors_.sortedkeys():
            d_list.append("\t%s: %s" % (key, self._descriptors_[key]))
            
        if len(d_list)>1:
            result.append("\n".join(d_list))
        else:
            result.append("".join(d_list))
            result.append("\n")
            
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
                            signal_index = neoutils.get_index_of_named_signal(self.parent.sceneBlock.segments[f], self.name, silent=True)
                            
                            if signal_index is None:
                                raise RuntimeError("Analysis unit %s on entire scan data %s does not appear to have been analysed for frame %d" %\
                                    (self.name, self.parent.name, f))
                            
                        else:
                            signal_index = neoutils.get_index_of_named_signal(self.parent.sceneBlock.segments[f], self.landmark.name, silent=True)
                        
                            if signal_index is None:
                                raise RuntimeError("Analysis unit %s on landmark %s in scan data %s does not appear to have been analysed for frame %d" %\
                                    (self.name, self.landmark.name, self.parent.name, f))
                            
                        annotations = self.parent.sceneBlock.segments[f].analogsignals[signal_index].annotations
                    
                    else:
                        if f not in range(len(self.parent.scansBlock.segments)):
                            raise RuntimeError("Frame %d does not appear to have been analysed for unit %s in scan data %s" % \
                                (f, self.name, self.parent.name))
                        
                        if self.landmark is None:
                            signal_index = neoutils.get_index_of_named_signal(self.parent.scansBlock.segments[f], self.name, silent=True)
                            
                            if signal_index is None:
                                raise RuntimeError("Analysis unit %s on entire scan data %s does not appear to have been analysed for frame %d" %\
                                    (self.name, self.parent.name, f))
                            
                        else:
                            signal_index = neoutils.get_index_of_named_signal(self.parent.scansBlock.segments[f], self.landmark.name, silent=True)
                        
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
                        signal_index = neoutils.get_index_of_named_signal(self.parent.sceneBlock.segments[f], self.name, silent=True)
                        
                        if signal_index is None:
                            raise RuntimeError("Analysis unit %s on entire scan data %s does not appear to have been analysed for frame %d" %\
                                (self.name, self.parent.name, f))
                        
                    else:
                        signal_index = neoutils.get_index_of_named_signal(self.parent.sceneBlock.segments[f], self.landmark.name, silent=True)
                    
                        if signal_index is None:
                            raise RuntimeError("Analysis unit %s on landmark %s in scan data %s does not appear to have been analysed for frame %d" %\
                                (self.name, self.landmark.name, self.parent.name, f))
                        
                    annotations = self.parent.sceneBlock.segments[f].analogsignals[signal_index].annotations
                    
                else:
                    if f not in range(len(self.parent.scansBlock.segments)):
                        raise RuntimeError("Frame %d does not appear to have been analysed for unit %s in scan data %s" % \
                            (f, self.name, self.parent.name))
                    
                    if self.landmark is None:
                        signal_index = neoutils.get_index_of_named_signal(self.parent.scansBlock.segments[f], self.name, silent=True)
                        
                        if signal_index is None:
                            raise RuntimeError("Analysis unit %s on entire scan data %s does not appear to have been analysed for frame %d" %\
                                (self.name, self.parent.name, f))
                        
                    else:
                        signal_index = neoutils.get_index_of_named_signal(self.parent.scansBlock.segments[f], self.landmark.name, silent=True)
                    
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
            raise TypeError("Expecting a ScanData object; got %s instead" % type(ob).__name__)
        
        
        self._parent_ = obj
            
    @property
    def landmark(self):
        if not hasattr(self, "_landmark_"):
            self._landmark_ = None
            
        if hasattr(self, "_landmark"):
            self._landmark_ = self._landmark
            del self._landmark
            
        return self._landmark_
    
    @landmark.setter
    def landmark(self, obj):
        if not isinstance(obj, pgui.PlanarGraphics):
            raise TypeError("Expecting a pictgui.PlanarGraphics object; got %s instead" % type(obj).__name__)
        
        if hasattr(self, "_landmark"):
            self._landmark_ = self._landmark
            del self._landmark
            
        self._landmark_ = obj
    
    @property
    def name(self):
        """
        This is the name of the landmark used to define this unit, or of the 
        "parent" ScanData when landmark is None
        """
        if not hasattr(self, "_landmark_"):
            self._landmark_ = None
            
        if not hasattr(self, "_unit_name_"):
            self._unit_name_ = None
            
        if hasattr(self, "_landmark"):
            self._landmark_ = self._landmark
            del self._landmark
            
        if not hasattr(self, "_parent_"):
            self._parent_ = None
            
        if hasattr(self, "_parent"):
            self._parent_ = self._parent
            del self._parent
        
        if not hasattr(self, "_unit_name_") or self._unit_name_ is None:
            if self._landmark_ is None:
                if self._parent_ is not None:
                    self._unit_name_ = self._parent_.name
                    
                else:
                    self._unit_name_ = "NA"

            else:
                self._unit_name_ = self._landmark_.name
                
        return self._unit_name_
    
    @name.setter
    def name(self, value):
        """Assigns a custom landmark name.
        
        Parameters:
        ===========
        value: a str or None
        
        When value is None, a string containing blanks only, or an empty string,
        the name is reset to the default, i.e. the name of self.landmark, or the
        name of the parent ScanData if self.landmark is None.
        
        
        """
        if not hasattr(self, "_unit_name_"):
            self._unit_name_ = None
            
        if not hasattr(self, "_parent_"):
            self._parent_ = None
            
        if hasattr(self, "_parent"):
            self._parent_ = self._parent
            del self._parent
        
        if isinstance(value, str):
            if len(value.strip()) == 0: # empty string passed
                # reset name to the landmark name or scandata
                if self._landmark_ is None:
                    if self._parent_ is not None:
                        self._unit_name_ = self._parent_.name
                        
                    else:
                        self._unit_name_ = "NA"
                    
                else:
                    self._unit_name_ = self._landmark_.name
                    
            else:
                self._unit_name_ = value
            
        elif name is None:
            # reset name to the landmark name or scandata
            if self._landmark_ is None:
                if self._parent_ is not None:
                    self._unit_name_ = self._parent_.name
                    
                else:
                    self._unit_name_ = "NA"
                
            else:
                self._unit_name_ = self._landmark_.name
            
        else:
            raise TypeError("expecting a string or None; got %s instead" % type(value).__name__)
        
    @property
    def type(self):
        if not hasattr(self, "_unit_type_"):
            self._unit_type_ = "unknown"
            
        if hasattr(self, "_type"):
            self._unit_type_ = self._type
            del self._type
            
        return self._unit_type_
    
    @type.setter
    def type(self, value):
        """Allow user-defined unit type names.
        """
        if not hasattr(self, "_unit_type_"):
            self._unit_type_ = "unknown"
            
        if hasattr(self, "_type"):
            self._unit_type_ = self._type
            del self._type
            
        if isinstance(value, str):
            if len(value.strip()) == 0:
                raise ValueError("type cannot be empty or contain only blank characters")
            
            if value.strip().lower() == "default":
                self._unit_type_ = UnitTypes[self._landmark_.name]
            
            else:
                self._unit_type_ = value
            
        elif value is None:
            self._unit_type_ = UnitTypes[self._landmark_.name]
            
        else:
            raise TypeError("Expecting a str or None; got %s instead" % type(value).__name__)
        
    @property
    def age(self):
        if not hasattr(self, "_age_"):
            self._age_ = "NA"
            
        return self._age_
    
    @age.setter
    def age(self, value):
        """str ('NA'), datetime.timedelta or pq.day, pq.month, or any custom age units in this module
        NOTE that timedelta objects hold up to days (for 'date'), 
        """
        if isinstance(value, str):
            if value.strip().lower() != "na":
                raise ValueError("When a str, age must be 'NA'; got %s instead" % valur)
            
            self._age_ = "NA"
            
        elif value is None:
            self._age_ = "NA"
            
        elif isinstance(value, datetime.timedelta):
            days = value.days
            seconds = value.seconds
            musecs = value.microseconds
            
            # NOTE: round up to the largest time unit
            
            if days == 0:
                # maybe seconds
                if seconds == 0:
                    self._age_ = musecs * pq.us
                
                else:
                    if musecs == 0:
                        self._age_ = seconds * pq.s
                        
                    else:
                        self._age_ = value.total_seconds() * pq.s
                        
            else:
                # just report age as days
                self._age_ = days * pq.day
                
        elif isinstance(value, pq.Quantity):
            if not check_time_units(value):
                raise TypeError("Expecting a time quantity; got %s instead" % type(value).__name__)
            
            self._age_ = value
            
        else:
            raise TypeError("Expecting a str ('NA'), a datetime.timedelta, a python time quantity, or None; got %s instead" % type(value).__name__)
        
    @property
    def gender(self):
        if not hasattr(self, "_gender_"):
            self._gender_ = "NA"
            
        return self._gender_
    
    @gender.setter
    def gender(self, value):
        if isinstance(value, str):
            if len(value.strip()) == 0:
                value = "NA"
                
            else:
                if value.lower().strip() not in ("na", "f", "m"):
                    value = "NA"
                    
                else:
                    value = value.strip().upper()
                    
                self._gender_ = value
            
        else:
            raise TypeError("Expecting a string, one of 'NA', 'F', 'M' (case-insensitive); got %s instead" % type(value).__name__)
        
        
    @property
    def genotype(self):
        """Genotype: 
        String, typically one of "na", "wt", "het", "hom", but not restricted to these
        """
        if not hasattr(self, "_genotype_"):
            self._genotype_ = "NA"
            
        return self._genotype_
    
    @genotype.setter
    def genotype(self, value):
        if isinstance(value, str):
            if len(value.strip()) == 0:
                value = "NA"
                
            else:
                self._genotype_ = value
            
        elif value is None:
            self.__genotyope__ = "NA"
            
        else:
            raise TypeError("Expecting a string; got %s instead" % type(value).__name__)
        
    @property
    def sourceID(self):
        if not hasattr(self, "_sample_source_"):
            self._sample_source_ = "NA"
            
        return self._sample_source_
    
    @sourceID.setter
    def sourceID(self, value):
        if not hasattr(self, "_sample_source_"):
            self._sample_source_ = "NA"
            
        if isinstance(value, str):
            if len(value.strip()) == 0:
                self._sample_source_ = "NA"
                
            else:
                self._sample_source_ = value
            
        elif value is None:
            self._sample_source_ = "NA"
            
        else:
            raise TypeError("Expecting a str or None; got %s instead" % type(value).__name__)
        
    @property
    def cell(self):
        if not hasattr(self, "_cell_"):
            self._cell_ = "NA"
            
        if hasattr(self, "_cell"):
            # API upgrade
            self._cell_ = self._cell
            del self._cell
            
        return self._cell_
    
    @cell.setter
    def cell(self, value):
        if hasattr(self, "_cell"):
            self._cell_ = self._cell
            del self._cell
        
        if isinstance(value, str):
            if len(value.strip()) == 0:
                self._cell_ = "NA"
                
            else:
                self._cell_ = value
            
        elif value is None:
            self._cell_ = "NA"
            
        else:
            raise TypeError("Expecting a str or None; got %s instead" % type(value).__name__)
        
    @property
    def inScene(self):
        if not hasattr(self, "_inscene_"):
            self._inscene_ = False
            
        if hasattr(self, "_inscene"):
            # API upgrade
            self._inscene_ = self._inscene
            del self._inscene
            
        else:
            self._inscene_ = False
        
        return self._inscene_
    
    @inScene.setter
    def inScene(self, value):
        if not isinstance(value, bool):
            raise TypeError("Expecting a bool; got %s instead" % type(value).__name__)
        self._inscene_ = value
        
        if hasattr(self, "_inscene"):
            del self._inscene
    
    @property
    def field(self):
        if not hasattr(self, "_field_"):
            self._field_ = "NA"
            
        if hasattr(self, "_field"):
            self._field_ = self._field
            del self._field
            
        return self._field_
    
    @field.setter
    def field(self, value):
        if isinstance(value, str):
            if len(value.strip()) == 0:
                self._field_ = "NA"
                
            else:
                self._field_ = strutils.string_to_valid_identifier(value)
                #self._field_ = strutils.string_to_R_identifier(value)
            
        elif value is None:
            self._field_ = "NA"
            
        else:
            raise TypeError("Expecting a str; got %s instead" % type(value).__name__)
        
        if hasattr(self, "_field"):
            del self._field
            
    @safeWrapper
    def protocol(self, index):
        """Returns a trigger protocol specified by "index".
        
        Parameters:
        ==========
        "index" : a str or an int
        
        When index is a str, it must be the name of a protocol associated with this unit
        and that protocol is returned.
        
        When index is an int, it must be a frame index present in the "frames" property
        of this analysis unit object.
        
        Returns:
        ========
        
        The trigger protocol named as specified by "index", or associated
        with the frame specified by "index", depending on whether "index" is a 
        string or an integer.
        
        If there are no protocols, or the specified frame index does not 
        associate a protocol, the function returns None.
        
        """
        if len(self.protocols) == 0:
            return None
        
        if isinstance(index, str):
            if index in [p.name for p in self.protocols]:
                
                protocols = [p for p in self.protocols if p.name == index]
                
                if len(protocols) > 1:
                    raise RuntimeError("There appears to be %d protocols named '%s'" % (len(protocols), index))
                
                return protocols[0]
            
            else:
                raise ValueError("AnalysisUnit %s does not associate a protocol named %s" % (self.name, index))
            
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
            del self._protocols
            
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
        
    @property
    def descriptors(self):
        """The descriptors dictionary (a DataBag object)
        """
        if not hasattr(self, "_descriptors_"):
            self._descriptors_ = DataBag()
            
        if hasattr(self, "_descriptors"):
            self._descriptors_ = self._descriptors
            del self._descriptors
            
        return self._descriptors_
    
    @descriptors.setter
    def descriptors(self, value):
        if isinstance(value, (DataBag, dict)):
            self._descriptors_.clear()
            
            v = DataBag()
            for item in value.items():
                if not isinstance(item[0], str):
                    raise TypeError("Expecting a dict or a DataBag with string keys only")
                
                v[strutils.string_to_valid_identifier(item[0])] = item[0]
                
            self._descriptors_ = v
            
        else:
            raise TypeError("Expecting a dict or a DataBag; got %s instead" % type(value).__name__)
    
    @property
    def descriptorsList(self):
        """List of key/value tuples.
        For convenience.
        """
        if not hasattr(self, "_descriptors_"):
            self._descriptors_ = DataBag()
            
        if hasattr(self, "_descriptors"):
            self._descriptors_ = self._descriptors
            del self._descriptors
            
        ##print(self._descriptors_)
        descr = sorted([d for d in self._descriptors_.keys()])
        return [(k, self._descriptors_[k]) for k in descr]
    
    def getDescriptor(self, name):
        """Returns None if descriptor name does not exist.
        """
        if not hasattr(self, "_descriptors_"):
            self._descriptors_ = DataBag()
            
        if hasattr(self, "_descriptors"):
            self._descriptors_ = self._descriptors
            del self._descriptors
            
        if name in self._descriptors_.keys():
            return self._descriptors_[name]
        
    
    def setDescriptor(self, name, value):
        """Sets/adds a descriptor.
        """
        if not hasattr(self, "_descriptors_"):
            self._descriptors_ = DataBag()
            
        if hasattr(self, "_descriptors"):
            self._descriptors_ = self._descriptors
            del self._descriptors
            
        self._descriptors_[name] = value
            
    def asScanData(self, average=None):
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
            if self.getDescriptor("averaged") is None:
                average = False
                
            else:
                average = self.getDescriptor("averaged")
            
        
        result = self._parent_.extractAnalysisUnit(self._landmark_, 
                                                   protocol=self._protocols_,
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
        
        sameType = self.type == other.type
        
        sameCell = self.cell == other.cell
        
        sameField = self.field == other.field
        
        sameDescriptors = self.descriptors == other.descriptors
        
        return sameParent and sameName and sameSource and sameLandmark and sameProtocols and sameType and sameCell and sameField and sameDescriptors
    
    def is_same_as(self, other):
        return self.isSameAs(other)
    
    def copy(self):
        """Returns a shallow copy of this copy.
        
        The result's landmark and protocol(s) are references to the landmark and
        protocol(s) of this unit.
        
        """
        descriptors = dict([i for i in self._descriptors_.sorteditems()])
        
        # the advantage of copying protocols is that when an analysis unit is 
        # copied and its protocol frames are adjusted, the original protocol 
        # frames will also be adjusted breaking the original data
        #
        # the disadvantage is that by copying the protocol here one effectively
        # creates a new TriggerProtocol object which brakes its ownershiop
        # by the parent data
        #result = AnalysisUnit(self.parent, landmark=self.landmark,
                           #protocols = [p.copy() for p in self.protocols], 
                           #unit_type = self.type, cell = self.cell, field = self.field, 
                           #scene=self.inScene, name=self.name, **descriptors)
        
        #result = AnalysisUnit(self.parent, self.dataSource, landmark=self.landmark,
                           #protocols = self.protocols, unit_type = self.type, 
                           #cell = self.cell, field = self.field, **descriptor)
                           
        # on balance, when extracting analysis unit data, best is to create
        # new analysis_units rather than just copying this one, after creating
        # new landmarks and new protocols to suit
        result = AnalysisUnit(self.parent, landmark=self.landmark,
                           protocols = [p for p in self.protocols], 
                           unit_type = self.type, cell = self.cell, field = self.field, 
                           scene=self.inScene, name=self.name, **descriptors)
        
        result.age = self.age
        #result.cell = self.cell
        result.gender = self.gender
        result.genotype = self.genotype
        result.sourceID = self.sourceID
        #result.inScene = self.inScene
        #result.parent = None

        
        return result
        
