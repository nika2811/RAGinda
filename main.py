# main.py

import json
import asyncio
import os
import config  # Import the configuration file

from retriever import HybridRetriever, find_category_with_gemini_rag, load_categories_from_file
from scrapers.zoommer_scraper import zommer_scraper_for_urls
from embedder import embed_all_products, save_faiss_index, load_products, search_similar

QUERIES = [
    # "სამსუნგის საათი მინდავიყიდო",
    "ლეპტოპი მჭირდება, თან რომ თამასშებიც გამიკაჩოს",
    # "აიფონის დამტენი ხომ არ გაქვთ?",
    # "პოვერ ბანკი",
    # "ველოსიპედი"
]

async def main():
    # Use config for file path
    categories = load_categories_from_file(config.CATEGORIES_FILE)
    if not categories:
        print("❌ Categories not loaded.")
        return

    retriever = HybridRetriever(categories)
    selected_subcategories = []
    unique_urls = set()

    for query in QUERIES:
        print(f"\n🔎 Query: {query}")
        # Use config for retriever parameter
        retrieved = retriever.search(query, top_k=config.RETRIEVER_TOP_K)
        if not retrieved:
            print("  ❌ Nothing found by retriever.")
            continue

        gemini_result = find_category_with_gemini_rag(query, retrieved)
        try:
            parts = gemini_result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0]
            final = parts.get('json') or json.loads(parts.get('text', '{}'))

            if "error" in final:
                print(f"  ⚠️ Gemini: {final['error']}")
            elif "subcategory_url" in final and final["subcategory_url"] not in unique_urls:
                # Use config for base URL
                full_url = config.WEBSITE_BASE_URL + final["subcategory_url"]
                print(f"  ✅ Found: {final['subcategory_name']} → {full_url}")
                selected_subcategories.append({
                    "name": final["subcategory_name"],
                    "url": final["subcategory_url"]
                })
                unique_urls.add(final["subcategory_url"])
        except Exception as e:
            print(f"  ⚠️ Failed to parse Gemini response: {e}")
            print(json.dumps(gemini_result, indent=2, ensure_ascii=False))

    if selected_subcategories:
        print("\n🗸 Starting targeted scraping...")
        await zommer_scraper_for_urls(selected_subcategories)
    else:
        print("❌ No subcategories selected for scraping.")
        return

    # === Step 2: Embed scraped data and save to FAISS ===
    print("\n🔮 Starting embedding of scraped products...")
    # Use config for file path
    products = load_products(config.SCRAPED_DATA_FILE)
    vectors, metadata = embed_all_products(products)
    save_faiss_index(vectors, metadata)

    # === Step 3: Test the search ===
    print("\n🔍 Running example semantic search...")
    example_query = "დიდი ბატარიით სმარტ საათი NFC-ით"
    results = search_similar(example_query)

    for r in results:
        print(f"- {r['title']} | {r['price']} ლარი | {r['category']}")

if __name__ == "__main__":
    asyncio.run(main())