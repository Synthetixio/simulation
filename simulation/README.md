# Havven Simulation

## Running the simulation

This will be an agent-based model of the Havven system.

Before it can be run, you will need Python 3.6 or later and to install the pre-requisites with pip:

```pip3 install -r requirements.txt```

To run the simulation, invoke:

```python3 run.py```

Or, to open the experiments notebook:

```jupyter notebook experiments.ipynb```

## Overview

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
* `model.py` - The actual ABM itself is defined here;
* `orderbook.py` - An order book class for constructing markets between the three main currencies.
