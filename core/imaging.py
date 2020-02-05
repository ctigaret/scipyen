"""Routines for image acquisition and laser scanning
"""

def cartesian_scan_angle_coordinate_transform(xy, wh, fast_slow_multiplier, theta, shift, zeta, fwd=True):
    """cartesian_scan_angle_coordinate_transform
    
    Transforms the coordinates of a point, between the Cartesian coordinate system
    (<x,y>) of an image and the scanning angle coordinate system (<fast,slow>) of
    the raster scanning device of the microscope. 
     
    For images, the Cartesian coordinate system is the first quadrant of a
    left-handed Cartesian reference system (with origin at top-left). The extent
    of the system's field of view is given by the image's dimensions.
     
    The scanning angle coordinate system represents a point as the ordered pair of
    the deflection angles of the fast and slow scanners (e.g., galvanometric
    mirrors). Physically, the extent of the scanning angle coordinate system is
    limited to the scanning angle range reference of the scanners, to either side
    of the coordinates' origin:
     
    maxScanAngleFast = 2 * scanAngularRangeReferenceFast
     
    maxScanAngleSlow = 2 * scanAngularRangeReferenceSlow
     
    % SYNTAX: 
    % 
    % [result] = csct(xy, fSize, sAM, theta, sShift, zF, sARR, fwd)
    % 
    % INPUTS: -- all inputs are numeric, except for the optional `fwd' which is
    %            logical, scalar.
    % 
    % xy    Nx2 matrix for N coordinates, where each row is an ordered pair,
    %       representing a Cartesian coordinate <x,y> in the case of Cartesian to
    %       angular transform, or an angular coordinate <psi, sigma> in the case of
    %       angular to Cartesian transform. 
    % 
    % fSize  an ordered pair with the <width, height> of the image where the
    %        Cartesian coordinates are defined. NOTE: this is the reversed order of
    %        what Matlab's function `size' returns.  
    % 
    %        for a matrix `I':         fSize = fliplr(size(I))
    % 
    % sAM    the scan angle multiplier given as ordered pair <fast, slow>
    % 
    % theta  scalar - the scan rotation angle (in degrees)
    %
    % sShift the scan angular shift given as the ordered pair <fast, slow>
    % 
    % zeta   scalar - the zoom factor; according to ScanImage documentation website:
    %                 "a factor by which both the Scan Amplitude X and Scan
    %                 Amplitude Y values are reduced during the scan
    % 
    % sARR   scan angular reference range given as the ordered pair <fast, slow> 
    % 
    % fwd   logical scalar, optional (default, true): when true, csct calculates the
    %       the forward (Cartesian to scan-angular) transform; otherwise, csct
    %       calculates the reverse (scan-angular to Cartesian) transform.
    % 
    % 
    % OUTPUTS: (numeric)
    % 
    % result: Nx2 matrix for N coordinates, where each row is the ordered pair of an
    %         angular coordinate when `fwd' is `true', or Cartesian coordinate (e.g.
    %         pixels) when `fwd' is `false'.
    %

    """
    
    xi_gamma = [_x_/_s_ - 0.5 for (_x_,_s_) in zip(xy, wh)]
