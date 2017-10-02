
from mesa.visualization.ModularVisualization import *

class ModularServer2(ModularServer):
    """ Main visualization application.

    Modifies Mesa's ModularServer to keep local/package includes in order they are added
    instead of keeping them in a set (randomised)
    """

    def __init__(self, model_cls, visualization_elements, name="Mesa Model",
                 model_params={}):
        """ Create a new visualization server with the given elements. """
        # Prep visualization elements:
        self.visualization_elements = visualization_elements
        self.package_includes = []
        self.local_includes = []
        self.js_code = []
        for element in self.visualization_elements:
            for include_file in element.package_includes:
                if include_file not in self.package_includes:
                    self.package_includes.append(include_file)
            for include_file in element.local_includes:
                if include_file not in self.local_includes:
                    self.local_includes.append(include_file)
            self.js_code.append(element.js_code)

        # Initializing the model
        self.model_name = name
        self.model_cls = model_cls
        self.description = 'No description available'
        if hasattr(model_cls, 'description'):
            self.description = model_cls.description
        elif model_cls.__doc__ is not None:
            self.description = model_cls.__doc__

        self.model_kwargs = model_params
        self.reset_model()

        # Initializing the tornado application itself:
        super().super().__init__(self.handlers, **self.settings)
