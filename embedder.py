import os
import json
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import hashlib
import re

# --- Configuration ---
SOURCE_PRODUCTS_PATH = "output/zoommer_scraping.json"
FAISS_INDEX_PATH = "output/products.faiss"
METADATA_PATH = "output/products_metadata.json"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
RRF_K = 60

# --- Initialization ---
print("⏳ ემბედინგის მოდელის ჩატვირთვა...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
print("✅ მოდელი ჩატვირთულია.")

def get_file_hash(filepath):
    """Calculates SHA256 hash of a file's content to check for updates."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def clean_and_extract_description(raw_description):
    """
    Extracts the meaningful product description from the noisy raw text
    by removing UI elements, other product info, and irrelevant sections.
    """
    if not isinstance(raw_description, str):
        return ""

    try:
        # Start after the last occurrence of "აღწერა" to get the primary description
        start_index = raw_description.rfind('აღწერა\n') + len('აღწერა\n')
        clean_text = raw_description[start_index:]
    except ValueError:
        clean_text = raw_description
        
    # Define markers that indicate the end of the relevant description
    stop_markers = [
        "მსგავსი პროდუქტები", "ფილიალები", "ერთად იაფია", 
        "გაეცანი საგარანტიო პირობებს", "Copyright ©", "დამატებითი მახასიათებლები"
    ]
    
    first_stop_index = len(clean_text)
    for marker in stop_markers:
        found_index = clean_text.find(marker)
        if found_index != -1:
            first_stop_index = min(first_stop_index, found_index)
            
    clean_text = clean_text[:first_stop_index]
    
    # Final cleanup of residual noise
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    clean_text = re.sub(r'\d+\s*₾', '', clean_text) # Remove prices
    clean_text = clean_text.replace("მეტის ნახვა", "").replace("დამატება", "")
    return clean_text

def build_searchable_text(product):
    """
    Creates a rich, CLEAN, and unified text representation of a product
    for both embedding and keyword search.
    """
    specs = product.get("specs", {})
    # Clean keys and join with values for a natural language feel
    spec_str = " ".join(f"{str(k).replace(':', '').strip()} {v}" for k, v in specs.items())
    
    clean_desc = clean_and_extract_description(product.get("description", ""))
    
    # Combine all relevant, clean fields into one searchable string
    return (
        f"{product.get('title', '')}. "
        f"კატეგორია: {product.get('category', '')}. "
        f"ფასი: {product.get('price', 0)} ლარი. "
        f"მახასიათებლები: {spec_str}. "
        f"აღწერა: {clean_desc}"
    ).lower()

def get_embedding(text, prefix="passage: "):
    """Generates a numpy embedding for a given text."""
    return np.array(embedding_model.encode([prefix + text]), dtype="float32")[0]

def create_or_update_index(products_path, index_path, meta_path):
    """Creates a FAISS index only if the source data has changed."""
    if not os.path.exists(products_path):
        print(f"❌ საწყისი ფაილი ვერ მოიძებნა: {products_path}")
        return

    current_hash = get_file_hash(products_path)
    if os.path.exists(index_path) and os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata_content = json.load(f)
        if metadata_content.get("_source_hash") == current_hash:
            print("✅ ინდექსი აქტუალურია. ემბედინგის გამოტოვება.")
            return

    print("🔄 ინდექსი მოძველებულია ან არ არსებობს. სრული განახლება...")
    with open(products_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    metadata_list = []
    for p in tqdm(products, desc="📦 ემბედინგი მიმდინარეობს"):
        p['product_id'] = p['link']
        p['searchable_text'] = build_searchable_text(p)
        metadata_list.append(p)

    if not metadata_list:
        print("⚠️ პროდუქტები ვერ მოიძებნა. ინდექსი არ შენახულა.")
        return

    vectors_np = np.vstack([get_embedding(p['searchable_text']) for p in metadata_list]).astype('float32')
    dim = vectors_np.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors_np)
    faiss.write_index(index, index_path)

    final_metadata = {"_source_hash": current_hash, "products": metadata_list}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(final_metadata, f, ensure_ascii=False, indent=2)
    print(f"✅ შენახულია {len(metadata_list)} პროდუქტი")

def hybrid_search(query_text, top_k=5):
    """Performs the definitive hybrid search on clean, pre-processed data."""
    if not (os.path.exists(FAISS_INDEX_PATH) and os.path.exists(METADATA_PATH)):
        print("❌ ინდექსი არ არსებობს. გთხოვთ, ჯერ გაუშვათ სკრიპტი ინდექსის შესაქმნელად.")
        return []
        
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)["products"]
    product_map = {p['product_id']: p for p in metadata}

    # --- 1. Semantic Search ---
    print("\n🔍 სემანტიკური ძიება (FAISS)...")
    index = faiss.read_index(FAISS_INDEX_PATH)
    query_vector = get_embedding(query_text.lower(), prefix="query: ").reshape(1, -1)
    _, indices = index.search(query_vector, k=min(20, len(metadata)))
    semantic_results = [metadata[i] for i in indices[0]]

    # --- 2. Keyword Search on Clean Data ---
    print("🔑 საკვანძო სიტყვებით ძიება...")
    query_lower = query_text.lower()
    keywords = set(word for word in re.split(r'\W+', query_lower) if len(word) > 1)
    keyword_scores = {}
    for product in metadata:
        score = 0
        full_text = product.get('searchable_text', '') # Uses pre-cleaned, unified text
        
        if query_lower in full_text:
            score += 1000 # Exact phrase match bonus
        
        for keyword in keywords:
            if keyword in full_text:
                score += 10
        
        if score > 0:
            keyword_scores[product['product_id']] = score
    
    sorted_keyword_ids = sorted(keyword_scores, key=keyword_scores.get, reverse=True)
    keyword_results = [product_map.get(pid) for pid in sorted_keyword_ids[:20] if product_map.get(pid)]

    # --- 3. Reciprocal Rank Fusion ---
    print("🔗 შედეგების გაერთიანება (RRF)...")
    rrf_scores = {}
    for rank, doc in enumerate(semantic_results):
        rrf_scores[doc['product_id']] = 1 / (RRF_K + rank + 1)
    for rank, doc in enumerate(keyword_results):
        doc_id = doc['product_id']
        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = 0
        rrf_scores[doc_id] += 1 / (RRF_K + rank + 1)
    
    sorted_doc_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
    final_results = [product_map[doc_id] for doc_id in sorted_doc_ids[:top_k]]
    return final_results

# --- Example Runner ---
if __name__ == "__main__":
    # This will now create the index based on CLEAN data
    create_or_update_index(SOURCE_PRODUCTS_PATH, FAISS_INDEX_PATH, METADATA_PATH)

    print("\n" + "="*50)
    print("HYBRID SEARCH EXAMPLE (ON CLEAN DATA)")
    print("="*50)
    
    query1 = "სმარტ საათი, დიდი ბატარიით და NFC-ით"
    print(f"\n🔎 ძიება: '{query1}'")
    results1 = hybrid_search(query1, top_k=5)
    for r in results1:
        print(f"  - {r['title']} | {r['price']} ლარი | {r['category']}")
    
    print("-" * 50)
    
    query2 = "SM-S908E"
    print(f"\n🔎 ძიება: '{query2}'")
    results2 = hybrid_search(query2, top_k=3)
    if results2:
        for r in results2:
            print(f"  - {r['title']} | {r['price']} ლარი | {r['category']}")
    else:
        print("  - ზუსტი დამთხვევა ვერ მოიძებნა, რადგან პროდუქტი ამ მოდელის ნომრით არ არსებობს მონაცემთა ბაზაში.")