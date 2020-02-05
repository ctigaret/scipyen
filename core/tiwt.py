from __future__ import print_function

import sys
import vigra
import pywt
import numpy as np
import numpy.matlib as mlib

# pywt module:
# Lee G, Gommers R, Wasilewski F, Wohlfahrt K, O’Leary A, Nahrstaedt H, and Contributors, 
# “PyWavelets - Wavelet Transforms in Python”, 2006-,
# https://github.com/PyWavelets/pywt [Online; accessed 2018].


def test_analysis_synthesis(img, wavename, levels, reclevel=None, rtol=1e-5, atol=1e-5):
    print("\nReconstruction using natural domain convolution with FIRs, in a pyramid algorithm")
    tiwtdec             = tiwt_dec(img, nLevels=levels, wavelet=wavename)

    tiwtrec, rec_coeffs = tiwt_rec(tiwtdec, reclevel, wavelet=wavename)
    
    tiwtcheck = img - tiwtrec
      
    OK = np.allclose(img, tiwtrec)
    if OK:
        print('Perfect reconstruction!')
    else:
        print('Close within relative tolerance: ', rtol, ' and absolute tolerance: ', atol, ': ', np.allclose(img, tiwtrec, rtol = rtol, atol = atol))
        
    print("Min difference between data and reconstruction: ", tiwtcheck.min())
    print("Max difference between data and reconstruction: ", tiwtcheck.max())
    print(" ")
      
    return tiwtrec, tiwtdec
    

def test_fft_analysis_synthesis(img, wavename, levels, reclevel=None, rtol=1e-5, atol=1e-5):
    ###### ACHIEVES PERFECT RECONSTRUCTION WITH HAAR WAVELETS, a-trous 
    ###### also for fft_dec/fft_rec
    print("\nReconstruction using fft convolution and pyramid algorithm")
    fftdec             = fft_dec(img, levels, wavelet=wavename)
    fftrec, rec_cfft   = fft_rec(fftdec, reclevel, wavelet=wavename)
    fftcheck           = img - fftrec
        
    OK = np.allclose(img,fftrec)
    if OK:
        print('Perfect reconstruction!')
    else:
        print('Close within relative tolerance: ', rtol, ' and absolute tolerance: ', atol, ': ', np.allclose(img, fftrec, rtol = rtol, atol = atol))
    print("Min difference between data and reconstruction: ", fftcheck.min())
    print("Max difference between data and reconstruction: ", fftcheck.max())
    print(" ")
    
    return fftrec, fftdec
    
    
def test_fft_purelet(data, levels, wavename):
   datahat = fft_purelet(data, levels, sigma2=0., wavelet=wavename)
   
   return datahat

    
def fft_purelet(image, nLevels, wavelet=None, sigma2=None, thr=None):
    '''

    '''
    
    if image.ndim > 2:
        raise ValueError("First argument was expected to be a 2D array")

    twopi   = np.pi * 2.0
    b0      = np.sqrt(2.0)/2.0

    N       = image.size
    N3      = N * 3
    NThetas = nLevels * 2

    thetaParams = [sigma2, b0, 3., 8., 100.]

    if thr is not None and (thr < 0 or thr >= nLevels):
        raise ValueError("Incorrect PURE-LET threshold value: must be >= 0, or None")

    ## NOTE: preallocate arrays -- keep everything as np.ndarray objects

    x             = np.zeros((image.shape[0], image.shape[1], 3)) # h, v, d, per-level

    xq            = np.zeros((image.shape[0], image.shape[1], 3)) # h, v, d, per-level

    xdor          = np.zeros((image.shape[0], image.shape[1], 3)) # h, v, d, per-level

    xqor          = np.zeros((image.shape[0], image.shape[1], 3))# h, v, d, per-level

    ## NOTE: from this we derive per-level diagonal terms

    dDR = np.ones((image.shape[0], image.shape[1], 3))

    Fy            = np.zeros((N, NThetas))

    yDelFy        = np.zeros((NThetas,))

    yDiv_Fy_delFy = np.zeros((NThetas,))

    ## NOTE: Notations:
    ## NOTE: g  = analysis low-pass;
    ## NOTE: g_ = synthesis low-pass
    ## NOTE: h  = analysis high-pass 
    ## NOTE: h_ = synthesis high-pass

    ## NOTE: prepare FIR kernels

    ## NOTE: requires time-reversal as explained in fft_dec/fft_rec 
    ## NOTE: this is done when calling polyval, in the loop
    if isinstance(wavelet, str):
        wavelet = pywt.Wavelet(wavelet)
        
        # analysis (decomposition) FIRs
        g0 = np.array(wavelet.dec_lo) 
        h0 = np.array(wavelet.dec_hi)

        # synthesis (reconstruction) FIRs
        g_0 = np.array(wavelet.rec_lo)
        h_0 = np.array(wavelet.rec_hi)

    elif isinstance(wavelet, pywt.Wavelet):
        # analysis (decomposition) FIRs
        g0 = np.array(wavelet.dec_lo)
        h0 = np.array(wavelet.dec_hi)

        # synthesis (reconstruction) FIRs
        g_0 = np.array(wavelet.rec_lo)
        h_0 = np.array(wavelet.rec_hi)

    elif wavelet == None: # use the Haar wavelet (un-normalized)
        # analysis (decomposition) FIRs
        g0 = np.array([ 1., 1.])
        h0 = np.array([-1., 1.])

        # synthesis (reconstruction) FIRs
        g_0 = np.array([1., 1.]) / 2.0
        h_0 = np.array([1.,-1.]) / 2.0

    else:
        raise ValueError("Second argument must be a valid pywt Wavelet object or a string with a valid pywt Wavelet name, or None")
    
    #print("g0: ", g0)
    #print("h0: ", h0)

    #print("g_0: ", g_0)
    #print("h_0: ", h_0)
    
    
    ## NOTE: sampled frequency domain (0..2*pi), one for each direction
    ## NOTE: (vertical, horizontal)

    zx_0 = np.exp(1j * twopi * np.linspace(0, 1, image.shape[0],  endpoint=False))
    zy_0 = np.exp(1j * twopi * np.linspace(0, 1, image.shape[1], endpoint=False))

    zx = np.zeros(zx_0.shape, dtype=np.complex128)
    zy = np.zeros(zy_0.shape, dtype=np.complex128)

    zx_ = np.zeros(zx_0.shape, dtype=np.complex128)
    zy_ = np.zeros(zy_0.shape, dtype=np.complex128)

    ## NOTE: low-pass reconstruction 2D transfer function is build it up recursively, 
    ## NOTE: noting that we start from the highest resolution level instead of 
    ## NOTE: the coarsest level as is usually done (see fft_rec)

    LL_ = np.ones(image.shape, dtype=np.complex128) # to be updated at end of each iteration

    ## NOTE: the input to the forward wavelet transform as implemented in the Fourier domain
    ## NOTE:
    ## NOTE: throughout the loop below, X is successively updated at each iteration by
    ## NOTE: convolution with the analysis low pass filter, which is simply the separable
    ## NOTE: 2D convolution with the low-pass 1D FIR transfer functions
    ## NOTE:
    ## NOTE: this IS the same as in the tiwt_purelet which implements convolution in the 
    ## NOTE: natural domain
    ## NOTE:
    ## NOTE: however, there the data is convolved using 2D separable convolution
    ## NOTE: with 1D analysis low pass FIR kernels
    ## NOTE: 
    ## NOTE: the low pass synthesis filter, however, is updated by convolving it with the
    ## NOTE: version of low pass synthesis transfer function from the previous level 
    ## NOTE: (i.e., multiplication in the Fourier domain)
    ## NOTE:
    ## NOTE: in contrast, in the image domain code (tiwt_purelet) reconstruction
    ## NOTE: is implemented by the inner loop which iterates in REVERSE order 
    ## NOTE: (i.e., back up the pyramid algorithm)

    X = np.fft.fft2(image, axes = (0,1)) 

    ## NOTE: iteration from finest (level 0) to coarsest level (nLevels-1)
    
    for k in range(nLevels):
        zexp = np.power(2.0, k) ## NOTE: dilation operator at level k

        ## NOTE: z^(-zexp) dyadically upsamples the filter but also time-reverses it, 
        ## NOTE: hence we compensate this by time-reversing the base FIRs kernels
        ## NOTE: used to generate the upsampled transfer functions (see above) 

                                      ## NOTE: level (k)  =         0,  1,  2,  3  
        zx = np.power(zx_0, -zexp) ## NOTE: z ^ -(2^k) => z ^ { -1, -2, -4, -8  }
        zy = np.power(zy_0, -zexp)

        zx_ = np.power(zx_0, zexp) ## NOTE: z ^ (2^k) => z ^ {   1,  2,  4,  8  }
        zy_ = np.power(zy_0, zexp)

        ## NOTE: 1D transfer functions for analysis (decomposition)

        Lx = np.polyval(g0[::-1, ], zx) ## NOTE: low pass; time reversal of the 
        Ly = np.polyval(g0[::-1, ], zy) ## NOTE: the FIR kernel is done here

        Hx = np.polyval(h0[::-1, ], zx) ## NOTE: high pass; time reversal of
        Hy = np.polyval(h0[::-1, ], zy) ## NOTE: the FIR kernel is done here

        ## NOTE: 1D transfer functions for synthesis (reconstruction)

        Lx_ = np.polyval(g_0, zx_)/2.0 ## NOTE: low pass; NO time reversal
        Ly_ = np.polyval(g_0, zy_)/2.0 ## NOTE:

        Hx_ = np.polyval(h_0, zx_)/2.0 ## NOTE: high pass
        Hy_ = np.polyval(h_0, zy_)/2.0 ## NOTE:

        ## NOTE: 2D transfer functions for analysis = outer product of combinations
        ## NOTE: of 1D transfer functions on both directions

        LL = np.outer(Lx, Ly)
        HL = np.outer(Hx, Ly)
        LH = np.outer(Lx, Hy)
        HH = np.outer(Hx, Hy)

        ## NOTE: 2D transfer functions for synthesis (details only).
        ## NOTE:
        ## NOTE: The approximation (LL_) is updated last thing in the iteration, 
        ## NOTE: in preparation for the next iteration --  see further below
    
        HL_ = np.outer(Hx_, Ly_)
        LH_ = np.outer(Lx_, Hy_)
        HH_ = np.outer(Hx_, Hy_)
        

        ## NOTE: 2D synthesis FIRs explained here
        ##
        ## NOTE: The 2D FIRs for wavelet reconstruction (a.k.a synthesis)
        ## NOTE: are hl_ll, lh_ll, hh_ll respectively for the 
        ## NOTE: horizontal, vertical and diagonal detail subbands.
        ## NOTE: 
        ## NOTE: They are obtained by inverse Fourier transform of the corresponding 
        ## NOTE: 2D transfer functions computed by element-wise multiplication
        ## NOTE: of the detail subband-specific 2D transfer functions 
        ## NOTE: (HL_, LH_, and HH_, calculated above) with the 2D transfer function
        ## NOTE: for the approximation subband at current decomposition level, LL_).
        ## NOTE:
        ## NOTE: This multiplication step is required, since we're iterating from 
        ## NOTE: the finest to coarsest level here (i.e.,, "top to bottom"), 
        ## NOTE: as opposed to performing the reconstruction in the "bottom up" 
        ## NOTE: order (from the coarsest to the finest level) as it is usually done.
        #
        #
        # what this basically does is to calculate the PRODUCT of the transfer functions
        # (in the Fourier domain) followed by inverse Fourier transform, which in theory is 
        # the same as the CONVOLUTION of the upsampled 2D FIRs in the natural domain, directly.
        
        ## NOTE: 2D transfer functions for DoR and QoR analysis are obtained by the 
        ## NOTE: Hadamard matrix product (element-wise multiplication) between 
        ## NOTE: the analysis and synthesis 2D FIRs. The 2D analysis FIRs are the
        ## NOTE: result of inverse Fourier transform of the 2D analysis transfer functions
        ## NOTE: (HL, LH, and HH). Finally, we forward Fourier transform the product to
        ## NOTE: obtain the 2D subband transfer functions for DoR and QoR
        
        hl_ll_ = np.fft.ifft2(HL_ * LL_, axes=(0, 1))  # horizontal
        lh_ll_ = np.fft.ifft2(LH_ * LL_, axes=(0, 1))  # vertical  
        hh_ll_ = np.fft.ifft2(HH_ * LL_, axes=(0, 1))  # diagonal  
        
        DoRHL = np.fft.fft2(np.fft.ifft2(HL, axes=(0, 1)) * hl_ll_) # horizontal
        DoRLH = np.fft.fft2(np.fft.ifft2(LH, axes=(0, 1)) * lh_ll_) # vertical  
        DoRHH = np.fft.fft2(np.fft.ifft2(HH, axes=(0, 1)) * hh_ll_) # diagonal  

        ## TODO: revisit this for asymmetric filters (e.g. Daubechies > db1 (Haar))
        QoRHL = np.fft.fft2(np.fft.ifft2(LL, axes=(0, 1)) * hl_ll_)
        QoRLH = np.fft.fft2(np.fft.ifft2(LL, axes=(0, 1)) * lh_ll_)
        QoRHH = np.fft.fft2(np.fft.ifft2(LL, axes=(0, 1)) * hh_ll_)


        ## NOTE: forward transform detail coefficients at level k calculated by
        ## NOTE: convolution (i.e. multiplication in the Fourier domain) with the 
        ## NOTE: high-pass analysis transfer functions

        fy_t1 = np.concatenate(((X * HL)[:,:,np.newaxis], \
                                (X * LH)[:,:,np.newaxis], \
                                (X * HH)[:,:,np.newaxis]), axis=2)
        
        #print("fy_t1.shape ", fy_t1.shape)

        ## NOTE: detail coefficients at current level (in the image domain)
        ## NOTE: will be used by the thresholding function purelet_theta_analytic
        ## NOTE: (see below)

        x = np.real(np.fft.ifft2(fy_t1, axes=(0,1)))

        ## NOTE: approximation with low-pass analysis transfer function, 
        ## NOTE: is stored for the next iteration;
        ## NOTE: at level 0, LL is all ones so as to accommodate this op

        X = X * LL

        # TODO: compute GDC coeffs for other (asymmetric) wavelets as well

        ## NOTE: forward transform approximation coefficients at level k calculated by
        ## NOTE: convolution (i.e. multiplication in the Fourier domain) with the
        ## NOTE: low-pass analysis transfer function

        xq = np.tile(np.real(np.fft.ifft2(X, axes=(0, 1)))[:,:,np.newaxis], (1, 1, 3))

        xdor[:,:,0] = np.real(np.fft.ifft2(X * DoRHL, axes=(0, 1)))
        xdor[:,:,1] = np.real(np.fft.ifft2(X * DoRLH, axes=(0, 1)))
        xdor[:,:,2] = np.real(np.fft.ifft2(X * DoRHH, axes=(0, 1)))

        xqor[:,:,0] = np.real(np.fft.ifft2(X * QoRHL, axes=(0, 1)))
        xqor[:,:,1] = np.real(np.fft.ifft2(X * QoRLH, axes=(0, 1)))
        xqor[:,:,2] = np.real(np.fft.ifft2(X * QoRHH, axes=(0, 1)))

        ## NOTE: sigma2 is None means we want to estimate AWGN variance from the 
        ## NOTE: finest detail coefficients using Donoho's formula
        
        #print(x.shape)
        if k==0 and sigma2 is None:
            sigma2 = np.power(np.median(np.abs(x[:,:,range(1,3)])) / 0.6745, 2.)
            #print("variance=",sigma2)
            thetaParams[0] = sigma2
    
        thetaParams[1] = np.power(b0, k+1)
        
        ## NOTE: pass approximation and detail coefficients to the theta function
        ## NOTE: these are in the natural domain
        
        t, dt_dx, dt_dy, dt_dxdy, d2t_dx2, d2t_dy2 = \
            purelet_theta_analytic(x, xq, thetaParams)

        ## NOTE: prepare diagonal terms -- these values are for db1 wavelets ONLY
        ## TODO: generate sets of diagonals for given problem size + wavelet
        ## 
        ## NOTE: dDR is all ones (N3 elements)
        
        diagsDR   = dDR * np.power(2., -2. * (k+1))
        diagsQR   = dDR * np.power(2., -2. * (k+1))
        diagsDoDR = np.power(diagsDR, 2.)
        diagsQoQR = -diagsDoDR
        diagsDoQR = diagsDR / 2.
        
        ## NOTE: d1t1_dx is all 1, hence the inner vector product with xdor 
        ## NOTE: is just the sum of all elements of xdor at current level, whereas
        ## NOTE: d1t1_dy is all 0 hence the inner vector product with xqor is 0
       
        yDelFy[k]         = ( np.sum(xdor) ) / N3
        
        ## NOTE: the inner vector product is essentially the sum of the element-wise 
        ## NOTE: product of the two vectors so to avoid confusion related to axes 
        ## NOTE: conversions (flatten-reshape) we just multiply these matrices 
        ## NOTE: element-wise then calculate the sum over the result
        
        yDelFy[k+nLevels] = ( np.sum(dt_dx * xdor) + \
                              np.sum(dt_dy * xqor) ) / N3
        
        ## NOTE: d1t1_dx is all ones, hence the inner vector product with diadsDR is just 
        ## NOTE: the sum of all elements of diagsDR,
        ##
        ## NOTE: d1t1_dy is all zeros hence its inner vector product with diagsQR is zero
        ##
        ## NOTE: d2t1_dx and d2t1_dy are all zero and similarly the mixed 
        ## NOTE: partial derivative of theta_1 in x and y, which is also zero
        
        # NOTE: diagsDR is the same value taken N3 times (width, height, 3), hence its arithmetic sum is THIS SAME value
        yDiv_Fy_delFy[k]  = np.sum(diagsDR) / N3
            
        #the inner vector product is the sum of the element-wise product of the vectors so to avoid
        #confusion related to axes conversions (flatten-reshape, which is column and which is row) 
        # we just multiply these matrices element wise then calculate their sum
        
        #yDiv_Fy_delFy[k+nLevels]  =( np.sum(dt_dx_all[:,:,:,k] * diagsDR) + np.sum(dt_dy_all[:,:,:,k] * diagsQR) - \
            #(np.sum(d2t_dx2_all[:,:,:,k] * diagsDoDR) + np.sum(d2t_dy2_all[:,:,:,k] * diagsQoQR) + 2. * np.sum(dt_dxdy_all[:,:,:,k] * diagsDoQR))) / N3
        
        yDiv_Fy_delFy[k+nLevels]  =( np.sum(dt_dx * diagsDR) + np.sum(dt_dy * diagsQR) - \
            (np.sum(d2t_dx2 * diagsDoDR) + np.sum(d2t_dy2 * diagsQoQR) + 2. * np.sum(dt_dxdy * diagsDoQR))) / N3
        
        ## NOTE: reconstruct subband data (Fy) from thresholded detail coefficients 
        ## NOTE: at current level:

       ## NOTE: fy_t2 ALSO in the Fourier domain (as fy_t1, see above)
        fy_t2 = np.fft.fft2(t, axes=(0, 1))

        fy_t1[:,:,0] = fy_t1[:,:,0] * HL_ * LL_
        fy_t2[:,:,0] = fy_t2[:,:,0] * HL_ * LL_
        
        fy_t1[:,:,1] = fy_t1[:,:,1] * LH_ * LL_
        fy_t2[:,:,1] = fy_t2[:,:,1] * LH_ * LL_
        
        fy_t1[:,:,2] = fy_t1[:,:,2] * HH_ * LL_
        fy_t2[:,:,2] = fy_t2[:,:,2] * HH_ * LL_
        
        ## NOTE: this overwrites the destination arrays, which is okay as we don't need 
        ## NOTE: their previous contents anymore
        ## NOTE: furthermore, the destination arrays now contain real data (as opposed to Fourier domain)
        
        fy_t1 = np.real(np.fft.ifft2(np.sum(fy_t1, axis=2), axes=(0, 1)))
        fy_t2 = np.real(np.fft.ifft2(np.sum(fy_t2, axis=2), axes=(0, 1)))
        
        # here is the only place were we still need to flatten
        Fy[:,k] = fy_t1.flatten(order="F")
        Fy[:,k+nLevels] = fy_t2.flatten(order="F")

        ## finally, at the end of the iteration, update the transfer function  
        # for the approximation subband of the inverse wavelet transform, LL_ 
        
        LL_ *= np.outer(Lx_, Ly_)
        
        #LL_ = LL_ * np.tile(Ly_, (image.shape[0], 1)) * np.tile(Lx_, (image.shape[1], 1)).T # approximation
        #LL_ = np.tile(Ly_, (image.shape[0], 1)) * np.tile(Lx_, (image.shape[1], 1)).T # approximation
        
    ## NOTE: reconstruct the low-pass (approximation) data in the image domain    
    Fy_lp = np.real(np.fft.ifft2(X * LL_, axes=(0, 1)))
                            
    ## NOTE: finally compute the PURE vector `c', and solve for the linear parameters
    yHi = (np.array(image) - Fy_lp).flatten(order="F") # this is faster, as we already have got these terms
    
    M = np.dot(Fy.T, Fy) / N
    
    yFy = np.dot(Fy.T, yHi) / N
    
    ## NOTE: the PURE-LET vector
    c = yFy - yDelFy - sigma2 * yDiv_Fy_delFy
    
    ## NOTE: solve the PURE-LET equation
    
    a = np.dot(np.linalg.pinv(M), c)
    
    ## NOTE: if thr is None, then just reconstruct the original image and
    ## NOTE: disregard any thresholding/denoising logic
    ## NOTE:
    ## NOTE: if thr is 0, the DO USE the denoising logic, but do NOT threshold the high-pass subbands
    ## NOTE: (i.e. only rely on the result of the PURE-theta function)
    ## NOTE:
    ## NOTE: finally, if thr is > 0 then on top of the above, zero the finest level detail subbands
    ## NOTE: up to the value of thr.
    
    ## when thr is None just reconstruct the original data (no denoising)
    ## when thr is zero, perform denoising without thresholding
    ## otherwise, threshold at thr level
    if thr is None:
        a[range(nLevels)] = 1 # make this the Id matrix
        a[range(nLevels, 2*nLevels)] = 0;
        
    else:
        if thr > 0 and thr < nLevels:
            a[range(thr)] = 0
            a[range(nLevels, nLevels+thr)] = 0

    ## NOTE: reconstruct from thresholded detail coeffs plus the low-pass residual
    ## NOTE: then cast back to VigraArray for their axes system
    
    if isinstance(image, vigra.VigraArray):
        ret = vigra.VigraArray(np.reshape(np.dot(Fy, a), (image.shape[0], image.shape[1]), order="F") + Fy_lp, axistags=image.axistags)
        
    else:
        ret = vigra.VigraArray(np.reshape(np.dot(Fy, a), (image.shape[0], image.shape[1]), order="F") + Fy_lp, axistags=vigra.VigraArray.defaultAxistags("xy"))

    return ret


def tiwt_purelet(image, nLevels, wavelet=None, sigma2=None, thr=None):
    '''
    # 2015-10-14:
    # all it does for now is to decompose - reconstruct in a single loop
    #
    # test dor and qor using a 2D Dirac
    #
    # seems to achieve some good level of reconstruction (at 1e-5 error level)
    # TODO: try other (biorthonormal) wavelets as well
    '''
    if image.channels > 1:
        raise ValueError("Multi-channel data not supported")
  
    if image.spatialDimensions > 2:
        if image.depth > 1:
            raise ValueError("3D data not supported")
    
    if isinstance(wavelet, str):
        wavelet = pywt.Wavelet(wavelet)
        g0 = np.array(wavelet.dec_lo)# 
        h0 = np.array(wavelet.dec_hi)# 
        
        g_0 = np.array(wavelet.rec_lo)# / 2.
        h_0 = np.array(wavelet.rec_hi)# / 2.

    elif isinstance(wavelet, pywt.Wavelet):
        g0 = np.array(wavelet.dec_lo)# 
        h0 = np.array(wavelet.dec_hi)# 
        
        g_0 = np.array(wavelet.rec_lo)# / 2.
        h_0 = np.array(wavelet.rec_hi)# / 2.
        
    elif wavelet == None:
        g0 = np.array([ 1., 1.])
        h0 = np.array([-1., 1.])
        
        g_0 = np.array([1., 1.]) / 2. #4.0
        h_0 = np.array([1.,-1.]) / 2. #4.0
        
    else:
        raise ValueError("Second argument must be a valid pywt Wavelet object or a string with a valid pywt Wavelet name, or None")
  
    #print("analysis low pass: ",  g0)
    #print("analysis high pass: ", h0)
    #print("synthesis low pass: ",  g_0)
    #print("synthesis high pass: ", h_0)
    
    kernels_rev_g = list()
    
    len0 = len(h0)
    
    print("len(h0): ", len(h0))
    
    cdel = len0/2 - 1
  
    if nLevels is None:
        nLevels = np.int(np.log2(min(image.shape)))
        for k in range(nLevels-1, -1, -1):
            fl = max(len(g0) << k, len(h0) << k)
            if fl <= min(LL.shape):
                nLevels = k
                break
            
  
    # avoid per-level filter being longer than the smaller image dimension
    newMaxLevels = nLevels
  
    N       = image.size
    
    print("image size: ", N)
    
    N3      = N * 3
    NThetas = nLevels * 2
    twopi   = np.pi * 2.0
    b0      = np.sqrt(2.0)/2.0
    
    thetaParams = [0, b0, 3., 8., 100.]
    
    if thr is not None and (thr < -1 or thr >= nLevels):
        raise ValueError("Incorrect PURE-LET threshold value, must be >= -1")
    
    x = vigra.VigraArray((image.shape[0], image.shape[1], 4, nLevels), \
                         axistags=vigra.VigraArray.defaultAxistags("xyzt"))
  
    # for testing only
    x_rev = vigra.VigraArray((image.shape[0], image.shape[1], 4, nLevels), \
                         axistags=vigra.VigraArray.defaultAxistags("xyzt"))
  
    # for testing only
    dor = vigra.VigraArray((image.shape[0], image.shape[1], 3, nLevels), \
                        axistags=vigra.VigraArray.defaultAxistags("xyzt"))
    
    xq = vigra.VigraArray((image.shape[0], image.shape[1], 3, nLevels), \
                         axistags=vigra.VigraArray.defaultAxistags("xyzt"))
    
    xdor = vigra.VigraArray((image.shape[0], image.shape[1], 3, nLevels), \
                         axistags=vigra.VigraArray.defaultAxistags("xyzt"))
    
    xqor = vigra.VigraArray((image.shape[0], image.shape[1], 3, nLevels), \
                         axistags=vigra.VigraArray.defaultAxistags("xyzt"))
    
    fy_t1 = vigra.VigraArray((image.shape[0], image.shape[1], 3), \
                         axistags=vigra.VigraArray.defaultAxistags("xyz"))
    
    Fy_1 = vigra.VigraArray((image.shape[0], image.shape[1], nLevels), \
                         axistags=vigra.VigraArray.defaultAxistags("xyz"))
    
    # start with the image input
    # after the first iteration in the loop below, this becomes the approximation
    # which will then be used as input for the next iteration
    LL = image.dropChannelAxis()
    
    ## NOTE: for DoR convolutions consider the approach of the fft_purelet:
    # 1) get the 1D DFT of the FIRs => 1D transfer functions
    #
    # 2) calculate outer products => 2D transfer functions
    #
    # 3) perform convolution of high pass subband synthesis trasfer function with
    #    the low pass synthesis transfer functions
    #
    # 3) transform the result back into image domain (inverse Fourier transform)
    #
    # 4) multiply the result elementwise with the inverse Fourier transform for the 
    #    high pass subband analysis 2D transfer functions
    #
    # 5) bring back into Fourier domain (forward Fourier transform the result) =>
    #    2D DoR transfer function
    #
    # 6) finally, convolve the data with this new 2D transfer function by using
    #    multiplication in the Fourier domain between the forward Fourier trasformed
    #    data and the 2D DoR transfer function
    #
    # 7) inverse Fourier transform (back into image domain), discard imaginary part
    #
    ## NOTE: if we were to do this, then what's the point in sticking with convolution in the 
    # image domain for the rest and NOT do everything in the Fourier domain 
    # (fft_purelet already does it)?
    #
    ## NOTE: image domain convolution has a speed advantage over Fourier transforms
    # for relatively small data (see timings.ods in VigraPurelet-src: for the typical
    # image of an EPSCaT (256 x 1024) or less, analysis followed by synthesis 
    # (no purelet denoising) at 4 levels is twice as fast in the image doman compared 
    # to Fourier transform
    # The cross-over point is at level 6 above which the Fourier-based algorithm 
    # becomes faster than the algorithm based on image domain convolution for all 
    # sample sizes tested (16,384 -- 1,048,576). In fact the speed of the Fourier 
    # transform-based algorithm decreases linearly with the sample size.
    
    ###zx_0 = np.exp(1j * twopi * np.linspace(0, 1, image.shape[0],  endpoint=False))
    ###zy_0 = np.exp(1j * twopi * np.linspace(0, 1, image.shape[1], endpoint=False))
    
    ###zx = np.zeros(zx_0.shape, dtype=np.complex128)
    ###zy = np.zeros(zy_0.shape, dtype=np.complex128)
    
    ###zx_ = np.zeros(zx_0.shape, dtype=np.complex128)
    ###zy_ = np.zeros(zy_0.shape, dtype=np.complex128)
    
    for k in range(nLevels):
        
        print("k: ", k)
        
        filterLen = len0 << k # a trous dyadic upsampling of FIRs
        
        print("filterLen: ", filterLen)
        
        delay = cdel * 2 ** k
    
        if(filterLen > min(LL.shape)):
            newMaxLevels = k-1
            print("upsampled FIR at level ", k, " is longer (",filterLen,") than the smallest image dimension (", min(LL.shape),")")
            break

        garray = np.zeros(filterLen) # a trous dyadic upsampling of FIRs
        harray = np.zeros(filterLen)
    
        g_array = np.zeros(filterLen)
        h_array = np.zeros(filterLen)
        
        for j in range(len(h0)):
            garray[j << k] = g0[j]
            harray[j << k] = h0[j]
            
            g_array[j << k] = g_0[j] / 2.
            h_array[j << k] = h_0[j] / 2.
            
        #### also calculate the DFT => 1D transfer functions:
        #### 1) prepare the z domain
        
        ###zexp = np.power(2.0, k)# * -1. # -(2^k) # dilation operator at level k
        
                                      #### level (k)  =         0,  1,  2,  3  
        ###zx = np.power(zx_0, -zexp) # z ^ -(2^k) => z ^ { -1, -2, -4, -8  }
        ###zy = np.power(zy_0, -zexp)
    
        ###zx_ = np.power(zx_0, zexp) # z ^ (2^k) => z ^ {   1,  2,  4,  8  }
        ###zy_ = np.power(zy_0, zexp)
    
        #### 2) calculate the DFT, then the 2D transfer functions:
        
        #### 2.1) 1D transfer functions -- analysis (decomposition)
        
        ###Lx = np.polyval(g0[::-1, ], zx) # low pass ; time reversal done here
        ###Ly = np.polyval(g0[::-1, ], zy) # time reversal done here
        
        
        ###Hx = np.polyval(h0[::-1, ], zx) # high pass; time reversal done here
        ###Hy = np.polyval(h0[::-1, ], zy) # time reversal done here
    
        #### 2.2) 1D transfer functions -- synthesis (reconstruction)

        ###Lx_ = np.polyval(g_0, zx_)/2.0 # low pass; NO time reversal
        ###Ly_ = np.polyval(g_0, zy_)/2.0 #
    
          
        ###Hx_ = np.polyval(h_0, zx_)/2.0 # high pass  
        ###Hy_ = np.polyval(h_0, zy_)/2.0 #            
            
        
        #### 2.3) 2D transfer functions for analysis = outer product of 1D transfer functions
        ###LL = np.tile(Ly, (image.shape[0], 1)) * np.tile(Lx, (image.shape[1], 1)).T # approximation
        ###HL = np.tile(Hy, (image.shape[0], 1)) * np.tile(Lx, (image.shape[1], 1)).T # horizontal details
        ###LH = np.tile(Ly, (image.shape[0], 1)) * np.tile(Hx, (image.shape[1], 1)).T # vertical   details
        ###HH = np.tile(Hy, (image.shape[0], 1)) * np.tile(Hx, (image.shape[1], 1)).T # diagonal   details
        
        #### 2D transfer functions for synthesis (details only)
        ##### approximation is updated last thing in the iteration, in prep for the next 
        ###HL_ = np.tile(Hy_, (image.shape[0], 1)) * np.tile(Lx_, (image.shape[1], 1)).T # horizontal details
        ###LH_ = np.tile(Ly_, (image.shape[0], 1)) * np.tile(Hx_, (image.shape[1], 1)).T # vertical   details
        ###HH_ = np.tile(Hy_, (image.shape[0], 1)) * np.tile(Hx_, (image.shape[1], 1)).T # diagonal   details
        
        
        ## NOTE: wrong approach! the product between fwd and rev kernels should be
        # between the fwd kernel and the _FULL_ rev filter 
        # (i.e. rev hig pass convolved with rev lowpass)
        #for j in range(filterLen):
            #m = j + filterLen/2
            
            #gog_array[j] = garray[j] * g_array[j]
            #hoh_array[j] = harray[j] * h_array[j]
            
            #if m > (filterLen-1):
                #m = m-filterLen
                
            #gog_array[j] = garray[j] * g_array[m]
            #hoh_array[j] = harray[j] * h_array[m]
            #gog_array[j << k] = g0[j] * g_0[j]
            #hoh_array[j << k] = h0[j] * h_0[j]
            
        #print("gog_array: ", gog_array)
        #print("hoh_array: ", hoh_array)

        fLeft = int(filterLen/2 - filterLen - delay)
        fRight = int(filterLen/2 - 1 - delay)
        
        g = vigra.filters.explictKernel(0, filterLen-1, garray)
        h = vigra.filters.explictKernel(0, filterLen-1, harray)
        
        g.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        h.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        
        g_ = vigra.filters.explictKernel(fLeft, fRight, g_array)
        h_ = vigra.filters.explictKernel(fLeft, fRight, h_array)
        
        g_.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        h_.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        
        #gog_ = vigra.filters.explictKernel(0, filterLen-1, gog_array)
        #hoh_ = vigra.filters.explictKernel(0, filterLen-1, hoh_array)
        
        #gog_.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        #hoh_.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        
        kernels_rev_g.append(g_)
        
        # convolve input to get the high pass subbands
        LH = vigra.filters.convolve(LL, (g, h)) # low/x  * high/y  => "horizontal" details
        HL = vigra.filters.convolve(LL, (h, g)) # high/x * low/y   => "vertical" details
        HH = vigra.filters.convolve(LL, (h, h)) # high/x * high/y  => "diagonal" details
    
        ## the generate the approximation (low pass) subband; this will become the input
        # for the next iteration
        LL = vigra.filters.convolve(LL, (g, g)) # low/x  * low/y   => "approximation" = input for next iteration
    
        # forward transform coefficients (at level k)
        x[:,:,0,k] = LL # approximation
        x[:,:,1,k] = LH # "horizontal" detail
        x[:,:,2,k] = HL # "vertical" details
        x[:,:,3,k] = HH # "diagonal" details
        
        # synthesize the detail image subband:
        
        fy_t1[:,:,0] = vigra.filters.convolve(x[:,:,1,k], (g_,h_))
        fy_t1[:,:,1] = vigra.filters.convolve(x[:,:,2,k], (h_,g_))
        fy_t1[:,:,2] = vigra.filters.convolve(x[:,:,3,k], (h_,h_))
        
        # for testing only
        #x_rev[:,:,0,k] = vigra.filters.convolve(x[:,:,0,k], (g_, g_))
        x_rev[:,:,0,k] = x[:,:,0,k] ## when at first level, this approximation is just added to the hi-pass subbands
        x_rev[:,:,1,k] = fy_t1[:,:,0]
        x_rev[:,:,2,k] = fy_t1[:,:,1]
        x_rev[:,:,3,k] = fy_t1[:,:,2]
        
        # for testing only
        #dor[:,:,0,k] = vigra.filters.convolve(x[:,:,1,k], (gog_, hoh_)) # WRONG !!!
        #dor[:,:,1,k] = vigra.filters.convolve(x[:,:,2,k], (hoh_, gog_))
        #dor[:,:,2,k] = vigra.filters.convolve(x[:,:,3,k], (hoh_, hoh_))
        
        if k > 0:
            # NOTE: INNER LOOP for convolution with synthesis low pass:
            # reverse iteration to convolve with synthesis low pass FIR kernels
            # this iplements the updating of the LL_ low pass transfer function in
            # fft_purelet
            #
            # see also comments in fft_purelet
            #
            for j in range(k-1, -1, -1):
                x_rev[:,:,0,k] = vigra.filters.convolve(x_rev[:,:,0,k], kernels_rev_g[j]) # testing
                for o in range(3):
                    fy_t1[:,:,o] = vigra.filters.convolve(fy_t1[:,:,o], kernels_rev_g[j])
                    x_rev[:,:,o+1,k] = vigra.filters.convolve(x_rev[:,:,o+1,k], kernels_rev_g[j]) # testing
                    #dor[:,:,o,k] = vigra.filters.convolve(dor[:,:,o,k], kernels_rev_g[j])
        
        Fy_1[:,:,k] = (fy_t1[:,:,0] + fy_t1[:,:,1] + fy_t1[:,:,2])
        
    Fy_lp = x[:,:,0,nLevels-1]
    
    print(len(kernels_rev_g))
    # reconstruct the residual low-pass
    for j in range(nLevels-1, -1, -1):
        print("j: ", j)
        Fy_lp = vigra.filters.convolve(Fy_lp, kernels_rev_g[j])
        
    ret = Fy_lp
    
    # then add up the high pass reconstructed subbands
    for j in range(nLevels):
        ret = ret + Fy_1[:,:,j]
        
    #return ret, Fy_lp, Fy_1, x, x_rev, dor
    return ret  #, x, x_rev #, dor
    
    
def fft_dec_transfer_functions( width, height, nLevels, wavelet=None):
    '''
    '''
    twopi = np.pi * 2.0
    
    if isinstance(wavelet, str):
        wavelet = pywt.Wavelet(wavelet)
        g0 = np.array(wavelet.dec_lo) #[::-1, ] # time-reversal -- needed as explained below 
        h0 = np.array(wavelet.dec_hi) #[::-1, ] # -- moved in the loop below
#        h0 = -1. * mirrorfilt(g0) # equivalent to the line above

    elif isinstance(wavelet, pywt.Wavelet):
        g0 = np.array(wavelet.dec_lo) #[::-1, ] # see comments above
        h0 = np.array(wavelet.dec_hi) #[::-1, ] 
#        h0 = -1. * mirrorfilt(g0) # equivalent to the line above
        
    elif wavelet == None:
        g0 = np.array([ 1., 1.]) # they will be time-reversed below
        h0 = np.array([-1., 1.])
    else:
        raise ValueError("Second argument must be a valid pywt Wavelet object or a string with a valid pywt Wavelet name, or None")
  
    print("analysis low pass: ",  g0)
    print("analysis high pass: ", h0)

    ret = vigra.VigraArray((width, height, 4, nLevels), \
                            axistags=vigra.AxisTags(vigra.AxisInfo.fx, vigra.AxisInfo.fy, vigra.AxisInfo.c, vigra.AxisInfo.ft), \
                            dtype=np.complex64)

    zx_0 = np.exp(1j * twopi * np.linspace(0, 1, width,  endpoint=False)) # 0 .. 2 * pi
    zy_0 = np.exp(1j * twopi * np.linspace(0, 1, height, endpoint=False))
  
    # see comments in fft_dec
    for k in range(nLevels):
        zexp = np.power(2.0, k)

        zx = np.power(zx_0, -zexp) 
        zy = np.power(zy_0, -zexp)

        # 1D transfer functions
        # low pass
        Lx = np.polyval(g0[::-1, ], zx) # time reversal done here
        Ly = np.polyval(g0[::-1, ], zy) #      and here

        # high pass -- use this code when using h0 given by pywt
        Hx = np.polyval(h0[::-1, ], zx) # time reversal done here
        Hy = np.polyval(h0[::-1, ], zy)

        LL = vigra.VigraArray(np.tile(Ly, (width, 1)) * np.tile(Lx, (height, 1)).T, \
                              axistags=vigra.AxisTags(vigra.AxisInfo.fx, vigra.AxisInfo.fy))
        
        HL = vigra.VigraArray(np.tile(Hy, (width, 1)) * np.tile(Lx, (height, 1)).T, \
                              axistags=vigra.AxisTags(vigra.AxisInfo.fx, vigra.AxisInfo.fy))
        
        LH = vigra.VigraArray(np.tile(Ly, (width, 1)) * np.tile(Hx, (height, 1)).T, \
                              axistags=vigra.AxisTags(vigra.AxisInfo.fx, vigra.AxisInfo.fy))
        
        HH = vigra.VigraArray(np.tile(Hy, (width, 1)) * np.tile(Hx, (height, 1)).T, \
                              axistags=vigra.AxisTags(vigra.AxisInfo.fx, vigra.AxisInfo.fy))

        # premultiply with approximation at prev level if k > 0
        if k > 0:
            LL = LL * ret[:,:,0,k-1]
            HL = HL * ret[:,:,0,k-1]
            LH = LH * ret[:,:,0,k-1]
            HH = HH * ret[:,:,0,k-1]

        ret[:,:,0,k] = LL
        ret[:,:,1,k] = HL
        ret[:,:,2,k] = LH
        ret[:,:,3,k] = HH

    return ret


def purelet_theta_analytic(x,y,thetaParams):
    '''
    PURE-LET Thresholding function for decomposition coefficients
    
    SYNTAX:

                [t, d1t2_dx, d1t2_dy, d1t2_dxdy, d2t2_dx, d2t2_dy]=...
                purelet_theta_analytic(x,y,thetaParams)

    INPUTS:
    x, y       = wavelet and scaling (or GDC) coefficients, respectively
    thetaParams = list of 5 elements:
        v          = variance of AWGN
        b          = scale-dependent factor (2^(-j/2))
        r,p,k      = theta function parameters (see Luisier et al 2011)
    
    implements
    
    t = x * exp(-(x/(r*t(w)))^p)  

    where :
        t(w) = sqrt(b * w + v), 

        w = y * tanh( k * y ) and k=100, a differentiable approximation of abs(y)
      
        with r = 3 and p = 8 (typically)
      
    the corresponding derivatives of the theta functions will be taken with
    respect to w (which approximates |y|) and NOT to y itself !!!
      
    Reference:
    
    Luisier, F., T. Blu, and M. Unser. 2011. Image denoising in mixed
    Poisson-Gaussian noise. IEEE Trans. Image Process. 20:696?708.
    
    Copyright 2011-2015 by Cezar M. Tigaret <Cezar.Tigaret@bristol.ac.uk>

    '''
# TODO: code refactoring:
#    1. do not return the unthresholded coefficients in theta_1   
#    2. do not work with vectors anymore, just use 2D matrices
#    3. derivatives for theta_1 are always the same, (ones and zeros) 
#       so don't bother with them anymore; instead factor them altogether out 
#       of the pyramid algorithm in fft_purelet
    
#    print("purelet_theta_analytic: x.shape = ", x.shape)
    tol = 1e-6

    #print(thetaParams)
  
    ky = thetaParams[4] * y
  
    w = y * np.tanh(ky) # smooth approximation of |y|: y * tanh(k*y)
    
    # tw = sqrt(b * w + v)
    #tw = thetaParams[1] * (w + thetaParams[0]) + tol # scale-dependent variance estimate: t(w) = beta * |y| + sigma^2

    tw = thetaParams[1] * w + thetaParams[0] + tol # scale-dependent variance estimate: t(w) = beta * |y| + sigma^2
  
    twsqr  = np.sqrt(tw) + tol
  
    atwsqr = thetaParams[2] * twsqr
  
    atwsqr[atwsqr == 0] = tol
  
#    print("purelet_theta_analytic: atwsqr.shape = ", atwsqr.shape)
    pexp = x / atwsqr  + tol # exponent in gT: x / (r * sqrt(t(w)))
  
    pexp[np.isnan(pexp)] = 0
    pexp[np.isinf(pexp)] = 0
  
    gTe = np.power(pexp, thetaParams[3])
  
    gT = np.exp(-gTe)
  
    t = x * gT
  
    pgTe = gTe * thetaParams[3]
  
    x[x==0] = tol
  
    bp2 = thetaParams[1] * thetaParams[3] / 2.
    b4 = np.power(thetaParams[1], 2.) / 4.
  
    gT_tw = gT / tw
  
    gT_x = gT / x
  
    x_tw = x / tw
  
    gT_tw[np.isnan(gT_tw)] = 0
    gT_tw[np.isinf(gT_tw)] = 0
  
    gT_x[np.isnan(gT_x)] = 0
    gT_x[np.isinf(gT_x)] = 0
  
    x_tw[np.isnan(x_tw)] = 0
    x_tw[np.isinf(x_tw)] = 0
  
    #print(x.size)
  
    #print(x[np.newaxis,...].T)
  
#    t = np.concatenate((x[np.newaxis,...].T, xgT[np.newaxis,...].T), axis = 1)
  
    #t = np.array((x.size,2)); # threshold functions: theta1 and theta2
    #t[:,0] = x;
    #t[:,1] = x * gT;
  
    # derivatives for theta1 -- not returned anymore as they are zeros and ones
    # first order
#    d1t1_dx = np.ones((x.size,))
#    d1t1_dy = np.zeros((x.size,))
#    d1t1_dxdy = np.zeros((x.size,))
#    # second order
#    d2t1_dx = np.zeros((x.size,))
#    d2t1_dy = np.zeros((x.size,))
  
    # derivatives for theta 2
    # first order
    dt_dx = (1 - pgTe) * gT # partial, in x
    
    dt_dy = bp2 * gT_tw * gTe * x # partial, in w (i.e. the approximation of abs(y)
    
    dt_dxdy = bp2 * gTe * gT_tw * (1 + thetaParams[3] - pgTe) # mixed partial, in x and in w
  
    # second order
    d2t_dx2  = gT_x * pgTe * (pgTe - thetaParams[3] - 1) # in x
    
    d2t_dy2  = b4 * gT_tw * x_tw * pgTe * (pgTe - thetaParams[3] - 4) # in w
  
    #print("d1t1_dx shape: ", d1t1_dx.shape)
    #print("d1t2_dx shape: ", d1t2_dx.shape)
    
#    dt_dx = np.concatenate((d1t1_dx[np.newaxis, ...].T, d1t2_dx[np.newaxis, ...].T), axis = 1)
#    dt_dy = np.concatenate((d1t1_dy[np.newaxis, ...].T, d1t2_dy[np.newaxis, ...].T), axis = 1)
  
#    dt2_dx2 = np.concatenate((d2t1_dx[np.newaxis, ...].T, d2t2_dx[np.newaxis, ...].T), axis = 1)
#    dt2_dy2 = np.concatenate((d2t1_dy[np.newaxis, ...].T, d2t2_dy[np.newaxis, ...].T), axis = 1)
  
#    dt_dxdy = np.concatenate((d1t1_dxdy[np.newaxis, ...].T, d1t2_dxdy[np.newaxis, ...].T), axis = 1)
  
    dt_dx[np.isnan(dt_dx)] = 0
    dt_dx[np.isinf(dt_dx)] = 0
  
    dt_dy[np.isnan(dt_dy)] = 0
    dt_dy[np.isinf(dt_dy)] = 0
  
    dt_dxdy[np.isnan(dt_dxdy)] = 0
    dt_dxdy[np.isinf(dt_dxdy)] = 0
  
    d2t_dx2[np.isnan(d2t_dx2)] = 0
    d2t_dx2[np.isinf(d2t_dx2)] = 0
  
    d2t_dy2[np.isnan(d2t_dy2)] = 0
    d2t_dy2[np.isinf(d2t_dy2)] = 0
  
 
    return t, dt_dx, dt_dy, dt_dxdy, d2t_dx2, d2t_dy2
  
def tiwt_dec(vigraimage, nLevels=None, wavelet=None):
    """ Translation invariant wavelet decomposition 
      using a trous algorithm
  
      Achieves perfect reconstruction within machine error
  
    """
  
      # vigraimage must be a 2D VigraArray with no channel axis
      # "L" = low-pass; "H" = high-pass; 
      #
      # in 1D stationary wavelet decomposition: 
      #	low-pass = approximation;
      # 	high-pass = detail
      #
      # in 2D stationary wavelet decomposition:
      #	approximation = filter input on BOTH dimensions (horizontal & vertical) 
      #		with the low-pass kernel (low x low)
      # 	details are:
      #		horizontal = filter dim 0 of input with low-pass kernel then 
      #			     dim 1 of input with high-pass kernel (low x high)
      #		vertical   = filter dim 0 of input with high-pass kernel then 
      #	                     dim 1 of input with low-pass (high x low)
      #		diagonal   = filter BOTH dimensions of input with high-pass kernel 
      #			     (high x high)
      #
      # at level 0 the input to the filter bank is the signal itself; 
      # for successive levels, the input is the approximation from the previous level
      
      # check we are given a 2D image devoid of channel axis (even if the latter is a singleton) 
      # so that broadcasting can take place!
  
    if vigraimage.channels > 1:
        raise ValueError("Multi-channel data not supported")
  
    if vigraimage.spatialDimensions > 2:
        if vigraimage.depth > 1:
            raise ValueError("3D data not supported")
     
    if isinstance(wavelet, str):
        wavelet = pywt.Wavelet(wavelet)
        g0 = np.array(wavelet.dec_lo)
        h0 = np.array(wavelet.dec_hi)
    elif isinstance(wavelet, pywt.Wavelet):
        g0 = np.array(wavelet.dec_lo)
        h0 = np.array(wavelet.dec_hi)
    elif wavelet == None:
        g0 = np.array([ 1., 1.])
        h0 = np.array([-1., 1.])
    else:
        raise ValueError("Second argument must be a valid pywt Wavelet object or a string with a valid pywt Wavelet name")
  
    # start with the image input
    LL = vigraimage.dropChannelAxis()
    
    if nLevels is None:
        nLevels = np.int(np.log2(min(LL.shape)))
        for k in range(nLevels-1, -1, -1):
            fl = max(len(g0) << k, len(h0) << k)
            if fl <= min(LL.shape):
                nLevels = k
                break
            
  
    # avoid per-level filter being longer than the smaller image dimension
    newMaxLevels = nLevels
  
    print('Analysis low pass FIR: ',  g0)
    print('Analysis high pass FIR: ', h0)
    
    ret = vigra.VigraArray((vigraimage.width, vigraimage.height, 4, newMaxLevels), \
                         axistags=vigra.VigraArray.defaultAxistags("xyzt"))
  
    #ret = vigra.VigraArray((vigraimage.width, vigraimage.height, 4, newMaxLevels), \
                         #axistags=vigraimage.axistags)
  
    # does dyadic a trous expansion of the kernels; 
    # at level 0 (starting level) this simply copies the values from g0, h0
    for i in range(nLevels):
        #print("level ", i)
        filterLen = len(h0) << i
    
        # avoid per-level filter being longer than the smaller image dimension
        if filterLen > min(LL.shape):
            newMaxLevels = i-1
            print("upsampled FIR at level ", i, " is longer (",filterLen,") than the smallest image dimension (", min(LL.shape),")")
            break
    
        garray = np.zeros(filterLen)
        harray = np.zeros(filterLen)
    
        for j in range(len(h0)):
            garray[j << i] = g0[j]
            harray[j << i] = h0[j]
      
        g = vigra.filters.explictKernel(0, filterLen-1, garray)
        h = vigra.filters.explictKernel(0, filterLen-1, harray)
        
        #print("g kernel: ")
        
        #for j in range(g.size()):
            #print(g[j])
            
        #print("h kernel: ")
        
        #for j in range(h.size()):
            #print(h[j])
        
        g.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        h.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        
        LH = vigra.filters.convolve(LL, (g, h)) # low/x  * high/y  => "horizontal" details
        HL = vigra.filters.convolve(LL, (h, g)) # high/x * low/y   => "vertical" details
        HH = vigra.filters.convolve(LL, (h, h)) # high/x * high/y  => "diagonal" details
    
        LL = vigra.filters.convolve(LL, (g, g)) # low/x  * low/y   => "approximation" = input for next iteration
    
        ret[:,:,0,i] = LL
        ret[:,:,1,i] = LH
        ret[:,:,2,i] = HL
        ret[:,:,3,i] = HH
    
    if newMaxLevels != nLevels:
        ret = ret.subarray((0,0,0,0), (LL.width, LL.height, 4, newMaxLevels+1))
    
    return ret

def tiwt_rec(coeffs, reclevel = None, wavelet=None):
    """ Synthesis of the image or of the approximation at level `reclevel' from 
        the set of decomposition coefficients.
        Achieves perfect reconstruction within machine error.
        
        Algorithm goes bottom-up (from the coarsest to the finest level)
    """

    if isinstance(wavelet, str):
        wavelet = pywt.Wavelet(wavelet)
        g0 = np.array(wavelet.rec_lo)
        h0 = np.array(wavelet.rec_hi)
    elif isinstance(wavelet, pywt.Wavelet):
        g0 = np.array(wavelet.rec_lo)
        h0 = np.array(wavelet.rec_hi)
    elif wavelet == None:
        g0 = np.array([1.,  1.]) / 2.0 # this is for unnormalized Haar wavelet
        h0 = np.array([1., -1.]) / 2.0
    else:
        raise ValueError("Second argument must be a valid pywt Wavelet object or a string with a valid pywt Wavelet name")
  
    print('Synthesis low pass FIR: ',  g0)
    print('Synthesis high pass FIR: ', h0)
    
#    print("shape of coeffs: ", coeffs.shape)
    
#    width, height, subbands, levels = coeffs.shape
    
    levels = coeffs.shape[coeffs.ndim-1]
    
    rec_cf = vigra.VigraArray(coeffs.shape, \
                         axistags=vigra.VigraArray.defaultAxistags("xyzt"))
                         
#    print("shape of rec_cf: ", rec_cf.shape)
  
    # start off from the highest (coarsest) approximation level
    ret = coeffs[:, :, 0, levels-1]
  
  
    len0 = len(h0)
    
    cdel = len0/2 - 1
    #cdel = 0
  
    if reclevel is None or reclevel < 0:
        reclevel = 0 # reconstruct the original data
    elif reclevel >= (levels-1):
        reclevel = levels-2 # reconstruct the approximation at the one before last level
  
    # this is a reverse iteration i.e. from the coarsest to the finest 
    # decomposition level
    for k in range(levels-1, reclevel-1, -1):
        filterLen = len0 << k # multiply by 2 to kth power
        
        delay = cdel * 2 ** k
    
        garray = np.zeros(filterLen)
        harray = np.zeros(filterLen)
        
        fLeft = int(filterLen/2 - filterLen - delay)
        fRight = int(filterLen/2 - 1 - delay)
        
        #print("level ", k, " left: ", fLeft, " right: ", fRight)
    
        for j in range(len(h0)):
            garray[j << k] = g0[j]
            harray[j << k] = h0[j]
    
        ## this achieves perfect reconstruction
        g = vigra.filters.explictKernel(fLeft, fRight, garray)
        h = vigra.filters.explictKernel(fLeft, fRight, harray)
        
        g.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        h.setBorderTreatment(vigra.filters.BorderTreatmentMode.BORDER_TREATMENT_WRAP)
        
        
        # ret here was the sum of the filtered approximation at the coarser level with the filtered
        # details at the coarser level, OR just the coarsest approximation if current level
        # is the coarsest level
        LL_ = vigra.filters.convolve(ret, (g,g)) # inverse transform for the aproximation
                                                 # at the current level by convolving it with
                                                 # the upsampled reconstruction low pass FIRs
                                                 # this assumes separable 2D convolution applies

        LH_ = vigra.filters.convolve(coeffs[:,:,1,k], (g,h))
        HL_ = vigra.filters.convolve(coeffs[:,:,2,k], (h,g))
        HH_ = vigra.filters.convolve(coeffs[:,:,3,k], (h,h))
        
        rec_cf[:,:,0,k] = LL_
        rec_cf[:,:,1,k] = LH_
        rec_cf[:,:,2,k] = HL_
        rec_cf[:,:,3,k] = HH_
    
        ret = (LL_ + LH_ + HL_ + HH_)/4
  
    return ret, rec_cf


def fft_dec(image, nLevels, wavelet = None):
    ''' Translation-invariant wavelet 2D decomposition in the Fourier domain.
    Uses orthogonal wavelets.
    
    Argments:
    data = a 2D :vigra.VigraArray:
    nLevels = int or None; maximum levels of analysis; must be 
    
    2015-06-06: 
    Achieves perfect reconstruction within machine error, using 
    default wavelet (normalized Haar), in conjunction with fft_rec.
    Because of rounding errors, the actual error between the original and
    the reconstructed image is in the order of 1e-17 (practically, zero)
    NOTE:
    Don't use vigra fourier routines, use np.fft module !!!
    Be aware that for N-dimensional arrays (e.g., volumes) np fft2/ifft2 needs to
    be applied on the innermost axes i.e., use axes = (0,1) as keyword argument
    TODO: try other (orthonormal) wavelets as well
    '''
    twopi = np.pi * 2.0
#    b0 = np.sqrt(2.0)/2.0
  
# Notations:
# g = low-pass
# h = high-pass

# g0 = the low-pass analysis FIR for level 0 -- to be dyadically  expanded a-trous in the Fourier domain
# h0 = the high-pass analysis FIR for level 0 -- to be dyadically expanded a-trous in the Fourier domain
#
# NOTE that these analysis FIRs need to be time-reversed.
# this can be done either in the time domain (i.e. when building up the np.array)
# or at the time when we construct the 1D transfer functions
#

## alternatively, when we are given only the low-pass analysis FIR g0,
## can construct h0 from g0 by mirrorfilt like so:
#h0 = -1. * mirrorfilt(g0)

    if isinstance(wavelet, str):
        wavelet = pywt.Wavelet(wavelet)
        g0 = np.array(wavelet.dec_lo) #[::-1, ] # time-reversal -- needed as explained below 
        h0 = np.array(wavelet.dec_hi) #[::-1, ] # -- moved in the loop below, when we build the per-level 1D transfer functions

    elif isinstance(wavelet, pywt.Wavelet):
        g0 = np.array(wavelet.dec_lo) #[::-1, ] # see comments above
        h0 = np.array(wavelet.dec_hi) #[::-1, ] 

    elif wavelet == None:
        g0 = np.array([ 1., 1.]) # they will be time-reversed below
        h0 = np.array([-1., 1.])
    else:
        raise ValueError("Second argument must be a valid pywt Wavelet object or a string with a valid pywt Wavelet name, or None")
  
    #print("analysis low pass: ",  g0)
    #print("analysis high pass: ", h0)

    # convolution in the natural domain equals point-wise multiplication in Fourier domain
    # notation:
    # L = low-pass 
    # H = high-pass (or, more correctly, band-pass)
    # LL, HL, LH, HH: 2D transfer functions
    # 
    #
    # at each level we generate the following transform coefficients: approx (LL), 
    # and details: horizontal (LH), vertical (HL) and diagonal (HH)
    #
    # NOTE: pre-alocated array as VigraArray for convenience (i.e., for visualization)
    # will hold 4 planes (each with the above transform coefficients) for each level, x nLevels
    ret = vigra.VigraArray((image.shape[0], image.shape[1], 4, nLevels), \
                            axistags=vigra.VigraArray.defaultAxistags('xyct'))
  
  
    # zx_0 and zy_0 are the normalized frequencies (the frequency domain) for the
    # transfer functions: they are obtained by regularly sampling the complex circle
    # corresponding to the normalized `width` and `height` respectively:
    # 
    # exp(i * 2pi * x/width) with `x` running from 0 to width-1 (i.e. normalized width), and
    #
    # exp(i * 2pi * y/height) with `y` running from 0 to height-1 (i.e., normalized height)
    #
    # with `i` being the imaginary unit i.e. the complex number <0.0, 1.0> -- 
    #       (in python (numpy) this is 1j)
    #
    zx_0 = np.exp(1j * twopi * np.linspace(0, 1, image.shape[0],  endpoint=False)) # 0 .. 2 * pi
    zy_0 = np.exp(1j * twopi * np.linspace(0, 1, image.shape[1], endpoint=False))
  
    X = np.fft.fft2(image.dropChannelAxis(), axes=(0, 1))
      
    for k in range(nLevels):
        zexp = np.power(2.0, k) # (2^k)
        
        # z^p dyadically upsamples the filter but also time-reverses it, hence
        # we compensate this by time-reversing the base FIRs (see above) from
        # which we generate the upsampled transfer functions
        
        #
        # this time-reversal results from the fact that np.polyval takes the
        # coefficients in the array in INCREASING order (like Matlab's polyval,
        # which is the opposite to the way np.polynomial package does); without
        # polyval's way of taking the coefficients in the INCREASING order, we wouldn't
        # need to reverse the array here
        #
        
        
        # in the following we calculate the (discrete) Fourier transform of the FIRs
        # thus obtaining the transfer functions; 
        
        # first we generate the vlues for the complex variable to evaluate the polynomial;
        # the polynomial coefficiets are represented by the elements in the FIR array
        
        # the argument is in fact the sampled complex circle (see above) exponentiated 
        # by a power of two which is equivalent to a dyadic upsampling of the FIR
        # (e.g. see the a trous-based algorithm in tiwt_dec and tiwt_rec)
        # Evaluating the polynomial represented by the (basic, not upsampled) FIR 
        # coefficients at this argument generates the transfer function of the
        # dyadically (a trous) upsampled FIR 
        
                                    # level (k):          0,  1,  2,  3  
        zx = np.power(zx_0, -zexp)  # z ^ -(2^k) => z ^ {-1, -2, -4, -8}
        zy = np.power(zy_0, -zexp)
        
        
        # we now evaluate the polynomial represented by the basic FIR coefficients
        # at the complex argument zx (or zy)
        
        # this is equivalent to evaluating the FIR polynomial at the argument
        # (example given for one dimension only):
        #
        # [ exp(i * 2pi * x/width) ] ^ -(2^k) = 
        #
        # exp( -(i * 2pi * x/width * 2^k) ) = 
        #
        #              1
        # -----------------------------    # for analysis, and:
        # exp( i * 2pi * x/width * 2^k )
        #
        # exp( i * 2pi * x/width * 2^k )   # for synthesis, see fft_rec
        #
    
        # 1D transfer functions
        # low pass
        Lx = np.polyval(g0[::-1, ], zx) # time reversal done here
        Ly = np.polyval(g0[::-1, ], zy) #      and here
        
        # high pass -- use this code when using h0 given by pywt
        Hx = np.polyval(h0[::-1, ], zx) # time reversal done here
        Hy = np.polyval(h0[::-1, ], zy)
        
        ##alternatively, if we have constructed h0 from g0 by mirrorfilt
        #Hx = np.polyval(h0, zx)
        #Hy = np.polyval(h0, zy)
        
    
        # 2D transfer functions = outer prod of 1D transfer functions
        LL = np.outer(Lx, Ly) # low-pass (approximations)
        HL = np.outer(Hx, Ly) # high-pass (or "band-pass" a.k.a details) horizontal
        LH = np.outer(Lx, Hy) #                                          vertical
        HH = np.outer(Hx, Hy) #                                          diagonal
        
        # obtain detail coefficients with high-pass transfer functions
        # (we need their real part)
    
        ret[:,:,1,k] = vigra.VigraArray(np.real(np.fft.ifft2(X * HL, axes=(0, 1))), \
                                        axistags=vigra.AxisTags(vigra.AxisInfo.x(), vigra.AxisInfo.y()))
                                        
        ret[:,:,2,k] = vigra.VigraArray(np.real(np.fft.ifft2(X * LH, axes=(0, 1))), \
                                        axistags=vigra.AxisTags(vigra.AxisInfo.x(), vigra.AxisInfo.y()))
                                        
        ret[:,:,3,k] = vigra.VigraArray(np.real(np.fft.ifft2(X * HH, axes=(0, 1))), \
                                        axistags=vigra.AxisTags(vigra.AxisInfo.x(), vigra.AxisInfo.y()))
    
        # obtain approximation with low-pass tansfer function, store it for the next iteration
        X = X * LL
    
        ret[:,:,0,k] = vigra.VigraArray(np.real(np.fft.ifft2(X, axes=(0, 1))), \
                                        axistags=vigra.AxisTags(vigra.AxisInfo.x(), vigra.AxisInfo.y()))
    
    return ret
    
def fft_rec(coeffs, reclevel, wavelet = None):
    '''
    # 2015-06-06: 
    # achieves perfect reconstruction within machine error, using 
    # default wavelet (normalized Haar), in conjunction with fft_dec, above
    # NOTE:
    # Don't use vigra fourier routines, use np.fft module !!!
    # Be aware that for N-dimensional arrays (e.g., volumes) np fft2/ifft2 needs to
    # be applied on the innermost axes i.e., use axes = (0,1) as keyword argument
    # TODO: try other (orthonormal) wavelets as well
    '''
    twopi = np.pi * 2.0
#    b0 = np.sqrt(2.0)/2.0
  
    if isinstance(wavelet, str):
        wavelet = pywt.Wavelet(wavelet)
        g0 = np.array(wavelet.rec_lo)
        h0 = np.array(wavelet.rec_hi)
    elif isinstance(wavelet, pywt.Wavelet):
        g0 = np.array(wavelet.rec_lo)
        h0 = np.array(wavelet.rec_hi)  
    elif wavelet == None:
        g0 = np.array([1.,  1.]) / 2.0
        h0 = np.array([1., -1.]) / 2.0
    else:
        raise ValueError("Second argument must be a valid pywt Wavelet object or a string with a valid pywt Wavelet name, or None")
  
    #print("synthesis low pass: ",  g0)
    #print("synthesis high pass: ", h0)
  
    width, height, subbands, levels = coeffs.shape
  
    if reclevel is None or reclevel < 0:
        reclevel = 0
    elif reclevel >= (levels-1) :
        reclevel = levels-2
  
    zx_0 = np.exp(1j * twopi * np.linspace(0, 1, width,  endpoint=False))# 0 .. 2 * pi
    zy_0 = np.exp(1j * twopi * np.linspace(0, 1, height, endpoint=False))
 
    # start off from the approximation at coarsest level
    X = np.fft.fft2(coeffs[:,:,0,levels-1].dropChannelAxis(), axes=(0, 1))
  
    ret_cf = vigra.VigraArray(coeffs.shape, \
                            axistags=vigra.VigraArray.defaultAxistags('xyct'))
  
    # this is a reverse iteration i.e. from the coarsest to the finest 
    # decomposition level
    for k in range(levels-1, reclevel-1, -1):
        zexp = np.power(2.0, k)      # 2^k
    
        # z^zexp dyadically upsamples the filter but also delays it
        # 
                                     # level:            0,  1,  2,  3  
        zx = np.power(zx_0, zexp)
        zy = np.power(zy_0, zexp) # z ^ (2^k) => z ^ {1,  2,  4,  8}
    
        # low pass   
        Lx = np.polyval(g0, zx)/2.0 # NO time reversal !!!
        Ly = np.polyval(g0, zy)/2.0
        # high pass
        Hx = np.polyval(h0, zx)/2.0
        Hy = np.polyval(h0, zy)/2.0

        # 2D transfer functions = outer prod of 1D transfer functions
        LL = np.outer(Lx, Ly) # low-pass (approximation)
        HL = np.outer(Hx, Ly) # high-pass (details) horizontal 
        LH = np.outer(Lx, Hy) #                     vertical
        HH = np.outer(Hx, Hy) #                     diagonal
        
        LL = LL * X

        HL = HL * np.fft.fft2(coeffs[:,:,1,k].dropChannelAxis(), axes=(0, 1))
        LH = LH * np.fft.fft2(coeffs[:,:,2,k].dropChannelAxis(), axes=(0, 1))
        HH = HH * np.fft.fft2(coeffs[:,:,3,k].dropChannelAxis(), axes=(0, 1))
        
        ret_cf[:,:,0,k] = vigra.VigraArray(np.real(np.fft.ifft2(LL)), \
                            axistags=vigra.AxisTags(vigra.AxisInfo.x(), vigra.AxisInfo.y()))
        
        ret_cf[:,:,1,k] = vigra.VigraArray(np.real(np.fft.ifft2(HL)), \
                            axistags=vigra.AxisTags(vigra.AxisInfo.x(), vigra.AxisInfo.y()))
        
        ret_cf[:,:,2,k] = vigra.VigraArray(np.real(np.fft.ifft2(LH)), \
                            axistags=vigra.AxisTags(vigra.AxisInfo.x(), vigra.AxisInfo.y()))
        
        ret_cf[:,:,3,k] = vigra.VigraArray(np.real(np.fft.ifft2(HH)), \
                            axistags=vigra.AxisTags(vigra.AxisInfo.x(), vigra.AxisInfo.y()))
        
        X = LL + LH + HL + HH
    
    # return a vigra "image"
    ret = vigra.VigraArray(np.real(np.fft.ifft2(X)), \
                           axistags=vigra.AxisTags(vigra.AxisInfo.x(), vigra.AxisInfo.y()))
    
    return ret, ret_cf

def generateData(dataSize, dirac = True):
    data = vigra.VigraArray((dataSize, dataSize), value=None, axistags=vigra.VigraArray.defaultAxistags('xy'))

    if dirac:
        data[0,0] = 1
    else:
        for k in range(min(data.width, data.height)):
            data[k,k] = 1
            
    return data


def runTests(data):
    wavename = "db1" # normalized Haar
    #wavename = 'db3' 
    #wavename = 'db2' 
    rtol = 1e-5
    atol = 1e-5
    levels = 6

    datahat = fft_purelet(data, levels, sigma2=0., wavelet=wavename, thr=3)
    datahat_tiwt = tiwt_purelet(data, levels, sigma2=0., wavelet=wavename, thr=3)
    return datahat, datahat_tiwt
