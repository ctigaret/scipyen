# # 1) select blocks and concatenate them for eack PathwayEpisode
# test_baseline = neoutils.concatenate_blocks(base_0001, base_0002, base_0003, base_0004, base_0005, base_0008, 
#                                             segments=[0], 
#                                             analogsignals = ["Im_prim_0", "Vm_sec_0", "Stim_0"])
# test_chase = neoutils.concatenate_blocks(chase_0000, chase_0001, chase_0002, chase_0003, chase_0004, chase_0005, chase_0006, chase_0007, chase_0008, chase_0009, chase_0010, chase_0011, chase_0012, chase_0013, chase_0014, chase_0015, chase_0016, chase_0017, chase_0018, chase_0019, chase_0020, chase_0021, chase_0022, chase_0023, chase_0024, chase_0025, chase_0026, chase_0027, chase_0028, chase_0029, chase_0030, chase_0031, chase_0032, chase_0033, chase_0034, chase_0035, chase_0036, chase_0037, chase_0038, chase_0039, chase_0040, chase_0041, chase_0042, chase_0043, chase_0044, chase_0045, 
#                                          segments=[0], 
#                                          analogsignals=["Im_prim_0", "Vm_sec_0", "Stim_0"])
# control_baseline = neoutils.concatenate_blocks(base_0001, base_0002, base_0003, base_0004, base_0005, base_0008, 
#                                                segments=[1], analogsignals = ["Im_prim_0", "Vm_sec_0", "Stim_1"])
# control_chase = neoutils.concatenate_blocks(chase_0000, chase_0001, chase_0002, chase_0003, chase_0004, chase_0005, chase_0006, chase_0007, chase_0008, chase_0009, chase_0010, chase_0011, chase_0012, chase_0013, chase_0014, chase_0015, chase_0016, chase_0017, chase_0018, chase_0019, chase_0020, chase_0021, chase_0022, chase_0023, chase_0024, chase_0025, chase_0026, chase_0027, chase_0028, chase_0029, chase_0030, chase_0031, chase_0032, chase_0033, chase_0034, chase_0035, chase_0036, chase_0037, chase_0038, chase_0039, chase_0040, chase_0041, chase_0042, chase_0043, chase_0044, chase_0045, 
#                                             segments=[1], analogsignals=["Im_prim_0", "Vm_sec_0", "Stim_1"])
# 
# # for s in test_baseline.segments:
# #     print(s.rec_datetime)
# # for s in test_chase.segments:
# #     print(s.rec_datetime)
# 
# # get the rec_datetime for first segments in the new blocks:
# 
# # test_baseline_begin = test_baseline.segments[0].rec_datetime
# # test_baseline_end = test_baseline.segments[-1].rec_datetime
# # test_baseline_nsegments = len(test_baseline.segments)
# # test_baseline_beginFrame = 0
# # test_baseline_endFrame = len(test_baseline.segments)-1
# # 
# # test_chase_begin = test_chase.segments[0].rec_datetime
# # test_chase_end = test_chase.segments[-1].rec_datetime
# # test_chase_nsegments = len(test_chase.segments)
# # test_chase_beginFrame = 0
# # test_chase_endFrame = len(test_chase.segments)-1
# 
# 
# 
# # make episodes, sort, then update their beginFrame & endFrame considering
# # the blocks will be further concatenated
# 
# test_baseline_episode = ltp.PathwayEpisode("Baseline", response="Im_prim_0", 
#                                            analogCommand="Vm_sec_0", digitalCommand="Stim_0", 
#                                            begin = test_baseline.segments[0].rec_datetime, 
#                                            end=test_baseline.segments[-1].rec_datetime,
#                                            beginFrame=0, 
#                                            endFrame = len(test_baseline.segments)-1)
# 
# 
# 
# test_chase_episode = ltp.PathwayEpisode("Chase", response="Im_prim_0", 
#                                            analogCommand="Vm_sec_0", digitalCommand="Stim_0", 
#                                            begin = test_chase.segments[0].rec_datetime, 
#                                            end=test_chase.segments[-1].rec_datetime,
#                                            beginFrame=0, 
#                                            endFrame = len(test_chase.segments)-1)
# 
# 
# nPathways = 2
# pathwaySweepNdx = [0,1]
# pathwayResponse = ["Im_prim_0", "Im_prim_0"]
# pathwayAnalogCommand = ["Vm_sec_0", "Vm_sec_0"]
# pathwayDigitalCommand = ["Stim_0", "Stim_1"]
# 
# nEpisodes = 2
# 
# # this list MUST be given in the SAME ORDER as that of the lists in the 
# # episodeBlocks, below
# episodeNames = ["Baseline", "Chase"]
# 
# # list of lists of episode-specific blocks
# episodeBlocks = [[base_0001, base_0002, base_0003, base_0004, base_0005, base_0008], 
#                  [chase_0000, chase_0001, chase_0002, chase_0003, chase_0004, chase_0005,
#                   chase_0006, chase_0007, chase_0008, chase_0009, chase_0010, chase_0011, 
#                   chase_0012, chase_0013, chase_0014, chase_0015, chase_0016, chase_0017, 
#                   chase_0018, chase_0019, chase_0020, chase_0021, chase_0022, chase_0023, 
#                   chase_0024, chase_0025, chase_0026, chase_0027, chase_0028, chase_0029, 
#                   chase_0030, chase_0031, chase_0032, chase_0033, chase_0034, chase_0035, 
#                   chase_0036, chase_0037, chase_0038, chase_0039, chase_0040, chase_0041, 
#                   chase_0042, chase_0043, chase_0044, chase_0045]]
#                  
# # now, sort the blocks in each list according to the rec_datetime if the blocks
# 
# for elist in episodeBlocks:
#     elist.sort(key = lambda x: x.rec_datetime)
#                  
# # 2 x 2 => four intermediate blocks - 
# # for each pathway create two pathwayepisodes using the corresponding
# # intermediate block, sort according to their 1st segment rec_datetime
# # then use the sorted list to concatenate into one full neo.Block per pathway
# # - rememeber to update the pathwayepisode's beginFrame and endFrame attributes.
# #
# # you may NOT need the intermediate blocks, just use the block lists above
# # 
# # create initial sorting index:
# ndx = list(range(nPathways))
# 
# # create the final sorting index that will be used sort the lists of episode block lists according to the rec_datetime of the
# #   first block in each list → creates a sorted sorting index
# #   
# # epis = reversed(test_baseline_episode, test_chase_episode)
# # epis = reversed((test_baseline_episode, test_chase_episode))
# # epis
# # sortedndx = sorted(ndx, key = lambda x: epis[x].begin)
# # epis = tuple(reversed(test_baseline_episode, test_chase_episode))
# # epis = tuple(reversed((test_baseline_episode, test_chase_episode)))
# # epis
# # sortedndx = sorted(ndx, key = lambda x: epis[x].begin)
# # sortedndx
# # sortedepis = list(map(lambda x: epis[x], sortedndx))
# # sortedepis
# # 

# # ------------
# # The idea is to generate a SynapticPathway with at least one PathwayEpisode,
# # given a list of source neo.Blocks (the 'trials')
# #
# # We can also use a dict to specify each pathway, in a list:
# #
# pathwaysDicts = list()
# 
# # for each pathway 
# pathwayDict = {}
# pathwayDict["index"] = 0    # a single int - the index of the pathway (>=0) in 
#                             # the experiment
# pathwayDict["segments"] = 0 # usually, a single int - then index of the Segment 
#                             # (a.k.a sweep) in the source blocks, containing the
#                             # data for this pathway
# # ATTENTION: this will be IGNORED during conditioning episodes where a plasticity
# # induction protocol may be applied repeatedly to the same pathway (i.e.,
# # involving more than one sweep)
# # NOTE: conditioning is applied to the "test" pathway; however this may involve
# # stimulation of additional pathways (e.g. to a 'weak' pathway, to test for
# # 'associativity' between pathways). In this case, the pathway data is present 
# # in all sweeps (the sweeps are NOT pathway-specific, as they contain information
# # pertaining simultaneously to more than one pathway.
#                             
# # NOTE: these mappings are COMMON for all source blocks
# pathwayDict["response"] = "Im_prim_0"       # str (signal name) or int (signal index)
# pathwayDict["analogCommand"] = "Vm_sec_0"   # str (signal name) or int (signal index)
# pathwayDict["digitalCommand"] = "Stim_0"    # str (signal name) or int (signal index)
# pathwayDict["pathwayType"] = ltp.PathwayType.Test # or ltp.PathwayType.Control, etc
# pathwayDict["name"] = "Test"                # str = some relevant name
# 
# 
# # each pathway has at least an episode - specified by another dict, collected in
# # a list
# pathwayDict["episodes"] = [] # list of episodes, prototype is episodeDict, below:
# 
# episodeDict = {}
# episodeDict["name"] = "Baseline"    # str =  some relevant name
# episodeDict["source"] = []          # list of neo.Blocks, ordered by rec_datetime
# episodeDict["pathways"] = []
# episodeDict["xtalk"] = []                   # list of unique int indices >= 0
#                                             # these are pathway indices (see above)
#                                             # and their order indicates
#                                             # the order in which the pathways 
#                                             # have been stimulated alternatively
#                                             # during a single paired-pulse stimulation
#                                             # see NOTE below
#                                             
# # NOTE: for a cross-talk, the pathwayType must be PathwayType.CrossTalk
# # and the 'order' key should be a sequence of pathway indices in the order they
# # were stimulated. The "xtalk" key is ignored for any other pathwayType value.
# #
# # A cross-talk pathway is a virtual pathway, where the possible synaptic overlap
# # between two putative 'real' pathways is tested using paired-pulse stimulation.
# #
# # This relies on a form of short-term plasticity seen with paired-pulse 
# # stimulation, when a pair of stimuli are delivered to the same pathway at a
# # short (20-30 ms) interval to evoke distinct synaptic responses in rapid succession.
# # In these conditions, the second synaptic response may be larger or smaller than 
# # the first, indicating respectively, paired-pulse 'facilitation' or 'depression'.
# #
# # Assuming that SINGLE stimuli evoke responses with the same amplitude in each 
# # pathway, then the absence of paired-pulse facilitation or depression when each
# # stimulus in a paired-pulse stimulation is delivered to alternative pathways 
# # indicates that the two pathways are independent (i.e., have no synaptic overlap).
# #
# # 
# 
# # NOTE: episodes in the pathwayDict["episodes"] list will be ordered by the
# # rec_datetime attribute of the first block in the episodeDict["source"] list; 
# # so, make sure you've assigned their names in a meaningful way (e.g., you typically
# # would avoid an episode named 'Baseline' to have been recorded AFTER an episode 
# # named "Chase", etc)
# 
# #


Constructing a SynapticPathway:
    
    a) from a concatenated new.Block and a Schedule
    • requires: 
        ∘ response signal(s) : GeneralIndexType
            - may be different per episode
    • optional:
        ∘ analog command signal(s): GeneralIndexType
        ∘ digital command signal(s): GeneralIndexType
        ∘ protocol - ?
            ⋆ TriggerProtocol (trigger events & timing)
            ⋆ CommandProtocol (i.e., command waveforms & timing)
    
Pseudo-code for parsing the protocol from an ABF:
    abf = getABF(neo Block object) ← inly works with neo Blocs created by reading
        and ABF file; will FAIL for synthetic neo.Blocks (even if these were 
        created through concatenation of ABF file-generated neo Blocks)
    
    Useful info:
        abf.sweepCount → the number of sweeps - corresponds to the number of 
            neo.Segment objects in the neo.Block
            
        
        abf.channelCount → the number of channels - corresponds to the number of
            neo.AnalogSignals objects in the segments (which must be the same in 
            all segments)
            
        abf.sweepNumber → current sweep "set" by setSweep
        
        abf.setSweep(sweep:int, channel:Optional[int] = 0)
        
        e.g.:
            
        abf.setSweep(12, absoluteTime=False); plt.clf(); plt.plot(abf.sweepX, abf.sweepY)

        compare with:
    
        abf.setSweep(12, absoluteTime=False); plt.clf(); plt.plot(abf.sweepX, abf.sweepY)
