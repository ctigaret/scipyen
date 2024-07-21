# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

from abc import ABC
class ElectrophysiologyProtocol(ABC):
    """Abstract base class for electrophysiology data acquisition protocols
    
    """
    def __init__(self, **kwargs):
        pass
        # self._nADCChannels_ = kwargs.get("nADCChannels",0)
        # self._nDACChannels_ = kwargs.get("nDACChannels",0)
        # self._nDigitalOutputs_ = kwargs.get("nDigitalOutputs", 0)
        # self._nTotalDigitalOutputs_ = kwargs.get("nTotalDigitalOutputs",0)
        # self._activeDACChannel_= kwargs.get("activeDACChannel", 0)
        # self._hasAltDacOutState_ = kwargs.get("altDACOutState",False)
        
    # TODO 2023-10-15 21:10:06 on backburner for now.
    # write subclasses for:
    # • CED Signal protocols ("configuration")
    # • other ephys acquisition software (CED Spike, ephus?)
    
#     def __init__(self):
#         # possible values for self._data_source_:
#         # "Axon", "CEDSignal", "CEDSpike", "Ephus", "NA", "unknown"
#         # default: "unknown"
#         self._data_source_ = "unknown"  
#         self._acquisition_protocol_ = dict()
#         self._acquisition_protocol_["trigger_protocol"] = TriggerProtocol()
#         self._averaged_runs_ = False
#         self._alternative_DAC_command_output_ = False
#         self._alternative_digital_outputs_ = False
#     
#     def parse_data(self, data:neo.Block, metadata:dict=None):
#         if hasattr(data, "annotations"):
#             self._data_source_ = data.annotations.get("software", "unknown")
#             if self._data_source_ == "Axon":
#                 self._parse_axon_data_(data, metadata)
#                 
#             else:
#                 # TODO 2020-02-20 11:32:16
#                 # parse CEDSignal, CEDSpike, EPhus, unknown
#                 pass
#             
#     def _parse_axon_data_(self, data:neo.Block, metadata:dict=None):
#         data_protocol = data.annotations.get("protocol", None)
#         
#         self._averaged_runs_ = data_protocol.get("lRunsPerTrial",1) > 1
#         self._n_sweeps_ = data_protocol.get("lEpisodesPerRun",1)
#         self._alternative_digital_outputs_ = data_protocol.get("nAlternativeDigitalOutputState", 0) == 1
#         self._alternative_DAC_command_output_ = data_protocol.get("nAlternativeDACOutputState", 0) == 1
#         
#     def _parse_ced_data_(self, data:object):
#         pass
