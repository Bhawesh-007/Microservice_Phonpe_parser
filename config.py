from requests import request
import os
import json
import requests
def fetch_categories():
    try:
        response = requests.get("http://localhost:8080/api/categories", timeout=5)
        if response.status_code==200:
            return response.json()
    except Exception as e:
        print(f"Cant fetch from the api fallback to local json file")
    return load_json_config(filepath = 'categories.json ' , default_data={"Uncategorized" : 9})
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
CATEGORY_ID_MAP = fetch_categories()
CATEGORY_POOL = list(CATEGORY_ID_MAP.keys())   
KNOWN_MERCHANTS = load_json_config(filepath='known_merchants.json', default_data={})
