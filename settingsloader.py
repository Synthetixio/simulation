import configparser
import os.path
import copy


def get_defaults():
    settings = {
        'Server': {
            # TODO: whether to used cached results or not
            'cached': True,

            # whether to run the model in a separate thread for each socket connection
            # it runs worse with threading, so better to just leave it as false...
            'threaded': False,
            'port': 3000,
            'fps_max': 6,  # max fps for the model to run at
            'fps_default': 3,
            'max_steps': 1500  # max number of steps to generate up to
        },
        'Model': {
            'num_agents_max': 175,
            'num_agents_min': 20,
            'num_agents': 50,

            # ignore Agent Fractions, and choose random figures
            'random_agents': False,
            'utilisation_ratio_max': '0.2',
            'continuous_order_matching': True
        },
        'Fees': {
            'fee_period': 50,
            'stable_nomin_fee_level': '0.005',
            'stable_havven_fee_level': '0.005',
            'stable_fiat_fee_level': '0.005',
            'stable_nomin_issuance_fee': '0',
            'stable_nomin_redemption_fee': '0'
        },
        'Agents': {
            'agent_minimum': 1,
            'wealth_parameter': 1000
        },
        'AgentFractions': {
            # these are normalised to total 1 later
            'Arbitrageur': 3,
            'Banker': 25,
            'Randomizer': 15,
            'NominShorter': 15,
            'HavvenEscrowNominShorter': 10,
            'HavvenSpeculator': 6,
            'NaiveSpeculator': 0,
            'Merchant': 0,
            'Buyer': 6,
            'MarketMaker': 20
        },
        'Havven': {
            'havven_supply': '1000000000',
            'nomin_supply': '0',
            'rolling_avg_time_window': 7,
            'use_volume_weighted_avg': True
        },
        'AgentDescriptions': {
            "Arbitrageur": "The arbitrageur finds arbitrage cycles and profits off them",
            "Banker": "The banker acquires as many Havvens as they can and issues nomins to buy more",
            "Randomizer": "The randomizer places random bids and asks on all markets close to the market price",
            "NominShorter": "The nomin shorter sells nomins when the price is high and buys when they are low",
            "HavvenEscrowNominShorter": "The havven escrow nomin shorters behave the same as the nomin shorters, but aquire nomins through escrowing havvens",
            "HavvenSpeculator": "The havven speculator buys havvens hoping the price will appreciate after some period.",
            "NaiveSpeculator": "The naive speculator behaves similarly to the havven speculators, but does so on all the markets",
            "Merchant": "The merchant provides goods for Buyers, selling them for nomins. They sell the nomins back into fiat",
            "Buyer": "The buyers bring fiat into the system systematically, trading it for nomins, to buy goods from the merchant",
            "MarketMaker": "The market maker creates liquidity on some market in what they hope to be a profitable manner"
        }

    }
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
        settings['AgentFractions'][i] = settings['AgentFractions'][i]/total

    return settings


if __name__ == "__main__":
    load_settings()
