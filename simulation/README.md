# Havven Simulation

## Running the simulation

This will be an agent-based model of the Havven system.

Before it can be run, you will need Python 3.6 or later and to install the pre-requisites with pip:

```pip3 install -r requirements.txt```

To run the simulation, invoke:

```python3 run.py```

Or, to open the experiments notebook:

```jupyter notebook experiments.ipynb```

To run the tests:

```python3 -m pytest --pyargs -v```

Note: Running pytest through python3 is more consistent (global pytest install, other python versions).
The -v flag is for verbose, to list every individual test passing.

## Overview

There will be three components to this simulation:

* The agents themselves. possible future players:
    * market makers
    * arbitrageurs
    * day-trading speculators
    * buy-and-hold speculators
    * merchants / citizens
    * cryptocurrency refugees
    * attackers
* The currency environment of Havven itself
* A virtual exchange to go between `NOM`, `CUR`, and `USD`

## Technicals
It runs on [Mesa](https://github.com/projectmesa/mesa), and includes the following files:

* `run.py` - the main entry point for the program
* `server.py` - the simulation and visualisation server are instantiated here
* `model.py` - the actual ABM of Havven itself
* `orderbook.py` - an order book class for constructing markets between the three main currencies
* `agents.py` - economic actors who will interact with the model and the order book
* `modelstats.py` - statistical functions for examining interesting economic properties of the Havven model

## TODO

* Type annotations and mypy everywhere
* Add all necessary agents
* Speed up the simulation (jupyter line_profiler, Cython, pure-python, pypy, pandas optimisation, better algorithms)
* Make things pretty
* Run experiments
