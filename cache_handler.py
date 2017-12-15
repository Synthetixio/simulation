"""
cache_handler.py

Functions to help with loading and generating caches of model runs
given certain parameters.

This should work hand-in-hand with CachedServer to allow users to view
these cached runs, without using large amounts of server resources by
generating new data per user.
"""

import settingsloader
import model
import pickle
import tqdm

run_settings = [
    # settings for each individual run to create a cache for.
    # name: having a "Default" run is required
    #   - all names have to be unique
    # max_steps: required, and ignore whatever is in settings.ini
    # settings: change the defaults set in settings.ini, per run
    #   - any settings that are not in settings.ini are ignored
    {
        "name": "Default",
        "description": """<p>This dataset runs the simulation with the default model settings,
        viewable in <i>settings</i>.</p><p>The agent fractions selected feel like a good balance of what
        could be expected in a real system. For more information about what the actors represent, read the
        <i>About</i> section.</p>""",
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 100
            }
        }
    },
    {
        "name": "High number of bankers, low collateralisation ratio",
        "description": """<p>This dataset, along with default collateralisation
        and high collateralisation, highlight how the collateralisation ratio helps with price shocks, as well
        as controlling nomin supply.</p><p>A low collateralisation ratio max (0.1) limits the supply of nomins quite harshly
        in relation to the havven price. This forces the havven price to need rise much faster than the nomin
        price, to allow for enough nomins to be created to keep the price at 1.</p>""",
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 125,
                "utilisation_ratio_max": 0.1
            },
            "AgentFractions": {
                "Banker": 100
            }
        }
    },
    {
        "name": "High number of bankers, default collateralisation ratio",
        "description": """<p>This dataset, along with low collateralisation
        and high collateralisation, highlight how the collateralisation ratio helps with price shocks, as well
        as controlling nomin supply.</p><p>The default collateralisation ratio max (0.25)
        creates a nice balance of a supply of nomins quite harshly
        in relation to the havven price. This forces the havven price to need rise faster than the nomin
        demand, to allow for enough nomins to be created to keep the price at 1.</p>""",
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 125,
            },
            "AgentFractions": {
                "Banker": 100
            }
        }
    },
    {
        "name": "High number of bankers, high collateralisation ratio",
        "description": """<p>This dataset, along with low collateralisation
        and default collateralisation, highlight how the collateralisation ratio helps with price shocks, as well
        as controlling nomin supply.</p><p>The high collateralisation ratio max (0.5)
        allows for the issuance of a large amount of nomins, which causes the intrinsic value of havven's to skyrocket
        as the value they can issue is so high. This creates massive oversupply of nomins, killing the price</p>""",
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 125,
                "utilisation_ratio_max": 0.5
            },
            "AgentFractions": {
                "Banker": 100
            }
        }
    },
    {
        "name": "High number of randomizers",
        "description": """<p>This dataset has a lot of irrational behavior, to see how well the price stays at 1,
        even with actors not caring about their actions.</p>""",
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 125,
            },
            "AgentFractions": {
                "Randomizer": 100
            }
        }
    },
    {
        "name": "One of each market player",
        "description": """<p>This dataset just shows off 1 of each market player type that exists in the system.
        This highlights how they all interact with each other.</p>""",
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 0,
            },
            "Agents": {
                'agent_minimum': 1
            }
        }
    },
    {
        "name": "Low number of Nomin Shorters",
        "description": """<p>This dataset removes a lot of the price control the nomin shorters bring,
        to see how well the price stays at 1 without the user expectation that the price would be near 1.</p>
        <p>This will show whether controlling the supply is enough to keep the price stable.</p>""",
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 125,
            },
            "AgentFractions": {
                "NominShorter": 0,
                "HavvenEscrowNominShorter": 0
            }
        }
    },
]


def generate_new_caches(data):
    """
    generate a new dataset for each dataset that doesn't already exist in data

    overwrites the defined default settings for every run

    generate visualisation results for every step up to max_steps, and save it to 'result'

    store the result in the format:
      data["name"] = {"data": result, "settings": settings, "max_steps": max_steps}
    """
    from server import get_vis_elements

    for n, item in enumerate(run_settings):
        if item["name"] in data and len(data[item['name']]['data']) == item['max_steps']:
            print("already have:", item['name'])
            continue
        print("\nGenerating", item["name"])
        result = []
        settings = settingsloader.get_defaults()

        for section in item["settings"]:
            for i in item['settings'][section]:
                settings[section][i] = item["settings"][section][i]

        model_settings = settings['Model']
        model_settings['agent_fractions'] = settings['AgentFractions']

        havven_model = model.HavvenModel(
            model_settings,
            settings['Fees'],
            settings['Agents'],
            settings['Havven']
        )
        vis_elements = get_vis_elements()

        for i in tqdm.tqdm(range(item["max_steps"])):
            # # The following is for running the loop without tqdm
            # # as when profiling the model tqdm shows up as ~17% runtime
            # if not i % 100:
            #     print(f"{n+1}/{len(run_settings)} [{'='*(i//100)}{'-'*(item['max_steps']//100 - i//100)}" +
            #           f"] {i}/{item['max_steps']}")
            havven_model.step()
            step_data = []
            for element in vis_elements:
                if i == 0:
                    if hasattr(element, "sent_data"):
                        element.sent_data = False
                        element_data = element.render(havven_model)
                    else:
                        element_data = element.render(havven_model)
                else:
                    element_data = element.render(havven_model)
                step_data.append(element_data)

            result.append(step_data)
        data[item["name"]] = {
            "data": result,
            "settings": settings,
            "max_steps": item["max_steps"],
            "description": item["description"]
        }
    return data


def load_saved():
    try:
        with open("cache_data.txt", 'rb') as f:
            print("Loading from cache_data.txt...")
            data = pickle.load(f)
    except IOError:
        data = {}
    except EOFError:
        data = {}
    return data


def save_data(data):
    """overwrite existing cache file with the presented data"""
    with open("cache_data.txt", "wb") as f:
        pickle.dump(data, f)
    print("Caches saved to cache_data.txt")


if __name__ == "__main__":
    _data = load_saved()
    all_cached = False
    for i in run_settings:
        if i['name'] not in _data:
            break
    else:
        all_cached = True

    if not all_cached:
        _data = generate_new_caches({})
        save_data(_data)
