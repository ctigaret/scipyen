import typing
from numbers import Number
import numpy as np
import vigra

def g_blob(meanX:float = 64., meanY:float = 64., meanZ:typing.Optional[float]=None,
           varX:float = 1.0, varY:float = 1.0, varZ:float = 0., n:int = 128):
    """Generates random normally distributed x and y coordinates for a set of points on a 2D grid.
    
    Parameters:
    -----------
    meanX, meanY, varX, varY: the parameters fo the Gaussian distribution, respectively,
        of the X and Y coordinates
    
    n: the number of points 
    
    meanZ, varZ: optional parameters for a Gaussian distribution of the values
        at the generates coordinates (see NOTE † below)
         
    
    Returns:
    --------
    a 2D numpy array of shape `n` × 2 (or n × 3†), with the generated random X and Y 
        coordinates, respectively, in columns 0 and 1, for `n` points
        
    NOTE: 
    † The generated coordinates are for samples in a virtual 2D space. By 
        default, each point has a value of 1 (adimensional). 
        
        When `meanZ` is passed as a float, then a third column will be generated,
        with random values at each point drawn from a Gaussian ditribution with
        parameters `meanZ`, `varZ`.
        
    """
    rng = np.random.default_rng()
    
    mean = (meanX, meanY) 
    
    cov = [[varX, 0.], [0., varY]] 
    
    ret = rng.multivariate_normal(mean, cov, size=n)
    
    if isinstance(meanZ, Number):
        vals = rng.normal(meanZ, varZ, n)
        return np.hstack([ret, vals[:,np.newaxis]])
    
    return ret

def g_blob_image(blob, img:typing.Optional[typing.Union[np.ndarray, vigra.VigraArray]]=None, size:int=128) -> vigra.VigraArray:
    """Embeds a `g_blob` result in an image.
    The image may be passed as the `img` argument, or a `size` by `size` synthetic
    image will be generated.
    
    See also: g_blob
    
    """
    
    if isinstance(img, np.ndarray):
        if img.ndim != 2:
            raise ValueError(f"Expecting a 2D array")
        
        if not isinstance(img, vigra.VigraArray):
            ret = vigra.VigraArray(img, axistags = vigra.defaultAxisTags(2, noChannels=True))
            
        ret = img
        
    else:
        ret = vigra.VigraArray(np.zeros((size, size)), axistags=vigra.defaultAxistags(2, noChannels=True))
    
    for k in range(blob.shape[0]):
        point = blob[k]
        if point.size == 2:
            xyc = point.astype(int)
            pval = 1.
        elif point.size == 3:
            xyc = point[:2].astype(int)
            pval = point[2]
            
        if xyc[0] < 0 or xyc[0] >= ret.shape[0]:
            continue
        
        if xyc[1] < 0 or xyc[1] >= ret.shape[1]:
            continue
        
        if pval < 0:
            pval = 0.
        
        ret[*xyc] += pval
        
    return ret
