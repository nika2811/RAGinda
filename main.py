import json
from retriever import HybridRetriever, find_category_with_gemini_rag, load_categories_from_file
from scrapers import zommer_scraper_for_urls

QUERIES = [
    "სამსუნგის საათი მინდა ვიყიდო",
    "ლეპტოპი მჭირდება, თან რომ თამაშებიც გამიქაჩოს",
    "აიფონის დამტენი ხომ არ გაქვთ?",
    "პოვერ ბანკი",
    "ველოსიპედი"
]

def main():
    categories = load_categories_from_file("categories.json")
    if not categories:
        print("❌ Categories not loaded.")
        return

    retriever = HybridRetriever(categories)
    selected_subcategories = []

    for query in QUERIES:
        print(f"\n🔎 Query: {query}")
        retrieved = retriever.search(query, top_k=3)
        if not retrieved:
            print("  ❌ Nothing found by retriever.")
            continue

        gemini_result = find_category_with_gemini_rag(query, retrieved)
        try:
            parts = gemini_result['candidates'][0]['content']['parts'][0]
            final = parts.get('json') or json.loads(parts['text'])
            if "error" in final:
                print(f"  ⚠️ Gemini: {final['error']}")
            else:
                full_url = "https://zoommer.ge" + final["subcategory_url"]
                print(f"  ✅ Found: {final['subcategory_name']} → {full_url}")
                selected_subcategories.append({
                    "name": final["subcategory_name"],
                    "url": final["subcategory_url"]
                })
        except Exception as e:
            print(f"  ⚠️ Failed to parse Gemini response: {e}")
            print(json.dumps(gemini_result, indent=2, ensure_ascii=False))

    if selected_subcategories:
        print("\n🕸️ Starting targeted scraping...")
        zommer_scraper_for_urls(selected_subcategories)
    else:
        print("❌ No subcategories selected for scraping.")

if __name__ == "__main__":
    main()