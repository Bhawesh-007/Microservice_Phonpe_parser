import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_json_config(filepath : str , default_data : dict)-> dict:

    if os.path.exists(filepath):
     try:
        with open(filepath , 'r') as f:
            return json.load(f)
     except Exception as e:
        print(f"Error reading {filepath}: {e}. Using defaults.")
    else:
        print("file not found using defaults")
    return default_data

# Boot backend resolves categories per-user by name, not by this id map,
# so the map only needs to stay internally consistent (id lookups on this
# process) rather than in sync with any particular user's DB ids.
CATEGORY_ID_MAP = load_json_config(filepath=os.path.join(BASE_DIR, 'categories.json'), default_data={"Uncategorized": 7})
CATEGORY_POOL = list(CATEGORY_ID_MAP.keys())
# Reverse lookup (id -> name) built once, instead of re-scanning CATEGORY_ID_MAP
# on every transaction to turn a category id back into its name.
CATEGORY_NAME_BY_ID = {cat_id: name for name, cat_id in CATEGORY_ID_MAP.items()}
KNOWN_MERCHANTS = load_json_config(filepath=os.path.join(BASE_DIR, 'known_merchants.json'), default_data={})
