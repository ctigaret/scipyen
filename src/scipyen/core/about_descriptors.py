    # NOTE: 2024-08-02 22:14:19
    # the 'neo' model — from baseneo (documentation)
    # :_necessary_attrs: A list of tuples containing the attributes that the
    #                    class must have. The tuple can have 2-4 elements.
    #                    The first element is the attribute name.
    #                    The second element is the attribute type.
    #                    The third element is the number of  dimensions
    #                    (only for numpy arrays and quantities).
    #                    The fourth element is the dtype of array
    #                    (only for numpy arrays and quantities).
    #                    This does NOT include the attributes holding the
    #                    parents or children of the object.
    #
    #
    # Descriptors that contain POD types (int, str, float, datetime) the specification is:
    #   (str, type) ↔ (name, value type)
    #
    # Descriptors that contain numpy ndarray types, the specification is as below:
    # 1) pq.Quantity:
    #   (str, <type>¹, int) ↔ (name, pq.Quantity¹, ndim²)
    #
    #   ¹ in most cases this is pq.Quantity; it can also be a tuple of types, 
    #       containing subclasses of pq.Quantity for increased stringency, see 
    #       'view.py' example further below
    #
    #
    #   ² ndim can be:
    #       0 for scalar Quantity objects; 
    
    #       1 for signal-like objects ("vectors") (this doesn't seem to be enforced,
    #           as one can set the data to a 2D array, where each "column vector" 
    #           can be considered a "channel", although I think the authors' 
    #           intention was to have one channel/signal i.e. one 1D array)
    #       (vectors), whereas 
    #
    #       3 in the case of:
    #           • image data in imagesequence, where the data is supposed to be 
    #               a "sequence" of 2D planes (hence 3D)
    #           • waveforms in spiketrain, where data is supposed to be:
    #               spike (axis 0), channel (axis 1) and spike time domain (axis 3)
    #               (each spike occurs at the spike time stamp in the spiketrain)
    #
    # 2) (generic) numpy ndarray (pn.ndarray):
    #   (str, <type>³, int, np.dtype) ↔ (name, np.ndarray, ndim, dtype c'tor⁴)
    #
    #   ³ always np.ndarray
    #
    #   ⁴ e.g. np.dtype('U'), np.dtype('i') — see 'view.py' example below
    #
    # and here are some examples:
    #   (str, tuple of types, int)
    #
    # from 'baseneo.py':
    # _necessary_attrs = ()
    # _recommended_attrs = (('name', str),
    #                        ('description', str),
    #                        ('file_origin', str))
    #
    # from 'block.py':
    # _recommended_attrs = ((('file_datetime', datetime),
    #                        ('rec_datetime', datetime),
    #                        ('index', int)) +
    #                       Container._recommended_attrs)
    #
    #
    # from 'analogsignal.py':
    # _necessary_attrs = (('signal', pq.Quantity, 2),
    #                     ('sampling_rate', pq.Quantity, 0),
    #                     ('t_start', pq.Quantity, 0))
    #
    #
    # from 'view.py':
    # _necessary_attrs = (
    #     ('index', np.ndarray, 1, np.dtype('i')),
    #     ('obj', ('AnalogSignal', 'IrregularlySampledSignal'), 1)
    # )
    #
    # from imagesequence
    # _necessary_attrs = (
    #     ("image_data", pq.Quantity, 3),
    #     ("sampling_rate", pq.Quantity, 0),
    #     ("spatial_scale", pq.Quantity, 0),
    #     ("t_start", pq.Quantity, 0),
    # )
    
    # NOTE: 2024-08-02 22:16:27 
    # Let's augment this with a fifth element - the default value'
    
    # therefore we need to specify:
    # str: descriptor name
    # type or tuple of types: descriptor value type
    # int: ()

  
