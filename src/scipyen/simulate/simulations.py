import typing
import numpy as np
import vigra

def g_blob(meanX:float = 64., meanY:float = 64., varX:float = 1.0, varY:float = 1.0, size:int = 128):
    "Normally distributed points on a grid"
    rng = np.random.default_rng()
    
    mean = (meanX, meanY) 
    
    cov = [[varX, 0.], [0., varY]] 
    
    return rng.multivariate_normal(mean, cov, size=size)

def g_blob_image(blob, img:typing.Optional[typing.Union[np.ndarray, vigra.VigraArray]]=None, size:int=128) -> vigra.VigraArray:
    """"Embeds a g_blob in an image.
    The image may be passed as the `img` argument, or a `size` by `size` synthetic
    image will be generated.
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
        xyc = blob[k].astype(int)
        if xyc[0] < 0 or xyc[0] >= ret.shape[0]:
            continue
        
        if xyc[1] < 0 or xyc[1] >= ret.shape[1]:
            continue
        
        ret[*blob[k].astype(int)] += 1
        
    return ret
