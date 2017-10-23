"""run.py: main entrypoint for the Havven simulation."""
from mesa.visualization.ModularVisualization import ModularServer
import server

S: ModularServer = server.make_server(threaded=False)
S.port = 8521
S.launch()
