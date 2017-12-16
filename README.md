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

There are three major components to this simulation:

* The currency environment of Havven itself;
* A virtual exchange to go between nomins, havvens, and fiat;
* The agents themselves. possible future players:
    - [x] random players
    - [x] arbitrageurs
    - [x] havven bankers
    - [x] central bankers
    - [x] merchants / consumers
    - [x] market makers
    - [x] day-trading speculators
    - [ ] buy-and-hold speculators
    - [ ] cryptocurrency refugees
    - [ ] attackers

## Technicals
It runs on [Mesa](https://github.com/projectmesa/mesa), and includes the following files and folders:

* `run.py` - the main entry point for the program
* `server.py` - the simulation and visualisation server are instantiated here
* `orderbook.py` - an order book class for constructing markets between the three main currencies
* `model.py` - the actual ABM of Havven itself
* `stats.py` - statistical functions for examining interesting economic properties of the Havven model
* `managers/` - helper classes for managing the Havven model's various parts
* `agents/` - economic actors who will interact with the model and the order book
* `test/` - the test suite
* `visualization/` - facilities for producing a live visualization web page
* `experiments.ipynb` - an environment for exploring system dynamics and scenarios in a more-efficient offline fashion.
