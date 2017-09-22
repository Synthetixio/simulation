# Havven Simulation

This will be an agent-based model of the Havven system. To run the simulation, invoke:

```python3 run.py```

There will be three components to this simulation:

* The agents themselves; possible future players:
    * market makers
    * arbitrageurs
    * day-trading speculators
    * buy-and-hold speculators
    * merchants / citizens
    * cryptocurrency refugees
    * attackers
* The currency environment of Havven itself;
* A virtual exchange to go between `NOM`, `CUR`, and `USD`;

## Technicals
It runs on [Mesa](https://github.com/projectmesa/mesa), and includes the following files:

* `run.py` - the main entry point for the program;
* `server.py` - the simulation and visualisation server are instantiated here;
* `model.py` - The actual ABM itself is defined here.
