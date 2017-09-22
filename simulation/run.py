# Run me to simulate Havven.
import server


s = server.make_server()
s.port = 8521
s.launch()