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
        "max_steps": 150,
        "settings": {
            "Model": {
                'num_agents': 100
            }
        }
    },
    {
        "name": "High number of bankers, low utilisation ratio",
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
        "name": "High number of bankers, default utilisation ratio",
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
        "name": "High number of bankers, high utilisation ratio",
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
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 125,
                "utilisation_ratio_max": 0.5
            },
            "AgentFractions": {
                "Randomizer": 100
            }
        }
    },
    {
        "name": "One of each market player",
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 0,
                "utilisation_ratio_max": 0.5
            }
        }
    },
    {
        "name": "Low number of Nomin Shorters",
        "max_steps": 1500,
        "settings": {
            "Model": {
                'num_agents': 125,
                "utilisation_ratio_max": 0.5
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
        data[item["name"]] = {"data": result, "settings": settings, "max_steps": item["max_steps"]}
        __import__('pprint').pprint([i[3] for i in data[item['name']]['data']])
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
    # _data = load_saved()
    # all_cached = False
    # for i in run_settings:
    #     if i['name'] not in _data:
    #         break
    # else:
    #     all_cached = True
    #
    # if not all_cached:
    _data = generate_new_caches({})
        # save_data(_data)
