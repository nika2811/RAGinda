# src/product_finder/utils/data_io.py
import json

def load_categories_from_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Categories file not found at '{path}'")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{path}'")
        return None

def load_products(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Scraped products file not found at '{json_path}'")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{json_path}'")
        return []