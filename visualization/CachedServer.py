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

import cache_handler


class CachedPageHandler(tornado.web.RequestHandler):
    """ Handler for the HTML template which holds the visualization. """
    def get(self):
        elements = self.application.visualization_elements
        for i, element in enumerate(elements):
            element.index = i
        self.render("cache_template.html", port=self.application.port,
                    model_name=self.application.model_name,
                    description=self.application.description,
                    package_includes=self.application.package_includes,
                    local_includes=self.application.local_includes,
                    scripts=self.application.js_code,
                    fps_max=self.application.fps_max,
                    fps_default=self.application.fps_default)


class CachedSocketHandler(tornado.websocket.WebSocketHandler):
    """ Handler for websocket. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resetlock = threading.Lock()
        self.step = 0
        self.last_step_time = time.time()

    def open(self):
        """
        When a new user connects to the server via websocket create a new model
        i.e. same IP can have multiple models

        """
        if self.application.verbose:
            print("Socket connection opened")

    def on_message(self, message):
        """
        Receiving a message from the websocket, parse, and act accordingly.
        """
        if self.application.verbose:
            print(message)
        msg = tornado.escape.json_decode(message)

        if msg["type"] == "get_steps":
            cache_data = self.application.cached_data_handler.get_step(msg['dataset'], msg['step'])
            if cache_data is False:
                message = {"type": "end"}
            else:
                data = [(msg['step']+1, cache_data)]

                message = {
                    "type": "viz_state",
                    "data": data,
                }
            self.write_message(message)
        elif msg["type"] == "get_datasets":
            data = self.application.cached_data_handler.get_dataset_info()
            message = {
                "type": "dataset_info",
                "data": data
            }
            self.write_message(message)
        else:
            if self.application.verbose:
                print("Unexpected message!")

    def on_close(self):
        """When the user closes the connection destroy the model"""
        if self.application.verbose:
            print("Connection closed:", self)
        del self


class CachedDataHandler:
    def __init__(self, default_settings):
        self.default_settings = default_settings
        data = cache_handler.load_saved()
        all_cached = False
        for i in cache_handler.run_settings:
            if i['name'] not in data:
                break
        else:
            all_cached = True

        if not all_cached:
            data = cache_handler.generate_new_caches(data)
            cache_handler.save_data(data)

        self.data = data

    def get_steps(self, dataset, step_start, step_end):
        if dataset in self.data and \
                0 <= step_start < step_end < len(self.data[dataset]):
            return self.data[dataset]['data'][step_start:step_end]
        return False

    def get_step(self, dataset, step):
        if dataset in self.data and 0 <= step < len(self.data[dataset]['data']):
            return self.data[dataset]['data'][step]
        return False

    def get_dataset_info(self):
        to_send = []
        for name in self.data:
            i = self.data[name]
            settings = copy.deepcopy(self.default_settings)
            for section in i["settings"]:
                if section not in settings:
                    continue
                for item in section:
                    if item in settings[section]:
                        settings[section][item] = i["settings"][section][item]
            to_send.append(
                {
                    "name": name,
                    "settings": settings,
                    "max_steps": i["max_steps"],
                }
            )
        return to_send


class CachedModularServer(tornado.web.Application):
    """ Main visualization application. """
    verbose = True

    port = 3000  # Default port to listen on

    # Handlers and other globals:
    page_handler = (r'/', CachedPageHandler)
    socket_handler = (r'/ws', CachedSocketHandler)
    static_handler = (r'/static/(.*)', tornado.web.StaticFileHandler,
                      {"path": os.path.dirname(__file__) + "/templates"})
    local_handler = (r'/local/(.*)', tornado.web.StaticFileHandler,
                     {"path": ''})

    handlers = [page_handler, socket_handler, static_handler, local_handler]

    settings = {"debug": True,
                "autoreload": False,
                "template_path": os.path.dirname(__file__) + "/templates"}

    EXCLUDE_LIST = ('width', 'height',)

    def __init__(self, settings, visualization_elements, name):
        self.port = settings['Server']['port']

        # Prep visualization elements:
        self.cached = settings['Server']['cached']
        if self.cached:
            self.cached_data_handler = CachedDataHandler(settings)
        self.threaded = settings['Server']['threaded']
        self.visualization_elements = visualization_elements
        self.model_name = name
        self.fps_max = settings['Server']['fps_max']
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
