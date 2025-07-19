#!/usr/bin/env python3
"""
დეტალური პროდუქტის ინფორმაციის ტესტი

ეს სკრიპტი ამოწმებს API-ს მიერ დაბრუნებულ დეტალურ ინფორმაციას
"""
import requests
import json
from typing import Dict, Any

def test_detailed_product_info(query: str, max_results: int = 3):
    """ტესტის გაშვება მოცემული მოთხოვნისთვის"""
    url = "http://localhost:8000/search"
    payload = {
        "query": query,
        "max_results": max_results
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"🔍 საძიებო მოთხოვნა: '{query}'")
        print(f"📊 ნაპოვნია: {data['total_results']} პროდუქტი")
        print(f"⏱️ გამოძახების დრო: {data['response_time_ms']:.2f}ms")
        print()
        
        # კატეგორიის ინფორმაცია
        if data.get('selected_category'):
            cat = data['selected_category']
            print(f"📂 არჩეული კატეგორია: {cat['category_name']} > {cat['subcategory_name']}")
            print()
        
        # პროდუქტების დეტალური ინფორმაცია
        for i, product in enumerate(data['products'], 1):
            print(f"{'='*60}")
            print(f"📦 პროდუქტი #{i}")
            print(f"{'='*60}")
            print(f"🏷️  სახელწოდება: {product['title']}")
            print(f"💰 ფასი: {product['price']} ლარი")
            print(f"📁 კატეგორია: {product['category']}")
            print(f"🔗 ლინკი: {product.get('link', 'N/A')}")
            print(f"🖼️  სურათი: {product.get('image', 'N/A')}")
            print(f"📝 დეტალური სახელწოდება: {product.get('product_title_detail', 'N/A')}")
            
            if product.get('description'):
                print(f"📄 აღწერა: {product['description']}")
            
            # ტექნიკური მახასიათებლები
            specs = product.get('specs', {})
            if specs:
                print("\n⚙️  ტექნიკური მახასიათებლები:")
                for key, value in specs.items():
                    print(f"   • {key} {value}")
            
            print(f"\n🎯 მსგავსების ქულა: {product.get('similarity_score', 0):.3f}")
            print()
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API გამოძახების შეცდომა: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON გარჩევის შეცდომა: {e}")
        return None

def main():
    """მთავარი ფუნქცია - რამდენიმე ტესტის გაშვება"""
    test_queries = [
        "ყურსასმენი",
        "Canon კამერა", 
        "gaming laptop",
        "Xiaomi ტელეფონი"
    ]
    
    print("🚀 დეტალური პროდუქტის ინფორმაციის ტესტის დაწყება")
    print("="*80)
    
    for query in test_queries:
        print(f"\n{'='*80}")
        test_detailed_product_info(query, max_results=2)
        print("="*80)

if __name__ == "__main__":
    main()
