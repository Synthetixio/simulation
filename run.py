"""run.py: main entrypoint for the Havven simulation."""
from mesa.visualization.ModularVisualization import ModularServer
import server

# currently, threaded bool isn't used, it is always threaded...
S: ModularServer = server.make_server(threaded=True)
S.port = 3000
S.launch()
