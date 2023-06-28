class IndicatorCalibration(object):
    def __init__(self, name=None, Kd = None, Fmin = None, Fmax = None):
        super().__init__(self)
        
        self.name=name
        self.Kd = Kd
        self.Fmin = Fmin
        self.Fmax = Fmax
