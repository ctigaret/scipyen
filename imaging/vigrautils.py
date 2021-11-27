import typing
from functools import singledispatch
import vigra
import numpy as np
import quantities as pq
from .axiscalibration import (AxesCalibration, 
                              AxisCalibrationData,
                              ChannelCalibrationData,)
from imaging import axisutils
from imaging.axisutils import STANDARD_AXIS_TAGS_KEYS

def getAxesLayout(img:vigra.VigraArray, 
                   userFrameAxis:typing.Optional[typing.Union[str, vigra.AxisInfo, int, 
                                                              typing.Sequence[typing.Union[str, vigra.AxisInfo, int]]]]=None,
                   timeVertical:bool = True,
                   ) -> typing.Tuple[int, typing.Optional[typing.Union[vigra.AxisInfo, typing.List[vigra.AxisInfo]]], vigra.AxisInfo, vigra.AxisInfo, vigra.AxisInfo]:
    """Proposes a layout for frame-by-frame display and analysis of a VigraArray.
    
    Based on user-soecified hints, suggests which array axes may be used:
        * to slice the array into meaningful 2D array views (data 'frames')
        * for the definition of a frame's width and height
        
    and proposes the number of frames in the array (array size along the 'frames'
    axis).
        
    Parameters:
    ===========
    img: N-dimensional VigraArray
    
    userFrameAxis: str, int, AxisInfo, or tuple/list of any of these
        This hints the possible axis or set of axes that may be used for slicing
        the array into meaningful 2D views ('frames')
        
    timeVertical: bool, default is True
        Whe True, the time dimension (when present) is to be shown vertically
    
    Returns:
    ========
    A tuple with the following elements:
     
    nFrames:int = the number of frames along the proposed "frame" axis
    
    All the others are vigra.AxisInfo objects, None, or tuple of vigra.AxisInfo
     
    horizontalAxisInfo:vigra.AxisInfo = the axis proposed for the frame 'width'.
    
        BY CONVENTION this is the first non-channel axis (usually, the 1st array
        dimension), which is also the innermost non-channel axis given by 
        img.innerNonChannelIndex property
        
    verticalAxisInfo:vigra.AxisInfo = the axis proposed for the frame 'height'.
    
    BY CONVENTION this is the 2nd non-channel axis (usually, the 2nd dimension)
        
    channelAxisInfo:vigra.AxisInfo or None = the channel axis
    
        This is either the AxisInfo with type flags of Channels, when it exists
        in img 'axistags' property, or None.
        
        BY CONVENTION this is the axis of the highest dimension of the array 
        (possibly absent in 2D arrays, and missing in 1D arrays, where the data
        inherently represents a single 'channel').
        
        In VigraArray objects, the channel axis represents channels in a 'color'
        space (RGB, Luv, etc.) for the so-called 'multi-channel' or 'multi-band'
        images - this relates to the data type of the pixels. 
        
        NOTE: In Scipyen, a 'channel' can also represent a distinct recording
        channel of data from the same source (e.g. a fluorescence channel, DIC, 
        etc.), or the real or imaginary part of complex numbers (e.g., the
        result of a Fourier transform).
        
        BY CONVENTION, a single data recording channel is interpreted as being
        stored in a 'grayscale' image (a.k.a, a 'single-channel' or 'single-band'
        image or volume). 
        
        In Scipyen, data containing several 'data channels' defined as above 
        is stored in a sequence of grayscale VigraArray with the same shape and 
        similar axis tags. For display purposes, there is nothing to prevent 
        'merging' these channels into a single VigraArray, although it does not 
        always make good sense to do so (especially whenn there are more than
        four distinct data channels).
        
    frameAxisInfo:vigra.AxisInfo or None
    
        When given, this is the AxisInfo along which the array can be 'sliced'
        in 'frames' defined for the purpose of display and/or analysis.
        
        BY CONVENTION for 3D arrays this is the 3rd non-channel axis (usually, 
        the 3rd dimension); for arrays with more than 4 dimensions and without a
        channels axis this is a tuple of axes (in increasing order).
        
     
     NOTE the last two values need not be along the first and second axis, as this
     depends on which axis is the channel axis (if it exists); by default, in vigra 
     library the channel axis is typically the outermost one, but that depends on
     the internal storage order (order of axes) for the pixel data in the array
    
    Code logic:
    ==========
    
    A "frame" is a 2D slice view of a VigraArray. Arrays can be sliced along 
    any axis, including a channel axis. This function attempts to "guess"
    a reasonable axis along which the array can be sliced into meaningful 2D 
    frames.
    
    NOTE: 2018-09-14 23:14:38
    give up on "separateChannels" thing -- useless; for arrays with > 4 dimensions
    we "flatten" the outermost nonchannel axes, thus setting the frames on the first 
    two axes
    
    """
    if not isinstance(img, vigra.VigraArray):
        raise TypeError("Expecting a VigraArray; got %s instead" % (type(img).__name__))
    
    if not hasattr(img, "axistags"):
        raise TypeError("'img' does not contain axis information")
    
    if img.ndim == 0:
        raise TypeError("Expecting a VigraArray with at least 1 dimension")
    
    #bring userFrameAxis to a common denominator: an AxisInfo object, or None
    if isinstance(userFrameAxis, (vigra.AxisInfo, str)):
        if userFrameAxis not in img.axistags:
            # CAUTION equality testing for AxisInfo objects ONLY takes into
            # account the axis typeFlags and key
            raise ValueError("Axis %s not found in image" % userFrameAxis.key)
        
        if isinstance(userFrameAxis, str):
            userFrameAxis = img.axistags[userFrameAxis]
            
        if userFrameAxis.typeFlags & vigra.AxisType.Channels:
            raise TypeError("Channels axes cannot be used as frame axes")
        
    elif isinstance(userFrameAxis, int):
        if userFrameAxis < 0 or userFrameAxis >= ndim:
            raise ValueError("Axis index expected to be in the semi-open interval [0 .. %d); got %d instead" % (img.ndim, userFrameAxis))
        
        userFrameAxis = img.axistags[userFrameAxis]
        
        if userFrameAxis.typeFlags & vigra.AxisType.Channels:
            raise TypeError("Channels axes cannot be used as frame axes")
        
    elif isinstance(userFrameAxis, (tuple, list)):
        if all([isinstance(ax, (vigra.AxisInfo, str, int)) for ax in userFrameAxis]):
            try:
                frax = tuple(img.axistags[ax] if isinstance(ax, str, int) else ax for ax in userFrameAxis)
                
            except Exception as e:
                raise RuntimeError("Invalid frame axis specified") from e
                
            userFrameAxis = frax
            
        else:
            raise TypeError("user frame axis sequence expected to contain vigra.AxisInfo objects, str or int elements")
        
        if any (ax.typeFlags & vigra.AxisType.Channels for ax in userFrameAxis):
            raise TypeError("Channels axes cannot be used as frame axes")
        
    elif userFrameAxis is not None:
        #warnings.warn("Invalid user frame axes specification; will set it to None", RuntimeWarning)
        userFrameAxis = None
        
    xIndex = img.axistags.index("x")
    if xIndex == img.ndim:
        # try by axis typeflags
        spaceAxes = tuple(ax for ax in img.axistags if ax.typeflags & vigra.AxisType.Space)
    yIndex = img.axistags.index("y")
    zIndex = img.axistags.index("z")
    tIndex = img.axistags.index("t")
    cIndex = img.channelIndex
    
    frameAxisInfo       = None
    channelAxisInfo     = None
    horizontalAxisInfo  = None
    verticalAxisInfo    = None
    nFrames             = 0
    
    if img.ndim == 1:
        nFrames = 1

        if img.order == "C":
            verticalAxisInfo = img.axistags[0] # 'column' vector
            
        elif img.order  ==  "F":
            horizontalAxisInfo = img.axistags[0] # 'row' vector
            
        else: # "V"
            horizontalAxisInfo = img.axistags[0] # 'row' vector
        
    elif img.ndim == 2: # trivial case; the check above passed means that there is no channel axis
        # this has a 'virtual', singleton channel axis;
        #if userFrameAxis is not None:
            #warnings.warn("Ignoring userFrameAxis for a 2D array", RuntimeWarning)

        # NOTE: the interpretation of the axes is is dependent on the img 'order'
        # attribute; we use the axistags 'x' and 'y' or 't' to determine the 
        # horizontal ('x') and vertical ('y' or 't') dimensions; when neither of 
        # thesee axistags exist (their index equals img.ndim) we fallback on the 
        # generic heuristic of horizontal on 1st dimension and vertical on 2nd
        # 
        nFrames = 1
        
        horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim else \
                              imt.axistags["t"] if tIndex < img.ndim and timeVertical is False else img.axistags[0]
        
        verticalAxisInfo    = img.axistags["y"] if xIndex < img.ndim else \
                              img.axistags["t"] if tIndex < img.ndim and timeVertical is True else img.axistags[1]
        
        
    elif img.ndim == 3:
        if cIndex == img.ndim: # no channel axis:
            if userFrameAxis is None:
                # first try AxisInfo with key "z", or a third AxisInfo with typeFlags & Space,
                # then AxisInfo with key "t", or an axisInfo with typeFlags & Time
                if zIndex < img.ndim:
                    frameAxisInfo = img.axistags[zIndex]
                    
                else:
                    spaceAxes = [ax for ax in img.axistags if ax.typeFlags & Space]
                    if len(spaceAxes) > 2:
                        frameAxisInfo = spaceAxes[2] 
                        
                    else:
                        if tIndex < img.ndim:
                            frameAxisInfo = img.axistags[tIndex]
                            
                        else:
                            frameAxisInfo = img.axistags[-1] # fall back to choosing the outermost axis as frame axis
                    
            else: # user-specified frameAxis - just check we're OK with it
                if isinstance(userFrameAxis, (list, tuple)):
                    if len(userFrameAxis) == 0:
                        raise TypeError("userFrameAxis sequence is empty")
                    
                    if any([not isinstance(ax, vigra.AxisInfo) for ax in userFrameAxis]):
                        raise TypeError("user frame axis sequence must contain only vigra.AxisInfo objects")
                    
                    frameAxisInfo = userFrameAxis[0]
                    
                elif not isinstance(userFrameAxis, vigra.AxisInfo):
                    raise TypeError("user frame axis must be either None, a vigra.AxisInfo, or a sequence of AxisInfo objects; got %s instead" % type(userFrameAxis).__name__)

                    frameAxisInfo = userFrameAxis
                
            # skip frame axis for width and height
            availableAxes = tuple(ax for ax in img.axistags if ax != frameAxisInfo and ax.typeFlags & vigra.AxisType.Channels == 0)
            
            horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim and img.axistags["x"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is False else \
                                  availableAxes[0]
                              
            verticalAxisInfo    = img.axistags["y"] if xIndex < img.ndim and img.axistags["y"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is True else \
                                  availableAxes[1]
                
            nFrames = img.shape[img.axistags.index(frameAxisInfo.key)]
            
        else:
            # there is a channel axis therefore this is really a 2D data array
            # (even though, numerically it is represented by a 3D array);
            # hence it contains a single displayable frame
            channelAxisInfo = img.axistags[cIndex]
            
            #if userFrameAxis is not None:
                #warnings.warn("Ignoring userFrameAxis for a 3D array with channel axis (effectively a 2D image, possibly multi-band)", RuntimeWarning)
            
            nFrames = 1
            
            availableAxes = tuple(ax for ax in img.axistags if (ax.typeFlags & vigra.AxisType.Channels == 0))
            
            horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim and img.axistags["x"] in availableAxes else \
                                  imt.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is False else \
                                  availableAxes[0]
                              
            verticalAxisInfo    = img.axistags["y"] if xIndex < img.ndim and img.axistags["y"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is True else \
                                  availableAxes[1]
            
                
    elif img.ndim > 3:
        if cIndex == img.ndim:
            # no channel axis
                
            if userFrameAxis is None:
                spaceAxes = tuple(ax for ax in img.axistags if ax.typeFlags & Space)
                if len(spaceAxes) > 2:
                    putativeZaxes = tuple(ax for ax in spaceAxes if "z" in ax.key.lower())
                else:
                    putativeZaxes = tuple()
                    
                timeAxes  = tuple(ax for ax in img.axistags if ax.typeFlags & Time)
                
                framesAxisInfo = tuple(sorted(list(putativeZaxes + timeAxes),ley = lambda x: img.axistags.index(x)))
                
                # TODO 2021-11-27 22:08:30
                # figure out if there is an x, t, t1, ... or t, t1, t2, ... etc
                
                if len(frameAxisInfo) == 0:
                    # consider the first two axes as horiz/vert
                    frameAxisInfo = tuple(img.axistags[k] for k in range(2,img.ndim))
                
            else: # user-specified frame axes - must be a tuple for >3D
                if not isinstance(userFrameAxis, (list, tuple)):
                    raise TypeError("For arrays with more than three dimensions the frame axis must be a sequence of axis info objects")
                
                if any([not isinstance(ax, vigra.AxisInfo) for ax in userFrameAxis]):
                    raise TypeError("For arrays with more than three dimensions the frame axis must be a sequence of axis info objects")
                
                if len(userFrameAxis) != img.ndim-2:
                    raise TypeError(f"For a {img.ndim}-D array with no channel axis, the user frame axis sequence must contain {img.dim-2} AxisInfo objects; got {len(userFrameAxis)} instead")
                    
                frameAxisInfo = userFrameAxis
                
            availableAxes = tuple(ax for ax in img.axistags if ax not in frameAxisInfo and ax.typeFlags & vigra.AxisType.Channels == 0)
            
            horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim and img.axistags["x"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is False else \
                                  availableAxes[0]
            verticalAxisInfo    = img.axistags["y"] if xIndex < img.ndim and img.axistags["y"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is True else \
                                  availableAxes[1]
                              
        else:
            channelAxisInfo = img.axistags[cIndex]
            # there is a channel axis => an N-D array becomes an (N-1)-D data 'block'
            # with a channel axis
            nonChannelAxes = [ax for ax in img.axistags if (ax.typeFlags & vigra.AxisType.Channels == 0)]
            
            if userFrameAxis is None:
                # consider first two axes as horiz/vert
                frameAxisInfo = tuple(nonChannelAxes[k] for k in range(2, len(nonChannelAxes)))
                
            else:
                if isinstance(userFrameAxis, vigra.AxisInfo):
                    if img.ndim  > 4:
                        raise TypeError(f"For arrays with more than four dimensions useFrameAxis must be a sequence with at least {img.ndim-3} elements")
                    
                    userFrameAxis = [userFrameAxis]
                    
                elif isinstance(userFrameAxis, (list, tuple)):
                    if any([not isinstance(ax, vigra.AxisInfo) for ax in userFrameAxis]):
                        raise TypeError("user frame axis sequence must contain only axis info objects")
                    
                    if len(userFrameAxis) != img.ndim-3:
                        raise TypeError(f"For a {img.ndim}-D array with channel axis, the user frame axis sequence must contain {img.dim-3} AxisInfo objects; got {len(userFrameAxis)} instead")
                    
                frameAxisInfo = userFrameAxis

            availableAxes = [ax for ax in img.axistags if ax not in frameAxisInfo and ax.typeFlags & vigra.AxisType.Channels == 0]
            
            horizontalAxisInfo  = img.axistags["x"] if xIndex < img.ndim and img.axistags["x"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is False else \
                                  availableAxes[0]
            verticalAxisInfo    = img.axistags["y"] if xIndex < img.ndim and img.axistags["y"] in availableAxes else \
                                  img.axistags["t"] if tIndex < img.ndim and img.axistags["t"] in availableAxes and timeVertical is True else \
                                  availableAxes[1]
                              
            
        # NOTE:this is WRONG
        #nFrames = sum([img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo])
        
        # NOTE: 2021-11-27 21:55:14 
        # this is OK but we don't use this anymore; return a tuple of frames along
        # each of the frame axes info
        #nFrames = np.prod([img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo])
        nFrames = tuple(img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo)
            
    nFrames = tuple(img.shape[img.axistags.index(ax.key)] for ax in frameAxisInfo)
    
    if isinstance(frameAxisInfo, (tuple, list)) and len(frameAxisInfo) == 1:
        frameAxisInfo = frameAxisInfo[0]
        
    if isinstance(nFrames, (tuple, list)) and len(nFrames) == 1:
        nFrames = nFrames[0]
        
    
    return nFrames, horizontalAxisInfo, verticalAxisInfo, channelAxisInfo, frameAxisInfo

@singledispatch
def kernel2array(value:typing.Union[vigra.filters.Kernel1D, vigra.filters.Kernel2D],
                 compact:bool=True):
    """
    Generates a numpy array with coordinates and values for the kernel's samples
    Parameters
    ----------
    value: Kernel1D or 2D
    compact:bool, default is True
    
    Returns:
    -------
    for a 1D kernel of N samples:
        when compact is False:
            list [X, KRN] with:
                X: 1D numpy array with shape (N,) containing kernel coordinates
                    from kernel.left() to kernel.right()
                    ATTENTION:  THE ELEMENTS ARE NOT SAMPLE INDICES!
                
                KRN: 1D numpy array with shape (N,) containing the kernel sample values;
                
        when compact is True:
            2D numpy array with shape (N,2):
                column 0 : coordinates from kernel.left() to kernel.right()
                column 1 : kernel sample values
                
    for a 2D kernel (N x M samples):
        when compact is False:
            list[XY, KRN] with:
                XY: list [X, Y] of 2D numpy arrays with size (N,M) - these are
                    the meshgrid with the coordinates of kernel's samples, 
                    from kernel.lowerRight() to kernel.upperLeft()
                    
                KRN: 2D numy array with shape (N,M)
                
        when compact is True:
            3D numy array with shape (N,M,3) where
            column 0: meshgrid X coordinates
            column 1: meshgrid Y coordinates
            column 2: kernel sample values
            
                
    In either case, the kernel's centre is at the centre (in the middle) of the
    the coordinate array(s).
    
    NOTE: To reconstruct from a compact array ('kernel_array'):
    -----------------------------------------------------------
    
    Pseudo-code:
    if kernel_array.ndim == 2 => Kernel1D, else Kernel2D
    
    Kernedl1D case:
    
    k1d         = vigra.filters.Kernel1D()
    left        = int(kernel_array[ 0, 0])
    right       = int(kernel_array[-1, 0])
    contents    = kernel_array[:, 0]
    k1d.initExplicitly(left, right, contents)
    
    Kernel2D case:
    
    k2d         = vigra.filters.Kernel2D()
    upperLeft   = (int(kernel_array[-1, 1, 0]), int(kernel_array[-1, -1, 1]))
    lowerRight  = (int(kernel_array[ 0, 0, 0]), int(kernel_array[ 0,  0, 1]))
    contents    = kernel_array[:, :, 2]
    k2d.initExplicitly(upperLeft, lowerRight, contents)
                
    """
    raise NotImplementedError(f"{type(value).__name__} objects are not supported")
    #if isinstance(value, vigra.filters.Kernel1D):
        #return vK1D2array(value, compact)
    
    #elif isinstance(value, vigra.filters.Kernel2D):
        #return vK2D2array(value, compact)
    
@kernel2array.register(vigra.filters.Kernel1D)
def _(value, compact=False):
    """Returns a numpy.ndarray representation of a vigra.Kernel1D object
    Arguments: 
    "value" = vigra.Kernel1D object
    """
    x = np.atleast_1d(np.arange(value.left(), value.right()+1))
    y = np.array(list(value[t] for t in range(value.left(), value.right()+1)))
    
    if compact:
        return np.concatenate([x[:,np.newaxis], y[:,np.newaxis]], axis=1)
    
    return x, y

@kernel2array.register(vigra.filters.Kernel2D)
def _(value, compact=False):
    xx = np.linspace(value.lowerRight()[0], value.upperLeft()[0], value.width(), 
                     dtype=np.dtype(int))
    
    yy = np.linspace(value.lowerRight()[1], value.upperLeft()[1], value.height(),
                     dtype=np.dtype(int))
    
    x = np.meshgrid(xx,yy)
    
    y = np.full((value.height(), value.width()), np.nan)
    
    for kx, x_ in enumerate(xx): # from left to right
        for ky, y_ in enumerate(yy): # from top to bottom
            y[kx, ky] = value[x_, y_]
           
    if compact:
        return np.concatenate([x[0][:,:,np.newaxis], x[1][:,:,np.newaxis], y[:,:,np.newaxis]], axis=2)
            
    return x, y
    

def getCalibratedAxisSize(image, axis):
    """Returns a calibrated length for "axis" in "image" VigraArray, as a python Quantity
    
    If axisinfo is not calibrated (i.e. does not have a calibration string in its
    description attribute) then returns the size of the axis in pixel_unit.
    
    Parameters:
    ==========
    
    image: vigra.VigraArray
    
    axis: vigra.AxisInfo, axis info key string, or an integer; any of these must 
        point to an existing axis in the image
    
    """
    
    if isinstance(axis, int):
        axsize = image.shape[axis]
        axisinfo = image.axistags[axis]
        
    elif isinstance(axis, str):
        axsize = image.shape[image.axistags.index(axis)]
        axisinfo = image.axistags[axis]

    elif isinstance(axis, vigra.AxisInfo):
        axsize = image.shape[image.axistags.index(axis.key)]
        axisinfo = axis

    else:
        raise TypeError("axis expected to be an int, str or vigra.AxisInfo; got %s instead" % type(axis).__name__)
    
    #axcal = AxesCalibration(axisinfo)
    axcal = AxisCalibrationData(axisinfo)
    
    # FIXME what to do when there are several channels?
    
    return axcal.calibratedDistance(axsize)

def getAxisResolution(axisinfo):
    """Returns the resolution of the axisinfo object as a Python Quantity.
    """
    if not isinstance(axisinfo, vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    
    axcal = AxesCalibration(axisinfo)
    
    # FIXME what to do when there are several channels?
    
    return axcal.getResolution(axisinfo.key)
    
def getAxisOrigin(axisinfo):
    """Returns the axis origin as a Python Quantity
    """
    if not isinstance(axisinfo. vigra.AxisInfo):
        raise TypeError("Expecting a vigra.AxisInfo object; got %s instead" % type(axisinfo).__name__)
    
    # FIXME what to do when there are several channels?
    
    axcal = AxesCalibration(axisinfo)
    
    return axcal.getOrigin(axisinfo.key)
    
def specifyAxisTags(image, newtags, newshape=None, in_place=False):
    """Assigns a new AxisTags object to a VigraArray.
    Optionally, reshapes the data array and removes or inserts new axes
    if necessary.
    
    Positional parameters:
    ======================
    
    image: vigra.VigraArray
    
    newtags: a sequence (tuple or list) of maximum five axistag keys (str):
            "a", "c", "e", "f", "n", "x", "y", "z", "t", "?", "s", "l",
            "fa", "fe", "fn", "ft","fx", "fy", "fz"
            
            or:
                a string with comma-, space- or comma-space-separated keys
                    e.g. "x, y, z, t, c" or "x y z t c" or "x,y,z,t,c" 
                    
            or:
                a string with single-character keys (unsparated) 
                    e.g. "xyztc"
                    
            or:
                a sequence of vigra.AxisInfo objects
            
            or:
                a vigra.AxisTags object
            
            The length of the new tags may be greater than image.ndim only if
            a new shape is also specified (see below).
            
            In any case, the maximum length of new tags is 5.
            
    Named parameters:
    ==================
    newshape: None (default), or:
            a sequence (tuple or list) of new axes lengths (int), 
            axistag keys, or None, with the same number of elements as "newtags" 
            
            When an :int:, the element indicates the length of the axis indicated 
            by the corresponding tag element in the "newtags"
            
            When a tag key :string:, the axis at the corresponding position in 
            "newtags" will receive the length of the axis with _THIS_ tag key in 
            the "image"
            
            When :None:, the length of the axis at the corresponding index in "newtags"
            will be calculated from the lengths of the other axes and the 
            total number of samples of "image".
            
            There can at most one None element.
            
    in_place: boolean (default is False); 
            when False, the function returns a reshape copy of image, adorned
                with the new axistags
                
            when True, the "image" argument is modified directly (i.e. it gets
                the new axistags and the new shape) and the function returns a 
                reference to it
            
            
    """
    
 #   Signature: vigra.makeAxistags(spec, order=None, noChannels=None)
 #   Docstring:
 #   Create a new :class:`~vigra.AxisTags` object from the specification ``spec``.
 #   ``spec`` can be one of the following:
 #
 #   * an instance of the ``AxisTags`` class. In this case, the function creates
 #   a copy of ``spec``. If ``order`` is given, the resulting axistags are
 #   transposed to the desired order ('C', 'F', or 'V'). If ``noChannels=True``,
 #   the channel axis (if any) is dropped from the specification.
 #
 #   * a string or tuple of axis keys (e.g. ``'xyc'`` or ``('x', 'y', 'c')`` respectively)
 #   or a tuple of :class:`~vigra.AxisInfo` objects (e.g.
 #   ``(AxisInfo.x, AxisInfo.y, AxisInfo.c)``). The function then constructs a
 #   new ``AxisTags`` object from this specification. If ``order`` is given,
 #   the resulting axistags are transposed to the desired order ('C', 'F', or 'V').
 #   If ``noChannels=True``, the channel axis (if any) is dropped from the specification.
 #
 #   * an integer signifying the desired number of axes. In this case, the call (including
 #   optional arguments ``order`` and ``noChannels``) is forwarded to the function
 #   :meth:`~vigra.VigraArray.defaultAxistags`, whose output is returned.
 #   File:      /usr/lib64/python3.4/site-packages/vigra/arraytypes.py
 #   Type:      function
 
 # golden rule: number of samples must not change
    
    
    if not isinstance(image, vigra.VigraArray):
        raise TypeError("First argument must be a VigraArray; got %s instead." % (type(image).__name__))
    
    
    # newtags can be:
    # a sequence of AxisInfo keys (str)
    # a sequence of vigra.AxisInfo objects
    # a vigra.AxisTags object
    # a str containing space- or comma-separated keys
    if isinstance(newtags, (tuple, list)):
        if len(newtags) > image.ndims:
            if newshape is None:
                raise TypeError("When a new shape is not specified, new tags must not exceed the number of image dimensions (%d)" % image.ndim)
            
        if len(newtags) > 5:
            raise ValueError("Cannot specify more than 5 axis tags")
            
        if all([isinstance(tag, str) for tag in newtags]):
            tagslist = [vigra.AxisInfo(s, vigra.AxisType(axisTypeFromString[s])) for s in newtags]
            newTags = vigra.AxisTags(*tagslist)
            
        elif all([isinstance(tag, vigra.AxisInfo)]):
            newTags = vigra.AxisTags(newtags) # this c'tor supports a sequence of AxisInfo objects as a single argument
            
        else:
            raise TypeError("Expecting a sequence of str or vigra.AxisInfo objects")
        
    elif isinstance(newtags, vigra.AxisTags):
        newTags = newtags
        
    elif isinstance(newtags, str):
        if " " in newtags:
            a = newtags.split()         # "x, y, z" and "x y z" cases
            a = [c.strip(",") for c in a]
            
        elif "," in newtags:
            a = newtags.split(",")      # "x,y,z" case
            
        else:
            a = newtags
            
        for c in a:
            if c not in STANDARD_AXIS_TAGS_KEYS:
                raise ValueError("Invalid AxisInfo key: %s" % c)
            
        tagslist = [vigra.AxisInfo(c, vigra.AxisType(axisTypeFromString[c])) for c in a]
        newTags = vigra.AxisTags(*tagslist)
        
    else:
        raise TypeError("Expecting a sequence of str or vigra.AxisInfo objects, or a single vigra.AxisTags object; got a %s instead" % type(newtags).__name__)

    if newshape is not None:
        if isinstance(newshape, (tuple, list)):
            if len(newshape) != len(newTags):
                raise ValueError("Length of new shape must equal that of the new axis tags (%d)" % len(newTags))
            
            if all([isinstance(s, numbers.Integral) for s in newshape]):
                if np.prod(newshape) != image.size:
                    raise ValueError("When reshaping, the total number of elements in image must stay the same")
                
                newShape = newshape
                
            else:
                raise TypeError("New shape must contain numbers only")
            
        else:
            raise TypeError("New shape must be given as a tuple or list of numbers; got %s instead" % type(newshape).__name__)
        
    else: # no shape was specified: infer it from the length of new tags
        newShape = image.shape  # start with a default
                                # this applies to the case when newtags are as
                                #   many as image.ndim
                                # more new tags are prohibited by the earlier check
                                #   if you want to _ADD_ axes, you must also specify
                                #   a new shape
                                # case with fewer tags is dealt with next:
        if len(newTags) < image.ndim: # fewer tags, check if there are singleton axes to get rid of
            a = image.ndim - len(newTags)
            
            newShape = list(image.shape)
            
            for k in range(image.ndim-1, a, -1):
                if k >= len(newTags):
                    if image.shape[k] == 1:
                        del newShape[k]
                    else: # force specification of a tag for non-singleton dimensions
                        raise ValueError("Dimension %d is not singleton (has size %d), but does not have a new tag specified" % (k, image.shape[k]))
                        
    assert(np.prod(newShape) == image.size)
    
    
    if in_place:
        image.shape=newShape
        image.axistags=newTags
        
    else:
        # NOTE: reshape ALWAYS returns a copy of the source array
        image = image.reshape(newShape, axistags=newTags)
    
    return image

