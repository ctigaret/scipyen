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
    # and here are some examples:
    #
    # from analosginals
    # _necessary_attrs = (('signal', pq.Quantity, 2),
    #                     ('sampling_rate', pq.Quantity, 0),
    #                     ('t_start', pq.Quantity, 0))
    #
    #
    # from view
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

  
