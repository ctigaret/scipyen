def guess_init_two_exp_sum(x:np.ndarray, y:np.ndarray, is_sorted:bool=True):
    r"""y ( x ) = a + b exp( p x ) + c exp( q x)
    Returns:
    WARNING: Work in progress, DO NOT USE
    ========
    4-tuple: (a, b, p, c, q)
    """
    # 4-tuple: (b, p, c, q)
    x,y = skg_preprocess(x,y,is_sorted)
    # ### params to optimize: b, p, c, q
    # ### params to optimize: a, b, p, c, q NOTE: 2025-05-12 10:07:03 - Lecca … Scarpa (2021) Math Meth Appl Sci 44: 10154 — 10171
    
    # see NOTE: 2025-05-12 10:07:03
    # ###  ⃗θ = (a, b, c, p, q)
    # ### y( ⃗θ;t ) = A⋅SS(t) + B⋅S(t) + C⋅t + D = a + b⋅exp(pt) + c⋅exp(qt)
    # ### with A = pq; B = (p+q)
    #
    # ### but in Jacquelin's Double exponential regression paper:
    # ### y(b, p, c, q; t) = -A⋅SS(t) + B⋅S(t) + C⋅t + D = b⋅exp(pt) + c⋅exp(qt)
    # ### with A = -pq; B = -(p+q) !!!
    
    #                    ₙ₋₁
    # all sums below are  Σ ⋅
    #                    ⁱ⁼⁰
    
    # also, REMEMBER in numpy x @ y is np.dot(x,y) whebn both x, y are 1D vectors of compatible shapes
    s = np.zeros(y.shape)
    s[1:] = np.cumsum(0.5* np.diff(x) * (y[1:] + y[:-1])) # mid-point approximation (mid-point rule less error term f``(0.5*(xₖ - xₖ₋₁))(xₖ - xₖ₋₁)³/24)
    
    ss = np.zeros(y.shape)          # SS in Lecca et al, and in Jacquelin
    ss[1:] = np.cumsum(0.5* np.diff(x) * (s[1:] + s[:-1]))
    
    xx   = x  * x
    Σssₖ2 = np.dot(S2, S2)            # Σ(S2ᵢ*S2ᵢ)    = Σ(S2ᵢ²)
    Σssₖsₖ  = np.dot(S2, S)             # Σ(S2ᵢ*Sᵢ) 
    Σssₖxₖ = np.dot(S2, x)             # Σ(S2ᵢ*xᵢ)
    S2x2 = np.dot(S2, x**2)          # Σ(S2ᵢ*xᵢ²)    Lecca et al 2021
    Σssₖyₖ  = np.dot(S2, y)             # Σ(S2ᵢ*yᵢ)
    SS   = np.dot(S, S)              # Σ(Sᵢ²)
    Sx   = np.dot(S, x)              # Σ(Sᵢ*xᵢ)    
    Sx2  = np.dot(S, xx)             # Σ(Sᵢ*xᵢ²)     Lecca et al 2021
    Sy   = np.dot(S, y)              # Σ(Sᵢ*yᵢ)
    Σx2  = np.dot(x, x)              # Σ(xᵢ²)        Lecca et al 2021
    Σx3  = np.dot(xx, x)             # Σ(xᵢ³)        Lecca et al 2021
    Σx4  = np.dot(xx, xx)            # Σ(xᵢ⁴)        Lecca et al 2021
    xy   = np.dot(x, y)              # Σ(xᵢ*yᵢ) = np.dot(x, y)
    x2y  = np.dot(xx, y)             # Σ(xᵢ² * yᵢ)   Lecca et al 2021
    ΣS   = S.sum()                   # Σ(Sᵢ)
    ΣS2  = S2.sum()                  # Σ(S2ᵢ)
    Σx   = x.sum()                   # Σ(xᵢ)
    Σy   = y.sum()                   # Σ(yᵢ)
    n    = x.shape[0]                # 
    
    # ### implementation of Lecca et al 2021 algorithm
    
    M = np.zeros((5,5)) # includes additive "bias"
    
                                                            #  _  NOTE: 𝑡 in Lecca is here 𝑥;                              ̅ 
    M[0,:] = [Σssₖ2,     Σssₖsₖ,    S2x2,   Σssₖxₖ,    ΣS2]        # | Σ(Sᵢ2²)      Σ(S2ᵢ*Sᵢ)    Σ(Sᵢ2*xᵢ²)   Σ(S2ᵢ*Sᵢ)     Σ(S2ᵢ) |           
    M[1,:] = [Σssₖsₖ,      SS,     Sx2,    Sx,     ΣS]         # | Σ(S2ᵢ*Sᵢ)    Σ(Sᵢ²)       Σ(Sᵢ*xᵢ²)    Σ(Sᵢ*xᵢ)      Σ(Sᵢ)  |
    M[2,:] = [S2x2,     Sx2,    Σx4,    Σx3,    Σx2]        # | Σ(S2ᵢ*xᵢ²)   Σ(Sᵢ*xᵢ²)    Σ(xᵢ⁴)       Σ(xᵢ³)        Σ(xᵢ²) |
    M[3,:] = [Σssₖxₖ,      Sx,     Σx3,    Σx2,    Σx]         # | Σ(S2ᵢ*xᵢ)    Σ(Sᵢ*xᵢ)     Σ(xᵢ³)       Σ(xᵢ²)        Σ(xᵢ)  |
    M[4,:] = [ΣS2,      ΣS,     Σx2,    Σx,     n]          # | Σ(S2ᵢ)       Σ(Sᵢ)        Σ(xᵢ²)       Σ(xᵢ)         n      |
                                                            #  ̅                                                            ̅ 
    
    Y = np.array([Σssₖyₖ,  Sy,     x2y,    Σx2,    Σy])
    
    return (M, Y)
    
    (A, B, C, D, E), *_ = linalg.lstsq(M, Y, overwrite_a = True, overwrite_b = False)
    
    print(f"A = {A}, B = {B}, C = {C}, D = {D}")
    
    sqB2A = np.sqrt(B**2 + 4*A)

    p = 0.5 * (B + sqB2A)
    q = 0.5 * (B - sqB2A)
    
    print(f"p = {p}, q = {q}")
    
    β = np.exp(p*x)
    η = np.exp(q*x)
    
    print(β, η)
    
    Σβ = β.sum()                            # Σ(βᵢ)
    Ση = η.sum()                            # Σ(ηᵢ)
    Σβη = β @ η         # np.dot(β, η)      # Σ(βᵢ * ηᵢ)
    Σβ2 = β @ β         # np.dot(β, β)      # Σ(βᵢ * βᵢ)
    Ση2 = η @ η         # np.dot(η, η)      # Σ(ηᵢ * ηᵢ)
    Σβy = β @ y         # np.dot(β, y)      # Σ(βᵢ * yᵢ)
    Σηy = η @ y         # np.dot(η, y)      # Σ(ηᵢ * yᵢ)
    
    Q = np.zeros((3,3))
    Q[0,:] = [n,  Σβ,  Ση]
    Q[1,:] = [Σβ, Σβ2, Σβη]
    Q[2,:] = [Ση, Σβη, Ση2]
    
    V = np.array([Σy, Σβy, Σηy])
    
    (a, b, c), *_ = linalg.lstsq(Q, V, overwrite_a = True, overwrite_b = False)
    
    return (a, b, p, c, q)
