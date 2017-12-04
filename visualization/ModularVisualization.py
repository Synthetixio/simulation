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
            "Shape Count: 1"],
    "run_num": current model's run
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
    {
    "type": "reset",
    "run_num": reset count.
    }

    Get a given state.
    {
    "type": "get_step",
    "step": index of the step to get from,
    "run_num": reset count,
    "fps": current user fps for having a calculation buffer.
    }

    Submit model parameter updates
    {
    "type": "submit_params",
    "param": name of model parameter,
    "value": new value for 'param'.
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
import threading
import time
import copy

from visualization.UserParam import UserSettableParameter


class PageHandler(tornado.web.RequestHandler):
    """ Handler for the HTML template which holds the visualization. """
    def get(self):
        elements = self.application.visualization_elements
        for i, element in enumerate(elements):
            element.index = i
        self.render("modular_template.html", port=self.application.port,
                    model_name=self.application.model_name,
                    description=self.application.description,
                    package_includes=self.application.package_includes,
                    local_includes=self.application.local_includes,
                    scripts=self.application.js_code,
                    fps_max=self.application.fps_max,
                    fps_default=self.application.fps_default)


class SocketHandler(tornado.websocket.WebSocketHandler):
    """ Handler for websocket. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resetlock = threading.Lock()
        self.step = 0
        self.last_step_time = time.time()
        self.current_run_num = 0
        self.last_run_num = 0

    def open(self):
        """
        When a new user connects to the server via websocket create a new model
        i.e. same IP can have multiple models

        TODO: do cached check here
        """
        # self is the connection, not a single socket object
        self.model_handler = ModelHandler(
            self.application.threaded,
            self.application.model_name,
            copy.deepcopy(self.application.model_cls),
            copy.deepcopy(self.application.model_params),
            copy.deepcopy(self.application.visualization_elements),
            copy.deepcopy(self.application.model_settings)
        )
        self.model_handler.reset_model(self.current_run_num)
        if self.application.threaded:
            self.model_run_thread = threading.Thread(
                target=self.model_handler.run_model,
                args=(self.model_handler,)
            ).start()
        if self.application.verbose:
            print("Socket opened:", self)

    def collect_data_from_step(self, step, fps=None):
        """
        Get the data from the model_handler from step to step+fps*2
        """
        data = []
        while len(data) < 1:
            if fps is None:
                self.model_handler.max_calc_step = min(
                    step + self.application.calculation_buffer,
                    self.application.max_steps
                )
                data = self.model_handler.data[step:]
            else:
                self.model_handler.max_calc_step = min(
                    step + max(self.application.calculation_buffer, fps * 10),
                    self.application.max_steps
                )
                data = self.model_handler.data[step:]
        return data

    def on_message(self, message):
        """
        Receiving a message from the websocket, parse, and act accordingly.
        """
        if self.application.verbose:
            print(message, len(self.model_handler.data))
        msg = tornado.escape.json_decode(message)

        if msg["type"] == "get_steps":
            # message format: {'type':'get_steps', 'run_num':int, 'step':int, 'fps':int}
            with self.resetlock:
                # ignore old messages...
                if msg['run_num'] != self.model_handler.current_run_num:
                    return
                client_current_step = msg['step']
                if client_current_step > self.application.max_steps:
                    message = {"type": "end"}
                elif self.model_handler.threaded:
                    client_fps = msg['fps']
                    data = self.collect_data_from_step(client_current_step, client_fps)
                    message = {
                        "type": "viz_state",
                        "data": data,
                        "run_num":  self.model_handler.current_run_num
                    }
                else:
                    curr_time = time.time()
                    # added first less than just in case the time rolls back to 0...
                    # this will prevent someone spamming get_steps, to stop both repeated steps being sent,
                    # as well as clogging up the server with requests
                    if self.last_step_time < curr_time < self.last_step_time + self.application.min_step_time:
                        return
                    self.last_step_time = curr_time
                    self.model_handler.step()
                    message = {
                        "type": "viz_state",
                        "data": [self.model_handler.data[-1]],
                        "run_num": self.model_handler.current_run_num
                    }
                self.write_message(message)

        elif msg["type"] == "reset":
            # message format: {'type':'reset', 'run_num':int}
            with self.resetlock:
                self.current_run_num = msg["run_num"]
                self.model_handler.reset_model(self.current_run_num)

        elif msg["type"] == "submit_params":
            # message format: {'type':'submit_params', 'param':"str", 'value':<object>}
            param = msg["param"]
            value = msg["value"]
            self.model_handler.set_model_kwargs(param, value)

        elif msg["type"] == "get_params":
            # message format: {'type':'get_params'}
            self.write_message({
                "type": "model_params",
                "params": self.application.user_params
            })
        else:
            if self.application.verbose:
                print("Unexpected message!")

    def on_close(self):
        """When the user closes the connection destroy the model"""
        if self.application.verbose:
            print("Connection closed:", self)
        del self.model_handler
        del self


class ModelHandler:
    """
    Handle the Model data collection and resetting
    """
    model = None
    current_run_num = -1

    def __init__(self, threaded, name, model_cls, model_params, visualization_elements, model_settings):
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

        self.model_settings = model_settings

        self.resetting = False
        self.current_step = 0
        self.max_calc_step = 10

        self.running = True
        self.data = []
        self.data_lock = threading.Lock()
        self.lock = threading.Lock()

    def reset_model(self, run_num):
        """Clear old and create a new model"""
        self.resetting = True
        with self.lock:
            self.create_model()
        self.current_run_num = run_num
        self.resetting = False
        self.current_step = 0

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
        self.model = self.model_cls(model_params,
                                    self.model_settings['Fees'],
                                    self.model_settings['Agents'],
                                    self.model_settings['Havven']
                                    )
        # clear the data queue
        with self.data_lock:
            self.data = []

    def render_model(self):
        """collect the data from the model and put it in the queue to be sent for rendering"""
        visualization_state = []
        for element in self.visualization_elements:
            element_state = element.render(self.model)
            visualization_state.append(element_state)
        self.data.append((self.current_step, visualization_state))

    def step(self):
        self.model.step()
        self.render_model()
        self.current_step += 1

    def set_model_kwargs(self, key, val):
        self.model_kwargs[key] = val

    @staticmethod
    def run_model(model_handler):
        try:
            while model_handler.running:
                # allow the model to reset if it hasn't already
                # TODO: does this cause the lag?
                while model_handler.resetting:
                    time.sleep(0.02)
                # slow it down significantly if the data isn't being used
                # higher value causes lag when the page is first created
                while len(model_handler.data) > model_handler.max_calc_step:
                    time.sleep(0.02)

                with model_handler.data_lock:
                    model_handler.step()

        except Exception as e:
            print("==========-ERROR-==========")
            print(__import__('traceback').print_tb(e))
            print("Model run thread closed.")
            print("=========-END ERR-=========")
            return

    def set_model_params(self, param, value):
        if isinstance(self.model_kwargs[param], UserSettableParameter):
            self.model_kwargs[param].value = value
        else:
            self.model_kwargs[param] = value


class ModularServer(tornado.web.Application):
    """ Main visualization application. """
    verbose = True

    port = 3000  # Default port to listen on

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

    def __init__(self, settings, model_cls, visualization_elements, name,
                 model_params={}):
        """ Create a new visualization server with the given elements. """
        self.model_settings = settings
        self.port = settings['Server']['port']

        # Prep visualization elements:
        self.cached = settings['Server']['cached']  # TODO: cached data
        self.threaded = settings['Server']['threaded']
        self.visualization_elements = visualization_elements
        self.model_name = name
        self.model_cls = model_cls
        self.model_params = model_params
        self.max_steps = settings['Server']['max_steps']
        self.calculation_buffer = 16
        self.fps_max = settings['Server']['fps_max']
        self.min_step_time = 1/(self.fps_max + 5)  # give some extra buffer room, just in case
        self.fps_default = settings['Server']['fps_default']

        self.description = ""

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

        # Initializing the application itself:
        super().__init__(self.handlers, **self.settings)

    @property
    def user_params(self):
        result = {}
        for param, val in self.model_params.items():
            if isinstance(val, UserSettableParameter):
                result[param] = val.json
        return result

    def launch(self, port=None):
        """ Run the app. """
        startLoop = not tornado.ioloop.IOLoop.initialized()
        if port is not None:
            self.port = port
        url = 'http://127.0.0.1:{PORT}'.format(PORT=self.port)
        print('Interface starting at {url}'.format(url=url))
        self.listen(self.port)
        tornado.autoreload.start()
        if startLoop:
            tornado.ioloop.IOLoop.instance().start()
