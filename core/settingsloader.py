"""
settingsloader.py

Loads settings from the settings file if it exists, otherwise generates a new
one with certain defaults.
"""
import json
import os.path
import copy
from decimal import Decimal as Dec


SETTINGS_FILE = "settings.json"


def get_defaults():
    settings = {
        # settings for the server
        "Server": {
            # generate and display cached results instead of generating them on the fly
            "cached": True,
            "port": 3000,
            # maximum fps for the app to run at
            "fps_max": 15,
            # default setting for fps
            "fps_default": 15,
            # limit how many steps can be generated in the non-cached version
            "cap_realtime_steps": False,
            "max_steps": 1500
        },

        "Model": {
            # Number of agents for the model to have
            "num_agents_max": 175,
            "num_agents_min": 20,
            "num_agents": 50,
            # Randomise the agent fractions
            "random_agents": False
        },

        "Market": {
            "continuous_order_matching": True
        },

        "Fees": {
            # how long between fee distributions
            "fee_period": 50,
            "nomin_issuance_fee": "0",
            "nomin_burning_fee": "0",
            # charge fees per transfer
            "transfer_fee": True,
            "transfer_fee_settings": {
                "nomin_fee_level": "0.002",
                "havven_fee_level": "0.002",
                "fiat_fee_level": "0.00"
            },
            # charge fees over time on all nomins
            "hedging_fee": False,
            "hedging_fee_settings": {
                # hedging fee will be charged per tick
                "hedge_length": 50,
                "nomin_fee_level": "0.005",
                "havven_fee_level": "0.005",
                "fiat_fee_level": "0.005"
            }
        },

        "Mint": {
            # allow burning nomins directly
            "discretionary_burning": True,
            # have a fixed cmax value
            "fixed_cmax": False,
            # if its fixed, up to what value
            "fixed_cmax_value": "0.2",
            # will the cmax value scale up with copt if its fixed
            "fixed_cmax_moves_up": False,
            # how low can cmax go
            "minimal_cmax": "0",
            # calculate and use copt for fee distribution
            "use_copt": True,
            "copt_settings": {
                "copt_sensitivity_parameter": "1.0",
                "copt_flattening_parameter": 1,
                "copt_buffer_parameter": "1.1"
            },
            # buffer on either side of issuance and burning
            # i.e. if 5%:
            #   burn nomins down to a value of 0.95
            #   issue nomins up to a value of 1.05
            "non_discretionary_cap_buffer": 0
        },

        "Havven": {
            "havven_supply": "1000000000",
            # initial supply of nomins (to help with some calculations)
            "nomin_supply": "0",
            "rolling_avg_time_window": 7,
            "use_volume_weighted_avg": True
        },

        "Agents": {
            # minimum number of each agent
            "agent_minimum": 1,
            "wealth_parameter": 1000,
            # add a havven foundation for setting initial parameters for copt
            "havven_foundation_enabled": True,
            # what value of cmax will havven use
            "havven_foundation_initial_c": "0.1",
            # what portion of all havvens does the foundation get
            "havven_foundation_cut": "0.2",

            "AgentFractions": {
                "Arbitrageur": 3,
                "Banker": 25,
                "Randomizer": 15,
                "MaxNominIssuer": 10,
                "NominShorter": 15,
                "HavvenEscrowNominShorter": 10,
                "HavvenSpeculator": 6,
                "NaiveSpeculator": 0,
                "Merchant": 0,
                "Buyer": 6,
                "MarketMaker": 20,
                "ValueHavvenBuyers": 10
            },

            "AgentDescriptions": {
                "Arbitrageur": "The arbitrageur finds arbitrage cycles and profits off them",
                "Banker": "The banker acquires as many Havvens for generating as many fees as possible, by targeting c_opt",
                "Randomizer": "The randomizer places random bids and asks on all markets close to the market price",
                "MaxNominIssuer": "The max nomin issuer acquires as many Havvens as they can and issues nomins to buy more",
                "NominShorter": "The nomin shorter sells nomins when the price is high and buys when they are low",
                "HavvenEscrowNominShorter": "The havven escrow nomin shorters behave the same as the nomin shorters, but aquire nomins through escrowing havvens",
                "HavvenSpeculator": "The havven speculator buys havvens hoping the price will appreciate after some period.",
                "NaiveSpeculator": "The naive speculator behaves similarly to the havven speculators, but does so on all the markets",
                "Merchant": "The merchant provides goods for Buyers, selling them for nomins. They sell the nomins back into fiat",
                "Buyer": "The buyers bring fiat into the system systematically, trading it for nomins, to buy goods from the merchant",
                "MarketMaker": "The market maker creates liquidity on some market in what they hope to be a profitable manner",
                "ValueHavvenBuyers": "The Value Havven Buyers wait until the value of havven utility is greater than the market price before buying",
            }
        }
    }

    from agents import player_names
    for item in player_names:
        if item not in settings['Agents']['AgentDescriptions'] or item not in settings['Agents']['AgentFractions']:
            print("=====================")
            print(f'ERROR: {item} not in default settings!!')
            print("=====================")
            raise Exception

    return copy.deepcopy(settings)


def parse_config(defaults, config):
    settings = {}
    for item in defaults:
        if item not in config:
            print(f"Warning: {item} not set in config, using default value...")
            settings[item] = defaults[item]
        elif type(defaults[item]) == dict:
            settings[item] = parse_config(defaults[item], config[item])
        elif type(defaults[item]) == int:
            settings[item] = int(config[item])
        elif type(defaults[item]) == bool:
            if type(config[item]) == bool:
                settings[item] = bool(config[item])
            elif config[item].lower() in ['true', 'false']:
                settings[item] = eval(config[item].title())
        elif type(defaults[item]) == Dec:
            try:
                settings[item] = Dec(config[item])
            except:
                print("Warning: {config[item]} is not Decimal friendly, using default value...")
                settings[item] = defaults[item]
        elif type(defaults[item]) == str:
            settings[item] = str(defaults[item])
        else:
            raise Exception(f"Error: unexpected type in defaults {type(defaults[item])}")
    return settings


def set_dec_to_str(defaults):
    settings = {}
    for item in defaults:
        if type(defaults[item]) == dict:
            settings[item] = set_dec_to_str(defaults[item])
        elif type(defaults[item]) == Dec:
            settings[item] = str(defaults[item])
        else:
            settings[item] = defaults[item]
    return settings


def load_settings():
    settings = get_defaults()

    if os.path.exists(SETTINGS_FILE):
        print(f"Loading settings from {SETTINGS_FILE}")
        with open(SETTINGS_FILE, 'r') as f:
            config = json.load(f)
        settings = parse_config(settings, config)
    else:
        print(f"No {SETTINGS_FILE} file present, creating one with default settings.")
        json_friendly = set_dec_to_str(settings)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(json_friendly, f)
    return settings
