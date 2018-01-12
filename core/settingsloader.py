"""
settingsloader.py

Loads settings from the settings file if it exists, otherwise generates a new
one with certain defaults.
"""
import configparser
import os.path
import copy


def get_defaults():
    settings = {
        # settings for the server/client side
        'Server': {
            # Whether to used cached results or not
            'cached': True,

            # whether to run the model in a separate thread for each socket connection
            # it runs worse with threading, so better to just leave it as false...
            'threaded': False,
            'port': 3000,
            'fps_max': 15,  # max fps for the model to run at
            'fps_default': 15,
            'max_steps': 1500  # max number of steps to generate up to
        },
        # settings concerning the model setup
        'Model': {
            'num_agents_max': 175,
            'num_agents_min': 20,
            'num_agents': 50,

            # ignore Agent Fractions, and choose random figures
            'random_agents': False,
            'continuous_order_matching': True,
        },
        # settings for everything fee related
        'Fees': {
            'fee_period': 50,
            'stable_nomin_fee_level': '0.005',  # 0 <= percentage < 1
            'stable_havven_fee_level': '0.005',  # 0 <= percentage < 1
            'stable_fiat_fee_level': '0.005',  # 0 <= percentage < 1
            'stable_nomin_issuance_fee': '0',  # 0 <= percentage < 1
            'stable_nomin_redemption_fee': '0'  # 0 <= percentage < 1
        },
        # settings for escrow, issuance, destruction, freeing of havvens/nomins
        'Mint': {
            # optimal collateralization parameters
            'copt_sensitivity_parameter': '1.0',  # strictly > 0
            'copt_flattening_parameter': 1,  # integer >= 1; i%2 == 1
            # cmax = copt * buffer_parameter
            'copt_buffer_parameter': '1.1',  # >= 1

            # minimal cmax value > 0 (model wont work with 0; should be a low value < 0.1)
            'minimal_cmax': '0.01',

            # True: nomins sold automatically/auctioned on the market when issued
            # False: nomins are given to players who issue (TODO: not implemeted)
            'non_discretionary_issuance': True,
            # if non discretionary, how off 1 is havven willing to go
            # i.e. sell nomins for 1-buffer, buy for 1+buffer
            'non_discretionary_cap_buffer': 0  # 0 <= buffer
        },
        'Agents': {
            'agent_minimum': 1,  # >= 0
            # multiplier for all agents to work with bigger numbers, rather than fractions
            'wealth_parameter': 1000,

            # Havven foundation for starting nomin issuance
            'havven_foundation_enabled': True,
            'havven_foundation_initial_c': '0.1',
            # what percentage of havvens does the foundation hold
            'havven_foundation_cut': '0.2',
        },
        # settings for the breakdown of how many of each agent exists in the model
        'AgentFractions': {
            # these are normalised to a total of 1 later
            'Arbitrageur': 3,
            'Banker': 25,
            'Randomizer': 15,
            'MaxNominIssuer': 10,
            'NominShorter': 15,
            'HavvenEscrowNominShorter': 10,
            'HavvenSpeculator': 6,
            'NaiveSpeculator': 0,
            'Merchant': 0,
            'Buyer': 6,
            'MarketMaker': 10
        },
        'Havven': {
            'havven_supply': '1000000000',  # static supply of havvens throughout the system
            'nomin_supply': '0',
            'rolling_avg_time_window': 7,
            'use_volume_weighted_avg': True,
        },
        'AgentDescriptions': {
            "Arbitrageur": "The arbitrageur finds arbitrage cycles and profits off them",
            "Banker": "The banker acquires as many Havvens for generating as many fees as" +
                      " possible, by targeting c_opt",
            "Randomizer": "The randomizer places random bids and asks on all markets" +
                          " close to the market price",
            'MaxNominIssuer': "The max nomin issuer acquires as many Havvens as they can and issues nomins" +
                              " to buy more",
            "NominShorter": "The nomin shorter sells nomins when the price is high" +
                            " and buys when they are low",
            "HavvenEscrowNominShorter": "The havven escrow nomin shorters behave" +
                                        " the same as the nomin shorters, but aquire" +
                                        " nomins through escrowing havvens",
            "HavvenSpeculator": "The havven speculator buys havvens hoping the price" +
                                " will appreciate after some period.",
            "NaiveSpeculator": "The naive speculator behaves similarly to the havven" +
                               " speculators, but does so on all the markets",
            "Merchant": "The merchant provides goods for Buyers, selling them for " +
                        "nomins. They sell the nomins back into fiat",
            "Buyer": "The buyers bring fiat into the system systematically, trading" +
                     " it for nomins, to buy goods from the merchant",
            "MarketMaker": "The market maker creates liquidity on some market in what" +
                           " they hope to be a profitable manner"
        }

    }

    from agents import player_names
    for item in player_names:
        if item not in settings['AgentDescriptions']:
            print("=====================")
            print(f'ERROR: {item} not in default settings!!')
            print("=====================")
            raise Exception

    return copy.deepcopy(settings)


def load_settings():
    settings = get_defaults()

    config = configparser.ConfigParser()
    config.optionxform = str  # allow for camelcase

    if os.path.exists("settings.ini"):
        print("Loading settings from settings.ini")
        config.read("settings.ini")
        for section in config:
            if section not in settings:
                if section is not "DEFAULT":
                    print(f"{section} is not a valid section, skipping.")
                continue
            for item in config[section]:
                if item not in settings[section]:
                    print(f"{item} is not a valid setting for {section}, skipping.")
                    continue
                if type(settings[section][item]) == str:
                    settings[section][item] = config[section][item]
                elif type(settings[section][item]) == int:
                    try:
                        settings[section][item] = config.getint(section, item)
                    except ValueError:
                        print(
                            f'''
Expected int for ({section}, {item}), got value "{config.get(section, item)}"
Using default value of: {settings[section][item]}
'''
                        )
                elif type(settings[section][item]) == bool:
                    try:
                        settings[section][item] = config.getboolean(section, item)
                    except ValueError:
                        print(
                            f'''
Expected boolean for ({section}, {item}), got value "{config.get(section, item)}"
Using default value of: {settings[section][item]}
'''
                        )
    else:
        print("No settings.ini file present, creating one with default settings.")
        for section in settings:
            config.add_section(section)
            for item in settings[section]:
                config.set(section, item, str(settings[section][item]))
        with open("settings.ini", 'w') as f:
            config.write(f)
    # make all the agent fractions floats based on max
    total = sum(settings['AgentFractions'][i] for i in settings['AgentFractions'])
    for i in settings['AgentFractions']:
        settings['AgentFractions'][i] = settings['AgentFractions'][i] / total

    return settings
