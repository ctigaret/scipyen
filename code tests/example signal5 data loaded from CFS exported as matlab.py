data:
    
{'Average6_c01_tbs_001__wave_data': array([[(array([], dtype='<U1'), array(['s'], dtype='<U1'), array([[0]], dtype=uint8), array([[9.99999975e-05]]), array([[6500]], dtype=int32), array([[1]], dtype=int32), array([[1]], dtype=int32), array([[(array([[1]], dtype=int32), array(['ADC 0'], dtype='<U5'), array(['pA'], dtype='<U2'))]],
       dtype=[('number', 'O'), ('title', 'O'), ('units', 'O')]), array([[(array([[1]], dtype=int32), array([[6500]], dtype=int32), array([[0]], dtype=uint8), array([[0]], dtype=int32), array([[0]], dtype=int32), array([[19]], dtype=int32), array(['Basic 0'], dtype='<U7'))]],
       dtype=[('number', 'O'), ('points', 'O'), ('start', 'O'), ('state', 'O'), ('tag', 'O'), ('sweeps', 'O'), ('label', 'O')]), array([[-67.4101177 ],
        [-67.39244963],
        [-67.38441869],
        ...,
        [-67.40369295],
        [-67.41493627],
        [-67.41654245]]))]],
       dtype=[('xlabel', 'O'), ('xunits', 'O'), ('start', 'O'), ('interval', 'O'), ('points', 'O'), ('chans', 'O'), ('frames', 'O'), ('chaninfo', 'O'), ('frameinfo', 'O'), ('values', 'O')]),
 '__globals__': [],
 '__header__': b'MATLAB 5.0 MAT-file, Platform: PCWIN, Created on: Fri Jul 06 14:08:13 2018',
 '__version__': '1.0'}
       
       
wave_data = data['Average6_c01_tbs_001__wave_data']
       
wave_data:

array([[(array([], dtype='<U1'), 
         array(['s'], dtype='<U1'), 
         array([[0]], dtype=uint8), 
         array([[9.99999975e-05]]), 
         array([[6500]], dtype=int32), 
         array([[1]], dtype=int32), 
         array([[1]], dtype=int32), 
         array([[(array([[1]], dtype=int32), array(['ADC 0'], dtype='<U5'), array(['pA'], dtype='<U2'))]],
                 dtype=[('number', 'O'),     ('title', 'O'),                ('units', 'O')]), 
         array([[(array([[1]], dtype=int32), array([[6500]], dtype=int32), array([[0]], dtype=uint8), array([[0]], dtype=int32), array([[0]], dtype=int32), array([[19]], dtype=int32), array(['Basic 0'], dtype='<U7'))]],
                 dtype=[('number', 'O'),     ('points', 'O'),              ('start', 'O'),            ('state', 'O'),            ('tag', 'O'),             ('sweeps', 'O'),                  ('label', 'O')]), 
         array([[-67.4101177 ],
                [-67.39244963],
                [-67.38441869],
                ...,
                [-67.40369295],
                [-67.41493627],
                [-67.41654245]]))]],
      dtype=[('xlabel', 'O'), 
             ('xunits', 'O'), 
             ('start', 'O'), 
             ('interval', 'O'), 
             ('points', 'O'), 
             ('chans', 'O'), 
             ('frames', 'O'), 
             ('chaninfo', 'O'), 
             ('frameinfo', 'O'), 
             ('values', 'O')])
      
      
# get relevant variables as python quantities:

t_start = wave_data.["start"][0][0][0] * eval("pq.%s" % wave_data["xunits"][0][0][0])

sampling_rate = int(1/wave_data["interval"][0][0][0]) * pq.Hz # to avoid floating point errors

channel_units = eval("pq.%s" % wave_data["chaninfo"][0][0]["units"][0][0][0])

channel_data = wave_data["values"][0][0]

c01_15g28_tbs_001_average_signal = neo.AnalogSignal(channel_data, units = channel_units, t_start = t_start, sampling_rate = sampling_rate)
