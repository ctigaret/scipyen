"""GUI widgets for model parameters inputs
TODO: 2022-10-28 11:32:10

GUI objects to allow editing of model parameters, upper and 
lower bound and fitting options (hooking into scipy optimize)

ModelParametersWidget - flexible widget based on model specifications
    Awaiting factoring out code in modelfitting so that a single
    object can be passed to the constructor.

    Widget is to be embedded in other dialogs, giving access to 
    values of individual parameter and bounds 
    
Also to create a ModelParametersDialog to return tuples with
model parameters, lower and upper bounds, and other fitting
options.

"""

class ModelParametersWidget():
    pass
