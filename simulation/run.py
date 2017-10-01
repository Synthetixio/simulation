"""run.py: main entrypoint for the Havven simulation."""
import server

S = server.make_server()
S.port = 8521
S.launch()
