# Implementing a way to "calibrate" the image channel data.

The channel data (actual pixel values) in an image may represent a physical 
measure rather than the mere pixel "intensity" in arbitrary units. While
axiscalibration.ChannelCalibrationData stores the physical units associated
with the "channel" axis of a VigraArray, the mathematical expression that
represents the relationship between the light intensity captured in a pixel
and the value of the physical measure at that pixel - the "calibration" itself
needs to be implemented elsewhere in Scipyen.

## NOTE: 2025-04-10 23:23:42 TODO
    
    To store the algebraic expression for the transformation of pixel intensity
    (a.u.)  into calibrated values consider:
    • py-openmath
    • openexpressions - simpler and more to the point of what I want to achieve?
      example: estimate change in [Ca²⁺]ᵢ using Kd * ΔF/F / max(ΔF/F)
          WARNING: openexpressions.Parser cannot parse expression strings containing
          unicode characters!!!
    
          notation used:
          Kd          -> 𝑲d
          x           -> ΔF/F  = (𝑭-𝑭₀)/𝑭₀
          xMax        -> max(ΔF/F) (i.e., fluorescence intensity at saturation)
    
          WARNING: background fluorescence must have been subtracted from both
              𝑭 and 𝑭₀ ‼
           
          from openexpressions.Parser import Parser
          math_parser = Parser()
          expression = math_parser.parse("Kd * x / xMax")
          this can be evaluated at a given pixel, with intensty 'x', e.g.:
          y = expression.eval({'Kd':2.5 * pq.uM, 'x': 128, 'xMax': 2048})
          -> y = array(0.625)*uM
          NOTE: quantities ARE supported by the evaluation code
    
          WARNING: for numpy arrays don't use numpy ufuncs for vectorizing; 
          just pass the array to the appripriate symbol in the call to eval, 
          e.g.:
          img1 = expression.eval({'Kd':2.5 * pq.uM, 'x': img, 'xMax': img.max()})
    
          img1 is a quantity array
    
          CAUTION: when the array in 'img' is a VigraArray, then you should create a 
          VigraArray from the resulting array, but be aware of the following:
          1) this will splice-out the quantity units
          2) you MUST supply and axistags parameter to the VigraArray constructor
          — this is the good time to apply a quantity calibration to the 
          channel axis in the axistags destined for the result!
          
    • openexpressions in conjunction with sympy (simpyfy) to perform some algebraic
      simplifications of the expression if needed
    
    • alternatives to openexpressions to consider
      ∘ https://github.com/louisfisch/mathematical-expression-parser
      ∘ pymep
      ∘ write your own parser using python's ast module

# Extract from Helmchen (2011) CSH Protocols RE: Ca²⁺ indicators

    F = Φ⋅Q_D⋅Q_F⋅α⋅𝐼₀⋅n = S⋅n 
    
where:
    
    F: 
        fluorescence intensity from an observation volume V
        
    n: 
        molar amount of dye molecules in V (i.e., number of moles in V - might 
                                            as well be the dye concentration)
        
    𝐼₀: 
        illumination intensity
    
    α: 
        dye absorption
        
    Q_F: 
        quantum yield of the dye
        
    Φ: 
        photon collection efficiency of the optical setup
        
    Q_D: 
        quantum efficiency of the detector

    S: 
        proportionality constant resulted from the multiplicaton of factors that 
        depend on dye properties or the experimental setup:
    
            S = Φ⋅Q_D⋅Q_F⋅α⋅𝐼₀
    
## For Ca²⁺ indicators:
    
    𝒏f: 
        molar amount of free indicator 
        
    𝒏b: 
        molar amount of Ca²⁺-bound indicator
        
    𝒏ₜ: 
        total molar amount of indicator = 𝒏f + 𝒏b
    
    It follows that:
        at 0 Ca²⁺ concentration: 𝒏f = 𝒏ₜ
        at saturating Ca²⁺ concentration: 𝒏b = 𝒏ₜ
    
    The bound and free indicator have different quantum yields => different "S" factors: 
    
            F   = Sf ⋅ 𝒏f + Sb ⋅ 𝒏b
                = Fmin + (Sb - Sf)/𝒏b
                = Fmax - (Sb - Sf)/𝒏f 
        
        where:
        
        Fmin = Sf ⋅ 𝒏ₜ: 
            fluorescence at 0 Ca²⁺ concentration
            
        Fmax = Sb ⋅ 𝒏ₜ: 
            fluorescence at saturating Ca²⁺ concentration
        
        assuming a fluorescence increase upon Ca²⁺ binding (i.e., bound 
        indicator has a higher quantum yield).
        
    Assuming 1:1 complexation of Ca²⁺ with the dye, the law of mass action is:

    Kd = 𝒏f ⋅ [Ca²⁺]ᵢ / 𝒏b: 
        the dissociation constant of the indicator

## Dye concentration

    Assuming all dye molecules sense the same illumination intensity (no inner 
    filtering condition):

    The intensity of light that is absorbed by a layer of fluorescent dye 
    of thickness 𝒍:

            𝑰abs =  𝑰₀(1-10ᵋˡᶜ) ≈ 𝑰₀ ln(10)ε𝒍𝒄
        
    where:
        ε: 
            molar extinction coefficient, ranging betwen 20,000-100,000 M⁻¹cm⁻¹
            
        c: 
            dye concentration
        
        The linear approximation of 𝑰abs and 𝒄 is valid for 𝒄 << [ln(10)ε𝒍]⁻¹
        
        ⟹ an upper limit of the useful dye concentration (!):
        
        • for cells with ⌀ 10 μm the concentration shoud be well below 5-20 mM
        
        • for thick cuvettes is ∼ 1 cm path length the dye should be more diluted,
        typically 1 μM
        
## Background subtraction:
    
    Background fluorescence 𝑭bkg must be subtracted from the observed fluorescence:

            𝑭 = 𝑭obs - 𝑭bkg

        before applying any conversion to [Ca²⁺]ᵢ

        𝑭bkg must be measured throughout the experiment in a slice region nearby the
        cell of interest, directly before and after the recording experiment.

    See also Chen et al 2006 In Situ Background Estimation in Quantitative Fluorescence Imaging
    
## Calibration methods:

### Single-wavelength measurements

    Maravall et al 2000:
        • suitable when small fluorescence changes are evoked AND the indicator
            is far from saturation (i.e., low affinity dye e.g.Fluo-5F)
            
        • estimate
            
            Δ[Ca²⁺]ᵢ = 𝑲d × (Δ𝑭/𝑭) / (Δ𝑭/𝑭)max
                                                condition: (Δ𝑭/𝑭) << (Δ𝑭/𝑭)max

            where:
                Δ𝑭/𝑭 = (𝑭-𝑭₀) / 𝑭₀ — typically, the pixel value in a Δ𝑭/𝑭 image
                𝑭₀ = the background-subtracted pre-stimulus fluorescence level.
                (Δ𝑭/𝑭)max — a constant obtained from imaging the flow from a
                    a pipette with known dye concentration and standard pCa
                    solutions with nominally 0 and saturating [Ca²⁺].
            

            It may be difficult to determine the saturating fluorescence changes
            for low affinity dyes.
        
    
