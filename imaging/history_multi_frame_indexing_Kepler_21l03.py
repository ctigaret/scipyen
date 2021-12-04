Problem:

a scandata object has n scan frames, m scene frames, p elphys segments

there obviously is no bi-univocal relationship between frames

Q1: how many virtual 'frames' in data?
A:  as many as the 'driver' data has

Q2: which is the 'driver' data?
A: which ever is not empty, but scans has priority:
    scans if not empty, else scene.
    
Q3: what about elphys?
A: although elphys is a 'primary' data child, it is not central to a scandata 
object - this may contain only imaging data
    
Q4: how many cases are there?
A: two: scans is the driver, or scene is the driver

Q5: what happens when scans has more frames than scene?
A: assume 1-2-1 frame correspondence between scans and scene until scene frames
    are exhausted
    
Q5.1: and what happens to the scans 'extra' frames?
A: either map them to None, or if you want, map them to the last frame in scene, 
    which is probably better and more logical

Q5.2: why? 
A: because mapping to None begs for index checking later - more if ... else clauses

Q5.3: but is it correct to assume that the last frame in the scene is related to
    all the 'extra' frames in the scans?
A: no. but in practice, an acquistion system usually does NOT record a scene 
    raster scan for every linescan frame in scans - it would take too much time 
    to do so and introduce underisable delays: when the linescan acquisition is
    automatized (e.g. triggered by an external TTL , say from electrophysiology)
    then acquiring a scene frame just before the linescan would significantly 
    delay the linescan acquisition potentially causing you to 'miss' the event
    you are trying to record
    
    admittedly, when the event itself is triggered by an electrophysiology 
    stimulus (e.g a synaptic event, action potential) or by photo-activation,
    the timing of the triggers MAY be adapted to account for the delay, such that
    the linescans acquisiton really begins WELL BEFORE the stimulus applicaton.
    
    This strategy would be even more cumbersome, because the delay needs to be
    calculated according to the size of the scene area relative to the linescan 
    trajectory, pixel dwell time of the laser, etc. and may require adjustment
    to the trigger protocols every time the raster scan parameter are changed -
    quite counterproductive...
    
    
    And even if the above could be done automatically, acquiring a scene frame
    before every linescan and would increase the specimen exposure to light 
    excitation (in fluorescence microscopy this is a REAL BAD THING).
    
    For all these reasons, when a linescan sequence or cycle is acquired, there
    really is only one scene frame associated with it. This is what ScanImage does...

Q5.4: but PrairieView stores a reference (scene) 'frame' for each scans frame?
A: yes, but this is (unnecessary) data duplication (and frankly, a waste of disk
    storage space), because it is clear that all the frames in the 'reference'
    cycle contain the exact same pixel data.
    
    Therefore the assumption in A(Q5.3) is implicit: for each cycle of linescans
    there is only ONE scene frame
    
Q5.5: so the problem stated above really is confected, since one needs a single 
    scene frame for several scans frames?
A: no. you may find desirable to concatenate several linescan cycles in one
    data object to analyse them together (e.g average repetitions of the same
    stimulus protocols, etc); if, between cycles, small adjustments are made to 
    the field of view and / or focal plane in order to compensate for small 
    drifts, then the 'scene' reference is really useful to keep your bearings... 
    even more so when the linescan trajectory has also been adjusted between 
    cycles.

    so if you take N consecutive cycles of 3 linescans each you end up with 
    N x 3 linescans 'frames', but only with N scene frames, in reality
    
    if you then concatenate these into one data object per experiment (which as
    mentioned above, is not at all unreasonable) you will have to specify the 
    scans-scene frame correspondence in some way.
    
    What PrairieView does is to alleviate somewhat this problem, by supplying
    one scene frame for each scan frame (even though the scene frames in a cycle
    convey the same information). With ScanImage, you really are on your own...
    
    furthermore, you may later decide that some linescan frames are an acquisition
    'failure' i.e., something freaky has happened during the linescan - not
    serious enough to terminate the experiment but enough to mess up the data 
    in that frame; in this case you may need to delete that particular frame 
    otherwise its analysis would give garbage that contaminates the entire 
    experiment.
    
    again you will need to specify some correspondence between scans frames and
    scene frames
    
Q5.6: OK, so what to do if there are more scans frames than scene frames?
A: see A(Q5.1) and A(Q5.2)

Q5.7: this works for a single linscan cycle of x frames with 1 scene frame, but
what about concatenated data?
A: you have the option to replicate the scene frames for each cycle BEFORE
    concatenating (with the associated extra disk space / memory use) OR
    generate a FrameIndexLookup
    
Q5.8:OK so how would this work?
A. asuming scans has N frames and scene only has one frame:
        map every frame in scans to the only scene frame
        
Q5.9: how to do that?
A. use FrameIndexLookup with MultiFrameIndex (ScanDataFrameIndex):
    {k: MFI(scans: k, scene: 0)} for k in range(scans frames)
    
    I agree it is probably better to use a numpy recarray instead of FLI & MFIs:
    
    indices = np.full((maxFrames, 3), np.nan)
    
    
    NOTE: see also np.sctypeDict, pd.Int64DType
    
    We need pandas Int64Dtype because they offer a NULL integer type equivalent
    to numpy NaN or math NaN (both ich the latter are floats)

    field_names = ("scans", "scene", "electrophysiology")
    idxdtype = np.dtype([(("Component", 'name'), f"U{max(len(s) for s in field_names)}"), (('Frame', 'index'), pd.Int64Dtype())])
    
    
    
create indexing tuples:
    indexing_tuples = tuple(tuple(scan, 0, np.nan) for scan in range(scans frames))
    
then create a structured array with your indexing needs:
    indexing_array = np.array([i for i in zip(field_names, indexing_tuple)])
    





Q6: What happens when scans has fewer frames than scene?
A: obviously, there are redundant frame in scene;

Q6.1: which frame in the scene is redundant?
A: by default all scene frames with index >= number of scans frames

Q6.2: how can this be made more specific?
A: by specifying frame relationships in a FrameIndexLookup which maps
scans frames to the relevant scene frames:
    {k: scans, scene, elphys} for k in range(number of frames in scans)
    
Q6.3: but this means one has to specify a relationship for each frame in scans - too tedious!
A: True

Q6.4: is there an alternative strategy?
A: Yes. let the data with the most frames be the 'driver'

Q6.5: so what happens then?
A: when scene has more frames than scans, then scene becomes the driver

Q6.6: and?
A: specify a relatinship only for those scene frames than correspond to a frame in scans:
    {k: scans, scene, elphys} for k in slelected scene frames
    
Q6.7: and if no relationship is specified?
A: then each scene frame corresponds in order to each scans frame until
    scans frames are exhausted
    
Q6.8: and then?
A: for scene frames with index >= number of scans frames return None or if you like 
return the last scans frame





    


# load data first

newax = vigra.AxisInfo("t1", vigra.AxisType.Time)
scene0 = vigrautils.concatenateImages(base_000_Cycle00001_Ch1Source, base_000_Cycle00002_Ch1Source, base_000_Cycle00003_Ch1Source, axis = newax)
scene1 = vigrautils.concatenateImages(base_000_Cycle00001_Ch2Source, base_000_Cycle00002_Ch2Source, base_000_Cycle00003_Ch2Source, axis = newax)
scans0 = vigrautils.concatenateImages(base_000_Cycle00001_CurrentSettings_Ch1_000001, base_000_Cycle00002_CurrentSettings_Ch1_000001, base_000_Cycle00003_CurrentSettings_Ch1_000001, axis = newax)
scans1 = vigrautils.concatenateImages(base_000_Cycle00001_CurrentSettings_Ch2_000001, base_000_Cycle00002_CurrentSettings_Ch2_000001, base_000_Cycle00003_CurrentSettings_Ch2_000001, axis = newax)
elphys = neoutils.concatenate_blocks(base_0000, base_0001, base_0002)
elphys0 = neoutils.concatenate_blocks(base_0000, base_0001)
elphys1 = neoutils.concatenate_blocks(base_0000, base_0002)
elphys2 = neoutils.concatenate_blocks(base_0001, base_0002)
sceF = vigrautils.nFrames(scene0)
scaF = vigrautils.nFrames(scans0)
ephF = len(elphys.segments) 
ephF0 = len(elphys0.segments) # short with segs 0 and 1
ephF1 = len(elphys1.segments) # short with segs 0 and 2
ephF2 = len(elphys2.segments) # short with segs 1 and 2
frs = [scaF, sceF, ephF]
frs0 = [scaF, sceF, ephF0]
frs1 = [scaF, sceF, ephF1] # thse last two are the same as frs0 EXCEPT 
frs2 = [scaF, sceF, ephF2] # that the segments in elphys1/2 are different!
maxF = max(frs) # always 3 in these examples!
dnames = ("scans", "scene", "electrophysiology")
smaxlen = max(len(s) for s in dnames)
mydtype = np.dtype([('name', f"U{smaxlen}"), ('nFrames', int)])
dframes = np.array([i for i in zip(dnames, frs)], dtype=mydtype).view(np.recarray)
dframes0 = np.array([i for i in zip(dnames, frs0)], dtype=mydtype).view(np.recarray)
dframes1 = np.array([i for i in zip(dnames, frs1)], dtype=mydtype).view(np.recarray)
dframes2 = np.array([i for i in zip(dnames, frs2)], dtype=mydtype).view(np.recarray)
shorts = np.where(dframes.nFrames < maxF)[0]
shorts0 = np.where(dframes0.nFrames < maxF)[0]
shorts1 = np.where(dframes1.nFrames < maxF)[0]
shorts2 = np.where(dframes2.nFrames < maxF)[0]
dframes0[shorts].name # --> array(['electrophysiology'], dtype='<U17')
dframes0[shorts].nFrames # --> array([2])

from core.multiframeindex import FrameIndexLookup
from imaging.scandata import ScanDataFrameIndex
from core import utilities

# note: use this also as a potential default for FrameIndexLookup.__getitem__
# might need to pass max frames for each data component if needed
# (standing in for scaF, sceF, ephF, and maxF, respectively)
df = dict((k,ScanDataFrameIndex(utilities.nth((s for s in range(scaF)),k,-1), 
                                utilities.nth((s for s in range(sceF)),k,-1), 
                                utilities.nth((s for s in range(ephF)),k,-1))) for k in range(maxF))

# default for short0
df0 = dict((k,ScanDataFrameIndex(utilities.nth((s for s in range(scaF)),k,-1), 
                                utilities.nth((s for s in range(sceF)),k,-1), 
                                utilities.nth((s for s in range(ephF0)),k,-1))) for k in range(maxF))

df1 = dict((k,ScanDataFrameIndex(utilities.nth((s for s in range(scaF)),k,-1), 
                                utilities.nth((s for s in range(sceF)),k,-1), 
                                utilities.nth((s for s in range(ephF1)),k,-1))) for k in range(maxF))

df2 = dict((k,ScanDataFrameIndex(utilities.nth((s for s in range(scaF)),k,-1), 
                                utilities.nth((s for s in range(sceF)),k,-1), 
                                utilities.nth((s for s in range(ephF2)),k,-1))) for k in range(maxF))

# df0
# -->
# {0: ScanDataFrameIndex electrophysiology:0 scans:0 scene:0,
#  1: ScanDataFrameIndex electrophysiology:1 scans:1 scene:1,
#  2: ScanDataFrameIndex electrophysiology:-1 scans:2 scene:2}

# so then frl[3] should throw index error !
# but 0 and 1 are mapped 1-2-1 so do we should NOT need a ScanDataFrameIndex
# for those!
# ideally, a FrameIndexLookup would contain only those indices where
# there is a shortfall?
#
# so by default FrameIndexLookup.__getitem__ should call nth(...) given
# _ANY_ index, such that it generates a data frame (sub) index dynamically
# EXCEPT for specific shortfalls where we specifically want to avoid this behaviour
# (do not want to have the lastframe in the short data component but a more 
# specific one given the data-wide frame index 'k')
# 

scd_for_ephF1 = ScanDataFrameIndex(1,1,0)
frl_for_ephF1 = FrameIndexLookup({1:scd_for_ephF1}, 
                                 scans_nFrames=scaF, 
                                 scene_nFrames = sceF, 
                                 electrophysiology_nFrames = ephF1)
