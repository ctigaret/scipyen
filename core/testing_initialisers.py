In [3]: scdata = ScanData()
parse_descriptor_specification ('scans', (<class 'list'>, <class 'tuple'>), <class 'vigra.arraytypes.VigraArray'>)
parse_descriptor_specification ('scene', (<class 'list'>, <class 'tuple'>), <class 'vigra.arraytypes.VigraArray'>)
parse_descriptor_specification ('electrophysiology', (<neo.core.block.Block object at 0x7f11f3bae080>, None))
parse_descriptor_specification ('scansBlock', <neo.core.block.Block object at 0x7f11f3bae0b0>)
parse_descriptor_specification ('scansProfiles', <neo.core.block.Block object at 0x7f11f3bae110>)
parse_descriptor_specification ('sceneBlock', <neo.core.block.Block object at 0x7f11f3bae2f0>)
parse_descriptor_specification ('sceneProfiles', <neo.core.block.Block object at 0x7f11f3bae1d0>)
parse_descriptor_specification ('electrophysiologyResult', <class 'pandas.core.frame.DataFrame'>)
parse_descriptor_specification ('imagingResult', <class 'pandas.core.frame.DataFrame'>)
parse_descriptor_specification ('result', <class 'pandas.core.frame.DataFrame'>)
parse_descriptor_specification ('sceneAxesCalibration', <class 'list'>, <class 'imaging.axiscalibration.AxesCalibration'>)
parse_descriptor_specification ('scansAxesCalibration', <class 'list'>, <class 'imaging.axiscalibration.AxesCalibration'>)
parse_descriptor_specification ('sceneLayout', <class 'dict'>)
parse_descriptor_specification ('scansLayout', <class 'dict'>)
parse_descriptor_specification ('framesMap', <class 'core.multiframeindex.FrameIndexLookup'>)
parse_descriptor_specification ('scansCursors', <class 'dict'>, <class 'gui.planargraphics.Cursor'>)
parse_descriptor_specification ('scansRois', <class 'dict'>, <class 'gui.planargraphics.PlanarGraphics'>)
parse_descriptor_specification ('scanTrajectory', (<class 'gui.planargraphics.PlanarGraphics'>, <class 'NoneType'>))
parse_descriptor_specification ('sceneCursors', <class 'dict'>, <class 'gui.planargraphics.Cursor'>)
parse_descriptor_specification ('sceneRois', <class 'dict'>, <class 'gui.planargraphics.PlanarGraphics'>)
parse_descriptor_specification ('analysisUnits', <class 'set'>, <class 'imaging.scandata.AnalysisUnit'>)
parse_descriptor_specification ('analysisUnit', <class 'imaging.scandata.AnalysisUnit'>)
parse_descriptor_specification ('metadata', <class 'dict'>)
parse_descriptor_specification ('analysisOptions', <class 'dict'>)
parse_descriptor_specification ('analysisMode', <ScanDataAnalysisMode.frame: 1>)
parse_descriptor_specification ('type', <ScanDataType.linescan: 1>)
parse_descriptor_specification ('sourceID', 'NA')
parse_descriptor_specification ('cell', 'NA')
parse_descriptor_specification ('field', 'NA')
parse_descriptor_specification ('genotype', 'NA')
parse_descriptor_specification ('sex', 'NA')
parse_descriptor_specification ('age', (array(0.) * s, 'NA'))
parse_descriptor_specification ('biometric_weight', (array(0.) * g, 'NA'))
parse_descriptor_specification ('biometric_height', (array(0.) * m, 'NA'))
parse_descriptor_specification ('procedure_type', 'NA')
parse_descriptor_specification ('procedure_name', 'NA')
parse_descriptor_specification ('procedure_dose', (array(0.) * g, 'NA'))
parse_descriptor_specification ('procedure_route', 'NA')
parse_descriptor_specification ('procedure_schedule', <Epoch: >)
parse_descriptor_specification ('triggers', [], <class 'core.triggerprotocols.TriggerProtocol'>)
parse_descriptor_specification ('file_datetime', <class 'datetime.datetime'>)
parse_descriptor_specification ('rec_datetime', <class 'datetime.datetime'>)
parse_descriptor_specification ('analysis_datetime', <class 'datetime.datetime'>)
parse_descriptor_specification ('descriptors', <class 'dict'>)
parse_descriptor_specification ('name', <class 'str'>)
parse_descriptor_specification ('description', <class 'str'>)
parse_descriptor_specification ('file_origin', <class 'str'>)

In [4]: sdata = ltp.SynapticPlasticityData()
parse_descriptor_specification ('pathways', (<class 'list'>, <class 'tuple'>), <class 'ephys.ltp.SynapticPathway'>)
parse_descriptor_specification ('Rs', <class 'neo.core.irregularlysampledsignal.IrregularlySampledSignal'>)
parse_descriptor_specification ('Rin', <class 'neo.core.irregularlysampledsignal.IrregularlySampledSignal'>)
parse_descriptor_specification ('SynapticResponse', <class 'list'>, <class 'neo.core.irregularlysampledsignal.IrregularlySampledSignal'>)
parse_descriptor_specification result
rt = {'name': 'r', 'default_value': 'e', 'default_value_type': <class 'str'>, 'default_element_types': None, 'default_item_types': None, 'default_value_ndim': None, 'default_value_dtype': None, 'default_value_shape': None, 'default_value_units': None, 'default_array_order': None, 'default_axistags': None}; param = u
---------------------------------------------------------------------------
ValueError                                Traceback (most recent call last)
Cell In[4], line 1
----> 1 sdata = ltp.SynapticPlasticityData()

File ~/scipyen/ephys/ltp.py:297, in SynapticPlasticityData.__init__(self, pathways, **kwargs)
    296 def __init__(self, pathways:typing.Optional[typing.Sequence[SynapticPathway]]=None, **kwargs):
--> 297     super().__init__(**kwargs)

File ~/scipyen/core/basescipyen.py:117, in BaseScipyenData.__init__(self, name, description, file_origin, **kwargs)
    116 def __init__(self, name=None, description=None, file_origin=None, **kwargs):
--> 117     WithDescriptors.__init__(self, name=None, description=None, file_origin=None, **kwargs)
    119     # so that we don't confuse baseneo._check_annotations in the __init__ 
    120     # further below
    121     for d in self._descriptor_attributes_:

File ~/scipyen/core/prog.py:1879, in WithDescriptors.__init__(self, *args, **kwargs)
   1877 def __init__(self, *args, **kwargs):
   1878    for attr in self._descriptor_attributes_:
-> 1879         attr_dict = parse_descriptor_specification(attr)
   1880         suggested_value = kwargs.pop(attr[0], attr_dict["value"])
   1881         if isinstance(suggested_value, tuple) and len(suggested_value):

File ~/scipyen/core/prog.py:1682, in parse_descriptor_specification(x)
   1680     if len(x) > 3:
   1681         for x_ in x[3:]:
-> 1682             __check_array_attribute__(ret, x_)
   1684 # NOTE: 2021-11-29 17:27:07
   1685 # generate arguments for a DescriptorGenericValidator
   1686 type_dict = dict()

File ~/scipyen/core/prog.py:1500, in parse_descriptor_specification.<locals>.__check_array_attribute__(rt, param)
   1498 if rt["default_value"] is not None:
   1499     if not isinstance(rt["default_value"], np.ndarray):
-> 1500         raise ValueError(f"Type of the default value type {type(rt['default_value']).__name__} is not a numpy ndarray")
   1502 if isinstance(param, collections.abc.Sequence):
   1503     if all(isinstance(x_, np.dtype) for x_ in param):

ValueError: Type of the default value type str is not a numpy ndarray

In [5]: 
