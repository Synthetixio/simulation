"""run.py: main entrypoint for the Havven simulation."""
from mesa.visualization.ModularVisualization import ModularServer

from core import server

S: ModularServer = server.make_server()
S.launch()
