# src/product_finder/core_logic/embedding.py
import json
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

from .. import config

embedding_model = SentenceTransformer(config.EMBEDDER_MODEL)

def build_embedding_text(product):
    # ... (function is unchanged) ...
    specs = product.get("specs", {})
    spec_str = ", ".join(f"{k.strip()}: {v}" for k, v in specs.items())
    return f"""
სათაური: {product.get('title')}
კატეგორია: {product.get('category')}
ფასი: {product.get('price')} ლარი
მახასიათებლები: {spec_str}
აღწერა: {product.get('description', '')}
    """

def get_embedding(text, prefix):
    return np.array(embedding_model.encode(prefix + text), dtype="float32")

def embed_all_products(products):
    vectors = []
    metadata = []

    print("პროდუქტების ემბედინგი მიმდინარეობს...")
    for p in tqdm(products, desc="📦 პროდუქტების ვექტორიზაცია"):
        try:
            text = build_embedding_text(p)
            emb = get_embedding(text, config.EMBEDDER_PASSAGE_PREFIX)
            vectors.append(emb)
            metadata.append(p)
        except Exception as e:
            print(f"❌ შეცდომა ემბედინგზე {p.get('title')}: {e}")

    if not vectors:
        return np.array([]), []
        
    return np.vstack(vectors), metadata

def save_faiss_index(vectors, metadata, index_path=config.FAISS_INDEX_FILE, meta_path=config.FAISS_METADATA_FILE):
    if vectors.size == 0:
        print("⚠️ ვექტორები ცარიელია. FAISS ინდექსი არ შეიქმნება.")
        return
        
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)
    faiss.write_index(index, index_path)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ FAISS ინდექსი და მეტამონაცემები შენახულია. ინდექსშია {len(metadata)} პროდუქტი.")

def search_similar(query_text, top_k=config.SEARCH_TOP_K, index_path=config.FAISS_INDEX_FILE, meta_path=config.FAISS_METADATA_FILE):
    query_vector = get_embedding(query_text, config.EMBEDDER_QUERY_PREFIX).reshape(1, -1)
    
    try:
        index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except FileNotFoundError:
        print("❌ ძიების შესასრულებლად საჭიროა index.faiss და metadata.json ფაილები.")
        return []

    distances, indices = index.search(query_vector, top_k)
    results = [metadata[i] for i in indices[0]]

    return results