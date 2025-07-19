# src/product_finder/core_logic/embedding.py
from typing import Dict

from .. import config

# Models are now managed centrally by the application state

def build_embedding_text(product: dict) -> str:
    """
    აუმჯობესებს პროდუქტის ტექსტურ აღწერას ემბედინგისთვის.
    - შლის "ხმაურიან" და ცარიელ მონაცემებს.
    - ქმნის ერთიან, სუფთა ტექსტს.
    - ფასს არ რთავს, რადგან ის სემანტიკური მახასიათებელი არაა.
    """
    if not isinstance(product, dict):
        return ""

    title = product.get('title', '').strip()
    category = product.get('category', '').strip()
    
    text_parts = [f"სათაური: {title}", f"კატეგორია: {category}"]

    specs = product.get('specs', {})
    if isinstance(specs, dict):
        spec_list = []
        for key, value in specs.items():
            # ვამოწმებთ, რომ მნიშვნელობა არ არის ცარიელი ან ტირე
            if isinstance(value, str) and value.strip() and value.strip() != '-':
                cleaned_key = key.strip().replace(':', '')
                spec_list.append(f"{cleaned_key}: {value.strip()}")
        
        if spec_list:
            text_parts.append("მახასიათებლები: " + ", ".join(spec_list))

    description = product.get('description', '').strip()
    if description:
        text_parts.append(f"აღწერა: {description}")

    # ვაერთებთ წერტილით და ჰარით, რაც უკეთესია მოდელისთვის
    return ". ".join(part for part in text_parts if part)
