# main.py (დიაგნოსტიკური ვერსია)

import json
import asyncio

# ყურადღება მიაქციეთ შეცვლილ იმპორტებს
from src.product_finder import config
from src.product_finder.utils.data_io import load_categories_from_file, load_products
from src.product_finder.core_logic.retriever import HybridRetriever
from src.product_finder.core_logic.llm import find_category_with_gemini_rag
from src.product_finder.core_logic.embedding import embed_all_products, save_faiss_index, search_similar
from src.product_finder.scraping.zoommer_scraper import zommer_scraper_for_urls



async def main():
    print("--- [DEBUG 1] main ფუნქცია დაიწყო ---")
    
    print("--- [DEBUG 2] იტვირთება კატეგორიები ---")
    categories = load_categories_from_file(config.CATEGORIES_FILE)
    if not categories:
        print("❌ კატეგორიები ვერ ჩაიტვირთა ან ფაილი ცარიელია. პროცესი ჩერდება.")
        return
    print(f"--- [DEBUG 3] კატეგორიები ჩაიტვირთა. ნაპოვნია {len(categories)} მთავარი კატეგორია ---")

    print("--- [DEBUG 4] იქმნება HybridRetriever ---")
    retriever = HybridRetriever(categories)
    print("--- [DEBUG 5] HybridRetriever შეიქმნა ---")


    # მომხმარებლისგან კითხვაზე შეყვანა
    user_query = await asyncio.to_thread(input, "\n🔎 შეიყვანეთ თქვენი მოთხოვნა: ")
    print(f"\nმომხმარებლის მოთხოვნა: {user_query}")
    retrieved = retriever.search(user_query, top_k=config.RETRIEVER_TOP_K)
    if not retrieved:
        print("❌ Retriever-მა რელევანტური კატეგორია ვერ იპოვა.")
        return

    print(f"--- [DEBUG 7] Retriever-მა იპოვა {len(retrieved)} კანდიდატი. იგზავნება LLM-თან ---")
    final_choice = find_category_with_gemini_rag(user_query, retrieved)
    print(f"--- [DEBUG 8] მიღებულია პასუხი LLM-სგან: {final_choice}")

    if "error" in final_choice:
        print(f"⚠️ LLM: {final_choice['error']}")
        return
    if "subcategory_url" not in final_choice:
        print("⚠️ LLM-მა ვერ შეარჩია კატეგორია.")
        return

    full_url = config.WEBSITE_BASE_URL + final_choice["subcategory_url"]
    print(f"✅ LLM-მა შეარჩია: {final_choice['subcategory_name']} → {full_url}")
    selected_subcategories = [{
        "name": final_choice["subcategory_name"],
        "url": final_choice["subcategory_url"]
    }]

    print("\n--- ეტაპი 2: მიზნობრივი სკრეიპინგი ---")
    await zommer_scraper_for_urls(selected_subcategories)

    print("\n--- ეტაპი 3: ემბედინგი და ვექტორული ბაზის შექმნა ---")
    products = load_products(config.SCRAPED_DATA_FILE)
    if not products:
        print("❌ დასამუშავებელი პროდუქტები ვერ მოიძებნა. პროცესი შეჩერებულია.")
        return

    vectors, metadata = embed_all_products(products)
    save_faiss_index(vectors, metadata)

    print("\n--- ეტაპი 4: სემანტიკური ძიება ---")
    print(f"\n🔍 ძიება: \"{user_query}\"")
    results = search_similar(user_query)

    print("\nნაპოვნი პროდუქტები:")
    for r in results:
        print(f"  - {r['title']} | {r['price']} ლარი | {r['category']}")

    print("--- [DEBUG 10] main ფუნქცია დასრულდა ---")

if __name__ == "__main__":
    try:
        print("--- [DEBUG 0] პროგრამა ეშვება __main__ ბლოკიდან ---")
        asyncio.run(main())
    except Exception as e:
        print(f"\n\nFATAL ERROR: კრიტიკული შეცდომა პროგრამის გაშვებისას: {e}")
        import traceback
        traceback.print_exc()