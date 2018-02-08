from core import settingsloader
from core import cachehandler
import os

if __name__ == "__main__":
    x = input("Clear and refresh settings.json (y/[any])? ")
    if x.lower() in ['y', 'yes']:
        # clear current settings
        os.remove("settings.json")
        settings = settingsloader.load_settings()

    x = input("Clear and refresh cache_data.pkl (y/[any])? ")
    if x.lower() in ['y', 'yes']:
        data = cachehandler.generate_new_caches({})
        cachehandler.save_data(data)
