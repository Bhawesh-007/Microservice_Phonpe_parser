import os
import json
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
    
CATEGORY_ID_MAP = load_json_config(filepath='categories.json', default_data={"Uncategorized" : 9})
KNOWN_MERCHANTS = load_json_config(filepath='known_merchants.json', default_data={})
CATEGORY_POOL = list(CATEGORY_ID_MAP.keys())