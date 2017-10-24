# -*- coding: utf-8 -*-
"""
ModularServer
=============

A visualization server which renders a model via one or more elements.

The concept for the modular visualization server as follows:
A visualization is composed of VisualizationElements, each of which defines how
to generate some visualization from a model instance and render it on the
client. VisualizationElements may be anything from a simple text display to
a multilayered HTML5 canvas.

The actual server is launched with one or more VisualizationElements;
it runs the model object through each of them, generating data to be sent to
the client. The client page is also generated based on the JavaScript code
provided by each element.

This file consists of the following classes:

VisualizationElement: Parent class for all other visualization elements, with
                      the minimal necessary options.
PageHandler: The handler for the visualization page, generated from a template
             and built from the various visualization elements.
SocketHandler: Handles the websocket connection between the client page and
                the server.
ModularServer: The overall visualization application class which stores and
               controls the model and visualization instance.


ModularServer should *not* need to be subclassed on a model-by-model basis; it
should be primarily a pass-through for VisualizationElement subclasses, which
define the actual visualization specifics.

For example, suppose we have created two visualization elements for our model,
called canvasvis and graphvis; we would launch a server with:

    server = ModularServer(MyModel, [canvasvis, graphvis], name="My Model")
    server.launch()

The client keeps track of what step it is showing. Clicking the Step button in
the browser sends a message requesting the viz_state corresponding to the next
step position, which is then sent back to the client via the websocket.

The websocket protocol is as follows:
Each message is a JSON object, with a "type" property which defines the rest of
the structure.

Server -> Client:
    Send over the model state to visualize.
    Model state is a list, with each element corresponding to a div; each div
    is expected to have a render function associated with it, which knows how
    to render that particular data. The example below includes two elements:
    the first is data for a CanvasGrid, the second for a raw text display.

    {
    "type": "viz_state",
    "data": [{0:[ {"Shape": "circle", "x": 0, "y": 0, "r": 0.5,
                "Color": "#AAAAAA", "Filled": "true", "Layer": 0,
                "text": 'A', "text_color": "white" }]},
            "Shape Count: 1"]
    }

    Informs the client that the model is over.
    {"type": "end"}

    Informs the client of the current model's parameters
    {
    "type": "model_params",
    "params": 'dict' of model params, (i.e. {arg_1: val_1, ...})
    }

Client -> Server:
    Reset the model.
    TODO: Allow this to come with parameters
    {
    "type": "reset"
    }

    Get a given state.
    {
    "type": "get_step",
    "step:" index of the step to get.
    }

    Submit model parameter updates
    {
    "type": "submit_params",
    "param": name of model parameter
    "value": new value for 'param'
    }

    Get the model's parameters
    {
    "type": "get_params"
    }

"""
import os
import tornado.autoreload
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.escape
import tornado.gen
import webbrowser
import threading
import queue
import time

from visualization.UserParam import UserSettableParameter

# Suppress several pylint warnings for this file.
# Attributes being defined outside of init is a Tornado feature.
# pylint: disable=attribute-defined-outside-init


class VisualizationElement:
    """
    Defines an element of the visualization.

    Attributes:
        package_includes: A list of external JavaScript files to include that
                          are part of the Mesa packages.
        local_includes: A list of JavaScript files that are local to the
                        directory that the server is being run in.
        js_code: A JavaScript code string to instantiate the element.

    Methods:
        render: Takes a model object, and produces JSON data which can be sent
                to the client.

    """

    package_includes = []
    local_includes = []
    js_code = ''
    render_args = {}

    def __init__(self):
        pass

    def render(self, model):
        """ Build visualization data from a model object.

        Args:
            model: A model object

        Returns:
            A JSON-ready object.

        """
        return "<b>VisualizationElement goes here</b>."

# =============================================================================
# Actual Tornado code starts here:


class PageHandler(tornado.web.RequestHandler):
    """ Handler for the HTML template which holds the visualization. """

    def get(self):
        elements = self.application.visualization_elements
        for i, element in enumerate(elements):
            element.index = i
        self.render("modular_template.html", port=self.application.port,
                    model_name=self.application.model_handler.model_name,
                    description=self.application.model_handler.description,
                    package_includes=self.application.package_includes,
                    local_includes=self.application.local_includes,
                    scripts=self.application.js_code)


class SocketHandler(tornado.websocket.WebSocketHandler):
    """ Handler for websocket. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resetlock = threading.Lock()
        self.step = 0

    def open(self):
        if self.application.verbose:
            print("Socket opened!")

    def check_origin(self, origin):
        return True

    @property
    def viz_state_message(self):
        if self.application.threaded:
            with self.resetlock:
                # block=True makes the program wait for data to be added
                data = self.application.model_handler.data_queue.get(block=True)
                return {
                    "type": "viz_state",
                    "step": self.step,
                    "data": data[1]
                }
        else:
            self.application.model_handler.step()
            data = self.application.model_handler.render_model()
            return {
                "type": "viz_state",
                "step": self.step,
                "data": data[1]
            }

    def on_message(self, message):
        """
        Receiving a message from the websocket, parse, and act accordingly.
        """
        if self.application.verbose:
            print(message, self.application.model_handler.data_queue.qsize())
        msg = tornado.escape.json_decode(message)

        if msg["type"] == "get_step":
            if not self.application.model_handler.running:
                self.write_message({"type": "end"})
            else:
                if self.application.threaded:
                    while self.application.model_handler.resetting:
                        time.sleep(0.05)
                # self.application.model_handler.step()
                message = self.viz_state_message
                self.write_message(message)
                self.step += 1

        elif msg["type"] == "reset":
            # on_message is async, so lock here as well when resetting
            with self.resetlock:
                # calculate the step here, so it doesn't skip TODO: check why it skips
                self.step = 1
                self.application.reset_model()
            self.write_message(self.viz_state_message)
            self.step += 1

        elif msg["type"] == "submit_params":
            param = msg["param"]
            value = msg["value"]

            # Is the param editable?
            if param in self.application.user_params:
                self.application.model_handler.set_model_kwargs(param, value)

        elif msg["type"] == "get_params":
            self.write_message({
                "type": "model_params",
                "params": self.application.user_params
            })

        else:
            if self.application.verbose:
                print("Unexpected message!")


class ModelHandler:
    """
    Handle the Model data collection and resetting
    """
    def __init__(self, threaded, name, model_cls, model_params, visualization_elements):
        self.threaded = threaded
        self.model_name = name
        self.model_cls = model_cls
        self.description = 'No description available'
        self.visualization_elements = visualization_elements
        if hasattr(model_cls, 'description'):
            self.description = model_cls.description
        elif model_cls.__doc__ is not None:
            self.description = model_cls.__doc__
        self.model_kwargs = model_params
        self.resetting = False

        self.running = True
        self.data_queue = queue.Queue()
        self.lock = threading.Lock()

    def reset_model(self):
        if self.threaded:
            self.resetting = True
            with self.lock:
                self.create_model()
            self.resetting = False
        else:
            self.create_model()

    def create_model(self):
        """Create a new model, with changed parameters"""
        model_params = {}
        for key, val in self.model_kwargs.items():
            if isinstance(val, UserSettableParameter):
                if val.param_type == 'static_text':  # static_text is never used for setting params
                    continue
                model_params[key] = val.value
            else:
                model_params[key] = val

        self.model = self.model_cls(**model_params)
        # clear the data queue
        with self.data_queue.mutex:
            self.data_queue.queue.clear()
            self.data_queue.all_tasks_done.notify_all()
            self.data_queue.unfinished_tasks = 0

    def render_model(self):
        """collect the data from the model and put it in the queue to be sent for rendering"""
        visualization_state = []
        for element in self.visualization_elements:
            element_state = element.render(self.model)
            visualization_state.append(element_state)

        return self.model.time-1, visualization_state

    def step(self):
        self.model.step()

    def set_model_kwargs(self, key, val):
        self.model_kwargs[key] = val


class ModularServer(tornado.web.Application):
    """ Main visualization application. """
    verbose = True

    port = 8521  # Default port to listen on

    # Handlers and other globals:
    page_handler = (r'/', PageHandler)
    socket_handler = (r'/ws', SocketHandler)
    static_handler = (r'/static/(.*)', tornado.web.StaticFileHandler,
                      {"path": os.path.dirname(__file__) + "/templates"})
    local_handler = (r'/local/(.*)', tornado.web.StaticFileHandler,
                     {"path": ''})

    handlers = [page_handler, socket_handler, static_handler, local_handler]

    settings = {"debug": True,
                "autoreload": False,
                "template_path": os.path.dirname(__file__) + "/templates"}

    EXCLUDE_LIST = ('width', 'height',)

    def __init__(self, threaded, model_cls, visualization_elements, name="Mesa Model",
                 model_params={}):
        """ Create a new visualization server with the given elements. """
        # Prep visualization elements:
        self.threaded = threaded
        self.visualization_elements = visualization_elements
        self.package_includes = set()
        self.local_includes = set()
        self.js_code = []
        for element in self.visualization_elements:
            for include_file in element.package_includes:
                self.package_includes.add(include_file)
            for include_file in element.local_includes:
                self.local_includes.add(include_file)
            self.js_code.append(element.js_code)

        # Initializing the model
        self.model_handler = ModelHandler(threaded, name, model_cls, model_params, visualization_elements)
        self.model_handler.create_model()
        if self.threaded:
            threading.Thread(target=self.run_model, args=(self.model_handler,)).start()

        # Initializing the application itself:
        super().__init__(self.handlers, **self.settings)

    @property
    def user_params(self):
        result = {}
        for param, val in self.model_handler.model_kwargs.items():
            if isinstance(val, UserSettableParameter):
                result[param] = val.json
        return result

    def reset_model(self):
        """ Reinstantiate the model object, using the current parameters. """
        self.model_handler.reset_model()

    def set_model_params(self, param, value):
        if isinstance(self.model_handler.model_kwargs[param], UserSettableParameter):
            self.model_handler.model_kwargs[param].value = value
        else:
            self.model_handler.model_kwargs[param] = value

    def launch(self, port=None):
        """ Run the app. """
        startLoop = not tornado.ioloop.IOLoop.initialized()
        if port is not None:
            self.port = port
        url = 'http://127.0.0.1:{PORT}'.format(PORT=self.port)
        print('Interface starting at {url}'.format(url=url))
        self.listen(self.port)
        webbrowser.open(url)
        tornado.autoreload.start()
        if startLoop:
            tornado.ioloop.IOLoop.instance().start()

    @staticmethod
    def run_model(model_handler):
        try:
            while model_handler.running:
                # allow the model to reset if it hasn't already
                if model_handler.resetting:
                    time.sleep(0.1)
                    continue

                # slow it down significantly if the data isn't being used
                # higher value causes lag when the page is first created
                if model_handler.data_queue.qsize() > 50:
                    time.sleep(0.5)
                start = time.time()

                with model_handler.lock:
                    model_handler.step()
                    data = model_handler.render_model()
                    model_handler.data_queue.put(data)

                end = time.time()
                # if calculated faster than 33 step/sec allow it some time to sleep
                if end - start < 0.03:
                    time.sleep(end-start)
        except Exception as e:
            print(e)
            print("Model run thread closed.")
            return
