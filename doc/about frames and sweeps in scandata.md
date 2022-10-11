
The data components in ScanData, by decreasing importance:

Primary (independent) data
1. scans(*)
2. scene(*)
3. electrophysiology

(*) Depending on the experiment, one of these is the 'master' data. The heuristic
here is that 'scans' are the 'master' data, whenever they exist. In their absence,
'scene' becomes the master data. Regardless, a 'master' data always exists.

Compare a line scan experiment to a time- or Z-series experiment. 

In the former, the 'scans' (which contain the line scan data) are the primary 
data of interest (hence, 'master' data) and the 'scene' may be absent altogether.
When present the 'scene' is relevant for the contextualization of the line scan 
data in the field of view, by providing the reference for the region of interest 
or scanning line where the line scan data was acquired.

In the latter, the 'scene' contains the sequence of 2D image frames acquired 
over time (time series) or over several focal depths (Z series). There are no
line scans here ('scans' is empty) and therefore, the primary data of interest
('master' data) is the 'scene'.

'electrophysiology' may be absent in both.

The 'scans', 'scene' and electrophysiology are considered 'independent' of each
other, in the sense that:
(a) they  may be acquired independently (e.g. separate hardware or acording to 
the capabilities/configuration of the acquisition software), and 

(b) the presence of electrophysiology data is NOT predicated on whether the master
data is the 'scans' or the 'scene.

In a properly designed and executed experiment each frame in the 'mastar' image
data corresponds to one frame in electrophysiology. For generality we assume 
this is not necessarily the case.

Furthermore, when both 'scans' and 'scene' data are present (and the 'scans'
data is implicitly, the 'master'), in a 'proper' experiment the 'scene' has either:

a) a single frame (which contextualizes ALL the frames in the 'scans')
b) as many frames as the 'scans' (with each 'scene' frame providing context for
the corresponding frame in 'scans' master data)

Again, for generality, we assume this is not necessarily the case.

Secondary (derived data; '<-' indicates which primary data they are derived from):
1. scansBlock       <- scans
2. scansProfiles    <- scans
3. sceneBlock       <- scene
4. sceneProfiles    <- scene

Since this data is derived from primary data components, it will have as many
frames as the primary data domponent that it has been derived from.


Auxiliary data (these need not be present, but when they do exist in the ScanData
object they relate as indicated by '<->'):

1. triggerProtocols <-> electrophysiology AND master data
2. analysisUnits    <-> master data AND electrophysiology

Both of these require frame/sweep 'normalization' i.e., augmenting the corresponding
primary data so that they contain the same number of frames (master data) and
sweeps (electrophysiology).

Ideally:
--------
* A ScanData object for a line scan experiment will have the same number of 
    frames and sweeps in all its image primary data, or a single frame in 'scene'
    data (with the 'scans' data being the 'master').

* If a ScanData object also contains electrophysiology, this will have the same
    number of sweeps as the number of frames in the master data (which is either
    the 'scans', for line scan experiments, or 'scene' for time- and Z-series
    experiments)
    
For generality, ScanData object manages "virtual frames", corresponding to the
maximum number of frames in the primary data. 

This is the basis for the following frame/sweep heuristic:

In the most trivial case only the 'master' data exists and there is a biunivocal
relation between virtual frames and the master data frames: a virtual frame 'k'
points to a real frame 'k' in the master data.

Whenever a primary (non-master) data exists, one of the following cases may
occur:

1) the non-master primary data has as many frames as the master data

2) the non-master primary data has one frame (or sweep) - this is considered to
apply to each and every frame of the master data (hence the virtual frame 'k' 
points to the same frame index 0 in the non-master data)

3) the non-master primary data has fewer frames than master data, but more than 
one frame -> some frames in the master data are semantically linked (point to)
the same non-primary data => use a frame lookup

4) the non-master primary data has more frames than master data; some of the 
frames in the non-master primary data will be skipped (i.e. are not semantically
linked to any of the master primary data frames) => use a frame lookup.

The frame lookup - a dict with int keys (virtual frame index) mapped to a dict with
fields: 'scans', 'scene', 'ephys', as necessary



    
